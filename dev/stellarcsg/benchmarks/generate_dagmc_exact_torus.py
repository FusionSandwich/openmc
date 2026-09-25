"""Generate and measure same-source DAGMC exact-torus reference meshes.

Run inside the pinned ``parastell-openmc:0.16.0`` container. Geometry and
reported coordinates are centimetres, matching OpenMC and StellarCSG.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq
from cad_to_dagmc import CadToDagmc
import numpy as np
from pymoab import core


MAJOR_RADIUS_CM = 500.0
MINOR_RADIUS_CM = 100.0
EXACT_AREA_CM2 = 4.0 * math.pi**2 * MAJOR_RADIUS_CM * MINOR_RADIUS_CM
EXACT_VOLUME_CM3 = 2.0 * math.pi**2 * MAJOR_RADIUS_CM * MINOR_RADIUS_CM**2


def surface_distance(points: np.ndarray) -> np.ndarray:
    cylindrical_radius = np.hypot(points[:, 0], points[:, 1])
    tube_radius = np.hypot(cylindrical_radius - MAJOR_RADIUS_CM, points[:, 2])
    return np.abs(tube_radius - MINOR_RADIUS_CM)


def measure_mesh(path: Path) -> dict:
    mesh = core.Core()
    mesh.load_file(str(path))
    triangles = list(mesh.get_entities_by_dimension(0, 2))
    vertices = list(mesh.get_entities_by_dimension(0, 0))
    sample_blocks = []
    mesh_area = 0.0
    signed_volume = 0.0
    for triangle in triangles:
        handles = mesh.get_connectivity(triangle)
        xyz = np.asarray(mesh.get_coords(handles), dtype=float).reshape(3, 3)
        a, b, c = xyz
        cross = np.cross(b - a, c - a)
        mesh_area += 0.5 * np.linalg.norm(cross)
        signed_volume += np.dot(a, np.cross(b, c)) / 6.0
        sample_blocks.append(np.vstack((
            xyz,
            0.5 * (a + b),
            0.5 * (b + c),
            0.5 * (c + a),
            (a + b + c) / 3.0,
        )))
    samples = np.vstack(sample_blocks)
    errors = surface_distance(samples)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": path.as_posix(),
        "bytes": path.stat().st_size,
        "sha256": digest,
        "vertices": len(vertices),
        "triangles": len(triangles),
        "sample_points": len(errors),
        "sampled_surface_error_max_cm": float(np.max(errors)),
        "sampled_surface_error_rms_cm": float(np.sqrt(np.mean(errors**2))),
        "sampled_surface_error_p95_cm": float(np.percentile(errors, 95)),
        "mesh_area_cm2": mesh_area,
        "exact_area_cm2": EXACT_AREA_CM2,
        "area_relative_error": mesh_area / EXACT_AREA_CM2 - 1.0,
        "mesh_signed_volume_cm3": signed_volume,
        "mesh_abs_volume_cm3": abs(signed_volume),
        "exact_volume_cm3": EXACT_VOLUME_CM3,
        "volume_relative_error": abs(signed_volume) / EXACT_VOLUME_CM3 - 1.0,
    }


def generate(path: Path, minimum: float, maximum: float) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    converter = CadToDagmc()
    converter.add_cadquery_object(
        cq.Solid.makeTorus(MAJOR_RADIUS_CM, MINOR_RADIUS_CM), ["Vacuum"]
    )
    converter.export_dagmc_h5m_file(
        str(path),
        implicit_complement_material_tag="Vacuum",
        meshing_backend="gmsh",
        h5m_backend="pymoab",
        min_mesh_size=minimum,
        max_mesh_size=maximum,
        imprint=False,
    )
    result = measure_mesh(path)
    result["gmsh_min_mesh_size_cm"] = minimum
    result["gmsh_max_mesh_size_cm"] = maximum
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/work"))
    args = parser.parse_args()
    root = args.root.resolve()
    specifications = (
        ("coarse", 10.0, 25.0),
        ("fine", 3.0, 10.0),
    )
    meshes = []
    for name, minimum, maximum in specifications:
        path = root / "dev/stellarcsg/qualified" / f"dagmc_exact_torus_{name}.h5m"
        item = generate(path, minimum, maximum)
        item["name"] = name
        meshes.append(item)
    report = {
        "schema": "stellarcsg.dagmc-exact-torus-fidelity/v1",
        "units": "cm",
        "source_geometry": {
            "type": "exact_circular_torus",
            "major_radius_cm": MAJOR_RADIUS_CM,
            "minor_radius_cm": MINOR_RADIUS_CM,
        },
        "generator": {
            "container_image": "parastell-openmc:0.16.0",
            "container_image_id": "sha256:ca0c3b1fba39ce27af6ebdb79df14795041922e72521f232cdd770ff1c416191",
            "cad_to_dagmc": "0.11.5",
            "cadquery": "2.7.0",
            "meshing_backend": "gmsh",
            "h5m_backend": "pymoab",
        },
        "error_method": "Exact torus distance sampled at every triangle vertex, edge midpoint, and centroid.",
        "meshes": meshes,
    }
    report_path = root / "dev/stellarcsg/reports/DAGMC_EXACT_TORUS_FIDELITY.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    csv_path = root / "dev/stellarcsg/reports/DAGMC_EXACT_TORUS_FIDELITY.csv"
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=sorted(meshes[0]))
        writer.writeheader()
        writer.writerows(meshes)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
