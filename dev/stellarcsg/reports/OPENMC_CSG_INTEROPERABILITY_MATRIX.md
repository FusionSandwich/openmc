# OpenMC CSG interoperability matrix

The custom surfaces participate in ordinary OpenMC half-space, intersection, union, and complement expressions. Targeted Python tests cover mixed regions with cylinders and spheres, deep complement structure, XML expression reconstruction, all four ordinary boundary labels, HDF5 summary reconstruction, and the new swept `auto`/`general` solver metadata. All 12 targeted tests passed.

A true hybrid transport smoke also passed in both linked executables: a native exact periodic blanket-vessel surface bounded the outer CSG cell and filled it with the identical fine DAGMC torus universe. The ordinary DAGMC-linked binary transported 10,000 histories with zero lost particles; the Double Down binary printed its Embree interface banner and also completed with zero lost particles. Their one-shot rates are retained only as diagnostics, not qualified ratios.

## Important boundary

Rigid translation and rotation remain explicitly unsupported for both payload-backed surface types. OpenMC's normal analytic surfaces transform by rewriting coefficients; these surfaces keep immutable external payloads, and no surface-level local/global transform is represented in current OpenMC XML. Silently pretending that cell-fill transforms solve this surface contract would be wrong. This phase therefore records transformation as `UNSUPPORTED_EXPLICIT_REJECTION`, while native geometry can still be placed through supported universe-fill architecture.

Vacuum, reflective, and white boundary values round-trip correctly, and exact-specialized normals are independently checked. Dedicated reflected-particle transport tests, plot generation, stochastic volumes, filters, and restart tests remain `NOT_RUN`; the JSON matrix never upgrades serialization evidence into transport qualification.
