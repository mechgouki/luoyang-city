"""Publish two source-preserving backbone maps with the current water evidence index."""
import copy
import html
import json
import re
import shutil
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from dual_cartography import dump, load, sha
from north_b4 import render_atlas
from prosperity_anchors_p461 import ROOT, SITE, offline_page

FOLDER = "backbone-469"
SOURCE = ROOT / "research/prosperity-v4" / FOLDER
PAGE = "prosperity-backbone-p469.html"
PREVIOUS = "prosperity-water-p468.html"
VERSION = "prosperity-backbone-p469"
ATLAS = f"downloads/{FOLDER}.pdf"
BUNDLE = f"downloads/{FOLDER}.zip"
ENTRY = (f'<p id="p469-entry" style="border-left:4px solid #34685e;padding:1rem;background:#e8eee7">'
         f'<a href="./{PAGE}">续读 · 城市水陆骨架与水系证据联读</a></p>\n')
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
PAPER, INK, MUTED = "#faf8f1", "#263c34", "#60716a"
RULE, WALL, ROAD_H, ROAD_V, WATER = "#d8dcd0", "#aaa58d", "#a36042", "#356b5b", "#427b87"
WALL_IDS = ("geo-inner-wall-aboveground", "geo-inner-wall-underground", "geo-palace-walls")
GEO_PATH = "research/prosperity-v1/geographic-evidence.json"
NETWORK_PATH = "research/prosperity-v4/network-462/network.json"
ROAD_PATH = "research/prosperity-v4/network-462/roads.json"
OUTER_PATH = "research/prosperity-v4/network-462/outer.json"
NORTH_PATH = "research/prosperity-v4/gates-465/readings.json"
SOUTH_PATH = "research/prosperity-v4/south-466/readings.json"
WATER_PATHS = {"P467": "research/prosperity-v4/water-467/readings.json",
               "P468": "research/prosperity-v4/water-468/readings.json"}
INPUTS = (GEO_PATH, NETWORK_PATH, ROAD_PATH, OUTER_PATH, NORTH_PATH, SOUTH_PATH, *WATER_PATHS.values())
SOURCE_LINKS = {
    "06a": "https://whc.unesco.org/uploads/nominations/1442.pdf#page=3457",
    "qian": "https://www.jstage.jst.go.jp/article/actaasiatica/126/0/126_1262/_pdf/-char/en#page=17",
}


def esc(value):
    return html.escape(str(value), quote=True)


def slug(value):
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value)).strip("-")


def tag(parent, name, **attributes):
    return ET.SubElement(parent, f"{{{SVG_NS}}}{name}", {
        key.rstrip("_").replace("_", "-"): str(value)
        for key, value in attributes.items() if value is not None
    })


def text(parent, x, y, value, size=20, color=INK, **attributes):
    result = tag(parent, "text", x=x, y=y, font_size=size, fill=color, **attributes)
    result.text = str(value)
    return result


def wrap(value, width=36):
    lines, line, used = [], "", 0
    for character in str(value):
        weight = 2 if unicodedata.east_asian_width(character) in ("W", "F") else 1
        if character == "\n" or (line and used + weight > width):
            lines.append(line)
            line, used = "", 0
            if character == "\n":
                continue
        line += character
        used += weight
    if line:
        lines.append(line)
    return lines


def paragraph(parent, x, y, value, size=18, color=MUTED, width=40, leading=29):
    lines = wrap(value, width)
    for index, line in enumerate(lines):
        text(parent, x, y + index * leading, line, size, color)
    return y + len(lines) * leading


def path(parent, points, frame, source_path, kind, **attributes):
    # Keep every input vertex, each original part and the source coordinate units.
    d = " ".join(("M" if index == 0 else "L") + f"{point[0]} {point[1]}"
                 for index, point in enumerate(points))
    return tag(parent, "path", d=d, fill="none", data_source_frame=frame,
               data_source_path=source_path, data_source_kind=kind, **attributes)


def point(parent, xy, frame, source_path, kind, radius=5, **attributes):
    return tag(parent, "circle", cx=xy[0], cy=xy[1], r=radius,
               data_source_frame=frame, data_source_path=source_path,
               data_source_kind=kind, **attributes)


def base_plate(frame, number, title, subtitle, metadata):
    root = ET.Element(f"{{{SVG_NS}}}svg", {
        "id": frame, "viewBox": "0 0 1440 1160", "width": "1440", "height": "1160",
        "role": "img", "aria-labelledby": f"{frame}-title {frame}-description",
        "lang": "zh-CN", "data-source-frame": frame,
    })
    tag(root, "title", id=f"{frame}-title").text = title
    tag(root, "desc", id=f"{frame}-description").text = subtitle
    tag(root, "metadata").text = json.dumps(metadata, ensure_ascii=False)
    tag(root, "style").text = """
    text {font-family:'Noto Sans CJK SC','Microsoft YaHei',sans-serif}
    .strong {font-weight:700} .map-label {font-weight:500}
    .context-link {cursor:pointer} .context-link:focus {outline:none}
    .context-link:focus circle,.context-link.is-selected circle {stroke:#b46d24;stroke-width:.9}
    .context-link.is-selected path {stroke:#b46d24;stroke-width:1.2}
    """
    tag(root, "rect", width=1440, height=1160, fill=PAPER)
    text(root, 48, 43, f"盛时洛阳  /  P4.6.9  /  来源骨架 {number:02d}", 18, MUTED)
    text(root, 48, 101, title, 42, INK, class_="strong")
    text(root, 48, 141, subtitle, 19, MUTED)
    return root


