# Getting started

Two paths. Pick the one that describes you.

- **A person** who wants to check whether a scanner actually detects anything: start below.
- **An AI agent** handed this repository and told to measure something: read
  [`AGENTS.md`](../AGENTS.md) instead. It is the complete procedure, and the short version is here in
  section 4.

---

## 0. What you need. Genuinely almost nothing.

**To verify every published number: Python 3 and nothing else.** No pip install, no virtualenv, no
network, no Docker, no API key. Verified by counting the imports: **every dependency is in the
Python standard library.**

| To do this | You need |
|---|---|
| **Reproduce our published results** | Python 3.9+ (CI runs 3.11). That is all. |
| Grow the corpus from advisory databases | + network access to `api.github.com` |
| Rebuild the corpus from source repositories | + `git` and network |
| **Run a third-party scanner yourself** | + Docker, because untrusted code never touches the host |
| Run our own `sol-audit` | + the [sol-audit](https://github.com/halobartku/sol-audit) repo on `PYTHONPATH`, optional |

The repository is about 49 MB, most of it corpus files and raw scanner output kept so that every
number can be re-derived rather than believed.

**Deliberately no dependencies.** A benchmark whose results cannot be reproduced because a package
version drifted is not a benchmark. If you can run `python`, you can check our work.

---

## 1. Check that our numbers are real. Two minutes, offline.

```bash
git clone https://github.com/halobartku/scannertruth
cd scannertruth

python test_all.py        # 122 checks on the code that produces every published figure
python tools/verify.py          # re-derives a published result from the raw data
python tools/control_c2.py      # the calibration controls must score zero
```

**What you should see.** `test_all.py` ends with `122 passed, 0 failed`. `verify.py` prints a table
and `OK: raw data reproduces the published result`. `control_c2.py` prints
`CONTROLS PASS: noisy scores 0 despite 2,392,280 findings`.

**What that last one means, and it is the important one.** We keep a fake scanner that flags every
non-empty line of every file. It produces 2,392,280 findings, so any ranking based on counting
findings would put it first. Our metric gives it **zero**. If it ever scored above zero, our metric
would be broken, and you just checked that it is not.

---

## 2. Read the results

| File | What is in it |
|---|---|
| [`docs/results/RESULTS-all.md`](../docs/results/RESULTS-all.md) | Six scanners, both corpora, one table |
| [`docs/results/RESULTS-realcrates.md`](../docs/results/RESULTS-realcrates.md) | The same bugs as whole projects, not extracted files |
| [`docs/PROTOCOL.md`](../docs/PROTOCOL.md) | The rules, including what makes a result provisional |
| [`docs/KNOWN-LIMITATIONS.md`](../docs/KNOWN-LIMITATIONS.md) | What this measurement cannot tell you |
| [`docs/ENGINEERING-LOG-2026-08-31.md`](../docs/ENGINEERING-LOG-2026-08-31.md) | 21 of our own errors, with dates |

**Read the limitations before quoting any number**, and read the log if you want to know whether to
trust us at all. It records the same reaction when a measurement damaged a competitor and when it
flattered us.

---

## 3. The one concept you need

Not "how many findings does the tool produce". That is easy to inflate and tells you nothing.

**Real recall: does the tool's rule fire on a vulnerable program AND stay silent on the same program
after its authors fixed it?**

A rule that fires on both has not detected a bug. It has recognised a shape of code that also exists
in working software. That single distinction is what separates every number in this repository from
the numbers a vendor prints on a landing page.

---

## 4. Measure a scanner yourself

**[`docs/WALKTHROUGH.md`](../docs/WALKTHROUGH.md) is the step-by-step**, written for a person, with every command
and what you should see. It measures a tool we have already measured, so you can compare your result
to ours and know whether you did it right. About 40 minutes, most of it a container build.

It covers the parts that are easy to get wrong, because we got them wrong:

- **Find the tool's real home first.** A registry name nearly made us measure an unrelated crate by
  a different author and call it a competitor.
- **Write the mapping before you run anything**, and commit it on its own. The timestamp is what
  stops you quietly adjusting it once you dislike the score.
- **Run per case, per variant, with a log per run.** A findings file cannot prove a case was
  analysed: a tool that ran and found nothing leaves the same silence as one that never saw it.
  Skipping this is what forced us to retract a published headline.
- **Classify a clean zero and an outage differently.** We have made that mistake in both directions,
  hours apart.

An AI agent given this repository should read [`AGENTS.md`](../AGENTS.md) instead, which is the same
procedure written to be executed unsupervised.

## 5. If you find something wrong

Open an issue. If a number here is wrong we will fix it and say that we did, in the engineering log,
with the date. That has happened repeatedly and the record is public.

If you are the author of a tool we measured: the mapping of your rules is our reading of your work.
[`docs/PROTOCOL.md`](../docs/PROTOCOL.md) gives you a right of reply, and **every third-party number here is
provisional until you use it.** We already understated one tool through a mapping error we made
ourselves, so this is not a formality.
