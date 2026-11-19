"""Keep the water atlas's historical uncertainties in its data and published maps."""
import hashlib
import json
import re
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/prosperity-v4/water-467"
SITE = ROOT / "_site"
NS = "{http://www.w3.org/2000/svg}"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def reachable(plate, start):
    """Follow only asserted water flow, never proximity or a proposed canal."""
    found, pending = {start}, [start]
    while pending:
        current = pending.pop()
        for segment in plate["segments"]:
            if segment["relationship_type"] == "flow" and segment["from"] == current:
                target = segment["to"]
                if target not in found:
                    found.add(target)
                    pending.append(target)
    return found


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.add(dict(attrs).get("href"))


class WaterEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read(SOURCE / "readings.json")
        cls.plates = {plate["id"]: plate for plate in cls.data["plates"]}
        cls.segments = {segment["id"]: segment
                        for plate in cls.data["plates"] for segment in plate["segments"]}

    def test_gate_inlets_and_pool_entities_remain_distinct(self):
        inner = self.plates["inner"]
        nodes = {node["id"]: node for node in inner["nodes"]}
        self.assertIn("西城阊阖", nodes["west-in"]["label"])
        self.assertIn("宫城南阊阖", nodes["palace-changhe"]["label"])
        self.assertNotEqual(nodes["west-in"]["id"], nodes["palace-changhe"]["id"])
        self.assertTrue({"tianyuan", "county-south-pool", "lingzhi-jiulong"} <= nodes.keys())
        self.assertEqual((self.segments["I02"]["from"], self.segments["I02"]["to"]),
                         ("tianyuan", "county-south-pool"))
        self.assertEqual((self.segments["I04"]["from"], self.segments["I04"]["to"]),
                         ("qianqiu", "lingzhi-jiulong"))
        self.assertEqual({self.segments[key]["relationship_type"] for key in ("I10", "I11")},
                         {"connection"})
        self.assertNotIn("yangqu-linked", reachable(inner, "imperial-pools"))
        self.assertNotIn("diquan-linked", reachable(inner, "imperial-pools"))
        phase_nodes = {node["id"] for node in self.plates["phases"]["nodes"]}
        self.assertTrue({"west-luo", "west-wangcheng", "west-gu",
                         "south-luo", "south-diversion", "south-yangqu"} <= phase_nodes)
        west = {self.segments[key][side] for key in ("P01", "P02") for side in ("from", "to")}
        south = {self.segments[key][side] for key in ("P03", "P04") for side in ("from", "to")}
        self.assertTrue(west.isdisjoint(south), "The two historically distinct Luo diversions merged")

    def test_outer_flow_keeps_the_unlocated_junctions_open(self):
        outer = self.plates["outer"]
        self.assertIn("mashi", reachable(outer, "qianjin"))
        self.assertNotIn("west-changhe", reachable(outer, "qianjin"),
                         "No source fixes the northern/western branch split at Qianjin or Xiliang")
        self.assertIn("luoyang-gou", reachable(outer, "southeast"))
        self.assertNotIn("jianchun", reachable(outer, "luoyang-gou"))
        self.assertNotIn("mashi", reachable(outer, "luoyang-gou"))
        outlet = self.segments["O08"]
        self.assertEqual((outlet["from"], outlet["to"], outlet["relationship_type"]),
                         ("ximing", "qingyang-right", "flow"))
        self.assertIn("下注陽渠", outlet["quote"])
        for plate in self.data["plates"]:
            for node in plate["nodes"]:
                self.assertNotRegex(node["label"], r"[泾涇][阳陽]渠")
        self.assertEqual(reachable(self.plates["inner"], "south-channel"), {"south-channel"})

        # The regional tributaries constrain direction, not an exact city junction.
        regional = self.plates["regional"]
        for sid, endpoints in {
            "R01": ("yique", "yi-east"),
            "R02": ("yi-east", "yi-luo"),
            "R04": ("zize", "chan"),
            "R05": ("chan", "chan-gu"),
            "R06": ("jian-now", "jian-network"),
            "R07": ("jian-network", "jian-luo"),
            "R09": ("jingu", "jingu-gu"),
        }.items():
            with self.subTest(segment=sid):
                segment = self.segments[sid]
                self.assertEqual((segment["from"], segment["to"]), endpoints)
                self.assertEqual((segment["relationship_type"], segment["period_class"]),
                                 ("flow", "text_context"))
        self.assertEqual(self.segments["R03"]["relationship_type"], "adjacency")
        self.assertEqual(reachable(regional, "yuanqiu"), {"yuanqiu"},
                         "The altar's relative location must not become a water source")
        self.assertNotIn("chan-gu", reachable(regional, "jian-now"),
                         "The separate Chan and Jian descriptions do not establish one shared inlet")

    def test_early_events_and_proposals_do_not_become_current_water(self):
        for sid in ("P01", "P02", "P03", "P04"):
            with self.subTest(segment=sid):
                segment = self.segments[sid]
                self.assertEqual(segment["period_class"], "older_event")
                self.assertEqual(segment["relationship_type"], "connection")
        for sid, endpoints in (("P05", ("plan496-luo", "plan496-gu")),
                               ("P06", ("plan-hongchi", "plan-luo"))):
            with self.subTest(segment=sid):
                segment = self.segments[sid]
                self.assertEqual((segment["from"], segment["to"]), endpoints)
                self.assertEqual((segment["relationship_type"], segment["period_class"]),
                                 ("proposal", "proposal"))
        self.assertIn("將通", self.segments["P05"]["quote"])
        self.assertIn("朕欲", self.segments["P06"]["quote"])
        self.assertEqual(self.segments["P07"]["relationship_type"], "adjacency")
        self.assertEqual((self.segments["P08"]["relationship_type"],
                          self.segments["P08"]["period_class"]), ("flow", "older_event"))
        for sid, endpoints in {
            "R08": ("jian-old", "jian-old-luo"),
            "R10": ("lake-flood", "hugou"),
            "R11": ("hugou", "hugou-chan"),
        }.items():
            with self.subTest(segment=sid):
                segment = self.segments[sid]
                self.assertEqual((segment["from"], segment["to"]), endpoints)
                self.assertEqual((segment["relationship_type"], segment["period_class"]),
                                 ("flow", "older_event"))
        self.assertNotEqual(self.segments["R08"]["from"], self.segments["R06"]["from"])
        self.assertNotEqual(self.segments["R08"]["to"], self.segments["R07"]["to"])

    def test_qili_alternatives_and_survey_endpoint_stay_conditional(self):
        east = self.plates["east-readings"]
        for sid in ("EAST01", "EAST02", "EAST03", "EAST04", "EAST05"):
            with self.subTest(segment=sid):
                segment = self.segments[sid]
                self.assertEqual((segment["relationship_type"], segment["period_class"]),
                                 ("hypothesis", "interpretation"))
        self.assertIn("偃师城南", self.segments["EAST03"]["limit"])
        self.assertIn("尾", self.segments["EAST03"]["limit"])
        for sid in ("EAST06", "EAST07"):
            self.assertEqual((self.segments[sid]["relationship_type"],
                              self.segments[sid]["period_class"]), ("connection", "broad_survey"))
        self.assertEqual(self.segments["EAST07"]["to"], "survey-dongtun")
        self.assertFalse(any(segment[side] == "inferred-mouth"
                             for segment in east["segments"] for side in ("from", "to")),
                         "A terrain-inferred mouth must not extend the observed survey line")
        for plate in self.data["plates"]:
            nodes = {node["id"]: node["label"] for node in plate["nodes"]}
            for start, label in nodes.items():
                if "鸿池" in label or "洪池" in label:
                    destinations = reachable(plate, start) - {start}
                    self.assertFalse(any("七里" in nodes[target] for target in destinations),
                                     "The disputed Hongchi-to-Qili join became an asserted flow path")

    def test_legacy_coverage_and_layout_only_coordinates(self):
        old = read(ROOT / "research/prosperity-v4/hydro-roads-anchor-p46.json")["water_features"]
        expected = {item["id"] for item in old}
        self.assertEqual(len(expected), 34)
        coverage = self.data["legacy_water_coverage"]
        self.assertEqual(len(coverage), 34)
        self.assertEqual({item["旧编号"] for item in coverage}, expected)
        self.assertTrue(all(item["状态"].strip() for item in coverage))
        for item in coverage:
            for sid in re.findall(r"(?:EAST|[OIPR])\d{2}", item["本册图段"]):
                self.assertIn(sid, self.segments, item["旧编号"])
        self.assertEqual(self.data["target_period"], [516, 528])
        self.assertIsNone(self.data["geographic_coordinates"])
        self.assertIsNone(self.data["new_516_528_bank_geometry"])
        self.assertEqual(self.data["new_metric_measurements"], 0)
        self.assertIn("页面布局", self.data["coordinate_system"])

        def check(value, trail="readings"):
            if isinstance(value, dict):
                for key, child in value.items():
                    path = f"{trail}.{key}"
                    geographic = key in {"latitude", "longitude", "lat", "lon", "lng", "crs",
                                         "modern_coordinates", "geographic_coordinates", "local_gis_transform"}
                    measured = bool(re.search(r"(?:width|depth|length|distance).*_(?:m|km)$", key))
                    if geographic or measured:
                        self.assertIsNone(child, path)
                    check(child, path)
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    check(child, f"{trail}[{index}]")
        check(self.data)


