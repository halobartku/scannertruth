# Engineering log, 2026-09-01

Ten more errors, numbered 22 to 31, continuing from
[the log of 2026-08-31](ENGINEERING-LOG-2026-08-31.md).

**Errors 22 to 30 are freshness defects, not computation defects.** Nothing in them was calculated
wrong. Each was a statement that was true when it was written, was never rechecked, and stopped
being true when the thing it described changed. That is a different failure mode from the twenty-one
before it, and it needed a different fix: the numbers on the front page are now **derived from the
repository rather than typed beside it**.

Five of the first seven were on the README. That is not a coincidence. **The front page is read by
everyone and verified by no one**, so it rots fastest and costs the most when it rots. Errors 29 and
30 are the same shape one level down, in the document that decides what enters the corpus.

**Error 31 is not.** It is a defect in the scorer itself, latent since the scorer was written,
found only because eight new cases gave four different files the same name. It is the one entry
here that changes a published verdict, and it is deliberately left unfixed so the correction can be
published as a correction rather than buried in a corpus commit.

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

## Part 6: two stale statements in the triage document, found while adding eight cases

Both were found by a candidate hunt on 2026-09-01, and both were re-verified against the
repositories here before being written down. Neither was a miscalculation. Both are the same
freshness shape as errors 22 to 27: a sentence that was a reasonable guess when it was written,
that nobody rechecked, and that would have sent the next reader somewhere wrong.

**Error 29. `CANDIDATES-TRIAGE.md` pointed the GHSA-c6rc-8jpp-2fgc fix at the wrong pull request.**
The row said the fix "needs one hop through PR #3837". It does not. In a clone of
`coral-xyz/anchor`, `git log --all --grep="#3837"` returns exactly one commit, `3a799e2d`, subject
`feat(account): Check Owner on Reload (#3837)`, first tag `v1.0.0`. That is a different bug, and it
is now in the corpus in its own right as `anchor-account-reload-owner`. The GHSA-c6rc fix is
`3eb1fb04`, `fix(lang): Improve Program generic key checking logic`, which carries no PR number and
whose first tag is `v1.0.2`, matching the advisory's stated patched version exactly.

**The cost had this not been caught**: a case built under a CVE number from the wrong commit. The
pair would have looked perfectly clean, and the label would have been wrong in the one way this
project cannot detect after the fact, because the answer key would have been ours rather than the
maintainers'.

*Cause: the advisory does not name a commit, so a plausible-looking PR number was written down as
if it were a resolution rather than as a lead still to be checked. The row now records the commit,
and the manifest records the first tag it shipped in.*

**Error 30. The triage document projected a corpus size that could never have been reached.** It
said two accepted candidates would take corpus 2 "from 9 valid cases to 11". One of the two,
GHSA-h6xm-c6r4-vmwf in `spl-token-swap`, has no fix and is not getting one: the advisory records no
patched version, and the pointer cast it reports is still present at HEAD today, at
`token-swap/program/src/instruction.rs:627`. Checked with `git grep` at HEAD rather than read off
the advisory. The package was deprecated rather than patched. The honest figure from that day's
triage was 10.

**Why this matters more than a number being two out.** It is a *forward* claim about the corpus,
which is the asset this project says is the whole point, and a forward claim about the asset is the
one a reader has no way to check. It is now corrected in place, with the strike-through visible
rather than the sentence rewritten, because that is how this project has handled every other
correction.

*Cause: a candidate was accepted as "pending build" on the strength of the advisory existing,
without anyone establishing that a fix commit existed to build against. Acceptance now requires the
fix commit, not the advisory.*

---

## Part 7: what adding eight cases did to every published denominator

Not an error. Recorded here because it is the exact shape of the defect this day was spent on, and
it was avoided rather than committed.

Eight cases were added to corpus 2 on 2026-09-01. Every score published on this page is a fraction
whose denominator is the corpus, so **adding a case silently changes every published figure unless
something stops it.** The suite already had the check that would have caught the sloppy version of
this: `test_the_real_vulnerability_denominator_is_reconciled_on_the_front_page`.

