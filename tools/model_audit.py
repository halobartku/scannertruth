#!/usr/bin/env python3
"""Measure a model-backed auditor the way we measure a scanner, plus the thing that makes it hard.

    python tools/model_audit.py --model qwen3.5:9b --runs 3
    python tools/model_audit.py --model qwen3.5:9b --runs 1 --case anchor-interface-account

A static scanner is deterministic: same code, same answer, so one measurement holds. A model is
not, and measuring one once is what everybody currently does. So every case is asked `--runs`
times and the spread is reported. A model that names the bug in one run out of three is a
33-percent auditor and is written down as one.

**Real recall is the whole point and it is what nobody applies to models.** An LLM asked to find
vulnerabilities will find something in almost any code. So each case is asked twice: once on the
vulnerable program and once on the *same program after its maintainers fixed it*. A model that
calls both of them vulnerable has detected nothing - it recognised a code shape, exactly like the
noisy control. That comparison is only possible because corpus 2 is built as vulnerable/fixed
pairs anchored to real fix commits, and it is the reason this measurement can exist at all.

Writes one JSON line per invocation before it returns, because a run without an artefact and a run
that never happened look identical afterwards.
"""
import argparse
import json
import pathlib
import re
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus2"
# The teaching corpus is a sibling checkout, the same one every scanner run uses. Frozen at
# 2022-07-16, so a model trained after that has very likely read it - which is exactly why the
# two corpora have to be measured with one command and reported side by side.
CORPUS1 = ROOT.parent / "sealevel-attacks" / "programs"
OLLAMA = "http://localhost:11434/api/generate"

# Versioned deliberately. A result measured under a different prompt is a different measurement,
# and without recording which one ran, the number is not reproducible even for us.
PROMPT_VERSION = "v1-2026-09-01"
PROMPT = """You are auditing a Solana program written in Rust for security vulnerabilities.

Answer with one JSON object and nothing else:
{"vulnerable": true or false, "class": "<short name of the vulnerability class, or empty>", "why": "<one sentence>"}

Say vulnerable=true ONLY if this code contains an exploitable security flaw. Ordinary code, style
issues, and missing tests are not vulnerabilities. Some of the programs you will see are already
fixed and are not vulnerable. Be precise rather than helpful.

CODE:
"""


def sources(case_dir, variant):
    """The .rs files of one variant, concatenated. Small by construction; these are single-file cases."""
    files = sorted((case_dir / variant).rglob("*.rs"))
    return "\n\n".join(f"// {f.relative_to(case_dir)}\n{f.read_text(encoding='utf-8', errors='replace')}"
                       for f in files)


def ask(model, code):
    body = json.dumps({
        "model": model,
        "prompt": PROMPT + code[:24000],
        "stream": False,
        "think": False,
        "options": {"temperature": 0},
    }).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        raw = (json.loads(r.read()).get("response") or "").strip()
    return raw


