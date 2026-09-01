Radar and VaultLint on the real crates, 2026-08-31. RECOVERED, not re-run.

The results page published a Radar table and a VaultLint table over the real crates on
2026-08-31. The repository held the Radar per-case run log (raw/realcrates-radar-run.log)
and no findings file for either tool, so both published tables rested on numbers nobody
outside the run host could recompute. This project's own rule is that an artefact per run
is what separates a measurement from a claim, and half of the real-crate evidence did not
have one here.

These files were recovered on 2026-09-01 from /tmp/c2crates-radar on the machine the run
happened on. They were NOT produced by a new run and nothing in them was regenerated.

What proves they are the same run: concatenating the per-case log recovered beside them is
byte-identical to raw/realcrates-radar-run.log, which was committed on 2026-08-31. The
duplicate was deleted rather than committed twice.

  <case>.<variant>.json   radar's own output, its own envelope, paths under /tmp/c2crates
  <case>.<variant>.log    radar's stdout for that invocation, including the three cases
                          where it printed "Exceeded maximum retries"

Beside this directory, raw/rc-recovered-20260831-vaultlint.json is the VaultLint run over
the same crates, recovered from /tmp/c2crates-vaultlint.json on the same host. It holds 38
findings under VL003, VL004 and VL005, which is the number the results page published, and
the per-case counts match the published table exactly. It was ONE invocation over the whole
corpus rather than one per case, which is the limitation the results page already states:
for the five cases with no findings it cannot tell "found nothing" from "did not analyse".

The corpus these ran against is the 2026-08-31 real-crate build, ten cases. The corpus has
eighteen cases now, so these files are the record of what was published, not a measurement
of the current corpus.
