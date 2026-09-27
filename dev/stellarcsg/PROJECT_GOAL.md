# StellarCSG project goal

## What success means

Create OpenMC CSG geometry that reproduces **complex stellarator plasma boundaries and coil winding-pack shapes**, then run particle transport through those shapes at least **80% as fast as similarly sized simplified built-in OpenMC CSG models**.

| Target | Our geometry must reproduce | Built-in speed reference |
|---|---|---|
| Stellarator plasma | The actual nonaxisymmetric plasma boundary, including periodicity and placement | A basic OpenMC torus of comparable size |
| Magnets/coils | The actual complex coil centreline, pack section and frame, corners, seams, trims and placement | Simple flat rings made with OpenMC cylinders and planes, with comparable size, count and section scale |

The simplified ring and torus are **speed references**. Their shapes may be less accurate. Our custom geometry must retain the complex target shape to pass; substituting a torus or ring for our own target does not meet the project goal.

Current pinned repository benchmark assets are **WISTELL-D**. The latest user wording calls the target **W7-D**; that name is pending confirmation against the pinned dataset. Preserve the actual file/content identities and do not silently substitute another machine's geometry. The overall goal also applies to other stellarator and tokamak configurations.

## Speed means elapsed transport time

For the same number of completed histories and declared physics/settings:

**T_custom_transport <= 1.25 x T_builtin_proxy_transport.**

For example, if the built-in proxy takes 10 seconds, our complex geometry may take at most 12.5 seconds. This is the elapsed-time expression of at least 80% as fast. Report seconds; do not substitute throughput or a geometry microbenchmark.

Each acceptance run must complete **at least 20,000 histories**, with matched source/energy, materials/nuclear data, hardware/threads, histories/seeds, world, tally and output policy. Declare source occupancy and material-path differences caused by the deliberately different proxy shapes. Repeat sufficiently long observations before a precise portable speed claim.

Record these costs separately:

1. Cold geometry construction and export.
2. Cached geometry reuse/export.
3. Runtime initialization/loading.
4. **Particle transport: the primary speed gate.**
5. Output and complete process wall time.

Software compilation is separate from geometry construction. A slower one-time geometry build can be acceptable if repeated transport meets the target. Missing build times stay UNKNOWN, not zero.

## Accuracy and usability must pass too

Independently compare the custom geometry to the intended CAD/equilibrium/pack definition, including first entry/exit, tangencies, thin chords, seams, normals and cell/material ownership. A missed or incorrect crossing cannot count as a speed improvement. The DAGMC reference must represent the same target and use verified Double Down/Embree for the requested performance comparison.

The geometry must work with ordinary OpenMC source generation and tallies: cell/material scoring, smaller local spatial tallies, mesh filters and useful coil/plasma bins. Successful execution or a written statepoint alone does not prove scoring accuracy or compatibility with every OpenMC feature.

## Where to start next

Use the [current method map](METHOD_MAP.md) for the selected **coil** and **nonaxisymmetric plasma** development routes. Use the [benchmark contract](reports/BENCHMARK_CONTRACT_BUILD_TRANSPORT_20260926.md) for acceptance and the [elapsed evidence/branch review](reports/FASTEST_METHOD_BRANCH_REVIEW_20260926.md) for history and limitations.

**Neither full complex coils nor general stellarator plasma has yet passed all accuracy, usability and native-proxy transport gates.**
