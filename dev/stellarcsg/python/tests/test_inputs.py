from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest

from stellarcsg.inputs import (
    periodic_surface_from_vmec_arrays,
    read_makegrid_coils,
    read_vmec_surface,
    write_coil_collection_hdf5,
)


def simple_vmec_arrays(nfp: int = 5):
    # m=0 major radius plus m=1 circular minor radius. xn already carries NFP.
    return {
        "nfp": np.asarray(nfp),
        "xm": np.asarray([0.0, 1.0]),
        "xn": np.asarray([0.0, 0.0]),
        "rmnc": np.asarray([[4.5, 0.8], [5.0, 1.0]]),
        "zmns": np.asarray([[0.0, 0.8], [0.0, 1.0]]),
    }


def test_vmec_arrays_compile_exact_torus() -> None:
    surface = periodic_surface_from_vmec_arrays(
        simple_vmec_arrays(), name="test", surface_index=-1,
        n_theta=48, n_phi=32, length_scale_to_cm=100.0)
    assert surface.n_field_periods == 5
    assert abs(surface.evaluate(np.asarray([600.0, 0.0, 0.0]))) < 2.0e-8
    assert surface.evaluate(np.asarray([500.0, 0.0, 0.0])) < 0.0
    points = surface.position(
        np.asarray([0.0, np.pi / 2]), np.asarray([0.0, 0.1]))
    np.testing.assert_allclose(surface.evaluate(points), 0.0, atol=2.0e-8)


def test_vmec_file_hdf5_fixture(tmp_path: Path) -> None:
    path = tmp_path / "wout_fixture.nc4"
    with h5py.File(path, "w") as h5:
        for key, value in simple_vmec_arrays(4).items():
            h5.create_dataset(key, data=value)
    surface = read_vmec_surface(path, n_theta=32, n_phi=24, units="m")
    assert surface.n_field_periods == 4
    assert surface.source_metadata["source_sha256"].startswith("sha256:")
    assert abs(surface.evaluate(np.asarray([600.0, 0.0, 0.0]))) < 5.0e-8


def test_vmec_asymmetric_terms() -> None:
    arrays = simple_vmec_arrays(3)
    arrays["rmns"] = np.asarray([[0.0, 0.0], [0.0, 0.04]])
    arrays["zmnc"] = np.asarray([[0.0, 0.0], [0.0, 0.03]])
    surface = periodic_surface_from_vmec_arrays(
        arrays, n_theta=48, n_phi=32, length_scale_to_cm=100.0)
    assert surface.source_metadata["asymmetric_terms_present"] is True
    assert np.all(np.isfinite(surface.position(0.7, 0.2)))


def test_makegrid_two_coils_and_hdf5(tmp_path: Path) -> None:
    path = tmp_path / "coils.txt"
    path.write_text("""periods 5
begin filament
mirror NIL
1 0 0 100000 coil-A
0 1 0 100000 coil-A
-1 0 0 100000 coil-A
0 -1 0 100000 coil-A
1 0 0 0 coil-A
2 0 0 -50000 coil-B
0 2 0 -50000 coil-B
-2 0 0 -50000 coil-B
0 -2 0 -50000 coil-B
2 0 0 0 coil-B
end
""")
    coils = read_makegrid_coils(path, units="m")
    assert len(coils) == 2
    assert coils[0].name == "coil-A"
    assert coils[0].current_a == 100000
    assert coils[1].current_a == -50000
    np.testing.assert_allclose(coils[0].xyz_cm[0], [100.0, 0.0, 0.0])
    assert coils[0].length_cm > 500.0
    output = tmp_path / "coils.h5"
    write_coil_collection_hdf5(output, coils)
    with h5py.File(output, "r") as h5:
        assert h5.attrs["filetype"] == "stellarcsg-coils"
        assert h5["coils/0000/xyz_cm"].shape == (4, 3)


def test_makegrid_rejects_current_change(tmp_path: Path) -> None:
    path = tmp_path / "bad.txt"
    path.write_text("0 0 0 1 a\n1 0 0 2 a\n0 1 0 1 a\n-1 0 0 1 a\n0 0 0 0 a\n")
    with pytest.raises(ValueError, match="current changes"):
        read_makegrid_coils(path, units="cm")
