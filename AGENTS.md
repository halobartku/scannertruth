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
on the teaching corpus and 2,392,280 on the real one, and scores **zero real recall** on both. If your
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
python tools/verify.py                                     # run-1 headline reproduces from raw data
python tools/control_c2.py                                 # controls must score zero
```

If all three pass, the harness is sound and you can trust what it tells you next. If any fails,
**stop and report that** rather than measuring anything.

---

## Measuring a scanner, end to end

### 1. Provenance, before you download anything
Find the tool's **own repository** and use the install path it documents. Check that any registry
package maps to that repo: author, repo link, publish date. `cargo install radar` nearly installed
an unrelated 2021 crate by a different author. If an install script is piped to a shell, read it in
full first and say so.

### 2. Run it in a container
Never on the host. Prefer the tool's official image, otherwise build inside `rust:slim`. Mount the
corpus **read-only**.

### 3. Write the mapping BEFORE you run it
Create `mappings/<scanner>.json` mapping the tool's rule ids to corpus classes, derived from **the
tool's own rule names and documentation**, never from which rules happened to fire. Commit it in its
own commit before the run; that timestamp is the pre-registration. **That commit must touch nothing
outside `mappings/`.** `python tools/preregistration_check.py` fails otherwise, and it exists
because the seven mappings published on 2026-08-31 each arrived in the same commit as the result
they scored, which cost this project the pre-registration claim (`docs/PROTOCOL.md` 3a).

`no-rule` and `unmappable` are permitted outcomes. Do not force a mapping for every class.

### 4. Run per case, per variant, and keep a log per run
**This is the step whose absence caused a retraction.** A findings file cannot prove coverage: a
tool that ran a case and found nothing leaves the same silence as one that never saw it.

Write one log entry per invocation: `{"leaf": "<case>/<variant>", "status": "ok|error", ...}` saved
as `<findings-file>.log`. `run_all.py` treats that log as the authority on which cases were
analysed, and reports `unknown` when it is absent rather than guessing.

Classify carefully:
- output exists and parses -> a result
- **exit 0 with no output -> a clean zero, not an outage** (read the tool's own log line)
- error, timeout, crash -> **unavailable, never zero**

### 5. Give the tool the layout it expects
Radar returns `400 Bad Request` on a bare `.rs` file, and `No Cargo.toml files found in any
subdirectories` when the manifest sits at the root of the path it is given. It wants the manifest
one level down. Record the failed attempt, then fix the layout and rerun; do not silently replace
one with the other.

### 6. Score
```bash
python tools/score2.py --scanner <name> --kind <name> --findings c2-<name>.json
python tools/unmapped_check.py --findings c2-<name>.json --kind <name>
python tools/run_all.py                                    # appends a dated row to runs/
```
- `detected` requires the mapped rule to fire **at the site the fix changed** and not on the fix.
- `unlocated` means it fired in the file but not at the bug. Do not collapse it either way.
- `unmapped_check.py` catches a real detection hiding under a rule your mapping missed. That has
  happened once and it changed a published number.

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
