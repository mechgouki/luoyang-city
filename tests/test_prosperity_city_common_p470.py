"""Check P470 against its earlier evidence, including unlocated objects and open walls."""
import csv
import hashlib
import io
import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
FOLDER = "common-470"
PAGE = "prosperity-city-common.html"
VERSION = "prosperity-city-common-p470"
SVG = "{http://www.w3.org/2000/svg}"
sys.path.insert(0, str(ROOT / "tools"))
from city_common_470_data import build_data


FROZEN_INPUTS = {
    "research/prosperity-v1/geographic-evidence.json": "80a2e5457789d0056bafe5cb5eb5df73bea23fb2e9d733a784ed0068562ead79",
    "research/prosperity-v4/city-distribution-p451.json": "8749bac2e6f56f017b99790b11d757edb165a4903749665a30b67c5430f932f9",
    "research/prosperity-v4/network-462/network.json": "f1081cfc39fb16e67e81271be177755fdab4cd46a18283e0d1ed46efb3e1275b",
    "research/prosperity-v4/network-462/roads.json": "6a48b686ef2c133731f080405d525b4a60e9bf0506cfb35a78ff0cfa2b0efb8d",
    "research/prosperity-v4/backbone-469/readings.json": "f82027d6affcc06c8d3e727f65f6ac29cd51111df04b4e01e1387841ee4b5c0a",
    "research/prosperity-v4/backbone-469/jianchun-plan-audit.json": "4471b8a411b21ecfea42509d9a88584a8a4f5677b3ad49af7319bdca59f6751f",
    "research/prosperity-v4/street-clusters-p453.json": "9b69da412a86d5e21e82b2cfdcac747b667ecad053de868618fd7474e4bcd116",
    "research/prosperity-v4/road-functions-p452.json": "6f963d3dfcfe7c74f02fefd4528958d65868cb53691259f40aa890f0649e074c",
    "research/prosperity-v1/text-review.json": "e897985535b46d802708e628da4bad5a40c667ad2283caad55aeb0b347cb3836",
    "research/dual-b1/decisions.json": "aee1cdc54a4f0888f3793712c559a75489ea484e9786d2bfe370466faedfb26f",
    "research/dual-b7/luonan-river-markets.json": "0acfc920d242f26f3e8de894085d0e7963ed2a4a74ec981a626a8f8450f8e42d",
}
COUNTS = {
    "source_features": 30, "features": 25, "site_remains": 24, "modern_features": 1,
    "prior_backbone_features": 22, "added_existing_features": 3, "building_cards": 4,
    "roads": 8, "gate_points": 10, "wall_groups": 4, "partial_enclosure_parts": 7,
    "water_records": 34, "water_relations": 100, "water_context_links": 9,
    "urban_scenes": 3, "urban_relations": 17, "new_geographic_coordinates": 0,
    "new_metric_measurements": 0, "new_historical_edges": 0, "new_geographic_footprints": 0,
}
DOWNLOADS = {
    f"{FOLDER}/city-common.svg", f"{FOLDER}/readings.json", f"{FOLDER}/places.csv",
    f"{FOLDER}/reuse-plan.json", f"{FOLDER}/bundle-manifest.json", "downloads/common-470.zip",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(content):
    return hashlib.sha256(content).hexdigest()


class Markup(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
            "meta", "param", "source", "track", "wbr"}

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.nodes, self.stack = [], []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "text": ""}
        self.nodes.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.nodes.append({"tag": tag, "attrs": dict(attrs), "text": ""})

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, text):
        for node in self.stack:
            node["text"] += text

    def with_attr(self, name):
        return [node for node in self.nodes if name in node["attrs"]]

    def by_id(self, identifier):
        matches = [node for node in self.nodes if node["attrs"].get("id") == identifier]
        if len(matches) != 1:
            raise AssertionError(f"Expected one #{identifier}, found {len(matches)}")
        return matches[0]


