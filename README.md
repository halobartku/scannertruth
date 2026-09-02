# ScannerTruth

[![verify](https://github.com/halobartku/scannertruth/actions/workflows/verify.yml/badge.svg)](https://github.com/halobartku/scannertruth/actions/workflows/verify.yml)

**An independent, repeatable measurement of Solana security scanners.**

Seven third-party scanners and our own, run against real vulnerabilities taken from their maintainers' own fix commits.
**Not one detection stands under its own pre-registered mapping.** The tool that scores 11 out of
11 on the corpus the whole field measures against scores **0 out of 16** here.

    git clone https://github.com/halobartku/scannertruth && cd scannertruth
    python test_all.py                        # 157 checks, no dependencies
    python tools/run_all.py --verify-coverage # every number can show what it analysed

Start with [`docs/results/RESULTS-all.md`](docs/results/RESULTS-all.md) for the scanner table,
[`docs/results/RESULTS-models.md`](docs/results/RESULTS-models.md) for the AI auditors, or
[`docs/PROTOCOL.md`](docs/PROTOCOL.md) for how a detection is scored and why a rule that also
fires on the fixed code has detected nothing.

---

## How to read the two badges

**Two dials, and they answer different questions.** `selfcheck` says the machinery is sound: 157
checks on three operating systems and four Python versions. `coverage` says whether every number
published here can show what it analysed. **`coverage` went green on 2026-09-01**: all 19 live
measurements carry a per-run log and no case on either corpus is unresolved, so "the tool read this
case and found nothing" and "the tool never saw this case" can be told apart everywhere. One
measurement is retired and reported as such rather than counted.

It was red the day before, and a single badge covering both would have gone green and told you
nothing. Per-row invocation counts are in `docs/COVERAGE.md`, generated from `raw/` rather than
typed, because a count in prose goes stale the next time a row is re-run.

Why this benchmark exists, and why the corpus every Solana scanner is graded on cannot answer the
question, is in [`docs/WHY.md`](docs/WHY.md).

---

## Start here

**A person?** [`docs/GETTING-STARTED.md`](docs/GETTING-STARTED.md) - what you need (Python 3, nothing else),
how to verify our numbers offline in two minutes, and the one concept that makes them mean anything.
To measure a scanner yourself, [`docs/WALKTHROUGH.md`](docs/WALKTHROUGH.md) is a worked example on a tool we
already measured, so you can check your answer against ours. [`docs/SCANNERS.md`](docs/SCANNERS.md) lists
every tool we know of, what it needs, and what we found.

**An AI agent handed this repository?** [`AGENTS.md`](AGENTS.md) - the whole measurement procedure,
written to be executed without supervision, including the three steps whose absence produced public
retractions.

```bash
git clone https://github.com/halobartku/scannertruth && cd scannertruth
python test_all.py && python tools/verify.py && python tools/control_c2.py
```

No `pip install`. **Every dependency is in the Python standard library**, deliberately: a benchmark
whose results cannot be reproduced because a package version drifted is not a benchmark.

---

**Will this run on your system?** The verification path runs on Windows, macOS and Linux with
Python 3.9-3.12 and nothing else. The per-task table, the one POSIX assumption that is ours, and the
commands for each system are in
[`docs/GETTING-STARTED.md`](docs/GETTING-STARTED.md#will-this-run-on-your-system).

---

## The one concept

**Real recall: does the tool's mapped rule fire on a vulnerable program AND stay silent on the same
program after its authors fixed it?**

A rule that fires on both has detected nothing. It has recognised a shape of code that also exists
in working software. Every number here rests on that distinction.

---

## The result

Eight scanners (seven third-party and ours) and two calibration controls, one protocol. Full tables in
[`docs/results/RESULTS-all.md`](docs/results/RESULTS-all.md).

| Scanner | Teaching corpus (2022, public) | Real vulnerabilities |
|---|---|---|
| `control-noisy` | **0 / 11**, from 81,928 findings | **0**, despite 2,629,968 findings |
| **Radar** (Auditware) | **11 / 11**, at `main` 2026-09-02 still 11 / 11 with noise 46% down to 39% and 11% (upper bounds) | 0 / 8, re-run 2026-09-01: also **0 / 16**; `main` 2026-09-02 (`24c56f9`): **0 / 17** |
| `sol-audit` v2 (ours) | 4 / 11 | *retired 2026-09-01, superseded by v3*; was 0 / 8 |
| `sol-audit` v3 (ours, 2026-09-01) | 5 / 11 | **0 / 16** |
| `vaultlint` 0.1.1 | 2 / 11 | **0 / 17 registered, 1 / 17 corrected**; 15 of 17 `no-rule` |
| **X-Ray** (sec3) | 2 / 11 | **0 / 8 registered, 1 / 8 corrected** |
| `solsec` | 0 / 11 | **0 / 16**, zero unavailable |
| `sol-azy` (FuzzingLabs) | 9 / 11 nominal, **4 / 11** real | **0 / 15 analysed**, 1 not run |
| `semgrep`, own registry | no Solana rules in the registry | - |
| `semgrep` + [SOL-0XX pack](https://github.com/Copenhagen0x/solana-security-standard) | 3 / 11 nominal, **0 / 11** real | **0 / 16** |

**Eight scanners, two detections between them, and neither one counts under the mapping we
registered before the run.** Both were found by `unmapped_check.py`, which asks the question
per-class scoring cannot: is a real detection hiding under a rule our mapping did not claim
for this class. X-Ray's was the first, in August. VaultLint's is new on 2026-09-01: VL002,
`missing owner check`, fires on `anchor-account-reload-owner` at the line the fix guards and
is silent on the same function once the owner check is added, which is real recall by our own
definition. Our mapping points VL002 at `owner-checks` and the case is `owner-check-after-cpi`,
so **as registered the score is still zero**. Both numbers are published and neither mapping is
edited, because a mapping rewritten after seeing output is not a pre-registration. Both results
are provisional until their authors have been offered the mapping.

What each row's denominator is, why two rows moved on 2026-09-01 without their zeros moving, and
what the control proves are in
[`docs/results/RESULTS-all.md`](docs/results/RESULTS-all.md#beside-the-table), verbatim from this page.

---

## What this project actually is

The corpus every Solana scanner is measured against, `coral-xyz/sealevel-attacks`, was last touched
**2022-07-16**. Eleven hand-written teaching programs, four years old, public, and cited directly in
at least two vendors' own rule tables. One vendor merged pull requests closing gaps against it on
the day we measured them.

That is not a benchmark. It is **a teaching aid everybody has memorised**, and a score on it measures
homework rather than whether a tool generalises.

So the interesting question is what happens off it, and answering that required ground truth that
did not exist. Building it is the work:

- **Corpus 2**: real production vulnerabilities, each taken from the maintainers' own fix commit and
  its parent, so the answer key is somebody else's. 17 valid cases, 17 built, 8 measured by every
  row including the oldest, so the 2026-08-31 rows read out of eight; every row re-run since reads
  out of 16 or 17. Class and repository concentration is recomputed from the
  manifest in [`docs/CLASS-BALANCE.md`](docs/CLASS-BALANCE.md) rather than described in prose.
- **Real crates**: the same bugs as whole projects rather than extracted files, built from each
  project's own `Cargo.toml` and sibling modules. This tests the packaging objection rather than
  arguing about it. Four scanners were run over all seventeen valid cases in both packagings on
  2026-09-01 and **every verdict that could be compared came out the same**, so for those four the
  packaging does not explain the result. Radar was re-run too and agrees on the eight cases it can
  be compared on, but it cannot finish eight of the seventeen real crates and its scoreable
  denominator there is five. VaultLint's row is still one whole-corpus invocation over a nine-case
  build.
  The crates are built on demand rather than committed, so counts come from
  [`docs/results/RESULTS-realcrates.md`](docs/results/RESULTS-realcrates.md) per case.
- **Acquisition**: `corpus_ghsa.py` reads advisory databases, where a fix commit is a structured
  field rather than prose to be mined. It has scanned 1,200 advisories.
- **A sealed holdout**, committed by hash before the round it scores.

**`docs/PROTOCOL.md` is copyable in an afternoon and that is fine.** What is not copyable is fresh,
verified, growing ground truth and the record of how each case was checked. That is the asset, and
it is also what decides whether this deserves to continue: if the corpus stops growing, there is
nothing here.

[`docs/ROADMAP.md`](docs/ROADMAP.md) has what exists today and four funded milestones, the largest being a
variance harness for **AI auditors**, which are non-deterministic and so cannot be measured the way
a conventional scanner is. Measuring one once, which is what everyone does today, says almost
nothing.

---

## Why you can check us rather than trust us

- **Every number re-derives from raw data.** `raw/` holds every scanner's output and run logs. That
  is why this repository is 49 MB and not 2.
- **157 checks**, mutation-verified: deliberate defects were introduced and caught, including one
  that reported a published figure changing under a refactor. `python test_all.py`.
- **CI on machines we do not control**, running that suite on every push.
- **Every published number is derived, not typed.** This page has been wrong twice, and both times
  the arithmetic was fine and the *freshness* was not: it advertised a check count eight behind what
  the suite actually ran, and said "nine real break-ins" beside a table reading out of eight. So the check count is now
  computed from the suite and the denominator read from the corpus manifest and the directory. If
  they disagree, the suite fails and nothing can be pushed. **Never type a count a machine can
  compute** - the rule applies to us before it applies to any vendor.
- **[45 of our own errors](docs/ENGINEERING-LOG-2026-09-02.md), with dates**, including a headline we
  retracted in public *before* we had the replacement data, and an unverifiable figure withdrawn
  from this page. That document, not the results, is the strongest thing here: it shows the same
  reaction when a measurement damaged a competitor and when it flattered us.
- **[`docs/KNOWN-LIMITATIONS.md`](docs/KNOWN-LIMITATIONS.md)** opens with our own mistake.

---

## Repository layout

```
README.md              this file
AGENTS.md              entry point for an AI agent asked to measure something
test_all.py            157 checks, mutation-verified. Run this first
tests/                 the checks themselves, one module per concern; test_all.py imports them all

docs/
  INDEX.md             the map: every script and who calls it, generated files, raw/ names, results pages
  GETTING-STARTED.md   entry point for a person
  WHY.md               why the benchmark exists, and why the corpus everyone grades on cannot answer it
  WALKTHROUGH.md       worked example: measure a scanner yourself, step by step
  SCANNERS.md          registry: every tool we know of, what it needs, what we measured
  PROTOCOL.md          the rules, and what makes a result provisional
  ROADMAP.md           what exists today, and four funded milestones
  ADAPTERS.md          adding a scanner: the declaration, and what comes for free
  KNOWN-LIMITATIONS.md what this measurement cannot tell you
  COVERAGE.md          generated: which measurement can show what it analysed, derived from raw/
  CLASS-BALANCE.md     generated: class and repository concentration of corpus 2, from the manifest
  ENGINEERING-LOG-*.md our errors, with dates: 21 on 2026-08-31, 20 more on 2026-09-01, 3 on 2026-09-02
  COMMITMENTS.md       three standing promises
  MANIFESTO.md         nine testable sentences, each with its named breach
  CANDIDATES-TRIAGE.md corpus candidates accepted and rejected, with reasons
  results/             the measurements themselves
    RESULTS-all.md         current: every scanner, both corpora, the table the front page reads
    RESULTS-corpus2.md     current: corpus 2 verdict by verdict
    RESULTS-realcrates.md  current: the packaging objection tested on whole crates
    RESULTS-models.md      current: model-backed auditors, three runs per variant
    RESULTS-wormhole.md    frozen: the first out-of-sample case
    RESULTS-scanners.md    scanner rows incl. the Radar re-measurements of 2026-09-02 (noise and method)
    RESULTS-v2.md          frozen: run 2, sol-audit v2
    RESULTS.md             frozen: run 1, sol-audit v1; verify.py re-derives it

tools/
  score.py score2.py   the scorers; score2 is the strict one, for real vulnerabilities
  run_all.py           the clock: re-measures on a schedule, diffs against the previous run
  clock_corpus1.py     the clock's corpus-1 scoring and source tables; run_all.py re-exports it
  clock_corpus2.py     the clock's corpus-2 scoring; run_all.py re-exports it
  control_c1.py        the calibration controls on the teaching corpus, rebuilt from a line inventory
  control_c2.py        the calibration controls on corpus 2, which must score zero
  verify.py            re-derives the run-1 result from raw data; that page only
  holdout.py           seal a holdout by hash before the round it scores
  corpus_ghsa.py       propose corpus candidates from advisory databases
  corpus_radar.py      propose corpus candidates from public sources; never adds one
  corpus_hashes.py     pin every corpus-2 file to a content hash and its upstream blob
  build_corpus2.py     build corpus 2 from each fix commit and its parent; --crates builds the real crates
  class_balance.py     writes docs/CLASS-BALANCE.md
  coverage_matrix.py   writes docs/COVERAGE.md
  shiftaware.py        compare findings across a fix without being fooled by line shift
  unmapped_check.py    find a detection hiding under a rule the mapping missed
  stale_findings.py    count findings that name a corpus file the rebuild removed
  preregistration_check.py  a mapping's commit must touch nothing but mappings/
  controls.py          one normalised Finding shape, plus the two controls
  scanner_spec.py      the adapter framework: run, classify, log, check determinism
  spec/                the framework's code; scanner_spec.py is the name everything imports
  emit_sol_audit.py    run our own scanner and emit findings in the envelope the clock reads
  legacy/              normalise_runs.py, the hand-run-to-findings converter behind two 2026-09-01 artefacts; superseded by scanner_spec.py
  rb.py                the first-day scorer for sol-audit against the teaching corpus
  rc_run.py            run a scanner over the real crates, one invocation per case per variant
  rc_score.py          score a real-crate run with score2's semantics
  rc_compare.py        extracted file versus real crate, verdict by verdict
  model_audit.py       measure a model-backed auditor the way a scanner is measured

adapters/              one declaration per scanner: provenance, invocation, parser, rows
corpus2/               real vulnerabilities, each pinned to its maintainers' own fix commit
mappings/              one file per tool: which rule claims which class, and how it was derived
raw/                   every scanner's raw output and run logs; raw/README.md is the naming key
runs/                  dated history from the clock
skills/                the method as three executable procedures
```

**`raw/` is the point of the layout.** Every published number recomputes from what is in there,
which is why this repository is 49 MB rather than 2.

[`docs/INDEX.md`](docs/INDEX.md) is the map: every script in `tools/` with the command that runs it
and who calls it, which files are generated and by what, which results page is current, and which
numbers on this page a test derives. [`raw/README.md`](raw/README.md) is the naming key for the raw
artefacts, and the rule that existing names are frozen because tests pin them.

## Honest limits

The short list this page used to carry is now the top of
[`docs/KNOWN-LIMITATIONS.md`](docs/KNOWN-LIMITATIONS.md), above the numbered limitations it
summarises. Read it before quoting any number here.

---

## Independence

Three standing promises, made while this project has no users and nobody offering it money: **the
data is open and free forever, our own scanner stays free and open, and we take no money from anyone
we measure.** Full text and reasoning in [`docs/COMMITMENTS.md`](docs/COMMITMENTS.md).

The nine sentences the project holds itself to, each with what a breach of it looks like, are in
[`docs/MANIFESTO.md`](docs/MANIFESTO.md), adopted 2026-09-02.

`docs/PROTOCOL.md` also carries a falsifier: if the pending grant is refused **and** no vendor thread
receives a technical reply within fourteen days, this has zero confirmed consumers and work stops.
It is written down so it binds when it is inconvenient.

---

## Why this exists

The argument is in [`docs/WHY.md`](docs/WHY.md).

Built as part of [Forge](https://github.com/halobartku), an experiment in what an autonomous agent
can and cannot do in the open. The engineering here is substantially done by that agent, operated
and signed off by a human. Every number is reproducible from the code and the raw data, so none of
that has to be taken on trust.

MIT licensed.
