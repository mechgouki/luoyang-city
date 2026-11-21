"""Publish the 21-source road register without merging independent source frames."""
import csv
import hashlib
import json
import shutil
from collections import Counter
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'research/roads-r6'
V4 = ROOT / 'research/prosperity-v4'
BASE = 'https://mechgouki.github.io/luoyang-city/'
PAGE = 'luoyang-road-atlas.html'
FOLDER = 'road-atlas'
KEY = 'road_locations'
VERSION = 'road-atlas-r6.1'
MANIFEST = FOLDER + '/manifest.json'
BUNDLE = 'downloads/luoyang-road-atlas.zip'
DOWNLOADS = {
    FOLDER + '/city-roads.svg': '全城主干道分级定位图 · SVG',
    FOLDER + '/roads.csv': '21 条逐路证据表 · CSV',
    FOLDER + '/roads.json': '完整来源、读点与对应关系 · JSON',
    MANIFEST: '版本与校验清单 · JSON',
    BUNDLE: '完整离线图集 · ZIP',
}
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
TEAL, AMBER, BLUE, INK, MUTED = '#24685f', '#ad6439', '#697c9a', '#243b38', '#667367'
PAPER = '#faf7ed'


def load(path):
    return json.loads(path.read_text())


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tag(parent, name, **attrs):
    return ET.SubElement(parent, '{' + NS + '}' + name,
                         {k.rstrip('_').replace('_', '-'): str(v) for k, v in attrs.items()})


def text(parent, x, y, value, size=16, color=INK, **attrs):
    node = tag(parent, 'text', x=x, y=y, fill=color, font_size=size,
               font_family='Noto Sans CJK SC, sans-serif', **attrs)
    node.text = value
    return node


def line(parent, points, color=TEAL, width=2, **attrs):
    return tag(parent, 'polyline', points=' '.join(f'{x},{y}' for x,y in points),
               fill='none', stroke=color, stroke_width=width,
               stroke_linecap='round', stroke_linejoin='round', **attrs)


def route_link(parent, rid, title, **attrs):
    a = tag(parent, 'a', href=BASE+PAGE+'#'+rid, tabindex=0, data_road_ref=rid, **attrs)
    tag(a, 'title').text = title
    return a


def unknown(parent, xy, radius, **attrs):
    return tag(parent, 'circle', cx=xy[0], cy=xy[1], r=radius,
               fill=PAPER, stroke=AMBER, stroke_width=radius/2.2,
               data_layer='unknown', **attrs)