But that check derived the results-table denominator from the **built** set, and it was right to
until today. A case can now be valid, built, and never analysed by anything. Deriving the
denominator from the built set would have restated every published zero as "0 / 16" the moment the
files landed on disk, which is not a stale number but a **fabricated** one: a zero out of sixteen
that no scanner ever produced. The check now separates built from measured and pins the table to
the measured set, and the manifest carries `"measured": false` per case so the distinction is data
rather than prose.

The calibration figure moved too. `control-noisy` produced 424,170 findings on corpus 2 when that
sentence was written; it produces **1,413,620** today, because both the corpus and the mapping set
have grown. Six documents quoted the old number. They now quote the derived one, and a check
recomputes it from the corpus and the mappings and fails any document that has drifted. The control
still scores **zero against all ten mappings** on the enlarged corpus, verified case by case before
the number was changed.

**`raw/c2-control-noisy.json` is stale as of this commit** and regenerates with
`python tools/control_c2.py`. It is a generated artefact, not a measurement of anybody's tool, and
it was left alone only because another agent was writing to `raw/` at the same time.

---

## Part 8: a scorer defect the eight new cases made visible

**Error 31. `score2.score_case` matches a finding to a case by FILENAME ONLY, so a finding on one
case's `processor.rs` can be credited to another case's `processor.rs`.** The matching line is
`if not p.endswith("/" + name): continue`, where `name` is a bare basename. The case directory is
used to locate the pair and to compute the fix site, and then never used to decide whether a
finding belongs to this case at all.

This was always wrong. It was mostly harmless while the corpus had nine cases with nearly distinct
filenames, and adding eight cases made it live: `processor.rs` now appears in four cases,
`state.rs` in two, `lib.rs` in three.

**It affects one published verdict.** Scored with findings restricted to their own case, Radar's
`squads-signer-auth` goes from `unlocated` to `missed`, so the published breakdown "2 `unlocated`,
5 missed, 1 no-rule" would read "1 `unlocated`, 6 missed, 1 no-rule". Radar's real recall is **0
either way**, so no headline moves, but a breakdown this project published about somebody else's
tool is wrong in the direction that flatters it, and it is still wrong.

**Nothing was changed here.** The scorer is untouched and every published number stands as
published, because:

- correcting it restates a third-party result, and this project's own protocol gives that vendor a
  right of reply before a result about their tool is treated as final;
- a scorer changed in the same session as a corpus is a scorer whose change cannot be attributed;
- the retraction has to come before the replacement, not bundled with it.

**What a fix looks like**, so that this is a five-minute job for whoever picks it up rather than a
re-derivation: require the finding path to contain the case directory, `if f"/{case}/" not in p and
not p.startswith(case + "/"): continue`, next to the existing basename test. Measured across every
raw corpus-2 findings file in the repository, that changes exactly two verdicts: the Radar one
above, and `token-2022-confidential-approve-mint`, which is one of today's unmeasured cases and was
never going to be published from that file anyway. `vaultlint` and `sol-audit` are unaffected.

The clock is not affected, and that is not luck: `run_all.measure_corpus2` consults the per-run log
first and never scores a case the log does not list, so a case with no run behind it can never pick
up another case's findings. The exposure is `score2.py` used directly, which is what `AGENTS.md`
step 6 tells an agent to do.

---

## What this day produced

- 92 checks, up from 82, running on three operating systems and three Python versions
- five broken links closed, and a link check that can see all of them
- two front-page figures converted from typed to derived
- one over-stated claim qualified and one unverifiable number withdrawn

## What is still wrong

- **`spl-token-lending-rounding` is still not built**, and eight further cases are built but have
  never been measured, so every real-vulnerability score reads out of **eight of seventeen valid
  cases**. The corpus grew today; the measurement did not.
- **Nothing has been run over the eight cases added today.** Until a scanner is, `run_all.py` will
  report `radar`, `vaultlint` and `sol-audit` on corpus 2 as `partial` rather than `measured`, which
  is correct and should not be edited away.
- **Four of six scanners have never been run on the real crates**, so the packaging objection is
  tested rather than retired.
- **Radar cannot finish on the three largest real crates**, which biases that coverage toward small
  projects and is itself a finding we owe Auditware.
- **`sol-audit` still has no per-run coverage log** while Radar and VaultLint do.
- **Still no vendor reply**, from any of the four threads.
