# RESULTS: real crates, not extracted files. The objection tested properly.

2026-08-31. The strongest objection to the corpus-2 result was always that **we packaged it**: each
vulnerability extracted into a synthetic single-file crate, so a tool needing project context fails
for our reasons rather than its own. It was a fair objection, and evidenced, since Radar returned
`400 Bad Request` on a bare `.rs` file until a manifest was supplied.

So the corpus was rebuilt from the **real crates**: the entire directory containing the implicated
file, at the fix commit and its parent, with the project's own `Cargo.toml` and every sibling
module. 927 `.rs` files in total.

## What happened when Radar was run over them

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

**Six scoreable pairs, zero detections. The packaging objection does not explain the result.**

## Radar cannot finish on large real crates

Three of the ten cases exceeded Radar's own retry budget: `Exceeded maximum retries. Tasks did not
complete in time.` The pattern is size — everything above roughly a hundred files failed, everything
below it finished. On `anchor-interface-account` the vulnerable variant completed and the fixed one
did not, which makes the pair useless for comparison even though half of it worked.

**Those are recorded as unavailable, never as zeros.** A benchmark that scored them zero would be
reporting our own timeout as a property of the tool.

Worth noting for the tool's authors rather than as a gotcha: when it gives up, Radar still prints
`Results written to <path>` for a file it did not write. We hit the identical bug in our own harness
the same evening, from the opposite direction, and it cost us a run.

## The analysis error this produced, and how it was caught

The first comparison matched findings by `(rule, line)` between the two variants. On that basis
Radar looked like it was **detecting things**: 23 findings present only on the vulnerable Cashio
variant, 6 on Solend, one each on three more cases. Cashio's included `Missing Token Mint
Constraint`, which is the class of the Cashio bug. That reads as a spectacular result.

**It was arithmetic.** A fix that inserts lines moves every finding below it. Solend's fix adds four
lines at 1796, so a finding at 2064 in the vulnerable file sits at 2068 in the fixed one and a naive
comparison calls it "present only on the vulnerable variant". Every one of Solend's six phantoms was
below the insertion point.

`shiftaware.py` maps each finding's line through the diff hunks before comparing, so a finding is
only counted as absent when it has no counterpart at its shifted position. Under that comparison
**every apparent detection disappears, on every case, including all 23 on Cashio.**

This also corrects something we published earlier the same evening. The Cashio case is genuinely
invalid — its fix commit adds `invariant!(false, "temporarily disabled")` and switches the program
off, which is established by reading the diff and the repository history, independently of any
scanner. But the mechanism we gave for the 23 findings, that they vanished because the fixed variant
is dead code, **was wrong**. They vanished because our comparison could not do arithmetic. The
conclusion stands, the explanation did not, and asserting a cause without testing it is a mistake
this log already records once.

## Reproduce

```
python build_corpus2.py --manifest corpus2/manifest.json --out /tmp/c2crates --crates
/root/percase-radar.sh            # per case, per variant, verifies output parses before saying ok
python shiftaware.py              # shift-corrected comparison
```

Raw run log: [`realcrates-radar-run.log`](realcrates-radar-run.log).

## Limits

- **One scanner.** VaultLint produced 38 findings on the real crates against 4 on the extracted
  files, which is a large enough difference to be worth scoring properly, and it has not been.
- **Three cases could not be measured at all**, and they are the three largest. Coverage here is
  biased toward small projects.
- **Six pairs is not a corpus.** It is enough to retire one objection, not to prove a general claim.
- The right of reply has not been exercised with Auditware for this result either. The open thread
  is [Auditware/radar#32](https://github.com/Auditware/radar/issues/32).
