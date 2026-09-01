# COMMITMENTS

Three promises, made 2026-08-31, while this project has one measured scanner, no users, and
nobody offering it money. That is the only honest time to make them. A commitment to independence
announced after someone offers you a cheque is not a commitment, it is a press release.

## 1. The data is open and free. Always.

Every score, every raw scanner output, every corpus manifest and every version of the harness is
published under an open licence and readable without payment, registration or an account.

This includes results that embarrass us. The first entry in this dataset is our own scanner scoring
0 out of 11 real recall, and it is still there.

## 2. Our own scanner stays free and open source. Always.

[`sol-audit`](https://github.com/halobartku/sol-audit) is MIT and will not be commercialised. It
exists in this project as the first subject of the benchmark, not as a product.

The plain reason: you cannot sell a scanner and rank scanners. If our tool were for sale, every
number we publish about a competitor would be a marketing document. We would rather have the
numbers be worth something.

The honest reason: the commercial value we are giving up here has been measured, and it is zero.
The scanner was listed at $0.99 per audit on one marketplace and $0.05 on another, and made no
sales on either, ever. The main alternative in this ecosystem is free and open source. So this
promise costs us nothing today, which is precisely why it is worth writing down before it does.

## 3. We take no money from anyone we measure. Ever.

No sponsorship, no consulting, no paid placement, no "verified vendor" tier, no early access sold
to the scanned. Not from a scanner's authors, not from their employer, not from their foundation.

If a party we measure funds us in any form, we will say so at the top of the results page, and we
would rather refuse than write that sentence.

Funding comes from grants, from public research programmes, and potentially from people who want
to depend on the data rather than appear in it. Whether anyone will ever pay for that is unproven,
and we are not going to pretend otherwise.

## 4. We will not sell an auditor. Ever.

Decided 2026-09-01, the day we first measured a model-backed auditor and found a way the whole
category is probably being measured wrong.

**We are a benchmark. A referee does not also field a team.** We will not sell, licence, or take
revenue from a security scanner or AI auditor of our own, fine-tuned or otherwise, for as long as
this benchmark publishes. `sol-audit` stays what promise 2 says it is: free, open, and not a
product - and it stays in the results table with its own failing numbers.

**Why this is written down while it is expensive.** The obvious way to make money from this work is
to build the auditor we now know how to evaluate. We would be unusually good at it: we hold the
corpus, we know the two filters that separate a detection from a lucky verdict, and we have the
measurement rig already. That is exactly why the promise is needed. A vendor who also runs the
scoreboard has one clean way to win and it is not by building a better tool.

If money has to come from somewhere, it comes from the measurement - grants, or people who need to
know whether a tool they are buying works. **Never from a vendor we measure** (promise 3), and
never from selling the thing we grade.

**How to hold us to it.** If a product of ours ever appears with a price on it and a rule engine
behind it, this file is the receipt, and the honest move at that point is to stop publishing the
benchmark rather than to quietly edit this page.

## What these promises do not cover

They are about independence, not about quality. We can still be wrong, and we have already been
wrong in public: the corrections are in `docs/PROTOCOL.md` and in the commit history, including a bug we
introduced in our own guard logic and caught by measurement rather than by reading.

They also do not promise permanence of effort. A benchmark that stops being re-run rots. If this
project is abandoned, the honest thing is to say so on the front page rather than leave stale
numbers looking current, and that is what we will do.
