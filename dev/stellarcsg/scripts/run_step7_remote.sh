#!/usr/bin/env bash
set -euo pipefail

cd /work
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
RESULTS=dev/stellarcsg/results/step7
RUN_DIR="$RESULTS/run"
mkdir -p "$RESULTS" "$RUN_DIR" "$RESULTS/logs"

record_error() {
  local status=$?
  printf '%s\n' "$status" > "$RESULTS/remote-error-status.txt"
  printf 'Step 7 remote runner failed at line %s while executing: %s\n' \
    "${BASH_LINENO[0]:-unknown}" "${BASH_COMMAND:-unknown}" \
    > "$RESULTS/remote-error.txt"
  assemble_reports "REMOTE_EXECUTION_ERROR"
  exit 0
}
trap record_error ERR

assemble_reports() {
  local fallback_decision="${1:-REMOTE_EXECUTION_ERROR}"
  export FALLBACK_DECISION="$fallback_decision"
  export DRIVER_STATUS="$(cat "$RESULTS/driver-status.txt" 2>/dev/null || true)"
  if [[ -f "$RUN_DIR/matched-csg-dagmc-summary.json" ]]; then
    cp "$RUN_DIR/matched-csg-dagmc-summary.json" \
      "$RESULTS/matched-csg-dagmc-summary.json"
  fi
  find "$RUN_DIR" -type f -name 'openmc-repeat-*.log' \
    -exec cp '{}' "$RESULTS/logs/" \; 2>/dev/null || true

  python - <<'PY'
import json
import os
from pathlib import Path

result_dir = Path('dev/stellarcsg/results/step7')
summary_path = result_dir / 'matched-csg-dagmc-summary.json'
if summary_path.exists():
    summary = json.loads(summary_path.read_text())
    decision = summary['decision']
    ratio = summary['native_to_dagmc_median_wall_time_ratio']
    equivalent = summary['transport_equivalent_under_5sigma_gate']
    facet = summary['maximum_sampled_facet_deviation_cm']
    native_time = summary['native']['median_wall_seconds']
    dagmc_time = summary['dagmc']['median_wall_seconds']
    z_score = summary['observable_comparison']['maximum_pairwise_z_score']
else:
    decision = os.environ.get('FALLBACK_DECISION', 'REMOTE_EXECUTION_ERROR')
    ratio = None
    equivalent = False
    facet = None
    native_time = None
    dagmc_time = None
    z_score = None

(result_dir / 'README.md').write_text(f'''# Step 7 remote comparison

A five-field-period non-axisymmetric spline surface was used to generate both:

1. a smooth native OpenMC `periodic-spline` CSG surface; and
2. a DAGMC H5M triangulation generated directly from the same surface samples.

Both models use the same one-group nearly-void material, source point, CSG
bounding box, histories, seeds, and tallies. The feature-branch OpenMC
executable is rebuilt inside `openmc/openmc:develop-dagmc` with both
`OPENMC_USE_STELLARATOR_CSG=ON` and `OPENMC_USE_DAGMC=ON`.

- Driver status: `{os.environ.get('DRIVER_STATUS', '')}`
- Decision: `{decision}`
- Transport equivalent under five-sigma gate: `{equivalent}`
- Maximum pairwise tally z-score: `{z_score}`
- Native median wall time [s]: `{native_time}`
- DAGMC median wall time [s]: `{dagmc_time}`
- Native/DAGMC median wall-time ratio: `{ratio}`
- Maximum sampled facet deviation [cm]: `{facet}`

`matched-csg-dagmc-summary.json` is the controlling compact result when the
transport driver reaches completion. The full H5M, MGXS, XML, statepoints, and
run directories are retained as a GitHub Actions artifact.
''')

Path('dev/stellarcsg/docs/STEP1_TO_STEP7_RESULTS.md').write_text(f'''# Native StellarCSG remote execution: Steps 1-7

**Branch:** `feature/native-stellarator-csg-openmc-0.16`  
**Final Step 7 decision:** `{decision}`

| Step | Result | Controlling evidence |
|---:|---|---|
| 1 | PASS | Remote clean bootstrap workflow and source archive |
| 2 | PASS | Release and sanitizer CTests; 10,000-ray adversarial campaign with zero classification or distance mismatches |
| 3 | PASS | Compiled OpenMC `periodic-spline` surface, Python API, XML/HDF5 round trip, and C++/Python tests |
| 4 | CORRECTNESS PASS | Matched OpenMC `ZTorus` comparison with zero sense, hit, or distance mismatches; timing is separately recorded |
| 5 | PASS | CAD-free classic-netCDF VMEC and MAKEGRID adapters with frozen hashes and approximately 1e-13 cm surface replay residual |
| 6 | BOUNDED PASS | Circular-cross-section swept-capsule coil prototype, segment BVH, and coil-local hexahedral mesh |
| 7 | {decision} | `results/step7/matched-csg-dagmc-summary.json`, compact logs, and the GitHub Actions artifact |

## Step 7 interpretation

- Transport equivalent under the preregistered five-sigma gate: `{equivalent}`.
- Maximum pairwise tally z-score: `{z_score}`.
- Native/DAGMC median wall-time ratio: `{ratio}`.
- Native median wall time: `{native_time}` s.
- DAGMC median wall time: `{dagmc_time}` s.
- Smooth-to-faceted maximum sampled deviation: `{facet}` cm.

The Step 7 benchmark is a synthetic five-field-period stellarator-like geometry,
not a production WISTELL-D blanket or magnet calculation. It tests equivalent
geometry generation and transport through both engines. It does not authorize
a general speedup claim or production-science use.
''')

Path('dev/stellarcsg/docs/EXECUTION_STATUS.md').write_text(f'''# StellarCSG execution status

Steps 1 through 7 have been executed remotely on the isolated feature branch.
See `STEP1_TO_STEP7_RESULTS.md` for the consolidated result and
`../results/step7/matched-csg-dagmc-summary.json` for the matched geometry
comparison when available.

Current decision: **{decision}**.
''')
PY
}

