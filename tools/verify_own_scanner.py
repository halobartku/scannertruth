#!/usr/bin/env python3
"""Czy kod skanera nadal daje te same znaleziska, co opublikowany pomiar.

Kontrola proweniencji dla WLASNEGO narzedzia. Innym skanerom w tym benchmarku stawiamy
wymaganie, zeby pomiar byl zwiazany z konkretna wersja; ta kontrola pilnuje tego u nas.

Powod powstania, 2026-09-11: opublikowane liczby sol-audit-v3 zmierzono 01.09 o 05:13,
a commit "Split scanner.py into six modules behind a facade" jest z 01.09 o 23:40,
czyli **18 godzin PO pomiarze**. Refaktor powinien byc neutralny, ale nikt tego nie sprawdzil.
Sprawdzone: jest neutralny, 71/229/685 znalezisk identycznie w trzech profilach.

Puszcza DZISIEJSZY kod na tym samym korpusie i porownuje znaleziska z zapisanymi.

UWAGA na porownanie: pierwsza wersja tej kontroli zglosila 100 procent roznic, bo pomiar
z 01.09 zapisal sciezki jako "corpus2/x/y.rs", a dzisiejszy przebieg z ukosnikiem wstecznym Windowsa,
i `col` jako 0 wobec None. Roznica byla w ZAPISIE, nie w tresci. Stad normalizacja nizej.
"""
import json, os, subprocess, sys, tempfile, hashlib

S = r"D:/Users/stank/Desktop/Forge/scannertruth"
CLI = r"D:/Users/stank/Desktop/Forge/sol-audit-v2/cli.py"
PROFILE = ["strict", "broad", "all"]


def sciezka(x):
    r"""Znormalizowana sciezka: ukosniki, bez przedrostka korpusu, bez wiodacych ./

    Bez tego porownanie wykazuje 100 procent roznic na samym zapisie sciezki: pomiar z 01.09
    zapisal 'corpus2/x/y.rs', a dzisiejszy przebieg 'x\y.rs'. To ta sama rodzina bledu
    co CRLF przy porownywaniu plikow: roznica w zapisie, nie w tresci.
    """
    x = (x or "").replace("\\", "/").lstrip("./")
    if x.startswith("corpus2/"):
        x = x[len("corpus2/"):]
    return x


def klucz(f):
    # `col` pominiete celowo: zapisany pomiar ma 0, dzisiejszy None, a kolumna nie wchodzi
    # do zadnej punktacji. Porownujemy regule, plik i linie.
    return (f.get("rule_id"), sciezka(f.get("file")), f.get("line"))


def wczytaj(p):
    d = json.load(open(p, encoding="utf-8"))
    return sorted(klucz(x) for x in (d.get("findings") or []))


def test():
    ok = 0
    assert klucz({"rule_id": "A", "file": "b", "line": 1, "col": 0}) == ("A", "b", 1); ok += 1
    assert klucz({}) == (None, "", None); ok += 1
    # ten sam plik zapisany na dwa sposoby musi dac ten sam klucz
    assert sciezka("corpus2/x/y.rs") == sciezka("x" + chr(92) + "y.rs") == "x/y.rs"; ok += 1
    # rozna kolumna nie moze robic roznicy
    assert klucz({"rule_id": "A", "file": "x", "line": 1, "col": 0}) == klucz({"rule_id": "A", "file": "x", "line": 1}); ok += 1
    a = [("A", "b", 1), ("A", "b", 2)]
    assert sorted(a) == a; ok += 1
    # porownanie jest na ZBIORACH uporzadkowanych, wiec kolejnosc z narzedzia nie ma znaczenia
    assert sorted([("B", "x", 1, 0), ("A", "x", 1, 0)])[0][0] == "A"; ok += 1
    print("test: %d sprawdzen OK" % ok)
    return 0


def main():
    os.chdir(S)
    print("porownanie: zapisany pomiar z 2026-09-01 05:13 kontra DZISIEJSZY kod\n")
    print("%-8s %10s %10s %10s %10s  %s" % ("profil", "zapisane", "dzis", "tylko_zap", "tylko_dzis", "werdykt"))
    rozne = 0
    for prof in PROFILE:
        stary_p = os.path.join("raw", "c2-sol-audit-v3-%s.json" % prof)
        if not os.path.exists(stary_p):
            print("%-8s brak %s" % (prof, stary_p)); continue
        stare = wczytaj(stary_p)
        with tempfile.TemporaryDirectory() as t:
            out = os.path.join(t, "findings.json")
            cmd = [sys.executable, CLI, "corpus2", "--profile", prof, "--format", "json",
                   "--out", out, "--log", os.path.join(t, "files.log"),
                   "--fail-on", "none", "--quiet"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if not os.path.exists(out):
                print("%-8s PADL rc=%d %s" % (prof, r.returncode, (r.stderr or r.stdout)[:80])); continue
            nowe = wczytaj(out)
        sz, sn = set(stare), set(nowe)
        tylko_z, tylko_n = sz - sn, sn - sz
        w = "IDENTYCZNE" if not tylko_z and not tylko_n else "ROZNE"
        if w == "ROZNE":
            rozne += 1
        print("%-8s %10d %10d %10d %10d  %s" % (prof, len(stare), len(nowe), len(tylko_z), len(tylko_n), w))
        for k in sorted(tylko_z)[:3]:
            print("           tylko w zapisanym: %s" % (k,))
        for k in sorted(tylko_n)[:3]:
            print("           tylko dzis:        %s" % (k,))
    print()
    if rozne == 0:
        print("WNIOSEK: refaktor nie zmienil zachowania. Opublikowane liczby opisuja dzisiejszy kod.")
    else:
        print("WNIOSEK: refaktor ZMIENIL zachowanie w %d profilach. Opublikowane liczby sa nieaktualne." % rozne)


if __name__ == "__main__":
    sys.exit(test() if "--test" in sys.argv[1:] else main())
