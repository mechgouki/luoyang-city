"""P4.6: bounded geo-evidence integrity for rivers, lakes and primary street reports."""
from pathlib import Path
import hashlib
import json
import re
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site";OUT=SITE/"prosperity-hydro-roads"
SOURCE=ROOT/"research/prosperity-v4/hydro-roads-anchor-p46.json"
NS="{http://www.w3.org/2000/svg}"
VERSION="prosperity-hydro-roads-anchor-p46"
def read(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class P46AnchorAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=read(SOURCE)
        cls.d=read(OUT/"data.json")
        cls.geo=read(ROOT/"research/prosperity-v1/geographic-evidence.json")
        cls.p452=read(ROOT/"research/prosperity-v4/road-functions-p452.json")
        cls.info=read(SITE/"build-info.json")
        cls.release=read(SITE/"release.json")
        cls.html=(SITE/"prosperity-hydro-roads.html").read_text(encoding="utf-8")
        cls.proof=read(OUT/"preservation.json")

    def test_report_counts_and_no_manufactured_ancient_water_polygons(self):
        self.assertEqual(self.d["version"],VERSION)
        self.assertEqual(self.d["water_features"],self.raw["water_features"])
        self.assertEqual(self.d["main_road_records"],self.raw["main_road_records"])
        self.assertEqual(len(self.d["source_registry"]),17)
        self.assertEqual(len(self.d["water_features"]),34)
        self.assertEqual(len(self.d["main_road_records"]),21)
        self.assertEqual(self.d["coordinates_added"],0)
        self.assertEqual(self.d["verified_new_ancient_common_ground_controls"],0)
        self.assertEqual(self.d["historic_waterbody_polygons_added"],0)
        self.assertEqual(self.d["historic_full_road_polylines_added"],0)
        self.assertFalse(self.d["approved_artistic_panorama_changed"])
        self.assertTrue(all(not r["ancient_geographic_line_or_polygon_verified"] for r in self.d["water_features"]))
        self.assertTrue(all(r["independent_ground_controls"]==0 for r in self.d["water_features"]))
        self.assertTrue(all(not r["ancient_full_route_georegistered"] for r in self.d["main_road_records"]))
        self.assertTrue(all(r["new_route_polyline"] is None for r in self.d["main_road_records"]))

    def test_modern_source_map_not_northern_wei_and_lakes_not_merged(self):
        water={w["id"]:w for w in self.d["water_features"]}
        modern=[w for w in water.values() if w["registered_source_feature_id"]]
        self.assertEqual(len(modern),1)
        self.assertEqual(modern[0]["id"],"W02")
        self.assertEqual(modern[0]["registered_source_feature_id"],"geo-modern-luo-river")
        geo={f["id"]:f for f in self.geo["features"]}
        self.assertEqual(geo["geo-modern-luo-river"]["layer"],"modern_geographic_reference")
        self.assertEqual(geo["geo-modern-luo-river"]["geometry"]["type"],"LineString")
        self.assertEqual(self.geo["crs"],"EPSG:4610")
        self.assertEqual(len(geo),30)
        self.assertEqual(water["W15"]["existing_entity_id"],"ic_diquan")
        self.assertEqual(water["W16"]["existing_entity_id"],"ic_tianyuan")
        self.assertNotEqual(water["W15"]["existing_entity_id"],water["W16"]["existing_entity_id"])
        self.assertEqual(water["W20"]["existing_entity_id"],"ic_mengfan_pool")
        self.assertIn("冬涸",water["W20"]["relative_topology_note"])
        self.assertEqual(water["W09"]["position_tier"],"phase_conditional_topology")
        self.assertEqual(water["W13"]["period"],"Han_Jin_older_strata")
        self.assertEqual(water["W14"]["period"],"Wei_Jin")

    def test_eight_prior_source_features_and_nine_distinct_outer_survey_mentions(self):
        roads=self.d["main_road_records"]
        assert len(self.p452["road_segments"])==8
        for i,p in enumerate(self.p452["road_segments"]):
            self.assertEqual(roads[i]["id"],f"R{i+1:02d}")
            self.assertEqual(roads[i]["registered_source_feature_id"],p["feature_id"])
            self.assertEqual(roads[i]["linked_prior_road_id"],"P452:"+p["id"])
            self.assertEqual(roads[i]["position_tier"],"preserved_source_map_geometry")
        self.assertEqual([x["id"] for x in roads[8:19]],[f"O{i:02d}" for i in range(1,12)])
        self.assertTrue(all(x["registered_source_feature_id"] is None for x in roads[8:19]))
        self.assertEqual([r["id"] for r in roads[-2:]],["X01","X02"])
        self.assertEqual(roads[-2]["sourced_metrics"]["width_approx_m"],34)
        self.assertEqual(roads[-2]["sourced_metrics"]["length_approx_m"],2500)
        self.assertEqual(roads[-1]["sourced_metrics"]["neighborhood_gate_gap_approx_m"],7.5)
        self.assertEqual(roads[-2]["linked_prior_road_id"],"candidate:P451_D03_only_not_confirmed")
        self.assertTrue(all(not r["ancient_full_route_georegistered"] for r in roads))

    def test_parallel_research_consolidated_inner_avenues_local_lanes_and_geology(self):
        self.assertEqual(len(self.d["source_registry"]),17)
        inner=self.d["inner_city_ten_road_literature_summary"]
        self.assertEqual(inner["east_west_count"],5)
        self.assertEqual(inner["north_south_count"],5)
        self.assertEqual(len(inner["east_west"])+len(inner["north_south"]),10)
        self.assertFalse(inner["exact_survey_to_old_eight_matched"])
        for street in inner["east_west"]+inner["north_south"]:
            self.assertIsNone(street["registered_original_survey_polyline"])
            self.assertFalse(street["matching_p1_old_remnant_resolved"])
        local=self.d["baima_local_ward_2024"]
        self.assertEqual(local["excavated_ward_streets_reported"],6)
        self.assertEqual((local["local_ew_street_spacing_m"],local["local_ns_street_spacing_m"]),(40,86))
        self.assertFalse(local["extension_to_whole_outer_city_allowed"])
        self.assertFalse(self.d["ancient_luo_yi_geologic_trend_2024"]["phase_specific_516_528_polyline_verified"])
        self.assertEqual(len(self.d["original_document_acquisition_queue"]),7)
        self.assertTrue(all(not x["scaled_survey_plan_acquired"] for x in self.d["original_document_acquisition_queue"]))
        self.assertTrue(self.d["northern_wei_east_yangqu_phase_controversy"]["not_a_confirmed_complete_field_dated_continuous_channel"])

    def test_diagrams_same_original_unchanged_and_four_page_atlas(self):
        original=SITE/"prosperity/source-layout.svg"
        copied=OUT/"unaltered-source-layout.svg"
        self.assertEqual(sha(original),sha(copied))
        self.assertEqual(sha(copied),self.d["build_reference"]["prior_original_source_map_sha256"])
        self.assertTrue(self.d["build_reference"]["original_map_copied_byte_identically"])
        for name,words in [
            ("hydrology-topology.svg",["翟泉","天渊池","千金堨","现代"]),
            ("roads-evidence.svg",["九条","铜驼","西明","2025"]),
            ("anchor-gates.svg",["34","北魏","现代"])
        ]:
            s=(OUT/name).read_text(encoding="utf-8")
            for word in words:self.assertIn(word,s)
            self.assertEqual(ET.parse(OUT/name).getroot().tag,NS+"svg")
        self.assertEqual(len(PdfReader(SITE/"downloads/prosperity-hydro-roads-p46-atlas.pdf").pages),4)

    def test_unchanged_legacy_and_approved_hero(self):
        self.assertTrue(self.proof["protected_unchanged"])
        for name,digest in self.proof["protected_sha256"].items():
            name = {"index.html": "homepage/history/index-before-r4.html",
                         "v3.0-dual.html": "homepage/history/v3.0-dual-before-v10.html"}.get(name, name)
            self.assertEqual(sha(SITE/name),digest,name)
            self.assertEqual(self.info["files_sha256"][name],digest,name)
        old=OUT/"history/prosperity-street-clusters-before-p46.html"
        self.assertEqual(sha(old),self.proof["prior_html_sha256"])
        after=(SITE/"prosperity-street-clusters.html").read_text(encoding="utf-8")
        self.assertIn('id="p46-first"',after)
        self.assertIn('href="./prosperity-hydro-roads.html"',after)
        self.assertEqual(re.sub(r'<section id="p46-first".*?</section>','',after,count=1,flags=re.S),
                         old.read_text(encoding="utf-8"))
        hero=read(SITE/"homepage/approval-v9.json")["hero"]
        self.assertEqual(hero["revision"],"panorama-approved-v9")
        self.assertEqual(hero["status"],"approved")
        self.assertEqual(hero["source_sha256"],"2a59bf83886d77f7c9226ec7f5d99c94ea6c63c6e207c2e560ee82f80ed93891")

    def test_html_bundle_hashes_and_version(self):
        for value in ("34项河湖","外郭九条","现代洛水","data-mode=\"water\"","data-mode=\"roads\""):
            self.assertIn(value,self.html)
        self.assertEqual(self.html.count('data-row="W'),34)
        self.assertEqual(self.html.count('data-row="R')+self.html.count('data-row="O')+self.html.count('data-row="X'),21)
        manifest=read(OUT/"bundle-manifest.json")
        self.assertEqual(manifest["source_commit"],self.info["source_commit"])
        with zipfile.ZipFile(SITE/"downloads/prosperity-hydro-roads-p46-package.zip") as archive:
            self.assertEqual(set(archive.namelist()),set(manifest["files_sha256"])|{"prosperity-hydro-roads/bundle-manifest.json"})
            for path,digest in manifest["files_sha256"].items():
                self.assertEqual(hashlib.sha256(archive.read(path)).hexdigest(),digest)
        for file in [SITE/"prosperity-hydro-roads.html",
                     SITE/"downloads/prosperity-hydro-roads-p46-atlas.pdf",
                     SITE/"downloads/prosperity-hydro-roads-p46-package.zip",
                     *OUT.rglob("*")]:
            if file.is_file():
                name=file.relative_to(SITE).as_posix()
                self.assertEqual(sha(file),self.info["files_sha256"][name])
        self.assertEqual(self.info["prosperity_hydro_roads"]["water_feature_records"],34)
        self.assertEqual(self.info["prosperity_hydro_roads"]["road_source_records"],21)
        self.assertEqual(self.info["prosperity_hydro_roads"]["registered_historical_water_polygons"],0)
        self.assertEqual(self.info["prosperity_hydro_roads"]["existing_inner_road_features_preserved"],8)
        self.assertEqual(self.release["prosperity_hydro_roads_version"],VERSION)

if __name__=="__main__":
    unittest.main()
