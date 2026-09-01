# Engineering log, 2026-08-31

Everything that happened on the day this benchmark was built, in order, including every mistake.

This exists because the project's only real asset is that its numbers can be checked, and a reader
who cannot see how a number was produced has to take it on faith. Twenty-one errors are recorded
below. Sixteen were caught by measurement or by a check, five by a person noticing. Two would have
put a false statement in a funding application, one had already been published before it was
caught, and one was a defect in our own ground truth.

---

## Part 1: before there was a benchmark

**14:00. The starting question was not about scanners at all.** It was whether to register a
foundation and whether autonomous agents could raise money for it. Six research agents were
dispatched across Polish micro-grants, corporate foundations, international open-source funds,
philanthropic AI funding, the legal mechanics of paying yourself from a foundation, and legal
alternatives.

**Error 1. I declared our own search infrastructure dead.** SearXNG on the VPS returned zero
results with all five engines suspended, so I warned every running agent that it was broken. Then I
checked the opportunity radar's output and found it had run successfully at 05:26 that morning with
real results. It was not dead, it was rate-limited, and the difference matters: a permanently dead
service gets replaced, a throttled one gets used more carefully. **Caught by looking at the artefact
instead of the symptom.**

**Error 2. I reported `live-state.json` as missing.** It was at `/root/cowork-shared/`, not
`/root/`. My path was wrong. I had been one command away from telling Bartosz a working system was
broken. **Caught by running `find` before writing the sentence.**

**The foundation answer, verified at source:** NOWEFIO 2026 requires registration before
31.12.2024, PROO excludes anything registered after 1.11.2022, OPP status requires two years. Every
large Polish public grant is closed to a new foundation for two to three years. Meanwhile NLnet,
Ethereum ESP, Solana Foundation, Manifund and the Transformative AI Fund all accept individuals.
So the conclusion was the opposite of the question: **a foundation is not needed for anything
available in the next three months.**

---

## Part 2: the error that would have gone into a funding application

**Error 3, the worst of the day.** Bartosz wrote "solana odrzucona". I assumed it meant the $8,000
benchmark grant, wrote that into six documents, published a strategic analysis built on a record of
"nought for two", and told him a competitor had rejected the ScannerTruth thesis.

The rejection email was for a **different application**: Superteam Agentic Engineering, $200, a
Solana rent reclaim scanner. **The $8,000 benchmark grant had not been rejected and is still open.**

I took an ambiguous three-word message and resolved it against the only Solana application I had in
mind, rather than asking which one. Six files corrected, four given correction banners.

**Then I verified the amount properly.** Opened the live application form on Superteam Earn: 8,000
USDG, title "Open Precision Benchmark for Solana Security Scanners". The draft on disk said 6,000
and was marked NOT SENT. Reading the notes would have produced a wrong number in a live
conversation.

**Error 4. A claim in the grant application was too strong.** It said "not one of them publishes a
measured false-positive rate". Auditware publishes exactly those numbers in its own pull request
descriptions. Anyone who knew the Radar repository could have refuted it in a minute. The accurate
version, which is also stronger, is that **vendors measure themselves against a corpus they tune
on, and nobody publishes an independent, cross-tool, repeatable measurement.**

---

## Part 3: the thing the application cited did not exist

The submitted application referenced `docs/PROTOCOL.md` and a public repository with the benchmark
harness. **Neither existed.** The workspace was not even a git repository, so there was also no
commit history to date the "pre-registered methodology" claim.

A reviewer clicking through to a 404 would have been worse than a weak result.

**Before building anything, I recomputed the headline from the raw data.** 2/11 nominal and 0/11
real reproduced exactly. The application's numbers were correct. I had been saying "0/11" all
afternoon and the full figure is **2/11 nominal, 0/11 real**, which is a better story: it shows
precisely how a scanner manufactures a score.

Published `scannertruth`: protocol, results, harness, raw data, and `verify.py`, which exits
non-zero if the published result does not reproduce.

**Error 5, and then error 6.** Local tooling state under `.omc/` was swept into the first commit.
Contents were benign, no credentials, but it exposed internal VPS paths and a username. I removed it
and added a `.gitignore`. **Then I created the second repository the same way an hour later and it
happened again**, because I had fixed the symptom in one repo instead of the cause in my own
procedure.

