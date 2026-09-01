# RESULTS: real crates, not extracted files. The objection tested properly.

The strongest objection to the corpus-2 result was always that **we packaged it**: each
vulnerability extracted into a minimal single-file crate, so a tool needing project context fails
for our reasons rather than its own. It was a fair objection, and evidenced, since Radar returned
`400 Bad Request` on a bare `.rs` file until a manifest was supplied.

So the corpus is also built from the **real crates**: the entire directory containing the
implicated file, at the fix commit and its parent, with the project's own `Cargo.toml` and every
sibling module. Same commits, same answer key, same cases. Only the packaging differs.

**2026-08-31**: Radar and VaultLint were run there, over a nine-case build. Four of the other tools
never were, so the objection was tested for a quarter of the measurements and retired for none.

**2026-09-01**: the four that had never run there were run, over all eighteen cases, per case, per
variant, with an artefact and a log line per invocation. **Radar was re-run over the same eighteen
crates as well**, not to re-measure it but to find out how badly its coverage is skewed by the
crates it cannot finish, which is the second thing this page was leaving unanswered. The
2026-08-31 run is kept as published in its own page, linked below, rather than replaced.

---

## Which four had never been run here, and how that was established

Not from a summary. From the repository, four ways, all agreeing:

1. **The `Limits` section of this page**, as it stood at the start of the day: *"Two scanners, not
   six. X-Ray, solsec and semgrep have not been run against the real crates."* sol-audit is the
   fourth: it is one of the six and it is not one of the two.
2. **`raw/` contains no real-crate artefact for any other tool.** `grep -rl "c2crates\|/tmp/whreal"
   raw/` matches exactly two files, `whreal-radar.json` and its README, and that one is Wormhole
   alone. The only other real-crate record was `raw/realcrates-radar-run.log`, a per-case log with
   counts and no findings behind it.
3. **`tools/run_all.py` has no real-crate corpus at all.** `SOURCES` and `SOURCES_CORPUS2` are the
   only two, so `docs/COVERAGE.md`, which is derived from them, cannot show a real-crate row for
   anybody, and does not.
4. **`docs/ENGINEERING-LOG-2026-09-01.md`** states it under *What is still wrong*: *"Four of eight
   scanners have never been run on the real crates."*

The four: **sol-audit (ours), X-Ray, solsec, and semgrep with the MIT SOL-0XX pack.**

**And a fifth, which the "four of eight" sentence predates.** `sol-azy` was measured on corpus 1
and corpus 2 on 2026-09-01, has mappings in `mappings/`, appears in the README's result table, and
is not in `tools/run_all.py` yet. It has no real-crate run either, and it is not one of the four
run here. Counting it, five of the measured tools had never seen a real crate this morning and
four of them have now. Saying "the four are done" and stopping would leave that gap closed on
paper only.

One more thing surfaced while establishing this, and it is worse than the gap it was found beside.
**Neither of the two tools that HAD been run there had a findings file in the repository.** The
Radar table below was published from a log holding counts; the VaultLint table, including its
38 findings, was published from a file that lived only on the run host. Both have now been
recovered from that host and committed, unchanged, as
[`raw/rc-recovered-20260831-radar/`](../../raw/rc-recovered-20260831-radar/) and
[`raw/rc-recovered-20260831-vaultlint.json`](../../raw/rc-recovered-20260831-vaultlint.json). The
recovered Radar log is byte-identical to the committed `raw/realcrates-radar-run.log`, which is
what ties the recovered files to the published table. The 38 VaultLint findings and every per-case
count in its table recompute from the recovered file exactly.

---

## The corpus these ran against

`python tools/build_corpus2.py --manifest corpus2/manifest.json --out /tmp/rc-crates --crates`
built **18 of 18 cases**, one of which (`cashio-account-data`) the manifest marks as not a valid
pair, so **17 are scoreable**. The crates hold **878 `.rs` files**, from 4 to 145 per case, median
34.

That total is quotable this time because the per-crate counts are committed in
[`raw/rc-crates-built-2026-09-01.json`](../../raw/rc-crates-built-2026-09-01.json), which the build
writes itself, and `test_all.py` recomputes the total from it rather than accepting the digits on
this page. An earlier version quoted a `.rs` total that nobody could recompute, because the crates
are built into a temporary directory and never committed. That was error 23, and it is not
repeated by quoting a different unverifiable number.

---

## What was run, and what it opened

One invocation per case per variant, container isolated, corpus mounted read-only where the tool
permits it, network off. Coverage is taken from **the tool's own account of what it opened**, never
from the presence of an output file.

