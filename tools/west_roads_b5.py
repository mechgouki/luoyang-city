#!/usr/bin/env python3
"""Continue the original literary map through R02; preserve all prior releases."""
from pathlib import Path
import csv,json,re,zipfile,xml.etree.ElementTree as ET
import cairosvg
from dual_cartography import NS,C,load,dump,node,text,para,rect,path,svg,world,crop,write_svg
from north_b4 import sha,fp,heading,gate_icon,render_atlas

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'_site'
DATA=ROOT/'research/dual-b5/west-roads.json'
NODES={
 'w_dajue':('wnode144',2250,3830,'T64 大觉寺','寺期未定 · 晚塔另记','temple',True),
 'w_rongjue':('wnode145',3640,3830,'T63 融觉寺','五层塔构件另页计时','temple',False),
 'w_linhuaizhai':('wnode146',2860,3940,'P221 临淮王彧宅','法云北 · 宅界未定','house',False),
 'w_fayun':('wnode147',2860,4400,'T60 法云寺','寺期未定 · 路侧未记','temple',True),
 'w_baoguang':('wnode148',3670,4400,'T59 宝光寺','寺期未定 · 园池不定岸','temple',True),
 'w_baima_xiyang':('wnode149',2720,5130,'T58 白马〔西阳条〕','寺期未定 · 两条不强合','temple',True),
 'w_xuanzhong':('wnode150',3620,5130,'T56 城阳王徽宅','后宣忠 · 宅寺分时','house',False),
 'w_chongjue':('wnode151',3620,5840,'T55 冲觉寺','舍宅寺 · 塔完工未记','temple',False),
}
GATES={'gate_changhe_west':(4400,3550),'gate_xiyang':(4400,4750),'gate_ximing':(4400,6100)}
SIDECARS=('w_yongming','w_wangdianyu')

def type_icon(parent,x,y,kind,undated=False,scale=1):
 g=node(parent,'g',transform=f'translate({x} {y}) scale({scale})')
 co=C['gold'] if kind=='house' else C['green']
 path(g,'M-52 -6L0 -35L52 -6',co,4)
 rect(g,-37,-5,74,39,'none' if undated else C['paper'],co,3)
 if kind=='house':
  path(g,'M-15 34V12H15V34 M-31 1H-19V13H-31Z M19 1H31V13H19Z',co,2)
 else:
  path(g,'M-22 -3V33 M0 -3V33 M22 -3V33 M-44 40H44',co,2)
 if undated:path(g,'M-65 -42H-75V48H-65 M65 -42H75V48H65',C['gold'],2,'6 5')
 return g

def node_group(eid,entry):
 cls,x,y,label,note,kind,undated=entry
 g=ET.Element('{'+NS+'}g',{'class':cls,'data-entity-id':eid,'data-batch':'dual-b5','data-footprint':'false','data-temporal-display':'undated' if undated else 'composite','style':'pointer-events:none'})
 node(g,'title').text=label+'；仅类型图符，锚点不动。'+note+'。'
 type_icon(g,x,y,kind,undated)
 text(g,x,y+79,label,29,C['gold'] if kind=='house' else C['green'],'middle',500)
 text(g,x,y+116,note,21,C['muted'],'middle')
 return g

