# Candidate triage, 2026-08-31

`corpus_ghsa.py` scanned **1,200 Rust advisories** and proposed **10 Solana-related**, 5 with a
direct fix commit. This is the human read that the tool refuses to do for itself. Nothing enters
the corpus without appearing here first.

| Advisory | Verdict | Why |
|---|---|---|
| GHSA-429q-fhh4-r6hj Anchor `InterfaceAccount` | **already in corpus** | `anchor-interface-account` |
| GHSA-9v25-r5q2-2p6w Candy Machine | **already in corpus** | `metaplex-candy-machine` |
| GHSA-8r76-fr72-j32w Bubblegum | **already in corpus** | `metaplex-bubblegum-creator` |
| GHSA-c6rc-8jpp-2fgc Anchor `Program<System>` not validated | **BUILT 2026-09-01** | `anchor-program-system`, fix `3eb1fb04`. See correction 1 below: this row used to say the fix needed "one hop through PR #3837", and that was wrong |
| GHSA-h6xm-c6r4-vmwf `spl-token-swap` u8 casting | **REJECT 2026-09-01: no fix exists** | see correction 2 below. It was accepted on 2026-08-31 pending a fix commit that does not exist and is not coming |
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
pull request before `build_corpus2.py` can pin them. ~~That would take corpus 2 from 9 valid cases
to 11~~ **Wrong, corrected 2026-09-01: it took it to 10.** One of the two has no fix and never will;
see correction 2. Still small, but growing by a mechanism that is not "somebody remembered a famous
hack".

That mechanism is the point. Before today the corpus could only grow from memory, which is a
selection process nobody can audit and one that guarantees the bias recorded as limitation 25.

---

# Two corrections to this document, 2026-09-01

Both were found by a candidate hunt on 2026-09-01 and each was re-verified here against the
repositories before being applied. They are logged as errors 29 and 30 in
[`ENGINEERING-LOG-2026-09-01.md`](ENGINEERING-LOG-2026-09-01.md).

**Correction 1. PR #3837 is not the fix for GHSA-c6rc-8jpp-2fgc.** This document said the
`Program<System>` fix "needs one hop through PR #3837". Checked in a clone of `coral-xyz/anchor`:
`git log --all --grep="#3837"` returns exactly one commit, `3a799e2d`, whose subject is
`feat(account): Check Owner on Reload (#3837)`, and its first tag is `v1.0.0`. That is a different
bug, now in the corpus as `anchor-account-reload-owner`. The GHSA-c6rc fix is `3eb1fb04`,
`fix(lang): Improve Program generic key checking logic`, which carries no PR number in its subject
and whose first tag is `v1.0.2`, matching the advisory's stated patched version. Following the
wrong hop would have built the wrong pair under a CVE number.

**Correction 2. The projection "from 9 valid cases to 11" could never have happened.** One of the
two accepted candidates, GHSA-h6xm-c6r4-vmwf, has no fix. The advisory records no patched version,
and the pointer cast it reports is still present at HEAD of the repository today:
`token-swap/program/src/instruction.rs:627`, `let val: &T = unsafe { &*(&input[1] as *const u8 as
*const T) };`. Checked with `git grep` at HEAD rather than taken from the advisory text.
`spl-token-swap` was deprecated rather than patched. The honest figure from that day's triage was
10, and it is now corrected in place above.

There is a second reason it would have been rejected even if a fix appeared: the defect is Rust
type soundness in `unpack`, a client-side instruction-parsing helper, not a Solana authorisation or
accounting bug on chain. Scoring contract scanners on it produces misses that say nothing about
what they claim to do, which is the reasoning that rejected `kora-lib`.

---

# Additions and rejections, 2026-09-01

Eight cases were built on 2026-09-01. They are listed in `corpus2/manifest.json` with their fix
SHAs, their pinned file, every exclusion and, where the severity is contested, a severity note. The
class and repository balance after the additions is recomputed in
[`CLASS-BALANCE.md`](CLASS-BALANCE.md).

**All eight are marked `"measured": false`.** They are in the corpus and in no published score.

## Held for a human decision, not built

**`squads-attach-ix-program-id`**, `Squads-Protocol/squads-mpl`, fix
`aa62d18d88cf276f2b4c47101e5fe12cb6e5ef47`, parent `088bd8d0`, single parent verified, one file
(`programs/squads-mpl/src/lib.rs`), class `arbitrary-cpi`. OtterSec finding OS-SQD-SUG-01, named in
the commit message, report committed in the repository as `Squads V3 - OtterSec Audit.pdf`.

The diff is clean and was read: `if tx.authority_index == 0 && &incoming_instruction.program_id !=
ctx.program_id { return err!(MsError::InvalidAuthorityIndex); }` added to `add_instruction`, so an
instruction attached under the multisig's own governance authority can only ever target MPL itself.
It is buildable and correctly labelled as a missing check.

