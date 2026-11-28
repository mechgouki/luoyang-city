from pathlib import Path
import json,hashlib,html,math,subprocess
P=Path(__file__).resolve().parent
SOURCE=P.parent/'city-plan-r11'/'yongning-published-plan.json'
before=SOURCE.read_bytes();d=json.loads(before)
assert len(d['components'])==23
W,H=1800,1510
s=1.08;ox,oy=40,210
parts=[]
def add(x):parts.append(x)
def txt(x,y,t,size=18,fill='#384841',weight='400',anchor='start',extra=''):
 add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" {extra}>{html.escape(t)}</text>')
def lines(x,y,ss,size=18,gap=29,fill='#53625b',weight='400'):
 for i,t in enumerate(ss):txt(x,y+i*gap,t,size,fill,weight)
def line(x1,y1,x2,y2,color='#A4AEA8',width=1.5,dash=None,extra=''):
 a=f' stroke-dasharray="{dash}"' if dash else ''
 add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"{a} {extra}/>')
def xy(p):return (ox+s*p[0],oy+s*p[1])
def path(ps):return ' '.join(f'{x},{y}' for x,y in ps)
meta={'title':'永宁寺院：可追溯平面','source_path':str(SOURCE),'source_sha256':hashlib.sha256(before).hexdigest(),'source_id':d['id'],'components_count':23,'source_url':d['source_refs'][0]['url'],'source_figure':'printed p.61, figure 2 right','output_transform':{'uniform_scale':s,'translate':[ox,oy],'rotation_deg':0},'north_arrow_source_px':d['calibration']['north_arrow'],'scale_bar_source_px':d['calibration']['scale_bar'],'supplemental_labels_not_geometry_constraints':['台基考古表值 38.2 m 见方','约 100 m 地下基概称','北门文献称似乌头门，位置未定'],'new_architectural_geometries':0,'geographic_registration_verified':False}
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">')
add('<title id="title">永宁寺院：可追溯平面</title><desc id="desc">只以刊载遗址平面的23个事实矢量组件统一等比绘制；保留原图北针与50米图尺，不作地理配准、不补造北门或僧房。</desc>')
add('<metadata>'+html.escape(json.dumps(meta,ensure_ascii=False))+'</metadata>')
add('<defs><marker id="north-head" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L7,3 L0,6 L2,3 Z" fill="#304A41"/></marker></defs>')
add('<g font-family="Noto Sans CJK SC, sans-serif">')
add(f'<rect width="{W}" height="{H}" fill="#FCFBF7"/>')
add('<rect x="1370" y="210" width="384" height="1158" rx="12" fill="#F1F3EE"/>')
txt(56,78,'永宁寺院：可追溯平面',40,'#263E35','700')
txt(58,119,'北魏洛阳永宁寺｜以刊载遗址总平面为据的等比例矢量重绘',22,'#57675f')
line(56,158,1744,158,'#CBD1C8',1.5)
txt(58,188,'图线和空白均按来源保留；未将平面事实改画为完整建筑复原。',18,'#67736b')
add(f'<g id="source-plan-components" transform="translate({ox},{oy}) scale({s})">')
# Place the faint underground outline first; source geometry itself stays untouched.
order=sorted(d['components'],key=lambda c: 0 if c['id']=='YN11-TOWER-FOUNDATION' else 1)
for c in order:
 cid=c['id'];typ=c['type'];g=c['geometry_type'];co=c['coordinates_px']
 sty='fill="none" stroke="#75857A" stroke-width="2.5"'
 if typ=='wall':sty='fill="none" stroke="#728277" stroke-width="3.2" stroke-dasharray="13 5 2 5"'
 elif cid=='YN11-TOWER-FOUNDATION':sty='fill="#E9EDE7" fill-opacity="0.50" stroke="#BDC7BB" stroke-width="2.2" stroke-dasharray="13 5 2 5"'
 elif cid.startswith('YN11-TOWER-'):sty='fill="#EBC794" stroke="#98672E" stroke-width="2.8"'
 elif typ in ['gate_foundation','hall_foundation'] or cid in ['YN11-BUDDHA-HALL','YN11-GATE-S','YN11-GATE-W']:
  sty='fill="#DCE7DF" stroke="#456A57" stroke-width="2.7"'
 elif typ=='road_edge':sty='fill="none" stroke="#B3BAB0" stroke-width="2.0" stroke-dasharray="12 5 2 5"'
 elif typ=='watercourse_edge':sty='fill="none" stroke="#8CA6AA" stroke-width="1.7" stroke-dasharray="10 4 2 4 2 4"'
 elif typ=='corner_structure':sty='fill="none" stroke="#728277" stroke-width="2.5" stroke-dasharray="8 4 2 4"'
 attrs=f'id="{cid}" data-source-geometry-type="{g}" data-source-coordinates="{html.escape(json.dumps(co,separators=(",",":")))}"'
 title=html.escape(c['label'])
 if g=='Polygon':add(f'<polygon {attrs} points="{path(co)}" {sty}><title>{title}</title></polygon>')
 elif g=='LineString':add(f'<polyline {attrs} points="{path(co)}" {sty}><title>{title}</title></polyline>')
 elif g=='Point':add(f'<circle {attrs} cx="{co[0]}" cy="{co[1]}" r="5" fill="#FCFBF7" stroke="#456A57" stroke-width="2.8"><title>{title}；点符号不表达门宽</title></circle>')
 else:raise ValueError(g)
