# Engineering log, 2026-09-03

Continuing from [the log of 2026-09-02](ENGINEERING-LOG-2026-09-02.md). Two entries so far.

**A note on the numbering, established by this entry.** The entries run from 1 to 46 and there are
45 of them: **number 9 was never issued.** Nothing was deleted; git history for `docs/` contains no
commit that ever added an "Error 9", so the number was skipped when the log was first written. The
gap is recorded here rather than closed, because renumbering published history would make every
earlier citation wrong to spare us one missing integer.

---

## Error 46. The count of our own errors was the highest number, not the number of entries

**2026-09-03, 03:10 to 03:40 CEST.** The front page has carried "45 of our own errors" since
2026-09-02. There were 44. The check that was supposed to make that impossible,
`test_the_error_count_matches_the_logs`, derives the figure like this:

    logged = max(logged, *numbers) if numbers else logged

It takes the **highest error number** in the logs and compares it with the README. Its own docstring
says the opposite: "Derived from the logs rather than typed, because the count only ever goes up".
Highest-number and count are the same quantity only while the numbering has no gaps, and the
numbering has had a gap at 9 since the first day. So the page overstated the record by one, the test
passed on every push, and the overstatement was in the direction that flatters us: a project whose
pitch is that it publishes its own mistakes claimed one more mistake than it had.

**Three figures in the same family were wrong at the same time**, and none of them was derived:

| where | said | is |
|---|---|---|
| `README.md`, the error claim | 45 errors | 45 entries, numbered to 46, after this one; it was 44 before |
| `README.md`, the per-day line | 21 on 08-31, 20 on 09-01, 3 on 09-02 | 20, 20, 4 |
| `docs/ENGINEERING-LOG-2026-09-02.md`, its opening | "Three entries" | four (42 to 45) |
| `docs/ROADMAP.md`, the run-log bullet | "Ours does not have one yet" | 22 of 22 have one, since 09-01 |

The per-day line reads 21 for 2026-08-31 because that log's headings run to 21, but error 6 shares
a heading with error 5 ("Error 5, and then error 6") and 9 does not exist, so the entries there
number 20. The same confusion between "how many" and "how far the numbering got", one line apart
from the check that had it too.

**Fixed in this commit.** The test now derives the **count of distinct documented numbers**, checks
the per-day breakdown line against the same derivation, and asserts that the set of missing numbers
is exactly the one the log declares, so a future gap has to be written down instead of silently
absorbed. The README carries the derived count. `ROADMAP.md`'s bullet is corrected against the gate
that answers it, `python tools/run_all.py --verify-coverage`.

**What this is an instance of.** Error 20 was a published headline that was wrong. Error 43 was an
artefact that existed and was read by nobody. This one is narrower and worse in one specific way:
**the guard existed, ran on every push, and was measuring a different quantity than the one it was
named after.** A check whose docstring and whose code disagree is not a weaker check than none, but
it is a more expensive one, because it also buys the belief that the thing is covered.

The general rule this repository keeps rediscovering: a check that cannot be shown failing has not
been shown to work. This one could never have failed, because `max` and `len` agree on every input
where the numbering is dense, and nobody fed it a sparse one.


---

## Error 47. The ROADMAP inventory was typed by hand, dated, and wrong within two days

**2026-09-03, 03:40 to 04:30 CEST.** The "What already exists, before the first dollar" section of
`docs/ROADMAP.md` is the inventory a funder reads first. Its header claimed: "Measured on 2026-09-01 by
counting the repository, so every figure below is checkable in thirty seconds." Checked on 2026-09-03:

| the table said | the repository has |
|---|---|
| 2165 lines of Python | 5,645 in `tools/` alone |
| 15 tools | 29 tracked `tools/*.py` |
| 1,625 lines of documentation in 15 files | 2,461 in 14, excluding the engineering logs |
| 46 commits | 186 (`git rev-list --count HEAD`) |
| 26 raw output files | 3,487 tracked under `raw/`, of which 1,635 are run logs and 1,851 are artefacts |

Nothing checked any of it, and none of it was derived in the first place: at commit `28801ec`, which
introduced the table, the tree already disagreed with the figures. They were typed from memory, dated,
and frozen. The one non-obvious row was reconstructed rather than guessed at: `raw/` held 34 files at
that commit, 8 of them run logs, so "26" counted everything that was not a log. That definition is kept
and is now written in the document, because a count that cannot say what it counts is a number, not a
claim.

The direction of the error is worth noting: the table *understated* the repository by 3x on lines and
4x on commits. A stale inventory does not only overstate; it sells the work short in the one document
whose job is to state it.

**Fixed in this commit.** The figures in `ROADMAP.md` are now derived by
`test_the_roadmap_inventory_is_derived_not_typed` (`tests/roadmap_inventory.py`), which recomputes each
quantity from the repository and compares it with the sentence that states it, figure matched to noun as
in the noisy-control check. The header names the test instead of a measurement date. The raw row says
what it counts. The check-count cascade (README, GETTING-STARTED, WALKTHROUGH, the three skills) moved
from 158 to 160 with the two new checks.

**What this is an instance of.** Error 46, found an hour earlier the same morning, was a published
figure guarded by a check that measured a different quantity. This one was a table of published figures
with no guard at all. The shared root: figures typed by hand stay true only until the next commit, and
the repository had already learned that lesson twice (errors 22 and 33) without applying it to the
document that faces the money.

One figure needed a rule of its own. A commit count cannot contain itself: the commit that corrects it
adds one, and the merge that lands the correction can add another. The check therefore accepts a lag of
at most 2 on that row and only that row, never an overstatement, and the table states the count as of
the correcting commit (187). Every other figure is exact or the suite fails.
---

## Not an error: what the family of error 46 looks like across the whole suite

**2026-09-03, 03:50 to 04:00 CEST.** Error 46 was a guard that ran on every push and measured a
different quantity than its name. The obvious next question is how many more there are, and
grepping does not answer it, because whether a loop body ever runs depends on the data rather than
on the code. `tools/assert_coverage.py` runs the whole suite under `sys.settrace` and counts which
`assert` lines the interpreter actually reaches.

    assertions in tests/: 270   executed at least once: 269   never: 1

The one is `tests/real_crate_run.py:170`, the `else` half of a two-sided check on whether the
packaging comparison still finds zero differences. It is idle because the data currently satisfies
the other branch, which is what a two-sided check is for. **So there is no second error 46 in the
suite, and that is now measured rather than assumed.**

**What the number does not say**, and the tool's own header says it first: it measures execution,
not the ability to fail. `assert x or True` executes on every run and can never fail. On the same
night, the sister project's `discover.py` carried exactly that line under a comment describing a
Bonferroni correction, and this tool would not have caught it. Execution is one necessary condition
of a check being real, not a sufficient one.

**The suite caught the tool while the tool was measuring the suite.** A plain `import test_all`
inside `tools/` reads to `test_no_external_python_dependencies` as a pip dependency, because
`test_all.py` sits at the repository root and has no sibling in `tools/`. The check was right, so
the new file bent rather than the check: the suite is loaded by path through `importlib`.

