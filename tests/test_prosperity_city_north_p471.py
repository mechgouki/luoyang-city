"""Verify northern-city reuse against the original geometry and reviewed text."""
from collections import Counter
import csv
import io
import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

from test_prosperity_city_common_p470 import FROZEN_INPUTS, Markup, read, sha, source_polyline


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
FOLDER = "north-471"
PAGE = "prosperity-city-north.html"
VERSION = "prosperity-city-north-p471"
SVG = "{http://www.w3.org/2000/svg}"
sys.path.insert(0, str(ROOT / "tools"))
from city_common_470_data import build_data as build_common
from city_north_471_data import build_data


COUNTS = {
    "source_features": 30, "features": 27, "site_remains": 26, "modern_features": 1,
    "prior_common_features": 25, "added_existing_features": 2, "north_entries": 3,
    "evidence_records": 16, "evidence_groups": 3, "entities": 16, "bound_entities": 3,
    "unbound_entities": 13, "source_binding_features": 4, "constraints": 21,
    "water_relations": 5, "roads": 3, "jinyong_wall_parts": 5, "jinyong_wall_vertices": 13,
    "corrected_quotations": 1, "modern_annotations": 2, "new_geographic_coordinates": 0,
    "new_metric_measurements": 0, "new_historical_relationships": 0, "new_geographic_footprints": 0,
}
GROUPS = {
    "G01": ["NG01", "NG02", "NG03", "NG04", "NG07", "NG08", "NG09"],
    "G02": ["NG13", "NG14", "NG15", "NG16"],
    "G03": ["NG05", "NG06", "NG10", "NG11", "NG12"],
}
DOWNLOADS = {
    f"{FOLDER}/city-overview.svg", f"{FOLDER}/north-detail.svg", f"{FOLDER}/readings.json",
    f"{FOLDER}/evidence.csv", f"{FOLDER}/reuse-plan.json", f"{FOLDER}/bundle-manifest.json",
    "downloads/north-471.zip",
}
ASSETS = (DOWNLOADS - {f"{FOLDER}/bundle-manifest.json", "downloads/north-471.zip"}) | {
    f"{FOLDER}/study.css", f"{FOLDER}/north-ui.js"}
ADDITIONS = {"geo-jinyong-bing-wall", "geo-jinyong-bing-reference"}
WATER_REFS = {"P467/outer/O02", "P467/outer/O03", "P467/outer/O04", "P467/outer/O05", "P467/inner/I01"}


def compact(text):
    return re.sub(r"\s+", "", text or "")


