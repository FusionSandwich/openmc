from __future__ import annotations

import h5py
import pytest

from stellarcsg import PeriodicRadialSurfaceData, read_surface, write_surface


def test_surface_hdf5_round_trip(tmp_path) -> None:
    path = tmp_path / "geometry.h5"
    source = PeriodicRadialSurfaceData.analytic_torus(
        name="plasma",
        major_radius_cm=500.0,
        minor_radius_cm=100.0,
        n_field_periods=5,
        helical_amplitude_cm=8.0,
    )
    write_surface(path, source)
    loaded = read_surface(path, "plasma", expected_content_id=source.content_id)
    assert loaded.content_id == source.content_id
    assert loaded.n_field_periods == source.n_field_periods
    assert loaded.source_metadata == source.source_metadata


def test_surface_hdf5_detects_modified_payload(tmp_path) -> None:
    path = tmp_path / "geometry.h5"
    source = PeriodicRadialSurfaceData.analytic_torus(
        name="plasma", major_radius_cm=500.0, minor_radius_cm=100.0
    )
    write_surface(path, source)
    with h5py.File(path, "r+") as h5:
        h5["/surfaces/plasma/radius_coefficients"][0, 0] += 1.0
    with pytest.raises(ValueError, match="content hash"):
        read_surface(path, "plasma")


def test_surface_hdf5_refuses_accidental_overwrite(tmp_path) -> None:
    path = tmp_path / "geometry.h5"
    source = PeriodicRadialSurfaceData.analytic_torus(
        name="plasma", major_radius_cm=500.0, minor_radius_cm=100.0
    )
    write_surface(path, source)
    with pytest.raises(FileExistsError):
        write_surface(path, source)
