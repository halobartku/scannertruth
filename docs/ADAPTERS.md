# Adding a scanner: the declaration

Adding a scanner to this benchmark used to cost an evening, and almost none of that evening went on
the scanner. Two people each added one on 2026-09-01, and both reports say the same thing about
where the time went: writing, for the fifth and sixth time, a per-case runner that walks the corpus,
invokes a container, captures stdout, decides whether the run actually happened, writes an artefact,
writes a log line, rewrites container paths onto corpus paths, and aggregates a findings file.

Those runners differ in four places: the image, the argv, the pattern that reads the tool's own
"I read N files" line, and the shape of its output. Those four things are a declaration now.

```
adapters/<tool>.json      what is different about this tool
tools/scanner_spec.py     what is the same about all of them
```

```bash
python tools/scanner_spec.py --list          # what is declared, and which clock rows it feeds
python tools/scanner_spec.py --self-check    # every declaration's positive control
python tools/scanner_spec.py --demo          # the module's own checks
python tools/run_all.py --verify-coverage    # can every measurement show what it analysed?
```

---

## What comes for free, and how each one is enforced

None of these is a convention somebody has to remember. Each is either refused at load time or
checked by the suite, because each of them is a mistake this project has already published.

| | How it comes for free | Enforced by |
|---|---|---|
| **An artefact and a log line per invocation**, with the exact command, exit code and wall time | `run_leaf` writes the tool's complete stdout and stderr before it returns, on success, on crash and on timeout | `test_the_framework_writes_an_artefact_and_a_log_line_for_every_invocation` drives four invocations, one of which crashes, and requires all four |
| **Unavailability classified, not inferred** | the declaration must say how the tool announces that it read the code; without that line the run is `unavailable`, never a zero | `validate` refuses a declaration that omits `coverage.evidence`; `test_a_clean_zero_and_an_outage_can_never_carry_the_same_status` drives the four observations a naive harness collapses into one |
| **A determinism check** | `--repeat 2` runs every leaf twice and compares findings by rule, file, line and column | `test_a_scanner_that_disagrees_with_itself_is_reported_not_averaged`; both passes stay on disk and nothing is averaged |
| **A positive control that crosses the parser** | the declaration carries a sample of the tool's own output holding one real finding, planted at the fix site of a synthetic case | `test_every_declaration_can_carry_a_detection_through_its_own_parser`, run for every declaration on every run of the suite |

The unavailability rule has four outcomes and they are different facts:

```
the tool said it read the files, and reported nothing   ok         a real zero
the tool exited 0 having said nothing                   unavailable  never a zero
the tool crashed, timed out, or was killed              unavailable  never a zero
the declaration admits the tool prints no such line     unknown      never a zero
```

A tool with no coverage line at all is still measurable: say so with
`"evidence": {"absent": true, "reason": "..."}` and every run is recorded `unknown`. That is the
honest verdict when the question cannot be answered, and `unknown` can never become a zero by
default. `--verify-coverage` counts it as a gap, which it is.

---

## Adding an eighth tool, end to end

Suppose a tool called **solguard** exists, it runs in a container, and it prints JSON. Here is the
whole job.

### 1. Provenance, before anything is downloaded

Find its own repository and take the install path it documents. `cargo install radar` nearly
installed an unrelated 2021 crate by a different author. Check that any registry package maps to
that repository: author, repo link, publish date.

### 2. Check its argument shape and its coverage line

Ten seconds of `--help` on the binary *and* on the subcommand, then one run on any directory, to
answer two questions the declaration has to state: what does it print when it has read files, and
what does its output look like?

### 3. Write `adapters/solguard.json`

```json
{
 "name": "solguard",
 "version": "1.2.0",
 "homepage": "https://github.com/example/solguard",
 "provenance": {
  "repository": "https://github.com/example/solguard",
  "install": "docker pull ghcr.io/example/solguard:1.2.0",
  "install_documented_at": "https://github.com/example/solguard README, install section",
  "checked_on": "2026-09-02"
 },
 "run": {
  "engine": "docker",
  "image": "ghcr.io/example/solguard:1.2.0",
  "network": "none",
  "mount": "/src",
  "command": ["scan", "--json", "{mount}"],
  "timeout_seconds": 900,
  "invocation_evidence": "solguard scan --help, read before the first run"
 },
 "layout": "variant-dir",
 "coverage": {
  "ok_exit_codes": [0],
  "evidence": {
   "pattern": "analysed (\\d+) source files",
   "minimum": 1,
   "means": "solguard's own count of the files it opened"
  }
 },
 "output": {"from": "stdout", "format": "semgrep"},
 "envelope": "semgrep",
 "positive_control": {
  "rule_id": "SG-014",
  "sample": {"results": [{"check_id": "SG-014", "path": "{path}",
                          "start": {"line": "{line}"}}]}
 },
 "measurements": [
  {"row": "solguard", "corpus": "corpus2", "raw": "c2-solguard.json",
   "mapping": "solguard"}
 ]
}
```

