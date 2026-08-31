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

# Where each scanner's raw output is expected, and how to pull (rule_id, path) pairs out of it.
SOURCES = {
    "radar": ("radar-full.json", "radar"),
    "vaultlint": ("vaultlint.json", "vaultlint"),
}


def extract(kind, blob):
    """Normalise a scanner's own JSON into (rule_id, path) pairs."""
    if kind == "radar":
        out = []
        for item in blob or []:
            for loc in item.get("locations") or []:
                out.append((item.get("name", ""), loc.split(":")[0]))
        return out
    if kind == "vaultlint":
        findings = blob.get("findings") if isinstance(blob, dict) else blob
        return [(x.get("rule_id", ""), x.get("file", "")) for x in findings or []]
    raise ValueError(kind)


def load_mapping(name, mappings_dir="mappings"):
    with open(os.path.join(mappings_dir, f"{name}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def measure(raw_dir=".", mappings_dir="mappings"):
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
            "classes": len(rows),
            "nominal": sum(1 for r in rows if r[4]),
            "real": sum(1 for r in rows if r[5]),
            "findings": len(findings),
            "findings_on_fixed_code": fixed,
            "per_class": {r[0]: {"insecure": r[1], "secure": r[2], "recommended": r[3],
                                 "nominal": r[4], "real": r[5]} for r in rows},
        })
    return results


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=".")
    ap.add_argument("--mappings", default="mappings")
    ap.add_argument("--out", default="runs")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    if args.demo:
        demo()
        return 0

    results = measure(args.raw, args.mappings)
    prev = previous(args.out)
    notes = diff_against(prev, results)

    stamp = datetime.date.today().isoformat()
    os.makedirs(args.out, exist_ok=True)
    payload = {"date": stamp, "corpus": "coral-xyz/sealevel-attacks",
               "results": results, "changes_since_previous": notes}
    with open(os.path.join(args.out, f"{stamp}.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)

    print(f"{'scanner':12} {'status':12} {'nominal':>8} {'real':>5} {'findings':>9} {'on fixed':>9}")
    for r in results:
        if r["status"] == "measured":
            print(f"{r['scanner']:12} {r['status']:12} {r['nominal']:>8} {r['real']:>5} "
                  f"{r['findings']:>9} {r['findings_on_fixed_code']:>9}")
        else:
            print(f"{r['scanner']:12} {r['status']:12}   {r.get('reason','')}")
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
