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

### 3a. Pre-registration, from the second scanner onward

A mapping of somebody else's rules is an interpretation of their work, and an interpretation made
after seeing the scores is worthless. So, for every scanner other than the first:

1. The mapping is committed to `mappings/<scanner>.json` **in its own commit, before the scanner is
   run.** The commit timestamp is the pre-registration. This is what the first result could not
   offer and is the reason this file admits that gap above.
2. The mapping is derived from the tool's **own rule names and documentation**, never from which of
   its rules happened to fire.
3. `no-rule` is a permitted outcome. A class the tool does not claim to cover is a coverage gap, not
   a failed detection, and forcing a mapping for every class would manufacture failures.
4. **`unmappable` is also a permitted outcome**, for a rule whose description is too broad to tie to
   one class. Recorded rather than resolved in whichever direction suits us.

Rule descriptions promise more than rules do. That is a known weakness of deriving a mapping from
documentation, and it is the reason the right of reply below is the strongest safeguard here, not
this one.

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
- The corpus was last updated in 2024 and eleven classes is a small sample. ~~Extending it with
  real Anchor programs ... is not done yet.~~ **Done:** corpus 2 holds ten production
  vulnerabilities where the maintainers' own fix commit is the answer key. See `RESULTS-corpus2.md`.
- ~~One scanner has been measured. One is not a survey.~~ **Six have been**, plus two controls.
  Six is still not a survey. See `RESULTS-all.md`.

### The gap the controls do not close

`control-noisy` proves a score cannot be bought with **volume**. Nothing here proves a score was not
bought by **tuning against the corpus itself**, because the teaching corpus is public and its
contents are known to everyone who builds one of these tools. A scanner fitted to it passes every
check in this document.

The only real defence is a **holdout**: at least one insecure/secure pair that is never published,
against which a tool is scored after its public result is fixed. We do not have one. Until we do,
**every score on corpus 1 in this repository should be read as in-sample**, including the 11/11, and
including our own. Corpus 2 is out-of-sample by construction, which is why its numbers carry more
weight despite being newer and smaller.

**A holdout appears to contradict this project's promise that the data is open and free forever.
It does not, if it rotates.** The intended shape: a holdout pair is withheld only until the round it
scores is published, and is then released into the public corpus while a new one is built for the
next round. Every case becomes public, on a delay measured in one round rather than never. A
permanently secret corpus would make this benchmark unauditable, which is worse than the problem it
solves.

### When this benchmark stops

A measuring institution with no one reading the measurements is a hobby that costs money, and the
honest version of this project names its own falsifier in advance. **If the pending grant is
refused and the open thread with a measured vendor draws no technical reply within fourteen days,
this benchmark has zero confirmed consumers and work on it stops.** Adding a third corpus or a
seventh scanner before that line is answered would be building supply for a demand we have not
demonstrated.
