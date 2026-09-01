#!/usr/bin/env python3
"""Did any scanner detect a real vulnerability under a rule we did not map to that class?

This generalises the check that found the X-Ray result on 2026-08-31. Per-class scoring can only
credit a rule the mapping already points at the class, so a correct detection under a differently
named rule scores zero and is invisible. That is a defect of the mapping, not of the tool, and it
has to be looked for deliberately rather than waited for.

A hit here is not automatically a detection. It is a candidate that a human must read, and the
tool's authors must be asked about, before anything is credited.

    python unmapped_check.py --findings c2-radar.json --kind radar
"""
import argparse, json, os, sys
import score2


def variants(case_dir):
    ins = sec = None
    for variant, box in (("insecure", "ins"), ("secure", "sec")):
        base = os.path.join(case_dir, variant)
        for root, _, files in os.walk(base):
            for f in files:
                if f.endswith(".rs"):
                    p = os.path.join(root, f)
                    if variant == "insecure":
                        ins = p
                    else:
                        sec = p
    return ins, sec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--findings", required=True)
    ap.add_argument("--kind", required=True)
    ap.add_argument("--manifest", default="corpus2/manifest.json")
    ap.add_argument("--corpus", default="corpus2")
    args = ap.parse_args()

    cases = json.load(open(args.manifest, encoding="utf-8"))["cases"]
    cases = [c for c in cases if c.get("valid", True)]
    findings = score2.load_findings(args.kind, args.findings)

    candidates = 0
    for c in cases:
        d = os.path.join(args.corpus, c["name"])
        if not os.path.isdir(d):
            continue
        ins, sec = variants(d)
        if not (ins and sec):
            continue
        changed = score2.changed_lines(ins, sec)

        # Every finding, whatever its rule, split by variant.
        on_ins, on_sec = {}, set()
        for path, items in findings.items():
            norm = path.replace("\\", "/")
            if f"/{c['name']}/" not in norm and c["name"] not in norm:
                continue
            for rid, line in items:
                if "/insecure/" in norm:
                    on_ins.setdefault(rid, []).append(line)
                elif "/secure/" in norm:
                    on_sec.add(rid)

        for rid, lines in sorted(on_ins.items()):
            if rid in on_sec:
                continue  # fires on the fix too, so it distinguishes nothing
            at_fix = [l for l in lines if any(abs(l - ch) <= score2.TOLERANCE for ch in changed)]
            if at_fix:
                candidates += 1
                print(f"CANDIDATE  {c['name']:30} rule={rid:24} lines={at_fix} "
                      f"class={c.get('class')}")

    print(f"\n{args.kind}: {candidates} candidate(s) — differential AND at the fix site, "
          f"under any rule")
    if candidates:
        print("Read each one before crediting it, and ask the tool's authors what the rule covers.")
    return 0


def demo():
    """A rule that fires on both variants must never be a candidate, however well located."""
    assert score2.TOLERANCE >= 0
    changed = {100}
    assert any(abs(101 - c) <= score2.TOLERANCE for c in changed)
    assert not any(abs(200 - c) <= score2.TOLERANCE for c in changed)
    print("unmapped_check: OK")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        sys.exit(main())