def legend_line(parent, x, y, label, color, dashed=False):
    tag(parent, "line", x1=x, y1=y-6, x2=x+31, y2=y-6, stroke=color,
        stroke_width=4, stroke_dasharray="7 5" if dashed else None)
    text(parent, x+46, y, label, 19)


def frame_06a(inputs, data):
    geo, network, roads = inputs["geo"], inputs["network"], inputs["roads"]
    features = {feature["id"]: feature for feature in geo["features"]}
    navigation = {item["mapped_feature_id"]: item for item in data["water_evidence_navigation"]}
    gate_ids = [gate["id"] for gate in network["gates"]]
    road_ids = [route["p1_feature_id"] for route in roads["routes"]]
    feature_ids = [*WALL_IDS, *road_ids, *gate_ids, "geo-modern-luo-river"]
    root = base_plate("frame-06a", 1, "城墙、门址与八条道路遗存",
                      "同一来源：管理规划图 06a · 道路与墙线保留原图分段，水道文献另在证据栏联读。",
                      {"source_frame_id": "frame-06a", "source": GEO_PATH,
                       "source_pdf_page": 3457, "native_units": "PDF point", "crs": geo["crs"],
                       "rendered_feature_ids": feature_ids, "new_historical_geometry": 0})
    tag(root, "rect", x=48, y=174, width=822, height=830, rx=12, fill="#f0f1e8", stroke=RULE)
    tag(root, "rect", x=894, y=174, width=498, height=830, rx=12, fill="#f4f2e8", stroke=RULE)
    defs = tag(root, "defs")
    clip = tag(defs, "clipPath", id="frame-06a-clip")
    tag(clip, "rect", x=49, y=175, width=820, height=828, rx=10)
    clipped = tag(root, "g", clip_path="url(#frame-06a-clip)")
    group = tag(clipped, "g", id="native-06a-geometry",
                transform="translate(66 190) scale(3.9) translate(-238 -228)",
                data_native_units="PDF point", data_source_frame="frame-06a")
    for index, feature_id in enumerate(WALL_IDS):
        feature = features[feature_id]
        wall = tag(group, "g", id="p469-"+feature_id)
        tag(wall, "title").text = feature["label"] + "；" + feature["source_historical_period"]
        for part, coordinates in enumerate(feature["source_pdf_geometry"]["coordinates"], 1):
            path(wall, coordinates, "frame-06a", f"{GEO_PATH}#{feature_id}/part/{part}", "site-remains",
                 stroke=WALL, stroke_width=(1.4, .75, 1.1)[index],
                 stroke_dasharray="1.4 .7" if index == 1 else None,
                 data_source_feature_id=feature_id, data_part=part)
    river = features["geo-modern-luo-river"]
    modern = tag(group, "g", id="modern-river-469", data_period="1997/1999",
                 data_not_ancient_river="true", data_source_frame="frame-06a", style="display:none",
                 aria_hidden="true")
    tag(modern, "title").text = "1997年航摄、1999年实测底图的近现代洛河中东段概略线，不是北魏河岸"
    path(modern, river["source_pdf_geometry"]["coordinates"], "frame-06a",
         GEO_PATH+"#geo-modern-luo-river", "modern-reference", stroke="#8e9d9c", stroke_width=1.2,
         stroke_dasharray="3 1.3", data_source_feature_id=river["id"])
    text(modern, 273, 422, "洛河参照 · 1997／1999", 4.1, "#647e80", class_="map-label")
    labels = {"Lh-1": (255, 384), "Lh-2": (255, 328), "Lh-3": (255, 295), "Lh-4": (255, 267),
              "Lz-1": (359, 401), "Lz-2": (340, 398), "Lz-3": (311, 400), "Lz-4": (286, 398)}
    for route in roads["routes"]:
        code, feature_id = route["code"], route["p1_feature_id"]
        feature = features[feature_id]
        attrs = {"id": "p469-road-"+code, "data_road": code}
        if feature_id in navigation:
            attrs.update(href="#context-"+feature_id, data_context_id=feature_id,
                         class_="context-link", aria_label=route["title"]+"：查看相关水道证据")
            road = tag(group, "a", **attrs)
        else:
            road = tag(group, "g", **attrs)
        tag(road, "title").text = code + " · " + route["title"] + "；" + feature["source_historical_period"]
        color = ROAD_H if code.startswith("Lh") else ROAD_V
        for part, coordinates in enumerate(feature["source_pdf_geometry"]["coordinates"], 1):
            path(road, coordinates, "frame-06a", f"{GEO_PATH}#{feature_id}/part/{part}", "site-remains",
                 stroke=color, stroke_width=.8, data_source_feature_id=feature_id, data_part=part)
        text(road, *labels[code], code, 4.1, color, class_="map-label", font_weight="700")
    offsets = {
        "geo-changhe-palace-gate": (3.0,-3.0,"start"), "geo-qianqiu-gate": (-2.4,-2.3,"end"),
        "geo-yunlong-gate": (2.6,-1.9,"start"), "geo-jianchun-gate": (3,-2,"start"),
        "geo-daxia-gate": (-2.5,-3,"end"), "geo-guangmo-gate": (2,-3,"start"),
        "geo-xiyang-gate": (2,-3.5,"start"), "geo-dongyang-gate": (2,-3,"start"),
        "geo-qingyang-gate": (2,-3,"start"), "geo-ximing-gate": (2,-3,"start"),
    }
    for gate in network["gates"]:
        feature_id = gate["id"]
        feature = features[feature_id]
        xy = feature["source_pdf_geometry"]["coordinates"]
        attrs = {"id": "p469-"+feature_id}
        if feature_id in navigation:
            attrs.update(href="#context-"+feature_id, data_context_id=feature_id,
                         class_="context-link", aria_label=gate["name"]+"：查看相关水道证据")
            mark = tag(group, "a", **attrs)
        else:
            mark = tag(group, "g", **attrs)
        tag(mark, "title").text = gate["name"] + "；来源图符中心，不是水口或桥位"
        point(mark, xy, "frame-06a", GEO_PATH+"#"+feature_id, "source-symbol", radius=1.25,
              fill=PAPER, stroke=INK, stroke_width=.5, data_source_feature_id=feature_id)
        dx, dy, anchor = offsets[feature_id]
        label = gate["name"].replace("内城", "").replace("宫城", "")
        text(mark, xy[0]+dx, xy[1]+dy, label, 4.1, INK, text_anchor=anchor, class_="map-label")
    text(group, 319, 298, "宫城", 5.8, MUTED, text_anchor="middle", class_="map-label")
    text(group, 307, 409, "南墙、宣阳门位置未补", 4, MUTED, class_="map-label")
    text(root, 78, 211, "N", 19, INK, font_weight="700")
    tag(root, "path", d="M85 252 L85 223 M78 233 L85 223 L92 233", fill="none", stroke=INK, stroke_width=2)
    sx = 922
    text(root, sx, 216, "一张原图，保留多种证据", 26, INK, class_="strong")
    legend_line(root, sx, 263, "横向道路原图子线", ROAD_H)
    legend_line(root, sx, 307, "纵向道路原图子线", ROAD_V)
    legend_line(root, sx, 351, "内城、宫城墙线遗存", WALL)
    tag(root, "circle", cx=sx+15, cy=389, r=6, fill=PAPER, stroke=INK, stroke_width=2)
    text(root, sx+46, 395, "门址图符中心", 19)
    legend_line(root, sx, 439, "近现代洛河参照", "#8e9d9c", True)
    text(root, sx, 491, "图线的年代", 23, INK, class_="strong")
    paragraph(root, sx, 526, "遗存附表涵盖东汉、魏晋至北魏。它们构成盛时布局参照，不能证明516—528年每年运行状态相同。", width=46)
    text(root, sx, 658, "留白的含义", 23, INK, class_="strong")
    paragraph(root, sx, 692, "保留道路断笔；不补内城南墙、宫城北缘或宣阳门。不把城门图符当作水口、桥头。", width=46)
    text(root, sx, 815, "点门址，读水道", 23, ROAD_V, class_="strong")
    paragraph(root, sx, 849, "网页可点门址与铜驼街，查看文献中的门北、门东、街侧关系。相对水道没有画成定位河线。", width=46)
    tag(root, "line", x1=48, y1=1027, x2=1392, y2=1027, stroke=RULE, stroke_width=2)
    text(root, 48, 1061, "来源：2012管理规划图06a，UNESCO申遗PDF第3457页；编号对照图04、遗存附表。", 18, MUTED)
    text(root, 48, 1093, "坐标保持原PDF点；既有配准为西安1980（EPSG:4610）。本图未新增地面控制、古岸线或量测。", 18, MUTED)
    text(root, 48, 1125, "洛河线只表示1997／1999底图的可辨中东段；图线缺口与交会均不自动认定为古桥或实际路口。", 18, MUTED)
    return root, feature_ids


