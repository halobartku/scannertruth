#!/usr/bin/env bash
# prov-watch.sh - straznik STARZENIA SIE PROWENIENCJI (hermes --monitor-script, raz na dobe).
#
# Czego NIE robi, bo robia to inne: ror-watch.sh pilnuje czterech watkow prawa do odpowiedzi,
# gh-watch-own.sh pilnuje naszych dwoch repozytoriow. Ten pilnuje czegos, czego nie pilnuje nikt:
# czy opublikowane pomiary nadal opisuja to, co zmierzyly.
#
# Powod powstania, 2026-09-11 (W-113): nasz wlasny skaner byl zmierzony 01.09 o 05:13,
# a refaktor "Split scanner.py into six modules" jest z 01.09 o 23:40. Osiemnascie godzin
# roznicy i NIKT tego nie zauwazyl przez dziesiec dni. `--verify-coverage` przechodzil,
# bo sprawdza, czy pomiar ma log, a nie czy pochodzi z tej samej wersji narzedzia.
#
# Kontrakt, ten sam co ror-watch.sh:
#   - stan w $HERMES_HOME/state/prov-watch.json
#   - brak zmiany  -> ZERO na stdout; diagnostyka tylko na stderr; kod wyjscia zawsze 0
#   - blad API     -> bez wyjscia i BEZ aktualizacji stanu dla tej pozycji (zlapie sie nastepnym razem)
#   - zmiana       -> "DRYF <co> | <szczegol>"
#   - stan zapisywany dopiero PO wypisaniu; pierwszy przebieg zasiewa baseline po cichu
# Nigdy niczego nie publikuje i nie zmienia w repozytorium.
set -u
HERMES_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="$HERMES_DIR/state"
ENV_FILE="$HERMES_DIR/.env"
# scannertruth lezy na VPS; sol-audit NIE lezy tu wcale, tylko na laptopie, wiec jego kod
# sledzimy przez commit w repozytorium zdalnym. To zreszta lepsze: sledzi zrodlo OPUBLIKOWANE,
# a nie czyjas lokalna kopie.
REPO="${SCANNERTRUTH_DIR:-/root/scannertruth}"
mkdir -p "$STATE_DIR"

python3 - "$STATE_DIR/prov-watch.json" "$ENV_FILE" "$REPO" <<'EOF'
import glob, hashlib, json, os, sys, urllib.request, urllib.error

state_p, env_p, repo = sys.argv[1:4]


def log(m):
    sys.stderr.write("prov-watch: " + m + "\n")


def token(path):
    try:
        for l in open(path, encoding="utf-8"):
            l = l.strip()
            if l.startswith("export "):
                l = l[7:].strip()
            if l.startswith("GITHUB_TOKEN="):
                return l.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception as e:
        log("env: %s" % e)
    return ""


H = {"User-Agent": "prov-watch", "Accept": "application/vnd.github+json"}
t = token(env_p)
if t:
    H["Authorization"] = "Bearer " + t


def api(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=20))


