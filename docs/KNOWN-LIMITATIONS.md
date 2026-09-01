# KNOWN LIMITATIONS

Written 2026-08-31, the day this benchmark was built, by the people who built it. Everything here
weakens something we published on the same day. It is here because a measurement project that only
documents other people's flaws is not a measurement project.

Ordered by how much damage each one does.

---

## 1. Two different metrics were reported side by side as if comparable. **Our error.**

On the teaching corpus, "nominal" means *a rule mapped to that vulnerability class fired*. On
corpus 2, our first pass counted **every finding of any kind**. Those are not the same measurement
and they were printed in the same table.

**Status: FIXED 2026-08-31, same day.** `score2.py` now scores corpus 2 with mapped rules only and
requires the finding to land at the site the fix changed. Results in `docs/results/RESULTS-corpus2.md`. The
conclusion did not change under the stricter method, which is worth stating: the result was not an
artefact of the sloppy one. Limitation 2 below is fixed by the same change. The paragraph that
follows is kept as the record of what was wrong.

**Original entry:** Corpus 2 was recomputed as a set difference over rule ids (does any
rule fire on the vulnerable variant and not on the fixed one). The 0/9 result survived the stricter
method. But corpus 2 still has **no class-to-rule mapping at all**, so its numbers answer a weaker
question than the teaching corpus numbers do: "did anything distinguish the two files" rather than
"did the right rule fire for the right reason". **Do not quote them as equivalent.**

## 2. Detection is matched at file level, not at the vulnerable line.

A rule that fires on line 5 of a 200-line file, for a reason unrelated to the bug, counts the same
as one that fires on the vulnerable line. On the teaching corpus this is defensible: the files are
small and contain one deliberate bug. **On corpus 2 it is close to meaningless.** A 200-line
production file has many reasons to attract a finding.

Fixing this needs location matching against the fix diff hunks, tolerant of line shift between the
two variants. Not done.

## 3. Contaminated pairs. **FIXED 2026-08-31.**

Every case now pins the single file the public disclosure implicates, established by reading each
fix commit's full diff against its advisory. Every exclusion carries a written reason in
`corpus2/manifest.json`, so the choice can be challenged rather than trusted.

The contamination was larger than expected. `metaplex-bubblegum-creator` went from six files to one.
`wormhole-sysvar` from three to one: its fix commit is a monorepo-wide dependency bump from
solana-program 1.7.0 to 1.9.4 plus a compiler attribute change across every crate, and exactly one
of its twelve .rs files contains the security fix. Cashio's second file was a kill switch, not a
logic fix. Metaplex Token Metadata's was a helper function never called in that diff.

**Effect on the numbers:** our own scanner lost one `unlocated` verdict, which had been sitting on a
file that was not the vulnerable one. Radar and VaultLint were unchanged. So the contamination was
real noise, and it was not the cause of anything.

**Original entry:**

We extract every `.rs` file the fix commit touched. `metaplex-bubblegum-creator` yields six files,
`wormhole-sysvar` three. Most fix commits also rename things, adjust imports, or touch a test
helper. Those files are packaged as part of a "vulnerability pair" and they are not one.

Worse, a fix that refactors while fixing produces differences unrelated to the bug, which can
manufacture a false "detection": a rule fires on code that was simply moved.

## 4. Packaging. **TESTED 2026-08-31: it is not the cause.**

The obvious objection to the corpus 2 result was that we extract single files into a synthetic
crate, so a tool needing project context would fail for our reasons rather than its own. We tested
it on the strongest case.

The Wormhole program was re-extracted as **the real crate**: `solana/bridge/program` in full, at the
fix commit and its parent, with its own `Cargo.toml` and every sibling module. Radar scanned
**46 files with 57 templates** and reported seven rules.

**Its `Unvalidated Sysvar Account` rule still did not fire.** Every finding in
`verify_signature.rs`, the file containing the bug, appears identically in the vulnerable and the
fixed variant.

So the failure survives the most favourable conditions we know how to give the tool, and the
packaging objection does not explain it. The original entry is kept below as the record.

**Original entry:**

Each variant is a single directory of loose `.rs` files with a synthetic `Cargo.toml` we wrote. The
real programs are multi-crate Anchor workspaces with macros, sibling modules and dependencies. A
tool that needs the project structure to resolve types will underperform for reasons that are our
fault, not the tool's.

Evidence this is real, not hypothetical: **Radar returned `400 Bad Request` on the bare Wormhole
file** and only produced findings after we added a manifest. Whatever it produced afterwards was
produced under conditions we invented.

