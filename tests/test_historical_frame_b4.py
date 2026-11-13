"""Guards against misrepresenting scan-grid calibration as geographic accuracy."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('historical_frame_b4', ROOT/'tools/historical_frame_b4.py')
frame = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frame)


class HistoricalFrameChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT/'research/dual-b4/historical-frame.json').read_text(encoding='utf-8'))

    def test_no_ground_or_ancient_registration_claim(self):
        d = self.data
        self.assertEqual(d['ancient_geographic_positions_added'],0)
        self.assertEqual(d['ancient_channels_added'],0)
        self.assertFalse(d['modern_dsm_modified'])
        self.assertFalse(d['ground_accuracy_assessed'])
        for sheet in d['sheets']:
            self.assertIsNone(sheet['horizontal_datum'])
            self.assertIsNone(sheet['geographic_crs'])

    def test_known_source_identity_and_observation_counts(self):
        expected={'NI49-7':'005a2b3c81f9135ab03739f2c8f52566c554f7c7af56c6bad5d9b47927970532',
                  'NI49-8':'d3525d1e86cc47536bb978721409e06852a07a3aee7298f69fb94b86cf94917c'}
        self.assertEqual({s['id'] for s in self.data['sheets']},set(expected))
        for sheet in self.data['sheets']:
            self.assertEqual(sheet['source_sha256'],expected[sheet['id']])
            self.assertEqual(len(sheet['fit_point_ids']),8)
            self.assertEqual(len(sheet['check_point_ids']),5)
            ids=[p['id'] for p in sheet['points']]
            self.assertEqual(len(ids),len(set(ids)))
            self.assertEqual(set(ids),set(sheet['fit_point_ids'])|set(sheet['check_point_ids']))
            self.assertFalse(set(sheet['fit_point_ids'])&set(sheet['check_point_ids']))

    def test_holdout_observations_cannot_change_fitted_model(self):
        for sheet in self.data['sheets']:
            before=frame.fit_sheet(sheet)
            modified=copy.deepcopy(sheet)
            for p in modified['points']:
                if p['role']=='check':
                    p['pixel_xy'][0]+=321
                    p['pixel_xy'][1]-=123
            after=frame.fit_sheet(modified)
            np.testing.assert_array_equal(before['coefficients_rows_x_y_intercept'],after['coefficients_rows_x_y_intercept'])
            self.assertGreater(after['internal_holdout_check']['rms_vector_scan_px'],100)

    def test_residuals_are_scan_internal_and_preserve_measurements(self):
        for sheet in self.data['sheets']:
            result=frame.fit_sheet(sheet)
            measured=np.array([p['pixel_xy'] for p in sheet['points']])
            targets=np.array([[p['printed_grid_east_m'],p['printed_grid_north_m']] for p in sheet['points']])
            # Independent uncentred normal-equation solution on only fitting points.
            x=np.column_stack([measured[:8],np.ones(8)])
            coefficients=np.linalg.solve(x.T@x,x.T@targets[:8])
            predicted=np.column_stack([measured,np.ones(13)])@coefficients
            actual=np.array([p['predicted_printed_grid_m'] for p in result['observations']])
            np.testing.assert_allclose(predicted,actual,atol=1e-5,rtol=0)
            np.testing.assert_array_equal([p['pixel_xy'] for p in result['observations']],measured)
            err=predicted[8:]-targets[8:]
            self.assertAlmostEqual(float(np.sqrt(np.mean(np.sum(err*err,axis=1)))),result['internal_holdout_check']['rms_vector_printed_grid_m'],places=5)
            self.assertIsNone(result['ground_accuracy'])
            self.assertIsNone(result['geographic_crs'])

    def test_internal_checks_and_rectification_do_not_extrapolate(self):
        for sheet in self.data['sheets']:
            left,bottom,right,top=sheet['rectified_printed_grid_extent_m']
            corners={(left,bottom),(left,top),(right,bottom),(right,top)}
            fit={(p['printed_grid_east_m'],p['printed_grid_north_m']) for p in sheet['points'] if p['role']=='fit'}
            self.assertTrue(corners.issubset(fit))
            for p in sheet['points']:
                self.assertTrue(all(isinstance(v,int) for v in p['pixel_xy']))
                self.assertEqual(p['printed_grid_east_m']%10000,0)
                self.assertEqual(p['printed_grid_north_m']%10000,0)
                if p['role']=='check':
                    self.assertTrue(left<p['printed_grid_east_m']<right)
                    self.assertTrue(bottom<p['printed_grid_north_m']<top)

    def test_affine_inverse_reproduces_known_scan_pixel(self):
        for sheet in self.data['sheets']:
            result=frame.fit_sheet(sheet)
            c=np.array(result['coefficients_rows_x_y_intercept'])
            m=np.array(result['pixel_centre_for_numerical_stability'])
            points=np.array([[1000.,1500.],[2000.,2500.]])
            grid=(points-m)@c[:2]+c[2]
            recovered=(grid-c[2])@np.linalg.inv(c[:2])+m
            np.testing.assert_allclose(recovered,points,atol=1e-8)

    def test_rectification_respects_pixel_centre_sampling(self):
        # A coordinate-coded image exposes a half-pixel translation error directly.
        y,x=np.mgrid[0:200,0:200]
        coded=np.stack([x,y,np.zeros_like(x)],axis=-1).astype('uint8')
        result={'coefficients_rows_x_y_intercept':[[1,0],[0,-1],[0,200]],
                'pixel_centre_for_numerical_stability':[0,0]}
        image,meta=frame.rectify(Image.fromarray(coded),result,[10,160,40,190],step=2)
        actual=np.asarray(image)
        np.testing.assert_array_equal(actual[0,0],[11,11,0])
        np.testing.assert_array_equal(actual[-1,-1],[39,39,0])
        self.assertIsNone(meta['geographic_crs'])


if __name__=='__main__':
    unittest.main()
