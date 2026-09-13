"""Prepare lossless hex binary64 replay input; never select rays by outcomes."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("capture", type=Path)
p.add_argument("output", type=Path)
a = p.parse_args()
raw = a.capture.read_bytes()
rows = [json.loads(line) for line in raw.splitlines()]
geometries = [r for r in rows if r["kind"] == "geometry"]
with a.output.open("x", encoding="ascii") as f:
    print(len(geometries), file=f)
    for geometry in geometries:
        rays = [r for r in rows if r["kind"] == "ray" and r["shape"] == geometry["shape"]]
        print(geometry["shape"], len(geometry["controls"]), len(rays), file=f)
        print(float(geometry["radius"]).hex(), file=f)
        for control in geometry["controls"]:
            print(*(float(x).hex() for x in control), file=f)
        for ray in rays:
            print(ray["index"], *(float(x).hex() for x in ray["origin"] + ray["direction"]), file=f)
print(json.dumps({"source_sha256": hashlib.sha256(raw).hexdigest(),
                  "replay_sha256": hashlib.sha256(a.output.read_bytes()).hexdigest(),
                  "geometry_count": len(geometries),
                  "ray_count": sum(r["kind"] == "ray" for r in rows)}))
