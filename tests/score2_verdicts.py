import io
import json
import os
import tempfile

from ._core import FIXED, MAP, VULN, _case, _findings_file


# ------------------------------------------------------------------- score2
# The verdict machine. Every branch here decides a published cell.


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
