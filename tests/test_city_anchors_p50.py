"""P5.0 priority: water, channel and trunk-road anchor evidence without fabricated ancient GIS."""
from pathlib import Path
import hashlib
import json
import re
import unittest
import zipfile
import xml.etree.ElementTree as ET
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
OUT=SITE/"city-anchors"
VERSION="city-anchors-hydro-roads-p50"
NS="{http://www.w3.org/2000/svg}"

def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class P50CityAnchors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=read(OUT/"data.json")
        cls.src=read(ROOT/"research/prosperity-v5/hydro-road-anchors-p50.json")
        cls.geo=read(ROOT/"research/prosperity-v1/geographic-evidence.json")
        cls.entities={x["id"]:x for x in read(ROOT/"data/entities.json")}
        cls.info=read(SITE/"build-info.json")
        cls.release=read(SITE/"release.json")
        cls.html=(SITE/"city-anchors.html").read_text(encoding="utf-8")
        cls.preservation=read(OUT/"preservation.json")

    def test_source_audit_does_not_claim_ancient_waterline_registered(self):
        self.assertEqual(self.d["version"],VERSION)
        self.assertEqual(self.d["completion_status"],"evidence_inventory_and_hypothesis_topology_not_verified_complete_geographic_city_skeleton")
        self.assertEqual(len(self.geo["features"]),30)
        self.assertEqual(self.geo["crs"],"EPSG:4610")
        modern=[f for f in self.geo["features"] if f["layer"]=="modern_geographic_reference"]
        self.assertEqual(len(modern),1)
        self.assertEqual(modern[0]["id"],"geo-modern-luo-river")
        self.assertEqual(modern[0]["source_historical_period"],"1997年航摄、1999年实测底图")
        self.assertEqual(modern[0]["geometry"]["type"],"LineString")
        self.assertEqual(self.d["evidence_policy"]["new_ancient_geographic_coordinates"],0)
        self.assertEqual(self.d["evidence_policy"]["ancient_coordinate_controls_approved"],0)
        self.assertTrue(self.d["evidence_policy"]["modern_luo_cannot_be_ancient"])
        self.assertEqual(self.d["evidence_policy"]["exact_ancient_river_lines_registered"],0)
        self.assertEqual(self.d["evidence_policy"]["complete_major_roads_registered"],0)
        self.assertEqual(self.d["evidence_policy"]["homepage_approved_version"],"panorama-approved-v9")
        self.assertTrue(self.d["evidence_policy"]["homepage_modification_forbidden"])

    def test_water_compartments_and_named_lakes_are_distinct(self):
        waters=self.d["water_components"]
        self.assertEqual(len(waters),15)
        self.assertEqual({x["id"] for x in waters},{f"W{i:02d}" for i in range(1,16)})
        for item in waters:
            self.assertIsNone(item["ancient_516_528_metric_geometry"])
            self.assertEqual(item["shared_geodetic_control_count"],0)
            self.assertTrue(item["source_ids"])
            if item["old_entity_id"]:
                self.assertIn(item["old_entity_id"],self.entities)
        actual=self.d["historical_waterbody_entity_ids"]
        self.assertEqual(len(actual),11)
        self.assertEqual(len(set(actual)),11)
        self.assertEqual(len(self.d["waterbody_entity_evidence"]),11)
        for item in self.d["waterbody_entity_evidence"]:
            original=self.entities[item["id"]]
            self.assertEqual(item["name"],original["name"])
            self.assertEqual(item["type"],original["type"])
            self.assertEqual(item["original_quote"],original["source_quote"])
            self.assertEqual(item["original_ref"],original["source_ref"])
            self.assertFalse(item["registered_ancient_shoreline"])
        names={x["id"] for x in self.d["extra_lakes_and_pools"]}
        self.assertEqual(names,{"EPOOL01","EPOOL02","EPOOL03","EPOOL04"})
        self.assertEqual(self.d["extra_lakes_and_pools"][0]["count"],3)
        guards={x["id"]:x for x in self.d["water_identity_guardrails"]}
        self.assertEqual(guards["SEPARATE01"]["a"],"ic_zhaoyi_pool")
        self.assertEqual(guards["SEPARATE01"]["b"],"ic_diquan")
        self.assertEqual(guards["SEPARATE02"]["b"],"ic_yonghe_pool_south")
        self.assertEqual(guards["SEPARATE03"]["a"],"ic_mengfan_pool")

    def test_topology_is_non_geographic_and_period_aware(self):
        topology=self.d["hydrological_topology"]
        self.assertEqual(len(topology),10)
        ids={x["id"] for x in self.d["water_components"]}
        for edge in topology:
            self.assertIn(edge["from"],ids)
            self.assertIn(edge["to"],ids)
            self.assertIsNone(edge["ancient_geographic_polyline"])
            self.assertTrue(edge["draw_schematic_only"])
        self.assertTrue(any(x["from"]=="W01" and x["to"]=="W07" for x in topology))
        self.assertTrue(any(x["from"]=="W10" and x["to"]=="W12" for x in topology))
        self.assertTrue(any("东汉" in x["evidence_summary"] for x in self.d["water_components"]))

    def test_major_road_inventory_keeps_three_scales_separate(self):
        roads=self.d["roads"]
        published=roads["inner_city_published_summary"]
        self.assertEqual((published["ew_count"],published["ns_count"]),(5,5))
        self.assertEqual(len(published["ew"]),5)
        self.assertEqual(len(published["ns"]),5)
        self.assertFalse(published["matching_to_old_8_fragments_resolved"])
        self.assertTrue(all(x["source_map_exact_registered_ancient_line"] is None
                            for x in published["ew"]+published["ns"]))
        assert_road_ids={x["feature_id"] for x in read(ROOT/"research/prosperity-v4/road-functions-p452.json")["road_segments"]}
        self.assertEqual(set(roads["p1_old_remnant_feature_ids"]),assert_road_ids)
        self.assertEqual(len(assert_road_ids),8)
        outer=roads["outer_city"]
        self.assertEqual(outer["published_major_corridor_count"],9)
        self.assertEqual(outer["individual_old_original_survey_paths_acquired"],0)
        self.assertTrue(outer["cannot_create_nine_synthetic_lines"])
        ward=roads["baimasi_local"]
        self.assertEqual(ward["new_roads_reported"],6)
        self.assertEqual(ward["local_ew_street_interval_m"],40)
        self.assertEqual(ward["local_ns_street_interval_m"],86)
        self.assertIn("NOT road width",ward["number_semantics"])
        self.assertTrue(ward["extrapolation_to_citywide_not_allowed"])

    def test_old_site_map_and_approved_panorama_unchanged(self):
        copy=OUT/"source-layout-unchanged.svg"
        original=SITE/"prosperity/source-layout.svg"
        self.assertEqual(sha(copy),sha(original))
        self.assertEqual(sha(copy),self.d["baseline_source_map_sha256"])
        self.assertEqual(sha(copy),self.info["files_sha256"]["prosperity/source-layout.svg"])
        self.assertEqual(self.preservation["source_map_original_sha256"],sha(original))
        self.assertTrue(self.preservation["all_prior_protected_unchanged"])
        for path,digest in self.preservation["protected_sha256"].items():
            self.assertEqual(sha(SITE/path),digest,path)
            self.assertEqual(self.info["files_sha256"][path],digest,path)
        prev=OUT/"history/prosperity-street-clusters-before-p50.html"
        self.assertEqual(sha(prev),self.preservation["original_p453_html_sha256"])
        now=(SITE/"prosperity-street-clusters.html").read_text(encoding="utf-8")
        self.assertEqual(now.count('id="p50-blocking"'),1)
        self.assertEqual(re.sub(r'<section id="p50-blocking".*?</section>','',now,count=1,flags=re.S),
                         prev.read_text(encoding="utf-8"))
        oldhero=read(SITE/"homepage/approval-v9.json")["hero"]
        self.assertEqual(oldhero["revision"],"panorama-approved-v9")
        self.assertEqual(oldhero["status"],"approved")
        self.assertEqual(oldhero["source_sha256"],"2a59bf83886d77f7c9226ec7f5d99c94ea6c63c6e207c2e560ee82f80ed93891")

    def test_four_page_schematic_atlas_and_file_checksums(self):
        self.assertIn('data-section="hydro"',self.html)
        self.assertIn('data-section="roads"',self.html)
        self.assertIn('data-panel="hydro"',self.html)
        self.assertIn('data-panel="roads"',self.html)
        self.assertIn("尚未全部定位",self.html)
        self.assertIn("40米",self.html)
        for name in ["water-topology.svg","road-matrix.svg","lake-evidence.svg"]:
            root=ET.parse(OUT/name).getroot()
            self.assertEqual(root.tag,NS+"svg")
            self.assertEqual(root.attrib["viewBox"],"0 0 1800 1450")
            self.assertGreater((OUT/name).stat().st_size,4000)
        self.assertEqual(len(PdfReader(SITE/"downloads/city-anchors-p50-atlas.pdf").pages),4)
        manifest=read(OUT/"bundle-manifest.json")
        self.assertEqual(manifest["version"],VERSION)
        self.assertEqual(manifest["source_commit"],self.info["source_commit"])
        with zipfile.ZipFile(SITE/"downloads/city-anchors-p50-package.zip") as z:
            self.assertEqual(set(z.namelist()),set(manifest["files_sha256"])|{"city-anchors/bundle-manifest.json"})
            for path,digest in manifest["files_sha256"].items():
                self.assertEqual(hashlib.sha256(z.read(path)).hexdigest(),digest)
        for path in [SITE/"city-anchors.html",SITE/"downloads/city-anchors-p50-atlas.pdf",
                     SITE/"downloads/city-anchors-p50-package.zip",*OUT.rglob("*")]:
            if path.is_file():
                self.assertEqual(sha(path),self.info["files_sha256"][path.relative_to(SITE).as_posix()],str(path))
        self.assertEqual(self.release["city_anchors_version"],VERSION)
        self.assertIn(VERSION,self.release["extensions"])
        self.assertEqual(self.info["city_anchors"]["water_components"],15)
        self.assertEqual(self.info["city_anchors"]["waterbody_named_entities"],11)
        self.assertEqual(self.info["city_anchors"]["inner_main_road_summary"],10)
        self.assertEqual(self.info["city_anchors"]["outer_major_road_summary"],9)
        self.assertEqual(self.info["city_anchors"]["approved_ancient_geo_controls"],0)
        self.assertFalse(self.info["city_anchors"]["complete_historical_water_network"])
        self.assertFalse(self.info["city_anchors"]["complete_georeferenced_trunk_road_network"])

if __name__=="__main__":
    unittest.main()
