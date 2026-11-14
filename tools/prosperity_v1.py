#!/usr/bin/env python3
"""Publish the first prosperity-first literary and source-geographic workbench."""
from pathlib import Path
import csv, html, hashlib, json, re, shutil, zipfile, xml.etree.ElementTree as ET
from dual_cartography import load, dump, write_svg, svg, text, para, rect, C, node, NS
from north_b4 import fp, render_atlas
from prosperity_maps import literary_plan, palace_relations, source_layout

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'_site'
RESEARCH=ROOT/'research/prosperity-v1'
OUT=SITE/'prosperity'
MUTABLE={'index.html','v3.0-dual.html','build-info.json','release.json'}
VERSION='prosperity-v1'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def is_own(p):
    return p.startswith('prosperity/') or p=='prosperity.html' or p.startswith('downloads/prosperity-') or (p.startswith('_assets/') and '-prosperity-v1.' in p)

def source_list(text_review,geo):
    found={}
    for source in geo.get('sources',[]):
        key=source.get('id',source.get('url','')); found[key]={'id':key,'title':source.get('title',key),'url':source.get('url','')+('#page='+str(source['pdf_page']) if source.get('pdf_page') else ''),'period':source.get('period',source.get('source_period',source.get('document_date',''))),'role':source.get('role','历史地理来源'),'note':source.get('note',source.get('rights_note',''))}
    for source in text_review.get('source_snapshots',[]):
        key=source.get('id',source.get('key',source.get('url','')));found[key]={'id':key,'title':source.get('title',source.get('edition',source.get('name',key)))+(' · 卷'+str(source['volume']) if source.get('volume') else ''),'url':source.get('url',''),'role':'古籍电子正文与注释分层核对','note':source.get('note','电子转录的匹配不等于古刻书影逐叶校勘。')}
    if not any('unesco' in str(v.get('url')) for v in found.values()):
        found['unesco-nomination']={'id':'unesco-nomination','title':'汉魏洛阳故城保护管理规划 · 申遗原件','url':'https://whc.unesco.org/uploads/nominations/1442.pdf#page=3457','period':'2012年规划；底图1997航摄、1999实测','role':'遗址分布与原图坐标依据','note':'原图西安1980坐标。图示遗址不自动等于盛时逐栋建筑清单。'}
    return list(found.values())

