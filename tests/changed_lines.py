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
