"""Publish the shared 06a city view while retaining source and relation scopes."""
from __future__ import annotations

import copy
import csv
import hashlib
import html
import io
import json
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from city_common_470_data import build_data
from prosperity_anchors_p461 import offline_page

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
FOLDER = "common-470"
SOURCE = ROOT / "research/prosperity-v4" / FOLDER
PAGE = "prosperity-city-common.html"
PREVIOUS = "prosperity-backbone-p469.html"
VERSION = "prosperity-city-common-p470"
BUNDLE = f"downloads/{FOLDER}.zip"
MANIFEST = f"{FOLDER}/bundle-manifest.json"
OFFICIAL = "https://mechgouki.github.io/luoyang-city/"
ENTRY = ('<aside id="p470-entry" style="border-left:4px solid #285e4c;padding:1.2rem 1.4rem;'
         'background:#e8ede2;margin:1.5rem 0"><strong>继续 · 城市骨架与建筑共同视图</strong>'
         f'<p><a href="./{PAGE}">在同一来源图中查看太极殿、阊阖门、建春门与永宁寺 →</a>'
         '　联读宫前、建春门与洛南三组城市关系。</p></aside>\n')
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
PAPER, INK, MUTED = "#fbfaf5", "#243e35", "#627265"
WALL, ROAD_H, ROAD_V, TEMPLE = "#a5a28b", "#a45b3d", "#38715c", "#94723c"
GEO_PATH = "research/prosperity-v1/geographic-evidence.json"
PROTECTED_FILES = (
    "prosperity/source-layout.svg",
    "prosperity-city-distribution/grounded-distribution.svg",
    "backbone-469/frame-06a.svg", "backbone-469/frame-qian2018.svg",
    "downloads/backbone-469.pdf", "backbone-469/readings.json",
    "backbone-469/urban-contexts.json", "backbone-469/jianchun-plan-audit.json",
    "backbone-469/jianchun-source-context.svg", "backbone-469/jianchun-structure-reading.svg",
)
CSV_FIELDS = ("card_id", "name", "feature_id", "entity_id", "source_frame",
              "source_geometry_role", "east_west_m", "north_south_m",
              "dimensions_approximate", "scene_binding_feature_id", "scope")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def esc(value):
    return html.escape(str(value), quote=True)


def tag(parent, name, **attributes):
    return ET.SubElement(parent, f"{{{SVG_NS}}}{name}", {
        key.rstrip("_").replace("_", "-"): str(value)
        for key, value in attributes.items() if value is not None
    })


def text(parent, x, y, value, size=18, color=INK, **attributes):
    # Explicit lower text keeps the light halo readable in SVG renderers that
    # do not implement paint-order (including the image QA renderer).
    if attributes.get("class_") in ("place-label", "road-label"):
        halo = tag(parent, "text", x=x, y=y, font_size=size, fill="none", stroke=PAPER,
                   stroke_width=1.1, stroke_linejoin="round", aria_hidden="true", **attributes)
        halo.text = str(value)
    item = tag(parent, "text", x=x, y=y, font_size=size, fill=color, **attributes)
    item.text = str(value)
    return item


def feature_paths(parent, feature, color, width, dashed=None):
    geometry = feature["source_pdf_geometry"]
    parts = geometry["coordinates"] if geometry["type"] == "MultiLineString" else [geometry["coordinates"]]
    for number, coordinates in enumerate(parts, 1):
        commands = " ".join(("M" if index == 0 else "L") + f"{xy[0]} {xy[1]}"
                            for index, xy in enumerate(coordinates))
        tag(parent, "path", d=commands, fill="none", stroke=color,
            stroke_width=width, stroke_dasharray=dashed,
            data_source_feature_id=feature["id"], data_part=number,
            data_source_frame="frame-06a", data_source_path=GEO_PATH + "#" + feature["id"])


