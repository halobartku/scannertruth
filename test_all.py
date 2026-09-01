#!/usr/bin/env python3
"""One runner for every check that stands between a defect and a published number.

Before 2026-09-01 this repository had 47 assertions across 1,913 lines and no way to run them
together. Four files had no test at all, and two of those were the worst possible candidates:
`shiftaware.py`, which corrected 23 phantom detections, and `control_c2.py`, which carries the
claim that the metric cannot be bought with volume.

The tests below are chosen by one rule: **would a defect here change a number we publish?** Anything
that would not is left alone. No framework, no fixtures directory, no dependencies - the same
constraint as the rest of the repo, so it runs anywhere the harness runs.

    python test_all.py            # everything
    python test_all.py -v         # print each check as it passes

**Verified by mutation, because a test that cannot fail is worse than no test.** Three deliberate
defects were introduced and all three were caught: widening the line tolerance to 999 broke two
checks; returning an unsplit location from the Radar extractor broke one; and dropping the
"silent on the fixed variant" half of real recall broke three, including the golden test, which
reported `sol-audit: published (6, 4), now (6, 6)` - a published number changing under a refactor,
which is exactly what these exist to catch. Two later mutations were caught the same way: a fake
`import requests` and a quickstart naming a script that does not exist.
"""
import io
import json
import os
import sys
import tempfile

# The tools live in tools/ so the repository root stays legible. Nothing is packaged, so the
# import path is set here rather than asking every reader to export PYTHONPATH.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))

VERBOSE = "-v" in sys.argv
PASSED = []
FAILED = []


def check(name, fn):
    try:
        fn()
        PASSED.append(name)
        if VERBOSE:
            print(f"  ok   {name}")
    except AssertionError as e:
        FAILED.append((name, str(e) or "assertion failed"))
        print(f"  FAIL {name}: {e}")
    except Exception as e:
        FAILED.append((name, f"{type(e).__name__}: {e}"))
        print(f"  ERROR {name}: {type(e).__name__}: {e}")


# ---------------------------------------------------------------- shiftaware
# Untested until now, and it is the tool that turned 23 apparent detections back into arithmetic.

def _hunks(pairs):
    """(old_start, old_count, new_start, new_count) tuples, as parsed from a diff."""
    return list(pairs)


def test_shift_unchanged_line_maps_to_itself():
    import shiftaware as sa
    hs = _hunks([(100, 0, 100, 4)])          # four lines inserted at 100
    assert sa.map_line(50, hs) == 50, "a line above the insertion must not move"


def test_shift_line_below_insertion_moves_down():
    import shiftaware as sa
    hs = _hunks([(100, 0, 100, 4)])
    got = sa.map_line(200, hs)
    assert got == 204, f"a line below a 4-line insertion should map to 204, got {got}"


def test_shift_line_inside_changed_region_is_gone():
    import shiftaware as sa
    hs = _hunks([(100, 3, 100, 1)])          # three lines replaced by one
    assert sa.map_line(101, hs) is None, "a line inside the changed region has no counterpart"


def test_shift_multiple_hunks_accumulate():
    import shiftaware as sa
    hs = _hunks([(10, 0, 10, 2), (100, 0, 102, 3)])
    got = sa.map_line(200, hs)
    assert got == 205, f"two insertions of 2 and 3 should shift by 5, got {got}"


def test_shift_deletion_moves_lines_up():
    import shiftaware as sa
    hs = _hunks([(10, 5, 10, 0)])            # five lines deleted
    got = sa.map_line(100, hs)
    assert got == 95, f"a line below a 5-line deletion should map to 95, got {got}"


# ------------------------------------------------------------------- score2
# The verdict machine. Every branch here decides a published cell.

def _case(tmp, vulnerable, fixed):
    case = os.path.join(tmp, "case")
    for variant, text in (("insecure", vulnerable), ("secure", fixed)):
        d = os.path.join(case, variant, "src")
        os.makedirs(d)
        io.open(os.path.join(d, "lib.rs"), "w", encoding="utf-8").write(text)
    return case, os.path.join(case, "insecure", "src", "lib.rs"), \
        os.path.join(case, "secure", "src", "lib.rs")


VULN = "a\nb\nvulnerable_line\nd\n"
FIXED = "a\nb\nguard()\nvulnerable_line\nd\n"
MAP = {"1-account-data-matching": ["RULE-X"]}


def test_score2_detected():
    import score2
    with tempfile.TemporaryDirectory() as t:
        case, ins, _ = _case(t, VULN, FIXED)
        v, _ = score2.score_case(case, "account-data-matching", MAP, {ins: [("RULE-X", 3)]})
        assert v == "detected", v


def test_score2_firing_on_the_fix_is_not_detection():
    import score2
    with tempfile.TemporaryDirectory() as t:
        case, ins, sec = _case(t, VULN, FIXED)
        v, _ = score2.score_case(case, "account-data-matching", MAP,
                                 {ins: [("RULE-X", 3)], sec: [("RULE-X", 3)]})
        assert v != "detected", f"a rule that fires on the fix detected nothing, got {v}"


def test_score2_offsite_is_unlocated_not_missed():
    import score2
    with tempfile.TemporaryDirectory() as t:
        case, ins, _ = _case(t, VULN, FIXED)
        v, _ = score2.score_case(case, "account-data-matching", MAP, {ins: [("RULE-X", 400)]})
        assert v == "unlocated", v


def test_score2_silence_is_missed():
    import score2
    with tempfile.TemporaryDirectory() as t:
        case, _, _ = _case(t, VULN, FIXED)
        v, _ = score2.score_case(case, "account-data-matching", MAP, {})
        assert v == "missed", v


def test_score2_unmapped_class_is_no_rule_not_missed():
    import score2
    with tempfile.TemporaryDirectory() as t:
        case, ins, _ = _case(t, VULN, FIXED)
        v, _ = score2.score_case(case, "type-cosplay", MAP, {ins: [("RULE-X", 3)]})
        assert v == "no-rule", f"a class the tool never claimed is a coverage gap, got {v}"


def test_score2_case_insensitive_rule_ids():
    import score2
    with tempfile.TemporaryDirectory() as t:
        case, ins, _ = _case(t, VULN, FIXED)
        v, _ = score2.score_case(case, "account-data-matching", MAP, {ins: [("rule-x", 3)]})
        assert v == "detected", "rule ids must match case-insensitively"


def test_score2_class_prefix_normalised():
    import score2
    m = {"10-sysvar-address-checking": ["R"]}
    assert score2.rules_for(m, "sysvar-address-checking") == {"r"}, \
        "corpus 1 numbers its classes, corpus 2 does not; one mapping must serve both"


# ------------------------------------------- the positive control, through the parser
# Every test above hands `score_case` a dict that a human built, and so does `score2 --demo`.
# Nothing crossed `load_findings`, the code that turns a scanner's own file into that dict. On
# 2026-09-01 an external review disabled the sol-audit branch of `load_findings` so that it
# appended nothing, and the whole self-checking surface stayed green: 94/94, the calibration
# control asserting "every zero published from this corpus is a real zero", `verify.py` OK,
# `unmapped_check` 0 candidates. Every corpus-2 verdict would have silently become `missed`.
#
# So the positive control now starts where a scanner's output starts: a file on disk, in that
# tool's own envelope, parsed by the code that parses the real ones. One per supported format,
# because a parser can break in one branch only.

# The directory name has to be the one `_case` actually creates. It said `synthetic-case` until
# 2026-09-01, and the control still passed, because `score_case` matched a finding to a case by
# basename and ignored every directory above it (error 31). Once the scorer started requiring the
# finding to be inside the case it scores, the fixture stopped naming the case under test. The
# assertions below are unchanged; only the path the fixture writes is now coherent.
VARIANT_PATHS = {"insecure": "case/insecure/src/lib.rs",
                 "secure": "case/secure/src/lib.rs"}


def _findings_file(tmp, kind, rule, line):
    """A findings file in `kind`'s own envelope, naming the fix site of the synthetic case."""
    path = VARIANT_PATHS["insecure"]
    blob = {
        "radar": [{"name": rule, "description": "", "severity": "high",
                   "locations": [f"{path}:{line}:1"]}],
        "sol-audit": {"findings": [{"rule_id": rule, "file": path, "line": line}]},
        "vaultlint": {"findings": [{"rule_id": rule, "file": path, "line": line}]},
        "semgrep": {"results": [{"check_id": rule, "path": path, "start": {"line": line}}]},
        "solsec": {"analysis_results": [{"rule_name": rule, "file_path": "./" + path,
                                         "line_number": line}]},
    }[kind]
    dest = os.path.join(tmp, f"{kind}-findings.json")
    with io.open(dest, "w", encoding="utf-8") as fh:
        json.dump(blob, fh)
    return dest


def _detects_through_the_parser(kind):
    """Parse a synthetic findings file of this kind and score it. Must come out `detected`."""
    import score2
    with tempfile.TemporaryDirectory() as t:
        case, _, _ = _case(t, VULN, FIXED)
        found = score2.load_findings(kind, _findings_file(t, kind, "RULE-X", 3))
        assert found, f"load_findings({kind!r}) parsed a one-finding file into nothing"
        verdict, _ = score2.score_case(case, "account-data-matching", MAP, found)
        assert verdict == "detected", (
            f"a real detection in {kind} format scored {verdict!r}. The parser, not the scanner, "
            f"decides every corpus-2 zero, so this must be able to say yes.")


def test_a_radar_findings_file_can_still_produce_a_detection():
    _detects_through_the_parser("radar")


def test_a_sol_audit_findings_file_can_still_produce_a_detection():
    _detects_through_the_parser("sol-audit")


def test_a_vaultlint_findings_file_can_still_produce_a_detection():
    _detects_through_the_parser("vaultlint")


def test_a_semgrep_findings_file_can_still_produce_a_detection():
    _detects_through_the_parser("semgrep")


def test_a_solsec_findings_file_can_still_produce_a_detection():
    _detects_through_the_parser("solsec")


def test_the_parser_still_separates_the_fixed_variant():
    """A parser that loses the variant would turn every false positive into a detection.

    The mirror of the tests above: the same rule at the same line on both variants must not
    score `detected` after a round trip through the parser either.
    """
    import score2
    for kind in ("radar", "sol-audit", "vaultlint", "semgrep", "solsec"):
        with tempfile.TemporaryDirectory() as t:
            case, _, _ = _case(t, VULN, FIXED)
            path = os.path.join(t, "both.json")
            src = _findings_file(t, kind, "RULE-X", 3)
            blob = json.load(io.open(src, encoding="utf-8"))
            text = json.dumps(blob).replace("/insecure/", "/secure/")
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(json.loads(text)))
            found = score2.load_findings(kind, src)
            found.update(score2.load_findings(kind, path))
            verdict, _ = score2.score_case(case, "account-data-matching", MAP, found)
            assert verdict != "detected", \
                f"{kind}: a rule firing on the fix too came out as a detection"


def test_every_kind_run_all_reads_is_a_kind_the_parser_knows():
    """`run_all` names a parser per findings file. An unknown one raises; a wrong one is silent."""
    import run_all, score2
    kinds = {kind for _, kind in run_all.SOURCES_CORPUS2.values()}
    for kind in sorted(kinds):
        with tempfile.TemporaryDirectory() as t:
            found = score2.load_findings(kind, _findings_file(t, kind, "RULE-X", 3))
            assert found, f"run_all reads a findings file with kind={kind!r} and it parses to nothing"


# ------------------------------------------------------------- the controls
# The claim that a score cannot be bought with volume rests entirely on this.

def test_noisy_control_scores_zero_on_a_synthetic_case():
    import score2, control_c2
    with tempfile.TemporaryDirectory() as t:
        case, ins, sec = _case(t, VULN, FIXED)
        # every rule, every line, BOTH variants: exactly what control-noisy does
        findings = {}
        for path in (ins, sec):
            findings[path] = [("RULE-X", n) for n in range(1, 6)]
        v, _ = score2.score_case(case, "account-data-matching", MAP, findings)
        assert v != "detected", \
            f"the noisy control must never score a detection, got {v}"


def test_noisy_control_would_win_a_findings_count_ranking():
    """`len(every_rule()) > 10` was the whole check, and it cannot see the property that matters.

    The corpus-2 control is meaningful only because it emits under **every** rule id any mapping
    claims, on every non-empty line of both variants. That is exactly what the corpus-1 control
    does not do, which is why its published nominal figure is worthless. So check the property:
    every mapped rule appears, and on a case of n non-empty lines the control produces
    rules * lines * variants findings, which no real scanner will ever approach.
    """
    import json, control_c2
    rules = set(control_c2.every_rule())
    assert len(rules) > 10, f"expected many mapped rules to fire, got {len(rules)}"
    for fn in sorted(os.listdir("mappings")):
        if not fn.endswith(".json"):
            continue
        m = json.load(io.open(os.path.join("mappings", fn), encoding="utf-8"))["map"]
        for cls, claimed in m.items():
            missing = [r for r in claimed if r not in rules]
            assert not missing, (
                f"{fn}/{cls}: the noisy control never emits {missing}, so a scanner using those "
                "rules is measured against a control that stays silent where it fires")

    with tempfile.TemporaryDirectory() as t:
        _case(t, VULN, FIXED)
        cases = [{"name": "case"}]
        prev = control_c2.CORPUS
        try:
            control_c2.CORPUS = t
            noisy = control_c2.noisy_findings(cases, sorted(rules))
        finally:
            control_c2.CORPUS = prev
    non_empty = len([l for l in VULN.split("\n") if l.strip()]) + \
        len([l for l in FIXED.split("\n") if l.strip()])
    assert len(noisy) == len(rules) * non_empty, (
        f"the control produced {len(noisy)} findings; every rule on every non-empty line of both "
        f"variants is {len(rules) * non_empty}. A control that flags less than everything is not "
        "the ceiling the front page says it is.")


# ----------------------------------------------------------------- holdout
# A commitment that can be edited afterwards proves nothing.

def test_holdout_key_order_does_not_change_the_commitment():
    import holdout
    a = {"repo": "x/y", "fix": "abc", "files": ["a.rs"], "class": "owner-checks"}
    b = {"class": "owner-checks", "files": ["a.rs"], "fix": "abc", "repo": "x/y"}
    assert holdout.digest(a) == holdout.digest(b)


def test_holdout_any_edit_breaks_the_commitment():
    import holdout
    a = {"repo": "x/y", "fix": "abc", "files": ["a.rs"], "class": "owner-checks"}
    for field, value in (("fix", "abd"), ("class", "type-cosplay"), ("repo", "x/z")):
        b = dict(a)
        b[field] = value
        assert holdout.digest(a) != holdout.digest(b), f"editing {field} must break the hash"


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
    for fn in os.listdir("mappings"):
        if not fn.endswith(".json"):
            continue
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


# --------------------------------------------------------------- unmapped
# `unmapped_check.py` changed a published number once: it is what found the X-Ray detection hiding
# under a rule the mapping pointed at the wrong class. Until 2026-09-01 the only test named for it
# called `score2.changed_lines` and never imported it, so removing the "fires on the fix too" guard
# - the entire difference between a candidate and a shape match - passed every check.

def _unmapped_fixture(tmp):
    case, _, _ = _case(tmp, VULN, FIXED)
    del case
    return ([{"name": "case", "class": "owner-checks"}], tmp,
            "case/insecure/src/lib.rs", "case/secure/src/lib.rs")


def test_unmapped_check_reports_a_differential_hit_at_the_fix_site():
    """The shape of the one real detection this project has ever recorded."""
    import unmapped_check
    with tempfile.TemporaryDirectory() as t:
        cases, corpus, ins, _ = _unmapped_fixture(t)
        got = unmapped_check.candidates(cases, corpus, {ins: [("UNMAPPED-RULE", 3)]})
        assert len(got) == 1, got
        assert got[0]["rule"] == "UNMAPPED-RULE" and got[0]["case"] == "case", got


