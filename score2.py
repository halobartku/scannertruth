#!/usr/bin/env python3
"""Score corpus 2 properly. Fixes limitations 1 and 2 in KNOWN-LIMITATIONS.md.

The first pass at corpus 2 counted findings of any kind, anywhere in the file, while the teaching
corpus counted only rules mapped to the vulnerability class. Those answer different questions and
should never have appeared in one table. This scorer closes both gaps:

**Mapped rules only.** Each case declares its vulnerability class. Each scanner has a published
class-to-rule mapping. A finding counts only if its rule is the one that claims to detect this class.

**Located, not just present.** A finding counts only if it lands on or near a line the fix actually
changed. A rule firing on line 5 of a 200-line production file for unrelated reasons is not a
detection of the bug on line 140, and at file granularity those are indistinguishable.

Three outcomes per case, and the middle one is the interesting one:

    detected  - a mapped rule fires at the fix site on the vulnerable variant and not on the fixed one
    unlocated - a mapped rule fires somewhere in the vulnerable file, but not at the fix site
    missed    - no mapped rule fires at all

`unlocated` exists because collapsing it into `detected` is exactly the flattery this benchmark is
supposed to remove, and collapsing it into `missed` would be unfair to the tool.
"""
import argparse
import difflib
import json
import os
import sys

TOLERANCE = 3  # lines either side of a changed region; fixes shift line numbers


def changed_lines(insecure_path, secure_path):
    """Line numbers IN THE VULNERABLE FILE that the fix altered or removed."""
    with open(insecure_path, encoding="utf-8", errors="replace") as fh:
        a = fh.readlines()
    with open(secure_path, encoding="utf-8", errors="replace") as fh:
        b = fh.readlines()
    hit = set()
    for tag, i1, i2, _, _ in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal":
            continue
        # 'insert' has i1 == i2: the fix added lines. Mark the seam, since a rule that should have
        # fired would fire where the missing check belonged.
        for line in range(i1 + 1, max(i2, i1 + 1) + 1):
            hit.add(line)
    return hit


def near(line, targets, tol=TOLERANCE):
    return any(abs(line - t) <= tol for t in targets)


def normalise(name):
    """Corpus 1 names classes `10-sysvar-address-checking`, corpus 2 `sysvar-address-checking`.

    One mapping must serve both, so the numeric prefix is stripped before matching. Without this
    every class silently reports `no-rule`, which is at least loud, but wrong.
    """
    return name.split("-", 1)[1] if name.split("-", 1)[0].isdigit() else name


def rules_for(mapping, class_name):
    want = normalise(class_name)
    for key, rules in mapping.items():
        if normalise(key) == want:
            return {r.lower() for r in rules}
    return set()


def score_case(case_dir, class_name, mapping, findings_by_path):
    """findings_by_path: {absolute-ish path: [(rule_id, line), ...]}"""
    rules = rules_for(mapping, class_name)
    if not rules:
        return "no-rule", {"reason": f"scanner has no rule mapped to class '{class_name}'"}

    ins_dir = os.path.join(case_dir, "insecure", "src")
    if not os.path.isdir(ins_dir):
        return "no-case", {}

    fired_anywhere = False
    fired_at_site = False
    fired_on_fixed = False

    for name in sorted(os.listdir(ins_dir)):
        if not name.endswith(".rs"):
            continue
        ins = os.path.join(ins_dir, name)
        sec = os.path.join(case_dir, "secure", "src", name)
        targets = changed_lines(ins, sec) if os.path.exists(sec) else set()

        for path, items in findings_by_path.items():
            p = path.replace("\\", "/")
            if not p.endswith("/" + name):
                continue
            on_fixed = "/secure/" in p
            for rule_id, line in items:
                if (rule_id or "").lower() not in rules:
                    continue
                if on_fixed:
                    fired_on_fixed = True
                    continue
                fired_anywhere = True
                if targets and near(line, targets):
                    fired_at_site = True

    if fired_at_site and not fired_on_fixed:
        return "detected", {}
    if fired_at_site and fired_on_fixed:
        return "unlocated", {"reason": "fires at the fix site but also on the fixed variant"}
    if fired_anywhere:
        return "unlocated", {"reason": "mapped rule fires in the file but not at the fix site"}
    return "missed", {}


def demo():
    """Self-check the two things that decide whether a case is scored honestly."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.rs")
        b = os.path.join(d, "b.rs")
        open(a, "w").write("one\ntwo\nBUG\nfour\n")
        open(b, "w").write("one\ntwo\nFIXED\nfour\n")
        ch = changed_lines(a, b)
        assert 3 in ch, ch
        assert 1 not in ch and 4 not in ch, ch

        # a pure addition marks the seam rather than nothing
        open(b, "w").write("one\ntwo\nCHECK\nBUG\nfour\n")
        ch2 = changed_lines(a, b)
        assert ch2, "an added guard must still mark a location in the vulnerable file"

    assert near(10, {12}) and not near(10, {20})

    assert normalise("10-sysvar-address-checking") == "sysvar-address-checking"
    assert normalise("sysvar-address-checking") == "sysvar-address-checking"
    m = {"10-sysvar-address-checking": ["Unvalidated Sysvar Account"]}
    assert rules_for(m, "sysvar-address-checking") == {"unvalidated sysvar account"}
    assert rules_for(m, "owner-checks") == set()
    print("score2: OK")


def load_findings(kind, path):
    with open(path, encoding="utf-8") as fh:
        blob = json.load(fh)
    out = {}
    if kind == "radar":
        for item in blob or []:
            for loc in item.get("locations") or []:
                parts = loc.split(":")
                if len(parts) >= 2 and parts[1].isdigit():
                    out.setdefault(parts[0], []).append((item.get("name", ""), int(parts[1])))
    elif kind in ("vaultlint", "sol-audit"):
        for x in (blob.get("findings") if isinstance(blob, dict) else blob) or []:
            out.setdefault(x.get("file", ""), []).append((x.get("rule_id", ""), x.get("line", 0)))
    elif kind == "semgrep":
        for r in (blob.get("results") if isinstance(blob, dict) else blob) or []:
            line = (r.get("start") or {}).get("line", 0)
            out.setdefault(r.get("path", ""), []).append((r.get("check_id", ""), line))
    elif kind == "solsec":
        for x in blob.get("analysis_results") or []:
            fp = x.get("file_path", "")
            if fp.startswith("./"):
                fp = fp[2:]
            out.setdefault(fp, []).append((x.get("rule_name", ""), x.get("line_number", 0)))
    else:
        raise ValueError(kind)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="corpus2")
    ap.add_argument("--manifest", default="corpus2/manifest.json")
    ap.add_argument("--scanner", required=False)
    ap.add_argument("--kind", required=False)
    ap.add_argument("--findings", required=False)
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        demo()
        return 0

    cases = json.load(open(args.manifest, encoding="utf-8"))["cases"]
    mapping = json.load(open(f"mappings/{args.scanner}.json", encoding="utf-8"))["map"]
    findings = load_findings(args.kind, args.findings)

    tally = {}
    print(f"{'case':30} {'class':28} {'verdict':10} note")
    for c in cases:
        d = os.path.join(args.corpus, c["name"])
        if not os.path.isdir(d):
            continue
        verdict, info = score_case(d, c["class"], mapping, findings)
        tally[verdict] = tally.get(verdict, 0) + 1
        print(f"{c['name']:30} {c['class']:28} {verdict:10} {info.get('reason','')}")
    print()
    print(f"{args.scanner}: " + "  ".join(f"{k}={v}" for k, v in sorted(tally.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
