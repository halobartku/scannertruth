# RESULTS: real crates, the 2026-08-31 run

**Status: frozen.** Run on 2026-08-31: Radar and VaultLint over the nine-case build of the real
crates. Superseded by [`RESULTS-realcrates.md`](RESULTS-realcrates.md), the 2026-09-01 run of six
tools over all eighteen cases, which is where the live numbers are. Moved here verbatim from that
page on 2026-09-02; nothing below was re-measured or reworded.

---

## The 2026-08-31 run, kept as published

### Radar over the nine-case build

| Case | .rs files | vulnerable | fixed | result |
|---|---|---|---|---|
| `wormhole-sysvar` | 23 | 7 findings | 7 findings | no detection |
| `solend-owner-checks` | 33 | 9 | 9 | no detection |
| `spl-token-lending-rounding` | 33 | 8 | 8 | no detection |
| `squads-signer-auth` | 4 | 5 | 5 | no detection |
| `squads-account-matching` | 4 | 5 | 5 | no detection |
| `metaplex-candy-machine` | 34 | 12 | 12 | no detection |
| `anchor-interface-account` | 101 | 14 | **did not complete** | unavailable |
| `metaplex-token-metadata` | 145 | **did not complete** | **did not complete** | unavailable |
| `metaplex-bubblegum-creator` | 111 | **did not complete** | **did not complete** | unavailable |
| ~~`cashio-account-data`~~ | 8 | - | - | excluded, invalid pair |

**Six scoreable pairs, zero detections.** On `anchor-interface-account` the vulnerable variant
completed and the fixed one did not, which makes the pair useless for comparison even though half
of it worked.

Worth noting for the tool's authors rather than as a gotcha: when it gives up, Radar still prints
`Results written to <path>` for a file it did not write. We hit the identical bug in our own
harness the same evening, from the opposite direction, and it cost us a run.

### VaultLint on the same crates

VaultLint produced **38 findings** on the real crates against 4 on the extracted files, which was
large enough a difference to be worth scoring rather than assuming. Scored the same way:

| Case | vulnerable | fixed | result |
|---|---|---|---|
| `wormhole-sysvar` | 3 | 3 | no detection |
| `solend-owner-checks` | 10 | 10 | no detection |
| `metaplex-candy-machine` | 3 | 3 | no detection |
| `anchor-interface-account` | 2 | 2 | no detection |
| `metaplex-token-metadata` | 1 | 1 | no detection |
| 5 further cases | - | - | no findings recorded |

**Zero detections.** Every one of the 38 findings appears on the fixed program too. Only three
rules fired at all: `VL003`, `VL004`, `VL005`.

Two things are worth saying in VaultLint's favour. Its extra findings on real crates are mostly
`VL003`, a workspace-level check for `overflow-checks = true` in `[profile.release]`, which is a
manifest property that simply cannot exist in an extracted single file - so the 4-to-38 jump is
largely the tool doing more with more context, exactly as its authors would predict. And **it
produced output on `metaplex-token-metadata` and `anchor-interface-account`, the two crates where
Radar exceeded its retry budget entirely.**

**A limitation of our own run, stated because it weakens the above:** VaultLint was invoked once
over the whole corpus rather than per case, so for the five cases with no findings we **cannot
distinguish "found nothing" from "did not analyse"**. Those are reported as no findings recorded,
not as zeros, and a per-case rerun is the fix.
