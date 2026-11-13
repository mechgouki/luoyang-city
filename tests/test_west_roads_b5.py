"""Protect B5's partial order, temporal boundaries and nonspatial records."""
import itertools,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from dual_cartography import load
from west_roads_b5 import NODES,GATES,SIDECARS,node_group,relations_plate,layers_plate

class WestRoadsB5(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.data=load(ROOT/'research/dual-b5/west-roads.json');cls.e={x['id']:x for x in cls.data['evidence']}
  cls.entities={x['id']:x for x in load(ROOT/'data/entities.json')};cls.markers=load(ROOT/'data/markers.json')
 def test_sources_and_existing_entities(self):
  self.assertEqual(set(self.e),{f'WR{i:02}' for i in range(1,25)})
  self.assertEqual(self.data['source_family_count'],1)
  sources={x['id'] for x in self.data['sources']}
  for e in self.e.values():
   self.assertTrue(set(e['entities'])<=self.entities.keys(),e['id'])
   self.assertIn(e['quote_source'],e['sources']);self.assertTrue(set(e['sources'])<=sources)
   self.assertTrue(all(e.get(k) for k in ['quote','quote_locator','reading','drawing','limit']))
 def test_no_ancient_positions_or_new_region_geometry(self):
  self.assertEqual(self.data['ancient_absolute_positions_added'],0)
  self.assertTrue(all(e['geographic_coordinates'] is None for e in self.e.values()))
  old=next(r for r in load(ROOT/'data/regions.json') if r['code']=='R02')
  self.assertEqual(self.data['region']['bbox'],old['bbox']);self.assertEqual(self.data['region']['id'],'L07')
 def test_only_old_node_anchors_and_distinct_city_gate(self):
  for eid,entry in NODES.items():
   m=next(m for m in self.markers if eid in m['ids'])
   self.assertEqual(m['kind'],'node');self.assertEqual((m['x'],m['y']),entry[1:3])
  for eid,xy in GATES.items():
   m=next(m for m in self.markers if eid in m['ids']);self.assertEqual((m['x'],m['y']),xy)
  self.assertNotIn('ic_changhe_palace',GATES)
  self.assertEqual(self.e['WR02']['identity_policy'],'distinct_existing_entities')
 def test_partial_order_allows_both_temples_first(self):
  constraints=self.e['WR06']['constraints'];ids=('w_dajue','w_rongjue','w_yongming')
  orders=[]
  for order in itertools.permutations(ids):
   pos={k:order.index(k) for k in ids}
   if all((pos[c['subject']]<pos[c['object']]) if c['relation']=='west_of' else (pos[c['subject']]>pos[c['object']]) for c in constraints):orders.append(order)
  self.assertEqual(set(orders),{('w_dajue','w_rongjue','w_yongming'),('w_dajue','w_yongming','w_rongjue')})
  self.assertFalse(self.e['WR06']['order_examples_are_geographic_solutions'])
 def test_sidecar_records_do_not_become_new_site_symbols(self):
  for eid in SIDECARS:
   self.assertNotIn(eid,NODES);self.assertIn('nonspatial_annotation',self.entities[eid]['modes'])
  self.assertEqual([(c['relation'],c['object']) for c in self.e['WR21']['constraints']],[('east_of','w_xuanzhong')])
  group=next(m for m in self.markers if 'w_chenliu' in m['ids'])
  self.assertIn('w_huyuanji',group['ids'])
  self.assertTrue({'w_chenliu','w_huyuanji'}.isdisjoint(NODES))
 def test_house_and_undated_temples_keep_distinct_states(self):
  self.assertEqual(NODES['w_xuanzhong'][5],'house')
  self.assertIn('城阳王徽宅',''.join(node_group('w_xuanzhong',NODES['w_xuanzhong']).itertext()))
  for eid in ['w_dajue','w_fayun','w_baoguang','w_baima_xiyang']:self.assertTrue(NODES[eid][6])
  plate=''.join(layers_plate().itertext())
  self.assertIn('532—534晚出；原文未给层数',plate)
  self.assertIn('528前是否完工未证',plate)
 def test_same_name_records_remain_unresolved(self):
  self.assertEqual(self.e['WR24']['identity_policy'],'two_records_same_site_unresolved')
  self.assertNotIn('r_baima_chanjian',NODES)
  self.assertIn('祗洹',self.e['WR15']['quote']);self.assertEqual(self.e['WR15']['entities'],['w_fayun'])
 def test_relation_plate_retains_non_entailments(self):
  plate=''.join(relations_plate().itertext())
  self.assertIn('先后仍开放',plate);self.assertIn('道南侧别不传给王典御',plate)
  self.assertIn('路侧未独立明记',plate);self.assertNotIn('西阳道北：法云',plate)

if __name__=='__main__':unittest.main()
