"""Versioned HDF5 interchange for periodic spline surfaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import h5py
import numpy as np

from .surface import PeriodicRadialSurfaceData

_SCHEMA_NAME = "stellarcsg-periodic-spline"
_SCHEMA_VERSION = (1, 0)


def _group_path(name: str) -> str:
    clean = name.strip("/")
    if not clean:
        raise ValueError("surface name/path cannot be empty")
    return f"/surfaces/{clean}"


def write_surface(
    filename: str | Path,
    surface: PeriodicRadialSurfaceData,
    *,
    overwrite: bool = False,
) -> None:
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "a") as h5:
        h5.attrs["schema_name"] = _SCHEMA_NAME
        h5.attrs["schema_version"] = np.asarray(_SCHEMA_VERSION, dtype=np.int32)
        group_path = _group_path(surface.name)
        if group_path in h5:
            if not overwrite:
                raise FileExistsError(f"surface group already exists: {group_path}")
            del h5[group_path]
        group = h5.create_group(group_path)
        group.create_dataset("schema_version", data=np.asarray(_SCHEMA_VERSION, dtype=np.int32))
        group.attrs["surface_type"] = "periodic-radial-bicubic"
        group.attrs["units"] = surface.units
        group.attrs["content_id"] = surface.content_id
        group.attrs["canonical_metadata_json"] = surface.canonical_metadata_json()
        group.attrs["n_field_periods"] = surface.n_field_periods
        group.attrs["characteristic_length"] = surface.characteristic_length
        group.attrs["coordinate_singularity_tolerance"] = (
            surface.coordinate_singularity_tolerance
        )
        group.attrs["source_metadata_json"] = json.dumps(
            dict(surface.source_metadata or {}), sort_keys=True, separators=(",", ":")
        )
        group.create_dataset(
            "axis_r_coefficients", data=surface.axis_r_coefficients, dtype="<f8"
        )
        group.create_dataset(
            "axis_z_coefficients", data=surface.axis_z_coefficients, dtype="<f8"
        )
        group.create_dataset(
            "radius_coefficients", data=surface.radius_coefficients, dtype="<f8"
        )


def write_surface_collection(
    filename: str | Path,
    surfaces: Iterable[PeriodicRadialSurfaceData],
    *,
    overwrite_file: bool = True,
) -> None:
    path = Path(filename)
    if overwrite_file and path.exists():
        path.unlink()
    for surface in surfaces:
        write_surface(path, surface, overwrite=False)


def read_surface(
    filename: str | Path,
    name: str,
    *,
    expected_content_id: str | None = None,
) -> PeriodicRadialSurfaceData:
    with h5py.File(filename, "r") as h5:
        group_path = name if name.startswith("/") else _group_path(name)
        group = h5[group_path]
        schema = tuple(int(value) for value in group["schema_version"][...])
        if schema[0] != _SCHEMA_VERSION[0]:
            raise ValueError(f"unsupported schema major version: {schema}")
        surface_type = group.attrs["surface_type"]
        if isinstance(surface_type, bytes):
            surface_type = surface_type.decode()
        if surface_type != "periodic-radial-bicubic":
            raise ValueError(f"unsupported surface type: {surface_type}")
        metadata_raw = group.attrs.get("source_metadata_json", "{}")
        if isinstance(metadata_raw, bytes):
            metadata_raw = metadata_raw.decode()
        data = PeriodicRadialSurfaceData(
            name=group_path.rsplit("/", 1)[-1],
            n_field_periods=int(group.attrs["n_field_periods"]),
            axis_r_coefficients=group["axis_r_coefficients"][...],
            axis_z_coefficients=group["axis_z_coefficients"][...],
            radius_coefficients=group["radius_coefficients"][...],
            units=str(group.attrs["units"]),
            characteristic_length=float(group.attrs["characteristic_length"]),
            coordinate_singularity_tolerance=float(
                group.attrs["coordinate_singularity_tolerance"]
            ),
            source_metadata=json.loads(str(metadata_raw)),
            content_id=str(group.attrs["content_id"]),
        )
    if expected_content_id is not None and data.content_id != expected_content_id:
        raise ValueError(
            f"content ID mismatch: expected {expected_content_id}, got {data.content_id}"
        )
    if data.compute_content_id() != data.content_id:
        raise ValueError("surface coefficient content hash does not verify")
    return data
