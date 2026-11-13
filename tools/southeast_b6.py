#!/usr/bin/env python3
"""Continue R08/R09 with attributed constraints; preserve earlier map releases."""
from pathlib import Path
import csv,json,re,zipfile,xml.etree.ElementTree as ET
import cairosvg
from dual_cartography import NS,C,load,dump,node,text,para,rect,path,svg,world,crop,write_svg
from north_b4 import sha,fp,heading,gate_icon,render_atlas
from west_roads_b5 import type_icon

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'_site'
INPUTS=[ROOT/'research/dual-b6/southeast-inner.json',ROOT/'research/dual-b6/southeast-outer.json']
NODES={
 'ic_daoguan':('wnode105',7140,4450,'P52 导官署','两署道北 · 西序属注引','office',False),
 'ic_taicang_wei':('wnode106',7490,4450,'P51 太仓署〔北魏〕','与晋太仓旧址分开','office',False),
 'ic_zhaoyi':('wnode107',7520,4990,'T06 昭仪尼寺','寺期未定 · 池非翟泉','temple',True),
 'ic_songming':('wnode108',7160,5940,'T12 嵩明寺','寺期未定 · 路侧未记','temple',True),
 'ic_xiufan':('wnode109',7510,5940,'T08 修梵寺','寺期未定 · 御道北','temple',True),
 'ic_jinglin_garden':('wnode110',7300,6450,'P64 景林寺西园','寺西 · 与御道关系未记','garden',False),
 'ic_jinglin':('wnode111',7650,6450,'T09 景林寺','寺期未定 · 御道东','temple',True),
 'v2_zhuangyan':('wnode123',8300,4500,'T31 庄严寺','寺期未定 · 租场回指待辨','temple',True),
 'v2_qintaishangjun':('wnode124',9900,4480,'T32 秦太上君寺','追福寺 · 塔期另记','temple',False),
 'v2_zhengshi':('wnode125',8450,5060,'T33 正始寺','道南采用周校 · 范正文西','temple',False),
 'office_dianyu':('wnode126',9070,5060,'P123 典虞曹','敬义里属 · 邻接未记','office',False),
 'v2_pingdeng':('wnode127',8510,5880,'T34 平等寺','寺与532始造塔分时','temple',False),
 'tomb_suqin':('wnode128',9330,5895,'P131 苏秦冢〔传称〕','里西北角 · 墓主未核','tomb',False),
 'v2_baoming':('wnode129',9900,5915,'T26 宝明寺','冢旁 · 前期年代依同名联接','temple',False),
 'market_small':('wnode130',10990,5935,'P132 洛阳小市','孝义里东 · 市界未定','market',False),
 'v2_jingning':('wnode131',8660,6430,'T35 景宁寺','分宅立寺 · 不等于全宅','temple',False),
 'v2_jianzhong':('wnode132',9750,6430,'T36 杨氏宅〔后建中〕','531后转寺 · 同名不强合','house',False),
}
GATES={'gate_dongyang':(7800,4750),'gate_qingyang':(7800,6100),'gate_kaiyang':(7500,6800)}
SIDECARS=('ic_hutong','ic_yuanhui','ic_yishou','ic_guangming','v2_guijue')

def read_research():
 parts=[load(p) for p in INPUTS]
 sources={}
 for part in parts:
  for s in part['sources']:
   if s['id'] in sources:assert sources[s['id']]['url']==s['url']
   else:sources[s['id']]=s
 records=[e for p in parts for e in p['evidence']]
 assert len({e['id'] for e in records})==len(records)
 assert all(e['geographic_coordinates'] is None for e in records)
 return {'version':'B6','base_commit':'6e9d817fac023a70c2d5d8be237c1d245f3f4880',
  'scope':'城东南R08门内与R09门外联读','regions':[p['region'] for p in parts],
  'sources':list(sources.values()),'source_family_count':1,'evidence':records,
  'ancient_absolute_positions_added':0,'source_parts':[str(p.relative_to(ROOT)) for p in INPUTS],
  'notes':['516—528河阴之变前文献合成时层；非单年快照。','原ID、锚点和179个点击目标保留。',
   '原文、校读、解释与显示安排分别记录；同里或邻近不自动给出相对方位。',
   '愿会、宜寿、光明、胡统及归觉沿用关系组或旁注，不新增定位节点。']}