class North471Sources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_data(ROOT)
        cls.plan = read(ROOT / "research/prosperity-v4/north-471/reuse-plan.json")
        cls.geo = read(ROOT / "research/prosperity-v1/geographic-evidence.json")
        cls.original = read(ROOT / "research/dual-b4/north-gates.json")
        cls.reviews = {row["key"]: row for row in read(ROOT / "research/prosperity-v1/text-review.json")["records"]}

    def test_source_hashes_and_original_frame_remain_unchanged(self):
        hashes = {**FROZEN_INPUTS,
                  "research/dual-b4/north-gates.json": "31810a50d3ddd93eee9c23a609f92a55a3bac0533cf2b72f494e47b8cb31f53f"}
        for path, expected in hashes.items():
            self.assertEqual(sha((ROOT / path).read_bytes()), expected, path)
            self.assertEqual(self.data["source_inputs_sha256"][path], expected, path)
        self.assertEqual(len(self.data["source_inputs_sha256"]), 15)
        for path, digest in self.data["source_inputs_sha256"].items():
            self.assertEqual(sha((ROOT / path).read_bytes()), digest, path)
        self.assertEqual(self.data["counts"], COUNTS)
        self.assertEqual(self.plan["expected_counts"], COUNTS)
        self.assertEqual(self.data["source_frame"]["crs"], "EPSG:4610")
        self.assertIsNone(self.data["new_geographic_transform"])
        self.assertIsNone(self.data["source_frame"]["new_geographic_transform"])
        self.assertFalse(self.data["modern_reference_default_visible"])
        self.assertEqual(self.data["display_frames"], self.plan["display_frames"])
        self.assertEqual(self.data["display_frames"]["north"]["native_bounds"], [270, 230, 390, 280])
        for frame in self.data["display_frames"].values():
            self.assertEqual(frame["native_units"], "PDF point")
            self.assertEqual(frame["semantics"], "display_crop_only")

    def test_common_data_and_all_twenty_seven_source_features_are_exact(self):
        self.assertEqual(self.data["common"], build_common(ROOT))
        features = {row["id"]: row for row in self.data["features"]}
        original = {row["id"]: row for row in self.geo["features"]}
        self.assertEqual(len(features), 27)
        self.assertEqual(set(features), {row["id"] for row in self.data["common"]["features"]} | ADDITIONS)
        self.assertEqual(set(self.data["source_frame"]["added_existing_feature_ids"]), ADDITIONS)
        for identifier, feature in features.items():
            self.assertEqual(feature, original[identifier], identifier)
        self.assertEqual(features[self.data["modern_feature_id"]]["layer"], "modern_geographic_reference")

    def test_jinyong_is_five_open_parts_and_a_representative_point(self):
        features = {row["id"]: row for row in self.data["features"]}
        wall = features["geo-jinyong-bing-wall"]
        point = features["geo-jinyong-bing-reference"]
        self.assertEqual(wall["source_pdf_geometry"]["type"], "MultiLineString")
        parts = wall["source_pdf_geometry"]["coordinates"]
        self.assertEqual(len(parts), 5)
        self.assertEqual(sum(map(len, parts)), 13)
        self.assertTrue(all(part[0] != part[-1] for part in parts))
        self.assertEqual(point["source_pdf_geometry"], {"type": "Point", "coordinates": [285.45, 259.35]})
        self.assertEqual(point["approximation"]["status"], "representative_point_within_mapped_remains")
        self.assertFalse(point["approximation"]["is_field_verified_gcp"])
        self.assertIsNone(point["approximation"]["absolute_ground_accuracy_m"])
        entries = {row["id"]: row for row in self.data["north_entries"]}
        self.assertEqual(set(entries), {"N01", "N02", "N03"})
        self.assertEqual(set(entries["N01"]["feature_ids"]), ADDITIONS)
        self.assertEqual(entries["N02"]["feature_ids"], ["geo-daxia-gate"])
        self.assertEqual(entries["N03"]["feature_ids"], ["geo-guangmo-gate"])
        for entry in entries.values():
            self.assertEqual(entry["navigation_semantics"], "context_link_only")
            self.assertIn(entry["point_feature_id"], entry["feature_ids"])
            self.assertTrue(all(features[key]["entity_id"] == entry["entity_id"] for key in entry["feature_ids"]))

    def test_all_legacy_records_keep_p1_overlay_and_ng15_notes_separate(self):
        self.assertEqual(self.data["original_evidence"], self.original["evidence"])
        self.assertEqual(len(self.data["evidence"]), 16)
        self.assertEqual(self.data["source_records"], {row["id"]: row for row in self.original["sources"]})
        for row, original in zip(self.data["evidence"], self.original["evidence"]):
            with self.subTest(record=row["id"]):
                self.assertEqual({key: value for key, value in row.items() if key != "reading_overlay"}, original)
                review = self.reviews["B4:" + row["id"]]
                self.assertEqual(self.data["text_review_records"][review["key"]], review)
                overlay = row["reading_overlay"]
                self.assertEqual(overlay["review_key"], review["key"])
                self.assertFalse(overlay["new_historical_discovery"])
                self.assertIsNone(row["geographic_coordinates"])
                if row["id"] != "NG15":
                    self.assertEqual(overlay["quote"], original["quote"])
                    self.assertFalse(overlay["correction_applied"])
                    self.assertEqual(overlay["annotations"], [])
                    continue
                manual = review["manual_context_review"]
                self.assertEqual(overlay["quote"], manual["corrected_quote"])
                self.assertEqual(overlay["quote"], "瑤光寺北有承明門，有金墉城，即魏氏所築。")
                self.assertNotEqual(overlay["quote"], row["quote"])
                self.assertTrue(overlay["correction_applied"])
                self.assertFalse(overlay["legacy_quote_display_allowed_as_body"])
                notes = [{**note, "author": manual["editorial_note"]["author"]}
                         for note in manual["source_contexts"] if note["layer"] == "现代夹注"]
                self.assertEqual(overlay["annotations"], notes)
                self.assertEqual(len(notes), 2)
                for note in notes:
                    self.assertNotIn(note["quote"], overlay["quote"])

    def test_groups_entities_and_constraints_do_not_create_locations(self):
        self.assertEqual({row["id"]: row["evidence_ids"] for row in self.data["evidence_groups"]}, GROUPS)
        grouped = [key for row in self.data["evidence_groups"] for key in row["evidence_ids"]]
        self.assertEqual(len(grouped), len(set(grouped)))
        self.assertEqual(set(grouped), {row["id"] for row in self.original["evidence"]})
        constraints = [item for row in self.data["evidence"] for item in row["constraints"]]
        self.assertEqual(len(constraints), 21)
        self.assertEqual(Counter(row["basis"] for row in constraints), {
            "direct": 14, "editorial_supplement": 1, "qualitative_text": 1,
            "paragraph_context": 2, "direct_section_context": 1,
            "explicit_direction_ambiguous_referent": 1, "narrative_context": 1})
        self.assertEqual(self.data["constraint_basis_counts"], dict(Counter(row["basis"] for row in constraints)))
        entities = {row["id"]: row for row in read(ROOT / "data/entities.json")}
        bindings = self.data["entity_bindings"]
        self.assertEqual(len(bindings), 16)
        self.assertEqual({row["entity_id"] for row in bindings},
                         {key for row in self.original["evidence"] for key in row["entities"]})
        bound = [row for row in bindings if row["feature_ids"]]
        self.assertEqual({row["entity_id"] for row in bound}, {"ic_jinyong", "gate_daxia", "gate_guangmo"})
        self.assertEqual(sum(len(row["feature_ids"]) for row in bound), 4)
        for row in bindings:
            self.assertEqual(row["name"], entities[row["entity_id"]]["name"])
            self.assertEqual(row["temporal_state"], entities[row["entity_id"]].get("temporal_state"))
            self.assertIsNone(row["geographic_coordinates"])
            if not row["feature_ids"]:
                self.assertIsNone(row["entry_id"])
                self.assertIsNone(row["binding_scope"])
        by_id = {row["id"]: row for row in self.data["evidence"]}
        self.assertEqual(entities["n_chanxu"]["temporal_state"], "undated")
        self.assertIsNone(by_id["NG07"]["constraints"][0]["distance_endpoints"])
        self.assertIsNone(by_id["NG05"]["constraints"][0]["absolute_direction"])
        self.assertEqual(self.data["road_role_bindings"], [])

    def test_water_and_roads_are_complete_existing_records_with_their_limits(self):
        water = {row["ref"]: row for row in read(ROOT / "research/prosperity-v4/backbone-469/readings.json")["current_relations"]}
        self.assertEqual({row["ref"] for row in self.data["water_relations"]}, WATER_REFS)
        for row in self.data["water_relations"]:
            self.assertEqual(row, water[row["ref"]])
            self.assertIsNone(row["geographic_coordinates"])
            self.assertFalse(row["annual_flow_516_528_confirmed"])
        self.assertEqual(self.data["water_navigation_semantics"], "context_link_only")
        source = read(ROOT / "research/prosperity-v4/network-462/roads.json")
        roads = {row["code"]: row for row in source["routes"]}
        self.assertEqual({row["code"] for row in self.data["roads"]}, {"Lz-2", "Lz-4", "Lh-4"})
        for road in self.data["roads"]:
            self.assertEqual(road, roads[road["code"]])
        cited = {key for row in self.data["roads"] for key in row["source_ids"]}
        self.assertEqual(self.data["road_sources"], [row for row in source["sources"] if row["id"] in cited])


