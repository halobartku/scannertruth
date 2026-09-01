# Roadmap

Four milestones, 25% each. Every one ends in an **artefact a funder can check without trusting us**:
a command to run or a page to open, not a progress report.

If a criterion is not met, the tranche is not due. None of the criteria below require our
interpretation.

## What already exists, before the first dollar

Not a prototype and not a plan. Measured on 2026-09-01 by counting the repository, so every figure
below is checkable in thirty seconds.

### Built and running

| | |
|---|---|
| **2165 lines** of Python across **15 tools**, plus a suite of **106 checks**, verified by mutation | `score.py`, `score2.py`, `run_all.py`, `holdout.py`, `control_c2.py`, `unmapped_check.py`, `shiftaware.py`, `corpus_ghsa.py`, ... |
| **1,625 lines** of documentation across 15 files | protocol, results, limitations, engineering log |
| **46 commits**, all public | every correction visible in history |
| **3 skills** | the method as executable procedure, not prose |
| **CI on machines we do not control** | the test suite, every self-check, the headline reproduction and the calibration controls, on every push |

### Measurement, done

- **Six scanners measured** with one protocol on the same day, plus **two calibration controls**.
- **A published mapping per tool**, each derived from the tool's own rule names and documentation
  and carrying a written `derivation`. The seven measured on 2026-08-31 were committed in the same
  commit as the result they score, so their ordering rests on our word rather than on a timestamp.
  This page claimed them as "pre-registered, committed before their runs" until 2026-09-01; that is
  retracted, and the rule is enforced from here on rather than asserted. Which mappings have git
  evidence and which do not is output, not prose: `python tools/preregistration_check.py`, and
  `docs/PROTOCOL.md` 3a.
- **Three corpora**: the public teaching set (pinned at `24555d04`), the real vulnerabilities in
  `corpus2/manifest.json` taken from their maintainers' own fix commits, and the same bugs rebuilt
  as **real crates**, per-case counts in `docs/results/RESULTS-realcrates.md`. The real crates are
  built on demand rather than committed, so a total file count is not quoted here (error 23).
- **26 raw output files** published, so every number can be re-derived rather than believed.
- **A clock** that re-measures on a schedule and diffs against the previous run, with two dated
  entries already published. A ranking can be produced once; a regression only shows up if the
  measurement repeats.

### The parts that make it a measurement rather than an opinion

- **`control-noisy`**: flags every non-empty line, 931 findings on one corpus and **1,413,620** on the
  other, and scores **zero real recall on both**. Proof the metric cannot be bought with volume.
- **A positive control on the scorer itself**, because until it was added the scorer had never once
  returned a detection and nobody had checked that it could.
- **A per-run log** proving each case was actually analysed, for Radar and VaultLint. Ours does not
  have one yet, which is milestone 1.
- **A test suite whose selection rule is "would a defect here change a published number"**, covering
  line-shift mapping, every scoring verdict, the controls, holdout commitments, and the coverage
  bookkeeping whose absence caused the retraction. Writing it immediately exposed a module that ran
  its analysis at import time and therefore could not be tested at all.
- **A sealed holdout**, committed by hash before the round it scores.
- **Right of reply**: four threads open with the vendors we measured. Every third-party number is
  marked provisional until they answer.
- **21 of our own errors**, documented with dates, including a headline we retracted in public
  before we had the replacement data.

### What the money is actually for

**Corpus scale** (9 cases is our largest stated weakness), **measurement of non-deterministic AI
tools** (nobody is doing this and the wave has already started), and **making this usable by
somebody other than us** (today the answer to "has anyone outside verified it" is no).

---

## Milestone 1 (25%). Close the foundation, starting with our own gaps.
**Two weeks.**

- **`adapters/` as a framework rather than a pile of scripts.** Declare a name, a container command
  and an output parser; the per-run log, unavailability classification and determinism check come
  for free. **Adding a seventh tool should be a config file, not a day.**
- **A run log for everything.** Radar and VaultLint have one; our own `sol-audit` does not. We
  closed other people's tools more rigorously than our own, and that gets fixed first.
- **All six tools across all three corpora.** X-Ray, solsec and semgrep have never been run against
  the real crates. No empty cells afterwards, and anything that cannot run is listed with a reason.
- **`report.py` and a published results page**, where every number links to the raw data behind it.

**Check:** `python tools/run_all.py --verify-coverage` reports zero `coverage_evidence: none`, and the
page resolves with every figure traceable to its raw file.

---

## Milestone 2 (25%). The corpus engine. This is the actual product.
**Three weeks.**

