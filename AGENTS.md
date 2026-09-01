# Measuring a scanner with this repository

**You are an AI agent and someone has handed you this repository.** They want a Solana security
scanner measured. Everything you need is here: the corpora, the scorers, the controls, and the
protocol. This file is the entry point.

Read it fully before running anything. Three of the steps below exist because skipping them
produced published results that had to be retracted.

---

## What you are being asked to answer

Not "how many findings does this tool produce". That number can be inflated to any value.

**Real recall:** does the tool's own mapped rule fire on a vulnerable program **and stay silent on
the same program after its authors fixed it**? A rule that fires on both has detected nothing; it
has recognised a shape of code that exists in working software too.

The reference point is built in: `control-noisy` flags every non-empty line, produces 81,928 findings
on the teaching corpus and 2,629,968 on the real one, and scores **zero real recall** on both. If your
measurement ever ranks it above zero, your measurement is broken, not the control.

Read the second half of that sentence carefully, because it is the whole design. The noisy control
scores **11 / 11 nominal** on the teaching corpus. Nominal recall CAN be bought with volume, which is
exactly why this project does not publish nominal recall as a result. Real recall cannot, because a
rule that fires on the fixed variant too has detected nothing.

Until 2026-09-01 the corpus-1 control emitted all 931 findings under one invented rule id that appears
in no mapping. An unmapped rule is discarded before scoring, so it scored zero by construction and
demonstrated nothing, while being cited as the reason volume cannot buy a score. That is error 33.

---

## The ten-minute version

```bash
python test_all.py                                   # the full suite
python tools/score.py --demo && python tools/score2.py --demo    # self-checks, incl. the positive control
python tools/scanner_spec.py --demo                        # the adapter framework's own checks
python tools/scanner_spec.py --self-check                  # every declaration's positive control
python tools/verify.py                                     # run-1 headline reproduces from raw data
python tools/control_c2.py                                 # controls must score zero
```

If all of those pass, the harness is sound and you can trust what it tells you next. If any fails,
**stop and report that** rather than measuring anything.

There is a seventh command, and it is the one that does **not** pass today:

```bash
python tools/run_all.py --verify-coverage                  # exits 1 on purpose. Read the next section.
```

---

## `--verify-coverage`, which is red, and what red means

`python tools/run_all.py --verify-coverage` asks one question of every measurement on the clock:
**can this row show what it analysed?** A findings file cannot, because a case that was analysed and
came back empty leaves exactly the same silence as a case nobody opened. A run log can.

It runs in CI as **its own job**, `coverage`, separate from `selfcheck`. Do not be surprised by it:
the badge you are looking at may be green on the machinery and red on the numbers. That combination
is deliberate and it is not a broken build. `selfcheck` says the machinery is sound; `coverage` says
whether what is published today can account for itself.

**It is red right now, and it exits 1.** Five of twenty measurements report `coverage_evidence:
none`, thirteen problems in total. The five with no run log are corpus-1 `radar`, corpus-1
`semgrep`, corpus-1 `vaultlint`, and `sol-audit` v2 on both corpora. Radar's 11 / 11 on the teaching
corpus, the most quoted figure in this project, is one of them. The other eight problems are cases
inside a denominator that no run log accounts for.

Read what that does and does not say:

- It does **not** mean a check broke. It means five historical measurements were made the way the
  documents used to teach, by hand, and the log was the step a person had to remember.
- **A case recorded `unavailable` with a reason is not a failure here.** "Could not run" is a
  published outcome under this project's rules. `not-run` and `unknown` are the gaps.
- It closes with **scanner runs, not with code**, and it is the acceptance check for milestone 1 in
  [`docs/ROADMAP.md`](docs/ROADMAP.md). Do not make it pass by relaxing it. If you cannot make a row
  pass, publish why.

Any measurement you make from here must not add a sixth. Run it through the declaration described
below and it cannot: the log is written before the run returns.

---

## Measuring a scanner, end to end

Since 2026-09-01 the per-case loop is a **declaration**, not a script you write.
`adapters/<tool>.json` says what is different about the tool; `tools/scanner_spec.py` holds what is
the same about all of them. [`docs/ADAPTERS.md`](docs/ADAPTERS.md) is the procedure in full, with an
eighth tool added end to end. Read it before you write a runner, because you should not write one.

