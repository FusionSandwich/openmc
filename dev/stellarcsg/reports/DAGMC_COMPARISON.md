# DAGMC comparison status

Updated: 2026-08-31

A same-source exact-torus comparison is retained. No synthetic-helical,
ParaStell, WISTELL-D, or coil DAGMC comparison is accepted.

## Pinned environment and joint binary

- Container: `parastell-openmc:0.16.0`
- Image ID: `sha256:ca0c3b1fba39ce27af6ebdb79df14795041922e72521f232cdd770ff1c416191`
- Branch OpenMC: `0.15.1-dev598`, commit
  `594670eee8a0c1e26a5b44d713468f74f4204ce3`
- DAGMC 3.2.4, cad_to_dagmc 0.11.5, CadQuery 2.7.0, Gmsh backend,
  PyMOAB H5M writer.
- CMake options: `OPENMC_USE_DAGMC=ON`,
  `OPENMC_ENABLE_EXPERIMENTAL_STELLARCSG=ON`, `OPENMC_USE_UWUW=OFF`.

No package was downloaded or installed for this build. The already-local
container supplied all headers and libraries.

## Same-source faceting convergence

The CAD source is the same exact circular torus used by the native benchmark:
major radius 500 cm and minor radius 100 cm.

| Mesh | Gmsh min/max size | Triangles | Sampled max error | Area rel. error | Volume rel. error | SHA-256 |
|---|---:|---:|---:|---:|---:|---|
| coarse | 10/25 cm | 8,682 | 1.473345 cm | -1.7031e-3 | -6.8902e-3 | `393ec6ef79718aa0c90996e74cc68303fc000ea0c9b258dcdf19fc7d57215a0b` |
| fine | 3/10 cm | 52,030 | 0.236576 cm | -2.8650e-4 | -1.1732e-3 | `2377cfa960399ce18ece599a736d8e9adb602a632339f541f4fb73530afdcb56` |

Surface error was sampled at every triangle vertex, edge midpoint, and
centroid. Both meshes pass DAGMC `check_watertight` with zero unsealed surfaces
or volumes and `overlap_check -p 3 -t 1` with no overlaps found.

## Matched collisionless transport

One joint OpenMC binary, one thread, 1,000,000 histories, fixed seed 918273645,
one warm-up, and five measured repetitions were used. DAGMC material tags were
bound to H1 at `1e-30 atom/b-cm`; all cases leaked 1.0 and had zero lost
particles.

| Case | Median histories/s | Min | Max | IQR | Median init (s) | Ratio to built-in |
|---|---:|---:|---:|---:|---:|---:|
| built-in torus | 393,278 | 296,996 | 469,424 | 38,363 | 3.3444 | 1.0000 |
| periodic spline torus | 210,111 | 173,825 | 217,592 | 14,903 | 2.7421 | 0.5343 |
| DAGMC coarse | 67,852.0 | 63,376.9 | 69,509.0 | 1,376.5 | 1.2052 | 0.1725 |
| DAGMC fine | 57,496.7 | 57,052.3 | 58,921.4 | 849.1 | 1.4405 | 0.1462 |

The periodic spline was 3.0966x faster than coarse DAGMC and 3.6543x faster
than fine DAGMC by median active histories/s. This meets the requested 1.3x
native-versus-DAGMC rate target for this exact-torus case.

## Geometry-debug caveat

Built-in and periodic-spline OpenMC `-g` runs passed with zero reported
overlaps. Both DAGMC `-g` runs stopped at batch 1 with
`Overlapping cells detected: 10001, 10002 on universe 1`, the explicit torus
volume versus DAGMC's implicit complement. This reproduces with and without an
explicit complement material tag, even though the independent DAGMC
watertightness and overlap utilities pass.

The timing results are retained as completed transport measurements, but the
DAGMC geometry is not promoted to fully geometry-debug-qualified status.

## Commands and retained evidence

```text
python dev/stellarcsg/benchmarks/generate_dagmc_exact_torus.py
check_watertight <mesh.h5m>
overlap_check -p 3 -t 1 <mesh.h5m>
python dev/stellarcsg/benchmarks/run_matched_dagmc_torus.py --repetitions 5
```

Machine-readable fidelity and timing receipts, raw repetitions, H5M files, and
plots are retained under `dev/stellarcsg/reports`,
`dev/stellarcsg/qualified`, and `dev/stellarcsg/plots/dagmc`.

## Remaining DAGMC boundary

No same-lineage H5M was generated for the helical plasma, nested layers,
ParaStell VMEC/coils, WISTELL-D plasma/blanket/coils, or swept circular coil.
The smallest next action is to resolve or formally classify the OpenMC
implicit-complement `-g` result, then repeat the same pinned generation and
convergence workflow for the exact circular coil.
