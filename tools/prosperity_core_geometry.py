"""Measured plan templates and explicitly schematic local structures for P2."""
import math
from pyproj import Transformer
from dual_cartography import C, node, text, para, rect, path, svg
from prosperity_maps import PROJECTION, projected_features, all_points

ITEMS = [
    ('core-changhe', 'M02', 'geo-changhe-palace-gate', '宫城阊阖门基', 'ic_changhe_palace', 44.5, 24.4, 1927),
    ('core-taiji', 'M03', 'geo-taiji-hall-reference', '太极殿遗址', None, 100.0, 60.0, 1930),
    ('core-yongning-tower', 'M05', 'geo-yongning-pagoda-reference', '永宁寺塔基', 'ic_yongning', 38.2, 38.2, 1931),
]
SOURCE = 'https://whc.unesco.org/uploads/nominations/1442.pdf'
COLORS = {'core-changhe':'#986c39', 'core-taiji':'#345f50', 'core-yongning-tower':'#537e86'}

def polygon(center, width, depth, angle=0):
    """Rectangle dimensions stay metric; rotation is a recorded working choice."""
    a=math.radians(angle); c,s=math.cos(a),math.sin(a)
    return [[center[0]+x*c-y*s, center[1]+x*s+y*c]
            for x,y in [(-width/2,-depth/2),(width/2,-depth/2),(width/2,depth/2),(-width/2,depth/2)]]

def bbox(points, pad=0):
    xs,ys=zip(*points)
    return [min(xs)-pad,min(ys)-pad,max(xs)-min(xs)+2*pad,max(ys)-min(ys)+2*pad]

def scale_models(geo, basis):
    source={f['id']:f for f in geo['features']}
    rules={t['source_feature_id']:t for t in basis['templates']}
    transform=Transformer.from_pipeline(PROJECTION)
    models=[]
    for ident,dimid,fid,name,eid,width,depth,page in ITEMS:
        f=source[fid]; rule=rules[fid]
        assert f['geometry']['type']=='Point'
        assert rule['dimensions_m']=={'east_west':width,'north_south':depth}
        center=list(transform.transform(*f['geometry']['coordinates']))
        angle=rule['orientation_angle_deg']
        assert rule['orientation_verified'] is False
        models.append({'id':ident,'name':name,'dimension_record_id':dimid,'entity_id':eid,
            'source_feature_id':fid,'anchor_source_coordinates':f['geometry']['coordinates'],
            'source_crs':'EPSG:4610','projection_pipeline':PROJECTION,'center_xy_m':center,
            'dimensions_m':{'east_west':width,'north_south':depth},
            'approximate_dimensions':ident in ('core-taiji','core-yongning-tower'),
            'orientation_angle_deg':angle,'orientation_verified':False,
            'orientation_convention':'north_axis_clockwise_from_local_north',
            'polygon_xy_m':polygon(center,width,depth,-angle),
            'geometry_role':'dimension_template_at_generalized_source_anchor',
            'historical_height_m':None,'roof_model':None,
            'surviving_height_m':2.2 if dimid=='M05' else None,
            'below_surface_or_fill_depth_m_approx':6 if dimid=='M03' else None,
            'position_note':rule['position_note'],'orientation_note':rule['orientation_note'],
            'source_url':SOURCE+'#page='+str(page),'source_label':'申遗附表 · PDF '+str(page),
            'drawing_lift_px':7,'drawing_lift_is_historical_height':False})
    return models

def heading(r,title,note,w=1800):
    text(r,65,48,'LUOYANG / CORE BUILDINGS / PLAN & SCALE',18,C['gold'])
    text(r,65,103,title,37,C['ink'],weight=500)
    text(r,65,145,note,19,C['muted'])
    path(r,f'M65 170H{w-65}',C['line'],1.5)

def points_attr(points):return ' '.join(f'{x:.3f},{y:.3f}' for x,y in points)

