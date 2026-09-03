#!/usr/bin/env python3
"""One runner for every check that stands between a defect and a published number.

Before 2026-09-01 this repository had 47 assertions across 1,913 lines and no way to run them
together. Four files had no test at all, and two of those were the worst possible candidates:
`shiftaware.py`, which corrected 23 phantom detections, and `control_c2.py`, which carries the
claim that the metric cannot be bought with volume.

The tests below are chosen by one rule: **would a defect here change a number we publish?** Anything
that would not is left alone. No framework, no fixtures directory, no dependencies - the same
constraint as the rest of the repo, so it runs anywhere the harness runs.

    python test_all.py            # everything
    python test_all.py -v         # print each check as it passes

**Verified by mutation, because a test that cannot fail is worse than no test.** Three deliberate
defects were introduced and all three were caught: widening the line tolerance to 999 broke two
checks; returning an unsplit location from the Radar extractor broke one; and dropping the
"silent on the fixed variant" half of real recall broke three, including the golden test, which
reported `sol-audit: published (6, 4), now (6, 6)` - a published number changing under a refactor,
which is exactly what these exist to catch. Two later mutations were caught the same way: a fake
`import requests` and a quickstart naming a script that does not exist.
"""
import sys

from tests._core import check, PASSED, FAILED, _documented_command_files

# Every module in tests/ contributes its `test_*` functions to this namespace. `main` sorts the
# whole namespace by name, so the order the checks run in is the same as before the split.
from tests.shiftaware import *
from tests.score2_verdicts import *
from tests.holdout_commitments import *
from tests.coverage_bookkeeping import *
from tests.unmapped import *

# ============================================================================ WAVE 2
# Added 2026-09-01 after the first suite was judged too thin for a project whose entire claim is
# that it measures carefully. Same selection rule: would a defect here change a published number?

from tests.score1 import *
from tests.run_all_extractors import *
from tests.changed_lines import *
from tests.candidate_triage import *
from tests.published_numbers import *
from tests.data_integrity import *

# ============================================================================ WAVE 3
# Documentation that drifts from the code is worse than no documentation: it tells a stranger to
# expect something the repository no longer does. These check that the promises in GETTING-STARTED
# and AGENTS.md are still true, and cover the paths waves 1 and 2 left alone.

from tests.no_dependencies import *
from tests.documented_commands import *
from tests.claims_banned import *
from tests.ci_honesty import *
from tests.protocol_results import *
from tests.corpus_pinned import *
from tests.corpus_growth import *
from tests.two_logs_one_run import *
from tests.adapter_framework import *
from tests.regression_pack import *
from tests.real_crate_run import *
from tests.ci_steps import *


def test_the_advertised_check_count_matches_the_suite():
    """The README said 82 while the suite ran 88. Adding tests without updating the
    figure is the easiest way to make the front page lie, so the figure is derived.

    Scoped to README and AGENTS until 2026-09-01, when an external review pointed out that
    GETTING-STARTED said 59, WALKTHROUGH said 81, ROADMAP said 81 and all three skills said 81,
    while the suite ran 94 - and that the skills' own instruction on a mismatch is to stop and
    report, so the project was telling its agents to halt. The fix that mattered was not the
    numbers; it was that the derived check covered two documents out of seven.
    """
    import io as _io, re
    actual = len([n for n in globals() if n.startswith("test_")])
    wrong = []
    for doc in _documented_command_files():
        s = _io.open(doc, encoding="utf-8").read()
        for n in re.findall(r"(\d+)\s+checks", s) + re.findall(r"(\d+)\s+passed", s):
            if int(n) != actual:
                wrong.append(f"{doc}: {n}")
    assert not wrong, (f"the suite defines {actual} checks; these documents say otherwise: {wrong}")


# -------------------------------------------------------------------- main
def main():
    print("running the checks that stand between a defect and a published number\n")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name[5:].replace("_", " "), fn)

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        print("\nA failure here means a number in this repository may be wrong. Fix it before "
              "publishing anything.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
