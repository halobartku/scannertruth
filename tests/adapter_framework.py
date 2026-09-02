import io
import json
import os
import tempfile


# ==================================================== the adapter framework, 2026-09-01
# `adapters/*.json` plus `tools/scanner_spec.py` replaced five hand-written per-case runners.
# Same selection rule as everything above: would a defect here change a published number?
#
# The one that matters most is `test_a_clean_zero_and_an_outage_can_never_carry_the_same_status`.
# Errors 20, 21, 35 and 36 are one defect wearing four hats: a harness that cannot tell "the tool
# ran this and found nothing" from "the tool never saw this". If that distinction collapses, every
# denominator in this repository is guesswork, so it is checked directly rather than left as a
# property of code somebody has to keep remembering.

# The literal tables `run_all.py` carried before the migration, copied here unchanged from commit
# 9b89b31. They are the published clock: which raw file scores which row, under which parser, and
# which mapping. Nothing derives them, on purpose. A golden record that regenerates itself proves
# nothing.
CLOCK_BEFORE_MIGRATION_C1 = {
    "radar": ("radar-full.json", "radar"),
    # added 2026-09-02: Radar at main after #35, a NEW row beside the old one (radar#32 promise)
    "radar-24c56f9": ("radar-24c56f9-c1.json", "radar"),
    "vaultlint": ("vaultlint.json", "vaultlint"),
    "sol-audit": ("sol-audit.json", "sol-audit"),
    "xray": ("xray-c1-raw.json", "xray"),
    "sol-audit-v3": ("c1-sol-audit-v3-strict.json", "sol-audit"),
    "sol-audit-v3-broad": ("c1-sol-audit-v3-broad.json", "sol-audit"),
    "sol-audit-v3-all": ("c1-sol-audit-v3-all.json", "sol-audit"),
    "solsec": ("c1-solsec-percase.json", "solsec"),
    "semgrep": ("semgrep-c1.json", "semgrep"),
    "semgrep-solana-standard": ("c1-semgrep-solana-standard.json", "semgrep"),
    "semgrep-solana-standard-wide": ("c1-semgrep-solana-standard.json", "semgrep"),
    # Added 2026-09-02, after the migration: the promised post-#36 re-measurement of radar.
    # Pre-existing rows above are still compared key by key, so a silent edit of any of
    # them keeps failing; this row is the deliberate addition, not a drift.
    "radar@2026-09-02": ("radar-c1-2026-09-02-post36.json", "radar"),
}
CLOCK_BEFORE_MIGRATION_C2 = {
    "radar": ("c2-radar-current.json", "radar"),
    "radar-24c56f9": ("c2-radar-24c56f9.json", "radar"),
    "vaultlint": ("c2-vaultlint-complete.json", "sol-audit"),
    "sol-audit": ("c2-sol-audit.json", "sol-audit"),
    "sol-audit-v3": ("c2-sol-audit-v3-strict.json", "sol-audit"),
    "sol-audit-v3-broad": ("c2-sol-audit-v3-broad.json", "sol-audit"),
    "sol-audit-v3-all": ("c2-sol-audit-v3-all.json", "sol-audit"),
    "solsec": ("c2-solsec-percase.json", "solsec"),
    "semgrep-solana-standard-c2": ("c2-semgrep-solana-standard.json", "semgrep"),
    "semgrep-solana-standard-c2-wide": ("c2-semgrep-solana-standard.json", "semgrep"),
}
CLOCK_BEFORE_MIGRATION_ALIAS = {
    "radar-24c56f9": "radar",  # added 2026-09-02: the new Radar row scores with the same pre-registered mapping
    "sol-audit-v3": "sol-audit",
    "sol-audit-v3-broad": "sol-audit",
    "sol-audit-v3-all": "sol-audit",
    "semgrep-solana-standard-c2": "semgrep-solana-standard-c2",
    # Same deliberate 2026-09-02 addition as the C1 literal above.
    "radar@2026-09-02": "radar",
}

