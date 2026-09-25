"""Native package tests; no transport launch or data acquisition.

Run against the actual pinned OpenMC Python package. A missing package is an
explicit module-level skip (BLOCKED), never an API pass. Local method-isolation
receipts do not count as executing this file.
"""
import importlib.util
import hashlib
from pathlib import Path
import shutil

import h5py
import lxml.etree as ET
import numpy as np
import pytest

openmc = pytest.importorskip('openmc', reason='BLOCKED_NATIVE_OPENMC_PYTHON')
if not hasattr(openmc, 'SweptSplineSurface'):
    pytest.skip('BLOCKED_NATIVE_OPENMC_PYTHON: complete pinned package required',
                allow_module_level=True)

spec = importlib.util.spec_from_file_location(
    'analytic_member_model', Path(__file__).with_name('analytic_member_model.py'))
fixture_model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_model)


@pytest.fixture(autouse=True)
def reset_ids():
    openmc.reset_auto_ids()
    yield
    openmc.reset_auto_ids()


@pytest.mark.parametrize('kind', [openmc.PeriodicSplineSurface, openmc.SweptSplineSurface])
@pytest.mark.parametrize('boundary', ['reflective', 'white', 'periodic'])
def test_spline_xml_preserves_payload_and_boundary(kind, boundary):
    surface = kind('toy.h5', '/member', 'sha256:'+'1'*64,
                   surface_id=301, boundary_type=boundary, albedo=0.375, name='member 7')
    element = surface.to_xml_element()
    openmc.reset_auto_ids()
    loaded = openmc.Surface.from_xml_element(element)
    assert loaded.id == 301 and loaded.name == 'member 7'
    assert loaded.data_file == 'toy.h5' and loaded.dataset == '/member'
    assert loaded.content_id == 'sha256:'+'1'*64
    assert loaded.albedo == 0.375 and loaded.boundary_type == boundary


@pytest.mark.parametrize('kind', [openmc.PeriodicSplineSurface, openmc.SweptSplineSurface])
def test_payload_hdf5_summary_roundtrip(kind, tmp_path):
    with h5py.File(tmp_path/'summary-fragment.h5', 'w') as h5:
        group = h5.create_group('surface 301')
        for key, value in dict(type=kind._type, name='member 7', boundary_type='white',
                               albedo='0.375', data_file='toy.h5', dataset='/member',
                               content_id='sha256:'+'1'*64).items():
            group[key] = np.bytes_(value)
        loaded = openmc.Surface.from_hdf5(group)
        assert loaded.id == 301 and loaded.albedo == 0.375
        assert loaded.dataset == '/member'


@pytest.mark.parametrize('kind', [openmc.PeriodicSplineSurface, openmc.SweptSplineSurface])
def test_unsupported_python_operations_are_explicit(kind):
    surface = kind('toy.h5', '/member', 'sha256:'+'1'*64)
    for operation, args in [(surface.evaluate, ((0, 0, 0),)),
                            (surface.translate, ((1, 2, 3),)),
                            (surface.rotate, ((0, 0, 90),))]:
        with pytest.raises(NotImplementedError):
            operation(*args)
    with pytest.raises(ValueError):
        kind('toy.h5', 'relative', 'sha256:'+'1'*64)
    with pytest.raises(ValueError):
        kind('toy.h5', '/member', '')
    element = surface.to_xml_element()
    element.set('units', 'm')
    with pytest.raises(ValueError):
        openmc.Surface.from_xml_element(element)


def test_material_member_union_and_tally_ownership(tmp_path):
    model = fixture_model.make_analytic_model()
    cells = model.geometry.get_all_cells()
    assert cells[201].fill.id == 101 and cells[202].fill.id == 102
    assert {surface.id for surface in cells[500].region.get_surfaces().values()} == {301, 302}
    assert np.array_equal(model.tallies[0].filters[0].bins, [201, 202])
    assert np.array_equal(model.tallies[1].filters[0].bins, [500])
    for tally in model.tallies:
        assert tally.estimator == 'tracklength' and tally.scores == ['flux']
    assert (0, 0, 0) in cells[201].region
    assert (4, 0, 0) in cells[202].region
    assert (0, 0, 0) in cells[500].region and (4, 0, 0) in cells[500].region
    assert (2, 0, 0) not in cells[500].region
    model.export_to_xml(directory=tmp_path)
    tree = ET.parse(str(tmp_path/'geometry.xml'))
    child_materials = {int(cell.get('id')): int(cell.get('material'))
                       for cell in tree.findall('cell') if cell.get('id') in ('201', '202')}
    assert child_materials == {201: 101, 202: 102}