def plate(data, atlas):
    """All transforms below arrange panels, never register one source into another."""
    root = ET.Element('{' + NS + '}svg', {
        'viewBox':'0 0 1440 1230', 'width':'1440', 'height':'1230',
        'role':'img', 'aria-labelledby':'road-map-title road-map-description', 'lang':'zh-CN'})
    tag(root,'title',id='road-map-title').text = '盛时洛阳全城主干道分级定位图'
    tag(root,'desc',id='road-map-description').text = ('21条来源记录。左图保留图06a的8条道路原始分段；右图在钱氏复原图框中显示5条样线和6组门端关系。实线表示可摘读图迹，虚线为示意连接，空圈表示实测端点未定。下方局部关系不按地理比例。')
    tag(root,'rect',width=1440,height=1230,fill=PAPER)
    text(root,32,47,'盛时洛阳 · 全城主干道分级定位',30,font_weight=600)
    text(root,33,79,'研究时段 516—528 年  /  21 条来源记录逐项对照  /  两幅来源图框分别读取',15,MUTED)
    line(root,[[33,109],[76,109]],TEAL,4)
    text(root,88,115,'实线：来源图可读路迹',16)
    line(root,[[347,109],[390,109]],AMBER,3,stroke_dasharray='8 7')
    text(root,402,115,'虚线：门端间示意连接',16)
    unknown(root,[676,109],5)
    text(root,690,115,'空圈：最后实测点／登陆点未知',16)
    text(root,1030,115,'图面依据不等于全线实测',15,AMBER)
    for x,w in [(28,590),(638,774)]:
        tag(root,'rect',x=x,y=140,width=w,height=680,rx=5,fill='#fffdf7',stroke='#d1d6c7')
    text(root,48,173,'A  内城：图06a道路原段',22,font_weight=600)
    text(root,48,199,'申遗资料 · 原PDF点坐标 · 原分段与缺口不补连',14,MUTED)
    text(root,658,173,'B  外郭与城南：钱氏图独立读框',22,font_weight=600)
    text(root,658,199,'2018 图一 / 2024 图6转载 · 原图像素 · 与A图没有配准',14,MUTED)
    features={f['id']:f for f in atlas['features']}
    # PDF coordinates remain numerically identical to the source paths.
    core = tag(root,'g', transform='translate(-650 -400) scale(2.85)', data_frame='frame-06a')
    for fid in ['geo-inner-wall-aboveground','geo-inner-wall-underground','geo-palace-walls','geo-yongning-temple-walls']:
        g=features[fid]['source_pdf_geometry']
        for coords in ([g['coordinates']] if g['type']=='LineString' else g['coordinates']):
            line(core,coords,'#a5b1a2',0.8,stroke_dasharray='1.4 1' if 'underground' in fid else 'none',data_source_feature=fid)
    nr=load(V4/'network-462/roads.json')['routes']
    rd=load(V4/'hydro-roads-anchor-p46.json')['main_road_records']
    by_feature={r['p1_feature_id']:r for r in nr}
    label_positions={'R01':(320,360),'R02':(333,333),'R03':(306,389),'R04':(307,290),
                     'R05':(293,261),'R06':(367,355),'R07':(338,346),'R08':(297,305)}
    names={r['id']:r['name'] for r in data['roads']}
    for record in rd[:8]:
        rid=record['id']; route=by_feature[record['registered_source_feature_id']]
        a=route_link(core,rid,names[rid]); g=tag(a,'g',data_layer='source')
        segments=route['source_pdf_geometry']['coordinates']
        for part,coords in enumerate(segments):
            line(g,coords,TEAL,1.25,data_source_feature=route['p1_feature_id'],data_part=part)
        for xy in [segments[0][0],segments[-1][-1]]:
            unknown(a,xy,1.4,data_geometry_role='source-trace-end-not-ancient-terminus')
        x,y=label_positions[rid]
        tag(a,'rect',x=x-1,y=y-4.2,width=11,height=5.3,fill='#fffdf7',rx=.6)
        text(a,x,y,rid,4.7,TEAL,font_weight=700)
    gates=[('geo-daxia-gate','大夏',-2,-5,'end'),('geo-guangmo-gate','广莫',2,-5,'start'),
           ('geo-jianchun-gate','建春',3,2,'start'),('geo-dongyang-gate','东阳',3,2,'start'),
           ('geo-qingyang-gate','青阳',3,2,'start'),('geo-ximing-gate','西明',-3,2,'end'),
           ('geo-xiyang-gate','西阳',-3,2,'end'),('geo-changhe-palace-gate','宫前阊阖',-4,-5,'end')]
    for fid,label,dx,dy,anchor in gates:
        x,y=features[fid]['source_pdf_geometry']['coordinates']
        tag(core,'circle',cx=x,cy=y,r=1.1,fill=INK)
        text(core,x+dx,y+dy,label,4.6,MUTED,text_anchor=anchor)
    text(core,322,278,'宫城',6,'#859280',text_anchor='middle')
    text(core,327,374,'内城',6,'#859280',text_anchor='middle')
    text(root,50,230,'北 ↑',14,MUTED)
    text(root,48,761,'R03 ↔ X01：西明—青阳大道的同路候选对应；',14,AMBER)
    text(root,48,784,'发掘窗口尚未取得可贴入本图的共同测线。',14,MUTED)
    text(root,48,806,'南端不补至宣阳、平昌、开阳等未定门址。',14,MUTED)
    north=load(V4/'gates-465/readings.json')['later_plan']
    south=load(V4/'south-466/readings.json')['plan']
    outer=load(V4/'network-462/outer.json')
    q=tag(root,'g',transform='translate(659 230) scale(.61)',data_frame='frame-qian2018')
    for field in ['inner_wall_px','outer_wall_px']:
        line(q,north[field],'#a5b1a2',3,data_source_path='gates-465/later_plan.'+field)
    text(q,540,335,'内城',26,'#8b9585')
    text(q,447,367,'不在本图补绘内部道路',18,MUTED)
    text(q,39,35,'北 ↑',21,MUTED)
    text(q,12,868,'六条东西外道只有门端读点；虚线只表示配对关系。',21,AMBER)
    text(q,12,904,'五条南北／承明样线据复原图摘读，原测点仍待核。',21,MUTED)
    # Only five outer records have traced strokes; six are endpoint pairs.
    outer_ids={'W1':'O01','W2':'O02','W3':'O03','E1':'O07','E2':'O08','E3':'O09'}
    for c in outer['corridors']:
        rid=outer_ids[c['id']]; a=route_link(q,rid,names[rid])
        points=[c['inner_station_px'],c['outer_station_px']]
        line(a,points,AMBER,3,stroke_dasharray='10 10',data_layer='inferred',data_geometry_role='endpoint-pair-connector')
        for i,xy in enumerate(points):
            if i==1: unknown(a,xy,6,data_geometry_role='not-survey-terminus')
            else: tag(a,'circle',cx=xy[0],cy=xy[1],r=4,fill=INK)
        x,y=c['inner_station_px']
        west=c['id'].startswith('W')
        gate_name='西垣阊阖' if rid=='O03' else c['inner_gate'].replace('内城','')
        text(a,x+(-10 if west else 10),y-14,gate_name,20,INK,text_anchor='end' if west else 'start')
        xx,yy=c['outer_station_px']
        text(a,xx+(10 if west else -10),yy-14,rid,21,AMBER,text_anchor='start' if west else 'end',font_weight=600)
    west=route_link(q,'O04',names['O04'])
    line(west,north['west']['trace_px'],BLUE,4,data_layer='source')
    unknown(west,north['west']['trace_px'][-1],5)
    text(west,402,189,'O04 承明西短段',19,BLUE,text_anchor='end')
    for rid,r in zip(['O05','O06'],north['north']):
        a=route_link(q,rid,names[rid])
        for field in ['to_wall_px','beyond_wall_to_frame_px']:
            line(a,r[field],BLUE,4,data_layer='source')
        xy=r['beyond_wall_to_frame_px'][-1]; unknown(a,xy,6)
        xx,yy=r['to_wall_px'][0];tag(a,'circle',cx=xx,cy=yy,r=4,fill=INK)
        dx=-14 if rid=='O05' else 14
        text(a,xx+dx,yy-16 if rid=='O05' else yy+28,rid+' '+r['name'],19,BLUE,text_anchor='end' if dx<0 else 'start')
    text(q,790,35,'邙山合流点未定',19,AMBER)
    for rid,name in [('O10','开阳'),('O11','平昌')]:
        a=route_link(q,rid,names[rid]); coords=south['road_samples_px'][name]
        line(a,coords,BLUE,4,data_layer='source')
        unknown(a,coords[-1],6)
        x,y=coords[0]; dx=16 if rid=='O10' else -16
        text(a,x+dx,y-22,rid,21,BLUE,text_anchor='start' if dx>0 else 'end',font_weight=600)
        text(a,x+dx,y-1,name,18,BLUE,text_anchor='start' if dx>0 else 'end')
    # The source's river band remains explicitly a later reconstruction.
    water=tag(q,'g',data_layer='inferred',data_geometry_role='later-reconstruction-water')
    for field in ['north_bank_sample_px','south_bank_sample_px']:
        line(water,south[field],'#88aaa7',2.5,stroke_dasharray='6 8',data_source_path='south-466/plan.'+field)
    for name in ['津阳','宣阳']:
        a=route_link(q,'S03','城南御道与永桥 · 相关背景线，不增入21条道路记录')
        line(a,south['road_samples_px'][name], '#9daab0',3,data_layer='source')
        x,y=south['road_samples_px'][name][0]; text(a,x-7,y-14,name,17,MUTED,text_anchor='end')
    a=route_link(q,'S03','永桥图符两端，不是已定登陆点')
    line(a,south['bridge_symbol_ends_px'],BLUE,6,data_layer='source')
    for xy in south['bridge_symbol_ends_px']:unknown(a,xy,6)
    text(a,535,691,'永桥图符',20,BLUE,text_anchor='end')
    text(q,394,791,'古洛水河带：后期复原图参照',19,'#71908b')
    for name,xy in south['places_px'].items():
        tag(q,'circle',cx=xy[0],cy=xy[1],r=3,fill='#a1ab9e')
    text(q,729,667,'明堂、辟雍等图符',18,MUTED)
    text(root,659,806,'B图中的图尺、门端和线端均不作为新增北魏地面测量。',14,MUTED)
    # These three panels are qualitative relations; no map coordinates are assigned.
    cards=[(28,443,'S01','白马寺南坊门 / X02 ↔ O02',[
        '西阳门外大道北侧 → 坊门 → 坊内中路',
        '约7.5米缺口，推为坊门；车辙带宽4.6米。',
        '坊门至中央十字的距离仍未知。',
        '地方发掘窗口未贴入右侧复原图。']),
        (488,445,'S02','司马门内道路 / 独立局部图',[
        '自西向东：宫院东墙—道路—仓区西墙',
        '2023图三段双线分别保留；不补断段。',
        '北魏最宽约40米为汇报值。',
        '两墙净距、同期测线与R4配准仍待证。']),
        (950,462,'S03','永桥与城南御道 / 桥头约束',[
        '宣阳门外 → 洛水浮桥 → 洛南御道',
        '四里保留古里口径，不换算今米。',
        '两岸登陆点未知；图符两端不是桥头。',
        '谷水、阳渠过路处沿用水系定位等级。'])]
    text(root,32,863,'C  发掘地段与过水关系',22,font_weight=600)
    text(root,370,863,'以下三卡只表示关系次序，不按地理比例；点击可回查原专题。',15,MUTED)
    for x,w,rid,title,lines in cards:
        a=route_link(root,rid,title,data_frame='qualitative-relations')
        tag(a,'rect',x=x,y=884,width=w,height=207,rx=4,fill='#edf0e5',stroke='#d1d6c7')
        text(a,x+18,918,title,18,font_weight=600)
        for i,value in enumerate(lines):text(a,x+18,951+i*32,value,14,AMBER if i==2 else MUTED)
    text(root,32,1126,'来源记录交叉：R03 ↔ X01 为同路候选对应；O02 ↔ X02 为同路局部发掘。门内外衔接不自动合成长路。',16)
    text(root,32,1158,'1993《北魏洛阳外廓城和水道的勘查》602—608页及完整附图仍缺：实测／推定线型、探孔与最后测点需原件复核。',15,AMBER)
    text(root,32,1192,'R6.1  ·  各路分期详见证据表，不等于全路在516—528年同期通行。原始图框与全部读点见配套JSON。',14,MUTED)
    return ET.tostring(root,encoding='unicode')+'\n'


