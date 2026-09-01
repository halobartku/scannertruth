#!/usr/bin/env python3
"""The packaging objection, made into a comparison a reader can run.

Corpus 2 extracts the implicated file into a minimal crate so scanners will parse it. The
objection is that a verdict obtained that way may be an artefact of our packaging rather
than of the tool. The real crates are the same fix commits taken as the whole crate the
project ships, so the two differ in packaging and in nothing else.

This compares the two, case by case, for one scanner:

    real crate   read from the committed raw/rc-score-<scanner>.json, which rc_score.py
                 wrote from the real-crate run
    corpus 2     scored here, now, by score2.score_case, from the committed corpus-2
                 findings file and the same mapping

A reader needs no VPS and no rebuild of the real crates: both sides come out of the
repository. Only the real-crate SCORES are taken on trust, and they carry the run log that
produced them.

    python tools/rc_compare.py --scanner xray --kind radar --c2-findings raw/xray-c2-raw.json
    python tools/rc_compare.py --all
    python tools/rc_compare.py --demo
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score2  # noqa: E402

# (label, rc-score file, mapping file, map key, corpus-2 findings, envelope kind)
# The corpus-2 log is `<findings>.log` in every case; it is consulted, not assumed, because a
# corpus-2 verdict for a case the tool never ran on is silence being read as a zero, which is
# error 20 and must not become half of a comparison.
PAIRS = [
    ("sol-audit v3, strict", "raw/rc-score-sol-audit-strict.json", "sol-audit", "map",
     "raw/c2-sol-audit-v3-strict.json", "sol-audit"),
    ("sol-audit v3, broad", "raw/rc-score-sol-audit-broad.json", "sol-audit", "map",
     "raw/c2-sol-audit-v3-broad.json", "sol-audit"),
    ("sol-audit v3, all", "raw/rc-score-sol-audit-all.json", "sol-audit", "map",
     "raw/c2-sol-audit-v3-all.json", "sol-audit"),
    ("semgrep + SOL-0XX, narrow", "raw/rc-score-semgrep-solana-standard-c2.json",
     "semgrep-solana-standard-c2", "map", "raw/c2-semgrep-solana-standard.json", "semgrep"),
    ("semgrep + SOL-0XX, wide", "raw/rc-score-semgrep-solana-standard-c2-wide.json",
     "semgrep-solana-standard-c2-wide", "map", "raw/c2-semgrep-solana-standard.json", "semgrep"),
    ("solsec", "raw/rc-score-solsec.json", "solsec", "map",
     "raw/c2-solsec-percase.json", "solsec"),
    ("X-Ray, pre-registered map", "raw/rc-score-xray.json", "xray", "map",
     "raw/xray-c2-raw.json", "radar"),
    ("X-Ray, corrected map", "raw/rc-score-xray-corrected.json", "xray", "corrected_map",
     "raw/xray-c2-raw.json", "radar"),
]


def corpus2_coverage(findings_path):
    """{case: True} for cases whose corpus-2 run log records BOTH variants as ok."""
    log = findings_path + ".log"
    if not os.path.exists(log):
        return None
    ok = {e.get("leaf") for e in json.load(open(log, encoding="utf-8"))
          if e.get("status") == "ok"}
    cases = {leaf.split("/")[0] for leaf in ok if leaf}
    return {c: ("%s/insecure" % c in ok and "%s/secure" % c in ok) for c in cases}


def corpus2_verdicts(mapping, kind, findings_path, corpus="corpus2",
                     manifest="corpus2/manifest.json"):
    cases = json.load(open(manifest, encoding="utf-8"))["cases"]
    findings = score2.load_findings(kind, findings_path)
    cover = corpus2_coverage(findings_path)
    out = {}
    for c in cases:
        if not c.get("valid", True):
            continue
        d = os.path.join(corpus, c["name"])
        if not os.path.isdir(d):
            out[c["name"]] = "not-built"
            continue
        if cover is not None and not cover.get(c["name"]):
            out[c["name"]] = "unavailable"
            continue
        out[c["name"]] = score2.score_case(d, c["class"], mapping, findings)[0]
    return out


def compare(label, rc_score_path, mapping_name, map_key, c2_findings, kind,
            mappings_dir="mappings", corpus="corpus2", manifest="corpus2/manifest.json"):
    rc = json.load(open(rc_score_path, encoding="utf-8"))
    real = {r["case"]: r["verdict"] for r in rc["cases"]}
    mapping = json.load(open(os.path.join(mappings_dir, mapping_name + ".json"),
                             encoding="utf-8"))[map_key]
    c2 = corpus2_verdicts(mapping, kind, c2_findings, corpus, manifest)

    rows, differ = [], 0
    for case in sorted(set(real) | set(c2)):
        a, b = c2.get(case, "absent"), real.get(case, "absent")
        # A case the tool could not run on either side is not a disagreement about packaging,
        # and it is not an agreement either: two unavailables are two missing observations.
        # Checked before equality, because `unavailable == unavailable` reads as "identical"
        # and would quietly inflate the number this whole page rests on.
        blocked = ({"unavailable", "not-built", "absent", "unknown"} & {a, b}) != set()
        if blocked:
            rows.append((case, a, b, "no comparison"))
            continue
        if a != b:
            differ += 1
        rows.append((case, a, b, "same" if a == b else "DIFFERS"))
    return rows, differ


def report(pairs=PAIRS, **kw):
    total_diff, total_cmp, total_blocked = 0, 0, 0
    for label, rc_path, mapping_name, map_key, c2_findings, kind in pairs:
        if not (os.path.exists(rc_path) and os.path.exists(c2_findings)):
            print("%-28s skipped: %s or %s is not in the repository"
                  % (label, rc_path, c2_findings))
            continue
        rows, differ = compare(label, rc_path, mapping_name, map_key, c2_findings, kind, **kw)
        blocked = sum(1 for r in rows if r[3] == "no comparison")
        same = sum(1 for r in rows if r[3] == "same")
        total_diff += differ
        total_cmp += same + differ
        total_blocked += blocked
        print("%-28s %2d cases compared, %2d identical, %2d differ, %2d not comparable"
              % (label, same + differ, same, differ, blocked))
        for case, a, b, verdict in rows:
            if verdict != "same":
                print("      %-38s corpus 2: %-12s real crate: %s" % (case, a, b))
    print()
    print("%d verdicts compared across packagings, %d differ, %d could not be compared"
          % (total_cmp, total_diff, total_blocked))
    return total_cmp, total_diff, total_blocked


def demo():
    """The comparison must be able to SEE a difference, or its zero means nothing."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        rc = os.path.join(d, "rc.json")
        # `a` agrees with what corpus 2 will produce; `b` deliberately does not, so a
        # comparison that can only ever print "same" fails here instead of in public.
        json.dump({"cases": [{"case": "a", "verdict": "detected"},
                             {"case": "b", "verdict": "detected"}]}, open(rc, "w"))
        manifest = os.path.join(d, "m.json")
        json.dump({"cases": [{"name": "a", "class": "owner-checks"},
                             {"name": "b", "class": "owner-checks"}]}, open(manifest, "w"))
        corpus = os.path.join(d, "corpus")
        for case, vuln in (("a", True), ("b", True)):
            for variant, text in (("insecure", "x\nBUG\ny\n"), ("secure", "x\nFIXED\ny\n")):
                sub = os.path.join(corpus, case, variant, "src")
                os.makedirs(sub)
                open(os.path.join(sub, "lib.rs"), "w").write(text)
        findings = os.path.join(d, "f.json")
        # A path relative to the corpus root, which is the shape every committed radar and
        # X-Ray findings file uses. An absolute Windows path would be split on its drive
        # letter by score2's radar parser and the finding would vanish - true of the parser,
        # not of any published file, since every one of them was written on Linux.
        json.dump([{"name": "RULE-X",
                    "locations": ["a/insecure/src/lib.rs:2:0"]}],
                  open(findings, "w"))
        maps = os.path.join(d, "mappings")
        os.makedirs(maps)
        json.dump({"map": {"owner-checks": ["RULE-X"]}},
                  open(os.path.join(maps, "t.json"), "w"))

        rows, differ = compare("t", rc, "t", "map", findings, "radar",
                               mappings_dir=maps, corpus=corpus, manifest=manifest)
        got = {r[0]: (r[1], r[2], r[3]) for r in rows}
        assert got["a"][2] == "same", got["a"]
        assert got["b"][2] == "DIFFERS", got["b"]
        assert differ == 1, differ
    print("rc_compare: OK (it can see a difference)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if args.demo:
        demo()
        return 0
    report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
