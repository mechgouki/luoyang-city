"""Semantic checks are separate from UI and deployment checks."""
import json,sys,unittest,itertools
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from network_v27 import network,path,enabled_edges,event_position,QUERIES

class Networks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.g=network();cls.q={q['id']:q for q in QUERIES}
  cls.data=json.loads((ROOT/'research/v2.7/passages.json').read_text())
 def result(self,q,enabled=(),families=('L','W')):return path(self.g,self.q[q],enabled,families)
 def test_node_ids_are_unique(self):
  self.assertEqual(len(self.g['nodes']),len({n['id'] for n in self.g['nodes']}))
 def test_all_edges_have_real_passage_references(self):
  ids={p['id'] for p in self.data['passages']}
  for e in self.g['edges']:self.assertTrue(set(e['evidence'])<=ids)
 def test_water_edge_endpoints_are_only_water_reaches(self):
  kinds={n['id']:n['kind'] for n in self.g['nodes']}
  for e in self.g['edges']:
   if e['kind'] in {'flow','overflow','identity_water'}:self.assertEqual([kinds[e['a']],kinds[e['b']]],['water','water'])
 def test_primary_water_sequence_is_supported(self):
  r=self.result('Q1');self.assertEqual(r['status'],'supported_under_conditions');self.assertEqual(r['edge_ids'],['WF1','WF2','WF3'])
 def test_east_cross_source_join_requires_explicit_identity(self):
  self.assertEqual(self.result('Q2')['status'],'not_established')
  self.assertEqual(self.result('Q2',['J1'])['premises'],['J1'])
 def test_southern_canal_identification_is_not_default(self):
  self.assertEqual(self.result('Q3')['status'],'not_established')
  self.assertEqual(self.result('Q3',['J2'])['premises'],['J2'])
 def test_bridge_identity_never_creates_water_flow(self):
  self.assertEqual(self.result('Q10',['J3'])['status'],'supported_under_conditions')
  self.assertEqual(self.result('Q8',['J3'])['status'],'not_established')
 def test_alignment_does_not_prove_confluence(self):
  self.assertEqual(self.result('Q4',['J1','J2','J3','FLOOD'])['status'],'not_established')
 def test_crossing_does_not_allow_flow_from_the_bridge(self):
  q={'start':'L_yong','end':'L_luoyong','mode':'flow'}
  self.assertEqual(path(self.g,q)['status'],'not_established')
 def test_flood_relief_requires_the_condition(self):
  self.assertEqual(self.result('Q7')['status'],'not_established')
  self.assertEqual(self.result('Q7',['FLOOD'])['edge_ids'],['OVERFLOW'])
 def test_reach_name_does_not_merge_distinct_receiving_segments(self):
  q={'start':'W_yang_dong','end':'W_yang_qing','mode':'flow'}
  self.assertEqual(path(self.g,q,['J1','J2','J3'])['status'],'not_established')
 def test_flow_is_not_implicitly_reversed(self):
  q={'start':'W_mashi','end':'W_north','mode':'flow'}
  self.assertEqual(path(self.g,q)['status'],'not_established')
 def test_itinerary_scopes_cannot_be_mixed(self):
  self.assertEqual(self.result('Q5')['status'],'supported_under_conditions')
  self.assertEqual(self.result('Q6')['status'],'supported_under_conditions')
  self.assertEqual(self.result('Q9')['status'],'not_established')
 def test_source_ablation_removes_dependent_joins(self):
  for families in [('L',),('W',)]:
   self.assertEqual(self.result('Q2',['J1'],families)['status'],'not_established')
   self.assertEqual(self.result('Q10',['J3'],families)['status'],'not_established')
 def test_all_480_query_results_have_checkable_typed_certificates(self):
  count=0
  for bits in itertools.product([False,True],repeat=4):
   opts=[k for k,on in zip(['J1','J2','J3','FLOOD'],bits) if on]
   for fam in [('L','W'),('L',),('W',)]:
    active={e['id']:e for e in enabled_edges(self.g,opts,fam)}
    for q in QUERIES:
     r=path(self.g,q,opts,fam);count+=1
     if r['status']=='not_established':self.assertEqual(r['edge_ids'],[]);continue
     self.assertEqual(r['nodes'][0],q['start']);self.assertEqual(r['nodes'][-1],q['end'])
     self.assertEqual(len(r['nodes']),len(r['edge_ids'])+1)
     for i,aid in enumerate(r['edge_ids']):
      ed=active[aid];pair=r['nodes'][i:i+2]
      self.assertTrue(pair==[ed['a'],ed['b']] or ed['kind'].startswith('identity_') and pair==[ed['b'],ed['a']])
      if q['mode']=='flow':self.assertIn(ed['kind'],{'flow','overflow','identity_water'})
      if q['mode']=='route':self.assertEqual(ed['route_scope'],q['scope']);self.assertEqual(ed['kind'],'route')
  self.assertEqual(count,480)

class Events(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.events={e['id']:e for e in json.loads((ROOT/'research/v2.7/passages.json').read_text())['events']}
 def test_527_damage_belongs_only_to_jianchun_bridge(self):
  e=self.events['T04'];self.assertEqual(e['object'],'bridge_jianchun');self.assertNotEqual(e['object'],'bridge_yong')
 def test_tower_fire_does_not_apply_to_whole_temple(self):
  e=self.events['T05'];self.assertEqual(e['component'],'yongning_tower');self.assertEqual(e['scope'],'塔')
 def test_earlier_damage_does_not_create_547_persistent_damage_state(self):
  self.assertEqual(event_position(self.events['T04'],547),'past_event_later_state_unknown')
  self.assertEqual(event_position(self.events['T05'],547),'past_event_later_state_unknown')
 def test_start_year_window_is_not_completion(self):
  self.assertEqual(event_position(self.events['T03'],523),'year_inside_uncertain_event_window')
  self.assertEqual(event_position(self.events['T03'],526),'past_event_later_state_unknown')
 def test_future_event_does_not_prove_object_absence(self):
  self.assertEqual(event_position(self.events['T05'],528),'event_not_yet_in_recorded_window')
 def test_undated_to_this_day_is_not_forced_to_547(self):
  self.assertIsNone(self.events['T09']['start'])
  self.assertEqual(event_position(self.events['T09'],547),'undated_reference')
 def test_general_observation_has_no_individual_object(self):
  self.assertIsNone(self.events['T08']['object']);self.assertEqual(self.events['T08']['kind'],'aggregate_observation')
 def test_moving_stones_is_not_removing_school_site(self):
  self.assertEqual(self.events['T07']['object'],'v3_shijing');self.assertEqual(self.events['T07']['kind'],'relocation')
 def test_foundation_and_construction_start_are_different(self):
  self.assertNotEqual(self.events['T02']['kind'],self.events['T03']['kind'])
 def test_all_dated_events_have_original_era_labels(self):
  for e in self.events.values():
   self.assertTrue(e['original_date']);self.assertTrue(e['state_note'])
   if e['start'] is not None:self.assertLessEqual(e['start'],e['end'])

if __name__=='__main__':unittest.main()
