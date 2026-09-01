# Codex execution prompt: preserve the qualified StellarCSG branch and pursue torus-class performance

## Role

Act as the implementation owner, numerical-methods researcher, benchmark owner, and repository custodian for the next StellarCSG milestone.

This is an execution task. Do not stop at a proposal. Preserve the current qualified implementation, reproduce its evidence, perform a focused literature and code review, implement the most promising next methods as separately selectable paths, test them against independent oracles, run matched OpenMC/DAGMC/Double Down/Embree benchmarks, retain negative results, and push all accepted work to the user’s OpenMC fork.

The principal technical objective is:

> Make generic stellarator plasma surfaces and finite non-planar magnet coils usable as native OpenMC CSG, while moving their runtime performance as close as practical to OpenMC’s built-in `ZTorus` function.

A result that is merely a little faster than ordinary DAGMC is not the final target. The development target is the same performance order as the built-in torus, subject to zero wrong-nearest-root events and fair matched-accuracy comparisons.

---

# 1. Repository boundary and preservation contract

Work only in:

```text
Repository: FusionSandwich/openmc
Qualified branch: codex/stellarcsg-native-csg-foundation-20260828
Qualified starting commit: c67b68fdaf7be2049308db7da449f14a25123847
Preservation branch: archive/stellarcsg-qualified-c67b68fd-20260831
```

The preservation branch already records the qualified state. Verify that it still points to the starting commit before editing.

Do not:

- modify `develop`, `master`, or another default branch;
- modify `openmc-dev/openmc`;
- create a pull request or draft pull request;
- force-push;
- rewrite or rebase published history;
- use `git reset --hard` against uncommitted user work;
- use destructive `git clean` commands without first proving the targeted files are generated and backed up;
- delete current benchmark reports, source fixtures, negative results, or oracle implementations;
- replace a working path before its replacement passes the same correctness and regression gates;
- relabel unmatched tests as matched comparisons;
- claim a method is implemented unless it has been compiled and executed.

Keep:

```text
OPENMC_ENABLE_EXPERIMENTAL_STELLARCSG=OFF
```

as the default.

## 1.1 Safe worktree procedure

Execute:

```bash
git clone https://github.com/FusionSandwich/openmc.git openmc-stellarcsg
cd openmc-stellarcsg
git fetch --all --tags --prune
git switch codex/stellarcsg-native-csg-foundation-20260828
git pull --ff-only origin codex/stellarcsg-native-csg-foundation-20260828
git status --short --branch
git rev-parse HEAD
git rev-parse origin/archive/stellarcsg-qualified-c67b68fd-20260831
```

The archive ref must resolve to:

```text
c67b68fdaf7be2049308db7da449f14a25123847
```

If the qualified branch has advanced, confirm that the current head is a descendant of `c67b68fd...`:

```bash
git merge-base --is-ancestor \
  c67b68fdaf7be2049308db7da449f14a25123847 \
  origin/codex/stellarcsg-native-csg-foundation-20260828
```

Do not reset a later valid head back to the old commit.

Before edits, create:

```text
dev/stellarcsg/reports/TORUS_CLASS_RESEARCH_STARTING_STATE.json
```

containing the current head, the archive ref, Git status, toolchain, hardware, relevant dependency versions, build flags, and SHA-256 values of all retained benchmark inputs.

Create a Git bundle as an additional local recovery artifact:

```bash
mkdir -p dev/stellarcsg/recovery
git bundle create \
  dev/stellarcsg/recovery/pre_torus_class_research.bundle \
  codex/stellarcsg-native-csg-foundation-20260828 \
  archive/stellarcsg-qualified-c67b68fd-20260831
sha256sum dev/stellarcsg/recovery/pre_torus_class_research.bundle \
  > dev/stellarcsg/recovery/pre_torus_class_research.bundle.sha256
```

Do not commit the bundle if it is unreasonably large. Commit its manifest and hash either way.

For high-risk research implementations, create a separate worktree and child branch inside the same GitHub repository:

