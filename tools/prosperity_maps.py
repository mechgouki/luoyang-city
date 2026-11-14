"""Draw source-coordinate city layouts without converting documentary pixels to GPS."""
from pathlib import Path
import copy, math, json, xml.etree.ElementTree as ET
from pyproj import Transformer
from dual_cartography import NS, C, node, text, para, rect, path, svg, world, write_svg

PROJECTION = '+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=aeqd +lat_0=34.7333333333 +lon_0=112.6166666667 +a=6378140 +rf=298.257'

def all_points(geometry):
    kind=geometry['type']; c=geometry['coordinates']
    if kind=='Point': return [c]
    if kind=='LineString': return c
    if kind in ('Polygon','MultiLineString'): return [p for ring in c for p in ring]
    if kind=='MultiPolygon': return [p for poly in c for ring in poly for p in ring]
    raise ValueError('Unsupported geometry '+kind)

def projected_features(features):
    t=Transformer.from_pipeline(PROJECTION)
    def convert(c):
        if isinstance(c[0],(int,float)):
            x,y=t.transform(float(c[0]),float(c[1])); return [x,y]
        return [convert(v) for v in c]
    return [dict(f,projected_geometry={'type':f['geometry']['type'],'coordinates':convert(f['geometry']['coordinates'])}) for f in features]

def title(r,kicker,heading,note,w=1800):
    text(r,65,52,kicker,18,C['gold'])
    text(r,65,103,heading,38,C['ink'],weight=500)
    text(r,65,142,note,19,C['muted'])
    path(r,f'M65 163H{w-65}',C['line'],1.5)

