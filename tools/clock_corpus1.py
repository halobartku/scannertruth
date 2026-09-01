#!/usr/bin/env python3
"""Corpus-1 scoring for the clock: the derived source tables, the extractors and `measure`.

Moved out of `tools/run_all.py` on 2026-09-01 without changing a line of the code below. `run_all`
re-exports every name defined here, so `run_all.extract`, `run_all.measure`, `run_all.load_mapping`,
`run_all.SOURCES`, `run_all.SOURCES_CORPUS2`, `run_all.MAPPING_ALIAS` and `run_all.ROW_NOTES` all
keep working. The tables are derived here, in the module whose functions read them, rather than in
the facade, so that `scanner_spec`'s lazy `import run_all` does not become a real import cycle.
"""
import json
import os

from score import score

# Where each scanner's raw output is expected, how to pull (rule_id, path) pairs out of it, and
# which mapping scores it. All three used to be literals maintained here by hand. They are derived
# from `adapters/*.json` instead, so that adding a tool is a declaration rather than an edit in
# three places, and so that every row on the clock has a file behind it saying where the tool came
# from, how it was invoked, how a run that could not happen is told from a run that found nothing,
# and what its parser is. The long provenance notes that used to live in this file live in those
# declarations now, beside the tool they describe.
#
# `test_all.py` pins the derived tables against the literals they replaced, so this cannot move a
# published row without the suite naming the row.
#
# A row may still be scored with another row's mapping - that is how one tool appears twice, at
# two versions or under two invocations, without a mapping file being written after the fact. A
# mapping created to score a run that has already happened is not a pre-registration, and
# `tools/preregistration_check.py` cannot tell the difference, so the rule is kept by not creating
# the file at all: each measurement names the mapping it is scored with.
import scanner_spec  # noqa: E402

SOURCES, SOURCES_CORPUS2, MAPPING_ALIAS, ROW_NOTES = scanner_spec.clock_tables()


def extract(kind, blob):
    """Normalise a scanner's own JSON into (rule_id, path) pairs."""
    if kind == "radar":
        out = []
        for item in blob or []:
            for loc in item.get("locations") or []:
                out.append((item.get("name", ""), loc.split(":")[0]))
        return out
    if kind in ("vaultlint", "sol-audit"):
        findings = blob.get("findings") if isinstance(blob, dict) else blob
        return [(x.get("rule_id", ""), x.get("file", "")) for x in findings or []]
    if kind in ("xray", "solsec"):
        # solsec's own report is {"analysis_results": [{rule_name, file_path, line_number}]}.
        # The 2026-08-31 corpus-1 file had been converted into the {name, locations} envelope
        # X-Ray and Radar use, by a script that was not committed. Both shapes are read here, so
        # the tool's own output can be scored without a conversion step nobody can reproduce.
        if isinstance(blob, dict) and isinstance(blob.get("analysis_results"), list):
            out = []
            for item in blob["analysis_results"]:
                fp = str(item.get("file_path", ""))
                out.append((item.get("rule_name", ""), fp[2:] if fp.startswith("./") else fp))
            return out
        out = []
        for item in blob or []:
            for loc in item.get("locations") or []:
                out.append((item.get("name", ""), str(loc).split(":")[0]))
        return out
    if kind == "semgrep":
        return [(r.get("check_id", ""), r.get("path", ""))
                for r in (blob or {}).get("results", [])]
    raise ValueError(kind)


def load_mapping(name, mappings_dir="mappings"):
    name = MAPPING_ALIAS.get(name, name)
    with open(os.path.join(mappings_dir, f"{name}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def measure(raw_dir="raw", mappings_dir="mappings"):
    """Returns a list of per-scanner result dicts, including the ones we could not run."""
    results = []
    for name, (filename, kind) in sorted(SOURCES.items()):
        path = os.path.join(raw_dir, filename)
        if not os.path.exists(path):
            results.append({"scanner": name, "status": "unavailable",
                            "reason": f"no raw output at {path}"})
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                blob = json.load(fh)
            findings = extract(kind, blob)
            mapping = load_mapping(name, mappings_dir)
        except Exception as exc:
            results.append({"scanner": name, "status": "error", "reason": repr(exc)})
            continue

        rows = score(findings, mapping["map"])
        fixed = sum(1 for _, p in findings
                    if "/secure/" in p.replace("\\", "/") or "/recommended/" in p.replace("\\", "/"))
        results.append({
            "scanner": name,
            "status": "measured",
            "source": filename,
            "mapping": MAPPING_ALIAS.get(name, name),
            "classes": len(rows),
            "nominal": sum(1 for r in rows if r[4]),
            "real": sum(1 for r in rows if r[5]),
            "findings": len(findings),
            "findings_on_fixed_code": fixed,
            "per_class": {r[0]: {"insecure": r[1], "secure": r[2], "recommended": r[3],
                                 "nominal": r[4], "real": r[5]} for r in rows},
        })
    return results