def test_rigid_native_analytic_control():
    sphere = openmc.Sphere(x0=4, y0=0, z0=0, r=1)
    moved = sphere.rotate((0, 0, 90)).translate((3, 0, 2))
    # Surface coefficients for this transform are finite native CSG controls;
    # spline rotate/translate are still unsupported and tested above.
    assert moved.evaluate((3, 4, 2)) == -1


def test_swept_collection_python_roundtrip_and_bounds(tmp_path):
    payload = tmp_path / 'coils.h5'
    with h5py.File(payload, 'w') as h5:
        for index, center_x in ((10, 0.0), (11, 10.0)):
            group = h5.create_group(f'members/coil_{index:03d}')
            group.attrs['units'] = 'cm'
            group.attrs['length_cm'] = 20.0
            group['centerline_coefficients'] = np.tile(
                [center_x, 0.0, 0.0], (4, 1))
            group['major_radius_coefficients'] = np.full(4, 2.0)
            group['minor_radius_coefficients'] = np.full(4, 1.0)
    collection = openmc.SweptSplineSurface(
        payload, dataset_prefix='/members/coil_', dataset_start=10,
        dataset_count=2, surface_id=302, boundary_type='white', albedo=0.375)
    element = collection.to_xml_element()
    assert element.get('dataset') is None and element.get('content_id') is None
    assert element.get('dataset_prefix') == '/members/coil_'
    assert element.get('dataset_start') == '10' and element.get('dataset_count') == '2'
    openmc.reset_auto_ids()
    loaded = openmc.Surface.from_xml_element(element)
    assert loaded.is_equal(collection) and loaded.albedo == 0.375
    bounds = collection.bounding_box('-')
    assert np.allclose(bounds.lower_left, [-2., -2., -2.], atol=1e-10)
    assert np.allclose(bounds.upper_right, [12., 2., 2.], atol=1e-10)
    assert np.all(bounds.lower_left < [-2., -2., -2.])
    assert np.all(bounds.upper_right > [12., 2., 2.])
    with h5py.File(tmp_path/'summary.h5', 'w') as h5:
        group = h5.create_group('surface 303')
        for key, value in dict(type='swept-spline', boundary_type='transmission',
                               data_file=str(payload),
                               dataset_prefix='/members/coil_').items():
            group[key] = np.bytes_(value)
        group['dataset_start'] = 10
        group['dataset_count'] = 2
        loaded_hdf5 = openmc.Surface.from_hdf5(group)
        assert loaded_hdf5.dataset is None
        assert loaded_hdf5.dataset_start == 10 and loaded_hdf5.dataset_count == 2
        assert loaded_hdf5.is_equal(collection)
    geometry_path = tmp_path / 'geometry.xml'
    openmc.Geometry([openmc.Cell(cell_id=402, region=-collection)]).export_to_xml(
        path=geometry_path)
    openmc.reset_auto_ids()
    reloaded_geometry = openmc.Geometry.from_xml(
        path=geometry_path, materials=openmc.Materials())
    assert reloaded_geometry.get_all_surfaces()[302].is_equal(collection)


