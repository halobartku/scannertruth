# Engineering log, 2026-09-02

Continuing from [the log of 2026-09-01](ENGINEERING-LOG-2026-09-01.md). One entry, error 42, and
it is not an error in the ordinary sense: nothing published today was wrong yesterday. It is the
record of a method substitution made under a constraint, the proof that was required before the
substitution was allowed to produce a number, and a near-miss that would have been error-shaped
if the order had been different.

---

## Error 42. The engine shim existed for a day with no proof and no measurement attached

**Context.** On `radar#32` we promised to walk the vendor's then-current `main` through the same
harness and publish it as a new row next to the old one, not over it. On 2026-09-01 22:48Z the
vendor reported their own post-#36 figures: 2 false positives, 11% noise, recall unchanged. Those
were vendor-reported; the promise was to measure it ourselves.

**The constraint.** Radar's production pipeline is docker-native: the CLI shells out to
`docker compose`, and the AST engine, the rules and the API that orchestrates them live inside
containers. The runtime available for this re-measurement had **no docker daemon** — `radar scan`
against any target ends in `Docker was not available after 10 attempts` and writes nothing. Every
earlier radar row in this repository was measured on a machine that had one.

**The substitution.** `/root/radar-engine-shim/bin/radar` is a CLI-compatible wrapper that imports
the vendor's own engine code — AST generation, template execution, suppression filtering, output
writing — directly from their repository checkout, unmodified, pinned by git, and runs it
in-process. It adds no rules, changes no thresholds, and touches no template. Every behavioural
decision in it is a documented copy of a named production code path (the mapping from CLI to
those paths is commented at the top of the shim, function by function).

**The proof it had to pass before it was allowed to produce a number.** A port that runs is not a
port that is right — the rule this project learned on its own product. So before measuring the new
revision, the shim was run against the **old** revision `206a469` — the exact code the docker
measurement of 2026-08-31/09-01 had scored — and compared to that measurement's raw output:

> **52 of 52 location rows identical: rule name, file, line and start column, no extras, none
> missing** (`raw/radar-shim-parity-2026-09-02/shim-on-206a469.json` vs `raw/radar-full.json`).

Only after byte-level parity on the old revision was the checkout moved to `67348ee` (post-#37)
for the measured row. The parity artefact is committed beside the measurement it licenses.

**What the shim does not claim.** It is not radar. It does not exercise the docker orchestration,
the API service, the queue, or the container boundary. It claims that the *scanning semantics* —
language detection, AST construction, template selection and execution, suppression, output
shape — are the vendor's own code at the pinned revision, and nothing else. If radar's behaviour
ever diverges between its container path and its library path, this measurement describes the
latter. That limitation is why the parity proof is against the docker run rather than against the
vendor's published figures: the comparison is to our own prior measurement of the same code, made
the production way.

**The measurement.** 35 invocations (11 classes, every variant present on disk, including the two
`insecure-still` variants the scorer ignores and the log records anyway), 35 ok, zero unavailable,
two passes, deterministic. Real recall **11/11**, unchanged. Findings **52 → 19**. Firings on
already-fixed variants **24 → 2**, both `Missing Owner Check` on `secure` variants of
`1-account-data-matching` and `4-initialization`. The error-39 upper-bound caveat applies.

The vendor's own report for the same revision: 2 false positives, 11% noise rate, recall
unchanged. **Our independent measurement lands on their numbers.** The row is published in
`RESULTS-scanners.md` beside the 2026-08-31 row, which stays.

**One thing this entry records as a defect even though nothing broke.** The shim existed before
this session — written 2026-09-01 22:48Z, the same minute PR #36 merged — and no measurement used
it, no parity proof accompanied it, and no document mentioned it. A method substitution without
its proof is exactly the shape of error this log exists for: it would have been trivially easy to
measure post-#36 with an unvalidated shim and publish the number. The order actually followed —
parity proof on the old revision first, new measurement second — is the order that will be
required if the shim is ever used again.
