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
 report={'base_url':base,'commit':info['source_commit'],'status':'passed','checked_files':len(results),'build_control_not_published':excluded,'network_counts':net['metrics'],'chronology_counts':chrono['metrics'],'terrain_counts':info['terrain_counts'],'dual_counts':info['dual_counts'],'north_b4':info['north_b4'],'historical_grid_points':26,'files':results,'checked_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 report['http_retries']=fetcher.retries
 report['west_roads_b5']=info['west_roads_b5'];report['historical_datum_b5']=info['historical_datum_b5']
 report['southeast_b6']=info['southeast_b6'];report['ground_review_b6']=ground['review_counts']
 print(f'LIVE PASS: {len(results)} public assets verified, including B1-B6, source lineage and named-ground review; HTTP retries: {len(fetcher.retries)}')
except Exception as e:
 report={'base_url':base,'status':'failed','error':str(e),'files':results,'http_retries':fetcher.retries};raise
finally:
 target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,ensure_ascii=False,indent=2))