def source_polyline(path_data):
    """Reject closures/curves and compare every original native PDF vertex."""
    number = r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?"
    tokens = re.findall(rf"[A-Za-z]|{number}", path_data)
    parts, active, command, index = [], None, None, 0
    while index < len(tokens):
        if re.fullmatch("[A-Za-z]", tokens[index]):
            command = tokens[index]
            assert command in {"M", "L"}, f"Source path acquired {command}"
            index += 1
        assert command in {"M", "L"} and index + 1 < len(tokens)
        point = [float(tokens[index]), float(tokens[index + 1])]
        if command == "M":
            active = []
            parts.append(active)
            command = "L"
        active.append(point)
        index += 2
    return parts


class Common470Sources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_data(ROOT)
        cls.geo = read(ROOT / "research/prosperity-v1/geographic-evidence.json")
        cls.distribution = read(ROOT / "research/prosperity-v4/city-distribution-p451.json")
        cls.clusters = read(ROOT / "research/prosperity-v4/street-clusters-p453.json")
        cls.backbone = read(ROOT / "research/prosperity-v4/backbone-469/readings.json")

    def test_eleven_prior_inputs_remain_byte_exact(self):
        plan = read(ROOT / "research/prosperity-v4/common-470/reuse-plan.json")
        frozen = {**plan["required_input_sha256"], **plan["required_urban_input_sha256"]}
        self.assertEqual(frozen, FROZEN_INPUTS)
        self.assertEqual(set(self.data["source_inputs_sha256"]),
                         set(frozen) | {"research/prosperity-v4/common-470/reuse-plan.json"})
        for path, expected in self.data["source_inputs_sha256"].items():
            with self.subTest(path=path):
                self.assertEqual(sha((ROOT / path).read_bytes()), expected)
                if path in FROZEN_INPUTS:
                    self.assertEqual(expected, FROZEN_INPUTS[path])

    def test_only_three_existing_features_join_the_prior_source_view(self):
        self.assertEqual(self.data["version"], "P4.7")
        self.assertEqual(self.data["counts"], COUNTS)
        source = {feature["id"]: feature for feature in self.geo["features"]}
        features = {feature["id"]: feature for feature in self.data["features"]}
        frame = self.data["source_frame"]
        additions = {"geo-taiji-hall-reference", "geo-yongning-pagoda-reference",
                     "geo-yongning-temple-walls"}
        prior = set(self.data["wall_feature_ids"]) - {"geo-yongning-temple-walls"}
        prior |= {road["p1_feature_id"] for road in self.data["roads"]}
        prior |= {gate["id"] for gate in self.data["gates"]} | {"geo-modern-luo-river"}
        self.assertEqual(len(prior), 22)
        self.assertEqual(set(features), prior | additions)
        self.assertEqual(frame["added_existing_feature_ids"],
                         ["geo-taiji-hall-reference", "geo-yongning-pagoda-reference",
                          "geo-yongning-temple-walls"])
        self.assertEqual(set(frame["prior_backbone_display_feature_ids"]), prior)
        self.assertEqual(len(self.data["features"]), len(features))
        for identifier, feature in features.items():
            self.assertEqual(feature, source[identifier], identifier)
        self.assertEqual({row["id"] for row in self.data["not_rendered_source_features"]},
                         set(source) - set(features))
        self.assertEqual(frame["crs"], "EPSG:4610")
        self.assertIsNone(frame["new_geographic_transform"])
        self.assertTrue(frame["shared_source_not_new_registration"])
        self.assertFalse(self.data["modern_reference_default_visible"])
        self.assertEqual(features["geo-modern-luo-river"]["layer"], "modern_geographic_reference")

    def test_building_cards_keep_identity_dimensions_and_nonfootprint_scope(self):
        originals = {row["id"]: row for row in self.distribution["anchored_buildings"]}
        places = {row["id"]: row for row in self.data["places"]}
        self.assertEqual(set(places), {"C01", "C02", "C03", "C04"})
        for identifier, place in places.items():
            self.assertEqual({key: value for key, value in place.items()
                              if key != "reading_navigation"}, originals[identifier])
            self.assertFalse(place["site_registered_polygon_allowed"])
            self.assertFalse(place["roof_style_verified"])
            self.assertIsNone(place["measured_elevation_m"])
            self.assertEqual(place["reading_navigation"]["semantics"], "project_reading_navigation_only")
        taiji = places["C03"]
        self.assertIsNone(taiji["entity_id"])
        self.assertIsNone(taiji["reading_navigation"]["scene_binding_feature_id"])
        self.assertEqual(taiji["reading_navigation"]["scene_bindings"], [])
        self.assertEqual(taiji["reading_navigation"]["urban_cluster_ids"], [])
        yongning = places["C04"]["reading_navigation"]
        self.assertEqual(yongning["selection_feature_ids"],
                         ["geo-yongning-pagoda-reference", "geo-yongning-temple-walls"])
        self.assertEqual(yongning["scene_binding_feature_id"], "geo-yongning-temple-walls")
        self.assertEqual(yongning["scene_bindings"], [row for row in self.clusters["spatial_index_references"]
                                                    if row["feature_id"] == "geo-yongning-temple-walls"])

    def test_roads_gates_and_seven_open_wall_parts_reuse_source_records(self):
        self.assertEqual(self.data["roads"], read(ROOT / "research/prosperity-v4/network-462/roads.json")["routes"])
        self.assertEqual(self.data["gates"], read(ROOT / "research/prosperity-v4/network-462/network.json")["gates"])
        self.assertEqual(self.data["enclosure_context"], self.distribution["enclosure_context"])
        wall = next(feature for feature in self.data["features"] if feature["id"] == "geo-yongning-temple-walls")
        self.assertEqual(wall["source_pdf_geometry"]["type"], "MultiLineString")
        self.assertEqual(len(wall["source_pdf_geometry"]["coordinates"]), 7)
        self.assertFalse(self.data["enclosure_context"][0]["closed_polygon_allowed"])
        self.assertEqual(self.data["jianchun_plan_audit"],
                         read(ROOT / "research/prosperity-v4/backbone-469/jianchun-plan-audit.json"))
        self.assertIsNone(self.data["jianchun_plan_audit"]["read_status"]["geographic_transform"])
        self.assertEqual(self.data["jianchun_plan_audit"]["read_status"]["accepted_control_pairs"], [])

    def test_scenes_and_functions_preserve_all_original_records_and_bindings(self):
        urban = self.data["urban"]
        self.assertEqual(urban["clusters"], self.clusters["clusters"])
        self.assertEqual(urban["scene_bindings"], self.clusters["spatial_index_references"])
        self.assertEqual(urban["evidence_grades"], self.clusters["evidence_grades"])
        self.assertEqual(urban["forbidden_inferences"], self.clusters["forbidden_inferences"])
        self.assertEqual(urban["functions"], read(ROOT / "research/prosperity-v4/road-functions-p452.json")["nongeographic_function_groups"])
        self.assertEqual(urban["counts"], {"scene_count": 3, "object_count": 20, "relation_count": 17,
                         "direct_relation_count": 16, "interpretive_relation_count": 1, "event_count": 2,
                         "function_group_count": 5, "function_object_count": 15, "reference_object_count": 5,
                         "source_binding_count": 3, "source_record_count": 12})
        nodes = {node["id"]: node for scene in urban["clusters"] for node in scene["nodes"]}
        function_ids = {identifier for group in urban["functions"] for identifier in group["entity_ids"]}
        self.assertEqual(set(nodes) - function_ids, set(urban["reference_entity_ids"]))
        self.assertIsNone(nodes["ic_palace_avenue"]["feature_id"])
        k03 = next(scene for scene in urban["clusters"] if scene["id"] == "K03")
        self.assertTrue(all(node["feature_id"] is None for node in k03["nodes"]))
        self.assertTrue(all(not edge["geographic_line_allowed"] for scene in urban["clusters"] for edge in scene["edges"]))
        self.assertEqual(urban["new_historical_relationships"], 0)
        self.assertEqual(urban["new_historical_coordinates"], 0)

    def test_relation_sources_are_full_original_records_with_source_locators(self):
        urban = self.data["urban"]
        p1 = {row["legacy_title"]: row for row in read(ROOT / "research/prosperity-v1/text-review.json")["records"]}
        b1 = {row["id"]: row for row in read(ROOT / "research/dual-b1/decisions.json")["decisions"]}
        b7 = {row["id"]: row for row in read(ROOT / "research/dual-b7/luonan-river-markets.json")["evidence"]}
        cited = {row["source_record"] for scene in urban["clusters"]
                 for row in scene["edges"] + scene.get("temporal_events", [])}
        self.assertEqual(set(urban["source_records"]), cited)
        for identifier, record in urban["source_records"].items():
            original = (b1[identifier.split(":", 1)[1]] if identifier.startswith("B1:")
                        else b7[identifier.split(":", 1)[1]] if identifier.startswith("B7:") else p1[identifier])
            self.assertEqual(record["record"], original, identifier)
            expected_locator = (original["quote_locator"] if identifier.startswith("B7:")
                                else original.get("quote_locator", original.get("legacy_locator", "")))
            self.assertEqual(record["locator"], expected_locator, identifier)
            self.assertTrue(record["links"], identifier)

    def test_water_corrections_remain_non_geographic_and_unchanged(self):
        for field in ("water_evidence_navigation", "current_water_ledger", "current_relations",
                      "corrected_current_I09", "target_period", "phase_rule"):
            self.assertEqual(self.data[field], self.backbone[field], field)
        self.assertEqual(self.data["water_correction"], self.backbone["correction"])
        self.assertEqual(self.data["water_relation_plates"], self.backbone["relation_plates"])
        for water in self.data["current_water_ledger"]:
            self.assertIsNone(water["geometry"])
            self.assertIsNone(water["geographic_frame"])
            self.assertIsNone(water["target_bank_geometry"])
        relations = {row["ref"]: row for row in self.data["current_relations"]}
        self.assertEqual(relations["P467/inner/I09"]["legacy_water_ids"], ["W17", "W18", "W19", "W34"])
        self.assertTrue(all(row["geographic_coordinates"] is None for row in relations.values()))


