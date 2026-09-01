#!/usr/bin/env python3
"""Score every scanner we have raw output for, and append one dated row per scanner to history.

This is the clock. A ranking can be produced once and frozen; a regression is only visible if the
same measurement is repeated on a schedule. That repetition is the product.

Usage:
    python run_all.py --raw raw/ --out runs/
    python run_all.py --demo

Design rule, learned the hard way on this project: a scanner whose raw output is missing is
recorded as **unavailable**, never as a zero. "We could not run it" and "it found nothing" are
different facts, and a history file that conflates them will eventually report a tool as having
regressed when in truth our own harness broke.
"""
import argparse
import datetime
import glob
import json
import os
import sys

from score import score

# Where each scanner's raw output is expected, how to pull (rule_id, path) pairs out of it, and
# which mapping scores it. All three used to be literals maintained here by hand. They are derived
# from `adapters/*.json` instead, so that adding a tool is a declaration rather than an edit in
# three places, and so that every row on the clock has a file behind it saying where the tool came
# from, how it was invoked, how a run that could not happen is told from a run that found nothing,
# and what its parser is. The long provenance notes that used to live in this file live in those
# declarations now, beside the tool they describe.
#
# `test_all.py` pins the derived tables against the literals they replaced, so this cannot move a
# published row without the suite naming the row.
#
# A row may still be scored with another row's mapping - that is how one tool appears twice, at
# two versions or under two invocations, without a mapping file being written after the fact. A
# mapping created to score a run that has already happened is not a pre-registration, and
# `tools/preregistration_check.py` cannot tell the difference, so the rule is kept by not creating
# the file at all: each measurement names the mapping it is scored with.
import scanner_spec  # noqa: E402

SOURCES, SOURCES_CORPUS2, MAPPING_ALIAS, ROW_NOTES = scanner_spec.clock_tables()


def extract(kind, blob):
    """Normalise a scanner's own JSON into (rule_id, path) pairs."""
    if kind == "radar":
        out = []
        for item in blob or []:
            for loc in item.get("locations") or []:
                out.append((item.get("name", ""), loc.split(":")[0]))
        return out
    if kind in ("vaultlint", "sol-audit"):
        findings = blob.get("findings") if isinstance(blob, dict) else blob
        return [(x.get("rule_id", ""), x.get("file", "")) for x in findings or []]
    if kind in ("xray", "solsec"):
        # solsec's own report is {"analysis_results": [{rule_name, file_path, line_number}]}.
        # The 2026-08-31 corpus-1 file had been converted into the {name, locations} envelope
        # X-Ray and Radar use, by a script that was not committed. Both shapes are read here, so
        # the tool's own output can be scored without a conversion step nobody can reproduce.
        if isinstance(blob, dict) and isinstance(blob.get("analysis_results"), list):
            out = []
            for item in blob["analysis_results"]:
                fp = str(item.get("file_path", ""))
                out.append((item.get("rule_name", ""), fp[2:] if fp.startswith("./") else fp))
            return out
        out = []
        for item in blob or []:
            for loc in item.get("locations") or []:
                out.append((item.get("name", ""), str(loc).split(":")[0]))
        return out
    if kind == "semgrep":
        return [(r.get("check_id", ""), r.get("path", ""))
                for r in (blob or {}).get("results", [])]
    raise ValueError(kind)