def make_map(data):
    """Draw original PDF-point vertices once; display transforms are not surveys."""
    features = {row["id"]: row for row in data["features"]}
    places = {row["feature_id"]: row for row in data["places"]}
    water = {row["mapped_feature_id"] for row in data["water_evidence_navigation"]}
    root = ET.Element(f"{{{SVG_NS}}}svg", {
        "id": "city-common-map", "viewBox": "0 0 900 1080", "width": "900", "height": "1080",
        "role": "img", "aria-labelledby": "common-map-title common-map-description", "lang": "zh-CN",
        "data-source-frame": "frame-06a", "data-native-units": "PDF point",
    })
    tag(root, "title", id="common-map-title").text = "宫城、道路与寺院：06a同源城市共同视图"
    tag(root, "desc", id="common-map-description").text = (
        "25项已有来源要素，包含四处建筑图符、八条道路原分段及永宁寺七段残墙。"
        "现代洛水默认关闭。没有新增古代位置、建筑足迹或古河线。")
    tag(root, "metadata").text = json.dumps({
        "version": VERSION, "source_frame": data["source_frame"], "counts": data["counts"],
        "new_historical_coordinates": 0, "new_geographic_footprints": 0,
        "modern_reference_default_visible": False,
    }, ensure_ascii=False)
    tag(root, "style").text = """
    text{font-family:'Noto Sans CJK SC','Microsoft YaHei',sans-serif}
    a{cursor:pointer} a:focus{outline:none}
    [data-place-id] circle{transition:fill .12s}
    [data-place-id].is-selected circle:not(.hit-area){fill:#b7772e;stroke:#64491e;stroke-width:.8}
    [data-place-id].is-selected path{stroke:#b7772e;stroke-width:1.3}
    [data-place-id]:focus circle:not(.hit-area){stroke:#b7772e;stroke-width:1}
    .place-label{font-weight:700}
    """
    tag(root, "rect", width=900, height=1080, fill=PAPER)
    text(root, 36, 35, "盛时洛阳 / P4.7 / 06a同源共同视图", 16, MUTED)
    text(root, 36, 77, "四处建筑参照，连同城墙与八条道路", 31, INK, font_weight="700")
    text(root, 36, 106, "保留原图符与断笔；报告尺度、文献关系在网页卡片中联读。", 16, MUTED)
    tag(root, "rect", x=35, y=125, width=830, height=825, rx=12, fill="#eff1e7", stroke="#d4d9c8")
    defs = tag(root, "defs")
    clip = tag(defs, "clipPath", id="common-map-clip")
    tag(clip, "rect", x=36, y=126, width=828, height=823, rx=11)
    clipped = tag(root, "g", clip_path="url(#common-map-clip)")
    native = tag(clipped, "g", id="common-native-06a", transform="translate(70 130) scale(4) translate(-245 -230)",
                 data_native_units="PDF point", data_source_frame="frame-06a")

    modern = tag(native, "g", data_city_layer="modern", style="display:none", aria_hidden="true")
    modern_feature = features[data["modern_feature_id"]]
    modern_group = tag(modern, "g", data_feature_id=modern_feature["id"], data_period="1997/1999",
                       data_not_ancient_river="true")
    tag(modern_group, "title").text = modern_feature["label"]
    feature_paths(modern_group, modern_feature, "#8faaa8", 1.1, "3 1.3")
    text(modern_group, 292, 418, "近现代洛水参照 · 1997／1999", 4, "#678b89")

    walls = tag(native, "g", data_city_layer="walls")
    for feature_id in data["wall_feature_ids"]:
        feature = features[feature_id]
        temple = feature_id == "geo-yongning-temple-walls"
        attributes = {"data_feature_id": feature_id}
        if temple:
            attributes.update(data_place_id="C04", href=OFFICIAL + PAGE + "#place-C04",
                              aria_label="永宁寺七段残墙：查看塔基与寺院范围")
        group = tag(walls, "a" if temple else "g", **attributes)
        tag(group, "title").text = feature["label"] + "；" + feature["source_historical_period"]
        underground = feature_id == "geo-inner-wall-underground"
        feature_paths(group, feature, TEMPLE if temple else WALL,
                      .85 if temple else .7 if underground else 1.25,
                      "1.4 .7" if underground else None)

    roads = tag(native, "g", data_city_layer="roads")
    road_labels = {"Lh-1": (257, 383), "Lh-2": (257, 325), "Lh-3": (257, 292), "Lh-4": (257, 265),
                   "Lz-1": (360, 400), "Lz-2": (343, 396), "Lz-3": (312, 398), "Lz-4": (287, 398)}
    for road in data["roads"]:
        feature_id, code = road["p1_feature_id"], road["code"]
        attrs = {"data_feature_id": feature_id, "data_road": code}
        if feature_id in water:
            attrs.update(href=OFFICIAL + PREVIOUS + "#context-" + feature_id,
                         data_water_context_id=feature_id, aria_label=road["title"] + "：查看水系证据")
        group = tag(roads, "a" if feature_id in water else "g", **attrs)
        tag(group, "title").text = code + " · " + road["title"] + "；道路图示残段"
        color = ROAD_H if code.startswith("Lh") else ROAD_V
        feature_paths(group, features[feature_id], color, .8)
        text(group, *road_labels[code], code, 4.1, color, class_="road-label", font_weight="600")

    points = tag(native, "g", data_city_layer="points")
    generic_offsets = {
        "geo-qianqiu-gate": (-3,-2,"end"), "geo-yunlong-gate": (3,-2,"start"),
        "geo-daxia-gate": (-3,-3,"end"), "geo-guangmo-gate": (3,-3,"start"),
        "geo-xiyang-gate": (3,-4,"start"), "geo-dongyang-gate": (3,-3,"start"),
        "geo-qingyang-gate": (3,-3,"start"), "geo-ximing-gate": (3,-4,"start"),
    }
    place_offsets = {"C01": (5, -5, "start"), "C02": (4, -5, "start"),
                     "C03": (5, 6, "start"), "C04": (-7, 2, "end")}
    for feature in data["features"]:
        if feature["source_pdf_geometry"]["type"] != "Point":
            continue
        feature_id = feature["id"]
        x, y = feature["source_pdf_geometry"]["coordinates"]
        place = places.get(feature_id)
        attrs = {"data_feature_id": feature_id}
        if place:
            attrs.update(href=OFFICIAL + PAGE + "#place-" + place["id"],
                         data_place_id=place["id"], aria_label=place["id"] + " " + place["name"])
        elif feature_id in water:
            attrs.update(href=OFFICIAL + PREVIOUS + "#context-" + feature_id,
                         data_water_context_id=feature_id, aria_label=feature["label"] + "：查看水系证据")
        group = tag(points, "a" if "href" in attrs else "g", **attrs)
        tag(group, "title").text = feature["label"] + "；来源图符中心"
        if place:
            tag(group, "circle", cx=x, cy=y, r=3.3, fill="transparent", class_="hit-area")
        tag(group, "circle", cx=x, cy=y, r=1.8 if place else 1.15,
            fill=INK if place else PAPER, stroke=INK, stroke_width=.45,
            data_source_feature_id=feature_id, data_source_frame="frame-06a",
            data_source_path=GEO_PATH + "#" + feature_id)
        if place:
            dx, dy, anchor = place_offsets[place["id"]]
            name = place["name"].replace("宫城", "").replace("内城", "")
            text(group, x+dx, y+dy, place["id"] + " " + name, 4.8, INK,
                 text_anchor=anchor, class_="place-label")
        else:
            dx, dy, anchor = generic_offsets[feature_id]
            name = feature["label"].replace("宫城", "").replace("内城", "").replace("位置参考", "")
            text(group, x+dx, y+dy, name, 3.7, MUTED, text_anchor=anchor)
    text(native, 307, 409, "南墙与宣阳门未补绘", 4, MUTED)
    text(root, 64, 163, "N", 17, INK, font_weight="700")
    tag(root, "path", d="M70 202 L70 174 M63 184 L70 174 L77 184", stroke=INK, stroke_width=2, fill="none")
    legend = ((48, ROAD_H, "横向道路原段"), (260, ROAD_V, "纵向道路原段"),
              (472, WALL, "城墙遗存"), (660, TEMPLE, "永宁寺残墙"))
    for x, color, label in legend:
        tag(root, "line", x1=x, y1=980, x2=x+26, y2=980, stroke=color, stroke_width=4)
        text(root, x+37, 986, label, 16)
    text(root, 36, 1022, "图源：2012管理规划06a（申遗PDF第3457页）；原PDF点框与既有西安1980参照。", 14, MUTED)
    text(root, 36, 1053, "图符不代表足迹；尺寸和文献关系不转为地理轮廓。古岸线、桥头与古高仍待证。", 14, MUTED)
    return root