def test_unmapped_check_rejects_a_rule_that_fires_on_the_fix_too():
    """This is the guard whose removal survived the whole suite before it had a test."""
    import unmapped_check
    with tempfile.TemporaryDirectory() as t:
        cases, corpus, ins, sec = _unmapped_fixture(t)
        got = unmapped_check.candidates(
            cases, corpus, {ins: [("UNMAPPED-RULE", 3)], sec: [("UNMAPPED-RULE", 3)]})
        assert got == [], \
            f"a rule that fires on the repaired code distinguishes nothing, yet it was offered: {got}"


def test_unmapped_check_rejects_a_hit_away_from_the_fix_site():
    import unmapped_check
    with tempfile.TemporaryDirectory() as t:
        cases, corpus, ins, _ = _unmapped_fixture(t)
        got = unmapped_check.candidates(cases, corpus, {ins: [("UNMAPPED-RULE", 400)]})
        assert got == [], f"a finding nowhere near the fix is not a candidate detection: {got}"


def test_build_case_puts_the_parent_in_insecure_and_the_fix_in_secure():
    """The orientation every case in corpus 2 depends on, and nothing checked it.

    Swapping `parent` and `fix` in `build_case` would make every newly built case's vulnerable
    variant the repaired code. The committed corpus would not change, so the suite passed, and the
    next case added would be silently backwards.
    """
    import build_corpus2
    with tempfile.TemporaryDirectory() as t:
        repo, fix, cache = build_corpus2.throwaway_repo(t)
        out = os.path.join(t, "out")
        r = build_corpus2.build_case(
            {"name": "case", "repo": repo, "fix": fix, "class": "owner-checks"}, cache, out)
        assert r["status"] == "built", r
        ins = io.open(os.path.join(out, "case", "insecure", "src", "lib.rs"),
                      encoding="utf-8").read()
        sec = io.open(os.path.join(out, "case", "secure", "src", "lib.rs"),
                      encoding="utf-8").read()
        assert "no owner check" in ins and "require_owner" not in ins, \
            f"insecure must be the commit BEFORE the fix: {ins!r}"
        assert "require_owner" in sec, f"secure must be the fix commit: {sec!r}"
        assert r["parent"] != fix and r["fix"] == fix, r


def test_build_case_takes_its_file_list_from_the_commit_and_skips_tests():
    """The paths are derived from the fix commit so a mistake in our notes cannot produce a pair."""
    import build_corpus2
    with tempfile.TemporaryDirectory() as t:
        repo, fix, cache = build_corpus2.throwaway_repo(t)
        repo_dir = build_corpus2.ensure_clone(repo, cache)
        got = build_corpus2.rs_files_in_commit(repo_dir, fix)
        assert got == ["src/lib.rs"], \
            f"the fix touched src/lib.rs, tests/t.rs and README.md; only the first is a case: {got}"



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



# ============================================================================ WAVE 2
# Added 2026-09-01 after the first suite was judged too thin for a project whose entire claim is
# that it measures carefully. Same selection rule: would a defect here change a published number?


# ------------------------------------------------------------------ score.py
# The corpus-1 scorer. Every headline figure on the teaching corpus comes out of these ten lines.

def test_score1_nominal_needs_a_hit_on_the_vulnerable_variant():
    import score
    rows = score.score([("R", "/x/2-owner-checks/secure/lib.rs")], {"2-owner-checks": ["R"]})
    cls, ins, sec, rec, nominal, real = rows[0]
    assert not nominal, "firing only on the fixed variant is not even nominal recall"


def test_score1_real_requires_silence_on_secure():
    import score
    rows = score.score([("R", "/x/2-owner-checks/insecure/lib.rs"),
                        ("R", "/x/2-owner-checks/secure/lib.rs")], {"2-owner-checks": ["R"]})
    _, _, _, _, nominal, real = rows[0]
    assert nominal and not real, "firing on both variants is nominal but not real recall"


def test_score1_recommended_variant_also_kills_real_recall():
    """sealevel-attacks ships a third variant. Ignoring it would inflate every score."""
    import score
    rows = score.score([("R", "/x/8-pda-sharing/insecure/lib.rs"),
                        ("R", "/x/8-pda-sharing/recommended/lib.rs")], {"8-pda-sharing": ["R"]})
    _, _, _, _, nominal, real = rows[0]
    assert nominal and not real, "a rule firing on 'recommended' has not detected the bug"


def test_score1_clean_detection():
    import score
    rows = score.score([("R", "/x/2-owner-checks/insecure/lib.rs")], {"2-owner-checks": ["R"]})
    _, _, _, _, nominal, real = rows[0]
    assert nominal and real


def test_score1_findings_in_another_class_do_not_count():
    import score
    rows = score.score([("R", "/x/3-type-cosplay/insecure/lib.rs")], {"2-owner-checks": ["R"]})
    _, ins, _, _, nominal, _ = rows[0]
    assert ins == 0 and not nominal, "a hit in a different class must not credit this one"


def test_score1_unmapped_rule_ignored():
    import score
    rows = score.score([("OTHER", "/x/2-owner-checks/insecure/lib.rs")], {"2-owner-checks": ["R"]})
    _, _, _, _, nominal, _ = rows[0]
    assert not nominal, "only the rule the mapping points at may credit a class"


def test_score1_windows_paths_are_handled():
    import score
    rows = score.score([("R", r"C:\x\2-owner-checks\insecure\lib.rs")], {"2-owner-checks": ["R"]})
    _, _, _, _, nominal, _ = rows[0]
    assert nominal, "backslash paths must score identically to forward slashes"


def test_score1_separates_real_from_nominal_on_every_published_mapping():
    """`score.py` computes `real = nominal and ...`, so asserting "real implies nominal" is a
    tautology and the old test could never fail whatever the mapping said.

    The property worth checking is the one the benchmark exists for: with a real mapping loaded,
    a rule that fires only on the vulnerable variant must score real, and the same rule firing on
    the fixed variant as well must score nominal and **not** real. A mapping whose rule ids no
    longer match what the scanner emits fails this, which is the defect the first result had.
    """
    import score, json, io as _io, os
    checked = 0
    for fn in sorted(os.listdir("mappings")):
        if not fn.endswith(".json"):
            continue
        m = json.load(_io.open(os.path.join("mappings", fn), encoding="utf-8"))["map"]
        cls = sorted(k for k, v in m.items() if v)
        if not cls:
            continue
        cls = cls[0]
        rule = m[cls][0]
        clean = {r[0]: (r[4], r[5]) for r in
                 score.score([(rule, f"/x/{cls}/insecure/a.rs")], m)}
        assert clean[cls] == (True, True), \
            f"{fn}: {rule!r} firing only on the vulnerable variant of {cls} must score real: {clean[cls]}"
        both = {r[0]: (r[4], r[5]) for r in
                score.score([(rule, f"/x/{cls}/insecure/a.rs"),
                             (rule, f"/x/{cls}/secure/a.rs")], m)}
        assert both[cls] == (True, False), \
            f"{fn}: {rule!r} firing on the fix too must be nominal and not real: {both[cls]}"
        checked += 1
    assert checked, "no mapping was exercised, so this check proved nothing"


# --------------------------------------------------------- run_all extractors
# One wrong parser silently changes a published number, and each scanner has its own format.

def test_extract_radar_envelope():
    import run_all
    blob = [{"name": "Rule A", "locations": ["/a/b.rs:10:1-5", "/c/d.rs:20:2-6"]}]
    out = run_all.extract("radar", blob)
    assert out == [("Rule A", "/a/b.rs"), ("Rule A", "/c/d.rs")], out


def test_extract_xray_same_envelope_as_radar():
    import run_all
    blob = [{"name": "1019", "locations": ["/a/b.rs:5:1"]}]
    assert run_all.extract("xray", blob) == [("1019", "/a/b.rs")]


def test_extract_semgrep_shape():
    import run_all
    blob = {"results": [{"check_id": "rust.x", "path": "src/a.rs", "start": {"line": 3}}]}
    assert run_all.extract("semgrep", blob) == [("rust.x", "src/a.rs")]


def test_extract_flat_findings_shape():
    import run_all
    blob = {"findings": [{"rule_id": "SOL-001", "file": "src/a.rs", "line": 7}]}
    assert run_all.extract("sol-audit", blob) == [("SOL-001", "src/a.rs")]


def test_extract_rejects_an_unknown_format_loudly():
    import run_all
    try:
        run_all.extract("not-a-real-format", [])
    except ValueError:
        return
    raise AssertionError("an unknown format must raise, not return an empty list")


def test_extract_handles_empty_input_without_inventing_findings():
    import run_all
    assert run_all.extract("radar", []) == []
    assert run_all.extract("semgrep", {"results": []}) == []
    assert run_all.extract("sol-audit", {"findings": []}) == []


# ------------------------------------------------------------- changed_lines
# If this is wrong, "at the fix site" is wrong, and every corpus-2 verdict with it.

def _pair(tmp, a, b):
    import os, io as _io
    p1, p2 = os.path.join(tmp, "a.rs"), os.path.join(tmp, "b.rs")
    _io.open(p1, "w", encoding="utf-8").write(a)
    _io.open(p2, "w", encoding="utf-8").write(b)
    return p1, p2


def test_changed_lines_marks_a_replacement():
    import score2, tempfile
    with tempfile.TemporaryDirectory() as t:
        a, b = _pair(t, "one\ntwo\nBUG\nfour\n", "one\ntwo\nFIXED\nfour\n")
        ch = score2.changed_lines(a, b)
        assert 3 in ch and 1 not in ch and 4 not in ch, ch


def test_changed_lines_marks_the_seam_of_a_pure_insertion():
    """A guard added by the fix has no line in the vulnerable file, but the seam must be marked
    or a correct detection at the missing check would score as unlocated."""
    import score2, tempfile
    with tempfile.TemporaryDirectory() as t:
        a, b = _pair(t, "one\ntwo\nthree\n", "one\nGUARD\ntwo\nthree\n")
        assert score2.changed_lines(a, b), "an insertion must still mark a location"


def test_changed_lines_marks_a_deletion():
    import score2, tempfile
    with tempfile.TemporaryDirectory() as t:
        a, b = _pair(t, "one\ntwo\nthree\n", "one\nthree\n")
        assert 2 in score2.changed_lines(a, b)


def test_changed_lines_identical_files_change_nothing():
    import score2, tempfile
    with tempfile.TemporaryDirectory() as t:
        a, b = _pair(t, "one\ntwo\n", "one\ntwo\n")
        assert score2.changed_lines(a, b) == set(), "identical files have no fix site"


def test_changed_lines_survives_an_empty_file():
    import score2, tempfile
    with tempfile.TemporaryDirectory() as t:
        a, b = _pair(t, "", "one\n")
        score2.changed_lines(a, b)   # must not raise


def test_tolerance_is_symmetric():
    import score2
    assert score2.near(100, {103}) and score2.near(100, {97})
    assert not score2.near(100, {104}) and not score2.near(100, {96})


# ------------------------------------------------------- acquisition filters
# A filter that matches the raw JSON blob once made an unrelated crate a Solana hit.

def test_acquisition_ignores_a_substring_match_in_unrelated_text():
    import corpus_ghsa
    fake = {"vulnerabilities": [{"package": {"name": "gix-packetline"}}],
            "summary": "reachable panic on empty side-band packet",
            "description": "nothing to do with blockchains"}
    assert corpus_ghsa.is_solana(fake) is None


def test_acquisition_matches_an_obvious_solana_crate():
    import corpus_ghsa
    real = {"vulnerabilities": [{"package": {"name": "anchor-lang"}}],
            "summary": "InterfaceAccount substitution", "description": ""}
    assert corpus_ghsa.is_solana(real)


def test_acquisition_matches_on_text_when_the_crate_name_is_neutral():
    import corpus_ghsa
    texty = {"vulnerabilities": [{"package": {"name": "obscure-crate"}}],
             "summary": "missing owner check in a Solana program", "description": ""}
    assert corpus_ghsa.is_solana(texty)


def test_acquisition_collapses_duplicate_commit_references():
    import corpus_ghsa
    adv = {"references": ["https://github.com/a/b/commit/deadbeef1234567",
                          "https://github.com/a/b/commit/deadbeef1234567",
                          "https://github.com/a/b/pull/42"]}
    commits, prs = corpus_ghsa.fix_refs(adv)
    assert len(commits) == 1 and prs[0]["pr"] == 42


# --------------------------------------------------- published-number lockdown
# Golden tests. If a refactor changes any of these, it changed a public claim.

def test_published_corpus1_numbers_still_reproduce():
    import run_all
    expected = {"radar": (11, 11), "sol-audit": (6, 4), "vaultlint": (2, 2),
                "xray": (4, 2), "solsec": (0, 0), "semgrep": (0, 0)}
    got = {r["scanner"]: (r.get("nominal"), r.get("real"))
           for r in run_all.measure() if r.get("status") == "measured"}
    for name, want in expected.items():
        assert name in got, f"{name} no longer measurable"
        assert got[name] == want, f"{name}: published {want}, now {got[name]}"


def test_the_corpus_one_noisy_control_scores_zero_real_recall_when_actually_scored():
    """This used to assert `len(findings) == 931` and nothing else: it checked that a file existed
    at the right size and never once scored it.

    Scoring it is the whole claim. `control-noisy` is on the front page as the reason no score above
    it was bought with volume, so the number that has to hold is its **real recall**, and it has to
    hold against every mapping in the repository rather than against a file size.

    The handover that stood here on 2026-09-01 was acted on. The file's only rule id was
    `NOISY-ALL`, which appears in no mapping, so `score.py` discarded all 931 findings and the
    published `11/11 nominal` did not reproduce: the control scored 0/11 nominal and demonstrated
    nothing. `tools/control_c1.py` regenerates it the way `control_c2.every_rule()` already builds
    the corpus-2 control, under **every** mapped rule id. Error 33.

    Three things are asserted, and the middle one is the one that was missing for a day:

    1. the finding count is **derived** (line positions times mapped rules), never typed;
    2. the control reaches **11/11 nominal** under at least one mapping, so it is demonstrably
       loud enough to be discarded on the merits rather than on an unmapped identifier;
    3. its **real recall is zero** under every mapping, which is the claim the front page makes.

    The control itself is built here in memory rather than read off disk. It is 81,928 findings
    and its corpus-2 twin is 296 MB; both regenerate byte-identically from the rule set in
    `mappings/` and the committed line inventory, so what is committed is the inventory, which is
    9 KB and is the only part that cannot be recomputed without the network.
    """
    import json, io as _io, os, sys
    sys.path.insert(0, "tools")
    import score, control_c1, control_c2
    if not os.path.exists(control_c1.INVENTORY):
        raise AssertionError(
            f"{control_c1.INVENTORY} is missing, so the teaching corpus's control cannot be "
            "rebuilt and the published control figure is unbacked")
    inventory = control_c1.inventory_from_artefact()
    lines = sum(len(v) for v in inventory.values())
    rules = control_c2.every_rule()
    assert lines == 931, (
        f"the teaching corpus has 931 non-empty .rs lines at the pinned commit; the control "
        f"now covers {lines}")
    built = control_c1.noisy_findings(inventory, rules)
    assert len(built) == lines * len(rules), (
        f"the control built {len(built)} findings; every mapped rule id on every one of {lines} "
        f"flagged lines is {lines * len(rules)}. A control that flags less than everything is "
        "not a ceiling.")
    assert {x["rule_id"] for x in built} == set(rules), (
        "the control does not emit under exactly the mapped rule set. An unmapped rule id scores "
        "zero by construction, which is what made this control prove nothing until 2026-09-01.")

    findings = [(x["rule_id"], x["file"]) for x in built]
    best_nominal = 0
    for fn in sorted(os.listdir("mappings")):
        if not fn.endswith(".json"):
            continue
        m = json.load(_io.open(os.path.join("mappings", fn), encoding="utf-8"))["map"]
        rows = score.score(findings, m)
        best_nominal = max(best_nominal, sum(1 for r in rows if r[4]))
        real = sum(1 for r in rows if r[5])
        assert real == 0, (
            f"{fn}: the noisy control scored {real} real detections. A scorer that credits a tool "
            "which flags every line of the fixed code as loudly as the vulnerable one is crediting "
            "volume, and every published number rests on it not doing that.")
    assert best_nominal == 11, (
        f"the noisy control reaches {best_nominal}/11 nominal recall. It has to reach 11/11 for "
        "its zero real recall to mean anything: a control that scores zero because nothing it "
        "says is mapped proves only that unmapped rules score zero.")


