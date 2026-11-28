"""V6: a metrically consistent height scale and evidence-labelled colour elevation.

Python only creates SVG primitives and parameters. Raster conversion is done with
Sharp/librsvg. This is a precise analytical diagram, not an image editing workflow.
"""
from pathlib import Path
from html import escape
import json

ROOT = Path(__file__).resolve().parent
SCALE = 8.35
GROUND_Y = 1500
CX = 400
W, H = 1280, 1800

params = {
    "id": "YONGNING-V6-SCALED-COLOUR-CONDITIONAL-147",
    "date": "2026-11-28",
    "status": "explicit_visual_reconstruction_scenario_not_measured_original",
    "storeys": 9,
    "base_width_m": 38.2,
    "base_height_m": 2.2,
    "base_source": "钱国祥2017，木塔基座含包壁宽约38.2米、高约2.2米",
    "chi_m_assumed": 0.273,
    "lower_edge_of_gold_discs_height_m_assumed": 49 * 10 * 0.273,
    "total_height_m_assumed": 147.0,
    "height_above_gold_disc_datum_m_assumed": 147.0 - 49 * 10 * 0.273,
    "height_endpoint_warning": "金露盘下不自动等于檐顶或完整塔身；147m不是文献直接数值。",
    "ground_floor_body_width_m_assumed": 29.4,
    "body_widths_m_assumed": [29.4, 28.5, 27.5, 26.4, 25.2, 24.0, 22.8, 21.6, 20.4],
    "first_eight_level_increments_m_assumed": [19.0, 17.0, 15.5, 14.0, 12.8, 11.8, 10.8, 9.8],
    "ninth_wall_height_m_assumed": 8.0,
    "ninth_bracket_band_height_m_assumed": 1.8,
    "ninth_roof_peak_height_m_assumed": 131.8,
    "eaves_overhang_per_side_m_assumed": 4.4,
    "bays_per_front_elevation": [9] * 9,
    "upper_bays_warning": "初层九间得到文献与柱网研究支持；上层沿用九间属于本案简化假设。",
    "gold_discs_chosen": 11,
    "gold_discs_variant": "周祖谟校释取十一；范祥雍校注正文保留三十并列十一异文。",
    "exterior_balconies": "八道上层木构平坐，类型学复原，并非遗址实测上部",
    "earth_core": "基部19.8m、残高约3.7m有考古依据；不指定原塔心终止层，不绘完整确定剖面。",
    "precise_values_warning": "层高、收分、出檐和上层开间数仅供本次可复算绘图；小数不代表历史精度。",
    "engineering_warning": "已作参数化力学筛查；原材、节点、塔心连接与地基未定，整体可行性尚未确立。不是施工图。",
    "scale_scope": "垂直标高与外轮廓参数按比例；构件笔画不是柱截面，栏杆与斗栱细部为示意。",
    "front_access_width_m_illustrative": 4.5,
    "access_warning": "4.5m参考钱国祥2017东侧踏道宽；正立面踏道仅示意，不宣称南道实测。",
    "height_progression_warning": "前八个层间递减；顶层墙身及完整攒尖屋面另行分配，不宣称九层墙身严格单调。",
    "colour": {
        "ground_outer_plaster": "朱色：钱国祥2017初层前檐墙外皮涂朱；屏幕红色色值仅显示选择",
        "doors": "朱漆：洛阳伽蓝记；户皆/并皆异文不改变门扇朱漆",
        "window_frames": "本案取红窗构，与并皆朱漆的版本相容；户皆版本不能单独证窗色",
        "upper_light_infill": "浅暖灰为未知表面占位示意，不声称塔上层原为白墙",
        "roof": "钱国祥等2010永宁寺出土板/筒瓦可支持青灰、黑灰色域；非琉璃釉色复原",
        "finial": "文本金瓶/金盘/金铎支持金色饰面；纯金、鎏金、包金工艺与质量未定",
        "iron_chains": "文本铁锁；暗铁色为材质显示，不是实测腐蚀/涂层",
        "posts_brackets": "红褐显示并保留彩饰存在的文字依据；具体纹样和各构件配色未定"
    },
}

