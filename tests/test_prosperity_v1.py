"""Verify the published workbench preserves identity and bounds its new claims."""
import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'_site'
NS='{http://www.w3.org/2000/svg}'

def read(path):return json.loads(path.read_text())

class ProsperityPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=read(SITE/'prosperity/data.json')
        cls.entities={e['id']:e for e in cls.data['entities']}
        cls.geo=read(SITE/'prosperity/geographic-evidence.json')
        cls.review=read(SITE/'prosperity/text-review.json')
        cls.info=read(SITE/'build-info.json')

    def test_existing_entities_and_shared_reading_positions_survive(self):
        original=read(ROOT/'data/entities.json');markers=read(ROOT/'data/markers.json')
        self.assertEqual(set(self.entities),{e['id'] for e in original})
        self.assertEqual(len(self.entities),339)
        plan=ET.parse(SITE/'prosperity/literary-plan.svg').getroot()
        hits=next(n for n in plan.iter() if n.get('id')=='prosperity-plan-targets')
        self.assertEqual(len(hits),len(markers))
        actual={tuple(json.loads(n.get('data-members'))):(float(n.get('cx')),float(n.get('cy'))) for n in hits}
        for m in markers:self.assertEqual(actual[tuple(m['ids'])],(m['x'],m['y']))
        for n in hits:
            ids=json.loads(n.get('data-members'))
            self.assertEqual(n.get('data-entity-id'),ids[0] if len(ids)==1 else None)

    def test_corrected_quote_and_edition_links_are_published_together(self):
        refs={r['id']:r for e in self.entities.values() for r in e['evidence_refs']}
        self.assertIn('堂東有扶桑海',refs['B2:G13']['quote'])
        self.assertIn('柰林西有都堂',refs['B2:G13']['quote'])
        self.assertNotIn('城之西北門也',refs['B4:NG15']['quote'])
        self.assertIn('现代校注',refs['B4:NG15']['reading'])
        self.assertIn('B0077/3',refs['v2.7:N14']['url'])
        self.assertTrue(all(r.get('text_checked') for r in refs.values() if r['id'] in {x['key'] for x in self.review['records']}))
        self.assertEqual(len(self.data['map_decisions']),11)
        self.assertIn('TXT08',{x['id'] for x in self.data['map_decisions']})

    def test_temporal_uncertainty_is_visible_in_entity_records(self):
        for e in self.entities.values():
            self.assertTrue(e.get('temporal_label'))
            if e['temporal_state']=='undated':self.assertTrue('年代' in e['temporal_label'] or '未' in e['temporal_label'])
        self.assertEqual(self.entities['ic_fusang']['kind'],'water')
        self.assertNotIn('geographic_geometry',self.entities['ic_fusang'])
        self.assertNotIn('geographic_geometry',self.entities['gate_xuanyang'])

    def test_geographic_bindings_are_only_explicit_reviewed_source_bindings(self):
        source={f['id']:f for f in self.geo['features']}
        for e in self.entities.values():
            expected=[f for f in source.values() if f.get('entity_id')==e['id']]
            self.assertEqual(e['source_feature_ids'],[f['id'] for f in expected])
            if expected:
                self.assertEqual(e['geographic_geometry']['geometries'],[f['geometry'] for f in expected])
                self.assertFalse(e['geographic_geometry']['absolute_accuracy_verified'])
                self.assertEqual(e['geographic_geometry']['source_crs'],'EPSG:4610')
            else:self.assertNotIn('geographic_geometry',e)
        self.assertEqual(self.info['prosperity']['located_entities'],11)
        self.assertNotIn('geo-changhe-palace-gate',self.entities['gate_changhe_west']['source_feature_ids'])

    def test_map_and_oblique_share_source_geometry_and_separate_modern_references(self):
        expected={f['id'] for f in self.geo['features']}
        for filename in ['source-layout.svg','layout-panorama.svg']:
            root=ET.parse(SITE/'prosperity'/filename).getroot()
            features={n.get('data-feature-id'):n for n in root.iter() if n.get('data-feature-id')}
            self.assertEqual(set(features),expected)
            modern=next(n for n in root.iter() if n.get('data-layer')=='modern_reference')
            self.assertEqual({n.get('data-feature-id') for n in modern.iter() if n.get('data-feature-id')},{'geo-modern-luo-river','geo-modern-mang-hill-label'})
            envelope=features['geo-palace-layout-envelope']
            self.assertTrue(all(n.get('stroke')=='none' for n in envelope if n.tag==NS+'path'))
            for fid in ['geo-inner-wall-aboveground','geo-inner-wall-underground','geo-palace-walls']:
                self.assertTrue(all('Z' not in n.get('d','') for n in features[fid] if n.tag==NS+'path'))
        for key in ['projection','panorama_projection']:
            p=self.data[key]
            self.assertEqual(p['source_crs'],'EPSG:4610')
            self.assertFalse(p['datum_conversion_performed'])
            self.assertFalse(p['heights_reconstructed'])
        self.assertEqual(self.data['projection']['projection_pipeline'],self.data['panorama_projection']['projection_pipeline'])

    def test_all_prior_public_assets_remain_byte_identical(self):
        preservation=read(SITE/'prosperity/preservation.json')
        self.assertTrue(preservation['protected_unchanged'])
        self.assertGreater(len(preservation['protected_files']),390)
        for path,digest in preservation['protected_files'].items():
            self.assertEqual(hashlib.sha256((SITE/path).read_bytes()).hexdigest(),digest,path)
            self.assertEqual(self.info['files_sha256'][path],digest,path)

    def test_downloads_are_real_complete_artifacts_with_bounded_metadata(self):
        pdf=PdfReader(SITE/'downloads/prosperity-v1-atlas.pdf')
        self.assertEqual(len(pdf.pages),6)
        with zipfile.ZipFile(SITE/'downloads/prosperity-v1-package.zip') as z:
            self.assertIsNone(z.testzip())
            self.assertTrue({'prosperity/data.json','prosperity/source-core.svg','entities.csv','README.txt'}<=set(z.namelist()))
        for field in ['wgs84_registration_completed','ancient_ground_surface_reconstructed','full_city_reconstruction_completed']:
            self.assertFalse(self.info['prosperity'][field])
        for d in self.data['downloads']:
            path=d['url'].removeprefix('./')
            self.assertTrue((SITE/path).is_file())
            self.assertEqual(hashlib.sha256((SITE/path).read_bytes()).hexdigest(),self.info['files_sha256'][path])
        self.assertIn('id="prosperity-entry"',(SITE/'index.html').read_text())

if __name__=='__main__':unittest.main()