def symbol(parent,x,y,kind,undated):
 if kind in ['temple','house']:return type_icon(parent,x,y,kind,undated)
 g=node(parent,'g',transform=f'translate({x} {y})')
 if kind=='office':
  co='#5d6d78';path(g,'M-51 -7L0 -35L51 -7 M-44 38H44',co,4)
  rect(g,-37,-6,74,40,C['paper'],co,3);path(g,'M-21 -2V32 M21 -2V32 M-11 8H11V33',co,2)
 elif kind=='garden':
  co=C['green'];path(g,'M-29 5V38 M25 -7V38 M-49 40H47',co,3)
  node(g,'ellipse',cx=-29,cy=-11,rx=22,ry=28,fill='none',stroke=co,stroke_width=3)
  node(g,'ellipse',cx=25,cy=-24,rx=25,ry=33,fill='none',stroke=co,stroke_width=3)
 elif kind=='market':
  co=C['gold']
  for dx in [-43,5]:
   path(g,f'M{dx} -8H{dx+38}L{dx+44} 6H{dx-6}Z',co,3)
   rect(g,dx,7,38,31,C['paper'],co,2);path(g,f'M{dx-2} 42H{dx+41}',co,3)
 elif kind=='tomb':
  co=C['ink'];path(g,'M-51 30C-38 -34 38 -34 51 30 M-59 34H59',co,3)
 else:raise ValueError(kind)
 return g

def node_group(eid,entry):
 cls,x,y,label,note,kind,undated=entry
 g=ET.Element('{'+NS+'}g',{'class':cls,'data-entity-id':eid,'data-batch':'dual-b6',
  'data-footprint':'false','data-temporal-display':'undated' if undated else ('conditional-identity' if eid=='v2_baoming' else ('house-before-temple' if kind=='house' else 'composite')),'style':'pointer-events:none'})
 node(g,'title').text=label+'；类型图符，原锚点保留。'+note+'。'
 symbol(g,x,y,kind,undated)
 color=C['gold'] if kind in ['house','market'] else ('#5d6d78' if kind=='office' else C['green'])
 text(g,x,y+78,label,27,color,'middle',500)
 text(g,x,y+114,note,19,C['muted'],'middle')
 return g

def changed_master(source,markers):
 root=ET.parse(source).getroot();wg=world(root);before=[ET.tostring(c) for c in wg]
 changed=set();audit=[]
 for eid,entry in NODES.items():
  cls,x,y,*_=entry;m=next(m for m in markers if eid in m['ids'])
  assert m['kind']=='node' and (m['x'],m['y'])==(x,y),eid
  old=[c for c in wg if c.get('class')==cls];assert len(old)==1,cls
  index=list(wg).index(old[0]);wg.remove(old[0]);wg.insert(index,node_group(eid,entry));changed.add(index)
  audit.append({'entity_id':eid,'literary_xy':[x,y],'anchor_moved':False,'type':entry[5],'tower_added_to_master':False,'identity_assumption_required_for_dating':eid=='v2_baoming','geographic_coordinates':None})
 assert all(ET.tostring(c)==before[i] for i,c in enumerate(wg) if i not in changed)
 gate_group=node(wg,'g',id='southeast-glyphs-b6',style='pointer-events:none')
 for eid,(x,y) in GATES.items():
  m=next(m for m in markers if eid in m['ids']);assert m['kind']=='gate' and (m['x'],m['y'])==(x,y)
  g=node(gate_group,'g',data_entity_id=eid,data_batch='dual-b6',data_footprint='false')
  node(g,'title').text='既有城门通行类型，楼层与实际立面未定；青／清阳共用原门ID。'
  gate_icon(g,x,y,False,.8)
  audit.append({'entity_id':eid,'literary_xy':[x,y],'anchor_moved':False,'type':'gate','storeys':None,'geographic_coordinates':None})
 for batch,count in [('dual-b1',7),('dual-b2',8),('dual-b4',4),('dual-b5',11)]:
  assert sum(n.get('data-batch')==batch for n in root.iter())==count,batch
 assert sum(n.get('id')=='west-glyphs-b3' for n in root.iter())==1
 assert not any(n.get('data-entity-id') in SIDECARS and n.get('data-batch')=='dual-b6' for n in root.iter())
 for n in root:
  if n.get('class')=='wt497 tb497':
   for child in list(n):n.remove(child)
   n.text='北魏洛阳 · 文献复原工作图 B6'
 result={'type_groups_changed':len(audit),'nodes_replaced':len(NODES),'gate_symbols_added':len(GATES),
  'anchors_moved':False,'new_ancient_coordinates':0,'source_sha256':sha(source),'changes':audit,
  'nonspatial_sidecars_preserved':list(SIDECARS),'original_target_count':179}
 node(root,'metadata').text=json.dumps(result,ensure_ascii=False)
 return root,result

