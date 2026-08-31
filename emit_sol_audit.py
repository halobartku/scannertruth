#!/usr/bin/env python3
"""Run our own scanner over a directory and emit findings in the shape the clock consumes.

Exists so sol-audit is measured by exactly the same pipeline as everyone else's tool. Until now our
own scores were computed by hand and were therefore not on the clock, which meant we could detect a
regression in somebody else's scanner and miss one in our own.
"""
import json, os, sys

def main():
    if len(sys.argv) < 3:
        print("usage: emit_sol_audit.py <scanner_dir> <corpus_dir> [out.json]"); return 2
    scanner_dir, corpus, out = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "sol-audit.json")
    sys.path.insert(0, scanner_dir)
    import scanner  # noqa: E402

    findings = []
    for root, dirs, files in os.walk(corpus):
        dirs[:] = [d for d in dirs if d not in (".git", "target", "node_modules")]
        for name in files:
            if not name.endswith(".rs"):
                continue
            p = os.path.join(root, name)
            try:
                src = open(p, encoding="utf-8", errors="replace").read()
                for f in scanner.scan_text(src, p) or []:
                    findings.append({
                        "rule_id": getattr(f, "rule_id", None) or (f.get("rule_id") if isinstance(f, dict) else ""),
                        "file": p.replace("\\", "/"),
                        "line": getattr(f, "line", None) or (f.get("line") if isinstance(f, dict) else 0),
                    })
            except Exception:
                # A crash counts as a miss, never an excuse. Same rule we apply to other tools.
                continue
    json.dump({"findings": findings}, open(out, "w", encoding="utf-8"), indent=1)
    print(f"{len(findings)} findings -> {out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
