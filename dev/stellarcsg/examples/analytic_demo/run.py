"""Generate a CAD-free helical reactor radial build and tally mesh."""

from pathlib import Path

from stellarcsg import (
    PeriodicRadialSurfaceData,
    build_layer_mesh,
    compile_radial_build,
    write_legacy_vtk,
    write_mesh_hdf5,
    write_surface_collection,
)

output = Path(__file__).resolve().parent / "output"
output.mkdir(exist_ok=True)

plasma = PeriodicRadialSurfaceData.analytic_torus(
    name="plasma",
    major_radius_cm=500.0,
    minor_radius_cm=100.0,
    n_field_periods=5,
    helical_amplitude_cm=8.0,
    n_axis=16,
    n_theta=32,
    n_phi=24,
)
boundaries = compile_radial_build(
    plasma,
    [
        ("first_wall_outer", 2.0),
        ("blanket_outer", 50.0),
        ("shield_outer", 40.0),
    ],
)
write_surface_collection(output / "compiled_geometry.h5", boundaries)
mesh = build_layer_mesh(
    boundaries,
    radial_bins_per_shell=(1, 2, 2),
    theta_bins=32,
    phi_bins=24,
    toroidal_extent="field-period",
)
write_mesh_hdf5(output / "tally_mesh.h5", mesh)
write_legacy_vtk(output / "tally_mesh.vtk", mesh)
print(f"wrote {len(boundaries)} surfaces and {mesh.n_elements} tally elements")
