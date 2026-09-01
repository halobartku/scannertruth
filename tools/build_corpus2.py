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


def crate_root_for(repo_dir, sha, path):
    """Nearest ancestor directory of `path` that has a Cargo.toml at this commit.

    Extracting a lone .rs file into a synthetic manifest is packaging we invented, and a tool that
    needs project context is then penalised for our choice rather than its own behaviour. Taking the
    real crate removes that objection at the cost of dragging in sibling modules.
    """
    parts = path.split("/")[:-1]
    while parts:
        d = "/".join(parts)
        p = subprocess.run(["git", "cat-file", "-e", f"{sha}:{d}/Cargo.toml"],
                           cwd=repo_dir, capture_output=True)
        if p.returncode == 0:
            return d
        parts.pop()
    return None


def archive_dir(repo_dir, sha, subdir, dest):
    """Extract a whole directory at a commit. Returns True on success."""
    os.makedirs(dest, exist_ok=True)
    tar = subprocess.run(["git", "archive", sha, subdir], cwd=repo_dir, capture_output=True)
    if tar.returncode != 0 or not tar.stdout:
        return False
    untar = subprocess.run(["tar", "-x", "-C", dest], input=tar.stdout, capture_output=True)
    return untar.returncode == 0


def build_case_crates(case, cache, out_root):
    """Variant of build_case that takes the whole crate rather than the implicated file alone."""
    name, repo, fix = case["name"], case["repo"], case["fix"]
    repo_dir = ensure_clone(repo, cache)
    run(["git", "fetch", "-q", "--depth", "50", "origin", fix], cwd=repo_dir, check=False)
    parent = run(["git", "rev-parse", f"{fix}^"], cwd=repo_dir).strip()

    paths = case.get("files") or rs_files_in_commit(repo_dir, fix)
    if not paths:
        return {"name": name, "status": "skipped", "reason": "no implicated file"}

    crate = crate_root_for(repo_dir, fix, paths[0])
    if not crate:
        return {"name": name, "status": "skipped",
                "reason": f"no Cargo.toml above {paths[0]}; cannot form a real crate"}

    ok = {}
    for variant, sha in (("insecure", parent), ("secure", fix)):
        ok[variant] = archive_dir(repo_dir, sha, crate,
                                  os.path.join(out_root, name, variant))
    if not (ok["insecure"] and ok["secure"]):
        shutil.rmtree(os.path.join(out_root, name), ignore_errors=True)
        return {"name": name, "status": "skipped",
                "reason": f"crate {crate} not present in both commits"}

    n = 0
    for _, _, files in os.walk(os.path.join(out_root, name, "insecure")):
        n += sum(1 for f in files if f.endswith(".rs"))
    return {"name": name, "status": "built", "repo": repo, "fix": fix, "parent": parent,
            "class": case.get("class"), "crate": crate, "implicated": paths,
            "rs_files_in_crate": n}


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
            # newline="\n" is not cosmetic. The default translates every "\n" to "\r\n" on Windows,
            # so the extracted file stops being the upstream blob it claims to be. That is how
            # eight cases were re-encoded on 2026-09-01 (error 34). .gitattributes stops git
            # rewriting them on checkout; this stops us writing them wrong in the first place.
            with open(dest, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
            written.append(f"{variant}/{os.path.basename(path)}")
        manifest_dir = os.path.join(out_root, name, variant)
        if os.path.isdir(manifest_dir):
            with open(os.path.join(manifest_dir, "Cargo.toml"), "w", encoding="utf-8",
                      newline="\n") as fh:
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


def throwaway_repo(cache, repo="local/fixture"):
    """A two-commit git repository, offline, laid out where `ensure_clone` will find it.

    The parent commit contains the bug and the child fixes it, which is the orientation the whole
    corpus depends on. Building it here rather than in the test means `--demo` and the test suite
    exercise the same fixture, and neither needs the network.

    Returns (repo, fix_sha, cache).
    """
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    d = os.path.join(cache, repo.replace("/", "__"))
    os.makedirs(os.path.join(d, "src"), exist_ok=True)
    os.makedirs(os.path.join(d, "tests"), exist_ok=True)

    def g(*args):
        p = subprocess.run(["git"] + list(args), cwd=d, capture_output=True, text=True,
                           env=dict(os.environ, **env))
        if p.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)}: {p.stderr.strip()[:200]}")
        return p.stdout

    g("init", "-q", ".")
    with open(os.path.join(d, "src", "lib.rs"), "w", encoding="utf-8") as fh:
        fh.write("fn transfer() {\n    // no owner check\n}\n")
    with open(os.path.join(d, "tests", "t.rs"), "w", encoding="utf-8") as fh:
        fh.write("// test file, never part of a corpus case\n")
    with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("not rust\n")
    g("add", "-A")
    g("commit", "-q", "-m", "the vulnerable state")

    with open(os.path.join(d, "src", "lib.rs"), "w", encoding="utf-8") as fh:
        fh.write("fn transfer() {\n    require_owner();\n}\n")
    with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("still not rust\n")
    with open(os.path.join(d, "tests", "t.rs"), "w", encoding="utf-8") as fh:
        fh.write("// touched by the fix, and still not a corpus file\n")
    g("add", "-A")
    g("commit", "-q", "-m", "the fix")
    return repo, g("rev-parse", "HEAD").strip(), cache


