#!/usr/bin/env python3
"""Measure a model-backed auditor the way we measure a scanner, plus the thing that makes it hard.

    python tools/model_audit.py --model qwen3.5:9b --runs 3
    python tools/model_audit.py --model qwen3.5:9b --runs 1 --case anchor-interface-account
    python tools/model_audit.py --model claude-opus-5 --provider claude-code --corpus 2 --resume --stop-at 06:45

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

**A sweep can be finished in pieces.** `--resume` reopens the newest directory for the same model,
provider and corpus and skips every (case, variant, run) that already has an answer; a line the
provider refused (the subscription's 429, a harness exception) is treated as absent and the call is
made again, appended after the old line, which stays. `--max-calls N` and `--stop-at HH:MM` end the
sweep cleanly between calls, so a subscription window can be used at night and handed back at a
fixed time. `--parallel N` runs calls concurrently; each still writes its own line.

**No output ceiling by default since 2026-09-02.** The model's own maximum applies and the line
records `"ceiling": "model maximum"`. An explicit `--max-tokens N` sends a ceiling, records it, and
falls back to no ceiling where the provider refuses the value; the 128,000 rows of 2026-09-02 are
labelled on the line the same way.
"""
import argparse
import datetime as _dt
import json
import os
import pathlib
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

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


def _ceiling(requested, sent):
    """What the line says about the output ceiling. `requested` is what --max-tokens asked for,
    `sent` what the final successful call carried (None after a provider refused the value)."""
    if sent is not None:
        return f"{sent} tokens, explicit"
    if requested is not None:
        return f"model maximum (provider refused {requested})"
    return "model maximum"


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


def ask_openrouter(model, code, think=False, max_tokens=None):
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
    # if a model thinks, let it think, and record how much. The ceiling went 8,000 (glm-5.3 thought
    # 33,813 characters on wormhole-sysvar and hit it), then 128,000 at 01:40, then none at all
    # ("zwieksz wszystkim limit do maxa tokenow"). No `max_tokens` is sent unless --max-tokens asks
    # for one; a provider that rejects the value gets the call again with no ceiling, and the line
    # records which happened.
    payload["max_tokens"] = max_tokens
    d = _post_with_ceiling_fallback(OPENROUTER, payload, key)
    msg = (d.get("choices") or [{}])[0].get("message", {}) or {}
    u = d.get("usage") or {}
    return ((msg.get("content") or "").strip(),
            (msg.get("reasoning") or ""),
            (d.get("choices") or [{}])[0].get("finish_reason", ""),
            {"prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
             "cost_usd": u.get("cost"), "reasoning": "requested" if think else "allowed",
             "max_tokens": payload.get("max_tokens"), "ceiling": _ceiling(max_tokens, payload.get("max_tokens"))})


ZAI = os.environ.get("GLM_BASE_URL", "https://api.z.ai/api/coding/paas/v4").rstrip("/") + "/chat/completions"