class North471Published(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read(SITE / FOLDER / "readings.json")
        cls.info = read(SITE / "build-info.json")
        cls.meta = cls.info["prosperity_city_north_p471"]
        cls.page = Markup((SITE / PAGE).read_text(encoding="utf-8"))

    def test_public_data_metadata_and_release_agree(self):
        self.assertEqual(self.data, build_data(ROOT))
        release = read(SITE / "release.json")
        self.assertEqual(self.meta["version"], VERSION)
        self.assertEqual(release["prosperity_city_north_p471_version"], VERSION)
        self.assertIn(VERSION, release["extensions"])
        self.assertEqual(self.meta["source_commit"], self.info["source_commit"])
        self.assertEqual(self.meta["page"], PAGE)
        self.assertEqual(self.meta["folder"], FOLDER)
        self.assertEqual(set(self.meta["plates"]), {"city-overview.svg", "north-detail.svg"})
        self.assertEqual(self.meta["counts"], COUNTS)
        self.assertEqual(self.meta["readings"], f"{FOLDER}/readings.json")
        self.assertEqual(self.meta["manifest"], f"{FOLDER}/bundle-manifest.json")
        self.assertEqual(self.meta["bundle"], "downloads/north-471.zip")
        self.assertEqual(set(self.meta["download_files"]), DOWNLOADS)
        for key in ("new_historical_coordinates", "new_metric_measurements", "new_historical_relationships", "new_geographic_footprints"):
            self.assertEqual(self.meta[key], 0)
        self.assertIsNone(self.meta["new_geographic_transform"])

    def test_both_svgs_keep_every_native_vertex_part_and_point(self):
        features = {row["id"]: row for row in self.data["features"]}
        for filename, identifier, native in (("city-overview.svg", "north-overview-map", "north-overview-native"),
                                             ("north-detail.svg", "north-detail-map", "north-detail-native")):
            svg = ET.parse(SITE / FOLDER / filename).getroot()
            self.assertEqual(svg.get("id"), identifier)
            feature_nodes = [node for node in svg.iter() if node.get("data-feature-id")]
            self.assertEqual(len(feature_nodes), 27)
            self.assertEqual({node.get("data-feature-id") for node in feature_nodes}, set(features))
            self.assertEqual(len([node for node in svg.iter() if node.get("id") == native]), 1)
            geometry = [node for node in svg.iter() if node.get("data-source-feature-id")]
            self.assertEqual({node.get("data-source-feature-id") for node in geometry}, set(features))
            for key, feature in features.items():
                with self.subTest(svg=filename, feature=key):
                    nodes = [node for node in geometry if node.get("data-source-feature-id") == key]
                    source = feature["source_pdf_geometry"]
                    if source["type"] == "Point":
                        self.assertEqual(len(nodes), 1)
                        self.assertEqual(nodes[0].tag, SVG + "circle")
                        self.assertEqual([float(nodes[0].get("cx")), float(nodes[0].get("cy"))], source["coordinates"])
                    else:
                        parts = [source["coordinates"]] if source["type"] == "LineString" else source["coordinates"]
                        self.assertEqual(len(nodes), len(parts))
                        self.assertEqual(len({node.get("data-part") for node in nodes}), len(parts))
                        self.assertEqual([node.get("data-part") for node in nodes], [str(number) for number in range(1, len(parts) + 1)])
                        self.assertTrue(all(node.tag == SVG + "path" and node.get("data-part") is not None for node in nodes))
                        self.assertEqual([part for node in nodes for part in source_polyline(node.get("d", ""))], parts)

    def test_static_html_keeps_readings_annotations_scope_and_native_links(self):
        for identifier in ("north-detail-map", "north-overview-map", "map-north", "map-overview"):
            self.page.by_id(identifier)
        self.assertEqual(len(self.page.with_attr("data-north-card")), 3)
        for entry in self.data["north_entries"]:
            card = self.page.by_id("north-" + entry["id"])
            self.assertIn(entry["name"], card["text"])
            self.assertIn(compact(entry["scope"]), compact(card["text"]))
            self.assertNotIn("hidden", card["attrs"])
        for anchor in self.page.with_attr("data-north-choice"):
            self.assertEqual(anchor["tag"], "a")
            self.assertEqual(anchor["attrs"]["href"], "#north-" + anchor["attrs"]["data-north-choice"])
        for anchor in self.page.with_attr("data-north-id"):
            if anchor["tag"] == "a":
                self.assertEqual(anchor["attrs"]["href"], "#north-" + anchor["attrs"]["data-north-id"])
        records = self.page.with_attr("data-evidence-id")
        self.assertEqual(len(records), 16)
        self.assertEqual(len(self.page.with_attr("data-evidence-quote")), 16)
        quotes = {node["attrs"]["data-evidence-quote"]: compact(node["text"])
                  for node in self.page.with_attr("data-evidence-quote")}
        for row in self.data["evidence"]:
            article = self.page.by_id("evidence-" + row["id"])
            self.assertNotIn("hidden", article["attrs"])
            self.assertEqual(quotes[row["id"]], compact(row["reading_overlay"]["quote"]))
            for field in ("reading", "limit", "temporal_note"):
                if row[field]:
                    self.assertIn(compact(row[field]), compact(article["text"]), (row["id"], field))
            for variant in row["variants"]:
                self.assertIn(compact(variant["reading"]), compact(article["text"]), row["id"])
        notes = self.page.with_attr("data-modern-annotation")
        self.assertEqual(len(notes), 2)
        ng15 = next(row for row in self.data["evidence"] if row["id"] == "NG15")
        for note in ng15["reading_overlay"]["annotations"]:
            self.assertTrue(any(compact(note["quote"]) in compact(node["text"]) and note["author"] in node["text"] for node in notes))
        self.assertEqual({node["attrs"]["data-evidence-group"] for node in self.page.with_attr("data-evidence-group")}, set(GROUPS))
        bindings = self.page.with_attr("data-north-entity")
        self.assertEqual(len(bindings), 16)
        self.assertEqual(Counter(node["attrs"]["data-entity-placed"] for node in bindings), {"true": 3, "false": 13})
        self.assertEqual({node["attrs"]["data-water-id"] for node in self.page.with_attr("data-water-id")}, WATER_REFS)
        self.assertEqual({node["attrs"]["data-north-road-code"] for node in self.page.with_attr("data-north-road-code")}, {"Lz-2", "Lz-4", "Lh-4"})
        water_cards = {node["attrs"]["data-water-id"]: node for node in self.page.with_attr("data-water-id")}
        for row in self.data["water_relations"]:
            for field in ("quote", "reading", "limit"):
                self.assertIn(compact(row[field]), compact(water_cards[row["ref"]]["text"]), (row["ref"], field))
        road_cards = {node["attrs"]["data-north-road-code"]: node for node in self.page.with_attr("data-north-road-code")}
        for row in self.data["roads"]:
            for field in ("observation", "measure_scope"):
                self.assertIn(compact(row[field]), compact(road_cards[row["code"]]["text"]), (row["code"], field))
        self.assertNotIn("checked", self.page.by_id("north-layer-modern")["attrs"])
        page_text = compact(" ".join(node["text"] for node in self.page.nodes))
        for boundary in ("五段", "310×240", "实测控制点", "13个", "2022年运河报告继续暂缓", "西安1980", "地理配准"):
            self.assertIn(boundary, page_text)

    def test_seven_unique_downloads_hashes_and_corrected_csv(self):
        paths = [urlsplit(node["attrs"].get("href", "")).path.removeprefix("./")
                 for node in self.page.nodes if node["tag"] == "a" and "download" in node["attrs"]]
        self.assertEqual(set(paths), DOWNLOADS)
        self.assertEqual(len(paths), 7)
        for path in DOWNLOADS | ASSETS | {PAGE}:
            self.assertEqual(sha((SITE / path).read_bytes()), self.info["files_sha256"][path], path)
        rows = list(csv.DictReader(io.StringIO((SITE / FOLDER / "evidence.csv").read_text(encoding="utf-8-sig"))))
        self.assertEqual(len(rows), 16)
        evidence = {row["id"]: row for row in self.data["evidence"]}
        self.assertEqual({row["evidence_id"] for row in rows}, set(evidence))
        for row in rows:
            original = evidence[row["evidence_id"]]
            self.assertEqual(row["display_quote"], original["reading_overlay"]["quote"])
            self.assertEqual(row["legacy_quote"], original["quote"])
            self.assertEqual(json.loads(row["annotations"]), original["reading_overlay"]["annotations"])
            self.assertEqual(json.loads(row["source_ids"]), original["sources"])
            self.assertEqual(row["geographic_coordinates"], "")
            self.assertEqual(row["limit"], original["limit"])
            self.assertEqual(row["temporal_note"], original["temporal_note"] or "")
        self.assertEqual(read(SITE / FOLDER / "reuse-plan.json"), read(ROOT / "research/prosperity-v4/north-471/reuse-plan.json"))

    def test_offline_zip_has_nine_members_and_matching_local_links(self):
        manifest_name = f"{FOLDER}/bundle-manifest.json"
        manifest = read(SITE / manifest_name)
        self.assertEqual(manifest["source_commit"], self.info["source_commit"])
        self.assertEqual(manifest["version"], VERSION)
        self.assertEqual(manifest["source_inputs_sha256"], self.data["source_inputs_sha256"])
        self.assertEqual(set(manifest["files_sha256"]), ASSETS)
        with zipfile.ZipFile(SITE / self.meta["bundle"]) as archive:
            members = set(archive.namelist())
            self.assertEqual(members, ASSETS | {manifest_name, "index.html"})
            self.assertEqual(len(archive.namelist()), 9)
            self.assertEqual(archive.read(manifest_name), (SITE / manifest_name).read_bytes())
            for path, expected in manifest["files_sha256"].items():
                content = archive.read(path)
                self.assertEqual(sha(content), expected, path)
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

    def test_previous_page_entry_is_reversible_and_older_assets_unchanged(self):
        preserved = self.meta["preservation"]
        self.assertEqual(read(SITE / self.meta["manifest"])["preservation"], preserved)
        self.assertEqual(preserved["previous_page"], "prosperity-city-common.html")
        self.assertEqual(preserved["entry_id"], "p471-entry")
        page = (SITE / preserved["previous_page"]).read_bytes()
        entry = preserved["entry_html"].encode("utf-8")
        self.assertEqual(page.count(entry), 1)
        self.assertEqual(page.count(b'id="p471-entry"'), 1)
        self.assertEqual(sha(page.replace(entry, b"")), preserved["previous_page_sha256"])
        protected = preserved["protected_files_sha256"]
        common = self.info["prosperity_city_common_p470"]
        self.assertTrue(set(common["download_files"]) | {"common-470/study.css", "common-470/common-ui.js"} <= set(protected))
        self.assertTrue(set(common["preservation"]["protected_files_sha256"]) <= set(protected))
        self.assertEqual(len([path for path in protected if path.endswith(".webp")]), 4)
        self.assertIn("prosperity-backbone-p469.html", protected)
        for path, expected in protected.items():
            self.assertEqual(sha((SITE / path).read_bytes()), expected, path)
            self.assertEqual(self.info["files_sha256"][path], expected, path)


if __name__ == "__main__":
    unittest.main()
