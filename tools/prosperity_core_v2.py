#!/usr/bin/env python3
"""Publish the core scale workbench while preserving the P1 research views."""
from pathlib import Path
import hashlib, json, re, shutil, zipfile
from dual_cartography import load, dump, write_svg
from north_b4 import fp, render_atlas
from prosperity_core_geometry import (ITEMS, SOURCE, scale_models, core_map,
    dimension_figure, comparison_plate, relation_plate, courtyard_plate)

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'_site'
OUT=SITE/'prosperity-core'
RESEARCH=ROOT/'research/prosperity-v2'
VERSION='prosperity-core-v2'
MUTABLE={'index.html','v3.0-dual.html','prosperity.html','build-info.json','release.json'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def own(path):
    return (path.startswith('prosperity-core/') or path in ['prosperity-core.html','prosperity-before-core.html']
        or path.startswith('downloads/prosperity-core-v2-') or (path.startswith('_assets/') and '-prosperity-core-v2.' in path))

def main():
    info=load(SITE/'build-info.json');assert info['prosperity']['version']=='prosperity-v1'
    protected={str(p.relative_to(SITE)):sha(p) for p in SITE.rglob('*') if p.is_file()
        and str(p.relative_to(SITE)) not in MUTABLE and not own(str(p.relative_to(SITE)))}
    geo=load(ROOT/'research/prosperity-v1/geographic-evidence.json')
    basis=load(RESEARCH/'core-scale-basis.json');relations=load(RESEARCH/'core-relations.json')
    models=scale_models(geo,basis)
    assert len(models)==3 and len(relations['scenes'])==3
    OUT.mkdir(parents=True,exist_ok=True)
    p,plan_boxes,plan_focus,plan_meta=core_map(geo,models)
    o,oblique_boxes,oblique_focus,oblique_meta=core_map(geo,models,True)
    write_svg(OUT/'core-plan.svg',p);write_svg(OUT/'core-oblique.svg',o)
    write_svg(OUT/'scale-comparison.svg',comparison_plate(models))
    write_svg(OUT/'courtyard-comparison.svg',courtyard_plate(geo,basis))
    figures=[{'id':'scale-comparison','title':'同一比例，看建筑大小','url':'./prosperity-core/scale-comparison.svg',
              'caption':'三片共用同一米制比例。门基、殿址范围与塔基地上遗存分别取值，上部建筑形态未定。'},
             {'id':'courtyard-comparison','title':'永宁寺院界：先核对，再落位','url':'./prosperity-core/courtyard-comparison.svg',
              'caption':'来源总图墙线与附表尺寸存在差异。212 × 301 m院界仅作独立比较，不覆盖城市图上的原墙线。'}]
    for scene in relations['scenes']:
        name=scene['id'].replace('_','-')+'.svg'
        write_svg(OUT/name,relation_plate(scene))
        figures.append({'id':scene['id'],'title':scene['title'],'url':'./prosperity-core/'+name,
                        'caption':'构成与方向关系图；间距和节点大小属于阅读安排，不换算为测绘尺度。'})
    items=[]
    for m in models:
        filename=m['id']+'-scale.svg';write_svg(OUT/filename,dimension_figure(m))
        d=m['dimensions_m']
        height_note=('约6 m是地下夯土深度，未用作台高。' if m['id']=='core-taiji'
            else '2.2 m是现存塔基残高，未用作盛时建筑高。' if m['id']=='core-yongning-tower'
            else '表列尺寸只指门基，不包括整组阙、院与连接基址。')+' 盛时原高与屋顶仍待证。'
        related='./prosperity.html#view=geography&'+('entity='+m['entity_id'] if m['entity_id'] else 'feature='+m['source_feature_id'])
        items.append({k:m[k] for k in ['id','name','entity_id','source_feature_id','position_note','orientation_note','source_url','source_label']} |
            {'kind':'定尺平面参照','dimensions_label':('约 ' if m['approximate_dimensions'] else '')+f"{d['east_west']:g} × {d['north_south']:g} m",
             'height_note':height_note,'boxes':{'plan':plan_boxes[m['id']],'oblique':oblique_boxes[m['id']]},
             'detail_figure':{'url':'./prosperity-core/'+filename,'caption':'按表列尺度绘制的外接尺度片；不代表完整建筑轮廓。'},
             'related_url':related})
    focuses=[{'id':key,'label':label,'boxes':{'plan':plan_focus[key],'oblique':oblique_focus[key]}}
             for key,label in [('all','全核心区'),('palace','宫城'),('yongning','永宁寺')]]
    sources=[{'title':'遗址分布与来源坐标','url':SOURCE+'#page=3457','note':'1997航摄、1999实测底图；西安1980坐标。定位保留总图概化。'},
        {'title':'建筑平面尺度附表','url':SOURCE+'#page=1926','note':'宫墙、宫城阊阖门基、太极殿与永宁寺，见1926—1931页。'},
        {'title':'阊阖门局部考古平剖面','url':SOURCE+'#page=1962','note':'三通道、东西阙与编号院区；不从小图补精确柱位。'},
        {'title':'永宁寺总图与西门','url':SOURCE+'#page=1965','note':'与文献关系对读；来源总图的尺度不能无条件移到单体图。'},
        {'title':'永宁寺塔基平剖面','url':SOURCE+'#page=1966','note':'塔心、周边构造与四向慢道；破坏沟不转为盛时水道。'},
        {'title':'永宁寺院布局参照图','url':SOURCE+'#page=3453','note':'用于检查塔与院心的相对关系，不能自动成为地理定位依据。'}]
    downloads=[{'label':'核心建筑图册 PDF','url':'./downloads/prosperity-core-v2-atlas.pdf','type':'pdf'},
        {'label':'核心尺度与局部关系数据包','url':'./downloads/prosperity-core-v2-package.zip','type':'zip'},
        {'label':'位置与尺度方法说明','url':'./prosperity-core/method.md','type':'md'},
        {'label':'局部关系与出处说明','url':'./prosperity-core/relations.md','type':'md'},
        {'label':'平面模板几何与证据 JSON','url':'./prosperity-core/models.json','type':'json'}]
    data={'version':VERSION,'source_commit':info['source_commit'],'title':'核心建筑，进入真实尺度',
        'period':'516—528 · 盛时综合','intro':'从宫门到殿址，再到永宁寺塔基。沿同一套位置依据，看清三座核心建筑的平面尺度与局部构成。',
        'maps':{'plan':{'url':'./prosperity-core/core-plan.svg','viewBox':[0,0,1800,1500],'title':'核心建筑定尺平面'},
                'oblique':{'url':'./prosperity-core/core-oblique.svg','viewBox':[0,0,1800,1500],'title':'核心建筑布局鸟瞰'}},
        'focuses':focuses,'items':items,'figures':figures,'sources':sources,'downloads':downloads,
        'projection':plan_meta,'oblique_projection':oblique_meta,
        'research_limits':{'new_ancient_absolute_coordinates':0,'historical_heights_reconstructed':False,
            'roofs_reconstructed':False,'ancient_ground_surface_reconstructed':False,'full_city_reconstruction_completed':False,
            'court_template_placed_in_city':False}}
    dump(OUT/'data.json',data)
    dump(OUT/'models.json',{'version':VERSION,'source_commit':info['source_commit'],'models':models,
        'position_source':'../prosperity/geographic-evidence.json','source_crs':'EPSG:4610',
        'historical_heights_reconstructed':False,'court_template_placed_in_city':False})
    dump(OUT/'core-scale-basis.json',basis);dump(OUT/'core-relations.json',relations)
    shutil.copyfile(ROOT/'docs/prosperity-core-scale-method.md',OUT/'method.md')
    shutil.copyfile(ROOT/'docs/prosperity-core-relations.md',OUT/'relations.md')
    atlas_names=['core-plan.svg','core-oblique.svg','scale-comparison.svg','courtyard-comparison.svg']
    atlas_names += [s['id'].replace('_','-')+'.svg' for s in relations['scenes']]
    render_atlas([OUT/n for n in atlas_names],SITE/'downloads/prosperity-core-v2-atlas.pdf')
    css=fp('prosperity-core-v2.css',(ROOT/'web/prosperity-core-v2.css').read_bytes())
    js=fp('prosperity-core-v2.js',(ROOT/'web/prosperity-core-v2.js').read_bytes())
    page=(ROOT/'web/prosperity-core-v2.html').read_text().replace('./prosperity-core-v2.css','./'+css).replace('./prosperity-core-v2.js','./'+js)
    (SITE/'prosperity-core.html').write_text(page)
    old=(SITE/'prosperity.html').read_text()
    old=re.sub(r'<p id="core-scale-entry".*?</p>\s*','',old,flags=re.S)
    (SITE/'prosperity-before-core.html').write_text(old)
    entry='<p id="core-scale-entry" style="padding:14px 18px;background:#e9eee2;border-left:3px solid #48715b"><a href="./prosperity-core.html" style="color:#244c3e;font-weight:600">继续看核心建筑尺度：宫城阊阖门、太极殿与永宁寺塔基 →</a></p>'
    new=old.replace('<nav class="view-switch"',entry+'\n    <nav class="view-switch"',1)
    assert old!=new,'P1 entry insertion failed'
    (SITE/'prosperity.html').write_text(new)
    for name in ['index.html','v3.0-dual.html']:
        p=SITE/name;s=p.read_text()
        s=re.sub(r'<p id="core-scale-home-link".*?</p>','',s,flags=re.S)
        match=re.search(r'<section id="prosperity-entry".*?</section>',s,re.S);assert match
        block=match.group(0).replace('</section>','<p id="core-scale-home-link"><a href="./prosperity-core.html">新增：核心建筑尺度与局部结构 →</a></p></section>')
        p.write_text(s[:match.start()]+block+s[match.end():])
    assert all(sha(SITE/p)==v for p,v in protected.items()),'A preserved P1 or earlier asset changed'
    dump(OUT/'preservation.json',{'version':VERSION,'source_commit':info['source_commit'],'protected_unchanged':True,
        'protected_files':protected,'existing_entity_ids_unchanged':True,'source_geometry_unchanged':True,
        'p1_entry_archive':'prosperity-before-core.html','p1_entry_before_sha256':sha(SITE/'prosperity-before-core.html'),
        'p1_entry_after_sha256':sha(SITE/'prosperity.html')})
    with zipfile.ZipFile(SITE/'downloads/prosperity-core-v2-package.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.iterdir()):
            if p.is_file():z.write(p,'prosperity-core/'+p.name)
        z.writestr('README.txt','核心尺度P2：3个表列尺度片沿用P1原图概略锚点；工作朝向不是实测方位角。局部构成图为无比例关系图。院界模板未落位，古高、屋顶及古代地面保持未知。')
    release=load(SITE/'release.json');release['extensions']=sorted(set(release.get('extensions',[])+[VERSION]))
    release['prosperity_core_version']=VERSION;release['current_milestone']='盛时P2：核心建筑尺度与局部结构';dump(SITE/'release.json',release)
    info['prosperity_core']={'version':VERSION,'source_commit':info['source_commit'],'metric_templates':3,
        'local_relation_scenes':len(relations['scenes']),'local_components':sum(len(s['nodes']) for s in relations['scenes']),
        'local_relations':sum(len(s['relations']) for s in relations['scenes']),'atlas_pages':len(atlas_names),
        'source_crs':'EPSG:4610','new_ancient_absolute_coordinates':0,'historical_heights_reconstructed':False,
        'roofs_reconstructed':False,'ancient_ground_surface_reconstructed':False,'court_template_placed_in_city':False,
        'protected_files':len(protected),'metadata':'prosperity-core/data.json'}
    info['files_sha256']={str(p.relative_to(SITE)):sha(p) for p in sorted(SITE.rglob('*')) if p.is_file() and p.name!='build-info.json'}
    dump(SITE/'build-info.json',info)
    (ROOT/'artifacts').mkdir(exist_ok=True);dump(ROOT/'artifacts/prosperity-core-build.json',info['prosperity_core'])
    print(json.dumps(info['prosperity_core'],ensure_ascii=False))

if __name__=='__main__':main()
