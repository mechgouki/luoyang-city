"""One reader-facing spatial atlas; source coordinates and relation canvases remain distinct."""
import json
from xml.etree import ElementTree as ET

from city_nodes_r7_maps import NS, el, label, lines, box, path_line, native_frame

GREEN, INK, BLUE, GOLD, MUTED = "#245a48", "#1d342e", "#3d788b", "#946634", "#596b64"
VIEWS = {
    "all": "0 0 1600 1860",
    "source": "20 100 1560 640",
    "palace-yongning": "20 735 780 535",
    "baima": "800 735 780 535",
    "sima": "20 1260 780 535",
    "jianchun": "800 1260 780 535",
}


def linked(parent, decision, title=None):
    if parent.tag == "{" + NS + "}a":
        assert parent.get("data-decision") == decision
        return parent
    node = el(parent, "a", href="#decision-" + decision, data_decision=decision,
              tabindex="0", aria_label=(title or decision) + "，查看空间判断与依据")
    el(node, "title").text = (title or decision) + "：查看证据与图面变化"
    return node


def chip(parent, decision, x, y, caption, color=GREEN, width=None):
    g = linked(parent, decision, caption)
    width = width or (len(caption) * 16 + 85)
    box(g, x, y - 24, width, 34, fill="#f3f7f4", stroke="#d4e0d8", rx=5)
    label(g, x + 10, y, decision, 14, fill=color, font_weight="700")
    label(g, x + 62, y, caption, 16, fill=INK)
    return g


def linkline(parent, decision, coords, color=GREEN, width=4, dashed=False, unknown=False, **attrs):
    g = linked(parent, decision)
    if dashed:
        attrs["stroke_dasharray"] = "7 5"
    path_line(g, coords, stroke=color, stroke_width=width, data_diagram="relative-not-geographic", **attrs)
    if unknown:
        for x, y in (coords[0], coords[-1]):
            el(g, "circle", cx=x, cy=y, r=5, fill="#fff", stroke=color, stroke_width=2,
               data_endpoint="unknown-not-ancient-road-end")
    return g


def relation_arrow(parent, decision, x1, y1, x2, y2, label_text=None, dashed=False, color=GREEN):
    g = linkline(parent, decision, [(x1, y1), (x2, y2)], color, 2, dashed)
    import math
    theta = math.atan2(y2 - y1, x2 - x1)
    wings = [(x2 - 8 * math.cos(theta + a), y2 - 8 * math.sin(theta + a)) for a in (-.5, .5)]
    path_line(g, [wings[0], (x2, y2), wings[1]], stroke=color, stroke_width=2)
    if label_text:
        label(g, (x1 + x2) / 2, (y1 + y2) / 2 - 9, label_text, 15, fill=color, text_anchor="middle")
    return g


def panel(root, key, x, y, title, subtitle):
    g = el(root, "g", id="map-panel-" + key, data_panel=key, data_coordinate_space="unscaled-relationship")
    box(g, x, y, 740, 505, fill="#fff", stroke="#c9d8cf", rx=10)
    label(g, x + 20, y + 35, title, 24, fill=GREEN, font_weight="700")
    label(g, x + 20, y + 62, subtitle, 16, fill=MUTED)
    return g


