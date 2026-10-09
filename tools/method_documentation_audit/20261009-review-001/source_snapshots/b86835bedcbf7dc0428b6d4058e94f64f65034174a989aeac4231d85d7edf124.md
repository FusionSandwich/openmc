# Combined native CSG model

Both staged combined models completed with zero lost particles. The first uses 12 coils; the second uses all 48 retained WISTELL-D coils. Each model contains the native plasma, seven periodic blanket boundaries, a swept-coil set, ordinary Boolean shell cells, and a vacuum sphere. Coil half-spaces are explicitly cut out of every blanket shell, so OpenMC receives a non-overlapping transport partition even where the proposed uniform engineering build intersects a winding.

| Model | Histories | Measured rate | Initialization | Transport | Lost particles |
|---|---:|---:|---:|---:|---:|
| One-period coil subset (12) | 10,000 | 3,331.0 histories/s | 8.3044 s | 2.9884 s | 0 |
| Full coil set (48) | 10,000 | 2,762.19 histories/s | 8.4332 s | 3.6071 s | 0 |

These are smoke-tier diagnostics, not accepted performance medians: each has one warm-up and one measured run, and the host still had elevated desktop activity.

## Engineering clearance result

The full uniform 135.5 cm blanket is not coil-compatible. A signed nearest-surface check over all 12,288 retained coil centerline samples gives a minimum vessel-to-winding clearance of -37.1463 cm, with 1,574 negative samples. The model runs because Boolean coil cut-outs make it topologically valid; that does not turn an intersecting blanket proposal into an acceptable design.

Accordingly, the plasma/blanket-only family is qualified geometrically, the combined cut-out model is a successful interoperability smoke, and the required coil-constrained nonuniform blanket remains `NOT_RUN`. It must be derived from an explicit available-distance field with positive minimum winding clearance.
