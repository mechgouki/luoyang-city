"""Scientific semantic tests, separate from website deployment tests."""
import sys,json,unittest,itertools
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from qualitative_space import Model,select,minimal_core
from normalize_v26 import normalize
from model_v26 import build_atoms,scenarios,SHORT

def order(i,lo,hi,axis='x',**kw):return dict(id=i,kind='order',less=lo,more=hi,axis=axis,**kw)
def member(i,node,v,phase='t0',boundary='city'):return dict(id=i,kind='membership',node=node,value=v,phase=phase,boundary=boundary)
def alias(i,a,b,domain='entity'):return dict(id=i,kind='alias',a=a,b=b,domain=domain)

class Semantics(unittest.TestCase):
 def test_direction_reversal(self):
  a=[order('a','Y','T'),order('b','T','Y')]
  self.assertFalse(Model(a).sat);self.assertEqual(set(minimal_core(a)),{'a','b'})
 def test_west_plus_east_does_not_decide_road_side(self):
  a=[order('a','Y','R'),order('b','Y','T')]
  for lo,hi in [('T','R'),('R','T')]:self.assertTrue(Model(a+[order('q',lo,hi)]).sat)
  self.assertEqual(Model(a).query(order('q','T','R'))['status'],'undetermined')
 def test_sequence_omission_is_not_absence(self):
  a=[order('1','ice','she','y'),order('2','she','jiuji','y'),order('3','jiuji','jiang','y'),
     order('4','sizhou','she','y'),order('5','ice','sizhou','y'),order('6','she','jiang','y')]
  self.assertTrue(Model(a).sat);self.assertEqual(Model(a).query(order('q','sizhou','jiuji','y'))['status'],'entailed')
 def test_homonymous_gates_are_not_merged(self):
  a=[order('1','temple','palace_changhe','y'),order('2','west_changhe','temple','y')]
  self.assertTrue(Model(a).sat)
  self.assertFalse(Model(a+[alias('3','palace_changhe','west_changhe')]).sat)
 def test_front_does_not_imply_south(self):
  m=Model([dict(id='front',kind='note',quote='太社前')])
  self.assertEqual(m.query(order('q','water','altar','y'))['status'],'undetermined')
 def test_time_and_boundary_not_silently_collapsed(self):
  a=[member('1','M','inside','a','A'),member('2','M','outside','b','B')]
  self.assertTrue(Model(a).sat)
  self.assertTrue(Model(a+[alias('t','a','b','phase')]).sat)
  self.assertFalse(Model(a+[alias('t','a','b','phase'),alias('r','A','B','reference')]).sat)
 def test_identity_time_boundary_all_required(self):
  a=[member('1','inner','inside','a','A'),member('2','outer','outside','b','B'),
     alias('i','inner','outer'),alias('t','a','b','phase'),alias('r','A','B','reference')]
  self.assertEqual(set(minimal_core(a)),{'1','2','i','t','r'})
 def test_dependencies_are_removed_with_source(self):
  a=[dict(id='source',kind='note',families=['L']),order('inherit','T','R',requires=['source'],group='w',families=['L'])]
  self.assertEqual(Model(a).query(order('q','T','R'))['status'],'entailed')
  self.assertEqual(Model(a[1:]).query(order('q','T','R'))['status'],'undetermined')
  self.assertEqual(select(a,{'w'},['L']),[])
 def test_witnesses_satisfy_edges_after_monotone_rescaling(self):
  a=[order('1','Y','T'),order('2','T','ic_palace_avenue'),order('3','Y','ic_changhe_palace','y')]
  w=Model(a).witness(['Y','T','ic_palace_avenue','ic_changhe_palace'])
  for factor in [.01,1,10000]:
   for c in a:self.assertLess(factor*w[c['axis']][c['less']]+77,factor*w[c['axis']][c['more']]+77)
 def test_exhaustive_small_graph_feasibility_and_entailment(self):
  # Independent permutation oracle for every directed graph on 3 objects (64 graphs).
  pairs=list(itertools.permutations('abc',2))
  for mask in range(64):
   a=[order(str(i),u,v) for i,(u,v) in enumerate(pairs) if mask>>i&1]
   valid=[p for p in itertools.permutations('abc') if all(p.index(c['less'])<p.index(c['more']) for c in a)]
   m=Model(a);self.assertEqual(m.sat,bool(valid))
   if valid:
    for u,v in pairs:
     expected=all(p.index(u)<p.index(v) for p in valid)
     self.assertEqual(m.query(order('q',u,v))['status']=='entailed',expected)