def palace(root):
    x, y = 40, 755
    g = panel(root, "palace-yongning", x, y, "宫前与永宁 · 门、寺、道及路侧", "北在上、东在右；无比例；官署图签不表示院界")
    # The road and the gate are conceptual placements; the exact 06a traces remain above.
    chip(g, "SP02", x + 280, y + 104, "宫前阊阖门", width=220)
    linkline(g, "SP03", [(x + 385, y + 130), (x + 385, y + 177)], GOLD, 8, unknown=True)
    linkline(g, "SP03", [(x + 385, y + 195), (x + 385, y + 250)], GOLD, 8, unknown=True)
    linkline(g, "SP03", [(x + 385, y + 268), (x + 385, y + 330)], GOLD, 8, unknown=True)
    label(g, x + 410, y + 153, "R01 残段", 17, fill=GOLD)
    label(g, x + 410, y + 180, "T01 御道", 17, fill=GOLD)
    label(g, x + 410, y + 207, "候选对应", 15, fill=MUTED)
    label(g, x + 402, y + 346, "南端接续未知", 15, fill=MUTED)
    t = linked(g, "SP02", "寺在门南、道西")
    box(t, x + 50, y + 180, 205, 100, fill="#eaf2ed", stroke=GREEN, stroke_dasharray="5 4")
    label(t, x + 152, y + 218, "永宁寺", 24, fill=GREEN, text_anchor="middle")
    label(t, x + 152, y + 251, "门南一里 · 道西", 17, fill=GREEN, text_anchor="middle")
    label(g, x + 52, y + 300, "寺框为关系范围，不是复原院墙", 15, fill=MUTED)
    # Textual directions do not establish mirror pairs or a measured avenue setback.
    chip(g, "SP04", x + 45, y + 139, "右卫府·道西", width=225)
    chip(g, "SP04", x + 510, y + 119, "左卫府·道东", width=205)
    chip(g, "SP04", x + 495, y + 273, "司徒府／国子学", width=225)
    label(g, x + 510, y + 310, "南向序列，独立路侧未定", 15, fill=MUTED)
    p = linked(g, "SP04", "太尉府寺东与道西解释分开")
    label(p, x + 275, y + 224, "太尉府", 18, fill=GOLD)
    relation_arrow(p, "SP04", x + 260, y + 266, x + 307, y + 266, "寺东", color=GREEN)
    relation_arrow(p, "SP04", x + 347, y + 297, x + 372, y + 297, dashed=True, color=GOLD)
    label(p, x + 272, y + 320, "道西：解释", 14, fill=GOLD)
    # Side-water relationship is separated from the avenue, with no invented outlet.
    linkline(g, "SP05", [(x + 345, y + 165), (x + 345, y + 188)], BLUE, 3, dashed=True, unknown=True)
    linkline(g, "SP05", [(x + 424, y + 230), (x + 424, y + 252)], BLUE, 3, dashed=True, unknown=True)
    chip(g, "SP05", x + 24, y + 383, "夹路支水：接口未明", width=335, color=BLUE)
    chip(g, "SP01", x + 379, y + 383, "来源门符／墙迹见上图", width=335)
    lines(g, x + 24, y + 424, ["本轮图面变化：门南、道西与官署路侧在同一局部窗可读。",
                              "实线方向为明文；金色虚线为段落解释。",
                              "路段留空、渠口留空，均不从全景画面补齐。"], 17, 28)


