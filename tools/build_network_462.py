"""Build the P4.6.2 road network in 06a PDF page coordinates (Python stdlib)."""
import json
import math
from itertools import combinations
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
P1 = Path('research/prosperity-v1/geographic-evidence.json')
P452 = Path('research/prosperity-v4/road-functions-p452.json')
OUT = ROOT / 'research/prosperity-v4/network-462'
NEAR = 2.0  # Paper points; a display threshold.
SEAM = .01
EPS = 1e-8
H = [f'Lh-{i}' for i in range(1,5)]
V = [f'Lz-{i}' for i in range(1,5)]
WALLS = ['geo-inner-wall-aboveground','geo-inner-wall-underground','geo-palace-walls']


def sub(a,b):
    return a[0]-b[0], a[1]-b[1]


def dot(a,b):
    return a[0]*b[0]+a[1]*b[1]


def cross(a,b):
    return a[0]*b[1]-a[1]*b[0]


def lerp(a,b,t):
    return a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t


def project(p,a,b):
    ab=sub(b,a)
    t=max(0., min(1.,dot(sub(p,a),ab)/dot(ab,ab))) if dot(ab,ab) else 0.
    return lerp(a,b,t)


def hits(a,b,c,d):
    ab, cd, ac = sub(b,a), sub(d,c), sub(c,a)
    det = cross(ab,cd)
    if abs(det)>EPS:
        u,v = cross(ac,cd)/det, cross(ac,ab)/det
        return [lerp(a,b,u)] if -EPS<=u<=1+EPS and -EPS<=v<=1+EPS else []
    pts=[]
    for p,r,s in ((a,c,d),(b,c,d),(c,a,b),(d,a,b)):
        if math.dist(p,project(p,r,s))<EPS and not any(math.dist(p,q)<EPS for q in pts):
            pts.append(p)
    return pts


def segments(parts):
    for i,part in enumerate(parts,1):
        for j,(a,b) in enumerate(zip(part,part[1:]),1):
            yield (i,j),a,b


def point(p):
    return [round(v,6) for v in p]


def compare(one,two):
    intersections=[]
    best=math.inf
    for i,a,b in segments(one):
        for j,c,d in segments(two):
            for p in hits(a,b,c,d):
                if not any(math.dist(p,h['point'])<1e-5 for h in intersections):
                    intersections.append(dict(point=point(p),segments=[i,j]))
            pairs=[(a,project(a,c,d)),(b,project(b,c,d)),(project(c,a,b),c),(project(d,a,b),d)]
            for u,v in pairs:
                dist=math.dist(u,v)
                if dist<best:
                    best=dist
                    nearest=dict(points=[point(u),point(v)],segments=[i,j])
    if intersections:
        best=0.
        h=intersections[0]
        nearest=dict(points=[h['point']]*2,segments=h['segments'])
    return dict(relation='intersects' if intersections else 'near' if best<=NEAR else 'separate',
                distance_pt=round(best,6),closest=nearest,intersections=intersections)


def angle(a,b):
    cos=dot(a,b)/(math.hypot(*a)*math.hypot(*b))
    return math.degrees(math.acos(max(-1.,min(1.,cos))))


def gap_inventory(roads):
    gaps=[]
    for code,road in roads.items():
        parts=road['parts']
        for i,(a,b) in enumerate(zip(parts,parts[1:]),1):
            p,q=a[-1],b[0]
            chord=sub(q,p)
            dist=math.dist(p,q)
            dev=[angle(sub(p,a[-2]),chord),angle(chord,sub(b[1],q))] if dist else [0.,0.]
            kind='seam' if dist<SEAM else 'aligned' if max(dev)<=10 else 'angled'
            # Chords are diagnostic only, never displayed or added to road geometry.
            crossings=[]
            if kind=='aligned':
                for other,rec in roads.items():
                    if other!=code:
                        result=compare([[p,q]],rec['parts'])
                        if result['intersections']:
                            crossings.append(dict(road=other,intersections=result['intersections']))
            gaps.append(dict(road=code,parts=[i,i+1],points=[p,q],center=point(lerp(p,q,.5)),
                             distance_pt=round(dist,6),angle_degrees=[round(v,2) for v in dev],
                             kind=kind,chord_crossings=crossings))
    return gaps


