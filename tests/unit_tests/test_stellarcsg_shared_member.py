"""Identity contract for shared coil acceleration members."""
import h5py
import numpy as np
import pytest

import openmc


def member(identifier=1, **kwargs):
    return openmc.SweptSplineSurface('coils.h5', dataset_prefix='/coils/coil_',
        dataset_start=1, dataset_count=2, member_id=identifier, **kwargs)


@pytest.mark.parametrize('value', [-1, 0, 3, 1.5, True, np.bool_(False)])
def test_invalid_member(value):
    with pytest.raises(ValueError, match='member_id'):
        member(value)


def test_single_dataset_cannot_select_member():
    with pytest.raises(ValueError, match='member_id'):
        openmc.SweptSplineSurface('coils.h5', '/coils/coil_001', 'test', member_id=1)


def test_member_xml_identity_and_union():
    a, b, union = member(1), member(2), member(None)
    assert not a.is_equal(b)
    assert not a.is_equal(union)
    rebuilt = openmc.Surface.from_xml_element(a.to_xml_element())
    assert rebuilt.member_id == 1
    assert rebuilt.is_equal(a)
    geom = openmc.Geometry([openmc.Cell(region=-a), openmc.Cell(region=-b)])
    geom.remove_redundant_surfaces()
    assert len(geom.get_all_surfaces()) == 2


def test_member_hdf5_identity(tmp_path):
    surface = member(2)
    with h5py.File(tmp_path / 'summary_fragment.h5', 'w') as h5:
        group = h5.create_group('surface 12')
        for key, value in {'data_file': 'coils.h5', 'dataset_prefix': '/coils/coil_',
                           'solver': 'auto'}.items():
            group[key] = np.bytes_(value)
        group['dataset_start'] = 1
        group['dataset_count'] = 2
        group['member_id'] = 2
        rebuilt = openmc.SweptSplineSurface._from_hdf5(group)
        assert rebuilt.is_equal(surface)


def test_permuted_member_ids_rejected(tmp_path):
    path = tmp_path / 'permuted.h5'
    with h5py.File(path, 'w') as h5:
        for suffix, coil_id in [(1, 2), (2, 1)]:
            group = h5.create_group(f'/coils/coil_{suffix:03d}')
            group.attrs['coil_id'] = coil_id
            group.attrs['units'] = 'cm'
            group['centerline_coefficients'] = np.ones((8, 3)) * suffix * 20
            group['major_radius_coefficients'] = np.ones(8)
            group['minor_radius_coefficients'] = np.ones(8)
    surface = member(1)
    surface.data_file = str(path)
    with pytest.raises(ValueError, match='coil_id'):
        surface.bounding_box('-')
