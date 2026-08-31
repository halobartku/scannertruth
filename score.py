#!/usr/bin/env python3
"""Score any scanner's findings against the corpus, using its own mapping file.

Same scoring rules as PROTOCOL.md, applied identically to every scanner:
  nominal = the class's rule fired on that class's `insecure` variant
  real    = nominal AND it did not fire on that class's `secure` or `recommended` variant
"""
import json, sys, collections

VARIANTS = ("insecure", "secure", "recommended")


def variant_of(path, cls):
    """Which variant of THIS class does this path belong to? None if it is another class."""
    if f"/{cls}/" not in path.replace("\\", "/"):
        return None
    for v in VARIANTS:
        if f"/{v}/" in path.replace("\\", "/"):
            return v
    return None


def score(findings, mapping):
    """findings: iterable of (rule_id, path). mapping: {class: [rule ids]}"""
    rows = []
    for cls, rules in mapping.items():
        counts = collections.Counter()
        rules_lower = {r.lower() for r in rules}
        for rule_id, path in findings:
            if (rule_id or "").lower() not in rules_lower:
                continue
            v = variant_of(path, cls)
            if v:
                counts[v] += 1
        nominal = counts["insecure"] > 0
        real = nominal and counts["secure"] == 0 and counts["recommended"] == 0
        rows.append((cls, counts["insecure"], counts["secure"], counts["recommended"],
                     nominal, real))
    rows.sort()
    return rows


def report(name, rows):
    n = len(rows)
    nom = sum(1 for r in rows if r[4])
    real = sum(1 for r in rows if r[5])
    print(f"=== {name} ===")
    print(f"{'class':30} {'ins':>4} {'sec':>4} {'rec':>4}  {'nominal':>7} {'real':>5}")
    for cls, i, s, rc, no, re_ in rows:
        print(f"{cls:30} {i:>4} {s:>4} {rc:>4}  {str(no):>7} {str(re_):>5}")
    print(f"\nNOMINAL {nom}/{n}   REAL {real}/{n}\n")
    return nom, real


def demo():
    """Self-check on constructed findings, independent of any real scanner."""
    m = {"c1": ["R1"], "c2": ["R2"], "c3": ["R3"]}
    f = [
        ("R1", "/x/c1/insecure/a.rs"),                                  # clean detection
        ("R2", "/x/c2/insecure/a.rs"), ("R2", "/x/c2/secure/a.rs"),     # fires on the fix too
        ("R3", "/x/c3/recommended/a.rs"),                               # only on the fixed variant
        ("R1", "/x/c2/insecure/a.rs"),                                  # right rule, wrong class
    ]
    rows = score(f, m)
    got = {r[0]: (r[4], r[5]) for r in rows}
    assert got["c1"] == (True, True), got
    assert got["c2"] == (True, False), got
    assert got["c3"] == (False, False), got
    print("score: OK")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo(); raise SystemExit
    mapping = json.load(open(sys.argv[1], encoding="utf-8"))
    raw = json.load(open(sys.argv[2], encoding="utf-8"))
    findings = []
    for item in raw:
        for loc in item.get("locations", []) or []:
            findings.append((item.get("name", ""), loc.split(":")[0]))
    report(mapping["scanner"], score(findings, mapping["map"]))
