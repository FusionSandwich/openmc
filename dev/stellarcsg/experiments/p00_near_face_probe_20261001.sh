#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "$0")/../../.." && pwd -P)"
cd "$repo"
task_lock=../local-coil-wave-20260926/compute.lock
mkdir "$task_lock"
printf '{"owner":"p00-near-face-probe-20261001","pid":%s}\n' "$$" > "$task_lock/owner.json"
release_own_lease() {
  if grep -q '"owner":"p00-near-face-probe-20261001"' "$task_lock/owner.json"; then
    rm "$task_lock/owner.json"
    rmdir "$task_lock"
  fi
}
trap release_own_lease EXIT
out=dev/stellarcsg/reports/p00-near-faces-20261001
mkdir "$out"
ulimit -v 1048576
ulimit -c 0
baseline=../stellarcsg-local-continuation-20260925/dev/stellarcsg/src/compiled_facet_surface_set.cpp
candidate=dev/stellarcsg/src/compiled_facet_surface_set.cpp
probe=dev/stellarcsg/experiments/p00_near_face_probe_20261001.cpp
for variant in baseline candidate; do
  source="$baseline"
  if [[ "$variant" == candidate ]]; then source="$candidate"; fi
  timeout 90s g++ -std=c++17 -O2 -I dev/stellarcsg/include \
    "$source" "$probe" -o "$out/$variant-probe"
  timeout 30s "$out/$variant-probe" > "$out/$variant.txt"
done
sha256sum "$baseline" "$candidate" "$probe" > "$out/identities.txt"
diff -u "$out/baseline.txt" "$out/candidate.txt"
cat "$out/candidate.txt"
