"""Independent re-computation from declared inputs; never imports/executes author calculator."""
from pathlib import Path
from decimal import Decimal as D
import json,math,hashlib
import numpy as np
ROOT=Path('/workspace/scratch/f1dbf35eff8a/luoyang-city/research')
OUT=Path('/workspace/scratch/f1dbf35eff8a/research-web-20261128/mechanics-colour')
pfile=ROOT/'yongning-reconstruction-survey-20261128/design-parameters.json'
rfile=ROOT/'yongning-structure-colour-v6-20261128/mechanics-results.json'
cfile=rfile.with_name('calculate_mechanics.py')
p=json.loads(pfile.read_text());saved=json.loads(rfile.read_text())
b=[D(str(x)) for x in p['body_widths_m_assumed']]
z0=D(str(p['base_height_m']));ztip=D(str(p['total_height_m_assumed']))
z=[D(str(x)) for x in p['floor_datums_m_assumed'][1:]]+[D(str(p['ninth_roof_peak_height_m_assumed']))]
h=[z[0]-z0]+[z[i]-z[i-1] for i in range(1,len(z))]
outer=[x+2*D(str(p['eaves_overhang_per_side_m_assumed'])) for x in b]
fa=[x*x for x in b]
ra=[D('1.10')*(outer[i]*outer[i]-(b[i+1]*b[i+1] if i<8 else 0)) for i in range(9)]
def arrays(qf,qr,pressure,extra_top_weight=0):
 w=[D(str(qf))*fa[i]+D(str(qr))*ra[i] for i in range(9)]
 w[-1]+=D(str(extra_top_weight))
 f=[D(str(pressure))*outer[i]*h[i] for i in range(9)]
 ffin=D(str(pressure))*3*(ztip-z[-1]);zfin=(ztip+z[-1])/2
 feq=ffin*(zfin-z0)/(z[-1]-z0)
 real_shear=sum(f)+ffin
 cm=sum(f[i]*(z[i]-h[i]/2-z0) for i in range(9))+ffin*(zfin-z0)
 f[-1]+=feq
 nm=sum(f[i]*(z[i]-z0) for i in range(9))
 return np.array(list(map(float,w))),np.array(list(map(float,f))),{'real_shear_kN':float(real_shear),'nodal_shear_kN':float(sum(f)),'centroid_moment_kNm':float(cm),'raised_moment_kNm':float(nm),'finial_force_kN':float(ffin),'finial_roof_equivalent_force_kN':float(feq)}
