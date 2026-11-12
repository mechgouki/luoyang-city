#!/usr/bin/env python3
"""Extend the already-published B1 + R03 palace B2 without replacing either.

West-market material was prepared as an unpublished, conflicting 'B2' package.
Its research is now B3 / L05. This program runs after dual_release.py.
No ancient geographic positions are created.
"""
from pathlib import Path
import csv, hashlib, html, io, json, re, xml.etree.ElementTree as ET
from dual_cartography import NS, load, dump, write_svg, world, region_page, svg, rect, text, para
from pypdf import PdfReader, PdfWriter
import cairosvg

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'_site'
WEST=ROOT/'research/dual-b3/west-market.json'
LABELS=[
 ('w_dashi',2375,6380,'洛阳大市','市'),('w_tongshang',3560,6395,'市东两里','工'),
 ('w_yangu',1535,6395,'市西两里','酤'),('w_cixiao',2375,5665,'市北两里','葬'),
 ('w_tiaoyin',2375,7165,'市南两里','乐'),('w_lingxian',2375,7900,'灵仙寺','寺'),
 ('w_heyang',1550,7900,'台西河阳','县'),('w_hougang',3300,7900,'台东侯宅','宅'),
 ('w_shouqiu',825,4875,'寿丘里','里')]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fp(name,body):
 p='_assets/'+hashlib.sha256(body).hexdigest()[:20]+'-'+Path(name).name
 (SITE/p).parent.mkdir(parents=True,exist_ok=True);(SITE/p).write_bytes(body);return p

def west_glyphs(world_group,markers):
 assert not any(g.get('id')=='west-glyphs-b3' for g in world_group)
 for eid,x,y,_,_ in LABELS:
  found=[m for m in markers if eid in m['ids']]
  assert len(found)==1 and abs(found[0]['x']-x)<.01 and abs(found[0]['y']-y)<.01, eid
 g=ET.SubElement(world_group,'{'+NS+'}g',{'id':'west-glyphs-b3','data-batch':'dual-b3',
      'data-footprint':'false','style':'pointer-events:none'})
 ET.SubElement(g,'{'+NS+'}title').text='城西B3：仅沿用旧文献示意锚点的类型图符，不是古建筑足迹或古代地理坐标'
 for eid,x,y,label,mark in LABELS:
  child=ET.SubElement(g,'{'+NS+'}g',{'data-entity-id':eid,'data-footprint':'false',
                                   'transform':f'translate({x},{y})'})
  ET.SubElement(child,'{'+NS+'}rect',{'x':'-45','y':'-85','width':'90','height':'63',
                       'rx':'8','fill':'#fffdf7','stroke':'#986b35','stroke-width':'5'})
  ET.SubElement(child,'{'+NS+'}path',{'d':'M-55 -84 L0 -125 L55 -84','fill':'none',
                        'stroke':'#986b35','stroke-width':'7','stroke-linejoin':'round'})
  tag=ET.SubElement(child,'{'+NS+'}text',{'x':'0','y':'-39','text-anchor':'middle',
                       'fill':'#986b35','font-size':'36','font-family':'Noto Sans CJK SC,sans-serif'})
  tag.text=mark
 return g

def relation_page():
 r=svg(1800,1300,'B3城西大市—寿丘：文献关系图，非地理比例')
 text(r,70,65,'北魏洛阳 / 城西 B3 · 文献关系（无共同地理比例尺）',26)
 text(r,70,129,'四向八里、两处无定位名录与寿丘',43)
 text(r,70,174,'卡片排列用于读懂关系，不表示里坊间距、排序或院址。',24)
 cards=[('市北','慈孝、奉终','棺椁、轜车',735,250),('市西','延/退酤、治觞','酿酒',150,520),
        ('市场','洛阳大市','西阳门外四里 / 御道南',735,520),('市东','通商、达货','工巧屠贩',1320,520),
        ('市南','调音、乐律','乐艺',735,790)]
 for head,title,subtitle,x,y in cards:
  rect(r,x,y,395,188,'#eff2e8','#a7bfae',3,12)
  text(r,x+22,y+43,head,25,'#4d6f5e')
  text(r,x+22,y+103,title,32,'#243f3a')
  text(r,x+22,y+145,subtitle,21,'#67746d')
 for d in ['M925 438V520','M545 610H735','M1130 610H1320','M925 708V790']:
  from dual_cartography import path
  path(r,d,'#537f7e',4,'10 7')
 text(r,80,1095,'另列：阜财／准财、金肆；开善寺属阜财里。不据此将两里安排进四向次序。',25)
 text(r,80,1150,'皇女台：市南／东南可兼容；寺在台上、台西河阳、台东侯宅另层。',25)
 text(r,80,1210,'寿丘：西自延酤／退酤，东止张方沟，南临洛水，北达芒山；里程不换算。',23)
 return r

