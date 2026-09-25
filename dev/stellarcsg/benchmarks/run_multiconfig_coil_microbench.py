"""Qualify the local swept kernel on each retained stellarator coil family."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess


REPO = Path(__file__).resolve().parents[3]
ATLAS = Path(r"C:\HTS_transport\plots\stellarcsg_multiconfig_20260831")
WSL_REPO = "/mnt/c/Users/joshu/OneDrive/Documents/ChatGPT/StellarCGS/openmc-stellarcsg"
BINARY = "./build/stellarcsg-instrumented/stellarcsg_file_swept_benchmark"


def main() -> None:
    results = []
    for receipt_path in sorted(ATLAS.glob("*/magnets/compile_receipt.json")):
        receipt = json.loads(receipt_path.read_text())
        case = receipt["case"]
        coil_id = int(receipt["native_csg"]["representative_nonplanar_coil_id"])
        payload = (
            f"/mnt/c/HTS_transport/plots/stellarcsg_multiconfig_20260831/"
            f"{case}/magnets/swept_coils_1cm.h5"
        )
        dataset = f"/coils/coil_{coil_id:03d}"
        command = (
            f'cd "{WSL_REPO}" && taskset -c 2 {BINARY} '
            f"{payload} {dataset} 100"
        )
        print(f"qualify {case} coil {coil_id}", flush=True)
        process = subprocess.run(
            ["wsl.exe", "bash", "-lc", command],
            text=True,
            capture_output=True,
        )
        record = {
            "case": case,
            "label": receipt["label"],
            "family": receipt["family"],
            "source_coil_count": receipt["native_csg"]["coil_count"],
            "representative_coil_id": coil_id,
            "source_sha256": receipt["source"]["sha256"],
            "compiled_payload_sha256": receipt["native_csg"]["payload_sha256"],
            "return_code": process.returncode,
            "stderr": process.stderr,
        }
        if process.returncode == 0:
            record.update(json.loads(process.stdout))
        else:
            record["stdout"] = process.stdout
        results.append(record)
        print(json.dumps({
            "case": case,
            "return_code": process.returncode,
            "oracle_mismatches": record.get("oracle_mismatches"),
        }), flush=True)
    report = {
        "schema": "stellarcsg.multiconfig-coil-local-kernel/v1",
        "date": "2026-08-31",
        "hardware": "Intel Core i9-10850K; one WSL thread pinned to CPU 2",
        "fixture": "most non-planar source coil; standardized 1 cm circular tube",
        "timing_rays_per_case": 1000,
        "independent_oracle_rays_per_case": 100,
        "production_global_reference_calls": 0,
        "results": results,
    }
    output = (
        REPO / "dev/stellarcsg/benchmarks/raw/"
        "multiconfig_coil_local_kernel_20260831.json"
    )
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"output": str(output), "cases": len(results)}, indent=2))


if __name__ == "__main__":
    main()