def changed_master(source,markers):
 root=ET.parse(source).getroot();wg=world(root);before=[ET.tostring(c) for c in wg]
 changed=set();audit=[]
 for eid,entry in NODES.items():
  cls,x,y,*_=entry;m=next(m for m in markers if eid in m['ids'])
  assert m['kind']=='node' and (m['x'],m['y'])==(x,y),eid
  old=[c for c in wg if c.get('class')==cls];assert len(old)==1,cls
  i=list(wg).index(old[0]);wg.remove(old[0]);wg.insert(i,node_group(eid,entry));changed.add(i)
  audit.append({'entity_id':eid,'literary_xy':[x,y],'anchor_moved':False,'geographic_coordinates':None,'type':entry[5],'tower_added_to_master':False})
 assert all(ET.tostring(c)==before[i] for i,c in enumerate(wg) if i not in changed)
 gates=node(wg,'g',id='west-roads-glyphs-b5',style='pointer-events:none')
 for eid,(x,y) in GATES.items():
  m=next(m for m in markers if eid in m['ids']);assert (m['x'],m['y'])==(x,y)
  g=node(gates,'g',data_entity_id=eid,data_batch='dual-b5',data_footprint='false')
  node(g,'title').text='西城门通行类型；楼层、实际立面与开间未指定。'
  gate_icon(g,x,y,False,.8)
  audit.append({'entity_id':eid,'literary_xy':[x,y],'anchor_moved':False,'geographic_coordinates':None,'type':'gate','storeys':None})
 for batch,count in [('dual-b1',7),('dual-b2',8),('dual-b4',4)]:
  assert sum(n.get('data-batch')==batch for n in root.iter())==count,batch
 assert sum(n.get('id')=='west-glyphs-b3' for n in root.iter())==1
 assert not any(n.get('data-entity-id') in SIDECARS and n.get('data-batch')=='dual-b5' for n in root.iter())
 for n in root:
  if n.get('class')=='wt497 tb497':
   for c in list(n):n.remove(c)
   n.text='北魏洛阳 · 文献复原工作图 B5'
 result={'type_groups_changed':11,'nodes_replaced':8,'gate_symbols_added':3,'anchors_moved':False,'new_ancient_coordinates':0,'source_sha256':sha(source),'changes':audit,'nonspatial_sidecars_preserved':list(SIDECARS)}
 node(root,'metadata').text=json.dumps(result,ensure_ascii=False)
 return root,result

def card(r,x,y,w,h,title,body,size=24):
 rect(r,x,y,w,h,'#f0f2e8',C['line'],2,9)
 text(r,x+28,y+48,title,29,C['green'],weight=500)
 return para(r,x+28,y+95,body,(w-56)/size,size)

def literary_plate(master,reg,archive=False):
 r=svg(2200,1560,'城西三门道 / '+('v2.4封存同区' if archive else 'B5文献类型图'))
 heading(r,'LUOYANG / L07 / '+('ARCHIVE' if archive else 'B5'),'城西三门道：寺院与王宅','516—528 盛时综合语境；↑ 北；沿用原文献锚点，不提供实测地理比例。')
 rect(r,75,240,1110,1205,'#f0f2e9',C['line'],2,9)
 crop(master,r,92,257,1076,1170,reg['bbox'])
 card(r,1240,240,885,320,'01  三条门道，各有路侧','城西阊阖、西阳、西明保持原城门身份。融觉在阊阖道南；宝光在西阳道北；冲觉在西明道北。门符不指定楼层。')
 card(r,1240,590,885,400,'02  两项关系继续留旁注','永明只得大觉东，未定与融觉先后或路侧；王典御只得宣忠寺东，未定御道侧别。宜年两宅仍是里内无序成员。阅读组锚点不转为寺址。')
 card(r,1240,1020,885,425,'03  宅、寺、塔分别表达','城阳王徽宅在盛时层保留宅型。大觉、法云、宝光、白马西阳条继续标寺期未定。塔层数、营建事件与完工时间见构件板，主图本批不添塔。')
 text(r,75,1515,('封存母图原样裁切。' if archive else '本批8节点类型＋3门符；B1—B4保持；永明与王典御的非定位旁注不动。')+' 图符边线不代表寺界或宅界。',21,C['muted'])
 return r

def relation_line(r,y,left,right,label):
 rect(r,120,y,410,78,C['paper'],C['line'],1,7);text(r,325,y+50,left,27,C['ink'],'middle')
 rect(r,1190,y,650,78,C['paper'],C['line'],1,7);text(r,1515,y+50,right,27,C['ink'],'middle')
 path(r,f'M555 {y+40}H1160 M1141 {y+29}L1160 {y+40}L1141 {y+51}',C['gold'],3)
 text(r,850,y+25,label,23,C['gold'],'middle')

