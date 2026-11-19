"""Protect the source frames and corrected water evidence in the city backbone.

These checks compare the public product with the archived evidence, not with
the generator's own geometry or formatting helpers.  In particular, a valid
source link must never manufacture an ancient river coordinate.
"""
import hashlib
import json
import re
import unittest
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/prosperity-v4/backbone-469"
SITE = ROOT / "_site"
NS = "{http://www.w3.org/2000/svg}"
I09 = "P467/inner/I09"
URBAN_SOURCE = "research/prosperity-v4/street-clusters-p453.json"
BASELINE_SHA = {
    URBAN_SOURCE:
        "9b69da412a86d5e21e82b2cfdcac747b667ecad053de868618fd7474e4bcd116",
    "research/prosperity-v1/geographic-evidence.json":
        "80a2e5457789d0056bafe5cb5eb5df73bea23fb2e9d733a784ed0068562ead79",
    "research/prosperity-v4/network-462/outer.json":
        "761da9e0abace43fc14e04dd330becc3c288df0a8a239a5d55417632bc5d1e5a",
    "research/prosperity-v4/gates-465/readings.json":
        "8db5f40297be313abe55f0c49ac32f706d1ce82da91adac7e74f8a743e2292e1",
    "research/prosperity-v4/south-466/readings.json":
        "545c09e3a0fc6f91f686e02ff34784455868faf434cc299945e8a49cd9bd0106",
    "research/prosperity-v4/water-467/readings.json":
        "bf51dad84680792dafbaacb14bea0a0715fa31a5cf13842fd0096f762132a789",
    "research/prosperity-v4/water-468/readings.json":
        "6703af3308fff4e266c3e50c6fcd2d8f8e357c08ceb678f0e327d37dbd18467d",
}
# First P469 main-build browser downloads, independently matched to public assets.
# Adding page-only context links must not redraw the published source maps or PDF.
FROZEN_BACKBONE_DOWNLOAD_SHA = {
    "backbone-469/frame-06a.svg":
        "b3d53efd6c45fcb92f28c10c298f114af723c69598597567dbc853c4368afa04",
    "backbone-469/frame-qian2018.svg":
        "8513c668f3efd855c33b25d160cbc5d8f78cf7a44f6af5fdc35b349ad29aa0ba",
    "downloads/backbone-469.pdf":
        "f4e8e7f9a0642224c49d5b6b00d24d19afcb425fc8b2692a7a0a9e0932119ab6",
}
RENDERED_06A = {
    "geo-inner-wall-aboveground", "geo-inner-wall-underground", "geo-palace-walls",
    "geo-road-east-west-south", "geo-tongtuo-cross-street",
    "geo-road-east-west-middle", "geo-road-east-west-north",
    "geo-road-north-south-east", "geo-road-north-south-mid-east",
    "geo-tongtuo-avenue", "geo-road-north-south-west",
    "geo-changhe-palace-gate", "geo-qianqiu-gate", "geo-yunlong-gate",
    "geo-jianchun-gate", "geo-daxia-gate", "geo-guangmo-gate",
    "geo-xiyang-gate", "geo-dongyang-gate", "geo-qingyang-gate", "geo-ximing-gate",
    "geo-modern-luo-river",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archived_relations():
    result = {}
    for version in (467, 468):
        data = read(ROOT / f"research/prosperity-v4/water-{version}/readings.json")
        for plate in data["plates"]:
            for edge in plate["segments"]:
                result[f"P{version}/{plate['id']}/{edge['id']}"] = edge
    return result


def objects(value, trail="root"):
    """Walk nested records without treating layout points as geographic data."""
    if isinstance(value, dict):
        yield trail, value
        for key, child in value.items():
            yield from objects(child, f"{trail}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from objects(child, f"{trail}[{index}]")


def linear_subpaths(path_data):
    """Read native SVG polyline coordinates, rejecting invented curve/closure commands."""
    number = r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?"
    tokens = re.findall(rf"[A-Za-z]|{number}", path_data)
    paths, active, command, index = [], None, None, 0
    while index < len(tokens):
        token = tokens[index]
        if re.fullmatch(r"[A-Za-z]", token):
            if token not in {"M", "L"}:
                raise AssertionError(f"Expected source polylines, found SVG command {token}")
            command = token
            index += 1
        if command not in {"M", "L"} or index + 1 >= len(tokens):
            raise AssertionError("Malformed source polyline")
        point = [float(tokens[index]), float(tokens[index + 1])]
        if command == "M":
            active = []
            paths.append(active)
            command = "L"
        active.append(point)
        index += 2
    return paths


class Markup(HTMLParser):
    """Small DOM reader for accessible evidence text and local download links."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
            "meta", "param", "source", "track", "wbr"}

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.stack = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "text": "", "children": []}
        self.nodes.append(node)
        if self.stack:
            self.stack[-1]["children"].append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "text": "", "children": []}
        self.nodes.append(node)
        if self.stack:
            self.stack[-1]["children"].append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        for node in self.stack:
            node["text"] += data

    def by_id(self, identifier):
        matches = [node for node in self.nodes if node["attrs"].get("id") == identifier]
        if len(matches) != 1:
            raise AssertionError(f"Expected one #{identifier}, found {len(matches)}")
        return matches[0]

    @staticmethod
    def descendants(node):
        for child in node["children"]:
            yield child
            yield from Markup.descendants(child)

    @property
    def hrefs(self):
        return {node["attrs"]["href"] for node in self.nodes
                if node["tag"] == "a" and "href" in node["attrs"]}


class Backbone469Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read(SOURCE / "readings.json")
        cls.frames = {frame["id"]: frame for frame in cls.data["frames"]}
        cls.relations = {edge["ref"]: edge for edge in cls.data["current_relations"]}
        cls.ledger = {item["id"]: item for item in cls.data["current_water_ledger"]}
        cls.archived = archived_relations()

    def test_archival_geometry_and_prior_water_data_are_not_rewritten(self):
        for name, expected in BASELINE_SHA.items():
            with self.subTest(source=name):
                self.assertEqual(digest(ROOT / name), expected,
                                 "A current synthesis must not rewrite archived evidence")

    def test_coordinate_frames_do_not_acquire_a_shared_registration(self):
        self.assertEqual(set(self.frames),
                         {"frame-06a", "frame-qian2018-zhu2024", "frame-relations"})
        source = self.frames["frame-06a"]
        self.assertEqual(source["crs"], "EPSG:4610")
        self.assertIn("4326", source["geographic_warning"])
        reconstruction = self.frames["frame-qian2018-zhu2024"]
        self.assertIsNone(reconstruction["crs"])
        self.assertEqual(reconstruction["image_size_px"], [1145, 951])
        self.assertEqual(reconstruction["scale_endpoints_px"],
                         [[980.5, 933], [1072.5, 933]])
        self.assertEqual(reconstruction["scale_represents_m"], 1000)
        self.assertIsNone(reconstruction["geographic_transform"])
        self.assertIsNone(self.frames["frame-relations"]["crs"])
        self.assertIsNone(self.frames["frame-relations"]["geographic_coordinates"])
        self.assertIsNone(self.frames["frame-relations"]["geographic_transform"])

    def test_original_geometry_and_qian_pixel_readings_are_preserved_deeply(self):
        original = read(ROOT / "research/prosperity-v1/geographic-evidence.json")
        frame = self.frames["frame-06a"]
        self.assertEqual(frame["source_crs"], original["crs"])
        self.assertEqual(len(frame["features"]), 30)
        self.assertEqual(frame["features"], original["features"],
                         "06a native and geographic geometry, periods and limits must survive intact")
        self.assertFalse(frame["modern_river_default_visible"])
        self.assertFalse(frame["provisional_envelope_default_visible"])
        qian = self.frames["frame-qian2018-zhu2024"]
        north = read(ROOT / "research/prosperity-v4/gates-465/readings.json")["later_plan"]
        south = read(ROOT / "research/prosperity-v4/south-466/readings.json")["plan"]
        corridors = read(ROOT / "research/prosperity-v4/network-462/outer.json")["corridors"]
        self.assertEqual(qian["north_reading"], north)
        self.assertEqual(qian["south_reading"], south)
        self.assertEqual(qian["outer_corridors"], corridors)
        self.assertFalse(north["source_map_merge_visible"])
        self.assertIsNone(north["northern_outer_gate_archaeological_structures"])

    def test_relation_export_is_complete_without_layout_or_geographic_coordinates(self):
        self.assertEqual(len(self.data["current_relations"]), 100)
        self.assertEqual(len(self.relations), 100, "Full reference IDs must be unique")
        self.assertEqual(set(self.relations), set(self.archived))
        for ref, edge in self.relations.items():
            with self.subTest(relation=ref):
                original = self.archived[ref]
                for key in ("id", "from", "to", "relationship_type", "period_class",
                            "source_ids", "locator"):
                    self.assertEqual(edge[key], original[key], f"{ref}.{key}")
                if ref != I09:
                    self.assertEqual(edge["quote"], original["quote"], ref)
                for trail, record in objects(edge, ref):
                    self.assertTrue({"points", "x", "y", "label_position"}.isdisjoint(record),
                                    f"Page-layout coordinates leaked into {trail}")
                    for key in ("geometry", "geographic_coordinates", "latitude", "longitude",
                                "lat", "lon", "lng", "local_gis_transform"):
                        if key in record:
                            self.assertIsNone(record[key], f"{trail}.{key}")

    def test_current_pool_correction_is_effective_in_both_directions(self):
        self.assertEqual(set(self.relations[I09]["legacy_water_ids"]),
                         {"W17", "W18", "W19", "W34"})
        self.assertEqual(set(self.data["corrected_current_I09"]["legacy_water_ids"]),
                         {"W17", "W18", "W19", "W34"})
        self.assertEqual(set(self.data["correction"]["withdrawn_legacy_ids"]), {"W20", "W21"})
        for water_id in ("W20", "W21"):
            self.assertNotIn(I09, self.ledger[water_id]["current_refs"], water_id)
        self.assertIn("P468/palace-pools-audit/H01", self.ledger["W20"]["current_refs"])
        self.assertIn("P468/palace-pools-audit/H04", self.ledger["W21"]["current_refs"])
        for ref in self.ledger["W20"]["current_refs"] + self.ledger["W21"]["current_refs"]:
            self.assertIn(self.relations[ref]["relationship_type"], {"adjacency", "containment"},
                          "Withdrawing I09 must not be undone by another invented inlet")
        self.assertTrue({"W20", "W21"} <= set(self.archived[I09]["legacy_water_ids"]),
                        "Historical indices must remain available as historical records")

    def test_drought_rain_and_seasonality_are_not_flattened_to_perennial_water(self):
        for record in (self.relations[I09], self.data["corrected_current_I09"]):
            quote = record["quote"]
            for phrase in ("若旱魃為害", "穀水注之不竭", "離畢滂潤", "陽穀泄之不盈"):
                self.assertIn(phrase, quote)
            self.assertLess(quote.index("若旱魃為害"), quote.index("穀水注之不竭"))
            self.assertLess(quote.index("離畢滂潤"), quote.index("陽穀泄之不盈"))
            self.assertFalse(record.get("annual_flow_516_528_confirmed", False))
        seasonal = self.relations["P468/palace-pools-audit/H01"]["seasonality"]
        self.assertEqual((seasonal["summer"], seasonal["winter"]), ("has_water", "dry"))
        self.assertFalse(seasonal["perennial_water_confirmed"])

    def test_all_water_ids_resolve_without_turning_the_modern_river_into_ancient_water(self):
        self.assertEqual(len(self.data["current_water_ledger"]), 34)
        self.assertEqual(set(self.ledger), {f"W{number:02}" for number in range(1, 35)})
        self.assertTrue(self.ledger["W02"]["modern_only"])
        self.assertEqual(self.ledger["W02"]["current_refs"], [])
        for item in self.ledger.values():
            refs = item["current_refs"]
            self.assertEqual(len(refs), len(set(refs)), item["id"])
            self.assertTrue(set(refs) <= self.relations.keys(), item["id"])
            if item["id"] not in {"W02", "W14"}:
                self.assertTrue(refs, f"{item['id']} has no current evidence to consult")
            for key in ("geometry", "geographic_frame", "target_bank_geometry"):
                self.assertIsNone(item[key], f"{item['id']}.{key}")
        self.assertEqual(self.ledger["W14"]["current_refs"], [])
        self.assertEqual(self.ledger["W14"]["context_plate_refs"], ["P468/palace-water"])
        self.assertIn("不能", self.ledger["W14"]["current_record"]["状态"])
        for edge in self.relations.values():
            self.assertNotIn("W02", edge.get("legacy_water_ids", []))

    def test_mapped_evidence_navigation_does_not_place_water_at_gate_symbols(self):
        features = {item["id"] for item in
                    read(ROOT / "research/prosperity-v1/geographic-evidence.json")["features"]}
        navigation = self.data["water_evidence_navigation"]
        self.assertEqual(len(navigation), 9)
        self.assertEqual(len({item["mapped_feature_id"] for item in navigation}), 9)
        for item in navigation:
            self.assertIn(item["mapped_feature_id"], features)
            self.assertEqual(item["semantics"], "context_link_only")
            self.assertTrue(item["limit"].strip())
            self.assertTrue(item["evidence_refs"])
            self.assertTrue(set(item["evidence_refs"]) <= self.relations.keys())
            for _, record in objects(item):
                self.assertTrue({"geometry", "coordinates", "points", "x", "y",
                                 "offset_m"}.isdisjoint(record),
                                "A documentary context link acquired a located channel")

    def test_synthesis_does_not_claim_new_ancient_banks_or_measurements(self):
        self.assertEqual(self.data["new_geographic_coordinates"], 0)
        self.assertEqual(self.data["new_metric_measurements"], 0)
        self.assertIsNone(self.data["new_516_528_bank_geometry"])
        expected_nulls = {
            "inner_south_wall_geometry", "xuanyang_gate_geographic_coordinates",
            "north_road_confluence_coordinates", "chengming_westernmost_survey_station",
            "daxia_last_field_station", "guangmo_last_field_station",
            "yinluo_section_width_m", "yinluo_section_depth_m", "biyong_flow_516_528",
            "ward_gate_to_central_cross_m",
        }
        unknowns = self.data["unknowns"]
        self.assertTrue(expected_nulls <= unknowns.keys())
        for key in expected_nulls:
            self.assertIsNone(unknowns[key], key)
        self.assertEqual(unknowns["yongqiao_bank_landings"], [None, None])


class Backbone469Publication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read(SOURCE / "readings.json")
        cls.svg06a = ET.parse(SITE / "backbone-469/frame-06a.svg").getroot()
        cls.svgqian = ET.parse(SITE / "backbone-469/frame-qian2018.svg").getroot()
        cls.page = Markup((SITE / "prosperity-backbone-p469.html").read_text(encoding="utf-8"))
        cls.urban = read(SITE / "backbone-469/urban-contexts.json")
        cls.urban_source = read(ROOT / URBAN_SOURCE)
        cls.urban_clusters = {cluster["id"]: cluster for cluster in cls.urban["clusters"]}

    def assertPointsEqual(self, actual, expected, label):
        self.assertEqual(len(actual), len(expected), label)
        for index, (observed, original) in enumerate(zip(actual, expected)):
            self.assertEqual(len(observed), 2, f"{label}[{index}]")
            for axis in (0, 1):
                self.assertAlmostEqual(observed[axis], original[axis], places=6,
                                       msg=f"{label}[{index}][{axis}]")

    def test_page_context_extension_keeps_published_map_and_pdf_bytes(self):
        for name, expected in FROZEN_BACKBONE_DOWNLOAD_SHA.items():
            with self.subTest(download=name):
                self.assertEqual(digest(SITE / name), expected,
                                 "A page-only evidence link changed a frozen map or PDF")
        archive = ROOT / "research/prosperity-v4/archive/backbone-469.pdf"
        self.assertEqual(archive.read_bytes(), (SITE / "downloads/backbone-469.pdf").read_bytes(),
                         "The published atlas must be the reviewed archive, not a font-dependent rerender")

    def test_urban_export_reuses_the_reviewed_clusters_and_sources(self):
        self.assertEqual(self.urban["source_path"], URBAN_SOURCE)
        self.assertEqual(self.urban["source_sha256"], BASELINE_SHA[URBAN_SOURCE])
        self.assertEqual(self.urban["source_version"], self.urban_source["version"])
        self.assertEqual(self.urban["evidence_grades"], self.urban_source["evidence_grades"])
        expected_clusters = [cluster for cluster in self.urban_source["clusters"]
                             if cluster["id"] in {"K01", "K02"}]
        self.assertEqual(self.urban["clusters"], expected_clusters,
                         "A context link must not paraphrase or recategorize the reviewed evidence")
        self.assertEqual(self.urban["new_historical_coordinates"], 0)
        self.assertTrue({URBAN_SOURCE, "research/prosperity-v1/text-review.json",
                         "research/dual-b1/decisions.json"}
                        <= self.urban["source_inputs_sha256"].keys())
        for path, expected in self.urban["source_inputs_sha256"].items():
            self.assertEqual(digest(ROOT / path), expected, path)
        used_records = {record["source_record"]
                        for cluster in expected_clusters
                        for record in [*cluster["edges"], *cluster.get("temporal_events", [])]}
        self.assertTrue(used_records <= self.urban["source_records"].keys())
        p1_records = {record["legacy_title"]: record for record in
                      read(ROOT / "research/prosperity-v1/text-review.json")["records"]}
        b1_records = {"B1:" + record["id"]: record for record in
                      read(ROOT / "research/dual-b1/decisions.json")["decisions"]}
        original_records = {**p1_records, **b1_records}
        for record_id in used_records:
            source = self.urban["source_records"][record_id]
            self.assertIn(source["source_path"], self.urban["source_inputs_sha256"])
            self.assertEqual(source["record"], original_records[record_id], record_id)
            self.assertEqual(source["locator"], original_records[record_id].get("legacy_locator", ""),
                             "Missing original locators must not be invented for the new view")
            self.assertTrue(source["links"], record_id)
            for link in source["links"]:
                self.assertTrue(link["title"].strip(), record_id)
                self.assertTrue(link["url"].startswith("https://"), record_id)

    def test_urban_navigation_uses_the_two_explicit_gate_bindings(self):
        expected = {"geo-changhe-palace-gate": ("ic_changhe_palace", "K01"),
                    "geo-jianchun-gate": ("gate_jianchun", "K02")}
        navigation = self.urban["navigation"]
        self.assertEqual(len(navigation), 2)
        self.assertEqual({row["mapped_feature_id"] for row in navigation}, set(expected))
        bindings = {(row["feature_id"], row["entity_id"], row["cluster_id"])
                    for row in self.urban_source["spatial_index_references"]}
        for row in navigation:
            feature_id = row["mapped_feature_id"]
            entity_id, cluster_id = expected[feature_id]
            self.assertEqual((row["entity_id"], row["cluster_id"]), (entity_id, cluster_id))
            self.assertIn((feature_id, entity_id, cluster_id), bindings)
            self.assertEqual(row["semantics"], "context_link_only")
            self.assertEqual(row["page"],
                             f"prosperity-street-clusters.html?cluster={cluster_id}&grade=all")
            self.assertTrue(row["limit"].strip())
            for _, record in objects(row):
                self.assertTrue({"geometry", "coordinates", "points", "x", "y",
                                 "offset_m", "local_gis_transform"}.isdisjoint(record))
        palace_road = next(node for node in self.urban_clusters["K01"]["nodes"]
                          if node["id"] == "ic_palace_avenue")
        self.assertIsNone(palace_road["feature_id"],
                          "The palace avenue must not silently become the whole Tongtuo geometry")

    def test_urban_bridge_events_and_interpretive_grade_keep_their_scope(self):
        palace, bridges = self.urban_clusters["K01"], self.urban_clusters["K02"]
        self.assertEqual((len(palace["edges"]), len(bridges["edges"])), (8, 5))
        conditional = [edge for edge in palace["edges"] if edge["grade"] == "C"]
        self.assertEqual([edge["id"] for edge in conditional], ["K01E08"])
        events = {event["id"]: event for event in bridges["temporal_events"]}
        self.assertEqual(set(events), {"K02T01", "K02T02"})
        collapse, construction = events["K02T01"], events["K02T02"]
        self.assertEqual((collapse["subject"], collapse["year"]), ("bridge_jianchun", 527))
        self.assertEqual(set(collapse["does_not_transfer_to"]), {"bridge_eaststone", "bridge_yong"})
        self.assertEqual((construction["subject"], construction["year"]), ("bridge_eaststone", 280))
        for cluster in (palace, bridges):
            self.assertTrue(cluster["non_geographic"])
            self.assertTrue(all(edge["geographic_line_allowed"] is False for edge in cluster["edges"]))

    def test_urban_records_are_visible_and_source_linked_without_javascript(self):
        for navigation in self.urban["navigation"]:
            cluster = self.urban_clusters[navigation["cluster_id"]]
            article = self.page.by_id("context-" + navigation["mapped_feature_id"])
            self.assertNotIn("hidden", article["attrs"])
            self.assertIn(navigation["limit"], article["text"])
            sections = [node for node in Markup.descendants(article)
                        if node["attrs"].get("data-urban-cluster") == cluster["id"]]
            self.assertEqual(len(sections), 1)
            section = sections[0]
            self.assertNotIn("hidden", section["attrs"])
            descendants = list(Markup.descendants(section))
            edges = {node["attrs"]["data-urban-edge-id"]: node
                     for node in descendants if "data-urban-edge-id" in node["attrs"]}
            self.assertEqual(set(edges), {edge["id"] for edge in cluster["edges"]})
            for edge in cluster["edges"]:
                rendered = edges[edge["id"]]
                self.assertEqual(rendered["attrs"]["data-evidence-grade"], edge["grade"])
                for field in ("quote", "scope", "source_record"):
                    self.assertIn(edge[field], rendered["text"], (edge["id"], field))
                hrefs = {node["attrs"].get("href") for node in Markup.descendants(rendered)}
                for link in self.urban["source_records"][edge["source_record"]]["links"]:
                    self.assertIn(link["url"], hrefs, edge["id"])
            events = {node["attrs"]["data-urban-event-id"]: node
                      for node in descendants if "data-urban-event-id" in node["attrs"]}
            self.assertEqual(set(events), {event["id"] for event in cluster.get("temporal_events", [])})
            names = {node["id"]: node["name"] for node in cluster["nodes"]}
            for event in cluster.get("temporal_events", []):
                rendered = events[event["id"]]
                for field in ("event", "scope", "source_record"):
                    self.assertIn(event[field], rendered["text"], (event["id"], field))
                self.assertIn(str(event["year"]), rendered["text"])
                self.assertIn(names[event["subject"]], rendered["text"])
                if event["id"] == "K02T01":
                    self.assertIn("东石桥", rendered["text"])
                    self.assertIn("永桥", rendered["text"])
            original_links = [node for node in descendants
                              if node["attrs"].get("data-urban-source-link") == cluster["id"]]
            self.assertEqual(len(original_links), 1)
            self.assertEqual(original_links[0]["attrs"]["href"], "./" + navigation["page"])
            self.assertNotIn("target", original_links[0]["attrs"], "The original-topic return check needs same-tab navigation")

    def test_inline_gate_links_do_not_modify_the_map_drawing(self):
        inline = self.page.by_id("frame-06a")
        inline_nodes = list(Markup.descendants(inline))
        navigation_ids = {row["mapped_feature_id"] for row in self.data["water_evidence_navigation"]}
        navigation_ids.update(row["mapped_feature_id"] for row in self.urban["navigation"])
        inline_links = [node for node in inline_nodes if "data-context-id" in node["attrs"]]
        self.assertEqual(len(inline_links), 10)
        self.assertEqual({node["attrs"]["data-context-id"] for node in inline_links}, navigation_ids)
        for node in inline_links:
            self.assertEqual(node["tag"], "a")
            self.assertEqual(node["attrs"]["href"], "#context-" + node["attrs"]["data-context-id"])
        # Anchor wrappers may differ, but every drawing element stays the same.
        visual_tags = {"circle", "ellipse", "line", "path", "polygon", "polyline", "rect", "text"}
        original_drawings = [(element.tag.removeprefix(NS), dict(element.attrib), "".join(element.itertext()))
                             for element in self.svg06a.iter()
                             if element.tag.removeprefix(NS) in visual_tags]
        inline_drawings = [(node["tag"], node["attrs"], node["text"])
                           for node in inline_nodes if node["tag"] in visual_tags]
        self.assertEqual(inline_drawings, original_drawings,
                         "A context link moved, resized, or redrew a source feature")

    def test_06a_rendering_keeps_original_vertices_and_does_not_complete_missing_walls(self):
        source = read(ROOT / "research/prosperity-v1/geographic-evidence.json")
        originals = {feature["id"]: feature for feature in source["features"]}
        drawn = defaultdict(list)
        for element in self.svg06a.iter():
            fid = element.get("data-source-feature-id")
            if fid and element.tag in {NS + "path", NS + "rect", NS + "circle"}:
                drawn[fid].append(element)
        self.assertEqual(set(drawn), RENDERED_06A,
                         "The focused skeleton must not add a south wall or a provisional envelope")
        parents = {child: parent for parent in self.svg06a.iter() for child in parent}
        transform_chains = set()
        for fid, elements in drawn.items():
            with self.subTest(feature=fid):
                geometry = originals[fid]["source_pdf_geometry"]
                for element in elements:
                    chain, ancestor = [], element
                    while ancestor is not None:
                        if ancestor.get("transform"):
                            chain.append(ancestor.get("transform"))
                        ancestor = parents.get(ancestor)
                    transform_chains.add(tuple(chain))
                if geometry["type"] == "Point":
                    self.assertEqual(len(elements), 1, fid)
                    marker = elements[0]
                    if marker.tag == NS + "rect":
                        point = [float(marker.get("x")) + float(marker.get("width")) / 2,
                                 float(marker.get("y")) + float(marker.get("height")) / 2]
                    else:
                        self.assertEqual(marker.tag, NS + "circle", fid)
                        point = [float(marker.get("cx")), float(marker.get("cy"))]
                    self.assertPointsEqual([point], [geometry["coordinates"]], fid)
                else:
                    observed = []
                    for element in elements:
                        self.assertEqual(element.tag, NS + "path", fid)
                        observed.extend(linear_subpaths(element.get("d", "")))
                    expected = geometry["coordinates"]
                    if geometry["type"] == "LineString":
                        expected = [expected]
                    self.assertEqual(len(observed), len(expected), fid)
                    for index, (actual, original) in enumerate(zip(observed, expected)):
                        self.assertPointsEqual(actual, original, f"{fid}/{index}")
        self.assertEqual(len(transform_chains), 1,
                         "A feature moved independently of its native source-map frame")

    def test_modern_luo_is_a_separate_dated_reference_layer(self):
        modern = [element for element in self.svg06a.iter()
                  if element.get("id") == "modern-river-469"]
        self.assertEqual(len(modern), 1)
        modern = modern[0]
        self.assertEqual(modern.get("data-period"), "1997/1999")
        self.assertEqual(modern.get("data-not-ancient-river"), "true")
        reference_paths = [element for element in self.svg06a.iter()
                           if element.get("data-source-feature-id") == "geo-modern-luo-river"]
        self.assertTrue(reference_paths)
        descendants = set(modern.iter())
        self.assertTrue(all(element in descendants for element in reference_paths))
        self.assertEqual({element.get("data-source-feature-id") for element in descendants
                          if element.get("data-source-feature-id")}, {"geo-modern-luo-river"})
        self.assertNotIn("checked", self.page.by_id("modern-river-toggle")["attrs"],
                         "The visible initial state contradicts the source-frame visibility policy")

    def test_frames_remain_separate_and_documentary_water_is_not_drawn_as_geography(self):
        for svg, frame_id in ((self.svg06a, "frame-06a"),
                              (self.svgqian, "frame-qian2018")):
            self.assertEqual(svg.get("id"), frame_id)
            self.assertEqual(svg.get("data-source-frame"), frame_id)
            for element in svg.iter():
                self.assertIsNone(element.get("data-segment-id"),
                                  "A P467/P468 layout segment became geographic map geometry")
        self.assertFalse(any(element.get("data-source-feature-id") for element in self.svgqian.iter()),
                         "06a features have been transferred to the unregistered reconstruction frame")

    def test_qian_lines_and_symbols_preserve_the_same_raster_without_joining_endpoints(self):
        north = read(ROOT / "research/prosperity-v4/gates-465/readings.json")["later_plan"]
        south = read(ROOT / "research/prosperity-v4/south-466/readings.json")["plan"]
        corridors = read(ROOT / "research/prosperity-v4/network-462/outer.json")["corridors"]
        expected_lines = {
            "gates-465:later_plan.inner_wall_px": north["inner_wall_px"],
            "gates-465:later_plan.outer_wall_px": north["outer_wall_px"],
            "gates-465:later_plan.west.trace_px": north["west"]["trace_px"],
        }
        expected_points = {}
        for route in north["north"]:
            prefix = f"gates-465:later_plan.north.{route['id']}."
            for key in ("to_wall_px", "beyond_wall_to_frame_px"):
                expected_lines[prefix + key] = route[key]
            expected_points[prefix + "to_wall_px[0]"] = route["to_wall_px"][0]
        for name, points in south["road_samples_px"].items():
            expected_lines[f"south-466:plan.road_samples_px.{name}"] = points
        for name in ("north_bank_sample_px", "south_bank_sample_px", "bridge_symbol_ends_px",
                     "scale_endpoints_px"):
            expected_lines[f"south-466:plan.{name}"] = south[name]
        for name, point in south["places_px"].items():
            expected_points[f"south-466:plan.places_px.{name}"] = point
        endpoint_paths = set()
        for corridor in corridors:
            for key in ("inner_station_px", "outer_station_px"):
                source_path = f"network-462:outer.corridors.{corridor['id']}.{key}"
                expected_points[source_path] = corridor[key]
                endpoint_paths.add(source_path)
        native = next(element for element in self.svgqian.iter()
                      if element.get("id") == "native-qian-geometry")
        lines = [element for element in native.iter(NS + "path")]
        points = [element for element in native.iter(NS + "circle")]
        self.assertEqual(len(lines), len(expected_lines))
        self.assertEqual(len(points), len(expected_points))
        self.assertEqual({element.get("data-source-path") for element in lines}, set(expected_lines))
        self.assertEqual({element.get("data-source-path") for element in points}, set(expected_points))
        for element in lines + points:
            source_path = element.get("data-source-path")
            with self.subTest(source_path=source_path):
                self.assertEqual(element.get("data-source-frame"), "frame-qian2018")
                self.assertIsNone(element.get("transform"), "A source object moved within its frame")
                if element.tag == NS + "path":
                    subpaths = linear_subpaths(element.get("d", ""))
                    self.assertEqual(len(subpaths), 1)
                    self.assertPointsEqual(subpaths[0], expected_lines[source_path], source_path)
                else:
                    actual = [float(element.get("cx")), float(element.get("cy"))]
                    self.assertPointsEqual([actual], [expected_points[source_path]], source_path)
                if source_path in endpoint_paths:
                    self.assertEqual(element.get("data-source-kind"), "endpoint-only")
                    self.assertEqual(element.tag, NS + "circle")
                if source_path.endswith("bridge_symbol_ends_px"):
                    self.assertEqual(element.get("data-source-kind"), "source-symbol")
                    self.assertEqual(element.get("data-not-excavated-landing"), "true")
                if source_path.endswith(("north_bank_sample_px", "south_bank_sample_px")):
                    self.assertEqual(element.get("data-source-kind"), "later-reconstruction")
                    self.assertTrue(element.get("stroke-dasharray"))
        self.assertEqual(len(endpoint_paths), 12)
        self.assertFalse(list(native.iter(NS + "polygon")))
        # The only anonymous straight lines in the native frame are two scale ticks.
        anonymous = list(native.iter(NS + "line"))
        self.assertEqual(len(anonymous), 2, "An unlabelled line joined separate road endpoints")
        for element, endpoint in zip(anonymous, south["scale_endpoints_px"]):
            self.assertEqual(float(element.get("x1")), endpoint[0])
            self.assertEqual(float(element.get("x2")), endpoint[0])
            self.assertEqual((float(element.get("y1")) + float(element.get("y2"))) / 2,
                             endpoint[1])

    def test_current_corrections_and_unknowns_are_visible_in_the_public_page(self):
        correction = self.page.by_id("current-i09")
        self.assertNotIn("hidden", correction["attrs"])
        for phrase in ("若旱魃為害", "穀水注之不竭", "離畢滂潤", "陽穀泄之不盈"):
            self.assertIn(phrase, correction["text"])
        ledger = {item["id"]: item for item in self.data["current_water_ledger"]}
        for water_id, item in ledger.items():
            row = self.page.by_id("water-" + water_id)
            current_links = [node["attrs"]["data-current-ref"]
                             for node in Markup.descendants(row)
                             if "data-current-ref" in node["attrs"]]
            self.assertEqual(set(current_links), set(item["current_refs"]), water_id)
            self.assertEqual(len(current_links), len(set(current_links)), water_id)
        for water_id in ("W20", "W21"):
            text = self.page.by_id("water-" + water_id)["text"]
            self.assertIn("撤回", text)
            self.assertIn("I09", text)
        self.assertIn("夏水冬竭", self.page.by_id("water-W20")["text"])
        self.assertIn("台下", self.page.by_id("water-W21")["text"])
        unknowns = self.page.by_id("unknowns")["text"]
        self.assertIn("南墙", unknowns)
        self.assertIn("合流", unknowns)
        self.assertIn("永桥", unknowns)
        self.assertNotIn("inner_south_wall_geometry", unknowns)
        self.assertNotIn("north_road_confluence_coordinates", unknowns)

    def test_context_links_reach_evidence_without_becoming_spatial_connections(self):
        anchors = [element for element in self.svg06a.iter(NS + "a")
                   if element.get("data-context-id")]
        expected = {row["mapped_feature_id"] for row in self.data["water_evidence_navigation"]}
        self.assertEqual(len(anchors), 9)
        self.assertEqual({anchor.get("data-context-id") for anchor in anchors}, expected)
        for anchor in anchors:
            identifier = "context-" + anchor.get("data-context-id")
            self.assertEqual(anchor.get("href"), "#" + identifier)
            self.page.by_id(identifier)
        evidence_nodes = [node for node in self.page.nodes
                          if node["tag"] == "details"
                          and "evidence-record" in node["attrs"].get("class", "").split()]
        expected_ids = {"evidence-" + record["ref"].replace("/", "-")
                        for record in self.data["current_relations"]}
        self.assertEqual({node["attrs"].get("id") for node in evidence_nodes}, expected_ids)
        self.assertEqual(len(evidence_nodes), 100)

    def test_downloads_and_offline_bundle_match_the_two_source_frames(self):
        info = read(SITE / "build-info.json")
        meta = info["prosperity_backbone_p469"]
        manifest_name = "backbone-469/bundle-manifest.json"
        manifest = read(SITE / manifest_name)
        self.assertEqual(meta["source_commit"], info["source_commit"])
        self.assertEqual(manifest["source_commit"], info["source_commit"])
        self.assertEqual(set(meta["rendered_06a_feature_ids"]), RENDERED_06A)
        self.assertEqual(set(meta["source_frames"]), {"frame-06a", "frame-qian2018"})
        self.assertEqual(meta["atlas_pages"], 2)
        self.assertEqual(meta["context_links"], 10)
        self.assertEqual(meta["water_context_links"], 9)
        self.assertEqual(meta["urban_context_links"], 2)
        self.assertEqual(meta["urban_contexts"], "backbone-469/urban-contexts.json")
        self.assertEqual(len(PdfReader(SITE / meta["atlas"]).pages), 2)
        self.assertEqual(read(SITE / meta["readings"]), self.data)
        self.assertEqual((SITE / meta["readings"]).read_bytes(),
                         (SOURCE / "readings.json").read_bytes())
        downloads = {urlsplit(href).path.removeprefix("./") for href in self.page.hrefs}
        required = {meta["atlas"], meta["bundle"], meta["readings"], meta["urban_contexts"],
                    "backbone-469/frame-06a.svg", "backbone-469/frame-qian2018.svg"}
        self.assertTrue(required <= downloads)
        published = required | {meta["page"], manifest_name,
                                "backbone-469/study.css", "backbone-469/backbone-ui.js"}
        for name in published:
            self.assertEqual(digest(SITE / name), info["files_sha256"][name], name)
        for name, expected in manifest["source_inputs_sha256"].items():
            self.assertEqual(digest(ROOT / name), expected, name)
        with zipfile.ZipFile(SITE / meta["bundle"]) as archive:
            members = set(archive.namelist())
            self.assertEqual(members, set(manifest["files_sha256"]) | {manifest_name, "index.html"})
            self.assertEqual(archive.read(manifest_name), (SITE / manifest_name).read_bytes())
            for name, expected in manifest["files_sha256"].items():
                content = archive.read(name)
                self.assertEqual(hashlib.sha256(content).hexdigest(), expected, name)
                self.assertEqual(content, (SITE / name).read_bytes(), name)
            offline = Markup(archive.read("index.html").decode("utf-8"))
            identifiers = {node["attrs"].get("id") for node in offline.nodes}
            for node in offline.nodes:
                for key in ("href", "src"):
                    if key not in node["attrs"]:
                        continue
                    url = node["attrs"][key]
                    parts = urlsplit(url)
                    if parts.scheme or parts.netloc:
                        continue
                    if parts.path:
                        self.assertIn(unquote(parts.path).removeprefix("./"), members, url)
                    elif parts.fragment:
                        self.assertIn(unquote(parts.fragment), identifiers, url)


if __name__ == "__main__":
    unittest.main()
