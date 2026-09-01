---
name: measure-a-scanner
description: Use when adding a security scanner to the ScannerTruth benchmark, or when asked to measure, benchmark or compare a code scanner against a corpus. Enforces provenance before install, container isolation, a pre-registered mapping, proof that every case was actually analysed, a positive control on the scorer, and the separation of "could not run" from "found nothing".
---

# Measuring a scanner

Adding a scanner is this project's one repeatable unit of work. It has been done six times, and on
2026-08-31 an audit found that two published headline numbers were wrong. The order below is what
survived that audit. Steps 3 and 6 exist because skipping them produced retractions.

Repo: `github.com/halobartku/scannertruth`. Protocol: `PROTOCOL.md`. Every error referenced by
number is in `ENGINEERING-LOG-2026-08-31.md`.

## Before anything: prove the harness works

```bash
python test_all.py     # 123 checks, mutation-verified; expect "123 passed, 0 failed"
```

A harness that cannot check itself cannot tell you anything about somebody else's tool. If any check
fails, **stop and report that** rather than measuring. The suite is mutation-verified: five
deliberate defects were introduced and all five were caught, including one that reported a published
number changing under a refactor.

`AGENTS.md` at the repo root is the condensed executable form of this skill, written so an agent
handed the repository can act without reading further. `WALKTHROUGH.md` is the same procedure for a
person, with a worked example on a tool already measured.

## The rule that outranks the rest

**A number you did not verify at its source is not a result.** Not the tool's summary line, not a
subagent's report, not a previous run's notes, not a file whose *name* says what it contains.

The generalised form, learned the expensive way: **everything that survived the audit had an
artefact per run; everything that collapsed had been inferred from a summary.**

## 1. Provenance, before anything is downloaded

`cargo install <name>` nearly installed an unrelated 2021 crate by a different author, because the
real tool was not published to that registry at all.

- Find the tool's **own repository** first and take the install path it documents.
- Check the registry name maps to that repo: author, repo link, publish date, downloads.
- If an install script is piped to a shell, **download and read it in full first**, and say so.
- Name mismatch, or a package whose repo does not mention the tool: stop and report.

## 2. Run it in a container, never on the host

Standing constraint: nothing untrusted executes on the host. Prefer the tool's official image;
otherwise build inside `rust:slim` or equivalent, with the corpus mounted **read-only**.

## 3. Prove every case was analysed. This is the step that was missing.

**Error 20, the worst of the day.** We published that two scanners detected nothing across eight
real vulnerabilities. Both numbers were **extrapolated from one case each**. The findings files
covered a single case, no run log existed, and nothing noticed.

**A findings file cannot prove coverage.** A tool that ran a case and found nothing leaves exactly
the same silence as one that never saw it.

So, before scoring anything:

- Run **per case, per variant**, one invocation each, and write a log line per invocation recording
  that it was attempted and how it ended.
- Print success **only after the output file exists and parses**. Radar prints
  `Results written to <path>` for files it did not write.
- **Exit code 0 with no output is a clean zero, not an outage** - error 21, made in the harness
  built to prevent error 20, four hours later. Read the tool's own log line before classifying.
- Absent or unparseable output is **unavailable**, never zero. With no log at all the honest
  verdict is **unknown**; guessing either way has already been wrong once in each direction.
- **Check the tool's argument shape before the run, not after.** We passed a flag to a binary when
  it belonged to a subcommand, and all 18 runs failed identically. The harness correctly recorded
  them as unavailable rather than as zeros, which is the point of the distinction, but the run was
  wasted. `--help` on the binary *and* on the subcommand costs ten seconds.

`run_all.py` records how coverage was established as `coverage_evidence`: `run log` when a
`<findings>.log` exists and is the authority, `none` when the question is unanswerable. A scanner
with unresolved cases drops to status `partial` with the reason attached, rather than reporting a
confident number over cases nobody can prove were analysed.

## 4. Give the tool what it expects before judging it

Radar returned `400 Bad Request` on a bare `.rs` file until a `Cargo.toml` was supplied, and later
`No Cargo.toml files found in any subdirectories` on a crate whose manifest sat at the **root** of
the path it was given. It needs the manifest in a *subdirectory*. Every case laid out the other way
was an invocation error being scored as a miss.

- Supply the manifest, workspace or build artefact the tool documents, and check the layout it
  expects rather than the one that seems obvious.
- Record the first failed attempt; do not quietly replace it with the successful run.
- A tool that cannot run at all goes in the **could-not-run** table with its reason. That table is
  published.

## 5. Pin the corpus, and say when you pinned it

Nothing in this repository recorded which corpus state produced its headline until it was dug out
of a working checkout after the fact. Record the commit **before** the run, in `PROTOCOL.md`. If
you recover it afterwards, say that you did.

Worth knowing about the teaching corpus: `sealevel-attacks` was last touched **2022-07-16** and at
least two measured tools cite its class pages in their own rule tables. **Every score on it is
in-sample**, including ours. Say so before anyone asks.

## 6. Write the mapping down before you score, and check the scorer can say yes

`mappings/<scanner>.json` maps the tool's rule ids to classes, derived from **the tool's own rule
names and documentation**, committed **in its own commit before the run** so the timestamp is the
pre-registration.