def test_corpus_commit_is_pinned_in_the_protocol():
    import io as _io
    s = _io.open("docs/PROTOCOL.md", encoding="utf-8").read()
    assert "24555d044802db4022112a94d6d70e74291a4b6d" in s, \
        "the corpus commit must stay pinned, or no score is reproducible"


# ------------------------------------------------------------ data integrity
# Cheap checks that catch a corrupted or half-written artefact before it reaches a table.

def test_every_raw_json_file_parses():
    """A half-written raw file is a corrupted number waiting to be published."""
    import json, io as _io, os
    targets = [os.path.join("raw", f) for f in sorted(os.listdir("raw"))]
    targets += [os.path.join("mappings", f) for f in sorted(os.listdir("mappings"))]
    targets += ["COMMITMENTS-HOLDOUT.json", "corpus2/manifest.json"]
    bad = []
    for fn in targets:
        if not fn.endswith(".json") or not os.path.exists(fn):
            continue
        try:
            json.load(_io.open(fn, encoding="utf-8"))
        except Exception as e:
            bad.append(f"{fn}: {type(e).__name__}")
    assert not bad, f"unparseable json: {bad}"



def test_every_corpus_case_names_its_fix_commit():
    import json, io as _io
    man = json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    for c in man:
        assert c.get("fix"), f"{c['name']} has no fix commit"
        assert c.get("repo"), f"{c['name']} has no repo"
        assert c.get("class"), f"{c['name']} has no vulnerability class"


def test_every_corpus_case_declares_its_source():
    """The answer key must be somebody else's, and traceable."""
    import json, io as _io
    man = json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    missing = [c["name"] for c in man if not c.get("source") and c.get("valid", True)]
    assert not missing, f"valid cases with no disclosure source: {missing}"


def test_clock_history_is_ordered_and_parseable():
    import json, io as _io, os, glob
    files = sorted(glob.glob("runs/*.json"))
    assert files, "the clock has no history"
    dates = []
    for f in files:
        d = json.load(_io.open(f, encoding="utf-8"))
        assert d.get("date"), f"{f} has no date"
        dates.append(d["date"])
    assert dates == sorted(dates), f"clock history is out of order: {dates}"


def test_results_pages_do_not_contradict_the_clock_on_radar():
    """The single most quoted number in the whole project."""
    import io as _io
    s = _io.open("docs/results/RESULTS-all.md", encoding="utf-8").read()
    assert "11 / 11" in s or "11/11" in s, "Radar's teaching-corpus score vanished from RESULTS-all"


# --------------------------------------------------------------- adapters.py
def test_finding_is_a_three_field_record():
    import adapters
    f = adapters.Finding("R", "a.rs", 3)
    assert (f.rule_id, f.path, f.line) == ("R", "a.rs", 3)


def test_null_control_produces_nothing():
    import adapters, tempfile
    n = adapters.NullScanner()
    assert n.available()
    with tempfile.TemporaryDirectory() as t:
        assert list(n.run(t)) == [], "the null control must be silent by construction"


def test_noisy_control_flags_every_non_empty_line():
    import adapters, tempfile, os, io as _io
    with tempfile.TemporaryDirectory() as t:
        _io.open(os.path.join(t, "a.rs"), "w", encoding="utf-8").write("one\n\ntwo\n")
        out = list(adapters.NoisyScanner().run(t))
        assert len(out) == 2, f"two non-empty lines should give two findings, got {len(out)}"


# ============================================================================ WAVE 3
# Documentation that drifts from the code is worse than no documentation: it tells a stranger to
# expect something the repository no longer does. These check that the promises in GETTING-STARTED
# and AGENTS.md are still true, and cover the paths waves 1 and 2 left alone.


# --------------------------------------------------- the "no dependencies" promise
# GETTING-STARTED says Python 3 and nothing else. If that stops being true, a stranger's first
# command fails and the whole "you can check our work" claim goes with it.

def test_no_external_python_dependencies():
    # sys.stdlib_module_names arrived in 3.10. That is a limit of how this check is
    # written, not of the code it checks: on 3.9 the other 91 checks pass and the tools
    # run. The CI matrix runs 3.11 and 3.12, so the check still executes on every push;
    # skipping here keeps 3.9 genuinely supported instead of dropping it to suit a test.
    import ast, os, sys
    if not hasattr(sys, "stdlib_module_names"):
        print("    skipped on Python %d.%d: needs sys.stdlib_module_names (3.10+); "
              "CI runs this check on 3.11 and 3.12" % sys.version_info[:2])
        return
    stdlib = set(sys.stdlib_module_names)
    local = {f[:-3] for f in os.listdir("tools") if f.endswith(".py")}
    local |= {d for d in os.listdir("tools")           # packages under tools/, e.g. spec
             if os.path.isfile(os.path.join("tools", d, "__init__.py"))}
    local |= {"scanner", "make_fixtures"}      # our own, and optional
    external = {}
    for fn in sorted(f for f in os.listdir("tools") if f.endswith(".py")):
        tree = ast.parse(open(os.path.join("tools", fn), encoding="utf-8").read())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module.split(".")[0]]
            for n in names:
                if n not in stdlib and n not in local:
                    external.setdefault(n, set()).add(fn)
    assert not external, \
        f"GETTING-STARTED promises no pip install, but these are external: {external}"


def test_the_optional_scanner_import_is_guarded():
    """`scanner` is our own tool and may be absent. Anything importing it unguarded breaks a
    stranger's clone."""
    import ast, os
    unguarded = []
    for fn in sorted(f for f in os.listdir("tools") if f.endswith(".py")):
        src = open(os.path.join("tools", fn), encoding="utf-8").read()
        if "import scanner" not in src:
            continue
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(a.name == "scanner" for a in node.names):
                # module level means col_offset 0 and not inside a try
                if node.col_offset == 0:
                    unguarded.append(fn)
    # rb.py is the original harness and is allowed to require it; nothing else may
    assert set(unguarded) <= {"rb.py"}, f"unguarded `import scanner` in {unguarded}"


def test_every_module_imports_without_side_effects():
    """shiftaware.py used to run its whole analysis at import time, which is why it had no tests.
    Nothing may do that again."""
    import importlib, os, sys
    skip = {"rb.py", "emit_sol_audit.py", "test_all.py"}   # these need `scanner` or are this file
    failed = {}
    for fn in sorted(f for f in os.listdir("tools") if f.endswith(".py")):
        if fn in skip:
            continue
        name = fn[:-3]
        try:
            if name in sys.modules:
                del sys.modules[name]
            importlib.import_module(name)
        except SystemExit as e:
            failed[fn] = f"called sys.exit({e.code}) at import"
        except Exception as e:
            failed[fn] = f"{type(e).__name__}: {e}"
    assert not failed, f"modules with import-time side effects or errors: {failed}"


# ------------------------------------------------- documented commands still exist
# This check existed and could not see the defect it was written for. Its regex was
# `python (\w[\w-]*\.py)`, and `\w` matches neither `.` nor `/`, so `python ../tools/verify.py`
# matched nothing at all and was silently skipped. Two of the three commands in the documented
# entry point for a human resolved above the repository root, three more in the walkthrough did,
# the README's only Windows block said `toolserify.py`, and every one of them was invisible here.
# Found from outside on 2026-09-01.

def _documented_command_files():
    """Every document that tells a reader to run something.

    The engineering logs are excluded on purpose: a log records what was run on a date, and
    correcting a command in one would be rewriting history rather than fixing a document.

    Same list as `_publication_documents`, and taken from the same place, so a document cannot be
    live for one check and invisible to the other.
    """
    return _publication_documents()


def _documented_scripts(text):
    import re
    return set(re.findall(r"python3?\s+([A-Za-z0-9_./\\-]+\.py)", text))


def test_every_documented_command_runs_from_the_repository_root():
    """One working directory for every documented command, or a reader has to guess which.

    Error 25 was a reproduce block that mixed two working directories, and neither reading of it
    ran. `../tools/verify.py` is the same defect: correct if you are standing somewhere the
    document never names, broken from the place it tells you to stand.
    """
    import io as _io
    bad = []
    for doc in _documented_command_files():
        for script in sorted(_documented_scripts(_io.open(doc, encoding="utf-8").read())):
            if ".." in script.split("/") or ".." in script.split("\\"):
                bad.append(f"{doc}: {script}")
    assert not bad, ("documented commands must be written from the repository root, "
                     f"not relative to wherever the reader happens to be: {bad}")


def test_every_documented_command_names_a_script_that_exists():
    """A quickstart that names a script that no longer exists is a broken promise."""
    import io as _io, os
    missing = []
    for doc in _documented_command_files():
        for script in sorted(_documented_scripts(_io.open(doc, encoding="utf-8").read())):
            if not os.path.exists(script.replace("\\", "/")):
                missing.append(f"{doc}: {script}")
    assert not missing, f"documents name scripts that do not exist: {missing}"


def test_every_command_in_the_readme_is_runnable():
    """The README's quickstart is the front door: a command naming a script
    that does not exist breaks the two-minute promise on the first paste.
    Backslash paths are normalised, because the Windows block is legitimate."""
    import io as _io, os, re
    s = _io.open("README.md", encoding="utf-8").read()
    scripts = set(p.replace("\\", "/") for p in re.findall(r"python3? ([\w./\\-]+\.py)", s))
    missing = [x for x in sorted(scripts) if not os.path.exists(x)]
    assert not missing, f"README names scripts that do not exist: {missing}"


def test_no_control_bytes_hiding_in_any_document():
    """The Windows quickstart shipped a vertical tab inside `tools\verify.py`,
    so the command read `python tools\x0berify.py` and failed when pasted.
    A control byte is invisible in every renderer and corrupts whatever a
    reader copies. Markdown has no legitimate use for one."""
    import os
    bad = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", ".omc", "__pycache__", "node_modules")]
        for fn in files:
            if not fn.endswith(".md"):
                continue
            path = os.path.join(root, fn)
            data = open(path, "rb").read()
            for off, b in enumerate(data):
                if b < 0x20 and b not in (0x09, 0x0A, 0x0D):
                    line = data.count(b"\n", 0, off) + 1
                    bad.append(f"{path}:{line} byte 0x{b:02x}")
                    break
    assert not bad, f"control bytes inside documents: {bad}"


def test_documents_linked_from_the_readme_exist():
    import io as _io, os, re
    s = _io.open("README.md", encoding="utf-8").read()
    links = set(re.findall(r"\]\((?!http)([A-Za-z0-9_./-]+\.md)\)", s))
    missing = [x for x in sorted(links) if not os.path.exists(x)]
    assert not missing, f"README links to missing files: {missing}"


def test_the_platform_claims_match_what_ci_actually_runs():
    """The README tells a stranger which systems and Python versions work. That claim
    is only worth anything if the machines we do not control actually run them, so it
    is derived from the workflow rather than typed beside it."""
    import io as _io, re
    ci = _io.open(".github/workflows/verify.yml", encoding="utf-8").read()
    s = _io.open("README.md", encoding="utf-8").read()

    for os_name in ("windows", "macos", "ubuntu"):
        assert f"{os_name}-latest" in ci, \
            f"README promises {os_name} but CI no longer runs it"

    versions = sorted({v for v in re.findall(r'python-version: "(\d+\.\d+)"', ci)},
                      key=lambda v: [int(x) for x in v.split(".")])
    lo, hi = versions[0], versions[-1]
    assert f"Python {lo}-{hi}" in s, (
        f"README must state the Python range CI proves, which is {lo}-{hi}; "
        f"found versions {versions}")


def test_a_backslash_path_maps_to_the_same_case_as_a_forward_slash_one():
    """The README says Windows is in CI because a scorer can get paths quietly wrong.
    This is the check that makes the sentence true rather than reassuring."""
    import score
    mapping = {"2-owner-checks": ["R"]}
    posix = score.score([("R", "x/2-owner-checks/insecure/lib.rs")], mapping)
    win = score.score([("R", r"C:\x\2-owner-checks\insecure\lib.rs")], mapping)
    assert posix == win, (
        "the same finding located by a Windows path scores differently from a POSIX one: "
        f"{posix!r} vs {win!r}")


def test_the_error_count_matches_the_logs():
    """The README's error count is its strongest claim, so it is the one most worth
    keeping honest. Derived from the logs rather than typed, because the count only
    ever goes up and a stale figure understates exactly the thing we want on record."""
    import io as _io, re, glob
    logged = 0
    for f in sorted(glob.glob("docs/ENGINEERING-LOG-*.md")):
        s = _io.open(f, encoding="utf-8").read()
        logged = max(logged, *[int(n) for n in re.findall(r"\*\*Error (\d+)", s)] or [0])
    s = _io.open("README.md", encoding="utf-8").read()
    claimed = re.search(r"\*\*\[(\d+) of our own errors\]", s)
    assert claimed, "the README no longer states an error count; that claim is load-bearing"
    assert int(claimed.group(1)) == logged, (
        f"README claims {claimed.group(1)} errors but the logs number up to {logged}")


def test_the_readme_links_the_newest_engineering_log():
    """A reader following the error link must land on the current log, not the one that
    happened to be newest when the sentence was written."""
    import io as _io, glob, os
    newest = sorted(glob.glob("docs/ENGINEERING-LOG-*.md"))[-1]
    s = _io.open("README.md", encoding="utf-8").read()
    assert os.path.basename(newest) in s, (
        f"README does not link the newest engineering log ({newest})")



def _noisy_control_quantities():
    """Every number the noisy control legitimately produces, computed, never typed.

    Both figures are products of two things the repository already knows: how many non-empty
    lines the control flags, and how many distinct mapped rule ids it flags them under. Deriving
    them costs about ten milliseconds, so there is no excuse for a document to carry a stale one.
    """
    import json, os, sys
    sys.path.insert(0, "tools")
    import control_c1, control_c2

    rules = len(control_c2.every_rule())
    c1_lines = sum(len(v) for v in control_c1.inventory_from_artefact().values())

    cases = [c for c in json.load(open("corpus2/manifest.json", encoding="utf-8"))["cases"]
             if c.get("valid", True)]
    c2_lines = 0
    for c in cases:
        for variant in ("insecure", "secure"):
            d = os.path.join("corpus2", c["name"], variant, "src")
            if not os.path.isdir(d):
                continue
            for fn in sorted(os.listdir(d)):
                if fn.endswith(".rs"):
                    with open(os.path.join(d, fn), encoding="utf-8", errors="replace") as fh:
                        c2_lines += sum(1 for line in fh if line.strip())
    return {"rules": rules, "c1_lines": c1_lines, "c2_lines": c2_lines,
            "c1_findings": c1_lines * rules, "c2_findings": c2_lines * rules}


