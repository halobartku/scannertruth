---
name: publish-a-measurement
description: Use when publishing, correcting or retracting a benchmark result, or when a measurement turns out to be wrong after it is already public. Enforces retracting before the replacement exists, leading with the uncomfortable number, and the right of reply.
---

# Publishing a measurement

A benchmark's only asset is that its numbers can be checked. This is the half that decides whether
anyone believes them, and it applies to both `measure-a-scanner` and `add-a-corpus-case`.

On 2026-08-31 this project published a headline, found it rested on one case, and retracted it in
public. That went well. The rules below are what made it go well, written down so the next one does
not depend on remembering.

## 1. Lead with the number that hurts

- A third-party tool beating ours goes in the **first paragraph**. Radar's 11/11 against our 4/11
  does.
- A tool whose claim the measurement **confirms** gets said plainly. VaultLint's precision claim
  held, and saying so matters: an instrument that only ever produces bad news is not trusted either.
- A finding that flatters us gets **more** scrutiny, not less. Radar appearing to detect the Cashio
  bug on real crates was the most flattering result of the day and was wrong twice over.

## 2. Retract before you have the replacement

When the Radar and VaultLint numbers were found to rest on one case each, banners went up on both
results pages **before any re-measurement existed**.

**Leaving an unsupported claim standing while you gather better numbers is the wrong order.** The
temptation is always to wait so the correction can be published alongside the fix. Do not. The
claim is wrong now.

## 3. Correct the mechanism, not only the number

The re-measurement confirmed the headline: still zero detections. But the old text had said the
mapped rule "never fired at all" on eight of nine cases, and measured, it fires in the right file on
two of them.

**Being right about the conclusion while wrong about the mechanism is still being wrong**, and it is
the version a reader is most likely to catch. Say which part survived and which did not.

## 4. Preserve what was published, beside the correction

- A pre-registered mapping stays **unedited** next to its correction. A benchmark that silently
  repairs its mapping after seeing scores is worth nothing, and pre-registration only means anything
  when it binds on an inconvenient result.
- Publish both numbers: `0/8 as registered, 1/8 corrected`.
- Superseded results pages keep their content and gain a banner saying what changed. Do not rewrite
  history into having been right.
- Never let an artefact's **name** assert something its contents do not. One raw file called
  `c2clean-radar.json` was a different corpus entirely, and while auditing it looked like the
  missing evidence. Rename it and leave a note saying what it actually is.

## 5. Right of reply is a requirement, not a courtesy

A mapping of somebody else's rules is an interpretation of their work. Offer it to them **before
treating the result as final**, and publish their correction beside yours rather than instead of it.

Until they answer, every third-party number is **provisional**, and say so in the protocol. The
X-Ray case is the proof this is not a formality: our mapping was wrong in a way only the tool's
authors could have settled quickly, and we published the wrong number first.

When you open the thread: no offer, no price, no link to anything paid. Solve or report; money
starts from the other side or not at all.

## 6. Publish the limitations in the same commit

Not later, not in a follow-up. `KNOWN-LIMITATIONS.md` opens with our own error for a reason.

State the selection bias, the in-sample warning, the sample size, and what the controls do **not**
cover, before anyone asks. A limitation a reader finds themselves costs far more than one you
handed them.

## 7. Keep the log of errors, with dates

Twenty-one errors are documented. That document, not the results, is the strongest thing to hand a
sceptic, because it shows the same reaction when a result damaged a competitor (we understated
X-Ray) and when it flattered us (we threw out our own corpus case).

Record what was believed, when, and what refuted it. A correction with no record of the original
claim is indistinguishable from never having been wrong, which is not a claim anyone believes.

## Red flags

| Thought | Reality |
|---|---|
| "I'll publish the correction once I have the new numbers" | Retract now. The claim is wrong now. |
| "The conclusion held, so the page is fine" | Correct the mechanism too, or a reader will. |
| "This mapping was obviously meant to include that class" | Then say it changed after seeing results, and leave the original beside it. |
| "The vendor will probably agree with our mapping" | Ask. Ours was wrong and only they could settle it. |
| "The limitations can go in a follow-up commit" | They go in this one. |
| "Deleting the wrong result keeps the record clean" | The record of being wrong is the asset. |
