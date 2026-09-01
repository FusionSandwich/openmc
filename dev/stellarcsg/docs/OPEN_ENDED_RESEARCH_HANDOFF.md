# Open-ended research handoff: native CSG for stellarator plasmas, blanket layers and magnet coils in OpenMC

## Purpose of this handoff

This document is for an independent research and architecture agent.

It deliberately does **not** prescribe one implementation. Its purpose is to communicate:

- the user’s actual end goal;
- the current repository state;
- what has already been attempted;
- what produced useful results;
- what failed or remains incomplete;
- the constraints that cannot be traded away casually;
- the open questions that need a broad literature and method review.

The reviewing agent should remain open to approaches outside the current periodic-spline and swept-spline implementations. It should conduct its own primary-source research across computational geometry, computer graphics, CAD/CAGD, numerical analysis, algebraic geometry, high-performance ray tracing, Monte Carlo transport and OpenMC architecture before recommending the next major method.

---

# 1. User’s primary goal

The user wants OpenMC to model:

1. stellarator plasma boundaries;
2. shaped axisymmetric plasma boundaries;
3. first wall, breeder blanket, back wall, shield and vessel layers;
4. finite planar and non-planar magnet coils;

using **native constructive solid geometry**, rather than using CAD/DAGMC as the transport geometry.

The desired user workflow is:

```text
plasma equilibrium or sampled surface
+ magnet centerlines and cross sections
+ spatially varying radial build
+ materials and source
        ↓
generic compiler
        ↓
native OpenMC CSG surfaces and cells
+ companion local tally meshes
```

A new device should require new coefficient/data files, not device-specific C++ and not recompiling generated code for each device.

The user’s performance objective is stronger than “slightly faster than DAGMC”:

> Make the general stellarator and coil CSG paths as fast as possible and, ideally, close to the performance of OpenMC’s built-in `ZTorus` surface.

The built-in torus is the performance reference because it demonstrates how fast a native analytic CSG primitive can be.

The user also wants:

- easy construction of nested breeding-blanket layers;
- local magnet coordinates and local tally data;
- geometry that can be compared fairly with ParaStell/DAGMC;
- eventual usefulness and maintainability sufficient for possible OpenMC adoption;
- no permanent mandatory dependency on CAD or MOAB for the native path;
- robust nearest-surface intersections, including tangent and coincident cases;
- no false speed claims based on incomparable geometries or hardware.

---

# 2. What counts as success

The strongest success would be:

```text
generic stellarator plasma native CSG
generic non-planar finite coil native CSG
zero wrong nearest roots
zero lost particles
easy nested blanket construction
same source geometry as reference
matched accuracy
same performance order as ZTorus
faster than ordinary and Double Down/Embree DAGMC
clean opt-in OpenMC integration
```

A method does not need to equal the quartic torus in every case to be useful. However, a result near 3–4% of `ZTorus` throughput is not the desired endpoint.

Usability also matters:

- one-command or simple Python model generation;
- explicit units and source hashes;
- clear rejection of unsupported topology;
- stable local coordinates;
- reproducible geometry and benchmark manifests;
- no hidden device-specific assumptions.

---

# 3. Repository state that must be preserved

```text
Repository: FusionSandwich/openmc
Active isolated branch: codex/stellarcsg-native-csg-foundation-20260828
Qualified commit: c67b68fdaf7be2049308db7da449f14a25123847
Preservation branch: archive/stellarcsg-qualified-c67b68fd-20260831
```

No pull request is required. Default and upstream OpenMC branches are not to be modified.

The experimental build option remains default off:

```text
OPENMC_ENABLE_EXPERIMENTAL_STELLARCSG=OFF
```

The current branch contains important reusable work and evidence. Future work should be additive, selectable and reversible. The current algorithms should remain available as baselines and correctness references until a replacement passes the same tests.

---

# 4. Current implementation in broad terms

## 4.1 Plasma and blanket surface representation

The current design represents a smooth toroidal surface using a periodic reference axis and a periodic radial spline:

```text
F(x,y,z)=rho-rho_s(theta,phi)
```

It supports:

- exact circular torus specialization;
- shaped axisymmetric behavior;
- nonaxisymmetric periodic surfaces;
- analytical gradients and normals;
- hash-bound HDF5 coefficient files;
- OpenMC Python/XML/C++ integration;
- conservative local patches;
- front-to-back BVH traversal;
- local proxy intersections;
- damped Newton correction;
- bounded local recovery;
- broad independent root oracle for qualification.

