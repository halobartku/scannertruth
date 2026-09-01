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
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus2"
# The teaching corpus is a sibling checkout, the same one every scanner run uses. Frozen at
# 2022-07-16, so a model trained after that has very likely read it - which is exactly why the
# two corpora have to be measured with one command and reported side by side.
CORPUS1 = ROOT.parent / "sealevel-attacks" / "programs"
OLLAMA = "http://localhost:11434/api/generate"
OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"

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


def _post_with_ceiling_fallback(url, payload, key):
    """POST a chat completion. A 400 that names `max_tokens` means the provider caps output below
    the ceiling we asked for; the call is repeated with no ceiling (the model's own maximum) and
    `payload["max_tokens"]` is set to None so the artefact line says so. A 429 is a shared quota
    (Z.ai's coding plan is also the VPS agent's) and is waited out a few times."""
    def post(body):
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=3600) as r:
            return json.loads(r.read())
    for attempt in range(6):
        try:
            return post({k: v for k, v in payload.items() if v is not None})
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")[:400]
            if e.code == 400 and "max_tokens" in text and payload.get("max_tokens") is not None:
                payload["max_tokens"] = None
                continue
            if e.code == 429 and attempt < 5:
                time.sleep(30 * (attempt + 1))
                continue
            raise RuntimeError(f"HTTP {e.code}: {text[:200]}")
    raise RuntimeError("gave up after six attempts")


def ask_openrouter(model, code, think=False):
    """One call through OpenRouter, returning the answer and what it actually cost.

    The key is read from the environment and never written to an artefact, a log line or the
    console. `usage.include` makes the provider report real token counts and real cost per call,
    so cost per detection is a measured number rather than an estimate - which matters, because
    "this auditor finds 2 of 17 for four dollars" is a sentence a buyer cannot read anywhere today.
    """
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT + code[:24000]}],
        "temperature": 0,
        "usage": {"include": True},
    }
    if think:
        payload["reasoning"] = {"enabled": True}
    # Reasoning is the provider's default otherwise, and it gets room. The first sweeps on
    # 2026-09-01 suppressed it (`reasoning.enabled: false`, 400-token belt) to match ollama's
    # think=False; those rows carry no `reasoning` field. On 2026-09-02 the owner's rule became:
    # if a model thinks, let it think, and record how much. `max_tokens` is only a ceiling now,
    # and 8,000 was not enough: glm-5.3 thought 33,813 characters on wormhole-sysvar and hit it.
    # 128,000 since 2026-09-02 01:40 (owner: "for everyone, 128k"); a provider that rejects the
    # value gets the call again with no ceiling at all, and the line records which happened.
    payload["max_tokens"] = 128000
    d = _post_with_ceiling_fallback(OPENROUTER, payload, key)
    msg = (d.get("choices") or [{}])[0].get("message", {}) or {}
    u = d.get("usage") or {}
    return ((msg.get("content") or "").strip(),
            (msg.get("reasoning") or ""),
            (d.get("choices") or [{}])[0].get("finish_reason", ""),
            {"prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
             "cost_usd": u.get("cost"), "reasoning": "requested" if think else "allowed",
             "max_tokens": payload.get("max_tokens")})


ZAI = os.environ.get("GLM_BASE_URL", "https://api.z.ai/api/coding/paas/v4").rstrip("/") + "/chat/completions"


def ask_zai(model, code, think=False):
    """One call to Z.ai's OpenAI-compatible endpoint, the one the VPS agent's coding plan pays for.

    Same shape as the OpenRouter call, two differences worth stating. Z.ai's switch for reasoning
    is `thinking: {type: disabled}`, not OpenRouter's `reasoning`; `max_tokens` stays as the second
    belt. And the response carries token counts but no price, because a coding plan is a quota, not
    a meter - the line records the tokens and says the cost basis is the plan. A 429 is the plan's
    quota, shared with the agent's own cron jobs, so the call waits and retries a few times rather
    than filing the case as unusable on the first refusal.
    """
    key = os.environ.get("GLM_API_KEY")
    if not key:
        raise RuntimeError("GLM_API_KEY is not set")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT + code[:24000]}],
        "temperature": 0,
    }
    if think:
        payload["thinking"] = {"type": "enabled"}
    # Same rule as OpenRouter since 2026-09-02: reasoning is the model's default and gets room.
    # (With `thinking.type: disabled` glm-5.3 obeyed on a trivial prompt and reasoned 1,734
    # characters anyway on the audit prompt, so "suppressed" was never a clean label here.)
    payload["max_tokens"] = 128000
    d = _post_with_ceiling_fallback(ZAI, payload, key)
    msg = (d.get("choices") or [{}])[0].get("message", {}) or {}
    u = d.get("usage") or {}
    return ((msg.get("content") or "").strip(),
            (msg.get("reasoning_content") or ""),
            (d.get("choices") or [{}])[0].get("finish_reason", ""),
            {"prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
             "cost_usd": None, "cost_basis": "z.ai coding plan quota, no per-call price",
             "reasoning": "requested" if think else "allowed", "max_tokens": payload.get("max_tokens")})


