#!/usr/bin/env python3
"""Does the git history actually show each mapping was committed before its run?

`docs/PROTOCOL.md` 3a used to claim that every mapping after the first was committed "in its own
commit, before the scanner is run", and that the commit timestamp was the pre-registration. On
2026-09-01 an external review checked that claim against the history and it did not hold: the seven
mappings measured on 2026-08-31 each first appear in the same commit as the result they score, three
of them in the commit carrying the headline. Nothing was fitted to a score, but nothing proved that
either, and a claim of process evidence that has no process evidence is worse than no claim.

The wording was retracted. This is the enforcement that replaces it, so the claim becomes checkable
instead of asserted:

    a commit that adds `mappings/<scanner>.json` may touch nothing outside `mappings/`.

An allowlist rather than a list of forbidden result paths, because the repository has already been
restructured once and a forbidden-path list would have silently stopped seeing `RESULTS-all.md` the
day it moved to `docs/results/`. "Its own commit" is the actual rule, so that is what is checked.
Mappings added before `ENFORCED_FROM` are reported as unproven rather than failing, because
rewriting history to make an old claim true is the opposite of the point. That set is derived from
the history, not typed here, so it cannot be quietly extended by adding a name to a list.

    python tools/preregistration_check.py
    python tools/preregistration_check.py --demo
"""
import argparse
import os
import subprocess
import sys

# The date the rule became enforceable, which is the date the retraction was written. Every mapping
# added on or after this date must have a clean add-commit. Everything before it is on the record as
# unproven in docs/PROTOCOL.md 3a and docs/KNOWN-LIMITATIONS.md.
ENFORCED_FROM = "2026-09-01"

# The only directory a pre-registration commit may touch. Anything else in the same commit means
# the mapping and something else moved together, and the timestamp stops separating them.
ALLOWED_PREFIX = "mappings/"

# Files in mappings/ that are not rule maps and cannot be pre-registered by construction: the
# adjudication of the free-text class names the model auditors returned is written after the
# answers are read, and says so (KNOWN-LIMITATIONS 49). Reported as post-hoc, never as
# pre-registered and never as a violation; the rule above is for rule maps.
POST_HOC = {"mappings/model-classes.json"}


def git(args, repo, env=None):
    p = subprocess.run(["git"] + args, cwd=repo, capture_output=True, text=True,
                       env=dict(os.environ, **env) if env else None)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.strip()[:200]}")
    return p.stdout


def history_is_usable(repo):
    """A shallow or absent history cannot answer the question. Say so; do not pass by default."""
    if not os.path.isdir(os.path.join(repo, ".git")):
        return False, "no .git directory: this is a copy of the tree, not a clone"
    try:
        shallow = git(["rev-parse", "--is-shallow-repository"], repo).strip()
    except (RuntimeError, OSError) as exc:
        return False, f"git unavailable: {exc}"
    if shallow == "true":
        return False, "shallow clone: fetch the full history (actions/checkout fetch-depth: 0)"
    return True, ""


def touched_by(sha, repo):
    out = git(["show", "--name-only", "--pretty=format:", sha], repo)
    return [line.strip() for line in out.splitlines() if line.strip()]


def added_in(path, repo):
    """(sha, iso-date, subject) of the commit that first added `path`, or None."""
    out = git(["log", "--diff-filter=A", "--format=%H\t%ad\t%s", "--date=short", "--", path], repo)
    lines = [l for l in out.splitlines() if l.strip()]
    if not lines:
        return None
    sha, date, subject = lines[-1].split("\t", 2)
    return sha, date, subject


def audit(repo="."):
    """One record per tracked mapping: was its add-commit free of results?

    Returns (records, reason_unusable). `records` is empty when the history cannot answer.
    """
    ok, why = history_is_usable(repo)
    if not ok:
        return [], why

    mappings = [p for p in git(["ls-files", "mappings"], repo).splitlines()
                if p.endswith(".json")]
    records = []
    for path in sorted(mappings):
        if path in POST_HOC:
            records.append({"mapping": path, "status": "post-hoc",
                            "detail": "an adjudication written after the runs, by design"})
            continue
        found = added_in(path, repo)
        if found is None:
            records.append({"mapping": path, "status": "untracked",
                            "detail": "no add-commit in this history"})
            continue
        sha, date, subject = found
        alongside = [f for f in touched_by(sha, repo) if not f.startswith(ALLOWED_PREFIX)]
        enforced = date >= ENFORCED_FROM
        if not alongside:
            status = "pre-registered"
        elif enforced:
            status = "VIOLATION"
        else:
            status = "unproven"
        records.append({"mapping": path, "sha": sha[:7], "date": date, "subject": subject,
                        "alongside": alongside, "status": status})
    return records, ""


def demo():
    """Build two throwaway commits and check the rule separates them."""
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        git(["init", "-q", "."], d, env)
        os.makedirs(os.path.join(d, "mappings"))
        os.makedirs(os.path.join(d, "docs", "results"))

        # clean: the mapping arrives alone
        with open(os.path.join(d, "mappings", "clean.json"), "w") as fh:
            json.dump({"map": {}}, fh)
        git(["add", "-A"], d, env)
        git(["commit", "-q", "-m", "pre-register clean", "--date", "2026-09-02T00:00:00"], d, env)

        # dirty: the mapping arrives with the result it scores
        with open(os.path.join(d, "mappings", "dirty.json"), "w") as fh:
            json.dump({"map": {}}, fh)
        with open(os.path.join(d, "docs", "results", "R.md"), "w") as fh:
            fh.write("dirty scores 9/9\n")
        git(["add", "-A"], d, env)
        git(["commit", "-q", "-m", "measure dirty", "--date", "2026-09-02T00:01:00"], d, env)

        by_name = {r["mapping"]: r for r in audit(d)[0]}
        assert by_name["mappings/clean.json"]["status"] == "pre-registered", by_name
        assert by_name["mappings/dirty.json"]["status"] == "VIOLATION", by_name
    print("preregistration_check: OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        demo()
        return 0

    records, why = audit(args.repo)
    if why:
        print(f"cannot check pre-registration: {why}")
        return 0

    for r in records:
        extra = ("with " + ", ".join(r["alongside"][:4])) if r.get("alongside") else ""
        print(f"{r['status']:14} {r['mapping']:32} {r.get('sha',''):8} {r.get('date','')} {extra}")

    unproven = [r for r in records if r["status"] == "unproven"]
    bad = [r for r in records if r["status"] in ("VIOLATION", "untracked")]
    post_hoc = [r for r in records if r["status"] == "post-hoc"]
    print(f"\n{len(records)} mappings: "
          f"{sum(1 for r in records if r['status'] == 'pre-registered')} pre-registered, "
          f"{len(unproven)} unproven (added before {ENFORCED_FROM}), {len(bad)} in violation"
          + (f", {len(post_hoc)} post-hoc adjudication (not a rule map, cannot be pre-registered)"
             if post_hoc else ""))
    if unproven:
        print("The unproven ones are on the record in docs/PROTOCOL.md 3a. They are not evidence.")
    if bad:
        print("A mapping committed alongside a result is not pre-registered. Split the commit.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