def build():
    data=json.loads((ROOT/P1).read_text())
    features={f['id']:f for f in data['features']}
    definitions=json.loads((ROOT/P452).read_text())['road_segments']
    roads={}
    for item in sorted(definitions,key=lambda r:r['source_code']):
        f=features[item['feature_id']]
        roads[item['source_code']]=dict(id=f['id'],name=item['name'],
            period=f.get('source_historical_period'), evidence=f['placement_note'],
            drawing_indices=f['source_drawing_indices'],parts=f['source_pdf_geometry']['coordinates'])
    pairs=[dict(roads=[a,b],**compare(roads[a]['parts'],roads[b]['parts'])) for a,b in combinations(roads,2)]
    gaps=gap_inventory(roads)
    river=features['geo-modern-luo-river']
    rc=river['source_pdf_geometry']['coordinates']
    water_checks=[dict(road=code,**compare(road['parts'],[rc])) for code,road in roads.items()]
    gates=[]
    for f in features.values():
        if 'gate' not in f['id'] or f['source_pdf_geometry']['type']!='Point':
            continue
        p=f['source_pdf_geometry']['coordinates']
        distances=[]
        for code,road in roads.items():
            res=compare([[p,p]],road['parts'])
            distances.append(dict(road=code,distance_pt=res['distance_pt'],foot=res['closest']['points'][1]))
        gates.append(dict(id=f['id'],code=f['source_feature_code'],name=f['label'].replace('位置参考',''),
                         point=p,period=f.get('source_historical_period'),evidence=f['placement_note'],roads=sorted(distances,key=lambda r:r['distance_pt'])))
    walls=[dict(id=k,name=features[k]['label'],evidence=features[k]['placement_note'],parts=features[k]['source_pdf_geometry']['coordinates']) for k in WALLS]
    orthogonal=[p for p in pairs if p['roads'][0][:2]!=p['roads'][1][:2]]
    summary=dict(roads=len(roads),parts=sum(len(r['parts']) for r in roads.values()),orthogonal_pairs=len(orthogonal),
                 intersections=sum(len(p['intersections']) for p in orthogonal),
                 near_misses=sum(p['relation']=='near' for p in orthogonal),
                 separate=sum(p['relation']=='separate' for p in orthogonal),
                 aligned_gaps=sum(g['kind']=='aligned' for g in gaps),seams=sum(g['kind']=='seam' for g in gaps),
                 gates=len(gates),near_gates=sum(g['roads'][0]['distance_pt']<=NEAR for g in gates))
    return dict(title='内城路段、门址图符与近现代洛河参照',version='P4.6.2',summary=summary,
            sources=dict(page=3457,map='管理规划图06a',verification_pages=[3454,3455],
                url='https://whc.unesco.org/uploads/nominations/1442.pdf#page=3457',input_files=[str(P1),str(P452)]),
            method=dict(space='同一PDF页，原点左上，x向右、y向下。单位为原图PDF点（pt）。',
                segments='各路保持同页同名矢量子线原有顺序。闭区间线段求交，含首末端接触。最短距离取全部线段的最小欧氏距离。',
                near_threshold_pt=NEAR,seam_threshold_pt=SEAM,alignment_threshold_degrees=10,
                near='未交图线以2 pt作为近接筛选阈值。门址距离按图符中心计算。',
                gaps='同一路号相邻图线末点至下段首点的图绘间隔。小于0.01 pt单列为微小接缝，其余两端切向与缺口方向均在10°以内时记为近共线。',
                gap_chord='弦段只用于判断图绘间隔可否容纳另一条实绘道路，不绘入图中，不计作图上路口。',
                inference='原图线型、制图或提取均可造成图绘留白。路口、废断、古津或桥址的考古认定仍需独立材料。',
                indexing='parts及segments序号自1起，drawing_indices沿用P1原编号。',
                source_geometry='道路以P1从原PDF矢量提取的折线计算；原图三次贝塞尔曲线各经过8个等参数区间采样。',
                river=river['placement_note']),
            roads=roads,walls=walls,gates=gates,river=dict(id=river['id'],name=river['label'],points=rc),
            road_pairs=pairs,road_gaps=gaps,road_to_river=water_checks)


