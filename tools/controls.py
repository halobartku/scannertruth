#!/usr/bin/env python3
"""Scanner controls: one normalised Finding shape, plus the null and noisy adapters.

A benchmark that can only measure its author's tool is a self-assessment. This module is the seam
that lets it measure anyone's: every scanner is wrapped so it produces the same normalised output.

    Finding(rule_id, path, line)

An adapter answers two questions: `available()` says whether the tool can run here, and `run(dir)`
returns findings. Nothing else. A scanner that is not installed is reported as unavailable rather
than silently scored zero, because "we could not run it" and "it found nothing" are different facts
and conflating them is how benchmarks lie.

**Control adapters are part of the design, not a test fixture.** `null` reports nothing and `noisy`
flags every line. They calibrate the metric: `noisy` must score high nominal recall and ZERO real
recall, and `null` must score zero on both. If the metric ever fails to put `noisy` at the bottom,
the metric is broken and the scanner rankings computed with it are worthless.

Usage:
    python tools/controls.py            # self-check, then which adapters are available here

No tool imports this module; the declarations the framework runs are `adapters/*.json`.
"""
import json
import os
import re
import shutil
import subprocess
from collections import namedtuple

Finding = namedtuple("Finding", "rule_id path line")

TIMEOUT = 300


def _rs_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "target", "node_modules")]
        for name in filenames:
            if name.endswith(".rs"):
                yield os.path.join(dirpath, name)


class Adapter:
    name = "abstract"
    version = "unknown"
    homepage = ""

    def available(self):
        raise NotImplementedError

    def run(self, directory):
        raise NotImplementedError

    def unavailable_reason(self):
        return "not installed"


# --------------------------------------------------------------------------- controls

class NullScanner(Adapter):
    """Reports nothing, ever. Floor of the scale."""
    name = "control-null"
    version = "1.0"

    def available(self):
        return True

    def run(self, directory):
        return []


class NoisyScanner(Adapter):
    """Flags every non-empty line of every file. Ceiling of nominal recall, floor of real recall.

    This is the scanner every vendor metric based on finding counts would rank first. If our metric
    does not rank it last, our metric is measuring the same nothing.
    """
    name = "control-noisy"
    version = "1.0"

    def available(self):
        return True

    def run(self, directory):
        out = []
        for path in _rs_files(directory):
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    for i, line in enumerate(fh, 1):
                        if line.strip():
                            out.append(Finding("NOISE-ALL", path, i))
            except OSError:
                continue
        return out


# --------------------------------------------------------------------------- real scanners

class SolAudit(Adapter):
    """Our own scanner. First subject of this benchmark, and it is not a product."""
    name = "sol-audit"
    version = "v2"
    homepage = "https://github.com/halobartku/sol-audit"

    def available(self):
        try:
            import scanner  # noqa: F401
            return True
        except Exception:
            return False

    def run(self, directory):
        import scanner
        out = []
        for path in _rs_files(directory):
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    src = fh.read()
                for item in scanner.scan_text(src, path) or []:
                    rid = getattr(item, "rule_id", None) or (
                        item.get("rule_id") if isinstance(item, dict) else None)
                    ln = getattr(item, "line", None) or (
                        item.get("line") if isinstance(item, dict) else 0)
                    if rid:
                        out.append(Finding(rid, path, ln or 0))
            except Exception:
                # A crash counts as a miss, never an excuse. See PROTOCOL.md.
                continue
        return out


class Semgrep(Adapter):
    """Widely used general static analyser. Not Solana-specific, which is itself worth measuring."""
    name = "semgrep"
    version = "installed"
    homepage = "https://semgrep.dev"

    def available(self):
        return shutil.which("semgrep") is not None

    def run(self, directory):
        cmd = ["semgrep", "--config", "auto", "--json", "--quiet",
               "--no-git-ignore", "--timeout", "60", directory]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        except (subprocess.TimeoutExpired, OSError):
            return []
        try:
            data = json.loads(proc.stdout or "{}")
        except ValueError:
            return []
        out = []
        for r in data.get("results", []):
            rid = r.get("check_id", "")
            out.append(Finding(rid, r.get("path", ""), (r.get("start") or {}).get("line", 0)))
        return out


