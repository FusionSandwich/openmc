from __future__ import annotations

import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

import h5py
import numpy as np


SCRIPT = Path(__file__).with_name("product06_compare_transport.py")
SPEC = importlib.util.spec_from_file_location("product06", SCRIPT)
product06 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(product06)


def _xml_model(directory: Path) -> None:
    directory.mkdir()
    for name, text in {
        "geometry.xml": "<geometry><surface data_file=\"/absolute/coil.h5\"/></geometry>",
        "materials.xml": "<materials><material id=\"1\"/></materials>",
        "tallies.xml": "<tallies><tally id=\"1\"/></tallies>",
        "settings.xml": "<settings><particles>16</particles><batches>1</batches></settings>",
    }.items():
        (directory / name).write_text(text)


def test_prepare_run_folder_preserves_immutable_xml_and_updates_settings(tmp_path) -> None:
    source, run = tmp_path / "source", tmp_path / "run"
    _xml_model(source)
    hashes = product06.prepare_run_folder(source, run, histories=64, seed=17)
    assert (run / "geometry.xml").read_bytes() == (source / "geometry.xml").read_bytes()
    settings = ET.parse(run / "settings.xml")
    assert settings.findtext("particles") == "64"
    assert settings.findtext("seed") == "17"
    assert hashes["geometry.xml"] == product06.sha256(source / "geometry.xml")
    assert product06.validate_absolute_hdf_bindings(source) == ["/absolute/coil.h5"]


def test_statepoint_summary_and_lane_disagreement(tmp_path) -> None:
    statepoint = tmp_path / "statepoint.1.h5"
    with h5py.File(statepoint, "w") as state:
        state["current_batch"] = 1
        state["n_particles"] = 64
        state["n_batches"] = 1
        state["n_realizations"] = 1
        state["global_tallies"] = np.zeros((4, 2))
        state["global_tallies"][3, 1] = 0.2
        state.create_dataset("tallies/tally 1/results", data=np.array([[[1.0]], [[2.0]]]))
        state.create_dataset("tallies/tally 2/results", data=np.array([[[3.0]]]))
    summary = product06.statepoint_summary(statepoint)
    assert summary["cell_flux"] == [1.0, 2.0]
    assert summary["flux_closure_absolute"] == 0.0
    attempts = [
        {"lane": "old", "seed": 17, "completion": "COMPLETE", "statepoint": summary},
        {"lane": "new", "seed": 17, "completion": "COMPLETE", "statepoint": {**summary, "global_flux": 3.1}},
        {"lane": "old", "seed": 19, "completion": "INCOMPLETE"},
    ]
    compared = product06.compare_attempts(attempts, 1.0e-12)
    assert compared[0]["status"] == "CANDIDATE_DISAGREEMENT"
    assert compared[1]["status"] == "BLOCKED_INCOMPLETE"
