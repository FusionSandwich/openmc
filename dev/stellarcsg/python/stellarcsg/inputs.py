"""CAD-free input adapters for VMEC surfaces and MAKEGRID coil filaments.

The adapters intentionally terminate in the frozen :mod:`stellarcsg` coefficient
and centerline data models.  Neither adapter imports a CAD kernel.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Mapping, Sequence

import h5py
import numpy as np

from .surface import PeriodicRadialSurfaceData

_TWO_PI = 2.0 * np.pi


def _scale_to_cm(units: str) -> float:
    normalized = units.strip().lower()
    scales = {"cm": 1.0, "centimeter": 1.0, "centimetre": 1.0,
              "m": 100.0, "meter": 100.0, "metre": 100.0,
              "mm": 0.1, "millimeter": 0.1, "millimetre": 0.1}
    try:
        return scales[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported geometry unit {units!r}") from exc


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


@contextmanager
def _open_dataset(path: Path):
    """Open classic/netCDF4 VMEC output, falling back to plain HDF5 fixtures."""
    try:
        from netCDF4 import Dataset  # type: ignore
    except ImportError:
        Dataset = None
    if Dataset is not None:
        try:
            dataset = Dataset(path, "r")
        except OSError:
            dataset = None
        if dataset is not None:
            try:
                yield dataset.variables
            finally:
                dataset.close()
            return
    with h5py.File(path, "r") as h5:
        yield h5


def _read(mapping: Mapping[str, object], name: str, *, required: bool = True):
    if name not in mapping:
        if required:
            raise KeyError(f"VMEC dataset is missing required variable {name!r}")
        return None
    value = mapping[name]
    try:
        array = np.asarray(value[...])  # h5py
    except (TypeError, AttributeError, IndexError):
        try:
            array = np.asarray(value[:])  # netCDF4
        except (TypeError, IndexError):
            array = np.asarray(value)
    return array


def _scalar(mapping: Mapping[str, object], name: str, *, required: bool = True):
    value = _read(mapping, name, required=required)
    if value is None:
        return None
    array = np.asarray(value)
    if array.size != 1:
        raise ValueError(f"VMEC variable {name!r} must be scalar")
    return array.reshape(-1)[0].item()


def _radial_mode_slice(array: np.ndarray, mode_count: int, surface_index: int,
                       name: str) -> np.ndarray:
    values = np.asarray(array, dtype=np.float64)
    if values.ndim == 1:
        if values.size != mode_count:
            raise ValueError(f"{name} has {values.size} entries, expected {mode_count}")
        if surface_index not in (-1, 0):
            raise IndexError(f"{name} contains one surface only")
        return values
    if values.ndim != 2:
        raise ValueError(f"{name} must be one- or two-dimensional")
    mode_axes = [axis for axis, size in enumerate(values.shape) if size == mode_count]
    if not mode_axes:
        raise ValueError(
            f"cannot identify the mode axis of {name} with shape {values.shape}"
        )
    # VMEC's conventional layout is (radial surface, Fourier mode).  Prefer
    # the final axis in the rare square-array case, while still accepting
    # transposed fixtures and converted files.
    mode_axis = mode_axes[-1]
    radial_axis = 1 - mode_axis
    radial_count = values.shape[radial_axis]
    index = surface_index if surface_index >= 0 else radial_count + surface_index
    if not 0 <= index < radial_count:
        raise IndexError(
            f"surface_index {surface_index} is outside {name}'s {radial_count} surfaces"
        )
    return values[index, :] if radial_axis == 0 else values[:, index]


def periodic_surface_from_vmec_arrays(
    arrays: Mapping[str, object],
    *,
    name: str = "plasma",
    surface_index: int = -1,
    n_theta: int = 96,
    n_phi: int = 64,
    length_scale_to_cm: float = 100.0,
    source_metadata: Mapping[str, object] | None = None,
) -> PeriodicRadialSurfaceData:
    """Compile a VMEC boundary from an in-memory variable mapping.

    The implementation follows VMEC's Fourier convention

    ``R = sum(rmnc*cos(m*theta - xn*phi) + rmns*sin(...))`` and
    ``Z = sum(zmns*sin(m*theta - xn*phi) + zmnc*cos(...))``.

    VMEC stores ``xn`` with field-period multiplication already applied.  Only
    one field period is sampled before conversion to the native periodic radial
    spline representation.
    """
    if n_theta < 8 or n_phi < 8:
        raise ValueError("VMEC sampling requires at least eight points per angle")
    if not np.isfinite(length_scale_to_cm) or length_scale_to_cm <= 0.0:
        raise ValueError("length_scale_to_cm must be finite and positive")

    nfp = int(_scalar(arrays, "nfp"))
    if nfp <= 0:
        raise ValueError("VMEC nfp must be positive")
    xm = np.asarray(_read(arrays, "xm"), dtype=np.float64).reshape(-1)
    xn = np.asarray(_read(arrays, "xn"), dtype=np.float64).reshape(-1)
    if xm.size == 0 or xm.shape != xn.shape:
        raise ValueError("VMEC xm and xn must be equal, non-empty mode vectors")

    rmnc = _radial_mode_slice(_read(arrays, "rmnc"), xm.size,
                              surface_index, "rmnc")
    zmns = _radial_mode_slice(_read(arrays, "zmns"), xm.size,
                              surface_index, "zmns")
    rmns_raw = _read(arrays, "rmns", required=False)
    zmnc_raw = _read(arrays, "zmnc", required=False)
    rmns = (np.zeros_like(rmnc) if rmns_raw is None else
            _radial_mode_slice(rmns_raw, xm.size, surface_index, "rmns"))
    zmnc = (np.zeros_like(zmns) if zmnc_raw is None else
            _radial_mode_slice(zmnc_raw, xm.size, surface_index, "zmnc"))

    theta = _TWO_PI * np.arange(n_theta, dtype=np.float64) / n_theta
    field_period = _TWO_PI / nfp
    phi = field_period * np.arange(n_phi, dtype=np.float64) / n_phi
    phase = (xm[:, None, None] * theta[None, :, None]
             - xn[:, None, None] * phi[None, None, :])
    cosine = np.cos(phase)
    sine = np.sin(phase)
    R = np.einsum("m,mij->ij", rmnc, cosine)
    R += np.einsum("m,mij->ij", rmns, sine)
    Z = np.einsum("m,mij->ij", zmns, sine)
    Z += np.einsum("m,mij->ij", zmnc, cosine)
    if np.any(R <= 0.0) or not np.all(np.isfinite(R)) or not np.all(np.isfinite(Z)):
        raise ValueError("VMEC surface evaluates to invalid cylindrical coordinates")

    # The m=0 Fourier terms give a parameterization-independent axis candidate
    # for the radial representation.  If a model omits m=0 terms, the generic
    # surface-grid compiler's inferred axis is used instead.
    m0 = np.isclose(xm, 0.0, rtol=0.0, atol=1.0e-12)
    axis_r = axis_z = None
    if np.any(m0):
        phase0 = -xn[m0, None] * phi[None, :]
        axis_r = (np.einsum("m,mj->j", rmnc[m0], np.cos(phase0))
                  + np.einsum("m,mj->j", rmns[m0], np.sin(phase0)))
        axis_z = (np.einsum("m,mj->j", zmns[m0], np.sin(phase0))
                  + np.einsum("m,mj->j", zmnc[m0], np.cos(phase0)))

    scale = float(length_scale_to_cm)
    xyz = np.stack((R * np.cos(phi)[None, :],
                    R * np.sin(phi)[None, :], Z), axis=-1) * scale
    metadata = dict(source_metadata or {})
    metadata.update({
        "kind": "vmec_fourier_surface",
        "surface_index": int(surface_index),
        "n_field_periods": nfp,
        "n_modes": int(xm.size),
        "sample_shape": [int(n_theta), int(n_phi)],
        "length_scale_to_cm": scale,
        "asymmetric_terms_present": bool(rmns_raw is not None or zmnc_raw is not None),
    })
    return PeriodicRadialSurfaceData.from_surface_grid(
        name=name,
        xyz_cm=xyz,
        phi=phi,
        n_field_periods=nfp,
        axis_r_cm=None if axis_r is None else axis_r * scale,
        axis_z_cm=None if axis_z is None else axis_z * scale,
        n_theta_coefficients=n_theta,
        source_metadata=metadata,
    )


def read_vmec_surface(
    path: str | Path,
    *,
    name: str = "plasma",
    surface_index: int = -1,
    n_theta: int = 96,
    n_phi: int = 64,
    units: str = "m",
) -> PeriodicRadialSurfaceData:
    """Read a VMEC ``wout`` file and freeze one surface for native CSG."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    scale = _scale_to_cm(units)
    with _open_dataset(source) as variables:
        return periodic_surface_from_vmec_arrays(
            variables,
            name=name,
            surface_index=surface_index,
            n_theta=n_theta,
            n_phi=n_phi,
            length_scale_to_cm=scale,
            source_metadata={"source_path": source.name,
                             "source_sha256": _file_sha256(source)},
        )


