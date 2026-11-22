"""Regression guards for R7's evidence limits and actual downloadable delivery."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from city_nodes_r7_contract import HOME_EDITS, add_home, restore_home
from city_nodes_r7_data import build_data
from city_nodes_r7_maps import overview, sima_map
from city_nodes_r7_verify import (
    CSV, DATA, KEY, NS, pointer, verify, verify_csv, verify_data, verify_links,
    verify_native_features, verify_protected_files, verify_sima_geometry, verify_source_inputs, verify_water_frame,
)


class CityNodesPreservationBoundary(unittest.TestCase):
    def setUp(self):
        # Only the root Pages control marker is consumed by hosting. A public
        # dotfile or a nested file with the same name must still be requested.
        self.contents = {".nojekyll": b"", "map.svg": b"<svg/>",
                         ".reader-note": b"public note", "downloads/.nojekyll": b"public attachment"}
        self.hashes = {path: hashlib.sha256(raw).hexdigest() for path, raw in self.contents.items()}

    def metadata(self, legacy=False):
        if legacy:
            return dict(protected_files_sha256=dict(self.hashes))
        return dict(protected_files_sha256={p: v for p, v in self.hashes.items() if p != ".nojekyll"},
                    build_control_files_sha256={".nojekyll": self.hashes[".nojekyll"]})

    def public_reader(self, path):
        if path == ".nojekyll":
            raise FileNotFoundError("Pages consumed its root control marker")
        return self.contents[path]

    def test_new_and_legacy_manifests_do_not_request_the_pages_control_marker(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy):
                requests = []
                def read(path):
                    requests.append(path)
                    return self.public_reader(path)
                public, controls = verify_protected_files(self.metadata(legacy), self.hashes, read)
                self.assertEqual(set(requests), set(self.contents) - {".nojekyll"})
                self.assertEqual(set(public), set(requests))
                self.assertEqual(controls, {".nojekyll": self.hashes[".nojekyll"]})

    def test_missing_or_changed_public_assets_still_fail_in_both_manifest_shapes(self):
        for legacy in (False, True):
            for missing in ("map.svg", ".reader-note", "downloads/.nojekyll"):
                with self.subTest(legacy=legacy, path=missing):
                    def read(path):
                        if path == missing:
                            raise FileNotFoundError("404: " + path)
                        return self.public_reader(path)
                    with self.assertRaisesRegex(FileNotFoundError, "404"):
                        verify_protected_files(self.metadata(legacy), self.hashes, read)
                    def changed(path):
                        return b"changed" if path == missing else self.public_reader(path)
                    with self.assertRaises(AssertionError):
                        verify_protected_files(self.metadata(legacy), self.hashes, changed)

    def test_metadata_cannot_hide_an_asset_as_a_control_or_omit_marker_protection(self):
        cases = []
        wrong = self.metadata()
        wrong["build_control_files_sha256"]["map.svg"] = wrong["protected_files_sha256"].pop("map.svg")
        cases.append(wrong)
        wrong = self.metadata()
        wrong["build_control_files_sha256"] = {}
        cases.append(wrong)
        wrong = self.metadata()
        wrong["build_control_files_sha256"][".nojekyll"] = "0" * 64
        cases.append(wrong)
        wrong = self.metadata()
        wrong["protected_files_sha256"][".nojekyll"] = self.hashes[".nojekyll"]
        cases.append(wrong)
        wrong = self.metadata(legacy=True)
        del wrong["protected_files_sha256"][".nojekyll"]
        cases.append(wrong)
        for meta in cases:
            with self.subTest(meta=meta):
                with self.assertRaises(AssertionError):
                    verify_protected_files(meta, self.hashes, self.public_reader)

    def test_local_marker_bytes_are_checked_without_requesting_them_over_http(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy):
                verify_protected_files(self.metadata(legacy), self.hashes, self.public_reader,
                                       build_control_reader=lambda path: self.contents[path])
                with self.assertRaisesRegex(AssertionError, "Build control bytes changed"):
                    verify_protected_files(self.metadata(legacy), self.hashes, self.public_reader,
                                           build_control_reader=lambda path: b"modified marker")


class CityNodesResearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = ROOT / "_site"
        cls.atlas = json.loads((cls.site / "city-atlas/atlas.json").read_bytes())
        cls.data = build_data(cls.site)

    def test_complete_indexes_and_source_joins_keep_previous_values(self):
        result = verify_data(copy.deepcopy(self.data), self.atlas)
        self.assertEqual(result["counts"], dict(nodes=4, findings=32, relations=32, segments=28,
                                                waters=9, entities_indexed=339, roads_indexed=84,
                                                waters_indexed=34))
        self.assertEqual(result["new_historical_coordinates"], 0)
        self.assertGreaterEqual(result["source_inputs"]["resolved_pointers"], 169)

    def test_period_geometry_and_water_values_cannot_be_promoted(self):
        for kind in ("period", "width", "road_geometry", "water_geometry", "registration"):
            with self.subTest(kind=kind):
                changed = copy.deepcopy(self.data)
                rows = {row["id"]: row for row in changed["segments"]}
                if kind == "period":
                    rows["P01"]["period"] = "516—528年均已证实同时通行"
                elif kind == "width":
                    rows["P07"]["reported_metrics"][0]["value"] = 40
                elif kind == "road_geometry":
                    rows["P01"]["geometry_refs"][0]["native_geometry"][0][-1] = [575, 1120]
                elif kind == "water_geometry":
                    changed["waters"][0]["target_bank_geometry"] = [[1, 2], [3, 4]]
                else:
                    changed["source_frames_registered_together"] = True
                with self.assertRaises(AssertionError):
                    verify_data(changed, self.atlas)

    def test_coverage_is_checked_by_identifier_not_claimed_count(self):
        for name in ("entity_index", "road_index", "water_index"):
            with self.subTest(index=name):
                changed = copy.deepcopy(self.data)
                # Keep length unchanged: a count-only check would miss this loss.
                changed[name][-1] = copy.deepcopy(changed[name][0])
                with self.assertRaises(AssertionError):
                    verify_data(changed, self.atlas)

    def test_baima_unknown_distance_and_sima_contemporaneity_remain_explicit(self):
        for nid, field, value in (("baima", "gate_to_central_cross_m", 40),
                                  ("baima", "all_six_roads_proven_contemporary_516_528", True),
                                  ("sima", "all_roads_proven_contemporary_516_528", True),
                                  ("sima", "accepted_new_r4_wall_segments", 1)):
            with self.subTest(node=nid, field=field):
                changed = copy.deepcopy(self.data)
                next(n for n in changed["nodes"] if n["id"] == nid)[field] = value
                with self.assertRaises(AssertionError):
                    verify_data(changed, self.atlas)

    def test_sources_resolve_and_hashes_cannot_silently_drift(self):
        verify_source_inputs(self.data)
        changed = copy.deepcopy(self.data)
        changed["source_inputs_sha256"]["research/prosperity-r5/sima-road.json"] = "0" * 64
        with self.assertRaises(AssertionError):
            verify_source_inputs(changed)
        changed = copy.deepcopy(self.data)
        changed["nodes"][0]["findings"][0]["source_inputs"][0]["pointer"] = "/features/999999"
        with self.assertRaises((AssertionError, IndexError)):
            verify_source_inputs(changed)
        changed = copy.deepcopy(self.data)
        del changed["source_inputs_sha256"]["research/prosperity-r5/sima-road.json"]
        with self.assertRaises(AssertionError):
            verify_source_inputs(changed)

    def test_json_pointer_preserves_escaped_keys_and_rejects_negative_indices(self):
        obj = {"a/b": {"~": ["first", "last"]}, "": 42}
        self.assertEqual(pointer(obj, "/a~1b/~0/1"), "last")
        self.assertEqual(pointer(obj, "/"), 42)
        self.assertIs(pointer(obj, ""), obj)
        with self.assertRaises(AssertionError):
            pointer(obj, "/a~1b/~0/-1")

    def test_sima_six_atomic_lines_and_blue_range_box_keep_native_values(self):
        svg = sima_map(self.atlas, self.data)
        self.assertEqual(verify_sima_geometry(svg)["sima_native_line_parts"], 6)
        changed = copy.deepcopy(svg)
        line = next(e for e in changed.iter() if e.get("data-sima-atomic-line") == "0")
        line.set("d", "M573 900 L575 1120")
        with self.assertRaises(AssertionError):
            verify_sima_geometry(changed)
        changed = copy.deepcopy(svg)
        frame = next(e for e in changed.iter() if e.get("data-frame") == "frame-sima2023")
        # Delete one trace while leaving all prose and reported counts untouched.
        anchor = next(e for e in frame if e.tag == NS + "a")
        anchor.remove(next(e for e in anchor if e.get("data-sima-atomic-line") == "5"))
        with self.assertRaises(AssertionError):
            verify_sima_geometry(changed)
        changed = copy.deepcopy(svg)
        region = next(e for e in changed.iter() if e.get("data-role") == "source-region-box-not-wall")
        region.attrib.pop("stroke-dasharray")
        with self.assertRaises(AssertionError):
            verify_sima_geometry(changed)

    def test_overview_does_not_shift_original_road_ink_or_water_symbols(self):
        svg = overview(self.atlas, self.data)
        self.assertGreater(verify_native_features(svg, "overview"), 20)
        self.assertEqual(verify_water_frame(svg), 12)
        changed = copy.deepcopy(svg)
        road = next(e for e in changed.iter() if e.get("data-native-geometry") == "geo-tongtuo-avenue")
        road.set("d", road.get("d").replace("314.108795", "315.108795"))
        with self.assertRaises(AssertionError):
            verify_native_features(changed, "overview")
        changed = copy.deepcopy(svg)
        water = next(e for e in changed.iter() if e.get("data-water-ref"))
        water.set("data-source-pointer", "/traces/99")
        with self.assertRaises(AssertionError):
            verify_water_frame(changed)


class CityNodesDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = ROOT / "_site"

    def test_release_downloads_protected_files_and_offline_bundle(self):
        info = json.loads((self.site / "build-info.json").read_bytes())
        read = lambda path: (self.site / path).read_bytes()
        result = verify(info, read, build_control_reader=read)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["build_control_files"], 1)
        self.assertTrue(result["build_control_content_verified"])
        self.assertEqual(result["downloads"], 9)
        self.assertEqual(result["homepage"]["revision"], "panorama-approved-v12")
        self.assertEqual(result["homepage"]["full_size"], [1672, 941])
        self.assertEqual(result["figures"]["sima"]["sima_native_line_parts"], 6)

    def test_csv_rejects_lossy_road_endpoints_and_measurements(self):
        data = json.loads((self.site / DATA).read_bytes())
        raw = (self.site / CSV).read_bytes()
        self.assertEqual(verify_csv(raw, data), 28)
        for field in ("period", "reported_metrics", "geometry_refs", "source_inputs"):
            with self.subTest(field=field):
                reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
                rows, fields = list(reader), reader.fieldnames
                row = next(r for r in rows if r["id"] == "P01")
                row[field] = "[]" if field != "period" else "516—528已证实"
                stream = io.StringIO()
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
                with self.assertRaises(AssertionError):
                    verify_csv(stream.getvalue().encode(), data)

    def test_manifest_cannot_hide_a_changed_download(self):
        info = json.loads((self.site / "build-info.json").read_bytes())
        def altered(path):
            raw = (self.site / path).read_bytes()
            return raw + b"\ncorrupt" if path == CSV else raw
        with self.assertRaises(AssertionError):
            verify(info, altered)

    def test_homepage_insertions_are_exactly_reversible(self):
        info = json.loads((self.site / "build-info.json").read_bytes())
        for path, entry in info[KEY]["predecessor_homepage"].items():
            original = (self.site / entry["archive"]).read_bytes()
            from panorama_v13_contract import restore_home as restore_candidate_entry
            actual = restore_candidate_entry((self.site / path).read_bytes())
            self.assertEqual(add_home(original), actual)
            self.assertEqual(restore_home(actual), original)
            self.assertEqual(add_home(actual), actual)
            broken = actual.replace(HOME_EDITS[0][1], b"<figcaption>changed</figcaption>", 1)
            self.assertNotEqual(restore_home(broken), original)

    def test_resource_closure_includes_picture_srcset_and_nested_downloads(self):
        markup = b'<p id="target"></p><a href="#target">x</a><picture><source srcset="./a.webp 600w, ./b.webp 1200w"><img src="./a.webp"></picture>'
        verify_links(markup, {"a.webp", "b.webp"})
        with self.assertRaises(AssertionError):
            verify_links(markup, {"a.webp"})
        with self.assertRaises(AssertionError):
            verify_links(b'<a href="#missing">x</a>', set())


if __name__ == "__main__":
    unittest.main()