def card(r,x,y,w,h,title,body,size=25):
 rect(r,x,y,w,h,'#f0f2e8',C['line'],2,9)
 text(r,x+26,y+48,title,29,C['green'],weight=500)
 para(r,x+26,y+96,body,(w-52)/size,size)

def literary_plate(master,reg,archive=False):
 inner=reg['source_region']=='R08';lid='L08' if inner else 'L09'
 r=svg(2200,1560,lid+' 城东南 / '+('v2.4封存同区' if archive else 'B6文献类型图'))
 title='城东南门内：寺、署与水池' if inner else '城东南门外：里、寺与市场'
 heading(r,'LUOYANG / '+lid+' / '+('ARCHIVE' if archive else 'B6'),title,'516—528河阴之变前合成时层；↑ 北；文献锚点不是实测坐标。')
 if inner:
  rect(r,75,240,915,1200,'#f0f2e9',C['line'],2,9);crop(master,r,92,257,881,1166,reg['bbox'])
  card(r,1030,240,1095,330,'01  门道与类型','昭仪在东阳门内御道南；两署在道北。修梵在青／清阳门内道北，景林在开阳门内道东。寺期未明继续用空心类型。')
  card(r,1030,600,1095,380,'02  水池、园与未定位关系','昭仪池与翟泉分开；愿会仅明确在池西南，宜寿里、光明寺按回指与宅寺关系相接，继续留在关系组。景林寺西有园，但园与御道路侧未详；院墙、池岸、园界不补绘。')
  card(r,1030,1010,1095,430,'03  正文、注引与回指','两署东西次序须标明注引层。嵩明在修梵西，路侧未独立明记。永和里“寺北”按近文解释，并保留回指层级；里内宅第不展开成街址。')
 else:
  rect(r,75,240,1370,1200,'#f0f2e9',C['line'],2,9);crop(master,r,92,257,1336,1166,reg['bbox'])
  card(r,1485,240,640,330,'01  同里与路侧','正始道南沿用周校；范正文仍为西。典虞曹只确证敬义里属，不能把现图位置读作正始东邻。',24)
  card(r,1485,600,640,380,'02  冢旁与里角','孝义里西北角属于传称苏秦冢；宝明只得冢旁。宝明前期年代依赖两条同名记录的联接，尚未独立证实。',24)
  card(r,1485,1010,640,430,'03  宅寺与晚塔','平等寺本体与532年始造塔分层。景宁分宅立寺，城东建中保留杨氏宅型；归觉继续留在殖货里非定位群组。',24)
 text(r,75,1510,('封存母图原样裁切。' if archive else '既有ID与锚点保留；类型图符不代表院界、实际平面或比例。')+' 旁注与无序成员不新增定位点。',22,C['muted'])
 return r

def small_box(r,x,y,w,label):
 rect(r,x,y,w,65,C['paper'],C['line'],1,7);text(r,x+w/2,y+43,label,25,C['ink'],'middle')

def arrow(r,x1,y,x2,label):
 path(r,f'M{x1} {y}H{x2} M{x2-14} {y-9}L{x2} {y}L{x2-14} {y+9}',C['gold'],3)
 text(r,(x1+x2)/2,y-14,label,20,C['gold'],'middle')

