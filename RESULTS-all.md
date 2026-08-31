# RESULTS: every scanner, both corpora, 2026-08-31

Six scanners and two calibration controls, measured with one protocol on the same day.

## The table

| Scanner | Teaching corpus, real recall | Real vulnerabilities, detected | Notes |
|---|---|---|---|
| `control-noisy` (flags every line) | **0 / 11** | — | 931 findings, perfect nominal, zero real |
| `control-null` (reports nothing) | **0 / 11** | — | the floor |
| **`radar`** (Auditware) | **11 / 11** | **0 / 9** | detects every teaching class, none of the real ones |
| `sol-audit` v2 (ours) | 4 / 11 | **0 / 9** | ours, free and open forever, not a product |
| `vaultlint` 0.1.1 | 2 / 11 | **0 / 9** | precision claim holds; 4 findings across 35 files |
| **`x-ray`** (sec3, formerly Soteria) | 2 / 11 | **0 / 9** | AGPL, official container, parses Rust to LLVM IR |
| `solsec` 0.2.1 | 0 / 11 | **0 / 9** | 77k downloads on crates.io |
| `semgrep` 1.174 | 0 | 0 | not a miss: `p/rust` has 11 rules and none concern Solana |

## What this says

**Six scanners. On real vulnerabilities, not one of them detected anything.**

Yesterday's version of this finding was one tool failing one case and could be waved away as an
outlier or a packaging artefact. It is now the entire toolchain that a Solana developer could
plausibly reach for, measured against ten production vulnerabilities with public fix commits, under
a protocol that requires the detection to land where the fix actually changed something.

The teaching corpus and the real one disagree completely. A tool with a perfect score on the corpus
everybody uses detects nothing on the bugs that actually cost money.

## The controls are what make this readable

`control-noisy` flags every non-empty line: **931 findings, 11/11 nominal recall, 0/11 real.** Any
metric built on counting findings ranks it first. This one ranks it last. So no score in the table
above was bought with volume, and a zero in the right-hand column is a real zero.

## What each tool is actually doing

**Radar** has excellent class detectors and noisy generic rules: 11/11 on the teaching corpus, and
46% of its findings there land on already-fixed code. Its own README uses that corpus as its usage
example, and its maintainer merged four pull requests titled "Close the last corpus gaps" on the
day we measured it. The 11/11 is in-sample and we say so.

**VaultLint** advertises precision and the measurement supports it: everything it detected, it
detected correctly. It produced four findings across 35 files, against Radar's 52. Different
strategy, not a worse tool.

**X-Ray** is the most substantial engineering of the group, compiling Rust to LLVM IR rather than
matching text, and it scores 2/11. Depth of analysis did not translate into recall here.

**semgrep** is not a failure, it is an absence: the world's most widely used generic static analyser
has eleven Rust rules and no Solana coverage at all. Worth knowing before anyone relies on it.

## Tools we could not run, recorded rather than omitted

| Tool | Why not |
|---|---|
| `solana-lints` (Trail of Bits) | dylint toolchain would not build in our container within the session |
| `anchor-sentinel` | requires `anchor build` and a generated IDL; the corpora are bare crates |
| `sol-azy` (FuzzingLabs) | ships no default rule set, so it detects nothing out of the box |
| `L3X` | requires a paid OpenAI key; not deterministic static analysis |
| `eloizer` | lower priority, not attempted |
| `cargo-audit`, `cargo-deny` | audit dependencies, not contract logic |

"Could not run" is kept separate from "found nothing" throughout. Conflating them is one of the
main ways a benchmark misleads.

## Limits

Every result here is provisional until each tool's authors have been offered their mapping for
correction, which `PROTOCOL.md` requires and which has not yet happened for anyone. Ten real cases
is a small corpus. The teaching corpus is public and known to be tuned against. Our own packaging
was tested on the strongest case and did not explain the result, but has not been tested on all of
them.

Full list in [`KNOWN-LIMITATIONS.md`](KNOWN-LIMITATIONS.md); how it was all built, with every
mistake, in [`ENGINEERING-LOG-2026-08-31.md`](ENGINEERING-LOG-2026-08-31.md).
