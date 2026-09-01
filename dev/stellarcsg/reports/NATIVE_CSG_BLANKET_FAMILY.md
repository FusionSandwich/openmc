# Native CSG blanket family

The CAD-free physical-normal compiler accepted the requested six-layer ARIES-like build around both an exact torus and the retained WISTELL-D plasma surface. The cumulative requested thickness is 135.5 cm: 0.5 cm tungsten armor, 10 cm first wall, 55 cm breeding blanket, 10 cm back wall, 30 cm shield, and 30 cm vacuum vessel.

No ParaStell, CadQuery, Gmsh, MOAB, or DAGMC code is used in this native generation path. Each boundary is an independently hash-bound periodic CSG half-space, so the OpenMC regions remain conventional nested Boolean shells.

## Geometry checks

| Check | Exact torus | WISTELL-D |
|---|---:|---:|
| Boundaries | 7 | 7 |
| Strict volume ordering | PASS | PASS |
| Positive minimum Jacobian | PASS | PASS |
| Field-period seam closure | 0 cm | 0 cm |
| Sampled parent separation | positive | positive |
| Compiler fold/intersection rejection | PASS | PASS |
| Clearance to 48-coil winding envelope | NOT_RUN | NOT_RUN |

The exact-torus volumes increase from 9.8696e7 cm³ at the LCFS to 5.4737e8 cm³ at the vessel. WISTELL-D volumes increase from 4.3876e8 cm³ to 1.7205e9 cm³. Full grids, content IDs, Jacobians, sampled separations, and volumes are retained in `NATIVE_CSG_BLANKET_FAMILY.json`.

The WISTELL-D full uniform build is geometrically admissible in the single-chart surface compiler, but it is not yet called coil-compatible: the winding-envelope clearance calculation is deliberately left `NOT_RUN` until the combined model phase. A coil-constrained nonuniform build must be derived from that clearance field rather than assuming the full uniform build fits.

## Retained artifacts

- `dev/stellarcsg/qualified/composite_blanket_families.h5`
- `dev/stellarcsg/plots/composite_blanket_interop/blanket_family_poloidal_sections.png`
- `dev/stellarcsg/plots/composite_blanket_interop/blanket_normal_offset_thickness_maps.png`

The section plot shows all seven boundaries at five toroidal angles. The thickness maps show total same-chart point displacement; for a shaped stellarator this is not itself the requested physical-normal thickness, because each sequential normal offset is remapped to the stable transport chart.