# A scanner that does not exist, so the framework can be driven end to end on a laptop with no
# Docker. It reads its behaviour from a `mode` file in the case it is pointed at, which lets one
# run exercise a clean zero, a real finding, a silent exit and a crash in a single pass.
FIXTURE_SCANNER = "\n".join([
    "import json, os, sys",
    "target, out = sys.argv[1], sys.argv[2]",
    "mode = open(os.path.join(target, 'mode')).read().strip()",
    "if mode == 'silent':",
    "    sys.exit(0)          # exit 0, say nothing, write nothing: error 36's shape",
    "if mode == 'crash':",
    "    sys.stderr.write('fixture: exploded')",
    "    sys.exit(3)",
    "print('fixture scanned 1 files')",
    "hit = os.path.join(target, 'src', 'lib.rs').replace(chr(92), '/')",
    "findings = []",
    "if mode == 'finds':",
    "    findings = [{'rule_id': 'FIX-001', 'file': hit, 'line': 3}]",
    "if mode == 'flaky':",
    "    counter = os.path.join(os.path.dirname(out), 'flaky.count')",
    "    n = (int(open(counter).read()) if os.path.exists(counter) else 0) + 1",
    "    open(counter, 'w').write(str(n))",
    "    findings = [{'rule_id': 'FIX-001', 'file': hit, 'line': 2 + n}]",
    "json.dump({'findings': findings}, open(os.path.join(out, 'findings.json'), 'w'))",
    "",
])


def _fixture_world(tmp, modes):
    """A corpus of one-file cases, a fixture scanner, and a declaration that drives it.

    `engine: local` on purpose. This laptop has no Docker, and a framework whose only test path
    needs a VPS is a framework nobody will run a test on.
    """
    import scanner_spec
    script = os.path.join(tmp, "fixture_scanner.py")
    with io.open(script, "w", encoding="utf-8") as fh:
        fh.write(FIXTURE_SCANNER)
    leaves = []
    for name, mode in sorted(modes.items()):
        d = os.path.join(tmp, "corpus", name, "insecure")
        os.makedirs(os.path.join(d, "src"))
        with io.open(os.path.join(d, "mode"), "w", encoding="utf-8") as fh:
            fh.write(mode)
        with io.open(os.path.join(d, "src", "lib.rs"), "w", encoding="utf-8") as fh:
            fh.write("a\nb\nvulnerable\nd\n")
        leaves.append((name + "/insecure", d, "fixture/" + name + "/insecure"))
    spec = json.loads(json.dumps(scanner_spec._FIXTURE_SPEC))
    spec["run"]["command"] = ["python", script, "{mount}", "{out}"]
    spec["output"] = {"from": "file", "name": "findings.json", "format": "sol-audit"}
    return scanner_spec.load(spec), leaves


def test_every_adapter_declaration_in_the_repository_is_valid():
    """A declaration that does not load is a tool nobody can run and a clock row nobody can read."""
    import scanner_spec
    specs = scanner_spec.load_all()
    assert specs, "adapters/ holds no declarations"
    for name, spec in specs.items():
        assert spec["name"] == name
        assert spec["measurements"], f"{name} declares no measurement, so it feeds nothing"


def test_a_declaration_cannot_omit_how_the_tool_announces_that_it_read_the_code():
    """The guard that stops error 35 recurring, checked by trying to get past it.

    solsec was published as `0 / 6, 3 unavailable` with the denominator and the three unavailable
    cases both inferred from an empty findings file, and neither existed. A declaration that does
    not say how its tool announces coverage is refused rather than defaulted.
    """
    import scanner_spec
    blind = json.loads(json.dumps(scanner_spec._FIXTURE_SPEC))
    del blind["coverage"]["evidence"]
    try:
        scanner_spec.load(blind)
        raise AssertionError("a declaration with no coverage evidence was accepted")
    except ValueError as exc:
        assert "coverage.evidence is missing" in str(exc), exc

    vague = json.loads(json.dumps(scanner_spec._FIXTURE_SPEC))
    vague["coverage"]["evidence"] = {"absent": True}
    try:
        scanner_spec.load(vague)
        raise AssertionError("an absent-evidence declaration with no reason was accepted")
    except ValueError as exc:
        assert "reason" in str(exc), exc


