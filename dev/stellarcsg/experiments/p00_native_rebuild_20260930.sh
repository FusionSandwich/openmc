#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/../../.." && pwd -P)"
cd "$repo"
task_lock=../local-coil-wave-20260926/compute.lock
mkdir "$task_lock"
printf '{"owner":"p00-native-rebuild-20260930","run":"boundary-margin-rebuild","pid":%s}\n' "$$" > "$task_lock/owner.json"
release_own_lease() {
  if grep -q '"owner":"p00-native-rebuild-20260930"' "$task_lock/owner.json"; then
    rm "$task_lock/owner.json"
    rmdir "$task_lock"
  fi
}
trap release_own_lease EXIT

build=/home/sman/builds/stellarcsg-p00-bbox-20260930-03
out=dev/stellarcsg/reports/p00-native-validation-20260930-04
mkdir -p "$out"
ulimit -v 2097152
ulimit -c 0
timeout 300s cmake --build "$build" --target openmc -- -j1 \
  > "$out/build.stdout" 2> "$out/build.stderr"
sha256sum dev/stellarcsg/src/compiled_facet_surface_set.cpp \
  "$build/bin/openmc" "$build/lib/libopenmc.so" > "$out/native-identities.txt"
ldd "$build/bin/openmc" > "$out/loader.txt"
printf 'corrected native rebuild completed\n'
