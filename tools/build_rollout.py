#!/usr/bin/env python3
"""v2.4 graphical rollout. Historical input and display decisions remain separate."""
from pathlib import Path
import copy, json, re, math, hashlib, subprocess, shutil, csv, zipfile, argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw
from pypdf import PdfReader, PdfWriter
import legacy_primitives as g

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'deliverables'; QA=ROOT/'qa'
SCENE=json.loads((ROOT/'data/baseline-scene-v23.json').read_text())
SEM=json.loads((ROOT/'research/semantic-display-audit.json').read_text())
POL=json.loads((ROOT/'research/auxiliary-sheet-policy.json').read_text())
OV=SEM['overrides']; F=SCENE['features']
AUDIT={x['feature_ref']:x for x in SEM['features']}
COL={'bg':'#faf9f5','paper':'#ffffff','ink':'#263f3b','muted':'#707b76',
     'green':'#356f62','gold':'#917452','blue':'#6f99a5','water':'#e0edf0',
     'garden':'#eff3e9','ward':'#f5f0e7','line':'#d5d8cf','red':'#955d51',
     'wall':'#88928b','office':'#5d6d78','market':'#9b7b3d','ritual':'#7f776d'}
g.C.update(COL);g.VERSION='2.4';g.BASE_ROADS=copy.deepcopy(SCENE['base_roads']);g.GATES=copy.deepcopy(SCENE['gates'])
BASE_NAME=g.display_name; OLD_RENDER=g.render_feature; OLD_GLYPH=g.glyph; OLD_WRAP=g.wrap
SIDE=[(i,f) for i,f in enumerate(F) if OV[SEM['features'][i]['feature_ref']]=='sidecar']
E_PAGE={SEM['features'][i]['feature_ref']:'E'+str(j//4+1).zfill(2) for j,(i,f) in enumerate(SIDE)}
RENDER_LOG=[]; VIEWS=[]
SOURCE_REFS={'market_fish':'B12n0077 p0132a12–15','v3_guizheng':'B12n0077 p0161a07–09',
             'house_xiaozhengde':'B12n0077 p0161a07–09','house_xiaobaoyin':'B12n0077 p0161a04–05；p0161a06–07',
             'v3_lingtai_stupa':'B12n0077 p0150a08'}
ROAD_ALIASES={'ic_xiyang_avenue':'road_xiyang','ic_changhe_city_avenue':'road_changhe_west','ic_kaiyang_avenue':'road_kaiyang'}
DISPLAY_NOTES={'central_nailin_group':'局部方向依上述明文；其余相互位置、间距与全局位置未定。'}

def original_ref(eid):
    e=g.D[eid]
    return e.get('source_ref') or e.get('source_locator') or ''

def wrap(s,n):
    lines=OLD_WRAP(s,n)
    for i in range(1,len(lines)):
        while lines[i] and lines[i][0] in '，。；：、！？）〕》':
            lines[i-1]+=lines[i][0];lines[i]=lines[i][1:]
    return [x for x in lines if x]
g.wrap=wrap

def text(x,y,s,size=32,fill='ink',anchor='start',weight=400,halo=False):
    out=[];block='tb'+str(len(g.TEXT_GEOMETRY))
    for i,line in enumerate(str(s).split('\n')):
        cn='wt'+str(len(g.TEXT_GEOMETRY));ww=g.units(line)*size
        left=x-ww/2 if anchor=='middle' else x-ww if anchor=='end' else x
        g.TEXT_GEOMETRY.append({'class':cn,'block_class':block,'bbox':[left,y+i*size*1.35-size,ww,size*1.25]})
        runs=re.split(r'([\x00-\x7f]+)',line)
        body=''.join('<tspan font-family="DejaVu Sans">'+g.esc(t)+'</tspan>' if t.isascii() else g.esc(t) for t in runs if t)
        ha=f' stroke="{COL["bg"]}" stroke-width="6" paint-order="stroke" stroke-linejoin="round"' if halo else ''
        out.append(f'<text class="{cn} {block}" x="{x}" y="{y+i*size*1.35}" font-family="Noto Sans CJK SC,sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{g.col(fill)}"{ha}>{body}</text>')
    return ''.join(out)
g.text=text

def display_name(eid,label=None):
    name=BASE_NAME(eid,label)
    if eid in g.PS and g.state(eid)=='undated' and not any(t in name for t in ['年未','时相','后改']):name+='〔年未定〕'
    if g.state(eid)=='name_layer' and not any(t in name for t in ['记名','后出']):name+='〔记名层〕'
    return name
g.display_name=display_name;g.temporal=lambda *args,**kwargs:''

def kind(eid,fallback='site'):
    e=g.D[eid];typ=e.get('type','');n=e['name']
    special={k:v['glyph'] for k,v in SEM['entity_symbol_overrides'].items()}
    special.update({'ic_taimiao':'ancestral','ic_taishe':'she','v3_mingtang':'ritual_hall'})
    if eid in special:return special[eid]
    if g.state(eid)=='later_temple':return 'house'
    if e['map_id'].startswith('T'):return 'temple'
    if typ in ['storehouse','仓储／赋税场地']:return 'storehouse'
    if typ in ['office','官署','赋税场地','former_office']:return 'office'
    if typ in ['school','学校旧址']:return 'school'
    if typ in ['ritual_site','礼制遗构','礼制建筑','祭坛']:return 'ritual'
    if typ in ['residence','former_residence','宅第','宅第／寺前身','宅第／传称旧址']:return 'house'
    if typ in ['market','市场','巷市','former_market','旧市']:return 'market'
    if typ in ['ward','里坊','former_ward']:return 'ward'
    if typ=='馆舍':return 'lodging'
    if typ in ['artificial_hill','hill','私园人工山','mountain_region']:return 'hill'
    if typ in ['garden','garden_complex','grove']:return 'garden'
    if typ in ['palace_structure','宫内堂','residence_building']:return 'hall'
    return fallback

def tone(k,eid=None):
    if eid and g.D[eid].get('type')=='palace_structure':return 'red'
    return {'temple':'green','tower':'green','palace':'red','office':'office','house':'gold','market':'market',
            'ward':'gold','ritual':'ritual','school':'ritual','lodging':'office','garden':'green','water':'blue',
            'hall':'office','platform':'ritual','stele':'ritual','mill':'blue','hill':'green','storehouse':'office',
            'ancestral':'ritual','she':'ritual','ritual_hall':'ritual'}.get(k,'ink')

def bracket(x,y,w,h,c='line',sw=2):
    q=min(28,w*.08,h*.12)
    return g.path([(x+q,y),(x,y),(x,y+h),(x+q,y+h)],c,sw)

def glyph(x,y,k,fill='green'):
    if k in ['bridge','bridge_ew','gate_ew','well']:return OLD_GLYPH(x,y,k,fill)
    if k=='hall':return g.rect(x-46,y-24,92,48,'paper',fill,2.7)+g.line(x-52,y-30,x+52,y-30,fill,1.8)+g.line(x-52,y+30,x+52,y+30,fill,1.8)
    if k=='tower':return g.rect(x-34,y-34,68,68,'paper',fill,2.7)+g.rect(x-23,y-23,46,46,'none',fill,2)+g.circle(x,y,5,fill,fill,1)
    chars={'temple':'寺','palace':'宫','office':'署','house':'宅','market':'市','ward':'里','ritual':'坛','school':'学','lodging':'馆','garden':'园','platform':'台','stele':'碑','mill':'功','site':'地','hill':'山','storehouse':'仓','ancestral':'庙','she':'社','ritual_hall':'堂'}
    return bracket(x-42,y-34,84,68,fill,2.4)+g.path([(x+22,y-34),(x+42,y-34),(x+42,y+34),(x+22,y+34)],fill,2.4)+text(x,y+14,chars.get(k,'地'),38,fill,'middle',500)
g.glyph=glyph

def node(f):
    x,y=f['x'],f['y'];eid=f['id'];e=g.D[eid]
    k=kind(eid,f.get('glyph','site'));color=tone(k,eid)
    if f.get('glyph') in ['bridge','bridge_ew','gate_ew','well']:k=f['glyph']
    name=display_name(eid,f.get('label'))
    label=(e['map_id']+' ' if f.get('show_id',True) else '')+name
    if f.get('uncertain') and '†' not in label:label+='†'
    nx=x+f.get('dx',0);ny=y+f.get('dy',77);sz=f.get('size',31);an=f.get('anchor','middle')
    a=[glyph(x,y,k,color),g.name_label(nx,ny,label,sz,an,color,eid)]
    if f.get('note'):a.append(text(nx,ny+len(label.split('\n'))*43,f['note'],24,'muted',an,halo=True))
    lw=max(g.units(t) for t in label.split('\n'))*sz;lx=nx-lw/2 if an=='middle' else nx-lw if an=='end' else nx
    left=min(x-50,lx);top=min(y-40,ny-sz);right=max(x+50,lx+lw);bottom=max(y+40,ny+(len(label.split('\n'))-1)*sz*1.35+sz*.25)
    cl='wnode'+str(len(g.NODE_GEOMETRY));g.NODE_GEOMETRY.append({'class':cl,'bbox':[left,top,right-left,bottom-top]})
    return f'<g class="{cl}">'+''.join(a)+'</g>'
g.node=node

def area(f):
    x,y,w,h=[f[k] for k in ['x','y','w','h']];style=f.get('style','range')
    c='green' if style=='garden' else 'market' if f.get('key')=='dashi_extent' else 'gold'
    fill='garden' if style=='garden' else 'ward';a=[]
    if str(f.get('coordinate_frame','world')).startswith('panel:'):
        a.append(bracket(x,y,w,h,c,2.2))
    else:
        a.append(g.rect(x,y,w,h,fill))
        q=min(45,w*.08,h*.15)
        for xx,yy,dx,dy in [(x,y,1,1),(x+w,y,-1,1),(x,y+h,1,-1),(x+w,y+h,-1,-1)]:
            a.append(g.path([(xx+dx*q,yy),(xx,yy),(xx,yy+dy*q)],c,1.7))
    label=f.get('label','');ts=min(36,max(23,(w-44)/max(1,g.units(label))))
    a.append(text(x+22,y+47,label,ts,c,weight=500))
    if f.get('note'):a.append(text(x+22,y+88,f['note'],23,'muted'))
    return ''.join(a)
g.area=area

def group(f):
    x,y,w,h=[f[k] for k in ['x','y','w','h']];cols=f.get('cols',1);title=f.get('title','')
    ids=f.get('ids',[]);labels=f.get('labels',[]);cw=(w-48)/cols;sz=28
    while True:
        names=[g.wrap(g.D[eid]['map_id']+' '+display_name(eid,labels[i] if i<len(labels) else None),(cw-32)/sz) for i,eid in enumerate(ids)]
        heights=[max(len(t) for t in names[i:i+cols])*sz*1.35+13 for i in range(0,len(ids),cols)]
        nl=g.wrap(f.get('note',''),(w-44)/23)
        used=88+sum(heights)+len(nl)*31+20
        if used<=h or sz<=20:break
        sz-=1
    ts=min(33,(w-44)/max(1,g.units(title)))
    a=[bracket(x,y,w,h,'line',2),text(x+22,y+43,title,ts,'green',weight=500)];yy=y+91
    for pos in range(0,len(ids),cols):
        for j,eid in enumerate(ids[pos:pos+cols]):
            i=pos+j;xx=x+24+j*cw;k=kind(eid);color=tone(k,eid)
            cl='wentry'+str(len(g.NODE_GEOMETRY));ww=max(g.units(t) for t in names[i])*sz
            g.NODE_GEOMETRY.append({'class':cl,'bbox':[xx,yy-sz,ww,(len(names[i])-1)*sz*1.35+sz*1.25]})
            a.append(f'<g class="{cl}">'+text(xx,yy,'\n'.join(names[i]),sz,color)+'</g>')
        yy+=heights[pos//cols]
    if nl:a.append(text(x+22,max(yy+6,y+h-23-(len(nl)-1)*31),'\n'.join(nl),23,'muted'))
    return ''.join(a)
g.group=group

def pool(f):
    a=[f'<ellipse cx="{f["cx"]}" cy="{f["cy"]}" rx="{f["rx"]}" ry="{f["ry"]}" fill="{COL["water"]}" opacity="0.75"/>']
    if f.get('label'):a.append(text(f['cx'],f['cy']+f.get('label_dy',12),f['label'],f.get('size',29),'blue','middle',halo=True))
    return ''.join(a)
g.pool=pool

def compound(f):
    eid=f['id'];x=f['x']+f['w']/2;y=f['y']+f['h']/2
    note={'ic_yongning':'院内关系见 D01','v3_jingming':'三池、塔与水功设施见 D07'}.get(eid,'群级标志；院内落位未定')
    return node({'id':eid,'x':x,'y':y,'glyph':kind(eid),'label':f.get('label'),'note':note,'size':33})
g.compound=compound

def road(points,width=50):return g.path(points,'#d4c8ae',width+7)+g.path(points,'paper',width)

def base_scene():
    a=[]
    for eid in ['luoshui','mangshan','palace_scope']:g.track({'kind':'context_outline','id':eid})
    a += [g.rect(4400,1800,3400,5000,'#f7f6f1','wall',6,'28 17'),text(6100,1745,'城内 · 轮廓与门距示意',42,'muted','middle')]
    a += [g.rect(5250,2050,2300,1900,'#f2eae5','red',2.5,'24 18'),text(6400,2010,'宫城与宫苑',52,'red','middle',500)]
    for r in g.BASE_ROADS:g.track({'kind':'road',**r});a.append(road(r['points'],r['width']))
    for alias,target in ROAD_ALIASES.items():g.track({'kind':'road_alias','id':alias,'alias_of':target,'coordinate_frame':'world'})
    a += [text(5530,3605,'千秋门内道〔局部试绘〕',25,'office',halo=True),text(6165,7250,'御道',32,'office'),text(6165,10480,'御道',32,'office')]
    pts=[(400,8970),(2300,9010),(4200,8940),(6100,9000),(8000,8970),(9800,9050),(11700,8960)]
    a += [g.path(pts,'water',130),g.path(pts,'blue',2,'none','20 11'),text(10500,8970,'洛水 · 河形示意',40,'blue')]
    a += [g.path([(500,650),(2300,570),(4100,680),(6000,550),(8000,660)],'#c6cfbc',32),text(2800,540,'芒山 / 北邙 · 区域参照',42,'green')]
    return ''.join(a)
g.base_scene=base_scene

def bridge_scene():
    g.track({'kind':'bridge','id':'bridge_yong','x':6100,'y':9000})
    # Display symbol only: the centre stays fixed; the south cap meets the road.
    a=[g.rect(6060,8825,80,350,'paper','office',3)]
    for y in range(8845,9170,28):a.append(g.line(6060,y,6140,y,'office',1.7))
    a += [text(6250,9010,'P167 永桥〔浮桥〕',35,'office',halo=True),text(6250,9060,'两岸华表另记；图符不计桥长',24,'muted',halo=True)]
    g.track({'kind':'annotation','id':'v3_yong_huabiao','coordinate_frame':'side_note:bridge'})
    return ''.join(a)
g.bridge_scene=bridge_scene

def render_feature(f):
    if f.get('id')=='altar_yuanqiu':
        g.track({'kind':'direction_reference','id':'altar_yuanqiu','coordinate_frame':'world_reference'})
        x,y=f['x'],f['y']
        return g.path([(x,y-75),(x,y)],'muted',3,arrow=True)+text(x+80,y-20,'圜丘方向 · 南向参照',30,'ritual')+text(x+80,y+26,'不定距离、坛形与占地',23,'muted')
    if f['kind']=='road':
        g.track(f);s=road(f.get('points',[]),f.get('width',42))
        if f.get('label'):s+=text(f['label_x'],f['label_y'],f['label'],25,'office',halo=True)
        return s
    return OLD_RENDER(f)
g.render_feature=render_feature

def legend(x,y,size=28):
    entries=[('寺 寺院','green'),('宫 宫苑','red'),('署 官署','office'),('宅 宅第','gold'),('市 市场','market'),('坛 / 学 礼制学校','ritual')]
    return ''.join(text(x+i*size*9.6,y,s,size,c) for i,(s,c) in enumerate(entries))
g.legend=legend

def refs_for(r):
    x,y,w,h=r['bbox'];refs=[]
    page_policy=POL['sheets'].get(r.get('number',''),{})
    explicit=page_policy.get('appendix_e_reference',{}).get('feature_keys',[])
    refs.extend(E_PAGE[k] for k in explicit if k in E_PAGE)
    for idx,f in SIDE:
        a=AUDIT[SEM['features'][idx]['feature_ref']]
        b=a.get('original_display_box')
        if not b and f['kind']=='relation':
            pts=f['points'];b=[min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts)-min(p[0] for p in pts),max(p[1] for p in pts)-min(p[1] for p in pts)]
        if b and x<=b[0]+b[2]/2<=x+w and y<=b[1]+b[3]/2<=y+h:refs.append(E_PAGE[a['feature_ref']])
    return sorted(set(refs))

def master_svg(scene,index=False):
    W,H=12400,12030
    a=[g.svg_open(W,H,(900,873.15)),text(210,160,'历史研究项目 / 洛阳伽蓝记 · 全城统一图式 v2.4',48,'green',weight=500),
       text(210,305,'北魏洛阳 · 盛时平面总图' if not index else '北魏洛阳 · 分区索引',112,'ink',weight=500),
       text(210,397,'516年至528年河阴事件前的文献合成 · 同一母图 · 分区等比裁切',45,'muted'),legend(210,493,38),
       text(6900,493,'〔年未定〕建寺年代待核   † 校读或定位候选',34,'muted'),
       text(210,566,'开放名录只示所属；浅色块只示阅读范围。未定位关系转见附录 E；地名编号对应完整证据登记。',34,'muted'),
       '<g transform="translate(200 640)">',scene]
    if index:
        for r in SCENE['regions']:
            x,y,w,h=r['bbox'];a += [g.rect(x,y,w,h,'none','red',7,'30 15'),g.rect(x+8,y+8,170,95,'paper','red',2),text(x+93,y+73,r['number'],56,'red','middle',500)]
    a += ['</g>',g.north(11750,210,1.4),g.line(210,11830,12190,11830,'line',2),
          text(210,11910,'文献相对平面；院形、道路宽度与间距仍为示意。绘图坐标不换算历史里尺或现代米制。',37,'muted'),text(12190,11910,'总图 / v2.4',37,'muted','end'),'</svg>']
    return ''.join(a)

def crop_page(scene,r,code,series):
    wide=r['bbox'][2]/r['bbox'][3]>2.7
    W,H=(4200,2450) if wide else (3600,2700)
    vx,vy,vw,vh=r['bbox'];mx,my,mw,mh=(80,330,4040,1220) if wide else (80,330,2640,2200)
    s=min(mw/vw,mh/vh);cx=mx+(mw-vw*s)/2;cy=my+(mh-vh*s)/2;tx=cx-vx*s;ty=cy-vy*s
    policy=POL['sheets'].get(code,{})
    title=policy.get('title',r['title'])
    if code=='D05':title='景明—台学 · 寺学与礼制旧迹'
    a=[g.svg_open(W,H,(490,285.83) if wide else (420,315)),g.crop_text_style(r['bbox']),
       text(80,82,'历史研究项目 / 北魏洛阳 · 全城统一图式 v2.4',28,'green',weight=500),
       text(80,176,code+'  '+title,min(65,(W-200)/max(1,g.units(code+'  '+title))),'ink',weight=500),
       text(80,249,series+' · 同一母图等比裁切 · 盛时合成 516年至528年河阴事件前',29,'muted'),g.line(80,285,W-80,285),
       f'<defs><clipPath id="crop"><rect x="{cx}" y="{cy}" width="{vw*s}" height="{vh*s}"/></clipPath></defs>',
       g.rect(cx,cy,vw*s,vh*s,'paper','line',1.5),f'<g clip-path="url(#crop)"><g transform="translate({tx} {ty}) scale({s})">',scene,'</g></g>']
    sections=policy.get('sidebar') or [{'title':'本区关系' if j==0 else '文献限制','text':t,'tone':'muted'} for j,t in enumerate(r.get('summary',[]))]
    if wide:
        for j,sec in enumerate(sections[:4]):
            xx=80+j*1010;yy=1640
            a += [g.line(xx,yy,xx+960,yy,'line',2),text(xx,yy+57,sec['title'],32,'green',weight=500),text(xx,yy+111,'\n'.join(g.wrap(sec['text'],31)),27,'ink')]
        a += [legend(80,2160,27),text(80,2220,'〔年未定〕表示建寺时间待核；†表示校读或位置候选。相关图外说明：'+('、'.join(refs_for(r)) or '见附录 A–E')+'。',27,'muted')]
    else:
        sx=2820;yy=365
        a.append(text(sx,yy,'读图与校核',35,'green',weight=500));yy+=75
        for sec in sections[:4]:
            lines=g.wrap(sec['text'],23)
            a += [text(sx,yy,sec['title'],29,'office',weight=500),text(sx,yy+52,'\n'.join(lines),27,'ink')]
            yy+=52+len(lines)*37+45
        refs=refs_for(r)
        if refs:
            a += [g.line(sx,yy,sx+690,yy),text(sx,yy+56,'图外说明：'+'、'.join(refs),28,'green'),text(sx,yy+105,'仅保留关系与来源，不赋予院址。',25,'muted')];yy+=160
        yy=max(yy,1560)
        a += [text(sx,yy,'图式约定',30,'green',weight=500),text(sx,yy+60,'类别用色；年代用文字。\n〔年未定〕：建寺时间待核。\n†：校读或定位仍有候选。\n开放括线：所属或无序名录。\n浅色范围不表示已知坊墙、池岸。',25,'muted')]
        a.append(g.minimap([r],0,sx+70,2010,540,495))
    a += [g.north(W-135,85,.8),g.line(80,H-115,W-80,H-115),text(80,H-59,'据《洛阳伽蓝记》周校释、范校注及既有校核。来源与显示去向见随图登记。',25,'muted'),text(W-80,H-59,code+' / v2.4 · 文献相对平面',25,'muted','end'),'</svg>']
    VIEWS.append({'code':code,'bbox':r['bbox'],'mode':'shared_world_crop','scale':s,'translation':[tx,ty],'sidecar_refs':refs_for(r)})
    return ''.join(a)

def pilot_template(stem,code):
    s=(ROOT/'templates'/stem).read_text()
    s=s.replace('首批应用样板','全城统一图式').replace('研究样板','统一图式')
    s=re.sub(r'0[1-6] / 06 ',code+' / v2.4 ',s)
    if code=='S06':s=s.replace('首版街区深化 /','街区关系专页 /')
    VIEWS.append({'code':code,'mode':'graphic_legend' if code=='L01' else 'thematic_geography_plus_separate_relationship_inset','template':stem,'geometry_source':None if code=='L01' else 'published v2.3 anchors as verified in v2.4-pilot-1'})
    return s

def sidecar_pages():
    pages=[]
    for j in range(0,len(SIDE),4):
        code='E'+str(j//4+1).zfill(2);a=[g.svg_open(3600,2700,(420,315)),text(80,83,'历史研究项目 / 北魏洛阳 · 全城统一图式 v2.4',28,'green',weight=500),text(80,179,code+'  图外关系与未定位置',65,'ink',weight=500),text(80,252,'这些条目已从地理画面移出；本页排版不产生方向、距离或相邻关系。',30,'muted'),g.line(80,285,3520,285)]
        for k,(idx,f) in enumerate(SIDE[j:j+4]):
            rec=SEM['features'][idx];x=85+(k%2)*1760;y=360+(k//2)*1090;cw=1660
            title=f.get('title') or f.get('label') or rec['label'];ids=rec['entity_ids']
            if f.get('key')=='yinian_west_yongming':title='宜年—永明 · 东西关系'
            a += [g.line(x,y,x+cw,y,'line',2),text(x,y+65,title,min(39,1540/max(1,g.units(title))),'green',weight=500)]
            yy=y+136
            for ii,eid in enumerate(ids):
                label=next((f.get('labels',[])[ii] for _ in [0] if ii<len(f.get('labels',[]))),None)
                nm=g.D[eid]['map_id']+' '+display_name(eid,label)
                a.append(text(x,yy,nm,29,tone(kind(eid),eid)));yy+=48
                g.track({'kind':'nonspatial_annotation','id':eid,'coordinate_frame':'appendix:'+code})
            note=DISPLAY_NOTES.get(rec['feature_ref'],f.get('note',''))
            if f['kind']=='relation':note='宜年里在永明寺西；永明在大觉寺东。只保留方向关系，不据此确定道路侧别或间距。'
            yy+=20
            if note:
                nl=g.wrap(note,52);a.append(text(x,yy,'\n'.join(nl),28,'ink'));yy+=len(nl)*38+32
            reason=g.wrap(rec['reason'],54);a += [text(x,yy,'表示限制',27,'office',weight=500),text(x,yy+48,'\n'.join(reason),27,'muted')];yy+=48+len(reason)*37+30
            refs=[]
            for eid in ids:
                ref=SOURCE_REFS.get(eid,original_ref(eid))
                if isinstance(ref,list):ref='；'.join(ref)
                if ref and ref not in refs:refs.append(ref)
            if refs:a.append(text(x,y+980,'\n'.join(g.wrap('出处：'+'；'.join(refs),75)),20,'muted'))
        a += [g.line(80,2585,3520,2585),text(80,2640,'原始记录与方位约束完整保留；本轮只撤去没有证据支持的页面落点含义。',25,'muted'),text(3520,2640,code+' / v2.4 · 非地理附图',25,'muted','end'),'</svg>']
        pages.append((code,''.join(a)))
    return pages

def export_job(spec):
    svg,png,pdf,width=spec
    for dst,opts in [(png,[f'--export-width={width}']),(pdf,[])]:
        rr=subprocess.run(['inkscape',str(svg),f'--export-filename={dst}',*opts],capture_output=True,text=True)
        if rr.returncode:raise RuntimeError(rr.stderr)
    im=Image.open(png).convert('RGB');im.thumbnail((1600,1450));im.save(QA/'previews'/(svg.stem+'.png'))
    return svg.stem

def build(draft=False):
    for d in [OUT,OUT/'editable',OUT/'regions',OUT/'details',OUT/'streets',OUT/'appendices',OUT/'data',QA/'pdf',QA/'previews']:d.mkdir(parents=True,exist_ok=True)
    order={'area':0,'water':1,'pool':1,'road':2,'relation':3,'compound':4,'group':5,'node':6,'text':7}
    active=[]
    for i,f in enumerate(F):
        ref=SEM['features'][i]['feature_ref'];action=OV[ref]
        RENDER_LOG.append({'feature_index':i,'feature_ref':ref,'mode':action,'destination':E_PAGE.get(ref,'world'),'original_geometry_preserved_in_input':True})
        if action!='sidecar':active.append(copy.deepcopy(f))
    scene=base_scene()+''.join(render_feature(f) for f in sorted(active,key=lambda f:order.get(f['kind'],9)))+g.gates_scene()+bridge_scene()
    g.WORLD_TEXT_GEOMETRY.extend(copy.deepcopy(g.TEXT_GEOMETRY));g.WORLD_NODE_GEOMETRY.extend(copy.deepcopy(g.NODE_GEOMETRY))
    (OUT/'editable/world-scene.svg').write_text(g.svg_open(12000,11000)+scene+'</svg>')
    jobs=[];atlas=[];sheets=[]
    def add(code,stem,svgtext,folder,width=4200,in_atlas=True):
        svg=OUT/'editable'/(stem+'.svg');svg.write_text(svgtext)
        png=OUT/folder/(stem+'.png');pdf=QA/'pdf'/(stem+'.pdf')
        jobs.append((svg,png,pdf,width))
        if in_atlas:atlas.append(pdf)
        sheets.append({'code':code,'stem':stem,'png':str(png.relative_to(OUT)),'svg':str(svg.relative_to(OUT)),'atlas_page':len(atlas) if in_atlas else None})
    add('M00','luoyang-v24-master-plan',master_svg(scene),'',7440)
    add('L01','v24-L01-graphic-key',pilot_template('L01_graphic_key.svg','L01'),'appendices',3600)
    add('I00','v24-region-index',master_svg(scene,True),'appendices',3600)
    for r in SCENE['regions']:add(r['number'],'v24-'+r['number']+'-'+r['slug'],crop_page(scene,r,r['number'],'区域平面'),'regions',4400)
    for r in SCENE['detail_regions']:
        code=r['number']
        add(code,'v24-'+code+'-'+r['slug'],pilot_template('D01_yongning_pilot.svg','D01') if code=='D01' else crop_page(scene,r,code,'局部详图'),'details',4200)
    add('D07','v24-D07-jingming',pilot_template('D07_jingming_pilot.svg','D07'),'details',4200)
    for r in SCENE['street_sheets']:add(r['number'],'v24-'+r['number']+'-'+r['slug'],crop_page(scene,r,r['number'],'街区关系核校'),'streets',4600)
    add('S06','v24-S06-luosouth',pilot_template('S06_luosouth_pilot.svg','S06'),'streets',4200)
    a=g.appendix_svg().replace('分组名录不参与主图距离；保留证据，等待后续定址。','分组名录不参与主图距离；新增的图外关系另见 E01–E06。').replace('地图未落点，不表示史料中没有记载；完整','据《洛阳伽蓝记》周校释、范校注；完整').replace('条记录均保存在证据登记内。','条记录与逐条出处见随图登记。')
    add('A','v24-A-unlocated',a,'appendices',4200)
    for p in SCENE['standalone_panels']:add(p['number'],'v24-'+p['number']+'-'+p['slug'],g.panel_svg(copy.deepcopy(p),p['number']),'appendices',4200)
    for code,svg in sidecar_pages():add(code,'v24-'+code+'-annotations',svg,'appendices',4200)
    selected=jobs if not draft else [j for j in jobs if any(q in j[0].stem for q in ['master-plan','R03-','R07-','R11-','S04-','E01-','E06-'])]
    with ThreadPoolExecutor(max_workers=3) as ex:
        for done in ex.map(export_job,selected):print('Rendered '+done,flush=True)
    if draft:return
    masterpdf=OUT/'luoyang-v24-master-plan.pdf';shutil.copy2(atlas[0],masterpdf)
    shutil.copy2(OUT/'editable/luoyang-v24-master-plan.svg',OUT/'luoyang-v24-master-plan.svg')
    writer=PdfWriter()
    for pdf in atlas:writer.append(str(pdf))
    writer.add_metadata({'/Title':'北魏洛阳 · 全城统一图式图册 v2.4','/Author':'历史研究项目','/Subject':'文献相对平面、分区图、局部关系与图外附记'})
    writer.write(OUT/'luoyang-v24-regional-atlas.pdf')
    records=[]
    for eid,e in g.D.items():
        uses=g.FEATURE_IDS.get(eid,[])
        records.append({'id':eid,'map_id':e['map_id'],'source_name':e['name'],'display_name':display_name(eid),
          'modes':sorted(set(u['kind'] for u in uses)) or ['register_only'],
          'frames':sorted(set(u.get('coordinate_frame','world') for u in uses)),
          'temporal_state':g.PS.get(eid,{}).get('prosperity_state'),
          'original_source_ref':original_ref(eid),'display_source_ref':SOURCE_REFS.get(eid,original_ref(eid)),'source_url':e.get('source_url',''),'coordinates':None})
    release={'version':'2.4','scope':'complete graphic rollout; historical geometry and disputes remain provisional',
      'world_scene_sha256':hashlib.sha256(scene.encode()).hexdigest(),'world_input_feature_count':len(F),'active_world_features':len(active),
      'sidecar_features':len(SIDE),'sidecar_groups':sum(f['kind']=='group' for _,f in SIDE),'source_records':len(g.D),
      'regional_maps':len(SCENE['regions']),'detail_maps':7,'street_maps':6,'appendix_maps':4+math.ceil(len(SIDE)/4),'atlas_pages':len(atlas),
      'sheets':sheets,'views':VIEWS,'render_policy':RENDER_LOG,
      'road_alias_registration':ROAD_ALIASES,'display_note_overrides':DISPLAY_NOTES,
      'bridge_display_join':{'anchor_unchanged':[6100,9000],'bridge_symbol_vertical_extent':[8825,9175],'road_start_y':9200,'road_cap_radius':25,'historical_length_inferred':False}}
    (OUT/'data/release-v24.json').write_text(json.dumps(release,ensure_ascii=False,indent=2))
    (OUT/'data/drawing-register-v24.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    for f in (ROOT/'data').glob('*.json'):shutil.copy2(f,OUT/'data'/f.name)
    for name in ['semantic-display-audit.json','auxiliary-sheet-policy.json','integrity-baseline.json']:
        shutil.copy2(ROOT/'research'/name,OUT/'data'/name)
    print(json.dumps({k:v for k,v in release.items() if k not in ['sheets','views','render_policy']},ensure_ascii=False,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--draft',action='store_true');args=ap.parse_args();build(args.draft)
