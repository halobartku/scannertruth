# Index: where everything is, and who calls it

A map for a person or an agent arriving cold. Every table here is hand-kept and every claim in it
is checkable in one command from the repository root; where a test recomputes the same fact, the
test is named so a stale row here fails loudly rather than misleading quietly.

## Two reading orders, and the one sentence they must agree on

**A person:** [`../README.md`](../README.md), then [`GETTING-STARTED.md`](GETTING-STARTED.md), then
[`results/RESULTS-all.md`](results/RESULTS-all.md) for the table, then [`PROTOCOL.md`](PROTOCOL.md)
for why a rule that also fires on the fixed code has detected nothing.

**An agent:** [`../AGENTS.md`](../AGENTS.md), then
[`../skills/measure-a-scanner/SKILL.md`](../skills/measure-a-scanner/SKILL.md), then
[`ADAPTERS.md`](ADAPTERS.md) for the declaration a scanner is measured through.

**The state of the coverage gate, which both orders must state the same way:**
`python tools/run_all.py --verify-coverage` **passes**. It went green on 2026-09-01: every live
measurement on the clock has a per-run log and no case on either corpus is unresolved. It was red
on the morning of 2026-09-01 and the day before, and any live document that still says it is red
is wrong, not this line. The derived matrix is [`COVERAGE.md`](COVERAGE.md).

## Every script in `tools/`

Commands are written from the repository root. "Who calls it" lists the CI step in
`.github/workflows/verify.yml`, the module in `tests/` that exercises it, and the live documents
that name it; "nothing" means no CI step, no test and no live document does.