The production path no longer calls the broad global oracle.

## 4.2 Coil representation

The current coil design uses:

- periodic cubic centerline splines;
- rotation-minimizing frames;
- finite circular or elliptical cross sections;
- local centerline spans;
- exact Bézier centerline hulls;
- conservative swept boxes;
- capsule proxies;
- local narrow-phase solves;
- per-coil span BVHs;
- one shared top-level BVH for the full coil set;
- broad independent coil oracles for testing.

## 4.3 Blanket geometry

The intended layer construction uses physical distance along the LCFS normal:

```text
r_k(theta,phi) = r_LCFS(theta,phi) + d_k(theta,phi) n_hat(theta,phi)
```

The architecture is designed to produce nested CSG regions such as:

```text
plasma                 = -S0
first wall             = +S0 & -S1
breeder                = +S1 & -S2
back wall              = +S2 & -S3
shield                 = +S3 & -S4
vacuum vessel          = +S4 & -S5
```

The complete optimized blanket-family implementation and performance test remain unfinished.

---

# 5. What was tried

## 5.1 Broad reference ray solver

The first generic surface method searched the complete ray interval, sampled many points, refined resolution, searched derivative stationary points and bisected candidate roots.

What it achieved:

- strong correctness behavior;
- an independent reference answer;
- handling of sign-changing and tangent roots;
- useful regression fixtures.

Why it was unsuitable for production:

- it repeated global work for nearly every surface query;
- WISTELL-D throughput was approximately 89 histories/s in the retained baseline;
- non-planar coil performance was effectively unusable.

Conclusion:

> Keep it as an oracle; do not return it to the hot path.

## 5.2 Exact torus specialization

The periodic-spline surface recognizes an exact torus and delegates to a compact quartic-style path.

Qualified result:

```text
Built-in ZTorus:                       774,121.5 histories/s
Periodic-spline torus specialization:  351,233 histories/s
```

This was much faster than fine DAGMC and showed that a native smooth custom surface can be competitive when the intersection reduces to compact fixed-degree algebra.

What remains unresolved:

- the custom torus path is still only about 45% of built-in `ZTorus`;
- there is likely avoidable framework or wrapper overhead;
- the exact torus does not validate the cost of a generic stellarator surface.

## 5.3 Local periodic patch/BVH method

The global surface scan was replaced by:

- conservative local spline-span patches;
- proxy triangles;
- flattened front-to-back BVH2;
- projected damped Newton correction;
- local bounded recovery.

Qualified WISTELL-D result:

```text
Native periodic CSG: 26,643.8 histories/s
Fine direct DAGMC:   21,511.8 histories/s
Native/DAGMC:        1.2386
```

This was roughly a 299-fold improvement over the old global path and passed initial correctness tests.

What remains poor:

```text
11.82672 microseconds per distance
66.713 BVH nodes/ray
6.696 candidate patches/ray
16.953 Newton iterations/ray
0.464 local subdivision calls/ray
```

The general WISTELL-D path is only about 3.4% of built-in `ZTorus`.

The short OpenMC plasma comparison also had native leakage around 0.9955 versus 1.0 for fine DAGMC. The speed result therefore exists, but full common-accuracy and transport closure are incomplete.

## 5.4 Local swept-coil span method

The global centerline search was replaced by:

- cubic span bounds;
- span BVH;
- capsule proxies;
- local correction;
- bounded local fallback.

Representative single-coil result:

```text
Native:       432,436 histories/s
Fine DAGMC:   910,634 histories/s
Native ratio: 0.4749
```

The native single coil remained about 2.1 times slower than fine DAGMC.

Kernel behavior was much better than the plasma surface:

```text
631.624 ns/distance
0.728 candidate spans/ray
2.015 Newton iterations/ray
3.7% local bounded fallback
```

The single-coil comparison also illustrates why histories/s alone does not isolate primitive speed: its DAGMC case exceeded the separately measured built-in torus throughput, which likely reflects a different number or pattern of geometry calls per history.

## 5.5 Shared complete-coil-set BVH

A shared top-level BVH was added over all 48 WISTELL-D coils.

Qualified result:

```text
48-coil native CSG: 289,656 histories/s
48-coil fine DAGMC: 49,189.5 histories/s
Native/DAGMC:       5.8886
```