## 5. Determinism. **CHECKED 2026-08-31: both third-party scanners are deterministic.**

Each was run twice over the same corpus and the findings compared by rule and location.

| Scanner | run 1 | run 2 | identical |
|---|---|---|---|
| `radar` | 52 findings | 52 findings | yes |
| `vaultlint` | 4 findings | 4 findings | yes |

This matters because the clock will one day print "real recall 11 -> 9, REGRESSION". Had either
tool been nondeterministic, that line would have been noise presented as signal. It is now
reasonable to read a change in the time series as a real change.

Still unverified: determinism across *versions* of the tool, across host machines, and for our own
scanner (which is pure Python over text and almost certainly deterministic, but has not been
checked, and "almost certainly" is how this project gets things wrong).

## 6. Corpus 2 selection is biased toward famous exploits.

We picked incidents with public postmortems, which means the best-documented ones, which are
exactly the cases most likely to have been turned into test material by vendors already. It is less
contaminated than the teaching corpus, not uncontaminated.

## 7. The class-to-rule mapping is still our judgement, and the right of reply is unexercised.

We derive mappings from each tool's own rule descriptions, publish them as diffable files, and
promise to publish the authors' corrections. **No author has been asked yet.** Both third-party
results are therefore provisional in a way that a reader skimming the table will not notice.

## 8. `n = 1` everywhere that matters.

Nine real cases, one run each, two third-party tools. No repetition, no confidence interval, no
sensitivity analysis. The Wormhole result is one file.

---

## Code-level gaps, concretely

| Gap | Consequence |
|---|---|
| ~~The clock only knows `radar` and `vaultlint`~~ **FIXED 2026-08-31.** `sol-audit` is now measured by the same pipeline, and the automated run reproduced the hand-computed 6 nominal / 4 real exactly. A mapping file existed for other people's scanners before it existed for ours. | |
| ~~The clock only runs the teaching corpus~~ **FIXED 2026-08-31.** Corpus 2 is scored on every run with `score2.py`, reported separately because the two corpora answer different questions. | |
| `adapters.py` contains a Semgrep adapter that **has never been executed**. Semgrep failed to install and the code path is untested. | Dead code that looks like coverage. |
| The `CargoBinary` / `VaultLint` adapter class is **dead**: VaultLint is actually run through Docker by the shell script, not through the adapter. | The adapter layer is less real than it appears. |
| `score.py` decides which class a file belongs to by testing whether `/<class>/` appears in the path. | A path containing the class name in another position would be misattributed. |
| Nothing asserts that a corpus pair actually differs. | A failed extraction would produce identical variants, every tool would score MISS, and it would look like a finding. *(Checked by hand today: all nine pairs differ. Not automated.)* |
| ~~`corpus_radar.py` has only ever been run in `--demo`~~ **RUN LIVE 2026-08-31: it finds nothing, and the reason is a design flaw of ours.** Twenty-three queries produced one regex hit, and that one was false. The acquisition layer greps search-result snippets for a raw `github.com/.../commit/` URL, but incident postmortems put that link in the page body, never in the snippet. The verification half is sound and worth keeping; the acquisition half needs rebuilding against GitHub Security Advisories and RustSec rather than web search. | A tool that looked like coverage and produced none. |
| ~~`spl-token-lending-rounding` skipped, almost certainly an artefact of shallow cloning~~ **That guess was WRONG and testing disproved it.** The SHA in the manifest was a merge commit with two parents; `git show` without `-m` prints the combined diff, which omits files identical to either parent, so the diff read as empty at any clone depth. Corrected to the squash-merge commit, which has one parent. | A cause asserted without testing it, published, and then refuted. |

---

## What we would fix first

1. **Give corpus 2 a class-to-rule mapping**, so its numbers answer the same question as corpus 1.
2. **Match findings against the fix diff hunks**, so "detected" means detected *there*.
3. **Run each scanner twice** and publish whether it is deterministic, before trusting any trend.
4. **Keep only the files the disclosure actually implicates**, instead of everything the commit touched.
5. **Put our own scanner and corpus 2 on the clock.**

Until 1 and 2 are done, the honest summary of the corpus 2 result is narrower than the headline
suggests: *no scanner produced any signal that distinguished the vulnerable version from the fixed
one, under a packaging we chose, at file granularity.* That is still a real and uncomfortable
result. It is not the same sentence as "no scanner detects real vulnerabilities", and we should not
let it be read as one.

## Added 2026-08-31, evening. Found by checking our own output rather than by being told.