| scanner | invocations | analysed | could not finish | findings | what proves coverage |
|---|---|---|---|---|---|
| sol-audit 3.0, strict | 36 | 36 | 0 | 1111 | its own `files_scanned` |
| sol-audit 3.0, broad | 36 | 36 | 0 | 3021 | its own `files_scanned` |
| sol-audit 3.0, all | 36 | 36 | 0 | 5031 | its own `files_scanned` |
| semgrep + SOL-0XX pack | 36 | 36 | 0 | 3633 | its own `paths.scanned` |
| solsec 0.2.1 | 36 | 36 | 0 | 5867 | its own `Found N Rust files to analyze` |
| X-Ray v0.0.6 | 36 | 30 | **6** | 108 | a parsed `.ll.json` report |
| Radar (re-run) | 36 | 20 | **16** | 143 | an output file that exists and parses |

Every row has a log with one entry per invocation: `raw/rc-<scanner>.json.log`. The per-invocation
artefacts are committed as `raw/rc-artefacts-<scanner>-2026-09-01.tar.gz`, one file per invocation
inside, compressed only because uncompressed they are 17 MB of JSON against a 9 MB repository.

**Provenance, before any of it ran.** semgrep from its official image `semgrep/semgrep:latest`
(digest `sha256:f1f7b718…`), loaded with the MIT SOL-0XX pack whose sha256 on disk,
`babf9119…d347d02e`, is the one pinned in `mappings/semgrep-solana-standard-c2.json` before the
first run on any corpus. X-Ray from the project's own image `ghcr.io/sec3-product/x-ray:latest`
(`sha256:543dc6a9…`). solsec 0.2.1 from crates.io built inside `rust:slim`, the image the previous
run built and the same tool version. sol-audit 3.0 from its own source at commit `582e7d2`, run
inside a stock Python image.

**No mapping was written for this run.** Every score below uses the mapping already in
`mappings/`, pre-registered before the corpus-2 runs. Writing a new mapping after seeing real-crate
output would have made this page an exercise in fitting.

---

## The scores, with the denominators said out loud

`detected` means the pre-registered mapped rule fires **at the site the fix changed** on the
vulnerable crate and **not on the same crate fixed**. `no-rule` means the scanner's mapping claims
no rule for that class, which is a coverage gap and not a failure. `unavailable` is a case the tool
could not finish, and it is never a zero.

| scanner | detected | unlocated | missed | no-rule | could not run | scoreable cases |
|---|---|---|---|---|---|---|
| sol-audit 3.0, strict / broad / all | **0** | 1 | 8 | 8 | 0 | 9 / 17 |
| semgrep + SOL-0XX, narrow reading | **0** | 3 | 5 | 9 | 0 | 8 / 17 |
| semgrep + SOL-0XX, wide reading | **0** | 3 | 14 | 0 | 0 | 17 / 17 |
| solsec 0.2.1 | **0** | 1 | 1 | 15 | 0 | 2 / 17 |
| X-Ray, pre-registered map | **0** | 0 | 8 | 6 | 3 | 8 / 17 |
| X-Ray, corrected map | **1** | 0 | 7 | 6 | 3 | 8 / 17 |
| Radar (re-run) | **0** | 0 | 5 | 4 | 8 | 5 / 17 |

All three sol-audit profiles return the identical verdict on every case, so they are one row.

**The one detection is X-Ray on `squads-account-matching`**, rule 1019 firing at the fix site on
the vulnerable crate and silent on the fixed one. It is the same case, the same rule and the same
correction as on corpus 2: the pre-registered mapping narrowed rule 1019 to a single class on the
strength of a vendor blog post, which is error 17, and the corrected mapping that widens it was
published beside the pre-registered one rather than replacing it. Both are scored here for the same
reason. **We are not the ones who get to decide which of our two mappings counts**, so both are on
the page.

That detection is also this page's positive control on real data. A scorer whose only observed
output is zero is not evidence about anybody's tool. `tools/rc_score.py --demo` drives a synthetic
real-crate case end to end and asserts `detected`, `unlocated`, `missed`, `no-rule` and
`unavailable` are all reachable; the X-Ray result shows the same path firing on a real crate that a
real tool really analysed.

