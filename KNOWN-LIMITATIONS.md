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
requires the finding to land at the site the fix changed. Results in `RESULTS-corpus2.md`. The
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

## 3. Corpus 2 pairs contain files that have nothing to do with the vulnerability.

We extract every `.rs` file the fix commit touched. `metaplex-bubblegum-creator` yields six files,
`wormhole-sysvar` three. Most fix commits also rename things, adjust imports, or touch a test
helper. Those files are packaged as part of a "vulnerability pair" and they are not one.

Worse, a fix that refactors while fixing produces differences unrelated to the bug, which can
manufacture a false "detection": a rule fires on code that was simply moved.

## 4. Our packaging of corpus 2 may itself cause the failures we report.

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
| `corpus_radar.py` has only ever been run in `--demo`. | Unknown whether it produces anything usable against live sources. |
| `spl-token-lending-rounding` was skipped as "fix touches no .rs file", which is almost certainly an artefact of shallow cloning rather than the truth. | One good case silently dropped. |

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