def baima(root):
    x, y = 820, 755
    g = panel(root, "baima", x, y, "白马寺坊街 · 中央十字与南口", "北在上、东在右；无比例；未配准到06a")
    # Only the reported middle crossing is joined; four secondary samples remain open.
    for coords in [[(x + 235, y + 110), (x + 235, y + 225)], [(x + 140, y + 165), (x + 335, y + 165)]]:
        linkline(g, "SP06", coords, GOLD, 7, unknown=True)
    for coords in [[(x + 100, y + 120), (x + 100, y + 146)], [(x + 370, y + 120), (x + 370, y + 146)],
                   [(x + 177, y + 93), (x + 290, y + 93)], [(x + 177, y + 252), (x + 290, y + 252)]]:
        linkline(g, "SP06", coords, GOLD, 4, unknown=True)
    label(g, x + 251, y + 132, "F01", 16, fill=GOLD)
    label(g, x + 291, y + 189, "F04", 16, fill=GOLD)
    chip(g, "SP08", x + 420, y + 111, "22米：纵街", width=285)
    chip(g, "SP09", x + 420, y + 159, "86／40米：街间距", width=285)
    lines(g, x + 435, y + 201, ["路缘／中心线基准未核", "不能累计成完整坊界"], 16, 27)
    unknown = linked(g, "SP07", "中央十字到南口接续未知")
    box(unknown, x + 77, y + 272, 319, 43, fill="#f7efe1", stroke="#d8b981", rx=5)
    label(unknown, x + 236, y + 300, "中央十字至南口：距离与接续未知", 16, fill=GOLD, text_anchor="middle")
    linkline(g, "SP07", [(x + 235, y + 331), (x + 235, y + 374)], GOLD, 7, unknown=True)
    linkline(g, "SP07", [(x + 57, y + 376), (x + 385, y + 376)], GOLD, 7, unknown=True)
    # Brackets express a reported gap; they do not assert masonry gate foundations.
    gap = linked(g, "SP08", "7.5米大道北缘缺口")
    path_line(gap, [(x + 207, y + 351), (x + 217, y + 351), (x + 217, y + 366)], stroke=GREEN, stroke_width=2)
    path_line(gap, [(x + 263, y + 351), (x + 253, y + 351), (x + 253, y + 366)], stroke=GREEN, stroke_width=2)
    label(gap, x + 72, y + 345, "X02／G11", 16, fill=GREEN)
    label(g, x + 73, y + 407, "O02 西阳门外大道", 18, fill=GOLD)
    chip(g, "SP08", x + 420, y + 280, "7.5米：缺口", width=285)
    label(g, x + 435, y + 319, "4.6米：车辙带，非整条路宽", 16, fill=MUTED)
    chip(g, "SP10", x + 420, y + 373, "沟槽不连咸池", width=285, color=BLUE)
    label(g, x + 435, y + 410, "槽与门址解释另核；W25独立索引", 15, fill=MUTED)
    lines(g, x + 24, y + 451, ["本轮图面变化：主街、次街、坊口与车辙带分出层级。",
                              "空心端只标材料到此；六街的各段使用层仍需分别核定。"], 17, 28)


