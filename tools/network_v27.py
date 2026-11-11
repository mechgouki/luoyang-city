#!/usr/bin/env python3
"""Typed textual networks and scoped events. No map coordinates or persistence."""
from pathlib import Path
from collections import deque, Counter
from itertools import product
import csv,hashlib,html,io,json,zipfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'_site'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write_json(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def network():
 nodes={};edges=[]
 def node(i,name,kind='water',maps=()):nodes[i]={'id':i,'name':name,'kind':kind,'map_ids':list(maps),'geometry':None}
 def edge(i,a,b,kind,ev,family,condition=None,scope=None):
  edges.append({'id':i,'a':a,'b':b,'kind':kind,'evidence':[ev],'families':family.split('+'),
   'requires':[condition] if condition else [],'route_scope':scope,'time_scope':'passage_specific_not_synchronized',
   'meaning':'仅为文字关系；不证明尺度、全年通行或永久状态。'})
 def chain(prefix,seq,ev,fam,kind='flow',scope=None):
  for n,(a,b) in enumerate(zip(seq,seq[1:]),1):edge(prefix+str(n),a,b,kind,ev,fam,scope=scope)
 for i,name,maps in [
  ('L_jian','L·建春外谷水段',['bridge_jianchun','gushui']),('L_yang','L·建春外阳渠段',['water_yangqu']),
  ('W_north','W·广莫门北水段',[]),('W_jian','W·建春石桥下水段',['bridge_jianchun']),
  ('W_yang_east','W·东出阳渠段',['water_yangqu']),('W_mashi','W·马市桥所经水段',[]),
  ('W_upper','W·城西入城上渠',[]),('W_wangxian','W·望先寺所经水段',[]),
  ('W_qianqiu','W·千秋附近分流段',['ic_qianqiu_gate']),('W_pool','W·灵芝九龙池',[]),
  ('W_palace','W·宫阊阖门南水段',['ic_changhe_palace']),('W_tongtuo','W·铜驼夹路渠群',['ic_palace_avenue']),
  ('W_ritual','W·庙社之间水段',['ic_taimiao','ic_taishe']),('W_nanqu','W·南渠（未合并）',[]),
  ('W_sima','W·司马门南水段',[]),('W_taicang','W·司空前太仓南段',[]),
  ('W_dongbridge','W·东阳门桥下水段',[]),('W_yang_dong','W·东阳出口阳渠',[]),
  ('W_ximing','W·西明门外谷水段',['gate_ximing']),('W_inner','W·西明分入支渠',['gate_ximing']),
  ('W_she','W·太社前水段',['ic_taishe']),('W_miao','W·太庙南水段',['ic_taimiao']),
  ('W_qing','W·靑陽门右水段',[]),('W_yang_qing','W·靑陽出口阳渠',[]),
  ('W_jinyang','W·津阳门南水段',[]),('W_xuanyang','W·宣阳门南水段',['gate_xuanyang']),
  ('W_lingtai','W·灵台北水段',['v3_lingtai']),('W_mingtang','W·明堂北水段',['v3_mingtang']),
  ('W_kaiyang','W·开阳门南水段',[]),('L_changfen','L·长分桥相关谷水',['w_changfenqiao','gushui']),
  ('L_luowest','L·分流所入洛水',['luoshui']),('L_luoyong','L·永桥所跨洛水',['luoshui'])]:node(i,name,maps=maps)
 for i,name,maps in [
  ('L_bridge_jian','L·建春门石桥',['bridge_jianchun']),('W_bridge_jian','W·建春门石桥',['bridge_jianchun']),
  ('L_bridge_east','L·东石桥',['bridge_eaststone']),('W_bridge_mashi','W·马市石桥',[]),
  ('L_yong','L·永桥',['bridge_yong']),('W_fuhang','W·洛水浮桁提及',[])]:node(i,name,'bridge',maps)
 for i,name,maps in [
  ('L_jian_gate','L·建春门',['gate_jianchun']),('L_eastroad','L·东桥北大道',['road_eaststone_north']),
  ('L_xuanyang','L·宣阳门',['gate_xuanyang']),('L_northbank','L·洛北岸',[]),
  ('L_southbank','L·洛南岸',[]),('L_siyi','L·桥南御道',['road_siyi']),
  ('L_jingming','L·景明寺集像',['v3_jingming']),('L_palgate','L·宫前受散花',['ic_changhe_palace']),
  ('W_gate_xuanyang','W·宣阳门提及',[]),('W_gate_palace','W·宫阊阖门提及',[])]:node(i,name,'route',maps)
 chain('LF',['L_jian','L_yang'],'N01','L')
 chain('WF',['W_north','W_jian','W_yang_east','W_mashi'],'N04','W')
 chain('WU',['W_upper','W_wangxian','W_qianqiu'],'N05','W')
 edge('WP','W_qianqiu','W_pool','flow','N05','W')
 chain('WC',['W_qianqiu','W_palace','W_tongtuo'],'N06','W')
 chain('WR',['W_tongtuo','W_ritual','W_nanqu'],'N07','W')
 chain('WI',['W_ximing','W_inner','W_she','W_miao','W_qing','W_yang_qing'],'N08','W')
 chain('WE',['W_tongtuo','W_sima','W_taicang','W_dongbridge','W_yang_dong'],'N09','W')
 chain('WS',['W_ximing','W_jinyang','W_xuanyang','W_lingtai','W_mingtang','W_kaiyang'],'N10','W')
 edge('OVERFLOW','L_changfen','L_luowest','overflow','N11','L','FLOOD')
 chain('RE',['L_jian_gate','L_bridge_east','L_eastroad'],'N02','L','route','east_bridge')
 chain('RY',['L_xuanyang','L_northbank','L_yong','L_southbank','L_siyi'],'N12','L','route','yong_approach')
 chain('RC',['L_jingming','L_xuanyang','L_palgate'],'N14','L','route','procession')
 edge('CJ','W_bridge_jian','W_jian','crossing','N04','W')
 edge('CM','W_bridge_mashi','W_mashi','crossing','N04','W')
 edge('CY','L_yong','L_luoyong','crossing','N12','L')
 # W mentions remain independent from L named objects. Directional alignment
 # is not a river edge, route edge, or identity assertion.
 chain('ALIGN',['W_gate_palace','W_gate_xuanyang','W_fuhang'],'N13','W','alignment')
 edge('JOIN1','L_yang','W_yang_east','identity_water','N04','L+W','J1')
 edge('JOIN2','W_nanqu','W_inner','identity_water','N07','W','J2')
 edge('JOIN3','L_bridge_east','W_bridge_mashi','identity_bridge','N02','L+W','J3')
 rows={
 'east':[
  {'title':'水经注：水流叙述次序','kind':'flow','nodes':['W_north','W_jian','W_yang_east','W_mashi'],'evidence':'N04'},
  {'title':'伽蓝记：独立水段；J1才与上列对接','kind':'flow','nodes':['L_jian','L_yang'],'evidence':'N01'},
  {'title':'出门、至桥、桥北道路：不是水流','kind':'route','nodes':['L_jian_gate','L_bridge_east','L_eastroad'],'evidence':'N02'},
  {'title':'J3：东石桥与马市桥同体是候选，不自动合水','kind':'identity_bridge','nodes':['L_bridge_east','W_bridge_mashi'],'evidence':'N02 / N04'}],
 'palace':[
  {'title':'西部上渠与宫前夹路水段','kind':'flow','nodes':['W_upper','W_wangxian','W_qianqiu','W_palace','W_tongtuo'],'evidence':'N05 / N06'},
  {'title':'宫前西转所注南渠：J2未默认认定','kind':'flow','nodes':['W_tongtuo','W_ritual','W_nanqu'],'evidence':'N07'},
  {'title':'西明入城、流经庙社、靑陽出城段','kind':'flow','nodes':['W_inner','W_she','W_miao','W_qing','W_yang_qing'],'evidence':'N08'},
  {'title':'另一出口：东阳石桥下注阳渠','kind':'flow','nodes':['W_tongtuo','W_sima','W_taicang','W_dongbridge','W_yang_dong'],'evidence':'N09'}],
 'west':[
  {'title':'谷水从西明向南、再沿南城诸处','kind':'flow','nodes':['W_ximing','W_jinyang','W_xuanyang','W_lingtai','W_mingtang','W_kaiyang'],'evidence':'N10'},
  {'title':'长分桥：中朝回溯、有条件的溢流','kind':'overflow','nodes':['L_changfen','L_luowest'],'evidence':'N11'},
  {'title':'西明分支：可核的局部入口','kind':'flow','nodes':['W_ximing','W_inner','W_she'],'evidence':'N08'}],
 'yong':[
  {'title':'出宣阳至洛北岸、渡桥、进入桥南御道','kind':'route','nodes':['L_xuanyang','L_northbank','L_yong','L_southbank','L_siyi'],'evidence':'N12'},
  {'title':'四月行像路径：不并作全年通行','kind':'route','nodes':['L_jingming','L_xuanyang','L_palgate'],'evidence':'N14'},
  {'title':'跨河关系（横线不表示流向）','kind':'crossing','nodes':['L_yong','L_luoyong'],'evidence':'N12'},
  {'title':'W独立提及：对齐不等于汇流，浮桁未并为L永桥','kind':'alignment','nodes':['W_gate_palace','W_gate_xuanyang','W_fuhang'],'evidence':'N13'}]}
 return {'nodes':list(nodes.values()),'edges':edges,'diagram_rows':rows}

QUERIES=[
 {'id':'Q1','title':'W广莫门北水段能沿本段记载到马市桥水段吗？','start':'W_north','end':'W_mashi','mode':'flow'},
 {'id':'Q2','title':'L建春谷水段能接上W马市桥水段吗？','start':'L_jian','end':'W_mashi','mode':'flow'},
 {'id':'Q3','title':'宫前夹路水能经南渠接到靑陽出口吗？','start':'W_palace','end':'W_yang_qing','mode':'flow'},
 {'id':'Q4','title':'宣阳门南谷水与永桥洛水有已证汇流吗？','start':'W_xuanyang','end':'L_luoyong','mode':'flow'},
 {'id':'Q5','title':'宣阳门到桥南御道的叙述行进链？','start':'L_xuanyang','end':'L_siyi','mode':'route','scope':'yong_approach'},
 {'id':'Q6','title':'景明集像到宫前的仪式阶段链？','start':'L_jingming','end':'L_palgate','mode':'route','scope':'procession'},
 {'id':'Q7','title':'长分相关谷水向洛水分流的条件链？','start':'L_changfen','end':'L_luowest','mode':'flow'},
 {'id':'Q8','title':'认定东石桥＝马市桥，会自动产生一条水流吗？','start':'L_bridge_east','end':'W_mashi','mode':'flow'},
 {'id':'Q9','title':'能把行像路径混入永桥普通往来吗？','start':'L_jingming','end':'L_siyi','mode':'route','scope':'yong_approach'},
 {'id':'Q10','title':'本案是否启用东石桥与马市桥同体？','start':'L_bridge_east','end':'W_bridge_mashi','mode':'identity'}]

def enabled_edges(graph,enabled=(),families=('L','W')):
 return [e for e in graph['edges'] if set(e['requires'])<=set(enabled) and set(e['families'])<=set(families)]

def path(graph,q,enabled=(),families=('L','W')):
 allowed={'flow':{'flow','overflow','identity_water'},'route':{'route'},'identity':{'identity_bridge'}}[q['mode']]
 adjacency={}
 for e in enabled_edges(graph,enabled,families):
  if e['kind'] not in allowed:continue
  if q['mode']=='route' and e['route_scope']!=q.get('scope'):continue
  adjacency.setdefault(e['a'],[]).append((e['b'],e))
  if e['kind'].startswith('identity_'):adjacency.setdefault(e['b'],[]).append((e['a'],e))
 queue=deque([(q['start'],[],[q['start']])]);seen={q['start']}
 while queue:
  n,proof,visited=queue.popleft()
  if n==q['end']:
   return {'status':'supported_under_conditions','edge_ids':[e['id'] for e in proof],'nodes':visited,
    'evidence':sorted({p for e in proof for p in e['evidence']}),'premises':sorted({p for e in proof for p in e['requires']}),
    'qualification':'仅此文字模型内的路径；不证明全年通行、共时水文或精确几何。'}
  for target,e in adjacency.get(n,[]):
   if target not in seen:seen.add(target);queue.append((target,proof+[e],visited+[target]))
 return {'status':'not_established','edge_ids':[],'nodes':[],'evidence':[],'premises':[],
  'qualification':'本组材料/前提未建立路径，不等于历史上不存在连接。'}

def event_position(event,year):
 """Locate the event; never propagate its postcondition to unobserved years."""
 a,b=event['start'],event['end']
 if a is None:return 'undated_reference'
 if year<a:return 'event_not_yet_in_recorded_window'
 if year>b:return 'past_event_later_state_unknown'
 return 'event_in_selected_year' if a==b else 'year_inside_uncertain_event_window'

EVENT_LABELS={'undated_reference':'叙述参照未定年','event_not_yet_in_recorded_window':'事件窗口在所选年之后；不判断对象当时是否存在',
 'past_event_later_state_unknown':'事件窗口已过；此年状态仍须另证','event_in_selected_year':'原文事件记于此年（年内月日仍依原记）',
 'year_inside_uncertain_event_window':'所选年落入事件日期区间；不能认定恰在此年发生'}
PANEL_TITLES={'east':'建春两桥：水流、道路与桥名分开','palace':'宫前支渠：南渠接缝与两个出口','west':'城西—城南：沿流水次序与条件溢流','yong':'永桥两岸：通行、跨河与行像路径'}

def diagram(panel,graph):
 esc=html.escape;names={n['id']:n['name'] for n in graph['nodes']}
 s='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1500 1000" role="img"><title>'+esc(PANEL_TITLES[panel])+'</title><desc>文本网络示意，不按地理比例；各行位置不表示实际南北，水流与通行不混合。</desc><style>text{font-family:system-ui,"Noto Sans CJK SC",sans-serif}</style><rect width="1500" height="1000" fill="#f5f3ec"/>'
 def t(x,y,txt,size=21,fill='#254b40'):return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}">{esc(txt)}</text>'
 s+=t(55,55,'北魏洛阳 · 跨区网络 v2.7',20)+t(55,103,PANEL_TITLES[panel],32)
 s+=t(55,145,'文本索引，非真实河形。各行上下位置不表示地理南北；未识别的接缝不自动相连。',19,'#65766c')
 colors={'flow':'#367f9c','route':'#927035','crossing':'#786083','alignment':'#78766c','overflow':'#367f9c','identity_bridge':'#9b624a'}
 for ri,row in enumerate(graph['diagram_rows'][panel]):
  y=205+ri*181;kind=row['kind'];c=colors[kind];seq=row['nodes'];count=len(seq)
  s+=t(60,y,row['title'],22)+t(60,y+30,'依据 '+row['evidence']+' · '+{'flow':'水流','route':'叙述通行','crossing':'桥与河跨越','alignment':'方向参照','overflow':'仅FLOOD启用','identity_bridge':'仅J3启用'}[kind],16,'#6b766c')
  step=1360/max(count,3);width=min(step-38,268)
  for i,n in enumerate(seq):
   x=60+i*step;yy=y+53
   s+=f'<rect x="{x}" y="{yy}" width="{width}" height="70" rx="8" fill="#fffef9" stroke="{c}" stroke-width="2"/>'
   label=names[n];cut=max(8,int((width-20)/18));lines=[label[:cut],label[cut:]] if len(label)>cut else [label]
   for j,line in enumerate(lines):s+=t(x+12,yy+27+j*24,line,18,c)
   if i<count-1:
    x1=x+width+5;x2=x+step-9;ym=yy+35;dash='stroke-dasharray="6 5"' if kind in {'identity_bridge','overflow','alignment'} else ''
    s+=f'<path d="M{x1} {ym}H{x2}" fill="none" stroke="{c}" stroke-width="2" {dash}/>'
    if kind in {'flow','route','overflow'}:s+=f'<path d="M{x2-8} {ym-5}l8 5l-8 5" fill="none" stroke="{c}" stroke-width="2"/>'
 s+=t(55,953,'无比例尺 · 不代表各段同时存在 · 阶段箭头不是常年可通行保证 · 假设开关见网站',19)
 return s+'</svg>'

