# RESULTS: multiple scanners, 2026-08-31, Radar re-measured 2026-09-02

First run of this benchmark against a scanner that is not ours. Same corpus, same protocol, same
scoring code for every tool. Raw data: `radar-full.json`. Mapping: `mappings/radar.json`.

## The table

| Scanner | Nominal recall | **Real recall** | Findings | On already-fixed code |
|---|---|---|---|---|
| `control-noisy` (flags every line) | 11 / 11 | **0 / 11** | 81,928 | almost all |
| `control-null` (reports nothing) | 0 / 11 | **0 / 11** | 0 | 0 |
| `sol-audit` v1 (ours, as sold) | 2 / 11 | **0 / 11** | - | 15 |
| `sol-audit` v2 (ours, repaired) | 6 / 11 | **4 / 11** | - | 23 |
| **`radar`** (Auditware, main of 2026-08-31) | **11 / 11** | **11 / 11** | 52 | 24 (46%, upper bound; vendor reports 40% after #34, re-measured below) |
| **`radar`** (Auditware, main after #35, `24c56f9`, 2026-09-02, docker image) | **11 / 11** | **11 / 11** | 36 | 14 (39%, upper bound) |
| **`radar`** (Auditware, main after #36 and #37, `67348ee`, 2026-09-02, engine shim) | **11 / 11** | **11 / 11** | **19** | **2 (11%, upper bound)**, confirms the vendor's own figures |
| **`radar`** (Auditware, main `fa81c25`, 2026-09-04, engine shim, corpus 2 re-run) | **11 / 11** | **11 / 11** | 19 | 2 (11%, upper bound); on corpus 2, `wormhole-sysvar` goes **missed → detected** at the pre-registered fix sites (`verify_signature.rs:92`, `:101`), exactly as the vendor reported in `radar#32` — detected 0→1, missed 7→6, everything else unchanged ([RESULTS-corpus2.md](RESULTS-corpus2.md)) |
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
> it stays vendor-reported until we re-measure that release as a new row. The mapping stayed
> pre-registered until 2026-09-03, when the vendor confirmed it in the thread: "As far as we can
> tell mappings/radar.json is correct — all 11 lines match our rule names verbatim, so we'd say
> publish as is" (`radar#32` comment 5523410629; an earlier version of this note said they had
> confirmed it, which the thread did not support at the time — error 41; it does now).

**Re-measured, 2026-09-02, as a new row.** Radar at `main` after #35 (checkout `24c56f9`, api image
`ghcr.io/auditware/radar-api@sha256:f205bf7a9af877e1f5426322d1445723362ae72c9ed23f53432fd698e997af7e`,
built from that revision at 2026-09-01T19:45Z; the rules live inside the image, not in the checkout,
so the image digest is the version) through `tools/scanner_spec.py`, same declaration, same
pre-registered mapping, `--repeat 2`, deterministic on both corpora. Teaching corpus: **36 findings,
14 on `secure` or `recommended`, 39%**, recall 11 / 11 nominal and real, unchanged. The vendor's
own figure of 40% with recall 13/13 is therefore reproduced within rounding (they count their 13
classes, we count the corpus's 11). What fell: Missing Signer Check 10 to 2, Missing Token Mint
Constraint 5 to 5, Missing Transfer Amount Validation 3 to 3, Missing has_one Constraint 3 to 2,
Missing Owner Check 2 to 2, Unvalidated Price Data Account 1 to 0. Real vulnerabilities (corpus 2):
34 invocations, 34 ok, 228 findings (231 before), **zero detections at a fix site**, 7 missed, 8
no-rule, 2 unlocated, as before. The 39% is still an upper bound for the reason in the correction
above. Raw: `raw/radar-24c56f9-c1.json` and `raw/c2-radar-24c56f9.json` with their `.log`,
`.run2` and `.determinism.json` files, per-invocation artefacts under `raw/radar-c1-2026-09-02-24c56f9/`
and `raw/radar-c2-2026-09-02-24c56f9/` (each with a README naming the digests). The 2026-08-31 row
above stays as published; the images it ran on are kept locally as `measured-2026-08-31`.

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
engineering is verified at source rather than taken on trust, and the sequence it records -
reproduce first, narrow, catch their own regression with adversarial fixtures outside our corpus,
revert part - is the right-of-reply protocol working as designed.

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
`ENGINEERING-LOG-2026-09-02.md`.

**Two divergence paths named by the vendor, published here because we asked for exactly this.**
On 2026-09-03 `forefy` answered the open invitation to point at any path where the container and
the library path could differ:

> rules are baked into the image (api/Dockerfile:113), so docker = digest and shim = commit; and we
> filter templates by detected framework, which looks inert on all 17 pack cases but could bite if
> one detected as anchor.

Both stand against this row and neither is disputed. The first means this row's version identity is
a **commit** while every docker row above identifies a **digest**, and those are not the same object:
a digest pins the rules, a commit pins the source they were built from. The second is a real
mechanism by which the shim and the image could select different templates, unobserved on our cases
but not excluded by them. Neither invalidates the parity artefact, which was measured location for
location; both are reasons this row should be re-measured under docker before it is leaned on.

The in-sample caveat below applies to this row exactly as it applies to the last: 11/11 on a public
2022 corpus is 11/11 of homework, not of generalisation.

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

**The mapping has now been confirmed by the vendor.** Under `docs/PROTOCOL.md` a third-party mapping
is offered to the tool's authors for correction before the number is treated as final, and their
answer published next to it either way. Asked on `radar#32` on 2026-09-01 and again on 09-02,
answered by `forefy` on **2026-09-03 09:12Z**:

> As far as we can tell mappings/radar.json is correct — all 11 lines match our rule names
> verbatim, so we'd say publish as is.

So the Radar rows above are no longer provisional on mapping grounds. They remain bounded by
everything else stated on this page: the noise column is an upper bound (error 39), and 11/11 on a
public 2022 corpus is in-sample.

*Before 2026-09-03 this section read "That has not been done yet for Radar." It was true when
written and stopped being true the moment the vendor answered; it is replaced rather than annotated,
because a correction added above a false sentence leaves the false sentence in the file.*

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
