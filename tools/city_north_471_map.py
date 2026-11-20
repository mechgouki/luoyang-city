"""Display the existing 06a geometry in a city overview and a northern crop.

Both plates retain the same 27 original feature records and native PDF-point
vertices.  The second plate is a display crop, not a new geographic transform.
"""
from __future__ import annotations

import copy
import json
from xml.etree import ElementTree as ET

import prosperity_city_common_p470 as common_map


SVG_NS = common_map.SVG_NS
SVG = "{" + SVG_NS + "}"
PAGE = "prosperity-city-north.html"
VERSION = "prosperity-city-north-p471"
OFFICIAL = common_map.OFFICIAL
GEO_PATH = common_map.GEO_PATH
PAPER, INK, MUTED = common_map.PAPER, common_map.INK, common_map.MUTED
JINYONG = "#506d75"
JINYONG_WALL = "geo-jinyong-bing-wall"
JINYONG_POINT = "geo-jinyong-bing-reference"
ENTRY_FEATURES = {
    "N01": (JINYONG_WALL, JINYONG_POINT),
    "N02": ("geo-daxia-gate",),
    "N03": ("geo-guangmo-gate",),
}
tag, text = common_map.tag, common_map.text


def _group(root, feature_id):
    found = [node for node in root.iter() if node.get("data-feature-id") == feature_id]
    if len(found) != 1:
        raise ValueError(f"P471 map requires exactly one source group: {feature_id}")
    return found[0]


def _layer(root, name):
    found = [node for node in root.iter() if node.get("data-city-layer") == name]
    if len(found) != 1:
        raise ValueError("P471 map layer is missing or duplicated: " + name)
    return found[0]


def _rename_ids(root, identifiers):
    for node in root.iter():
        if node.get("id") in identifiers:
            node.set("id", identifiers[node.get("id")])
        for key, value in list(node.attrib.items()):
            for old, new in identifiers.items():
                value = value.replace("url(#" + old + ")", "url(#" + new + ")")
            if key in {"aria-labelledby", "aria-describedby"}:
                value = " ".join(identifiers.get(token, token) for token in value.split())
            node.set(key, value)


def _source_attributes(group, feature):
    for key, value in {
        "data-source-frame": "frame-06a",
        "data-source-path": GEO_PATH + "#" + feature["id"],
        "data-source-geometry-type": feature["source_pdf_geometry"]["type"],
        "data-source-historical-period": feature.get("source_historical_period"),
        "data-entity-id": feature.get("entity_id"),
        "data-entity-binding-scope": feature.get("entity_binding_scope"),
        "data-source-reference-role": feature.get("approximation", {}).get("status"),
    }.items():
        if value is not None:
            group.set(key, str(value))


def _north_link(group, entry):
    group.tag = SVG + "a"
    group.set("data-north-id", entry["id"])
    group.set("href", OFFICIAL + PAGE + "#north-" + entry["id"])
    group.set("aria-label", entry["id"] + " " + entry["name"] + "：查看北城文献与参照范围")


def _north_label(group, x, y, label, *, anchor="start", size=4.6):
    for child in list(group):
        if child.tag == SVG + "text":
            group.remove(child)
    text(group, x, y, label, size, INK, text_anchor=anchor, class_="place-label")


def _style(map_id):
    scope = "#" + map_id
    return f"""
    {scope} text{{font-family:'Noto Sans CJK SC','Microsoft YaHei',sans-serif}}
    {scope} a{{cursor:pointer}}
    {scope} a:focus-visible{{outline:.65px solid #b9823b;outline-offset:1px}}
    {scope} a:focus-visible circle[data-source-feature-id]{{stroke:#a36a2b;stroke-width:.9}}
    {scope} a:focus-visible path[data-source-feature-id]{{stroke:#a36a2b;stroke-width:1.35}}
    {scope} .place-label{{font-weight:700}}
    {scope} [data-north-id].is-selected circle[data-source-feature-id]{{fill:#dfbf83;stroke:#64491e;stroke-width:.8}}
    {scope} [data-north-id].is-selected circle[data-point-role="representative"]{{fill:{PAPER};stroke:#a36a2b;stroke-width:.9}}
    {scope} [data-north-id].is-selected path[data-source-feature-id]{{stroke:#b7772e;stroke-width:1.35}}
    {scope} [data-north-id]:focus circle[data-source-feature-id]{{stroke:#a36a2b;stroke-width:.9}}
    {scope} [data-north-id]:focus path[data-source-feature-id]{{stroke:#a36a2b;stroke-width:1.35}}
    """