@dataclass(frozen=True)
class CoilCenterline:
    """One closed, CAD-free magnet filament in transport centimetres."""

    name: str
    xyz_cm: np.ndarray
    current_a: float
    source_metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("coil name cannot be empty")
        xyz = np.asarray(self.xyz_cm, dtype=np.float64)
        if xyz.ndim != 2 or xyz.shape[1] != 3 or xyz.shape[0] < 4:
            raise ValueError("coil centerline must have shape (n>=4, 3)")
        if not np.all(np.isfinite(xyz)):
            raise ValueError("coil coordinates must be finite")
        if np.linalg.norm(xyz[0] - xyz[-1]) <= 1.0e-10:
            xyz = xyz[:-1]
        if xyz.shape[0] < 4:
            raise ValueError("coil has too few unique points")
        segment_lengths = np.linalg.norm(np.roll(xyz, -1, axis=0) - xyz, axis=1)
        if np.any(segment_lengths <= 1.0e-10):
            raise ValueError("coil contains duplicate adjacent points")
        if not np.isfinite(self.current_a):
            raise ValueError("coil current must be finite")
        object.__setattr__(self, "xyz_cm", np.ascontiguousarray(xyz))

    @property
    def length_cm(self) -> float:
        return float(np.sum(np.linalg.norm(
            np.roll(self.xyz_cm, -1, axis=0) - self.xyz_cm, axis=1)))

    @property
    def content_id(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.name.encode())
        digest.update(np.asarray([self.current_a], dtype="<f8").tobytes())
        digest.update(np.asarray(self.xyz_cm, dtype="<f8", order="C").tobytes())
        return "sha256:" + digest.hexdigest()


