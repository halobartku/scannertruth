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
