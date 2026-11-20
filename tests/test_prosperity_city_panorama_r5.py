"""Geometry, spatial ordering and provenance regressions specific to the R5 projections."""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from PIL import Image
from city_panorama_r5_scene import CAMERAS, clipped_segments
from verify_city_panorama_r5 import verify


class Panorama(unittest.TestCase):
    site=ROOT/"_site"

    def test_release(self):
        info=json.loads((self.site/"build-info.json").read_bytes())
        self.assertEqual(verify(info,lambda p:(self.site/p).read_bytes())["offline_members"],10)

    def test_painted_and_projected_landmark_order(self):
        scene=json.loads((self.site/"city-panorama/scene.json").read_bytes())
        art=scene["image"]; landmarks=art["painting_footpoints_px"]
        primary={m["id"]:m["projected_ground_px"]["core"] for m in scene["models"]}
        for points in (landmarks,primary):
            self.assertLess(points["C04"][0],points["C01"][0])
            self.assertGreater(points["C04"][1],points["C01"][1])
            self.assertLess(points["C03"][1],points["C01"][1])
            self.assertGreater(points["C02"][0],points["C01"][0])
        for key,(x,y) in landmarks.items():
            px,py=primary[key]
            self.assertLess(abs(x/art["width"]-px/1600),.035)
            self.assertLess(abs(y/art["height"]-py/950),.035)
        for filename,width in [("panorama.webp",art["width"]),("panorama-small.webp",art["small_width"])]:
            with Image.open(self.site/"city-panorama"/filename) as im:
                self.assertEqual(im.width,width)
                self.assertAlmostEqual(im.height/im.width,art["height"]/art["width"],places=3)

    def test_clips_line_parts_without_joining_undocumented_gaps(self):
        self.assertEqual(clipped_segments([[0,0],[3,3],[6,0]],2),
                         [[[0,0],[2,2]],[[4,2],[6,0]]])
        self.assertNotEqual(CAMERAS["city"]["mode"],CAMERAS["core"]["mode"])