def _prepare_geometry(data):
    root = common_map.make_map(data["common"])
    features = {feature["id"]: feature for feature in data["features"]}
    entries = {entry["id"]: entry for entry in data["north_entries"]}
    if len(features) != 27 or set(entries) != set(ENTRY_FEATURES):
        raise ValueError("P471 requires 27 source features and the three northern entries")
    if {feature["id"] for feature in data["common"]["features"]} | {JINYONG_WALL, JINYONG_POINT} != set(features):
        raise ValueError("P471 can add only the two existing Jinyong component references")
    for identifier, required in ENTRY_FEATURES.items():
        if tuple(entries[identifier]["feature_ids"]) != required:
            raise ValueError("P471 northern entry source identity changed: " + identifier)

    # Existing four-building links continue to P470 and retain their source
    # marks.  They are not controls for the new three-entry northern interface.
    for node in root.iter():
        node.attrib.pop("data-place-id", None)

    wall = features[JINYONG_WALL]
    geometry = wall["source_pdf_geometry"]
    if geometry["type"] != "MultiLineString" or len(geometry["coordinates"]) != 5 or sum(map(len, geometry["coordinates"])) != 13:
        raise ValueError("Jinyong must keep its five open parts and thirteen vertices")
    wall_group = tag(_layer(root, "walls"), "a", data_feature_id=JINYONG_WALL)
    _north_link(wall_group, entries["N01"])
    tag(wall_group, "title").text = "金墉丙城东、南墙：五段原图遗存，仅为金墉城的部分组成"
    common_map.feature_paths(wall_group, wall, JINYONG, .95)

    point = features[JINYONG_POINT]
    if point["source_pdf_geometry"]["type"] != "Point":
        raise ValueError("Jinyong representative reference must remain a point")
    x, y = point["source_pdf_geometry"]["coordinates"]
    point_group = tag(_layer(root, "points"), "a", data_feature_id=JINYONG_POINT)
    _north_link(point_group, entries["N01"])
    tag(point_group, "title").text = "金墉丙城范围内图示代表点：非门址、三城中心或实测控制点"
    tag(point_group, "circle", cx=x, cy=y, r=3.8, fill="transparent", class_="hit-area", data_display_only="hit-area")
    tag(point_group, "circle", cx=x, cy=y, r=1.7, fill=PAPER, stroke=JINYONG,
        stroke_width=.6, stroke_dasharray=".8 .4", data_point_role="representative",
        data_source_feature_id=JINYONG_POINT, data_source_frame="frame-06a",
        data_source_path=GEO_PATH + "#" + JINYONG_POINT)
    _north_label(point_group, x-8, y-7, "N01 金墉丙城", anchor="end", size=4.5)

    for identifier in ("N02", "N03"):
        entry = entries[identifier]
        feature = features[entry["point_feature_id"]]
        group = _group(root, feature["id"])
        _north_link(group, entry)
        x, y = feature["source_pdf_geometry"]["coordinates"]
        hit_area = tag(group, "circle", cx=x, cy=y, r=3.3, fill="transparent", class_="hit-area", data_display_only="hit-area")
        group.remove(hit_area)
        group.insert(1, hit_area)
        _north_label(group, x-3 if identifier == "N02" else x+3, y-3,
                     identifier + " " + entry["name"], anchor="end" if identifier == "N02" else "start", size=4.4)

    for feature in features.values():
        _source_attributes(_group(root, feature["id"]), feature)
    return root


