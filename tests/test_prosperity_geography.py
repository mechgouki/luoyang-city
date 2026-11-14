"""Protect the historical meaning of the new source-map geographic layer.

These checks do not certify ground accuracy or replace UI rendering review.
"""
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def vertices(value):
    if len(value) == 2 and all(isinstance(v, (int, float)) for v in value):
        yield value
    else:
        for child in value:
            yield from vertices(child)


class ProsperityGeographyChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'research/prosperity-v1/geographic-evidence.json').read_text(encoding='utf-8'))
        cls.features = {f['id']: f for f in cls.data['features']}
        cls.entities = {e['id']: e for e in json.loads((ROOT / 'data/entities.json').read_text(encoding='utf-8'))}

    def test_xian_datum_and_longitude_first_axes_are_not_silently_relabelled(self):
        d = self.data
        self.assertEqual(d['crs'], 'EPSG:4610')
        self.assertEqual(d['coordinate_order'], 'longitude,latitude')
        self.assertEqual(d['calibration']['crs'], 'EPSG:4610')
        self.assertIn('Xian 1980', d['calibration']['datum'])
        self.assertIsNone(d['calibration']['original_map_projection'])
        self.assertIn('not RFC7946', d['geometry_format_note'])
        for feature in d['features']:
            for lon, lat in vertices(feature['geometry']['coordinates']):
                self.assertTrue(112.50 < lon < 112.75, (feature['id'], lon))
                self.assertTrue(34.60 < lat < 34.80, (feature['id'], lat))
        # Independent source-map relationships also catch coordinate/feature swaps.
        temple = self.features['geo-yongning-pagoda-reference']['geometry']['coordinates']
        gate = self.features['geo-changhe-palace-gate']['geometry']['coordinates']
        hall = self.features['geo-taiji-hall-reference']['geometry']['coordinates']
        self.assertLess(temple[0], gate[0])  # Yongning lies west of the axial road.
        self.assertLess(temple[1], gate[1])  # Yongning lies south of the palace gate.
        self.assertGreater(hall[1], gate[1])  # Taiji lies north of the palace gate.

    def test_printed_grid_fit_stays_distinct_from_ground_accuracy(self):
        calibration = self.data['calibration']
        controls = calibration['pixel_control_points']
        self.assertEqual(len(controls), 16)
        self.assertEqual(self.data['summary']['field_verified_ground_control_points'], 0)
        for axis in ('longitude', 'latitude'):
            selected = [c for c in controls if c['axis_constraint'] == axis]
            self.assertEqual(len(selected), 8)
            a, b, c0 = calibration['fit'][axis]['coefficients_pdf_pt']
            errors = []
            for control in selected:
                self.assertEqual(control['kind'], 'printed_graticule_tick_not_ground_control')
                x, y = control['pdf_point']
                errors.append(a * x + b * y + c0 - control['value_degrees'])
            rmse = math.sqrt(sum(v * v for v in errors) / len(errors))
            self.assertAlmostEqual(rmse, calibration['fit'][axis]['rmse_degrees'], places=11)
        for feature in self.data['features']:
            approximation = feature['approximation']
            self.assertIsNone(approximation['absolute_ground_accuracy_m'])
            self.assertFalse(approximation['is_field_verified_gcp'])
            self.assertGreaterEqual(approximation['working_display_tolerance_m'], 100)
        registration = next(s for s in self.data['sources'] if s['id'] == 'unesco-1442-component-table')
        self.assertIsNone(registration['reference_point']['datum_in_table'])
        self.assertIn('not used as a ground control', registration['reference_point']['role'])

    def test_feature_coordinates_remain_reproducible_from_the_reviewed_pdf_page(self):
        calibration = self.data['calibration']
        self.assertEqual(calibration['page'], 3457)
        self.assertEqual(calibration['printed_identifier'], '06a')
        self.assertEqual(calibration['source_image_size']['embedded_topographic_raster_px'], [811, 778])
        fits = calibration['fit']
        for feature in self.data['features']:
            source_vertices = list(vertices(feature['source_pdf_geometry']['coordinates']))
            result_vertices = list(vertices(feature['geometry']['coordinates']))
            self.assertEqual(len(source_vertices), len(result_vertices))
            for (x, y), (lon, lat) in zip(source_vertices, result_vertices):
                for axis, value in [('longitude', lon), ('latitude', lat)]:
                    a, b, c = fits[axis]['coefficients_pdf_pt']
                    self.assertAlmostEqual(a * x + b * y + c, value, delta=6e-8)

    def test_modern_river_and_regional_label_cannot_become_northern_wei_terrain(self):
        calibration = self.data['calibration']
        self.assertEqual((calibration['base_aerial_year'], calibration['base_survey_year']), (1997, 1999))
        river = self.features['geo-modern-luo-river']
        self.assertEqual(river['layer'], 'modern_geographic_reference')
        self.assertTrue(river['not_ancient_river'])
        self.assertNotIn('entity_id', river)  # No automatic replacement of historic luoshui geometry.
        hill = self.features['geo-modern-mang-hill-label']
        self.assertEqual(hill['layer'], 'regional_label_reference')
        self.assertIsNone(hill['elevation_m'])
        self.assertTrue(hill['not_a_summit_or_height_control'])
        gaps = {g['id']: g for g in self.data['unlocated_or_unverified']}
        for key in ['gap-historical-luo', 'gap-historical-terrain', 'gap-datum-transformation']:
            self.assertIsNone(gaps[key]['geometry'])

    def test_missing_southern_wall_and_gate_are_not_closed_with_a_protection_boundary(self):
        for key in ['geo-inner-wall-aboveground', 'geo-inner-wall-underground']:
            feature = self.features[key]
            self.assertEqual(feature['geometry']['type'], 'MultiLineString')
            self.assertTrue(feature['southern_wall_missing'])
            for line in feature['geometry']['coordinates']:
                self.assertNotEqual(line[0], line[-1])
        self.assertFalse(any(f.get('entity_id') == 'gate_xuanyang' for f in self.data['features']))
        gaps = {g['id']: g for g in self.data['unlocated_or_unverified']}
        self.assertIsNone(gaps['gap-inner-south-wall']['geometry'])
        self.assertIsNone(gaps['gap-xuanyang-gate']['geometry'])
        outer = self.features['geo-outer-city-related-remains']
        self.assertTrue(outer['do_not_treat_as_surveyed_city_wall'])
        self.assertEqual(outer['source_legend'], 'Boundary of Relevant Remains')

    def test_palace_display_envelope_cannot_supply_an_evidence_wall_stroke(self):
        envelope = self.features['geo-palace-layout-envelope']
        self.assertEqual(envelope['layer'], 'layout_envelope')
        self.assertEqual(envelope['inferred_edges'], [0])
        self.assertTrue(envelope['not_for_survey_measurement'])
        rendering = envelope['rendering']
        self.assertTrue(rendering['fill'])
        self.assertFalse(rendering['stroke'])
        self.assertTrue(rendering['never_promote_to_evidence_wall'])
        self.assertEqual(rendering['outline_feature_id'], 'geo-palace-walls')
        evidence = self.features['geo-palace-walls']
        self.assertEqual(evidence['geometry']['type'], 'MultiLineString')
        self.assertFalse(evidence['rendering']['close_path'])
        self.assertFalse(evidence['rendering']['fill'])

    def test_mixed_period_remains_and_same_name_gates_are_not_merged(self):
        excluded = {e['source_feature_code'] for e in self.data['excluded_from_prosperity_active_layer']}
        self.assertTrue({'Cnm-2', 'Jn-3.1/Jn-3.2', 'Jn-4.2'}.issubset(excluded))
        active_codes = {f['source_feature_code'] for f in self.data['features'] if f['layer'] == 'site_remains'}
        self.assertNotIn('Cnm-2', active_codes)
        self.assertNotIn('Jn-3.1', active_codes)
        self.assertNotIn('Jn-3.2', active_codes)
        self.assertNotIn('Jn-4.2', active_codes)
        for feature in self.data['features']:
            if feature['layer'] == 'site_remains':
                self.assertIn('北魏', feature['source_historical_period'])
            if 'entity_id' in feature:
                self.assertIn(feature['entity_id'], self.entities)
                self.assertTrue(feature['entity_binding_note'])
        gate = self.features['geo-changhe-palace-gate']
        self.assertEqual(gate['source_feature_code'], 'Cgm-3')
        self.assertEqual(gate['entity_id'], 'ic_changhe_palace')
        self.assertNotEqual(gate['entity_id'], 'gate_changhe_west')
        for key in ['geo-jinyong-bing-wall', 'geo-jinyong-bing-reference']:
            self.assertEqual(self.features[key]['entity_id'], 'ic_jinyong')
            self.assertEqual(self.features[key]['entity_binding_scope'], 'partial_component_reference')
        for key in ['geo-taiji-hall-reference', 'geo-yunlong-gate']:
            self.assertNotIn('entity_id', self.features[key])


if __name__ == '__main__':
    unittest.main()
