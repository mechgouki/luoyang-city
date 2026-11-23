"""Independent evidence and downloadable-delivery checks for the R9 spatial atlas.

The checks use the published files and pre-existing reviewed node sources. They
protect source identity, uncertainty boundaries and the offline evidence chain.
"""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys
import unittest
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from city_nodes_r7_verify import pointer, verify_native_features, _path_points
from homepage_artwork_v10 import V12
from city_spatial_r9_verify import verify as verify_live_spatial, verify_csv, verify_data, verify_page

KEY = "city_spatial_r9"
FOLDER = "city-spatial-r9"
DATA = FOLDER + "/decisions.json"
NODE_IDS = {"palace-yongning", "baima", "sima", "jianchun"}
NS = "{http://www.w3.org/2000/svg}"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class SpatialEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = ROOT / "_site"
        cls.data = json.loads((cls.site / DATA).read_bytes())
        cls.info = json.loads((cls.site / "build-info.json").read_bytes())
        cls.meta = cls.info[KEY]
        cls.prior = {nid: json.loads((ROOT / ("research/city-nodes-r7/reviews/" + nid + ".json")).read_bytes())
                     for nid in NODE_IDS}

    def test_research_boundaries_are_explicit_and_predecessor_findings_resolve(self):
        data = self.data
        self.assertEqual(data["research_version"], "R9.1")
        self.assertEqual(data["source_commit"], self.info["source_commit"])
        self.assertEqual(self.meta["source_commit"], self.info["source_commit"])
        self.assertEqual(data["target_years"], [516, 528])
        self.assertEqual(data["new_historical_coordinates"], 0)
        self.assertEqual(data["new_shoreline_geometries"], 0)
        self.assertIs(data["source_frames_registered_together"], False)
        self.assertEqual({node["id"] for node in data["nodes"]}, NODE_IDS)
        rows = data["decisions"]
        identifiers = [row["id"] for row in rows]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(len(rows), 20)
        self.assertEqual({row["node_id"] for row in rows}, NODE_IDS)
        all_classes = set()
        for row in rows:
            with self.subTest(decision=row["id"]):
                self.assertTrue(row["evidence_classes"])
                self.assertLessEqual(set(row["evidence_classes"]), {"source", "relation", "unknown"})
                all_classes.update(row["evidence_classes"])
                for field in ("previous_expression", "judgment", "map_change", "remaining_unknown"):
                    self.assertIsInstance(row[field], str)
                    self.assertTrue(row[field].strip(), field)
                previous = {finding["id"] for finding in self.prior[row["node_id"]]["findings"]}
                self.assertTrue(row["prior_finding_ids"])
                self.assertLessEqual(set(row["prior_finding_ids"]), previous)
                self.assertTrue(row["evidence"])
                for evidence in row["evidence"]:
                    for field in ("source_id", "title", "url", "locator", "excerpt_or_summary", "quote_kind"):
                        self.assertTrue(evidence[field], (row["id"], field))
                    self.assertIn(urlsplit(evidence["url"]).scheme, {"http", "https"})
        self.assertEqual(all_classes, {"source", "relation", "unknown"})

    def test_evidence_inputs_are_fingerprinted_and_each_pointer_is_real(self):
        fingerprints = self.data["source_inputs_sha256"]
        self.assertTrue(fingerprints)
        cache = {}
        for path, checksum in fingerprints.items():
            source = (ROOT / path).resolve()
            self.assertTrue(source.is_relative_to(ROOT), path)
            raw = source.read_bytes()
            self.assertEqual(digest(raw), checksum, path)
            if source.suffix == ".json":
                cache[path] = json.loads(raw)
        count = 0
        for decision in self.data["decisions"]:
            self.assertTrue(decision["source_inputs"], decision["id"])
            for reference in decision["source_inputs"]:
                source_path = reference.get("source_path") or reference.get("path") or reference.get("file")
                location = reference.get("json_pointer", reference.get("pointer"))
                self.assertIn(source_path, fingerprints)
                self.assertIsNotNone(location, reference)
                actual = pointer(cache[source_path], location)
                # A resolved null is valid evidence for an explicitly unknown value.
                if "native_geometry" in reference:
                    self.assertEqual(reference["native_geometry"], actual)
                if "city_registration" in reference:
                    self.assertIs(reference["city_registration"], False)
                count += 1
        self.assertGreaterEqual(count, len(self.data["decisions"]))

    def test_each_map_target_reaches_a_published_decision(self):
        svg_paths = [p for p in self.meta["download_files"] if p.endswith(".svg")]
        self.assertEqual(len(svg_paths), 1)
        root = ET.fromstring((self.site / svg_paths[0]).read_bytes())
        self.assertEqual(root.tag, NS + "svg")
        self.assertTrue(root.get("viewBox"))
        self.assertTrue(list(root.iter(NS + "title")), "Downloadable figure lacks an accessible title")
        targets = {}
        for element in root.iter():
            if element.get("data-decision"):
                identifier = element.get("data-decision")
                href = element.get("href") or element.get("{http://www.w3.org/1999/xlink}href")
                if href:
                    self.assertEqual(urlsplit(href).fragment, "decision-" + identifier)
                    targets[identifier] = href
        self.assertEqual(set(targets), {row["id"] for row in self.data["decisions"]})
        all_ids = [e.get("id") for e in root.iter() if e.get("id")]
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_native_06a_and_sima_ink_remains_in_its_own_source_coordinates(self):
        svg_path = next(p for p in self.meta["download_files"] if p.endswith(".svg"))
        root = ET.fromstring((self.site / svg_path).read_bytes())
        self.assertGreater(verify_native_features(root, "overview"), 20)
        self.assertEqual(root.get("data-source-frames-registered-together"), "false")
        frames = [e for e in root.iter() if e.get("data-frame") == "sima2023-independent"]
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].get("data-city-registration"), "false")
        source = json.loads((ROOT / "research/prosperity-r5/sima-road.json").read_bytes())["image"]
        lines = [e for e in frames[0].iter() if e.get("data-sima-atomic-line") is not None]
        self.assertEqual([line.get("data-sima-atomic-line") for line in lines], [str(i) for i in range(6)])
        self.assertEqual([_path_points(line) for line in lines], source["sima_road_ink_px"])
        boxes = [e for e in frames[0].iter() if e.get("data-role") == "source-region-box-not-wall"]
        self.assertEqual(len(boxes), 1)
        region = boxes[0]
        self.assertTrue(region.get("stroke-dasharray"))
        self.assertEqual([float(region.get("x")), float(region.get("y")),
                          float(region.get("x")) + float(region.get("width")),
                          float(region.get("y")) + float(region.get("height"))],
                         source["storage_box_centerline_px"])
        changed = copy.deepcopy(root)
        line = next(e for e in changed.iter() if e.get("data-native-geometry") == "geo-tongtuo-avenue")
        line.set("d", line.get("d").replace("314.108795", "315.108795"))
        with self.assertRaises(AssertionError):
            verify_native_features(changed, "overview")

    def test_csv_retains_every_decision_and_its_evidence(self):
        csv_paths = [p for p in self.meta["download_files"] if p.endswith(".csv")]
        self.assertEqual(len(csv_paths), 1)
        raw = (self.site / csv_paths[0]).read_bytes()
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        expected = {r["id"]: r for r in self.data["decisions"]}
        self.assertEqual([r["id"] for r in rows], list(expected))
        for row in rows:
            original = expected[row["id"]]
            for field in ("node_id", "previous_expression", "judgment", "map_change", "remaining_unknown"):
                self.assertEqual(row[field], original[field], (row["id"], field))
            for field in ("evidence_classes", "evidence", "prior_finding_ids", "source_inputs"):
                self.assertEqual(json.loads(row[field]), original[field], (row["id"], field))

    def test_resources_are_exact_and_protected_previous_evidence_is_unchanged(self):
        hashes = self.info["files_sha256"]
        for path in self.meta["download_files"]:
            self.assertEqual(digest((self.site / path).read_bytes()), hashes[path], path)
        protected = self.meta["protected_files_sha256"]
        required = {"city-nodes/readings.json", "city-nodes/segments.csv", "luoyang-city-nodes.html",
                    "all-roads/records.json", V12.full, V12.small, V12.metadata}
        self.assertLessEqual(required, set(protected))
        for path, checksum in protected.items():
            self.assertEqual(digest((self.site / path).read_bytes()), checksum, path)
            self.assertEqual(hashes[path], checksum, path)
        bundle = self.meta["bundle"]
        with ZipFile(self.site / bundle) as archive:
            names = archive.namelist()
            self.assertEqual(len(names), len(set(names)), "Duplicate archive members")
            for name in names:
                path = PurePosixPath(name)
                self.assertFalse(path.is_absolute(), name)
                self.assertNotIn("..", path.parts)
            self.assertIn(self.meta.get("offline_entry", "index.html"), names)
            self.assertIn(DATA, names)
            self.assertEqual(archive.read(DATA), (self.site / DATA).read_bytes())


class SpatialLiveContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = ROOT / "_site"
        cls.info = json.loads((cls.site / "build-info.json").read_bytes())
        cls.meta = cls.info[KEY]
        cls.data = json.loads((cls.site / DATA).read_bytes())
        cls.atlas = json.loads((cls.site / "city-atlas/atlas.json").read_bytes())
        cls.previous = json.loads((cls.site / "city-nodes/readings.json").read_bytes())

    def test_live_reader_is_used_for_every_public_resource_and_control_is_not_requested(self):
        requested = []
        def read(path):
            requested.append(path)
            self.assertNotEqual(path, ".nojekyll")
            return (self.site / path).read_bytes()
        report = verify_live_spatial(self.info, read)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["research"]["counts"]["decisions"], 20)
        self.assertGreaterEqual(report["research"]["resolved_pointers"], 100)
        self.assertGreater(report["research"]["classical_quotes"], 0)
        self.assertGreater(report["research"]["prior_review_summaries"], 0)
        self.assertLessEqual({DATA, "city-spatial-r9/decisions.csv", "city-spatial-r9/overview.svg",
                             "luoyang-city-spatial.html", self.meta["bundle"], "city-atlas/atlas.json",
                             "city-nodes/readings.json"}, set(requested))

    def test_semantic_checks_reject_promoted_summary_registration_and_lost_csv_fields(self):
        for kind in ("quote", "registration", "pointer", "interpretation"):
            with self.subTest(kind=kind):
                changed = copy.deepcopy(self.data)
                if kind == "quote":
                    item = next(e for row in changed["decisions"] for e in row["evidence"]
                                if e["quote_kind"] == "prior_review_summary")
                    item["quote_kind"] = "classical_text_quote"
                elif kind == "registration":
                    changed["source_frames_registered_together"] = True
                elif kind == "pointer":
                    changed["decisions"][0]["source_inputs"][0]["pointer"] = "/findings/-1"
                else:
                    changed["decisions"][0]["remaining_unknown"] = "全部位置和尺度已确认"
                with self.assertRaises(AssertionError):
                    verify_data(changed, self.meta, self.info, self.atlas, self.previous)
        raw = (self.site / "city-spatial-r9/decisions.csv").read_bytes()
        source = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        rows, fields = list(source), source.fieldnames
        rows[0]["source_inputs"] = "[]"
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        with self.assertRaises(AssertionError):
            verify_csv(b"\xef\xbb\xbf" + stream.getvalue().encode(), self.data)

    def test_html_cannot_present_a_reused_summary_as_a_primary_quotation(self):
        raw = (self.site / "luoyang-city-spatial.html").read_bytes()
        changed, count = re.subn(r"<details><summary>查看既有核验摘要</summary><p>(.*?)</p></details>".encode(),
                                rb"<blockquote>\1</blockquote>", raw, count=1, flags=re.DOTALL)
        self.assertEqual(count, 1)
        with self.assertRaises(AssertionError):
            verify_page(changed, self.data, self.info["files_sha256"])

    def test_a_new_outer_zip_checksum_cannot_hide_changed_inner_evidence(self):
        from city_layout_r10_contract import restore_r9_context
        from zipfile import ZIP_DEFLATED
        contents = io.BytesIO()
        with ZipFile(self.site / self.meta["bundle"]) as original, ZipFile(contents, "w", ZIP_DEFLATED) as changed:
            for name in original.namelist():
                raw = original.read(name)
                changed.writestr(name, raw + b"\n" if name == DATA else raw)
        corrupted = contents.getvalue()
        info = copy.deepcopy(self.info)
        info["files_sha256"][self.meta["bundle"]] = digest(corrupted)
        def read(path):
            return corrupted if path == self.meta["bundle"] else (self.site / path).read_bytes()

        # Later publication layers may reject the changed predecessor inventory
        # before the R9 verifier reaches the contents of the offline bundle.
        with self.subTest(context="complete publication"), self.assertRaises(AssertionError):
            verify_live_spatial(info, read)

        # Validate and restore the genuine predecessor before injecting the same
        # corruption, so R9's own inner-evidence check is exercised independently.
        restored, read_r9 = restore_r9_context(self.info, lambda path: (self.site / path).read_bytes())
        for key in ("panorama_review_v14", "city_plan_r11", "city_layout_r10"):
            self.assertNotIn(key, restored)
        self.assertEqual(verify_live_spatial(restored, read_r9)["status"], "passed")
        info_r9 = copy.deepcopy(restored)
        info_r9["files_sha256"][self.meta["bundle"]] = digest(corrupted)

        def read_corrupted_r9(path):
            return corrupted if path == self.meta["bundle"] else read_r9(path)

        with self.subTest(context="verified R9 view"), self.assertRaisesRegex(
                AssertionError, "Offline evidence differs") as failure:
            verify_live_spatial(info_r9, read_corrupted_r9)
        self.assertEqual(failure.exception.args[0], (DATA, "Offline evidence differs"))


if __name__ == "__main__":
    unittest.main()
