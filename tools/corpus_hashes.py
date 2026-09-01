#!/usr/bin/env python3
"""Pin every corpus-2 file to a content hash, and to the upstream blob it was extracted from.

The central claim of this benchmark is that the answer key is the project's own fix. Until
2026-09-01 nothing in this repository connected `corpus2/<case>/<variant>/src/*.rs` to the commit
it is supposed to be a copy of. The manifest carried commit SHAs and the test suite checked that
they *looked* like SHAs. A one-character edit to any corpus file passed every check and changed
every verdict, and a stranger could not check the ground truth without cloning nine repositories
by hand and diffing by eye.

This writes two hashes per file into `corpus2/manifest.json`:

  sha256       the content hash, so tampering is detectable offline with nothing but this file
  git_blob     git's own blob id, sha1("blob <len>\\0" + content), so provenance is checkable
               with one command against the upstream repository and no diffing:

                   git -C <clone of the upstream repo> cat-file blob <git_blob>

               and, the other way round, that the blob is the one the fix commit produced:

                   git -C <clone> rev-parse <fix>:<upstream path>          -> secure variant
                   git -C <clone> rev-parse <fix>^:<upstream path>         -> insecure variant

The second form is the one that matters, because it ties the file to a commit rather than merely
proving the file has not changed since we hashed it. It is recorded per file as `upstream`, from
`corpus2/built.json`, which already knows each case's fix and parent SHA.

Nothing here can be verified offline against upstream: that needs the clones. What it does give is
a fixed target. A stranger with the nine clones can now check the whole corpus in a loop, and
anybody without them can still detect a local edit.

    python tools/corpus_hashes.py            # report drift, change nothing
    python tools/corpus_hashes.py --write    # write the hashes into the manifest
    python tools/corpus_hashes.py --demo
"""
import argparse
import hashlib
import json
import os
import sys

CORPUS = "corpus2"
MANIFEST = os.path.join(CORPUS, "manifest.json")
BUILT = os.path.join(CORPUS, "built.json")
VARIANTS = ("insecure", "secure")


def git_blob_id(data):
    """git's own object id for a blob: sha1 of the header plus the bytes, no repository needed."""
    header = ("blob %d\0" % len(data)).encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def hash_file(path):
    with open(path, "rb") as fh:
        data = fh.read()
    return {"sha256": hashlib.sha256(data).hexdigest(),
            "git_blob": git_blob_id(data),
            "bytes": len(data)}


def upstream_for(built_entry, variant, basename):
    """Which upstream commit and path this variant's file was extracted from.

    `insecure` is the fix commit's parent, `secure` is the fix commit. The upstream path is the
    one the manifest pins; a case pins exactly one file, so the basename identifies it.
    """
    if not built_entry:
        return None
    commit = built_entry.get("parent") if variant == "insecure" else built_entry.get("fix")
    paths = [p for p in built_entry.get("files") or [] if os.path.basename(p) == basename]
    if not commit or len(paths) != 1:
        return None
    return {"repo": built_entry.get("repo"), "commit": commit, "path": paths[0],
            "verify": "git -C <clone of %s> rev-parse %s:%s"
                      % (built_entry.get("repo"), commit, paths[0])}


def compute(corpus=CORPUS, built_path=BUILT):
    """{case name: {"<variant>/<relpath>": {...}}} for every built case on disk."""
    built = {}
    if os.path.exists(built_path):
        for e in json.load(open(built_path, encoding="utf-8")):
            built[e.get("name")] = e
    out = {}
    for case in sorted(os.listdir(corpus)):
        case_dir = os.path.join(corpus, case)
        if not os.path.isdir(case_dir):
            continue
        files = {}
        for variant in VARIANTS:
            vdir = os.path.join(case_dir, variant)
            if not os.path.isdir(vdir):
                continue
            for root, _dirs, names in os.walk(vdir):
                for name in sorted(names):
                    full = os.path.join(root, name)
                    rel = os.path.relpath(full, case_dir).replace("\\", "/")
                    entry = hash_file(full)
                    if name.endswith(".rs"):
                        up = upstream_for(built.get(case), variant, name)
                        if up:
                            entry["upstream"] = up
                        else:
                            entry["upstream_note"] = (
                                "not resolvable from built.json; this file's provenance is not "
                                "pinned to an upstream blob")
                    else:
                        entry["generated_by"] = (
                            "tools/build_corpus2.py, not an upstream file: the manifest is "
                            "synthesised around the extracted source")
                    files[rel] = entry
        if files:
            out[case] = files
    return out


