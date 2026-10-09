# Adoption readiness

The experimental surface remains opt-in and defaults to `OPENMC_ENABLE_EXPERIMENTAL_STELLARCSG=OFF`. The runtime adds no mandatory dependency, performs no HDF5 access or allocation in `distance()`, retains ordinary OpenMC surface semantics, and keeps the independent global solver outside the production hot path.

Ready for continued experimental use:

- periodic local patch/BVH kernel with zero production oracle calls;
- swept-coil span/BVH kernel with circular and general elliptical narrow phases;
- shared top-level coil-set BVH and XML/HDF5 collection loading;
- deterministic standalone, sanitizer, adapter, and geometry-debug coverage;
- same-lineage WISTELL-D native/DAGMC evidence and 13-configuration coil-oracle coverage.

Not ready for upstream adoption:

- general periodic forced-torus, shaped-axisymmetric, and synthetic-helical OpenMC performance gates were not run;
- WISTELL-D plasma common-accuracy closure is incomplete;
- single non-planar coil is still 2.106× slower than fine DAGMC;
- local coil fallback exceeds the preregistered 0.01% target;
- blanket layer-family sharing is not implemented;
- DAGMC OpenMC geometry-debug reports the explicit/implicit-complement overlap;
- Embree/Double Down and Tier 3 materialized transport were not run;
- high-statistics 10-million/1-million-ray targets remain incomplete.

No pull request should be opened from this milestone without resolving or explicitly narrowing these boundaries.
