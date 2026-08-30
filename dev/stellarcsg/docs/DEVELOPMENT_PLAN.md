# Development and Test Plan: Native Custom CSG Geometry for Stellarator Monte Carlo in OpenMC

**Working project name:** `StellarCSG`  
**Primary objective:** Generate native OpenMC constructive-solid-geometry (CSG) models directly from plasma-surface and magnet-curve data, without CAD or DAGMC in the particle-tracking path, while generating companion meshes for spatially resolved magnet tallies.  
**Document type:** Technical development plan, feasibility gates, and executable Codex prompt set  
**Version:** 1.0  
**Date:** 2026-08-27  

---

## Executive summary

This project should test whether a stellarator can be represented in OpenMC by a small number of **new smooth CSG primitives**, rather than by a large triangulated CAD/DAGMC model or by a decomposition into thousands of conventional planes and quadrics.

The proposed system would let a user provide:

1. a plasma surface, such as a VMEC equilibrium surface, a sampled parametric surface, or a compatible Python object;
2. magnet centerlines or finite-build magnet definitions;
3. a spatially varying radial build for first wall, breeder, shield, vessel, and other components;
4. material definitions and a fusion source;

and automatically produce:

- a native OpenMC CSG geometry containing one smooth primitive per plasma/blanket boundary and one or more smooth swept primitives per magnet;
- OpenMC cells and materials built from Boolean half-spaces of those primitives;
- a companion layer-aligned and coil-aligned tally mesh;
- stable local coordinates and IDs for every blanket and magnet tally element;
- OpenMC tallies for energy-resolved flux, heating, damage-energy, reaction rates, and boundary current;
- geometry and neutronics benchmarks against built-in CSG and DAGMC reference models.

The first implementation should **not** attempt to support every possible arbitrary solid. It should implement two reusable families that cover the dominant low- and medium-fidelity stellarator geometry:

1. **PeriodicSplineSurface** for plasma, first-wall, blanket, shield, and vessel surfaces.
2. **SweptSplineSurface** for finite-build non-planar magnet coils.

These should be generic geometry classes. Device-specific geometry is represented by coefficients and control data loaded from a versioned HDF5 file. A new stellarator should therefore require **new input data, not new C++ code or recompilation**.

The transport geometry and tally mesh must remain separate:

- OpenMC transports particles on the smooth CSG surfaces.
- A conformal or near-conformal tetrahedral/hexahedral mesh is generated from the same parameterization only for tallies, visualization, data export, and optional deterministic coupling.

That distinction is central. An H5M or Exodus tally mesh does not imply DAGMC transport. OpenMC can use native CSG for tracking while scoring into an unstructured mesh.

### Recommended decision

Proceed through a strict sequence of proof-of-principle gates:

1. Standalone geometry-kernel tests using an axisymmetric torus with an exact answer.
2. Native OpenMC integration for one periodic spline surface.
3. Nested smooth shells and an automatically generated tally mesh.
4. A synthetic non-axisymmetric helical stellarator.
5. A generic input adapter for VMEC/sampled surfaces.
6. A generic swept-coil primitive.
7. A full WISTELL-D or HELIAS comparison against DAGMC.

Do **not** begin with the full WISTELL-D model. The project is worth continuing only if the custom primitive is robust and produces a material speed or memory advantage over DAGMC/Embree at matched geometric accuracy.

### Core go/no-go targets

The proposed method should continue toward a research-grade tool only if it demonstrates:

- no missed or false surface crossings in a large adversarial ray suite;
- geometry errors that can be systematically reduced below the neutronics tolerance;
- stable behavior for grazing and tangent rays;
- native OpenMC tally agreement with equivalent built-in CSG and DAGMC models;
- at least about **1.3–1.5× end-to-end transport speedup** over DAGMC/Embree for a representative stellarator model, or a comparably valuable reduction in initialization time and memory;
- one-command model generation from supported plasma and magnet inputs without CAD;
- stable mapping from each CSG component to local tally-mesh coordinates.

---

# 1. What this project is and is not

## 1.1 Definition of “native custom CSG”

For this project, a geometry is native CSG only when OpenMC transports particles by evaluating smooth surface primitives of the form

\[
F(\mathbf{x})=0,
\]

and represents cells as Boolean combinations of the corresponding positive and negative half-spaces.

The following do **not** count as the desired result:

- STL or triangle-surface tracking;
- DAGMC/MOAB transport;
- converting each triangle or small patch to an individual plane;
- importing CAD into a ray-tracing kernel;
- voxel transport;
- using a mesh as the transport geometry.

The companion tally mesh is permitted because it does not define the particle-tracking geometry.

## 1.2 Why OpenMC can support this in principle

At the audited OpenMC development snapshot `7ecd3a9613f06ed0dc22368c9540faf4aaacc65f`, the C++ `Surface` abstraction requires the operations needed by a new primitive:

- `evaluate(Position)` for the implicit function;
- `distance(Position, Direction, coincident)` for the next ray intersection;
- `normal(Position)` for the local surface normal;
- `bounding_box(...)` for spatial bounds;
- serialization to HDF5.

