"""Reader-facing plates; native source frames and relationship canvases stay separate."""
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from city_atlas_r4_maps import geometry
from city_nodes_r7_contract import BASE, PAGE

ROOT = Path(__file__).resolve().parents[1]
NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
INK, GREEN, GOLD, PAPER, BLUE = "#263f36", "#315f4e", "#916331", "#f6f3e9", "#427a8b"


def el(parent, tag, **attrs):
    return ET.SubElement(parent, "{" + NS + "}" + tag,
                         {k.replace("_", "-"): str(v) for k, v in attrs.items()})


def label(parent, x, y, message, size=18, **attrs):
    node = el(parent, "text", x=x, y=y, font_size=size, fill=attrs.pop("fill", INK), **attrs)
    node.text = str(message)
    return node


def lines(parent, x, y, messages, size=16, step=25, **attrs):
    for i, message in enumerate(messages):
        label(parent, x, y + i * step, message, size, **attrs)


def box(parent, x, y, w, h, fill="#fffdf7", stroke="#d4d8c9", **attrs):
    return el(parent, "rect", x=x, y=y, width=w, height=h, fill=fill, stroke=stroke, rx=attrs.pop("rx", 8), **attrs)


def link(parent, anchor, road_id=None, **attrs):
    if road_id:
        attrs["data_segment_ref"] = road_id
    return el(parent, "a", href=BASE + PAGE + "#" + anchor, **attrs)


def plate(key, title, subtitle, height, width=1200):
    root = ET.Element("{" + NS + "}svg", {
        "viewBox": f"0 0 {width} {height}", "width": str(width), "height": str(height),
        "role": "img", "aria-labelledby": key + "-title " + key + "-desc", "lang": "zh-CN",
        "font-family": "Noto Sans CJK SC, sans-serif", "data-plate": key,
        "data-new-geographic-coordinates": "0"})
    el(root, "title", id=key + "-title").text = title
    el(root, "desc", id=key + "-desc").text = subtitle
    el(root, "rect", width=width, height=height, fill=PAPER)
    label(root, 40, 49, title, 29, font_weight="700")
    label(root, 40, 82, subtitle, 16, fill="#526457")
    return root


def native_frame(parent, key, x, y, w, h, crop, features, road_ids=None):
    """Retain 06a source coordinates, adding only a viewport transform and links."""
    cx, cy, cw, ch = crop
    scale = min(w / cw, h / ch)
    dx, dy = x + (w - cw * scale) / 2 - cx * scale, y + (h - ch * scale) / 2 - cy * scale
    box(parent, x, y, w, h, rx=0)
    defs = el(parent, "defs")
    clip = el(defs, "clipPath", id=key + "-crop")
    el(clip, "rect", x=x + 1, y=y + 1, width=w - 2, height=h - 2)
    viewport = el(parent, "g", clip_path=f"url(#{key}-crop)")
    native = el(viewport, "g", transform=f"translate({dx} {dy}) scale({scale})",
                data_frame="frame-06a", data_city_registration="false")
    for f in sorted(features, key=lambda f: (0 if f["layer"] == "layout_envelope" else 2 if f["source_pdf_geometry"]["type"] == "Point" else 1)):
        if f["id"].startswith("geo-modern-"):
            continue
        rid = (road_ids or {}).get(f["id"])
        group = link(native, "segment-" + rid, rid) if rid else el(native, "a", href=BASE + "prosperity-city-atlas.html#feature-" + f["id"])
        group.set("data-feature", f["id"])
        el(group, "title").text = f["label"] + "；" + f["source_historical_period"]
        geometry(group, f, scale)
    return native, scale, dx, dy


def road_label(parent, rid, x, y, caption, size=17, **attrs):
    group = link(parent, "segment-" + rid, rid)
    label(group, x, y, caption, size, fill=attrs.pop("fill", GREEN), **attrs)
    return group


