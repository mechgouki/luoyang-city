import importlib.util,json,unittest,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('dual',ROOT/'tools/dual_batch1.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
class Semantics(unittest.TestCase):
 def setUp(self):self.data=json.loads((ROOT/'research/dual1/changes.json').read_text())
 def test_scope_has_three_regions(self):self.assertEqual({r['code'] for r in self.data['regions']},{'R07','R04','R10'})
 def test_changes_unique(self):self.assertEqual(len({c['id'] for c in self.data['changes']}),10)
 def test_no_ancient_coordinate(self):self.assertTrue(all(c['ancient_lonlat'] is None for c in self.data['changes']))
 def test_every_change_has_provenance(self):self.assertTrue(all(c['before'] and c['after'] and c['source'] and c['evidence'] for c in self.data['changes']))
 def test_bridge_event_not_transferred(self):
  c={x['entity']:x for x in self.data['changes']};self.assertIn('N17',c['bridge_jianchun']['evidence']);self.assertNotIn('N17',c['bridge_eaststone']['evidence'])
 def test_school_not_movable_stone(self):self.assertNotIn('v3_shijing',[c['entity'] for c in self.data['changes']])
 def test_jingming_dashed_is_not_permanent_construction(self):
  c=next(c for c in self.data['changes'] if c['entity']=='v3_jingming');self.assertIn('竣工未证',c['note'])
 def test_flat_present_surface_class(self):
  z=np.zeros((81,81));c,r,v=d.terrain_classes(z,z,np.ones_like(z,bool));self.assertEqual(c[40,40],1);self.assertEqual(c[0,40],0)
 def test_high_slope_class_even_if_small_relief(self):
  z=np.zeros((81,81));c,_,_=d.terrain_classes(z,np.full_like(z,9),np.ones_like(z,bool));self.assertEqual(c[40,40],3)
 def test_relief_class(self):
  z=np.tile(np.arange(81)*2.,(81,1));c,r,v=d.terrain_classes(z,np.zeros_like(z),np.ones_like(z,bool));self.assertEqual(c[40,40],3);self.assertEqual(r[40,40],120)
 def test_transition_class(self):
  z=np.tile(np.arange(81)*.5,(81,1));c,_,_=d.terrain_classes(z,np.full_like(z,4),np.ones_like(z,bool));self.assertEqual(c[40,40],2)
 def test_missing_neighbour_not_classified(self):
  z=np.zeros((81,81));v=np.ones_like(z,bool);v[20,20]=False;c,_,_=d.terrain_classes(z,z,v);self.assertEqual(c[40,40],0)
 def test_yongning_has_two_components(self):
  r=d.tag('svg');d.glyph(r,0,0,'tower_hall','#000');boxes=r.findall('.//{'+d.NS+'}rect');self.assertTrue(float(boxes[0].get('y'))<float(boxes[1].get('y')))
 def test_direction_signs_of_bridges(self):
  r=d.tag('svg');d.glyph(r,0,0,'bridge_ns','#000');b=r.find('.//{'+d.NS+'}rect');self.assertGreater(float(b.get('height')),float(b.get('width')))
 def test_no_artificial_courtyard_outline(self):
  r=d.tag('svg');d.glyph(r,0,0,'temple','#000');paths=[x.get('d','') for x in r.findall('.//{'+d.NS+'}path')];self.assertTrue(any('M-91' in x and not x.endswith('Z') for x in paths))
 def test_focus_crops_are_schematic(self):
  self.assertTrue(all('focus_bbox' in r for r in self.data['regions']));self.assertIn('未配准',self.data['scope'])
if __name__=='__main__':unittest.main()
