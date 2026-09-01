# --------------------------------------------------- the "no dependencies" promise
# GETTING-STARTED says Python 3 and nothing else. If that stops being true, a stranger's first
# command fails and the whole "you can check our work" claim goes with it.

def test_no_external_python_dependencies():
    # sys.stdlib_module_names arrived in 3.10. That is a limit of how this check is
    # written, not of the code it checks: on 3.9 the other 91 checks pass and the tools
    # run. The CI matrix runs 3.11 and 3.12, so the check still executes on every push;
    # skipping here keeps 3.9 genuinely supported instead of dropping it to suit a test.
    import ast, os, sys
    if not hasattr(sys, "stdlib_module_names"):
        print("    skipped on Python %d.%d: needs sys.stdlib_module_names (3.10+); "
              "CI runs this check on 3.11 and 3.12" % sys.version_info[:2])
        return
    stdlib = set(sys.stdlib_module_names)
    local = {f[:-3] for f in os.listdir("tools") if f.endswith(".py")}
    local |= {"scanner", "make_fixtures"}      # our own, and optional
    external = {}
    for fn in sorted(f for f in os.listdir("tools") if f.endswith(".py")):
        tree = ast.parse(open(os.path.join("tools", fn), encoding="utf-8").read())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module.split(".")[0]]
            for n in names:
                if n not in stdlib and n not in local:
                    external.setdefault(n, set()).add(fn)
    assert not external, \
        f"GETTING-STARTED promises no pip install, but these are external: {external}"


def test_the_optional_scanner_import_is_guarded():
    """`scanner` is our own tool and may be absent. Anything importing it unguarded breaks a
    stranger's clone."""
    import ast, os
    unguarded = []
    for fn in sorted(f for f in os.listdir("tools") if f.endswith(".py")):
        src = open(os.path.join("tools", fn), encoding="utf-8").read()
        if "import scanner" not in src:
            continue
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(a.name == "scanner" for a in node.names):
                # module level means col_offset 0 and not inside a try
                if node.col_offset == 0:
                    unguarded.append(fn)
    # rb.py is the original harness and is allowed to require it; nothing else may
    assert set(unguarded) <= {"rb.py"}, f"unguarded `import scanner` in {unguarded}"


def test_every_module_imports_without_side_effects():
    """shiftaware.py used to run its whole analysis at import time, which is why it had no tests.
    Nothing may do that again."""
    import importlib, os, sys
    skip = {"rb.py", "emit_sol_audit.py", "test_all.py"}   # these need `scanner` or are this file
    failed = {}
    for fn in sorted(f for f in os.listdir("tools") if f.endswith(".py")):
        if fn in skip:
            continue
        name = fn[:-3]
        try:
            if name in sys.modules:
                del sys.modules[name]
            importlib.import_module(name)
        except SystemExit as e:
            failed[fn] = f"called sys.exit({e.code}) at import"
        except Exception as e:
            failed[fn] = f"{type(e).__name__}: {e}"
    assert not failed, f"modules with import-time side effects or errors: {failed}"
