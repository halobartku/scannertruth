# Walkthrough: measure a scanner yourself

A complete worked example, for a person, with every command and what you should see. It measures
**VaultLint**, a tool we have already measured, so you can compare your result to ours and know
whether you did it right.

Roughly 40 minutes, most of it a container build you can walk away from.

**Before you start**, read one paragraph in [`docs/GETTING-STARTED.md`](../docs/GETTING-STARTED.md): the concept
of **real recall**. Without it the numbers below are meaningless.

---

## What you need

- Python 3, already required for everything here
- **Docker**, and this is the one hard rule: a scanner you did not write never runs on your machine
  directly. It runs in a container with the corpus mounted read-only.
- About 2 GB of disk for the container image

---

## Step 0. Prove the harness works before you trust it

```bash
git clone https://github.com/halobartku/scannertruth
cd scannertruth
python test_all.py
```

Expect `151 passed, 0 failed`. **If anything fails, stop.** A harness that cannot check itself cannot
tell you anything about somebody else's tool, and reporting a number from a broken harness is how
this project produced a retraction.

---

## Step 1. Find the tool's real home before downloading anything

Do not search a package registry and install the first name that matches. `cargo install radar`
would have installed **an unrelated 2021 crate by a different author**, and we would have measured a
random package and called it a competitor.

For VaultLint: the crate on crates.io, its listed repository, and the version. Check that the name
maps to the project you think it is.

**If a name does not map to a repository that mentions the tool, stop and say so.** That is a
finding, not an obstacle.

---

## Step 2. Write the mapping BEFORE you run anything

This is the step that makes the result honest. You are deciding, in advance, **which of the tool's
rules is supposed to catch which class of bug** - and you decide it from the tool's own
documentation, never from which rules turn out to fire.

```bash
cp mappings/vaultlint.json mappings/my-vaultlint.json
# now edit it: read the tool's rule list and map each rule to a corpus class
git add mappings/my-vaultlint.json
git commit -m "pre-register mapping for vaultlint"
python tools/preregistration_check.py
```

That second command is not decoration. A mapping commit may contain **nothing but `mappings/`**. If
it arrives beside a results page, a run file or a raw findings file, it is not pre-registered
whatever the commit message says, and CI rejects it. This is enforced because it was once only
asserted: the seven mappings published on 2026-08-31 each arrived in the same commit as the result
they scored, and the claim had to be retracted. See `docs/PROTOCOL.md` 3a.

**Commit it on its own, before the run.** The commit timestamp is the pre-registration, and it is
the only thing that stops you from quietly adjusting the mapping once you dislike the score.

Two outcomes are allowed and you should use them:
- `no-rule`: the tool never claimed to cover this class. A coverage gap, not a failure.
- `unmappable`: the rule's description is too broad to tie to one class.

**A trap we fell into.** X-Ray has a rule called "the account may not be properly validated". We
mapped it to one narrow class because the vendor's blog presented it as catching one specific hack.
That was an example of the rule, not its scope. It detected a real vulnerability and our mapping
scored it zero. Map from the rule's own name and docs, not from marketing.

---

## Step 3. Build the tool in a container

```bash
docker build -t vaultlint-runner:local - <<'EOF'
FROM rust:slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      pkg-config libssl-dev ca-certificates && rm -rf /var/lib/apt/lists/*
RUN cargo install vaultlint --version 0.1.1 --locked
ENTRYPOINT ["vaultlint"]
EOF
```

Ten to twenty minutes. Pin the version: an unpinned build measures whatever shipped today and your
number stops being comparable to anyone else's.

Then find out how it wants to be called, because guessing wastes a whole run. **Save the output**,
because the next step has to cite it:

```bash
mkdir -p raw
docker run --rm --entrypoint vaultlint vaultlint-runner:local --help       > raw/my-vaultlint-help.txt
docker run --rm --entrypoint vaultlint vaultlint-runner:local scan --help >> raw/my-vaultlint-help.txt
```

