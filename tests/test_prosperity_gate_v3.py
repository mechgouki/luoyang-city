"""Check source/metric boundaries, downloadable evidence, and the P2 archive chain."""
import csv
import copy
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import sys
import unittest
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / '_site'
OUT = SITE / 'prosperity-gate'
sys.path.insert(0, str(ROOT / 'tools'))
from prosperity_gate_geometry import build_gate_geometry

NS = '{http://www.w3.org/2000/svg}'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def vertices(value):
    if isinstance(value, dict):
        if 'x' in value and 'y' in value:
            return [(value['x'], value['y'])]
        return vertices(next(value[key] for key in ['coordinates', 'points', 'vertices'] if key in value))
    if len(value) == 2 and all(isinstance(part, (int, float)) for part in value):
        return [tuple(value)]
    return [point for part in value for point in vertices(part)]


class Markup(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class PublishedGatePlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = read(ROOT / 'research/prosperity-v3/gate-plan.json')
        cls.models = read(OUT / 'models.json')
        cls.data = read(OUT / 'data.json')
        cls.info = read(SITE / 'build-info.json')

    def test_original_raster_and_pixel_readings_are_preserved(self):
        source = self.data['source_raster']
        published = SITE / source['url'].removeprefix('./')
        self.assertEqual(digest(published), source['sha256'])
        with Image.open(published) as image:
            self.assertEqual(image.size, (source['width_px'], source['height_px']))
        self.assertEqual((OUT / 'gate-plan.json').read_bytes(), (ROOT / 'research/prosperity-v3/gate-plan.json').read_bytes())
        inputs = {item['id']: item for item in self.source['components']}
        sources = {item['id'] for item in self.data['sources']}
        self.assertGreaterEqual(len(inputs), 6)
        self.assertEqual({item['id'] for item in self.data['components']}, set(inputs))
        for component in self.data['components']:
            with self.subTest(component=component['id']):
                self.assertEqual(component['source_px'], inputs[component['id']]['source_px'])
                self.assertTrue(component['source_links'])
                self.assertTrue({item['id'] for item in component['source_links']} <= sources)
                points = vertices(component['source_px'])
                self.assertGreaterEqual(len(points), 2)
                for x, y in points:
                    self.assertTrue(0 <= x <= source['width_px'] and 0 <= y <= source['height_px'])

    def test_local_conversion_preserves_shape_instead_of_fitting_table_dimensions(self):
        """One image scale must preserve ratios across all independently traced parts."""
        ratios = []
        all_points = []
        for component in self.models['components']:
            raw, local = vertices(component['source_px']), vertices(component['coordinates_m'])
            self.assertEqual(len(raw), len(local))
            self.assertTrue(all(math.isfinite(value) for point in local for value in point))
            for left in range(len(raw)):
                for right in range(left + 1, len(raw)):
                    pixels = math.dist(raw[left], raw[right])
                    if pixels:
                        ratios.append(math.dist(local[left], local[right]) / pixels)
            all_points.extend(local)
            if component['geometry_type'].lower() == 'polygon':
                self.assertGreaterEqual(len(set(raw)), 3)
                area = abs(sum(local[i][0] * local[(i + 1) % len(local)][1]
                               - local[(i + 1) % len(local)][0] * local[i][1] for i in range(len(local)))) / 2
                self.assertGreater(area, 0, component['id'])
        self.assertTrue(ratios)
        # Rounding at export may affect the final decimal but cannot rescale individual parts.
        self.assertLess(max(ratios) - min(ratios), 1e-5)
        self.assertGreater(min(ratios), 0)
        bar = self.source['calibration']['scale_bar']
        expected_scale = bar['length_m'] / math.dist(bar['start_px'], bar['end_px'])
        self.assertAlmostEqual(sum(ratios) / len(ratios), expected_scale, places=5)
        self.assertLess(max(math.dist(point, other) for point in all_points for other in all_points), 1000)
        rebuilt = build_gate_geometry(self.source)
        self.assertEqual([item['coordinates_m'] for item in rebuilt['components']],
                         [item['coordinates_m'] for item in self.models['components']])

    def test_table_dimensions_do_not_control_the_local_calibration(self):
        changed = copy.deepcopy(self.source)
        changed['diagnostics']['dimension_check']['table_dimensions_m'] = {'east_west': 89.0, 'north_south': 48.8}
        rebuilt = build_gate_geometry(changed)
        self.assertEqual(rebuilt['calibration']['m_per_px'], self.models['calibration']['m_per_px'])
        self.assertEqual([item['coordinates_m'] for item in rebuilt['components']],
                         [item['coordinates_m'] for item in self.models['components']])
        self.assertIs(self.source['diagnostics']['dimension_check']['table_used_for_scale_calibration'], False)

    def test_image_north_and_east_keep_the_intended_axis_directions(self):
        """Recover the affine basis from published points, independently of conversion helpers."""
        main = next(item for item in self.models['components'] if item['kind'] == 'gate_base')
        raw, local = vertices(main['source_px']), vertices(main['coordinates_m'])
        first = [raw[1][axis] - raw[0][axis] for axis in range(2)]
        second = [raw[2][axis] - raw[0][axis] for axis in range(2)]
        local_first = [local[1][axis] - local[0][axis] for axis in range(2)]
        local_second = [local[2][axis] - local[0][axis] for axis in range(2)]
        determinant = first[0] * second[1] - first[1] * second[0]
        self.assertNotEqual(determinant, 0)

        def published_vector(vector):
            alpha = (vector[0] * second[1] - vector[1] * second[0]) / determinant
            beta = (first[0] * vector[1] - first[1] * vector[0]) / determinant
            return [alpha * local_first[axis] + beta * local_second[axis] for axis in range(2)]

        arrow = self.source['calibration']['north_arrow']
        north = [arrow['tip_px'][axis] - arrow['tail_px'][axis] for axis in range(2)]
        east = [-north[1], north[0]]  # The raster has x rightwards and y downwards.
        north_m, east_m = published_vector(north), published_vector(east)
        self.assertAlmostEqual(north_m[0], 0, places=5)
        self.assertGreater(north_m[1], 0)
        self.assertGreater(east_m[0], 0)
        self.assertAlmostEqual(east_m[1], 0, places=5)
        self.assertIs(arrow['external_reference_verified'], False)
        self.assertIs(self.source['calibration']['independent_vertical_scale_verified'], False)
        self.assertIsNone(self.source['calibration']['statistical_uncertainty_model'])
        self.assertIs(self.models['calibration']['reading_range_is_statistical_confidence_interval'], False)
        for reading in self.models['diagnostics']['dimension_check']['measurements'].values():
            self.assertIs(reading['is_field_accuracy_estimate'], False)

    def test_invalid_source_bounds_scale_and_solved_city_claim_are_rejected(self):
        outside = copy.deepcopy(self.source)
        outside['components'][0]['source_px'][0][0] = outside['source_raster']['width_px']
        outside['components'][0]['source_px'][-1] = outside['components'][0]['source_px'][0][:]
        no_scale = copy.deepcopy(self.source)
        no_scale['calibration']['scale_bar']['end_px'] = no_scale['calibration']['scale_bar']['start_px'][:]
        solved = copy.deepcopy(self.source)
        solved['city_link']['registration_verified'] = True
        for name, invalid in [('outside native pixels', outside), ('zero scale baseline', no_scale), ('unjustified registration', solved)]:
            with self.subTest(case=name), self.assertRaises(ValueError):
                build_gate_geometry(invalid)

    def test_city_link_does_not_publish_new_absolute_coordinates_or_a_verified_transform(self):
        for document in [self.source, self.models, self.data]:
            self.assertIs(document['city_link']['registration_verified'], False)
        limits = self.data['research_limits']
        self.assertEqual(limits['new_ancient_absolute_coordinates'], 0)
        for field in ['city_footprint_placed', 'external_true_north_verified', 'historical_heights_reconstructed',
                      'roofs_reconstructed', 'ancient_ground_surface_reconstructed']:
            self.assertIs(limits[field], False)
        self.assertEqual(self.models['coordinate_scope'], 'image_local_only')
        link = self.data['city_link']
        self.assertEqual(link['common_control_points_count'], 0)
        for field in ['translation_m', 'rotation_deg', 'city_geometry', 'global_accuracy_m']:
            self.assertIsNone(link[field])
        self.assertIs(link['city_overlay_allowed'], False)
        p2 = next(item for item in read(SITE / 'prosperity-core/models.json')['models'] if item['id'] == 'core-changhe')
        self.assertEqual(link['anchor_coordinates'], p2['anchor_source_coordinates'])
        self.assertEqual(link['working_axis_angle_deg'], p2['orientation_angle_deg'])
        forbidden = {'latitude', 'longitude', 'coordinates_wgs84', 'coordinates_epsg4610', 'geographic_coordinates'}

        def check_keys(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for child in value.values():
                    check_keys(child)
            elif isinstance(value, list):
                for child in value:
                    check_keys(child)
        check_keys(self.models['components'])
        check_keys(self.models['calibration'])

    def test_svg_selection_and_source_layer_have_distinct_contents(self):
        components = {item['id'] for item in self.data['components']}
        for view, entry in self.data['maps'].items():
            root = ET.parse(SITE / entry['url'].removeprefix('./')).getroot()
            self.assertEqual([float(value) for value in root.get('viewBox').split()], [0, 0, 1600, 1100])
            self.assertFalse(list(root.iter(NS + 'script')))
            selected = {node.get('data-component-id') for node in root.iter() if node.get('data-component-id')}
            self.assertTrue(selected <= components)
            if view == 'local':
                self.assertEqual(selected, components)
                source_layer = next(node for node in root.iter() if node.get('id') == 'source-layer')
                self.assertTrue(list(source_layer.iter(NS + 'image')))
                self.assertFalse(any(node.get('data-component-id') for node in source_layer.iter()))

    def test_partial_que_traces_and_connection_paths_remain_open_lines(self):
        parts = self.models['components']
        self.assertEqual(sum(item['kind'] == 'passage' for item in parts), 3)
        drawing = ET.parse(OUT / 'local-plan.svg').getroot()
        groups = {node.get('data-component-id'): node for node in drawing.iter() if node.get('data-component-id')}
        for component in parts:
            if component['kind'] in {'que_base', 'underground_foundation', 'foundation_connection'}:
                self.assertEqual(component['geometry_type'], 'LineString')
                points = vertices(component['coordinates_m'])
                self.assertNotEqual(points[0], points[-1], component['id'])
                lines = list(groups[component['id']].iter(NS + 'polyline'))
                self.assertEqual(len(lines), 1)
                self.assertEqual(lines[0].get('fill'), 'none')
                self.assertFalse(list(groups[component['id']].iter(NS + 'polygon')))
                if component['kind'] == 'underground_foundation':
                    self.assertTrue(lines[0].get('stroke-dasharray'))

    def test_csv_keeps_pixels_and_local_metres_in_separate_columns(self):
        with (OUT / 'readings.csv').open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        models = {item['id']: item for item in self.models['components']}
        self.assertEqual(len(rows), sum(len(vertices(item['source_px'])) for item in models.values()))
        seen = set()
        for row in rows:
            model, index = models[row['component_id']], int(row['vertex_index'])
            key = (row['component_id'], index)
            self.assertNotIn(key, seen)
            seen.add(key)
            self.assertEqual([float(row['source_x_px']), float(row['source_y_px'])], list(vertices(model['source_px'])[index]))
            for actual, expected in zip([float(row['local_x_m']), float(row['local_y_m'])], vertices(model['coordinates_m'])[index]):
                self.assertAlmostEqual(actual, expected, places=7)
            self.assertEqual(row['coordinate_scope'], 'image_local_only; city_registration_unverified')

    def test_downloads_atlas_and_bundle_are_complete_and_hash_consistent(self):
        pdf = PdfReader(SITE / 'downloads/prosperity-gate-v3-atlas.pdf')
        self.assertEqual(len(pdf.pages), 3)
        self.assertTrue(all(page.get_contents() is not None for page in pdf.pages))
        for item in self.data['downloads']:
            path = SITE / item['url'].removeprefix('./')
            self.assertTrue(path.is_file(), str(path))
            self.assertGreater(path.stat().st_size, 40)
        self.assertTrue({'pdf', 'zip', 'svg', 'csv', 'json', 'md'} <= {item['type'] for item in self.data['downloads']})
        with zipfile.ZipFile(SITE / 'downloads/prosperity-gate-v3-package.zip') as archive:
            self.assertIsNone(archive.testzip())
            required = {'README.txt', 'prosperity-gate/local-plan.svg', 'prosperity-gate/city-link.svg',
                        'prosperity-gate/scale-diagnostics.svg', 'prosperity-gate/gate-plan.json',
                        'prosperity-gate/models.json', 'prosperity-gate/readings.csv', 'prosperity-gate/method.md',
                        'downloads/prosperity-gate-v3-atlas.pdf'}
            self.assertTrue(required <= set(archive.namelist()))
            manifest = json.loads(archive.read('prosperity-gate/bundle-manifest.json'))
            self.assertEqual(set(manifest['files_sha256']), set(archive.namelist()) - {'README.txt', 'prosperity-gate/bundle-manifest.json'})
            for name, expected in manifest['files_sha256'].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), expected, name)

    def test_prior_html_updates_are_explicit_reversible_and_preserve_p2_proofs(self):
        proof = read(OUT / 'preservation.json')
        self.assertTrue(proof['protected_unchanged'])
        self.assertGreater(len(proof['protected_files']), 400)
        for path, expected in proof['protected_files'].items():
            self.assertEqual(digest(SITE / path), expected, path)
        self.assertIn('prosperity-core/preservation.json', proof['protected_files'])
        self.assertEqual({update['path'] for update in proof['intentional_html_updates']},
                         {'index.html', 'v3.0-dual.html', 'prosperity.html', 'prosperity-core.html'})
        for update in proof['intentional_html_updates']:
            previous = (SITE / update['archive_path']).read_bytes()
            current = (SITE / update['path']).read_bytes()
            self.assertEqual(hashlib.sha256(previous).hexdigest(), update['before_sha256'])
            self.assertEqual(hashlib.sha256(current).hexdigest(), update['after_sha256'])
            pattern = rb'<p id="' + re.escape(update['entry_id'].encode()) + rb'"[^>]*>.*?</p>'
            matches = re.findall(pattern, current, flags=re.S)
            self.assertEqual(len(matches), 1)
            self.assertIn(b'./prosperity-gate.html', matches[0])
            self.assertEqual(re.sub(pattern, b'', current, flags=re.S), previous)
        p2 = read(SITE / 'prosperity-core/preservation.json')
        self.assertEqual(digest(SITE / 'prosperity-before-gate.html'), p2['p1_entry_after_sha256'])

    def test_no_script_page_is_useful_and_all_new_assets_are_in_release_manifest(self):
        page = (SITE / 'prosperity-gate.html').read_text(encoding='utf-8')
        self.assertNotIn('{{', page)
        markup = Markup(page)
        self.assertTrue(any(tag == 'img' and attrs.get('src') == './prosperity-gate/local-plan.svg' for tag, attrs in markup.tags))
        links = {attrs.get('href') for tag, attrs in markup.tags if tag == 'a'}
        for entry in self.data['downloads']:
            self.assertIn(entry['url'], links)
        self.assertIn('城市配准', page)
        self.assertIn('44.5 × 24.4 m', page)
        self.assertIn('<noscript>', page)
        self.assertEqual(self.data['source_commit'], self.info['source_commit'])
        self.assertEqual(self.info['prosperity_gate']['version'], self.data['version'])
        release = read(SITE / 'release.json')
        self.assertEqual(release['prosperity_gate_version'], self.data['version'])
        for path in SITE.rglob('*'):
            if path.is_file() and ('prosperity-gate' in str(path.relative_to(SITE)) or path.name.endswith('-before-gate.html')):
                relative = path.relative_to(SITE).as_posix()
                self.assertEqual(self.info['files_sha256'][relative], digest(path), relative)


if __name__ == '__main__':
    unittest.main()
