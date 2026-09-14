#!/usr/bin/env python3
"""Prepare one-period WISTELL-D receipts and clipped native-surface XML."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from stellarcsg.one_period import prepare_one_period_model


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vmec", type=Path, required=True)
    parser.add_argument("--filaments", type=Path, required=True)
    parser.add_argument("--swept-coils", type=Path, required=True)
    parser.add_argument("--sector-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--symmetry-policy", choices=("reject", "record-approximation"), default="reject")
    parser.add_argument("--seam-tolerance-cm", type=float, default=1.0e-8)
    parser.add_argument("--diagnostic-clipped", action="store_true", help="write a nonperiodic vacuum-sector XML model using native swept-coil surfaces")
    args = parser.parse_args()
    plan = prepare_one_period_model(vmec_file=args.vmec, filament_file=args.filaments,
        swept_coils_file=args.swept_coils, sector_manifest_file=args.sector_manifest,
        symmetry_policy=args.symmetry_policy, seam_tolerance_cm=args.seam_tolerance_cm)
    files = plan.export_openmc_diagnostic(args.output, diagnostic_clipped=True) if args.diagnostic_clipped else plan.export(args.output)
    print(json.dumps({"status": "DIAGNOSTIC_CLIPPED_NATIVE_SWEPT_MODEL_NOT_TRANSPORT_QUALIFIED" if args.diagnostic_clipped else "PREPARED_NOT_TRANSPORT_QUALIFIED", "files": {k: str(v) for k, v in files.items()},
                      "members": len(plan.members), "approximation_record": plan.approximation_record}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
