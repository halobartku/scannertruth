"""The command line."""
import argparse
import os
import sys

# Rebinds this module's `__doc__` to the package's: `main` prints the first line of the
# framework docstring as --help's description, exactly as the one-file version did.
from . import __doc__  # noqa: F401
from .control import positive_control
from .demo import demo
from .measure import corpus_leaves, run_measurement
from .validate import load_all


# --------------------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adapters", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--run", help="the declared scanner to run")
    ap.add_argument("--corpus", default="corpus2")
    ap.add_argument("--corpus-root", default=None)
    ap.add_argument("--out", help="findings file to write; the log lands beside it")
    ap.add_argument("--artefacts", default=None)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--tool-root", default=None,
                    help="where the tool itself lives, for a declaration that runs a local checkout")
    ap.add_argument("--arg", action="append", default=[], metavar="NAME=VALUE",
                    help="substitute {NAME} in run.command. Only a token the declaration lists in "
                         "run.arg_defaults is accepted, so a typo cannot leave the default in "
                         "place while the output is filed under another name. sol-audit's three "
                         "published profiles differ by exactly this one token.")
    args = ap.parse_args()
    overrides = {}
    for pair in args.arg:
        if "=" not in pair:
            print(f"--arg expects NAME=VALUE, got {pair!r}", file=sys.stderr)
            return 2
        key, val = pair.split("=", 1)
        overrides[key] = val

    if args.demo:
        demo()
        return 0

    specs = load_all(args.adapters)

    if args.list:
        print(f"{'scanner':28} {'engine':7} {'format':11} {'envelope':10} rows")
        for name, spec in sorted(specs.items()):
            rows = ", ".join(f"{m['corpus'].replace('corpus', 'c')}:{m['row']}"
                             + ("" if m.get("on_clock", True) else " (off clock)")
                             for m in spec["measurements"]) or "none"
            print(f"{name:28} {spec['run']['engine']:7} {spec['output']['format']:11} "
                  f"{spec['envelope']:10} {rows}")
        return 0

    if args.self_check:
        for name, spec in sorted(specs.items()):
            got = positive_control(spec)
            print(f"  positive control OK  {name:26} {got['format']} -> {got['envelope']}")
        print(f"\n{len(specs)} declarations, every one can carry a detection to `detected` "
              "and stays silent on the fix")
        return 0

    if args.run:
        if args.run not in specs:
            print(f"no declaration named {args.run!r}; have {sorted(specs)}", file=sys.stderr)
            return 2
        spec = specs[args.run]
        if not args.out:
            print("--out is required: the findings file and its run log go there", file=sys.stderr)
            return 2
        leaves = corpus_leaves(args.corpus, root=args.corpus_root)
        artefacts = args.artefacts or os.path.splitext(args.out)[0] + "-runs"
        print(f"{spec['name']} {spec.get('version', '')} over {len(leaves)} invocations "
              f"({args.corpus}), {args.repeat} pass(es)")
        log, findings, det = run_measurement(spec, leaves, args.out, artefacts, args.repeat,
                                            tool_root=args.tool_root, args=overrides)
        counts = {}
        for e in log:
            counts[e["status"]] = counts.get(e["status"], 0) + 1
        print(f"\n{len(log)} invocations: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
        print(f"{len(findings)} findings, determinism: {det['verdict']}")
        print(f"written: {args.out}, {args.out}.log, {args.out}.determinism.json")
        return 0

    ap.print_help()
    return 0