```bash
git worktree add ../openmc-stellarcsg-torus-class \
  -b codex/stellarcsg-torus-class-fastpath-20260901 \
  HEAD
cd ../openmc-stellarcsg-torus-class
git push -u origin codex/stellarcsg-torus-class-fastpath-20260901
```

Use no PR. Push logical commits to the child branch while researching. Only fast-forward or cherry-pick validated commits back to `codex/stellarcsg-native-csg-foundation-20260828` after all preservation and no-regression checks pass. Leave failed experiments on named experimental commits/branches or retain them in reports; do not overwrite the qualified implementation.

---

# 2. Current qualified evidence that must remain reproducible

Reproduce these results before changing algorithms. If hardware differs, preserve the old values and add a new machine-specific baseline rather than replacing them.

## 2.1 End-to-end OpenMC medians

```text
Built-in OpenMC ZTorus:                     774,121.5 histories/s
Periodic-spline exact-torus specialization: 351,233 histories/s
WISTELL-D periodic plasma native CSG:         26,643.8 histories/s
WISTELL-D periodic plasma fine DAGMC:         21,511.8 histories/s
Representative non-planar coil native CSG:   432,436 histories/s
Representative non-planar coil fine DAGMC:   910,634 histories/s
Complete 48-coil native CSG:                 289,656 histories/s
Complete 48-coil fine DAGMC:                  49,189.5 histories/s
```

Derived observations:

```text
Spline torus / built-in ZTorus:       0.4537
WISTELL plasma / fine DAGMC:          1.2386
WISTELL plasma / built-in ZTorus:     0.0344
Single coil / fine DAGMC:             0.4749
Single coil / built-in ZTorus:        0.5586
Complete 48-coil set / fine DAGMC:    5.8886
Complete set / built-in ZTorus:       0.3742
```

## 2.2 Kernel diagnostics

WISTELL-D periodic plasma:

```text
11.82672 microseconds per distance call
66.713 BVH nodes per ray
6.696 candidate patches per ray
16.953 Newton iterations per ray
0.464 local subdivision calls per ray
0 production global-oracle calls
```

Representative WISTELL-D non-planar coil:

```text
631.624 ns per distance call
213.908 ns per classification call
7.978 BVH nodes per ray
0.728 candidate spans per ray
2.015 Newton iterations per ray
3.7% local bounded fallback
0 production global-oracle calls
```

Complete 48-coil set:

```text
1.060176 microseconds per distance call
2.858 candidate coils per ray
0.766 candidate spans per ray
23.585 combined BVH nodes per ray
1.105 Newton iterations per ray
0.657% local bounded fallback
0 production global-oracle calls
```

## 2.3 Correctness evidence

Preserve and rerun:

- forced-general exact torus: 100,000 randomized and 4,099 adversarial rays, zero wrong/missed/false roots;
- representative non-planar coil: 1,000 oracle rays, zero mismatches;
- complete 48-coil set: 100 broad-oracle set rays plus 4,800 per-coil oracle solves, zero mismatches;
- thirteen selected real-coil configurations: 1,300 independent-oracle rays, zero mismatches;
- native plasma, single-coil, and complete-set OpenMC geometry-debug passes;
- ordinary DAGMC transport with zero lost particles;
- retained OpenMC DAGMC geometry-debug complaint involving explicit volume and implicit complement.

Do not weaken these tests while optimizing.

## 2.4 Current architecture that must not be discarded

The qualified implementation already contains:

- data-driven periodic spline surfaces;
- exact torus specialization;
- general periodic span patches;
- proxy triangles;
- flattened front-to-back BVH2;
- projected damped Newton correction;
- bounded local recovery;
- no broad oracle in the production path;
- cubic Bézier coil spans;
- exact centerline hulls and conservative swept boxes;
- capsule proxies;
- shared top-level 48-coil BVH;
- versioned, hash-bound geometry data;
- OpenMC C++/Python/XML/HDF5 integration;
- independent broad correctness oracles;
- retained DAGMC models and benchmark scripts.

