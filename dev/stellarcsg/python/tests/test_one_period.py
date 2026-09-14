from __future__ import annotations

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import h5py
import numpy as np
import pytest
from scipy.io import netcdf_file

from stellarcsg.one_period import prepare_one_period_model


def _inputs(tmp_path, rotation_error: float = 0.0):
    vmec = tmp_path / "wout.nc"
    with netcdf_file(vmec, "w") as handle:
        handle.createDimension("surface", 1)
        handle.createDimension("mode", 2)
        handle.createDimension("axis", 1)
        handle.createDimension("scalar", 1)
        handle.createVariable("nfp", "i", ("scalar",))[:] = [4]
        handle.createVariable("rmnc", "d", ("surface", "mode"))[:] = [[5.0, 1.0]]
        handle.createVariable("zmns", "d", ("surface", "mode"))[:] = [[0.0, 1.0]]
        handle.createVariable("xm", "d", ("mode",))[:] = [0.0, 1.0]
        handle.createVariable("xn", "d", ("mode",))[:] = [0.0, 0.0]
        for name, value in (("raxis_cc", 5.0), ("zaxis_cs", 0.0)):
            handle.createVariable(name, "d", ("axis",))[:] = [value]
    filament = tmp_path / "coils.makegrid"
    filament.write_text("periods 4\n1 0 0 1\n0 1 0 1\n-1 0 0 1\n0 -1 0 1\n0 0 0 0\n")
    coils = tmp_path / "coils.h5"
    with h5py.File(coils, "w") as handle:
        group = handle.create_group("/coils/coil_001")
        group.attrs["units"] = "cm"
        group.attrs["content_id"] = "sha256:synthetic"
        group.attrs["coil_id"] = 1
        group["centerline_coefficients"] = np.array([[600.0, 0.0, 0.0], [500.0, 100.0, 0.0], [400.0, 0.0, 0.0], [500.0, -100.0, 0.0]])
        group["major_radius_coefficients"] = np.full(4, 1.0)
        group["minor_radius_coefficients"] = np.full(4, 1.0)
    manifest = tmp_path / "sector.json"
    manifest.write_text(json.dumps({"nfp": 4, "sector_degrees": [0, 90], "sources": {
        "vmec": hashlib.sha256(vmec.read_bytes()).hexdigest(), "filaments": hashlib.sha256(filament.read_bytes()).hexdigest(),
        "coils": hashlib.sha256(coils.read_bytes()).hexdigest()}, "members": [{
        "dataset": "/coils/coil_001", "coil_id": 1, "retained_span_count": 4,
        "crosses_0_plane_candidate": True, "crosses_90_plane_candidate": False}],
        "rotation_diagnostic": [{"max_aligned_control_error_cm": rotation_error}]}))
    return vmec, filament, coils, manifest


def test_one_period_plan_records_explicit_symmetry_approximation(tmp_path) -> None:
    vmec, filament, coils, manifest = _inputs(tmp_path, rotation_error=2.0e-4)
    with pytest.raises(ValueError, match="REJECT_PERIODIC_SEAM_MISMATCH"):
        prepare_one_period_model(vmec_file=vmec, filament_file=filament, swept_coils_file=coils,
            sector_manifest_file=manifest, seam_tolerance_cm=1.0e-8)
    plan = prepare_one_period_model(vmec_file=vmec, filament_file=filament, swept_coils_file=coils,
        sector_manifest_file=manifest, symmetry_policy="record-approximation", seam_tolerance_cm=1.0e-8)
    assert plan.approximation_record is not None
    assert plan.members[0].material_id == "winding-pack-001"
    assert plan.members[0].crosses_lower_seam_candidate
    assert plan.source_hashes["vmec"] == hashlib.sha256(vmec.read_bytes()).hexdigest()
    files = plan.export(tmp_path / "export")
    payload = json.loads(files["model_plan"].read_text())
    assert payload["status"] == "PREPARED_NOT_TRANSPORT_QUALIFIED"
    assert payload["finite_coil_members"][0]["sector_neighbor_geometry"]["complete_curve_retained"]
    with pytest.raises(FileExistsError):
        plan.export(tmp_path / "export")


def test_one_period_rejects_nfp_mismatch(tmp_path) -> None:
    vmec, filament, coils, manifest = _inputs(tmp_path)
    filament.write_text(filament.read_text().replace("periods 4", "periods 5"))
    payload = json.loads(manifest.read_text())
    payload["sources"]["filaments"] = hashlib.sha256(filament.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="REJECT_NFP_MISMATCH"):
        prepare_one_period_model(vmec_file=vmec, filament_file=filament, swept_coils_file=coils,
            sector_manifest_file=manifest)


def test_one_period_rejects_manifest_source_hash_mismatch(tmp_path) -> None:
    vmec, filament, coils, manifest = _inputs(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["sources"]["coils"] = "0" * 64
    manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="REJECT_SOURCE_HASH_MISMATCH"):
        prepare_one_period_model(vmec_file=vmec, filament_file=filament, swept_coils_file=coils,
            sector_manifest_file=manifest)


def test_native_swept_diagnostic_xml_has_no_surrogate_or_openmc_dependency(tmp_path) -> None:
    vmec, filament, coils, manifest = _inputs(tmp_path, rotation_error=2.0e-4)
    plan = prepare_one_period_model(vmec_file=vmec, filament_file=filament, swept_coils_file=coils,
        sector_manifest_file=manifest, symmetry_policy="record-approximation")
    files = plan.export_openmc_diagnostic(tmp_path / "diagnostic", diagnostic_clipped=True)
    with h5py.File(files["plasma_surface"], "r") as handle:
        assert "/surfaces/plasma_boundary" in handle
    geometry = ET.parse(files["geometry"]).getroot()
    plasma = geometry.find("surface[@type='periodic-spline']")
    assert plasma is not None
    assert plasma.attrib["dataset"] == "/surfaces/plasma_boundary"
    assert plasma.attrib["solver"] == "reference"
    assert Path(plasma.attrib["data_file"]).is_absolute()
    swept = geometry.find("surface[@type='swept-spline']")
    assert swept is not None
    assert swept.attrib["dataset"] == "/coils/coil_001"
    assert swept.attrib["content_id"] == "sha256:synthetic"
    assert swept.attrib["units"] == "cm"
    assert Path(swept.attrib["data_file"]).is_absolute()
    assert not geometry.findall("surface[@type='sphere']")
    for plane in geometry.findall("surface[@type='x-plane']") + geometry.findall("surface[@type='y-plane']"):
        assert plane.attrib["boundary"] == "vacuum"
    material = ET.parse(files["materials"]).find("material")
    assert material is not None and material.find("nuclide").attrib["name"] == "H1"
    assert material.find("density").attrib["value"] == "1e-6"
    space = ET.parse(files["settings"]).find("source/space")
    assert space is not None and space.attrib["type"] == "box"
    assert "0 0 0" not in (space.findtext("parameters") or "")
    receipt = json.loads(files["receipt"].read_text())
    assert receipt["periodic_boundaries"] == "NOT_USED"
    assert "proxy" not in receipt["coil_geometry"]