| Script | Job | Command from the root | Who calls it |
|---|---|---|---|
| `controls.py` | one normalised `Finding` shape and the two control adapters, `null` and `noisy`; `tools/adapters.py` until 2026-09-02, renamed so it stops sharing a name with the `adapters/` declarations | `python tools/controls.py --demo` | `tests/data_integrity.py`, `tests/adapter_framework.py`; README, KNOWN-LIMITATIONS, `results/RESULTS-scanners.md`. No tool imports it; `adapters/*.json` are the declarations the framework reads |
| `build_corpus2.py` | build corpus 2 from each fix commit and its parent; `--crates` builds the real crates | `python tools/build_corpus2.py --manifest corpus2/manifest.json --out corpus2` | CI `--demo`; `tests/unmapped.py`; README, CANDIDATES-TRIAGE, KNOWN-LIMITATIONS, `results/RESULTS-corpus2.md`, `results/RESULTS-realcrates.md` |
| `class_balance.py` | recompute class and repository concentration from the manifest into `CLASS-BALANCE.md` | `python tools/class_balance.py` (`--check` exits 1 if stale) | `tests/corpus_growth.py`; `CLASS-BALANCE.md` |
| `control_c1.py` | rebuild and score the calibration controls on the teaching corpus from the committed line inventory | `python tools/control_c1.py` | `tests/published_numbers.py`, `tests/corpus_growth.py`, `tests/documented_commands.py`; no live document names it |
| `control_c2.py` | run the calibration controls over corpus 2; both must score zero real recall | `python tools/control_c2.py` | CI step; `tests/published_numbers.py`, `tests/score2_verdicts.py`, `tests/corpus_growth.py`; README, AGENTS, GETTING-STARTED, WALKTHROUGH, the measure-a-scanner skill |
| `clock_corpus1.py` | the clock's corpus-1 scoring (`measure`, `extract`, `load_mapping`) and the source tables `SOURCES`, `SOURCES_CORPUS2`, `MAPPING_ALIAS`, `ROW_NOTES`; split out of `run_all.py` on 2026-09-02 | not run directly; `run_all.py` re-exports every name | every consumer of `run_all.<name>`; `tools/coverage_matrix.py`, `tools/stale_findings.py` through `run_all` |
| `clock_corpus2.py` | the clock's corpus-2 scoring (`measure_corpus2`); split out of `run_all.py` on 2026-09-02 | not run directly; `run_all.py` re-exports it | the same, through `run_all` |
| `corpus_ghsa.py` | propose corpus-2 candidates from GitHub Security Advisories and RustSec | `python tools/corpus_ghsa.py` | CI `--demo`; `tests/candidate_triage.py`; README, CANDIDATES-TRIAGE, ROADMAP, the add-a-corpus-case skill |
| `corpus_hashes.py` | pin every corpus-2 file to a content hash and to the upstream blob it came from | `python tools/corpus_hashes.py --write` | `tests/corpus_pinned.py`; no live document names it |
| `corpus_radar.py` | propose candidate cases from public sources, never add them; keeps state in `.corpus_seen.json` at the root | `python tools/corpus_radar.py --out corpus-candidates.md` | KNOWN-LIMITATIONS only; no test, no CI step |
| `coverage_matrix.py` | derive which measurement can show what it analysed, from `raw/`, into `COVERAGE.md` | `python tools/coverage_matrix.py --write` | `tests/corpus_growth.py`; `COVERAGE.md` |
| `emit_sol_audit.py` | run our own scanner over a directory and write findings in the envelope the clock reads; needs `sol-audit` on `PYTHONPATH` | `python tools/emit_sol_audit.py <sol-audit checkout> <corpus dir> raw/<out>.json` | `tests/no_dependencies.py` (listed as needing `scanner`); README, ADAPTERS |
| `holdout.py` | commit to a holdout case by hash before the round it scores | `python tools/holdout.py verify --spec spec.json --against COMMITMENTS-HOLDOUT.json` | `tests/holdout_commitments.py`; README, PROTOCOL, ROADMAP, the add-a-corpus-case skill |
| `model_audit.py` | measure a model-backed auditor the way a scanner is measured: one JSON line per invocation, three runs per variant | `python tools/model_audit.py --model <name> --corpus 2 --runs 3` | AGENTS, `results/RESULTS-models.md`; imported by the suite, no direct test |
| `normalise_runs.py` | turn a directory of per-run Radar or VaultLint artefacts into the findings file and run log the clock reads | `python tools/normalise_runs.py --kind radar --runs <dir> --out raw/<out>.json` | nothing. Named only in the 2026-09-01 engineering log; superseded for new work by `scanner_spec.py --run` |
| `preregistration_check.py` | a mapping's commit must touch nothing outside `mappings/` | `python tools/preregistration_check.py` | CI step and CI `--demo`; `tests/coverage_bookkeeping.py`; README, AGENTS, ADAPTERS, PROTOCOL, ROADMAP, WALKTHROUGH, the measure-a-scanner skill |
| `rb.py` | the first-day scorer for `sol-audit` against `sealevel-attacks`; needs `scanner` on `PYTHONPATH` and defaults to `/tmp` | `python tools/rb.py` | `tests/coverage_bookkeeping.py`, `tests/documented_commands.py`; README, PROTOCOL |
| `rc_compare.py` | the packaging objection as a comparison: extracted file versus real crate, verdict by verdict | `python tools/rc_compare.py --all` | `tests/real_crate_run.py`; KNOWN-LIMITATIONS, `results/RESULTS-realcrates.md` |
| `rc_run.py` | run a scanner over the real crates, one invocation per case per variant, with a log line each | `python tools/rc_run.py --tool semgrep --crates <dir> --out <dir>`; sol-audit also needs `--tool-dir <checkout>` | `tests/real_crate_run.py`; `results/RESULTS-realcrates.md`. `--out` is required; `--rules` defaults to the committed ruleset copy under `raw/` |
| `rc_score.py` | score a real-crate run with the semantics of `score2.py` | `python tools/rc_score.py --scanner <name> --kind <kind> --findings raw/rc-<name>.json --log raw/rc-<name>.json.log` | `tests/real_crate_run.py`; KNOWN-LIMITATIONS, `results/RESULTS-realcrates.md` |
| `run_all.py` | the clock: score every row on both corpora, run the coverage gate, append a dated row to `runs/` | `python tools/run_all.py --verify-coverage` (read-only); `python tools/run_all.py` appends a row | CI job `coverage`; nine test modules including `tests/published_numbers.py` and `tests/coverage_bookkeeping.py`; README, AGENTS, ADAPTERS, ROADMAP, WALKTHROUGH, all three skills |
| `scanner_spec.py` and `spec/` | the adapter framework: validate a declaration, run it per case, classify zero versus outage, log, check determinism | `python tools/scanner_spec.py --run <tool> --corpus corpus2 --out raw/c2-<tool>.json --repeat 2` | `tests/adapter_framework.py`, `tests/documented_commands.py`; README, AGENTS, ADAPTERS, ROADMAP, WALKTHROUGH, two skills. `scanner_spec.py` is a facade; the code is in `spec/` |
| `score.py` | the teaching-corpus scorer: nominal and real recall from a findings list and a mapping | `python tools/score.py mappings/<tool>.json raw/<findings>.json` | CI `--demo`; fourteen test modules; README, AGENTS, ROADMAP, `results/RESULTS-realcrates.md`, `results/RESULTS-scanners.md`, the measure-a-scanner skill |
| `score2.py` | the strict corpus-2 scorer: mapped rules only, located at the fix site, silent on the fix | `python tools/score2.py --scanner <name> --kind <kind> --findings raw/c2-<name>.json` | CI `--demo`; `tests/score2_verdicts.py`, `tests/changed_lines.py`, `tests/unmapped.py`, `tests/corpus_growth.py`; README, AGENTS, ADAPTERS, ROADMAP, WALKTHROUGH, `results/RESULTS-all.md`, `results/RESULTS-corpus2.md`, two skills |
| `shiftaware.py` | compare findings across a fix without being fooled by line shift; defaults to `/tmp` | `python tools/shiftaware.py` | `tests/shiftaware.py`, `tests/no_dependencies.py`; README, AGENTS, ROADMAP, `results/RESULTS-realcrates.md`, the measure-a-scanner skill |
| `stale_findings.py` | per findings file, how many findings name a corpus file that no longer exists | `python tools/stale_findings.py` | `tests/corpus_growth.py`; no live document names it |
| `unmapped_check.py` | a real detection hiding under a rule the mapping did not claim for that class | `python tools/unmapped_check.py --findings raw/c2-<name>.json --kind <kind>` | CI step, three invocations plus `--demo`; `tests/unmapped.py`, `tests/score2_verdicts.py`; README, AGENTS, ADAPTERS, ROADMAP, WALKTHROUGH, `results/RESULTS-corpus2.md`, the measure-a-scanner skill |
| `verify.py` | re-derive the run-1 headline in `results/RESULTS.md` from `raw/benchmark-raw.json`; that page only | `python tools/verify.py` | CI step; `tests/ci_honesty.py`, `tests/documented_commands.py`; README, AGENTS, GETTING-STARTED, PROTOCOL, `results/RESULTS.md` |

