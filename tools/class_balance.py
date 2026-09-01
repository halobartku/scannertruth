#!/usr/bin/env python3
"""Recompute the corpus 2 class and repository balance from the manifest.

The corpus's largest stated weakness is that it is small and lopsided: for most of its
life more than half of it was "somebody forgot to compare two pubkeys", and five
repositories supplied every case. Those two numbers are the ones a reader should use to
discount a score, so they must be recomputed from the manifest rather than typed into a
document and left to rot. Never type a count a machine can compute.

    python tools/class_balance.py            # rewrite docs/CLASS-BALANCE.md
    python tools/class_balance.py --check    # exit 1 if the document is stale
"""
import argparse
import collections
import io
import json
import os
import sys

MANIFEST = "corpus2/manifest.json"
OUT = "docs/CLASS-BALANCE.md"


def load():
    with io.open(MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)["cases"]


def partition(cases):
    valid = [c for c in cases if c.get("valid", True)]
    built = [c for c in valid if os.path.isdir(os.path.join("corpus2", c["name"]))]
    measured = [c for c in built if c.get("measured", True)]
    return valid, built, measured


def table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def render():
    cases = load()
    valid, built, measured = partition(cases)
    invalid = [c for c in cases if not c.get("valid", True)]

    by_class = collections.Counter(c["class"] for c in valid)
    by_repo = collections.Counter(c["repo"] for c in valid)
    unmeasured = [c["name"] for c in built if not c.get("measured", True)]
    unbuilt = [c["name"] for c in valid if c not in built]

    biggest_class = by_class.most_common(1)[0]
    biggest_repo = by_repo.most_common(1)[0]
    top3 = sum(n for _, n in by_repo.most_common(3))

    lines = []
    lines.append("# Corpus 2 class and repository balance")
    lines.append("")
    lines.append("**This file is generated. Do not edit it.** Run "
                 "`python tools/class_balance.py`, which reads `corpus2/manifest.json` and the "
                 "`corpus2/` directory. `test_all.py` fails if the two disagree, because a "
                 "concentration figure that nobody recomputes is how a corpus quietly stops "
                 "meaning what its front page says.")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(table([
        ["cases listed", len(cases)],
        ["valid", len(valid)],
        ["invalid, kept in the manifest so the error stays visible", len(invalid)],
        ["built", len(built)],
        ["measured by at least one scanner", len(measured)],
        ["built but not yet measured", len(unmeasured)],
        ["valid but not built", len(unbuilt)],
        ["distinct classes among the valid cases", len(by_class)],
        ["distinct repositories among the valid cases", len(by_repo)],
    ], ["", "n"]))
    lines.append("")
    if unmeasured:
        lines.append("Not yet measured, and therefore not in the denominator of any published "
                     "score: " + ", ".join(f"`{n}`" for n in sorted(unmeasured)) + ".")
        lines.append("")
    if unbuilt:
        lines.append("Valid but not built, reported as `not-built` rather than skipped: "
                     + ", ".join(f"`{n}`" for n in sorted(unbuilt)) + ".")
        lines.append("")
    lines.append("## By class")
    lines.append("")
    lines.append(table(
        [[cls, n, ", ".join(f"`{c['name']}`" for c in valid if c["class"] == cls)]
         for cls, n in sorted(by_class.items(), key=lambda kv: (-kv[1], kv[0]))],
        ["class", "n", "cases"]))
    lines.append("")
    lines.append("## By repository")
    lines.append("")
    lines.append(table(
        [[repo, n] for repo, n in sorted(by_repo.items(), key=lambda kv: (-kv[1], kv[0]))],
        ["repository", "n"]))
    lines.append("")
    lines.append("## What this says about a score")
    lines.append("")
    lines.append(f"The largest class is `{biggest_class[0]}` with {biggest_class[1]} of "
                 f"{len(valid)} valid cases. The largest repository is `{biggest_repo[0]}` with "
                 f"{biggest_repo[1]}, and the three largest supply {top3} of {len(valid)}. A "
                 "scanner implementing exactly the detection pattern behind the largest class "
                 "scores better here than its general ability warrants, and a scanner tuned "
                 "against the largest repository does too. Both concentrations are still real "
                 "after every addition; they are smaller, not gone.")
    lines.append("")
    lines.append("Both figures sit on top of the selection bias that cannot be fixed by adding "
                 "cases at all: every case here comes from a public advisory, audit or "
                 "postmortem, and those are public precisely because nobody caught them in "
                 "time. The corpus is therefore systematically harder than the population of "
                 "real bugs and understates every scanner measured on it.")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the document on disk is stale, and write nothing")
    args = ap.parse_args()
    text = render()
    if args.check:
        if not os.path.exists(OUT):
            print(f"{OUT} does not exist")
            return 1
        if io.open(OUT, encoding="utf-8").read() != text:
            print(f"{OUT} is stale; run python tools/class_balance.py")
            return 1
        print(f"{OUT} is up to date")
        return 0
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
