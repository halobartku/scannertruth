# ------------------------------------------------------------ data integrity
# Cheap checks that catch a corrupted or half-written artefact before it reaches a table.

def test_every_raw_json_file_parses():
    """A half-written raw file is a corrupted number waiting to be published."""
    import json, io as _io, os
    targets = [os.path.join("raw", f) for f in sorted(os.listdir("raw"))]
    targets += [os.path.join("mappings", f) for f in sorted(os.listdir("mappings"))]
    targets += ["COMMITMENTS-HOLDOUT.json", "corpus2/manifest.json"]
    bad = []
    for fn in targets:
        if not fn.endswith(".json") or not os.path.exists(fn):
            continue
        try:
            json.load(_io.open(fn, encoding="utf-8"))
        except Exception as e:
            bad.append(f"{fn}: {type(e).__name__}")
    assert not bad, f"unparseable json: {bad}"



def test_every_corpus_case_names_its_fix_commit():
    import json, io as _io
    man = json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    for c in man:
        assert c.get("fix"), f"{c['name']} has no fix commit"
        assert c.get("repo"), f"{c['name']} has no repo"
        assert c.get("class"), f"{c['name']} has no vulnerability class"


def test_every_corpus_case_declares_its_source():
    """The answer key must be somebody else's, and traceable."""
    import json, io as _io
    man = json.load(_io.open("corpus2/manifest.json", encoding="utf-8"))["cases"]
    missing = [c["name"] for c in man if not c.get("source") and c.get("valid", True)]
    assert not missing, f"valid cases with no disclosure source: {missing}"


def test_clock_history_is_ordered_and_parseable():
    import json, io as _io, os, glob
    files = sorted(glob.glob("runs/*.json"))
    assert files, "the clock has no history"
    dates = []
    for f in files:
        d = json.load(_io.open(f, encoding="utf-8"))
        assert d.get("date"), f"{f} has no date"
        dates.append(d["date"])
    assert dates == sorted(dates), f"clock history is out of order: {dates}"


def test_results_pages_do_not_contradict_the_clock_on_radar():
    """The single most quoted number in the whole project."""
    import io as _io
    s = _io.open("docs/results/RESULTS-all.md", encoding="utf-8").read()
    assert "11 / 11" in s or "11/11" in s, "Radar's teaching-corpus score vanished from RESULTS-all"


# --------------------------------------------------------------- adapters.py
def test_finding_is_a_three_field_record():
    import adapters
    f = adapters.Finding("R", "a.rs", 3)
    assert (f.rule_id, f.path, f.line) == ("R", "a.rs", 3)


def test_null_control_produces_nothing():
    import adapters, tempfile
    n = adapters.NullScanner()
    assert n.available()
    with tempfile.TemporaryDirectory() as t:
        assert list(n.run(t)) == [], "the null control must be silent by construction"


def test_noisy_control_flags_every_non_empty_line():
    import adapters, tempfile, os, io as _io
    with tempfile.TemporaryDirectory() as t:
        _io.open(os.path.join(t, "a.rs"), "w", encoding="utf-8").write("one\n\ntwo\n")
        out = list(adapters.NoisyScanner().run(t))
        assert len(out) == 2, f"two non-empty lines should give two findings, got {len(out)}"
