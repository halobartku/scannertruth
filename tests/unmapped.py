import io
import os
import tempfile

from ._core import FIXED, VULN, _case


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
