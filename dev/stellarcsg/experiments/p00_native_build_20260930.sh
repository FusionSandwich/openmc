#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/../../.." && pwd -P)"
cd "$repo"
task_lock=../local-coil-wave-20260926/compute.lock
mkdir "$task_lock"
printf '{"owner":"p00-native-build-20260930","run":"bbox-classification-native","pid":%s}\n' "$$" > "$task_lock/owner.json"
release_own_lease() {
  if grep -q '"owner":"p00-native-build-20260930"' "$task_lock/owner.json"; then
    rm "$task_lock/owner.json"
    rmdir "$task_lock"
  fi
}
trap release_own_lease EXIT

out=dev/stellarcsg/reports/p00-native-validation-20260930-03
build=/home/sman/builds/stellarcsg-p00-bbox-20260930-03
mkdir -p "$out"
if [[ -e "$build" ]]; then
  echo 'Unique native build target already exists; refusing overwrite' >&2
  exit 2
fi
ulimit -v 2097152
ulimit -c 0
export OMP_NUM_THREADS=1
timeout 120s cmake -S "$repo" -B "$build" -G 'Unix Makefiles' \
  -DCMAKE_BUILD_TYPE=Release \
  -DOPENMC_BUILD_TESTS=OFF \
  -DOPENMC_USE_OPENMP=OFF \
  -DOPENMC_USE_MPI=OFF \
  -DOPENMC_USE_DAGMC=OFF \
  -DOPENMC_ENABLE_STRICT_FP=ON \
  -DOPENMC_ENABLE_EXPERIMENTAL_STELLARCSG=ON \
  -DGIT_SUBMODULE=OFF \
  > "$out/configure.stdout" 2> "$out/configure.stderr"
timeout 1650s cmake --build "$build" --target openmc -- -j1 \
  > "$out/build.stdout" 2> "$out/build.stderr"
sha256sum "$build/bin/openmc" "$build/lib/libopenmc.so" \
  > "$out/native-identities.txt"
ldd "$build/bin/openmc" > "$out/loader.txt"
printf 'native build completed\n'
