# RESULTS: multiple scanners, 2026-08-31

First run of this benchmark against a scanner that is not ours. Same corpus, same protocol, same
scoring code for every tool. Raw data: `radar-full.json`. Mapping: `mappings/radar.json`.

## The table

| Scanner | Nominal recall | **Real recall** | Findings | On already-fixed code |
|---|---|---|---|---|
| `control-noisy` (flags every line) | 11 / 11 | **0 / 11** | 81,928 | almost all |
| `control-null` (reports nothing) | 0 / 11 | **0 / 11** | 0 | 0 |
| `sol-audit` v1 (ours, as sold) | 2 / 11 | **0 / 11** | - | 15 |
| `sol-audit` v2 (ours, repaired) | 6 / 11 | **4 / 11** | - | 23 |
| **`radar`** (Auditware, main of 2026-08-31) | **11 / 11** | **11 / 11** | 52 | 24 (46%, upper bound; vendor reports 40% after #34, not yet re-measured by us) |
| **`radar`** (Auditware, main of 2026-09-02, post-#36) | **11 / 11** | **11 / 11** | **19** | **2 (11%, upper bound)** — measured by us; confirms the vendor's own figures |
| **`vaultlint`** 0.1.1 | 2 / 11 | **2 / 11** | **4** | 1 (25%) |

Two scanners, two opposite strategies, and the benchmark separates them cleanly. That separation is
the whole reason to have one.

## Read the control rows first

They are not filler. They are what makes the rest of the table mean anything.

`control-noisy` flags every non-empty line of every file. It produces **81,928 findings** and a
**perfect nominal recall of 11/11** - and **zero real recall**. Any metric based on counting
findings would rank it first. Ours ranks it last, which is the point.

`control-null` reports nothing and scores zero on both.

**So a real recall of 11/11 cannot be bought with volume.** That is the calibration that lets us
report Radar's score without hand-waving.

## Radar: excellent detectors, noisy periphery

Radar detects **every one of the eleven classes correctly**: it fires on the vulnerable program and
stays silent on the same program fixed. Eleven out of eleven. Our own repaired scanner manages four.

That is the honest headline and it is not comfortable for us. A tool built by people who do this
properly is roughly three times better than ours on the axis that matters.

But the second column matters too. **24 of Radar's 52 findings, 46%, land on code that is already
fixed.** The offenders are its generic rules rather than its class detectors:

> **Correction, 2026-09-01 (error 39).** The 46% is an **upper bound, not a measurement**, for
> every scanner in this table. The corpus labels a variant secure *with respect to its own class*,
> and this column counts every firing on a secure variant as noise. A scanner that correctly finds a
> different real flaw in a fixed file is therefore penalised for being right. Auditware's maintainer
> pointed this out on `radar#32` with an example: `9-closing-accounts/recommended` has no signer
> check and lets any caller drain it, and Radar flagging it is correct. Fixing the metric needs a
> per-variant, per-class ground truth the corpus does not carry, so the column keeps its label and
> gains this note.
>
> **Vendor reply, same thread.** Before changing anything they reproduced this figure independently
> (23 of 50 firings, same rule breakdown). They then narrowed the rules (#33, reported 35%), wrote
> adversarial fixtures outside our corpus, found the narrowing had broken four real detections, and
> reverted part of it (#34). The figure they asked us to publish for the current release is
> **46% to 40%, recall unchanged at 13/13**. The 46% in the table is our measurement of the `main`
> we installed on 2026-08-31, before #33 and #34; the 40% is theirs, on code we have not run, and
> it stays vendor-reported until we re-measure that release as a new row. The mapping stays as
> pre-registered; the vendor has not commented on it either way (an earlier version of this note
> said they had confirmed it, which the thread does not support; error 41).

| Radar rule | findings on fixed code |
|---|---|
| Missing Signer Check | 10 |
| Missing Token Mint Constraint | 5 |
| Missing Transfer Amount Validation | 3 |
| Missing has_one Constraint | 3 |
| Missing Owner Check | 2 |
| Unvalidated Price Data Account | 1 |

Two of these fire **more often on the `recommended` variant than on the vulnerable one**, and
`Unvalidated Price Data Account` fires *only* on fixed code. That is the same failure mode that
gave our own v1 a real recall of zero, surviving inside a tool that is otherwise excellent.

**Recall and noise are different axes.** A scanner can be first on one and unremarkable on the
other, and a single ranking number would hide it. This is why the benchmark reports both.

## Re-measured 2026-09-02: the vendor's fix is real, and it is better than they claimed

The row above dated 2026-09-02 is the re-measurement promised on `radar#32`: the vendor's `main`
at `67348ee`, after their noise-reduction PRs #33/#34/#35/#36 and the dependency bump #37,
against the same corpus at the same pinned commit, scored with the same pre-registered mapping.

Measured by us, not vendor-reported: **real recall unchanged at 11/11**; findings **52 → 19**;
firings on already-fixed variants **24 → 2**. The vendor's own figures for the same release were
2 false positives and an 11% noise rate; our independent run lands on exactly that. Their
engineering is verified at source rather than taken on trust, and the sequence it records —
reproduce first, narrow, catch their own regression with adversarial fixtures outside our corpus,
revert part — is the right-of-reply protocol working as designed.

The two remaining firings on fixed code are both `Missing Owner Check` on `secure` variants of
`1-account-data-matching` and `4-initialization`. The error-39 caveat applies to this row as to
every other: the column is an upper bound, because a correct cross-class firing on a variant
labelled secure-for-its-own-class is counted as noise.

Method disclosure: this run, unlike every earlier radar row, was made without a docker daemon,
through an engine shim that executes the vendor's own pipeline code unmodified from their
checkout at `67348ee`. Before measuring, the shim was parity-proven against the docker
measurement of the older revision `206a469`: **52 of 52 location rows identical, rule for rule,
file for file, line and column for line and column** (`raw/radar-shim-parity-2026-09-02/`).
The full reasoning, and what the shim does and does not claim, is
`ENGINEERING-LOG-2026-09-02.md`. The in-sample caveat below applies to this row exactly as it
applies to the last: 11/11 on a public 2022 corpus is 11/11 of homework, not of generalisation.

## VaultLint: the precision claim holds, and you can see what it cost

VaultLint advertises precision as its differentiator. **The measurement supports the claim.**
Everything it detected, it detected correctly: two classes, both real, no nominal-only detections,
nothing dressed up as a find. Where Radar has nine clean detectors and six noisy rules, VaultLint
has no noisy detectors at all among the ones it maps to.

The price is coverage. It produced **four findings across 35 files**, against Radar's 52, and it
touches three of eleven classes. Real recall 2/11.

One finding is worth recording precisely because it does not cost VaultLint anything in the score:
`VL002 (missing owner check)` fired on **both** the insecure and the secure variant of
`4-initialization`, a class it is not mapped to. Under per-class scoring that is neither punished
nor rewarded, which is correct. It is counted in the noise column, because firing on an
already-fixed program tells you something whatever the file is labelled.

**So the two tools are not on a single ladder.** Radar catches everything and shouts sometimes.
VaultLint says little and is right when it does. Which you want depends on whether an ignored alert
or a missed bug is worse in your workflow, and a single ranking number would have erased that
entirely. This is the clearest argument in the whole project for reporting both axes.

## The caveat that matters more than the score

**Radar's own README uses `radar -p sealevel-attacks` as its usage example.** Its authors know this
corpus and have every reason to have tuned against it. An 11/11 here should be read as
**in-sample for Radar**, exactly as our 4/11 is in-sample for us.

This is not an accusation. It is the expected outcome for a public corpus that has been available
for years, and it is the single strongest argument for the next piece of work: **this corpus can no
longer discriminate between a tool that generalises and a tool that has done its homework.** A
corpus assembled from real programs with publicly disclosed vulnerabilities, where the fix commit
is the answer key, is the only way to tell those apart.

## Status of this measurement

**Provisional.** Under `docs/PROTOCOL.md` a third-party mapping should be offered to the tool's authors
for correction before the number is treated as final, and their correction published. That has not
been done yet for Radar. `mappings/radar.json` records this.

The mapping was derived from Radar's own rule names as emitted in its JSON output, not from which
rules happened to fire. Four Radar rules name no class in this corpus and are excluded from
per-class scoring; a scanner is not penalised for detecting things the corpus does not label. Their
behaviour on fixed code is still reported above, because firing on a correct program is
informative whether or not the corpus has a label for it.

## Reproduce

```
# from the repository root
python tools/score.py --demo                                  # self-check the scoring logic
python tools/score.py mappings/radar.json raw/radar-full.json # rescore Radar from raw output
python tools/controls.py                                      # which scanners are available here
```
