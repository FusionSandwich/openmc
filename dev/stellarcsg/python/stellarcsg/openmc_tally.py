"""Helpers for attaching generated MOAB meshes to OpenMC tally definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np


def make_energy_resolved_mesh_tally(
    *,
    mesh_file: str | Path,
    energy_bounds_eV: Iterable[float],
    name: str = "stellarcsg local spectrum",
    scores: Iterable[str] = ("flux",),
    estimator: str = "tracklength",
):
    """Create an OpenMC tally on a StellarCSG-generated MOAB mesh.

    The OpenMC build must include DAGMC/MOAB support for a MOAB unstructured
    mesh. This helper defines volume scores; boundary angular-current export is
    a separate future contract.
    """
    try:
        import openmc
    except ImportError as error:
        raise RuntimeError("OpenMC Python package is required") from error

    bounds = np.asarray(tuple(energy_bounds_eV), dtype=np.float64)
    if bounds.ndim != 1 or bounds.size < 2 or np.any(np.diff(bounds) <= 0.0):
        raise ValueError("energy_bounds_eV must be a strictly increasing vector")
    mesh = openmc.UnstructuredMesh(str(mesh_file), library="moab")
    tally = openmc.Tally(name=name)
    tally.filters = [openmc.MeshFilter(mesh), openmc.EnergyFilter(bounds)]
    tally.scores = list(scores)
    tally.estimator = estimator
    return tally
