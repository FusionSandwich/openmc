from __future__ import annotations

import json

import h5py
import numpy as np

from stellarcsg import (
    PeriodicRadialSurfaceData,
    build_layer_mesh,
    compile_radial_build,
    write_legacy_vtk,
    write_mesh_hdf5,
)


def test_layer_mesh_is_positive_and_volume_converges(tmp_path) -> None:
    major = 500.0
    inner_radius = 100.0
    thickness = 20.0
    base = PeriodicRadialSurfaceData.analytic_torus(
        name="inner", major_radius_cm=major, minor_radius_cm=inner_radius
    )
    outer = base.with_radial_thickness("outer", thickness)
    mesh = build_layer_mesh(
        [base, outer],
        radial_bins_per_shell=2,
        theta_bins=80,
        phi_bins=96,
        toroidal_extent="full",
    )
    volumes = mesh.approximate_element_volumes_cm3()
    assert mesh.n_elements == 2 * 80 * 96
    assert np.min(volumes) > 0.0
    exact = 2.0 * np.pi**2 * major * (
        (inner_radius + thickness) ** 2 - inner_radius**2
    )
    assert abs(np.sum(volumes) - exact) / exact < 0.01

    h5_path = tmp_path / "mesh.h5"
    vtk_path = tmp_path / "mesh.vtk"
    write_mesh_hdf5(h5_path, mesh)
    write_legacy_vtk(vtk_path, mesh)
    assert vtk_path.read_text(encoding="utf-8").startswith("# vtk DataFile")
    with h5py.File(h5_path, "r") as h5:
        assert h5["connectivity"].shape == (mesh.n_elements, 8)
        assert json.loads(h5.attrs["surface_names_json"]) == ["inner", "outer"]


def test_field_period_mesh_and_metadata() -> None:
    base = PeriodicRadialSurfaceData.analytic_torus(
        name="plasma",
        major_radius_cm=500.0,
        minor_radius_cm=100.0,
        n_field_periods=5,
        helical_amplitude_cm=5.0,
    )
    boundaries = compile_radial_build(base, [("wall", 2.0), ("shield", 30.0)])
    mesh = build_layer_mesh(
        boundaries,
        radial_bins_per_shell=(1, 3),
        theta_bins=20,
        phi_bins=12,
        toroidal_extent="field-period",
    )
    assert mesh.n_elements == (1 + 3) * 20 * 12
    assert np.isclose(mesh.toroidal_extent_rad, 2.0 * np.pi / 5.0)
    assert set(mesh.shell_index) == {0, 1}
    assert set(mesh.radial_index[mesh.shell_index == 1]) == {0, 1, 2}
