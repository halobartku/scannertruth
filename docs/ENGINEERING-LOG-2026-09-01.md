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
sentence was written; it produced **1,413,620** when this entry was written and **2,392,280**
after the SOL-0XX Semgrep mapping was pre-registered on 2026-09-01, because both the corpus
and the mapping set have grown. Six documents quoted the old number. They now quote the derived one, and a check
recomputes it from the corpus and the mappings and fails any document that has drifted. The control
still scores **zero against all ten mappings** on the enlarged corpus (fourteen after
the Semgrep pre-registration, still zero), verified case by case before
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

## Part 9: the rule this project repeats most often, broken in the artefact built to enforce it, and then nearly broken again in the opposite direction

**Error 32. The runner that decided `ok` versus `UNAVAILABLE` for every Radar corpus-2 run asked
whether radar had written an output file. radar writes no output file when it finds nothing.** So a
clean zero and a failed run were the same observation to the only thing that classified them, which
is the exact confusion "unavailable is not zero" exists to prevent, inside the artefact that was
built to enforce it.

It surfaced as a disagreement. `raw/c2-radar-percase.log` line 1 said:

```
anchor-interface-account insecure UNAVAILABLE rc=0 no-parseable-output
```

`raw/c2-radar-complete.json.log`, the log `run_all.py` treats as the authority on which cases were
analysed, said `{"leaf": "anchor-interface-account/insecure", "status": "ok", "findings": 0}`. One
run, two records, and they contradicted each other for a day with nothing in the repository able to
say which was right.

**The external audit read the human log and prescribed correcting the machine one**: mark the run
unavailable, drop Radar's corpus-2 denominator from eight to seven, and correct the "36 successes,
zero unavailable" banner. That fix was applied here first, and then reverted, because it is
backwards. radar's own stdout for that run was recovered from the machine it ran on and is now in
the repository at
`raw/radar-c2-2026-08-31-stdout/anchor-interface-account.insecure.log`:

```
[i] Ran 57 templates
[i] Scanned 1 file (interface_account.rs)
[i] radar completed successfully. No results found.
```

The case was analysed. Fifty-seven templates ran against it. The zero is real. **The human log was
wrong, the machine log was right, and following the audit would have removed a real zero from a
third-party tool's denominator** - a correction in the direction that flatters the tool, arrived at
by trusting a classifier that could not see the difference it was classifying.

All eighteen stdout logs from that run were checked the same way. Every one reports
`radar completed successfully` with a non-zero `Scanned N file` count, so **"18 runs each, 36 in
total, 36 successes, zero unavailable" is true**. It was true by luck: the sentence rested on a
classifier that had already mislabelled one of the thirty-six.

The defect reproduced on demand. A fresh per-case run on 2026-09-01, with a runner written before
any of this was known, classified the same leaf `UNAVAILABLE` again, along with four others that
radar had in fact analysed and found nothing in.

**What changed.** `raw/c2-radar-percase.log` line 1 now records `ok rc=0 findings=0`, with the
original line, the reason and the evidence kept underneath it rather than rewritten away. The
eighteen stdout artefacts are committed. `tools/normalise_runs.py` classifies a radar run from
radar's own stdout and never from the presence of a file, and its `--demo` asserts that a run which
found nothing and wrote nothing is `ok`. Two new checks: the two logs for one run must agree on
every leaf, and the run log must agree with the tool's own account of what it did.

**What this is really about.** A log is only evidence if something outside the log can contradict
it. Two records of one run were written and never compared; one was derived from a proxy for the
thing it claimed to measure. The lesson is not "radar is unusual". It is that a coverage classifier
must read the tool's own statement about what it did, and that the second record exists to be
diffed against the first.

---

## Part 10: the calibration control on the teaching corpus proved nothing, and had proved nothing since the day it was written

**Error 33. `raw/c1-control-noisy.json` emitted all 931 of its findings under one invented rule id,
`NOISY-ALL`, which appears in no mapping. `tools/score.py` discards a finding whose rule is not
mapped, so it discarded all 931 before scoring.** The corpus-1 noisy control therefore scored
**0/11 nominal**, not the `11 / 11 nominal, 0 / 11 real` published on the front page, in two
results pages and in the roadmap.

