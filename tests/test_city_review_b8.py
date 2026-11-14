"""Protect B8's correction layer, shared targets and untouched historical input."""
import copy
import hashlib
import re
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from city_audit_b8 import build_audit
from city_review_b8 import read_cases, enrich_ledger, changed_master, install_correction_notices
from dual_cartography import load, world, NS
from dual_release import report
import test_luonan_b7


class CityReviewB8(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_luonan_b7.LuonanB7.setUpClass()
        cls.previous = copy.deepcopy(test_luonan_b7.LuonanB7.master)
        cls.cases = read_cases()
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            path = site / 'assets/master-dual-b7-luonan.svg'
            path.parent.mkdir()
            ET.ElementTree(cls.previous).write(path, encoding='utf-8')
            cls.original = build_audit(site, source_commit='unit-review')
            cls.ledger = enrich_ledger(cls.original, cls.cases)
            cls.master, cls.audit = changed_master(path, cls.ledger)
        cls.rows = {r['id']: r for r in cls.ledger['entities']}
        cls.targets = {g.get('data-target-id'): g for g in cls.master.iter()
                       if g.get('class') == 'city-review-target'}

    def test_01_all_entities_keep_baseline_while_two_current_readings_are_explicit(self):
        self.assertEqual(len(self.ledger['entities']), 339)
        self.assertEqual(self.ledger['case_count'], 14)
        self.assertEqual(self.ledger['case_linked_entities'], 80)
        self.assertFalse(any(e['case_ids'] for e in self.original['entities']))
        self.assertEqual(sum(bool(e['current_review']) for e in self.ledger['entities']), 2)
        old = self.rows['v2_baoming']
        self.assertEqual(old['legacy_temporal_state'], 'attested_by_528')
        self.assertEqual(old['current_review']['temporal_label'], '前期身份有条件')
        self.assertIn('旧宅', self.rows['house_xiaobaoyin']['display_name'])
        self.assertNotEqual(self.rows['house_xiaobaoyin']['display_name'], self.rows['house_xiaobaoyin']['name'])
        self.assertTrue(all(e['geographic_coordinates'] is None for e in self.ledger['entities']))

    def test_02_review_rings_reuse_exact_existing_targets_and_preserve_old_geometry(self):
        self.assertEqual(len(self.targets), 179)
        self.assertEqual(self.audit['review_targets'], 179)
        self.assertEqual(self.audit['new_interactive_targets'], 0)
        self.assertFalse(self.audit['anchors_moved'])
        before = [ET.tostring(c) for c in world(self.previous)]
        after = [ET.tostring(c) for c in list(world(self.master))[:-1]]
        self.assertEqual(before, after)
        for row in self.ledger['entities']:
            for target in row['targets']:
                group = self.targets[target['id']]
                self.assertEqual(group.get('data-entity-ids').split(), target['member_ids'])
                circle = next(c for c in group if c.tag == '{'+NS+'}circle')
                self.assertEqual([float(circle.get('cx')),float(circle.get('cy'))],[target['x'],target['y']])
                self.assertEqual(group.get('data-footprint'),'false')

    def test_03_shared_area_is_one_target_for_two_entities_not_two_locations(self):
        a = self.rows['ic_donggong_reserved']
        b = self.rows['ic_taicang_jin']
        self.assertEqual(a['marker_state'], 'group_member')
        self.assertEqual(a['targets'], b['targets'])
        t = a['targets'][0]
        self.assertEqual(t['kind'], 'area')
        g = self.targets[t['id']]
        self.assertEqual(g.get('data-shared'), 'true')
        self.assertEqual(len([c for c in g if c.get('class') == 'b8-ring']),2)
        self.assertEqual(self.rows['w_yinian']['marker_state'],'individual')
        self.assertIn('nonspatial_annotation',self.rows['w_yinian']['drawing_status']['baseline_modes'])

    def test_04_no_target_does_not_create_missing_sites_or_lose_region_membership(self):
        self.assertEqual(self.rows['bridge_yong']['targets'],[])
        self.assertEqual(self.rows['road_siyi']['targets'],[])
        self.assertIn('R11',self.rows['bridge_yong']['explicit_focus_regions'])
        ids = {i for g in self.targets.values() for i in g.get('data-entity-ids').split()}
        self.assertNotIn('bridge_yong',ids)
        self.assertNotIn('road_siyi',ids)
        self.assertEqual(self.rows['bridge_yong']['crop_regions'],[])

    def test_05_cases_use_real_records_and_attribute_direct_and_context_objects(self):
        known = set(self.rows)
        sources = {s['id']:s for s in self.cases['sources']}
        refs = {(r['batch'],r['id'],r['path']) for e in self.ledger['entities'] for r in e['direct_evidence_refs']}
        self.assertEqual(self.cases['source_family_count'],1)
        self.assertEqual(len(sources),10)
        for c in self.cases['records']:
            self.assertTrue(set(c['entities']) <= known)
            for r in c['evidence_refs']:
                self.assertIn((r['batch'],r['id'],r['path']),refs)
            for s in c['source_checks']:
                self.assertIn(s['source_id'],sources)
                self.assertEqual(s['url'],sources[s['source_id']]['url'])
                self.assertTrue(set(s['direct_entity_ids']) <= known)
                self.assertTrue(set(s['context_entity_ids']) <= known)
            self.assertTrue(c['finding'] and c['action'] and c['remaining_question'])

    def test_06_g15_correction_preserves_original_and_separates_body_from_commentary(self):
        legacy = next(e for e in load(ROOT/'research/dual-b2/palace-gardens.json')['evidence'] if e['id']=='G15')
        e = next(c for c in self.cases['records'] if c['id']=='CB14')['errata']
        self.assertEqual(legacy['quote'],e['legacy_quote'])
        self.assertEqual(e['legacy_quote_kind'],'compressed_paraphrase_not_verbatim')
        self.assertEqual(e['correction_scope'],'quotation_layer')
        self.assertEqual(e['corrected_source_quote'],'若旱魃為害，穀水注之不竭；離畢滂潤，陽穀泄之不盈。')
        self.assertEqual(e['commentary_variant']['quote'],'穀當作渠。')
        self.assertFalse(e['commentary_variant']['changes_body_quote_silently'])
        self.assertTrue(e['original_data_preserved'])
        self.assertFalse(e['legacy_originals_are_overwritten'])

    def test_07_html_notice_preserves_exact_old_bytes_and_relative_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            site=Path(tmp);(site/'downloads').mkdir()
            originals={
                'dual-b2.html':'<!doctype html><html><body class="original"><p>原B2页</p></body></html>'.encode(),
                'downloads/dual-map-report.html':report({'regions':[], 'b1':{'decisions':[]}, 'b2':{'evidence':[]}}).encode()
            }
            for rel,body in originals.items():(site/rel).write_bytes(body)
            updates=install_correction_notices(site,self.cases)
            self.assertEqual(len(updates),2)
            for u in updates:
                original=originals[u['path']]
                self.assertEqual((site/u['archive_path']).read_bytes(),original)
                self.assertEqual(u['before_sha256'],hashlib.sha256(original).hexdigest())
                html=(site/u['path']).read_text()
                self.assertEqual(html.count('id="b8-quotation-correction"'),1)
                self.assertIn('G15',html)
                self.assertIn('case=CB14',html)
                stripped=re.sub(r'<section id="b8-quotation-correction".*?</section>','',html,count=1,flags=re.S)
                self.assertEqual(stripped.encode(),original)
                self.assertNotEqual(u['before_sha256'],u['after_sha256'])
            self.assertIn('../dual-city-review.html',(site/'downloads/dual-map-report.html').read_text())
            self.assertIn('./dual-city-review.html',(site/'dual-b2.html').read_text())


if __name__=='__main__':
    unittest.main()
