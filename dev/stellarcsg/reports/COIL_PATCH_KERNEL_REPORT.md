# Swept-coil local-span kernel milestone

The production swept-coil path no longer scans the complete centerline or calls the global reference solver. It compiles each periodic cubic centerline into local power-polynomial spans, builds exact Bézier centerline hulls and conservative swept boxes, traverses a flattened BVH2 front-to-back, intersects curvature-expanded capsule proxies, and corrects candidates against the authoritative smooth surface.

For circular sections, the hot solver directly enforces that the ray point is perpendicular to the cubic centerline tangent and exactly one cross-section radius from the centerline. Elliptical sections retain the general projected two-parameter surface solve. Point classification uses a centerline BVH, bracketed local refinement, and an exact-coordinate thread-local cache.

On WISTELL-D coil 031 from `coils.wistell-d` SHA-256 `7748369407d28a70f35b5c4a7c0ab860495a08fd0030002112ea933fe570159b`, the matched-source instrumented microbenchmark measured **631.624 ns per distance call** and **213.908 ns per classification call**. It averaged 7.978 BVH nodes, 0.728 candidate spans, and 2.015 Newton iterations per ray. The 1,000-ray reference comparison had zero mismatches and production made zero global-oracle calls. Local fallback remained 3.7%, above the 0.01% target.

The seven-repeat, single-thread, CPU-pinned 100,000-particle OpenMC result was **432,436 histories/s** for native swept CSG and **910,634 histories/s** for the same-lineage fine direct DAGMC model. Native is **0.4749×** fine DAGMC, or DAGMC is **2.1058× faster**. This is still a failed non-planar coil parity gate, although it is approximately **1.82 million times faster** than the retained 0.2376435 histories/s global-solver baseline.

Native geometry-debug passed 10,000 particles with zero lost particles, geometry errors, or overlapping cells. The fine DAGMC geometry-debug run retained the known explicit-volume/implicit-complement overlap complaint. The pinned DAGMC build is `nompi_nodoubledown`; no Embree/Double Down result was produced.

The next architectural requirement is the shared top-level coil-set BVH. The current result qualifies one representative surface kernel only and must not be extrapolated to a 48–78 coil set.
