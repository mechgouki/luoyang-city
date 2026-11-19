"""Protect the evidence boundaries in the moat, palace-drain and pond supplement."""
import hashlib
import json
import re
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/prosperity-v4/water-468"
SITE = ROOT / "_site"
NS = "{http://www.w3.org/2000/svg}"
PLATES = {"west-moats", "palace-water", "fanghu-zhaoyi", "independent-pools"}
P467_DATA_SHA = "bf51dad84680792dafbaacb14bea0a0715fa31a5cf13842fd0096f762132a789"
P467_ATLAS_SHA = "68c994d5a558ee222134afd98cf15e095b6b4dce4c75d999e68c9789d4d0d404"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reachable(plate, start, undirected=False):
    """Adjacency, containment, interpretation and strata cannot convey water."""
    found, pending = {start}, [start]
    allowed = {"flow", "connection"} if undirected else {"flow"}
    while pending:
        current = pending.pop()
        for edge in plate["segments"]:
            if edge["relationship_type"] not in allowed:
                continue
            targets = []
            if edge["from"] == current:
                targets.append(edge["to"])
            if undirected and edge["to"] == current:
                targets.append(edge["from"])
            for target in targets:
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


class Water468Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read(SOURCE / "readings.json")
        cls.plates = {plate["id"]: plate for plate in cls.data["plates"]}
        cls.segments = {edge["id"]: edge for plate in cls.data["plates"]
                        for edge in plate["segments"]}
        cls.moats = {item["id"]: item for item in
                     read(SOURCE / "moats-zhangfang-source-audit.json")["moat_records"]}
        cls.pools = {item["id"]: item for item in
                     read(SOURCE / "pools-source-audit.json")["records"]}

    def test_western_flood_event_does_not_identify_a_current_moat(self):
        west = self.plates["west-moats"]
        nodes = {node["id"]: node for node in west["nodes"]}
        self.assertEqual(nodes["m-west-gate"]["label"], "西城阊阖门")
        self.assertNotEqual("m-ditch", self.segments["M04"]["from"])
        self.assertNotEqual("m-ditch", self.segments["M04"]["to"])
        self.assertEqual((self.segments["M03"]["from"], self.segments["M03"]["to"],
                          self.segments["M03"]["relationship_type"]),
                         ("m-ditch", "m-shouqiu", "adjacency"))
        self.assertEqual({edge["id"] for edge in west["segments"]
                          if edge["relationship_type"] == "flow"}, {"M04"})
        self.assertEqual(self.segments["M04"]["period_class"], "older_event")
        for sid in ("M05", "M06", "M07", "M08"):
            with self.subTest(segment=sid):
                edge = self.segments[sid]
                self.assertEqual((edge["relationship_type"], edge["period_class"]),
                                 ("hypothesis", "interpretation"))
        for sid in ("M09", "M10"):
            edge = self.segments[sid]
            self.assertEqual((edge["relationship_type"], edge["period_class"]),
                             ("adjacency", "broad_survey"))
            for endpoint in (edge["from"], edge["to"]):
                self.assertEqual(reachable(west, endpoint, undirected=True), {endpoint},
                                 "A surveyed moat acquired an unproved hydraulic join")

    def test_moat_summary_preserves_the_scope_and_distinct_depth_quantities(self):
        west, east = self.moats["MOAT-W"], self.moats["MOAT-E"]
        for record in (west, east):
            self.assertIsNone(record["flow_direction"])
            self.assertEqual(record["target_period_516_528_status"],
                             "broad_period_includes_target_but_not_phase_resolved")
            self.assertIsNone(record["measurements"]["original_channel_depth_m"])
            self.assertIsNone(record["measurements"]["water_depth_m"])
        wm, em = west["measurements"], east["measurements"]
        self.assertEqual((wm["reported_width_m"]["minimum"],
                          wm["reported_width_m"]["maximum"]), (18, 28))
        self.assertEqual(wm["reported_warp_soil_depth_m"], {"minimum": 3, "maximum": 4})
        self.assertIsNone(wm["burial_depth_m"])
        self.assertIsNone(wm["verified_sediment_thickness_m"])
        self.assertIn("城壕概述", em["scope"])
        self.assertIn("未说明", em["scope"])
        self.assertEqual((em["usual_reported_width_m"]["minimum"],
                          em["usual_reported_width_m"]["maximum"]), (18, 40))
        self.assertEqual(em["separate_width_upper_bound_m"], 100)
        self.assertEqual(em["depth_where_mud_encountered_below_recorded_ground_m"],
                         {"minimum": 4, "maximum": 4.5})
        self.assertEqual(em["reported_accumulated_mud_thickness_m"], {"greater_than": 4})
        self.assertIsNone(em["absolute_elevation_m"])
        self.assertIn("不得相加", em["depth_semantics"])

    def test_palace_connections_do_not_invent_a_pool_outlet_or_current_old_channel(self):
        self.assertEqual({edge["id"] for edge in self.plates["palace-water"]["segments"]
                          if edge["relationship_type"] == "flow"},
                         {"D02", "D03", "D05", "D07", "D09"})
        expected = {
            "D01": "adjacency", "D02": "flow", "D03": "flow", "D04": "connection",
            "D05": "flow", "D06": "connection", "D07": "flow", "D08": "stratigraphy",
            "D09": "flow", "D10": "stratigraphy",
        }
        for sid, relationship in expected.items():
            with self.subTest(segment=sid):
                self.assertEqual(self.segments[sid]["relationship_type"], relationship)
        for sid in ("D02", "D03", "D05", "D09"):
            self.assertEqual(self.segments[sid]["period_class"], "broad_survey")
        self.assertEqual(self.segments["D07"]["period_class"], "older_event")
        for sid, endpoints in {
            "D02": ("d1-south", "d1-north"),
            "D03": ("d2-south", "d2-north"),
            "D04": ("d3-wall", "d4-join"),
            "D05": ("d4-join", "d4-south"),
            "D09": ("d-trench-north", "d-trench-south"),
        }.items():
            self.assertEqual((self.segments[sid]["from"], self.segments[sid]["to"]), endpoints)
        self.assertEqual(reachable(self.plates["palace-water"], "d-pool", undirected=True),
                         {"d-pool"}, "A nearby drain became a proven pool outlet")
        self.assertEqual(self.segments["D08"]["stratigraphic_relation"], "cuts")
        self.assertEqual(self.segments["D10"]["stratigraphic_relation"], "overlies")

    def test_palace_windows_and_channel_numbering_do_not_become_one_measured_line(self):
        def endpoints(*sids):
            return {self.segments[sid][side] for sid in sids for side in ("from", "to")}

        main = endpoints("D02", "D03", "D04", "D05", "D06")
        north = endpoints("D09")
        qianqiu = endpoints("D10")
        self.assertTrue(main.isdisjoint(north), "Main excavation and northern trench merged")
        self.assertTrue((main | north).isdisjoint(qianqiu),
                        "Qianqiu numbered conduits became the southwest numbered drains")
        palace = self.plates["palace-water"]
        for start in north | qianqiu:
            self.assertTrue(reachable(palace, start, undirected=True).isdisjoint(main),
                            "A shared direction or stratigraphic line supplied a missing connection")
        for start in qianqiu | {"d-wall-cut", "d-old-silt"}:
            self.assertEqual(reachable(palace, start, undirected=True), {start},
                             "A stratigraphic relationship became a hydraulic connection")
        early = endpoints("D07")
        for start in early:
            self.assertTrue(reachable(palace, start, undirected=True).isdisjoint(main | north),
                            "A superseded open channel became a contemporary supply route")

    def test_ancient_pool_dimensions_remain_in_original_units(self):
        dimensions = self.pools["POOL-W29"]["textual_dimensions"]
        self.assertEqual((dimensions["east_west"], dimensions["north_south"],
                          dimensions["unit"]), (190, 70, "步"))
        self.assertIsNone(dimensions["metres"])
        self.assertIsNone(dimensions["depth"])
        self.assertFalse(dimensions["transfer_to_hualin_pool"])
        self.assertNotIn("textual_dimensions", self.pools["POOL-HUALIN-FANGHU"])
        self.assertEqual(self.data["target_period"], [516, 528])
        self.assertIsNone(self.data["geographic_coordinates"])
        self.assertEqual(self.data["new_metric_measurements"], 0)
        self.assertIsNone(self.data["new_516_528_bank_geometry"])

        def check(value, trail="readings"):
            if isinstance(value, dict):
                for key, child in value.items():
                    path = f"{trail}.{key}"
                    if key in {"latitude", "longitude", "lat", "lon", "lng", "crs",
                               "modern_coordinates", "geographic_coordinates", "local_gis_transform"}:
                        self.assertIsNone(child, path)
                    check(child, path)
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    check(child, f"{trail}[{index}]")
        check(self.data)

    def test_two_fanghu_pools_and_zhaoyi_dry_pit_do_not_merge(self):
        plate = self.plates["fanghu-zhaoyi"]
        for sid, endpoints in {
            "F01": ("fanghu-gushui-outer", "fanghu-ruanqu"),
            "F02": ("fanghu-gushui-outer", "fanghu-left-pool"),
            "F03": ("fanghu-gushui-outer", "fanghu-outer"),
            "F04": ("fanghu-ruanqu", "fanghu-hongchi"),
            "F05": ("hualin-gushui-branch", "hualin-garden-water"),
            "F06": ("hualin-garden-water", "hualin-tianyuan"),
        }.items():
            edge = self.segments[sid]
            self.assertEqual((edge["from"], edge["to"], edge["relationship_type"]),
                             (*endpoints, "flow"))
        self.assertIn("fanghu-hongchi", reachable(plate, "fanghu-gushui-outer"))
        self.assertEqual(reachable(plate, "fanghu-outer"), {"fanghu-outer"},
                         "The side pool became a through-route or acquired a return outlet")
        self.assertEqual(reachable(plate, "fanghu-left-pool"), {"fanghu-left-pool"})
        self.assertEqual(self.segments["F07"]["relationship_type"], "containment")
        self.assertEqual((self.segments["F07"]["from"], self.segments["F07"]["to"]),
                         ("hualin-duting", "hualin-fanghu"))
        self.assertEqual(reachable(plate, "hualin-fanghu", undirected=True), {"hualin-fanghu"},
                         "The garden-system outlet was assigned to the hall's pool")
        self.assertTrue(reachable(plate, "fanghu-gushui-outer", undirected=True).isdisjoint(
                        reachable(plate, "hualin-gushui-branch", undirected=True)))
        nodes = {node["id"] for node in plate["nodes"]}
        separate = {"zhaoyi-pool", "zhaoyi-dry-pit", "zhaoyi-diquan-reference"}
        self.assertTrue(separate <= nodes)
        for nid in separate:
            self.assertEqual(reachable(plate, nid, undirected=True), {nid})
        self.assertEqual(self.segments["F08"]["relationship_type"], "containment")
        self.assertTrue(all(edge["from"] not in separate or edge["to"] not in separate
                            for edge in plate["segments"]),
                        "Separate textual identifications were joined on the map")

    def test_independent_ponds_and_waterpower_do_not_acquire_a_supply_network(self):
        plate = self.plates["independent-pools"]
        self.assertTrue(all(edge["relationship_type"] in {"adjacency", "containment"}
                            for edge in plate["segments"]))
        for node in plate["nodes"]:
            self.assertEqual(reachable(plate, node["id"], undirected=True), {node["id"]})
        for sid, endpoints in {
            "L01": ("l-yh-north", "l-yonghe"),
            "L02": ("l-yh-south", "l-yonghe"),
            "L04": ("l-baoguang-garden", "l-xianchi"),
            "L08": ("l-gu-reference", "l-tushan"),
            "L09": ("l-jingming", "l-jm-three"),
            "L10": ("l-jingming", "l-jm-waterpower"),
        }.items():
            self.assertEqual((self.segments[sid]["from"], self.segments[sid]["to"]), endpoints)
        for sid in ("L01", "L02"):
            self.assertIn("里南北皆有池", self.segments[sid]["quote"])
            self.assertFalse(self.segments[sid]["annual_flow_516_528_confirmed"])
        self.assertIn("每侧恰一池", self.segments["L01"]["limit"])
        self.assertIn("寺有三池", self.segments["L09"]["quote"])
        counted = {node["id"] for node in plate["nodes"]
                   if node["id"].startswith("l-jm-pool-count-")}
        self.assertEqual(counted, {f"l-jm-pool-count-{number}" for number in (1, 2, 3)})
        for edge in plate["segments"]:
            endpoints = {edge["from"], edge["to"]}
            self.assertTrue(endpoints.isdisjoint(counted),
                            "A count symbol became a located pool with a known inlet")
            self.assertNotEqual(endpoints, {"l-gu-reference", "l-fishpond"})
            self.assertNotEqual(endpoints, {"l-jm-three", "l-jm-waterpower"})

    def test_reported_values_do_not_merge_windows_or_turn_structural_height_into_water_depth(self):
        rows = {row["id"]: row for row in self.data["reported_measurements"]}
        self.assertTrue({"MW", "ME", "POOL", "D12", "D3", "D4", "TRENCH", "EARLY", "FANGHU"}
                        <= rows.keys())
        for row in rows.values():
            self.assertFalse(row["new_measurement_by_project"])
        for rid in ("MW", "ME"):
            self.assertIsNone(rows[rid]["original_channel_depth_m"])
            self.assertIsNone(rows[rid]["water_depth_m"])
        self.assertIn("城壕概述", rows["ME"]["label"])
        self.assertIn("不相加", rows["ME"]["limit"])
        self.assertRegex(rows["D4"]["value_text"], r"外宽\s*3\.8")
        self.assertRegex(rows["TRENCH"]["value_text"], r"基槽上口\s*3\.8")
        self.assertRegex(rows["D3"]["value_text"], r"残高\s*1\.9")
        self.assertIn("水深", rows["D3"]["limit"])
        self.assertIn("水深", rows["D4"]["limit"])
        self.assertIn("多期", rows["EARLY"]["value_text"])
        self.assertIn("不是当时水深", rows["EARLY"]["limit"])
        self.assertEqual(rows["FANGHU"]["unit"], "步")
        self.assertIsNone(rows["FANGHU"]["metres"])

    def test_all_twelve_remaining_objects_have_a_review_without_new_bank_geometry(self):
        expected = {f"W{number:02}" for number in (10, 11, 12, 13, 14, 22, 23, 24, 25, 26, 27, 29)}
        coverage = self.data["legacy_water_coverage"]
        self.assertEqual(len(coverage), len(expected))
        self.assertEqual({item["旧编号"] for item in coverage}, expected)
        for item in coverage:
            self.assertIn(item["本册图"], self.plates)
            self.assertTrue(item["状态"].strip())
        self.assertEqual(self.data["new_geographic_coordinates"], 0)
        self.assertIsNone(self.data["new_516_528_bank_geometry"])
        questions = {question["id"]: question for question in self.data["open_questions"]}
        self.assertTrue({"water02", "water01", "moat-logs", "palace-joins", "pond-mouths"}
                        <= questions.keys())


