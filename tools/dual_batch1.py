#!/usr/bin/env python3
"""Two parallel maps; never infer ancient geographic coordinates from old pixels."""
from pathlib import Path
import base64,copy,csv,hashlib,html,io,json,re,shutil,zipfile
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
from scipy.ndimage import maximum_filter,minimum_filter,binary_erosion
import rasterio
from rasterio.io import MemoryFile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'_site';NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS);E=html.escape

def read(path):return json.loads((OUT/path).read_text(encoding='utf-8'))
def digest(b):return hashlib.sha256(b).hexdigest()
def write(path,body):
 p=OUT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body,encoding='utf-8')
def dump(path,value):write(path,json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def tag(name,**a):return ET.Element('{'+NS+'}'+name,{k.replace('_','-'):str(v) for k,v in a.items()})
def add(parent,name,**a):
 n=tag(name,**a);parent.append(n);return n
def txt(parent,x,y,value,size=23,fill='#29483f',**a):
 t=add(parent,'text',x=x,y=y,font_size=size,fill=fill,font_family='Noto Sans CJK SC,Microsoft YaHei,sans-serif',**a);t.text=value;return t

def glyph(parent,x,y,kind,color):
 g=add(parent,'g',transform=f'translate({x} {y})',fill='none',stroke=color,stroke_width='3',data_glyph=kind)
 def rect(xx,yy,w,h,dash=None):
  a={'x':xx,'y':yy,'width':w,'height':h,'fill':'#faf9f5'}
  if dash:a['stroke_dasharray']=dash
  return add(g,'rect',**a)
 if kind.startswith('bridge'):
  if kind=='bridge_ns':
   rect(-24,-68,48,136)
   for yy in range(-58,60,20):add(g,'path',d=f'M-22 {yy}H22',stroke_width='1.5')
  else:
   add(g,'path',d='M-76 -24H-16M16 -24H76M-76 24H-16M16 24H76',stroke_width='4')
   add(g,'path',d='M-15 -33L-4 -12L-13 9L2 33M9 -33L20 -9L12 13L25 33',stroke='#a56c43',stroke_width='3')
   add(g,'path',d='M-76 0H76',stroke_dasharray='8 7',stroke_width='1.5')
  return
 if kind=='tower_hall':
  rect(-62,-103,124,39);add(g,'path',d='M-67 -83H67',stroke_width='1.5')
  rect(-37,-29,74,74);rect(-23,-15,46,46);add(g,'path',d='M-37 8H37M0 -29V45',stroke_width='1.3')
  txt(g,89,-76,'殿',20,color,text_anchor='middle',stroke='none');txt(g,82,22,'塔',20,color,text_anchor='middle',stroke='none')
 elif kind=='tower_uncertain':
  rect(-44,-50,88,88,'7 5');rect(-27,-33,54,54,'5 4')
  txt(g,0,15,'7',29,color,text_anchor='middle',stroke='none');txt(g,73,-40,'†',28,'#a56c43',stroke='none')
 elif kind=='office':
  rect(-66,-43,132,76);add(g,'path',d='M-66 -13H66M-33 -43V33M33 -43V33',stroke_width='1.5');add(g,'path',d='M-79 -50L0 -70L79 -50',stroke_width='3')
 elif kind=='school':
  rect(-69,-38,138,68);add(g,'path',d='M-75 -43H75M-45 -38V30M0 -38V30M45 -38V30',stroke_width='1.5')
 else:
  rect(-58,-37,116,70);add(g,'path',d='M-77 -41L-45 -66H45L77 -41Z',fill='#ecf2e8',stroke_width='3');add(g,'path',d='M-23 -37V33M23 -37V33',stroke_width='1.5')
 add(g,'path',d='M-91 -69H-101V49H-91M91 -69H101V49H91',stroke_width='1.4',stroke_dasharray='4 4')

def patch_master(path,data,markers):
 root=ET.parse(OUT/path).getroot();group=next(x for x in root if x.tag==f'{{{NS}}}g' and x.get('transform'))
 add(root,'style').text='text{stroke:none}'
 stamps=[]
 for change in data['changes']:
  m=next(x for x in markers if change['entity'] in x['ids'] and x['kind']!='group');matches=[]
  for n in group:
   if n.tag!=f'{{{NS}}}g' or not n.get('class','').startswith('wnode'):continue
   if any(f'{change["map_id"]} ' in ''.join(t.itertext()) for t in n.findall(f'{{{NS}}}text')):matches.append(n)
  assert len(matches)==1,(change['id'],len(matches))
  g=matches[0];before=ET.tostring(g);texts=g.findall(f'{{{NS}}}text');label=[t for t in texts if change['map_id']+' ' in ''.join(t.itertext())][0];color=label.get('fill','#356f62')
  for node in list(g):
   if node.tag!=f'{{{NS}}}text':g.remove(node)
   elif node is not label and float(node.get('y',0))<float(label.get('y',0)):g.remove(node)
  for t in [t for t in g.findall(f'{{{NS}}}text') if t is not label]:g.remove(t)
  glyph(g,m['x'],m['y'],change['glyph'],color);new_icon=g[-1];g.remove(new_icon);g.insert(0,new_icon)
  g.set('data-entity',change['entity']);g.set('data-change',change['id'])
  if change['entity']=='v3_hanguozixue':
   for t in label:label.remove(t)
   label.text=change['map_id']+' 汉国子学堂旧址'
  txt(g,label.get('x'),float(label.get('y'))+43,change['note'],22,'#7c664b',text_anchor=label.get('text-anchor','middle'),stroke='#faf9f5',stroke_width='5',paint_order='stroke')
  stamps.append({'change':change['id'],'entity':change['entity'],'old_group_hash':digest(before),'new_group_hash':digest(ET.tostring(g)),'anchor':[m['x'],m['y']]})
 for child in root:
  if child.tag==f'{{{NS}}}text' and child.get('class')=='wt497 tb497':child.text='北魏洛阳 · 文献工作图 v2.10';child.set('font-size','86')
  if child.tag==f'{{{NS}}}text' and child.get('class')=='wt498 tb498':
   for c in list(child):child.remove(c)
   child.text='三片区构件与时层深化；旧版另存。图符不是实测足迹；古代地理坐标未据本图产生。'
 return root,stamps

def wrap(text,width):
 result=[]
 while text:
  n=min(width,len(text))
  if n<len(text) and text[n] in '。；，、':n+=1
  result.append(text[:n]);text=text[n:]
 return result

def panel_svg(master,region,info,data,markers):
 root=tag('svg',viewBox='0 0 1800 1260',role='img');add(root,'title').text=info['title']+' 文献工作图';add(root,'rect',width=1800,height=1260,fill='#faf9f5');add(root,'style').text='text{stroke:none}'
 defs=master.find(f'{{{NS}}}defs')
 if defs is not None:root.append(copy.deepcopy(defs))
 txt(root,52,57,'LUOYANG / DOCUMENT WORKMAP 2.10',18,'#698171');txt(root,52,109,info['code']+'  '+info['title'],37);txt(root,52,151,'共同母图裁切 · 地点锚点未移 · 构件与时间作用范围已更新',21,'#758171')
 x,y,w,h=region['bbox'];viewport=add(root,'svg',x=45,y=190,width=1140,height=965,viewBox=f'{x+200} {y+640} {w} {h}')
 group=next(g for g in master if g.tag==f'{{{NS}}}g' and g.get('transform'));viewport.append(copy.deepcopy(group))
 add(root,'path',d='M1220 200V1160',stroke='#cad3c7',stroke_width=2);txt(root,1260,228,'这一片具体改了什么',25);yy=278
 for change in data['changes']:
  if change['region']!=info['code']:continue
  txt(root,1260,yy,change['id']+'  '+change['name'],23);yy+=34
  for line in wrap(change['note'],21):txt(root,1260,yy,line,18,'#786346');yy+=28
  txt(root,1260,yy,'据 '+', '.join(change['evidence']),16,'#778078');yy+=47
 yy=max(yy+12,790);txt(root,1260,yy,'阅读限制',24);yy+=40
 for note in info['notes']:
  for line in wrap(note,25):txt(root,1260,yy,line,18,'#6b776c');yy+=29
  yy+=16
 txt(root,52,1203,'图符表示类别／有据构件，不是院墙、实际开间或占地。方位来自文字，间距仍为显示安排。',20,'#6e786b')
 return ET.tostring(root,encoding='unicode')

def terrain_classes(z,slope,valid,cell=30):
 # Fixed diagnostic criteria, not a validated palaeolandform model.
 radius=30;size=2*radius+1;safe=np.where(valid,z,0)
 hi=maximum_filter(np.where(valid,safe,-np.inf),size=size,mode='constant',cval=-np.inf);lo=minimum_filter(np.where(valid,safe,np.inf),size=size,mode='constant',cval=np.inf)
 interior=binary_erosion(valid,structure=np.ones((size,size)),border_value=0);relief=hi-lo;cls=np.zeros(z.shape,np.uint8);cls[interior]=2
 cls[interior&(relief<=20)&(slope<=3)]=1;cls[interior&((relief>=60)|(slope>=8))]=3
 return cls,relief,interior

def make_terrain():
 meta=read('terrain/v3.0/metadata.json')
 with zipfile.ZipFile(OUT/'downloads/luoyang-terrain-v30-gis.zip') as zf:
  with MemoryFile(zf.read('display-dsm-sigma90m.tif')) as mem:
   with mem.open() as ds:z=ds.read(1);profile=ds.profile;valid=(ds.read_masks(1)>0)&np.isfinite(z)
  with MemoryFile(zf.read('slope-display-sigma90m-deg.tif')) as mem:
   with mem.open() as ds:slope=ds.read(1);valid&=(ds.read_masks(1)>0)&np.isfinite(slope)
 cls,local_relief,interior=terrain_classes(z,slope,valid);colors=np.array([[246,245,238],[207,223,205],[228,217,185],[183,157,132]],np.uint8);rgb=colors[cls]
 hill=np.array(Image.open(OUT/'terrain/v3.0/hillshade.png').convert('L').resize((z.shape[1],z.shape[0])),dtype=float)/255;rgb=(rgb.astype(float)*(0.78+0.22*hill[:,:,None])).astype(np.uint8);rgb[~interior]=colors[0];Image.fromarray(rgb).save(OUT/'dual1/terrain-interpretation.png')
 profile.update(dtype='uint8',nodata=0,count=1,compress='deflate',predictor=1)
 with rasterio.open(OUT/'dual1/modern-form-classes.tif','w',**profile) as ds:ds.write(cls,1);ds.update_tags(MEANING='Present-surface diagnostic classes; NOT ancient stable terrain or palaeochannels')
 policy={'rule':'On sigma90m modern DSM, 61×61 cells (1.83km window): class1 relief≤20m AND slope≤3deg; class3 relief≥60m OR slope≥8deg; remainder class2. No-data/border class0.','labels':{'0':'未分类／边界邻域不足','1':'现代起伏较缓参考','2':'现代过渡形态参考','3':'现代起伏较强参考'},'counts_pixels':{str(i):int((cls==i).sum()) for i in range(4)},'cell_m':30,'ancient_registered_nodes':0,'historic_stability':'not_assessed','palaeochannels':'not_delineated','limits':['阈值为本项目探索性读图规则，未经过地貌调查验证；不等同台地/河漫滩/古河道。','排除邻域不完整的边缘，未在边界造假平地。','现代河道迁移/填筑敏感带待跨期图源配准，本批没有自动划区。','现代建设和植被影响未被平滑去除；两类坡度原产品继续保留。'],'input_sha256':meta['sources']['cop30.tif']['sha256'],'source_notice':meta['source_notice'],'vertical_reference':meta['vertical_reference']}
 dump('dual1/terrain-method.json',policy);return policy

def terrain_plate(data,meta):
 root=tag('svg',viewBox='0 0 1800 1260',role='img');add(root,'title').text='地形解释与建筑群阅读样板（建筑未配准）';add(root,'rect',width=1800,height=1260,fill='#faf9f5')
 txt(root,45,55,'LUOYANG / TERRAIN STUDY — PARALLEL TRACK',18,'#698171');txt(root,45,110,'新图：地形解释与建筑群样板',38);txt(root,45,151,'真实现代DSM + 文献建筑群分框。无古代定位点、无古河岸线、无旧图拉伸配准。',22,'#8b6946')
 im=add(root,'image',x=45,y=200,width=1100,height=1000,preserveAspectRatio='xMidYMid meet');im.set('{http://www.w3.org/1999/xlink}href','data:image/png;base64,'+base64.b64encode((OUT/'dual1/terrain-interpretation.png').read_bytes()).decode())
 txt(root,65,229,'北 ↑  /  EPSG:32649',19);txt(root,65,1162,'112.35–112.95°E / 34.50–34.95°N',19)
 for x,col,label in [(65,'#cfdfcd','起伏较缓'),(320,'#e4d9b9','过渡形态'),(570,'#b79d84','起伏较强')]:add(root,'rect',x=x,y=1194,width=22,height=17,fill=col);txt(root,x+32,1209,label+'（现代）',17)
 add(root,'path',d='M1185 200V1200',stroke='#c5d0c0',stroke_width=2);txt(root,1222,228,'建筑群：仅文献插图，未地理落位',22,'#925e3a')
 for yy,reg in zip([270,560,850],data['regions']):
  add(root,'rect',x=1220,y=yy,width=535,height=255,rx=12,fill='#f0f3e9',stroke='#d0d9c9');txt(root,1240,yy+35,reg['code']+'  '+reg['title'],22);examples=[c for c in data['changes'] if c['region']==reg['code']][:3]
  for xx,c in zip([1315,1480,1645],examples):
   gg=add(root,'g',transform=f'translate({xx} {yy+119}) scale(.57)');glyph(gg,0,0,c['glyph'],'#356f62');txt(root,xx,yy+190,c['name'].replace('〔城东〕',''),16,text_anchor='middle')
  txt(root,1240,yy+228,'图符尺寸不代表占地；右栏顺序无地理含义。',16,'#747e70')
 return ET.tostring(root,encoding='unicode')

def main():
 info=read('build-info.json');assert info.get('terrain_version') in ['v3.0-alpha.1','v3.0'],info.keys()
 protected={str(p.relative_to(OUT)):digest(p.read_bytes()) for folder in ['data','assets/sheets','terrain/v3.0'] for p in (OUT/folder).rglob('*') if p.is_file()}
 for name in ['assets/master-v24.svg','assets/master-v28-review.svg','v2.8.html','v2.9.html','v3.0.html','downloads/luoyang-v24-regional-atlas.pdf']:protected[name]=digest((OUT/name).read_bytes())
 data=json.loads((ROOT/'research/dual1/changes.json').read_text());entities=read('data/entities.json');byid={e['id']:e for e in entities};markers=read('data/markers.json');regions=read('data/regions.json')
 ev=read('data/research-v25.json')['evidence'];npas=read('data/network-v27.json')['passages'];trecs=read('data/chronology-v29.json')['records'];known={e['id'] for e in ev+npas+trecs};(OUT/'dual1').mkdir(exist_ok=True)
 for c in data['changes']:
  assert c['entity'] in byid and set(c['evidence'])<=known,c;assert c['ancient_lonlat'] is None
  c['name']=byid[c['entity']]['name'];c['map_id']=byid[c['entity']]['map_id'];c['quote']=byid[c['entity']]['source_quote'];c['source_ref']=byid[c['entity']]['source_ref']
 master,stamps=patch_master('assets/master-v24.svg',data,markers);integrated,_=patch_master('assets/master-v28-review.svg',data,markers)
 write('dual1/master-v210-work.svg',ET.tostring(master,encoding='unicode'));write('dual1/master-v210-integrated.svg',ET.tostring(integrated,encoding='unicode'))
 for reg in data['regions']:
  geo=dict(next(x for x in regions if x['code']==reg['code']));reg['original_region_bbox']=geo['bbox'];geo['bbox']=reg['focus_bbox'];reg['bbox']=geo['bbox'];reg['sheet']='dual1/'+reg['code']+'-v210.svg';write(reg['sheet'],panel_svg(master,geo,reg,data,markers))
 terrain=make_terrain();write('dual1/terrain-parallel.svg',terrain_plate(data,read('terrain/v3.0/metadata.json')))
 data['patch_verification']=stamps;data['terrain']=terrain;data['release_commit']=info['source_commit'];data['evidence_records']=[x for x in ev+npas+trecs if x['id'] in set(i for c in data['changes'] for i in c['evidence'])];dump('dual1/changes.json',data)
 report='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>双图并行第一批：改图报告</title><style>body{max-width:1200px;margin:30px auto;padding:25px;font:17px/1.8 sans-serif;color:#284a3c}td,th{border:1px solid #ccd4c6;padding:12px}table{border-collapse:collapse}img{width:100%}@media print{tr{break-inside:avoid}}</style><h1>双图并行第一批</h1><p>'+E(data['scope'])+'</p><h2>原文献工作图 v2.10</h2><table><tr><th>对象</th><th>旧画法</th><th>新画法</th><th>依据</th></tr>'
 report+=''.join('<tr>'+''.join('<td>'+E(str(x))+'</td>' for x in [c['id']+' '+c['name'],c['before'],c['after'],', '.join(c['evidence'])])+'</tr>' for c in data['changes'])+'</table>'
 for reg in data['regions']:report+=f'<h2>{E(reg["title"])}</h2><img src="../{reg["sheet"]}" alt="{E(reg["title"])}">'
 report+='<h2>地形解释（独立新图）</h2><img src="../dual1/terrain-parallel.svg"><p>'+E(terrain['rule'])+'</p>';report+=''.join('<p>'+E(s)+'</p>' for s in terrain['limits'])+'<h2>图源</h2>'+''.join('<p><a href="'+E(s['url'])+'">'+E(s['title'])+'</a>：'+E(s['verified'])+'</p>' for s in data['sources'])+'<p>'+E(terrain['source_notice'])+'</p></html>';write('downloads/dual1-report.html',report)
 buff=io.StringIO(newline='');writer=csv.writer(buff);writer.writerow(['change','entity','name','region','before','after','evidence','ancient_lonlat'])
 for c in data['changes']:writer.writerow([c['id'],c['entity'],c['name'],c['region'],c['before'],c['after'],';'.join(c['evidence']),''])
 write('downloads/dual1-changes.csv','\ufeff'+buff.getvalue());shutil.copyfile(ROOT/'dual1.html',OUT/'dual-map.html')
 index=(OUT/('pre-dual.html' if info.get('dual_batch_version')=='dual1' else 'index.html')).read_text(encoding='utf-8');write('pre-dual.html',index)
 runtime=re.search(r'<script src="\./([^\"]+-runtime\.js)"></script>',index);assert runtime
 boot=(OUT/runtime.group(1)).read_text();release=dict(read('release.json'),release='v3.1-alpha.1',web_version='0.8.0',entrypoint='dual-map.html',document_workmap='v2.10',description=data['scope'])
 body=(OUT/'dual1/master-v210-integrated.svg').read_bytes();asset='_assets/'+digest(body)[:20]+'-master-v210-integrated.svg';(OUT/asset).write_bytes(body)
 mapping=json.loads(re.search(r'window\.ATLAS_ASSETS=(.*?);\n',boot).group(1));mapping['assets/master-v28-review.svg']=asset
 boot=re.sub(r'window\.ATLAS_RELEASE=.*?;\n','window.ATLAS_RELEASE='+json.dumps(release,ensure_ascii=False)+';\n',boot,count=1);boot=re.sub(r'window\.ATLAS_ASSETS=.*?;\n','window.ATLAS_ASSETS='+json.dumps(mapping)+';\n',boot,count=1)
 bootpath='_assets/'+digest(boot.encode())[:20]+'-runtime.js';write(bootpath,boot);index=index.replace(runtime.group(1),bootpath,1);index=re.sub(r'<span class="brand-release">[^<]+</span>','<span class="brand-release">v3.1-alpha.1</span>',index,count=1)
 notice='<section id="dual-release-entry" class="c29-entry"><strong>双图并行：文献工作图 v2.10 ＋ 独立地形解释样板</strong><span>三片区已更新构件图符与时层说明；地形图不替代原图。</span><a href="./dual-map.html">打开双图工作台 ↗</a></section>'
 index=index.replace('<div class="v28-summary">',notice+'<div class="v28-summary">',1).replace('一张地图，读到最新研究','原图继续深化，双图读到最新研究');write('index.html',index);dump('release.json',release)
 with zipfile.ZipFile(OUT/'downloads/dual1-workpack.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in (OUT/'dual1').iterdir():
   if p.is_file():z.write(p,'dual1/'+p.name)
  for p in ['dual-map.html','downloads/dual1-report.html','downloads/dual1-changes.csv']:z.write(OUT/p,p)
  z.write(ROOT/'tools/dual_batch1.py','source/tools/dual_batch1.py');z.write(ROOT/'research/dual1/changes.json','source/research/dual1/changes.json');z.write(ROOT/'dual1.html','source/dual1.html')
 for path,h in protected.items():assert digest((OUT/path).read_bytes())==h,path
 info.update({'portal_version':'v3.1-alpha.1','web_version':'0.8.0','document_workmap_version':'v2.10','dual_batch_version':'dual1','dual_changes':len(stamps),'ancient_georeferenced_new':0})
 dump('dual1-build-check.json',{'protected_unchanged':len(protected),'changes':len(stamps),'geographic_ancient_points':0})
 info['files_sha256']={str(p.relative_to(OUT)):digest(p.read_bytes()) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='build-info.json'};dump('build-info.json',info)
 print('DUAL1: 10 changed SVG groups, 3 regions, modern terrain interpretation, prior assets unchanged:',len(protected))

if __name__=='__main__':main()
