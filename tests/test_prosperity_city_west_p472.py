"""Regress the paired readings, identities, native drawings and publication chain."""
import json
import re
import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from test_prosperity_city_common_p470 import Markup

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT/"_site"
sys.path.insert(0,str(ROOT/"tools"))
from city_west_472_data import B5, CATALOG, P1, build_data
from verify_city_west_p472 import PAGE, check_preservation, verify


def read(path):
    return json.loads(path.read_bytes())


class WestCity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_data()
        cls.info = read(SITE/"build-info.json")
        cls.page = Markup((SITE/PAGE).read_text())
        cls.rows = {r["id"]:r for r in cls.data["records"]}

    def test_all_24_pairs_keep_editions_locators_manual_review_and_drawing_separate(self):
        old = read(ROOT/B5)["evidence"]
        current = {p["key"]:p for p in read(ROOT/P1)["records"] if p["batch"]=="B5"}
        self.assertEqual(read(SITE/"west-472/readings.json"),self.data)
        for r, b in zip(self.data["records"],old,strict=True):
            p = current["B5:"+b["id"]]
            self.assertEqual((r["b5"],r["p1"]),(b,p))
            self.assertIsNone(p["manual_context_review"])
            self.assertEqual(p["affected_entity_ids"],b["entities"])
            self.assertEqual(r["working_reading"]["p1_key"],p["key"])
            self.assertEqual([s["declared_source_id"] for s in p["source_checks"]],[b["quote_source"]])
            card = self.page.by_id(b["id"])["text"]
            for value in (p["legacy_quote"],b["reading"],b["limit"],b["quote_locator"],r["working_reading"]["map_reading"],
                          r["working_reading"]["period_label"],b["temporal_note"] or "",*(v["reading"] for v in b["variants"])):
                self.assertIn(value,card)
            for check in p["source_checks"]:
                for seg in check["segments"]:
                    self.assertIn(seg["line_start"]+"–"+seg["line_end"],card)
        self.assertEqual(self.data["source_family_count"],1)
        self.assertEqual(len(self.data["text_sources"]),6)
        self.assertEqual({s["key"] for s in self.data["p1_snapshots"]},{"B0077-1","B0077-4","B0077-5"})

    def test_review_groups_and_object_ids_cover_each_record_and_original_period(self):
        groups = self.data["groups"]
        expected = {"order":[1,2],"changhe":[3,4,5,6,7,8,9,10,22],"xiyang":[11,12,13,14,15,16,19,20,21,23,24],"ximing":[17,18]}
        self.assertEqual({g["id"]:g["evidence_ids"] for g in groups},{g:[f"WR{i:02d}" for i in seq] for g,seq in expected.items()})
        catalog = {e["id"]:e for e in read(ROOT/CATALOG)}
        self.assertEqual(len(catalog),339)
        for e in self.data["entities"]:
            self.assertEqual(e["temporal_state"],catalog[e["id"]]["temporal_state"])
            self.assertEqual(e["records"],[k for k,r in self.rows.items() if e["id"] in r["b5"]["entities"]])
            card = self.page.by_id("entity-"+e["id"])["text"]
            self.assertIn(e["period_label"],card)
            if not e["feature_id"]:
                self.assertIn("未定位",card)
        self.assertEqual(self.data["legacy_canvas"]["bbox"],[1180,2400,3330,3850])

    def test_huai_huan_late_towers_and_house_identity(self):
        eight = self.rows["WR08"]
        self.assertEqual(eight["p1"]["quotation_class"],"edited_reading_with_visible_markers")
        self.assertIn("捨宅〔立〕也，……懷所居之堂，上置七佛",self.page.by_id("WR08")["text"])
        self.assertIn("范",self.page.by_id("WR08")["text"])
        for key, words in {"WR04":["三里","一里"],"WR08":["环","七佛"],"WR09":["532—534","层数"],
                           "WR13":["普泰末","寺门"],"WR18":["五层","528","竣工"],
                           "WR20":["529","败散"],"WR21":["三层","王典御"],"WR24":["同一性","待考"]}.items():
            for word in words:
                self.assertIn(word,self.page.by_id(key)["text"])
        self.assertEqual(self.rows["WR18"]["b5"]["entities"],["w_chongjue"])
        self.assertEqual(self.rows["WR24"]["b5"]["entities"],["w_baima_xiyang","r_baima_chanjian"])
        self.assertIn("城阳王徽宅〔后宣忠〕",self.page.by_id("entity-w_xuanzhong")["text"])

    def test_download_and_inline_drawings_differ_only_in_link_destination(self):
        html = (SITE/PAGE).read_text()
        for inline, filename in zip(re.findall(r"<svg\b.*?</svg>",html,re.S),["west-source.svg","west-relations.svg"],strict=True):
            external = (SITE/"west-472"/filename).read_text().rstrip("\n")
            self.assertEqual(external.replace("https://mechgouki.github.io/luoyang-city/"+PAGE+"#","#"),inline)
            plate = ET.fromstring(inline)
            self.assertTrue(all(self.page.by_id(a.get("href")[1:]) for a in plate.findall(".//*[@href]")))
        self.assertEqual(self.rows["WR02"]["p1"]["affected_entity_ids"],["gate_changhe_west","ic_changhe_palace"])
        self.assertEqual(self.page.by_id("entity-gate_changhe_west")["attrs"]["data-records"],"WR01 WR02 WR03")

    def test_relation_plate_distinguishes_distance_outside_gate_from_road_side(self):
        plate = ET.fromstring((SITE/"west-472/west-relations.svg").read_bytes())
        for record, wording in (("WR19","门外一里／道南"), ("WR23","门外三里／道南"), ("WR17","门外一里／道北")):
            box, = plate.findall(f'.//*[@data-reading="{record}"]')
            self.assertIn(wording,"".join(box.itertext()))
            constraint = self.rows[record]["b5"]["constraints"]
            self.assertEqual(constraint[0]["relation"],"outside_gate")
            self.assertIsNone(constraint[0]["distance_endpoints"])
            self.assertNotIn("distance",constraint[1])

    def test_site_downloads_and_both_prior_release_chains(self):
        report = verify(self.info,lambda path:(SITE/path).read_bytes())
        self.assertEqual(report["preservation"],{"frozen_files":28,"protected_in_build":33,"previous_offline_members":17,
                                                  "previous_pages":2,"previous_manifests":2,"previous_bundles":2})
        self.assertEqual(report["distinct_resources"],45)

    def test_unlisted_change_to_a_prior_page_or_nested_manifest_fails(self):
        baseline = read(ROOT/"tests/fixtures/p471-published-hashes.json")
        for filename,old,new in (("prosperity-city-north.html","北门","新门"),
                                 ("north-471/bundle-manifest.json","p471-entry","p472-entry")):
            def get(path):
                raw = (SITE/path).read_bytes()
                return raw.replace(old.encode(),new.encode(),1) if path == filename else raw
            with self.subTest(filename=filename), self.assertRaises(AssertionError):
                check_preservation(self.info,get,baseline)
