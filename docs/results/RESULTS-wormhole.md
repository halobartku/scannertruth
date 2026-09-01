# RESULTS: the first out-of-sample case. Nobody caught it.

2026-08-31. One real vulnerability, taken from production code, measured with the same protocol as
everything else in this repository.

## The case

**Wormhole Solana core bridge, February 2022, roughly 320 million dollars.**

| | |
|---|---|
| Repository | `wormhole-foundation/wormhole` |
| Fix commit | [`7edbbd36`](https://github.com/wormhole-foundation/wormhole/commit/7edbbd3677ee6ca681be8722a607bc576a3912c8) |
| Vulnerable parent | `79ab522f` |
| File | `solana/bridge/program/src/api/verify_signature.rs`, 219 lines |
| Class | sysvar-address-checking |

The program read the Instructions sysvar without verifying that the account it was handed actually
was that sysvar. An attacker supplied a forged account and convinced `verify_signatures` that a
previous secp256k1 instruction had validated the guardian signatures. It had not.

The fix is two function calls:

```
-  load_current_index(&accs.instruction_acc.try_borrow_mut_data()?)
+  load_current_index_checked(&accs.instruction_acc)?

-  load_instruction_at(...)
+  load_instruction_at_checked(...)
```

The `_checked` variants verify the account address. That is the whole difference between the
vulnerable and the fixed program, which makes this an insecure/secure pair of exactly the kind the
benchmark scores.

## The result

| Scanner | Score on the teaching corpus | Detected Wormhole? | Findings on vulnerable | Findings on fixed |
|---|---|---|---|---|
| `radar` | **11 / 11 real recall** | **no** | 3 rules | **the same 3 rules, identical** |
| `vaultlint` | 2 / 11 real recall | **no** | 0 | 0 |
| `sol-audit` v2 (ours) | 4 / 11 real recall | **no** | 9 | **9, identical** |

**None of them found it. Every finding any of them produced fires identically on the vulnerable and
the fixed program**, which by this benchmark's definition means none of them detected anything at
all on this case.

Radar in particular has a rule named `Unvalidated Sysvar Account`, and on the teaching corpus that
rule detects this exact class perfectly. On the real instance of the same bug, it does not fire.

## Why this matters more than the 11/11

Yesterday the honest summary of this project was an argument: *a public corpus that vendors tune
against stops measuring whether a tool generalises.*

Today it is a measurement. The same tool, the same protocol, the same afternoon:

- teaching corpus, eleven curated classes: **11 / 11**
- one real vulnerability from production: **0 / 1**

That is the gap the second corpus exists to expose, and it is larger than we expected.

## Caveats, and they are not small

**One case is one case.** n = 1. This is a data point, not a corpus, and it must not be quoted as
"scanners do not work". It is the first out-of-sample measurement we have ever made, and its value
is that it points hard in a direction we can now go and test properly.

**The Wormhole code is raw `solana_program`, not Anchor.** Radar and VaultLint are both
Anchor-oriented. That is a real partial defence for them. It is also part of the point: production
Solana code is not always Anchor, and a scanner's coverage of the ecosystem is a property worth
measuring rather than assuming.

**The packaging objection was tested and does not hold.** After first reporting this, we
re-extracted the Wormhole program as the real crate: `solana/bridge/program` in full, at both
commits, with its own `Cargo.toml` and all 46 sibling files. Radar ran 57 templates over it. Its
`Unvalidated Sysvar Account` rule still did not fire, and every finding in `verify_signature.rs`
appeared identically in both variants. The result is not an artefact of our packaging.

**We packaged the file ourselves.** The two variants were extracted from the repository at the fix
commit and its parent, and given a minimal synthetic `Cargo.toml` so the tools would parse them.
That is not how the code exists in the real project, and it may affect analysis that depends on
crate context. Stated because someone should be able to challenge it.

**Radar initially failed outright.** With the bare file and no `Cargo.toml` it returned
`400 Bad Request` from its AST service rather than a result. We added the manifest and re-ran
rather than reporting that failure, because a tool should be given what it expects before being
judged. The first attempt is recorded here anyway.

## Reproduce

```
git clone --filter=blob:none --no-checkout https://github.com/wormhole-foundation/wormhole.git
cd wormhole
git show 7edbbd3677ee6ca681be8722a607bc576a3912c8:solana/bridge/program/src/api/verify_signature.rs > secure.rs
git show 79ab522f802ccc5ba34278d3c648fa62e06f4f1c:solana/bridge/program/src/api/verify_signature.rs > insecure.rs
diff insecure.rs secure.rs
```

Ten further verified candidates for this corpus, each with a fix commit that was opened and
checked, are listed in the project notes: Cashio, Solend, SPL Token Lending, Squads Protocol,
Metaplex Token Metadata, Metaplex Candy Machine, and two advisories against Anchor itself.
