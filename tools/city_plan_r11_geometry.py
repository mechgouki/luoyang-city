#!/usr/bin/env python3
"""R11 shared drawing geometry, with source traces and candidate placement apart.

The master frame is the existing Xi'an 1980 source-map AEQD display projection.
No datum transformation, physical-control adjustment, or field registration is
performed.  The returned GeoJSON-shaped objects are local metres, not RFC 7946
longitude/latitude.  Input files are never modified by this module.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from prosperity_gate_geometry import build_gate_geometry
from prosperity_maps import PROJECTION, all_points, projected_features


DATA = "research/city-plan-r11"
GEO_PATH = "research/prosperity-v1/geographic-evidence.json"
GATE_PATH = "research/prosperity-v3/gate-plan.json"
DIM_PATH = "research/prosperity-v1/building-dimensions.json"
AXIS_PATH = "research/prosperity-v4/axis-measurements.json"
AXIS_AUDIT_PATH = "research/prosperity-v4/primary-source-audit.json"
CITY_PATH = "research/prosperity-v4/city-distribution-p451.json"
MODERN_IDS = {"geo-modern-luo-river", "geo-modern-mang-hill-label"}
FRAME_ID = "r11-xian1980-source-local-aeqd"


def _read(root: Path, path: str) -> dict:
    return json.loads((root / path).read_text(encoding="utf-8"))


def _hash(root: Path, path: str) -> str:
    return hashlib.sha256((root / path).read_bytes()).hexdigest()


def _ref(root: Path, ident: str, path: str, pointer: str, **extra: Any) -> dict:
    return {"id": ident, "path": path, "pointer": pointer,
            "sha256": _hash(root, path),
            "locator": path + (" · " + pointer if pointer else ""), **extra}


def _xy(point: list) -> list[float]:
    if len(point) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in point):
        raise ValueError("Expected a finite x/y point")
    return [float(point[0]), float(point[1])]


def _walk_coordinates(coords: list, convert) -> list:
    if coords and isinstance(coords[0], (int, float)):
        return convert(coords)
    return [_walk_coordinates(part, convert) for part in coords]


def _matrix(anchor: list, bearing_deg: float) -> list:
    """A bearing is clockwise from master north; x is east, y is north."""
    angle = math.radians(bearing_deg)
    c, s = math.cos(angle), math.sin(angle)
    return [[c, s, anchor[0]], [-s, c, anchor[1]], [0.0, 0.0, 1.0]]


def _apply(matrix: list, point: list) -> list:
    x, y = _xy(point)
    return [round(matrix[0][0] * x + matrix[0][1] * y + matrix[0][2], 6),
            round(matrix[1][0] * x + matrix[1][1] * y + matrix[1][2], 6)]


def _local_geometry(kind: str, coordinates: list) -> dict:
    """Local trace files use a flat vertex list for one Polygon."""
    coords = copy.deepcopy(coordinates)
    if kind == "Polygon" and coords and isinstance(coords[0][0], (int, float)):
        coords = [coords]
    geometry = {"type": kind, "coordinates": coords}
    if kind == "Polygon":
        if any(len(ring) < 4 or ring[0] != ring[-1] for ring in coords):
            raise ValueError("A traced or dimension-template polygon must close explicitly")
    if kind not in {"Point", "LineString", "MultiLineString", "Polygon", "MultiPolygon"}:
        raise ValueError("Unsupported geometry type: " + kind)
    for point in all_points(geometry):
        _xy(point)
    return geometry


def _transformed(geometry: dict, matrix: list) -> dict:
    return {"type": geometry["type"],
            "coordinates": _walk_coordinates(geometry["coordinates"], lambda p: _apply(matrix, p))}


def _rectangle(width: float, depth: float) -> dict:
    return _local_geometry("Polygon", [
        [-width / 2, -depth / 2], [width / 2, -depth / 2],
        [width / 2, depth / 2], [-width / 2, depth / 2],
        [-width / 2, -depth / 2],
    ])


def _source_role(feature: dict) -> str:
    if feature["layer"] == "layout_envelope":
        return "legacy_display_envelope"
    if feature["layer"] == "regional_reconstruction_range":
        return "source_related_range"
    if feature["geometry"]["type"] == "Point":
        return "source_symbol"
    return "source_remains_line"


def _resolve_binding(spec: dict, anchor: list, bearing: float, **extra: Any) -> dict:
    result = copy.deepcopy(spec)
    result.update({
        "target_frame_id": FRAME_ID,
        "target_anchor_xy_m": list(anchor),
        "resolved_clockwise_bearing_deg": bearing,
        "local_metric_to_master_matrix": _matrix(anchor, bearing),
        "uniform_scale_of_metric_geometry": 1.0,
        "verified_shared_controls": 0,
        "field_registration_verified": False,
        "datum_transformation_performed": False,
        "source_registration_flags_modified": False,
        **extra,
    })
    return result


def _pixel_calibration(data: dict) -> tuple[dict, Any]:
    """An image scale and marked north define local image metres only."""
    cal = copy.deepcopy(data["calibration"])
    scale = cal["scale_bar"]
    start, end = _xy(scale["start_px"]), _xy(scale["end_px"])
    span = math.dist(start, end)
    tol = float(scale.get("endpoint_tolerance_px", 0))
    length = float(scale["length_m"])
    if span <= 2 * tol or length <= 0 or tol < 0:
        raise ValueError("Invalid printed scale bar")
    arrow = cal["north_arrow"]
    tail, tip = _xy(arrow["tail_px"]), _xy(arrow["tip_px"])
    dx, dy = tip[0] - tail[0], tip[1] - tail[1]
    arrow_length = math.hypot(dx, dy)
    arrow_tol = float(arrow.get("endpoint_tolerance_px", 0))
    if arrow_length <= 2 * arrow_tol or arrow_tol < 0:
        raise ValueError("Invalid image north arrow")
    north = [dx / arrow_length, dy / arrow_length]
    east = [-north[1], north[0]]
    origin = _xy(cal["local_origin_px"])
    mpp = length / span

    def convert(point: list) -> list:
        point = _xy(point)
        px, py = point[0] - origin[0], point[1] - origin[1]
        return [mpp * (px * east[0] + py * east[1]),
                mpp * (px * north[0] + py * north[1])]

    cal.update({
        "scale_span_px": span,
        "m_per_px": mpp,
        "m_per_px_reading_range": [length / (span + 2 * tol), length / (span - 2 * tol)],
        "north_unit_in_source_px": north,
        "east_unit_in_source_px": east,
        "north_arrow_angle_from_image_up_clockwise_deg": math.degrees(math.atan2(dx, -dy)),
        "north_arrow_reading_envelope_deg": math.degrees(math.asin(2 * arrow_tol / arrow_length)),
        "external_orientation_verified": False,
        "reading_range_is_statistical_confidence_interval": False,
        "pixel_isotropy_independently_verified": False,
    })
    return cal, convert


def build_geometry(root: Path) -> dict:
    """Build the shared source frame and separately identified candidate layers.

    ``features[*].geometry`` uses ordinary GeoJSON nesting in local metres.
    Source-map projected coordinates are retained at full float precision, using
    the exact pre-existing ``projected_features`` implementation.  Candidate
    attachments are reproducibly rounded to six decimal places; this is never
    an assertion of archaeological accuracy.
    """
    root = Path(root)
    choices = _read(root, DATA + "/frame-bindings.json")
    specifications = {item["id"]: item for item in choices["bindings"]}
    source = _read(root, GEO_PATH)
    source_before = copy.deepcopy(source)
    selected = [item for item in source["features"] if item["id"] not in MODERN_IDS]
    if len(selected) != 28:
        raise ValueError("R11 requires the unchanged 28 historic-source features")
    projected = projected_features(selected)
    by_source = {item["id"]: item for item in projected}
    source_index = {item["id"]: i for i, item in enumerate(source["features"])}
    source_points = {item["id"]: item["projected_geometry"]["coordinates"]
                     for item in projected if item["geometry"]["type"] == "Point"}
    features, bindings, diagnostics, sources = [], [], {}, []

    for item in projected:
        index = source_index[item["id"]]
        role = _source_role(item)
        limits = [item.get("placement_note", ""), item.get("temporal_interpretation", ""),
                  "原图经纬网转换只建立同一来源框；不增加考古实体的定位精度。"]
        if role == "legacy_display_envelope":
            limits.append("北边为旧版显示推定闭合边；此面默认隐藏，绝不作为已证宫墙。")
        feature = {
            "id": item["id"], "component_id": item["id"],
            "entity_ids": [item["entity_id"]] if item.get("entity_id") else [],
            "label": item["label"], "geometry": copy.deepcopy(item["projected_geometry"]),
            "geometry_role": role, "placement_status": "source_frame_reuse",
            "source_refs": [_ref(root, "source06a-" + item["id"], GEO_PATH,
                                 f"/features/{index}",
                                 url="https://whc.unesco.org/uploads/nominations/1442.pdf#page=3457",
                                 locator="2012管理规划图06a；PDF第3457页")],
            "limits": [s for s in limits if s],
            "source_feature_id": item["id"], "source_frame_id": "frame-06a",
            "source_layer": item["layer"],
            "period": item.get("source_historical_period", item.get("source_period")),
            "default_visible": role != "legacy_display_envelope",
            "field_registration_verified": False,
            "source_geometry_preserved": True,
        }
        if item.get("rendering"):
            feature["source_rendering"] = copy.deepcopy(item["rendering"])
        features.append(feature)
    sources.append(_ref(root, "source06a", GEO_PATH, "/features",
                        url="https://whc.unesco.org/uploads/nominations/1442.pdf#page=3457"))

    # The two map symbols define only a working bearing, not a measured axis.
    changhe = source_points["geo-changhe-palace-gate"]
    taiji = source_points["geo-taiji-hall-reference"]
    dx, dy = taiji[0] - changhe[0], taiji[1] - changhe[1]
    palace_bearing = math.degrees(math.atan2(dx, dy))
    source_axis_length = math.hypot(dx, dy)

    gate_data = _read(root, GATE_PATH)
    local_gate = build_gate_geometry(gate_data)
    gate_binding = _resolve_binding(
        specifications["bind-changhe-s37"], changhe, palace_bearing,
        source_local_origin_px=gate_data["calibration"]["local_origin_px"],
        local_calibration=local_gate["calibration"],
        source_component_count=len(local_gate["components"]),
    )
    bindings.append(gate_binding)
    for i, component in enumerate(local_gate["components"]):
        local = _local_geometry(component["geometry_type"], component["coordinates_m"])
        features.append({
            "id": "r11-changhe-" + component["id"],
            "component_id": component["id"], "entity_ids": ["ic_changhe_palace"],
            "label": component.get("label", component.get("name", component["id"])),
            "geometry": _transformed(local, gate_binding["local_metric_to_master_matrix"]),
            "geometry_role": "local_plan_direction_trace" if component["kind"] == "foundation_connection" else "local_plan_trace",
            "placement_status": "candidate_source_symbol_attachment",
            "binding_id": gate_binding["id"],
            "source_refs": [_ref(root, "S37-" + component["id"], GATE_PATH,
                                 f"/components/{i}",
                                 url="https://whc.unesco.org/uploads/nominations/1442.pdf#page=1962",
                                 locator="宫城阊阖门平剖图；附录37，PDF第1962页")],
            "limits": [component.get("limits", component.get("note", ""))]
                      if isinstance(component.get("limits", component.get("note", "")), str)
                      else list(component.get("limits", [])),
            "evidence_status": component["evidence_status"],
            "local_geometry_m": local,
            "trace_tolerance_m_nominal": component["trace_tolerance_m_nominal"],
            "period": "魏晋至北魏叠压遗存；局部线不自动代表516—528每年的完整建成状态",
            "region_ids": ["R03", "R07"],
            "default_visible": True, "field_registration_verified": False,
        })
        features[-1]["limits"] += [
            "原图局部轮廓与尺度保留；母图平移、朝向为候选工作绑定。",
            "图示原点与06a门符是否同一物理中心未证；两阙开放边不补闭合。",
        ]
        features[-1]["limits"] = [s for s in features[-1]["limits"] if s]
    sources.append(_ref(root, "S37", GATE_PATH, "",
                        url="https://whc.unesco.org/uploads/nominations/1442.pdf#page=1962"))
    diagnostics["changhe_local_scale_check"] = local_gate["diagnostics"]

    # Dimension patches are their own role; they are never declared excavated
    # outlines. The more detailed Taiji dimensional alternatives stay recorded.
    dimension_data = _read(root, DIM_PATH)
    axis_data = _read(root, AXIS_PATH)
    city_data = _read(root, CITY_PATH)
    axis_audit = _read(root, AXIS_AUDIT_PATH)
    template_specs = [
        ("r11-taiji-scale", "taiji-main-base-scale", "太极殿遗址约100×60米尺度片", [],
         "bind-taiji-scale", taiji, palace_bearing,
         float(dimension_data["massing_items"][2]["plan_dimensions_m"]["east_west_approx"]),
         float(dimension_data["massing_items"][2]["plan_dimensions_m"]["north_south_approx"]),
         "scale_template", DIM_PATH, "/massing_items/2", ["R03"],
         "魏晋至北魏遗址尺度约数；不是上部殿身足迹",
         ["表列100×60米仅为基址约数；P4.2另列北边102.3、南边98.4、南北58—61.5米。",
          "没有把这些边长拼成新的实测梯形；原图符中心和宫轴朝向均为候选工作参照。"]),
        ("r11-gate2-scale", "palace-gate2-base-scale", "二号宫门约44.5×24米尺度片", [],
         "bind-gate2-scale", _apply(_matrix(changhe, palace_bearing), [0, 95]),
         palace_bearing, float(axis_data["second_gate"]["foundation_ew_m"]),
         float(axis_data["second_gate"]["foundation_ns_m"]),
         "scale_template", AXIS_PATH, "/second_gate", ["R03"],
         "魏晋始建、北魏修补沿用；后期改造不合并复原",
         ["95米为阊阖门以北的报告约距，量测基点未定；本图将其临时作为模板参照点间距。",
          "早报南北23米与后报24米分开保留；三通道不据数量补柱网或门阙。"]),
        ("r11-gate3-surviving-scale", "palace-gate3-south-remnant-scale", "三号宫门早期南半残存约40×10米", [],
         "bind-gate3-surviving-scale", _apply(_matrix(changhe, palace_bearing), [0, 175]),
         palace_bearing, float(axis_data["third_gate"]["early"]["surviving_ew_m_approx"]),
         float(axis_data["third_gate"]["early"]["surviving_ns_m_approx"]),
         "partial_surviving_scale_template", AXIS_PATH, "/third_gate/early", ["R03"],
         axis_data["third_gate"]["early"]["period"],
         ["40×10米只表达早期残存南半部尺度，不代表完整门基。",
          "80米北向约距端点未定；残存尺度片参照点只用于候选布置。",
          "中期55×45米夯土与北朝晚期柱网不并入516—528盛时图。"]),
        ("r11-jianchun-scale", "jianchun-gate-base-scale", "建春门约12.5×30米尺度片", ["gate_jianchun"],
         "bind-jianchun-scale", source_points["geo-jianchun-gate"], 0.0,
         float(city_data["anchored_buildings"][1]["reported_footprint_m"]["east_west"]),
         float(city_data["anchored_buildings"][1]["reported_footprint_m"]["north_south"]),
         "scale_template", CITY_PATH, "/anchored_buildings/1", ["R04"],
         "东汉至北魏多期遗址；非单期完整门楼足迹",
         ["矩形仅为报告尺寸片，不是2018图二残破构件边界或整幅图框。",
          "朝向暂按母图东西、南北轴；原址精确方位及角点对应未证。"]),
    ]
    for ident, component, label, entities, bind_id, anchor, bearing, ew, ns, role, path, pointer, regions, period, limits in template_specs:
        binding = _resolve_binding(specifications[bind_id], anchor, bearing,
                                   dimensions_m={"east_west": ew, "north_south": ns})
        bindings.append(binding)
        reference_details = {
            "r11-taiji-scale": {
                "url": "https://whc.unesco.org/uploads/nominations/1442.pdf#page=1930",
                "locator": "申遗附表M03／太极殿；PDF第1930—1931页，约100×60米基址尺度",
            },
            "r11-gate2-scale": {
                "url": "https://www.kuba.co.jp/nabunken1020/img/nabunken20121020.pdf",
                "locator": "钱国祥2012中日合作考古报告，印刷第28—30页二号宫门段；23／24米异报另见primary-source-audit",
            },
            "r11-gate3-surviving-scale": {
                "url": "https://www.kuba.co.jp/nabunken1020/img/nabunken20121020.pdf",
                "locator": "钱国祥2012中日合作考古报告，印刷第28—30页三号宫门早期南部残存段",
            },
            "r11-jianchun-scale": {
                "url": "https://www.sohu.com/a/298263205_199807",
                "locator": "钱国祥《汉魏洛阳城城门与宫院门的考察研究》2018图二与建春门段；本站P4.5.1 C02尺寸卡",
            },
        }[ident]
        features.append({
            "id": ident, "component_id": component, "entity_ids": entities,
            "label": label, "geometry": _transformed(_rectangle(ew, ns), binding["local_metric_to_master_matrix"]),
            "geometry_role": role, "placement_status": "candidate_dimension_template",
            "binding_id": bind_id, "source_refs": [_ref(root, component, path, pointer, **reference_details)],
            "limits": limits, "period": period, "region_ids": regions,
            "dimensions_m": {"east_west": ew, "north_south": ns},
            "default_visible": True, "field_registration_verified": False,
        })
    sources.extend([_ref(root, "building-dimensions", DIM_PATH, "/massing_items"),
                    _ref(root, "palace-axis-measurements", AXIS_PATH, ""),
                    _ref(root, "palace-axis-audit", AXIS_AUDIT_PATH, ""),
                    _ref(root, "city-dimension-cards", CITY_PATH, "/anchored_buildings")])
    diagnostics["palace_axis_not_closed"] = {
        "source_map_symbol_distance_m": source_axis_length,
        "source_working_bearing_deg": palace_bearing,
        "reported_shared_steps_m": [95, 80],
        "reported_third_gate_to_taiji_alternatives_m": [200, 300],
        "reported_chain_alternatives_m": [375, 475],
        "other_report_total_m": axis_audit["external_total"]["distance_m"],
        "same_measurement_endpoints_verified": False,
        "chain_stretched_to_source_symbols": False,
        "unclosed_difference_from_375_m": source_axis_length - 375,
        "unclosed_difference_from_475_m": source_axis_length - 475,
        "note": "二、三门沿报告约距候选排列；不把剩余差距吸收为强制拉伸或新增已证中轴路。",
    }

    # The newly acquired published Yongning plan is supplied by the independent
    # primary-plan audit. Missing data is visible in diagnostics, never replaced
    # by a guessed complete monastery plan.
    yongning_path = DATA + "/yongning-published-plan.json"
    if (root / yongning_path).exists():
        plan = _read(root, yongning_path)
        cal, pixel_to_m = _pixel_calibration(plan)
        y_binding = _resolve_binding(
            specifications["bind-yongning-published-plan"],
            source_points["geo-yongning-pagoda-reference"], 0.0,
            source_local_origin_px=plan["calibration"]["local_origin_px"],
            local_calibration=cal,
            source_component_count=len(plan["components"]),
        )
        bindings.append(y_binding)
        published_refs = {ref["id"]: ref for ref in plan.get("source_refs", []) if isinstance(ref, dict)}
        primary_ref = next(iter(published_refs.values()), {})
        supporting_refs = {ref["id"]: (i, ref) for i, ref in enumerate(plan.get("supporting_source_refs", []))
                           if isinstance(ref, dict)}
        published_locator = (
            "杭侃《洛阳伽蓝记》慧嶷故事四论，《故宫博物院院刊》2025年第11期，"
            "印页061图二右图／PDF第9页；重刊1996年永宁寺考古报告总平面"
        )
        for i, component in enumerate(plan["components"]):
            native = _local_geometry(component.get("geometry_type", component.get("type")),
                                     component.get("source_px", component.get("coordinates_px")))
            local = {"type": native["type"],
                     "coordinates": _walk_coordinates(native["coordinates"], pixel_to_m)}
            comp_id = component.get("component_id", component["id"])
            role = component.get("geometry_role", "published_plan_trace")
            if native["type"] == "Point" and role == "published_plan_trace":
                role = "published_plan_marker"
            refs = [_ref(root, "yongning-published-" + component["id"], yongning_path,
                         f"/components/{i}", url=primary_ref.get("url"),
                         locator=published_locator + "；" + component.get("label", component["id"]),
                         published_source_ids=copy.deepcopy(component.get("source_refs", [])))]
            for supporting_id in component.get("source_refs", []):
                if isinstance(supporting_id, str) and supporting_id in supporting_refs:
                    source_i, supporting = supporting_refs[supporting_id]
                    refs.append(_ref(
                        root, supporting_id, yongning_path, f"/supporting_source_refs/{source_i}",
                        url=supporting.get("url"),
                        locator="奈良国立文化財研究所年報1995，印页2—3；永宁寺西门调查文字，原图版留白",
                        source_role=supporting.get("source_role"),
                    ))
            limits = component.get("limits", [])
            if isinstance(limits, str):
                limits = [limits]
            phase = component.get("phase", plan.get("phase", plan.get("period", "北魏永宁寺刊载平面")))
            period_label = phase.get("source_phase", "北魏永宁寺刊载平面") if isinstance(phase, dict) else phase
            features.append({
                "id": "r11-yongning-" + component["id"],
                "component_id": comp_id, "entity_ids": component.get("entity_ids", ["ic_yongning"]),
                "label": component.get("label", component["id"]),
                "geometry": _transformed(local, y_binding["local_metric_to_master_matrix"]),
                "geometry_role": role,
                "placement_status": "candidate_source_symbol_attachment",
                "binding_id": y_binding["id"], "source_refs": refs,
                "limits": list(limits) + [
                    "刊载平面描线按同一图尺等比转换；不与06a寺墙残段强制拟合。",
                    "塔座图示中心向06a广义塔符候选绑定；同一物理中心及外部真北均未验证。",
                ],
                "evidence_status": component.get("evidence_status"),
                "source_legend": component.get("source_legend"),
                "period": period_label, "source_phase": copy.deepcopy(phase),
                "region_ids": ["R07"], "local_geometry_m": local,
                "default_visible": component.get("default_visible", True),
                "field_registration_verified": False,
            })
            if component.get("trace_uncertainty_px") is not None:
                features[-1]["trace_tolerance_m_nominal"] = float(component["trace_uncertainty_px"]) * cal["m_per_px"]
        sources.append(_ref(root, "yongning-published-plan", yongning_path, "",
                            url=primary_ref.get("url"), locator=published_locator))
        diagnostics["yongning_published_plan"] = {
            "loaded": True, "components": len(plan["components"]),
            "calibration": cal,
            "source_diagnostics": copy.deepcopy(plan.get("diagnostics", {})),
            "source_measurements": copy.deepcopy(plan.get("measurements", {})),
            "source_validation": copy.deepcopy(plan.get("validation", {})),
            "source_06a_walls_changed": False,
            "fit_to_table_212_by_301_performed": False,
            "source_plans_share_physical_controls": False,
        }
    else:
        diagnostics["yongning_published_plan"] = {
            "loaded": False, "required_path": yongning_path,
            "note": "新图未提交；不生成替代寺院、佛殿、门址或院界。",
        }

    # A second source overview is an explicitly separate scenario.  Its grey
    # rammed-earth symbols are not hall footprints; investigation blocks remain
    # point symbols.  A one-anchor attachment preserves disagreement with 06a.
    palace_path = DATA + "/palace-2013-published-plan.json"
    if (root / palace_path).exists():
        plan = _read(root, palace_path)
        cal, native_to_m = _pixel_calibration(plan)
        cal["native_pdf_vector_to_canonical_frame_is_uniform"] = True
        p_binding = _resolve_binding(
            specifications["bind-palace2013-published-overview"], changhe, 0.0,
            source_local_origin_px=plan["calibration"]["local_origin_px"],
            local_calibration=cal,
            source_component_count=len(plan["components"]),
        )
        bindings.append(p_binding)
        source_refs = [ref for ref in plan.get("source_refs", []) if isinstance(ref, dict)]
        primary_ref = source_refs[0] if source_refs else {}
        locator = "奈良文化財研究所紀要2013，印页52图69「北魏宮城の構造と調査地」；宫城概览图"
        for i, component in enumerate(plan["components"]):
            native = _local_geometry(component.get("geometry_type", component.get("type")),
                                     component.get("source_px", component.get("coordinates_px")))
            local = {"type": native["type"],
                     "coordinates": _walk_coordinates(native["coordinates"], native_to_m)}
            limits = component.get("limits", [])
            if isinstance(limits, str):
                limits = [limits]
            phase = component.get("phase", plan.get("phase", "北魏宫城概览；逐条细分时相未定"))
            period_label = phase.get("source_phase", "北魏宫城概览；逐条细分时相未定") if isinstance(phase, dict) else phase
            features.append({
                "id": "r11-palace2013-" + component["id"],
                "component_id": component.get("component_id", component["id"]),
                "entity_ids": component.get("entity_ids", []),
                "label": component.get("label", component["id"]),
                "geometry": _transformed(local, p_binding["local_metric_to_master_matrix"]),
                "geometry_role": component.get("geometry_role", "published_overview_trace"),
                "placement_status": "candidate_source_symbol_attachment",
                "binding_id": p_binding["id"],
                "source_plan_id": "palace-2013", "toggle_group": "palace-2013",
                "default_visible": False, "region_ids": ["R03"],
                "source_refs": [_ref(root, "palace2013-" + component["id"], palace_path,
                                     f"/components/{i}", url=primary_ref.get("url"),
                                     locator=locator + "；" + component.get("label", component["id"]))],
                "limits": list(limits) + [
                    "图69按自身图尺等比接入，阊阖调查区图示中心只作一处候选绑定；不是已证现场控制点。",
                    "隔壁、版筑、道路和调查标识保持原图性质；灰色版筑范围不代表上部殿身或新核实完整房基。",
                    "与06a宫城源框独立对照；不以第二个太极图符强制缩放、剪切或移动整组几何。",
                ],
                "evidence_status": component.get("evidence_status"),
                "source_legend": component.get("source_legend"),
                "source_type": component.get("source_type") or (component.get("source_legend") or {}).get("source_type"),
                "period": period_label, "source_phase": copy.deepcopy(phase),
                "phase_unknown": component.get("phase_unknown", phase.get("phase_unknown", True) if isinstance(phase, dict) else True),
                "local_geometry_m": local,
                "field_registration_verified": False,
            })
            if component.get("trace_uncertainty_px") is not None:
                features[-1]["trace_tolerance_m_nominal"] = float(component["trace_uncertainty_px"]) * cal["m_per_px"]
        sources.append(_ref(root, "palace2013-published-overview", palace_path, "",
                            url=primary_ref.get("url"), locator=locator))
        compare = {}
        diagnostic_points = plan.get("diagnostic_points", {})
        if "changhe_reference_px" in diagnostic_points and "taiji_reference_px" in diagnostic_points:
            c_local = native_to_m(diagnostic_points["changhe_reference_px"])
            t_local = native_to_m(diagnostic_points["taiji_reference_px"])
            candidate_taiji = _apply(p_binding["local_metric_to_master_matrix"], t_local)
            native_distance = math.dist(c_local, t_local)
            offset = [candidate_taiji[0] - taiji[0], candidate_taiji[1] - taiji[1]]
            compare = {
                "published_symbol_distance_m": native_distance,
                "source06a_symbol_distance_m": source_axis_length,
                "distance_difference_m": source_axis_length - native_distance,
                "candidate_published_taiji_xy_m": candidate_taiji,
                "source06a_taiji_xy_m": list(taiji),
                "candidate_minus_source06a_taiji_xy_m": offset,
                "candidate_taiji_symbol_displacement_m": math.hypot(*offset),
                "metric_scale_fitted_to_second_symbol": False,
                "same_physical_points_verified": False,
                "note": "数值比较两幅概化图符及一锚候选绑定的差异，不是现场定位误差或置信范围。",
            }
        diagnostics["palace2013_published_plan"] = {
            "loaded": True, "components": len(plan["components"]),
            "default_visible": False, "toggle_group": "palace-2013",
            "calibration": cal,
            "source_measurements": copy.deepcopy(plan.get("measurements", {})),
            "source_validation": copy.deepcopy(plan.get("validation", {})),
            "source_comparison": compare,
            "source06a_geometry_changed": False,
            "published_rammed_earth_is_building_footprint": False,
            "verified_shared_controls": 0,
        }
    else:
        diagnostics["palace2013_published_plan"] = {
            "loaded": False, "required_path": palace_path,
            "note": "宫城刊图轮廓尚未提交；不生成替代夯土块、宫墙或院落。",
        }

    ids = [item["id"] for item in features]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate R11 geometry feature id")
    for feature in features:
        _local_geometry(feature["geometry"]["type"], feature["geometry"]["coordinates"])
    if source != source_before:
        raise ValueError("Source map was mutated")
    source_checks = {item["id"]: item["geometry"] for item in features if item["placement_status"] == "source_frame_reuse"}
    if any(source_checks[item["id"]] != item["projected_geometry"] for item in projected):
        raise ValueError("A source feature changed during projection reuse")
    points = [point for feature in features for point in all_points(feature["geometry"])]
    xs, ys = zip(*points)
    frame = {
        "id": FRAME_ID, "title": "西安1980来源图的共同复原绘图母框",
        "source_crs": "EPSG:4610", "datum": "Xi'an 1980",
        "projection_pipeline": PROJECTION, "units": "m",
        "axis_order": ["east", "north"], "x_direction": "east", "y_direction": "north",
        "origin_longitude_latitude": [112.6166666667, 34.7333333333],
        "datum_transformation_performed": False, "is_wgs84": False,
        "new_field_coordinates": 0, "verified_shared_controls": 0,
        "source_bounds_xy_m": [min(p[0] for item in projected for p in all_points(item["projected_geometry"])),
                               min(p[1] for item in projected for p in all_points(item["projected_geometry"])),
                               max(p[0] for item in projected for p in all_points(item["projected_geometry"])),
                               max(p[1] for item in projected for p in all_points(item["projected_geometry"]))],
        "bounds_xy_m": [min(xs), min(ys), max(xs), max(ys)],
        "note": "统一绘图坐标使现有材料可联读；候选平移与转角不构成新测地配准。",
    }
    diagnostics.update({
        "source_feature_count": 28, "source_geometry_exactly_preserved": True,
        "excluded_modern_feature_ids": sorted(MODERN_IDS),
        "feature_count": len(features),
        "geometry_role_counts": dict(Counter(f["geometry_role"] for f in features)),
        "placement_status_counts": dict(Counter(f["placement_status"] for f in features)),
        "verified_shared_controls": 0,
        "new_field_coordinates": 0,
        "invented_unknown_courtyard_polygons": 0,
        "omitted_metric_outline_studies": [
            {"object": "太极东堂", "reason": "东西尺寸和殿间间隔有报道，南北偏移未定；不在本层暗设对齐中心。"},
            {"object": "太极北部宫院及2017东北院", "reason": "部分构件尺度可读；完整院界和跨年同体未核，不合成闭合面。"},
            {"object": "白马坊建筑和完整坊界", "reason": "有道路报告尺度，无可追摹建筑/坊界平面；留给母图相对范围对象层。"},
        ],
        "source_inputs_unchanged": True,
    })
    return {"frame": frame, "features": features, "bindings": bindings,
            "sources": sources, "diagnostics": diagnostics}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, help="Optional derived JSON destination; does not edit evidence inputs")
    args = parser.parse_args()
    result = build_geometry(args.root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"frame": result["frame"]["id"],
                      "features": len(result["features"]),
                      "bindings": len(result["bindings"]),
                      "yongning_loaded": result["diagnostics"]["yongning_published_plan"]["loaded"]}, ensure_ascii=False))
