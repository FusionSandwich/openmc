"""CAD-free layer-conformal tally meshes generated from CSG surface data."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Sequence

import h5py
import numpy as np

from .surface import PeriodicRadialSurfaceData


@dataclass(frozen=True)
class HexMesh:
    vertices_cm: np.ndarray
    connectivity: np.ndarray
    shell_index: np.ndarray
    radial_index: np.ndarray
    theta_index: np.ndarray
    phi_index: np.ndarray
    surface_names: tuple[str, ...]
    n_radial_per_shell: tuple[int, ...]
    theta_bins: int
    phi_bins: int
    toroidal_extent_rad: float

    def __post_init__(self) -> None:
        vertices = np.asarray(self.vertices_cm, dtype=np.float64)
        connectivity = np.asarray(self.connectivity, dtype=np.int64)
        if vertices.ndim != 2 or vertices.shape[1] != 3:
            raise ValueError("vertices_cm must have shape (n, 3)")
        if connectivity.ndim != 2 or connectivity.shape[1] != 8:
            raise ValueError("connectivity must have shape (n, 8)")
        if np.any(connectivity < 0) or np.any(connectivity >= vertices.shape[0]):
            raise ValueError("connectivity references invalid vertices")
        if not np.all(np.isfinite(vertices)):
            raise ValueError("mesh vertices must be finite")
        object.__setattr__(self, "vertices_cm", np.ascontiguousarray(vertices))
        object.__setattr__(self, "connectivity", np.ascontiguousarray(connectivity))

    @property
    def n_elements(self) -> int:
        return int(self.connectivity.shape[0])

    def approximate_element_volumes_cm3(self) -> np.ndarray:
        p = self.vertices_cm[self.connectivity]
        tetrahedra = (
            (0, 1, 2, 6),
            (0, 2, 3, 6),
            (0, 3, 7, 6),
            (0, 7, 4, 6),
            (0, 4, 5, 6),
            (0, 5, 1, 6),
        )
        volume = np.zeros(self.n_elements, dtype=np.float64)
        for a, b, c, d in tetrahedra:
            signed = np.einsum(
                "ij,ij->i",
                p[:, b] - p[:, a],
                np.cross(p[:, c] - p[:, a], p[:, d] - p[:, a]),
            ) / 6.0
            volume += np.abs(signed)
        return volume


def build_layer_mesh(
    surfaces: Sequence[PeriodicRadialSurfaceData],
    *,
    radial_bins_per_shell: int | Sequence[int] = 1,
    theta_bins: int = 48,
    phi_bins: int = 48,
    toroidal_extent: str | float = "full",
) -> HexMesh:
    """Build a conformal hexahedral tally mesh between nested radial surfaces."""
    if len(surfaces) < 2:
        raise ValueError("at least two nested surfaces are required")
    reference = surfaces[0]
    for surface in surfaces[1:]:
        if surface.n_field_periods != reference.n_field_periods:
            raise ValueError("all surfaces must have the same field-period count")
        if not np.array_equal(surface.axis_r_coefficients, reference.axis_r_coefficients):
            raise ValueError("first mesh version requires shared axis R coefficients")
        if not np.array_equal(surface.axis_z_coefficients, reference.axis_z_coefficients):
            raise ValueError("first mesh version requires shared axis Z coefficients")
    if theta_bins < 4 or phi_bins < 1:
        raise ValueError("theta_bins must be >= 4 and phi_bins must be positive")
    if isinstance(radial_bins_per_shell, int):
        radial_bins = [radial_bins_per_shell] * (len(surfaces) - 1)
    else:
        radial_bins = [int(value) for value in radial_bins_per_shell]
    if len(radial_bins) != len(surfaces) - 1 or any(value < 1 for value in radial_bins):
        raise ValueError("radial bin count must be positive for every shell")
    if toroidal_extent == "full":
        extent = 2.0 * np.pi
    elif toroidal_extent == "field-period":
        extent = 2.0 * np.pi / reference.n_field_periods
    else:
        extent = float(toroidal_extent)
        if not 0.0 < extent <= 2.0 * np.pi:
            raise ValueError("toroidal_extent must be in (0, 2pi]")

    theta = 2.0 * np.pi * np.arange(theta_bins) / theta_bins
    phi = np.linspace(0.0, extent, phi_bins + 1)
    theta_grid, phi_grid = np.meshgrid(theta, phi, indexing="ij")
    axis_r, axis_z, _, _ = reference.axis(phi_grid)
    boundary_radius = [surface.radius(theta_grid, phi_grid)[0] for surface in surfaces]
    for inner, outer in zip(boundary_radius[:-1], boundary_radius[1:]):
        if np.min(outer - inner) <= 0.0:
            raise ValueError("surfaces are not strictly nested on the mesh grid")

    radial_layers: list[np.ndarray] = []
    layer_shell: list[int] = []
    layer_radial: list[int] = []
    for shell, n_radial in enumerate(radial_bins):
        for local in range(n_radial):
            fraction = local / n_radial
            radial_layers.append(
                (1.0 - fraction) * boundary_radius[shell]
                + fraction * boundary_radius[shell + 1]
            )
            layer_shell.append(shell)
            layer_radial.append(local)
    radial_layers.append(boundary_radius[-1])
    radius = np.stack(radial_layers, axis=0)
    R = axis_r[None, ...] + radius * np.cos(theta_grid)[None, ...]
    Z = axis_z[None, ...] + radius * np.sin(theta_grid)[None, ...]
    X = R * np.cos(phi_grid)[None, ...]
    Y = R * np.sin(phi_grid)[None, ...]
    vertices = np.stack((X, Y, Z), axis=-1).reshape(-1, 3)

    n_radial_nodes = radius.shape[0]
    n_phi_nodes = phi_bins + 1

    def node(ir: int, itheta: int, iphi: int) -> int:
        return (ir * theta_bins + (itheta % theta_bins)) * n_phi_nodes + iphi

    cells: list[list[int]] = []
    shell_index: list[int] = []
    radial_index: list[int] = []
    theta_index: list[int] = []
    phi_index: list[int] = []
    radial_interval = 0
    for shell, n_radial in enumerate(radial_bins):
        for local in range(n_radial):
            for itheta in range(theta_bins):
                next_theta = (itheta + 1) % theta_bins
                for iphi in range(phi_bins):
                    cells.append(
                        [
                            node(radial_interval, itheta, iphi),
                            node(radial_interval + 1, itheta, iphi),
                            node(radial_interval + 1, next_theta, iphi),
                            node(radial_interval, next_theta, iphi),
                            node(radial_interval, itheta, iphi + 1),
                            node(radial_interval + 1, itheta, iphi + 1),
                            node(radial_interval + 1, next_theta, iphi + 1),
                            node(radial_interval, next_theta, iphi + 1),
                        ]
                    )
                    shell_index.append(shell)
                    radial_index.append(local)
                    theta_index.append(itheta)
                    phi_index.append(iphi)
            radial_interval += 1
    if radial_interval + 1 != n_radial_nodes:
        raise RuntimeError("internal radial mesh indexing failure")

    mesh = HexMesh(
        vertices_cm=vertices,
        connectivity=np.asarray(cells, dtype=np.int64),
        shell_index=np.asarray(shell_index, dtype=np.int32),
        radial_index=np.asarray(radial_index, dtype=np.int32),
        theta_index=np.asarray(theta_index, dtype=np.int32),
        phi_index=np.asarray(phi_index, dtype=np.int32),
        surface_names=tuple(surface.name for surface in surfaces),
        n_radial_per_shell=tuple(radial_bins),
        theta_bins=theta_bins,
        phi_bins=phi_bins,
        toroidal_extent_rad=extent,
    )
    volumes = mesh.approximate_element_volumes_cm3()
    if np.any(~np.isfinite(volumes)) or np.any(volumes <= 0.0):
        raise ValueError("mesh contains zero, negative, or non-finite element volumes")
    return mesh


def write_mesh_hdf5(filename: str | Path, mesh: HexMesh) -> None:
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as h5:
        h5.attrs["schema_name"] = "stellarcsg-tally-mesh"
        h5.attrs["schema_version"] = np.asarray((1, 0), dtype=np.int32)
        h5.attrs["length_units"] = "cm"
        h5.attrs["surface_names_json"] = json.dumps(mesh.surface_names)
        h5.attrs["n_radial_per_shell_json"] = json.dumps(mesh.n_radial_per_shell)
        h5.attrs["theta_bins"] = mesh.theta_bins
        h5.attrs["phi_bins"] = mesh.phi_bins
        h5.attrs["toroidal_extent_rad"] = mesh.toroidal_extent_rad
        h5.create_dataset("vertices_cm", data=mesh.vertices_cm, dtype="<f8")
        h5.create_dataset("connectivity", data=mesh.connectivity, dtype="<i8")
        metadata = h5.create_group("element_metadata")
        metadata.create_dataset("shell_index", data=mesh.shell_index)
        metadata.create_dataset("radial_index", data=mesh.radial_index)
        metadata.create_dataset("theta_index", data=mesh.theta_index)
        metadata.create_dataset("phi_index", data=mesh.phi_index)
        metadata.create_dataset(
            "approximate_volume_cm3", data=mesh.approximate_element_volumes_cm3()
        )


def write_legacy_vtk(filename: str | Path, mesh: HexMesh) -> None:
    """Write an ASCII VTK unstructured grid for ParaView inspection."""
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("# vtk DataFile Version 3.0\n")
        stream.write("StellarCSG tally mesh\n")
        stream.write("ASCII\n")
        stream.write("DATASET UNSTRUCTURED_GRID\n")
        stream.write(f"POINTS {mesh.vertices_cm.shape[0]} double\n")
        np.savetxt(stream, mesh.vertices_cm, fmt="%.17g")
        stream.write(f"CELLS {mesh.n_elements} {mesh.n_elements * 9}\n")
        cells = np.column_stack(
            (np.full(mesh.n_elements, 8, dtype=np.int64), mesh.connectivity)
        )
        np.savetxt(stream, cells, fmt="%d")
        stream.write(f"CELL_TYPES {mesh.n_elements}\n")
        np.savetxt(stream, np.full(mesh.n_elements, 12, dtype=np.int32), fmt="%d")
        stream.write(f"CELL_DATA {mesh.n_elements}\n")
        for name, values in (
            ("shell_index", mesh.shell_index),
            ("radial_index", mesh.radial_index),
            ("theta_index", mesh.theta_index),
            ("phi_index", mesh.phi_index),
        ):
            stream.write(f"SCALARS {name} int 1\n")
            stream.write("LOOKUP_TABLE default\n")
            np.savetxt(stream, values, fmt="%d")


def write_moab_h5m(filename: str | Path, mesh: HexMesh) -> None:
    """Write an OpenMC-compatible MOAB H5M tally mesh when PyMOAB is installed.

    Install MOAB/PyMOAB from conda-forge. This function is optional so that the
    mathematical and VTK/HDF5 tests remain runnable on systems without MOAB.
    """
    try:
        from pymoab import core, types
    except ImportError as error:
        raise RuntimeError(
            "MOAB export requires pymoab; install it from conda-forge"
        ) from error

    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    database = core.Core()
    vertex_handles = np.asarray(
        database.create_vertices(mesh.vertices_cm.reshape(-1)), dtype=np.uint64
    )
    element_handles = np.empty(mesh.n_elements, dtype=np.uint64)
    for index, connectivity in enumerate(mesh.connectivity):
        element_handles[index] = database.create_element(
            types.MBHEX, vertex_handles[connectivity]
        )
    for name, values in (
        ("SHELL_INDEX", mesh.shell_index),
        ("RADIAL_INDEX", mesh.radial_index),
        ("THETA_INDEX", mesh.theta_index),
        ("PHI_INDEX", mesh.phi_index),
    ):
        tag = database.tag_get_handle(
            name,
            1,
            types.MB_TYPE_INTEGER,
            types.MB_TAG_DENSE | types.MB_TAG_CREAT,
        )
        database.tag_set_data(tag, element_handles, np.asarray(values, dtype=np.int32))
    database.write_file(str(path))