New methods must be implemented as selectable alternatives or replacements protected by tests. Do not throw away the current path until another path is demonstrably better.

---

# 3. Source-grounded geometry requirements

The supplied stellarator-neutronics paper by Miralles-Dolz et al. used ParaStell to generate 3-D models from 45 VMEC equilibria. Seven could not be generated mainly because radial-build surfaces intersected from excessive torsion or interpolation effects. The paper’s ParaStell workflow constructs successive in-vessel layers by offsetting outward along the LCFS normal, and for devices with more than two field periods it models one complete field period using rotational periodic boundaries. Its models excluded magnets.

Preserve these consequences:

- reject unsupported folds/intersections explicitly;
- do not silently smooth an inadmissible surface into a different device;
- keep physical-normal blanket construction;
- use one complete rotational field period for initial WISTELL-D qualification;
- do not infer coil performance from that paper because its simulation set omitted magnets.

The supplied Bogaarts–Warmer paper defines stellarator surfaces through Fourier/parametric coordinates, adds a physical distance coordinate beyond the LCFS, uses equal-arc-length poloidal reparameterization to improve geometric regularity, constructs nonuniform layer-distance fields, creates coil-winding surfaces, and uses rotation-minimizing frames for finite coils. It explicitly warns that Frenet–Serret frames generate irregular finite coils. It also shows that stellarator half-module symmetry transforms both position and direction and is not ordinary reflection or rotational periodicity.

Preserve these consequences:

- retain physical normal-distance layers;
- evaluate equal-arc-length parameterization as a conditioning and patch-quality tool;
- retain rotation-minimizing frames;
- keep half-module boundary conditions outside this performance milestone;
- treat deterministic/FW-CADIS methods as later variance-reduction support, not a cure for slow geometry intersections.

The current research question goes beyond both papers: neither demonstrates a native custom OpenMC CSG primitive operating near `ZTorus` speed.

---

# 4. Mandatory phase A: unblock and normalize Double Down / Embree

The latest comparison used a DAGMC binary explicitly identified as:

```text
nompi_nodoubledown
```

This is not a fundamental Embree blocker. Build or recover a matched Double Down / Embree environment before drawing a final native-versus-mesh conclusion.

## 4.1 Build matrix

Create two DAGMC installation prefixes from the same source commits:

```text
_deps/dagmc-obb
_deps/dagmc-doubledown
```

Use the same:

- compiler;
- optimization flags;
- MOAB;
- OpenMC commit;
- H5M files;
- thread count;
- CPU affinity.

Build and verify:

```text
ordinary DAGMC OBB traversal
DAGMC Double Down / Embree traversal
```

Also run native CSG through both OpenMC executables to detect link/build effects unrelated to geometry.

Verify actual linkage, not only CMake completion:

```bash
grep -E 'DOUBLE_DOWN|DAGMC|EMBREE' <build>/CMakeCache.txt
ldd <prefix>/lib/libdagmc.so | grep -E 'libdd|embree|moab'
```

Record exact Double Down, Embree, DAGMC, MOAB and OpenMC versions.

If the earlier working environment exists locally, identify its exact image ID, library paths and commits. Do not compare it numerically until the same geometry, source bank, histories, node, threads and compiler are rerun.

## 4.2 Matched cases

Run ordinary DAGMC and Double Down/Embree for:

- exact torus coarse and fine H5M;
- WISTELL-D plasma H5M;
- representative single non-planar coil;
- complete 48-coil set;
- one synthetic helical plasma;
- one planar torus-equivalent coil.

The same H5M SHA-256 must be used for ordinary and Double Down traversal.

Produce:

```text
dev/stellarcsg/reports/DOUBLE_DOWN_BUILD_AND_LINKAGE.json
dev/stellarcsg/reports/DOUBLE_DOWN_MATCHED_RESULTS.json
dev/stellarcsg/reports/DOUBLE_DOWN_MATCHED_RESULTS.md
```

If a dependency really cannot be built, record the exact compile/link/runtime error, searched prefixes, available packages and smallest next action. “Unavailable in the currently selected binary” is not sufficient evidence of a fundamental blocker.