def label(parent,x,y,label,color,size=22):
    width=sum(size if ord(ch)>127 else size*.55 for ch in label)
    rect(parent,x-6,y-size-3,width+12,size+11,C['paper'],rx=3).set('opacity','.95')
    text(parent,x,y,label,size,color,weight=500)

def core_map(geo,models,oblique=False):
    W,H=1800,1500
    r=svg(W,H,'核心建筑尺度与布局鸟瞰' if oblique else '宫城与永宁寺核心建筑尺度平面')
    heading(r,'同一布局，进入建筑尺度' if oblique else '从代表位置，到定尺平面',
            '定尺片沿用概略位置；工作朝向另记。斜视厚度仅用于阅读。' if oblique else '宫城阊阖门、太极殿与永宁塔基；位置依据和尺寸依据分别保留。')
    source=projected_features(geo['features']); source_by_id={f['id']:f for f in source}
    palace=all_points(source_by_id['geo-palace-walls']['projected_geometry'])
    temple=all_points(source_by_id['geo-yongning-temple-walls']['projected_geometry'])
    core_points=palace+temple
    x,y,w,h=bbox(core_points,190)
    xmin,ymin,xmax,ymax=x,y,x+w,y+h
    panel=(100,210,1600,1080)
    scale=min(panel[2]/(w+.32*h if oblique else w),panel[3]/(.67*h if oblique else h))
    dw=(w+.32*h if oblique else w)*scale;dh=(.67*h if oblique else h)*scale
    left=panel[0]+(panel[2]-dw)/2;top=panel[1]+(panel[3]-dh)/2
    def xy(a,b,lift=0):
        return [left+((a-xmin)+(.32*(b-ymin) if oblique else 0))*scale,
                top+dh-(b-ymin)*scale*(.67 if oblique else 1)-lift]
    frame=[xy(xmin,ymin),xy(xmax,ymin),xy(xmax,ymax),xy(xmin,ymax)]
    node(r,'polygon',points=points_attr(frame),fill='#eef1e7',stroke='#ccd5c5',stroke_width=1.5)
    defs=node(r,'defs');clip=node(defs,'clipPath',id='core-frame');node(clip,'polygon',points=points_attr(frame))
    grid=node(r,'g',clip_path='url(#core-frame)',data_layer='metric_reading_grid')
    for a in range(math.ceil(xmin/200)*200,math.floor(xmax/200)*200+1,200):
        p,q=xy(a,ymin),xy(a,ymax);path(grid,f'M{p[0]} {p[1]}L{q[0]} {q[1]}','#dbe1d4',1)
    for b in range(math.ceil(ymin/200)*200,math.floor(ymax/200)*200+1,200):
        p,q=xy(xmin,b),xy(xmax,b);path(grid,f'M{p[0]} {p[1]}L{q[0]} {q[1]}','#dbe1d4',1)
    context=node(r,'g',clip_path='url(#core-frame)',data_layer='unchanged_source_context')
    context_ids=['geo-palace-layout-envelope','geo-palace-walls','geo-yongning-temple-walls',
                 'geo-tongtuo-avenue','geo-tongtuo-cross-street','geo-road-east-west-middle',
                 'geo-road-north-south-west','geo-road-east-west-north']
    for fid in context_ids:
        f=source_by_id[fid];geo_f=f['projected_geometry'];g=node(context,'g',data_source_feature_id=fid)
        node(g,'title').text=f['label']+'；沿用来源图遗存，不添加缺失墙段。'
        rings=geo_f['coordinates']
        if geo_f['type']=='Polygon':
            for ring in rings:node(g,'polygon',points=points_attr([xy(*p) for p in ring]),fill='#476a53',fill_opacity='.08',stroke='none')
        else:
            is_wall=fid in ['geo-palace-walls','geo-yongning-temple-walls']
            for ring in rings:
                path(g,'M'+'L'.join(f'{a:.3f} {b:.3f}' for a,b in [xy(*p) for p in ring]),
                     '#9b795a' if is_wall else '#bea678',2.6 if is_wall else 2,'8 5')
    # These labels identify source context, without inventing additional templates.
    for fid in ['geo-qianqiu-gate','geo-yunlong-gate']:
        f=source_by_id[fid];a,b=xy(*f['projected_geometry']['coordinates'])
        node(context,'circle',cx=a,cy=b,r=5,fill=C['paper'],stroke=C['muted'],stroke_width=1.8)
        label(context,a+10,b-10,f['label'].replace('宫城','').replace('位置参考',''),C['muted'],18)
    p=xy(sum(a for a,b in palace)/len(palace),max(b for a,b in palace)-100)
    label(r,p[0]-80,p[1],'宫城图示范围',C['muted'],23)
    p=xy(min(a for a,b in temple)-120,min(b for a,b in temple)+100)
    label(r,p[0]-135,p[1],'永宁寺墙线',C['muted'],20)
    boxes={}
    for m in sorted(models,key=lambda m:m['center_xy_m'][1],reverse=True):
        ident=m['id'];color=COLORS[ident];lift=m['drawing_lift_px'] if oblique else 0
        g=node(r,'g',data_core_id=ident,data_source_feature_id=m['source_feature_id'],
               data_geometry_role=m['geometry_role'],data_historical_height='unknown')
        node(g,'title').text=m['name']+'；'+m['position_note']+' '+m['orientation_note']
        ground=[xy(*p) for p in m['polygon_xy_m']];top_points=[xy(*p,lift) for p in m['polygon_xy_m']]
        if lift:
            for i in range(4):
                j=(i+1)%4
                node(g,'polygon',points=points_attr([ground[i],ground[j],top_points[j],top_points[i]]),fill=color,fill_opacity='.45',stroke=color,stroke_width='.6',data_role='drawing_thickness')
        node(g,'polygon',points=points_attr(top_points),fill=color,fill_opacity='.28',stroke=color,stroke_width=2.3,data_role='dimension_template')
        a,b=xy(*m['center_xy_m'],lift)
        node(g,'circle',cx=a,cy=b,r=3,fill=color,data_role='source_anchor')
        # Transparent hit zone improves access while leaving the measured polygon unchanged.
        node(g,'circle',cx=a,cy=b,r=22,fill='transparent',data_role='interaction_only',style='pointer-events:all')
        label(g,a+32,b-19,m['name'],color,23)
        dim=m['dimensions_m'];prefix='约 ' if m['approximate_dimensions'] else ''
        label(g,a+32,b+12,prefix+f"{dim['east_west']:g} × {dim['north_south']:g} m",C['muted'],18)
        boxes[ident]=bbox(ground+top_points,32)
    focuses={'all':[0,0,W,H]}
    for ident,pts in [('palace',palace),('yongning',temple)]:
        b=bbox([xy(*p) for p in pts],90);focuses[ident]=b
    text(r,1680,220,'北 ↗' if oblique else '北 ↑',24,C['green'],'end')
    text(r,65,1352,'彩色面：表列尺度片　虚线：原图遗存线　圆心：原图代表位置　网格：200 m',19,C['muted'])
    text(r,65,1392,'院墙沿用原图；301 × 212 m 院界模板仅在独立校核图中比较，不覆盖遗存线。',19,C['muted'])
    text(r,65,1430,'基准：西安1980来源框架；画布基面不是北魏地面。建筑原高与屋顶保持未知。',19,C['muted'])
    bar=200*scale;path(r,f'M1360 1470h{bar:.3f}',C['ink'],3)
    text(r,1360,1453,'200 m · 平面东西向',16,C['muted'])
    return r,boxes,focuses,{'source_crs':'EPSG:4610','projection_pipeline':PROJECTION,
        'extent_xy_m':[xmin,ymin,xmax,ymax],'meters_to_svg_px':scale,'oblique':oblique,
        'oblique_y_scale':.67 if oblique else 1,'oblique_x_shear':.32 if oblique else 0,
        'affine_svg_from_metric':[scale,0,(.32 if oblique else 0)*scale,-(.67 if oblique else 1)*scale,
            left-xmin*scale-(.32 if oblique else 0)*ymin*scale,
            top+dh+(.67 if oblique else 1)*ymin*scale],
        'historical_heights_reconstructed':False,'ancient_ground_surface_reconstructed':False,
        'source_context_feature_ids':context_ids}

