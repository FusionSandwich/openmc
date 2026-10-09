# Independent performance review

Accepted the narrow A/B observation after reading the six retained runs and recalculating their metrics. All six have 160 canonical ordered IDs, successful exits, valid output, 69 hits and 91 misses, stable identical recorded inputs and the same build-14 executable. Commands differ only by disabling the optional Bernstein prefix. The child intervals do not overlap.

The mean summed distance-call time is 0.865648128 s on and 3.507428628 s off: 4.052 times faster observed with the prefix. Mean child walltime is 1.547896783 s on and 4.032761971 s off: 2.605 times faster observed. These denominators measure different work and should remain separately labeled.

Every non-timing query field is bit-for-bit identical across replicates within each variant. That includes geometry/coefficient identity, origins, normalized directions, disposition, returned binary64 distance, and scientific state. The exact 04/05 certificates therefore cover identical results in 10/12 and 11/13 respectively; timings do not alter the mathematical certificates. No new oracle was run.

All six retain the same nine normal/projection telemetry blocks (a00 and w0-w7) and nine missing normal timings. Distance and evaluate timings are complete. This is not complete normal-service performance or throughput acceptance.

Excluding 06-09 because they overlapped the independent Fraction verifier is conservative and matches the declared operational context. That overlap was not reconstructed from process receipts here. The retained runs are still local observations subject to background load, fixed on/off ordering and only three pairs; no confidence interval or general causal performance guarantee follows.

The comparison is the same exact-control implementation with its optional acceleration disabled. It does not establish native throughput, particle transport, physical varying-frame coil performance or the 80% milestone. Historical final-acceptance.json was preserved. Detailed hashes and recalculated values are in performance-review.json.
