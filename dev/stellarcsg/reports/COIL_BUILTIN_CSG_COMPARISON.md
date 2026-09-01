# Coil comparison against built-in CSG

The exact C0 control passes. With identical 500 cm major radius, 25 cm tube radius, source, boundary, seed, binary, and one pinned thread, the native exact planar swept coil reached a median 724,869 histories/s versus 690,434 for built-in `ZTorus`: **1.04987× built-in** across seven randomized measured repetitions. Both transported 7,000,000 measured histories with zero lost particles.

The speed recovery comes from the intended design: the swept adapter caches the planar torus parameters and calls the same `openmc::torus_distance` kernel as `SurfaceZTorus`. Permanent adapter tests compare multiple exact roots directly and obtain bitwise-equal distances. Production broad-oracle calls are zero.

The forced-general path is intentionally retained and selectable with `solver="general"`, but it reached only 68,707.9 histories/s, or 0.09951× built-in. It therefore fails the preferred 0.75 gate. This is a real negative result: generic span solving is a correctness/control path for an exactly reducible coil, not a competitive transport path.

C1 elliptical-section, C3 racetrack, C4 capsule-chain, and matched C0 DAGMC/Double Down campaigns remain `NOT_RUN`. C2 is not applicable to the accepted closed-centerline contract. These statuses are not inferred from C0.