def dimension_figure(m,comparison=False):
    r=svg(1100,820,m['name']+'尺度参照')
    heading(r,m['name'],'依据附表制作的外接尺度片；不作为完整建筑轮廓。',1100)
    dim=m['dimensions_m'];scale=min(650/dim['east_west'],380/dim['north_south'])
    w,h=dim['east_west']*scale,dim['north_south']*scale;x=(1100-w)/2;y=405-h/2
    rect(r,x,y,w,h,COLORS[m['id']],COLORS[m['id']],2,0).set('fill-opacity','.18')
    path(r,f'M{x} {y-24}H{x+w} M{x} {y-32}V{y-16} M{x+w} {y-32}V{y-16}',C['ink'],1.7)
    text(r,550,y-38,f"东西 {'约' if m['approximate_dimensions'] else ''}{dim['east_west']:g} m",24,C['ink'],'middle')
    path(r,f'M{x+w+24} {y}V{y+h} M{x+w+16} {y}H{x+w+32} M{x+w+16} {y+h}H{x+w+32}',C['ink'],1.7)
    text(r,x+w+45,y+h/2,f"南北 {dim['north_south']:g} m",22,C['ink'])
    text(r,65,675,m['source_label']+'；位置与尺寸来自不同尺度的记录。',21,C['muted'])
    para(r,65,722,'盛时原高和屋顶未定。'+('约6 m为地下夯土深度。' if m['id']=='core-taiji' else '2.2 m为现存塔基残高。' if m['id']=='core-yongning-tower' else '此尺寸只指门基，不包括整组阙、院与连接基址。'),49,21)
    return r

