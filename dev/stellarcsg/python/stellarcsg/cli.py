"""Command-line entry points for local StellarCSG qualification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .io import write_surface_collection
from .mesh import build_layer_mesh, write_legacy_vtk, write_mesh_hdf5
from .surface import PeriodicRadialSurfaceData, compile_radial_build


def _demo(args: argparse.Namespace) -> int:
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    plasma = PeriodicRadialSurfaceData.analytic_torus(
        name="plasma",
        major_radius_cm=args.major_radius_cm,
        minor_radius_cm=args.minor_radius_cm,
        n_field_periods=args.n_field_periods,
        n_axis=args.axis_coefficients,
        n_theta=args.theta_coefficients,
        n_phi=args.phi_coefficients,
        helical_amplitude_cm=args.helical_amplitude_cm,
    )
    boundaries = compile_radial_build(
        plasma,
        [
            ("first_wall_outer", args.first_wall_cm),
            ("blanket_outer", args.blanket_cm),
            ("shield_outer", args.shield_cm),
        ],
    )
    geometry_file = output / "compiled_geometry.h5"
    write_surface_collection(geometry_file, boundaries)
    mesh = build_layer_mesh(
        boundaries,
        radial_bins_per_shell=(1, 2, 2),
        theta_bins=args.mesh_theta_bins,
        phi_bins=args.mesh_phi_bins,
        toroidal_extent=args.extent,
    )
    write_mesh_hdf5(output / "tally_mesh.h5", mesh)
    write_legacy_vtk(output / "tally_mesh.vtk", mesh)
    volumes = mesh.approximate_element_volumes_cm3()
    report = {
        "schema_version": 1,
        "geometry_file": str(geometry_file.name),
        "surface_content_ids": {surface.name: surface.content_id for surface in boundaries},
        "mesh": {
            "vertices": int(mesh.vertices_cm.shape[0]),
            "elements": mesh.n_elements,
            "minimum_approximate_element_volume_cm3": float(np.min(volumes)),
            "maximum_approximate_element_volume_cm3": float(np.max(volumes)),
            "total_approximate_volume_cm3": float(np.sum(volumes)),
        },
        "limitations": [
            "radial single-chart representation",
            "reference compiler and tally mesh only",
            "native OpenMC transport adapter is experimental and not production-qualified",
        ],
    }
    (output / "validation_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stellarcsg")
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser(
        "demo", help="compile a helical analytic stellarator and local tally mesh"
    )
    demo.add_argument("--output-dir", default="stellarcsg-demo-output")
    demo.add_argument("--major-radius-cm", type=float, default=500.0)
    demo.add_argument("--minor-radius-cm", type=float, default=100.0)
    demo.add_argument("--n-field-periods", type=int, default=5)
    demo.add_argument("--helical-amplitude-cm", type=float, default=8.0)
    demo.add_argument("--first-wall-cm", type=float, default=2.0)
    demo.add_argument("--blanket-cm", type=float, default=50.0)
    demo.add_argument("--shield-cm", type=float, default=40.0)
    demo.add_argument("--axis-coefficients", type=int, default=16)
    demo.add_argument("--theta-coefficients", type=int, default=32)
    demo.add_argument("--phi-coefficients", type=int, default=24)
    demo.add_argument("--mesh-theta-bins", type=int, default=32)
    demo.add_argument("--mesh-phi-bins", type=int, default=24)
    demo.add_argument(
        "--extent", choices=("full", "field-period"), default="field-period"
    )
    demo.set_defaults(handler=_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
