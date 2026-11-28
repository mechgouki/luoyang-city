#!/usr/bin/env python3
"""V6's declared architecture as a native, transparent 2.5D SVG scene.

This is code-native illustration, not editing, tracing or compositing a PNG.
Only tower-layer.svg and tower-projection.json are written by the default run.
The V6 source JSON supplies every floor datum, body width and principal height.
The affine camera is a display choice for V12, not historical registration.

    python draw_tower_scene.py
    python draw_tower_scene.py --preview /tmp/tower-preview.png

--preview uses Sharp/librsvg to rasterize a magnified SVG viewport on a neutral
warm background.  It does not read or modify any bitmap. The deliverable SVG
has a transparent 1672 x 941 canvas and contains no embedded background image.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "yongning-structure-colour-v6-20261128/design-parameters.json"
ALGORITHM_SOURCE = SOURCE.with_name("draw_scaled_elevation.py")
CANVAS = (1672, 941)
P = json.loads(SOURCE.read_text(encoding="utf-8"))

# X=east/right, Y=north/back, Z=up, in the V6 scenario's local model metres.
# Translation is solved from the front midpoint of the 38.2 m plinth.
A, B, C, D, E = 1.32, 0.10, 0.03, -0.42, -1.30
FRONT_TARGET = (516.0, 403.0)
BASE_HALF = P["base_width_m"] / 2
OX = FRONT_TARGET[0] - B * -BASE_HALF
OY = FRONT_TARGET[1] - D * -BASE_HALF

parts: list[str] = []
geometry: list[dict] = []


def num(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def project(q: tuple[float, float, float]) -> tuple[float, float]:
    x, y, z = q
    return OX + A*x + B*y, OY + C*x + D*y + E*z


def screen(q) -> list[float]:
    return [round(v, 6) for v in project(q)]


def xy(q) -> str:
    return ",".join(num(v) for v in project(q))


def path(d: str, fill="none", stroke="none", sw=.15, opacity=1.0,
         extra="") -> None:
    parts.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" '
                 f'stroke-width="{num(sw)}" opacity="{num(opacity)}" '
                 f'stroke-linecap="round" stroke-linejoin="round" {extra}/>')


def poly(points, fill, stroke="none", sw=.15, opacity=1.0) -> None:
    path("M" + "L".join(xy(q) for q in points) + "Z",
         fill, stroke, sw, opacity)


def line(q1, q2, color, sw=.18, opacity=1.0) -> None:
    path("M"+xy(q1)+"L"+xy(q2), stroke=color, sw=sw, opacity=opacity)


def group(identifier: str, kind: str | None = None, **attrs) -> None:
    tail = f' data-kind="{kind}"' if kind else ""
    tail += "".join(f' {k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    parts.append(f'<g id="{identifier}"{tail}>')


def end() -> None:
    parts.append("</g>")


def front_quad(x1, x2, y, z1, z2):
    return [(x1,y,z1),(x2,y,z1),(x2,y,z2),(x1,y,z2)]


def right_quad(x, y1, y2, z1, z2):
    return [(x,y1,z1),(x,y2,z1),(x,y2,z2),(x,y1,z2)]


def ring(half, z):
    return [(-half,-half,z),(half,-half,z),(half,half,z),(-half,half,z)]


def roof_outer_z(eave, u):
    # Restrained upturn: exact central eave datum retained; all curvature is
    # explicitly illustrative, never an excavated roof section.
    return eave + .175 + .375*u*u


def roof_face(oh, rh, eave, peak, face):
    def q(u, half, z):
        if face == "front": return (u*half,-half,z)
        if face == "right": return (half,u*half,z)
        if face == "back": return (-u*half,half,z)
        return (-half,-u*half,z)
    a=q(-1,oh,eave+.55); b=q(1,oh,eave+.55)
    c=q(1,rh,peak); d=q(-1,rh,peak); middle=q(0,oh,eave-.20)
    dpath=f'M{xy(a)}Q{xy(middle)} {xy(b)}L{xy(c)}L{xy(d)}Z'
    polyfill=f'url(#yn15-roof-{face})'
    path(dpath, polyfill, "#6b6e5d", .075)
    # Tile runs follow the roof slope, instead of screen-vertical hatching.
    count=35 if face == "front" else 23
    for k in range(1,count):
        u=-1+2*k/count
        outer=q(u,oh,roof_outer_z(eave,u)); inner=q(u,rh,peak)
        ctrl=tuple(inner[j]*.36+outer[j]*.64 for j in range(3))
        ctrl=(ctrl[0],ctrl[1],ctrl[2]-.34)
        color="#c6c0a1" if k%3 else "#293f39"
        path(f'M{xy(inner)}Q{xy(ctrl)} {xy(outer)}',stroke=color,
             sw=.11 if k%3 else .09, opacity=.29 if k%3 else .20)
    # Three very quiet tile courses avoid a smooth plastic roof face.
    for f in [.28,.55,.80]:
        h=rh*(1-f)+oh*f
        zz=peak*(1-f)+(eave+.175)*f-.25*math.sin(math.pi*f)
        path(f'M{xy(q(-1,h,zz+.30*f))}Q{xy(q(0,h,zz-.09))} '
             f'{xy(q(1,h,zz+.30*f))}',stroke="#b0af94",sw=.075,opacity=.17)


def bell(x, y, z):
    sx,sy=project((x,y,z))
    path(f'M{num(sx)},{num(sy)}v.55',stroke="#96824d",sw=.13)
    path(f'M{num(sx-.25)},{num(sy+.50)}q.25,-.32 .50,0l.10,.44h-.70Z',
         "url(#yn15-gold)","#8d7442",.065,.85)


def draw_roof(i, bw, eave, peak):
    group(f"roof-{i:02d}","main-roof",data_main_roof=i)
    oh=(bw+2*P["eaves_overhang_per_side_m_assumed"])/2
    rh=bw*.72/2 if i<9 else 2.0
    # Far surfaces first, then front; the next storey's body provides occlusion.
    for face in ["back","left","right","front"]:
        roof_face(oh,rh,eave,peak,face)
    poly(ring(rh,peak),"#67715f",opacity=.95)
    for side in ["front","right"]:
        if side=="front":
            p1=(-oh,-oh,eave+.55); p2=(oh,-oh,eave+.55); mid=(0,-oh,eave-.20)
        else:
            p1=(oh,-oh,eave+.55); p2=(oh,oh,eave+.55); mid=(oh,0,eave-.20)
        # Soft brown under-eave and a very fine warm arris, without black outline.
        lowered=lambda q:(q[0],q[1],q[2]-.24)
        path(f'M{xy(lowered(p1))}Q{xy(lowered(mid))} {xy(lowered(p2))}',
             stroke="#574d38",sw=.48,opacity=.72)
        path(f'M{xy(p1)}Q{xy(mid)} {xy(p2)}',stroke="#c4b18b",sw=.17,opacity=.8)
    # Visible hip seams and corner bells remain understated at panorama scale.
    for sx,sy in [(-1,-1),(1,-1),(1,1)]:
        line((sx*rh,sy*rh,peak),(sx*oh,sy*oh,eave+.55),"#b0ac8f",.16,.63)
        bell(sx*oh,sy*oh,eave+.35)
    end()
    return {"id":f"roof-{i:02d}","eave_datum_m":eave,"peak_m":peak,
            "outer_width_m":2*oh,"inner_ridge_width_m":2*rh,
            "outer_corner_screen_px":[screen(q) for q in ring(oh,eave+.55)],
            "front_eave_mid_screen_px":screen((0,-oh,eave+.175)),
            "peak_axis_screen_px":screen((0,0,peak))}


def draw_wall_face(bw,z,wall,side,ground):
    h=bw/2; span=bw/9
    def q(u,zz): return (u,-h,zz) if side=="front" else (h,u,zz)
    corners=[q(-h,z),q(h,z),q(h,z+wall),q(-h,z+wall)]
    color=("url(#yn15-ground-front)" if ground else "url(#yn15-upper-front)")
    if side=="right": color="url(#yn15-ground-right)" if ground else "url(#yn15-upper-right)"
    poly(corners,color)
    for b in range(9):
        mid=-h+(b+.5)*span; fw=span*.72
        isdoor=3<=b<=5
        bottom=z+(.10 if isdoor else wall*.32); top=z+wall*.83
        aperture=[q(mid-fw/2,bottom),q(mid+fw/2,bottom),q(mid+fw/2,top),q(mid-fw/2,top)]
        poly(aperture,"url(#yn15-door)" if isdoor else "url(#yn15-window)","#8c573b",.10)
        line(q(mid-fw/2,top),q(mid+fw/2,top),"#553f2d",.23,.66)
        if isdoor:
            line(q(mid,bottom),q(mid,top),"#d29a62",.12,.73)
            for k in [-1,1]:
                cx,cy=project(q(mid+k*.11,z+wall*.38))
                parts.append(f'<circle cx="{num(cx)}" cy="{num(cy)}" r=".095" fill="#bda25a"/>')
        else:
            for k in range(1,5):
                u=mid-fw/2+fw*k/5
                line(q(u,bottom),q(u,top),"#ad7854",.10,.77)
            line(q(mid-fw/2,(bottom+top)/2),q(mid+fw/2,(bottom+top)/2),"#a97350",.11,.72)
        # Sparse grain is native SVG linework, deterministic and not a bitmap.
        if side=="front":
            u=mid-fw*.49
            line(q(u,z+.18),q(u,z+wall*.23),"#d7b58a",.085,.28)
    for b in range(10):
        u=-h+b*span; width=.46
        poly([q(u-width/2,z),q(u+width/2,z),q(u+width/2,z+wall),q(u-width/2,z+wall)],
             "url(#yn15-post-front)" if side=="front" else "#765039")
        if side=="front":line(q(u-width*.23,z+.05),q(u-width*.23,z+wall-.05),"#d49762",.10,.62)
    for zz in [z+.04,z+wall*.86,z+wall]:
        poly([q(-h,zz-.10),q(h,zz-.10),q(h,zz+.10),q(-h,zz+.10)],"#925739")
        line(q(-h,zz+.12),q(h,zz+.12),"#c28e60",.12,.59)


def draw_brackets(bw,z,wall,bracket):
    h=bw/2
    # The band is a shadow and repeated arm glyphs, not a Song/Qing order claim.
    poly(front_quad(-h,h,-h,z+wall,z+wall+bracket),"#65503a",opacity=.29)
    poly(right_quad(h,-h,h,z+wall,z+wall+bracket),"#4f4332",opacity=.33)
    for b in range(10):
        x=-h+b*bw/9
        for k in range(3):
            zz=z+wall+bracket*(k+.35)/3; arm=.34+.22*k
            y=-h-.12*k
            line((x-arm,y,zz),(x+arm,y,zz),"#6d4932",.24,.90)
            line((x-arm,y,zz+.10),(x+arm,y,zz+.10),"#b3875b",.10,.70)
        line((x,-h,z+wall),(x,-h-.25,z+wall+bracket),"#795037",.23,.85)
    for b in range(10):
        yy=-h+b*bw/9
        for k in range(3):
            zz=z+wall+bracket*(k+.35)/3; arm=.34+.22*k
            line((h+.08*k,yy-arm,zz),(h+.08*k,yy+arm,zz),"#6e4b35",.19,.87)


def draw_floor(i,bw,z,wall,bracket):
    group(f"floor-{i:02d}","wall-storey",data_occupied_storey=i,
          data_floor_z_m=num(z),data_body_width_m=num(bw))
    h=bw/2
    if i>1:
        hh=h+.35
        poly(right_quad(hh,-hh,hh,z-1.35,z+.1),"#73523b")
        poly(front_quad(-hh,hh,-hh,z-1.35,z+.1),"url(#yn15-floor-band)")
        line((-hh,-hh,z-.65),(hh,-hh,z-.65),"#c3976a",.17,.62)
    draw_wall_face(bw,z,wall,"right",i==1)
    draw_wall_face(bw,z,wall,"front",i==1)
    draw_brackets(bw,z,wall,bracket)
    end()
    return {"id":f"floor-{i:02d}","floor_datum_m":z,"body_width_m":bw,
            "wall_height_m":wall,"bracket_band_height_m":bracket,
            "front_wall_screen_px":[screen(q) for q in front_quad(-h,h,-h,z,z+wall)],
            "right_wall_screen_px":[screen(q) for q in right_quad(h,-h,h,z,z+wall)],
            "front_wall_mid_screen_px":screen((0,-h,z+wall/2)),
            "front_visible_wall_height_before_occlusion_px":-E*wall,
            "front_bays":9,"front_door_bays":3,"front_window_bays":6}


def draw_balcony(i,bw,z):
    group(f"balcony-{i:02d}","external-balcony",data_upper_storey=i)
    h=bw/2; g=h+1.4; deck=z+.20
    # Only external strips: no opaque deck painted across the wall interiors.
    poly([(-g,-g,deck),(g,-g,deck),(g,-h,deck),(-g,-h,deck)],"#a67950")
    poly([(h,-h,deck),(g,-h,deck),(g,g,deck),(h,g,deck)],"#7f5d3e")
    poly(front_quad(-g,g,-g,z-.38,deck),"#935c3c")
    poly(right_quad(g,-g,g,z-.38,deck),"#755039")
    line((-g,-g,deck),(g,-g,deck),"#d0a172",.21,.91)
    for side in ["front","right"]:
        def q(u,zz):return (u,-g,zz) if side=="front" else (g,u,zz)
        for zz,sw in [(z+.48,.22),(z+.90,.16),(z+1.70,.25)]:
            line(q(-g,zz),q(g,zz),"#995d3e" if side=="front" else "#785039",sw)
            if side=="front":line(q(-g,zz+.08),q(g,zz+.08),"#d5a372",.09,.80)
        for k in range(19):
            u=-g+2*g*k/18
            line(q(u,z+.4),q(u,z+1.74),"#9b6442" if side=="front" else "#78533a",.20)
    end()
    return {"id":f"balcony-{i:02d}","floor_datum_m":z,"outer_width_m":2*g,
            "rail_top_m":z+1.7,"front_rail_endpoints_px":[screen((-g,-g,z+1.7)),screen((g,-g,z+1.7))]}


def draw_base():
    group("tower-ground-contact","contact-shadow")
    sx,sy=project((0,-9,0))
    parts.append(f'<ellipse cx="{num(sx+1)}" cy="{num(sy+1.1)}" rx="28" ry="5.4" '
                 'fill="#594c37" opacity=".13" filter="url(#yn15-contact-soften)"/>')
    end()
    group("tower-plinth","plinth")
    h=BASE_HALF; zh=P["base_height_m"]
    poly(ring(h,zh),"url(#yn15-stone-top)","#a89879",.11)
    poly(right_quad(h,-h,h,0,zh),"#998b70", "#8e8169",.09)
    poly(front_quad(-h,h,-h,0,zh),"url(#yn15-stone-front)","#a08d71",.10)
    for zz in [zh/3,zh*2/3]:
        line((-h,-h,zz),(h,-h,zz),"#8b806a",.10,.42)
        line((h,-h,zz),(h,h,zz),"#807863",.10,.34)
    for row in range(3):
        for j in range(8):
            xx=-h+(j+.5*(row%2))*h/4
            if -h<xx<h:line((xx,-h,row*zh/3),(xx,-h,(row+1)*zh/3),"#8c826b",.09,.39)
    line((-h,-h,zh),(h,-h,zh),"#d3c2a0",.22,.93)
    line((h,-h,zh),(h,h,zh),"#c1b390",.16,.72)
    # Inset step glyphs preserve the front midpoint; no invented external ramp.
    sw=P["front_access_width_m_illustrative"]/2
    poly(front_quad(-sw,sw,-h-.006,0,zh),"#b0a48b")
    for k in range(1,7):
        line((-sw,-h-.008,zh*k/7),(sw,-h-.008,zh*k/7),"#7e7964",.10,.62)
    end()


def draw_chains(front=True):
    h=(P["body_widths_m_assumed"][-1]+2*P["eaves_overhang_per_side_m_assumed"])/2
    yy=-h if front else h
    group("finial-chains-front" if front else "finial-chains-rear","iron-chain-detail")
    for sign in [-1,1]:
        start=(0,0,144.7); finish=(sign*h,yy,123.3)
        ctrl=(sign*h*.52,yy*.52,132.7)
        path(f'M{xy(start)}Q{xy(ctrl)} {xy(finish)}',stroke="#655f4e",sw=.12,opacity=.70 if front else .45)
    end()


def draw_finial():
    datum=P["lower_edge_of_gold_discs_height_m_assumed"]
    peak=P["ninth_roof_peak_height_m_assumed"]
    group("finial-pedestal","finial-support")
    poly(right_quad(1.5,-1.5,1.5,peak,datum),"#97763a",sw=.08)
    poly(front_quad(-1.5,1.5,-1.5,peak,datum),"url(#yn15-gold)","#97783d",.08)
    poly(ring(1.5,datum),"#d3b76d",sw=.08)
    line((0,0,peak),(0,0,145.7),"#a48743",.43)
    line((-.08,0,datum),( -.08,0,145.4),"#e1c77b",.12,.77)
    end()
    discs=[]
    for i in range(P["gold_discs_chosen"]):
        z=datum+.4+i*.82; radius=1.9-i*.095
        cx,cy=project((0,0,z)); rx=radius*A
        # V6 itself uses a thin ellipse glyph, rather than a surveyed 3D disk.
        # Keep its readable separation at this illustration's smaller scale.
        ry=1.8*abs(E)/8.35
        group(f"disc-{i+1:02d}","gold-disc",data_gold_disc=i+1,data_z_m=num(z))
        parts.append(f'<ellipse cx="{num(cx)}" cy="{num(cy)}" rx="{num(rx)}" ry="{num(ry)}" '
                     'fill="url(#yn15-gold)" stroke="#8a713b" stroke-width=".09"/>')
        path(f'M{num(cx-rx*.85)},{num(cy-.07)}Q{num(cx)},{num(cy-ry*.91)} {num(cx+rx*.85)},{num(cy-.07)}',
             stroke="#e7cc81",sw=.10,opacity=.89)
        end()
        discs.append({"id":f"disc-{i+1:02d}","z_m":z,"radius_m_assumed":radius,
                      "screen_centre_px":[round(cx,6),round(cy,6)],"screen_rx_px":rx,"screen_ry_px":ry})
    group("finial-vase","finial-top")
    path(f'M{xy((-.25,0,144.4))}Q{xy((-1.3,0,145.3))} {xy((0,0,P["total_height_m_assumed"]))}'
         f'Q{xy((1.3,0,145.3))} {xy((.25,0,144.4))}Z',
         "url(#yn15-gold)","#96773a",.10)
    path(f'M{xy((-.12,0,144.6))}Q{xy((-.48,0,145.5))} {xy((0,0,146.7))}',
         stroke="#edd68f",sw=.14,opacity=.82)
    end()
    draw_chains(front=True)
    return discs


DEFS = '''<defs>
 <linearGradient id="yn15-roof-front" x1="0" y1="0" x2=".15" y2="1"><stop stop-color="#7b7d78"/><stop offset=".55" stop-color="#6c706c"/><stop offset="1" stop-color="#565d59"/></linearGradient>
 <linearGradient id="yn15-roof-right" x1="0" y1="0" x2="1" y2=".7"><stop stop-color="#636762"/><stop offset="1" stop-color="#525955"/></linearGradient>
 <linearGradient id="yn15-roof-left" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#8b877b"/><stop offset="1" stop-color="#6d706a"/></linearGradient>
 <linearGradient id="yn15-roof-back" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#6e726c"/><stop offset="1" stop-color="#60645e"/></linearGradient>
 <linearGradient id="yn15-upper-front" x1="0" y1="0" x2=".1" y2="1"><stop stop-color="#b7ad8e"/><stop offset=".22" stop-color="#dfcfab"/><stop offset="1" stop-color="#cbbb96"/></linearGradient>
 <linearGradient id="yn15-upper-right"><stop stop-color="#b8ae90"/><stop offset="1" stop-color="#a2997e"/></linearGradient>
 <linearGradient id="yn15-ground-front" x1="0" y1="0" x2=".15" y2="1"><stop stop-color="#98573c"/><stop offset=".2" stop-color="#b66645"/><stop offset="1" stop-color="#a75a3c"/></linearGradient>
 <linearGradient id="yn15-ground-right"><stop stop-color="#945538"/><stop offset="1" stop-color="#824d34"/></linearGradient>
 <linearGradient id="yn15-post-front"><stop stop-color="#ba7d50"/><stop offset=".25" stop-color="#aa6942"/><stop offset=".65" stop-color="#925235"/><stop offset="1" stop-color="#7b4b32"/></linearGradient>
 <linearGradient id="yn15-door"><stop stop-color="#8e4a32"/><stop offset=".35" stop-color="#aa5e3d"/><stop offset="1" stop-color="#88452e"/></linearGradient>
 <linearGradient id="yn15-window" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#41483c"/><stop offset="1" stop-color="#5b5946"/></linearGradient>
 <linearGradient id="yn15-floor-band" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#765039"/><stop offset=".45" stop-color="#a3784d"/><stop offset="1" stop-color="#76583d"/></linearGradient>
 <linearGradient id="yn15-stone-top" x1="0" y1="0" x2=".5" y2="1"><stop stop-color="#c8b99a"/><stop offset="1" stop-color="#b5a487"/></linearGradient>
 <linearGradient id="yn15-stone-front" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#c8b89a"/><stop offset="1" stop-color="#a8997e"/></linearGradient>
 <linearGradient id="yn15-gold"><stop stop-color="#8f7335"/><stop offset=".28" stop-color="#c2a151"/><stop offset=".47" stop-color="#dfc376"/><stop offset=".72" stop-color="#b99a4d"/><stop offset="1" stop-color="#96783b"/></linearGradient>
 <filter id="yn15-contact-soften" x="-30%" y="-100%" width="170%" height="300%"><feGaussianBlur stdDeviation=".75"/></filter>
</defs>'''


def build():
    assert P["storeys"]==9 and P["gold_discs_chosen"]==11
    assert len(P["body_widths_m_assumed"])==len(P["floor_datums_m_assumed"])==9
    parts.clear(); geometry.clear()
    parts.extend([f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS[0]}" height="{CANVAS[1]}" viewBox="0 0 {CANVAS[0]} {CANVAS[1]}" role="img" aria-labelledby="tower-title tower-desc">',
                  '<title id="tower-title">永宁寺九层塔：V6条件方案的2.5D构图投影</title>',
                  '<desc id="tower-desc">九个墙身层、九道主檐、八道上层外廊、十一金盘。层高与收分直接读取V6参数；画面投影不是历史相机配准、遗址实测或147米结构可建性证明。上层浅墙仍为未知原色的示意。透明背景，无嵌入位图。</desc>',DEFS])
    group("yongning-tower-v15","parametric-tower")
    draw_base(); draw_chains(front=False)
    for idx,(bw,z) in enumerate(zip(P["body_widths_m_assumed"],P["floor_datums_m_assumed"]),1):
        if idx<9:
            inc=P["first_eight_level_increments_m_assumed"][idx-1]
            wall=.62*inc; bracket=.11*inc; eave=z+wall+bracket; peak=z+inc-1.25
            assert math.isclose(z+inc,P["floor_datums_m_assumed"][idx],abs_tol=1e-10)
        else:
            wall=P["ninth_wall_height_m_assumed"]
            bracket=P["ninth_bracket_band_height_m_assumed"]
            eave=z+wall+bracket; peak=P["ninth_roof_peak_height_m_assumed"]
        f=draw_floor(idx,bw,z,wall,bracket)
        f["roof"]=draw_roof(idx,bw,eave,peak)
        f["balcony"]=draw_balcony(idx,bw,z) if idx>1 else None
        geometry.append(f)
    discs=draw_finial(); end(); parts.append("</svg>")
    svg="\n".join(parts)+"\n"
    tree=ET.fromstring(svg)
    kinds={key:sum(1 for el in tree.iter() if el.attrib.get("data-kind")==key)
           for key in ["wall-storey","main-roof","external-balcony","gold-disc"]}
    assert kinds=={"wall-storey":9,"main-roof":9,"external-balcony":8,"gold-disc":11}
    assert not any(el.tag.endswith("image") for el in tree.iter())
    assert screen((0,-BASE_HALF,0))==list(FRONT_TARGET)
    assert len({el.attrib["id"] for el in tree.iter() if "id" in el.attrib})==sum("id" in el.attrib for el in tree.iter())
    svg_path=ROOT/"tower-layer.svg";svg_path.write_text(svg,encoding="utf-8")
    result={
        "schema":"yongning-v15-native-svg-projection-v1","date":"2026-11-28",
        "status":"native_svg_candidate_for_visual_review_not_published_approval",
        "canvas_px":list(CANVAS),"transparent_background":True,"embedded_bitmap_count":0,
        "source_parameters_path":str(SOURCE.relative_to(ROOT.parent)),
        "source_parameters_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "source_height_algorithm_path":str(ALGORITHM_SOURCE.relative_to(ROOT.parent)),
        "source_height_algorithm_sha256":hashlib.sha256(ALGORITHM_SOURCE.read_bytes()).hexdigest(),
        "source_parameter_id":P["id"],
        "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "svg_sha256":hashlib.sha256(svg_path.read_bytes()).hexdigest(),
        "display_projection":{
            "kind":"affine_2_5D_artistic_display_not_historical_camera_registration",
            "model_axes":{"X":"right/east","Y":"back/north","Z":"up"},
            "formula":"u=origin_x+1.32X+0.10Y; v=origin_y+0.03X-0.42Y-1.30Z",
            "matrix_2x4":[[A,B,0,OX],[C,D,E,OY]],
            "translation_rule":"Set projected plinth front-edge midpoint (0,-base_width/2,0) exactly to (516,403).",
            "axis_ground_screen_px":screen((0,0,0)),
            "front_plinth_ground_midpoint_screen_px":screen((0,-BASE_HALF,0)),
            "front_plinth_top_midpoint_screen_px":screen((0,-BASE_HALF,P["base_height_m"])),
            "apex_screen_px":screen((0,0,P["total_height_m_assumed"])),
            "base_ground_corners_screen_px":[screen(q) for q in ring(BASE_HALF,0)],
            "base_top_corners_screen_px":[screen(q) for q in ring(BASE_HALF,P["base_height_m"])],
            "original_r12_frozen_H_used":False,"source_ground_homography_modified":False,
            "not_registration_to_archaeology_or_historic_camera":True},
        "exact_group_counts":kinds,"floors":geometry,"gold_discs":discs,
        "v6_parameters_preserved":{"base_width_m":P["base_width_m"],"base_height_m":P["base_height_m"],
            "total_height_m_assumed":P["total_height_m_assumed"],
            "floor_datums_m_assumed":P["floor_datums_m_assumed"],
            "body_widths_m_assumed":P["body_widths_m_assumed"],
            "eaves_overhang_per_side_m_assumed":P["eaves_overhang_per_side_m_assumed"]},
        "illustrative_detail_choices":{
            "visible_front":"nine bays; central three door bays and six window bays; upper assignment assumed",
            "right_side":"same bay rhythm projected on narrow side; not all bays distinguishable at native panorama size",
            "post_glyph_width_m":.46,"post_glyph_is_not_engineering_section":True,
            "roof_curvature":"V6 main eave and peak datums retained; small quadratic curvature is an illustration choice",
            "balcony_projection_per_side_m":1.4,"rail_height_above_floor_m":1.7,
            "disc_glyph_vertical_radius_px":1.8*abs(E)/8.35,
            "disc_depth_note":"Thin elliptical glyph scaled from V6's drawing; not measured disk geometry",
            "access_width_m":P["front_access_width_m_illustrative"],
            "access_depth":"inset step glyph only; no new external south ramp footprint inferred",
            "light":"warm afternoon front/left light; right faces quieter and darker",
            "wall_colours":"vermilion first-storey infill; pale warm-gray upper infill is an unverified display assumption",
            "texture":"native gradients and fine deterministic tile/wood lines; no raster texture"},
        "research_limits":[P["precise_values_warning"],P["engineering_warning"],P["colour"]["upper_light_infill"],
            "投影用于方案在艺术背景中的构图，不是历史相机配准或实测147m。",
            "SVG构件计数可精确核验；缩小后的每个细部是否可辨仍需实际成图审查。",
            "未嵌入背景、未宣布首页成图通过，未修改旧V12或R12/V14冻结底稿。"],
        "checks":{"nine_wall_groups":kinds["wall-storey"]==9,"nine_main_roof_groups":kinds["main-roof"]==9,
            "eight_balcony_groups":kinds["external-balcony"]==8,"eleven_disc_groups":kinds["gold-disc"]==11,
            "front_ground_midpoint_exact":screen((0,-BASE_HALF,0))==list(FRONT_TARGET),
            "no_embedded_bitmaps":True,"svg_ids_unique":True}}
    (ROOT/"tower-projection.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result


def render_preview(destination: Path):
    """Rasterize a native SVG viewport using Sharp; never load a PNG input."""
    node=os.environ.get("CODEX_PRIMARY_RUNTIME_NODE") or shutil.which("node")
    modules=os.environ.get("CODEX_PRIMARY_RUNTIME_NODE_MODULES")
    if not node:raise RuntimeError("Node is required only for --preview; SVG/JSON are already saved.")
    destination.parent.mkdir(parents=True,exist_ok=True)
    js=r'''const fs=require('fs');const path=require('path');
const sharp=require(process.argv[3]?path.join(process.argv[3],'sharp'):'sharp');
let svg=fs.readFileSync(process.argv[1],'utf8');
svg=svg.replace('width="1672" height="941" viewBox="0 0 1672 941"',
 'width="640" height="1720" viewBox="478 195 80 215"');
svg=svg.replace(/(<desc[^>]*>[\s\S]*?<\/desc>)/,'$1<rect x="478" y="195" width="80" height="215" fill="#c6b38e"/>');
sharp(Buffer.from(svg)).png().toFile(process.argv[2]).then(()=>console.log(process.argv[2]));'''
    subprocess.run([node,"-e",js,str(ROOT/"tower-layer.svg"),str(destination),modules or ""],check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview",type=Path,help="Optional scratch PNG rendered from a magnified native SVG viewport with Sharp.")
    args=parser.parse_args()
    result=build()
    print(json.dumps({"svg":str(ROOT/"tower-layer.svg"),"geometry":str(ROOT/"tower-projection.json"),
                      "counts":result["exact_group_counts"],"anchors":result["display_projection"]},ensure_ascii=False,indent=2))
    if args.preview:render_preview(args.preview)


if __name__=="__main__":main()
