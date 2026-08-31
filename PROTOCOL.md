# PROTOCOL

The scoring rules for this benchmark, and an honest account of what was fixed before running,
what was corrected after, and what cannot be independently verified.

## 1. Corpus and ground truth

Corpus: [`coral-xyz/sealevel-attacks`](https://github.com/coral-xyz/sealevel-attacks), the
vulnerability corpus maintained by the Anchor team. Eleven vulnerability classes.

Each class ships the same program in more than one variant:

| Variant | Meaning |
|---|---|
| `insecure` | the program **with** the bug |
| `secure` | the same program with the bug **fixed** |
| `recommended` | the same program written the idiomatic, safe way |

**This is what makes the ground truth objective rather than a judgement call.** A finding of class
*C* on the `secure` or `recommended` variant of class *C* is a false positive by construction,
because that program does not contain the bug. Nobody has to adjudicate.

We do not create ground truth. A benchmark whose author also writes the answer key is not a
benchmark. The corpus is maintained by the Anchor team and any dispute about a label is a dispute
with them, not with us.

## 2. Scoring definitions

For each of the 11 classes:

- **Nominal detection.** The scanner emitted at least one finding whose rule id is in the mapping
  for that class, on the `insecure` variant.
- **Real detection.** Nominal detection **and** the scanner did **not** emit a finding of that same
  class on the `secure` or `recommended` variant.

**Nominal recall** counts nominal detections. **Real recall** counts real detections. The gap
between them is the whole point of this benchmark: a scanner that fires on both the bug and its fix
is matching a code shape, not detecting a vulnerability, and its nominal score is meaningless.

Two further rules, both of which cost the scanner under test rather than help it:

- **A crash counts as a miss, never an excuse.** If the scanner throws on a file, that file yields
  no detection.
- **A class with no corresponding rule counts as a miss.** A scanner that cannot detect a bug does
  not detect it. Three of the eleven classes have no corresponding rule in the scanner under test
  and are recorded as structural gaps: `6-duplicate-mutable-accounts`, `9-closing-accounts`,
  `10-sysvar-address-checking`.

## 3. The class-to-rule mapping

The mapping from corpus class to scanner rule ids is fixed in `rb.py` and is reproduced in the
source with a comment on every line explaining which rule is expected to catch which class.

**The mapping was written before the scanner was run, and it was corrected once. Both facts
matter, so both are stated here.**

The first version of the mapping guessed semantic rule identifiers such as `SOL-MISSING-SIGNER`.
The scanner does not emit those. It emits numeric codes, `SOL-001` through `SOL-016`. So the first
mapping could never have matched anything, and every class would have scored zero for a reason
that had nothing to do with the scanner's ability.

The corrected mapping was derived from **each rule's own description of what it detects**, read
from `scanner.RULES`, and **not** from which rules happened to fire on the corpus. That is the
difference between fixing a broken mapping and fitting the criteria to the result. A reader who
wants to check this can compare the mapping in `rb.py` against the rule descriptions in
`scanner.py` without running anything.

**What cannot be independently verified, stated plainly:** the workspace this was developed in was
not under version control, so there is no commit history that timestamps the pre-registration.
The claim that the mapping preceded the run rests on our word and on the internal consistency of
the code, not on a verifiable timestamp. From this repository onward there is history, so this
limitation applies to the first result only and will not apply to any future one.

## 4. Procedure

1. Clone the corpus.
2. For each class, run the scanner over every `.rs` file under each variant directory.
3. Record every finding, its rule id, and the raw scanner output.
4. Apply the definitions in section 2.

The harness is `rb.py`. The raw per-class output is `benchmark-raw.json`. `verify.py` re-derives
the headline numbers from that raw file, so the reported result can be checked without rerunning
the scanner.

## 5. Conflict of interest

The first scanner measured by this benchmark is our own, `sol-audit`, which we were selling at the
time. It scored **2/11 nominal and 0/11 real**. We published that, rewrote the product listing to
lead with it, and set the price to zero the same day.

This is disclosed because it cuts both ways. It is evidence of independence, and it is also a
reason to check our arithmetic rather than take it on trust, which is why the raw data and the
verifier are in this repository.

## 6. What this benchmark does not measure

- It does not measure real-world safety. Recall against a labelled corpus is a lower bound and a
  comparable one. Nothing more is claimed.
- It does not cover vulnerability classes outside the corpus.
- The corpus was last updated in 2024 and eleven classes is a small sample. Extending it with real
  Anchor programs carrying publicly disclosed vulnerabilities, where the fix commit is the answer
  key, is the obvious next step and is not done yet.
- One scanner has been measured. One is not a survey.
