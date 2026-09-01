"""One invocation: the argv, the staging, the artefact, and zero versus outage."""
import json
import os
import re
import shutil
import subprocess
import time

from . import ROOT
from .parsers import _int, PARSERS, parse_text_regex


# --------------------------------------------------------------------------- invocation

def _subst(value, mapping):
    for key, val in mapping.items():
        value = value.replace("{" + key + "}", val)
    return value


def _args_for(spec, args=None):
    """The declaration's own argument defaults, with the caller's overrides on top.

    sol-audit has three profiles, all three were run and all three are published, and the three
    rows differ by one token. Before this the declaration could only produce the `strict` row and
    the other two had to be run by a script outside the framework, which is exactly the situation
    the framework exists to end. A token the declaration does not declare is refused, so a typo
    cannot silently leave the default in place and label the run with the other profile's name.
    """
    defaults = dict(spec["run"].get("arg_defaults") or {})
    for key, val in (args or {}).items():
        if key not in defaults:
            raise ValueError(
                f"{spec['name']}: --arg {key}={val} names a token this declaration does not "
                f"declare. run.arg_defaults holds {sorted(defaults) or 'nothing'}.")
        defaults[key] = val
    return defaults


def command_for(spec, target_dir, artefact_dir, tool_root=None, args=None):
    """The exact argv. Recorded in the log so a reader can rerun it without reading this file."""
    run = spec["run"]
    mount = run.get("mount", "/src")
    out_mount = run.get("out_mount")
    if run["engine"] == "unrecorded":
        raise ValueError(f"{spec['name']}: nobody recorded how this was invoked. "
                         + run.get("reason", ""))
    root = tool_root or run.get("tool_root") or ""
    if root and not os.path.isabs(root):
        root = os.path.normpath(os.path.join(ROOT, root))
    extra = _args_for(spec, args)
    if run["engine"] == "local":
        tokens = {"mount": target_dir, "target": target_dir, "tool_root": root,
                  "out": artefact_dir, "artefact_dir": artefact_dir, "root": ROOT, **extra}
        return [_subst(a, tokens) for a in run["command"]]
    cmd = ["docker", "run", "--rm"]
    if run.get("network", "none"):
        cmd += ["--network", run.get("network", "none")]
    # Absolute, because docker reads a relative bind source as the NAME of a named volume. Passing
    # `--artefacts raw/solsec-c2` produced `docker: invalid characters for a local volume name` on
    # all 34 invocations of a solsec run. The framework classified every one of them `unavailable`
    # rather than a zero, which is what it is for, but the run still had to be done twice.
    cmd += ["-v", f"{os.path.abspath(target_dir)}:{mount}:ro"]
    if out_mount:
        cmd += ["-v", f"{os.path.abspath(artefact_dir)}:{out_mount}"]
    # A file or directory this MEASUREMENT needs inside the container that is not the corpus and
    # not the tool: semgrep's ruleset is the case that forced it. Without this the declaration
    # named `--config /rules/solana-security-standard.yaml` and nothing put a ruleset there, so
    # running it from the declaration alone would have scanned every case with a config the
    # container does not have. `from` is relative to this repository so the declaration stays
    # portable between the laptop and the VPS.
    for m in run.get("mounts") or []:
        src = m["from"]
        if not os.path.isabs(src):
            src = os.path.normpath(os.path.join(ROOT, src))
        cmd += ["-v", f"{src}:{m['to']}" + (":ro" if m.get("ro", True) else "")]
    for key, val in sorted((run.get("env") or {}).items()):
        cmd += ["-e", f"{key}={val}"]
    if run.get("entrypoint"):
        cmd += ["--entrypoint", run["entrypoint"]]
    cmd += [run["image"]]
    tokens = {"mount": mount, "out": out_mount or "", "target": mount, "tool_root": root,
              "artefact_dir": out_mount or "", "root": ROOT, **extra}
    return cmd + [_subst(a, tokens) for a in run["command"]]