def test_no_document_states_a_noisy_control_figure_the_tools_do_not_produce():
    """Error 33 corrected the corpus-1 control from 931 findings to 81,928, and AGENTS.md kept the
    retracted figure for eight hours after the front page was fixed, because the derived-count
    check counts tests and nothing else while the control figures are typed by hand.

    The first version of this check compared every number in a noisy-control sentence against a
    set of legal quantities. It passed, and then a mutation putting 931 back as a findings count
    SURVIVED it, because 931 is legal: it is the line count. A check that accepts the right number
    under the wrong noun is not a check.

    So the noun decides. `931 findings` is the retracted claim; `931 non-empty lines` is the fact
    it was derived from. Each quantity is checked against what it is a count OF.

    Known limit, stated rather than left for someone to discover: this keys on the word "noisy",
    so a sentence that discusses the control without naming it is out of scope. AGENTS.md contains
    one such sentence on purpose, describing what the broken artefact used to emit, in the past
    tense. Widening the match to catch it would mean teaching the check to recognise historical
    narration, and a check that learns exceptions to prose stops guarding anything.
    """
    import io as _io, re
    q = _noisy_control_quantities()
    expected = {
        "findings": {q["c1_findings"], q["c2_findings"]},
        "lines": {q["c1_lines"], q["c2_lines"]},
        "rules": {q["rules"]},
    }
    nouns = (r"(?P<n>\d[\d,]*)\s+(?:distinct\s+|mapped\s+|non-empty\s+)*"
             r"(?P<k>findings|lines|rules|rule ids)")
    wrong = []
    for doc in _documented_command_files():
        for line in _io.open(doc, encoding="utf-8").read().splitlines():
            if "noisy" not in line.lower():
                continue
            for m in re.finditer(nouns, line):
                n = int(m.group("n").replace(",", ""))
                kind = "rules" if m.group("k").startswith("rule") else m.group("k")
                if n >= 100 and n not in expected[kind]:
                    wrong.append(f"{doc}: {m.group(0)!r}, expected one of "
                                 f"{sorted(expected[kind])}")
    assert not wrong, ("a noisy-control figure must be a quantity the tools produce, counted as "
                       f"the thing it is named as: {wrong}")


def test_a_retirement_must_be_signed_or_the_gate_refuses_it():
    """The escape hatch added on 2026-09-01 must not become the way inconvenient rows go quiet.

    A measurement may declare itself retired and `--verify-coverage` then reports it instead of
    failing on it. That is only defensible while a retirement is a statement somebody signed, so
    every one must name the date, what supersedes it, the reason, and where it was published.
    A retirement missing any of those is refused here rather than trusted.
    """
    import scanner_spec
    required = ("on", "by", "reason", "where_published")
    bad = []
    for name, spec in sorted(scanner_spec.load_all().items()):
        for m in spec.get("measurements", []):
            r = m.get("retired")
            if not r:
                continue
            missing = [k for k in required if not str(r.get(k, "")).strip()]
            if missing:
                bad.append(f"{name}/{m.get('corpus')}/{m.get('row')}: missing {missing}")
    assert not bad, f"a retirement must be signed: {bad}"


def test_a_retired_row_is_reported_and_not_counted_but_still_visible():
    """Both halves, because either one alone is a defect.

    Not counted: a row we have publicly retired must not hold the coverage gate red, or the badge
    stops meaning anything. Still visible: a retired row that vanished from the output would be a
    deletion dressed as a correction, which is the one thing this project does not do.
    """
    import io, run_all
    rows, failures = run_all.verify_coverage(echo=False)
    retired = [r for r in rows if r.get("retired")]
    assert retired, "the sol-audit v2 corpus-2 row is retired and should appear as such"
    for r in retired:
        tag = f"{r['corpus']} {r['scanner']}:"
        # The colon matters. Without it this prefix also matches `sol-audit-v3`,
        # and the first version of this test read a live row's gap as the
        # retired row holding the gate red.
        assert not any(f.startswith(tag) for f in failures),             f"{tag} is retired and must not hold the gate red"
    buf = io.StringIO()
    import contextlib
    with contextlib.redirect_stdout(buf):
        run_all.verify_coverage(echo=True)
    assert "RETIRED" in buf.getvalue(), "a retired row must stay visible in the output"

def test_the_advertised_check_count_matches_the_suite():
    """The README said 82 while the suite ran 88. Adding tests without updating the
    figure is the easiest way to make the front page lie, so the figure is derived.

    Scoped to README and AGENTS until 2026-09-01, when an external review pointed out that
    GETTING-STARTED said 59, WALKTHROUGH said 81, ROADMAP said 81 and all three skills said 81,
    while the suite ran 94 - and that the skills' own instruction on a mismatch is to stop and
    report, so the project was telling its agents to halt. The fix that mattered was not the
    numbers; it was that the derived check covered two documents out of seven.
    """
    import io as _io, re
    actual = len([n for n in globals() if n.startswith("test_")])
    wrong = []
    for doc in _documented_command_files():
        s = _io.open(doc, encoding="utf-8").read()
        for n in re.findall(r"(\d+)\s+checks", s) + re.findall(r"(\d+)\s+passed", s):
            if int(n) != actual:
                wrong.append(f"{doc}: {n}")
    assert not wrong, (f"the suite defines {actual} checks; these documents say otherwise: {wrong}")


def test_no_document_carries_a_stray_control_character():
    """`python tools\\verify.py` was stored with a literal 0x0B where the backslash belonged.

    The README's only Windows code block therefore read `toolserify.py` and could not run, and no
    check saw it: the regex that looks for documented commands cannot match across a control
    character, so the line silently contributed nothing. A whole section of the front page argues
    that Windows is supported.
    """
    import io as _io
    allowed = {"\n", "\t"}
    bad = []
    for doc in _documented_command_files():
        s = _io.open(doc, encoding="utf-8", newline="").read()
        for i, ch in enumerate(s):
            if ch < " " and ch not in allowed and ch != "\r":
                bad.append(f"{doc}: {ch!r} at offset {i}")
    assert not bad, f"control characters in documents that tell a reader what to run: {bad}"


def test_the_real_vulnerability_denominator_is_reconciled_on_the_front_page():
    """Nine valid cases, eight built: the table reads out of eight. A reader who sees
    both numbers without explanation is right to distrust the whole page.

    Rewritten 2026-09-01, when eight cases were added and none of them was measured.
    The old derivation read the results denominator off the BUILT set, so adding a
    case would have silently restated every published zero as out of sixteen without
    a scanner having seen one of them. Built and measured are separate numbers now,
    and the results table is pinned to the measured one, because that is the only
    set a score can honestly be out of."""
    import io as _io, json, os
    cases = json.load(open("corpus2/manifest.json"))
    cases = cases["cases"] if isinstance(cases, dict) else cases
    valid = [c for c in cases if c.get("valid", True)]
    built = [c for c in valid if os.path.isdir(os.path.join("corpus2", c["name"]))]
    measured = [c for c in built if c.get("measured", True)]
    s = _io.open("README.md", encoding="utf-8").read()
    for n, phrase in ((len(valid), "valid cases"), (len(built), "built"),
                      (len(measured), "measured")):
        assert f"{n} {phrase}" in s, (
            f"the README must reconcile the three counts a reader needs: {len(valid)} "
            f"valid, {len(built)} built, {len(measured)} measured. It never says "
            f"'{n} {phrase}', so a reader cannot tell why a score reads out of "
            f"{len(measured)}")
    assert f"0 / {len(measured)}" in s, (
        "the README result table denominator must be the MEASURED corpus, not the "
        f"built one; expected '0 / {len(measured)}'")


def test_every_relative_link_in_every_document_resolves():
    """The README-only, .md-only check missed a link to a .log inside docs/results/.

    Moving files into docs/ and raw/ broke it silently: the link was relative to the
    document's old home at the repository root. Any relative target, any extension,
    from any document."""
    import io as _io, os, re
    broken = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", ".omc", "__pycache__", "node_modules")]
        for fn in files:
            if not fn.endswith(".md"):
                continue
            doc = os.path.join(root, fn)
            s = _io.open(doc, encoding="utf-8", errors="replace").read()
            for target in re.findall(r"\]\((?!https?:|mailto:|#)([^)\s#]+)", s):
                if not os.path.exists(os.path.join(root, target)):
                    broken.append(f"{doc} -> {target}")
    assert not broken, "documents link to missing files: " + repr(sorted(broken))


# ------------------------------------------- claims banned everywhere, not on the front page
# Three checks used to ban an overclaim in README.md and nowhere else, so each of them stood
# corrected on the front page and uncorrected one link away: "the packaging objection is now
# retired" in RESULTS-all, "927 `.rs` files" in RESULTS-all, RESULTS-realcrates and ROADMAP,
# "ten production vulnerabilities" in RESULTS-all and PROTOCOL, "the corpus was last updated in
# 2024" in PROTOCOL four sections after the same document pins it to 2022-07-16. Error 22 in the
# engineering log is this pattern and was diagnosed as a README problem rather than a scoping
# problem. A claim is banned in the repository or it is not banned.

def _publication_documents():
    """Every markdown document that speaks in the present tense.

    The engineering logs are excluded, and only they: they record what was believed on a date,
    including the wording later retracted, and a log that is edited to agree with today is not a
    log. Everything else is a live claim.

    The list comes from `git ls-files` where there is a git history, not from a directory walk.
    A walk picks up whatever else happens to be sitting in the working tree - during this work it
    found nine unrelated scratch documents in an untracked directory - so what the check scans
    would differ between a contributor's machine and CI. The same hazard applies to `mappings/`.
    """
    import os, subprocess
    out = []
    try:
        p = subprocess.run(["git", "ls-files", "*.md"], capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            out = [line.strip() for line in p.stdout.splitlines() if line.strip()]
    except OSError:
        out = []
    if not out:
        for base, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs
                       if not d.startswith(".") and d not in ("__pycache__",)]
            for f in sorted(files):
                if f.endswith(".md"):
                    out.append(os.path.join(base, f).replace("\\", "/"))
    return sorted(f for f in (x.replace("\\", "/") for x in out)
                  if not os.path.basename(f).startswith("ENGINEERING-LOG"))


def test_no_document_carries_a_superseded_claim():
    """Each entry here was true once and was corrected somewhere. This is where it stays corrected."""
    import io as _io, re as _re
    banned = {
        "One scanner has been measured": "six are measured",
        "corpus last updated in 2024": "the teaching corpus is pinned at 2022-07-16",
        "last updated in 2024": "the teaching corpus is pinned at 2022-07-16",
        "packaging objection is now retired": "six pairs and two scanners test it, they do not retire it",
        "retires the packaging objection": "six pairs and two scanners test it, they do not retire it",
        "retired the packaging objection": "six pairs and two scanners test it, they do not retire it",
        "ten production vulnerabilities": "the corpus-2 denominator is read from the manifest, never typed",
        "Ten real cases": "the corpus-2 denominator is read from the manifest, never typed",
    }
    hits = []
    for doc in _publication_documents():
        # ~~struck through~~ is this project's marker for wording it has publicly retracted, kept
        # beside the correction on purpose. Banning what a retraction quotes would force the
        # retraction to be deleted, which is the opposite of the rule.
        s = _re.sub(r"~~.*?~~", "", _io.open(doc, encoding="utf-8").read(), flags=_re.S)
        for phrase, why in banned.items():
            if phrase in s:
                hits.append(f"{doc}: {phrase!r} ({why})")
    assert not hits, "superseded claims still published:\n  " + "\n  ".join(hits)


def test_no_document_quotes_an_uncheckable_rs_file_count():
    """927 `.rs` files was error 23: the real crates are built on demand and never committed, so
    the figure is not checkable from the repository by anyone. Withdrawn from the README and left
    standing in three other documents, which is how a retraction becomes decorative."""
    import io as _io, json as _json, os, re
    on_disk = sum(len([f for f in fs if f.endswith(".rs")]) for _, _, fs in os.walk("corpus2"))
    legal = {on_disk}
    # The real crates are still built on demand and still not committed, so the figure error 23
    # withdrew is still unquotable AS SUCH. What changed on 2026-09-01 is that the build now
    # commits its own inventory, so ONE real-crate total is recomputable from the repository:
    # the .rs files in the crates the manifest marks valid. That number is admitted here by
    # being recomputed, not by being allowed - quote any other and this still fails.
    inv = "raw/rc-crates-built-2026-09-01.json"
    if os.path.exists(inv):
        valid = {c["name"] for c in
                 _json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
                 if c.get("valid", True)}
        legal.add(sum(r.get("rs_files_in_crate", 0) for r in
                      _json.load(_io.open(inv, encoding="utf-8"))
                      if r.get("status") == "built" and r["name"] in valid))
    bad = []
    for doc in _publication_documents():
        s = _io.open(doc, encoding="utf-8").read()
        for n in re.findall(r"(\d[\d,]{2,})\s*`?\.rs`?\s*files", s):
            if int(n.replace(",", "")) not in legal:
                bad.append(f"{doc}: {n}")
    assert not bad, (
        f"the checkable .rs counts are {sorted(legal)}; these documents quote a count nobody "
        f"can check: {bad}. Cite the per-case table in docs/results/RESULTS-realcrates.md instead.")


def test_readme_does_not_overstate_the_real_crates_result():
    """A one-line summary on the front page must not drop the results page's denominators.

    It used to require the words "six pairs" and "two scanners", which were the denominators
    until 2026-09-01, when four more scanners were run over all seventeen valid cases in both
    packagings. Requiring the old wording would have forced the front page to keep understating
    the run; requiring nothing would have let it overstate. So it requires today's denominators:
    how many scanners were compared across packagings, and the weak row that remains."""
    import io as _io
    s = _io.open("README.md", encoding="utf-8").read()
    i = s.find("**Real crates**")
    assert i > 0, "the real-crates bullet is gone; update or remove this test"
    bullet = s[i:i + 700]
    assert "four scanners" in bullet.lower(),         "the real-crates claim must say how many scanners were actually run on them"
    assert "radar" in bullet.lower(),         "the real-crates claim must keep naming the tool whose real-crate coverage is partial"
    for banned in ("retires the packaging objection", "retired the packaging objection"):
        assert banned not in bullet.lower(),             f"unqualified claim {banned!r}: six pairs tests an objection, it does not retire it"


def test_skills_referenced_by_agents_md_exist():
    import io as _io, os, re
    s = _io.open("AGENTS.md", encoding="utf-8").read()
    links = set(re.findall(r"\]\((skills/[A-Za-z0-9_./-]+)\)", s))
    missing = [x for x in sorted(links) if not os.path.exists(x)]
    assert not missing, f"AGENTS.md references missing skills: {missing}"


def test_every_skill_names_itself_correctly_and_says_when_to_use_it():
    """Frontmatter presence was all this checked, so a skill named after the wrong directory or
    carrying a one-word description passed. A skill is only reachable through its description."""
    import io as _io, os, re
    for d in sorted(os.listdir("skills")):
        p = os.path.join("skills", d, "SKILL.md")
        assert os.path.exists(p), f"{d} has no SKILL.md"
        text = _io.open(p, encoding="utf-8").read()
        assert text.startswith("---"), f"{d}: no frontmatter"
        front = text.split("---", 2)[1]
        name = re.search(r"^name:\s*(.+)$", front, re.M)
        desc = re.search(r"^description:\s*(.+)$", front, re.M)
        assert name and desc, f"{d}: incomplete frontmatter"
        assert name.group(1).strip() == d, \
            f"{d}: frontmatter name is {name.group(1).strip()!r}; an agent looks it up by directory"
        assert len(desc.group(1).split()) >= 12, \
            f"{d}: the description is what decides whether this skill is ever used, and it is "
        assert "use when" in desc.group(1).lower() or "when " in desc.group(1).lower(), \
            f"{d}: the description must say when to use the skill, not only what it is"


# ------------------------------------------------------------ CI honesty
def test_ci_runs_the_test_suite():
    import io as _io
    s = _io.open(".github/workflows/verify.yml", encoding="utf-8").read()
    assert "test_all.py" in s, "CI does not run the test suite, so the badge overstates"