---

# 5. Mandatory phase B: remove framework overhead visible in the exact-torus specialization

The exact periodic-spline torus currently achieves only 45.37% of built-in `ZTorus`. Before tackling harder geometry, identify and remove avoidable framework overhead.

## 5.1 Required comparison

Use the same ray corpus and the same OpenMC fixed-source model for:

```text
built-in ZTorus
periodic-spline exact-torus specialization
general periodic patch path forced on the same torus
```

Add a geometry-kernel benchmark that normalizes:

- hit probability;
- inside/outside origin distribution;
- root distance distribution;
- incidence angle;
- tangent and near-tangent fraction;
- coincident fraction;
- two-root and four-root rays.

End-to-end histories/s alone is insufficient because different models may make different numbers of distance/classification calls per history.

Measure:

```text
ns/distance
ns/evaluate/classification
distance calls/history
crossings/history
geometry CPU fraction
instructions/call
cycles/call
branches and branch misses
cache misses
quartic-solver calls
heap allocations
```

Use `perf`, compiler optimization reports, disassembly and, where possible, LTO/PGO.

## 5.2 Targeted cleanup

Investigate and only retain changes that measurably help:

- call the same OpenMC quartic helper used by `ZTorus`;
- inline the specialization dispatch;
- return a raw distance rather than constructing generic result objects;
- eliminate residual spline evaluation after an algebraically validated torus root;
- remove redundant direction normalization after confirming OpenMC’s direction contract, retaining debug assertions;
- precompute constant coefficient combinations;
- compile disabled counters to header-level constant no-ops;
- eliminate wrapper conversions and virtual layers unique to StellarCSG;
- use `noexcept`, `[[likely]]`, alignment and structure layout only where profiles justify them;
- test LTO;
- test PGO with a representative mixed ray corpus;
- verify that no HDF5, allocation, locks, strings or dynamic callbacks appear in the hot path.

Hard gate:

```text
periodic-spline exact-torus specialization >= 0.85 * built-in ZTorus
```

Stretch gate:

```text
>= 0.95 * built-in ZTorus
```

If the gate fails, produce a cycle-level accounting of the remaining overhead before proceeding.

---

# 6. Mandatory phase C: conventional high-performance parametric patch redesign

Implement a second-generation periodic-surface path while preserving the current patch solver as `legacy_patch_v1`.

Use a compile-time or runtime method selector such as:

```text
legacy_patch_v1
bezier_patch_v2
algebraic_proxy_v1
```

Do not overwrite the current algorithm until the new method passes.

## 6.1 Convert spline spans to tensor-product Bézier patches

At geometry-compilation time, convert each local spline span into a tensor-product Bézier control net and precompute:

- position control net;
- first-derivative control nets;
- second-derivative/curvature bounds;
- normal cone;
- parameter bounds;
- neighbor and seam ownership;
- conservative geometric error bounds.

Evaluate Bernstein polynomials with a compact, vectorizable implementation.

## 6.2 Tight spatial bounds

Compare:

- current AABB/BVH2;
- tangent-aligned oriented boxes;
- skewed parallelepipeds;
- k-DOPs;
- quantized OBBs;
- BVH4;
- BVH8;
- structured toroidal-bin index plus a small local BVH.

The periodic theta,varphi topology should be exploited rather than treating patches as an unordered triangle soup.

Select the structure using measured:

```text
nodes visited
candidate patches
bytes/patch
build time
traversal cycles
SIMD utilization
```

Initial targets:

```text
median candidate patches <= 2
p99 candidate patches <= 8
median BVH nodes <= 16
```

## 6.3 Replace triangle-only seeds

Implement and benchmark one or more direct local proxies:

- direct bilinear-patch ray intersection;
- biquadratic proxy;
- local quadric;
- osculating torus;
- two-triangle proxy retained as control.

The proxy supplies candidate parameters only. The authoritative spline/Bézier patch supplies the final surface.

## 6.4 Exact local correction

