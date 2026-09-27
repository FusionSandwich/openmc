import h5py
import lxml.etree as ET
import numpy as np
import pytest

import openmc


def make_mesh(mesh_id=1):
    mesh = openmc.RegularMesh(mesh_id=mesh_id)
    mesh.dimension = (2, 2, 2)
    mesh.lower_left = (0.0, 0.0, 0.0)
    mesh.upper_right = (2.0, 2.0, 2.0)
    return mesh


def test_transform_identity_and_tallies_xml(tmp_path):
    mesh = make_mesh()
    translated = openmc.MeshFilter(mesh, filter_id=11)
    translated.translation = (1.0, 0.0, 0.0)
    translated_other = openmc.MeshFilter(mesh, filter_id=12)
    translated_other.translation = (2.0, 0.0, 0.0)

    rotated = openmc.MeshFilter(mesh, filter_id=13)
    rotated.rotation = (0.0, 0.0, 90.0)
    rotated_other = openmc.MeshFilter(mesh, filter_id=14)
    rotated_other.rotation = (0.0, 0.0, 180.0)

    assert translated != translated_other
    assert rotated != rotated_other

    identical = openmc.MeshFilter(mesh, filter_id=15)
    identical.translation = translated.translation.copy()
    assert identical == translated
    assert hash(identical) == hash(translated)
    assert openmc.MeshFilter(make_mesh(mesh_id=2)) != openmc.MeshFilter(mesh)

    tallies = openmc.Tallies()
    for filt in (translated, translated_other, rotated, rotated_other):
        tally = openmc.Tally()
        tally.filters = [filt]
        tally.scores = ['flux']
        tallies.append(tally)
    path = tmp_path / 'tallies.xml'
    tallies.export_to_xml(path)
    filters = ET.parse(path).getroot().findall('filter')
    assert len(filters) == 4
    assert [int(f.get('id')) for f in filters] == [11, 12, 13, 14]

    meshes = {mesh.id: mesh}
    loaded = [openmc.MeshFilter.from_xml_element(f, meshes=meshes)
              for f in filters]
    assert loaded[0].translation.tolist() == [1.0, 0.0, 0.0]
    assert loaded[1].translation.tolist() == [2.0, 0.0, 0.0]
    assert np.array_equal(loaded[2].rotation, [0.0, 0.0, 90.0])
    assert np.array_equal(loaded[3].rotation, [0.0, 0.0, 180.0])


def test_hash_contract_numeric_equal_transforms_and_mesh_subclasses():
    mesh = make_mesh()
    positive_zero = openmc.MeshFilter(mesh)
    positive_zero.translation = (0, 1, 2)
    negative_zero = openmc.MeshFilter(mesh)
    negative_zero.translation = (-0.0, 1.0, 2.0)
    assert positive_zero == negative_zero
    assert hash(positive_zero) == hash(negative_zero)

    material_a = openmc.MeshMaterialFilter(mesh, [(0, 1)])
    material_b = openmc.MeshMaterialFilter(mesh, [(0, 2)])
    assert material_a != material_b
    material_a.translation = (1.0, 0.0, 0.0)
    material_c = openmc.MeshMaterialFilter(mesh, [(0, 1)])
    material_c.translation = (2.0, 0.0, 0.0)
    assert material_a != material_c

    surface_a = openmc.MeshSurfaceFilter(mesh)
    surface_b = openmc.MeshSurfaceFilter(mesh)
    assert surface_a == surface_b
    assert hash(surface_a) == hash(surface_b)
    assert surface_a != openmc.MeshFilter(mesh)

    tally_a = openmc.Tally()
    tally_a.filters = [material_a]
    tally_b = openmc.Tally()
    tally_b.filters = [material_b]
    tallies = openmc.Tallies([tally_a, tally_b])
    xml_filters = ET.Element('filters')
    tallies._create_filter_subelements(xml_filters)
    assert len(xml_filters) == 2


@pytest.mark.parametrize('size', [9, 12])
def test_hdf5_rotation_reads_stored_row_major_matrix(tmp_path, size):
    mesh = make_mesh()
    matrix = np.array([[0.25, 0.5, 0.75], [1.25, 1.5, 1.75],
                       [2.25, 2.5, 2.75]])
    values = matrix.ravel() if size == 9 else np.r_[matrix.ravel(), 10., 20., 30.]
    path = tmp_path / 'statepoint.h5'
    with h5py.File(path, 'w') as h5:
        group = h5.create_group('tallies/filter 7')
        group.create_dataset('type', data=np.bytes_('mesh'))
        group.create_dataset('bins', data=mesh.id)
        group.create_dataset('translation', data=[1., 2., 3.])
        group.create_dataset('rotation', data=values)
    with h5py.File(path, 'r') as h5:
        out = openmc.MeshFilter.from_hdf5(h5['tallies/filter 7'],
                                          meshes={mesh.id: mesh})
    assert np.array_equal(out.rotation, matrix)
    assert np.array_equal(out.translation, [1., 2., 3.])


@pytest.mark.parametrize('shape', [(8,), (10,), (3, 3), (2, 6)])
def test_hdf5_rotation_rejects_wrong_length_or_shape(tmp_path, shape):
    mesh = make_mesh()
    path = tmp_path / 'bad.h5'
    with h5py.File(path, 'w') as h5:
        group = h5.create_group('filter 8')
        group.create_dataset('type', data=np.bytes_('mesh'))
        group.create_dataset('bins', data=mesh.id)
        group.create_dataset('rotation', data=np.zeros(shape))
    with h5py.File(path, 'r') as h5, pytest.raises(ValueError):
        openmc.MeshFilter.from_hdf5(h5['filter 8'], meshes={mesh.id: mesh})


@pytest.mark.parametrize('field', ['rotation', 'translation'])
def test_hdf5_transform_rejects_nonfinite_values(tmp_path, field):
    mesh = make_mesh()
    path = tmp_path / 'bad.h5'
    values = np.zeros(9 if field == 'rotation' else 3)
    values[0] = np.nan
    with h5py.File(path, 'w') as h5:
        group = h5.create_group('filter 9')
        group.create_dataset('type', data=np.bytes_('mesh'))
        group.create_dataset('bins', data=mesh.id)
        group.create_dataset(field, data=values)
    with h5py.File(path, 'r') as h5, pytest.raises(ValueError):
        openmc.MeshFilter.from_hdf5(h5['filter 9'], meshes={mesh.id: mesh})


@pytest.mark.parametrize('field,values', [
    ('rotation', [0., 0., 0., 1.]),
    ('rotation', [[0., 1.], [2., 3.]]),
    ('translation', [0., 0., np.inf]),
])
def test_transform_setters_validate_public_shapes_and_values(field, values):
    filt = openmc.MeshFilter(make_mesh())
    with pytest.raises(ValueError):
        setattr(filt, field, values)
