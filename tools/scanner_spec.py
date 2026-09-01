#!/usr/bin/env python3
"""Adapters as declarations rather than as scripts. The framework lives in `tools/spec/`.

This module is the name everything imports and the script everything runs; it hands on every
name the one-file version had, so `import scanner_spec` and `python tools/scanner_spec.py` are
unchanged. The docstring that explains the framework is `tools/spec/__init__.py`'s.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from spec import (  # noqa: E402,F401
    HERE, ROOT, ADAPTERS_DIR,
    _int, parse_radar, parse_sol_audit, parse_semgrep, parse_solsec, parse_text_regex,
    PARSERS, WRITERS,
    REQUIRED_TOP, LAYOUTS, _problems, validate, load, load_all, clock_tables,
    _subst, _args_for, command_for, classify, _stage, _rewrite, run_leaf,
    corpus_leaves, _key, run_measurement, determinism,
    VULN, FIXED, CONTROL_CLASS, _synthetic_case, _fill, _corpus1_control, positive_control,
    demo, _FIXTURE_SPEC,
    main,
)


if __name__ == "__main__":
    sys.exit(main())
