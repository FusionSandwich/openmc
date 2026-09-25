"""Native package tests; no transport launch or data acquisition.

Run against the actual pinned OpenMC Python package. A missing package is an
explicit module-level skip (BLOCKED), never an API pass. Local method-isolation
receipts do not count as executing this file.
"""
import importlib.util
from pathlib import Path

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


@pytest.mark.xfail(strict=True, reason='BLOCKED_SPLINE_EQUALITY_EMPTY_COEFFICIENTS')
@pytest.mark.parametrize('kind', [openmc.PeriodicSplineSurface, openmc.SweptSplineSurface])
def test_payload_equality_has_defined_semantics(kind):
    first = kind('toy.h5', '/member', 'sha256:'+'1'*64)
    second = kind('toy.h5', '/member', 'sha256:'+'1'*64)
    assert first.is_equal(second)
