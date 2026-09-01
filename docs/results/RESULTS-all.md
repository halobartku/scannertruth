# RESULTS: every scanner, both corpora, 2026-08-31

> **RE-MEASURED AND CLOSED, 2026-08-31.** Radar and VaultLint were re-run **per case, per
> variant, over every case, with a log per run**. Both now carry `coverage_evidence: run log`, the
> strongest form: 18 runs each, 36 in total, **36 successes, zero unavailable**.
>
> **That sentence is true and its evidence was defective, 2026-09-01 (error 32).** The runner
> decided `ok` versus `UNAVAILABLE` by asking whether radar had written an output file, and radar
> writes no output file when it finds nothing. One of the 36 was recorded as `UNAVAILABLE` in
> `raw/c2-radar-percase.log` and as `ok, findings: 0` in the log that actually scores, and nothing
> compared the two. radar's own stdout for all 18 runs is now committed at
> `raw/radar-c2-2026-08-31-stdout/`; every one reports `radar completed successfully` with a
> non-zero `Scanned N file` count, so the count stands at 36 and 36. Two checks now compare the
> two logs, and compare the run log with the tool's own account of what it did.
>
> **The conclusion held. Nothing detects anything on corpus 2** except the single X-Ray finding
> under a corrected mapping. But two details were wrong before and are worth more than the
> headline: Radar's mapped rule was said to "never fire at all" on eight of nine cases - it in fact
> fires in the right file on two of them, just not at the fix site (`unlocated`). And VaultLint's
> shape is coverage, not failure: **7 of 8 cases are `no-rule`**, a limit it states about itself.



> **THE CORPUS GREW AFTER THIS MEASUREMENT, 2026-09-01.** Eight cases were added to corpus 2 later
> the same day, taking it to **17 valid cases and 16 built**. **Nothing on this page has been
> re-measured against them.** Every "real vulnerabilities" column below is out of the **eight cases
> measured on 2026-09-01**, and the eight new ones are not counted as zeros: `run_all.py` reports
> them as `not-run` or `unknown` and every corpus-2 row it produces now reads `partial` rather than
> `measured` until the tools are run again. The new cases are listed in `corpus2/manifest.json`
> with `"measured": false`, and in [`../CLASS-BALANCE.md`](../CLASS-BALANCE.md).

Six scanners and two calibration controls, measured with one protocol on the same day.

## The table

| Scanner | Teaching corpus, real recall | Real vulnerabilities, detected | Notes |
|---|---|---|---|
| `control-noisy` (flags every line) | **0 / 11** | — | 81,928 findings, 11 / 11 nominal, zero real |
| `control-null` (reports nothing) | **0 / 11** | — | the floor |
| **`radar`** (Auditware) | **11 / 11** | **0 / 8**, and **0 / 16** on re-run | re-run 2026-09-01, run log 34/34; 2 `unlocated`, 7 missed, 7 no-rule, scoreable denominator 9 |
| `sol-audit` v2 (ours) | 4 / 11 | *retired 2026-09-01* (was **0 / 8**) | ours, free and open forever, not a product. The corpus-2 cell is RETIRED, not deleted: it never had a run log on either corpus, 96 of its 426 findings name files the corpus rebuild removed, and v3 supersedes it with a log on both. The teaching-corpus 4 / 11 stands; it measures a different tool from v3 and is not superseded by it. |
| `sol-audit` v3 (ours, 2026-09-01) | 5 / 11 | **0 / 16** | re-run per case, run log 35/35 and 34/34, zero unavailable; scored with the mapping pre-registered for v2, which does not claim v3's fourteen new rules, so this understates it. `unmapped_check`: 0 candidates |
| `vaultlint` 0.1.1 | 2 / 11 | **0 / 17 registered, 1 / 17 corrected** | re-run per case 2026-09-01, run log 36/36, **zero unavailable**, the only corpus-2 row with complete coverage; 15 of 17 `no-rule`, scoreable denominator 2. `unmapped_check`: **1 candidate**, VL002 on `anchor-account-reload-owner`, differential and at the fix site. The mapping points VL002 at `owner-checks`, this case is `owner-check-after-cpi`, so it scores zero as registered. Mapping left unedited; provisional until its authors reply. |
| **`x-ray`** (sec3, formerly Soteria) | 2 / 11 | **0 / 8 registered, 1 / 8 corrected** | the one real detection anything has made; see below |
| `solsec` 0.2.1 | 0 / 11 | **0 / 16** | re-run per case 2026-09-01, run log 34/34, **zero unavailable**; 14 no-rule, scoreable denominator 2 |
| `semgrep` 1.174, own registry | 0 | 0 | not a miss: `p/rust` has 11 rules and none concern Solana |
| `semgrep` + SOL-0XX pack | 3 / 11 nominal, **0 / 11** real | **0 / 16** | new 2026-09-01, mapping pre-registered before the run, run log 35/35 and 34/34; 3 `unlocated`, all of them "fires at the fix site but also on the fix" |

## What this says

**Seven scanners and two controls. The denominator below is eight because that is what was measured
on 2026-08-31; the re-runs later that week cover sixteen and seventeen, and the conclusion did not
move. One detection between them, and it took a correction to
our own mapping to see it.**

An earlier version of this page said no scanner detected anything. That was wrong, and the error
was ours, not the tools'. Details in the section below. The corrected statement is narrower and
still stark: the teaching corpus and the real one disagree almost completely. A tool with a perfect
score on the corpus everybody uses detects nothing on the bugs that actually cost money, and the
single real detection in the whole exercise came from a different tool, under a rule we had mapped
to the wrong class.

Measured on 2026-08-31 against the eight built cases of corpus 2, each a production vulnerability
with a public fix commit, under a protocol that requires the detection to land where the fix
actually changed something.

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

## Why the teaching-corpus column matters less than it looks

`coral-xyz/sealevel-attacks` was last modified **2022-07-16**. Two of the tools measured here cite
its class pages directly as the reference for their own rules, and one vendor was closing gaps
against it on the day of measurement. **Every number in the left-hand column should be read as a
measure of familiarity with a four-year-old public teaching set**, ours included.

The right-hand column is the one that required building something: real vulnerabilities, taken from
maintainers' own fix commits, that no scanner author had seen as a test set.

## The controls are what make this readable

`control-noisy` flags every non-empty line: **81,928 findings, 11/11 nominal recall, 0/11 real.** Any
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
but not that it is invalid. See [`docs/results/RESULTS-realcrates.md`](../../docs/results/RESULTS-realcrates.md).

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
correction, which `docs/PROTOCOL.md` requires and which has not yet happened for anyone. Eight
built cases is a small corpus. The teaching corpus is public and known to be tuned against. Our own packaging
was tested on the strongest case and did not explain the result, but has not been tested on all of
them.

**The packaging objection was tested and does not explain the result.** Rebuilt as real crates,
each with the project's own `Cargo.toml` and sibling modules, Radar detects nothing across six
scoreable pairs and cannot complete at all on the three largest. Six pairs and two of six
scanners test the objection; they do not retire it, and this page said they did until
2026-09-01. The per-case file counts are in the table on that page; the 927 figure quoted here
was not checkable from this repository, because the real crates are built on demand and never
committed (error 23). [`docs/results/RESULTS-realcrates.md`](../../docs/results/RESULTS-realcrates.md).

Full list in [`docs/KNOWN-LIMITATIONS.md`](../../docs/KNOWN-LIMITATIONS.md); how it was all built, with every
mistake, in [`docs/ENGINEERING-LOG-2026-08-31.md`](../../docs/ENGINEERING-LOG-2026-08-31.md).
