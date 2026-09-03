from ._core import _publication_documents

# --------------------------------------------- the ROADMAP inventory, derived not typed
# Error 47. The "What already exists" table in ROADMAP.md was typed by hand on 2026-09-01 and
# every derivable figure in it was wrong two days later: 2165 lines of Python (5,645 in tools/
# alone by 2026-09-03), 15 tools (29), 1,625 lines of documentation in 15 files (3,921 in 18),
# 46 commits (186), 26 raw output files (3,487 tracked under raw/, 1,635 of them run logs). The
# numbers were never derived from anything: git history shows they do not match the tree even at
# the commit that introduced them, so they were typed from memory and frozen. The original
# meaning of the raw count was reconstructed from commit 28801ec, where the sentence was
# written: raw/ held 34 files, 8 of them run logs, so "26" counted everything that was not a
# log. That definition is kept below and named in the document, because a count that cannot
# say what it counts is a number, not a claim.
#
# Same shape as test_the_error_count_matches_the_logs: the document states a figure, the figure
# is derived here, and the two must agree or the suite fails.


def _git(args):
    import subprocess
    p = subprocess.run(["git"] + args, capture_output=True, text=True)
    assert p.returncode == 0, f"git {' '.join(args)} failed: {p.stderr.strip()}"
    return p.stdout


def _tracked(glob):
    """Tracked paths matching a pathspec, each one once.

    dict.fromkeys is load-bearing. During a merge `git ls-files` prints one line per index
    STAGE, so every conflicted path arrives two or three times and every count derived from
    this function silently inflates. On 2026-09-03 that put "3,870 lines of documentation
    across 20 files" into ROADMAP - the true figures were 2,466 and 14 - and the numbers were
    written from a suite run taken mid-merge. A derivation that depends on when it is run is
    not a derivation.
    """
    seen = [f for f in _git(["ls-files", "--", glob]).splitlines() if f.strip()]
    return list(dict.fromkeys(seen))


def _tracked_flat(directory, suffix):
    """Tracked files DIRECTLY in a directory, none of its subdirectories.

    git's pathspec `*` crosses directory separators, so `git ls-files -- 'tools/*.py'`
    also returns `tools/legacy/*.py`; the count and the tree then disagree about what
    a flat glob means. Depth is enforced here in Python, where it means what it says.
    """
    prefix = directory.rstrip("/") + "/"
    return [f for f in _tracked(directory + "/*" + suffix)
            if "/" not in f[len(prefix):]]


def _line_total(files):
    import io as _io
    total = 0
    for f in files:
        with _io.open(f, encoding="utf-8", errors="replace") as fh:
            total += sum(1 for _ in fh)
    return total


def _roadmap_inventory():
    """Every figure the ROADMAP inventory table states, computed from the working tree.

    The definitions are the ones the document names, and nothing else counts: tools are
    the tracked Python files directly in tools/ (the subdirectories hold packs and legacy
    code, not the checked-in toolset); documentation is docs/*.md minus the engineering
    logs, which are records rather than documentation; a raw artefact is a tracked file
    under raw/ that is neither a run log nor raw/README.md.
    """
    import os
    tools = _tracked_flat("tools", ".py")
    docs = [f for f in _tracked_flat("docs", ".md") if "ENGINEERING-LOG" not in f]
    raw = _tracked("raw/")
    artefacts = [f for f in raw if not f.endswith(".log") and f != "raw/README.md"]
    skills = [d for d in sorted(os.listdir("skills"))
              if os.path.isfile(os.path.join("skills", d, "SKILL.md"))]
    adapters = [f for f in sorted(os.listdir("adapters")) if f.endswith(".json")]
    # The error count is derived from the logs by the same helper the README's own claim uses,
    # so the two pages cannot disagree. They did on 2026-09-03: README said 47 and ROADMAP said
    # 46, one line below a paragraph about figures not being typed by hand (error 48).
    from .documented_commands import _documented_error_numbers
    return {
        "lines": _line_total(tools),
        "tools": len(tools),
        "doclines": _line_total(docs),
        "docfiles": len(docs),
        "commits": int(_git(["rev-list", "--count", "HEAD"]).strip()),
        "raw": len(artefacts),
        "skills": len(skills),
        "adapters": len(adapters),
        "errors": len(_documented_error_numbers()),
    }


