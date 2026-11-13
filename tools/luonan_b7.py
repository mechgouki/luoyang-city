#!/usr/bin/env python3
"""Publish R11 as attributed reading groups, with no new located sites."""
from pathlib import Path
import copy,csv,json,re,zipfile,xml.etree.ElementTree as ET
import cairosvg
from dual_cartography import NS,C,load,dump,node,text,para,rect,path,svg,world,crop,write_svg,hall
from north_b4 import sha,fp,heading,render_atlas

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'_site'
INPUTS=[ROOT/'research/dual-b7/luonan-groups.json',ROOT/'research/dual-b7/luonan-river-markets.json']
GROUPS={
 'wards':('li_guizheng','li_guide','li_muhua','li_muyi'),
 'guesthouses':('guan_jinling','guan_yanran','guan_fusang','guan_yanzi'),
 'temples':('v3_guizheng','v3_puti'),
 'fish':('market_fish','house_xiaobaoyin'),
 'sitong':('market_sitong',),
}
ANCHORS={'wards':(5050,9680),'guesthouses':(7320,9645),'temples':(5050,10180),'fish':(5050,10540),'sitong':(7320,10600)}
SIDECARS=('house_xiaozhengde','v3_guizheng','v3_puti','market_fish','house_xiaobaoyin','market_sitong','fang_whiteelephant','fang_lion','v3_yong_huabiao')

def read_research():
 parts=[load(p) for p in INPUTS];sources={}
 for part in parts:
  for s in part['sources']:
   if s['id'] in sources:assert sources[s['id']]['url']==s['url']
   else:sources[s['id']]=s
 records=[e for p in parts for e in p['evidence']]
 assert len({e['id'] for e in records})==len(records)
 assert all(e['geographic_coordinates'] is None and e['source_region']=='R11' for e in records)
 assert parts[0]['region']['bbox']==parts[1]['region']['bbox']==[4100,8720,4350,2230]
 return {'version':'B7','base_commit':'9d0580332d635beb1d68963ae6c032598c2ff515',
  'scope':'洛南R11永桥、四夷馆里与市场','region':parts[0]['region'],
  'sources':list(sources.values()),'source_family_count':1,'evidence':records,
  'ancient_absolute_positions_added':0,'source_parts':[str(p.relative_to(ROOT)) for p in INPUTS],
  'notes':['516—528河阴之变前文献合成时层；不是单年快照。','339实体、179交互目标及原有锚点保留。',
   '馆里目录不构成南北次序；制度对应不构成一一对街。',
   '归正寺、菩提寺、两市与两坊保留非定位旁注；永桥沿用绘图锚点，没有新增交互点。',
   '原文、校补、解释和版面安排分别记录。']}

