# Candidate triage, 2026-08-31

`corpus_ghsa.py` scanned **1,200 Rust advisories** and proposed **10 Solana-related**, 5 with a
direct fix commit. This is the human read that the tool refuses to do for itself. Nothing enters
the corpus without appearing here first.

| Advisory | Verdict | Why |
|---|---|---|
| GHSA-429q-fhh4-r6hj Anchor `InterfaceAccount` | **already in corpus** | `anchor-interface-account` |
| GHSA-9v25-r5q2-2p6w Candy Machine | **already in corpus** | `metaplex-candy-machine` |
| GHSA-8r76-fr72-j32w Bubblegum | **already in corpus** | `metaplex-bubblegum-creator` |
| GHSA-c6rc-8jpp-2fgc Anchor `Program<System>` not validated | **ACCEPT, pending build** | on-chain framework, a validation class we already measure. Fix commit needs one hop through PR #3837 |
| GHSA-h6xm-c6r4-vmwf `spl-token-swap` u8 casting | **ACCEPT, pending build** | on-chain program, arithmetic soundness. Needs the fix commit resolved |
| GHSA-725g-w329-g7qr kora-lib transfer fee | **REJECT: out of scope** | see below |
| GHSA-x442-m7cc-hr92 kora-lib fee payer policy | **REJECT: out of scope** | same |
| GHSA-9qmm-4mfr-r3wj `solana_rbpf` incorrect calculation | **REJECT: out of scope** | the VM, not a program running on it |
| GHSA-ffx3-8qvm-pq3j `solana_rbpf` overflow | **REJECT: out of scope** | same |
| GHSA-xwqr-xmgg-j69q `solana_rbpf` overflow | **REJECT: out of scope** | same |

## Why kora-lib is rejected, though it is a real vulnerability with a real fix

Its fix commit [`8cbd8217`](https://github.com/solana-foundation/kora/commit/8cbd8217ee505e6b37c63ef835ff095cfa8ab318)
is genuine: three non-test `.rs` files, +104/-5 in `token/token.rs`, and the message says "fix
program_id checks", which is a class this benchmark scores.

But **kora is a relayer and paymaster, not an on-chain program.** Its crates are ordinary server
Rust. Every scanner in this benchmark is built to analyse Anchor and native Solana *programs*, and
scoring them against a server library would produce misses that say nothing about the thing they
claim to do. That is the same error as scoring a tool zero for a case our own harness could not run.

Recorded rather than dropped, because "we found it and chose not to use it" and "we never found it"
should never look the same from outside.

## Why the `solana_rbpf` advisories are rejected

`solana_rbpf` is the virtual machine that *executes* programs. A bug there is a validator bug, not a
contract bug. Same reasoning, different layer.

## What this leaves

**Two new accepted candidates**, both on-chain, both needing their fix commit resolved through a
pull request before `build_corpus2.py` can pin them. That would take corpus 2 from 9 valid cases to
11 - still small, but growing by a mechanism that is not "somebody remembered a famous hack".

That mechanism is the point. Before today the corpus could only grow from memory, which is a
selection process nobody can audit and one that guarantees the bias recorded as limitation 25.