---

## Part 4: repairing the scanner

The diagnosis was structural, not a matter of missing rules: **every v1 rule tested for the presence
of a construct and none tested for the absence of a check.** A vulnerable program and its fix
contain the same constructs, so those rules must fire on both. This is predictable by reading the
rules, without running anything.

Every rule was rewritten as "construct present AND guard absent". Real recall went **0/11 to 4/11**.

**Error 7, and it is the same error the project exists to expose.** I added `declare_id!` to the
list of program-id guards. Every Anchor program declares its own id, so it guards nothing about a
CPI target, and it silently suppressed a correct detection on `5-arbitrary-cpi`, costing a class.
**Caught by measurement, not by reading the code.** Presence of a symbol is not evidence of a check.

**A regression was introduced and disclosed rather than omitted:** `1-account-data-matching` was a
clean miss in v1 and became a false positive in v2. A silent miss traded for a wrong alarm.

**Also concluded honestly:** `8-pda-sharing` is probably not detectable by a text scanner at all.
The fix does not add a check, it changes a PDA seed from shared to account-specific. That is
semantic, not syntactic. Better to say so than to write a rule that appears to catch it.

---

## Part 5: the channel that was not delivering

**Error 8, and it cost a whole day.** Three instructions were filed to the agent's task file with
`## A.146` headings. The brief that the agent actually reads extracts them with the regex
`^# (A\.\d+)` — one hash, not two. **None of my three instructions existed from the agent's
perspective**, including the decisive question about whether being an individual rather than an NGO
had ever cost us money, filed that morning while Bartosz was mid-conversation with Superteam.

The artefact existed. The delivery did not. This is the project's most repeated failure and I
committed a fresh instance of it while writing about it.

**Fixed and verified at the receiving end**, not at the sending end: the headings were corrected and
the brief was regenerated and read back to confirm the entries appear.

---

## Part 6: measuring somebody else's tool

**Near miss 9, prevented by a warning from Bartosz.** He said to check what we download. Provenance
check on crates.io: `cargo install radar` would have installed **an unrelated 2021 crate by a
different author**. The real Radar by Auditware is not published on crates.io at all. Installing by
name would have measured a random package and called it a competitor.

**Error 10.** I had already installed Rust via `curl | sh` as root before that warning, from the
official domain over TLS, but without telling him first. The Radar install script was then
downloaded and read in full, all sixty lines, before being run. It is clean.

Everything untrusted afterwards ran in containers: VaultLint built inside `rust:slim` with the
corpus mounted read-only, Semgrep as an image, and Radar orchestrates its own containers.

**Radar scored 11/11 real recall.** Better than ours by a factor of nearly three, stated in the
first paragraph of the results because it is uncomfortable.

**Then the context arrived.** Searching Radar's issue tracker for prior art turned up four pull
requests filed **that same day** by `forefy`, who works at Auditware, with titles including "Close
the last corpus gaps". The vendor was tuning the tool against this corpus on the day we measured it.

I first read this as "someone is doing exactly what we do" and corrected within a minute: a vendor
self-testing is not an independent benchmark. It is the thing we say is insufficient, and it became
**the best possible evidence for our own thesis**, dated and documented.

**VaultLint scored 2/11 real, and its precision claim held.** Everything it detected, it detected
correctly. The first time this benchmark confirmed somebody's claim rather than refuting it, which
matters: a measuring instrument that only ever produces bad news is suspect.

---

## Part 7: the clock

**Error 11.** The voice-generation script ended with `touch done` regardless of whether the previous
steps succeeded. The marker appeared, the files did not. Exactly the "it looked done and nothing
happened" pattern, in a script I wrote while documenting that pattern.

**Error 12.** I diagnosed the cause as a missing `ffmpeg` and told Bartosz the daily voice cron was
probably broken too. It was not: `ffmpeg` lives at `/root/bin/ffmpeg` and I had called the bare
name. **A false alarm about a working system**, corrected within two minutes.

The clock was then built to record a scanner with no raw output as **unavailable, never as a zero**,
because a history that conflates "we could not run it" with "it found nothing" will eventually
report a regression that was our own harness breaking. It was tested end to end by running it, not
by trusting the crontab entry, and it published its own first entry.

