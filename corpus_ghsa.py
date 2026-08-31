#!/usr/bin/env python3
"""Find corpus-2 candidates in GitHub Security Advisories and RustSec.

The previous acquisition tool searched the open web for postmortems and was useless: 23 queries,
one hit, and that one false. The design was wrong, not the effort - postmortems put the fix commit
in the page body, and a search snippet never contains it.

Advisory databases are the right source because they are *structured*: an advisory names the
affected package and links its fix, so a commit URL is a field rather than something to be mined
out of prose.

This tool **proposes** candidates. It never adds a case to the corpus. A candidate becomes a case
only after a human reads the fix commit and confirms it repairs the vulnerability rather than, say,
disabling the program - which is exactly how `cashio-account-data` got in and had to be thrown out.

    python corpus_ghsa.py                  # discover, print candidates
    python corpus_ghsa.py --json out.json  # machine-readable
    python corpus_ghsa.py --demo           # self-check the filters
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request

API = "https://api.github.com/advisories"

# Package-name markers. Matched against the ADVISORY'S OWN package fields, not the whole blob:
# matching raw JSON made `gix-packetline` a Solana hit because "spl-" appears inside unrelated text.
PKG_MARKERS = ("solana", "anchor-lang", "anchor-spl", "spl-", "metaplex", "mpl-",
               "sealevel", "pyth", "serum", "squads", "wormhole", "jito", "raydium")

# Summary/description markers, for advisories whose crate name gives nothing away.
TEXT_MARKERS = (r"\bsolana\b", r"\banchor\s+program\b", r"\bspl\s+token\b",
                r"\bprogram\s+derived\s+address\b", r"\bpda\b", r"\bcpi\b")

COMMIT_RE = re.compile(r"https://github\.com/([^/]+)/([^/]+)/commit/([0-9a-f]{7,40})")
PR_RE = re.compile(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)")


def get(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "scannertruth-corpus-acquisition"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode()), r.headers.get("Link", "")


def packages_of(adv):
    out = []
    for v in adv.get("vulnerabilities") or []:
        p = (v.get("package") or {}).get("name")
        if p:
            out.append(p)
    return out


def is_solana(adv):
    """Package-name match first, text match second, and say which fired.

    Kept deliberately generous: a false candidate costs one human read, a missed one costs a case
    that never enters the corpus and is never noticed.
    """
    pkgs = [p.lower() for p in packages_of(adv)]
    for p in pkgs:
        for m in PKG_MARKERS:
            if m in p:
                return f"package {p!r} matches {m!r}"
    text = " ".join([adv.get("summary") or "", adv.get("description") or ""]).lower()
    for m in TEXT_MARKERS:
        if re.search(m, text):
            return f"text matches /{m}/"
    return None


def fix_refs(adv):
    """Commit URLs are usable directly; PR URLs need one more hop a human can make."""
    blob = json.dumps(adv)
    commits = [{"repo": f"{m.group(1)}/{m.group(2)}", "sha": m.group(3)}
               for m in COMMIT_RE.finditer(blob)]
    prs = [{"repo": f"{m.group(1)}/{m.group(2)}", "pr": int(m.group(3))}
           for m in PR_RE.finditer(blob)]
    seen, uniq = set(), []
    for c in commits:
        k = (c["repo"], c["sha"])
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    return uniq, prs


def discover(max_pages=12):
    """Walk the Rust ecosystem advisories. Unauthenticated, so it is rate limited and slow."""
    out, url = [], f"{API}?ecosystem=rust&per_page=100"
    pages = 0
    while url and pages < max_pages:
        try:
            data, link = get(url)
        except urllib.error.HTTPError as e:
            # Rate limiting is an OUTAGE, not an absence. Returning what we have while
            # pretending it is the whole answer is how a radar reports "no opportunities".
            print(f"STOPPED after {pages} page(s): HTTP {e.code}. "
                  f"Treat this as incomplete, not as 'no more candidates'.", file=sys.stderr)
            return out, False
        if not isinstance(data, list):
            return out, False
        out.extend(data)
        pages += 1
        nxt = re.search(r'<([^>]+)>;\s*rel="next"', link or "")
        url = nxt.group(1) if nxt else None
    return out, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--pages", type=int, default=12)
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        return demo()

    advisories, complete = discover(args.pages)
    print(f"scanned {len(advisories)} rust advisories "
          f"({'complete' if complete else 'INCOMPLETE - rate limited'})\n")

    candidates = []
    for adv in advisories:
        why = is_solana(adv)
        if not why:
            continue
        commits, prs = fix_refs(adv)
        candidates.append({
            "ghsa": adv.get("ghsa_id"),
            "summary": (adv.get("summary") or "")[:110],
            "packages": packages_of(adv),
            "severity": adv.get("severity"),
            "published": (adv.get("published_at") or "")[:10],
            "matched_because": why,
            "fix_commits": commits,
            "fix_prs": prs,
            "usable": bool(commits),
        })

    usable = [c for c in candidates if c["usable"]]
    print(f"solana-related: {len(candidates)}   with a direct fix commit: {len(usable)}\n")
    for c in candidates:
        mark = "USABLE  " if c["usable"] else "needs-hop"
        print(f"{mark} {c['ghsa']}  {c['published']}  {c['summary']}")
        print(f"          {c['matched_because']}; packages={c['packages']}")
        for fc in c["fix_commits"]:
            print(f"          fix: https://github.com/{fc['repo']}/commit/{fc['sha']}")
        for pr in c["fix_prs"][:2]:
            print(f"          pr:  https://github.com/{pr['repo']}/pull/{pr['pr']}")

    print("\nNOTHING HAS BEEN ADDED TO THE CORPUS. Each candidate needs a human to read the fix "
          "commit and confirm it repairs the bug rather than disabling the code path. One case "
          "already had to be removed for exactly that.")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"complete": complete, "candidates": candidates}, fh, indent=1)
        print(f"written: {args.json}")
    return 0


def demo():
    """The filters are the whole tool, so they are what gets checked."""
    fake = {"vulnerabilities": [{"package": {"name": "gix-packetline"}}],
            "summary": "reachable panic on empty side-band packet",
            "description": "unrelated to blockchains"}
    assert is_solana(fake) is None, "raw-text matching must not resurrect false positives"

    real = {"vulnerabilities": [{"package": {"name": "anchor-lang"}}],
            "summary": "InterfaceAccount substitution", "description": ""}
    assert is_solana(real), "an obvious Solana crate must match"

    texty = {"vulnerabilities": [{"package": {"name": "obscure-crate"}}],
             "summary": "missing owner check in a Solana program", "description": ""}
    assert is_solana(texty), "text markers must catch crates with neutral names"

    adv = {"references": ["https://github.com/a/b/commit/deadbeef1234567",
                          "https://github.com/a/b/commit/deadbeef1234567",
                          "https://github.com/a/b/pull/42"]}
    commits, prs = fix_refs(adv)
    assert len(commits) == 1, f"duplicate commit refs must collapse: {commits}"
    assert prs and prs[0]["pr"] == 42
    print("corpus_ghsa: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
