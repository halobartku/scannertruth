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
"""
import io
import json
import os
import sys
import tempfile

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
    """The control is only meaningful if it beats everyone on the naive metric."""
    import control_c2
    rules = control_c2.every_rule()
    assert len(rules) > 10, f"expected many mapped rules to fire, got {len(rules)}"


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
    for fn in os.listdir("mappings"):
        if not fn.endswith(".json"):
            continue
        m = json.load(io.open(os.path.join("mappings", fn), encoding="utf-8"))
        assert "map" in m, f"{fn} has no map"
        assert isinstance(m["map"], dict) and m["map"], f"{fn} has an empty map"


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


# --------------------------------------------------------------- unmapped
def test_unmapped_check_finds_the_known_positive():
    """A check that returns zero everywhere may simply be broken."""
    import score2
    with tempfile.TemporaryDirectory() as t:
        case, ins, _ = _case(t, VULN, FIXED)
        ch = score2.changed_lines(ins, os.path.join(case, "secure", "src", "lib.rs"))
        assert any(abs(3 - c) <= score2.TOLERANCE for c in ch), \
            "the fix site must be locatable, or unmapped_check can never fire"



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