def test_swept_collection_member_content_binding(tmp_path):
    payload = tmp_path / 'bound-coils.h5'
    ids = ('sha256:' + 'a' * 64, 'sha256:' + 'b' * 64)
    with h5py.File(payload, 'w') as h5:
        for index, content_id in zip((10, 11), ids):
            group = h5.create_group(f'members/coil_{index:03d}')
            group.attrs['units'] = 'cm'
            group.attrs['content_id'] = content_id
            group.attrs['length_cm'] = 20.0
            group['centerline_coefficients'] = np.tile([float(index), 0., 0.], (4, 1))
            group['major_radius_coefficients'] = np.full(4, 2.0)
            group['minor_radius_coefficients'] = np.full(4, 1.0)
    surface = openmc.SweptSplineSurface(
        payload, dataset_prefix='/members/coil_', dataset_indices=[10, 11],
        member_content_ids=ids)
    xml = surface.to_xml_element()
    assert xml.get('member_content_ids') == ' '.join(ids)
    assert openmc.Surface.from_xml_element(xml).is_equal(surface)
    assert surface.bounding_box('-').lower_left[0] < 8.0
    with h5py.File(tmp_path / 'bound-summary.h5', 'w') as h5:
        group = h5.create_group('surface 305')
        for key, value in dict(type='swept-spline', boundary_type='transmission',
                               data_file=str(payload), dataset_prefix='/members/coil_',
                               dataset_indices='10 11',
                               member_content_ids=' '.join(ids)).items():
            group[key] = np.bytes_(value)
        assert openmc.Surface.from_hdf5(group).is_equal(surface)
    with pytest.raises(ValueError):
        openmc.SweptSplineSurface(
            payload, dataset_prefix='/members/coil_', dataset_indices=[10, 11],
            member_content_ids=ids[:1])
    with h5py.File(payload, 'r+') as h5:
        h5['members/coil_011'].attrs.modify('content_id', 'sha256:' + 'c' * 64)
    with pytest.raises(ValueError, match='member content ID mismatch'):
        surface.bounding_box('-')


