"""Execute real SweptSplineSurface methods with a controlled Surface base.

This is not an import of the OpenMC package. lxml, NumPy and h5py are real;
base construction/XML and BoundingBox are test doubles. Supply either the
real openmc/surface.py or the retained source excerpt. No code is downloaded.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path

import h5py
import lxml.etree as ET
import numpy as np


class SurfaceDouble:
    def __init__(self, surface_id=None, boundary_type='transmission',
                 albedo=1.0, name=''):
        self.id = surface_id
        self.boundary_type = boundary_type
        self.albedo = albedo
        self.name = name or ''

    def to_xml_element(self):
        element = ET.Element('surface', id=str(self.id), type=self._type,
                             name=self.name, coeffs='')
        if self.boundary_type != 'transmission':
            element.set('boundary', self.boundary_type)
            if self.boundary_type in {'reflective', 'periodic', 'white'}:
                if not math.isclose(self.albedo, 1.0):
                    element.set('albedo', str(self.albedo))
        return element


class BoundingBoxDouble:
    def __init__(self, lower, upper):
        self.lower_left, self.upper_right = np.asarray(lower), np.asarray(upper)

    @classmethod
    def infinite(cls):
        return cls([-np.inf]*3, [np.inf]*3)


def check_type(name, value, expected):
    if not isinstance(value, expected):
        raise TypeError(name)


def get_text(element, name, default=None):
    return element.get(name, element.findtext(name, default))


def load_class(source):
    tree = ast.parse(source.read_text(), filename=str(source))
    matches = [node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == 'SweptSplineSurface']
    if len(matches) != 1:
        raise ValueError('Exactly one actual SweptSplineSurface class required')
    namespace = dict(Surface=SurfaceDouble, BoundingBox=BoundingBoxDouble,
                     Path=Path, check_type=check_type, get_text=get_text,
                     _ALBEDO_BOUNDARIES={'reflective', 'periodic', 'white'}, np=np)
    exec(compile(ast.Module(body=matches, type_ignores=[]), str(source), 'exec'),
         namespace)
    return namespace['SweptSplineSurface']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--adapter-hdf5', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cls = load_class(args.source)
    rows = []

    def check(name, predicate, block='BLOCKED_PYTHON_CONTRACT'):
        try:
            ok = bool(predicate())
            note = ''
        except Exception as error:
            ok, note = False, f'{type(error).__name__}: {error}'
        rows.append(dict(case=name, passed=ok, observed=note,
                         block_code=None if ok else block))

    def raises(kind, function):
        try:
            function()
        except kind:
            return True
        return False

    def surface(**kwargs):
        return cls(data_file='payload.h5', dataset='/member',
                   content_id='member-7', surface_id=901, **kwargs)

    for boundary in ('reflective', 'white', 'periodic'):
        original = surface(boundary_type=boundary, albedo=0.375, name='member 7')
        element = original.to_xml_element()
        check(f'{boundary}_xml_export_has_albedo',
              lambda element=element: element.get('albedo') == '0.375')
        check(f'{boundary}_xml_roundtrip_preserves_albedo',
              lambda element=element: cls._from_xml_element(element).albedo == 0.375,
              'BLOCKED_ALBEDO_ROUNDTRIP')
    check('xml_id_payload_and_units', lambda: dict(surface().to_xml_element().attrib)
          == dict(id='901', type='swept-spline', name='', data_file='payload.h5',
                  dataset='/member', content_id='member-7', units='cm'))
    check('xml_roundtrip_identity', lambda: cls._from_xml_element(
          surface().to_xml_element()).__dict__ == surface().__dict__)
    bad = surface().to_xml_element()
    bad.set('units', 'm')
    check('unsupported_units_explicit', lambda: raises(ValueError,
          lambda: cls._from_xml_element(bad)))
    check('relative_dataset_rejected', lambda: raises(ValueError,
          lambda: cls('x.h5', 'relative', 'identity')))
    check('empty_identity_rejected', lambda: raises(ValueError,
          lambda: cls('x.h5', '/member', '')))
    for method, values in [('evaluate', ((0, 0, 0),)),
                           ('translate', ((1, 2, 3),)),
                           ('rotate', ((0, 0, 90),))]:
        check(f'{method}_unsupported_explicit', lambda method=method, values=values:
              raises(NotImplementedError, lambda: getattr(surface(), method)(*values)))
    with h5py.File(args.adapter_hdf5, 'r') as h5:
        loaded = cls._from_hdf5(h5['surface 901'], surface_id=901)
        check('cpp_inner_hdf5_to_python_member', lambda:
              loaded.dataset == '/member' and loaded.content_id == 'member-7'
              and loaded.data_file == 'sub/../payload.h5')
        group = h5['surface 902']
        check('cpp_inner_hdf5_collection_keys', lambda:
              int(group['dataset_start'][()]) == 10
              and int(group['dataset_count'][()]) == 2
              and group['dataset_prefix'][()].decode() == '/members/')
        check('cpp_collection_hdf5_python_roundtrip', lambda:
              (lambda loaded: loaded.data_file == 'payload.h5'
               and loaded.dataset is None and loaded.content_id is None
               and loaded.dataset_prefix == '/members/'
               and loaded.dataset_start == 10 and loaded.dataset_count == 2)(
                   cls._from_hdf5(group, surface_id=902)),
              'BLOCKED_COLLECTION_PYTHON_REPRESENTATION')
    collection = ET.Element('surface', id='902', type='swept-spline',
                            data_file='payload.h5', dataset_prefix='/members/',
                            dataset_start='10', dataset_count='2')
    check('cpp_collection_xml_python_roundtrip', lambda:
          (lambda loaded: loaded.dataset_prefix == '/members/'
           and loaded.dataset_start == 10 and loaded.dataset_count == 2
           and loaded.dataset is None and loaded.content_id is None)(
               cls._from_xml_element(collection)),
          'BLOCKED_COLLECTION_PYTHON_REPRESENTATION')
    collection_surface = cls(data_file='payload.h5', dataset_prefix='/members/',
                             dataset_start=10, dataset_count=2, surface_id=902)
    check('collection_xml_export_matches_cpp_selector', lambda:
          {key: collection_surface.to_xml_element().get(key) for key in
           ('data_file', 'dataset_prefix', 'dataset_start', 'dataset_count', 'units')}
          == dict(data_file='payload.h5', dataset_prefix='/members/',
                  dataset_start='10', dataset_count='2', units='cm'))
    check('collection_xml_roundtrip_identity', lambda:
          cls._from_xml_element(collection_surface.to_xml_element()).__dict__
          == collection_surface.__dict__)
    check('collection_mixed_selector_rejected', lambda: raises(ValueError,
          lambda: cls('x.h5', '/member', 'identity',
                      dataset_prefix='/members/', dataset_count=2)))
    check('collection_zero_count_rejected', lambda: raises(ValueError,
          lambda: cls('x.h5', dataset_prefix='/members/', dataset_count=0)))
    check('collection_overflow_rejected', lambda: raises(ValueError,
          lambda: cls('x.h5', dataset_prefix='/members/', dataset_start=2**31-1,
                      dataset_count=2)))
    check('single_payload_equality', lambda:
          surface().is_equal(surface()) and not surface().is_equal(
              cls('payload.h5', '/member', 'different', surface_id=902)))
    check('collection_selector_equality', lambda:
          collection_surface.is_equal(cls('payload.h5', dataset_prefix='/members/',
                                          dataset_start=10, dataset_count=2))
          and not collection_surface.is_equal(cls(
              'payload.h5', dataset_prefix='/members/', dataset_start=11,
              dataset_count=2)))
    check('positive_halfspace_unbounded', lambda:
          np.isposinf(surface().bounding_box('+').upper_right).all())
    check('invalid_halfspace_rejected', lambda: raises(ValueError,
          lambda: surface().bounding_box('bogus')))
    (args.output/'results.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    failed = sum(not row['passed'] for row in rows)
    receipt = dict(evidence='actual-methods-with-controlled-base', checks=len(rows),
                   passed=len(rows)-failed, failed=failed,
                   source=str(args.source), source_sha256=hashlib.sha256(
                       args.source.read_bytes()).hexdigest(),
                   adapter_hdf5_sha256=hashlib.sha256(
                       args.adapter_hdf5.read_bytes()).hexdigest(),
                   runner_sha256=hashlib.sha256(
                       Path(__file__).read_bytes()).hexdigest(),
                   native_openmc_imported=False, transport_run=False)
    (args.output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
