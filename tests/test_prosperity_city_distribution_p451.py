"""P4.5.1: source-map anchors, unlocated architecture, reproducible dimensions and publication invariants."""
from pathlib import Path
import hashlib
import json
import re
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
OUT=SITE/"prosperity-city-distribution"
VERSION="prosperity-city-distribution-p451"
NS="{http://www.w3.org/2000/svg}"

def data(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class SourceDistributionP451(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.new=data(OUT/"data.json")
        cls.src=data(ROOT/"research/prosperity-v4/city-distribution-p451.json")
        cls.geo=data(ROOT/"research/prosperity-v1/geographic-evidence.json")
        cls.p44=data(ROOT/"research/prosperity-v4/architecture-types-p44.json")
        cls.info=data(SITE/"build-info.json")
        cls.rel=data(SITE/"release.json")
        cls.html=(SITE/"prosperity-city-distribution.html").read_text(encoding="utf-8")

    def test_source_scope_and_separate_reference_layers(self):
        n=self.new
        self.assertEqual(n["version"],VERSION)
        self.assertEqual(n["inputs"]["original_source_crs"],"EPSG:4610 (Xian 1980, as printed on 2012 source map)")
        self.assertEqual(len(self.geo["features"]),30)
        self.assertEqual(sum(bool(x.get("entity_id")) for x in self.geo["features"]),13)
        self.assertEqual(n["source_map_audit"]["site_remains_features"],26)
        self.assertEqual(n["source_map_audit"]["modern_river_line_features"],1)
        self.assertEqual(n["source_map_audit"]["source_map_illustrative_envelope_features"],1)
        self.assertEqual(n["source_map_audit"]["newly_geolocated_historical_buildings"],0)
        self.assertEqual(n["source_map_audit"]["independently_registered_ancient_gcp_count"],0)
        self.assertFalse(n["source_map_audit"]["quantitative_population_density_recovered"])
        self.assertTrue(n["source_map_overlay"]["do_not_use_as_building_footprint_corners"])
        self.assertFalse(n["source_map_overlay"]["display_coordinates_have_ancient_geographic_meaning"])
        self.assertEqual(n["source_map_overlay"]["new_historical_coordinates_added"],0)
        self.assertEqual(n["source_map_overlay"]["original_base_map_sha256"],sha(SITE/"prosperity/source-layout.svg"))

    def test_no_silent_source_or_type_promotion(self):
        old={f["id"]:f for f in self.geo["features"]}
        anchors=self.new["anchored_buildings"]
        self.assertEqual(len(anchors),4)
        self.assertEqual([x["id"] for x in anchors],["C01","C02","C03","C04"])
        self.assertEqual({x["feature_id"] for x in anchors},{
            "geo-changhe-palace-gate","geo-jianchun-gate",
            "geo-taiji-hall-reference","geo-yongning-pagoda-reference"})
        for b in anchors:
            original=old[b["feature_id"]]
            self.assertEqual(original["geometry"]["type"],"Point")
            self.assertEqual(original.get("entity_id"),b["entity_id"])
            self.assertFalse(b["site_registered_polygon_allowed"])
            self.assertIsNone(b["measured_elevation_m"])
            self.assertFalse(b["roof_style_verified"])
        known_types={x["id"] for x in self.p44["types"]}
        anchored_types={x["type_id"] for x in anchors if x["type_id"]}
        unplaced_types={x["type_id"] for x in self.new["unplaced_p44_types"]}
        self.assertEqual(known_types,anchored_types|unplaced_types)
        self.assertFalse(anchored_types&unplaced_types)
        self.assertEqual(len(unplaced_types),4)
        self.assertEqual(self.new["enclosure_context"][0]["feature_id"],"geo-yongning-temple-walls")
        self.assertFalse(self.new["enclosure_context"][0]["closed_polygon_allowed"])

    def test_existing_svg_is_same_and_highlights_its_original_centers(self):
        original=ET.parse(SITE/"prosperity/source-layout.svg").getroot()
        marked=ET.parse(OUT/"grounded-distribution.svg").getroot()
        self.assertEqual(original.attrib["viewBox"],marked.attrib["viewBox"])
        for feature in self.geo["features"]:
            old=[x for x in original.iter() if x.get("data-feature-id")==feature["id"]]
            new=[x for x in marked.iter() if x.get("data-feature-id")==feature["id"] and x.get("class")!="source-binding"]
            self.assertEqual(len(old),1,feature["id"])
            self.assertEqual(len(new),1,feature["id"])
            self.assertEqual(ET.tostring(old[0]),ET.tostring(new[0]),feature["id"])
        overlays=[x for x in marked.iter() if x.get("class")=="source-binding"]
        self.assertEqual(len(overlays),4)
        refs=self.new["source_map_overlay"]["display_only_svg_locations"]
        self.assertEqual(set(refs),{"C01","C02","C03","C04"})
        for overlay in overlays:
            ref=overlay.get("data-feature-id")
            binding=overlay.get("data-binding-id")
            self.assertIn(binding,refs)
            old=[x for x in original.iter() if x.get("data-feature-id")==ref][0]
            circle=[x for x in old.iter() if x.tag==NS+"circle" and x.get("r")=="8"][0]
            self.assertEqual(refs[binding],[round(float(circle.get("cx")),2),round(float(circle.get("cy")),2)])
            self.assertEqual(overlay.get("tabindex"),"0")

    def test_honest_same_meter_scale_without_geographic_footprints(self):
        root=ET.parse(OUT/"scale-plates.svg").getroot()
        cards=[x for x in root.iter() if x.get("data-kind")=="unplaced_dimension_reference_only"]
        self.assertEqual(len(cards),4)
        binding={x["id"]:x for x in self.new["anchored_buildings"]}
        for card in cards:
            ident=card.get("data-binding-id")
            d=binding[ident]["reported_footprint_m"]
            self.assertAlmostEqual(float(card.get("width"))/d["east_west"],3.2,places=5)
            self.assertAlmostEqual(float(card.get("height"))/d["north_south"],3.2,places=5)
        self.assertEqual(binding["C01"]["reported_footprint_m"],{"east_west":44.5,"north_south":24.4})
        self.assertEqual(binding["C02"]["reported_footprint_m"],{"east_west":12.5,"north_south":30})
        self.assertEqual(binding["C03"]["reported_footprint_m"],{"east_west":100,"north_south":60})
        self.assertEqual(binding["C04"]["reported_footprint_m"],{"east_west":38.2,"north_south":38.2})

    def test_approved_homepage_kept_and_new_navigation_injected_once(self):
        h2=data(SITE/"homepage/approval-v9.json")["hero"]
        self.assertEqual(h2["revision"],"panorama-approved-v9")
        self.assertEqual(h2["status"],"approved")
        self.assertEqual(h2["source_sha256"],"2a59bf83886d77f7c9226ec7f5d99c94ea6c63c6e207c2e560ee82f80ed93891")
        proof=data(OUT/"preservation.json")
        self.assertTrue(proof["protected_unchanged"])
        self.assertEqual(len(proof["protected_files_sha256"]),proof["protected_files_sha256"].__len__())
        for path,value in proof["protected_files_sha256"].items():
            self.assertEqual(sha(SITE/path),value,path)
        for name in ("index.html","v3.0-dual.html"):
            old=(OUT/"history"/name.replace(".html","-before-p451.html")).read_text(encoding="utf-8")
            preserved = {"index.html": "homepage/history/index-before-r4.html",
                         "v3.0-dual.html": "homepage/history/v3.0-dual-before-v10.html"}.get(name, name)
            now=(SITE/preserved).read_text(encoding="utf-8")
            self.assertEqual(sha(OUT/"history"/name.replace(".html","-before-p451.html")),proof["pre_edit_html_sha256"][name])
            self.assertEqual(now.count('id="prosperity-p451-entry"'),1)
            self.assertIn('data-hero-revision="panorama-approved-v9"',now)
            self.assertIn(h2["asset"],now)
            self.assertEqual(re.sub(r'<section id="prosperity-p451-entry".*?</section>\n','',now,count=1,flags=re.S),old)

    def test_web_entry_assets_archive_and_hashes(self):
        self.assertIn('data-binding-id="C01"',self.html)
        self.assertIn('data-select-binding="C04"',self.html)
        self.assertIn("现代洛水",self.html)
        self.assertIn("516",self.html)
        for source in ("./prosperity-city-distribution/grounded-distribution.svg",
                       "./prosperity-city-distribution/scale-plates.svg",
                       "./prosperity-city-distribution/evidence-tiers.svg",
                       "./prosperity-city-distribution/data.json"):
            self.assertIn(source,self.html)
        self.assertEqual(len(PdfReader(SITE/"downloads/prosperity-city-distribution-p451-atlas.pdf").pages),3)
        manifest=data(OUT/"bundle-manifest.json")
        self.assertEqual(manifest["source_commit"],self.info["source_commit"])
        with zipfile.ZipFile(SITE/"downloads/prosperity-city-distribution-p451-package.zip") as z:
            self.assertEqual(set(z.namelist()),set(manifest["files_sha256"])|{"prosperity-city-distribution/bundle-manifest.json"})
            for path,expected in manifest["files_sha256"].items():
                self.assertEqual(hashlib.sha256(z.read(path)).hexdigest(),expected)
        for p in [SITE/"prosperity-city-distribution.html",
                  SITE/"downloads/prosperity-city-distribution-p451-atlas.pdf",
                  SITE/"downloads/prosperity-city-distribution-p451-package.zip",*OUT.rglob("*")]:
            if p.is_file():
                relative=p.relative_to(SITE).as_posix()
                self.assertEqual(sha(p),self.info["files_sha256"][relative])
        self.assertEqual(self.rel["prosperity_city_distribution_version"],VERSION)
        self.assertIn(VERSION,self.rel["extensions"])
        self.assertEqual(self.info["prosperity_city_distribution"]["source_feature_count"],30)
        self.assertEqual(self.info["prosperity_city_distribution"]["anchored_building_count"],4)
        self.assertEqual(self.info["prosperity_city_distribution"]["unlocated_gate_type_count"],4)
        self.assertEqual(self.info["prosperity_city_distribution"]["new_absolute_ancient_coordinates"],0)

if __name__=="__main__":
    unittest.main()