def ask_claude_code(model, code, think=False):
    """One call through the Claude Code CLI in headless mode (`claude -p`), paid by the
    subscription rather than by an API key.

    Two things make this a measurement rather than a chat. First, it runs from an empty
    directory with settings, MCP servers and tools switched off: on 2026-09-01 the same call made
    from the project directory carried 88,750 tokens of CLAUDE.md, memory and the skills list into
    the model's context - including this benchmark's own skills - before it judged the code. From
    a clean directory it carries about 3,300, which is the prompt. Second, effort is pinned to
    `max`: the owner's rule since 2026-09-02 is that a model that can think gets to think, and the
    calibration rows at effort `high` are kept beside this as the cheaper point. Thinking cannot be
    turned off on these models by any route, so `think` is ignored and the thinking token count is
    recorded instead. The cost recorded is the CLI's own estimate at API prices; what was actually
    paid is the subscription, and the line says so.
    """
    import subprocess, tempfile
    if not hasattr(ask_claude_code, "cwd"):
        ask_claude_code.cwd = tempfile.mkdtemp(prefix="model-audit-clean-")
    cmd = ["claude", "-p", "--model", model, "--output-format", "json", "--no-session-persistence",
           "--effort", "max", "--tools", "", "--setting-sources", "", "--strict-mcp-config",
           "--mcp-config", '{"mcpServers":{}}',
           "--system-prompt", "You answer with one JSON object and nothing else."]
    r = subprocess.run(cmd, input=PROMPT + code[:24000], capture_output=True, text=True,
                       encoding="utf-8", timeout=1800, cwd=ask_claude_code.cwd, shell=(os.name == "nt"))
    if r.returncode != 0 and not r.stdout.strip():
        raise RuntimeError(f"claude -p rc={r.returncode}: {r.stderr.strip()[:200]}")
    d = json.loads(r.stdout)
    u = d.get("usage") or {}
    ctx = (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0)
    stop = d.get("stop_reason") or d.get("subtype") or ""
    return ((d.get("result") or "").strip() if not d.get("is_error") else "",
            "",
            stop,
            {"prompt_tokens": ctx, "completion_tokens": u.get("output_tokens"),
             "thinking_tokens": (u.get("output_tokens_details") or {}).get("thinking_tokens"),
             "cost_usd": d.get("total_cost_usd"), "cost_basis": "api-equivalent estimate, paid by subscription",
             "effort": "max", "reasoning": "allowed", "is_error": bool(d.get("is_error")), "api_error_status": d.get("api_error_status")})


def ask(model, code, think=False):
    body = json.dumps({
        "model": model,
        "prompt": PROMPT + code[:24000],
        "stream": False,
        "think": think,
        "options": {"temperature": 0},
    }).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.loads(r.read())
    # With thinking on, ollama splits the reply: reasoning into `thinking`, the answer into
    # `response`. On a large real crate the 9b model spent its whole budget reasoning and returned
    # an EMPTY response, which the parser can only report as "no json" - indistinguishable from a
    # crash. Both fields and the stop reason are recorded so an empty answer is diagnosable as
    # "thought itself out of room" rather than filed as an unexplained failure.
    return ((d.get("response") or "").strip(), (d.get("thinking") or ""),
            d.get("done_reason", ""), {})


def verdict(raw):
    """Parse the model's answer. An unparseable answer is NOT a detection - it is recorded as such."""
    # The answer is one JSON object, but a model that writes a long `why` can put a brace inside
    # it (a code fragment, a struct literal), and the first `{`-to-first-`}` span is then not the
    # object. On 2026-09-02 Claude Fable 5.1 answered solend-owner-checks with a valid object whose
    # `why` did exactly that, and the old regex filed a real answer as "no json in response". So:
    # start at the first `{` and try every closing brace from the LAST one backwards; the first
    # span that parses is the object. An answer with no parseable span is still not a detection.
    start = raw.find("{")
    if start < 0:
        return None, "no json in response"
    d = None
    for end in range(len(raw) - 1, start, -1):
        if raw[end] != "}":
            continue
        try:
            d = json.loads(raw[start:end + 1])
            break
        except json.JSONDecodeError:
            continue
    if d is None:
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
    ap.add_argument("--provider", choices=("ollama", "openrouter", "claude-code", "zai"), default="ollama",
                    help="openrouter reads OPENROUTER_API_KEY from the environment and records the "
                         "real cost of every call; the key is never written anywhere")
    ap.add_argument("--think", action="store_true",
                    help="let the model reason before answering. Same model and same prompt with "
                         "this flag is a controlled comparison: the only variable is the thinking, "
                         "so a difference in the result is attributable to it and not to a model swap.")
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
    think_tag = ("-think" if args.think else "") + {"openrouter": "-or", "claude-code": "-cc", "zai": "-zai"}.get(args.provider, "")
    out_dir = ROOT / "raw" / f"model-{args.model.replace(':', '-').replace('/', '-')}{think_tag}-c{args.corpus}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log = (out_dir / "runs.jsonl").open("a", encoding="utf-8")

    print(f"model={args.model}  think={args.think}  corpus={args.corpus}  prompt={PROMPT_VERSION}  runs={args.runs}  cases={len(cases)}")
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
                    fn = {"openrouter": ask_openrouter, "claude-code": ask_claude_code, "zai": ask_zai}.get(args.provider, ask)
                    raw, thinking, done, usage = fn(args.model, code, think=args.think)
                    err = None
                except Exception as exc:  # noqa: BLE001
                    raw, thinking, done, usage, err = "", "", "", {}, f"{type(exc).__name__}"
                v, note = verdict(raw) if not err else (None, err)
                log.write(json.dumps({
                    "corpus": args.corpus, "case": c["name"], "class": c.get("class", ""),
                    "variant": variant, "run": i + 1,
                    "model": args.model, "prompt_version": PROMPT_VERSION, "think": args.think,
                    "vulnerable": v, "note": note, "sec": round(time.time() - t0, 1),
                    "raw": raw[:600] if v is not None else raw[:6000], "done_reason": done,
                    "thinking_chars": len(thinking), "thinking_tail": thinking[-300:],
                    "provider": args.provider, **usage,
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
    assert verdict('')[0] is None                                # an empty answer is not a verdict
    print("ok: prose and hedges are not detections, quoted booleans are")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        main()