def terrain_note():
 r=svg(1800,1050,'B3现代地貌与未配准古代研究：界限')
 text(r,60,90,'新地形参照 / 城西B3',45)
 text(r,60,160,'可读的现代地表模型，不是北魏河岸线、坊墙或人工山遗址',27)
 from dual_cartography import path
 for i,(t,detail) in enumerate([
 ('真实现代地表','Copernicus 30米DSM，经项目既有计算处理；建筑、植被和近代填挖仍可能影响地表。'),
 ('地形分类','低位／高位／坡度是相对邻域参数，没有判定长期稳定台地或古河道。'),
 ('城西文献布局','大市、八里、皇女台、寿丘只按文献示意锚点阅读，不指向现代地表点。'),
 ('当前研究界限','没有给新建筑或水道增加经纬度，旧图和R03宫苑B2依旧独立保留。')
 ]):
  y=240+i*173
  rect(r,65,y,1660,145,'#eff2e9','#bcc9ba',2,9)
  text(r,93,y+48,t,31,'#2c6b53')
  para(r,93,y+94,detail,87,24)
 text(r,75,978,'打开双图网页的「独立地形」栏，可查看已发布的真实现代地形图层。',26)
 return r

def page_html():
 return r'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>北魏洛阳 · 城西大市—寿丘 B3 双图</title>