---

## Part 8: corpus 2, and the methodological error I caught myself

Nine real vulnerabilities were extracted from maintainers' own fix commits and their parents:
Wormhole, Cashio, Solend, Squads twice, Metaplex three times, and one against Anchor itself. File
paths are derived from each commit rather than typed in, so a mistake in the notes cannot silently
produce a wrong pair.

**Nothing detected anything.** Radar 0, VaultLint 0, ours 0.

**Error 13, found by asking myself what we had oversimplified.** Corpus 2 was first scored by
**counting findings of any kind anywhere in the file**, while corpus 1 counted only rules mapped to
the vulnerability class. Two different questions, printed in one table as if comparable.

Rewritten as `score2.py`: mapped rules only, and the finding must land **at the site the fix
changed**, tolerant of line shift. A third verdict, `unlocated`, was added for a mapped rule that
fires in the file but not at the bug, because collapsing it either way lets the author choose the
flattering answer.

**The conclusion survived the stricter method**, which is the part worth stating: it was not an
artefact of the sloppy one. And the strict scorer immediately surfaced two `unlocated` cases in our
own scanner that the hand measurement had lumped in with the misses.

**Error 14.** Corpus 1 names classes `10-sysvar-address-checking`, corpus 2 `sysvar-address-checking`.
The first strict run reported `no-rule` for all nine cases. The tool was loud about it rather than
silently scoring zero, which is how it was caught in seconds.

**Error 15, twice.** Editing `run_all.py` through a shell heredoc split a string literal across two
lines and broke the file, then broke it again the same way while fixing it. Nested quoting through
bash. Resolved by avoiding the escape entirely.

---

## Part 9: testing our own strongest objection

The obvious attack on the corpus 2 result was that **we packaged it**: single files extracted into a
synthetic crate, so an Anchor-oriented tool would fail for our reasons rather than its own. That
objection was real and evidenced, since Radar had returned `400 Bad Request` on a bare file until a
manifest was supplied.

So it was tested on the strongest case. The Wormhole program was re-extracted as **the real crate**:
`solana/bridge/program` in full, at both commits, with its own `Cargo.toml` and all 46 sibling
modules. Radar ran 57 templates.

**Its `Unvalidated Sysvar Account` rule still did not fire**, and every finding in the vulnerable
file appeared identically in the fixed one. The objection does not explain the miss.

**Determinism was checked** before trusting any of this over time: each scanner run twice, findings
compared by rule and location. Radar 52 = 52, VaultLint 4 = 4, both identical.

**Semgrep was added as a third tool** and produced zero findings under three configurations, with
zero errors. Not a miss: `p/rust` contains eleven rules in total and none concern Solana. The most
widely used generic static analyser has no coverage of this domain at all.

---

## Part 10: the same error, a third time

**Error 16, and it is error 11 wearing different clothes.** The per-case run of Radar over the
real-crate corpus printed `ok` for all ten cases and `PER_CASE_DONE`. The output file was **zero
bytes**. The loop reported the completion of a step rather than the existence of its result, which
is the exact failure recorded earlier in this log as a `touch done` that fired regardless of
success, and which the log itself calls the project's most repeated failure.

Nothing was scored from it. The run was rewritten to print `ok` only after the output file exists
**and** parses as JSON, and to print `FAILED` with the return code otherwise, so a silent
production of nothing is no longer indistinguishable from a clean result.

The general shape, now three instances deep: **we check that a step ran, not that it produced
something.** Every remaining harness step should be read with that question.

---

## Part 11: the headline was wrong, and our own mapping was hiding it

**Error 17, and it is the most consequential of the day**, because unlike the others it had already
been published and it understated somebody else's tool rather than ours.

The consolidated page went out saying that none of six scanners detected anything on real
vulnerabilities. Checking X-Ray's single corpus-2 finding before quoting it in conversation showed
that statement to be false.

X-Ray's rule `1019` is named **"The account may not be properly validated and may be untrustful"**.
We mapped it to `sysvar-address-checking` and nothing else, because sec3's own blog presents 1019 as
the rule that catches the Wormhole hack. **That is an example of the rule, not its scope**, and
narrowing a generic rule to one class on the strength of a marketing post was our error.

