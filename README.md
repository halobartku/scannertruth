# ScannerTruth

[![verify](https://github.com/halobartku/scannertruth/actions/workflows/verify.yml/badge.svg)](https://github.com/halobartku/scannertruth/actions/workflows/verify.yml)

An independent, repeatable measurement of Solana security scanners.

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
wrote. As of 2026-09-01 there are **17 valid cases**, **16 built** and **8 measured**: eight cases
were added on 2026-09-01 and no scanner has been run over them yet, so they are not in the
denominator of any figure on this page, and the one valid case that is not built is reported as
`not-built` rather than quietly dropped. The best scanner on the market scores **11/11 on the
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
| `control-noisy`, 931 findings | **0 / 11** | **0**, despite 1,413,620 findings |
| **Radar** (Auditware) | **11 / 11** | 0 / 8 |
| `sol-audit` (ours) | 4 / 11 | 0 / 8 |
| `vaultlint` | 2 / 11 | 0 / 8, of which 7 are `no-rule` |
| **X-Ray** (sec3) | 2 / 11 | **0 / 8 registered, 1 / 8 corrected** |
| `solsec` | 0 / 11 | 0 / 6, 3 unavailable |
| `semgrep` | no Solana rules at all | - |

**Six scanners, eight real vulnerabilities, one detection between them** - and seeing that one
required correcting a mapping error of our own.

**Every "real vulnerabilities" figure above is out of the eight cases measured on 2026-09-01.**
Eight further cases were added to the corpus later that day and **have not been measured by
anything**. They are not counted as zeros, they are not counted at all: `run_all.py` reports them
as `not-run` or `unknown` and drops the reporting scanner's status to `partial` until it is run
again. The table will read out of sixteen when, and only when, there is a run behind it.

**The control is what makes the table readable.** `control-noisy` flags every non-empty line. It
would rank first on any metric that counts findings. Here it scores zero, so no score above was
bought with volume.

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
  its parent, so the answer key is somebody else's. 17 valid cases, 16 built, 8 measured, which is
  why the table above reads out of eight. Class and repository concentration is recomputed from the
  manifest in [`docs/CLASS-BALANCE.md`](docs/CLASS-BALANCE.md) rather than described in prose.
- **Real crates**: the same bugs as whole projects rather than extracted files, built from each
  project's own `Cargo.toml` and sibling modules. This tests the packaging objection rather than
  arguing about it, and on the six pairs that could be scored it did not explain the result.
  Two scanners, not six; three of the largest cases could not be measured at all. The crates are
  built on demand rather than committed, so counts come from
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

Of six tools measured on 2026-09-01: **one is actively developed**, two have been silent for half a
year, and one is effectively abandoned despite 77,684 lifetime downloads against 56 recent ones.
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
- **109 checks**, mutation-verified: deliberate defects were introduced and caught, including one
  that reported a published figure changing under a refactor. `python test_all.py`.
- **CI on machines we do not control**, running that suite on every push.
- **Every published number is derived, not typed.** This page has been wrong twice, and both times
  the arithmetic was fine and the *freshness* was not: it advertised a check count eight behind what
  the suite actually ran, and said "nine real break-ins" beside a table reading out of eight. So the check count is now
  computed from the suite and the denominator read from the corpus manifest and the directory. If
  they disagree, the suite fails and nothing can be pushed. **Never type a count a machine can
  compute** - the rule applies to us before it applies to any vendor.
- **[30 of our own errors](docs/ENGINEERING-LOG-2026-09-01.md), with dates**, including a headline we
  retracted in public *before* we had the replacement data, and an unverifiable figure withdrawn
  from this page. That document, not the results, is the strongest thing here: it shows the same
  reaction when a measurement damaged a competitor and when it flattered us.
- **[`docs/KNOWN-LIMITATIONS.md`](docs/KNOWN-LIMITATIONS.md)** opens with our own mistake.

---

## Repository layout

```
README.md              this file
AGENTS.md              entry point for an AI agent asked to measure something
test_all.py            109 checks, mutation-verified. Run this first

docs/
  GETTING-STARTED.md   entry point for a person
  WALKTHROUGH.md       worked example: measure a scanner yourself, step by step
  SCANNERS.md          registry: every tool we know of, what it needs, what we measured
  PROTOCOL.md          the rules, and what makes a result provisional
  ROADMAP.md           what exists today, and four funded milestones
  KNOWN-LIMITATIONS.md what this measurement cannot tell you
  ENGINEERING-LOG-*.md our errors, with dates: 21 on 2026-08-31, 9 more on 2026-09-01
  COMMITMENTS.md       three standing promises
  CANDIDATES-TRIAGE.md corpus candidates accepted and rejected, with reasons
  results/             the measurements themselves

tools/
  score.py score2.py   the scorers; score2 is the strict one, for real vulnerabilities
  run_all.py           the clock: re-measures on a schedule, diffs against the previous run
  control_c2.py        the calibration controls, which must score zero
  verify.py            re-derives a published result from raw data
  holdout.py           seal a holdout by hash before the round it scores
  corpus_ghsa.py       propose corpus candidates from advisory databases
  shiftaware.py        compare findings across a fix without being fooled by line shift
  unmapped_check.py    find a detection hiding under a rule the mapping missed
  preregistration_check.py  a mapping's commit must touch nothing but mappings/
  adapters.py          one normalised Finding shape, plus the two controls

corpus2/               real vulnerabilities, each pinned to its maintainers' own fix commit
mappings/              one file per tool: which rule claims which class, and how it was derived
raw/                   every scanner's raw output and run logs
runs/                  dated history from the clock
skills/                the method as three executable procedures
```

**`raw/` is the point of the layout.** Every published number recomputes from what is in there,
which is why this repository is 49 MB rather than 2.

## Honest limits

- **Seventeen real cases is a small corpus**, and only eight of them have been measured, so every
  score above is out of eight and not out of sixteen. This is our largest stated weakness; growing
  it is milestone 2, and the eight cases added on 2026-09-01 are growth that has not yet been
  measured rather than a better number.
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
- **`sol-audit` still has no per-run coverage log** while Radar and VaultLint do. We closed other
  people's tools more rigorously than our own; that is milestone 1.
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