def read_makegrid_coils(
    path: str | Path,
    *,
    units: str = "m",
    current_zero_tolerance: float = 0.0,
) -> list[CoilCenterline]:
    """Read MAKEGRID/FOCUS filament text without a CAD dependency.

    Data lines are interpreted as ``x y z current [name ...]``.  A line whose
    current is zero terminates the active filament; ``end`` terminates the set.
    Header and comment lines are retained in source metadata but otherwise
    ignored.  Every emitted filament is explicitly closed in the data contract.
    """
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    scale = _scale_to_cm(units)
    source_hash = _file_sha256(source)
    coils: list[CoilCenterline] = []
    points: list[list[float]] = []
    current: float | None = None
    label = ""
    header: list[str] = []

    def finish(line_number: int) -> None:
        nonlocal points, current, label
        if not points:
            return
        if current is None:
            raise ValueError(f"coil ending at line {line_number} has no nonzero current")
        name = label or f"coil_{len(coils):04d}"
        coils.append(CoilCenterline(
            name=name,
            xyz_cm=np.asarray(points, dtype=np.float64) * scale,
            current_a=current,
            source_metadata={"kind": "makegrid", "source_path": source.name,
                             "source_sha256": source_hash,
                             "termination_line": line_number},
        ))
        points = []
        current = None
        label = ""

    for line_number, raw_line in enumerate(source.read_text().splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith(("#", "!")):
            continue
        tokens = stripped.replace(",", " ").split()
        if tokens[0].lower() == "end":
            finish(line_number)
            break
        if len(tokens) < 4:
            header.append(stripped)
            continue
        try:
            x, y, z, line_current = map(float, tokens[:4])
        except ValueError:
            header.append(stripped)
            continue
        if abs(line_current) <= current_zero_tolerance:
            finish(line_number)
            continue
        if current is None:
            current = line_current
        elif not np.isclose(line_current, current, rtol=1.0e-10, atol=1.0e-12):
            raise ValueError(
                f"coil current changes from {current} to {line_current} at line {line_number}"
            )
        points.append([x, y, z])
        if len(tokens) > 4:
            label = " ".join(tokens[4:])
    else:
        finish(line_number if 'line_number' in locals() else 0)

    if not coils:
        raise ValueError(f"no closed coil filaments were found in {source}")
    # Keep the shared header on each record without mutating the frozen mapping.
    if header:
        coils = [CoilCenterline(c.name, c.xyz_cm, c.current_a,
                                {**dict(c.source_metadata or {}), "header": header})
                 for c in coils]
    return coils


def write_coil_collection_hdf5(path: str | Path, coils: Sequence[CoilCenterline]) -> None:
    """Persist frozen centerlines for replay by the swept-magnet stage."""
    if not coils:
        raise ValueError("at least one coil is required")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(target, "w") as h5:
        h5.attrs["filetype"] = "stellarcsg-coils"
        h5.attrs["schema_major"] = 1
        h5.attrs["schema_minor"] = 0
        root = h5.create_group("coils")
        for index, coil in enumerate(coils):
            group = root.create_group(f"{index:04d}")
            group.attrs["name"] = coil.name
            group.attrs["content_id"] = coil.content_id
            group.attrs["current_a"] = coil.current_a
            group.attrs["units"] = "cm"
            group.create_dataset("xyz_cm", data=coil.xyz_cm)