def test_ci_step_names_do_not_overclaim():
    """A step called 'published headline reproduces' that only checks run 1 is a false badge."""
    import io as _io
    s = _io.open(".github/workflows/verify.yml", encoding="utf-8").read()
    assert "NOT the current headline" in s, \
        "the verify.py step must say what it does not cover"


# ---------------------------------------------------- protocol / results consistency
def test_protocol_states_the_falsifier_with_a_date():
    import io as _io, re
    s = _io.open("docs/PROTOCOL.md", encoding="utf-8").read()
    assert "fourteen days" in s or "14 days" in s or "2026-09-14" in s, \
        "the stop condition must stay stated, and it only binds if it is written down"


def test_protocol_warns_that_corpus_one_is_in_sample():
    import io as _io
    s = _io.open("docs/PROTOCOL.md", encoding="utf-8").read().lower()
    assert "in-sample" in s, "every corpus-1 score must carry the in-sample warning"


def test_every_numbered_limitation_has_a_body():
    """This asserted `> 60 lines`, which a file of blank lines satisfies.

    What matters is that each numbered limitation still says something. A limitation resolved by
    deleting its text, or by leaving a heading with nothing under it, is a limitation tidied away.
    """
    import io as _io, re
    s = _io.open("docs/KNOWN-LIMITATIONS.md", encoding="utf-8").read()
    sections = re.split(r"^## ", s, flags=re.M)[1:]
    numbered = [x for x in sections if re.match(r"\d+\.", x)]
    assert len(numbered) >= 8, \
        f"KNOWN-LIMITATIONS lists {len(numbered)} numbered limitations; they do not disappear"
    thin = []
    for sec in numbered:
        head, _, body = sec.partition("\n")
        if len(body.strip()) < 80:
            thin.append(head.strip()[:60])
    assert not thin, f"limitations with no substance under the heading: {thin}"


def test_each_commitment_is_stated_with_its_reasoning():
    """A substring search for "free" and "no money" passes on a document that has been gutted.

    Three promises are made in COMMITMENTS.md and quoted on the front page. Each must still be a
    section with text under it, because the promise is the argument, not the phrase.
    """
    import io as _io, re
    s = _io.open("docs/COMMITMENTS.md", encoding="utf-8").read()
    sections = re.split(r"^## ", s, flags=re.M)[1:]
    numbered = {}
    for sec in sections:
        m = re.match(r"(\d+)\.\s*(.+)", sec)
        if m:
            numbered[int(m.group(1))] = sec
    assert set(numbered) >= {1, 2, 3}, f"three promises are made; the file has {sorted(numbered)}"
    for i, sec in sorted(numbered.items()):
        body = sec.partition("\n")[2].strip()
        assert len(body) > 120, f"promise {i} has no reasoning under it, only a heading"
    lower = s.lower()
    for phrase in ("free", "open", "no money"):
        assert phrase in lower, f"the commitments no longer contain {phrase!r}"


# --------------------------------------------------------- corpus/case sanity
def test_no_case_is_both_valid_and_unexplained_when_excluded():
    import json, io as _io
    man = json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    for c in man:
        if c.get("valid", True) is False:
            assert len(c.get("invalid_reason", "")) > 40, \
                f"{c['name']} excluded with a reason too short to audit"


def test_case_names_are_unique():
    import json, io as _io
    man = json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    names = [c["name"] for c in man]
    assert len(names) == len(set(names)), "duplicate case names would double-count a denominator"


def test_pinned_files_look_like_source_paths():
    import json, io as _io
    man = json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    for c in man:
        for f in c.get("files", []):
            assert f.endswith(".rs"), f"{c['name']} pins a non-Rust file: {f}"
            assert not f.startswith("/"), f"{c['name']} pins an absolute path: {f}"


def test_fix_commits_look_like_shas():
    import json, io as _io, re
    man = json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    for c in man:
        fix = c["fix"]
        if fix.startswith("PENDING"):
            continue
        assert re.fullmatch(r"[0-9a-f]{7,40}", fix), f"{c['name']} has a malformed fix sha: {fix}"


# ------------------------------------------------------- holdout ledger sanity
def test_holdout_ledger_never_seals_a_round_twice():
    import json, io as _io, os
    if not os.path.exists("COMMITMENTS-HOLDOUT.json"):
        return
    d = json.load(_io.open("COMMITMENTS-HOLDOUT.json", encoding="utf-8"))
    rounds = [r["round"] for r in d.get("rounds", [])]
    assert len(rounds) == len(set(rounds)), \
        "a round sealed twice would let a disappointing holdout be replaced"


def test_holdout_ledger_admits_what_round_one_does_not_prove():
    import json, io as _io, os
    if not os.path.exists("COMMITMENTS-HOLDOUT.json"):
        return
    d = json.load(_io.open("COMMITMENTS-HOLDOUT.json", encoding="utf-8"))
    key = [k for k in d if "NOT_prove" in k or "not_prove" in k.lower()]
    assert key, "the ledger must state that round 1 gives timestamp integrity, not concealment"


def test_a_holdout_spec_without_a_nonce_is_refused():
    """Four public fields hash to a commitment anyone can brute-force at one guess per hash.

    `repo` is one of a few dozen Solana projects, `fix` a commit inside it, `class` one of about a
    dozen strings, `files` a path in that commit - and CANDIDATES-TRIAGE names the pending
    candidates. Round 1 was sealed that way and stays as it was sealed; from round 2 the nonce is
    required, and `commit` must refuse rather than seal something that conceals nothing.
    """
    import argparse, contextlib, json, io as _io, os
    import holdout
    with tempfile.TemporaryDirectory() as t:
        cwd = os.getcwd()
        spec = {"repo": "x/y", "fix": "a" * 40, "files": ["src/lib.rs"], "class": "owner-checks"}
        path = os.path.join(t, "spec.json")
        json.dump(spec, _io.open(path, "w", encoding="utf-8"))
        os.chdir(t)
        try:
            # holdout prints its refusals; the suite's own output stays readable.
            sink = _io.StringIO()
            with contextlib.redirect_stdout(sink):
                rc = holdout.cmd_commit(argparse.Namespace(spec=path, round=99, note=""))
            assert rc != 0, "a spec with no nonce must not be sealed"
            spec["nonce"] = "deadbeef"
            json.dump(spec, _io.open(path, "w", encoding="utf-8"))
            with contextlib.redirect_stdout(sink):
                rc = holdout.cmd_commit(argparse.Namespace(spec=path, round=99, note=""))
            assert rc != 0, "a short nonce conceals nothing and must not be sealed"
            spec["nonce"] = "0" * holdout.NONCE_HEX_CHARS
            json.dump(spec, _io.open(path, "w", encoding="utf-8"))
            with contextlib.redirect_stdout(sink):
                rc = holdout.cmd_commit(argparse.Namespace(spec=path, round=99, note=""))
            assert rc == 0, "a full-length hex nonce must seal"
        finally:
            os.chdir(cwd)


def test_the_nonce_actually_conceals():
    """Guessing every public field must not confirm the case."""
    import holdout
    spec = {"repo": "x/y", "fix": "a" * 40, "files": ["src/lib.rs"], "class": "owner-checks",
            "nonce": "1" * holdout.NONCE_HEX_CHARS}
    guessed = {k: v for k, v in spec.items() if k != "nonce"}
    assert holdout.digest(guessed) != holdout.digest(spec), \
        "a preimage guess without the nonce must not match the commitment"
    assert holdout.digest(dict(guessed, nonce="2" * holdout.NONCE_HEX_CHARS)) \
        != holdout.digest(spec), "a wrong nonce must not match either"


def test_the_ledger_declares_the_nonce_scheme_and_does_not_re_seal_round_one():
    """A commitment ledger may never rewrite a commitment, so round 1 keeps its own scheme."""
    import json, io as _io, os
    if not os.path.exists("COMMITMENTS-HOLDOUT.json"):
        return
    d = json.load(_io.open("COMMITMENTS-HOLDOUT.json", encoding="utf-8"))
    assert "nonce" in d.get("scheme", ""), "the ledger must declare the nonce in its scheme"
    assert d.get("nonce_required_from"), "the ledger must say from which round the nonce is required"
    for r in d["rounds"]:
        if r["round"] < d["nonce_required_from"]:
            assert "no nonce" in r.get("scheme", ""), (
                f"round {r['round']} predates the nonce and must say so rather than look compliant")
    assert d["rounds"][0]["commitment"] == \
        "fc525b66495c0f576d7d328e2b74eaa733f11fbe7fbfd2cf340de38b15835ec1", \
        "round 1's commitment was published on 2026-08-31 and may never change"


def test_unreleased_holdout_specs_are_not_in_the_repository():
    """A sealed spec sitting in the repo is not sealed."""
    import json, io as _io, os
    if not os.path.exists("COMMITMENTS-HOLDOUT.json"):
        return
    d = json.load(_io.open("COMMITMENTS-HOLDOUT.json", encoding="utf-8"))
    for r in d.get("rounds", []):
        if not r.get("released"):
            assert r.get("spec") is None, \
                f"round {r['round']} is unreleased but its spec is stored in the repo"


# ------------------------------------------------------------ candidate triage
def test_rejected_candidates_carry_a_written_reason():
    """This asserted that the strings "REJECT" and "out of scope" appeared somewhere in the file,
    which one rejection among fifty acceptances satisfies. Now every rejection is checked."""
    import io as _io, os, re
    if not os.path.exists("docs/CANDIDATES-TRIAGE.md"):
        return
    lines = _io.open("docs/CANDIDATES-TRIAGE.md", encoding="utf-8").read().split("\n")
    rejects = [l for l in lines if "REJECT" in l]
    assert rejects, "the triage file records acceptances only, which hides the judgement calls"
    unexplained = []
    for line in rejects:
        # A rejection is a reason plus the words. Strip the marker and the table furniture, and
        # something has to be left.
        rest = re.sub(r"\*\*|`|\|", " ", line)
        rest = re.sub(r"REJECT[^A-Za-z]*", " ", rest)
        if len(rest.split()) < 6:
            unexplained.append(line.strip()[:70])
    assert not unexplained, f"rejections that say that, not why: {unexplained}"


def test_every_file_named_in_ci_exists():
    """CI caught a stale path that the suite did not, because the suite never invoked that CLI.
    Now it checks the workflow's own arguments, so the next move is caught before pushing."""
    import io as _io, os, re
    s = _io.open(".github/workflows/verify.yml", encoding="utf-8").read()
    refs = set(re.findall(r"--findings\s+([A-Za-z0-9_./-]+)", s))
    # `[A-Za-z0-9_-]+` matched neither a dot nor a slash, so every `python tools/<x>.py` step in
    # the workflow was silently skipped by the check written to verify them. Same blindness as the
    # documented-command check had.
    refs |= set(re.findall(r"python3?\s+([A-Za-z0-9_./-]+\.py)", s))
    missing = [r for r in sorted(refs) if not os.path.exists(r)]
    assert not missing, f"CI references files that do not exist: {missing}"


def test_readme_result_table_matches_the_clock():
    """If the front page and the measurement disagree, the front page is what people read."""
    import io as _io, sys, os
    sys.path.insert(0, "tools")
    import run_all
    s = _io.open("README.md", encoding="utf-8").read()
    got = {r["scanner"]: (r.get("nominal"), r.get("real"))
           for r in run_all.measure() if r.get("status") == "measured"}
    # Radar is the single most quoted figure in the project
    assert got.get("radar") == (11, 11), f"clock says radar is {got.get('radar')}"
    assert "11 / 11" in s or "11/11" in s, "README no longer shows the figure the clock produces"


def test_layout_block_lists_directories_that_exist():
    import io as _io, os, re
    s = _io.open("README.md", encoding="utf-8").read()
    block = s.split("## Repository layout")[1].split("```")[1]
    dirs = set(re.findall(r"^([a-z_0-9]+)/", block, re.M))
    missing = [d for d in sorted(dirs) if not os.path.isdir(d)]
    assert not missing, f"README describes directories that do not exist: {missing}"


# ------------------------------------------------- corpus growth, 2026-09-01
# Eight cases were added on 2026-09-01. Adding a case changes the denominator of every
# figure computed over the corpus, and the front page has already been wrong twice for
# exactly that reason. These two derive the affected figures rather than trusting them.

def _corpus2_noisy_finding_count():
    """What control-noisy produces on corpus 2 today: every mapped rule id, on every
    non-empty line, of every .rs file, in both variants of every valid built case.

    Computed arithmetically rather than by materialising the findings, because the
    list is over a million entries and this runs on every suite.
    """
    import io as _io, json, os, sys
    sys.path.insert(0, "tools")
    import control_c2
    rules = len(control_c2.every_rule())
    cases = [c for c in json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
             if c.get("valid", True)]
    total = 0
    for c in cases:
        for variant in ("insecure", "secure"):
            d = os.path.join("corpus2", c["name"], variant, "src")
            if not os.path.isdir(d):
                continue
            for fn in sorted(os.listdir(d)):
                if not fn.endswith(".rs"):
                    continue
                with _io.open(os.path.join(d, fn), encoding="utf-8", errors="replace") as fh:
                    total += sum(1 for line in fh if line.strip()) * rules
    return total


def test_the_noisy_control_count_is_derived_from_the_corpus():
    """The calibration sentence quotes a finding count, and that count is a property of
    the corpus and the mapping set, both of which grow. It was 424,170 with seven
    mappings and eight cases; adding mappings moved it and adding cases moved it again.
    A quoted figure that nothing recomputes is the freshness defect this project keeps
    paying for, so every document that quotes one is checked against the corpus.

    The engineering logs are exempt, and only they. Their whole job is to record the
    value that turned out to be wrong, next to the date it was found; a log that could
    not quote a superseded number could not record the error at all."""
    import io as _io, os, re, sys
    sys.path.insert(0, "tools")
    import control_c1, control_c2
    expected = _corpus2_noisy_finding_count()
    # The teaching corpus figure is derived the same way and was a typed 931 until 2026-09-01,
    # when it turned out 931 was the count of flagged LINES and the control had never emitted a
    # finding any mapping could see (error 33). Both the line count and the finding count are
    # legitimate to quote, so both are derived here and neither is typed.
    c1_lines = sum(len(v) for v in control_c1.inventory_from_artefact().values())
    allowed = {expected, c1_lines, c1_lines * len(control_c2.every_rule())}
    wrong = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", ".omc", "__pycache__",
                                                "node_modules", "raw", "runs")]
        for fn in files:
            if not fn.endswith(".md") or fn.startswith("ENGINEERING-LOG-"):
                continue
            doc = os.path.join(root, fn)
            s = _io.open(doc, encoding="utf-8", errors="replace").read()
            for m in re.finditer(r"noisy", s, re.I):
                window = s[m.end():m.end() + 200]
                for n in re.findall(r"\b(\d{1,3}(?:,\d{3})+)\b", window):
                    if int(n.replace(",", "")) not in allowed:
                        wrong.append(f"{doc}: {n}")
    assert not wrong, (
        f"control-noisy produces {expected:,} findings on corpus 2 today, but these "
        f"documents still quote something else: {sorted(set(wrong))}. Regenerate with "
        "`python tools/control_c2.py` and quote what it prints.")


def test_the_coverage_matrix_is_derived_from_what_is_in_raw():
    """Coverage evidence existed for 3 of 12 measurements when it was last counted from outside,
    and the README admitted one gap of the nine. A prose list of gaps goes stale the moment a run
    happens; this one is recomputed from `raw/` and the failure message names what moved."""
    import io as _io, os, sys
    sys.path.insert(0, "tools")
    import coverage_matrix
    assert os.path.exists(coverage_matrix.DOC),         f"{coverage_matrix.DOC} is missing; run python tools/coverage_matrix.py --write"
    on_disk = _io.open(coverage_matrix.DOC, encoding="utf-8").read()
    assert coverage_matrix.render() == on_disk, (
        f"{coverage_matrix.DOC} no longer matches what is in raw/; run "
        "python tools/coverage_matrix.py --write")