def comparison_plate(models):
    r=svg(1800,1320,'三个核心建筑的同尺度比较')
    heading(r,'同一比例，看清门基、殿址与塔基','以下三片共用同一米制比例；空白不代表周边没有其他建筑。')
    scale=4.7; centers=[345,900,1455];base_y=790
    for m,cx in zip(models,centers):
        col=COLORS[m['id']];d=m['dimensions_m'];w,h=d['east_west']*scale,d['north_south']*scale
        rect(r,cx-255,240,510,715,'#eef1e7',C['line'],1,7)
        text(r,cx,300,m['name'],29,col,'middle',500)
        text(r,cx,342,('约 ' if m['approximate_dimensions'] else '')+f"{d['east_west']:g} × {d['north_south']:g} m",24,C['muted'],'middle')
        rect(r,cx-w/2,base_y-h,w,h,col,col,2).set('fill-opacity','.25')
        path(r,f'M{cx-w/2} {base_y+27}h{w}',col,2)
        text(r,cx,base_y+66,f"{d['east_west']:g} m",24,col,'middle')
        text(r,cx,915,'外接尺度片 · 上部形制未定',19,C['muted'],'middle')
    path(r,'M80 1030h470',C['ink'],3);text(r,80,1011,'100 m · 三片同一比例',22,C['ink'])
    para(r,65,1110,'太极殿约100 × 60 m是遗址平面范围；阊阖44.5 × 24.4 m只指门基。永宁塔基38.2 m方形取自地上遗存记录。三片均不直接给出盛时屋顶范围。',76,24)
    text(r,65,1260,'依据：申遗附录PDF1927、1930—1931。残高与地下夯土深度没有用于向上拉伸。',20,C['muted'])
    return r