**We got this wrong and it cost 18 runs.** We passed `--format json` to the binary when it belongs
to the `scan` subcommand. All 18 failed identically. The harness correctly recorded them as
**unavailable rather than as zeros**, which is the whole point of the distinction, but the run was
still wasted.

While you are here, run the tool once against any directory and **watch for the line where it says
how many files it read**. That one line is what separates "found nothing" from "never ran", it is
the field the next step cannot be written without, and nothing but the tool itself can tell you what
it looks like.

---

## Step 4. Declare it, instead of writing the runner

Until this afternoon this walkthrough handed you a shell loop here: twenty lines that walked
`corpus2/*/`, invoked the container per variant, redirected stdout to a file and appended a line to
`out/run.log`. It worked, and it is gone, because **four of its defects have each cost this project
a published number**:

- it enumerated directories rather than reading `corpus2/manifest.json`, so it would have run cases
  the manifest marks invalid and missed the fact that the case count has been 9, then 16, then 17
- `echo "rc=$?"` after a redirect reports the exit code of the redirect, not of the tool
- if the loop died halfway, the cases it never reached left no trace at all
- and it left the hardest decision, zero versus outage, to you at the end, from files that no longer
  remembered what the tool had said

All four are the same defect wearing different hats, and the fix is not a better loop. It is to stop
writing loops. `tools/scanner_spec.py` holds the loop, once; `adapters/<tool>.json` holds what is
different about your tool. [`docs/ADAPTERS.md`](ADAPTERS.md) is the reference and adds an eighth tool
end to end.

### The declaration

```bash
python tools/scanner_spec.py --list       # what is already declared, and what each row feeds
```

Copy the shape and write `adapters/my-vaultlint.json`:

```json
{
 "name": "my-vaultlint",
 "version": "0.1.1",
 "homepage": "https://github.com/vaultlint/vaultlint",
 "provenance": {
  "repository": "https://github.com/vaultlint/vaultlint",
  "install": "cargo install vaultlint --version 0.1.1 --locked, inside rust:slim",
  "install_documented_at": "the crate's own page and repository README",
  "checked_on": "the date you did step 1"
 },
 "run": {
  "engine": "docker",
  "image": "vaultlint-runner:local",
  "network": "none",
  "mount": "/src",
  "command": ["scan", "--format", "json", "--fail-on", "never", "{mount}"],
  "timeout_seconds": 900,
  "invocation_evidence": "raw/my-vaultlint-help.txt, the --help output saved in step 3"
 },
 "layout": "variant-dir",
 "coverage": {
  "ok_exit_codes": [0],
  "evidence": {
   "pattern": "PUT THE LINE YOU SAW IN STEP 3 HERE, capturing the count as group 1",
   "minimum": 1,
   "means": "vaultlint's own count of the files it opened"
  }
 },
 "output": {"from": "stdout", "format": "vaultlint"},
 "envelope": "vaultlint",
 "positive_control": {
  "rule_id": "VL002",
  "sample": {"findings": [{"rule_id": "VL002", "file": "{path}", "line": "{line}"}]}
 },
 "measurements": [
  {"row": "my-vaultlint", "corpus": "corpus2", "raw": "c2-my-vaultlint.json",
   "mapping": "my-vaultlint", "on_clock": false}
 ]
}
```

**Three traps in that file, and we hit all three.**

`"on_clock": false` keeps your row off the published tables. Leave it out and your row joins the
clock, a golden check compares the derived tables against the committed ones, and the suite tells
you a published row moved. It is not wrong to put a row on the clock; it is wrong to do it by
accident.

`invocation_evidence` must name a file that exists in this repository. The suite refuses a
declaration that states a command and cites nothing, because a command typed from memory is the same
class of claim as a number typed from memory. Before the run the thing you have to cite is the
`--help` transcript from step 3, so save it: `docker run ... --help > raw/my-vaultlint-help.txt`.

