---
name: measure-a-scanner
description: Use when adding a security scanner to the ScannerTruth benchmark, or when asked to measure, benchmark or compare a code scanner against a corpus. Enforces provenance before install, container isolation, a pre-registered mapping, proof that every case was actually analysed, a positive control on the scorer, and the separation of "could not run" from "found nothing".
---

# Measuring a scanner

Adding a scanner is this project's one repeatable unit of work. `adapters/` holds a declaration for
every tool measured so far, and on 2026-08-31 an audit found that two published headline numbers
were wrong. The order below is what survived that audit. Steps 4 and 6 exist because skipping them
produced retractions.

Repo: `github.com/halobartku/scannertruth`. Protocol: `PROTOCOL.md`. Every error referenced by
number is in `ENGINEERING-LOG-2026-08-31.md`.

## Before anything: prove the harness works

```bash
python test_all.py                          # 151 checks, mutation-verified; expect "151 passed, 0 failed"
python tools/scanner_spec.py --demo         # the adapter framework's own checks
python tools/scanner_spec.py --self-check   # every declaration's positive control
```

A harness that cannot check itself cannot tell you anything about somebody else's tool. If any check
fails, **stop and report that** rather than measuring. The suite is mutation-verified: five
deliberate defects were introduced and all five were caught, including one that reported a published
number changing under a refactor.

One command in this repository is **expected to fail**, and you should run it anyway so you are not
surprised by it later:

```bash
python tools/run_all.py --verify-coverage   # exits 1: some published rows cannot show what they analysed
```

It asks whether every measurement on the clock can show what it analysed, it runs in CI as its own
job (`coverage`, separate from `selfcheck`), and it is red because several historical measurements
were made by hand and the run log was the step a person had to remember. Read the current list
off the command rather than off a count written here; rows are being run and retired. A red
`coverage` beside a green `selfcheck` is not a broken build: the machinery is sound and the
numbers are not all accounted for. It closes with scanner runs, never with a code change and
never by relaxing it.

`AGENTS.md` at the repo root is the condensed executable form of this skill, written so an agent
handed the repository can act without reading further. `docs/WALKTHROUGH.md` is the same procedure
for a person, with a worked example on a tool already measured. `docs/ADAPTERS.md` is the
declaration in full.

## What the framework does, and what is still yours

Since 2026-09-01 the per-case loop is a **declaration**, not a script you write.
`adapters/<tool>.json` says what is different about the tool; `tools/scanner_spec.py` holds what is
the same about all of them.

**The protocol below has not changed. Only who performs each step has.** That distinction is the
whole reason this section exists: an agent that believes the framework does something it does not is
worse off than one that does everything by hand.

| The framework does this, before it returns | You still do this, and nothing checks it for you |
|---|---|
| the per-case, per-variant loop, with the case list read from the manifest every run | provenance: the tool's own repository and its documented install path |
| one artefact and one log line per invocation, on success, on crash and on timeout | the container image, where the vendor ships none |
| `ok` / `unavailable` / `unknown`, from the rule you declared | **the coverage pattern and the layout**, both read off the tool |
| rewriting container paths back onto corpus paths | the mapping, pre-registered in its own commit |
| the determinism verdict, **only when `--repeat 2` asks for it** | scoring, `unmapped_check.py`, the controls |
| the positive control across your parser, envelope and scorer | a parser, if the output shape is not one of the six already here |
| putting the row on the clock, from `measurements` | right of reply, and publishing |

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

## 2. Read the tool's argument shape and its coverage line. Yours, and only yours.

**Check the tool's argument shape before the run, not after.** We passed a flag to a binary when it
belonged to a subcommand, and all 18 runs failed identically. The harness correctly recorded them as
unavailable rather than as zeros, which is the point of the distinction, but the run was wasted.
`--help` on the binary *and* on the subcommand costs ten seconds.

Then one run against any directory, to answer the two questions the declaration has to state and
nothing can answer for you:

- **What does the tool print when it has read files?** `solsec` prints `Found N Rust files to
  analyze`; `radar` prints `Scanned N file`; `sol-azy` prints `N files scanned`. This is the line
  that separates a zero from an outage, and you are the one who reads it off the tool.
- **What shape is its output?** One of six the project already parses, or a seventh that needs a
  parser written. The seventh is the real limit on "adding a tool is a config file".

## 3. Declare the adapter, and check the declaration before running anything

Write `adapters/<tool>.json`. `docs/ADAPTERS.md` adds an eighth tool end to end and is the reference;
what follows is what this skill enforces about it.

**The container is a field, not a habit.** `"engine": "docker"`, `"network": "none"`, the corpus
mounted read-only by the framework. Standing constraint unchanged: nothing untrusted executes on the
host. Prefer the tool's official image; otherwise build inside `rust:slim` or equivalent, which is
still your job because the vendor may ship none.

**`coverage.evidence` decides every zero this tool will ever produce.** `validate` refuses a
declaration that omits it. A tool that prints no such line at all must say so with
`{"absent": true, "reason": "..."}`, and then every run is `unknown`, never a zero.

**`layout` is the other field you read off the tool.** Radar returned `400 Bad Request` on a bare
`.rs` file until a `Cargo.toml` was supplied, and later `No Cargo.toml files found in any
subdirectories` on a crate whose manifest sat at the **root** of the path it was given. It needs the
manifest in a *subdirectory*, which is `"layout": "wrapped-pkg"`. Every case laid out the other way
was an invocation error being scored as a miss. Record the first failed attempt; do not quietly
replace it with the successful run.