def classify(spec, exit_code, combined_output, parsed, evidence_text=None):
    """(status, files_seen, reason). The one function that decides zero versus outage.

    `status` is one of:

        ok           the tool says it read the code and its output parsed. Findings may be zero,
                     and a zero here is a real zero.
        unavailable  it did not run, or did not say it ran, or said nothing this parser can read.
                     Never a zero, never in a denominator.
        unknown      the declaration admits the tool prints no coverage line at all, so the run
                     cannot be classified either way. Also never a zero.
    """
    cov = spec["coverage"]
    ev = cov["evidence"]
    if exit_code not in cov["ok_exit_codes"]:
        return "unavailable", None, f"exit {exit_code}, not in {cov['ok_exit_codes']}"
    for pattern in cov.get("failure_patterns", []):
        m = re.search(pattern, combined_output or "")
        if m:
            return "unavailable", None, m.group(0)[:200]
    if parsed is None:
        return "unavailable", None, "the tool produced no output this parser could read"
    if ev.get("absent"):
        return "unknown", None, ev["reason"]
    # The tool's own account of what it read. Usually its stdout; `evidence.source` names a file
    # instead for a tool that writes its coverage log rather than printing it.
    text = combined_output if evidence_text is None else evidence_text
    if ev.get("count") == "matches":
        seen = len(re.findall(ev["pattern"], text or ""))
        m = seen > 0
    else:
        m = re.search(ev["pattern"], text or "")
        seen = _int(m.group(1)) if m else 0
    if not m:
        return "unavailable", None, (
            f"no line matching {ev['pattern']!r} ({ev['means']}): the tool did not say it read "
            "anything, so silence here is not a measurement")
    if seen < ev.get("minimum", 1):
        return "unavailable", seen, f"the tool reports {seen} files read"
    if cov.get("success_pattern") and not re.search(cov["success_pattern"], combined_output or ""):
        return "unavailable", seen, f"no line matching {cov['success_pattern']!r}"
    return "ok", seen, ""


def _stage(spec, source_dir, work_root, leaf):
    """The directory actually handed to the tool, and how to undo the staging in a path.

    Radar refuses a target whose `Cargo.toml` sits at the root of the path it is given and exits 0
    while writing nothing, which reads as a clean zero. The layout it wants is declared rather than
    rediscovered.
    """
    if spec["layout"] == "variant-dir":
        return source_dir, ""
    dest = os.path.join(work_root, leaf.replace("/", ".") + ".pkg", "pkg")
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(source_dir, dest)
    return os.path.dirname(dest), "pkg/"


def _rewrite(path, mount, staged_prefix, path_prefix):
    """A container path back onto the corpus path the scorers use. Prefix only; nothing else."""
    p = str(path).replace("\\", "/")
    mount = str(mount).replace("\\", "/").rstrip("/")
    rel = p[len(mount) + 1:] if p.startswith(mount + "/") else p.lstrip("/")
    if staged_prefix and rel.startswith(staged_prefix):
        rel = rel[len(staged_prefix):]
    return f"{path_prefix.rstrip('/')}/{rel}"


