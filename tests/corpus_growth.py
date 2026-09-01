# ------------------------------------------------- corpus growth, 2026-09-01
# Eight cases were added on 2026-09-01. Adding a case changes the denominator of every
# figure computed over the corpus, and the front page has already been wrong twice for
# exactly that reason. These two derive the affected figures rather than trusting them.

def _corpus2_noisy_finding_count():
    """What control-noisy produces on corpus 2 today: every mapped rule id, on every
    non-empty line, of every .rs file, in both variants of every valid built case.

    Computed arithmetically rather than by materialising the findings, because the
    list is over a million entries and this runs on every suite.
    """
    import io as _io, json, os, sys
    sys.path.insert(0, "tools")
    import control_c2
    rules = len(control_c2.every_rule())
    cases = [c for c in json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
             if c.get("valid", True)]
    total = 0
    for c in cases:
        for variant in ("insecure", "secure"):
            d = os.path.join("corpus2", c["name"], variant, "src")
            if not os.path.isdir(d):
                continue
            for fn in sorted(os.listdir(d)):
                if not fn.endswith(".rs"):
                    continue
                with _io.open(os.path.join(d, fn), encoding="utf-8", errors="replace") as fh:
                    total += sum(1 for line in fh if line.strip()) * rules
    return total


def test_the_noisy_control_count_is_derived_from_the_corpus():
    """The calibration sentence quotes a finding count, and that count is a property of
    the corpus and the mapping set, both of which grow. It was 424,170 with seven
    mappings and eight cases; adding mappings moved it and adding cases moved it again.
    A quoted figure that nothing recomputes is the freshness defect this project keeps
    paying for, so every document that quotes one is checked against the corpus.

    The engineering logs are exempt, and only they. Their whole job is to record the
    value that turned out to be wrong, next to the date it was found; a log that could
    not quote a superseded number could not record the error at all."""
    import io as _io, os, re, sys
    sys.path.insert(0, "tools")
    import control_c1, control_c2
    expected = _corpus2_noisy_finding_count()
    # The teaching corpus figure is derived the same way and was a typed 931 until 2026-09-01,
    # when it turned out 931 was the count of flagged LINES and the control had never emitted a
    # finding any mapping could see (error 33). Both the line count and the finding count are
    # legitimate to quote, so both are derived here and neither is typed.
    c1_lines = sum(len(v) for v in control_c1.inventory_from_artefact().values())
    allowed = {expected, c1_lines, c1_lines * len(control_c2.every_rule())}
    wrong = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", ".omc", "__pycache__",
                                                "node_modules", "raw", "runs")]
        for fn in files:
            if not fn.endswith(".md") or fn.startswith("ENGINEERING-LOG-"):
                continue
            doc = os.path.join(root, fn)
            s = _io.open(doc, encoding="utf-8", errors="replace").read()
            for m in re.finditer(r"noisy", s, re.I):
                window = s[m.end():m.end() + 200]
                for n in re.findall(r"\b(\d{1,3}(?:,\d{3})+)\b", window):
                    if int(n.replace(",", "")) not in allowed:
                        wrong.append(f"{doc}: {n}")
    assert not wrong, (
        f"control-noisy produces {expected:,} findings on corpus 2 today, but these "
        f"documents still quote something else: {sorted(set(wrong))}. Regenerate with "
        "`python tools/control_c2.py` and quote what it prints.")


def test_the_coverage_matrix_is_derived_from_what_is_in_raw():
    """Coverage evidence existed for 3 of 12 measurements when it was last counted from outside,
    and the README admitted one gap of the nine. A prose list of gaps goes stale the moment a run
    happens; this one is recomputed from `raw/` and the failure message names what moved."""
    import io as _io, os, sys
    sys.path.insert(0, "tools")
    import coverage_matrix
    assert os.path.exists(coverage_matrix.DOC),         f"{coverage_matrix.DOC} is missing; run python tools/coverage_matrix.py --write"
    on_disk = _io.open(coverage_matrix.DOC, encoding="utf-8").read()
    assert coverage_matrix.render() == on_disk, (
        f"{coverage_matrix.DOC} no longer matches what is in raw/; run "
        "python tools/coverage_matrix.py --write")


