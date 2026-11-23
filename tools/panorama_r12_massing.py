#!/usr/bin/env python3
"""Illustrative elevation guide over the frozen R12 ground projection.

This is a precise DRAWING aid, not an archaeological upper-structure model.
Ground rings come from R11; vertical display units and all roof/body taper are
explicit artistic parameters.  They never enter the R11 data or projection.json.
"""
from pathlib import Path
import hashlib
import json
import math
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/panorama-r12'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    import cairosvg
    source = OUT / 'projection.json'
    data = json.loads(source.read_text())
    h = data['source_xy_m_to_canvas_homography']
    features = {f['id']: f for f in data['features']}
    def p3(p, z=0):
        x,y=p
        w=h[2][0]*x+h[2][1]*y+h[2][2]
        return [(h[0][0]*x+h[0][1]*y+h[0][2])/w,
                (h[1][0]*x+h[1][1]*y+h[1][2]-z)/w]
    def points(ps):
        return ' '.join(f'{x:.5f},{y:.5f}' for x,y in ps)
    chunks=[]
    layer_centres={}
    def poly(ps,fill,stroke='#454c4a',width=.45):
        chunks.append(f'<polygon points="{points(ps)}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round"/>')
    def line(ps,color='#677570',width=.6):
        chunks.append(f'<polyline points="{points(ps)}" fill="none" stroke="{color}" stroke-width="{width}"/>')
    def ring(ident):
        r=features[ident]['geometry']['coordinates'][0]
        return r[:-1] if r[0]==r[-1] else r
    def scaled(r,s):
        c=[sum(p[k] for p in r)/len(r) for k in (0,1)]
        return [[c[k]+s*(p[k]-c[k]) for k in (0,1)] for p in r]
    def prism(r,z0,z1):
        faces=[]
        for i,a in enumerate(r):
            b=r[(i+1)%len(r)]
            faces.append((sum(p3(p,z0)[1] for p in (a,b))/2,
                          [p3(a,z0),p3(b,z0),p3(b,z1),p3(a,z1)]))
        for index,(_,face) in enumerate(sorted(faces)):
            poly(face,['#c9c9c2','#e4e3d9','#d4d3ca','#f3f0e4'][index%4])
        poly([p3(p,z1) for p in r],'#edece3')
    def roof(r,z,height):
        # A generic display-only roof; never treated as a recovered footprint.
        if len(r)!=4:
            poly([p3(p,z) for p in r],'#5c6563'); return
        west=[(r[0][k]+r[3][k])/2 for k in (0,1)]
        east=[(r[1][k]+r[2][k])/2 for k in (0,1)]
        rw=[west[k]*.75+east[k]*.25 for k in (0,1)]
        re=[west[k]*.25+east[k]*.75 for k in (0,1)]
        base=[p3(p,z) for p in r]
        a,b=p3(rw,z+height),p3(re,z+height)
        poly([base[0],base[1],b,a],'#9ca6a2')
        poly([base[3],base[0],a],'#6f7c77')
        poly([base[1],base[2],b],'#87938f')
        poly([base[2],base[3],a,b],'#56635e')
    def stacked(ident,n,storey,base_scale,taper,roof_rise):
        r=ring(ident)
        centre=[sum(p[k] for p in r)/len(r) for k in (0,1)]
        layer_centres[ident]=[]
        poly([p3(p) for p in r],'#ddd5c5','#6a6b63',.55)
        z=0
        for level in range(n):
            s=base_scale*(1-taper*level)
            body=scaled(r,s)
            layer_centres[ident].append(p3(centre,z+storey/2))
            prism(body,z,z+storey)
            roof(scaled(r,s*1.15),z+storey,roof_rise)
            z+=storey+roof_rise*.55
        return z, r

    # Known source walls remain disconnected at their recorded gaps.
    ground_xml=ET.fromstring((OUT/'projection-clean.svg').read_text())
    ns='{http://www.w3.org/2000/svg}'
    ground=''.join(ET.tostring(c,encoding='unicode') for c in ground_xml if c.tag not in {ns+'title',ns+'desc'})
    # Far palace footprint references. Upper blocks are expressly not evidence.
    stacked('r11-taiji-scale',1,13,.82,0,4)
    stacked('r11-changhe-gate-main-base',1,7,.82,0,2.5)
    # Temple is rendered in ground-depth order: rear hall, tower, front gate.
    stacked('r11-yongning-YN11-BUDDHA-HALL',1,8,.86,0,3)
    tower_top,tower_ring=stacked('r11-yongning-YN11-TOWER-PLINTH',9,6.2,.82,.057,2.0)
    c=[sum(p[k] for p in tower_ring)/len(tower_ring) for k in (0,1)]
    line([p3(c,tower_top+1),p3(c,tower_top+10)],'#56635e',.9)
    stacked('r11-yongning-YN11-GATE-S',3,2.0,.87,.025,.8)
    mass=''.join(chunks)
    description='Ground uses the unchanged R12 homography. Nine tower storeys and three south-gate storeys are a counting aid. All heights, roofs, taper and upper forms are artistic display parameters, not archaeological measurements.'
    def svg(width,height,body):
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><title>R12 illustrative massing guide</title><desc>{description}</desc><rect width="100%" height="100%" fill="#faf9f5"/>{body}</svg>'
    overview=svg(1672,941,ground+mass)
    detail=svg(1600,1100,f'<g transform="translate(-1830 -1450) scale(5.2)">{ground}{mass}</g>')
    counts=[]
    for ident,label,offset in [('r11-yongning-YN11-TOWER-PLINTH','塔',32),('r11-yongning-YN11-GATE-S','门',42)]:
        for index,(u,v) in enumerate(layer_centres[ident],1):
            x,y=u*5.2-1830,v*5.2-1450
            tx=(u+offset)*5.2-1830
            counts.append(f'<path d="M{x+35:.3f},{y:.3f}H{tx-8:.3f}" stroke="#8a8a80" stroke-width="1" fill="none"/><text x="{tx:.3f}" y="{y+4:.3f}" font-size="12" font-family="Noto Sans CJK SC,sans-serif" fill="#33453e">{label}{index}</text>')
    counted=svg(1600,1100,f'<g transform="translate(-1830 -1450) scale(5.2)">{ground}{mass}</g>'+''.join(counts)+'<text x="40" y="45" font-size="25" font-family="Noto Sans CJK SC,sans-serif" fill="#33453e">九层塔与三层门：楼层表达占位，高度与屋顶未定</text><text x="40" y="78" font-size="19" font-family="Noto Sans CJK SC,sans-serif" fill="#33453e">高度、收分及屋顶均为绘图参数，非考古立面复原</text>')
    for name,content,scale in [('massing-overview-clean',overview,2),('massing-yongning-clean',detail,1),('massing-yongning-counted',counted,1)]:
        sp=OUT/(name+'.svg');sp.write_text(content)
        root=ET.fromstring(content)
        cairosvg.svg2png(bytestring=content.encode(),write_to=str(OUT/(name+'.png')),
                        output_width=int(root.attrib['width'])*scale,output_height=int(root.attrib['height'])*scale)
    audit={
        'schema':'luoyang-r12-illustrative-massing-v1',
        'ground_projection_path':'research/panorama-r12/projection.json',
        'ground_projection_sha256':sha(source),
        'ground_matrix':h,
        'z0_uses_frozen_ground_projection':True,
        'third_coordinate_role':'artistic_display_units_not_metres',
        'projection_extension':'u=(H_row0 dot [x,y,1])/w; v=((H_row1 dot [x,y,1])-z_display)/w',
        'algorithm_reference':{
            'path':'tools/panorama_r12_massing.py',
            'sha256':sha(Path(__file__)),
            'role':'This JSON records the principal display parameters. The complete drawing algorithm is the source code locked by this SHA256; neither is an archaeological upper-structure model.'},
        'display_transforms':{
            'overview':{'vector_canvas_px':[1672,941],'png_render_scale':2,'png_canvas_px':[3344,1882]},
            'yongning_detail':{
                'canvas_px':[1600,1100],
                'after_ground_and_display_height_projection':[[5.2,0,-1830],[0,5.2,-1450],[0,0,1]],
                'svg_transform':'translate(-1830 -1450) scale(5.2)',
                'role':'Uniform enlargement of the same assembly for counting; never an independent temple placement or scale.'}},
        'shared_display_parameters':{
            'body_scale_formula':'base_scale * (1 - linear_taper_per_level * zero_based_level)',
            'scale_centre':'arithmetic mean of source ring vertices, excluding the repeated closing point',
            'roof_eave_scale_relative_to_body':1.15,
            'floor_advance_formula':'floor_units + roof_rise_units * 0.55',
            'roof_rise_floor_advance_factor':.55,
            'roof_ridge_interpolation_weights':[[.75,.25],[.25,.75]],
            'tower_finial_start_offset_above_stack_units':1,
            'tower_finial_end_offset_above_stack_units':10},
        'tower_storeys':9,'south_gate_storeys':3,
        'storey_reference':'research/city-spatial-r9/panorama-candidate-review.json /checks/0 and /checks/2; these preserve the prior reviewed visual typology, not a new elevation measurement.',
        'display_parameters':{
            'tower':{'floor_units':6.2,'roof_rise_units':2.0,'body_scale_inside_plinth':.82,'linear_taper_per_level':.057,'finial_units':10},
            'south_gate':{'floor_units':2.0,'roof_rise_units':.8,'body_scale_inside_foundation':.87,'linear_taper_per_level':.025},
            'buddha_hall':{'floor_units':8,'roof_rise_units':3,'body_scale_inside_published_frame':.86},
            'taiji':{'floor_units':13,'roof_rise_units':4,'body_scale_inside_scale_patch':.82},
            'changhe':{'floor_units':7,'roof_rise_units':2.5,'body_scale_inside_source_base':.82}},
        'source_inputs_sha256':dict(data['source_inputs_sha256']),
        'upper_structure_source_roles':{
            ident:{'ground_geometry_role':features[ident]['geometry_role'],
                   'ground_placement_status':features[ident]['placement_status'],
                   'upper_structure_role':'artistic_display_placeholder_only'}
            for ident in ['r11-taiji-scale','r11-changhe-gate-main-base',
                          'r11-yongning-YN11-BUDDHA-HALL','r11-yongning-YN11-TOWER-PLINTH',
                          'r11-yongning-YN11-GATE-S']},
        'source_r11_geometry_modified':False,
        'illustrative_layer_centres_px':layer_centres,
        'new_verified_building_heights':0,'new_ancient_coordinates':0,'field_registration_verified':False,
        'not_historical_reconstruction':True,
        'limits':['Only ground rings have the cited source roles. No upper-storey footprint, height, roof or taper is claimed as excavated.',
                  'Scale patches remain approximate scale patches, not measured complete building footprints.',
                  'The Taiji block is an artistic placeholder over a scale_template, and the Buddha-hall block is an artistic placeholder over a published_site_box; neither block is a recovered upper structure.',
                  'No additional temple wall, north gate, cloister or symmetric corner tower is generated.',
                  'The 2x overview PNG only increases display resolution; the 1672x941 vector frame and H remain unchanged.',
                  'The 5.2x detail is a display enlargement of the same assembly; it must not be pasted into the city at enlarged size.'],
        'outputs_sha256':{p.name:sha(p) for p in OUT.glob('massing-*') if p.suffix in ['.svg','.png']},
    }
    src=ROOT/'research/city-spatial-r9/panorama-candidate-review.json'
    audit['source_inputs_sha256']['research/city-spatial-r9/panorama-candidate-review.json']=sha(src)
    for path in [Path(__file__),source,OUT/'projection-clean.svg']:
        audit['source_inputs_sha256'][str(path.resolve().relative_to(ROOT))]=sha(path)
    (OUT/'massing-display-parameters.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'outputs':audit['outputs_sha256'],'ground_projection_sha256':audit['ground_projection_sha256'],'new_verified_heights':0}))

if __name__=='__main__':
    main()
