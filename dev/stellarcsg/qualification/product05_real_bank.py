"""Freeze hit-rich coil031 rays from source controls, without candidate tuning."""
import csv
import hashlib
import json
from pathlib import Path
import h5py
import numpy as np


def main():
    root = Path(__file__).resolve().parents[3]
    out = root / "dev/stellarcsg/reports/product05/real-bank"
    out.mkdir(parents=True, exist_ok=False)
    payload = root / "dev/stellarcsg/reports/recovery04/wistell-coils-1cm.h5"
    source_hash = hashlib.sha256(payload.read_bytes()).hexdigest()
    with h5py.File(payload) as f:
        group = f["/coils/coil_031"]
        controls = np.asarray(group["centerline_coefficients"])
        r = float(group["major_radius_coefficients"][0])
        if not (np.all(group["major_radius_coefficients"][:] == r)
                and np.all(group["minor_radius_coefficients"][:] == r)):
            raise ValueError("constant circular section required")
    header = "id,geometry,coefficient_hash,source_sha256,category,heldout,expected,expected_distance,group,ox,oy,oz,dx,dy,dz".split(",")
    rows = []
    for i in range(32):
        # Off-knot samples distributed over the entire finite centerline.
        q = len(controls) * (i + .371) / 32
        index, u = int(q), q % 1
        p = controls[(np.arange(4) + index - 1) % len(controls)]
        weights = np.array([(1-u)**3, 3*u**3-6*u*u+4,
                            -3*u**3+3*u*u+3*u+1, u**3]) / 6
        deriv = np.array([-3*(1-u)**2, 9*u*u-12*u,
                          -9*u*u+6*u+3, 3*u*u]) / 6
        c, tangent = weights @ p, deriv @ p
        tangent /= np.linalg.norm(tangent)
        axis = np.eye(3)[np.argmin(np.abs(tangent))]
        normal = np.cross(tangent, axis)
        normal /= np.linalg.norm(normal)
        cases = [("entry_near", c + 1.002*r*normal, -normal),
                 ("entry", c + 1.5*r*normal, -normal),
                 ("interior_exit", c + .4*r*normal, normal),
                 ("center_exit", c, -normal),
                 ("grazing_stress", c + r*normal - .2*r*tangent, tangent)]
        for category, origin, direction in cases:
            rows.append([f"real{i:02d}_{category}", "wistell_coil031", "6d8dd682de8c0bfe",
                         source_hash, category, 0, "reference_required", "", "",
                         *map(lambda v: format(float(v), ".17g"), origin),
                         *map(lambda v: format(float(v), ".17g"), direction)])
    keys = {(r[1], *r[9:]) for r in rows}
    if len(keys) != 160:
        raise RuntimeError("nonunique queries")
    with (out / "rays.csv").open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    (out / "manifest.json").write_text(json.dumps({
        "schema": "stellarcsg.real-stress/v1", "count": len(rows),
        "bank_sha256": hashlib.sha256((out / "rays.csv").read_bytes()).hexdigest(),
        "payload_sha256": source_hash, "nominal_radius_cm": r,
        "section_assumption": "standardized circular test envelope; not source winding pack",
        "generation": "32 off-knot source-cubic samples, 5 geometric constructions each",
        "oracle_status": "reference required; constructed distances are not reference roots",
        "held_out_configuration": False,
        "performance_claim": "stress coverage, not realistic distributed transport"}, indent=2))
    print(out)


if __name__ == "__main__":
    main()
