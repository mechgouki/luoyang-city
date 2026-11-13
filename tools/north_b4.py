#!/usr/bin/env python3
"""Publish the next literary region after B1/B2/B3 and printed-grid preparation.

All ancient anchors remain relative literary coordinates. Grid calibration is a
separate historical-image study and is never applied to the literary SVG.
"""
from pathlib import Path
import copy,csv,hashlib,io,json,re,zipfile,xml.etree.ElementTree as ET
import cairosvg
from pypdf import PdfReader,PdfWriter
from dual_cartography import NS,C,load,dump,node,text,para,rect,path,svg,world,crop,write_svg

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'_site'
DATA=ROOT/'research/dual-b4/north-gates.json'
ANCHORS={'gate_daxia':(5000,1800),'gate_guangmo':(7200,1800),'n_chanxu':(4680,1100),'n_ningxuan':(8040,1260)}
TEMPLE_CLASSES={'n_chanxu':'wnode155','n_ningxuan':'wnode156'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fp(name,body):
 p='_assets/'+hashlib.sha256(body).hexdigest()[:20]+'-'+Path(name).name
 (SITE/p).parent.mkdir(parents=True,exist_ok=True);(SITE/p).write_bytes(body);return p

def gate_icon(parent,x,y,three=False,s=1):
 """Counted type symbol, not a measured elevation or roof reconstruction."""
 g=node(parent,'g',transform=f'translate({x} {y}) scale({s})')
 if three:
  for yy,ww in [(-28,32),(-5,43),(18,54)]:
   path(g,f'M{-ww} {yy} L0 {yy-15} L{ww} {yy}',C['gold'],3)
   path(g,f'M{-ww*.65} {yy+2}v16h{ww*1.3}v-16',C['gold'],2)
  path(g,'M-12 34V26Q0 10 12 26V34',C['gold'],2)
 else:
  rect(g,-43,-20,86,58,C['paper'],C['ink'],3)
  path(g,'M-16 38V13Q0 -8 16 13V38',C['ink'],3)
  path(g,'M-53 -22H53',C['ink'],3)
 return g

def temple_group(eid,cls):
 x,y=ANCHORS[eid]
 g=ET.Element('{'+NS+'}g',{'class':cls,'data-entity-id':eid,'data-batch':'dual-b4','data-footprint':'false','style':'pointer-events:none'})
 node(g,'title').text='寺院类型图符；无塔依据、内部院址与朝向未定。原文献锚点保留。'
 path(g,f'M{x-49} {y-5}L{x} {y-31}L{x+49} {y-5}',C['green'],4)
 rect(g,x-35,y-4,70,36,'none',C['green'],3)
 path(g,f'M{x-9} {y+32}v-23h18v23',C['green'],3)
 if eid=='n_chanxu':
  path(g,f'M{x-62} {y-35}h-10v77h10 M{x+62} {y-35}h10v77h-10',C['gold'],2,'5 5')
  text(g,x,y+75,'T69 禅虚寺†〔年未定〕',31,C['green'],'middle',500)
  text(g,x,y+118,'御道西；门“外”为校补',24,C['muted'],'middle')
 else:
  text(g,x,y+75,'T70 凝玄寺〔范作凝圆〕',31,C['green'],'middle',500)
  text(g,x,y+118,'御道东 · 门外一里',24,C['muted'],'middle')
  text(g,x,y+154,'高显地势为线索，古址未定',21,C['gold'],'middle')
 return g

def changed_master(source,markers):
 root=ET.parse(source).getroot();wg=world(root);before=[ET.tostring(c) for c in wg]
 for eid,xy in ANCHORS.items():
  found=[m for m in markers if eid in m['ids']]
  assert len(found)==1 and (found[0]['x'],found[0]['y'])==xy,eid
 changed=set()
 for eid,cls in TEMPLE_CLASSES.items():
  old=[c for c in wg if c.get('class')==cls];assert len(old)==1,cls
  i=list(wg).index(old[0]);wg.remove(old[0]);wg.insert(i,temple_group(eid,cls));changed.add(i)
 assert all(ET.tostring(c)==before[i] for i,c in enumerate(wg) if i not in changed)
 g=node(wg,'g',id='north-glyphs-b4',style='pointer-events:none',data_footprint='false')
 for eid,three in [('gate_daxia',True),('gate_guangmo',False)]:
  x,y=ANCHORS[eid]
  child=node(g,'g',data_entity_id=eid,data_batch='dual-b4',data_footprint='false')
  node(child,'title').text='大夏三层†：采用周、范北魏营造校读；非复原立面。' if three else '广莫门类型；本批不指定楼层和实际立面。'
  gate_icon(child,x,y,three,.85)
  text(child,x,y+105,'三层† · 校读类型' if three else '普通门符 · 层数未定',23,C['gold'],'middle')
 assert len([n for n in root.iter() if n.get('data-batch')=='dual-b1'])==7
 assert len([n for n in root.iter() if n.get('data-batch')=='dual-b2'])==8
 assert len([n for n in root.iter() if n.get('id')=='west-glyphs-b3'])==1
 for n in root:
  if n.get('class')=='wt497 tb497':
   for child in list(n):n.remove(child)
   n.text='北魏洛阳 · 文献复原工作图 B4'
 node(root,'metadata').text=json.dumps({'batch':'dual-north-b4','source_sha256':sha(source),'anchors_moved':False,'new_ancient_coordinates':0,'type_groups_changed':4},ensure_ascii=False)
 return root,{'groups_replaced':2,'gate_symbols_added':2,'type_groups_changed':4,'source_sha256':sha(source),'ancient_absolute_positions_added':0,'anchors':{k:{'literary_xy':list(v),'anchor_moved':False,'geographic_coordinates':None} for k,v in ANCHORS.items()}}

def heading(r,kicker,title,subtitle,w=2200):
 text(r,75,64,kicker,22,C['gold'])
 text(r,75,130,title,47,C['ink'],weight=500)
 text(r,75,178,subtitle,23,C['muted'])
 path(r,f'M75 209H{w-75}',C['line'],2)

def north_plate(master,reg,archive=False):
 r=svg(2200,1560,'北门—金墉与闻义里 / '+('v2.4档案同区对照' if archive else 'B4文献平面'))
 heading(r,'LUOYANG / L06 / '+('ARCHIVE' if archive else 'B4'),'北门—金墉与闻义里','516—528 盛时综合语境；文献坐标未转换成经纬度。↑ 北')
 rect(r,75,235,2050,585,'#f0f2e9',C['line'],2,8)
 crop(master,r,92,252,2016,551,reg['bbox'])
 text(r,95,850,'全区索引 · 包含西面北端承明门，以及城东北闻义里；同一张母图裁切。',22,C['muted'])
 rect(r,75,900,990,430,'#f0f2e9',C['line'],2,8)
 rect(r,1100,900,1025,430,'#f0f2e9',C['line'],2,8)
 text(r,100,945,'A  两座北门与门外寺园',29,C['green'],weight=500)
 text(r,1125,945,'B  承明—金墉局部',29,C['green'],weight=500)
 crop(master,r,95,975,950,330,[4300,800,4300,1360])
 crop(master,r,1120,975,985,330,[3100,1900,2750,1250])
 para(r,95,1380,'大夏三层†为已选校读的类型表达；禅虚不添塔，凝玄地势只入线索。',42,23)
 para(r,1125,1380,'承明属西面门序北端。金墉门殿名物保留目录，不由“城前”补正南轴。',42,23)
 text(r,75,1520,('封存母图仅裁切展示，原文件未修改。' if archive else '本批改4组类型图符；既有B1、宫苑B2、城西B3保留。')+' 图幅、图符和插图之间不提供实测地理比例。',21,C['muted'])
 return r

def small_card(r,x,y,w,h,title,body,accent=None):
 rect(r,x,y,w,h,C['paper'],C['line'],2,9)
 text(r,x+25,y+45,title,28,accent or C['green'],weight=500)
 return para(r,x+25,y+88,body,max(8,(w-50)/24),23)

def gates_plate():
 r=svg(2000,1470,'B4 两门与两场：方位、前向和用途变化分层')
 heading(r,'B4 / NG01—NG09 / 文献关系','两门各有楼制，两场分别建档','每一行是独立关系板；面板位置、间距和连线长度没有地理意义。',2000)
 rect(r,75,250,1850,390,'#edf0e5',C['line'],2,10)
 text(r,110,302,'01  城北门序与城上宫观',27,C['green'],weight=500)
 gate_icon(r,420,427,True,2.3);gate_icon(r,1580,427,False,2.3)
 text(r,420,580,'西 · 大夏门 / 三层†',29,C['ink'],'middle',500)
 text(r,1580,580,'东 · 广莫门 / 本批不数层',29,C['ink'],'middle',500)
 path(r,'M650 425H1350',C['gold'],6,'18 12')
 text(r,1000,386,'城上宫观相连',29,C['gold'],'middle')
 text(r,1000,467,'栋数、门距和高度比例未定',22,C['muted'],'middle')
 text(r,1000,612,'† 采用周、范所取的北魏营造读法；高度与营造主语异文见 NG02。',22,C['muted'],'middle')
 rect(r,75,680,900,370,'#f1f3e9',C['line'],2,10)
 rect(r,1010,680,915,370,'#f1f3e9',C['line'],2,10)
 text(r,105,730,'02  禅虚寺前阅武场',29,C['green'],weight=500)
 small_card(r,105,770,320,130,'禅虚寺†','大夏御道西；“外”为校补')
 small_card(r,605,770,340,130,'阅武场','岁终农隙习战；未定位')
 path(r,'M435 836H592',C['gold'],4,'10 8')
 text(r,516,810,'寺前',24,C['gold'],'middle')
 text(r,516,875,'朝向未定',20,C['muted'],'middle')
 para(r,105,970,'前向依建筑朝向，不自动化成南方。没有据此增加一块有边界的场地。',35,23)
 text(r,1040,730,'03  宣武场到光风园',29,C['green'],weight=500)
 small_card(r,1040,770,365,130,'中朝 · 宣武场','大夏门东北')
 small_card(r,1520,770,375,130,'叙述时 · 光风园','苜蓿生焉')
 path(r,'M1420 836H1505',C['gold'],4)
 text(r,1464,808,'用途变迁',19,C['gold'],'middle')
 para(r,1040,970,'这条变迁链不把宣武场等同禅虚寺前阅武场。“今”为书中叙述时层。',36,23)
 rect(r,75,1090,1850,250,'#edf0e5',C['line'],2,10)
 text(r,105,1140,'04  凝玄寺：分别保存四种约束',29,C['green'],weight=500)
 for i,(title,body) in enumerate([('量距','广莫门外一里'),('路侧','御道东'),('里属','永平里'),('地势线索','高显，下临城阙')]):
  x=105+i*455;small_card(r,x,1175,425,125,title,body)
 text(r,75,1408,'一里未换算为像素；高显未匹配现代高点；寺院院形、绝对高程与确切朝向仍未定。',24,C['muted'])
 return r

def membership_plate():
 r=svg(2000,1480,'B4 金墉通行、名物与闻义里成员关系')
 heading(r,'B4 / NG10—NG16 / 无共同地理比例','通行关系与里内目录','城前保留朝向限制；目录的排列不产生宫殿轴线、街址或窑址。',2000)
 rect(r,75,250,1850,510,'#edf0e5',C['line'],2,10)
 text(r,110,305,'01  承明门与金墉城前大道',30,C['green'],weight=500)
 small_card(r,110,360,420,160,'承明门','西面城门序列的北端；不列为第三座北门。')
 small_card(r,765,360,450,160,'东西大道','位于金墉城前；“前”未定为南。')
 small_card(r,1450,360,435,160,'金墉城','独立保留范围示意；句前疑缺文。')
 path(r,'M545 438H750',C['green'],4,'12 8');text(r,648,410,'门当大道',23,C['green'],'middle')
 path(r,'M1230 438H1435',C['gold'],4,'12 8');text(r,1332,410,'城前',23,C['gold'],'middle')
 text(r,110,595,'王南寺',29,C['green'],weight=500)
 para(r,110,640,'到寺、通门属于通行叙述；“城西”回指仍有解释余地。本图不把线变成一条测得的道路。',68,24)
 rect(r,75,805,900,490,'#f1f3e9',C['line'],2,10)
 rect(r,1010,805,915,490,'#f1f3e9',C['line'],2,10)
 text(r,105,863,'02  金墉 · 无序名物',29,C['green'],weight=500)
 text(r,1040,863,'03  闻义里 · 无序成员',29,C['green'],weight=500)
 left=[('光极门','金墉城门名；门侧未定'),('光极殿','城内构成；不补中轴'),('重楼飞阁','景观描述；不枚举栋数')]
 right=[('郭文远宅','堂宇、园林；无独立街址'),('宋云宅','明记里属；不定与郭宅先后'),('制瓦／瓦器','生业叙述；没有据此增加窑点')]
 for i,((t,b),(t2,b2)) in enumerate(zip(left,right)):
  y=900+i*112
  rect(r,105,y,840,93,C['paper'],C['line'],1,7);text(r,130,y+39,t,25,C['ink']);text(r,380,y+39,b,23,C['muted'])
  rect(r,1040,y,855,93,C['paper'],C['line'],1,7);text(r,1065,y+39,t2,25,C['ink']);text(r,1320,y+39,b2,22,C['muted'])
 para(r,75,1360,'瑶光北有承明可保留；金墉句前疑有缺文，不将叙事相邻转换为“瑶光—承明—金墉”的确定南北轴线。',79,25)
 return r

def terrain_plate(site):
 r=svg(2200,1480,'B4 凝玄文本地势与现代参照分层')
 heading(r,'B4 / 地形研究并行','从地势线索到可复核的地图','左图为现代DSM地势参照；右栏为古代文本与近代地图处理，三者没有古址定位连线。')
 import base64
 im=node(r,'image',x=75,y=260,width=1100,height=1003,preserveAspectRatio='none')
 im.set('{http://www.w3.org/1999/xlink}href','data:image/png;base64,'+base64.b64encode((site/'dual/terrain-reading.png').read_bytes()).decode())
 rect(r,75,260,1100,1003,'none',C['line'],2)
 text(r,95,1309,'现代DSM参数化地势阅读；颜色不鉴定古台地或古河道。',22,C['muted'])
 small_card(r,1240,260,885,270,'古文线索 · 凝玄寺','“地形高显，下临城阙”已经登记。缺少高程、视点和明确朝向，不能凭这句话匹配现代高点。')
 small_card(r,1240,565,885,330,'近代图面 · 印刷网格校准','两幅AMS原图使用各8个拟合点和5个留出检查点，检验扫描图内部方格网的一致性。印刷网格米残差不是地面定位精度。')
 small_card(r,1240,930,885,335,'下一道证据门槛','还需查明近代图的水平基准、独立地面对应，并分别处理河岸年代与古今地貌变化。当前古建筑与古水道坐标均未因此新增。')
 from terrain_v30 import NOTICE,LIABILITY
 y=para(r,75,1370,NOTICE,125,15)
 para(r,75,y+7,LIABILITY,125,14)
 return r

def evidence_plate(data):
 r=svg(2200,1560,'B4 原文证据索引与研究层次')
 heading(r,'B4 / 原文与处理记录','证据索引与本批判断边界','完整引文、异文、采用解释和画法见证据表及专题页；下列四个卷册来自同一部古籍。')
 for i,e in enumerate(data['evidence']):
  col=i//8;row=i%8;x=75+col*1050;y=250+row*92
  rect(r,x,y,1005,76,'#eff1e7',C['line'],1,6)
  text(r,x+20,y+32,e['id']+' · '+e['title'],25,C['ink'])
  text(r,x+20,y+62,'引文采用 '+e['quote_source']+'；原文 / 校读 / 显示安排分别登记',18,C['muted'])
 text(r,75,1055,'电子文本 · 原书《洛阳伽蓝记》',29,C['green'],weight=500)
 y=1100
 for s in data['sources']:
  text(r,75,y,s['id']+' · '+s['title']+'  '+s['url'],20,C['muted']);y+=42
 text(r,75,1320,'本批还修正：寿丘位于延酤／退酤以西、张方沟以东；原图误写的东西界标已更正，锚点未移动。',24,C['gold'])
 para(r,75,1380,'近代图面控制点和现代DSM是独立资料层。26个网格点不是26个古址；内部留出残差不代表地面精度。古地理配准与古河岸时层仍待研究。',82,24)
 text(r,75,1516,'在线逐条查阅：https://mechgouki.github.io/luoyang-city/dual-north.html · 2026-11-13',21,C['muted'])
 return r

def render_atlas(paths,target):
 writer=PdfWriter()
 for p in paths:writer.append(PdfReader(io.BytesIO(cairosvg.svg2pdf(url=str(p)))))
 with target.open('wb') as f:writer.write(f)

def main():
 data=load(DATA);info=load(SITE/'build-info.json')
 assert info.get('west_b3',{}).get('records')==16 and (SITE/'historical-frame/metadata.json').exists()
 assert len(data['evidence'])==16 and all(e['geographic_coordinates'] is None for e in data['evidence'])
 assert not (SITE/'dual-north.html').exists(),'Rebuild the preceding stages before regenerating B4'
 protected={str(p.relative_to(SITE)):sha(p) for p in SITE.rglob('*') if p.is_file() and p.name not in ['build-info.json','index.html','v3.0-dual.html','release.json']}
 master,audit=changed_master(SITE/'assets/master-dual-b3-west.svg',load(SITE/'data/markers.json'))
 master_file=SITE/'assets/master-dual-b4-north.svg';write_svg(master_file,master)
 out=SITE/'dual/maps';out.mkdir(parents=True,exist_ok=True)
 write_svg(out/'L06.svg',north_plate(master,data['region']))
 write_svg(out/'L06-archive.svg',north_plate(ET.parse(SITE/'assets/master-v24.svg').getroot(),data['region'],True))
 write_svg(out/'N-gates.svg',gates_plate());write_svg(out/'N-membership.svg',membership_plate())
 write_svg(out/'T4-north.svg',terrain_plate(SITE))
 write_svg(out/'N-evidence.svg',evidence_plate(data))
 data['source_commit']=info['source_commit'];data['drawing_audit']=audit
 dump(SITE/'dual/north-b4.json',data)
 for dest,src in [('dual-north.html','north-b4.html'),('north-b4.js','north-b4.js')]:
  (SITE/dest).write_bytes((ROOT/'web'/src).read_bytes())
 with (SITE/'downloads/dual-north-b4-evidence.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['编号','主题','实体ID','引文来源','原文','采用读法','画法','保留限制','时层'])
  for e in data['evidence']:w.writerow([e['id'],e['title'],';'.join(e['entities']),e['quote_source'],e['quote'],e['reading'],e['drawing'],e['limit'],e.get('temporal_note','')])
 plates=[out/n for n in ['L06.svg','N-gates.svg','N-membership.svg','T4-north.svg']]+[SITE/'historical-frame/frame-summary.svg',out/'N-evidence.svg']
 render_atlas(plates,SITE/'downloads/dual-north-b4-atlas.pdf')
 cairosvg.svg2png(url=str(out/'N-gates.svg'),write_to=str(SITE/'dual/north-b4-preview.png'),output_width=1600)
 index=(SITE/'index.html').read_text(encoding='utf-8')
 match=re.search(r'<script src="\./([^"]+-runtime\.js)"></script>',index);assert match
 boot=(SITE/match.group(1)).read_text(encoding='utf-8');m=re.search(r'window\.ATLAS_ASSETS=(.*?);\n',boot);assert m
 mapping=json.loads(m.group(1));assert 'assets/master-v28-review.svg' in mapping
 mapping['assets/master-v28-review.svg']=fp(master_file.name,master_file.read_bytes())
 boot=boot[:m.start(1)]+json.dumps(mapping,ensure_ascii=False)+boot[m.end(1):]
 index=index.replace(match.group(1),fp('runtime.js',boot.encode()),1)
 banner='<section id="north-b4-entry" style="margin:16px 0;padding:23px;border:1px solid #bbbea7;background:#f1f0e4;border-radius:8px"><h2>北门与金墉 · B4</h2><p>两门楼制、门外寺园与金墉通行关系进入新分区；16条原文逐项可查。近代地图另完成印刷方格网校准，古址仍未配准。</p><p><a href="./dual-north.html#literary?id=NG01">进入北门与金墉 ↗</a>　<a href="./historical-frame.html">查看近代图面校准 ↗</a>　<a href="./downloads/dual-north-b4-atlas.pdf">下载本批图册 ↗</a></p></section>'
 assert index.count('id="west-b3-entry"')==1
 index=index.replace('<section id="west-b3-entry"',banner+'<section id="west-b3-entry"',1)
 index=index.replace('<nav aria-label="主导航" class="topnav">','<nav aria-label="主导航" class="topnav"><a href="./dual-north.html">北门B4 ↗</a>',1)
 js=fp('north-main-b4.js',(ROOT/'web/north-main-b4.js').read_bytes())
 index=index.replace('</body>',f'<script defer src="./{js}"></script><style>.topnav{{flex-wrap:wrap}}.topnav a{{white-space:nowrap}}</style></body>')
 (SITE/'index.html').write_text(index,encoding='utf-8');(SITE/'v3.0-dual.html').write_text(index,encoding='utf-8')
 release=load(SITE/'release.json');assert release['release']=='v3.0-dual.b2'
 release['extensions']=sorted(set(release.get('extensions',[])+['dual-north-b4','historical-frame-b4']))
 release['current_milestone']='B4 北门—金墉与近代图面校准';dump(SITE/'release.json',release)
 assert all(sha(SITE/p)==h for p,h in protected.items()),'A prior published asset was changed by B4'
 dump(SITE/'dual/north-b4-preservation.json',{'protected_files':len(protected),'protected_unchanged':True,'sha256':protected,'explicit_prior_correction':'B3寿丘关系图改为延酤以西、张方沟以东；W14补齐东西二里；在B3生成步骤完成。'})
 with zipfile.ZipFile(SITE/'downloads/dual-north-b4-package.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in plates+[out/'L06-archive.svg',master_file,SITE/'dual/north-b4.json',SITE/'downloads/dual-north-b4-evidence.csv',SITE/'downloads/dual-north-b4-atlas.pdf',ROOT/'docs/dual-north-b4-research.md']:
   z.write(p,('docs/'+p.name) if p.is_relative_to(ROOT/'docs') else str(p.relative_to(SITE)))
 info['north_b4']={'source_commit':info['source_commit'],'records':16,'region':'L06','type_groups_changed':4,'new_ancient_coordinates':0,'previous_release_preserved':'B1+B2+B3','protected_files':len(protected)}
 info['historical_frame_b4']={'metadata':'historical-frame/metadata.json','historical_geographic_registration_complete':False,'ancient_coordinates_added':0}
 info['files_sha256']={str(p.relative_to(SITE)):sha(p) for p in sorted(SITE.rglob('*')) if p.is_file() and p.name!='build-info.json'}
 dump(SITE/'build-info.json',info)
 print('Built B4: 16 evidence records, L06, 4 type groups, 6-page atlas; prior files preserved:',len(protected))

if __name__=='__main__':main()
