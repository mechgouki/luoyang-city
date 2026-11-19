"""Draw the 1973 survey and the 2018 reconstruction in their own source frames."""
import shutil
from xml.etree import ElementTree as ET

from dual_cartography import dump, load, sha
from north_b4 import render_atlas
from prosperity_anchors_p461 import ROOT, SITE, digest
from prosperity_corridors_p463 import INK, MUTED, ROAD, WATER, label, line, node, plate
from prosperity_field_p464 import PAGE as PREVIOUS

FOLDER = "gates-465"
SOURCE = ROOT / "research/prosperity-v4" / FOLDER
PAGE = "prosperity-gates-p465.html"
ATLAS = f"downloads/{FOLDER}.pdf"
ENTRY = f'<p id="p465-entry"><a href="./{PAGE}">续读 · 承明门西段、邙山北路与北垣河道</a></p>\n'
WALL, PAPER = "#64756b", "#faf8f0"


def trace(root, points, project, color, width=4, dash=None):
    coords = [project(x, y) for x, y in points]
    path = node(root, "polyline", points=" ".join(f"{x:.1f},{y:.1f}" for x, y in coords),
                fill="none", stroke=color, stroke_width=width, stroke_linejoin="round",
                stroke_linecap="round")
    if dash:
        path.set("stroke-dasharray", dash)


def dot(root, xy, hollow=False):
    x, y = xy
    node(root, "circle", cx=x, cy=y, r=6.5, stroke=ROAD, stroke_width=3,
         fill=PAPER if hollow else ROAD)


def field_plate(data):
    root = plate("1973年实测图上的三座城门", "选取内城西北部。门位和墙线依原图像素等比绘制，报告所载的地面距离另注。")
    def project(x, y):
        return 67 + (x-650)*0.69, 172 + (y-600)*0.69
    for wall in data["wall_traces_px"]:
        trace(root, wall, project, WALL, 4)
    trace(root, data["h4_sample_px"], project, ROAD, 3)
    positions = [("IV","Ⅳ  阊阖门",14,28),("V","Ⅴ  承明门",14,34),
                 ("VI","Ⅵ  大夏门",-65,-17),("VII","Ⅶ  广莫门",-40,-22)]
    for key, name, dx, dy in positions:
        xy = project(*data["points"][key])
        dot(root, xy)
        label(root, xy[0]+dx, xy[1]+dy, name, 20)
    label(root, 230, 407, "城内横四道", 17, ROAD)
    label(root, 374, 326, "金村", 17, MUTED)
    label(root, 48, 322, "翟泉", 17, MUTED)
    label(root, 577, 349, "东北角", 16, MUTED)
    line(root, 671, 162, 671, 573, "#c8cbbc", 1)
    label(root, 702, 196, "西垣 · Ⅴ号", 22, ROAD)
    label(root, 702, 232, "门下路土叠压墙基。", 17)
    label(root, 702, 262, f"阙口宽约{data['v_gap_width_approx_m']}米。", 17)
    label(root, 702, 292, f"南至Ⅳ号约{data['v_to_iv_reported_approx_m']}米。", 17)
    label(root, 702, 348, "北垣 · Ⅵ号", 22, ROAD)
    label(root, 702, 384, "阙口中有两堵夯土隔墙，", 17)
    label(root, 702, 414, "工作队据此判断一门三道。", 17)
    label(root, 702, 466, "北垣 · Ⅶ号", 22, ROAD)
    label(root, 702, 502, "路土穿过受损缺口，内外可见。", 17)
    label(root, 702, 532, f"东至内城东北角约{data['vii_to_ne_corner_reported_approx_m']}米。", 17)
    line(root, 46, 605, 973, 605, "#c8cbbc", 1)
    label(root, 47, 646, "Ⅴ、Ⅶ的门名是工作队结合门位与文献所作的比定。出城道路的最后探点仍待查。", 18)
    label(root, 47, 694, "图源：《考古》1973年第4期199页。现据谢美婧2009年论文附录5核图。", 16, MUTED)
    return root


def outer_plate(data):
    root = plate("两条北路在哪里穿过图上的北郭？", "据钱国祥2018年图一。棕线为作者所绘道路走向，空心圆标出图中的墙路交点。")
    # Use the same scale on both axes, so graphical angles and distances are preserved.
    def map_xy(x, y):
        return 68 + (x-430)*1.83, 173 + (y-5)*1.83
    line(root, 70, 175, 599, 175, "#bfc4b8", 1)
    label(root, 72, 160, "邙山方向 · 原图北边缘", 16, MUTED)
    trace(root, data["inner_wall_px"], map_xy, WALL, 4)
    trace(root, data["outer_wall_px"], map_xy, WALL, 3, "10 5")
    label(root, 70, 247, "北外郭", 16, MUTED)
    for road in data["north"]:
        pts = road["to_wall_px"]
        trace(root, pts, map_xy, ROAD, 4)
        trace(root, road["beyond_wall_to_frame_px"], map_xy, ROAD, 3, "5 4")
        inner, crossing = map_xy(*pts[0]), map_xy(*pts[-1])
        dot(root, inner)
        dot(root, crossing, hollow=True)
        label(root, inner[0]+8, inner[1]+29, road["name"], 19)
    west = data["west"]["trace_px"]
    trace(root, west, map_xy, ROAD, 3, "5 3")
    wx, wy = map_xy(*west[0])
    dot(root, (wx, wy))
    label(root, wx+10, wy+30, "承明门", 19)
    label(root, 322, 576, "内城", 19, MUTED)
    line(root, 663, 160, 663, 607, "#c8cbbc", 1)
    label(root, 692, 193, "内城门至北郭交点", 22)
    for i, road in enumerate(data["north"]):
        y = 248 + 83*i
        label(root, 693, y, road["name"], 20, ROAD)
        label(root, 693, y+35, f"图上直距约 {road['chord_km_one_decimal']:.1f} 公里", 22)
    label(root, 692, 405, "原图比例尺", 18, MUTED)
    label(root, 692, 437, "92像素对应1公里。", 17)
    label(root, 692, 484, "两条线分别伸到图框北边。", 17)
    label(root, 692, 513, "图内没有画出两路的交会点。", 17)
    label(root, 692, 559, "承明门以西只见一小段画线，", 17)
    label(root, 692, 587, "它的西端没有探孔编号。", 17)
    line(root, 45, 619, 975, 619, "#c8cbbc", 1)
    label(root, 46, 655, "钱氏推断墙路交会处有郭门。《文化瀍河》提出道路可能穿山沟越郭，可能未建城门。", 18)
    label(root, 46, 698, "图示距离供对读复原方案。北郭是否有门基、两路在哪里会合，须由发掘记录另行定位。", 16, MUTED)
    return root