def frame_qian(inputs):
    north, south, outer = inputs["north"]["later_plan"], inputs["south"]["plan"], inputs["outer"]
    root = base_plate("frame-qian2018", 2, "南北道路与古洛水图带同框对读",
                      "同一来源：钱国祥2018图一，朱岩石2024图6转载 · 这是复原图读数，地面位置另待证明。",
                      {"source_frame_id": "frame-qian2018", "native_units": "source image pixel",
                       "image_size_px": [1145,951], "source_pdf_page": 17,
                       "crs": None, "new_historical_geometry": 0,
                       "png_sha256": inputs["south"]["sources"]["q18"]["png_sha256"]})
    tag(root, "rect", x=48, y=174, width=984, height=830, rx=12, fill="#f0f1e8", stroke=RULE)
    tag(root, "rect", x=1052, y=174, width=340, height=830, rx=12, fill="#f4f2e8", stroke=RULE)
    group = tag(root, "g", id="native-qian-geometry", transform="translate(66 196) scale(.82)",
                data_source_frame="frame-qian2018", data_native_units="source image pixel")
    def trace(coords, source_path, color, width=4, kind="source-sample", **attrs):
        return path(group, coords, "frame-qian2018", source_path, kind,
                    stroke=color, stroke_width=width, **attrs)
    trace(north["inner_wall_px"], "gates-465:later_plan.inner_wall_px", WALL, 5, "later-reconstruction")
    trace(north["outer_wall_px"], "gates-465:later_plan.outer_wall_px", WALL, 5, "later-reconstruction")
    text(group, 432, 39, "北郭图示摘段", 19, MUTED, class_="map-label")
    trace(north["west"]["trace_px"], "gates-465:later_plan.west.trace_px", ROAD_H, 4)
    text(group, 435, 194, "承明门西截绘段", 19, ROAD_H, text_anchor="end", class_="map-label")
    for route in north["north"]:
        for key in ("to_wall_px", "beyond_wall_to_frame_px"):
            trace(route[key], f"gates-465:later_plan.north.{route['id']}.{key}", ROAD_V, 4)
        xy = route["to_wall_px"][0]
        point(group, xy, "frame-qian2018", f"gates-465:later_plan.north.{route['id']}.to_wall_px[0]",
              "source-symbol", 5, fill=PAPER, stroke=ROAD_V, stroke_width=2)
        dx, dy, anchor = (-12,27,"end") if route["id"] == "VI" else (12,27,"start")
        text(group, xy[0]+dx, xy[1]+dy, route["name"], 20, ROAD_V, text_anchor=anchor, class_="map-label")
    text(group, 625, -3, "两线在原图边缘仍分开", 18, MUTED, text_anchor="middle", class_="map-label")
    text(group, 602, 322, "内城", 29, MUTED, text_anchor="middle")
    text(group, 602, 354, "未摘绘的墙段与路段留白", 18, MUTED, text_anchor="middle")
    for corridor in outer["corridors"]:
        code = corridor["id"]
        for key in ("outer_station_px", "inner_station_px"):
            xy = corridor[key]
            point(group, xy, "frame-qian2018", f"network-462:outer.corridors.{code}.{key}",
                  "endpoint-only", 6, fill=PAPER, stroke=ROAD_H, stroke_width=2,
                  data_corridor=code, data_endpoint=key)
            label = code if key == "outer_station_px" else code+" · "+corridor["inner_gate"].replace("内城", "")
            if key == "inner_station_px":
                anchor, dx = ("end", -12) if code.startswith("W") else ("start", 12)
            else:
                anchor, dx = ("start", 12) if code.startswith("W") else ("end", -12)
            text(group, xy[0]+dx, xy[1]-12, label, 18, ROAD_H, text_anchor=anchor, class_="map-label")
    for name, samples in south["road_samples_px"].items():
        trace(samples, f"south-466:plan.road_samples_px.{name}", ROAD_V, 4)
        x, y = samples[0]
        dx, anchor = {"津阳":(-8,"end"), "宣阳":(-4,"end"), "平昌":(0,"end"), "开阳":(8,"start")}[name]
        text(group, x+dx, y-16, name, 20, ROAD_V, text_anchor=anchor, class_="map-label")
    for name in ("north_bank_sample_px", "south_bank_sample_px"):
        trace(south[name], "south-466:plan."+name, WATER, 4, "later-reconstruction",
              stroke_dasharray="8 4")
    trace(south["bridge_symbol_ends_px"], "south-466:plan.bridge_symbol_ends_px", "#78658b", 7, "source-symbol",
          data_not_excavated_landing="true")
    text(group, 547, 678, "永桥图符", 20, "#78658b", text_anchor="end", class_="map-label")
    offsets = {"灵台": (-12,-16,"end"), "明堂": (-8,29,"end"), "辟雍": (0,28,"middle"), "太学": (12,-9,"start")}
    for name, xy in south["places_px"].items():
        point(group, xy, "frame-qian2018", "south-466:plan.places_px."+name,
              "source-symbol", 4, fill=INK, stroke=PAPER, stroke_width=1)
        dx, dy, anchor = offsets[name]
        text(group, xy[0]+dx, xy[1]+dy, name, 19, INK, text_anchor=anchor, class_="map-label")
    text(group, 378, 764, "原图古洛水河带摘段", 22, WATER)
    text(group, 378, 796, "两岸样线不代表本轮测得的古岸线", 18, MUTED)
    scale = south["scale_endpoints_px"]
    trace(scale, "south-466:plan.scale_endpoints_px", INK, 3, "source-scale")
    for xy in scale:
        tag(group, "line", x1=xy[0], y1=xy[1]-7, x2=xy[0], y2=xy[1]+7, stroke=INK, stroke_width=2)
    text(group, (scale[0][0]+scale[1][0])/2, scale[0][1]-17, "原图 1 公里", 17, INK, text_anchor="middle")
    text(group, 34, 875, "W1—W3、E1—E3：同号只表示一对门端读点", 19, ROAD_H)
    text(group, 34, 908, "门端没有连成实测道路；图面直线距离也不是连续钻探路长。", 18, MUTED)
    text(root, 79, 225, "N", 19, INK, font_weight="700")
    tag(root, "path", d="M86 266 L86 237 M79 247 L86 237 L93 247", fill="none", stroke=INK, stroke_width=2)
    sx = 1076
    text(root, sx, 216, "三组读图，可同框", 23, INK, class_="strong")
    y = paragraph(root, sx, 254, "北路与承明门西短线来自P465；南路、河带与桥符来自P466；东西门端来自P462。", width=29, size=18)
    text(root, sx, y+28, "保留原图像素", 22, INK, class_="strong")
    y = paragraph(root, sx, y+64, "三组均取同一1145×951嵌入图。图尺92像素＝原图1公里，不是新增地面量测。", width=29)
    text(root, sx, y+28, "图上仍不知道", 22, INK, class_="strong")
    y = paragraph(root, sx, y+64, "承明门以西最后实测点、北路终点与合流点、永桥桥头，以及可归入516—528年的古岸段。", width=29)
    text(root, sx, y+28, "没有跨图配准", 22, WATER, class_="strong")
    paragraph(root, sx, y+64, "本图与左册06a各自独立。古洛水图带没有投到06a，也没有换成现代经纬度。", width=29)
    tag(root, "line", x1=48, y1=1027, x2=1392, y2=1027, stroke=RULE, stroke_width=2)
    text(root, 48, 1061, "图源：钱国祥《汉魏洛阳城城门与宫院门的考察研究》2018图一；朱岩石2024印页17图6转载。", 18, MUTED)
    text(root, 48, 1093, "摘绘线端为现有读图范围；古洛水为学者复原图的图带，永桥为制图符号，均非新确定的北魏地面位置。", 18, MUTED)
    text(root, 48, 1125, "北魏盛时相关证据逐条另列；辟雍180米引水干道未接入此图，其516—528年通水情况仍待证。", 18, MUTED)
    return root