def test_the_roadmap_inventory_is_derived_not_typed():
    """Each count in the ROADMAP's "What already exists" section is checked against the
    repository, so the section can never again be two days stale. The figure follows the
    noun, as in the noisy-control check: 5,645 lines and 29 tools are different quantities,
    and swapping them would pass a check that only compared numbers."""
    import io as _io, re
    q = _roadmap_inventory()
    roadmap = _io.open("docs/ROADMAP.md", encoding="utf-8").read()

    # What each row of the inventory must state. The phrasing is pinned loosely (a number
    # followed by its noun) so wording can evolve while the figure cannot drift.
    wanted = [
        (q["lines"], r"\*\*([\d,]+) lines\*\* of Python", "Python lines in tools/*.py"),
        (q["tools"], r"across \*\*([\d,]+) tools\*\*", "tracked tools/*.py files"),
        (q["doclines"], r"\*\*([\d,]+) lines\*\* of documentation", "documentation lines"),
        (q["docfiles"], r"documentation across ([\d,]+) files", "documentation files"),
        (q["commits"], r"\*\*([\d,]+) commits\*\*", "commits"),
        (q["raw"], r"\*\*([\d,]+) raw artefacts\*\*", "raw artefacts under raw/"),
        (q["errors"], r"\*\*([\d,]+) of our own errors\*\*", "documented errors"),
        (q["skills"], r"\*\*([\d,]+) skills\*\*", "skills"),
        (q["adapters"], r"\*\*([\d,]+) adapter declarations\*\*", "adapter declarations"),
    ]
    wrong = []
    for n, pattern, what in wanted:
        m = re.search(pattern, roadmap)
        assert m, (f"docs/ROADMAP.md no longer states {what} in the shape /{pattern}/; "
                   "if the section was reworded, teach this check the new phrasing")
        stated = int(m.group(1).replace(",", ""))
        if what == "commits":
            # The commit count is the one figure that cannot contain itself: the commit that
            # states it adds one, and the way it lands can add one more (a merge commit). A lag
            # of at most 2 is therefore honest and unavoidable; overstatement never is, and a
            # lag of 3 means the figure was not refreshed when it should have been.
            if not 0 <= n - stated <= 2:
                wrong.append(f"{what}: ROADMAP says {stated}, repository has {n} "
                             "(lag beyond the stating commit and its merge)")
        elif stated != n:
            wrong.append(f"{what}: ROADMAP says {stated}, repository has {n}")
    assert not wrong, ("the ROADMAP inventory is stale - every figure in it is derivable, "
                       f"so staleness is a choice: {wrong}")


def test_the_roadmap_names_its_derivation_guard():
    """Error 47's second half. The section header claimed the figures were "measured on
    2026-09-01 ... checkable in thirty seconds", which was true for one day. A claim of
    measurability that outlives the measurement is worse than none, so the header must
    name the check that keeps the figures true, and the date must be gone: an inventory
    maintained by a test does not need a measurement date any more than the error count
    needs one."""
    import io as _io
    s = _io.open("docs/ROADMAP.md", encoding="utf-8").read()
    assert "Measured on 2026-09-01" not in s, (
        "the ROADMAP inventory is derived by test_the_roadmap_inventory_is_derived_not_typed; "
        "a hand-measurement date on a derived table is exactly the sentence that went stale")
    assert "test_the_roadmap_inventory_is_derived_not_typed" in s, (
        "the ROADMAP inventory header must name the test that derives its figures, so a "
        "reader is sent to the check rather than to a date")