## Generated files, and the test that recomputes each

| File | Generated by | Recomputed by |
|---|---|---|
| `COVERAGE.md` | `python tools/coverage_matrix.py --write` | `test_the_coverage_matrix_is_derived_from_what_is_in_raw` in `tests/corpus_growth.py` |
| `CLASS-BALANCE.md` | `python tools/class_balance.py` | `test_class_balance_document_is_derived_from_the_manifest` in `tests/corpus_growth.py` |
| `../runs/<date>.json` | `python tools/run_all.py` | `test_published_corpus1_numbers_still_reproduce` in `tests/published_numbers.py` checks the numbers; the history order is checked in `tests/data_integrity.py` |
| `../raw/<out>.determinism.json` | `python tools/scanner_spec.py --run ... --repeat 2` | `test_a_single_pass_cannot_claim_a_determinism_verdict` in `tests/adapter_framework.py` |
| `../corpus2/manifest.json` hashes | `python tools/corpus_hashes.py --write` | `test_every_corpus_file_matches_the_hash_recorded_in_the_manifest` in `tests/corpus_pinned.py` |
| `../raw/c1-control-noisy.json`, `../raw/c2-control-*.json` | `python tools/control_c1.py`, `python tools/control_c2.py` | not committed (`.gitignore`); rebuilt in memory by `tests/published_numbers.py` and `tests/corpus_growth.py` |

## `raw/`: the naming key

The full key, including what every suffix means and which names are frozen, is
[`../raw/README.md`](../raw/README.md). The short form:

- `c1-` and `c2-` prefixes are the teaching corpus and the real-vulnerability corpus;
  `rc-` is the real crates; `model-` is a model-backed auditor.
- `<out>.json` is the findings file, `<out>.json.log` the per-invocation run log the coverage
  gate reads, `<out>.run2.json` the second pass, `<out>.json.determinism.json` the verdict.
- A directory ending `-fw` was written by the framework; the rest were written by hand and
  their layouts differ, which is why they are documented rather than renamed.
