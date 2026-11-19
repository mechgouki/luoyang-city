"""Jianchun's local plan must not become an unsupported city-map footprint."""
import hashlib
import json
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/prosperity-v4/backbone-469"
SITE = ROOT / "_site"
NS = "{http://www.w3.org/2000/svg}"


class JianchunSourceAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = json.loads((SOURCE / "jianchun-plan-audit.json").read_text())

    def test_republished_plan_is_not_promoted_to_original_or_ground_control(self):
        state = self.audit["read_status"]
        self.assertTrue(state["qian2018_figure2_derivative_visually_read"])
        self.assertFalse(state["original_1988_full_journal_pages_read"])
        self.assertFalse(state["original_1988_full_metric_plan_read"])
        self.assertFalse(state["p44_archive_modified"])
        self.assertTrue(state["same_feature_association"])
        self.assertEqual(state["accepted_control_pairs"], [])
        self.assertIsNone(state["geographic_transform"])
        self.assertFalse(state["georegistration_completed"])
        self.assertEqual(len(self.audit["candidate_control_pairs"]), 5)
        self.assertTrue(all(not row["accepted"] for row in self.audit["candidate_control_pairs"]))
        account = self.audit["research_accounting"]
        for key in ("new_ancient_absolute_coordinates", "new_metric_measurements",
                    "new_geographic_building_footprints", "new_geographic_bridge_positions",
                    "new_geographic_water_lines"):
            self.assertEqual(account[key], 0, key)

    def test_reported_residual_dimensions_and_inferred_count_remain_distinct(self):
        rows = {row["id"]: row for row in self.audit["reported_quantities"]}
        self.assertEqual(rows["JQ01"]["value"], 30)
        self.assertEqual(rows["JQ02"]["value"], 12.5)
        self.assertEqual(rows["JQ03"]["value"], 8)
        self.assertEqual(rows["JQ03"]["evidence_kind"], "source_reported_surviving_width")
        self.assertEqual(rows["JQ04"]["value_each"], 6)
        self.assertEqual(rows["JQ05"]["range"], [4, 5])
        self.assertEqual(rows["JQ06"]["reported_surviving_count"], 6)
        self.assertEqual(rows["JQ06"]["author_inferred_original_count"], 8)
        self.assertEqual(rows["JQ06"]["unit"], "count")
        self.assertTrue(all(not row["new_measurement"] for row in rows.values()))
        dates = self.audit["excavation_date_discrepancy"]
        self.assertIsNone(dates["selected_date"])
        self.assertEqual({row["reported_year"] for row in dates["records"]}, {1985, 1986})

    def test_five_archived_inputs_still_match_the_reviewed_source_bytes(self):
        self.assertEqual(len(self.audit["frozen_inputs"]), 5)
        for row in self.audit["frozen_inputs"]:
            self.assertEqual(hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(), row["sha256"])
        p44 = json.loads((ROOT / "research/prosperity-v4/architecture-types-p44.json").read_text())
        gate = next(row for row in p44["types"] if row["id"] == "inner_city_gate")
        self.assertFalse(gate["original_metric_plan_read"])

    def test_context_crop_keeps_exact_source_vertices_and_symbol_center(self):
        drawing = ET.parse(SITE / "backbone-469/jianchun-source-context.svg").getroot()
        geo = json.loads((ROOT / "research/prosperity-v1/geographic-evidence.json").read_text())
        features = {row["id"]: row for row in geo["features"]}
        source_paths = [p for p in drawing.iter(NS + "path") if p.get("data_source_feature_id") or p.get("data-source-feature-id")]
        self.assertGreater(len(source_paths), 2)
        for path in source_paths:
            source = features[path.get("data-source-feature-id")]["source_pdf_geometry"]
            parts = source["coordinates"] if source["type"] == "MultiLineString" else [source["coordinates"]]
            points = parts[int(path.get("data-part")) - 1]
            observed = [float(value) for value in path.get("d").replace("M", " ").replace("L", " ").split()]
            self.assertEqual(observed, [value for point in points for value in point])
        mark = next(p for p in drawing.iter(NS + "circle") if p.get("data-source-feature-id") == "geo-jianchun-gate")
        self.assertEqual([float(mark.get("cx")), float(mark.get("cy"))],
                         features["geo-jianchun-gate"]["source_pdf_geometry"]["coordinates"])
        self.assertEqual(mark.get("data-semantics"), "source-symbol-center-not-ground-control")

    def test_structure_is_unscaled_and_does_not_trace_or_republish_source_image(self):
        drawing = ET.parse(SITE / "backbone-469/jianchun-structure-reading.svg").getroot()
        metadata = json.loads(drawing.find(NS + "metadata").text)
        self.assertFalse(metadata["metric_geometry"])
        self.assertIsNone(metadata["geographic_transform"])
        self.assertEqual(len(list(drawing.iter(NS + "image"))), 0)
        words = " ".join(drawing.itertext())
        for expected in ("不按比例", "残宽", "汉晋", "尚未核实"):
            self.assertIn(expected, words)
        page = (SITE / "prosperity-backbone-p469.html").read_text()
        self.assertIn('id="jianchun-plan-audit"', page)
        self.assertIn("1988原刊整页：待得", page)
        self.assertIn("可复认共同控制：0组", page)
        self.assertNotIn("98357df099984848b60a9c704da175dd.jpeg\"", page)
        published = SITE / "backbone-469/jianchun-plan-audit.json"
        self.assertEqual(published.read_bytes(), (SOURCE / published.name).read_bytes())


if __name__ == "__main__":
    unittest.main()
