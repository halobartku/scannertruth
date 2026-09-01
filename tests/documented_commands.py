from ._core import _documented_command_files


# ------------------------------------------------- documented commands still exist
# This check existed and could not see the defect it was written for. Its regex was
# `python (\w[\w-]*\.py)`, and `\w` matches neither `.` nor `/`, so `python ../tools/verify.py`
# matched nothing at all and was silently skipped. Two of the three commands in the documented
# entry point for a human resolved above the repository root, three more in the walkthrough did,
# the README's only Windows block said `toolserify.py`, and every one of them was invisible here.
# Found from outside on 2026-09-01.


def _documented_scripts(text):
    import re
    return set(re.findall(r"python3?\s+([A-Za-z0-9_./\\-]+\.py)", text))


def test_every_documented_command_runs_from_the_repository_root():
    """One working directory for every documented command, or a reader has to guess which.

    Error 25 was a reproduce block that mixed two working directories, and neither reading of it
    ran. `../tools/verify.py` is the same defect: correct if you are standing somewhere the
    document never names, broken from the place it tells you to stand.
    """
    import io as _io
    bad = []
    for doc in _documented_command_files():
        for script in sorted(_documented_scripts(_io.open(doc, encoding="utf-8").read())):
            if ".." in script.split("/") or ".." in script.split("\\"):
                bad.append(f"{doc}: {script}")
    assert not bad, ("documented commands must be written from the repository root, "
                     f"not relative to wherever the reader happens to be: {bad}")


def test_every_documented_command_names_a_script_that_exists():
    """A quickstart that names a script that no longer exists is a broken promise."""
    import io as _io, os
    missing = []
    for doc in _documented_command_files():
        for script in sorted(_documented_scripts(_io.open(doc, encoding="utf-8").read())):
            if not os.path.exists(script.replace("\\", "/")):
                missing.append(f"{doc}: {script}")
    assert not missing, f"documents name scripts that do not exist: {missing}"


def test_every_command_in_the_readme_is_runnable():
    """The README's quickstart is the front door: a command naming a script
    that does not exist breaks the two-minute promise on the first paste.
    Backslash paths are normalised, because the Windows block is legitimate."""
    import io as _io, os, re
    s = _io.open("README.md", encoding="utf-8").read()
    scripts = set(p.replace("\\", "/") for p in re.findall(r"python3? ([\w./\\-]+\.py)", s))
    missing = [x for x in sorted(scripts) if not os.path.exists(x)]
    assert not missing, f"README names scripts that do not exist: {missing}"


def test_no_control_bytes_hiding_in_any_document():
    """The Windows quickstart shipped a vertical tab inside `tools\verify.py`,
    so the command read `python tools\x0berify.py` and failed when pasted.
    A control byte is invisible in every renderer and corrupts whatever a
    reader copies. Markdown has no legitimate use for one."""
    import os
    bad = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", ".omc", "__pycache__", "node_modules")]
        for fn in files:
            if not fn.endswith(".md"):
                continue
            path = os.path.join(root, fn)
            data = open(path, "rb").read()
            for off, b in enumerate(data):
                if b < 0x20 and b not in (0x09, 0x0A, 0x0D):
                    line = data.count(b"\n", 0, off) + 1
                    bad.append(f"{path}:{line} byte 0x{b:02x}")
                    break
    assert not bad, f"control bytes inside documents: {bad}"


def test_documents_linked_from_the_readme_exist():
    import io as _io, os, re
    s = _io.open("README.md", encoding="utf-8").read()
    links = set(re.findall(r"\]\((?!http)([A-Za-z0-9_./-]+\.md)\)", s))
    missing = [x for x in sorted(links) if not os.path.exists(x)]
    assert not missing, f"README links to missing files: {missing}"


