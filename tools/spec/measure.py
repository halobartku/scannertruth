"""The corpora, and a whole measurement over one of them with its determinism verdict."""
import json
import os

from . import ROOT
from .parsers import WRITERS
from .run import run_leaf


# --------------------------------------------------------------------------- corpora

def corpus_leaves(corpus, root=None, manifest=None, path_prefix=None, variants=None):
    """(leaf, directory, path_prefix) per case per variant, read from disk and the manifest.

    The corpus-2 case count is read from the manifest on every call and never written down. It was
    9, then 16, then 17, and it changed under a measurement once already: B3's sweep started
    against 9 built cases and finished against 17, and only a digest taken before the run caught
    it. A framework that hard-codes the number would publish the drift as a result.
    """
    if corpus == "corpus2":
        root = root or os.path.join(ROOT, "corpus2")
        manifest = manifest or os.path.join(root, "manifest.json")
        path_prefix = path_prefix or "corpus2"
        variants = variants or ("insecure", "secure")
        with open(manifest, encoding="utf-8") as fh:
            cases = json.load(fh)["cases"]
        out = []
        for case in cases:
            if not case.get("valid", True):
                continue
            for variant in variants:
                d = os.path.join(root, case["name"], variant)
                if os.path.isdir(d):
                    out.append((f"{case['name']}/{variant}", d,
                                f"{path_prefix}/{case['name']}/{variant}"))
        return out

    # Corpus 1 is not committed here; it is fetched at its pinned commit and its classes are the
    # directories under programs/. Same rule: enumerate, never assume - and that means the
    # variants too. `9-closing-accounts` ships five (`insecure-still` and `insecure-still-still`
    # as well as the usual three), so a hard-coded triple recorded 33 invocations where the runs
    # already published record 35, and the two directories it skipped left no trace of having
    # been skipped. `score.variant_of` ignores those two either way, which is exactly why a
    # run log has to say the corpus has them rather than quietly agreeing with the scorer.
    if not root:
        raise ValueError("corpus1 is not in this repository; pass --corpus-root to the checkout")
    path_prefix = path_prefix or "/tmp/sealevel-attacks/programs"
    out = []
    for cls in sorted(os.listdir(root)):
        if not os.path.isdir(os.path.join(root, cls)):
            continue
        for variant in sorted(os.listdir(os.path.join(root, cls))):
            if variants and variant not in variants:
                continue
            d = os.path.join(root, cls, variant)
            if os.path.isdir(os.path.join(d, "src")):
                out.append((f"{cls}/{variant}", d, f"{path_prefix}/{cls}/{variant}"))
    return out


# --------------------------------------------------------------------------- a whole measurement

def _key(f):
    return (f["rule_id"], f["file"].replace("\\", "/"), f["line"], f["col"])


def run_measurement(spec, leaves, out_path, artefact_root, repeat=1, echo=True,
                    tool_root=None, args=None):
    """Every leaf, `repeat` times. Writes the findings file, the run log and the determinism note.

    Nothing here averages, merges or drops a pass. Pass 1 is the measurement; passes after it exist
    only to answer whether the tool says the same thing twice, and their findings are written to
    their own file so both remain readable.
    """
    os.makedirs(artefact_root, exist_ok=True)
    passes = []
    for n in range(1, max(1, repeat) + 1):
        tag = "" if n == 1 else f".run{n}"
        log, findings, per_leaf = [], [], {}
        for leaf, source, prefix in leaves:
            entry, got = run_leaf(spec, leaf, source, prefix, artefact_root, tag,
                                  tool_root, args)
            log.append(entry)
            findings.extend(got)
            per_leaf[leaf] = {_key(f) for f in got}
            if echo:
                print(f"  {entry['status']:12} {leaf:52} exit={entry['exit_code']} "
                      f"files={entry['files_seen']} {entry['wall_seconds']}s "
                      f"{entry.get('reason', '')}".rstrip())
        passes.append((tag, log, findings, per_leaf))

    envelope = spec["envelope"]
    for tag, log, findings, _per_leaf in passes:
        dest = out_path if not tag else out_path.replace(".json", tag + ".json")
        with open(dest, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(WRITERS[envelope](findings), fh, indent=1)
            fh.write("\n")
        with open(dest + ".log", "w", encoding="utf-8", newline="\n") as fh:
            json.dump(log, fh, indent=1)
            fh.write("\n")

    verdict = determinism(passes)
    with open(out_path + ".determinism.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(verdict, fh, indent=1)
        fh.write("\n")
    return passes[0][1], passes[0][2], verdict


def determinism(passes):
    """Same input twice, same findings? Reported, never averaged and never quietly resolved."""
    if len(passes) < 2:
        return {"runs": len(passes), "verdict": "not-checked",
                "reason": "run with --repeat 2 or more to answer this"}
    base = passes[0][3]
    differing = []
    for entry in passes[1:]:
        other = entry[3]
        for leaf in sorted(set(base) | set(other)):
            if base.get(leaf, set()) != other.get(leaf, set()):
                differing.append({"pass": entry[0] or ".run1", "leaf": leaf,
                                  "only_in_first": sorted(base.get(leaf, set())
                                                          - other.get(leaf, set()))[:5],
                                  "only_in_later": sorted(other.get(leaf, set())
                                                          - base.get(leaf, set()))[:5]})
    total = sum(len(p[1]) for p in passes)
    return {"runs": len(passes), "invocations": total,
            "verdict": "deterministic" if not differing else "non-deterministic",
            "differing": differing,
            "note": ("every pass produced the same findings by rule, file, line and column"
                     if not differing else
                     "this tool does not agree with itself; its score is a sample, not a value, "
                     "and it is reported as non-deterministic rather than averaged")}
