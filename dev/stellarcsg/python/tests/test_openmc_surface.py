from __future__ import annotations

import pytest

openmc = pytest.importorskip("openmc")

from stellarcsg.openmc_surface import PeriodicSplineSurface


def test_openmc_surface_writes_experimental_xml() -> None:
    surface = PeriodicSplineSurface(
        data_file="compiled_geometry.h5",
        dataset="/surfaces/plasma",
        content_id="sha256:0123456789abcdef",
        solver="reference",
        surface_id=9123,
        name="plasma boundary",
    )
    element = surface.to_xml_element()
    assert element.get("id") == "9123"
    assert element.get("type") == "periodic-spline"
    assert element.get("data_file") == "compiled_geometry.h5"
    assert element.get("dataset") == "/surfaces/plasma"
    assert element.get("content_id") == "sha256:0123456789abcdef"
    assert element.get("solver") == "reference"
    assert (-surface).surface is surface
