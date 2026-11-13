"""Protect B6's evidence boundaries and preservation of the earlier map.

The SVG fixture is built from tracked inputs, so these tests also run before
the website build. No cached _site output or publication step is required.
"""
import copy
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from dual_cartography import load, world, changed_master as palace_master
from dual_release import read_snapshot
from west_b3 import west_glyphs
from north_b4 import changed_master as north_master
from west_roads_b5 import changed_master as west_roads_master
from southeast_b6 import (
    NODES, GATES, SIDECARS, changed_master, read_research,
    literary_plate, relations_plate, layers_plate,
)


def triple(constraint):
    return tuple(constraint[key] for key in ('subject', 'relation', 'object'))


class SoutheastB6(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inner = load(ROOT / 'research/dual-b6/southeast-inner.json')
        cls.outer = load(ROOT / 'research/dual-b6/southeast-outer.json')
        cls.data = read_research()
        cls.e = {e['id']: e for e in cls.data['evidence']}
        cls.entities = {e['id']: e for e in load(ROOT / 'data/entities.json')}
        cls.markers = load(ROOT / 'data/markers.json')
        cls.original_markers = copy.deepcopy(cls.markers)
        cls.positive = {
            triple(c) for e in cls.e.values() for c in e['constraints']
        }

        # Exercise the real B6 conversion against the earlier drawing stages,
        # rather than trusting the conversion's self-reported audit counts.
        with tempfile.TemporaryDirectory(prefix='luoyang-b6-test-') as tmp:
            path = Path(tmp) / 'previous.svg'
            earlier, _ = palace_master(
                ROOT / 'assets/master-v24.svg', read_snapshot(), cls.markers, 'b2'
            )
            west_glyphs(world(earlier), cls.markers)
            ET.ElementTree(earlier).write(path, encoding='utf-8')
            earlier, _ = north_master(path, cls.markers)
            ET.ElementTree(earlier).write(path, encoding='utf-8')
            cls.previous, _ = west_roads_master(path, cls.markers)
            ET.ElementTree(cls.previous).write(path, encoding='utf-8')
            cls.master, cls.audit = changed_master(path, cls.markers)

        cls.new_glyphs = [
            n for n in cls.master.iter() if n.get('data-batch') == 'dual-b6'
        ]
        cls.glyph_by_id = {n.get('data-entity-id'): n for n in cls.new_glyphs}

    def test_01_34_records_keep_regions_and_attributed_sources(self):
        expected_inner = {f'EI{i:02}' for i in range(1, 17)}
        expected_outer = {f'EO{i:02}' for i in range(1, 19)}
        self.assertEqual(set(self.e), expected_inner | expected_outer)
        self.assertEqual(len(self.data['evidence']), 34)
        self.assertEqual({e['id'] for e in self.inner['evidence']}, expected_inner)
        self.assertEqual({e['id'] for e in self.outer['evidence']}, expected_outer)
        sources = {s['id']: s for s in self.data['sources']}
        self.assertEqual(set(sources), {'Z1', 'F1', 'Z2', 'F2'})
        self.assertEqual(len({s['url'] for s in sources.values()}), 4)
        self.assertEqual({s['family'] for s in sources.values()}, {'L'})
        self.assertEqual(self.data['source_family_count'], 1)
        for eid, e in self.e.items():
            with self.subTest(evidence=eid):
                self.assertEqual(e['source_region'], 'R08' if eid in expected_inner else 'R09')
                self.assertIn(e['quote_source'], e['sources'])
                self.assertTrue(set(e['sources']) <= sources.keys())
                self.assertTrue(set(e['entities']) <= self.entities.keys())
                for field in ['quote', 'quote_locator', 'textual_layer', 'reading', 'drawing', 'limit']:
                    self.assertTrue(e[field], field)
                for c in e['constraints']:
                    self.assertIn(c['subject'], self.entities)
                    if c['object'] is not None:
                        self.assertIn(c['object'], self.entities)
                    for candidate in c.get('object_candidates', []):
                        self.assertIn(candidate, self.entities)

    def test_02_old_region_boxes_and_no_ancient_coordinates(self):
        old = {r['code']: r for r in load(ROOT / 'data/regions.json')}
        for part, rid, lid in [(self.inner, 'R08', 'L08'), (self.outer, 'R09', 'L09')]:
            self.assertEqual(part['region']['id'], lid)
            self.assertEqual(part['region']['source_region'], rid)
            self.assertEqual(part['region']['bbox'], old[rid]['bbox'])
            self.assertEqual(part['source_family_count'], 1)
            self.assertEqual(part['ancient_absolute_positions_added'], 0)
        self.assertEqual(self.data['ancient_absolute_positions_added'], 0)
        self.assertTrue(all(e['geographic_coordinates'] is None for e in self.e.values()))

    def test_03_only_17_old_nodes_and_three_old_gates_are_changed(self):
        expected_nodes = {
            'ic_daoguan', 'ic_taicang_wei', 'ic_zhaoyi', 'ic_songming',
            'ic_xiufan', 'ic_jinglin_garden', 'ic_jinglin', 'v2_zhuangyan',
            'v2_qintaishangjun', 'v2_zhengshi', 'office_dianyu', 'v2_pingdeng',
            'tomb_suqin', 'v2_baoming', 'market_small', 'v2_jingning', 'v2_jianzhong',
        }
        expected_gates = {'gate_dongyang', 'gate_qingyang', 'gate_kaiyang'}
        self.assertEqual(set(NODES), expected_nodes)
        self.assertEqual(set(GATES), expected_gates)
        self.assertEqual(len(self.new_glyphs), 20)
        self.assertEqual(set(self.glyph_by_id), expected_nodes | expected_gates)
        self.assertEqual(self.audit['nodes_replaced'], 17)
        self.assertEqual(self.audit['gate_symbols_added'], 3)
        self.assertFalse(self.audit['anchors_moved'])
        for eid, glyph in self.glyph_by_id.items():
            with self.subTest(entity=eid):
                marker = next(m for m in self.markers if eid in m['ids'])
                self.assertEqual(marker['kind'], 'node' if eid in expected_nodes else 'gate')
                placed = next(n for n in glyph.iter() if n.get('transform', '').startswith('translate('))
                match = re.match(r'translate\(([-\d.]+)[ ,]+([-\d.]+)\)', placed.get('transform'))
                self.assertIsNotNone(match)
                self.assertEqual(tuple(map(float, match.groups())), (marker['x'], marker['y']))
                self.assertEqual(glyph.get('data-footprint'), 'false')

    def test_04_prior_batch_counts_and_contents_are_unchanged(self):
        expected = {'dual-b1': 7, 'dual-b2': 8, 'dual-b3': 1, 'dual-b4': 4, 'dual-b5': 11}
        counts = Counter(n.get('data-batch') for n in self.master.iter())
        for batch, count in expected.items():
            with self.subTest(batch=batch):
                self.assertEqual(counts[batch], count)
                before = [ET.tostring(n) for n in self.previous.iter() if n.get('data-batch') == batch]
                after = [ET.tostring(n) for n in self.master.iter() if n.get('data-batch') == batch]
                self.assertEqual(after, before)

    def test_05_unselected_map_children_are_preserved_byte_for_byte(self):
        before, after = list(world(self.previous)), list(world(self.master))
        replaced_classes = {entry[0] for entry in NODES.values()}
        self.assertEqual(len(after), len(before) + 1)  # One container for three gate types.
        self.assertEqual(after[-1].get('id'), 'southeast-glyphs-b6')
        for i, old in enumerate(before):
            if old.get('class') not in replaced_classes:
                self.assertEqual(ET.tostring(after[i]), ET.tostring(old), i)

    def test_06_five_sidecars_do_not_become_new_site_glyphs(self):
        expected = {'ic_hutong', 'ic_yuanhui', 'ic_yishou', 'ic_guangming', 'v2_guijue'}
        self.assertEqual(set(SIDECARS), expected)
        self.assertTrue(expected.isdisjoint(NODES))
        self.assertTrue(expected.isdisjoint(self.glyph_by_id))
        for eid in expected:
            self.assertEqual(next(m for m in self.markers if eid in m['ids'])['kind'], 'group')

    def test_07_179_target_registry_is_unchanged_and_glyphs_are_pointer_transparent(self):
        self.assertEqual(len(self.markers), 179)
        self.assertEqual(self.markers, self.original_markers)
        self.assertEqual(load(ROOT / 'data/manifest.json')['place_markers'], 179)
        parents = {child: parent for parent in self.master.iter() for child in parent}
        for glyph in self.new_glyphs:
            n, transparent = glyph, False
            while n is not None:
                if n.get('pointer-events') == 'none' or 'pointer-events:none' in n.get('style', '').replace(' ', ''):
                    transparent = True
                    break
                n = parents.get(n)
            self.assertTrue(transparent, glyph.get('data-entity-id'))
        # DOM target totals are separately exercised by the browser checks.

    def test_08_two_taicangs_and_two_pools_remain_distinct(self):
        for eid, pair in [
            ('EI03', ('ic_taicang_wei', 'ic_taicang_jin')),
            ('EI05', ('ic_zhaoyi_pool', 'ic_diquan')),
        ]:
            e = self.e[eid]
            self.assertEqual(e['identity_policy'], 'distinct_existing_entities')
            self.assertEqual(set(e['identity_pair']), set(pair))
            self.assertTrue(set(pair) <= self.entities.keys())
            self.assertIn((pair[0], 'not_identical', pair[1]), self.positive)
        self.assertNotIn('ic_taicang_jin', self.glyph_by_id)
        self.assertNotIn('ic_diquan', self.glyph_by_id)
        self.assertNotIn('ic_zhaoyi_pool', self.glyph_by_id)

    def test_09_office_order_stays_attributed_to_commentary(self):
        e = self.e['EI03']
        west = next(c for c in e['constraints'] if triple(c) == ('ic_daoguan', 'west_of', 'ic_taicang_wei'))
        self.assertEqual(west['basis'], 'commentary_citation')
        for office in ['ic_daoguan', 'ic_taicang_wei']:
            north = next(c for c in e['constraints'] if triple(c) == (office, 'north_of', 'ic_dongyang_avenue'))
            self.assertEqual(north['basis'], 'direct')
            self.assertEqual(NODES[office][5], 'office')

    def test_10_temple_relative_directions_do_not_transfer_road_sides(self):
        for eid, subject, reference, road, forbidden_relation in [
            ('EI12', 'ic_songming', 'ic_xiufan', 'ic_qingyang_avenue', 'north_of'),
            ('EI14', 'ic_jinglin_garden', 'ic_jinglin', 'ic_kaiyang_avenue', 'west_of'),
        ]:
            e = self.e[eid]
            self.assertFalse(e['route_side_transfer_allowed'])
            self.assertIn((subject, 'west_of', reference), self.positive)
            self.assertNotIn((subject, forbidden_relation, road), self.positive)
            self.assertFalse(any(c['subject'] == subject and c['object'] == road for c in e['constraints']))
            self.assertIn((subject, forbidden_relation, road), {triple(c) for c in e['forbidden_inferences']})

    def test_11_yonghe_referent_is_an_interpretation_not_direct_text(self):
        c = next(c for c in self.e['EI13']['constraints'] if c['subject'] == 'ic_yonghe')
        self.assertEqual(triple(c), ('ic_yonghe', 'north_of', 'ic_xiufan'))
        self.assertEqual(c['basis'], 'interpretation')
        self.assertTrue(c['referent_note'])
        self.assertNotIn(('ic_yonghe', 'north_of', 'ic_qingyang_avenue'), self.positive)

    def test_12_shared_ward_does_not_make_dianyu_the_eastern_neighbor(self):
        e = self.e['EO07']
        self.assertEqual({triple(c) for c in e['constraints']}, {
            ('office_dianyu', 'within', 'li_jingyi'),
            ('v2_zhengshi', 'within', 'li_jingyi'),
        })
        self.assertFalse(e['east_of_zhengshi_established'])
        self.assertIsNone(e['relative_position_with_zhengshi'])
        for c in e['non_entailment_constraints']:
            self.assertNotIn(triple(c), self.positive)
        self.assertEqual(NODES['office_dianyu'][5], 'office')

    def test_13_tomb_corner_is_not_inherited_by_baoming(self):
        e = self.e['EO14']
        self.assertIn(('tomb_suqin', 'northwest_corner_of', 'li_xiaoyi'), self.positive)
        self.assertIn(('v2_baoming', 'near', 'tomb_suqin'), self.positive)
        self.assertNotIn(('v2_baoming', 'northwest_corner_of', 'li_xiaoyi'), self.positive)
        self.assertEqual(e['northwest_corner_applies_to'], 'tomb_suqin')
        self.assertFalse(e['baoming_at_ward_northwest_corner_established'])
        self.assertFalse(e['tomb_owner_archaeologically_confirmed'])
        self.assertIsNone(e['tomb_geometry'])

    def test_14_pingdeng_tower_is_late_with_two_unmerged_completion_readings(self):
        e = self.e['EO11']
        component = e['component']
        self.assertEqual(component['construction_start_year_ce'], 532)
        self.assertEqual(set(component['completion_year_candidates_ce']), {533, 534})
        self.assertIsNone(component['completion_year_selected'])
        self.assertTrue(all(y > 528 for y in component['completion_year_candidates_ce']))
        self.assertFalse(component['draw_in_main'])
        self.assertFalse(e['main_period_tower_allowed'])
        self.assertFalse(e['construction_start_is_completion'])
        self.assertEqual(self.e['EO10']['attestation_year_ce'], 527)
        self.assertEqual(NODES['v2_pingdeng'][5], 'temple')
        self.assertFalse(NODES['v2_pingdeng'][6])
        self.assertTrue(all(not c['tower_added_to_master'] for c in self.audit['changes'] if c['type'] != 'gate'))

    def test_15_baoming_dating_retains_the_same_name_identity_condition(self):
        e = self.e['EO15']
        self.assertEqual(e['identity_policy'], 'existing_candidate_link_identity_not_resolved')
        self.assertTrue(e['identity_assumption_required_for_dating'])
        self.assertFalse(e['independent_pre528_attestation_of_tomb_side_record'])
        self.assertIn('取决于', e['temporal_note'])
        self.assertEqual(sum(n.get('data-entity-id') == 'v2_baoming' for n in self.new_glyphs), 1)

    def test_16_undated_temples_and_post_conversion_residence_remain_distinct(self):
        for eid in ['ic_zhaoyi', 'ic_songming', 'ic_xiufan', 'ic_jinglin', 'v2_zhuangyan']:
            self.assertEqual(NODES[eid][5], 'temple')
            self.assertTrue(NODES[eid][6])
            self.assertEqual(self.glyph_by_id[eid].get('data-temporal-display'), 'undated')
        self.assertEqual(NODES['v2_jianzhong'][5], 'house')
        self.assertEqual(self.glyph_by_id['v2_jianzhong'].get('data-temporal-display'), 'house-before-temple')
        self.assertEqual(self.e['EO13']['date_lower_bound_ce'], 531)
        self.assertIsNone(self.e['EO13']['date_upper_bound_ce'])
        self.assertEqual(self.e['EO18']['date_range_ce'], [528, 530])
        self.assertTrue(self.e['EO18']['after_heyin_event'])
        self.assertIsNone(self.e['EO18']['completion_year_ce'])

    def test_17_rendered_relations_keep_non_entailments_visible(self):
        plate = ''.join(relations_plate().itertext())
        for phrase in [
            '宜寿里“寺南”暂按愿会回指', '但标为解释', '不能自动继承道北',
            '正文未给两者相对方位', '寺不自动继承里角', '寺西之园与御道的关系未记',
        ]:
            self.assertIn(phrase, plate)
        inner = ''.join(literary_plate(self.master, self.inner['region']).itertext())
        self.assertIn('愿会仅明确在池西南', inner)
        self.assertNotIn('池西南愿会、宜寿里与光明寺', inner)

    def test_18_rendered_dates_and_named_components_do_not_date_whole_temples(self):
        plate = ''.join(layers_plate().itertext())
        for phrase in [
            '532始造五层塔', '533／534', '愿会“五重”指神桑，不是五层塔',
            '胡统五重塔随旁注', '修梵金刚是造像', '房内小型祇洹精舍不另造寺址',
            '晋代佛像铭不是建寺纪年', '永熙时段属周注推定',
            '景林石铭未记年，普泰初属任官语境',
        ]:
            self.assertIn(phrase, plate)
        self.assertIn('只归所引像铭', self.e['EI09']['temporal_note'])
        self.assertIn('任官语境', self.e['EI16']['temporal_note'])


if __name__ == '__main__':
    unittest.main()