**Not built, because the decision is about corpus composition rather than about the code, and that
is a judgement for a human:**

1. Squads already supplies two cases and `squads-recursive-execute` makes three. A fourth would put
   four of eighteen cases in one repository, which moves the concentration in the wrong direction.
2. The impact is disputed by another auditor. Neodyme's MPL3 section says of this very finding that
   OtterSec's claim, that the multisig's lamports could be drained, is wrong, because all multisig
   accounts are owned by MPL at execution time and MPL has no close instruction. Read out of the
   PDF, not summarised.
3. The commit also deletes an unrelated `msg!("TX PDA: {:?}", ...)` debug line from
   `create_transaction` in the same file. That contamination cannot be separated and would need a
   `contamination_note`.

`squads-recursive-execute` was built and carries a `severity_note` recording the same kind of
dispute in stronger terms: its auditor graded it **Info** with "no impact, except for
inconsistency". Whether either case belongs in a corpus of *vulnerabilities* is one question, and
it should be answered once, for both.

## Rejected, with reasons

Recorded so that "we found it and chose not to use it" and "we never found it" do not look the same
from outside. Each was examined as an actual diff.

| Candidate | Verdict |
|---|---|
| `spl-token-swap` GHSA-h6xm-c6r4-vmwf | **REJECT: no fix exists**, and the defect is Rust type soundness in a client-side helper. See correction 2 |
| SPL `58221fc9` "add program id checks (#1714)" | **REJECT:** the check lands in client-side instruction constructors, not in on-chain validation, and the rest of the commit is test churn. The vulnerable variant would be a file of instruction builders with no `invoke` in it |
| mango-v4 `2ee152f7` oracle staleness | **REJECT: no single implicated file.** 17 files, 13 of them non-test Rust across seven instruction handlers plus client and liquidator crates. The disclosure implicates the design, not a file. mango-v4 remains the best unexplored seam for oracle classes: ten OtterSec PDFs sit unread at `mango-v4/audits/` |
| Anchor `e59e8751` "Scrub discriminator on close" | **REJECT: the parent is not cleanly vulnerable.** The parent already writes the closed-account sentinel; the fix only removes a condition that skipped it. A scanner would see the defence in both variants. Also `lang-v2/`, an unreleased prototype |
| SPL `e8bafb4b` invalid fee account in token-swap | **REJECT: the failure mode is to skip, not to reject.** Every call site consumes the new check as `is_ok()` or `Err(_) => 0`, so an invalid fee account waives the fee instead of failing the instruction. The bug fixed is a denial of service, not a theft |
| helium-program-library `82a0a3cb`, `e29044ec` | **REJECT: criterion 4 fails.** The commit messages are "Add missing check" and "Add missing constraint", the repository has no audit reports and no advisory exists. The label would be entirely ours |
| solido `0db0323` missing writable check | **REJECT: the author says it is not exploitable on chain.** The commit message states the method is used only by the CLI. A good example of a commit that greps as a security fix and is not one |
| SPL `23c487dd` "lending: add extra owner check" | **REJECT: no public description**, and `owner-checks` plus `account-data-matching` are already the corpus's heaviest classes. An unsourced case in an over-weighted class makes the bias worse and the evidence thinner at once. Note the tension with `anchor-account-reload-owner`, which was admitted on a pull-request title alone; that case carries a `source_strength_note` recording it |
| marginfi-v2 `adcdd92` | **REJECT: the commit message and the diff disagree.** It announces a failing test and also adds the guards that presumably make it pass, so which commit is the fix cannot be said with confidence. marginfi carries 13 audit PDFs and deserves a dedicated pass |
| SPL `d3de2025` OS-SPL-ADV-02 | **REJECT: instruction-builder signer flags, not on-chain logic.** Audit-attributed and two lines, but in a client-side constructor. Same reasoning as #1714 |
| squads-mpl `a2448c5` MPL2 | **REJECT, narrowly:** Neodyme graded it Low and wrote that the inconsistency "does not have any immediate implications". It also shares a parent with `squads-recursive-execute`, so building both would put two cases on one baseline commit in one file |

## What the hunt could not reach, said as "not searched"

Structured advisory sources for Solana Rust are exhausted: the GitHub Advisory Database returns
eight reviewed advisories for `ecosystem:rust` plus `solana` and all eight are adjudicated in the
table at the top of this file. The corpus cannot grow from GHSA alone any more.

**Not searched at all** on 2026-09-01, for want of web-search budget: Immunefi, Code4rena, Sherlock,
Cantina, rekt.news, and the auditors' own blogs. Absence of candidates from those sources here means
they were not looked at, not that they are empty. Twenty-four audit PDFs are known to be committed
in repositories already cloned and have not been read: ten OtterSec Mango v4, thirteen marginfi, one
OtterSec Squads. That is the seam to work next, and it is a better one than commit-message
archaeology.