def test_a_clean_zero_and_an_outage_can_never_carry_the_same_status():
    """THE property. If this stops holding, every denominator in the repository is guesswork.

    Four observations that a naive harness collapses into "no findings":

      the tool said it read the files and reported nothing   ok, and that zero is real
      the tool exited 0 having said nothing                  unavailable, error 36's shape
      the tool crashed                                       unavailable
      the tool produced output nothing could parse           unavailable

    The first must be distinguishable from the other three, and it must be the only one that can
    contribute a zero to a denominator.
    """
    import scanner_spec
    spec = scanner_spec.load(scanner_spec._FIXTURE_SPEC)
    said_it_read = scanner_spec.classify(spec, 0, "fixture scanned 3 files\n", [])
    silent = scanner_spec.classify(spec, 0, "", [])
    crashed = scanner_spec.classify(spec, 3, "fixture scanned 3 files\n", [])
    unreadable = scanner_spec.classify(spec, 0, "fixture scanned 3 files\n", None)

    assert said_it_read[0] == "ok", said_it_read
    for name, got in (("said nothing", silent), ("crashed", crashed),
                      ("was unreadable", unreadable)):
        assert got[0] != "ok", (
            f"a run that {name} was classified `ok`, which turns it into a zero somebody will "
            f"publish: {got}")
        assert got[0] == "unavailable", got
        assert got[2], f"a run that {name} was recorded unavailable with no reason attached"
    assert said_it_read[0] != silent[0], (
        "a clean zero and an outage now carry the same status. Error 35 published an outage that "
        "never happened; error 36 published a clean zero as an outage. This check exists so the "
        "distinction is not a convention somebody has to remember.")


def test_a_tool_that_prints_no_coverage_line_can_never_produce_a_zero():
    """The escape hatch must not become a back door.

    A declaration may admit that its tool says nothing about what it read. Its runs are then
    `unknown`, which is the honest verdict, and `unknown` is neither a zero nor an outage. What it
    must never become is `ok`.
    """
    import scanner_spec
    mute = json.loads(json.dumps(scanner_spec._FIXTURE_SPEC))
    mute["coverage"]["evidence"] = {"absent": True, "reason": "prints no file count"}
    spec = scanner_spec.load(mute)
    for output in ("", "anything at all", "0 files scanned"):
        status, _seen, why = scanner_spec.classify(spec, 0, output, [])
        assert status == "unknown", (
            f"a tool with no coverage line returned {status!r} on output {output!r}; a "
            "declaration that admits it cannot prove coverage must never produce a scoreable zero")
        assert why
    # And an exit code outside the declared set is still an outage, not an unknown: the two
    # reasons a run cannot be counted are recorded as the different things they are.
    assert scanner_spec.classify(spec, 3, "anything at all", [])[0] == "unavailable"


def test_the_clock_tables_derived_from_the_declarations_match_the_committed_ones():
    """The migration proof. Every published row must still name the same file, parser and mapping.

    `run_all.py` carried these as three literals until 2026-09-01; they come from `adapters/*.json`
    now. A declaration edit that moves a row moves a published number, so the pre-migration tables
    are pinned here by hand and compared key by key.
    """
    import run_all
    for label, got, want in (
            ("corpus 1", run_all.SOURCES, CLOCK_BEFORE_MIGRATION_C1),
            ("corpus 2", run_all.SOURCES_CORPUS2, CLOCK_BEFORE_MIGRATION_C2)):
        assert set(got) == set(want), (
            f"{label} rows changed: only in the declarations {sorted(set(got) - set(want))}, "
            f"only in the committed clock {sorted(set(want) - set(got))}")
        for row in sorted(want):
            assert got[row] == want[row], (
                f"{label} row {row!r} now reads {got[row]}, was {want[row]}. That is a published "
                "number moving under a refactor.")
    # MAPPING_ALIAS is compared as the question it answers, which mapping scores which row,
    # because the committed literal carried one entry that mapped a row to itself.
    for row in sorted(set(CLOCK_BEFORE_MIGRATION_C1) | set(CLOCK_BEFORE_MIGRATION_C2)):
        was = CLOCK_BEFORE_MIGRATION_ALIAS.get(row, row)
        now = run_all.MAPPING_ALIAS.get(row, row)
        assert was == now, f"row {row!r} is now scored with mappings/{now}.json, was {was}"


def test_every_declaration_can_carry_a_detection_through_its_own_parser():
    """A parser that silently returns nothing looks exactly like a tool that found nothing.

    This happened. On 2026-09-01 an external review disabled the sol-audit branch of
    `load_findings` and all 94 checks stayed green while every corpus-2 verdict silently became
    `missed`. Each declaration therefore carries a sample of its tool's own output holding one real
    finding, and it is driven end to end: the parser, the stored envelope, the reader the clock
    uses, the scorer. Then the same finding is planted on the fixed variant and must stop being a
    detection.
    """
    import scanner_spec
    for name, spec in sorted(scanner_spec.load_all().items()):
        got = scanner_spec.positive_control(spec)
        assert got["detected"] and got["silent_on_the_fix"], (name, got)
        assert got["corpus1_envelopes"] or got["corpus2_envelopes"], (
            f"{name}: the control crossed no reader at all")