def relations_plate():
 r=svg(2000,1560,'B5 已知偏序、路侧与近邻关系')
 heading(r,'B5 / 相对关系','寺序保留分支，路侧逐条核对','每行与每块面板各自阅读；相同列、连线长度和图框宽度没有地理含义。',2000)
 rect(r,75,245,1850,430,'#edf0e5',C['line'],2,10)
 text(r,110,298,'01  大觉、融觉、永明与宜年的已知关系',28,C['green'],weight=500)
 relation_line(r,328,'大觉寺','融觉寺','向东 · 一里许')
 relation_line(r,423,'大觉寺','永明寺〔旁注〕','向东 · 距离未记')
 relation_line(r,518,'宜年里〔关系〕','永明寺〔旁注〕','向东 · 距离未记')
 text(r,120,643,'融觉 / 永明的先后仍开放；融觉的御道南不能沿上述关系传给其他对象。',23,C['muted'])
 rect(r,75,705,900,450,'#f1f3e9',C['line'],2,10)
 text(r,110,761,'02  法云—宝光：西向与近邻',28,C['green'],weight=500)
 rect(r,115,805,335,85,C['paper'],C['line'],1,8);text(r,282,859,'法云寺',28,C['ink'],'middle')
 rect(r,600,805,335,85,C['paper'],C['line'],1,8);text(r,767,859,'宝光寺',28,C['ink'],'middle')
 path(r,'M470 845H580',C['green'],3,'10 7');text(r,525,801,'隔墙并门',20,C['green'],'middle')
 para(r,115,943,'宝光在西阳道北；法云在宝光西，隔墙并门，路侧未独立明记。临淮王彧宅在法云北，咸池属宝光园。墙线与院形未定。',33,25)
 rect(r,1010,705,915,450,'#f1f3e9',C['line'],2,10)
 text(r,1045,761,'03  西阳道南与寺东关系',28,C['green'],weight=500)
 para(r,1045,824,'西阳门外一里：城阳王徽宅〔后宣忠〕。\n西阳门外三里：白马西阳条。\n王典御寺：宣忠寺东，留非定位旁注。',32,26)
 para(r,1045,1025,'距门里数不换算为图面像素；宣忠的道南侧别不传给王典御。',32,24)
 rect(r,75,1185,1850,250,'#edf0e5',C['line'],2,10)
 text(r,110,1241,'04  西明门道：冲觉寺的两个独立约束',29,C['green'],weight=500)
 text(r,120,1318,'门外一里',33,C['ink']);text(r,610,1318,'御道北',33,C['ink'])
 para(r,1085,1291,'保留量距和路侧；距离端点未知，不从塔心反推一里。',30,25)
 text(r,75,1507,'城西阊阖门与宫前阊阖门分开；同名寺、未定路侧和跨期构件不生成新的地理点。',23,C['muted'])
 return r

def layers_plate():
 r=svg(2200,1560,'B5 宅寺变迁与塔构件条件')
 heading(r,'B5 / 建筑构件与时间','先辨宅与寺，再读塔的营造阶段','横向卡片是事件次序；列宽不表示持续时间。寺期未定与塔期晚出分别判断。')
 rect(r,75,240,2050,315,'#edf0e5',C['line'],2,10)
 text(r,110,295,'01  城阳王徽宅 → 后宣忠寺',31,C['green'],weight=500)
 for x,title,body in [(110,'516—528 主图','保留王宅名称与宅型'),(800,'529 胜负未决','发愿舍宅为寺'),(1490,'529 北海败散后','兑现舍宅；竣工日未载')]:
  rect(r,x,330,600,135,C['paper'],C['line'],1,8);text(r,x+25,377,title,26,C['ink']);text(r,x+25,424,body,24,C['muted'])
 text(r,110,515,'原文回述不把后出的寺名提前到整个盛时断面。',24,C['muted'])
 rect(r,75,590,2050,590,'#f1f3e9',C['line'],2,10)
 text(r,110,648,'02  构件条件表：层数与落成日期分开',31,C['green'],weight=500)
 rows=[('融觉','五层塔记述','落成年未单记；一／三里范围异文不作寺界'),('冲觉','五层塔记述','孝昌元年复政后追福；528前是否完工未证'),('宝光','三层塔／石基','寺期未定；石基不推成全塔石造'),('王典御','三层塔记述','构件随非定位旁注；落成年、路侧未定'),('大觉','永熙砖塔','532—534晚出；原文未给层数')]
 for i,(name,component,note) in enumerate(rows):
  y=690+i*88
  rect(r,110,y,1980,73,C['paper'],C['line'],1,6)
  text(r,138,y+47,name,26,C['ink']);text(r,440,y+47,component,25,C['green']);text(r,940,y+47,note,24,C['muted'])
 rect(r,75,1215,2050,220,'#edf0e5',C['line'],2,10)
 text(r,110,1271,'03  仍然开放的材料',29,C['green'],weight=500)
 para(r,110,1322,'大觉原宅堂的怀／环异文保留版本条件；永明千余间与三千余僧不展开成逐间平面。陈留王舍半宅安置佛徒未给寺名；白马两条记录的同异未定。',76,25)
 text(r,75,1510,'本批在主图使用寺、宅、门类型图符；这张表中的塔描述未自动转成盛时完成状态。',23,C['muted'])
 return r

