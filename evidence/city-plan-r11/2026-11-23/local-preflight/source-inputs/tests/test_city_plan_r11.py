"""Independent archaeological/coordinate guards for the actual R11 delivery.

These tests inspect source numbers and delivered vertices, not just manifest
claims.  In particular a source symbol must not turn into a measured footprint,
and a change of sheet/viewport must not change the reconstructed geometry.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import unittest
from xml.etree import ElementTree as ET

from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
FOLDER = "city-plan-r11"
NS = "{http://www.w3.org/2000/svg}"
NUMBER = re.compile(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")
SOURCE28_HASH = "80a2e5457789d0056bafe5cb5eb5df73bea23fb2e9d733a784ed0068562ead79"
# The spelling below is the frozen R10.1 source-map projection.  It is kept
# independent of city_plan_r11_geometry/projected_features on purpose.
SOURCE_PIPELINE = (
    "+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad "
    "+step +proj=aeqd +lat_0=34.7333333333 +lon_0=112.6166666667 "
    "+a=6378140 +rf=298.257"
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def flat_points(coordinates):
    if isinstance(coordinates[0], (int, float)):
        return [coordinates]
    return [point for part in coordinates for point in flat_points(part)]


def map_points(coordinates, transform):
    if isinstance(coordinates[0], (int, float)):
        return list(transform(*coordinates))
    return [map_points(part, transform) for part in coordinates]


def cross(origin, a, b):
    return ((a[0] - origin[0]) * (b[1] - origin[1])
            - (a[1] - origin[1]) * (b[0] - origin[0]))


def svg_features(path):
    root = ET.fromstring(path.read_bytes())
    result = {}
    for anchor in root.iter(NS + "a"):
        fid = anchor.get("data-feature-id")
        if fid:
            if fid in result:
                raise AssertionError("Duplicate drawn geometry: " + fid)
            result[fid] = anchor
    return root, result


class R11ActualSpatialEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = read_json(SITE / FOLDER / "plan.json")
        cls.features = {f["id"]: f for f in cls.plan["features"]}
        cls.objects = {o["id"]: o for o in cls.plan["objects"]}
        cls.coverage = {r["id"]: r for r in cls.plan["coverage"]}
        cls.geo_path = ROOT / "research/prosperity-v1/geographic-evidence.json"
        cls.old_geo = read_json(cls.geo_path)
        cls.yongning = read_json(ROOT / "research/city-plan-r11/yongning-published-plan.json")
        cls.palace = read_json(ROOT / "research/city-plan-r11/palace-2013-published-plan.json")
        cls.gate = read_json(ROOT / "research/prosperity-v3/gate-plan.json")
        cls.svg_all, cls.all_drawn = svg_features(SITE / FOLDER / "maps/all.svg")

    def assert_points_close(self, actual, expected, tolerance=1.1e-6):
        actual, expected = flat_points(actual), flat_points(expected)
        self.assertEqual(len(actual), len(expected))
        for a, b in zip(actual, expected):
            self.assertLessEqual(math.dist(a, b), tolerance, (a, b))

    def test_28_source_geometries_keep_every_vertex_and_frozen_datum(self):
        # Source identity comes from the real predecessor file, not an R11 flag.
        self.assertEqual(hashlib.sha256(self.geo_path.read_bytes()).hexdigest(), SOURCE28_HASH)
        baseline = {f["id"]: f for f in self.old_geo["features"]
                    if f["id"] not in {"geo-modern-luo-river", "geo-modern-mang-hill-label"}}
        delivered = {f["id"]: f for f in self.plan["features"] if f["layer"] == "source"}
        self.assertEqual(len(baseline), 28)
        self.assertEqual(set(delivered), set(baseline))
        transform = Transformer.from_pipeline(SOURCE_PIPELINE)
        for fid, source in baseline.items():
            with self.subTest(feature=fid):
                expected = {"type": source["geometry"]["type"],
                            "coordinates": map_points(source["geometry"]["coordinates"], transform.transform)}
                self.assertEqual(delivered[fid]["geometry"], expected)
                self.assertFalse(delivered[fid]["field_registration_verified"])
        self.assertEqual(self.plan["frame"]["projection_pipeline"], SOURCE_PIPELINE)
        self.assertFalse(self.plan["frame"]["datum_transformation_performed"])
        self.assertFalse(self.plan["frame"]["is_wgs84"])

    def test_three_local_source_plans_keep_one_equal_scale_between_all_parts(self):
        for source, prefix in [(self.gate, "r11-changhe-"),
                               (self.yongning, "r11-yongning-"),
                               (self.palace, "r11-palace2013-")]:
            with self.subTest(source=source["id"]):
                ruler = source["calibration"]["scale_bar"]
                scale = ruler["length_m"] / math.dist(ruler["start_px"], ruler["end_px"])
                before, after = [], []
                for component in source["components"]:
                    feature = self.features[prefix + component["id"]]
                    self.assertEqual(feature["geometry"]["type"], component["geometry_type"])
                    before += flat_points(component["source_px"])
                    after += flat_points(feature["geometry"]["coordinates"])
                self.assertEqual(len(before), len(after))
                # Cross-component distances detect local rearrangement as well
                # as anisotropic stretching.  Three noncollinear anchors avoid
                # an apparently correct test using only one dimension.
                a = 0
                b = max(range(len(before)), key=lambda i: math.dist(before[a], before[i]))
                c = max(range(len(before)), key=lambda i: abs(cross(before[a], before[b], before[i])))
                self.assertGreater(abs(cross(before[a], before[b], before[c])), 1)
                for index in (a, b, c):
                    for i in range(len(before)):
                        self.assertAlmostEqual(math.dist(after[index], after[i]),
                                               math.dist(before[index], before[i]) * scale,
                                               delta=2e-6)
                # Image y points down; the drawing y points north.  Apart from
                # that required sign change, no mirror operation is allowed.
                self.assertAlmostEqual(cross(after[a], after[b], after[c]) /
                                       (cross(before[a], before[b], before[c]) * scale * scale),
                                       -1, delta=1e-7)

    def test_candidate_registration_does_not_turn_into_survey_control(self):
        self.assertEqual(self.plan["coordinate_contract"]["verified_shared_controls"], 0)
        self.assertEqual(self.plan["coordinate_contract"]["new_field_coordinates"], 0)
        for binding in self.plan["bindings"]:
            with self.subTest(binding=binding["id"]):
                self.assertFalse(binding["field_registration_verified"])
                self.assertEqual(binding["verified_shared_controls"], 0)
                matrix = binding["local_metric_to_master_matrix"]
                u = [matrix[0][0], matrix[1][0]]
                v = [matrix[0][1], matrix[1][1]]
                self.assertAlmostEqual(math.hypot(*u), 1, places=12)
                self.assertAlmostEqual(math.hypot(*v), 1, places=12)
                self.assertAlmostEqual(u[0] * v[0] + u[1] * v[1], 0, places=12)
                self.assertAlmostEqual(u[0] * v[1] - u[1] * v[0], 1, places=12)

    def test_yongning_gate_gaps_remain_and_no_north_gate_is_invented(self):
        index = {c["id"]: c for c in self.yongning["components"]}
        wall_ids = [cid for cid in index if cid.startswith("YN11-WALL-")]
        self.assertEqual(len(wall_ids), 7)
        for cid in wall_ids:
            self.assertEqual(self.features["r11-yongning-" + cid]["geometry"]["type"], "LineString")
        for high, low in [("YN11-WALL-W-N", "YN11-WALL-W-S"),
                          ("YN11-WALL-E-N", "YN11-WALL-E-S")]:
            self.assertGreater(index[low]["source_px"][0][1] - index[high]["source_px"][-1][1], 70)
        self.assertGreater(index["YN11-WALL-S-E"]["source_px"][0][0]
                           - index["YN11-WALL-S-W"]["source_px"][-1][0], 140)
        self.assertNotIn("YN11-GATE-N", index)
        self.assertFalse(any("北门" in c["label"] for c in index.values()))
        self.assertEqual(index["YN11-GATE-E-MARK"]["geometry_type"], "Point")
        self.assertEqual(index["YN11-CORNER-SW"]["geometry_type"], "LineString")
        self.assertNotEqual(index["YN11-CORNER-SW"]["source_px"][0],
                            index["YN11-CORNER-SW"]["source_px"][-1])
        self.assertFalse(any("passage" in c["id"].lower() for c in index.values()))

    def test_yongning_south_gate_direction_and_size_are_from_the_plan(self):
        ring = self.features["r11-yongning-YN11-GATE-S"]["geometry"]["coordinates"][0]
        width = (math.dist(ring[0], ring[1]) + math.dist(ring[2], ring[3])) / 2
        depth = (math.dist(ring[1], ring[2]) + math.dist(ring[3], ring[0])) / 2
        self.assertTrue(45 < width < 47)
        self.assertTrue(18 < depth < 20)
        dx, dy = ring[1][0] - ring[0][0], ring[1][1] - ring[0][1]
        self.assertGreater(dx, 40)
        self.assertLess(abs(dy), 8)
        # The new source must not rewrite the predecessor's actual table row.
        old = read_json(ROOT / "research/prosperity-v1/building-dimensions.json")
        row = next(i for i in old["massing_items"] if i["item_id"] == "M06")
        self.assertEqual(row["plan_dimensions_m"],
                         {"length": 45.5, "width": 19.1, "axis_assignment_from_table": None})
        self.assertFalse(self.yongning["calibration"]["fit_to_tabulated_dimensions"])

    def test_temple_neighbour_solver_uses_one_wall_source_not_a_union_of_frames(self):
        temple = self.objects["object-ic_yongning"]
        self.assertIn("geo-yongning-temple-walls", temple["source_feature_ids"])
        evaluated = temple["evaluation_feature_ids"]
        expected = {"r11-yongning-" + c["id"] for c in self.yongning["components"]
                    if c["id"].startswith("YN11-WALL-")}
        self.assertEqual(set(evaluated), expected,
                         "Different source remnants became one synthetic courtyard boundary")
        self.assertIsNone(temple["geometry"])
        points = [p for fid in evaluated for p in flat_points(self.features[fid]["geometry"]["coordinates"])]
        expected_box = [min(p[0] for p in points), min(p[1] for p in points),
                        max(p[0] for p in points), max(p[1] for p in points)]
        self.assertEqual(temple["evaluation_bbox_m"], expected_box)

    def test_palace_investigation_symbols_are_points_and_have_no_fake_north_wall(self):
        walls = []
        for component in self.palace["components"]:
            f = self.features["r11-palace2013-" + component["id"]]
            self.assertFalse(f["default_visible"])
            self.assertFalse(f["field_registration_verified"])
            self.assertTrue(f["source_phase"]["phase_unknown"])
            self.assertEqual(f["layer"], "palace")
            if component["type"] == "investigation_markers":
                self.assertEqual(f["geometry"]["type"], "Point")
                self.assertEqual(f["geometry_role"], "published_investigation_location_marker")
            if component["type"] == "partition_walls":
                self.assertEqual(f["geometry"]["type"], "MultiLineString")
                walls += component["native_pdf_coordinates_pt"]
            if component["type"] == "rammed_earth":
                self.assertIn("版筑", f["label"])
                self.assertEqual(f["geometry_role"], "published_rammed_earth_extent")
        # A northern closure across the source's large open top would have a
        # long horizontal span near y426 PDF points.  The only extant short
        # cap lines there belong to the ends of two separate side walls.
        for a, b in walls:
            self.assertFalse(max(a[1], b[1]) < 431 and abs(a[0] - b[0]) > 20)
        top_road = self.features["r11-palace2013-P13-ROAD-HUALIN-S"]
        self.assertEqual(top_road["geometry_role"], "published_road_band")
        for fid, drawn in self.all_drawn.items():
            if fid.startswith("r11-palace2013-"):
                self.assertIn("display:none", drawn.get("style", ""))
        legacy = self.features["geo-palace-layout-envelope"]
        self.assertFalse(legacy["default_visible"])

    def test_native_palace_vectors_are_not_changed_by_the_canonical_frame(self):
        frame = self.palace["source_raster"]
        self.assertEqual(frame["render_scale_px_per_pdf_point"], 4)
        self.assertEqual(frame["pdf_clip_rect_pt"], [304, 386, 542, 795])
        for component in self.palace["components"]:
            expected = map_points(component["native_pdf_coordinates_pt"],
                                  lambda x, y: (4 * (x - 304), 4 * (y - 386)))
            self.assertEqual(component["source_px"], expected)

    def test_palace_two_source_discrepancy_is_retained_not_fitted_away(self):
        tagged = self.palace["diagnostic_points"]
        ruler = self.palace["calibration"]["scale_bar"]
        mpp = 200 / math.dist(ruler["start_px"], ruler["end_px"])
        local_distance = math.dist(tagged["changhe_reference_px"], tagged["taiji_reference_px"]) * mpp
        self.assertTrue(500 < local_distance < 503)
        a = self.features["geo-changhe-palace-gate"]["geometry"]["coordinates"]
        b = self.features["geo-taiji-hall-reference"]["geometry"]["coordinates"]
        self.assertTrue(573 < math.dist(a, b) < 575)
        self.assertGreater(math.dist(a, b) - local_distance, 70)
        gate = self.features["r11-palace2013-P13-MARK-GATE1"]["geometry"]["coordinates"]
        self.assert_points_close(gate, a)
        # In the actual delivered layer the two source Taiji references remain
        # apart.  A dual-point rubber sheet would make this separation vanish.
        ring = self.features["r11-palace2013-P13-RAMMED-TAIJI"]["geometry"]["coordinates"][0][:-1]
        center = [sum(p[k] for p in ring) / len(ring) for k in (0, 1)]
        self.assertTrue(74 < math.dist(center, b) < 79)
        self.assertAlmostEqual(math.dist(center, gate), local_distance, delta=2e-6)

    def test_catalog_coverage_is_not_a_claim_of_339_building_footprints(self):
        catalog = read_json(ROOT / "data/entities.json")
        self.assertEqual(set(self.coverage), {e["id"] for e in catalog})
        self.assertEqual(len(self.coverage), 339)
        self.assertFalse(self.plan["coordinate_contract"]["all_entities_have_footprints"])
        self.assertFalse(any(r["is_one_building_footprint"] for r in self.coverage.values()))
        self.assertTrue(any(r["placement_group"] == "unplaced" for r in self.coverage.values()))
        self.assertTrue(any(r["placement_group"] == "candidate" for r in self.coverage.values()))
        for feature in self.plan["features"]:
            if feature["layer"] == "candidate":
                self.assertEqual(feature["geometry"]["type"], "Point")
                self.assertEqual(feature["geometry_role"], "candidate_marker")
                self.assertFalse(feature["position_unique"])
        for row in self.coverage.values():
            if row["placement_group"] == "unplaced":
                self.assertEqual(row["feature_ids"], [])
        self.assertEqual(len({r["id"] for r in self.plan["constraints"]}), len(self.plan["constraints"]))

    def test_later_pingdeng_and_dajue_towers_do_not_enter_the_prosperity_layer(self):
        expected = {"v2_pingdeng": "five_storey_tower_later_532_start_533_or_534_finish",
                    "w_dajue": "brick_tower_later_532_534_storeys_unspecified"}
        for entity, state in expected.items():
            row = self.coverage[entity]
            self.assertEqual(row["tower_state"], state)
            self.assertTrue(row["later_elements"])
            # The temple can be a literary candidate point while its later
            # tower must not acquire a footprint or a separate tower marker.
            for fid in row["feature_ids"]:
                f = self.features[fid]
                self.assertEqual(f["geometry"]["type"], "Point")
                self.assertNotIn("塔", f["label"].replace("〔无晚出塔〕", ""))
            attached = [f for f in self.plan["features"] if entity in f.get("entity_ids", [])]
            self.assertTrue(attached)
            self.assertTrue(all(f["geometry"]["type"] == "Point" for f in attached))

    def test_every_sheet_draws_the_same_actual_vertices_not_only_equal_hashes(self):
        first = None
        for view in self.plan["views"]:
            root, drawn = svg_features(SITE / FOLDER / "maps" / (view["id"] + ".svg"))
            self.assertEqual(root.get("data-coordinate-frame"), self.plan["frame"]["id"])
            self.assertEqual(set(drawn), set(self.features))
            signature = {}
            for fid, node in drawn.items():
                feature = self.features[fid]
                if feature["geometry"]["type"] == "Point":
                    outer = node.find(NS + "g")
                    transform = outer.get("transform")
                    values = [float(x) for x in NUMBER.findall(transform)]
                    self.assertTrue(transform.startswith("translate("))
                    x, y = feature["geometry"]["coordinates"]
                    self.assert_points_close(values, [x, -y])
                    signature[fid] = ("point", transform)
                else:
                    paths = node.findall(NS + "path")
                    actual = []
                    for path in paths:
                        values = [float(x) for x in NUMBER.findall(path.get("d"))]
                        self.assertEqual(len(values) % 2, 0)
                        actual.extend([values[i:i + 2] for i in range(0, len(values), 2)])
                    expected = [[x, -y] for x, y in flat_points(feature["geometry"]["coordinates"])]
                    self.assert_points_close(actual, expected)
                    signature[fid] = ("path", tuple(p.get("d") for p in paths))
            if first is None:
                first = signature
            else:
                self.assertEqual(signature, first, "Viewport rearranged city geometry: " + view["id"])

    def test_source_dashes_and_open_walls_survive_svg_export(self):
        for fid in ["geo-inner-wall-underground", "geo-palace-walls"]:
            feature = self.features[fid]
            self.assertEqual(feature["source_rendering"]["line_style"], "dashed")
            for path in self.all_drawn[fid].findall(NS + "path"):
                self.assertTrue(path.get("stroke-dasharray"), "Source dashed wall became solid: " + fid)
                self.assertEqual(path.get("fill"), "none")
                self.assertNotIn("Z", path.get("d").upper())
        for component in self.yongning["components"]:
            style = component["source_legend"]["outline_line_style"]
            if component["id"].startswith("YN11-WALL-"):
                self.assertIn("点划线", style, "The published interrupted wall lines were lost")
            if "点划线" in style or "虚线" in style:
                drawn = self.all_drawn["r11-yongning-" + component["id"]]
                for path in drawn.findall(NS + "path"):
                    self.assertTrue(path.get("stroke-dasharray"), component["id"])


if __name__ == "__main__":
    unittest.main()
