#!/usr/bin/env python3
"""Turn a directory of per-run scanner artefacts into the findings file and run log the clock reads.

This exists because the 2026-09-01 audit found that `raw/c2-radar-complete.json`,
`raw/c2-vaultlint-complete.json` and `raw/c2-xray.json` are not raw output at all: they are the
tools' own output hand-normalised into another scanner's envelope with the container paths
rewritten, and **no conversion script was committed**. The two most-quoted corpus-2 rows sat
behind a transformation nobody could reproduce. Whatever else is wrong with a number, the step
that produced it has to be in the repository.

Radar in particular needs two things doing carefully, and one of them has already cost this
project a published error.

**radar writes no output file when it finds nothing.** The runner that produced the 2026-08-31
log decided `ok` versus `UNAVAILABLE` by asking whether an output file existed, so a clean zero
and a failed run were indistinguishable, and one clean zero was published as UNAVAILABLE
(error 32). radar's own stdout is the authority: it prints `Scanned N file` and `radar completed
successfully` for a run that happened, whether or not it found anything. That is what is read
here.

**radar refuses a target whose Cargo.toml sits at its root**, so each case is wrapped as
`<case>.<variant>/pkg/{Cargo.toml,src}` before the run and the wrapper prefix is stripped
afterwards. The rewrite is a pure string operation on the location prefix; no line, column,
rule name or severity is touched.

    python tools/normalise_runs.py --kind radar --runs <dir> --out raw/c2-radar-current.json
    python tools/normalise_runs.py --demo
"""
import argparse
import json
import os
import re
import sys

ANSI = re.compile(r"\x1b\[[0-9;]*m")
WRAPPED = re.compile(r"^.*/(?P<case>[^/]+)\.(?P<variant>insecure|secure|recommended)/pkg/(?P<rest>.*)$")


def classify_radar(stdout_text):
    """(status, files_scanned, reason). radar's own account of whether the run happened."""
    s = ANSI.sub("", stdout_text)
    m = re.search(r"Scanned (\d+) file", s)
    scanned = int(m.group(1)) if m else 0
    if "radar completed successfully" in s and scanned > 0:
        return "ok", scanned, ""
    fail = re.search(r"Failed to process source path[^\"\n]*", s)
    retry = re.search(r"Exceeded maximum retries[^\"\n]*", s)
    return "unavailable", scanned, (fail or retry).group(0) if (fail or retry) else (
        "no 'Scanned N file' line: radar did not report analysing anything")


def rewrite(location, corpus="corpus2"):
    """/tmp/<anything>/<case>.<variant>/pkg/src/x.rs:12:3-9 -> corpus2/<case>/<variant>/src/x.rs:12:3-9"""
    loc = str(location).replace("\\", "/")
    head, sep, tail = loc.partition(".rs:")
    path, suffix = (head + ".rs", ":" + tail) if sep else (loc, "")
    m = WRAPPED.match(path)
    if not m:
        return loc
    return f"{corpus}/{m.group('case')}/{m.group('variant')}/{m.group('rest')}{suffix}"


def collect_radar(runs_dir, corpus="corpus2"):
    """Returns {"<case>/<variant>": (log entry, [findings in radar's own envelope])}."""
    out = {}
    leaves = sorted(fn[:-len(".stdout.log")] for fn in os.listdir(runs_dir)
                    if fn.endswith(".stdout.log"))
    for leaf in leaves:
        stdout_path = os.path.join(runs_dir, leaf + ".stdout.log")
        json_path = os.path.join(runs_dir, leaf + ".json")
        with open(stdout_path, encoding="utf-8", errors="replace") as fh:
            status, scanned, reason = classify_radar(fh.read())
        case, _, variant = leaf.rpartition(".")
        entry = {"leaf": f"{case}/{variant}", "status": status, "files_scanned": scanned,
                 "artefact": os.path.join(runs_dir, leaf + ".json").replace("\\", "/"),
                 "stdout": stdout_path.replace("\\", "/")}
        if status != "ok":
            entry["reason"] = reason
            out[entry["leaf"]] = (entry, [])
            continue
        got, items_out = 0, []
        if os.path.exists(json_path) and os.path.getsize(json_path):
            with open(json_path, encoding="utf-8") as fh:
                for item in json.load(fh) or []:
                    locs = [rewrite(x, corpus) for x in item.get("locations") or []]
                    got += len(locs)
                    items_out.append({**item, "locations": locs})
        entry["findings"] = got
        out[entry["leaf"]] = (entry, items_out)
    return out


