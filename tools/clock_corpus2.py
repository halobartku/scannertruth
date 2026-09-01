#!/usr/bin/env python3
"""Corpus-2 scoring for the clock: `measure_corpus2`, which scores with `score2.py`.

Moved out of `tools/run_all.py` on 2026-09-01 without changing a line of the code below. `run_all`
re-exports `measure_corpus2`, so `run_all.measure_corpus2` keeps working. The source table and the
mapping loader come from `clock_corpus1`, which is where the clock derives them.
"""
import json
import os

from clock_corpus1 import MAPPING_ALIAS, SOURCES_CORPUS2, load_mapping


def measure_corpus2(raw_dir="raw", corpus_dir="corpus2", mappings_dir="mappings"):
    """Corpus 2, scored with score2.py. Absent raw output is unavailable, never a zero."""
    try:
        import score2
    except Exception as exc:
        return [{"corpus": "corpus2", "status": "error", "reason": repr(exc)[:120]}]
    manifest = os.path.join(corpus_dir, "manifest.json")
    if not os.path.exists(manifest):
        return [{"corpus": "corpus2", "status": "unavailable", "reason": "no manifest"}]
    cases = json.load(open(manifest, encoding="utf-8"))["cases"]
    # Same exclusion score2.py enforces: a pair whose "fix" does not fix the bug is not a case.
    # Two components disagreeing about which cases exist is how a denominator drifts unnoticed.
    cases = [c for c in cases if c.get("valid", True)]

    out = []
    for name, (filename, kind) in sorted(SOURCES_CORPUS2.items()):
        path = os.path.join(raw_dir, filename)
        if not os.path.exists(path):
            out.append({"scanner": name, "corpus": "corpus2", "status": "unavailable",
                        "reason": f"no raw output at {path}"})
            continue
        try:
            mapping = load_mapping(name, mappings_dir)["map"]
            findings = score2.load_findings(kind, path)
        except Exception as exc:
            out.append({"scanner": name, "corpus": "corpus2", "status": "error",
                        "reason": repr(exc)[:120]})
            continue
        # WHICH CASES WERE ACTUALLY ANALYSED?
        #
        # A run log is the only real evidence. A findings file cannot answer this: a scanner that
        # ran a case and found nothing leaves no entry, and so does a scanner that never saw it.
        # Treating "no entry" as "not run" is error 21 from the log; treating it as "ran and found
        # nothing" is error 20. Both were made on 2026-08-31, hours apart.
        #
        # So: if <filename>.log exists, it is the authority. If not, we say plainly that the
        # question is unanswerable rather than guessing in either direction.
        # A case is analysed only if EVERY variant of it ran. This used to read "any leaf with
        # status ok", which let one good variant vouch for a broken one: Radar's
        # anchor-interface-account/insecure produced no parseable output, its /secure ran fine,
        # and the case was scored `missed` off the back of the variant that worked. That is
        # error 32, and it is rule 3 broken inside the artefact built to enforce rule 3. A run
        # that did not happen cannot contribute a zero to anybody's denominator.
        log_path = os.path.join(raw_dir, filename + ".log")
        analysed, unavailable, evidence = None, set(), "none"
        if os.path.exists(log_path):
            try:
                entries = json.load(open(log_path, encoding="utf-8"))
                by_case = {}
                for e in entries:
                    case = str(e.get("leaf", "")).split("/")[0]
                    by_case.setdefault(case, []).append(e.get("status"))
                analysed = {c for c, st in by_case.items() if st and all(s == "ok" for s in st)}
                unavailable = {c for c in by_case if c not in analysed}
                evidence = "run log"
            except Exception:
                analysed = None

        seen = set()
        for path_key in findings:
            norm = str(path_key).replace("\\", "/")
            for c in cases:
                if f"/{c['name']}/" in norm or norm.startswith(c["name"] + "/"):
                    seen.add(c["name"])

        tally = {}
        for c in cases:
            d = os.path.join(corpus_dir, c["name"])
            if not os.path.isdir(d):
                tally["not-built"] = tally.get("not-built", 0) + 1
                continue
            if analysed is not None:
                if c["name"] in unavailable:
                    # The log says a variant of this case was attempted and produced nothing
                    # usable. That is not a zero and it is not "never run" either.
                    tally["unavailable"] = tally.get("unavailable", 0) + 1
                    continue
                if c["name"] not in analysed:
                    tally["not-run"] = tally.get("not-run", 0) + 1
                    continue
            elif c["name"] not in seen:
                # No run log, and nothing in the findings file belongs to this case. Silence,
                # and silence is not a measurement. Recorded as unknown rather than guessed.
                tally["unknown"] = tally.get("unknown", 0) + 1
                continue
            verdict, _ = score2.score_case(d, c["class"], mapping, findings)
            tally[verdict] = tally.get(verdict, 0) + 1

        unresolved = (tally.get("unknown", 0) + tally.get("not-run", 0)
                      + tally.get("unavailable", 0))
        status = "measured" if not unresolved else "partial"
        # The scoreable denominator, published beside the raw tally: a case nobody could run,
        # nobody has built, or nobody has a rule for is not a case this tool failed.
        scoreable = sum(v for k, v in tally.items()
                        if k in ("detected", "unlocated", "missed"))
        entry = {"scanner": name, "corpus": "corpus2", "status": status,
                 "source": filename, "mapping": MAPPING_ALIAS.get(name, name),
                 "coverage_evidence": evidence, "scoreable_denominator": scoreable, **tally}
        if status == "partial":
            reasons = []
            if tally.get("unavailable"):
                reasons.append(f"{tally['unavailable']} attempted but produced no usable output")
            if tally.get("not-run"):
                reasons.append(f"{tally['not-run']} the run log says were never run")
            if tally.get("unknown"):
                reasons.append(
                    f"{tally['unknown']} with no run log for {filename}, so 'found nothing' "
                    "and 'never analysed' cannot be told apart")
            entry["reason"] = (f"{unresolved} of {len(cases)} cases unresolved: "
                               + "; ".join(reasons))
        out.append(entry)
    return out

