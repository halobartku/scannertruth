#!/usr/bin/env python3
"""Regenerate and score the calibration controls on corpus 1, the teaching corpus.

Corpus 2 has had a real noisy control since 2026-08-31: `control_c2.every_rule()` emits under
**every rule id any mapping claims**, which is what makes its zero mean something. Corpus 1 never
did. `raw/c1-control-noisy.json` emitted all 931 of its findings under one invented rule id,
`NOISY-ALL`, which appears in no mapping, so `tools/score.py` discarded every one of them before
scoring and the control scored 0/11 nominal.

That is not the published figure. `11 / 11 nominal, 0 / 11 real` was published on the front page,
on two results pages and in the roadmap, and it does not reproduce from the raw file. Worse than
an arithmetic slip: an unmapped rule id scores zero **by construction**, so the corpus-1 control
demonstrated nothing at all about whether volume can buy a score, while being cited as the reason
it cannot. Error 33.

This tool is the corpus-1 half of `control_c2.py`, built the same way:

- **control-noisy** flags every non-empty line of every `.rs` file of every variant, under every
  rule id any mapping in `mappings/` claims. If it ever scores a real detection, the scorer is
  crediting volume and every published number rests on sand.
- **control-null** reports nothing and must also score zero, so the floor is measured.

Corpus 1 is not vendored in this repository (a known limitation). Two modes, and both are honest
about which one ran:

    python tools/control_c1.py --corpus <checkout>   # walk a real sealevel-attacks checkout
    python tools/control_c1.py                       # rebuild from raw/c1-control-inventory.json

The second mode reads the line inventory out of the existing artefact and re-emits it under the
current rule set. That inventory was checked against the upstream corpus at the pinned commit
24555d044802db4022112a94d6d70e74291a4b6d on 2026-09-01: 35 files, 931 non-empty lines, every
per-file count identical. So the coverage the original control recorded was right. Only its rule
id was wrong.
"""
import argparse
import collections
import json
import os
import sys

import score
try:
    import control_c2
except ImportError:  # running from tools/ with a different sys.path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import control_c2

CORPUS_COMMIT = "24555d044802db4022112a94d6d70e74291a4b6d"
CORPUS_NAME = "coral-xyz/sealevel-attacks"
PATH_PREFIX = "/tmp/sealevel-attacks/programs"
NOISY = "raw/c1-control-noisy.json"
NULL = "raw/c1-control-null.json"
# The committed artefact is the INVENTORY, not the findings.
#
# The noisy control is every mapped rule id on every flagged line: 931 lines times 88 rules is
# 81,928 findings on corpus 1, and the same construction on corpus 2 is 2.4 million and 296 MB.
# Committing a deterministically regenerable file of that size is how this repository came to be
# 49 MB of which 45 was one generated control (audit row 47). What is worth committing is the
# thing that cannot be regenerated without the network: which lines of which files the pinned
# corpus actually has. That is 20 KB, it is checkable against upstream, and every control on this
# corpus is derivable from it plus `mappings/`.
INVENTORY = "raw/c1-control-inventory.json"


def inventory_from_checkout(root):
    """{path: [line numbers of the non-empty lines]} for every .rs file under <checkout>/programs.

    Line numbers, not a count. The control flags the line it saw, so line 45 of a file with 39
    non-empty lines is a real record and `range(1, count+1)` would be a fabricated one.
    """
    programs = os.path.join(root, "programs")
    if not os.path.isdir(programs):
        programs = root
    inv = {}
    for dirpath, _dirs, files in os.walk(programs):
        for fn in sorted(files):
            if not fn.endswith(".rs"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, programs).replace("\\", "/")
            with open(full, encoding="utf-8", errors="replace") as fh:
                inv[PATH_PREFIX + "/" + rel] = [i for i, line in enumerate(fh, 1) if line.strip()]
    return inv


def inventory_from_artefact(path=INVENTORY):
    """{path: [line numbers]} out of the committed inventory, or out of a findings file.

    Corpus 1 is not vendored here, so the inventory is what makes the control reproducible
    offline. Verified against upstream at the pinned commit, see the module docstring.
    """
    with open(path, encoding="utf-8") as fh:
        blob = json.load(fh)
    if "lines" in blob:
        return {k: list(v) for k, v in blob["lines"].items()}
    inv = collections.defaultdict(set)
    for item in blob.get("findings") or []:
        inv[item["file"]].add(int(item["line"]))
    return {k: sorted(v) for k, v in inv.items()}


def write_inventory(inventory, path=INVENTORY):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"corpus": CORPUS_NAME, "corpus_commit": CORPUS_COMMIT,
                   "what": "non-empty line numbers of every .rs file in the pinned teaching "
                           "corpus. The noisy control is this inventory crossed with every rule "
                           "id in mappings/, so the control regenerates from what is committed "
                           "here without a network fetch.",
                   "files": len(inventory),
                   "non_empty_lines": sum(len(v) for v in inventory.values()),
                   "lines": {k: inventory[k] for k in sorted(inventory)}}, fh, indent=1)
        fh.write("\n")