The protocol below has not changed. What changed is **who performs each step**, and that is the only
thing this section is careful about: a step the framework performs is one you cannot forget, and a
step it does not perform is one that is still entirely yours.

### 1. Provenance, before you download anything
**Yours.** Find the tool's **own repository** and use the install path it documents. Check that any
registry package maps to that repo: author, repo link, publish date. `cargo install radar` nearly
installed an unrelated 2021 crate by a different author. If an install script is piped to a shell,
read it in full first and say so.

### 2. Read the tool's argument shape and its coverage line
**Yours, and nothing can do it for you.** Ten seconds of `--help` on the binary *and* on the
subcommand, then one run against any directory, to answer the two questions the declaration has to
state: what does the tool print when it has read files, and what shape is its output? We once passed
`--format json` to a binary when it belonged to the `scan` subcommand and all 18 runs failed
identically.

### 3. Declare the adapter, and check it before running anything
Write `adapters/<tool>.json`: the image, the argv, how the tool announces that it read the code, and
the shape of its output. Container isolation is a field, not a habit: `"engine": "docker"`,
`"network": "none"`, and the corpus is mounted read-only by the framework. Nothing untrusted runs on
the host.

`coverage.evidence` is the field that decides every zero this tool will ever produce, and **the
pattern is read off the tool by you**. `validate` refuses a declaration that omits it, and a tool
that prints no such line must say so with `{"absent": true, "reason": "..."}`, after which every run
is recorded `unknown` and can never become a zero.

`layout` is the other one you read off the tool. Radar returns `400 Bad Request` on a bare `.rs`
file, and `No Cargo.toml files found in any subdirectories` when the manifest sits at the root of the
path it is given: it wants the manifest one level down, which is `"layout": "wrapped-pkg"`. Getting
this wrong produces a silent zero that looks exactly like a clean miss. Record the failed attempt;
do not silently replace it with the successful run.

```bash
python tools/scanner_spec.py --self-check
```

This plants your declared rule id at the fix site of a synthetic case, parses it with your parser,
writes it in your envelope, reads it back with the reader the clock uses, and requires the scorer to
say `detected`. **If it fails, stop.** A parser that silently returns nothing is indistinguishable
from a tool that found nothing.

Two traps worth knowing before the suite tells you: a declaration must carry at least one entry in
`measurements`, and a measurement is on the clock unless you say `"on_clock": false`. Putting a new
row on the clock changes the published tables, and the suite will say which row moved.

### 4. Write the mapping BEFORE you run it
**Yours.** Create `mappings/<scanner>.json` mapping the tool's rule ids to corpus classes, derived
from **the tool's own rule names and documentation**, never from which rules happened to fire. Commit
it in its own commit before the run; that timestamp is the pre-registration. **That commit must touch
nothing outside `mappings/`.** `python tools/preregistration_check.py` fails otherwise, and it exists
because the seven mappings published on 2026-08-31 each arrived in the same commit as the result
they scored, which cost this project the pre-registration claim (`docs/PROTOCOL.md` 3a).

`no-rule` and `unmappable` are permitted outcomes. Do not force a mapping for every class.

### 5. Run it
```bash
python tools/scanner_spec.py --run <tool> --corpus corpus2 --out raw/c2-<tool>.json --repeat 2
```

One invocation per case, per variant, with the case list read from `corpus2/manifest.json` on every
run and never written down. Three files come out: the findings, `<out>.log`, and
`<out>.determinism.json`.

**This is the step whose absence caused a retraction**, and it is now the step you cannot skip. A
findings file cannot prove coverage: a tool that ran a case and found nothing leaves the same silence
as one that never saw it. `run_leaf` writes the tool's complete stdout and stderr, plus a log entry
carrying the exact command, the exit code and the wall time, **before it returns, on success, on
crash and on timeout**. A log entry whose status is not `ok` carries `"findings": null`, not `0`, so
an outage has no findings count for anything downstream to read as a zero.