def changed_master(source,markers):
 root=ET.parse(source).getroot();wg=world(root);original=list(wg)
 original_bytes={id(n):ET.tostring(n) for n in original};wrapped=set();audit=[]
 assert len(markers)==179
 assert not any('bridge_yong' in m['ids'] or 'road_siyi' in m['ids'] for m in markers)
 for key,ids in GROUPS.items():
  m=next(m for m in markers if set(ids)==set(m['ids']))
  assert m['kind']=='group' and (m['x'],m['y'])==ANCHORS[key]

 def wrap(gid,children,ids,mode,xy):
  index=list(wg).index(children[0]);g=ET.Element('{'+NS+'}g',{
   'id':gid,'data-batch':'dual-b7','data-entity-ids':' '.join(ids),'data-footprint':'false',
   'data-locating-mode':mode,'style':'pointer-events:none'})
  node(g,'title').text='B7阅读组；原文字、图符与锚点保留；组内对象没有独立地址。'
  for child in children:
   wg.remove(child);g.append(child);wrapped.add(id(child))
  wg.insert(index,g)
  audit.append({'group_id':gid,'entities':list(ids),'mode':mode,'literary_xy':list(xy),'anchor_moved':False,
   'geographic_coordinates':None,'interactive_marker_present':mode!='bridge_annotation'})
  return g

 def bycls(name):return next(n for n in original if n.get('class')==name)
 def span(first,last):
  a=original.index(bycls(first));b=original.index(bycls(last));return original[a-1:b+1]

 g=wrap('luonan-wards-b7',span('wt164 tb164','wt169 tb169'),GROUPS['wards'],'group',ANCHORS['wards'])
 for dx in [-65,0,65]:hall(g,4515+dx,9740,43,C['gold'])
 text(g,4695,9720,'无序里名 · 不是四处独立院址',26,C['gold'])
 text(g,4695,9770,'里属、迁居与舍宅分别核对',24,C['muted'])
 g=wrap('luonan-guesthouses-b7',span('wt170 tb170','wt175 tb175'),GROUPS['guesthouses'],'group',ANCHORS['guesthouses'])
 for dx in [-65,0,65]:hall(g,6550+dx,9680,43,'#5d6d78')
 text(g,6730,9660,'居馆 → 赐宅：制度关系',26,'#5d6d78')
 text(g,6730,9710,'不据目录次序画成四组对街',24,C['muted'])
 text(g,6392,9807,'“三年”仅在吴人、北夷两段明记',24,C['gold'])

 # Existing bridge drawing is retained byte for byte, including its unscaled deck.
 start=next(i for i,n in enumerate(original) if n.tag=='{'+NS+'}rect' and n.get('x')=='6060' and n.get('y')=='8825')
 end=original.index(bycls('wt495 tb495'))
 g=wrap('luonan-bridge-b7',original[start:end+1],('bridge_yong','v3_yong_huabiao'),'bridge_annotation',(6100,9000))
 text(g,6250,9120,'门外四里；神龟属作颂年，建桥年未定',24,C['muted'])
 g=wrap('luonan-direction-b7',span('wt406 tb406','wt407 tb407'),('altar_yuanqiu',),'direction_reference',(6100,10810))
 node(g,'desc').text='保留南向参照，不表示坛址已定位，不画坛台平面。'

 panels=[
  ('temples',4330,10030,1440,255,'里内寺院 · 年未定 · 旁注',[
   'T51 归正寺：萧正德宅改寺，寺期未定',
   'T52 菩提寺：慕义里属；不补里内位置',
   '两寺同框仅供阅读，不能推出彼此邻接']),
  ('fish',4330,10385,1440,255,'归正里附见 · 里内无定位',[
   'P181 鱼鳖市：归正里居民自立巷市',
   'P194 萧宝夤旧宅：后迁城内永安里',
   '宝夤旧宅与萧正德宅改归正寺分别登记']),
  ('sitong',6370,10385,1800,255,'洛水南市场 · 旁注，框位不表路侧',[
   'P180 四通市〔俗称永桥市〕',
   '洛水南有明文；御道路侧与桥旁距离未记',
   '与归正里鱼鳖巷市分开，未证为同一市场']),
 ]
 for key,x,y,w,h,title,lines in panels:
  g=node(wg,'g',id='luonan-'+key+'-b7',data_batch='dual-b7',data_entity_ids=' '.join(GROUPS[key]),
   data_footprint='false',data_locating_mode='nonspatial_annotation',style='pointer-events:none')
  node(g,'title').text='文字旁注组；框是阅读版面，不是建筑、院界或市场范围。'
  rect(g,x,y,w,h,'#f7f5ed',C['line'],2,10)
  text(g,x+25,y+46,title,30,C['green'],weight=500)
  for j,line in enumerate(lines):text(g,x+25,y+103+j*54,line,26 if j<2 else 23,C['ink'] if j<2 else C['muted'])
  audit.append({'group_id':'luonan-'+key+'-b7','entities':list(GROUPS[key]),'mode':'nonspatial_annotation',
   'literary_xy':list(ANCHORS[key]),'anchor_moved':False,'geographic_coordinates':None,'interactive_marker_present':True})
 # Original children either remain direct children or are wrapped without changes.
 assert all(ET.tostring(n)==original_bytes[id(n)] for n in original)
 for batch,count in [('dual-b1',7),('dual-b2',8),('dual-b4',4),('dual-b5',11),('dual-b6',20)]:
  assert sum(n.get('data-batch')==batch for n in root.iter())==count,batch
 assert sum(n.get('id')=='west-glyphs-b3' for n in root.iter())==1
 for n in root:
  if n.get('class')=='wt497 tb497':
   for child in list(n):n.remove(child)
   n.text='北魏洛阳 · 文献复原工作图 B7'
 result={'reading_groups_changed':7,'original_children_preserved':len(original),'old_children_wrapped':len(wrapped),
  'anchors_moved':False,'new_ancient_coordinates':0,'new_individual_site_glyphs':0,'new_interactive_targets':0,
  'source_sha256':sha(source),'changes':audit,'nonspatial_sidecars_preserved':list(SIDECARS),'original_target_count':179,
  'bridge_drawing_anchor':[6100,9000],'bridge_interactive_marker_present':False}
 node(root,'metadata').text=json.dumps(result,ensure_ascii=False)
 return root,result

