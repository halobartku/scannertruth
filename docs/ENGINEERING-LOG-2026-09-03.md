# Engineering log, 2026-09-03

Continuing from [the log of 2026-09-02](ENGINEERING-LOG-2026-09-02.md). One entry so far.

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

