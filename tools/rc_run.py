#!/usr/bin/env python3
"""Run a scanner over the REAL CRATES, one invocation per case per variant.

The real-crate corpus is the answer to the packaging objection: corpus 2 extracts each
implicated file into a minimal crate so a scanner will parse it, and a fair critic can say
that the result is then an artefact of our packaging rather than of the tool. The real
crates are the same fix commits and their parents taken as the whole crate directory the
project itself ships, produced by `build_corpus2.py --crates`.

Until 2026-09-01 only Radar and VaultLint had ever been run there, so the objection was
tested for a quarter of the tools and retired for none. This runner exists to close that,
and it follows the same protocol as every other run in this repository:

  * one artefact per invocation, kept, plus one JSON log line per invocation
  * coverage is read from the TOOL'S OWN account of what it opened, never from the presence
    of an output file: `paths.scanned` for semgrep, `Found N Rust files` for solsec,
    `files_scanned` for sol-audit, a parsed `.ll.json` report for X-Ray
  * a run that errored, timed out or opened nothing is UNAVAILABLE, never a zero
  * the container gets the corpus read-only and, where the tool permits it, no network

Usage:
    python3 rc_run.py --tool semgrep --crates /tmp/rc-crates --out /root/rc-out
    python3 rc_run.py --demo
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

SEMGREP_IMAGE = "semgrep/semgrep:latest"
SOLSEC_IMAGE = "solsec-runner:0.2.1"
XRAY_IMAGE = "ghcr.io/sec3-product/x-ray:latest"
PY_IMAGE = "nikolaik/python-nodejs:python3.11-nodejs20"

FILES_RE = re.compile(r"Found (\d+) Rust files to analyze")
# solsec exits 1 when it finds a critical issue: "Critical issues found. Failing as requested."
# That is a CI gate reporting a result, not an outage, and the first version of this runner
# recorded eight such runs as unavailable - a "could not run" about a scan that completed and
# said so in its own log, which is the mistake this project made in the opposite direction on
# 2026-09-01 (error 36). Corrected after seeing the output, deliberately and on the record: the
# tool's own log line decides, not the exit code.
SOLSEC_GATE_RE = re.compile(r"Critical issues found\. Failing as requested")


def leaves(crates_root):
    """(leaf, absolute target dir) for every case/variant on disk, sorted."""
    out = []
    for case in sorted(os.listdir(crates_root)):
        d = os.path.join(crates_root, case)
        if not os.path.isdir(d):
            continue
        for variant in ("insecure", "secure"):
            vd = os.path.join(d, variant)
            if os.path.isdir(vd):
                out.append(("%s/%s" % (case, variant), vd))
    return out


def sh(cmd, timeout):
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout or "", p.stderr or "", round(time.time() - t0, 1)
    except subprocess.TimeoutExpired:
        return 124, "", "TIMEOUT after %ss" % timeout, round(time.time() - t0, 1)


def write_log(path, cmd, rc, wall, stdout, stderr):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("COMMAND: " + " ".join(cmd) + "\n")
        fh.write("RC: %s\nWALL: %ss\n\nSTDOUT:\n%s\n\nSTDERR:\n%s\n"
                 % (rc, wall, stdout[-4000:], stderr[-4000:]))


# --------------------------------------------------------------------------- semgrep

def semgrep(leaf, target, out_dir, rules_dir, timeout):
    oj = os.path.join(out_dir, leaf.replace("/", ".") + ".json")
    ol = oj[:-5] + ".log"
    cmd = ["docker", "run", "--rm", "--network", "none",
           "-v", target + ":/src:ro", "-v", rules_dir + ":/rules:ro",
           "-e", "SEMGREP_SEND_METRICS=off", "-e", "SEMGREP_ENABLE_VERSION_CHECK=0",
           SEMGREP_IMAGE, "semgrep",
           "--config", "/rules/solana-security-standard.yaml",
           "--json", "--quiet", "--no-git-ignore", "--metrics=off",
           "--disable-version-check", "--timeout", "60", "/src"]
    rc, so, se, wall = sh(cmd, timeout)
    with open(oj, "w", encoding="utf-8") as fh:
        fh.write(so)
    write_log(ol, cmd, rc, wall, "", se)
    try:
        blob = json.loads(so)
    except Exception as exc:
        return None, {"rc": rc, "wall_s": wall, "artefact": oj,
                      "why": "output did not parse as JSON: %r" % (exc,)}
    scanned = (blob.get("paths") or {}).get("scanned") or []
    if rc not in (0, 1) or not scanned:
        return None, {"rc": rc, "wall_s": wall, "artefact": oj, "files_opened": len(scanned),
                      "why": "rc=%s scanned=%d errors=%s" % (rc, len(scanned), blob.get("errors"))}
    rows = []
    for r in blob.get("results") or []:
        p = r.get("path", "")
        rel = p[len("/src/"):] if p.startswith("/src/") else p.lstrip("/")
        cid = r.get("check_id", "")
        rows.append({"check_id": cid[len("rules."):] if cid.startswith("rules.") else cid,
                     "path": leaf + "/" + rel,
                     "start": {"line": (r.get("start") or {}).get("line", 0)},
                     "raw_check_id": cid})
    return rows, {"rc": rc, "wall_s": wall, "artefact": oj, "files_opened": len(scanned),
                  "errors": blob.get("errors") or []}


# ---------------------------------------------------------------------------- solsec

def solsec(leaf, target, out_dir, _rules, timeout):
    od = os.path.join(out_dir, leaf.replace("/", "."))
    os.makedirs(od, exist_ok=True)
    cmd = ["docker", "run", "--rm", "--network", "none",
           "-v", target + ":/src:ro", "-v", od + ":/out",
           SOLSEC_IMAGE, "scan", "/src", "-o", "/out", "--json-only", "--no-open"]
    rc, so, se, wall = sh(cmd, timeout)
    combined = so + se
    write_log(os.path.join(od, "run.log"), cmd, rc, wall, so, se)
    files = FILES_RE.search(combined)
    n = int(files.group(1)) if files else 0
    report = os.path.join(od, "security-report.json")
    blob = None
    if os.path.exists(report):
        try:
            with open(report, encoding="utf-8") as fh:
                blob = json.load(fh)
        except Exception:
            blob = None
    gated = bool(SOLSEC_GATE_RE.search(combined))
    if rc not in (0, 1) or (rc == 1 and not gated) or n == 0 or blob is None:
        return None, {"rc": rc, "wall_s": wall, "artefact": od, "files_opened": n,
                      "why": "rc=%s gate=%s files=%s report=%s"
                             % (rc, gated, n,
                                "parsed" if blob is not None else "missing/unparseable")}
    rows = []
    src = blob.get("analysis_results") if isinstance(blob, dict) else blob
    for r in src or []:
        fp = str(r.get("file_path") or r.get("file") or "")
        if fp.startswith("./"):
            fp = fp[2:]
        if fp.startswith("/src/"):
            fp = fp[len("/src/"):]
        rows.append(dict(r, file_path=leaf + "/" + fp))
    return rows, {"rc": rc, "wall_s": wall, "artefact": od, "files_opened": n,
                  "exit_gate": gated}


# ------------------------------------------------------------------------- sol-audit

def sol_audit(leaf, target, out_dir, tool_dir, timeout, profile="strict"):
    oj = os.path.join(out_dir, leaf.replace("/", ".") + "." + profile + ".json")
    ol = oj[:-5] + ".log"
    per_file = oj[:-5] + ".files.log"
    cmd = ["docker", "run", "--rm", "--network", "none",
           "-v", tool_dir + ":/tool:ro", "-v", target + ":/src:ro",
           "-v", os.path.dirname(oj) + ":/out",
           PY_IMAGE, "python3", "/tool/cli.py", "--format", "json", "--profile", profile,
           "--out", "/out/" + os.path.basename(oj), "--log", "/out/" + os.path.basename(per_file),
           "--fail-on", "none", "/src"]
    rc, so, se, wall = sh(cmd, timeout)
    write_log(ol, cmd, rc, wall, so, se)
    blob = None
    if os.path.exists(oj):
        try:
            with open(oj, encoding="utf-8") as fh:
                blob = json.load(fh)
        except Exception:
            blob = None
    if rc != 0 or blob is None or not blob.get("files_scanned"):
        return None, {"rc": rc, "wall_s": wall, "artefact": oj, "profile": profile,
                      "files_opened": (blob or {}).get("files_scanned", 0),
                      "why": "rc=%s report=%s files_scanned=%s"
                             % (rc, "parsed" if blob else "missing/unparseable",
                                (blob or {}).get("files_scanned"))}
    rows = []
    for f in blob.get("findings") or []:
        rows.append(dict(f, file=leaf + "/" + str(f.get("file", "")).replace("\\", "/")))
    return rows, {"rc": rc, "wall_s": wall, "artefact": oj, "profile": profile,
                  "files_opened": blob.get("files_scanned", 0),
                  "errors": blob.get("errors") or []}


# ------------------------------------------------------------------------------ xray

def xray(leaf, target, out_dir, _rules, timeout, network="none"):
    """X-Ray writes its build tree into the directory it is given, so the corpus cannot be
    mounted read-only for it. The variant is copied to a scratch directory and that copy is
    mounted instead, which keeps the corpus itself untouched and leaves no `.xray` directory
    for the next tool to scan."""
    od = os.path.join(out_dir, leaf.replace("/", "."))
    os.makedirs(od, exist_ok=True)
    work = os.path.join(out_dir, "_work", leaf.replace("/", "."))
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(os.path.dirname(work), exist_ok=True)
    shutil.copytree(target, work)
    xray_dir = os.path.join(work, ".xray")
    cmd = ["docker", "run", "--rm", "--network", network,
           "--volume", work + ":/workspace", XRAY_IMAGE, "/workspace"]
    rc, so, se, wall = sh(cmd, timeout)
    write_log(os.path.join(od, "run.log"), cmd, rc, wall, so, se)
    reports = sorted(glob.glob(os.path.join(xray_dir, "build", "*.ll.json")))
    for r in reports:
        shutil.copy(r, os.path.join(od, os.path.basename(r)))
    if not reports:
        shutil.rmtree(work, ignore_errors=True)
        return None, {"rc": rc, "wall_s": wall, "artefact": od, "files_opened": 0,
                      "why": "rc=%s no .ll.json report produced" % rc}
    rows = []
    for r in reports:
        try:
            with open(r, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:
            return None, {"rc": rc, "wall_s": wall, "artefact": od,
                          "why": "report did not parse: %r" % (exc,)}
        for bucket in ("untrustfulAccounts", "unsafeOperations", "cosplayAccounts"):
            for item in data.get(bucket) or []:
                inst = item.get("inst") or {}
                fn = inst.get("filename", "")
                if not fn:
                    continue
                rows.append({"name": str(item.get("id", "")),
                             "rule_name": item.get("description", ""),
                             "bucket": bucket,
                             "locations": ["%s/%s:%s:%s" % (leaf, fn.lstrip("/"),
                                                            inst.get("line", 0),
                                                            inst.get("col", 0))]})
    shutil.rmtree(work, ignore_errors=True)
    return rows, {"rc": rc, "wall_s": wall, "artefact": od, "files_opened": len(reports),
                  "reports": len(reports)}


# ----------------------------------------------------------------------------- radar

def radar(leaf, target, out_dir, _rules, timeout, _network="none"):
    """Radar orchestrates its own containers, so it is driven through its own CLI.

    Two things this project has already paid for: radar wants the `Cargo.toml` in a
    SUBDIRECTORY of the path it is given, which the real-crate layout satisfies, and it
    prints `Results written to <path>` for files it did not write, so the output file is
    opened and parsed before anything is called ok. `-f none` stops it exiting 1 merely for
    having findings, which leaves a non-zero exit meaning a real failure.
    """
    oj = os.path.join(out_dir, leaf.replace("/", ".") + ".json")
    ol = oj[:-5] + ".log"
    if os.path.exists(oj):
        os.remove(oj)
    cmd = ["radar", "scan", "-p", target, "-f", "none", "-o", oj]
    rc, so, se, wall = sh(cmd, timeout)
    write_log(ol, cmd, rc, wall, so, se)
    blob = None
    if os.path.exists(oj) and os.path.getsize(oj):
        try:
            with open(oj, encoding="utf-8") as fh:
                blob = json.load(fh)
        except Exception:
            blob = None
    if blob is None:
        m = re.search(r"Exceeded maximum retries[^\"\n]*", so + se)
        return None, {"rc": rc, "wall_s": wall, "artefact": oj,
                      "why": m.group(0) if m else "rc=%s no parseable output" % rc}
    items = blob if isinstance(blob, list) else (blob.get("findings") or [])
    rows = []
    for it in items:
        locs = []
        for loc in it.get("locations") or []:
            rel = loc
            if target in loc:
                rel = loc.split(target, 1)[1].lstrip("/")
            locs.append(leaf + "/" + rel)
        rows.append(dict(it, locations=locs))
    return rows, {"rc": rc, "wall_s": wall, "artefact": oj, "files_opened": None,
                  "raw_findings": len(items)}


ENVELOPE = {"semgrep": ("results", semgrep),
            "solsec": ("analysis_results", solsec),
            "sol-audit": ("findings", sol_audit),
            "xray": (None, xray),
            "radar": (None, radar)}


def do(tool, crates_root, out_root, findings_path, log_path, rules_dir, tool_dir,
       timeout, profile=None, network="none"):
    key, fn = ENVELOPE[tool]
    os.makedirs(out_root, exist_ok=True)
    rows, log = [], []
    for leaf, target in leaves(crates_root):
        if tool == "sol-audit":
            got, meta = fn(leaf, target, out_root, tool_dir, timeout, profile)
        elif tool == "xray":
            got, meta = fn(leaf, target, out_root, rules_dir, timeout, network)
        else:
            got, meta = fn(leaf, target, out_root, rules_dir, timeout)
        if got is None:
            log.append(dict(meta, leaf=leaf, status="unavailable", reason=meta.get("why", "")))
            print("UNAVAILABLE %-50s %s" % (leaf, meta.get("why", "")), flush=True)
            continue
        rows.extend(got)
        log.append(dict(meta, leaf=leaf, status="ok", findings=len(got)))
        print("ok          %-50s findings=%-5d files=%-4s %ss"
              % (leaf, len(got), meta.get("files_opened", "?"), meta.get("wall_s")), flush=True)
    payload = rows if key is None else {key: rows}
    with open(findings_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    with open(log_path, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1)
    ok = sum(1 for e in log if e["status"] == "ok")
    print("%s: %d invocations, %d ok, %d unavailable, %d findings"
          % (tool, len(log), ok, len(log) - ok, len(rows)))
    return log


def demo():
    """Check the two decisions this runner makes, without needing docker.

    Both are the ones that have gone wrong in this repository before: which leaves exist,
    and whether an empty result is a zero or an outage.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        for case in ("b-case", "a-case"):
            for variant in ("insecure", "secure"):
                os.makedirs(os.path.join(d, case, variant, "src"))
        open(os.path.join(d, "loose.txt"), "w").write("not a case")
        got = [leaf for leaf, _ in leaves(d)]
        assert got == ["a-case/insecure", "a-case/secure",
                       "b-case/insecure", "b-case/secure"], got
    assert FILES_RE.search("Found 12 Rust files to analyze").group(1) == "12"
    assert FILES_RE.search("Found 0 Rust files to analyze").group(1) == "0"
    assert SOLSEC_GATE_RE.search("ERROR solsec::cli] Critical issues found. Failing as requested.")
    assert not SOLSEC_GATE_RE.search("ERROR solsec::cli] could not open /src")
    print("rc_run: OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", choices=sorted(ENVELOPE))
    ap.add_argument("--crates", default="/tmp/rc-crates")
    ap.add_argument("--out", default="/root/rc-20260901/out")
    ap.add_argument("--findings")
    ap.add_argument("--log")
    ap.add_argument("--rules", default="/root/st-fix-20260901/rules")
    ap.add_argument("--tool-dir", default="/root/rc-20260901/sol-audit")
    ap.add_argument("--profile", default="strict")
    ap.add_argument("--network", default="none")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        demo()
        return 0
    if not args.tool:
        ap.error("--tool is required unless --demo")
    stem = args.tool + ("-" + args.profile if args.tool == "sol-audit" else "")
    findings = args.findings or os.path.join(args.out, "rc-%s.json" % stem)
    log = args.log or (findings + ".log")
    do(args.tool, args.crates, os.path.join(args.out, stem), findings, log,
       args.rules, args.tool_dir, args.timeout, args.profile, args.network)
    return 0


if __name__ == "__main__":
    sys.exit(main())
