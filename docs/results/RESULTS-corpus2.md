# RESULTS: corpus 2, real vulnerabilities. Eight valid cases, one detection.

> **RE-MEASURED AND CLOSED, 2026-08-31.** Radar and VaultLint were re-run **per case, per
> variant, over every case, with a log per run**. Both now carry `coverage_evidence: run log`, the
> strongest form: 18 runs each, 36 in total, **36 successes, zero unavailable**.
>
> **The evidence behind that sentence was defective, 2026-09-01 (error 32).** The runner decided
> `ok` versus `UNAVAILABLE` by asking whether radar had written an output file, and radar writes
> none when it finds nothing. radar's own stdout for all 18 runs is now committed at
> `raw/radar-c2-2026-08-31-stdout/` and confirms 36 and 36; two checks now compare the human log,
> the log that scores, and the tool's own account of what it did.
>
> **The conclusion held. Nothing detects anything on corpus 2** except the single X-Ray finding
> under a corrected mapping. But two details were wrong before and are worth more than the
> headline: Radar's mapped rule was said to "never fire at all" on eight of nine cases - it in fact
> fires in the right file on two of them, just not at the fix site (`unlocated`). And VaultLint's
> shape is coverage, not failure: **7 of 8 cases are `no-rule`**, a limit it states about itself.



> **THE CORPUS GREW AFTER THIS MEASUREMENT, 2026-09-01.** The table of cases below is the corpus as
> it stood on 2026-08-31. Eight more were added on 2026-09-01, and `spl-token-lending-rounding`
> was built later the same day, which makes seventeen. **Radar, solsec and semgrep with
> the SOL-0XX pack have since been re-run per case over sixteen of those seventeen** and detect
> nothing on any of them. **`vaultlint` has since been re-run over all seventeen**, 36
> invocations, 36 ok, zero unavailable, and its row on this page is superseded by
> `RESULTS-all.md`: 0 / 17 as registered, and one `unmapped_check` candidate, VL002 on
> `anchor-account-reload-owner`, differential and at the fix site. **The `sol-audit` v2 row on
> this page is retired**, superseded by v3 on 2026-09-01; it never had a run log and 96 of its
> 426 findings name files the corpus rebuild removed. The tables below are left exactly as
> published on 2026-08-31; this page's denominator of eight is still the right one for reading
> them as the record of that day, and the wrong one for reading them as a current result. Radar's own per-case
> breakdown moved on the re-run: `squads-signer-auth` is `missed`, not `unlocated` (error 31).
> The current corpus is `corpus2/manifest.json`, and its class and repository balance is recomputed
> in [`../CLASS-BALANCE.md`](../CLASS-BALANCE.md).

2026-08-31. Production Solana programs, each taken from the maintainers' own fix commit and its
parent, scored with a stricter method than the teaching corpus.

**Superseded in part.** This page records the first pass. Two things changed the same evening and
the consolidated, current table is in [`docs/results/RESULTS-all.md`](../../docs/results/RESULTS-all.md):

1. **One case was thrown out.** `cashio-account-data` is not a valid pair: its "fix" commit adds
   `invariant!(false, "temporarily disabled")` and switches the program off, so the fixed variant is
   dead code rather than repaired code. Excluded from every denominator, nine scored cases became
   **eight**, and `score2.py` now refuses to score any case marked `valid: false`.
2. **There is one detection, not zero.** X-Ray's rule `1019` fired on `squads-account-matching`
   at the fix site, on the vulnerable variant only. Our pre-registered mapping scored it zero
   because we had narrowed that rule to a single class. Our error, published both ways.

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

- **unlocated** - the mapped rule fires somewhere in the file, but not where the bug was
- **no-rule** - the scanner has no rule for this class at all, which is a coverage gap, not a failure

## The result

| Scanner | detected | unlocated | missed | no-rule | Teaching corpus score |
|---|---|---|---|---|---|
| `radar` | **0** | 0 | 8 | 1 | **11 / 11** |
| `vaultlint` | **0** | 0 | 1 | 8 | 2 / 11 |
| `sol-audit` v2 (ours) | **0** | 1 | 7 | 1 | 4 / 11 |

