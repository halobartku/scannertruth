# ------------------------------------------------------- acquisition filters
# A filter that matches the raw JSON blob once made an unrelated crate a Solana hit.

def test_acquisition_ignores_a_substring_match_in_unrelated_text():
    import corpus_ghsa
    fake = {"vulnerabilities": [{"package": {"name": "gix-packetline"}}],
            "summary": "reachable panic on empty side-band packet",
            "description": "nothing to do with blockchains"}
    assert corpus_ghsa.is_solana(fake) is None


def test_acquisition_matches_an_obvious_solana_crate():
    import corpus_ghsa
    real = {"vulnerabilities": [{"package": {"name": "anchor-lang"}}],
            "summary": "InterfaceAccount substitution", "description": ""}
    assert corpus_ghsa.is_solana(real)


def test_acquisition_matches_on_text_when_the_crate_name_is_neutral():
    import corpus_ghsa
    texty = {"vulnerabilities": [{"package": {"name": "obscure-crate"}}],
             "summary": "missing owner check in a Solana program", "description": ""}
    assert corpus_ghsa.is_solana(texty)


def test_acquisition_collapses_duplicate_commit_references():
    import corpus_ghsa
    adv = {"references": ["https://github.com/a/b/commit/deadbeef1234567",
                          "https://github.com/a/b/commit/deadbeef1234567",
                          "https://github.com/a/b/pull/42"]}
    commits, prs = corpus_ghsa.fix_refs(adv)
    assert len(commits) == 1 and prs[0]["pr"] == 42


# ------------------------------------------------------------ candidate triage
def test_rejected_candidates_carry_a_written_reason():
    """This asserted that the strings "REJECT" and "out of scope" appeared somewhere in the file,
    which one rejection among fifty acceptances satisfies. Now every rejection is checked."""
    import io as _io, os, re
    if not os.path.exists("docs/CANDIDATES-TRIAGE.md"):
        return
    lines = _io.open("docs/CANDIDATES-TRIAGE.md", encoding="utf-8").read().split("\n")
    rejects = [l for l in lines if "REJECT" in l]
    assert rejects, "the triage file records acceptances only, which hides the judgement calls"
    unexplained = []
    for line in rejects:
        # A rejection is a reason plus the words. Strip the marker and the table furniture, and
        # something has to be left.
        rest = re.sub(r"\*\*|`|\|", " ", line)
        rest = re.sub(r"REJECT[^A-Za-z]*", " ", rest)
        if len(rest.split()) < 6:
            unexplained.append(line.strip()[:70])
    assert not unexplained, f"rejections that say that, not why: {unexplained}"


def test_every_file_named_in_ci_exists():
    """CI caught a stale path that the suite did not, because the suite never invoked that CLI.
    Now it checks the workflow's own arguments, so the next move is caught before pushing."""
    import io as _io, os, re
    s = _io.open(".github/workflows/verify.yml", encoding="utf-8").read()
    refs = set(re.findall(r"--findings\s+([A-Za-z0-9_./-]+)", s))
    # `[A-Za-z0-9_-]+` matched neither a dot nor a slash, so every `python tools/<x>.py` step in
    # the workflow was silently skipped by the check written to verify them. Same blindness as the
    # documented-command check had.
    refs |= set(re.findall(r"python3?\s+([A-Za-z0-9_./-]+\.py)", s))
    missing = [r for r in sorted(refs) if not os.path.exists(r)]
    assert not missing, f"CI references files that do not exist: {missing}"


def test_readme_result_table_matches_the_clock():
    """If the front page and the measurement disagree, the front page is what people read."""
    import io as _io, sys, os
    sys.path.insert(0, "tools")
    import run_all
    s = _io.open("README.md", encoding="utf-8").read()
    got = {r["scanner"]: (r.get("nominal"), r.get("real"))
           for r in run_all.measure() if r.get("status") == "measured"}
    # Radar is the single most quoted figure in the project
    assert got.get("radar") == (11, 11), f"clock says radar is {got.get('radar')}"
    assert "11 / 11" in s or "11/11" in s, "README no longer shows the figure the clock produces"


def test_layout_block_lists_directories_that_exist():
    import io as _io, os, re
    s = _io.open("README.md", encoding="utf-8").read()
    block = s.split("## Repository layout")[1].split("```")[1]
    dirs = set(re.findall(r"^([a-z_0-9]+)/", block, re.M))
    missing = [d for d in sorted(dirs) if not os.path.isdir(d)]
    assert not missing, f"README describes directories that do not exist: {missing}"
