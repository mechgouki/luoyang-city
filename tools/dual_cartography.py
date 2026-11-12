#!/usr/bin/env python3
"""Reproducible paired maps: reviewed B1 and R03 B2. No new georeference."""
from pathlib import Path
import base64,copy,hashlib,json,math,xml.etree.ElementTree as E,zipfile
import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter,distance_transform_edt
from PIL import Image
NS='http://www.w3.org/2000/svg';XL='http://www.w3.org/1999/xlink';E.register_namespace('',NS);E.register_namespace('xlink',XL)
C={'paper':'#faf9f5','ink':'#243f3a','muted':'#66776e','green':'#326e5c','blue':'#4a7891','gold':'#9f7438','line':'#cdd5c9'}
B1={'ic_yongning':'wnode0','v3_jingming':'wnode2','ic_taiwei':'wnode90','ic_jingle':'wnode103','bridge_jianchun':'wnode117','bridge_eaststone':'wnode118','v3_hanguozixue':'wnode138'}
B2={'ic_yaoguang':'wnode63','ic_lingyun_platform':'wnode66','ic_jiuhua':'wnode72','ic_penglai':'wnode73','ic_jingyang_hill':'wnode75','ic_henge':'wnode76','ic_xihe':'wnode77','ic_qingshu':'wnode78'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def node(p,tag,**a):return E.SubElement(p,'{'+NS+'}'+tag,{k.replace('_','-'):str(v) for k,v in a.items() if v is not None})
def text(p,x,y,s,size=22,color=None,anchor='start',weight=400):
 n=node(p,'text',x=x,y=y,font_size=size,fill=color or C['ink'],text_anchor=anchor,font_weight=weight,font_family='Noto Sans CJK SC,Microsoft YaHei,sans-serif');n.text=s;return n

def para(p,x,y,s,width=25,size=22):
 line='';units=0
 for ch in s+'\n':
  u=1 if ord(ch)>127 else .54
  if ch=='\n' or (units+u>width and line):
   text(p,x,y,line,size,C['muted']);y+=int(size*1.5);line='';units=0
  if ch!='\n':line+=ch;units+=u
 if line:text(p,x,y,line,size,C['muted']);y+=int(size*1.5)
 return y

def rect(p,x,y,w,h,fill='none',stroke=None,sw=2,rx=0):return node(p,'rect',x=x,y=y,width=w,height=h,fill=fill,stroke=stroke,stroke_width=sw,rx=rx)
def path(p,d,color=None,w=3,dash=None,fill='none'):return node(p,'path',d=d,fill=fill,stroke=color or C['green'],stroke_width=w,stroke_dasharray=dash,stroke_linecap='round',stroke_linejoin='round')
def svg(w,h,title):
 r=E.Element('{'+NS+'}svg',{'viewBox':f'0 0 {w} {h}','width':str(w),'height':str(h),'role':'img'});node(r,'title').text=title;rect(r,0,0,w,h,C['paper']);return r

def write_svg(p,r):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(E.tostring(r,encoding='utf-8',xml_declaration=True))
def world(r):return next(g for g in r if g.tag=='{'+NS+'}g' and g.get('transform'))
def hall(p,x,y,w=90,color=None):
 co=color or C['green'];path(p,f'M{x-w*.6} {y-5} L{x} {y-34} L{x+w*.6} {y-5}',co,5)
 rect(p,x-w*.44,y-5,w*.88,34,C['paper'],co,4)
 for dx in [-.23,0,.23]:path(p,f'M{x+w*dx} {y-3}v30',co,3)
def tower(p,x,y):
 for j,w in enumerate([23,32,41]):
  yy=y-40+j*20;path(p,f'M{x-w} {yy+8}L{x} {yy-5}L{x+w} {yy+8}',w=4);path(p,f'M{x-w*.65} {yy+9}v10h{w*1.3}v-10',w=3)
 path(p,f'M{x} {y-47}v-15',w=4)
def mound(p,x,y):path(p,f'M{x-75} {y+20}Q{x-65} {y-5} {x-45} {y-2}Q{x-5} {y-60} {x+35} {y-8}Q{x+55} {y-3} {x+75} {y+20}',w=4)

def b2_group(eid,cls,mark):
 x,y=mark['x'],mark['y'];g=E.Element('{'+NS+'}g',{'class':cls,'data-entity-id':eid,'data-batch':'dual-b2','data-footprint':'false'})
 node(g,'title').text=mark['label']+'；类型与构件图符，原示意锚点不动，不是院墙或测量足迹。'
 if eid=='ic_yaoguang':
  tower(g,x-55,y-5);hall(g,x+65,y+6,70)
  text(g,x,y-88,'构件目录 · 内址未定',23,C['gold'],'middle');text(g,x,y+82,'T04 瑶光寺',35,C['green'],'middle',500)
  text(g,x,y+120,'五层塔 / 讲殿尼房',25,C['muted'],'middle');text(g,x,y+155,'530侵扰不等于寺毁',23,C['muted'],'middle')
 elif eid=='ic_lingyun_platform':
  rect(g,x-64,y-5,128,40,C['paper'],C['gold'],4);path(g,f'M{x-76} {y+46}h152',C['gold'],4)
  pts=' '.join(f'{x+23*math.cos(i*math.pi/4)},{y-17+23*math.sin(i*math.pi/4)}' for i in range(8));node(g,'polygon',points=pts,fill=C['paper'],stroke=C['blue'],stroke_width=4)
  text(g,x,y+92,'P34 凌云台',30,C['ink'],'middle',500);text(g,x,y+128,'台上八角井 · 台形未定',22,C['muted'],'middle')
 elif eid=='ic_jiuhua':
  rect(g,x-65,y+18,130,35,C['paper'],C['gold'],4);hall(g,x,y-15,90)
  text(g,x,y+97,'P77 九华台',30,C['ink'],'middle',500);text(g,x,y+134,'台上清凉殿',24,C['muted'],'middle')
 elif eid in ['ic_penglai','ic_henge','ic_xihe']:
  mound(g,x,y+10);hall(g,x,y-26,78)
  title,sub={'ic_penglai':('P79 蓬莱山','人工作山 / 山上仙人馆'),'ic_henge':('P85 姮娥峰','峰上露寒馆†'),'ic_xihe':('P84 羲和岭','岭上温风室')}[eid]
  text(g,x,y+92,title,29,C['green'],'middle',500);text(g,x,y+128,sub,22,C['muted'],'middle')
 elif eid=='ic_jingyang_hill':
  path(g,f'M{x-47} {y-36}h-13v72h13 M{x+47} {y-36}h13v72h-13',C['gold'],4,'8 6');text(g,x,y+12,'山 / 殿',26,C['gold'],'middle')
  text(g,x,y+82,'P83 景山殿†',29,C['ink'],'middle',500);text(g,x,y+117,'周：景阳山 / 范：景阳殿候选',19,C['muted'],'middle')
 else:
  hall(g,x,y,85);text(g,x,y+82,'P87 清暑殿',29,C['green'],'middle',500);text(g,x,y+118,'与百果园先后未定',22,C['muted'],'middle')
 return g

def changed_master(source,snapshot,markers,batch='b2'):
 root=E.parse(source).getroot();g=world(root);before=[E.tostring(c) for c in g];changes=[];replacements={}
 for eid,cls in B1.items():replacements[eid]=E.fromstring(snapshot[eid])
 if batch=='b2':
  for eid,cls in B2.items():replacements[eid]=b2_group(eid,cls,next(m for m in markers if eid in m['ids']))
 for eid,new in replacements.items():
  cls=new.get('class');old=[c for c in g if c.get('class')==cls];assert len(old)==1,(eid,cls)
  i=list(g).index(old[0]);g.remove(old[0]);g.insert(i,new);m=next(m for m in markers if eid in m['ids'])
  changes.append({'entity_id':eid,'class':cls,'index':i,'literary_xy':[m['x'],m['y']],'geographic_coordinates':None,'anchor_moved':False,'batch':new.get('data-batch')})
 changed={c['index'] for c in changes};assert all(E.tostring(c)==before[i] for i,c in enumerate(g) if i not in changed)
 defs=root.find('{'+NS+'}defs')
 if defs is not None:node(defs,'style').text='text[paint-order]{stroke:none !important;}'
 for t in root:
  if t.get('class')=='wt497 tb497':
   for c in list(t):t.remove(c)
   t.text='北魏洛阳 · 文献复原工作图 '+batch.upper();t.set('font-size','86')
  if t.get('class')=='wt498 tb498':
   for c in list(t):t.remove(c)
   t.text='原图继续深化；建筑图符非实测足迹。旧版独立封存，地形图另设入口。'
 node(root,'metadata').text=json.dumps({'batch':batch,'source_sha256':sha(source),'changed':changes,'new_ancient_coordinates':0},ensure_ascii=False)
 return root,{'groups_changed':len(changes),'groups_preserved':len(g)-len(changes),'changes':changes,'source_sha256':sha(source)}

def crop(master,p,x,y,w,h,bbox):
 n=node(p,'svg',x=x,y=y,width=w,height=h,viewBox=' '.join(map(str,bbox)),preserveAspectRatio='xMidYMid meet')
 d=master.find('{'+NS+'}defs')
 if d is not None:n.append(copy.deepcopy(d))
 g=copy.deepcopy(world(master));g.attrib.pop('transform',None);n.append(g);return n

def region_page(master,reg,items,batch):
 r=svg(1800,1300,reg['name']+' / 双图并行 '+batch)
 text(r,65,65,'北魏洛阳 / 文献原图继续深化',23,C['green']);text(r,65,125,reg['id']+'  '+reg['name'],43,weight=500)
 text(r,65,171,'516—528 盛时综合语境；图符、距离与院形的解释精度分别保留。',22,C['muted'])
 rect(r,65,220,1170,850,'#f5f5ee',C['line'],rx=8);crop(master,r,80,235,1140,820,reg['bbox'])
 text(r,90,1115,'↑ 北  ·  从同一张当前文献母图裁切；非实测比例。',22,C['green'])
 para(r,90,1155,reg.get('note','旧示意位置保留。未定名物不分配新地理坐标。'),48,22)
 y=240;text(r,1285,y,'本区改图与保留',27,weight=500);y+=55
 for title,body in items:
  text(r,1285,y,title,20,C['green'],weight=500);y+=31;y=para(r,1285,y,body,19,22)+21
 text(r,65,1258,'原文、校读与显示安排分层；类型图符不代表真实院墙、开间、池岸或精确地形。',21,C['muted'])
 return r

def diagram(kind):
 r=svg(1600,1050,'B2 宫苑条件关系 / '+kind)
 text(r,60,60,'B2 / 宫苑 · 文本关系，不是地理平面',23,C['green'])
 if kind in ['platform','hill']:
  mode='台：采用周氏补字回指九华台' if kind=='platform' else '山：保留他本山字回指蓬莱山'
  text(r,60,120,'钓台殿：两种所属解释',40,weight=500);text(r,60,172,mode,25,C['gold'])
  for x,title,sub in [(85,'九华台','池中台；台上清凉殿有明文'),(855,'蓬莱山','人工营作山；山上仙人馆有明文')]:
   rect(r,x,245,650,450,'#eef2e8',C['line'],rx=12);text(r,x+30,299,title,32,C['green']);text(r,x+30,346,sub,23,C['muted'])
   hall(r,x+320,418,145);text(r,x+320,503,'台 / 山上构件示意',23,C['muted'],'middle')
  chosen=410 if kind=='platform' else 1180
  rect(r,chosen-200,560,400,85,C['paper'],C['gold'],3,8);text(r,chosen,613,'钓台殿†：条件所属',27,C['gold'],'middle')
  para(r,65,770,'G09：这次切换只改变所属关系图。主地图中的钓台殿仍为未定位附记，不新增点、不转成确定院址。',62,26)
  para(r,65,875,'另须区分西游园的灵芝钓台与此处钓台殿；同一“钓”字不构成同址证明。',62,23)
 else:
  text(r,60,120,'诸海与地下石窦：联系不等于地表河道',36,weight=500)
  text(r,60,170,'G14—G15 / 集合性叙述与水情条件分别表达',24,C['muted'])
  rect(r,580,335,430,170,'#e4eff0',C['blue'],3,12);text(r,795,391,'诸海 · 集合节点',31,C['blue'],'middle');text(r,795,439,'不展开成任意两池全互联',22,C['muted'],'middle')
  for x,y,name in [(70,335,'谷水'),(1150,335,'阳渠'),(580,665,'翟泉')]:
   rect(r,x,y,340,95,C['paper'],C['blue'],2,8);text(r,x+170,y+59,name,29,C['blue'],'middle')
  path(r,'M410 382H580',C['blue'],4,'12 9');path(r,'M1010 382H1150',C['blue'],4,'12 9');path(r,'M795 505V665',C['blue'],4,'12 9')
  text(r,487,310,'西通',23,C['blue'],'middle');text(r,1080,310,'东连',23,C['blue'],'middle');text(r,835,599,'亦相连',23,C['blue'])
  text(r,75,810,'地下石窦联系：原文有据；管线几何、坡降、常流与同期状态未定。',25,C['muted'])
  text(r,75,864,'大旱：谷水注之；霖雨：阳穀泄之。保留原字与校读，不视为全年水文。',24,C['muted'])
  text(r,75,921,'现代DSM不能据此识别地下工程；不在地表分类图添加同名水线。',24,C['gold'])
 text(r,60,1010,'来源：《洛阳伽蓝记》卷一及周、范校语。每项解释见网页 G09 / G14 / G15；无地理比例尺。',20,C['muted'])
 return r

def terrain(site,out):
 import tempfile
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory() as td:
  td=Path(td)
  with zipfile.ZipFile(site/'downloads/luoyang-terrain-v30-gis.zip') as z:
   for name in ['display-dsm-sigma90m.tif','slope-display-sigma90m-deg.tif']:
    assert name in z.namelist();(td/name).write_bytes(z.read(name))
  with rasterio.open(td/'display-dsm-sigma90m.tif') as s:
   a=s.read(1,masked=True);valid=~np.ma.getmaskarray(a);z=np.asarray(a.filled(0),dtype='float64');profile=s.profile.copy();transform=s.transform
  with rasterio.open(td/'slope-display-sigma90m-deg.tif') as s:
   sl=s.read(1,masked=True);valid &= ~np.ma.getmaskarray(sl);sl=np.asarray(sl.filled(0))
  assert abs(transform.a-30)<1e-6 and abs(transform.e+30)<1e-6
  den=gaussian_filter(valid.astype('float64'),1000/30,mode='constant',cval=0,truncate=3)
  mean=gaussian_filter(np.where(valid,z,0),1000/30,mode='constant',cval=0,truncate=3)/np.maximum(den,1e-9)
  rel=z-mean;edge=distance_transform_edt(valid)*30<3000;good=valid&~edge;k=np.zeros(z.shape,dtype='uint8')
  for code,mask in [(1,(sl<=3)&(rel< -5)),(2,(sl<=3)&(rel>5)),(3,(sl<=3)&(np.abs(rel)<=5)),(4,(sl>3)&(sl<=8)),(5,sl>8)]:k[good&mask]=code
  k[valid&edge]=6;assert np.all(k[valid]>0) and np.all(k[~valid]==0)
  colors=np.array([[250,249,245],[173,204,208],[205,198,161],[225,226,201],[183,192,165],[144,161,134],[232,232,224]],dtype='uint8')
  im=Image.fromarray(colors[k]);im.save(out/'terrain-classes.png');original=Image.open(site/'terrain/v3.0/relief.png').convert('RGB').resize(im.size,Image.Resampling.BILINEAR);Image.blend(original,im,.68).save(out/'terrain-reading.png')
  profile.update(driver='GTiff',dtype='uint8',count=1,nodata=0,compress='deflate',predictor=1)
  with rasterio.open(out/'modern-terrain-reading-classes.tif','w',**profile) as dst:dst.write(k,1);dst.update_tags(purpose='Modern heuristic classes, not ancient terrain or geomorphic stability')
  profile.update(dtype='float32',nodata=-9999.,predictor=3)
  with rasterio.open(out/'modern-relative-height-1km.tif','w',**profile) as dst:dst.write(np.where(valid,rel,-9999).astype('float32'),1)
  names=['相对低位缓面','相对高位缓面','平缓过渡面','缓坡面','较陡坡面','边缘邻域不足']
  data={'source_commit':'82336ab80ed683a944a53e4e87fec297f1a9a8d8','input_sha256':{p.name:sha(p) for p in td.iterdir()},'status':'modern_heuristic_interpretation','shape':list(k.shape),'transform':list(transform)[:6],'crs':profile['crs'].to_string(),'valid_pixels':int(valid.sum()),'classes':{str(i):{'name':names[i-1],'pixels':int((k==i).sum()),'area_km2':float((k==i).sum()*.0009),'rgb':colors[i].tolist()} for i in range(1,7)},'parameters':{'smoothing_sigma_m':90,'neighbourhood_sigma_m':1000,'edge_exclusion_m':3000,'relative_threshold_m':5,'slope_thresholds_deg':[3,8]},'sensitivity':[{'flat_max_deg':s,'low_below_m':h,'area_km2':round(float(np.sum(good&(sl<=s)&(rel<-h))*.0009),3)} for s in [2,3,5] for h in [3,5,8]],'ancient_registered_buildings':0,'ancient_river_lines_added':0,'limits':['现代建筑、植被、填挖与误差未去除。','高低相对于参数化邻域，不是古台地、河漫滩或地貌稳定性的鉴定。','古代园林人工山、池与地下石窦不自动映射到现代地表。']}
  dump(out/'terrain-reading.json',data);return data

def terrain_plate(out,master,regions,data,batch):
 r=svg(2000,1450,'独立地形解释 / '+batch)
 text(r,65,65,'北魏洛阳 / 新图独立建设 · '+batch,24,C['green']);text(r,65,125,'现代地表与古代建筑：先分层，再定位',41,weight=500)
 text(r,65,175,'左：参数化地势阅读；右：文献建筑插图。插图没有地理坐标，不对地面拉定位线。',23,C['muted'])
 a=node(r,'image',x=65,y=240,width=1150,height=1048,preserveAspectRatio='none');a.set('{'+XL+'}href','data:image/png;base64,'+base64.b64encode((out/'terrain-reading.png').read_bytes()).decode())
 rect(r,65,240,1150,1048,'none',C['line']);text(r,85,280,'现代DSM · UTM 49N · 30米计算网格',22,weight=500)
 scale=1150/(data['shape'][1]*30)*10000;path(r,f'M100 1240h{scale}',C['ink'],5);text(r,100,1214,'0',18);text(r,100+scale,1214,'10 km',18,anchor='end')
 text(r,85,1325,'比例尺仅适用于左侧现代地形，不适用于右侧历史插图。',22,C['muted'])
 if batch=='B1':
  for i,reg in enumerate(regions[:3]):
   y=245+i*290;rect(r,1280,y,650,270,'#f1f3ea',C['line'],rx=10);text(r,1300,y+36,reg['name'],24,weight=500);crop(master,r,1300,y+55,610,165,reg['bbox']);text(r,1300,y+247,'沿用文献示意图；未完成地理配准',19,C['gold'])
 else:
  reg=regions[-1];rect(r,1280,245,650,585,'#f1f3ea',C['line'],rx=10);text(r,1300,288,'B2  宫苑—景阳山—瑶光',28,weight=500);crop(master,r,1300,310,610,460,reg['bbox']);text(r,1300,806,'无经纬度 · 不是与左图等尺度的局部',21,C['gold'])
  y=885
  for s in ['蓬莱为人工作山，不匹配现代天然峰。','景山殿／景阳山名物异读继续保留。','诸海地下联系不改画为地表河槽。']:
   y=para(r,1290,y,s,27,24)+12
 y=1200
 for i in range(1,7):
  cl=data['classes'][str(i)];x=1280+(i-1)%2*330;yy=y+(i-1)//2*47;co='#'+''.join(f'{a:02x}' for a in cl['rgb']);rect(r,x,yy-18,22,22,co,C['line']);text(r,x+31,yy,cl['name'],19)
 text(r,65,1408,'produced using Copernicus WorldDEM-30 © DLR e.V. and © Airbus Defence and Space GmbH · 非古地貌测绘',18,C['muted'])
 return r
