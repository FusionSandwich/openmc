from __future__ import annotations

import json

from stellarcsg.cli import main


def test_demo_cli(tmp_path) -> None:
    output = tmp_path / "demo"
    result = main(
        [
            "demo",
            "--output-dir",
            str(output),
            "--mesh-theta-bins",
            "12",
            "--mesh-phi-bins",
            "8",
        ]
    )
    assert result == 0
    assert (output / "compiled_geometry.h5").exists()
    assert (output / "tally_mesh.h5").exists()
    assert (output / "tally_mesh.vtk").exists()
    report = json.loads((output / "validation_report.json").read_text())
    assert report["mesh"]["elements"] == (1 + 2 + 2) * 12 * 8
