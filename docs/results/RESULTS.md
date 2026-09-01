# RESULTS

Scanner under test: **`sol-audit`**, our own static security scanner for Solana / Anchor programs.
Corpus: `coral-xyz/sealevel-attacks`, 11 vulnerability classes.
Scoring: see `docs/PROTOCOL.md`. Raw output: `benchmark-raw.json`. Re-derive from the repository root with `python tools/verify.py`.

## Headline

| Metric | Result |
|---|---|
| **Nominal recall** | **2 / 11** |
| **Real recall** | **0 / 11** |

Both apparent detections fired identically on the fixed variant of the same program. The scanner
was matching code shapes, not detecting vulnerabilities.

## Per class

`on` is the number of findings whose rule id is in the mapping for that class.

| Class | insecure (on) | secure (on) | recommended (on) | Nominal | Real |
|---|---|---|---|---|---|
| 0-signer-authorization | 0 | 0 | 0 | no | no |
| 1-account-data-matching | 0 | 0 | 0 | no | no |
| 2-owner-checks | 0 | 0 | 0 | no | no |
| 3-type-cosplay | 0 | 0 | 0 | no | no |
| 4-initialization | 0 | 0 | 0 | no | no |
| 5-arbitrary-cpi | **2** | **2** | 0 | yes | **no** |
| 6-duplicate-mutable-accounts | 0 | 0 | 0 | no | no |
| 7-bump-seed-canonicalization | 0 | 0 | 0 | no | no |
| 8-pda-sharing | **2** | **2** | **3** | yes | **no** |
| 9-closing-accounts | 0 | 0 | 0 | no | no |
| 10-sysvar-address-checking | 0 | 0 | 0 | no | no |

## Reading the two rows that matter

**`5-arbitrary-cpi`:** two findings on the buggy program, two findings on the fixed program.
Identical. Whatever the rule is keyed on, it is present in both, so it carries no information about
whether the bug is there.

**`8-pda-sharing`:** two findings on the buggy program, two on the fixed one, and **three on the
`recommended` variant**. The scanner fired *more* on the most correct version of the program than
on the vulnerable one. This is the clearest single illustration of the failure mode this benchmark
exists to expose.

## Why this is not simply "the scanner is bad"

The scanner produced a large number of findings on real repositories, and that number had been
cited, by us, as evidence that it worked. It was not evidence of anything. Finding counts can be
reported without any ground truth; recall against a labelled corpus cannot.

Three of the eleven classes have no corresponding rule in this scanner at all
(`6-duplicate-mutable-accounts`, `9-closing-accounts`, `10-sysvar-address-checking`). They are
recorded as structural gaps and counted as misses, because a scanner that cannot detect a bug does
not detect it.

## Provenance

Result produced 2026-08. Recomputed from the raw file on 2026-08-31 as part of preparing this
repository; the headline reproduced exactly.

`verify.py` reads `benchmark-raw.json` and recomputes both numbers. If it disagrees with this page,
this page is wrong.