H=np.array(list(map(float,h)));B=np.array(list(map(float,b)))
# D transforms node displacements to storey differences, base displacement=0.
Dmat=np.eye(9)
for i in range(1,9):Dmat[i,i-1]=-1
case_checks=[];max_u_err=0.;max_k_err=0.;max_eta_err=0.;max_T_err=0.;max_pd_err=0.;all_status=True
selected=[]
for s in saved['lateral_scenarios']:
 w,f,wind=arrays(s['q_floor_assembly_kPa'],s['q_roof_kPa'],s['effective_pressure_kPa'],s.get('extra_top_weight_kN_assumed',0))
 P=np.array([sum(w[i:]) for i in range(9)])
 V=np.array([sum(f[i:]) for i in range(9)])
 side=s['equivalent_square_base_side_m']*B/B[0]
 I=side**4/12
 kref=s['equivalent_column_count_per_story']*12*(s['E_GPa']*1e6)*I/H**3
 kg=P/H;k=s['eta_fraction_of_fixed_end_bound']*kref-kg
 K=Dmat.T@np.diag(k)@Dmat
 fail=[i+1 for i,ki in enumerate(k) if ki<=0]
 eta_pos=max(kg/kref);eta_screen=max((kg+V/(H*.005))/kref)
 max_k_err=max(max_k_err,float(max(abs(k-np.array(s['k_effective_kN_per_m'])))))
 max_eta_err=max(max_eta_err,abs(eta_screen-s['eta_needed_for_chosen_1_over_200_drift_screen']))
 details={'id':s['id'],'failed_storeys':fail,'eta_positive':float(eta_pos),'eta_screen':float(eta_screen),'minimum_effective_spring_kN_m':float(min(k)),'min_matrix_eigenvalue_kN_m':float(min(np.linalg.eigvalsh(K)))}
 if fail:
  assert s['roof_displacement_m'] is None and s['failed_story_indices_1based']==fail
  assert details['min_matrix_eigenvalue_kN_m']<=0
 else:
  u=np.linalg.solve(K,f);delta=Dmat@u;ratio=delta/H
  ratio_max=float(max(ratio));roof=float(u[-1])
  expected='passes_only_chosen_linear_drift_screen' if ratio_max<=.005 else 'exceeds_chosen_drift_screen'
  if ratio_max>.02:expected='large_drift_linear_value_diagnostic_only'
  all_status=all_status and expected==s['status']
  eig=np.linalg.eigvals(np.diag(9.81/w)@K)
  assert max(abs(eig.imag))<1e-8 and min(eig.real)>0
  period=2*math.pi/math.sqrt(min(eig.real))
  extra_gravity_moment=float(w@u)
  max_pd_err=max(max_pd_err,abs(extra_gravity_moment-s['gravity_secondary_base_moment_kNm']),abs(wind['raised_moment_kNm']+extra_gravity_moment-s['primary_plus_gravity_base_moment_kNm']))
  max_u_err=max(max_u_err,max(abs(u-np.array(s['node_displacement_m']))))
  max_T_err=max(max_T_err,abs(period-s['fundamental_period_s']))
  details.update({'roof_node_z_m':float(z[-1]),'roof_displacement_m':roof,'max_drift_ratio':ratio_max,'period_s':float(period),'max_equilibrium_residual_kN':float(max(abs(K@u-f))),'extra_PDelta_base_moment_kNm':extra_gravity_moment,'first_plus_PDelta_moment_kNm':wind['raised_moment_kNm']+extra_gravity_moment,'first_story_hand_delta_m':float(V[0]/k[0]),'first_story_matrix_delta_m':float(delta[0]),'first_order_roof_displacement_m':float(sum(V/(s['eta_fraction_of_fixed_end_bound']*kref))),'status':expected})
 if s['id'] in ['sq1-eta0.03-p1','sq1-eta0.3-p1','sq1-eta1-p1','sq1.2-eta0.5-p1','extra-top-weight-500kN','extra-top-weight-2000kN']:
  selected.append(details)
 case_checks.append(details)
assert all_status
w,f,wi=arrays(6,4,1);W=float(sum(w));M=wi['raised_moment_kNm'];peak=2*W/64+M/(16*float(b[0]))
inertia_checks=[]
inertia_max={'base_shear_kN':0.,'base_moment_kNm':0.,'roof_displacement_m':0.,'drift_ratio':0.}
for q in saved.get('horizontal_inertia_static_sensitivity',[]):
 s=next(x for x in saved['lateral_scenarios'] if x['id']==q['frame_case'])
 # All named frames use central gravity; compute the imposed force field afresh.
 coef=D(str(q['horizontal_inertia_coefficient_assumed']))
 ww=[D('6')*fa[i]+D('4')*ra[i] for i in range(9)]
 denominator=sum(ww[i]*(z[i]-z0) for i in range(9))
 force=np.array([float(coef*sum(ww)*ww[i]*(z[i]-z0)/denominator) for i in range(9)])
 ptotal=np.array([float(sum(ww[i:])) for i in range(9)])
 side=s['equivalent_square_base_side_m']*B/B[0]
 k=s['eta_fraction_of_fixed_end_bound']*s['equivalent_column_count_per_story']*(s['E_GPa']*1e6)*side**4/H**3-ptotal/H
 assert min(k)>0
 K=Dmat.T@np.diag(k)@Dmat
 u=np.linalg.solve(K,force)
 drift=Dmat@u/H
 values={'base_shear_kN':float(sum(force)),'base_moment_kNm':float(force@np.array([float(x-z0) for x in z])), 'roof_displacement_m':float(u[-1]), 'drift_ratio':float(max(drift))}
 mappings={'base_shear_kN':'base_shear_kN','base_moment_kNm':'base_moment_about_plinth_top_kNm','roof_displacement_m':'roof_displacement_m','drift_ratio':'max_interstory_drift_ratio'}
 for a,bb in mappings.items():inertia_max[a]=max(inertia_max[a],abs(values[a]-q[bb]))
 expected='passes_only_chosen_static_drift_screen' if values['drift_ratio']<=.005 else 'exceeds_chosen_drift_screen'
 if values['drift_ratio']>.02:expected='large_drift_linear_value_diagnostic_only'
 assert expected==q['status']
 assert math.isclose(values['base_shear_kN'],float(coef)*W,rel_tol=1e-13)
 inertia_checks.append({'frame_case':q['frame_case'],'C':float(coef),**values,'status':expected,'max_equilibrium_residual_kN':float(max(abs(K@u-force))), 'extra_PDelta_base_moment_kNm':float(np.array(list(map(float,ww)))@u)})
