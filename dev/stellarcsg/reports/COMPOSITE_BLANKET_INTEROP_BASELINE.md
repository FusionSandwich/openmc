# Composite blanket and interoperability baseline

The c0290b exact-torus checkpoint is preserved and its correctness baseline has been reproduced on the isolated research branch. All standalone, sanitizer, Python, ordinary-DAGMC-linked adapter, and Double Down/Embree-linked adapter tests passed. A default build with the experimental option left off compiled and transported 1,000,000 histories through the built-in `ZTorus` model with zero lost particles.

## Frozen performance references

The accepted exact-torus paired result remains the performance gate: built-in `ZTorus` 749,597 histories/s median versus exact periodic spline 730,255 histories/s, a ratio of 0.9741968. The retained pre-fastpath planar swept-coil result was 384,171 histories/s versus 929,676 histories/s for its built-in torus control, showing the adapter wrapper path—not the quartic kernel—is the first coil optimization target. The retained WISTELL-D 48-coil native median is 289,656 histories/s versus 49,189.5 histories/s for the fine ordinary DAGMC mesh.

No new timing sample was accepted during this freeze because an unrelated WSL DPA calculation and four broad filesystem searches were active. This is a contamination guard, not a performance failure. The paired torus, single-coil, and 48-coil reruns remain required and will be retained after the host is quiet.

## Current call graph and optimization boundary

- Exact periodic surfaces cache torus parameters in the OpenMC adapter. Their evaluation and normal use direct algebra, and distance calls the same `openmc::torus_distance` helper as `SurfaceZTorus`.
- A single swept surface is loaded and compiled once. Planar circular coils are already recognized inside `CompiledSweptSplineSurface`, but adapter calls still pass through the swept object, an internal periodic object, result packaging, and per-call root-option construction before reaching the shared quartic kernel.
- A swept collection adds a top-level coil BVH and dispatches to individual compiled coils.
- Ordinary OpenMC regions determine senses with `Surface::evaluate` and crossings with virtual `Surface::distance`; supported fill transforms are handled at cell/universe level.
- DAGMC geometry is a separate universe implementation backed by DAGMC/MOAB. Native CSG cells can fill a DAGMC universe, but transformed DAGMC cells are rejected by the current code.

The safe Phase 1 change is therefore a native exact-planar swept adapter path that caches the same torus parameters and calls the same OpenMC kernel while retaining a selectable forced-general path.

## Reproduced checks

| Check | Result |
|---|---:|
| Standalone Release CTest | 2/2 PASS |
| GCC ASan/UBSan CTest | 2/2 PASS |
| Python pytest | 14/14 PASS |
| Ordinary DAGMC-linked adapter CTest | 1/1 PASS |
| Double Down/Embree-linked adapter CTest | 1/1 PASS |
| Default experimental-OFF build and built-in torus smoke | PASS |
| Native swept-coil smoke in ordinary linked binary | PASS |
| Native swept-coil smoke in Double Down/Embree linked binary | PASS |

The Double Down executable resolves `libdagmc.so`, `libdd.so`, `libembree4.so.4`, and `libMOAB.so.5` at runtime. Exact binary hashes and raw-reference paths are in `COMPOSITE_BLANKET_INTEROP_BASELINE.json`.