def sima(root, sima_source):
    x, y = 40, 1280
    g = panel(root, "sima", x, y, "司马门与仓区 · 内外分区与三类道路", "北在上、东在右；关系无比例；2023图元独立")
    # Zones express reported relationships, not reconstructed walls or quantities.
    p = linked(g, "SP12", "宫院内部夹道")
    box(p, x + 24, y + 91, 230, 215, fill="#eef4ef", stroke=GREEN, stroke_dasharray="6 5")
    label(p, x + 42, y + 123, "太极宫院", 22, fill=GREEN)
    label(p, x + 42, y + 158, "东围廊", 17)
    linkline(p, "SP12", [(x + 157, y + 144), (x + 157, y + 267)], GOLD, 4, unknown=True)
    label(p, x + 176, y + 196, "P07", 16, fill=GOLD)
    label(p, x + 172, y + 225, "4.7米", 16, fill=GOLD)
    label(p, x + 43, y + 287, "东墙内夹道", 16, fill=MUTED)
    path_line(g, [(x + 254, y + 92), (x + 254, y + 305)], stroke=GREEN, stroke_width=3)
    p = linked(g, "SP11", "宫院东墙—道路—仓区西墙")
    linkline(p, "SP11", [(x + 310, y + 105), (x + 310, y + 285)], GOLD, 12, unknown=True)
    lines(p, x + 326, y + 157, ["P01", "最宽约", "40米"], 16, 29, fill=GOLD)
    label(p, x + 266, y + 319, "非两墙净距", 15, fill=MUTED)
    q = linked(g, "SP13", "仓区内路与南北分隔")
    box(q, x + 412, y + 91, 300, 215, fill="#eff3f7", stroke=GREEN, stroke_dasharray="6 5")
    label(q, x + 431, y + 123, "宫内仓区", 22, fill=GREEN)
    label(q, x + 431, y + 154, "北部建筑区", 16)
    path_line(q, [(x + 431, y + 174), (x + 550, y + 174)], stroke=GREEN, stroke_width=3)
    path_line(q, [(x + 580, y + 174), (x + 694, y + 174)], stroke=GREEN, stroke_width=3)
    label(q, x + 432, y + 202, "分区墙", 15, fill=MUTED)
    linkline(q, "SP13", [(x + 565, y + 216), (x + 565, y + 284)], GOLD, 6, unknown=True)
    lines(q, x + 581, y + 239, ["P08", "约13米"], 16, 27, fill=GOLD)
    label(q, x + 432, y + 285, "南部窖穴区", 16)
    label(g, x + 437, y + 329, "内路分东西；墙分南北；接点未知", 15, fill=MUTED)
    # Exact source line coordinates are never translated into the main city frame.
    native = el(g, "g", data_frame="sima2023-independent", data_city_registration="false",
                data_source_path="research/prosperity-r5/sima-road.json",
                transform=f"translate({x + 23} {y + 348})")
    box(native, 0, 0, 220, 85, fill="#f7faf9", stroke="#c9d7d2", rx=0)
    # Fit source frame into this viewport, retaining the original numeric geometry.
    coords = [v for line in sima_source["image"]["sima_road_ink_px"] for v in line]
    xs = [v[0] for v in coords]; ys = [v[1] for v in coords]
    bx1, by1, bx2, by2 = sima_source["image"]["storage_box_centerline_px"]
    xmin, xmax = min(xs + [bx1]), max(xs + [bx2]); ymin, ymax = min(ys + [by1]), max(ys + [by2])
    scale = min(190 / (xmax - xmin), 70 / (ymax - ymin))
    atom = el(native, "g", transform=f"translate({12 - xmin*scale} {7 - ymin*scale}) scale({scale})")
    a = linked(atom, "SP15", "2023原图六根路迹原子线")
    for i, points in enumerate(sima_source["image"]["sima_road_ink_px"]):
        path_line(a, points, stroke=GOLD, stroke_width=2 / scale, data_sima_atomic_line=i,
                  data_source_pointer="/image/sima_road_ink_px/" + str(i))
    el(a, "rect", x=bx1, y=by1, width=bx2-bx1, height=by2-by1, fill="none", stroke=BLUE,
       stroke_width=1 / scale, stroke_dasharray=f"{4/scale} {3/scale}",
       data_source_pointer="/image/storage_box_centerline_px", data_role="source-region-box-not-wall")
    label(native, 82, 78, "独立原图框", 13, fill=MUTED)
    chip(g, "SP15", x + 265, y + 376, "六线不跨图挪位", width=220)
    chip(g, "SP14", x + 499, y + 376, "宫外仓区另框", width=214)
    label(g, x + 268, y + 416, "三门参照各不同；宫内外统计与使用层分别核验", 15, fill=MUTED)
    lines(g, x + 24, y + 455, ["本轮图面变化：宫院、主路、仓区及仓内分区一眼可辨。",
                              "168口、3排、13口保留统计口径，不转换为同期屋顶阵列。"], 17, 28)