def source_layout(features,panorama=False,detail=False):
    projected=projected_features(features)
    pts=[p for f in projected for p in all_points(f['projected_geometry'])]
    if not pts: raise ValueError('No reviewed source geometry; refuse placeholder city')
    xs,ys=zip(*pts); xmin,xmax=min(xs)-300,max(xs)+300; ymin,ymax=min(ys)-300,max(ys)+300
    W,H=1800,1100 if panorama else 1440
    r=svg(W,H,'盛时城市分布 · 来源图坐标下的工作布局' if not panorama else '同一城市骨架的布局鸟瞰')
    title(r,'LUOYANG / PROSPERITY / SOURCE-GRID LAYOUT',
          '宫城、内城与永宁寺' if detail else '城市骨架，进入地理空间' if not panorama else '从同一套布局，望向洛阳',
          '西安1980原图经纬网；来源图所绘遗址与范围。古今地面和建筑时层分别核对。' if not panorama else '平面来自同一套来源图坐标；抬高线条仅帮助阅读，不表示古代墙高或建筑体量。')
    scale=min(1540/(xmax-xmin),1080/(ymax-ymin))
    if panorama: scale=min(1500/((xmax-xmin)+.28*(ymax-ymin)),720/(.63*(ymax-ymin)))
    def xy(x,y,z=0):
        if panorama:
            width=((xmax-xmin)+.28*(ymax-ymin))*scale;height=.63*(ymax-ymin)*scale
            return [150+(1500-width)/2+(x-xmin)*scale+.28*(y-ymin)*scale,205+(720-height)/2+height-(y-ymin)*scale*.63-z]
        return [130+(1540-(xmax-xmin)*scale)/2+(x-xmin)*scale,210+(1080-(ymax-ymin)*scale)/2+(ymax-y)*scale]
    frame=[xy(xmin,ymin),xy(xmax,ymin),xy(xmax,ymax),xy(xmin,ymax)]
    node(r,'polygon',points=' '.join(f'{x:.2f},{y:.2f}' for x,y in frame),fill='#eef1e6',stroke='#ccd5c5',stroke_width=1.5)
    # This is a metric reading grid in the original datum, not a recovered ancient ground surface.
    for x in range(math.ceil(xmin/1000)*1000,math.floor(xmax/1000)*1000+1,1000):
        a,b=xy(x,ymin),xy(x,ymax);path(r,f'M{a[0]} {a[1]}L{b[0]} {b[1]}','#d7ddcf',1)
    for y in range(math.ceil(ymin/1000)*1000,math.floor(ymax/1000)*1000+1,1000):
        a,b=xy(xmin,y),xy(xmax,y);path(r,f'M{a[0]} {a[1]}L{b[0]} {b[1]}','#d7ddcf',1)
    boxes={}; labels=[]
    historical=node(r,'g',data_layer='site_remains')
    modern=node(r,'g',data_layer='modern_reference')
    ordered=sorted(projected,key=lambda f:0 if f.get('layer')=='layout_envelope' else 2 if f['geometry']['type']=='Point' else 1)
    for idx,f in enumerate(ordered):
        gdata=f['projected_geometry']; typ=gdata['type']; c=gdata['coordinates']
        fid=f['id'];is_modern=fid.startswith('geo-modern-');is_envelope=f.get('layer')=='layout_envelope'
        cat=f.get('category') or ('modern_river' if 'modern-luo' in fid else 'road' if 'road-' in fid or 'tongtuo-' in fid else 'wall' if 'wall' in fid else 'site')
        eid=f.get('entity_id')
        co='#4b8794' if cat in ('river','water','modern_river') else '#b58c56' if cat in ('road','axis') else '#9b7258' if cat in ('wall','city_wall','palace_wall') else '#386d5b'
        parent=modern if is_modern else historical
        el=node(parent,'g',data_feature_id=f['id'],data_entity_id=eid,data_coordinate_frame='source_xian1980',data_geometry_role='display_envelope_no_wall_evidence' if is_envelope else f.get('geometry_role','source_map_generalized'))
        node(el,'title').text=f.get('label',f['id'])+'；'+f.get('placement_note','来源图所绘对象，非本项目实测。')
        def line(ring,closed=False):
            points=[xy(*p) for p in ring];d='M'+'L'.join(f'{a:.2f} {b:.2f}' for a,b in points)+('Z' if closed else '')
            underground='underground' in f.get('source_legend','').lower() or f.get('rendering',{}).get('line_style')=='dashed' or fid in ('geo-jinyong-bing-wall','geo-yongning-temple-walls')
            dash='9 6' if f.get('dashed') or underground or 'underground' in fid or 'outer-city' in fid or cat in ('modern_river','road') else None
            if is_envelope:
                node(el,'path',d=d,fill='#386d5b',fill_opacity=f.get('rendering',{}).get('fill_opacity',.10),stroke='none')
            else:
                path(el,d,co,2.3 if cat=='road' else 3.4,dash,'none')
            if panorama and cat in ('wall','city_wall','palace_wall'):
                raised=[xy(*p,z=7) for p in ring]
                path(el,'M'+'L'.join(f'{a:.2f} {b:.2f}' for a,b in raised),co,3,dash)
        if typ=='Point':
            x,y=xy(*c);node(el,'circle',cx=x,cy=y,r=8,fill=C['paper'],stroke=co,stroke_width=2.5)
            node(el,'circle',cx=x,cy=y,r=3,fill=co)
        elif typ=='LineString':line(c)
        elif typ=='Polygon':
            for ring in c:line(ring,True)
        elif typ=='MultiLineString':
            for ring in c:line(ring)
        elif typ=='MultiPolygon':
            for poly in c:
                for ring in poly:line(ring,True)
        qp=[xy(*p) for p in all_points(gdata)];xx,yy=zip(*qp)
        if eid:
            b=[min(xx)-24,min(yy)-24,max(max(xx)-min(xx)+48,100),max(max(yy)-min(yy)+48,100)]
            if eid in boxes:
                old=boxes[eid];right=max(old[0]+old[2],b[0]+b[2]);bottom=max(old[1]+old[3],b[1]+b[3]);b=[min(old[0],b[0]),min(old[1],b[1]),right-min(old[0],b[0]),bottom-min(old[1],b[1])]
            boxes[eid]=b
        if f.get('show_label',typ=='Point' or cat=='modern_river' or 'outer-city' in fid):
            ax=sum(xx)/len(xx);ay=sum(yy)/len(yy)
            label=f.get('short_label',f.get('label',fid)).replace('位置参考','').replace('内城','').replace('宫城','').replace('遗址','').replace('（来源图标注）','')
            if fid=='geo-changhe-palace-gate':label='宫城阊阖门'
            if 'outer-city' in fid:
                label='外郭相关遗存范围（概略）';ax=min(xx)+65;ay=min(yy)+35
            labels.append((ax,ay,label,co,eid,parent))
    occupied=[]
    for ax,ay,label,co,eid,parent in labels:
        width=sum(18 if ord(ch)>127 else 10 for ch in label)
        candidates=[(ax+16,ay-12),(ax+16,ay+28),(ax-width-16,ay-12),(ax-width-16,ay+28),
                    (ax+16,ay-44),(ax-width-16,ay-44),(ax+16,ay+60),(ax-width-16,ay+60)]
        best=None
        for x,y in candidates:
            x=max(145,min(x,1645-width));y=max(235,min(y,H-170));b=(x-5,y-20,x+width+5,y+5)
            overlap=sum(max(0,min(b[2],o[2])-max(b[0],o[0]))*max(0,min(b[3],o[3])-max(b[1],o[1])) for o in occupied)
            score=overlap*100+abs(x-ax)+abs(y-ay)
            if best is None or score<best[0]:best=(score,x,y,b)
        _,x,y,b=best;occupied.append(b)
        if abs(y-ay)>18 or x<ax:path(parent,f'M{ax} {ay}L{min(max(ax,x),x+width)} {y-8}',co,1)
        rect(parent,x-3,y-20,width+6,26,C['paper'],rx=2).set('opacity','.94')
        t=text(parent,x,y,label,18,co,weight=500)
        if eid:t.set('data-entity-id',eid)
    text(r,1690,215,'北 ↗' if panorama else '北 ↑',23,C['green'],'end',500)
    text(r,65,H-136,'实线：地上遗存　虚线：地下或概略线路　圆点：图示代表位置　淡色：宫城布局参考范围',18,C['muted'])
    text(r,65,H-105,'西安1980来源图坐标；现代DSM另页，河山参照按1997/1999底图显示。',19,C['muted'])
    text(r,65,H-75,'范围与符号保留原图概化；未定位地点继续在文献图中阅读。近现代河流不作北魏河道。',19,C['muted'])
    if panorama:text(r,65,H-44,'斜视图与平面图逐点使用相同几何；没有据此填补坊墙、民居密度、古代地面或建筑立面。',18,C['muted'])
    else:
        x,y=1360,1390; length=1000*scale
        path(r,f'M{x} {y}h{length}',C['ink'],4);text(r,x,y-13,'来源坐标局部米制参考 · 1 km',16,C['muted'])
    return r,boxes,{'source_crs':'EPSG:4610','projection_pipeline':PROJECTION,'datum_conversion_performed':False,'local_extent_m':[xmin,ymin,xmax,ymax],'grid_m':1000,'geometry_features':len(features),'heights_reconstructed':False}

