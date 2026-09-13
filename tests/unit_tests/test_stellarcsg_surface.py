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
        solver='general',
    )
    restored = openmc.Surface.from_xml_element(surface.to_xml_element())
    assert isinstance(restored, openmc.SweptSplineSurface)
    assert restored.dataset == '/coils/coil_001'
    assert restored.solver == 'general'

    path = tmp_path / 'summary-swept.h5'
    with h5py.File(path, 'w') as h5:
        group = h5.create_group('surface 81')
        group['geom_type'] = np.bytes_('csg')
        group['type'] = np.bytes_('swept-spline')
        group['boundary_type'] = np.bytes_('transmission')
        group['data_file'] = np.bytes_('coils.h5')
        group['dataset'] = np.bytes_('/coils/coil_001')
        group['content_id'] = np.bytes_(CONTENT_ID)
        group['solver'] = np.bytes_('general')
    with h5py.File(path, 'r') as h5:
        summary = openmc.Surface.from_hdf5(h5['surface 81'])
    assert isinstance(summary, openmc.SweptSplineSurface)
    assert summary.content_id == CONTENT_ID
    assert summary.solver == 'general'


def test_swept_spline_rejects_invalid_solver():
    with pytest.raises(ValueError, match="'auto' or 'general'"):
        openmc.SweptSplineSurface(
            data_file='coils.h5', dataset='/coils/coil_001',
            content_id=CONTENT_ID, solver='unchecked'
        )


@pytest.mark.parametrize('boundary_type', [
    'transmission', 'vacuum', 'reflective', 'white'
])
def test_custom_surfaces_preserve_boundary_types(boundary_type):
    surface = openmc.PeriodicSplineSurface(
        surface_id=91, data_file='coefficients.h5',
        dataset='/surfaces/plasma', content_id=CONTENT_ID,
        boundary_type=boundary_type,
    )
    restored = openmc.Surface.from_xml_element(surface.to_xml_element())
    assert restored.boundary_type == boundary_type


def test_custom_and_ordinary_boolean_regions_serialize():
    custom = openmc.PeriodicSplineSurface(
        surface_id=92, data_file='coefficients.h5',
        dataset='/surfaces/plasma', content_id=CONTENT_ID,
    )
    coil = openmc.SweptSplineSurface(
        surface_id=93, data_file='coils.h5', dataset='/coils/coil_001',
        content_id=CONTENT_ID,
    )
    sphere = openmc.Sphere(surface_id=94, r=1000.0)
    cylinder = openmc.ZCylinder(surface_id=95, r=200.0)
    region = ((-custom & +cylinder) | (-coil & -sphere)) & ~(+custom & +sphere)
    encoded = str(region)
    restored = openmc.Region.from_expression(encoded, region.get_surfaces())
    assert str(restored) == encoded
    assert set(restored.get_surfaces()) == {92, 93, 94, 95}


def test_swept_spline_rejects_transforms():
    surface = openmc.SweptSplineSurface(
        data_file='coils.h5', dataset='/coils/coil_001', content_id=CONTENT_ID
    )
    with pytest.raises(NotImplementedError, match='payload'):
        surface.translate((1.0, 0.0, 0.0))


def test_swept_collection_xml_roundtrip():
    surface = openmc.SweptSplineSurface(
        'coils.h5', dataset_prefix='/coils/coil_', dataset_start=7,
        dataset_count=12, name='coil union', boundary_type='reflective', albedo=0.7,
    )
    element = surface.to_xml_element()
    assert element.get('type') == 'swept-spline'
    assert element.get('dataset') is None
    assert element.get('content_id') is None
    assert element.get('coeffs') is None
    assert element.get('dataset_prefix') == '/coils/coil_'
    assert element.get('dataset_start') == '7'
    assert element.get('dataset_count') == '12'
    restored = openmc.Surface.from_xml_element(element)
    assert restored.is_collection
    assert restored.dataset is None
    assert restored.content_id is None
    assert restored.id == surface.id
    assert restored.name == 'coil union'
    assert restored.boundary_type == 'reflective'
    assert restored.albedo == 0.7
    assert restored.dataset_prefix == surface.dataset_prefix
    assert restored.dataset_start == 7
    assert restored.dataset_count == 12
    assert restored.solver == 'auto'
    assert len((-restored).get_surfaces()) == 1
    with pytest.raises(NotImplementedError, match='payload'):
        restored.translate([1.0, 0.0, 0.0])
    with pytest.raises(NotImplementedError, match='payload'):
        restored.rotate([0.0, 0.0, 90.0])


