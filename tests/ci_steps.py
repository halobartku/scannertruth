"""The CI workflow's own steps, checked like every other promise in this repository.

Error 44 (2026-09-02): `mappings/model-classes.json` landed in `mappings/`, the test suite was
taught to recognise it, and the suite stayed green - while `control_c1.py` and `control_c2.py`,
which run only as CI steps, indexed `["map"]` on it and put the badge red on five platforms.
Error 45 did it again the same day. The lesson, named at the end of error 44: a check that lives
outside the suite has no test that says it still runs on the current tree.

So the workflow is read as a promise, the same way README commands are. From
`.github/workflows/verify.yml` these commands are extracted:

    python test_all.py
    python tools/score.py --demo
    python tools/score2.py --demo
    python tools/build_corpus2.py --demo
    python tools/unmapped_check.py --demo
    python tools/corpus_ghsa.py --demo
    python tools/preregistration_check.py --demo
    python tools/preregistration_check.py
    python tools/verify.py
    python tools/control_c2.py
    python tools/unmapped_check.py --findings raw/c2-radar-complete.json --kind sol-audit
    python tools/unmapped_check.py --findings raw/c2-vaultlint-complete.json --kind sol-audit
    python tools/unmapped_check.py --findings raw/c2-sol-audit.json --kind sol-audit
    python tools/run_all.py --verify-coverage

Four questions, each named after a way this list has already broken:

    every script named exists      - a rename deletes a step and the badge goes red on a stranger
    every script imports           - a moved module is error 44's cousin, caught before the push
    every flag is still offered    - a flag renamed after a demo was written (error 44's shape:
                                     the command runs, the argument is gone, the step dies)
    every command runs green       - in a scratch copy of the tree, the same way CI's runner sees
                                     it, in minutes, not a matrix's worth of setup

The last one runs the actual commands rather than parsing them, because that is the only level
at which error 44 lived: both scripts existed, both imported, the flag was valid - and the
command still died on a KeyError nobody local had run into. What cannot be cheap is said so
below rather than skipped quietly: `control_c2.py` needs ~3 minutes over the whole corpus, and
the workflow is guarded by inventory + flag checks instead of a run.

The scanner is deliberately dumb. `python <script> [flags]` and nothing else: expressions,
`pip install`, `make` - nothing in this workflow uses them, and a scanner that tries to
understand every shell line will be wrong about the interesting ones. If a step needs
something richer, it starts a fresh run block, and that is visible here as a command that
fails to parse.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

from ._core import ROOT

WORKFLOW = os.path.join(ROOT, ".github", "workflows", "verify.yml")

# `python test_all.py` would run this module inside itself: a suite that re-enters itself on
# every run cannot fail cleanly and takes twice as long to say nothing new. The "Test suite"
# step's health is the run you are already inside.
NOT_RUN_HERE = {"test_all.py"}


def _ci_commands():
    """Every `python ...` command the workflow runs, as (step_name, command) pairs.

    Straight text scan over `run:` blocks. A `run: |` block can hold several commands; a
    single-line `run:` holds one. `$ ...` template lines belong to the runner, not the tree,
    and are skipped - the matrix expands them, this repository cannot evaluate them.
    """
    lines = open(WORKFLOW, encoding="utf-8").read().splitlines()
    commands, step, block = [], None, False
    for line in lines:
        m = re.match(r"\s*-\s*name:\s*(.+)$", line)
        if m:
            step, block = m.group(1).strip(), False
            continue
        if re.match(r"\s*run:\s*\|\s*$", line):
            block = True
            continue
        if re.match(r"\s*run:\s*[^|]", line):
            block = False
            m2 = re.match(r"\s*run:\s*(.+)$", line)
            if m2 and not m2.group(1).strip().startswith("$"):
                commands.append((step, m2.group(1).strip()))
            continue
        if block:
            cmd = line.strip()
            if cmd.startswith("python "):
                commands.append((step, cmd))
    return commands


def _split(argv):
    """One space-split, flags recognised by shape (`--x` or `--x=y`), no quoting.

    Nothing in this workflow quotes an argument; if that ever changes, the command is new
    and this splitter must learn it - the tests below would say which one.
    """
    return argv.split()


def test_the_workflow_scanner_finds_any_commands_at_all():
    """A scanner that returns nothing on a live workflow looks exactly like one that
    works. Fourteen commands run in verify.yml today; zero means the scanner broke,
    not that CI got simpler."""
    cmds = _ci_commands()
    assert len(cmds) == 14, (
        f"expected 14 python commands in verify.yml, scanner found {len(cmds)}: "
        f"{[c[1] for c in cmds]} - update the module docstring and this count together")


def test_every_script_a_ci_step_calls_exists():
    """A step whose script was renamed or deleted goes red on the next push and green
    nowhere else. This is the existence half of `test_documented_commands`, pointed at
    the workflow instead of the prose."""
    missing = []
    for step, argv in _ci_commands():
        script = _split(argv)[1]
        if not os.path.isfile(os.path.join(ROOT, script)):
            missing.append(f"{step}: {argv}")
    assert not missing, f"CI steps call scripts that do not exist: {missing}"


def test_every_script_a_ci_step_calls_imports():
    """Error 44's cousin: the file is there, the import is not. Checked by running the
    script's own imports through compile+exec, so a module that moved or vanished dies
    here instead of in the badge."""
    bad = []
    seen = set()
    for step, argv in _ci_commands():
        script = _split(argv)[1]
        if script in seen:
            continue
        seen.add(script)
        path = os.path.join(ROOT, script)
        # compile() first: a SyntaxError must be reported as one, not as raw noise
        try:
            src = compile(open(path, encoding="utf-8").read(), path, "exec")
        except SyntaxError as e:
            bad.append(f"{script}: SyntaxError: {e}")
            continue
        namespace = {"__name__": "ci_step_import_check", "__file__": path}
        tools_dir = os.path.dirname(path)
        old_path = list(sys.path)
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        try:
            exec(src, namespace)
        except SystemExit:
            pass   # a well-behaved CLI that parses argv at import time and exits is fine
        except BaseException as e:
            bad.append(f"{script}: {type(e).__name__}: {e}")
        finally:
            sys.path[:] = old_path
    assert not bad, f"scripts CI calls that no longer import: {bad}"


def test_every_flag_a_ci_step_passes_is_still_offered():
    """A demo flag renamed after the step was written leaves a command that exists,
    imports, and dies on `unrecognized arguments`. Verify each `--flag` against the
    script's own argparse, where the script has one; a flag on a script without
    argparse is checked as a plain string in the source, which is the same contract
    the script's own `main` enforces."""
    bad = []
    for step, argv in _ci_commands():
        parts = _split(argv)
        script_path = os.path.join(ROOT, parts[1])
        flags = [a for a in parts[2:] if a.startswith("--")]
        src = open(script_path, encoding="utf-8").read()
        if "add_argument" in src:
            # ask argparse itself, exactly as the command will at 06:00 UTC on a
            # stranger's runner: a flag it never heard of is an error, not a pass
            probe = parts[2:] + ["--ci-steps-probe"]
            proc = subprocess.run([sys.executable, script_path] + probe,
                                  capture_output=True, text=True, cwd=ROOT, timeout=120)
            # our probe is nonsense on purpose: `error: unrecognized arguments:` means
            # argparse got as far as rejecting it, so every earlier flag was accepted
            if "unrecognized arguments" not in (proc.stderr or ""):
                continue
            for flag in flags:
                name = flag.split("=", 1)[0]
                if name not in src:
                    bad.append(f"{step}: {argv} -- {name} is not an argument of {parts[1]}")
        else:
            for flag in flags:
                if flag not in src:
                    bad.append(f"{step}: {argv} -- {parts[1]} never mentions {flag}")
    assert not bad, f"CI steps pass flags the scripts do not offer: {bad}"


