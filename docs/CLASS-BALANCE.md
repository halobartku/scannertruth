# Corpus 2 class and repository balance

**This file is generated. Do not edit it.** Run `python tools/class_balance.py`, which reads `corpus2/manifest.json` and the `corpus2/` directory. `test_all.py` fails if the two disagree, because a concentration figure that nobody recomputes is how a corpus quietly stops meaning what its front page says.

## Counts

|  | n |
|---|---|
| cases listed | 18 |
| valid | 17 |
| invalid, kept in the manifest so the error stays visible | 1 |
| built | 16 |
| measured by at least one scanner | 8 |
| built but not yet measured | 8 |
| valid but not built | 1 |
| distinct classes among the valid cases | 13 |
| distinct repositories among the valid cases | 8 |

Not yet measured, and therefore not in the denominator of any published score: `anchor-account-reload-owner`, `anchor-program-system`, `solido-anker-arbitrary-cpi`, `solido-deposit-reserve-account`, `spl-stake-pool-fee-rounding`, `spl-stake-pool-mint-decimals`, `squads-recursive-execute`, `token-2022-confidential-approve-mint`.

Valid but not built, reported as `not-built` rather than skipped: `spl-token-lending-rounding`.

## By class

| class | n | cases |
|---|---|---|
| account-data-matching | 3 | `squads-account-matching`, `metaplex-token-metadata`, `token-2022-confidential-approve-mint` |
| arithmetic-rounding-drain | 2 | `spl-token-lending-rounding`, `spl-stake-pool-fee-rounding` |
| signer-authorization | 2 | `squads-signer-auth`, `metaplex-bubblegum-creator` |
| arbitrary-cpi | 1 | `solido-anker-arbitrary-cpi` |
| cpi-recursion | 1 | `squads-recursive-execute` |
| instruction-introspection | 1 | `metaplex-candy-machine` |
| mint-configuration-validation | 1 | `spl-stake-pool-mint-decimals` |
| owner-check-after-cpi | 1 | `anchor-account-reload-owner` |
| owner-checks | 1 | `solend-owner-checks` |
| pda-derived-address-validation | 1 | `solido-deposit-reserve-account` |
| program-account-validation | 1 | `anchor-program-system` |
| sysvar-address-checking | 1 | `wormhole-sysvar` |
| type-cosplay | 1 | `anchor-interface-account` |

## By repository

| repository | n |
|---|---|
| solana-labs/solana-program-library | 4 |
| Squads-Protocol/squads-mpl | 3 |
| metaplex-foundation/metaplex-program-library | 3 |
| chorusone/solido | 2 |
| coral-xyz/anchor | 2 |
| otter-sec/anchor | 1 |
| solendprotocol/solana-program-library | 1 |
| wormhole-foundation/wormhole | 1 |

## What this says about a score

The largest class is `account-data-matching` with 3 of 17 valid cases. The largest repository is `solana-labs/solana-program-library` with 4, and the three largest supply 10 of 17. A scanner implementing exactly the detection pattern behind the largest class scores better here than its general ability warrants, and a scanner tuned against the largest repository does too. Both concentrations are still real after every addition; they are smaller, not gone.

Both figures sit on top of the selection bias that cannot be fixed by adding cases at all: every case here comes from a public advisory, audit or postmortem, and those are public precisely because nobody caught them in time. The corpus is therefore systematically harder than the population of real bugs and understates every scanner measured on it.