**Nothing is hiding under an unmapped rule, with one candidate that turns out not to be one.**
`rc_score.py` reports every rule of any kind that fires at the fix site on the vulnerable crate and
nowhere in the fixed file. Across all six runs that list has exactly three entries: X-Ray's 1019
above, and semgrep's `sol-010-init-if-needed` twice on `wormhole-sysvar`. The semgrep one is not a
detection and the reason is in the rule's own text: SOL-010 is about reinitialization and fires on
`try_borrow_mut_data()`, and the Wormhole fix replaces `load_current_index` with
`load_current_index_checked`, which removes the raw borrow. The rule went quiet because the code it
matches was deleted, not because the vulnerability it names was fixed. **A differential comparison
with no mapping would have counted it**, which is precisely why the mapping exists.

---

## The packaging objection, as a comparison rather than an assertion

Corpus 2 and the real crates now hold **the same seventeen valid cases**, differing in packaging
and in nothing else. So the objection can be answered case by case rather than argued:

```
python tools/rc_compare.py
```

It scores corpus 2 now, from the committed findings files and the same mappings, reads the
real-crate verdicts from the committed `raw/rc-score-*.json`, and puts them side by side. A case
either tool could not run on either side is **not** counted as agreement; two unavailables are two
missing observations, and treating them as a match would have inflated the only number this
section has.

| scanner | verdicts compared | identical | differ | not comparable |
|---|---|---|---|---|
| sol-audit 3.0, strict | 17 | 17 | **0** | 0 |
| sol-audit 3.0, broad | 17 | 17 | **0** | 0 |
| sol-audit 3.0, all | 17 | 17 | **0** | 0 |
| semgrep + SOL-0XX, narrow | 17 | 17 | **0** | 0 |
| semgrep + SOL-0XX, wide | 17 | 17 | **0** | 0 |
| solsec 0.2.1 | 17 | 17 | **0** | 0 |
| Radar | 9 | 9 | **0** | 8 |
| X-Ray, pre-registered map | 7 | 7 | **0** | 10 |
| X-Ray, corrected map | 7 | 7 | **0** | 10 |

**125 verdicts compared across the two packagings. Zero differ. 28 could not be compared**, and
those 28 are named in the tool's output rather than rounded away: X-Ray's corpus-2 findings file
predates eight of the cases, and Radar and X-Ray between them cannot finish eleven of the real
crates. `spl-token-lending-rounding` was in that list until 2026-09-01, when every corpus-2 row
here was re-run over all seventeen cases. Radar's eight remaining are real-crate failures, not
corpus-2 gaps. **Radar's
nine uncomparable cases are the point of the next section**: two of them are cases where it returns
`unlocated` on the extracted file and cannot open the real crate at all.

---

## What could not finish, and the skew that leaves

### X-Ray cannot open three crates, and it is scope rather than size

`anchor-interface-account`, `anchor-program-system` and `anchor-account-reload-owner` are all the
same crate, `anchor-lang`, and X-Ray answers with its own line:

```
X-Ray v0.0.6
No Xargo.toml or Cargo.toml file found in: /workspace
```

The manifest is plainly there. What is not there is a program: `anchor-lang`'s manifest has no
`[lib] crate-type = ["cdylib"]`, so it is a library other programs link, not something that gets
deployed, and X-Ray compiles deployable programs. Pointing X-Ray straight at the crate root instead
of its parent produces the identical message, so this is not our layout being wrong. **Recorded as
unavailable, never as three zeros**, and reported here because X-Ray's message names the wrong
cause and cost an hour to see through.

Those three are also the only cases in the corpus whose vulnerability lives in a library rather
than in a program. On corpus 2 they are single extracted files with a synthetic manifest, and X-Ray
opens them. That is the packaging objection running in the opposite direction, in our favour, and
it is worth saying plainly: **on these three cases the extracted corpus flatters X-Ray by giving it
something it can compile.**

### Radar cannot finish eight of the seventeen, and the published reason for it was wrong

Rather than report the old coverage figure and note that it was biased, Radar was re-run over all
eighteen current crates. **36 invocations, 20 completed, 16 could not finish**, and the eight cases
it cannot finish are:

`anchor-account-reload-owner`, `anchor-interface-account`, `anchor-program-system`,
`metaplex-bubblegum-creator`, `metaplex-token-metadata`, `spl-stake-pool-fee-rounding`,
`spl-stake-pool-mint-decimals`, `token-2022-confidential-approve-mint`.

Its message on every one of the 16 is its own: `Exceeded maximum retries. Tasks did not complete in
time.` `radar scan --help` offers no flag for the retry budget or the time limit, so there is no
argument to change that would let it finish, and inventing one would be tuning. Every one is
recorded **unavailable**. None is a zero.

