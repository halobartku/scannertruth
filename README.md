# ScannerTruth

[![verify](https://github.com/halobartku/scannertruth/actions/workflows/verify.yml/badge.svg)](https://github.com/halobartku/scannertruth/actions/workflows/verify.yml)

**An independent, repeatable measurement of Solana security scanners.**

Seven scanners, run against real vulnerabilities taken from their maintainers' own fix commits.
**Not one detection stands under its own pre-registered mapping.** The tool that scores 11 out of
11 on the corpus the whole field measures against scores **0 out of 16** here.

    git clone https://github.com/halobartku/scannertruth && cd scannertruth
    python test_all.py                        # 151 checks, no dependencies
    python tools/run_all.py --verify-coverage # every number can show what it analysed

Start with [`docs/results/RESULTS-all.md`](docs/results/RESULTS-all.md) for the scanner table,
[`docs/results/RESULTS-models.md`](docs/results/RESULTS-models.md) for the AI auditors, or
[`docs/PROTOCOL.md`](docs/PROTOCOL.md) for how a detection is scored and why a rule that also
fires on the fixed code has detected nothing.

---

## How to read the two badges

**Two dials, and they answer different questions.** `selfcheck` says the machinery is sound: 151
checks on three operating systems and four Python versions. `coverage` says whether every number
published here can show what it analysed. **`coverage` went green on 2026-09-01**: all 19 live
measurements carry a per-run log and no case on either corpus is unresolved, so "the tool read this
case and found nothing" and "the tool never saw this case" can be told apart everywhere. One
measurement is retired and reported as such rather than counted.

It was red the day before, and a single badge covering both would have gone green and told you
nothing. Per-row invocation counts are in `docs/COVERAGE.md`, generated from `raw/` rather than
typed, because a count in prose goes stale the next time a row is re-run.

## Every Solana scanner is graded on the same test paper, and it has not changed since 2022

`coral-xyz/sealevel-attacks`, the corpus the entire category is measured against, was last modified
**16 July 2022**, at commit `24555d04`. Eleven hand-written teaching programs. Four years. Public
the whole time.

At least two of the tools we measured cite that corpus **in their own rule tables**. One vendor
merged pull requests closing the last gaps in it **on the day we measured them**. None of that is
dishonest; it is what any engineer would do. But it means a score on that corpus measures **how
thoroughly a tool has done a fixed piece of homework**, not whether it works on anything else.

An exam with the same questions for four years stops telling you who can do the subject.

**So we built the other exam.** Real break-ins, each taken from the fix commit its own maintainers
wrote. As of 2026-09-01 there are **17 valid cases**, **17 built** and **8 measured**. Eight is the
floor: it is the set every row in the table below covers, and a row that has since been re-run
over more says so and states its own larger denominator. No case is ever quietly dropped, and a
case a given scanner has not been run over is reported as `not-run`, never as a zero. The best scanner on the market scores **11/11 on the
four-year-old paper and zero on the real one.**

---

Vendors publish finding counts. **A finding count is not recall.** A scanner that flags fixed code
as often as vulnerable code produces an impressive number and catches nothing. We know because we
measured it on our own product first, and published the result that killed the claim.

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

## Will this run on your system?

**The verification path runs on Windows, macOS and Linux, and CI proves it on all three.** It is
pure Python standard library with no install step, so there is no package version that can drift
between your machine and ours.

| What you want to do | Windows | macOS | Linux | What you need |
|---|---|---|---|---|
| **Check our numbers** - `test_all.py`, `verify.py`, `control_c2.py` | yes | yes | yes | Python 3.9-3.12, nothing else |
| **Score findings you already have** - `score.py`, `score2.py` | yes | yes | yes | the same |
| **Build the real crates** - `build_corpus2.py --crates` | no | yes | yes | `git`, and a POSIX temp path |
| **Run the scanners themselves** | via WSL2 | mostly | yes | Docker, Rust, or a vendor key - see [`docs/SCANNERS.md`](docs/SCANNERS.md) |

**Why the split.** Checking a result and producing one are different jobs with different costs.
Verification reads JSON we already published, so it can afford to depend on nothing. Measuring has
to clone repositories and drive somebody else's tool, and those tools are Linux-first: Radar ships
as a Docker image, and one AI auditor needs a paid model key. That is their constraint, not ours,
and it is recorded in the registry rather than hidden behind an install script of our own.

**The remaining POSIX assumption is ours and it is written down**: `build_corpus2.py`, `rb.py` and
`shiftaware.py` default to `/tmp` paths, which do not exist on Windows. Pass `--cache` and `--out`
explicitly, or use WSL2. Nothing on the verification path has that problem.

**How, on each system:**

```bash
# macOS / Linux - python3, because bare `python` may not exist
git clone https://github.com/halobartku/scannertruth && cd scannertruth
python3 test_all.py && python3 tools/verify.py && python3 tools/control_c2.py
```

```powershell
# Windows PowerShell - && is not a chain operator in Windows PowerShell 5.1
git clone https://github.com/halobartku/scannertruth; cd scannertruth
python test_all.py; python tools\verify.py; python tools\control_c2.py
```

Two minutes, no network after the clone. If any check fails on your machine and not on ours, that
is a bug we want: **a benchmark that only reproduces on the author's laptop is not reproducible.**

**Windows is in CI deliberately.** Paths are the one thing a scorer can get quietly wrong, and a
finding located by a backslash path has to map to the same case as a forward-slash one. That is
tested rather than assumed.

---

## The one concept

**Real recall: does the tool's mapped rule fire on a vulnerable program AND stay silent on the same
program after its authors fixed it?**

A rule that fires on both has detected nothing. It has recognised a shape of code that also exists
in working software. Every number here rests on that distinction.

---

## The result

Six scanners and two calibration controls, one protocol, measured the same day. Full tables in
[`docs/results/RESULTS-all.md`](docs/results/RESULTS-all.md).

| Scanner | Teaching corpus (2022, public) | Real vulnerabilities |
|---|---|---|
| `control-noisy` | **0 / 11**, from 81,928 findings | **0**, despite 2,629,968 findings |
| **Radar** (Auditware) | **11 / 11** | 0 / 8, re-run 2026-09-01: also **0 / 16** |
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

VaultLint has now been run over all seventeen built cases and is the only row here with complete
coverage. Radar, solsec, semgrep-with-the-pack and sol-audit v3 have been run over sixteen of
the seventeen and detect nothing on any of them.

`sol-azy` was published in the could-not-run table until 2026-09-01 with the reason "ships no
default rule set, so it detects nothing out of the box". That reason was false: it has an internal
rule set, it was measured on 2026-09-01 with a mapping committed before the run, and it scores
4 / 11 real on the teaching corpus, which is not nothing. Recorded as error 36. This is the
project's own most-repeated rule inverted: we published "could not run" about a tool we had run.

The `solsec` and `semgrep` rows moved on 2026-09-01 and neither zero moved with them. `solsec`
was published as `0 / 6, 3 unavailable`; run per case with a log it is **34 invocations, 34
successes, zero unavailable**, so the denominator was inferred from silence and the three
unavailable cases did not exist (error 35). `semgrep` was published as having *no Solana rules at
all*; that is true of its own registry and false of semgrep, which loads a maintained MIT pack of
30 Solana rules with one `--config`. Measured, that pack detects nothing either.

**Denominators differ by row, and which one a row uses is stated in the row.** Eight cases were
measured on 2026-08-31, eight more were added on 2026-09-01, and the seventeenth was built later
the same day. `vaultlint` has since been re-run per case over all seventeen with a log per
invocation, so it reads out of seventeen. Radar, solsec, semgrep-with-the-pack and sol-audit v3
read out of sixteen, and `run_all.py` reports every one of them `partial` because the
seventeenth case is recorded as `not-run` rather than as a zero. X-Ray still reads out of eight.
A case nobody has run is not a case anybody failed, and the `partial` is removed by running the
case, never by editing the row.

**The raw denominator is not the honest one either.** A class no scanner has a rule for is a
coverage gap, not a failure, and `run_all.py` now publishes a `scoreable_denominator` beside every
tally: Radar 9 of 16, semgrep-with-the-pack 8 narrow and 16 wide, solsec **2**. Both numbers are
published because only one of them is fair and only the other is comparable.

**The control is what makes the table readable.** `control-noisy` flags every non-empty line under
every rule id any mapping in this repository claims: 81,928 findings on the teaching corpus and
2,629,968 on the real one. It would rank first on any metric that counts findings. It reaches
**11 / 11 nominal recall** and **0 / 11 real**, so nominal recall demonstrably can be bought with
volume, which is why this project does not publish it as a result, and real recall demonstrably
cannot. Until 2026-09-01 the teaching-corpus control emitted under one rule id that no mapping
knew, so the scorer discarded all 931 of its findings and it proved nothing at all while being
cited here as the reason nothing above it was bought with volume. That is error 33.

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
  its parent, so the answer key is somebody else's. 17 valid cases, 17 built, 8 measured, which is
  why the table above reads out of eight. Class and repository concentration is recomputed from the
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

## Who this is for, and why it matters

### The harm is not missing tools. It is false assurance.

A team buys a scanner, runs it, gets a clean report, ticks "we have security tooling" in the
documentation, tells investors "it's been scanned", and **sleeps better while being exactly as
exposed as before.**

That is not hypothetical. Our own scanner produced 194 findings on one repository and detected
nothing. The best tool on the market scores a perfect 11/11 on the corpus everyone uses and **zero
on eight real break-ins**. A clean report from a tool of unmeasured effectiveness is not
information; it is noise that people act on, usually by deciding *not* to spend money on a human
audit.

### Who this helps

**Teams building on Solana.** Today you choose a scanner by its marketing. With a measured real
recall you know what a green report is worth, and whether it justifies skipping a human review.
That is a budget decision, and right now it is made blind.

**Teams already paying for audits.** You can ask your auditor: *what is the measured effectiveness
of the tooling you use, and how do you know?* Until now that question had no possible answer.

**Grant programmes and foundations.** They fund security tooling and have **no instrument to
evaluate what the funding produced.** Not carelessness, an absent measuring device. A benchmark lets
a programme compare applications and ask a grantee for measured real recall instead of a finding
count.

**Honest tool vendors, and this is not a courtesy.** Our measurement *confirmed* VaultLint's
precision claim: everything it detected, it detected correctly. That is an asset they earned. Today
a good tool and a loud tool look identical, because the only visible number is a finding count and
that number rewards noise. Which is also why every vendor here gets a
[right of reply](docs/PROTOCOL.md) before a result is treated as final.

**The ecosystem, before the AI-audit wave lands.** It has already started: one tool is in our
could-not-run table because it needs a paid model key. There is currently **no way to compare these
tools at all**, so the choice will be made on marketing. Worse, an AI auditor is
*non-deterministic*: the same code can give a different answer tomorrow, so the single measurement
everyone performs today says almost nothing. Repeated measurement is the only honest form, and it is
what the clock in this repository does.

### The market context, measured rather than assumed

Of the six tools measured on 2026-08-31, surveyed for activity on 2026-09-01: **one is actively
developed**, two have been silent for half a year, and one is effectively abandoned despite 77,684
lifetime downloads against 56 recent ones.
[`docs/SCANNERS.md`](docs/SCANNERS.md) has the table.

**That is not a mature market. It is missing infrastructure.** Which is the whole argument for
building this now rather than in two years.

---

## Why the ground truth is not a matter of opinion

The teaching corpus is maintained by the Anchor team. Every class ships the same program twice: with
the bug (`insecure`) and with it fixed (`secure`, `recommended`). A finding of class *C* on the
fixed variant of class *C* is a false positive **by construction**. Nothing to adjudicate.

Corpus 2 works the same way one step harder: each pair is a real program immediately before and
after the fix **its own maintainers wrote** in response to a public disclosure. We do not decide
what the bug was.

**A benchmark whose author also writes the answer key is not a benchmark.**

---

## Why you can check us rather than trust us

- **Every number re-derives from raw data.** `raw/` holds every scanner's output and run logs. That
  is why this repository is 49 MB and not 2.
- **151 checks**, mutation-verified: deliberate defects were introduced and caught, including one
  that reported a published figure changing under a refactor. `python test_all.py`.
- **CI on machines we do not control**, running that suite on every push.
- **Every published number is derived, not typed.** This page has been wrong twice, and both times
  the arithmetic was fine and the *freshness* was not: it advertised a check count eight behind what
  the suite actually ran, and said "nine real break-ins" beside a table reading out of eight. So the check count is now
  computed from the suite and the denominator read from the corpus manifest and the directory. If
  they disagree, the suite fails and nothing can be pushed. **Never type a count a machine can
  compute** - the rule applies to us before it applies to any vendor.
- **[41 of our own errors](docs/ENGINEERING-LOG-2026-09-01.md), with dates**, including a headline we
  retracted in public *before* we had the replacement data, and an unverifiable figure withdrawn
  from this page. That document, not the results, is the strongest thing here: it shows the same
  reaction when a measurement damaged a competitor and when it flattered us.
- **[`docs/KNOWN-LIMITATIONS.md`](docs/KNOWN-LIMITATIONS.md)** opens with our own mistake.

---

## Repository layout

```
README.md              this file
AGENTS.md              entry point for an AI agent asked to measure something
test_all.py            151 checks, mutation-verified. Run this first
tests/                 the checks themselves, one module per concern; test_all.py imports them all

docs/
  INDEX.md             the map: every script and who calls it, generated files, raw/ names, results pages
  GETTING-STARTED.md   entry point for a person
  WALKTHROUGH.md       worked example: measure a scanner yourself, step by step
  SCANNERS.md          registry: every tool we know of, what it needs, what we measured
  PROTOCOL.md          the rules, and what makes a result provisional
  ROADMAP.md           what exists today, and four funded milestones
  ADAPTERS.md          adding a scanner: the declaration, and what comes for free
  KNOWN-LIMITATIONS.md what this measurement cannot tell you
  COVERAGE.md          generated: which measurement can show what it analysed, derived from raw/
  CLASS-BALANCE.md     generated: class and repository concentration of corpus 2, from the manifest
  ENGINEERING-LOG-*.md our errors, with dates: 21 on 2026-08-31, 20 more on 2026-09-01
  COMMITMENTS.md       three standing promises
  CANDIDATES-TRIAGE.md corpus candidates accepted and rejected, with reasons
  results/             the measurements themselves
    RESULTS-all.md         current: every scanner, both corpora, the table the front page reads
    RESULTS-corpus2.md     current: corpus 2 verdict by verdict
    RESULTS-realcrates.md  current: the packaging objection tested on whole crates
    RESULTS-models.md      current: model-backed auditors, three runs per variant
    RESULTS-wormhole.md    frozen: the first out-of-sample case
    RESULTS-scanners.md    superseded by RESULTS-all.md: the first multi-scanner run
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
  adapters.py          one normalised Finding shape, plus the two controls
  scanner_spec.py      the adapter framework: run, classify, log, check determinism
  spec/                the framework's code; scanner_spec.py is the name everything imports
  emit_sol_audit.py    run our own scanner and emit findings in the envelope the clock reads
  normalise_runs.py    turn a directory of per-run artefacts into a findings file and a run log
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

- **Seventeen real cases is a small corpus**, and only one row above, `vaultlint`, is out of all
  seventeen. The rest are out of sixteen or out of eight, and each says which. This is our
  largest stated weakness; growing it is milestone 2, and the nine cases built on 2026-09-01
  are growth rather than a better number.
- **Corpus 2 is drawn from public postmortems**, which are famous precisely because nobody caught
  them in time. It is therefore systematically harder than the population of real bugs and
  **understates every scanner measured on it**. It answers "do these catch the ones that cost
  money". It cannot support "these tools do not work", and nothing here claims that.
- **Every teaching-corpus score is in-sample**, including the 11/11 and our own 4/11, because that
  corpus is public and at least two measured tools cite it in their own rules. A holdout is the only
  real answer; round 1 is sealed but gives timestamp integrity, not concealment.
- **Every third-party number is provisional.** Four right-of-reply threads are open with the vendors
  we measured and none has answered. Our X-Ray mapping was wrong in a way only its authors could
  have settled quickly, so this is not a formality.
- **The mappings published on 2026-08-31 are not pre-registered in any way a stranger can check.**
  We claimed they were committed before their runs. The history says each one first appears in the
  same commit as the result it scores. They were written from the tools' own rule names and
  documentation, and each carries its `derivation`, but the ordering rests on our word.
  `docs/PROTOCOL.md` 3a carries the retraction, and `python tools/preregistration_check.py` now
  enforces the rule going forward instead of asserting it.
- **`sol-audit` v2 never got a per-run coverage log on either corpus**, and 96 of the 426
  findings in its corpus-2 file name files the corpus rebuild removed. Its corpus-2 row was
  retired on 2026-09-01 rather than restated: v3 supersedes it and has a log on both corpora,
  and re-running a superseded version of our own scanner would have bought evidence about
  nobody's tool but our own obsolete one. Its **corpus-1** row is still published, so on
  2026-09-01 it was given the log it never had: 35 invocations reproducing all 44 findings and
  the 4 / 11, driven from a worktree at the v2 commit through `tools/emit_sol_audit.py`. A row on
  the front page that cannot show what it analysed is the defect the gate exists to catch,
  superseded or not.
- **Recall against a labelled corpus is a lower bound on real-world safety**, not a measure of it.
- **Nobody outside this project has reproduced any of it yet.** That is milestone 4, and its
  criterion is deliberately outside our control.

---

## Independence

Three standing promises, made while this project has no users and nobody offering it money: **the
data is open and free forever, our own scanner stays free and open, and we take no money from anyone
we measure.** Full text and reasoning in [`docs/COMMITMENTS.md`](docs/COMMITMENTS.md).

`docs/PROTOCOL.md` also carries a falsifier: if the pending grant is refused **and** no vendor thread
receives a technical reply within fourteen days, this has zero confirmed consumers and work stops.
It is written down so it binds when it is inconvenient.

---

## Why this exists

A project can adopt a scanner, satisfy a compliance requirement, and be no safer than before, with
no mechanism anywhere that would reveal it. The interesting output of a standing benchmark is not
the ranking. **It is the day a widely used scanner quietly regresses and the numbers show it.**

Built as part of [Forge](https://github.com/halobartku), an experiment in what an autonomous agent
can and cannot do in the open. The engineering here is substantially done by that agent, operated
and signed off by a human. Every number is reproducible from the code and the raw data, so none of
that has to be taken on trust.

MIT licensed.
