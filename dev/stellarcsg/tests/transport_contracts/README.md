# Analytic OpenMC adapter contracts

Base: `FusionSandwich/openmc@c08eea92ca3fb63eb8adbf44cfb4ea8612639e30`.
This suite is opt-in. It does not enable experimental StellarCSG in CMake,
run transport, replace solver mathematics, import a period, or read WISTELL.

## Evidence boundaries

`adapter_isolation.cpp` compiles the actual `src/surface_*_spline.cpp` adapters
and actual `compiled_swept_surface_set.cpp`. Its controlled dependencies are in
`doubles/`: an analytic sphere member, map-backed XML node, test fatal-error
exception, minimal OpenMC base types, and a minimal HDF5 wrapper using the
installed real HDF5 library. The periodic backend double is also a sphere,
**not a torus**. No test-double timing is a native ZTorus measurement. The
production coefficient reader, spline roots, OpenMC particle tracking, C API,
MPI/OpenMP exception boundaries, and nuclear data are not exercised.

The entire actual collection traversal is used, not a rewritten union method.
This exposes interface/aggregation behavior on exact controlled members; it
does not establish whether every counterexample is admitted by the real spline
compiler. Every desired-contract failure remains a failed JSON record and a
nonzero child exit. Do not interpret the wrapper merely completing as PASS.

`python_method_isolation.py` extracts the actual SweptSplineSurface class via
AST and supplies a controlled base class. It uses real lxml/NumPy/h5py. On a
complete checkout point it at `openmc/surface.py`; the delivered evidence used
the retained class excerpt. It is not a native OpenMC package import.

`test_analytic_ownership.py` is a finite rational box/track oracle: 16 tests,
with exact per-track, member, material, and independent merged-union closure.
Its 23/4 weighted centimetres is an unnormalized diagnostic sum, not a neutron
transport result or flux prediction. Overlap is rejected using exact positive-
volume intersection, not an inflated tolerance. Touching boundaries are allowed.

`test_native_python_api.py` uses the real Python package, including material /
cell / parent-union / CellFilter associations. Missing native Python support is
BLOCKED, not PASS. The current environment cannot execute these assertions.
`analytic_member_model.py` exports a two-sphere native CSG example without
launching transport. Its separate swept-member binding helper takes explicit
payload/material maps; it does not invent an outer assembly or source for coils.

## Runs

Audit memory (including cgroup), system/target/data free space, significant
processes, tools/environments, caches and local checkouts before building. No
script installs anything. Existing GCC C++17, HDF5 development files, Python,
NumPy, lxml, h5py and pytest are used. Supply a fresh output directory.

```bash
# Run from a complete pinned checkout with the patch applied.
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export AUDIT_RECEIPT=/absolute/path/to/completed-audit.txt
D=dev/stellarcsg/tests/transport_contracts
bash "$D/run_isolation.sh" "$PWD/results/contracts-01"
# Initial patch: exit 1, 47 checks / 40 PASS / 7 FAIL.
# Local collection guard/tie repair: exit 1, 47 checks / 43 PASS / 4 FAIL.
# Continue deliberately in another command; do not hide that status.
python -m pytest -c /dev/null --confcutdir="$D" -q "$D/test_analytic_ownership.py"
python "$D/python_method_isolation.py" --source openmc/surface.py \
  --adapter-hdf5 results/contracts-01/adapter-output.h5 \
  --output results/python-methods-01
# Expected after albedo fix: exit 1, 20 checks / 18 PASS / 2 FAIL.
python -m pytest -c /dev/null --confcutdir="$D" -q "$D/test_native_python_api.py"
# Last command is native-package-only; do not claim skipped assertions passed.
```

The native CellFilter implementation (`src/tallies/filter_cell.cpp`) examines
all particle coordinate levels. The manual fixture therefore puts member cells
201/202 inside parent-union cell 500, and uses two separate tallies. Never sum
ancestor and descendant bins together in one filter to claim union closure:
that would count a physical segment twice. Actual native scoring/closure is
still NOT_RUN; the analytic rational ledger is a separate oracle.

## Explicit remaining contracts

* `BLOCKED_TERMINAL_STATUS`: a boolean found flag plus historical diagnostic
  counts cannot encode a terminal unresolved disposition. Injected unresolved
  diagnostics are currently dropped by the adapters/collection. A nonzero
  historical unresolved count might also describe a subsequently resolved
  fallback; rejecting every nonzero count would be unjustified overblocking.
* The local collection repair rejects NaN member hits and duplicate member IDs,
  and chooses the minimum stable ID at equal distance. These three controlled
  checks now pass. Repeated physical coil IDs across images require an explicit
  `(physical_coil_id, image_id)` / unique member ID; that interface is absent.
  A stable bookkeeping tie is not proof of a unique normal at a nonsmooth
  shared contact.
* `BLOCKED_MATERIAL_OVERLAP`: nearest constituent boundary is not generally the
  exterior union boundary for overlapping members. The controlled example
  returns distance 2 while union evaluation is -3; true union exit is 3.
  Reject an inadmissible material overlap or implement an expressly supported
  union geometry policy in the owning lane. Do not resolve it by relabeling.
* `BLOCKED_COLLECTION_PYTHON_REPRESENTATION`: C++ prefix/start/count collection
  XML/HDF5 has no corresponding Python SweptSplineSurface representation.
  Use individually bound, admitted member surfaces/cells when attribution is
  required. The opaque C++ collection's scalar distance does not expose member
  IDs/materials to the OpenMC Surface API.

Proposed owning-lane outcome interface: terminal `hit`, `no_hit`, `unresolved`,
plus stable member identity, contact kind, and unresolved-prefix information.
A `hit` requires finite nonnegative distance and resolution/exclusion of every
possibly earlier interval. A `no_hit` must carry the agreed completeness
semantics; a sampled reference is not a certificate. Unresolved must cause an
explicit run/query failure through the native adapter/C API, never a silently
lost history. Historical diagnostics remain separate. This is a proposal,
not an implemented new solver protocol.

Geometric contact at t=0 is distinct from tracking suppression. The tests
explicitly forward `coincident=false/true`, retain a positive dyadic near-zero
hit, and retain the farther inward exit. They verify adapter behavior under a
controlled backend, not repair of production a06/a08 origin/tangent failures.

## Promotion gates

Native runtime/data/transport and full C++/C-API integration remain BLOCKED.
Spline completeness, geometry admission, image ownership, winding-pack fidelity,
40 cm-offset physical assembly and matched mesh comparison remain unqualified.
The raw WISTELL source hashes matching accepted inputs do not make the 1 cm
circular/no-blanket diagnostic the accepted physical assembly. No WISTELL,
Bateman, mesh, remote, or full-machine run is part of this suite.

All candidate/old/native-ZTorus query costs, cost ratios, throughput ratios,
quantiles and repeated-run variability are null: no performance measurement
was made, and native ZTorus is unavailable. Performance comparison is INCOMPLETE,
not waived. Preferred <=1.25x old and temporary <=2x old guardrails are unchanged
and unevaluated. Unit-test wall time is not geometry throughput.
