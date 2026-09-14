"""Generate and initialize a bounded clipped diagnostic using a retained reference.

Never interpreted as recovered-candidate or periodic transport qualification.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "dev/stellarcsg/python"))
from stellarcsg.one_period import prepare_one_period_model
from stellarcsg.surface import PeriodicRadialSurfaceData
from stellarcsg.vmec import VmecBoundary
from product05_simple import build


def main():
    out = ROOT / "dev/stellarcsg/reports/product05" / (sys.argv[1] if len(sys.argv)>1 else "model-01")
    out.mkdir(parents=True, exist_ok=False)
    data = ROOT / "dev/stellarcsg/test_data"
    args = dict(vmec_file=data / "wistell_d/wout_wistell-d.nc",
                filament_file=data / "wistell_d/coils.wistell-d",
                swept_coils_file=ROOT / "dev/stellarcsg/reports/recovery04/wistell-coils-1cm.h5",
                sector_manifest_file=ROOT / "dev/stellarcsg/reports/recovery04/sector-1cm.json")
    result = {"status": "unqualified_clipped_diagnostic", "acquisition_bytes": 0}
    try:
        prepare_one_period_model(**args)
        result["default_periodic_preparation"] = "UNEXPECTED_ACCEPTANCE"
    except ValueError as error:
        result["default_periodic_preparation"] = str(error)
    try:
        plan = prepare_one_period_model(**args, symmetry_policy="record-approximation")
    except ValueError as error:
        result["model_preparation_failure"] = str(error)
        (out / "receipt.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        raise
    plan.export(out / "plan")
    plan.export_openmc_diagnostic(out / "xml", diagnostic_clipped=True)
    build(out / "simple")
    vmec = VmecBoundary.from_wout(args["vmec_file"])
    theta, phi = np.meshgrid(2*np.pi*(np.arange(96)+.371)/96,
                            (np.pi/2)*(np.arange(48)+.613)/48, indexing="ij")
    points = vmec.position_cm(theta, phi)
    axis_r, axis_z, _, _ = plan.plasma.axis(phi)
    rho = np.hypot(np.hypot(points[...,0], points[...,1])-axis_r, points[...,2]-axis_z)
    error = np.abs(plan.plasma.evaluate(points))
    result["plasma_sampled_radial_fit"] = {
        "samples": int(error.size), "max_cm": float(error.max()),
        "rms_cm": float(np.sqrt(np.mean(error**2))), "p95_cm": float(np.percentile(error,95)),
        "max_local_radius_fraction": float(np.max(error/rho)),
        "metric": "off-grid VMEC point to compiled radial surface along its local radius; not two-sided Hausdorff certification",
        "normal_volume_clearance": "NOT_MEASURED"}
    try:
        generic = VmecBoundary.from_wout(data / "parastell_generic/wout_vmec.nc")
        grid, azimuth, _, _ = generic.surface_grid_cm(64,32)
        PeriodicRadialSurfaceData.from_surface_grid(name="heldout",xyz_cm=grid,phi=azimuth,n_field_periods=generic.n_field_periods)
        result["heldout_plasma_import"] = "COMPILED_NOT_FIDELITY_QUALIFIED"
    except ValueError as error:
        result["heldout_plasma_import"] = str(error)
    binary = Path("/mnt/d/codex-verification/stellarcsg-20260913-03/native/bin/openmc")
    library = binary.parents[1] / "lib/libopenmc.so"
    result["binary_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
    result["library_sha256"] = hashlib.sha256(library.read_bytes()).hexdigest()
    if result["library_sha256"] != "451b21536d4178a81c4ec5c9a44f6e04eac194c58c87a639d643441ff2717d48":
        raise RuntimeError("retained reference library changed")
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENMC_CROSS_SECTIONS="/mnt/c/Users/joshu/Documents/2026_DPA/openc-hts-dpa/.data/openmc/cross_sections.xml", LD_LIBRARY_PATH=str(library.parent))
    command = [str(binary), "-g", "-n", "16"]
    result["command"] = command
    result["solver_lane"] = "retained dc76/5ed exact reference, NOT recovered candidate"
    (out / "receipt.json").write_text(json.dumps(result, indent=2))
    with (out / "transport.stdout").open("w") as stdout, (out / "transport.stderr").open("w") as stderr:
        try:
            run = subprocess.run(command,cwd=out / "xml",env=env,stdout=stdout,stderr=stderr,timeout=120)
            result["transport_exit_code"] = run.returncode
        except subprocess.TimeoutExpired:
            result["transport_exit_code"] = "TIMEOUT_120S"
    (out / "receipt.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
