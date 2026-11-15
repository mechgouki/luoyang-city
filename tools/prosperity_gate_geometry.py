#!/usr/bin/env python3
"""Auditable image-local geometry for the Changhe gate plan.

The module deliberately has no geographic placement operation: the printed
scale and north arrow establish image-local metres, not a city registration.
It uses only the standard library and never modifies its input dictionary.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import html
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "research" / "prosperity-v3"
VIEWBOX = "0 0 1600 1100"
PALETTE = {
    "gate_base": ("#236a64", "#3b8c80"),
    "passage": ("#ad671f", "#e4b165"),
    "que_base": ("#4c537b", "none"),
    "underground_foundation": ("#9c7d3b", "none"),
    "foundation_connection": ("#34798f", "none"),
}
EVIDENCE_LABELS = {
    "observed_solid_trace": "原图可辨实线；人工量读",
    "observed_passage_limits": "基座间通道带；端线用于截取可辨段",
    "source_dashed_extent": "原图地下基础虚线；保留未闭合范围",
    "schematic_centerline_from_visible_foundation": "按可见基础走向取示意中心线；无宽度含义",
}


def _distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _point(point):
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        raise ValueError("A source point must contain exactly x and y")
    result = [float(point[0]), float(point[1])]
    if not all(math.isfinite(x) for x in result):
        raise ValueError("Source coordinates must be finite")
    return result


def _round_point(point):
    return [round(point[0], 6), round(point[1], 6)]


def build_gate_geometry(data):
    """Return image-local metres, reading envelopes, and unchanged city metadata.

    coordinates_m is a flat list of vertices, like source_px. Polygon closure
    is explicit in both lists. The output is not RFC 7946 / geographic GeoJSON.
    Numeric precision is for reproducibility, never a claim of field accuracy.
    """
    cal = copy.deepcopy(data["calibration"])
    scale = cal["scale_bar"]
    start, end = _point(scale["start_px"]), _point(scale["end_px"])
    span = _distance(start, end)
    tolerance = float(scale["endpoint_tolerance_px"])
    length_m = float(scale["length_m"])
    if tolerance < 0 or span <= 2 * tolerance or length_m <= 0:
        raise ValueError("Scale bar or reading tolerance is invalid")
    mpp = length_m / span
    mpp_range = [length_m / (span + 2 * tolerance),
                 length_m / (span - 2 * tolerance)]
    arrow = cal["north_arrow"]
    tail, tip = _point(arrow["tail_px"]), _point(arrow["tip_px"])
    dx, dy = tip[0] - tail[0], tip[1] - tail[1]
    arrow_length = math.hypot(dx, dy)
    north_tolerance = float(arrow["endpoint_tolerance_px"])
    if north_tolerance < 0 or arrow_length <= 2 * north_tolerance:
        raise ValueError("North arrow or reading tolerance is invalid")
    north = [dx / arrow_length, dy / arrow_length]
    east = [-north[1], north[0]]
    origin = _point(cal["local_origin_px"])

    def pixel_to_m(point):
        px, py = _point(point)
        v = [px - origin[0], py - origin[1]]
        return [mpp * (v[0] * east[0] + v[1] * east[1]),
                mpp * (v[0] * north[0] + v[1] * north[1])]

    cal.update({
        "scale_span_px": span,
        "m_per_px": mpp,
        "m_per_px_reading_range": mpp_range,
        "north_unit_in_source_px": north,
        "east_unit_in_source_px": east,
        "north_arrow_length_px": arrow_length,
        "north_arrow_angle_from_image_up_clockwise_deg": math.degrees(math.atan2(dx, -dy)),
        "north_arrow_reading_angle_envelope_deg": math.degrees(math.asin(2 * north_tolerance / arrow_length)),
        "coordinate_formula": "x_m = m_per_px * dot(p_px - local_origin_px, east_unit); y_m = m_per_px * dot(p_px - local_origin_px, north_unit)",
        "reading_range_is_statistical_confidence_interval": False,
        "external_orientation_verified": False,
    })
    models = []
    all_points = []
    ids = set()
    for item in data["components"]:
        if item["id"] in ids:
            raise ValueError("Duplicate component id")
        ids.add(item["id"])
        if item["geometry_type"] not in {"Polygon", "LineString"}:
            raise ValueError("Unsupported source geometry")
        points = [_point(p) for p in item["source_px"]]
        if len(points) < 2:
            raise ValueError("Insufficient trace points")
        if item["geometry_type"] == "Polygon" and points[0] != points[-1]:
            raise ValueError("Source polygon must be explicitly closed")
        w, h = data["source_raster"]["width_px"], data["source_raster"]["height_px"]
        if any(not (0 <= p[0] < w and 0 <= p[1] < h) for p in points):
            raise ValueError("Trace point lies outside native raster")
        model = copy.deepcopy(item)
        coords = [pixel_to_m(p) for p in points]
        model["coordinates_m"] = [_round_point(p) for p in coords]
        model["coordinate_space"] = "image_local_marked_north_metres"
        model["evidence_label"] = EVIDENCE_LABELS[item["evidence_status"]]
        model["trace_tolerance_m_nominal"] = item["trace_tolerance_px"] * mpp
        model["closed_outline"] = item["geometry_type"] == "Polygon"
        model["city_overlay_allowed"] = False
        model["dimensions_label"] = (
            "原生图读线约 ±%.1f m；另有比例尺量读范围" % model["trace_tolerance_m_nominal"]
        )
        if item["kind"] == "foundation_connection":
            model["dimensions_label"] = "路径中心示意；线宽和全廊长度未定"
        elif item["kind"] in {"que_base", "underground_foundation"}:
            model["dimensions_label"] = "开放边线；不计算完整阙基长宽或面积"
        models.append(model)
        all_points.extend(coords)

    diagnostic = copy.deepcopy(data["diagnostics"])
    check = diagnostic["dimension_check"]
    gate = next(item for item in models if item["id"] == check["component_id"])
    measurements = {}
    for direction, pairs in check["edge_pairs"].items():
        edge_lengths = [_distance(gate["source_px"][a], gate["source_px"][b])
                        for a, b in pairs]
        mean_px = sum(edge_lengths) / len(edge_lengths)
        mean_m = mean_px * mpp
        trace = float(gate["trace_tolerance_px"])
        lo = max(0.0, mean_px - 2 * trace) * mpp_range[0]
        hi = (mean_px + 2 * trace) * mpp_range[1]
        reference = float(check["table_dimensions_m"][direction])
        measurements[direction] = {
            "edge_lengths_px": edge_lengths,
            "mean_edge_length_px": mean_px,
            "image_read_length_m": mean_m,
            "reading_envelope_m": [lo, hi],
            "table_length_m": reference,
            "difference_m": mean_m - reference,
            "difference_fraction_of_table": (mean_m - reference) / reference,
            "table_value_inside_reading_envelope": lo <= reference <= hi,
            "is_field_accuracy_estimate": False,
        }
    check["measurements"] = measurements
    check["status"] = "difference_retained_without_refitting_scale"
    all_inside = all(item["table_value_inside_reading_envelope"] for item in measurements.values())
    check["all_table_values_inside_reading_envelopes"] = all_inside
    check["interpretation"] = (
        "图读名义边长与表列值有差异；所列人工量读包络均包含对应表值。"
        "这不能判定两项已经吻合，也不能单凭小图判定原址尺寸矛盾。"
        if all_inside else
        "至少一个表列尺寸超出所设人工量读包络；需要继续核对结构边界与图件变形。"
        "该差异不是现场位置误差，不能通过反向缩放自动消除。"
    )
    ew, ns = measurements["east_west"], measurements["north_south"]
    gate["dimensions_label"] = "图读约 %.1f × %.1f m；表列 %g × %g m，分开保存" % (
        ew["image_read_length_m"], ns["image_read_length_m"], ew["table_length_m"], ns["table_length_m"])
    diagnostic["summary"] = (
        "比例尺换算后，主门基平均相对边约 %.1f × %.1f m；图读减表值为 %+.1f / %+.1f m。"
        "保留量读包络与边界定义差异，不作反向缩放。" % (
            ew["image_read_length_m"], ns["image_read_length_m"],
            ew["difference_m"], ns["difference_m"]))
    city = copy.deepcopy(data["city_link"])
    if city["registration_verified"] or city["city_overlay_allowed"]:
        raise ValueError("This P3 module must not claim a solved city registration")
    if city["common_control_points_count"] != 0 or city["city_geometry"] is not None:
        raise ValueError("Unexpected geographic control or new city geometry")
    return {
        "schema_version": data["schema_version"],
        "version": data["version"], "id": data["id"], "label": data["label"],
        "calibration": cal, "components": models,
        "relationships": copy.deepcopy(data["relationships"]),
        "bounds": {
            "min_x": min(p[0] for p in all_points), "min_y": min(p[1] for p in all_points),
            "max_x": max(p[0] for p in all_points), "max_y": max(p[1] for p in all_points),
            "unit": "m", "coordinate_space": "image_local_marked_north_metres",
        },
        "diagnostics": diagnostic, "city_link": city, "limits": list(data["limits"]),
        "historical_height_m": None, "historical_ground_elevation_m": None,
        "roof_model": None,
    }


def _esc(value):
    return html.escape(str(value), quote=True)


def _text(x, y, value, size=25, fill="#344b45", weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{_esc(value)}</text>')


def _lines(x, y, lines, size=24, gap=39, fill="#52635d"):
    return "".join(_text(x, y + i * gap, line, size=size, fill=fill)
                   for i, line in enumerate(lines))


def _rect(x, y, w, h, fill="#ffffff", stroke="#d6ddd3", radius=18):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
            f'fill="{fill}" stroke="{stroke}"/>')


def _open_svg(title, subtitle):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'viewBox="{VIEWBOX}" role="img" aria-label="{_esc(title)}">',
            f'<title>{_esc(title)}</title>',
            '<style>text{font-family:"Noto Sans CJK SC","Microsoft YaHei",sans-serif} '
            '[data-component-id]{cursor:pointer;outline:none} '
            '[data-component-id]:focus .trace,[data-component-id].is-selected .trace{'
            'stroke:#bd3c24;stroke-width:6;filter:drop-shadow(0 0 3px #ffffff)} '
            '.trace{stroke-linejoin:round;stroke-linecap:round}</style>',
            '<rect width="1600" height="1100" fill="#f4f3ec"/>',
            _text(60, 64, "P3 · 宫城阊阖门", 24, "#6b7d69", 600),
            _text(60, 113, title, 39, "#203d35", 700),
            _text(60, 153, subtitle, 23, "#61706a")]


def _close_svg(parts):
    parts.append(_text(60, 1070, "来源：申遗文档 1442.pdf · PDF 1962 / 附录 37；表列尺度见 PDF 1927。图内量读，城市接合未定。", 21, "#6e776f"))
    parts.append("</svg>")
    return "\n".join(parts)


def _raster_uri(data):
    path = DATA_DIR / data["source_raster"]["path"]
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != data["source_raster"]["sha256"]:
        raise ValueError("Native source raster hash mismatch")
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")


def _component_svg(component, mapper):
    stroke, fill = PALETTE[component["kind"]]
    pts = [mapper(p) for p in component["source_px"]]
    points = " ".join(f"{p[0]:.3f},{p[1]:.3f}" for p in pts)
    tag = "polygon" if component["geometry_type"] == "Polygon" else "polyline"
    extra = ' stroke-dasharray="11 8"' if component["kind"] == "underground_foundation" else ""
    if component["kind"] in {"passage", "foundation_connection"}:
        extra = ' stroke-dasharray="6 5"'
    width = 4.5 if component["kind"] == "que_base" else 3.5
    return (f'<g data-component-id="{_esc(component["id"])}" tabindex="0" role="button" '
            f'aria-label="{_esc(component["label"])}"><title>{_esc(component["label"] + "：" + component["note"])}</title>'
            f'<{tag} class="trace" data-role="trace" points="{points}" stroke="{stroke}" stroke-width="{width}" '
            f'fill="{fill}" fill-opacity="0.20"{extra}/></g>')


def _scale_bar(x, y, pixels, label="20 m"):
    return (f'<path d="M{x} {y-8}v16 M{x} {y}h{pixels} M{x+pixels} {y-8}v16" '
            f'fill="none" stroke="#294e44" stroke-width="3"/>'
            + _text(x, y + 32, "0", 20) + _text(x + pixels, y + 32, label, 20, anchor="end"))


def render_gate_local(data, models=None):
    """Native image and independently selectable conservative trace overlay."""
    models = models or build_gate_geometry(data)
    p = _open_svg("原件上的门基、门道与两阙", "原件可切换；实线、来源虚线和连接示意分别保存。下图保持原件图面方向。")
    p += [_rect(50, 182, 1060, 835), _rect(1135, 182, 415, 835, "#eaf0e6")]
    sx, sy, k = 69, 198, 1.84
    mapper = lambda q: (sx + k * q[0], sy + k * q[1])
    p.append(f'<g id="source-layer"><image x="{sx}" y="{sy}" width="{555*k}" height="{434*k}" '
             f'opacity="0.77" xlink:href="{_raster_uri(data)}"/></g>')
    for item in models["components"]:
        p.append(_component_svg(item, mapper))
    ox, oy = mapper(data["calibration"]["local_origin_px"])
    p.append(f'<path d="M{ox-11} {oy}h22 M{ox} {oy-11}v22" stroke="#b5332e" stroke-width="2.8"/>')
    p += [_text(1165, 229, "从像素到米", 29, "#294d40", 700),
          _lines(1165, 276, ["20 m 标尺 = 81 原生像素", "1 px ≈ 0.247 m", "图内原点：门基四角均值"], 22, 36),
          _text(1165, 419, "读图方式", 28, "#294d40", 700)]
    legend = [("#236a64", "主门基主体边缘", False), ("#ad671f", "三条门道可辨段", True),
              ("#4c537b", "两阙可见边缘", False), ("#9c7d3b", "地下基础来源虚线", True),
              ("#34798f", "连接路径示意", True)]
    for i, (color, label, dashed) in enumerate(legend):
        yy = 464 + 47 * i
        dash = ' stroke-dasharray="8 6"' if dashed else ""
        p.append(f'<path d="M1168 {yy-7}h40" stroke="{color}" stroke-width="4"{dash}/>')
        p.append(_text(1224, yy, label, 22))
    p += [_text(1165, 746, "保留不确定的边", 27, "#294d40", 700),
          _lines(1165, 790, ["阙基边线未闭合。", "黑色探方框不作建筑边。", "连接线不代表廊宽或屋顶。", "原件周缘另含剖面带。"], 22, 37),
          _text(1165, 978, "共同控制：0 · 未作城市配准", 22, "#9c4b36", 600)]
    return _close_svg(p)


def render_gate_city_link(data, models=None):
    """Display the known P2 city anchor beside the unregistered local plan."""
    models = models or build_gate_geometry(data)
    city = models["city_link"]
    p = _open_svg("局部平面怎样接上城市位置", "两个尺度空间分别可读；位置、旋转的共同控制仍缺失，局部描图不绘成城市实测足迹。")
    p += [_rect(50, 185, 710, 817), _rect(840, 185, 710, 817),
          _text(85, 237, "已有城市框架 · P2 原值", 29, "#294d40", 700),
          _text(875, 237, "本轮局部图 · 原件比例尺", 29, "#294d40", 700)]
    anchor = city["anchor_local_m"]
    comparison = city["comparison_reference"]
    x0, y0, scale = 397, 842, 0.78
    def city_point(point):
        return x0 + (point[0] - anchor[0]) * scale, y0 - (point[1] - anchor[1]) * scale
    tx, ty = city_point(comparison["anchor_local_m"])
    p.append(f'<path d="M{x0} {y0} L{tx} {ty}" stroke="#94a69b" stroke-width="3" stroke-dasharray="10 9"/>')
    angle = city["working_axis_angle_deg"]
    for ident, label, dims, center in [
        ("p2-taiji-reference", "太极殿来源点", comparison["dimensions_m"], (tx, ty)),
        ("p2-gate-reference", "阊阖门来源点", city["p2_reference_dimensions_m"], (x0, y0)),
    ]:
        x, y = center
        w, h = dims["east_west"] * scale, dims["north_south"] * scale
        p.append(f'<g id="{ident}" transform="rotate({angle} {x} {y})">'
                 f'<rect x="{x-w/2}" y="{y-h/2}" width="{w}" height="{h}" fill="#aec5ad" fill-opacity="0.45" '
                 f'stroke="#5f805e" stroke-width="2"/><circle cx="{x}" cy="{y}" r="5" fill="#345d46"/></g>')
        p.append(_text(x + 72, y + 8, label, 23))
    p += [_text(98, 546, "1.129°", 34, "#5d755d", 600),
          _lines(98, 586, ["两来源点工作轴", "不是建筑实测方位"], 22, 35),
          _text(86, 291, "来源图符位置 + 表列尺度片", 23, "#6b796f"),
          _text(86, 958, "锚点不移动 · 现有工作轴不升级", 23, "#6b796f")]
    mapper = lambda q: (866 + 1.3 * (q[0] - 15), 363 + 1.3 * (q[1] - 78))
    for item in models["components"]:
        p.append(_component_svg(item, mapper))
    north = models["calibration"]["north_unit_in_source_px"]
    nx, ny = 1458 + 70 * north[0], 452 + 70 * north[1]
    p.append(f'<path d="M1458 452 L{nx:.2f} {ny:.2f} M{nx-6:.2f} {ny+13:.2f} '
             f'L{nx:.2f} {ny:.2f} L{nx+8:.2f} {ny+12:.2f}" fill="none" stroke="#526b5c" stroke-width="3"/>')
    p.append(_text(1454, 359, "图内北", 22, "#526b5c", anchor="middle"))
    p.append(_scale_bar(900, 828, 81 * 1.3))
    p += [_text(875, 291, "门基、门道、阙基可辨段已换算为米", 23, "#6b796f"),
          _text(1195, 898, "图内北向可读；外部基准未知", 22, "#6b796f", anchor="middle"),
          _text(1195, 950, "没有把图内中心对齐成现场中心", 23, "#9c4b36", anchor="middle"),
          _rect(85, 667, 280, 126, "#f9efe1", "#c69c63"),
          _text(225, 717, "0 个共同控制", 28, "#875c2f", 700, "middle"),
          _text(225, 759, "位置与旋转尚未接合", 22, "#875c2f", anchor="middle")]
    return _close_svg(p)


def render_gate_diagnostics(data, models=None):
    """Make scale calibration and independent table comparison inspectable."""
    models = models or build_gate_geometry(data)
    cal = models["calibration"]
    measurements = models["diagnostics"]["dimension_check"]["measurements"]
    ew, ns = measurements["east_west"], measurements["north_south"]
    uri = _raster_uri(data)
    p = _open_svg("标尺量读与门基尺寸核对", f"只用原图 20 m 标尺定尺；{ew['table_length_m']:g} × {ns['table_length_m']:g} m 表列值保留为分开的核对，不参与缩放。")
    p += [_rect(50, 185, 715, 275), _rect(790, 185, 760, 275),
          _text(80, 232, "01  原图标尺", 28, "#294d40", 700)]
    p.append(f'<svg x="80" y="252" width="430" height="140" viewBox="15 389 122 40">'
             f'<image x="0" y="0" width="555" height="434" xlink:href="{uri}"/>'
             '<path d="M30 401v19 M111 401v19" stroke="#bd4b33" stroke-width="0.7"/></svg>')
    p += [_text(524, 294, "81 px → 20 m", 26, "#294d40", 600),
          _lines(524, 334, ["每端约 ±1.5 px", "单一印刷比例尺"], 21, 34),
          _text(80, 428, "名义 0.2469 m/px；量读范围 0.2381–0.2564", 23),
          _text(820, 232, "02  图内北箭", 28, "#294d40", 700)]
    p.append(f'<svg x="820" y="248" width="125" height="175" viewBox="439 65 43 88">'
             f'<image x="0" y="0" width="555" height="434" xlink:href="{uri}"/></svg>')
    angle = abs(cal["north_arrow_angle_from_image_up_clockwise_deg"])
    envelope = cal["north_arrow_reading_angle_envelope_deg"]
    p += [_text(978, 290, f"图面向上偏左约 {angle:.1f}°", 26, "#294d40", 600),
          _lines(978, 334, [f"端点量读造成约 ±{envelope:.1f}° 方向包络", "图内北向 ≠ 已核定的外部基准", "纵横印刷尺度没有独立验证"], 23, 39),
          _rect(50, 485, 760, 532), _rect(835, 485, 715, 532),
          _text(80, 535, "03  同比例边长比较", 28, "#294d40", 700),
          _text(80, 574, "仅比较长宽，图形居中不作任何位置配准", 22, "#6b796f")]
    cx, cy, scale = 430, 768, 12
    for w, h, color, dash in [(ew["image_read_length_m"], ns["image_read_length_m"], "#246a63", False),
                              (ew["table_length_m"], ns["table_length_m"], "#c17932", True)]:
        extra = ' stroke-dasharray="11 8"' if dash else ""
        p.append(f'<rect x="{cx-w*scale/2:.2f}" y="{cy-h*scale/2:.2f}" width="{w*scale:.2f}" height="{h*scale:.2f}" '
                 f'fill="none" stroke="{color}" stroke-width="4"{extra}/>')
    p += [_text(430, 751, f"图读约 {ew['image_read_length_m']:.1f} × {ns['image_read_length_m']:.1f} m", 30, "#246a63", 600, "middle"),
          _text(430, 797, f"表列 {ew['table_length_m']:g} × {ns['table_length_m']:g} m", 28, "#a76028", 500, "middle"),
          _text(80, 974, "实线：平均相对边长　虚线：表列长宽", 23, "#52635d"),
          _text(865, 535, "保留差异与量读范围", 28, "#294d40", 700)]
    for yy, name, value in [(595, "东西", ew), (705, "南北", ns)]:
        lo, hi = value["reading_envelope_m"]
        p += [_text(865, yy, f"{name}：差 {value['difference_m']:+.1f} m", 27, "#426252", 600),
              _text(865, yy + 39, f"人工量读包络约 {lo:.1f}–{hi:.1f} m", 24)]
    reading_conclusion = ("包络均含表值，不能据此宣布吻合。" if models["diagnostics"]["dimension_check"]["all_table_values_inside_reading_envelopes"] else "至少一个表值落在量读包络之外。")
    p += [_lines(865, 824, [reading_conclusion, "端点容差是读图范围，不是置信区间。", "差异也可能涉及边界定义或印刷变形；", "现有小图不足以判定其原因。"], 23, 40)]
    return _close_svg(p)


gate_local_svg = render_gate_local
gate_city_link_svg = render_gate_city_link
gate_diagnostics_svg = render_gate_diagnostics
