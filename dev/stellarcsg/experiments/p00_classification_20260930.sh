#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/../../.." && pwd -P)"
cd "$repo"
task_lock=../local-coil-wave-20260926/compute.lock
mkdir "$task_lock" # Atomic admission; never take an existing lease.
printf '{"owner":"p00-classification-20260930","run":"bounded-facet-test","pid":%s}\n' "$$" > "$task_lock/owner.json"
release_own_lease() {
  if grep -q '"owner":"p00-classification-20260930"' "$task_lock/owner.json"; then
    rm "$task_lock/owner.json"
    rmdir "$task_lock"
  fi
}
trap release_own_lease EXIT

out=dev/stellarcsg/reports/p00-classification-20260930-03
mkdir -p "$out"
ulimit -v 1048576
timeout 90s g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic \
  -I dev/stellarcsg/include \
  dev/stellarcsg/src/compiled_facet_surface_set.cpp \
  dev/stellarcsg/tests/test_compiled_facet_surface_set.cpp \
  -o "$out/facet_test"
STELLARCSG_FACET_FIXTURE=dev/stellarcsg/reports/local-cont-20260925/p00-accepted-facet-fixture.txt \
  timeout 30s "$out/facet_test"

cp ../stellarcsg-local-continuation-20260925/dev/stellarcsg/src/compiled_facet_surface_set.cpp \
  "$out/baseline.cpp"
for variant in baseline candidate; do
  source=dev/stellarcsg/src/compiled_facet_surface_set.cpp
  if [[ "$variant" == baseline ]]; then source="$out/baseline.cpp"; fi
  timeout 90s g++ -std=c++17 -O2 -I dev/stellarcsg/include \
    "$source" dev/stellarcsg/experiments/p00_classification_probe_20260930.cpp \
    -o "$out/$variant-probe"
done
sha256sum "$out/baseline.cpp" dev/stellarcsg/src/compiled_facet_surface_set.cpp \
  dev/stellarcsg/reports/local-cont-20260925/p00-accepted-facet-fixture.txt \
  "$out/baseline-probe" "$out/candidate-probe" > "$out/identities.txt"
for variant in baseline candidate baseline candidate; do
  timeout 60s "$out/$variant-probe" \
    dev/stellarcsg/reports/local-cont-20260925/p00-accepted-facet-fixture.txt \
    | tee -a "$out/$variant-results.txt"
done
