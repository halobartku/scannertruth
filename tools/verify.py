#!/usr/bin/env python3
"""Re-derive the headline numbers in RESULTS.md from benchmark-raw.json.

Run: python verify.py
Exits non-zero if the raw data does not reproduce the published result, so this doubles as a
regression check on the claim rather than only a pretty-printer.

SCOPE, stated because the name promises more than it delivers: this verifies **RESULTS.md only** -
run 1, `sol-audit` v1, 2/11 nominal and 0/11 real. It does not touch the six-scanner table in
RESULTS-all.md, the corpus-2 results, or the real-crate results. Nothing currently re-derives the
current headline from raw data, and until something does, a green check here must not be read as
the headline being verified.
"""
import json
import sys

PUBLISHED_NOMINAL = 2
PUBLISHED_REAL = 11 - 11  # 0. Written this way so a careless edit to one constant is visible.
EXPECTED_CLASSES = 11


def load(path="raw/benchmark-raw.json"):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def on_target(entry, variant):
    """Findings on `variant` whose rule id is in this class's mapping. Missing variant means zero."""
    return (entry.get(variant) or {}).get("on_target", 0)


def score(data):
    nominal = real = 0
    rows = []
    for entry in data:
        ins = on_target(entry, "insecure")
        sec = on_target(entry, "secure")
        rec = on_target(entry, "recommended")
        detected = ins > 0
        fired_on_fixed = sec > 0 or rec > 0
        # Real detection requires firing on the bug AND staying silent on the same program fixed.
        is_real = detected and not fired_on_fixed
        nominal += detected
        real += is_real
        rows.append((entry["class"], ins, sec, rec, detected, is_real))
    return nominal, real, rows


def main():
    data = load()
    nominal, real, rows = score(data)

    width = max(len(r[0]) for r in rows)
    print(f"{'class':{width}} {'ins':>4} {'sec':>4} {'rec':>4}  nominal  real")
    for name, ins, sec, rec, detected, is_real in rows:
        print(f"{name:{width}} {ins:>4} {sec:>4} {rec:>4}  {str(detected):>7}  {str(is_real):>4}")

    total = len(rows)
    print()
    print(f"nominal recall: {nominal}/{total}")
    print(f"real recall:    {real}/{total}")

    problems = []
    if total != EXPECTED_CLASSES:
        problems.append(f"expected {EXPECTED_CLASSES} classes, found {total}")
    if nominal != PUBLISHED_NOMINAL:
        problems.append(f"nominal recall {nominal} != published {PUBLISHED_NOMINAL}")
    if real != PUBLISHED_REAL:
        problems.append(f"real recall {real} != published {PUBLISHED_REAL}")

    if problems:
        print()
        for p in problems:
            print("MISMATCH:", p)
        print("RESULTS.md does not match the raw data. RESULTS.md is the thing that is wrong.")
        return 1

    print()
    print("OK: raw data reproduces the published result.")
    return 0


def demo():
    """Self-check on constructed data, so the scoring logic is testable without the corpus."""
    # Fires on the bug and stays silent on the fix: a real detection.
    good = [{"class": "x", "insecure": {"on_target": 1}, "secure": {"on_target": 0},
             "recommended": {"on_target": 0}}]
    n, r, _ = score(good)
    assert (n, r) == (1, 1), (n, r)

    # Fires on both: nominal only. This is the failure mode the benchmark exists to catch.
    shape_matcher = [{"class": "x", "insecure": {"on_target": 2}, "secure": {"on_target": 2},
                      "recommended": {"on_target": 0}}]
    n, r, _ = score(shape_matcher)
    assert (n, r) == (1, 0), (n, r)

    # Fires only on the fixed variant: not a detection at all.
    backwards = [{"class": "x", "insecure": {"on_target": 0}, "secure": {"on_target": 3},
                  "recommended": {"on_target": 0}}]
    n, r, _ = score(backwards)
    assert (n, r) == (0, 0), (n, r)

    # Missing variant key must not crash and must count as zero.
    sparse = [{"class": "x", "insecure": {"on_target": 1}}]
    n, r, _ = score(sparse)
    assert (n, r) == (1, 1), (n, r)

    print("demo: scoring logic OK")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        sys.exit(main())
