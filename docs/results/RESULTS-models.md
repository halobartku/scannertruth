# Two model-backed auditors, both corpora, 2026-09-01

Run with `tools/model_audit.py`, prompt version `v1-2026-09-01` (verbatim in the engineering log),
temperature 0, three invocations per case per variant, one JSON line written per invocation before
it returned. Raw logs in `raw/model-*-c*-2026-09-01/runs.jsonl`.

**Why this page exists.** On 2026-09-01 an outside reviewer ran this repository and asked why we
benchmark static scanners when AI is available. It is the best question the project has had, and
this is the answer we could produce the same evening with two free local models.

## The table

| | Teaching corpus (frozen 2022-07-16) | Real vulnerabilities |
|---|---|---|
| `qwen3.5:9b` | **6 / 11** verdict right | **2 / 17** verdict right, **0** after the class check |
| `gemma4:12b` | **7 / 11** verdict right | **0 / 17** |

**"Verdict right" is not a detection.** It means the model called the vulnerable program vulnerable
and stayed silent on the same program after its maintainers fixed it. Whether it is a detection
depends on it naming the class that is actually present, and that is where both models fall apart.

## What the models named, which is the whole story

`gemma4:12b` on the teaching corpus returned **"Missing Ownership Check" for five different
vulnerability classes**: signer-authorization, account-data-matching, owner-checks, initialization,
and arbitrary-cpi. One phrase, applied to almost anything that looks unfixed, silent on code that
looks fixed. It scores 7 out of 11 on the verdict and is right about *what* it found roughly once.

**That is the model-shaped version of `control-noisy`.** Our noisy control flags every line, scores
11/11 nominal and 0/11 real. Gemma flags almost every unfixed program with one stock phrase. The
mechanism is different and the failure is identical: a detector that cannot distinguish between
classes has not detected a class.

`qwen3.5:9b` is more discriminating and still fails the check. It returned `"Arbitrary CPI"` and
`"DuplicateMutableAccounts"` verbatim - the second in CamelCase, matching the corpus directory name
character for character - and then called `4-initialization` "Reentrancy" and `8-pda-sharing`
"Missing Authority Check".

## The finding that is new, and it is about the corpus rather than the models

Both models do markedly better on the corpus frozen in 2022 than on real vulnerabilities, which is
exactly the pattern all seven static scanners showed. **But the mechanism is different and worse.**

A static scanner can be **tuned** against a public corpus. That is the criticism we have been
making since the first measurement. A model can have **memorised** it. `sealevel-attacks` has been
public since 2022 with the vulnerability class written into each directory name, surrounded by four
years of tutorials and blog posts quoting it. A model returning `DuplicateMutableAccounts` in the
corpus's own CamelCase is not evidence of analysis.

**So measuring an AI auditor on the teaching corpus measures recall of the internet, not capability
on code.** Anyone benchmarking an AI auditor against `sealevel-attacks` today - and it is the
obvious corpus to reach for - is producing a number that means less than it appears to.

This is a claim about two models under one prompt at one temperature. It replicates across both,
which is why it is written down as a finding rather than a suspicion, and it is exactly the kind of
claim that a vendor with a stake should be invited to falsify.

## Recorded against our own roadmap

Milestone 3 argues non-determinism is the hard part of measuring models. **At temperature 0 there
was almost no spread**: nearly every cell came out 3/3 or 0/3 across both models and both corpora,
the single exception being `gemma4:12b` on `8-pda-sharing` (fixed variant, 1 of 3). The claim needs
narrowing to non-zero temperature and to tools that do their own retrieval, rather than repeating.

## What this does not show

- **One prompt, and a deliberately plain one.** A prompt tuned for recall would score higher. A
  prompt tuned against this corpus would be the homework-tuning we criticise in vendors. The
  version string exists so a better prompt is a *new* measurement, not a quiet replacement.
- **Two small local models.** Nothing here licenses a claim about frontier models, which is the
  measurement that would actually matter and which we have not run.
- **A verdict-and-class protocol, not a located finding.** Static scanners are scored on where they
  fire. Models are not asked for a location yet.
