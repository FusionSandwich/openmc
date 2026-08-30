"""Compile and independently qualify a VMEC LCFS coefficient payload."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from stellarcsg import (
    PeriodicRadialSurfaceData,
    VmecBoundary,
    compile_normal_build,
    write_surface_collection,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _model_geometry(surface, theta, phi):
    radius, radius_theta, radius_phi = surface.radius(theta, phi)
    axis_r, axis_z, axis_r_phi, axis_z_phi = surface.axis(phi)
    ct, st = np.cos(theta), np.sin(theta)
    cp, sp = np.cos(phi), np.sin(phi)
    major = axis_r + radius * ct
    height = axis_z + radius * st
    major_theta = radius_theta * ct - radius * st
    height_theta = radius_theta * st + radius * ct
    major_phi = axis_r_phi + radius_phi * ct
    height_phi = axis_z_phi + radius_phi * st
    position = np.stack((major * cp, major * sp, height), axis=-1)
    dtheta = np.stack(
        (major_theta * cp, major_theta * sp, height_theta), axis=-1
    )
    dphi = np.stack(
        (
            major_phi * cp - major * sp,
            major_phi * sp + major * cp,
            height_phi,
        ),
        axis=-1,
    )
    return position, dtheta, dphi


def _integrals(position, dtheta, dphi, nfp):
    area_vector = np.cross(dphi, dtheta)
    jacobian = np.linalg.norm(area_vector, axis=-1)
    dtheta_step = 2.0 * np.pi / position.shape[0]
    dphi_step = 2.0 * np.pi / (nfp * position.shape[1])
    area = float(np.sum(jacobian) * dtheta_step * dphi_step * nfp)
    volume = float(
        abs(np.sum(position * area_vector) / 3.0)
        * dtheta_step * dphi_step * nfp
    )
    return area, volume, jacobian, area_vector


def _rotate_z(points, angle):
    result = np.array(points, copy=True)
    c, s = np.cos(angle), np.sin(angle)
    result[..., 0] = c * points[..., 0] - s * points[..., 1]
    result[..., 1] = s * points[..., 0] + c * points[..., 1]
    return result


def qualify(args):
    source_path = Path(args.wout)
    vmec = VmecBoundary.from_wout(source_path)
    source_grid, phi, _, _ = vmec.surface_grid_cm(
        args.fit_theta, args.fit_phi
    )
    try:
        surface = PeriodicRadialSurfaceData.from_surface_grid(
            name=args.name,
            xyz_cm=source_grid,
            phi=phi,
            n_field_periods=vmec.n_field_periods,
            n_theta_coefficients=args.fit_theta,
            source_metadata={
                "kind": "vmec_lcfs",
                "source_path": source_path.name,
                "source_sha256": _sha256(source_path),
                "fit_theta": args.fit_theta,
                "fit_phi": args.fit_phi,
            },
        )
    except ValueError as error:
        message = str(error)
        classification = (
            "REJECT_THETA_FOLD"
            if "theta fold" in message or "geometric-theta fold" in message
            else "FIT_TOLERANCE_NOT_MET"
        )
        result = {
            "schema_version": 1,
            "case": args.name,
            "classification": classification,
            "source": {
                "path": source_path.as_posix(),
                "sha256": _sha256(source_path),
                "n_field_periods": vmec.n_field_periods,
            },
            "compiler_error": message,
            "coefficient_payload": None,
            "plots": [],
        }
        output_json = Path(args.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return 2

    theta_source = 2.0 * np.pi * np.arange(args.check_theta) / args.check_theta
    phi_check = (
        2.0 * np.pi * np.arange(args.check_phi)
        / (vmec.n_field_periods * args.check_phi)
    )
    ts, ps = np.meshgrid(theta_source, phi_check, indexing="ij")
    source_position, source_dtheta, source_dphi = (
        vmec.position_and_derivatives_cm(ts, ps)
    )
    check_axis_r, check_axis_z, _, _ = surface.axis(ps)
    source_major = np.hypot(source_position[..., 0], source_position[..., 1])
    q_r = source_major - check_axis_r
    q_z = source_position[..., 2] - check_axis_z
    geometric_theta = np.unwrap(np.arctan2(q_z, q_r), axis=0)
    source_radius = np.hypot(q_r, q_z)
    fitted_radius = surface.radius(geometric_theta, ps)[0]
    radial_error = np.abs(fitted_radius - source_radius)
    fitted_position = surface.position(geometric_theta, ps)

    source_area, source_volume, source_jacobian, source_area_vector = _integrals(
        source_position, source_dtheta, source_dphi, vmec.n_field_periods
    )
    tg, pg = np.meshgrid(
        2.0 * np.pi * np.arange(args.check_theta) / args.check_theta,
        phi_check,
        indexing="ij",
    )
    model_position, model_dtheta, model_dphi = _model_geometry(surface, tg, pg)
    model_area, model_volume, model_jacobian, _ = _integrals(
        model_position, model_dtheta, model_dphi, vmec.n_field_periods
    )
    _, fitted_source_dtheta, fitted_source_dphi = _model_geometry(
        surface, geometric_theta, ps
    )
    fitted_normal = np.cross(fitted_source_dphi, fitted_source_dtheta)
    source_normal = source_area_vector
    fitted_normal /= np.linalg.norm(fitted_normal, axis=-1)[..., None]
    source_normal /= np.linalg.norm(source_normal, axis=-1)[..., None]
    normal_angle = np.degrees(
        np.arccos(np.clip(np.sum(source_normal * fitted_normal, axis=-1), -1.0, 1.0))
    )

    theta_step = np.diff(
        np.concatenate(
            (geometric_theta, geometric_theta[:1] + 2.0 * np.pi), axis=0
        ),
        axis=0,
    )
    minimum_theta_step = float(np.min(theta_step))
    minimum_radius = float(np.min(source_radius))
    seam_phi = 2.0 * np.pi / vmec.n_field_periods
    seam_theta = 2.0 * np.pi * np.arange(args.check_theta) / args.check_theta
    source_start = vmec.position_cm(seam_theta, np.zeros_like(seam_theta))
    source_end = vmec.position_cm(
        seam_theta, np.full_like(seam_theta, seam_phi)
    )
    model_start = surface.position(seam_theta, np.zeros_like(seam_theta))
    model_end = surface.position(seam_theta, np.full_like(seam_theta, seam_phi))
    source_seam = float(np.max(np.linalg.norm(
        source_end - _rotate_z(source_start, seam_phi), axis=-1
    )))
    model_seam = float(np.max(np.linalg.norm(
        model_end - _rotate_z(model_start, seam_phi), axis=-1
    )))

    classification = "PASS_SINGLE_CHART"
    if np.min(source_major) <= 1.0e-10 * surface.characteristic_length:
        classification = "REJECT_R_ZERO_BOUND"
    elif minimum_theta_step <= 0.0:
        classification = "REJECT_THETA_FOLD"
    elif min(float(np.min(source_jacobian)), float(np.min(model_jacobian))) <= 0.0:
        classification = "REJECT_PHI_FOLD"
    elif float(np.max(radial_error)) > args.fit_tolerance_cm:
        classification = "FIT_TOLERANCE_NOT_MET"

    boundaries = [surface]
    layer_error = None
    if classification == "PASS_SINGLE_CHART" and args.layers:
        try:
            boundaries = compile_normal_build(
                surface,
                [
                    ("first_wall", 2.0),
                    ("breeder", 40.0),
                    ("back_wall", 2.0),
                    ("shield", 30.0),
                    ("vessel", 5.0),
                ],
                sample_factor=1,
            )
        except ValueError as error:
            layer_error = str(error)

    output_h5 = Path(args.output_h5)
    output_h5.parent.mkdir(parents=True, exist_ok=True)
    write_surface_collection(output_h5, boundaries, overwrite_file=True)
    plot_dir = Path(args.plot_dir)
    plot_dir.mkdir(parents=True, exist_ok=True)

    slice_degrees = [0.0, 22.5, 45.0, 67.5, 90.0]
    figure, axes = plt.subplots(1, 5, figsize=(16, 3.4), constrained_layout=True)
    line_theta = np.linspace(0.0, 2.0 * np.pi, 513)
    for axis, degrees in zip(axes, slice_degrees):
        slice_phi = np.radians(degrees)
        source_line = vmec.position_cm(
            line_theta, np.full_like(line_theta, slice_phi)
        )
        source_R = np.hypot(source_line[:, 0], source_line[:, 1])
        axis.plot(source_R, source_line[:, 2], "k.", ms=1.0, label="VMEC")
        for index, boundary in enumerate(boundaries):
            model_line = boundary.position(
                line_theta, np.full_like(line_theta, slice_phi)
            )
            axis.plot(
                np.hypot(model_line[:, 0], model_line[:, 1]),
                model_line[:, 2],
                lw=1.0,
                label="spline" if index == 0 else boundary.name,
            )
        axis.set_title(f"{degrees:g}°")
        axis.set_aspect("equal")
        axis.set_xlabel("R [cm]")
    axes[0].set_ylabel("Z [cm]")
    axes[-1].legend(fontsize=6)
    figure.savefig(plot_dir / "poloidal_slices.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(7, 4), constrained_layout=True)
    image = axis.imshow(
        radial_error,
        origin="lower",
        aspect="auto",
        extent=(0.0, 360.0 / vmec.n_field_periods, 0.0, 360.0),
    )
    axis.set_xlabel("toroidal angle [deg]")
    axis.set_ylabel("VMEC poloidal parameter [deg]")
    figure.colorbar(image, ax=axis, label="Cartesian radial error [cm]")
    figure.savefig(plot_dir / "fit_error_heatmap.png", dpi=180)
    plt.close(figure)

    view_points = model_position[:: max(1, args.check_theta // 64),
                                 :: max(1, args.check_phi // 64)]
    figure = plt.figure(figsize=(12, 4), constrained_layout=True)
    ax_top = figure.add_subplot(131)
    ax_side = figure.add_subplot(132)
    ax_iso = figure.add_subplot(133, projection="3d")
    ax_top.scatter(view_points[..., 0], view_points[..., 1], s=0.3)
    ax_top.set_aspect("equal")
    ax_top.set_title("top")
    ax_side.scatter(view_points[..., 0], view_points[..., 2], s=0.3)
    ax_side.set_aspect("equal")
    ax_side.set_title("side")
    ax_iso.scatter(
        view_points[..., 0], view_points[..., 1], view_points[..., 2], s=0.2
    )
    ax_iso.set_title("isometric one-period payload")
    figure.savefig(plot_dir / "views.png", dpi=180)
    plt.close(figure)

    result = {
        "schema_version": 1,
        "case": args.name,
        "classification": classification,
        "source": {
            "path": source_path.as_posix(),
            "sha256": _sha256(source_path),
            "n_field_periods": vmec.n_field_periods,
        },
        "coefficient_payload": {
            "path": output_h5.as_posix(),
            "content_id": surface.content_id,
            "dataset": f"/surfaces/{surface.name}",
            "n_theta": surface.n_theta,
            "n_phi": surface.n_phi,
            "layer_content_ids": {item.name: item.content_id for item in boundaries},
        },
        "fit": {
            "independent_points": int(radial_error.size),
            "maximum_cartesian_error_cm": float(np.max(radial_error)),
            "rms_cartesian_error_cm": float(np.sqrt(np.mean(radial_error**2))),
            "p95_cartesian_error_cm": float(np.percentile(radial_error, 95.0)),
            "approximate_hausdorff_error_cm": float(np.max(radial_error)),
            "maximum_normal_angle_deg": float(np.max(normal_angle)),
            "rms_normal_angle_deg": float(np.sqrt(np.mean(normal_angle**2))),
            "surface_area_source_cm2": source_area,
            "surface_area_model_cm2": model_area,
            "surface_area_relative_error": (model_area - source_area) / source_area,
            "volume_source_cm3": source_volume,
            "volume_model_cm3": model_volume,
            "volume_relative_error": (model_volume - source_volume) / source_volume,
            "source_seam_closure_cm": source_seam,
            "model_seam_closure_cm": model_seam,
            "minimum_radius_cm": minimum_radius,
            "minimum_geometric_theta_step_rad": minimum_theta_step,
            "minimum_source_jacobian_cm2": float(np.min(source_jacobian)),
            "minimum_model_jacobian_cm2": float(np.min(model_jacobian)),
            "declared_fit_tolerance_cm": args.fit_tolerance_cm,
        },
        "normal_layers": {
            "requested": bool(args.layers),
            "accepted_boundaries": [item.name for item in boundaries],
            "error": layer_error,
        },
        "plots": [
            (plot_dir / "poloidal_slices.png").as_posix(),
            (plot_dir / "fit_error_heatmap.png").as_posix(),
            (plot_dir / "views.png").as_posix(),
        ],
    }
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if classification == "PASS_SINGLE_CHART" and layer_error is None else 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wout", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--output-h5", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--plot-dir", required=True)
    parser.add_argument("--fit-theta", type=int, default=192)
    parser.add_argument("--fit-phi", type=int, default=96)
    parser.add_argument("--check-theta", type=int, default=257)
    parser.add_argument("--check-phi", type=int, default=129)
    parser.add_argument("--fit-tolerance-cm", type=float, default=0.1)
    parser.add_argument("--layers", action="store_true")
    raise SystemExit(qualify(parser.parse_args()))


if __name__ == "__main__":
    main()