- **The commit must contain nothing but `mappings/`.** Run `python tools/preregistration_check.py`
  after committing it; a mapping that arrives beside a results page, a run file or a raw findings
  file is not pre-registered, whatever the commit message says. This is enforced because it was
  once only asserted: the seven mappings published on 2026-08-31 each arrived in the same commit as
  their result, and the claim had to be retracted (`docs/PROTOCOL.md` 3a).
- Use the ids the tool actually emits.
- `no-rule` and `unmappable` are permitted outcomes. Forcing a mapping for every class
  manufactures failures.
- **Beware narrowing a generic rule on the strength of a vendor blog post.** X-Ray's rule named
  "the account may not be properly validated" was mapped to one class because a blog presented it
  as catching one specific hack. It detected a real vulnerability at the fix site and our mapping
  scored it zero (error 17). Publish both numbers and leave the pre-registered map unedited.
- **Validate the scorer against a known positive before believing its zeros.** Until 2026-08-31
  this project's corpus-2 scorer had never once returned `detected`, and nobody had checked that it
  could. `score2.py --demo` now drives a synthetic case end to end on every run.

## 7. Score with the scorers, and compare shift-aware

```
# from the repository root
python tools/score.py --demo && python tools/score2.py --demo  # includes the positive control
python tools/score2.py --scanner <name> --kind <name> --findings raw/c2-<name>.json
python tools/unmapped_check.py --findings raw/<file>.json --kind <name>
python tools/control_c2.py                                     # controls must score zero
```

- **Real recall** is the only number that means anything: the mapped rule fires on the vulnerable
  variant **and stays silent on the same program fixed**.
- Corpus 2 additionally requires the finding to land **where the fix changed something**.
- **A fix that inserts lines moves every finding below it.** Comparing `(rule, line)` naively
  reports those as present-only-on-the-vulnerable-variant, which reads as detection and is
  arithmetic. It produced 23 phantom "detections" on one case (error 19). Map each line through the
  diff hunks before comparing: `shiftaware.py`.
- **Per-class scoring cannot see a detection under an unmapped rule.** `unmapped_check.py` asks the
  complementary question and is itself validated against the one case known to be real.

## 8. Check the controls, every time

`control-noisy` flags every non-empty line: 81,928 findings on corpus 1, 2,629,968 on corpus 2, and
**zero real recall on both**. If it ever scores above zero, the scorer is crediting volume and every
result is void. `control-null` establishes the floor.

Run each scanner **twice** and compare findings by rule and location before trusting anything over
time.

## 9. Never tune to produce a result

If changing a threshold, a mapping or a target would turn a zero into a number, **the zero is the
finding**. This is the whole thesis of the project turned on itself: vendors tune against the corpus
they are measured on, and doing the same makes the benchmark worthless.

If a parameter genuinely must change, say in writing that it changed **after** seeing results, and
why. Two things were nearly tuned on 2026-08-31: a mapping we wanted to "clarify" after seeing a
score, and a candidate-selection target that would have made trades appear before a deadline.

## 10. Publish the uncomfortable number first

- A third-party tool beating ours goes in the first paragraph.
- A tool whose claim the measurement **confirms** gets said plainly.
- **Retract before you have the replacement.** When the Radar and VaultLint numbers were found to
  rest on one case each, the retraction was published before the re-measurement existed. Leaving an
  unsupported claim standing while gathering better numbers is the wrong order.
- Add what is still wrong to `KNOWN-LIMITATIONS.md` in the same commit, not later.
- Third-party results stay **provisional** until the tool's authors have been offered the mapping
  for correction (`PROTOCOL.md`, right of reply).

## Related skills

This skill covers **running a tool against a corpus**. Two neighbouring jobs have their own traps
and their own skill:

- **`add-a-corpus-case`** - acquiring, triaging and validating ground truth. Different failure
  modes entirely: a fix commit that disables the program rather than repairing it, scope judgements
  that must be written down including the rejections, and the selection bias of a corpus drawn from
  incidents that are famous because nobody caught them.
- **`publish-a-measurement`** - what to do when the number goes public, and what to do when it
  turns out to be wrong afterwards. Retract before the replacement exists; correct the mechanism,
  not only the number; right of reply.


## Red flags

| Thought | Reality |
|---|---|
| "The tool printed a summary, I'll use that" | Open the raw output and count. |
| "The agent reported 4/11, good enough" | Rerun the scorer yourself. It has been wrong. |
| "It found nothing, so it scores zero" | Only if you can prove it ran. Otherwise: unavailable. |
| "No output means it failed" | Exit 0 with no findings is a clean zero. Read the tool's log line. |
| "This file is named c2-<tool>.json, so it is the corpus-2 run" | One such file was the Wormhole real-crate run. Check the paths inside. |
| "Same rule, different line, so it disappeared after the fix" | The fix moved the lines. Compare shift-aware. |
| "This symbol is present, so the check exists" | `declare_id!` is in every Anchor program and guards nothing. |
| "I'll adjust the mapping so the result makes sense" | The mapping is pre-registered, and it is theirs to correct, not ours to tune. |
| "The scorer returns zero everywhere, so nothing detects anything" | Prove the scorer can return a positive first. |
| "One case is enough to say scanners don't work" | n=1 is a direction to test. Two headlines were extrapolated from n=1 and had to be retracted. |
