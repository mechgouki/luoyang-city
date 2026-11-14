"""Regression gates for text layers, excerpt integrity and nonentity references."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from prosperity_text_audit import (CbetaReader, EVIDENCE_INPUTS, OUTPUT, ROOT,
                                    WikiReader, literal_references, normalize,
                                    sequence_match, stream, validate)


class SourceLayerTests(unittest.TestCase):
    def test_modern_inline_annotation_is_not_ancient_subcommentary(self):
        html = '''<div class="div-commentary">
        <span class="t" l="0082a09">瑤光寺北有承明門，</span>
        <small class="inline-note"><span class="t" l="0082a09">城之西北門也。</span></small>
        <span class="t" l="0082a09">有金墉城，即魏氏所築。</span></div>'''
        reader = CbetaReader()
        reader.feed(html)
        body, loc = stream(reader.units)
        note, _ = stream(reader.units, True)
        self.assertIsNotNone(sequence_match('瑤光寺北有承明門，有金墉城，即魏氏所築。', body, loc))
        self.assertNotIn('城之西北門', body)
        self.assertIn('城之西北門也', note)
        self.assertIsNone(sequence_match('瑤光寺北有承明門，城之西北門也。有金墉城', body))

    def test_unmarked_omission_and_changed_historical_nouns_do_not_pass(self):
        body = normalize('在建春門外陽渠南。寺南有租塲。陽渠北有建陽里。')
        self.assertIsNone(sequence_match('在建春門外陽渠南。陽渠北有建陽里。', body))
        self.assertIsNotNone(sequence_match('在建春門外陽渠南。……陽渠北有建陽里。', body))
        self.assertIsNone(sequence_match('碑西有都堂', normalize('柰林西有都堂')))
        self.assertIsNone(sequence_match('堂東有扶桑殿', normalize('堂東有扶桑海')))
        self.assertNotEqual(normalize('婬穢'), normalize('淫穢'))

    def test_excerpt_order_must_be_preserved(self):
        self.assertIsNone(sequence_match('太廟……太社', normalize('太社前又東逕太廟南')))
        self.assertIsNotNone(sequence_match('太社……太廟', normalize('太社前又東逕太廟南')))

    def test_wiki_small_text_rule_depends_on_edition(self):
        html = '<div class="mw-parser-output">太社。<small>將作曹南。</small>司州。</div>'
        keep, drop = WikiReader(False), WikiReader(True)
        keep.feed(html)
        drop.feed(html)
        self.assertIn('將作曹南', ''.join(keep.parts))
        self.assertNotIn('將作曹南', ''.join(drop.parts))


class PublishedLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(OUTPUT.read_text())
        cls.rows = {r['key']: r for r in cls.data['records']}
        cls.refs = cls.data['constraint_references']

    def test_full_legacy_coverage_and_original_quotes_are_preserved(self):
        expected = {}
        for batch, path, field, _ in EVIDENCE_INPUTS:
            records = json.loads((ROOT / path).read_text())[field]
            expected.update({batch + ':' + r['id']: r['quote'] for r in records})
        self.assertEqual({k: r['legacy_quote'] for k, r in self.rows.items()}, expected)
        for source in self.data['inputs']:
            self.assertEqual(hashlib.sha256((ROOT / source['path']).read_bytes()).hexdigest(), source['sha256'])
        validate(self.data)

    def test_full_literal_reference_coverage_without_identity_promotion(self):
        entities = json.loads((ROOT / 'data/entities.json').read_text())
        self.assertEqual(self.refs, literal_references(entities))
        self.assertEqual(len(self.refs), 236)
        self.assertEqual(sum(r['resolution_class'] == 'unique_catalog_name_link' for r in self.refs), 198)
        self.assertTrue(all(not r['historical_identity_verified'] for r in self.refs))
        by_target = {r['raw_target']: r for r in self.refs}
        self.assertEqual(by_target['白象']['resolution_class'], 'nonbuilt_object')
        self.assertEqual(by_target['白象']['candidate_entity_ids'], [])
        self.assertEqual(by_target['南北']['resolution_class'], 'orientation_value')
        self.assertEqual(by_target['寺院']['resolution_class'], 'self_extent_attribute')
        self.assertEqual(by_target['庄严寺／东安里']['candidate_entity_ids'], ['v2_zhuangyan', 'li_dongan'])
        self.assertEqual(by_target['汉濯龙园']['resolution_class'], 'disputed_period_identity_claim')
        self.assertEqual(by_target['city_reference_in_jinyong_context']['candidate_entity_ids'], [])

    def test_corrections_retain_body_note_boundary_and_prior_provenance(self):
        g13 = self.rows['B2:G13']['manual_context_review']
        self.assertIn('柰林西有都堂', g13['corrected_quote'])
        self.assertIn('堂東有扶桑海', g13['corrected_quote'])
        self.assertNotIn('園中有柰林', g13['corrected_quote'])
        ng15 = self.rows['B4:NG15']['manual_context_review']
        self.assertNotIn('城之西北門', ng15['corrected_quote'])
        self.assertEqual(ng15['editorial_note']['layer'], '现代夹注')
        g15 = self.rows['B2:G15']['manual_context_review']
        self.assertEqual(g15['prior_correction'], 'B8:CB14')
        self.assertFalse(g15['new_historical_discovery'])
        self.assertEqual(self.rows['v2.5:E18']['record_role'], 'project_logic_with_ancient_quote')

    def test_counts_describe_matching_not_all_version_collation(self):
        c = self.data['counts']
        self.assertEqual((c['legacy_quote_sequence_match_records'], c['manual_exception_records']), (172, 11))
        self.assertEqual(c['secondary_edition_difference_reviews'], 10)
        self.assertEqual(c['version_readings_identified_not_arbitrated'], 10)
        self.assertEqual(c['new_substantive_project_quote_errors'], 2)
        self.assertEqual(c['new_ancient_absolute_coordinates'], 0)
        for row in self.rows.values():
            manual = row['manual_context_review']
            if manual:
                self.assertTrue(all(x['segments'] for x in manual['corrected_excerpt_checks']))
                self.assertTrue(all(x['segments'] for x in manual['source_contexts']))
        self.assertTrue(all(s['sha256'] and s['bytes'] > 0 for s in self.data['source_snapshots']))
        self.assertTrue(all(not s['manuscript_or_print_scan_checked'] for s in self.data['source_snapshots']))


if __name__ == '__main__':
    unittest.main()
