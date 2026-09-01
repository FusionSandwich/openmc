# Exact torus final parity study

The accepted periodic exact-torus fast path does not regress. Across 21 randomized million-history repetitions on one pinned CPU, built-in `ZTorus` reached 696,970 histories/s median and the exact periodic surface reached 711,268 histories/s median, a ratio of **1.02051**.

The bootstrap 95% interval for the median ratio is 0.97160–1.03215. Its one-sided 95% lower bound is 0.97647, so the study excludes a slowdown worse than 3%. The hard 0.95 gate, preferred 3% non-inferiority gate, and 0.99 stretch median gate all pass. Both cases completed 21,000,000 measured histories with zero lost particles.

The means are 704,088.3 histories/s built-in and 702,026.4 exact periodic. That small reversal between mean and median, together with the overlapping distributions, is reported as statistical parity rather than evidence that either shared-kernel wrapper is intrinsically faster.