def evidence_plate(data):
 r=svg(2200,1700,'B5 原文与研究记录索引')
 heading(r,'B5 / 文献与采用解释','证据索引：原文、校读与图示分别保存','完整引文、版本差异、时层与图示限制见专题页；现代整理本仍属同一原书来源家族。')
 es=data['evidence'];rows=(len(es)+1)//2;assert rows<=12
 for i,e in enumerate(es):
  col=i//rows;row=i%rows;x=75+1050*col;y=245+row*82
  rect(r,x,y,1005,70,'#eff1e7',C['line'],1,6)
  title=e['id']+' · '+e['title'];text(r,x+20,y+30,title,23,C['ink'])
  text(r,x+20,y+56,'引文采用 '+e['quote_source']+' · 年代与未定位置分别登记',18,C['muted'])
 text(r,75,1297,'电子文本与校注',29,C['green'],weight=500)
 assert len(data['sources'])<=6
 for i,s in enumerate(data['sources']):
  x=75+(i//3)*1050;y=1340+(i%3)*61
  text(r,x,y,s['id']+' · '+s['title'],20,C['muted'])
  text(r,x,y+27,s['url'],18,C['muted'])
 para(r,75,1550,'地形并行专题已核到数字化提供者的基准处理记录；原纸图与后期数字产品的坐标定义分层登记。独立地面检查及古代水系落位仍是后续工作。',88,23)
 text(r,75,1660,'在线逐条查阅：https://mechgouki.github.io/luoyang-city/dual-west-roads.html · 2026-11-13',21,C['muted'])
 return r

def main():
 data=load(DATA);info=load(SITE/'build-info.json')
 assert info.get('north_b4',{}).get('records')==16
 assert (SITE/'historical-datum/metadata.json').exists()
 assert len(data['evidence'])<=24 and all(e['geographic_coordinates'] is None for e in data['evidence'])
 assert not (SITE/'dual-west-roads.html').exists(),'Rebuild all preceding stages before B5'
 protected={str(p.relative_to(SITE)):sha(p) for p in SITE.rglob('*') if p.is_file() and p.name not in ['build-info.json','index.html','v3.0-dual.html','release.json']}
 master,audit=changed_master(SITE/'assets/master-dual-b4-north.svg',load(SITE/'data/markers.json'))
 master_file=SITE/'assets/master-dual-b5-west-roads.svg';write_svg(master_file,master)
 out=SITE/'dual/maps'
 write_svg(out/'L07.svg',literary_plate(master,data['region']))
 write_svg(out/'L07-archive.svg',literary_plate(ET.parse(SITE/'assets/master-v24.svg').getroot(),data['region'],True))
 write_svg(out/'W5-relations.svg',relations_plate());write_svg(out/'W5-layers.svg',layers_plate());write_svg(out/'W5-evidence.svg',evidence_plate(data))
 data['source_commit']=info['source_commit'];data['drawing_audit']=audit
 dump(SITE/'dual/west-roads-b5.json',data)
 (SITE/'dual-west-roads.html').write_bytes((ROOT/'web/west-roads-b5.html').read_bytes())
 (SITE/'west-roads-b5.js').write_bytes((ROOT/'web/west-roads-b5.js').read_bytes())
 with (SITE/'downloads/dual-west-roads-b5-evidence.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['编号','主题','实体ID','引文来源','原文','采用读法','画法','保留限制','时层'])
  for e in data['evidence']:w.writerow([e['id'],e['title'],';'.join(e['entities']),e['quote_source'],e['quote'],e['reading'],e['drawing'],e['limit'],e.get('temporal_note','')])
 plates=[out/'L07.svg',out/'W5-relations.svg',out/'W5-layers.svg',SITE/'historical-datum/source-summary.svg',SITE/'historical-datum/review-summary.svg',out/'W5-evidence.svg']
 render_atlas(plates,SITE/'downloads/dual-west-roads-b5-atlas.pdf')
 cairosvg.svg2png(url=str(out/'W5-relations.svg'),write_to=str(SITE/'dual/west-roads-b5-preview.png'),output_width=1600)
 index=(SITE/'index.html').read_text();match=re.search(r'<script src="\./([^"]+-runtime\.js)"></script>',index);assert match
 boot=(SITE/match.group(1)).read_text();m=re.search(r'window\.ATLAS_ASSETS=(.*?);\n',boot);assert m
 mapping=json.loads(m.group(1));mapping['assets/master-v28-review.svg']=fp(master_file.name,master_file.read_bytes())
 boot=boot[:m.start(1)]+json.dumps(mapping,ensure_ascii=False)+boot[m.end(1):];index=index.replace(match.group(1),fp('runtime.js',boot.encode()),1)
 banner='<section id="west-roads-b5-entry" style="margin:16px 0;padding:23px;border:1px solid #bbbea7;background:#eeefe2;border-radius:8px"><h2>城西三门道 · B5</h2><p>寺序、宅改寺与建筑构件分别核对；原有锚点保留。历史图研究另核清原纸图与后期数字坐标的来历。</p><p><a href="./dual-west-roads.html#literary?id=WR01">进入城西三门道 ↗</a>　<a href="./historical-datum.html">查看历史图基准研究 ↗</a>　<a href="./downloads/dual-west-roads-b5-atlas.pdf">下载本批图册 ↗</a></p></section>'
 assert index.count('id="north-b4-entry"')==1
 index=index.replace('<section id="north-b4-entry"',banner+'<section id="north-b4-entry"',1)
 index=index.replace('<nav aria-label="主导航" class="topnav">','<nav aria-label="主导航" class="topnav"><a href="./dual-west-roads.html">城西门道B5 ↗</a>',1)
 js=fp('west-roads-main-b5.js',(ROOT/'web/west-roads-main-b5.js').read_bytes());index=index.replace('</body>',f'<script defer src="./{js}"></script></body>')
 (SITE/'index.html').write_text(index);(SITE/'v3.0-dual.html').write_text(index)
 release=load(SITE/'release.json');release['extensions']=sorted(set(release.get('extensions',[])+['dual-west-roads-b5','historical-datum-b5']));release['current_milestone']='B5 城西三门道与历史地图基准核查';dump(SITE/'release.json',release)
 assert all(sha(SITE/p)==h for p,h in protected.items()),'B5 modified a protected prior resource'
 dump(SITE/'dual/west-roads-b5-preservation.json',{'protected_files':len(protected),'protected_unchanged':True,'sha256':protected})
 with zipfile.ZipFile(SITE/'downloads/dual-west-roads-b5-package.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in plates+[out/'L07-archive.svg',master_file,SITE/'dual/west-roads-b5.json',SITE/'downloads/dual-west-roads-b5-evidence.csv',SITE/'downloads/dual-west-roads-b5-atlas.pdf',ROOT/'docs/dual-west-roads-b5-research.md',ROOT/'docs/historical-datum-b5-research.md']:
   z.write(p,('docs/'+p.name) if p.is_relative_to(ROOT/'docs') else str(p.relative_to(SITE)))
 info['west_roads_b5']={'source_commit':info['source_commit'],'records':len(data['evidence']),'region':'L07','type_groups_changed':11,'nonspatial_sidecars_preserved':list(SIDECARS),'new_ancient_coordinates':0,'previous_release_preserved':'B1+B2+B3+B4','protected_files':len(protected)}
 info['historical_datum_b5']={'metadata':'historical-datum/metadata.json','original_horizontal_datum_identified':False,'ancient_coordinates_added':0}
 info['files_sha256']={str(p.relative_to(SITE)):sha(p) for p in sorted(SITE.rglob('*')) if p.is_file() and p.name!='build-info.json'};dump(SITE/'build-info.json',info)
 print('Built B5:',len(data['evidence']),'evidence, 11 type groups, L07, six-page atlas; protected',len(protected))

if __name__=='__main__':main()
