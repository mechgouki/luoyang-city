"""Keep the paper map, digitizer's CRS assignment and internal RMS distinct."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


datum = module('historical_datum_b5', ROOT / 'tools/historical_datum_b5.py')
frame = module('historical_frame_b4_for_b5', ROOT / 'tools/historical_frame_b4.py')


class HistoricalDatumChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = datum.read_data()
        cls.b4 = json.loads((ROOT / 'research/dual-b4/historical-frame.json').read_text(encoding='utf-8'))

    def test_paper_datum_cannot_inherit_digitizer_working_definition(self):
        datum.validate_data(self.data)
        self.assertIsNone(self.data['original_horizontal_datum'])
        self.assertIsNone(self.data['original_geographic_crs'])
        self.assertFalse(self.data['project_registration_to_wgs84'])
        for sheet in self.data['sheets']:
            self.assertIsNone(sheet['paper_map']['horizontal_datum'])
            digital = sheet['digitized_product']
            self.assertEqual(digital['assigned_horizontal_datum'], 'D_WGS_1984')
            self.assertEqual(digital['assignment_role'], 'post_publication_digitization_working_definition')
            self.assertFalse(digital['original_paper_datum_identified'])
        changed = copy.deepcopy(self.data)
        changed['sheets'][0]['paper_map']['horizontal_datum'] = 'D_WGS_1984'
        with self.assertRaises(AssertionError):
            datum.validate_data(changed)

    def test_verified_source_identities_are_pinned(self):
        expected = {
            'NI49-7': ('005a2b3c81f9135ab03739f2c8f52566c554f7c7af56c6bad5d9b47927970532',
                       '0369a41628d6259def11270c77dc3fe687cf538da8404394c44ec85a6fa29577'),
            'NI49-8': ('d3525d1e86cc47536bb978721409e06852a07a3aee7298f69fb94b86cf94917c',
                       '49d7844845f30ded1e5cf82257935a2e575e79441b513af341541c27cffbf4d2')}
        self.assertEqual(len(self.data['sheets']), 2)
        for sheet in self.data['sheets']:
            digital = sheet['digitized_product']
            self.assertEqual((sheet['source_sha256'], digital['metadata_sha256']), expected[sheet['id']])
            self.assertIn('raw.githubusercontent.com/harvard-library/harvard-geodata/', digital['metadata_url'])
            self.assertIn('31403f56c50699a0fdd46b0a5620e1472aa27112', digital['metadata_url'])
            self.assertEqual(digital['process_location']['xpath'], '/metadata/dataqual/lineage/procstep[2]/procdesc')
            self.assertEqual(digital['paper_source_printed_date'], sheet['paper_map']['printed_date'])
            self.assertNotEqual(digital['raster_size_px'], sheet['source_size_px'])
        self.assertEqual(len(self.data['english_excerpt']['text'].split()), 13)

    def test_residual_conditions_and_values_are_not_conflated(self):
        original = {sheet['id']: sheet for sheet in self.b4['sheets']}
        expected_rms = {'NI49-7': 23.98942, 'NI49-8': 48.70132}
        for sheet in self.data['sheets']:
            digital = sheet['digitized_product']; b4 = sheet['b4_internal_calibration']
            self.assertEqual(digital['rms_m'], expected_rms[sheet['id']])
            self.assertEqual(digital['registration_control_count'], 4)
            self.assertIsNone(digital['model_order_reported'])
            self.assertIsNone(digital['independent_ground_check_count_reported'])
            result = frame.fit_sheet(original[sheet['id']])
            self.assertEqual(b4['fit_count'], 8)
            self.assertEqual(b4['heldout_count'], 5)
            self.assertAlmostEqual(b4['fit_rms_printed_grid_m'], result['fit']['rms_vector_printed_grid_m'], places=8)
            self.assertAlmostEqual(b4['heldout_rms_printed_grid_m'], result['internal_holdout_check']['rms_vector_printed_grid_m'], places=8)
            self.assertAlmostEqual(b4['heldout_rms_scan_px'], result['internal_holdout_check']['rms_vector_scan_px'], places=8)
            self.assertFalse(b4['ground_accuracy_assessed'])

    def test_crops_are_valid_original_pixel_rectangles(self):
        expected = {'projection-grid', 'compilation', 'reliability', 'grid-zone', 'printing', 'top-collar', 'bottom-full'}
        for sheet in self.data['sheets']:
            self.assertEqual({crop['id'] for crop in sheet['crops']}, expected)
            width, height = sheet['source_size_px']
            for crop in sheet['crops']:
                x0, y0, x1, y1 = crop['raw_scan_crop_xyxy']
                self.assertTrue(all(isinstance(v, int) for v in [x0, y0, x1, y1]))
                self.assertTrue(0 <= x0 < x1 <= width)
                self.assertTrue(0 <= y0 < y1 <= height)
            self.assertEqual(sheet['source_size_px'], next(s for s in self.b4['sheets'] if s['id'] == sheet['id'])['source_size_px'])

    def test_changed_scan_bytes_are_rejected_before_image_use(self):
        with tempfile.TemporaryDirectory() as temp:
            for sheet in self.data['sheets']:
                (Path(temp) / sheet['source_file']).write_bytes(b'not the reviewed original scan')
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                datum.verified_images(self.data, Path(temp))

    def test_latitude_band_and_compilation_lineages_remain_distinct(self):
        west, east = self.data['sheets']
        for sheet in [west, east]:
            self.assertEqual(sheet['paper_map']['grid_zone_number'], 49)
            self.assertEqual(sheet['paper_map']['grid_zone_designation_as_printed'], '49S')
            self.assertIn('纬带', sheet['paper_map']['latitude_band_interpretation'])
        self.assertEqual(len(west['paper_map']['compilation_sources']), 2)
        self.assertEqual(len(east['paper_map']['compilation_sources']), 1)
        self.assertEqual(east['paper_map']['compilation_sources'][0]['sheets'], ['I-49-K', 'I-49-L'])

    def test_no_ground_features_or_ancient_positions_are_invented(self):
        self.assertEqual(self.data['approved_ground_control_points'], [])
        self.assertEqual(self.data['ancient_geographic_positions_added'], 0)
        self.assertEqual(self.data['ancient_channels_added'], 0)
        self.assertFalse(self.data['modern_dsm_modified'])
        self.assertFalse(self.data['ground_accuracy_assessed'])
        for record in self.data['candidate_review_queue']:
            self.assertEqual(record['record_kind'], 'feature_type_screening')
            self.assertFalse(record['physical_feature_identified'])
            self.assertFalse(record['approved_as_ground_control'])
            self.assertIsNone(record['coordinates'])
        self.assertEqual(sum(r['status'] == 'pending' for r in self.data['candidate_review_queue']), 3)
        self.assertEqual(sum(r['status'] == 'excluded' for r in self.data['candidate_review_queue']), 2)


if __name__ == '__main__':
    unittest.main()