Solve the ray/patch system in local parameters using analytical derivatives. Use:

- two-dimensional damped Newton;
- trust-region or line search;
- previous/neighbor seed where safe;
- deterministic seam ownership;
- stable coincidence rules;
- scale-aware residuals.

Target:

```text
median exact-correction steps <= 3
p99 <= 8
```

## 6.5 Replace scan/golden-section recovery

The current WISTELL-D path performs local subdivision/recovery on approximately 46.4% of rays. Replace the expensive scan, bisection and golden-section path with local methods such as:

- Bézier clipping;
- interval Newton;
- Krawczyk operator;
- Bernstein sign/convex-hull exclusion;
- adaptive local subdivision restricted to one patch.

The production broad global oracle must remain unreachable:

```text
production_global_reference_calls == 0
```

Target expensive local recovery:

```text
<0.1% initially
<0.01% preferred
```

---

# 7. Mandatory phase D: prototype a low-degree algebraic proxy atlas

This is a research implementation, not a predetermined replacement. Preserve it as a separate method.

The hypothesis is:

> A spline surface can be compiled into small bounded patches with low-degree implicit polynomial proxies. A ray then produces a fixed-degree univariate polynomial, making the runtime workload closer to `ZTorus`, followed by one or two exact spline corrections.

## 7.1 Literature and code review

Search primary computational-geometry, CAGD and rendering sources for:

- approximate implicitization of Bézier/B-spline patches;
- SVD-based implicitization;
- monoid implicitization and inverse maps;
- low-degree algebraic approximants;
- moving curves/moving surfaces;
- resultants and syzygy methods;
- Bernstein-basis polynomial root isolation;
- rational and Chebyshev approximants;
- certified error bounds and phantom-branch rejection;
- ray tracing algebraic surfaces;
- interval-certified correction to parametric patches.

Treat prior suggestions as leads, not constraints. Verify algorithms and licenses from primary sources and original repositories.

## 7.2 Offline patch compiler

For each patch, test degree 4 first and degree 6 where required:

```text
P_i(x,y,z)=0
```

Store:

- polynomial coefficients in a stable basis;
- spatial patch bound;
- approximation/error bound;
- inverse or patch-domain map;
- branch/domain rejection data;
- derivative bounds;
- source patch identity.

Reject a patch when the required error or branch-separation bound cannot be certified.

## 7.3 Runtime

For ray:

```text
x(t)=o+t d
```

form:

```text
p_i(t)=P_i(o+t d)
```

Then:

1. solve all real roots of the quartic/sextic;
2. reject roots outside the patch’s spatial and parametric domain;
3. choose the nearest positive candidate;
4. apply one or two exact corrections against the authoritative parametric patch;
5. certify or locally subdivide;
6. never accept a phantom algebraic branch.

Reuse a robust fixed-degree solver and compare coefficient-formation cost to OpenMC’s torus quartic.

## 7.4 A/B decision

Compare `bezier_patch_v2` and `algebraic_proxy_v1` on the same retained ray corpora:

```text
wrong/missed/false roots
ns/distance
candidate patches
polynomial roots tested
exact corrections
local fallback
memory
compile time
model-file size
```

Do not choose the algebraic method merely because it is mathematically novel. Retain it only if it improves the Pareto front.

---

# 8. Mandatory phase E: second-generation coil narrow phase

Preserve the current coil-set top-level BVH; its sublinear scaling is a successful component.

Implement two separately selectable local coil methods and compare them.

## 8.1 Piecewise analytic line/arc/biarc sweep

At compile time, approximate each rotation-minimizing-frame centerline with adaptive G1-continuous:

- line segments;
- circular arcs;
- biarcs.

For a circular cross section:

```text
line sweep     -> cylinder/capsule intersection
circular arc   -> oriented torus-segment quartic
```

Use exact segment-domain and ownership tests. Bound complete swept-surface deviation, not only centerline deviation.

Investigate whether a clothoid or another short analytic segment family improves curvature continuity without making intersection too expensive.

## 8.2 Direct Bézier-tube intersector

