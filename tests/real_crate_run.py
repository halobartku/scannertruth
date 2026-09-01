# ------------------------------------------------- the real-crate run, 2026-09-01
# Four of the eight measurements had never been run against the real crates, so the packaging
# objection was tested for two tools and retired for none. These checks stand behind the page
# that closed that gap, and the first three exist because a scorer whose only observed output is
# zero is not evidence about anybody's tool.

RC_DOC = "docs/results/RESULTS-realcrates.md"
RC_RUN_ROWS = [
    ("raw/rc-sol-audit-v3-strict.json.log", "sol-audit 3.0, strict"),
    ("raw/rc-sol-audit-v3-broad.json.log", "sol-audit 3.0, broad"),
    ("raw/rc-sol-audit-v3-all.json.log", "sol-audit 3.0, all"),
    ("raw/rc-semgrep-solana-standard.json.log", "semgrep + SOL-0XX pack"),
    ("raw/rc-solsec.json.log", "solsec 0.2.1"),
    ("raw/rc-xray.json.log", "X-Ray v0.0.6"),
    ("raw/rc-radar.json.log", "Radar (re-run)"),
]
RC_SCORE_ROWS = [
    ("raw/rc-score-sol-audit-strict.json", "sol-audit 3.0, strict / broad / all"),
    ("raw/rc-score-sol-audit-broad.json", "sol-audit 3.0, strict / broad / all"),
    ("raw/rc-score-sol-audit-all.json", "sol-audit 3.0, strict / broad / all"),
    ("raw/rc-score-semgrep-solana-standard-c2.json", "semgrep + SOL-0XX, narrow reading"),
    ("raw/rc-score-semgrep-solana-standard-c2-wide.json", "semgrep + SOL-0XX, wide reading"),
    ("raw/rc-score-solsec.json", "solsec 0.2.1"),
    ("raw/rc-score-xray.json", "X-Ray, pre-registered map"),
    ("raw/rc-score-xray-corrected.json", "X-Ray, corrected map"),
    ("raw/rc-score-radar.json", "Radar (re-run)"),
]


def _rc_module(name):
    import importlib, os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    return importlib.import_module(name)


