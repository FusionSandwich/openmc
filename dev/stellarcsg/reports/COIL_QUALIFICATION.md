# Swept-coil qualification

The retained compiler uses equal-arc-length periodic cubic centerlines and rotation-minimizing frames with the residual closure twist distributed around each closed curve. Circular and elliptical cross sections are represented; rounded rectangles remain outside the accepted envelope.

WISTELL-D coils compiled: 48.  Public ParaStell coils compiled: 40.

Machine-readable diagnostics, content IDs, curvature margins, self- and coil-pair clearances are in `COIL_QUALIFICATION.json`.

| Set | Max frame error | Min adjacent-frame dot | Min curvature margin | Min self-clearance | Min pair clearance |
|---|---:|---:|---:|---:|---:|
| WISTELL-D | 3.331e-16 | 0.997961 | 38.1835 cm | 7.48067 cm | 29.5784 cm |
| ParaStell generic | 3.331e-16 | 0.999595 | 110.376 cm | 9.37637 cm | 67.2326 cm |

The exact circular analytic centerline has maximum independent error 4.72568e-7 cm and is tagged with its equivalent 500 cm major and 25 cm minor torus radii.

The native opt-in OpenMC `SweptSplineSurface` loads and verifies these payloads. The exact planar circular case delegates to the exact torus distance kernel. The generic swept path is still a research reference implementation: it uses a dense global centerline search and scalar refinement, not the requested patch BVH and interval-certified solve. No 10-million-ray generic swept campaign or materialized coil transport has been accepted.
