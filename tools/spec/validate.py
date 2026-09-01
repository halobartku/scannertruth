"""Reading a declaration, refusing one that cannot be trusted, and the clock tables."""
import glob
import json
import os
import re

from . import ADAPTERS_DIR, ROOT
from .parsers import PARSERS, WRITERS


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