<style>:root{color-scheme:light}*{box-sizing:border-box}body{font:16px/1.75 system-ui,"Noto Sans CJK SC",sans-serif;margin:0;background:#f8f8f3;color:#284538}header{background:#edf2e8;padding:19px 4vw;border-bottom:1px solid #cbd3c4}header h1{font-size:25px;margin:2px 0}a{color:#28674b}header nav{display:flex;gap:20px;flex-wrap:wrap}.wrap{max-width:1650px;padding:24px 3vw;margin:auto}.tabs{display:flex;flex-wrap:wrap;gap:9px;margin:17px 0}.tabs button,.zoom button{border:1px solid #a8bcae;background:white;border-radius:6px;padding:9px 16px;cursor:pointer;font:inherit}.tabs button[aria-pressed="true"]{background:#326e5c;color:white}.grid{display:grid;grid-template-columns:minmax(0,1fr) 355px;gap:23px}.viewer{border:1px solid #b6c7b8;background:white;overflow:auto;border-radius:9px;min-height:570px}.viewer img{display:block;width:100%;height:auto;transform-origin:top left}.side{padding:23px;border:1px solid #b9c9bc;background:#fff;border-radius:9px;max-height:78vh;overflow:auto}.side select{width:100%;padding:9px}.side blockquote{border-left:4px solid #aa885c;padding:12px;background:#f3f0e6;margin:16px 0}.note{font-size:13px;color:#626f66}.zoom{margin:10px 0}.evidence{margin-top:22px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.evidence article{background:white;padding:18px;border:1px solid #cad4c9;border-radius:7px;scroll-margin:25px}.evidence h3{margin:5px 0;font-size:17px}.evidence p{margin:7px 0;font-size:13px}@media(max-width:850px){.grid{grid-template-columns:1fr}.viewer{min-height:320px}.side{max-height:none}.evidence{grid-template-columns:1fr}} </style>
<header><nav><a href="./">当前文献母图</a><a href="./dual-b2.html">宫苑B2（原版保留）</a><a href="./dual-b1.html">宫前等B1</a><a href="./v3.0.html">现代地形</a><a href="./downloads/dual-west-b3-atlas.pdf">B3图册PDF</a></nav><h1>城西大市—寿丘 B3 · 独立双图</h1><div class="note">原文献图继续深化，现代地形独立参照；图符和示意锚点不是实测古址坐标。旧版和宫苑B2均保留。</div></header>
<main class="wrap"><div class="tabs">
<button data-tab="literary" aria-pressed="true">城西文献图</button><button data-tab="relations">四向八里关系</button>
<button data-tab="terrain">现代地形参照</button><button data-tab="evidence">16条原文证据</button></div>
<div class="grid"><section><div class="zoom"><button id="plus" aria-label="放大">＋</button> <button id="minus" aria-label="缩小">−</button> <button id="reset">重置</button></div><div class="viewer" id="viewer"><img id="map" alt="当前研究图"></div>
<p class="note" id="caption">同一文献母图裁切的城西区域。锚点和图符没有地理比例尺。</p></section><aside class="side"><strong>原文—解释—限制</strong><label for="site">选择核查条目</label><select id="site"></select><section id="detail">正在载入证据…</section></aside></div>
<section class="evidence" id="all" hidden></section>
<p class="note">正文、现代校读及本项目画法是不同层次；两种校注本属于同一原书来源家族，不作独立重复计票。未进行古刻书影逐叶校勘。</p>
</main>
<script>
let records=[],tab='literary',zoom=1;const $=s=>document.querySelector(s);
const esc=t=>String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
const images={literary:['dual/maps/L05.svg','文献母图裁切；无古址实测比例。'],relations:['dual/maps/W-market.svg','关系位置只是排版示意，不是城西实测街区图。'],terrain:['dual/terrain-reading.png','Copernicus现代DSM参数化阅读；没有任何古建筑位置线。']};
function select(i){const e=records.find(x=>x.id===i)||records[0];if(!e)return;$('#site').value=e.id;$('#detail').innerHTML='<h2>'+esc(e.id+' · '+e.title)+'</h2><blockquote>'+esc(e.quote)+'</blockquote><p><b>读法：</b>'+esc(e.reading)+'</p><p><b>边界：</b>'+esc(e.limit)+'</p><p>地理坐标：<b>未定位</b></p><a href="https://deerpark.app/cbeta/B0077/4" target="_blank" rel="noopener">《洛阳伽蓝记》卷四电子文本 ↗</a>';if(location.hash!=='#'+tab+'?id='+e.id)history.replaceState(null,'','#'+tab+'?id='+e.id)}
function show(t){tab=t;document.querySelectorAll('.tabs button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.tab===t?'true':'false'));$('#all').hidden=t!=='evidence';$('#viewer').hidden=t==='evidence';$('.zoom').hidden=t==='evidence';if(t!=='evidence'){const [u,c]=images[t];$('#map').src='./'+u;$('#caption').textContent=c;zoom=1;$('#map').style.transform='scale(1)'}else{$('#caption').textContent='共16项：原文、采纳读法与保留限制可以逐条追溯。'}}
function restore(){let [t,q='']=(location.hash.slice(1)||'literary').split('?');t=images[t]||t==='evidence'?t:'literary';show(t);select(new URLSearchParams(q).get('id')||'W01')}
fetch('./dual/west-b3.json').then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()}).then(d=>{records=d.evidence;$('#site').innerHTML=records.map(e=>'<option value="'+esc(e.id)+'">'+esc(e.id+' '+e.title)+'</option>').join('');$('#all').innerHTML=records.map(e=>'<article id="ev-'+e.id+'"><h3>'+esc(e.id+' · '+e.title)+'</h3><blockquote>'+esc(e.quote)+'</blockquote><p>'+esc(e.reading)+'</p><p><b>限制：</b>'+esc(e.limit)+'</p></article>').join('');restore();document.documentElement.dataset.westB3Ready='true'}).catch(e=>{$('#detail').textContent='加载证据失败：'+e;document.documentElement.dataset.westB3Ready='error'});
document.querySelectorAll('.tabs button').forEach(b=>b.addEventListener('click',()=>{show(b.dataset.tab);select($('#site').value)}));
$('#site').addEventListener('change',()=>select($('#site').value));
$('#plus').onclick=()=>{zoom=Math.min(4,zoom*1.35);$('#map').style.transform='scale('+zoom+')'};
$('#minus').onclick=()=>{zoom=Math.max(.6,zoom/1.35);$('#map').style.transform='scale('+zoom+')'};
$('#reset').onclick=()=>{zoom=1;$('#map').style.transform='scale(1)'};
window.addEventListener('hashchange',()=>{if(records.length)restore()});
</script></html>'''

def main():
 data=load(WEST);assert len(data['evidence'])==16 and all(e['geographic_coordinates'] is None for e in data['evidence'])
 info=load(SITE/'build-info.json');assert info['dual_version']=='B1+B2' and info['source_commit']
 assert not (SITE/'dual-west.html').exists(), 'Do not silently replace an earlier B3 release'
 root=ET.parse(SITE/'assets/master-dual-b2.svg').getroot()
 markers=load(SITE/'data/markers.json');wg=world(root);count=len(list(wg))
 west_glyphs(wg,markers);assert len(list(wg))==count+1
 site_map=SITE/'assets/master-dual-b3-west.svg';write_svg(site_map,root)
 out=SITE/'dual/maps';out.mkdir(parents=True,exist_ok=True)
 reg=dict(data['region'],note='沿用旧文献示意锚点；市、里、桥、台的方位由文献分层解释，不是实测地理比例。')
 items=[(e['id']+' · '+e['title'],e['reading']) for e in data['evidence'] if e['id'] in ('W01','W03','W05','W07','W09','W14')]
 write_svg(out/'L05.svg',region_page(root,reg,items,'B3'))
 write_svg(out/'W-market.svg',relation_page())
 write_svg(out/'T3-west.svg',terrain_note())
 dump(SITE/'dual/west-b3.json',data)
 (SITE/'dual-west.html').write_text(page_html(),encoding='utf-8')
 with (SITE/'downloads/dual-west-b3-evidence.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['编号','主题','相关对象','原文','采用读法','保留限制'])
  for e in data['evidence']:w.writerow([e['id'],e['title'],';'.join(e['entities']),e['quote'],e['reading'],e['limit']])
 writer=PdfWriter()
 for p in ['L05.svg','W-market.svg','T3-west.svg']:
  writer.append(PdfReader(io.BytesIO(cairosvg.svg2pdf(url=str(out/p)))))
 with (SITE/'downloads/dual-west-b3-atlas.pdf').open('wb') as f:writer.write(f)
 index=(SITE/'index.html').read_text(encoding='utf-8')
 match=re.search(r'<script src="\./([^"]+-runtime\.js)"></script>',index);assert match
 runtime=SITE/match.group(1);boot=runtime.read_text(encoding='utf-8')
 m=re.search(r'window\.ATLAS_ASSETS=(.*?);\n',boot);assert m
 mapping=json.loads(m.group(1))
 assert 'assets/master-v28-review.svg' in mapping
 mapping['assets/master-v28-review.svg']=fp(site_map.name,site_map.read_bytes())
 boot=boot[:m.start(1)]+json.dumps(mapping,ensure_ascii=False)+boot[m.end(1):]
 index=index.replace(match.group(1),fp('runtime.js',boot.encode()),1)
 banner='<section id="west-b3-entry" style="margin:16px 0;padding:20px;border:1px solid #bcb59d;background:#f8f4e8;border-radius:8px"><h2>城西大市—寿丘 · B3新分区</h2><p>在已发布B1及宫苑B2之外，新增城西文献图、类型图符、四向八里关系及16条逐项证据；现代地形仍不作古址坐标。</p><p><a href="./dual-west.html#literary?id=W01">进入城西双图 ↗</a>　<a href="./downloads/dual-west-b3-atlas.pdf">下载城西图册 ↗</a>　<a href="./dual-b2.html">宫苑B2继续保留 ↗</a></p></section>'
 assert index.count('id="dual-release-entry"')==1
 index=index.replace('<section id="dual-release-entry"',banner+'<section id="dual-release-entry"',1)
 assert index.count('<nav aria-label="主导航" class="topnav">')==1
 index=index.replace('<nav aria-label="主导航" class="topnav">','<nav aria-label="主导航" class="topnav"><a href="./dual-west.html">城西B3 ↗</a>',1)
 (SITE/'index.html').write_text(index,encoding='utf-8')
 (SITE/'v3.0-dual.html').write_text(index,encoding='utf-8')
 release=load(SITE/'release.json');assert release['release']=='v3.0-dual.b2'
 release['extensions']=sorted(set(release.get('extensions',[])+['dual-west-b3']))
 dump(SITE/'release.json',release)
 info['west_b3']={'source_commit':info['source_commit'],'records':16,'region':'L05','new_ancient_coordinates':0,'previous_release_preserved':'B1+B2'}
 info['files_sha256']={str(p.relative_to(SITE)):sha(p) for p in sorted(SITE.rglob('*')) if p.is_file() and p.name!='build-info.json'}
 dump(SITE/'build-info.json',info)
 print('Built west B3, 16 evidence records, new region L05, preserved published B1 and palace B2')

if __name__=='__main__':main()
