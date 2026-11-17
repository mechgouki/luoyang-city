"""P4.2 source-vetted palace structures, period and extent report boundaries."""
from pathlib import Path
import hashlib,json,unittest,xml.etree.ElementTree as ET,zipfile
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
OUT=SITE/"prosperity-taiji-courts"
SRC=ROOT/"research/prosperity-v4/taiji-court-relations.json"
def load(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class TaijiCourtsEvidence(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source=load(SRC);cls.data=load(OUT/"data.json");cls.info=load(SITE/"build-info.json")
  cls.page=(SITE/"prosperity-taiji-courts.html").read_text(encoding="utf-8")
 def test_data_published_verbatim_and_release_identity(self):
  self.assertEqual(self.data,self.source)
  self.assertEqual(self.data["version"],"prosperity-taiji-courts-p42")
  self.assertEqual(self.info["prosperity_taiji_courts"]["version"],self.data["version"])
  self.assertEqual(self.info["prosperity_taiji_courts"]["source_commit"],self.info["source_commit"])
  self.assertEqual(load(SITE/"release.json")["prosperity_taiji_courts_version"],self.data["version"])
 def test_hall_dimensions_provenance_and_no_height(self):
  m=self.data["main_hall"]
  self.assertEqual([m["north_ew_m"],m["south_ew_m"],m["ns_review_m"]],[102.3,98.4,61.5])
  self.assertTrue(m["preserved_platform_not_one_phase_roof"])
  self.assertIsNone(m["historical_height_m"])
  east=self.data["east_hall"]
  self.assertEqual([x["ew_m"] for x in east["observations"]],[47.9,48])
  self.assertEqual([x["ns_m"] for x in east["observations"]],[21.3,23])
  self.assertEqual([x["gap_from_main_east_m"] for x in east["observations"]],[13,14])
  self.assertEqual([x["source_id"] for x in east["observations"]],["JLU2016","XU2020"])
  self.assertFalse(east["relative_north_south_offset_verified"])
  self.assertIsNone(east["roof_height_m"])
  self.assertTrue(east["connection"]["upper_gallery_inferred_not_directly_preserved"])
 def test_partial_court_dimensions_cannot_form_closed_polygon(self):
  x=self.data["northern_courts"]
  self.assertTrue(x["two_courts_east_west"])
  self.assertEqual(x["excavated_ns_strip_range_m"],[11,14])
  self.assertEqual([x["west"]["ew_m_approx"],x["west"]["inner_court_ew_m"],x["west"]["inner_court_ns_m"]],[20,8,4])
  self.assertEqual([x["east"]["south_corridor_bays"],x["east"]["south_corridor_length_remaining_m"]],[9,37])
  self.assertEqual([x["separating_ew_paved_road"]["ew_length_remaining_m"],x["separating_ew_paved_road"]["ns_width_m"]],[52,4])
  self.assertTrue(x["east"]["unexcavated_east_boundary"])
  self.assertFalse(x["complete_courtyard_polygon_known"])
  self.assertFalse(x["northeast_court_2017"]["same_as_earlier_two_courts_verified"])
 def test_courtyard_extent_variants_remain_independent(self):
  a,b=self.data["courtyard_extent_variants"]
  self.assertEqual([a["ew_m"],a["ns_m"]],[340,310])
  self.assertEqual([b["ew_m"],b["ns_m"]],[320,380])
  self.assertEqual([b["ew_m"]-a["ew_m"],b["ns_m"]-a["ns_m"]],[-20,70])
  self.assertEqual(self.data["difference_B_minus_A_m"],{"ew":-20,"ns":70})
  self.assertFalse(self.data["same_courtyard_boundary_identified"])
  self.assertTrue(all(not item["shared_control_verified"] for item in [a,b] if "shared_control_verified" in item))
 def test_three_phase_models_are_not_collapsed(self):
  x=self.data["phase_models"]
  self.assertEqual([i["id"] for i in x],["wei_jin","northern_wei","northern_zhou"])
  self.assertIn("柱网",x[0]["corridor"])
  self.assertIn("夯土隔墙",x[1]["corridor"])
  self.assertIn("未完成",x[2]["boundary"])
  self.assertEqual(self.data["geographic_registration"]["verified_common_control_points"],0)
  self.assertEqual(self.data["geographic_registration"]["new_absolute_coordinates"],0)
  self.assertFalse(self.data["geographic_registration"]["city_geographic_overlay_allowed"])
 def test_source_lineage_and_unknown_types_are_explicit(self):
  self.assertEqual(len(self.data["sources"]),6)
  ids={i["id"] for i in self.data["sources"]}
  self.assertTrue({"JLU2016","XU2020","CASS2015","QIAN2017","CH2023","HENAN2017"}<=ids)
  self.assertIn("同一考古",self.data["source_dependency_note"])
  self.assertFalse(self.data["research_limits"]["whole_courtyard_shape_reconstructed"])
  self.assertFalse(self.data["research_limits"]["building_heights_reconstructed"])
  self.assertFalse(self.data["research_limits"]["unexcavated_edges_closed"])
 def test_3_independent_svg_figures_with_source_caveats(self):
  for name,marker in [("halls-scale.svg","102.3"),("north-courts-relations.svg","52m"),("court-extents.svg","380m")]:
   path=OUT/name
   root=ET.parse(path).getroot()
   self.assertEqual(root.tag,"{http://www.w3.org/2000/svg}svg")
   self.assertEqual(root.get("viewBox"),"0 0 1480 960")
   self.assertIn(marker,path.read_text(encoding="utf-8"))
   self.assertGreater(len(path.read_bytes()),2000)
 def test_page_source_links_and_interactions_explicit(self):
  for p in ['id="halls"','id="northern-courts"','id="phases"','id="extent"','id="sources"','id="downloads"']:
   self.assertIn(p,self.page)
  for i in ["wei_jin","northern_wei","northern_zhou"]:
   self.assertIn(f'data-phase="{i}"',self.page)
  self.assertIn('id="extent-select"',self.page)
  self.assertIn("340",self.page);self.assertIn("310",self.page);self.assertIn("320",self.page);self.assertIn("380",self.page)
  self.assertIn("北魏",self.page);self.assertIn("北周",self.page)
  for s in self.data["sources"]:
   self.assertIn(s["url"],self.page)
 def test_pdf_zip_manifest_has_verifiable_raw_files(self):
  pdf=SITE/"downloads/prosperity-taiji-courts-p42-atlas.pdf"
  self.assertEqual(len(PdfReader(pdf).pages),3)
  manifest=load(OUT/"bundle-manifest.json")
  self.assertEqual(manifest["source_commit"],self.info["source_commit"])
  z=SITE/"downloads/prosperity-taiji-courts-p42-package.zip"
  with zipfile.ZipFile(z) as f:
   self.assertEqual(set(f.namelist()),set(manifest["files_sha256"])|{"prosperity-taiji-courts/bundle-manifest.json"})
   for name,hashValue in manifest["files_sha256"].items():
    self.assertEqual(hashlib.sha256(f.read(name)).hexdigest(),hashValue)
  for p in [SITE/"prosperity-taiji-courts.html",pdf,z,*OUT.iterdir()]:
   if p.is_file():
    relative=p.relative_to(SITE).as_posix()
    self.assertEqual(self.info["files_sha256"][relative],sha(p),relative)
 def test_previous_milestones_and_access_paths_remain(self):
  for old in ["index.html","prosperity-gate.html","prosperity-axis.html","prosperity-axis-sources.html"]:
   self.assertIn("prosperity-taiji-courts.html",(SITE/old).read_text(encoding="utf-8"),old)
  self.assertEqual(self.info["prosperity_gate"]["version"],"prosperity-gate-v3")
  self.assertEqual(self.info["prosperity_axis_source_audit"]["version"],"prosperity-axis-p41-source-audit")
  self.assertTrue((SITE/"prosperity-gate/sources/changhe-plan-native.jpeg").is_file())
if __name__=="__main__":unittest.main()