def entities_data(ledger,text_review,geo,geo_boxes,pano_boxes):
    originals={e['id']:e for e in load(ROOT/'data/entities.json')}
    reviewed={r.get('key',r.get('record_key','')):r for r in text_review.get('records',[])}
    decisions=text_review.get('map_decisions',[])
    output=[]
    for row in ledger:
        eid=row['id'];original=originals[eid]; targets=row['targets']
        box=None
        if targets:
            xs=[t['x']+200 for t in targets];ys=[t['y']+640 for t in targets]
            box=[min(xs)-650,min(ys)-520,max(xs)-min(xs)+1300,max(ys)-min(ys)+1040]
        evidence=[]
        applicable=[d for d in decisions if eid in d.get('affected_entity_ids',d.get('entity_ids',[]))]
        for ref in row['direct_evidence_refs']:
            item=reviewed.get(ref['key'],{})
            manual=item.get('manual_context_review') or {}
            q=manual.get('corrected_quote') or item.get('legacy_quote','')
            related=[d for d in applicable if ref['key'] in d.get('evidence_keys',[])]
            for decision in related:
                if decision.get('corrected_quote'):q=decision['corrected_quote']
            reading='；'.join(d.get('finding',d.get('visual_instruction','')) for d in related)
            if not reading:reading=manual.get('finding') or item.get('legacy_reading_preserved','')
            reading=reading.replace('small.inline-note','现代夹注层')
            editorial=manual.get('editorial_note')
            if editorial:
                reading+=' 另列'+editorial.get('author','')+'现代校注：“'+editorial.get('quote','')+'”'+('；“'+editorial['second_note']+'”' if editorial.get('second_note') else '')
            checks=item.get('source_checks',[])
            corrected_checks=manual.get('corrected_excerpt_checks',[])
            source_url=next((c.get('url') for c in corrected_checks if c.get('status')=='matched' and c.get('url')),None)
            if not source_url:source_url=next((c.get('retrieved_url') or c.get('declared_url') for c in checks if c.get('status')=='matched_in_nonmodern_note_text'),None)
            locator=manual.get('locator') or item.get('legacy_locator')
            evidence.append({'id':ref['key'],'title':ref.get('title',ref['key']),'quote':q,
                             'reading':reading+(' 出处：'+locator if locator else ''),
                             'url':source_url or (checks[0].get('retrieved_url') if checks else None) or ref.get('link',original['source_url']),
                             'quote_class':item.get('quotation_class'),'text_checked':item.get('electronic_text_checked',False)})
        if not evidence:
            evidence=[{'id':original.get('source_ref',''),'title':'既有名录出处','quote':original.get('source_quote',''),'reading':'保留原名录记录；未因本次界面整合而增加历史确证。','url':original.get('source_url','')}]
        matching=[f for f in geo.get('features',[]) if f.get('entity_id')==eid]
        status='source_mapped_extent' if matching else ('relative_only' if original.get('constraints') else 'unlocated')
        placement='；'.join(dict.fromkeys(f.get('placement_note','来源图已绘范围，仍保留概化与时层限制。') for f in matching)) if matching else '现有文献关系保留；本批尚无可以核验的来源图地理位置。'
        comps='；'.join(d.get('visual_instruction','') for d in applicable if d.get('visual_instruction')).replace('small.inline-note','现代夹注层')
        if not comps:comps=row.get('current_review',{}).get('note',original.get('notes',''))
        temporal_labels={'attested_by_528':'528年前已有相关记载；不表示516—528年全段状态一致。',
                         'later_temple':'封存记载有宅第后改寺的时层；改寺时间与盛时状态另核。',
                         'undated':'年代未详：不能直接据名录确认盛时寺院状态。',
                         'name_layer':'名称时层需区分；后出名称不提前用于盛时。'}
        current=row.get('current_review',{})
        temporal_label=current.get('temporal_label') or temporal_labels.get(row.get('legacy_temporal_state'),'本批未新增该对象的盛时断代结论。')
        e={'id':eid,'name':row.get('display_name',row['name']),'kind':original['type'],
           'aliases':original.get('aliases',[]),'component_summary':comps or '点击下方记载，区分建筑构成、方位与采用解释。',
           'plan_target_ids':[t['id'] for t in targets],'plan_bbox':box,
           'map_bboxes':{k:v for k,v in [('plan',box),('geography',geo_boxes.get(eid)),('panorama',pano_boxes.get(eid))] if v},
           'geographic_status':status,'placement_note':placement,'source_url':original.get('source_url',''),
           'evidence_refs':evidence,'source_feature_ids':[f['id'] for f in matching],
           'shared_plan_target':any(t['member_count']>1 for t in targets),
           'temporal_state':row.get('legacy_temporal_state'),'temporal_label':temporal_label,
           'region_ids':row.get('explicit_focus_regions',[])}
        if matching:
            e['geographic_geometry']={'source_crs':'EPSG:4610','geometries':[f['geometry'] for f in matching],
                                     'role':'source_map_generalized_geometry','absolute_accuracy_verified':False}
            for f in matching:
                evidence.append({'id':f['id'],'title':f.get('label',f['id'])+' · 来源图位置','reading':f.get('placement_note',''),'url':f.get('source_url','https://whc.unesco.org/uploads/nominations/1442.pdf#page=3457')})
        if eid in ['ic_fusang','ic_nailin','ic_dutang','ic_maoci_stele','ic_maoci_hall','ic_liushang']:
            e['detail_figure']={'url':'./prosperity/palace-relations.svg','caption':'G13 原文更正后的四条独立关系；不是院内复原平面。'}
        output.append(e)
    return output

