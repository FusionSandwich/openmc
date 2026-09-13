"""Finite-coil compiler admissibility and rigid-transform regressions."""

from dataclasses import replace
import hashlib
import json

import h5py
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from stellarcsg.coil import (
    SweptSplineData, _rotation_minimizing_frame, write_swept_collection,
)
from stellarcsg.spline import sample_periodic_cubic


@pytest.fixture
def points():
    angle = np.arange(64) * 2.0 * np.pi / 64
    radius = 12.0 + 0.8 * np.cos(3.0 * angle)
    return np.column_stack((radius * np.cos(angle), radius * np.sin(angle),
                            1.2 * np.sin(2.0 * angle)))


@pytest.fixture
def coil(points):
    return SweptSplineData.from_centerline(
        17, points, major_radius_cm=0.25, minor_radius_cm=0.16,
        sample_count=64, source_metadata={"fixture": "nonplanar elliptical coil"},
    )


def test_rigid_transform_preserves_finite_surface_and_frame(coil):
    rotation = Rotation.from_rotvec([0.37, -0.61, 0.29]).as_matrix()
    translation = np.array([23.0, -7.0, 4.0])
    transformed = coil.rigid_transform(rotation, translation)
    arc = coil.length_cm * np.r_[0.0, 1.0, np.linspace(-0.07, 1.08, 257)]
    source = coil.frame(arc)
    target = transformed.frame(arc)
    np.testing.assert_allclose(target[0], source[0] @ rotation.T + translation,
                               atol=3e-13, rtol=0.0)
    for original, result in zip(source[1:], target[1:]):
        np.testing.assert_allclose(result, original @ rotation.T, atol=3e-13, rtol=0.0)
    # Check actual elliptical boundary points, not only centerline samples.
    alpha = np.linspace(0.0, 2.0 * np.pi, arc.size)
    angle = 2.0 * np.pi * arc / coil.length_cm
    major = sample_periodic_cubic(coil.major_radius_coefficients_cm, angle)[0]
    minor = sample_periodic_cubic(coil.minor_radius_coefficients_cm, angle)[0]
    before = source[0] + (major * np.cos(alpha))[:, None] * source[2] + (minor * np.sin(alpha))[:, None] * source[3]
    after = target[0] + (major * np.cos(alpha))[:, None] * target[2] + (minor * np.sin(alpha))[:, None] * target[3]
    np.testing.assert_allclose(after, before @ rotation.T + translation, atol=3e-13, rtol=0.0)
    for component in target:
        np.testing.assert_allclose(component[0], component[1], atol=3e-13, rtol=0.0)
    assert transformed.coil_id == coil.coil_id
    assert transformed.length_cm == coil.length_cm
    np.testing.assert_array_equal(transformed.major_radius_coefficients_cm, coil.major_radius_coefficients_cm)
    np.testing.assert_array_equal(transformed.minor_radius_coefficients_cm, coil.minor_radius_coefficients_cm)
    assert transformed.source_metadata["rigid_transform"]["parent_content_id"] == coil.content_id
    assert "rigid_transform" not in coil.source_metadata
    assert transformed.content_id != coil.content_id
    inverse = transformed.rigid_transform(rotation.T, -rotation.T @ translation)
    np.testing.assert_allclose(inverse.centerline_coefficients_cm, coil.centerline_coefficients_cm,
                               atol=2e-14, rtol=0.0)
    for original, result in zip(source, inverse.frame(arc)):
        np.testing.assert_allclose(result, original, atol=3e-13, rtol=0.0)


