"""Complete road coverage, source identity and delivery remain independently verifiable."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from verify_all_road_atlas_r62 import SOURCE, verify, verify_catalog, verify_evidence_boundaries


class AllRoadAtlas(unittest.TestCase):
    def test_all_known_road_families_have_evidence_records(self):
        report = verify_catalog(json.loads(SOURCE.read_bytes()))
        self.assertEqual(report["groups"]["legacy"], 21)
        self.assertEqual(report["documentary_entities"], 21)
        self.assertEqual(report["bridge_entities"], 5)

    def test_local_widths_passage_components_and_unknowns_are_not_promoted(self):
        report = verify_evidence_boundaries(json.loads(SOURCE.read_bytes()))
        self.assertEqual(report["ward_streets"], 6)
        self.assertEqual(report["unresolved_ward_road_class"], 1)
        self.assertIsNone(report["third_gate_passage_count"])

    def test_downloads_offline_bundle_and_predecessors(self):
        site = ROOT / "_site"
        info = json.loads((site / "build-info.json").read_bytes())
        report = verify(info, lambda path: (site / path).read_bytes())
        self.assertEqual(report["downloads"], 6)
        self.assertEqual(report["offline_members"], 8)
        self.assertEqual(report["preservation"]["old_sources"], 21)


if __name__ == "__main__":
    unittest.main()