# Paper coordinates in the map panel stay in their native units.
SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)


def tag(element, name, **attrs):
    return ET.SubElement(element, f'{{{SVG}}}{name}',
                         {k.replace('_','-'):str(v) for k,v in attrs.items()})


def txt(el, x, y, label, **attrs):
    tag(el,'text',x=x,y=y,**attrs).text = label


def path(el, coords, **attrs):
    commands = ' '.join(('M' if i == 0 else 'L')+f'{p[0]:.6f} {p[1]:.6f}' for i,p in enumerate(coords))
    return tag(el,'path',d=commands,fill='none',**attrs)


def draw(data):
    root = ET.Element(f'{{{SVG}}}svg', dict(viewBox='0 0 980 796',role='img',
                      **{'aria-labelledby':'map-title map-description','lang':'zh-CN'}))
    tag(root,'title',id='map-title').text = data['title']
    tag(root,'desc',id='map-description').text = '图06a同页复核。八条图示道路，十一个横纵相交处。铜驼大道与宫城南横街近接而留白。蓝线为近现代参照。'
    tag(root,'style').text = """
    text { font-family: 'Noto Sans CJK SC','Microsoft YaHei',sans-serif;fill:#292f2a }
    .fine { fill:#575c53 } .heading { font-weight:700 } .mono { font-family:ui-monospace,monospace }
    .road-label,.gate-label,.water-label { paint-order:stroke;stroke:#faf7ed;stroke-width:1;stroke-linejoin:round }
    .road-label { font-size:3.4px;font-family:ui-monospace,monospace;font-weight:bold }
    .gate-label { font-size:2.85px;fill:#373a35 }
    .water-label {font-size:3px;fill:#236175}
    [data-road], [data-roads] {cursor:pointer}
    """
    paper, panel, ink, line = '#fcfaf3', '#f5f2e8', '#273d37', '#c9c8b9'
    hstroke, vstroke, purple, water = '#ad593d', '#315e53', '#886287', '#347f98'
    tag(root,'rect',width=980,height=796,fill=paper)
    txt(root,24,30,'汉魏洛阳故城  /  研究图 P4.6.2',font_size=14,fill='#5c675e')
    txt(root,24,68,'内城路段、门址图符与洛河参照',font_size=32,**{'class':'heading'})
    txt(root,25,93,'管理规划图 06a 同页比对  ·  地下道路遗存的概略图线，近现代河道单列',font_size=13,**{'class':'fine'})
    tag(root,'rect',x=24,y=111,width=523,height=637,rx=2,fill=panel,stroke=line)
    defs=tag(root,'defs')
    clip=tag(defs,'clipPath',id='p462-panel-clip',clipPathUnits='userSpaceOnUse')
    tag(clip,'rect',x=25,y=112,width=521,height=635)
    frame=tag(root,'g',clip_path='url(#p462-panel-clip)')
    map_el=tag(frame,'g',transform='translate(25.15 112) scale(3.175) translate(-248 -228)')
    walls = tag(map_el,'g',id='walls')
    for wall,stroke,width in zip(data['walls'],['#c4c0ad','#c8c4b8','#afa991'],[1.3,.75,.9]):
        for part in wall['parts']:
            path(walls,part,stroke=stroke,stroke_width=width)
    river = tag(map_el,'g',id='modern-river')
    tag(river,'title').text = '近现代洛河，仅采样可辨中东段'
    path(river,data['river']['points'],stroke=water,stroke_width=1.3)
    txt(river,285,418,'洛河  ·  1997／1999 年底图',**{'class':'water-label'})
    roads = tag(map_el,'g',id='roads')
    label_pos={'Lh-1':(260,384),'Lh-2':(260,328),'Lh-3':(260,295),'Lh-4':(263,267),
               'Lz-1':(357,399),'Lz-2':(340,389),'Lz-3':(308,397),'Lz-4':(285,394)}
    for code,road in data['roads'].items():
        g=tag(roads,'g',id='road-'+code,data_road=code)
        tag(g,'title').text=code+' · '+road['name']
        stroke=hstroke if code in H else vstroke
        for idx,part in enumerate(road['parts'],1):
            path(g,part,stroke=stroke,stroke_width=.64,data_part=idx)
        x,y=label_pos[code]
        txt(g,x,y,code,fill=stroke,**{'class':'road-label'})
    intersections=tag(map_el,'g',id='intersections')
    for row in data['road_pairs']:
        for hit in row['intersections']:
            a,b=row['roads']
            g=tag(intersections,'g',id=f'hit-{a}-{b}',data_roads=f'{a} {b}')
            tag(g,'title').text=f'{a} × {b} · 实绘图线相交'
            x,y=hit['point']
            tag(g,'circle',cx=x,cy=y,r=1.2,fill=paper,stroke=ink,stroke_width=.42)
            tag(g,'circle',cx=x,cy=y,r=.43,fill=ink)
    gaps=tag(map_el,'g',id='gaps')
    for rec in data['road_gaps']:
        code=rec['road']
        p,q=rec['points']
        g=tag(gaps,'g',data_road=code,id=f"gap-{code}-{rec['parts'][0]}")
        tag(g,'title').text=code+' 子线 '+str(rec['parts'])+f" · {rec['distance_pt']:.4f} pt"
        x,y=rec['center']
        if rec['kind']=='seam':
            tag(g,'circle',cx=x,cy=y,r=.65,fill='none',stroke='#817c72',stroke_width=.22)
        else:
            dx,dy=sub(q,p)
            length=math.hypot(dx,dy)
            normal=(-dy/length, dx/length)
            # Offset the purple comb mark so it does not connect two original ends.
            path(g,[(x+normal[0]*.65,y+normal[1]*.65),(x+normal[0]*1.60,y+normal[1]*1.60)],
                 stroke=purple,stroke_width=.44)
    near=tag(map_el,'g',id='near-misses')
    for row in data['road_pairs']:
        if row['relation']=='near':
            a,b=row['roads']
            g=tag(near,'g',id=f'near-{a}-{b}',data_roads=f'{a} {b}')
            tag(g,'title').text=f"{a} × {b} · 近接未交 {row['distance_pt']:.3f} pt"
            x,y=lerp(*row['closest']['points'],.5)
            tag(g,'circle',cx=x,cy=y,r=2.35,stroke='#bd791e',stroke_width=.58,fill='none',
                stroke_dasharray='1.5 .65')
    anchors=tag(map_el,'g',id='anchors')
    gate_offsets={'阊阖门':(2.3,-2.4),'千秋门':(-1.7,-1.7),'云龙门':(1.2,-1.8),'建春门':(1.5,-1.6),
                  '大夏门':(1.8,-1.7),'广莫门':(2.5,0),'西阳门':(1.2,-2.3),'东阳门':(1.2,-2.1),
                  '青阳门':(1.0,-2.0),'西明门':(1.2,-2.2)}
    for gate in data['gates']:
        x,y=gate['point']
        label=gate['name'][2:]
        g=tag(anchors,'g',id=gate['id'],data_gate=gate['code'])
        tag(g,'title').text=gate['name']+' · '+gate['code']+' 图符中心'
        tag(g,'rect',x=x-.7,y=y-.7,width=1.4,height=1.4,fill='#faf7ed',stroke='#524831',stroke_width=.45)
        dx,dy=gate_offsets[label]
        txt(g,x+dx,y+dy,label,text_anchor='end' if dx<0 else 'start',**{'class':'gate-label'})
    # Static legend remains legible if this SVG is opened or downloaded alone.
    right=565
    txt(root,right,133,'横道 × 纵道',font_size=21,**{'class':'heading'})
    txt(root,right,157,'每格比对一组原图线段。近接以纸面距离 2 pt 为限。',font_size=12,**{'class':'fine'})
    lookup={tuple(row['roads']):row for row in data['road_pairs']}
    for j,code in enumerate(V):
        txt(root,659+j*78,184,code,font_size=15,text_anchor='middle',fill=vstroke,**{'class':'mono'})
    styles={'intersects':('相交','#d9e6db','#284f41'),'near':('近接','#f5e4bb','#8a5c19'),
            'separate':('分离','#eeece4','#585b53')}
    for i,a in enumerate(H):
        y=191+i*34
        txt(root,right,y+19,a,font_size=15,fill=hstroke,**{'class':'mono'})
        for j,b in enumerate(V):
            row=lookup[a,b]
            label,bg,fg=styles[row['relation']]
            g=tag(root,'g',data_roads=f'{a} {b}',id=f'cell-{a}-{b}')
            tag(g,'title').text=f"{a} × {b} · {row['distance_pt']:.3f} pt"
            tag(g,'rect',x=623+j*78,y=y,width=72,height=29,rx=3,fill=bg)
            txt(g,659+j*78,y+19,label,font_size=13,text_anchor='middle',fill=fg)
    txt(root,right,354,'宫城南横街与铜驼大道',font_size=19,**{'class':'heading'})
    txt(root,right,378,'Lh-2 从 Lz-3 首段与次段之间的留白穿过。',font_size=14)
    txt(root,right,400,'最短图距约 0.94 pt，图上保留为近接。',font_size=14)
    txt(root,right,446,'图面符号',font_size=19,**{'class':'heading'})
    def legend(y,label,color,kind):
        if kind=='gate':
            tag(root,'rect',x=right+5,y=y-9,width=8,height=8,fill=paper,stroke=color,stroke_width=1.5)
        elif kind=='cross':
            tag(root,'circle',cx=right+9,cy=y-5,r=5,fill=paper,stroke=color,stroke_width=1.5)
            tag(root,'circle',cx=right+9,cy=y-5,r=2,fill=color)
        elif kind=='near':
            tag(root,'circle',cx=right+9,cy=y-5,r=6,fill='none',stroke=color,stroke_width=1.9,stroke_dasharray='4 2')
        elif kind=='gap':
            path(root,[(right+8,y-10),(right+10,y-2)],stroke=color,stroke_width=2)
        else:
            path(root,[(right,y-5),(right+18,y-5)],stroke=color,stroke_width=2.7)
        txt(root,right+28,y,label,font_size=13)
    for i,args in enumerate([('横道原图子线',hstroke,'line'),('纵道原图子线',vstroke,'line'),
                             ('实绘线交点',ink,'cross'),('图线近接未交（≤ 2 pt）','#bd791e','near'),
                             ('近共线的图绘间隔（侧边短划）',purple,'gap'),
                             ('门址图符中心','#524831','gate'),('内城及宫城墙线遗存','#b1ad9b','line'),
                             ('近现代洛河中东段概略线',water,'line')]):
        legend(471+i*24,*args)
    txt(root,right,683,'单位为原 PDF 页面的点（pt）。',font_size=13,**{'class':'fine'})
    txt(root,right,705,'图线交会与原图留白均须由发掘资料另行核对。',font_size=13,**{'class':'fine'})
    tag(root,'path',d='M24 759H956',stroke=line)
    txt(root,24,780,'来源　丝绸之路申遗文本 C02-CN 管理规划图 06a（PDF 第 3457 页），结合图 04 编号；洛河仅作 1997 年航摄、1999 年实测底图参照。',font_size=11,**{'class':'fine'})
    ET.indent(root)
    ET.ElementTree(root).write(OUT/'network.svg',encoding='utf-8',xml_declaration=True)


if __name__ == '__main__':
    data=build()
    OUT.mkdir(exist_ok=True,parents=True)
    (OUT/'network.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    draw(data)