def relations_plate():
 r=svg(2200,1660,'B6 门内外关系与不成立的推论')
 heading(r,'B6 / 空间关系','同里、邻近与方向：分别核对','各面板独立阅读；连线长度、框大小与列对齐均没有地理比例意义。')
 for x in [75,1120]:
  for y in [245,685,1125]:rect(r,x,y,1005,400,'#edf0e5',C['line'],2,9)
 text(r,105,295,'01  昭仪池与寺里关系组',29,C['green'],weight=500)
 small_box(r,110,330,260,'昭仪池');small_box(r,675,330,350,'愿会寺〔旁注〕');arrow(r,390,364,650,'西南')
 para(r,110,450,'宜寿里“寺南”暂按愿会回指；光明承段宅改寺，均留关系组。昭仪池明确非翟泉；石崇家池仍标赵逸所说。',35,25)
 text(r,1150,295,'02  敬义里：同属，不等于东邻',29,C['green'],weight=500)
 small_box(r,1155,330,385,'正始寺');small_box(r,1660,330,385,'典虞曹')
 text(r,1600,445,'两者均属敬义里',27,C['green'],'middle')
 para(r,1155,498,'正文未给两者相对方位。正始道南是本项目沿用周校的读法；范正文西与异本南分别保存。',35,25)
 text(r,105,735,'03  修梵、嵩明与永和里',29,C['green'],weight=500)
 small_box(r,110,770,330,'嵩明寺');small_box(r,705,770,330,'修梵寺');arrow(r,460,804,680,'向东')
 para(r,110,885,'嵩明只得修梵西，不能自动继承道北。永和里“寺北”按近文回指修梵，但标为解释；里内诸宅仍是无序成员。',35,25)
 text(r,1150,735,'04  孝义里角与苏秦冢旁',29,C['green'],weight=500)
 small_box(r,1155,770,430,'苏秦冢〔传称〕');small_box(r,1660,770,385,'宝明寺')
 text(r,1370,884,'冢：里西北角',25,C['green'],'middle');text(r,1850,884,'寺：冢旁',25,C['green'],'middle')
 para(r,1155,942,'寺不自动继承里角。宝明前期年代依赖两条同名记录的联接；冢旁条本身没有前528纪年。墓主亦未核。',35,25)
 text(r,105,1175,'05  景林寺与寺西园',29,C['green'],weight=500)
 small_box(r,110,1210,330,'寺西园');small_box(r,705,1210,330,'景林寺');arrow(r,460,1244,680,'向东')
 para(r,110,1325,'景林在开阳门内御道东。寺西之园与御道的关系未记，不据图上距离补出园越过御道、面积或园墙。',35,25)
 text(r,1150,1175,'06  门外里数，不作像素尺',29,C['green'],weight=500)
 para(r,1155,1230,'东阳门外：庄严一里，秦太上君二里。青／清阳门外：平等二里，景宁与孝义里三里。',35,26)
 para(r,1155,1380,'量距端点与路线未详；里数不换成图符间距，也不证明院址在同一直线上。',35,25)
 text(r,75,1610,'青／清阳为同一既有城门的文本异写；关系组锚点仅供阅读，不增加历史地理坐标。',23,C['muted'])
 return r

def layers_plate():
 r=svg(2200,1560,'B6 宅寺塔时层与文本年代')
 heading(r,'B6 / 时间与构件','寺院、宅第与塔：使用不同的时间证据','516—528河阴之变前是本项目合成语境；出现一个年号不等于给整处建筑群定年。')
 rows=[
  ('秦太上君寺','为太后之母追福','五层塔记述另存','没有单记塔的完工年，主图本批不加塔'),
  ('平等寺','527年活动支持寺本体','532始造五层塔','完工533／534的周、范校读分列，均晚于工作层'),
  ('归觉〔殖货里组〕','主图继续刘胡兄弟宅','永安中舍宅为寺','528—530叙事晚于河阴前断面；未拆出独立寺点'),
  ('景宁与城东建中','分宅立景宁寺','531后杨氏宅转建中','分宅不等于全宅；城东、城内建中保持不同记录'),
 ]
 for i,(name,early,later,limit) in enumerate(rows):
  y=245+i*185
  rect(r,75,y,2050,165,'#edf0e5',C['line'],2,9)
  text(r,110,y+43,name,28,C['green'],weight=500)
  text(r,110,y+93,early,25,C['ink']);text(r,915,y+93,later,25,C['gold'])
  text(r,110,y+141,limit,24,C['muted'])
 for x in [75,1120]:rect(r,x,1000,1005,445,'#f2eddf',C['line'],2,9)
 text(r,110,1056,'名物与建筑构件分开',30,C['green'],weight=500)
 for i,line in enumerate(['愿会“五重”指神桑，不是五层塔。','胡统五重塔随旁注，不新增寺院坐标。','修梵金刚是造像，不据此画塔。','景林房内小型祇洹精舍不另造寺址。']):text(r,110,1130+i*75,line,25,C['muted'])
 text(r,1155,1056,'铭文、传记与建寺日期分开',30,C['green'],weight=500)
 for i,line in enumerate(['光明的晋代佛像铭不是建寺纪年。','愿会砍桑：永熙时段属周注推定。','景林石铭未记年，普泰初属任官语境。','寺院、园与石铭各自营建年月仍未定。']):text(r,1155,1130+i*75,line,25,C['muted'])
 text(r,75,1510,'昭仪、愿会、光明、修梵、嵩明、景林继续保留寺期未定；后出塔构件不自动进入盛时母图。',23,C['muted'])
 return r