def test_swept_collection_cpp_summary_roundtrip(tmp_path):
    path = tmp_path / 'collection-summary.h5'
    # Exact fields emitted by SurfaceSweptSpline::to_hdf5_inner in collection
    # mode: the C++ writer omits dataset, content_id, and solver.
    with h5py.File(path, 'w') as handle:
        group = handle.create_group('surface 582')
        for key, value in {
            'geom_type': 'csg', 'type': 'swept-spline',
            'boundary_type': 'transmission', 'name': 'coil union',
            'data_file': 'coils.h5', 'dataset_prefix': '/coils/coil_',
        }.items():
            group[key] = np.bytes_(value)
        group['dataset_start'] = np.int32(9)
        group['dataset_count'] = np.int32(48)
    with h5py.File(path, 'r') as handle:
        restored = openmc.Surface.from_hdf5(handle['surface 582'])
    assert restored.is_collection
    assert restored.id == 582
    assert restored.dataset_prefix == '/coils/coil_'
    assert restored.dataset_start == 9
    assert restored.dataset_count == 48
    assert restored.solver == 'auto'
    element = restored.to_xml_element()
    assert element.get('dataset_count') == '48'
    assert element.get('dataset') is None
    assert element.get('content_id') is None


def test_swept_collection_bounds_match_individual_union(tmp_path):
    path = tmp_path / 'collection.h5'
    with h5py.File(path, 'w') as handle:
        for index, center, major, minor in [
            (998, [2., 1., -3.], 0.3, 0.2),
            (999, [-1., 4., 2.], 0.1, 0.5),
            (1000, [0., -2., 0.], 0.7, 0.6),
        ]:
            group = handle.create_group(f'coils/coil_{index:03d}')
            group.attrs['units'] = 'cm'
            group['centerline_coefficients'] = np.tile(center, (8, 1))
            group['major_radius_coefficients'] = np.full(8, major)
            group['minor_radius_coefficients'] = np.full(8, minor)
    collection = openmc.SweptSplineSurface(
        path, dataset_prefix='/coils/coil_', dataset_start=998, dataset_count=3)
    bounds = collection.bounding_box('-')
    np.testing.assert_allclose(bounds.lower_left, [-1.5, -2.7, -3.3])
    np.testing.assert_allclose(bounds.upper_right, [2.3, 4.5, 2.5])
    assert np.all(np.isneginf(collection.bounding_box('+').lower_left))
    assert np.all(np.isposinf(collection.bounding_box('+').upper_right))
    singles = [openmc.SweptSplineSurface(path, f'/coils/coil_{index:03d}', CONTENT_ID)
               for index in range(998, 1001)]
    np.testing.assert_array_equal(
        bounds.lower_left, np.min([s.bounding_box('-').lower_left for s in singles], axis=0))
    np.testing.assert_array_equal(
        bounds.upper_right, np.max([s.bounding_box('-').upper_right for s in singles], axis=0))


@pytest.mark.parametrize('kwargs', [
    {'dataset': '/coils/coil_000'}, {'content_id': CONTENT_ID},
    {'dataset_prefix': 'coils/coil_'}, {'dataset_prefix': ''},
    {'dataset_prefix': '/coils/../coil_'}, {'dataset_prefix': '/coils/\x00'},
    {'dataset_start': -1}, {'dataset_start': 0.5}, {'dataset_start': True},
    {'dataset_count': 0}, {'dataset_count': -1}, {'dataset_count': 1.5},
    {'dataset_count': True}, {'dataset_count': None},
    {'dataset_count': 2147483648}, {'dataset_start': 2147483647},
    {'dataset_start': np.int64(9223372036854775807)}, {'solver': 'general'},
])
def test_swept_collection_rejects_invalid_contract(kwargs):
    options = {'dataset_prefix': '/coils/coil_', 'dataset_count': 2}
    options.update(kwargs)
    with pytest.raises((ValueError, TypeError)):
        openmc.SweptSplineSurface('coils.h5', **options)