def _md_rows(text):
    """Every markdown table row as a list of plain cells, bold and backticks stripped."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|- :"):
            continue
        cells = []
        for c in line.strip("|").split("|"):
            c = c.strip()
            while c.startswith("*") or c.startswith("`"):
                c = c[1:]
            while c.endswith("*") or c.endswith("`"):
                c = c[:-1]
            cells.append(c.strip())
        rows.append(cells)
    return rows


def test_rc_run_classifies_the_solsec_exit_gate_as_a_result():
    _rc_module("rc_run").demo()


def test_rc_score_positive_control_in_the_real_crate_layout():
    _rc_module("rc_score").demo()


def test_rc_compare_can_see_a_difference_between_packagings():
    _rc_module("rc_compare").demo()


def test_every_real_crate_run_covers_every_case_and_variant():
    """One invocation per case per variant, and the leaves are the crates that were built."""
    import io as _io, json as _json, os as _os
    built = _json.load(_io.open("raw/rc-crates-built-2026-09-01.json", encoding="utf-8"))
    want = set()
    for r in built:
        if r.get("status") == "built":
            want.add(r["name"] + "/insecure")
            want.add(r["name"] + "/secure")
    assert want, "the crate inventory is empty, so this check proves nothing"
    checked = 0
    for log_path, _label in RC_RUN_ROWS:
        assert _os.path.exists(log_path), log_path + " is missing"
        entries = _json.load(_io.open(log_path, encoding="utf-8"))
        got = [e["leaf"] for e in entries]
        assert len(got) == len(set(got)), log_path + " logs a leaf twice"
        assert set(got) == want, (
            "%s covers %d leaves, the corpus has %d; missing %s, extra %s"
            % (log_path, len(got), len(want), sorted(want - set(got))[:3],
               sorted(set(got) - want)[:3]))
        checked += 1
    assert checked == len(RC_RUN_ROWS)


def test_a_real_crate_the_tool_could_not_finish_is_never_scored_as_a_zero():
    """The scored file must say `unavailable` for exactly the cases its log could not finish."""
    import io as _io, json as _json, os as _os
    manifest = _json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    valid = set(c["name"] for c in manifest if c.get("valid", True))
    checked = 0
    for score_path, _label in RC_SCORE_ROWS:
        assert _os.path.exists(score_path), score_path + " is missing"
        scored = _json.load(_io.open(score_path, encoding="utf-8"))
        log = _os.path.join("raw", _os.path.basename(scored["log"]))
        assert _os.path.exists(log), score_path + " names a log that is not in raw/: " + log
        entries = _json.load(_io.open(log, encoding="utf-8"))
        blocked = set(e["leaf"].split("/")[0] for e in entries
                      if e.get("status") != "ok") & valid
        said = set(r["case"] for r in scored["cases"] if r["verdict"] == "unavailable")
        assert said == blocked, (
            "%s: the run log could not finish %s but the scored file marks %s unavailable; "
            "anything in the first set and not the second is an outage published as a zero"
            % (score_path, sorted(blocked), sorted(said)))
        checked += 1
    assert checked == len(RC_SCORE_ROWS)


def test_the_real_crate_run_table_matches_the_logs_it_was_derived_from():
    import io as _io, json as _json
    doc = _io.open(RC_DOC, encoding="utf-8").read()
    rows = _md_rows(doc)
    for log_path, label in RC_RUN_ROWS:
        entries = _json.load(_io.open(log_path, encoding="utf-8"))
        ok = [e for e in entries if e.get("status") == "ok"]
        want = [label, str(len(entries)), str(len(ok)), str(len(entries) - len(ok)),
                str(sum(e.get("findings", 0) for e in ok))]
        got = [r for r in rows if r and r[0] == label]
        assert got, RC_DOC + " has no run row for " + repr(label)
        assert any(r[:5] == want for r in got), (
            "%s run row for %r is %s, the log says %s" % (RC_DOC, label, got[0][:5], want))


def test_the_real_crate_score_table_matches_the_scored_files():
    import io as _io, json as _json
    doc = _io.open(RC_DOC, encoding="utf-8").read()
    rows = _md_rows(doc)
    manifest = _json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    valid = sum(1 for c in manifest if c.get("valid", True))
    for score_path, label in RC_SCORE_ROWS:
        t = _json.load(_io.open(score_path, encoding="utf-8"))["tally"]
        # A case with no mapped rule is not scoreable, and neither is one the tool could not
        # finish. Subtracting only the first would publish a denominator that counts outages.
        scoreable = valid - t.get("no-rule", 0) - t.get("unavailable", 0)
        want = [label, str(t.get("detected", 0)), str(t.get("unlocated", 0)),
                str(t.get("missed", 0)), str(t.get("no-rule", 0)),
                str(t.get("unavailable", 0)), "%d / %d" % (scoreable, valid)]
        got = [r for r in rows if r and r[0] == label]
        assert got, RC_DOC + " has no score row for " + repr(label)
        assert any(r[:7] == want for r in got), (
            "%s score row for %r is %s, %s says %s"
            % (RC_DOC, label, got[0][:7], score_path, want))


def test_the_packaging_comparison_headline_is_recomputed_not_typed():
    import io as _io, os as _os
    rc_compare = _rc_module("rc_compare")
    doc = _io.open(RC_DOC, encoding="utf-8").read()
    compared = differ = blocked = 0
    for label, rc_path, mapping_name, map_key, c2, kind in rc_compare.PAIRS:
        if not (_os.path.exists(rc_path) and _os.path.exists(c2)):
            continue
        r, d = rc_compare.compare(label, rc_path, mapping_name, map_key, c2, kind)
        compared += sum(1 for x in r if x[3] != "no comparison")
        blocked += sum(1 for x in r if x[3] == "no comparison")
        differ += d
    assert compared, "the comparison compared nothing, so its zero means nothing"
    assert ("%d verdicts compared" % compared) in doc, (
        "%s does not say '%d verdicts compared'" % (RC_DOC, compared))
    assert ("%d could not be compared" % blocked) in doc, (
        "%s does not say '%d could not be compared'" % (RC_DOC, blocked))
    if differ == 0:
        assert "Zero differ" in doc, RC_DOC + " should say 'Zero differ'"
    else:
        assert "Zero differ" not in doc, (
            "%d verdicts now differ across packagings and the page still says zero" % differ)


def test_the_two_solsec_real_crate_runs_agree_finding_for_finding():
    """The only repeat-run evidence on the real crates, and it exists by accident.

    The first runner read solsec's CI exit code as an outage and recorded eight completed scans
    as unavailable. The rerun that corrected the classifier repeated the 28 invocations the first
    attempt did finish, so the two files can be compared over those 28 - which is a determinism
    check the run did not set out to make, and the page quotes its number.
    """
    import io as _io, json as _json, os as _os
    first, second = "raw/rc-solsec-attempt1-exitcode.json", "raw/rc-solsec.json"
    for p in (first, second, first + ".log"):
        assert _os.path.exists(p), p + " is missing, so the determinism claim is uncheckable"
    ok = set(e["leaf"] for e in _json.load(_io.open(first + ".log", encoding="utf-8"))
             if e.get("status") == "ok")
    assert len(ok) == 28, "the first attempt finished %d invocations, not 28" % len(ok)

    def rows(path, leaves=None):
        out = []
        for x in _json.load(_io.open(path, encoding="utf-8"))["analysis_results"]:
            fp = x["file_path"]
            leaf = "/".join(fp.split("/")[:2])
            if leaves is not None and leaf not in leaves:
                continue
            out.append((fp, x["rule_name"], x["line_number"]))
        return sorted(out)

    a, b = rows(first), rows(second, ok)
    assert a == b, ("the two solsec runs disagree over the 28 invocations they share: "
                    "%d findings against %d" % (len(a), len(b)))
    doc = _io.open(RC_DOC, encoding="utf-8").read()
    assert str(len(a)) in doc, (
        "%s should quote the %d findings the two runs agree on" % (RC_DOC, len(a)))
