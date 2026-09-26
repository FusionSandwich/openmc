"""The represented geometry choice must survive every supported boundary."""
import tempfile
import unittest
from pathlib import Path

import h5py
import openmc


class TestOffsetRepresentation(unittest.TestCase):
    def test_xml_identity_and_legacy_default(self):
        args = dict(data_file='fixture.h5', dataset='/coils/coil_002',
                    content_id='sha256:fixture')
        legacy = openmc.SweptSplineSurface(**args)
        exact = openmc.SweptSplineSurface(**args, representation='exact_control_offset')
        self.assertFalse(legacy.is_equal(exact))
        restored = openmc.Surface.from_xml_element(exact.to_xml_element())
        self.assertTrue(restored.is_equal(exact))
        elem = exact.to_xml_element()
        elem.attrib.pop('representation')
        self.assertEqual(openmc.Surface.from_xml_element(elem).representation,
                         'legacy_rounded_frame')

    def test_hdf5_preserves_representation(self):
        with tempfile.TemporaryDirectory() as tmp:
            with h5py.File(Path(tmp) / 'surface.h5', 'w') as f:
                group = f.create_group('surface 1')
                for key, value in dict(data_file='fixture.h5',
                                       dataset='/coils/coil_002',
                                       content_id='sha256:fixture',
                                       representation='exact_control_offset').items():
                    group[key] = value
                restored = openmc.SweptSplineSurface._from_hdf5(group)
                self.assertEqual(restored.representation, 'exact_control_offset')

    def test_unsupported_selector_rejected(self):
        with self.assertRaises(ValueError):
            openmc.SweptSplineSurface('fixture.h5', dataset_prefix='/coils/coil_',
                                     dataset_count=3, representation='exact_control_offset')
        with self.assertRaises(ValueError):
            openmc.SweptSplineSurface('fixture.h5', dataset='/coils/coil_002',
                                     content_id='sha256:fixture', representation='guess')


if __name__ == '__main__':
    unittest.main()