def path_line(parent, coords, **attrs):
    return el(parent, "path", d=" ".join(("M" if i == 0 else "L") + f"{x} {y}" for i, (x, y) in enumerate(coords)),
              fill="none", **attrs)


def overview(atlas, data):
    root = plate("r7-overview", "盛时洛阳 · 四处城市节点联读", "516—528 年研究窗口｜遗址图、水系研究图与文献关系分别保留来源图框", 1220)
    label(root, 40, 124, "① 由城市遗址图找到研究地段", 20, font_weight="700")
    roads = {r.get("source_feature_id"): r["id"] for r in data["segments"] if r.get("source_feature_id")}
    _, scale, dx, dy = native_frame(root, "r7-overview-city", 40, 145, 580, 535, (93, 134, 478, 448), atlas["features"], roads)
    label(root, 58, 176, "北 ↑", 17)
    for number, fid, ox, oy in [("1", "geo-yongning-pagoda-reference", -32, 28), ("2", "geo-xiyang-gate", -32, -7),
                                ("3", "geo-taiji-hall-reference", -25, -18), ("4", "geo-jianchun-gate", 16, 5)]:
        f = next(f for f in atlas["features"] if f["id"] == fid)
        px, py = f["source_pdf_geometry"]["coordinates"]
        node = data["nodes"][int(number) - 1]
        a = link(root, "node-" + node["id"])
        el(a, "line", x1=px * scale + dx, y1=py * scale + dy,
           x2=px * scale + dx + ox, y2=py * scale + dy + oy,
           stroke="#6c8072", stroke_width=1, data_role="annotation-leader")
        el(a, "circle", cx=px * scale + dx + ox, cy=py * scale + dy + oy, r=14, fill=GREEN)
        label(a, px * scale + dx + ox, py * scale + dy + oy + 6, number, 16, fill="#fff", text_anchor="middle")
    lines(root, 53, 708, ["底图：2012年保护管理图06a；城墙与八条内城路迹沿原图保留。",
                         "圈号指向已有参照对象；引线只用于标注，不是古代道路。",
                         "外圈虚线为相关遗存范围，不是完整实测外郭墙。"], 14, 23)
    cards = [
        ("palace-yongning", "1  宫前与永宁寺", ["参照：永宁塔基与宫前门址", "道路残段与御道名称保留候选对应。", "官署方位：原文明示、段落推读分别读。"]),
        ("baima", "2  白马寺坊门与街道", ["参照：西阳门，发掘地段在门外", "白马寺局部尚未接入本图坐标。", "中央十字至南坊门距离仍未知。"]),
        ("sima", "3  司马门与仓区", ["参照：太极殿，司马门见独立原图", "六根原图路迹原子线保留断口。", "道路、夹道、仓区内路不合并宽度。"]),
        ("jianchun", "4  建春门三桥", ["参照：建春门门址", "三桥依文献关系分别列出。", "527年第一桥变化，不扩展至三桥。"]),
    ]
    for i, (key, title, msgs) in enumerate(cards):
        y = 145 + i * 143
        a = link(root, "node-" + key)
        box(a, 653, y, 507, 128)
        label(a, 674, y + 32, title + "  →", 21, fill=GREEN, font_weight="700")
        lines(a, 674, y + 59, msgs, 16, 25)
    label(root, 40, 786, "② 水系另图联读：相同地名帮助查证，两个图框不强行叠合", 20, font_weight="700")
    water = json.loads((ROOT / "research/water-atlas/huang-figure1.json").read_bytes())
    box(root, 40, 808, 1120, 304, rx=0)
    ws = .76
    native = el(root, "g", transform=f"translate(220 822) scale({ws})", data_frame="huang-figure1",
                data_source_path="research/water-atlas/huang-figure1.json", data_city_registration="false")
    for name, coords in water["cities"]:
        path_line(native, coords, stroke="#9aa88e", stroke_width=2 / ws)
    for i, (wid, name, kind, coords) in enumerate(water["traces"]):
        present = wid in {w["id"] for w in data["waters"]}
        a = link(native, "water-" + wid) if present else el(native, "a", href=BASE + "luoyang-water-atlas.html#" + wid)
        a.set("data-water-ref", wid)
        a.set("data-source-pointer", "/traces/" + str(i))
        el(a, "title").text = wid + " " + name + "；研究示意图原生图框，非北魏实测岸线。"
        if kind == "symbol":
            el(a, "circle", cx=coords[0][0], cy=coords[0][1], r=5 / ws, fill="#fff", stroke=BLUE, stroke_width=2 / ws)
        else:
            attrs = {"stroke": BLUE, "stroke_width": 2 / ws}
            if kind == "dry":
                attrs["stroke_dasharray"] = "7 6"
            path_line(a, coords, **attrs)
    for x, y, text in [(490, 63, "洛阳城"), (390, 178, "洛水"), (625, 101, "阳渠"), (790, 188, "鸿池陂"), (328, 123, "谷水")]:
        label(native, x, y, text, 16 / ws, fill=BLUE)
    lines(root, 58, 847, ["黄学超图1", "独立来源图框", "10项水体", "12段笔画／符号", "", "水面与岸线未测定"], 15, 28)
    lines(root, 40, 1152, ["读图规则：遗存线按原段；关系线只表示材料中的次序；空缺处保留未知，不从首页画面补路、补桥头或补古岸。",
                          "点圈号进入节点核验；点道路或水体查逐项证据。完整339对象、84道路来源、34水项仍可从总索引回查。"], 16, 27)
    return root


