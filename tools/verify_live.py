#!/usr/bin/env python3
"""Verify the actual HTTPS commit and every public asset. No deployment mocks."""
import argparse,concurrent.futures,hashlib,json,os,time
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
 report={'base_url':base,'commit':info['source_commit'],'status':'passed','checked_files':len(results),'build_control_not_published':excluded,'network_counts':net['metrics'],'chronology_counts':chrono['metrics'],'terrain_counts':info['terrain_counts'],'dual_counts':info['dual_counts'],'north_b4':info['north_b4'],'historical_grid_points':26,'files':results,'checked_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 report['http_retries']=fetcher.retries
 report['west_roads_b5']=info['west_roads_b5'];report['historical_datum_b5']=info['historical_datum_b5']
 report['southeast_b6']=info['southeast_b6'];report['ground_review_b6']=ground['review_counts']
 report['luonan_b7']=info['luonan_b7'];report['source_continuity_b7']=continuity['review_counts']
 print(f'LIVE PASS: {len(results)} public assets verified, including B1-B7, source lineage and source continuity; HTTP retries: {len(fetcher.retries)}')
except Exception as e:
 report={'base_url':base,'status':'failed','error':str(e),'files':results,'http_retries':fetcher.retries};raise
finally:
 target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,ensure_ascii=False,indent=2))