Adding 48 times as many coils increased native distance cost only about 2.29 times. This is one of the clearest successes.

Interpretation:

- the set-level scene acceleration is working;
- the complete set can outperform a very large triangle mesh;
- this does not prove that the local single-coil intersection is optimal;
- the complete set still runs at only about 37% of built-in `ZTorus`.

## 5.6 Ordinary DAGMC comparison

Same-lineage coarse and fine DAGMC models were generated for several cases.

What worked:

- ordinary transport completed with zero lost particles;
- independent mesh checks found watertight, nonoverlapping meshes;
- retained mesh error and volume data exist.

Unresolved issue:

- OpenMC geometry-debug reports overlap between an explicit DAGMC volume and the implicit complement even where independent DAGMC utilities report no overlap;
- this complaint is retained rather than suppressed.

## 5.7 Double Down / Embree

The latest pinned DAGMC binary was named:

```text
nompi_nodoubledown
```

Therefore the most recent matched test did not run Double Down/Embree.

This should be treated as an environment/build omission, not evidence that Embree is intrinsically unavailable. An earlier Double Down result existed under a different model/node/thread contract and cannot be combined numerically with the latest tests.

A fair future comparison requires ordinary and Double Down DAGMC builds from the same source commits, using the same H5M hash and OpenMC model on the same hardware.

---

# 6. What has worked well

The following should be retained unless evidence shows a better replacement:

1. **Generic coefficient-driven geometry.** New devices do not require new C++.
2. **Native OpenMC half-space semantics.** The surfaces behave like CSG surfaces rather than a mesh universe.
3. **Independent broad oracles.** They provide a trustworthy way to test optimized paths.
4. **No global oracle in production.**
5. **Exact torus specialization.**
6. **Shared coil-set BVH.**
7. **Rotation-minimizing coil frames.**
8. **Hash-bound source provenance.**
9. **Opt-in OpenMC integration, default off.**
10. **Retention of negative results rather than qualification inflation.**
11. **Substantial improvement over the original global methods.**
12. **Initial shape coverage across thirteen coil configurations.**

---

# 7. What has not yet worked or remains incomplete

1. Generic WISTELL-D plasma is still roughly 29 times slower than built-in `ZTorus`.
2. Exact custom torus itself is about 2.2 times slower than built-in `ZTorus`.
3. Representative single non-planar coil is slower than fine DAGMC.
4. Double Down/Embree has not been rerun under the current matched contract.
5. Forced-general torus OpenMC performance was not run.
6. Shaped-axisymmetric performance was not run.
7. Synthetic-helical distance and OpenMC performance gates were not run.
8. Tier 3 materialized neutron transport was not run.
9. Complete optimized blanket-family construction/performance was not run.
10. Symmetric Hausdorff and normal-angle comparisons are incomplete.
11. Plasma leakage/current closure needs investigation.
12. High-statistics real-device oracle campaigns remain limited.
13. Local fallback remains above the desired level.
14. OpenMC adoption review has not occurred.
15. The method’s supported topology is narrower than arbitrary CAD.
16. It is not yet established that generic smooth CSG can reach torus-class speed on the target hardware.

---

# 8. Source-derived context

## 8.1 ParaStell multi-equilibrium study

Miralles-Dolz et al. generated neutronics-ready models from a database of 45 VMEC equilibria and successfully completed 38. Seven failed mainly because successive radial-build surfaces intersected through excessive torsion or interpolation effects.

The paper:

- uses ParaStell, CAD/mesh generation and DAGMC;
- constructs layers by outward normal offsets;
- models one complete field period for NFP greater than two;
- excludes magnets from the presented models;
- demonstrates why explicit admissibility/rejection tests are needed;
- provides a diverse geometry corpus for future testing.

It does not answer whether a new native spline/algebraic CSG surface can be as fast as `ZTorus`.

## 8.2 SBGeom/deterministic workflow

Bogaarts and Warmer present:

- Fourier/parametric stellarator surfaces;
- a physical distance coordinate beyond the LCFS;
- nonuniform distance fields `d(theta,phi)`;
- equal-arc-length poloidal parameterization;
- coil-winding-surface fitting;
- finite coils with rotation-minimizing frames;
- deterministic transport;
- a stellarator half-module boundary transformation;
- automated variance reduction.

The geometry ideas are relevant. The paper’s statement that CSG is unsuitable concerns conventional CSG representations available to those workflows; this project is testing whether new custom smooth CSG primitives change that conclusion.