def report(corpus=CORPUS, manifest_path=MANIFEST, built_path=BUILT):
    """Compare the manifest's recorded hashes against the files on disk. Returns a problem list."""
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    recorded = {c["name"]: c.get("file_hashes") for c in manifest["cases"]}
    now = compute(corpus, built_path)
    problems = []
    for case, files in sorted(now.items()):
        have = recorded.get(case)
        if not have:
            problems.append(f"{case}: no file_hashes in the manifest")
            continue
        for rel in sorted(set(have) | set(files)):
            if rel not in have:
                problems.append(f"{case}/{rel}: on disk but not recorded in the manifest")
            elif rel not in files:
                problems.append(f"{case}/{rel}: recorded in the manifest but not on disk")
            elif have[rel].get("sha256") != files[rel]["sha256"]:
                problems.append(
                    f"{case}/{rel}: CONTENT CHANGED. manifest {have[rel].get('sha256')[:16]}... "
                    f"disk {files[rel]['sha256'][:16]}...")
    for case in sorted(recorded):
        if recorded[case] and case not in now:
            problems.append(f"{case}: hashes recorded but the case is not built on disk")
    return problems


def write(corpus=CORPUS, manifest_path=MANIFEST, built_path=BUILT):
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    now = compute(corpus, built_path)
    n = 0
    for case in manifest["cases"]:
        files = now.get(case["name"])
        if files is None:
            case.pop("file_hashes", None)
            continue
        case["file_hashes"] = files
        n += len(files)
    manifest["file_hashes_note"] = (
        "Added 2026-09-01. sha256 detects any local edit with no network; git_blob is git's own "
        "object id, so `git cat-file blob <git_blob>` in a clone of the named repository resolves "
        "the same bytes, and `git rev-parse <commit>:<path>` proves the blob is the one that "
        "commit produced. Recompute and check with `python tools/corpus_hashes.py`. Before this "
        "existed, a one-character edit to any corpus file passed every check in the repository "
        "and changed every verdict.")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return n


def demo():
    """Self-check the two functions a defect would hide in: the blob id and the drift detector."""
    import tempfile
    # git's own documented example: the blob id of "what is up, doc?\n" plus a known-empty blob.
    assert git_blob_id(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391", git_blob_id(b"")
    assert git_blob_id(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"

    with tempfile.TemporaryDirectory() as d:
        corpus = os.path.join(d, "corpus2")
        case = os.path.join(corpus, "demo-case")
        for variant in VARIANTS:
            os.makedirs(os.path.join(case, variant, "src"))
            with open(os.path.join(case, variant, "src", "lib.rs"), "w") as fh:
                fh.write("fn %s() {}\n" % variant)
        built = os.path.join(d, "built.json")
        with open(built, "w") as fh:
            json.dump([{"name": "demo-case", "repo": "x/y", "fix": "f" * 40, "parent": "a" * 40,
                        "files": ["deep/path/lib.rs"]}], fh)
        got = compute(corpus, built)
        assert set(got["demo-case"]) == {"insecure/src/lib.rs", "secure/src/lib.rs"}, got
        assert got["demo-case"]["insecure/src/lib.rs"]["upstream"]["commit"] == "a" * 40
        assert got["demo-case"]["secure/src/lib.rs"]["upstream"]["commit"] == "f" * 40

        manifest = os.path.join(d, "manifest.json")
        with open(manifest, "w") as fh:
            json.dump({"cases": [{"name": "demo-case", "class": "x"}]}, fh)
        assert report(corpus, manifest, built), "an unhashed case must be reported"
        write(corpus, manifest, built)
        assert report(corpus, manifest, built) == [], report(corpus, manifest, built)

        # the whole point: one character changes, and the check says so
        with open(os.path.join(case, "insecure", "src", "lib.rs"), "w") as fh:
            fh.write("fn insecure() {} \n")
        problems = report(corpus, manifest, built)
        assert any("CONTENT CHANGED" in p for p in problems), problems
    print("corpus_hashes: OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write the hashes into the manifest")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        demo()
        return 0
    if args.write:
        n = write()
        print(f"recorded {n} file hashes in {MANIFEST}")
    problems = report()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  " + p)
        return 1
    print("every corpus file matches the hash recorded in the manifest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
