#!/usr/bin/env python3
"""First-batch temporal dossiers; preserve baseline geometry and former releases."""
from pathlib import Path
import csv, hashlib, html, io, json, re, shutil, xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'_site'
NS='http://www.w3.org/2000/svg';ET.register_namespace('',NS)
LABELS={'before':'明确在目标年以前','at':'原文纪年落在目标年','later':'明确晚于目标年','overlap':'区间包含目标年，具体时点不定','alternatives':'纪年异记跨越目标年，不能归一','lower_bound':'只有下限，不能判定是否已在目标年前发生','unanchored':'叙述现在未独立定年','undated':'未提供可用确年'}
def digest(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def relation_to(date,year):
    """Temporal location of a record, NOT persistence of its consequence."""
    k=date['kind']
    if k=='year':return 'before' if date['year']<year else 'at' if date['year']==year else 'later'
    if k=='interval':return 'before' if date['end']<year else 'later' if date['start']>year else 'overlap'
    if k=='alternatives':
        values={relation_to({'kind':'year','year':y},year) for y in date['years']}
        return values.pop() if len(values)==1 else 'alternatives'
    if k=='after':return 'later' if date['lower']>year else 'lower_bound'
    if k=='narrator_now':return 'unanchored'
    if k=='undated':return 'undated'
    raise ValueError('Unknown date kind '+k)
def fingerprint(path,body):
    name='_assets/'+digest(body)[:20]+'-'+Path(path).name
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body);return name

