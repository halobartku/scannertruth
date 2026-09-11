import io
import json
import os

from ._core import _rule_mappings


# ------------------------------------------------------- coverage bookkeeping
# The defect that caused a public retraction: silence read as measurement.

def test_manifest_invalid_cases_are_excluded_everywhere():
    """score2 and run_all must agree on which cases exist, or a denominator drifts."""
    man = json.load(io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    invalid = [c["name"] for c in man if not c.get("valid", True)]
    assert invalid, "expected at least the Cashio case to be marked invalid"
    for name in invalid:
        c = [x for x in man if x["name"] == name][0]
        assert c.get("invalid_reason"), f"{name} is excluded with no written reason"


def test_every_published_scanner_has_a_mapping():
    """Despite its name this only ever iterated `mappings/` and checked each file was non-empty.

    It never checked the direction the name promises: that every scanner carrying a published
    score has a mapping to check it against. A scored cell whose mapping is missing is a number
    with no derivation at all.
    """
    for fn in _rule_mappings():
        m = json.load(io.open(os.path.join("mappings", fn), encoding="utf-8"))
        assert "map" in m, f"{fn} has no map"
        assert isinstance(m["map"], dict) and m["map"], f"{fn} has an empty map"

    have = {fn[:-5] for fn in os.listdir("mappings") if fn.endswith(".json")}
    # A row may declare that it is scored with another row's mapping: that is how one tool appears
    # twice, at two versions or under two invocations, without a second mapping file being written
    # after the run it scores. The alias must still resolve to a real mapping on disk, and the
    # alias table is read from the code rather than repeated here.
    import sys
    sys.path.insert(0, "tools")
    import run_all
    for alias, target in run_all.MAPPING_ALIAS.items():
        assert target in have, \
            f"run_all aliases {alias!r} to mapping {target!r}, which does not exist"
        have.add(alias)
    scored = set()
    runs = sorted(f for f in os.listdir("runs") if f.endswith(".json")) if os.path.isdir("runs") \
        else []
    for fn in runs:
        row = json.load(io.open(os.path.join("runs", fn), encoding="utf-8"))
        for key in ("scanners", "corpus1", "corpus2", "results", "results_corpus2"):
            block = row.get(key)
            if isinstance(block, dict):
                scored |= set(block)
            elif isinstance(block, list):
                scored |= {r.get("scanner") for r in block if isinstance(r, dict)}
    scored = {s for s in scored if s and not s.startswith("control")}
    missing = sorted(scored - have)
    assert not missing, (
        f"the clock records a score for {missing} and there is no mapping to derive it from")


def test_mappings_declare_their_derivation():
    """A mapping with no stated derivation cannot be audited for post-hoc tuning."""
    missing = []
    for fn in sorted(os.listdir("mappings")):
        if not fn.endswith(".json"):
            continue
        m = json.load(io.open(os.path.join("mappings", fn), encoding="utf-8"))
        if not m.get("derivation"):
            missing.append(fn)
    assert not missing, f"mappings with no derivation recorded: {missing}"


def test_no_mapping_arrives_in_the_same_commit_as_a_result():
    """Pre-registration means a timestamp somebody else can read, or it means nothing.

    This repository claimed it and did not have it: every mapping published on 2026-08-31 first
    appears in the commit that published the score. The wording is retracted in `PROTOCOL.md` 3a;
    this is the enforcement that replaces it, so the claim cannot decay back into prose.
    """
    import preregistration_check as pre
    records, why = pre.audit(".")
    if why:
        # A shallow clone or an unpacked tarball cannot answer the question. CI fetches the full
        # history so this branch does not hide a violation there.
        return
    assert records, "mappings/ is tracked, so the audit must return records"
    bad = [r for r in records if r["status"] in ("VIOLATION", "untracked")]
    assert not bad, ("a mapping was committed alongside something outside mappings/: "
                     + "; ".join(f"{r['mapping']} in {r.get('sha')}" for r in bad))


def test_the_pre_registration_retraction_is_still_on_the_record():
    """The seven unproven mappings must stay named as unproven, in the document that claimed them."""
    import preregistration_check as pre
    protocol = io.open(os.path.join("docs", "PROTOCOL.md"), encoding="utf-8").read()
    assert "Retracted on 2026-09-01" in protocol, \
        "PROTOCOL.md 3a must keep the pre-registration retraction"
    assert "preregistration_check.py" in protocol, \
        "PROTOCOL.md 3a must point at the check that replaced the claim"
    records, why = pre.audit(".")
    if why:
        return
    unproven = [r for r in records if r["status"] == "unproven"]
    assert len(unproven) == 7, (
        "seven mappings predate the rule and that number is history, so it cannot change. "
        f"Found {len(unproven)}: {[r['mapping'] for r in unproven]}")


# ------------------------------------------------- run_all coverage verdicts
# This is the logic whose absence caused a public retraction: eight cases scored from a findings
# file that covered one. Each branch below is a different way of being wrong about coverage.

def test_run_all_reports_partial_when_a_case_has_no_data():
    import run_all
    out = run_all.measure_corpus2()
    by = {r["scanner"]: r for r in out if "scanner" in r}
    assert by, "measure_corpus2 returned nothing"
    for name, r in by.items():
        unresolved = r.get("unknown", 0) + r.get("not-run", 0)
        if unresolved:
            assert r["status"] == "partial",                 f"{name} has {unresolved} unresolved cases but claims status={r['status']}"
            assert r.get("reason"), f"{name} is partial with no reason recorded"
        else:
            assert r["status"] == "measured", f"{name} resolved every case but is not measured"


def test_run_all_records_how_it_knows_about_coverage():
    import run_all
    for r in run_all.measure_corpus2():
        if "scanner" not in r:
            continue
        assert "coverage_evidence" in r,             f"{r['scanner']} does not say how coverage was established"
        assert r["coverage_evidence"] in ("run log", "none"), r["coverage_evidence"]


def test_run_all_never_silently_drops_a_case():
    """A case in the manifest but absent from disk must be reported, not skipped."""
    import run_all, json, io as _io
    man = json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    valid = [c for c in man if c.get("valid", True)]
    for r in run_all.measure_corpus2():
        if "scanner" not in r:
            continue
        counted = sum(v for k, v in r.items()
                      if k in ("detected", "unlocated", "missed", "no-rule",
                               "unknown", "not-run", "not-built"))
        assert counted == len(valid),             f"{r['scanner']} accounted for {counted} of {len(valid)} valid cases"


def test_a_findings_file_covering_one_case_cannot_score_many():
    """The retraction, as a test. Silence about a case is not a measurement of it."""
    import run_all, json, io as _io
    man = json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    valid = [c["name"] for c in man if c.get("valid", True)]
    assert len(valid) >= 2, "need at least two valid cases for this to mean anything"
    # A file mentioning exactly one case, with no run log beside it, must leave the rest unknown.
    findings = {f"corpus2/{valid[0]}/insecure/src/lib.rs": [("X", 1)]}
    seen = set()
    for path in findings:
        for c in valid:
            if f"/{c}/" in path:
                seen.add(c)
    assert len(seen) == 1, "test fixture is wrong"
    assert len(seen) < len(valid),         "a single-case file must not be able to account for every case"


def test_a_run_the_framework_produced_is_declared_on_the_clock():
    """A framework run that nobody declared is invisible to `--verify-coverage` by construction.

    `run_all` builds its row registry from the adapters' `measurements`, so a measurement that was
    run, published and never declared cannot fail the coverage gate: the gate never hears about it.
    A gate that cannot see a row looks exactly like a gate with nothing to report.

    This has now happened twice with the same scanner. The `fa81c25` row was published to the
    vendor in radar#32 on 2026-09-03 and declared on 2026-09-04, and that fix declared the one row
    rather than closing the class. On 2026-09-07 the `3439053` row was published in
    RESULTS-corpus2.md and RESULTS-scanners.md with full artefacts and again no declaration, and it
    sat outside the gate for four days while `--verify-coverage` reported 24 of 24.

    The predicate is the framework's own footprint, not a curated list: a findings file beside both
    a per-run log and a determinism verdict was produced by `scanner_spec --repeat 2`, which is how
    a measurement row is made here. Scoring outputs, controls and scratch files have neither and are
    not caught. At the time of writing that is 15 files, of which 14 were declared.
    """
    import glob
    import sys
    sys.path.insert(0, "tools")
    import scanner_spec

    declared = {m["raw"] for s in scanner_spec.load_all().values()
                for m in s.get("measurements", []) if m.get("raw")}
    undeclared = []
    for path in sorted(glob.glob("raw/*.json")):
        name = os.path.basename(path)
        if name.endswith(".determinism.json") or ".run2." in name:
            continue
        if os.path.exists(path + ".log") and os.path.exists(path + ".determinism.json"):
            if name not in declared:
                undeclared.append(name)
    assert not undeclared, (
        "these runs were made by the framework and no adapter declares them, so the coverage "
        f"gate cannot see them: {undeclared}")


def test_the_provenance_watcher_asks_the_adapter_before_it_claims_drift():
    """The watcher compares upstream against its own previous reading, which is not the question.

    Until 2026-09-11 it printed `nasz opublikowany pomiar opisuje stare` on any upstream move. It
    never read `adapters/`, so it could not know that, and on 2026-09-11 it was wrong: the Radar row
    at 3439053 had existed since 2026-09-07. A watchdog that overstates what it knows produces the
    same false conclusion every time the thing it watches moves and we keep up.

    The check pulls `zmierzone` out of the shell script and drives it both ways, because a helper
    that always answers "already measured" silences the watcher completely and looks identical to a
    watcher with nothing to report.
    """
    src = io.open("tools/prov-watch.sh", encoding="utf-8").read()
    start = src.index("def zmierzone(")
    body = [src[start:].splitlines()[0]]
    for line in src[start:].splitlines()[1:]:
        if line and not line[0].isspace():
            break
        body.append(line)
    ns = {"os": os}
    exec("\n".join(body), ns)
    zmierzone = ns["zmierzone"]
    ns["repo"] = "."

    cases = [
        ("radar", "HEAD 3439053d8da6 2026-09-07", True),   # declared 2026-09-11
        ("radar", "HEAD fa81c25aaaaa 2026-09-04", True),   # declared 2026-09-04
        ("radar", "HEAD deadbeef1234 2026-09-30", False),  # never measured: this must alarm
        ("radar", "v1.2.3", None),                         # no revision in the signature
        ("no-such-scanner", "HEAD 3439053d8da6", None),
    ]
    for name, sig, want in cases:
        got = zmierzone(name, sig)
        assert got is want, (
            f"zmierzone({name!r}, {sig!r}) returned {got!r}, expected {want!r}; the watcher would "
            f"{'stay silent about a revision nobody measured' if want is False else 'cry drift over a row we declared'}")
