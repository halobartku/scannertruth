# Why ScannerTruth exists

The argument for the benchmark, moved here verbatim from the front page on 2026-09-02 so that
`README.md` can stay short. The numbers quoted below are the ones the README table carries.

## Why this exists

A project can adopt a scanner, satisfy a compliance requirement, and be no safer than before, with
no mechanism anywhere that would reveal it. The interesting output of a standing benchmark is not
the ranking. **It is the day a widely used scanner quietly regresses and the numbers show it.**

---

## Every Solana scanner is graded on the same test paper, and it has not changed since 2022

`coral-xyz/sealevel-attacks`, the corpus the entire category is measured against, was last modified
**16 July 2022**, at commit `24555d04`. Eleven hand-written teaching programs. Four years. Public
the whole time.

At least two of the tools we measured cite that corpus **in their own rule tables**. One vendor
merged pull requests closing the last gaps in it **on the day we measured them**. None of that is
dishonest; it is what any engineer would do. But it means a score on that corpus measures **how
thoroughly a tool has done a fixed piece of homework**, not whether it works on anything else.

An exam with the same questions for four years stops telling you who can do the subject.

**So we built the other exam.** Real break-ins, each taken from the fix commit its own maintainers
wrote. As of 2026-09-01 there are **17 valid cases**, **17 built** and **8 measured**. Eight is the
floor: it is the set every row in the table below covers, and a row that has since been re-run
over more says so and states its own larger denominator. No case is ever quietly dropped, and a
case a given scanner has not been run over is reported as `not-run`, never as a zero. The best scanner on the market scores **11/11 on the
four-year-old paper and zero on the real one.**

---

Vendors publish finding counts. **A finding count is not recall.** A scanner that flags fixed code
as often as vulnerable code produces an impressive number and catches nothing. We know because we
measured it on our own product first, and published the result that killed the claim.

---

## Who this is for, and why it matters

### The harm is not missing tools. It is false assurance.

A team buys a scanner, runs it, gets a clean report, ticks "we have security tooling" in the
documentation, tells investors "it's been scanned", and **sleeps better while being exactly as
exposed as before.**

That is not hypothetical. Our own scanner produced 194 findings on one repository and detected
nothing. The best tool on the market scores a perfect 11/11 on the corpus everyone uses and **zero
on eight real break-ins**. A clean report from a tool of unmeasured effectiveness is not
information; it is noise that people act on, usually by deciding *not* to spend money on a human
audit.

### Who this helps

**Teams building on Solana.** Today you choose a scanner by its marketing. With a measured real
recall you know what a green report is worth, and whether it justifies skipping a human review.
That is a budget decision, and right now it is made blind.

**Teams already paying for audits.** You can ask your auditor: *what is the measured effectiveness
of the tooling you use, and how do you know?* Until now that question had no possible answer.

**Grant programmes and foundations.** They fund security tooling and have **no instrument to
evaluate what the funding produced.** Not carelessness, an absent measuring device. A benchmark lets
a programme compare applications and ask a grantee for measured real recall instead of a finding
count.

**Honest tool vendors, and this is not a courtesy.** Our measurement *confirmed* VaultLint's
precision claim: everything it detected, it detected correctly. That is an asset they earned. Today
a good tool and a loud tool look identical, because the only visible number is a finding count and
that number rewards noise. Which is also why every vendor here gets a
[right of reply](PROTOCOL.md) before a result is treated as final.

**The ecosystem, before the AI-audit wave lands.** It has already started: one tool is in our
could-not-run table because it needs a paid model key. There is currently **no way to compare these
tools at all**, so the choice will be made on marketing. Worse, an AI auditor is
*non-deterministic*: the same code can give a different answer tomorrow, so the single measurement
everyone performs today says almost nothing. Repeated measurement is the only honest form, and it is
what the clock in this repository does.

### The market context, measured rather than assumed

Of the six tools measured on 2026-08-31, surveyed for activity on 2026-09-01: **one is actively
developed**, two have been silent for half a year, and one is effectively abandoned despite 77,684
lifetime downloads against 56 recent ones.
[`docs/SCANNERS.md`](SCANNERS.md) has the table.

**That is not a mature market. It is missing infrastructure.** Which is the whole argument for
building this now rather than in two years.

---

## Why the ground truth is not a matter of opinion

The teaching corpus is maintained by the Anchor team. Every class ships the same program twice: with
the bug (`insecure`) and with it fixed (`secure`, `recommended`). A finding of class *C* on the
fixed variant of class *C* is a false positive **by construction**. Nothing to adjudicate.

Corpus 2 works the same way one step harder: each pair is a real program immediately before and
after the fix **its own maintainers wrote** in response to a public disclosure. We do not decide
what the bug was.

**A benchmark whose author also writes the answer key is not a benchmark.**
