# --------------------------------------------------------- corpus/case sanity
def test_no_case_is_both_valid_and_unexplained_when_excluded():
    import json, io as _io
    man = json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    for c in man:
        if c.get("valid", True) is False:
            assert len(c.get("invalid_reason", "")) > 40, \
                f"{c['name']} excluded with a reason too short to audit"


def test_case_names_are_unique():
    import json, io as _io
    man = json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    names = [c["name"] for c in man]
    assert len(names) == len(set(names)), "duplicate case names would double-count a denominator"


def test_pinned_files_look_like_source_paths():
    import json, io as _io
    man = json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    for c in man:
        for f in c.get("files", []):
            assert f.endswith(".rs"), f"{c['name']} pins a non-Rust file: {f}"
            assert not f.startswith("/"), f"{c['name']} pins an absolute path: {f}"


def test_fix_commits_look_like_shas():
    import json, io as _io, re
    man = json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    for c in man:
        fix = c["fix"]
        if fix.startswith("PENDING"):
            continue
        assert re.fullmatch(r"[0-9a-f]{7,40}", fix), f"{c['name']} has a malformed fix sha: {fix}"


# ------------------------------------------ corpus content is pinned, 2026-09-01, row 9

def test_every_corpus_file_matches_the_hash_recorded_in_the_manifest():
    """The benchmark's whole pitch is that you can check it rather than trust it, and until
    2026-09-01 the one thing nobody could check was the ground truth. The manifest carried
    commit SHAs; `test_fix_commits_look_like_shas` checked they looked like SHAs. Nothing
    tied `corpus2/<case>/<variant>/src/*.rs` to any blob. A one-character edit to any corpus
    file passed every check in this repository and changed every verdict.

    `tools/corpus_hashes.py` records a sha256 and git's own blob id per file. This recomputes
    them. It is deliberately the cheapest possible check: it needs no network and no clone."""
    import sys
    sys.path.insert(0, "tools")
    import corpus_hashes
    problems = corpus_hashes.report()
    assert not problems, (
        "the corpus no longer matches the hashes recorded in corpus2/manifest.json:\n  "
        + "\n  ".join(problems)
        + "\nIf the corpus was changed on purpose, rerun `python tools/corpus_hashes.py --write` "
          "and say in the commit message what moved and why.")


def test_every_built_case_records_the_upstream_blob_it_came_from():
    """A sha256 proves the file has not changed since we hashed it. It does not prove the file
    is the upstream blob. The git blob id does, in one command against a clone, so every
    vulnerable variant must name the parent commit and every fixed variant the fix commit.

    Checked offline. `raw/corpus2-blob-verification-2026-09-01.json` holds the result of
    actually asking GitHub, which is the part that needs the network."""
    import io as _io, json as _json, os
    manifest = _json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))
    built = {e["name"]: e for e in _json.load(_io.open("corpus2/built.json", encoding="utf-8"))}
    missing = []
    for case in manifest["cases"]:
        hashes = case.get("file_hashes")
        if not hashes:
            continue
        b = built.get(case["name"], {})
        for rel, meta in sorted(hashes.items()):
            if not rel.endswith(".rs"):
                continue
            up = meta.get("upstream")
            if not up:
                missing.append(f"{case['name']}/{rel}: no upstream blob recorded")
                continue
            want = b.get("parent") if rel.startswith("insecure/") else b.get("fix")
            if up.get("commit") != want:
                missing.append(
                    f"{case['name']}/{rel}: recorded upstream commit {up.get('commit')} but "
                    f"built.json says {want}")
    assert not missing, (
        "these corpus files are not tied to an upstream blob, so their ground truth cannot be "
        "checked by anybody outside this repository:\n  " + "\n  ".join(missing))