def jianchun(root):
    x, y = 820, 1280
    g = panel(root, "jianchun", x, y, "建春门桥渠 · 桥向、分期与未定接口", "各组北在上、东在右；无比例；三桥位置不由排版推出")
    a = linked(g, "SP16", "第一桥与527年事件")
    box(a, x + 24, y + 92, 200, 194, fill="#f4f7f4", stroke="#d2ded6")
    label(a, x + 40, y + 124, "建春门外石桥", 19, fill=GREEN)
    label(a, x + 40, y + 154, "B01 · 明悬尼寺在南", 15)
    lines(a, x + 40, y + 198, ["527年大雨受损", "528年前修复未定", "事件只归第一桥"], 16, 28, fill=GOLD)
    a = linked(g, "SP17", "东石桥南北通行")
    box(a, x + 240, y + 92, 235, 194, fill="#f4f7f4", stroke="#d2ded6")
    label(a, x + 256, y + 124, "东石桥 B02 · 南北向", 18, fill=GREEN)
    linkline(a, "SP17", [(x + 356, y + 151), (x + 356, y + 174)], GOLD, 5, unknown=True)
    label(a, x + 259, y + 164, "建阳里", 15)
    label(a, x + 388, y + 164, "绥民里", 15)
    for dx in [-8, 8]:
        path_line(a, [(x + 356 + dx, y + 188), (x + 356 + dx, y + 224)], stroke=GREEN, stroke_width=3)
    for yy in [191, 205, 220]:
        path_line(a, [(x + 348, y + yy), (x + 364, y + yy)], stroke=GREEN, stroke_width=2)
    linkline(a, "SP17", [(x + 356, y + 239), (x + 356, y + 260)], GOLD, 5, unknown=True)
    label(a, x + 259, y + 275, "桥头与御道路口未定", 15, fill=MUTED)
    a = linked(g, "SP17", "七里桥至三门")
    box(a, x + 491, y + 92, 222, 194, fill="#f4f7f4", stroke="#d2ded6")
    label(a, x + 507, y + 124, "七里桥 B03", 19, fill=GREEN)
    label(a, x + 507, y + 154, "崇义里东有桥", 16)
    relation_arrow(a, "SP17", x + 514, y + 199, x + 680, y + 199, "桥东一里至三门")
    lines(a, x + 507, y + 242, ["桥名七里不是门至桥距", "营造异说及比定保留"], 15, 27, fill=MUTED)
    a = linked(g, "SP18", "北渠迹与南渠解释")
    box(a, x + 24, y + 302, 438, 92, fill="#eef5f6", stroke="#c8dadd")
    label(a, x + 38, y + 332, "调查关系：渠迹在路北（宽年代）", 17, fill=BLUE)
    label(a, x + 38, y + 365, "分期解释：北魏阳渠在路南", 17, fill=GOLD)
    chip(g, "SP19", x + 479, y + 329, "暗渠接口未定", width=234, color=BLUE)
    chip(g, "SP20", x + 479, y + 378, "七里涧异读并存", width=234, color=BLUE)
    lines(g, x + 24, y + 430, ["本轮图面变化：东石桥的纵向通行与三桥各自参照可直接阅读。",
                              "两行水道关系不是同期双渠；门下暗渠不接外渠。",
                              "鸿池出口、桥头与渠口均保留未知，不由异读补成确定水网。"], 17, 28)


