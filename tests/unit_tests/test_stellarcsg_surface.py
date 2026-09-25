import h5py
import numpy as np
import pytest

import openmc


CONTENT_ID = 'sha256:' + '1a' * 32


def test_periodic_spline_xml_roundtrip():
    surface = openmc.PeriodicSplineSurface(
        surface_id=71,
        name='plasma',
        data_file='coefficients.h5',
        dataset='/surfaces/plasma',
        content_id=CONTENT_ID,
    )

    element = surface.to_xml_element()
    assert element.get('type') == 'periodic-spline'
    assert element.get('units') == 'cm'
    assert element.get('coeffs') is None

    restored = openmc.Surface.from_xml_element(element)
    assert isinstance(restored, openmc.PeriodicSplineSurface)
    assert restored.id == 71
    assert restored.data_file == 'coefficients.h5'
    assert restored.dataset == '/surfaces/plasma'
    assert restored.content_id == CONTENT_ID
    assert restored.solver == 'layered'


def test_periodic_spline_hdf5_roundtrip(tmp_path):
    path = tmp_path / 'summary.h5'
    with h5py.File(path, 'w') as h5:
        group = h5.create_group('surface 72')
        group['geom_type'] = np.bytes_('csg')
        group['type'] = np.bytes_('periodic-spline')
        group['boundary_type'] = np.bytes_('transmission')
        group['data_file'] = np.bytes_('coefficients.h5')
        group['dataset'] = np.bytes_('/surfaces/blanket')
        group['content_id'] = np.bytes_(CONTENT_ID)
        group['solver'] = np.bytes_('layered')

    with h5py.File(path, 'r') as h5:
        restored = openmc.Surface.from_hdf5(h5['surface 72'])
    assert isinstance(restored, openmc.PeriodicSplineSurface)
    assert restored.id == 72
    assert restored.dataset == '/surfaces/blanket'


def test_periodic_spline_rejects_invalid_contract():
    with pytest.raises(ValueError, match='absolute HDF5'):
        openmc.PeriodicSplineSurface(
            data_file='coefficients.h5',
            dataset='surfaces/plasma',
            content_id=CONTENT_ID,
        )
    with pytest.raises(ValueError, match='layered'):
        openmc.PeriodicSplineSurface(
            data_file='coefficients.h5',
            dataset='/surfaces/plasma',
            content_id=CONTENT_ID,
            solver='unchecked',
        )


def test_periodic_spline_rejects_transforms():
    surface = openmc.PeriodicSplineSurface(
        data_file='coefficients.h5',
        dataset='/surfaces/plasma',
        content_id=CONTENT_ID,
    )
    with pytest.raises(NotImplementedError, match='coefficient payload'):
        surface.translate((1.0, 0.0, 0.0))
    with pytest.raises(NotImplementedError, match='coefficient payload'):
        surface.rotate((0.0, 0.0, 90.0))


def test_swept_spline_xml_and_hdf5_roundtrip(tmp_path):
    surface = openmc.SweptSplineSurface(
        surface_id=81,
        name='coil',
        data_file='coils.h5',
        dataset='/coils/coil_001',
        content_id=CONTENT_ID,
    )
    restored = openmc.Surface.from_xml_element(surface.to_xml_element())
    assert isinstance(restored, openmc.SweptSplineSurface)
    assert restored.dataset == '/coils/coil_001'

    path = tmp_path / 'summary-swept.h5'
    with h5py.File(path, 'w') as h5:
        group = h5.create_group('surface 81')
        group['geom_type'] = np.bytes_('csg')
        group['type'] = np.bytes_('swept-spline')
        group['boundary_type'] = np.bytes_('transmission')
        group['data_file'] = np.bytes_('coils.h5')
        group['dataset'] = np.bytes_('/coils/coil_001')
        group['content_id'] = np.bytes_(CONTENT_ID)
    with h5py.File(path, 'r') as h5:
        summary = openmc.Surface.from_hdf5(h5['surface 81'])
    assert isinstance(summary, openmc.SweptSplineSurface)
    assert summary.content_id == CONTENT_ID


def test_swept_spline_rejects_transforms():
    surface = openmc.SweptSplineSurface(
        data_file='coils.h5', dataset='/coils/coil_001', content_id=CONTENT_ID
    )
    with pytest.raises(NotImplementedError, match='payload'):
        surface.translate((1.0, 0.0, 0.0))
