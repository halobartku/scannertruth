"""The Radar regression pack: without these it is a directory, not a result.

Three things have to hold or the pack lies to its first user. The committed copy must be what
`tools/regression_pack.py` builds today. Its scorer must be our scorer, byte for byte. And
`check.py`, fed the per-invocation artefacts of the published `24c56f9` row, must return the
same verdict for every case as `docs/results/RESULTS-scanners.md` reports for that row.
"""
import io
import json
import os
import shutil
import tempfile

from ._core import ROOT

PACK = os.path.join(ROOT, "regression-pack-radar")
ARTEFACTS = os.path.join(ROOT, "raw", "radar-c2-2026-09-02-24c56f9")
# The published row: "7 missed, 8 no-rule, 2 unlocated" (RESULTS-scanners.md, re-measured 2026-09-02).
PUBLISHED_TALLY = {"missed": 7, "no-rule": 8, "unlocated": 2}


def test_regression_pack_is_a_fresh_build():
    import regression_pack
    diff = regression_pack.stale(PACK)
    assert not diff, f"committed pack differs from a fresh build: {diff[:5]}; run python tools/regression_pack.py"


def test_regression_pack_scorer_is_ours_verbatim():
    a = io.open(os.path.join(ROOT, "tools", "score2.py"), encoding="utf-8").read()
    b = io.open(os.path.join(PACK, "score2.py"), encoding="utf-8").read()
    assert a == b, "regression-pack-radar/score2.py is not tools/score2.py"


def test_regression_pack_check_reproduces_the_published_24c56f9_row():
    import score2
    with tempfile.TemporaryDirectory() as t:
        for leaf in os.listdir(ARTEFACTS):
            if leaf.endswith(".run2") or not os.path.isdir(os.path.join(ARTEFACTS, leaf)):
                continue
            shutil.copytree(os.path.join(ARTEFACTS, leaf), os.path.join(t, leaf))
        # check.py chdirs into the pack on import, so import it there and come back.
        cwd = os.getcwd()
        import importlib.util
        spec = importlib.util.spec_from_file_location("pack_check", os.path.join(PACK, "check.py"))
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            rows = mod.check(t)
        finally:
            os.chdir(cwd)
    got = {r["id"]: r["verdict"] for r in rows}
    tally = {}
    for v in got.values():
        tally[v] = tally.get(v, 0) + 1
    assert tally == PUBLISHED_TALLY, f"pack tally {tally} != published {PUBLISHED_TALLY}"
    # And case by case against the scorer run the table was generated from.
    mapping = json.load(open(os.path.join(ROOT, "mappings", "radar.json"), encoding="utf-8"))["map"]
    findings = score2.load_findings("radar", os.path.join(ROOT, "raw", "c2-radar-24c56f9.json"))
    cases = json.load(open(os.path.join(ROOT, "corpus2", "manifest.json"), encoding="utf-8"))["cases"]
    for c in cases:
        if not c.get("valid", True):
            assert c["name"] not in got, f"invalid pair {c['name']} is in the pack"
            continue
        v, _ = score2.score_case(os.path.join(ROOT, "corpus2", c["name"]), c["class"], mapping, findings)
        assert got.get(c["name"]) == v, f"{c['name']}: pack says {got.get(c['name'])}, score2 says {v}"


def test_regression_pack_holds_no_holdout_case():
    ledger = json.load(open(os.path.join(ROOT, "COMMITMENTS-HOLDOUT.json"), encoding="utf-8"))
    sealed = {(r.get("spec") or {}).get("name") for r in ledger["rounds"]} - {None}
    in_pack = set(os.listdir(os.path.join(PACK, "cases")))
    assert not (sealed & in_pack), f"holdout case(s) in the pack: {sealed & in_pack}"
    valid = {c["name"] for c in json.load(open(os.path.join(ROOT, "corpus2", "manifest.json"),
                                               encoding="utf-8"))["cases"] if c.get("valid", True)}
    assert in_pack == valid, f"pack cases != valid corpus2 cases: {in_pack ^ valid}"


def test_regression_pack_readme_offers_nothing():
    text = io.open(os.path.join(PACK, "README.md"), encoding="utf-8").read().lower()
    for word in ("price", "pricing", "$", "usd", "consult", "hire", "sponsor", "subscribe", "buy"):
        assert word not in text, f"vendor-thread rule: README must not contain {word!r}"


def test_regression_pack_readme_names_only_scripts_that_ship_in_the_pack():
    """The README is read from inside the pack, so its commands resolve there, not from the repo root."""
    import re
    text = io.open(os.path.join(PACK, "README.md"), encoding="utf-8").read()
    named = set(re.findall(r"(?:python3?\s+|\./)([\w./-]+\.(?:py|sh))", text))
    assert named, "README names no script at all"
    missing = sorted(n for n in named if not os.path.exists(os.path.join(PACK, n)))
    assert not missing, f"pack README names scripts that are not in the pack: {missing}"