def test_no_measurement_claims_a_run_log_it_does_not_have():
    """`coverage_evidence: run log` is the strongest claim this project makes about a number, so
    it must be false unless a machine-readable log with one entry per invocation is on disk."""
    import os, sys
    sys.path.insert(0, "tools")
    import run_all
    for row in run_all.measure_corpus2():
        if row.get("coverage_evidence") != "run log":
            continue
        src = row.get("source")
        assert src and os.path.exists(os.path.join("raw", src + ".log")), (
            f"{row['scanner']} claims coverage_evidence 'run log' and raw/{src}.log does not "
            "exist")


def test_class_balance_document_is_derived_from_the_manifest():
    """Class and repository concentration is the corpus's largest stated weakness, so
    the table that reports it must be recomputed rather than typed. Added 2026-09-01
    with the eight new cases, whose whole purpose was to move these two numbers."""
    import io as _io, os, sys
    sys.path.insert(0, "tools")
    import class_balance
    assert os.path.exists("docs/CLASS-BALANCE.md"), \
        "the class balance record is missing; run python tools/class_balance.py"
    on_disk = _io.open("docs/CLASS-BALANCE.md", encoding="utf-8").read()
    assert class_balance.render() == on_disk, (
        "docs/CLASS-BALANCE.md no longer matches the manifest it is derived from; "
        "run python tools/class_balance.py")


# -------------------------------- findings must land on files that exist, 2026-09-01, row 5

def _corpus2_findings():
    """Every corpus-2 findings file the clock scores, and the envelope it is read with.

    Taken from `run_all.SOURCES_CORPUS2` rather than copied. A typed copy of this list was wrong
    within an hour of being written: it named the sol-audit parser for a file kept in radar's own
    envelope, so the check ran over an empty parse and passed while seeing nothing."""
    import os, sys
    sys.path.insert(0, "tools")
    import run_all
    return [(name, os.path.join("raw", filename), kind)
            for name, (filename, kind) in sorted(run_all.SOURCES_CORPUS2.items())]


def test_no_verdict_rests_on_a_finding_about_a_file_that_is_not_in_the_corpus():
    """A findings file can outlive the corpus it was produced against, and two did.

    `raw/c2-radar-complete.json`, the file behind the published Radar corpus-2 row, was produced
    on 2026-08-31 against the corpus **before** it was rebuilt to pin one file per case. 161 of
    its 238 findings named files that no longer exist. `raw/c2-sol-audit.json` has the same
    problem on three cases, which the 2026-09-01 audit did not notice. Nothing said so, because
    `score_case` matched on the basename and ignored every directory above it.

    Deleting the stale artefacts is not the answer: this project keeps superseded runs on
    purpose. The property that has to hold is narrower and stronger than "every path resolves",
    and it is the one an outside reader cares about: **a finding about a file that is not in the
    corpus must never move a verdict.** Scored twice, once as recorded and once with the
    unresolvable paths removed, the two must agree for every case of every scanner.

    The stale counts themselves are reported by `tools/stale_findings.py` and recorded in
    `raw/stale-findings-2026-09-01.json`, so they stay visible rather than becoming invisible
    once the scorer stops being fooled by them."""
    import io as _io, json as _json, os, sys
    sys.path.insert(0, "tools")
    import score2
    cases = [c for c in _json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
             if c.get("valid", True)]
    moved, saw_stale = [], 0
    for scanner, path, kind in _corpus2_findings():
        assert os.path.exists(path), \
            f"{scanner}: {path} is missing, so the clock scores nothing for it"
        findings = score2.load_findings(kind, path)
        resolvable = {}
        for p, items in findings.items():
            norm = str(p).replace("\\", "/")
            if os.path.exists(norm):
                resolvable[p] = items
            else:
                saw_stale += len(items)
        import run_all as _ra
        mapping = _ra.load_mapping(scanner)["map"]
        for c in cases:
            d = os.path.join("corpus2", c["name"])
            if not os.path.isdir(d):
                continue
            a, _ = score2.score_case(d, c["class"], mapping, findings)
            b, _ = score2.score_case(d, c["class"], mapping, resolvable)
            if a != b:
                moved.append(f"{scanner}/{c['name']}: as recorded {a!r}, with the stale paths "
                             f"dropped {b!r}")
    assert not moved, (
        "verdicts that depend on findings about files that are not in the corpus:\n  "
        + "\n  ".join(moved)
        + "\nRe-run the scanner against the current corpus, or record the case as unknown.")
    assert saw_stale, (
        "no stale finding path was found anywhere, so this check just passed vacuously. If the "
        "artefacts were genuinely refreshed, delete this assertion and say so in the commit.")
