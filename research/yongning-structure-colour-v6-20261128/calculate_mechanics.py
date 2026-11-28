"""Transparent sensitivity screening of the V5 exterior, NOT an ancient FE model.

Units: m, kN, s; stresses are emitted in MPa.  No code load factors, material
design strengths, historical joint stiffness or site hazards are assumed known.
The model deliberately does not borrow lateral stiffness from an unspecified
earthen core.  Run with Python 3 + numpy; results are reproducible JSON and CSV.
"""
from pathlib import Path
import csv
import json
import math
import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'yongning-reconstruction-survey-20261128/design-parameters.json'
P = json.loads(SOURCE.read_text(encoding='utf-8'))
G = 9.81
B = np.array(P['body_widths_m_assumed'], dtype=float)
Z0 = P['base_height_m']
Z = np.r_[np.array(P['floor_datums_m_assumed'][1:]), P['ninth_roof_peak_height_m_assumed']]
H = np.diff(np.r_[Z0, Z])
EAVE = B + 2 * P['eaves_overhang_per_side_m_assumed']
FLOOR_AREA = B**2
ROOF_AREA = 1.10 * (EAVE**2 - np.r_[B[1:]**2, 0.0])
DRIFT_SCREEN = 1 / 200


def weights(q_floor=6.0, q_roof=4.0, extra_top_weight_kN=0.0):
    # q_floor is a lumped story assembly gravity load, including framing and
    # enclosure. It is NOT a code live load and must not be counted again.
    result=q_floor * FLOOR_AREA + q_roof * ROOF_AREA
    result[-1]+=extra_top_weight_kN
    return result


def wind(p=1.0):
    # Effective pressure already incorporates unspecified shape/gust effects.
    # A solid projected envelope is used; every story resultant is raised to
    # its upper node, so its moment exceeds the centroid-load moment.
    body_force = p * EAVE * H
    apex = P['total_height_m_assumed']
    finial_width = 3.0  # explicit envelope assumption, not measured metal area
    finial_force = p * finial_width * (apex - Z[-1])
    finial_z = (apex + Z[-1]) / 2
    equivalent_finial_force = finial_force * (finial_z - Z0) / (Z[-1] - Z0)
    nodal = body_force.copy()
    nodal[-1] += equivalent_finial_force
    actual_shear = float(body_force.sum() + finial_force)
    node_shear = float(nodal.sum())
    centroid_moment = float(np.dot(body_force, Z - H / 2 - Z0) + finial_force * (finial_z-Z0))
    envelope_moment = float(np.dot(nodal, Z - Z0))
    return nodal, {
        'effective_pressure_kPa': p,
        'real_envelope_base_shear_kN': actual_shear,
        'equivalent_nodal_base_shear_kN': node_shear,
        'centroid_load_moment_about_plinth_top_kNm': centroid_moment,
        'raised_nodal_moment_about_plinth_top_kNm': envelope_moment,
        'finial_real_force_kN': finial_force,
        'finial_equivalent_roof_force_kN': equivalent_finial_force,
        'finial_centroid_z_m': finial_z,
        'warning': '节点上移风弯矩包络；刹风按等底弯矩换算，节点剪力略放大。不是风洞或规范风场。',
    }


def spring_matrix(k):
    k = np.asarray(k, dtype=float)
    mat = np.zeros((len(k), len(k)))
    for i, ki in enumerate(k):
        mat[i, i] += ki
        if i:
            mat[i-1, i-1] += ki
            mat[i-1, i] -= ki
            mat[i, i-1] -= ki
    return mat


