"""The road spacings and each author's pond contacts retain independent frames."""
import hashlib
import json
import math
import unittest
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

from pypdf import PdfReader
from test_prosperity_anchors_p461 import References

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"


class CorridorsStudy(unittest.TestCase):
    def test_study_and_readings(self):
        record = json.loads((SITE / "corridors-463/evidence.json").read_text())
        ward = record["ward"]
        self.assertEqual((ward["ns_offsets_m"], ward["ew_offsets_m"]), ([-86,0,86],[-40,0,40]))
        self.assertEqual((ward["central_ns_width_m"], ward["gate_gap_m"]), (22,7.5))
        self.assertIsNone(ward["gate_to_central_cross_m"])
        older = json.loads((SITE / "network-462/outer.json").read_text())
        self.assertEqual({r[2] for r in record["roads"] if r[2]}, {r["id"] for r in older["corridors"]})
        self.assertEqual((len(set(r[0] for r in record["roads"])),len(record["southern_separate"])), (9,2))
        pond = record["hongchi"]
        self.assertEqual([len(f["contacts"]) for f in pond["figures"]],[4,3])
        self.assertIsNone(pond["northern_wei_shoreline"])
        self.assertEqual(pond["archaeological_control"]["period"],"商代")
        for figure in pond["figures"]:
            left, top, right, bottom = figure["crop_xyxy"]
            self.assertTrue(0 <= left < right <= figure["size"][0])
            self.assertTrue(0 <= top < bottom <= figure["size"][1])
            for side, name, (x, y) in figure["contacts"]:
                self.assertTrue(left < x < right and top < y < bottom, (side, name))

    def test_field_supplement(self):
        info = json.loads((SITE / "build-info.json").read_text())
        study = info["prosperity_field_p464"]
        data = json.loads((SITE / study["readings"]).read_text())
        self.assertEqual(len(PdfReader(SITE / study["atlas"]).pages), 2)
        self.assertEqual(len(study["plates"]), 2)
        ward = data["ward"]
        self.assertEqual((ward["rut_band_width_m"], ward["groove_ew_length_approx_m"], ward["groove_ns_width_m"]), (4.6, 4.6, 0.4))
        self.assertEqual(ward["east_foundation_ew_exposed_gt_m"], 24)
        self.assertIsNone(ward["gate_to_central_cross_m"])
        self.assertIsNone(data["hongchi"]["southern_outlet_516_528_coordinates"])
        self.assertEqual(data["hongchi"]["pond_internal_bank_orientation"], "东西")

    def test_gate_readings_in_their_source_frames(self):
        info = json.loads((SITE / "build-info.json").read_text())
        study = info["prosperity_gates_p465"]
        data = json.loads((SITE / study["readings"]).read_text())
        self.assertEqual(len(PdfReader(SITE / study["atlas"]).pages), 3)
        field = data["field_plan"]
        self.assertEqual(set(field["points"]), {"IV", "V", "VI", "VII"})
        self.assertIsNone(field["excluded_gap"]["formal_gate_or_named_road"])
        later = data["later_plan"]
        self.assertNotEqual(field["size_px"], later["size_px"])
        scale = math.dist(*later["scale_endpoints_px"])
        self.assertEqual(scale, later["scale_px_per_km"])
        for road in later["north"]:
            first, last = road["to_wall_px"][0], road["to_wall_px"][-1]
            self.assertEqual(last, road["beyond_wall_to_frame_px"][0])
            self.assertEqual(round(math.dist(first, last) / scale, 1), road["chord_km_one_decimal"])
        self.assertFalse(later["source_map_merge_visible"])
        self.assertTrue(all(value is None for value in data["open_endpoints"].values()))
        self.assertIsNone(data["moat"]["water_depth_516_528_m"])
        self.assertEqual(data["moat"]["channel_width_approx_m"], [20, 24])

    def test_southern_roads_and_water_evidence(self):
        info = json.loads((SITE / "build-info.json").read_text())
        study = info["prosperity_south_p466"]
        self.assertEqual(len(PdfReader(SITE / study["atlas"]).pages), 3)
        data = json.loads((SITE / study["readings"]).read_text())
        plan = data["plan"]
        centers = [sum(edges)/2 for edges in plan["road_edges_at_row_px"].values()]
        gap = abs(centers[1] - centers[0])
        self.assertEqual(gap, plan["symbol_spacing_px"])
        self.assertEqual(round(gap/math.dist(*plan["scale_endpoints_px"]), 1), plan["map_spacing_approx_km"])
        ditch = data["excavation"]["biyong"]
        self.assertEqual((ditch["trunk_preserved_m"], ditch["fork_north_of_hall_approx_m"],
                          ditch["lateral_each_gt_m"], ditch["south_each_approx_m"]), (180,156,180,400))
        self.assertTrue(all(ditch[x] is None for x in ("flow_516_528","southern_closure","water_source")))
        self.assertIsNone(data["diversion"]["section_width_m"])
        self.assertFalse(data["diversion"]["section_read"])
        self.assertEqual(data["texts"]["bank_landings"], [None,None])
        self.assertIsNone(data["modern_coordinates"])

    def test_offline_edition(self):
        info = json.loads((SITE/"build-info.json").read_text())
        study = info["prosperity_corridors_p463"]
        self.assertEqual(len(PdfReader(SITE/study["atlas"]).pages),3)
        with zipfile.ZipFile(SITE/study["bundle"]) as archive:
            manifest = json.loads(archive.read(study["manifest"]))
            self.assertEqual(manifest["source_commit"], study["source_commit"])
            for name, digest in manifest["files_sha256"].items():
                self.assertEqual(archive.read(name), (SITE/name).read_bytes())
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(),digest)
            index = archive.read("index.html")
            self.assertEqual(hashlib.sha256(index).hexdigest(), manifest["offline_index_sha256"])
            refs = References()
            refs.feed(index.decode())
            for url in refs.urls:
                parts = urlsplit(url)
                if parts.scheme or parts.netloc:
                    continue
                if parts.path:
                    self.assertIn(unquote(parts.path).removeprefix("./"),archive.namelist())
                elif parts.fragment:
                    self.assertIn(unquote(parts.fragment),refs.ids)