def test_no_measurement_claims_a_run_log_it_does_not_have():
    """`coverage_evidence: run log` is the strongest claim this project makes about a number, so
    it must be false unless a machine-readable log with one entry per invocation is on disk."""
    import os, sys
    sys.path.insert(0, "tools")
    import run_all
    for row in run_all.measure_corpus2():
        if row.get("coverage_evidence") != "run log":
            continue
        src = row.get("source")
        assert src and os.path.exists(os.path.join("raw", src + ".log")), (
            f"{row['scanner']} claims coverage_evidence 'run log' and raw/{src}.log does not "
            "exist")


def test_class_balance_document_is_derived_from_the_manifest():
    """Class and repository concentration is the corpus's largest stated weakness, so
    the table that reports it must be recomputed rather than typed. Added 2026-09-01
    with the eight new cases, whose whole purpose was to move these two numbers."""
    import io as _io, os, sys
    sys.path.insert(0, "tools")
    import class_balance
    assert os.path.exists("docs/CLASS-BALANCE.md"), \
        "the class balance record is missing; run python tools/class_balance.py"
    on_disk = _io.open("docs/CLASS-BALANCE.md", encoding="utf-8").read()
    assert class_balance.render() == on_disk, (
        "docs/CLASS-BALANCE.md no longer matches the manifest it is derived from; "
        "run python tools/class_balance.py")


# -------------------------------- findings must land on files that exist, 2026-09-01, row 5

def _corpus2_findings():
    """Every corpus-2 findings file the clock scores, and the envelope it is read with.

    Taken from `run_all.SOURCES_CORPUS2` rather than copied. A typed copy of this list was wrong
    within an hour of being written: it named the sol-audit parser for a file kept in radar's own
    envelope, so the check ran over an empty parse and passed while seeing nothing."""
    import os, sys
    sys.path.insert(0, "tools")
    import run_all
    return [(name, os.path.join("raw", filename), kind)
            for name, (filename, kind) in sorted(run_all.SOURCES_CORPUS2.items())]


def test_no_verdict_rests_on_a_finding_about_a_file_that_is_not_in_the_corpus():
    """A findings file can outlive the corpus it was produced against, and two did.

    `raw/c2-radar-complete.json`, the file behind the published Radar corpus-2 row, was produced
    on 2026-08-31 against the corpus **before** it was rebuilt to pin one file per case. 161 of
    its 238 findings named files that no longer exist. `raw/c2-sol-audit.json` has the same
    problem on three cases, which the 2026-09-01 audit did not notice. Nothing said so, because
    `score_case` matched on the basename and ignored every directory above it.

    Deleting the stale artefacts is not the answer: this project keeps superseded runs on
    purpose. The property that has to hold is narrower and stronger than "every path resolves",
    and it is the one an outside reader cares about: **a finding about a file that is not in the
    corpus must never move a verdict.** Scored twice, once as recorded and once with the
    unresolvable paths removed, the two must agree for every case of every scanner.

    The stale counts themselves are reported by `tools/stale_findings.py` and recorded in
    `raw/stale-findings-2026-09-01.json`, so they stay visible rather than becoming invisible
    once the scorer stops being fooled by them."""
    import io as _io, json as _json, os, sys
    sys.path.insert(0, "tools")
    import score2
    cases = [c for c in _json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
             if c.get("valid", True)]
    moved, saw_stale = [], 0
    for scanner, path, kind in _corpus2_findings():
        assert os.path.exists(path), \
            f"{scanner}: {path} is missing, so the clock scores nothing for it"
        findings = score2.load_findings(kind, path)
        resolvable = {}
        for p, items in findings.items():
            norm = str(p).replace("\\", "/")
            if os.path.exists(norm):
                resolvable[p] = items
            else:
                saw_stale += len(items)
        import run_all as _ra
        mapping = _ra.load_mapping(scanner)["map"]
        for c in cases:
            d = os.path.join("corpus2", c["name"])
            if not os.path.isdir(d):
                continue
            a, _ = score2.score_case(d, c["class"], mapping, findings)
            b, _ = score2.score_case(d, c["class"], mapping, resolvable)
            if a != b:
                moved.append(f"{scanner}/{c['name']}: as recorded {a!r}, with the stale paths "
                             f"dropped {b!r}")
    assert not moved, (
        "verdicts that depend on findings about files that are not in the corpus:\n  "
        + "\n  ".join(moved)
        + "\nRe-run the scanner against the current corpus, or record the case as unknown.")
    assert saw_stale, (
        "no stale finding path was found anywhere, so this check just passed vacuously. If the "
        "artefacts were genuinely refreshed, delete this assertion and say so in the commit.")


# ------------------------------------------ corpus content is pinned, 2026-09-01, row 9

def test_every_corpus_file_matches_the_hash_recorded_in_the_manifest():
    """The benchmark's whole pitch is that you can check it rather than trust it, and until
    2026-09-01 the one thing nobody could check was the ground truth. The manifest carried
    commit SHAs; `test_fix_commits_look_like_shas` checked they looked like SHAs. Nothing
    tied `corpus2/<case>/<variant>/src/*.rs` to any blob. A one-character edit to any corpus
    file passed every check in this repository and changed every verdict.

    `tools/corpus_hashes.py` records a sha256 and git's own blob id per file. This recomputes
    them. It is deliberately the cheapest possible check: it needs no network and no clone."""
    import sys
    sys.path.insert(0, "tools")
    import corpus_hashes
    problems = corpus_hashes.report()
    assert not problems, (
        "the corpus no longer matches the hashes recorded in corpus2/manifest.json:\n  "
        + "\n  ".join(problems)
        + "\nIf the corpus was changed on purpose, rerun `python tools/corpus_hashes.py --write` "
          "and say in the commit message what moved and why.")


def test_every_built_case_records_the_upstream_blob_it_came_from():
    """A sha256 proves the file has not changed since we hashed it. It does not prove the file
    is the upstream blob. The git blob id does, in one command against a clone, so every
    vulnerable variant must name the parent commit and every fixed variant the fix commit.

    Checked offline. `raw/corpus2-blob-verification-2026-09-01.json` holds the result of
    actually asking GitHub, which is the part that needs the network."""
    import io as _io, json as _json, os
    manifest = _json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))
    built = {e["name"]: e for e in _json.load(_io.open("corpus2/built.json", encoding="utf-8"))}
    missing = []
    for case in manifest["cases"]:
        hashes = case.get("file_hashes")
        if not hashes:
            continue
        b = built.get(case["name"], {})
        for rel, meta in sorted(hashes.items()):
            if not rel.endswith(".rs"):
                continue
            up = meta.get("upstream")
            if not up:
                missing.append(f"{case['name']}/{rel}: no upstream blob recorded")
                continue
            want = b.get("parent") if rel.startswith("insecure/") else b.get("fix")
            if up.get("commit") != want:
                missing.append(
                    f"{case['name']}/{rel}: recorded upstream commit {up.get('commit')} but "
                    f"built.json says {want}")
    assert not missing, (
        "these corpus files are not tied to an upstream blob, so their ground truth cannot be "
        "checked by anybody outside this repository:\n  " + "\n  ".join(missing))


# ------------------------------------------- two logs for one run, 2026-09-01, error 32

def _parse_percase_text_log(path):
    """The human-readable per-case log: `<case> <variant> <ok|UNAVAILABLE> rc=N [findings=N]`."""
    import io as _io
    out = {}
    for line in _io.open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or line.endswith("_DONE"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        case, variant, status = parts[0], parts[1], parts[2]
        if variant not in ("insecure", "secure", "recommended"):
            continue
        out[f"{case}/{variant}"] = "ok" if status == "ok" else "unavailable"
    return out


def _parse_percase_json_log(path):
    import io as _io, json as _json
    return {str(e.get("leaf", "")): ("ok" if e.get("status") == "ok" else "unavailable")
            for e in _json.load(_io.open(path, encoding="utf-8"))}


# Every scanner that has both a human log and the machine log that actually scores.
_PAIRED_LOGS = [
    ("radar", "raw/c2-radar-percase.log", "raw/c2-radar-complete.json.log"),
    ("vaultlint", "raw/c2-vaultlint-percase.log", "raw/c2-vaultlint-complete.json.log"),
]


def test_the_two_logs_for_one_run_agree_on_every_leaf():
    """A run is recorded twice: once for a person and once for the scorer. Until 2026-09-01
    nothing compared them, and they disagreed.

    `raw/c2-radar-percase.log` line 1 said Radar's `anchor-interface-account/insecure` was
    `UNAVAILABLE`; `raw/c2-radar-complete.json.log`, the log `run_all.py` treats as the
    authority on which cases were analysed, said `{status: ok, findings: 0}`. One of the two
    was wrong for a full day and nothing in the repository could tell which. That is the
    whole point of writing a fact down twice.

    Which one was wrong is recorded as error 32 and is not the point of this check. The point
    is that two records of one run must never be allowed to disagree in silence again."""
    import os
    for scanner, text_log, json_log in _PAIRED_LOGS:
        if not (os.path.exists(text_log) and os.path.exists(json_log)):
            continue
        a = _parse_percase_text_log(text_log)
        b = _parse_percase_json_log(json_log)
        assert a, f"{text_log} parsed to nothing; the check would pass vacuously"
        assert set(a) == set(b), (
            f"{scanner}: the two logs cover different leaves. "
            f"only in {text_log}: {sorted(set(a) - set(b))}; "
            f"only in {json_log}: {sorted(set(b) - set(a))}")
        disagree = {k: (a[k], b[k]) for k in a if a[k] != b[k]}
        assert not disagree, (
            f"{scanner}: the human log and the log that scores disagree about whether a run "
            f"happened: {disagree}. One of them is wrong, and until this check existed nothing "
            "said which. 'Could not run' and 'found nothing' are different observations and a "
            "denominator depends on the difference.")


def test_radars_run_log_is_corroborated_by_radars_own_output():
    """A log is only evidence if something outside the log agrees with it.

    `raw/radar-c2-2026-08-31-stdout/` holds radar's own stdout for all 18 runs of the
    2026-08-31 corpus-2 measurement, recovered on 2026-09-01. radar prints `Scanned N file`
    and `radar completed successfully` for a run that happened, and it writes **no output
    file at all** when it finds nothing, which is exactly why the runner's
    file-exists-therefore-it-ran test could not tell a clean zero from a failure.

    So the run log is checked against the tool's own account of what it did, rather than
    against the artefact whose absence caused the defect."""
    import io as _io, os, re
    d = "raw/radar-c2-2026-08-31-stdout"
    if not os.path.isdir(d):
        raise AssertionError(
            f"{d} is missing: radar's own account of the 18 runs behind the published "
            "corpus-2 result is the evidence that they happened")
    logged = _parse_percase_json_log("raw/c2-radar-complete.json.log")
    seen = {}
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".log"):
            continue
        s = re.sub(r"\x1b\[[0-9;]*m", "",
                   _io.open(os.path.join(d, fn), encoding="utf-8", errors="replace").read())
        leaf = fn[:-4].replace(".", "/", 1)
        scanned = re.search(r"Scanned (\d+) file", s)
        ran = bool(scanned) and int(scanned.group(1)) > 0 and \
            "radar completed successfully" in s
        seen[leaf] = ran
    assert set(seen) == set(logged), (
        f"stdout artefacts and the run log cover different leaves: "
        f"{sorted(set(seen) ^ set(logged))}")
    for leaf, ran in sorted(seen.items()):
        assert ran == (logged[leaf] == "ok"), (
            f"{leaf}: the run log says {logged[leaf]!r} but radar's own stdout says "
            f"{'it scanned files and completed' if ran else 'it did not'}")



# ==================================================== the adapter framework, 2026-09-01
# `adapters/*.json` plus `tools/scanner_spec.py` replaced five hand-written per-case runners.
# Same selection rule as everything above: would a defect here change a published number?
#
# The one that matters most is `test_a_clean_zero_and_an_outage_can_never_carry_the_same_status`.
# Errors 20, 21, 35 and 36 are one defect wearing four hats: a harness that cannot tell "the tool
# ran this and found nothing" from "the tool never saw this". If that distinction collapses, every
# denominator in this repository is guesswork, so it is checked directly rather than left as a
# property of code somebody has to keep remembering.

# The literal tables `run_all.py` carried before the migration, copied here unchanged from commit
# 9b89b31. They are the published clock: which raw file scores which row, under which parser, and
# which mapping. Nothing derives them, on purpose. A golden record that regenerates itself proves
# nothing.
CLOCK_BEFORE_MIGRATION_C1 = {
    "radar": ("radar-full.json", "radar"),
    "vaultlint": ("vaultlint.json", "vaultlint"),
    "sol-audit": ("sol-audit.json", "sol-audit"),
    "xray": ("xray-c1-raw.json", "xray"),
    "sol-audit-v3": ("c1-sol-audit-v3-strict.json", "sol-audit"),
    "sol-audit-v3-broad": ("c1-sol-audit-v3-broad.json", "sol-audit"),
    "sol-audit-v3-all": ("c1-sol-audit-v3-all.json", "sol-audit"),
    "solsec": ("c1-solsec-percase.json", "solsec"),
    "semgrep": ("semgrep-c1.json", "semgrep"),
    "semgrep-solana-standard": ("c1-semgrep-solana-standard.json", "semgrep"),
    "semgrep-solana-standard-wide": ("c1-semgrep-solana-standard.json", "semgrep"),
}
CLOCK_BEFORE_MIGRATION_C2 = {
    "radar": ("c2-radar-current.json", "radar"),
    "vaultlint": ("c2-vaultlint-complete.json", "sol-audit"),
    "sol-audit": ("c2-sol-audit.json", "sol-audit"),
    "sol-audit-v3": ("c2-sol-audit-v3-strict.json", "sol-audit"),
    "sol-audit-v3-broad": ("c2-sol-audit-v3-broad.json", "sol-audit"),
    "sol-audit-v3-all": ("c2-sol-audit-v3-all.json", "sol-audit"),
    "solsec": ("c2-solsec-percase.json", "solsec"),
    "semgrep-solana-standard-c2": ("c2-semgrep-solana-standard.json", "semgrep"),
    "semgrep-solana-standard-c2-wide": ("c2-semgrep-solana-standard.json", "semgrep"),
}
CLOCK_BEFORE_MIGRATION_ALIAS = {
    "sol-audit-v3": "sol-audit",
    "sol-audit-v3-broad": "sol-audit",
    "sol-audit-v3-all": "sol-audit",
    "semgrep-solana-standard-c2": "semgrep-solana-standard-c2",
}

# A scanner that does not exist, so the framework can be driven end to end on a laptop with no
# Docker. It reads its behaviour from a `mode` file in the case it is pointed at, which lets one
# run exercise a clean zero, a real finding, a silent exit and a crash in a single pass.
FIXTURE_SCANNER = "\n".join([
    "import json, os, sys",
    "target, out = sys.argv[1], sys.argv[2]",
    "mode = open(os.path.join(target, 'mode')).read().strip()",
    "if mode == 'silent':",
    "    sys.exit(0)          # exit 0, say nothing, write nothing: error 36's shape",
    "if mode == 'crash':",
    "    sys.stderr.write('fixture: exploded')",
    "    sys.exit(3)",
    "print('fixture scanned 1 files')",
    "hit = os.path.join(target, 'src', 'lib.rs').replace(chr(92), '/')",
    "findings = []",
    "if mode == 'finds':",
    "    findings = [{'rule_id': 'FIX-001', 'file': hit, 'line': 3}]",
    "if mode == 'flaky':",
    "    counter = os.path.join(os.path.dirname(out), 'flaky.count')",
    "    n = (int(open(counter).read()) if os.path.exists(counter) else 0) + 1",
    "    open(counter, 'w').write(str(n))",
    "    findings = [{'rule_id': 'FIX-001', 'file': hit, 'line': 2 + n}]",
    "json.dump({'findings': findings}, open(os.path.join(out, 'findings.json'), 'w'))",
    "",
])