colmax=0
for row in saved['column_checks']:
 a=row['size_m']**2 if row['shape']=='square' else math.pi*row['size_m']**2/4
 I=row['size_m']**4/12 if row['shape']=='square' else math.pi*row['size_m']**4/64
 ne=math.pi**2*8e6*I/(row['effective_length_factor']*row['clear_length_assumption_m'])**2
 colmax=max(colmax,abs(ne-row['ideal_Euler_Pcr_kN']),abs(peak/a/1000-row['axial_demand_MPa']))
coremax=0
for row in saved['core_self_weight_scenarios']:
 height=row['height_assumed_m'];a=row['base_side_m'];btop=row['top_side_assumed_m'];gamma=row['unit_weight_assumed_kN_m3']
 v=height*(a*a+a*btop+btop*btop)/3;wg=gamma*v
 coremax=max(coremax,abs(v-row['volume_m3']),abs(wg-row['self_weight_kN']),abs(wg/a/a/1000-row['base_mean_self_compression_MPa']))
eavemax=0
for row in saved['eaves_cantilever_screen']:
 bw=row['beam_width_m_assumed'];dep=row['beam_depth_m_assumed'];L=row['cantilever_length_m_assumed']
 # Independent local roof load: same 1.10 slope-area convention as main gravity.
 q=float(D('4')*D('1.10')*b[0]/D('9'))
 assert math.isclose(row['roof_surface_area_factor'],1.10,abs_tol=1e-12)
 assert math.isclose(row['tributary_width_m_assumed'],float(b[0]/D('9')),abs_tol=1e-12)
 I=bw*dep**3/12;Mloc=q*L**2/2;S=bw*dep**2/6;tip=q*L**4/(8*8e6*I)
 eavemax=max(eavemax,abs(q-row['line_load_kN_m']),abs(q*L-row['root_vertical_reaction_kN']),abs(Mloc-row['root_moment_kNm']),abs(tip-row['elastic_tip_deflection_m']),abs(Mloc/S/1000-row['required_bending_stress_MPa']))
assert max_pd_err<1e-7 and eavemax<1e-7
# Unit tests are distinct elementary identities, not copies of source main().
kk=1000.;pp=1900.;hh=19.;vv=100.
one=vv/(kk-pp/hh)
assert math.isclose(one,1/9)
# Preserve source hashes and record explanatory scope of corrected mechanics.
report={'scope':'independent_formula_and_Dt_diagK_D_matrix_recompute_not_historical_validation','inputs':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [pfile,cfile,rfile]},'cases_checked':len(case_checks),'saved_statuses_match':all_status,'horizontal_inertia_cases_checked':len(inertia_checks),'horizontal_inertia_max_absolute_errors':inertia_max,'horizontal_inertia_independent_results':inertia_checks,'max_absolute_errors':{'k_kN_m':max_k_err,'displacements_m':float(max_u_err),'eta':float(max_eta_err),'period_s':float(max_T_err),'PDelta_moments_kNm':float(max_pd_err),'column_Euler_or_stress':colmax,'core_values':coremax,'eaves_values':eavemax},'geometry':{'sum_floor_assembly_area_m2':float(sum(fa)),'sum_roof_area_m2':float(sum(ra)),'node_z_m':list(map(float,z)),'story_h_m':list(map(float,h))},'weight_kN':W,'wind':wi,'peak_column_demand_kN':peak,'selected':selected,'all_case_summary':case_checks,'additional_interpretation_checks':{'roof_node_is_not_finial_tip':True,'first_order_global_moments_omit_extra_sum_Wu':True,'mass_fixed_while_stiffness_section_or_count_changes':True}}
(OUT/'v6-independent-calculation-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k in ['cases_checked','saved_statuses_match','horizontal_inertia_cases_checked','horizontal_inertia_max_absolute_errors','max_absolute_errors','geometry','weight_kN','wind','peak_column_demand_kN','selected']},ensure_ascii=False,indent=2))
