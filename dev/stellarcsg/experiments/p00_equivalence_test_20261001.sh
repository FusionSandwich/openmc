#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/../../.." && pwd -P)"
cd "$repo"
task_lock=../local-coil-wave-20260926/compute.lock
mkdir "$task_lock"
printf '{"owner":"p00-equivalence-test-20261001","pid":%s}\n' "$$" > "$task_lock/owner.json"
release_own_lease() {
  if grep -q '"owner":"p00-equivalence-test-20261001"' "$task_lock/owner.json"; then
    rm "$task_lock/owner.json"
    rmdir "$task_lock"
  fi
}
trap release_own_lease EXIT

out=dev/stellarcsg/reports/p00-equivalence-20261001-02
mkdir "$out"
ulimit -v 1048576
ulimit -c 0
timeout 90s g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic \
  -I dev/stellarcsg/include \
  dev/stellarcsg/src/compiled_facet_surface_set.cpp \
  dev/stellarcsg/tests/test_compiled_facet_surface_set.cpp \
  -o "$out/facet_test" > "$out/build.stdout" 2> "$out/build.stderr"
STELLARCSG_FACET_FIXTURE=dev/stellarcsg/reports/local-cont-20260925/p00-accepted-facet-fixture.txt \
  timeout 30s "$out/facet_test" > "$out/test.stdout" 2> "$out/test.stderr"
sha256sum dev/stellarcsg/src/compiled_facet_surface_set.cpp \
  dev/stellarcsg/tests/test_compiled_facet_surface_set.cpp \
  "$out/facet_test" > "$out/identities.txt"
cat "$out/test.stdout"
