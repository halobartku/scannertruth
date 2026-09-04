# Engineering log, 2026-09-04

Continuing from [the log of 2026-09-03](ENGINEERING-LOG-2026-09-03.md).

---

## The framework filter the vendor named: measured, and it did not divide

**2026-09-04.** This is not an error entry. It closes the largest open risk on the radar rows,
and the closure belongs beside the numbers rather than in a chat log.

On 2026-09-03 in [`radar#32`](https://github.com/Auditware/radar/issues/32) the vendor answered
our open invitation to name any path where the container and the library path could differ:

> rules are baked into the image (api/Dockerfile:113), so docker = digest and shim = commit; and we
> filter templates by detected framework, which looks inert on all 17 pack cases but could bite if
> one detected as anchor.

Both paths stood against our `fa81c25` row, and neither was disputed. That row carried our only
new detection, so the risk was not academic: had the shim and the image disagreed, the detection
would have been an artefact of how we ran the scanner rather than a property of the scanner.

**Measured on 2026-09-04.** The same revision `fa81c25`, run through the vendor's real image
`ghcr.io/auditware/radar-api@sha256:1616723a1879668d4050def641e541f2c9edc878974b06011fb6b1a3bc519b4f`,
over all 17 corpus-2 cases, both variants:

    shim   274 location rows    detected 1, missed 6, no-rule 8, unlocated 2
    image  274 location rows    detected 1, missed 6, no-rule 8, unlocated 2
    diff   0 rows appear, 0 rows disappear

Two passes of the image agree with each other, so the run is deterministic, and both run logs
report 36 invocations with 36 ok. The comparison was made after normalising the location format,
because `f36d1a4` changed it from `file:line:col` to `file:line:startcol-endcol` and a literal
diff reports every row as new.

**What this settles and what it does not.** It settles the framework filter **on our 17 cases**:
the mechanism the vendor named exists and is inert here. It is not a proof that the two can never
diverge, and this entry does not claim one. The image row is published **beside** the shim row in
[`RESULTS-corpus2.md`](results/RESULTS-corpus2.md), not in place of it, so a reader can see both
measurements and their agreement rather than a single merged number.

**Order, because the order is the point.** The row was declared in `adapters/radar.json` and in
the golden record **before** it was published anywhere. That is the opposite of what happened with
the shim row on 2026-09-03, which went to the vendor while `--verify-coverage` still reported
22 of 22 without covering it. Coverage now reads **24 of 24** and includes both.

**Reproduce:**

    python3 tools/scanner_spec.py --run radar --corpus corpus2 --out raw/c2-radar-fa81c25.json --repeat 2
    python3 tools/run_all.py --verify-coverage

Raw artefacts for the image pass: `raw/c2-radar-fa81c25-image.json`, `.run2.json`, and one `.log`
per pass.

## The correction that came with it

The comment we posted on 2026-09-03 carried two wrong numbers, and they were corrected in the same
thread on 2026-09-04 (comment `5542858480`) together with the measurement above. `34 invocations`
was the `24c56f9` figure carried across by transcription; the `fa81c25` run made **36 per pass,
72 in total**. `46 new or changed rows` conflated a net change with a row count; **50 rows appear
and 4 disappear**, of which 44 are generic-rule effects.

Neither error changed a verdict. Both were ours, both were public for a day, and both were found
by our own coverage gate rather than by the vendor.
