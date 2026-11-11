#!/usr/bin/env python3
"""Integrate audited research into the default map; preserve all source geometry.
Run after the v2.7 build. Emit fingerprinted dependencies and a separate release
entrypoint. This does not claim to invalidate arbitrary external HTML caches.
"""
from pathlib import Path
import hashlib, html, json, re, shutil, xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'_site'
NS='http://www.w3.org/2000/svg'; ET.register_namespace('',NS)
def read(path):return json.loads((OUT/path).read_text(encoding='utf-8'))
def digest(data):return hashlib.sha256(data).hexdigest()
def write(path,body):
 p=OUT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body,encoding='utf-8')
def dump(path,value):write(path,json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def fingerprint(path,body=None):
 body=(OUT/path).read_bytes() if body is None else body
 dest='_assets/'+digest(body)[:20]+'-'+Path(path).name
 p=OUT/dest;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body);return dest

def main():
 info=read('build-info.json'); assert info.get('network_version')=='v2.7','Run v2.7 build first'
 preserved={str(p.relative_to(OUT)):digest(p.read_bytes()) for p in (OUT/'data').glob('*.json')}
 preserved['assets/master-v24.svg']=digest((OUT/'assets/master-v24.svg').read_bytes())
 entities=read('data/entities.json');markers=read('data/markers.json');r=read('data/research-v25.json');m=read('data/milestone-v26.json');n=read('data/network-v27.json')
 modeled={a[k] for a in m['atoms'] for k in ('less','more','node','a','b') if k in a}
 coverage=[]
 for e in entities:
  ev=[x for x in r['evidence'] if e['id'] in x['entities']]
  coverage.append({'id':e['id'],'name':e['name'],'evidence':[x['id'] for x in ev],'panel':ev[0]['group'] if ev else None,
   'model':e['id'] in modeled,'network':[x['id'] for x in n['passages'] if e['id'] in x['map_ids']],
   'events':[x['id'] for x in n['events'] if x['object']==e['id']]})
 by_id={x['id']:x for x in coverage}; shown=[]
 tree=ET.parse(OUT/'assets/master-v24.svg');root=tree.getroot()
 groups=[x for x in root if x.tag==f'{{{NS}}}g' and x.get('transform')];assert len(groups)==1
 layer=ET.SubElement(groups[0],f'{{{NS}}}g',{'id':'review-layer-v28','pointer-events':'none','aria-label':'已有关联研究的原图符；不是新增定位'})
 for mark in markers:
  # Open group lists are intentionally not assigned new geographic dots.
  hits=[by_id[i] for i in mark['ids'] if i in by_id and any(by_id[i][k] for k in ('evidence','model','network','events'))]
  if not hits or mark['kind']=='group':continue
  event=any(h['events'] for h in hits);shown.append({'ids':mark['ids'],'x':mark['x'],'y':mark['y'],'kind':mark['kind'],'event':event})
  g=ET.SubElement(layer,f'{{{NS}}}g',{'class':'v28-signal','data-review-event':str(event).lower(),'data-entities':','.join(mark['ids'])})
  ET.SubElement(g,f'{{{NS}}}title').text='专题覆盖：'+mark['label']+'；沿用原示意点／范围，不新增古址定位。'
  ET.SubElement(g,f'{{{NS}}}circle',{'cx':str(mark['x']),'cy':str(mark['y']),'r':str(168 if mark['kind']=='compound' else 115),'fill':'none','stroke':'#23836b','stroke-width':'15','opacity':'.85'})
  if event:ET.SubElement(g,f'{{{NS}}}rect',{'x':str(mark['x']+100),'y':str(mark['y']-140),'width':'70','height':'70','rx':'13','fill':'#b27b32'})
 # Only new document metadata/title is changed; original drawing elements remain.
 for child in root:
  if child.tag==f'{{{NS}}}text' and child.get('class')=='wt497 tb497':child.text='北魏洛阳 · 研究整合地图 v2.8';child.set('font-size','86')
  if child.tag==f'{{{NS}}}text' and child.get('class')=='wt498 tb498':
   for c in list(child):child.remove(c)
   child.text='底图几何沿用 v2.4；圆环为后续研究覆盖，非新测绘。完整证据见网站。'
 original_children=list(groups[0])[:-1]
 old=ET.parse(OUT/'assets/master-v24.svg').getroot();oldgroup=[x for x in old if x.tag==f'{{{NS}}}g' and x.get('transform')][0]
 assert [ET.tostring(x) for x in original_children]==[ET.tostring(x) for x in oldgroup],'Historical drawing changed'
 write('assets/master-v28-review.svg',ET.tostring(root,encoding='unicode'))
 dump('data/review-layer-v28.json',{'release':'v2.8','basis':'v2.4 geometry + v2.5/v2.6/v2.7 research','coverage':coverage,'markers':shown,
  'stats':{'marked':len(shown),'records':len(coverage),'evidence':len(r['evidence']),'atoms':len(m['atoms']),'passages':len(n['passages']),'events':len(n['events'])},
  'limitations':'圆环是研究覆盖标记，原图符本身仍是示意位置。群组未定位名录不新增点；城市总括事件不分配地图位置。'})
 release={'release':'v2.8','web_version':'0.5.0','entrypoint':'v2.8.html','source_commit':info['source_commit'],
  'geometry_baseline':'v2.4','research_modules':['v2.5','v2.6','v2.7'],'description':'默认研究整合地图与内容指纹发布；不新增历史坐标结论。'}
 dump('release.json',release)
 for path in ('portal-v28.js','portal-v28.css'):shutil.copyfile(ROOT/path,OUT/path)
 index=(OUT/'index.html').read_text(encoding='utf-8')
 header='''<div class="map-header"><div><div class="eyebrow">当前公开版本 · v2.8 / 研究整合地图</div><h1>一张地图，读到最新研究</h1><p>宫前证据、候选平面、水陆网络与事件，已经接入同一张地图。底图位置仍保留文献限制。</p></div><div class="v28-release-state"><span id="v28-online-status" role="status">正在核对在线版本…</span><button id="v28-check-release">检查更新</button><a id="v28-update-link" hidden>加载最新发布 ↗</a></div></div>
<div class="v28-summary"><a href="#map?region=R07"><em>01 / 地图</em><b>宫前区域 · 最新依据</b><small>在原图上点击绿色圆环地点</small></a><a href="#model?case=s011"><em>02 / 方案</em><b>13张候选平面</b><small>切换前提，查看位置为何变化</small></a><a href="#network"><em>03 / 连接</em><b>水陆网络 · 20段证据</b><small>区分水流、跨越与道路通行</small></a><a href="#map?layer=events&year=534"><em>04 / 年代</em><b>事件现在可以在图上读</b><small>534年塔火不等于整座寺院消失</small></a></div>'''
 start=index.index('    <div class="map-header">');end=index.index('    <div class="workspace">',start)
 index=index[:start]+header+'\n'+index[end:]
 index=index.replace('<strong>北魏洛阳文献地图</strong>','<strong>北魏洛阳文献地图<span class="brand-release">v2.8</span></strong>',1)
 index=index.replace('>交互地图</a>','>整合地图</a>',1).replace('>分区图册</a>','>底图档案</a>',1)
 controls='''<div class="v28-layers" aria-label="研究图层"><button data-v28-layer="review" aria-pressed="true">最新研究层</button><button data-v28-layer="events" aria-pressed="false">事件阅读层</button><button data-v28-layer="baseline" aria-pressed="false">仅底图</button><label>阅读年份 <select id="v28-year" disabled><option>516</option><option>527</option><option selected>534</option><option>546</option><option>547</option></select></label><div class="v28-layer-note">这是研究覆盖与事件索引，不把候选布局、文字网络当作新的真实岸线或建筑足迹。</div></div><div id="v28-layer-legend" class="v28-map-key">绿色圆环＝专题覆盖；橙色方标＝事件记录。</div>'''
 index=index.replace('        <div class="map-tools">',controls+'\n        <div class="map-tools">',1)
 index=index.replace('ATLAS · 37 SHEETS','底图档案 · v2.4 · 37 SHEETS').replace('<h1>从全城到街巷</h1>','<h1>原始分区图册 · 封存底图</h1>')
 index=index.replace('地理基线 v2.4 · 最新专题 v2.7','当前整合版 v2.8 · 原始几何底图 v2.4')
 helpbox='''<details class="v28-help"><summary>本次具体更新了什么？为什么仍能看到“底图 v2.4”？</summary><p>v2.8是新的默认整合地图：研究覆盖标记、地点证据入口与事件阅读层已进入主地图。v2.4仅指封存的几何底图，不是当前网站版本。候选位置与水道接缝仍留在检验视图，未因换版改成定论。</p><p><a href="./assets/master-v28-review.svg" target="_blank" rel="noopener">下载新版整合地图 SVG ↗</a>　<a href="./downloads/release-v28.html" target="_blank" rel="noopener">本版更新说明与全部入口 ↗</a>　<a href="./downloads/luoyang-v24-regional-atlas.pdf">封存底图 PDF（v2.4）</a></p></details>'''
 index=index.replace('    <div class="bottom-disclaimer">',helpbox+'\n    <div class="bottom-disclaimer">',1)
 index=index.replace('<title>北魏洛阳 · 文献地图</title>','<title>北魏洛阳 · 研究整合地图 v2.8</title>')
 index=index.replace('</head>','<link rel="stylesheet" href="./portal-v28.css"><script defer src="./portal-v28.js"></script></head>')
 # Immutable content URLs: avoid mixing a new HTML page with cached old JS/JSON.
 mapping={}
 for path in sorted([str(p.relative_to(OUT)) for p in (OUT/'data').glob('*.json')]+['assets/master-v28-review.svg']):mapping[path]=fingerprint(path)
 bootstrap='window.ATLAS_RELEASE='+json.dumps(release,ensure_ascii=False)+';\nwindow.ATLAS_ASSETS='+json.dumps(mapping)+';\n'+'''window.atlasURL=function(input){const u=new URL(input,location.href),base=new URL('.',location.href);if(u.origin===base.origin&&u.pathname.startsWith(base.pathname)){const key=decodeURIComponent(u.pathname.slice(base.pathname.length));if(window.ATLAS_ASSETS[key])return new URL(window.ATLAS_ASSETS[key],base).href}return u.href};window.atlasFetch=function(input,options){return fetch(window.atlasURL(input),options)};'''
 boot=fingerprint('runtime.js',bootstrap.encode())
 def script(match):
  path=match.group(1).removeprefix('./');code=(OUT/path).read_text(encoding='utf-8')
  if path=='app.js':code=code.replace("fetch('./assets/master-v24.svg')","fetch('./assets/master-v28-review.svg')")
  if path!='portal-v28.js':code=re.sub(r'\bfetch\(', 'atlasFetch(',code)
  return '<script defer src="./'+fingerprint(path,code.encode())+'"></script>'
 index=re.sub(r'<script defer src="([^"]+)"></script>',script,index)
 index=re.sub(r'<link rel="stylesheet" href="([^"]+)">',lambda x:'<link rel="stylesheet" href="./'+fingerprint(x.group(1).removeprefix('./'))+'">',index)
 index=index.replace('<head>','<head>\n<script src="./'+boot+'"></script>',1)
 write('index.html',index);write('v2.8.html',index)
 report='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v2.8 网站与整合地图更新</title><style>body{max-width:850px;margin:40px auto;padding:20px;font:17px/1.9 sans-serif;color:#284638}a{color:#21745a}li{margin:15px 0}</style><h1>v2.8：新版成果进入默认地图</h1><p>本次修复默认页仍醒目标作v2.4、研究分散于专题页、未区分当前发布与封存底图的问题。</p><p>新增研究覆盖图层与事件阅读层、独立整合SVG、当前发布核对、内容指纹依赖和独立版本入口。不移动原地点、不补院墙、不将事件扩张为整寺或547年永久状态。</p><ul><li><a href="../v2.8.html#map">研究整合地图 v2.8</a></li><li><a href="../v2.8.html#map?layer=events&amp;year=534">在地图上读534年事件</a></li><li><a href="../v2.8.html#model?case=s011">空间前提与候选平面</a></li><li><a href="../v2.8.html#network">水陆文本网络与事件资料</a></li><li><a href="../assets/master-v28-review.svg">新版整合SVG（底图几何仍源自v2.4）</a></li><li><a href="../data/review-layer-v28.json">实体—研究覆盖对应表</a></li><li><a href="../release.json">发布版本、提交与入口</a></li></ul><p>新入口使用内容指纹代码和数据，避免旧缓存混搭。已缓存的旧HTML不能被服务器隔空改写；独立v2.8.html入口提供直接取得新版的路径。在线版本核对失败时不冒称已核验。</p></html>'''
 write('downloads/release-v28.html',report)
 for path,sha in preserved.items():assert digest((OUT/path).read_bytes())==sha,path
 info.update({'portal_version':'v2.8','web_version':'0.5.0','entrypoint':'v2.8.html','portal_counts':{'marked':len(shown),'coverage':len(coverage)},'research_version':'v2.4 geometry + v2.5/v2.6/v2.7 research; integrated release v2.8'})
 info['files_sha256']={str(p.relative_to(OUT)):digest(p.read_bytes()) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='build-info.json'}
 dump('build-info.json',info)
 dump('../artifacts/v28-integration-audit.json',{'geometry_children_unchanged':True,'preserved_sha256':preserved,'marker_count':len(shown),'coverage_count':len(coverage),'fingerprinted_dependencies':mapping,'release':release})
 print(f'v2.8: {len(shown)} original marker groups with research coverage; immutable geometry and source data verified; versioned entrypoint and dependencies emitted.')
if __name__=='__main__':main()