def verdict(raw):
    """Parse the model's answer. An unparseable answer is NOT a detection - it is recorded as such."""
    m = re.search(r'\{.*?\}', raw, re.S)
    if not m:
        return None, "no json in response"
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None, "malformed json"
    v = d.get("vulnerable")
    if isinstance(v, str):
        # Only the two words count. Treating anything-not-"true" as False would score a hedge
        # ("maybe", "unclear") as "the model said it is safe", which silently flatters the model
        # on the fixed variant, where staying silent is what earns a detection.
        s = v.strip().lower()
        v = True if s == "true" else False if s == "false" else None
    if not isinstance(v, bool):
        return None, "no boolean verdict"
    return v, (d.get("class") or "")[:60]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="qwen3.5:9b")
    ap.add_argument("--runs", type=int, default=3, help="invocations per variant; spread is the point")
    ap.add_argument("--case", help="one case only, for a smoke test")
    ap.add_argument("--corpus", choices=("1", "2"), default="2",
                    help="1 = the teaching corpus everybody scores on, 2 = real vulnerabilities")
    args = ap.parse_args()

    if args.corpus == "1":
        if not CORPUS1.is_dir():
            sys.exit(f"teaching corpus not found at {CORPUS1}")
        root = CORPUS1
        # "3-type-cosplay" carries its class in its own directory name; strip the ordinal.
        cases = [{"name": d.name, "class": d.name.split("-", 1)[1]}
                 for d in sorted(CORPUS1.iterdir()) if d.is_dir()]
    else:
        root = CORPUS
        manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
        cases = [c for c in manifest["cases"] if c.get("valid", True)]
    if args.case:
        cases = [c for c in cases if c["name"] == args.case]
        if not cases:
            sys.exit(f"no such case: {args.case}")

    stamp = time.strftime("%Y-%m-%d")
    out_dir = ROOT / "raw" / f"model-{args.model.replace(':', '-').replace('/', '-')}-c{args.corpus}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log = (out_dir / "runs.jsonl").open("a", encoding="utf-8")

    print(f"model={args.model}  corpus={args.corpus}  prompt={PROMPT_VERSION}  runs={args.runs}  cases={len(cases)}")
    print(f"artefacts: {out_dir}\n")

    detected = both = neither = missed = unusable = 0
    for c in cases:
        case_dir = root / c["name"]
        if not (case_dir / "insecure").is_dir() or not (case_dir / "secure").is_dir():
            print(f"  {c['name']:38s} SKIP (no vulnerable/fixed pair built)")
            continue

        hits = {"insecure": 0, "secure": 0}
        named = {}
        bad = 0
        for variant in ("insecure", "secure"):
            code = sources(case_dir, variant)
            for i in range(args.runs):
                t0 = time.time()
                try:
                    raw = ask(args.model, code)
                    err = None
                except Exception as exc:  # noqa: BLE001
                    raw, err = "", f"{type(exc).__name__}"
                v, note = verdict(raw) if not err else (None, err)
                log.write(json.dumps({
                    "corpus": args.corpus, "case": c["name"], "class": c.get("class", ""),
                    "variant": variant, "run": i + 1,
                    "model": args.model, "prompt_version": PROMPT_VERSION,
                    "vulnerable": v, "note": note, "sec": round(time.time() - t0, 1),
                    "raw": raw[:600],
                }, ensure_ascii=False) + "\n")
                log.flush()
                if v is None:
                    bad += 1
                elif v:
                    hits[variant] += 1
                    named.setdefault(variant, note)

        # Real recall: it must fire on the vulnerable program AND stay silent on the fixed one.
        # "Fires on both" is the model-shaped version of the noisy control, and it is not a detection.
        fires_vuln = hits["insecure"] > 0
        fires_fixed = hits["secure"] > 0
        if bad == args.runs * 2:
            mark, unusable = "UNUSABLE", unusable + 1
        elif fires_vuln and not fires_fixed:
            # A static scanner is credited only when its MAPPED rule fires, not when any rule does.
            # A model always supplies a reason, and the reason can be wrong while the verdict is
            # right - on 2026-09-01 qwen3.5:9b called an account-data-matching bug "Reentrancy" and
            # would have scored a detection. So the class it named is carried through here and the
            # verdict alone is not enough. Agreement is adjudicated by hand in mappings/, never by
            # string equality, because "Integer Overflow" and "arithmetic-rounding-drain" are close
            # enough to argue about and that argument must happen in the open.
            mark = f"verdict only, named \"{named.get('insecure','')}\" for class {c.get('class','')}"
            detected += 1
        elif fires_vuln and fires_fixed:
            mark, both = "fires on the fix too", both + 1
        elif not fires_vuln and not fires_fixed:
            mark, neither = "silent on both", neither + 1
        else:
            mark, missed = "only on the fixed one", missed + 1
        print(f"  {c['name']:38s} vuln {hits['insecure']}/{args.runs}  fixed {hits['secure']}/{args.runs}  {mark}")

    log.close()
    n = detected + both + neither + missed + unusable
    # NOT "real detections". This counts cases where the verdict was right on both variants, which
    # is necessary and not sufficient. Whether it is a detection depends on the class named being
    # the class present, and that is adjudicated by hand. Calling this line "real detections" on
    # 2026-09-01 would have published 2/17 for a model that named Reentrancy for an
    # account-data-matching bug - the exact overclaim this project exists to catch.
    print(f"\n  verdict right on both variants (necessary, not sufficient): {detected} / {n}")
    print("    ^ each one still needs its named class adjudicated against the real class above")
    print(f"  fires on the fix too (no detection):                    {both}")
    print(f"  silent on both:                                        {neither}")
    print(f"  only on the fixed variant:                             {missed}")
    print(f"  unusable answers:                                      {unusable}")
    print(f"\n  per-run log: {out_dir / 'runs.jsonl'}")


def demo():
    """Self-check: the verdict parser must accept what a model actually returns and refuse the rest."""
    assert verdict('{"vulnerable": true, "class": "missing signer", "why": "x"}')[0] is True
    assert verdict('sure!\n{"vulnerable": false, "class": "", "why": "looks fixed"}\n')[0] is False
    assert verdict('{"vulnerable": "true"}')[0] is True          # models quote booleans
    assert verdict('I think it might be unsafe')[0] is None      # prose is not a verdict
    assert verdict('{"vulnerable": "maybe"}')[0] is None         # neither is a hedge
    assert verdict('{broken')[0] is None
    print("ok: prose and hedges are not detections, quoted booleans are")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        main()