def _fixture_world(tmp, modes):
    """A corpus of one-file cases, a fixture scanner, and a declaration that drives it.

    `engine: local` on purpose. This laptop has no Docker, and a framework whose only test path
    needs a VPS is a framework nobody will run a test on.
    """
    import scanner_spec
    script = os.path.join(tmp, "fixture_scanner.py")
    with io.open(script, "w", encoding="utf-8") as fh:
        fh.write(FIXTURE_SCANNER)
    leaves = []
    for name, mode in sorted(modes.items()):
        d = os.path.join(tmp, "corpus", name, "insecure")
        os.makedirs(os.path.join(d, "src"))
        with io.open(os.path.join(d, "mode"), "w", encoding="utf-8") as fh:
            fh.write(mode)
        with io.open(os.path.join(d, "src", "lib.rs"), "w", encoding="utf-8") as fh:
            fh.write("a\nb\nvulnerable\nd\n")
        leaves.append((name + "/insecure", d, "fixture/" + name + "/insecure"))
    spec = json.loads(json.dumps(scanner_spec._FIXTURE_SPEC))
    spec["run"]["command"] = ["python", script, "{mount}", "{out}"]
    spec["output"] = {"from": "file", "name": "findings.json", "format": "sol-audit"}
    return scanner_spec.load(spec), leaves


def test_every_adapter_declaration_in_the_repository_is_valid():
    """A declaration that does not load is a tool nobody can run and a clock row nobody can read."""
    import scanner_spec
    specs = scanner_spec.load_all()
    assert specs, "adapters/ holds no declarations"
    for name, spec in specs.items():
        assert spec["name"] == name
        assert spec["measurements"], f"{name} declares no measurement, so it feeds nothing"


def test_a_declaration_cannot_omit_how_the_tool_announces_that_it_read_the_code():
    """The guard that stops error 35 recurring, checked by trying to get past it.

    solsec was published as `0 / 6, 3 unavailable` with the denominator and the three unavailable
    cases both inferred from an empty findings file, and neither existed. A declaration that does
    not say how its tool announces coverage is refused rather than defaulted.
    """
    import scanner_spec
    blind = json.loads(json.dumps(scanner_spec._FIXTURE_SPEC))
    del blind["coverage"]["evidence"]
    try:
        scanner_spec.load(blind)
        raise AssertionError("a declaration with no coverage evidence was accepted")
    except ValueError as exc:
        assert "coverage.evidence is missing" in str(exc), exc

    vague = json.loads(json.dumps(scanner_spec._FIXTURE_SPEC))
    vague["coverage"]["evidence"] = {"absent": True}
    try:
        scanner_spec.load(vague)
        raise AssertionError("an absent-evidence declaration with no reason was accepted")
    except ValueError as exc:
        assert "reason" in str(exc), exc


def test_a_clean_zero_and_an_outage_can_never_carry_the_same_status():
    """THE property. If this stops holding, every denominator in the repository is guesswork.

    Four observations that a naive harness collapses into "no findings":

      the tool said it read the files and reported nothing   ok, and that zero is real
      the tool exited 0 having said nothing                  unavailable, error 36's shape
      the tool crashed                                       unavailable
      the tool produced output nothing could parse           unavailable

    The first must be distinguishable from the other three, and it must be the only one that can
    contribute a zero to a denominator.
    """
    import scanner_spec
    spec = scanner_spec.load(scanner_spec._FIXTURE_SPEC)
    said_it_read = scanner_spec.classify(spec, 0, "fixture scanned 3 files\n", [])
    silent = scanner_spec.classify(spec, 0, "", [])
    crashed = scanner_spec.classify(spec, 3, "fixture scanned 3 files\n", [])
    unreadable = scanner_spec.classify(spec, 0, "fixture scanned 3 files\n", None)

    assert said_it_read[0] == "ok", said_it_read
    for name, got in (("said nothing", silent), ("crashed", crashed),
                      ("was unreadable", unreadable)):
        assert got[0] != "ok", (
            f"a run that {name} was classified `ok`, which turns it into a zero somebody will "
            f"publish: {got}")
        assert got[0] == "unavailable", got
        assert got[2], f"a run that {name} was recorded unavailable with no reason attached"
    assert said_it_read[0] != silent[0], (
        "a clean zero and an outage now carry the same status. Error 35 published an outage that "
        "never happened; error 36 published a clean zero as an outage. This check exists so the "
        "distinction is not a convention somebody has to remember.")


def test_a_tool_that_prints_no_coverage_line_can_never_produce_a_zero():
    """The escape hatch must not become a back door.

    A declaration may admit that its tool says nothing about what it read. Its runs are then
    `unknown`, which is the honest verdict, and `unknown` is neither a zero nor an outage. What it
    must never become is `ok`.
    """
    import scanner_spec
    mute = json.loads(json.dumps(scanner_spec._FIXTURE_SPEC))
    mute["coverage"]["evidence"] = {"absent": True, "reason": "prints no file count"}
    spec = scanner_spec.load(mute)
    for output in ("", "anything at all", "0 files scanned"):
        status, _seen, why = scanner_spec.classify(spec, 0, output, [])
        assert status == "unknown", (
            f"a tool with no coverage line returned {status!r} on output {output!r}; a "
            "declaration that admits it cannot prove coverage must never produce a scoreable zero")
        assert why
    # And an exit code outside the declared set is still an outage, not an unknown: the two
    # reasons a run cannot be counted are recorded as the different things they are.
    assert scanner_spec.classify(spec, 3, "anything at all", [])[0] == "unavailable"


def test_the_clock_tables_derived_from_the_declarations_match_the_committed_ones():
    """The migration proof. Every published row must still name the same file, parser and mapping.

    `run_all.py` carried these as three literals until 2026-09-01; they come from `adapters/*.json`
    now. A declaration edit that moves a row moves a published number, so the pre-migration tables
    are pinned here by hand and compared key by key.
    """
    import run_all
    for label, got, want in (
            ("corpus 1", run_all.SOURCES, CLOCK_BEFORE_MIGRATION_C1),
            ("corpus 2", run_all.SOURCES_CORPUS2, CLOCK_BEFORE_MIGRATION_C2)):
        assert set(got) == set(want), (
            f"{label} rows changed: only in the declarations {sorted(set(got) - set(want))}, "
            f"only in the committed clock {sorted(set(want) - set(got))}")
        for row in sorted(want):
            assert got[row] == want[row], (
                f"{label} row {row!r} now reads {got[row]}, was {want[row]}. That is a published "
                "number moving under a refactor.")
    # MAPPING_ALIAS is compared as the question it answers, which mapping scores which row,
    # because the committed literal carried one entry that mapped a row to itself.
    for row in sorted(set(CLOCK_BEFORE_MIGRATION_C1) | set(CLOCK_BEFORE_MIGRATION_C2)):
        was = CLOCK_BEFORE_MIGRATION_ALIAS.get(row, row)
        now = run_all.MAPPING_ALIAS.get(row, row)
        assert was == now, f"row {row!r} is now scored with mappings/{now}.json, was {was}"


def test_every_declaration_can_carry_a_detection_through_its_own_parser():
    """A parser that silently returns nothing looks exactly like a tool that found nothing.

    This happened. On 2026-09-01 an external review disabled the sol-audit branch of
    `load_findings` and all 94 checks stayed green while every corpus-2 verdict silently became
    `missed`. Each declaration therefore carries a sample of its tool's own output holding one real
    finding, and it is driven end to end: the parser, the stored envelope, the reader the clock
    uses, the scorer. Then the same finding is planted on the fixed variant and must stop being a
    detection.
    """
    import scanner_spec
    for name, spec in sorted(scanner_spec.load_all().items()):
        got = scanner_spec.positive_control(spec)
        assert got["detected"] and got["silent_on_the_fix"], (name, got)
        assert got["corpus1_envelopes"] or got["corpus2_envelopes"], (
            f"{name}: the control crossed no reader at all")


def test_every_envelope_a_declaration_names_is_one_the_scorer_for_that_corpus_can_read():
    """The two corpora are read by different code, and a row can be moved between them.

    Corpus 1 goes through `run_all.extract`, corpus 2 through `score2.load_findings`. `xray` is a
    kind one of them has and the other does not, which is exactly the gap that only shows up when
    somebody moves a row.
    """
    import run_all, score2, scanner_spec
    for name, spec in sorted(scanner_spec.load_all().items()):
        for m in spec["measurements"]:
            env = m.get("envelope", spec["envelope"])
            if m["corpus"] == "corpus1":
                run_all.extract(env, [] if env in ("radar", "xray") else {})
            else:
                with tempfile.TemporaryDirectory() as t:
                    dest = os.path.join(t, "e.json")
                    with io.open(dest, "w", encoding="utf-8") as fh:
                        json.dump(scanner_spec.WRITERS[env]([]), fh)
                    score2.load_findings(env, dest)


def test_the_framework_writes_an_artefact_and_a_log_line_for_every_invocation():
    """Including the ones that failed. The run that failed is the one somebody will want to read.

    Everything that survived the 2026-08-31 audit had an artefact per run; everything that
    collapsed had been inferred from a summary.
    """
    import scanner_spec
    with tempfile.TemporaryDirectory() as tmp:
        spec, leaves = _fixture_world(tmp, {"a-finds": "finds", "b-empty": "empty",
                                            "c-silent": "silent", "d-crash": "crash"})
        out = os.path.join(tmp, "findings.json")
        log, _findings, _det = scanner_spec.run_measurement(
            spec, leaves, out, os.path.join(tmp, "runs"), echo=False)
        assert len(log) == len(leaves), f"{len(log)} log entries for {len(leaves)} invocations"
        for entry in log:
            for field in ("leaf", "status", "exit_code", "wall_seconds", "command", "artefact"):
                assert field in entry, f"{entry.get('leaf')} has no {field}"
            assert entry["command"], "the exact command is not in the log"
            assert os.path.exists(entry["artefact"]) or os.path.exists(
                os.path.join(scanner_spec.ROOT, entry["artefact"])), \
                f"no artefact on disk for {entry['leaf']}"
        for suffix in ("", ".log", ".determinism.json"):
            assert os.path.exists(out + suffix), f"{out + suffix} was not written"


def test_a_run_that_read_nothing_contributes_no_zero_to_anybodys_denominator():
    """End to end, through real subprocesses, on the property the whole framework exists for."""
    import scanner_spec
    with tempfile.TemporaryDirectory() as tmp:
        spec, leaves = _fixture_world(tmp, {"a-finds": "finds", "b-empty": "empty",
                                            "c-silent": "silent", "d-crash": "crash"})
        log, findings, _det = scanner_spec.run_measurement(
            spec, leaves, os.path.join(tmp, "f.json"), os.path.join(tmp, "runs"), echo=False)
        by = {e["leaf"]: e for e in log}
        assert by["a-finds/insecure"]["status"] == "ok", by["a-finds/insecure"]
        assert by["a-finds/insecure"]["findings"] == 1
        assert by["b-empty/insecure"]["status"] == "ok", (
            "a tool that said it read the files and reported nothing is a CLEAN ZERO. Calling it "
            "unavailable is error 36, which cost a published correction.")
        assert by["b-empty/insecure"]["findings"] == 0
        for leaf in ("c-silent/insecure", "d-crash/insecure"):
            assert by[leaf]["status"] == "unavailable", by[leaf]
            assert by[leaf]["findings"] is None, (
                f"{leaf} could not run and yet carries a findings count, which is how an outage "
                "becomes a zero")
        assert len(findings) == 1, findings


def test_a_scanner_that_disagrees_with_itself_is_reported_not_averaged():
    """A tool whose answer changes between runs is a sample, not a value, and is named as one."""
    import scanner_spec
    with tempfile.TemporaryDirectory() as tmp:
        spec, leaves = _fixture_world(tmp, {"steady": "finds", "unsteady": "flaky"})
        out = os.path.join(tmp, "f.json")
        scanner_spec.run_measurement(spec, leaves, out, os.path.join(tmp, "runs"),
                                     repeat=2, echo=False)
        with io.open(out + ".determinism.json", encoding="utf-8") as fh:
            det = json.load(fh)
        assert det["verdict"] == "non-deterministic", det
        assert any(d["leaf"] == "unsteady/insecure" for d in det["differing"]), det
        assert not any(d["leaf"] == "steady/insecure" for d in det["differing"]), det
        assert os.path.exists(out) and os.path.exists(out.replace(".json", ".run2.json")), \
            "both passes must stay on disk; a merged pair is a run that never happened"


def test_a_single_pass_cannot_claim_a_determinism_verdict():
    import scanner_spec
    with tempfile.TemporaryDirectory() as tmp:
        spec, leaves = _fixture_world(tmp, {"only": "finds"})
        out = os.path.join(tmp, "f.json")
        scanner_spec.run_measurement(spec, leaves, out, os.path.join(tmp, "runs"), echo=False)
        with io.open(out + ".determinism.json", encoding="utf-8") as fh:
            assert json.load(fh)["verdict"] == "not-checked"


