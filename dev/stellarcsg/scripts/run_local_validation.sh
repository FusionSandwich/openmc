#!/usr/bin/env bash
set -euo pipefail

with_openmc=false
if [[ ${1:-} == "--openmc-adapter" ]]; then
  with_openmc=true
elif [[ $# -gt 0 ]]; then
  echo "usage: $0 [--openmc-adapter]" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
validation_root="$repo_root/build/stellarcsg-local-validation"
cpp_build="$validation_root/cpp"
demo_output="$validation_root/demo"
mkdir -p "$validation_root"

cmake -S "$repo_root/dev/stellarcsg" -B "$cpp_build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DSTELLARCSG_ENABLE_HDF5=ON \
  -DSTELLARCSG_BUILD_TESTS=ON \
  -DSTELLARCSG_BUILD_BENCHMARKS=ON \
  -DSTELLARCSG_BUILD_TOOLS=ON
cmake --build "$cpp_build" --parallel
ctest --test-dir "$cpp_build" --output-on-failure
"$cpp_build/stellarcsg_surface_benchmark" \
  | tee "$validation_root/geometry_benchmark.json"

export PYTHONPATH="$repo_root/dev/stellarcsg/python${PYTHONPATH:+:$PYTHONPATH}"
pytest -q "$repo_root/dev/stellarcsg/python/tests"
rm -rf "$demo_output"
python -m stellarcsg.cli demo --output-dir "$demo_output" \
  > "$validation_root/demo_stdout.json"
"$cpp_build/stellarcsg_inspect_surface" \
  "$demo_output/compiled_geometry.h5" /surfaces/plasma 600 0 0 \
  > "$validation_root/python_to_cpp_surface_probe.json"

if $with_openmc; then
  openmc_build="$validation_root/openmc-adapter"
  cmake -S "$repo_root" -B "$openmc_build" \
    -DCMAKE_BUILD_TYPE=Release \
    -DOPENMC_BUILD_TESTS=OFF \
    -DOPENMC_USE_OPENMP=ON \
    -DSTELLARCSG_BUILD_OPENMC_ADAPTER_TESTS=ON \
    -DCMAKE_PROJECT_INCLUDE="$repo_root/dev/stellarcsg/openmc_adapter/enable.cmake"
  cmake --build "$openmc_build" \
    --target stellarcsg_openmc_adapter_tests --parallel
  ctest --test-dir "$openmc_build" \
    -R stellarcsg_openmc_adapter_tests --output-on-failure
fi

printf 'StellarCSG validation complete: %s\n' "$validation_root"
