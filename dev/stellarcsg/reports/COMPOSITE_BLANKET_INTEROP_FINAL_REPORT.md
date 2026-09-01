# Composite blanket and interoperability qualification report

## Outcome

This phase establishes two strong positive results and several explicit boundaries.

First, exact planar circular swept coils now use a native OpenMC adapter fast path. The adapter caches torus parameters and invokes the same quartic kernel as built-in `ZTorus`, while `solver="general"` keeps the general span path selectable. Seven randomized million-history runs gave 724,869 histories/s exact swept versus 690,434 built-in, or 1.04987×, with zero lost particles and exact root equality to the shared kernel. The forced-general result was only 0.09951× and fails its preferred gate.

Second, the accepted periodic torus remains at statistical parity. Twenty-one randomized million-history runs gave 711,268 histories/s exact periodic versus 696,970 built-in, ratio 1.02051. The bootstrap 95% interval is 0.97160–1.03215 and the one-sided 95% lower bound is 0.97647, passing the 3% non-inferiority requirement.

The direct physical-normal compiler also produced the requested six-layer, 135.5 cm ARIES-like family around both an exact torus and WISTELL-D. All 14 boundaries have positive Jacobians, strict volume ordering, positive sampled parent separation, and zero field-period seam error. However, the full WISTELL-D uniform build intersects the winding envelope: minimum sampled signed clearance is -37.1463 cm. It is qualified as a plasma/blanket geometry family, not as a coil-compatible blanket design.

## Interoperability and combined geometry

Custom surfaces serialize in ordinary Boolean intersections, unions, complements, mixed standard/custom regions, all four ordinary boundary labels, XML, and summary HDF5. A hybrid native-CSG outer region filled by the identical fine DAGMC torus passed in both ordinary and Double Down-linked executables with zero lost particles. Double Down linkage to Embree 4.3.0, Double Down 1.1.0, DAGMC 3.2.4, and MOAB 5.5.1 is verified at runtime.

The combined WISTELL-D model—native plasma, seven blanket boundaries, and either 12 or 48 native swept coils—also completed with zero lost particles. Its smoke rates were 3,331.0 and 2,762.19 histories/s respectively, but those are one-repetition diagnostics, not qualified medians. Boolean coil cut-outs make the intersecting uniform build a valid transport partition; they do not make it an acceptable engineering clearance.

Rigid transforms remain explicitly unsupported because payload-backed surfaces do not yet carry a local/global transform in OpenMC XML. The result is recorded as a failed capability, not silently substituted with unrelated cell-fill transforms.

## Validation

The final sweep passed 32 checks with zero failures: 2 Release CTests, 2 ASan/UBSan CTests, 14 StellarCSG Python tests, 12 OpenMC custom-surface API tests, and one adapter test in each ordinary-DAGMC and Double Down-linked executable. The default experimental-OFF build and built-in torus transport smoke passed earlier in the same worktree.

## Qualification boundary

This branch is not a complete qualification of the entire execution prompt. C1 elliptical exact coils, C3 racetrack, C4 capsule-chain, 1–12 layer performance scaling, a coil-constrained nonuniform blanket, rigid transforms, full ecosystem plot/volume/filter/restart transport, the complete repeated ordinary-DAGMC versus Double Down matrix, multi-thread scaling, and Tier 3 materialized tally closure remain `NOT_RUN`. The full gate table is in `COMPOSITE_BLANKET_INTEROP_GATE_STATUS.json`.

No pull request was created. The default, qualified, and both archive branches were not modified; only `codex/stellarcsg-composite-blanket-interoperability-20260901` was pushed.