def source_links(record_id, urban):
    record = urban["source_records"][record_id]
    links = []
    for source in record["links"]:
        title = source.get("title", source.get("id", "原来源"))
        url = source.get("url")
        links.append(f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(title)}</a>' if url else esc(title))
    locator = (" · " + esc(record["locator"])) if record["locator"] else ""
    return f'<span data-source-record="{esc(record_id)}">{esc(record_id)}</span>{locator}；' + "；".join(links)


def place_html(data):
    buttons, cards = [], []
    notes = {
        "C01": ("宫城南门", "宫城南门的位置参照，与内城西垣同名的阊阖门分开。", "独立报告的局部门基尺寸；未据此把矩形贴到图符上。"),
        "C02": ("内城东门", "保留原城门图符。门内结构与门外两桥分别阅读。", "中门道8米为残宽；北门道下所见汉晋排水遗迹，其盛时通水未证。"),
        "C03": ("宫城大殿", "沿用来源图位置参照。宫院细部和不同量距口径在太极殿专题中详读。", "约100×60米为粗略报告参照；不作为唯一精确殿基或宫院范围。"),
        "C04": ("寺院塔基遗存", "塔基点与7段寺院残墙分别保留；下方文字关系针对所属寺院。", "38.2米指残存塔基平面；寺墙不补成完整矩形，也不据残高推算塔高。"),
    }
    for place in data["places"]:
        identifier, name = place["id"], place["name"]
        nav = place["reading_navigation"]
        buttons.append(f'<a href="#place-{identifier}" role="button" data-place-choice="{identifier}" aria-pressed="false"><span class="number">{identifier}</span>{esc(name)}</a>')
        dimensions = place["reported_footprint_m"]
        approximate = "约" if place["dimensions_approximate"] else ""
        measurement = f'{approximate}{dimensions["east_west"]:g} × {dimensions["north_south"]:g} 米'
        links = [f'<a href="./{esc(link["href"])}">{esc(link["label"])}</a>' for link in nav["detail_links"]]
        if nav["urban_cluster_ids"]:
            cluster_id = nav["urban_cluster_ids"][0]
            links.insert(0, f'<a href="#scene-{cluster_id}" data-open-scene="{cluster_id}">联读{"所属寺院的" if identifier == "C04" else ""}城市关系 ↓</a>')
        if identifier == "C02":
            links.append('<a href="./prosperity-backbone-p469.html#context-geo-jianchun-gate">门外水道与最新门内核读</a>')
        kind, position, limitation = notes[identifier]
        entity = place["entity_id"] or ""
        cards.append(f'<article id="place-{identifier}" data-place-card="{identifier}" data-feature-id="{esc(place["feature_id"])}" data-entity-id="{esc(entity)}">'
                     f'<p class="eyebrow">{identifier} / 来源图建筑参照</p><h3>{esc(name)}</h3><p class="place-kind">{esc(kind)} · <span class="tag">原图符位置</span></p>'
                     f'<h4>位置与范围</h4><p>{esc(position)}</p><h4>独立报告尺度 · 东西 × 南北</h4><p class="dimension">{esc(measurement)}</p>'
                     f'<p class="boundary">{esc(limitation)}</p><h4>年代与材料</h4><p>{esc(place["chronology"])}</p>'
                     f'<p class="source-line">尺寸依据：{esc(place["dimension_source"])}</p><nav class="place-links">{"".join(links)}</nav></article>')
    return "".join(buttons), "".join(cards)


