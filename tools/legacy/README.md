# tools/legacy

Scripts that produced a committed artefact and are kept so that artefact stays reproducible.
Nothing here is on the verification path and nothing new should be run with it; the adapter
framework, `tools/scanner_spec.py` with a declaration in `adapters/`, does the same job with a
per-run log the coverage gate reads.

| Script | What it produced | When | Superseded by |
|---|---|---|---|
| `normalise_runs.py` | `raw/c2-vaultlint-complete.json` and `.log` from the per-case artefacts in `raw/vaultlint-c2-2026-09-01/`, the file the clock scores for VaultLint on corpus 2 (`adapters/vaultlint.json`). Its Radar output, `raw/c2-radar-current.json`, from `raw/radar-c2-2026-09-01/` was overwritten the same day by the framework re-run in `raw/radar-c2-2026-09-01-fw/`, whose log carries the framework's fields | 2026-09-01 | `scanner_spec.py --run`, from 2026-09-01 |

Moved here on 2026-09-02. Run from the repository root:

```
python tools/legacy/normalise_runs.py --demo
```
