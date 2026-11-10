#!/usr/bin/env python3
"""One vector scene, regional viewports, and a full documentary plan.
World x/y are illustrative drawing coordinates, never geographic coordinates.
"""
from pathlib import Path
import json, math, html, csv, subprocess, shutil, hashlib, zipfile, sys, re
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageOps, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter, Transformation

ROOT=Path(__file__).resolve().parent
INPUT=ROOT if (ROOT/'scene-central.json').exists() else ROOT/'data'
SOURCE=ROOT/'data'
OUT=ROOT/'deliverables'
VERSION='2.4'
FILE_PREFIX='luoyang-v24-'
MAPS=OUT/'regions'; DETAILS=OUT/'details'; STREETS=OUT/'streets'; EDIT=OUT/'editable'; DATA=OUT/'data'; QA=ROOT/'qa'
for p in [OUT,MAPS,DETAILS,STREETS,EDIT,DATA,QA]:p.mkdir(parents=True,exist_ok=True)
D={e['id']:e for e in json.loads((SOURCE/'places.json').read_text())['entities']}
PS=json.loads((SOURCE/'prosperity_overrides.json').read_text())
DISPLAY_CORRECTIONS={
 'ic_diaotai_palace':{'note':'钓台殿所在台／山有异解；周补台并释九华台上，范存上／山异文。本轮从蓬莱山关联中移出，不定点。','source_url':'https://deerpark.app/cbeta/B0077/1','parallel_url':'https://tripitaka2.zensoul.org/B/B0078/1'},
 'v2_changmancang':{'note':'范祥雍在龙华条明确主张南租场即上文明悬东常满仓租场；正文未明言同址。图位采用范注候选，身份合并保留解释层次。','source_url':'https://tripitaka2.zensoul.org/B/B0078/2','parallel_url':'https://deerpark.app/cbeta/B0077/2'},
 'v3_lingtai_stupa':{'note':'原登记行码a06应核为a08；造塔年月未见明文，附记于灵台，不绘成528年前已竣工塔。','verified_source_ref':'B12n0077 p0150a08','source_url':'https://deerpark.app/cbeta/B0077/3'}
}
C={'bg':'#f8f5ec','paper':'#fffdf8','ink':'#263f40','muted':'#74817b','green':'#286c60','gold':'#a77a36','blue':'#4f8a9b','water':'#d9eaf0','garden':'#e6eddb','ward':'#f1eadc','line':'#c3c6b8','red':'#a45b42','wall':'#6b7468'}
FONT='Noto Sans CJK SC,Noto Sans CJK JP,sans-serif'
TEXT_GEOMETRY=[]; WORLD_TEXT_GEOMETRY=[]; NODE_GEOMETRY=[]; WORLD_NODE_GEOMETRY=[]
DEFS='''<defs>
<marker id="relarr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M1 1L9 5L1 9" fill="none" stroke="#8c958b" stroke-width="1.5"/></marker>
<pattern id="hatch" width="38" height="38" patternUnits="userSpaceOnUse"><path d="M0 38L38 0" stroke="#b1b79d" stroke-width="1" opacity=".35"/></pattern>
<pattern id="reserved" width="28" height="28" patternUnits="userSpaceOnUse"><path d="M0 28L28 0" stroke="#b79a63" stroke-width="1" opacity=".32"/></pattern>
</defs>'''
def esc(s):return html.escape(str(s))
def col(c):return C.get(c,c)
def units(s):return sum(.55 if ord(ch)<128 else 1 for ch in str(s))
def wrap(s,n):
    out=[];line='';width=0
    for ch in str(s):
        if ch=='\n':out.append(line);line='';width=0;continue
        q=.55 if ord(ch)<128 else 1
        if line and width+q>n:out.append(line);line='';width=0
        line+=ch;width+=q
    if line:out.append(line)
    return out
def rect(x,y,w,h,fill='none',stroke=None,sw=2,dash=None,r=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{col(fill)}"'+(f' stroke="{col(stroke)}" stroke-width="{sw}"' if stroke else '')+(f' stroke-dasharray="{dash}"' if dash else '')+'/>'
def text(x,y,s,size=32,fill='ink',anchor='start',weight=400,halo=False):
    lines=str(s).split('\n'); a=[];block='tb'+str(len(TEXT_GEOMETRY))
    for i,line in enumerate(lines):
        haloattr=f' stroke="{C["bg"]}" stroke-width="7" paint-order="stroke" stroke-linejoin="round"' if halo else ''
        cn='wt'+str(len(TEXT_GEOMETRY));ww=units(line)*size;left=x-ww/2 if anchor=='middle' else x-ww if anchor=='end' else x
        TEXT_GEOMETRY.append({'class':cn,'block_class':block,'bbox':[left,y+i*size*1.35-size,ww,size*1.25]})
        a.append(f'<text class="{cn} {block}" x="{x}" y="{y+i*size*1.35}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{col(fill)}"{haloattr}>{esc(line)}</text>')
    return ''.join(a)
def line(x1,y1,x2,y2,stroke='line',sw=2,dash=None):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col(stroke)}" stroke-width="{sw}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>'
def path(points,stroke='line',sw=2,fill='none',dash=None,arrow=False):
    d=' '.join(('M' if i==0 else 'L')+f'{p[0]} {p[1]}' for i,p in enumerate(points))
    return f'<path d="{d}" stroke="{col(stroke)}" stroke-width="{sw}" fill="{col(fill)}" stroke-linecap="round" stroke-linejoin="round"'+(f' stroke-dasharray="{dash}"' if dash else '')+(' marker-end="url(#relarr)"' if arrow else '')+'/>'