def baima_map(atlas, data):
    root = plate("r7-baima", "白马寺南坊门 · 六街、中央十字与门外大道", "相对次序图｜图上间距无比例；跨年度发现分别登记，不组成完整同期里坊网格", 1010)
    box(root, 40, 120, 720, 700)
    label(root, 61, 153, "北 ↑  坊内", 17)
    label(root, 420, 153, "六街登记 ≠ 九处交点均已发掘", 16, fill=GOLD)
    # Only the reported central crossing is continuous. Other streets remain separate specimens.
    for rid, points in [("F01", [[380, 212], [380, 401]]), ("F04", [[237, 309], [545, 309]]),
                        ("F02", [[155, 218], [155, 271]]), ("F03", [[634, 218], [634, 271]]),
                        ("F05", [[287, 188], [458, 188]]), ("F06", [[287, 439], [458, 439]])]:
        a = link(root, "segment-" + rid, rid)
        path_line(a, points, stroke=GOLD, stroke_width=7, stroke_linecap="butt", data_diagram="reported-road-relationship")
        for x, y in (points[0], points[-1]):
            el(a, "circle", cx=x, cy=y, r=5, fill="#fffdf7", stroke=GOLD, stroke_width=2)
    road_label(root, "F05", 473, 194, "北横街 F05", 16)
    road_label(root, "F02", 80, 298, "西纵街 F02", 15)
    road_label(root, "F03", 590, 298, "东纵街 F03", 15)
    road_label(root, "F04", 468, 342, "中横街 F04", 16)
    road_label(root, "F01", 400, 248, "居中纵街 F01", 17)
    road_label(root, "F06", 473, 445, "南横街 F06", 16)
    label(root, 399, 377, "报告宽22米；不按图宽量取", 15)
    a = link(root, "finding-BA03")
    box(a, 61, 347, 188, 77, fill="#eef1e6")
    lines(a, 76, 375, ["其余交点未补全", "道路实际端点未知"], 16, 26)
    # A visible blank is intentional: no recovered measurement connects the gate and the central cross.
    a = link(root, "finding-BA07")
    box(a, 228, 478, 355, 76, fill="#f5eddc", stroke="#c5ac7e")
    lines(a, 245, 506, ["中央十字至南坊门：距离未知", "尚缺同图测线，图上不补连续街段"], 16, 26, fill="#785729")
    a = link(root, "segment-X02", "X02")
    path_line(a, [[380, 584], [380, 688]], stroke=GOLD, stroke_width=8)
    road_label(root, "X02", 405, 607, "南口交会 X02", 17)
    a = link(root, "segment-G11", "G11")
    # Brackets describe the reported opening; no symmetric gate piers are inferred.
    path_line(a, [[345, 634], [357, 634], [357, 659], [345, 659]], stroke="#71816c", stroke_width=2)
    path_line(a, [[415, 634], [403, 634], [403, 659], [415, 659]], stroke="#71816c", stroke_width=2)
    label(a, 441, 645, "大道北缘缺口 G11 · 约7.5米", 16, fill=GREEN)
    label(a, 441, 670, "坊门解释；不补墩台、门楼", 14, fill=GREEN)
    a = link(root, "segment-O02", "O02")
    path_line(a, [[85, 691], [709, 691]], stroke=GOLD, stroke_width=8)
    label(a, 85, 728, "西阳门外大道 O02   → 西阳门方向", 17, fill=GREEN)
    lines(root, 61, 772, ["X02与门洞处的局部接触有报道；门建筑性质与具体使用层另行核验。"], 15)
    for y, title, msgs in [
        (120, "量值各归其位", ["22米：居中纵街宽", "7.5米：南门缺口宽", "4.6米：车辙带宽", "三者不能替代彼此。"]),
        (309, "86米与40米", ["年度报告的街间距另列。", "测量基线尚未核同；", "不累计成完整坊宽、坊深。"]),
        (480, "使用年代", ["北魏归属沿用报告。", "六条街道的使用层尚未", "逐一细分至516—528年。"]),
        (650, "坊门沟槽与咸池", ["沟槽的构造解释待原图。", "W25只供同大道地望联读，", "不画成坊门沟槽的水源。"]),
    ]:
        box(root, 786, y, 374, 168 if y == 120 else 149)
        label(root, 806, y + 34, title, 21, font_weight="700")
        lines(root, 806, y + 65, msgs, 17, 26)
    a = link(root, "water-W25")
    label(a, 806, 833, "W25 咸池：查看地望依据 →", 16, fill=BLUE)
    lines(root, 40, 887, ["来源：2024年度里坊发掘纪要；2025年度南坊门纪要；2026年人民日报报道。具体段落与本轮访问情况见核验卡。",
                         "图例：棕线＝已报道的道路关系；圆端＝图上停止，不表示古路止点；明显空白＝接续测线缺失。",
                         "下一份关键原件：坊门、中央十字和两条道路在同一比例尺、同一基准上的发掘平面及分层测线。"], 16, 32)
    return root


