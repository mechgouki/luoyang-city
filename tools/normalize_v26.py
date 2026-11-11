"""Lossless registry normalization. Lexical lookup is NOT identity adjudication."""
from collections import Counter, defaultdict
import hashlib,json,re

# Only explicitly defined projections are offered, never automatically submitted to solver.
DIRECTION={
 'east_of':('x','target','subject'),'west_of':('x','subject','target'),
 'north_of':('y','target','subject'),'south_of':('y','subject','target'),
 'has_east':('x','subject','target'),'has_west':('x','target','subject'),
 'has_north':('y','subject','target'),'has_south':('y','target','subject'),
 'faces_west':('x','target','subject'),'west_facing_of':('x','subject','target'),
 'bounds_south':('y','target','subject'),'neighbors_north':('y','subject','target'),
 'south_boundary_neighbor':('y','subject','target'),'north_neighbor':('y','target','subject'),
 'north_connected_to':('y','target','subject')}
FAMILIES={
 'membership': 'inside within contains in_ward within_region in_city part_of_former_residence within_rear_garden upper_part_of eastern_part_of',
 'gate_relation':'inside_gate outside_gate outside outside_north_gate associated_with_gate related_gate gate_of',
 'topology':'on between near faces adjacent_separated_by_wall crosses_or_on_water crosses passes overflow_to on_north_and_south_banks associated_access_via',
 'identity_claim':'same_site_claim not_identical same_historical_site reported_former_identity',
 'time_or_use':'converted_from predecessor_site predecessor_of later_became historical_site_of historical_site prior_housing_of later_moved_to associated_former_site historically_associated_with',
 'directional_extent':'southwest_of northeast_of southeast_of northwest_of northwest_corner_of southeast_corner_of west_sector_of east_sector_of eastward_to eastward_extent_to connected_north southern_boundary northern_extent on_south_road_of',
 'orientation_or_quantity':'in_front_of below orientation extent_original',
 'association':'at_region associated_with associated'}
FAMILY={v:k for k,vals in FAMILIES.items() for v in vals.split()}
FAMILY.update({v:'directional_projection' for v in DIRECTION})
CATEGORIES={
 'religious':'temple 寺院 尼寺 寺院旧址',
 'official':'office 官署 former_office',
 'residential':'residence former_residence 宅第 宅第／寺前身 宅第／传称旧址 residence_building',
 'ward_or_area':'ward 里坊 area regional_landmark enclosure former_ward',
 'palace_or_garden':'palace_structure garden grove garden_complex 宫苑旧址 私园人工山 宫内堂',
 'water':'water watercourse pond river watercourse_region well 水道 河流',
 'transport':'road city_gate palace_gate enclosure_gate bridge weir pass 道路 城门 桥 浮桥 郭门',
 'market':'market former_market 市场 旧市 巷市',
 'ritual_or_school':'school ritual_site 学校旧址 礼制遗构 礼制建筑 祭坛',
 'landform':'hill artificial_hill mountain_region',
 'object_or_structure':'platform storehouse stele 塔 碑刻群 标志物组 建筑／前代塔',
 'special_function':'馆舍 兽苑／坊 仓储／赋税场地 赋税场地 training_ground 临时设施',
 'unresolved_or_historical':'named_place_unknown_function former_structure reserved_site hill_or_palace_structure_disputed historical_site 墓冢传称 旧台／市楼 志怪叙事地点 county_site'}
CATEGORY={v:k for k,vals in CATEGORIES.items() for v in vals.split()}

def basic(s):
    return re.sub(r'\s+','',str(s or ''))
def base_name(s):
    return basic(re.sub(r'[〔（(].*?[〕）)]','',str(s or '')))
