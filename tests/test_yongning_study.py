"""Guard the new study's image identity and exact old-publication boundary."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from panorama_v14_contract import restore_r11_context
from yongning_study import FOLDER, MANIFEST, PAGE, verify


class YongningDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = ROOT / "_site"
        cls.info = json.loads((cls.site / "build-info.json").read_bytes())

    def test_actual_three_images_review_and_downloads_match(self):
        result = verify(self.info, lambda path: (self.site / path).read_bytes())
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["original_images"], 3)
        self.assertEqual(result["downloads"], 8)
        self.assertFalse(result["full_panorama_accepted"])
        self.assertFalse(result["homepage_replacement_approved"])

    def test_old_downloads_and_complete_r11_inventory_are_preserved(self):
        parent = self.info["panorama_review_v14"]
        self.assertEqual(len(parent["download_files"]), 27)
        self.assertFalse(any(path.startswith(FOLDER + "/") for path in parent["download_files"]))
        old, reader = restore_r11_context(self.info, lambda path: (self.site / path).read_bytes())
        self.assertNotIn(PAGE, old["files_sha256"])
        self.assertNotIn(MANIFEST, old["files_sha256"])
        self.assertFalse(any(path.startswith(FOLDER + "/") for path in old["files_sha256"]))
        self.assertEqual(json.loads(reader("release.json"))["current_milestone"], "盛时 R11.1 · 全城统一坐标复原工作平面")

    def test_changed_study_files_and_out_of_scope_pages_fail(self):
        for target in (FOLDER + "/corrected-local.png", FOLDER + "/review.json", PAGE):
            def changed(path):
                content = (self.site / path).read_bytes()
                return content + b"tampered" if path == target else content
            with self.subTest(path=target), self.assertRaises(AssertionError):
                verify(self.info, changed)
        info = copy.deepcopy(self.info)
        info["files_sha256"]["unregistered-study-page.html"] = "0" * 64
        with self.assertRaisesRegex(AssertionError, "predecessor inventory is incomplete"):
            restore_r11_context(info, lambda path: (self.site / path).read_bytes())


if __name__ == "__main__":
    unittest.main()