def test_the_platform_claims_match_what_ci_actually_runs():
    """The README tells a stranger which systems and Python versions work. That claim
    is only worth anything if the machines we do not control actually run them, so it
    is derived from the workflow rather than typed beside it."""
    import io as _io, re
    ci = _io.open(".github/workflows/verify.yml", encoding="utf-8").read()
    s = _io.open("README.md", encoding="utf-8").read()

    for os_name in ("windows", "macos", "ubuntu"):
        assert f"{os_name}-latest" in ci, \
            f"README promises {os_name} but CI no longer runs it"

    versions = sorted({v for v in re.findall(r'python-version: "(\d+\.\d+)"', ci)},
                      key=lambda v: [int(x) for x in v.split(".")])
    lo, hi = versions[0], versions[-1]
    assert f"Python {lo}-{hi}" in s, (
        f"README must state the Python range CI proves, which is {lo}-{hi}; "
        f"found versions {versions}")


def test_a_backslash_path_maps_to_the_same_case_as_a_forward_slash_one():
    """The README says Windows is in CI because a scorer can get paths quietly wrong.
    This is the check that makes the sentence true rather than reassuring."""
    import score
    mapping = {"2-owner-checks": ["R"]}
    posix = score.score([("R", "x/2-owner-checks/insecure/lib.rs")], mapping)
    win = score.score([("R", r"C:\x\2-owner-checks\insecure\lib.rs")], mapping)
    assert posix == win, (
        "the same finding located by a Windows path scores differently from a POSIX one: "
        f"{posix!r} vs {win!r}")


def test_the_error_count_matches_the_logs():
    """The README's error count is its strongest claim, so it is the one most worth
    keeping honest. Derived from the logs rather than typed, because the count only
    ever goes up and a stale figure understates exactly the thing we want on record."""
    import io as _io, re, glob
    logged = 0
    for f in sorted(glob.glob("docs/ENGINEERING-LOG-*.md")):
        s = _io.open(f, encoding="utf-8").read()
        # Two heading schemes: `**Error N.` inline up to error 37, `## Error N.` from 38 on. The
        # regex saw only the first until 2026-09-01 and the README understated the record by
        # four while this check passed. Both forms count; a number is counted once whichever
        # form it uses, or both.
        numbers = {int(n) for n in re.findall(r"(?:\*\*|^#+ )Error (\d+)", s, re.M)}
        logged = max(logged, *numbers) if numbers else logged
    s = _io.open("README.md", encoding="utf-8").read()
    claimed = re.search(r"\*\*\[(\d+) of our own errors\]", s)
    assert claimed, "the README no longer states an error count; that claim is load-bearing"
    assert int(claimed.group(1)) == logged, (
        f"README claims {claimed.group(1)} errors but the logs number up to {logged}")


def test_the_readme_links_the_newest_engineering_log():
    """A reader following the error link must land on the current log, not the one that
    happened to be newest when the sentence was written."""
    import io as _io, glob, os
    newest = sorted(glob.glob("docs/ENGINEERING-LOG-*.md"))[-1]
    s = _io.open("README.md", encoding="utf-8").read()
    assert os.path.basename(newest) in s, (
        f"README does not link the newest engineering log ({newest})")



def _noisy_control_quantities():
    """Every number the noisy control legitimately produces, computed, never typed.

    Both figures are products of two things the repository already knows: how many non-empty
    lines the control flags, and how many distinct mapped rule ids it flags them under. Deriving
    them costs about ten milliseconds, so there is no excuse for a document to carry a stale one.
    """
    import json, os, sys
    sys.path.insert(0, "tools")
    import control_c1, control_c2

    rules = len(control_c2.every_rule())
    c1_lines = sum(len(v) for v in control_c1.inventory_from_artefact().values())

    cases = [c for c in json.load(open("corpus2/manifest.json", encoding="utf-8"))["cases"]
             if c.get("valid", True)]
    c2_lines = 0
    for c in cases:
        for variant in ("insecure", "secure"):
            d = os.path.join("corpus2", c["name"], variant, "src")
            if not os.path.isdir(d):
                continue
            for fn in sorted(os.listdir(d)):
                if fn.endswith(".rs"):
                    with open(os.path.join(d, fn), encoding="utf-8", errors="replace") as fh:
                        c2_lines += sum(1 for line in fh if line.strip())
    return {"rules": rules, "c1_lines": c1_lines, "c2_lines": c2_lines,
            "c1_findings": c1_lines * rules, "c2_findings": c2_lines * rules}


