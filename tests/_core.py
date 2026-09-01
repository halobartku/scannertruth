"""Shared fixtures and the runner behind every module in `tests/`.

`python test_all.py` is still the command. It imports every module in this package and runs
each `test_*` function through `check` below, so the suite output does not change. Anything two
modules need lives here; everything else stays beside the checks that use it.
"""
import io
import json
import os
import sys

# The tools live in tools/ so the repository root stays legible. Nothing is packaged, so the
# import path is set here rather than asking every reader to export PYTHONPATH.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

VERBOSE = "-v" in sys.argv
PASSED = []
FAILED = []


def check(name, fn):
    try:
        fn()
        PASSED.append(name)
        if VERBOSE:
            print(f"  ok   {name}")
    except AssertionError as e:
        FAILED.append((name, str(e) or "assertion failed"))
        print(f"  FAIL {name}: {e}")
    except Exception as e:
        FAILED.append((name, f"{type(e).__name__}: {e}"))
        print(f"  ERROR {name}: {type(e).__name__}: {e}")


def _case(tmp, vulnerable, fixed):
    case = os.path.join(tmp, "case")
    for variant, text in (("insecure", vulnerable), ("secure", fixed)):
        d = os.path.join(case, variant, "src")
        os.makedirs(d)
        io.open(os.path.join(d, "lib.rs"), "w", encoding="utf-8").write(text)
    return case, os.path.join(case, "insecure", "src", "lib.rs"), \
        os.path.join(case, "secure", "src", "lib.rs")


VULN = "a\nb\nvulnerable_line\nd\n"
FIXED = "a\nb\nguard()\nvulnerable_line\nd\n"
MAP = {"1-account-data-matching": ["RULE-X"]}


# The directory name has to be the one `_case` actually creates. It said `synthetic-case` until
# 2026-09-01, and the control still passed, because `score_case` matched a finding to a case by
# basename and ignored every directory above it (error 31). Once the scorer started requiring the
# finding to be inside the case it scores, the fixture stopped naming the case under test. The
# assertions below are unchanged; only the path the fixture writes is now coherent.
VARIANT_PATHS = {"insecure": "case/insecure/src/lib.rs",
                 "secure": "case/secure/src/lib.rs"}


def _findings_file(tmp, kind, rule, line):
    """A findings file in `kind`'s own envelope, naming the fix site of the synthetic case."""
    path = VARIANT_PATHS["insecure"]
    blob = {
        "radar": [{"name": rule, "description": "", "severity": "high",
                   "locations": [f"{path}:{line}:1"]}],
        "sol-audit": {"findings": [{"rule_id": rule, "file": path, "line": line}]},
        "vaultlint": {"findings": [{"rule_id": rule, "file": path, "line": line}]},
        "semgrep": {"results": [{"check_id": rule, "path": path, "start": {"line": line}}]},
        "solsec": {"analysis_results": [{"rule_name": rule, "file_path": "./" + path,
                                         "line_number": line}]},
    }[kind]
    dest = os.path.join(tmp, f"{kind}-findings.json")
    with io.open(dest, "w", encoding="utf-8") as fh:
        json.dump(blob, fh)
    return dest


def _documented_command_files():
    """Every document that tells a reader to run something.

    The engineering logs are excluded on purpose: a log records what was run on a date, and
    correcting a command in one would be rewriting history rather than fixing a document.

    Same list as `_publication_documents`, and taken from the same place, so a document cannot be
    live for one check and invisible to the other.
    """
    return _publication_documents()


def _publication_documents():
    """Every markdown document that speaks in the present tense.

    The engineering logs are excluded, and only they: they record what was believed on a date,
    including the wording later retracted, and a log that is edited to agree with today is not a
    log. Everything else is a live claim.

    The list comes from `git ls-files` where there is a git history, not from a directory walk.
    A walk picks up whatever else happens to be sitting in the working tree - during this work it
    found nine unrelated scratch documents in an untracked directory - so what the check scans
    would differ between a contributor's machine and CI. The same hazard applies to `mappings/`.
    """
    import os, subprocess
    out = []
    try:
        p = subprocess.run(["git", "ls-files", "*.md"], capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            out = [line.strip() for line in p.stdout.splitlines() if line.strip()]
    except OSError:
        out = []
    if not out:
        for base, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs
                       if not d.startswith(".") and d not in ("__pycache__",)]
            for f in sorted(files):
                if f.endswith(".md"):
                    out.append(os.path.join(base, f).replace("\\", "/"))
    return sorted(f for f in (x.replace("\\", "/") for x in out)
                  if not os.path.basename(f).startswith("ENGINEERING-LOG"))