The arithmetic error is the small half. The large half is that the control **demonstrated nothing
at all**. An unmapped rule id scores zero by construction. The control existed to show that a tool
which flags every line cannot buy a score, and instead it showed that a rule nobody maps scores
zero, which is true of any string. Meanwhile README:129 cited it as the reason no score in the table
was bought with volume, and `docs/PROTOCOL.md` built the "what the controls do and do not close"
argument on it.

`tools/control_c2.py` had this right for corpus 2 from the day it was written: `every_rule()` emits
the control under **every rule id any mapping claims**. Nobody noticed the two controls were built
differently. The check that guarded the corpus-1 control asserted `len(findings) == 931` and never
scored the file, so it verified that a file existed at the right size.

**What changed.** `tools/control_c1.py` is the corpus-1 half of `control_c2.py`. It rebuilds the
control under every mapped rule id, from a real checkout of `coral-xyz/sealevel-attacks` at the
pinned commit `24555d044802db4022112a94d6d70e74291a4b6d` where one is available, and from the
recorded line inventory where it is not. The regenerated control is **81,928 findings: 931 flagged
lines times 88 mapped rule ids.**

**The corrected figure, and it is the published one.** Scored against every mapping in the
repository, the control now reaches **11 / 11 nominal and 0 / 11 real**. The number that was
published was right; the artefact behind it was not, and for a day the repository could not have
produced it. Nominal recall can be bought with volume, which is exactly why this project does not
publish nominal recall as a result. Real recall cannot, and now there is evidence for that on both
corpora rather than on one.

A second, smaller thing fell out of the rebuild. The old artefact's line numbers were sequential
ordinals, 1..N, not the line numbers of the non-empty lines it claimed to have flagged. It never
mattered, because `score.py` scores on rule and path only. It is now the real line numbers.

The replacement check derives the count instead of typing it, asserts the control emits under
exactly the mapped rule set, asserts it reaches 11/11 nominal, and asserts 0 real against every
mapping. A control that cannot reach nominal recall is not a ceiling, and until today nothing said
so.

---

## Part 11: eight corpus files were not the upstream blobs they are supposed to be

**Error 34. Of the seventeen built corpus-2 cases, the eight added on 2026-09-01 did not match
their upstream blobs. Every `.rs` file in them had CRLF line endings; upstream has LF.** Content
was otherwise byte-identical. `build_corpus2.py` extracts with git, and git on Windows converted
the line endings on the way out.

Nothing in the repository could have caught this, which is the point of row 9 of the audit: the
manifest carried commit SHAs, and the check on them asserted that they looked like SHAs. Nothing
tied `corpus2/<case>/<variant>/src/*.rs` to any blob. A one-character edit to any corpus file
passed every check and changed every verdict.

It was found within minutes of hashes existing.

**Why it is not cosmetic.** The corpus is the answer key, and the claim is that the answer key is
the project's own fix. Eight of seventeen cases were a re-encoding of it. A scanner reading `\r`
at the end of every line is reading different bytes from the ones the disclosure was written
against, and the corpus was internally inconsistent: ten cases LF, eight CRLF, in one benchmark.
Two of the eight are among the largest files in the corpus.

**What changed.** The eight cases are normalised back to LF, which is byte-for-byte the upstream
blob. `corpus2/manifest.json` now records, per file, a `sha256`, git's own blob id, and the
upstream repository, commit and path the file was extracted from, so provenance is one command:

```
git -C <clone> rev-parse <commit>:<path>      # must equal the recorded git_blob
```

`tools/corpus_hashes.py` writes and rechecks them and `test_all.py` recomputes them on every run.
The result of actually asking upstream is committed at
`raw/corpus2-blob-verification-2026-09-01.json`: **35 of 35 source files match the upstream blob
exactly**, where before the normalisation 19 matched and 16 did not.

No published number moves. All eight cases carry `"measured": false` and are in nobody's
denominator. Every scanner run in this session was made against the normalised corpus, pinned by
digest `63982de746dbad71d498b8ee98acd07555ff43f7ea708fc138708bee016f300a` on both machines before
any tool ran.

---

## Part 12: solsec's denominator was inferred from silence, and the silence was not there

**Error 35. `solsec` was published as `0 / 6` on corpus 2 with "three cases produced no output at
all, with no log explaining why, so its denominator is six". There was no solsec run log anywhere
in the repository, solsec was absent from `run_all.SOURCES_CORPUS2`, and no committed code path
produced the tally.** The three unavailable cases were inferred from the absence of entries in a
findings file. That is error 20 republished under a different scanner, on the same page that
retracts error 20.