def test_transformed_hdf5_payload_identity(coil, tmp_path):
    transformed = coil.rigid_transform(Rotation.from_euler("xyz", [17, 24, -51], degrees=True).as_matrix(),
                                      [1.0, 2.0, -3.0])
    path = tmp_path / "coil.h5"
    write_swept_collection(path, [transformed])
    names = ("centerline_coefficients", "normal_coefficients", "binormal_coefficients",
             "major_radius_coefficients", "minor_radius_coefficients")
    with h5py.File(path, "r") as handle:
        group = handle["coils/coil_017"]
        metadata = group.attrs["canonical_metadata_json"]
        digest = hashlib.sha256(metadata.encode())
        arrays = [group[name][...] for name in names]
        for values in arrays:
            digest.update(np.asarray(values, dtype="<f8", order="C").tobytes())
        assert "sha256:" + digest.hexdigest() == group.attrs["content_id"] == transformed.content_id
        assert group.attrs["surface_type"] == "swept-elliptical-cubic"
        restored = SweptSplineData(
            coil_id=int(group.attrs["coil_id"]), centerline_coefficients_cm=arrays[0],
            normal_coefficients=arrays[1], binormal_coefficients=arrays[2],
            major_radius_coefficients_cm=arrays[3], minor_radius_coefficients_cm=arrays[4],
            length_cm=float(group.attrs["length_cm"]),
            source_metadata=json.loads(metadata)["source_metadata"],
            content_id=group.attrs["content_id"],
        )
    assert restored.computed_content_id() == transformed.content_id
    for before, after in zip(transformed.frame(2.7), restored.frame(2.7)):
        np.testing.assert_array_equal(before, after)


@pytest.mark.parametrize("radius", [np.nan, np.inf, -np.inf, 0.0, -1.0])
@pytest.mark.parametrize("section", ["major_radius_cm", "minor_radius_cm"])
def test_invalid_section_rejected(points, radius, section):
    kwargs = {"major_radius_cm": 0.25, section: radius}
    with pytest.raises(ValueError, match="finite and positive"):
        SweptSplineData.from_centerline(1, points, **kwargs)


@pytest.mark.parametrize("count", [0, -1, 7, 8.5, True])
def test_invalid_sample_count_rejected(points, count):
    with pytest.raises(ValueError, match="sample_count"):
        SweptSplineData.from_centerline(1, points, major_radius_cm=0.25, sample_count=count)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_nonfinite_centerline_rejected(points, value):
    points[3, 2] = value
    with pytest.raises(ValueError, match="finite"):
        SweptSplineData.from_centerline(1, points, major_radius_cm=0.25)


def test_duplicate_centerline_rejected(points):
    points[4] = points[3]
    with pytest.raises(ValueError, match="duplicate"):
        SweptSplineData.from_centerline(1, points, major_radius_cm=0.25)


def test_ambiguous_frame_rejected():
    with pytest.raises(ValueError, match="antiparallel"):
        _rotation_minimizing_frame(np.array([[1., 0., 0.], [-1., 0., 0.]]))


def test_invalid_compiled_data_rejected(coil):
    with pytest.raises(ValueError, match="finite"):
        replace(coil, normal_coefficients=np.full((64, 3), np.nan))
    with pytest.raises(ValueError, match="parallel"):
        replace(coil, normal_coefficients=np.zeros((64, 3)))
    with pytest.raises(ValueError, match="tangent"):
        replace(coil, centerline_coefficients_cm=np.zeros((64, 3)))
    with pytest.raises(ValueError, match="finite"):
        replace(coil, length_cm=np.inf)
    with pytest.raises(ValueError, match="integer"):
        replace(coil, coil_id=1.5)
    with pytest.raises(ValueError, match="finite"):
        coil.frame(np.nan)


@pytest.mark.parametrize("rotation", [np.diag([1., 1., -1.]), np.eye(3) * 2.,
                                      np.zeros((2, 2)), np.full((3, 3), np.nan)])
def test_invalid_rotation_rejected(coil, rotation):
    with pytest.raises(ValueError, match="rotation"):
        coil.rigid_transform(rotation)


@pytest.mark.parametrize("translation", [[0., 1.], [0., np.inf, 0.]])
def test_invalid_translation_rejected(coil, translation):
    with pytest.raises(ValueError, match="translation"):
        coil.rigid_transform(np.eye(3), translation)


def test_mutated_payload_rejected_before_transform_or_write(coil, tmp_path):
    coil.centerline_coefficients_cm[0, 0] += 0.1
    with pytest.raises(ValueError, match="content hash"):
        coil.rigid_transform(np.eye(3))
    path = tmp_path / "protected.h5"
    path.write_bytes(b"existing bytes")
    with pytest.raises(ValueError, match="content hash"):
        write_swept_collection(path, [coil])
    assert path.read_bytes() == b"existing bytes"


def test_duplicate_coil_identity_rejected_before_write(coil, tmp_path):
    with pytest.raises(ValueError, match="unique coil IDs"):
        write_swept_collection(tmp_path / "coils.h5", [coil, coil])