It fired once in all of corpus 2: `squads-account-matching/insecure`, `src/lib.rs:310`. The
maintainers' fix changed lines **309 and 311**, adding the check that the instruction account keys
match the submitted keys. It did not fire on the fixed variant. A real vulnerability, detected at
the fix site, differentially — **the only such detection any of the six scanners made** — and our
pre-registered mapping scored it zero.

Both numbers are now published, **0/9 as registered and 1/9 corrected**, with the pre-registered map
preserved unedited beside the correction. A benchmark that quietly repairs its mapping after seeing
the scores is worth nothing, and the point of pre-registration is that it binds when the result is
inconvenient. What sec3's rule actually covers is theirs to say, which is what the right of reply is
for, and they have not been asked.

**Two denominators were wrong as well**, both found in the same check. X-Ray ran nine cases, not
ten: the findings files list only cases where something fired, so coverage has to be read from the
run log. And solsec produced no output at all for three of nine cases with no log explaining why,
which makes it 0/6 with three **unavailable**, not 0/9. That is the exact distinction this project
insists on and we had just collapsed it in our own table.

**The lesson is narrower than "check your work".** Every one of these errors came from trusting a
derived artefact instead of the thing it was derived from: a findings file instead of a run log, a
blog post instead of a rule name, a summary line instead of raw JSON. The check that keeps working
is going one level down toward the source.

**And solsec turned out to be the cleanest demonstration of the project's thesis anyone could ask
for:** 108 findings on corpus 2, and every rule that fired on a vulnerable program fired on its fix
too, without a single exception. A benchmark that counts findings ranks it near the top. This one
ranks it at zero.

---

## Part 12: a case in our own corpus where the fix was not a fix

**Error 18, and it is a ground-truth error, which is the worst kind this project can make.** Every
other number here rests on the claim that the `secure` variant is the vulnerable program with the
bug removed. For one case that was false.

Radar, run over the **real crate** rather than the isolated file, produced **23 findings on
`cashio-account-data/insecure` that were absent from `secure`**, including `Missing Token Mint
Constraint`, which is the class of the Cashio bug. Read quickly, that is a detection, and a
spectacular one: the tool that found nothing on the isolated files finds the bug the moment it is
given the real project.

Reading the diff instead showed what the commit does:

```
+ vipers::invariant!(false, "temporarily disabled");
```

added to `print_cash` and `burn_cash`. **It does not fix the vulnerability, it switches the program
off.**

**Correction, made an hour later, to this entry's explanation.** The sentence originally here said
the findings disappear from the `secure` variant because the code is dead. That was asserted, not
tested, and it is wrong. They disappeared because our comparison matched findings by `(rule, line)`
and the fix inserts lines, shifting every finding below it. Under a shift-corrected comparison all
23 have counterparts in the fixed variant and none of them was ever differential. See error 19.
**The case is still invalid** — that follows from reading the diff and the history, independently of
any scanner — but the mechanism given for the 23 findings was not. `git log` confirms there is no other candidate: three commits in the repository's entire
history touch that file, this is the last, and everything after the exploit is a dependency bump.
Cashio never shipped a fix because the protocol was shut down.

The case is now marked `valid: false` in the manifest with the reason, excluded from every
denominator, and **`score2.py` refuses to score any case marked that way**. A note in a manifest
does not stop the next run from counting it. Corpus 2 drops from nine scored cases to eight.

**What nearly happened is the point.** A result that flattered the story arrived, and the only thing
between it and publication was reading a four-line diff. This is the same discipline that produced
error 17 in the opposite direction, where the surprising result damaged somebody else's tool. The
rule that catches both is identical: **a result you did not expect is a reason to go to the source,
whichever way it points.**

---

## Part 13: a comparison that could not do arithmetic

**Error 19, and it is error 15 again: a cause asserted without testing it, published, then
refuted.**

Running Radar over the real crates, the first comparison matched findings by `(rule, line)` between
variants. On that basis Radar appeared to be detecting things it had missed on the extracted files:
23 findings present only on vulnerable Cashio, 6 on Solend, one each on three more cases. It was the
result the packaging objection predicted, arriving exactly where it was expected.

