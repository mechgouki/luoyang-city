"""Guard catalog dates, source identity and unsupported source-chain upgrades."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source_continuity_b7', ROOT / 'tools/source_continuity_b7.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class SourceContinuityChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = review.read_data()
        cls.records = {record['id']: record for record in cls.data['records']}

    def test_catalog_dates_do_not_collapse_into_survey_or_printing_dates(self):
        review.validate_data(self.data)
        z, y, s = (self.records[key] for key in ('zhengzhou-1942', 'yanshi-1934', 'sishui-1935'))
        self.assertEqual((z['photography_date'], z['survey_date'], z['publication_date_as_cataloged']), ('1942-08', '1942-11', '[1942]'))
        self.assertEqual((y['upstream_map_date'], y['plate_date'], y['publication_date_as_cataloged']), ('1926', '1934', '1934.4'))
        self.assertEqual((s['upstream_map_date'], s['plate_date'], s['publication_date_as_cataloged']), ('1931', '1934', '1935.1'))
        self.assertEqual(s['upstream_map_scale_denominator'], 50000)
        changed = copy.deepcopy(self.data)
        changed['records'][1]['survey_date'] = '1934'
        with self.assertRaisesRegex(ValueError, 'Plate making is not a new survey'):
            review.validate_data(changed)
        changed = copy.deepcopy(self.data)
        changed['records'][0]['publication_date_as_cataloged'] = '1942'
        with self.assertRaisesRegex(ValueError, 'inferred publication'):
            review.validate_data(changed)

    def test_official_record_identities_and_catalog_only_evidence_are_explicit(self):
        expected = {'zhengzhou-1942': ('YG821-2507', '000008299342'), 'yanshi-1934': ('YG821-2519', '000008299355'), 'sishui-1935': ('YG821-2516', '000008299352')}
        for key, ids in expected.items():
            record = self.records[key]
            self.assertEqual((record['call_number'], record['bibliographic_id']), ids)
            self.assertTrue(record['catalog_only'])
            self.assertFalse(record['original_scan_seen_in_this_batch'])
            self.assertIsNone(record['raw_scan_crop_xyxy'])
        changed = copy.deepcopy(self.data)
        changed['records'][0]['original_scan_seen_in_this_batch'] = True
        with self.assertRaisesRegex(ValueError, 'No original image'):
            review.validate_data(changed)

    def test_period_and_scale_compatibility_are_not_actual_source_matches(self):
        self.assertTrue(self.records['zhengzhou-1942']['period_matches_l500_west_citation'])
        for record in self.data['records']:
            self.assertFalse(record['actual_l500_source_match'])
            self.assertFalse(record['actual_l531_source_match'])
        relation = next(row for row in self.data['baseline_relations'] if row['id'] == 'L500-east')
        self.assertFalse(relation['japanese_source_listed'])
        changed = copy.deepcopy(self.data)
        changed['records'][2]['actual_l531_source_match'] = True
        with self.assertRaisesRegex(ValueError, 'does not establish map use'):
            review.validate_data(changed)

    def test_no_datum_point_coordinate_or_historical_scan_is_invented(self):
        self.assertIsNone(self.data['original_horizontal_datum'])
        self.assertIsNone(self.data['original_geographic_crs'])
        self.assertEqual(self.data['approved_ground_control_points'], [])
        self.assertEqual(self.data['source_assets'], [])
        self.assertEqual(self.data['ancient_geographic_positions_added'], 0)
        self.assertFalse(self.data['modern_dsm_modified'])
        changed = copy.deepcopy(self.data)
        changed['original_horizontal_datum'] = 'WGS84'
        with self.assertRaisesRegex(ValueError, 'No original-map datum'):
            review.validate_data(changed)
        changed = copy.deepcopy(self.data)
        changed['records'][0]['coordinates'] = [112.0, 34.0]
        with self.assertRaisesRegex(ValueError, 'No pixels or geographic points'):
            review.validate_data(changed)

    def test_isolated_build_preserves_identity_and_packages_a_reproducible_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            identity = {'source_commit': 'reviewed-publication-commit', 'ground_review_b6': {'preserved': True}}
            (site / 'build-info.json').write_text(json.dumps(identity))
            data = review.build(site)
            published = json.loads((site / 'source-continuity/metadata.json').read_text())
            self.assertEqual(published['source_commit'], identity['source_commit'])
            self.assertEqual(published['research_input_sha256'], review.sha(review.DATA))
            after = json.loads((site / 'build-info.json').read_text())
            self.assertEqual(after['ground_review_b6'], identity['ground_review_b6'])
            self.assertEqual(after['source_continuity_b7']['metadata_sha256'], review.sha(site / 'source-continuity/metadata.json'))
            self.assertEqual(data['review_counts']['historical_scans_added'], 0)
            for filename in ('edition-summary.svg', 'continuity-summary.svg'):
                svg = ET.parse(site / 'source-continuity' / filename).getroot()
                self.assertEqual((svg.attrib['width'], svg.attrib['height']), ('2200', '1560'))
                self.assertEqual(svg.findall('.//{http://www.w3.org/2000/svg}image'), [])
            with zipfile.ZipFile(site / 'downloads/luoyang-source-continuity-b7.zip') as archive:
                names = set(archive.namelist())
                self.assertTrue({'source-continuity.html', 'source-continuity/metadata.json', 'tools/source_continuity_b7.py', 'research/dual-b7/source-continuity.json', 'build-info.json'} <= names)
                self.assertFalse(any(name.endswith(('.tif', '.tiff', '.png', '.jpg', '.wld')) for name in names))


if __name__ == '__main__':
    unittest.main()
