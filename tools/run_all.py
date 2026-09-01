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


# The clock's scoring jobs live beside this file now: corpus 1 in `clock_corpus1.py` (which also
# derives the source tables from `adapters/*.json`) and corpus 2 in `clock_corpus2.py`. They are
# re-exported here so that `run_all.<name>` keeps working for every caller, and so this module
# stays the CLI: history, the coverage gate and `main`.
from clock_corpus1 import (  # noqa: F401
    MAPPING_ALIAS, ROW_NOTES, SOURCES, SOURCES_CORPUS2, extract, load_mapping, measure)
from clock_corpus2 import measure_corpus2  # noqa: F401


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
            retired = _retired_declaration(corpus, scanner)
            if retired:
                row["retired"] = retired
            if corpus == "corpus2" and scanner in c2_by_row:
                m = c2_by_row[scanner]
                row["unresolved"] = {k: m[k] for k in ("unknown", "not-run", "unavailable")
                                     if m.get(k)}
                row["scoreable_denominator"] = m.get("scoreable_denominator")
            rows.append(row)
    return rows


def _retired_declaration(corpus, scanner):
    """A measurement may declare itself retired, and the gate reports it without failing on it.

    Added 2026-09-01 because the gate demanded a run log for the `sol-audit` v2 corpus-2 row on the
    same day that row was retired as superseded by v3. A red badge for a reason we had already
    published and acted on is worse than no badge: it teaches a reader to ignore the colour.

    The hatch is deliberately narrow. A retirement names a date, what supersedes it, a reason and
    where it was published, and a check refuses one that does not. Retiring is a statement somebody
    signs, not a way to quiet an inconvenient line, and the row keeps appearing in the output marked
    RETIRED so nothing disappears.
    """
    import scanner_spec
    # load_all returns a dict keyed by name, so iterate values. Writing this as a bare
    # `for spec in load_all()` walked the keys and every lookup silently returned None,
    # which a broad `except Exception` then hid completely. The except is narrow now: a
    # declaration this cannot read is a bug worth crashing on, not one worth swallowing.
    for spec in scanner_spec.load_all().values():
        for m in spec.get("measurements", []):
            if m.get("corpus") == corpus and m.get("row") == scanner and m.get("retired"):
                return m["retired"]
    return None


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
        if r.get("retired"):
            continue
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
            if r.get("retired"):
                detail = ("RETIRED " + r["retired"]["on"] + ", superseded by "
                          + r["retired"]["by"] + "; not counted against this check")
            print(f"{r['corpus']:9} {r['scanner']:32} {r['coverage_evidence']:9} {detail}")
        live = [r for r in rows if not r.get("retired")]
        retired_n = len(rows) - len(live)
        none = sum(1 for r in live if r["coverage_evidence"] == "none")
        print(f"\ncoverage_evidence: none      {none} of {len(live)} live measurements")
        print(f"coverage_evidence: run log   {len(live) - none} of {len(live)} live measurements")
        if retired_n:
            print(f"retired, reported and not counted   {retired_n}")
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
