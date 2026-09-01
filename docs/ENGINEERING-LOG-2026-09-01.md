# Engineering log, 2026-09-01

Seven more errors, numbered 22 to 28, continuing from
[the log of 2026-08-31](ENGINEERING-LOG-2026-08-31.md).

**Every one of them was a freshness defect, not a computation defect.** Nothing here was calculated
wrong. Each was a statement that was true when it was written, was never rechecked, and stopped
being true when the thing it described changed. That is a different failure mode from the twenty-one
before it, and it needed a different fix: the numbers on the front page are now **derived from the
repository rather than typed beside it**.

Five of the seven were on the README. That is not a coincidence. **The front page is read by
everyone and verified by no one**, so it rots fastest and costs the most when it rots.

---

## Part 1: a claim that kept its shape after its evidence changed

**Error 22. The real-crates claim on the front page dropped every qualifier the results page
states.** `RESULTS-realcrates.md` is careful: six scoreable pairs, **two of six scanners**, three of
the largest cases unmeasurable, and a closing line saying it retires one objection rather than
proving a general claim. The one-line summary on the README said the packaging objection was
retired, full stop.

Nobody edited the results page down. The summary was written when it was closer to true, and the
qualifiers were never carried forward.

**Error 23. `927 .rs files` was quoted as a fact a reader could check, and it was not.** `corpus2/`
holds nineteen. The real crates are built on demand into a temporary directory and were never
committed, so the number could not be recomputed from the repository by anyone, including us. It
also counted `cashio-account-data`, excluded since as an invalid pair (error 18).

The fix is not a better number. **A figure nobody can recompute does not belong on the front page**,
so the bullet now points at the per-case table.

*Found because Bartosz asked whether the claim still held after corpus 2 changed. It did not.*

---

## Part 2: the restructure moved files and the link check was too narrow to notice

**Error 24. Five broken links, and a test that could not see four of them.** Moving documents into
`docs/` and raw data into `raw/` left links pointing at a home those files no longer have. The
existing check read **README only and `.md` targets only**, so a link to a `.log` inside
`docs/results/` passed, and so did three links in `docs/` itself.

Generalised to every relative target in every document, it found the other four immediately.

**Error 25. The reproduce block mixed two working directories.** One command was relative to
`docs/results/`, the next two to the repository root. **Neither reading of it ran.** A reproduce
block that cannot be pasted is worse than none, because it looks like evidence of reproducibility.

---

## Part 3: two numbers on the front page disagreeing with the repository

Found on a last read-through before the README was to be handed to someone.

**Error 26. The README advertised 82 checks while the suite ran 90.** Tests had been added three
times without touching the sentence that says how many there are.

**Error 27. The page said "nine real break-ins" in three places against a result table reading
"0 / 8", and never reconciled them.** Nine cases are valid; eight are built; `spl-token-lending-
rounding` is reported `not-built`.

That last part is the sting. **This project built the `not-built` discipline specifically to stop
denominators drifting silently** (error 15), and the front page was the one place not applying it.
A reader seeing nine and eight without explanation is right to distrust the rest of the page.

### The fix, which is the only durable part

Both are now **derived, not typed**:

- the check count is computed from the suite and compared against README and `AGENTS.md`
- the denominator is read from `corpus2/manifest.json` and from the directory, so when the ninth
  case is built the test **fails on purpose** and demands the prose be updated

The count test **failed on its own introduction** - adding it changed 88 to 90 - which is the
cleanest possible demonstration that it works.

**The general rule, now standing: never type a count a machine can compute.**

---

## Part 4: an assertion of portability, and what the machine found

The claim that this runs anywhere rested on one Linux runner and one Windows laptop. CI now runs the
whole verification surface on **ubuntu, macOS and Windows**, plus Python 3.9 and 3.12.

All three operating systems passed on the first run. **Python 3.9 failed**, and not in the tools:
`sys.stdlib_module_names` arrived in 3.10, so our own no-dependencies check could not execute there
while 91 of 92 checks passed.

**The tempting fix was to raise the floor to 3.10**, which would have made the README true by
weakening the claim. That is the same move as loosening a threshold to get a result, and it is
refused here for the same reason. The check skips on 3.9, says so in its output, and still runs on
3.11 and 3.12, so the promise it guards is enforced on every push.

Windows is in the matrix deliberately rather than for completeness. **Paths are the one thing a
scorer can get quietly wrong**, so a finding located by a backslash path now has a test proving it
lands on the same case as a forward-slash one.

---

## Part 5: an error outside this repository that was about this repository

**Error 28. Thirty-two open tasks, including all four vendor right-of-reply threads, were assigned
to a worker profile that had stopped.** It last completed anything on 2026-08-30 21:33; only one
profile was live.

**A task assigned to a queue nobody reads is indistinguishable from no task at all.** The falsifier
clock in `PROTOCOL.md` - fourteen days, zero technical replies - was running the entire time, and
the threads it depends on had nobody driving them.

Recorded here rather than kept internal because it directly affects a published commitment: when
this document says vendor threads are being led, that has to be true.

---

## What this day produced

- 92 checks, up from 82, running on three operating systems and three Python versions
- five broken links closed, and a link check that can see all of them
- two front-page figures converted from typed to derived
- one over-stated claim qualified and one unverifiable number withdrawn

## What is still wrong

- **`spl-token-lending-rounding` is still not built**, so every real-vulnerability score reads out
  of eight rather than nine.
- **Four of six scanners have never been run on the real crates**, so the packaging objection is
  tested rather than retired.
- **Radar cannot finish on the three largest real crates**, which biases that coverage toward small
  projects and is itself a finding we owe Auditware.
- **`sol-audit` still has no per-run coverage log** while Radar and VaultLint do.
- **Still no vendor reply**, from any of the four threads.
