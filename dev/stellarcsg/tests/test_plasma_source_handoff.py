"""Synthetic contract controls only; no UQ source or native transport is admitted."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from stellarcsg.plasma_source import load_bounded_plasma_source


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(directory: Path, name: str, value) -> dict:
    path = directory / name
    path.write_text(json.dumps(value, allow_nan=False) + "\n")
    return {"name": name, "sha256": _sha(path)}


def synthetic_bundle(directory: Path, *, clearance_status="QUALIFIED_BOUNDED_SOURCE",
                     gap=2.0, source_probability=1.0, sampling_valid=True,
                     physical_rate=None, invert_cell=False) -> Path:
    # This intentionally fabricated fixture exercises wiring. Its evidence
    # flags are not a real clearance or sampling certificate.
    mesh = directory / "synthetic-mesh.h5m"
    mesh.write_bytes(b"synthetic fixture; not a MOAB mesh\n")
    mesh_binding = {"name": mesh.name, "sha256": _sha(mesh)}
    wall = directory / "synthetic-wall.h5m"
    wall.write_bytes(b"synthetic fixture; not a stellarator wall\n")
    wall_binding = {"name": wall.name, "sha256": _sha(wall)}
    mesh_data = {
        "vertices_cm": [[1, 1, 0], [2, 1, 0], [1, 2, 0], [1, 1, 1]],
        "vertex_s": [0, .5, .5, .5],
        "connectivity": [[0, 2, 1, 3] if invert_cell else [0, 1, 2, 3]],
        "volumes_cm3": [1 / 6], "support_s_max": 1.0,
        "tetra_s": [[0, .5, .5, .5]], "centroids_cm": [[1.25, 1.25, .25]],
        "tetrahedron_count": 1,
    }
    mesh_data_binding = _write(directory, "mesh-data.json", mesh_data)
    case = {
        "case_id": "synthetic", "evidence_class": "B",
        "phase": "analyst_stress_test", "physical_rate_n_s": physical_rate,
        "source_strength": 1.0, "source_mesh": {"sha256": mesh_binding["sha256"]},
        "mesh_data": {"sha256": mesh_data_binding["sha256"]},
        "probabilities": [source_probability],
        "integrated_shape_strengths_cm3": [1 / 6],
        "shape_integral_cm3": 1 / 6,
        "cell_birth_spectra": [
            {"energies_eV": [14_100_000.0], "probabilities": [1.0]}],
    }
    case_binding = _write(directory, "case.json", case)
    source_result = {
        "status": "VMEC_SOURCE_MESH_EXPORTED_PENDING_CONTAINMENT",
        "exit_code": 0, "physical_rate_n_s": None,
        "evidence_class": "B", "phase": "analyst_stress_test",
        "checks": {"vmec": {"nfp": 4}, "support_s_max": 1.0},
        "tetrahedron_count": 1,
        "mesh_file": {"sha256": mesh_binding["sha256"]},
        "mesh_data_file": {"sha256": mesh_data_binding["sha256"]},
        "cases": [{"id": "synthetic", "source_file":
                   {"sha256": case_binding["sha256"]}}],
    }
    source_binding = _write(directory, "source-result.json", source_result)
    sampling = {
        "status": "VMEC_NATIVE_SOURCE_SAMPLING_CHECKS_PASSED",
        "exit_code": 0, "case_id": "synthetic", "physical_rate_n_s": None,
        "evidence_class": "B", "source_strength": 1.0,
        "native_element_count": 1,
        "input_sha256": {name: binding["sha256"] for name, binding in
                         (("source", source_binding), ("mesh", mesh_binding),
                          ("mesh_data", mesh_data_binding), ("case", case_binding))},
        **{name: sampling_valid for name in (
            "native_element_volumes_in_source_order_passed",
            "all_sites_uniquely_assigned", "unit_weight_passed",
            "isotropy_passed", "spatial_and_joint_energy_counts_passed",
            "conditional_energy_support_passed",
            "pooled_uniform_barycentric_moments_passed")},
    }
    sampling_binding = _write(directory, "sampling-result.json", sampling)
    clearance = {
        "schema": "stellarator_uq.bound-source-clearance/v1",
        "status": clearance_status,
        "source_mesh_sha256": mesh_binding["sha256"],
        "wall_h5m_sha256": wall_binding["sha256"],
        "certified_gap_lower_bound_cm": gap,
        "continuous_wall_error_bound_cm": .1,
        "required_clearance_cm": 1.0,
        "whole_cells_inside_cavity": True,
        "periodic_sector_contained": True,
        "source_wall_intersection_excluded": True,
    }
    clearance_binding = _write(directory, "clearance-result.json", clearance)
    handoff = {
        "schema": "stellarcsg.plasma-source-handoff/v1",
        "state": "ADMITTED_BOUNDED_DIAGNOSTIC", "field_period_degrees": 90,
        "coordinate_units": "cm", "physical_rate_n_s": physical_rate,
        "case_id": "synthetic",
        "files": {"source_result": source_binding,
                  "sampling_result": sampling_binding,
                  "clearance_result": clearance_binding,
                  "mesh": mesh_binding, "mesh_data": mesh_data_binding,
                  "case": case_binding, "wall": wall_binding},
    }
    return directory / _write(directory, "admission.json", handoff)["name"]


def _load(handoff: Path):
    return load_bounded_plasma_source(
        handoff, expected_wall_sha256=_sha(handoff.parent / "synthetic-wall.h5m"))


class PlasmaSourceHandoffTests(unittest.TestCase):
    def test_synthetic_constructor_contract(self):
        with TemporaryDirectory() as temporary:
            handoff = synthetic_bundle(Path(temporary))
            admitted = _load(handoff)
            self.assertIsNone(admitted.physical_rate_n_s)
            self.assertEqual(admitted.probabilities, (1.0,))
            self.assertEqual(admitted.wall_sha256,
                             _sha(handoff.parent / "synthetic-wall.h5m"))
            import openmc
            mesh, source = admitted.make_openmc_source(openmc)
            self.assertEqual(mesh.library, "moab")
            self.assertEqual(source.strength, 1.0)

    def test_unqualified_clearance_rejected(self):
        with TemporaryDirectory() as temporary:
            handoff = synthetic_bundle(Path(temporary),
                                       clearance_status="FACET_SURFACES_INTERSECT_OR_TOUCH")
            with self.assertRaisesRegex(ValueError, "clearance"):
                _load(handoff)

    def test_clearance_margin_rejected(self):
        with TemporaryDirectory() as temporary:
            handoff = synthetic_bundle(Path(temporary), gap=1.05)
            with self.assertRaisesRegex(ValueError, "clearance"):
                _load(handoff)

    def test_sampling_gate_rejected(self):
        with TemporaryDirectory() as temporary:
            handoff = synthetic_bundle(Path(temporary), sampling_valid=False)
            with self.assertRaisesRegex(ValueError, "sampling"):
                _load(handoff)

    def test_rate_stays_separate(self):
        with TemporaryDirectory() as temporary:
            handoff = synthetic_bundle(Path(temporary), physical_rate=1e19)
            with self.assertRaisesRegex(ValueError, "not admitted"):
                _load(handoff)

    def test_cell_probability_and_orientation_rejected(self):
        for overrides, message in (({"source_probability": .9}, "probabilities"),
                                   ({"invert_cell": True}, "tetrahedron")):
            with self.subTest(overrides=overrides), TemporaryDirectory() as temporary:
                handoff = synthetic_bundle(Path(temporary), **overrides)
                with self.assertRaisesRegex(ValueError, message):
                    _load(handoff)

    def test_tampered_mesh_rejected(self):
        with TemporaryDirectory() as temporary:
            handoff = synthetic_bundle(Path(temporary))
            (handoff.parent / "synthetic-mesh.h5m").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                _load(handoff)

    def test_tampered_wall_rejected(self):
        with TemporaryDirectory() as temporary:
            handoff = synthetic_bundle(Path(temporary))
            (handoff.parent / "synthetic-wall.h5m").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                _load(handoff)

    def test_caller_fixed_wall_identity_required(self):
        with TemporaryDirectory() as temporary:
            handoff = synthetic_bundle(Path(temporary))
            with self.assertRaisesRegex(ValueError, "required"):
                load_bounded_plasma_source(handoff, expected_wall_sha256="")
            with self.assertRaisesRegex(ValueError, "expected fixed geometry"):
                load_bounded_plasma_source(
                    handoff, expected_wall_sha256="0" * 64)


if __name__ == "__main__":
    unittest.main()
