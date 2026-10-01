#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "$0")/../../.." && pwd -P)"
cd "$repo"
task_lock=../local-coil-wave-20260926/compute.lock
mkdir "$task_lock"
printf '{"owner":"p00-per-case-20261001","pid":%s}\n' "$$" > "$task_lock/owner.json"
release_own_lease() {
  if grep -q '"owner":"p00-per-case-20261001"' "$task_lock/owner.json"; then
    rm "$task_lock/owner.json"
    rmdir "$task_lock"
  fi
}
trap release_own_lease EXIT

out=dev/stellarcsg/reports/p00-per-case-20261001
mkdir "$out"
ulimit -v 1048576
ulimit -c 0
baseline=../stellarcsg-local-continuation-20260925/dev/stellarcsg/src/compiled_facet_surface_set.cpp
candidate=dev/stellarcsg/src/compiled_facet_surface_set.cpp
probe=dev/stellarcsg/experiments/p00_classification_probe_20260930.cpp
fixture=dev/stellarcsg/reports/local-cont-20260925/p00-accepted-facet-fixture.txt
for variant in baseline candidate; do
  source="$baseline"
  if [[ "$variant" == candidate ]]; then source="$candidate"; fi
  timeout 90s g++ -std=c++17 -O2 -I dev/stellarcsg/include \
    "$source" "$probe" -o "$out/$variant-probe"
  timeout 30s "$out/$variant-probe" "$fixture" --per-case \
    > "$out/$variant-manifest.txt"
done
test "$(wc -l < "$out/baseline-manifest.txt")" -eq 1944
cmp "$out/baseline-manifest.txt" "$out/candidate-manifest.txt"
sha256sum "$baseline" "$candidate" "$probe" "$fixture" \
  "$out/baseline-manifest.txt" "$out/candidate-manifest.txt" \
  > "$out/identities.txt"
printf '1944 point/component classifications match per case\n'
