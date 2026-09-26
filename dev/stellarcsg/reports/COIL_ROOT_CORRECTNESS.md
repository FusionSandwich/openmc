# Swept-coil root correctness

The forced-general planar circular-coil unit corpus compared 100 deterministic rays with the exact torus specialization and found no hit-classification or nearest-root failures.

For the representative WISTELL-D non-planar coil 031, 1,000 deterministic Fibonacci-sphere directions were launched from the matched OpenMC source point. The local span kernel agreed with the independent broad scalar oracle on every hit/miss and nearest distance at the 1e-6 cm gate. Production global-reference calls were zero.

One earlier six-iteration trial exposed a 2.1e-6 cm near-grazing distance error with a 2.24e-7 cm Cartesian residual. That change was rejected; circular acceptance is now scaled to the cross-section rather than total coil length, and the retained 1,000-ray rerun has zero mismatches.

For the complete 48-coil WISTELL-D set, 1,000 deterministic rays agreed with a brute scan of all per-coil fast kernels. A further 100 rays were compared with 4,800 independent broad per-coil oracle solves: zero misses, false hits, or wrong nearest roots, with maximum distance error `1.1162e-9 cm`. Production global-reference calls remained zero.

This is initial qualification, not the requested high-statistics closure. The 10-million-ray planar target, at least one million rays per real configuration, and thirteen-configuration independent-oracle corpus remain not run.
