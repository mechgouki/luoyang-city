"""Protect B8's catalog/physical-object and access/obtainment distinctions."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source_access_b8', ROOT / 'tools/source_access_b8.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class SourceAccessChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = review.read_data()

    def test_catalog_identifier_and_documented_index_do_not_become_obtained_sheet(self):
        review.validate_data(self.data)
        upstream = {r['id']: r for r in self.data['upstream_records']}
        index = upstream['henan-1931-50k']
        self.assertEqual(index['catalog_record_number'], '4798')
        self.assertEqual(index['catalog_sheet_count'], 263)
        self.assertEqual(index['notes_as_cataloged'], '接合表1張')
        self.assertTrue(index['index_sheet_documented'])
        self.assertFalse(index['index_sheet_obtained'])
        self.assertIsNone(index['historical_sheet_number'])
        changed = copy.deepcopy(self.data)
        changed['upstream_records'][1]['historical_sheet_number'] = '4798'
        with self.assertRaisesRegex(ValueError, 'catalog item number is not'):
            review.validate_data(changed)

    def test_years_editions_and_complete_series_identity_stay_distinct(self):
        records = {r['id']: r for r in self.data['access_records']}
        self.assertEqual(records['zhengzhou-1942']['target_publication_as_cataloged'], '[1942]')
        self.assertIn('西9行南1段', records['yanshi-1934']['target_series'])
        self.assertIn('西9行南1段', records['sishui-1935']['target_series'])
        rejected = {r['id']: r for r in self.data['rejected_matches']}
        self.assertEqual(rejected['th-gaoping-1924']['candidate_name'], '高平縣')
        self.assertEqual(rejected['gifu-sishui-1934']['candidate_name'], '泗水縣')
        changed = copy.deepcopy(self.data)
        changed['comparison_records'][0]['catalog_year'] = '1926'
        with self.assertRaisesRegex(ValueError, 'collections must stay separate'):
            review.validate_data(changed)

    def test_access_routes_do_not_assert_images_copy_permission_or_geographic_points(self):
        self.assertEqual(self.data['source_assets'], [])
        self.assertEqual(self.data['approved_ground_control_points'], [])
        for record in self.data['access_records']:
            self.assertIsNone(record['public_image_url'])
            self.assertFalse(record['historical_image_inspected'])
            self.assertFalse(record['item_specific_copy_eligibility_confirmed'])
            self.assertFalse(record['actual_ams_source_match'])
        changed = copy.deepcopy(self.data)
        changed['access_records'][0]['historical_image_obtained'] = True
        with self.assertRaisesRegex(ValueError, 'Catalog access is not'):
            review.validate_data(changed)
        changed = copy.deepcopy(self.data)
        changed['original_horizontal_datum'] = 'WGS84'
        with self.assertRaisesRegex(ValueError, 'remain unknown'):
            review.validate_data(changed)

    def test_numbered_pier_is_an_exclusion_from_a_retrospective_account(self):
        pier = self.data['structure_reviews'][0]
        self.assertEqual(pier['id'], 'huanghe-railway-pier-11')
        self.assertEqual(pier['status'], 'excluded_as_continuously_surviving_point')
        self.assertIsNone(pier['coordinates'])
        self.assertIsNone(pier['anchor_pixel'])
        self.assertFalse(pier['approved_as_ground_control'])
        changed = copy.deepcopy(self.data)
        changed['structure_reviews'][0]['evidence_level'] = 'original_engineering_drawing'
        with self.assertRaisesRegex(ValueError, 'retrospective'):
            review.validate_data(changed)

    def test_offline_builder_binds_commit_and_writes_only_its_three_files(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            sentinel = '{"source_commit":"parent-owned","unrelated":true}\n'
            (site / 'build-info.json').write_text(sentinel)
            metadata = review.build_review(site, 'explicit-b8-publication')
            self.assertEqual((site / 'build-info.json').read_text(), sentinel)
            self.assertEqual(metadata['source_commit'], 'explicit-b8-publication')
            self.assertEqual(metadata['baseline_commit'], 'e959da7c16db7cb814bb7460c03e5c7d860be1fa')
            self.assertEqual(metadata['research_input_sha256'], review.sha(review.DATA))
            self.assertEqual({p.name for p in (site / 'source-access').iterdir()}, {'metadata.json', 'access-summary.svg', 'upstream-summary.svg'})
            self.assertFalse((site / 'source-access.html').exists())
            self.assertEqual(json.loads((site / 'source-access/metadata.json').read_text()), metadata)
            for name in ('access-summary.svg', 'upstream-summary.svg'):
                path = site / 'source-access' / name
                svg = ET.parse(path).getroot()
                self.assertEqual((svg.attrib['width'], svg.attrib['height']), ('2200', '1560'))
                self.assertEqual(svg.findall('.//{http://www.w3.org/2000/svg}image'), [])
                self.assertEqual(metadata['plate_sha256'][name], review.sha(path))


if __name__ == '__main__':
    unittest.main()