def literary_plan(source,ledger):
    r=ET.parse(source).getroot(); w=world(r)
    for g in list(w):
        if g.get('id')=='city-audit-overlay-b8':w.remove(g)
    for n in r:
        cls=n.get('class','')
        replacement={'wt497 tb497':'北魏洛阳 · 盛时文献平面','wt498 tb498':'516—528 盛时综合；文献关系与地理位置分别阅读。','wt506 tb506':'本批核对原文、节录与校注。扶桑海为水体；都堂在柰林西，组内仍不补地理位置。','wt509 tb509':'盛时文献工作图 / P1'}.get(cls)
        if replacement:
            for ch in list(n):n.remove(ch)
            n.text=replacement
    hits=node(w,'g',id='prosperity-plan-targets',data_coordinate_frame='documentary_canvas')
    targets={t['id']:t for e in ledger for t in e['targets']}
    for tid,t in targets.items():
        attrs={'data-target-id':tid,'data-entity-ids':' '.join(t['member_ids']),'data-members':json.dumps(t['member_ids'])}
        if len(t['member_ids'])==1:attrs['data-entity-id']=t['member_ids'][0]
        hit=node(hits,'circle',cx=t['x'],cy=t['y'],r=108,fill='transparent',style='pointer-events:all;cursor:pointer',**attrs)
        node(hit,'title').text=t['label']+('（共享阅读组）' if len(t['member_ids'])>1 else '')
    r.set('width','12400');r.set('height','12030')
    return r

def palace_relations():
    r=svg(1800,1350,'宫苑引文更正：都堂、柰林与扶桑海')
    title(r,'TEXT / SPATIAL RELATIONS / G13','一个字、一个参照物，改变怎样读图','以下四幅分别表示文献关系；各图间距不换算为古代距离。')
    rows=[('都堂在柰林西','都堂','柰林','西 ←','旧引“碑西”更正为“柰林西”。'),
          ('堂东有扶桑海','都堂','扶桑海','→ 东','水体以“海”为名；没有据此画出池岸。'),
          ('柰林南有碑','柰林','石碑','南 ↓','石碑在柰林南；文献没有记两者距离。'),
          ('碑北作苗茨堂','苗茨堂','石碑','↑ 北','高祖于碑北作苗茨堂；堂、碑间距未记。')]
    for i,(h,a,b,direction,note) in enumerate(rows):
        x=65+(i%2)*855;y=215+(i//2)*475
        rect(r,x,y,815,430,'#edf0e5',C['line'],1,10)
        text(r,x+30,y+55,f'0{i+1}  {h}',29,C['ink'],weight=500)
        if i<2:
            text(r,x+155,y+212,a,33,C['green'],'middle',500)
            if i==1:
                node(r,'ellipse',cx=x+650,cy=y+201,rx=112,ry=52,fill='#dce9eb',stroke=C['blue'],stroke_width=2)
                text(r,x+650,y+213,b,33,C['blue'],'middle',500)
            else:text(r,x+650,y+212,b,33,C['green'],'middle',500)
            path(r,f'M{x+265} {y+201}H{x+520}',C['gold'],2)
            text(r,x+392,y+175,direction,24,C['gold'],'middle')
        else:
            text(r,x+408,y+159,a,31,C['green'],'middle',500)
            text(r,x+408,y+279,b,31,C['green'],'middle',500)
            path(r,f'M{x+408} {y+178}V{y+239}',C['gold'],2)
            text(r,x+485,y+218,direction,24,C['gold'])
        para(r,x+30,y+365,note,32,21)
    para(r,65,1197,'四幅图分别表达方位，不拼成院内总平面。百果园归属的篇章回指单独解释；未给柰林、碑、都堂或扶桑海添加古址经纬度。',75,22)
    text(r,65,1308,'来源：周校本卷一0094a12–14、0095a11–12；范校本0406a11–12、0407a02。',20,C['muted'])
    return r