def card(r,x,y,w,h,title,body,size=25):
 rect(r,x,y,w,h,'#eef1e7',C['line'],2,9)
 text(r,x+26,y+47,title,29,C['green'],weight=500)
 return para(r,x+26,y+94,body,(w-52)/size,size)

def literary_plate(master,reg,archive=False):
 r=svg(2200,1560,'L10 洛南 / '+('v2.4封存同区' if archive else 'B7文献阅读图'))
 heading(r,'LUOYANG / L10 / '+('ARCHIVE' if archive else 'B7'),'永桥以南：馆、里与市场','516—528河阴之变前合成时层；↑ 北；文献锚点与旁注框不提供实测位置。')
 rect(r,75,240,2050,1060,'#f0f2e9',C['line'],2,9);crop(master,r,92,257,2016,1026,reg['bbox'])
 for x,w,title,body in [
  (75,660,'目录与道路','四馆道东、四里道西；内部无序，制度对应不证明一一对街。'),
  (770,660,'两市分别查','鱼鳖市属归正里巷市；四通市仅明确洛水南，俗称不作桥旁坐标。'),
  (1465,660,'时层与方向','寺期未定继续旁注；圜丘只作南向参照，伊水河道未据此复原。')]:
  card(r,x,1320,w,170,title,body,22)
 text(r,75,1530,('封存母图原样裁切。' if archive else '7组阅读表达；成员不拆点，旧图符与交互锚点保留。')+' 框线、文字排布与类型图符均不代表院界或比例。',21,C['muted'])
 return r

def institutions_plate():
 r=svg(2200,1560,'B7 四馆四里安置关系')
 heading(r,'B7 / 制度与目录','从居馆到赐宅：四组关系，分别阅读','表格展示文献对应，不代表东西街景、南北次序、同步迁居或普遍实施年限。')
 cols=[105,475,900,1360];ys=[355,535,715,895]
 for x,label in zip(cols,['人群称谓〔按原文〕','先居馆','赐宅里','明写的时间条件']):text(r,x,285,label,27,C['green'],weight=500)
 rows=[('吴人','金陵馆','归正里','三年已后'),('北夷','燕然馆','归德里','三年已后'),('东夷','扶桑馆','慕化里','本段未重写“三年”'),('西夷','崦嵫馆','慕义里','本段未重写“三年”')]
 for y,row in zip(ys,rows):
  rect(r,75,y-45,2050,145,'#eef1e7',C['line'],1,8)
  for x,s in zip(cols,row):text(r,x,y+10,s,31,C['ink'])
  path(r,f'M690 {y}H835 M820 {y-10}L835 {y}L820 {y+10}',C['gold'],3)
  text(r,750,y+53,'安置叙述',21,C['gold'],'middle')
 card(r,75,1065,1005,355,'道路关系与目录顺序','四馆在御道东、四里在御道西，有正文与校补层需要分别查阅。馆里名单不确定内部南北次序，也不证明每馆与对应里恰好隔街相对。',26)
 card(r,1120,1065,1005,355,'季节入侍与落户分开','“雁臣”秋来春去描述季节性入侍；不能据此让所有北来人员长期住入归德里。万余家等集合叙述不换成坊数、院数或住宅密度。',26)
 text(r,75,1510,'四馆补文、道西“馆／里”校改及周氏整理层见LG逐条记录；不是两份独立史料的计票。',23,C['muted'])
 return r

