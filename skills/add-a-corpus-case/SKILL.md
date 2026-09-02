---
name: add-a-corpus-case
description: Use when adding a vulnerability to a benchmark corpus, acquiring candidate cases from advisory databases, or deciding whether a fix commit can serve as ground truth. Enforces that the fix actually fixes the bug, that scope is judged in writing, and that selection bias is disclosed.
---

# Adding a corpus case

**The corpus is the asset.** The scoring rules in `PROTOCOL.md` are copyable in an afternoon; ground
truth has to be acquired, checked, and defended. The teaching corpus everyone else uses was last
touched 2022-07-16, so anything measured only on it measures homework.

This is the other half of `measure-a-scanner`. Running a tool and building the thing you run it
against are different jobs with different ways of going wrong.

## 0. Run the suite first

```bash
python test_all.py     # 156 checks, several of which guard the corpus itself
```

Among them: every case must name its fix commit, its repository and its class; case names must be
unique or a denominator double-counts; pinned paths must be relative Rust files; an excluded case
must carry a reason long enough to audit; and an unreleased holdout spec must not be sitting in the
repository, because a sealed spec you can read is not sealed.

## 1. Acquire from structured sources, not from prose

The first acquisition tool searched the open web for postmortems: 23 queries, one hit, false. The
design was wrong, not the effort. **A postmortem puts its fix commit in the page body, and a search
snippet never contains it.**

Advisory databases are the right source because the fix is a *field*: `corpus_ghsa.py` reads GitHub
Security Advisories and RustSec, where an advisory names the affected package and links its fix.

- Match on the advisory's **own package and summary fields**, never the raw JSON blob. Matching the
  blob made `gix-packetline` a Solana hit because `spl-` appeared inside unrelated text.
- **Rate limiting is an incomplete scan, never an absence of candidates.** Say which it was.
- The tool **proposes**. It never adds a case.

## 2. Read the fix commit. This is the step that cannot be skipped.

**A commit labelled as the fix is not evidence that it fixes anything.**

`cashio-account-data` was accepted, published, and later thrown out. Its "fix" adds
`vipers::invariant!(false, "temporarily disabled")` to two functions: it **switches the program
off**. The secure variant is dead code, so any detection there would have been spurious. `git log`
confirmed there was no other candidate: three commits in the repository's history touch that file,
this was the last, and everything after the exploit is a dependency bump.

Before accepting a case, read the diff and answer:

- Does the change **add or repair a check**, or does it disable, delete or bypass the code path?
- Is the vulnerable variant genuinely vulnerable? One "fix" removed a guard that the *parent* had,
  because the commit was a later refactor rather than the repair.
- Does the commit touch non-test `.rs` files at all?
- Is the SHA a **merge commit**? `git show` without `-m` prints the combined diff and omits files
  identical to either parent, which once caused a case to be recorded as "skipped, no implicated
  file" when the file was right there.

Scan for shutdown-shaped fixes mechanically (`invariant!(false`, `unimplemented!`, `panic!`,
`return Err` with no added condition, "temporarily disabled") **and then read it anyway**. The
mechanical scan flags candidates; it does not decide.

## 3. Judge scope, in writing, including the rejections

A real vulnerability with a real fix can still be the wrong case. `kora-lib` had both, and was
rejected: it is a relayer, ordinary server Rust, not an on-chain program. Scoring contract scanners
against a server library produces misses that say nothing about what they claim to do. The
`solana_rbpf` advisories were rejected one layer lower: that is the VM that *executes* programs.

**Write the rejection and its reason into `CANDIDATES-TRIAGE.md`.** "We found it and chose not to
use it" and "we never found it" must never look the same from outside.

## 4. Pin exactly what the disclosure implicates

- Derive file paths **from the commit**, never type them from notes.
- Pin the single implicated file per case, with a written reason for every exclusion. Before this,
  Bubblegum carried 6 files and Wormhole 3, most of them unrelated: Wormhole's fix commit is a
  monorepo-wide `solana-program` version bump.
- Record the corpus commit, and if you recovered it after the fact, say so.
- Mark an unusable case `valid: false` **with its reason, and keep it**. Deleting it hides that the
  mistake happened. The scorer refuses to score anything marked that way, because a note in a
  manifest does not stop the next run from counting it. Since 2026-09-01 the scanner framework
  reads the manifest on every invocation and skips those cases too, so the flag now removes a case
  from the runs as well as from the scores.
- A case listed but **not built** must be reported as `not-built`, not silently skipped. Skipping
  shrank a denominator from nine to eight and nothing said so. Both `score2.py` and `run_all.py`
  now print it on its own line, and they agree on which cases exist: two components disagreeing
  about the denominator is how a number drifts without anyone noticing.

## 5. Disclose the bias, because it is real and it favours nobody

Every case here comes from a public postmortem, audit or advisory. **Those incidents are famous
precisely because nobody caught them in time.** A corpus assembled from the bugs that got through is
systematically harder than the population of real bugs and **understates every scanner measured on
it**.

That makes it the right corpus for "do these tools catch the ones that cost money" and the wrong
one for "these tools do not work". Nothing built from it may claim the second.

## 6. Two variants, one difference, and a holdout that is sealed

- The pair must differ by the fix and as little else as possible.
- Extracting a lone file into a synthetic manifest is **packaging you invented**; a tool needing
  project context is then penalised for your choice. Build the real crate too and compare.
- A holdout is worthless if it can be picked or edited after seeing scores. Commit `sha256` over the
  canonical spec **before** the run (`holdout.py`), release the spec when the round publishes. State
  plainly whether a given round gives concealment or only timestamp integrity.

## Red flags

| Thought | Reality |
|---|---|
| "The advisory says this commit is the fix" | Read the diff. One "fix" disabled the program. |
| "Findings vanish from the secure variant, so it was detected" | A fix that inserts lines moves every finding below it. Compare shift-aware. |
| "It's Rust and it's Solana, so it belongs" | A relayer and a VM are not on-chain programs. Write the rejection down. |
| "The case isn't built yet, I'll just skip it" | Report `not-built`. A silent skip shrinks the denominator. |
| "Deleting the bad case keeps the corpus clean" | Keep it marked invalid. The record of the mistake is the point. |
| "A corpus of famous hacks is a representative sample" | It is a sample of what nobody caught. Say so before quoting any number from it. |
