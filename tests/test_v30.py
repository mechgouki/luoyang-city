"""Terrain numerical semantics. Synthetic planes are confined to unit tests."""
import unittest,sys,math
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import terrain_v30 as t
class TerrainSemantics(unittest.TestCase):
 def test_flat_slope(self):
  s,h=t.derivatives(np.ones((12,13))*100);self.assertTrue(np.allclose(s[1:-1,1:-1],0));self.assertTrue(np.allclose(h[1:-1,1:-1],math.sqrt(.5)))
 def test_east_gradient(self):
  z=np.tile(np.arange(15)*3.,(15,1));s,_=t.derivatives(z);self.assertTrue(np.allclose(s[1:-1,1:-1],math.degrees(math.atan(.1))))
 def test_north_gradient(self):
  z=np.tile((-np.arange(15)*6.)[:,None],(1,15));s,_=t.derivatives(z);self.assertTrue(np.allclose(s[1:-1,1:-1],math.degrees(math.atan(.2))))
 def test_plane_gradient_both_axes(self):
  y,x=np.mgrid[:15,:15];s,_=t.derivatives(3.*x+6.*y);self.assertAlmostEqual(s[7,7],math.degrees(math.atan(math.hypot(.1,.2))))
 def test_no_zero_height_for_void(self):
  z=np.ones((20,20))*200;z[10,10]=np.nan;s,h=t.derivatives(z);self.assertTrue(np.isnan(s[9:12,9:12]).all());self.assertTrue(np.isnan(h[9:12,9:12]).all())
 def test_boundary_derivatives_masked(self):
  s,h=t.derivatives(np.ones((10,10)));self.assertTrue(np.isnan(s[0]).all());self.assertTrue(np.isnan(h[:,-1]).all())
 def test_shade_bounds(self):
  y,x=np.mgrid[:20,:20];s,h=t.derivatives((x*15-y*12).astype(float));self.assertGreaterEqual(np.nanmin(h),0);self.assertLessEqual(np.nanmax(h),1)
 def test_positive_spacing(self):
  with self.assertRaises(ValueError):t.derivatives(np.ones((3,3)),0)
 def test_constant_smoothing(self):self.assertTrue(np.allclose(t.smooth(np.ones((30,30))*175,3),175))
 def test_smoothing_does_not_fill_missing(self):
  z=np.ones((50,50));z[25,25]=np.nan;self.assertTrue(np.isnan(t.smooth(z,3)[25,25]))
 def test_sources_are_pinned(self):
  self.assertEqual(len(t.SOURCES),3)
  for v in t.SOURCES.values():self.assertTrue(v['url'].startswith('https://'));self.assertEqual(len(v['sha256']),64)
 def test_not_native_resolution_claim(self):self.assertEqual(t.CRS,'EPSG:32649');self.assertEqual(t.CELL,30);self.assertEqual(t.SIGMA,90)
 def test_authorized_window(self):self.assertEqual(t.BBOX,[112.35,34.5,112.95,34.95])
 def test_source_attribution(self):self.assertIn('Copernicus WorldDEM-30',t.NOTICE);self.assertIn('liability',t.LIABILITY)
 def test_graph_not_transformed(self):
  code=Path(t.__file__).read_text();self.assertIn("'historical_registered_nodes':0,'geometry':None",code)
 def test_no_sinkfill(self):
  code=Path(t.__file__).read_text();self.assertNotIn('import richdem',code);self.assertNotIn('fill_depressions(',code)
if __name__=='__main__':unittest.main()
