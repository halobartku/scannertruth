# `raw/`: what the names mean, and why the old ones do not change

Every published number in this repository recomputes from what is in this directory. It grew over
two days under at least seven naming schemes, and the schemes are documented here rather than
unified, for one reason: **existing names are frozen.** About thirty of them are pinned by literal
string in `tests/`, three in `.github/workflows/verify.yml`, every one by a results page, and the
`measurements` block of each `adapters/*.json` turns a filename into a clock row. Renaming an
artefact would break the derivation that makes it evidence. New artefacts follow the scheme in the
last section; old ones keep the name they were published under.

## The three file types a measurement leaves behind

For a measurement written to `<out>.json` by `python tools/scanner_spec.py --run ... --out <out>.json`:

| File | What it is |
|---|---|
| `<out>.json` | the findings, in the tool's own envelope (`radar`, `sol-audit`, `semgrep`, `solsec`, `vaultlint`, `xray`) |
| `<out>.json.log` | one entry per invocation: the exact command, exit code, wall time and status. This is what `run_all.py --verify-coverage` reads; a findings file cannot prove coverage |
| `<out>.run2.json`, `<out>.run2.json.log` | the second pass over the same corpus, produced by `--repeat 2` |
| `<out>.json.determinism.json` | the verdict from comparing the two passes; `not-checked` when there was only one |

Hand-driven measurements from before the framework existed left `<out>.json` and, where a person
remembered, a `.log` beside it. Which rows have which evidence is derived into
[`../docs/COVERAGE.md`](../docs/COVERAGE.md).

## Prefixes

| Prefix | Meaning |
|---|---|
| `c1-` | the teaching corpus, `coral-xyz/sealevel-attacks` at the pinned commit |
| `c2-` | corpus 2, the real vulnerabilities under `corpus2/` |
| `c2ext-` | corpus 2 after it was extended from ten to eighteen manifest cases on 2026-09-01, scored under the addendum mapping `mappings/sol-azy-c2ext.json` that was registered for the new cases |
| `c2clean-` | asserted "corpus 2, contamination-cleaned". The Radar file with this prefix was not that and was renamed `whreal-radar.json` (see its README); the two that remain, `c2clean-sol-audit.json` and `c2clean-vaultlint.json`, are 2026-08-31 runs whose paths point at a `corpus2clean/` checkout, and neither is on the clock |
| `rc-` | the real crates: whole projects built by `build_corpus2.py --crates` rather than extracted files. `rc-<tool>.json` is the run, `rc-score-<tool>.json` the `rc_score.py` output, `rc-artefacts-<tool>-<date>.tar.gz` the per-invocation artefacts from `rc_run.py`, `rc-crates-built-<date>.json` the build inventory |
| `rc-recovered-20260831-` | recovered on 2026-09-01 from the machine the 2026-08-31 run happened on, **not re-run**; the only name without hyphens in the date, kept because it is cited |
| `whreal-` | the Wormhole program as its real crate under `/tmp/whreal/`, the first out-of-sample case |
| `model-` | a model-backed auditor, see the directory scheme below |
| `radar-full`, `vaultlint`, `sol-audit`, `semgrep-c1`, `benchmark-raw`, `xray-c1-raw`, `solsec-c1-raw` | first-day names from before the corpus prefix existed. They are teaching-corpus runs and the clock reads them by the names in `adapters/*.json` |

## Suffixes inside a name