def research_plate(review,geo):
    r=svg(1800,1440,'盛时洛阳本版依据与边界')
    text(r,70,70,'PROSPERITY / EVIDENCE & BOUNDARIES',20,C['gold'])
    text(r,70,132,'把文献关系与地理依据接起来',39,C['ink'],weight=500)
    sections=[('文献核对','已有183条研究记录逐项登记；电子正文、古书子注、现代校注和编辑概述分别处理。实际核验结果与仍需核对项在下载表中分列。'),
              ('地理依据','中国申遗原件中的洛阳保护管理规划提供来源图经纬网和遗址图示。原图为西安1980坐标，底图1997航摄、1999实测；本版没有把它转换为WGS84。'),
              ('本版城市分布','图示位置与范围独立记录；小建筑和门的符号不能当作足迹。没有定位依据的对象仍保留文献关系，未补精确点位。'),
              ('布局鸟瞰','斜视图由城市分布图的同一套平面几何计算。显示抬高不等于古代墙高；未补民居密度和未知院界。'),
              ('仍待解决','古代河道与地面、未定位建筑、来源图绝对误差及分期细节仍需继续研究。本版工程上线不表示四阶段的全部历史问题已经解决。')]
    for i,(h,b) in enumerate(sections):
        y=210+i*220;rect(r,65,y,1670,185,'#eef1e7',C['line'],1,8);text(r,95,y+48,h,28,C['green'],weight=500);para(r,95,y+90,b,74,23)
    text(r,65,1370,'时间：516—528盛时综合。旧B1—B8、H1与历史版本全部保留。',20,C['muted'])
    return r

