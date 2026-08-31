# RESULTS: multiple scanners, 2026-08-31

First run of this benchmark against a scanner that is not ours. Same corpus, same protocol, same
scoring code for every tool. Raw data: `radar-full.json`. Mapping: `mappings/radar.json`.

## The table

| Scanner | Nominal recall | **Real recall** | Findings | On already-fixed code | Noise per file |
|---|---|---|---|---|---|
| `control-noisy` (flags every line) | 11 / 11 | **0 / 11** | 931 | almost all | 26.6 |
| `control-null` (reports nothing) | 0 / 11 | **0 / 11** | 0 | 0 | 0 |
| `sol-audit` v1 (ours, as sold) | 2 / 11 | **0 / 11** | — | 15 | 0.7 |
| `sol-audit` v2 (ours, repaired) | 6 / 11 | **4 / 11** | — | 23 | 1.0 |
| **`radar`** (Auditware) | **11 / 11** | **11 / 11** | 52 | **24 (46%)** | 0.69 |

## Read the control rows first

They are not filler. They are what makes the rest of the table mean anything.

`control-noisy` flags every non-empty line of every file. It produces **931 findings** and a
**perfect nominal recall of 11/11** — and **zero real recall**. Any metric based on counting
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

**Provisional.** Under `PROTOCOL.md` a third-party mapping should be offered to the tool's authors
for correction before the number is treated as final, and their correction published. That has not
been done yet for Radar. `mappings/radar.json` records this.

The mapping was derived from Radar's own rule names as emitted in its JSON output, not from which
rules happened to fire. Four Radar rules name no class in this corpus and are excluded from
per-class scoring; a scanner is not penalised for detecting things the corpus does not label. Their
behaviour on fixed code is still reported above, because firing on a correct program is
informative whether or not the corpus has a label for it.

## Reproduce

```
python score.py --demo                              # self-check the scoring logic
python score.py mappings/radar.json radar-full.json # rescore Radar from raw output
python adapters.py                                  # which scanners are available here
```
