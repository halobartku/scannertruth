"""Adapters as declarations rather than as scripts.

Adding a scanner to this benchmark has cost roughly an evening every time it has been done, and
almost none of that evening went on the scanner. Two agents each added one on 2026-09-01 and their
reports say where the time went: writing, for the fifth and sixth time, a per-case runner that
iterates the corpus, invokes a container, captures stdout, decides whether the run happened,
writes an artefact, writes a log line, rewrites container paths onto corpus paths and aggregates a
findings file. `run_solsec.py` and `run_semgrep.py` are the same 120 lines twice, and the two
differ in exactly four places: the image, the argv, the regex that reads the tool's own "I read N
files" line, and the shape of its output.

Those four places are what a declaration holds. Everything else is here, once.

    adapters/<tool>.json   what is different about this tool
    tools/scanner_spec.py  what is the same about all of them

**What comes for free, and why each one is not optional.**

*One artefact and one log line per invocation.* `run_leaf` writes the tool's complete stdout and
stderr unedited, and a log entry carrying the exact command, the exit code and the wall time.
Errors 20 and 21: two published numbers were extrapolated from one case each because a findings
file was the only record, and a findings file cannot tell "ran and found nothing" from "never
ran".

*Unavailability classified, not inferred.* A declaration MUST say how the tool announces that it
read the code - `solsec` prints `Found N Rust files to analyze`, `radar` prints `Scanned N file`,
`sol-azy` prints `N files scanned` - and `validate` refuses a declaration that does not. Without
that line the run is `unavailable`, never a zero, and a tool that has no such line at all must say
so explicitly, in which case its runs are `unknown` and can never become zeros by default. Error
35 read silence as a measurement (`solsec: 0 / 6, 3 unavailable`, all of it inferred from an empty
file) and error 36 read a measurement as silence (a clean radar zero published as "could not
run"). Both on the same day, in opposite directions.

*A determinism check.* `--repeat 2` runs every leaf twice and compares findings by rule, path,
line and column. The verdict is written beside the findings file. A tool that disagrees with
itself is reported as `non-deterministic` with the differing leaves named; nothing is averaged and
neither run is discarded.

*A positive control that crosses the parser.* Every declaration carries a sample of the tool's own
output with one real finding in it. `positive_control` plants that finding at the fix site of a
synthetic case, parses it with this tool's parser, writes it in this tool's stored envelope, reads
it back with the same `score2.load_findings` that reads the committed files, and asserts the
scorer says `detected`. On 2026-09-01 an external review disabled one branch of `load_findings`
and every check in the repository stayed green while every corpus-2 verdict silently became
`missed`. A parser can break in one branch only, so the control runs per declaration.

Usage:

    python tools/scanner_spec.py --list                 what is declared, and what it feeds
    python tools/scanner_spec.py --self-check           positive control, every declaration
    python tools/scanner_spec.py --demo                 self-check of this module
    python tools/scanner_spec.py --run solsec --corpus corpus2 --out raw/c2-solsec.json
"""
import os
import sys

# `HERE` is tools/, as it was when this lived in tools/scanner_spec.py: the lazy imports of
# `score2`, `score` and `run_all` in control.py resolve against it.
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
ADAPTERS_DIR = os.path.join(ROOT, "adapters")
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# Every module-level name the one-file version had, so `tools/scanner_spec.py` can hand them on
# unchanged. The underscore names are listed because the suite and the demo reach them.
from .parsers import (  # noqa: E402
    _int, parse_radar, parse_sol_audit, parse_semgrep, parse_solsec, parse_text_regex,
    PARSERS, WRITERS,
)
from .validate import (  # noqa: E402
    REQUIRED_TOP, LAYOUTS, _problems, validate, load, load_all, clock_tables,
)
from .run import (  # noqa: E402
    _subst, _args_for, command_for, classify, _stage, _rewrite, run_leaf,
)
from .measure import corpus_leaves, _key, run_measurement, determinism  # noqa: E402
from .control import (  # noqa: E402
    VULN, FIXED, CONTROL_CLASS, _synthetic_case, _fill, _corpus1_control, positive_control,
)
from .demo import demo, _FIXTURE_SPEC  # noqa: E402
from .cli import main  # noqa: E402