def demo():
    import tempfile
    ok = ("[i] Ran 57 templates\n[i] Scanned 1 file (interface_account.rs)\n"
          "[i] radar completed successfully. No results found.\n")
    bad = ('[e] 400 Client Error\n{"error": "Failed to process source path /radar_data/contract: '
           'No Cargo.toml files found in any subdirectories."}\n')
    assert classify_radar(ok)[0] == "ok", classify_radar(ok)
    assert classify_radar(ok)[1] == 1
    assert classify_radar(bad)[0] == "unavailable"
    assert "Failed to process source path" in classify_radar(bad)[2]

    assert rewrite("/tmp/radar-c2-wrap/wormhole-sysvar.insecure/pkg/src/verify_signature.rs:68:8-25") \
        == "corpus2/wormhole-sysvar/insecure/src/verify_signature.rs:68:8-25"
    assert rewrite("corpus2/x/insecure/src/a.rs:1:1") == "corpus2/x/insecure/src/a.rs:1:1"

    with tempfile.TemporaryDirectory() as d:
        # a run that found nothing writes NO json file, and must still be ok, not unavailable.
        with open(os.path.join(d, "case-a.insecure.stdout.log"), "w") as fh:
            fh.write(ok)
        with open(os.path.join(d, "case-b.secure.stdout.log"), "w") as fh:
            fh.write("[i] Ran 57 templates\n[i] Scanned 2 file\n"
                     "[i] radar completed successfully. json results were saved to disk.\n")
        with open(os.path.join(d, "case-b.secure.json"), "w") as fh:
            json.dump([{"name": "Type Cosplay", "locations":
                        ["/tmp/w/case-b.secure/pkg/src/lib.rs:9:1-2"]}], fh)
        with open(os.path.join(d, "case-c.insecure.stdout.log"), "w") as fh:
            fh.write(bad)
        runs = collect_radar(d)
        assert runs["case-a/insecure"][0]["status"] == "ok", runs
        assert runs["case-a/insecure"][0]["findings"] == 0, runs
        assert runs["case-c/insecure"][0]["status"] == "unavailable", runs
        assert runs["case-b/secure"][1][0]["locations"] ==             ["corpus2/case-b/secure/src/lib.rs:9:1-2"], runs
    print("normalise_runs: OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", default="radar", choices=["radar"])
    ap.add_argument("--runs")
    ap.add_argument("--out")
    ap.add_argument("--corpus", default="corpus2")
    ap.add_argument("--extra-runs", action="append", default=[],
                    help="another run directory whose leaves REPLACE the ones already collected")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        demo()
        return 0

    runs = collect_radar(args.runs, args.corpus)
    # A later run directory REPLACES a leaf outright rather than adding to it. Two runs of one
    # leaf are two observations of the same thing, and merging them would invent a run that never
    # happened. Both directories stay on disk either way.
    for extra in args.extra_runs:
        runs.update(collect_radar(extra, args.corpus))
    log = [runs[k][0] for k in sorted(runs)]
    findings = [f for k in sorted(runs) for f in runs[k][1]]
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(findings, fh, indent=1)
        fh.write("\n")
    with open(args.out + ".log", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(log, fh, indent=1)
        fh.write("\n")
    ok = sum(1 for e in log if e["status"] == "ok")
    print(f"{len(log)} runs, {ok} ok, {len(log) - ok} unavailable, "
          f"{sum(len(f['locations']) for f in findings)} findings")
    print(f"written: {args.out} and {args.out}.log")
    return 0


if __name__ == "__main__":
    sys.exit(main())
