"""Fail-closed handoff for a wall-bounded one-period UQ MeshSource.

An admitted bundle is still a diagnostic normalized birth PDF. Its physical
neutron rate is separate and null in this class-B contract. No source is
constructed from an exported mesh that lacks bound sampling and clearance.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re


_SHA = re.compile(r"[0-9a-f]{64}\Z")
_FILES = ("source_result", "sampling_result", "clearance_result",
          "mesh", "mesh_data", "case", "wall")
_SAMPLING_CHECKS = (
    "native_element_volumes_in_source_order_passed",
    "all_sites_uniquely_assigned", "unit_weight_passed", "isotropy_passed",
    "spatial_and_joint_energy_counts_passed",
    "conditional_energy_support_passed",
    "pooled_uniform_barycentric_moments_passed",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _number(value, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(f"{name} must be finite") from error
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'valid'}")
    return result


def _bound_file(directory: Path, entry: dict, name: str) -> tuple[Path, str]:
    if not isinstance(entry, dict) or set(entry) != {"name", "sha256"}:
        raise ValueError(f"invalid {name} file binding")
    filename, expected = entry["name"], entry["sha256"]
    if (not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", filename)
            or Path(filename).name != filename or not isinstance(expected, str)
            or not _SHA.fullmatch(expected)):
        raise ValueError(f"unsafe or invalid {name} file binding")
    path = (directory / filename).resolve(strict=True)
    if path.parent != directory or not path.is_file() or _sha256(path) != expected:
        raise ValueError(f"{name} path or SHA-256 mismatch")
    return path, expected


def _positive_tetra_volumes(mesh_data: dict) -> int:
    vertices = mesh_data["vertices_cm"]
    connectivity = mesh_data["connectivity"]
    volumes = mesh_data["volumes_cm3"]
    vertex_s = mesh_data["vertex_s"]
    tetra_s = mesh_data["tetra_s"]
    centroids = mesh_data["centroids_cm"]
    support = _number(mesh_data["support_s_max"], "support_s_max", positive=True)
    if (support > 1 or not vertices or not connectivity
            or len(connectivity) != len(volumes)
            or len(connectivity) != len(tetra_s)
            or len(connectivity) != len(centroids)
            or len(vertex_s) != len(vertices)
            or mesh_data["tetrahedron_count"] != len(connectivity)):
        raise ValueError("invalid source mesh array lengths or support")
    points = []
    for point, s in zip(vertices, vertex_s):
        if len(point) != 3:
            raise ValueError("source vertex is not Cartesian xyz")
        xyz = tuple(_number(x, "source vertex") for x in point)
        if xyz[0] < -1e-9 or xyz[1] < -1e-9 or not 0 <= _number(s, "vertex s") <= support:
            raise ValueError("source vertex leaves the declared first period")
        points.append(xyz)
    for index, (tet, stated_volume) in enumerate(zip(connectivity, volumes)):
        if (len(tet) != 4 or any(type(v) is not int or v < 0 or v >= len(points)
                                 for v in tet) or len(set(tet)) != 4):
            raise ValueError(f"invalid tetrahedron connectivity at {index}")
        a, b, c, d = (points[v] for v in tet)
        stated_s = tuple(_number(s, "tetra s") for s in tetra_s[index])
        expected_s = tuple(_number(vertex_s[v], "vertex s") for v in tet)
        centroid = tuple(_number(x, "centroid") for x in centroids[index])
        if (len(stated_s) != 4 or stated_s != expected_s or len(centroid) != 3
                or any(not math.isclose(centroid[j],
                    math.fsum(p[j] for p in (a, b, c, d)) / 4,
                    rel_tol=1e-12, abs_tol=1e-9) for j in range(3))):
            raise ValueError(f"tetrahedron profile or centroid mismatch at {index}")
        u, v, w = (tuple(p[j] - a[j] for j in range(3)) for p in (b, c, d))
        determinant = math.fsum((u[0]*v[1]*w[2], u[1]*v[2]*w[0],
                                 u[2]*v[0]*w[1], -u[2]*v[1]*w[0],
                                 -u[1]*v[0]*w[2], -u[0]*v[2]*w[1]))
        calculated = determinant / 6.0
        stated = _number(stated_volume, "source cell volume", positive=True)
        if (not math.isfinite(calculated) or calculated <= 0
                or not math.isclose(calculated, stated, rel_tol=1e-10, abs_tol=1e-8)):
            raise ValueError(f"nonpositive or inconsistent tetrahedron at {index}")
    return len(connectivity)


@dataclass(frozen=True)
class BoundedPlasmaSource:
    mesh_path: Path
    case_id: str
    probabilities: tuple[float, ...]
    spectra: tuple[tuple[tuple[float, ...], tuple[float, ...]], ...]
    handoff_sha256: str
    mesh_sha256: str
    wall_sha256: str
    physical_rate_n_s: None = None

    def make_openmc_source(self, openmc_module=None):
        """Construct normalized OpenMC objects; native sampling is upstream evidence."""
        if openmc_module is None:
            import openmc as openmc_module
        mesh = openmc_module.UnstructuredMesh(
            str(self.mesh_path), library="moab", length_multiplier=1.0)
        sources = [openmc_module.IndependentSource(
            strength=p, angle=openmc_module.stats.Isotropic(),
            energy=openmc_module.stats.Discrete(energies, weights))
            for p, (energies, weights) in zip(self.probabilities, self.spectra)]
        source = openmc_module.MeshSource(mesh, sources)
        if not math.isclose(source.strength, 1.0, rel_tol=0, abs_tol=1e-12):
            raise ValueError("OpenMC normalized source strength changed")
        return mesh, source


def load_bounded_plasma_source(
    handoff_path: Path, *, expected_wall_sha256: str
) -> BoundedPlasmaSource:
    """Validate a UQ bundle against the caller's fixed geometry wall hash."""
    if not isinstance(expected_wall_sha256, str) or not _SHA.fullmatch(
            expected_wall_sha256):
        raise ValueError("expected fixed-wall SHA-256 is required")
    handoff_path = Path(handoff_path).resolve(strict=True)
    directory = handoff_path.parent
    handoff = json.loads(handoff_path.read_text())
    if (handoff.get("schema") != "stellarcsg.plasma-source-handoff/v1"
            or handoff.get("state") != "ADMITTED_BOUNDED_DIAGNOSTIC"
            or handoff.get("field_period_degrees") != 90
            or handoff.get("coordinate_units") != "cm"
            or handoff.get("physical_rate_n_s", 0) is not None
            or not isinstance(handoff.get("case_id"), str)
            or not isinstance(handoff.get("files"), dict)
            or set(handoff["files"]) != set(_FILES)):
        raise ValueError("plasma source handoff is not admitted for this period")
    bound = {name: _bound_file(directory, handoff["files"][name], name)
             for name in _FILES}
    source_result, sampling, clearance, mesh_data, case = (
        json.loads(bound[name][0].read_text()) for name in
        ("source_result", "sampling_result", "clearance_result", "mesh_data", "case"))
    hashes = {name: binding[1] for name, binding in bound.items()}
    if hashes["wall"] != expected_wall_sha256:
        raise ValueError("source wall differs from the expected fixed geometry")
    if (source_result.get("status") != "VMEC_SOURCE_MESH_EXPORTED_PENDING_CONTAINMENT"
            or source_result.get("exit_code") != 0
            or source_result.get("evidence_class") != "B"
            or source_result.get("phase") != "analyst_stress_test"
            or source_result.get("checks", {}).get("vmec", {}).get("nfp") != 4
            or source_result.get("physical_rate_n_s", 0) is not None
            or source_result.get("tetrahedron_count") != mesh_data.get("tetrahedron_count")
            or source_result.get("checks", {}).get("support_s_max") != mesh_data.get("support_s_max")
            or source_result.get("mesh_file", {}).get("sha256") != hashes["mesh"]
            or source_result.get("mesh_data_file", {}).get("sha256") != hashes["mesh_data"]):
        raise ValueError("source export identity or status is invalid")
    matches = [row for row in source_result.get("cases", [])
               if row.get("id") == handoff["case_id"]]
    if (len(matches) != 1 or matches[0].get("source_file", {}).get("sha256") != hashes["case"]
            or case.get("case_id") != handoff["case_id"]
            or case.get("source_mesh", {}).get("sha256") != hashes["mesh"]
            or case.get("mesh_data", {}).get("sha256") != hashes["mesh_data"]
            or case.get("evidence_class") != "B"
            or case.get("phase") != "analyst_stress_test"
            or case.get("physical_rate_n_s", 0) is not None
            or case.get("source_strength") != 1.0):
        raise ValueError("source case identity or evidence is invalid")
    if (sampling.get("status") != "VMEC_NATIVE_SOURCE_SAMPLING_CHECKS_PASSED"
            or sampling.get("exit_code") != 0
            or sampling.get("evidence_class") != "B"
            or sampling.get("case_id") != handoff["case_id"]
            or sampling.get("physical_rate_n_s", 0) is not None
            or sampling.get("source_strength") != 1.0
            or any(sampling.get(flag) is not True for flag in _SAMPLING_CHECKS)
            or not set(hashes[name] for name in ("source_result", "mesh", "mesh_data", "case"))
                <= set(sampling.get("input_sha256", {}).values())):
        raise ValueError("native source sampling evidence is incomplete")
    gap = _number(clearance.get("certified_gap_lower_bound_cm"), "source-wall gap")
    error = _number(clearance.get("continuous_wall_error_bound_cm"), "wall error")
    required = _number(clearance.get("required_clearance_cm"), "required clearance", positive=True)
    wall_hash = clearance.get("wall_h5m_sha256")
    if (clearance.get("schema") != "stellarator_uq.bound-source-clearance/v1"
            or clearance.get("status") != "QUALIFIED_BOUNDED_SOURCE"
            or clearance.get("source_mesh_sha256") != hashes["mesh"]
            or wall_hash != hashes["wall"]
            or clearance.get("whole_cells_inside_cavity") is not True
            or clearance.get("periodic_sector_contained") is not True
            or clearance.get("source_wall_intersection_excluded") is not True
            or error < 0 or gap - error < required):
        raise ValueError("source clearance does not admit bounded support")
    count = _positive_tetra_volumes(mesh_data)
    if (sampling.get("native_element_count") != count
            or len(case.get("probabilities", [])) != count
            or len(case.get("cell_birth_spectra", [])) != count):
        raise ValueError("source element order or array length mismatch")
    probabilities = tuple(_number(p, "element probability") for p in case["probabilities"])
    if any(p < 0 for p in probabilities) or not math.isclose(
            math.fsum(probabilities), 1.0, rel_tol=0, abs_tol=1e-12):
        raise ValueError("source element probabilities are not normalized")
    strengths = tuple(_number(s, "integrated shape strength")
                      for s in case.get("integrated_shape_strengths_cm3", []))
    integral = _number(case.get("shape_integral_cm3"), "shape integral", positive=True)
    if (len(strengths) != count or any(s < 0 for s in strengths)
            or not math.isclose(math.fsum(strengths), integral, rel_tol=1e-12)
            or any(not math.isclose(p, s / integral, rel_tol=1e-12, abs_tol=1e-14)
                   for p, s in zip(probabilities, strengths))):
        raise ValueError("source probabilities do not match profile integrals")
    spectra = []
    for row in case["cell_birth_spectra"]:
        energies = tuple(_number(e, "birth energy", positive=True) for e in row["energies_eV"])
        weights = tuple(_number(p, "birth weight") for p in row["probabilities"])
        if (not 1 <= len(energies) <= 2 or len(weights) != len(energies)
                or len(set(energies)) != len(energies)
                or any(p < 0 for p in weights)
                or not math.isclose(math.fsum(weights), 1.0, rel_tol=0, abs_tol=1e-12)):
            raise ValueError("invalid conditional birth spectrum")
        spectra.append((energies, weights))
    return BoundedPlasmaSource(bound["mesh"][0], handoff["case_id"],
        probabilities, tuple(spectra), _sha256(handoff_path), hashes["mesh"],
        hashes["wall"])
