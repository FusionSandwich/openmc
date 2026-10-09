# Double Down / Embree composite results

The new research build is genuinely linked to DAGMC 3.2.4, Double Down 1.1.0, Embree 4.3.0, and MOAB 5.5.1. Runtime linkage inspection resolves all four libraries, and execution prints `Using the DOUBLE-DOWN interface to Embree.` The adapter test and native swept-surface smoke both pass.

A hybrid model containing a native periodic CSG outer region and the identical fine DAGMC torus universe completed 10,000 histories with zero lost particles in both linked executables. The one-shot diagnostic rates were 38,688.1 histories/s ordinary and 69,137.6 histories/s Double Down.

Those numbers are not promoted to a qualified speedup: they are single smoke runs with elevated desktop activity. The required seven-repetition matched campaigns across every coil, blanket, and combined case remain `NOT_RUN`. Retained ordinary-DAGMC results are not relabeled as Embree results.
