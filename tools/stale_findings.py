#!/usr/bin/env python3
"""Count, per findings file, how many findings name a corpus file that no longer exists.

Corpus 2 was rebuilt on 2026-08-31 to pin one file per case (limitation 3). Two findings files
predate that rebuild and still name the files it removed. `score2.score_case` now refuses to
score on a path that does not resolve, so those findings cannot move a verdict any more. That fix
makes the problem invisible, which is the wrong kind of fixed: a run measured against a corpus
that no longer exists is weaker evidence than a run measured against this one, and a reader is
entitled to know which rows are in that position.

    python tools/stale_findings.py                 # print the table
    python tools/stale_findings.py --write <path>  # and record it as an artefact
    python tools/stale_findings.py --demo
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score2  # noqa: E402

# Kept in step with run_all.SOURCES_CORPUS2 by test_all.py.
SOURCES = {
    "radar": ("raw/c2-radar-current.json", "sol-audit"),
    "vaultlint": ("raw/c2-vaultlint-complete.json", "sol-audit"),
    "sol-audit": ("raw/c2-sol-audit.json", "sol-audit"),
}


def survey(sources=None):
    sources = sources or SOURCES
    out = {}
    for scanner, (path, kind) in sorted(sources.items()):
        if not os.path.exists(path):
            out[scanner] = {"file": path, "status": "missing"}
            continue
        findings = score2.load_findings(kind, path)
        total = sum(len(v) for v in findings.values())
        stale_paths, stale = [], 0
        for p, items in sorted(findings.items()):
            norm = str(p).replace("\\", "/")
            if not os.path.exists(norm):
                stale_paths.append({"path": norm, "findings": len(items)})
                stale += len(items)
        out[scanner] = {
            "file": path, "status": "read", "findings": total, "stale": stale,
            "stale_pct": round(100.0 * stale / total, 1) if total else 0.0,
            "stale_paths": stale_paths,
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        demo()
        return 0
    data = survey()
    print(f"{'scanner':12} {'findings':>9} {'stale':>7} {'stale %':>8}  file")
    for scanner, row in sorted(data.items()):
        if row["status"] != "read":
            print(f"{scanner:12} {'-':>9} {'-':>7} {'-':>8}  {row['file']} MISSING")
            continue
        print(f"{scanner:12} {row['findings']:>9} {row['stale']:>7} {row['stale_pct']:>7}%  "
              f"{row['file']}")
        for sp in row["stale_paths"]:
            print(f"{'':12} {sp['findings']:>9} findings on {sp['path']} (not in the corpus)")
    if args.write:
        payload = {"generated": "tools/stale_findings.py",
                   "meaning": "findings recorded against corpus files that no longer exist. "
                              "score2.score_case refuses to score on them, so they cannot move a "
                              "verdict; they are counted here so the weakness stays visible.",
                   "scanners": data}
        with open(args.write, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(payload, fh, indent=1)
            fh.write("\n")
        print(f"\nwritten: {args.write}")
    return 0


def demo():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        real = os.path.join(d, "real.rs")
        open(real, "w").write("x\n")
        blob = os.path.join(d, "f.json")
        with open(blob, "w") as fh:
            json.dump({"findings": [
                {"rule_id": "R", "file": real.replace("\\", "/"), "line": 1},
                {"rule_id": "R", "file": os.path.join(d, "gone.rs").replace("\\", "/"), "line": 1},
            ]}, fh)
        got = survey({"demo": (blob, "sol-audit")})["demo"]
        assert got["findings"] == 2 and got["stale"] == 1, got
        assert got["stale_paths"][0]["path"].endswith("gone.rs"), got
    print("stale_findings: OK")


if __name__ == "__main__":
    sys.exit(main())