def noisy_findings(inventory, rules):
    out = []
    for path in sorted(inventory):
        for line in inventory[path]:
            for rule in rules:
                out.append({"rule_id": rule, "file": path, "line": line})
    return out


def report(findings, label):
    """Score the control against every mapping. The worst case is what matters."""
    pairs = [(f["rule_id"], f["file"]) for f in findings]
    worst_nominal, worst_real = 0, 0
    for fn in sorted(os.listdir("mappings")):
        if not fn.endswith(".json"):
            continue
        mapping = json.load(open(os.path.join("mappings", fn), encoding="utf-8"))["map"]
        rows = score.score(pairs, mapping)
        nom = sum(1 for r in rows if r[4])
        real = sum(1 for r in rows if r[5])
        worst_nominal = max(worst_nominal, nom)
        worst_real = max(worst_real, real)
        print(f"  {label} vs {fn[:-5]:34} nominal={nom}/{len(rows)} real={real}/{len(rows)}")
    return worst_nominal, worst_real


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", help="a sealevel-attacks checkout at " + CORPUS_COMMIT)
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        demo()
        return 0

    if args.corpus:
        inventory = inventory_from_checkout(args.corpus)
        source = f"walked {args.corpus}"
        recorded = inventory_from_artefact() if os.path.exists(INVENTORY) else {}
        if recorded and recorded != inventory:
            print("WARNING: the checkout does not match the recorded inventory. Differences:")
            for k in sorted(set(recorded) | set(inventory)):
                if recorded.get(k) != inventory.get(k):
                    print(f"  {k}: artefact={recorded.get(k)} checkout={inventory.get(k)}")
    else:
        inventory = inventory_from_artefact()
        source = f"rebuilt from the line inventory recorded in {INVENTORY}"

    rules = control_c2.every_rule()
    findings = noisy_findings(inventory, rules)
    lines = sum(len(v) for v in inventory.values())
    print(f"corpus 1: {len(inventory)} files, {lines} non-empty lines, "
          f"{len(rules)} distinct mapped rules ({source})\n")

    os.makedirs("raw", exist_ok=True)
    write_inventory(inventory)
    with open(NOISY, "w", encoding="utf-8") as fh:
        json.dump({"scanner": "control-noisy", "corpus": CORPUS_NAME,
                   "corpus_commit": CORPUS_COMMIT, "lines_flagged": lines,
                   "rules": len(rules), "findings": findings}, fh)
    with open(NULL, "w", encoding="utf-8") as fh:
        json.dump({"scanner": "control-null", "corpus": CORPUS_NAME,
                   "corpus_commit": CORPUS_COMMIT, "findings": []}, fh)
    print(f"control-noisy: {len(findings):,} findings written to {NOISY}")
    print(f"               ({lines} lines x {len(rules)} rules)\n")

    n_nom, n_real = report(findings, "noisy")
    print()
    z_nom, z_real = report([], "null ")
    print()
    if n_real == 0 and z_real == 0:
        print(f"CONTROLS PASS: noisy scores {n_real} real recall despite {len(findings):,} "
              f"findings and {n_nom} nominal, null scores 0.")
        print("Nominal recall CAN be bought with volume, which is why this project does not "
              "publish nominal recall as a result. Real recall cannot.")
        return 0
    print(f"CONTROLS FAIL: noisy real={n_real}, null real={z_real}. A control scoring above zero "
          "means the scorer is crediting volume, and every corpus-1 number is suspect.")
    return 1


def demo():
    """Self-check the two things that would silently break: the inventory and the rule fan-out."""
    inv = {PATH_PREFIX + "/0-signer-authorization/insecure/src/lib.rs": [1, 2, 7],
           PATH_PREFIX + "/0-signer-authorization/secure/src/lib.rs": [4, 9]}
    out = noisy_findings(inv, ["R1", "R2"])
    assert len(out) == (3 + 2) * 2, len(out)
    assert {f["rule_id"] for f in out} == {"R1", "R2"}
    # the recorded line number survives; a blank line 3 is not invented as a finding
    assert sorted({f["line"] for f in out if f["file"].endswith("insecure/src/lib.rs")}) == [1, 2, 7]

    # The defect this tool exists to fix: one unmapped rule id scores zero by construction,
    # which is not evidence of anything. Under a rule the mapping knows, the control reaches
    # every class it flags. Both halves are asserted, so neither can regress in silence.
    mapping = {"0-signer-authorization": ["R1"]}
    unmapped = [(f["rule_id"], f["file"]) for f in noisy_findings(inv, ["NOISY-ALL"])]
    rows = score.score(unmapped, mapping)
    assert sum(1 for r in rows if r[4]) == 0, "an unmapped rule id cannot reach the scorer"
    mapped = [(f["rule_id"], f["file"]) for f in out]
    rows = score.score(mapped, mapping)
    assert sum(1 for r in rows if r[4]) == 1, "a mapped rule id must reach nominal recall"
    assert sum(1 for r in rows if r[5]) == 0, "and must never reach real recall, it fires on both"
    print("control_c1: OK")


if __name__ == "__main__":
    sys.exit(main())
