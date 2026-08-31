# ScannerTruth

**An open, reproducible benchmark for Solana security scanners. The first tool it measured was our
own, and our own scored zero.**

Everyone building on Solana relies on automated security scanners. Almost nobody knows how well any
of them work. Vendors publish finding counts. **Finding counts are not recall.** A scanner that
flags fixed code as often as vulnerable code will produce an impressive number and catch nothing.

We know this because we measured it on our own product.

## The result

`sol-audit`, our own static scanner for Solana and Anchor programs, which we were selling:

| Metric | Result |
|---|---|
| Nominal recall | **2 / 11** |
| Real recall | **0 / 11** |

Both apparent detections fired identically on the **fixed** version of the same program. On one
class it fired *more* on the idiomatic, safe variant than on the vulnerable one.

We published this, rewrote the product listing to lead with it, and set the price to zero the same
day. Full numbers in [`RESULTS.md`](RESULTS.md).

**Run 2, 2026-08-31.** The scanner was then repaired and re-measured. Real recall **0/11 to 4/11**.
See [`RESULTS-v2.md`](RESULTS-v2.md) and [`sol-audit`](https://github.com/halobartku/sol-audit).
Run 1 is left exactly as published; a benchmark that rewrites its own history is worthless.

**Run 3, 2026-08-31: the first scanner that is not ours.** Auditware's Radar scores **11/11 real
recall**, against our repaired scanner's 4/11. Two control scanners calibrate the metric: one that
flags every line scores 11/11 nominal and **0/11 real**, so a real-recall score cannot be bought
with volume. Radar also puts **46% of its findings on already-fixed code**. Full table and the
in-sample caveat in [`RESULTS-scanners.md`](RESULTS-scanners.md).

**Six scanners now, and on real vulnerabilities none of them detects anything.** Radar, VaultLint,
X-Ray (sec3), solsec, semgrep and ours, measured with one protocol on the same day. Full table:
[`RESULTS-all.md`](RESULTS-all.md).

**Run 5, 2026-08-31: nine real vulnerabilities, no detections by anything.** Corpus 2 is built from
production Solana programs at the maintainers' own fix commit and its parent: Wormhole, Cashio,
Solend, Squads, three Metaplex advisories and one against Anchor itself. Radar scores **11/11 on the
teaching corpus and 0/8 here**; ours scores 4/11 and 0/9. Scored more strictly than corpus 1: a
detection must fire at the site the fix changed. [`RESULTS-corpus2.md`](RESULTS-corpus2.md).

**Run 4, 2026-08-31: the first out-of-sample case, and nobody caught it.** The Wormhole
sysvar-check bug, 320 million dollars, taken from the real fix commit and its parent. Radar scores
11/11 on the teaching corpus and **does not detect it**; every finding it produces fires identically
on the vulnerable and the fixed program. So does ours. VaultLint reports nothing.
[`RESULTS-wormhole.md`](RESULTS-wormhole.md).

**How all of this was actually built, mistakes included:**
[`ENGINEERING-LOG-2026-08-31.md`](ENGINEERING-LOG-2026-08-31.md) is the full record of the day this
benchmark was made, in order, with fifteen errors recorded. Eleven were caught by measurement,
four by a person noticing, and two would have put a false statement in a funding application.

**What is wrong with all of this:** [`KNOWN-LIMITATIONS.md`](KNOWN-LIMITATIONS.md) lists every
weakness we know of in our own method and code, ordered by how much damage each does. It opens with
an error we made and published on the same day. A measurement project that only documents other
people's flaws is not a measurement project.

## Independence

Three standing promises, made while this project has one measured scanner, no users and nobody
offering it money: **the data is open and free, our own scanner stays free and open source, and we
take no money from anyone we measure.** Full text and the reasoning in
[`COMMITMENTS.md`](COMMITMENTS.md).

## Why the ground truth is not a matter of opinion

The corpus is [`coral-xyz/sealevel-attacks`](https://github.com/coral-xyz/sealevel-attacks),
maintained by the Anchor team. Every vulnerability class ships the same program twice: once with the
bug (`insecure`) and once with it fixed (`secure`, `recommended`).

So a finding of class *C* on the fixed variant of class *C* is a false positive **by construction**.
There is nothing to adjudicate. That property is what makes this measurable at all.

We do not write the answer key. A benchmark whose author also writes the answer key is not a
benchmark.

## Run it

```
python verify.py          # re-derive the published headline from the raw data
python verify.py --demo   # self-check the scoring logic on constructed cases
python rb.py              # rerun the full benchmark (needs the corpus, see PROTOCOL.md)
```

`verify.py` exits non-zero if `benchmark-raw.json` does not reproduce what `RESULTS.md` claims.
If they disagree, `RESULTS.md` is the thing that is wrong.

## Contents

| File | What it is |
|---|---|
| [`PROTOCOL.md`](PROTOCOL.md) | scoring rules, the class-to-rule mapping, what was corrected and what cannot be verified |
| [`RESULTS.md`](RESULTS.md) | the numbers, per class |
| `rb.py` | the harness |
| `scanner.py` | the scanner under test, `sol-audit`, stdlib only |
| `benchmark-raw.json` | raw per-class output |
| `verify.py` | re-derives the headline; runnable check |

## Honest limits

- **One scanner has been measured. One is not a survey.** Extending this to VaultLint, sec3/Soteria,
  Radar and others is the work that has not been done yet.
- Eleven classes, from a corpus last updated in 2024. Extending it with real Anchor programs
  carrying publicly disclosed vulnerabilities, where the fix commit is the answer key, is the
  obvious next step.
- Recall against a labelled corpus is a lower bound on real-world safety, not a measure of it.
- Three of the eleven classes have no corresponding rule in the scanner under test at all. They are
  counted as misses, because a scanner that cannot detect a bug does not detect it.
- **The pre-registration of the mapping is not independently timestamped.** The workspace predates
  this repository and had no version control. This is stated in full in `PROTOCOL.md` rather than
  left for someone to notice.

## Why this exists

A project can adopt a scanner, satisfy a compliance requirement, and be no safer than before, with
no mechanism anywhere that would reveal it. The interesting output of a standing benchmark is not
the ranking. It is the day a widely used scanner quietly regresses and the numbers show it.

Built as part of [Forge](https://github.com/halobartku), an experiment in what an autonomous agent
can and cannot do in the open. The engineering here is substantially done by that agent, operated
and signed off by a human. Every number in this repository is reproducible from the code and the
raw data, so none of that has to be taken on trust.

MIT licensed.