class CargoBinary(Adapter):
    """Base for cargo-installed Rust scanners that print human-readable diagnostics."""
    binary = None
    args = ()
    # `path:line` or `--> path:line:col`, the shape rustc-family tools emit.
    LOC = re.compile(r"(?:-->\s*)?([\w./\\-]+\.rs):(\d+)")
    RULE = re.compile(r"\b([A-Z][A-Z0-9_-]{2,}|[a-z][a-z0-9_-]*::[a-z0-9_-]+)\b")

    def available(self):
        return self.binary is not None and shutil.which(self.binary) is not None

    def run(self, directory):
        try:
            proc = subprocess.run([self.binary, *self.args, directory],
                                  capture_output=True, text=True, timeout=TIMEOUT)
        except (subprocess.TimeoutExpired, OSError):
            return []
        out = []
        for line in (proc.stdout + proc.stderr).splitlines():
            loc = self.LOC.search(line)
            if not loc:
                continue
            rule = self.RULE.search(line)
            out.append(Finding(rule.group(1) if rule else "UNLABELLED",
                               loc.group(1), int(loc.group(2))))
        return out


class VaultLint(CargoBinary):
    name = "vaultlint"
    binary = "vaultlint"
    homepage = "https://github.com/vaultlint/vaultlint"


class Radar(Adapter):
    """Auditware Radar. Runs its own containers; we consume the JSON it writes.

    Note for the record: Radar's own README uses `sealevel-attacks` as its usage example, so any
    score it gets on that corpus should be read as in-sample for Radar. Stated in PROTOCOL.md.
    """
    name = "radar"
    version = "main"
    homepage = "https://github.com/Auditware/radar"
    OUTPUT = "/tmp/output.json"
    LOC = re.compile(r"^(?P<path>.+?):(?P<line>\d+):")

    def available(self):
        return shutil.which("radar") is not None

    def run(self, directory):
        try:
            subprocess.run(["radar", "-p", directory], capture_output=True,
                           text=True, timeout=3000)
        except (subprocess.TimeoutExpired, OSError):
            return []
        return self.parse(self.OUTPUT)

    @classmethod
    def parse(cls, output_path):
        """Radar writes a list of {name, description, severity, certainty, locations}."""
        try:
            with open(output_path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return []
        out = []
        for item in data or []:
            rule = item.get("name", "").strip()
            for loc in item.get("locations", []) or []:
                m = cls.LOC.match(loc)
                if m:
                    out.append(Finding(rule, m.group("path"), int(m.group("line"))))
        return out


ADAPTERS = [NullScanner(), NoisyScanner(), SolAudit(), Semgrep(), VaultLint(), Radar()]


def by_name(name):
    for a in ADAPTERS:
        if a.name == name:
            return a
    raise KeyError(name)


def demo():
    """Self-check: the controls must behave as the calibration argument requires."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "a.rs")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("fn main() {\n    let x = 1;\n}\n")

        assert NullScanner().run(d) == [], "null control must report nothing"

        noisy = NoisyScanner().run(d)
        assert len(noisy) == 3, f"noisy control must flag every non-empty line, got {len(noisy)}"
        assert all(f.rule_id == "NOISE-ALL" for f in noisy)

        assert NullScanner().available() and NoisyScanner().available()

        # An uninstalled tool must be unavailable, never silently a zero score.
        missing = CargoBinary()
        missing.binary = "definitely-not-installed-xyz"
        assert not missing.available()

    print("controls: OK")


if __name__ == "__main__":
    demo()
    print()
    print(f"{'adapter':16} {'available':>10}   homepage")
    for a in ADAPTERS:
        print(f"{a.name:16} {str(a.available()):>10}   {a.homepage}")