def csv_output(p,headers,rows):
 b=io.StringIO(newline='');w=csv.writer(b);w.writerow(headers);w.writerows(rows);p.write_text('\ufeff'+b.getvalue(),encoding='utf-8')

def main():
 if not (OUT/'build-info.json').exists():raise SystemExit('Build baseline and v2.5/v2.6 first')
 info=load(OUT/'build-info.json');before={p:h for p,h in info['files_sha256'].items() if p!='index.html'}
 source=load(ROOT/'research/v2.7/passages.json');g=network();entities=load(ROOT/'data/entities.json');ids={e['id'] for e in entities}
 ps={p['id'] for p in source['passages']};ns={n['id'] for n in g['nodes']};source_ids={s['id'] for s in source['sources']}
 assert len(ps)==len(source['passages']) and len(ns)==len(g['nodes'])
 for p in source['passages']:assert p['source'] in source_ids and set(p['map_ids'])<=ids,p['id']
 for n in g['nodes']:assert set(n['map_ids'])<=ids,n['id']
 for e in g['edges']:
  assert e['a'] in ns and e['b'] in ns and set(e['evidence'])<=ps,e['id']
  if e['kind'] in {'flow','overflow','identity_water'}:assert all(next(n for n in g['nodes'] if n['id']==k)['kind']=='water' for k in [e['a'],e['b']]),e['id']
 for ev in source['events']:
  assert ev['object'] is None or ev['object'] in ids,ev['id']
  assert ev['evidence'] in ps
  assert (ev['start'] is None)==(ev['end'] is None)
  assert ev['start'] is None or ev['start']<=ev['end']
 scenarios=[]
 for bits in product([False,True],repeat=4):
  enabled=[k for k,b in zip(['J1','J2','J3','FLOOD'],bits) if b]
  for families in [['L','W'],['L'],['W']]:
   scenarios.append({'id':'n'+''.join('1' if b else '0' for b in bits)+'-'+''.join(families),'enabled':enabled,'families':families,
    'queries':[{**q,**path(g,q,enabled,families)} for q in QUERIES]})
 sampled={ev['object'] for ev in source['events'] if ev['object']};partial={m for p in source['passages'] for m in p['map_ids']}
 audit=[{'entity_id':e['id'],'name':e['name'],'status':'scoped_events_sampled' if e['id'] in sampled else 'passages_reviewed_no_dated_event_added' if e['id'] in partial else 'event_series_not_reviewed',
  'event_ids':[ev['id'] for ev in source['events'] if ev['object']==e['id']],
  'legacy_temporal_state':e.get('temporal_state'),'valid_from':None,'valid_to':None} for e in entities]
 data={**source,**g,'queries':QUERIES,'scenarios':scenarios,'event_labels':EVENT_LABELS,'event_audit':audit,
  'panels':[{'id':k,'title':v,'path':'assets/networks-v27/'+k+'.svg'} for k,v in PANEL_TITLES.items()],
  'limits':['拓扑节点不是经纬坐标；同名阳渠只建立待证候选。','水流、叙述通行、跨越、对齐分层。缺少路径只表示本模型未建立。','跨源接缝包含同段和研究共时假设，不是独立史料。','事件视图显示事件相对年代，不自动推演建筑一直存续或持续毁坏。','547是总括观察框架，尚未获得每个对象的残存状态。'],
  'metrics':{'passages':len(ps),'nodes':len(ns),'edges':len(g['edges']),'queries':len(QUERIES),'scenarios':len(scenarios),'events':len(source['events']),'event_coverage':dict(Counter(a['status'] for a in audit))}}
 write_json(OUT/'data/network-v27.json',data)
 for k in PANEL_TITLES:
  p=OUT/f'assets/networks-v27/{k}.svg';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(diagram(k,g),encoding='utf-8')
 for f in ['networks-v27.js','networks-v27.css']:(OUT/f).write_bytes((ROOT/f).read_bytes())
 index=(OUT/'index.html').read_text(encoding='utf-8');assert 'id="page-network"' not in index,'Run clean baseline build first'
 index=index.replace('</head>','<link rel="stylesheet" href="./networks-v27.css"><script defer src="./networks-v27.js"></script></head>')
 index=index.replace('<a href="#issues"','<a href="#network" data-nav="network">水陆与事件 v2.7</a>\n<a href="#issues"',1)
 index=index.replace('<main id="page-about"','<main id="page-network" class="page page-article" hidden><div id="network-content">水陆专题载入中…</div></main>\n<main id="page-about"',1)
 index=index.replace('地理基线 v2.4 · 空间检验 v2.6','地理基线 v2.4 · 最新专题 v2.7')
 index=index.replace('每个地点，都可以追溯到文字。','每个地点，都可以追溯到文字。 <a href="#network">最新：水陆网络与事件作用范围 v2.7 ↗</a>')
 (OUT/'index.html').write_text(index,encoding='utf-8')
 csv_output(OUT/'downloads/network-edges-v27.csv',['编号','源节点','目标节点','关系类型','依据','条件','通行段落作用域'],[[e['id'],e['a'],e['b'],e['kind'],'/'.join(e['evidence']),'/'.join(e['requires']),e['route_scope'] or ''] for e in g['edges']])
 csv_output(OUT/'downloads/events-v27.csv',['事件','作用对象','构件','范围','最早年','最晚年','原日期','依据','限制'],[[e['name'],e['object'] or '城市总括',e.get('component',''),e['scope'],e['start'],e['end'],e['original_date'],e['evidence'],e['state_note']] for e in source['events']])
 csv_output(OUT/'downloads/event-audit-v27.csv',['实体ID','名称','本轮事件审阅状态','已登记事件','原年代分类'],[[a['entity_id'],a['name'],a['status'],'/'.join(a['event_ids']),a['legacy_temporal_state'] or ''] for a in audit])
 esc=html.escape
 report='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>水陆网络与事件作用范围 v2.7</title><style>body{font:17px/1.8 sans-serif;max-width:1200px;margin:40px auto;padding:20px}img{max-width:100%}article{border-top:1px solid #ccc;padding:20px 0}blockquote{margin:12px;padding:12px;background:#f3f4ed}@media print{img{break-after:page}article{break-inside:avoid}}</style><h1>水陆网络与事件作用范围 v2.7</h1><p>'+esc(source['scope'])+'</p><h2>本次可检验结论</h2><p>建春外水段跨源续接依赖J1；宫前南渠与西明支渠续接依赖J2。认定桥梁同体（J3）不产生水流。宣阳水道与永桥的几何接近不提供汇流边。长分向洛分流须启用条件，且保留中朝回溯。未建立路径不等于历史上不存在。</p><p>这是所选语义模型的条件结果，不是穷尽水网或唯一城市平面。W浮桁提及与L永桥保持独立，不暗中认定同体。</p>'
 for p in data['panels']:report+='<h2>'+esc(p['title'])+'</h2><img src="../'+p['path']+'" alt="'+esc(p['title'])+'">'
 report+='<h2>20条段落证据</h2>'
 for p in source['passages']:
  s=next(s for s in source['sources'] if s['id']==p['source'])
  report+='<article id="'+p['id']+'"><h3>'+p['id']+' · '+esc(p['anchor'])+'</h3><blockquote>'+esc(p['quote'])+'</blockquote><p>'+esc(p['reading'])+'</p><a href="'+esc(s['url'],quote=True)+'">'+esc(s['title'])+'</a></article>'
 report+='<h2>10项事件，不是十项对象现状</h2>'
 for e in source['events']:report+='<article><h3>'+e['id']+' · '+esc(e['name'])+'</h3><p>'+esc(e['original_date'])+'；作用范围：'+esc(e['scope'])+'</p><p>'+esc(e['state_note'])+'</p></article>'
 report+='<h2>339对象审阅账本</h2><p>'+esc(str(data['metrics']['event_coverage']))+'。既有粗略年代标签不等于完成事件年表；未审项未补造日期。</p><h2>尚需考定</h2><p>具体水段同体与共时、南渠身份、东石桥/马市桥同体、雨毁后的修复、塔火后的院内构件残存、547逐址状态，均不能由本批自动解决。不改变母图岸线，不把古里换成米制尺度。</p><h2>复现与边界</h2><p>48种前提/来源组合输出路径边、依据和前提。水流路径不含跨越、对齐或通行边；事件窗口外的对象状态另待证。全量339对象的覆盖账本不等于全量完成年代考证。</p></html>'
 (OUT/'downloads/network-study-v27.html').write_text(report,encoding='utf-8')
 # Deterministic source ZIP for independent reproduction; public repo files only.
 source_files=['research/v2.7/passages.json','tools/network_v27.py','networks-v27.js','networks-v27.css','tests/test_v27.py','tests/browser_v27.py','docs/v2.7-release-notes.md']
 with zipfile.ZipFile(OUT/'downloads/v27-reproducible-sources.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for name in source_files:
   if not (ROOT/name).exists():continue
   entry=zipfile.ZipInfo(name,date_time=(2026,11,11,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;z.writestr(entry,(ROOT/name).read_bytes())
 for p,h in before.items():assert digest(OUT/p)==h,'Changed an existing asset: '+p
 info.update({'research_version':'v2.4 + R07-v2.5 + v2.6-models + v2.7-networks-events','web_version':'0.4.0','network_version':'v2.7','network_counts':data['metrics']})
 info['files_sha256']={str(p.relative_to(OUT)):digest(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='build-info.json'}
 write_json(OUT/'build-info.json',info)
 print('v2.7 BUILD',data['metrics'],'previous public assets unchanged except index.html')

if __name__=='__main__':main()
