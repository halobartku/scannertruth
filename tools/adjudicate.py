#!/usr/bin/env python3
"""Apply the existing class rules in mappings/model-classes.json to one model run.

    python tools/adjudicate.py raw/model-<name>/runs.jsonl

Prints, for every verdict-right case, the verdict the existing rules give, or UNMAPPED with the
phrases that have no rule. It never writes a verdict: a phrase without a rule is a human judgement
under the owner's rule of 2026-09-02, and the tool's job is to make that list short and exact.
Exit code 1 when anything is unmapped, so a script cannot mistake "not judged" for "judged no".
"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _named(row):
    try:
        return json.loads(row["raw"]).get("class") or row.get("note") or ""
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
        return row.get("note") or ""


def verdict_right_named(rows):
    """Cases fired on the vulnerable variant at least once and never on the fixed one, with at least
    one valid answer on the fixed one (a fixed variant with only limit messages is not "silent"),
    and the distinct class strings named on the vulnerable firing runs, in first-seen order."""
    by = collections.defaultdict(list)
    for r in rows:
        by[r["case"]].append(r)
    out = {}
    for case, rs in by.items():
        ins = [r for r in rs if r["variant"] == "insecure" and r.get("vulnerable") is True]
        sec = [r for r in rs if r["variant"] == "secure" and isinstance(r.get("vulnerable"), bool)]
        if not ins or not sec or any(r.get("vulnerable") is True for r in sec):
            continue
        named = []
        for r in ins:
            n = _named(r)
            if n and n not in named:
                named.append(n)
        out[case] = {"real_class": rs[0]["class"], "named": named}
    return out


def apply_rules(real_class, named, rules):
    """counts if any phrase counts; else None if any phrase has no rule; else disputed if any is
    disputed; else no. Matching is case-insensitive on the whole phrase, nothing fuzzier."""
    table = {(r["real_class"], p.lower()): (r["verdict"], r["reason"]) for r in rules for p in r["phrases"]}
    hits = [(n, table.get((real_class, n.lower()))) for n in named]
    for n, h in hits:
        if h and h[0] == "counts":
            return "counts", f"'{n}': {h[1]}"
    if not hits or any(h is None for _, h in hits):
        return None
    for n, h in hits:
        if h[0] == "disputed":
            return "disputed", f"'{n}': {h[1]}"
    n, h = hits[0]
    return "no", f"'{n}': {h[1]}"


def main(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    rules = json.loads((ROOT / "mappings" / "model-classes.json").read_text(encoding="utf-8"))["rules"]
    table = {(r["real_class"], p.lower()) for r in rules for p in r["phrases"]}
    unmapped = 0
    for case, c in sorted(verdict_right_named(rows).items()):
        got = apply_rules(c["real_class"], c["named"], rules)
        if got is None:
            unmapped += 1
            missing = [n for n in c["named"] if (c["real_class"], n.lower()) not in table]
            print(f"UNMAPPED  {case} [{c['real_class']}]: {missing}")
        else:
            print(f"{got[0]:9} {case} [{c['real_class']}]: {got[1]}")
    print(f"\n{unmapped} case(s) need a human judgement")
    return 1 if unmapped else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