def main():
    review=load(RESEARCH/'text-review.json');geo=load(RESEARCH/'geographic-evidence.json')
    terrain=load(RESEARCH/'terrain-constraints.json');dimensions=load(RESEARCH/'building-dimensions.json')
    assert len(review['records'])==183,'All prior evidence needs a review row'
    assert geo.get('features'),'No fabricated geographical placeholder permitted'
    info=load(SITE/'build-info.json');ledger=load(SITE/'city-review/ledger.json')['entities']
    assert len(ledger)==339 and info['homepage']['version']=='homepage-v1'
    OUT.mkdir(parents=True,exist_ok=True)
    protected={str(p.relative_to(SITE)):sha(p) for p in SITE.rglob('*') if p.is_file() and str(p.relative_to(SITE)) not in MUTABLE and not is_own(str(p.relative_to(SITE)))}
    plan=literary_plan(SITE/'assets/master-dual-b8-review.svg',ledger)
    geography,gboxes,projection=source_layout(geo['features'])
    panorama,pboxes,panoprojection=source_layout(geo['features'],True)
    core,_,_=source_layout([f for f in geo['features'] if not f['id'].startswith('geo-modern-') and f['id']!='geo-outer-city-related-remains'],detail=True)
    write_svg(OUT/'literary-plan.svg',plan);write_svg(OUT/'source-layout.svg',geography)
    write_svg(OUT/'source-core.svg',core)
    write_svg(OUT/'layout-panorama.svg',panorama);write_svg(OUT/'palace-relations.svg',palace_relations())
    write_svg(OUT/'evidence-summary.svg',research_plate(review,geo))
    entities=entities_data(ledger,review,geo,gboxes,pboxes)
    maps={
      'plan':{'title':'盛时文献平面','url':'./prosperity/literary-plan.svg','viewBox':[0,0,12400,12030],
              'coordinate_system':'documentary_canvas','basis_label':'文献关系 · 非实测比例','source_period':'516—528盛时综合',
              'note':'沿用已有对象与相对关系，逐项核对原文、校注与研究解释。','limitations':['画布间距与建筑图符尺寸不换算为古代距离。','共享组成员没有因被列入地图而取得独立地址。']},
      'geography':{'title':'来源图坐标下的城市分布','url':'./prosperity/source-layout.svg','viewBox':[0,0,1800,1440],
              'coordinate_system':'EPSG:4610 local metric projection','basis_label':'来源图地理框架 · 西安1980坐标','source_period':'2012规划；1997航摄、1999实测底图；古迹分期另核',
              'note':'从原图网格取得城市骨架的位置依据。图示范围和现代地表与盛时解释分别记录。',
              'limitations':['原图内部拟合残差不是地面精度，尚未完成WGS84转换。','来源图上的小建筑和门为放大符号，不能用符号大小当真实占地。','近现代洛水线不代替北魏河道；没有位置证据的对象不补地理点。']},
      'panorama':{'title':'由同一布局生成的鸟瞰','url':'./prosperity/layout-panorama.svg','viewBox':[0,0,1800,1100],
              'coordinate_system':'derived_source_grid_oblique','basis_label':'布局计算斜视 · 非建筑立面复原','source_period':'平面位置依据同城市分布图',
              'note':'平面与鸟瞰逐点对应；可以用相同地点核查城市骨架。',
              'limitations':['抬高线条用于阅读，未推断古代墙高、塔高或建筑立面。','民居密度、未知坊墙和古代地面不由美术效果补出。']}}
    data={'version':VERSION,'source_commit':info['source_commit'],'period':'516—528 年盛时综合','maps':maps,
          'intro':'先读文献中的城市，再沿来源图核查位置。宫苑引文更正与城市骨架在这里使用同一套地点档案。',
          'regions':[{'id':r['code'],'name':r['title'],'bbox':[r['bbox'][0]+200,r['bbox'][1]+640,*r['bbox'][2:]],'entity_ids':r['focus_ids']} for r in load(ROOT/'data/regions.json')],
          'entities':entities,'sources':source_list(review,geo),'source_features':geo['features'],
          'text_review_summary':review['counts'],
          'terrain_constraints':terrain['records'],
          'map_decisions':[{k:(v.replace('small.inline-note','现代夹注层') if isinstance(v,str) else v) for k,v in d.items() if k in ['id','title','finding','visual_instruction','corrected_quote','locator','evidence_keys']} for d in review['map_decisions']],
          'projection':projection,'panorama_projection':panoprojection,
          'downloads':[{'label':'本版图册 PDF','url':'./downloads/prosperity-v1-atlas.pdf','type':'pdf'},
                       {'label':'内城骨架放大 SVG','url':'./prosperity/source-core.svg','type':'svg'},
                       {'label':'地点与定位依据 CSV','url':'./downloads/prosperity-v1-entities.csv','type':'csv'},
                       {'label':'引文核对 JSON','url':'./prosperity/text-review.json','type':'json'},
                       {'label':'地理来源与原图坐标 JSON','url':'./prosperity/geographic-evidence.json','type':'json'},
                       {'label':'历史地形线索 JSON','url':'./prosperity/terrain-constraints.json','type':'json'},
                       {'label':'建筑尺度与建模依据说明','url':'./prosperity/building-dimensions.md','type':'md'},
                       {'label':'建筑尺度依据 JSON','url':'./prosperity/building-dimensions.json','type':'json'},
                       {'label':'完整数据包 ZIP','url':'./downloads/prosperity-v1-package.zip','type':'zip'}]}
    dump(OUT/'data.json',data);dump(OUT/'text-review.json',review);dump(OUT/'geographic-evidence.json',geo)
    dump(OUT/'terrain-constraints.json',terrain);dump(OUT/'building-dimensions.json',dimensions)
    shutil.copyfile(ROOT/'docs/prosperity-building-dimensions.md',OUT/'building-dimensions.md')
    with (SITE/'downloads/prosperity-v1-entities.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['id','name','kind','geographic_status','source_features','placement_note','source_url']);writer.writeheader()
        for e in entities:writer.writerow({k:(';'.join(e['source_feature_ids']) if k=='source_features' else e.get(k,'')) for k in writer.fieldnames})
    render_atlas([OUT/n for n in ['literary-plan.svg','palace-relations.svg','source-layout.svg','source-core.svg','layout-panorama.svg','evidence-summary.svg']],SITE/'downloads/prosperity-v1-atlas.pdf')
    for filename in ['prosperity-v1.css','prosperity-v1.js']:
        dest=fp(filename,(ROOT/'web'/filename).read_bytes())
        if filename.endswith('.css'):css=dest
        else:js=dest
    content=(ROOT/'web/prosperity-v1.html').read_text().replace('./prosperity-v1.css','./'+css).replace('./prosperity-v1.js','./'+js)
    (SITE/'prosperity.html').write_text(content)
    with zipfile.ZipFile(SITE/'downloads/prosperity-v1-package.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.iterdir()):
            if p.is_file() and p.name!='preservation.json':z.write(p,'prosperity/'+p.name)
        z.write(SITE/'downloads/prosperity-v1-entities.csv','entities.csv')
        z.writestr('README.txt','盛时洛阳第一版。文献画布、来源图西安1980坐标和现代地表分别处理。geometry字段为来源坐标JSON，不是RFC7946 WGS84 GeoJSON。详见数据内来源、时层和限制。')
    entry='''<section id="prosperity-entry" style="max-width:1320px;margin:34px auto;padding:28px 5%;background:#e9eee2;border-left:4px solid #497461"><p style="letter-spacing:.12em;color:#6a7357">盛时洛阳 · 从文献走向地理</p><h2 style="font-size:clamp(24px,3vw,38px);margin:12px 0">同一座城，两种空间读法</h2><p>查看原文核对后的平面、来源图中的城市骨架，以及由相同布局生成的鸟瞰。</p><p><a href="./prosperity.html" style="display:inline-block;padding:13px 20px;background:#24493e;color:#fff;text-decoration:none">打开盛时城市复原 →</a></p></section>'''
    for filename in ['index.html','v3.0-dual.html']:
        p=SITE/filename;s=p.read_text();s=re.sub(r'<section id="prosperity-entry".*?</section>','',s,flags=re.S)
        marker='<main id="page-map"'
        if marker in s:s=s.replace(marker,entry+'\n'+marker,1)
        else:
            from homepage_v1 import Elements
            element=Elements(s).one(ident='page-map');s=s[:element['start']]+entry+s[element['start']:]
        s=s.replace('下一研究批次为 B9 引文核对。','当前继续完善盛时平面、历史地形依据与城市分布。')
        p.write_text(s)
    assert all(sha(SITE/p)==v for p,v in protected.items()),'Earlier public asset changed'
    dump(OUT/'preservation.json',{'version':VERSION,'source_commit':info['source_commit'],'protected_unchanged':True,'protected_files':protected,'source_entity_ids_unchanged':True,'legacy_geometry_unchanged':True})
    release=load(SITE/'release.json');release['extensions']=sorted(set(release.get('extensions',[])+[VERSION]));release['prosperity_version']=VERSION;release['current_milestone']='盛时P1：文献审校与来源图城市骨架';dump(SITE/'release.json',release)
    info['prosperity']={'version':VERSION,'source_commit':info['source_commit'],'entities':len(entities),'source_geometries':len(geo['features']),
                        'located_entities':sum(bool(e['source_feature_ids']) for e in entities),'evidence_records':183,'source_crs':'EPSG:4610',
                        'terrain_constraints':len(terrain['records']),'building_dimension_items':len(dimensions['massing_items']),
                        'wgs84_registration_completed':False,'ancient_ground_surface_reconstructed':False,'full_city_reconstruction_completed':False,
                        'atlas_pages':6,'protected_files':len(protected),'metadata':'prosperity/data.json'}
    info['files_sha256']={str(p.relative_to(SITE)):sha(p) for p in sorted(SITE.rglob('*')) if p.is_file() and p.name!='build-info.json'};dump(SITE/'build-info.json',info)
    dump(ROOT/'artifacts/prosperity-build.json',info['prosperity'])
    print('Prosperity:',json.dumps(info['prosperity'],ensure_ascii=False))

if __name__=='__main__':main()