`format` is how the tool speaks; `envelope` is how its findings are stored. They are usually the
same. Both come from a fixed set the scorers already read: `radar`, `xray`, `sol-audit`,
`vaultlint`, `semgrep`, `solsec`, and `text-regex` for a tool that prints prose rather than JSON.
A tool whose output matches none of them needs a parser adding to `tools/scanner_spec.py`, and that
is the one part of adding a tool that is still code.

### 4. Check the declaration before running anything

```bash
python tools/scanner_spec.py --self-check
```

This plants `SG-014` at the fix site of a synthetic vulnerable/fixed pair, parses it with
solguard's parser, writes it in solguard's envelope, reads it back with the same code that reads
every committed findings file, and requires the scorer to say `detected`. Then it plants the same
finding on the fixed variant too and requires the answer to stop being a detection.

If this fails, stop. A parser that silently returns nothing is indistinguishable from a tool that
found nothing, and that exact failure once kept every check in this repository green while turning
every corpus-2 verdict into a miss.

### 5. Pre-register the mapping, in its own commit

`mappings/solguard.json`, derived from solguard's own rule names and documentation, never from
which rules happened to fire. The commit must touch nothing outside `mappings/`.

```bash
git add mappings/solguard.json && git commit -m "Pre-register the solguard mapping"
python tools/preregistration_check.py
```

### 6. Run it

```bash
python tools/scanner_spec.py --run solguard --corpus corpus2 --out raw/c2-solguard.json --repeat 2
```

One invocation per case per variant, with the case list read from `corpus2/manifest.json` on every
run and never written down. Three files come out:

```
raw/c2-solguard.json                    the findings, in solguard's own envelope
raw/c2-solguard.json.log                one entry per invocation: command, exit code, wall time, status
raw/c2-solguard.json.determinism.json   deterministic, non-deterministic, or not-checked
```

### 7. Score it, and check the coverage

```bash
python tools/score2.py --scanner solguard --kind semgrep --findings raw/c2-solguard.json
python tools/unmapped_check.py --findings raw/c2-solguard.json --kind semgrep
python tools/run_all.py --verify-coverage
python tools/run_all.py
```

The `measurements` block already put solguard on the clock, so `run_all.py` picks it up with no
further edit. `--verify-coverage` will say whether its run log accounts for every case.

### What is still by hand

Everything in this list is a judgement, not a keystroke, which is why none of it is generated:

- **provenance**: finding the tool's own repository and reading its documented install path
- **the mapping**, and the decision that a class has `no-rule` rather than a forced match
- **the container image**: building one where the vendor ships none
- **the coverage pattern and the layout**: both are read off the tool, and both are the traps.
  radar refuses a target whose `Cargo.toml` sits at the root of the path it is given and exits 0
  writing nothing; sol-azy reads nothing at all unless a directory looks like an Anchor or SBF
  project. Each produced a silent zero that looked exactly like a clean miss.
- **a new parser**, if the tool's output shape is not one of the six already here
- **right of reply**: the result is provisional until the tool's authors have been offered the
  mapping for correction

---

## The declarations that exist

`python tools/scanner_spec.py --list` prints this, derived. Nine tools are declared; four can be
run from the declaration alone.

Three carry `"engine": "unrecorded"`: sol-audit v2, VaultLint and X-Ray. Nobody wrote down how they
were invoked, so those published rows cannot be reproduced from this repository. The declaration
says that in a field rather than leaving it as a silence, and `--verify-coverage` and the suite
both treat a stated command with no evidence behind it as an error.

One declaration, `sol-azy`, is deliberately **off the clock**: it is measured, it has a run log and
a two-run determinism check, and putting it on the clock is a decision somebody should take rather
than a side effect of a refactor. There is also a trap to handle first, recorded in its
declaration: `run_all.previous()` takes the lexicographically last file in `runs/`, so any file
sorting after `runs/<today>.json` makes the next scheduled run report every existing scanner as
having disappeared.

---

## Related

- [`AGENTS.md`](../AGENTS.md) is the procedure this framework is meant to make cheap, not replace.
  Read it first; nothing here removes a step from it.
- [`docs/COVERAGE.md`](COVERAGE.md) is the derived matrix of which measurement can show what it
  analysed.
- [`docs/PROTOCOL.md`](PROTOCOL.md) carries the pre-registration rule and the right of reply.