def markets_plate():
 r=svg(2200,1560,'B7 市场、通行与旁注范围')
 heading(r,'B7 / 空间关系','两个市场：所属与方向提供不同信息','各面板独立阅读；没有把洛水南、归正里内、永桥俗称转换成精确市场轮廓。')
 card(r,75,245,1005,520,'01  归正里 → 鱼鳖巷市','归正里居民自立巷市，以水族口味得名。吴人坊是该段归正里俗称；鱼鳖市不能继承卷二段首小市北张景仁现宅的地点。\n\n萧宝夤曾获归正里宅，后迁永安里；旧宅附见与市场记录分开，不据人物并列确定巷市地址。',27)
 card(r,1120,245,1005,520,'02  洛水南 → 四通市','四通市另立于洛水南，民间称永桥市。该名称没有给出市场距桥多远、御道哪一侧或市场边界。\n\n当前保留独立记录；没有把四通市与鱼鳖市合并，也没有画出彼此连通的市场街道。',27)
 card(r,75,805,1005,590,'03  宣阳门 → 永桥 → 洛南','宣阳门外四里至洛水，永桥为浮桥。里数的具体测量端点、路线与图示比例未定。神龟作颂是文辞活动年代，不能定为建桥年。\n\n两岸华表为桥附记；原文高度与注引根数分别保留，不据此量画立面、桥长、浮舟数量或古河宽。',27)
 card(r,1120,805,1005,590,'04  御道、两坊与圜丘','白象、狮子两坊明记永桥南、道东；只保留关系旁注，边界与内部位置未记。狮子到京与遣归事件晚于工作时层，不画成516—528年实有狮子的景观。\n\n四夷馆里处永桥南、圜丘北、伊洛之间。圜丘只作南向参照；不由这句补出祭坛位置或伊水古河道。',27)
 text(r,75,1510,'主图的旁注框是阅读安排；其中四通市框位在右侧，不表示它在御道东。',24,C['gold'])
 return r

def layers_plate():
 r=svg(2200,1560,'B7 人物迁居、寺院与动物时层')
 heading(r,'B7 / 年代与对象','到来、居馆、筑宅与舍宅：不共用一个日期','每一事件单独承接时间证据；目录排列与同段叙事不能补出未记的建寺或建坊年。')
 rows=[
  ('萧正德与归正寺','正文正光四年到来；周注另引三年','先馆后宅；宅转寺没有独立纪年','不以523加三年推出526建寺；“后”为周校补'),
  ('萧宝夤与两处宅','归正里获宅，世宗朝又获永安里宅','516—528语境中的归正里为旧宅附见','不能与萧正德合并，也不能将其旧宅改作归正寺'),
  ('菩提寺','西域胡人所立；慕义里属','寺院成立年未定','神异故事、人物活动与里人口不能代替营建年代'),
  ('白象坊与狮子坊','白象509入贡，先养乘黄曹；后迁坊','狮子永安末到京；531诏遣归，途中被杀','509不是建坊年；狮子晚事不进入河阴前景观'),
  ('永桥与华表','神龟为常景作颂的叙述年代','桥的创建年、华表独立营建年未明','过桥行为不还原桥面宽度、桥墩或固定木梁桥'),
 ]
 for i,(name,dated,undated,limit) in enumerate(rows):
  y=245+i*211;rect(r,75,y,2050,190,'#eef1e7',C['line'],2,9)
  text(r,110,y+42,name,29,C['green'],weight=500)
  text(r,110,y+91,dated,26,C['ink']);text(r,1100,y+91,undated,25,C['gold'])
  text(r,110,y+148,limit,25,C['muted'])
 text(r,75,1390,'校读层保留：正光／景明、三年／四年、補“后”与否，不把后世注引折叠成统一正文。',25,C['green'])
 text(r,75,1510,'未定年与后出事件仍可检索，但不自动变成盛时母图上同时存在的建筑和景观。',23,C['muted'])
 return r

