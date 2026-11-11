#!/usr/bin/env python3
"""Build audited, solver-generated R07 candidates and a lossless registry layer."""
from pathlib import Path
from collections import Counter
import csv,hashlib,html,io,json,math
from qualitative_space import Model,select,minimal_core
from model_v26 import SHORT,EXTRA_NAMES,GROUPS,QUERIES,build_atoms,scenarios
from normalize_v26 import normalize
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'_site';esc=html.escape
STATE={'entailed':'模型内必然','contradicted':'模型内排除','undetermined':'未能限定','inconsistent':'前提不相容'}
CORE=[SHORT[k] for k in ['P','R','Y','J','T','Z','U','L','S','G','O','M','H','I','V','B','K','A','N','W','Q','D']]

def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def dump(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csvfile(path,headers,rows):
 buff=io.StringIO(newline='');w=csv.writer(buff);w.writerow(headers);w.writerows(rows)
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text('\ufeff'+buff.getvalue(),encoding='utf-8')

def candidates(atoms,cases):
 result=[]
 for case in cases:
  if not case['id'].startswith('s') or len(case['id'])!=4:continue
  base=select(atoms,set(case['enabled']),case['excluded_families'])
  focus=SHORT['J'] if case['id'][2:]=='00' and case['id'][1]=='1' else SHORT['T']
  for side in ['west','east']:
   choice={'id':'DISPLAY_CHOICE','kind':'order','axis':'x','less':focus if side=='west' else SHORT['R'],
            'more':SHORT['R'] if side=='west' else focus,'layer':'witness_selection_not_evidence'}
   chosen=Model(base+[choice])
   if not chosen.sat:continue
   # Display-only linear extension puts the palace reference at the top. It is NOT a textual assertion.
   aesthetic=[{'id':'DISPLAY_NORTH_'+str(i),'kind':'order','axis':'y','less':n,'more':SHORT['P'],
               'layer':'display_only'} for i,n in enumerate(CORE) if n not in {SHORT['P'],SHORT['R']}]
   witness_model=Model(base+[choice]+aesthetic)
   if not witness_model.sat:witness_model=chosen;aesthetic=[]
   coords=witness_model.witness(CORE)
   # Nearby display choices satisfy the same theory, but are not new evidence.
   coords['x'][SHORT['P']]=0.0
   coords['y'][SHORT['Y']]=coords['y'][SHORT['T']]-.12
   coords['y'][SHORT['J']]=coords['y'][SHORT['T']]-.18
   coords['y'][SHORT['D']]=coords['y'][SHORT['T']]+.12
   for atom in base+[choice]+aesthetic:
    if atom['kind']=='order' and atom['less'] in CORE and atom['more'] in CORE:
     assert coords[atom['axis']][atom['less']]<coords[atom['axis']][atom['more']],atom['id']
   domains={n:{axis:Model(base).query({'kind':'order','axis':axis,'less':n,'more':SHORT['R'] if axis=='x' else SHORT['P']})['status'] for axis in ['x','y']} for n in CORE}
   result.append({'id':case['id']+'-'+side,'case_id':case['id'],'focus_id':focus,'selected_side':side,
     'path':'assets/models-v26/'+case['id']+'-'+side+'.svg','coordinates':coords,'domains':domains,
     'logical_certificate':{'active_atom_ids':[a['id'] for a in base],'selection':choice,
       'display_only_atom_ids':[a['id'] for a in aesthetic],
       'scope':'代表解非唯一复原；北置门、宫门道轴对中、太尉/永宁/景乐近置和分数微调仅为显示，逐边验证仍满足约束。未使用v2.4坐标。'},
     'metric_range':'unbounded: positive scaling preserves every admitted strict-order constraint'})
 return result

def txt(x,y,s,size=20,fill='#25483e',weight=400):
 return f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{fill}" font-weight="{weight}">{esc(s)}</text>'
def svg_plan(candidate,names,bounds,case):
 xs,ys=bounds;xmin,xmax=xs;ymin,ymax=ys
 def xy(n):return (100+(candidate['coordinates']['x'][n]-xmin)/(xmax-xmin)*1050,
                    250+(ymax-candidate['coordinates']['y'][n])/(ymax-ymin)*1060)
 roadx=100+(0-xmin)/(xmax-xmin)*1050
 s='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1450" role="img">'
 s+=f'<title>{esc(case["title"])}：{esc(names[candidate["focus_id"]])}道{("西" if candidate["selected_side"]=="west" else "东")}可行例</title>'
 s+='<desc>求解器生成的定性平面代表解，不是实测；全图采用相同参照和显示范围。未约束的量仍为未知。</desc>'
 s+='<style>text{font-family:"Noto Sans CJK SC","Microsoft YaHei",sans-serif}</style><rect width="1600" height="1450" fill="#f5f3eb"/>'
 s+=txt(65,62,'北魏洛阳 / R07 可检验空间复原 · v2.6',21,weight=600)
 title=names[candidate['focus_id']]+'：御道'+('西' if candidate['selected_side']=='west' else '东')+'的一种可行平面'
 s+=txt(65,113,title,34,weight=600)+txt(65,155,case['title']+'；其他未列前提见网页条件表。',19,'#62746b')
 s+='<rect x="65" y="200" width="1120" height="1160" rx="12" fill="#fffdf7" stroke="#c9d0c4"/>'
 s+=f'<path d="M{roadx} 230V1325" stroke="#ddd3b9" stroke-width="20"/>'
 s+=txt(roadx+18,230,'御道：方向参照',17,'#887347')
 s+='<path d="M110 310V245l-6 11m6-11l6 11" fill="none" stroke="#496a5c" stroke-width="2"/>'+txt(100,335,'北',19)
 # Context connections are limited to facts; no parcel outlines or temple footprints.
 pointmap={n:xy(n) for n in CORE}
 for a,b in [('Y','T'),('Y','W'),('Y','Z'),('Y','U')]:
  x1,y1=pointmap[SHORT[a]];x2,y2=pointmap[SHORT[b]]
  s+=f'<path d="M{x1:.2f} {y1:.2f}L{x2:.2f} {y2:.2f}" stroke="#c7d8cd" stroke-dasharray="5 5" fill="none"/>'
 placed=[]
 for n in sorted(CORE,key=lambda n:(pointmap[n][1],pointmap[n][0])):
  if n==SHORT['R']:continue
  x,y=pointmap[n];focus=n==candidate['focus_id'];name=names[n]
  if n==SHORT['P']:name='宫前阊阖门（北置仅为显示）'
  knownx=candidate['domains'][n]['x']!='undetermined'; color='#a06927' if focus else '#2c6958' if n in {SHORT['Y'],SHORT['J']} else '#527069'
  s+=f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{9 if focus else 5}" fill="{color if knownx else "#fffdf7"}" stroke="{color}" stroke-width="2"/>'
  w=max(55,len(name)*16+12);h=26
  choices=[(lx,y+dy) for dy in [-12,-42,18,-72,48,-102,78] for lx in [x+12,x-w-12]]
  best=None
  for lx,ly in choices:
   lx=max(80,min(1170-w,lx));ly=max(250,min(1330-h,ly))
   overlap=sum(max(0,min(lx+w,bx+bw)-max(lx,bx))*max(0,min(ly+h,by+bh)-max(ly,by)) for bx,by,bw,bh in placed)
   score=overlap*100+abs(lx-x)+abs(ly-y)
   if best is None or score<best[0]:best=(score,lx,ly)
  _,lx,ly=best;placed.append((lx,ly,w,h))
  s+=f'<path d="M{x:.2f} {y:.2f}L{max(lx,min(x,lx+w)):.2f} {ly+h/2:.2f}" stroke="{color}" stroke-width="0.8"/>'
  s+=f'<rect x="{lx:.2f}" y="{ly:.2f}" width="{w}" height="{h}" rx="4" fill="#fffdf7" fill-opacity=".94"/>'
  s+=txt(lx+6,ly+19,name,16,color,600 if focus else 400)
 s+=txt(1220,245,'读图条件',26,weight=600)
 lines=['点位由定性约束求得','同一坐标框可直接比较','坐标单位不是米或里','点大小不代表建筑占地','门对中、邻处近置为显示','间距与未连边先后不作史实','不绘未经证明的城墙院界','空心点：路侧仍未限定','实体同名对应需另行审查']
 for i,line in enumerate(lines):s+=txt(1220,290+i*38,line,17,'#56695f')
 s+=txt(1220,690,'本例选项',24,weight=600)
 s+=txt(1220,735,names[candidate['focus_id']],21,'#9a6825',600)
 s+=txt(1220,775,'选择道'+('西' if candidate['selected_side']=='west' else '东')+'后，仍可满足',17,'#9a6825')
 s+=txt(1220,805,'全部已启用的模型约束。',17,'#9a6825')
 s+=txt(1220,835,'不等于这个选项已被证明。',17)
 s+=txt(1220,880,'未穷尽连续位置及线上情形。',17)
 s+=txt(1220,925,'尺度可任意正比例变换，',17)+txt(1220,955,'所以不能给出有限米制范围。',17)
 s+=txt(65,1405,'研究基线 v2.4 未移动；本图只展示所列前提下的一个可行解。证据、反例和删源检验见网站 v2.6。',19)
 return s+'</svg>'

def source_review(evidence):
 return {'reviewed_at':'2026-11-11','source_family_policy':'Z/F归为L家族。H为后出汇编，可能转引L；W另组但具体身份和时层仍须假设。不以条数投票。',
  'sources':evidence['sources'],
  'passage_locators':[
   {'id':'L-YONGNING','family':'L','url':'https://deerpark.app/cbeta/B0078/1','anchor':'在宮前閶闔門南一里御道西','scope':'永宁开篇与官署段正文及范校；本轮网页文本复核','manuscript_image_verified':False},
   {'id':'L-JINGLE','family':'L','url':'https://deerpark.app/cbeta/B0077/1','anchor':'御道東。東字各本並脫','scope':'景乐段周校与四邻；本轮网页文本复核','manuscript_image_verified':False},
   {'id':'H-INNER','family':'H','url':'https://zh.wikisource.org/wiki/河南志#後魏城闕古蹟','anchor':'太府寺。〈右衛府南。〉','scope':'官署条至右城内；本轮复核电子转录','manuscript_image_verified':False},
   {'id':'H-OUTER','family':'H','url':'https://zh.wikisource.org/wiki/河南志#後魏城闕古蹟','anchor':'清陽門外有太廟','scope':'门外太庙与西明门外太社；本轮复核电子转录','manuscript_image_verified':False},
   {'id':'W-ROUTE','family':'W','url':'https://www.shidianguji.com/zh/book/SK1022/chapter/1l91zmgs71mor','anchor':'門左枝渠東泒入城','scope':'本轮检索定位对应句；沿用v2.5经注节录，未作完整书影复核。页面全文抓取可能截断，不以此声称新版本校勘。','manuscript_image_verified':False}],
  'fixed_global_assumptions':['将被选的段落投影到同一个研究时相t0，不宣称516—528间任一年全部共存',
    '局部御道作为南北方向参照；只比较x/y顺序，不给道路宽度与城市真实曲线',
    'H与L的同名一般官署在工作案对应，太府及门外庙社另设提及ID；同名对应尚非普遍身份定论',
    '方向投影比邻接、面对、门内外等自然语言弱；未编码的含义不会自动成立']}

def report_page(data):
 qtable='<table><tr><th>检验</th>'+''.join('<th>'+esc(q['title'])+'</th>' for q in QUERIES[:6])+'</tr>'
 for c in data['cases']:
  qtable+='<tr><td>'+esc(c['title'])+'</td>'+''.join('<td>'+STATE[q['status']]+'</td>' for q in c['queries'][:6])+'</tr>'
 qtable+='</table>'
 norms=data['normalization_metrics'];counts=data['atom_counts']
 rows=''.join('<tr><td>'+a['id']+'</td><td>'+esc(a['quote'])+'</td><td>'+esc(a['layer'])+'</td><td>'+esc(a['evidence_id'])+'</td><td>'+esc(a['source_locator'])+'</td><td>'+esc(','.join(a['requires']))+'</td></tr>' for a in data['atoms'])
 paragraphs=[
 ('问题与范围','本研究检验R07的路侧、官署次序与庙社异记。结果属于明列前提下的模型，不是全城实测图。v2.4的339实体和37页底图未被更改。'),
 ('数据复核','482条原关系全部保留。先前按字段称321条为名称关系不够准确：其中85条target值本来就是实体ID。全库共有245条可验证ID引用，另1条target_id=city_jinyang找不到对象，未擅造实体补齐。名称唯一匹配只建立候选链接，不裁定历史身份。'),
 ('模型','只计算严格x/y偏序、显式同体、时相和城界参照，以及城内外布尔归属。方向反转形成环则不可满足；归属矛盾只有在对象、时相、参照都合并后才成立。邻接、实际边界、路径长度、道路宽度及建筑不相交约束均不在模型内。'),
 ('方法可检验性','每条原子记录保留E证据编号、逐句定位、来源组、层次与依赖。依赖来源删去时，相应假设也退出。偏序求解不用旧地图像素、最优拟合、权重或可信度分数。提供可行秩赋值与子集极小冲突集；后者不保证基数最小或列出全部冲突。'),
 ('结果一：太尉路侧','s111按西侧组继承时，太尉在道西是模型结论。s011撤去该继承后，永宁在道西且太尉在寺东仍成立，但太尉道西和道东各有可行例。因此寺东不等于道路东；两例不穷尽连续位置，也不代表等概率；在该弱模型内，点恰在参照线上也没有被自动排除。'),
 ('结果二：景乐补字的依赖','s110不采用景乐〈东〉补字，但保留司徒道东继承时，由御道在司徒西、司徒在景乐西可推出景乐道东。s100同时撤去东侧继承与补字后，路侧未定。这是推导对前提的敏感性，不是新版本独立证实补字。'),
 ('结果三：省略与身份','九级府与司州可在同一南向偏序中插入，无需把文献省略解释为不存在。太府与太尉不合并、试合并两个模型均可满足；方位系统不能单独裁决官名身份。'),
 ('结果四：庙社冲突的条件','在城内条目工作对应成立的前提下，只有把门外/城内对象、时相和城界参照三个层面同时合并，才产生城内/外冲突。分别放松任一合并即可消除此类冲突，但这不证明实际不同体、不同时或不同城界，更不能据此编出迁建过程。'),
 ('稳定性与未定','8种路侧/校补组合下的必然关系可以比较；再做L/H/W组删源。H可能沿用L，不能把删源结果当作独立证据数量或概率。所有数值坐标仅为一个可行显示解；正比例放大不会破坏偏序，因此没有可推的有限米制区间。'),
 ('原文核查边界','本轮复核范本永宁官署段、周本景乐校注、河南志对应正文的电子转录。W沿用上一批节录并重新检索定位，未完成全卷书影逐页核对。18张卡不是18份独立来源。引用转录时保留校者与来源层级。'),
 ('下一研究接口','水系、道路、桥梁可接入同一框架，但不能先画连线再倒推证据。年表需独立事件与构件状态；首次见载不作始建，末次见载不作毁灭。本里程碑未对547年全部建筑编造状态。')]
 body=''.join('<h2>'+esc(h)+'</h2><p>'+esc(p)+'</p>' for h,p in paragraphs)
 body+='<h2>机器计算结果</h2>'+qtable
 body+='<h2>规范化计数</h2><pre>'+esc(json.dumps(norms,ensure_ascii=False,indent=2))+'</pre>'
 body+='<h2>两个可行例：同一约束集 s011</h2>'+''.join('<figure><img src="../'+p['path']+'" alt="定性可行例"><figcaption>'+p['id']+'</figcaption></figure>' for p in data['candidates'] if p['case_id']=='s011')
 body+='<h2>原子判断与前提</h2><table><tr><th>ID</th><th>原句/前提</th><th>层次</th><th>证据卡</th><th>定位</th><th>依赖</th></tr>'+rows+'</table>'
 body+='<h2>电子来源与依赖</h2>'+''.join('<p><a href="'+esc(s['url'],quote=True)+'">'+esc(s['id']+' '+s['title'])+'</a>：'+esc(s['dependency'])+'</p>' for s in data['source_review']['sources'])
 return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>从叙述方位到多解平面 · v2.6</title><style>body{font:16px/1.85 system-ui,sans-serif;max-width:1250px;margin:45px auto;padding:0 20px;color:#25483e}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:10px;border:1px solid #bcc8ba;vertical-align:top}pre{white-space:pre-wrap}img{width:100%}h2{margin-top:40px}figure{margin:20px 0}@media print{tr{break-inside:avoid}figure{break-before:page}}</style></head><body><h1>从叙述方位到多解平面</h1><p>北魏洛阳宫前区域的文献空间约束研究 · v2.6</p>'+body+'</body></html>'

def main():
 if not (OUT/'data/research-v25.json').is_file():raise SystemExit('Build the v2.4 website and v2.5 supplement first')
 info=read('_site/build-info.json');entities=read('data/entities.json');ev=read('_site/data/research-v25.json')
 baseline={p:sha(ROOT/p) for p in ['data/entities.json','data/markers.json','data/regions.json','data/disputes.json','data/sheets.json','assets/master-v24.svg']}
 registry=normalize(entities);atoms=build_atoms(ev);cases=scenarios(atoms);plans=candidates(atoms,cases)
 names={e['id']:e['name'].split('〔')[0].split('（')[0] for e in entities}
 names.update({SHORT[k]:v for k,v in EXTRA_NAMES.items()})
 xx=[v for p in plans for v in p['coordinates']['x'].values()];yy=[v for p in plans for v in p['coordinates']['y'].values()]
 bounds=((min(xx)-.8,max(xx)+.8),(min(yy)-.5,max(yy)+.4));cm={c['id']:c for c in cases}
 for p in plans:
  path=OUT/p['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_text(svg_plan(p,names,bounds,cm[p['case_id']]),encoding='utf-8')
 # Stable only across the explicitly enumerated interpretation profiles, not all imaginable history.
 interpretation_cases=[c for c in cases if c['id'].startswith('s') and len(c['id'])==4]
 stable=[q['id'] for q in QUERIES if all(next(x for x in c['queries'] if x['id']==q['id'])['status']=='entailed' for c in interpretation_cases)]
 data={'version':'v2.6-r07','base_commit':'c801c47a18a866bf13a64513ef29c6015e9055d8','geometry_baseline':'v2.4',
   'title':'从叙述方位到多解平面','names':names,'groups':GROUPS,'atoms':atoms,'cases':cases,'candidates':plans,
   'normalization_metrics':registry['metrics'],'atom_counts':dict(Counter(a['layer'] for a in atoms)),
   'stable_queries_across_eight_profiles':stable,'source_review':source_review(ev),
   'model_scope':'严格方向偏序＋同体/时相/参照合并＋城内外。无距离、建筑范围、不相交或真实街道几何。',
   'all_numeric_ranges':'unbounded_without_metric_evidence','common_plot_bounds':bounds,'baseline_sha256':baseline}
 dump(OUT/'data/milestone-v26.json',data);dump(OUT/'data/relations-v26.json',registry)
 csvfile(OUT/'downloads/relations-v26.csv',['ID','主体','原关系','目标原值','解析状态','候选ID','依据','原始JSON'],
  [[r['id'],r['subject_id'],r['relation_raw'],r['target']['raw'],r['target']['status'],'|'.join(r['target']['candidates']),r['source']['locator'],json.dumps(r['original'],ensure_ascii=False)] for r in registry['records']])
 csvfile(OUT/'downloads/atoms-v26.csv',['ID','证据卡','层次','种类','关系原句/前提','来源家族','假设组','依赖','定位'],
  [[a['id'],a['evidence_id'],a['layer'],a['kind'],a['quote'],'|'.join(a['families']),a['group'],'|'.join(a['requires']),a['source_locator']] for a in atoms])
 csvfile(OUT/'downloads/sensitivity-v26.csv',['方案','查询','结果','充分支持集（含依赖）'],
  [[c['id'],q['title'],q['status'],'|'.join(q['support_subset'])] for c in cases for q in c['queries']])
 (OUT/'downloads/r07-study-v26.html').write_text(report_page(data),encoding='utf-8')
 for f in ['models-v26.js','models-v26.css']:(OUT/f).write_bytes((ROOT/f).read_bytes())
 app=(OUT/'app.js').read_text(encoding='utf-8')
 app=app.replace("window.addEventListener('hashchange',route)","window.addEventListener('hashchange',()=>route())")
 (OUT/'app.js').write_text(app,encoding='utf-8')
 index=(OUT/'index.html').read_text(encoding='utf-8')
 if 'models-v26.js' in index:raise ValueError('Fresh v2.5 build required; refusing duplicate injection')
 index=index.replace('</head>','<link rel="stylesheet" href="./models-v26.css"><script defer src="./models-v26.js"></script></head>')
 index=index.replace('<a href="#research"','<a href="#model" data-nav="model">空间检验 v2.6</a>\n<a href="#research"',1)
 index=index.replace('<main id="page-about"','<main id="page-model" class="page page-article" hidden><div id="model-content">空间检验载入中…</div></main>\n<main id="page-about"')
 index=index.replace('地理基线 v2.4 · 宫前专题 v2.5','地理基线 v2.4 · 空间检验 v2.6')
 (OUT/'index.html').write_text(index,encoding='utf-8')
 for p,digest in baseline.items():assert sha(OUT/p)==digest,'Changed baseline '+p
 info.update({'research_version':'v2.4 + R07-v2.5 + v2.6-models','web_version':'0.3.0','milestone_version':'v2.6-r07',
  'milestone_counts':{'relations':len(registry['records']),'atoms':len(atoms),'cases':len(cases),'candidates':len(plans)},'baseline_sha256':baseline})
 info['files_sha256']={str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='build-info.json'}
 dump(OUT/'build-info.json',info)
 dump(ROOT/'artifacts/v26-calculation.json',{'metrics':registry['metrics'],'counts':info['milestone_counts'],
   'case_satisfiability':{c['id']:c['sat'] for c in cases},'baseline_unchanged':True,'stable_queries':stable})
 print('v2.6 BUILD',info['milestone_counts'],'baseline hashes unchanged; numerical ranges remain unbounded')

if __name__=='__main__':main()
