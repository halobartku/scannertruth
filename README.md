# ScannerTruth

[![verify](https://github.com/halobartku/scannertruth/actions/workflows/verify.yml/badge.svg)](https://github.com/halobartku/scannertruth/actions/workflows/verify.yml)

Every self-check, the headline reproduction, and the corpus-2 calibration controls run on GitHub's
machines on every push. A green badge is not independent verification, but the checks run somewhere
we do not control and you can read what they assert.

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




## What comes next

[`ROADMAP.md`](ROADMAP.md) carries four funded milestones, each ending in an artefact a funder can
check without trusting us. The largest engineering items are the ones this project's own audit
exposed: a corpus engine that turns an advisory into a validated pair with a false-fix detector, and
a variance harness for **AI auditors**, which are non-deterministic and therefore cannot be measured
the way a conventional scanner is. Measuring one once, which is what everyone does today, is
worthless.

## Hand this repository to an agent

`AGENTS.md` is the entry point for an AI agent asked to measure a scanner. It carries the whole
procedure: provenance before install, container isolation, a mapping pre-registered before the run,
a log per run proving every case was analysed, shift-aware comparison, and the rules that override
anything an agent might otherwise infer.

The point of the project stated as a capability: **you should not need to be a security engineer to
find out whether a scanner works.** You need a corpus somebody else's maintainers wrote the answer
key for, a scorer that cannot be fooled by volume, and a procedure an agent can follow without
supervision. That is what is in here.

## Skills

The method, written as three executable procedures rather than prose, because the same mistakes are
available every time and two of them produced public retractions:

| Skill | Job | Why it is separate |
|---|---|---|
| [`measure-a-scanner`](skills/measure-a-scanner/SKILL.md) | run a tool against a corpus | provenance, containers, pre-registered mapping, proof every case was analysed |
| [`add-a-corpus-case`](skills/add-a-corpus-case/SKILL.md) | build and validate ground truth | a fix commit that disables the program is not a fix; scope and its rejections go in writing |
| [`publish-a-measurement`](skills/publish-a-measurement/SKILL.md) | publish, correct, retract | retract before the replacement exists; correct the mechanism, not only the number |

They are split this way because the corpus, not the scoring, is the asset. Running a tool and
building the thing you run it against fail in completely different ways.

## What this project actually is

The corpus every Solana scanner is measured against, `coral-xyz/sealevel-attacks`, was last touched
on **2022-07-16**. Eleven hand-written teaching programs, four years old, public, and cited directly
in at least two vendors' own rule tables. One vendor merged pull requests titled "close the last
corpus gaps" against it on the day we measured them.

That is not a benchmark. It is a **teaching aid that everyone has memorised**, and a score on it
measures how thoroughly a tool has done its homework, not whether it generalises.

So the interesting question is not who wins on that corpus. It is **what happens off it** - and
answering that requires ground truth that did not exist. Building it is the work:

- **Corpus 2**: real production vulnerabilities, each taken from the maintainers' own fix commit
  and its parent, so the answer key is somebody else's. Nine valid cases today.
- **Real crates**: the same vulnerabilities as whole projects rather than extracted files, 927
  `.rs` files, which retires the packaging objection instead of arguing about it.
- **Acquisition**: `corpus_ghsa.py` reads advisory databases, where a fix commit is a structured
  field rather than prose to be mined. It scanned 1,200 Rust advisories and proposed candidates
  with the out-of-scope ones rejected in writing.
- **A sealed holdout**, committed by hash before the round it scores.

**The protocol is copyable. Anyone can read `PROTOCOL.md` and reimplement the scoring in an
afternoon.** What is not copyable is fresh, verified, growing ground truth and the record of how
each case was checked. That is the asset, and it is also the thing that decides whether this
project deserves to continue: if the corpus stops growing, there is nothing here.


**Six scanners, eight real vulnerabilities, one detection between them.** Radar, VaultLint,
X-Ray (sec3), solsec, semgrep and ours, measured with one protocol on the same day. Full table:
[`RESULTS-all.md`](RESULTS-all.md).

**Run 5, 2026-08-31: eight valid real vulnerabilities.** Corpus 2 is built from
production Solana programs at the maintainers' own fix commit and its parent: Wormhole, Cashio,
Solend, Squads, three Metaplex advisories and one against Anchor itself. Radar scores **11/11 on the
teaching corpus and 0/8 here**; ours scores 4/11 and 0/8. Scored more strictly than corpus 1: a
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
