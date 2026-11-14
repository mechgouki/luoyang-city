#!/usr/bin/env python3
"""Verify the actual HTTPS commit and every public asset. No deployment mocks."""
import argparse,concurrent.futures,hashlib,json,os,re,time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse
from live_http import LiveFetcher
p=argparse.ArgumentParser();p.add_argument('--base-url',required=True);p.add_argument('--commit',default=os.environ.get('GITHUB_SHA'));p.add_argument('--output',default='artifacts/live-http.json');args=p.parse_args()
base=args.base_url.rstrip('/')+'/'
if urlparse(base).scheme!='https':raise SystemExit('HTTPS required for live verification')
fetcher=LiveFetcher(base)
get=fetcher.get
info=None
for attempt in range(12):
 try:
  info=json.loads(get('build-info.json'))
  if args.commit and info['source_commit']!=args.commit:raise ValueError('Deployment/CDN serves another commit')
  if info.get('supplement_version')!='v2.5-r07' or info.get('network_version')!='v2.7' or info.get('chronology_version')!='v2.9':raise ValueError('Missing required earlier milestone')
  if info.get('dual_version')!='B1+B2':raise ValueError('Missing dual-map release')
  break
 except Exception:
  if attempt==11:raise
  time.sleep(10)
results=[];excluded=['.nojekyll']
def check(item):
 path,digest=item;body=get(path);actual=hashlib.sha256(body).hexdigest()
 if actual!=digest:raise ValueError(f'{path}: SHA-256 mismatch')
 return {'path':path,'bytes':len(body),'sha256':actual,'status':'passed'}
