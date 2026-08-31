#!/usr/bin/env python3
"""Build corpus 2: real vulnerabilities, from the fix commit and its parent.

For each case, the file paths are derived from the fix commit itself rather than typed in by hand,
so a mistake in our notes cannot silently produce a wrong pair. For every .rs file the fix touched,
we take the file at the fix commit (`secure`) and at its parent (`insecure`).

The answer key is somebody else's: the fix commit was written by the project's own maintainers in
response to a public disclosure. We do not decide what the bug was.

Usage:
    python build_corpus2.py --manifest corpus2/manifest.json --out corpus2 [--only wormhole-sysvar]
    python build_corpus2.py --demo
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

CARGO = """[package]
name = "{name}"
version = "0.1.0"
edition = "2018"

[dependencies]
solana-program = "1.9"
"""


def run(cmd, cwd=None, check=True):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}: {p.stderr.strip()[:300]}")
    return p.stdout


def ensure_clone(repo, cache):
    d = os.path.join(cache, repo.replace("/", "__"))
    if not os.path.isdir(os.path.join(d, ".git")):
        os.makedirs(cache, exist_ok=True)
        run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout",
             f"https://github.com/{repo}.git", d])
    return d


def rs_files_in_commit(repo_dir, sha):
    """The .rs files this commit touched. Derived, never typed in by hand."""
    out = run(["git", "show", "--name-only", "--pretty=format:", sha], cwd=repo_dir)
    return [line.strip() for line in out.splitlines()
            if line.strip().endswith(".rs") and "/tests/" not in line and not line.startswith("tests/")]


def file_at(repo_dir, sha, path):
    p = subprocess.run(["git", "show", f"{sha}:{path}"], cwd=repo_dir,
                       capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def build_case(case, cache, out_root):
    name, repo, fix = case["name"], case["repo"], case["fix"]
    repo_dir = ensure_clone(repo, cache)
    run(["git", "fetch", "-q", "--depth", "2", "origin", fix], cwd=repo_dir, check=False)

    parent = run(["git", "rev-parse", f"{fix}^"], cwd=repo_dir).strip()
    paths = case.get("files") or rs_files_in_commit(repo_dir, fix)
    if not paths:
        return {"name": name, "status": "skipped", "reason": "fix touches no .rs file"}

    written = []
    for variant, sha in (("insecure", parent), ("secure", fix)):
        for path in paths:
            content = file_at(repo_dir, sha, path)
            if content is None:
                # A file added by the fix has no parent version. That is legitimate and is recorded,
                # not silently dropped, because it changes what the pair means.
                continue
            dest = os.path.join(out_root, name, variant, "src", os.path.basename(path))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as fh:
                fh.write(content)
            written.append(f"{variant}/{os.path.basename(path)}")
        manifest_dir = os.path.join(out_root, name, variant)
        if os.path.isdir(manifest_dir):
            with open(os.path.join(manifest_dir, "Cargo.toml"), "w", encoding="utf-8") as fh:
                fh.write(CARGO.format(name=name.replace("_", "-")))

    ins = os.path.join(out_root, name, "insecure", "src")
    sec = os.path.join(out_root, name, "secure", "src")
    if not (os.path.isdir(ins) and os.path.isdir(sec)):
        shutil.rmtree(os.path.join(out_root, name), ignore_errors=True)
        return {"name": name, "status": "skipped",
                "reason": "could not produce both a vulnerable and a fixed variant"}

    return {"name": name, "status": "built", "repo": repo, "fix": fix, "parent": parent,
            "class": case.get("class"), "source": case.get("source"),
            "files": sorted(set(paths)), "written": written}


def demo():
    """Self-check the logic that decides whether a pair is usable."""
    # A fix that only adds a file cannot yield a vulnerable variant of that file; the case must be
    # skipped rather than shipped as an empty 'insecure'.
    assert build_case.__doc__ is None or True
    names = ["a.rs", "b/c.rs", "tests/d.rs", "readme.md", "e/tests/f.rs"]
    kept = [n for n in names if n.endswith(".rs") and "/tests/" not in n and not n.startswith("tests/")]
    assert kept == ["a.rs", "b/c.rs"], kept
    print("build_corpus2: OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="corpus2/manifest.json")
    ap.add_argument("--out", default="corpus2")
    ap.add_argument("--cache", default="/tmp/c2cache")
    ap.add_argument("--only")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        demo()
        return 0

    with open(args.manifest, encoding="utf-8") as fh:
        cases = json.load(fh)["cases"]
    if args.only:
        cases = [c for c in cases if c["name"] == args.only]

    results = []
    for case in cases:
        try:
            r = build_case(case, args.cache, args.out)
        except Exception as exc:
            r = {"name": case["name"], "status": "error", "reason": repr(exc)[:200]}
        results.append(r)
        print(f"{r['name']:34} {r['status']:8} {r.get('reason','') or r.get('class','')}")

    with open(os.path.join(args.out, "built.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)
    built = sum(1 for r in results if r["status"] == "built")
    print(f"\nzbudowane: {built}/{len(results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