def main():
    info=load(OUT/'build-info.json');assert info['portal_version']=='v2.8','Build v2.8 first'
    preserved={str(p.relative_to(OUT)):digest(p.read_bytes()) for p in (OUT/'data').glob('*.json')}
    preserved.update({p:digest((OUT/p).read_bytes()) for p in ['assets/master-v24.svg','assets/master-v28-review.svg','downloads/luoyang-v24-regional-atlas.pdf','v2.8.html']})
    data=load(ROOT/'research/v2.9/dossiers.json');entities=load(OUT/'data/entities.json');markers=load(OUT/'data/markers.json')
    ids={e['id'] for e in entities};dmap={d['id']:d for d in data['dossiers']}
    assert len(dmap)==12 and len({r['id'] for r in data['records']})==25
    for r in data['records']:
        assert r['site_id'] in ids and r['subject_id'] in ids
        assert r['dossier_id'] in dmap and r['state_valid_from'] is None and r['state_valid_to'] is None
        r['target_relations']={str(y):relation_to(r['date'],y) for y in [528,531,532,533,534,546,547]}
    tree=ET.parse(OUT/'assets/master-v24.svg');root=tree.getroot()
    original_group=next(g for g in root if g.tag==f'{{{NS}}}g' and g.get('transform'))
    transform=original_group.get('transform');nums=re.findall(r'-?\d+(?:\.\d+)?',transform);assert transform.startswith('translate(') and len(nums)==2
    tx,ty=map(float,nums)
    for d in data['dossiers']:
        usable=[m for m in markers if d['site_id'] in m['ids'] and m['kind']!='group']
        d['anchor']=dict(x=usable[0]['x']+tx,y=usable[0]['y']+ty,kind=usable[0]['kind'],basis='沿用v2.4原图符，非实测坐标') if usable else None
        d['record_ids']=[r['id'] for r in data['records'] if r['dossier_id']==d['id']]
        d['status_at_547']='unknown'
    data['labels']=LABELS
    data['coverage']=[{'entity_id':e['id'],'dossier_id':next((d['id'] for d in data['dossiers'] if e['id']==d['site_id']),None),'review_state':'first_batch_scoped_review' if any(d['site_id']==e['id'] for d in data['dossiers']) else 'not_reviewed_in_v29'} for e in entities]
    data['metrics']={'dossiers':12,'records':25,'anchors':sum(d['anchor'] is not None for d in data['dossiers']),'entity_ledger':len(entities),'unreviewed_in_this_batch':len(entities)-12}
    save(OUT/'data/chronology-v29.json',data)
    # Low contrast denotes geographic context, not survival or destruction.
    svg=ET.Element(f'{{{NS}}}svg',{'viewBox':'0 0 12400 12030','role':'img','aria-label':'同址时层对照的共同示意底图，不代表某年完整现状'})
    ET.SubElement(svg,f'{{{NS}}}rect',{'width':'12400','height':'12030','fill':'#faf9f4'})
    defs=root.find(f'{{{NS}}}defs')
    if defs is not None:svg.append(defs)
    wrapper=ET.SubElement(svg,f'{{{NS}}}g',{'opacity':'.25','id':'chrono-context'});wrapper.append(original_group)
    layer=ET.SubElement(svg,f'{{{NS}}}g',{'id':'chrono-anchors'})
    for d in data['dossiers']:
        if not d['anchor']:continue
        x,y=d['anchor']['x'],d['anchor']['y']
        g=ET.SubElement(layer,f'{{{NS}}}g',{'class':'chrono-anchor','data-dossier':d['id'],'tabindex':'0','role':'button','aria-label':d['title']})
        ET.SubElement(g,f'{{{NS}}}title').text=d['title']+'；位置为原示意锚点，颜色不表示存废。'
        ET.SubElement(g,f'{{{NS}}}circle',{'cx':str(x),'cy':str(y),'r':'135','fill':'#fffdf7','stroke':'#496f62','stroke-width':'15'})
        ET.SubElement(g,f'{{{NS}}}text',{'x':str(x),'y':str(y+25),'text-anchor':'middle','font-family':'sans-serif','font-size':'74','fill':'#31594d'}).text=d['id'].rsplit('-',1)[-1]
    (OUT/'assets/chronology-v29.svg').write_text(ET.tostring(svg,encoding='unicode'),encoding='utf-8')
    buf=io.StringIO(newline='');w=csv.writer(buf);w.writerow(['记录','地点档案','作用对象','性质','日期类型','原纪年','短引','出处','限制'])
    for r in data['records']:w.writerow([r['id'],dmap[r['dossier_id']]['title'],r['scope'],r['kind'],r['date']['kind'],r['date']['label'],r['quote'],r['source_id']+' / '+r['locator'],r['interpretation_limit']])
    (OUT/'downloads/chronology-v29.csv').write_text('\ufeff'+buf.getvalue(),encoding='utf-8')
    E=html.escape;sources={s['id']:s for s in data['sources']}
    report='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>同址时层对照 v2.9</title><style>body{max-width:1100px;margin:32px auto;padding:20px;font:17px/1.8 sans-serif;color:#26483d}article{border:1px solid #bcc9be;padding:22px;margin:24px 0}blockquote{margin:16px 0;padding:14px;background:#f3f4ea}small{color:#627067}h2{break-after:avoid}@media print{article{break-inside:avoid}}</style><h1>同址时层对照 v2.9：首批12处</h1><p>'+E(data['scope'])+'</p><p>坐标仍是v2.4示意位置。该年之前发生变化，不等于该年现状已证。首批12处的547年完整存废均不据现有片段武断填写。</p>'
    for d in data['dossiers']:
        report+=f'<section><h2>{E(d["id"]+" · "+d["title"])}</h2><p><b>早期：</b>{E(d["early_reading"])}</p><p><b>变化：</b>{E(d["change_reading"])}</p><p>{E(d["status_note"])}</p>'
        for r in data['records']:
            if r['dossier_id']!=d['id']:continue
            source=sources[r['source_id']]
            report+=f'<article id="{r["id"]}"><h3>{E(r["id"]+" · "+r["title"])}</h3><p>{E(r["date"]["label"])} · {E(r["scope"])}</p><blockquote>{E(r["quote"])}</blockquote><p>{E(r["interpretation_limit"])}</p><small><a href="{source["url"]}">{E(source["title"])}</a> / {E(r["locator"])}</small></article>'
        report+='</section>'
    report+='<h2>方法与覆盖边界</h2>'+''.join('<p>'+E(v)+'</p>' for v in data['policy'].values())+'<p>339对象账本中12处完成本批片段核查，327处未进入本批；不是对所有对象的年代考证已经完成。</p></html>'
    (OUT/'downloads/chronology-study-v29.html').write_text(report,encoding='utf-8')
    for path in ('chronology-v29.js','chronology-v29.css'):shutil.copyfile(ROOT/path,OUT/path)
    index=(OUT/'index.html').read_text(encoding='utf-8')
    runtime_match=re.search(r'<script src="\./([^\"]+-runtime\.js)"></script>',index);assert runtime_match
    oldboot=(OUT/runtime_match.group(1)).read_text(encoding='utf-8')
    mapping=json.loads(re.search(r'window\.ATLAS_ASSETS=(.*?);\n',oldboot).group(1))
    release=dict(load(OUT/'release.json'),release='v2.9',web_version='0.6.0',entrypoint='v2.9.html',description='首批12处同址时层对照；事件记录不等于547年逐址存废',research_modules=['v2.5','v2.6','v2.7','v2.9'])
    save(OUT/'release.json',release)
    for path in ('data/chronology-v29.json','assets/chronology-v29.svg'):mapping[path]=fingerprint(path,(OUT/path).read_bytes())
    boot=re.sub(r'window\.ATLAS_RELEASE=.*?;\n','window.ATLAS_RELEASE='+json.dumps(release,ensure_ascii=False)+';\n',oldboot,count=1)
    boot=re.sub(r'window\.ATLAS_ASSETS=.*?;\n','window.ATLAS_ASSETS='+json.dumps(mapping)+';\n',boot,count=1)
    index=index.replace(runtime_match.group(1),fingerprint('runtime.js',boot.encode()),1)
    index=index.replace('<span class="brand-release">v2.8</span>','<span class="brand-release">v2.9</span>')
    index=index.replace('当前公开版本 · v2.8 / 研究整合地图','当前公开版本 · v2.9 / 同址时层对照')
    index=index.replace('当前整合版 v2.8 · 原始几何底图 v2.4','当前整合版 v2.9 · 原始几何底图 v2.4')
    index=index.replace('本次具体更新了什么？为什么仍能看到“底图 v2.4”？','底图与v2.8叠层的保留说明（当前主入口已为v2.9）')
    index=index.replace('<title>北魏洛阳 · 研究整合地图 v2.8</title>','<title>北魏洛阳 · 同址时层对照 v2.9</title>')
    index=index.replace('<nav aria-label="主导航" class="topnav">','<nav aria-label="主导航" class="topnav"><a href="#compare" data-nav="compare">时层对照 v2.9</a>',1)
    index=index.replace('<main id="page-about"','<main id="page-compare" class="page page-article" hidden><div id="chronology-content" aria-live="polite">同址档案载入中…</div></main>\n<main id="page-about"',1)
    notice='<section class="c29-entry"><strong>新增：盛时—末期，同一地点怎样变化？</strong><span>12处档案 · 25条记录 · 相同地图参照 · 不把未知画成废墟</span><a href="#compare?site=D29-01&year=547">打开同址对照 ↗</a></section>'
    index=index.replace('<div class="v28-summary">',notice+'<div class="v28-summary">',1)
    js=fingerprint('chronology-v29.js',(ROOT/'chronology-v29.js').read_bytes());css=fingerprint('chronology-v29.css',(ROOT/'chronology-v29.css').read_bytes())
    index=index.replace('</head>',f'<link rel="stylesheet" href="./{css}"><script defer src="./{js}"></script></head>')
    (OUT/'index.html').write_text(index,encoding='utf-8');(OUT/'v2.9.html').write_text(index,encoding='utf-8')
    info.update({'portal_version':'v2.9','chronology_version':'v2.9','web_version':'0.6.0','chronology_counts':data['metrics'],'research_version':'v2.4 geometry + v2.5–v2.7 research + v2.9 temporal dossiers'})
    for path,sha in preserved.items():assert digest((OUT/path).read_bytes())==sha,path
    info['files_sha256']={str(p.relative_to(OUT)):digest(p.read_bytes()) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='build-info.json'}
    save(OUT/'build-info.json',info)
    print('v2.9:',data['metrics'],'; previous data, baseline geometry and v2.8 archive unchanged')
if __name__=='__main__':main()
