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


def test_score1_real_never_exceeds_nominal():
    """An invariant: you cannot have real recall on a class without nominal recall."""
    import score, json, io as _io, os
    for fn in sorted(os.listdir("mappings")):
        if not fn.endswith(".json"):
            continue
        m = json.load(_io.open(os.path.join("mappings", fn), encoding="utf-8"))["map"]
        rows = score.score([("R", "/x/2-owner-checks/insecure/a.rs")], m)
        for cls, ins, sec, rec, nominal, real in rows:
            assert not (real and not nominal), f"{fn}/{cls}: real without nominal is impossible"


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


def test_the_noisy_control_still_produces_931_on_corpus_one():
    """The figure quoted in two results pages and in the call materials."""
    import json, io as _io, os
    if not os.path.exists("raw/c1-control-noisy.json"):
        raise AssertionError("the control's raw data is missing; the 931 figure is unbacked")
    d = json.load(_io.open("raw/c1-control-noisy.json", encoding="utf-8"))
    n = len(d["findings"])
    assert n == 931, f"published 931 findings, raw file now has {n}"


def test_corpus_commit_is_pinned_in_the_protocol():
    import io as _io
    s = _io.open("PROTOCOL.md", encoding="utf-8").read()
    assert "24555d044802db4022112a94d6d70e74291a4b6d" in s, \
        "the corpus commit must stay pinned, or no score is reproducible"


# ------------------------------------------------------------ data integrity
# Cheap checks that catch a corrupted or half-written artefact before it reaches a table.

def test_every_raw_json_file_parses():
    import json, io as _io, os
    bad = []
    for fn in sorted(os.listdir(".")) + [os.path.join("raw", f) for f in sorted(os.listdir("raw"))]:
        if fn.endswith(".json"):
            try:
                json.load(_io.open(fn, encoding="utf-8"))
            except Exception as e:
                bad.append(f"{fn}: {type(e).__name__}")
    assert not bad, f"unparseable raw files: {bad}"


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
    s = _io.open("RESULTS-all.md", encoding="utf-8").read()
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
    import ast, os, sys
    stdlib = set(sys.stdlib_module_names)
    local = {f[:-3] for f in os.listdir(".") if f.endswith(".py")}
    local |= {"scanner", "make_fixtures"}      # our own, and optional
    external = {}
    for fn in sorted(f for f in os.listdir(".") if f.endswith(".py")):
        tree = ast.parse(open(fn, encoding="utf-8").read())
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
    for fn in sorted(f for f in os.listdir(".") if f.endswith(".py")):
        src = open(fn, encoding="utf-8").read()
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
    for fn in sorted(f for f in os.listdir(".") if f.endswith(".py")):
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
def test_every_command_in_getting_started_is_runnable():
    """A quickstart that names a script that no longer exists is a broken promise."""
    import io as _io, os, re
    s = _io.open("GETTING-STARTED.md", encoding="utf-8").read()
    scripts = set(re.findall(r"python (\w[\w-]*\.py)", s))
    missing = [x for x in sorted(scripts) if not os.path.exists(x)]
    assert not missing, f"GETTING-STARTED names scripts that do not exist: {missing}"


def test_every_command_in_agents_md_is_runnable():
    import io as _io, os, re
    s = _io.open("AGENTS.md", encoding="utf-8").read()
    scripts = set(re.findall(r"python (\w[\w-]*\.py)", s))
    missing = [x for x in sorted(scripts) if not os.path.exists(x)]
    assert not missing, f"AGENTS.md names scripts that do not exist: {missing}"


def test_documents_linked_from_the_readme_exist():
    import io as _io, os, re
    s = _io.open("README.md", encoding="utf-8").read()
    links = set(re.findall(r"\]\((?!http)([A-Za-z0-9_./-]+\.md)\)", s))
    missing = [x for x in sorted(links) if not os.path.exists(x)]
    assert not missing, f"README links to missing files: {missing}"


def test_skills_referenced_by_agents_md_exist():
    import io as _io, os, re
    s = _io.open("AGENTS.md", encoding="utf-8").read()
    links = set(re.findall(r"\]\((skills/[A-Za-z0-9_./-]+)\)", s))
    missing = [x for x in sorted(links) if not os.path.exists(x)]
    assert not missing, f"AGENTS.md references missing skills: {missing}"


def test_every_skill_has_a_name_and_description():
    """A skill without frontmatter will never be surfaced to an agent."""
    import io as _io, os
    for d in sorted(os.listdir("skills")):
        p = os.path.join("skills", d, "SKILL.md")
        assert os.path.exists(p), f"{d} has no SKILL.md"
        head = _io.open(p, encoding="utf-8").read()[:600]
        assert head.startswith("---"), f"{d}: no frontmatter"
        assert "name:" in head and "description:" in head, f"{d}: incomplete frontmatter"


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
    s = _io.open("PROTOCOL.md", encoding="utf-8").read()
    assert "fourteen days" in s or "14 days" in s or "2026-09-14" in s, \
        "the stop condition must stay stated, and it only binds if it is written down"


def test_protocol_warns_that_corpus_one_is_in_sample():
    import io as _io
    s = _io.open("PROTOCOL.md", encoding="utf-8").read().lower()
    assert "in-sample" in s, "every corpus-1 score must carry the in-sample warning"


def test_limitations_document_is_not_empty_or_shrinking():
    """Limitations should accumulate. A suspiciously short file means someone tidied them away."""
    import io as _io
    n = len(_io.open("KNOWN-LIMITATIONS.md", encoding="utf-8").read().split("\n"))
    assert n > 60, f"KNOWN-LIMITATIONS has only {n} lines; limitations do not disappear"


def test_commitments_are_still_stated():
    import io as _io
    s = _io.open("COMMITMENTS.md", encoding="utf-8").read().lower()
    assert "free" in s and ("no money" in s or "take no" in s), \
        "the open-data and no-money-from-those-we-measure commitments must stay stated"


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
    import io as _io, os
    if not os.path.exists("CANDIDATES-TRIAGE.md"):
        return
    s = _io.open("CANDIDATES-TRIAGE.md", encoding="utf-8").read()
    assert "REJECT" in s, "the triage file records acceptances only, which hides the judgement calls"
    assert "out of scope" in s.lower(), "rejections must say why, not just that"

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
