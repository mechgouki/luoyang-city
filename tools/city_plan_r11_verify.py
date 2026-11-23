"""Verify R11 publication bytes, shared geometry, sources, and honest coverage.

This module intentionally uses only the standard library so the HTTPS acceptance
job can run it before the browser/PDF runtime is installed.
"""
import csv
import io
import json
import math
from collections import Counter
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from city_plan_r11_contract import *

ROOT=Path(__file__).resolve().parents[1]
NS='{http://www.w3.org/2000/svg}'


class Document(HTMLParser):
    def __init__(self,raw):
        super().__init__();self.ids=[];self.downloads=[];self.feature_buttons=[];self.script='';self.in_data=False
        self.feed(raw.decode())
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.append(a['id'])
        if a.get('data-download'):self.downloads.append(a['data-download'])
        if a.get('data-focus-feature'):self.feature_buttons.append(a['data-focus-feature'])
        if tag=='script' and a.get('id')=='plan-data':self.in_data=True
    def handle_endtag(self,tag):
        if tag=='script':self.in_data=False
    def handle_data(self,data):
        if self.in_data:self.script+=data


def pointer(document,path):
    assert path=='' or path.startswith('/')
    current=document
    for token in path.split('/')[1:]:
        token=token.replace('~1','/').replace('~0','~')
        if isinstance(current,list):
            assert token.isdecimal() and str(int(token))==token
            current=current[int(token)]
        else:current=current[token]
    return current


def all_points(geometry):
    def walk(c):
        if isinstance(c[0],(int,float)):yield c
        else:
            for p in c:yield from walk(p)
    return list(walk(geometry['coordinates']))


