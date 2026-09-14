"""Serial local exclusion experiment; never modifies an environment or promotes a solver."""
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[3]
    out = root / "build" / (sys.argv[1] if len(sys.argv) > 1 else "product05-cover-01")
    out.mkdir(parents=True, exist_ok=False)
    q = root / "dev/stellarcsg/qualification"
    old = root.parent / "stellarcsg-fast-recovery-04"
    lib = old / "build/recovery-04-baseline/libstellarcsg_reference.a"
    bank = q / "recovery04_frozen_bank.csv"
    coils = root / "dev/stellarcsg/reports/recovery04/wistell-coils-1cm.h5"
    receipt = {"acquisition_bytes": 0, "parallelism": 1, "commands": [],
               "bank_sha256": sha(bank), "coils_sha256": sha(coils),
               "library_sha256": sha(lib), "source_sha256": {
                   p.name: sha(p) for p in q.glob("product05*.*")}}

    def run(args, name):
        receipt["commands"].append(args)
        with (out / f"{name}.stdout").open("w") as stdout, (out / f"{name}.stderr").open("w") as stderr:
            result = subprocess.run(args, stdout=stdout, stderr=stderr, timeout=120)
        receipt[name + "_exit_code"] = result.returncode
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2))
        if result.returncode:
            raise RuntimeError(f"{name} failed; inspect retained logs")

    base = ["g++", "-std=c++17", "-O3", "-ffp-contract=off", "-fno-fast-math",
            "-I" + str(root / "dev/stellarcsg/include")]
    run(base + [str(q / "product05_cover_test.cpp"), "-o", str(out / "test")], "build-test")
    run([str(out / "test")], "test")
    run(base + ["-DSTELLARCSG_HAS_HDF5", "-I/usr/include/hdf5/serial",
                str(q / "product05_interval_cover.cpp"), str(lib),
                "-L/usr/lib/x86_64-linux-gnu/hdf5/serial", "-lhdf5_hl", "-lhdf5",
                "-o", str(out / "probe")], "build-probe")
    run([str(out / "probe"), str(bank), str(coils)], "probe")
    rows = [json.loads(s) for s in (out / "probe.stdout").read_text().splitlines()]
    reference = {r["id"]: r for r in map(json.loads, (root / "dev/stellarcsg/reports/recovery04/frozen-final-off/exact_reference-0.jsonl").read_text().splitlines()) if "id" in r}
    false_exclusions = [r["id"] for r in rows if r["state"] == "ROOT_FREE" and reference[r["id"]]["candidate_found"]]
    receipt.update({"probe_sha256": sha(out / "probe"), "query_count": len(rows),
                    "root_free": sum(r["state"] == "ROOT_FREE" for r in rows),
                    "unresolved": sum(r["state"] == "UNRESOLVED" for r in rows),
                    "false_exclusions_against_exact": false_exclusions,
                    "single_run_mean_ns": statistics.mean(r["probe_ns"] for r in rows),
                    "claim": "experimental_exclusion_only_not_distance_or_transport"})
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2))
    if false_exclusions or len(rows) != 160:
        raise RuntimeError("incomplete or false exclusion")


if __name__ == "__main__":
    main()
