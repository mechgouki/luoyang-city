"""B8 structural ledger regressions that do not require a prebuilt website."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from city_audit_b8 import MASTER_PATH, ROOT, REVIEW_STATUS, build_audit


# Representative actual B7 conventions.  B3's batch is on its parent, a B7
# reading group names multiple entities, and Baoming has an identity condition.
# Other current-master tags are deliberately absent: absence must not mean loss.
MASTER_FIXTURE = '''<svg xmlns="http://www.w3.org/2000/svg">
 <g id="west-glyphs-b3" data-batch="dual-b3" data-footprint="false">
  <g data-entity-id="w_dashi" data-footprint="false" transform="translate(2375,6380)"/>
  <g data-entity-id="w_yangu" data-footprint="false" transform="translate(1535,6395)"/>
 </g>
 <g id="luonan-bridge-b7" data-batch="dual-b7" data-entity-ids="bridge_yong v3_yong_huabiao"
    data-locating-mode="bridge_annotation" data-footprint="false"/>
 <g class="wnode127" data-batch="dual-b6" data-entity-id="v2_baoming"
    data-temporal-display="conditional-identity" data-footprint="false"/>
</svg>'''


class CityAuditB8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.site = Path(cls.temporary.name)
        master = cls.site / MASTER_PATH
        master.parent.mkdir(parents=True)
        master.write_text(MASTER_FIXTURE, encoding='utf-8')
        cls.audit = build_audit(cls.site, source_commit='fixture-review')
        cls.rows = {row['id']: row for row in cls.audit['entities']}

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_all_339_rows_remain_structural_not_new_historical_verifications(self):
        original = json.loads((ROOT / 'data/entities.json').read_text())
        self.assertEqual([row['id'] for row in self.audit['entities']], [row['id'] for row in original])
        self.assertEqual(len(self.rows), 339)
        self.assertEqual(self.audit['source_commit'], 'fixture-review')
        self.assertEqual(self.audit['counts']['new_historical_verifications'], 0)
        for row in self.audit['entities']:
            self.assertEqual(row['review_status'], REVIEW_STATUS)
            self.assertFalse(row['historical_verification_added'])
            self.assertIsNone(row['geographic_coordinates'])
            self.assertIsNone(row['drawing_status']['geographic_coordinates'])
            self.assertEqual(row['case_ids'], [])

    def test_target_entities_and_target_groups_are_counted_separately(self):
        counts = self.audit['counts']
        self.assertEqual({key: counts[key] for key in [
            'targets', 'targeted_entities', 'individual_entities', 'group_entities',
            'no_interactive_target_entities', 'groups', 'shared_or_group_targets',
            'shared_non_group_targets']}, {
                'targets': 179, 'targeted_entities': 237, 'individual_entities': 136,
                'group_entities': 101, 'no_interactive_target_entities': 102,
                'groups': 42, 'shared_or_group_targets': 43, 'shared_non_group_targets': 1})
        reserved = self.rows['ic_donggong_reserved']
        jin_granary = self.rows['ic_taicang_jin']
        self.assertEqual(reserved['marker_state'], 'group_member')
        self.assertEqual(reserved['targets'], jin_granary['targets'])
        self.assertEqual(reserved['targets'][0]['kind'], 'area')
        self.assertEqual(reserved['targets'][0]['member_count'], 2)
        self.assertEqual(self.rows['market_sitong']['marker_state'], 'group_member')
        self.assertEqual(self.rows['market_sitong']['targets'][0]['member_count'], 1)
        self.assertIn('nonspatial_annotation', self.rows['w_yinian']['drawing_status']['baseline_modes'])
        self.assertEqual(self.rows['w_yinian']['marker_state'], 'individual')
        self.assertIsNone(self.rows['w_yinian']['geographic_coordinates'])

    def test_focus_crop_and_unlocated_bridge_are_not_equated(self):
        self.assertEqual(self.audit['counts']['explicit_focus_entities'], 125)
        self.assertEqual(self.audit['counts']['no_explicit_focus_entities'], 214)
        bridge = self.rows['bridge_yong']
        self.assertEqual(bridge['marker_state'], 'no_interactive_target')
        self.assertEqual(bridge['explicit_focus_regions'], ['R10', 'R11'])
        self.assertEqual(bridge['crop_regions'], [])
        self.assertTrue(bridge['drawing_status']['current_master_refs'])
        self.assertEqual(bridge['finding_ids'], [])
        yongning = self.rows['ic_yongning']
        self.assertEqual(yongning['explicit_focus_regions'], ['R06', 'R07'])
        self.assertIn('R07', yongning['crop_regions'])
        self.assertEqual(yongning['drawing_status']['current_master_index_state'], 'no_explicit_entity_tag')
        self.assertFalse(self.audit['policies']['missing_target_or_focus_is_omission'])

    def test_evidence_is_explicit_indexing_and_not_transitive_or_independent_votes(self):
        counts = self.audit['counts']
        self.assertEqual(counts['direct_evidence_records'], 183)
        self.assertEqual(counts['direct_evidence_entities'], 209)
        self.assertEqual(counts['direct_evidence_refs'], 506)
        self.assertFalse(self.audit['policies']['evidence_counts_are_independent_sources'])
        self.assertFalse(self.audit['policies']['derived_v26_models_counted_as_new_evidence'])
        fish_keys = {ref['key'] for ref in self.rows['market_fish']['direct_evidence_refs']}
        sitong_keys = {ref['key'] for ref in self.rows['market_sitong']['direct_evidence_refs']}
        self.assertIn('B7:LR07', fish_keys)
        self.assertNotIn('B7:LR07', sitong_keys)
        self.assertIn('B7:LR10', fish_keys & sitong_keys)  # Explicit comparison is not identity.
        self.assertEqual(self.rows['ic_sanji_jinyang']['direct_evidence_refs'], [])
        for row in self.audit['entities']:
            for ref in row['direct_evidence_refs']:
                self.assertIn(row['id'], ref['entity_ids'])
                self.assertEqual(ref['relation'], 'explicit_reference')
                self.assertTrue(ref['link'].startswith('./'))

    def test_chronology_retains_component_scope_and_site_context(self):
        tower = next(ref for ref in self.rows['ic_yongning']['chronology_refs'] if ref['id'] == 'T29-02')
        self.assertEqual(tower['scope'], '九层塔')
        self.assertIsNone(tower['state_valid_to'])
        stone = next(ref for ref in self.rows['v3_shijing']['chronology_refs'] if ref['id'] == 'T29-09')
        school = next(ref for ref in self.rows['v3_hanguozixue']['chronology_refs'] if ref['id'] == 'T29-09')
        self.assertEqual(stone['role'], 'subject')
        self.assertEqual(stone['scope'], '可移动石经')
        self.assertEqual(school['role'], 'site_context')
        self.assertEqual(school['subject_id'], 'v3_shijing')
        self.assertEqual(self.rows['house_gaoyang']['chronology_refs'], [])
        self.assertEqual(self.rows['house_gaoyang']['chronology_dossiers'][0]['role'], 'related_context')
        self.assertEqual(self.audit['counts']['chronology_records'], 25)
        self.assertEqual(self.audit['counts']['chronology_ref_entities'], 13)

    def test_b3_parent_batch_and_b7_plural_entity_tags_are_both_read(self):
        dashi = self.rows['w_dashi']['drawing_status']['current_master_refs'][0]
        self.assertEqual(dashi['batch'], 'dual-b3')
        self.assertTrue(dashi['batch_inherited'])
        self.assertEqual(dashi['ancestor_group_id'], 'west-glyphs-b3')
        self.assertFalse(dashi['footprint'])
        bridge = self.rows['bridge_yong']['drawing_status']['current_master_refs'][0]
        huabiao = self.rows['v3_yong_huabiao']['drawing_status']['current_master_refs'][0]
        self.assertEqual(bridge, huabiao)
        self.assertEqual(bridge['locating_mode'], 'bridge_annotation')
        self.assertFalse(bridge['batch_inherited'])

    def test_known_external_reference_and_conditional_temporal_reading_stay_explicit(self):
        self.assertNotIn('city_jinyang', self.rows)
        external = self.rows['ic_sanji_jinyang']['constraint_references'][0]
        self.assertEqual(external['resolution'], 'known_external_reference')
        self.assertEqual(external['target_value'], 'city_jinyang')
        baoming = self.rows['v2_baoming']
        self.assertEqual(baoming['legacy_temporal_state'], 'attested_by_528')
        self.assertEqual(baoming['drawing_status']['current_temporal_displays'], ['conditional-identity'])
        findings = {item['code']: item for item in self.audit['findings']}
        self.assertEqual(findings['known_external_reference']['status'], 'retained_external_reference')
        self.assertEqual(findings['legacy_temporal_requires_identity_condition']['entity_ids'], ['v2_baoming'])
        self.assertEqual(self.audit['counts']['structural_issues'], 0)
        self.assertEqual(self.audit['counts']['interpretation_cautions'], 2)
        self.assertEqual(self.audit['counts']['legacy_constraint_references'], {
            'registered_entity_reference': 245, 'known_external_reference': 1,
            'literal_reference_not_resolved': 236})

    def test_builder_is_deterministic_read_only_and_does_not_fallback_when_master_missing(self):
        before = {str(p.relative_to(self.site)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.site.rglob('*') if p.is_file()}
        self.assertEqual(self.audit, build_audit(self.site, source_commit='fixture-review'))
        after = {str(p.relative_to(self.site)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.site.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(list(after), [MASTER_PATH])
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaisesRegex(FileNotFoundError, 'Build B7 first'):
                build_audit(empty)
        with self.assertRaisesRegex(ValueError, 'source_commit'):
            build_audit(self.site, source_commit='')


if __name__ == '__main__':
    unittest.main()
