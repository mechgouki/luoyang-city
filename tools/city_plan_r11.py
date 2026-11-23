"""Publish the R11 shared-coordinate reconstruction without changing earlier maps."""
import copy
import csv
import json
import math
from collections import Counter
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

from city_plan_r11_contract import (
    KEY, VERSION, RESEARCH_VERSION, PAGE, FOLDER, DATA, MANIFEST, PDF, BUNDLE,
    HOME_PAGES, HOME_ARCHIVES, RELEASE_ARCHIVE, BUILD_CONTROL_FILES,
    CURRENT_MILESTONE, digest, add_home, restore_r10_context,
)
from city_plan_r11_geometry import build_geometry
from city_plan_r11_maps import bounds, frame_box, geom_hash, layer, sheet, method_sheet
from city_plan_r11_page import make_page
from city_plan_r11_pdf import build_pdf

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'research/city-plan-r11'
BASE='https://mechgouki.github.io/luoyang-city/'


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):return digest(Path(path).read_bytes())
def dump(path,data):Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def refs(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if k in {'source_refs','source_inputs'} and isinstance(v,list):
                yield from (r for r in v if isinstance(r,dict))
            else:yield from refs(v)
    elif isinstance(value,list):
        for v in value:yield from refs(v)


def resolve(document,pointer):
    assert pointer=='' or pointer.startswith('/'),pointer
    v=document
    for segment in pointer.split('/')[1:]:
        key=segment.replace('~1','/').replace('~0','~')
        if isinstance(v,list):
            assert key.isdecimal() and str(int(key))==key
            v=v[int(key)]
        else:v=v[key]
    return v


def source_index(geometry,objects):
    records={}
    sources=[*geometry.get('sources',[]),*objects.get('sources',[]),*refs(geometry),*refs(objects)]
    for path in sorted(SOURCE.glob('*.json')):
        sources.append({'path':str(path.relative_to(ROOT)),'pointer':''})
    for r in sources:
        if not isinstance(r,dict) or not r.get('path'):continue
        p=r['path'];target=(ROOT/p).resolve()
        if not target.is_relative_to(ROOT) or not target.is_file():
            raise ValueError('A cited project source is missing: '+p)
        pointer=r.get('pointer','');key=(p,pointer)
        raw=target.read_bytes();checksum=digest(raw)
        if r.get('sha256') and r['sha256']!=checksum:
            raise ValueError('Source input changed while deriving geometry: '+p)
        actual=resolve(json.loads(raw),pointer) if p.endswith('.json') else raw.decode()
        encoded=json.dumps(actual,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        records[key]={'path':p,'pointer':pointer,'sha256':checksum,'value_sha256':digest(encoded),
                      'locator':r.get('locator') or r.get('label') or p+pointer,
                      'url':r.get('url'),'excerpt':encoded.decode()[:1400]}
    return list(records.values())


def make_views(geometry,objects,features):
    source=[f for f in features if layer(f)=='source' and f.get('default_visible') is not False]
    # A city view is a camera, not a polygon claiming an ancient city boundary.
    extent=bounds([f for f in features if f.get('default_visible') is not False],180)
    views=[{'id':'all','title':'全城 · 共同坐标复原平面','bbox':frame_box(extent,1790,965),
            'subtitle':'来源骨架、局部原图与文献候选位置在同一母图中联读。'}]
    focus=[f for f in features if f['id'] in {'geo-changhe-palace-gate','geo-taiji-hall-reference','geo-yongning-pagoda-reference'} or f['id'].startswith('r11-yongning-')]
    views.append({'id':'core','title':'宫城中轴—永宁寺 · 共同坐标取景','bbox':frame_box(bounds(focus,140),1790,965),
                  'subtitle':'局部轮廓等比接入；不同来源的距离与方向差异保留在图上。'})
    for identifier,prefix,title,note in [
        ('changhe','r11-changhe-','阊阖门 · 原图构件接入','10个构件按S37原图20米尺等比转换；候选绑定仍未取得现场共同控制。'),
        ('yongning','r11-yongning-','永宁寺 · 刊载平面接入','寺墙、塔基、佛殿与门址逐项描取；06a残墙与新刊载图分别保留。')]:
        fs=[f for f in features if f['id'].startswith(prefix)]
        if not fs:raise ValueError('Missing required real traced plan: '+identifier)
        views.append({'id':identifier,'title':title,'bbox':frame_box(bounds(fs,20),1790,965),'subtitle':note})
    palace=[f for f in features if f.get('source_plan_id')=='palace-2013' or f['id'].startswith('r11-palace2013-')]
    if palace:
        views.append({'id':'palace2013','title':'宫城 · 2013年刊载概览对照','bbox':frame_box(bounds(palace,60),1790,965),
                      'subtitle':'同名阊阖—太极图示点距：本图约502米，06a约574米。隔壁、版筑与调查标记各按原类型读取。'})
    regions=objects['regions']
    assert len(regions)==11
    for region in regions:
        rid=region['id'];box=region.get('bbox') or region.get('bbox_xy_m') or region.get('view_bbox_m') or region.get('bounds_xy_m')
        if box is None:
            fs=[f for f in features if rid in f.get('region_ids',[])]
            box=bounds(fs,140)
        if box is None:
            box=geometry['frame']['source_bounds_xy_m']
        assert len(box)==4 and box[0]<box[2] and box[1]<box[3],(rid,box)
        views.append({'id':rid,'title':rid+' · '+region.get('title',region.get('name',rid)),
                      'bbox':frame_box(box,1790,965),'subtitle':'同一母图的片区取景；窗口边缘不是历史坊界或行政边界。',
                      'region_record':region})
    return views


def build_data(commit):
    from city_plan_r11_objects import build_objects
    geometry=build_geometry(ROOT)
    objects=build_objects(ROOT,geometry)
    features=copy.deepcopy(geometry['features']+objects['features'])
    assert len({f['id'] for f in features})==len(features),'Duplicate map feature'
    for f in features:
        f['layer']=layer(f);f['geometry_sha256']=geom_hash(f)
        f.setdefault('source_refs',[]);f.setdefault('limits',[])
        if isinstance(f['limits'],str):f['limits']=[f['limits']]
    entities=copy.deepcopy(objects['entities'])
    raw_entities={e['id']:e for e in load(ROOT/'data/entities.json')}
    assert len(entities)==339 and {e['id'] for e in entities}==set(raw_entities)
    feature_by_id={f['id']:f for f in features}
    for e in entities:
        e.setdefault('name',raw_entities[e['id']]['name'])
        e.setdefault('source_refs',[])
        e.setdefault('feature_ids',[])
        assert all(fid in feature_by_id for fid in e['feature_ids']),e['id']
        links=[feature_by_id[fid] for fid in e['feature_ids']]
        if any(f['layer'] in {'source','trace','scale','palace'} for f in links):group='source'
        elif links:group='candidate'
        else:group='unplaced'
        e['placement_group']=group
    index=source_index(geometry,objects)
    layers=Counter(f['layer'] for f in features)
    constraints=objects['constraints']
    views=make_views(geometry,objects,features)
    # The paper source is a secondary publication of an identified excavation
    # figure; this relationship is explicit rather than relabelled as a new survey.
    source_summary=[
        {'id':'source-06a','label':'2012年申遗文本图06a：全城来源骨架（PDF第3457页）','url':'https://whc.unesco.org/uploads/nominations/1442.pdf'},
        {'id':'source-s37','label':'申遗附件S37阊阖门局部平面（PDF第1962页）；本项目已保存原生图及校准','path':'research/prosperity-v3/gate-plan.json'},
        {'id':'source-yongning','label':'杭侃《〈洛阳伽蓝记〉慧嶷故事四论》，2025年第11期，第61页图二右；重刊1996永宁寺发掘报告第7页平面','url':'https://img.dpm.org.cn/Uploads/file/2026/03/03/1772531673ogEopWUYs218985.pdf'},
        {'id':'source-nara1995','label':'奈良国立文化財研究所年報1995：永宁寺西门调查文字（图版在此次PDF中留白）','url':'https://repository.nabunken.go.jp/dspace/bitstream/11177/5227/1/AN00181387_1995_2_3.pdf'},
        {'id':'source-relations','label':'R10已核关系与原文指针：本轮用于共同母图候选位置校核','path':'research/city-layout-r10/regions.json'},
    ]
    for s in geometry.get('sources',[]):
        if '2013' in str(s) and isinstance(s,dict):source_summary.append(copy.deepcopy(s))
    return {
        'schema':'luoyang-city-plan-r11-v1','research_version':RESEARCH_VERSION,'implementation_version':VERSION,
        'source_commit':commit,'target_years':[516,528],'baseline_commit':'a2d1aac203d468ab0584a09f2c9ec0bfc6dd372b',
        'frame':geometry['frame'],'features':features,'bindings':geometry['bindings'],
        'objects':objects.get('objects',[]),'coverage':entities,'constraints':constraints,'regions':objects['regions'],'views':views,
        'source_index':index,'source_inputs_sha256':{r['path']:r['sha256'] for r in index},
        'source_summary':source_summary,'diagnostics':{'geometry':geometry['diagnostics'],'objects':objects['diagnostics']},
        'coordinate_contract':{'all_views_share_geometry':True,'source_projection_reused':True,
                               'frame_is_wgs84':False,'field_registration_verified':False,'verified_shared_controls':0,
                               'new_field_coordinates':0,'hypothesis_coordinates_are_measurements':False,
                               'all_entities_have_footprints':False,'unknown_boundaries_filled':False,
                               'legacy_display_rectangles_reused_as_buildings':False,
                               'modern_river_used_as_northern_wei_bank':False},
        'counts':{'source_features':layers['source'],'trace_features':layers['trace'],'scale_features':layers['scale'],
                  'published_overview_features':layers['palace'],
                  'candidate_features':layers['candidate'],'features':len(features),'entities':len(entities),
                  'regions':len(objects['regions']),'views':len(views),'constraints':len(constraints),
                  'entity_placement_groups':dict(Counter(e['placement_group'] for e in entities)),
                  'source_files':len({r['path'] for r in index}),'source_pointers':len(index)},
        'homepage_revision':'panorama-approved-v12','homepage_replacement_approved':False,
        'new_historical_coordinates':0,'new_shoreline_geometries':0,'evidence_grade_upgrades':0,
    }


def write_csv(path,fields,rows):
    with Path(path).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(row.get(k),ensure_ascii=False) if isinstance(row.get(k),(list,dict,bool)) or row.get(k) is None else row[k] for k in fields})


