"""End-to-end consistency of the unified map and the two joined registers."""
import io
import json
from pathlib import Path
import sys
import unittest

from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from city_atlas_r4_data import build_data, index
from verify_city_atlas_r4 import verify


class UnifiedAtlas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site=ROOT/"_site"
        cls.data=json.loads((cls.site/"city-atlas/atlas.json").read_bytes())
        cls.info=json.loads((cls.site/"build-info.json").read_bytes())

    def test_public_contract_and_predecessor_preservation(self):
        report=verify(self.info,lambda p:(self.site/p).read_bytes())
        self.assertEqual(report["coverage_rows"],339)
        self.assertEqual(report["preservation"]["p472_offline_members"],9)

    def test_full_rebuild_and_identity_checks(self):
        self.assertEqual(build_data(self.site),self.data)
        es=index(self.data["entities"]); readings=index(self.data["records"],"key")
        for e in es.values():
            for k in e["evidence"]:
                self.assertIn(e["id"],readings[k]["affected_entity_ids"])
            ref=e["location_reading_ref"]
            if ref and ref!="catalog":
                self.assertIn(e["id"],readings[ref]["affected_entity_ids"])
            self.assertTrue(e["next_evidence"])
        self.assertEqual(es["gate_changhe_west"]["level"],"relative")
        self.assertEqual(es["ic_changhe_palace"]["level"],"source")
        self.assertEqual(es["ic_liuteng_house"]["level"],"unlocated")
        self.assertEqual(es["v2_baoming"]["temporal_state"],"attested_by_528")
        self.assertEqual(es["v2_baoming"]["period"],"conditional")
        self.assertIsNone(next(f for f in self.data["features"] if f["id"]=="geo-taiji-hall-reference").get("entity_id"))

    def test_unequal_frames_and_coverage_membership(self):
        es=index(self.data["entities"])
        self.assertEqual(len(self.data["calibration"]["pixel_control_points"]),16)
        self.assertTrue(all(not f["approximation"]["is_field_verified_gcp"] for f in self.data["features"]))
        for region in self.data["regions"][:-1]:
            code=region["region"]
            expected={e["id"] for e in es.values() if code in set(e["focus_regions"]+e["evidence_regions"])}
            self.assertEqual(set(region["entity_ids"]),expected)
        leftover={e["id"] for e in es.values() if not (e["focus_regions"] or e["evidence_regions"])}
        self.assertEqual(set(self.data["regions"][-1]["entity_ids"]),leftover)

    def test_atlas_pdf_has_three_vector_pages(self):
        pdf=PdfReader(io.BytesIO((self.site/"downloads/city-atlas.pdf").read_bytes()))
        self.assertEqual(len(pdf.pages),3)
        self.assertIn("城市分布总图",pdf.metadata.title)
        for page in pdf.pages:
            self.assertGreater(len(page.get_contents().get_data()),2000)
            self.assertIn("/Font",page["/Resources"])
