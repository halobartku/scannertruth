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

    python holdout.py commit --spec spec.json --round 1
    python holdout.py verify --spec spec.json --against COMMITMENTS-HOLDOUT.json
    python holdout.py --demo
"""
import argparse
import datetime
import hashlib
import json
import os
import sys

LEDGER = "COMMITMENTS-HOLDOUT.json"


def canonical(spec):
    """Byte-stable rendering, so the hash cannot drift on key order or whitespace."""
    return json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(spec):
    return hashlib.sha256(canonical(spec)).hexdigest()


def load_ledger():
    if os.path.exists(LEDGER):
        with open(LEDGER, encoding="utf-8") as fh:
            return json.load(fh)
    return {"scheme": "sha256 over canonical JSON of the case spec",
            "why": "a holdout chosen or edited after seeing scores proves nothing",
            "rounds": []}


def cmd_commit(args):
    with open(args.spec, encoding="utf-8") as fh:
        spec = json.load(fh)
    for field in ("repo", "fix", "files", "class"):
        if field not in spec:
            print(f"FATAL: spec is missing {field!r}. An incomplete spec would let the case be "
                  f"'clarified' later, which is the hole this closes.")
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


def demo():
    """The properties worth checking are: stable hashing, and detection of any edit."""
    spec = {"repo": "x/y", "fix": "abc123", "files": ["src/lib.rs"], "class": "owner-checks"}
    reordered = {"class": "owner-checks", "files": ["src/lib.rs"], "fix": "abc123", "repo": "x/y"}
    assert digest(spec) == digest(reordered), "key order must not change the commitment"

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
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo or args.cmd is None:
        return demo()
    return {"commit": cmd_commit, "release": cmd_release, "verify": cmd_verify}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