def demo():
    """Self-check the logic that decides whether a pair is usable.

    This used to open with `assert build_case.__doc__ is None or True`, which cannot fail, and then
    re-implement the `.rs` filter inline instead of calling `rs_files_in_commit`. CI ran it as a
    self-check. Swapping `parent` and `fix` in `build_case` - which inverts the ground truth of
    every case built from then on - survived the whole suite. It runs against a real two-commit
    repository now, and calls the functions it claims to check.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        repo, fix, cache = throwaway_repo(d)
        repo_dir = ensure_clone(repo, cache)

        kept = rs_files_in_commit(repo_dir, fix)
        assert kept == ["src/lib.rs"], f"the fix touched src/lib.rs, tests/t.rs and README.md: {kept}"

        out = os.path.join(d, "out")
        r = build_case({"name": "case", "repo": repo, "fix": fix, "class": "owner-checks"},
                       cache, out)
        assert r["status"] == "built", r
        ins = open(os.path.join(out, "case", "insecure", "src", "lib.rs"), encoding="utf-8").read()
        sec = open(os.path.join(out, "case", "secure", "src", "lib.rs"), encoding="utf-8").read()
        assert "no owner check" in ins, f"insecure must hold the PARENT of the fix commit: {ins!r}"
        assert "require_owner" in sec, f"secure must hold the FIX commit: {sec!r}"
        assert "require_owner" not in ins, "the vulnerable variant must not contain the fix"
    print("build_corpus2: OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="corpus2/manifest.json")
    ap.add_argument("--out", default="corpus2")
    ap.add_argument("--cache", default="/tmp/c2cache")
    ap.add_argument("--only")
    ap.add_argument("--crates", action="store_true",
                    help="extract the whole crate containing the implicated file, not just the file")
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
            builder = build_case_crates if args.crates else build_case
            r = builder(case, args.cache, args.out)
        except Exception as exc:
            r = {"name": case["name"], "status": "error", "reason": repr(exc)[:200]}
        results.append(r)
        extra = r.get("reason") or (f"{r.get('crate','')}  ({r.get('rs_files_in_crate','?')} .rs)"
                                    if args.crates else r.get("class", ""))
        print(f"{r['name']:34} {r['status']:8} {extra}")

    with open(os.path.join(args.out, "built.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)
    built = sum(1 for r in results if r["status"] == "built")
    print(f"\nzbudowane: {built}/{len(results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