def human(value):
    if value is None:return '未定'
    if isinstance(value,bool):return '是' if value else '否'
    if isinstance(value,list):return '；'.join(human(v) for v in value) or '无新增记录'
    if isinstance(value,dict):
        if 'label' in value and 'value' in value:
            amount='—'.join(str(v) for v in value['value']) if isinstance(value['value'],list) else str(value['value'])
            return value['label']+' '+amount+value.get('unit','')+'（'+value.get('scope','')+'；'+value.get('source_ref','')+'）'
        if 'id' in value and 'relation' in value:
            return value['id']+' '+value['relation']+'；等级：'+value.get('level','')+'；'+value.get('limit','')
        return '；'.join(str(k)+'：'+human(v) for k,v in value.items())
    return str(value)


def link(url,label):
    return f'<a href="{escape(url,quote=True)}">{escape(label)}</a>'


def level_of(road):
    return 'source' if road['id'].startswith('R') else 'reconstruction' if road['id'].startswith('O') else 'relation'


def source_lookup(data):
    sources=data.get('sources',{})
    return sources if isinstance(sources,dict) else {s['id']:s for s in sources}


def source_html(data,refs):
    sources=source_lookup(data); items=[]
    for ref in refs:
        s=sources.get(ref,{})
        if isinstance(s,str):s={'title':s}
        title=s.get('title',s.get('name',ref)); url=s.get('url')
        locator=s.get('locator',s.get('pages_figure',s.get('scope','')))
        items.append('<li>'+ (link(url,title) if url else escape(title))+'　'+escape(human(locator))+f' <span class="source-id">{escape(ref)}</span></li>')
    return '<ul>'+''.join(items)+'</ul>'


