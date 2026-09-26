"""Local volume tallies using standard OpenMC mesh and cell filters."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np


def make_energy_resolved_mesh_tally(
    *,
    energy_bounds_eV: Iterable[float],
    mesh_file: str | Path | None = None,
    mesh=None,
    cells=None,
    name: str = "stellarcsg local spectrum",
    scores: Iterable[str] = ("flux",),
    estimator: str = "tracklength",
):
    """Create a local energy-resolved volume tally with ordinary OpenMC filters.

    Parameters
    ----------
    energy_bounds_eV : iterable of float
        Finite, nonnegative, strictly increasing energy boundaries in eV.
    mesh : openmc.MeshBase, optional
        Existing regular, rectilinear, cylindrical, spherical or unstructured
        tally mesh. Specify exactly one of ``mesh`` and ``mesh_file``.
        Structured meshes need no MOAB/DAGMC support.
    mesh_file : path-like, optional
        Backward-compatible path to a MOAB unstructured mesh. Requires an
        OpenMC build with MOAB support.
    cells : iterable of openmc.Cell or int, optional
        Restrict each mesh bin to these CSG cells. An intersection can occupy
        only part of a mesh element; its volume is not the full mesh volume.
    name : str, optional
        Tally name.
    scores : iterable of str, optional
        Volume scores such as flux, absorption or damage-energy.
    estimator : str, optional
        Standard OpenMC tally estimator, subject to score/filter compatibility.

    Returns
    -------
    openmc.Tally
        Ordinary tally, usable with StatePoint, slicing and DataFrame APIs.
        Scores retain OpenMC's per-source normalization. This function does not
        divide by volume or source rate. Use the standard SurfaceFilter or
        MeshSurfaceFilter API separately for currents.
    """
    try:
        import openmc
    except ImportError as error:
        raise RuntimeError("OpenMC Python package is required") from error

    bounds = np.asarray(tuple(energy_bounds_eV), dtype=np.float64)
    if (bounds.ndim != 1 or bounds.size < 2 or not np.isfinite(bounds).all()
            or bounds[0] < 0 or np.any(np.diff(bounds) <= 0.0)):
        raise ValueError("energy_bounds_eV must be finite, nonnegative and strictly increasing")
    if (mesh is None) == (mesh_file is None):
        raise ValueError("specify exactly one of mesh and mesh_file")
    if mesh is None:
        mesh = openmc.UnstructuredMesh(str(mesh_file), library="moab")
    elif not isinstance(mesh, openmc.MeshBase):
        raise TypeError("mesh must be an OpenMC MeshBase")
    tally = openmc.Tally(name=name)
    tally.filters = [openmc.MeshFilter(mesh), openmc.EnergyFilter(bounds)]
    if cells is not None:
        cells = list(cells)
        if not cells:
            raise ValueError("cells cannot be empty")
        tally.filters.append(openmc.CellFilter(cells))
    tally.scores = list(scores)
    tally.estimator = estimator
    return tally