def load_mapping(name, mappings_dir="mappings"):
    name = MAPPING_ALIAS.get(name, name)
    with open(os.path.join(mappings_dir, f"{name}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def measure(raw_dir="raw", mappings_dir="mappings"):
    """Returns a list of per-scanner result dicts, including the ones we could not run."""
    results = []
    for name, (filename, kind) in sorted(SOURCES.items()):
        path = os.path.join(raw_dir, filename)
        if not os.path.exists(path):
            results.append({"scanner": name, "status": "unavailable",
                            "reason": f"no raw output at {path}"})
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                blob = json.load(fh)
            findings = extract(kind, blob)
            mapping = load_mapping(name, mappings_dir)
        except Exception as exc:
            results.append({"scanner": name, "status": "error", "reason": repr(exc)})
            continue

        rows = score(findings, mapping["map"])
        fixed = sum(1 for _, p in findings
                    if "/secure/" in p.replace("\\", "/") or "/recommended/" in p.replace("\\", "/"))
        results.append({
            "scanner": name,
            "status": "measured",
            "source": filename,
            "mapping": MAPPING_ALIAS.get(name, name),
            "classes": len(rows),
            "nominal": sum(1 for r in rows if r[4]),
            "real": sum(1 for r in rows if r[5]),
            "findings": len(findings),
            "findings_on_fixed_code": fixed,
            "per_class": {r[0]: {"insecure": r[1], "secure": r[2], "recommended": r[3],
                                 "nominal": r[4], "real": r[5]} for r in rows},
        })
    return results


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


def previous(runs_dir):
    """Most recent prior run, for regression detection."""
    files = sorted(glob.glob(os.path.join(runs_dir, "*.json")))
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as fh:
        return json.load(fh)


def diff_against(prev, results):
    """The reason the clock exists: say out loud what moved since last time."""
    if not prev:
        return ["first recorded run, nothing to compare against"]
    was = {r["scanner"]: r for r in prev.get("results", [])}
    notes = []
    for r in results:
        old = was.get(r["scanner"])
        if not old:
            notes.append(f"{r['scanner']}: new to the benchmark")
            continue
        if r["status"] != "measured" or old.get("status") != "measured":
            if r["status"] != old.get("status"):
                notes.append(f"{r['scanner']}: {old.get('status')} -> {r['status']}"
                             f" ({r.get('reason', '')})")
            continue
        if r["real"] != old["real"]:
            arrow = "REGRESSION" if r["real"] < old["real"] else "improvement"
            notes.append(f"{r['scanner']}: real recall {old['real']} -> {r['real']}  {arrow}")
        if r["findings_on_fixed_code"] != old.get("findings_on_fixed_code"):
            notes.append(f"{r['scanner']}: findings on fixed code "
                         f"{old.get('findings_on_fixed_code')} -> {r['findings_on_fixed_code']}")
    for name in was:
        if name not in {r["scanner"] for r in results}:
            notes.append(f"{name}: disappeared from this run")
    return notes or ["no change since the previous run"]


def coverage_rows(raw_dir="raw", corpus_dir="corpus2", mappings_dir="mappings"):
    """One row per clock measurement: what evidence exists that it analysed what it claims to.

    `coverage_evidence` uses exactly the vocabulary `measure_corpus2` already writes into every
    run file:

        run log   a `<findings>.log` exists, with one entry per invocation, and it is the authority
        none      there is no such log, so which cases were analysed cannot be answered at all

    A findings file is not evidence of coverage and is not graded as a third level here. A case
    that was analysed and came back empty leaves exactly the same silence as a case nobody opened,
    and this project has published that mistake in both directions on the same day: error 35 read
    silence as a measurement, error 36 read a measurement as silence.

    For corpus 2 the row also carries the cases that are still unresolved, which is the other half
    of the question. `unavailable` is a case the tool attempted and could not complete, which is a
    permitted outcome as long as it is published with its reason. `not-run` and `unknown` are not
    outcomes; they are gaps.
    """
    c2_by_row = {r.get("scanner"): r
                 for r in measure_corpus2(raw_dir, corpus_dir, mappings_dir) if "scanner" in r}
    rows = []
    for corpus, sources in (("corpus1", SOURCES), ("corpus2", SOURCES_CORPUS2)):
        for scanner, (filename, _kind) in sorted(sources.items()):
            path = os.path.join(raw_dir, filename)
            log = path + ".log"
            entries = None
            if os.path.exists(log):
                try:
                    entries = json.load(open(log, encoding="utf-8"))
                except Exception:
                    entries = None
            row = {"corpus": corpus, "scanner": scanner, "raw": "raw/" + filename,
                   "coverage_evidence": "run log" if entries is not None else "none"}
            if entries is None:
                row["reason"] = (
                    "no run log at raw/" + os.path.basename(log) + ", so 'the tool ran this case "
                    "and found nothing' and 'the tool never saw this case' cannot be told apart")
            else:
                ok = sum(1 for e in entries if e.get("status") == "ok")
                row["invocations"] = len(entries)
                row["ok"] = ok
                row["not_ok"] = len(entries) - ok
            if corpus == "corpus2" and scanner in c2_by_row:
                m = c2_by_row[scanner]
                row["unresolved"] = {k: m[k] for k in ("unknown", "not-run", "unavailable")
                                     if m.get(k)}
                row["scoreable_denominator"] = m.get("scoreable_denominator")
            rows.append(row)
    return rows


def verify_coverage(raw_dir="raw", corpus_dir="corpus2", mappings_dir="mappings", echo=True):
    """Milestone 1's acceptance check. Returns (rows, failures); failures being empty is the pass.

    The roadmap words it as `reports zero coverage_evidence: none`, and that is the first of the
    two conditions below. The second follows from the same sentence in the same milestone - "no
    empty cells afterwards, and anything that cannot run is listed with a reason" - because a run
    log that covers eight of seventeen cases answers the question for eight of them and leaves
    nine as silence, which is the thing the log exists to prevent.

    A case recorded `unavailable` with a reason is NOT a failure. "Could not run" is a permitted
    and published outcome; it is `not-run` and `unknown` that are gaps.
    """
    rows = coverage_rows(raw_dir, corpus_dir, mappings_dir)
    failures = []
    for r in rows:
        if r["coverage_evidence"] == "none":
            failures.append(f"{r['corpus']} {r['scanner']}: coverage_evidence: none - {r['reason']}")
        gaps = r.get("unresolved") or {}
        for kind in ("not-run", "unknown"):
            if gaps.get(kind):
                failures.append(
                    f"{r['corpus']} {r['scanner']}: {gaps[kind]} cases {kind}, so its denominator "
                    "rests on cases nobody can show were analysed")
    if echo:
        print("coverage evidence, one row per measurement on the clock\n")
        print(f"{'corpus':9} {'scanner':32} {'evidence':9} detail")
        for r in rows:
            if r["coverage_evidence"] == "run log":
                detail = f"{r['invocations']} invocations, {r['ok']} ok, {r['not_ok']} not ok"
                gaps = r.get("unresolved") or {}
                if gaps:
                    detail += "; " + ", ".join(f"{v} {k}" for k, v in sorted(gaps.items()))
            else:
                detail = r["reason"]
            print(f"{r['corpus']:9} {r['scanner']:32} {r['coverage_evidence']:9} {detail}")
        none = sum(1 for r in rows if r["coverage_evidence"] == "none")
        print(f"\ncoverage_evidence: none      {none} of {len(rows)} measurements")
        print(f"coverage_evidence: run log   {len(rows) - none} of {len(rows)} measurements")
    return rows, failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="raw")
    ap.add_argument("--mappings", default="mappings")
    ap.add_argument("--out", default="runs")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--verify-coverage", action="store_true",
                    help="milestone 1's acceptance check: every measurement has a run log and no "
                         "case is left unresolved. Exits non-zero and says which rows fail.")
    args = ap.parse_args()

    if args.demo:
        demo()
        return 0

    if args.verify_coverage:
        _rows, failures = verify_coverage(args.raw, "corpus2", args.mappings)
        if not failures:
            print("\nPASS: every measurement on the clock has a per-run log and no case is "
                  "unresolved.")
            return 0
        print(f"\nFAIL: {len(failures)} problem(s). Milestone 1 is not met.\n")
        for f in failures:
            print("  -", f)
        print("\nThis is not a warning to read past. A denominator that rests on silence is the "
              "\ndefect that produced this project's retractions: two published numbers were "
              "\nextrapolated from one case each (error 20), a clean zero was published as an "
              "\noutage (error 36), and an outage that never happened was published as a "
              "\ndenominator (error 35).")
        return 1

    results = measure(args.raw, args.mappings)
    results_c2 = measure_corpus2(args.raw, "corpus2", args.mappings)
    prev = previous(args.out)
    notes = diff_against(prev, results)

    stamp = datetime.date.today().isoformat()
    os.makedirs(args.out, exist_ok=True)
    payload = {"date": stamp, "corpus": "coral-xyz/sealevel-attacks",
               "results": results, "corpus2": results_c2, "changes_since_previous": notes}
    with open(os.path.join(args.out, f"{stamp}.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)

    print(f"{'scanner':12} {'status':12} {'nominal':>8} {'real':>5} {'findings':>9} {'on fixed':>9}")
    for r in results:
        if r["status"] == "measured":
            print(f"{r['scanner']:12} {r['status']:12} {r['nominal']:>8} {r['real']:>5} "
                  f"{r['findings']:>9} {r['findings_on_fixed_code']:>9}")
        else:
            print(f"{r['scanner']:12} {r['status']:12}   {r.get('reason','')}")
    print("\ncorpus 2 (strict: mapped rules, located at the fix site):")
    for r in results_c2:
        if r.get("status") == "measured":
            counts = {k: v for k, v in r.items() if k not in ("scanner", "corpus", "status")}
            print(f"  {r['scanner']:12} " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        else:
            print(f"  {r.get('scanner','?'):12} {r.get('status')}  {r.get('reason','')}")

    print("\nchanges since previous run:")
    for n in notes:
        print("  -", n)
    print(f"\nwritten: {args.out}/{stamp}.json")
    return 0


def demo():
    """Self-check the parts that will silently rot: unavailability and regression detection."""
    prev = {"results": [
        {"scanner": "radar", "status": "measured", "real": 11, "findings_on_fixed_code": 24},
        {"scanner": "vaultlint", "status": "measured", "real": 2, "findings_on_fixed_code": 1},
    ]}
    now = [
        {"scanner": "radar", "status": "measured", "real": 9, "findings_on_fixed_code": 24},
        {"scanner": "vaultlint", "status": "unavailable", "reason": "no raw output"},
    ]
    notes = diff_against(prev, now)
    joined = " | ".join(notes)
    assert "REGRESSION" in joined, joined
    assert "measured -> unavailable" in joined, joined
    assert "improvement" not in joined, joined

    # An unavailable scanner must never be recorded as a zero score.
    res = measure(raw_dir="/definitely/not/here")
    assert all(r["status"] == "unavailable" for r in res), res
    assert all("real" not in r for r in res), "unavailable must not carry a score"

    # First run must not crash for want of a predecessor.
    assert diff_against(None, now) == ["first recorded run, nothing to compare against"]

    print("run_all: OK")


if __name__ == "__main__":
    sys.exit(main())