def card(road,data):
    level=level_of(road)
    label={'source':'06a 原图路迹','reconstruction':'复原图读点／样线','relation':'发掘地段关系'}[level]
    pairs=[('可定位路段','locatable_segment'),('时代与使用限制','period'),('起点与状态','start'),('终点与状态','end'),
           ('所经城门','gates'),('来源重叠与接续','overlap_note'),('已有报告量值','reported_metrics'),('推定连接','inferred_connections')]
    facts=''.join('<div><dt>'+label_+'</dt><dd>'+escape(human(road.get(key)))+'</dd></div>' for label_,key in pairs)
    water=[]
    for w in road.get('water_constraints',[]):
        if isinstance(w,dict):
            wid=w.get('id',w.get('water_id',''))
            name=wid+' '+w.get('relation','')
            content=link(BASE+'luoyang-water-atlas.html#'+wid,name) if wid.startswith('W') else escape(name)
            body='；'.join(human(w[k]) for k in ('level','limit') if k in w)
            water.append('<p>'+content+'　'+escape(body)+'</p>')
        else:water.append('<p>'+escape(str(w))+'</p>')
    return f'''<details class="road" data-road="{road['id']}" data-level="{level}" id="{road['id']}">
<summary><span class="road-id">{road['id']}</span><span class="road-title">{escape(road['name'])}</span><span class="badge {level}">{label}</span></summary>
<div class="road-body"><dl class="facts">{facts}</dl><div class="constraint"><strong>桥渠与待证部分</strong>{''.join(water)}<p>{escape(human(road.get('missing_evidence')))}</p></div>
<div class="sources"><strong>出处、页码与图号</strong>{source_html(data,road.get('source_refs',[]))}</div></div></details>'''


