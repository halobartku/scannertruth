#!/usr/bin/env bash
# One command: radar on every case, both variants, then the verdicts.
#
#   ./run.sh                 # uses `radar` from PATH
#   RADAR=/path/to/radar ./run.sh
#
# Each variant is staged as _staged/<case>.<variant>/pkg/{Cargo.toml,src} because radar refuses a
# target whose Cargo.toml sits at the root of the path it is given (it prints "No Cargo.toml files
# found in any subdirectories", exits 0 and writes nothing). check.py strips the prefix again.
# radar writes no output file when it finds nothing; stdout.log is kept so that a clean zero and a
# scan that never ran stay distinguishable.
set -u
cd "$(dirname "$0")"
RADAR=${RADAR:-radar}
PY=$(command -v python3 || command -v python)

for case in cases/*/; do
  id=$(basename "$case")
  for v in insecure secure; do
    staged="_staged/$id.$v"
    rm -rf "$staged"; mkdir -p "$staged/pkg"
    cp -r "$case$v/." "$staged/pkg/"
    out="results/$id.$v"
    mkdir -p "$out"; rm -f "$out/radar.json"
    echo "== $id/$v"
    "$RADAR" scan -p "$(pwd)/$staged" -f none -o "$(pwd)/$out/radar.json" 2>&1 | tee "$out/stdout.log"
  done
done

"$PY" check.py
