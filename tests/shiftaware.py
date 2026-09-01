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
