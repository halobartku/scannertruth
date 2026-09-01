# RESULTS, run 2 - sol-audit v2, 2026-08-31

Second dated run of the same benchmark, same corpus, same scoring rules as `docs/PROTOCOL.md`.
**Run 1 in `docs/results/RESULTS.md` is not modified.** A benchmark that rewrites its own history is worthless.

Scanner: [`sol-audit` v2](https://github.com/halobartku/sol-audit). Raw output:
`benchmark-raw-2026-08-31-v2.json`.

| Metric | v1 (run 1) | v2 (run 2) |
|---|---|---|
| Nominal recall | 2 / 11 | 6 / 11 |
| **Real recall** | **0 / 11** | **4 / 11** |

## Per class

| Class | v1 | v2 | note |
|---|---|---|---|
| 0-signer-authorization | miss | **real** | fixed |
| 1-account-data-matching | miss | nominal | **regression: now fires on the fix too** |
| 2-owner-checks | miss | **real** | fixed |
| 3-type-cosplay | miss | miss | |
| 4-initialization | miss | miss | |
| 5-arbitrary-cpi | nominal | **real** | fixed |
| 6-duplicate-mutable-accounts | miss | miss | rule added, does not fire |
| 7-bump-seed-canonicalization | miss | miss | |
| 8-pda-sharing | nominal | nominal | probably not statically decidable |
| 9-closing-accounts | miss | miss | rule added, does not fire |
| 10-sysvar-address-checking | miss | **real** | fixed |

## What changed in the scanner

Every rule was rewritten from "construct is present" to "construct is present **and** the
corresponding guard is absent". The original defect was structural: no v1 rule looked for a missing
check, and a bug and its fix contain the same constructs, so those rules could not distinguish them.

## What got worse

`1-account-data-matching` was a clean miss and is now a false positive. Recorded, not omitted.

## What this run does not establish

**This is an in-sample result.** The scanner was improved against the corpus it is scored on. The
mitigation is that no rule keys on corpus-specific text and the change is one principle applied
uniformly, but that is an argument rather than a proof. An out-of-sample corpus does not exist yet.

Do not read 4/11 as "the scanner works". Read it as "the scanner has stopped reporting detections it
cannot make". Five of eleven classes remain undetected.