**This corrects something this page published on 2026-08-31**, and `docs/KNOWN-LIMITATIONS.md` 21
still carries the wrong wording above its correction so the record survives. It said "the pattern
is size - everything above roughly a hundred files failed, everything below it finished". That is
false:
`spl-stake-pool` fails at **38** `.rs` files and `token-2022` fails at **63**, both far below a
hundred. The split in this corpus is clean on two measures at once and the data cannot separate
them:

| Radar over the 17 valid crates | `.rs` files | Rust source bytes |
|---|---|---|
| the 9 it finished | 4 to **34** | 33 KB to **393 KB** |
| the 8 it did not | **38** to 145 | **688 KB** to 1133 KB |

Nothing in the corpus falls between 34 and 38 files, or between 393 KB and 688 KB, so this run
cannot say which quantity Radar is hitting, only that the threshold is far lower than the earlier
wording implied. The per-crate volumes are committed in
[`raw/rc-crate-bytes-2026-09-01.json`](../../raw/rc-crate-bytes-2026-09-01.json) so the boundary can
be recomputed rather than taken on trust.

**What the skew costs.** Radar's real-crate evidence covers **9 of 17 cases and 185 of the 878
`.rs` files, 21 percent of the corpus by volume**, and every crate in it is at the small end. Its
scoreable denominator is **5 of 17** once the four `no-rule` classes come out. Two of the eight it
cannot finish, `metaplex-token-metadata` and `token-2022-confidential-approve-mint`, are cases
where it returns `unlocated` on the extracted file: the extracted corpus is the only place Radar
can see them at all. **"Radar detects nothing on the real crates" is a statement about small
crates**, and it stays that way until either Radar finishes a large one or somebody measures that
band another way.

---

## The 2026-08-31 run

Kept as published, verbatim, in
[`RESULTS-realcrates-2026-08-31.md`](RESULTS-realcrates-2026-08-31.md): Radar over the nine-case
build and VaultLint on the same crates, six scoreable pairs and zero detections for either.

---

## Two things their authors should see

**The SOL-0XX rule for this exact class fires on the fixed code and not on the vulnerable code.**
On `wormhole-sysvar`, `sol-035-instructions-sysvar-substitution` - the rule whose own message is
about pinning the instructions sysvar - fires twice on the **fixed** variant and never on the
vulnerable one. It matches the `_checked` introspection helpers, and the vulnerable code is
vulnerable precisely because it uses the unchecked ones. The rule is not wrong about what it
matches; it is pointed at the safe form. Offered to the ruleset's maintainer under the right of
reply, whose correction is published whatever it says.

**solsec exits 1 when it finds a critical issue**, with `Critical issues found. Failing as
requested.` in its own log. The first version of our runner read a non-zero exit as an outage and
recorded eight completed scans as unavailable. That is a "could not run" published about a run that
ran, which this project got wrong in the other direction the same day, and it was corrected after
seeing the output, deliberately and on the record: the log of the first attempt is kept as
[`raw/rc-solsec-attempt1-exitcode.json.log`](../../raw/rc-solsec-attempt1-exitcode.json.log). Its
28 successful runs and the 28 matching runs of the corrected attempt agree on all 3212 findings,
by file, rule and line, which is the only determinism evidence on this page and it was free.

---

## The analysis error the first real-crate run produced, and how it was caught