def input_data():
    return {"geo": load(ROOT/GEO_PATH), "network": load(ROOT/NETWORK_PATH), "roads": load(ROOT/ROAD_PATH),
            "outer": load(ROOT/OUTER_PATH), "north": load(ROOT/NORTH_PATH), "south": load(ROOT/SOUTH_PATH)}


def ref_of(record):
    for key in ("ref", "reference", "id", "key", "uid", "relation_ref"):
        value = record.get(key)
        if isinstance(value, str) and value.startswith(("P467/", "P468/")):
            return value
    version = str(record.get("source_version", record.get("version", record.get("edition", ""))))
    version = "P467" if "467" in version else "P468" if "468" in version else version
    plate = record.get("plate_id", record.get("plate"))
    segment = record.get("segment_id", record.get("id"))
    return f"{version}/{plate}/{segment}" if version in WATER_PATHS and plate and segment else None


def relation_catalog(data):
    catalog, sources = {}, {}
    for version, relative in WATER_PATHS.items():
        water = load(ROOT/relative)
        sources[version] = {item["id"]: item for item in water["sources"]}
        for plate in water["plates"]:
            for segment in plate["segments"]:
                ref = f"{version}/{plate['id']}/{segment['id']}"
                record = {key: copy.deepcopy(value) for key, value in segment.items()
                          if key not in ("points", "x", "y", "label_position")}
                record.update(ref=ref, version=version, plate_id=plate["id"], plate_title=plate["title"])
                catalog[ref] = record
    records = data.get("current_relations", [])
    if isinstance(records, dict):
        records = [dict(value, ref=key) for key, value in records.items()]
    for record in records:
        ref = ref_of(record)
        if ref in catalog:
            catalog[ref].update({key: value for key, value in record.items()
                                 if key not in ("points", "x", "y", "label_position")})
            catalog[ref]["ref"] = ref
    correction = data["corrected_current_I09"]
    i09 = catalog["P467/inner/I09"]
    i09.update(quote=correction["quote"], legacy_water_ids=correction["legacy_water_ids"],
               reading=correction.get("meaning", correction.get("reading", i09["reading"])),
               annual_flow_516_528_confirmed=False)
    assert not {"W20", "W21"} & set(i09["legacy_water_ids"])
    assert "若旱" in i09["quote"] and "滂潤" in i09["quote"]
    return catalog, sources


