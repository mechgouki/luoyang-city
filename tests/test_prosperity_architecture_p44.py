"""P4.4 gate/courtyard architecture typology, provenance, drawing and predecessor regression."""
from pathlib import Path
import hashlib
import json
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
OUT=SITE/"prosperity-architecture"
SRC=ROOT/"research/prosperity-v4/architecture-types-p44.json"

def data(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class P44Architecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=data(SRC)
        cls.public=data(OUT/"data.json")
        cls.info=data(SITE/"build-info.json")
        cls.html=(SITE/"prosperity-architecture.html").read_text(encoding="utf-8")

    def test_unchanged_source_and_prior_data(self):
        self.assertEqual(self.public,self.source)
        self.assertEqual(
            data(SITE/"prosperity-taiji-courts/data.json"),
            data(ROOT/"research/prosperity-v4/taiji-court-relations.json"))
        self.assertEqual(
            data(SITE/"prosperity-palace-boundaries/data.json"),
            data(ROOT/"research/prosperity-v4/palace-boundary-variants-p43.json"))
        p43=(SITE/"prosperity-palace-boundaries.html").read_text(encoding="utf-8")
        self.assertEqual(p43.count('id="p44-next"'),1)
        self.assertIn('href="./prosperity-architecture.html"',p43)
        homepage=data(SITE/"homepage/metadata.json")
        self.assertEqual(homepage["hero"]["revision"],"panorama-interim-v8")
        self.assertEqual(homepage["hero"]["visual_review"],"further_revision_requested")

    def test_six_types_are_structurally_different(self):
        d=self.public
        self.assertEqual(len(d["types"]),6)
        byid={t["id"]:t for t in d["types"]}
        self.assertEqual(len(byid),6)
        self.assertEqual([t["passage_count"] for t in d["types"]],[3,3,3,1,1,1])
        self.assertEqual(byid["palace_axial_gate"]["reported_bay_grid"],{"frontage_bays":7,"depth_bays":4})
        self.assertEqual(byid["palace_axial_gate"]["observed_evidence"]["changhe_column_bases"],40)
        self.assertEqual(byid["palace_side_gate"]["reported_bay_grid"],{"frontage_bays":5,"depth_bays":2})
        self.assertEqual(byid["east_ge_gate"]["observed_evidence"]["base_count_per_row"],4)
        self.assertEqual(byid["roofed_court_gate"]["reported_bay_grid"],{"frontage_bays":1,"depth_bays":2})
        self.assertAlmostEqual(byid["corridor_court_gate"]["observed_evidence"]["door_opening_m_approx"],2.5)
        self.assertTrue(all(t["roof_height_m"] is None and not t["upper_floors_known"] for t in d["types"]))

    def test_reports_not_silently_merged_or_average(self):
        readings=self.public["source_scope_comparisons"]
        self.assertEqual(len(readings),3)
        self.assertEqual([(r["readings"][0]["value_m"],r["readings"][1]["value_m"]) for r in readings],
                         [(4,4.3),(2.3,2.9),(3.5,4)])
        self.assertEqual(readings[0]["result"],"different_measurement_semantics_do_not_average")
        self.assertEqual(readings[1]["result"],"measurement_reference_and_reporting_stage_unverified")
        self.assertEqual(readings[2]["result"],"identity_of_described_gates_not_verified")
        self.assertIsNone(readings[2]["subject_id"])

    def test_explicit_uncertainty_and_source_lineages(self):
        d=self.public
        self.assertEqual(len(d["sources"]),4)
        self.assertEqual(d["sources"][0]["original_publication"],"《华夏考古》2018年第6期")
        self.assertEqual(d["sources"][0]["source_family"],d["sources"][1]["source_family"])
        self.assertTrue(all(not item["readable_metric_original"] for item in d["figure_inventory"]))
        self.assertTrue(all(item["not_applied_as_city_geography"] for item in d["figure_inventory"]))
        self.assertEqual(d["geo_registration"]["verified_common_ground_controls"],0)
        self.assertEqual(d["geo_registration"]["new_ancient_absolute_coordinates"],0)
        self.assertFalse(d["geo_registration"]["roof_dimensions_verified"])
        self.assertFalse(d["geo_registration"]["full_court_overlay_allowed"])
        self.assertFalse(d["chronology"]["phase_specific_roof_models_verified"])

    def test_svg_structure_and_originality(self):
        for item,words in [
            ("gate-matrix.svg",["阊阖门","神虎门","东閤门","廊道式"]),
            ("east-ge-source-comparison.svg",["4.3","2.9","3.5"]),
            ("palace-relation-grammar.svg",["阊阖门","止车门","端门","太极东堂"])
        ]:
            path=OUT/item
            root=ET.parse(path).getroot()
            self.assertEqual(root.tag,"{http://www.w3.org/2000/svg}svg")
            self.assertEqual(root.attrib["viewBox"],"0 0 1660 1050")
            contents=path.read_text(encoding="utf-8")
            for word in words:
                self.assertIn(word,contents)
            self.assertGreater(len(contents),2800)
        matrix=ET.parse(OUT/"gate-matrix.svg").getroot()
        dots=[x for x in matrix.iter() if x.tag.endswith("circle")]
        self.assertGreaterEqual(len(dots),70)

    def test_downloads_zip_and_website(self):
        pdf=SITE/"downloads/prosperity-architecture-p44-atlas.pdf"
        self.assertEqual(len(PdfReader(pdf).pages),3)
        self.assertIn('data-type="east_ge_gate"',self.html)
        self.assertIn('data-type-panel="east_ge_gate"',self.html)
        for t in self.public["types"]:
            self.assertIn(f'data-type="{t["id"]}"',self.html)
            self.assertIn(t["inference"],self.html)
        for source in self.public["sources"]:
            self.assertIn(source["url"],self.html)
        self.assertEqual(self.html.count('<img src="./prosperity-architecture/'),3)
        manifest=data(OUT/"bundle-manifest.json")
        self.assertEqual(manifest["source_commit"],self.info["source_commit"])
        zip_path=SITE/"downloads/prosperity-architecture-p44-package.zip"
        with zipfile.ZipFile(zip_path) as arc:
            self.assertEqual(set(arc.namelist()),set(manifest["files_sha256"])|{"prosperity-architecture/bundle-manifest.json"})
            for path,digest in manifest["files_sha256"].items():
                self.assertEqual(hashlib.sha256(arc.read(path)).hexdigest(),digest)
        for path in [SITE/"prosperity-architecture.html",pdf,zip_path,*OUT.iterdir()]:
            if path.is_file():
                key=path.relative_to(SITE).as_posix()
                self.assertEqual(sha(path),self.info["files_sha256"][key])

    def test_release_and_predecessor_still_accessible(self):
        release=data(SITE/"release.json")
        self.assertEqual(release["prosperity_architecture_version"],"prosperity-architecture-p44")
        self.assertIn("prosperity-architecture-p44",release["extensions"])
        self.assertEqual(self.info["prosperity_architecture"]["types"],6)
        self.assertEqual(self.info["prosperity_architecture"]["atlas_pages"],3)
        self.assertEqual(self.info["prosperity_architecture"]["common_geographic_controls"],0)
        for previous in ["index.html","prosperity.html","prosperity-gate.html","prosperity-axis-sources.html","prosperity-taiji-courts.html","prosperity-palace-boundaries.html"]:
            self.assertTrue((SITE/previous).is_file(),previous)

if __name__=="__main__":
    unittest.main()
