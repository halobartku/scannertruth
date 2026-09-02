from ._core import _rule_mappings

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
    for fn in _rule_mappings():
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