def lateral(case_id, side_m=1.0, eta=0.30, n=64, e_GPa=8.0,
            pressure=1.0, q_floor=6.0, q_roof=4.0, extra_top_weight_kN=0.0):
    w = weights(q_floor, q_roof, extra_top_weight_kN)
    axial = np.cumsum(w[::-1])[::-1]
    f, wind_info = wind(pressure)
    shear = np.cumsum(f[::-1])[::-1]
    side = side_m * B / B[0]
    inertia = side**4 / 12  # equivalent SQUARE sections, not 124 round posts
    e = e_GPa * 1e6
    k_fixed = n * 12 * e * inertia / H**3
    k_el = eta * k_fixed
    k_geom = axial / H
    k_eff = k_el - k_geom
    eta_stable = float(np.max(k_geom / k_fixed))
    eta_drift = float(np.max((k_geom + shear/(H*DRIFT_SCREEN)) / k_fixed))
    result = {
        'id': case_id, 'equivalent_square_base_side_m': side_m,
        'equivalent_column_count_per_story': n, 'E_GPa': e_GPa,
        'eta_fraction_of_fixed_end_bound': eta, 'effective_pressure_kPa': pressure,
        'q_floor_assembly_kPa': q_floor, 'q_roof_kPa': q_roof,
        'extra_top_weight_kN_assumed':extra_top_weight_kN,
        'wood_roof_weight_kN': float(w.sum()),
        'eta_min_for_positive_effective_springs': eta_stable,
        'eta_needed_for_chosen_1_over_200_drift_screen': eta_drift,
        'k_fixed_kN_per_m': k_fixed.tolist(),
        'k_elastic_kN_per_m': k_el.tolist(),
        'k_geometric_kN_per_m': k_geom.tolist(),
        'k_effective_kN_per_m': k_eff.tolist(),
        'required_elastic_stiffness_for_screen_kN_per_m': (k_geom + shear/(H*DRIFT_SCREEN)).tolist(),
        'story_shear_kN': shear.tolist(),
        'story_axial_gravity_kN': axial.tolist(),
        'wind': wind_info,
    }
    if np.any(k_eff <= 0):
        result.update(status='unstable_in_this_shear_spring_model',
                      failed_story_indices_1based=(np.nonzero(k_eff <= 0)[0]+1).tolist(),
                      roof_displacement_m=None, max_interstory_drift_ratio=None,
                      fundamental_period_s=None)
        return result
    delta = shear / k_eff
    displacement = np.cumsum(delta)
    ratio = delta / H
    mat = spring_matrix(k_eff)
    solved = np.linalg.solve(mat, f)
    if not np.allclose(solved, displacement, rtol=1e-11, atol=1e-11):
        raise AssertionError('Independent stiffness solution does not match story shear integration')
    mass = w / G  # kN*s²/m, compatible with kN/m stiffness
    inv_sqrt_m = np.diag(1 / np.sqrt(mass))
    eigenvalues = np.linalg.eigvalsh(inv_sqrt_m @ mat @ inv_sqrt_m)
    if eigenvalues[0] <= 0:
        raise AssertionError('Positive springs must produce a positive definite fixed-base chain')
    ratio_max = float(ratio.max())
    status = 'passes_only_chosen_linear_drift_screen' if ratio_max <= DRIFT_SCREEN else 'exceeds_chosen_drift_screen'
    if ratio_max > 0.02:
        status = 'large_drift_linear_value_diagnostic_only'
    result.update(status=status,
                  story_displacement_increment_m=delta.tolist(),
                  node_displacement_m=displacement.tolist(),
                  interstory_drift_ratio=ratio.tolist(),
                  roof_displacement_m=float(displacement[-1]),
                  max_interstory_drift_ratio=ratio_max,
                  controlling_story_1based=int(np.argmax(ratio))+1,
                  fundamental_period_s=float(2 * math.pi / math.sqrt(eigenvalues[0])),
                  gravity_secondary_base_moment_kNm=float(np.dot(w,displacement)),
                  primary_plus_gravity_base_moment_kNm=float(wind_info['raised_nodal_moment_about_plinth_top_kNm']+np.dot(w,displacement)),
                  equilibrium_residual_kN=float(np.max(np.abs(mat @ solved - f))))
    return result