Reference: [OpenMC `Surface` interface](https://github.com/openmc-dev/openmc/blob/7ecd3a9613f06ed0dc22368c9540faf4aaacc65f/include/openmc/surface.h).

The architecture therefore already supports a new compiled CSG surface class. What does not currently exist is a suitable generic stellarator surface implementation and the corresponding Python/input-generation layer.

## 1.3 Primary scientific purpose

The initial scientific application is to generate spatially and directionally resolved radiation fields at superconducting magnets as reactor geometry, blanket composition, shield composition, and magnet position are varied.

The principal output should remain the radiation field:

\[
\phi_n(E,\mathbf{x}),\qquad
\phi_\gamma(E,\mathbf{x}),\qquad
J(E,\Omega,\mathbf{x}),
\]

not TBR or one scalar DPA value.

TBR, total heating, and damage-energy may be retained as secondary checks and response metrics.

## 1.4 Explicit non-goals for the first implementation

The first implementation should not attempt to:

- replace every OpenMC surface with a runtime Python callback;
- represent arbitrary industrial CAD solids;
- resolve micrometre-scale REBCO layers throughout the full reactor;
- implement a general NURBS CAD kernel inside OpenMC;
- guarantee support for every non-star-shaped surface in version 1;
- provide full stellarator-symmetry boundary conditions before full-device geometry works;
- predict critical-current degradation directly;
- upstream the code to OpenMC before independent geometry and transport verification.

---

# 2. Proposed end-user workflow

The intended user experience should resemble the current Python-based OpenMC examples. The following API is a **proposed design**, not an existing OpenMC interface.

## 2.1 Minimal Python example

```python
import openmc
import stellarcsg

# 1. Plasma surface from VMEC or another supported source
plasma = stellarcsg.PlasmaSurface.from_vmec(
    "wout_device.nc",
    surface_label=1.0,
    n_field_periods="read-from-file",
)

# 2. Magnet centerlines and finite cross sections
coils = stellarcsg.CoilSet.from_filaments(
    "coils.dat",
    cross_section=stellarcsg.RoundedRectangle(
        width=58.0,
        height=58.0,
        corner_radius=3.0,
        units="cm",
    ),
    frame="rotation-minimizing",
)

# 3. Spatially varying reactor radial build
radial_build = stellarcsg.RadialBuild(
    base_surface=plasma,
    layers=[
        stellarcsg.Layer("sol", 5.0, material=None),
        stellarcsg.Layer("first_wall", 2.0, material="first_wall"),
        stellarcsg.Layer(
            "breeder",
            thickness=stellarcsg.ThicknessField.from_yaml("breeder.yaml"),
            material="breeder",
        ),
        stellarcsg.Layer(
            "shield",
            thickness=stellarcsg.ThicknessField.from_yaml("shield.yaml"),
            material="shield",
        ),
        stellarcsg.Layer("vessel", 6.0, material="vessel"),
    ],
)

# 4. Compile device-specific data into generic CSG primitives
compiled = stellarcsg.compile_geometry(
    plasma=plasma,
    radial_build=radial_build,
    coils=coils,
    representation="periodic-bicubic-spline",
    output="compiled_geometry.h5",
    tolerance=0.05,   # cm, initial feasibility value
)

# 5. Produce an OpenMC model using native CSG transport
builder = stellarcsg.OpenMCBuilder(compiled)
model = builder.make_model(materials="materials.py")

# 6. Generate companion tally meshes from the same parameterization
meshes = compiled.make_tally_meshes(
    blanket_resolution=(64, 128, 4),       # theta, phi, radial bins/layer
    coil_resolution=(120, 8, 8),           # arc, local-u, local-v bins
    formats=("exodus", "h5m", "vtu"),
)

# 7. Add local magnet spectra
model.tallies += stellarcsg.make_magnet_spectrum_tallies(
    model=model,
    coil_mesh=meshes.coils,
    energy_edges="ccfe-709-plus-fine-tail",
    include_photons=True,
)

model.export_to_xml()
openmc.run()
```

## 2.2 Supported input adapters

Version 1 should support these inputs in order of priority:

1. **VMEC equilibrium file** for plasma surfaces.
2. **Explicit sampled surface** on a periodic \((\theta,\phi)\) grid.
3. **Python parametric surface object** implementing a small protocol:
   - `position(theta, phi)`;
   - optionally `normal(theta, phi)`;
   - field-period count and units.
4. **Coil filament point files** in a documented format.
5. **SIMSOPT-compatible coil curves** or a neutral interchange file exported from SIMSOPT.
6. Later: DESC surfaces, surface point clouds, or other equilibrium formats through adapters.

No supported input should require CAD.

## 2.3 Output artifacts

Each compiled case should contain:

```text
case/
├── geometry_input.yaml
├── compiled_geometry.h5
├── geometry_manifest.json
├── geometry.xml
├── materials.xml
├── settings.xml
├── tallies.xml
├── meshes/
│   ├── blanket_tally.e
│   ├── blanket_tally.h5m
│   ├── blanket_tally.vtu
│   ├── coils_tally.e
│   ├── coils_tally.h5m
│   ├── coils_tally.vtu
│   └── mesh_map.h5
├── qa/
│   ├── fit_errors.csv
│   ├── nested_surface_clearance.csv
│   ├── random_ray_results.h5
│   ├── volume_comparison.csv
│   └── geometry_hashes.json
└── run/
    ├── statepoint.*.h5
    ├── summary.h5
    └── performance.json
```

---

# 3. Recommended software architecture

## 3.1 Do not begin as a large OpenMC fork

Start with a standalone library:

```text
stellarcsg/
├── cpp/                 # Geometry kernel and ray intersections
├── python/              # Input adapters, fitting, model generation
├── tests/               # Analytic, property-based, and OpenMC tests
├── benchmarks/          # Geometry-only and neutronics benchmarks
├── schemas/             # HDF5/YAML/JSON contracts
├── examples/            # Torus, helical torus, VMEC, coil examples
└── third_party/         # Only pinned, license-compatible dependencies
```

The standalone C++ kernel should be independently testable before it is called from OpenMC.

OpenMC integration should then be a thin wrapper around the validated kernel:

```text
OpenMC Surface subclass
    -> load compiled coefficients
    -> call stellarcsg evaluate/distance/normal/bbox
```

This reduces the risk of confusing geometry-kernel bugs with OpenMC transport behavior.

## 3.2 Main components

### A. Geometry input layer

Responsible for reading VMEC/sampled surfaces and coil centerlines, validating units and periodicity, and producing a common internal representation.

### B. Geometry compiler

Responsible for fitting or constructing the generic CSG primitive coefficients, checking admissibility, and writing a hash-bound HDF5 geometry file.

### C. C++ geometry kernel

Responsible for fast and robust:

- point classification;
- surface evaluation;
- local coordinate inversion;
- ray intersection;
- surface normal calculation;
- bounding-box and patch lookup;
- intersection diagnostics.

### D. OpenMC adapter

Responsible for:

- new Python `Surface` classes;
- XML/HDF5 serialization;
- C++ surface construction;
- OpenMC cell generation;
- plotting, geometry-debug, and regression tests.

### E. Tally-mesh generator

Responsible for layer-aligned and coil-aligned meshes and stable local IDs.

### F. Benchmark and evidence system

Responsible for matched CSG/DAGMC models, common sources, tally definitions, timing, memory, geometry error, and uncertainty comparison.

---

# 4. Mathematical geometry design

## 4.1 Required generic surface operations

Every custom CSG primitive must provide:

\[
F(\mathbf{x})
\]

for inside/outside classification,

\[
\nabla F(\mathbf{x})
\]

for normals and Newton derivatives, and

\[
d(\mathbf{x},\Omega)
=
\min\{t>0:F(\mathbf{x}+t\Omega)=0\}
\]

for the nearest positive ray intersection.

The implementation must return the **nearest** valid positive intersection, not merely any root.

## 4.2 Primary plasma/blanket representation: periodic bicubic radial spline

For the initial supported class, define a toroidal reference axis in cylindrical coordinates:

\[
R_a(\varphi),\qquad Z_a(\varphi).
\]

For a Cartesian point \((x,y,z)\), calculate

\[
R=\sqrt{x^2+y^2},
\qquad
\varphi=\operatorname{atan2}(y,x).
\]

Then define local poloidal coordinates

\[
q_R=R-R_a(\varphi),
\qquad
q_Z=z-Z_a(\varphi),
\]

\[
\rho=\sqrt{q_R^2+q_Z^2},
\qquad
\theta=\operatorname{atan2}(q_Z,q_R).
\]

Represent the surface radius as a periodic tensor-product spline:

\[
\rho_s(\theta,\varphi)
=
\sum_{i,j} c_{ij}
B_i^{(p)}(\theta)
B_j^{(q)}(N_{\mathrm{FP}}\varphi).
\]

The implicit surface is

\[
F(x,y,z)=\rho-\rho_s(\theta,\varphi).
\]

The negative half-space is inside the surface when the orientation contract is satisfied.

### Why this is the primary candidate

- It is not tied to one device.
- It uses compact spline support, so only a small local coefficient stencil is evaluated at a point.
- It naturally preserves field periodicity.
- It can be fitted from VMEC, jax-sbgeom, ParaStell, or sampled points.
- The same parameterization can generate a tally mesh.
- Surface derivatives are analytical and local.

### Mandatory admissibility test

The representation is valid only when each surface is single-valued in the chosen coordinates:

\[
\rho=\rho_s(\theta,\varphi).
\]

The compiler must test this rather than assume it.

For every toroidal plane and sampled poloidal ray:

- confirm exactly one outward intersection with the surface;
- confirm positive Jacobian orientation;
- confirm no self-intersection;
- confirm minimum radius and curvature bounds;
- record the margin to failure.

If a surface fails, the compiler must reject it or route it to a documented fallback. It must not silently force a bad fit.

## 4.3 Fallback 1: multi-chart periodic spline

Some surfaces may not be single-valued around one reference axis. A multi-chart surface can split the poloidal domain into overlapping charts:

\[
F_k(\mathbf{x})=0,\qquad k=1,\ldots,K.
\]

Each chart has:

- a valid local coordinate map;
- a bounded parameter domain;
- overlap with neighboring charts;
- a conservative spatial bounding box;
- deterministic ownership rules at chart overlaps.

The full surface is a patch set managed by one CSG primitive. This remains a smooth custom primitive rather than triangle geometry, but ray intersection must search candidate patches.

Version 1 need not implement multi-chart transport if the initial target devices pass the single-chart test. It should nevertheless define the interface so the design does not become device-specific.

## 4.4 Fallback 2: compact implicit RBF surface

For a more general smooth closed surface, fit

\[
F(\mathbf{x})
=
\sum_i w_i\psi\!\left(\frac{\|\mathbf{x}-\mathbf{x}_i\|}{h_i}\right)
+p(\mathbf{x}).
\]

Use compactly supported radial basis functions and a spatial index so only nearby centers are evaluated.

This fallback is more general but should not be the first implementation because:

- nearest-root certification is harder;
- memory and neighbor lookup may reduce the speed advantage;
- generating exactly nested offset surfaces is less straightforward;
- local tally coordinates are not as natural.

The feasibility project should compare it only if the periodic spline fails important target geometries.

## 4.5 Generic magnet representation: swept spline surface

A magnet is represented by a periodic centerline

\[
\mathbf{c}(s),\qquad s\in[0,L),
\]

and a local orthonormal frame

\[
\{\mathbf{T}(s),\mathbf{N}(s),\mathbf{B}(s)\}.
\]

Use a rotation-minimizing frame by default to avoid arbitrary twist.

For a point near the coil, determine its local centerline coordinate \(s_*\), then

\[
u=(\mathbf{x}-\mathbf{c}(s_*))\cdot\mathbf{N}(s_*),
\]

\[
v=(\mathbf{x}-\mathbf{c}(s_*))\cdot\mathbf{B}(s_*).
\]

A generic smooth cross-section function defines the boundary:

\[
g(u,v;s_*)=0.
\]

Supported initial cross sections should include:

- circle;
- ellipse;
- smooth superellipse;
- rounded rectangle;
- periodic spline cross section.

The implicit surface can be written schematically as

\[
F_{\mathrm{coil}}(\mathbf{x})=g(u(\mathbf{x}),v(\mathbf{x});s_*(\mathbf{x})).
\]

### Critical difficulty

The closest or ownership coordinate \(s_*\) must be found robustly and efficiently. A naive global minimization along every coil for every surface query would be too slow.

The implementation should therefore use:

1. precomputed centerline spline segments;
2. conservative segment bounding boxes;
3. a small BVH or interval index over segments;
4. a local Newton solve initialized from the candidate segment;
5. deterministic tie handling near high-curvature or equidistant regions.

For ray intersection, the preferred robust formulation is a parametric surface solve:

\[
\mathbf{S}(s,\alpha)
=
\mathbf{x}_0+t\Omega,
\]

solving for \((s,\alpha,t)\) on a candidate surface patch, with safeguarded subdivision when Newton fails.

A simpler circular or elliptical coil should be implemented first. Rounded rectangles and nested case/winding-pack surfaces come later.

## 4.6 Nested reactor layers

For ordered surfaces

\[
S_0,S_1,\ldots,S_n,
\]

the material layer \(i\) is

\[
\mathcal{V}_i=(+S_i)\cap(-S_{i+1})
\]

under the chosen sign convention.

The compiler must check:

- strict nesting;
- positive minimum clearance;
- no surface crossing;
- consistent field-period seams;
- no gaps between intended adjacent layers;
- volume monotonicity.

A layer thickness may be defined by:

- a constant;
- a periodic spline field \(t(\theta,\varphi)\);
- a table on a periodic grid;
- a function of available distance to coils;
- a user-provided target surface.

Normal-offset construction is only one option. The code should allow direct target surfaces because normal offsets can self-intersect in concave regions.

## 4.7 Field-period transforms

Initial geometry tests should use full \(360^\circ\) models so a new periodic-boundary implementation is not confused with the surface work.

Later, the geometry compiler may instantiate repeated periods by transforms. It must preserve:

- points;
- directions;
- normals;
- surface senses;
- coil identities;
- local tally coordinates;
- source-rate normalization.

Rotational periodic boundary conditions are a separate qualification task. OpenMC 0.16 generalized rotational periodic boundaries, but the exact suitability for the required stellarator transformation must be verified rather than assumed.

---

# 5. Ray-intersection algorithm and robustness plan

## 5.1 Baseline algorithm before optimization

The first standalone kernel should prioritize correctness:

1. Intersect the ray with a conservative surface bounding box or bounding torus.
2. Establish a finite interval \([t_a,t_b]\) containing all possible intersections.
3. Subdivide the interval using bounds on \(F\) or conservative patch bounds.
4. Identify sign-changing intervals and possible tangent intervals.
5. Apply Brent/bisection to sign-changing intervals.
6. Apply interval Newton or derivative-based minimization for tangent roots.
7. Return the smallest positive validated root.
8. Confirm the residual, side change, and local normal.

This method may be slower than the final design but provides an independent oracle.

## 5.2 Optimized algorithm

After correctness is established:

1. Use toroidal and poloidal patch bounding boxes.
2. Predict the next parameter patch crossed by the ray.
3. Use the previous surface coordinate as an initial guess after nearby events.
4. Use Newton or Halley iterations with
   \[
   G(t)=F(\mathbf{x}_0+t\Omega),
   \qquad
   G'(t)=\nabla F\cdot\Omega.
   \]
5. Fall back to the robust oracle when:
   - the Newton step leaves the bracket;
   - \(|G'|\) is too small;
   - the iteration does not contract;
   - multiple candidate roots are plausible;
   - the ray is nearly tangent.

The production code should count fallback frequency. Performance claims are not credible without reporting how often difficult paths occur.

## 5.3 Coincident and grazing cases

The implementation must explicitly define:

- the surface-coincidence tolerance;
- how the `coincident` hint from OpenMC is used;
- how a particle is advanced after crossing to prevent immediate recrossing;
- how sign is selected when \(|F|\) is near zero;
- how tangent roots are distinguished from numerical noise;
- how extremely shallow crossings are handled.

OpenMC 0.16 added settings related to surface-grazing behavior. The integration task should inspect those semantics and avoid creating a conflicting private convention.

## 5.4 Required diagnostic counters

Every debug build should record:

- number of `evaluate` calls;
- number of distance calls;
- average and maximum candidate patches;
- Newton iteration histogram;
- fallback count;
- tangent/grazing count;
- rejected roots;
- residual distribution;
- missed-root oracle disagreements;
- time per surface type.

These counters are necessary to determine whether a speed problem comes from representation, patch lookup, or the root solver.

---

# 6. Geometry compiler and input generality

## 6.1 Common input protocol

A plasma/blanket surface adapter should return:

```python
class ParametricClosedSurface(Protocol):
    n_field_periods: int
    units: str

    def position(self, theta, phi) -> array[..., 3]: ...
    def normal(self, theta, phi) -> array[..., 3] | None: ...
    def metadata(self) -> dict: ...
```

A coil adapter should return:

```python
class PeriodicCurve(Protocol):
    units: str

    def position(self, s) -> array[..., 3]: ...
    def tangent(self, s) -> array[..., 3] | None: ...
    def metadata(self) -> dict: ...
```

The compiler must not depend directly on VMEC after the adapter has produced this protocol.

## 6.2 Fitting sequence for plasma and blanket surfaces

1. Read and normalize the source geometry.
2. Determine field periodicity from input evidence.
3. Establish a reference axis.
4. Sample the target surface at an over-resolved grid.
5. Test single-chart star-shapedness.
6. Fit periodic spline coefficients with regularization.
7. Evaluate fit on a denser independent validation grid.
8. Calculate:
   - pointwise normal error;
   - radial error;
   - approximate Hausdorff error;
   - area and volume error;
   - curvature extrema;
   - seam closure.
9. Increase knots/order until tolerance is met or a resource limit is reached.
10. Reject unsupported topology or switch to a fallback.

Training and validation sample grids must be different. Otherwise the fit can appear exact while being wrong between sample points.

## 6.3 Fitting sequence for coils

1. Read each closed centerline.
2. repair only duplicate endpoint and parameter-order issues that are explicitly allowed;
3. fit a periodic centerline spline;
4. calculate arc length and reparameterize near-uniformly;
5. construct a rotation-minimizing frame;
6. check frame closure and distribute any residual twist according to a documented policy;
7. generate finite surfaces from the requested cross section;
8. detect self-intersection and coil-coil overlap;
9. build candidate-patch bounds and the tally-mesh mapping;
10. assign stable `coil_id`, `arc_bin`, and cross-section coordinates.

## 6.4 Device-specific data file

`compiled_geometry.h5` should contain at least:

```text
/schema_version
/units
/source_hashes
/global/n_field_periods
/global/tolerance

/surfaces/<surface_id>/type
/surfaces/<surface_id>/name
/surfaces/<surface_id>/orientation
/surfaces/<surface_id>/axis_knots
/surfaces/<surface_id>/axis_coefficients
/surfaces/<surface_id>/theta_knots
/surfaces/<surface_id>/phi_knots
/surfaces/<surface_id>/radius_coefficients
/surfaces/<surface_id>/patch_bounding_boxes
/surfaces/<surface_id>/fit_metrics

/coils/<coil_id>/centerline_knots
/coils/<coil_id>/centerline_coefficients
/coils/<coil_id>/frame_data
/coils/<coil_id>/cross_section
/coils/<coil_id>/patch_bounding_boxes
/coils/<coil_id>/fit_metrics

/cells/<cell_id>/region_expression
/cells/<cell_id>/material_key

/meshes/...
```

The HDF5 file should be immutable for a run and referenced by content hash from the OpenMC input manifest.

## 6.5 No per-device recompilation

The generic C++ primitive reads coefficients from the HDF5 file. A new plasma or magnet changes only the data.

The project should reject any design that generates device-specific C++ source and recompiles OpenMC for each model. Such a workflow would not be usable as a general research tool.

---

# 7. Companion tally-mesh design

## 7.1 Transport geometry and tally mesh are independent

The transport model remains native CSG. The mesh is used for scoring and postprocessing.

This allows:

- smooth CSG tracking;
- local spectra on a regular indexing system;
- visualization in ParaView;
- data transfer to deterministic solvers;
- mesh refinement without changing the physical transport surfaces.

## 7.2 Plasma/blanket mesh

Use the same parameter coordinates as the CSG surfaces:

\[
(\lambda,\theta,\varphi)\mapsto\mathbf{x},
\]

where \(\lambda\) interpolates between adjacent layer boundaries.

A logical mesh element is indexed by

```text
layer_id
radial_bin
poloidal_bin
toroidal_bin
```

Map each logical hexahedron to Cartesian vertices and either:

- export hexahedra where supported;
- split into a deterministic 5- or 6-tetrahedron pattern;
- alternate split orientation in a controlled way to avoid systematic bias.

Required checks:

- positive Jacobian at quadrature points;
- positive cell volume;
- no inverted elements;
- exact periodic index closure;
- total mesh volume convergence toward CSG volume;
- stable global element IDs.

## 7.3 Magnet mesh

Use coil-aligned coordinates:

\[
(s,u,v)\mapsto
\mathbf{c}(s)+u\mathbf{N}(s)+v\mathbf{B}(s).
\]

A magnet element is indexed by

```text
coil_id
arc_bin
u_bin
v_bin
region_id   # case, winding pack, coolant, etc.
```

This mesh is the main output for local magnet spectra.

Each element should also store:

- centroid;
- volume;
- local frame;
- mean magnetic-field direction if supplied;
- nearest plasma/blanket coordinates;
- surface distance and shielding thickness descriptors;
- parent CSG cell ID.

## 7.4 File formats

Generate all three during development:

1. **ExodusII `.e`** for OpenMC `UnstructuredMesh(..., "libmesh")` and broad finite-element interoperability.
2. **MOAB H5M `.h5m`** for OpenMC `UnstructuredMesh(..., "moab")`, especially when tracklength tally support is required.
3. **VTU or VTKHDF** for visualization and inspection.

At the audited OpenMC snapshot, the unstructured-mesh regression tests exercise both libMesh and MOAB. The tests explicitly skip libMesh tracklength tallies, while MOAB is tested with collision and tracklength estimators. Reference: [OpenMC unstructured-mesh regression test](https://github.com/openmc-dev/openmc/blob/7ecd3a9613f06ed0dc22368c9540faf4aaacc65f/tests/regression_tests/unstructured_mesh/test.py).

Therefore:

- use Exodus/libMesh collision tallies for the easiest first proof;
- qualify MOAB/H5M for production tracklength flux tallies;
- do not confuse MOAB tally-mesh use with DAGMC transport.

## 7.5 Material and cell intersection

A tally mesh may not align perfectly with the smooth CSG surface between vertices. Protect layer-resolved responses by combining filters:

```python
mesh_filter = openmc.MeshFilter(coil_mesh)
cell_filter = openmc.CellFilter([winding_pack_cell])
energy_filter = openmc.EnergyFilter(energy_edges)
```

This scores the intersection of the mesh element and the selected CSG cell.

Also use OpenMC mesh material-volume utilities to estimate and document the physical material fraction of each mesh element where needed.

## 7.6 Local boundary data

Volume spectra are not sufficient for deterministic boundary coupling. The project should provide a second local product for particles crossing into a magnet envelope.

Two possible implementations must be evaluated:

### Path A: existing OpenMC filters and surface-source bank

Use current surface, energy, particle, and angular filters together with a surface source bank. OpenMC 0.16 includes surface-flux tally support, `MuSurfaceFilter`, `MeshSurfaceFilter`, and generalized angular capabilities. The exact spatial patching capability for the proposed curved custom surface must be verified in a bounded test.

### Path B: new parametric surface-coordinate filter

At a custom-surface crossing, the CSG primitive already calculates local coordinates:

- plasma/blanket: \((\theta,\varphi)\);
- magnet: \((s,\alpha)\) or \((s,u,v)\).

Expose these coordinates to a new tally filter:

```text
ParametricSurfaceFilter(surface_id, bins_theta, bins_phi)
CoilSurfaceFilter(coil_id, bins_s, bins_perimeter)
```

This avoids creating thousands of artificial CSG patch surfaces merely for tallies.

Path B is likely the clean long-term method, but it should not be implemented until volume-mesh tallies and the custom surface are already correct.

---

# 8. OpenMC integration work

## 8.1 Files likely requiring modification

The implementation agent must verify the live repository, but likely files include:

```text
include/openmc/surface.h
src/surface.cpp
openmc/surface.py
openmc/__init__.py
openmc/geometry.py or XML export paths
tests/unit_tests/test_surface.py
tests/regression_tests/<new cases>/
docs/source/pythonapi/generated/...
docs/source/usersguide/geometry.rst
```

Do not assume this list is exhaustive.

## 8.2 Proposed C++ classes

```cpp
class SurfacePeriodicSpline : public Surface {
public:
  double evaluate(Position r) const override;
  double distance(Position r, Direction u, bool coincident) const override;
  Direction normal(Position r) const override;
  BoundingBox bounding_box(bool pos_side) const override;
  void to_hdf5_inner(hid_t group_id) const override;
};

class SurfaceSweptSpline : public Surface {
public:
  double evaluate(Position r) const override;
  double distance(Position r, Direction u, bool coincident) const override;
  Direction normal(Position r) const override;
  BoundingBox bounding_box(bool pos_side) const override;
  void to_hdf5_inner(hid_t group_id) const override;
};
```

The classes should delegate the numerical kernel to the standalone library where possible.

## 8.3 Proposed Python classes

```python
openmc.PeriodicSplineSurface(
    data_file="compiled_geometry.h5",
    dataset="/surfaces/first_wall",
    boundary_type="transmission",
)

openmc.SweptSplineSurface(
    data_file="compiled_geometry.h5",
    dataset="/coils/coil_003/outer_case",
)
```

The Python objects should behave like other OpenMC surfaces:

```python
cell.region = +inner_surface & -outer_surface
```

## 8.4 Input storage

Do not put thousands of coefficients directly in `geometry.xml` by default.

Use XML references to a hash-bound HDF5 dataset. Small analytic test cases may allow inline coefficients for readability.

## 8.5 Transform support

The first implementation may instantiate coefficients directly in global coordinates. Later versions should support translation and rotation consistent with OpenMC surface transforms.

Any transform must update:

- point evaluation;
- direction handling;
- normals;
- bounding boxes;
- local tally coordinates;
- HDF5 metadata.

## 8.6 Plotting and geometry debug

Before transport, require:

- OpenMC slice plots through many toroidal planes;
- solid ray-trace plots if supported;
- geometry-debug runs;
- random point classification against an independent reference;
- overlap checks between all nested cells and coils.

A model that merely completes transport without lost particles is not automatically correct.

---

# 9. Mathematical test ladder

## Test M0: one-dimensional root solver

Test the safeguarded root finder on functions with:

- one simple root;
- multiple roots;
- double/tangent roots;
- roots near interval boundaries;
- nearly flat derivatives;
- no root;
- roots separated below the initial scan spacing.

No OpenMC dependency.

## Test M1: circle and sphere surrogate

Represent a circle/sphere through the spline machinery and compare:

- `evaluate`;
- normal;
- ray distance;
- inside/outside classification;
- nearest root.

The expected answer is analytical.

## Test M2: built-in torus equivalence

Fit an axisymmetric torus with the periodic spline primitive and compare against OpenMC's exact torus equation.

Sample at least:

- random points inside/outside;
- isotropic rays;
- radial rays;
- grazing rays;
- rays beginning on the surface;
- rays producing two or four torus intersections.

This is the most important initial mathematical oracle because it resembles a stellarator but retains an exact reference.

## Test M3: analytic helical perturbation

Define a smooth synthetic surface such as

\[
\rho_s(\theta,\varphi)
=
r_0\left[1
+\epsilon_1\cos(m\theta-nN_{\mathrm{FP}}\varphi)
+\epsilon_2\sin(m'\theta-n'N_{\mathrm{FP}}\varphi)
\right].
\]

This surface has a known direct evaluation and can test non-axisymmetric periodic behavior.

## Test M4: nested shells

Generate 3–5 nested periodic surfaces with known positive separation. Test:

- strict ordering;
- cell lookup;
- ray sequence through layers;
- volume convergence;
- no skipped layers.

## Test M5: circular swept coil

Use a planar circular centerline with circular cross section. Compare against an exact torus or known swept geometry.

## Test M6: non-planar swept coil

Use an analytic helical or sinusoidally perturbed closed centerline. Compare the optimized solver against a high-accuracy subdivision oracle.

## Test M7: randomized property tests

For each surface:

1. sample a random valid point and direction;
2. obtain the optimized distance;
3. independently search all roots with the oracle;
4. confirm the optimized result is the nearest positive root;
5. advance slightly before and after the root and confirm the expected sense change when the crossing is not tangent.

Use deterministic seeds and retain every failure case as a permanent regression fixture.

## Test M8: adversarial cases

Include:

- tangent rays;
- rays nearly parallel to local surface;
- points within the coincidence tolerance;
- high-curvature regions;
- parameter seams;
- axis-angle branch cuts;
- very short path lengths between nested layers;
- close coil-coil approaches;
- repeated reflections if boundaries are enabled.

---

# 10. Geometry-quality acceptance metrics

For every compiled surface, report:

## 10.1 Fit accuracy

- maximum pointwise distance on validation samples;
- RMS distance;
- approximate Hausdorff distance;
- maximum normal-angle error;
- area difference;
- enclosed-volume difference.

## 10.2 Topology and nesting

- star-shapedness margin;
- minimum Jacobian;
- minimum layer separation;
- number of detected self-intersections;
- coil self-intersection status;
- coil-coil minimum clearance;
- field-period seam mismatch.

## 10.3 Ray accuracy

- maximum distance error against oracle;
- percentile distance errors;
- missed-root count;
- false-root count;
- wrong-nearest-root count;
- tangent classification count;
- fallback rate.

## 10.4 Initial numerical targets

These are feasibility targets and may be refined after scale analysis:

- exact analytic tests: distance error \(<10^{-9}\) times the characteristic length where conditioning permits;
- fitted device surfaces: user-selected geometric tolerance, initially 0.01–0.1 cm;
- zero wrong-root events in at least \(10^7\) randomized/adversarial rays before OpenMC integration;
- volume agreement with the reference geometry better than 0.05% for the benchmark model;
- seam closure below one tenth of the requested surface-fit tolerance.

---

# 11. OpenMC neutronics benchmark ladder

## Benchmark N0: homogeneous sphere/cylinder smoke test

Purpose: verify parser, surface object, HDF5 loading, and cell half-space behavior.

Use a custom spline representation of a geometry that OpenMC can solve with built-in surfaces.

Compare:

- volume;
- leakage;
- collision count;
- flux;
- heating;
- histories per second.

## Benchmark N1: exact torus — built-in CSG vs custom CSG

Construct the same toroidal shell with:

1. built-in OpenMC torus surfaces;
2. custom periodic spline surfaces.

Use identical:

- materials;
- source distribution;
- seeds;
- settings;
- tallies.

This isolates the custom geometry implementation from CAD/faceting differences.

Required outputs:

- pointwise geometry comparison;
- leakage and balance;
- flux in nested toroidal regions;
- energy-resolved spectra;
- runtime and memory;
- distance-call statistics.

## Benchmark N2: exact torus — built-in CSG vs custom CSG vs DAGMC

Generate a high-quality faceted torus and run the same model through DAGMC/Embree.

This determines whether the custom root solver can actually beat modern faceted ray tracing.

## Benchmark N3: synthetic helical stellarator

Use a known analytic periodic surface with several nested layers. Compare:

- custom CSG;
- a high-resolution DAGMC representation generated from the same function.

Perform geometry refinement on the DAGMC side and spline-knot refinement on the CSG side.

## Benchmark N4: swept magnet only

Place one or several finite swept coils around a source. Compare custom CSG against a high-resolution DAGMC or independent mesh reference.

## Benchmark N5: generic VMEC surface

Use a public or project-authorized VMEC surface, compile it without CAD, and generate:

- plasma/source region;
- first wall;
- two simple blanket layers;
- outer vacuum boundary.

No magnets yet.

## Benchmark N6: VMEC plus finite magnets

Add coil centerlines and simple finite cross sections. Generate one smooth CSG primitive per magnet envelope and casing.

## Benchmark N7: WISTELL-D or HELIAS reference

Only after N0–N6 pass, apply the pipeline to the authoritative project geometry.

Compare against a hash-bound DAGMC model generated from the same source data.

Primary responses:

- energy-resolved neutron spectra at selected magnet locations;
- photon spectra;
- magnet heating;
- flux above selected thresholds;
- local hotspot identity;
- leakage and source normalization;
- geometry and transport throughput.

TBR may be calculated as a secondary geometry/physics check but is not the primary objective.

---

# 12. Statistical comparison contract

## 12.1 Separate error sources

Report separately:

- Monte Carlo sampling uncertainty;
- CSG fit error;
- DAGMC faceting error;
- source discretization error;
- tally-mesh discretization error;
- nuclear-data uncertainty, if evaluated;
- geometry tolerance/root-solver numerical error.

Do not fold these into one unexplained number.

## 12.2 Matched-run strategy

For code-path comparisons:

- use common source definitions;
- use identical batch/particle counts;
- use matched seeds where supported;
- also run independent seeds to avoid mistaking common-random-number cancellation for unbiased agreement;
- compare batchwise responses, not only final means.

## 12.3 Acceptance tests

For integral responses with good statistics:

\[
z=
\frac{R_{\mathrm{custom}}-R_{\mathrm{reference}}}
{\sqrt{\sigma_{\mathrm{custom}}^2+\sigma_{\mathrm{reference}}^2}}
\]

should generally remain within preregistered statistical bounds, while the absolute or relative difference remains below a physics-relevant tolerance.

For spectral bins:

- compare only bins meeting an uncertainty threshold;
- combine neighboring bins when necessary for a stable diagnostic;
- compare integrated bands and spectral moments;
- preserve the raw fine-bin data.

## 12.4 Performance measurement

Record separately:

- geometry compilation time;
- OpenMC initialization time;
- first-batch time;
- active histories per second;
- total wall time;
- peak resident memory;
- scaling with threads and MPI ranks;
- geometry-kernel time fraction;
- root-solver fallback rate.

A speed claim must use the same physical geometry tolerance and transport settings.

---

# 13. Go/no-go matrix

| Gate | Required evidence | Continue criterion |
|---|---|---|
| G0: Repository/build | Pinned OpenMC, DAGMC/Embree, MOAB, libMesh builds | Reproducible clean build and test manifest |
| G1: Root mathematics | Analytic and adversarial ray suite | Zero wrong nearest roots in preregistered suite |
| G2: OpenMC custom surface | Built-in shape reproduced by custom primitive | Correct cell lookup, no lost particles, tally agreement |
| G3: Performance | Custom torus vs DAGMC/Embree | Plausible speed or memory advantage |
| G4: Non-axisymmetric surface | Synthetic helical geometry | Correctness and refinement convergence |
| G5: Generic input | VMEC/sampled surface compiled without CAD | One-command reproducible model generation |
| G6: Tally mesh | Coil/blanket local mesh with stable IDs | Volume and tally closure; ParaView inspection passes |
| G7: Magnet primitive | Non-planar swept coil | Robust nearest intersections and no overlaps |
| G8: Device model | WISTELL-D/HELIAS CSG vs DAGMC | Spectra and hotspot agreement within preregistered limits |
| G9: End-to-end speed | Full representative case | Target 1.3–1.5× transport speedup or strong memory/startup benefit |

### Stop or redirect conditions

Stop the native CSG route or narrow its scope if:

- nearest-root correctness cannot be guaranteed for important geometries;
- common target surfaces repeatedly fail the single-chart and practical multi-chart representations;
- custom CSG is slower than DAGMC/Embree at matched accuracy after bounded optimization;
- coil intersection cost dominates and cannot be reduced;
- the OpenMC modifications become too invasive to maintain;
- tally localization cannot be made stable across geometry refinements.

A negative result would still be publishable if it rigorously establishes the boundary where implicit CSG ceases to outperform faceted transport.

---

# 14. Proposed work packages and schedule

## WP0 — Freeze and audit the development environment

**Duration:** 2–3 days  
**Outputs:** pinned repositories, build manifests, baseline tests, reference performance.

## WP1 — Mathematical contract and robust scalar root solver

**Duration:** 1 week  
**Outputs:** specification, root oracle, analytic tests, tolerance policy.

## WP2 — Periodic spline surface kernel

**Duration:** 1–2 weeks  
**Outputs:** evaluate/gradient/distance/bounds, torus and helical tests.

## WP3 — Geometry compiler and generic surface adapters

**Duration:** 1–2 weeks  
**Outputs:** VMEC/sampled-surface adapters, fitting, admissibility tests, HDF5 schema.

## WP4 — Tally-mesh generator

**Duration:** 1–2 weeks, parallel with WP3  
**Outputs:** blanket and coil meshes, Exodus/H5M/VTU exports, stable mapping.

## WP5 — OpenMC periodic-spline integration

**Duration:** 1–2 weeks  
**Outputs:** C++ and Python surface classes, XML/HDF5 loading, tests and documentation.

## WP6 — Neutronic torus and synthetic-helical benchmark

**Duration:** 1 week  
**Outputs:** built-in/custom/DAGMC comparison and performance decision.

## WP7 — Swept magnet surface

**Duration:** 2–4 weeks  
**Outputs:** circular/elliptical first, then rounded-rectangle surface and local mesh.

## WP8 — Full generic API and user examples

**Duration:** 1 week  
**Outputs:** OpenMC-style Python examples, command-line interface, schema docs.

## WP9 — WISTELL-D/HELIAS demonstration

**Duration:** 2–4 weeks  
**Outputs:** matched native-CSG and DAGMC models, magnet spectra, performance and paper-quality evidence.

## WP10 — Independent review and release decision

**Duration:** 1 week  
**Outputs:** hostile review, reproducibility package, upstream/fork decision.

---

# 15. Parallel execution map

After WP0 is frozen, these lanes can run in parallel:

```text
Lane A: Math/root oracle
    A1 mathematical contract
    A2 periodic spline kernel
    A3 adversarial ray tests

Lane B: Input/compiler
    B1 common surface protocol
    B2 VMEC adapter
    B3 spline fitting and admissibility

Lane C: Mesh/tallies
    C1 parametric blanket mesh
    C2 coil-aligned mesh
    C3 OpenMC unstructured tally validation

Lane D: OpenMC integration
    D1 surface parser and Python class
    D2 C++ wrapper
    D3 regression tests

Lane E: References/benchmarks
    E1 exact torus models
    E2 DAGMC reference generation
    E3 common tallies and performance harness

Lane F: Magnet primitive
    F1 centerline/frame math
    F2 circular swept tube
    F3 finite winding pack and mesh
```

Dependencies:

- D2 depends on a stable A2 interface.
- B2 and C1 may proceed against a pure-Python reference before A2 is complete.
- E1 and E2 can proceed immediately after WP0.
- F2 depends on F1 but not on the plasma surface kernel.
- The full device benchmark depends on A–F passing their bounded gates.

---

# 16. Executable Codex prompts

The following prompts are designed to be run in separate Codex sessions. Replace local paths only where necessary. Each session must preserve a manifest of repository commit hashes, commands, tests, and generated artifact hashes.

## Prompt 00 — Freeze repositories, builds, and baseline evidence

```text
Act as the build and reproducibility owner for a new native-stellarator-CSG project.

Goal:
Create a frozen, reproducible development baseline for extending OpenMC with generic smooth CSG surfaces while retaining DAGMC/Embree and unstructured tally meshes as comparison paths.

Required repositories:
- openmc-dev/openmc at an explicitly recorded commit; inspect the current main/develop branch before choosing
- svalinn/parastell at an explicitly recorded commit
- IPP-SRS/jax-sbgeom at an explicitly recorded commit
- any required DAGMC, MOAB, Embree, libMesh, HDF5, Gmsh, meshio, and test dependencies

Do not implement the new geometry yet.

Tasks:
1. Audit the live repositories and document licenses, build requirements, current branches, current tests, and the exact OpenMC files involved in Surface subclasses, XML/HDF5 surface input, geometry distance calculations, unstructured mesh tallies, and geometry debug.
2. Build a pinned OpenMC development environment with:
   - native CSG
   - DAGMC/Embree if available
   - MOAB unstructured mesh support
   - libMesh unstructured mesh support
   - Python API
3. Run relevant existing unit/regression tests, including:
   - surface tests
   - torus tests
   - DAGMC tests
   - unstructured mesh collision and tracklength tests
   - MeshSurfaceFilter/MuSurfaceFilter/surface-flux tests where present
4. Record which unstructured tally estimators are supported by each backend in this exact build.
5. Create a minimal built-in OpenMC torus fixed-source benchmark and record initialization time, histories/s, memory, and tally outputs.
6. Create or identify a matching DAGMC torus reference and record the same metrics.
7. Produce a machine-readable manifest with all commit hashes, compilers, CMake options, package versions, commands, test results, and artifact hashes.

Required outputs:
- BASELINE_AUDIT.md
- environment lock files or container definition
- build_manifest.json
- test_results.json
- baseline_torus_native/
- baseline_torus_dagmc/
- no changes to OpenMC production source

Acceptance:
The baseline is complete only if a fresh environment can reproduce the two reference runs and the relevant tests. Clearly mark unavailable optional dependencies rather than silently skipping them.
```

## Prompt 01 — Write the mathematical contract before coding

```text
Act as an independent applied-mathematics reviewer. Develop the formal contract for a generic native CSG surface suitable for OpenMC stellarator transport.

Scope:
- periodic bicubic radial spline for plasma/blanket surfaces
- future multi-chart extension
- swept spline tube for finite magnets
- nearest positive ray intersection
- inside/outside sense
- normal calculation
- coincidence and grazing behavior
- conservative bounding boxes

Required work:
1. Define the coordinate map, orientation, periodicity, differentiability requirements, and admissibility conditions.
2. Derive F(x), gradient F, and dF/dt along a ray for the periodic radial-spline surface.
3. Define a robust nearest-root algorithm and a slower independent oracle.
4. Address multiple intersections, tangent roots, branch cuts in atan2, toroidal seams, and points on the axis.
5. Define star-shapedness tests and conditions requiring rejection or multi-chart handling.
6. Define the swept-coil closest-coordinate problem and at least two viable intersection formulations.
7. Specify numerical tolerances in dimensionless form tied to characteristic length and machine precision.
8. Define invariants and property-based tests.
9. Identify cases in which the proposed implicit function is not a signed-distance function and explain the implications.
10. Return explicit go/no-go conditions for implementing each primitive.

Do not write production code. Do not assume every VMEC surface is single-chart admissible.

Outputs:
- MATHEMATICAL_CONTRACT.md
- equations in implementable notation
- test-case catalogue
- pseudocode for robust and optimized intersection algorithms
- risk register
```

## Prompt 02A — Implement the standalone periodic-spline kernel

```text
Implement a standalone C++ geometry kernel for a periodic bicubic radial-spline CSG surface, with Python bindings only if useful for tests.

Inputs:
- the frozen mathematical contract
- periodic axis spline data
- periodic theta/phi knot vectors
- radius/control coefficients
- field-period count
- tolerance policy

Required API:
- evaluate(point)
- gradient(point)
- normal(point)
- local_coordinates(point)
- distance_robust(point, direction, coincident)
- distance_fast(point, direction, coincident)
- bounding_box()
- diagnostics()

Implementation requirements:
1. No Python callback in the ray-intersection loop.
2. Compact-support spline evaluation.
3. Deterministic results across thread counts.
4. A robust independent root oracle.
5. Fast path with safeguarded fallback.
6. Diagnostic counters for iterations, patches, fallbacks, and residuals.
7. Serialization round trip to a versioned HDF5 test format.

Tests:
- circle/sphere surrogate
- exact axisymmetric torus
- analytic helical perturbation
- nested shells
- 10^7 deterministic randomized/adversarial rays if runtime permits
- all failures retained as fixtures

Benchmarks:
- evaluate calls/s
- distance calls/s
- iteration distribution
- fast/oracle agreement
- comparison with triangle BVH intersection for a matched torus if available

Outputs:
- source and tests
- PERIODIC_SPLINE_KERNEL_REPORT.md
- benchmark JSON/CSV
- no OpenMC modification yet
```

## Prompt 02B — Implement the standalone swept-coil kernel

```text
Implement and test a standalone smooth swept-spline CSG primitive for finite-build stellarator magnets.

Start with:
- periodic centerline spline
- rotation-minimizing frame
- circular and elliptical cross sections

Later, only after passing:
- smooth superellipse
- rounded rectangle
- nested case and winding-pack surfaces

Required API:
- evaluate(point)
- normal(point)
- local_coordinates(point) -> coil arc coordinate and cross-section coordinates
- distance_robust(point, direction, coincident)
- distance_fast(...)
- bounding_box()
- centerline/frame diagnostics

Required tests:
1. Planar circular centerline + circular section, compared with an exact torus.
2. Planar ellipse or nonuniform radius case.
3. Non-planar analytic closed centerline.
4. Frame closure and residual-twist handling.
5. High-curvature and close-approach cases.
6. Random and grazing rays.
7. Self-intersection rejection.
8. Two-coil minimum-clearance and overlap tests.

Do not hide failures by increasing tolerances. Return a clear statement of the geometry envelope the implementation can support.

Outputs:
- swept-coil kernel and tests
- SWEPT_COIL_KERNEL_REPORT.md
- performance and robustness evidence
```

## Prompt 03 — Build the generic geometry compiler and input adapters

```text
Build a Python geometry compiler that converts supported plasma and coil inputs into the generic coefficient-based StellarCSG HDF5 schema.

Required input adapters:
1. VMEC plasma boundary.
2. Sampled periodic surface array.
3. Generic Python ParametricClosedSurface protocol.
4. Coil filament point file.
5. Generic Python PeriodicCurve protocol.

Required compiler behavior:
- explicit units
- field-period detection from live input
- reference-axis construction
- independent fitting and validation grids
- periodic spline fitting
- star-shapedness/admissibility tests
- fit refinement until tolerance or resource cap
- no silent repair of topology
- strict layer nesting and clearance tests
- stable surface, cell, and coil IDs
- content-hashed HDF5 output

Generate proposed OpenMC Python objects but do not require the OpenMC fork to exist yet; use a neutral intermediate model.

Required examples:
- exact torus
- analytic helical surface
- one public/project-authorized VMEC case
- one coil set

Outputs:
- compiler package
- schema documentation
- GEOMETRY_COMPILER_REPORT.md
- example compiled_geometry.h5 files
- fit-error and admissibility reports
```

## Prompt 04 — Build the layer- and coil-aligned tally mesh generator

```text
Develop a companion mesh generator from the same parameterization used by the native CSG geometry.

Purpose:
The mesh is for OpenMC tallies, ParaView, local magnet data, and deterministic coupling. It must not become the transport geometry.

Required mesh families:
1. Plasma/blanket mesh in (layer, radial, theta, phi) coordinates.
2. Coil mesh in (coil_id, arc, u, v, region) coordinates.
3. Optional surface-patch mesh for visualization and boundary mapping.

Required formats:
- ExodusII for libMesh
- MOAB H5M
- VTU or VTKHDF
- mapping HDF5/JSON

Required element metadata:
- stable global ID
- parent layer or coil
- parent CSG cell ID
- local coordinates
- centroid and volume
- local normal/frame where relevant
- material key

Tests:
- positive Jacobians
- no inverted elements
- periodic closure
- volume convergence to the CSG geometry
- stable IDs under repeated generation
- ParaView readability
- OpenMC collision tally on Exodus/libMesh
- OpenMC collision and tracklength tally on MOAB if available
- combined MeshFilter + CellFilter correctness

Use exact repository evidence for which estimators are supported in the frozen OpenMC build.

Outputs:
- mesh generator
- TALLY_MESH_CONTRACT.md
- mesh QA reports
- OpenMC mesh-tally smoke models
```

## Prompt 05 — Add the periodic-spline surface to OpenMC

```text
Integrate the validated periodic-spline geometry kernel into the frozen OpenMC fork as a new native CSG surface.

Required work:
1. Audit the live OpenMC surface architecture before editing.
2. Add a C++ Surface subclass wrapping the standalone kernel.
3. Add parser/serialization support for an external hash-bound HDF5 dataset.
4. Add the Python Surface class and region/half-space behavior.
5. Add HDF5 summary output.
6. Add bounding-box support.
7. Ensure geometry type remains CSG, not DAGMC.
8. Add unit and regression tests.
9. Add debug diagnostics behind a non-production option.
10. Document transforms and explicitly reject unsupported transforms rather than applying them incorrectly.

Required regression cases:
- custom sphere/cylinder surrogate
- exact torus comparison
- nested shells
- reflective/vacuum boundaries where valid
- coincident and grazing rays
- plots and geometry debug

Do not integrate the swept-coil primitive in this prompt.

Outputs:
- reviewable OpenMC branch
- OPENMC_PERIODIC_SPLINE_INTEGRATION.md
- test evidence
- no performance claims until Prompt 07
```

## Prompt 06 — Prepare matched native-CSG and DAGMC reference models

```text
Act as the independent reference-model owner.

Prepare matched OpenMC models for:
1. exact torus using built-in OpenMC CSG
2. the same torus using a high-resolution DAGMC/Embree surface
3. analytic helical stellarator using DAGMC
4. nested helical layers using DAGMC

Requirements:
- generated from shared mathematical source data
- explicit geometry tolerances
- volume and area checks
- identical materials, source, settings, tallies, and normalization
- independent geometry artifact hashes
- fine and coarse DAGMC faceting levels
- no use of the new custom CSG code in reference generation

Tallies:
- leakage
- region flux
- energy spectrum
- heating
- selected surface current
- unstructured tally-mesh flux where available

Outputs:
- reference models
- REFERENCE_GEOMETRY_REPORT.md
- geometry and tally manifests
```

## Prompt 07 — Run the decisive torus and synthetic-stellarator benchmark

```text
Run an independent correctness and performance comparison between:
- built-in OpenMC CSG
- new periodic-spline native CSG
- DAGMC/Embree at multiple faceting tolerances

Cases:
1. exact torus
2. nested toroidal shells
3. analytic non-axisymmetric helical surface
4. nested helical layers

Method:
- use matched sources and physics
- use both common and independent seeds
- record batchwise results
- separate geometry error from Monte Carlo uncertainty
- measure initialization, active histories/s, wall time, memory, surface-call counts, root iterations, and fallback rate
- perform spline refinement and DAGMC faceting refinement
- include adversarial grazing-source variants

Acceptance decision:
- confirm no statistically or physically significant bias
- determine the accuracy/performance Pareto front
- recommend continue, optimize, narrow scope, or stop

Outputs:
- DECISIVE_BENCHMARK_REPORT.md
- all raw data and scripts
- a signed go/no-go recommendation
```

## Prompt 08 — Add the swept-coil surface to OpenMC

```text
Only run after the standalone swept-coil kernel passes and the periodic-spline OpenMC integration is stable.

Integrate the generic swept-spline magnet primitive into OpenMC.

Required scope:
- circular and elliptical cross sections first
- one surface per coil outer envelope
- optional nested case and winding-pack surfaces after basic qualification
- local coil coordinates exposed to Python/statepoint metadata
- stable coil identity
- bounding-box/segment acceleration
- no CAD

Tests:
- exact torus-equivalent circular coil
- non-planar closed coil
- multiple coils
- partial/full field-period instantiation
- coil local tally mesh
- source-to-coil transport
- comparison with matched DAGMC finite coils

Outputs:
- reviewable OpenMC branch
- OPENMC_SWEPT_COIL_INTEGRATION.md
- tests and benchmark evidence
```

## Prompt 09 — Build the OpenMC-style public API and examples

```text
Design and implement the user-facing StellarCSG Python API so a researcher can provide plasma and magnet geometry without CAD and obtain an OpenMC model plus local tally meshes.

Required public workflows:
- from_vmec(...)
- from_sampled_surface(...)
- from_parametric_surface(...)
- CoilSet.from_filaments(...)
- RadialBuild(...)
- compile_geometry(...)
- OpenMCBuilder(...)
- make_tally_meshes(...)
- make_magnet_spectrum_tallies(...)

Provide examples analogous in clarity to OpenMC examples:
1. analytic torus
2. synthetic stellarator
3. VMEC plasma without magnets
4. VMEC plasma with finite magnets
5. blanket/shield parameter sweep
6. coil-local spectral tally

Requirements:
- explicit units
- clear errors for unsupported topology
- deterministic IDs and hashes
- no hidden CAD dependency
- no device-specific code generation
- complete schema and API documentation

Outputs:
- package/API implementation
- examples
- USER_GUIDE.md
- API stability proposal
```

## Prompt 10 — Qualify local magnet tallies and boundary output

```text
Independently qualify the local-data products required for downstream deterministic magnet transport.

Volume path:
- coil-aligned unstructured mesh
- energy-resolved neutron and photon flux
- heating and damage-energy responses
- MeshFilter + CellFilter semantics
- element volume and normalization

Boundary path:
- incident current at the magnet envelope
- energy and local incidence angle
- local patch/arc coordinate
- particle weight and normalization
- uncertainty/effective sample size

Evaluate current OpenMC 0.16 capabilities including surface-flux tallies, SurfaceFilter, MuSurfaceFilter, MeshSurfaceFilter, and surface-source writing. Determine whether they can represent the required curved-surface spatial patches without ambiguity.

If not, design a minimal ParametricSurfaceFilter/CoilSurfaceFilter using the local coordinates already calculated by the custom surface.

Required invariants:
- integrated boundary current closure
- volume-flux vs reaction-rate consistency
- local/global coordinate round trip
- no area double counting at seams
- exact source-rate normalization

Outputs:
- LOCAL_TALLY_CONTRACT.md
- qualified example files
- implementation recommendation for any new filter
```

## Prompt 11 — Apply the method to the authoritative WISTELL-D or HELIAS model

```text
Apply the qualified generic StellarCSG pipeline to one authoritative stellarator case without adding device-specific geometry logic.

Use only hash-bound source plasma and coil files. Record lineage and field-period count from live files.

Build:
- plasma/source region
- first wall
- at least two blanket/shield configurations
- vessel
- finite magnet envelopes and winding-pack regions
- local coil tally meshes

Generate two matched transport models from the same source data:
1. native custom CSG OpenMC
2. DAGMC/Embree OpenMC reference

Primary comparison:
- neutron and photon spectra at magnet hotspots and low-flux locations
- hotspot identity
- local current distributions
- magnet heating
- selected reaction responses
- throughput, startup, and memory

Secondary:
- TBR only as a model-consistency check

Do not claim production-science conclusions if geometry or statistics remain unqualified.

Outputs:
- DEVICE_DEMONSTRATION_REPORT.md
- complete reproducibility bundle
- performance and physics comparison
- list of remaining blockers
```

## Prompt 12 — Independent hostile final review

```text
Act as an independent hostile reviewer of the native stellarator CSG project.

Review:
- mathematical admissibility
- nearest-root guarantees
- coincidence/grazing behavior
- OpenMC integration correctness
- input generality
- device-specific assumptions
- mesh/tally normalization
- DAGMC comparison fairness
- statistical tests
- performance claims
- reproducibility and licensing

Attempt to identify:
- plausible but wrong geometry
- missed roots
- incorrect surface sense
- fit-overtraining
- mismatched source normalization
- tally mesh volume errors
- common-random-number misuse
- unfair faceting tolerances
- unsupported generality claims

Return:
1. components qualified for reuse;
2. components restricted to a stated envelope;
3. blockers to publication;
4. blockers to OpenMC upstreaming;
5. exact additional tests required;
6. final recommendation: RELEASE, RESEARCH-ONLY, NARROW-SCOPE, or STOP.
```

---

# 17. Immediate 14-day starting plan

## Days 1–2

- Run Prompt 00.
- Freeze OpenMC, DAGMC/Embree, MOAB, libMesh, jax-sbgeom, and ParaStell commits.
- Build native CSG and DAGMC torus baselines.
- Verify unstructured tally-mesh support and estimators.

## Days 2–4

- Run Prompt 01.
- Independently review the mathematical contract before code.
- Decide characteristic length and tolerance conventions.

## Days 4–8

- Run Prompt 02A.
- Implement the periodic spline evaluator and robust root oracle.
- Test exact torus and helical perturbation.
- Stop if nearest-root behavior is not reliable.

## Days 6–10, in parallel

- Run Prompt 04 for the tally-mesh prototype using the analytic torus/helical mappings.
- Export Exodus, H5M, and VTU.
- Verify OpenMC mesh tallies independently of the custom CSG surface.

## Days 8–12

- Run Prompt 05 for a bounded OpenMC integration.
- Use only exact torus and nested shell tests.

## Days 10–14

- Run Prompts 06 and 07.
- Make the first hard decision based on correctness and speed.

### Day-14 decision

Continue to VMEC and magnets only if:

- the custom surface is mathematically robust;
- OpenMC integration is correct;
- the tally mesh works;
- the geometry-only and end-to-end performance indicate a credible path to beating DAGMC for smooth stellarator layers.

---

# 18. Suggested repository and branch strategy

## Primary repositories

1. `StellarCSG` — independent geometry compiler/kernel/mesh generator.
2. `openmc-stellarcsg` — pinned OpenMC fork or feature branch.
3. `stellarcsg-benchmarks` — immutable reference models and evidence.

## Suggested branches

```text
stellarcsg/main
stellarcsg/math-contract
stellarcsg/periodic-spline-kernel
stellarcsg/swept-coil-kernel
stellarcsg/input-adapters
stellarcsg/tally-mesh

openmc-stellarcsg/baseline-freeze
openmc-stellarcsg/periodic-spline-surface
openmc-stellarcsg/swept-coil-surface
openmc-stellarcsg/parametric-surface-filter

benchmarks/native-torus
benchmarks/dagmc-torus
benchmarks/synthetic-helical
benchmarks/device-demo
```

Do not merge feature branches based only on a successful smoke run. Require the evidence bundle and independent review.

---

# 19. Data and provenance rules

Every generated geometry must record:

- source file hashes;
- adapter name/version;
- units;
- field-period count;
- fit representation and order;
- knot/control data hash;
- training and validation grids;
- fit tolerances and achieved errors;
- topology/admissibility results;
- mesh resolution and export hashes;
- OpenMC commit/build flags;
- material and nuclear-data hashes;
- source normalization;
- random seeds and run settings.

Any mismatch between the CSG and DAGMC source lineage invalidates the benchmark.

---

# 20. Publication and software contribution strategy

The project can produce several distinct contributions.

## Paper A — Geometry method

**Possible title:** *Native Periodic-Spline CSG Primitives for Monte Carlo Transport in Stellarator Geometries*

Focus:

- mathematical representation;
- robust ray intersection;
- generic input compilation;
- geometry accuracy;
- speed and memory against DAGMC.

## Paper B — Magnet-local tally framework

**Possible title:** *A CAD-Free Stellarator-to-Magnet Radiation Interface Using Native CSG and Coil-Aligned Tally Meshes*

Focus:

- generic plasma and coil inputs;
- local magnet coordinates;
- boundary and volume spectra;
- downstream deterministic coupling.

## Paper C — Application

Focus:

- parametric blanket/shield changes;
- resulting spectra at multiple magnet locations;
- inputs to beyond-DPA magnet models.

Do not combine all three into the first publication. The geometry method needs a clean benchmark before the radiation-damage application expands the scope.

---

# 21. Main technical risks and mitigations

| Risk | Consequence | Mitigation |
|---|---|---|
| Surface is not single-chart star-shaped | Radial spline invalid | Explicit admissibility test; multi-chart or RBF fallback; reject unsupported cases |
| Ray has multiple/tangent roots | Wrong nearest crossing | Independent interval/subdivision oracle; safeguarded fast path; adversarial tests |
| Spline fit hides local geometry error | Biased transport | Independent validation grid, Hausdorff/normal/volume metrics, refinement study |
| Custom root solve slower than Embree | No speed benefit | Early torus benchmark before VMEC/magnet work |
| Coil closest-point solve dominates | Poor performance | Segment BVH, local Newton, simpler initial cross sections, separate benchmark |
| Tally mesh crosses smooth material surfaces | Mixed local responses | CellFilter intersection, mesh material-volume audit, refinement |
| CSG and DAGMC models use different source geometry | False physics comparison | Generate both from one hash-bound source representation |
| Python callbacks enter transport loop | Severe slowdown/thread issues | All geometry evaluation compiled in C++ |
| Large coefficient payload in XML | Slow/unwieldy input | External versioned HDF5 datasets |
| OpenMC upstream changes | Maintenance burden | Thin wrapper, pinned baseline, isolated kernel, frequent rebase tests |
| Method supports only one device | Weak generality | Neutral surface/curve protocols and multiple test devices |
| Full-device symmetry mishandled | doubled/sign-reversed source or response | Full 360° first; separate symmetry qualification |

---

# 22. Current source evidence used to shape this plan

The following live/open sources were checked while preparing this plan:

1. **OpenMC surface abstraction**, audited at commit `7ecd3a9613f06ed0dc22368c9540faf4aaacc65f`:  
   [include/openmc/surface.h](https://github.com/openmc-dev/openmc/blob/7ecd3a9613f06ed0dc22368c9540faf4aaacc65f/include/openmc/surface.h)

2. **OpenMC unstructured mesh tests**, including libMesh/MOAB and estimator behavior:  
   [tests/regression_tests/unstructured_mesh/test.py](https://github.com/openmc-dev/openmc/blob/7ecd3a9613f06ed0dc22368c9540faf4aaacc65f/tests/regression_tests/unstructured_mesh/test.py)

3. **OpenMC 0.16 development features**, including surface-flux tallies, `MeshSurfaceFilter`, generalized rotational periodic boundaries, unstructured-mesh updates, and surface-grazing controls:  
   [0.16.0 release notes](https://github.com/openmc-dev/openmc/blob/7ecd3a9613f06ed0dc22368c9540faf4aaacc65f/docs/source/releasenotes/0.16.0.rst)

4. **jax-sbgeom**, audited at commit `ecfb5be5251e0f610c708619cea6a18ae5fcfaea`, for parameterized surfaces, layered meshes, and coil volumetric meshes:  
   [IPP-SRS/jax-sbgeom](https://github.com/IPP-SRS/jax-sbgeom)

5. **ParaStell**, for VMEC/coil inputs, radial builds, source generation, and current magnet meshing architecture:  
   [svalinn/parastell](https://github.com/svalinn/parastell)

6. Moreno, Bader, and Wilson, *ParaStell: parametric modeling and neutronics support for stellarator fusion power plants*, Frontiers in Nuclear Engineering 3 (2024), DOI: `10.3389/fnuen.2024.1384788`.

7. Alguacil et al., *Fast generation of parametric neutronic models for stellarators: Coupling HeliasGeom and GEOUNED*, Fusion Engineering and Design 203 (2024) 114470, DOI: `10.1016/j.fusengdes.2024.114470`.

8. Lyytinen et al., *Proof-of-principle of parametric stellarator neutronics modeling using Serpent2*, Nuclear Fusion 64 (2024) 076042, DOI: `10.1088/1741-4326/ad4f9f`.

These sources establish that the geometry/source-generation and mesh-tally components are plausible, but they do not establish that a native spline CSG primitive will be faster. That remains the central experimental question of this plan.

---

# 23. Final recommendation

The proposed method is worth testing, but the project should be treated first as a **geometry-kernel and performance experiment**, not immediately as a full reactor-analysis tool.

The most defensible initial architecture is:

\[
\boxed{
\text{VMEC/sampled plasma + coil filaments}
\rightarrow
\text{generic coefficient compiler}
\rightarrow
\text{native OpenMC spline CSG}
}
\]

with a parallel scoring path:

\[
\boxed{
\text{same parameterization}
\rightarrow
\text{blanket/coil tally meshes}
\rightarrow
\text{local spectra and boundary data}
}
\]

The strongest feature of this architecture is that it could provide both:

- faster smooth-geometry Monte Carlo without CAD in the transport path; and
- a clean, stable local-coordinate interface for magnet designers and deterministic/atomistic modelers.

The first decisive result should be available before implementing the full device: an exact torus and synthetic helical model showing whether the new smooth primitive is both correct and materially faster than DAGMC/Embree at matched accuracy.
