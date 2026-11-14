"""Check P2's published geometry, identities and explicitly bounded claims.

Read built artifacts as a reader would; do not import the drawing generator.
These tests cannot certify ground accuracy or replace browser/visual review.
"""
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET
import zipfile

from pypdf import PdfReader
from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / '_site'
OUT = SITE / 'prosperity-core'
NS = '{http://www.w3.org/2000/svg}'
NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
LOCAL_PROJECTION = (
    '+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad '
    '+step +proj=aeqd +lat_0=34.7333333333 +lon_0=112.6166666667 '
    '+a=6378140 +rf=298.257'
)
EXPECTED = {
    'core-changhe': ('geo-changhe-palace-gate', 'ic_changhe_palace', 'M02', 44.5, 24.4),
    'core-taiji': ('geo-taiji-hall-reference', None, 'M03', 100.0, 60.0),
    'core-yongning-tower': ('geo-yongning-pagoda-reference', 'ic_yongning', 'M05', 38.2, 38.2),
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def coordinate_pairs(value):
    numbers = [float(v) for v in re.findall(NUMBER, value)]
    if len(numbers) % 2:
        raise AssertionError('An SVG point/path has an incomplete coordinate pair')
    return list(zip(numbers[::2], numbers[1::2]))


def svg_xy(point, projection, lift=0):
    # SVG's public matrix convention: [a,b,c,d,e,f], not row-major 2x3.
    a, b, c, d, e, f = projection['affine_svg_from_metric']
    x, y = point
    return (a*x + c*y + e, b*x + d*y + f - lift)


class HTMLReferences(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.elements = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class ProsperityCorePublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read(OUT / 'data.json')
        cls.model_file = read(OUT / 'models.json')
        cls.models = {m['id']: m for m in cls.model_file['models']}
        cls.basis = read(OUT / 'core-scale-basis.json')
        cls.rules = {t['id']: t for t in cls.basis['templates']}
        cls.relations = read(OUT / 'core-relations.json')
        cls.scenes = {s['id']: s for s in cls.relations['scenes']}
        cls.geo = read(ROOT / 'research/prosperity-v1/geographic-evidence.json')
        cls.features = {f['id']: f for f in cls.geo['features']}
        cls.info = read(SITE / 'build-info.json')
        cls.transform = Transformer.from_pipeline(LOCAL_PROJECTION)
        cls.maps = {
            mode: ET.parse(OUT / filename).getroot()
            for mode, filename in [('plan', 'core-plan.svg'), ('oblique', 'core-oblique.svg')]
        }

    def assertPointsClose(self, actual, expected, delta=0.001):
        self.assertEqual(len(actual), len(expected))
        for actual_point, expected_point in zip(actual, expected):
            self.assertEqual(len(actual_point), 2)
            for a, b in zip(actual_point, expected_point):
                self.assertAlmostEqual(a, b, delta=delta)

    def test_three_templates_keep_the_reviewed_source_and_entity_identities(self):
        self.assertEqual(set(self.models), set(EXPECTED))
        self.assertEqual(set(self.rules), set(EXPECTED))
        items = {item['id']: item for item in self.data['items']}
        self.assertEqual(set(items), set(EXPECTED))
        for ident, (source_id, entity_id, dimension_id, _, _) in EXPECTED.items():
            with self.subTest(item=ident):
                model = self.models[ident]
                self.assertEqual(model['source_feature_id'], source_id)
                self.assertEqual(model['entity_id'], entity_id)
                self.assertEqual(model['dimension_record_id'], dimension_id)
                self.assertEqual(items[ident]['entity_id'], entity_id)
                self.assertEqual(items[ident]['source_feature_id'], source_id)
                self.assertNotEqual(model['entity_id'], 'gate_changhe_west')
        self.assertIn('entity=ic_changhe_palace', items['core-changhe']['related_url'])
        self.assertIn('feature=geo-taiji-hall-reference', items['core-taiji']['related_url'])
        self.assertNotIn('entity=', items['core-taiji']['related_url'])
        for name in ['core-scale-basis.json', 'core-relations.json']:
            self.assertEqual(read(OUT / name), read(ROOT / 'research/prosperity-v2' / name))
        for source in self.basis['inputs']:
            self.assertEqual(digest(ROOT / source['path']), source['sha256'])

    def test_metric_edges_and_centroids_match_dimensions_and_unchanged_p1_anchors(self):
        self.assertEqual(self.model_file['source_crs'], 'EPSG:4610')
        self.assertEqual(self.geo['coordinate_order'], 'longitude,latitude')
        self.assertEqual(self.basis['coordinate_reference']['projection_pipeline'], LOCAL_PROJECTION)
        for ident, (source_id, _, _, width, depth) in EXPECTED.items():
            with self.subTest(item=ident):
                model = self.models[ident]
                source_point = self.features[source_id]['geometry']['coordinates']
                self.assertEqual(model['anchor_source_coordinates'], source_point)
                self.assertEqual(self.rules[ident]['anchor_coordinates'], source_point)
                self.assertEqual(model['projection_pipeline'], LOCAL_PROJECTION)
                center = self.transform.transform(*source_point)
                self.assertPointsClose([model['center_xy_m']], [center], delta=1e-6)
                polygon = model['polygon_xy_m']
                self.assertEqual(len(polygon), 4)
                centroid = [sum(p[i] for p in polygon)/4 for i in (0, 1)]
                self.assertPointsClose([centroid], [center], delta=1e-6)
                self.assertEqual(model['dimensions_m'], {'east_west': width, 'north_south': depth})
                for i, expected_length in enumerate([width, depth, width, depth]):
                    self.assertAlmostEqual(math.dist(polygon[i], polygon[(i+1) % 4]), expected_length, places=6)
        # Independent spatial relations catch an accidental exchange of same-format coordinates.
        self.assertLess(self.models['core-yongning-tower']['center_xy_m'][0], self.models['core-changhe']['center_xy_m'][0])
        self.assertLess(self.models['core-yongning-tower']['center_xy_m'][1], self.models['core-changhe']['center_xy_m'][1])
        self.assertGreater(self.models['core-taiji']['center_xy_m'][1], self.models['core-changhe']['center_xy_m'][1])

    def test_working_angle_has_the_right_sign_and_does_not_certify_height_or_roof(self):
        for ident, model in self.models.items():
            with self.subTest(item=ident):
                rule = self.rules[ident]
                self.assertFalse(model['orientation_verified'])
                self.assertFalse(rule['orientation_verified'])
                self.assertIsNone(rule['measured_orientation_angle_deg'])
                self.assertEqual(model['orientation_convention'], 'north_axis_clockwise_from_local_north')
                self.assertEqual(model['orientation_angle_deg'], rule['orientation_angle_deg'])
                p = model['polygon_xy_m']
                north_edge = [p[2][i] - p[1][i] for i in (0, 1)]
                bearing = math.degrees(math.atan2(north_edge[0], north_edge[1]))
                self.assertAlmostEqual(bearing, rule['orientation_angle_deg'], places=6)
                self.assertGreater(north_edge[0], 0)  # Positive bearing tilts north toward east.
                self.assertIsNone(model['historical_height_m'])
                self.assertIsNone(model['roof_model'])
                self.assertIsNone(rule['historical_ground_elevation_m'])
                self.assertTrue(model['position_note'] and model['orientation_note'])
                self.assertEqual(model['drawing_lift_px'], 7)
                self.assertFalse(model['drawing_lift_is_historical_height'])
        self.assertEqual(self.models['core-taiji']['below_surface_or_fill_depth_m_approx'], 6)
        self.assertIsNone(self.models['core-taiji']['surviving_height_m'])
        self.assertEqual(self.models['core-yongning-tower']['surviving_height_m'], 2.2)
        for key in ['historical_heights_reconstructed', 'roofs_reconstructed', 'ancient_ground_surface_reconstructed', 'full_city_reconstruction_completed']:
            self.assertFalse(self.data['research_limits'][key])

    def test_actual_plan_and_oblique_polygons_use_models_and_only_seven_pixel_lift(self):
        for mode, root in self.maps.items():
            projection = self.data['projection' if mode == 'plan' else 'oblique_projection']
            self.assertEqual(projection['source_crs'], 'EPSG:4610')
            self.assertEqual(projection['projection_pipeline'], LOCAL_PROJECTION)
            self.assertFalse(projection['historical_heights_reconstructed'])
            self.assertFalse(projection['ancient_ground_surface_reconstructed'])
            self.assertFalse(any(n.get('transform') for n in root.iter()), 'Unrecorded SVG transform would change the published geometry')
            groups = {n.get('data-core-id'): n for n in root.iter() if n.get('data-core-id')}
            self.assertEqual(set(groups), set(EXPECTED))
            for ident, group in groups.items():
                with self.subTest(mode=mode, item=ident):
                    model = self.models[ident]
                    self.assertEqual(group.get('data-source-feature-id'), model['source_feature_id'])
                    self.assertEqual(group.get('data-historical-height'), 'unknown')
                    polygons = [n for n in group if n.tag == NS+'polygon' and n.get('data-role') == 'dimension_template']
                    self.assertEqual(len(polygons), 1)
                    lift = 7 if mode == 'oblique' else 0
                    ground = [svg_xy(p, projection) for p in model['polygon_xy_m']]
                    top = [(x, y-lift) for x, y in ground]
                    self.assertPointsClose(coordinate_pairs(polygons[0].get('points')), top)
                    anchors = [n for n in group if n.get('data-role') == 'source_anchor']
                    self.assertEqual(len(anchors), 1)
                    self.assertPointsClose([(float(anchors[0].get('cx')), float(anchors[0].get('cy')))], [svg_xy(model['center_xy_m'], projection, lift)])
                    sides = [n for n in group if n.get('data-role') == 'drawing_thickness']
                    self.assertEqual(len(sides), 4 if mode == 'oblique' else 0)
                    for i, side in enumerate(sides):
                        j = (i+1) % 4
                        self.assertPointsClose(coordinate_pairs(side.get('points')), [ground[i], ground[j], top[j], top[i]])

    def test_court_is_unplaced_and_source_wall_paths_are_preserved_without_closure(self):
        comparison = self.basis['comparison_templates'][0]
        self.assertEqual(comparison['dimensions_m'], {'east_west': 212, 'north_south': 301})
        self.assertFalse(comparison['city_overlay_allowed'])
        self.assertIsNone(comparison['anchor_coordinates'])
        self.assertIsNone(comparison['tower_position_in_template_m'])
        diagnostic = self.basis['courtyard_diagnostic']
        self.assertFalse(diagnostic['fit_adopted_for_city_overlay'])
        self.assertFalse(diagnostic['north_side_observed'])
        self.assertFalse(diagnostic['tower_was_used_as_fit_control'])
        self.assertGreater(diagnostic['measured_wall_spacing_m'] - diagnostic['table_width_m'], 50)
        self.assertGreater(diagnostic['fixed_template_rms_m'], 20)
        self.assertFalse(self.model_file['court_template_placed_in_city'])
        self.assertFalse(self.data['research_limits']['court_template_placed_in_city'])
        for mode, root in self.maps.items():
            projection = self.data['projection' if mode == 'plan' else 'oblique_projection']
            self.assertFalse(any(n.get('data-role') == 'unplaced_dimension_comparison' for n in root.iter()))
            for feature_id in ['geo-palace-walls', 'geo-yongning-temple-walls']:
                group = next(n for n in root.iter() if n.get('data-source-feature-id') == feature_id)
                paths = [n for n in group if n.tag == NS+'path']
                source_lines = self.features[feature_id]['geometry']['coordinates']
                self.assertEqual(len(paths), len(source_lines))
                self.assertFalse(any(n.tag == NS+'polygon' for n in group))
                for line, element in zip(source_lines, paths):
                    with self.subTest(mode=mode, wall=feature_id):
                        self.assertNotEqual(line[0], line[-1])
                        self.assertNotRegex(element.get('d'), '[zZ]')
                        self.assertTrue(element.get('stroke-dasharray'))
                        expected = [svg_xy(self.transform.transform(*p), projection) for p in line]
                        self.assertPointsClose(coordinate_pairs(element.get('d')), expected)
            envelope = next(n for n in root.iter() if n.get('data-source-feature-id') == 'geo-palace-layout-envelope')
            self.assertTrue(all(n.get('stroke') == 'none' for n in envelope if n.tag == NS+'polygon'))
        plate = ET.parse(OUT / 'courtyard-comparison.svg').getroot()
        unplaced = next(n for n in plate.iter() if n.get('data-role') == 'unplaced_dimension_comparison')
        self.assertEqual(unplaced.get('data-city-overlay-allowed'), 'false')
        self.assertFalse(any(n.tag == NS+'circle' for n in unplaced.iter()), 'Do not add the tower at the independent court template centre')

    def test_three_relation_scenes_and_rendered_nodes_remain_nonmetric(self):
        self.assertEqual(set(self.scenes), {'changhe_gate_complex', 'yongning_compound', 'yongning_pagoda_base'})
        self.assertEqual(sum(len(s['nodes']) for s in self.scenes.values()), 27)
        self.assertEqual(sum(len(s['relations']) for s in self.scenes.values()), 30)
        sources = {s['id'] for s in self.relations['sources']}
        evidence = {e['id'] for e in self.relations['evidence']}
        all_node_ids = []
        for scene in self.scenes.values():
            self.assertEqual(scene['coordinate_semantics'], 'schematic_not_metric')
            node_ids = {n['id'] for n in scene['nodes']}
            self.assertEqual(len(node_ids), len(scene['nodes']))
            all_node_ids.extend(node_ids)
            for node in scene['nodes']:
                for field in ['measured_plan_xy_m', 'geographic_coordinates', 'footprint_geometry_m', 'historical_height_m', 'roof_model']:
                    self.assertIn(field, node)
                    self.assertIsNone(node[field], (node['id'], field))
                self.assertEqual(node['diagram_layout']['units'], 'editorial_canvas')
                self.assertFalse(node['diagram_layout']['is_archaeological_measurement'])
                self.assertFalse(node['point_is_entity_location'])
                self.assertTrue(set(node['source_refs']) <= sources)
                self.assertTrue(set(node['evidence_refs']) <= evidence)
            for edge in scene['relations']:
                self.assertTrue({edge['subject'], edge['object']} <= node_ids)
                self.assertIsNone(edge['distance_m'])
                self.assertIsNone(edge['bearing_degrees'])
                self.assertFalse(edge['has_measured_edge_geometry'])
                self.assertTrue(set(edge['source_refs']) <= sources)
                self.assertTrue(set(edge['evidence_refs']) <= evidence)
            root = ET.parse(OUT / (scene['id'].replace('_', '-')+'.svg')).getroot()
            drawn = {n.get('data-component-id'): n for n in root.iter() if n.get('data-component-id')}
            self.assertEqual(set(drawn), node_ids)
            self.assertTrue(all(n.get('data-coordinate-semantics') == 'schematic_not_metric' for n in drawn.values()))
        self.assertEqual(len(set(all_node_ids)), 27)
        self.assertEqual(self.relations['coordinate_contract']['new_ancient_coordinates'], 0)
        self.assertEqual(self.relations['coordinate_contract']['new_ground_control_points'], 0)

    def test_north_gate_is_roofless_and_unknown_south_passages_are_not_completed(self):
        nodes = {n['id']: n for n in self.scenes['yongning_compound']['nodes']}
        north, south = nodes['yn-gate-north'], nodes['yn-gate-south']
        self.assertFalse(north['roof_present'])
        self.assertEqual(north['diagram_layout']['shape'], 'roofless_gate_symbol')
        self.assertFalse(north['plan_visible_in_S40'])
        self.assertIn('ground_passage_count', south)
        self.assertIsNone(south['ground_passage_count'])
        self.assertEqual(south['literary_level_count'], 3)
        self.assertIsNone(south['dimensions_m']['axis_assignment_from_table'])
        self.assertIsNone(nodes['yn-hall']['dimensions_m'])
        self.assertFalse(nodes['yn-hall']['shared_axis_with_tower_proven'])
        self.assertIsNone(nodes['yn-gate-east']['dimensions_m'])
        self.assertEqual(nodes['yn-lodgings']['placement_mode'], 'unlocated_catalogue')
        self.assertFalse(nodes['yn-lodgings']['catalogue_is_directional'])
        self.assertIsNone(nodes['yn-lodgings']['individual_building_count'])
        gate_parts = self.scenes['changhe_gate_complex']['nodes']
        self.assertEqual(sum(n['kind'] == 'passage' for n in gate_parts), 3)
        root = ET.parse(OUT / 'yongning-compound.svg').getroot()
        groups = {n.get('data-component-id'): n for n in root.iter() if n.get('data-component-id')}
        self.assertIn('不施屋', ''.join(groups['yn-gate-north'].itertext()))
        self.assertFalse(any(n.tag == NS+'polygon' for n in groups['yn-gate-north'].iter()))
        self.assertIn('此卡片不表示寺内方位', ''.join(groups['yn-lodgings'].itertext()))

    def test_all_p1_and_earlier_assets_remain_byte_identical(self):
        preservation = read(OUT / 'preservation.json')
        protected = preservation['protected_files']
        self.assertTrue(preservation['protected_unchanged'])
        self.assertGreater(len(protected), 400)
        self.assertTrue({
            'data/entities.json', 'prosperity/geographic-evidence.json',
            'prosperity/source-layout.svg', 'prosperity/layout-panorama.svg',
            'downloads/prosperity-v1-atlas.pdf', 'downloads/prosperity-v1-package.zip',
        } <= set(protected))
        for relative_path, expected_hash in protected.items():
            self.assertEqual(digest(SITE / relative_path), expected_hash, relative_path)
            self.assertEqual(self.info['files_sha256'][relative_path], expected_hash, relative_path)
        self.assertEqual(read(SITE / 'data/entities.json'), read(ROOT / 'data/entities.json'))
        self.assertEqual(read(SITE / 'prosperity/geographic-evidence.json'), self.geo)
        self.assertEqual(digest(SITE / preservation['p1_entry_archive']), preservation['p1_entry_before_sha256'])
        self.assertEqual(digest(SITE / 'prosperity.html'), preservation['p1_entry_after_sha256'])

    def test_pdf_zip_and_all_advertised_downloads_are_real_consistent_artifacts(self):
        pdf = PdfReader(SITE / 'downloads/prosperity-core-v2-atlas.pdf')
        self.assertEqual(len(pdf.pages), 7)
        self.assertTrue(all(page.get_contents() is not None for page in pdf.pages))
        with zipfile.ZipFile(SITE / 'downloads/prosperity-core-v2-package.zip') as archive:
            self.assertIsNone(archive.testzip())
            required = {
                'README.txt', 'prosperity-core/data.json', 'prosperity-core/models.json',
                'prosperity-core/core-scale-basis.json', 'prosperity-core/core-relations.json',
                'prosperity-core/core-plan.svg', 'prosperity-core/core-oblique.svg',
                'prosperity-core/courtyard-comparison.svg', 'prosperity-core/method.md',
                'prosperity-core/changhe-gate-complex.svg', 'prosperity-core/yongning-compound.svg',
                'prosperity-core/yongning-pagoda-base.svg',
            }
            self.assertTrue(required <= set(archive.namelist()))
            for name in required - {'README.txt'}:
                self.assertEqual(archive.read(name), (SITE / name).read_bytes(), name)
        for entry in self.data['downloads']:
            relative_path = entry['url'].removeprefix('./')
            path = SITE / relative_path
            self.assertTrue(path.is_file(), relative_path)
            self.assertGreater(path.stat().st_size, 100, relative_path)
            self.assertEqual(digest(path), self.info['files_sha256'][relative_path], relative_path)

    def test_p1_and_homepage_entrypoints_and_release_counts_are_published(self):
        for filename, entry_id in [('prosperity.html', 'core-scale-entry'), ('index.html', 'core-scale-home-link'), ('v3.0-dual.html', 'core-scale-home-link')]:
            page = HTMLReferences((SITE / filename).read_text(encoding='utf-8'))
            entries = [a for _, a in page.elements if a.get('id') == entry_id]
            self.assertEqual(len(entries), 1, filename)
            self.assertNotIn('hidden', entries[0])
            self.assertNotEqual(entries[0].get('aria-hidden'), 'true')
            self.assertNotRegex(entries[0].get('style', ''), r'display\s*:\s*none')
            self.assertIn('./prosperity-core.html', [a.get('href') for tag, a in page.elements if tag == 'a'])
        page = HTMLReferences((SITE / 'prosperity-core.html').read_text(encoding='utf-8'))
        self.assertIn('./prosperity.html', [a.get('href') for tag, a in page.elements if tag == 'a'])
        for tag, attrs in page.elements:
            asset = attrs.get('src') if tag == 'script' else attrs.get('href') if tag == 'link' else None
            if asset and asset.startswith('./_assets/'):
                relative_path = asset.removeprefix('./')
                self.assertEqual(digest(SITE / relative_path), self.info['files_sha256'][relative_path])
        published = self.info['prosperity_core']
        for key, value in [('metric_templates', 3), ('local_relation_scenes', 3), ('local_components', 27), ('local_relations', 30), ('atlas_pages', 7), ('new_ancient_absolute_coordinates', 0)]:
            self.assertEqual(published[key], value)
        self.assertEqual(published['source_crs'], 'EPSG:4610')
        for key in ['historical_heights_reconstructed', 'roofs_reconstructed', 'ancient_ground_surface_reconstructed', 'court_template_placed_in_city']:
            self.assertFalse(published[key])
        for record in [self.data, self.model_file, published]:
            self.assertEqual(record['source_commit'], self.info['source_commit'])


if __name__ == '__main__':
    unittest.main()
