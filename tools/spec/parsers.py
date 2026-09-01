"""The parsers and writers: one entry per output shape this project has met."""
import re


# --------------------------------------------------------------------------- parsers
# One entry per output shape this project has met. The name is the same token `run_all.py` and
# `score2.load_findings` already use as `kind`, so a declaration cannot name a parser for its
# stored file that the scorer does not have. `test_all.py` asserts that correspondence.

def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_radar(blob):
    """[{name, locations: ["path:line:col-col", ...]}] - radar and X-Ray share this envelope."""
    out = []
    for item in blob or []:
        for loc in item.get("locations") or []:
            parts = str(loc).split(":")
            out.append({"rule_id": item.get("name", ""), "file": parts[0],
                        "line": _int(parts[1] if len(parts) > 1 else 0),
                        "col": _int(parts[2].split("-")[0] if len(parts) > 2 else 0)})
    return out


def parse_sol_audit(blob):
    """{"findings": [{rule_id, file, line}]} - sol-audit's and vaultlint's shape."""
    items = blob.get("findings") if isinstance(blob, dict) else blob
    return [{"rule_id": x.get("rule_id", ""), "file": x.get("file", ""),
             "line": _int(x.get("line")), "col": _int(x.get("col"))} for x in items or []]


def parse_semgrep(blob):
    """{"results": [{check_id, path, start: {line}}]}."""
    items = blob.get("results") if isinstance(blob, dict) else blob
    return [{"rule_id": r.get("check_id", ""), "file": r.get("path", ""),
             "line": _int((r.get("start") or {}).get("line")),
             "col": _int((r.get("start") or {}).get("col"))} for r in items or []]


def parse_solsec(blob):
    """{"analysis_results": [{rule_name, file_path, line_number}]}."""
    items = blob.get("analysis_results") if isinstance(blob, dict) else blob
    out = []
    for x in items or []:
        fp = str(x.get("file_path", ""))
        out.append({"rule_id": x.get("rule_name", ""), "file": fp[2:] if fp.startswith("./") else fp,
                    "line": _int(x.get("line_number")), "col": _int(x.get("column"))})
    return out


def parse_text_regex(text, patterns):
    """Human-readable diagnostics, the shape rustc-family and Starlark-rule tools emit.

    Two regexes and a scope rule, because sol-azy prints a summary table before the detail and a
    parser that reads both counts every finding twice:

        rule      matched against each line; the last match becomes the rule in force
        location  `path:line[:col]`, attributed to the rule in force
        begin_at  optional: ignore everything before this marker (sol-azy's "Detailed findings:")
    """
    rule_re = re.compile(patterns["rule"])
    loc_re = re.compile(patterns["location"])
    begin = patterns.get("begin_at")
    started = begin is None
    current, out = None, []
    for line in (text or "").splitlines():
        if not started:
            started = begin in line
            continue
        m = rule_re.search(line)
        if m:
            current = m.group(1).strip()
            continue
        m = loc_re.search(line.strip())
        if m and current is not None:
            out.append({"rule_id": current, "file": m.group(1), "line": _int(m.group(2)),
                        "col": _int(m.group(3)) if m.lastindex and m.lastindex >= 3 else 0})
    return out


PARSERS = {
    "radar": parse_radar,
    "xray": parse_radar,
    "sol-audit": parse_sol_audit,
    "vaultlint": parse_sol_audit,
    "semgrep": parse_semgrep,
    "solsec": parse_solsec,
    "text-regex": parse_text_regex,
}

# How to write findings back out in a tool's own envelope. `text-regex` has no writer: a tool that
# speaks prose is stored in the flat `sol-audit` envelope, which is what every text tool measured
# here has done, and the declaration says so rather than leaving it to be guessed.
WRITERS = {
    "radar": lambda fs: [{"name": f["rule_id"], "description": "", "severity": "", "certainty": "",
                          "locations": [f"{f['file']}:{f['line']}:{f['col']}"]} for f in fs],
    "xray": lambda fs: [{"name": f["rule_id"], "rule_name": f["rule_id"],
                         "locations": [f"{f['file']}:{f['line']}:{f['col']}"]} for f in fs],
    "sol-audit": lambda fs: {"findings": [{"rule_id": f["rule_id"], "file": f["file"],
                                           "line": f["line"], "col": f["col"]} for f in fs]},
    "vaultlint": lambda fs: {"findings": [{"rule_id": f["rule_id"], "file": f["file"],
                                           "line": f["line"], "col": f["col"]} for f in fs]},
    "semgrep": lambda fs: {"results": [{"check_id": f["rule_id"], "path": f["file"],
                                        "start": {"line": f["line"]},
                                        "end": {"line": f["line"]}} for f in fs]},
    "solsec": lambda fs: {"analysis_results": [{"rule_name": f["rule_id"], "file_path": f["file"],
                                                "line_number": f["line"],
                                                "column": f["col"]} for f in fs]},
}