def source_html(record, sources):
    version = record["version"]
    result = []
    current_sources = {item["id"]: item for item in record.get("sources", [])}
    for source_id in record.get("source_ids", []):
        source = current_sources.get(source_id, sources.get(version, {}).get(source_id))
        if not source:
            continue
        label = source.get("title", source_id)
        url = source.get("url", "")
        result.append(f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>' if url else esc(label))
    return "；".join(result)


def evidence_id(ref):
    return "evidence-" + slug(ref)


def relation_link(ref, catalog):
    item = catalog.get(ref)
    if not item:
        return esc(ref)
    return f'<a href="#{evidence_id(ref)}" data-current-ref="{esc(ref)}">{esc(item["version"])} {esc(item.get("id", ref.rsplit("/",1)[-1]))} · {esc(item.get("label", "证据"))}</a>'


def context_html(data, inputs, catalog, sources):
    feature_names = {feature["id"]: feature["label"].replace("位置参考", "").replace("图示残段", "")
                     for feature in inputs["geo"]["features"]}
    options, buttons, articles = ['<option value="">全部9处参照</option>'], [], []
    for row in data["water_evidence_navigation"]:
        feature_id = row["mapped_feature_id"]
        name = feature_names.get(feature_id, feature_id)
        options.append(f'<option value="{esc(feature_id)}">{esc(name)}</option>')
        buttons.append(f'<button type="button" data-context-choice="{esc(feature_id)}" aria-pressed="false">{esc(name)}</button>')
        entries = []
        for ref in row["evidence_refs"]:
            record = catalog[ref]
            source_page = record.get("page", f'prosperity-water-{record["version"].lower()}.html#map={record["plate_id"]}&layer=all')
            entries.append(f'<li data-evidence-ref="{esc(ref)}"><h4>{relation_link(ref, catalog)}</h4><blockquote>{esc(record.get("quote", ""))}</blockquote>'
                           f'<p>{esc(record.get("reading", ""))}</p><p class="boundary">{esc(record.get("limit", ""))}</p>'
                           f'<p class="source-line">{source_html(record, sources)}</p>'
                           f'<p class="source-line"><a href="./{esc(source_page)}">打开原分册关系图与上下文</a></p></li>')
        articles.append(f'<article class="context-card" id="context-{esc(feature_id)}" data-context-card="{esc(feature_id)}">'
                        f'<p class="eyebrow">地理参照 × 相对关系</p><h3>{esc(name)}</h3>'
                        f'<p class="boundary">{esc(row.get("limit", "关联只指文献上下文，不为水体新增位置。"))}</p>'
                        '<p>下列水道关系单独阅读；所选门道的图上位置没有赋给河渠、池口或桥头。</p>'
                        f'<ul class="context-evidence">{"".join(entries)}</ul></article>')
    return "".join(options), "".join(buttons), "".join(articles)


def water_table(data, catalog):
    rows = []
    for row in data["current_water_ledger"]:
        water_id = row["id"]
        current = row.get("current_record", {})
        current = current if isinstance(current, dict) else {"状态": str(current)}
        refs = [ref for ref, record in catalog.items() if water_id in record.get("legacy_water_ids", [])]
        explicit = row.get("evidence_refs", row.get("current_refs", []))
        if explicit:
            refs = [ref for ref in explicit if ref in catalog]
        if water_id in ("W20", "W21"):
            refs = [ref for ref in refs if ref != "P467/inner/I09"]
        links = "<br>".join(relation_link(ref, catalog) for ref in refs)
        plate_id = current.get("本册图")
        if not links and plate_id:
            plate_title = next((record["plate_title"] for record in catalog.values()
                                if record["version"] == "P468" and record["plate_id"] == plate_id), "主题关系图")
            links = f'<a href="./prosperity-water-p468.html#map={esc(plate_id)}&amp;layer=all">P468 · {esc(plate_title)}</a>'
        if not links:
            links = "近现代地理参照单列" if row.get("modern_only") else "详见分册原文、关系与分期"
        status = row.get("status", current.get("状态", "已核相对关系；完整岸线与池口仍未定位"))
        if isinstance(status, dict):
            status = json.dumps(status, ensure_ascii=False)
        note = ""
        if water_id == "W20":
            note = '<p class="withdrawal">撤回旧I09索引；现采用长秋寺北、夏水冬竭。</p>'
        elif water_id == "W21":
            note = '<p class="withdrawal">撤回旧I09索引；现采用西游园凌云台下，不解作台南。</p>'
        elif water_id == "W02":
            note = '<p class="withdrawal">1997／1999底图，不计入古水系通水。</p>'
        rows.append(f'<tr id="water-{esc(water_id)}" data-water-id="{esc(water_id)}" data-water-name="{esc(row["name"])}">'
                    f'<th scope="row"><span class="record-id">{esc(water_id)}</span> {esc(row["name"])}</th>'
                    f'<td>{esc(status)}{note}</td><td class="evidence-links">{links}</td></tr>')
    return "".join(rows)


def evidence_html(catalog, sources):
    relation_names = {"flow":"水流", "connection":"相连", "adjacency":"方位相邻", "containment":"所属／范围", "hypothesis":"解释方案", "stratigraphy":"地层关系", "proposal":"拟议工程"}
    period_names = {"text_context":"文献上下文", "older_event":"较早事件", "broad_survey":"较宽年代调查", "interpretation":"学者解释", "proposal":"规划建议，未据此认定已实施"}
    output = []
    for ref, record in catalog.items():
        quote = record.get("quote", "")
        output.append(f'<details class="evidence-record" id="{evidence_id(ref)}">'
                      f'<summary><span class="record-id">{esc(record["version"])} {esc(record.get("id", ref.rsplit("/",1)[-1]))}</span>'
                      f'<span>{esc(record.get("label", "证据关系"))}</span>'
                      f'<span class="tag">{esc(relation_names.get(record.get("relationship_type"), record.get("relationship_type", "关系")))}</span></summary>'
                      f'<div class="evidence-body"><p class="source-line">{esc(record["plate_title"])} · '
                      f'{esc(period_names.get(record.get("period_class"), record.get("period_class", "时层另核")))}</p>'
                      f'<blockquote>{esc(quote)}</blockquote><p>{esc(record.get("reading", ""))}</p>'
                      f'<p class="boundary">{esc(record.get("limit", ""))}</p>'
                      f'<p class="source-line">出处：{esc(record.get("locator", ""))}</p>'
                      f'<p class="source-line">{source_html(record, sources)}</p></div></details>')
    return "".join(output)


def unknowns_html(data):
    records = data.get("unknowns", [])
    if isinstance(records, dict):
        labels = {
            "inner_south_wall_geometry": "内城南墙：暂不补绘连续墙线。",
            "xuanyang_gate_geographic_coordinates": "宣阳门：文献方位可读，地理坐标未确定。",
            "yongqiao_bank_landings": "永桥两岸桥头：原图桥符号不替代考古登陆点。",
            "north_road_confluence_coordinates": "两条邙山北路合流位置：原图边缘仍分开，地面交会点未定。",
            "chengming_westernmost_survey_station": "承明门以西最后实测点：待原刊探孔或实测编号与图线对回。",
            "daxia_last_field_station": "大夏门北路调查终点：目前只有后出复原图读段，最后实测点未定。",
            "guangmo_last_field_station": "广莫门北路调查终点：目前只有后出复原图读段，最后实测点未定。",
            "yinluo_section_width_m": "城南引洛渠渠宽：2022年报告暂缓，尚未取得可核剖线与钻孔的折页。",
            "yinluo_section_depth_m": "城南引洛渠渠深、淤积界面与断代：留待同一剖面与平面图核合。",
            "biyong_flow_516_528": "辟雍引水干道：残长180米属于辟雍，其516—528年通水情况仍待证。",
            "ward_gate_to_central_cross_m": "白马寺北里坊南门至中央十字：接续关系可记，距离和连续揭露范围未明。",
        }
        records = [labels[key] for key in records if key in labels]
    if not records:
        records = [
            "城南引洛渠的剖线、钻孔与渠宽渠深：2022年报告暂缓，保留津阳门外大街东侧的已核关系。",
            "可归入516—528年的古洛河北岸岸段与永桥桥头：尚无本轮可定位几何。",
            "承明门以西最后实测点、两条邙山北路终点及其合流位置：原刊实测依据仍待补。",
            "辟雍残长180米引水干道：属于辟雍；其北魏盛时通水状况仍待证。",
        ]
    output = []
    for record in records:
        if isinstance(record, str):
            output.append(f"<li>{esc(record)}</li>")
        else:
            title = record.get("title", record.get("label", record.get("id", "待核问题")))
            body = record.get("detail", record.get("reason", record.get("status", record.get("limit", record.get("next_step", "")))))
            output.append(f"<li><strong>{esc(title)}</strong><p>{esc(body)}</p></li>")
    return "".join(output)


def road01_html(data):
    road = data.get("road01")
    if not road:
        return ""
    sources = {source["id"]: source for source in road.get("sources", [])}
    links = "；".join(f'<a href="{esc(sources[key]["url"])}" target="_blank" rel="noopener">{esc(sources[key]["title"])}</a>'
                     for key in ("cass2025", "rmrb2026") if key in sources)
    return ('<article class="research-update" id="road01-update"><p class="eyebrow">本轮补核 · 白马寺北里坊</p>'
            '<h2>门道接续可记，门到十字的距离仍空着</h2>'
            '<p>公开发掘文字记西阳门外大道北缘约7.5米缺口，向北接坊内居中纵街。结合前一年度三纵三横的报告，可保留通向中央十字的接续关系；没有证据把中间全段画成连续揭露。</p>'
            '<p>7.5米为报道的开口宽度；22米是居中纵街宽度，40米和86米是另述街间距离。这些数字没有代入坊门至中央十字的长度，也未加入本册两幅来源图的坐标。</p>'
            '<p class="boundary">现有资料归北魏，尚未把相关使用层独立细分到516—528年。总平面、比例尺与门到中央交点的距离继续待核。</p>'
            f'<p class="source-line">{links}</p></article>')


def audit_downloads_html():
    return "".join(f'<a href="./{FOLDER}/{esc(path.name)}" download>{esc(path.name)}</a>'
                   for path in sorted(SOURCE.glob("*.json")) if path.name != "readings.json")


def render_page(data, inputs, plates, catalog, sources):
    options, buttons, contexts = context_html(data, inputs, catalog, sources)
    correction = data["corrected_current_I09"]
    template = (SOURCE/"index.html").read_text(encoding="utf-8")
    replacements = {
        "<!-- FRAME_06A -->": ET.tostring(plates[0], encoding="unicode"),
        "<!-- FRAME_QIAN -->": ET.tostring(plates[1], encoding="unicode"),
        "<!-- CONTEXT_OPTIONS -->": options,
        "<!-- CONTEXT_BUTTONS -->": buttons,
        "<!-- CONTEXT_CARDS -->": contexts,
        "<!-- WATER_ROWS -->": water_table(data, catalog),
        "<!-- EVIDENCE_RECORDS -->": evidence_html(catalog, sources),
        "<!-- I09_QUOTE -->": esc(correction["quote"]),
        "<!-- I09_MEANING -->": esc(correction.get("meaning", correction.get("reading", "华林园池群旱涝条件下的供排水总说。"))),
        "<!-- UNKNOWNS -->": unknowns_html(data),
        "<!-- ROAD01_UPDATE -->": road01_html(data),
        "<!-- AUDIT_DOWNLOADS -->": audit_downloads_html(),
    }
    for marker, value in replacements.items():
        if template.count(marker) != 1:
            raise ValueError(f"P469 template marker must occur once: {marker}")
        template = template.replace(marker, value)
    return template


def build(site=SITE):
    site = Path(site)
    data = load(SOURCE/"readings.json")
    inputs = input_data()
    if len(data["current_water_ledger"]) != 34 or len(data["water_evidence_navigation"]) != 9:
        raise ValueError("P469 requires the 34-object current index and nine context-only map links")
    if inputs["geo"]["crs"] != "EPSG:4610":
        raise ValueError("Review the source CRS before changing the P469 map")
    if (inputs["north"]["later_plan"]["size_px"] != [1145,951]
            or inputs["south"]["plan"]["image_size_px"] != [1145,951]):
        raise ValueError("The two Qian readings must share the same source raster")
    if inputs["north"]["later_plan"]["scale_endpoints_px"] != inputs["south"]["plan"]["scale_endpoints_px"]:
        raise ValueError("The Qian source scale differs")
    catalog, sources = relation_catalog(data)
    if len(catalog) != 100:
        raise ValueError("P469 current evidence must preserve the 100 reviewed relationships")
    before_sources = {relative: sha(ROOT/relative) for relative in INPUTS}
    dest = site/FOLDER
    dest.mkdir(parents=True, exist_ok=True)
    (site/"downloads").mkdir(parents=True, exist_ok=True)
    first, feature_ids = frame_06a(inputs, data)
    second = frame_qian(inputs)
    plates = (first, second)
    paths = [dest/"frame-06a.svg", dest/"frame-qian2018.svg"]
    for diagram, filename in zip(plates, paths):
        ET.indent(diagram)
        ET.ElementTree(diagram).write(filename, encoding="utf-8", xml_declaration=True)
    render_atlas(paths, site/ATLAS)
    copied = []
    for source_path in [*sorted(SOURCE.glob("*.json")), SOURCE/"study.css", SOURCE/"backbone-ui.js"]:
        shutil.copyfile(source_path, dest/source_path.name)
        copied.append(dest/source_path.name)
    page = render_page(data, inputs, plates, catalog, sources)
    (site/PAGE).write_text(page, encoding="utf-8")
    previous = site/PREVIOUS
    original = previous.read_text(encoding="utf-8").replace(ENTRY, "")
    marker = '<section id="explore"'
    if original.count(marker) != 1 or "P4.6.8" not in original:
        raise ValueError("Review P468 before adding the P469 continuation")
    previous.write_text(original.replace(marker, ENTRY+marker, 1), encoding="utf-8")
    info, release = load(site/"build-info.json"), load(site/"release.json")
    release["extensions"] = sorted(set(release["extensions"]) | {VERSION})
    release["prosperity_backbone_p469_version"] = VERSION
    release["current_milestone"] = "盛时 P4.6.9 · 城市水陆骨架与水系证据联读"
    dump(site/"release.json", release)
    bundle_manifest = {
        "version": VERSION, "source_commit": info["source_commit"], "page": PAGE,
        "atlas": ATLAS, "atlas_pages": 2, "source_inputs_sha256": before_sources,
        "files_sha256": {path.relative_to(site).as_posix(): sha(path) for path in [*paths, *copied, site/ATLAS]},
        "new_historical_coordinates": 0, "new_metric_measurements": 0,
    }
    dump(dest/"bundle-manifest.json", bundle_manifest)
    with zipfile.ZipFile(site/BUNDLE, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("index.html", offline_page(page, FOLDER, ATLAS))
        for path in [*paths, *copied, site/ATLAS, dest/"bundle-manifest.json"]:
            archive.write(path, path.relative_to(site).as_posix())
    info["prosperity_backbone_p469"] = {
        "version": VERSION, "source_commit": info["source_commit"], "page": PAGE,
        "atlas": ATLAS, "atlas_pages": 2, "bundle": BUNDLE, "package": BUNDLE,
        "readings": f"{FOLDER}/readings.json", "plates": [path.name for path in paths],
        "entry_id": "p469-entry", "source_frames": ["frame-06a", "frame-qian2018"],
        "rendered_06a_feature_ids": feature_ids, "current_water_objects": 34,
        "context_links": 9, "current_relations": len(catalog),
        "geographic_coordinates_added": 0, "new_metric_measurements": 0,
        "new_516_528_bank_geometry": None, "approved_h2_changed": False,
        "source_inputs_sha256": before_sources,
        "correction": {"previous_segment": "P467/inner/I09", "withdrawn_legacy_ids": ["W20", "W21"],
                       "conditional_flow_preserved": True, "archived_bytes_changed": False},
        "data_files": [path.relative_to(site).as_posix() for path in copied if path.suffix == ".json"]
                      + [f"{FOLDER}/bundle-manifest.json"],
    }
    changed = [*paths, *copied, site/PAGE, previous, site/ATLAS, site/BUNDLE,
               dest/"bundle-manifest.json", site/"release.json"]
    for path in changed:
        info["files_sha256"][path.relative_to(site).as_posix()] = sha(path)
    if any(sha(ROOT/relative) != before for relative, before in before_sources.items()):
        raise ValueError("P469 must not mutate its archived source evidence")
    dump(site/"build-info.json", info)
    return info["prosperity_backbone_p469"]


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