def ask_zai(model, code, think=False, max_tokens=None):
    """One call to Z.ai's OpenAI-compatible endpoint, the one the VPS agent's coding plan pays for.

    Same shape as the OpenRouter call, two differences worth stating. Z.ai's switch for reasoning
    is `thinking: {type: disabled}`, not OpenRouter's `reasoning`; `max_tokens` is only sent when
    asked for. And the response carries token counts but no price, because a coding plan is a
    quota, not a meter - the line records the tokens and says the cost basis is the plan. A 429 is
    the plan's quota, shared with the agent's own cron jobs, so the call waits and retries a few
    times rather than filing the case as unusable on the first refusal.
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
    # Same rule as OpenRouter since 2026-09-02: reasoning is the model's default and gets room, and
    # since the same evening no ceiling at all unless --max-tokens asks for one. (With
    # `thinking.type: disabled` glm-5.3 obeyed on a trivial prompt and reasoned 1,734 characters
    # anyway on the audit prompt, so "suppressed" was never a clean label here.)
    payload["max_tokens"] = max_tokens
    d = _post_with_ceiling_fallback(ZAI, payload, key)
    msg = (d.get("choices") or [{}])[0].get("message", {}) or {}
    u = d.get("usage") or {}
    return ((msg.get("content") or "").strip(),
            (msg.get("reasoning_content") or ""),
            (d.get("choices") or [{}])[0].get("finish_reason", ""),
            {"prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
             "cost_usd": None, "cost_basis": "z.ai coding plan quota, no per-call price",
             "reasoning": "requested" if think else "allowed",
             "max_tokens": payload.get("max_tokens"), "ceiling": _ceiling(max_tokens, payload.get("max_tokens"))})


_CWD_LOCK = threading.Lock()


def ask_claude_code(model, code, think=False, max_tokens=None):
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
    recorded instead. The CLI exposes no output ceiling either, so `max_tokens` is ignored and the
    line says the ceiling is the model's maximum. The cost recorded is the CLI's own estimate at
    API prices; what was actually paid is the subscription, and the line says so. When the
    subscription window is exhausted the CLI returns `is_error: true` with `api_error_status: 429`
    and an empty result; the line keeps both fields, and that is what `--resume` looks for.
    """
    import subprocess, tempfile
    with _CWD_LOCK:
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
             "effort": "max", "reasoning": "allowed", "max_tokens": None, "ceiling": "model maximum",
             "is_error": bool(d.get("is_error")), "api_error_status": d.get("api_error_status")})