def scene_html(data):
    urban = data["urban"]
    names = urban["entity_names"]
    headings = {"K01": "宫前 · 寺院、官署与学校", "K02": "建春门 · 两座石桥与桥北里坊", "K03": "洛南 · 永桥、市场与归正里"}
    predicates = {"west_of": ("在", "以西"), "east_of": ("在", "以东"),
                  "north_of": ("在", "以北"), "south_of": ("在", "以南"),
                  "outside": ("位于", "外"), "on": ("位于", "上"), "within": ("位于", "内")}
    buttons, panels = [], []
    for cluster in urban["clusters"]:
        identifier = cluster["id"]
        buttons.append(f'<a href="#scene-{identifier}" role="button" data-scene-choice="{identifier}" aria-pressed="false">{esc(headings[identifier])}'
                       f'<small>{len(cluster["nodes"])}个对象 · {len(cluster["edges"])}条关系</small></a>')
        nodes = []
        for node in cluster["nodes"]:
            mapped = node["feature_id"] is not None
            state = "来源图已有参照" if mapped else "文献关系参照" if node["id"] in urban["reference_entity_ids"] else "文献相对关系"
            nodes.append(f'<li data-urban-node-id="{esc(node["id"])}" data-mapped="{str(mapped).lower()}">{esc(node["name"])}<small>{state}</small></li>')
        edges = []
        for edge in cluster["edges"]:
            condition = edge["grade"] == "C"
            grade = "条件解释" if condition else "原文关系"
            preposition, suffix = predicates[edge["predicate"]]
            edges.append(f'<article class="relation" data-urban-edge-id="{esc(edge["id"])}" data-evidence-grade="{esc(edge["grade"])}">'
                         f'<p class="relation-title">{esc(names[edge["subject"]])}<span class="predicate">{esc(preposition)}</span>{esc(names[edge["object"]])}<span class="predicate">{esc(suffix)}</span></p>'
                         f'<p class="relation-meta"><span class="tag{" condition" if condition else ""}">{esc(edge["grade"])} · {grade}</span>　{esc(edge["id"])}</p>'
                         '<details><summary>展开原文、出处与范围</summary>'
                         f'<blockquote>{esc(edge["quote"])}</blockquote><p class="boundary">{esc(edge["scope"])}</p>'
                         f'<p class="source-line">{source_links(edge["source_record"], urban)}</p></details></article>')
        events = []
        for event in cluster.get("temporal_events", []):
            excluded = "、".join(names[key] for key in event.get("does_not_transfer_to", []))
            exclude = f'<p class="boundary">该事件不转移到：{esc(excluded)}。</p>' if excluded else ""
            events.append(f'<li data-urban-event-id="{esc(event["id"])}"><time>{esc(event["year"])}年</time><strong>{esc(names[event["subject"]])}</strong>'
                          f'<p>{esc(event["event"])}</p><p>{esc(event["scope"])}</p>{exclude}'
                          f'<p class="source-line">{source_links(event["source_record"], urban)}</p></li>')
        event_html = ('<section class="events"><h4>两座桥的事件分别记录</h4><p>527年第一石桥的颓桥记录与280年东石桥的建造记述分开，不将一桥事件转移给另一桥。</p>'
                      f'<ul>{"".join(events)}</ul></section>') if events else ""
        notes = "".join(f'<li>{esc(note)}</li>' for note in cluster["uncertainty_notes"])
        if identifier == "K03":
            location = '<p class="notice" data-scene-location-status="unbound">本组尚无06a地理绑定。宣阳门、永桥、洛水与市场保持文献关系，不借用近现代河线定位。</p>'
            water = '<a href="./prosperity-backbone-p469.html#water-W01">旁读古洛水证据索引</a> · <a href="./prosperity-backbone-p469.html#map=frame-qian2018">查看独立的钱氏图框</a>'
        elif identifier == "K01":
            location = '<p class="scene-scope" data-scene-location-status="source-references">位置入口为宫城阊阖门图符与永宁寺残墙。宫前御道未与铜驼道路残段建立全段同体关系；官署与学校不据文献方位补点。</p>'
            water = '<a href="./prosperity-backbone-p469.html#context-geo-tongtuo-avenue">旁读铜驼街水系记录</a>；这里的来源路段不代替宫前御道全段。'
        else:
            location = '<p class="scene-scope" data-scene-location-status="source-references">原建春门图符作为阅读入口；两座石桥、桥北大道及里坊没有获得门址的坐标。</p>'
            water = '<a href="./prosperity-backbone-p469.html#context-geo-jianchun-gate">旁读建春门水道、门内平面与共同控制核查</a>'
        panels.append(f'<article class="scene-panel" id="scene-{identifier}" data-scene-panel="{identifier}"><div class="scene-heading"><h3>{esc(headings[identifier])}</h3>'
                      f'<a href="./prosperity-street-clusters.html?cluster={identifier}&amp;grade=all">打开原关系专题 ↗</a></div>{location}'
                      f'<p class="scene-scope">{esc(cluster["reading_scope"])}</p><ul class="node-list">{"".join(nodes)}</ul><div class="relations">{"".join(edges)}</div>{event_html}'
                      f'<details class="scene-notes"><summary>本组关系仍需保留的区别</summary><ul>{notes}</ul></details><p class="scene-water">{water}</p></article>')
    return "".join(buttons), "".join(panels)