def _north_arrow(root, x, y, *, size=17):
    text(root, x-6, y, "N", size, INK, font_weight="700")
    tag(root, "path", d=f"M{x} {y+39} L{x} {y+11} M{x-7} {y+21} L{x} {y+11} L{x+7} {y+21}",
        stroke=INK, stroke_width=2, fill="none", data_display_only="north-arrow")


def _legend_line(root, x, y, color, label, size=15):
    tag(root, "line", x1=x, y1=y, x2=x+25, y2=y, stroke=color, stroke_width=4)
    text(root, x+36, y+5, label, size)


def _legend_point(root, x, y, label, *, representative=False, size=15):
    tag(root, "circle", cx=x+12, cy=y, r=5, fill=PAPER, stroke=JINYONG if representative else INK,
        stroke_width=2, stroke_dasharray="2.8 1.7" if representative else None)
    text(root, x+36, y+5, label, size)


def _compose(base, data, *, detail=False):
    root = copy.deepcopy(base)
    prefix = "detail" if detail else "overview"
    map_id = "north-detail-map" if detail else "north-overview-map"
    native_id = "north-detail-native" if detail else "north-overview-native"
    identifiers = {"city-common-map": map_id, "common-map-title": prefix+"-map-title",
                   "common-map-description": prefix+"-map-description", "common-map-clip": prefix+"-map-clip",
                   "common-native-06a": native_id}
    _rename_ids(root, identifiers)
    height = 650 if detail else 1080
    root.set("viewBox", f"0 0 900 {height}")
    root.set("height", str(height))
    root.set("data-display-frame", "north" if detail else "overview")
    root.set("data-display-semantics", "original-PDF-crop-only")
    root.find(SVG+"title").text = "北门与金墉丙城：06a原图北部放大" if detail else "北门—金墉：27项同源参照的全城视图"
    root.find(SVG+"desc").text = (
        "两幅图均保留27项已有来源要素；本图仅作原PDF局部裁切。" if detail else "27项已有来源要素，包含金墉丙城五段残墙与范围内代表点、大夏门、广莫门。") + (
        "空心虚线圆为丙城范围内代表点，不是门址、三城中心或实测控制点。"
        "现代洛水默认关闭。没有补全甲乙城、道路或古河线。")
    bounds = [270, 230, 390, 280] if detail else [236.5, 229, 443.5, 434.75]
    root.find(SVG+"metadata").text = json.dumps({
        "version": VERSION, "source_frame": data.get("source_frame", data["common"]["source_frame"]),
        "display_frame": "north" if detail else "overview", "source_pdf_display_bounds": bounds,
        "display_crop_only": True, "source_feature_count": 27, "site_remains_count": 26,
        "modern_reference_count": 1, "modern_reference_default_visible": False,
        "new_geographic_transform": None, "new_historical_coordinates": 0,
        "new_geographic_footprints": 0, "Jinyong_component_scope": "partial_component_reference",
        "Jinyong_point_role": "representative_point_within_mapped_remains",
    }, ensure_ascii=False)
    root.find(SVG+"style").text = _style(map_id)
    native = next(node for node in root.iter() if node.get("id") == native_id)
    clip = next(node for node in root.iter() if node.get("id") == prefix+"-map-clip")
    clipped = next(node for node in root if node.tag == SVG+"g" and node.get("clip-path"))
    root.remove(clipped)
    for child in list(root):
        if child.tag in {SVG+"rect", SVG+"text", SVG+"path", SVG+"line"}:
            root.remove(child)
    tag(root, "rect", width=900, height=height, fill=PAPER)
    text(root, 36, 35, "盛时洛阳 / P4.7.1 / 06a北城参照", 16, MUTED)
    if detail:
        native.set("transform", "translate(30 125) scale(7) translate(-270 -230)")
        frame = dict(x="30", y="125", width="840", height="350", rx="10")
        clip.find(SVG+"rect").attrib.update(frame)
        text(root, 36, 77, "北门与金墉丙城 · 来源图局部放大", 32, INK, font_weight="700")
        text(root, 36, 106, "保留同一原PDF几何；裁切范围不表示新增测量精度。", 18, MUTED)
        for identifier, dx, dy, anchor in (("N01", -9, -11, "start"), ("N02", 3, -4, "start"), ("N03", 3, -3, "start")):
            entry = next(row for row in data["north_entries"] if row["id"] == identifier)
            point = next(row for row in data["features"] if row["id"] == entry["point_feature_id"])
            x, y = point["source_pdf_geometry"]["coordinates"]
            _north_label(_group(clipped, point["id"]),
                         x+dx, y+dy, identifier+" "+entry["name"], anchor=anchor, size=4.8)
        for code, x, y in (("Lh-4", 320, 277), ("Lz-2", 362, 277)):
            group = next(node for node in native.iter() if node.get("data-road") == code)
            for label in group.findall(SVG+"text"):
                label.set("x", str(x)); label.set("y", str(y)); label.set("font-size", "3.7")
        tag(root, "rect", **frame, fill="#eff1e7", stroke="#d4d9c8")
        root.append(clipped)
        _north_arrow(root, 59, 154, size=17)
        _legend_line(root, 43, 510, JINYONG, "丙城部分残墙", 20)
        _legend_point(root, 310, 510, "范围内代表点", representative=True, size=20)
        _legend_point(root, 610, 510, "来源图门址图符", size=20)
        _legend_line(root, 43, 548, common_map.WALL, "城墙遗存", 18)
        _legend_line(root, 310, 548, common_map.ROAD_H, "横向道路原段", 18)
        _legend_line(root, 610, 548, common_map.ROAD_V, "纵向道路原段", 18)
        text(root, 36, 590, "金墉仅示丙城部分遗存；代表点非门址或金墉三城中心。", 22, MUTED)
        text(root, 36, 626, "原PDF裁切，非新配准；未补甲乙城、道路或北魏河线。", 22, MUTED)
    else:
        frame = dict(x=35, y=125, width=830, height=825, rx=12)
        text(root, 36, 77, "北门与金墉，接入同一座城市", 32, INK, font_weight="700")
        text(root, 36, 106, "27项同源参照；金墉只显示丙城残墙与范围内代表点。", 16, MUTED)
        tag(root, "rect", **frame, fill="#eff1e7", stroke="#d4d9c8")
        root.append(clipped)
        _north_arrow(root, 70, 163)
        for x, color, label in ((48, common_map.ROAD_H, "横向道路原段"), (260, common_map.ROAD_V, "纵向道路原段"),
                                (472, common_map.WALL, "城墙遗存"), (660, common_map.TEMPLE, "永宁寺残墙")):
            _legend_line(root, x, 975, color, label, 14)
        _legend_line(root, 48, 1005, JINYONG, "丙城部分残墙", 14)
        _legend_point(root, 310, 1005, "丙城范围内代表点", representative=True, size=14)
        _legend_point(root, 660, 1005, "门址图符", size=14)
        text(root, 36, 1035, "图源：2012管理规划06a · 申遗PDF第3457页；原PDF点几何与既有西安1980参照。", 13, MUTED)
        text(root, 36, 1060, "丙城仅局部遗存；代表点不指门址或三城中心。近现代洛水默认隐藏；未新增地理配准。", 13, MUTED)
    return root


def make_maps(data):
    """Return both SVG elements without mutating source records or their parts."""
    base = _prepare_geometry(data)
    maps = {"overview": _compose(base, data), "north": _compose(base, data, detail=True)}
    all_ids = []
    for root in maps.values():
        groups = [node.get("data-feature-id") for node in root.iter() if node.get("data-feature-id")]
        if len(groups) != 27 or len(set(groups)) != 27:
            raise ValueError("Each P471 plate must retain exactly 27 unique source groups")
        all_ids.extend(node.get("id") for node in root.iter() if node.get("id"))
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("P471 SVG title, clip and native IDs must be distinct across both plates")
    return maps