For cubic Bézier centerline spans, investigate primary literature and implementations for:

- tight disjoint cylindrical/conical bounds;
- ray/fiber or ray/tube intersection;
- tangential-cone iteration;
- direct limit-surface intersection;
- certified span-local closest coordinates.

Eliminate global closest-point scans.

For circular/elliptical section:

```text
S(s,alpha)=c(s)+a cos(alpha) N(s)+b sin(alpha) B(s)
```

Use analytical derivatives and one candidate span at a time.

## 8.3 Embree diagnostic

Where geometrically equivalent, compare:

- Embree round Bézier/B-spline curve primitive;
- Embree user geometry with the exact StellarCSG narrow phase;
- custom StellarCSG BVH and narrow phase.

Use this to distinguish traversal cost from narrow-phase cost. Do not replace a finite closed coil volume with a curve primitive and call the geometry identical unless inside/outside and cross-section semantics are matched.

## 8.4 Coil gates

Planar torus-equivalent coil, with exact-torus delegation disabled:

```text
zero wrong roots
zero production global-oracle calls
>= fine Double Down/DAGMC throughput at matched surface error
>= 0.75 * built-in ZTorus preferred
```

Representative non-planar coil:

```text
>= fine Double Down/DAGMC at matched complete swept-surface error
>= 0.75 * built-in ZTorus preferred
```

Complete coil set:

```text
retain shared two-level BVH
no linear scan
zero wrong roots
zero lost particles
>= fine Double Down/DAGMC
>= 0.50 * built-in ZTorus minimum
>= 0.75 preferred
```

---

# 9. Common accuracy contract

The previous coil Pareto plot used centerline reconstruction error for native CSG and swept-surface chordal deviation for mesh. Replace this with a common finite-surface reference.

For both native and mesh, compute:

1. approximate symmetric two-sided Hausdorff distance;
2. RMS surface distance;
3. p95 surface distance;
4. maximum normal-angle error;
5. area and/or enclosed-volume error;
6. seam closure;
7. minimum inter-layer or coil–coil clearance;
8. topology/watertightness;
9. source centerline error as a separate secondary metric.

For plasma surfaces also compute:

- point classification disagreement;
- enclosed volume;
- surface area;
- field-period seam error;
- layer nesting;
- leakage and current closure.

Vary native patch tolerance and mesh faceting tolerance to produce a genuine accuracy–speed Pareto front.

A speed ratio is valid only when:

- source lineage matches;
- physical extent matches;
- transforms match;
- common error is reported;
- source, histories, thread count, CPU affinity and tally burden match.

---

# 10. Required benchmark ladder

Run both geometry-only and OpenMC end-to-end tests.

## 10.1 Primitive/kernel cases

```text
K0 built-in ZTorus
K1 exact spline-torus specialization
K2 exact torus forced through bezier_patch_v2
K3 exact torus forced through algebraic_proxy_v1
K4 shaped axisymmetric/Miller-like plasma
K5 synthetic helical plasma
K6 authoritative WISTELL-D plasma
K7 planar torus-equivalent coil
K8 analytic non-planar coil
K9 representative WISTELL-D coil 031
K10 complete 48-coil set
K11 selected most non-planar coil from all 13 configurations
```

Report:

```text
ns/distance
ns/classification
nodes visited
candidates
proxy roots
correction steps
local fallback
global oracle calls
maximum/p95 error versus oracle
```

## 10.2 OpenMC Tier 2 geometry-dominant cases

Use one executable, matched sources and minimal physics:

```text
O0 built-in ZTorus
O1 exact spline-torus specialization
O2 forced-general torus
O3 shaped axisymmetric plasma
O4 synthetic helical plasma
O5 WISTELL-D plasma
O6 planar coil
O7 representative non-planar coil
O8 complete coil set
```

## 10.3 OpenMC Tier 3 materialized cases

After Tier 2 correctness and performance gates:

- 14.1 MeV neutron source;
- identical simple materials;
- identical cells and tallies;
- neutron-only first;
- coupled photons later.

