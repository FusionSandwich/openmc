# WISTELL-D qualification

Updated: 2026-08-30

The authoritative WISTELL-D VMEC boundary passes the compiler's supported
single-chart envelope. Six cumulative physical-normal boundaries were accepted:
LCFS, first wall (2 cm), breeder (40 cm), back wall (2 cm), shield (30 cm), and
vessel (5 cm). The displaced physical points were remapped and refitted; the
layers were not formed by adding thickness to the magnetic-axis radius.

## Provenance

| Input | SHA-256 |
|---|---|
| `wout_wistell-d.nc` | `9231969001203a8133255ee0a275bf552b114cc12524dda0608ab2f12047f7ac` |
| `coils.wistell-d` | `7748369407d28a70f35b5c4a7c0ab860495a08fd0030002112ea933fe570159b` |
| `blanket_boundary.npy` | `fdb85b2c0c8cd72f5d000302e0b67349ebf72679f98f9c4d7739e5d8484cdde3` |
| `magnet_boundary.npy` | `3579e5d8fe97dd74c8700e5676964159f00f07989ca6436528f60462889f05bd` |
| `nwl.npy` | `56baa090d61b67273efba61213849b7516beabb2a57fc2ad4751a6f3a32b2db4` |

The source has four field periods. The retained LCFS payload uses 512 poloidal
by 192 toroidal coefficients and content ID
`sha256:0d299bcfa901c5c5572abee7926ba9814b4220e96721c5e5c5c680aff3584f26`.

## Independent-grid fidelity

| Metric | Result |
|---|---:|
| Independent points | 197,633 |
| Maximum Cartesian / approximate Hausdorff error | 0.0343814882 cm |
| RMS Cartesian error | 0.00241720174 cm |
| p95 Cartesian error | 0.00288530862 cm |
| Maximum normal-angle error | 0.119189736 deg |
| RMS normal-angle error | 0.0113659102 deg |
| Surface-area relative error | -6.98034e-8 |
| Volume relative error | -7.11035e-8 |
| Source/model seam closure | 4.58286e-13 / 0 cm |
| Minimum radius | 44.5109905 cm |
| Minimum source/model Jacobian | 75,113.6467 / 51,821.7182 cm2 |
| Classification | `PASS_SINGLE_CHART` |

The public ParaStell VMEC example is separately provenance-labeled and is
rejected as `REJECT_THETA_FOLD`; it is not substituted for WISTELL-D.

## Coil compiler result

All 48 WISTELL-D filament coils compiled to periodic equal-arc cubic
centerlines with rotation-minimizing frames. With the qualification cross
section (10 cm by 8 cm), the minimum coil-pair clearance is 29.5783951 cm. All
reported curvature margins and nonlocal self-clearances are positive; detailed
per-coil frame and clearance values are retained in `COIL_QUALIFICATION.json`.

## Retained artifacts

- `dev/stellarcsg/qualified/wistell_d_periodic_surfaces.h5`
- `dev/stellarcsg/qualified/wistell_d_swept_coils.h5`
- `dev/stellarcsg/reports/WISTELL_D_FIDELITY.json`
- `dev/stellarcsg/reports/COIL_QUALIFICATION.json`
- `dev/stellarcsg/plots/wistell_d/poloidal_slices.png`
- `dev/stellarcsg/plots/wistell_d/fit_error_heatmap.png`
- `dev/stellarcsg/plots/wistell_d/views.png`
- `dev/stellarcsg/plots/coils/wistell_d_full_coils.png`

These are compiler/fidelity artifacts, not a completed materialized WISTELL-D
transport or same-lineage DAGMC qualification.
