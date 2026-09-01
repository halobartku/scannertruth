"""The positive control: one planted finding carried from the parser to `detected`."""
import json
import os
import tempfile

from .parsers import PARSERS, WRITERS, parse_text_regex


# --------------------------------------------------------------------------- positive control

VULN = "use anchor_lang::prelude::*;\npub fn go() {\n    let x = read();\n}\n"
FIXED = "use anchor_lang::prelude::*;\npub fn go() {\n    require_owner();\n    let x = read();\n}\n"
CONTROL_CLASS = "account-data-matching"


def _synthetic_case(tmp):
    """A vulnerable/fixed pair whose fix inserts a guard at line 3, as score2.demo builds one."""
    case = os.path.join(tmp, "case")
    for variant, text in (("insecure", VULN), ("secure", FIXED)):
        sub = os.path.join(case, variant, "src")
        os.makedirs(sub)
        with open(os.path.join(sub, "lib.rs"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return case


def _fill(sample, path, line):
    if isinstance(sample, str):
        return sample.replace("{path}", path).replace("{line}", str(line))
    if isinstance(sample, list):
        return [_fill(x, path, line) for x in sample]
    if isinstance(sample, dict):
        return {k: _fill(v, path, line) for k, v in sample.items()}
    return sample


def _corpus1_control(spec, parsed, envelope, rule):
    """The same proof for a corpus-1 row, which is read and scored by different code.

    `score2` never sees a corpus-1 measurement: `run_all.extract` reads the file and `score.score`
    scores it. A control that only crossed the corpus-2 path would leave X-Ray, whose only row is
    on corpus 1, with no proof its parser can say yes at all.
    """
    import run_all
    import score
    name = spec["name"]
    findings = [{**f, "file": f"/c/1-{CONTROL_CLASS}/{'insecure' if i == 0 else 'secure'}/lib.rs"}
                for i, f in enumerate(parsed)]
    blob = WRITERS[envelope](findings[:1])
    pairs = run_all.extract(envelope, blob)
    assert pairs, f"{name}: run_all.extract({envelope!r}) read a one-finding file into nothing"
    rows = score.score(pairs, {f"1-{CONTROL_CLASS}": [rule]})
    got = {r[0]: (r[4], r[5]) for r in rows}
    assert got[f"1-{CONTROL_CLASS}"] == (True, True), (
        f"{name}: a finding on the vulnerable variant only scored {got}, not nominal and real")
    on_both = WRITERS[envelope]([findings[0],
                                 {**findings[0],
                                  "file": findings[0]["file"].replace("/insecure/", "/secure/")}])
    rows = score.score(run_all.extract(envelope, on_both), {f"1-{CONTROL_CLASS}": [rule]})
    got = {r[0]: (r[4], r[5]) for r in rows}
    assert got[f"1-{CONTROL_CLASS}"] == (True, False), (
        f"{name}: firing on the fixed variant too still scored real recall: {got}")


def positive_control(spec):
    """Plant one real finding at a fix site and prove this declaration can carry it to `detected`.

    It crosses everything between a scanner's mouth and a published verdict: this tool's parser,
    this tool's stored envelope, `score2.load_findings`, and `score2.score_case`. Then it plants
    the same finding on the fixed variant too and requires that the answer stops being `detected`,
    because a parser that loses the variant would turn every false positive into a detection.

    A declaration with corpus-1 rows additionally crosses `run_all.extract` and `score.score`,
    which is the other reader entirely.

    Returns a dict; raises AssertionError with the tool named if it cannot say yes.
    """
    import score2
    name, fmt, envelope = spec["name"], spec["output"]["format"], spec["envelope"]
    rule = spec["positive_control"]["rule_id"]
    mapping = {"1-" + CONTROL_CLASS: [rule]}
    rows = spec["measurements"] or [{"corpus": "corpus2", "envelope": envelope}]
    # Which readers do this declaration's rows actually go through? A control that crossed only
    # the corpus-2 path would leave X-Ray, whose only row is on corpus 1, with no proof at all,
    # and it would miss that vaultlint's two rows are stored in two different envelopes.
    c2_envelopes = sorted({r.get("envelope", envelope) for r in rows if r["corpus"] == "corpus2"})
    c1_envelopes = sorted({r.get("envelope", envelope) for r in rows if r["corpus"] == "corpus1"})

    with tempfile.TemporaryDirectory() as tmp:
        case = _synthetic_case(tmp)
        # Relative to the case's parent, which is what a scanner emits once the container prefix
        # has been rewritten off, and what `score2.resolve_in_case` resolves against. It also has
        # to be relative for a reason worth writing down: radar's envelope packs the location into
        # `path:line:col` and splits it on the colon, so a Windows absolute path with a drive
        # letter cannot survive that envelope at all. Every path this project stores is relative,
        # so this never bites in practice; an absolute one would fail the control on Windows for a
        # reason that has nothing to do with the parser under test.
        ins = "case/insecure/src/lib.rs"

        sample = _fill(spec["positive_control"]["sample"], ins, 3)
        parsed = (parse_text_regex(sample, spec["output"]["patterns"]) if fmt == "text-regex"
                  else PARSERS[fmt](sample))
        assert parsed, (
            f"{name}: its own positive-control sample parsed to nothing. The parser, not the "
            "scanner, decides every zero this declaration will ever produce.")
        assert any(f["rule_id"] == rule for f in parsed), (
            f"{name}: the sample parsed, but not to the rule id {rule!r} it declares: "
            f"{sorted({f['rule_id'] for f in parsed})}")

        for env in c2_envelopes:
            stored = os.path.join(tmp, f"stored-{env}.json")
            with open(stored, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(WRITERS[env](parsed), fh)
            found = score2.load_findings(env, stored)
            assert found, f"{name}: the {env} envelope wrote a file score2 parses into nothing"
            verdict, info = score2.score_case(case, CONTROL_CLASS, mapping, found)
            assert verdict == "detected", (
                f"{name} ({env}): a real finding at the fix site scored {verdict!r} "
                f"({info.get('reason', '')}). A silent parse regression would look exactly like a "
                "clean zero.")

            on_fix = [{**f, "file": f["file"].replace("/insecure/", "/secure/")} for f in parsed]
            both = os.path.join(tmp, f"both-{env}.json")
            with open(both, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(WRITERS[env](parsed + on_fix), fh)
            verdict2, _ = score2.score_case(case, CONTROL_CLASS, mapping,
                                            score2.load_findings(env, both))
            assert verdict2 != "detected", (
                f"{name} ({env}): the same rule firing on the FIXED variant too still scored "
                "`detected`. That is the whole difference between real recall and shape matching.")

            empty = os.path.join(tmp, f"empty-{env}.json")
            with open(empty, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(WRITERS[env]([]), fh)
            verdict3, _ = score2.score_case(case, CONTROL_CLASS, mapping,
                                            score2.load_findings(env, empty))
            assert verdict3 == "missed", f"{name} ({env}): an empty file scored {verdict3!r}"

    for env in c1_envelopes:
        _corpus1_control(spec, parsed, env, rule)

    return {"scanner": name, "format": fmt, "envelope": envelope, "rule_id": rule,
            "corpus1_envelopes": c1_envelopes, "corpus2_envelopes": c2_envelopes,
            "detected": True, "silent_on_the_fix": True}