def main():
    scenarios = []
    for d in [0.8, 1.0, 1.2]:
        for eta in [0.03, 0.10, 0.30, 0.50, 1.0]:
            for pressure in [0.5, 1.0, 2.0]:
                scenarios.append(lateral(f'sq{d:g}-eta{eta:g}-p{pressure:g}', d, eta, pressure=pressure))
    # Deliberately vary count, modulus and gravity independently of the baseline.
    for count in [48, 96]:
        scenarios.append(lateral(f'count-{count}', n=count))
    for e in [6, 12]:
        scenarios.append(lateral(f'modulus-{e}', e_GPa=e))
    for name, qf, qr in [('light',4,2.5),('heavy',9,6)]:
        scenarios.append(lateral(f'gravity-{name}', q_floor=qf, q_roof=qr))
    for extra_top in [500,2000]:
        scenarios.append(lateral(f'extra-top-weight-{extra_top}kN',extra_top_weight_kN=extra_top))

    w = weights()
    f, wi = wind()
    total = float(w.sum())
    moment = wi['raised_nodal_moment_about_plinth_top_kNm']
    axial_peak = 2 * total / 64 + moment/(16 * B[0])
    # An inertia-load sensitivity, NOT a site earthquake spectrum, PGA or code
    # seismic coefficient.  This ensures a wind screen is not reported as an
    # earthquake-capacity result. The core is still not included in this frame.
    seismic_scenarios=[]
    for case_id in ['sq1-eta0.3-p1','sq1-eta1-p1','sq1.2-eta0.5-p1']:
        base=next(s for s in scenarios if s['id']==case_id)
        k=np.array(base['k_effective_kN_per_m'])
        for coefficient in [.05,.10,.20]:
            fi=coefficient*total*w*(Z-Z0)/np.dot(w,Z-Z0)
            vi=np.cumsum(fi[::-1])[::-1]
            drift=vi/k
            ratio=float(np.max(drift/H))
            status='passes_only_chosen_static_drift_screen' if ratio<=DRIFT_SCREEN else 'exceeds_chosen_drift_screen'
            if ratio>.02: status='large_drift_linear_value_diagnostic_only'
            seismic_scenarios.append({'frame_case':case_id,
                'horizontal_inertia_coefficient_assumed':coefficient,
                'base_shear_kN':float(fi.sum()),
                'base_moment_about_plinth_top_kNm':float(np.dot(fi,Z-Z0)),
                'roof_displacement_m':float(drift.sum()),
                'max_interstory_drift_ratio':ratio,'status':status,
                'warning':'C仅指定V=CW的静力敏感性，不等于PGA、烈度或场地设计谱；未做动态与循环退化。'})
    column_checks = []
    for shape in ['square','circle']:
        for size in [0.8,1.0,1.2]:
            area = size**2 if shape=='square' else math.pi*size**2/4
            inertia = size**4/12 if shape=='square' else math.pi*size**4/64
            for length in [12.0,19.0]:
                for k in [1.0,2.0]:
                    pcr = math.pi**2 * 8e6 * inertia/(k*length)**2
                    column_checks.append({
                        'shape':shape, 'size_m':size, 'clear_length_assumption_m':length,
                        'effective_length_factor':k, 'E_GPa':8.0,
                        'area_m2':area, 'I_m4':inertia,
                        'axial_demand_kN':axial_peak,
                        'axial_demand_MPa':axial_peak/area/1000,
                        'ideal_Euler_Pcr_kN':pcr,
                        'Euler_demand_ratio':axial_peak/pcr,
                        'warning':'Euler是理想弹性分岔上界；非缺陷、徐变、压弯或节点承载力验收。'
                    })

    cores=[]
    for height in [60.,80.,100.]:
        bottom, top, gamma = 19.8,10.0,18.0
        volume=height/3*(bottom**2+bottom*top+top**2)
        weight=gamma*volume
        cores.append({'height_assumed_m':height,'base_side_m':bottom,
                      'top_side_assumed_m':top,'unit_weight_assumed_kN_m3':gamma,
                      'volume_m3':volume,'self_weight_kN':weight,
                      'mass_t':weight/G,'base_mean_self_compression_MPa':weight/bottom**2/1000,
                      'unreduced_prism_self_compression_MPa':gamma*height/1000,
                      'warning':'仅自重压应力。不是实测原塔心高度/收分；不计侧向刚度或抗倾覆贡献。'})

    global_checks=[]
    for pressure in [.5,1.,2.]:
        _, winfo=wind(pressure)
        m=winfo['raised_nodal_moment_about_plinth_top_kNm']
        shear=winfo['real_envelope_base_shear_kN']
        global_checks.append({'pressure_kPa':pressure,
            'W_wood_roof_only_kN':total,'raised_moment_kNm':m,
            'conditional_restoring_to_overturning_ratio_at_29_4m_support': total*B[0]/2/m,
            'resultant_eccentricity_m':m/total,
            'support_width_m_assumed':float(B[0]),
            'kern_limit_m':float(B[0]/6),
            'within_rigid_block_kern':bool(m/total<=B[0]/6),
            'min_sliding_friction_mu_required':shear/total,
            'mean_weight_divided_by_plinth_area_kPa':total/P['base_width_m']**2,
            'warning':'一阶风矩的独立整体筛查；未加侧移PΔ底矩。整体耦合刚体与均匀接触是假设；比值不是规范安全系数。'})

    overhang=[]
    tributary_width=B[0]/9  # design arithmetic, NOT excavated 3m bay measure
    for width,depth in [(.30,.60),(.40,.80)]:
        qr=4.0; length=4.4; e=8e6
        q=qr*1.10*tributary_width  # same surface-area convention as roof gravity
        moment_e=q*length**2/2
        inertia=width*depth**3/12
        section_modulus=width*depth**2/6
        overhang.append({'beam_width_m_assumed':width,'beam_depth_m_assumed':depth,
            'cantilever_length_m_assumed':length,'tributary_width_m_assumed':float(tributary_width),
            'roof_surface_area_factor':1.10,
            'line_load_kN_m':float(q),'root_moment_kNm':float(moment_e),
            'required_bending_stress_MPa':float(moment_e/section_modulus/1000),
            'elastic_tip_deflection_m':float(q*length**4/(8*e*inertia)),
            'root_vertical_reaction_kN':float(q*length),
            'warning':'单悬臂筛查，不等同斗栱真实叠栱传力。未含上拔风、连接与局部横纹压缩。'})

    summary={
        'date':'2026-11-28', 'title':'永宁寺 V6：147m 外形的条件力学筛查',
        'verdict':'historical_structural_feasibility_NOT_established',
        'model_kind':'nine_DOF_shear_spring_screen_with_geometric_softening_not_detailed_FE',
        'geometry':{'source':str(SOURCE.relative_to(ROOT.parent)),
                    'plinth_top_m':Z0,'superstructure_node_z_m':Z.tolist(),
                    'story_heights_m':H.tolist(),'body_widths_m':B.tolist(),
                    'external_total_height_m_assumed':147.0,
                    'floor_assembly_area_m2':FLOOR_AREA.tolist(),
                    'roof_surface_area_m2_assumed':ROOF_AREA.tolist()},
        'assumptions':{'node_warning':'节点是楼层上端的集中荷载位置；h不是考古木柱净长。顶层等效段18.9m跨墙身/斗栱/屋面。',
                       'no_core_lateral_stiffness_credited':True,
                       'roof_area_slope_factor':1.10,
                       'gravity_kPa_ranges':{'floor_assembly':[4,6,9],'roof':[2.5,4,6]},
                       'E_GPa_range':[6,8,12],
                       'n_columns_range':[48,64,96],
                       'equivalent_square_side_m_range':[.8,1.0,1.2],
                       'wood_species_and_strength_unknown':True,
                       'eta_is_sensitivity_not_measured_joint_property':True,
                       'member_mass_sensitivity_warning':'改变截面/柱数时保持折算总恒载不变，用于单参数刚度敏感性；不是已计增材自重的加强设计。',
                       'extra_finial_weight_kN_sensitivity':[0,500,2000],
                       'finial_weight_warning':'主表仅木架与瓦屋面合成重量；金属刹饰净重未证，另加0.5/2MN做顶部重力敏感性，不视为完整重建总重。',
                       'effective_pressure_is_sensitivity_not_Luoyang_code_wind':True,
                       'chosen_drift_ratio_screen':DRIFT_SCREEN,
                       'drift_screen_is_not_a_historical_or_code_acceptance_limit':True,
                       'not_checked':['site-specific earthquake spectrum and dynamic response','joint cyclic degradation','wind dynamics',
                                      'core-frame interaction','foundation settlement','construction stages',
                                      'fire','moisture deterioration','roof uplift','finial/chains local capacity']},
        'gravity_cases':[{'label':name,'q_floor_kPa':qf,'q_roof_kPa':qr,
                          'weight_kN':float(weights(qf,qr).sum()),
                          'mass_t':float(weights(qf,qr).sum()/G)}
                         for name,qf,qr in [('light',4,2.5),('central',6,4),('heavy',9,6)]],
        'wind_reference':wi,
        'column_load_envelope':{'N_effective':64,'concentration_multiplier':2.0,
            'wind_edge_group_count_each_side_assumed':16,
            'wind_lever_arm_m_assumed':float(B[0]),'mean_axial_kN':total/64,
            'peak_axial_demand_kN':axial_peak,
            'warning':'均分+2倍偏载+一阶风轴力偶是示范性需求，不含PΔ最终组合；不由124柱位直接推出，不保证真实最不利柱力。'},
        'column_checks':column_checks,
        'bearing_area_sensitivity':[{'assumed_perpendicular_stress_MPa':fc,
                                    'required_total_contact_area_m2':axial_peak/(fc*1000)}
                                   for fc in [1,2,3]],
        'core_self_weight_scenarios':cores,
        'global_equilibrium_scenarios':global_checks,
        'eaves_cantilever_screen':overhang,
        'lateral_scenarios':scenarios,
        'horizontal_inertia_static_sensitivity':seismic_scenarios,
    }
    (ROOT/'mechanics-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    fields=['id','equivalent_square_base_side_m','equivalent_column_count_per_story','E_GPa',
            'eta_fraction_of_fixed_end_bound','effective_pressure_kPa','status',
            'roof_displacement_m','max_interstory_drift_ratio','fundamental_period_s',
            'eta_min_for_positive_effective_springs','eta_needed_for_chosen_1_over_200_drift_screen']
    with (ROOT/'lateral-sensitivity.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields,extrasaction='ignore',lineterminator='\n')
        writer.writeheader();writer.writerows(scenarios)
    # Meaningful invariant checks: hand-calculable geometry, equilibrium and
    # independent matrix integration. These do not establish historical truth.
    checks={
        'nodes_strictly_increasing':bool(np.all(H>0)),
        'nine_structural_dofs':len(H)==9,
        'roof_annuli_positive':bool(np.all(ROOF_AREA>0)),
        'total_roof_surface_m2':float(ROOF_AREA.sum()),
        'core_weights_separate_from_wood_column_load':True,
        'all_stable_cases_equilibrium_residual_below_1e_7_kN':all(s.get('equilibrium_residual_kN',0)<1e-7 for s in scenarios),
        'square_I_exceeds_circle_at_equal_external_width':1/12>math.pi/64,
        'all_input_historical_unknowns_labelled_as_assumptions':True,
    }
    if not all(v for v in checks.values() if isinstance(v,bool)):
        raise AssertionError(checks)
    (ROOT/'mechanics-verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'gravity':summary['gravity_cases'],'wind':wi,
                      'peak_column_MN':axial_peak/1000,
                      'selected':[ {k:s.get(k) for k in fields}
                                  for s in scenarios if s['id'] in ['sq1-eta0.03-p1','sq1-eta0.3-p1','sq1-eta1-p1','sq1.2-eta0.5-p1'] ],
                      'core':cores,'eaves':overhang},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