**19. Ground truth was assumed, not read, for one case.** `cashio-account-data`'s fix commit
disables the program instead of repairing it. Excluded, and every other fix diff was then read
individually. **Generalised fix:** `score2.py` refuses to score any case marked `valid: false`, so
the exclusion is enforced by code rather than by a note. **Still open:** nothing automatically
detects a shutdown-shaped commit; the audit was manual and would have to be repeated for new cases.

**20. Per-class scoring cannot see a detection under an unmapped rule.** X-Ray detected a real
vulnerability under a rule we had mapped to a different class, and scored zero for it.
**Partial fix:** `unmapped_check.py` asks the complementary question across all findings and is
validated against that known case. **Still open:** it can only find candidates. Deciding whether a
candidate is a detection requires reading it, and properly requires asking the tool's authors.

**21. Radar cannot complete on large real crates.** On the real-crate corpus it exceeds its own
retry budget on the bigger projects and, when it does, still prints `Results written to <path>` for
a file it did not write. Those pairs are recorded as **unavailable**, never as zero. This is a real
limit on measuring tools against real code, and it means our real-crate coverage is biased toward
small projects.

**22. Every corpus-1 result is in-sample.** Stated in `docs/PROTOCOL.md` and repeated here because it is
the single most load-bearing caveat in the project. The teaching corpus is public, at least two of
the measured tools cite it directly as the reference for their own rules, and one vendor was closing
gaps against it on the day we measured. A holdout is the only real answer and we do not have one.

**23. The right of reply still has not been exercised with anyone.** Three threads are drafted and
assigned. Until they are answered, every third-party number in this repository is provisional, and
the X-Ray case is the proof that this is not a formality: our mapping was wrong in a way only the
tool's authors could have settled quickly.

## Added 2026-08-31, late. Both found by asking what we had not checked.

**24. The corpus-2 scorer had never returned a positive verdict, and nobody had checked it could.**
Every number this project published from corpus 2 was a zero, produced by an instrument whose only
observed output was zero. If `score_case` had a defect making `detected` unreachable, every result
would look exactly as it does. It does work - `score2.py --demo` now drives a synthetic
vulnerable/fixed pair end to end and asserts three verdicts: `detected` when a mapped rule fires at
the fix site and not on the fix, not-detected when it fires on both, and `unlocated` when it fires
far from the fix. **FIXED**, and it runs on every invocation. The uncomfortable part is that the
project wrote this exact rule into its own skill file the same day - *a check returning zero
everywhere may simply be broken* - and then did not apply it to its own scorer.

**25. Corpus 2 is selected from public postmortems, and that is a bias we never stated.**
Every case comes from a rekt.news writeup, a published audit, a GitHub Security Advisory or a
RustSec entry: Wormhole, Cashio, Solend, SPL, Squads, Metaplex, Anchor. Those incidents are
*famous precisely because nobody caught them in time*. A corpus assembled from the bugs that got
through is systematically harder than the population of real bugs, and it will understate any
scanner. It is still the right corpus for the question "do these tools catch the ones that cost
money", but it cannot support the broader claim "these tools do not work", and nothing in this
repository should be read as making it. Unfixed, and probably unfixable without a source of
disclosed-but-uncelebrated vulnerabilities.

**26. No calibration control was ever run on corpus 2.** `control-noisy` and `control-null` cover
the teaching corpus only. The corpus that carries the headline has no floor and no ceiling
established by construction. Item 24 partly substitutes for this, but a real `control-noisy` run
over corpus 2 is still missing.

**27. The line tolerance is arbitrary, so we tested whether anything depends on it. Nothing does.**
`TOLERANCE = 3` decides how close a finding must land to a changed line to count as located, and
the number was picked by hand with no justification. Sweeping it from 0 to 25 lines across every
valid corpus-2 case and all four measured tools changes **no verdict at all** - the results are
identical at every setting. The published numbers therefore do not rest on that constant. Recorded
because an unjustified constant in a scoring rule is a fair thing for a reader to attack, and the
answer should exist before they ask.

## Added 2026-08-31, deepest pass. Four findings, one of them in the headline.

**28. Radar was never run over corpus 2 as a corpus, and neither was VaultLint.** Every Radar
artefact in this repository is either the teaching corpus (complete, all 11 classes, 52 locations)
or **Wormhole alone** - twice, once as an isolated file and once as the real crate. `c2-radar.json`
holds findings from that single case. `c2clean-radar.json`, despite the name, is not a corpus-2 run
at all: its paths are `/tmp/whreal/`, the Wormhole real crate. VaultLint's corpus-2 file covers
`solend-owner-checks` only. **The published "0 of 8 real vulnerabilities" for both tools was
extrapolated from one case each.** Retracted; a per-case re-run with a log per run is replacing it.