def test_swept_collection_requires_both_prefix_and_count():
    with pytest.raises(TypeError, match='dataset_prefix'):
        openmc.SweptSplineSurface('coils.h5', dataset_count=1)


def test_swept_collection_rejects_mixed_xml():
    surface = openmc.SweptSplineSurface(
        'coils.h5', dataset_prefix='/coils/coil_', dataset_count=2)
    element = surface.to_xml_element()
    element.set('dataset', '/coils/coil_000')
    with pytest.raises(ValueError, match='omit dataset'):
        openmc.Surface.from_xml_element(element)


@pytest.mark.parametrize('surface_type', [openmc.PeriodicSplineSurface,
                                         openmc.SweptSplineSurface])
def test_payload_surface_equality_uses_definition(surface_type):
    first = surface_type('geometry.h5', '/surfaces/first', CONTENT_ID)
    second = surface_type('geometry.h5', '/surfaces/first', CONTENT_ID)
    assert first.is_equal(second)
    for key, value in [('data_file', 'other.h5'), ('dataset', '/surfaces/second'),
                       ('content_id', 'sha256:' + 'ff' * 32)]:
        altered = second.clone()
        setattr(altered, key, value)
        assert not first.is_equal(altered)
    changed_solver = second.clone()
    changed_solver.solver = ('reference' if surface_type is openmc.PeriodicSplineSurface
                             else 'general')
    assert not first.is_equal(changed_solver)
    sphere = openmc.Sphere(r=1.0)
    assert not first.is_equal(sphere)
    assert not sphere.is_equal(first)


@pytest.mark.parametrize('surface_type', [openmc.PeriodicSplineSurface,
                                         openmc.SweptSplineSurface])
def test_distinct_payload_surfaces_survive_merge(surface_type):
    first = surface_type('geometry.h5', '/surfaces/first', CONTENT_ID)
    second = surface_type('geometry.h5', '/surfaces/second', CONTENT_ID)
    duplicate = first.clone()
    cells = [openmc.Cell(region=-surface) for surface in (first, second, duplicate)]
    geometry = openmc.Geometry(cells, merge_surfaces=True)
    replaced = geometry.remove_redundant_surfaces()
    assert replaced == {duplicate.id: first}
    assert set(geometry.get_all_surfaces()) == {first.id, second.id}
    assert cells[1].region.surface is second


def test_payload_collection_equality_and_merge():
    first = openmc.SweptSplineSurface(
        'coils.h5', dataset_prefix='/coils/coil_', dataset_start=0, dataset_count=12)
    duplicate = first.clone()
    assert first.is_equal(duplicate)
    variants = []
    for key, value in [('data_file', 'other.h5'), ('dataset_prefix', '/other/coil_'),
                       ('dataset_start', 1), ('dataset_count', 48)]:
        altered = first.clone()
        setattr(altered, key, value)
        assert not first.is_equal(altered)
        variants.append(altered)
    single = openmc.SweptSplineSurface('coils.h5', '/coils/coil_000', CONTENT_ID)
    assert not first.is_equal(single)
    surfaces = [first, duplicate, single, *variants]
    geometry = openmc.Geometry([openmc.Cell(region=-s) for s in surfaces])
    assert geometry.remove_redundant_surfaces() == {duplicate.id: first}
    assert len(geometry.get_all_surfaces()) == len(surfaces) - 1


def test_payload_merge_preserves_boundary_settings_and_solver():
    first = openmc.PeriodicSplineSurface(
        'geometry.h5', '/surfaces/first', CONTENT_ID,
        boundary_type='reflective', albedo=0.4)
    second = first.clone()
    second.albedo = 0.6
    third = first.clone()
    third.boundary_type = 'vacuum'
    fourth = first.clone()
    fourth.solver = 'reference'
    geometry = openmc.Geometry([openmc.Cell(region=-s)
                               for s in (first, second, third, fourth)])
    assert geometry.remove_redundant_surfaces() == {}


def test_standard_surface_merge_still_uses_numeric_coefficients():
    first, duplicate, distinct = openmc.Sphere(r=1.), openmc.Sphere(r=1.), openmc.Sphere(r=2.)
    geometry = openmc.Geometry([openmc.Cell(region=-s) for s in (first, duplicate, distinct)])
    assert geometry.remove_redundant_surfaces() == {duplicate.id: first}