**`coverage.evidence.pattern` is the one field you cannot copy from us**, and this is the honest
part of the walkthrough. Our own `adapters/vaultlint.json` said `"engine": "unrecorded"` and
`"evidence": {"absent": true, ...}` until 2026-09-01, because nobody had written down how VaultLint
was invoked on 2026-08-31 or what it prints when it has read files. That line has since been
recovered, by reading the committed artefacts rather than by remembering, and it is worth showing
you what it turned out to be: VaultLint has no single argv that answers both questions. `--format
json` gives the findings and no file count; the human formatter gives `analyzing N Rust file` and
nothing a parser can read. So the declaration runs the tool twice inside one container, human
output to stderr for what it read and json to stdout for what it found, and the pattern reads the
first. Expect your tool to make you work for this field too. If it turns out to print no such line
at all, say so with `{"absent": true, "reason": "..."}` and every run comes back `unknown`, which is
the honest verdict when the question cannot be answered, and can never quietly become a zero.

### Check the declaration before you run anything

```bash
python tools/scanner_spec.py --self-check
```

This plants `VL002` at the fix site of a synthetic vulnerable/fixed pair, parses it with VaultLint's
parser, writes it in VaultLint's envelope, reads it back with the same code that reads every
committed findings file, and requires the scorer to say `detected`. Then it plants the same finding
on the fixed variant too and requires the answer to stop being a detection.

**If this fails, stop.** A parser that silently returns nothing is indistinguishable from a tool that
found nothing, and that exact failure once kept every check in this repository green while turning
every corpus-2 verdict into a miss.

---

## Step 5. Run it

```bash
python tools/scanner_spec.py --run my-vaultlint --corpus corpus2 --out raw/c2-my-vaultlint.json --repeat 2
```

One invocation per case, per variant, with the case list read from the manifest on every run. Three
files come out:

```
raw/c2-my-vaultlint.json                    the findings, in vaultlint's own envelope
raw/c2-my-vaultlint.json.log                one entry per invocation: command, exit code, wall time, status
raw/c2-my-vaultlint.json.determinism.json   deterministic, non-deterministic, or not-checked
```

### What you no longer have to remember

**The run log.** This was the step whose absence caused us to retract a published headline: a
findings file cannot prove a case was analysed, because a tool that ran and found nothing leaves
exactly the same silence as a tool that never saw the case. We published "0 of 8" for two scanners
when the data behind it covered one case each. The framework writes the tool's complete stdout and
stderr, plus a log entry carrying the exact command, the exit code and the wall time, **before it
returns, on success, on crash and on timeout**. There is no path through it that produces a findings
file and no log.

**The classification.** We used to get this wrong in both directions: we scored invocation errors as
"did not detect", and then, in the harness written to prevent that, we scored a clean zero as
unavailable. It is one function now, and the four outcomes stay four different facts:

| What happened | What it is |
|---|---|
| The tool said it read the files and reported nothing | `ok`, and a **clean zero** |
| Exit 0 having said nothing | `unavailable`, **never zero** |
| Error, timeout, crash, bad arguments, output no parser can read | `unavailable`, **never zero** |
| Your declaration admits the tool prints no coverage line | `unknown`, **never zero** |

**The determinism check.** `--repeat 2` runs every invocation twice and compares findings by rule,
file, line and column. Both passes stay on disk and nothing is averaged.

### What is still yours, and do not skip it

The status column is only as good as the `coverage.evidence` pattern you wrote. Open two or three of
the artefacts under `raw/c2-my-vaultlint-runs/` and read the tool's own words against the verdict
the framework gave them. If your pattern never matches, every case comes back `unavailable` and you
have an outage, not a measurement. If it matches something it should not, you have manufactured
clean zeros, which is worse.