def downloads_for(data):
    files=[(PDF,'完整复原工作图册 · PDF',f"{data['pdf']['pages']}页；全城A2、局部与片区A3矢量图"),
           (BUNDLE,'图纸与证据离线包 · ZIP','解压后打开index.html，离线地图与表格可用')]
    files += [(FOLDER+'/maps/'+v['id']+'.svg',v['title']+' · SVG','同一坐标母图的独立矢量取景') for v in data['views']]
    files += [(FOLDER+'/maps/method.svg','图例与方法 · SVG','来源轮廓、候选接入和未定位对象如何区分'),
              (FOLDER+'/coverage.csv','全部339项对象去向 · CSV','来源关联、候选点、时相与未定位说明'),
              (FOLDER+'/features.csv','全部图上构件与坐标 · CSV','共同坐标、轮廓角色、来源指针与限制'),
              (FOLDER+'/constraints.csv','方向关系处理表 · CSV','逐条关系、评估结果与原文指针'),
              (FOLDER+'/source-index.csv','逐段图源核验 · CSV','源文件与字段、原值校验及定位语'),
              (DATA,'完整工作坐标与证据 · JSON','局部米制工作数据，不是WGS84 GeoJSON'),
              (FOLDER+'/source-index.json','图源复核索引 · JSON','本轮所有实际使用字段与内容摘要'),
              (MANIFEST,'发布与文件校验清单 · JSON','完整资源哈希、来源提交与前版保护')]
    return files