solsec 0.2.1 was rebuilt from crates.io in a container and run per case, per variant, over both
corpora, with one artefact and one log line per invocation. Coverage was read from solsec's own
output line, `Found N Rust files to analyze`, rather than from whether a file appeared.

**Corpus 2: 34 invocations, 34 ok, zero unavailable, 356 findings.** There were no cases solsec
could not analyse. The published "3 unavailable" was an artefact of reading silence, and so was the
denominator of six. Measured: **0 detected**, 1 `unlocated`, 1 `missed`, 14 `no-rule`, 1 not built.
The honest scoreable denominator is **2**, not 6: solsec has a mapped rule for two of the sixteen
built classes and the other fourteen are a coverage gap rather than a failure.

**Corpus 1: 35 invocations, 35 ok, zero unavailable, 28 findings, 0 / 11 nominal and 0 / 11 real.**
The published corpus-1 figure reproduces exactly. It now has a run log behind it, which it did not
before.

The zero did not move. The reason the zero can be trusted did.

---

## Part 13: our own scanner, re-run per case, and the one number that went up

The corpus-2 findings file for `sol-audit` had no run log, so its denominator rested on the
absence of entries in a file, and 96 of its 426 findings named files the corpus rebuild removed.
It was the last row on the coverage matrix with no evidence behind it.

It was also nearly recorded as unfixable. The commit that re-measured Radar, solsec and semgrep
said "sol-audit cannot be re-run: its source is not on this machine or the build host". **That is
wrong.** The source is at `Forge/sol-audit-v2`, and a search that looked for a directory called
`sol-audit` did not find it. The claim is corrected here rather than quietly dropped, because "we
could not run it" is exactly the sentence this project treats as a result, and a wrong one is
worse than no claim at all.

**sol-audit 3.0, 34 invocations on corpus 2 and 35 on corpus 1, all three profiles, one artefact
and one log line per run, 207 invocations in total, zero unavailable.**

| corpus | profile | result |
|---|---|---|
| 1 | strict | 6 / 11 nominal, **5 / 11 real** |
| 1 | broad | 6 / 11 nominal, **5 / 11 real** |
| 1 | all | 7 / 11 nominal, **5 / 11 real** |
| 2 | strict, broad and all | **0 detected**, 1 `unlocated`, 8 missed, 7 `no-rule`, 1 not built |

**Corpus 2 is zero under every profile**, and `unmapped_check` reports **0 candidates**, so no
detection is hiding under a rule the mapping does not claim. Our own tool, rewritten to 30 rules
tonight, detects none of the sixteen real vulnerabilities. That is the same answer every
third-party tool has given, and it is the answer its own README already leads with.

**Corpus 1 went up, from 4 / 11 to 5 / 11, and it is published as a new row rather than as a
correction.** v2's 4 / 11 is not wrong; it is a measurement of a different tool. A number that
moved because the tool changed is a different fact from a number that moved because the corpus
changed, and collapsing the two is how a benchmark stops being able to say which happened. Both
rows stand, both dated, and the clock now records the source file and the mapping behind each.

Three things were held fixed, and none of them is the tool:

- the mapping is `mappings/sol-audit.json` **as pre-registered for v2 on 2026-08-31**. v3 added
  SOL-020 to SOL-030; the mapping does not claim them and will not be extended to claim them,
  because a mapping written after both the rules and the corpus are known is not a
  pre-registration. **The row therefore understates v3, deliberately.**
- every profile the CLI offers was run, and all three are published. Nothing was chosen after
  seeing output.
- the titles of SOL-001 to SOL-019 were read and checked against the mapping before the run,
  because a renumbered rule id would have made the mapping measure something else in silence.

`run_all.py` now records the `source` file and the `mapping` behind every row it writes, so a
reader comparing two dated runs can see whether the artefact or the mapping moved underneath the
number.

---

## What this day produced

- 120 checks, up from 82, running on three operating systems and three Python versions
- five broken links closed, and a link check that can see all of them
- two front-page figures converted from typed to derived
- one over-stated claim qualified and one unverifiable number withdrawn
- **five more errors found and published: 31 to 35**, one of which was the external audit getting
  a correction backwards and one of which was found by the very check the audit asked for
