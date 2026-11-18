"""Check the published P4.6.2 article, atlas and extracted offline edition."""
import hashlib
import json
import unittest
import zipfile
from collections import Counter
from itertools import combinations
from pathlib import Path
from urllib.parse import unquote, urlsplit

from pypdf import PdfReader
from test_prosperity_anchors_p461 import References

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/prosperity-v4/network-462"
SITE = ROOT / "_site"


class NetworkStudy(unittest.TestCase):
    def test_packaged_study(self):
        info = json.loads((SITE / "build-info.json").read_text())
        meta = info["prosperity_network_p462"]
        manifest = json.loads((SITE / meta["manifest"]).read_text())
        self.assertEqual(manifest["version"], meta["version"])
        self.assertEqual(manifest["source_commit"], "576b6a6dbb3fe6d688f712a36f48a6a752e53d5f")
        page = (SITE / meta["page"]).read_text()
        svg = (SOURCE / "network.svg").read_text()
        figure = svg[svg.index("<svg"):svg.rindex("</svg>") + len("</svg>")]
        self.assertEqual(page.count(figure), 1)
        ENTRY = next(line + "\n" for line in page.splitlines() if line.startswith('<p id="p463-entry">'))
        self.assertEqual(page.count(ENTRY), 1)
        self.assertEqual(page.replace(ENTRY, "").replace(figure, "<!-- NETWORK_SVG -->"), (SOURCE / "index.html").read_text())
        expected_sources = {"network-462/" + p.relative_to(SOURCE).as_posix()
                            for p in SOURCE.rglob("*") if p.is_file() and p != SOURCE / "index.html"}
        self.assertEqual(set(manifest["files_sha256"]), expected_sources | {meta["atlas"]})
        plates = meta["atlas_plates"]
        self.assertEqual(set(plates), {Path(name).name for name in expected_sources if name.endswith(".svg")})
        self.assertEqual(len(PdfReader(SITE / meta["atlas"]).pages), len(plates))
        with zipfile.ZipFile(SITE / meta["bundle"]) as archive:
            members = set(archive.namelist())
            self.assertEqual(members, set(manifest["files_sha256"]) | {"index.html", meta["manifest"]})
            index = archive.read("index.html")
            self.assertEqual(hashlib.sha256(index).hexdigest(), manifest["offline_index_sha256"])
            self.assertEqual(archive.read(meta["manifest"]), (SITE / meta["manifest"]).read_bytes())
            for name, checksum in manifest["files_sha256"].items():
                data = archive.read(name)
                self.assertEqual(hashlib.sha256(data).hexdigest(), checksum, name)
                self.assertEqual(info["files_sha256"][name], checksum, name)
                self.assertEqual(data, (SITE / name).read_bytes(), name)
                if name in expected_sources:
                    self.assertEqual(data, (SOURCE / Path(name).relative_to("network-462")).read_bytes(), name)
            refs = References()
            refs.feed(index.decode())
            for url in refs.urls:
                parts = urlsplit(url)
                if parts.scheme or parts.netloc:
                    continue
                if parts.path:
                    self.assertIn(unquote(parts.path).removeprefix("./"), members, url)
                elif parts.fragment:
                    self.assertIn(unquote(parts.fragment), refs.ids, url)

    def test_source_road_relations(self):
        study = json.loads((SITE / "network-462/network.json").read_text())
        roads = study["roads"]
        original = json.loads((ROOT / "research/prosperity-v1/geographic-evidence.json").read_text())
        features = {record["id"]: record for record in original["features"]}
        for record in [*roads.values(), *study["walls"]]:
            self.assertEqual(record["parts"], features[record["id"]]["source_pdf_geometry"]["coordinates"])
        for gate in study["gates"]:
            self.assertEqual(gate["point"], features[gate["id"]]["source_pdf_geometry"]["coordinates"])
        river = features[study["river"]["id"]]
        self.assertEqual(river["layer"], "modern_geographic_reference")
        self.assertEqual(study["river"]["points"], river["source_pdf_geometry"]["coordinates"])
        self.assertEqual(len(roads), 8)
        self.assertEqual(study["sources"]["page"], 3457)
        pairs = study["road_pairs"]
        self.assertEqual({tuple(sorted(row["roads"])) for row in pairs}, set(combinations(sorted(roads), 2)))
        self.assertEqual(Counter(row["relation"] for row in pairs), {"intersects": 11, "near": 1, "separate": 16})
        for row in pairs:
            if row["relation"] == "intersects":
                self.assertTrue(row["intersections"])
                self.assertEqual(row["distance_pt"], 0)
            else:
                self.assertFalse(row["intersections"])
                self.assertGreater(row["distance_pt"], 0)
        water_checks = study["road_to_river"]
        self.assertEqual({row["road"] for row in water_checks}, set(roads))
        self.assertTrue(all(row["relation"] == "separate" and not row["intersections"] for row in water_checks))
        gaps = study["road_gaps"]
        self.assertEqual(Counter(row["kind"] for row in gaps), {"aligned": 21, "seam": 1})
        self.assertEqual({(row["road"], *row["parts"]) for row in gaps}, {
            (road, part, part + 1) for road, rec in roads.items() for part in range(1, len(rec["parts"]))
        })
        for gap in gaps:
            a, b = gap["parts"]
            parts = roads[gap["road"]]["parts"]
            self.assertEqual(gap["points"], [parts[a - 1][-1], parts[b - 1][0]])

    def test_documentary_evidence_and_limits(self):
        data = SITE / "network-462"
        roads = json.loads((data / "roads.json").read_text())
        self.assertEqual(roads["source_sha256"], hashlib.sha256((ROOT / roads["source_data"]).read_bytes()).hexdigest())
        network = json.loads((data / "network.json").read_text())
        pairs = {tuple(row["roads"]): row for row in network["road_pairs"]}
        self.assertEqual(len(roads["junctions"]), 12)
        for item in roads["junctions"]:
            computed = pairs[tuple(item["pair"])]
            self.assertEqual(bool(computed["intersections"]), bool(item.get("intersection_pdf_xy")))
        self.assertEqual(roads["new_field_control_points"], 0)
        self.assertEqual(roads["new_historical_gis_geometry"], 0)

        outer = json.loads((data / "outer.json").read_text())
        self.assertEqual({row["id"] for row in outer["corridors"]}, {"W1", "W2", "W3", "E1", "E2", "E3"})
        self.assertEqual({(row["gate"], row["width_m"]) for row in outer["reported_widths"]},
                         {("E2", 18), ("E2", 8), ("W1", 30), ("W3", 40)})
        east = json.loads((data / "east.json").read_text())
        self.assertTrue((data / east["bibliography"]).is_file())
        self.assertIsNone(east["period_question"]["coordinates"])
        self.assertIsNone(east["period_question"]["shoreline"])
        bridges = json.loads((data / "crossings.json").read_text())
        self.assertEqual({row["name"] for row in bridges["crossings"]}, {"建春门石桥", "东石桥", "七里桥"})
        southern = json.loads((data / "waters.json").read_text())
        self.assertTrue(southern["source_epochs_are_distinct"])
        self.assertIsNone(southern["modern_coordinates"])
        self.assertIsNone(southern["local_gis_transform"])
        self.assertIn("xuanyang-yongqiao", {row["id"] for row in southern["relations"]})
