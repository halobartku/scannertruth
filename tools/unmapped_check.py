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


def candidates(cases, corpus_dir, findings):
    """Rules that fire at the fix site on the vulnerable variant and nowhere on the fixed one.

    Returned rather than printed, so the decision this makes can be tested. Until 2026-09-01 the
    only test named for this module called `score2.changed_lines` and never imported this one, so
    deleting the "fires on the fix too" guard below - the entire difference between a candidate
    detection and a shape match - changed nothing anybody could see.
    """
    out = []
    for c in cases:
        d = os.path.join(corpus_dir, c["name"])
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
                out.append({"case": c["name"], "rule": rid, "lines": at_fix,
                            "class": c.get("class")})
    return out


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

    found = candidates(cases, args.corpus, findings)
    for c in found:
        print(f"CANDIDATE  {c['case']:30} rule={c['rule']:24} lines={c['lines']} "
              f"class={c['class']}")

    print(f"\n{args.kind}: {len(found)} candidate(s) - differential AND at the fix site, "
          f"under any rule")
    if found:
        print("Read each one before crediting it, and ask the tool's authors what the rule covers.")
    return 0


def demo():
    """A rule that fires on both variants must never be a candidate, however well located.

    Driven through `candidates` itself. This used to re-implement the tolerance arithmetic beside
    the module instead of calling into it, so it agreed with itself no matter what the module did.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        case = os.path.join(d, "case")
        for variant, text in (("insecure", "a\nb\nBUG\nd\n"),
                              ("secure", "a\nb\nguard()\nBUG\nd\n")):
            sub = os.path.join(case, variant, "src")
            os.makedirs(sub)
            with open(os.path.join(sub, "lib.rs"), "w", encoding="utf-8") as fh:
                fh.write(text)
        cases = [{"name": "case", "class": "owner-checks"}]
        ins = "case/insecure/src/lib.rs"
        sec = "case/secure/src/lib.rs"

        hit = candidates(cases, d, {ins: [("ANY-RULE", 3)]})
        assert len(hit) == 1 and hit[0]["rule"] == "ANY-RULE", hit

        both = candidates(cases, d, {ins: [("ANY-RULE", 3)], sec: [("ANY-RULE", 3)]})
        assert both == [], f"a rule firing on the fix too is not a candidate: {both}"

        far = candidates(cases, d, {ins: [("ANY-RULE", 400)]})
        assert far == [], f"a finding nowhere near the fix is not a candidate: {far}"
    print("unmapped_check: OK")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        sys.exit(main())
