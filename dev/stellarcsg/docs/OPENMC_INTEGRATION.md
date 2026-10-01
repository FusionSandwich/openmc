# Local tallies and plasma sources with native spline CSG

The integration target is the ordinary OpenMC model: spline surfaces define
`Cell.region`; standard cells, materials, filters, tallies and source objects
remain in use. There is no separate spline tally format. Experimental native
surface support must be enabled in the OpenMC library/executable.

## Small local scoring regions

Two approaches are useful:

1. Overlay a standard mesh on the CSG geometry. A `MeshFilter` scores local
   pieces of tracks/events without changing the material geometry. Add a
   `CellFilter` or `MaterialFilter` to restrict the scored part of each bin.
2. Split an existing spline-bounded region using ordinary planes, boxes or
   other CSG regions and assign the same material to the resulting cells.
   `CellFilter` then selects the desired subvolume. The pieces must partition
   the original region without gaps or overlap.

The helper now accepts ordinary OpenMC meshes, including regular, rectilinear,
cylindrical and spherical meshes. MOAB is needed only for the optional
unstructured MOAB mesh path, not for native CSG itself:

```python
import openmc
from stellarcsg.openmc_tally import make_energy_resolved_mesh_tally

# Coordinates in cm; select a box appropriate to the existing model.
mesh = openmc.RegularMesh()
mesh.dimension = (20, 20, 20)
mesh.lower_left = (98., -3., -3.)
mesh.upper_right = (103., 3., 3.)
local = make_energy_resolved_mesh_tally(
    mesh=mesh,
    cells=[coil_cell],
    energy_bounds_eV=[0., 1e3, 1e5, 1e6, 5e6, 10e6, 14.2e6],
    scores=["flux", "total", "absorption", "damage-energy"],
)
model.tallies.append(local)
```

This creates an ordinary `openmc.Tally`; use `StatePoint.get_tally`,
`get_slice`, `get_reshaped_data` and `get_pandas_dataframe` for results. Surface
currents use `SurfaceFilter`; mesh-face currents use `MeshSurfaceFilter`.
Normal OpenMC score/filter/estimator compatibility rules still apply.

Scores retain OpenMC's per-source normalization. Tracklength flux before volume
normalization is cm/source. For a mesh intersected with a cell, **the full mesh
element volume is not the scored material volume**. Use the intersection's
volume, with appropriate uncertainty, for volume-averaged flux or atom-count
normalization. `VolumeCalculation` can estimate explicitly split local-cell
volumes using native geometry. A material DPA conversion additionally requires
a declared damage model, composition, displacement energies and source rate.
Neither the helper nor a plotting/export function should silently supply them.

## New plasma sources

Use ordinary `openmc.MeshSource` as the integration interface for a spatial
plasma profile. It accepts standard meshes or supported unstructured meshes,
with an `IndependentSource` for each element. The following is a diagnostic
source inside the R=100 cm/r=20 cm torus proxy, not a device source profile:

```python
source_mesh = openmc.RegularMesh()
source_mesh.dimension = (2, 1, 1)
source_mesh.lower_left = (95., -1., -1.)
source_mesh.upper_right = (105., 1., 1.)
components = [
    openmc.IndependentSource(
        strength=p,
        angle=openmc.stats.Isotropic(),
        energy=openmc.stats.Discrete([energy], [1.]),
    )
    for p, energy in [(0.25, 2.45e6), (0.75, 14.1e6)]
]
model.settings.source = openmc.MeshSource(
    source_mesh, components,
    constraints={"domains": [plasma_cell], "rejection_strategy": "resample"},
)
```

Element strengths are integrated source probabilities/rates, not unintegrated
emissivity densities. Multidimensional arrays must follow OpenMC mesh ordering.
The example preserves an explicit position/energy correlation. Directions,
energy in eV, coordinates in cm and physical rate must be specified separately.

The domain constraint is evaluated by compiled OpenMC cell lookup, including
the spline boundary. It can reject sites outside the plasma. **Rejection is
not a substitute for fitting the source support:** it can change element
probabilities and energy correlations. Prove or independently bound complete
source-element containment and preserve the intended profile before admitting
a physical source. Sampling checks alone do not prove whole-cell containment.

With an initialized model, `openmc.lib.sample_external_source` and
`openmc.lib.find_cell` provide native sampling and containment diagnostics.
`CellBornFilter`/`MeshBornFilter` provide transport diagnostics, but secondary
neutrons can be born in material outside the original source mesh. Do not
require all secondary birth positions to lie in the plasma source support.

The existing VMEC/UQ adapter remains an optional producer of the same
MeshSource interface. Its current handoff uses MOAB and binds clearance to a
fixed wall H5M. That wall identity does not establish equivalence to a CSG
plasma boundary. See `PLASMA_SOURCE_HANDOFF.md` for admission constraints. No
physical WISTELL-D source is admitted by the new diagnostic tests.

## Compatibility boundaries and coverage

The executable integration suite is
`dev/stellarcsg/qualification/check_openmc_integration.py`; its bounded runner
and receipts are under `reports/openmc-integration-20260926/`. It checks plasma
native/spline pairs with mesh and constrained-box sources, and coil native/
spline pairs with a file source. Check that report's results before treating
any capability as tested. The mesh-source case is deliberately standard-mesh;
it does not test a real UQ MOAB bundle.

The [completed results](../reports/openmc-integration-20260926/RESULTS.md)
retain the initial failed spatial comparison and the fresh passing campaign
after a native spherical-mesh equator repair. Thirty-seven plasma tally
comparisons pass the unchanged numerical criterion; eighteen coil comparisons
pass a looser approximation criterion. These are finite proxy regressions,
not full-spectrum statistical qualification or a performance benchmark.

The initial matrix covers local subcells; regular/rectilinear/cylindrical/
spherical meshes; mesh plus cell/material restrictions; energy spectra;
tracklength/collision/analog scores; surface and mesh-face current; cell
instances; universe, birth-cell, birth-mesh, time, particle, outgoing-energy,
scattering-cosine and response-function filters; native local volume;
XML/Summary/StatePoint, DataFrame, reshape and score slicing.

Further qualification is required for repeated-universe/lattice instances,
distributed cells, derivatives, MGXS/depletion, weight windows and variance
reduction, coupled neutron/photon transport, MPI/OpenMP, unstructured backends,
boundary conditions, arbitrary non-axisymmetric plasma and full magnet packs.
Success in the initial matrix does not certify every filter/score combination.

Pure-Python `point in spline_region` / `Geometry.find()` still lack a spline
evaluator. Use the initialized native C API for geometric membership. Generic
Python surface translation/rotation remains unsupported; transform and rebind
coefficient payloads. Python plotting/automatic model-building tools that
depend on these methods require their own adapters or tests. These limitations
must remain visible rather than being bypassed with an approximate torus.

Official interfaces: [OpenMC tally specification](https://docs.openmc.org/en/stable/io_formats/tallies.html),
[MeshFilter](https://docs.openmc.org/en/stable/pythonapi/generated/openmc.MeshFilter.html),
and [source API](https://docs.openmc.org/en/stable/_modules/openmc/source.html).
