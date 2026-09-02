#!/usr/bin/env python3
"""Score the Radar results that run.sh wrote, with the scorer that produced the published row.

Usage:
    python check.py                  # reads results/, prints one verdict per case
    python check.py --results DIR    # results written somewhere else
    python check.py --json out.json  # also write the verdicts as JSON

Verdicts come from score2.score_case, unchanged: a finding counts only if its rule is the one
mapped to the case's class and it lands within TOLERANCE lines of a line the fix changed.

    detected   mapped rule fires at the fix site on the vulnerable variant, silent on the fixed one
    unlocated  mapped rule fires in the file but not at the fix site, or fires on the fixed variant too
    missed     no mapped rule fires
    no-rule    the mapping names no Radar rule for this class; nothing to regress
    not-run    run.sh left no evidence that radar scanned this variant

`fires_on_fixed` counts every finding on the fixed variant, mapped or not. That is an upper bound
on noise, not a false-positive count: a finding on fixed code may be a real, unrelated defect.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
import score2  # noqa: E402

VARIANTS = ("insecure", "secure")
SCANNED = re.compile(r"Scanned (\d+) file")


def _unstage(location, case, variant):
    """`.../_staged/<case>.<variant>/pkg/src/x.rs:12:3` -> `cases/<case>/<variant>/src/x.rs`, line 12."""
    path, _, rest = location.replace("\\", "/").partition(":")
    line = rest.split(":")[0]
    tail = path.split("/pkg/", 1)[1] if "/pkg/" in path else path.rsplit("/src/", 1)[-1]
    if not tail.startswith("src/"):
        tail = "src/" + tail
    return f"cases/{case}/{variant}/{tail}", (int(line) if line.isdigit() else 0)


def load_results(results_dir, cases):
    """Returns (findings_by_path for score2, {case: {variant: status}}, {case: fires_on_fixed})."""
    findings, status, on_fixed = {}, {}, {}
    for c in cases:
        status[c] = {}
        on_fixed[c] = []
        for v in VARIANTS:
            leaf = os.path.join(results_dir, f"{c}.{v}")
            out = os.path.join(leaf, "radar.json")
            log = os.path.join(leaf, "stdout.log")
            scanned = False
            if os.path.exists(log):
                scanned = bool(SCANNED.search(open(log, encoding="utf-8", errors="replace").read()))
            blob = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else []
            # radar writes no file when it finds nothing, so a missing file is a zero only when
            # its own stdout says it scanned something. Otherwise it is not evidence.
            status[c][v] = "ok" if (scanned or os.path.exists(out)) else "not-run"
            for item in blob or []:
                for loc in item.get("locations") or []:
                    path, line = _unstage(loc, c, v)
                    findings.setdefault(path, []).append((item.get("name", ""), line))
                    if v == "secure":
                        on_fixed[c].append(item.get("name", ""))
    return findings, status, on_fixed


def check(results_dir="results"):
    cases = [c["name"] for c in json.load(open("manifest.json", encoding="utf-8"))["cases"]]
    classes = {c["name"]: c["class"] for c in json.load(open("manifest.json", encoding="utf-8"))["cases"]}
    mapping = json.load(open("mapping.json", encoding="utf-8"))["map"]
    findings, status, on_fixed = load_results(results_dir, cases)
    rows = []
    for c in cases:
        if "not-run" in status[c].values():
            rows.append({"id": c, "class": classes[c], "verdict": "not-run",
                         "reason": "no radar.json and no 'Scanned N file' line for " +
                                   ", ".join(v for v, s in status[c].items() if s == "not-run"),
                         "fires_on_fixed": None})
            continue
        v, info = score2.score_case(os.path.join("cases", c), classes[c], mapping, findings)
        rows.append({"id": c, "class": classes[c], "verdict": v, "reason": info.get("reason", ""),
                     "fires_on_fixed": len(on_fixed[c]), "rules_on_fixed": sorted(set(on_fixed[c]))})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--json")
    a = ap.parse_args()
    rows = check(a.results)
    print(f"{'case':38} {'class':30} {'verdict':10} {'on-fixed':>8}  note")
    tally = {}
    for r in rows:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
        fx = "-" if r["fires_on_fixed"] is None else str(r["fires_on_fixed"])
        print(f"{r['id']:38} {r['class']:30} {r['verdict']:10} {fx:>8}  {r['reason']}")
    print()
    print("radar: " + "  ".join(f"{k}={v}" for k, v in sorted(tally.items())))
    total_fixed = sum(r["fires_on_fixed"] or 0 for r in rows)
    print(f"findings on fixed variants (upper bound on noise): {total_fixed}")
    if a.json:
        json.dump({"tally": tally, "cases": rows}, open(a.json, "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