def moat_plate(data):
    root = plate("广莫门到内城东北角的护城河", "1973年勘查报告分别记录墙河间距、河道宽度和淤积深度。三项各从零起算，单位为米。")
    start, scale = 365, 14
    for value in range(0,41,5):
        x = start+scale*value
        line(root, x, 194, x, 417, "#dedfd3", 1)
        label(root, x, 182, value, 16, MUTED, "middle")
    for y, name, bounds in [(237,"河道与内城北垣相距",data["offset_from_inner_north_wall_approx_m"]),
                            (313,"河道宽",data["channel_width_approx_m"])]:
        lo, hi = bounds
        label(root, 48, y+6, name, 21)
        line(root, start, y, start+lo*scale, y, "#b0c8c4", 8)
        line(root, start+lo*scale, y, start+hi*scale, y, WATER, 10)
        label(root, start+hi*scale+12, y+7, f"{lo}–{hi}", 18, WATER)
    depth = data["silt_depth_at_least_m"]
    y, end = 386, start+depth*scale
    label(root, 48, y+6, "淤土深", 21)
    line(root, start, y, end, y, WATER, 8)
    node(root, "path", d=f"M {end+3} {y-7} l 8 7 -8 7", fill="none", stroke=WATER, stroke_width=3)
    label(root, end+24, y+6, f"{depth}以上", 18, WATER)
    line(root, 46, 454, 976, 454, "#c8cbbc", 1)
    label(root, 47, 497, "在何处重新探到河道？", 23, WATER)
    label(root, 47, 537, "金墉甲城北侧一段受1958年中州大渠施工影响。在甲城东约300米、今渠南侧一带复见河道。", 17)
    label(root, 47, 573, "再往东南，经广莫门至内城东北角，与北垣并行，过角折南。", 18)
    label(root, 47, 633, "报告未说明墙河间距以哪两缘为准，也未给出这一段过水桥涵的位置。", 18)
    label(root, 47, 692, "深度是勘查所见的淤土堆积。516—528年的常水位、水深及过河设施仍待同期材料。", 16, MUTED)
    return root


def build(site=SITE):
    dest = site / FOLDER
    dest.mkdir(exist_ok=True)
    data = load(SOURCE / "readings.json")
    plates = []
    for name, graphic in [("field", field_plate(data["field_plan"])), ("north", outer_plate(data["later_plan"])),
                          ("moat", moat_plate(data["moat"]))]:
        path = dest / f"{name}.svg"
        ET.ElementTree(graphic).write(path, encoding="utf-8", xml_declaration=True)
        plates.append(path)
    render_atlas(plates, site / ATLAS)
    shutil.copyfile(SOURCE / "readings.json", dest / "readings.json")
    shutil.copyfile(SOURCE / "index.html", site / PAGE)
    previous = site / PREVIOUS
    original = previous.read_text().replace(ENTRY, "")
    marker = '<nav aria-label="补图目录">'
    if digest(original.encode()) != "b10ba2f7b9b4aff401aea3a28b8e2753155838159dc69acdb436fe7b88668796" or original.count(marker) != 1:
        raise ValueError("Review the P4.6.4 page before adding the next study")
    previous.write_text(original.replace(marker, ENTRY+marker, 1))
    info = load(site / "build-info.json")
    release = load(site / "release.json")
    version = "prosperity-gates-p465"
    release["extensions"] = sorted(set(release["extensions"]) | {version})
    release["current_milestone"] = "盛时 P4.6.5 · 承明门西段、邙山北路与北垣河道"
    dump(site / "release.json", release)
    info["prosperity_gates_p465"] = {"version": version, "source_commit": info["source_commit"],
                                     "page": PAGE, "atlas": ATLAS, "readings": f"{FOLDER}/readings.json",
                                     "plates": [p.name for p in plates]}
    for path in [*plates, dest / "readings.json", site / ATLAS, site / PAGE, previous, site / "release.json"]:
        info["files_sha256"][path.relative_to(site).as_posix()] = sha(path)
    dump(site / "build-info.json", info)