def X(m): return CX + m * SCALE
def Y(m): return GROUND_Y - m * SCALE
parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
'''<defs>
<pattern id="earth" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M0 10L10 0" stroke="#d6c7ac" stroke-width="1"/></pattern>
<style>text{font-family:"Noto Sans CJK SC","Noto Sans CJK JP",sans-serif;fill:#273b38}.title{font-size:42px;font-weight:600}.subtitle{font-size:21px;fill:#63706a}.label{font-size:20px}.small{font-size:17px;fill:#65706a}.note{font-size:21px}.section{font-size:23px;font-weight:600;fill:#8a4d33}</style>
</defs>''',
'<rect width="1280" height="1800" fill="#faf8f2"/>']

def path(d, fill='none', stroke='#514b3f', sw=1.5, extra=''):
    parts.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')
def rect(x,y,w,h,fill,stroke='none',sw=1):
    parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def line(x1,y1,x2,y2,color='#9a9e95',sw=1,extra=''):
    path(f'M{x1:.2f},{y1:.2f}L{x2:.2f},{y2:.2f}',stroke=color,sw=sw,extra=extra)
def text(x,y,t,cls='label',anchor='start'):
    parts.append(f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{escape(t)}</text>')
def note(y,title,lines):
    text(760,y,title,'section')
    for i,t in enumerate(lines): text(760,y+36+i*33,t,'note')

text(65,78,'永宁寺塔 V6 · 标高与色彩','title')
text(65,120,'正投影立面｜147 m 条件方案｜室外地面为 ±0.00','subtitle')
text(65,154,'九层方形木塔 · 2026.11.28 · 高度可复算，原高未定','small')
line(65,180,1215,180,'#d8d6ca')

# Base and scale: the two archaeological dimensions are kept distinct from the
# dimensions of the independently traced temple plan.
rect(X(-19.1),Y(2.2),38.2*SCALE,2.2*SCALE,'#c6c8bd','#78867c')
line(95,GROUND_Y,675,GROUND_Y,'#6c776c',1.6)
path(f'M{X(-2.25)},{Y(2.2)}L{X(2.25)},{Y(2.2)}L{X(2.25)},{Y(0)}L{X(-2.25)},{Y(0)}Z','#c7c9bd','#7c897f')
for i in range(1,7):
    yy=Y(2.2-2.2*i/7); dx=2.25
    line(X(-dx),yy,X(dx),yy,'#929b90',.8)

floor_levels=[]
z=2.2
widths=params['body_widths_m_assumed']
for i, bw in enumerate(widths):
    floor_levels.append(z)
    if i < 8:
        inc=params['first_eight_level_increments_m_assumed'][i]
        wall=inc*.62
        bracket=inc*.11
        eave=z+wall+bracket
        peak=z+inc-1.25
    else:
        wall=8.0; bracket=1.8; eave=z+wall+bracket
        peak=131.8
    left=X(-bw/2); right=X(bw/2); span=bw/9
    if i > 0:
        # A continuous timber floor band joins the previous roof and the next
        # balcony. It must not leave the visible wall tiers floating in space.
        rect(X(-bw/2-.35),Y(z+.1),(bw+.7)*SCALE,1.45*SCALE,'#85543c','#634a36',.8)
        line(X(-bw/2-.35),Y(z-.65),X(bw/2+.35),Y(z-.65),'#b68157',1.2)
    # Light wall panels, red posts, three central door bays. This carries a clear
    # design decision for upper floors, rather than claiming excavated openings.
    rect(left,Y(z+wall),bw*SCALE,wall*SCALE,'#b44a3b' if i==0 else '#ddd8cc','#916148',1.1)
    for b in range(9):
        mid=-bw/2+(b+.5)*span
        isdoor=3<=b<=5
        bottom=z+(0.1 if isdoor else wall*.32)
        top=z+wall*.83
        fw=span*.72
        rect(X(mid-fw/2),Y(top),fw*SCALE,(top-bottom)*SCALE,'#a23a2b' if isdoor else '#383b3b','#963d30',.7)
        if not isdoor:
            for k in range(1,5):line(X(mid-fw/2+fw*k/5),Y(top),X(mid-fw/2+fw*k/5),Y(bottom),'#a75943',.65)
            line(X(mid-fw/2),Y((top+bottom)/2),X(mid+fw/2),Y((top+bottom)/2),'#a75943',.65)
        else:
            line(X(mid),Y(top),X(mid),Y(bottom),'#c49c62',.8)
            for side in [-.15,.15]:
                parts.append(f'<circle cx="{X(mid+side)}" cy="{Y(z+wall*.38)}" r="1.3" fill="#b9964c"/>')
    for b in range(10):
        xx=X(-bw/2+b*span)
        rect(xx-1.7,Y(z+wall),3.4,wall*SCALE,'#984d35')
    for zz in [z,z+wall*.86,z+wall]:
        rect(left,Y(zz)-1,bw*SCALE,2.2,'#9c573b')
    # Broad bracket band, shown schematically rather than in a Song/Qing order.
    for b in range(10):
        xx=X(-bw/2+b*span)
        for k in range(3):
            level=z+wall+bracket*(k+.35)/3
            arm=(.35+k*.23)*SCALE
            line(xx-arm,Y(level),xx+arm,Y(level),'#7e4934',2)
        line(xx,Y(z+wall),xx,Y(eave),'#754d36',2)
    # Roof plan is square; this is its front projection. The restrained rise at
    # the corners is an illustrative early-roof choice, not a measured section.
    ew=bw+8.8
    if i<8:
        ridge=bw*.72
        d=(f'M{X(-ew/2)},{Y(eave+.55)} Q{X(-ew/2+1.8)},{Y(eave-.05)} {X(-bw/2)},{Y(eave+.8)} '
           f'L{X(-ridge/2)},{Y(peak)} L{X(ridge/2)},{Y(peak)} L{X(bw/2)},{Y(eave+.8)} '
           f'Q{X(ew/2-1.8)},{Y(eave-.05)} {X(ew/2)},{Y(eave+.55)} Z')
    else:
        d=(f'M{X(-ew/2)},{Y(eave+.6)} Q{X(-bw*.45)},{Y(eave+.9)} {X(-2.0)},{Y(peak)} '
           f'L{X(2.0)},{Y(peak)} Q{X(bw*.45)},{Y(eave+.9)} {X(ew/2)},{Y(eave+.6)} Z')
    path(d,'#555d60','#394348',1.8)
    # Tile rhythm is a drawing convention.
    for k in range(1,31):
        xx=-ew/2+ew*k/31
        px=xx*(.70 if i<8 else .12)
        line(X(xx),Y(eave+.55),X(px),Y(peak-.15),'#82878a',.55)
    line(X(-ew/2),Y(eave+.4),X(ew/2),Y(eave+.4),'#354047',1.7)
    for sign in [-1,1]:
        bx=X(sign*ew/2); by=Y(eave+.4)
        line(bx,by,bx,by+6,'#84744b',.7)
        path(f'M{bx-2},{by+6}Q{bx},{by+3} {bx+2},{by+6}L{bx+2.7},{by+9}L{bx-2.7},{by+9}Z','#b09448','#8d794b',.5)
    if i>0:
        # Balcony at the actual upper-floor datum: not counted as another level.
        gw=bw+2.8
        gy=Y(z+.5)
        rect(X(-gw/2),Y(z+.4),gw*SCALE,3,'#9c573b')
        line(X(-gw/2),Y(z+1.7),X(gw/2),Y(z+1.7),'#8c4a35',1.7)
        line(X(-gw/2),Y(z+.9),X(gw/2),Y(z+.9),'#8c4a35',1.2)
        for k in range(19):
            xx=X(-gw/2+gw*k/18)
            line(xx,Y(z+.4),xx,Y(z+1.7),'#92513a',1.3)
    # Floor-base labels are placed at the exact floor datums, not wall centres.
    text(213,Y(z)+5,f'{i+1} 层  +{z:.1f}','small','end')
    line(220,Y(z),left-9,Y(z),'#b6b8ae',.85,extra='stroke-dasharray="3 3"')
    if i<8:z+=inc

params['floor_datums_m_assumed']=floor_levels

# Finial: the datum under the gold disc assembly is explicit.
datum=params['lower_edge_of_gold_discs_height_m_assumed']
rect(X(-1.5),Y(datum),3*SCALE,(datum-131.8)*SCALE,'#b39348','#8a733f')
line(CX,Y(131.8),CX,Y(145.6),'#a3853c',3)
for i in range(11):
    zz=datum+.4+i*.82
    rx=(1.9-i*.095)*SCALE
    parts.append(f'<ellipse cx="{CX}" cy="{Y(zz)}" rx="{rx}" ry="1.8" fill="#c2a04d" stroke="#8b753d" stroke-width=".7"/>')
path(f'M{X(-.25)},{Y(144.4)} Q{X(-1.3)},{Y(145.3)} {CX},{Y(147)} Q{X(1.3)},{Y(145.3)} {X(.25)},{Y(144.4)}Z','#b89a47','#8d773d',.9)
for sign in [-1,1]:
    path(f'M{CX},{Y(144.7)} Q{X(sign*5.0)},{Y(132.4)} {X(sign*(widths[-1]+8.8)/2)},{Y(123.3)}',stroke='#8e8a78',sw=.85)

# Exact guides avoid asserting the image-rendering output as measured geometry.
for height,label in [(147,'+147.00 m  宝瓶顶〔方案〕'),(datum,'+133.77 m  金盘下〔条件换算〕')]:
    yy=Y(height)
    line(CX+20,yy,683,yy,'#a79b7b',1,extra='stroke-dasharray="4 5"')
    text(688,yy-8,label,'small')
line(625,Y(0),625,Y(147),'#596f68',1.5)
for zz in range(0,148):
    yy=Y(zz)
    length=12 if zz%10==0 else 7 if zz%5==0 else 3.5
    line(625-length,yy,628,yy,'#596f68',1.2 if zz%10==0 else .7)
    if zz%10==0: text(640,yy+5,str(zz),'label')
line(613,Y(147),628,Y(147),'#8f7030',2)
text(640,Y(145),'m','small')
text(173,1547,'层底标高 / m','small','middle')
line(X(-19.1),1540,X(19.1),1540,'#7e8a7b')
for xx in [X(-19.1),X(19.1)]:line(xx,1534,xx,1546,'#7e8a7b')
text(CX,1570,'台基 38.2 m · 台基顶 +2.2 m','label','middle')
text(CX,1603,'台基尺寸有考古依据；各层分配为本案假设','small','middle')

note(442,'01  标尺与文献端点',[
 '每大格10 m，小格1 m。',
 '49 丈 × 10 × 0.273 m = 133.77 m；',
 '盘下至塔顶另设13.23 m。',
 '147 m是候选高度，不是实测原高。'])

text(760,655,'02  色彩依据','section')
swatches=[
 ('#b44a3b','朱红初层外墙','考古：钱国祥2017。'),
 ('#a23a2b','朱漆门扇；红窗构','门色明确；窗色有校本差别。'),
 ('#555d60','青灰至黑灰瓦面','本址出土瓦研究：钱等2010。'),
 ('#c2a04d','金色瓶、盘与铃铎','文献有据；金属工艺与重量未定。'),
 ('#ddd8cc','浅暖灰上层墙面','未知原色的示意，不能据作白墙。'),
 ('#984d35','红褐梁柱与斗栱','彩饰存在有文字，具体配色推定。'),
]
for i,(c,head,detail) in enumerate(swatches):
    yy=695+i*79
    rect(760,yy-17,22,22,c,'#9a9b8d',.6)
    text(794,yy,head,'note')
    text(794,yy+29,detail,'small')

note(1210,'03  力学检查后的定位',[
 '木架与屋面中值情景约6,000 t。',
 '存在通过位移筛查的参数组合；',
 '真实柱材、连接、塔心与地基未定。',
 '整体可行性尚未得到证明。'])
note(1412,'04  仍保留的复原假设',[
 '上层九间、八道平坐与4.4 m出檐；',
 '金盘采用十一重校本；',
 '土心原高、收分、暗层不画成定论。'])

rect(65,1650,1150,104,'#eceee6')
text(88,1683,'怎么读这张复原图','section')
text(88,1716,'标高和外轮廓按参数绘制；构件笔画不是柱截面。屏幕色值不是出土颜料测色结果。','small')
text(88,1741,'依据：《洛阳伽蓝记》《水经注》、钱国祥等2010、钱国祥2017；力学参数与限制见随附说明。','small')
parts.append('</svg>')
(ROOT/'yongning-v6-scaled-elevation.svg').write_text('\n'.join(parts),encoding='utf-8')
(ROOT/'design-parameters.json').write_text(json.dumps(params,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Wrote yongning-v6-scaled-elevation.svg and design-parameters.json')