def skrot_drzewa(katalog, wzorce):
    """Skrot tresci plikow, posortowany po nazwie. CR zdejmowane po obu stronach,
    bo bez tego to samo drzewo na Windowsie i na Linuksie daje rozne skroty."""
    h = hashlib.sha256()
    for w in wzorce:
        for p in sorted(glob.glob(os.path.join(katalog, w))):
            h.update(os.path.basename(p).encode())
            h.update(open(p, "rb").read().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


try:
    state = json.load(open(state_p, encoding="utf-8"))
    if not isinstance(state, dict):
        state = {}
except Exception:
    state = {}
first = not state
out, new = [], dict(state)

# --- 1. kod naszego skanera: HEAD repozytorium, bo lokalnie go tu nie ma ---------------
try:
    d = api("https://api.github.com/repos/halobartku/sol-audit/commits?per_page=1")
    sig = (d[0]["sha"][:12] + " " + d[0]["commit"]["author"]["date"][:10]) if d else ""
except Exception as e:
    log("skaner: %s, stan zachowany" % e)
    sig = None
if sig:
    prev = state.get("skaner")
    if prev is None:
        log("skaner: baseline %s" % sig)
    elif prev != sig:
        out.append("DRYF skaner | nowy commit %s (bylo %s) | opublikowany pomiar moze go juz nie opisywac"
                   % (sig, prev))
        out.append("  sprawdz: cd scannertruth && python tools/verify_own_scanner.py")
    new["skaner"] = sig

# --- 2. korpus wobec stanu z chwili pomiaru ------------------------------------------
man = os.path.join(repo, "corpus2", "manifest.json")
if os.path.exists(man):
    sig = hashlib.sha256(open(man, "rb").read().replace(b"\r\n", b"\n")).hexdigest()[:16]
    prev = state.get("korpus2")
    if prev is None:
        log("korpus2: baseline %s" % sig)
    elif prev != sig:
        out.append("DRYF korpus2 | manifest zmieniony (%s -> %s) | pomiary opisuja poprzedni korpus"
                   % (prev, sig))
    new["korpus2"] = sig
else:
    log("korpus2: brak manifestu, stan zachowany")

# --- 3. wersje CUDZYCH skanerow -------------------------------------------------------
# Ten sam zarzut, ktory postawilibysmy komus innemu: pomiar ma opisywac wersje, ktora zmierzyl.
# Zrodlo musi byc TO, z ktorego instalowalismy, a nie to, ktore najlatwiej odpytac.
# 2026-09-11: pierwsza wersja pytala GitHuba o solsec i dostala v0.2.0, podczas gdy adapter
# mowi 0.2.1 - bo instalacja szla `cargo install solsec --version 0.2.1`, czyli z crates.io.
# Bylby to falszywy alarm przy kazdym przebiegu.
SLEDZONE = {
    "radar":     ("gh", "Auditware/radar"),
    "sol-azy":   ("gh", "FuzzingLabs/sol-azy"),
    "xray":      ("gh", "sec3-product/x-ray"),
    "solsec":    ("crates", "solsec"),
    "vaultlint": ("crates", "vaultlint"),
}
for nazwa, (zrodlo, gh) in sorted(SLEDZONE.items()):
    if zrodlo == "crates":
        klucz = "wydanie:" + nazwa
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(
                "https://crates.io/api/v1/crates/%s" % gh,
                headers={"User-Agent": "prov-watch (forge benchmark provenance check)"}), timeout=20))
            sig = (d.get("crate") or {}).get("max_version") or ""
        except Exception as e:
            log("%s: %s, stan zachowany" % (nazwa, e)); continue
        prev = state.get(klucz)
        if prev is None:
            log("%s: baseline crates.io %s" % (nazwa, sig))
        elif prev != sig:
            out.append("DRYF %s | crates.io ma %s (bylo %s) | nasz opublikowany pomiar opisuje stare"
                       % (nazwa, sig, prev))
        new[klucz] = sig
        continue
    klucz = "wydanie:" + nazwa
    try:
        d = api("https://api.github.com/repos/%s/releases/latest" % gh)
        sig = d.get("tag_name") or d.get("name") or ""
    except urllib.error.HTTPError as e:
        if e.code == 404:
            try:
                tags = api("https://api.github.com/repos/%s/tags?per_page=1" % gh)
                if tags:
                    sig = tags[0]["name"]
                else:
                    # Bez wydan i bez tagow zostaje HEAD galezi domyslnej. Inaczej taki skaner
                    # bylby jedynym, ktorego starzenia NIE widzimy, a radar i sol-azy sa wlasnie takie.
                    c = api("https://api.github.com/repos/%s/commits?per_page=1" % gh)
                    sig = ("HEAD " + c[0]["sha"][:12] + " " + c[0]["commit"]["author"]["date"][:10]) if c else "brak"
            except Exception as e2:
                log("%s: %s, stan zachowany" % (nazwa, e2)); continue
        else:
            log("%s: HTTP %s, stan zachowany" % (nazwa, e.code)); continue
    except Exception as e:
        log("%s: %s, stan zachowany" % (nazwa, e)); continue
    prev = state.get(klucz)
    if prev is None:
        log("%s: baseline %s" % (nazwa, sig))
    elif prev != sig:
        out.append("DRYF %s | nowe wydanie %s (bylo %s) | nasz opublikowany pomiar opisuje stare"
                   % (nazwa, sig, prev))
    new[klucz] = sig

if out:
    sys.stdout.write("\n".join(out) + "\n")
    sys.stdout.flush()
elif first:
    log("pierwszy przebieg, baseline zasiany, nic nie wypisano")

if new != state:
    tmp = state_p + ".tmp"
    json.dump(new, open(tmp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    os.replace(tmp, state_p)
EOF
exit 0
