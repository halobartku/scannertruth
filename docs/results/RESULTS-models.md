# Model-backed auditors, both corpora, 2026-09-01 and 2026-09-02

Run with `tools/model_audit.py`, prompt version `v1-2026-09-01` (verbatim in the engineering log),
temperature 0 where the provider exposes it (the Claude Code CLI does not; those rows ran at its default), three invocations per case per variant, one JSON line written per invocation before
it returned. Raw logs in `raw/model-*-c*-2026-09-01/runs.jsonl`.

**Why this page exists.** On 2026-09-01 an outside reviewer ran this repository and asked why we
benchmark static scanners when AI is available. It is the best question the project has had, and
this is the answer we could produce the same evening with two free local models.

## The table

| | Teaching corpus (frozen 2022-07-16) | Real vulnerabilities |
|---|---|---|
| `qwen3.5:9b` | **6 / 11** verdict right | **2 / 17** verdict right, **0** after the class check |
| `gemma4:12b` | **7 / 11** verdict right | **0 / 17** |

That table is the history of the first evening, two local models under the suppressed regime,
and it stays as written. Every model run since, including the frontier models and the reasoning
regimes, is in the derived table at the bottom of this page, with the class each model named
adjudicated strict and lenient.

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
- **Two small local models on 2026-09-01.** The first evening ran only qwen3.5:9b and gemma4:12b
  and licensed no claim about frontier models. The table below now holds frontier rows (2026-09-02,
  regimes kept apart, several still incomplete); the zero of this section is the local-model zero.
- **A verdict-and-class protocol, not a located finding.** Static scanners are scored on where they
  fire. Models are not asked for a location yet.

## Every model run so far, derived from the artefacts

Generated by `python tools/model_results.py` from `raw/model-*/runs.jsonl` and
`mappings/model-classes.json` on 2026-09-02 13:45 CEST; re-run it rather than editing the table.
Regimes: `suppressed` (reasoning refused, 400-token belt, the 2026-09-01 rows), `allowed` or
`requested` (reasoning free, 128,000-token ceiling, from 2026-09-02), `effort high` or `effort max`
(Claude Code subscription harness). Rows from different regimes are never merged. `IN PROGRESS`
rows are sweeps still running when the table was generated; their counts are over the cases seen so
far, not over the corpus. `partial` and `calibration` rows are kept as artefacts and are not sweeps.

**"Verdict right" is necessary and not sufficient.** It says the model called the vulnerable
variant vulnerable on at least one valid run and never called the fixed variant vulnerable. It
becomes a detection only if the class the model named is the class present, and that is the
"detections after adjudication" column. The adjudication rule, set by the owner on 2026-09-02: **a
named class counts when it names the mechanism or a clear synonym of it; naming only the effect
does not count.** "Unverified instructions sysvar account" for `sysvar-address-checking` counts;
"missing signature verification" for the same case is the effect and does not; "reentrancy" for
`cpi-recursion` is arguable and is recorded as disputed. **Strict** counts only the cases whose
named class counts; **lenient** adds the disputed ones. Every phrase, its verdict and the reason
are in `mappings/model-classes.json`, one rule per phrase per real class, so the same phrase for
the same class is judged the same way everywhere and anyone can dispute a line. The spread between
strict and lenient is the size of that judgement.

**On real vulnerabilities, corpus 2, adjudicated, strongest first.**

- **`claude-opus-5`, Claude Code harness, effort max: 10 strict / 10 lenient of 17.** Eleven
  verdict-right; the one that falls at adjudication is `metaplex-token-metadata`, where it named a
  lock-state check rather than the missing binding between mint, token and owner. Its ten named
  classes read as the mechanism: "unverified instructions sysvar", "missing account discriminator
  check (type confusion)", "missing program ID validation", "missing owner/program validation on
  the token-swap pool (unchecked CPI target)", "rounding direction / precision loss". **This row is
  partial.** Only 14 of the 17 cases have a usable answer on both variants; the sweep shared the
  owner's Claude subscription window with the session that supervised it, the window ran out at
  about 03:15 CEST, and 118 of the 204 lines in the directory are the limit message (error 43).
  The corpus-1 row for Opus is 132 limit messages and no measurement at all.
