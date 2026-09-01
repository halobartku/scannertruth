# --------------------------------------------------------- run_all extractors
# One wrong parser silently changes a published number, and each scanner has its own format.

def test_extract_radar_envelope():
    import run_all
    blob = [{"name": "Rule A", "locations": ["/a/b.rs:10:1-5", "/c/d.rs:20:2-6"]}]
    out = run_all.extract("radar", blob)
    assert out == [("Rule A", "/a/b.rs"), ("Rule A", "/c/d.rs")], out


def test_extract_xray_same_envelope_as_radar():
    import run_all
    blob = [{"name": "1019", "locations": ["/a/b.rs:5:1"]}]
    assert run_all.extract("xray", blob) == [("1019", "/a/b.rs")]


def test_extract_semgrep_shape():
    import run_all
    blob = {"results": [{"check_id": "rust.x", "path": "src/a.rs", "start": {"line": 3}}]}
    assert run_all.extract("semgrep", blob) == [("rust.x", "src/a.rs")]


def test_extract_flat_findings_shape():
    import run_all
    blob = {"findings": [{"rule_id": "SOL-001", "file": "src/a.rs", "line": 7}]}
    assert run_all.extract("sol-audit", blob) == [("SOL-001", "src/a.rs")]


def test_extract_rejects_an_unknown_format_loudly():
    import run_all
    try:
        run_all.extract("not-a-real-format", [])
    except ValueError:
        return
    raise AssertionError("an unknown format must raise, not return an empty list")


def test_extract_handles_empty_input_without_inventing_findings():
    import run_all
    assert run_all.extract("radar", []) == []
    assert run_all.extract("semgrep", {"results": []}) == []
    assert run_all.extract("sol-audit", {"findings": []}) == []