def test_every_ci_command_runs_green_on_a_copy_of_the_tree():
    """Error 44 in one sentence: every file existed, every import passed, and the badge
    was still red because nothing had RUN the command on the tree as it stood.

    Each command runs in a scratch copy of the working tree, so the run sees the same
    files CI's checkout would, and cannot mistake the repository for a fixture. Scripts
    that write into the tree (the controls overwrite raw/*.json) stay honest by writing
    into the copy, never into the working tree. `test_all.py` is excluded: it is this
    suite, and a suite that re-entered itself would report its own failure as a defect.
    `control_c2.py` is excluded and says so: ~3 minutes over every corpus file under
    every mapping, every run, for a defect class the flag and import checks already
    cover. The excluded commands are asserted to be exactly those two, so the list
    cannot grow quietly.
    """
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        commands = [(step, _split(argv)) for step, argv in _ci_commands()]
        excluded = {a[1] for _, a in commands
                    if a[1] in NOT_RUN_HERE or a[1] == "tools/control_c2.py"}
        assert excluded == {"test_all.py", "tools/control_c2.py"}, (
            "the not-run list changed: " + repr(sorted(excluded)))
        to_run = [(s, a) for s, a in commands if a[1] not in excluded]

        # The copy is built from hard links, not shutil.copy2 of 39 MB of raw findings:
        # a fresh file per run is a fresh 39 MB of temp filesystem, and /tmp on a CI
        # runner is a size-capped tmpfs on a different device, where links cannot go.
        # The copy lives NEXT TO the repository (same filesystem, so one link per file,
        # no data copied) and outside it, so it never shows up in git status. The cost
        # of links is that a command writing through a shared inode would edit the
        # working tree's own file, so the tree is guarded: git status is compared
        # before and after, and any change - modification or untracked artefact -
        # fails this check by name.
        before = subprocess.run(["git", "status", "--porcelain"],
                                capture_output=True, text=True).stdout
        copy = tempfile.mkdtemp(prefix=".ci-steps-",
                                dir=os.path.dirname(ROOT) or ".")
        try:
            # the tracked tree and nothing else: a walk of the working directory would
            # smuggle untracked scratch files into the copy and the commands would run
            # against a tree CI never sees. `git ls-files` is the checkout's own list.
            tracked = subprocess.run(["git", "ls-files", "-z"],
                                     capture_output=True).stdout.split(b"\0")
            # dict.fromkeys, and it is not decoration: during a merge `git ls-files` prints one
            # line per index STAGE, so every conflicted path arrives two or three times, the
            # second os.link hits an existing destination and this check dies with
            # FileExistsError instead of saying anything about CI. Found on 2026-09-03 while
            # merging this branch, which is the first time the suite was run mid-merge.
            tracked = list(dict.fromkeys(
                t.decode("utf-8", "surrogateescape") for t in tracked if t))
            if tracked:
                for rel in tracked:
                    if not os.path.isfile(rel):
                        continue
                    dest = os.path.join(copy, rel)
                    os.makedirs(os.path.dirname(dest) or copy, exist_ok=True)
                    os.link(rel, dest)
            else:
                for root, dirs, files in os.walk("."):
                    dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".omc")]
                    rel = os.path.relpath(root, ".")
                    dest = os.path.join(copy, rel) if rel != "." else copy
                    os.makedirs(dest, exist_ok=True)
                    for fn in files:
                        os.link(os.path.join(root, fn), os.path.join(dest, fn))
            # .git is copied, not linked: `preregistration_check.py` reads the history,
            # and in a copy without it the tool says "cannot check" and exits 0 - green
            # while enforcing nothing, which is the quiet failure fetch-depth: 0 in the
            # workflow exists to prevent. 5 MB of git objects is cheap next to that.
            shutil.copytree(os.path.join(ROOT, ".git"), os.path.join(copy, ".git"))
            failures = []
            for step, argv in to_run:
                # argv[0] is the literal `python` from the workflow; this process is
                # already the interpreter, so it is dropped rather than re-run
                proc = subprocess.run([sys.executable] + argv[1:], capture_output=True,
                                      text=True, cwd=copy, timeout=600)
                if argv[1:] == ["tools/preregistration_check.py"] and \
                        "cannot check" in (proc.stdout or ""):
                    # the history is in the copy (see above); a "cannot check" now
                    # means the step went green without enforcing its rule
                    failures.append(f"{step}: preregistration_check ran but could not "
                                    "check - the rule is not being enforced")
                if proc.returncode != 0:
                    excerpt = (proc.stderr or proc.stdout).strip().splitlines()
                    tail = excerpt[-3:] if excerpt else ["(no output)"]
                    failures.append(f"{step}: `{' '.join(argv)}` exit {proc.returncode}: "
                                    + " | ".join(tail))
            assert not failures, ("a command CI runs fails on the current tree - the badge "
                                  f"is red or about to be: {failures}")
        finally:
            shutil.rmtree(copy, ignore_errors=True)
            after = subprocess.run(["git", "status", "--porcelain"],
                                   capture_output=True, text=True).stdout
            assert after == before, (
                "running the CI commands outside a throwaway copy changed the working "
                f"tree:\n{after}")
    finally:
        os.chdir(cwd)


