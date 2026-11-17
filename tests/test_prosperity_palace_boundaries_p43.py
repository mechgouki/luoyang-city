"""P4.3: provenance, source ranking, identical figure scales and previous milestone safety."""
from pathlib import Path
import hashlib
import json
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
OUT=SITE/"prosperity-palace-boundaries"
SRC=ROOT/"research/prosperity-v4/palace-boundary-variants-p43.json"

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class PalaceBoundaryP43(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=read(SRC)
        cls.published=read(OUT/"data.json")
        cls.info=read(SITE/"build-info.json")
        cls.html=(SITE/"prosperity-palace-boundaries.html").read_text(encoding="utf-8")
    def test_complete_source_retained_and_older_p42_not_replaced(self):
        self.assertEqual(self.published,self.source)
        self.assertEqual(read(SITE/"prosperity-taiji-courts/data.json"),read(ROOT/"research/prosperity-v4/taiji-court-relations.json"))
        self.assertEqual([x["ns_m"] for x in read(SITE/"prosperity-taiji-courts/data.json")["courtyard_extent_variants"]],[310,380])
        self.assertIn('id="p43-next"',(SITE/"prosperity-taiji-courts.html").read_text(encoding="utf-8"))
        self.assertNotIn("p43-next",(SITE/"index.html").read_text(encoding="utf-8"))
    def test_report_and_source_lineage(self):
        d=self.published
        self.assertEqual([(x["ew_m"],x["ns_m"]) for x in d["reporting_variants"]],[(340,310),(320,370),(320,380)])
        self.assertEqual(len(d["sources"]),6)
        self.assertEqual(d["sources"][0]["lineage_group"],d["sources"][1]["lineage_group"])
        self.assertTrue(all(not s["is_independent_excavation_measurement"] for s in d["sources"]))
        self.assertIn("popular",d["reporting_variants"][1]["source_grade"])
        self.assertEqual(d["metric_differences_m"],{"B_minus_A":{"ew":-20,"ns":60},"C_minus_A":{"ew":-20,"ns":70},"C_minus_B":{"ew":0,"ns":10}})
        self.assertTrue(all(not v["original_measurement_endpoints_available"] and not v["real_boundary_polygon_available"] for v in d["reporting_variants"]))
    def test_no_ground_truth_promoted(self):
        reg=self.published["spatial_registration"]
        self.assertEqual(reg["verified_common_ground_controls"],0)
        self.assertEqual(reg["verified_shared_endpoints"],0)
        self.assertEqual(reg["new_absolute_ancient_coordinates"],0)
        self.assertFalse(reg["site_court_walls_overlay_allowed"])
        self.assertFalse(reg["roof_heights_reconstructed"])
        self.assertTrue(all(x["absolute_coordinates"] is None for x in self.published["additional_anchors"]))
        self.assertEqual(self.published["additional_anchors"][0]["ns_remaining_m"],27)
    def test_true_same_scale_svg_and_provenance(self):
        root=ET.parse(OUT/"extent-comparison.svg").getroot()
        self.assertEqual(root.tag,"{http://www.w3.org/2000/svg}svg")
        self.assertEqual(root.attrib["viewBox"],"0 0 1580 940")
        rects=[x for x in root.iter() if x.tag.endswith("rect") and x.get("stroke-dasharray")=="13 8"]
        self.assertEqual(len(rects),3)
        for r,obs in zip(rects,self.published["reporting_variants"]):
            self.assertAlmostEqual(float(r.attrib["width"])/obs["ew_m"],1.1,places=3)
            self.assertAlmostEqual(float(r.attrib["height"])/obs["ns_m"],1.1,places=3)
        for s in self.published["sources"]:
            self.assertIn(s["url"],self.html)
        for code in ["310","370","380","2017","2022","2023","200","300"]:
            self.assertIn(code,self.html)
    def test_downloads_bundle_and_published_manifest(self):
        pdf=SITE/"downloads/prosperity-palace-boundaries-p43-atlas.pdf"
        self.assertEqual(len(PdfReader(pdf).pages),1)
        self.assertTrue((SITE/"downloads/prosperity-palace-boundaries-p43-package.zip").is_file())
        m=read(OUT/"bundle-manifest.json")
        self.assertEqual(m["version"],self.published["version"])
        self.assertEqual(m["source_commit"],self.info["source_commit"])
        with zipfile.ZipFile(SITE/"downloads/prosperity-palace-boundaries-p43-package.zip") as archive:
            self.assertEqual(set(archive.namelist()),set(m["files_sha256"])|{"prosperity-palace-boundaries/bundle-manifest.json"})
            for name,digest in m["files_sha256"].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(),digest)
        for path in [SITE/"prosperity-palace-boundaries.html",pdf,*OUT.iterdir()]:
            if path.is_file():
                rel=path.relative_to(SITE).as_posix()
                self.assertEqual(self.info["files_sha256"][rel],sha(path))
    def test_version_identity_and_links(self):
        d=self.published
        rel=read(SITE/"release.json")
        self.assertEqual(rel["prosperity_palace_boundaries_version"],d["version"])
        self.assertIn(d["version"],rel["extensions"])
        self.assertEqual(self.info["prosperity_palace_boundaries"]["source_commit"],self.info["source_commit"])
        self.assertEqual(self.info["prosperity_palace_boundaries"]["scope_variants"],3)
        self.assertEqual(self.info["prosperity_palace_boundaries"]["verified_geographic_controls"],0)
        self.assertIn('href="./prosperity-palace-boundaries.html"',(SITE/"prosperity-taiji-courts.html").read_text(encoding="utf-8"))
        self.assertIn('href="./prosperity-taiji-courts.html"',self.html)

if __name__=="__main__":
    unittest.main()
