"""Guard source identities and the distinction between named areas and points."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ground_review_b6', ROOT / 'tools/ground_review_b6.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class GroundReviewChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = review.read_data()
        cls.b5 = json.loads((ROOT / 'research/dual-b5/historical-datum.json').read_text(encoding='utf-8'))

    def test_named_regions_do_not_become_ground_points_or_ancient_positions(self):
        review.validate_data(self.data)
        self.assertEqual(self.data['approved_ground_control_points'], [])
        self.assertEqual(self.data['ancient_geographic_positions_added'], 0)
        self.assertEqual(self.data['ancient_channels_added'], 0)
        self.assertFalse(self.data['modern_dsm_modified'])
        self.assertFalse(self.data['ground_accuracy_assessed'])
        self.assertFalse(self.data['project_registration_to_wgs84'])
        for record in self.data['candidates']:
            self.assertIsNone(record['anchor_pixel'])
            self.assertIsNone(record['coordinates'])
            self.assertFalse(record['physical_point_identified'])
            self.assertFalse(record['approved_as_ground_control'])
        changed = copy.deepcopy(self.data)
        changed['candidates'][0]['coordinates'] = [112.0, 34.0]
        with self.assertRaises(AssertionError):
            review.validate_data(changed)

    def test_original_scan_identity_and_datum_are_inherited_without_redefinition(self):
        previous = {sheet['id']: sheet for sheet in self.b5['sheets']}
        for sheet in self.data['sheets']:
            for key in ('source_url', 'source_file', 'source_sha256', 'source_size_px'):
                self.assertEqual(sheet[key], previous[sheet['id']][key])
            self.assertIsNone(sheet['original_horizontal_datum'])
            self.assertIsNone(sheet['original_geographic_crs'])
            self.assertEqual(sheet['digital_assignment_role'], 'post_publication_digitization_working_definition')
        changed = copy.deepcopy(self.data)
        changed['original_horizontal_datum'] = 'WGS84'
        with self.assertRaises(AssertionError):
            review.validate_data(changed)

    def test_candidate_decisions_have_distinct_and_specific_evidence(self):
        by_id = {record['id']: record for record in self.data['candidates']}
        baima, bridge = by_id['baima'], by_id['huanghe-railway']
        self.assertEqual(baima['status'], 'pending')
        self.assertIn('Pai-ma-ssu', baima['map_label_read'])
        self.assertIn('POPULATED PLACES', baima['map_symbol_observation'])
        self.assertIn('legend', [crop['id'] for crop in baima['crops']])
        self.assertIn('不以此审核裁决B5', baima['scope_exclusion'])
        self.assertEqual(bridge['status'], 'excluded')
        self.assertIn('PEIPING-HANKOW RAILWAY', bridge['map_label_read'])
        self.assertTrue({'1958', '1987'} <= {event['year'] for event in bridge['continuity_events']})
        self.assertIn('另立', bridge['verdict'])
        self.assertIn('桥台', bridge['admission_gate'])
        for record in [baima, bridge]:
            self.assertTrue(record['blockers'])
            self.assertTrue(record['default_source_id'] in record['source_ids'])

    def test_cited_compilation_year_is_not_substituted_for_observed_printing(self):
        records = {record['id']: record for record in self.data['lineage_records']}
        for key in ('l531-k', 'l531-l'):
            record = records[key]
            self.assertEqual(record['l500_cited_year'], 1945)
            self.assertEqual(record['observed_compiled_year'], 1945)
            self.assertEqual(record['observed_printed_year'], 1946)
            self.assertFalse(record['exact_l500_source_impression_verified'])
            self.assertEqual(record['projection_as_printed'], 'Polyconic Projection')
            self.assertIn('Yard', record['grid_as_printed'])
            self.assertIsNone(record['original_horizontal_datum'])
            self.assertIsNone(record['geographic_crs_assigned'])
        self.assertEqual(records['japanese-north-china']['status'], 'earlier_catalog_records_only')
        self.assertFalse(records['japanese-north-china']['exact_l500_source_impression_verified'])
        changed = copy.deepcopy(self.data)
        changed['lineage_records'][0]['geographic_crs_assigned'] = 'EPSG:4326'
        with self.assertRaises(AssertionError):
            review.validate_data(changed)

    def test_fixed_iiif_responses_match_reviewed_sha_and_original_region_dimensions(self):
        paths = review.verified_source_assets(self.data)
        self.assertEqual(len(paths), 4)
        expected = {
            'l531-i49-k-compilation': 'f7f1f37921964301b3ece8e764a663b91fe1665bf08c534c57d4df1227c2958b',
            'l531-i49-k-projection': '054818ddc8d48d0da8abcf598b2d3847ce216ae3ad69d4b11848ed8dba84e0a3',
            'l531-i49-l-compilation': 'd92f4b04373cad19aa0f3876cd752b7a122677adc36f5e211b296d6926dbe8ee',
            'l531-i49-l-projection': '097b128cb46814e3594e62f5cb1510954a28e39ba99f81ae0c5a9be51029be8c'}
        for asset in self.data['source_assets']:
            self.assertEqual(asset['sha256'], expected[asset['id']])
            self.assertEqual(review.sha(paths[asset['id']]), expected[asset['id']])
            self.assertIsNone(asset['source_full_image_sha256'])
            self.assertEqual(asset['size_px'], asset['raw_iiif_crop_xywh'][2:])
        with tempfile.TemporaryDirectory() as temp:
            for asset in self.data['source_assets']:
                dest = Path(temp) / asset['local_file']; dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(paths[asset['id']], dest)
            corrupted = Path(temp) / self.data['source_assets'][0]['local_file']
            corrupted.write_bytes(corrupted.read_bytes() + b'changed')
            with self.assertRaisesRegex(ValueError, 'Fixed source crop SHA-256 mismatch'):
                review.verified_source_assets(self.data, temp)

    def test_bad_original_scan_is_rejected_before_any_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / 'inputs'; cache.mkdir()
            for sheet in self.data['sheets']:
                (cache / sheet['source_file']).write_bytes(b'unreviewed scan bytes')
            site = Path(temp) / 'site'
            with self.assertRaisesRegex(ValueError, 'Original scan SHA-256 mismatch'):
                review.build(site, cache)
            self.assertFalse(site.exists())


if __name__ == '__main__':
    unittest.main()