class WaterPublication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = read(SOURCE / "readings.json")
        cls.info = read(SITE / "build-info.json")
        cls.meta = cls.info["prosperity_water_p467"]

    def test_published_svg_arrows_follow_evidence_types(self):
        for plate in self.raw["plates"]:
            svg = ET.parse(SITE / f"water-467/{plate['id']}.svg").getroot()
            self.assertEqual(svg.get("data-water-map"), plate["id"])
            groups = {group.get("data-segment-id"): group for group in svg.iter(NS + "g")
                      if group.get("class") == "water-segment"}
            self.assertEqual(set(groups), {segment["id"] for segment in plate["segments"]})
            for segment in plate["segments"]:
                with self.subTest(segment=segment["id"]):
                    group = groups[segment["id"]]
                    self.assertEqual((group.get("data-from"), group.get("data-to")),
                                     (segment["from"], segment["to"]))
                    self.assertEqual(group.get("data-relationship"), segment["relationship_type"])
                    self.assertEqual(group.get("data-period-class"), segment["period_class"])
                    routes = [path for path in group.findall(NS + "path")
                              if path.get("class") == "segment-route"]
                    self.assertEqual(len(routes), 1)
                    route = routes[0]
                    self.assertEqual(bool(route.get("marker-end")), segment["relationship_type"] == "flow")
                    if segment["period_class"] != "text_context":
                        self.assertTrue(route.get("stroke-dasharray"), "A noncurrent layer lost its distinct style")

    def test_atlas_and_source_downloads_match_the_published_sections(self):
        plates = self.raw["plates"]
        plate_ids = {plate["id"] for plate in plates}
        self.assertTrue({"outer", "inner", "east-readings", "phases", "regional"} <= plate_ids)
        self.assertEqual(len(self.meta["plates"]), len(plates))
        self.assertEqual(set(self.meta["plates"]), {f"{pid}.svg" for pid in plate_ids})
        self.assertEqual(self.meta["atlas_pages"], len(plates))
        self.assertEqual(len(PdfReader(SITE / self.meta["atlas"]).pages), len(plates))
        self.assertTrue(self.meta["layout_coordinates_only"])
        self.assertEqual(self.meta["geographic_coordinates_added"], 0)
        self.assertEqual(read(SITE / self.meta["readings"]), self.raw)

        page = (SITE / self.meta["page"]).read_text(encoding="utf-8")
        self.assertEqual(set(re.findall(r'data-water-map="([^"]+)"', page)), plate_ids)
        links = Links()
        links.feed(page)
        self.assertIn(self.meta["atlas"], links.hrefs)
        expected_sources = {f"water-467/{path.name}" for path in SOURCE.glob("*.json")}
        self.assertEqual(set(self.meta["data_files"]), expected_sources)
        for name in expected_sources:
            self.assertIn(name, links.hrefs, "Source evidence exists but is absent from downloads")
            self.assertEqual((SITE / name).read_bytes(), (SOURCE / Path(name).name).read_bytes())
        for pid in plate_ids:
            self.assertIn(f"water-467/{pid}.svg", links.hrefs)
        publications = expected_sources | {f"water-467/{pid}.svg" for pid in plate_ids}
        publications |= {self.meta["page"], self.meta["atlas"],
                         "water-467/study.css", "water-467/water-ui.js"}
        for name in publications:
            self.assertEqual(hashlib.sha256((SITE / name).read_bytes()).hexdigest(),
                             self.info["files_sha256"][name], name)


if __name__ == "__main__":
    unittest.main()