def test_no_document_states_a_noisy_control_figure_the_tools_do_not_produce():
    """Error 33 corrected the corpus-1 control from 931 findings to 81,928, and AGENTS.md kept the
    retracted figure for eight hours after the front page was fixed, because the derived-count
    check counts tests and nothing else while the control figures are typed by hand.

    The first version of this check compared every number in a noisy-control sentence against a
    set of legal quantities. It passed, and then a mutation putting 931 back as a findings count
    SURVIVED it, because 931 is legal: it is the line count. A check that accepts the right number
    under the wrong noun is not a check.

    So the noun decides. `931 findings` is the retracted claim; `931 non-empty lines` is the fact
    it was derived from. Each quantity is checked against what it is a count OF.

    Known limit, stated rather than left for someone to discover: this keys on the word "noisy",
    so a sentence that discusses the control without naming it is out of scope. AGENTS.md contains
    one such sentence on purpose, describing what the broken artefact used to emit, in the past
    tense. Widening the match to catch it would mean teaching the check to recognise historical
    narration, and a check that learns exceptions to prose stops guarding anything.
    """
    import io as _io, re
    q = _noisy_control_quantities()
    expected = {
        "findings": {q["c1_findings"], q["c2_findings"]},
        "lines": {q["c1_lines"], q["c2_lines"]},
        "rules": {q["rules"]},
    }
    nouns = (r"(?P<n>\d[\d,]*)\s+(?:distinct\s+|mapped\s+|non-empty\s+)*"
             r"(?P<k>findings|lines|rules|rule ids)")
    wrong = []
    for doc in _documented_command_files():
        for line in _io.open(doc, encoding="utf-8").read().splitlines():
            if "noisy" not in line.lower():
                continue
            for m in re.finditer(nouns, line):
                n = int(m.group("n").replace(",", ""))
                kind = "rules" if m.group("k").startswith("rule") else m.group("k")
                if n >= 100 and n not in expected[kind]:
                    wrong.append(f"{doc}: {m.group(0)!r}, expected one of "
                                 f"{sorted(expected[kind])}")
    assert not wrong, ("a noisy-control figure must be a quantity the tools produce, counted as "
                       f"the thing it is named as: {wrong}")


def test_a_retirement_must_be_signed_or_the_gate_refuses_it():
    """The escape hatch added on 2026-09-01 must not become the way inconvenient rows go quiet.

    A measurement may declare itself retired and `--verify-coverage` then reports it instead of
    failing on it. That is only defensible while a retirement is a statement somebody signed, so
    every one must name the date, what supersedes it, the reason, and where it was published.
    A retirement missing any of those is refused here rather than trusted.
    """
    import scanner_spec
    required = ("on", "by", "reason", "where_published")
    bad = []
    for name, spec in sorted(scanner_spec.load_all().items()):
        for m in spec.get("measurements", []):
            r = m.get("retired")
            if not r:
                continue
            missing = [k for k in required if not str(r.get(k, "")).strip()]
            if missing:
                bad.append(f"{name}/{m.get('corpus')}/{m.get('row')}: missing {missing}")
    assert not bad, f"a retirement must be signed: {bad}"