**A fix that inserts lines moves every finding below it.** Solend's fix adds four lines at 1796, so
a finding at 2064 in the vulnerable file sits at 2068 in the fixed one, and the comparison called it
absent. All six of Solend's phantoms were below the insertion point, which is what gave it away.

`shiftaware.py` maps each line through the diff hunks before comparing. Under it, **every apparent
detection disappears on every case**, including all 23 on Cashio, and Radar's real-crate result is
zero across six scoreable pairs.

Two things follow. The packaging objection is retired properly rather than on one case. And the
explanation published an hour earlier for the Cashio findings — that they vanished because the fixed
variant is dead code — was wrong, and has been corrected in place. The case is still invalid; that
was established by reading the diff, which is why the conclusion survived an explanation that did
not.

**Three of ten cases could not be measured at all.** Radar exceeds its own retry budget above
roughly a hundred files, and on one case the vulnerable variant completed while the fixed one did
not, which makes the pair useless even though half of it worked. Recorded as unavailable. When it
gives up it still prints `Results written to <path>` for a file it did not write, which is the
identical bug we made ourselves in error 16, twelve hours apart, in opposite directions.

---

## Part 14: the headline rested on one case, and the harness hid it both ways

**Error 20, the worst of the day, because it was the headline.** The published claim that Radar
detects 0 of 8 real vulnerabilities was **extrapolated from one case**. Every Radar artefact in the
repository was either the teaching corpus, complete and properly evidenced, or **Wormhole alone,
twice**: once as an isolated file, once as the real crate. `c2clean-radar.json`, which reads as a
cleaned corpus-2 run, is not one at all - its paths are `/tmp/whreal/`. VaultLint's corpus-2 file
covers `solend-owner-checks` only.

The cause was mechanical and invisible. **Radar requires a `Cargo.toml` in a subdirectory of the
path it is given.** Corpus-2 cases carry their manifest at the root, so it answers
`400 Bad Request: No Cargo.toml files found in any subdirectories` and analyses nothing. Wormhole
passed on the accident of its layout; the real crates passed because the crate is nested. Every
other case was an invocation error being recorded as a miss.

**Retracted in public before the replacement data existed**, because leaving an unsupported claim
standing while gathering better numbers is the wrong order.

Re-measured with the corpus wrapped one level deeper: **18 runs, 18 successes, zero unavailable,
238 findings, all nine cases.** The conclusion held - 0 detected of 8 valid cases - but the detail
did not. The old text said the mapped rule "never fired at all" on eight of nine. It fires in the
right file on two of them, just not where the fix changed anything. Those are `unlocated`. Being
right about the headline while wrong about the mechanism is still being wrong.

**Error 21, mine, in the opposite direction and within the same hour.** The new harness marked
`anchor-interface-account/insecure` **unavailable**. Radar had run it perfectly: 57 templates, one
file scanned, `completed successfully. No results found.` It wrote no JSON, and my script read a
missing file as a failed run. So after a full day of insisting that "could not run" and "found
nothing" must never be confused, I confused them myself, in the tool built to stop exactly that.

**What survived the audit, stated as loudly as what did not.** Corpus 1 is properly evidenced:
`runs/2026-08-31.json` carries per-class records for radar (11), sol-audit (13) and vaultlint (11),
all `measured`, and X-Ray's log shows 35 leaves across 11 classes, all `ok`. The real-crate results
stand, because that run wrote a log per run. The pattern is exact: **everything that held up had a
per-run artefact; everything that collapsed had been inferred from a summary.**

---

## What the day produced

Two public repositories, a benchmark with four scanners and two calibration controls, two corpora,
a monthly clock that has already published a run, and a limitations document that opens with our own
error.

**And the finding, in the form it survived the evening's two corrections:** on a curated public
corpus a tool scores 11/11; on eight real vulnerabilities that same tool, measured the same day with
the same protocol, detects nothing. Across all six scanners there is exactly one real detection, and
our own mapping was hiding it. The corpus everyone
uses has stopped separating tools that generalise from tools that have done their homework, and we
watched the homework being done.

## What is still wrong

In `docs/KNOWN-LIMITATIONS.md`, kept current. Corpus 2 pairs still contain files the fix touched that
have nothing to do with the bug. The right of reply has not been exercised with any vendor. Nine
cases is a small corpus. And nobody outside this project has yet said they want any of this data.
