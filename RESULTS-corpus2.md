# RESULTS: corpus 2, real vulnerabilities. Nine cases, no detections.

2026-08-31. Nine production Solana programs, each taken from the maintainers' own fix commit and
its parent, scored with a stricter method than the teaching corpus.

## The corpus

| Case | Class | Project | Fix |
|---|---|---|---|
| `wormhole-sysvar` | sysvar-address-checking | Wormhole core bridge, ~320M USD | [`7edbbd36`](https://github.com/wormhole-foundation/wormhole/commit/7edbbd3677ee6ca681be8722a607bc576a3912c8) |
| `cashio-account-data` | account-data-matching | Cashio | [`7df65818`](https://github.com/cashioapp/cashio/commit/7df658184c2610139fa2c0058363c66b28add4c4) |
| `solend-owner-checks` | owner-checks | Solend token-lending | [`4c2d5c10`](https://github.com/solendprotocol/solana-program-library/commit/4c2d5c10e2240fd79398dbad586aa73fd9077f0f) |
| `squads-signer-auth` | signer-authorization | Squads Protocol | [`4b5c0e9c`](https://github.com/Squads-Protocol/squads-mpl/commit/4b5c0e9c7d043b27c4a89bb8ab0bbe743fef8f27) |
| `squads-account-matching` | account-data-matching | Squads Protocol | [`352673d9`](https://github.com/Squads-Protocol/squads-mpl/commit/352673d96c06d3c9450b9f3b20ed994aad74e4be) |
| `metaplex-token-metadata` | account-data-matching | Metaplex, GHSA-5233-j5mj-qxww | [`7f163a17`](https://github.com/metaplex-foundation/metaplex-program-library/commit/7f163a1777d2540af92d7cb5cf89ea0393094619) |
| `metaplex-candy-machine` | instruction-introspection | Metaplex, GHSA-9v25-r5q2-2p6w | [`e6b3aff6`](https://github.com/metaplex-foundation/metaplex-program-library/commit/e6b3aff603ac06236bf77c2ec21ead93c6836dce) |
| `metaplex-bubblegum-creator` | signer-authorization | Metaplex, GHSA-8r76-fr72-j32w | [`c18591a7`](https://github.com/metaplex-foundation/metaplex-program-library/commit/c18591a7ce9bb561940cb94df4b7c35ef9cc0f57) |
| `anchor-interface-account` | type-cosplay | Anchor itself, RUSTSEC-2026-0146 | [`26ef3696`](https://github.com/otter-sec/anchor/commit/26ef36968a62e28a1f028e7adae4806af30c747d) |

The answer key is the maintainers' own fix, written in response to a public disclosure. We do not
decide what the bug was. File paths are derived from each commit rather than typed in by hand.

## Scoring, and why it is stricter than corpus 1

A case counts as **detected** only if the rule that the scanner's own mapping says handles this
class fires **at the site the fix changed**, on the vulnerable variant, and not on the fixed one.

Two intermediate verdicts exist so that nothing is flattered or unfairly punished:

- **unlocated** — the mapped rule fires somewhere in the file, but not where the bug was
- **no-rule** — the scanner has no rule for this class at all, which is a coverage gap, not a failure

## The result

| Scanner | detected | unlocated | missed | no-rule | Teaching corpus score |
|---|---|---|---|---|---|
| `radar` | **0** | 0 | 8 | 1 | **11 / 11** |
| `vaultlint` | **0** | 0 | 1 | 8 | 2 / 11 |
| `sol-audit` v2 (ours) | **0** | 1 | 7 | 1 | 4 / 11 |

**Nothing was detected by anything.**

For Radar this is sharper than it first appears. It is not that the tool fired noisily and we
discounted it. On eight of nine cases the rule that Radar's own naming says detects that class
**never fired at all**. Its `Unvalidated Sysvar Account` rule handles that class perfectly on the
teaching corpus; on the Wormhole bug, the canonical real instance of exactly that class, it is
silent.

For VaultLint the shape is different and more honest: it mostly has **no rule for these classes**,
which is a stated coverage limit rather than a failed detection.

Our own scanner produces the only two `unlocated` verdicts in the table: on two cases a mapped rule
fires somewhere in the vulnerable file but not where the fix changed anything. Under the looser
first method those would have been counted as ordinary misses, and under a generous one they could
have been counted as detections. They are neither, and the category exists so that we cannot quietly
choose.

## Corpus 1 against corpus 2, same tools, same day

| | teaching corpus | real vulnerabilities |
|---|---|---|
| `radar` | 11 / 11 | 0 / 8 |
| `sol-audit` v2 | 4 / 11 | 0 / 9 |

That gap is the entire argument for this corpus existing, and it is larger than we expected.

## What we corrected about our own method, on the same day we published it

The first pass at corpus 2 **counted findings of any kind, anywhere in the file**, while corpus 1
counted only rules mapped to the class. Two different questions, printed in one table. It was our
error and it is recorded in [`KNOWN-LIMITATIONS.md`](KNOWN-LIMITATIONS.md).

The numbers above use the corrected method. The conclusion did not change, which is worth stating
plainly: a stricter measurement produced the same answer, so the result is not an artefact of the
sloppy one.

## What still limits this

- **Our packaging is ours.** Each variant is extracted into a minimal crate so the tools will parse
  it. Real programs are multi-crate Anchor workspaces. A tool that needs project context is
  penalised for a reason that is our fault. Radar returned `400 Bad Request` on a bare file until we
  supplied a manifest.
- ~~Pairs include files the fix touched that are unrelated to the bug~~ **FIXED.** Each case now
  pins the single file the disclosure implicates, with a written reason for every exclusion in
  `corpus2/manifest.json`. Rescoring on the cleaned corpus changed nothing for Radar or VaultLint
  and removed one spurious `unlocated` from ours.
- **Determinism is unverified.** No scanner has been run twice and compared.
- **Nine cases, one run each.** This is a small corpus and a first measurement.
- **The right of reply has not been exercised** for either third-party tool.

Full list, including code-level gaps, in [`KNOWN-LIMITATIONS.md`](KNOWN-LIMITATIONS.md).

## Reproduce

```
python build_corpus2.py --manifest corpus2/manifest.json --out corpus2
python score2.py --demo
python score2.py --scanner radar --kind radar --findings c2-radar.json
python score2.py --scanner vaultlint --kind vaultlint --findings c2-vaultlint.json
```