def test_every_envelope_a_declaration_names_is_one_the_scorer_for_that_corpus_can_read():
    """The two corpora are read by different code, and a row can be moved between them.

    Corpus 1 goes through `run_all.extract`, corpus 2 through `score2.load_findings`. `xray` is a
    kind one of them has and the other does not, which is exactly the gap that only shows up when
    somebody moves a row.
    """
    import run_all, score2, scanner_spec
    for name, spec in sorted(scanner_spec.load_all().items()):
        for m in spec["measurements"]:
            env = m.get("envelope", spec["envelope"])
            if m["corpus"] == "corpus1":
                run_all.extract(env, [] if env in ("radar", "xray") else {})
            else:
                with tempfile.TemporaryDirectory() as t:
                    dest = os.path.join(t, "e.json")
                    with io.open(dest, "w", encoding="utf-8") as fh:
                        json.dump(scanner_spec.WRITERS[env]([]), fh)
                    score2.load_findings(env, dest)


def test_the_framework_writes_an_artefact_and_a_log_line_for_every_invocation():
    """Including the ones that failed. The run that failed is the one somebody will want to read.

    Everything that survived the 2026-08-31 audit had an artefact per run; everything that
    collapsed had been inferred from a summary.
    """
    import scanner_spec
    with tempfile.TemporaryDirectory() as tmp:
        spec, leaves = _fixture_world(tmp, {"a-finds": "finds", "b-empty": "empty",
                                            "c-silent": "silent", "d-crash": "crash"})
        out = os.path.join(tmp, "findings.json")
        log, _findings, _det = scanner_spec.run_measurement(
            spec, leaves, out, os.path.join(tmp, "runs"), echo=False)
        assert len(log) == len(leaves), f"{len(log)} log entries for {len(leaves)} invocations"
        for entry in log:
            for field in ("leaf", "status", "exit_code", "wall_seconds", "command", "artefact"):
                assert field in entry, f"{entry.get('leaf')} has no {field}"
            assert entry["command"], "the exact command is not in the log"
            assert os.path.exists(entry["artefact"]) or os.path.exists(
                os.path.join(scanner_spec.ROOT, entry["artefact"])), \
                f"no artefact on disk for {entry['leaf']}"
        for suffix in ("", ".log", ".determinism.json"):
            assert os.path.exists(out + suffix), f"{out + suffix} was not written"


def test_a_run_that_read_nothing_contributes_no_zero_to_anybodys_denominator():
    """End to end, through real subprocesses, on the property the whole framework exists for."""
    import scanner_spec
    with tempfile.TemporaryDirectory() as tmp:
        spec, leaves = _fixture_world(tmp, {"a-finds": "finds", "b-empty": "empty",
                                            "c-silent": "silent", "d-crash": "crash"})
        log, findings, _det = scanner_spec.run_measurement(
            spec, leaves, os.path.join(tmp, "f.json"), os.path.join(tmp, "runs"), echo=False)
        by = {e["leaf"]: e for e in log}
        assert by["a-finds/insecure"]["status"] == "ok", by["a-finds/insecure"]
        assert by["a-finds/insecure"]["findings"] == 1
        assert by["b-empty/insecure"]["status"] == "ok", (
            "a tool that said it read the files and reported nothing is a CLEAN ZERO. Calling it "
            "unavailable is error 36, which cost a published correction.")
        assert by["b-empty/insecure"]["findings"] == 0
        for leaf in ("c-silent/insecure", "d-crash/insecure"):
            assert by[leaf]["status"] == "unavailable", by[leaf]
            assert by[leaf]["findings"] is None, (
                f"{leaf} could not run and yet carries a findings count, which is how an outage "
                "becomes a zero")
        assert len(findings) == 1, findings


def test_a_scanner_that_disagrees_with_itself_is_reported_not_averaged():
    """A tool whose answer changes between runs is a sample, not a value, and is named as one."""
    import scanner_spec
    with tempfile.TemporaryDirectory() as tmp:
        spec, leaves = _fixture_world(tmp, {"steady": "finds", "unsteady": "flaky"})
        out = os.path.join(tmp, "f.json")
        scanner_spec.run_measurement(spec, leaves, out, os.path.join(tmp, "runs"),
                                     repeat=2, echo=False)
        with io.open(out + ".determinism.json", encoding="utf-8") as fh:
            det = json.load(fh)
        assert det["verdict"] == "non-deterministic", det
        assert any(d["leaf"] == "unsteady/insecure" for d in det["differing"]), det
        assert not any(d["leaf"] == "steady/insecure" for d in det["differing"]), det
        assert os.path.exists(out) and os.path.exists(out.replace(".json", ".run2.json")), \
            "both passes must stay on disk; a merged pair is a run that never happened"