def courtyard_plate(geo,basis):
    """Compare incompatible scales without placing the diagnostic courtyard in the city."""
    diag=basis['courtyard_diagnostic']
    assert diag['fit_adopted_for_city_overlay'] is False and not diag['north_side_observed']
    r=svg(1800,1450,'永宁寺院界尺度校核')
    heading(r,'永宁寺院界，先校核再落位','两侧共用同一比例；左为来源图墙线，右为附表外接尺度框。')
    for x in (65,935):rect(r,x,215,800,840,'#eef1e7',C['line'],1,8)
    text(r,100,272,'A  来源图中可读的三面墙',28,C['green'],weight=500)
    text(r,970,272,'B  附表范围的独立尺度框',28,C['gold'],weight=500)
    scale=1.8; centers=[(465,650),(1335,650)]
    angle=math.radians(diag['fit_angle_deg']);cos,sin=math.cos(angle),math.sin(angle)
    origin=diag['fit_center_local_m']
    def local(p):
        x,y=p[0]-origin[0],p[1]-origin[1]
        return [x*cos-y*sin,x*sin+y*cos]
    def xy(p,side=0):return [centers[side][0]+p[0]*scale,centers[side][1]-p[1]*scale]
    wall_group=node(r,'g',data_role='source_wall_comparison',data_source_feature_id=diag['source_feature_id'])
    for ring in diag['source_wall_geometry_local_m']['coordinates']:
        pts=[xy(local(p)) for p in ring]
        path(wall_group,'M'+'L'.join(f'{a:.3f} {b:.3f}' for a,b in pts),'#9b795a',3,'8 5')
    tower=xy(local(diag['tower_anchor_local_m']))
    node(wall_group,'circle',cx=tower[0],cy=tower[1],r=7,fill=C['paper'],stroke=C['green'],stroke_width=2)
    label(wall_group,tower[0]+18,tower[1]-12,'原图塔基符号',C['green'],21)
    text(r,465,335,'北侧没有可读墙线，保持开口',20,C['muted'],'middle')
    template=node(r,'g',data_role='unplaced_dimension_comparison',data_city_overlay_allowed='false')
    w,h=diag['table_width_m']*scale,diag['table_length_m']*scale
    q=rect(template,1335-w/2,650-h/2,w,h,'none',C['gold'],2.5,0);q.set('stroke-dasharray','9 6')
    text(template,1335,628,'212 × 301 m',30,C['gold'],'middle',500)
    text(template,1335,669,'独立比较 · 没有地理落点',20,C['muted'],'middle')
    text(r,1335,335,'虚框不是已定位的四面古墙',20,C['muted'],'middle')
    text(r,465,974,f"来源图墙间距约 {diag['measured_wall_spacing_m']:.1f} m",24,C['ink'],'middle')
    text(r,1335,974,'表列东西范围 212 m',24,C['ink'],'middle')
    for x in (115,985):
        path(r,f'M{x} 1020h{100*scale}',C['ink'],3);text(r,x+100*scale+15,1026,'100 m',18,C['muted'])
    delta=diag['measured_wall_spacing_m']-diag['table_width_m']
    text(r,65,1120,f'图内宽度相差约 {delta:.1f} m；不能同时把两组边界当成同一个已证院界。',27,C['ink'],weight=500)
    para(r,65,1170,'把212 × 301 m框贴合来源南墙，会使诊断院心几乎与塔符中心重合；完整院内复原参照图却呈现塔偏院心南侧。当前拟合未获采用，塔点也未被用作拟合控制。',75,23)
    para(r,65,1275,'这里比较的是来源图内部的概化与尺度差异，不是现场院宽、古址误差或定位精度。原三面墙、表列尺寸和塔的相对关系分别保留，等待更细的共同依据。',75,22)
    text(r,65,1402,'依据：PDF1931附表、3457来源总图、3453院内复原参照。没有新增北墙或改变P1原坐标。',19,C['muted'])
    return r

