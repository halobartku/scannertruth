#!/usr/bin/env python3
"""Run the calibration controls over corpus 2, which they had never covered.

`control-noisy` and `control-null` established the ceiling and the floor on the teaching corpus.
The corpus that carries this project's headline had neither. That is a real gap: a corpus where
every measured tool scores zero looks identical whether the tools miss everything or the scoring
cannot award a hit.

- **control-noisy** flags every non-empty line of every file, under every rule the mapping knows.
  It is the tool a findings-count metric ranks first. On this corpus it must score **zero**: it
  fires just as loudly on the fixed variant, so nothing it says distinguishes a bug from its repair.
- **control-null** reports nothing and must also score zero. It exists so the floor is measured
  rather than assumed.

If noisy ever scores above zero here, the scorer is crediting volume and the headline is worthless.

    python control_c2.py            # writes c2-control-noisy.json, c2-control-null.json and scores
"""
import json
import os
import sys

import score2

CORPUS = "corpus2"
MANIFEST = os.path.join(CORPUS, "manifest.json")


def every_rule(mappings_dir="mappings"):
    """Every rule id any scanner claims, so the noisy control cannot be excused as unmapped."""
    rules = set()
    for fn in sorted(os.listdir(mappings_dir)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(mappings_dir, fn), encoding="utf-8") as fh:
            m = json.load(fh)
        for rule_list in (m.get("map") or {}).values():
            rules.update(rule_list)
    return sorted(rules)


def noisy_findings(cases, rules):
    """Every rule, on every non-empty line, of every file, in BOTH variants.

    Both variants is the point. A control that only shouted at the vulnerable side would score a
    perfect run and prove nothing; the reason noisy scores zero is that it cannot tell the two apart.
    """
    out = []
    for c in cases:
        for variant in ("insecure", "secure"):
            d = os.path.join(CORPUS, c["name"], variant, "src")
            if not os.path.isdir(d):
                continue
            for fn in sorted(os.listdir(d)):
                if not fn.endswith(".rs"):
                    continue
                path = os.path.join(d, fn)
                with open(path, encoding="utf-8", errors="replace") as fh:
                    lines = fh.readlines()
                for i, line in enumerate(lines, 1):
                    if not line.strip():
                        continue
                    for r in rules:
                        out.append({"rule_id": r, "file": path.replace("\\", "/"),
                                    "line": i})
    return out


def score(label, findings_file, cases):
    """Score the control against every scanner's mapping; the worst case is what matters."""
    findings = score2.load_findings("sol-audit", findings_file)
    worst = {}
    for fn in sorted(os.listdir("mappings")):
        if not fn.endswith(".json"):
            continue
        scanner = fn[:-5]
        doc = json.load(open(os.path.join("mappings", fn), encoding="utf-8"))
        if "map" not in doc:
            # mappings/model-classes.json is a post-hoc adjudication of model answers, not a rule map
            continue
        mapping = doc["map"]
        tally = {}
        for c in cases:
            d = os.path.join(CORPUS, c["name"])
            if not os.path.isdir(d):
                continue
            v, _ = score2.score_case(d, c["class"], mapping, findings)
            tally[v] = tally.get(v, 0) + 1
        worst[scanner] = tally.get("detected", 0)
        print(f"  {label} vs {scanner:16} detected={tally.get('detected', 0)} "
              f"unlocated={tally.get('unlocated', 0)} missed={tally.get('missed', 0)} "
              f"no-rule={tally.get('no-rule', 0)}")
    return max(worst.values()) if worst else 0


def main():
    cases = json.load(open(MANIFEST, encoding="utf-8"))["cases"]
    cases = [c for c in cases if c.get("valid", True)]
    # The header counted the manifest and every row below counts the directory, so this tool
    # printed one denominator and then scored against another, with no reconciliation, in the
    # tool whose whole job is to make the denominator trustworthy. Say all three.
    built = [c for c in cases if os.path.isdir(os.path.join(CORPUS, c["name"]))]
    rules = every_rule()
    print(f"corpus 2: {len(cases)} valid cases, {len(built)} built, "
          f"{len(cases) - len(built)} not-built; every row below is scored over the "
          f"{len(built)} built. {len(rules)} distinct mapped rules\n")

    noisy = noisy_findings(cases, rules)
    with open("raw/c2-control-noisy.json", "w", encoding="utf-8") as fh:
        json.dump({"findings": noisy}, fh)
    with open("raw/c2-control-null.json", "w", encoding="utf-8") as fh:
        json.dump({"findings": []}, fh)
    print(f"control-noisy: {len(noisy):,} findings written\n")

    n = score("noisy", "raw/c2-control-noisy.json", cases)
    print()
    z = score("null ", "raw/c2-control-null.json", cases)

    print()
    if n == 0 and z == 0:
        print("CONTROLS PASS: noisy scores 0 despite "
              f"{len(noisy):,} findings, null scores 0.")
        print("Real recall on corpus 2 cannot be bought with volume, so every zero "
              "published from this corpus is a real zero.")
        return 0
    print(f"CONTROLS FAIL: noisy={n}, null={z}. A control scoring above zero means the "
          "scorer is crediting volume. Every corpus-2 result is suspect until this is fixed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
