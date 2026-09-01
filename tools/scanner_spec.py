#!/usr/bin/env python3
"""Adapters as declarations rather than as scripts.

Adding a scanner to this benchmark has cost roughly an evening every time it has been done, and
almost none of that evening went on the scanner. Two agents each added one on 2026-09-01 and their
reports say where the time went: writing, for the fifth and sixth time, a per-case runner that
iterates the corpus, invokes a container, captures stdout, decides whether the run happened,
writes an artefact, writes a log line, rewrites container paths onto corpus paths and aggregates a
findings file. `run_solsec.py` and `run_semgrep.py` are the same 120 lines twice, and the two
differ in exactly four places: the image, the argv, the regex that reads the tool's own "I read N
files" line, and the shape of its output.

Those four places are what a declaration holds. Everything else is here, once.

    adapters/<tool>.json   what is different about this tool
    tools/scanner_spec.py  what is the same about all of them

**What comes for free, and why each one is not optional.**

*One artefact and one log line per invocation.* `run_leaf` writes the tool's complete stdout and
stderr unedited, and a log entry carrying the exact command, the exit code and the wall time.
Errors 20 and 21: two published numbers were extrapolated from one case each because a findings
file was the only record, and a findings file cannot tell "ran and found nothing" from "never
ran".

*Unavailability classified, not inferred.* A declaration MUST say how the tool announces that it
read the code - `solsec` prints `Found N Rust files to analyze`, `radar` prints `Scanned N file`,
`sol-azy` prints `N files scanned` - and `validate` refuses a declaration that does not. Without
that line the run is `unavailable`, never a zero, and a tool that has no such line at all must say
so explicitly, in which case its runs are `unknown` and can never become zeros by default. Error
35 read silence as a measurement (`solsec: 0 / 6, 3 unavailable`, all of it inferred from an empty
file) and error 36 read a measurement as silence (a clean radar zero published as "could not
run"). Both on the same day, in opposite directions.

*A determinism check.* `--repeat 2` runs every leaf twice and compares findings by rule, path,
line and column. The verdict is written beside the findings file. A tool that disagrees with
itself is reported as `non-deterministic` with the differing leaves named; nothing is averaged and
neither run is discarded.

*A positive control that crosses the parser.* Every declaration carries a sample of the tool's own
output with one real finding in it. `positive_control` plants that finding at the fix site of a
synthetic case, parses it with this tool's parser, writes it in this tool's stored envelope, reads
it back with the same `score2.load_findings` that reads the committed files, and asserts the
scorer says `detected`. On 2026-09-01 an external review disabled one branch of `load_findings`
and every check in the repository stayed green while every corpus-2 verdict silently became
`missed`. A parser can break in one branch only, so the control runs per declaration.

Usage:

    python tools/scanner_spec.py --list                 what is declared, and what it feeds
    python tools/scanner_spec.py --self-check           positive control, every declaration
    python tools/scanner_spec.py --demo                 self-check of this module
    python tools/scanner_spec.py --run solsec --corpus corpus2 --out raw/c2-solsec.json
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ADAPTERS_DIR = os.path.join(ROOT, "adapters")
if HERE not in sys.path:
    sys.path.insert(0, HERE)


# --------------------------------------------------------------------------- parsers
# One entry per output shape this project has met. The name is the same token `run_all.py` and
# `score2.load_findings` already use as `kind`, so a declaration cannot name a parser for its
# stored file that the scorer does not have. `test_all.py` asserts that correspondence.

def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_radar(blob):
    """[{name, locations: ["path:line:col-col", ...]}] - radar and X-Ray share this envelope."""
    out = []
    for item in blob or []:
        for loc in item.get("locations") or []:
            parts = str(loc).split(":")
            out.append({"rule_id": item.get("name", ""), "file": parts[0],
                        "line": _int(parts[1] if len(parts) > 1 else 0),
                        "col": _int(parts[2].split("-")[0] if len(parts) > 2 else 0)})
    return out


def parse_sol_audit(blob):
    """{"findings": [{rule_id, file, line}]} - sol-audit's and vaultlint's shape."""
    items = blob.get("findings") if isinstance(blob, dict) else blob
    return [{"rule_id": x.get("rule_id", ""), "file": x.get("file", ""),
             "line": _int(x.get("line")), "col": _int(x.get("col"))} for x in items or []]


def parse_semgrep(blob):
    """{"results": [{check_id, path, start: {line}}]}."""
    items = blob.get("results") if isinstance(blob, dict) else blob
    return [{"rule_id": r.get("check_id", ""), "file": r.get("path", ""),
             "line": _int((r.get("start") or {}).get("line")),
             "col": _int((r.get("start") or {}).get("col"))} for r in items or []]


def parse_solsec(blob):
    """{"analysis_results": [{rule_name, file_path, line_number}]}."""
    items = blob.get("analysis_results") if isinstance(blob, dict) else blob
    out = []
    for x in items or []:
        fp = str(x.get("file_path", ""))
        out.append({"rule_id": x.get("rule_name", ""), "file": fp[2:] if fp.startswith("./") else fp,
                    "line": _int(x.get("line_number")), "col": _int(x.get("column"))})
    return out


def parse_text_regex(text, patterns):
    """Human-readable diagnostics, the shape rustc-family and Starlark-rule tools emit.

    Two regexes and a scope rule, because sol-azy prints a summary table before the detail and a
    parser that reads both counts every finding twice:

        rule      matched against each line; the last match becomes the rule in force
        location  `path:line[:col]`, attributed to the rule in force
        begin_at  optional: ignore everything before this marker (sol-azy's "Detailed findings:")
    """
    rule_re = re.compile(patterns["rule"])
    loc_re = re.compile(patterns["location"])
    begin = patterns.get("begin_at")
    started = begin is None
    current, out = None, []
    for line in (text or "").splitlines():
        if not started:
            started = begin in line
            continue
        m = rule_re.search(line)
        if m:
            current = m.group(1).strip()
            continue
        m = loc_re.search(line.strip())
        if m and current is not None:
            out.append({"rule_id": current, "file": m.group(1), "line": _int(m.group(2)),
                        "col": _int(m.group(3)) if m.lastindex and m.lastindex >= 3 else 0})
    return out


PARSERS = {
    "radar": parse_radar,
    "xray": parse_radar,
    "sol-audit": parse_sol_audit,
    "vaultlint": parse_sol_audit,
    "semgrep": parse_semgrep,
    "solsec": parse_solsec,
    "text-regex": parse_text_regex,
}

# How to write findings back out in a tool's own envelope. `text-regex` has no writer: a tool that
# speaks prose is stored in the flat `sol-audit` envelope, which is what every text tool measured
# here has done, and the declaration says so rather than leaving it to be guessed.
WRITERS = {
    "radar": lambda fs: [{"name": f["rule_id"], "description": "", "severity": "", "certainty": "",
                          "locations": [f"{f['file']}:{f['line']}:{f['col']}"]} for f in fs],
    "xray": lambda fs: [{"name": f["rule_id"], "rule_name": f["rule_id"],
                         "locations": [f"{f['file']}:{f['line']}:{f['col']}"]} for f in fs],
    "sol-audit": lambda fs: {"findings": [{"rule_id": f["rule_id"], "file": f["file"],
                                           "line": f["line"], "col": f["col"]} for f in fs]},
    "vaultlint": lambda fs: {"findings": [{"rule_id": f["rule_id"], "file": f["file"],
                                           "line": f["line"], "col": f["col"]} for f in fs]},
    "semgrep": lambda fs: {"results": [{"check_id": f["rule_id"], "path": f["file"],
                                        "start": {"line": f["line"]},
                                        "end": {"line": f["line"]}} for f in fs]},
    "solsec": lambda fs: {"analysis_results": [{"rule_name": f["rule_id"], "file_path": f["file"],
                                                "line_number": f["line"],
                                                "column": f["col"]} for f in fs]},
}


# --------------------------------------------------------------------------- validation

REQUIRED_TOP = ("name", "provenance", "run", "layout", "coverage", "output", "envelope",
                "positive_control", "measurements")
LAYOUTS = ("variant-dir", "wrapped-pkg")


def _problems(spec):
    """Every reason this declaration cannot be trusted, not just the first."""
    bad = []
    for key in REQUIRED_TOP:
        if key not in spec:
            bad.append(f"missing {key!r}")
    if bad:
        return bad

    prov = spec["provenance"]
    for key in ("repository", "install", "install_documented_at", "checked_on"):
        if not prov.get(key):
            bad.append(
                f"provenance.{key} is empty. `cargo install radar` nearly installed an unrelated "
                "2021 crate by a different author; the install path has to be the one the tool's "
                "own repository documents, and the declaration has to say where that was read")

    run = spec["run"]
    if run.get("engine") not in ("docker", "local", "unrecorded"):
        bad.append("run.engine must be 'docker', 'local' or 'unrecorded'")
    if run.get("engine") == "docker" and not run.get("image"):
        bad.append("run.engine is docker but no run.image is named")
    if run.get("engine") == "unrecorded":
        # A row whose invocation nobody wrote down. It can still be read, scored and checked; it
        # cannot be reproduced, and the declaration says so out loud instead of implying it could.
        # Three of this project's published rows are in this state, all from 2026-08-31.
        if not run.get("reason"):
            bad.append("run.engine is 'unrecorded' and no reason says why the command is not known")
        if not run.get("invocation_evidence"):
            bad.append("run.invocation_evidence must name what IS known about how this ran, even "
                       "if that is only the image, so the gap is a stated fact and not a silence")
    else:
        if not run.get("command"):
            bad.append("run.command is empty: nothing would be invoked")
        if not run.get("timeout_seconds"):
            bad.append("run.timeout_seconds is unset: a hung run would look like a clean zero")
        if not run.get("invocation_evidence"):
            bad.append("run.invocation_evidence must say where this command was read from - an "
                       "artefact in raw/, the tool's --help, or the report that ran it. A command "
                       "typed from memory is the same class of claim as a number typed from memory")
        if spec["layout"] not in LAYOUTS:
            bad.append(f"layout must be one of {LAYOUTS}; radar needs 'wrapped-pkg' because it "
                       "refuses a target whose Cargo.toml sits at the root of the path it is given")
        for i, m in enumerate(run.get("mounts") or []):
            if not m.get("from") or not m.get("to"):
                bad.append(f"run.mounts[{i}] needs 'from' (a path in this repository) and 'to'")
                continue
            src = m["from"]
            if not os.path.isabs(src):
                src = os.path.normpath(os.path.join(ROOT, src))
            if not os.path.exists(src):
                # Docker creates an empty directory for a bind mount whose source is missing, so
                # a wrong path here does not fail: it silently scans the corpus with no ruleset
                # and every case comes back clean. Refused at load time instead.
                bad.append(f"run.mounts[{i}] names {m['from']!r}, which is not in this repository. "
                           "Docker would create an empty directory there and the run would look "
                           "like a clean zero.")

    cov = spec["coverage"]
    if run.get("engine") == "unrecorded":
        cov = dict(cov or {})
        cov.setdefault("ok_exit_codes", [0])
        cov.setdefault("evidence", {"absent": True, "reason": run.get("reason", "unrecorded")})
    if not cov.get("ok_exit_codes"):
        bad.append("coverage.ok_exit_codes is unset: semgrep exits 1 when it has findings, so "
                   "'exit 0' is not a portable definition of a run that happened")
    ev = cov.get("evidence")
    if not isinstance(ev, dict):
        bad.append(
            "coverage.evidence is missing. It must say how THIS tool announces that it read the "
            "code, so a silent run can be told from an empty one. Error 35 published a "
            "denominator of six and three unavailable cases, all inferred from an empty findings "
            "file, and none of them existed. If the tool prints no such line, say so explicitly "
            'with {"absent": true, "reason": "..."} and every run will be recorded `unknown` '
            "rather than becoming a zero.")
    elif ev.get("absent"):
        if not ev.get("reason"):
            bad.append("coverage.evidence.absent needs a written reason")
    else:
        if ev.get("count") not in (None, "group", "matches"):
            bad.append("coverage.evidence.count must be 'group' (the pattern captures the number, "
                       "the default) or 'matches' (the number is how many times it matches)")
        if not ev.get("pattern"):
            bad.append("coverage.evidence.pattern is empty")
        else:
            try:
                if re.compile(ev["pattern"]).groups < 1 and ev.get("count") != "matches":
                    bad.append("coverage.evidence.pattern must capture the file count in group 1, "
                               "or declare count='matches'")
            except re.error as exc:
                bad.append(f"coverage.evidence.pattern does not compile: {exc}")
        if not ev.get("means"):
            bad.append("coverage.evidence.means must say in words what the pattern is counting, "
                       "so the next reader can check it against the tool rather than trust it")

    out = spec["output"]
    if run.get("engine") != "unrecorded":
        if out.get("from") not in ("stdout", "file"):
            bad.append("output.from must be 'stdout' or 'file'")
        if out.get("from") == "file" and not out.get("name"):
            bad.append("output.from is 'file' but output.name does not say which file")
    if out.get("rule_id_strip_prefix") and not spec.get("rule_id_note"):
        bad.append("output.rule_id_strip_prefix rewrites every rule id this tool emits, so the "
                   "declaration must carry a `rule_id_note` saying why the tool emits two forms "
                   "of the same id and where both were observed. A silent rewrite is how a "
                   "mapping gets fitted to a result.")
    fmt = out.get("format")
    if fmt not in PARSERS:
        bad.append(f"output.format {fmt!r} is not a parser this project has: {sorted(PARSERS)}")
    elif fmt == "text-regex":
        pats = out.get("patterns") or {}
        for key in ("rule", "location"):
            if not pats.get(key):
                bad.append(f"output.format is text-regex but output.patterns.{key} is missing")

    if spec["envelope"] not in WRITERS:
        bad.append(f"envelope {spec['envelope']!r} is not a stored shape the scorer reads: "
                   f"{sorted(WRITERS)}")

    pc = spec["positive_control"]
    if not pc.get("rule_id") or "sample" not in pc:
        bad.append(
            "positive_control needs a rule_id and a sample of the tool's OWN output holding one "
            "finding, with {path} and {line} where the location goes. Without it a parser that "
            "silently returns nothing is indistinguishable from a tool that found nothing, which "
            "is how a disabled branch of load_findings kept 94 checks green while turning every "
            "corpus-2 verdict into a miss.")

    for i, m in enumerate(spec["measurements"]):
        for key in ("row", "corpus", "raw", "mapping"):
            if not m.get(key):
                bad.append(f"measurements[{i}] is missing {key!r}")
        if m.get("envelope", spec["envelope"]) not in WRITERS:
            bad.append(f"measurements[{i}] names envelope {m['envelope']!r}, which no scorer reads")
    return bad


def validate(spec):
    bad = _problems(spec)
    if bad:
        raise ValueError(f"{spec.get('name', '<unnamed>')}: " + "; ".join(bad))
    return spec


def load(path_or_dict):
    if isinstance(path_or_dict, dict):
        return validate(dict(path_or_dict))
    with open(path_or_dict, encoding="utf-8") as fh:
        return validate(json.load(fh))


def load_all(adapters_dir=None):
    """Every declaration, by name. Order is the filename order so output is stable."""
    d = adapters_dir or ADAPTERS_DIR
    out = {}
    for path in sorted(glob.glob(os.path.join(d, "*.json"))):
        if os.path.basename(path) == "corpora.json":
            continue
        spec = load(path)
        if spec["name"] in out:
            raise ValueError(f"two declarations claim the name {spec['name']!r}")
        out[spec["name"]] = spec
    return out


# --------------------------------------------------------------------------- the clock tables
# `run_all.py` used to carry these as three literals maintained by hand. They are derived from the
# declarations instead, so a tool that has been declared appears on the clock without a second
# edit, and a row that exists on the clock has a declaration behind it saying where the tool came
# from and how its output is read. `test_all.py` pins the derived tables against the values the
# literals held, so this refactor cannot move a published row without the suite saying which one.

def clock_tables(adapters_dir=None):
    """(SOURCES, SOURCES_CORPUS2, MAPPING_ALIAS, NOTES) as run_all consumes them."""
    c1, c2, alias, notes = {}, {}, {}, {}
    for spec in load_all(adapters_dir).values():
        for m in spec["measurements"]:
            if not m.get("on_clock", True):
                continue
            row, envelope = m["row"], m.get("envelope", spec["envelope"])
            table = c1 if m["corpus"] == "corpus1" else c2
            if row in table:
                raise ValueError(f"two declarations claim the clock row {row!r} on {m['corpus']}")
            table[row] = (m["raw"], envelope)
            if m["mapping"] != row:
                alias[row] = m["mapping"]
            notes[(m["corpus"], row)] = m.get("note", "")
    return c1, c2, alias, notes


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


# --------------------------------------------------------------------------- corpora

def corpus_leaves(corpus, root=None, manifest=None, path_prefix=None, variants=None):
    """(leaf, directory, path_prefix) per case per variant, read from disk and the manifest.

    The corpus-2 case count is read from the manifest on every call and never written down. It was
    9, then 16, then 17, and it changed under a measurement once already: B3's sweep started
    against 9 built cases and finished against 17, and only a digest taken before the run caught
    it. A framework that hard-codes the number would publish the drift as a result.
    """
    if corpus == "corpus2":
        root = root or os.path.join(ROOT, "corpus2")
        manifest = manifest or os.path.join(root, "manifest.json")
        path_prefix = path_prefix or "corpus2"
        variants = variants or ("insecure", "secure")
        with open(manifest, encoding="utf-8") as fh:
            cases = json.load(fh)["cases"]
        out = []
        for case in cases:
            if not case.get("valid", True):
                continue
            for variant in variants:
                d = os.path.join(root, case["name"], variant)
                if os.path.isdir(d):
                    out.append((f"{case['name']}/{variant}", d,
                                f"{path_prefix}/{case['name']}/{variant}"))
        return out

    # Corpus 1 is not committed here; it is fetched at its pinned commit and its classes are the
    # directories under programs/. Same rule: enumerate, never assume - and that means the
    # variants too. `9-closing-accounts` ships five (`insecure-still` and `insecure-still-still`
    # as well as the usual three), so a hard-coded triple recorded 33 invocations where the runs
    # already published record 35, and the two directories it skipped left no trace of having
    # been skipped. `score.variant_of` ignores those two either way, which is exactly why a
    # run log has to say the corpus has them rather than quietly agreeing with the scorer.
    if not root:
        raise ValueError("corpus1 is not in this repository; pass --corpus-root to the checkout")
    path_prefix = path_prefix or "/tmp/sealevel-attacks/programs"
    out = []
    for cls in sorted(os.listdir(root)):
        if not os.path.isdir(os.path.join(root, cls)):
            continue
        for variant in sorted(os.listdir(os.path.join(root, cls))):
            if variants and variant not in variants:
                continue
            d = os.path.join(root, cls, variant)
            if os.path.isdir(os.path.join(d, "src")):
                out.append((f"{cls}/{variant}", d, f"{path_prefix}/{cls}/{variant}"))
    return out


# --------------------------------------------------------------------------- a whole measurement

def _key(f):
    return (f["rule_id"], f["file"].replace("\\", "/"), f["line"], f["col"])


def run_measurement(spec, leaves, out_path, artefact_root, repeat=1, echo=True,
                    tool_root=None, args=None):
    """Every leaf, `repeat` times. Writes the findings file, the run log and the determinism note.

    Nothing here averages, merges or drops a pass. Pass 1 is the measurement; passes after it exist
    only to answer whether the tool says the same thing twice, and their findings are written to
    their own file so both remain readable.
    """
    os.makedirs(artefact_root, exist_ok=True)
    passes = []
    for n in range(1, max(1, repeat) + 1):
        tag = "" if n == 1 else f".run{n}"
        log, findings, per_leaf = [], [], {}
        for leaf, source, prefix in leaves:
            entry, got = run_leaf(spec, leaf, source, prefix, artefact_root, tag,
                                  tool_root, args)
            log.append(entry)
            findings.extend(got)
            per_leaf[leaf] = {_key(f) for f in got}
            if echo:
                print(f"  {entry['status']:12} {leaf:52} exit={entry['exit_code']} "
                      f"files={entry['files_seen']} {entry['wall_seconds']}s "
                      f"{entry.get('reason', '')}".rstrip())
        passes.append((tag, log, findings, per_leaf))

    envelope = spec["envelope"]
    for tag, log, findings, _per_leaf in passes:
        dest = out_path if not tag else out_path.replace(".json", tag + ".json")
        with open(dest, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(WRITERS[envelope](findings), fh, indent=1)
            fh.write("\n")
        with open(dest + ".log", "w", encoding="utf-8", newline="\n") as fh:
            json.dump(log, fh, indent=1)
            fh.write("\n")

    verdict = determinism(passes)
    with open(out_path + ".determinism.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(verdict, fh, indent=1)
        fh.write("\n")
    return passes[0][1], passes[0][2], verdict


def determinism(passes):
    """Same input twice, same findings? Reported, never averaged and never quietly resolved."""
    if len(passes) < 2:
        return {"runs": len(passes), "verdict": "not-checked",
                "reason": "run with --repeat 2 or more to answer this"}
    base = passes[0][3]
    differing = []
    for entry in passes[1:]:
        other = entry[3]
        for leaf in sorted(set(base) | set(other)):
            if base.get(leaf, set()) != other.get(leaf, set()):
                differing.append({"pass": entry[0] or ".run1", "leaf": leaf,
                                  "only_in_first": sorted(base.get(leaf, set())
                                                          - other.get(leaf, set()))[:5],
                                  "only_in_later": sorted(other.get(leaf, set())
                                                          - base.get(leaf, set()))[:5]})
    total = sum(len(p[1]) for p in passes)
    return {"runs": len(passes), "invocations": total,
            "verdict": "deterministic" if not differing else "non-deterministic",
            "differing": differing,
            "note": ("every pass produced the same findings by rule, file, line and column"
                     if not differing else
                     "this tool does not agree with itself; its score is a sample, not a value, "
                     "and it is reported as non-deterministic rather than averaged")}


# --------------------------------------------------------------------------- positive control

VULN = "use anchor_lang::prelude::*;\npub fn go() {\n    let x = read();\n}\n"
FIXED = "use anchor_lang::prelude::*;\npub fn go() {\n    require_owner();\n    let x = read();\n}\n"
CONTROL_CLASS = "account-data-matching"


def _synthetic_case(tmp):
    """A vulnerable/fixed pair whose fix inserts a guard at line 3, as score2.demo builds one."""
    case = os.path.join(tmp, "case")
    for variant, text in (("insecure", VULN), ("secure", FIXED)):
        sub = os.path.join(case, variant, "src")
        os.makedirs(sub)
        with open(os.path.join(sub, "lib.rs"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return case


def _fill(sample, path, line):
    if isinstance(sample, str):
        return sample.replace("{path}", path).replace("{line}", str(line))
    if isinstance(sample, list):
        return [_fill(x, path, line) for x in sample]
    if isinstance(sample, dict):
        return {k: _fill(v, path, line) for k, v in sample.items()}
    return sample


def _corpus1_control(spec, parsed, envelope, rule):
    """The same proof for a corpus-1 row, which is read and scored by different code.

    `score2` never sees a corpus-1 measurement: `run_all.extract` reads the file and `score.score`
    scores it. A control that only crossed the corpus-2 path would leave X-Ray, whose only row is
    on corpus 1, with no proof its parser can say yes at all.
    """
    import run_all
    import score
    name = spec["name"]
    findings = [{**f, "file": f"/c/1-{CONTROL_CLASS}/{'insecure' if i == 0 else 'secure'}/lib.rs"}
                for i, f in enumerate(parsed)]
    blob = WRITERS[envelope](findings[:1])
    pairs = run_all.extract(envelope, blob)
    assert pairs, f"{name}: run_all.extract({envelope!r}) read a one-finding file into nothing"
    rows = score.score(pairs, {f"1-{CONTROL_CLASS}": [rule]})
    got = {r[0]: (r[4], r[5]) for r in rows}
    assert got[f"1-{CONTROL_CLASS}"] == (True, True), (
        f"{name}: a finding on the vulnerable variant only scored {got}, not nominal and real")
    on_both = WRITERS[envelope]([findings[0],
                                 {**findings[0],
                                  "file": findings[0]["file"].replace("/insecure/", "/secure/")}])
    rows = score.score(run_all.extract(envelope, on_both), {f"1-{CONTROL_CLASS}": [rule]})
    got = {r[0]: (r[4], r[5]) for r in rows}
    assert got[f"1-{CONTROL_CLASS}"] == (True, False), (
        f"{name}: firing on the fixed variant too still scored real recall: {got}")


def positive_control(spec):
    """Plant one real finding at a fix site and prove this declaration can carry it to `detected`.

    It crosses everything between a scanner's mouth and a published verdict: this tool's parser,
    this tool's stored envelope, `score2.load_findings`, and `score2.score_case`. Then it plants
    the same finding on the fixed variant too and requires that the answer stops being `detected`,
    because a parser that loses the variant would turn every false positive into a detection.

    A declaration with corpus-1 rows additionally crosses `run_all.extract` and `score.score`,
    which is the other reader entirely.

    Returns a dict; raises AssertionError with the tool named if it cannot say yes.
    """
    import score2
    name, fmt, envelope = spec["name"], spec["output"]["format"], spec["envelope"]
    rule = spec["positive_control"]["rule_id"]
    mapping = {"1-" + CONTROL_CLASS: [rule]}
    rows = spec["measurements"] or [{"corpus": "corpus2", "envelope": envelope}]
    # Which readers do this declaration's rows actually go through? A control that crossed only
    # the corpus-2 path would leave X-Ray, whose only row is on corpus 1, with no proof at all,
    # and it would miss that vaultlint's two rows are stored in two different envelopes.
    c2_envelopes = sorted({r.get("envelope", envelope) for r in rows if r["corpus"] == "corpus2"})
    c1_envelopes = sorted({r.get("envelope", envelope) for r in rows if r["corpus"] == "corpus1"})

    with tempfile.TemporaryDirectory() as tmp:
        case = _synthetic_case(tmp)
        # Relative to the case's parent, which is what a scanner emits once the container prefix
        # has been rewritten off, and what `score2.resolve_in_case` resolves against. It also has
        # to be relative for a reason worth writing down: radar's envelope packs the location into
        # `path:line:col` and splits it on the colon, so a Windows absolute path with a drive
        # letter cannot survive that envelope at all. Every path this project stores is relative,
        # so this never bites in practice; an absolute one would fail the control on Windows for a
        # reason that has nothing to do with the parser under test.
        ins = "case/insecure/src/lib.rs"

        sample = _fill(spec["positive_control"]["sample"], ins, 3)
        parsed = (parse_text_regex(sample, spec["output"]["patterns"]) if fmt == "text-regex"
                  else PARSERS[fmt](sample))
        assert parsed, (
            f"{name}: its own positive-control sample parsed to nothing. The parser, not the "
            "scanner, decides every zero this declaration will ever produce.")
        assert any(f["rule_id"] == rule for f in parsed), (
            f"{name}: the sample parsed, but not to the rule id {rule!r} it declares: "
            f"{sorted({f['rule_id'] for f in parsed})}")

        for env in c2_envelopes:
            stored = os.path.join(tmp, f"stored-{env}.json")
            with open(stored, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(WRITERS[env](parsed), fh)
            found = score2.load_findings(env, stored)
            assert found, f"{name}: the {env} envelope wrote a file score2 parses into nothing"
            verdict, info = score2.score_case(case, CONTROL_CLASS, mapping, found)
            assert verdict == "detected", (
                f"{name} ({env}): a real finding at the fix site scored {verdict!r} "
                f"({info.get('reason', '')}). A silent parse regression would look exactly like a "
                "clean zero.")

            on_fix = [{**f, "file": f["file"].replace("/insecure/", "/secure/")} for f in parsed]
            both = os.path.join(tmp, f"both-{env}.json")
            with open(both, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(WRITERS[env](parsed + on_fix), fh)
            verdict2, _ = score2.score_case(case, CONTROL_CLASS, mapping,
                                            score2.load_findings(env, both))
            assert verdict2 != "detected", (
                f"{name} ({env}): the same rule firing on the FIXED variant too still scored "
                "`detected`. That is the whole difference between real recall and shape matching.")

            empty = os.path.join(tmp, f"empty-{env}.json")
            with open(empty, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(WRITERS[env]([]), fh)
            verdict3, _ = score2.score_case(case, CONTROL_CLASS, mapping,
                                            score2.load_findings(env, empty))
            assert verdict3 == "missed", f"{name} ({env}): an empty file scored {verdict3!r}"

    for env in c1_envelopes:
        _corpus1_control(spec, parsed, env, rule)

    return {"scanner": name, "format": fmt, "envelope": envelope, "rule_id": rule,
            "corpus1_envelopes": c1_envelopes, "corpus2_envelopes": c2_envelopes,
            "detected": True, "silent_on_the_fix": True}


# --------------------------------------------------------------------------- self-check

def demo():
    """The properties that would let a defect here publish a wrong number."""
    # 1. Unavailability must never collapse into a zero, in either direction.
    spec = load(_FIXTURE_SPEC)
    ok, seen, why = classify(spec, 0, "fixture scanned 3 files\n", [])
    assert ok == "ok" and seen == 3 and not why, (ok, seen, why)
    silent, seen, why = classify(spec, 0, "", [])
    assert silent == "unavailable", (
        "exit 0 with no coverage line was classified as a run that happened; that is error 35")
    assert "did not say it read anything" in why, why
    crashed, _, why = classify(spec, 3, "fixture scanned 3 files\n", [])
    assert crashed == "unavailable", "a non-zero exit was classified as a result"
    unreadable, _, why = classify(spec, 0, "fixture scanned 3 files\n", None)
    assert unreadable == "unavailable", "unparseable output was classified as a result"
    assert ok != silent, "a clean zero and an outage must not carry the same status"

    # 2. A declaration that does not say how the tool announces coverage is refused outright.
    blind = json.loads(json.dumps(_FIXTURE_SPEC))
    del blind["coverage"]["evidence"]
    try:
        load(blind)
        raise AssertionError("a declaration with no coverage evidence was accepted")
    except ValueError as exc:
        assert "coverage.evidence is missing" in str(exc), exc

    # 3. A tool that admits it prints no coverage line gets `unknown`, never `ok`.
    mute = json.loads(json.dumps(_FIXTURE_SPEC))
    mute["coverage"]["evidence"] = {"absent": True, "reason": "prints no file count"}
    status, _, why = classify(load(mute), 0, "", [])
    assert status == "unknown", status
    assert why == "prints no file count", why

    # 3b. A declared token is substituted; an undeclared one is refused rather than ignored.
    # sol-audit's broad and all rows differ from strict by this token alone. Before it existed the
    # declaration could only produce one of the three and the other two came from a script outside
    # the framework, which is the situation the framework exists to end.
    profiled = json.loads(json.dumps(_FIXTURE_SPEC))
    profiled["run"]["command"] = ["python", "{mount}", "--profile", "{profile}"]
    profiled["run"]["arg_defaults"] = {"profile": "strict"}
    spec_p = load(profiled)
    assert command_for(spec_p, "/t", "/o")[-1] == "strict", "the declared default was not used"
    assert command_for(spec_p, "/t", "/o", args={"profile": "all"})[-1] == "all"
    try:
        command_for(spec_p, "/t", "/o", args={"proflie": "all"})
        raise AssertionError("a token the declaration does not declare was accepted, which would "
                             "have run the default and filed it under the other name")
    except ValueError as exc:
        assert "does not declare" in str(exc), exc

    # 3c. A mount whose source is missing is refused at load time. Docker creates an empty
    # directory for it instead of failing, so semgrep would have scanned every case with no
    # ruleset and every case would have come back clean.
    mounted = json.loads(json.dumps(_FIXTURE_SPEC))
    mounted["run"] = {"engine": "docker", "image": "x:1", "mount": "/src",
                      "mounts": [{"from": "adapters/radar.json", "to": "/rules/r.json"}],
                      "command": ["scan", "{mount}"], "timeout_seconds": 60,
                      "invocation_evidence": "tools/scanner_spec.py demo"}
    argv = command_for(load(mounted), "relative/target", "relative/out")
    assert any(a.endswith("adapters" + os.sep + "radar.json:/rules/r.json:ro")
               or a.endswith("adapters/radar.json:/rules/r.json:ro") for a in argv), argv
    # Every bind source docker is given is absolute. A relative one is read as the name of a
    # named volume, not as a directory, and 34 invocations died on that before this line existed.
    for i, a in enumerate(argv):
        if a == "-v":
            assert not argv[i + 1].startswith("relative"), (
                "a relative bind source reached docker, which reads it as a volume NAME: "
                + argv[i + 1])
    mounted["run"]["mounts"] = [{"from": "adapters/does-not-exist.json", "to": "/rules/r.json"}]
    try:
        load(mounted)
        raise AssertionError("a mount naming a path that is not here was accepted; docker would "
                             "have created an empty directory and the run would look like a zero")
    except ValueError as exc:
        assert "not in this repository" in str(exc), exc

    # 3d. Corpus 1's variants are enumerated, not assumed. Two of the five directories under
    # `9-closing-accounts` are not in the usual triple, and a run log that omits them says the
    # corpus is smaller than it is.
    with tempfile.TemporaryDirectory() as tmp:
        for cls, variant in (("9-closing-accounts", "insecure"),
                             ("9-closing-accounts", "insecure-still"),
                             ("9-closing-accounts", "secure"),
                             ("0-signer-authorization", "insecure")):
            os.makedirs(os.path.join(tmp, cls, variant, "src"))
        leaves = {leaf for leaf, _d, _p in corpus_leaves("corpus1", root=tmp)}
        assert "9-closing-accounts/insecure-still" in leaves, leaves
        assert len(leaves) == 4, leaves

    # 3e. A declared rule-id prefix is stripped on the way into the envelope, and only when the
    # declaration says why. semgrep emits `rules.<id>` for a local config and `<id>` for the same
    # ruleset by URL; the mapping registered before the run holds the second form. The first
    # framework run without this turned three `unlocated` verdicts into `missed` with the tool,
    # the ruleset and the corpus all byte-identical to the run that published them.
    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "case")
        os.makedirs(target)
        with open(os.path.join(target, "__main__.py"), "w", encoding="utf-8",
                  newline="\n") as fh:
            # The coverage line goes to stderr so stdout stays parseable JSON: the same split
            # vaultlint's declaration relies on.
            fh.write('import sys\n'
                     'print("fixture scanned 1 files", file=sys.stderr)\n'
                     'print(\'{"findings": [{"rule_id": "rules.R1", "file": "src/lib.rs",'
                     ' "line": 3}]}\')\n')
        striking = json.loads(json.dumps(_FIXTURE_SPEC))
        striking["output"]["rule_id_strip_prefix"] = "rules."
        striking["rule_id_note"] = "the fixture emits both forms, as semgrep does"
        entry, got = run_leaf(load(striking), "case/insecure", target, "corpus/case/insecure",
                              os.path.join(tmp, "artefacts"))
        assert entry["status"] == "ok", entry
        assert [f["rule_id"] for f in got] == ["R1"], got
        striking["output"].pop("rule_id_strip_prefix")
        _e, got2 = run_leaf(load(striking), "case/insecure", target, "corpus/case/insecure",
                            os.path.join(tmp, "artefacts2"))
        assert [f["rule_id"] for f in got2] == ["rules.R1"], (
            "the prefix was stripped without the declaration asking for it")

    # 4. Path rewriting is a prefix operation and nothing else.
    assert _rewrite("/src/src/lib.rs", "/src", "", "corpus2/x/insecure") == \
        "corpus2/x/insecure/src/lib.rs"
    assert _rewrite("/src/pkg/src/lib.rs", "/src", "pkg/", "corpus2/x/insecure") == \
        "corpus2/x/insecure/src/lib.rs"

    # 5. Determinism is a verdict, not an average.
    def _pass(tag, line):
        f = {"rule_id": "R", "file": "corpus2/x/insecure/src/lib.rs", "line": line, "col": 0}
        return (tag, [{"leaf": "x/insecure", "status": "ok"}], [f], {"x/insecure": {_key(f)}})
    a, b, c = _pass("", 3), _pass(".run2", 3), _pass(".run2", 9)
    assert determinism([a, b])["verdict"] == "deterministic"
    bad = determinism([a, c])
    assert bad["verdict"] == "non-deterministic", bad
    assert bad["differing"], bad
    assert determinism([a])["verdict"] == "not-checked"

    # 6. Every declaration in the repository proves its parser can carry a detection.
    for name, spec in sorted(load_all().items()):
        positive_control(spec)

    # 7. The clock tables derive without collision.
    c1, c2, alias, _ = clock_tables()
    assert c1 and c2, (c1, c2)
    print("scanner_spec: OK (including the positive control for every declaration)")


# A declaration used only by the self-check and the suite. It is a real one: `run.engine` is
# `local` so the framework can be driven end to end on a laptop with no Docker, which is where
# most of this project's development happens.
_FIXTURE_SPEC = {
    "name": "fixture-scanner",
    "version": "0",
    "provenance": {"repository": "https://example.invalid/fixture",
                   "install": "none: this is a fixture, not a tool",
                   "install_documented_at": "tools/scanner_spec.py",
                   "checked_on": "2026-09-01"},
    "run": {"engine": "local", "command": ["python", "{mount}"], "timeout_seconds": 60,
            "invocation_evidence": "defined in tools/scanner_spec.py; the suite writes the script"},
    "layout": "variant-dir",
    "coverage": {"ok_exit_codes": [0],
                 "evidence": {"pattern": r"fixture scanned (\d+) files", "minimum": 1,
                              "means": "the fixture's own count of files read"}},
    "output": {"from": "stdout", "format": "sol-audit"},
    "envelope": "sol-audit",
    "positive_control": {"rule_id": "FIX-001",
                         "sample": {"findings": [{"rule_id": "FIX-001", "file": "{path}",
                                                  "line": "{line}"}]}},
    "measurements": [],
}


# --------------------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adapters", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--run", help="the declared scanner to run")
    ap.add_argument("--corpus", default="corpus2")
    ap.add_argument("--corpus-root", default=None)
    ap.add_argument("--out", help="findings file to write; the log lands beside it")
    ap.add_argument("--artefacts", default=None)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--tool-root", default=None,
                    help="where the tool itself lives, for a declaration that runs a local checkout")
    ap.add_argument("--arg", action="append", default=[], metavar="NAME=VALUE",
                    help="substitute {NAME} in run.command. Only a token the declaration lists in "
                         "run.arg_defaults is accepted, so a typo cannot leave the default in "
                         "place while the output is filed under another name. sol-audit's three "
                         "published profiles differ by exactly this one token.")
    args = ap.parse_args()
    overrides = {}
    for pair in args.arg:
        if "=" not in pair:
            print(f"--arg expects NAME=VALUE, got {pair!r}", file=sys.stderr)
            return 2
        key, val = pair.split("=", 1)
        overrides[key] = val

    if args.demo:
        demo()
        return 0

    specs = load_all(args.adapters)

    if args.list:
        print(f"{'scanner':28} {'engine':7} {'format':11} {'envelope':10} rows")
        for name, spec in sorted(specs.items()):
            rows = ", ".join(f"{m['corpus'].replace('corpus', 'c')}:{m['row']}"
                             + ("" if m.get("on_clock", True) else " (off clock)")
                             for m in spec["measurements"]) or "none"
            print(f"{name:28} {spec['run']['engine']:7} {spec['output']['format']:11} "
                  f"{spec['envelope']:10} {rows}")
        return 0

    if args.self_check:
        for name, spec in sorted(specs.items()):
            got = positive_control(spec)
            print(f"  positive control OK  {name:26} {got['format']} -> {got['envelope']}")
        print(f"\n{len(specs)} declarations, every one can carry a detection to `detected` "
              "and stays silent on the fix")
        return 0

    if args.run:
        if args.run not in specs:
            print(f"no declaration named {args.run!r}; have {sorted(specs)}", file=sys.stderr)
            return 2
        spec = specs[args.run]
        if not args.out:
            print("--out is required: the findings file and its run log go there", file=sys.stderr)
            return 2
        leaves = corpus_leaves(args.corpus, root=args.corpus_root)
        artefacts = args.artefacts or os.path.splitext(args.out)[0] + "-runs"
        print(f"{spec['name']} {spec.get('version', '')} over {len(leaves)} invocations "
              f"({args.corpus}), {args.repeat} pass(es)")
        log, findings, det = run_measurement(spec, leaves, args.out, artefacts, args.repeat,
                                            tool_root=args.tool_root, args=overrides)
        counts = {}
        for e in log:
            counts[e["status"]] = counts.get(e["status"], 0) + 1
        print(f"\n{len(log)} invocations: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
        print(f"{len(findings)} findings, determinism: {det['verdict']}")
        print(f"written: {args.out}, {args.out}.log, {args.out}.determinism.json")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
