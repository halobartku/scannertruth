#!/usr/bin/env python3
"""Build `regression-pack-radar/`: corpus 2 as a one-command regression check for Radar.

Auditware's pain in Auditware/radar#34 was a noise reduction that killed real detections. This
pack lets them ask, on every rule change, two questions against 17 real vulnerabilities: does a
mapped rule still fire at the fix site of the vulnerable variant, and is it silent on the fixed one.

The pack is a copy of `corpus2/` in the layout the harness already uses, plus the scorer that
produced the published row, verbatim (`score2.py` is copied, not rewritten), a `run.sh` that
stages each variant the way `tools/spec/run.py` does for Radar (`wrapped-pkg`) and a `check.py`
that undoes the staging prefix and calls `score2.score_case`. Nothing in here is a second
implementation of anything that decides a published number.

Usage:
    python tools/regression_pack.py               # rebuild regression-pack-radar/ in place
    python tools/regression_pack.py --out DIR     # build somewhere else
    python tools/regression_pack.py --check       # exit 1 if the committed pack differs from a fresh build

The committed pack is derived, and `tests/regression_pack.py` fails when it drifts from a fresh
build, for the same reason the front-page numbers are re-derived: a stale copy is the error we
keep making.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import score2  # noqa: E402

DEFAULT_OUT = os.path.join(ROOT, "regression-pack-radar")
REFERENCE_RUN = "raw/c2-radar-24c56f9.json"   # the published row this pack is checked against
REFERENCE_REVISION = "24c56f9 (Auditware/radar main after #35, api image sha256:f205bf7a9af8..., 2026-09-02)"
CASES_DIR = "cases"
PACK_FILES = ("README.md", "run.sh", "check.py", "score2.py", "expected.json", "mapping.json", "manifest.json")


def valid_cases():
    manifest = json.load(open(os.path.join(ROOT, "corpus2", "manifest.json"), encoding="utf-8"))
    return [c for c in manifest["cases"] if c.get("valid", True)]


def _parent_of(name):
    for b in json.load(open(os.path.join(ROOT, "corpus2", "built.json"), encoding="utf-8")):
        if b["name"] == name:
            return b.get("parent")
    return None


def _mapped_rules(mapping, class_name):
    """Rule names as the mapping spells them (score2.rules_for lower-cases them for matching)."""
    for k, rules in mapping.items():
        if score2.normalise(k) == score2.normalise(class_name):
            return list(rules)
    return []


def _fix_sites(case_dir):
    """Per vulnerable file: the lines the fix changed, exactly as score2 computes them."""
    out = {}
    ins = os.path.join(case_dir, "insecure", "src")
    for f in sorted(os.listdir(ins)):
        if not f.endswith(".rs"):
            continue
        sec = os.path.join(case_dir, "secure", "src", f)
        if os.path.exists(sec):
            out[f"src/{f}"] = sorted(score2.changed_lines(os.path.join(ins, f), sec))
    return out


def _reference_verdicts(mapping, cases):
    """Our verdicts on the published run. Same call the results table came from."""
    findings = score2.load_findings("radar", os.path.join(ROOT, REFERENCE_RUN))
    out = {}
    for c in cases:
        v, info = score2.score_case(os.path.join(ROOT, "corpus2", c["name"]), c["class"], mapping, findings)
        out[c["name"]] = {"verdict": v, **({"reason": info["reason"]} if info.get("reason") else {})}
    return out


def build(out):
    cases = valid_cases()
    mapping_doc = json.load(open(os.path.join(ROOT, "mappings", "radar.json"), encoding="utf-8"))
    mapping = mapping_doc["map"]

    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, CASES_DIR))

    expected = []
    for c in cases:
        src = os.path.join(ROOT, "corpus2", c["name"])
        shutil.copytree(src, os.path.join(out, CASES_DIR, c["name"]))
        expected.append({
            "id": c["name"],
            "class": c["class"],
            "mapped_rules": _mapped_rules(mapping, c["class"]),
            "fix_sites": _fix_sites(src),
            "tolerance_lines": score2.TOLERANCE,
            "provenance": {
                "repo": c["repo"], "fix_commit": c["fix"], "parent_commit": _parent_of(c["name"]),
                "source": c.get("source"), "files": c.get("files", []),
                "license": "the upstream repository's own; these are unmodified excerpts of public source",
            },
            "note": c.get("note", ""),
        })

    reference = _reference_verdicts(mapping, cases)
    for e in expected:
        e["reference"] = reference[e["id"]]

    json.dump({"scanner": "radar", "reference_revision": REFERENCE_REVISION,
               "reference_run": REFERENCE_RUN,
               "verdicts": "detected | unlocated | missed | no-rule | unknown, defined in score2.py",
               "cases": expected},
              open(os.path.join(out, "expected.json"), "w", encoding="utf-8"), indent=1)
    json.dump(mapping_doc, open(os.path.join(out, "mapping.json"), "w", encoding="utf-8"), indent=1)
    json.dump({"cases": [{"name": c["name"], "class": c["class"]} for c in cases]},
              open(os.path.join(out, "manifest.json"), "w", encoding="utf-8"), indent=1)
    shutil.copy(os.path.join(ROOT, "tools", "score2.py"), os.path.join(out, "score2.py"))
    shutil.copy(os.path.join(ROOT, "tools", "pack", "check.py"), os.path.join(out, "check.py"))
    shutil.copy(os.path.join(ROOT, "tools", "pack", "run.sh"), os.path.join(out, "run.sh"))
    shutil.copy(os.path.join(ROOT, "tools", "pack", "README.md"), os.path.join(out, "README.md"))
    return out


def tree_hashes(root):
    out = {}
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            rel = os.path.relpath(p, root).replace("\\", "/")
            if rel.split("/")[0] in ("_staged", "results", "__pycache__"):
                continue
            out[rel] = hashlib.sha256(open(p, "rb").read().replace(b"\r\n", b"\n")).hexdigest()
    return out


def stale(committed=DEFAULT_OUT):
    """Files that differ between the committed pack and a fresh build. Empty means fresh."""
    with tempfile.TemporaryDirectory() as t:
        fresh = tree_hashes(build(os.path.join(t, "pack")))
    have = tree_hashes(committed) if os.path.isdir(committed) else {}
    return sorted(k for k in set(fresh) | set(have) if fresh.get(k) != have.get(k))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        diff = stale(a.out)
        for f in diff:
            print("stale:", f)
        print("regression pack:", "fresh" if not diff else f"{len(diff)} file(s) differ from a fresh build")
        return 1 if diff else 0
    build(a.out)
    n = len(os.listdir(os.path.join(a.out, CASES_DIR)))
    print(f"regression pack: {n} cases written to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