The paper does not provide a near-`ZTorus` ray-intersection method for arbitrary surfaces.

---

# 9. Open research questions

The reviewing agent should not assume that periodic radial splines plus Newton iteration are the final answer.

Key questions include:

1. Is `ZTorus`-class performance feasible for a generic smooth stellarator surface on a CPU, or is there a defensible lower bound separating analytic quadrics/quartics from arbitrary surfaces?
2. Which surface representation minimizes total OpenMC work, not only mathematical approximation error?
3. Can the source surface be compiled into fixed-degree local algebraic equations?
4. Can exact or approximate implicitization produce reliable ray polynomials without phantom branches?
5. Are direct parametric patch methods faster when paired with better bounds and seeds?
6. Can structured toroidal/poloidal topology replace general-purpose BVH traversal?
7. Would a hierarchy of specializations cover most practical devices more effectively than one universal method?
8. Can neighboring surfaces in a blanket family share one lookup and basis evaluation?
9. Can particle coherence or previous patch coordinates be used safely in OpenMC?
10. What is the best narrow phase for a rotation-minimizing swept coil?
11. Can coils be decomposed into analytic line/arc/biarc segments with controlled full-surface error?
12. Can Embree user geometry or hardware ray-tracing structures accelerate native CSG without turning the geometry into triangles?
13. Would a custom OpenMC universe/scene accelerator be more appropriate than many independent `Surface` calls?
14. How should tangent and repeated roots be certified without expensive global scans?
15. What common error metric is sufficient to claim native and mesh geometry are physically equivalent?
16. What interface would OpenMC maintainers be likely to accept?
17. Which methods remain thread-safe, deterministic and dependency-light?
18. How should multi-chart or non-star-shaped surfaces be supported?
19. Could a different coordinate map substantially simplify intersection?
20. Is a hybrid method—analytic where possible, general elsewhere—the most realistic route?

---

# 10. Broad literature-review mandate

Conduct a primary-source review across, at minimum:

- computational geometry;
- computer-aided geometric design;
- parametric and implicit surface intersection;
- algebraic geometry and approximate implicitization;
- Bézier and B-spline ray tracing;
- subdivision surface ray tracing;
- interval arithmetic and certified roots;
- Bernstein polynomial methods;
- resultants, moving lines/surfaces and syzygies;
- ray tracing quadrics, tori and higher algebraic surfaces;
- coherent and packet ray traversal;
- BVH, OBB, k-DOP, spatial grids and structured indexing;
- Embree and user-defined geometry;
- hardware ray tracing;
- ray/fiber, ray/tube and swept-surface intersection;
- Monte Carlo particle-transport geometry kernels;
- OpenMC, MCNP, Serpent, Geant4 and related geometry designs;
- finite-element/isogeometric analysis geometry kernels;
- CAD kernel intersection approaches;
- signed-distance, level-set and R-function methods;
- high-order mesh-free or spectral geometry representations.

Search recent and classic work. Prefer original papers, official code, dissertations and maintained libraries.

Do not limit the review to the methods already proposed. Identify at least ten genuinely distinct candidate directions.

For each candidate, assess:

```text
representation
runtime intersection complexity
nearest-root guarantee
tangent/repeated-root behavior
inside/outside semantics
precomputation cost
memory
accuracy control
device generality
blanket nesting
coil applicability
threading/SIMD
dependency burden
OpenMC integration invasiveness
license
evidence of actual performance
```

Rank candidates, but preserve uncertainty.

---

# 11. Examples of directions to investigate, not mandated solutions

These are prompts for exploration, not requirements:

- tensor-product Bézier patches with direct bilinear or biquadratic seeds;
- interval/Bernstein clipping;
- low-degree approximate implicitization;
- monoid implicitization and inverse maps;
- local resultants;
- Chebyshev/minimax local approximants;
- rational Bézier or NURBS patch intersectors;
- subdivision surfaces with precomputed patches;
- local osculating quadrics or tori;
- structured `(theta,phi)` cell lookup instead of a generic BVH;
- wide or compressed BVHs;
- oriented/skewed patch bounds;
- ray packets and SIMD;
- per-particle coherence caches;
- algebraic surface families tailored to stellarators;
- multi-chart atlases;
- analytic line/arc/biarc coil sweeps;
- direct Bézier-tube/ray-fiber algorithms;
- Embree round curves;
- Embree user geometry;
- GPU or hardware-RT prototypes;
- custom CSG scene/universe acceleration;
- hybrid native CSG plus local exact mesh only for unsupported regions;
- offline symbolic or numerical code generation for generic fixed-degree kernels, without device-specific recompilation;
- machine-learned seeds only if correctness remains independently certified.

