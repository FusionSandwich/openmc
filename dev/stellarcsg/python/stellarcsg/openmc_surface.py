"""Opt-in Python surface wrapper for the experimental OpenMC C++ adapter."""

from __future__ import annotations

import math
from pathlib import Path

import lxml.etree as ET

try:
    import openmc
except ImportError as error:  # pragma: no cover - exercised only without OpenMC
    raise ImportError(
        "stellarcsg.openmc_surface requires the Python package from the OpenMC source tree"
    ) from error


class PeriodicSplineSurface(openmc.Surface):
    """Reference a frozen periodic-spline surface in a StellarCSG HDF5 file.

    The corresponding OpenMC executable must be built with
    ``dev/stellarcsg/openmc_adapter/enable.cmake``. An ordinary OpenMC binary
    will reject the ``periodic-spline`` surface type.
    """

    _type = "periodic-spline"
    _coeff_keys: tuple[str, ...] = ()

    def __init__(
        self,
        *,
        data_file: str | Path,
        dataset: str,
        content_id: str,
        solver: str = "reference",
        surface_id: int | None = None,
        boundary_type: str = "transmission",
        albedo: float = 1.0,
        name: str = "",
    ) -> None:
        super().__init__(
            surface_id=surface_id,
            boundary_type=boundary_type,
            albedo=albedo,
            name=name,
        )
        if not dataset.startswith("/"):
            raise ValueError("dataset must be an absolute HDF5 group path")
        if not content_id:
            raise ValueError("content_id cannot be empty")
        if solver != "reference":
            raise ValueError("this milestone only supports solver='reference'")
        self.data_file = str(data_file)
        self.dataset = dataset
        self.content_id = content_id
        self.solver = solver

    def _get_base_coeffs(self) -> tuple[float, ...]:
        return ()

    def is_equal(self, other: object) -> bool:
        return (
            isinstance(other, PeriodicSplineSurface)
            and self.data_file == other.data_file
            and self.dataset == other.dataset
            and self.content_id == other.content_id
            and self.solver == other.solver
        )

    def evaluate(self, point):
        from .io import read_surface

        surface = read_surface(
            self.data_file, self.dataset, expected_content_id=self.content_id
        )
        return float(surface.evaluate(point))

    def translate(self, vector, inplace=False):
        raise NotImplementedError(
            "translate the source coefficient data before creating this surface"
        )

    def rotate(self, rotation, pivot=(0.0, 0.0, 0.0), order="xyz", inplace=False):
        raise NotImplementedError(
            "rotate the source coefficient data before creating this surface"
        )

    def to_xml_element(self):
        element = ET.Element("surface")
        element.set("id", str(self.id))
        if self.name:
            element.set("name", self.name)
        element.set("type", self.type)
        if self.boundary_type != "transmission":
            element.set("boundary", self.boundary_type)
            if self.boundary_type in {"reflective", "periodic", "white"} and not math.isclose(
                self.albedo, 1.0
            ):
                element.set("albedo", str(self.albedo))
        element.set("data_file", self.data_file)
        element.set("dataset", self.dataset)
        element.set("content_id", self.content_id)
        element.set("solver", self.solver)
        return element
