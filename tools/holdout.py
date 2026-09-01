#!/usr/bin/env python3
"""Commit to a holdout case before measuring, prove afterwards that it was not chosen to fit.

Every corpus-1 number in this repository is in-sample: the teaching corpus is public, and at least
two of the tools measured cite it directly as the reference for their own rules. `control-noisy`
proves a score cannot be bought with volume. Nothing here proved a score was not bought by tuning
against a corpus the tool's authors could read.

A holdout is the only real answer, and a holdout is worthless if the people running it can pick or
edit it after seeing the scores. So the case is **committed to cryptographically before the run**:

    round N:  publish SHA-256(canonical spec)  ->  measure  ->  publish the spec itself

Anyone can then recompute the hash and confirm the case that scored the round is the case that was
sealed before it. The corpus stays open and free, as promised: the spec is released the moment the
round it scores is published, so every case becomes public on a one-round delay rather than never.

    python holdout.py nonce                       # a fresh one; put it in the spec first
    python holdout.py commit --spec spec.json --round 2
    python holdout.py verify --spec spec.json --against COMMITMENTS-HOLDOUT.json
    python holdout.py --demo

**The spec must carry a high-entropy `nonce`, from round 2 onward.** Without one the commitment
conceals nothing, because every other field is public and enumerable: `repo` is one of a few dozen
Solana projects, `fix` is a commit id inside it, `class` is one of about a dozen strings, `files` is
a path in that commit. A vendor guesses a candidate, hashes it, and compares - one hash per guess.
`docs/CANDIDATES-TRIAGE.md` publishes the accepted-pending-build candidates by name, so round 1's
search space was roughly two. Round 1 was sealed under the original scheme and stays exactly as it
was sealed; it gives timestamp integrity and **no** concealment, and so does any other pre-nonce
round. A nonce of 256 bits makes the preimage unguessable without changing anything else about the
scheme, and it is released with the spec so the commitment stays checkable by anyone.

Found from outside on 2026-09-01. The ledger claimed round 2 would give concealment; it would not
have.
"""
import argparse
import datetime
import hashlib
import json
import os
import secrets
import sys

LEDGER = "COMMITMENTS-HOLDOUT.json"

# The fields a spec must carry. `nonce` is the one added on 2026-09-01; the other four are all
# public, so on their own they are a password made of the answer.
REQUIRED = ("repo", "fix", "files", "class", "nonce")

# 64 hex characters, 256 bits. Long enough that guessing the other four fields buys nothing.
NONCE_HEX_CHARS = 64

SCHEME = ("sha256 over canonical JSON of the case spec, which must carry a 256-bit hex nonce; "
          "the nonce is released with the spec")
SCHEME_ROUND_1 = ("sha256 over canonical JSON of the case spec, no nonce: timestamp integrity "
                  "only, no concealment")


def canonical(spec):
    """Byte-stable rendering, so the hash cannot drift on key order or whitespace."""
    return json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(spec):
    return hashlib.sha256(canonical(spec)).hexdigest()


def load_ledger():
    if os.path.exists(LEDGER):
        with open(LEDGER, encoding="utf-8") as fh:
            return json.load(fh)
    return {"scheme": SCHEME,
            "why": "a holdout chosen or edited after seeing scores proves nothing",
            "rounds": []}


def cmd_commit(args):
    with open(args.spec, encoding="utf-8") as fh:
        spec = json.load(fh)
    for field in REQUIRED:
        if field not in spec:
            print(f"FATAL: spec is missing {field!r}. An incomplete spec would let the case be "
                  f"'clarified' later, which is the hole this closes.")
            if field == "nonce":
                print("       Run `python tools/holdout.py nonce` and put the value in the spec. "
                      "Without it every field is public and the preimage is guessable.")
            return 2

    if not valid_nonce(spec["nonce"]):
        print(f"FATAL: nonce must be {NONCE_HEX_CHARS} hex characters. A short or guessable one "
              f"conceals nothing, which is the whole reason the field exists.")
        return 2

    ledger = load_ledger()
    if any(r["round"] == args.round for r in ledger["rounds"]):
        print(f"FATAL: round {args.round} is already sealed. Sealing twice would let a "
              f"disappointing holdout be replaced.")
        return 2

    ledger["rounds"].append({
        "round": args.round,
        "sealed_at": datetime.datetime.now(datetime.timezone.utc)
                             .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commitment": digest(spec),
        "scheme": SCHEME,
        "released": False,
        "spec": None,
        "note": args.note or "",
    })
    with open(LEDGER, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=1)
    print(f"round {args.round} sealed: {digest(spec)}")
    print(f"The spec itself stays out of this repository until round {args.round} is published.")
    return 0


