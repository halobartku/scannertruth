from ._core import _rule_mappings

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
    for fn in _rule_mappings():
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