- **Existing names are frozen.** About thirty of them are pinned by literal string in `tests/`,
  three by CI and every one by a results page. New artefacts follow the scheme; old ones keep
  their names.

## Which mapping scores which row

`adapters/<tool>.json` names the mapping and the raw file in its `measurements` block, and
`python tools/scanner_spec.py --list` prints the adapter-to-row half of this table derived. The
hand copy here exists so a reader can see at a glance that the adapter and mapping names do not
line up one to one.

| Clock row | Corpus | Adapter | Mapping | Findings | Run log |
|---|---|---|---|---|---|
| `radar` | 1 | `radar.json` | `radar.json` | `raw/radar-full.json` | `raw/radar-full.json.log` |
| `radar` | 2 | `radar.json` | `radar.json` | `raw/c2-radar-current.json` | `raw/c2-radar-current.json.log` |
| `semgrep` | 1 | `semgrep.json` | `semgrep.json` | `raw/semgrep-c1.json` | `raw/semgrep-c1.json.log` |
| `semgrep-solana-standard` | 1 | `semgrep-solana-standard.json` | `semgrep-solana-standard.json` | `raw/c1-semgrep-solana-standard.json` | `raw/c1-semgrep-solana-standard.json.log` |
| `semgrep-solana-standard-wide` | 1 | same | `semgrep-solana-standard-wide.json` | same file, second pre-registered reading | same |
| `semgrep-solana-standard-c2` | 2 | same | `semgrep-solana-standard-c2.json` | `raw/c2-semgrep-solana-standard.json` | `raw/c2-semgrep-solana-standard.json.log` |
| `semgrep-solana-standard-c2-wide` | 2 | same | `semgrep-solana-standard-c2-wide.json` | same file, wide reading | same |
| `sol-audit` | 1 | `sol-audit.json` | `sol-audit.json` | `raw/sol-audit.json` | `raw/sol-audit.json.log` |
| `sol-audit` | 2 | `sol-audit.json` | `sol-audit.json` | `raw/c2-sol-audit.json` | none; **retired** 2026-09-01, reported and not counted |
| `sol-audit-v3`, `-broad`, `-all` | 1 | `sol-audit-v3.json` | `sol-audit.json` | `raw/c1-sol-audit-v3-{strict,broad,all}.json` | each `.json.log` |
| `sol-audit-v3`, `-broad`, `-all` | 2 | `sol-audit-v3.json` | `sol-audit.json` | `raw/c2-sol-audit-v3-{strict,broad,all}.json` | each `.json.log` |
| `solsec` | 1 | `solsec.json` | `solsec.json` | `raw/c1-solsec-percase.json` | `raw/c1-solsec-percase.json.log` |
| `solsec` | 2 | `solsec.json` | `solsec.json` | `raw/c2-solsec-percase.json` | `raw/c2-solsec-percase.json.log` |
| `vaultlint` | 1 | `vaultlint.json` | `vaultlint.json` | `raw/vaultlint.json` | `raw/vaultlint.json.log` |
| `vaultlint` | 2 | `vaultlint.json` | `vaultlint.json` | `raw/c2-vaultlint-complete.json` (hand-converted into the `sol-audit` envelope) | `raw/c2-vaultlint-complete.json.log` |
| `xray` | 1 | `xray.json` | `xray.json` (carries both the registered and the corrected map) | `raw/xray-c1-raw.json` | `raw/xray-c1-raw.json.log` |
| `sol-azy` | 2 | `sol-azy.json`, **off the clock** by declaration | `sol-azy-c2ext.json` | `raw/c2ext-sol-azy.json` | `raw/c2ext-sol-azy.json.log` |

Mappings with no clock row: `sol-azy.json` and `sol-azy-wide.json` are the two corpus-1 readings
for `sol-azy`, scored by hand into `raw/sol-azy-scores-2026-09-01.json`; `solana-lints.json` has
no adapter because the dylint toolchain never built (`raw/solana-lints-2026-09-01/`), so it sits
in the could-not-run table of [`SCANNERS.md`](SCANNERS.md). X-Ray's corpus-2 result is not on the
clock either: it was scored by hand from `raw/xray-c2-raw.json` and is published in
[`results/RESULTS-corpus2.md`](results/RESULTS-corpus2.md).

## The results pages, and which is current

