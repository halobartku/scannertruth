from ._core import _publication_documents


# ------------------------------------------- claims banned everywhere, not on the front page
# Three checks used to ban an overclaim in README.md and nowhere else, so each of them stood
# corrected on the front page and uncorrected one link away: "the packaging objection is now
# retired" in RESULTS-all, "927 `.rs` files" in RESULTS-all, RESULTS-realcrates and ROADMAP,
# "ten production vulnerabilities" in RESULTS-all and PROTOCOL, "the corpus was last updated in
# 2024" in PROTOCOL four sections after the same document pins it to 2022-07-16. Error 22 in the
# engineering log is this pattern and was diagnosed as a README problem rather than a scoping
# problem. A claim is banned in the repository or it is not banned.


def test_no_document_carries_a_superseded_claim():
    """Each entry here was true once and was corrected somewhere. This is where it stays corrected."""
    import io as _io, re as _re
    banned = {
        "One scanner has been measured": "six are measured",
        "corpus last updated in 2024": "the teaching corpus is pinned at 2022-07-16",
        "last updated in 2024": "the teaching corpus is pinned at 2022-07-16",
        "packaging objection is now retired": "six pairs and two scanners test it, they do not retire it",
        "retires the packaging objection": "six pairs and two scanners test it, they do not retire it",
        "retired the packaging objection": "six pairs and two scanners test it, they do not retire it",
        "ten production vulnerabilities": "the corpus-2 denominator is read from the manifest, never typed",
        "Ten real cases": "the corpus-2 denominator is read from the manifest, never typed",
    }
    hits = []
    for doc in _publication_documents():
        # ~~struck through~~ is this project's marker for wording it has publicly retracted, kept
        # beside the correction on purpose. Banning what a retraction quotes would force the
        # retraction to be deleted, which is the opposite of the rule.
        s = _re.sub(r"~~.*?~~", "", _io.open(doc, encoding="utf-8").read(), flags=_re.S)
        for phrase, why in banned.items():
            if phrase in s:
                hits.append(f"{doc}: {phrase!r} ({why})")
    assert not hits, "superseded claims still published:\n  " + "\n  ".join(hits)


def test_no_document_quotes_an_uncheckable_rs_file_count():
    """927 `.rs` files was error 23: the real crates are built on demand and never committed, so
    the figure is not checkable from the repository by anyone. Withdrawn from the README and left
    standing in three other documents, which is how a retraction becomes decorative."""
    import io as _io, json as _json, os, re
    on_disk = sum(len([f for f in fs if f.endswith(".rs")]) for _, _, fs in os.walk("corpus2"))
    legal = {on_disk}
    # The real crates are still built on demand and still not committed, so the figure error 23
    # withdrew is still unquotable AS SUCH. What changed on 2026-09-01 is that the build now
    # commits its own inventory, so ONE real-crate total is recomputable from the repository:
    # the .rs files in the crates the manifest marks valid. That number is admitted here by
    # being recomputed, not by being allowed - quote any other and this still fails.
    inv = "raw/rc-crates-built-2026-09-01.json"
    if os.path.exists(inv):
        valid = {c["name"] for c in
                 _json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
                 if c.get("valid", True)}
        legal.add(sum(r.get("rs_files_in_crate", 0) for r in
                      _json.load(_io.open(inv, encoding="utf-8"))
                      if r.get("status") == "built" and r["name"] in valid))
    bad = []
    for doc in _publication_documents():
        s = _io.open(doc, encoding="utf-8").read()
        for n in re.findall(r"(\d[\d,]{2,})\s*`?\.rs`?\s*files", s):
            if int(n.replace(",", "")) not in legal:
                bad.append(f"{doc}: {n}")
    assert not bad, (
        f"the checkable .rs counts are {sorted(legal)}; these documents quote a count nobody "
        f"can check: {bad}. Cite the per-case table in docs/results/RESULTS-realcrates.md instead.")


def test_readme_does_not_overstate_the_real_crates_result():
    """A one-line summary on the front page must not drop the results page's denominators.

    It used to require the words "six pairs" and "two scanners", which were the denominators
    until 2026-09-01, when four more scanners were run over all seventeen valid cases in both
    packagings. Requiring the old wording would have forced the front page to keep understating
    the run; requiring nothing would have let it overstate. So it requires today's denominators:
    how many scanners were compared across packagings, and the weak row that remains."""
    import io as _io
    s = _io.open("README.md", encoding="utf-8").read()
    i = s.find("**Real crates**")
    assert i > 0, "the real-crates bullet is gone; update or remove this test"
    bullet = s[i:i + 700]
    assert "four scanners" in bullet.lower(),         "the real-crates claim must say how many scanners were actually run on them"
    assert "radar" in bullet.lower(),         "the real-crates claim must keep naming the tool whose real-crate coverage is partial"
    for banned in ("retires the packaging objection", "retired the packaging objection"):
        assert banned not in bullet.lower(),             f"unqualified claim {banned!r}: six pairs tests an objection, it does not retire it"


def test_skills_referenced_by_agents_md_exist():
    import io as _io, os, re
    s = _io.open("AGENTS.md", encoding="utf-8").read()
    links = set(re.findall(r"\]\((skills/[A-Za-z0-9_./-]+)\)", s))
    missing = [x for x in sorted(links) if not os.path.exists(x)]
    assert not missing, f"AGENTS.md references missing skills: {missing}"


def test_every_skill_names_itself_correctly_and_says_when_to_use_it():
    """Frontmatter presence was all this checked, so a skill named after the wrong directory or
    carrying a one-word description passed. A skill is only reachable through its description."""
    import io as _io, os, re
    for d in sorted(os.listdir("skills")):
        p = os.path.join("skills", d, "SKILL.md")
        assert os.path.exists(p), f"{d} has no SKILL.md"
        text = _io.open(p, encoding="utf-8").read()
        assert text.startswith("---"), f"{d}: no frontmatter"
        front = text.split("---", 2)[1]
        name = re.search(r"^name:\s*(.+)$", front, re.M)
        desc = re.search(r"^description:\s*(.+)$", front, re.M)
        assert name and desc, f"{d}: incomplete frontmatter"
        assert name.group(1).strip() == d, \
            f"{d}: frontmatter name is {name.group(1).strip()!r}; an agent looks it up by directory"
        assert len(desc.group(1).split()) >= 12, \
            f"{d}: the description is what decides whether this skill is ever used, and it is "
        assert "use when" in desc.group(1).lower() or "when " in desc.group(1).lower(), \
            f"{d}: the description must say when to use the skill, not only what it is"
