"""P4.5.3: 17 source-limited relationships, immutable old site index, and no new GIS."""
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
OUT=SITE/"prosperity-street-clusters"
VERSION="prosperity-street-clusters-p453"
NS="{http://www.w3.org/2000/svg}"

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class P453SourceRelations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=read(OUT/"data.json")
        cls.raw=read(ROOT/"research/prosperity-v4/street-clusters-p453.json")
        cls.info=read(SITE/"build-info.json")
        cls.release=read(SITE/"release.json")
        cls.html=(SITE/"prosperity-street-clusters.html").read_text(encoding="utf-8")
        cls.proof=read(OUT/"preservation.json")
    def test_all_prior_site_and_metadata_unchanged_except_one_link(self):
        self.assertTrue(self.proof["protected_unchanged"])
        for path,digest in self.proof["protected_files"].items():
            self.assertEqual(sha(SITE/path),digest,path)
            self.assertEqual(self.info["files_sha256"][path],digest)
        self.assertEqual(read(SITE/"homepage/approval-v9.json")["hero"]["revision"],"panorama-approved-v9")
        original=OUT/"history/prosperity-road-functions-before-p453.html"
        self.assertEqual(sha(original),self.proof["previous_p452_html_sha256"])
        updated=(SITE/"prosperity-road-functions.html").read_text(encoding="utf-8")
        self.assertEqual(updated.count('id="p453-next"'),1)
        self.assertIn('href="./prosperity-street-clusters.html"',updated)
        self.assertEqual(re.sub(r'<section id="p453-next".*?</section>','',updated,count=1,flags=re.S),
                         original.read_text(encoding="utf-8"))
        self.assertEqual(self.info["files_sha256"]["prosperity/source-layout.svg"],sha(SITE/"prosperity/source-layout.svg"))
        self.assertEqual(self.info["prosperity_city_distribution"]["anchored_building_count"],4)
        self.assertEqual(self.info["prosperity_road_functions"]["road_feature_count"],8)
    def test_true_source_entities_and_graded_relations(self):
        self.assertEqual(self.d,self.raw)
        self.assertEqual(self.d["version"],VERSION)
        c=self.d["clusters"]
        self.assertEqual([x["id"] for x in c],["K01","K02","K03"])
        nodes={x["id"] for group in c for x in group["nodes"]}
        self.assertEqual(len(nodes),20)
        assert_nodes={x["id"] for x in read(ROOT/"data/entities.json")}
        self.assertTrue(nodes<=assert_nodes)
        edges=[(group["id"],e) for group in c for e in group["edges"]]
        self.assertEqual(len(edges),17)
        self.assertEqual(sum(e["grade"]=="A" for _,e in edges),16)
        self.assertEqual(sum(e["grade"]=="C" for _,e in edges),1)
        self.assertTrue(all(not e["geographic_line_allowed"] for _,e in edges))
        self.assertTrue(all(group["non_geographic"] for group in c))
        self.assertEqual([e["id"] for _,e in edges if e["grade"]=="C"],["K01E08"])
        palace={e["id"]:e for e in c[0]["edges"]}
        self.assertEqual((palace["K01E01"]["subject"],palace["K01E01"]["object"]),
                         ("ic_yongning","ic_palace_avenue"))
        self.assertEqual(palace["K01E06"]["subject"],"ic_guozixue")
        self.assertEqual(palace["K01E06"]["object"],"ic_situ")
        self.assertEqual(palace["K01E08"]["source_record"],"B1:B03")
        bridge={e["id"]:e for e in c[1]["edges"]}
        self.assertEqual(bridge["K02E04"]["object"],"road_eaststone_north")
        self.assertEqual(bridge["K02E05"]["object"],"road_eaststone_north")
        self.assertEqual(c[1]["temporal_events"][0]["year"],527)
        self.assertEqual(c[1]["temporal_events"][0]["subject"],"bridge_jianchun")
        south={e["id"]:e for e in c[2]["edges"]}
        self.assertEqual(south["K03E03"]["object"],"luoshui")
        self.assertEqual(south["K03E04"]["object"],"li_guizheng")
    def test_no_fake_bridges_market_location_river_or_roof(self):
        a=self.d["audit"]
        self.assertEqual(a["new_ancient_wgs84_points"],0)
        self.assertEqual(a["sourced_footprint_polygons_created"],0)
        self.assertIsNone(a["measured_old_roof_height_m"])
        self.assertFalse(a["existing_source_geometry_modified"])
        self.assertFalse(a["ancient_river_channel_constructed"])
        self.assertFalse(a["historical_population_density_estimated"])
        self.assertFalse(a["homepage_visual_changed"])
        forbidden={(x["a"],x["b"]) for x in self.d["forbidden_inferences"]}
        self.assertIn(("bridge_jianchun","bridge_eaststone"),forbidden)
        self.assertIn(("market_sitong","market_fish"),forbidden)
        self.assertIn(("v3_jingming","bridge_yong"),forbidden)
    def test_diagrams_exact_index_and_nonspatial_attestation(self):
        old=SITE/"prosperity-city-distribution/grounded-distribution.svg"
        copy=OUT/"source-index-unchanged.svg"
        self.assertEqual(sha(old),sha(copy))
        self.assertEqual(sha(copy),self.proof["source_index_sha256"])
        paths=["palace-street.svg","jianchun-stones.svg","south-bridge-market.svg"]
        for name in paths:
            root=ET.parse(OUT/name).getroot()
            self.assertEqual(root.tag,NS+"svg")
            self.assertEqual(root.attrib["viewBox"],"0 0 1800 1370")
            self.assertGreater(len((OUT/name).read_bytes()),3000)
            self.assertIn("非地理",ET.tostring(root,encoding="unicode"))
        self.assertIn("御道西",(OUT/"palace-street.svg").read_text(encoding="utf-8"))
        self.assertIn("527",(OUT/"jianchun-stones.svg").read_text(encoding="utf-8"))
        self.assertIn("洛水",(OUT/"south-bridge-market.svg").read_text(encoding="utf-8"))
    def test_page_bundles_hash_integrity_and_four_page_atlas(self):
        for ident in ("K01","K02","K03"):
            self.assertIn('data-cluster="'+ident+'"',self.html)
            self.assertIn('data-cluster-panel="'+ident+'"',self.html)
        for grade in ("A","C"):
            self.assertIn('data-grade="'+grade+'"',self.html)
        self.assertEqual(self.html.count('class="relation-row"'),17)
        self.assertIn('source-index-unchanged.svg',self.html)
        self.assertEqual(len(PdfReader(SITE/"downloads/prosperity-street-clusters-p453-atlas.pdf").pages),4)
        manifest=read(OUT/"bundle-manifest.json")
        self.assertEqual(manifest["version"],VERSION)
        self.assertEqual(manifest["source_commit"],self.info["source_commit"])
        with zipfile.ZipFile(SITE/"downloads/prosperity-street-clusters-p453-package.zip") as z:
            self.assertEqual(set(z.namelist()),
                             set(manifest["files_sha256"])|{"prosperity-street-clusters/bundle-manifest.json"})
            for path,digest in manifest["files_sha256"].items():
                self.assertEqual(hashlib.sha256(z.read(path)).hexdigest(),digest)
        for p in [SITE/"prosperity-street-clusters.html",
                  SITE/"downloads/prosperity-street-clusters-p453-atlas.pdf",
                  SITE/"downloads/prosperity-street-clusters-p453-package.zip",
                  *OUT.rglob("*")]:
            if p.is_file():self.assertEqual(sha(p),self.info["files_sha256"][p.relative_to(SITE).as_posix()])
        self.assertEqual(self.release["prosperity_street_clusters_version"],VERSION)
        self.assertIn(VERSION,self.release["extensions"])
        self.assertEqual(self.info["prosperity_street_clusters"]["direct_relations"],16)
        self.assertEqual(self.info["prosperity_street_clusters"]["conditional_relations"],1)
        self.assertEqual(self.info["prosperity_street_clusters"]["atlas_pages"],4)

if __name__=="__main__":
    unittest.main()
