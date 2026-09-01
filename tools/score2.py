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


def resolve_in_case(path, case_dir):
    """Does this finding belong to THIS case, and does the file it names still exist?

    Returns `(in_case, on_disk_path_or_None)`.

    Two defects live here and both were open on 2026-09-01.

    **Error 31.** Until today a finding was matched to a case by BASENAME alone. The case
    directory located the pair and computed the fix site, and was then never used to decide
    whether a finding belonged to the case at all. With nine cases and nearly distinct filenames
    that was nearly harmless. After the additions of 2026-09-01, `processor.rs` appears in four
    cases, `state.rs` in two and `lib.rs` in three, and a finding in one case decided a verdict
    in another.

    **Row 5 of the audit.** A findings file can outlive the corpus it was produced against, and
    one did. The path is resolved relative to the case directory rather than the process's
    working directory, so a relative finding path is not mistaken for a missing file, which is
    the way an existence check turns a real detection into a silent nothing.
    """
    p = path.replace("\\", "/")
    case = os.path.basename(os.path.normpath(case_dir))
    parts = [x for x in p.split("/") if x not in ("", ".")]
    if case not in parts:
        return False, None
    i = len(parts) - 1 - parts[::-1].index(case)
    parent = os.path.dirname(os.path.normpath(case_dir)) or "."
    candidate = os.path.join(parent, *parts[i:])
    return True, (candidate if os.path.exists(candidate) else None)


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
    # A finding recorded against a file that is not in the corpus is not evidence about the file
    # that replaced it. `raw/c2-radar-complete.json` was produced before the corpus was rebuilt to
    # pin one file per case, and 161 of its 238 findings name paths that no longer resolve. Those
    # are counted here and never scored, so a case whose only mapped evidence is stale comes back
    # `unknown` rather than as a miss the tool never earned. Row 5 of the 2026-09-01 audit.
    stale = 0

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
            in_case, on_disk = resolve_in_case(p, case_dir)
            if not in_case:
                continue
            mapped = [(r, ln) for r, ln in items if (r or "").lower() in rules]
            if not mapped:
                continue
            if on_disk is None:
                stale += len(mapped)
                continue
            on_fixed = "/secure/" in p
            for rule_id, line in mapped:
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
    if stale:
        return "unknown", {"reason": f"{stale} mapped findings for this case name files that are "
                                     "not in the corpus, so there is no evidence either way"}
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

    # POSITIVE CONTROL, end to end through score_case itself.
    #
    # Until 2026-08-31 this scorer had never once returned "detected" for
    # anything, and nobody had checked that it could. Every published zero
    # rested on an instrument whose only observed output was zero. It does
    # work - confirmed against the real X-Ray finding on
    # squads-account-matching - but that was the luck of one tool happening to
    # fire, not method. A synthetic case now drives the scoring path on every
    # run, so a corpus of zeros can never again quietly mean a scorer that
    # cannot say yes.
    #
    # It stops short of `load_findings`: this control hands `score_case` a dict
    # directly, so a parser that returns nothing still passes here. That gap was
    # real and was found from outside on 2026-09-01 - the sol-audit branch of
    # `load_findings` was disabled and every check in the repository stayed
    # green. `test_all.py` now runs the same control from a findings file in
    # each supported envelope, which is where a scanner's output actually
    # starts.
    with tempfile.TemporaryDirectory() as d:
        case = os.path.join(d, "synthetic-case")
        vulnerable = "\n".join(["a", "b", "vulnerable_line", "d"]) + "\n"
        fixed = "\n".join(["a", "b", "guard()", "vulnerable_line", "d"]) + "\n"
        for variant, text in (("insecure", vulnerable), ("secure", fixed)):
            sub = os.path.join(case, variant, "src")
            os.makedirs(sub)
            open(os.path.join(sub, "lib.rs"), "w").write(text)
        mapping = {"1-account-data-matching": ["RULE-X"]}
        ins_path = os.path.join(case, "insecure", "src", "lib.rs")
        sec_path = os.path.join(case, "secure", "src", "lib.rs")

        # fires on the vulnerable variant at the fix site, silent on the fix
        v, _ = score_case(case, "account-data-matching", mapping,
                          {ins_path: [("RULE-X", 3)]})
        assert v == "detected", f"positive control returned {v!r}, not 'detected'"

        # the same rule firing on the fix too is not a detection
        v, _ = score_case(case, "account-data-matching", mapping,
                          {ins_path: [("RULE-X", 3)], sec_path: [("RULE-X", 3)]})
        assert v != "detected", f"firing on the fix must not score detected: {v!r}"

        # firing far from the fix is neither a detection nor a clean miss
        v, _ = score_case(case, "account-data-matching", mapping,
                          {ins_path: [("RULE-X", 400)]})
        assert v == "unlocated", f"off-site finding returned {v!r}"

    print("score2: OK (including the positive control)")


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
    # A case whose "secure" variant does not actually fix the bug is not a pair, and scoring it
    # produces a verdict about something else. Enforced here rather than left as a note in the
    # manifest, because a note does not stop the next run from counting it.
    excluded = [c["name"] for c in cases if not c.get("valid", True)]
    cases = [c for c in cases if c.get("valid", True)]
    for name in excluded:
        print(f"EXCLUDED {name}: manifest marks it not a valid insecure/secure pair")
    mapping = json.load(open(f"mappings/{args.scanner}.json", encoding="utf-8"))["map"]
    findings = load_findings(args.kind, args.findings)

    tally = {}
    print(f"{'case':30} {'class':28} {'verdict':10} note")
    for c in cases:
        d = os.path.join(args.corpus, c["name"])
        if not os.path.isdir(d):
            # A case listed as valid but absent from disk was being skipped in silence, so the
            # denominator shrank without anyone saying so. Say so.
            print(f"{c['name']:30} {c['class']:28} {'not-built':10} "
                  f"in the manifest but not on disk; excluded from the denominator")
            tally["not-built"] = tally.get("not-built", 0) + 1
            continue
        verdict, info = score_case(d, c["class"], mapping, findings)
        tally[verdict] = tally.get(verdict, 0) + 1
        print(f"{c['name']:30} {c['class']:28} {verdict:10} {info.get('reason','')}")
    print()
    print(f"{args.scanner}: " + "  ".join(f"{k}={v}" for k, v in sorted(tally.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
