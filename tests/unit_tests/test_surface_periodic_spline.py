from pathlib import Path

import h5py
import numpy as np
import pytest

import openmc


@pytest.fixture
def coefficient_file(tmp_path):
    pytest.importorskip("stellarcsg")
    from stellarcsg import PeriodicRadialSurfaceData, write_surface

    path = tmp_path / "surfaces.h5"
    data = PeriodicRadialSurfaceData.analytic_torus(
        name="torus", major_radius_cm=500.0, minor_radius_cm=100.0,
        n_axis=8, n_theta=12, n_phi=8)
    write_surface(path, data)
    return path, data


def test_periodic_spline_xml_round_trip(coefficient_file):
    path, data = coefficient_file
    surface = openmc.PeriodicSplineSurface(
        path, "/surfaces/torus", data.content_id, solver="fast",
        name="custom torus")
    element = surface.to_xml_element()
    restored = openmc.Surface.from_xml_element(element)
    assert isinstance(restored, openmc.PeriodicSplineSurface)
    assert restored.data_file == str(path)
    assert restored.dataset == "/surfaces/torus"
    assert restored.content_id == data.content_id
    assert restored.solver == "fast"
    assert restored.is_equal(surface)


def test_periodic_spline_python_evaluation_and_bounds(coefficient_file):
    path, data = coefficient_file
    surface = openmc.PeriodicSplineSurface(
        path, "/surfaces/torus", data.content_id)
    assert abs(surface.evaluate((600.0, 0.0, 0.0))) < 1.0e-10
    assert surface.evaluate((500.0, 0.0, 0.0)) < 0.0
    box = surface.bounding_box('-')
    np.testing.assert_array_less(box.lower_left, (-599.0, -599.0, -99.0))
    np.testing.assert_array_less((599.0, 599.0, 99.0), box.upper_right)


def test_periodic_spline_rejects_invalid_inputs(tmp_path):
    with pytest.raises(ValueError):
        openmc.PeriodicSplineSurface(tmp_path / "x.h5", "relative", "id")
    with pytest.raises(ValueError):
        openmc.PeriodicSplineSurface(tmp_path / "x.h5", "/surface", "id",
                                     solver="unknown")