- **`build_case.py`: advisory to validated pair, automatically.** Acquisition already proposes
  candidates; building a case is still manual. This closes the path: advisory, fix commit,
  **check that it repairs rather than disables**, extract both variants as file and as real crate,
  propose a class, and hand a human a card to accept or reject.
  The human stays in the loop deliberately. An automaton that adds its own cases would have let in
  a second Cashio.
- **A false-fix detector.** Rules for commits that switch code off instead of repairing it
  (`invariant!(false)`, `unimplemented!`, deleted paths), plus merge-commit detection where the
  combined diff hides the implicated file. Every rejection lands in `docs/CANDIDATES-TRIAGE.md` **with
  its reason**.
- **Corpus from 9 to at least 25 valid cases**, grown by acquisition rather than by remembering
  famous hacks. This attacks our largest stated limitation: sample size.
- **Holdout round 2, this time with concealment.** Round 1 gives timestamp integrity only, because
  its case came from a public shortlist. Round 2 measures a case nobody outside the project has
  seen, then publishes the case alongside the result.

**Check:** `build_case.py --advisory <id> --dry-run` walks the whole path without adding anything;
`holdout.py verify` confirms the released spec hashes to the sealed commitment; the corpus holds
25+ valid cases, each linked to its maintainers' own fix commit.

---

## Milestone 3 (25%). Measuring AI auditors. Nobody is doing this.
**Four weeks.**

A conventional scanner is deterministic: same code, same answer, check it once. **An AI auditor is
not.** The same code can produce a different answer tomorrow after a model or prompt change, so
measuring it once is worthless, and measuring it once is what everyone currently does. We have
already had to exclude one such tool from a measurement because it required a paid API key. The wave
has started.

- **`variance.py`: repeatability as a first-class number.** Every non-deterministic tool runs **n
  times on the same case**, and the result is not just detection but spread. A tool that finds the
  bug in three runs out of ten **is a 30% tool, not a 100% tool**, and will be reported that way.
- **A model-backed adapter** that records which model and which prompt version was measured.
  Without that, the result is not reproducible even for us.
- **At least three AI auditors measured and published**, with spread, cost per run, and whether they
  can be run repeatably at all.
- **The protocol extended for non-determinism**, written **before** the measurement, because a
  definition of real recall for a tool that answers differently each time is exactly the thing that
  must not be decided after seeing scores.

**Check:** `tools/variance.py --scanner <tool> --runs 10 --case <case>`, which does not exist
yet, reports detections, spread
and cost; the results page carries a repeatability column; the protocol change is committed before
the first measurement.

---

## Milestone 4 (25%). Used by somebody who is not us.
**Four weeks.**

This is the milestone that decides whether this was a measurement institution or a hobby with a tidy
repository.

- **A machine-readable public feed.** Results as versioned JSON at a stable URL, so anyone can pull
  them into their own CI or site, plus a small "what is tool X's measured real recall" lookup.
- **The agent path, walked by an outsider.** `AGENTS.md` exists but nobody outside this project has
  followed it. The criterion is hard: **a person who is not us takes the repository, measures a tool
  we have not measured, and publishes the result.** If that turns out to be impossible, the
  instructions are wrong, and finding that out is itself worth the milestone.
- **Vendor replies incorporated.** Four threads are open. Every correction received is published
  **beside** our number, dated. Silence is recorded too.
- **The first quarterly report.** Not a ranking: **change over time.** What improved, what regressed,
  what entered the corpus. It is the one output that cannot be produced once and frozen.

**Check:** the JSON feed resolves; the report is published; the repository contains a measurement
performed by somebody who is not us; vendor corrections are published or their absence recorded.

---

## Summary

| Milestone | Share | Weeks | Criterion in one line |
|---|---|---|---|
| 1 | 25% | 2 | Every measurement has coverage evidence; results page live |
| 2 | 25% | +3 | 25+ cases grown by acquisition; concealed holdout round closed |
| 3 | 25% | +4 | Three AI auditors measured with spread over 10 runs each |
| 4 | 25% | +4 | Someone outside the project completed a measurement with this repo |

**Thirteen weeks total.**

## What is not promised

**Not that scanners will turn out good or bad.** We promise the measurement, not the result. If the
tools do better than they do today, that gets published with the same energy.

**Not revenue.** The data stays open and free, and we take no money from anyone we measure.

**Not that the project survives.** `docs/PROTOCOL.md` carries a falsifier and it binds regardless of
funding: if nobody uses this, it stops, and unspent funds go back.