- **the whole corpus tied to upstream**: 35 of 35 source files match the upstream git blob exactly
- **four measurements added or replaced**, all per case, all with a log per invocation: Radar
  re-run on the current corpus, semgrep with the SOL-0XX pack as an eighth tool, solsec, and our
  own sol-audit 3.0
- **coverage evidence from 3 of 12 measurements to 15 of 20**, in a matrix that is generated

**Error 36. `sol-azy` was published in the could-not-run table with the reason "ships no default
rule set, so it detects nothing out of the box", on the same day it was measured, with the raw
output, the run logs and three pre-registered mappings sitting in this repository.** It has an
internal rule set. It was invoked as `sol-azy sast -d <case-dir> -s` in a `rust:slim` container
with the corpus mounted read only and no network, against corpus 1 pinned at `24555d04` and
corpus 2 pinned by file digest and verified byte-identical on two machines before any run. It
scores **9 / 11 nominal and 4 / 11 real** on the teaching corpus, which is the same real recall
our own v2 scanner had, and **0 detected on the expanded corpus 2, 15 of 17 cases analysed, one
not built and one not run**.

Found on 2026-09-01 while refreshing the Polish briefing documents, by an agent checking every
figure in them against the repository rather than against the previous version of the document.

**This is the project's own most-repeated rule inverted.** We say, in the README, in AGENTS.md and
in three skills, that "could not run" and "found nothing" are different observations and that
conflating them is how a benchmark misleads. Here we published *could not run* about a tool we had
run, whose result we held, and which was not nothing. Errors 20 and 35 were the same confusion in
the other direction: silence read as a measurement. This one is a measurement read as silence.

The row is corrected on the front page and in `docs/SCANNERS.md`. The could-not-run table now
carries only tools with no result behind them, which is what it claims to contain.

## What is still wrong

**Error 37. The retraction in error 33 was applied to the front page and to nothing else.**
`AGENTS.md`, `docs/ROADMAP.md`, `docs/KNOWN-LIMITATIONS.md`, both results pages and the
`measure-a-scanner` skill all still said the corpus-1 noisy control produces **931 findings**, the
figure error 33 retracted that morning. Six live documents, one of them the instruction sheet an
agent loads before measuring anything.

The cause is structural, not clerical: the derived-count check counts tests and nothing else, so
every other published quantity is typed by hand and drifts silently. A check now derives both
control figures from what the tools actually produce, in about ten milliseconds, and **the noun
decides**: `931 findings` is illegal, `931 non-empty lines` is the fact it was derived from.

The first version of that check compared numbers against a set of legal quantities and passed. A
mutation putting `931 findings` back **survived it**, because 931 is legal as a line count. A check
that accepts the right number under the wrong noun is not a check, so it was rewritten to match the
quantity against what it is a count of. The rewritten version failed on introduction and named five
documents nobody had looked at. Both directions are mutation-verified: the retracted findings count
is caught, the legitimate line count is not.

- **`spl-token-lending-rounding` is still not built.** Every corpus-2 figure reads out of sixteen
  built valid cases, or out of eight for the two rows that have not been re-run.
- **`sol-audit` v2 and `vaultlint` have not been re-run over the eight cases added today**, so
  `run_all.py` reports them as `partial`, which is correct and should not be edited away. Radar,
  solsec, semgrep-with-the-pack and sol-audit v3 have been, and detect nothing on any of them.
- **`sol-audit` v2 still has no per-run coverage log on either corpus**, and 96 of the 426
  findings in its corpus-2 file name files the corpus rebuild removed. The scorer now refuses to
  score on them; `raw/stale-findings-2026-09-01.json` keeps the count visible.
- **Four of eight scanners have never been run on the real crates**, so the packaging objection is
  tested rather than retired.
- **Radar cannot finish on the three largest real crates**, which biases that coverage toward small
  projects and is itself a finding we owe Auditware.
- **Corpus 2 cannot be compiled by any compiler-based analyser**, and corpus 1 no longer resolves
  its dependencies at all (`anchor-lang 0.20.1` is yanked). X-Ray and solana-lints are being scored
  against corpora they cannot open.
- **Nine classes of sixteen have no rule in any mapping**, so the raw denominator is not the honest
  one. `run_all.py` now publishes a `scoreable_denominator` beside every tally; the results pages
  quote it for some rows and not yet for all.
- **Still no vendor reply**, from any of the threads, and none has been opened with Copenhagen0x
  for the SOL-0XX pack or with the solsec author about the corrected denominator. Every result
  here is provisional until they have been.