class Common470Published(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read(SITE / FOLDER / "readings.json")
        cls.info = read(SITE / "build-info.json")
        cls.meta = cls.info["prosperity_city_common_p470"]
        cls.page = Markup((SITE / PAGE).read_text(encoding="utf-8"))
        cls.svg = ET.parse(SITE / FOLDER / "city-common.svg").getroot()

    def test_public_dataset_and_release_describe_the_same_reviewed_view(self):
        self.assertEqual(self.data, build_data(ROOT))
        release = read(SITE / "release.json")
        self.assertEqual(self.meta["version"], VERSION)
        self.assertEqual(release["prosperity_city_common_p470_version"], VERSION)
        self.assertIn(VERSION, release["extensions"])
        self.assertEqual(self.meta["source_commit"], self.info["source_commit"])
        self.assertEqual(self.meta["page"], PAGE)
        self.assertEqual(self.meta["folder"], FOLDER)
        self.assertEqual(self.meta["plates"], ["city-common.svg"])
        self.assertEqual(self.meta["counts"], COUNTS)
        self.assertEqual(self.meta["new_historical_coordinates"], 0)
        self.assertEqual(self.meta["readings"], f"{FOLDER}/readings.json")
        self.assertEqual(self.meta["manifest"], f"{FOLDER}/bundle-manifest.json")
        self.assertEqual(self.meta["bundle"], "downloads/common-470.zip")

    def test_svg_retains_every_native_vertex_and_point_without_new_closure(self):
        self.assertEqual(self.svg.get("id"), "city-common-map")
        features = {row["id"]: row for row in self.data["features"]}
        self.assertEqual({node.get("data-feature-id") for node in self.svg.iter()
                          if node.get("data-feature-id")}, set(features))
        geometry = [node for node in self.svg.iter() if node.get("data-source-feature-id")]
        self.assertEqual({node.get("data-source-feature-id") for node in geometry}, set(features))
        for identifier, feature in features.items():
            with self.subTest(feature=identifier):
                nodes = [node for node in geometry if node.get("data-source-feature-id") == identifier]
                source = feature["source_pdf_geometry"]
                if source["type"] == "Point":
                    self.assertEqual(len(nodes), 1)
                    self.assertEqual(nodes[0].tag, SVG + "circle")
                    self.assertEqual([float(nodes[0].get("cx")), float(nodes[0].get("cy"))], source["coordinates"])
                else:
                    parts = [source["coordinates"]] if source["type"] == "LineString" else source["coordinates"]
                    self.assertEqual(len(nodes), len(parts))
                    self.assertEqual(len({node.get("data-part") for node in nodes}), len(parts))
                    self.assertTrue(all(node.get("data-part") is not None and node.tag == SVG + "path" for node in nodes))
                    actual = [part for node in nodes for part in source_polyline(node.get("d", ""))]
                    self.assertEqual(actual, parts)

    def test_static_cards_scenes_fallback_links_and_all_relations_are_present(self):
        self.page.by_id("city-common-map")
        for place in self.data["places"]:
            card = self.page.by_id("place-" + place["id"])
            self.assertIn(place["name"], card["text"])
            self.assertNotIn("hidden", card["attrs"])
        panels = self.page.with_attr("data-scene-panel")
        self.assertEqual({node["attrs"]["id"] for node in panels}, {"scene-K01", "scene-K02", "scene-K03"})
        self.assertTrue(all("hidden" not in node["attrs"] for node in panels))
        edges = {row["id"] for scene in self.data["urban"]["clusters"] for row in scene["edges"]}
        events = {row["id"] for scene in self.data["urban"]["clusters"] for row in scene.get("temporal_events", [])}
        self.assertEqual({node["attrs"]["data-urban-edge-id"] for node in self.page.with_attr("data-urban-edge-id")}, edges)
        self.assertEqual({node["attrs"]["data-urban-event-id"] for node in self.page.with_attr("data-urban-event-id")}, events)
        anchors = [node for node in self.page.with_attr("data-place-id") if node["tag"] == "a"]
        self.assertEqual({node["attrs"]["data-place-id"] for node in anchors}, {"C01", "C02", "C03", "C04"})
        for anchor in anchors:
            self.assertEqual(anchor["attrs"]["href"], "#place-" + anchor["attrs"]["data-place-id"])
        self.assertNotIn("checked", self.page.by_id("layer-modern")["attrs"])
        old = Markup((SITE / "prosperity-backbone-p469.html").read_text(encoding="utf-8"))
        old.by_id("p470-entry")
        self.assertTrue(any(node["attrs"].get("href", "").removeprefix("./") == PAGE for node in old.nodes))

    def test_six_download_targets_are_visible_unique_and_hash_registered(self):
        links = [node for node in self.page.nodes if node["tag"] == "a" and "download" in node["attrs"]]
        paths = [urlsplit(node["attrs"].get("href", "")).path.removeprefix("./") for node in links]
        for path in DOWNLOADS:
            self.assertEqual(paths.count(path), 1, path)
        for path in DOWNLOADS | {PAGE, f"{FOLDER}/study.css", f"{FOLDER}/common-ui.js"}:
            self.assertEqual(sha((SITE / path).read_bytes()), self.info["files_sha256"][path], path)
        rows = list(csv.DictReader(io.StringIO((SITE / FOLDER / "places.csv").read_text(encoding="utf-8-sig"))))
        self.assertEqual(len(rows), 4)
        # The exported card identifier remains explicit even if display columns expand.
        self.assertEqual({row["card_id"] for row in rows}, {"C01", "C02", "C03", "C04"})
        places = {place["id"]: place for place in self.data["places"]}
        for row in rows:
            place = places[row["card_id"]]
            self.assertEqual(row["feature_id"], place["feature_id"])
            self.assertEqual(row["entity_id"], place["entity_id"] or "")
            self.assertEqual(row["scene_binding_feature_id"], place["reading_navigation"]["scene_binding_feature_id"] or "")
            self.assertEqual(float(row["east_west_m"]), place["reported_footprint_m"]["east_west"])
            self.assertEqual(float(row["north_south_m"]), place["reported_footprint_m"]["north_south"])
        self.assertEqual(read(SITE / FOLDER / "reuse-plan.json"), read(ROOT / "research/prosperity-v4/common-470/reuse-plan.json"))

    def test_offline_archive_is_complete_and_all_declared_bytes_match(self):
        manifest_name = f"{FOLDER}/bundle-manifest.json"
        manifest = read(SITE / manifest_name)
        self.assertEqual(manifest["source_commit"], self.info["source_commit"])
        self.assertEqual(manifest["version"], VERSION)
        declared = manifest["files_sha256"]
        self.assertNotIn(manifest_name, declared)
        self.assertNotIn(self.meta["bundle"], declared)
        with zipfile.ZipFile(SITE / self.meta["bundle"]) as archive:
            members = set(archive.namelist())
            self.assertEqual(members, set(declared) | {manifest_name, "index.html"})
            self.assertEqual(len(members), len(archive.namelist()))
            self.assertEqual(archive.read(manifest_name), (SITE / manifest_name).read_bytes())
            for path, expected in declared.items():
                content = archive.read(path)
                self.assertEqual(sha(content), expected, path)
                if path != "index.html":
                    self.assertEqual(content, (SITE / path).read_bytes(), path)
            offline = Markup(archive.read("index.html").decode("utf-8"))
            identifiers = {node["attrs"].get("id") for node in offline.nodes}
            for node in offline.nodes:
                for key in ("href", "src"):
                    parts = urlsplit(node["attrs"].get(key, ""))
                    if parts.scheme or parts.netloc:
                        continue
                    if parts.path:
                        self.assertIn(unquote(parts.path).removeprefix("./"), members)
                    elif parts.fragment:
                        self.assertIn(unquote(parts.fragment), identifiers)

    def test_prior_page_only_gains_one_reversible_entry_and_old_assets_keep_hashes(self):
        preserved = self.meta["preservation"]
        manifest = read(SITE / self.meta["manifest"])
        self.assertEqual(manifest["preservation"], preserved)
        self.assertEqual(preserved["previous_page"], "prosperity-backbone-p469.html")
        self.assertEqual(preserved["entry_id"], "p470-entry")
        page = (SITE / preserved["previous_page"]).read_bytes()
        entry = preserved["entry_html"].encode("utf-8")
        self.assertEqual(page.count(entry), 1)
        self.assertEqual(page.count(b'id="p470-entry"'), 1)
        self.assertEqual(sha(page.replace(entry, b"")), preserved["previous_page_sha256"])
        protected = preserved["protected_files_sha256"]
        expected_maps = {
            "prosperity/source-layout.svg", "prosperity-city-distribution/grounded-distribution.svg",
            "backbone-469/frame-06a.svg", "backbone-469/frame-qian2018.svg", "downloads/backbone-469.pdf",
            "backbone-469/readings.json", "backbone-469/urban-contexts.json",
            "backbone-469/jianchun-plan-audit.json", "backbone-469/jianchun-source-context.svg",
            "backbone-469/jianchun-structure-reading.svg",
        }
        self.assertTrue(expected_maps <= set(protected))
        panoramas = {path for path in protected if path.endswith(".webp")}
        self.assertEqual(len(panoramas), 4)
        for path, expected in protected.items():
            self.assertEqual(sha((SITE / path).read_bytes()), expected, path)
            self.assertEqual(self.info["files_sha256"][path], expected, path)


if __name__ == "__main__":
    unittest.main()
