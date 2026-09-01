import tempfile


# ----------------------------------------------------------------- holdout
# A commitment that can be edited afterwards proves nothing.

def test_holdout_key_order_does_not_change_the_commitment():
    import holdout
    a = {"repo": "x/y", "fix": "abc", "files": ["a.rs"], "class": "owner-checks"}
    b = {"class": "owner-checks", "files": ["a.rs"], "fix": "abc", "repo": "x/y"}
    assert holdout.digest(a) == holdout.digest(b)


def test_holdout_any_edit_breaks_the_commitment():
    import holdout
    a = {"repo": "x/y", "fix": "abc", "files": ["a.rs"], "class": "owner-checks"}
    for field, value in (("fix", "abd"), ("class", "type-cosplay"), ("repo", "x/z")):
        b = dict(a)
        b[field] = value
        assert holdout.digest(a) != holdout.digest(b), f"editing {field} must break the hash"


# ------------------------------------------------------- holdout ledger sanity
def test_holdout_ledger_never_seals_a_round_twice():
    import json, io as _io, os
    if not os.path.exists("COMMITMENTS-HOLDOUT.json"):
        return
    d = json.load(_io.open("COMMITMENTS-HOLDOUT.json", encoding="utf-8"))
    rounds = [r["round"] for r in d.get("rounds", [])]
    assert len(rounds) == len(set(rounds)), \
        "a round sealed twice would let a disappointing holdout be replaced"


def test_holdout_ledger_admits_what_round_one_does_not_prove():
    import json, io as _io, os
    if not os.path.exists("COMMITMENTS-HOLDOUT.json"):
        return
    d = json.load(_io.open("COMMITMENTS-HOLDOUT.json", encoding="utf-8"))
    key = [k for k in d if "NOT_prove" in k or "not_prove" in k.lower()]
    assert key, "the ledger must state that round 1 gives timestamp integrity, not concealment"


def test_a_holdout_spec_without_a_nonce_is_refused():
    """Four public fields hash to a commitment anyone can brute-force at one guess per hash.

    `repo` is one of a few dozen Solana projects, `fix` a commit inside it, `class` one of about a
    dozen strings, `files` a path in that commit - and CANDIDATES-TRIAGE names the pending
    candidates. Round 1 was sealed that way and stays as it was sealed; from round 2 the nonce is
    required, and `commit` must refuse rather than seal something that conceals nothing.
    """
    import argparse, contextlib, json, io as _io, os
    import holdout
    with tempfile.TemporaryDirectory() as t:
        cwd = os.getcwd()
        spec = {"repo": "x/y", "fix": "a" * 40, "files": ["src/lib.rs"], "class": "owner-checks"}
        path = os.path.join(t, "spec.json")
        json.dump(spec, _io.open(path, "w", encoding="utf-8"))
        os.chdir(t)
        try:
            # holdout prints its refusals; the suite's own output stays readable.
            sink = _io.StringIO()
            with contextlib.redirect_stdout(sink):
                rc = holdout.cmd_commit(argparse.Namespace(spec=path, round=99, note=""))
            assert rc != 0, "a spec with no nonce must not be sealed"
            spec["nonce"] = "deadbeef"
            json.dump(spec, _io.open(path, "w", encoding="utf-8"))
            with contextlib.redirect_stdout(sink):
                rc = holdout.cmd_commit(argparse.Namespace(spec=path, round=99, note=""))
            assert rc != 0, "a short nonce conceals nothing and must not be sealed"
            spec["nonce"] = "0" * holdout.NONCE_HEX_CHARS
            json.dump(spec, _io.open(path, "w", encoding="utf-8"))
            with contextlib.redirect_stdout(sink):
                rc = holdout.cmd_commit(argparse.Namespace(spec=path, round=99, note=""))
            assert rc == 0, "a full-length hex nonce must seal"
        finally:
            os.chdir(cwd)


def test_the_nonce_actually_conceals():
    """Guessing every public field must not confirm the case."""
    import holdout
    spec = {"repo": "x/y", "fix": "a" * 40, "files": ["src/lib.rs"], "class": "owner-checks",
            "nonce": "1" * holdout.NONCE_HEX_CHARS}
    guessed = {k: v for k, v in spec.items() if k != "nonce"}
    assert holdout.digest(guessed) != holdout.digest(spec), \
        "a preimage guess without the nonce must not match the commitment"
    assert holdout.digest(dict(guessed, nonce="2" * holdout.NONCE_HEX_CHARS)) \
        != holdout.digest(spec), "a wrong nonce must not match either"


def test_the_ledger_declares_the_nonce_scheme_and_does_not_re_seal_round_one():
    """A commitment ledger may never rewrite a commitment, so round 1 keeps its own scheme."""
    import json, io as _io, os
    if not os.path.exists("COMMITMENTS-HOLDOUT.json"):
        return
    d = json.load(_io.open("COMMITMENTS-HOLDOUT.json", encoding="utf-8"))
    assert "nonce" in d.get("scheme", ""), "the ledger must declare the nonce in its scheme"
    assert d.get("nonce_required_from"), "the ledger must say from which round the nonce is required"
    for r in d["rounds"]:
        if r["round"] < d["nonce_required_from"]:
            assert "no nonce" in r.get("scheme", ""), (
                f"round {r['round']} predates the nonce and must say so rather than look compliant")
    assert d["rounds"][0]["commitment"] == \
        "fc525b66495c0f576d7d328e2b74eaa733f11fbe7fbfd2cf340de38b15835ec1", \
        "round 1's commitment was published on 2026-08-31 and may never change"


def test_unreleased_holdout_specs_are_not_in_the_repository():
    """A sealed spec sitting in the repo is not sealed."""
    import json, io as _io, os
    if not os.path.exists("COMMITMENTS-HOLDOUT.json"):
        return
    d = json.load(_io.open("COMMITMENTS-HOLDOUT.json", encoding="utf-8"))
    for r in d.get("rounds", []):
        if not r.get("released"):
            assert r.get("spec") is None, \
                f"round {r['round']} is unreleased but its spec is stored in the repo"