**`invocation_evidence` must cite a file in this repository**, not describe a memory. A command
typed from memory is the same class of claim as a number typed from memory, and the suite fails a
declaration that cites nothing. If nobody wrote the command down, the honest declaration says
`"engine": "unrecorded"` with a reason. Three published rows are in exactly that state.

Then, before running the tool at all:

```bash
python tools/scanner_spec.py --self-check
```

It plants your declared rule id at the fix site of a synthetic case, parses it with your parser,
writes it in your envelope, reads it back with the reader the clock uses, and requires the scorer to
say `detected`; then plants the same finding on the fixed variant and requires the answer to stop
being a detection. **If this fails, stop.** A parser that silently returns nothing is
indistinguishable from a tool that found nothing, and that exact defect once kept every check in the
repository green while turning every corpus-2 verdict into a miss.

Two traps before the suite finds them for you: a declaration must carry at least one entry in
`measurements`, and a measurement is on the clock unless you write `"on_clock": false`. Putting a
row on the clock changes the published tables, and a golden check will name the row that moved.

A tool that cannot run at all still goes in the **could-not-run** table with its reason. That table
is published.

## 4. Run it, and let the log be structural rather than remembered

**Error 20, the worst of the day.** We published that two scanners detected nothing across eight
real vulnerabilities. Both numbers were **extrapolated from one case each**. The findings files
covered a single case, no run log existed, and nothing noticed.

**A findings file cannot prove coverage.** A tool that ran a case and found nothing leaves exactly
the same silence as one that never saw it.

That is why this no longer depends on anyone remembering:

```bash
python tools/scanner_spec.py --run <tool> --corpus corpus2 --out raw/c2-<tool>.json --repeat 2
```

`run_leaf` writes the tool's complete stdout and stderr, plus a log entry carrying the exact
command, the exit code and the wall time, **before it returns, on success, on crash and on timeout**.
A log entry whose status is not `ok` carries `"findings": null`, not `0`, so an outage has no
findings count for anything downstream to read as a zero. One invocation per case, per variant, with
the case list read from `corpus2/manifest.json` on every run: it has been 9, then 16, then 17, and
it changed under a measurement once already.

Classification comes from the rule you declared, and the four outcomes stay four different facts:

- the tool said it read the files and reported nothing -> `ok`, and a zero here is a real zero
- **exit 0 having said nothing is `unavailable`, never a zero** - error 35, silence read as a
  measurement
- a crash, a timeout, or output no parser can read -> `unavailable`, never a zero
- the declaration admits the tool prints no coverage line -> `unknown`, never a zero

Error 21 is the same defect facing the other way: a clean zero recorded as an outage, made in the
harness built to prevent error 20, four hours later. Both directions are now one function,
`classify`, with a check that drives all four observations through it.

**Three things here are still yours.** The classification is only as good as the
`coverage.evidence` pattern you wrote, so read the first few `stdout.log` artefacts against the
tool's own words rather than trusting the status column. The determinism check runs **only if you
ask for it**: without `--repeat 2` the verdict file says `not-checked`, which is honest and is not a
determinism check. And a tool whose output shape is new needs a parser, which is code.

`run_all.py` records how coverage was established as `coverage_evidence`: `run log` when a
`<findings>.log` exists and is the authority, `none` when the question is unanswerable. A scanner
with unresolved cases drops to status `partial` with the reason attached, rather than reporting a
confident number over cases nobody can prove were analysed. Check your own row with
`python tools/run_all.py --verify-coverage` before publishing anything; it must not add another gap.

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
  could. `score2.py --demo` drives a synthetic case end to end on every run, and
  `scanner_spec.py --self-check` does the same **per declaration**, because a parser can break in
  one branch only and every other branch stays green while it does.

## 7. Score with the scorers, and compare shift-aware

```
# from the repository root
python tools/score.py --demo && python tools/score2.py --demo  # includes the positive control
python tools/scanner_spec.py --self-check                      # the same proof, per declaration
python tools/score2.py --scanner <name> --kind <name> --findings raw/c2-<name>.json
python tools/unmapped_check.py --findings raw/<file>.json --kind <name>
python tools/control_c2.py                                     # controls must score zero
python tools/run_all.py --verify-coverage                      # your row must show what it analysed
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
time. `--repeat 2` does the comparison for you, per leaf, by rule, file, line and column, and writes
the verdict beside the findings; both passes stay on disk and nothing is averaged. Without the flag
the verdict is `not-checked` and you have not answered the question. Most measurements here
predate the framework and have no determinism file at all, so check `raw/` before assuming a
published row has been repeated.

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
| "There is a declaration for this tool, so I can run it" | Three declarations say `engine: unrecorded`. Nobody wrote the command down, and `command_for` refuses rather than inventing one. |
| "The framework wrote a run log, so coverage is proved" | It proves the invocation happened and records what the tool said. Whether `ok` was the right verdict depends on the `coverage.evidence` pattern **you** wrote. Read the artefacts. |
| "The determinism file is there, so the tool is deterministic" | Without `--repeat 2` it says `not-checked`. That is an unanswered question, not an answer. |
| "The framework classified it, so I don't need to look at stdout" | `run_leaf` keeps the complete stdout and stderr of every invocation for exactly this. Looking is the cheapest check in the project. |