This determines whether geometry improvements materially affect real transport.

## 10.4 DAGMC traversal matrix

For the same H5M hashes:

```text
ordinary DAGMC OBB
Double Down / Embree DAGMC
```

For native:

```text
custom BVH
optional Embree BVH/user geometry
```

Do not combine results from different nodes or thread counts.

Use:

- at least one warm-up;
- at least seven measured repetitions;
- randomized method order;
- fixed affinity;
- medians, IQR and coefficient of variation;
- raw retained repetitions.

---

# 11. Performance targets

Current built-in `ZTorus` reference:

```text
774,121.5 histories/s
```

Use these as strong research targets, not excuses to distort correctness.

| Case | Minimum target | Preferred target |
|---|---:|---:|
| Exact spline torus specialization | 85% of `ZTorus` | 95% |
| Forced-general torus | 50% | 75% |
| Shaped axisymmetric | 50% | 75% |
| Synthetic helical | beat fine Double Down/DAGMC | at least 50% |
| WISTELL-D plasma | beat fine Double Down/DAGMC | at least 50% |
| Single non-planar coil | beat fine Double Down/DAGMC | at least 75% |
| Complete coil set | beat fine Double Down/DAGMC | at least 50%; 75% preferred |

Global invariants:

```text
wrong nearest roots = 0
missed roots = 0
false roots = 0
production global oracle calls = 0
lost particles = 0
```

Do not declare the project failed merely because arbitrary smooth surfaces cannot equal a quartic exactly. Determine the actual asymptotic and constant-cost boundary. But do not call 3–4% of `ZTorus` “close.”

---

# 12. Tests and regression protection

Add permanent tests for:

- exact torus with specialization on and off;
- four-root torus rays;
- shaped axisymmetric surface;
- synthetic helical surface;
- WISTELL-D source fixture;
- tangent, near-tangent and coincident rays;
- seams and `atan2` branch cuts;
- re-entry through nonconvex geometry;
- closely spaced blanket layers;
- planar torus-equivalent coil;
- non-planar analytic coil;
- representative WISTELL-D coil;
- complete 48-coil set;
- all 13 selected configurations;
- ordinary and Double Down DAGMC smoke runs;
- OpenMC default build with StellarCSG disabled.

For every mismatch, retain:

```text
origin
direction
expected root(s)
observed root
surface hash
method
tolerance
candidate patches/spans
iteration trace
```

Never delete the broad oracle. Keep it as an offline/reference implementation.

Run:

```bash
git diff --check
cmake/ctest Release
GCC or Clang ASan/UBSan
Python tests
OpenMC adapter tests
default-OFF OpenMC build
enabled OpenMC tests
geometry-debug runs
```

The optional `libmcpl` failure must remain separately classified and must not be confused with a StellarCSG regression.

---

# 13. Required retained outputs

Create:

```text
dev/stellarcsg/reports/
├── TORUS_CLASS_RESEARCH_STARTING_STATE.json
├── TORUS_CLASS_BASELINE.json
├── TORUS_CLASS_BASELINE.md
├── DOUBLE_DOWN_BUILD_AND_LINKAGE.json
├── DOUBLE_DOWN_MATCHED_RESULTS.json
├── DOUBLE_DOWN_MATCHED_RESULTS.md
├── EXACT_TORUS_OVERHEAD_REPORT.json
├── EXACT_TORUS_OVERHEAD_REPORT.md
├── BEZIER_PATCH_V2_REPORT.json
├── BEZIER_PATCH_V2_REPORT.md
├── ALGEBRAIC_PROXY_ATLAS_REPORT.json
├── ALGEBRAIC_PROXY_ATLAS_REPORT.md
├── COIL_NARROW_PHASE_V2_REPORT.json
├── COIL_NARROW_PHASE_V2_REPORT.md
├── COMMON_SURFACE_ACCURACY_V2.json
├── TORUS_CLASS_OPENMC_RESULTS.json
├── TORUS_CLASS_DAGMC_RESULTS.json
├── TORUS_CLASS_GATE_STATUS.json
└── TORUS_CLASS_FINAL_REPORT.md
```