- **`glm-5.3`, Z.ai coding plan, reasoning allowed: 5 strict / 6 lenient of 17**, from 12
  verdict-right. Half of its right verdicts came with the wrong class: "flash loan / reentrancy" and
  "oracle price manipulation" for the missing owner check in Solend, "integer overflow" for the
  rounding drain in token-lending, "improper input validation" for the rounding drain in the stake
  pool, "instruction replay" for the recursive execute. The disputed one is
  `solido-deposit-reserve-account`, where "unchecked reserve account" names the right account and
  not the missing derivation check. 15 of 17 cases have a usable pair; 9 of 102 answers were
  unusable.
- **`claude-fable-5-1`, Claude Code harness, effort max: 5 strict / 5 lenient of the 7 cases it
  covered**, from 6 verdict-right. The same subscription window: 43 valid answers, then 59 limit
  messages, so 10 of 17 cases have no usable pair and this is not a corpus number. Its corpus-1 row
  is 66 limit messages, not a measurement.
- **`deepseek-v4-flash`, reasoning requested: 2 strict / 3 lenient of 17**, from 5 verdict-right;
  the disputed one is "reentrancy" for `squads-recursive-execute`. With reasoning allowed or
  suppressed the same model is 1 / 1 of 17 in both regimes: one of its two right verdicts each time
  named the effect ("missing signature verification" for the Wormhole sysvar) or a different
  mechanism ("missing signer check" for the stake-pool fee rounding).
- **`qwen3.5-397b`, reasoning allowed: 2 strict / 3 lenient of 17** (USD 4.27), from 5
  verdict-right; the disputed one is "missing owner verification" for `metaplex-token-metadata`,
  which is the check the fix adds under the name of a different class. Suppressed, the same model is
  0 / 0 of 17.
- **`devstral-2512`, reasoning allowed: 0 strict / 1 lenient of 17**, from 4 verdict-right, the
  highest verdict count of any OpenRouter model and every one of them the wrong class: "reentrancy"
  for the Wormhole sysvar, "integer overflow" for the rounding drain, "missing account validation"
  for the candy-machine introspection; the lenient one is "reentrancy" for the recursive execute.
- **`qwen3.5:9b` and `gemma4:12b`, local, suppressed: 0 / 0 of 17.** These are the two rows of the
  table at the top of this page.

So the sentence "no model detects a real vulnerability" was true of the two local models under the
suppressed regime and is not true of the reasoning regimes: under the adjudication rule Opus reaches
ten of the fourteen cases it answered, and glm-5.3 five of seventeen, on prompt v1 with no tuning.
The teaching-corpus columns say what they said before, only more so: `deepseek-v4-flash` with
reasoning allowed is 8 / 8 of 11 and `qwen3.5-397b` suppressed is 9 / 10 of 11 on a corpus whose
class names have been public since 2022, and the memorisation caveat above applies to every corpus-1
figure.

**Two rows are not sweeps and are kept for what they show.** `moonshotai/kimi-k2.7-code` with
reasoning allowed thought 409,758 to 601,622 characters on three of its first eight calls, hit the
128,000-token ceiling or a provider error and returned no answer (one call took 1,604 s); the sweep
was stopped by hand after nine calls and the directory kept with a README. `deepseek-v4-flash` with
reasoning requested scores 7 / 11 on the teaching corpus, the same as with reasoning suppressed, so
on that corpus thinking changed nothing for that model.

