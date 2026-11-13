"""Protect B7's group readings, event dates, and unchanged earlier map.

The fixture is assembled from tracked sources before the website build. Tests
check the resulting SVG and historical non-entailments, not only audit totals.
"""
import copy
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
from southeast_b6 import changed_master as southeast_master
from luonan_b7 import (
    ANCHORS, GROUPS, SIDECARS, changed_master, read_research,
    literary_plate, institutions_plate, markets_plate, layers_plate,
)


def triple(constraint):
    return constraint['subject'], constraint['relation'], constraint.get('object')


class LuonanB7(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups = load(ROOT / 'research/dual-b7/luonan-groups.json')
        cls.river = load(ROOT / 'research/dual-b7/luonan-river-markets.json')
        cls.data = read_research()
        cls.e = {e['id']: e for e in cls.data['evidence']}
        cls.entities = {e['id']: e for e in load(ROOT / 'data/entities.json')}
        cls.markers = load(ROOT / 'data/markers.json')
        cls.original_markers = copy.deepcopy(cls.markers)
        cls.positive = {triple(c) for e in cls.e.values() for c in e['constraints']}

        with tempfile.TemporaryDirectory(prefix='luoyang-b7-test-') as tmp:
            path = Path(tmp) / 'previous.svg'
            earlier, _ = palace_master(
                ROOT / 'assets/master-v24.svg', read_snapshot(), cls.markers, 'b2'
            )
            west_glyphs(world(earlier), cls.markers)
            ET.ElementTree(earlier).write(path, encoding='utf-8')
            earlier, _ = north_master(path, cls.markers)
            ET.ElementTree(earlier).write(path, encoding='utf-8')
            earlier, _ = west_roads_master(path, cls.markers)
            ET.ElementTree(earlier).write(path, encoding='utf-8')
            cls.previous, _ = southeast_master(path, cls.markers)
            ET.ElementTree(cls.previous).write(path, encoding='utf-8')
            cls.master, cls.audit = changed_master(path, cls.markers)

        cls.new_groups = [
            n for n in cls.master.iter() if n.get('data-batch') == 'dual-b7'
        ]
        cls.g = {n.get('id'): n for n in cls.new_groups}

    def test_01_25_records_keep_attributed_text_and_one_source_family(self):
        expected_groups = {f'LG{i:02}' for i in range(1, 12)}
        expected_river = {f'LR{i:02}' for i in range(1, 15)}
        self.assertEqual(set(self.e), expected_groups | expected_river)
        self.assertEqual(len(self.data['evidence']), 25)
        self.assertEqual({e['id'] for e in self.groups['evidence']}, expected_groups)
        self.assertEqual({e['id'] for e in self.river['evidence']}, expected_river)
        sources = {s['id']: s for s in self.data['sources']}
        self.assertEqual(set(sources), {'Z3', 'F3', 'Z2', 'F2'})
        self.assertEqual(len({s['url'] for s in sources.values()}), 4)
        self.assertEqual({s['family'] for s in sources.values()}, {'L'})
        self.assertEqual(self.data['source_family_count'], 1)
        # A person and two quoted aliases are named literals, not new site IDs.
        named_literals = {'张景仁', '吳人坊', '永橋市'}
        for eid, e in self.e.items():
            with self.subTest(evidence=eid):
                self.assertEqual(e['source_region'], 'R11')
                self.assertIn(e['quote_source'], e['sources'])
                self.assertTrue(set(e['sources']) <= sources.keys())
                self.assertTrue(set(e['entities']) <= self.entities.keys())
                for field in ['quote', 'quote_locator', 'textual_layer', 'reading', 'drawing', 'limit']:
                    self.assertTrue(e[field], field)
                for c in e['constraints']:
                    self.assertIn(c['subject'], self.entities.keys() | named_literals)
                    if c.get('object') is not None:
                        self.assertIn(c['object'], self.entities.keys() | named_literals)
                    for target in c.get('object_ids', []) + c.get('objects', []):
                        self.assertIn(target, self.entities)

    def test_02_same_R11_box_and_no_ancient_coordinates_or_new_entities(self):
        old = next(r for r in load(ROOT / 'data/regions.json') if r['code'] == 'R11')
        for part in [self.groups, self.river]:
            self.assertEqual(part['region']['id'], 'L10')
            self.assertEqual(part['region']['source_region'], 'R11')
            self.assertEqual(part['region']['bbox'], old['bbox'])
            self.assertEqual(part['region']['bbox'], [4100, 8720, 4350, 2230])
            self.assertEqual(part['ancient_absolute_positions_added'], 0)
        self.assertTrue(all(e['geographic_coordinates'] is None for e in self.e.values()))
        self.assertEqual(self.data['ancient_absolute_positions_added'], 0)
        self.assertEqual(len(self.entities), 339)

    def test_03_seven_reading_groups_keep_old_anchors_and_plural_membership(self):
        expected = {
            'wards': {'li_guizheng', 'li_guide', 'li_muhua', 'li_muyi'},
            'guesthouses': {'guan_jinling', 'guan_yanran', 'guan_fusang', 'guan_yanzi'},
            'temples': {'v3_guizheng', 'v3_puti'},
            'fish': {'market_fish', 'house_xiaobaoyin'},
            'sitong': {'market_sitong'},
        }
        self.assertEqual({k: set(v) for k, v in GROUPS.items()}, expected)
        self.assertEqual(len(self.new_groups), 7)
        for key, ids in expected.items():
            with self.subTest(group=key):
                marker = next(m for m in self.markers if set(m['ids']) == ids)
                self.assertEqual(marker['kind'], 'group')
                self.assertEqual(ANCHORS[key], (marker['x'], marker['y']))
                g = self.g[f'luonan-{key}-b7']
                self.assertEqual(set(g.get('data-entity-ids').split()), ids)
                self.assertEqual(g.get('data-locating-mode'),
                                 'group' if key in ['wards', 'guesthouses'] else 'nonspatial_annotation')
                self.assertIsNone(g.get('data-entity-id'))
        self.assertEqual(self.audit['reading_groups_changed'], 7)
        self.assertFalse(self.audit['anchors_moved'])

    def test_04_all_original_map_children_survive_unchanged_even_when_wrapped(self):
        before = Counter(ET.tostring(n) for n in world(self.previous))
        after = Counter(ET.tostring(n) for n in world(self.master).iter())
        self.assertFalse(before - after)
        self.assertEqual(world(self.master).attrib, world(self.previous).attrib)
        # Unchanged child coordinates would still move if their new wrapper did.
        for g in self.new_groups:
            self.assertIsNone(g.get('transform'), g.get('id'))
        self.assertEqual(self.audit['original_children_preserved'], sum(before.values()))

    def test_05_prior_batch_counts_and_subtrees_are_unchanged(self):
        expected = {'dual-b1': 7, 'dual-b2': 8, 'dual-b3': 1,
                    'dual-b4': 4, 'dual-b5': 11, 'dual-b6': 20}
        counts = Counter(n.get('data-batch') for n in self.master.iter())
        for batch, count in expected.items():
            with self.subTest(batch=batch):
                self.assertEqual(counts[batch], count)
                before = [ET.tostring(n) for n in self.previous.iter() if n.get('data-batch') == batch]
                after = [ET.tostring(n) for n in self.master.iter() if n.get('data-batch') == batch]
                self.assertEqual(after, before)

    def test_06_179_targets_unchanged_and_no_individual_site_glyphs_added(self):
        self.assertEqual(len(self.markers), 179)
        self.assertEqual(self.markers, self.original_markers)
        self.assertEqual(load(ROOT / 'data/manifest.json')['place_markers'], 179)
        old_ids = Counter(n.get('data-entity-id') for n in self.previous.iter()
                          if n.get('data-entity-id'))
        new_ids = Counter(n.get('data-entity-id') for n in self.master.iter()
                          if n.get('data-entity-id'))
        self.assertEqual(new_ids, old_ids)
        for g in self.new_groups:
            self.assertEqual(g.get('data-footprint'), 'false')
            self.assertIn('pointer-events:none', g.get('style', '').replace(' ', ''))
        self.assertEqual(self.audit['new_individual_site_glyphs'], 0)
        self.assertEqual(self.audit['new_interactive_targets'], 0)
        # Actual DOM target totals are checked separately in the browser.

    def test_07_sidecars_bridge_and_altar_keep_their_nonlocating_roles(self):
        expected = {'house_xiaozhengde', 'v3_guizheng', 'v3_puti', 'market_fish',
                    'house_xiaobaoyin', 'market_sitong', 'fang_whiteelephant',
                    'fang_lion', 'v3_yong_huabiao'}
        self.assertEqual(set(SIDECARS), expected)
        for eid in expected - {'v3_yong_huabiao'}:
            self.assertIn('nonspatial_annotation', self.entities[eid]['modes'])
        self.assertIn('annotation', self.entities['v3_yong_huabiao']['modes'])
        self.assertIn('direction_reference', self.entities['altar_yuanqiu']['modes'])
        self.assertEqual(self.g['luonan-direction-b7'].get('data-locating-mode'), 'direction_reference')
        self.assertEqual(self.g['luonan-bridge-b7'].get('data-locating-mode'), 'bridge_annotation')
        for eid in ['bridge_yong', 'road_siyi', 'house_xiaozhengde', 'v3_yong_huabiao', 'water_yi']:
            self.assertFalse(any(eid in m['ids'] for m in self.markers), eid)
        self.assertFalse(self.audit['bridge_interactive_marker_present'])
        self.assertEqual(self.audit['bridge_drawing_anchor'], [6100, 9000])

    def test_08_catalogue_is_not_internal_order_or_opposite_street_pairs(self):
        e = self.e['LG02']
        self.assertFalse(e['catalogue_order_is_spatial'])
        self.assertFalse(e['spatial_order_established'])
        self.assertFalse(e['one_to_one_opposite_street_established'])
        self.assertFalse(e['individual_footprints_allowed'])
        members = set(e['catalogue_hall_ids']) | set(e['catalogue_ward_ids'])
        self.assertEqual(members, set(GROUPS['wards']) | set(GROUPS['guesthouses']))
        for eid in GROUPS['guesthouses']:
            self.assertIn((eid, 'east_of', 'road_siyi'), self.positive)
            self.assertIn('group', self.entities[eid]['modes'])
        for eid in GROUPS['wards']:
            self.assertIn((eid, 'west_of', 'road_siyi'), self.positive)
            self.assertIn('group', self.entities[eid]['modes'])
        self.assertFalse(any(s in members and o in members for s, _, o in self.positive))

    def test_09_only_two_institutional_transitions_explicitly_say_three_years(self):
        expected = {
            ('guan_jinling', 'li_guizheng'): 3,
            ('guan_yanran', 'li_guide'): 3,
            ('guan_fusang', 'li_muhua'): None,
            ('guan_yanzi', 'li_muyi'): None,
        }
        processes = [self.e['LG03']['process'], self.e['LG04']['process'],
                     *self.e['LG07']['processes']]
        self.assertEqual(processes, self.groups['institutional_correspondences'])
        self.assertEqual({(p['accommodation_entity_id'], p['subsequent_residential_ward_id']):
                          p['waiting_period_years'] for p in processes}, expected)
        for p in processes:
            self.assertEqual(p['waiting_period_explicit'], p['waiting_period_years'] is not None)
            self.assertFalse(p['is_spatial_opposition'])
            self.assertIsNone(p['journey_geometry'])
        self.assertFalse(self.e['LG07']['omitted_waiting_period_means_immediate'])
        self.assertFalse(self.e['LG07']['all_four_waiting_periods_explicitly_three_years'])

    def test_10_court_rank_seasonal_service_and_external_names_do_not_make_sites(self):
        self.assertFalse(self.e['LG05']['court_rank_is_geographic_relation'])
        self.assertFalse(self.e['LG05']['event_year_is_building_date'])
        self.assertIsNone(self.e['LG05']['individual_housing_date_ce'])
        self.assertIsNone(self.e['LG05']['individual_waiting_period_years'])
        self.assertEqual(self.e['LG06']['seasonal_pattern']['arrival'], '秋')
        self.assertEqual(self.e['LG06']['seasonal_pattern']['departure'], '春')
        self.assertFalse(self.e['LG06']['permanent_residence_for_all_established'])
        self.assertFalse(self.e['LG08']['external_names_are_luoyang_sites'])
        self.assertEqual(self.e['LG08']['new_local_entity_ids'], [])
        self.assertIsNone(self.e['LG09']['exact_household_count'])
        self.assertFalse(self.e['LG09']['household_grid_allowed'])
        self.assertFalse(self.e['LG09']['specific_changhe_gate_identification_established'])
        self.assertEqual(set(self.e['LG09']['forbidden_existing_entity_identifications']),
                         {'ic_changhe_palace', 'gate_changhe_west'})

    def test_11_zhengde_arrival_readings_do_not_date_residence_or_temple(self):
        e = self.e['LG10']
        readings = {x['year_ce']: x for x in e['arrival_date_readings']}
        self.assertEqual(set(readings), {522, 523})
        self.assertEqual(readings[523]['layer'], 'adopted_primary_text')
        self.assertEqual(set(readings[523]['sources']), {'Z3', 'F3'})
        self.assertIn('commentary', readings[522]['layer'])
        self.assertFalse(e['independent_chronicle_check'])
        self.assertIsNone(e['arrival_year_selected'])
        self.assertFalse(e['arrival_year_is_temple_foundation_year'])
        self.assertIsNone(e['house_construction_completion_year_ce'])
        self.assertIsNone(e['process']['waiting_period_in_this_case_years'])

    def test_12_two_undated_temples_do_not_inherit_group_years_or_shared_address(self):
        gz, pt = self.e['LG11'], self.e['LR11']
        self.assertIn(('house_xiaozhengde', 'predecessor_of', 'v3_guizheng'), self.positive)
        self.assertIn(('v3_guizheng', 'within', 'li_guizheng'), self.positive)
        self.assertIn(('v3_puti', 'inside', 'li_muyi'), self.positive)
        self.assertEqual(gz['temple_temporal_state'], 'undated')
        self.assertFalse(gz['inherits_group_event_year'])
        self.assertFalse(gz['three_year_rule_sets_temple_date'])
        self.assertIsNone(gz['temple_foundation_year_ce'])
        self.assertIsNone(gz['temple_completion_year_ce'])
        self.assertFalse(gz['tower_added_to_main'])
        self.assertEqual(pt['main_temporal_state'], 'undated')
        self.assertIsNone(pt['temple_foundation_year_ce'])
        self.assertFalse(pt['narrative_event_dates_temple'])
        self.assertFalse(pt['shared_marker_proves_adjacency'])
        self.assertFalse(pt['shared_marker_proves_same_compound'])
        for eid in ['v3_guizheng', 'v3_puti']:
            self.assertEqual(self.entities[eid]['temporal_state'], 'undated')
        self.assertEqual(self.g['luonan-temples-b7'].get('data-locating-mode'), 'nonspatial_annotation')

    def test_13_baoyin_former_residence_is_not_zhengdes_conversion(self):
        e = self.e['LR06']
        self.assertTrue(e['move_precedes_main_516_528'])
        self.assertFalse(e['occupancy_continues_into_main_period_established'])
        self.assertFalse(e['converted_to_guizheng_temple_established'])
        self.assertEqual(e['different_person_from'], '蕭正德')
        self.assertIsNone(e['move_year_ce'])
        self.assertIn(('house_xiaobaoyin', 'inside', 'li_guizheng'), self.positive)
        self.assertIn(('house_xiaobaoyin', 'occupant_later_resided_in', 'li_yongan'), self.positive)
        self.assertNotIn(('house_xiaobaoyin', 'predecessor_of', 'v3_guizheng'), self.positive)

    def test_14_fish_market_ward_does_not_inherit_heading_or_neighbors(self):
        e = self.e['LR07']
        self.assertEqual(e['ward_id'], 'li_guizheng')
        self.assertIn(('market_fish', 'inside', 'li_guizheng'), self.positive)
        self.assertFalse(e['inherit_position_from_paragraph_heading'])
        self.assertFalse(e['fish_market_in_xiaoyi_established'])
        self.assertFalse(e['fish_market_north_of_small_market_established'])
        self.assertFalse(e['adjacent_to_xiaobaoyin_house_established'])
        self.assertFalse(self.e['LR08']['market_moves_with_person'])
        for c in self.positive:
            if c[0] == 'market_fish':
                self.assertEqual(c, ('market_fish', 'inside', 'li_guizheng'))

    def test_15_sitong_alias_does_not_merge_markets_or_supply_a_roadside(self):
        e = self.e['LR10']
        self.assertIn(('market_sitong', 'south_of', 'luoshui'), self.positive)
        self.assertIn(('market_sitong', 'also_called', '永橋市'), self.positive)
        self.assertIn(('li_guizheng', 'also_called', '吳人坊'), self.positive)
        self.assertFalse(e['fish_sitong_identity_established'])
        self.assertFalse(e['merge_authorized'])
        self.assertIsNone(e['market_sitong_roadside'])
        self.assertIsNone(e['market_sitong_ward'])
        self.assertFalse(e['adjacent_to_bridge_established'])
        self.assertIsNone(e['distance_to_bridge'])
        self.assertFalse(any(s == 'market_sitong' and o in {'road_siyi', 'bridge_yong'}
                             for s, _, o in self.positive))
        self.assertFalse(self.e['LR12']['roadside_inherited_by_sitong'])

    def test_16_arrival_era_and_household_variants_are_not_market_date_or_area(self):
        e = self.e['LR08']
        self.assertEqual(e['date_readings']['Z2']['era'], '正光年初')
        self.assertEqual(e['date_readings']['F2']['era'], '景明年初')
        self.assertIsNone(e['selected_arrival_year_ce'])
        self.assertIsNone(e['market_foundation_year_ce'])
        population = self.e['LR09']['population_statement']
        self.assertEqual(population['main_text'], '三千餘家')
        self.assertEqual(population['annotator_cited_variant'], '三十餘家')
        self.assertIsNone(population['adopted_exact_households'])
        self.assertFalse(population['independent_census'])
        self.assertFalse(self.e['LR09']['quantity_converted_to_area'])
        self.assertEqual(self.e['LR09']['river_channels_added'], 0)

    def test_17_bridge_type_distance_and_commemoration_do_not_supply_geometry_or_date(self):
        bridge, commemoration, huabiao = self.e['LR01'], self.e['LR02'], self.e['LR03']
        self.assertEqual(bridge['bridge_type'], 'floating_bridge')
        distance = next(c for c in bridge['constraints'] if c['object'] == 'gate_xuanyang')
        self.assertEqual(distance['distance_original'], '四里')
        self.assertIsNone(distance['distance_metric'])
        for field in ['bridge_construction_year_ce', 'specific_pontoon_count', 'bridge_width', 'river_width']:
            self.assertIsNone(bridge[field])
        self.assertEqual(commemoration['event']['date_range_ce'], [518, 520])
        self.assertFalse(commemoration['event']['bridge_construction_dated'])
        self.assertIsNone(commemoration['bridge_construction_year_ce'])
        self.assertFalse(commemoration['rhetoric_generates_network_edges'])
        self.assertEqual(huabiao['component']['height_original'], '二十丈')
        self.assertIsNone(huabiao['component']['height_metric'])
        self.assertIsNone(huabiao['component']['pillar_count_from_main_text'])
        self.assertTrue(huabiao['annotation_only'])

    def test_18_region_reference_and_ritual_do_not_locate_altar_or_crossing_route(self):
        e = self.e['LR04']
        self.assertTrue(e['direction_reference_only'])
        self.assertIsNone(e['altar_footprint'])
        self.assertIsNone(e['altar_absolute_position'])
        self.assertEqual(e['river_channels_added'], 0)
        self.assertFalse(e['region_bbox_is_geographic'])
        self.assertFalse(self.e['LG01']['continuous_straight_road_established'])
        self.assertFalse(self.e['LR05']['procession_crosses_yong_established'])
        self.assertFalse(self.e['LR05']['ordinary_crossing_equals_procession'])
        self.assertIn(('v3_jingming', 'procession_to', 'gate_xuanyang'), self.positive)
        self.assertFalse(any(r == 'procession_to' and 'bridge_yong' in [s, o]
                             for s, r, o in self.positive))

    def test_19_two_animal_wards_have_separate_events_and_no_simultaneous_scene(self):
        wards, elephant, lion = self.e['LR12'], self.e['LR13'], self.e['LR14']
        for eid in ['fang_whiteelephant', 'fang_lion']:
            self.assertIn((eid, 'east_of', 'road_siyi'), self.positive)
            self.assertIn((eid, 'south_of', 'bridge_yong'), self.positive)
        self.assertIsNone(wards['internal_order'])
        self.assertFalse(wards['adjacency_between_wards_established'])
        self.assertEqual(elephant['events'][0]['year_ce'], 509)
        self.assertEqual(elephant['events'][0]['kind'], 'tribute_arrival')
        self.assertFalse(elephant['arrival_is_ward_foundation'])
        self.assertIsNone(elephant['ward_foundation_year_ce'])
        self.assertFalse(elephant['animal_presence_all_main_years_established'])
        self.assertTrue(lion['post_heyin_event'])
        self.assertEqual(lion['annotator_correspondence_year_ce'], 530)
        self.assertEqual(lion['return_order_year_ce'], 531)
        self.assertFalse(lion['actual_return_home_established'])
        self.assertFalse(lion['lion_alive_in_main_period_allowed'])
        self.assertIsNone(lion['ward_foundation_year_ce'])

    def test_20_rendered_relations_expose_group_and_market_limits(self):
        institutions = ''.join(institutions_plate().itertext())
        self.assertEqual(institutions.count('三年已后'), 2)
        self.assertEqual(institutions.count('本段未重写“三年”'), 2)
        self.assertIn('不证明每馆与对应里恰好隔街相对', institutions)
        self.assertIn('季节性入侍', institutions)
        markets = ''.join(markets_plate().itertext())
        for phrase in ['鱼鳖市不能继承', '当前保留独立记录', '不表示它在御道东',
                       '圜丘只作南向参照', '神龟作颂是文辞活动年代']:
            self.assertIn(phrase, markets)
        literary = ''.join(literary_plate(self.master, self.data['region']).itertext())
        self.assertIn('制度对应不证明一一对街', literary)
        self.assertIn('寺期未定继续旁注', literary)
        self.assertIn('框线、文字排布与类型图符均不代表院界或比例', literary)

    def test_21_rendered_dates_do_not_turn_arrival_into_construction(self):
        plate = ''.join(layers_plate().itertext())
        for phrase in ['正文正光四年到来；周注另引三年', '宅转寺没有独立纪年',
                       '不以523加三年推出526建寺', '“后”为周校补',
                       '归正里为旧宅附见', '寺院成立年未定', '509不是建坊年',
                       '531诏遣归，途中被杀', '桥的创建年、华表独立营建年未明']:
            self.assertIn(phrase, plate)
        for key, phrase in [('temples', '两寺同框仅供阅读，不能推出彼此邻接'),
                            ('fish', '萧宝夤旧宅：后迁城内永安里'),
                            ('sitong', '御道路侧与桥旁距离未记')]:
            self.assertIn(phrase, ''.join(self.g[f'luonan-{key}-b7'].itertext()))


if __name__ == '__main__':
    unittest.main()