def test_facet_set_payload_identity_roundtrip_and_bounds(tmp_path):
    reports = Path(__file__).resolve().parents[2] / 'reports/local-cont-20260925'
    payload = reports / 'p00-accepted-facet-payload-01.h5'
    identity = 'sha256:c580f1c228ee9633df197aed32e5f41bc6bcb7b382d8a68f677e69787e8c57a6'
    surface = openmc.FacetSetSurface(
        payload, '/facets/one_period', identity, surface_id=306)
    element = surface.to_xml_element()
    assert element.get('type') == 'facet-set'
    assert element.get('content_id') == identity
    assert openmc.Surface.from_xml_element(element).is_equal(surface)
    delegated = openmc.FacetSetSurface(
        payload, '/facets/one_period', identity, periodic_caps='x0 y0',
        surface_id=307)
    assert delegated.to_xml_element().get('periodic_caps') == 'x0 y0'
    assert openmc.Surface.from_xml_element(
        delegated.to_xml_element()).is_equal(delegated)
    assert np.isfinite(delegated.bounding_box('-').lower_left).all()
    with pytest.raises(ValueError, match='periodic_caps'):
        openmc.FacetSetSurface(payload, '/facets/one_period', identity,
                               periodic_caps='z0')
    geometry_path = tmp_path / 'facet-geometry.xml'
    openmc.Geometry([openmc.Cell(cell_id=406, region=-surface)]).export_to_xml(
        path=geometry_path)
    openmc.reset_auto_ids()
    reloaded_geometry = openmc.Geometry.from_xml(
        path=geometry_path, materials=openmc.Materials())
    assert reloaded_geometry.get_all_surfaces()[306].is_equal(surface)
    box = surface.bounding_box('-')
    with h5py.File(payload, 'r') as h5:
        vertices = h5['facets/one_period/triangle_vertices'][:]
    assert np.all(box.lower_left < vertices.min(axis=(0, 1)))
    assert np.all(box.upper_right > vertices.max(axis=(0, 1)))
    with h5py.File(tmp_path / 'facet-summary.h5', 'w') as h5:
        group = h5.create_group('surface 306')
        for key, value in dict(type='facet-set', boundary_type='transmission',
                               data_file=str(payload), dataset='/facets/one_period',
                               content_id=identity).items():
            group[key] = np.bytes_(value)
        assert openmc.Surface.from_hdf5(group).is_equal(surface)
        delegated_group = h5.create_group('surface 307')
        for key, value in dict(type='facet-set', boundary_type='transmission',
                               data_file=str(payload), dataset='/facets/one_period',
                               content_id=identity, periodic_caps='x0 y0').items():
            delegated_group[key] = np.bytes_(value)
        assert openmc.Surface.from_hdf5(delegated_group).is_equal(delegated)
    with pytest.raises(ValueError, match='periodic'):
        openmc.FacetSetSurface(payload, '/facets/one_period', identity,
                               boundary_type='periodic')
    tampered = tmp_path / 'tampered-facets.h5'
    shutil.copyfile(payload, tampered)
    with h5py.File(tampered, 'r+') as h5:
        vertices = h5['facets/one_period/triangle_vertices']
        vertices[0, 0, 0] = np.nextafter(vertices[0, 0, 0], np.inf)
    with pytest.raises(ValueError, match='SHA-256 does not verify'):
        openmc.FacetSetSurface(
            tampered, '/facets/one_period', identity).bounding_box('-')
    degenerate = tmp_path / 'degenerate-facets.h5'
    shutil.copyfile(payload, degenerate)
    with h5py.File(degenerate, 'r+') as h5:
        group = h5['facets/one_period']
        vertices = group['triangle_vertices'][:]
        vertices[0, 2] = vertices[0, 1]
        group['triangle_vertices'][:] = vertices
        components = group['component_ids'][:]
        metadata = group.attrs['canonical_metadata_json']
        if isinstance(metadata, bytes):
            metadata = metadata.decode()
        digest = hashlib.sha256(metadata.encode())
        digest.update(vertices.astype('<f8').tobytes())
        digest.update(components.astype('<i4').tobytes())
        degenerate_id = 'sha256:' + digest.hexdigest()
        group.attrs['content_id'] = degenerate_id
    with pytest.raises(ValueError, match='degenerate triangles'):
        openmc.FacetSetSurface(degenerate, '/facets/one_period',
                               degenerate_id).bounding_box('-')
    inward = tmp_path / 'inward-facets.h5'
    shutil.copyfile(payload, inward)
    with h5py.File(inward, 'r+') as h5:
        group = h5['facets/one_period']
        vertices = group['triangle_vertices'][:]
        vertices[:, [1, 2]] = vertices[:, [2, 1]]
        group['triangle_vertices'][:] = vertices
        components = group['component_ids'][:]
        metadata = group.attrs['canonical_metadata_json']
        if isinstance(metadata, bytes):
            metadata = metadata.decode()
        digest = hashlib.sha256(metadata.encode())
        digest.update(vertices.astype('<f8').tobytes())
        digest.update(components.astype('<i4').tobytes())
        inward_id = 'sha256:' + digest.hexdigest()
        group.attrs['content_id'] = inward_id
    with pytest.raises(ValueError, match='wind outward'):
        openmc.FacetSetSurface(inward, '/facets/one_period',
                               inward_id).bounding_box('-')


def test_swept_python_box_contains_rounded_stored_power_witness(tmp_path):
    # Rounded cubic-power conversion can leave the rounded control hull by
    # one centimeter at this magnitude; the old Python bound missed it.
    controls = [9007199254740992., 9007199254740994.,
                9007199254740990., 9007199254741000.,
                9007199254740988., 9007199254740988.,
                9007199254740988., 9007199254740992.]
    payload = tmp_path / 'rounded-power.h5'
    with h5py.File(payload, 'w') as h5:
        group = h5.create_group('members/coil_010')
        group.attrs['units'] = 'cm'
        group.attrs['length_cm'] = 1.0
        group['centerline_coefficients'] = np.column_stack(
            (controls, np.arange(8, dtype=float), np.zeros(8)))
        group['major_radius_coefficients'] = np.full(8, .25)
        group['minor_radius_coefficients'] = np.full(8, .25)
    surface = openmc.SweptSplineSurface(
        payload, dataset_prefix='/members/coil_', dataset_indices=[10])
    rounded_center_x = 9007199254740987.0
    old_control_bound = float(min(controls) - .25 - 1e-12)
    assert old_control_bound > rounded_center_x
    assert surface.bounding_box('-').lower_left[0] <= rounded_center_x