def run_leaf(spec, leaf, source_dir, path_prefix, artefact_root, tag="", tool_root=None,
             args=None):
    """One invocation. Returns (log_entry, findings). Writes the artefact before it returns.

    The artefact is written whatever happens, including on a crash and on a timeout, because the
    run that failed is the one somebody will want to read.
    """
    # Absolute from here down, and this is not tidiness. `wrapped-pkg` hands the tool a directory
    # under `<artefact_root>/_staged`, and `_rewrite` strips that directory off the paths the tool
    # reports by prefix. A tool reports absolute paths; a relative `--artefacts` made the prefix
    # relative, no path matched, and every finding in a 34-invocation radar run came back as
    # `corpus2/<case>/<variant>/root/st-fw-.../_staged/...`. Nothing crashed. `score2` refused to
    # score a path that is not on disk and returned `unknown` for three cases, which is the only
    # reason this was noticed rather than published.
    artefact_root = os.path.abspath(artefact_root)
    source_dir = os.path.abspath(source_dir)
    artefact_dir = os.path.join(artefact_root, leaf.replace("/", ".") + tag)
    os.makedirs(artefact_dir, exist_ok=True)
    work_root = os.path.join(artefact_root, "_staged")
    os.makedirs(work_root, exist_ok=True)
    target, staged_prefix = _stage(spec, source_dir, work_root, leaf)
    cmd = command_for(spec, target, artefact_dir, tool_root, args)

    started = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=spec["run"]["timeout_seconds"])
        rc, stdout, stderr = proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        rc, stdout, stderr = -9, "", f"TIMEOUT after {spec['run']['timeout_seconds']}s"
    except OSError as exc:
        rc, stdout, stderr = -1, "", f"could not invoke: {exc!r}"
    wall = round(time.time() - started, 2)

    combined = stdout + ("\n" + stderr if stderr else "")
    stdout_path = os.path.join(artefact_dir, "stdout.log")
    with open(stdout_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("COMMAND: " + " ".join(cmd) + "\n")
        fh.write(f"EXIT: {rc}\nWALL_SECONDS: {wall}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}\n")

    fmt = spec["output"]["format"]
    raw_text, blob = None, None
    if spec["output"]["from"] == "stdout":
        raw_text = stdout
    else:
        candidate = os.path.join(artefact_dir, spec["output"]["name"])
        if os.path.exists(candidate):
            with open(candidate, encoding="utf-8", errors="replace") as fh:
                raw_text = fh.read()
    parsed = None
    if raw_text is not None:
        if fmt == "text-regex":
            parsed = parse_text_regex(raw_text, spec["output"]["patterns"])
        else:
            try:
                blob = json.loads(raw_text) if raw_text.strip() else None
            except ValueError:
                blob = None
            # An empty output file is a parseable nothing for a tool that writes one only when it
            # has findings; `no_output_means_empty` says which kind of tool this is, and it is a
            # property of the tool, not a default. radar writes no file at all on a clean zero.
            if blob is None and raw_text.strip():
                parsed = None
            elif blob is None:
                parsed = [] if spec["output"].get("no_output_means_empty") else None
            else:
                parsed = PARSERS[fmt](blob)
    elif spec["output"].get("no_output_means_empty"):
        parsed = []

    ev_source = (spec["coverage"].get("evidence") or {}).get("source")
    evidence_text = None
    if ev_source:
        ev_path = os.path.join(artefact_dir, ev_source)
        if os.path.exists(ev_path):
            with open(ev_path, encoding="utf-8", errors="replace") as fh:
                evidence_text = fh.read()
        else:
            evidence_text = ""
    status, seen, reason = classify(spec, rc, combined, parsed, evidence_text)
    findings = []
    if status == "ok":
        mount = spec["run"].get("mount", "/src") if spec["run"]["engine"] == "docker" else target
        # semgrep prefixes a rule id with `rules.` when its config is a local file and does not
        # when the same ruleset is loaded by URL, and the mapping pre-registered before the run
        # holds the URL form. Stripping it is envelope normalisation, declared once and applied
        # to every id alike; it is not a rename to make anything match, and the declaration that
        # asks for it has to say so in `rule_id_note`. Without this the first framework run of
        # semgrep-solana-standard turned three `unlocated` verdicts into `missed` while the tool,
        # the ruleset and the corpus were all byte-identical to the run that published them.
        strip = spec["output"].get("rule_id_strip_prefix")
        for f in parsed or []:
            rid = f["rule_id"]
            if strip and rid.startswith(strip):
                rid = rid[len(strip):]
            findings.append({**f, "rule_id": rid,
                             "file": _rewrite(f["file"], mount, staged_prefix, path_prefix)})

    try:
        artefact = os.path.relpath(stdout_path, ROOT)
    except ValueError:
        # A path on another Windows drive has no relative form from the repository root.
        artefact = stdout_path
    entry = {"leaf": leaf, "status": status, "exit_code": rc, "wall_seconds": wall,
             "files_seen": seen, "findings": len(findings) if status == "ok" else None,
             "command": " ".join(cmd), "artefact": artefact.replace("\\", "/")}
    if reason:
        entry["reason"] = reason
    return entry, findings