def validate_data(data):
    assert data['schema']=='luoyang-city-plan-r11-v1'
    assert data['target_years']==[516,528]
    frame=data['frame'];contract=data['coordinate_contract']
    assert frame['id']=='r11-xian1980-source-local-aeqd' and frame['units']=='m'
    assert frame['axis_order']==['east','north'] and frame['source_crs']=='EPSG:4610'
    for field in ['frame_is_wgs84','field_registration_verified','hypothesis_coordinates_are_measurements',
                  'all_entities_have_footprints','unknown_boundaries_filled','legacy_display_rectangles_reused_as_buildings',
                  'modern_river_used_as_northern_wei_bank']:
        assert contract[field] is False,('Unsupported historical precision',field)
    assert contract['all_views_share_geometry'] is contract['source_projection_reused'] is True
    assert contract['verified_shared_controls']==contract['new_field_coordinates']==0
    assert data['homepage_revision']=='panorama-approved-v12' and data['homepage_replacement_approved'] is False
    assert data['new_historical_coordinates']==data['new_shoreline_geometries']==data['evidence_grade_upgrades']==0
    features=data['features'];index={f['id']:f for f in features}
    assert len(index)==len(features)
    assert len([f for f in features if f['layer']=='source'])==28
    assert len([f for f in features if f['id'].startswith('r11-changhe-')])==10
    assert len([f for f in features if f['id'].startswith('r11-yongning-')])==23
    assert len([f for f in features if f['layer']=='trace'])==33
    assert len([f for f in features if f['layer']=='scale'])==4
    for f in features:
        g=f['geometry'];ps=all_points(g)
        assert ps and all(len(p)==2 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in p) for p in ps)
        assert g['type'] in {'Point','LineString','MultiLineString','Polygon','MultiPolygon'}
        if f['layer']=='candidate':assert g['type']=='Point',('A textual candidate became an invented footprint',f['id'])
        if f.get('field_registration_verified') is not None:assert f['field_registration_verified'] is False
        assert f.get('source_refs'),('Missing map evidence',f['id'])
        raw=json.dumps(g,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        assert digest(raw)==f['geometry_sha256']
        if f['geometry_role']=='legacy_display_envelope':assert f['default_visible'] is False
    catalog=json.loads((ROOT/'data/entities.json').read_text())
    entities=data['coverage'];ids=[e['id'] for e in entities]
    assert len(ids)==len(set(ids))==339 and set(ids)=={e['id'] for e in catalog}
    for e in entities:
        assert all(f in index for f in e['feature_ids']),e['id']
        assert e['placement_group'] in {'source','candidate','unplaced'}
        if e['placement_group']=='unplaced':assert not e['feature_ids']
    assert len(data['regions'])==11 and {r['id'] for r in data['regions']}=={f'R{i:02}' for i in range(1,12)}
    assert len({v['id'] for v in data['views']})==len(data['views'])
    assert {'all','core','changhe','yongning',*[f'R{i:02}' for i in range(1,12)]}<={v['id'] for v in data['views']}
    for view in data['views']:
        b=view['bbox'];assert len(b)==4 and b[0]<b[2] and b[1]<b[3]
    for binding in data['bindings']:
        assert binding['verified_shared_controls']==0 and binding['field_registration_verified'] is False
        m=binding['local_metric_to_master_matrix']
        assert abs(m[0][0]*m[1][1]-m[0][1]*m[1][0]-1)<1e-10
        assert abs(m[0][0]**2+m[1][0]**2-1)<1e-10
        assert abs(m[0][1]**2+m[1][1]**2-1)<1e-10
    assert sum(r.get('origin')=='R10' for r in data['constraints'])==259
    assert len({r['id'] for r in data['constraints']})==len(data['constraints'])
    assert data['counts']['constraints']==len(data['constraints'])
    return {'features':len(features),'coverage':len(entities),'constraints':len(data['constraints']),
            'layers':dict(Counter(f['layer'] for f in features)),
            'entity_placement_groups':dict(Counter(e['placement_group'] for e in entities))}


def check_sources(data):
    sources={}
    for path,checksum in data['source_inputs_sha256'].items():
        p=(ROOT/path).resolve();assert p.is_relative_to(ROOT) and p.is_file(),path
        raw=p.read_bytes();assert digest(raw)==checksum,('Source bytes changed',path)
        sources[path]=json.loads(raw) if path.endswith('.json') else raw.decode()
    for ref in data['source_index']:
        actual=pointer(sources[ref['path']],ref['pointer']) if ref['path'].endswith('.json') else sources[ref['path']]
        raw=json.dumps(actual,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        assert digest(raw)==ref['value_sha256'],('Source pointer changed',ref['path'],ref['pointer'])
        assert ref['sha256']==data['source_inputs_sha256'][ref['path']]
    return {'files':len(sources),'pointers':len(data['source_index'])}


def svg_geometry(raw):
    root=ET.fromstring(raw);result={}
    for group in root.iter(NS+'a'):
        fid=group.get('data-feature-id')
        if not fid:continue
        assert fid not in result
        # Publication label offsets and symbol sizes are excluded. The source
        # path or point anchor, not just an asserted metadata hash, is compared.
        paths=[p.get('d') for p in group.findall(NS+'path')]
        anchors=[p.get('transform') for p in group.findall(NS+'g')]
        result[fid]={'paths':paths,'anchors':anchors,'hash':group.get('data-geometry-sha256'),
                     'role':group.get('data-geometry-role')}
    return root,result


def verify(info,reader,*,build_control_reader=None):
    get=lru_cache(maxsize=None)(reader);hashes=info['files_sha256'];meta=info[KEY]
    assert meta['version']==VERSION and meta['research_version']==RESEARCH_VERSION
    assert json.loads(get(MANIFEST))==meta
    required={DATA,PAGE,PDF,FOLDER+'/source-index.json',FOLDER+'/atlas.js',FOLDER+'/atlas.css',RELEASE_ARCHIVE,*HOME_ARCHIVES.values()}
    assert required<=set(meta['files_sha256'])
    for path,checksum in meta['files_sha256'].items():assert digest(get(path))==checksum==hashes[path],path
    assert digest(get(MANIFEST))==hashes[MANIFEST] and digest(get(BUNDLE))==hashes[BUNDLE]
    for ext in ['css','js']:assert get(FOLDER+'/atlas.'+ext)==(ROOT/'web'/(VERSION+'.'+ext)).read_bytes()
    old_info,old_reader=restore_r10_context(info,get)
    assert KEY not in old_info and 'city_layout_r10' in old_info
    expected_old=set(old_info['files_sha256'])-{*HOME_PAGES,'release.json',*BUILD_CONTROL_FILES}
    assert set(meta['protected_files_sha256'])==expected_old
    for p,checksum in meta['protected_files_sha256'].items():assert digest(get(p))==checksum==old_info['files_sha256'][p],p
    if build_control_reader:
        for p,checksum in meta['build_control_files_sha256'].items():assert digest(build_control_reader(p))==checksum
    data=json.loads(get(DATA));assert data['source_commit']==meta['source_commit']==info['source_commit']
    assert data['counts']==meta['counts'] and data['coordinate_contract']==meta['coordinate_contract']
    result=validate_data(data);result['sources']=check_sources(data)
    assert data['source_inputs_sha256']==meta['source_inputs_sha256']
    first=None
    for view in data['views']:
        path=FOLDER+'/maps/'+view['id']+'.svg';root,geometry=svg_geometry(get(path))
        assert root.get('data-coordinate-frame')==data['frame']['id']
        assert set(geometry)=={f['id'] for f in data['features']}
        if first is None:first=geometry
        else:assert geometry==first,('A region redrew/rearranged the city geometry',view['id'])
    for f in data['features']:assert first[f['id']]['hash']==f['geometry_sha256']
    page=Document(get(PAGE));assert len(page.ids)==len(set(page.ids)),'Duplicate page anchor'
    assert json.loads(page.script)==data
    assert set(page.feature_buttons)=={f['id'] for f in data['features']}
    assert {'feature-'+f['id'] for f in data['features']}<=set(page.ids)
    assert {'entity-'+e['id'] for e in data['coverage']}<=set(page.ids)
    assert page.downloads==meta['download_files'] and len(page.downloads)==len(set(page.downloads))
    csv_counts={}
    for key,fields in data['csv_fields'].items():
        rows=list(csv.DictReader(io.StringIO(get(FOLDER+'/'+key+'.csv').decode('utf-8-sig'))))
        expected=data['source_index'] if key=='source-index' else data[key]
        assert len(rows)==len(expected) and set(rows[0])==set(fields)
        for written,original in zip(rows,expected):
            for field in fields:
                value=original.get(field)
                wanted=json.dumps(value,ensure_ascii=False) if isinstance(value,(dict,list,bool)) or value is None else str(value)
                assert written[field]==wanted,(key,field)
        csv_counts[key]=len(rows)
    assert get(PDF).startswith(b'%PDF-') and get(PDF).rstrip().endswith(b'%%EOF')
    assert meta['pdf_details']==data['pdf'] and data['pdf']['pages']==len(data['views'])+1
    with ZipFile(io.BytesIO(get(BUNDLE))) as z:
        names=z.namelist();assert len(names)==len(set(names))
        assert set(names)=={'index.html',MANIFEST,*meta['files_sha256']}
        for path in meta['files_sha256']:assert z.read(path)==get(path),path
        offline=Document(z.read('index.html'));assert json.loads(offline.script)==data and offline.downloads==page.downloads
        assert z.read(MANIFEST)==get(MANIFEST)
    result.update({'status':'passed','source_commit':info['source_commit'],'same_geometry_views':len(data['views']),
                   'csv_rows':csv_counts,'pdf_pages':data['pdf']['pages'],'downloads':len(page.downloads),
                   'protected_public_files':len(expected_old),'offline_members':len(names)})
    return result