**29. The root cause, which also explains the missing coverage.** Radar requires a `Cargo.toml` in
a **subdirectory** of the path it is given. Corpus-2 cases carry their manifest at the root, so
Radar answers `400 Bad Request: No Cargo.toml files found in any subdirectories` and analyses
nothing. Wormhole passed because of its layout; the real crates passed because the crate is nested.
Every other case was an invocation error being scored as a miss - our error, in our favour's
opposite direction, and invisible without a per-run log.

**30. The teaching corpus was not pinned anywhere.** No commit was recorded, so nothing in this
repository established which corpus state produced 11/11. Recovered after the fact from the working
checkout: `24555d044802db4022112a94d6d70e74291a4b6d`, 2022-07-16. **FIXED** in `docs/PROTOCOL.md`, with
the recovery disclosed. The corpus itself has not been touched since July 2022.

**31. `verify.py` verifies run 1 only, and the CI step claimed more.** It checks `docs/results/RESULTS.md`
(sol-audit v1, 2/11 nominal, 0/11 real) and nothing else - not the six-scanner table, not corpus 2,
not the real crates. The workflow step was labelled "Published headline reproduces from raw data".
**Step renamed and the scope stated in the module docstring.** Nothing currently re-derives the
current headline from raw data, and that remains open.

**32. `control-noisy`'s corpus-1 numbers have no raw file in this repository.** The 931 findings and
its 11/11 nominal / 0/11 real appear in two results pages with nothing stored to re-derive them
from. The control is deterministic and cheap to re-run, so this is weaker than 28, but it is the
same species: a published number with no artefact behind it.

## Added 2026-09-01, on building eight new cases

**33. Eight of the seventeen valid cases have never been analysed by anything.** They were built on
2026-09-01 and no scanner has been run over them. They carry `"measured": false` in the manifest,
`run_all.py` reports them as `not-run` or `unknown`, and every corpus-2 row it produces now reads
`partial`. **Nothing here is a zero on them.** The corpus grew; the measurement did not, and until
it does, "17 cases" is a statement about ground truth and "0 / 8" is a statement about scanners,
and the two must not be printed as one fraction.

**34. Nothing in the new pairs was compiled, because there is no Rust toolchain on the machine that
built them.** The pairs are exact file contents at the fix commit and its parent, extracted by
`git show`, so their *fidelity* is not in question. What is unverified is whether either variant
builds in the minimal crate `build_corpus2.py` writes around it: every pinned file has imports and
callees that the extracted crate does not contain. This is limitation 4 in a sharper form. It
matters most for `token-2022-confidential-approve-mint`, whose real crate pulls the zk proof crates,
and for `solido-deposit-reserve-account`, whose parent commit deliberately contains a failing test.
**No claim is made here that any new case compiles.**

**35. `solido-anker-arbitrary-cpi` pins the check but not the sink.** The missing validation is in
`anker/src/state.rs`; the `invoke_signed` it protects is in `anker/src/processor.rs`, which is
excluded because its role in the fix commit is to thread an argument through. A scanner that needs
to see the source and the sink in one file cannot see this bug in this pair, and should be scored
`no-rule` or `missed` on it with that in mind rather than credited with a general blindness.

**36. Two of the new cases have a severity their own auditor disputes.** `squads-recursive-execute`
is graded **Info** by Neodyme, with "no impact, except for inconsistency" written in the report's
own table. It is built with a `severity_note` carrying that quote, and it is flagged for a human
decision, because the sibling candidate `squads-attach-ix-program-id` was held back partly for the
same reason and consistency has to run one way or the other. **A corpus of "real vulnerabilities"
containing a case its auditor says has no impact is a claim this project should either defend or
withdraw, not leave ambiguous.**

**37. `anchor-account-reload-owner` rests on a pull request title.** No advisory, no audit finding.
Acceptance criterion 4 exists so the label is not our opinion, and here it is thinner than anywhere
else in the corpus. It carries a `source_strength_note` saying so. Note also that a comparable
unsourced owner check, SPL `23c487dd`, was rejected on exactly that ground; the difference is that
this one is in a class nothing else covers and that one is in the corpus's heaviest class, which is
a defensible distinction but a distinction a reviewer is entitled to challenge.

**38. `raw/c2-control-noisy.json` is stale with respect to the enlarged corpus.** The published
count was recomputed and the control was re-scored case by case, so the number and the zero are
both current, but the artefact in `raw/` was left as it was because another agent was writing to
that directory at the time. `python tools/control_c2.py` regenerates it.