def make_page(data,svg,commit,offline=False):
    prefix=BASE if offline else './'
    inline=svg.replace('<svg ','<svg id="road-map" ',1).replace(BASE+PAGE+'#','#')
    groups=[('内城 · 8 条来源图路迹','R'),('外郭与城南 · 11 条调查来源','O'),('单列发掘 · 2 条局部证据','X')]
    registers=''.join('<section class="register-group"><h3>'+title+'</h3>'+''.join(card(r,data) for r in data['roads'] if r['id'].startswith(code))+'</section>' for title,code in groups)
    supplements=[]
    fallback={
        'S01':('白马寺南坊门','2025年发掘明确西阳门外大道与坊内南北中路的交会。约7.5米缺口由发掘者推为坊门；4.6米为车辙带宽。坊门至中央十字没有已核长度。','prosperity-field-p464.html'),
        'S02':('司马门内道路','2023年公开图保留三段双线。北魏路面最宽约40米为发掘汇报值；两墙净距和同一测线待核，当前接入R4的墙段为零。','prosperity-city-panorama.html#sima-road'),
        'S03':('永桥两岸登陆点','宣阳门外至洛水浮桥四里保留古里口径。钱氏图的桥符两端只供读图；两岸登陆点和同期古岸线仍未知。','prosperity-south-p466.html'),
    }
    for sid,(title,body,path) in fallback.items():
        record=next((s for s in data.get('supplements',[]) if s['id']==sid),{})
        supplements.append(f'<article id="{sid}"><small>{sid} · 关联专题，不增计道路条数</small><h3>{title}</h3><p>{body}</p>'+source_html(data,record.get('source_refs',[]))+link(prefix+path,'查看局部图与原始记录 →')+'</article>')
    downloads=''.join(f'<li><a href="{BASE if offline and p==BUNDLE else "./"}{p}" download>{label}</a></li>' for p,label in DOWNLOADS.items())
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>全城主干道分级定位 · 盛时洛阳</title><meta name="description" content="逐条核对北魏洛阳21项道路来源，用原图路迹、推定连接和未知端点阅读全城交通骨架。"><link rel="stylesheet" href="./road-atlas/atlas.css"><script src="./road-atlas/atlas.js" defer></script></head><body>
<header><div class="wrap">{link(prefix,'盛时洛阳 · 城市复原')}<nav>{link(prefix+'prosperity-city-atlas.html','城市总图')}{link(prefix+'luoyang-water-atlas.html','水系定位')}{link(prefix+'prosperity-city-panorama.html','城市全景')}{link('#downloads','下载图表')}</nav></div></header>
<main class="wrap"><section class="mast"><div><p class="eyebrow">北魏都城研究 / 516—528 年</p><h1>全城主干道<br>分级定位</h1></div><p class="lead">从宫前御道读到外郭诸门。21 条来源逐项对照，路迹保留原图分段，发掘地段单独回接；每条道路都能查到时代、出处、起讫与尚缺的证据。</p></section>
<div class="numbers"><span><strong>8</strong>内城来源图路迹</span><span><strong>11</strong>外围调查来源</span><span><strong>2</strong>单列发掘记录</span><span><strong>3</strong>局部接续专题</span></div>
<figure class="figure"><div class="map-tools" id="map-tools" hidden><label><input id="show-source" type="checkbox" checked><span class="key-line"></span>图面摘读</label><label><input id="show-inferred" type="checkbox" checked><span class="key-line inferred"></span>推定／参照</label><label><input id="show-unknown" type="checkbox" checked><span class="key-point"></span>端点未定</label><button type="button" data-map-panel="inner">看内城</button><button type="button" data-map-panel="outer">看外围</button><label for="zoom">放大 <input id="zoom" type="range" min="100" max="220" step="20" value="100"><output id="zoom-value">100%</output></label>{link('./road-atlas/city-roads.svg','打开矢量原图 ↗')}</div>
<div id="map-scroll" tabindex="0" aria-label="道路总图，可用左右方向键或触摸横移">{inline}</div><figcaption><p><strong>一张总图，两个独立来源图框。</strong> 左图保存06a的原始路迹；右图保存钱氏复原图的读点。实线说明图上有可读笔画，虚线说明连接属示意；空圈标记尚未核定的实测端点。点选编号可展开证据。手机可横向滑动。</p>{link('#register','查看21条逐路证据 ↓')}</figcaption></figure>
<div class="reading"><article><h3>21 条记录 ≠ 21 条独立大道</h3><p>R03与X01构成西明—青阳同名大道的候选对应，O02与X02讨论西阳门外大道及其局部发掘。门内与门外记录先按出处对读，连续同层路段仍需测线证明。</p></article><article><h3>图上能读到什么</h3><p>8条06a原迹、5条外围复原图样线保留其分段。6条东西外道目前只有两端读点，图中虚线用于显示对应关系，沿线转折与最后实测点仍未核。</p></article><article><h3>遇水处沿用水系等级</h3><p>永桥登陆点、鸿池陂出口及谷水／阳渠部分分合点继续留缺。道路与水道相邻不直接证明桥位；本批没有新增516—528年古岸线。</p></article></div>
<section id="register"><div class="section-head"><h2>逐路证据表</h2><p>编号沿用R4依据表 · 点击展开完整记录</p></div><div class="filter" id="filter" hidden><label for="query">查找 <input id="query" type="search" placeholder="编号、城门、桥渠或地名"></label><label for="evidence-filter">来源 <select id="evidence-filter"><option value="">全部</option><option value="source">06a原图路迹</option><option value="reconstruction">外围复原图读点</option><option value="relation">发掘地段关系</option></select></label><button id="clear" type="button">显示全部</button><output id="count" aria-live="polite">21 / 21 条来源记录</output></div><noscript><p>可以直接点开下方每条记录；地图编号和下载无需脚本。</p></noscript><p id="empty" class="empty" hidden>没有符合条件的来源记录。可清空条件后继续查阅。</p>{registers}</section>
<section id="local-studies"><h2>接入三处已有成果</h2><div class="supplements">{''.join(supplements)}</div></section>
<section class="audit" id="source-1993"><h2>1993 年报告：原件续查位置</h2><p>《北魏洛阳外廓城和水道的勘查》，《考古》1993年第7期，602—608页。本次重新核对原刊目录与文献详情，仍未取得这7页原刊及完整《汉魏洛阳城遗址及地形图》。1982年航片和1990年春测绘是附图的编制背景，不能据此断言每条线都已实测。</p><p><strong>下一份最有价值的原件是完整附图，必须连同图例、图边和正文一起取得。</strong> 先分实测与推定线型，再核各条道路的起讫、探孔及测线终止处。图缺失不妨碍其他已取得图源的路段继续使用。2022年运河报告仍按既定决定暂缓。</p><div class="table-wrap"><table><thead><tr><th>对应记录</th><th>具体要补什么</th></tr></thead><tbody><tr><td>O01—O03、O07—O09</td><td>六条东西外道完整线型、墙路交会处测点，推定郭门与实际路土末点的区别。</td></tr><tr><td>O04 承明门西</td><td>西向最后钻孔／测站；短线转点线的位置与图例含义。</td></tr><tr><td>O05、O06 两条北路</td><td>登邙路线最后测点、北郭交点的依据、是否实测到两路合流。</td></tr><tr><td>O10、O11 城南两路</td><td>原图实际覆盖边界、南端测线和层位；原报告如未覆盖，须回查南郊发掘总平面。</td></tr></tbody></table></div><p>{link('https://www.cqvip.com/journal/94762X/1000076712','维普原刊期次页')} · {link('https://github.com/mechgouki/luoyang-city/blob/'+commit+'/research/roads-r6/source-1993-audit.json','本次访问与逐路缺件记录')} · {link('https://github.com/mechgouki/luoyang-city/issues/47','研究记录 #47')}</p></section>
<section class="downloads" id="downloads"><h2>下载与离线阅读</h2><p>CSV含21条主记录的全部证据字段；JSON同时保存原始读点、对应关系与三处补充。SVG可放大或打印，离线包包含本页和所有图表。</p><ul>{downloads}</ul></section>
</main><footer class="footer"><div class="wrap">研究 R6.1 / 网站 {VERSION} · 来源提交 {escape(commit[:12])}　{link('https://github.com/mechgouki/luoyang-city/issues/52','项目交接 #52')}　{link(prefix,'项目首页')}</div></footer></body></html>'''


def build(site=ROOT/'_site'):
    info=load(site/'build-info.json'); release=load(site/'release.json'); dest=site/FOLDER;dest.mkdir(exist_ok=True)
    data=load(DATA/'roads.json')
    data.update(implementation_version=VERSION,source_commit=info['source_commit'],new_historical_coordinates=0,
                accepted_target_bank_geometries=0)
    paths=['research/roads-r6/roads.json','research/roads-r6/source-1993-audit.json',
           'research/prosperity-v4/hydro-roads-anchor-p46.json','research/prosperity-v4/network-462/roads.json',
           'research/prosperity-v4/network-462/outer.json','research/prosperity-v4/gates-465/readings.json',
           'research/prosperity-v4/south-466/readings.json','research/prosperity-r5/sima-road.json']
    data['source_inputs_sha256']={p:sha(ROOT/p) for p in paths}
    data['source_1993_audit']=load(DATA/'source-1993-audit.json')
    outer=load(V4/'network-462/outer.json')
    data['display_connectors']=[dict(source_frame='frame-qian2018',source_pair=c['id'],
        coordinates=[c['inner_station_px'],c['outer_station_px']],kind='inferred_endpoint_pair',
        note='显示两门端读点的配对关系；这条直线不是原图道路描迹，也不是实测道路。') for c in outer['corridors']]
    data['preservation']={'homepage_hero':'panorama-approved-v11','selection_number':'07',
        'source_frames_registered_together':False,'new_historical_coordinates':0,
        'accepted_target_bank_geometries':0,'sima_segments_transferred_to_r4':0}
    atlas=load(site/'city-atlas/atlas.json')
    svg=plate(data,atlas);(dest/'city-roads.svg').write_text(svg)
    dump(dest/'roads.json',data)
    sources=source_lookup(data)
    columns={'id':'id','name':'name','来源组':'source_group','道路图号':'source_code','时代':'period',
             '可定位路段':'locatable_segment','起点':'start','终点':'end','端点状态':'endpoint_status',
             '城门':'gates','桥渠与证据等级':'water_constraints','推定连接':'inferred_connections',
             '对应记录编号':'overlap_ids','对应结论':'overlap_note','报告量值与口径':'reported_metrics',
             '待补原件与测线':'missing_evidence','出处编号':'source_refs','出处页码图号与链接':None,
             '独立图框':None,'几何性质':None}
    with (dest/'roads.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for road in data['roads']:
            row={k:human(road.get(v)) for k,v in columns.items() if v}
            row['出处页码图号与链接']=' | '.join(' · '.join(str(sources[ref].get(k,'')) for k in ['title','locator','url']).strip(' ·') for ref in road.get('source_refs',[]))
            geom=road.get('geometry') or road.get('reconstruction_geometry') or {}
            row['独立图框']=geom.get('frame_id','06a' if road.get('geometry') else '无地理配准')
            row['几何性质']=road['trace_grade']+'；'+geom.get('kind',geom.get('type','仅关系'))
            writer.writerow(row)
    for name in ['atlas.css','atlas.js']:shutil.copyfile(DATA/name,dest/name)
    html=make_page(data,svg,info['source_commit']);(site/PAGE).write_text(html)
    assets=[FOLDER+'/'+n for n in ['city-roads.svg','roads.csv','roads.json','atlas.css','atlas.js']]
    study=dict(version=VERSION,research_version='R6.1',source_commit=info['source_commit'],page=PAGE,
               manifest=MANIFEST,bundle=BUNDLE,download_files=list(DOWNLOADS),
               counts=dict(source_records=21,inner=8,outer=11,excavation=2,supplements=3,
                           original_source_traces=8,later_plan_traces=5,endpoint_pairs=6),
               source_inputs_sha256=data['source_inputs_sha256'],files_sha256={p:sha(site/p) for p in assets})
    dump(site/MANIFEST,study)
    with ZipFile(site/BUNDLE,'w',ZIP_DEFLATED) as z:
        z.writestr('index.html',make_page(data,svg,info['source_commit'],offline=True))
        for p in [*assets,MANIFEST]:z.write(site/p,p)
    info[KEY]=study
    release['extensions']=sorted(set(release['extensions'])|{VERSION})
    release[KEY+'_version']=VERSION;release['current_milestone']='盛时 R6.1 · 全城主干道分级定位'
    dump(site/'release.json',release)
    for p in [*assets,MANIFEST,BUNDLE,PAGE,'release.json']:info['files_sha256'][p]=sha(site/p)
    dump(site/'build-info.json',info)
    return study


if __name__=='__main__':
    print(build()['counts'])