def build(site=ROOT/'_site'):
    site=Path(site);info_now=load(site/'build-info.json')
    previous_info,read_previous=restore_r10_context(info_now,lambda p:(site/p).read_bytes())
    assert 'city_layout_r10' in previous_info
    before_release=read_previous('release.json');before_homes={p:read_previous(p) for p in HOME_PAGES}
    original_hashes=copy.deepcopy(previous_info['files_sha256'])
    dest=site/FOLDER;dest.mkdir(parents=True,exist_ok=True)
    (dest/'maps').mkdir(exist_ok=True);(dest/'archive').mkdir(exist_ok=True)
    (site/RELEASE_ARCHIVE).write_bytes(before_release)
    for p,raw in before_homes.items():(site/HOME_ARCHIVES[p]).write_bytes(raw)
    data=build_data(previous_info['source_commit'])
    maps={v['id']:sheet(data,v) for v in data['views']};method=method_sheet(data)
    for vid,svg in {**maps,'method':method}.items():(dest/'maps'/(vid+'.svg')).write_text(svg,encoding='utf-8')
    data['pdf']=build_pdf(site/PDF,maps,method,data)
    data['counts']['pdf_pages']=data['pdf']['pages']
    data['csv_fields']={
        'features':['id','component_id','entity_ids','label','geometry_role','placement_status','binding_id','layer','geometry','source_refs','limits','geometry_sha256'],
        'coverage':sorted({k for r in data['coverage'] for k in r}),
        'constraints':sorted({k for r in data['constraints'] for k in r}),
        'source-index':['path','pointer','sha256','value_sha256','locator','url','excerpt'],
    }
    dump(site/DATA,data);dump(dest/'source-index.json',data['source_index'])
    for key,fields in data['csv_fields'].items():write_csv(dest/(key+'.csv'),fields,data['source_index'] if key=='source-index' else data[key])
    for ext in ('css','js'):shutil.copyfile(ROOT/'web'/(VERSION+'.'+ext),dest/('atlas.'+ext))
    downloads=downloads_for(data)
    (site/PAGE).write_text(make_page(data,downloads),encoding='utf-8')
    for p,raw in before_homes.items():(site/p).write_bytes(add_home(raw))
    assets=sorted(str(p.relative_to(site)) for p in dest.rglob('*') if p.is_file() and str(p.relative_to(site))!=MANIFEST)
    assets += [PAGE,PDF]
    protected={p:h for p,h in original_hashes.items() if p not in {*HOME_PAGES,'release.json',*BUILD_CONTROL_FILES}}
    for p,checksum in protected.items():assert sha(site/p)==checksum,('R11 changed previous publication',p)
    meta={
        'version':VERSION,'research_version':RESEARCH_VERSION,'source_commit':data['source_commit'],
        'page':PAGE,'folder':FOLDER,'record':DATA,'manifest':MANIFEST,'pdf':PDF,'bundle':BUNDLE,'offline_entry':'index.html',
        'counts':data['counts'],'pdf_details':data['pdf'],'download_files':[d[0] for d in downloads],
        'files_sha256':{p:sha(site/p) for p in assets},'protected_files_sha256':protected,
        'build_control_files_sha256':{p:original_hashes[p] for p in BUILD_CONTROL_FILES if p in original_hashes},
        'source_inputs_sha256':data['source_inputs_sha256'],'coordinate_contract':data['coordinate_contract'],
        'predecessor_release':{'path':RELEASE_ARCHIVE,'sha256':digest(before_release)},
        'predecessor_homepage':{p:{'archive':HOME_ARCHIVES[p],'sha256':digest(raw)} for p,raw in before_homes.items()},
        'homepage_before_sha256':{p:digest(raw) for p,raw in before_homes.items()},
        'homepage_after_sha256':{p:sha(site/p) for p in HOME_PAGES},
        'homepage_revision':'panorama-approved-v12','homepage_replacement_approved':False,
        'new_historical_coordinates':0,'new_shoreline_geometries':0,'evidence_grade_upgrades':0,
    }
    dump(site/MANIFEST,meta)
    with ZipFile(site/BUNDLE,'w',ZIP_DEFLATED) as z:
        z.writestr('index.html',make_page(data,downloads,offline=True))
        for p in [*assets,MANIFEST]:z.writestr(p,(site/p).read_bytes())
    release=json.loads(before_release);release['extensions']=sorted(set(release['extensions'])|{VERSION})
    release[KEY+'_version']=VERSION;release['current_milestone']=CURRENT_MILESTONE;dump(site/'release.json',release)
    info=copy.deepcopy(previous_info);info[KEY]=meta;info['files_sha256']=original_hashes
    for p in [*assets,MANIFEST,BUNDLE,*HOME_PAGES,'release.json']:info['files_sha256'][p]=sha(site/p)
    dump(site/'build-info.json',info)
    return meta


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--site',type=Path,default=ROOT/'_site');p.add_argument('--verify',action='store_true');args=p.parse_args()
    if args.verify:
        from city_plan_r11_verify import verify
        result=verify(load(args.site/'build-info.json'),lambda name:(args.site/name).read_bytes())
    else:result=build(args.site)['counts']
    print(json.dumps(result,ensure_ascii=False))