| Suffix | Meaning |
|---|---|
| `-percase` | one invocation per case per variant, as opposed to one invocation over the whole corpus. The `solsec` rows read from these; the earlier whole-corpus files stay beside them |
| `-complete` | the 2026-08-31 re-run over every case then in the corpus. `c2-radar-complete.json` was produced before the corpus was rebuilt and is superseded; `c2-vaultlint-complete.json` is the file the clock scores for VaultLint on corpus 2 |
| `-current` | the file that supersedes a `-complete` one after the corpus rebuild; `c2-radar-current.json` is the Radar corpus-2 row |
| `-corrected` | scored with the corrected mapping beside the pre-registered one; both files are kept and both numbers are published (`rc-score-xray.json`, `rc-score-xray-corrected.json`) |
| `-attempt1`, `-attempt1-exitcode`, `-attempt1-percase` | a first attempt that was wrong in a way worth keeping: recorded, not replaced |
| `-2026-08-31` on a `c2-vaultlint-` file | the earlier run kept after the same name was re-used for the 2026-09-01 one |
| `.run2` | the second pass of the determinism check |

## Directories

A directory holds one artefact per invocation. Five layouts exist and none is wrong; they are the
record of who wrote them.

| Directory pattern | Written by | Layout inside |
|---|---|---|
| `<tool>-c<N>-<date>-fw/` | the framework, `tools/scanner_spec.py --run` | `<case>.<variant>[.run2]/` holding the tool's own output file and `stdout.log` |
| `radar-c2-2026-09-01-lf/` | a hand-driven per-case script, before the framework | `<case>.<variant>.json` and `<case>.<variant>.stdout.log`. The suffix was never expanded in writing; the contents are the cases added on 2026-09-01 |
| `radar-c2-2026-08-31-stdout/` | the 2026-08-31 per-case Radar run over nine cases | `<case>.<variant>.log`, radar's stdout only; the findings for that run are `c2-radar-complete.json` |
| `radar-c2-2026-09-01/`, `vaultlint-c2-2026-09-01/`, `semgrep-solana-standard-2026-09-01/`, `solsec-2026-09-01/`, `solazy-2026-09-01/`, `sol-audit-v3-2026-09-01/` | hand-driven per-case scripts on 2026-09-01; the Radar one was turned into `c2-radar-current.json` and its log by `tools/normalise_runs.py` | flat `<case>.<variant>.<ext>` files, or `c1/` and `c2/` subdirectories of them; `sol-audit-v3-2026-09-01/c1/<case>.<variant>.<profile>.{json,log,filelog}` carries the profile in the name |
| `model-<model>[-think][-or|-cc]-c<N>-<date>[-partial|-calibration]/` | `tools/model_audit.py` | `runs.jsonl`, one line per invocation. `-or` is OpenRouter, `-cc` the Claude Code CLI, no tag is a local Ollama model; `-think` is reasoning on. `-partial` and `-calibration` directories carry a `README.txt` saying why they stopped and where the full sweep is |
| `rc-recovered-20260831-radar/` | recovered, see its `README.txt` | `<case>.<variant>.json` and `.log` |
| `solana-lints-2026-09-01/`, `corpus2-compilability-2026-09-01/` | attempts that produced no measurement: the dylint toolchain that would not build, and the compilability probe | logs only |

Only some directories carry a `README.txt`; every new one must.

## One-off files

`ghsa-candidates.json` is `corpus_ghsa.py` output; `stale-findings-<date>.json` is
`stale_findings.py --write` output; `corpus2-blob-verification-<date>.json` records that every
built case matches its upstream blob (error 34); `c1-control-inventory.json` is the 9 KB line
inventory from which the teaching-corpus control is rebuilt, because the control itself is not
committed; `dylint-attempt-1.log` is the solana-lints build that failed; `sol-azy-scores-<date>.json`
holds the hand-scored corpus-1 readings for `sol-azy`.

## The scheme for anything new

    <corpus>-<tool>[-<variant>]-<date>[.runN].<ext>

`<corpus>` is `c1`, `c2` or `rc`; `<tool>` is the adapter name; `<variant>` is a profile or a
mapping reading when the tool has more than one; `<date>` is `YYYY-MM-DD`. A per-invocation
directory takes the same stem and ends in `-fw` when the framework wrote it. Every new directory
gets a `README.txt` in its first commit saying what produced it and whether it is on the clock.
Nothing already here is renamed to fit this; the tests pin the old names and the pages cite them.