class Registry(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.entities=json.loads((ROOT/'data/entities.json').read_text())
  cls.registry=normalize(cls.entities)
  cls.atoms=build_atoms(json.loads((ROOT/'research/v2.5/evidence.json').read_text()))
  cls.cases={s['id']:s for s in scenarios(cls.atoms)}
 def test_all_482_relations_losslessly_retained(self):
  self.assertEqual(len(self.registry['records']),482)
  self.assertEqual(self.registry['metrics']['target_field_contains_existing_id'],85)
  self.assertEqual(self.registry['metrics']['target_status']['explicit_id'],245)
  self.assertEqual(len({r['id'] for r in self.registry['records']}),482)
 def test_broken_old_id_preserved_as_unresolved(self):
  r=next(r for r in self.registry['records'] if r['original'].get('target_id')=='city_jinyang')
  self.assertEqual(r['target']['status'],'unresolved');self.assertEqual(r['target']['candidates'],[])
 def test_ambiguous_name_never_automerge(self):
  E=[{'id':'a','name':'同名寺','type':'temple'},{'id':'b','name':'同名寺','type':'temple'},
    {'id':'c','name':'甲','type':'temple','constraints':[{'relation':'east_of','target':'同名寺'}]}]
  r=normalize(E)['records'][0];self.assertEqual(r['target']['status'],'name_ambiguous');self.assertEqual(r['target']['candidates'],['a','b'])
 def test_has_east_projection_orientation(self):
  r=next(r for r in self.registry['records'] if r['subject_id']=='ic_yongning' and r['relation_raw']=='has_east')
  self.assertEqual(r['projection_template']['less'],'subject');self.assertEqual(r['projection_template']['more'],'target')
 def test_all_18_cards_atomized_and_dependencies_valid(self):
  self.assertEqual(len({a['evidence_id'] for a in self.atoms}),18)
  ids={a['id'] for a in self.atoms};self.assertEqual(len(ids),len(self.atoms))
  for a in self.atoms:self.assertTrue(set(a['requires'])<=ids)
 def test_sixteen_scenarios(self):
  self.assertEqual(len(self.cases),16)
  self.assertEqual([c['id'] for c in self.cases.values() if not c['sat']],['ritual111'])
 def test_road_side_sensitivity(self):
  q=lambda c,i:next(q for q in self.cases[c]['queries'] if q['id']==i)['status']
  self.assertEqual(q('s111','taiwei_west'),'entailed');self.assertEqual(q('s011','taiwei_west'),'undetermined')
  self.assertEqual(q('s110','jingle_east'),'entailed');self.assertEqual(q('s100','jingle_east'),'undetermined')
 def test_provenance_support_includes_enabling_evidence(self):
  q=next(q for q in self.cases['s110']['queries'] if q['id']=='jingle_east')
  self.assertTrue({'F08','F09','GES','F22'}<=set(q['support_subset']))
 def test_full_certificate_checks_unplotted_nodes_too(self):
  for case in self.cases.values():
   certificate=case['witness_certificate']
   if not case['sat']:
    self.assertIsNone(certificate);continue
   ranks={axis:{tuple(r['context']):r['rank'] for r in values} for axis,values in certificate['rank_assignment'].items()}
   for edge in certificate['checked_edges']:
    self.assertLess(ranks[edge['axis']][tuple(edge['less'])],ranks[edge['axis']][tuple(edge['more'])])
   self.assertEqual(set(certificate['active_atom_ids']),set(case['active_ids']))
 def test_temporal_audit_does_not_invent_dates(self):
  self.assertEqual(self.registry['metrics']['temporal_audit']['event_series_not_reviewed'],253)
  self.assertTrue(all(t['valid_from'] is None and t['valid_to'] is None for t in self.registry['temporal_audit']))

if __name__=='__main__':unittest.main()