def circle(x,y,r,fill='none',stroke='green',sw=2):return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col(fill)}" stroke="{col(stroke)}" stroke-width="{sw}"/>'
def state(eid):return PS.get(eid,{}).get('prosperity_state','undated')
def display_name(eid,label=None):
    p=PS.get(eid,{})
    if label:return label
    if p.get('prosperity_state') in ['later_temple','later_name','name_layer']:
        n=p.get('prior_name') or p.get('main_scene_name') or D[eid]['name']
    else:n=label or D[eid]['name']
    return n
def temporal(x,y,eid,sz=10):
    s=state(eid)
    if s=='attested_by_528':return circle(x,y,sz,'green','green',2)
    if s in ['later_temple','later_name','name_layer']:return rect(x-sz,y-sz,sz*2,sz*2,'paper','gold',3)
    return circle(x,y,sz,'paper','green',3)
LABELS=[]; FEATURE_IDS=defaultdict(list)
def track(f):
    f.setdefault('coordinate_frame','world')
    for eid in ([f['id']] if f.get('id') else [])+f.get('ids',[])+f.get('related_ids',[]):
        if eid not in D: raise ValueError('Unknown source ID: '+eid)
        FEATURE_IDS[eid].append(f)
def name_label(x,y,label,size=32,anchor='middle',fill='ink',key='',halo=True):
    for i,t in enumerate(str(label).split('\n')):
        ww=units(t)*size
        left=x-ww/2 if anchor=='middle' else x-ww if anchor=='end' else x
        LABELS.append({'key':key,'text':t,'bbox':[left,y+i*size*1.35-size,ww,size*1.25]})
    return text(x,y,label,size,fill,anchor,500,halo)
def glyph(x,y,k,fill='green'):
    c=col(fill);a=[]
    if k in ['temple','tower']:
        a+=[rect(x-33,y-33,66,66,'paper',c,3),rect(x-20,y-20,40,40,'none',c,2),rect(x-7,y-7,14,14,c)]
        a+=[line(x-40,y,x-33,y,c,3),line(x+33,y,x+40,y,c,3),line(x,y-40,x,y-33,c,3),line(x,y+33,x,y+40,c,3)]
    elif k in ['office','hall','house']:
        a+=[rect(x-46,y-28,92,56,'paper',c,3),line(x-46,y,x+46,y,c,1.5)]
        for off in [-23,0,23]:a.append(line(x+off,y-28,x+off,y+28,c,1.2))
    elif k=='well':a=[circle(x,y,22,'paper',c,3),circle(x,y,11,'none',c,2)]
    elif k=='platform':
        a=[rect(x-42,y-34,84,68,'#e7e4d7',c,2.4),rect(x-29,y-22,58,44,'paper',c,2)]
        for yy in [-30,30]:a.append(line(x-34,y+yy,x+34,y+yy,c,1))
    elif k=='stele':a=[rect(x-27,y+16,54,16,'paper',c,2),rect(x-12,y-31,24,47,'paper',c,2.4)]
    elif k=='mill':
        a=[circle(x,y,29,'paper',c,2.5),circle(x,y,9,'none',c,2)]
        for ang in range(0,360,45):
            r=math.radians(ang);a.append(line(x+11*math.cos(r),y+11*math.sin(r),x+34*math.cos(r),y+34*math.sin(r),c,2))
    elif k=='garden':
        for dx,dy in [(-20,10),(10,-12),(28,17)]:a.append(circle(x+dx,y+dy,17,'garden','green',1.5))
    elif k=='bridge':
        a=[rect(x-23,y-50,46,100,'paper','ink',3)]
        for off in range(-40,50,15):a.append(line(x-23,y+off,x+23,y+off,'ink',1.4))
    elif k=='bridge_ew':
        a=[rect(x-60,y-24,120,48,'paper','ink',3)]
        for off in range(-48,60,16):a.append(line(x+off,y-24,x+off,y+24,'ink',1.4))
    elif k=='gate_ew':
        a=[rect(x-29,y-46,58,92,'paper'),line(x-44,y-44,x+44,y-44,'ink',4),line(x-44,y+44,x+44,y+44,'ink',4)]
    else:a=[circle(x,y,15,'paper',c,3),line(x-24,y,x+24,y,c,1.3),line(x,y-24,x,y+24,c,1.3)]
    return ''.join(a)
def node(f):
    x,y=f['x'],f['y'];eid=f['id'];e=D[eid];s=state(eid)
    color='gold' if s in ['later_temple','later_name','name_layer'] else ('green' if e['map_id'].startswith('T') else 'ink')
    k=f.get('glyph','site')
    if s=='later_temple':k='house'
    a=[glyph(x,y,k,color)]
    if e['map_id'].startswith('T'):a.append(temporal(x-50,y-38,eid,9))
    label=display_name(eid,f.get('label'))
    if f.get('show_id',True):label=e['map_id']+' '+label
    if f.get('uncertain') and '†' not in label:label+='†'
    a.append(name_label(x+f.get('dx',0),y+f.get('dy',77),label,f.get('size',31),f.get('anchor','middle'),color,eid))
    if f.get('note'):
        ny=y+f.get('dy',77)+len(str(label).split('\n'))*43
        a.append(text(x+f.get('dx',0),ny,f['note'],24,'muted',f.get('anchor','middle'),halo=True))
    # Suppress orphaned or amputated point symbols at crop edges, as one label unit.
    nx=x+f.get('dx',0);ny=y+f.get('dy',77);sz=f.get('size',31);an=f.get('anchor','middle')
    lw=max(units(t) for t in str(label).split('\n'))*sz;lx=nx-lw/2 if an=='middle' else nx-lw if an=='end' else nx
    left=min(x-60,lx);top=min(y-55,ny-sz);right=max(x+60,lx+lw);bottom=max(y+50,ny+(len(str(label).split('\n'))-1)*sz*1.35+sz*.25)
    cl='wnode'+str(len(NODE_GEOMETRY));NODE_GEOMETRY.append({'class':cl,'bbox':[left,top,right-left,bottom-top]})
    return f'<g class="{cl}">'+''.join(a)+'</g>'