def build_map(atlas, data, sima_source):
    root = ET.Element("{" + NS + "}svg", {
        "id": "spatial-map", "viewBox": VIEWS["all"], "width": "1600", "height": "1860",
        "role": "img", "aria-labelledby": "r9-map-title r9-map-desc", "lang": "zh-CN",
        "font-family": "Noto Sans CJK SC, sans-serif", "data-original-viewbox": VIEWS["all"],
        "data-new-geographic-coordinates": "0", "data-new-shoreline-geometries": "0",
        "data-source-frames-registered-together": "false"})
    el(root, "title", id="r9-map-title").text = "盛时洛阳城市空间总图：来源骨架与四处局部关系"
    el(root, "desc", id="r9-map-desc").text = "主图保留图06a既有几何，四局部窗无比例。所有二十项图面决策可点选查看依据，独立图框不构成共同配准。"
    el(root, "rect", width=1600, height=1860, fill="#f4f7f4")
    label(root, 40, 49, "盛时洛阳 · 城市空间总图", 34, fill=INK, font_weight="700")
    label(root, 40, 84, "516—528年研究窗口 · 同一阅读框架，分别保留位置、关系与未知", 20, fill=MUTED)
    label(root, 40, 130, "来源骨架｜06a原图几何", 23, fill=GREEN, font_weight="700")
    native, scale, dx, dy = native_frame(root, "r9-source-city", 40, 150, 790, 530,
                                        (93, 134, 478, 448), atlas["features"])
    native.set("data-coordinate-space", "06a-source-pdf-units")
    for f in atlas["features"]:
        found = next((a for a in native if a.get("data-feature") == f["id"]), None)
        if found is not None:
            found.set("data-source-geometry", json.dumps(f["source_pdf_geometry"], ensure_ascii=False, separators=(",", ":")))
            # This atlas uses colour for evidence type. Recolour only the
            # source primitives; keep their paths, points, breaks and widths.
            for primitive in found.iter():
                if primitive.get("data-native-geometry"):
                    if primitive.get("stroke") not in (None, "none"):
                        primitive.set("stroke", GREEN)
                    if primitive.get("fill") == "#dcdfbf":
                        primitive.set("fill", "#dce9df")
            if f["id"] in {"geo-yongning-temple-walls", "geo-yongning-pagoda-reference", "geo-changhe-palace-gate", "geo-tongtuo-avenue"}:
                decision = "SP03" if f["id"] == "geo-tongtuo-avenue" else "SP01"
                found.set("href", "#decision-" + decision); found.set("data-decision", decision)
    label(root, 57, 181, "北 ↑", 17, fill=GREEN)
    for fid, decision, caption, ox, oy in [
        ("geo-yongning-pagoda-reference", "SP02", "宫前与永宁", -190, 50),
        ("geo-xiyang-gate", "SP07", "西阳门参照", -195, -10),
        ("geo-taiji-hall-reference", "SP11", "太极殿参照", -185, -70),
        ("geo-jianchun-gate", "SP19", "建春门参照", 32, 7),
    ]:
        f = next(f for f in atlas["features"] if f["id"] == fid)
        px, py = f["source_pdf_geometry"]["coordinates"]
        ax, ay = px * scale + dx, py * scale + dy
        a = linked(root, decision, caption)
        el(a, "line", x1=ax, y1=ay, x2=ax+ox, y2=ay+oy, stroke="#657e71", stroke_width=1.3, data_role="reading-index-not-road")
        label(a, ax+ox+(0 if ox<0 else 5), ay+oy-7, caption, 17, fill=GREEN)
        el(a, "circle", cx=ax, cy=ay, r=5, fill="#fff", stroke=GREEN, stroke_width=2)
    lines(root, 55, 705, ["原段逐值沿用；引线仅供阅读，外圈为相关遗存范围，浅色面为候选范围。"], 15, fill=MUTED)
    box(root, 855, 150, 705, 570, fill="#fff", stroke="#c9d8cf")
    label(root, 880, 187, "三种依据，在图上有不同含义", 25, fill=GREEN, font_weight="700")
    for yy, color, title, detail in [
        (234, GREEN, "来源图位置", "主图内原有图符与遗迹线；不升级为现场控制点。"),
        (304, GOLD, "文献／报告关系", "局部窗中的方位、接触与分区；图上间距无比例。"),
        (374, MUTED, "仍待定位", "空心端、空白与独立图框；保留缺失的接续和接口。"),
    ]:
        el(root, "circle", cx=895, cy=yy-6, r=7, fill="#fff" if color==MUTED else color, stroke=color, stroke_width=2)
        label(root, 915, yy, title, 21, fill=color, font_weight="700")
        label(root, 880, yy+30, detail, 17, fill=MUTED)
    label(root, 880, 454, "这轮把四类空间组织画清楚", 22, fill=GREEN, font_weight="700")
    for i, (decision, title) in enumerate([
        ("SP02", "门南道西与官署路侧分别成立"),
        ("SP06", "中央十字、次街和南口分出层级"),
        ("SP11", "宫院、主路、仓区形成不同空间"),
        ("SP17", "东石桥桥向与桥渠分期分别阅读"),
    ]):
        chip(root, decision, 880, 497+i*47, title, width=650)
    palace(root); baima(root); sima(root, sima_source); jianchun(root)
    label(root, 40, 1822, "每个SP编号对应同页证据行；本轮新增古代坐标0、古岸线0，图面深化不等于新增发掘。", 18, fill=MUTED)
    return ET.tostring(root, encoding="unicode")