def test_the_calibration_control_survives_every_file_in_mappings():
    """Error 44, verbatim: `control_c2.py` - a CI step - iterated `mappings/*.json` and
    indexed `["map"]`, and died on the adjudication file that has no `map` key. The fix
    skips such files and says why; this check is what makes the fix load-bearing, because
    `control_c2.py` is too slow to run in full here (see above) and a reverted guard would
    otherwise redden the badge and nothing else.

    It drives `control_c2.score()` itself over every mapping file with null findings:
    null scores zero against every mapping, so any nonzero answer means the scoring
    path itself broke, and any KeyError means the guard is gone. The mapping files are
    read from the working tree, the real ones, because the defect was a real file that
    the fixtures of the day did not contain.
    """
    import contextlib
    import io as _io
    import json
    import tempfile
    import control_c2
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        cases = json.load(open("corpus2/manifest.json", encoding="utf-8"))["cases"]
        cases = [c for c in cases if c.get("valid", True)]
        with tempfile.TemporaryDirectory(prefix="ci-steps-null-") as d:
            findings = os.path.join(d, "null-findings.json")
            with open(findings, "w", encoding="utf-8") as fh:
                json.dump({"findings": []}, fh)
            quiet = _io.StringIO()
            with contextlib.redirect_stdout(quiet):
                worst = control_c2.score("null", findings, cases)
            # control_c1.report is the other function error 44 named: the same loop,
            # the same guard, the same KeyError when the guard is gone. Driven with
            # null findings for the same reason - it must answer (0, 0) or the scoring
            # path itself is broken.
            import control_c1
            with contextlib.redirect_stdout(quiet):
                worst_c1 = control_c1.report([], "null")
        assert worst == 0, (
            "null findings must score zero against every mapping; the calibration "
            f"control's scoring path is broken (worst={worst})")
        assert worst_c1 == (0, 0), (
            f"control_c1.report must answer (0, 0) on null findings, got {worst_c1}")
    finally:
        os.chdir(cwd)
