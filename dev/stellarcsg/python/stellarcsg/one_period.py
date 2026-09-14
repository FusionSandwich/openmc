"""Explicit one-field-period model preparation for finite stellarator coils.

This module prepares immutable geometry and identity metadata. Its XML export
uses native swept-spline surface records, but remains a diagnostic clipped
sector model rather than a transport qualification.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Literal
import xml.etree.ElementTree as ET

import h5py
import numpy as np

from .coil import read_makegrid_filaments
from .io import write_surface
from .surface import PeriodicRadialSurfaceData
from .vmec import VmecBoundary


SymmetryPolicy = Literal["reject", "record-approximation"]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _decode(value: Any) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def _rotate_z(points: np.ndarray, angle: float) -> np.ndarray:
    result = np.array(points, dtype=np.float64, copy=True)
    cosine, sine = math.cos(angle), math.sin(angle)
    result[..., 0] = cosine * points[..., 0] - sine * points[..., 1]
    result[..., 1] = sine * points[..., 0] + cosine * points[..., 1]
    return result


@dataclass(frozen=True)
class CoilMember:
    """One complete finite coil retained for a sector-clipped material cell."""

    coil_id: int
    dataset: str
    content_id: str
    section_major_radius_cm: float
    section_minor_radius_cm: float
    material_id: str
    cell_id: str
    crosses_lower_seam_candidate: bool
    crosses_upper_seam_candidate: bool
    retained_span_count: int
    diagnostic_source_anchor_cm: tuple[float, float, float]

    def as_dict(self) -> dict[str, object]:
        return {
            "coil_id": self.coil_id,
            "dataset": self.dataset,
            "content_id": self.content_id,
            "section": {
                "shape_assumption": "swept elliptical section from HDF5 coefficients",
                "major_radius_cm": self.section_major_radius_cm,
                "minor_radius_cm": self.section_minor_radius_cm,
            },
            "member_identity": {"cell_id": self.cell_id, "material_id": self.material_id},
            "sector_neighbor_geometry": {
                "complete_curve_retained": True,
                "crosses_lower_seam_candidate": self.crosses_lower_seam_candidate,
                "crosses_upper_seam_candidate": self.crosses_upper_seam_candidate,
                "retained_span_count": self.retained_span_count,
            },
            "diagnostic_source_anchor_cm": list(self.diagnostic_source_anchor_cm),
        }


@dataclass(frozen=True)
class OnePeriodModelPlan:
    """Serializable input-to-model preparation receipt for one field period."""

    plasma: PeriodicRadialSurfaceData
    members: tuple[CoilMember, ...]
    n_field_periods: int
    sector_degrees: tuple[float, float]
    source_hashes: dict[str, str]
    seam_diagnostic: dict[str, object]
    symmetry_policy: SymmetryPolicy
    approximation_record: dict[str, object] | None
    swept_coils_file: Path

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": "stellarcsg.one-period-plan/v1",
            "status": "PREPARED_NOT_TRANSPORT_QUALIFIED",
            "units": "cm",
            "n_field_periods": self.n_field_periods,
            "sector_degrees": list(self.sector_degrees),
            "sector_region": ["x >= 0", "y >= 0"],
            "plasma": {
                "surface_dataset": "/surfaces/plasma_boundary",
                "content_id": self.plasma.content_id,
                "representation": "periodic-radial-bicubic",
                "source_units": "VMEC metres converted once to centimetres",
            },
            "finite_coil_members": [member.as_dict() for member in self.members],
            "per_member_cell_blueprint": [
                {
                    "cell_id": member.cell_id,
                    "material_id": member.material_id,
                    "surface_dataset": member.dataset,
                    "surface_content_id": member.content_id,
                    "region": ["inside this complete finite swept coil", "x >= 0", "y >= 0"],
                    "surface_type": "swept-spline",
                    "status": "NATIVE_INDIVIDUAL_SWEPT_SURFACE_DIAGNOSTIC",
                }
                for member in self.members
            ],
            "source_hashes": self.source_hashes,
            "seam_diagnostic": self.seam_diagnostic,
            "symmetry_policy": self.symmetry_policy,
            "approximation_record": self.approximation_record,
            "transport_limitations": [
                "This is a preparation plan, not a qualified transport model.",
                "Finite coil curves are retained whole and their future material cells must be intersected with the sector halfspaces.",
                "The native individual swept-spline records retain the supplied coil payload directly.",
                "The plasma fit uses the requested source grid; its input-to-model geometric fidelity is NOT_MEASURED.",
                "No periodic boundary condition is emitted. A seam mismatch is retained as an approximation record, never corrected by forced copies.",
                "The clipped diagnostic XML is not a qualified transport model: material physics, overlap clearance, particle navigation, and tally results require separate acceptance.",
            ],
        }

    def export(self, directory: str | Path) -> dict[str, Path]:
        """Write plasma coefficients and a non-executable model-plan receipt."""
        output = Path(directory)
        output.mkdir(parents=True, exist_ok=True)
        surface_file = output / "plasma_boundary.h5"
        plan_file = output / "one_period_model.json"
        if surface_file.exists() or plan_file.exists():
            raise FileExistsError("one-period export refuses to overwrite an existing receipt")
        write_surface(surface_file, self.plasma)
        payload = self.as_dict()
        payload["plasma"]["data_file"] = str(surface_file.resolve())
        payload["swept_coils_file"] = str(self.swept_coils_file.resolve())
        plan_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {"plasma_surface": surface_file, "model_plan": plan_file}

    def export_openmc_diagnostic(self, directory: str | Path, *, diagnostic_clipped: bool) -> dict[str, Path]:
        """Export a nonperiodic diagnostic model using native swept surfaces."""
        if not diagnostic_clipped:
            raise ValueError("REJECT_DIAGNOSTIC_OPT_IN: pass diagnostic_clipped=True; periodic production export is unavailable")
        output = Path(directory)
        output.mkdir(parents=True, exist_ok=True)
        names = ("plasma_boundary.h5", "materials.xml", "geometry.xml", "settings.xml", "tallies.xml", "diagnostic_receipt.json")
        if any((output / name).exists() for name in names):
            raise FileExistsError("diagnostic export refuses to overwrite existing files")
        surface_file = output / "plasma_boundary.h5"
        write_surface(surface_file, self.plasma)
        plasma_path, payload_path = surface_file.resolve(), self.swept_coils_file.resolve()
        _write_xml(output / "materials.xml", _materials_xml(self.members))
        _write_xml(output / "geometry.xml", _geometry_xml(self.members, plasma_path, payload_path, self.plasma.content_id))
        _write_xml(output / "settings.xml", _settings_xml(self.members))
        _write_xml(output / "tallies.xml", _tallies_xml(self.members))
        receipt = {"status": "DIAGNOSTIC_CLIPPED_NATIVE_SWEPT_MODEL_NOT_TRANSPORT_QUALIFIED",
            "periodic_boundaries": "NOT_USED", "sector_boundary_type": "vacuum",
            "coil_geometry": "native individual swept-spline HDF5 surfaces from the supplied payload",
            "swept_coils_file": str(payload_path), "plasma_surface_file": str(plasma_path),
            "source_hashes": self.source_hashes, "members": len(self.members),
            "model_gaps": self.as_dict()["transport_limitations"]}
        (output / "diagnostic_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {"plasma_surface": surface_file, "materials": output / "materials.xml", "geometry": output / "geometry.xml",
                "settings": output / "settings.xml", "tallies": output / "tallies.xml", "receipt": output / "diagnostic_receipt.json"}


def _read_payload_members(path: Path, manifest: dict[str, object]) -> tuple[CoilMember, ...]:
    listed = {str(item["dataset"]): item for item in manifest.get("members", [])}
    if not listed:
        raise ValueError("sector manifest has no retained finite coil members")
    members: list[CoilMember] = []
    with h5py.File(path, "r") as handle:
        for dataset, record in sorted(listed.items()):
            if not dataset.startswith("/coils/") or dataset not in handle:
                raise ValueError(f"sector member is absent from swept payload: {dataset}")
            group = handle[dataset]
            units = _decode(group.attrs.get("units", ""))
            content_id = _decode(group.attrs.get("content_id", ""))
            coil_id = int(group.attrs.get("coil_id", -1))
            major = np.asarray(group["major_radius_coefficients"], dtype=float)
            minor = np.asarray(group["minor_radius_coefficients"], dtype=float)
            if "centerline_coefficients" not in group:
                raise ValueError(f"payload member lacks centerline coefficients: {dataset}")
            centerline = np.asarray(group["centerline_coefficients"], dtype=float)
            if units != "cm" or not content_id or coil_id <= 0:
                raise ValueError(f"payload member lacks cm units, content ID, or coil ID: {dataset}")
            if major.size == 0 or minor.size == 0 or not np.isfinite(major).all() or not np.isfinite(minor).all() or np.min(major) <= 0 or np.min(minor) <= 0:
                raise ValueError(f"payload member has invalid section coefficients: {dataset}")
            if coil_id != int(record["coil_id"]):
                raise ValueError(f"manifest/payload coil ID mismatch for {dataset}")
            if centerline.ndim != 2 or centerline.shape[1] != 3 or centerline.shape[0] != major.size or not np.isfinite(centerline).all():
                raise ValueError(f"payload member has invalid centerline coefficients: {dataset}")
            # A source box around an actual centerline coefficient is a
            # hit-rich diagnostic origin, not a replacement coil geometry.
            radius = float(max(np.max(major), np.max(minor)))
            eligible = centerline[(centerline[:, 0] > 2.0 * radius) & (centerline[:, 1] > 2.0 * radius)]
            anchor = eligible[len(eligible) // 2] if len(eligible) else centerline[len(centerline) // 2]
            members.append(CoilMember(
                coil_id=coil_id, dataset=dataset, content_id=content_id,
                section_major_radius_cm=float(np.max(major)), section_minor_radius_cm=float(np.max(minor)),
                material_id=f"winding-pack-{coil_id:03d}", cell_id=f"finite-coil-{coil_id:03d}",
                crosses_lower_seam_candidate=bool(record.get("crosses_0_plane_candidate")),
                crosses_upper_seam_candidate=bool(record.get("crosses_90_plane_candidate")),
                retained_span_count=int(record.get("retained_span_count", 0)),
                diagnostic_source_anchor_cm=tuple(float(value) for value in anchor),
            ))
    return tuple(members)


def _write_xml(path: Path, root: ET.Element) -> None:
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def _materials_xml(members: tuple[CoilMember, ...]) -> ET.Element:
    root = ET.Element("materials")
    for member in members:
        material = ET.SubElement(root, "material", id=str(1000 + member.coil_id), name=member.material_id + "_DIAGNOSTIC_H1")
        ET.SubElement(material, "density", units="atom/b-cm", value="1e-6")
        ET.SubElement(material, "nuclide", name="H1", ao="1.0")
    return root


def _geometry_xml(members: tuple[CoilMember, ...], plasma_file: Path, coil_file: Path, plasma_content_id: str) -> ET.Element:
    root = ET.Element("geometry")
    ET.SubElement(root, "surface", id="1", type="periodic-spline", name="plasma_boundary",
                  data_file=str(plasma_file), dataset="/surfaces/plasma_boundary", content_id=plasma_content_id,
                  solver="reference", units="cm")
    ET.SubElement(root, "surface", id="2", type="x-plane", name="sector_x0_vacuum", coeffs="0", boundary="vacuum")
    ET.SubElement(root, "surface", id="3", type="y-plane", name="sector_y0_vacuum", coeffs="0", boundary="vacuum")
    coil_ids: list[str] = []
    for member in members:
        surface_id = 10000 + member.coil_id
        coil_ids.append(str(surface_id))
        ET.SubElement(root, "surface", id=str(surface_id), type="swept-spline", name=member.cell_id,
                      data_file=str(coil_file), dataset=member.dataset, content_id=member.content_id, units="cm")
    outside_all = " ".join(coil_ids)
    for member in members:
        surface_id = str(10000 + member.coil_id)
        region = " ".join([f"-{surface_id}", "2", "3"])
        ET.SubElement(root, "cell", id=str(2000 + member.coil_id), name=member.cell_id,
                      material=str(1000 + member.coil_id), region=region)
    ET.SubElement(root, "cell", id="10", name="plasma_diagnostic_void", region=" ".join(["-1", "2", "3", outside_all]))
    ET.SubElement(root, "cell", id="11", name="sector_exterior_diagnostic_void", region=" ".join(["1", "2", "3", outside_all]))
    return root


def _settings_xml(members: tuple[CoilMember, ...]) -> ET.Element:
    root = ET.Element("settings")
    ET.SubElement(root, "run_mode").text = "fixed source"
    ET.SubElement(root, "particles").text = "100"
    ET.SubElement(root, "batches").text = "1"
    anchor = np.asarray(members[len(members) // 2].diagnostic_source_anchor_cm, dtype=float)
    # A small box about one retained centerline point produces distributed,
    # hit-rich starts away from the origin axis and sector seams.
    padding = np.full(3, 0.05)
    source = ET.SubElement(root, "source", particle="neutron")
    space = ET.SubElement(source, "space", type="box")
    ET.SubElement(space, "parameters").text = " ".join(f"{value:.12g}" for value in np.r_[anchor - padding, anchor + padding])
    ET.SubElement(source, "angle", type="isotropic")
    energy = ET.SubElement(source, "energy", type="discrete")
    ET.SubElement(energy, "parameters").text = "14000000.0"
    return root


def _tallies_xml(members: tuple[CoilMember, ...]) -> ET.Element:
    root = ET.Element("tallies")
    tally = ET.SubElement(root, "tally", id="1", name="diagnostic_member_identity")
    ET.SubElement(tally, "filter", type="cell", bins=" ".join(["10", *[str(2000 + member.coil_id) for member in members]]))
    ET.SubElement(tally, "scores").text = "flux"
    return root


def _source_seam(vmec: VmecBoundary, sample_count: int) -> dict[str, object]:
    theta = 2.0 * np.pi * np.arange(sample_count) / sample_count
    span = 2.0 * np.pi / vmec.n_field_periods
    lower = vmec.position_cm(theta, np.zeros_like(theta))
    upper = vmec.position_cm(theta, np.full_like(theta, span))
    error = np.linalg.norm(upper - _rotate_z(lower, span), axis=1)
    return {"method": "VMEC boundary endpoint versus rotated first endpoint", "sample_count": sample_count,
            "max_source_plasma_seam_error_cm": float(np.max(error)), "mean_source_plasma_seam_error_cm": float(np.mean(error))}


def prepare_one_period_model(
    *, vmec_file: str | Path, filament_file: str | Path, swept_coils_file: str | Path,
    sector_manifest_file: str | Path, symmetry_policy: SymmetryPolicy = "reject",
    seam_tolerance_cm: float = 1.0e-8, n_theta: int = 64, n_phi: int = 32,
) -> OnePeriodModelPlan:
    """Prepare a single sector, explicitly rejecting unapproved symmetry changes."""
    if symmetry_policy not in {"reject", "record-approximation"}:
        raise ValueError("symmetry_policy must be 'reject' or 'record-approximation'")
    if seam_tolerance_cm <= 0 or not math.isfinite(seam_tolerance_cm):
        raise ValueError("seam_tolerance_cm must be finite and positive")
    vmec_path, filament_path = Path(vmec_file), Path(filament_file)
    payload_path, manifest_path = Path(swept_coils_file), Path(sector_manifest_file)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_hashes = {"vmec": _sha256(vmec_path), "makegrid_filaments": _sha256(filament_path),
        "swept_coil_payload": _sha256(payload_path), "sector_manifest": _sha256(manifest_path)}
    expected_hashes = {str(value).lower() for value in dict(manifest.get("sources", {})).values()}
    if expected_hashes and not {source_hashes["vmec"], source_hashes["makegrid_filaments"], source_hashes["swept_coil_payload"]} <= expected_hashes:
        raise ValueError("REJECT_SOURCE_HASH_MISMATCH: supplied VMEC, MAKEGRID, or swept payload differs from the sector manifest")
    vmec = VmecBoundary.from_wout(vmec_path)
    filament_nfp, _ = read_makegrid_filaments(filament_path)
    manifest_nfp = int(manifest.get("nfp", -1))
    if len({vmec.n_field_periods, filament_nfp, manifest_nfp}) != 1:
        raise ValueError("REJECT_NFP_MISMATCH: VMEC, MAKEGRID, and sector manifest must agree")
    if manifest.get("sector_degrees") != [0, 90] or vmec.n_field_periods != 4:
        raise ValueError("REJECT_SECTOR_ASSUMPTION: this initial importer requires WISTELL-D NFP=4 and [0, 90] degrees")
    grid, phi, _, _ = vmec.surface_grid_cm(n_theta, n_phi)
    plasma = PeriodicRadialSurfaceData.from_surface_grid(
        name="plasma_boundary", xyz_cm=grid, phi=phi, n_field_periods=vmec.n_field_periods,
        source_metadata={"importer": "stellarcsg.one_period", "vmec_source_units": "m", "transport_units": "cm"},
    )
    seam = _source_seam(vmec, n_theta)
    rotation_errors = [float(item["max_aligned_control_error_cm"]) for item in manifest.get("rotation_diagnostic", [])]
    seam["max_manifest_coil_rotation_error_cm"] = max(rotation_errors, default=0.0)
    seam["tolerance_cm"] = seam_tolerance_cm
    mismatch = max(seam["max_source_plasma_seam_error_cm"], seam["max_manifest_coil_rotation_error_cm"])
    approximation = None
    if mismatch > seam_tolerance_cm:
        if symmetry_policy == "reject":
            raise ValueError("REJECT_PERIODIC_SEAM_MISMATCH: use record-approximation only with an explicit representation-change record")
        approximation = {"kind": "input_symmetry_mismatch_retained", "maximum_observed_cm": mismatch,
            "tolerance_cm": seam_tolerance_cm,
            "policy": "No rotated copies are imposed; complete supplied finite coil members are retained and sector-clipped later."}
    return OnePeriodModelPlan(
        plasma=plasma, members=_read_payload_members(payload_path, manifest), n_field_periods=vmec.n_field_periods,
        sector_degrees=(0.0, 90.0), source_hashes=source_hashes,
        seam_diagnostic=seam, symmetry_policy=symmetry_policy, approximation_record=approximation,
        swept_coils_file=payload_path.resolve(),
    )
