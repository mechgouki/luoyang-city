#!/usr/bin/env python3
"""Build the R07 evidence supplement without modifying the v2.4 source atlas."""
from pathlib import Path
import csv, hashlib, html, io, json, os, re
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '_site'
ESC = html.escape

def read(p): return json.loads((ROOT / p).read_text(encoding='utf-8'))
def dump(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def text(x,y,s,size=22,color='#203f39'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{ESC(s)}</text>'
def box(x,y,w,h,name,note='',color='#376e60'):
    a=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="#fffdf8" stroke="{color}" stroke-width="2"/>'
    a+=text(x+14,y+31,name,23,color)
    if note: a+=text(x+14,y+59,note,17,'#65716c')
    return a

def sheet(title,subtitle,body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1500 1100" role="img">'
      f'<title>{ESC(title)}</title><desc>{ESC(subtitle)}；无比例尺，框为关系节点，不是院墙。</desc>'
      '<style>text{font-family:"Noto Sans CJK SC","Microsoft YaHei",sans-serif}</style>'
      '<rect width="1500" height="1100" fill="#f7f5ef"/>'
      +text(55,60,'北魏洛阳 / R07 文献研究 v2.5',18,'#68766c')
      +text(55,110,title,34)+text(55,150,subtitle,20,'#68766c')+body
      +'<path d="M55 1015H1445" stroke="#b5c0b4"/>'
      +text(55,1050,'无地理比例尺 · 箭头只表示文献关系 · 不推定等距、紧邻、院界或同时存在',18)
      +text(55,1080,'来源和校读按 E 编号回查网页证据表；v2.4 地理母图保持原样。',17,'#68766c')+'</svg>')

def chain(x,y,items,notes,w=390,step=100):
    s=''
    for i,n in enumerate(items):
        yy=y+i*step;s+=box(x,yy,w,70,n,notes[i])
        if i<len(items)-1:
            s+=f'<path d="M{x+w/2} {yy+73}v20l-5 -6m5 6l5 -6" fill="none" stroke="#8b806b" stroke-width="2"/>'
    return s

def drawings():
    a=text(90,205,'御道西组（后项路侧为段落归组）',23)+text(835,205,'御道东组（后项路侧为段落归组）',23)
    a+=chain(90,235,['右卫府','太尉府 †','将作曹','九级府','太社 †','凌阴里'],['道西明文 / E05','右卫南；太府异记 / E06–08','太尉南 / E05','将作南；功能未详 / E08','九级南；门外异记 / E12','太社南；H另列司州 / E18'])
    a+=chain(835,235,['左卫府','司徒府','国子学','宗正寺','太庙 †','护军府','衣冠里'],['道东明文 / E03','左卫南 / E03','司徒南；断句差异 / E04','学校南；官署非佛寺 / E04','宗正南；门外异记 / E11','太庙南 / E04','护军南 / E04'],step=100)
    a+='<path d="M680 225V935" stroke="#c6b899" stroke-width="12"/>'
    a+=text(600,965,'↑ 北　御道示意　南 ↓',18)
    a+=text(90,900,'H =《河南志》；左右栏同高不表示相互正对。',18)
    a+=text(90,932,'“南有”允许中间另有设施，不能画成等大连续院落。',18)
    b=text(65,215,'官名与序列：两种文本分别读',24)
    b+=box(65,240,650,85,'《伽蓝记》工作链 / E05','右卫 → 太尉 → 将作 → 九级 → 太社 → 凌阴')
    b+=box(755,240,680,85,'《河南志》另一链 / E06','右卫 → 太府 → 将作 → 太社 → 司州 → 凌阴','#8b6242')
    b+=text(65,360,'范主张“太府”为误；本图记录该校断，但不合并官署身份（E07）。',22)
    b+=text(65,400,'九级与司州可以在宽泛南向次序中共存：这是相容性推理，不是新发现的平面（E18）。',20)
    b+='<path d="M65 440H1435" stroke="#bec8bd"/>'
    b+=text(65,490,'城内主案：有条件采用',26)+text(800,490,'门外异记：独立保存',26,'#8b6242')
    b+=box(65,520,660,110,'H 的宫前列表，末署“右城内” / E09','包含宗正南太庙、将作南太社；属于后出地志分类。')
    b+=box(65,655,660,110,'W：支渠入城后流经庙社 / E10','入城 → 太社前 → 太庙南 → 清阳门右 → 阳渠')
    b+=box(800,520,635,110,'太庙：清阳门外 / E11','无门距、院形；同名是否同体、同时均待证。','#8b6242')
    b+=box(800,655,635,110,'太社：西明门外一里 / E12','御道北属下句王宅，不转给太社。','#8b6242')
    b+=text(65,830,'不作迁建断言　/　不新增两座同期庙社　/　不把门外记载平均到城墙上',23)
    b+=text(65,880,'两栏是证据对照，不是两幅同尺度城市地图；水道只表达流经顺序。',21)
    b+=text(65,930,'F、Z同出《伽蓝记》；H有汇编依赖；W含多时层。引用数量不等于独立证据数量。',20)
    c=text(65,210,'永宁寺四邻 / E01–02',25)
    c+=box(65,465,240,80,'永康里','寺西相对')+box(370,465,250,80,'永宁寺','御道西；门南一里')+box(690,465,240,80,'太尉府 †','寺东；路侧另论')
    c+=box(370,315,250,80,'御史台','寺北相邻')+box(370,615,250,80,'昭玄曹','寺南界')
    for d in ['M305 505H370','M620 505H690','M495 395V465','M495 545V615']:
        c+=f'<path d="{d}" stroke="#7b8d82" stroke-width="2" stroke-dasharray="7 5"/>'
    c+=text(65,750,'H另以太尉府为两署参照 / E16；不必互斥，也不能推出院墙宽度。',20)
    c+=text(1000,210,'景乐寺校补 / E13–15',25)
    c+=box(1010,270,400,100,'景乐寺 †：御道〈东〉','“东”为补字；不当作传本原字。')
    c+=box(1010,405,400,100,'西望永宁，正相当','只保存相望；间距与中轴未知。')
    c+=box(1010,540,400,130,'寺西司徒 · 东高肇宅','北连义井里；周校据邻接支持补东。')
    c+=text(65,825,'水经旁证 / E15',24)
    c+=box(65,850,1350,105,'渠水夹路过太尉、司徒两坊间；水西有永宁','这是路水与官署的关系旁证，不能单独解决太尉／太府身份，亦不提供渠线精确几何。')
    return {'R07-A':sheet('宫前官署：先读南北关系','工作方案A /《伽蓝记》序列；节点排版非实测',a),
            'R07-B':sheet('太尉／太府与庙社：把异记放在一起','比较方案B / 不择定同体、同时或迁建过程',b),
            'R07-C':sheet('永宁—景乐：从四邻到校补','关系方案C / 正文、补字和旁证分开',c)}

def main():
    if not (OUT/'build-info.json').is_file(): raise SystemExit('Run tools/build_site.py first')
    original_info=read('_site/build-info.json')
    r=read('research/v2.5/evidence.json');entities=read('data/entities.json');issues=read('data/disputes.json');sheets=read('data/sheets.json')
    ids={e['id'] for e in entities}; issue_ids={d['id'] for d in issues}
    for e in r['evidence']:
        assert set(e['entities'])<=ids, e['id'];assert set(e['issues'])<=issue_ids,e['id']
        assert all(k in e for k in ('quote','locator','interpretation','constraint','drawing'))
    assert len({e['id'] for e in r['evidence']})==len(r['evidence'])
    status_names={'open':'尚待研究','conditional':'有条件采用','clarified':'逻辑／指代已澄清','unlocated':'证据不足暂不定位'}
    conditional={'C02','C04','C05','C07','C09','C14','C19','C23'}
    unlocated={'C12','C13','C15','C16','C20','C25','C29'}
    statuses=[]
    for d in issues:
        i=d['id'];state='clarified' if i in {'C03','C10'} else 'conditional' if i in conditional else 'unlocated' if i in unlocated else 'open'
        refs=['R07','S01','E01'] if i in {'C01','C02','C03','C04','C07','C10'} else []
        statuses.append({'id':i,'status':state,'label':status_names[state],
          'review_scope':'v2.5复核' if i in {'C01','C02','C03','C04','C07'} else '依据既有记录整理状态，非本轮重新考定',
          'note':'已澄清的是关系逻辑／参照身份，不代表全部古址已定。' if state=='clarified' else '状态描述本项目绘图处理，不代表学界定论。',
          'current_sheets':[{'atlas_version':'v2.4','code':c,'page':next(s['page'] for s in sheets if s['code']==c)} for c in refs],
          'legacy_refs':[{'atlas_version':'v1.1','plate':d['audit_plate'],'available':False,'note':'旧专题页未随本次发布；不链接到当前图册同号页。'}] if d.get('audit_plate') else []})
    r['status_registry']=statuses
    r['panels']=[{'id':k,'title':v,'path':f'assets/research/{k}.svg'} for k,v in [('R07-A','官署两链'),('R07-B','身份与庙社异记'),('R07-C','永宁与景乐')]]
    dump(OUT/'data/research-v25.json',r)
    for code,svg in drawings().items():
        p=OUT/f'assets/research/{code}.svg';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(svg,encoding='utf-8')
    for name in ('research.js','research.css'):(OUT/name).write_bytes((ROOT/name).read_bytes())
    index=(OUT/'index.html').read_text(encoding='utf-8')
    index=index.replace('</head>','<link rel="stylesheet" href="./research.css"><script defer src="./research.js"></script></head>')
    index=index.replace('<a href="#issues"','<a href="#research" data-nav="research">宫前专题 v2.5</a>\n      <a href="#issues"',1)
    index=index.replace('<main id="page-about"','<main id="page-research" class="page page-article" hidden><div id="research-content" aria-live="polite">专题载入中…</div></main>\n  <main id="page-about"')
    index=index.replace('公开研究预览 · v2.4','地理基线 v2.4 · 宫前专题 v2.5')
    index=index.replace('待研究争议</small>','研究问题档案</small>')
    (OUT/'index.html').write_text(index,encoding='utf-8')
    buff=io.StringIO(newline='');w=csv.writer(buff);w.writerow(['编号','原文','来源','定位段落','层次','空间约束','校读/推理','图形处理'])
    for e in r['evidence']: w.writerow([e['id'],e['quote'],'/'.join(e['sources']),e['locator'],e['kind'],e['constraint'],e['interpretation'],e['drawing']])
    (OUT/'downloads/r07-evidence-v25.csv').write_text('\ufeff'+buff.getvalue(),encoding='utf-8')
    rows=''.join('<tr>'+''.join('<td>'+ESC(str(v))+'</td>' for v in [e['id'],e['quote'],e['locator'],e['kind'],e['constraint'],e['interpretation'],e['drawing']])+'</tr>' for e in r['evidence'])
    report='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>R07 v2.5 证据报告</title><style>body{font:16px/1.7 sans-serif;max-width:1400px;margin:40px auto;padding:20px}td,th{border:1px solid #ccc;padding:12px;vertical-align:top}table{border-collapse:collapse}img{width:100%} @media print{img{break-after:page}tr{break-inside:avoid}}</style><h1>R07 宫前专题 v2.5</h1><p>'+ESC(r['scope'])+'</p>'
    report+=''.join(f'<h2>{ESC(p["title"])}</h2><img src="../{p["path"]}" alt="{p["title"]}">' for p in r['panels'])
    report+='<h2>逐条证据</h2><table><tr><th>编号</th><th>原文</th><th>出处</th><th>层次</th><th>约束</th><th>解释</th><th>图形</th></tr>'+rows+'</table><h2>来源及依赖</h2>'
    report+=''.join(f'<p><a href="{ESC(s["url"],quote=True)}">{ESC(s["id"]+" · "+s["title"])}</a><br>{ESC(s["dependency"])}</p>' for s in r['sources'])
    report+='</html>';(OUT/'downloads/r07-report-v25.html').write_text(report,encoding='utf-8')
    info=original_info.copy();info.update({'research_version':'v2.4 + R07-v2.5','web_version':'0.2.0','supplement_version':'v2.5-r07','evidence_count':len(r['evidence']),'baseline_geometry_unchanged':True})
    baseline={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['data/entities.json','data/markers.json','data/regions.json','data/disputes.json','data/sheets.json','assets/master-v24.svg']}
    for p,h in baseline.items(): assert hashlib.sha256((OUT/p).read_bytes()).hexdigest()==h,p
    info['files_sha256']={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='build-info.json'}
    info['baseline_sha256']=baseline
    dump(OUT/'build-info.json',info)
    print(f'R07 v2.5: {len(r["evidence"])} evidence records; 3 diagrams; 30 status records; baseline hashes unchanged')

if __name__=='__main__': main()
