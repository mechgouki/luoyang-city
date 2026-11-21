"""Road source identity, independent frames, and uncertainty remain part of the public release."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from verify_road_atlas_r6 import ROAD_IDS, verify, verify_research


class RoadAtlas(unittest.TestCase):
    site = ROOT / "_site"

    def test_published_release_and_downloads_are_traceable(self):
        info = json.loads((self.site / "build-info.json").read_bytes())
        report = verify(info, lambda path: (self.site / path).read_bytes())
        self.assertEqual(report["records"], 21)
        self.assertEqual(report["supplements"], 3)
        self.assertEqual(report["downloads"], 5)

    def test_old_source_ids_are_preserved_without_counting_supplements_as_new_roads(self):
        original = json.loads((ROOT / "research/prosperity-v4/hydro-roads-anchor-p46.json").read_bytes())
        data = json.loads((self.site / "road-atlas/roads.json").read_bytes())
        self.assertEqual([r["id"] for r in original["main_road_records"]], ROAD_IDS)
        self.assertEqual([r["id"] for r in data["roads"]], ROAD_IDS)
        self.assertFalse(set(ROAD_IDS) & {r["id"] for r in data["supplements"]})

    def test_source_fragments_independent_frames_and_unknown_landings_remain_explicit(self):
        data = json.loads((ROOT / "research/roads-r6/roads.json").read_bytes())
        counts = verify_research(data)
        self.assertEqual(sum(counts.values()), 21)


if __name__ == "__main__":
    unittest.main()