{
  echo "container_image=openmc/openmc:develop-dagmc"
  echo "trigger_sha=${GITHUB_SHA:-unknown}"
  uname -a
  python --version
  cmake --version | head -1
  c++ --version | head -1
  command -v openmc || true
  openmc --version || true
  command -v overlap_check || true
  find /root/DAGMC -maxdepth 3 -type f -name '*Config.cmake' -print 2>/dev/null || true
} | tee "$RESULTS/environment.txt"

python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -e 'dev/stellarcsg[test,vmec]'
python -m pip install vertices_to_h5m
python - <<'PY' | tee -a "$RESULTS/environment.txt"
import importlib.metadata
import openmc
import pymoab
import stellarcsg
for name in ('openmc', 'stellarcsg', 'vertices_to_h5m', 'pymoab'):
    try:
        print(f'{name}_version={importlib.metadata.version(name)}')
    except importlib.metadata.PackageNotFoundError:
        print(f'{name}_version=installed-unversioned')
print(f'openmc_python={openmc.__file__}')
print(f'stellarcsg_python={stellarcsg.__file__}')
print(f'pymoab_python={pymoab.__file__}')
PY

base64 --decode dev/stellarcsg/patches/step7-matched-csg-dagmc.patch.gz.b64 \
  | gzip --decompress > /tmp/step7-matched-csg-dagmc.patch
git config --global --add safe.directory /work
git apply --3way /tmp/step7-matched-csg-dagmc.patch
python -m py_compile dev/stellarcsg/examples/step7_matched_csg_dagmc.py

cmake -S . -B build/step7 \
  -DCMAKE_BUILD_TYPE=Release \
  -DOPENMC_USE_STELLARATOR_CSG=ON \
  -DOPENMC_USE_DAGMC=ON \
  -DDAGMC_ROOT=/root/DAGMC \
  -DCMAKE_PREFIX_PATH=/root/DAGMC \
  -DOPENMC_BUILD_TESTS=ON \
  -DOPENMC_USE_MPI=OFF \
  -DOPENMC_USE_OPENMP=ON \
  -DOPENMC_FORCE_VENDORED_LIBS=ON \
  2>&1 | tee "$RESULTS/cmake-configure.log"
cmake --build build/step7 --parallel 2 \
  2>&1 | tee "$RESULTS/cmake-build.log"

{
  build/step7/bin/openmc --version
  echo '--- linked geometry libraries ---'
  ldd build/step7/bin/openmc | grep -Ei 'dagmc|moab|embree|double|hdf5' || true
  echo '--- CMake DAGMC settings ---'
  grep -Ei 'DAGMC|DOUBLE_DOWN|EMBREE|STELLARATOR_CSG' \
    build/step7/CMakeCache.txt || true
} | tee "$RESULTS/openmc-build-provenance.txt"

ctest --test-dir build/step7 \
  -R 'stellarcsg_openmc_(surface_tests|ztorus_comparison)' \
  --output-on-failure | tee "$RESULTS/ctest-native-surface.log"
build/step7/bin/stellarcsg_openmc_ztorus_comparison 20000 10000 \
  | tee "$RESULTS/ztorus-fast-replay.json"
python - <<'PY'
import json
p = 'dev/stellarcsg/results/step7/ztorus-fast-replay.json'
data = json.load(open(p))
assert data['passed'], data
assert data['sense_mismatches'] == 0, data
assert data['ray_classification_mismatches'] == 0, data
assert data['ray_distance_mismatches'] == 0, data
PY

set +e
set -o pipefail
python dev/stellarcsg/examples/step7_matched_csg_dagmc.py \
  --openmc-exec build/step7/bin/openmc \
  --output-dir "$RUN_DIR" \
  --particles 6000 \
  --batches 10 \
  --repeats 3 \
  --mesh-theta 96 \
  --mesh-phi 192 \
  | tee "$RESULTS/transport-driver.log"
driver_status=${PIPESTATUS[0]}
set +o pipefail
set -e
printf '%s\n' "$driver_status" > "$RESULTS/driver-status.txt"

set +e
if command -v overlap_check >/dev/null 2>&1; then
  overlap_check "$RUN_DIR/matched-stellarator.h5m" -p 500 \
    > "$RESULTS/overlap-check.log" 2>&1
  echo "overlap_check_status=$?" >> "$RESULTS/overlap-check.log"
else
  echo 'overlap_check executable unavailable in container' \
    > "$RESULTS/overlap-check.log"
fi
set -e

assemble_reports "REMOTE_EXECUTION_ERROR"
trap - ERR
exit 0
