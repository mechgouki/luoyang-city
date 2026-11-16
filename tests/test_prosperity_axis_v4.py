"""Verify P4 measurement semantics, source lineage, phase separation and production assets."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
import zipfile

from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
SOURCE=ROOT/"research/prosperity-v4/axis-measurements.json"
OUT=SITE/"prosperity-axis"
VERSION="prosperity-axis-p4-metric-review"
SVG_NS="{http://www.w3.org/2000/svg}"

def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class P4AxisEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load(SOURCE)
        cls.published=load(OUT/"data.json")
        cls.info=load(SITE/"build-info.json")
        cls.html=(SITE/"prosperity-axis.html").read_text(encoding="utf-8")

    def test_source_data_is_published_without_revision(self):
        self.assertEqual(self.published,self.data)
        self.assertEqual(self.data["version"],VERSION)
        self.assertEqual(self.info["prosperity_axis"]["version"],VERSION)
        self.assertEqual(self.info["prosperity_axis"]["source_commit"],self.info["source_commit"])
        self.assertEqual(self.info["prosperity_axis"]["atlas_pages"],3)

    def test_segment_chain_and_independent_measurement_both_preserved(self):
        rows=self.data["axis_segments"]
        self.assertEqual([x["length_m"] for x in rows],[95,80,300])
        self.assertTrue(all(x["measured_absolute_coordinates"] is False for x in rows))
        self.assertTrue(all(x["source_ids"]==["QIAN2012"] for x in rows))
        self.assertEqual(sum(x["length_m"] for x in rows),475)
        self.assertEqual(self.data["chain_sum_m"],475)
        self.assertEqual(self.data["independent_report"]["distance_m"],460)
        self.assertFalse(self.data["independent_report"]["same_reference_points_verified"])
        self.assertEqual(self.data["comparison_difference_m"],15)
        self.assertIn("not a demonstrated archaeological contradiction",self.data["comparison_status"])

    def test_gate_2_roads_and_architecture_not_promoted_to_map(self):
        gate=self.data["second_gate"]
        self.assertEqual((gate["foundation_ew_m"],gate["foundation_ns_m"]),(44.5,24))
        self.assertEqual(gate["passage_count"],3)
        self.assertFalse(gate["paired_que"])
        self.assertEqual(gate["ew_road_south_distance_report_m"],23)
        self.assertEqual(gate["ew_road_north_distance_report_m"],40)
        self.assertEqual(gate["ew_road_width_m_approx"],10)
        self.assertEqual(gate["north_south_paved_road_width_m"],[7.9,8.1])
        self.assertEqual(gate["cart_rut_separation_m_approx"],1.2)
        self.assertFalse(gate["road_reference_point_verified"])

    def test_three_gate_3_phases_not_merged(self):
        d=self.data["third_gate"]
        self.assertEqual(d["early"]["kind"],"surviving_not_original_full_footprint")
        self.assertEqual((d["early"]["surviving_ew_m_approx"],d["early"]["surviving_ns_m_approx"]),(40,10))
        self.assertEqual((d["middle"]["ew_m_approx"],d["middle"]["ns_m_approx"]),(55,45))
        self.assertEqual(d["middle"]["kind"],"later_disturbance_ram_earth")
        self.assertEqual(d["late"]["columns_east_west_rows"],14)
        self.assertNotEqual(d["early"]["period"],d["late"]["period"])
        self.assertIn("不得合并",self.data["temporal_warning"])

    def test_taiji_shapes_preserve_asymmetry_and_unknown_west_hall(self):
        t=self.data["taiji"]
        m=t["main_hall"]
        self.assertEqual([m["north_width_m"],m["south_width_m"]],[102.3,98.4])
        self.assertEqual(m["ns_depth_m_reported"],[59,61.5])
        self.assertEqual([t["east_hall"]["ew_m"],t["east_hall"]["ns_m"]],[48,23])
        self.assertEqual(t["east_hall"]["reported_gap_from_main_east_m"],14)
        self.assertFalse(t["east_hall"]["relative_ns_alignment_verified"])
        self.assertTrue(t["west_hall"]["exists_recorded"])
        self.assertFalse(t["west_hall"]["footprint_measured_in_this_batch"])
        self.assertIsNone(t["west_hall"]["geometry"])

    def test_original_map_links_and_source_dependency_flags(self):
        ids={x["id"] for x in self.data["sources"]}
        self.assertTrue({"QIAN2012","NARA2013","XU2020","LUOYANG2024","UNESCO-S37"}<=ids)
        self.assertTrue(all(x["url"].startswith("https://") for x in self.data["sources"]))
        figs={x["id"]:x for x in self.data["original_figures"]}
        self.assertEqual(figs["FIG-NARA-69"]["figure_number"],"图69")
        self.assertFalse(figs["FIG-NARA-69"]["registration_approved"])
        self.assertTrue(figs["FIG-NARA-69"]["unresolved_figure_label"])
        self.assertTrue(figs["FIG-UNESCO-S37"]["embedded_in_prior_p3"])
        self.assertTrue(self.data["source_independence_note"])

    def test_zero_common_controls_is_hard_invariant(self):
        reg=self.data["registration"]
        self.assertEqual(reg["verified_common_controls"],0)
        self.assertFalse(reg["local_to_city_verified"])
        self.assertEqual(reg["absolute_points_added"],0)
        self.assertFalse(reg["ancient_ground_surface_confirmed"])
        self.assertFalse(reg["roof_heights_confirmed"])
        for x in self.data["axis_segments"]:
            self.assertNotIn("geographic_coordinates",x)
            self.assertNotIn("wgs84",x)

    def test_generated_svg_are_three_distinct_nonempty_documents(self):
        for fn,marker in [
            ("axis-segments.svg","475 m"),
            ("third-gate-phases.svg","55"),
            ("taiji-dimensions.svg","102.3")]:
            path=OUT/fn
            node=ET.parse(path).getroot()
            self.assertEqual(node.tag,SVG_NS+"svg")
            self.assertEqual(node.get("viewBox"),"0 0 1440 840")
            self.assertIn(marker,path.read_text(encoding="utf-8"))
            self.assertGreater(len(path.read_bytes()),1300)

    def test_page_exposes_original_sources_and_caveats(self):
        self.assertIn('id="distance"',self.html)
        self.assertIn('id="phases"',self.html)
        self.assertIn('id="taiji"',self.html)
        self.assertIn('id="originals"',self.html)
        self.assertIn("独立共同控制点",self.html)
        self.assertIn("475",self.html)
        self.assertIn("460",self.html)
        self.assertIn("残部",self.html)
        self.assertIn("西堂",self.html)
        self.assertIn("宫城中轴",self.html)
        for src in self.data["sources"]:
            self.assertIn(src["url"].replace("&","&amp;"),self.html)
        self.assertIn('data-phase="early"',self.html)
        self.assertIn('data-phase="middle"',self.html)
        self.assertIn('data-phase="late"',self.html)

    def test_pdf_and_zip_manifest_reproducible(self):
        pdf=SITE/"downloads/prosperity-axis-v4-atlas.pdf"
        zip_path=SITE/"downloads/prosperity-axis-v4-package.zip"
        self.assertEqual(len(PdfReader(pdf).pages),3)
        manifest=load(OUT/"bundle-manifest.json")
        self.assertEqual(manifest["version"],VERSION)
        self.assertEqual(manifest["source_commit"],self.info["source_commit"])
        with zipfile.ZipFile(zip_path) as archive:
            names=set(archive.namelist())
            self.assertIn("prosperity-axis.html",names)
            self.assertIn("prosperity-axis/data.json",names)
            self.assertIn("prosperity-axis/measurements.csv",names)
            self.assertIn("prosperity-axis/bundle-manifest.json",names)
            self.assertEqual(set(manifest["files_sha256"])|{"prosperity-axis/bundle-manifest.json"},names)
            for name,expected in manifest["files_sha256"].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(),expected,name)

    def test_entry_links_and_prior_source_plan_are_preserved(self):
        self.assertEqual(self.info["prosperity_gate"]["version"],"prosperity-gate-v3")
        self.assertIn("prosperity-axis.html",(SITE/"prosperity-gate.html").read_text(encoding="utf-8"))
        self.assertIn("prosperity-axis.html",(SITE/"index.html").read_text(encoding="utf-8"))
        self.assertIn("prosperity-axis.html",(SITE/"prosperity.html").read_text(encoding="utf-8"))
        self.assertTrue((SITE/"prosperity-gate/sources/changhe-plan-native.jpeg").is_file())
        self.assertEqual(self.info["files_sha256"]["prosperity-gate/sources/changhe-plan-native.jpeg"],
                         sha(SITE/"prosperity-gate/sources/changhe-plan-native.jpeg"))

    def test_release_index_has_all_new_hashes(self):
        self.assertEqual(load(SITE/"release.json")["prosperity_axis_version"],VERSION)
        for path in [SITE/"prosperity-axis.html", SITE/"downloads/prosperity-axis-v4-atlas.pdf",
                     SITE/"downloads/prosperity-axis-v4-package.zip",*OUT.glob("*")]:
            if not path.is_file():continue
            rel=path.relative_to(SITE).as_posix()
            self.assertEqual(self.info["files_sha256"][rel],sha(path),rel)

if __name__=="__main__":
    unittest.main()