def relation_plate(scene):
    r=svg(1800,1400,scene['title'])
    heading(r,scene['title'],'局部构成关系 · 非测绘比例；节点大小和间距属于阅读安排。')
    nodes={n['id']:n for n in scene['nodes']}
    raw=[]
    for n in nodes.values():
        q=n['diagram_layout'];raw += [[q['x'],q['y']],[q['x']+q['width'],q['y']+q['height']]]
    minx,miny,width,height=bbox(raw);scale=min(1570/max(width,1),870/max(height,1))
    ox=115+(1570-width*scale)/2;oy=220+(870-height*scale)/2
    def qbox(n):
        q=n['diagram_layout'];return [ox+(q['x']-minx)*scale,oy+(q['y']-miny)*scale,q['width']*scale,q['height']*scale]
    for edge in scene['relations']:
        if not any(s in edge['relation'] for s in ['connect','接']):continue
        if edge['subject'] not in nodes or edge['object'] not in nodes:continue
        a,b=qbox(nodes[edge['subject']]),qbox(nodes[edge['object']]);p=[a[0]+a[2]/2,a[1]+a[3]/2];q=[b[0]+b[2]/2,b[1]+b[3]/2]
        path(r,f'M{p[0]} {p[1]}L{q[0]} {q[1]}','#b4b9a8',2,'5 5')
    # Container symbols precede their children and stay visually distinct from measured plans.
    ordered=sorted(nodes.values(),key=lambda n:n['diagram_layout']['width']*n['diagram_layout']['height'],reverse=True)
    for n in ordered:
        x,y,w,h=qbox(n);g=node(r,'g',data_component_id=n['id'],data_coordinate_semantics='schematic_not_metric')
        shape=n['diagram_layout'].get('shape','box')
        container=shape in ('conceptual_frame','square_outline','dashed_surrounding_band') or n['kind']=='gate_base'
        dashed=shape in ('conceptual_frame','dashed_surrounding_band','dashed_area','catalogue_card','connection_symbol')
        fill='none' if shape in ('conceptual_frame','square_outline','dashed_surrounding_band') else '#fbfaf5' if n['kind']=='passage' else '#e9eee2'
        card=rect(g,x,y,w,h,fill,C['green'],1.6,3)
        if dashed:card.set('stroke-dasharray','8 6')
        label_text=n['label'];size=min(26,max(17,(w-16)/max(len(label_text),1)))
        if shape=='dashed_surrounding_band':
            text(g,x+w/2,y+h-15,label_text,size,C['muted'],'middle',500)
        elif container:
            text(g,x+15,y+size+13,label_text,size,C['muted'],weight=500)
        elif n['id']=='yn-tower':
            size=min(24,(w-20)/4)
            text(g,x+w/2,y+h/2-6,'九层木塔',size,C['ink'],'middle',500)
            text(g,x+w/2,y+h/2+size+9,'塔基',size,C['ink'],'middle',500)
        elif n.get('placement_mode')=='unlocated_catalogue':
            text(g,x+w/2,y+h*.32,'构成目录 · 不定位',20,C['gold'],'middle',500)
            text(g,x+w/2,y+h*.56,label_text,size,C['ink'],'middle',500)
            text(g,x+w/2,y+h*.78,'此卡片不表示寺内方位',17,C['muted'],'middle')
        else:text(g,x+w/2,y+h/2+size*.35,label_text,size,C['ink'],'middle',500)
    text(r,1680,220,'方位示意 · 北 ↑',21,C['green'],'end')
    guide=scene.get('rendering_guidance',[])
    if isinstance(guide,dict):guide=list(guide.values())
    if isinstance(guide,str):guide=[guide]
    notes={'changhe_gate_complex':'三条通道有图版依据；院区虚框仅供阅读。两翼连接画为基址联系，不推定为有顶廊。44.5 × 24.4 m只指主门基。',
        'yongning_compound':'塔北有佛殿，但两者的精确轴线与间距未定。北门不施屋；南门地面通道数不由“通三閣道／通三道”直接判定。僧房仅列非定位目录。',
        'yongning_pagoda_base':'中央塔心、周围构造和四向慢道来自图版。虚线环带不表示完整环廊；未补柱网数量、坡道尺寸或建筑高度。破坏沟没有画为盛时古渠。'}
    short=notes.get(scene['id'],'；'.join(str(v) for v in guide[:3]))
    para(r,65,1160,short or '按可核读关系组织；没有添加古代地理坐标、未记距离或屋顶。',76,22)
    text(r,65,1350,'来源关系与编辑画布分开保存；完整节点、出处与限制见 core-relations.json。',19,C['muted'])
    return r
