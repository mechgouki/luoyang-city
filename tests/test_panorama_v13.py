"""The candidate cannot silently replace V12 or weaken earlier evidence."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from panorama_v13 import validate_record
from panorama_v13_contract import HOME_ANCHOR, HOME_ENTRY, KEY, add_home, restore_home
from panorama_v13_verify import verify


class CandidateContract(unittest.TestCase):
    def test_exact_entry_restores_the_previous_homepage(self):
        before = b"<main>" + HOME_ANCHOR + b"</main>"
        after = add_home(before)
        self.assertEqual(restore_home(after), before)
        self.assertEqual(add_home(after), after)
        with self.assertRaises(ValueError):
            restore_home(after.replace(b'./luoyang-panorama-v13.html', b'./different.html'))
        with self.assertRaises(ValueError):
            restore_home(after + HOME_ENTRY)
        changed = after.replace(b"<main>", b"<main data-unexpected=\"yes\">")
        self.assertNotEqual(restore_home(changed), before)

    def test_candidate_metadata_cannot_claim_approval_or_crop_mobile(self):
        record = json.loads((ROOT / "research/panorama-r8/image-record.json").read_bytes())
        validate_record(record)
        for field, value in (("homepage_replacement_approved", True), ("status", "approved")):
            changed = copy.deepcopy(record)
            changed[field] = value
            with self.assertRaises(AssertionError):
                validate_record(changed)
        changed = copy.deepcopy(record)
        changed["small"]["height"] *= 2
        with self.assertRaises(AssertionError):
            validate_record(changed)
        changed = copy.deepcopy(record)
        changed["source_png_sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            validate_record(changed)
        changed = copy.deepcopy(record)
        changed["source_png"]["width"] += 1
        with self.assertRaises(AssertionError):
            validate_record(changed)


class CandidateDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = ROOT / "_site"
        cls.info = json.loads((cls.site / "build-info.json").read_bytes())

    def test_resources_provenance_and_previous_homepage(self):
        read = lambda path: (self.site / path).read_bytes()
        result = verify(self.info, read, build_control_reader=read)
        self.assertEqual(result["status"], "passed")
        self.assertFalse(result["homepage_replacement_approved"])
        self.assertEqual(result["homepage_revision"], "panorama-approved-v12")
        self.assertEqual(result["reversible_homepages"], 2)

    def test_changed_candidate_or_earlier_evidence_is_rejected(self):
        for target in (self.info[KEY]["images"]["v13"]["full"], "city-nodes/segments.csv"):
            with self.subTest(path=target):
                def changed(path):
                    raw = (self.site / path).read_bytes()
                    return raw + b"tampered" if path == target else raw
                with self.assertRaises(AssertionError):
                    verify(self.info, changed)


if __name__ == "__main__":
    unittest.main()
