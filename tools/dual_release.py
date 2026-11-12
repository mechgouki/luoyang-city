#!/usr/bin/env python3
"""Publish reviewed B1 plus R03 B2 without overwriting prior research assets."""
from pathlib import Path
import base64,csv,hashlib,html,io,json,re,shutil,zipfile,zlib
import xml.etree.ElementTree as E
from dual_cartography import *
ROOT=Path(__file__).resolve().parents[1];SITE=ROOT/'_site';VERSION='v3.0-dual.b2'
def fp(site,name,body):
 path='_assets/'+hashlib.sha256(body).hexdigest()[:20]+'-'+Path(name).name
 (site/path).write_bytes(body);return path

def read_snapshot():
 spec=load(ROOT/'research/dual-b1/glyphs.json');raw=zlib.decompress(base64.b64decode(spec['data'],validate=True))
 assert len(raw)==spec['uncompressed_size'] and hashlib.sha256(raw).hexdigest()==spec['uncompressed_sha256'],'B1 snapshot is incomplete or altered'
 data=json.loads(raw);assert set(data)==set(B1);return data

def report(data):
 esc=html.escape
 head='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>双图B1+B2研究报告</title><style>body{max-width:1050px;margin:35px auto;padding:20px;font:17px/1.85 sans-serif;color:#27453c}article{padding:23px;border:1px solid #c7d3c5;margin:24px 0;border-radius:8px}blockquote{margin:15px 0;background:#edf3e9;padding:14px}small{color:#687769}a{color:#286b52}img{max-width:100%}@media print{article{break-inside:avoid}}</style><h1>双图 B1+B2：原图继续深化，新图独立建设</h1><p>B1三处分区发布；B2推进R03宫苑—景阳山—瑶光。没有将旧图像素换成古址经纬度。</p><p><a href="../dual-b2.html">打开互动双图</a> · <a href="dual-map-atlas.pdf">下载图册PDF</a> · <a href="dual-evidence.csv">下载证据表</a></p>'
 head+='<h2>原文献图实质修改</h2><p>累计15组图符，其中B1七组按已审快照保存，B2八组新拆构件；原179点击目标位置不变。原图与地形插图共用实体编号，但不强行共用地理坐标。</p>'
 for reg in data['regions']:
  head+=f'<h2>{esc(reg["id"]+" · "+reg["name"])}</h2><img alt="分区文献图" src="../dual/maps/{reg["id"]}.svg">'
 head+='<h2>B1 已审改图决定</h2>'
 for d in data['b1']['decisions']:
  head+=f'<article id="{d["id"]}"><h3>{d["id"]} · {esc(d["after"])}</h3><p>旧表达：{esc(d["before"])}</p><blockquote>{esc(d["quote"])}</blockquote><p>{esc(d["limit"])}</p><small>依据：{esc(" / ".join(d["evidence"]))}</small></article>'
 head+='<h2>B2 电子原文与校读（16项）</h2>'
 for e in data['b2']['evidence']:
  head+=f'<article id="{e["id"]}"><h3>{e["id"]} · {esc(e["title"])}</h3><p>{esc(e["layer"]+" / "+e["locator"])}</p><blockquote>{esc(e["quote"])}</blockquote><p><b>解释：</b>{esc(e["reading"])}</p><p><b>图面：</b>{esc(e["drawing"])}</p>'
  head+=' '.join(f'<a href="{s["url"]}">{esc(s["id"]+" "+s["title"])}</a>' for s in data['b2']['sources'] if s['id'] in e['sources'])+'</article>'
 head+='<h2>地形解释边界</h2><p>现代90米sigma平滑DSM的1公里sigma邻域相对高低，仅为参数化地势阅读，3公里边缘邻域不足另标。没有诊断古台地、河漫滩、人工山遗址或地貌长期稳定性。R03诸海地下石窦不是现代地表水槽。</p><p>钓台殿仍不定位；清暑与百果园之间不增设南北次序；四殿总括不补第四处院址。景阳山／景山殿校读与张伦私园同名山分别处理。</p><p>本轮核查电子转录及周、范校语，未宣称完成古刻书影逐叶校勘。研究成立条件、名物异读与现代图符属于不同层次。</p></html>'
 return head