def normalize(entities):
    by_id={e['id']:e for e in entities}; names=defaultdict(set); simplified=defaultdict(set)
    for e in entities:
        vals=[e.get('name'),e.get('source_name')]
        vals += [a if isinstance(a,str) else a.get('name') for a in e.get('aliases',[])]
        for v in vals:
            if v:names[basic(v)].add(e['id']);simplified[base_name(v)].add(e['id'])
    def resolve(value):
        if not isinstance(value,str):return {'status':'unresolved','raw':value,'candidates':[]}
        if value in by_id:return {'status':'explicit_id','raw':value,'candidates':[value]}
        found=sorted(names.get(basic(value),[]))
        if found:return {'status':'name_unique' if len(found)==1 else 'name_ambiguous','raw':value,'candidates':found,'identity_verified':False}
        found=sorted(simplified.get(base_name(value),[]))
        if found:return {'status':'name_variant_candidate','raw':value,'candidates':found,'identity_verified':False}
        if '／' in value:
            return {'status':'compound_expression','raw':value,'candidates':[],
                    'parts':[resolve(v) for v in value.split('／')], 'note':'不自动把斜杠解释为同义、合取或择一。'}
        return {'status':'unresolved','raw':value,'candidates':[]}
    records=[]; temporal=[]; classes=[]
    for e in entities:
        classes.append({'id':e['id'],'raw_type':e.get('type'),'category':CATEGORY.get(e.get('type'),'unmapped'),
                        'note':'检索分类，不改对象身份、用途时期或原始类别。'})
        temporal.append({'id':e['id'],'legacy_state':e.get('temporal_state'),
                         'audit_status':'legacy_coarse_state_present' if e.get('temporal_state') else 'event_series_not_reviewed',
                         'valid_from':None,'valid_to':None,'note':'空时间范围不等于不存在；粗标签不是建毁年份。'})
        for i,c in enumerate(e.get('constraints',[])):
            target=resolve(c.get('target_id',c.get('target')))
            family=FAMILY.get(c['relation'],'unmapped_semantics')
            rec={'id':f"N26:{e['id']}:{i+1:02d}",'subject_id':e['id'],'raw_index':i,
                 'original':c,'target':target,'relation_raw':c['relation'],'relation_family':family,
                 'source':{'url':e.get('source_url'),'locator':e.get('source_ref'),
                    'quote':c.get('source_quote',c.get('quote',e.get('source_quote',''))),
                    'quote_scope':'relation' if c.get('source_quote') or c.get('quote') else 'entity_context',
                    'legacy_basis':c.get('evidence_kind',c.get('basis'))},
                 'time_scope':{'valid_from':None,'valid_to':None,'legacy_state':e.get('temporal_state')},
                 'processing_status':'indexed_requires_semantic_review',
                 'solver_admission':'not_automatic','assumptions':[],
                 'distance_original':c.get('distance_text',c.get('distance_original',c.get('distance'))),
                 'original_unit':c.get('unit')}
            if c['relation'] in DIRECTION:
                ax,lo,hi=DIRECTION[c['relation']]
                rec['projection_template']={'axis':ax,'less':lo,'more':hi,
                    'note':'仅保留方位投影；邻接、面对或边界语义未被这条不等式完全表达。'}
            records.append(rec)
    metrics={'entities':len(entities),'relations':len(records),
      'target_id_field':sum('target_id' in r['original'] for r in records),
      'target_field':sum('target' in r['original'] for r in records),
      'target_field_contains_existing_id':sum(r['target']['status']=='explicit_id' and 'target' in r['original'] for r in records),
      'target_status':dict(sorted(Counter(r['target']['status'] for r in records).items())),
      'relation_families':dict(sorted(Counter(r['relation_family'] for r in records).items())),
      'raw_relation_types':len({r['relation_raw'] for r in records}),
      'raw_entity_types':len({e.get('type') for e in entities}),
      'unmapped_types':[c for c in classes if c['category']=='unmapped'],
      'temporal_audit':dict(Counter(t['audit_status'] for t in temporal))}
    assert len(records)==sum(len(e.get('constraints',[])) for e in entities)
    assert all(r['original']==by_id[r['subject_id']]['constraints'][r['raw_index']] for r in records)
    assert not metrics['unmapped_types'],metrics['unmapped_types']
    assert 'unmapped_semantics' not in metrics['relation_families'],metrics['relation_families']
    return {'version':'v2.6','normalization_policy':'无损索引；文字匹配不是历史身份裁决；全量不自动送入求解器。',
            'records':records,'temporal_audit':temporal,'entity_categories':classes,'metrics':metrics}