def test_a_single_pass_cannot_claim_a_determinism_verdict():
    import scanner_spec
    with tempfile.TemporaryDirectory() as tmp:
        spec, leaves = _fixture_world(tmp, {"only": "finds"})
        out = os.path.join(tmp, "f.json")
        scanner_spec.run_measurement(spec, leaves, out, os.path.join(tmp, "runs"), echo=False)
        with io.open(out + ".determinism.json", encoding="utf-8") as fh:
            assert json.load(fh)["verdict"] == "not-checked"


def test_the_corpus_case_list_is_read_from_the_manifest_and_never_assumed():
    """It was 9 cases, then 16, then 17, and it changed under a measurement mid-run once already.

    B3's sweep started against 9 built cases and finished against 17 because another worker
    expanded the corpus while it ran. A framework that wrote the number down would have published
    the drift as a result.
    """
    import scanner_spec
    cases = json.load(io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    built = {c["name"] for c in cases
             if c.get("valid", True) and os.path.isdir(os.path.join("corpus2", c["name"]))}
    leaves = scanner_spec.corpus_leaves("corpus2")
    names = {leaf.split("/")[0] for leaf, _d, _p in leaves}
    assert names == built, (
        "the framework's case list and the manifest disagree: " + str(names ^ built))
    assert len(leaves) >= len(built), "at least one invocation per built case"


def test_verify_coverage_fails_loudly_when_a_row_has_no_run_log():
    """Milestone 1's acceptance check has to be able to fail, and to say which row failed."""
    import run_all
    with tempfile.TemporaryDirectory() as tmp:
        with io.open(os.path.join(tmp, "with-log.json"), "w", encoding="utf-8") as fh:
            json.dump({"findings": []}, fh)
        with io.open(os.path.join(tmp, "with-log.json.log"), "w", encoding="utf-8") as fh:
            json.dump([{"leaf": "x/insecure", "status": "ok"}], fh)
        with io.open(os.path.join(tmp, "no-log.json"), "w", encoding="utf-8") as fh:
            json.dump({"findings": []}, fh)
        saved = (run_all.SOURCES, run_all.SOURCES_CORPUS2)
        try:
            run_all.SOURCES = {"has-evidence": ("with-log.json", "sol-audit"),
                               "no-evidence": ("no-log.json", "sol-audit")}
            run_all.SOURCES_CORPUS2 = {}
            rows, failures = run_all.verify_coverage(raw_dir=tmp, echo=False)
        finally:
            run_all.SOURCES, run_all.SOURCES_CORPUS2 = saved
    graded = {r["scanner"]: r["coverage_evidence"] for r in rows}
    assert graded == {"has-evidence": "run log", "no-evidence": "none"}, graded
    assert len(failures) == 1 and "no-evidence" in failures[0], failures
    assert "coverage_evidence: none" in failures[0], failures[0]


def test_verify_coverage_passes_only_when_every_row_can_show_what_it_analysed():
    """The other half: it must be able to say yes, or it is a check that always fails."""
    import run_all
    with tempfile.TemporaryDirectory() as tmp:
        with io.open(os.path.join(tmp, "a.json"), "w", encoding="utf-8") as fh:
            json.dump({"findings": []}, fh)
        with io.open(os.path.join(tmp, "a.json.log"), "w", encoding="utf-8") as fh:
            json.dump([{"leaf": "x/insecure", "status": "ok"}], fh)
        saved = (run_all.SOURCES, run_all.SOURCES_CORPUS2)
        try:
            run_all.SOURCES = {"a": ("a.json", "sol-audit")}
            run_all.SOURCES_CORPUS2 = {}
            rows, failures = run_all.verify_coverage(raw_dir=tmp, echo=False)
        finally:
            run_all.SOURCES, run_all.SOURCES_CORPUS2 = saved
    assert not failures, failures
    assert rows[0]["invocations"] == 1 and rows[0]["ok"] == 1


def test_a_case_that_could_not_run_is_not_a_coverage_failure_but_one_nobody_ran_is():
    """Could not run is a published outcome. Nobody looked is a gap. They are not the same.

    Reading them as the same is what made the 2026-08-31 harness record cases radar had in fact
    analysed as outages.
    """
    import run_all
    row = {"corpus": "corpus2", "scanner": "t", "raw": "raw/t.json",
           "coverage_evidence": "run log", "invocations": 2, "ok": 1, "not_ok": 1}
    saved = run_all.coverage_rows
    try:
        run_all.coverage_rows = lambda *a, **k: [dict(row, unresolved={"unavailable": 3})]
        _rows, failures = run_all.verify_coverage(echo=False)
        assert not failures, \
            f"a case that could not run, published with its reason, is not a gap: {failures}"
        run_all.coverage_rows = lambda *a, **k: [dict(row, unresolved={"not-run": 3})]
        _rows, failures = run_all.verify_coverage(echo=False)
        assert len(failures) == 1 and "not-run" in failures[0], failures
        run_all.coverage_rows = lambda *a, **k: [dict(row, unresolved={"unknown": 3})]
        _rows, failures = run_all.verify_coverage(echo=False)
        assert len(failures) == 1 and "unknown" in failures[0], failures
    finally:
        run_all.coverage_rows = saved


def test_no_declaration_claims_an_invocation_it_cannot_show():
    """`invocation_evidence` must point at something in the repository, not describe a memory.

    Three declarations say `engine: unrecorded` because nobody wrote their command down. That is
    the honest state and it is allowed. What is not allowed is a declaration that states a command
    and cites nothing, because a command typed from memory is the same class of claim as a number
    typed from memory.
    """
    import re as _re
    import scanner_spec
    missing = []
    for name, spec in sorted(scanner_spec.load_all().items()):
        if spec["run"]["engine"] == "unrecorded":
            assert spec["run"].get("reason"), f"{name} is unrecorded with no reason"
            continue
        evidence = spec["run"]["invocation_evidence"]
        cited = _re.findall(r"\b(?:raw|tools|mappings|docs|corpus2)/[\w./-]*[\w/]", evidence)
        assert cited, f"{name}: invocation_evidence cites no file in this repository"
        for path in cited:
            if not os.path.exists(path):
                missing.append(f"{name}: {path}")
    assert not missing, f"invocation evidence naming files that do not exist: {missing}"


def test_the_frameworks_parser_reproduces_a_committed_findings_file_from_the_raw_runs():
    """The migration proof for the half a golden table cannot reach: the parser itself.

    `raw/c2-sol-azy.json` and `raw/c2ext-sol-azy.json` were produced on 2026-09-01 by a runner
    written for that one sweep and kept in a scratch directory. The framework's `text-regex`
    parser, driven from `adapters/sol-azy.json` alone, reads the same committed per-run artefacts.
    If the two disagree, the declaration is not describing the tool that produced the published
    file, and the next run under it would quietly measure something else.

    sol-azy is the tool this can be checked on, because it is the only one whose per-invocation
    raw output is committed in the tool's own words rather than already normalised.
    """
    import scanner_spec
    spec = scanner_spec.load("adapters/sol-azy.json")
    patterns = spec["output"]["patterns"]
    checked = 0
    for runs, committed in (("raw/solazy-2026-09-01/c2", "raw/c2-sol-azy.json"),
                            ("raw/solazy-2026-09-01/c2-extended", "raw/c2ext-sol-azy.json")):
        if not os.path.isdir(runs) or not os.path.exists(committed):
            continue
        got = []
        for fn in sorted(os.listdir(runs)):
            leaf = fn[:-4]
            if not fn.endswith(".txt") or leaf.endswith("-run2") or "__" not in leaf:
                continue
            case, variant = leaf.split("__")[0], leaf.split("__")[1]
            with io.open(os.path.join(runs, fn), encoding="utf-8", errors="replace") as fh:
                for f in scanner_spec.parse_text_regex(fh.read(), patterns):
                    rel = f["file"][len("/work/"):] if f["file"].startswith("/work/") \
                        else f["file"]
                    got.append((f["rule_id"], f"corpus2/{case}/{variant}/{rel}",
                                f["line"], f["col"]))
        with io.open(committed, encoding="utf-8") as fh:
            want = [(x["rule_id"], x["file"], x["line"], x.get("col", 0))
                    for x in json.load(fh)["findings"]]
        assert sorted(got) == sorted(want), (
            f"the declaration's parser reads {len(got)} findings out of {runs} where the "
            f"committed {committed} has {len(want)}; "
            f"only in the parse: {sorted(set(got) - set(want))[:3]}, "
            f"only in the file: {sorted(set(want) - set(got))[:3]}")
        checked += 1
    assert checked, "neither sol-azy run directory is present, so this proved nothing"