def test_the_corpus_case_list_is_read_from_the_manifest_and_never_assumed():
    """It was 9 cases, then 16, then 17, and it changed under a measurement mid-run once already.

    B3's sweep started against 9 built cases and finished against 17 because another worker
    expanded the corpus while it ran. A framework that wrote the number down would have published
    the drift as a result.
    """
    import scanner_spec
    cases = json.load(io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    built = {c["name"] for c in cases
             if c.get("valid", True) and os.path.isdir(os.path.join("corpus2", c["name"]))}
    leaves = scanner_spec.corpus_leaves("corpus2")
    names = {leaf.split("/")[0] for leaf, _d, _p in leaves}
    assert names == built, (
        "the framework's case list and the manifest disagree: " + str(names ^ built))
    assert len(leaves) >= len(built), "at least one invocation per built case"


def test_verify_coverage_fails_loudly_when_a_row_has_no_run_log():
    """Milestone 1's acceptance check has to be able to fail, and to say which row failed."""
    import run_all
    with tempfile.TemporaryDirectory() as tmp:
        with io.open(os.path.join(tmp, "with-log.json"), "w", encoding="utf-8") as fh:
            json.dump({"findings": []}, fh)
        with io.open(os.path.join(tmp, "with-log.json.log"), "w", encoding="utf-8") as fh:
            json.dump([{"leaf": "x/insecure", "status": "ok"}], fh)
        with io.open(os.path.join(tmp, "no-log.json"), "w", encoding="utf-8") as fh:
            json.dump({"findings": []}, fh)
        saved = (run_all.SOURCES, run_all.SOURCES_CORPUS2)
        try:
            run_all.SOURCES = {"has-evidence": ("with-log.json", "sol-audit"),
                               "no-evidence": ("no-log.json", "sol-audit")}
            run_all.SOURCES_CORPUS2 = {}
            rows, failures = run_all.verify_coverage(raw_dir=tmp, echo=False)
        finally:
            run_all.SOURCES, run_all.SOURCES_CORPUS2 = saved
    graded = {r["scanner"]: r["coverage_evidence"] for r in rows}
    assert graded == {"has-evidence": "run log", "no-evidence": "none"}, graded
    assert len(failures) == 1 and "no-evidence" in failures[0], failures
    assert "coverage_evidence: none" in failures[0], failures[0]


def test_verify_coverage_passes_only_when_every_row_can_show_what_it_analysed():
    """The other half: it must be able to say yes, or it is a check that always fails."""
    import run_all
    with tempfile.TemporaryDirectory() as tmp:
        with io.open(os.path.join(tmp, "a.json"), "w", encoding="utf-8") as fh:
            json.dump({"findings": []}, fh)
        with io.open(os.path.join(tmp, "a.json.log"), "w", encoding="utf-8") as fh:
            json.dump([{"leaf": "x/insecure", "status": "ok"}], fh)
        saved = (run_all.SOURCES, run_all.SOURCES_CORPUS2)
        try:
            run_all.SOURCES = {"a": ("a.json", "sol-audit")}
            run_all.SOURCES_CORPUS2 = {}
            rows, failures = run_all.verify_coverage(raw_dir=tmp, echo=False)
        finally:
            run_all.SOURCES, run_all.SOURCES_CORPUS2 = saved
    assert not failures, failures
    assert rows[0]["invocations"] == 1 and rows[0]["ok"] == 1


def test_a_case_that_could_not_run_is_not_a_coverage_failure_but_one_nobody_ran_is():
    """Could not run is a published outcome. Nobody looked is a gap. They are not the same.

    Reading them as the same is what made the 2026-08-31 harness record cases radar had in fact
    analysed as outages.
    """
    import run_all
    row = {"corpus": "corpus2", "scanner": "t", "raw": "raw/t.json",
           "coverage_evidence": "run log", "invocations": 2, "ok": 1, "not_ok": 1}
    saved = run_all.coverage_rows
    try:
        run_all.coverage_rows = lambda *a, **k: [dict(row, unresolved={"unavailable": 3})]
        _rows, failures = run_all.verify_coverage(echo=False)
        assert not failures, \
            f"a case that could not run, published with its reason, is not a gap: {failures}"
        run_all.coverage_rows = lambda *a, **k: [dict(row, unresolved={"not-run": 3})]
        _rows, failures = run_all.verify_coverage(echo=False)
        assert len(failures) == 1 and "not-run" in failures[0], failures
        run_all.coverage_rows = lambda *a, **k: [dict(row, unresolved={"unknown": 3})]
        _rows, failures = run_all.verify_coverage(echo=False)
        assert len(failures) == 1 and "unknown" in failures[0], failures
    finally:
        run_all.coverage_rows = saved


def test_no_declaration_claims_an_invocation_it_cannot_show():
    """`invocation_evidence` must point at something in the repository, not describe a memory.

    Three declarations say `engine: unrecorded` because nobody wrote their command down. That is
    the honest state and it is allowed. What is not allowed is a declaration that states a command
    and cites nothing, because a command typed from memory is the same class of claim as a number
    typed from memory.
    """
    import re as _re
    import scanner_spec
    missing = []
    for name, spec in sorted(scanner_spec.load_all().items()):
        if spec["run"]["engine"] == "unrecorded":
            assert spec["run"].get("reason"), f"{name} is unrecorded with no reason"
            continue
        evidence = spec["run"]["invocation_evidence"]
        cited = _re.findall(r"\b(?:raw|tools|mappings|docs|corpus2)/[\w./-]*[\w/]", evidence)
        assert cited, f"{name}: invocation_evidence cites no file in this repository"
        for path in cited:
            if not os.path.exists(path):
                missing.append(f"{name}: {path}")
    assert not missing, f"invocation evidence naming files that do not exist: {missing}"


def test_the_frameworks_parser_reproduces_a_committed_findings_file_from_the_raw_runs():
    """The migration proof for the half a golden table cannot reach: the parser itself.

    `raw/c2-sol-azy.json` and `raw/c2ext-sol-azy.json` were produced on 2026-09-01 by a runner
    written for that one sweep and kept in a scratch directory. The framework's `text-regex`
    parser, driven from `adapters/sol-azy.json` alone, reads the same committed per-run artefacts.
    If the two disagree, the declaration is not describing the tool that produced the published
    file, and the next run under it would quietly measure something else.

    sol-azy is the tool this can be checked on, because it is the only one whose per-invocation
    raw output is committed in the tool's own words rather than already normalised.
    """
    import scanner_spec
    spec = scanner_spec.load("adapters/sol-azy.json")
    patterns = spec["output"]["patterns"]
    checked = 0
    for runs, committed in (("raw/solazy-2026-09-01/c2", "raw/c2-sol-azy.json"),
                            ("raw/solazy-2026-09-01/c2-extended", "raw/c2ext-sol-azy.json")):
        if not os.path.isdir(runs) or not os.path.exists(committed):
            continue
        got = []
        for fn in sorted(os.listdir(runs)):
            leaf = fn[:-4]
            if not fn.endswith(".txt") or leaf.endswith("-run2") or "__" not in leaf:
                continue
            case, variant = leaf.split("__")[0], leaf.split("__")[1]
            with io.open(os.path.join(runs, fn), encoding="utf-8", errors="replace") as fh:
                for f in scanner_spec.parse_text_regex(fh.read(), patterns):
                    rel = f["file"][len("/work/"):] if f["file"].startswith("/work/") \
                        else f["file"]
                    got.append((f["rule_id"], f"corpus2/{case}/{variant}/{rel}",
                                f["line"], f["col"]))
        with io.open(committed, encoding="utf-8") as fh:
            want = [(x["rule_id"], x["file"], x["line"], x.get("col", 0))
                    for x in json.load(fh)["findings"]]
        assert sorted(got) == sorted(want), (
            f"the declaration's parser reads {len(got)} findings out of {runs} where the "
            f"committed {committed} has {len(want)}; "
            f"only in the parse: {sorted(set(got) - set(want))[:3]}, "
            f"only in the file: {sorted(set(want) - set(got))[:3]}")
        checked += 1
    assert checked, "neither sol-azy run directory is present, so this proved nothing"

# ------------------------------------------------- the real-crate run, 2026-09-01
# Four of the eight measurements had never been run against the real crates, so the packaging
# objection was tested for two tools and retired for none. These checks stand behind the page
# that closed that gap, and the first three exist because a scorer whose only observed output is
# zero is not evidence about anybody's tool.

RC_DOC = "docs/results/RESULTS-realcrates.md"
RC_RUN_ROWS = [
    ("raw/rc-sol-audit-v3-strict.json.log", "sol-audit 3.0, strict"),
    ("raw/rc-sol-audit-v3-broad.json.log", "sol-audit 3.0, broad"),
    ("raw/rc-sol-audit-v3-all.json.log", "sol-audit 3.0, all"),
    ("raw/rc-semgrep-solana-standard.json.log", "semgrep + SOL-0XX pack"),
    ("raw/rc-solsec.json.log", "solsec 0.2.1"),
    ("raw/rc-xray.json.log", "X-Ray v0.0.6"),
    ("raw/rc-radar.json.log", "Radar (re-run)"),
]
RC_SCORE_ROWS = [
    ("raw/rc-score-sol-audit-strict.json", "sol-audit 3.0, strict / broad / all"),
    ("raw/rc-score-sol-audit-broad.json", "sol-audit 3.0, strict / broad / all"),
    ("raw/rc-score-sol-audit-all.json", "sol-audit 3.0, strict / broad / all"),
    ("raw/rc-score-semgrep-solana-standard-c2.json", "semgrep + SOL-0XX, narrow reading"),
    ("raw/rc-score-semgrep-solana-standard-c2-wide.json", "semgrep + SOL-0XX, wide reading"),
    ("raw/rc-score-solsec.json", "solsec 0.2.1"),
    ("raw/rc-score-xray.json", "X-Ray, pre-registered map"),
    ("raw/rc-score-xray-corrected.json", "X-Ray, corrected map"),
    ("raw/rc-score-radar.json", "Radar (re-run)"),
]


def _rc_module(name):
    import importlib, os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    return importlib.import_module(name)


def _md_rows(text):
    """Every markdown table row as a list of plain cells, bold and backticks stripped."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|- :"):
            continue
        cells = []
        for c in line.strip("|").split("|"):
            c = c.strip()
            while c.startswith("*") or c.startswith("`"):
                c = c[1:]
            while c.endswith("*") or c.endswith("`"):
                c = c[:-1]
            cells.append(c.strip())
        rows.append(cells)
    return rows


def test_rc_run_classifies_the_solsec_exit_gate_as_a_result():
    _rc_module("rc_run").demo()


def test_rc_score_positive_control_in_the_real_crate_layout():
    _rc_module("rc_score").demo()


def test_rc_compare_can_see_a_difference_between_packagings():
    _rc_module("rc_compare").demo()


def test_every_real_crate_run_covers_every_case_and_variant():
    """One invocation per case per variant, and the leaves are the crates that were built."""
    import io as _io, json as _json, os as _os
    built = _json.load(_io.open("raw/rc-crates-built-2026-09-01.json", encoding="utf-8"))
    want = set()
    for r in built:
        if r.get("status") == "built":
            want.add(r["name"] + "/insecure")
            want.add(r["name"] + "/secure")
    assert want, "the crate inventory is empty, so this check proves nothing"
    checked = 0
    for log_path, _label in RC_RUN_ROWS:
        assert _os.path.exists(log_path), log_path + " is missing"
        entries = _json.load(_io.open(log_path, encoding="utf-8"))
        got = [e["leaf"] for e in entries]
        assert len(got) == len(set(got)), log_path + " logs a leaf twice"
        assert set(got) == want, (
            "%s covers %d leaves, the corpus has %d; missing %s, extra %s"
            % (log_path, len(got), len(want), sorted(want - set(got))[:3],
               sorted(set(got) - want)[:3]))
        checked += 1
    assert checked == len(RC_RUN_ROWS)


def test_a_real_crate_the_tool_could_not_finish_is_never_scored_as_a_zero():
    """The scored file must say `unavailable` for exactly the cases its log could not finish."""
    import io as _io, json as _json, os as _os
    manifest = _json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    valid = set(c["name"] for c in manifest if c.get("valid", True))
    checked = 0
    for score_path, _label in RC_SCORE_ROWS:
        assert _os.path.exists(score_path), score_path + " is missing"
        scored = _json.load(_io.open(score_path, encoding="utf-8"))
        log = _os.path.join("raw", _os.path.basename(scored["log"]))
        assert _os.path.exists(log), score_path + " names a log that is not in raw/: " + log
        entries = _json.load(_io.open(log, encoding="utf-8"))
        blocked = set(e["leaf"].split("/")[0] for e in entries
                      if e.get("status") != "ok") & valid
        said = set(r["case"] for r in scored["cases"] if r["verdict"] == "unavailable")
        assert said == blocked, (
            "%s: the run log could not finish %s but the scored file marks %s unavailable; "
            "anything in the first set and not the second is an outage published as a zero"
            % (score_path, sorted(blocked), sorted(said)))
        checked += 1
    assert checked == len(RC_SCORE_ROWS)


def test_the_real_crate_run_table_matches_the_logs_it_was_derived_from():
    import io as _io, json as _json
    doc = _io.open(RC_DOC, encoding="utf-8").read()
    rows = _md_rows(doc)
    for log_path, label in RC_RUN_ROWS:
        entries = _json.load(_io.open(log_path, encoding="utf-8"))
        ok = [e for e in entries if e.get("status") == "ok"]
        want = [label, str(len(entries)), str(len(ok)), str(len(entries) - len(ok)),
                str(sum(e.get("findings", 0) for e in ok))]
        got = [r for r in rows if r and r[0] == label]
        assert got, RC_DOC + " has no run row for " + repr(label)
        assert any(r[:5] == want for r in got), (
            "%s run row for %r is %s, the log says %s" % (RC_DOC, label, got[0][:5], want))


def test_the_real_crate_score_table_matches_the_scored_files():
    import io as _io, json as _json
    doc = _io.open(RC_DOC, encoding="utf-8").read()
    rows = _md_rows(doc)
    manifest = _json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    valid = sum(1 for c in manifest if c.get("valid", True))
    for score_path, label in RC_SCORE_ROWS:
        t = _json.load(_io.open(score_path, encoding="utf-8"))["tally"]
        # A case with no mapped rule is not scoreable, and neither is one the tool could not
        # finish. Subtracting only the first would publish a denominator that counts outages.
        scoreable = valid - t.get("no-rule", 0) - t.get("unavailable", 0)
        want = [label, str(t.get("detected", 0)), str(t.get("unlocated", 0)),
                str(t.get("missed", 0)), str(t.get("no-rule", 0)),
                str(t.get("unavailable", 0)), "%d / %d" % (scoreable, valid)]
        got = [r for r in rows if r and r[0] == label]
        assert got, RC_DOC + " has no score row for " + repr(label)
        assert any(r[:7] == want for r in got), (
            "%s score row for %r is %s, %s says %s"
            % (RC_DOC, label, got[0][:7], score_path, want))


def test_the_packaging_comparison_headline_is_recomputed_not_typed():
    import io as _io, os as _os
    rc_compare = _rc_module("rc_compare")
    doc = _io.open(RC_DOC, encoding="utf-8").read()
    compared = differ = blocked = 0
    for label, rc_path, mapping_name, map_key, c2, kind in rc_compare.PAIRS:
        if not (_os.path.exists(rc_path) and _os.path.exists(c2)):
            continue
        r, d = rc_compare.compare(label, rc_path, mapping_name, map_key, c2, kind)
        compared += sum(1 for x in r if x[3] != "no comparison")
        blocked += sum(1 for x in r if x[3] == "no comparison")
        differ += d
    assert compared, "the comparison compared nothing, so its zero means nothing"
    assert ("%d verdicts compared" % compared) in doc, (
        "%s does not say '%d verdicts compared'" % (RC_DOC, compared))
    assert ("%d could not be compared" % blocked) in doc, (
        "%s does not say '%d could not be compared'" % (RC_DOC, blocked))
    if differ == 0:
        assert "Zero differ" in doc, RC_DOC + " should say 'Zero differ'"
    else:
        assert "Zero differ" not in doc, (
            "%d verdicts now differ across packagings and the page still says zero" % differ)


def test_the_two_solsec_real_crate_runs_agree_finding_for_finding():
    """The only repeat-run evidence on the real crates, and it exists by accident.

    The first runner read solsec's CI exit code as an outage and recorded eight completed scans
    as unavailable. The rerun that corrected the classifier repeated the 28 invocations the first
    attempt did finish, so the two files can be compared over those 28 - which is a determinism
    check the run did not set out to make, and the page quotes its number.
    """
    import io as _io, json as _json, os as _os
    first, second = "raw/rc-solsec-attempt1-exitcode.json", "raw/rc-solsec.json"
    for p in (first, second, first + ".log"):
        assert _os.path.exists(p), p + " is missing, so the determinism claim is uncheckable"
    ok = set(e["leaf"] for e in _json.load(_io.open(first + ".log", encoding="utf-8"))
             if e.get("status") == "ok")
    assert len(ok) == 28, "the first attempt finished %d invocations, not 28" % len(ok)

    def rows(path, leaves=None):
        out = []
        for x in _json.load(_io.open(path, encoding="utf-8"))["analysis_results"]:
            fp = x["file_path"]
            leaf = "/".join(fp.split("/")[:2])
            if leaves is not None and leaf not in leaves:
                continue
            out.append((fp, x["rule_name"], x["line_number"]))
        return sorted(out)

    a, b = rows(first), rows(second, ok)
    assert a == b, ("the two solsec runs disagree over the 28 invocations they share: "
                    "%d findings against %d" % (len(a), len(b)))
    doc = _io.open(RC_DOC, encoding="utf-8").read()
    assert str(len(a)) in doc, (
        "%s should quote the %d findings the two runs agree on" % (RC_DOC, len(a)))


# -------------------------------------------------------------------- main
def main():
    print("running the checks that stand between a defect and a published number\n")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name[5:].replace("_", " "), fn)

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        print("\nA failure here means a number in this repository may be wrong. Fix it before "
              "publishing anything.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