def evidence_plate(data,region):
 es=[e for e in data['evidence'] if e['source_region']==region]
 assert len(es)<=22
 name='门内 R08' if region=='R08' else '门外 R09'
 r=svg(2200,1560,'B6 '+name+' 证据索引')
 heading(r,'B6 / 逐条依据',name+'：正文、校读与采用解释','完整引文与限制见专题页；不同校注不是不同原书的独立互证。')
 rows=(len(es)+1)//2
 for i,e in enumerate(es):
  x=75+(i//rows)*1050;y=245+(i%rows)*84
  rect(r,x,y,1005,73,'#eff1e7',C['line'],1,6)
  text(r,x+18,y+31,e['id']+' · '+e['title'],22,C['ink'])
  text(r,x+18,y+60,'引文采用 '+e['quote_source']+' · 关系、时层和显示限制分栏',18,C['muted'])
 used={sid for e in es for sid in e['sources']};ss=[s for s in data['sources'] if s['id'] in used]
 text(r,75,1230,'可复核来源',28,C['green'],weight=500)
 for i,s in enumerate(ss):
  x=75+(i%2)*1050;y=1282+(i//2)*65
  text(r,x,y,s['id']+' · '+s['title'],20,C['muted']);text(r,x,y+28,s['url'],18,C['muted'])
 text(r,75,1510,'在线逐条查阅：https://mechgouki.github.io/luoyang-city/dual-southeast.html · 2026-11-13',21,C['muted'])
 return r

def main():
 data=read_research();info=load(SITE/'build-info.json')
 assert info.get('west_roads_b5',{}).get('records')==24
 assert (SITE/'ground-review/metadata.json').is_file()
 assert not (SITE/'dual-southeast.html').exists(),'Rebuild all preceding stages before B6'
 protected={str(p.relative_to(SITE)):sha(p) for p in SITE.rglob('*') if p.is_file() and p.name not in ['build-info.json','index.html','v3.0-dual.html','release.json']}
 master,audit=changed_master(SITE/'assets/master-dual-b5-west-roads.svg',load(SITE/'data/markers.json'))
 master_file=SITE/'assets/master-dual-b6-southeast.svg';write_svg(master_file,master)
 maps=SITE/'dual/maps';archive=ET.parse(SITE/'assets/master-v24.svg').getroot()
 for reg in data['regions']:
  write_svg(maps/(reg['id']+'.svg'),literary_plate(master,reg))
  write_svg(maps/(reg['id']+'-archive.svg'),literary_plate(archive,reg,True))
 write_svg(maps/'SE6-relations.svg',relations_plate());write_svg(maps/'SE6-layers.svg',layers_plate())
 for reg,suffix in [('R08','inner'),('R09','outer')]:write_svg(maps/('SE6-evidence-'+suffix+'.svg'),evidence_plate(data,reg))
 data['source_commit']=info['source_commit'];data['drawing_audit']=audit;dump(SITE/'dual/southeast-b6.json',data)
 (SITE/'dual-southeast.html').write_bytes((ROOT/'web/southeast-b6.html').read_bytes())
 (SITE/'southeast-b6.js').write_bytes((ROOT/'web/southeast-b6.js').read_bytes())
 with (SITE/'downloads/dual-southeast-b6-evidence.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['编号','分区','主题','实体ID','引文来源','原文','采用解释','画法','限制','时层'])
  for e in data['evidence']:w.writerow([e['id'],e['source_region'],e['title'],';'.join(e['entities']),e['quote_source'],e['quote'],e['reading'],e['drawing'],e['limit'],e.get('temporal_note','')])
 plates=[maps/'L08.svg',maps/'L09.svg',maps/'SE6-relations.svg',maps/'SE6-layers.svg',SITE/'ground-review/candidate-summary.svg',SITE/'ground-review/lineage-summary.svg',maps/'SE6-evidence-inner.svg',maps/'SE6-evidence-outer.svg']
 render_atlas(plates,SITE/'downloads/dual-southeast-b6-atlas.pdf')
 cairosvg.svg2png(url=str(maps/'SE6-relations.svg'),write_to=str(SITE/'dual/southeast-b6-preview.png'),output_width=1600)
 index=(SITE/'index.html').read_text();match=re.search(r'<script src="\./([^"]+-runtime\.js)"></script>',index);assert match
 boot=(SITE/match.group(1)).read_text();m=re.search(r'window\.ATLAS_ASSETS=(.*?);\n',boot);assert m
 mapping=json.loads(m.group(1));mapping['assets/master-v28-review.svg']=fp(master_file.name,master_file.read_bytes())
 boot=boot[:m.start(1)]+json.dumps(mapping,ensure_ascii=False)+boot[m.end(1):];index=index.replace(match.group(1),fp('runtime.js',boot.encode()),1)
 banner='<section id="southeast-b6-entry" style="margin:16px 0;padding:23px;border:1px solid #b9c5ad;background:#eaf0e3;border-radius:8px"><h2>城东南门内外 · B6</h2><p>同里、路侧、邻近和宅寺年代分别核对；既有锚点保留。历史图并行审核具名地物与上游编图资料。</p><p><a href="./dual-southeast.html#inner?id=EI01">进入城东南联读 ↗</a>　<a href="./ground-review.html">查看具名地物审核 ↗</a>　<a href="./downloads/dual-southeast-b6-atlas.pdf">下载本批图册 ↗</a></p></section>'
 assert index.count('id="west-roads-b5-entry"')==1
 index=index.replace('<section id="west-roads-b5-entry"',banner+'<section id="west-roads-b5-entry"',1)
 index=index.replace('<nav aria-label="主导航" class="topnav">','<nav aria-label="主导航" class="topnav"><a href="./dual-southeast.html">城东南B6 ↗</a>',1)
 js=fp('southeast-main-b6.js',(ROOT/'web/southeast-main-b6.js').read_bytes());index=index.replace('</body>',f'<script defer src="./{js}"></script></body>')
 (SITE/'index.html').write_text(index);(SITE/'v3.0-dual.html').write_text(index)
 release=load(SITE/'release.json');release['extensions']=sorted(set(release.get('extensions',[])+['dual-southeast-b6','ground-review-b6']));release['current_milestone']='B6 城东南门内外与具名地物审核';dump(SITE/'release.json',release)
 assert all(sha(SITE/p)==h for p,h in protected.items()),'B6 modified a protected prior resource'
 dump(SITE/'dual/southeast-b6-preservation.json',{'protected_files':len(protected),'protected_unchanged':True,'sha256':protected})
 with zipfile.ZipFile(SITE/'downloads/dual-southeast-b6-package.zip','w',zipfile.ZIP_DEFLATED) as z:
  docs=[ROOT/'docs/dual-southeast-inner-b6-research.md',ROOT/'docs/dual-southeast-outer-b6-research.md',ROOT/'docs/ground-review-b6-research.md',ROOT/'docs/dual-southeast-b6-release-notes.md']
  for p in plates+[maps/'L08-archive.svg',maps/'L09-archive.svg',master_file,SITE/'dual/southeast-b6.json',SITE/'downloads/dual-southeast-b6-evidence.csv',SITE/'downloads/dual-southeast-b6-atlas.pdf']+docs:
   z.write(p,('docs/'+p.name) if p.is_relative_to(ROOT/'docs') else str(p.relative_to(SITE)))
 info['southeast_b6']={'source_commit':info['source_commit'],'records':len(data['evidence']),'regions':['L08','L09'],'type_groups_changed':len(NODES)+len(GATES),'nonspatial_sidecars_preserved':list(SIDECARS),'new_ancient_coordinates':0,'previous_release_preserved':'B1+B2+B3+B4+B5','protected_files':len(protected),'atlas_pages':8}
 info.setdefault('ground_review_b6',{}).update({'metadata':'ground-review/metadata.json','ancient_coordinates_added':0})
 info['files_sha256']={str(p.relative_to(SITE)):sha(p) for p in sorted(SITE.rglob('*')) if p.is_file() and p.name!='build-info.json'};dump(SITE/'build-info.json',info)
 print('Built B6:',len(data['evidence']),'evidence,',len(NODES)+len(GATES),'type groups, L08+L09, eight-page atlas; protected',len(protected))

if __name__=='__main__':main()