def functions_html(data):
    urban = data["urban"]
    nodes = {node["id"]: node for cluster in urban["clusters"] for node in cluster["nodes"]}
    scene_for = {node["id"]: cluster["id"] for cluster in urban["clusters"] for node in cluster["nodes"]}
    options, cards = [], []
    for group in urban["functions"]:
        options.append(f'<option value="{esc(group["id"])}">{esc(group["title"])} · {len(group["entity_ids"])}个对象</option>')
        for entity_id in group["entity_ids"]:
            node = nodes[entity_id]
            scene_id = scene_for[entity_id]
            spatial = "来源图已有参照" if node["feature_id"] else "仅有文献相对关系"
            cards.append(f'<article class="function-object" data-function-object="{esc(entity_id)}" data-function-group="{esc(group["id"])}">'
                         f'<span class="tag">{esc(group["title"])}</span><h3>{esc(node["name"])}</h3><p>{spatial}</p>'
                         f'<a href="#scene-{scene_id}" data-open-scene="{scene_id}">查看所在场景的关系 →</a></article>')
    return "".join(options), "".join(cards)


def page_html(data, diagram, source_commit):
    inline = copy.deepcopy(diagram)
    for element in inline.iter():
        href = element.get("href", "")
        if href.startswith(OFFICIAL + PAGE + "#"):
            element.set("href", "#" + href.split("#", 1)[1])
    places, cards = place_html(data)
    scenes, panels = scene_html(data)
    functions, objects = functions_html(data)
    audit_rows = []
    for path, digest in data["source_inputs_sha256"].items():
        commit = source_commit if "/common-470/" in path else data["source_baseline_commit"]
        link = f"https://github.com/mechgouki/luoyang-city/blob/{commit}/{path}"
        audit_rows.append(f'<li><a href="{esc(link)}" target="_blank" rel="noopener">{esc(path)}</a><code>SHA256 {digest}</code></li>')
    replacements = {
        "<!-- COMMON_MAP -->": ET.tostring(inline, encoding="unicode"),
        "<!-- PLACE_BUTTONS -->": places, "<!-- PLACE_CARDS -->": cards,
        "<!-- SCENE_BUTTONS -->": scenes, "<!-- SCENE_PANELS -->": panels,
        "<!-- FUNCTION_OPTIONS -->": functions, "<!-- FUNCTION_OBJECTS -->": objects,
        "<!-- SOURCE_AUDIT -->": '<ul class="source-audit">' + "".join(audit_rows) + "</ul>",
        "<!-- SOURCE_COMMIT -->": esc(source_commit),
    }
    page = (SOURCE / "index.html").read_text(encoding="utf-8")
    for marker, value in replacements.items():
        if page.count(marker) != 1:
            raise ValueError("P470 template marker must occur exactly once: " + marker)
        page = page.replace(marker, value)
    return page


