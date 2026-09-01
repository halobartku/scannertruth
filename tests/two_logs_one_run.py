# ------------------------------------------- two logs for one run, 2026-09-01, error 32

def _parse_percase_text_log(path):
    """The human-readable per-case log: `<case> <variant> <ok|UNAVAILABLE> rc=N [findings=N]`."""
    import io as _io
    out = {}
    for line in _io.open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or line.endswith("_DONE"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        case, variant, status = parts[0], parts[1], parts[2]
        if variant not in ("insecure", "secure", "recommended"):
            continue
        out[f"{case}/{variant}"] = "ok" if status == "ok" else "unavailable"
    return out


def _parse_percase_json_log(path):
    import io as _io, json as _json
    return {str(e.get("leaf", "")): ("ok" if e.get("status") == "ok" else "unavailable")
            for e in _json.load(_io.open(path, encoding="utf-8"))}


# Every scanner that has both a human log and the machine log that actually scores.
_PAIRED_LOGS = [
    ("radar", "raw/c2-radar-percase.log", "raw/c2-radar-complete.json.log"),
    ("vaultlint", "raw/c2-vaultlint-percase.log", "raw/c2-vaultlint-complete.json.log"),
]


def test_the_two_logs_for_one_run_agree_on_every_leaf():
    """A run is recorded twice: once for a person and once for the scorer. Until 2026-09-01
    nothing compared them, and they disagreed.

    `raw/c2-radar-percase.log` line 1 said Radar's `anchor-interface-account/insecure` was
    `UNAVAILABLE`; `raw/c2-radar-complete.json.log`, the log `run_all.py` treats as the
    authority on which cases were analysed, said `{status: ok, findings: 0}`. One of the two
    was wrong for a full day and nothing in the repository could tell which. That is the
    whole point of writing a fact down twice.

    Which one was wrong is recorded as error 32 and is not the point of this check. The point
    is that two records of one run must never be allowed to disagree in silence again."""
    import os
    for scanner, text_log, json_log in _PAIRED_LOGS:
        if not (os.path.exists(text_log) and os.path.exists(json_log)):
            continue
        a = _parse_percase_text_log(text_log)
        b = _parse_percase_json_log(json_log)
        assert a, f"{text_log} parsed to nothing; the check would pass vacuously"
        assert set(a) == set(b), (
            f"{scanner}: the two logs cover different leaves. "
            f"only in {text_log}: {sorted(set(a) - set(b))}; "
            f"only in {json_log}: {sorted(set(b) - set(a))}")
        disagree = {k: (a[k], b[k]) for k in a if a[k] != b[k]}
        assert not disagree, (
            f"{scanner}: the human log and the log that scores disagree about whether a run "
            f"happened: {disagree}. One of them is wrong, and until this check existed nothing "
            "said which. 'Could not run' and 'found nothing' are different observations and a "
            "denominator depends on the difference.")


def test_radars_run_log_is_corroborated_by_radars_own_output():
    """A log is only evidence if something outside the log agrees with it.

    `raw/radar-c2-2026-08-31-stdout/` holds radar's own stdout for all 18 runs of the
    2026-08-31 corpus-2 measurement, recovered on 2026-09-01. radar prints `Scanned N file`
    and `radar completed successfully` for a run that happened, and it writes **no output
    file at all** when it finds nothing, which is exactly why the runner's
    file-exists-therefore-it-ran test could not tell a clean zero from a failure.

    So the run log is checked against the tool's own account of what it did, rather than
    against the artefact whose absence caused the defect."""
    import io as _io, os, re
    d = "raw/radar-c2-2026-08-31-stdout"
    if not os.path.isdir(d):
        raise AssertionError(
            f"{d} is missing: radar's own account of the 18 runs behind the published "
            "corpus-2 result is the evidence that they happened")
    logged = _parse_percase_json_log("raw/c2-radar-complete.json.log")
    seen = {}
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".log"):
            continue
        s = re.sub(r"\x1b\[[0-9;]*m", "",
                   _io.open(os.path.join(d, fn), encoding="utf-8", errors="replace").read())
        leaf = fn[:-4].replace(".", "/", 1)
        scanned = re.search(r"Scanned (\d+) file", s)
        ran = bool(scanned) and int(scanned.group(1)) > 0 and \
            "radar completed successfully" in s
        seen[leaf] = ran
    assert set(seen) == set(logged), (
        f"stdout artefacts and the run log cover different leaves: "
        f"{sorted(set(seen) ^ set(logged))}")
    for leaf, ran in sorted(seen.items()):
        assert ran == (logged[leaf] == "ok"), (
            f"{leaf}: the run log says {logged[leaf]!r} but radar's own stdout says "
            f"{'it scanned files and completed' if ran else 'it did not'}")