def test_a_retired_row_is_reported_and_not_counted_but_still_visible():
    """Both halves, because either one alone is a defect.

    Not counted: a row we have publicly retired must not hold the coverage gate red, or the badge
    stops meaning anything. Still visible: a retired row that vanished from the output would be a
    deletion dressed as a correction, which is the one thing this project does not do.
    """
    import io, run_all
    rows, failures = run_all.verify_coverage(echo=False)
    retired = [r for r in rows if r.get("retired")]
    assert retired, "the sol-audit v2 corpus-2 row is retired and should appear as such"
    for r in retired:
        tag = f"{r['corpus']} {r['scanner']}:"
        # The colon matters. Without it this prefix also matches `sol-audit-v3`,
        # and the first version of this test read a live row's gap as the
        # retired row holding the gate red.
        assert not any(f.startswith(tag) for f in failures),             f"{tag} is retired and must not hold the gate red"
    buf = io.StringIO()
    import contextlib
    with contextlib.redirect_stdout(buf):
        run_all.verify_coverage(echo=True)
    assert "RETIRED" in buf.getvalue(), "a retired row must stay visible in the output"


def test_no_document_carries_a_stray_control_character():
    """`python tools\\verify.py` was stored with a literal 0x0B where the backslash belonged.

    The README's only Windows code block therefore read `toolserify.py` and could not run, and no
    check saw it: the regex that looks for documented commands cannot match across a control
    character, so the line silently contributed nothing. A whole section of the front page argues
    that Windows is supported.
    """
    import io as _io
    allowed = {"\n", "\t"}
    bad = []
    for doc in _documented_command_files():
        s = _io.open(doc, encoding="utf-8", newline="").read()
        for i, ch in enumerate(s):
            if ch < " " and ch not in allowed and ch != "\r":
                bad.append(f"{doc}: {ch!r} at offset {i}")
    assert not bad, f"control characters in documents that tell a reader what to run: {bad}"


def test_the_real_vulnerability_denominator_is_reconciled_on_the_front_page():
    """Nine valid cases, eight built: the table reads out of eight. A reader who sees
    both numbers without explanation is right to distrust the whole page.

    Rewritten 2026-09-01, when eight cases were added and none of them was measured.
    The old derivation read the results denominator off the BUILT set, so adding a
    case would have silently restated every published zero as out of sixteen without
    a scanner having seen one of them. Built and measured are separate numbers now,
    and the results table is pinned to the measured one, because that is the only
    set a score can honestly be out of."""
    import io as _io, json, os
    cases = json.load(open("corpus2/manifest.json"))
    cases = cases["cases"] if isinstance(cases, dict) else cases
    valid = [c for c in cases if c.get("valid", True)]
    built = [c for c in valid if os.path.isdir(os.path.join("corpus2", c["name"]))]
    measured = [c for c in built if c.get("measured", True)]
    s = _io.open("README.md", encoding="utf-8").read()
    for n, phrase in ((len(valid), "valid cases"), (len(built), "built"),
                      (len(measured), "measured")):
        assert f"{n} {phrase}" in s, (
            f"the README must reconcile the three counts a reader needs: {len(valid)} "
            f"valid, {len(built)} built, {len(measured)} measured. It never says "
            f"'{n} {phrase}', so a reader cannot tell why a score reads out of "
            f"{len(measured)}")
    assert f"0 / {len(measured)}" in s, (
        "the README result table denominator must be the MEASURED corpus, not the "
        f"built one; expected '0 / {len(measured)}'")


def test_every_relative_link_in_every_document_resolves():
    """The README-only, .md-only check missed a link to a .log inside docs/results/.

    Moving files into docs/ and raw/ broke it silently: the link was relative to the
    document's old home at the repository root. Any relative target, any extension,
    from any document."""
    import io as _io, os, re
    broken = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", ".omc", "__pycache__", "node_modules")]
        for fn in files:
            if not fn.endswith(".md"):
                continue
            doc = os.path.join(root, fn)
            s = _io.open(doc, encoding="utf-8", errors="replace").read()
            for target in re.findall(r"\]\((?!https?:|mailto:|#)([^)\s#]+)", s):
                if not os.path.exists(os.path.join(root, target)):
                    broken.append(f"{doc} -> {target}")
    assert not broken, "documents link to missing files: " + repr(sorted(broken))