**Nothing was detected by any of these three.** X-Ray, measured later the same evening, produced
the single exception described above and in `docs/results/RESULTS-all.md`.

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
| `sol-audit` v2 | 4 / 11 | 0 / 8 (first pass said 0/9, before cashio was excluded) |

That gap is the entire argument for this corpus existing, and it is larger than we expected.

## Radar re-measured on corpus 2, 2026-09-04, at `fa81c25` (post-#36)

> New row beside the old one, nothing overwritten. Same corpus commit, same pre-registered mapping
> (`mappings/radar.json`, confirmed by the vendor in
> [`radar#32`](https://github.com/Auditware/radar/issues/32) comment 5523410629), same engine shim
> and procedure as the `67348ee` row of 2026-09-02. Raw:
> `raw/c2-radar-fa81c25.json` (+ `.run2`, `.log`, `.determinism.json`), per-invocation artefacts
> under `raw/radar-c2-2026-09-04-fa81c25/` with a README naming the revision.

| Radar revision | detected | missed | no-rule | unlocated |
|---|---|---|---|---|
| `24c56f9` (post-#35, 2026-09-02, docker) | 0 | 7 | 8 | 2 |
| `fa81c25` (post-#36 + docs/skill commits, 2026-09-04, engine shim) | **1** | **6** | 8 | 2 |
| `fa81c25`, same revision, **real docker image**, 2026-09-04 | **1** | **6** | 8 | 2 |

### The shim row and the docker row are the same row, and that was not guaranteed

The detection above was first measured through the **engine shim**, and the vendor themselves named
two ways shim and image could diverge: rules are baked into the image (`api/Dockerfile:113`), and
templates are filtered by detected framework. They called both "inert on all 17 pack cases", which
is a statement about seventeen cases rather than about the mechanism. Our only new corpus-2
detection rested on that.

So we measured the same revision again through
`ghcr.io/auditware/radar-api@sha256:1616723a1879668d4050def641e541f2c9edc878974b06011fb6b1a3bc519b4f`,
36 invocations per pass, 36 ok, two passes, deterministic. **The two rows are identical, and not
only in the scored verdicts: all 274 location rows match exactly.** Normalising the location format
and diffing the two raw files gives **0 rows appearing and 0 disappearing**:

    python -c "import json,re,collections
    def rows(p):
        out=[]
        for f in json.load(open(p)):
            for L in f.get('locations') or []:
                m=re.match(r'^(.*):(\d+):(\d+)(?:-(\d+))?$',L)
                out.append((f['name'],m.group(1),int(m.group(2)),int(m.group(3))))
        return collections.Counter(out)
    a=rows('raw/c2-radar-fa81c25.json'); b=rows('raw/c2-radar-fa81c25-image.json')
    print(sum((a-b).values()), sum((b-a).values()))"
    # -> 0 0

Image integrity was checked separately: **23 of 23 layer blobs plus the config are intact**, and the
only differences between the image contents and the checkout are build files (`.dockerignore`,
`Dockerfile`, tests) and build artefacts, **none in engine code**.

Raw: `raw/c2-radar-fa81c25-image.json` (+ `.run2`, + per-pass `.log`). Declared in
`adapters/radar.json` and in the golden record **before** being published here, which is the order
the shim row got wrong.

**The one new detection is `wormhole-sysvar`, and it is exactly what the vendor said it would be.**
Their comment 5523410629 claimed `Unvalidated Sysvar Account` would go missed→detected, firing at
`verify_signature.rs:92` and `:101` — both inside the pre-registered fix-sites — and stay silent on
the secure variant. Our run fires at exactly those two lines (`92:69-87`, `101:57-76`), on the
vulnerable variant only.

**36 invocations × 2 passes, all ok, deterministic** (72 in total; `raw/c2-radar-fa81c25.json.log`
and `.run2.json.log` each list 36, and `.determinism.json` records `"invocations": 72`). Of those
36, **34 are scored**: 17 valid cases × 2 variants. The 18th manifest case,
`cashio-account-data`, carries `valid: false` and is scanned but excluded from scoring. The
`24c56f9` row beside this one was 34 invocations, because that run did not scan the excluded case.

*Correction, 2026-09-04:* this paragraph and
[radar#32 comment 5523415188](https://github.com/Auditware/radar/issues/32) first said
"34 invocations × 2 passes". That was the `24c56f9` figure carried across by transcription. The
scored count is unchanged; the number of invocations actually run was not.

**274 location rows against 228, and the diff needs one caveat before it means anything.**
`f36d1a4` changed the location format: `24c56f9` emits `file:line:col`, `fa81c25` emits
`file:line:startcol-endcol`. A literal row-by-row diff between the two therefore reports every
row as new, which is an artefact of the format and not a finding. Normalising to the start
column, **50 rows appear and 4 disappear**, and 228 + 50 - 4 = 274.

| what appears | rows |
|---|---|
| `Unused Function Parameters`, `spl-stake-pool-mint-decimals`, 20 per variant | 40 |
| `Unused Function Parameters`, `solido-anker-arbitrary-cpi`, 1 per variant | 2 |
| `Incorrect Ceiling Division`, `spl-stake-pool-mint-decimals`, 1 per variant | 2 |
| `Unvalidated Sysvar Account`, `wormhole-sysvar`, insecure variant only | **2** |
| line moves: `Invoke Signed Unvalidated Seeds` and `Anchor Admin Without Timelock`, 2 each | 4 |

The 4 line moves pair exactly with the 4 rows that disappear, same rule and same case. So
**44 rows are `f36d1a4` generic-rule effects** (42 `Unused Function Parameters` plus 2
`Incorrect Ceiling Division`) and 2 are the wormhole detection. None of those generic rules is
mapped to a corpus-2 class, so no verdict other than wormhole changes.

*Correction, 2026-09-04:* the earlier text said "the remaining 46 new/changed rows" and broke
them down as "+21" and "+1". Both counted a single variant. Every corpus-2 case is scanned in
two variants, so the totals are 42 and 2, and the non-wormhole figure is 44, not 46. 46 is the
net change in row count, not the number of generic-rule rows.

Vendor-reported became measured. The right of reply works in both directions: we publish their
confirmed claim beside our earlier number, with the raw artefacts to check it.

## What we corrected about our own method, on the same day we published it

The first pass at corpus 2 **counted findings of any kind, anywhere in the file**, while corpus 1
counted only rules mapped to the class. Two different questions, printed in one table. It was our
error and it is recorded in [`docs/KNOWN-LIMITATIONS.md`](../../docs/KNOWN-LIMITATIONS.md).

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
- ~~**Determinism is unverified.**~~ **FIXED.** Each scanner was run twice and findings compared by
  rule and location: Radar 52 = 52, VaultLint 4 = 4, both identical.
- **Eight valid cases, one run each.** This is a small corpus and a first measurement.
- ~~Ground truth is the maintainers' own fix~~ **and that has to be read, not assumed.** One of the
  ten cases built turned out to have a fix commit that disabled the program instead of repairing
  it. Every remaining fix diff was then read individually; nine of ten hold up.
- **A detection under an unmapped rule is invisible to per-class scoring.** `unmapped_check.py`
  now asks the complementary question, and it is validated against the one case known to be real
  so that a run of zeros cannot silently mean a broken check.
- **The right of reply has not been exercised** for either third-party tool.

Full list, including code-level gaps, in [`docs/KNOWN-LIMITATIONS.md`](../../docs/KNOWN-LIMITATIONS.md).

## Reproduce

```
# from the repository root
python tools/build_corpus2.py --manifest corpus2/manifest.json --out corpus2
python tools/score2.py --demo
python tools/score2.py --scanner radar --kind radar --findings raw/c2-radar.json
python tools/score2.py --scanner vaultlint --kind vaultlint --findings raw/c2-vaultlint.json
```
