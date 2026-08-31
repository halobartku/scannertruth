# Engineering log, 2026-08-31

Everything that happened on the day this benchmark was built, in order, including every mistake.

This exists because the project's only real asset is that its numbers can be checked, and a reader
who cannot see how a number was produced has to take it on faith. Sixteen errors are recorded
below. Twelve were caught by measurement or by a check, four by a person noticing. Two would have
put a false statement in a funding application.

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

The submitted application referenced `PROTOCOL.md` and a public repository with the benchmark
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

## What the day produced

Two public repositories, a benchmark with four scanners and two calibration controls, two corpora,
a monthly clock that has already published a run, and a limitations document that opens with our own
error.

**And the finding:** on a curated public corpus a tool scores 11/11; on nine real vulnerabilities
that same tool, measured the same day with the same protocol, detects nothing. The corpus everyone
uses has stopped separating tools that generalise from tools that have done their homework, and we
watched the homework being done.

## What is still wrong

In `KNOWN-LIMITATIONS.md`, kept current. Corpus 2 pairs still contain files the fix touched that
have nothing to do with the bug. The right of reply has not been exercised with any vendor. Nine
cases is a small corpus. And nobody outside this project has yet said they want any of this data.