try:
 required_b7_assets={
  'dual-luonan.html','luonan-b7.js','source-continuity.html','source-continuity/continuity.js',
  'dual/luonan-b7.json','dual/luonan-b7-preservation.json','source-continuity/metadata.json',
  'assets/master-dual-b7-luonan.svg','dual/maps/L10.svg','dual/maps/L10-archive.svg',
  'dual/maps/LN7-institutions.svg','dual/maps/LN7-markets.svg','dual/maps/LN7-layers.svg',
  'dual/maps/LN7-evidence-groups.svg','dual/maps/LN7-evidence-river.svg',
  'source-continuity/edition-summary.svg','source-continuity/continuity-summary.svg',
  'dual/luonan-b7-map.png','dual/luonan-b7-preview.png',
  'downloads/dual-luonan-b7-atlas.pdf','downloads/dual-luonan-b7-evidence.csv',
  'downloads/dual-luonan-b7-package.zip','downloads/luoyang-source-continuity-b7.zip',
 }
 assert required_b7_assets.issubset(info['files_sha256']), f'Missing B7 assets: {sorted(required_b7_assets-set(info["files_sha256"]))}'
 required_b8_assets={
  'dual-city-review.html','city-review-b8.js','assets/master-dual-b8-review.svg',
  'city-review/ledger.json','city-review/cases.json','city-review/metadata.json',
  'city-review/errata.json','city-review/preservation.json','city-review/overview.png',
  'source-access/metadata.json','source-access/access-summary.svg','source-access/upstream-summary.svg',
  'downloads/luoyang-city-review-b8-atlas.pdf','downloads/luoyang-city-review-b8-ledger.csv',
  'downloads/luoyang-city-review-b8-package.zip','dual-b2-before-b8.html','downloads/dual-map-report-before-b8.html',
 }
 assert required_b8_assets.issubset(info['files_sha256']), f'Missing B8 assets: {sorted(required_b8_assets-set(info["files_sha256"]))}'
 required_homepage_assets={'homepage/metadata.json','homepage/preservation.json'}
 assert required_homepage_assets.issubset(info['files_sha256']), 'Missing homepage metadata or preservation record'
 public_files=[(path,digest) for path,digest in info['files_sha256'].items() if path not in excluded]
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(check,public_files))
 assert info['counts']['sheets']==37 and info['counts']['entities']==339
 assert len(json.loads(get('data/research-v25.json'))['evidence'])==18
 assert len(json.loads(get('data/milestone-v26.json'))['atoms'])==69
 net=json.loads(get('data/network-v27.json'))
 assert len(net['passages'])==20 and len(net['events'])==10 and len(net['scenarios'])==48 and len(net['event_audit'])==339
 chrono=json.loads(get('data/chronology-v29.json'))
 assert len(chrono['dossiers'])==12 and len(chrono['records'])==25 and len(chrono['coverage'])==339
 assert sum(d['anchor'] is not None for d in chrono['dossiers'])==11
 release=json.loads(get('release.json'))
 assert release['source_commit']==info['source_commit'] and release['release']=='v3.0-dual.b2' and info['portal_version']=='v3.0-dual.b2'
 terrain=json.loads(get('terrain/v3.0/metadata.json'))
 assert info.get('terrain_version')=='v3.0-alpha.1' and terrain['synthetic'] is False
 assert terrain['analysis_grid']==[1695,1860] and terrain['ancient_registered_nodes']==0
 dual=json.loads(get('dual/data.json'));preserved=json.loads(get('dual/preservation.json'))
 assert dual['source_commit']==info['source_commit'] and dual['new_ancient_coordinates']==0
 assert len(dual['b1']['decisions'])==14 and len(dual['b2']['evidence'])==16 and len(dual['regions'])==4
 assert dual['audits']['b1']['groups_changed']==7 and dual['audits']['b2']['groups_changed']==15
 assert preserved['protected_unchanged'] is True and all(e['geographic_coordinates'] is None for e in dual['b2']['evidence'])
 north=json.loads(get('dual/north-b4.json'));frame=json.loads(get('historical-frame/metadata.json'))
 assert 'dual-north-b4' in release['extensions'] and 'dual-west-b3' in release['extensions']
 assert north['source_commit']==info['source_commit']==info['north_b4']['source_commit']
 assert len(north['evidence'])==16 and north['region']['id']=='L06'
 assert north['ancient_absolute_positions_added']==0 and all(e['geographic_coordinates'] is None for e in north['evidence'])
 assert json.loads(get('dual/north-b4-preservation.json'))['protected_unchanged'] is True
 assert frame['ancient_geographic_positions_added']==0 and frame['ground_accuracy_assessed'] is False
 assert len(frame['sheets'])==2 and sum(len(s['points']) for s in frame['sheets'])==26
 assert all(s['calibration']['fit']['count']==8 and s['calibration']['internal_holdout_check']['count']==5 and s['geographic_crs'] is None for s in frame['sheets'])
 west_roads=json.loads(get('dual/west-roads-b5.json'));datum=json.loads(get('historical-datum/metadata.json'))
 assert 'dual-west-roads-b5' in release['extensions'] and 'historical-datum-b5' in release['extensions']
 assert west_roads['source_commit']==info['source_commit']==info['west_roads_b5']['source_commit']==datum['source_commit']
 assert len(west_roads['evidence'])==24 and west_roads['region']['id']=='L07'
 assert west_roads['ancient_absolute_positions_added']==0 and all(e['geographic_coordinates'] is None for e in west_roads['evidence'])
 assert west_roads['drawing_audit']['type_groups_changed']==11 and west_roads['drawing_audit']['anchors_moved'] is False
 assert set(west_roads['drawing_audit']['nonspatial_sidecars_preserved'])=={'w_yongming','w_wangdianyu'}
 assert json.loads(get('dual/west-roads-b5-preservation.json'))['protected_unchanged'] is True
 assert datum['original_horizontal_datum'] is None and datum['original_geographic_crs'] is None
 assert datum['project_registration_to_wgs84'] is False and datum['ground_accuracy_assessed'] is False
 assert datum['ancient_geographic_positions_added']==0 and len(datum['approved_ground_control_points'])==0
 assert len(datum['sheets'])==2 and all(s['digitized_product']['assignment_role']=='post_publication_digitization_working_definition' for s in datum['sheets'])
 southeast=json.loads(get('dual/southeast-b6.json'));ground=json.loads(get('ground-review/metadata.json'))
 assert {'dual-southeast-b6','ground-review-b6'}.issubset(release['extensions'])
 assert southeast['source_commit']==info['source_commit']==info['southeast_b6']['source_commit']==ground['source_commit']
 assert len(southeast['evidence'])==34 and southeast['source_family_count']==1 and len(southeast['sources'])==4
 assert [r['id'] for r in southeast['regions']]==['L08','L09']
 assert [r['bbox'] for r in southeast['regions']]==[[6500,4110,1710,2870],[7700,4050,4200,2700]]
 assert southeast['ancient_absolute_positions_added']==0 and all(e['geographic_coordinates'] is None for e in southeast['evidence'])
 assert southeast['drawing_audit']['type_groups_changed']==20 and southeast['drawing_audit']['anchors_moved'] is False
 assert southeast['drawing_audit']['original_target_count']==179 and info['southeast_b6']['atlas_pages']==8
 assert set(southeast['drawing_audit']['nonspatial_sidecars_preserved'])=={'ic_hutong','ic_yuanhui','ic_yishou','ic_guangming','v2_guijue'}
 assert json.loads(get('dual/southeast-b6-preservation.json'))['protected_unchanged'] is True
 records={e['id']:e for e in southeast['evidence']}
 assert records['EO15']['identity_assumption_required_for_dating'] is True
 assert records['EO07']['east_of_zhengshi_established'] is False and records['EO14']['baoming_at_ward_northwest_corner_established'] is False
 assert ground['original_horizontal_datum'] is None and ground['original_geographic_crs'] is None
 assert ground['project_registration_to_wgs84'] is False and ground['ground_accuracy_assessed'] is False
 assert ground['ancient_geographic_positions_added']==0 and ground['ancient_channels_added']==0 and ground['modern_dsm_modified'] is False
 assert ground['approved_ground_control_points']==[] and len(ground['candidates'])==2 and len(ground['source_assets'])==4
 assert all(c['approved_as_ground_control'] is False and c['coordinates'] is None and c['anchor_pixel'] is None for c in ground['candidates'])
 assert all(r['exact_l500_source_impression_verified'] is False for r in ground['lineage_records'])
 assert [r['observed_printed_year'] for r in ground['lineage_records'] if r['id'] in ['l531-k','l531-l']]==[1946,1946]
 luonan=json.loads(get('dual/luonan-b7.json'));continuity=json.loads(get('source-continuity/metadata.json'))
 assert {'dual-luonan-b7','source-continuity-b7'}.issubset(release['extensions'])
 assert luonan['source_commit']==info['source_commit']==info['luonan_b7']['source_commit']==continuity['source_commit']==info['source_continuity_b7']['source_commit']
 assert len(luonan['evidence'])==info['luonan_b7']['records']==25
 assert {e['id'] for e in luonan['evidence']}=={f'LG{i:02}' for i in range(1,12)}|{f'LR{i:02}' for i in range(1,15)}
 assert luonan['source_family_count']==1 and {s['id'] for s in luonan['sources']}=={'Z3','F3','Z2','F2'}
 assert all(s['family']=='L' for s in luonan['sources'])
 assert luonan['region']['id']=='L10' and luonan['region']['source_region']=='R11' and luonan['region']['bbox']==[4100,8720,4350,2230]
 assert luonan['ancient_absolute_positions_added']==0 and all(e['geographic_coordinates'] is None and e['source_region']=='R11' for e in luonan['evidence'])
 audit=luonan['drawing_audit']
 assert audit['reading_groups_changed']==info['luonan_b7']['reading_groups_changed']==7
 assert audit['anchors_moved'] is False and audit['original_target_count']==179
 assert audit['bridge_drawing_anchor']==[6100,9000] and audit['bridge_interactive_marker_present'] is False
 assert audit['new_individual_site_glyphs']==audit['new_interactive_targets']==audit['new_ancient_coordinates']==0
 assert info['luonan_b7']['new_individual_site_glyphs']==info['luonan_b7']['new_interactive_targets']==info['luonan_b7']['new_ancient_coordinates']==0
 assert info['luonan_b7']['atlas_pages']==8 and info['luonan_b7']['previous_release_preserved']=='B1+B2+B3+B4+B5+B6'
 assert set(audit['nonspatial_sidecars_preserved'])=={'house_xiaozhengde','v3_guizheng','v3_puti','market_fish','house_xiaobaoyin','market_sitong','fang_whiteelephant','fang_lion','v3_yong_huabiao'}
 assert json.loads(get('dual/luonan-b7-preservation.json'))['protected_unchanged'] is True
 records={e['id']:e for e in luonan['evidence']}
 assert records['LR01']['bridge_construction_year_ce'] is None and records['LR02']['event']['bridge_construction_dated'] is False
 assert records['LR03']['height_converted_to_map_scale'] is False and records['LR03']['annotation_only'] is True
 assert records['LR04']['direction_reference_only'] is True and records['LR04']['altar_footprint'] is None
 assert records['LR05']['procession_crosses_yong_established'] is False
 assert records['LR06']['move_precedes_main_516_528'] is True and records['LR06']['occupancy_continues_into_main_period_established'] is False
 assert records['LR06']['converted_to_guizheng_temple_established'] is False
 assert records['LR07']['ward_id']=='li_guizheng' and records['LR07']['inherit_position_from_paragraph_heading'] is False
 assert records['LR08']['market_moves_with_person'] is False
 assert records['LR10']['fish_sitong_identity_established'] is False and records['LR10']['merge_authorized'] is False
 assert records['LR10']['adjacent_to_bridge_established'] is False and records['LR10']['market_sitong_roadside'] is None
 assert records['LR11']['main_temporal_state']=='undated' and records['LR11']['temple_foundation_year_ce'] is None
 assert records['LR12']['internal_order'] is None and records['LR13']['arrival_is_ward_foundation'] is False
 assert records['LR14']['lion_alive_in_main_period_allowed'] is False and records['LR14']['actual_return_home_established'] is False
 assert continuity['review_counts']=={
  'catalog_records_reviewed':3,'period_matched_catalog_candidates':1,'earlier_impressions':2,
  'upstream_chinese_map_mentions':2,'historical_scans_added':0,'exact_l500_source_matches':0,
  'exact_l531_source_matches':0,'approved_ground_control_points':0,
 }
 assert info['source_continuity_b7']['review_counts']==continuity['review_counts']
 assert info['source_continuity_b7']['metadata']=='source-continuity/metadata.json'
 assert info['source_continuity_b7']['metadata_sha256']==info['files_sha256']['source-continuity/metadata.json']
 assert continuity['original_horizontal_datum'] is None and continuity['original_geographic_crs'] is None
 assert continuity['project_registration_to_wgs84'] is False and continuity['ground_accuracy_assessed'] is False
 assert continuity['coordinate_assignment_performed'] is False and continuity['modern_dsm_modified'] is False
 assert continuity['new_historical_image_obtained'] is False
 assert continuity['ancient_geographic_positions_added']==continuity['ancient_channels_added']==continuity['approved_control_points']==0
 assert continuity['approved_ground_control_points']==[] and continuity['source_assets']==[] and continuity['named_records']==3
 assert len(continuity['records'])==3 and {r['id'] for r in continuity['records']}=={'zhengzhou-1942','yanshi-1934','sishui-1935'}
 assert {r['id']:r['status'] for r in continuity['records']}=={'zhengzhou-1942':'period-match','yanshi-1934':'earlier','sishui-1935':'earlier'}
 assert all(r['catalog_only'] is True and r['original_scan_seen_in_this_batch'] is False and r['coordinates'] is None and r['approved_as_ground_control'] is False for r in continuity['records'])
 assert all(r['actual_l500_source_match'] is False and r['actual_l531_source_match'] is False and r['original_horizontal_datum'] is None and r['original_geographic_crs'] is None for r in continuity['records'])
 # B8 checks the real published associations and correction layer without promoting them to historical certainty.
 ledger=json.loads(get('city-review/ledger.json'));cases=json.loads(get('city-review/cases.json'))
 city=json.loads(get('city-review/metadata.json'));access=json.loads(get('source-access/metadata.json'))
 errata=json.loads(get('city-review/errata.json'));city_preserved=json.loads(get('city-review/preservation.json'))
 assert {'city-review-b8','source-access-b8'}.issubset(release['extensions'])
 assert all(d['source_commit']==info['source_commit'] for d in [ledger,cases,city,access,errata,info['city_review_b8'],info['source_access_b8']])
 assert all(d['baseline_commit']=='e959da7c16db7cb814bb7460c03e5c7d860be1fa' for d in [ledger,cases,city,access,errata])
 expected_counts={'entities':339,'targets':179,'regions':11,'targeted_entities':237,
  'individual_entities':136,'group_entities':101,'no_interactive_target_entities':102,
  'groups':42,'shared_or_group_targets':43,'shared_non_group_targets':1,
  'explicit_focus_entities':125,'direct_evidence_records':183,'direct_evidence_entities':209,
  'direct_evidence_refs':506,'no_direct_evidence_refs_entities':130,
  'new_ancient_coordinates':0,'new_interactive_targets':0,'new_historical_verifications':0}
 assert city['counts']==ledger['counts'] and all(ledger['counts'][k]==v for k,v in expected_counts.items())
 assert info['city_review_b8']['entities']==339 and info['city_review_b8']['targets']==179
 assert city['atlas_pages']==info['city_review_b8']['atlas_pages']==8
 assert city['new_ancient_coordinates']==city['new_interactive_targets']==0
 assert city['historical_full_entity_revalidation_claimed'] is False
 baseline_entities=json.loads(get('data/entities.json'));markers=json.loads(get('data/markers.json'))
 baseline_regions=json.loads(get('data/regions.json'))
 rows={e['id']:e for e in ledger['entities']}
 assert len(rows)==len(ledger['entities'])==339 and set(rows)=={e['id'] for e in baseline_entities}
 assert len(markers)==179 and len(baseline_regions)==len(ledger['regions'])==11
 targets={}
 for original in baseline_entities:
  row=rows[original['id']]
  assert all(row[k]==original[k] for k in ['id','map_id','name','type']), original['id']
  assert row['legacy_temporal_state']==original.get('temporal_state')
  assert row['geographic_coordinates'] is None and row['historical_verification_added'] is False
  assert row['drawing_status']['geographic_coordinates'] is None
  assert row['explicit_focus_regions']==[r['code'] for r in baseline_regions if row['id'] in r['focus_ids']]
  expected_indexes=[i for i,m in enumerate(markers) if row['id'] in m['ids']]
  assert [t['source_index'] for t in row['targets']]==expected_indexes, row['id']
  expected_state='no_interactive_target' if not expected_indexes else 'group_member' if any(markers[i]['kind']=='group' or len(markers[i]['ids'])>1 for i in expected_indexes) else 'individual'
  assert row['marker_state']==expected_state, row['id']
  for t in row['targets']:
   m=markers[t['source_index']]
   assert t['id']==f'target-{t["source_index"]+1:03}' and t['member_ids']==m['ids']
   assert [t['kind'],t['x'],t['y'],t['member_count']]==[m['kind'],m['x'],m['y'],len(m['ids'])]
   assert t['coordinate_frame']=='documentary_canvas_not_geographic'
   assert t['id'] not in targets or targets[t['id']]==t
   targets[t['id']]=t
  assert all(row['id'] in ref['entity_ids'] and ref['relation']=='explicit_reference' for ref in row['direct_evidence_refs'])
 assert len(targets)==179 and sum(len(row['direct_evidence_refs']) for row in rows.values())==506
 associated_evidence={r['key'] for row in rows.values() for r in row['direct_evidence_refs']}
 unassociated_network={f'v2.7:{r["id"]}' for r in net['passages'] if not r['map_ids']}
 assert unassociated_network=={'v2.7:N18','v2.7:N20'}
 assert associated_evidence.isdisjoint(unassociated_network) and len(associated_evidence)==181
 assert len(associated_evidence|unassociated_network)==ledger['counts']['direct_evidence_records']==183
 assert 'city_jinyang' not in rows and any(r['resolution']=='known_external_reference' for r in rows['ic_sanji_jinyang']['constraint_references'])
 assert rows['bridge_yong']['targets']==[] and rows['bridge_yong']['crop_regions']==[]
 assert rows['bridge_yong']['explicit_focus_regions']==['R10','R11']
 assert rows['ic_donggong_reserved']['targets']==rows['ic_taicang_jin']['targets']
 assert rows['ic_donggong_reserved']['targets'][0]['kind']=='area'
 assert rows['v2_baoming']['legacy_temporal_state']=='attested_by_528'
 assert 'conditional-identity' in rows['v2_baoming']['drawing_status']['current_temporal_displays']
 assert rows['v2_baoming']['current_review']['temporal_label']=='前期身份有条件'
 assert rows['house_xiaobaoyin']['display_name']=='萧宝夤归正里旧宅〔后迁永安里〕'
 assert city['display_override_entities']==sum(bool(e['current_review']) for e in rows.values())==2
 assert all(e['current_review'].get('changes_catalog') is False for e in rows.values() if e['current_review'])
 assert [r['id'] for r in cases['records']]==[f'CB{i:02}' for i in range(1,15)]
 assert city['case_count']==info['city_review_b8']['case_count']==len(cases['records'])==14
 assert cases['source_family_count']==1 and len(cases['sources'])==10
 assert all(r['geographic_coordinates'] is None and set(r['entities'])<=set(rows) for r in cases['records'])
 assert all(row['case_ids']==[c['id'] for c in cases['records'] if row['id'] in c['entities']] for row in rows.values())
 assert city['case_linked_entities']==info['city_review_b8']['case_linked_entities']==sum(bool(e['case_ids']) for e in rows.values())==80
 correction=next(r for r in cases['records'] if r['id']=='CB14')['errata']
 assert errata['original_research_data_preserved'] is True and errata['records']==[dict(correction,case_id='CB14')]
 assert city['quotation_corrections']==info['city_review_b8']['quotation_corrections']==1
 assert correction['legacy_quote']==next(e for e in dual['b2']['evidence'] if e['id']=='G15')['quote']=='大旱則穀水注之，霖雨則陽穀泄之。'
 assert correction['corrected_source_quote']=='若旱魃為害，穀水注之不竭；離畢滂潤，陽穀泄之不盈。'
 assert correction['correction_scope']=='quotation_layer' and correction['original_data_preserved'] is True
 assert correction['legacy_originals_are_overwritten'] is False
 assert correction['commentary_variant']['quote']=='穀當作渠。' and correction['commentary_variant']['changes_body_quote_silently'] is False
 assert city_preserved['protected_unchanged'] is True
 assert city['protected_files']==info['city_review_b8']['protected_files']==city_preserved['protected_files']==len(city_preserved['sha256'])
 assert all(info['files_sha256'][path]==digest for path,digest in city_preserved['sha256'].items())
 updates=city_preserved['intentional_html_updates']
 assert updates==city['intentional_html_updates'] and {u['path']:u['archive_path'] for u in updates}=={
  'dual-b2.html':'dual-b2-before-b8.html','downloads/dual-map-report.html':'downloads/dual-map-report-before-b8.html'}
 for update in updates:
  assert update['case_id']=='CB14' and update['before_sha256']==info['files_sha256'][update['archive_path']]
  assert update['after_sha256']==info['files_sha256'][update['path']]
  after=get(update['path']);before=get(update['archive_path'])
  assert after.count(b'id="b8-quotation-correction"')==1 and b'case=CB14' in after
  assert b'id="b8-quotation-correction"' not in before
  restored,count=re.subn(rb'<section id="b8-quotation-correction"[^>]*>.*?</section>',b'',after,count=1,flags=re.DOTALL)
  assert count==1 and restored==before, update['path']
 drawing=city['drawing_audit'];assert drawing==city_preserved['drawing_audit']
 assert drawing['review_targets']==179 and drawing['all_original_world_children_preserved'] is True
 assert drawing['anchors_moved'] is False and drawing['marker_catalog_unchanged'] is True
 assert drawing['new_ancient_coordinates']==drawing['new_interactive_targets']==0
 assert drawing['source_master']==city['original_master_retained']=='assets/master-dual-b7-luonan.svg'
 assert drawing['source_sha256']==info['files_sha256'][drawing['source_master']]
 assert drawing['overlay_role']=='review_association_not_historical_confidence'
 ns='{http://www.w3.org/2000/svg}'
 previous=ET.fromstring(get(drawing['source_master']));current=ET.fromstring(get('assets/master-dual-b8-review.svg'))
 previous_world=next(g for g in previous if g.tag==ns+'g' and g.get('transform'))
 current_world=next(g for g in current if g.tag==ns+'g' and g.get('transform'))
 assert len(previous_world)==drawing['original_world_children'] and len(current_world)==len(previous_world)+1
 assert [ET.tostring(g) for g in previous_world]==[ET.tostring(g) for g in list(current_world)[:-1]]
 overlay=list(current_world)[-1];assert overlay.get('id')=='city-audit-overlay-b8'
 rings=[g for g in overlay if g.get('class')=='city-review-target']
 assert len(rings)==179 and {g.get('data-target-id') for g in rings}==set(targets)
 for g in rings:
  t=targets[g.get('data-target-id')];circle=next(c for c in g if c.tag==ns+'circle')
  assert g.get('data-entity-ids').split()==t['member_ids'] and g.get('data-footprint')=='false'
  assert [float(circle.get('cx')),float(circle.get('cy'))]==[t['x'],t['y']]
  assert g.get('data-shared')==str(t['kind']=='group' or t['member_count']>1).lower()
 outputs=city['outputs']
 assert isinstance(outputs,list) and outputs and len(outputs)==len(set(outputs))
 assert all(isinstance(path,str) and path and not path.startswith('/') and '..' not in path.split('/') and ':' not in path for path in outputs)
 assert set(outputs)<=set(info['files_sha256']) and required_b8_assets-{'city-review/metadata.json'}<=set(outputs)
 assert access['review_counts']==city['source_access_counts']==info['source_access_b8']['review_counts']=={
  'target_maps_access_reviewed':3,'target_historical_scans_obtained':0,
  'bounded_university_catalog_records_screened':35,'rejected_name_or_number_matches':3,
  'upstream_target_series_records':2,'documented_join_index_targets':1,'join_index_images_obtained':0,
  'comparative_series_records_kept_separate':2,'named_structure_exclusions_added':1,
  'actual_ams_source_matches':0,'approved_ground_control_points':0}
 assert access['original_horizontal_datum'] is None and access['original_geographic_crs'] is None
 assert all(access[k] is False for k in ['project_registration_to_wgs84','ground_accuracy_assessed','modern_dsm_modified','coordinate_assignment_performed','new_historical_image_obtained'])
 assert access['approved_ground_control_points']==[] and access['source_assets']==[]
 assert access['ancient_geographic_positions_added']==access['ancient_channels_added']==access['approved_control_points']==0
 assert info['source_access_b8']['metadata']=='source-access/metadata.json'
 assert info['source_access_b8']['approved_control_points']==0 and info['source_access_b8']['project_registration_to_wgs84'] is False and info['source_access_b8']['original_horizontal_datum'] is None
 assert len(access['access_records'])==3 and {r['id'] for r in access['access_records']}=={'zhengzhou-1942','yanshi-1934','sishui-1935'}
 assert all(r['historical_image_obtained'] is False and r['historical_image_inspected'] is False and r['actual_ams_source_match'] is False for r in access['access_records'])
 assert all(r['public_image_url'] is None and r['raw_scan_crop_xyxy'] is None and r['copy_request_status']=='service_route_identified_not_applied' for r in access['access_records'])
 assert len(access['upstream_records'])==2 and len(access['rejected_matches'])==3 and len(access['comparison_records'])==2
 assert all(r['historical_sheet_number'] is None and r['actual_parent_sheet_match'] is False and r['index_sheet_obtained'] is False and r['catalog_record_number_is_historical_sheet_number'] is False for r in access['upstream_records'])
 assert len(access['structure_reviews'])==1 and access['structure_reviews'][0]['id']=='huanghe-railway-pier-11'
 assert all(r['approved_as_ground_control'] is False and r['coordinates'] is None and r['anchor_pixel'] is None and r['physical_point_in_ams_identified'] is False and r['current_component_identity_verified'] is False for r in access['structure_reviews'])
 assert access['plates']==['source-access/access-summary.svg','source-access/upstream-summary.svg']
 assert all(access['plate_sha256'][Path(path).name]==info['files_sha256'][path] for path in access['plates'])
 homepage=json.loads(get('homepage/metadata.json'))
 home_preserved=json.loads(get('homepage/preservation.json'))
 assert homepage['version']==release['homepage_version']==info['homepage']['version']=='homepage-v1'
 assert homepage['source_commit']==home_preserved['source_commit']==info['source_commit']
 assert homepage['research_milestone']=='B8' and homepage['research_release_unchanged']==release['release']
 assert homepage['new_historical_claims']==homepage['new_ancient_coordinates']==0
 assert homepage['research_data_changed'] is False and homepage['source_geometry_changed'] is False
 assert len(homepage['questions'])==info['homepage']['question_count']==3
 assert home_preserved['protected_unchanged'] is True
 assert home_preserved['protected_files']==info['homepage']['protected_files']==len(home_preserved['sha256'])
 assert all(info['files_sha256'][path]==digest for path,digest in home_preserved['sha256'].items())
 assert homepage['hero']['generated_image'] is True and homepage['hero']['measured_reconstruction'] is False
 assert {homepage['hero']['asset'],homepage['hero']['small_asset']}<=set(info['files_sha256'])
 home_html=get('index.html').decode('utf-8')
 assert all(f'id="{ident}"' in home_html for ident in ['home-hero','home-start','home-questions','home-research'])
 assert home_html.index('id="home-hero"') < home_html.index('id="home-questions"') < home_html.index('id="map-viewport"') < home_html.index('id="home-research"')
 assert '研究性复原示意' in home_html
 report={'base_url':base,'commit':info['source_commit'],'status':'passed','checked_files':len(results),'build_control_not_published':excluded,'network_counts':net['metrics'],'chronology_counts':chrono['metrics'],'terrain_counts':info['terrain_counts'],'dual_counts':info['dual_counts'],'north_b4':info['north_b4'],'historical_grid_points':26,'files':results,'checked_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 report['http_retries']=fetcher.retries
 report['west_roads_b5']=info['west_roads_b5'];report['historical_datum_b5']=info['historical_datum_b5']
 report['southeast_b6']=info['southeast_b6'];report['ground_review_b6']=ground['review_counts']
 report['luonan_b7']=info['luonan_b7'];report['source_continuity_b7']=continuity['review_counts']
 report['city_review_b8']=info['city_review_b8'];report['city_audit_counts']=ledger['counts'];report['source_access_b8']=access['review_counts']
 report['homepage']=info['homepage']
 print(f'LIVE PASS: {len(results)} public assets verified, including B1-B8 and the H1 homepage; HTTP retries: {len(fetcher.retries)}')
except Exception as e:
 report={'base_url':base,'status':'failed','error':str(e),'files':results,'http_retries':fetcher.retries};raise
finally:
 target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,ensure_ascii=False,indent=2))
