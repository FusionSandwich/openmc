# Matched DAGMC comparison

The complete 48-coil WISTELL-D result reverses the earlier single-coil ranking. With 100,000 histories, seven randomized repetitions, one pinned CPU, and identical source, seed, materials, and source lineage, native CSG reached **289,656 histories/s**. Coarse and fine direct DAGMC reached **69,868.9** and **49,189.5 histories/s**. Native was **5.889× faster than fine DAGMC**.

The representative non-planar single-coil gate remains a failure: native reached 432,436 histories/s versus 910,634 for fine DAGMC, or 0.4749×. WISTELL-D periodic plasma passed the minimum gate at 1.2386× fine DAGMC but missed the preferred 1.3× target.

Native geometry-debug passed. Both complete-set DAGMC meshes complete ordinary transport without lost particles and pass independent watertightness/overlap checks, but OpenMC geometry-debug reports explicit-volume/implicit-complement overlap (`10049, 10001`). This negative result is retained. Embree/Double Down was unavailable in the pinned `nompi_nodoubledown` binary and was not inferred from direct DAGMC.
