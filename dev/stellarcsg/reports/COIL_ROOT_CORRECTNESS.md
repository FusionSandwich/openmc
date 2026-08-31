# Swept-coil root correctness

The forced-general planar circular-coil unit corpus compared 100 deterministic rays with the exact torus specialization and found no hit-classification or nearest-root failures.

For the representative WISTELL-D non-planar coil 031, 1,000 deterministic Fibonacci-sphere directions were launched from the matched OpenMC source point. The local span kernel agreed with the independent broad scalar oracle on every hit/miss and nearest distance at the 1e-6 cm gate. Production global-reference calls were zero.

One earlier six-iteration trial exposed a 2.1e-6 cm near-grazing distance error with a 2.24e-7 cm Cartesian residual. That change was rejected; circular acceptance is now scaled to the cross-section rather than total coil length, and the retained 1,000-ray rerun has zero mismatches.

This is initial qualification, not the requested high-statistics closure. The 10-million-ray planar target, at least one million rays per real configuration, thirteen-configuration corpus, and complete coil-set tests remain not run.
