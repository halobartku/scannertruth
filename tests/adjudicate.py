import json

# ------------------------------------------------------------ adjudicate
# Adjudicating a new model by hand took forty minutes on 2026-09-24 and one pass in the wrong file
# format. The tool applies existing rules only; a phrase without a rule must come out as "not judged",
# never as "no".

_RULES = [
    {"real_class": "owner-checks", "verdict": "counts", "reason": "mechanism", "phrases": ["Missing owner check"]},
    {"real_class": "owner-checks", "verdict": "no", "reason": "generic", "phrases": ["Missing account validation"]},
]


def _row(case, variant, vulnerable, cls, klass="owner-checks"):
    return {"case": case, "variant": variant, "class": klass, "vulnerable": vulnerable,
            "raw": json.dumps({"vulnerable": vulnerable, "class": cls})}


def test_adjudicate_counts_when_any_phrase_counts():
    import adjudicate
    got = adjudicate.apply_rules("owner-checks", ["Missing account validation", "missing owner check"], _RULES)
    assert got[0] == "counts", got


def test_adjudicate_unmapped_phrase_is_not_a_no():
    import adjudicate
    assert adjudicate.apply_rules("owner-checks", ["Missing account validation", "Totally new name"], _RULES) is None
    assert adjudicate.apply_rules("owner-checks", ["Missing account validation"], _RULES)[0] == "no"


def test_adjudicate_only_verdict_right_cases_are_named():
    import adjudicate
    rows = [_row("a", "insecure", True, "Missing owner check"), _row("a", "secure", False, ""),
            _row("b", "insecure", True, "Missing owner check"), _row("b", "secure", True, "x")]
    rows.append(_row("c", "insecure", True, "Missing owner check"))
    rows.append({"case": "c", "variant": "secure", "class": "owner-checks", "vulnerable": None, "raw": ""})
    got = adjudicate.verdict_right_named(rows)
    assert list(got) == ["a"] and got["a"]["named"] == ["Missing owner check"], got