class Water468Publication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read(SOURCE / "readings.json")
        cls.info = read(SITE / "build-info.json")
        cls.meta = cls.info["prosperity_water_p468"]

    def test_rendered_arrows_distinguish_water_from_containment_and_strata(self):
        nonflow_seen = set()
        for plate in self.data["plates"]:
            svg = ET.parse(SITE / f"water-468/{plate['id']}.svg").getroot()
            self.assertEqual(svg.get("data-water-map"), plate["id"])
            groups = {group.get("data-segment-id"): group for group in svg.iter(NS + "g")
                      if group.get("class") == "water-segment"}
            self.assertEqual(set(groups), {edge["id"] for edge in plate["segments"]})
            for edge in plate["segments"]:
                with self.subTest(segment=edge["id"]):
                    group = groups[edge["id"]]
                    self.assertEqual((group.get("data-from"), group.get("data-to")),
                                     (edge["from"], edge["to"]))
                    self.assertEqual(group.get("data-relationship"), edge["relationship_type"])
                    self.assertEqual(group.get("data-period-class"), edge["period_class"])
                    routes = [path for path in group.findall(NS + "path")
                              if path.get("class") == "segment-route"]
                    self.assertEqual(len(routes), 1)
                    route = routes[0]
                    self.assertEqual(bool(route.get("marker-end")),
                                     edge["relationship_type"] == "flow")
                    if edge["relationship_type"] != "flow":
                        nonflow_seen.add(edge["relationship_type"])
                    if edge["period_class"] != "text_context":
                        self.assertTrue(route.get("stroke-dasharray"))
        self.assertTrue({"containment", "stratigraphy", "adjacency", "hypothesis", "connection"}
                        <= nonflow_seen)

    def test_all_four_maps_and_source_downloads_match_the_page_and_pdf(self):
        plates = self.data["plates"]
        edges = [edge for plate in plates for edge in plate["segments"]]
        plate_ids = {plate["id"] for plate in plates}
        self.assertEqual(plate_ids, PLATES)
        self.assertEqual(set(self.meta["plates"]), {f"{pid}.svg" for pid in plate_ids})
        self.assertEqual(self.meta["atlas_pages"], len(plates))
        self.assertEqual(len(PdfReader(SITE / self.meta["atlas"]).pages), len(plates))
        self.assertEqual(self.meta["segments"], len(edges))
        self.assertEqual(self.meta["relation_counts"],
                         dict(Counter(edge["relationship_type"] for edge in edges)))
        self.assertEqual(self.meta["period_counts"],
                         dict(Counter(edge["period_class"] for edge in edges)))
        self.assertTrue(self.meta["layout_coordinates_only"])
        self.assertEqual(self.meta["geographic_coordinates_added"], 0)
        self.assertEqual(self.meta["new_metric_measurements"], 0)
        self.assertEqual(read(SITE / self.meta["readings"]), self.data)

        page = (SITE / self.meta["page"]).read_text(encoding="utf-8")
        self.assertEqual(set(re.findall(r'data-water-map="([^"]+)"', page)), plate_ids)
        links = Links()
        links.feed(page)
        expected_sources = {f"water-468/{path.name}" for path in SOURCE.glob("*.json")}
        self.assertEqual(set(self.meta["data_files"]), expected_sources)
        self.assertTrue({f"water-468/{name}.json" for name in
                         ("readings", "moats-zhangfang-source-audit", "west-palace-source-audit",
                          "pools-source-audit")} <= expected_sources)
        for name in expected_sources:
            self.assertIn(name, links.hrefs)
            self.assertEqual((SITE / name).read_bytes(), (SOURCE / Path(name).name).read_bytes())
        downloads = expected_sources | {f"water-468/{pid}.svg" for pid in plate_ids}
        downloads.add(self.meta["atlas"])
        self.assertTrue(downloads <= links.hrefs)
        publications = downloads | {self.meta["page"], "water-468/study.css", "water-468/water-ui.js"}
        for name in publications:
            self.assertEqual(digest(SITE / name), self.info["files_sha256"][name], name)
        measurements = self.data["reported_measurements"]
        self.assertEqual(self.meta["reported_value_rows"], len(measurements))
        for row in measurements:
            self.assertIn(f'id="measure-{row["id"]}"', page)

    def test_p467_fifty_three_relations_and_original_pdf_remain_frozen(self):
        old_source = ROOT / "research/prosperity-v4/water-467/readings.json"
        self.assertEqual(digest(old_source), P467_DATA_SHA)
        self.assertEqual(digest(SITE / "water-467/readings.json"), P467_DATA_SHA)
        old = read(old_source)
        self.assertEqual(sum(len(plate["segments"]) for plate in old["plates"]), 53)
        self.assertEqual(digest(ROOT / "research/prosperity-v4/archive/water-467.pdf"),
                         P467_ATLAS_SHA)
        self.assertEqual(digest(SITE / "downloads/water-467.pdf"), P467_ATLAS_SHA)
        self.assertEqual(len(PdfReader(SITE / "downloads/water-467.pdf").pages), 5)


if __name__ == "__main__":
    unittest.main()