def evidence_plate(data,prefix):
 es=[e for e in data['evidence'] if e['id'].startswith(prefix)];assert len(es)<=24
 name='四馆四里与归正寺' if prefix=='LG' else '永桥、市场与旁注'
 r=svg(2200,1560,'B7 '+name+'证据索引')
 heading(r,'B7 / 逐条依据',name+'：查到具体文本层','原文、校读、采用解释、画法和限制分栏保存；电子整理本属于同一古籍来源家族。')
 rows=(len(es)+1)//2
 for i,e in enumerate(es):
  x=75+(i//rows)*1050;y=245+(i%rows)*102
  rect(r,x,y,1005,89,'#eef1e7',C['line'],1,6)
  text(r,x+18,y+35,e['id']+' · '+e['title'],23,C['ink'])
  text(r,x+18,y+67,'采用 '+e['quote_source']+' · 所属、时层与显示限制单列',20,C['muted'])
 used={sid for e in es for sid in e['sources']};ss=[s for s in data['sources'] if s['id'] in used]
 text(r,75,1220,'可复核来源',28,C['green'],weight=500)
 for i,s in enumerate(ss):
  x=75+(i%2)*1050;y=1272+(i//2)*74
  text(r,x,y,s['id']+' · '+s['title'],21,C['muted']);text(r,x,y+31,s['url'],18,C['muted'])
 text(r,75,1510,'在线逐条查阅：https://mechgouki.github.io/luoyang-city/dual-luonan.html · 2026-11-13',21,C['muted'])
 return r

def main():
 data=read_research();info=load(SITE/'build-info.json')
 assert info.get('southeast_b6',{}).get('records')==34
 assert (SITE/'source-continuity/metadata.json').is_file()
 assert not (SITE/'dual-luonan.html').exists(),'Rebuild preceding stages before B7'
 protected={str(p.relative_to(SITE)):sha(p) for p in SITE.rglob('*') if p.is_file() and p.name not in ['build-info.json','index.html','v3.0-dual.html','release.json']}
 master,audit=changed_master(SITE/'assets/master-dual-b6-southeast.svg',load(SITE/'data/markers.json'))
 master_file=SITE/'assets/master-dual-b7-luonan.svg';write_svg(master_file,master)
 maps=SITE/'dual/maps';archive=ET.parse(SITE/'assets/master-v24.svg').getroot()
 write_svg(maps/'L10.svg',literary_plate(master,data['region']))
 write_svg(maps/'L10-archive.svg',literary_plate(archive,data['region'],True))
 for name,fn in [('institutions',institutions_plate),('markets',markets_plate),('layers',layers_plate)]:write_svg(maps/('LN7-'+name+'.svg'),fn())
 for prefix,name in [('LG','groups'),('LR','river')]:write_svg(maps/('LN7-evidence-'+name+'.svg'),evidence_plate(data,prefix))
 data['source_commit']=info['source_commit'];data['drawing_audit']=audit;dump(SITE/'dual/luonan-b7.json',data)
 (SITE/'dual-luonan.html').write_bytes((ROOT/'web/luonan-b7.html').read_bytes())
 (SITE/'luonan-b7.js').write_bytes((ROOT/'web/luonan-b7.js').read_bytes())
 with (SITE/'downloads/dual-luonan-b7-evidence.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['编号','分区','主题','实体ID','引文来源','原文','采用解释','画法','限制','时层'])
  for e in data['evidence']:w.writerow([e['id'],e['source_region'],e['title'],';'.join(e['entities']),e['quote_source'],e['quote'],e['reading'],e['drawing'],e['limit'],e.get('temporal_note','')])
 plates=[maps/'L10.svg',maps/'LN7-institutions.svg',maps/'LN7-markets.svg',maps/'LN7-layers.svg',SITE/'source-continuity/edition-summary.svg',SITE/'source-continuity/continuity-summary.svg',maps/'LN7-evidence-groups.svg',maps/'LN7-evidence-river.svg']
 render_atlas(plates,SITE/'downloads/dual-luonan-b7-atlas.pdf')
 cairosvg.svg2png(url=str(maps/'LN7-institutions.svg'),write_to=str(SITE/'dual/luonan-b7-preview.png'),output_width=1800)
 cairosvg.svg2png(url=str(maps/'L10.svg'),write_to=str(SITE/'dual/luonan-b7-map.png'),output_width=2400)
 index=(SITE/'index.html').read_text();match=re.search(r'<script src="\./([^"]+-runtime\.js)"></script>',index);assert match
 boot=(SITE/match.group(1)).read_text();m=re.search(r'window\.ATLAS_ASSETS=(.*?);\n',boot);assert m
 mapping=json.loads(m.group(1));mapping['assets/master-v28-review.svg']=fp(master_file.name,master_file.read_bytes())
 boot=boot[:m.start(1)]+json.dumps(mapping,ensure_ascii=False)+boot[m.end(1):];index=index.replace(match.group(1),fp('runtime.js',boot.encode()),1)
 banner='<section id="luonan-b7-entry" style="margin:16px 0;padding:23px;border:1px solid #b9c5ad;background:#eaf0e3;border-radius:8px"><h2>洛南馆里与市场 · B7</h2><p>四馆四里的安置关系、两处市场、永桥通行与宅寺年代逐项核对。历史图线追到日方具体图幅的版次与底图注记。</p><p><a href="./dual-luonan.html#map?id=LG01">进入洛南联读 ↗</a>　<a href="./source-continuity.html">查看图源年代核对 ↗</a>　<a href="./downloads/dual-luonan-b7-atlas.pdf">下载本批图册 ↗</a></p></section>'
 assert index.count('id="southeast-b6-entry"')==1
 index=index.replace('<section id="southeast-b6-entry"',banner+'<section id="southeast-b6-entry"',1)
 index=index.replace('<nav aria-label="主导航" class="topnav">','<nav aria-label="主导航" class="topnav"><a href="./dual-luonan.html">洛南B7 ↗</a>',1)
 js=fp('luonan-main-b7.js',(ROOT/'web/luonan-main-b7.js').read_bytes());index=index.replace('</body>',f'<script defer src="./{js}"></script></body>')
 (SITE/'index.html').write_text(index);(SITE/'v3.0-dual.html').write_text(index)
 release=load(SITE/'release.json');release['extensions']=sorted(set(release.get('extensions',[])+['dual-luonan-b7','source-continuity-b7']));release['current_milestone']='B7 洛南馆里与市场、图源年代核对';dump(SITE/'release.json',release)
 assert all(sha(SITE/p)==h for p,h in protected.items()),'B7 modified a protected prior resource'
 dump(SITE/'dual/luonan-b7-preservation.json',{'protected_files':len(protected),'protected_unchanged':True,'sha256':protected})
 with zipfile.ZipFile(SITE/'downloads/dual-luonan-b7-package.zip','w',zipfile.ZIP_DEFLATED) as z:
  docs=[ROOT/'docs/dual-luonan-groups-b7-research.md',ROOT/'docs/dual-luonan-river-b7-research.md',ROOT/'docs/source-continuity-b7-research.md',ROOT/'docs/dual-luonan-b7-release-notes.md']
  for p in plates+[maps/'L10-archive.svg',master_file,SITE/'dual/luonan-b7.json',SITE/'downloads/dual-luonan-b7-evidence.csv',SITE/'downloads/dual-luonan-b7-atlas.pdf']+docs:
   z.write(p,('docs/'+p.name) if p.is_relative_to(ROOT/'docs') else str(p.relative_to(SITE)))
  for p in sorted((SITE/'source-continuity').rglob('*')):
   if p.is_file() and p not in plates:z.write(p,str(p.relative_to(SITE)))
 info['luonan_b7']={'source_commit':info['source_commit'],'records':len(data['evidence']),'regions':['L10'],
  'reading_groups_changed':7,'new_individual_site_glyphs':0,'nonspatial_sidecars_preserved':list(SIDECARS),
  'new_ancient_coordinates':0,'new_interactive_targets':0,'previous_release_preserved':'B1+B2+B3+B4+B5+B6','protected_files':len(protected),'atlas_pages':8}
 info['files_sha256']={str(p.relative_to(SITE)):sha(p) for p in sorted(SITE.rglob('*')) if p.is_file() and p.name!='build-info.json'};dump(SITE/'build-info.json',info)
 print('Built B7:',len(data['evidence']),'evidence, 7 reading groups, L10, eight-page atlas; protected',len(protected))

if __name__=='__main__':main()