Retain raw data under:

```text
dev/stellarcsg/benchmarks/raw/torus_class/
```

Retain plots under:

```text
dev/stellarcsg/plots/torus_class/
```

Required plots:

- exact torus cycle/call breakdown;
- throughput relative to `ZTorus`;
- common accuracy–speed Pareto curves;
- candidate patches and Newton/correction histograms;
- local fallback map;
- BVH node/candidate distributions;
- WISTELL-D source versus native surface;
- native versus ordinary DAGMC versus Double Down/Embree;
- single-coil and coil-set scaling;
- common finite swept-surface error;
- memory and initialization time.

Every plot must state hardware, threads, source lineage, histories/rays, method, accuracy tolerance and whether specialization was enabled.

---

# 14. Commit and push policy

Commit and push after each accepted phase:

```text
1. Preserve and reproduce the c67b68fd qualified baseline
2. Restore matched Double Down / Embree comparison
3. Remove exact-torus framework overhead
4. Add Bézier patch v2 compiler and traversal
5. Add local clipping/certification path
6. Prototype low-degree algebraic proxy atlas
7. Add piecewise analytic coil sweep
8. Add direct Bézier-tube coil intersector
9. Add common surface-accuracy metrics
10. Retain matched OpenMC/DAGMC/Embree results
11. Record final gate status and adoption boundary
```

Before each push:

```bash
git status --short
git diff --check
git add -A
git diff --cached --check
git commit -m "<specific message>"
git push origin <current research branch>
```

When the child branch is complete:

1. verify the original qualified branch still descends from `c67b68fd`;
2. rerun the full baseline and new suite in a fresh worktree;
3. fast-forward or cherry-pick only tested commits;
4. push the existing isolated qualified branch;
5. leave the archive branch untouched;
6. verify no PR exists.

---

# 15. Stop, redirect and negative-result rules

Do not spend unlimited time tuning one method.

After bounded implementation and profiling, preserve a negative result and redirect when:

- wrong-nearest-root events remain;
- candidate traversal remains effectively global;
- local clipping/certification routinely explodes in depth;
- algebraic proxies create unresolved phantom branches;
- exact correction removes the proxy’s speed advantage;
- a method uses too much memory or compilation time for practical devices;
- full coil-set scaling becomes linear;
- a method requires OpenMC changes too invasive for realistic adoption;
- the native method remains more than five times slower than matched fine Double Down/Embree after the algorithmic rewrite.

A failed hypothesis can still be a useful result. Record why it failed and retain the test corpus.

---

# 16. Final response required from Codex

Return:

1. final repository branch and SHA;
2. archive branch verification;
3. all commits created;
4. exact toolchain and dependency versions;
5. exact Double Down/Embree build and linkage evidence;
6. test counts;
7. wrong/missed/false-root counts;
8. raw repetitions and medians for every benchmark;
9. ratio to built-in `ZTorus`;
10. ratio to ordinary DAGMC;
11. ratio to Double Down/Embree;
12. common geometry error for each representation;
13. candidate patches/spans, nodes, corrections and fallback rates;
14. initialization, memory and geometry-time fraction;
15. lost-particle and geometry-debug results;
16. gate table with `PASS`, `FAIL`, `BLOCKED`, or `NOT_RUN`;
17. paths to reports, raw data and plots;
18. clear differentiation among:
    - exact torus specialization;
    - general periodic surface;
    - general coil surface;
    - complete coil set;
    - ordinary DAGMC;
    - Double Down/Embree;
    - geometry-only;
    - Tier 2 OpenMC;
    - Tier 3 OpenMC;
19. confirmation that default/upstream branches were untouched and no PR was created.

The central question to answer experimentally is:

> Can a generic stellarator surface or coil be compiled into local geometry whose runtime ray intersection is dominated by a small fixed amount of polynomial/proxy work, rather than iterative global search, while preserving exact native CSG semantics and zero wrong nearest roots?