def cmd_release(args):
    with open(args.spec, encoding="utf-8") as fh:
        spec = json.load(fh)
    ledger = load_ledger()
    for r in ledger["rounds"]:
        if r["round"] != args.round:
            continue
        if r["commitment"] != digest(spec):
            print("MISMATCH. The spec does not hash to the sealed commitment. Either this is a "
                  "different case, or it was edited after sealing. Do not publish the round.")
            return 1
        r["released"] = True
        r["spec"] = spec
        r["released_at"] = datetime.datetime.now(datetime.timezone.utc) \
                                   .strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(LEDGER, "w", encoding="utf-8") as fh:
            json.dump(ledger, fh, indent=1)
        print(f"round {args.round} released and verified against its commitment.")
        return 0
    print(f"FATAL: no sealed round {args.round}")
    return 2


def cmd_verify(args):
    with open(args.spec, encoding="utf-8") as fh:
        spec = json.load(fh)
    with open(args.against, encoding="utf-8") as fh:
        ledger = json.load(fh)
    d = digest(spec)
    for r in ledger["rounds"]:
        if r["commitment"] == d:
            print(f"MATCH: this spec is the case sealed for round {r['round']} "
                  f"at {r['sealed_at']}.")
            return 0
    print("NO MATCH: this spec was not sealed in any round in that ledger.")
    return 1


def valid_nonce(value):
    if not isinstance(value, str) or len(value) != NONCE_HEX_CHARS:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def cmd_nonce(args):
    print(secrets.token_hex(NONCE_HEX_CHARS // 2))
    return 0


def demo():
    """The properties worth checking are: stable hashing, detection of any edit, and concealment."""
    nonce = secrets.token_hex(NONCE_HEX_CHARS // 2)
    spec = {"repo": "x/y", "fix": "abc123", "files": ["src/lib.rs"], "class": "owner-checks",
            "nonce": nonce}
    reordered = {"class": "owner-checks", "nonce": nonce, "files": ["src/lib.rs"],
                 "fix": "abc123", "repo": "x/y"}
    assert digest(spec) == digest(reordered), "key order must not change the commitment"

    # Concealment: someone who guesses every public field still cannot reproduce the commitment.
    guessed = {k: v for k, v in spec.items() if k != "nonce"}
    assert digest(guessed) != digest(spec),         "a spec without its nonce must not hash to the same commitment"
    assert digest(dict(guessed, nonce=secrets.token_hex(NONCE_HEX_CHARS // 2))) != digest(spec),         "guessing the public fields and a wrong nonce must not confirm the case"

    assert valid_nonce(nonce)
    assert not valid_nonce("deadbeef"), "a short nonce is not a nonce"
    assert not valid_nonce("z" * NONCE_HEX_CHARS), "a nonce must be hex"

    edited = dict(spec)
    edited["fix"] = "abc124"
    assert digest(spec) != digest(edited), "a one-character edit must break the commitment"

    edited2 = dict(spec)
    edited2["class"] = "signer-authorization"
    assert digest(spec) != digest(edited2), "reclassifying the case must break the commitment"
    print("holdout: OK")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("commit"); c.add_argument("--spec", required=True)
    c.add_argument("--round", type=int, required=True); c.add_argument("--note", default="")
    r = sub.add_parser("release"); r.add_argument("--spec", required=True)
    r.add_argument("--round", type=int, required=True)
    v = sub.add_parser("verify"); v.add_argument("--spec", required=True)
    v.add_argument("--against", default=LEDGER)
    sub.add_parser("nonce")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo or args.cmd is None:
        return demo()
    return {"commit": cmd_commit, "release": cmd_release, "verify": cmd_verify,
            "nonce": cmd_nonce}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
