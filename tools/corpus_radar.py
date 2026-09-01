#!/usr/bin/env python3
"""Corpus radar: find candidate test cases, never add them.

The benchmark is only worth as much as its answer key. An automated harvester that pulls
"vulnerabilities" off the internet and adds them to a corpus would produce mislabelled cases within
a week, and every number computed afterwards would be quietly wrong. So this tool proposes; a human
disposes.

A candidate is only worth looking at if all four of these are true, and the radar checks all four
before it will list anything:

  1. a public repository
  2. a commit or PR that FIXED the bug          <- this is the answer key
  3. the code as it stood before that commit    <- this is the vulnerable case
  4. a public description of what the bug was   <- so the label is not our opinion

Anything missing one of them is rejected with the reason recorded, because the rejections are as
useful as the finds: they tell you which sources are worth watching next time.

State lives in `.corpus_seen.json` so a scheduled run reports only what is new.

Usage:
    python tools/corpus_radar.py --out corpus-candidates.md   # needs the network
    python tools/corpus_radar.py --demo
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

SEEN = ".corpus_seen.json"
UA = {"User-Agent": "scannertruth-corpus-radar"}

# Sources that publish fixes with public descriptions attached. Deliberately short: a source that
# does not link a fix commit produces candidates that always fail requirement 2.
QUERIES = [
    "solana anchor program vulnerability postmortem fix commit",
    "solana program exploit disclosure github fix pull request",
    "anchor smart contract audit report github findings fixed commit",
    "solana security advisory rust crate anchor fixed in",
    "immunefi solana bug disclosure public fix",
]

GITHUB_COMMIT = re.compile(
    r"https?://github\.com/([\w.-]+)/([\w.-]+)/(?:commit|pull)/([0-9a-f]{7,40}|\d+)")


def searx(query, endpoint="http://127.0.0.1:8888/search"):
    """Our own metasearch. Returns [] on failure, but callers must treat that as an OUTAGE."""
    url = f"{endpoint}?q={urllib.parse.quote(query)}&format=json"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.load(r)
    except Exception:
        return None, "searx unreachable"
    dead = data.get("unresponsive_engines") or []
    results = data.get("results") or []
    # An empty result set with every engine suspended is a failure, not an absence. This project has
    # already published a wrong conclusion built on exactly that confusion.
    if not results and dead:
        return None, f"all engines suspended: {[d[0] for d in dead]}"
    return results, None


def gh(path):
    try:
        req = urllib.request.Request(f"https://api.github.com{path}", headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except Exception:
        return None


def check_candidate(owner, repo, ref):
    """Verify the four requirements as far as a machine can. Returns (ok, reason, detail)."""
    meta = gh(f"/repos/{owner}/{repo}")
    if not meta:
        return False, "repo not reachable", {}
    if meta.get("private"):
        return False, "repo is private", {}

    # requirement 2 and 3: the fix commit must exist and must touch Rust
    if ref.isdigit():
        pr = gh(f"/repos/{owner}/{repo}/pulls/{ref}")
        if not pr or not pr.get("merged_at"):
            return False, "PR not merged, so there is no fixed state", {}
        files = gh(f"/repos/{owner}/{repo}/pulls/{ref}/files") or []
        parent = pr.get("base", {}).get("sha")
    else:
        commit = gh(f"/repos/{owner}/{repo}/commits/{ref}")
        if not commit:
            return False, "commit not reachable", {}
        files = commit.get("files") or []
        parents = commit.get("parents") or []
        parent = parents[0]["sha"] if parents else None

    rust = [f for f in files if (f.get("filename") or "").endswith(".rs")]
    if not rust:
        return False, "fix touches no .rs file", {}
    if not parent:
        return False, "no parent commit, cannot reconstruct the vulnerable state", {}

    return True, "", {
        "repo": f"{owner}/{repo}",
        "stars": meta.get("stargazers_count"),
        "fix_ref": ref,
        "vulnerable_parent": parent,
        "rust_files_changed": [f["filename"] for f in rust][:10],
        "changed_lines": sum((f.get("changes") or 0) for f in rust),
    }


def load_seen(path=SEEN):
    try:
        with open(path, encoding="utf-8") as fh:
            return set(json.load(fh))
    except Exception:
        return set()


def save_seen(seen, path=SEEN):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sorted(seen), fh, indent=1)


def scan(queries=None, limit_per_query=12):
    queries = queries or QUERIES
    seen = load_seen()
    found, rejected, outages = [], [], []

    for q in queries:
        results, err = searx(q)
        if results is None:
            outages.append((q, err))
            continue
        for item in results[:limit_per_query]:
            for text in (item.get("url", ""), item.get("content", "")):
                for m in GITHUB_COMMIT.finditer(text or ""):
                    owner, repo, ref = m.group(1), m.group(2), m.group(3)
                    key = f"{owner}/{repo}@{ref}"
                    if key in seen:
                        continue
                    seen.add(key)
                    ok, reason, detail = check_candidate(owner, repo, ref)
                    detail["source_url"] = item.get("url", "")
                    detail["source_title"] = (item.get("title") or "")[:120]
                    (found if ok else rejected).append(
                        {**detail, "key": key, **({} if ok else {"rejected_because": reason})})
    save_seen(seen)
    return found, rejected, outages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="corpus-candidates.md")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        demo()
        return 0

    found, rejected, outages = scan()

    if outages and not found and not rejected:
        print("OUTAGE: search returned nothing usable. This is NOT 'no candidates found'.")
        for q, err in outages:
            print(f"  {q[:50]}: {err}")
        return 2

    lines = ["# Corpus candidates", "",
             "Proposed, never added. Every entry still needs a human to confirm the label.", ""]
    if found:
        lines += ["| repo | stars | fix | vulnerable parent | .rs changed | source |",
                  "|---|---|---|---|---|---|"]
        for c in found:
            lines.append(f"| {c['repo']} | {c.get('stars')} | `{c['fix_ref']}` | "
                         f"`{c['vulnerable_parent'][:8]}` | {len(c['rust_files_changed'])} | "
                         f"{c.get('source_url','')} |")
    else:
        lines.append("_No new candidates passed all four requirements this run._")
    lines += ["", f"## Rejected ({len(rejected)})", ""]
    for r in rejected:
        lines.append(f"- `{r['key']}` — {r['rejected_because']}")
    if outages:
        lines += ["", "## Search outages, treat as missing coverage not as absence", ""]
        lines += [f"- `{q[:60]}`: {e}" for q, e in outages]

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"candidates: {len(found)}  rejected: {len(rejected)}  outages: {len(outages)}")
    print(f"written: {args.out}")
    return 0


def demo():
    """Self-check the parts that decide whether a bad case can slip into the corpus."""
    m = GITHUB_COMMIT.search("see https://github.com/foo/bar/commit/a1b2c3d4e5f6 for the fix")
    assert m and m.group(1) == "foo" and m.group(3) == "a1b2c3d4e5f6", m

    m2 = GITHUB_COMMIT.search("fixed in https://github.com/o/r/pull/42 thanks")
    assert m2 and m2.group(3) == "42", m2

    assert GITHUB_COMMIT.search("https://gitlab.com/o/r/commit/abc1234") is None, \
        "only github refs are checkable by this radar"

    # The failure that matters: an empty search with dead engines must not read as "nothing exists".
    import unittest.mock as mock
    with mock.patch.object(sys.modules[__name__], "searx",
                           lambda q, **k: (None, "all engines suspended: ['brave']")):
        found, rejected, outages = scan(queries=["anything"])
    assert found == [] and rejected == [] and len(outages) == 1, (found, rejected, outages)
    assert "suspended" in outages[0][1]

    print("corpus_radar: OK")


if __name__ == "__main__":
    sys.exit(main())
