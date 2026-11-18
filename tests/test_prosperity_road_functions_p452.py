"""P4.5.2: eight original P1 road paths and five source-limited documentary contexts."""
from pathlib import Path
import hashlib
import json
import re
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pypdf import PdfReader
NS="{http://www.w3.org/2000/svg}"
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
OUT=SITE/"prosperity-road-functions"
VER="prosperity-road-functions-p452"
def read(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class P452RoadReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=read(OUT/"data.json")
        cls.src=read(ROOT/"research/prosperity-v4/road-functions-p452.json")
        cls.geo=read(ROOT/"research/prosperity-v1/geographic-evidence.json")
        cls.info=read(SITE/"build-info.json")
        cls.release=read(SITE/"release.json")
        cls.page=(SITE/"prosperity-road-functions.html").read_text(encoding="utf-8")
        cls.preserve=read(OUT/"preservation.json")
    def test_authoritative_inputs_and_exact_eight_road_ids(self):
        self.assertEqual(self.d["version"],VER)
        self.assertEqual(self.d["road_segments"],self.src["road_segments"])
        self.assertEqual(len(self.geo["features"]),30)
        self.assertEqual(sum(bool(x.get("entity_id")) for x in self.geo["features"]),13)
        ids={x["id"] for x in self.geo["features"] if x["id"].startswith("geo-road-") or x["id"].startswith("geo-tongtuo-")}
        roadids={x["feature_id"] for x in self.d["road_segments"]}
        self.assertEqual(len(roadids),8)
        self.assertEqual(roadids,ids)
        self.assertEqual(len(self.d["contexts"]),5)
        self.assertEqual(len(self.d["nongeographic_function_groups"]),5)
        self.assertEqual(len(self.d["road_source_details"]),8)
    def test_road_geometry_metrics_are_only_structural_not_new_routes(self):
        source={x["id"]:x for x in self.geo["features"]}
        for road in self.d["road_source_details"]:
            f=source[road["feature_id"]]
            self.assertEqual(road["source_map_line_parts"],len(f["geometry"]["coordinates"]))
            self.assertEqual(road["source_map_vertex_count"],sum(len(x) for x in f["geometry"]["coordinates"]))
            self.assertEqual(road["source_code"],f["source_feature_code"])
            self.assertEqual(road["published_source_geometry_type"],"MultiLineString")
            self.assertTrue(road["original_geometry_unchanged"])
            self.assertFalse(road["source_map_wgs84_registration_verified"])
            self.assertEqual(f["layer"],"site_remains")
            if road["id"]!="D01":
                self.assertIsNone(road["sourced_length_m"])
                self.assertIsNone(road["sourced_width_m_range"])
        main=self.d["road_source_details"][0]
        self.assertEqual(main["id"],"D01")
        self.assertEqual(main["sourced_length_m"],1650)
        self.assertEqual(main["sourced_width_m_range"],[40,65])
        self.assertFalse(main["same_as_palace_imperial_road_verified"])
    def test_original_all_source_geometries_identical_and_overlays_exact(self):
        old=ET.parse(SITE/"prosperity/source-layout.svg").getroot()
        new=ET.parse(OUT/"road-evidence-map.svg").getroot()
        self.assertEqual(old.get("viewBox"),new.get("viewBox"))
        for feature in self.geo["features"]:
            oid=feature["id"]
            before=[x for x in old.iter() if x.get("data-feature-id")==oid]
            after=[x for x in new.iter() if x.get("data-feature-id")==oid]
            self.assertEqual(len(before),1,oid)
            self.assertEqual(len(after),1,oid)
            self.assertEqual(ET.tostring(before[0]),ET.tostring(after[0]),oid)
        road_groups=[x for x in new.iter() if x.get("class")=="road-group"]
        self.assertEqual(len(road_groups),8)
        for group in road_groups:
            self.assertEqual(group.get("tabindex"),"0")
            ident=group.get("data-road-id")
            originals=self.d["source_map_overlay"]["cloned_exact_original_svg_path_data"][ident]
            drawn=[x.get("d") for x in group if x.get("class")=="road-line"]
            self.assertEqual(drawn,originals)
        self.assertEqual(sha(SITE/"prosperity/source-layout.svg"),self.d["source_map_overlay"]["source_map_sha256"])
        self.assertTrue(self.d["source_map_overlay"]["same_existing_location_only"])
        self.assertFalse(self.d["source_map_overlay"]["source_map_geometry_mutated"])
        self.assertEqual(self.d["source_map_overlay"]["new_historical_coordinates_added"],0)
        self.assertEqual(self.d["source_map_overlay"]["new_street_connections_added"],0)
    def test_only_textual_contexts_and_no_bridge_conflation(self):
        scenarios={x["id"]:x for x in self.d["contexts"]}
        self.assertEqual(set(scenarios),{"R01","R02","R03","R04","R05"})
        self.assertEqual(scenarios["R01"]["mapped_road_ids"],["D01","D02"])
        self.assertFalse(scenarios["R01"]["route_measured"])
        self.assertEqual(scenarios["R02"]["original_quote"],"在宮前閶闔門南一里御道西。")
        self.assertEqual(scenarios["R03"]["entity_ids"][1:3],["bridge_jianchun","bridge_eaststone"])
        self.assertTrue("527" in scenarios["R03"]["not_proved"])
        self.assertEqual(scenarios["R04"]["mapped_road_ids"],[])
        self.assertIn("浮橋",scenarios["R04"]["original_quote"])
        self.assertIn("不",scenarios["R05"]["not_proved"])
        self.assertEqual(self.d["unchanged_assets"]["changed_ancient_original_geometries"],0)
        self.assertEqual(self.d["unchanged_assets"]["added_historical_geographic_anchors"],0)
        self.assertFalse(self.d["data_lineage"]["modern_river_used_as_ancient_river"])
        self.assertTrue(all(not c["route_measured"] for c in scenarios.values()))
        self.assertTrue(all(not x["new_building_footprint"] for x in self.d["nongeographic_function_groups"]))
    def test_archived_p451_original_and_approved_h2_untouched(self):
        self.assertEqual(read(SITE/"homepage/approval-v9.json")["hero"]["revision"],"panorama-approved-v9")
        self.assertTrue(self.preserve["protected_unchanged"])
        self.assertEqual(len(self.preserve["protected_sha256"]),self.preserve["protected_files"])
        for name,digest in self.preserve["protected_sha256"].items():
            self.assertEqual(sha(SITE/name),digest,name)
            self.assertEqual(self.info["files_sha256"][name],digest,name)
        previous=OUT/"history/prosperity-city-distribution-before-p452.html"
        self.assertEqual(sha(previous),self.preserve["previous_p451_html_sha256"])
        new=(SITE/"prosperity-city-distribution.html").read_text(encoding="utf-8")
        self.assertIn('id="p452-next"',new)
        self.assertIn('href="./prosperity-road-functions.html"',new)
        self.assertEqual(
            re.sub(r'<section id="p452-next".*?</section>','',new,count=1,flags=re.S),
            previous.read_text(encoding="utf-8")
        )
        self.assertIn('data-hero-revision="panorama-approved-v9"',(SITE/"index.html").read_text())
        self.assertEqual(read(SITE/"prosperity-city-distribution/data.json")["version"],"prosperity-city-distribution-p451")
    def test_page_atlas_and_integrity(self):
        self.assertIn('data-road-id="D01"',self.page)
        self.assertIn('data-road-control="D08"',self.page)
        self.assertIn('data-context="R05"',self.page)
        self.assertIn("现代洛水",self.page)
        self.assertEqual(len(PdfReader(SITE/"downloads/prosperity-road-functions-p452-atlas.pdf").pages),3)
        for art,contents in [
            ("qualitative-relations.svg",["R01","R02","R05"]),
            ("function-layers.svg",["T01","T05"])]:
            src=(OUT/art).read_text(encoding="utf-8")
            for token in contents:self.assertIn(token,src)
        m=read(OUT/"bundle-manifest.json")
        self.assertEqual(m["version"],VER)
        self.assertEqual(m["source_commit"],self.info["source_commit"])
        with zipfile.ZipFile(SITE/"downloads/prosperity-road-functions-p452-package.zip") as z:
            self.assertEqual(set(z.namelist()),set(m["files_sha256"])|{"prosperity-road-functions/bundle-manifest.json"})
            for path,digest in m["files_sha256"].items():
                self.assertEqual(hashlib.sha256(z.read(path)).hexdigest(),digest)
        for art in [*OUT.rglob("*"),SITE/"downloads/prosperity-road-functions-p452-package.zip",
                    SITE/"downloads/prosperity-road-functions-p452-atlas.pdf",SITE/"prosperity-road-functions.html"]:
            if art.is_file():
                self.assertEqual(sha(art),self.info["files_sha256"][art.relative_to(SITE).as_posix()])
        self.assertEqual(self.release["prosperity_road_functions_version"],VER)
        self.assertEqual(self.info["prosperity_road_functions"]["road_feature_count"],8)
        self.assertEqual(self.info["prosperity_road_functions"]["documentary_context_count"],5)
        self.assertEqual(self.info["prosperity_road_functions"]["function_groups"],5)
        self.assertEqual(self.info["prosperity_road_functions"]["new_ancient_coordinates"],0)

if __name__=="__main__":
    unittest.main()
