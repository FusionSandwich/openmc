#!/usr/bin/env bash
# Focused adapter contracts. No transport, kernel benchmark, or acquisition.
set -eu
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=${1:?usage: AUDIT_RECEIPT=path run_isolation.sh NEW_OUTPUT_DIRECTORY}
CPU=${CPU:-0}
CXX=${CXX:-g++}
: "${AUDIT_RECEIPT:?Complete the environment audit and supply its readable receipt}"
test -s "$AUDIT_RECEIPT"
if test -e "$OUT"; then echo "Refusing to overwrite evidence: $OUT" >&2; exit 2; fi
mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
ulimit -v 1572864
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd "$ROOT"
"$CXX" --version > "$OUT/compiler.txt"
# Splitting pkg-config's installed compiler/linker flags is intentional.
set +e
taskset -c "$CPU" timeout 45s "$CXX" \
  -std=c++17 -O0 -g0 -UNDEBUG -Wall -Wextra -Werror \
  -fno-fast-math -ffp-contract=off \
  -Idev/stellarcsg/tests/transport_contracts/doubles -Iinclude \
  -Idev/stellarcsg/include $(pkg-config --cflags hdf5) \
  dev/stellarcsg/tests/transport_contracts/adapter_isolation.cpp \
  src/surface_swept_spline.cpp src/surface_periodic_spline.cpp \
  dev/stellarcsg/src/compiled_swept_surface_set.cpp \
  $(pkg-config --libs hdf5) -o "$OUT/adapter_isolation" \
  > "$OUT/build.log" 2>&1
BUILD=$?
printf '%s\n' "$BUILD" > "$OUT/build-exit.txt"
if test "$BUILD" -ne 0; then cat "$OUT/build.log" >&2; exit "$BUILD"; fi
taskset -c "$CPU" timeout 15s "$OUT/adapter_isolation" "$OUT/adapter-output.h5" \
  > "$OUT/results.jsonl" 2> "$OUT/stderr.txt"
STATUS=$?
printf '%s\n' "$STATUS" > "$OUT/child-exit.txt"
sha256sum "$OUT/adapter_isolation" > "$OUT/binary.sha256"
cat "$OUT/stderr.txt"
# Known desired-contract failures remain failures. Never normalize exit 1 to 0.
exit "$STATUS"
