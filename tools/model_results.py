#!/usr/bin/env python3
"""Derive the model-auditor results table from the per-invocation artefacts, never by hand.

Usage:
    python tools/model_results.py            # markdown table of every raw/model-*/runs.jsonl
    python tools/model_results.py --demo     # self-check on a synthetic log

One row per (model, provider, corpus, regime) directory. A directory whose name carries -partial or
-calibration is listed as such and never scored as a sweep. "Verdict right" is the tool's own
necessary-not-sufficient count: fires on at least one valid run of the vulnerable variant, silent on
every valid run of the fixed one; the class the model named still has to be adjudicated by hand,
and that adjudication is read from mappings/model-classes.json into the "detections after
adjudication" column: strict counts the cases whose named class was adjudicated `counts`, lenient
adds the `disputed` ones. A verdict-right case the mapping does not carry is shown as not
adjudicated rather than counted either way. Cost is the sum of `cost_usd` on the lines: real money
for OpenRouter, an API-price estimate paid by the subscription for claude-code, none for ollama and
the Z.ai plan.

ponytail: a directory is one sweep; the case list per corpus is read from the lines themselves,
so an interrupted sweep shows as done/expected with expected taken from the manifest (corpus 2)
or 11 cases (corpus 1), 2 variants, and the max run number seen.
"""
import glob
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def expected_calls(corpus, runs):
    if corpus == "1":
        cases = 11
    else:
        m = json.loads((ROOT / "corpus2" / "manifest.json").read_text(encoding="utf-8"))
        cases = sum(1 for c in m["cases"] if c.get("valid", True))
    return cases * 2 * runs


def summarise(path):
    lines = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    if not lines:
        return None
    first = lines[0]
    runs = max(x.get("run", 1) for x in lines)
    regime = first.get("reasoning") or ("requested" if first.get("think") else "suppressed")
    if (first.get("provider") or "ollama") == "claude-code":
        regime = f"effort {first.get('effort', '?')}"
    by_case = {}
    for x in lines:
        by_case.setdefault(x["case"], {"insecure": [], "secure": []})[x["variant"]].append(x.get("vulnerable"))
    right_cases = []
    for c, v in by_case.items():
        ins = [a for a in v["insecure"] if a is not None]
        sec = [a for a in v["secure"] if a is not None]
        if ins and sec and any(ins) and not any(sec):
            right_cases.append(c)
    right = len(right_cases)
    exp = expected_calls(first.get("corpus", "2"), runs)
    return {
        "dir": os.path.basename(os.path.dirname(path)),
        "model": first.get("model"), "provider": first.get("provider") or "ollama",
        "corpus": first.get("corpus"), "regime": regime, "max_tokens": first.get("max_tokens"),
        "done": len(lines), "expected": exp, "complete": len(lines) >= exp,
        "verdict_right": right, "right_cases": sorted(right_cases), "cases_seen": len(by_case),
        "unusable": sum(1 for x in lines if x.get("vulnerable") is None),
        "thinking_calls": sum(1 for x in lines if (x.get("thinking_chars") or 0) > 0),
        "cost": round(sum(float(x.get("cost_usd") or 0) for x in lines), 3),
        "prompt": first.get("prompt_version"),
    }


def load_adjudication(path=ROOT / "mappings" / "model-classes.json"):
    """{directory: {case: verdict}} from the hand adjudication; empty if the file is absent."""
    if not pathlib.Path(path).exists():
        return {}
    out = {}
    for c in json.loads(pathlib.Path(path).read_text(encoding="utf-8"))["cases"]:
        out.setdefault(c["dir"], {})[c["case"]] = c["verdict"]
    return out


def adjudicate(row, adjudication):
    """Strict and lenient detections for one row, plus the verdict-right cases nobody adjudicated."""
    if "partial" in row["dir"] or "calibration" in row["dir"]:
        return {"strict": None, "lenient": None, "unadjudicated": 0, "text": "not a sweep"}
    verdicts = adjudication.get(row["dir"], {})
    strict = sum(1 for c in row["right_cases"] if verdicts.get(c) == "counts")
    lenient = strict + sum(1 for c in row["right_cases"] if verdicts.get(c) == "disputed")
    missing = sum(1 for c in row["right_cases"] if c not in verdicts)
    text = f"{strict} / {lenient}"
    if missing:
        text += f" ({missing} not adjudicated)"
    return {"strict": strict, "lenient": lenient, "unadjudicated": missing, "text": text}


def table(rows, adjudication=None):
    if adjudication is None:
        adjudication = load_adjudication()
    out = ["| directory | model | provider | corpus | regime | calls | verdict right (necessary, not sufficient) | detections after adjudication (strict / lenient) | unusable | reasoned | cost USD |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        status = "complete" if r["complete"] else f"IN PROGRESS {r['done']}/{r['expected']}"
        flag = " (partial, not a sweep)" if "partial" in r["dir"] else " (calibration)" if "calibration" in r["dir"] else ""
        adj = adjudicate(r, adjudication)["text"]
        out.append(f"| `{r['dir']}` | {r['model']} | {r['provider']} | {r['corpus']} | {r['regime']}{flag} | {status} | "
                   f"{r['verdict_right']} / {r['cases_seen']} seen | {adj} | {r['unusable']} | {r['thinking_calls']} | {r['cost']} |")
    return "\n".join(out)


def demo():
    import tempfile
    d = pathlib.Path(tempfile.mkdtemp()) / "model-demo-or-c2-2026-01-01"
    d.mkdir()
    rows = []
    for case, ins, sec in [("a", True, False), ("b", True, True), ("c", None, False),
                           ("d", True, False), ("e", True, False)]:
        for variant, verdict in (("insecure", ins), ("secure", sec)):
            rows.append({"corpus": "2", "case": case, "variant": variant, "run": 1, "model": "demo",
                         "provider": "openrouter", "vulnerable": verdict, "cost_usd": 0.5, "reasoning": "allowed"})
    (d / "runs.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    s = summarise(str(d / "runs.jsonl"))
    assert s["verdict_right"] == 3 and s["right_cases"] == ["a", "d", "e"], s   # fires on vulnerable, silent on fixed
    assert s["unusable"] == 1 and s["cost"] == 5.0 and s["regime"] == "allowed" and not s["complete"], s
    # One named class that counts, one that does not, one disputed: strict 1, lenient 2, and a
    # verdict-right case the mapping has not seen is reported, never counted.
    adjudication = {d.name: {"a": "counts", "d": "no", "e": "disputed"}}
    adj = adjudicate(s, adjudication)
    assert (adj["strict"], adj["lenient"], adj["unadjudicated"]) == (1, 2, 0), adj
    assert adjudicate(s, {d.name: {"a": "counts"}})["text"] == "1 / 1 (2 not adjudicated)"
    assert "| 1 / 2 |" in table([s], adjudication)
    print("model_results: OK")


def main():
    if "--demo" in sys.argv:
        return demo()
    rows = [s for s in (summarise(p) for p in sorted(glob.glob(str(ROOT / "raw" / "model-*" / "runs.jsonl")))) if s]
    print(table(rows))


if __name__ == "__main__":
    main()