def places_csv(data):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for place in data["places"]:
        nav = place["reading_navigation"]
        writer.writerow({
            "card_id": place["id"], "name": place["name"], "feature_id": place["feature_id"],
            "entity_id": place["entity_id"] or "", "source_frame": data["source_frame"]["id"],
            "source_geometry_role": place["source_feature_represents"],
            "east_west_m": place["reported_footprint_m"]["east_west"],
            "north_south_m": place["reported_footprint_m"]["north_south"],
            "dimensions_approximate": str(place["dimensions_approximate"]).lower(),
            "scene_binding_feature_id": nav["scene_binding_feature_id"] or "", "scope": nav["scope"],
        })
    return stream.getvalue()


def build(site=SITE):
    site = Path(site)
    info, release = load(site / "build-info.json"), load(site / "release.json")
    protected = {path: sha(site / path) for path in PROTECTED_FILES}
    for path in info["files_sha256"]:
        if path.endswith(("-luoyang-panorama.webp", "-luoyang-panorama-small.webp",
                          "-luoyang-panorama-approved-v9.webp", "-luoyang-panorama-approved-v9-small.webp")):
            protected[path] = sha(site / path)
    previous = site / PREVIOUS
    original = previous.read_text(encoding="utf-8").replace(ENTRY, "")
    if original.count('<section id="explore"') != 1 or "P4.6.9" not in original:
        raise ValueError("Review the P469 page before adding the P470 continuation")
    previous_sha = hashlib.sha256(original.encode("utf-8")).hexdigest()
    data = build_data(ROOT)
    dest = site / FOLDER
    dest.mkdir(parents=True, exist_ok=True)
    (site / "downloads").mkdir(parents=True, exist_ok=True)
    diagram = make_map(data)
    ET.indent(diagram)
    ET.ElementTree(diagram).write(dest / "city-common.svg", encoding="utf-8", xml_declaration=True)
    dump(dest / "readings.json", data)
    (dest / "places.csv").write_text(places_csv(data), encoding="utf-8", newline="")
    for filename in ("study.css", "common-ui.js", "reuse-plan.json"):
        shutil.copyfile(SOURCE / filename, dest / filename)
    page = page_html(data, diagram, info["source_commit"])
    (site / PAGE).write_text(page, encoding="utf-8")
    previous.write_text(original.replace('<section id="explore"', ENTRY + '<section id="explore"', 1), encoding="utf-8")
    if previous.read_text(encoding="utf-8").replace(ENTRY, "") != original:
        raise ValueError("The P469 page changed beyond the unique continuation entry")
    assets = [dest / filename for filename in ("city-common.svg", "readings.json", "places.csv",
                                               "study.css", "common-ui.js", "reuse-plan.json")]
    preservation = {"previous_page": PREVIOUS, "previous_page_sha256": previous_sha,
                    "entry_id": "p470-entry", "entry_html": ENTRY, "protected_files_sha256": protected}
    manifest = {"version": VERSION, "source_commit": info["source_commit"], "page": PAGE, "bundle": BUNDLE,
                "source_inputs_sha256": data["source_inputs_sha256"],
                "files_sha256": {path.relative_to(site).as_posix(): sha(path) for path in assets},
                "new_historical_coordinates": 0, "new_metric_measurements": 0,
                "new_historical_relationships": 0, "preservation": preservation}
    dump(site / MANIFEST, manifest)
    with zipfile.ZipFile(site / BUNDLE, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("index.html", offline_page(page, FOLDER, ""))
        for path in [*assets, site / MANIFEST]:
            archive.write(path, path.relative_to(site).as_posix())
    release["extensions"] = sorted(set(release["extensions"]) | {VERSION})
    release["prosperity_city_common_p470_version"] = VERSION
    release["current_milestone"] = "盛时 P4.7 · 城市骨架与建筑共同视图"
    dump(site / "release.json", release)
    study = {
        "version": VERSION, "source_commit": info["source_commit"], "page": PAGE,
        "folder": FOLDER, "bundle": BUNDLE, "package": BUNDLE, "manifest": MANIFEST,
        "readings": f"{FOLDER}/readings.json", "plates": ["city-common.svg"],
        "entry_id": "p470-entry", "counts": data["counts"], "urban_counts": data["urban"]["counts"],
        "source_inputs_sha256": data["source_inputs_sha256"], "new_historical_coordinates": 0,
        "new_metric_measurements": 0, "new_historical_relationships": 0,
        "new_geographic_transform": None, "new_geographic_footprints": 0,
        "preservation": preservation,
        "download_files": [f"{FOLDER}/city-common.svg", f"{FOLDER}/readings.json", f"{FOLDER}/places.csv",
                           f"{FOLDER}/reuse-plan.json", MANIFEST, BUNDLE],
    }
    info["prosperity_city_common_p470"] = study
    for path in [*assets, site / PAGE, previous, site / MANIFEST, site / BUNDLE, site / "release.json"]:
        info["files_sha256"][path.relative_to(site).as_posix()] = sha(path)
    if any(sha(site / path) != digest for path, digest in protected.items()):
        raise ValueError("P470 modified a protected prior map, data file, atlas or panorama")
    if any(sha(ROOT / path) != digest for path, digest in data["source_inputs_sha256"].items()):
        raise ValueError("P470 must not mutate its source records")
    dump(site / "build-info.json", info)
    return study


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