| directory | model | provider | corpus | regime | calls | verdict right (necessary, not sufficient) | detections after adjudication (strict / lenient) | unusable | reasoned | cost USD |
| `model-anthropic-claude-fable-5.1-or-c2-2026-09-01` | anthropic/claude-fable-5.1 | openrouter | 2 | suppressed | IN PROGRESS 2/34 | 1 / 1 seen | 1 / 1 | 0 | 0 | 0.249 |
| `model-claude-fable-5-1-cc-c1-2026-09-02` | claude-fable-5-1 | claude-code | 1 | effort max | complete | 0 / 11 seen | 0 / 0 | 66 | 0 | 0.0 |
| `model-claude-fable-5-1-cc-c2-2026-09-01-calibration` | claude-fable-5-1 | claude-code | 2 | effort high (calibration) | IN PROGRESS 2/34 | 1 / 1 seen | not a sweep | 0 | 0 | 0.183 |
| `model-claude-fable-5-1-cc-c2-2026-09-01-partial` | claude-fable-5-1 | claude-code | 2 | effort high (partial, not a sweep) | IN PROGRESS 44/102 | 7 / 8 seen | not a sweep | 0 | 0 | 6.258 |
| `model-claude-fable-5-1-cc-c2-2026-09-01` | claude-fable-5-1 | claude-code | 2 | effort max | complete | 6 / 17 seen | 5 / 5 | 59 | 0 | 57.103 |
| `model-claude-opus-5-cc-c1-2026-09-02` | claude-opus-5 | claude-code | 1 | effort max | complete | 0 / 11 seen | 0 / 0 | 132 | 0 | 0.0 |
| `model-claude-opus-5-cc-c2-2026-09-01-calibration` | claude-opus-5 | claude-code | 2 | effort high (calibration) | IN PROGRESS 2/34 | 1 / 1 seen | not a sweep | 0 | 0 | 0.099 |
| `model-claude-opus-5-cc-c2-2026-09-02` | claude-opus-5 | claude-code | 2 | effort max | complete | 11 / 17 seen | 10 / 10 | 118 | 0 | 21.495 |
| `model-deepseek-deepseek-v4-flash-or-c1-2026-09-01` | deepseek/deepseek-v4-flash | openrouter | 1 | suppressed | complete | 7 / 11 seen | 6 / 6 | 0 | 0 | 0.003 |
| `model-deepseek-deepseek-v4-flash-or-c1-2026-09-02` | deepseek/deepseek-v4-flash | openrouter | 1 | allowed | complete | 8 / 11 seen | 8 / 8 | 1 | 48 | 0.055 |
| `model-deepseek-deepseek-v4-flash-or-c2-2026-09-01-partial` | deepseek/deepseek-v4-flash | openrouter | 2 | suppressed (partial, not a sweep) | IN PROGRESS 53/102 | 0 / 9 seen | not a sweep | 0 | 0 | 0.018 |
| `model-deepseek-deepseek-v4-flash-or-c2-2026-09-01` | deepseek/deepseek-v4-flash | openrouter | 2 | suppressed | complete | 2 / 17 seen | 1 / 1 | 0 | 0 | 0.04 |
| `model-deepseek-deepseek-v4-flash-or-c2-2026-09-02` | deepseek/deepseek-v4-flash | openrouter | 2 | allowed | complete | 2 / 17 seen | 1 / 1 | 1 | 68 | 0.168 |
| `model-deepseek-deepseek-v4-flash-think-or-c1-2026-09-02` | deepseek/deepseek-v4-flash | openrouter | 1 | requested | complete | 7 / 11 seen | 7 / 7 | 0 | 66 | 0.019 |
| `model-deepseek-deepseek-v4-flash-think-or-c2-2026-09-01-partial` | deepseek/deepseek-v4-flash | openrouter | 2 | requested (partial, not a sweep) | IN PROGRESS 17/102 | 0 / 2 seen | not a sweep | 0 | 17 | 0.01 |
| `model-deepseek-deepseek-v4-flash-think-or-c2-2026-09-01` | deepseek/deepseek-v4-flash | openrouter | 2 | requested | complete | 5 / 17 seen | 2 / 3 | 4 | 102 | 0.188 |
| `model-gemma4-12b-c1-2026-09-01` | gemma4:12b | ollama | 1 | suppressed | complete | 7 / 11 seen | 0 / 0 | 0 | 0 | 0.0 |
| `model-gemma4-12b-c2-2026-09-01` | gemma4:12b | ollama | 2 | suppressed | complete | 0 / 17 seen | 0 / 0 | 0 | 0 | 0.0 |
| `model-glm-5.3-zai-c1-2026-09-02` | glm-5.3 | zai | 1 | allowed | complete | 6 / 11 seen | 5 / 6 | 17 | 49 | 0.0 |
| `model-glm-5.3-zai-c2-2026-09-01` | glm-5.3 | zai | 2 | allowed | complete | 12 / 17 seen | 5 / 6 | 9 | 94 | 0.0 |
| `model-mistralai-devstral-2512-or-c1-2026-09-02` | mistralai/devstral-2512 | openrouter | 1 | allowed | complete | 9 / 11 seen | 5 / 6 | 0 | 0 | 0.013 |
| `model-mistralai-devstral-2512-or-c2-2026-09-02` | mistralai/devstral-2512 | openrouter | 2 | allowed | complete | 4 / 17 seen | 0 / 1 | 0 | 0 | 0.085 |
| `model-moonshotai-kimi-k2.7-code-or-c2-2026-09-02` | moonshotai/kimi-k2.7-code | openrouter | 2 | allowed | IN PROGRESS 9/102 | 0 / 2 seen | 0 / 0 | 3 | 9 | 0.653 |
| `model-qwen-qwen3.5-397b-a17b-or-c1-2026-09-01` | qwen/qwen3.5-397b-a17b | openrouter | 1 | suppressed | complete | 10 / 11 seen | 9 / 10 | 0 | 4 | 0.085 |
| `model-qwen-qwen3.5-397b-a17b-or-c1-2026-09-02` | qwen/qwen3.5-397b-a17b | openrouter | 1 | allowed | complete | 8 / 11 seen | 7 / 8 | 3 | 64 | 1.626 |
| `model-qwen-qwen3.5-397b-a17b-or-c2-2026-09-01-partial` | qwen/qwen3.5-397b-a17b | openrouter | 2 | suppressed (partial, not a sweep) | IN PROGRESS 11/102 | 1 / 2 seen | not a sweep | 0 | 1 | 0.054 |
| `model-qwen-qwen3.5-397b-a17b-or-c2-2026-09-01` | qwen/qwen3.5-397b-a17b | openrouter | 2 | suppressed | complete | 1 / 17 seen | 0 / 0 | 3 | 7 | 0.456 |
| `model-qwen-qwen3.5-397b-a17b-or-c2-2026-09-02` | qwen/qwen3.5-397b-a17b | openrouter | 2 | allowed | complete | 5 / 17 seen | 2 / 3 | 4 | 99 | 4.271 |
| `model-qwen3.5-9b-2026-09-01` | qwen3.5:9b | ollama | None | suppressed | complete | 2 / 17 seen | 0 / 0 | 0 | 0 | 0.0 |
| `model-qwen3.5-9b-c1-2026-09-01` | qwen3.5:9b | ollama | 1 | suppressed | complete | 6 / 11 seen | 2 / 2 | 0 | 0 | 0.0 |
| `model-qwen3.5-9b-think-c1-2026-09-01` | qwen3.5:9b | ollama | 1 | requested | IN PROGRESS 2/22 | 0 / 1 seen | 0 / 0 | 2 | 2 | 0.0 |
| `model-qwen3.5-9b-think-c2-2026-09-01` | qwen3.5:9b | ollama | 2 | requested | IN PROGRESS 1/34 | 0 / 1 seen | 0 / 0 | 1 | 0 | 0.0 |