def area(f):
    x,y,w,h=[f[k] for k in ['x','y','w','h']];style=f.get('style','range')
    fill={'garden':'garden','ward':'ward','palace':'#e9eadf','reserve':'url(#reserved)','range':'url(#hatch)'}.get(style,'ward')
    a=[rect(x,y,w,h,fill,'line',2,'18 13',22),text(x+22,y+50,f.get('label',''),38,'green' if style=='garden' else 'muted',weight=600)]
    if f.get('note'):a.append(text(x+22,y+90,f['note'],24,'muted'))
    return ''.join(a)
def group(f):
    x,y,w,h=[f[k] for k in ['x','y','w','h']];cols=f.get('cols',1)
    title=f.get('title','');ts=min(35,(w-44)/max(1,units(title)))
    a=[rect(x,y,w,h,'#f5f2e8','line',1.8,'10 10',12),text(x+22,y+45,title,ts,'green',weight=600)]
    ids=f.get('ids',[]);labels=f.get('labels',[]);cw=(w-48)/cols;sz=29
    while True:
        names=[]
        for i,eid in enumerate(ids):
            nm=D[eid]['map_id']+' '+display_name(eid,labels[i] if i<len(labels) else None)
            names.append(wrap(nm,(cw-42)/sz))
        heights=[max(len(t) for t in names[i:i+cols])*sz*1.35+16 for i in range(0,len(ids),cols)]
        note_lines=wrap(f.get('note',''),(w-44)/24)
        used=90+sum(heights)+len(note_lines)*32+25
        if used<=h or sz<=21:break
        sz-=1
    yy=y+95
    for pos in range(0,len(ids),cols):
        for j,eid in enumerate(ids[pos:pos+cols]):
            i=pos+j;xx=x+24+j*cw;e=D[eid]
            cl='wentry'+str(len(NODE_GEOMETRY))
            entry_width=30+max(units(t) for t in names[i])*sz
            entry_height=(len(names[i])-1)*sz*1.35+sz*1.25
            NODE_GEOMETRY.append({'class':cl,'bbox':[xx,yy-sz,entry_width,entry_height]})
            a.append(f'<g class="{cl}">')
            if e['map_id'].startswith('T'):a.append(temporal(xx+9,yy-9,eid,8))
            else:a.append(circle(xx+9,yy-9,4,'muted','muted'))
            a.append(text(xx+30,yy,'\n'.join(names[i]),sz,'gold' if state(eid) in ['later_temple','later_name','name_layer'] else 'ink'))
            a.append('</g>')
        yy+=heights[pos//cols]
    if note_lines:
        base=max(yy+10,y+h-25-(len(note_lines)-1)*32)
        a.append(text(x+22,base,'\n'.join(note_lines),24,'muted'))
    return ''.join(a)
def pool(f):
    a=[f'<ellipse cx="{f["cx"]}" cy="{f["cy"]}" rx="{f["rx"]}" ry="{f["ry"]}" fill="{C["water"]}" stroke="{C["blue"]}" stroke-width="2.5" stroke-dasharray="12 8"/>']
    if f.get('label'):a.append(text(f['cx'],f['cy']+f.get('label_dy',12),f['label'],f.get('size',29),'blue','middle',halo=True))
    return ''.join(a)
def compound(f):
    x,y,w,h=[f[k] for k in ['x','y','w','h']];eid=f['id'];layout=f.get('layout','house')
    title=D[eid]['map_id']+' '+display_name(eid,f.get('label'));tone='gold' if state(eid) in ['later_temple','later_name','name_layer'] else 'green'
    # Keep the temporal badge and heading together when a regional crop cuts the title.
    heading=temporal(x+w/2-units(title)*19-25,y-43,eid,10)+text(x+w/2,y-30,title,38,tone,'middle',700)
    cl='wcompoundheading'+str(len(NODE_GEOMETRY));tw=units(title)*38
    NODE_GEOMETRY.append({'class':cl,'bbox':[x+w/2-tw/2-35,y-68,tw+35,48]})
    a=[rect(x,y,w,h,'#f4efe2',tone,2.6,'12 9'),f'<g class="{cl}">'+heading+'</g>']
    if layout=='yongning':
        # All footprints are illustrative. Text establishes hall north of tower,
        # four gates and gate hierarchy; it does not establish bay or column grids.
        tx=x+w/2;ty=y+h*.57
        a.append(line(tx,y+65,tx,y+h-65,'#a8b8a6',1.5,'8 8'))
        a.append(text(tx+16,y+h*.36,'暂同轴',18,'muted'))
        a+=[rect(x+w*.19,y+h*.135,w*.62,h*.18,'none','green',1.6,'7 5'),rect(x+w*.23,y+h*.16,w*.54,h*.13,'#d3dfd7','green',2.3),text(tx,y+h*.245,'佛殿 · 在塔北',23,'green','middle')]
        tw=w*.29
        a+=[rect(tx-tw*.59,ty-tw*.59,tw*1.18,tw*1.18,'none','green',1.7,'7 5'),rect(tx-tw/2,ty-tw/2,tw,tw,'#d3dfd7','green',2.4),rect(tx-tw*.35,ty-tw*.35,tw*.7,tw*.7,'paper','green',1.5),text(tx,ty-6,'木塔',24,'green','middle'),text(tx,ty+29,'九层',24,'green','middle')]
        # Double wall outline has open gaps at four gates. Wall form is schematic.
        for off in [0,11]:
            a+=[line(x+off,y+off,tx-55,y+off,'green',2,'9 6'),line(tx+55,y+off,x+w-off,y+off,'green',2,'9 6'),line(x+off,y+h-off,tx-100,y+h-off,'green',2,'9 6'),line(tx+100,y+h-off,x+w-off,y+h-off,'green',2,'9 6')]
            for xx in [x+off,x+w-off]:
                a+=[line(xx,y+off,xx,y+h*.43,'green',2,'9 6'),line(xx,y+h*.60,xx,y+h-off,'green',2,'9 6')]
        # North is an unroofed gateway. No roof or gatehouse rectangle is added.
        a.append(rect(tx-56,y-9,112,31,'bg'))
        a+=[rect(tx-54,y-4,11,15,'green'),rect(tx+43,y-4,11,15,'green'),line(tx-43,y+7,tx-16,y+29,'green',2),line(tx+43,y+7,tx+16,y+29,'green',2),text(tx,y+64,'北门一道 · 无屋',21,'green','middle')]
        # Three south passages are a candidate plan interpretation of 三道 / 三阁道.
        a.append(rect(tx-100,y+h-32,200,64,'paper','green',2.5))
        for dx in [-61,0,61]:
            a+=[rect(tx+dx-16,y+h-34,32,68,'#f4efe2'),line(tx+dx-18,y+h-32,tx+dx-18,y+h+32,'green',1.6),line(tx+dx+18,y+h-32,tx+dx+18,y+h+32,'green',1.6)]
        a+=[text(tx,y+h-54,'南门三重 · 三道†',21,'green','middle')]
        for xx in [x,x+w]:
            a.append(rect(xx-24,y+h*.43,48,h*.17,'paper','green',2.3))
            a.append(rect(xx-26,y+h*.485,52,h*.06,'#f4efe2'))
        a+=[text(x+60,y+h*.47,'西门\n两重',20,'green'),text(x+w-60,y+h*.47,'东门\n两重',20,'green','end')]
        for xx in [x+w*.07,x+w*.79]:
            for yy in [y+h*.325,y+h*.72]:
                a.append(rect(xx,yy,w*.14,h*.09,'#ede9df','line',1.5,'6 5'))
        a.append(text(tx,y+h*.87,'房舍千余间 · 分布未定',20,'muted','middle'))
        a.append(text(tx,y+h+70,'院界、轴线、占地与三道平面均为试绘',21,'muted','middle'))
    elif layout=='jingming':
        for xx,yy,ww,hh in [(.16,.13,.68,.12),(.12,.35,.18,.17),(.70,.35,.18,.17),(.24,.83,.52,.08)]:a.append(rect(x+w*xx,y+h*yy,w*ww,h*hh,'#dae4db','green',2,'8 5'))
        a.append(text(x+w/2,y+h*.21,'复殿重房 · 形制未定',24,'green','middle'))
        a.append(rect(x+w*.41,y+h*.37,w*.18,h*.18,'url(#reserved)','gold',2,'8 6'))
        a.append(text(x+w/2,y+h*.60,'七层塔：始造，未证竣工',23,'gold','middle'))
        # The three pool symbols encode textual count, not excavated outlines or order.
        for xx,yy in [(.22,.68),(.50,.72),(.78,.68)]:
            a.append(f'<ellipse cx="{x+w*xx}" cy="{y+h*yy}" rx="{w*.085}" ry="{h*.039}" fill="{C["water"]}" stroke="{C["blue"]}" stroke-width="2" stroke-dasharray="7 5"/>')
        a.append(text(x+w/2,y+h*.80,'三池 · 仅示数量，落位未定',22,'blue','middle'))
        a.append(glyph(x+w*.84,y+h*.92,'mill','blue'))
        a.append(text(x+w*.78,y+h*.955,'水功碾磨〔设施附记〕',19,'blue','end'))
        a.append(text(x+w/2,y+h+40,'建筑、三池与碾磨均为类型示意',23,'muted','middle'))
    else:
        a+=[rect(x+w*.2,y+h*.24,w*.6,h*.2,'#eee4d0','gold',2,'9 7'),text(x+w/2,y+h*.68,'宅第范围示意',28,'gold','middle')]
    return ''.join(a)
def render_feature(f):
    track(f);k=f['kind']
    if k=='node':return node(f)
    if k=='area':return area(f)
    if k=='group':return group(f)
    if k=='pool':return pool(f)
    if k=='compound':return compound(f)
    if k in ['water','road','relation']:
        pts=f.get('points',[])
        if not pts:return ''
        if k=='water':out=path(pts,'water',f.get('width',65))+path(pts,'blue',3,'none','15 10')
        elif k=='road':out=path(pts,'#e6d7b3',f.get('width',42))+path(pts,'#b39a68',2,'none','16 10')
        else:out=path(pts,'#90988b',2,'none','9 8' if f.get('uncertain') else None,True)
        if f.get('label'):
            p=pts[len(pts)//2];out+=text(f.get('label_x',p[0]+15),f.get('label_y',p[1]-18),f['label'],25,'blue' if k=='water' else 'muted',halo=True)
        return out
    if k=='text':return text(f['x'],f['y'],f['text'],f.get('size',32),f.get('color','muted'),f.get('anchor','start'),f.get('weight',400),True)
    raise ValueError('Unknown feature kind '+k)

BASE_ROADS=[
 {'key':'palace_xuanyang','ids':['ic_palace_avenue','road_xuanyang'],'points':[[6100,3950],[6100,8920]],'width':50},
 {'key':'luosouth','ids':['road_siyi'],'points':[[6100,9200],[6100,10600]],'width':50},
 {'key':'changhe_west','ids':['road_changhe_west'],'points':[[1400,3550],[4400,3550]],'width':50},
 {'key':'xiyang','ids':['road_xiyang'],'points':[[1300,4750],[5050,4750]],'width':50},
 {'key':'ximing','ids':['road_ximing'],'points':[[3300,6100],[4400,6100]],'width':50},
 {'key':'jianchun','ids':['ic_jianchun_avenue','road_jianchun'],'points':[[7100,3550],[11600,3550]],'width':50},
 {'key':'dongyang','ids':['ic_dongyang_avenue','road_dongyang'],'points':[[7000,4750],[11600,4750]],'width':50},
 {'key':'qingyang','ids':['ic_qingyang_avenue','road_qingyang'],'points':[[7000,6100],[11600,6100]],'width':50},
 {'key':'daxia','ids':['road_daxia'],'points':[[5000,700],[5000,1800]],'width':50},
 {'key':'guangmo','ids':['road_guangmo'],'points':[[7200,700],[7200,1800]],'width':50},
 {'key':'jinyang','ids':['road_jinyang'],'points':[[4750,6800],[4750,8150]],'width':50},
 {'key':'kaiyang','ids':['road_kaiyang'],'points':[[7500,6250],[7500,8450]],'width':50},
 {'key':'qianqiu_inside','ids':['ic_qianqiu_road'],'points':[[5260,3550],[6400,3550]],'width':42}
]
def base_scene():
    a=[]
    for eid in ['ic_palace_avenue','ic_xiyang_avenue','ic_changhe_city_avenue','ic_dongyang_avenue','ic_qingyang_avenue','ic_kaiyang_avenue','ic_jianchun_avenue','road_jianchun','road_dongyang','road_qingyang','road_xuanyang','road_kaiyang','road_siyi','road_jinyang','road_ximing','road_xiyang','road_changhe_west','road_daxia','road_guangmo']:
        track({'kind':'road','id':eid})
    for eid in ['luoshui','mangshan','palace_scope']:track({'kind':'context_outline','id':eid})
    # The enclosing rectangle encodes city-gate order, not excavated wall geometry.
    a.append(rect(4400,1800,3400,5000,'#f0eddf','wall',9,'28 17'))
    a.append(rect(4430,1830,3340,4940,'none','#b1b5a6',2,'25 20'))
    a.append(text(6100,1745,'城内 · 轮廓与门距示意',42,'muted','middle'))
    a.append(rect(5250,2050,2300,1900,'#e8edde','green',4,'20 15'))
    a.append(text(6400,2010,'宫城与宫苑',54,'green','middle',700))
    # Every trunk is owned once here. Gaps remain where continuity lacks evidence.
    for r in BASE_ROADS:
        track({'kind':'road',**r});a.append(path(r['points'],'#eadbb7',r['width']));a.append(path(r['points'],'#b2a17d',2,'none','15 11'))
    a.append(text(5530,3605,'千秋门内道〔局部试绘〕',25,'gold',halo=True))
    a.append(text(6165,7250,'御道',32,'gold'))
    a.append(text(6165,10480,'御道',32,'gold'))
    a.append(path([(400,8970),(2300,9010),(4200,8940),(6100,9000),(8000,8970),(9800,9050),(11700,8960)],'water',130))
    a.append(path([(400,8970),(2300,9010),(4200,8940),(6100,9000),(8000,8970),(9800,9050),(11700,8960)],'blue',4,'none','20 11'))
    a.append(text(10500,8970,'洛水 · 河形示意',43,'blue'))
    a.append(path([(500,650),(2300,570),(4100,680),(6000,550),(8000,660)],'#b6c1a8',40))
    a.append(text(2800,540,'芒山 / 北邙 · 区域参照',44,'green'))
    return ''.join(a)
def bridge_scene():
    track({'kind':'bridge','id':'bridge_yong','x':6100,'y':9000,'related_ids':['v3_yong_huabiao']})
    a=[rect(6060,8850,80,300,'paper','ink',3)]
    for y in range(8870,9150,28):a.append(line(6060,y,6140,y,'ink',2))
    a+=[circle(6200,8845,14,'paper','ink',3),circle(6200,9155,14,'paper','ink',3),text(6250,9010,'P167 永桥〔浮桥〕',36,'ink',halo=True),text(6250,9060,'南北岸华表示意',27,'muted',halo=True)]
    return ''.join(a)
GATES=[('gate_chengming',4400,2350,'w','承明门'),('gate_changhe_west',4400,3550,'w','阊阖〔城西〕'),('gate_xiyang',4400,4750,'w','西阳门'),('gate_ximing',4400,6100,'w','西明门'),
 ('gate_jianchun',7800,3550,'e','建春门'),('gate_dongyang',7800,4750,'e','东阳门'),('gate_qingyang',7800,6100,'e','青 / 清阳门†'),
 ('gate_daxia',5000,1800,'n','大夏门'),('gate_guangmo',7200,1800,'n','广莫门'),('gate_jinyang',4750,6800,'s','津阳门†'),('gate_xuanyang',6100,6800,'s','宣阳门'),('gate_pingchang',6800,6800,'s','平昌门'),('gate_kaiyang',7500,6800,'s','开阳门'),('ic_changhe_palace',6100,3950,'s','阊阖〔宫前〕')]
def gates_scene():
    a=[]
    for eid,x,y,side,label in GATES:
        track({'kind':'gate','id':eid,'x':x,'y':y})
        if side in ['w','e']:
            a+=[rect(x-32,y-56,64,112,'bg'),line(x-45,y-56,x+45,y-56,'ink',5),line(x-45,y+56,x+45,y+56,'ink',5)]
            a.append(name_label(x+(85 if side=='e' else -85),y-64,label,36,'start' if side=='e' else 'end','ink',eid))
        else:
            a+=[rect(x-62,y-30,124,60,'bg'),line(x-62,y-45,x-62,y+45,'ink',5),line(x+62,y-45,x+62,y+45,'ink',5)]
            a.append(name_label(x,y+100 if side=='s' else y-85,label,36,'middle','ink',eid))
    return ''.join(a)
def north(x,y,size=1):
    return line(x,y+90*size,x,y,'ink',4*size)+path([(x-12*size,y+22*size),(x,y),(x+12*size,y+22*size)],'ink',4*size)+text(x,y-24*size,'北',32*size,'ink','middle',700)
def svg_open(w,h,physical=None):
    wh=f'width="{w}" height="{h}"' if not physical else f'width="{physical[0]}mm" height="{physical[1]}mm"'
    return f'<svg xmlns="http://www.w3.org/2000/svg" {wh} viewBox="0 0 {w} {h}">{DEFS}'+rect(0,0,w,h,'bg')
def legend(x,y,size=30):
    a=[];entries=[('●','528年前已有时证','green'),('○','建寺年代未明','green'),('□','宅第 / 后出记名','gold'),('†','校补或定位候选','gold')]
    for i,(s,t,c) in enumerate(entries):a.append(text(x+i*size*12,y,s+' '+t,size,c))
    return ''.join(a)
def master_svg(scene,regions,index=False):
    a=[svg_open(12400,11800,(900,856.45)),text(210,160,'历史研究项目 / 洛阳伽蓝记 · 分区平面细化 v'+VERSION,48,'green',weight=700),text(210,305,'北魏洛阳 · 盛时平面总图' if not index else '北魏洛阳 · 分区索引',115,'ink',weight=700),text(210,395,'516年至528年河阴之变前的文献合成  |  北向一致 · 同一母图 · 区域等比裁切',45,'muted'),legend(210,483,38),'<g transform="translate(200 560)">',scene]
    if index:
        for i,r in enumerate(regions,1):
            x,y,w,h=r['bbox'];a.append(rect(x,y,w,h,'none','red',8,'30 15'));a.append(rect(x+8,y+8,170,95,'paper','red',3,r=12));a.append(text(x+93,y+73,f'R{i:02d}',57,'red','middle',700))
    a+=['</g>',text(3200,483,'虚线：显示范围  |  细箭头：文献关系  |  建筑符号：类型示意',38,'muted'),north(11750,210,1.4),line(210,11630,12190,11630,'line',2),text(210,11710,'相对方位据文献；城界、院界、道路形状与间距为示意。图内像素仅用于拼接，无历史里尺或现代坐标。',37,'muted'),text(12190,11710,'总图 / v'+VERSION,37,'muted','end'),'</svg>']
    return ''.join(a)
def minimap(regions,selected,x,y,w=540,h=495):
    scale=min(w/12000,h/11000);a=[rect(x,y,w,h,'paper','line',2)]
    a.append(rect(x+4400*scale,y+1800*scale,3400*scale,5000*scale,'#eee8da','wall',2))
    a.append(line(x,y+9000*scale,x+w,y+9000*scale,'blue',3))
    for i,r in enumerate(regions):
        xx,yy,ww,hh=r['bbox']
        if i==selected:a.append(rect(x+xx*scale,y+yy*scale,ww*scale,hh*scale,'#d5e4d8','green',3))
    a.append(text(x+20,y+h+42,'分区位置 · 同一母图裁切',25,'muted'))
    return ''.join(a)
def region_svg(scene,r,i,regions):
    if r['bbox'][2]/r['bbox'][3]>2.7:return wide_region_svg(scene,r,i,regions)
    code=r.get('sheet_code',f'R{i+1:02d}');detail=r.get('sheet_kind')=='detail'
    W,H=3600,2700; vx,vy,vw,vh=r['bbox']; mx,my,mw,mh=80,320,2780,2210
    s=min(mw/vw,mh/vh); tx=mx+(mw-vw*s)/2-vx*s;ty=my+(mh-vh*s)/2-vy*s
    cx=mx+(mw-vw*s)/2;cy=my+(mh-vh*s)/2
    subtitle='局部放大 · 直接取自同一母图 · 位置与方向保持一致' if detail else '盛时合成：516年至528年河阴之变前  ·  地名编号与总图一致'
    a=[svg_open(W,H,(420,315)),crop_text_style(r['bbox']),text(80,85,'历史研究项目 / 北魏洛阳 · 文献相对平面 v'+VERSION,27,'green',weight=700),text(80,178,code+'  '+r['title'],66,'ink',weight=700),text(80,250,subtitle,30,'muted'),line(80,283,3520,283,'line',2),f'<defs><clipPath id="crop"><rect x="{cx}" y="{cy}" width="{vw*s}" height="{vh*s}"/></clipPath></defs>',rect(cx,cy,vw*s,vh*s,'#fbf8ef','line',2),f'<g clip-path="url(#crop)"><g transform="translate({tx} {ty}) scale({s})">',scene,'</g></g>']
    sx=2940;a+=[text(sx,368,'本区如何阅读',38,'green',weight=700)]
    y=430
    for stext in r.get('summary',[])[:4]:
        a.append(text(sx,y,'\n'.join(wrap(stext,18)),29,'ink'));y+=len(wrap(stext,18))*43+38
    y=max(y+30,1000)
    a.append(text(sx,y,'时层符号',34,'green',weight=700));y+=65
    for t,c in [('● 528年前已有时证','green'),('○ 年代未明的文献候选','green'),('□ 宅第或后出记名层','gold'),('† 校补 / 位置有争议','gold')]:a.append(text(sx,y,t,27,c));y+=55
    y+=30
    a.append(text(sx,y,'\n'.join(wrap('虚线范围、院界、门距和路形均为试绘；建筑符号只表达类型及文献关系。',18)),26,'muted'))
    a.append(minimap([r] if detail else regions,0 if detail else i,sx,1810,560,514));a.append(north(3470,85,.8))
    a+= [line(80,2585,3520,2585,'line',2),text(80,2640,'据《洛阳伽蓝记》周校释、范校注；改订依据与校核结果见随图研究说明。',25,'muted'),text(3520,2640,code+(' · 局部放大' if detail else f' / {len(regions):02d}')+' · 相对平面，无比例尺',25,'muted','end'),'</svg>']
    return ''.join(a)
def wide_region_svg(scene,r,i,regions):
    code=r.get('sheet_code',f'R{i+1:02d}');detail=r.get('sheet_kind')=='detail'
    W,H=3600,1800;vx,vy,vw,vh=r['bbox'];mx,my,mw,mh=80,320,3440,920
    s=min(mw/vw,mh/vh);cx=mx+(mw-vw*s)/2;cy=my+(mh-vh*s)/2;tx=cx-vx*s;ty=cy-vy*s
    a=[svg_open(W,H,(420,210)),crop_text_style(r['bbox']),text(80,85,'历史研究项目 / 北魏洛阳 · 文献相对平面 v'+VERSION,27,'green',weight=700),text(80,178,code+'  '+r['title'],66,'ink',weight=700),text(80,250,'盛时合成：516年至528年河阴之变前 · 同一母图等比裁切',30,'muted'),line(80,283,3520,283,'line',2),f'<defs><clipPath id="crop"><rect x="{cx}" y="{cy}" width="{vw*s}" height="{vh*s}"/></clipPath></defs>',rect(cx,cy,vw*s,vh*s,'#fbf8ef','line',2),f'<g clip-path="url(#crop)"><g transform="translate({tx} {ty}) scale({s})">',scene,'</g></g>']
    for j,st in enumerate(r.get('summary',[])[:3]):
        a.append(text(80+j*1145,1330,'\n'.join(wrap(st,34)),29,'ink'))
    a+=[legend(80,1540,27),text(80,1620,'虚线范围、门距与路形为示意；相邻裁切的对象来自同一母图。',27,'muted'),north(3470,85,.8),line(80,1695,3520,1695,'line',2),text(80,1750,'据《洛阳伽蓝记》周校释、范校注及既有版本审计。完整出处见证据登记。',25,'muted'),text(3520,1750,code+(' · 局部放大' if detail else f' / {len(regions):02d}')+' · 相对平面，无比例尺',25,'muted','end'),'</svg>']
    return ''.join(a)
def crop_text_style(bbox):
    x,y,w,h=bbox;hide=set()
    for t in WORLD_TEXT_GEOMETRY+WORLD_NODE_GEOMETRY:
        xx,yy,ww,hh=t['bbox']
        if xx<x+3 or yy<y+3 or xx+ww>x+w-3 or yy+hh>y+h-3:hide.add('.'+t.get('block_class',t['class']))
    return '<style>'+','.join(sorted(hide))+'{display:none}</style>' if hide else ''
def appendix_svg():
    # These names remain visible without being assigned invented street addresses.
    groups=[('仅知城内 / 城西', ['xref_banruo','xref_chanlin','xref_lingjue','v3_chongxu','a_wangnan']),('无可用街址', ['n_chongli','v3_chengguang','w_mingdiling_qihuan']),('北邙山上',['n_fengwang','n_qixianwu']),('京东石关',['e_yuanlingjun','e_liuchangqiu']),('嵩高及山上关系',['r_xianju','r_qichan','r_songyang','r_daochang','r_zhongding','r_shengdao']),('京南关口',['r_shiku','r_lingyan']),('京西瀍涧',['r_baima_chanjian','r_zhaole'])]
    a=[svg_open(3600,2700,(420,315)),text(80,85,'历史研究项目 / 北魏洛阳 · 文献相对平面',27,'green',weight=700),text(80,180,'附图 A · 郭外与未定位记录',66,'ink',weight=700),text(80,255,'分组名录不参与主图距离；新增的图外关系另见 E01–E06。',31,'muted'),line(80,290,3520,290,'line',2)]
    for i,(title,ids) in enumerate(groups):
        x=90+(i%2)*1730;y=350+(i//2)*525
        f={'kind':'group','key':'index_'+str(i),'x':x,'y':y,'w':1650,'h':460,'title':title,'ids':ids,'cols':2,'note':'组内列名无先后空间含义；不是实测范围。','located':False,'coordinate_frame':'appendix:A'}
        track(f);a.append(group(f))
    a.append(text(1880,2110,'同名与时代问题保留',38,'green',weight=700));a.append(text(1880,2185,'西阳条白马与瀍涧条白马：身份关系未定。\n齐献武王寺：保留记名层，不认定盛时已建。\n崇虚：城西所指与园址解释仍待定。\n晋阳三级寺与洛水神宅不作洛阳地图点。',30,'muted'))
    a+=[line(80,2585,3520,2585,'line',2),text(80,2640,'据《洛阳伽蓝记》周校释、范校注；完整339条记录与逐条出处见随图登记。',26,'muted'),text(3520,2640,'附图 A / v'+VERSION,26,'muted','end'),'</svg>']
    return ''.join(a)
def panel_svg(p,code):
    a=[svg_open(3600,2700,(420,315)),text(80,85,'历史研究项目 / 北魏洛阳 · 文献关系附图 v'+VERSION,27,'green',weight=700),text(80,178,'附图 '+code+' · '+p['title'],62,'ink',weight=700),text(80,250,'独立关系图 · 不参与总图距离或拼接 · 箭头表示文献关系',30,'gold'),line(80,283,3520,283,'line',2),rect(80,320,3440,2110,'#fbf8ef','line',2),'<g transform="translate(150 350) scale(1.1)">']
    for f in p['features']:
        f['coordinate_frame']='panel:'+p['slug'];a.append(render_feature(f))
    a.append('</g>')
    summary='  /  '.join(p.get('summary',[]))
    a.append(text(80,2495,'\n'.join(wrap(summary,116)),24,'muted'))
    a+=[line(80,2585,3520,2585,'line',2),text(80,2640,'只表达有据关系；原文量距保留原单位，不折算为当前图面距离。',26,'muted'),text(3520,2640,'附图 '+code+' / v'+VERSION,26,'muted','end'),'</svg>']
    return ''.join(a)
def wide_street_svg(scene,r,code):
    W,H=4200,2550;vx,vy,vw,vh=r['bbox'];mx,my,mw,mh=90,350,4020,1550
    scale=min(mw/vw,mh/vh);cx=mx+(mw-vw*scale)/2;cy=my+(mh-vh*scale)/2
    tx=cx-vx*scale;ty=cy-vy*scale
    a=[svg_open(W,H,(490,297.5)),crop_text_style(r['bbox']),text(90,92,'历史研究项目 / 北魏洛阳 · 第二批街区平面深化 v'+VERSION,31,'green',weight=700),text(90,202,code+'  '+r['title'],72,'ink',weight=700),text(90,280,'统一母图等比裁切 · 盛时合成516年至528年河阴之变前 · 门序、归属与通行关系',32,'muted'),line(90,315,4110,315,'line',2),f'<defs><clipPath id="crop"><rect x="{cx}" y="{cy}" width="{vw*scale}" height="{vh*scale}"/></clipPath></defs>',rect(cx,cy,vw*scale,vh*scale,'#fbf8ef','line',2),f'<g clip-path="url(#crop)"><g transform="translate({tx} {ty}) scale({scale})">',scene,'</g></g>']
    for i,section in enumerate(r['panels'][:4]):
        sx=90+i*1010;yy=1960;cw=975;lines=wrap(section['text'],29);tone=section.get('tone','green');hh=110+len(lines)*42
        a += [rect(sx,yy,cw,hh,'paper','line',2,r=14),rect(sx,yy,9,hh,tone),text(sx+28,yy+52,section['title'],35,tone,weight=700),text(sx+28,yy+108,'\n'.join(lines),30,'ink')]
    a += [north(4050,110,.9),line(90,2375,4110,2375,'line',2),text(90,2430,'依据：'+r['source_note'],27,'muted'),text(90,2485,'正文关系、校释解释与本图假设分开阅读；门距、城界、路形与内部尺度均未实测。',27,'muted'),text(4110,2485,code+' / 同一母图，无历史比例尺',27,'muted','end'),'</svg>']
    return ''.join(a)
def street_svg(scene,r,code):
    if r.get('layout')=='wide':return wide_street_svg(scene,r,code)
    W,H=4200,3000;vx,vy,vw,vh=r['bbox'];mx,my,mw,mh=90,350,3000,2380
    scale=min(mw/vw,mh/vh);cx=mx+(mw-vw*scale)/2;cy=my+(mh-vh*scale)/2
    tx=cx-vx*scale;ty=cy-vy*scale
    a=[svg_open(W,H,(490,350)),crop_text_style(r['bbox']),text(90,92,'历史研究项目 / 北魏洛阳 · 第'+('二' if r.get('batch',1)==2 else '一')+'批街区平面深化 v'+VERSION,31,'green',weight=700),text(90,202,code+'  '+r['title'],72,'ink',weight=700),text(90,280,'统一母图裁切 · 盛时合成 516年至528年河阴之变前 · 方向与相接关系校核',32,'muted'),line(90,315,4110,315,'line',2),f'<defs><clipPath id="crop"><rect x="{cx}" y="{cy}" width="{vw*scale}" height="{vh*scale}"/></clipPath></defs>',rect(cx,cy,vw*scale,vh*scale,'#fbf8ef','line',2),f'<g clip-path="url(#crop)"><g transform="translate({tx} {ty}) scale({scale})">',scene,'</g></g>']
    sx=3190;cw=890;yy=395
    for section in r['panels']:
        lines=wrap(section['text'],25);hh=100+len(lines)*44
        tone=section.get('tone','green')
        a+=[rect(sx,yy,cw,hh,'paper','line',2,r=14),rect(sx,yy,9,hh,tone),text(sx+30,yy+53,section['title'],35,tone,weight=700),text(sx+30,yy+109,'\n'.join(lines),31,'ink')]
        yy+=hh+35
    a+=[text(sx,yy+40,'证据层次',35,'green',weight=700),text(sx,yy+103,'正文关系 / 校释解释 / 本图假设',29,'ink'),text(sx,yy+157,'\n'.join(wrap('桥、门和建筑符号表达通行与类型；院界、坊界、占地和间距均非实测。',26)),28,'muted')]
    a.append(minimap([r],0,sx+175,2200,500,458))
    a+=[north(4050,110,.9),line(90,2830,4110,2830,'line',2),text(90,2890,'依据：'+r['source_note'],28,'muted'),text(90,2940,'本批约束与修订见《v2.3 第二批街区深化说明》；前批校核另保留。',27,'muted'),text(4110,2940,code+' / 同一母图，无历史比例尺',27,'muted','end'),'</svg>']
    return ''.join(a)
def make_contact(pngs):
    thumbs=[]
    for p in pngs:
        im=Image.open(p).convert('RGB');im.thumbnail((800,620));card=Image.new('RGB',(840,680),'#f1eee5');card.paste(im,((840-im.width)//2,12));ImageDraw.Draw(card).text((20,646),p.stem,fill='#263f40');thumbs.append(card)
    sheet=Image.new('RGB',(840*3,680*math.ceil(len(thumbs)/3)),'white')
    for i,t in enumerate(thumbs):sheet.paste(t,((i%3)*840,(i//3)*680))
    sheet.save(QA/'contact-sheet.jpg',quality=90)
def export_one(spec):
    svg,png,pdf,width=spec
    env=None
    for dest,opts in [(png,[f'--export-width={width}']), (pdf,[])]:
        if dest:
            r=subprocess.run(['inkscape',str(svg),f'--export-filename={dest}',*opts],capture_output=True,text=True)
            if r.returncode:raise RuntimeError(str(svg)+' '+r.stderr)
    return str(svg)