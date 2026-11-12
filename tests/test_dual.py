"""Data, semantic boundaries and unchanged-geometry regression checks."""
import unittest,sys,copy,hashlib,json,base64,zlib
from pathlib import Path
import xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from dual_cartography import B1,B2,NS,load,world,changed_master,diagram
from dual_release import read_snapshot
class DualMaps(unittest.TestCase):
 @classmethod
 def setUpClass(c):
  c.entities=load(ROOT/'data/entities.json');c.ids={e['id'] for e in c.entities};c.markers=load(ROOT/'data/markers.json');c.b1=load(ROOT/'research/dual-b1/decisions.json');c.b2=load(ROOT/'research/dual-b2/palace-gardens.json');c.snapshot=read_snapshot();c.original=E.parse(ROOT/'assets/master-v24.svg').getroot()
  c.master1,c.audit1=changed_master(ROOT/'assets/master-v24.svg',c.snapshot,c.markers,'b1');c.master2,c.audit2=changed_master(ROOT/'assets/master-v24.svg',c.snapshot,c.markers,'b2')
 def test_01_snapshot_full_hash(self):self.assertEqual(set(self.snapshot),set(B1))
 def test_02_b1_decisions_unique(self):self.assertEqual({x['id'] for x in self.b1['decisions']},{f'B{i:02}' for i in range(1,15)})
 def test_03_b2_evidence_unique(self):self.assertEqual({x['id'] for x in self.b2['evidence']},{f'G{i:02}' for i in range(1,17)})
 def test_04_references_valid(self):
  for e in self.b2['evidence']:self.assertTrue(set(e['entities'])<=self.ids,e['id'])
 def test_05_quotes_and_layers(self):
  for e in self.b2['evidence']:
   for k in ['quote','locator','layer','reading','drawing','sources']:self.assertTrue(e[k],(e['id'],k))
 def test_06_no_new_absolute_coordinates(self):self.assertTrue(all(e['geographic_coordinates'] is None for e in self.b2['evidence']))
 def test_07_same_source_family_not_double_votes(self):self.assertEqual({s['family'] for s in self.b2['sources']},{'L'})
 def test_08_seven_reviewed_groups(self):self.assertEqual(self.audit1['groups_changed'],7)
 def test_09_eight_new_groups(self):self.assertEqual(self.audit2['groups_changed'],15);self.assertTrue(set(B1).isdisjoint(B2))
 def test_10_all_other_world_children_preserved(self):
  a=list(world(self.original));b=list(world(self.master2));indices={e['index'] for e in self.audit2['changes']};self.assertEqual(len(a),len(b))
  for i in range(len(a)):
   if i not in indices:self.assertEqual(E.tostring(a[i]),E.tostring(b[i]),i)
 def test_11_existing_anchors_not_moved(self):
  for e in self.audit2['changes']:
   m=next(m for m in self.markers if e['entity_id'] in m['ids']);self.assertEqual(e['literary_xy'],[m['x'],m['y']]);self.assertFalse(e['anchor_moved'])
 def test_12_figures_are_not_footprints(self):
  for g in world(self.master2):
   if g.get('data-batch'):self.assertEqual(g.get('data-footprint'),'false')
 def test_13_unlocated_stays_unlocated(self):
  for eid in ['ic_diaotai_palace','ic_nailin','ic_maoci_hall','ic_dutang','ic_liushang','ic_fusang','ic_baiguo']:self.assertNotIn(eid,B2)
 def test_14_qingshu_baiguo_no_added_order(self):
  e=next(e for e in self.b2['evidence'] if e['id']=='G12');self.assertIn('彼此前后没有明文',e['reading']);self.assertNotIn('ic_baiguo',B2)
 def test_15_distinguish_same_named_hills(self):self.assertIn('v2_jingyangshan',self.ids);self.assertIn('ic_jingyang_hill',B2);self.assertNotIn('v2_jingyangshan',B2)
 def test_16_underwater_is_not_surface(self):
  s=''.join(diagram('water').itertext());self.assertIn('地下石窦',s);self.assertIn('不展开成任意两池全互联',s);self.assertIn('不视为全年水文',s)
 def test_17_alternative_membership_not_placement(self):
  a=E.tostring(diagram('platform'));b=E.tostring(diagram('hill'));self.assertNotEqual(a,b);self.assertIn('不新增点',''.join(diagram('hill').itertext()))
 def test_18_yongning_destruction_limited(self):self.assertIn('不由此推寺院整体毁尽',next(d for d in self.b1['decisions'] if d['id']=='B02')['limit'])
 def test_19_jianchun_event_not_eastbridge(self):self.assertIn('527',next(d for d in self.b1['decisions'] if d['id']=='B07')['after'])
 def test_20_scalar_grid_not_ancient_bounds(self):self.assertTrue(all(len(r['bbox'])==4 and r['bbox'][2]>0 and r['bbox'][3]>0 for r in self.b1['regions']+[self.b2['region']]))
 def test_21_quantities_not_grid_of_rooms(self):
  e=next(e for e in self.b2['evidence'] if e['id']=='G02');self.assertIn('不画五百',e['drawing'])
 def test_22_collective_four_not_new_fourth_location(self):self.assertIn('不据总数补',next(e for e in self.b2['evidence'] if e['id']=='G06')['reading'])
if __name__=='__main__':unittest.main()
