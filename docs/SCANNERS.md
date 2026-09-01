# Scanner registry

Every Solana security scanner we know of, what shape it is, what it needs, and what we measured.

## Why this points instead of instructing

**There are no install commands here, deliberately.**

Our own procedure begins: *find the tool's own repository and use the install path it documents*.
That rule exists because `cargo install radar` would have installed an unrelated 2021 crate by a
different author, and we would have measured a random package and called it a competitor. Writing
our own install steps would invite you to trust us over the vendor, which is the same failure one
step removed.

Install instructions are also the fastest-rotting thing in any repository. A stale command here
costs you an hour and costs us the only thing we have.

So: canonical link, tool shape, prerequisites, whether it is alive, and our measured result. For
installing it, go to their documentation.

---

## The tools

**Scanners measured 2026-08-31**, which is the date on every artefact in `raw/`. The header here
read 2026-09-01 until then, which is the date of the market survey below, not of any measurement.
Two different questions were asked on two different days and the page gave one date for both.

**Market survey (the popularity figures and the "alive?" column) checked 2026-09-01.** Those are
**weak signals** and are marked as such; they say something about attention, not about quality, and
unlike the measurements they have no artefact in this repository.

| Tool | Where it lives | Shape | Needs | Alive? |
|---|---|---|---|---|
| **Radar** | `github.com/Auditware/radar` | orchestrates its own containers, has a CI gating flag | Docker | **yes**, commits on the day we measured |
| **X-Ray** | `github.com/sec3-product/x-ray` | official container, compiles Rust to LLVM IR | Docker | quiet since March 2026 |
| **solana-lints** | Trail of Bits, `crytic/solana-lints` | dylint toolchain | Rust nightly + dylint | quiet since February 2026 |
| **VaultLint** | crates.io `vaultlint` | plain binary, `scan` subcommand | Rust, or a container to build it in | new, released July 2026 |
| **solsec** | crates.io `solsec` | plain binary | Rust | last release June 2025 |
| **semgrep** | `semgrep.dev` | generic multi-language scanner | Docker or pip | very much alive; **no Solana rules in its own registry**, but the MIT [SOL-0XX pack](https://github.com/Copenhagen0x/solana-security-standard) is 30 Solana rules loaded with one `--config <raw url>`, measured 2026-09-01 |
| **L3X** | model-backed | AI auditor | **paid OpenAI key** | see the note on AI tools below |
| **sol-audit** | `github.com/halobartku/sol-audit` | ours, plain Python | Python 3 | free and open forever, not a product |

### Weak popularity signals, for context only

Radar 151 stars. X-Ray 56. solana-lints 48. solsec 77,684 lifetime crate downloads but **56
recent**, which is the difference between a tool that was used and a tool that is used. VaultLint
**52 downloads in its entire history**.

**Read that table twice.** One tool in this category is actively developed. Two have been silent for
half a year. One is effectively abandoned despite a large historical download count. That is not a
mature market; it is missing infrastructure.

---

## What we measured

Full tables in [`docs/results/RESULTS-all.md`](../docs/results/RESULTS-all.md). The short version, where **real recall** means the
mapped rule fired on the vulnerable program **and stayed silent on the same program fixed**:

| Tool | Teaching corpus (2022, public) | Real vulnerabilities |
|---|---|---|
| Radar | **11 / 11** | 0 / 8 |
| sol-audit (ours) | 4 / 11 | 0 / 8 |
| VaultLint | 2 / 11 | 0 / 8, of which 7 are `no-rule` |
| X-Ray | 2 / 11 | 0 / 8 registered, **1 / 8** corrected |
| solsec | 0 / 11 | 0 / 6, 3 unavailable |
| semgrep, own registry | no Solana rules in the registry | - |
| semgrep + SOL-0XX pack (MIT, 30 rules) | 3 / 11 nominal, 0 / 11 real | 0 / 16 |

Every teaching-corpus figure is **in-sample**: that corpus is public, four years old, and at least
two of these tools cite it in their own rule tables. Every third-party figure is **provisional**
until its authors use their [right of reply](../docs/PROTOCOL.md).

Our mapping of each tool's rules is in [`mappings/`](../mappings/), one file per tool, each recording
how it was derived.

---

## A note on AI auditors, because the category is about to flood

L3X sits in our could-not-run table because it needs a paid API key. It will not be the last.

**A conventional scanner is deterministic**: same code, same answer, so one measurement holds. **An
AI auditor is not.** The same code can produce a different answer tomorrow after a model or prompt
change. Measuring one once tells you almost nothing, and measuring one once is what everyone
currently does.

Treat any "our AI auditor found N issues" claim as unmeasured until someone reports **spread across
repeated runs**. Building that is [milestone 3](../docs/ROADMAP.md).

---

## Tools we tried and could not run, kept separate from tools that found nothing

Conflating those two is one of the main ways a benchmark misleads, so they get their own table.

| Tool | Why not |
|---|---|
| solana-lints | dylint toolchain would not build in our container within the session |
| anchor-sentinel | needs `anchor build` and a generated IDL; our corpora are bare crates |
| sol-azy | ships no default rule set, so it detects nothing out of the box |
| L3X | requires a paid API key; not deterministic static analysis |
| cargo-audit, cargo-deny | audit dependencies, not contract logic. Different job |

---

## Missing one?

Open an issue with the tool's **own** repository link. If it runs in a container and produces
machine-readable output, adding it is mostly writing a mapping and a run loop. The procedure is
[`AGENTS.md`](../AGENTS.md) for an agent, [`docs/WALKTHROUGH.md`](../docs/WALKTHROUGH.md) for a person, and we would
rather measure your tool than guess about it.