| Page | Status | Date | Raw source | Pinned by |
|---|---|---|---|---|
| [`results/RESULTS-all.md`](results/RESULTS-all.md) | **current**: the scanner table the README points at. The title says 2026-08-31; the banner records the 2026-09-01 re-measurement | 2026-08-31, re-measured 2026-09-01 | the clock rows above, `../runs/2026-09-01.json` | `test_results_pages_do_not_contradict_the_clock_on_radar` (`tests/data_integrity.py`); the README table by `test_readme_result_table_matches_the_clock` |
| [`results/RESULTS-corpus2.md`](results/RESULTS-corpus2.md) | **current**: per-case corpus-2 verdicts | 2026-08-31, re-measured 2026-09-01 | `raw/c2-*.json` and their logs | the same clock tests, through `run_all.py` |
| [`results/RESULTS-realcrates.md`](results/RESULTS-realcrates.md) | **current**: the packaging objection tested; links the 2026-08-31 run rather than carrying it | 2026-09-01 | `raw/rc-*.json`, `raw/rc-score-*.json`, `raw/rc-recovered-*` | three tests in `tests/real_crate_run.py` parse its tables against the raw files |
| [`results/RESULTS-realcrates-2026-08-31.md`](results/RESULTS-realcrates-2026-08-31.md) | **frozen**: Radar and VaultLint over the nine-case build, moved verbatim out of `RESULTS-realcrates.md` on 2026-09-02 | 2026-08-31 | `raw/rc-recovered-20260831-radar/`, `raw/rc-recovered-20260831-vaultlint.json` | none |
| [`results/RESULTS-models.md`](results/RESULTS-models.md) | **current**: model-backed auditors; the only page that names its generator in its first five lines | 2026-09-01 | `raw/model-*/runs.jsonl`, written by `tools/model_audit.py` | no test; the page derives its own counts from the JSONL |
| [`results/RESULTS-wormhole.md`](results/RESULTS-wormhole.md) | **frozen**: the first out-of-sample case, before corpus 2 existed | 2026-08-31 | `raw/whreal-radar.json` (see its README), `raw/c2-radar.json` | none |
| [`results/RESULTS-scanners.md`](results/RESULTS-scanners.md) | **superseded** by `RESULTS-all.md`: the first multi-scanner run | 2026-08-31 | `raw/radar-full.json` | none |
| [`results/RESULTS-v2.md`](results/RESULTS-v2.md) | **frozen**: run 2, `sol-audit` v2 | 2026-08-31 | `raw/benchmark-raw-2026-08-31-v2.json` | none |
| [`results/RESULTS.md`](results/RESULTS.md) | **frozen**: run 1, `sol-audit` v1 | 2026-08 | `raw/benchmark-raw.json` | `tools/verify.py` in CI; `test_ci_step_names_do_not_overclaim` keeps the step from claiming more |

## Which numbers in the README are derived, and by which test

| Number on the front page | Test | Module |
|---|---|---|
| the error count, `N of our own errors` | `test_the_error_count_matches_the_logs` | `tests/documented_commands.py` |
| the newest engineering log is the one linked | `test_the_readme_links_the_newest_engineering_log` | `tests/documented_commands.py` |
| the check count, `N checks`, in every live document | `test_the_advertised_check_count_matches_the_suite` | `test_all.py` |
| valid, built and measured corpus-2 counts, and the `0 / N` denominator | `test_the_real_vulnerability_denominator_is_reconciled_on_the_front_page` | `tests/documented_commands.py` |
| Radar's `11 / 11` | `test_readme_result_table_matches_the_clock` | `tests/candidate_triage.py` |
| the real-crates bullet does not overclaim | `test_readme_does_not_overstate_the_real_crates_result` | `tests/claims_banned.py` |
| every directory in the layout block exists | `test_layout_block_lists_directories_that_exist` | `tests/candidate_triage.py` |
| the Python range CI proves | `test_the_platform_claims_match_what_ci_actually_runs` | `tests/documented_commands.py` |
| every script a document names exists and is written from the root | `test_every_documented_command_names_a_script_that_exists`, `test_every_documented_command_runs_from_the_repository_root` | `tests/documented_commands.py` |
| every relative link resolves | `test_every_relative_link_in_every_document_resolves` | `tests/documented_commands.py` |

Not derived, and known to be typed: the repository size quoted in the README. Treat it as
approximate.