def test_swept_selector_identity_and_invalid_collections():
    single = openmc.SweptSplineSurface('coils.h5', '/coil', 'content-a')
    assert single.is_equal(openmc.SweptSplineSurface(
        'coils.h5', '/coil', 'content-a'))
    assert not single.is_equal(openmc.SweptSplineSurface(
        'coils.h5', '/coil', 'content-b'))
    collection = openmc.SweptSplineSurface(
        'coils.h5', dataset_prefix='/members/coil_', dataset_start=10,
        dataset_count=2)
    assert not collection.is_equal(single)
    assert not collection.is_equal(openmc.SweptSplineSurface(
        'coils.h5', dataset_prefix='/members/coil_', dataset_start=11,
        dataset_count=2))
    with pytest.raises(ValueError):
        openmc.SweptSplineSurface('coils.h5', '/coil', 'content-a',
                                  dataset_prefix='/members/', dataset_count=2)
    for count, start in ((0, 0), (2, -1), (2, 2**31-1)):
        with pytest.raises(ValueError):
            openmc.SweptSplineSurface('coils.h5', dataset_prefix='/members/',
                                      dataset_start=start, dataset_count=count)
    malformed = ET.Element('surface', id='999', type='swept-spline',
                           data_file='coils.h5', dataset='/coil',
                           content_id='content-a', dataset_prefix='/members/',
                           dataset_count='2')
    with pytest.raises(ValueError):
        openmc.Surface.from_xml_element(malformed)
    malformed.attrib.pop('dataset')
    malformed.attrib.pop('content_id')
    malformed.set('dataset_count', '2garbage')
    with pytest.raises(ValueError):
        openmc.Surface.from_xml_element(malformed)


def test_swept_explicit_index_selector_roundtrip(tmp_path):
    payload = tmp_path / 'coils.h5'
    with h5py.File(payload, 'w') as h5:
        for index, center_x in ((10, 0.0), (11, 100.0), (30, 30.0)):
            group = h5.create_group(f'members/coil_{index:03d}')
            group.attrs['units'] = 'cm'
            group.attrs['length_cm'] = 20.0
            group['centerline_coefficients'] = np.tile([center_x, 0., 0.], (4, 1))
            group['major_radius_coefficients'] = np.full(4, 2.0)
            group['minor_radius_coefficients'] = np.full(4, 1.0)
    selected = openmc.SweptSplineSurface(
        payload, dataset_prefix='/members/coil_', dataset_indices=[30, 10],
        surface_id=304)
    assert selected.dataset_indices == (30, 10)
    assert selected.to_xml_element().get('dataset_indices') == '30 10'
    assert selected.to_xml_element().get('dataset_count') is None
    assert openmc.Surface.from_xml_element(selected.to_xml_element()).is_equal(selected)
    bounds = selected.bounding_box('-')
    assert bounds.lower_left[0] < -2.0 and bounds.upper_right[0] > 32.0
    assert bounds.upper_right[0] < 33.0  # omitted member 11 is not selected
    with h5py.File(tmp_path / 'summary.h5', 'w') as h5:
        group = h5.create_group('surface 304')
        for key, value in dict(type='swept-spline', boundary_type='transmission',
                               data_file=str(payload),
                               dataset_prefix='/members/coil_',
                               dataset_indices='30 10').items():
            group[key] = np.bytes_(value)
        assert openmc.Surface.from_hdf5(group).is_equal(selected)
    for invalid in ([], [10, 10], [-1], [2**31], [True]):
        with pytest.raises(ValueError):
            openmc.SweptSplineSurface(
                payload, dataset_prefix='/members/coil_', dataset_indices=invalid)
    with pytest.raises(ValueError):
        openmc.SweptSplineSurface(
            payload, dataset_prefix='/members/coil_', dataset_indices=[30],
            dataset_count=1)


@pytest.mark.parametrize('kind', [openmc.PeriodicSplineSurface, openmc.SweptSplineSurface])
def test_payload_equality_has_defined_semantics(kind):
    first = kind('toy.h5', '/member', 'sha256:'+'1'*64)
    second = kind('toy.h5', '/member', 'sha256:'+'1'*64)
    assert first.is_equal(second)
    assert not first.is_equal(kind('toy.h5', '/member', 'sha256:'+'2'*64))
