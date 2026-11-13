"""Protect evidence distinctions, historical anchors and the known west-label regression."""
import sys,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from dual_cartography import load
from north_b4 import ANCHORS,TEMPLE_CLASSES,gates_plate,membership_plate
from west_b3 import relation_page

class NorthB4(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d=load(ROOT/'research/dual-b4/north-gates.json')
  cls.e={e['id']:e for e in cls.d['evidence']}
  cls.entities={e['id'] for e in load(ROOT/'data/entities.json')}
 def test_01_source_identity_and_quote_attribution(self):
  self.assertEqual(set(self.e),{f'NG{i:02}' for i in range(1,17)})
  source_ids={s['id'] for s in self.d['sources']}
  self.assertEqual(self.d['source_family_count'],1)
  for e in self.e.values():
   self.assertIn(e['quote_source'],e['sources'])
   self.assertTrue(set(e['sources'])<=source_ids)
   self.assertTrue(set(e['entities'])<=self.entities)
   self.assertTrue(e['quote_locator'] and e['quote'] and e['reading'] and e['drawing'] and e['limit'])
 def test_02_no_ancient_geographic_registration(self):
  self.assertEqual(self.d['ancient_absolute_positions_added'],0)
  self.assertTrue(all(e['geographic_coordinates'] is None for e in self.e.values()))
 def test_03_existing_anchors_and_region_identity(self):
  markers=load(ROOT/'data/markers.json')
  for eid,xy in ANCHORS.items():
   m=[m for m in markers if eid in m['ids']];self.assertEqual(len(m),1)
   self.assertEqual((m[0]['x'],m[0]['y']),xy)
  self.assertEqual(self.d['region']['id'],'L06')
  x,y,w,h=self.d['region']['bbox']
  for eid in ['gate_daxia','gate_guangmo','ic_jinyong','gate_chengming','n_wenyi']:
   m=next(m for m in markers if eid in m['ids'])
   self.assertTrue(x<=m['x']<=x+w and y<=m['y']<=y+h,eid)
 def test_04_daxia_layer_count_remains_a_selected_reading(self):
  e=self.e['NG02']
  self.assertEqual(e['claim_status'],'selected_editorial_reading')
  self.assertIn('†',e['drawing'])
  self.assertIn('本批',e['drawing'])
  self.assertTrue(e['variants'])
 def test_05_two_fields_are_not_merged_or_oriented(self):
  front=self.e['NG05'];conversion=self.e['NG06']
  self.assertIn('n_yuewuchang',front['entities'])
  self.assertIn('n_guangfeng',conversion['entities'])
  relation=next(c for c in front['constraints'] if c['relation']=='in_front_of')
  self.assertIsNone(relation['absolute_direction'])
  self.assertIn('不能与禅虚寺前阅武场无证合并',conversion['limit'])
 def test_06_high_ground_is_not_a_modern_coordinate(self):
  e=self.e['NG08'];self.assertIn('地形高顯',e['quote'])
  self.assertIn('现代',e['limit']);self.assertIsNone(e['geographic_coordinates'])
 def test_07_front_and_membership_do_not_create_addresses(self):
  self.assertIn('不是北面第三门',self.e['NG13']['reading'])
  self.assertIn('不拆成两个',self.e['NG12']['drawing'])
  self.assertIn('无序',self.e['NG16']['drawing'])
  a=''.join(gates_plate().itertext());b=''.join(membership_plate().itertext())
  self.assertIn('三层†',a);self.assertIn('朝向未定',a)
  self.assertIn('不列为第三座北门',b);self.assertIn('不枚举栋数',b)
 def test_08_west_shouqiu_rendered_direction_regression(self):
  text=''.join(relation_page().itertext())
  self.assertIn('延酤／退酤以西，张方沟以东',text)
  self.assertNotIn('西自延酤',text)
  w=next(e for e in load(ROOT/'research/dual-b3/west-market.json')['evidence'] if e['id']=='W14')
  self.assertIn('东西二里',w['reading'])

if __name__=='__main__':unittest.main()