And `--repeat 2` is a flag, not a default. Without it the determinism file says `not-checked`, which
is an unanswered question rather than an answer.

---

## Step 6. Score it

```bash
python tools/score2.py --scanner my-vaultlint --kind vaultlint --findings raw/c2-my-vaultlint.json
python tools/unmapped_check.py --findings raw/c2-my-vaultlint.json --kind vaultlint
```

You will get one verdict per case:

- **`detected`** - the mapped rule fired at the site the fix changed, and stayed silent on the fix
- **`unlocated`** - it fired in the right file but not at the bug. Neither a hit nor a clean miss,
  and the category exists so you cannot quietly pick whichever suits you
- **`missed`** - the mapped rule never fired
- **`no-rule`** - the tool has no rule for this class at all

`unmapped_check.py` asks the complementary question: **did something detect the bug under a rule
your mapping missed?** Run it. It is how we found the only real detection in the whole corpus, under
a rule we had mapped to the wrong class.

---

## Step 7. Check your row can show what it analysed

```bash
python tools/run_all.py --verify-coverage
```

This asks of every measurement on the clock the one question a findings file cannot answer: can this
row show what it analysed? It runs in CI as its own job. It was **red on the morning of
2026-09-01**, because several rows published before this framework existed were run by hand and
nobody wrote the log; our own corpus-1 VaultLint row was one of them. It went green the same day
once those rows were re-run per case.

Your row is off the clock while `"on_clock": false` is in your declaration, so this will not list it.
Read your own `raw/c2-my-vaultlint.json.log` instead and answer the same question of it: is there one
entry per case per variant, and does every entry that is not `ok` carry a reason?

---

## Step 8. Compare to ours

Our published result on the real-vulnerability corpus: **0 of 17 as registered, 1 of 17 corrected**,
with **15 of the 17 `no-rule`**, which is a stated coverage limit rather than a failure. That leaves
a scoreable denominator of two. The corrected one is VL002, `missing owner check`, which fires on
`anchor-account-reload-owner` at the line the fix guards and is silent once the owner check is added.
Our pre-registered mapping points VL002 at a different class, so as registered it scores zero, and
both numbers are published with the mapping left unedited.

VaultLint is currently the only row measured over all seventeen built cases. On the teaching corpus
it scores 2/11 real recall with 4 findings across 35 files, and **its precision claim held**:
everything it detected, it detected correctly.

Denominators move here as cases are built and rows are re-run, so take the current ones from
`python tools/run_all.py` rather than from this page. If your numbers differ from what it prints,
one of us is wrong and we would like to know which. Open an issue.

---

## Step 9. Sanity-check yourself against the controls

Before believing any number you just produced:

```bash
python tools/control_c2.py
```

The noisy control flags every non-empty line: **2,629,968 findings, and it must score zero.** If your
method would give it anything above zero, your method is counting volume. This is the check that
separates a measurement from a marketing figure.

---

## What a finished measurement contains

Not just the number. All five:

1. the numbers, with **real recall separated from nominal**
2. the **per-run log** proving each case was analysed, or an explicit list of what was not
3. the mapping you pre-registered, **unedited**
4. what you could not run, and why, kept **separate** from what found nothing
5. what would change the answer

**If you cannot produce item 2, you do not have a measurement yet.** Say that instead of publishing
a number. We learned this the expensive way and it is written into
[`docs/PROTOCOL.md`](../docs/PROTOCOL.md).

Items 2 and 4 are now the framework's: they are the `.log` file beside your findings, and it is
written whether the run succeeds, crashes or times out. Items 1, 3 and 5 are yours, and item 5 is
the one nothing will ever produce for you.

---

## And one rule that outranks the rest

**If changing a threshold, a mapping, or a target would turn a zero into a number, the zero is the
finding.**

This benchmark exists because vendors tune against the corpus they are measured on. The moment you
do the same, your measurement is worth exactly what theirs is.
