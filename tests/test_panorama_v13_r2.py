"""A revised candidate cannot acquire approval, crop images or rewrite prior evidence."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from panorama_v13_r2 import validate_record
from panorama_v13_r2_contract import (HOME_ANCHOR, HOME_ENTRIES, SPATIAL_ENTRY, KEY,
    SOURCE_RECORD, add_home, strip_current_entries)
from panorama_v13_r2_verify import verify


class CandidateContract(unittest.TestCase):
    def test_two_entries_restore_previous_bytes_exactly(self):
        before = b'<main>' + HOME_ANCHOR + b'</main>'
        after = add_home(before)
        self.assertEqual(strip_current_entries(after), before)
        self.assertEqual(add_home(after), after)
        for changed in (after + SPATIAL_ENTRY, after.replace(b'./luoyang-city-spatial.html', b'./other.html'),
                        after.replace(HOME_ENTRIES, SPATIAL_ENTRY)):
            with self.assertRaises(ValueError):
                strip_current_entries(changed)
        unrelated = after.replace(b'<main>', b'<main data-change="unexpected">')
        self.assertNotEqual(strip_current_entries(unrelated), before)

    def test_candidate_guards_identity_approval_and_detail_view(self):
        record = json.loads((ROOT / SOURCE_RECORD).read_bytes())
        validate_record(record)
        for path, value in [(['homepage_replacement_approved'], True), (['status'], 'approved'),
                            (['source_png_sha256'], '0' * 64), (['source_image', 'sha256'], '0' * 64),
                            (['small', 'height'], record['small']['height'] * 2),
                            (['detail_view', 'width'], record['full']['width'] + 1)]:
            changed = copy.deepcopy(record)
            parent = changed
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(AssertionError):
                validate_record(changed)


class CandidateDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = ROOT / '_site'
        cls.info = json.loads((cls.site / 'build-info.json').read_bytes())

    def test_published_identity_details_and_protection(self):
        read = lambda p: (self.site / p).read_bytes()
        result = verify(self.info, read, build_control_reader=read)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['homepage_revision'], 'panorama-approved-v12')
        self.assertFalse(result['homepage_replacement_approved'])
        self.assertEqual(result['original_image_detail_views'], 2)
        self.assertEqual(result['reversible_homepages'], 2)

    def test_changed_candidate_or_prior_result_is_rejected(self):
        paths = (self.info[KEY]['images']['v13r2']['full'], 'panorama-v13/review.json',
                 'city-spatial-r9/manifest.json', 'city-nodes/segments.csv')
        for target in paths:
            def altered(path):
                raw = (self.site / path).read_bytes()
                return raw + b'tampered' if path == target else raw
            with self.subTest(path=target), self.assertRaises(AssertionError):
                verify(self.info, altered)


if __name__ == '__main__':
    unittest.main()
