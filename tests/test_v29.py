"""Temporal semantics are separate from visual/browser acceptance."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from chronology_v29 import relation_to
D=json.loads((ROOT/'research/v2.9/dossiers.json').read_text())
R={r['id']:r for r in D['records']}
class Dates(unittest.TestCase):
 def test_exact_event_is_not_persistent_state(self):
  self.assertEqual(relation_to(R['T29-02']['date'],534),'at');self.assertEqual(relation_to(R['T29-02']['date'],547),'before')
  self.assertIsNone(R['T29-02']['state_valid_to'])
 def test_interval_is_not_whole_period_event(self):
  d=R['T29-04']['date'];self.assertEqual(relation_to(d,523),'overlap');self.assertEqual(relation_to(d,547),'before')
 def test_future_not_visible_as_past(self):self.assertEqual(relation_to(R['T29-20']['date'],528),'later')
 def test_alternative_years_not_continuous_interval(self):
  d=R['T29-16']['date'];self.assertEqual(d['kind'],'alternatives');self.assertNotIn('start',d)
  self.assertEqual(relation_to(d,529),'alternatives');self.assertEqual(relation_to(d,547),'before')
 def test_lower_bound_remains_unclosed(self):
  self.assertEqual(relation_to(R['T29-18']['date'],547),'lower_bound');self.assertEqual(relation_to(R['T29-18']['date'],528),'later')
 def test_narrator_now_not_547(self):self.assertEqual(relation_to(R['T29-07']['date'],547),'unanchored')
 def test_undated_repairs_not_exact_year(self):self.assertEqual(relation_to(R['T29-11']['date'],547),'undated')
 def test_unknown_date_type_rejected(self):
  with self.assertRaises(ValueError):relation_to({'kind':'invented'},547)
class Research(unittest.TestCase):
 def test_counts_and_unique_identifiers(self):
  self.assertEqual(len(D['dossiers']),12);self.assertEqual(len(R),25);self.assertEqual(len({d['site_id'] for d in D['dossiers']}),12)
 def test_every_record_has_source_scope_and_limit(self):
  sources={s['id'] for s in D['sources']};ids={d['id'] for d in D['dossiers']}
  for r in R.values():
   self.assertIn(r['source_id'],sources);self.assertIn(r['dossier_id'],ids)
   for k in ('quote','scope','locator','interpretation_limit'):self.assertTrue(r[k])
 def test_fire_only_tower(self):self.assertEqual(R['T29-02']['scope'],'九层塔');self.assertEqual(R['T29-02']['prior_event_id'],'T05')
 def test_jingle_activity_not_temple_fire(self):
  r=R['T29-12'];self.assertEqual(r['scope'],'表演活动');self.assertEqual(r['kind'],'activity_change');self.assertNotEqual(r['date']['kind'],'year')
 def test_yaoguang_intrusion_not_fire(self):self.assertEqual(R['T29-14']['kind'],'intrusion')
 def test_two_jianzhong_not_merged(self):
  a=next(d for d in D['dossiers'] if d['id']=='D29-07');b=next(d for d in D['dossiers'] if d['id']=='D29-08');self.assertNotEqual(a['site_id'],b['site_id'])
 def test_portable_stones_not_palace_school(self):
  r=R['T29-09'];self.assertEqual(r['subject_id'],'v3_shijing');self.assertEqual(r['site_id'],'v3_hanguozixue');self.assertNotEqual(r['site_id'],'ic_guozixue')
 def test_explicit_completion_not_transferred_to_jingming(self):
  self.assertEqual(R['T29-20']['date']['year'],533)
  self.assertFalse(any(r['kind']=='completion' for r in R.values() if r['dossier_id']=='D29-02'))
 def test_547_unknown_not_mass_ruin(self):self.assertTrue(all(d['status_at_547']=='unknown' for d in D['dossiers']))
 def test_no_fabricated_status_intervals(self):self.assertTrue(all(r['state_valid_from'] is None and r['state_valid_to'] is None for r in R.values()))
 def test_prior_event_links_not_duplicate_claims(self):
  links=[r['prior_event_id'] for r in R.values() if 'prior_event_id' in r];self.assertEqual(len(links),len(set(links)))
 def test_all_source_versions_one_family(self):self.assertEqual({s['family'] for s in D['sources']},{'L'})
if __name__=='__main__':unittest.main()
