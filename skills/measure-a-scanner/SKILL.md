---
name: measure-a-scanner
description: Use when adding a new security scanner to the ScannerTruth benchmark, or when asked to measure, benchmark or compare a code scanner against the corpora. Enforces provenance checks before install, container isolation, a written mapping before scoring, and the separation of "could not run" from "found nothing".
---

# Measuring a scanner

Adding a scanner to the benchmark is the project's one repeatable unit of work. It has been done
six times and the same four mistakes are available every time. This is the order that avoids them.

Repo: `github.com/halobartku/scannertruth`. Protocol: `PROTOCOL.md`.

## The rule that outranks the rest

**A number you did not verify at its source is not a result.** Not the tool's summary line, not a
subagent's report, not a previous run's notes. Open the raw output and count. Every published
figure in this project was recomputed from raw JSON before it went in a table, and doing so caught
a real error at least twice.

## 1. Provenance, before anything is downloaded

`cargo install <name>` nearly installed an unrelated 2021 crate by a different author, because the
real tool was not published to that registry at all. That would have measured a random package and
called it a competitor.

- Find the tool's **own repository** first and take the install path it documents.
- Check the registry name actually maps to that repo: author, repo link, publish date, downloads.
- If an install script is piped to a shell, **download and read it in full first**. Say so, and say
  what it does, before running it.
- Name mismatch, or a package whose repo does not mention the tool: stop and report. Do not guess.

## 2. Run it in a container, never on the host

Standing constraint from Bartosz: nothing untrusted executes on the host or bare on the VPS.

- Prefer the tool's official image; otherwise build inside `rust:slim` or equivalent.
- Mount the corpus **read-only**.
- Some tools orchestrate their own containers. Fine, but confirm what they pull.

## 3. Give the tool what it expects before judging it

Radar returned `400 Bad Request` on a bare `.rs` file until a `Cargo.toml` was supplied. Reporting
that as a zero would have been measuring our packaging, not the tool.

- Supply a manifest, workspace, or build artefact if the tool needs one.
- Record the first failed attempt anyway; do not quietly replace it with the successful run.
- If it needs something the corpus cannot provide (Anchor IDL, a paid API key, a toolchain that
  will not build), it goes in the **could-not-run** table with the reason. That table is published.

## 4. Write the mapping down before you score

`mappings/<scanner>.json` maps the tool's rule ids to the eleven vulnerability classes. It is
written **from the tool's own documentation and rule names**, before any score is computed, so the
mapping cannot be tuned until it flatters or damns anyone.

- Use the ids the tool actually emits. Ours emits `SOL-001`, not the semantic names first guessed.
- No rule for a class is `no-rule`: a coverage gap, not a failed detection. Keep them distinct.
- The mapping is an interpretation of somebody else's work, so it is **offered to the tool's
  authors for correction** (`PROTOCOL.md`, right of reply). Results are provisional until then.

## 5. Score with the scorers, not by eye

```
python score.py  --scanner <name> --findings <raw>.json        # corpus 1, teaching
python score2.py --scanner <name> --kind <name> --findings c2-<name>.json   # corpus 2, real
python score.py --demo && python score2.py --demo              # self-checks first
```

- **Nominal recall**: the mapped rule fires on the vulnerable variant.
- **Real recall**: nominal **and silent on the same program fixed.** This is the only number that
  means anything. The gap between the two is what the project exists to show.
- Corpus 2 additionally requires the finding to land **where the fix changed something**, within a
  line tolerance. A mapped rule firing elsewhere in the file is `unlocated` — neither a detection
  nor a clean miss, and the category exists so the author cannot quietly pick the flattering one.

## 6. Check the controls, every time

`control-noisy` flags every non-empty line: 931 findings, 11/11 nominal, **0/11 real.** If a run
ever shows it scoring above zero on real recall, the harness is broken, not the control. It is the
proof that no score was bought with volume.

Run each scanner **twice** and compare findings by rule and location before trusting anything over
time. Radar 52 = 52, VaultLint 4 = 4.

## 7. Publish the uncomfortable number first

- A third-party tool beating ours goes in the **first paragraph**. Radar's 11/11 does.
- A tool whose claim the measurement **confirms** gets said plainly. VaultLint's precision held.
- Missing raw output is recorded as **unavailable, never as zero.** A history that conflates "we
  could not run it" with "it found nothing" will eventually report a regression that was our own
  harness breaking.
- Add what is still wrong to `KNOWN-LIMITATIONS.md` in the same commit, not later.

## Red flags

| Thought | Reality |
|---|---|
| "The tool printed a summary, I'll use that" | Open the raw output and count. |
| "The agent reported 4/11, good enough" | Rerun the scorer yourself. It has been wrong. |
| "It found nothing, so it scores zero" | Only if it ran. Otherwise it is unavailable. |
| "This symbol is present, so the check exists" | `declare_id!` is present in every Anchor program and guards nothing. Presence is not a check. |
| "I'll adjust the mapping so the result makes sense" | The mapping is written before scoring, and it is theirs to correct, not ours to tune. |
| "One case is enough to say scanners don't work" | n=1 is a direction to test, never a headline. |
