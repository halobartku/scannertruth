#!/usr/bin/env python3
"""Czy RustSec ma solanowe doradztwa, ktorych GHSA-po-ekosystemie nie widzi.

Dokumentacja `corpus_ghsa.py` mowi, ze czyta "GitHub Security Advisories and RustSec",
a kod pyta wylacznie `api.github.com/advisories?ecosystem=rust`. GHSA importuje RustSec,
ale czy w calosci i czy z tym samym oznaczeniem ekosystemu - to jest pytanie, nie zalozenie.
"""
import json, re, sys, urllib.request

IDX = "https://api.github.com/repos/rustsec/advisory-db/git/trees/main?recursive=1"
MARK = re.compile(r"solana|anchor|spl[-_]|mpl[-_]|metaplex|pyth|serum|raydium|jupiter|wormhole", re.I)


def test():
    ok = 0
    assert MARK.search("solana-program"); ok += 1
    assert MARK.search("mpl-bubblegum"); ok += 1
    assert MARK.search("anchor-lang"); ok += 1
    assert not MARK.search("tokio"); ok += 1
    assert not MARK.search("serde"); ok += 1
    # 'spl' bez separatora nie moze lapac przypadkowych slow
    assert not MARK.search("splendid"); ok += 1
    print("test: %d sprawdzen OK" % ok)
    return 0


def main():
    r = urllib.request.Request(IDX, headers={"User-Agent": "forge-corpus"})
    d = json.load(urllib.request.urlopen(r, timeout=60))
    if d.get("truncated"):
        print("UWAGA: drzewo obciete, to jest skan NIEPELNY")
    # RustSec trzyma doradztwa jako .md pod crates/, nie .toml. Sprawdzone 2026-09-11:
    # pierwsza wersja szukala .toml i znalazla 1 plik z 1 250, co wygladalo jak pusta baza.
    sciezki = [x["path"] for x in d.get("tree", [])
               if x["path"].endswith(".md") and x["path"].startswith("crates/")]
    print("plikow doradztw w RustSec: %d" % len(sciezki))
    traf = [p for p in sciezki if MARK.search(p)]
    print("pasujacych do markerow solanowych po NAZWIE CRATE'A: %d" % len(traf))
    for p in sorted(traf):
        print("   ", p)


if __name__ == "__main__":
    sys.exit(test() if "--test" in sys.argv[1:] else main())
