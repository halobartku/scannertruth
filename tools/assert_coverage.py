#!/usr/bin/env python3
"""Which assertions in the suite never execute.

    python tools/assert_coverage.py          # run the suite under trace, list assertions never run

A green test whose assertions never executed has checked nothing, and it is indistinguishable from
a passing one in the output. The usual cause is that every assertion sits inside a loop over a
collection that turns out to be empty: no iterations, no assertions, one more "passed".

This exists because error 46 was a check that ran on every push and measured a different quantity
than the one it was named after. That defect is not this one, but it is the same family: a guard
that is believed to be working. Grepping for the shape does not settle it, because whether a loop
is empty depends on the data, so this counts line executions with sys.settrace instead of reading
the code and guessing.

**What this measures and what it does not.** It measures execution: did the interpreter reach this
assert. It does NOT measure whether the assertion could fail. `assert x or True` executes on every
run and can never fail; only a mutation shows that. Read this as one necessary condition of a check
being real, not as proof that it is.
"""
import ast
import glob
import io
import os
import sys


def assertion_lines(root="."):
    """{absolute file path: {line numbers of assert statements}} for everything in tests/."""
    out = {}
    for f in sorted(glob.glob(os.path.join(root, "tests", "*.py"))):
        src = io.open(f, encoding="utf-8").read()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Assert):
                out.setdefault(os.path.abspath(f), set()).add(node.lineno)
    return out


def run_suite_under_trace(wanted):
    """Run test_all.main() and return {file: {lines actually executed}} for the wanted lines."""
    seen = {}

    def tracer(frame, event, _arg):
        if event == "line":
            fn = frame.f_code.co_filename
            if fn in wanted and frame.f_lineno in wanted[fn]:
                seen.setdefault(fn, set()).add(frame.f_lineno)
        return tracer

    # Loaded by path rather than with `import test_all`, and the reason is a check in the suite
    # this file measures: `test_no_external_python_dependencies` reads the imports of every tool
    # and calls anything without a sibling module external. `test_all.py` lives at the repository
    # root, not in tools/, so a plain import of it reads as a pip dependency and turns the suite
    # red. The check is right and this file is the odd one, so this file bends.
    import importlib.util
    sys.path.insert(0, ".")
    spec = importlib.util.spec_from_file_location("_suite", os.path.join(".", "test_all.py"))
    suite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suite)
    sys.settrace(tracer)
    try:
        suite.main()
    except SystemExit:
        pass
    finally:
        sys.settrace(None)
    return seen


def main():
    wanted = assertion_lines()
    seen = run_suite_under_trace(wanted)
    total = sum(len(v) for v in wanted.values())
    live = sum(len(v) for v in seen.values())
    print()
    print("=" * 72)
    print("assertions in tests/: %d   executed at least once: %d   never: %d"
          % (total, live, total - live))
    for f in sorted(wanted):
        missing = sorted(wanted[f] - seen.get(f, set()))
        if not missing:
            continue
        src = io.open(f, encoding="utf-8").read().splitlines()
        print("\n%s: %d never executed" % (os.path.relpath(f), len(missing)))
        for line in missing:
            print("   %5d  %s" % (line, src[line - 1].strip()[:100]))
    print()
    print("A line here is not automatically a defect: the second half of an if/else that guards a")
    print("condition the data does not currently meet is correct and idle. It is a list of places")
    print("to look, and the question to ask at each one is whether the collection can be empty.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
