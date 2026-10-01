"""Actual-file forgeries against the integration auditor, no transport launches."""
import argparse
import copy
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import numpy as np

from audit_openmc_integration import load, read, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.report / "plasma-native-mesh"
    original = read(source / "receipt.json")
    wrapper = read(args.report / "campaign-progress.json")[0]
    load(source, wrapper)
    results = []
    for name in ("closure", "sample_hash", "mean", "uncertainty", "runtime", "missing_output",
                 "boolean_exit", "nonzero_exit", "failure_log", "XML_hash_map",
                 "source_constraint", "source_position", "source_direction", "mesh_geometry"):
        with tempfile.TemporaryDirectory(prefix="integration-negative-") as temporary:
            directory = Path(temporary) / source.name
            directory.mkdir()
            for p in source.iterdir():
                if p.is_file() and p.name != "receipt.json":
                    (directory / p.name).symlink_to(p.resolve())
            log = directory.parent / f"{directory.name}.txt"
            log.symlink_to((args.report / log.name).resolve())
            value, status = copy.deepcopy(original), copy.deepcopy(wrapper)

            def replace_bytes(path, data):
                path.unlink()
                path.write_bytes(data)

            def rebind_input(filename):
                digest = sha(directory / filename)
                value["output_hashes"][filename] = value["xml_hashes"][filename] = digest
                launch = read(directory / "launch.json")
                launch["xml_hashes"][filename] = digest
                replace_bytes(directory / "launch.json", json.dumps(launch).encode())
                value["output_hashes"]["launch.json"] = sha(directory / "launch.json")

            if name == "closure":
                value["closure_max_abs"]["2"] += .1
            elif name == "sample_hash":
                value["sampling"]["sha256"] = "0" * 64
            elif name == "mean":
                value["tallies"]["1"]["mean"][0][0][0] += 1
            elif name == "uncertainty":
                value["tallies"]["1"]["std_dev"][0][0][0] += 1
            elif name == "runtime":
                value["runtime_s"]["transport"] *= 2
            elif name == "missing_output":
                value["output_hashes"].pop("statepoint.5.h5")
            elif name == "boolean_exit":
                status["exit_code"] = False
            elif name == "nonzero_exit":
                status["exit_code"] = 1
            elif name == "failure_log":
                replace_bytes(log, log.read_bytes() + b"\nlost particle\n")
                status["log_sha256"] = sha(log)
            elif name == "XML_hash_map":
                value["xml_hashes"]["settings.xml"] = "0" * 64
            elif name == "source_constraint":
                p = directory / "settings.xml"
                tree = ET.parse(p)
                node = tree.getroot().find("source")
                node.remove(node.find("constraints"))
                replace_bytes(p, ET.tostring(tree.getroot()))
                rebind_input(p.name)
            elif name in ("source_position", "source_direction"):
                p = directory / "sampled-source.npy"
                sites = np.load(p, allow_pickle=False)
                sites["r" if name == "source_position" else "u"][0] = [0., 0., 0.]
                p.unlink()
                np.save(p, sites, allow_pickle=False)
                value["output_hashes"][p.name] = value["sampling"]["sha256"] = sha(p)
            elif name == "mesh_geometry":
                p = directory / "tallies.xml"
                tree = ET.parse(p)
                tree.getroot().find("mesh[@id='101']/upper_right").text = "151 151 151"
                replace_bytes(p, ET.tostring(tree.getroot()))
                rebind_input(p.name)
            (directory / "receipt.json").write_text(json.dumps(value))
            status["receipt_sha256"] = sha(directory / "receipt.json")
            try:
                load(directory, status)
            except ValueError as error:
                results.append(dict(control=name, state="REJECTED", reason=str(error)))
            else:
                raise AssertionError(f"forgery accepted: {name}")
    result = dict(controls=results, audit_sha256=sha(Path(__file__).with_name("audit_openmc_integration.py")),
                  test_sha256=sha(__file__), baseline_receipt_sha256=sha(source / "receipt.json"))
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(dict(state="ALL_FORGERIES_REJECTED", controls=len(results))))


if __name__ == "__main__":
    main()