Classification is done from your declaration, not guessed:
- the tool said it read the files and reported nothing -> `ok`, and that is a real zero
- exit 0 having said nothing, or a crash, a timeout, unparseable output -> `unavailable`, never zero
- the declaration admits the tool prints no coverage line -> `unknown`, never zero

**Two things here are still yours.** The classification is only as good as the `coverage.evidence`
pattern you wrote, so check the first few `stdout.log` artefacts against the tool's own words rather
than trusting the status column. And the determinism check runs **only if you ask for it**: without
`--repeat 2` the verdict file says `not-checked`, which is honest and is not a determinism check.

### 6. Score
**Yours.** Nothing in the framework scores anything.

```bash
python tools/score2.py --scanner <name> --kind <name> --findings raw/c2-<name>.json
python tools/unmapped_check.py --findings raw/c2-<name>.json --kind <name>
python tools/run_all.py --verify-coverage                  # your row must not be a sixth gap
python tools/run_all.py                                    # appends a dated row to runs/
```
- `detected` requires the mapped rule to fire **at the site the fix changed** and not on the fix.
- `unlocated` means it fired in the file but not at the bug. Do not collapse it either way.
- `unmapped_check.py` catches a real detection hiding under a rule your mapping missed. That has
  happened once and it changed a published number.
- The `measurements` block of your declaration already put the row on the clock, so `run_all.py`
  picks it up with no second edit.

### 7. Compare shift-aware if you compare locations yourself
A fix that inserts lines moves every finding below it. Comparing `(rule, line)` naively reports
those as absent-after-the-fix, which reads as detection and is arithmetic. It produced 23 phantom
detections on one case. Use `shiftaware.py`.

### 8. Publish honestly
Lead with the number that hurts. Record limitations in the same commit. Third-party results are
**provisional** until the tool's authors have been offered the mapping for correction. If something
you published turns out to be wrong, **retract before you have the replacement**.

---

## Rules that override anything else you might infer

1. **Never tune to produce a result.** If changing a threshold, a mapping or a target would turn a
   zero into a number, the zero is the finding. This benchmark exists because vendors tune against
   the corpus they are measured on.
2. **A number you did not verify at its source is not a result.** Not a summary line, not a previous
   run's notes, not a file whose *name* says what it contains. One raw file here was named for a
   corpus it did not contain.
3. **Unavailable is not zero.** Publish a could-not-run table separately.
4. **Every score on corpus 1 is in-sample.** `sealevel-attacks` was last touched 2022-07-16 and at
   least two measured tools cite it in their own rule tables. Say so with every corpus-1 number.
5. **Corpus 2 is drawn from public postmortems**, which are famous because nobody caught them in
   time. It is systematically harder than the population of real bugs and understates every tool.
   It answers "do these catch the ones that cost money". It cannot support "these tools do not work".

---

## The deeper method

[`docs/ADAPTERS.md`](docs/ADAPTERS.md) is the declaration in full, with an eighth tool added end to
end and an explicit list of what a person must still do by hand.
[`docs/COVERAGE.md`](docs/COVERAGE.md) is the derived matrix of which measurement can show what it
analysed.

Three skills carry the full procedure, including the failures that produced each rule:

- [`skills/measure-a-scanner`](skills/measure-a-scanner/SKILL.md) - this file in depth
- [`skills/add-a-corpus-case`](skills/add-a-corpus-case/SKILL.md) - building ground truth: a fix
  commit that disables the program is not a fix
- [`skills/publish-a-measurement`](skills/publish-a-measurement/SKILL.md) - publishing, correcting,
  retracting

And [`docs/ENGINEERING-LOG-2026-08-31.md`](docs/ENGINEERING-LOG-2026-08-31.md) records 21 errors with dates.
Read it if you want to know which of the rules above were bought with real mistakes. All of them.

---

## What to hand back

A measurement is finished when it contains:

- the numbers, with **real recall** separated from nominal
- the per-run log proving every case was analysed, or an explicit list of what was not
- the mapping you pre-registered, unedited
- what you could not run, and why
- what would change the answer

If you cannot produce the second item, you do not have a measurement yet. Say that instead.
