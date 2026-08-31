# RESULTS: every scanner, both corpora, 2026-08-31

Six scanners and two calibration controls, measured with one protocol on the same day.

## The table

| Scanner | Teaching corpus, real recall | Real vulnerabilities, detected | Notes |
|---|---|---|---|
| `control-noisy` (flags every line) | **0 / 11** | — | 931 findings, perfect nominal, zero real |
| `control-null` (reports nothing) | **0 / 11** | — | the floor |
| **`radar`** (Auditware) | **11 / 11** | **0 / 8** | detects every teaching class, none of the real ones |
| `sol-audit` v2 (ours) | 4 / 11 | **0 / 8** | ours, free and open forever, not a product |
| `vaultlint` 0.1.1 | 2 / 11 | **0 / 8** | precision claim holds; 4 findings across 35 files |
| **`x-ray`** (sec3, formerly Soteria) | 2 / 11 | **0 / 8 registered, 1 / 8 corrected** | the one real detection anything has made; see below |
| `solsec` 0.2.1 | 0 / 11 | **0 / 6**, 3 unavailable | 108 findings, every one fires on the fix too |
| `semgrep` 1.174 | 0 | 0 | not a miss: `p/rust` has 11 rules and none concern Solana |

## What this says

**Six scanners, eight real vulnerabilities, one detection between them, and it took a correction to
our own mapping to see it.**

An earlier version of this page said no scanner detected anything. That was wrong, and the error
was ours, not the tools'. Details in the section below. The corrected statement is narrower and
still stark: the teaching corpus and the real one disagree almost completely. A tool with a perfect
score on the corpus everybody uses detects nothing on the bugs that actually cost money, and the
single real detection in the whole exercise came from a different tool, under a rule we had mapped
to the wrong class.

Measured against ten production vulnerabilities with public fix commits, under a protocol that
requires the detection to land where the fix actually changed something.

## The one real detection, and our error that hid it

X-Ray's rule `1019` is named **"The account may not be properly validated and may be untrustful"**.
We mapped it to `sysvar-address-checking` alone, because sec3's own blog presents 1019 as the rule
that catches the Wormhole hack. That is an example of the rule, not its scope, and narrowing it was
our mistake.

On corpus 2 it fired once, on `squads-account-matching/insecure` at `src/lib.rs:310`. The fix
changed lines **309 and 311** — it added the check that the instruction account keys match the
submitted keys. It did not fire on the fixed variant. That is a detection of a real vulnerability,
at the fix site, differential.

Our pre-registered mapping scored it **zero**, because that case's class is `account-data-matching`
and we had not mapped 1019 there.

Both numbers are published. **0/8 as pre-registered, 1/8 under the corrected mapping.** The
pre-registered map is preserved unedited in `mappings/xray.json` beside the correction, because a
benchmark that silently repairs its mapping after seeing the scores is worth nothing. And this is
exactly the case the **right of reply** exists for: sec3 should be the ones to say what 1019 covers,
and they have not been asked yet.

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

**solsec** is the clearest illustration of why real recall is the only number that matters. It
produced **108 findings** on corpus 2 and detected nothing: every rule that fired on a vulnerable
program fired on the fixed one too, without exception. A findings count would rank it second in
this table. It also produced no output at all for three of the cases it was given, with no log
explaining why, so its denominator is **six**, and the three are recorded as unavailable rather than as zeros.

**semgrep** is not a failure, it is an absence: the world's most widely used generic static analyser
has eleven Rust rules and no Solana coverage at all. Worth knowing before anyone relies on it.

## A case we had to throw out, found by checking our own data

`cashio-account-data` is **not a valid pair and has been excluded from every denominator.**

The commit we used as the fix, `7df65818`, does not fix the vulnerability. It adds
`vipers::invariant!(false, "temporarily disabled")` to `print_cash` and `burn_cash`, disabling the
program. It is an emergency shutdown. Only three commits in the repository's history ever touched
that file, this is the last of them, and everything after the exploit is a dependency bump: Cashio
never shipped a fix, because the protocol was shut down.

So the `secure` variant is dead code. Findings vanish from it for reasons that have nothing to do
with the bug, and **any detection credited on this pair would have been spurious.** It was found
while checking why Radar appeared to produce 23 insecure-only findings on the real crate: a result
too good to accept without reading the diff. Those 23 later turned out to be an artefact of our own
line-shift-blind comparison rather than evidence of anything, which changes how the case was found
but not that it is invalid. See [`RESULTS-realcrates.md`](RESULTS-realcrates.md).

The case stays in `corpus2/manifest.json` marked `valid: false` with the reason, rather than being
deleted, and `score2.py` now refuses to score any case marked that way. A note in a manifest does
not stop the next run from counting it; a check in the scorer does.

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

**The scoring is insensitive to its one arbitrary constant.** The line tolerance that decides
whether a finding counts as landing at the fix site was swept from 0 to 25 lines across every case
and all four tools: **no verdict changes at any setting.**

**Corpus 2 is drawn entirely from public postmortems** - rekt.news, published audits, GitHub
advisories, RustSec. Those incidents are famous *because nobody caught them in time*, so the corpus
is systematically harder than the population of real bugs and understates every scanner measured on
it. It answers "do these tools catch the ones that cost money". It cannot support "these tools do
not work", and nothing here should be read as claiming that.

**The right of reply is now open, not exercised.** Four threads, one per measured tool:
[radar#32](https://github.com/Auditware/radar/issues/32),
[x-ray#51](https://github.com/sec3-product/x-ray/issues/51),
[vaultlint#1](https://github.com/vaultlint/vaultlint/issues/1),
[solsec#14](https://github.com/hasip-timurtas/solsec/issues/14). No replies yet. Until they answer,
every third-party number below is provisional, and the X-Ray correction shows that is not a
formality.

Every result here is provisional until each tool's authors have been offered their mapping for
correction, which `PROTOCOL.md` requires and which has not yet happened for anyone. Ten real cases
is a small corpus. The teaching corpus is public and known to be tuned against. Our own packaging
was tested on the strongest case and did not explain the result, but has not been tested on all of
them.

**The packaging objection is now retired.** Rebuilt as real crates (927 `.rs` files, each project's
own `Cargo.toml` and sibling modules) Radar detects nothing across six scoreable pairs, and cannot
complete at all on the three largest. [`RESULTS-realcrates.md`](RESULTS-realcrates.md).

Full list in [`KNOWN-LIMITATIONS.md`](KNOWN-LIMITATIONS.md); how it was all built, with every
mistake, in [`ENGINEERING-LOG-2026-08-31.md`](ENGINEERING-LOG-2026-08-31.md).