def sima_map(atlas, data):
    root = plate("r7-sima", "司马门内道路 · 宫院、宫内仓区与宫外仓区", "原图像素框与关系示意分开｜三种路宽分别归属于报告对象；不以蓝框推定仓墙", 1060)
    source = json.loads((ROOT / "research/prosperity-r5/sima-road.json").read_bytes())
    box(root, 40, 122, 660, 620, rx=0)
    label(root, 60, 153, "2023年公开位置图的可读图元", 19, font_weight="700")
    # The exact original pixels are retained; the crop is only a display transform.
    scale, dx, dy = .62, -90, -282
    native = el(root, "g", transform=f"translate({dx} {dy}) scale({scale})",
                data_frame="frame-sima2023", data_city_registration="false")
    a = link(native, "segment-P01", "P01")
    a.set("data-source-path", "research/prosperity-r5/sima-road.json")
    for i, points in enumerate(source["image"]["sima_road_ink_px"]):
        path_line(a, points, stroke=GOLD, stroke_width=3 / scale,
                  data_source_pointer=f"/image/sima_road_ink_px/{i}", data_sima_atomic_line=i)
    bx1, by1, bx2, by2 = source["image"]["storage_box_centerline_px"]
    el(native, "rect", x=bx1, y=by1, width=bx2 - bx1, height=by2 - by1, fill="#edf1e6",
       stroke="#718a96", stroke_width=2 / scale, stroke_dasharray="9 7", data_source_pointer="/image/storage_box_centerline_px",
       data_role="source-region-box-not-wall")
    lines(root, bx1 * scale + dx + 10, by1 * scale + dy + 70, ["宫内", "仓窖区", "范围框", "不是墙线"], 16, 30, fill=BLUE)
    for landmark in source["landmarks"]:
        px, py = landmark["pixel"]
        el(native, "circle", cx=px, cy=py, r=5 / scale, fill="#fff", stroke="#789080", stroke_width=2 / scale,
           data_source_landmark=landmark["label"])
        lx, ly = (px * scale + dx + 14, py * scale + dy + 6) if landmark["label"] == "千秋门" else (px * scale + dx - 18, py * scale + dy - 15)
        label(root, lx, ly, landmark["label"], 16)
    gx, gy = source["image"]["gate_label_px"]
    road_label(root, "P01", gx * scale + dx - 42, gy * scale + dy + 29, "司马门内路 P01", 17)
    a = link(root, "finding-SI08")
    lines(a, 485, 259, ["六根原子线", "逐值沿用", "中间断口不补", "", "双线图距不能", "反算实际路宽"], 16, 28)
    lines(root, 60, 699, ["原图像素未经本批地理配准；原图蓝框不是新增的实测仓墙。"], 15)
    for rid, y, title, msgs in [
        ("P01", 122, "约40米 · 司马门内路", ["北魏路面最宽处。", "不是两墙之间的已测净距。"]),
        ("P07", 285, "约4.7米 · 宫院夹道", ["东北角院落的东围廊与", "宫院东墙之间，属宫院内部。"]),
        ("P08", 448, "约13米 · 仓区内路", ["宫内仓区南部的内部道路。", "不等同司马门内路。"]),
    ]:
        a = link(root, "segment-" + rid, rid)
        box(a, 728, y, 432, 145)
        label(a, 750, y + 36, title, 21, fill=GREEN, font_weight="700")
        lines(a, 750, y + 73, msgs, 18, 30)
    a = link(root, "segment-P11", "P11")
    box(a, 728, 611, 432, 131, fill="#eef0e4")
    label(a, 750, 648, "P11 · 宫城东墙外的道路局部", 20, fill=GREEN, font_weight="700")
    lines(a, 750, 683, ["宫外仓区另列；不接入宫内道路图。", "168口总勘探、13口发掘与3排须核范围。"], 16, 28)
    label(root, 40, 789, "空间次序另读：宫院东墙 → 司马门内路 → 宫内仓区西墙", 21, font_weight="700")
    for x, title, text in [(40, "宫院东墙", "东北角院落有发掘"), (424, "司马门内路 P01", "路面多期叠压"), (808, "仓区西墙", "西北角已有识别")]:
        group = link(root, "segment-P01", "P01") if x == 424 else link(root, "finding-SI01")
        box(group, x, 811, 352, 91)
        label(group, x + 18, 843, title, 19, font_weight="700")
        label(group, x + 18, 875, text, 16)
    lines(root, 40, 944, ["三对象的东西关系有据；同一横断面上的墙内缘、路边缘、净距与北魏使用层仍缺共同测线。",
                         "宫外仓窖的统计口径保留各自来源，不据窖数画同期房屋网格。516—528年的逐段同时通行仍待分层核验。",
                         "来源：2023考古队位置图；2017、2023、2024年度田野汇报；2026新华社与人民日报采访。点图元回查。"], 16, 31)
    return root


def build_maps(atlas, data):
    from city_nodes_r7_core_maps import palace_map, jianchun_map
    roots = {"overview": overview(atlas, data), "palace-yongning": palace_map(atlas, data),
             "baima": baima_map(atlas, data), "sima": sima_map(atlas, data), "jianchun": jianchun_map(atlas, data)}
    return {key: ET.tostring(root, encoding="unicode") for key, root in roots.items()}
