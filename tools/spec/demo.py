"""The self-check, and the fixture declaration it and the suite drive."""
import json
import os
import sys
import tempfile

from .control import positive_control
from .measure import _key, corpus_leaves, determinism
from .run import _rewrite, classify, command_for, run_leaf
from .validate import clock_tables, load, load_all


# --------------------------------------------------------------------------- self-check

def demo():
    """The properties that would let a defect here publish a wrong number."""
    # 1. Unavailability must never collapse into a zero, in either direction.
    spec = load(_FIXTURE_SPEC)
    ok, seen, why = classify(spec, 0, "fixture scanned 3 files\n", [])
    assert ok == "ok" and seen == 3 and not why, (ok, seen, why)
    silent, seen, why = classify(spec, 0, "", [])
    assert silent == "unavailable", (
        "exit 0 with no coverage line was classified as a run that happened; that is error 35")
    assert "did not say it read anything" in why, why
    crashed, _, why = classify(spec, 3, "fixture scanned 3 files\n", [])
    assert crashed == "unavailable", "a non-zero exit was classified as a result"
    unreadable, _, why = classify(spec, 0, "fixture scanned 3 files\n", None)
    assert unreadable == "unavailable", "unparseable output was classified as a result"
    assert ok != silent, "a clean zero and an outage must not carry the same status"

    # 2. A declaration that does not say how the tool announces coverage is refused outright.
    blind = json.loads(json.dumps(_FIXTURE_SPEC))
    del blind["coverage"]["evidence"]
    try:
        load(blind)
        raise AssertionError("a declaration with no coverage evidence was accepted")
    except ValueError as exc:
        assert "coverage.evidence is missing" in str(exc), exc

    # 3. A tool that admits it prints no coverage line gets `unknown`, never `ok`.
    mute = json.loads(json.dumps(_FIXTURE_SPEC))
    mute["coverage"]["evidence"] = {"absent": True, "reason": "prints no file count"}
    status, _, why = classify(load(mute), 0, "", [])
    assert status == "unknown", status
    assert why == "prints no file count", why

    # 3b. A declared token is substituted; an undeclared one is refused rather than ignored.
    # sol-audit's broad and all rows differ from strict by this token alone. Before it existed the
    # declaration could only produce one of the three and the other two came from a script outside
    # the framework, which is the situation the framework exists to end.
    profiled = json.loads(json.dumps(_FIXTURE_SPEC))
    profiled["run"]["command"] = ["python", "{mount}", "--profile", "{profile}"]
    profiled["run"]["arg_defaults"] = {"profile": "strict"}
    spec_p = load(profiled)
    assert command_for(spec_p, "/t", "/o")[-1] == "strict", "the declared default was not used"
    assert command_for(spec_p, "/t", "/o", args={"profile": "all"})[-1] == "all"
    try:
        command_for(spec_p, "/t", "/o", args={"proflie": "all"})
        raise AssertionError("a token the declaration does not declare was accepted, which would "
                             "have run the default and filed it under the other name")
    except ValueError as exc:
        assert "does not declare" in str(exc), exc

    # 3c. A mount whose source is missing is refused at load time. Docker creates an empty
    # directory for it instead of failing, so semgrep would have scanned every case with no
    # ruleset and every case would have come back clean.
    mounted = json.loads(json.dumps(_FIXTURE_SPEC))
    mounted["run"] = {"engine": "docker", "image": "x:1", "mount": "/src",
                      "mounts": [{"from": "adapters/radar.json", "to": "/rules/r.json"}],
                      "command": ["scan", "{mount}"], "timeout_seconds": 60,
                      "invocation_evidence": "tools/scanner_spec.py demo"}
    argv = command_for(load(mounted), "relative/target", "relative/out")
    assert any(a.endswith("adapters" + os.sep + "radar.json:/rules/r.json:ro")
               or a.endswith("adapters/radar.json:/rules/r.json:ro") for a in argv), argv
    # Every bind source docker is given is absolute. A relative one is read as the name of a
    # named volume, not as a directory, and 34 invocations died on that before this line existed.
    for i, a in enumerate(argv):
        if a == "-v":
            assert not argv[i + 1].startswith("relative"), (
                "a relative bind source reached docker, which reads it as a volume NAME: "
                + argv[i + 1])
    mounted["run"]["mounts"] = [{"from": "adapters/does-not-exist.json", "to": "/rules/r.json"}]
    try:
        load(mounted)
        raise AssertionError("a mount naming a path that is not here was accepted; docker would "
                             "have created an empty directory and the run would look like a zero")
    except ValueError as exc:
        assert "not in this repository" in str(exc), exc

    # 3d. Corpus 1's variants are enumerated, not assumed. Two of the five directories under
    # `9-closing-accounts` are not in the usual triple, and a run log that omits them says the
    # corpus is smaller than it is.
    with tempfile.TemporaryDirectory() as tmp:
        for cls, variant in (("9-closing-accounts", "insecure"),
                             ("9-closing-accounts", "insecure-still"),
                             ("9-closing-accounts", "secure"),
                             ("0-signer-authorization", "insecure")):
            os.makedirs(os.path.join(tmp, cls, variant, "src"))
        leaves = {leaf for leaf, _d, _p in corpus_leaves("corpus1", root=tmp)}
        assert "9-closing-accounts/insecure-still" in leaves, leaves
        assert len(leaves) == 4, leaves

    # 3e. A declared rule-id prefix is stripped on the way into the envelope, and only when the
    # declaration says why. semgrep emits `rules.<id>` for a local config and `<id>` for the same
    # ruleset by URL; the mapping registered before the run holds the second form. The first
    # framework run without this turned three `unlocated` verdicts into `missed` with the tool,
    # the ruleset and the corpus all byte-identical to the run that published them.
    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "case")
        os.makedirs(target)
        with open(os.path.join(target, "__main__.py"), "w", encoding="utf-8",
                  newline="\n") as fh:
            # The coverage line goes to stderr so stdout stays parseable JSON: the same split
            # vaultlint's declaration relies on.
            fh.write('import sys\n'
                     'print("fixture scanned 1 files", file=sys.stderr)\n'
                     'print(\'{"findings": [{"rule_id": "rules.R1", "file": "src/lib.rs",'
                     ' "line": 3}]}\')\n')
        striking = json.loads(json.dumps(_FIXTURE_SPEC))
        striking["output"]["rule_id_strip_prefix"] = "rules."
        striking["rule_id_note"] = "the fixture emits both forms, as semgrep does"
        entry, got = run_leaf(load(striking), "case/insecure", target, "corpus/case/insecure",
                              os.path.join(tmp, "artefacts"))
        assert entry["status"] == "ok", entry
        assert [f["rule_id"] for f in got] == ["R1"], got
        striking["output"].pop("rule_id_strip_prefix")
        _e, got2 = run_leaf(load(striking), "case/insecure", target, "corpus/case/insecure",
                            os.path.join(tmp, "artefacts2"))
        assert [f["rule_id"] for f in got2] == ["rules.R1"], (
            "the prefix was stripped without the declaration asking for it")

    # 3f. `wrapped-pkg` staging survives a relative --artefacts. The staged directory is what
    # `_rewrite` strips off by prefix, so a relative one matches nothing a tool reports and every
    # finding keeps the whole staging path glued to the corpus path. A 34-invocation radar run
    # produced 31 such paths, all of them plausible-looking and none of them on disk.
    with tempfile.TemporaryDirectory() as tmp:
        was = os.getcwd()
        try:
            os.chdir(tmp)
            src = os.path.join(tmp, "insecure", "src")
            os.makedirs(src)
            with open(os.path.join(tmp, "insecure", "__main__.py"), "w", encoding="utf-8",
                      newline="\n") as fh:
                fh.write('import json, os, sys\n'
                         'here = os.path.dirname(os.path.abspath(__file__))\n'
                         'print("fixture scanned 1 files", file=sys.stderr)\n'
                         'print(json.dumps({"findings": [{"rule_id": "FIX-001",\n'
                         '    "file": os.path.join(here, "src", "lib.rs"), "line": 3}]}))\n')
            with open(os.path.join(src, "lib.rs"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write("fn main() {}\n")
            wrapped = json.loads(json.dumps(_FIXTURE_SPEC))
            wrapped["layout"] = "wrapped-pkg"
            wrapped["run"]["command"] = [sys.executable, "{mount}/pkg"]
            _entry, got = run_leaf(load(wrapped), "case/insecure",
                                   os.path.join(tmp, "insecure"), "corpus/case/insecure",
                                   "relative-artefacts")
            assert [f["file"] for f in got] == ["corpus/case/insecure/src/lib.rs"], got
        finally:
            os.chdir(was)

    # 4. Path rewriting is a prefix operation and nothing else.
    assert _rewrite("/src/src/lib.rs", "/src", "", "corpus2/x/insecure") == \
        "corpus2/x/insecure/src/lib.rs"
    assert _rewrite("/src/pkg/src/lib.rs", "/src", "pkg/", "corpus2/x/insecure") == \
        "corpus2/x/insecure/src/lib.rs"

    # 5. Determinism is a verdict, not an average.
    def _pass(tag, line):
        f = {"rule_id": "R", "file": "corpus2/x/insecure/src/lib.rs", "line": line, "col": 0}
        return (tag, [{"leaf": "x/insecure", "status": "ok"}], [f], {"x/insecure": {_key(f)}})
    a, b, c = _pass("", 3), _pass(".run2", 3), _pass(".run2", 9)
    assert determinism([a, b])["verdict"] == "deterministic"
    bad = determinism([a, c])
    assert bad["verdict"] == "non-deterministic", bad
    assert bad["differing"], bad
    assert determinism([a])["verdict"] == "not-checked"

    # 6. Every declaration in the repository proves its parser can carry a detection.
    for name, spec in sorted(load_all().items()):
        positive_control(spec)

    # 7. The clock tables derive without collision.
    c1, c2, alias, _ = clock_tables()
    assert c1 and c2, (c1, c2)
    print("scanner_spec: OK (including the positive control for every declaration)")


# A declaration used only by the self-check and the suite. It is a real one: `run.engine` is
# `local` so the framework can be driven end to end on a laptop with no Docker, which is where
# most of this project's development happens.
_FIXTURE_SPEC = {
    "name": "fixture-scanner",
    "version": "0",
    "provenance": {"repository": "https://example.invalid/fixture",
                   "install": "none: this is a fixture, not a tool",
                   "install_documented_at": "tools/scanner_spec.py",
                   "checked_on": "2026-09-01"},
    "run": {"engine": "local", "command": ["python", "{mount}"], "timeout_seconds": 60,
            "invocation_evidence": "defined in tools/scanner_spec.py; the suite writes the script"},
    "layout": "variant-dir",
    "coverage": {"ok_exit_codes": [0],
                 "evidence": {"pattern": r"fixture scanned (\d+) files", "minimum": 1,
                              "means": "the fixture's own count of files read"}},
    "output": {"from": "stdout", "format": "sol-audit"},
    "envelope": "sol-audit",
    "positive_control": {"rule_id": "FIX-001",
                         "sample": {"findings": [{"rule_id": "FIX-001", "file": "{path}",
                                                  "line": "{line}"}]}},
    "measurements": [],
}
