#!/usr/bin/env python3
"""Score a scanner's real-crate run, with the same semantics `score2.py` uses on corpus 2.

`score2.py` cannot read a real-crate run, and the difference is one line of layout rather than
of method: corpus 2 puts the implicated file at `<case>/<variant>/src/<basename>`, while a real
crate keeps the project's own tree, so the same file sits at
`<case>/<variant>/<repo-relative path>`. Everything that decides a verdict is imported from
`score2` rather than reimplemented here, so the two scorers cannot drift:

    changed_lines   what the fix altered, in the vulnerable file
    near            the +/- 3 line tolerance
    rules_for       the pre-registered class-to-rule mapping, normalised across both corpora
    load_findings   the scanner envelopes

Verdicts, unchanged from score2:

    detected     a mapped rule fires at the fix site on the vulnerable variant and not on the fix
    unlocated    a mapped rule fires in the file, but not at the fix site, or fires on the fix too
    missed       no mapped rule fires in the implicated file
    no-rule      the pre-registered mapping claims no rule for this class
    unavailable  the run log says one of the two variants was not analysed. NEVER a zero.

Plus one thing score2 does not do, because on a real crate it matters more: `--candidates`
reports every rule of any kind that fires at the fix site on the vulnerable variant and nowhere
in the fixed file. That is the `unmapped_check.py` question, asked per case: a detection hiding
under a rule the pre-registered mapping does not claim.

Usage:
    python3 rc_score.py --scanner sol-audit --kind sol-audit --findings rc-sol-audit-strict.json \
        --crates /tmp/rc-crates --manifest corpus2/manifest.json --log rc-sol-audit-strict.json.log
    python3 rc_score.py --demo
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score2  # noqa: E402


def coverage(log_path):
    """{leaf: status} from the per-invocation log, or None when there is no log at all.

    No log means the honest verdict is `unknown`, not zero: a findings file cannot tell a case
    that was analysed and came back empty from a case nobody opened. Errors 20, 21 and 32.
    """
    if not log_path or not os.path.exists(log_path):
        return None
    with open(log_path, encoding="utf-8") as fh:
        return {e.get("leaf"): e.get("status") for e in json.load(fh)}


def findings_in(findings_by_path, leaf, rel):
    """Findings recorded against `<leaf>/<rel>`, as [(rule, line)]."""
    want = (leaf + "/" + rel).replace("\\", "/")
    out = []
    for path, items in findings_by_path.items():
        if path.replace("\\", "/") == want:
            out.extend(items)
    return out


def score_case(case, crates_root, mapping, findings_by_path, cover):
    name, klass = case["name"], case["class"]
    files = case.get("files") or []
    ins_leaf, sec_leaf = name + "/insecure", name + "/secure"

    if cover is not None:
        for leaf in (ins_leaf, sec_leaf):
            if cover.get(leaf) != "ok":
                return "unavailable", {"reason": "run log says %s is %s"
                                                 % (leaf, cover.get(leaf) or "absent")}
    else:
        return "unknown", {"reason": "no per-invocation log, so coverage cannot be established"}

    rules = score2.rules_for(mapping, klass)
    fired_anywhere = fired_at_site = fired_on_fixed = False
    candidates, site_lines = [], 0

    for rel in files:
        ins = os.path.join(crates_root, name, "insecure", rel)
        sec = os.path.join(crates_root, name, "secure", rel)
        if not (os.path.exists(ins) and os.path.exists(sec)):
            continue
        targets = score2.changed_lines(ins, sec)
        site_lines += len(targets)
        ins_hits = findings_in(findings_by_path, ins_leaf, rel)
        sec_hits = findings_in(findings_by_path, sec_leaf, rel)
        sec_rules = {(r or "").lower() for r, _ in sec_hits}

        for rule, line in ins_hits:
            rid = (rule or "").lower()
            at_site = bool(targets) and score2.near(line, targets)
            if rid in rules:
                fired_anywhere = True
                if at_site:
                    fired_at_site = True
            if at_site and rid not in sec_rules:
                candidates.append({"rule": rule, "file": rel, "line": line,
                                   "mapped": rid in rules})
        if any((r or "").lower() in rules for r, _ in sec_hits):
            fired_on_fixed = True

    if not site_lines:
        return "no-fix-site", {"reason": "the implicated file did not resolve in both variants"}
    if not rules:
        return "no-rule", {"reason": "the pre-registered mapping claims no rule for class "
                                     "'%s'" % klass, "candidates": candidates}
    if fired_at_site and not fired_on_fixed:
        return "detected", {"candidates": candidates}
    if fired_at_site and fired_on_fixed:
        return "unlocated", {"reason": "fires at the fix site but also on the fixed variant",
                             "candidates": candidates}
    if fired_anywhere:
        return "unlocated", {"reason": "mapped rule fires in the file but not at the fix site",
                             "candidates": candidates}
    return "missed", {"candidates": candidates}


def run(scanner, kind, findings_path, crates_root, manifest_path, log_path, mappings_dir,
        show_candidates=True, map_key="map"):
    """`map_key` selects which mapping in the file to score against.

    It exists for one published case and is not a knob to turn until a number improves.
    `mappings/xray.json` carries two: the pre-registered `map`, and `corrected_map`, which
    widens rule 1019 from one class to two after the pre-registration narrowed a generic rule
    on the strength of a vendor blog post (error 17). Both were published for corpus 2 and
    both are published here, together, whichever way the numbers fall.
    """
    cases = json.load(open(manifest_path, encoding="utf-8"))["cases"]
    mapping = json.load(open(os.path.join(mappings_dir, scanner + ".json"),
                             encoding="utf-8"))[map_key]
    findings = score2.load_findings(kind, findings_path)
    cover = coverage(log_path)

    tally, rows = {}, []
    print("%-38s %-32s %-12s %s" % ("case", "class", "verdict", "note"))
    for c in cases:
        if not c.get("valid", True):
            print("%-38s %-32s %-12s manifest marks the pair invalid"
                  % (c["name"], c["class"], "excluded"))
            tally["excluded"] = tally.get("excluded", 0) + 1
            continue
        if not os.path.isdir(os.path.join(crates_root, c["name"])):
            print("%-38s %-32s %-12s not built as a real crate"
                  % (c["name"], c["class"], "not-built"))
            tally["not-built"] = tally.get("not-built", 0) + 1
            continue
        verdict, info = score_case(c, crates_root, mapping, findings, cover)
        tally[verdict] = tally.get(verdict, 0) + 1
        rows.append({"case": c["name"], "class": c["class"], "verdict": verdict, **info})
        print("%-38s %-32s %-12s %s" % (c["name"], c["class"], verdict, info.get("reason", "")))
        if show_candidates:
            for cand in info.get("candidates") or []:
                print("      candidate at fix site, absent from the fix: %s  %s:%s%s"
                      % (cand["rule"], os.path.basename(cand["file"]), cand["line"],
                         "  [mapped]" if cand["mapped"] else "  [not in the mapping]"))
    print()
    print("%s: %s" % (scanner, "  ".join("%s=%d" % kv for kv in sorted(tally.items()))))
    return rows, tally


def demo():
    """The positive control, driven through the real-crate path resolution.

    score2's own control proves score2 can return `detected` for a corpus-2 layout. It says
    nothing about this file, which resolves the implicated file differently, and a scorer whose
    only observed output is zero is not evidence about anybody's tool.
    """
    import tempfile
    rel = "programs/thing/src/lib.rs"
    with tempfile.TemporaryDirectory() as d:
        crates = os.path.join(d, "crates")
        for variant, text in (("insecure", "a\nb\nvulnerable_line\nd\n"),
                              ("secure", "a\nb\nguard()\nvulnerable_line\nd\n")):
            p = os.path.join(crates, "case", variant, rel)
            os.makedirs(os.path.dirname(p))
            open(p, "w").write(text)
        case = {"name": "case", "class": "account-data-matching", "files": [rel]}
        mapping = {"1-account-data-matching": ["RULE-X"]}
        cover = {"case/insecure": "ok", "case/secure": "ok"}
        ins, sec = "case/insecure/" + rel, "case/secure/" + rel

        v, _ = score_case(case, crates, mapping, {ins: [("RULE-X", 3)]}, cover)
        assert v == "detected", "positive control returned %r, not detected" % v

        v, _ = score_case(case, crates, mapping,
                          {ins: [("RULE-X", 3)], sec: [("RULE-X", 3)]}, cover)
        assert v != "detected", "firing on the fix must not score detected: %r" % v

        v, _ = score_case(case, crates, mapping, {ins: [("RULE-X", 400)]}, cover)
        assert v == "unlocated", "off-site finding returned %r" % v

        v, _ = score_case(case, crates, mapping, {}, cover)
        assert v == "missed", "no findings should be a miss, not %r" % v

        v, info = score_case(case, crates, {"other-class": ["RULE-X"]},
                             {ins: [("RULE-X", 3)]}, cover)
        assert v == "no-rule", v

        # an unavailable run is never a zero
        v, _ = score_case(case, crates, mapping, {ins: [("RULE-X", 3)]},
                          {"case/insecure": "ok", "case/secure": "unavailable"})
        assert v == "unavailable", "a half-run pair must be unavailable, not %r" % v

        # a detection under a rule the mapping does not claim is still reported
        _, info = score_case(case, crates, mapping, {ins: [("OTHER-RULE", 3)]}, cover)
        names = [c["rule"] for c in info["candidates"]]
        assert names == ["OTHER-RULE"], names

        # no log at all is unknown, not a miss
        v, _ = score_case(case, crates, mapping, {}, None)
        assert v == "unknown", v
    print("rc_score: OK (including the positive control)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scanner")
    ap.add_argument("--kind")
    ap.add_argument("--findings")
    ap.add_argument("--crates", default="/tmp/rc-crates")
    ap.add_argument("--manifest", default="corpus2/manifest.json")
    ap.add_argument("--log")
    ap.add_argument("--mappings", default="mappings")
    ap.add_argument("--map-key", default="map",
                    help="which mapping in the file to score against; xray.json also carries "
                         "corrected_map, published beside the pre-registered one since error 17")
    ap.add_argument("--out")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        demo()
        return 0
    for required in ("scanner", "kind", "findings"):
        if not getattr(args, required):
            ap.error("--%s is required unless --demo" % required)
    log = args.log or (args.findings + ".log")
    rows, tally = run(args.scanner, args.kind, args.findings, args.crates, args.manifest,
                      log, args.mappings, map_key=args.map_key)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"scanner": args.scanner, "findings_file": args.findings,
                       "log": log, "map_key": args.map_key, "tally": tally, "cases": rows},
                      fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