The reviewing agent may reject all of these and recommend a different method.

---

# 12. Fair benchmarking requirements

Any future recommendation must distinguish:

```text
primitive intersection cost
point classification cost
surface calls per history
crossings per history
initialization time
active transport time
memory
accuracy
```

A single-coil DAGMC run exceeding a separate `ZTorus` run does not prove triangles are intrinsically faster; the models may create different workloads.

Use a normalized ray corpus in addition to OpenMC histories/s.

Compare native, ordinary DAGMC and Double Down/Embree with:

- identical source geometry;
- identical H5M for the two DAGMC traversals;
- identical OpenMC executable where possible;
- same machine and CPU affinity;
- same thread count;
- same source bank;
- same histories/batches;
- same materials and tallies;
- randomized run order;
- multiple repetitions;
- common geometry-error metrics.

Retain raw results.

---

# 13. Research deliverable requested from the reviewing agent

The first response should not immediately rewrite the code.

Produce:

1. a concise restatement of the user’s goal;
2. an audit of the current implementation and benchmark fairness;
3. a broad source-cited literature map;
4. at least ten candidate algorithmic directions;
5. a comparison matrix;
6. a shortlist of two to four methods worth prototyping;
7. one low-risk optimization track and one high-risk/high-reward track;
8. a preservation-safe implementation plan;
9. decisive microbenchmarks that can reject weak ideas quickly;
10. estimated performance requirements to reach:
    - 85% of `ZTorus` for exact custom torus;
    - 50% for WISTELL-D plasma;
    - 75% for a single coil;
    - 50–75% for the complete coil set;
11. an adoption-oriented OpenMC architecture recommendation;
12. explicit uncertainties and reasons a target may be infeasible.

After the review is accepted, implement prototypes on separate selectable paths and retain all current work.

---

# 14. Preservation and repository instructions for any future agent

Before changing code:

```bash
git fetch --all --tags --prune
git switch codex/stellarcsg-native-csg-foundation-20260828
git pull --ff-only
git merge-base --is-ancestor \
  c67b68fdaf7be2049308db7da449f14a25123847 \
  HEAD
git rev-parse origin/archive/stellarcsg-qualified-c67b68fd-20260831
git status --short --branch
```

Never overwrite the archive branch.

Use a new worktree/branch for high-risk prototypes. No force-push and no PR are required.

Keep current methods selectable:

```text
reference_oracle
exact_torus
legacy_periodic_patch
legacy_swept_span
shared_coil_set_bvh
```

New approaches should be additional named methods until they pass.

Preserve:

- current raw benchmark results;
- current plots;
- current H5M hashes;
- current WISTELL-D source hashes;
- failure fixtures;
- geometry-debug complaints;
- negative gate statuses;
- old performance numbers;
- independent oracles.

A later result may supersede an earlier conclusion, but it should not erase the earlier evidence.

---

# 15. Decision framework

Continue a candidate method when it shows:

- zero wrong roots;
- local rather than global work;
- controllable accuracy;
- promising normalized primitive cost;
- realistic OpenMC integration;
- stable performance across several configurations.

Stop or narrow it when:

- it depends on global scanning;
- tangent handling dominates;
- local patch counts remain high;
- proxy branches cannot be rejected safely;
- memory/precomputation becomes impractical;
- it only works for one device;
- it requires mandatory heavyweight dependencies unacceptable to OpenMC;
- it remains far slower than Double Down/Embree at matched accuracy after bounded optimization.

A negative result is acceptable when it clearly establishes a boundary and preserves evidence.

---

# 16. Final mission statement

The project is not merely to construct a mathematically valid stellarator surface. It is to determine whether a compact family of new native OpenMC CSG primitives can provide:

- generic stellarator and shaped-axisymmetric plasma geometry;
- easy nested blanket and shield layers;
- generic finite non-planar coil geometry;
- robust nearest intersections;
- local coordinates for magnet radiation data;
- no CAD or triangle transport for supported surfaces;
- performance approaching OpenMC’s built-in analytic CSG.

The independent agent should treat the current implementation as valuable evidence and infrastructure, not as the only possible solution.