def ask(model, code, think=False, max_tokens=None):
    body = json.dumps({
        "model": model,
        "prompt": PROMPT + code[:24000],
        "stream": False,
        "think": think,
        # -1 is ollama's "no limit"; the model's own maximum applies unless --max-tokens asks for less.
        "options": {"temperature": 0, "num_predict": -1 if max_tokens is None else max_tokens},
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
            d.get("done_reason", ""), {"max_tokens": max_tokens, "ceiling": _ceiling(max_tokens, max_tokens)})


ASK = {"openrouter": ask_openrouter, "claude-code": ask_claude_code, "zai": ask_zai, "ollama": ask}


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


# ----------------------------------------------------------------- resume
def refused(line):
    """True when a null-verdict line is the provider or the harness refusing, not the model
    answering. The Claude Code subscription's exhausted window is `is_error: true` with
    `api_error_status: 429` and an empty `raw` (every such line on 2026-09-01/02 looks like that);
    a harness exception leaves the exception's class name in `note`; a provider that says so in
    words leaves "limit" or "usage" in `raw`. "Could not run" and "found nothing" must stay
    different observations, so these lines are re-done and a model's own unusable answer is not."""
    if line.get("vulnerable") is not None:
        return False
    if line.get("is_error") or line.get("api_error_status") is not None:
        return True
    if re.fullmatch(r"\w*(Error|Exception)", line.get("note") or ""):
        return True
    text = (line.get("raw") or "").lower()
    return "limit" in text or "usage" in text


def completed(path):
    """Every (case, variant, run) an existing runs.jsonl already answers, with the verdict to reuse.
    A line with a verdict wins over any other line for the same key; a null line counts only when
    it is the model's own unusable answer (see `refused`)."""
    done = {}
    if not pathlib.Path(path).is_file():
        return done
    for l in open(path, encoding="utf-8"):
        if not l.strip():
            continue
        x = json.loads(l)
        key = (x["case"], x["variant"], x.get("run", 1))
        if x.get("vulnerable") is not None:
            done[key] = (x["vulnerable"], x.get("note", ""))
        elif not refused(x):
            done.setdefault(key, (None, x.get("note", "")))
    return done


def newest_sweep_dir(prefix):
    """The newest `raw/<prefix>-<date>` that is a sweep, so `--resume` continues the existing
    directory for this model, provider and corpus instead of opening one for today. `-partial` and
    `-calibration` directories are never sweeps and are never resumed."""
    cands = [p for p in (ROOT / "raw").glob(prefix + "-*")
             if p.is_dir() and not p.name.endswith(("-partial", "-calibration"))]
    return max(cands, key=lambda p: p.name) if cands else None


def parse_stop_at(hhmm, now=None):
    """`--stop-at HH:MM` is today's HH:MM, local time. If it has already passed the sweep makes no
    call at all: a window that crosses midnight is deliberately not guessed, because a sweep launched
    late (a laptop that woke at 07:30 for a 03:00 task) must not run into the working day."""
    now = now or _dt.datetime.now()
    t = _dt.datetime.strptime(hhmm, "%H:%M").time()
    return _dt.datetime.combine(now.date(), t)


# ----------------------------------------------------------------- the sweep
def sweep(jobs, fn, log_path, meta, runs, existing=None, parallel=1, max_calls=None, deadline=None,
          out=print):
    """Run every job not already answered, one JSON line per call, and classify each case once all
    its runs are in. `jobs` is a list of (case dict, variant, run, code). Returns the tallies.

    With `parallel` > 1 the calls go through a thread pool; the file write and the tallies sit
    behind one lock, so lines never interleave and a case is classified exactly once, after its last
    run. Line order in the file may then differ from case order, which scoring does not depend on.
    `max_calls` and `deadline` are checked before each call starts, never during one: a call that is
    in flight finishes and writes its line, a call that has not started is not made, and nothing
    partial is ever written.
    """
    existing = existing or {}
    lock = threading.Lock()
    tally = {}
    for c, variant, run, _ in jobs:
        tally.setdefault(c["name"], {"case": c, "hits": {"insecure": 0, "secure": 0}, "named": {},
                                     "bad": 0, "answered": 0, "planned": 0, "printed": False})["planned"] += 1
    state = {"calls": 0, "skipped": 0, "stop": None}
    totals = {"detected": 0, "both": 0, "neither": 0, "missed": 0, "unusable": 0}

    def classify(name):
        t = tally[name]
        c, hits, bad = t["case"], t["hits"], t["bad"]
        # Real recall: it must fire on the vulnerable program AND stay silent on the fixed one.
        # "Fires on both" is the model-shaped version of the noisy control, and it is not a detection.
        fires_vuln = hits["insecure"] > 0
        fires_fixed = hits["secure"] > 0
        if bad == runs * 2:
            mark, totals["unusable"] = "UNUSABLE", totals["unusable"] + 1
        elif fires_vuln and not fires_fixed:
            # A static scanner is credited only when its MAPPED rule fires, not when any rule does.
            # A model always supplies a reason, and the reason can be wrong while the verdict is
            # right - on 2026-09-01 qwen3.5:9b called an account-data-matching bug "Reentrancy" and
            # would have scored a detection. So the class it named is carried through here and the
            # verdict alone is not enough. Agreement is adjudicated by hand in mappings/, never by
            # string equality, because "Integer Overflow" and "arithmetic-rounding-drain" are close
            # enough to argue about and that argument must happen in the open.
            mark = f"verdict only, named \"{t['named'].get('insecure', '')}\" for class {c.get('class', '')}"
            totals["detected"] += 1
        elif fires_vuln and fires_fixed:
            mark, totals["both"] = "fires on the fix too", totals["both"] + 1
        elif not fires_vuln and not fires_fixed:
            mark, totals["neither"] = "silent on both", totals["neither"] + 1
        else:
            mark, totals["missed"] = "only on the fixed one", totals["missed"] + 1
        t["printed"] = True
        out(f"  {c['name']:38s} vuln {hits['insecure']}/{runs}  fixed {hits['secure']}/{runs}  {mark}")

    def record(name, variant, v, note):
        """Under the lock: one answer into the case's tallies; classify when the case is complete."""
        t = tally[name]
        t["answered"] += 1
        if v is None:
            t["bad"] += 1
        elif v:
            t["hits"][variant] += 1
            t["named"].setdefault(variant, note)
        if t["answered"] == t["planned"]:
            classify(name)

    # Answers already on file are reused, and say so, before any call is made.
    todo = []
    skipped_by = {}
    for c, variant, run, code in jobs:
        key = (c["name"], variant, run)
        if key in existing:
            v, note = existing[key]
            state["skipped"] += 1
            skipped_by.setdefault((c["name"], variant), []).append(run)
            record(c["name"], variant, v, note)
        else:
            todo.append((c, variant, run, code))
    for (name, variant), rs in skipped_by.items():
        out(f"  skip  {name}/{variant}  run {','.join(str(r) for r in rs)}  (already answered)")

    log = open(log_path, "a", encoding="utf-8")

    def one(job):
        c, variant, run, code = job
        with lock:
            if state["stop"] is None:
                if max_calls is not None and state["calls"] >= max_calls:
                    state["stop"] = f"--max-calls {max_calls} reached"
                elif deadline is not None and _dt.datetime.now() >= deadline:
                    state["stop"] = f"--stop-at {deadline.strftime('%H:%M')} reached"
            if state["stop"] is not None:
                return
            state["calls"] += 1
        t0 = time.time()
        try:
            raw, thinking, done, usage = fn(meta["model"], code, think=meta["think"], max_tokens=meta["max_tokens"])
            err = None
        except Exception as exc:  # noqa: BLE001
            raw, thinking, done, usage, err = "", "", "", {}, f"{type(exc).__name__}"
        v, note = verdict(raw) if not err else (None, err)
        line = json.dumps({
            "corpus": meta["corpus"], "case": c["name"], "class": c.get("class", ""),
            "variant": variant, "run": run,
            "model": meta["model"], "prompt_version": PROMPT_VERSION, "think": meta["think"],
            "vulnerable": v, "note": note, "sec": round(time.time() - t0, 1),
            "raw": raw[:600] if v is not None else raw[:6000], "done_reason": done,
            "thinking_chars": len(thinking), "thinking_tail": thinking[-300:],
            "provider": meta["provider"], **usage,
        }, ensure_ascii=False) + "\n"
        with lock:
            log.write(line)
            log.flush()
            record(c["name"], variant, v, note)

    try:
        if parallel > 1:
            with ThreadPoolExecutor(max_workers=parallel) as pool:
                list(pool.map(one, todo))
        else:
            for job in todo:
                one(job)
    finally:
        log.close()

    for name, t in tally.items():
        if not t["printed"]:
            out(f"  {name:38s} STOPPED with {t['answered']} of {t['planned']} runs answered; not classified")
    planned = len(jobs)
    remaining = planned - state["skipped"] - state["calls"]
    out(f"\n  calls made now {state['calls']}, reused from file {state['skipped']}, "
        f"still to do {remaining} of {planned} planned" + (f"  [stopped: {state['stop']}]" if state["stop"] else ""))
    return {**totals, **state, "remaining": remaining, "planned": planned}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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
    ap.add_argument("--max-tokens", type=int, default=None,
                    help="send an explicit output ceiling. Default: none, the model's own maximum; "
                         "the line records which. A provider that refuses the value gets the call "
                         "again with no ceiling and the line says so.")
    ap.add_argument("--resume", action="store_true",
                    help="continue the newest existing directory for this model, provider and corpus: "
                         "skip every (case, variant, run) that already has an answer, re-do the ones "
                         "the provider refused (subscription 429, harness exception), append.")
    ap.add_argument("--max-calls", type=int, default=None,
                    help="stop cleanly after this many calls have been started")
    ap.add_argument("--stop-at", default=None, metavar="HH:MM",
                    help="stop cleanly once local time reaches HH:MM today; no new call starts after "
                         "it, a call in flight finishes and writes its line. Already past: no call.")
    ap.add_argument("--parallel", type=int, default=1,
                    help="calls in flight at once, each still one line. Suggested: 6 for openrouter, "
                         "3 for zai (its plan quota answers 429, the retry handles it), 2 for "
                         "claude-code (the subscription window), 1 for ollama.")
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
    prefix = f"model-{args.model.replace(':', '-').replace('/', '-')}{think_tag}-c{args.corpus}"
    out_dir = newest_sweep_dir(prefix) if args.resume else None
    if args.resume and out_dir is None:
        print(f"nothing to resume under raw/{prefix}-*; starting a fresh directory")
    out_dir = out_dir or ROOT / "raw" / f"{prefix}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = completed(out_dir / "runs.jsonl") if args.resume else {}

    deadline = parse_stop_at(args.stop_at) if args.stop_at else None

    print(f"model={args.model}  think={args.think}  corpus={args.corpus}  prompt={PROMPT_VERSION}  runs={args.runs}  cases={len(cases)}"
          f"  parallel={args.parallel}  ceiling={'model maximum' if args.max_tokens is None else args.max_tokens}")
    print(f"artefacts: {out_dir}" + (f"  (resumed: {len(existing)} answers on file)" if args.resume else ""))
    if deadline:
        print(f"stop-at: {deadline:%Y-%m-%d %H:%M} local" + ("  (already passed, no call will be made)" if _dt.datetime.now() >= deadline else ""))
    if args.max_calls is not None:
        print(f"max-calls: {args.max_calls}")
    print()

    jobs = []
    for c in cases:
        case_dir = root / c["name"]
        if not (case_dir / "insecure").is_dir() or not (case_dir / "secure").is_dir():
            print(f"  {c['name']:38s} SKIP (no vulnerable/fixed pair built)")
            continue
        for variant in ("insecure", "secure"):
            code = sources(case_dir, variant)
            for i in range(args.runs):
                jobs.append((c, variant, i + 1, code))

    meta = {"model": args.model, "provider": args.provider, "corpus": args.corpus, "think": args.think,
            "max_tokens": args.max_tokens}
    r = sweep(jobs, ASK[args.provider], out_dir / "runs.jsonl", meta, args.runs, existing=existing,
              parallel=args.parallel, max_calls=args.max_calls, deadline=deadline)

    n = r["detected"] + r["both"] + r["neither"] + r["missed"] + r["unusable"]
    # NOT "real detections". This counts cases where the verdict was right on both variants, which
    # is necessary and not sufficient. Whether it is a detection depends on the class named being
    # the class present, and that is adjudicated by hand. Calling this line "real detections" on
    # 2026-09-01 would have published 2/17 for a model that named Reentrancy for an
    # account-data-matching bug - the exact overclaim this project exists to catch.
    print(f"\n  verdict right on both variants (necessary, not sufficient): {r['detected']} / {n}")
    print("    ^ each one still needs its named class adjudicated against the real class above")
    print(f"  fires on the fix too (no detection):                    {r['both']}")
    print(f"  silent on both:                                        {r['neither']}")
    print(f"  only on the fixed variant:                             {r['missed']}")
    print(f"  unusable answers:                                      {r['unusable']}")
    if r["remaining"]:
        print(f"  NOT a complete sweep: {r['remaining']} calls still to do; run again with --resume")
    print(f"\n  per-run log: {out_dir / 'runs.jsonl'}")


def demo():
    """Self-check: the verdict parser must accept what a model actually returns and refuse the rest;
    resume must reuse an answer and re-do a refusal; a parallel sweep must write every line whole."""
    import tempfile
    assert verdict('{"vulnerable": true, "class": "missing signer", "why": "x"}')[0] is True
    assert verdict('sure!\n{"vulnerable": false, "class": "", "why": "looks fixed"}\n')[0] is False
    assert verdict('{"vulnerable": "true"}')[0] is True          # models quote booleans
    assert verdict('I think it might be unsafe')[0] is None      # prose is not a verdict
    assert verdict('{"vulnerable": "maybe"}')[0] is None         # neither is a hedge
    assert verdict('{broken')[0] is None
    assert verdict('')[0] is None                                # an empty answer is not a verdict
    print("ok: prose and hedges are not detections, quoted booleans are")

    # --resume on a file with one answer and one subscription refusal, shaped like the real lines
    # of 2026-09-02: the refusal is is_error/429 with an empty raw. One skip, one re-do.
    d = pathlib.Path(tempfile.mkdtemp(prefix="model-audit-demo-"))
    log = d / "runs.jsonl"
    base = {"corpus": "2", "model": "demo", "provider": "claude-code", "run": 1}
    log.write_text(
        json.dumps({**base, "case": "a", "variant": "insecure", "vulnerable": True, "note": "signer", "raw": '{"vulnerable": true}'}) + "\n"
        + json.dumps({**base, "case": "a", "variant": "secure", "vulnerable": None, "note": "no json in response",
                      "raw": "", "is_error": True, "api_error_status": 429}) + "\n"
        + json.dumps({**base, "case": "b", "variant": "insecure", "vulnerable": None, "note": "no json in response",
                      "raw": "You have reached your usage limit for this window"}) + "\n"
        + json.dumps({**base, "case": "b", "variant": "secure", "vulnerable": None, "note": "no json in response",
                      "raw": "I would rather not say, this is ordinary code."}) + "\n", encoding="utf-8")
    done = completed(log)
    assert ("a", "insecure", 1) in done and done[("a", "insecure", 1)] == (True, "signer"), done   # the skip
    assert ("a", "secure", 1) not in done, done                                                    # the re-do (429)
    assert ("b", "insecure", 1) not in done, done                                                  # the re-do (limit text)
    assert ("b", "secure", 1) in done and done[("b", "secure", 1)][0] is None, done                # the model's own miss stays
    cases = [{"name": "a", "class": "x"}, {"name": "b", "class": "y"}]
    jobs = [(c, v, 1, "code") for c in cases for v in ("insecure", "secure")]
    printed = []
    calls = []
    lock = threading.Lock()

    def stub(model, code, think=False, max_tokens=None):
        with lock:
            calls.append(threading.get_ident())
        time.sleep(0.05)
        return '{"vulnerable": false, "class": "", "why": "stub"}', "", "stop", {"max_tokens": max_tokens, "ceiling": "model maximum"}

    meta = {"model": "demo", "provider": "claude-code", "corpus": "2", "think": False, "max_tokens": None}
    r = sweep(jobs, stub, log, meta, 1, existing=done, parallel=2, out=printed.append)
    assert r["skipped"] == 2 and r["calls"] == 2 and r["remaining"] == 0, r
    assert sum("skip" in p for p in printed) == 2, printed
    assert len(set(calls)) == 2, "parallel=2 should have used two threads"
    lines = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 6, len(lines)                          # 4 old lines stay, 2 new appended
    new = {(x["case"], x["variant"]) for x in lines[4:]}
    assert new == {("a", "secure"), ("b", "insecure")}, new
    assert all(x["vulnerable"] is False and x["ceiling"] == "model maximum" for x in lines[4:])
    print("ok: resume reuses an answer, re-does a 429 and a limit message, keeps a model's own miss")

    # --max-calls stops between calls: one line written, the other job never started.
    r = sweep(jobs[:2], stub, d / "capped.jsonl", meta, 1, max_calls=1, out=printed.append)
    assert r["calls"] == 1 and r["remaining"] == 1 and "max-calls" in r["stop"], r
    assert len((d / "capped.jsonl").read_text(encoding="utf-8").splitlines()) == 1
    # --stop-at in the past makes no call at all; the file stays empty.
    r = sweep(jobs[:2], stub, d / "late.jsonl", meta, 1,
              deadline=_dt.datetime.now() - _dt.timedelta(minutes=1), out=printed.append)
    assert r["calls"] == 0 and "stop-at" in r["stop"], r
    assert (d / "late.jsonl").read_text(encoding="utf-8") == ""
    assert parse_stop_at("06:45").time() == _dt.time(6, 45)
    print("ok: --max-calls and --stop-at end the sweep between calls, nothing partial on disk")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("demo", "--demo"):
        demo()
    else:
        main()
