"""P4.1 original-publication inventory, naming and measurement disagreements."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
OUT=SITE/"prosperity-axis-sources"
SRC=ROOT/"research/prosperity-v4/primary-source-audit.json"
VERSION="prosperity-axis-p41-source-audit"
def load(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class PrimarySourceAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load(SRC)
        cls.published=load(OUT/"audit.json")
        cls.info=load(SITE/"build-info.json")
        cls.page=(SITE/"prosperity-axis-sources.html").read_text(encoding="utf-8")

    def test_record_matches_original_payload(self):
        self.assertEqual(self.data,self.published)
        self.assertEqual(self.data["version"],VERSION)
        self.assertEqual(self.info["prosperity_axis_source_audit"]["version"],VERSION)
        self.assertEqual(self.info["prosperity_axis_source_audit"]["source_commit"],self.info["source_commit"])

    def test_gate_one_is_not_duplicated(self):
        iden=self.data["identity"]
        self.assertEqual(iden["archaeological_label"],"一号建筑遗构／一号宫门")
        self.assertEqual(iden["historical_name"],"阊阖门")
        self.assertEqual(iden["separate_archaeological_sites_created"],0)
        self.assertEqual(self.data["resolved_labels_count"],1)
        self.assertGreaterEqual(len(iden["evidence_ids"]),2)

    def test_two_distance_scenarios_are_not_silent_normalized(self):
        self.assertEqual([x["distance_m"] for x in self.data["distance_conflicts"]],[200,300])
        self.assertEqual([x["distance_m"] for x in self.data["shared_segments_from_prior_P4"]],[95,80])
        self.assertEqual(self.data["external_total"]["distance_m"],460)
        self.assertFalse(self.data["external_total"]["same_measuring_endpoints_verified"])
        cases=self.data["alternatives"]
        self.assertEqual([x["sum_m"] for x in cases],[375,475])
        self.assertEqual([x["difference_vs_external_m"] for x in cases],[-85,15])
        for case in cases:
            self.assertEqual(case["sum_m"],95+80+case["third_to_taiji_m"])
            self.assertEqual(case["difference_vs_external_m"],case["sum_m"]-460)
            self.assertFalse(case["geographic_registration"])
        self.assertIn("同一队伍",self.data["source_lineage"]["rule"])

    def test_two_publication_phase_gate_widths_remain_separate(self):
        dims=self.data["second_gate_phased_dimensions"]
        self.assertEqual([x["north_south_m"] for x in dims],[23.0,24.0])
        self.assertEqual([x["east_west_m"] for x in dims],[44.5,44.5])
        self.assertEqual([x["source_id"] for x in dims],["NARA2009","NARA2010"])
        self.assertIn("未取得",self.data["second_gate_diameter_assessment"])

    def test_figure_catalog_and_formal_reports_not_falsely_claimed(self):
        sources={item["id"]:item for item in self.data["sources"]}
        self.assertTrue({"NARA2009","NARA2010","NARA2011","NARA2013","KAOGU2009","KAOGU2010"}<=sources.keys())
        self.assertEqual(self.data["completely_acquired_formal_chinese_journal_plans"],0)
        for sid in ["KAOGU2009","KAOGU2010"]:
            self.assertEqual(sources[sid]["source_kind"],"formal-excavation-journal-not-accessed")
        for sid in ["NARA2009","NARA2010"]:
            self.assertFalse(any(sources[sid].get(k,False) for k in
                ["full_excavation_plan_of_number_2_available","full_excavation_plan_of_number_3_available"]))
        figs=self.data["onsite_figure_audit"]
        self.assertGreaterEqual(len(figs),6)
        self.assertTrue(any(x.get("label_gate_1") and x.get("label_changhe") for x in figs))
        self.assertTrue(all(x["url"].startswith("https://") for x in sources.values()))
        self.assertTrue(all(x.get("image_raster_republished") is False for x in sources.values()))

    def test_geographic_proofs_not_fabricated(self):
        reg=self.data["city_registration"]
        self.assertEqual(reg["new_city_control_points"],0)
        self.assertEqual(reg["absolute_coordinates_added"],0)
        self.assertFalse(reg["exact_survey_alignment_approved"])
        self.assertNotIn("coordinates_wgs84",self.data)
        self.assertIn("不推导独立地理坐标",self.data["methodological_scope"])

    def test_two_original_svg_charts_are_valid(self):
        for name,marker in [("distance-comparison.svg","375"),("figure-inventory.svg","2009")]:
            path=OUT/name
            root=ET.parse(path).getroot()
            self.assertEqual(root.tag,"{http://www.w3.org/2000/svg}svg")
            self.assertEqual(root.get("viewBox"),"0 0 1600 1000")
            text=path.read_text(encoding="utf-8")
            self.assertIn(marker,text)
            self.assertGreater(len(text),3000)

    def test_page_readable_links_and_both_scenarios(self):
        self.assertIn("一号门",self.page)
        self.assertIn("200米",self.page)
        self.assertIn("300米",self.page)
        self.assertIn("475米",self.page)
        self.assertIn("375米",self.page)
        self.assertIn("二号门",self.page)
        self.assertIn('id="scenario"',self.page)
        self.assertIn('id="sources"',self.page)
        self.assertIn("原始测绘平面",self.page)
        for item in self.data["sources"]:
            # Every source has an audit link, but formal reports link to the catalog only.
            self.assertIn(item["url"].split("#")[0],self.page)
        self.assertTrue((OUT/"style.css").is_file())
        self.assertTrue((OUT/"app.js").is_file())

    def test_zip_pdf_and_release_integrity(self):
        pdf=SITE/"downloads/prosperity-axis-p41-atlas.pdf"
        z=SITE/"downloads/prosperity-axis-p41-package.zip"
        self.assertEqual(len(PdfReader(pdf).pages),2)
        manifest=load(OUT/"bundle-manifest.json")
        self.assertEqual(manifest["version"],VERSION)
        self.assertEqual(manifest["source_commit"],self.info["source_commit"])
        with zipfile.ZipFile(z) as zf:
            self.assertEqual(set(zf.namelist()),set(manifest["files_sha256"])|{"prosperity-axis-sources/bundle-manifest.json"})
            for name,value in manifest["files_sha256"].items():
                self.assertEqual(hashlib.sha256(zf.read(name)).hexdigest(),value,name)
        self.assertEqual(load(SITE/"release.json")["prosperity_axis_source_audit_version"],VERSION)
        for path in [SITE/"prosperity-axis-sources.html",pdf,z,*OUT.iterdir()]:
            if path.is_file():
                rel=path.relative_to(SITE).as_posix()
                self.assertEqual(self.info["files_sha256"][rel],sha(path),rel)

    def test_source_page_is_findable_without_wiping_previous_release(self):
        for name in ["index.html","prosperity-axis.html","prosperity-gate.html"]:
            self.assertIn("prosperity-axis-sources.html",(SITE/name).read_text(encoding="utf-8"))
        self.assertTrue((SITE/"prosperity-axis/data.json").is_file())
        self.assertTrue((SITE/"prosperity-gate/sources/changhe-plan-native.jpeg").is_file())
        self.assertEqual(self.info["prosperity_axis"]["version"],"prosperity-axis-p4-metric-review")
        self.assertEqual(self.info["prosperity_gate"]["version"],"prosperity-gate-v3")

if __name__=="__main__":unittest.main()