add('</g>')
# North arrow uses exact source endpoints with no rotation correction.
a=xy(d['calibration']['north_arrow']['tail_px']);b=xy(d['calibration']['north_arrow']['tip_px'])
line(*a,*b,'#304A41',2.8,extra='marker-end="url(#north-head)"')
txt(78,241,'北',23,'#304A41','700','middle')
txt(96,431,'原图标北',16,'#647568','400','middle')
# Labels and leaders are annotations, never architectural outlines.
txt(759,247,'北墙保留原刊连续线',18,'#67776b','400','middle')
txt(*xy((670,303)),'佛殿基址',20,'#315444','600','middle')
txt(*xy((670,328)),'原刊图示框',15,'#647568','400','middle')
txt(*xy((671.5,576)),'木塔台基',21,'#815423','700','middle')
txt(*xy((671.5,609)),'38.2 m 方',20,'#815423','600','middle')
txt(*xy((671.5,635)),'考古表值',14,'#866C46','400','middle')
txt(*xy((671.5,696)),'四慢道：按刊图凸出轮廓',17,'#8F6D3C','400','middle')
txt(*xy((671.5,719)),'不补画踏步、坡度与栏杆',15,'#7A846D','400','middle')
line(*xy((832,690)),*xy((856,690)),'#AAB7A5',1.5)
lines(*xy((870,662)),['地下基图示范围','约 100 m（概称）','不按表值改形'],16,25,'#6E7F6B')
line(*xy((372,592)),*xy((390,592)),'#93A590',1.5)
lines(*xy((403,583)),['西门基址','原刊轮廓'],17,27,'#456A57')
line(*xy((991,625)),*xy((1001,625)),'#93A590',1.5)
lines(*xy((1008,620)),['东门标位','不示门宽'],17,27,'#456A57')
txt(*xy((676,1034)),'南门基址',20,'#315444','600','middle')
line(*xy((342,982)),*xy((373,1019)),'#A0AAA0',1.4)
txt(*xy((382,1028)),'西南角楼：仅可辨边线',16,'#6C7D6E')
x,y=xy((140,720));txt(x,y,'津阳门大道（原图名）',19,'#858F80','400','middle',f'transform="rotate(-90 {x} {y})"')
x,y=xy((1080,300));txt(x,y,'寺东水沟（图示）',17,'#7D9698','400','middle',f'transform="rotate(-90 {x} {y})"')
x,y=xy((1170,720));txt(x,y,'寺东坊间路（图示）',17,'#8B9484','400','middle',f'transform="rotate(-90 {x} {y})"')
# Scale bar has the same source 157px * uniform scale as all plan geometry.
xs,ys=xy(d['calibration']['scale_bar']['start_px']);xe,ye=xy(d['calibration']['scale_bar']['end_px']);mid=(xs+xe)/2
add(f'<rect x="{xs}" y="{ys-10}" width="{mid-xs}" height="10" fill="#304A41"/>')
add(f'<rect x="{mid}" y="{ys-10}" width="{xe-mid}" height="10" fill="#FCFBF7" stroke="#304A41" stroke-width="1.5"/>')
txt(xs,ys+25,'0',16,'#456052','400','middle');txt(mid,ys+25,'25',16,'#456052','400','middle');txt(xe,ys+25,'50 m',16,'#456052','400','middle')
# Side panel.
px=1398
txt(px,256,'图例',25,'#304A41','700')
legend=[('台基与四侧慢道轮廓','#EBC794','#98672E',None),('佛殿 / 门址图示框','#DCE7DF','#456A57',None),('地下基图示范围','#E9EDE7','#BDC7BB','10 4 2 4'),('寺墙 / 道路图示线',None,'#728277','10 4 2 4'),('水沟图示边线',None,'#8CA6AA','10 4 2 4 2 4')]
for i,(lab,fill,stroke,dash) in enumerate(legend):
 y=306+i*57
 if fill:add(f'<rect x="{px}" y="{y-18}" width="35" height="22" fill="{fill}" stroke="{stroke}" stroke-width="2"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
 else:line(px,y-7,px+35,y-7,stroke,2.5,dash)
 txt(px+49,y,lab,18,'#415C4D')
lines(px,593,['颜色用于突出对象，','不代表“全部发掘”或测绘等级。'],16,25,'#6E7D70')
line(px,640,1726,640,'#D0D8CD',1.2)
txt(px,681,'北门仅作文字注记',22,'#304A41','700')
lines(px,721,['文献称似乌头门，位置未定。','源图无可辨北门基址，','本图未在北墙补画开口。'],18,29)
txt(px,846,'尺度如何阅读',22,'#304A41','700')
lines(px,886,['50 m 图尺源长 157 px；','23 个组件全用同一缩放。','台基约 39 m 为刊图图读，','38.2 m 为考古尺寸表值；','二者差异不通过拉伸消除。'],18,29)
lines(px,1063,['北针保持来源图方向，','不等于核验后的地理真北。'],18,29)
txt(px,1178,'留白不等于“空院”',22,'#304A41','700')
lines(px,1219,['未增绘僧房、廊庑、院内路，','也未补齐尚缺证据的建筑。','单一刊图不等于某年的','完整同层营建平面。'],18,29)
line(56,1413,1744,1413,'#CBD1C8',1.5)
lines(58,1446,['原源图：杭侃《〈洛阳伽蓝记〉慧嶷故事四论》，《故宫博物院院刊》2025 年第 11 期，p.61 图二右；重刊自 1996 年考古报告 p.7。','事实矢量：R11 yongning-published-plan.json｜原刊坐标与统一图尺；未地理配准。表值标签不参与几何拟合。绘制：2026-11-28。'],17,28,'#6A776D')
add('</g></svg>')
out=P/'our-temple-plan.svg';out.write_text('\n'.join(parts))
(P/'our-temple-plan.metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
assert SOURCE.read_bytes()==before
print(out)
