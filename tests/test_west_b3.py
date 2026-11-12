"""West B3 rebase checks: existing B1 and palace B2 must not be redefined."""
import unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from dual_cartography import B1,B2,load
from west_b3 import LABELS

class WestB3(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d=load(ROOT/'research/dual-b3/west-market.json')
  cls.markers=load(ROOT/'data/markers.json')
  cls.ids={e['id'] for e in load(ROOT/'data/entities.json')}
 def test_01_namespace_is_separate(self):
  self.assertEqual(self.d['version'],'dual-west-b3')
  self.assertEqual(self.d['region']['id'],'L05')
  self.assertEqual(self.d['region']['bbox'],[250,4750,4250,3850])
  self.assertEqual(len(self.d['evidence']),16)
  self.assertEqual({e['id'] for e in self.d['evidence']},{f'W{i:02}' for i in range(1,17)})
 def test_02_no_new_geocoordinates(self):
  self.assertEqual(self.d['ancient_absolute_positions_added'],0)
  self.assertTrue(all(e['geographic_coordinates'] is None for e in self.d['evidence']))
 def test_03_quotations_and_decisions(self):
  for e in self.d['evidence']:
   self.assertTrue(e['quote'] and e['reading'] and e['limit'])
   self.assertTrue(set(e['entities'])<=self.ids,e['id'])
 def test_04_source_family_not_independent(self):
  self.assertEqual({s['family'] for s in self.d['sources']},{'L'})
 def test_05_all_icons_reuse_old_anchors(self):
  for eid,x,y,_,_ in LABELS:
   matches=[m for m in self.markers if eid in m['ids']]
   self.assertEqual(len(matches),1,eid)
   self.assertEqual((matches[0]['x'],matches[0]['y']),(x,y),eid)
 def test_06_no_published_b2_entities(self):
  self.assertTrue(set(eid for e in self.d['evidence'] for eid in e['entities']).isdisjoint(set(B2)))
  self.assertTrue(set(eid for e in self.d['evidence'] for eid in e['entities']).isdisjoint(set(B1)))
 def test_07_no_false_market_grid(self):
  self.assertIn('不等于正方形',next(e for e in self.d['evidence'] if e['id']=='W02')['limit'])
  self.assertIn('不等于所有',next(e for e in self.d['evidence'] if e['id']=='W16')['limit'])
 def test_08_royal_temple_membership_unlocated(self):
  e=next(e for e in self.d['evidence'] if e['id']=='W10')
  self.assertIn('台与寺',e['reading'])
  self.assertIsNone(e['geographic_coordinates'])
if __name__=='__main__':unittest.main()