The first comparison matched findings by `(rule, line)` between the two variants. On that basis
Radar looked like it was **detecting things**: 23 findings present only on the vulnerable Cashio
variant, 6 on Solend, one each on three more cases. Cashio's included `Missing Token Mint
Constraint`, which is the class of the Cashio bug. That reads as a spectacular result.

**It was arithmetic.** A fix that inserts lines moves every finding below it. Solend's fix adds
four lines at 1796, so a finding at 2064 in the vulnerable file sits at 2068 in the fixed one and a
naive comparison calls it "present only on the vulnerable variant". Every one of Solend's six
phantoms was below the insertion point.

`shiftaware.py` maps each finding's line through the diff hunks before comparing, so a finding is
only counted as absent when it has no counterpart at its shifted position. Under that comparison
**every apparent detection disappears, on every case, including all 23 on Cashio.**

This also corrects something published earlier the same evening. The Cashio case is genuinely
invalid - its fix commit adds `invariant!(false, "temporarily disabled")` and switches the program
off, which is established by reading the diff and the repository history, independently of any
scanner. But the mechanism given for the 23 findings, that they vanished because the fixed variant
is dead code, **was wrong**. They vanished because our comparison could not do arithmetic. The
conclusion stands, the explanation did not, and asserting a cause without testing it is a mistake
this log already records once.

---

## What this does to the packaging objection

**For the four scanners run on 2026-09-01, the objection is retired.** Not "weakened": the same
seventeen cases were scored under both packagings with the same pre-registered mappings, and every
verdict that could be compared came out the same. Whatever those tools are failing to see, our
packaging is not what stopped them, because unpackaging changed nothing at all.

**For Radar it is answered on the cases it can open and unanswerable on the rest.** Its eight
comparable verdicts agree across packagings too, so nothing suggests the packaging is doing the
work there either. But it cannot finish 8 of the 17 real crates, its scoreable denominator is 5,
and two of the cases it cannot open are cases where the extracted file is the only thing it can
see. **A zero over five small crates is not the same claim as a zero over seventeen**, and this
page does not let the first stand in for the second.

**It is not retired for VaultLint at all.** One whole-corpus invocation on a nine-case build, in
which five of ten cases cannot distinguish "found nothing" from "never analysed", is not evidence
about packaging. `sol-azy` has never been run on a real crate.

**And retiring the objection is not the same as proving the general claim.** Seventeen cases drawn
from public postmortems is a corpus that is systematically harder than the population of real
bugs, and it answers "do these tools catch the ones that cost money". It cannot support "these
tools do not work". What today removes is one specific alternative explanation for a zero, on four
of the tools that carry one, and it narrows that explanation on a fifth.

---

## Reproduce

```bash
# on a host with docker; the crates are built on demand and never committed
python tools/build_corpus2.py --manifest corpus2/manifest.json --out /tmp/rc-crates --crates
python tools/rc_run.py   --tool semgrep   --crates /tmp/rc-crates --out /tmp/rc-out
python tools/rc_run.py   --tool solsec    --crates /tmp/rc-crates --out /tmp/rc-out
python tools/rc_run.py   --tool sol-audit --crates /tmp/rc-crates --out /tmp/rc-out --profile strict                          --tool-dir /tmp/sol-audit   # a checkout of the sol-audit repository
python tools/rc_run.py   --tool xray      --crates /tmp/rc-crates --out /tmp/rc-out
python tools/rc_run.py   --tool radar     --crates /tmp/rc-crates --out /tmp/rc-out
python tools/rc_score.py --scanner solsec --kind solsec --findings raw/rc-solsec.json \
                         --crates /tmp/rc-crates

# these two need nothing but the repository
python tools/rc_score.py --demo      # the positive control, in the real-crate layout
python tools/rc_compare.py           # the packaging comparison, both sides from raw/
```

Raw artefacts: `raw/rc-*.json` with a `.log` per findings file, per-invocation output in
`raw/rc-artefacts-*.tar.gz`, scored verdicts in `raw/rc-score-*.json`, the crate inventory in
`raw/rc-crates-built-2026-09-01.json`.

---

## Limits

- **Radar's real-crate zero rests on 5 scoreable cases of 17**, all of them small crates, and
  VaultLint's on one whole-corpus invocation over a nine-case build that predates eight of the
  cases.
- **`sol-azy` has still never been run on a real crate**, and neither Radar nor VaultLint has been
  run on the current eighteen-case build. Three runs would close this page rather than one.
- **None of this appears in `docs/COVERAGE.md`.** That matrix is derived from `run_all.py`, which
  knows two corpora, and the real crates are not one of them. The per-invocation logs are the
  coverage evidence for this page until a real-crate corpus is registered there, which is a change
  to a file another agent is rebuilding today and was deliberately not made from here.
- **Radar cannot finish 8 of the 17 real crates**, and the boundary is far lower than this page
  once said: it fails at 38 `.rs` files, not at a hundred. Its coverage is 21 percent of the corpus
  by source volume.
- **X-Ray cannot open the three `anchor-lang` cases at all**, so its denominator is 8 of 17 and
  three cases it scores on corpus 2 are unavailable here.
- **Seventeen cases is not a corpus.** It is enough to retire one objection about four tools, not
  to prove a general claim about any of them.
- **Every third-party result here is provisional** until its authors have used the right of reply
  in [`docs/PROTOCOL.md`](../PROTOCOL.md). The open thread with Auditware is
  [Auditware/radar#32](https://github.com/Auditware/radar/issues/32); nothing has been sent to
  sec3, to the solsec author or to the SOL-0XX maintainer about this page yet.
- **The `no-rule` counts are large and they are the real story for two tools.** solsec's mapping
  claims a rule for the class of only 2 of the 17 cases, sol-audit's for 9. A zero over a
  denominator of two says almost nothing about solsec, and this page does not pretend otherwise.
