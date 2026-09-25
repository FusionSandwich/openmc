# Periodic parametric-patch kernel milestone

The generic WISTELL-D periodic CSG path is now faster than the same-lineage fine direct DAGMC model in the matched single-thread OpenMC geometry gate.

Five measured 10,000-history repetitions gave medians of **26,643.8 histories/s** for native CSG and **21,511.8 histories/s** for fine DAGMC: native CSG is **1.2386× faster**. This is a **299× improvement** over the retained 89.11265 histories/s global-solver baseline. Both methods reported zero lost particles and zero geometry errors. The preferred 1.3× gate was narrowly missed.

The instrumented file-surface microbenchmark median was **11.82672 µs per distance call** over seven repetitions. It visited 66.713 BVH nodes and 6.696 candidate patches per call, used 16.953 Newton iterations per call, and made zero production global-oracle calls. These internal counts exceed the aspirational targets and remain optimization opportunities.

The kernel uses conservative spline-span patches, curvature/twist-expanded triangle proxies, a flattened front-to-back BVH2, patch-local power-polynomial evaluation, damped projected Newton, and bounded local ray/tangent recovery. The broad global interval implementation remains private evidence and is not reachable from production `distance()`.

Correctness passed 100,000 randomized forced-general torus rays plus 4,099 adversarial rays with no failures. The 10-million-ray and real-device randomized oracle targets remain not run.

This milestone establishes the speed result, not final common-accuracy closure. Native leakage was 0.9955 and fine-mesh leakage was 1.0 in the short collisionless gate; common full-surface error and independent classification still need to resolve that difference.