def main():
 site=SITE;info=load(site/'build-info.json');assert info.get('terrain_version')=='v3.0-alpha.1'
 protected={str(p.relative_to(site)):sha(p) for p in site.rglob('*') if p.is_file() and p.name not in ['index.html','release.json','build-info.json']}
 out=site/'dual';maps=out/'maps';out.mkdir(exist_ok=True);maps.mkdir(exist_ok=True)
 b1=load(ROOT/'research/dual-b1/decisions.json');b2=load(ROOT/'research/dual-b2/palace-gardens.json');snapshot=read_snapshot()
 entities=load(site/'data/entities.json');ids={e['id'] for e in entities};markers=load(site/'data/markers.json')
 assert all(set(e['entities'])<=ids and e['geographic_coordinates'] is None for e in b2['evidence'])
 master1,audit1=changed_master(site/'assets/master-v24.svg',snapshot,markers,'b1');master2,audit2=changed_master(site/'assets/master-v24.svg',snapshot,markers,'b2')
 integrated,_=changed_master(site/'assets/master-v28-review.svg',snapshot,markers,'b2')
 write_svg(maps/'literary-master-b1.svg',master1);write_svg(maps/'literary-master-b2.svg',master2);write_svg(site/'assets/master-dual-b2.svg',integrated)
 regions=b1['regions']+[dict(b2['region'],note='地下联系、人工山与名物异读分层；钓台殿和柰林群仍不定位。')]
 by={d['id']:d for d in b1['decisions']}
 for reg in regions:
  items=[(i+' · '+by[i]['action'],by[i]['after']) for i in reg.get('changes',[])]
  if reg['id']=='L04':items=[('G01—G04  瑶光与西游园','瑶光塔、讲殿尼房分开列；井在凌云台上，凉风观在井北。'),('G07—G09  台与人工山','九华台上清凉殿；蓬莱山上仙人馆。钓台殿仍以异读附记。'),('G10—G13  山名与未定次序','景山殿有山／殿校读；清暑与百果园先后未定，柰林群不新增院址。'),('G14—G16  地下与时层','诸海联系记地下石窦；不以现代沟谷配准，也不把530侵扰画成寺毁。')]
  write_svg(maps/(reg['id']+'.svg'),region_page(master2 if reg['id']=='L04' else master1,reg,items,'B2' if reg['id']=='L04' else 'B1'))
 for kind in ['platform','hill','water']:write_svg(maps/('G-'+kind+'.svg'),diagram(kind))
 terrain_data=terrain(site,out)
 write_svg(maps/'T1.svg',terrain_plate(out,master1,regions,terrain_data,'B1'));write_svg(maps/'T2.svg',terrain_plate(out,master2,regions,terrain_data,'B2'))
 data={'version':VERSION,'source_commit':info['source_commit'],'base_commit':b1['base_commit'],'b1':b1,'b2':b2,'regions':regions,'terrain':terrain_data,'audits':{'b1':audit1,'b2':audit2},'entities':[{'id':e['id'],'name':e['name']} for e in entities],'new_ancient_coordinates':0,'map_kind':'literary qualitative reference + independent modern terrain; no ancient registration'}
 dump(out/'data.json',data);dump(out/'b1-glyphs-decoded.json',snapshot)
 csvbuf=io.StringIO(newline='');w=csv.writer(csvbuf);w.writerow(['编号','对象','层次','原文','出处','解释','图面处理','限制'])
 for d in b1['decisions']:w.writerow([d['id'],d['entity'],'B1决定',d['quote'],';'.join(d['evidence']),d['before'],d['after'],d['limit']])
 for e in b2['evidence']:w.writerow([e['id'],';'.join(e['entities']),e['layer'],e['quote'],e['locator'],e['reading'],e['drawing'],'不产生古址经纬度；未完成古刻逐页校勘'])
 (site/'downloads/dual-evidence.csv').write_text('\ufeff'+csvbuf.getvalue(),encoding='utf-8');(site/'downloads/dual-map-report.html').write_text(report(data),encoding='utf-8')
 import cairosvg
 from pypdf import PdfReader,PdfWriter
 writer=PdfWriter();pages=['L01','L02','L03','T1','L04','G-platform','G-hill','G-water','T2']
 for code in pages:
  binary=cairosvg.svg2pdf(url=str(maps/(code+'.svg')));writer.append(PdfReader(io.BytesIO(binary)))
 with (site/'downloads/dual-map-atlas.pdf').open('wb') as f:writer.write(f)
 writer=PdfWriter()
 for code in ['literary-master-b1','L01','L02','L03','T1']:writer.append(PdfReader(io.BytesIO(cairosvg.svg2pdf(url=str(maps/(code+'.svg'))))))
 with (site/'downloads/dual-b1-atlas.pdf').open('wb') as f:writer.write(f)
 release=dict(load(site/'release.json'),release=VERSION,web_version='0.8.0',entrypoint='v3.0-dual.html',description='双图B1正式发布＋B2宫苑深化；原文献图与独立地形图并行',research_modules=['v2.5','v2.6','v2.7','v2.9','dual-b1','dual-b2'])
 template=(ROOT/'web/dual-viewer.html').read_text(encoding='utf-8')
 assets={str(p.relative_to(site)):fp(site,p.name,p.read_bytes()) for p in [out/'data.json',*maps.glob('*.svg'),out/'terrain-classes.png',out/'terrain-reading.png']}
 for name,reg,batch in [('dual-b1.html','L01','B1'),('dual-b2.html','L04','B2')]:
  config={'release':release,'assets':assets,'default_region':reg,'batch':batch}
  (site/name).write_text(template.replace('__DUAL_CONFIG__',json.dumps(config,ensure_ascii=False).replace('</','<\\/')),encoding='utf-8')
 index=(site/'index.html').read_text(encoding='utf-8');runtime=re.search(r'<script src="\./([^\"]+-runtime\.js)"></script>',index);assert runtime
 boot=(site/runtime.group(1)).read_text(encoding='utf-8');mapping=json.loads(re.search(r'window\.ATLAS_ASSETS=(.*?);\n',boot).group(1))
 mapping['assets/master-v28-review.svg']=fp(site,'master-dual-b2.svg',(site/'assets/master-dual-b2.svg').read_bytes());mapping['dual/data.json']=assets['dual/data.json']
 boot=re.sub(r'window\.ATLAS_RELEASE=.*?;\n','window.ATLAS_RELEASE='+json.dumps(release,ensure_ascii=False)+';\n',boot,count=1);boot=re.sub(r'window\.ATLAS_ASSETS=.*?;\n','window.ATLAS_ASSETS='+json.dumps(mapping)+';\n',boot,count=1)
 index=index.replace(runtime.group(1),fp(site,'runtime.js',boot.encode()),1)
 index=re.sub(r'<span class="brand-release">[^<]*</span>',f'<span class="brand-release">{VERSION}</span>',index,count=1)
 index=index.replace('当前公开版本 · v3.0 第一批 / 真实地形基底','当前公开版本 · 双图 B1+B2 / 文献图继续深化')
 index=index.replace('<title>北魏洛阳 · 同址时层对照 v2.9</title>','<title>北魏洛阳 · 双图并行 B1+B2</title>')
 banner='<section id="dual-release-entry" style="margin:15px 0;padding:20px;border:1px solid #b9cdbd;border-left:5px solid #326e5c;background:#edf3e8;border-radius:8px"><h2>原文献图已更新 · 新增宫苑—景阳山区域</h2><p>B1三处分区正式发布，B2继续细化台、山、殿、塔；旧版档案保留。地下水联系和古址经纬度没有因换版变成定论。</p><p><a href="./dual-b2.html#literary?region=L04">打开 B2 宫苑双图 ↗</a>　<a href="./dual-b1.html">回看已发布 B1 ↗</a>　<a href="./downloads/dual-map-atlas.pdf">下载双图图册 ↗</a></p></section>'
 index=index.replace('<div class="v28-summary">',banner+'<div class="v28-summary">',1)
 index=index.replace('<nav aria-label="主导航" class="topnav">','<nav aria-label="主导航" class="topnav"><a href="./dual-b2.html">双图 B1+B2 ↗</a>',1)
 index=index.replace('>仅底图</button>','>仅文献图</button>')
 portal=re.search(r'<script defer src="\./([^\"]+-portal-v28\.js)"></script>',index)
 if portal:
  code=(site/portal.group(1)).read_text(encoding='utf-8').replace('档案底图模式：关闭研究标记，保留原图面。','当前文献图：关闭研究标记；封存v2.4在双图工作台中另行对照。').replace('研究整合地图 v2.8 · 北魏洛阳','双图文献工作图 B1+B2 · 北魏洛阳')
  index=index.replace(portal.group(1),fp(site,'portal-dual.js',code.encode()))
 js=fp(site,'dual-main.js',(ROOT/'web/dual-main.js').read_bytes());index=index.replace('</head>',f'<script defer src="./{js}"></script></head>')
 (site/'index.html').write_text(index,encoding='utf-8');(site/'v3.0-dual.html').write_text(index,encoding='utf-8');dump(site/'release.json',release)
 with zipfile.ZipFile(site/'downloads/dual-map-package.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(out.rglob('*')):
   if p.is_file():z.write(p,str(p.relative_to(site)))
  for path in ['dual-b1.html','dual-b2.html','downloads/dual-map-report.html','downloads/dual-evidence.csv','downloads/dual-map-atlas.pdf','downloads/dual-b1-atlas.pdf']:z.write(site/path,path)
  for path in ['assets/master-v24.svg','data/entities.json',*sorted(set(assets.values()))]:z.write(site/path,path)
 for p,h in protected.items():assert sha(site/p)==h,'Pre-existing asset modified: '+p
 verification={'baseline_commit':b1['base_commit'],'source_commit':info['source_commit'],'protected_files':len(protected),'protected_unchanged':True,'sha256':protected,'b1_groups':audit1['groups_changed'],'cumulative_groups':audit2['groups_changed'],'ancient_coordinates_added':0}
 dump(out/'preservation.json',verification)
 info.update(portal_version=VERSION,web_version='0.8.0',dual_version='B1+B2',dual_counts={'b1_decisions':14,'b2_evidence':16,'regions':4,'changed_groups':15,'new_ancient_coordinates':0})
 info['files_sha256']={str(p.relative_to(site)):sha(p) for p in sorted(site.rglob('*')) if p.is_file() and p.name!='build-info.json'};dump(site/'build-info.json',info)
 print('Dual B1+B2:',info['dual_counts'],'preserved files',len(protected))
if __name__=='__main__':main()
