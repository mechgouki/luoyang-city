#!/usr/bin/env python3
"""Project unchanged R11 ground geometry into one declared pictorial plane.

The homography is a composition aid, not a camera reconstruction or field
registration.  No height is assigned.  Detail views are uniform crops of the
same projection.  The old panorama is hashed but never sampled as evidence.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import math
from pathlib import Path

import numpy as np

from city_plan_r11_geometry import build_geometry
from prosperity_maps import all_points


CANVAS = [1672, 941]
BASELINE = "research/city-spatial-r9/panorama-v13-r2-source.png"
BASELINE_SHA = "b2bc1486c1e6a7461fcbafd7234b4e15365cc3f65d3f454eb20882818284ade4"
BASELINE_COMMIT = "129abaee724870ec00bc25c6e2fd2998a215063b"
FAMILY = "Noto Sans CJK SC, sans-serif"
INK = "#263f3a"
PAPER = "#faf9f5"
COLORS = {"wall": "#4d847c", "tower": "#397d9a", "gate": "#bd653e", "hall": "#776599", "palace": "#8b7847", "context": "#c1c9c2"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(matrix, point):
    q = np.asarray(matrix, dtype=float) @ np.array([point[0], point[1], 1.0])
    if not math.isfinite(float(q[2])) or float(q[2]) <= 0:
        raise ValueError("Projection has a non-positive ground-plane denominator")
    return [float(q[0] / q[2]), float(q[1] / q[2])]


def walk(coords, matrix):
    if coords and isinstance(coords[0], (int, float)):
        return project(matrix, coords)
    return [walk(part, matrix) for part in coords]


def bounds(features, ids):
    pts = [p for ident in ids for p in all_points(features[ident]["projected_geometry"])]
    return [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)]


def centre(geometry):
    pts = list(all_points(geometry))
    return [(min(p[k] for p in pts) + max(p[k] for p in pts)) / 2 for k in (0, 1)]


def matrix_for(features):
    # Exactly two display anchors plus declared global projection parameters.
    # No third landmark is force-fitted, no object receives a private transform.
    p = features["geo-yongning-pagoda-reference"]["geometry"]["coordinates"]
    q = features["geo-changhe-palace-gate"]["geometry"]["coordinates"]
    a, g = 0.38, 0.00012
    A = np.array([[p[1], 1.0], [q[1], 1.0]])
    b, c = np.linalg.solve(A, [515 * (1 + g * p[1]) - a * p[0], 650 * (1 + g * q[1]) - a * q[0]])
    e, f = np.linalg.solve(A, [430 * (1 + g * p[1]), 315 * (1 + g * q[1])])
    return [[a, float(b), float(c)], [0.0, float(e), float(f)], [0.0, g, 1.0]]


def visibility(feature):
    ident = feature["id"]
    if feature.get("source_plan_id") == "palace-2013":
        return False, "2013宫城概览逐项时相未知，独立对照层不作为本轮地上建筑底稿。"
    if feature["geometry_role"] == "legacy_display_envelope":
        return False, "旧显示包络的北缘不是已证宫墙，排除。"
    if ident == "geo-outer-city-related-remains":
        return False, "外郭相关遗存范围不是连续城墙，不送入艺术编辑导图。"
    if ident == "geo-yongning-temple-walls":
        return False, "旧06a寺墙另存于R11，不与新刊23构件拼接或混合为一座寺院。"
    if feature["geometry"]["type"] == "Point":
        return False, "点符不是建筑占地；仅在有文字的审看版另示必要参照。"
    return True, "按来源角色投影；未给高度，开放线保持开放。"


def polygon_paths(geometry):
    kind, coords = geometry["type"], geometry["coordinates"]
    if kind == "LineString":
        return [(coords, False)]
    if kind == "MultiLineString":
        return [(p, False) for p in coords]
    if kind == "Polygon":
        return [(p, True) for p in coords]
    if kind == "MultiPolygon":
        return [(p, True) for poly in coords for p in poly]
    return []


def style(feature, detail=False):
    ident = feature["id"]
    color, fill, dash, width = COLORS["context"], "none", None, 1.2
    if ident == "geo-palace-walls":
        color, width = COLORS["palace"], 2.0
    if "underground" in ident:
        dash = "4 4"
    if ident.startswith("r11-changhe-"):
        color, width = COLORS["palace"], 1.6
        fill = color if feature["geometry"]["type"] == "Polygon" else "none"
    if ident.startswith("r11-") and "scale" in ident:
        color, fill, dash, width = COLORS["palace"], COLORS["palace"], "4 3", 1.5
    if ident.startswith("r11-yongning-"):
        color, width = COLORS["wall"], 2.0
        if "WALL" in ident:
            dash = "6 3"
        if "TOWER-FOUNDATION" in ident:
            color, fill, dash, width = "#a7a9aa", "none", "5 4", 1.4
        elif "TOWER-" in ident:
            color, fill, width = COLORS["tower"], COLORS["tower"], 1.7
        elif "GATE-" in ident:
            color, fill, width = COLORS["gate"], COLORS["gate"], 1.7
        elif "BUDDHA-HALL" in ident:
            color, fill, width = COLORS["hall"], COLORS["hall"], 1.7
        elif "DITCH" in ident:
            color, width = "#91aeb8", 1.1
        elif "ROAD" in ident:
            color, width = "#9aa69a", 1.2
    if detail:
        width = max(width, 2.0)
    return color, fill, dash, width


def svg_start(width, height, title):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
            f'<title>{html.escape(title)}</title>', f'<rect width="{width}" height="{height}" fill="{PAPER}"/>',
            '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="#526c64"/></marker></defs>']


def text(parts, x, y, value, size=20, color=INK, weight=400, anchor="start"):
    parts.append(f'<text x="{x}" y="{y}" font-family="{FAMILY}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{html.escape(value)}</text>')


def line(parts, points, color=INK, width=1.5, dash=None, marker=False):
    d = "M" + " L".join(f"{p[0]:.4f},{p[1]:.4f}" for p in points)
    parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"' + (f' stroke-dasharray="{dash}"' if dash else "") + (' marker-end="url(#arrow)"' if marker else "") + '/>')


def draw_features(parts, features, detail_matrix=None, yongning_only=False):
    for feature in features:
        if not feature["visible_in_clean_guide"]:
            continue
        if yongning_only and not feature["id"].startswith("r11-yongning-"):
            continue
        geom = copy.deepcopy(feature["projected_geometry"])
        if detail_matrix is not None:
            geom["coordinates"] = walk(geom["coordinates"], detail_matrix)
        color, fill, dash, width = style(feature, detail_matrix is not None)
        parts.append(f'<g data-feature-id="{feature["id"]}" data-geometry-role="{feature["geometry_role"]}">')
        for points, closed in polygon_paths(geom):
            d = "M" + " L".join(f"{p[0]:.4f},{p[1]:.4f}" for p in points) + (" Z" if closed else "")
            parts.append(f'<path d="{d}" fill="{fill}" fill-opacity="0.21" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"' + (f' stroke-dasharray="{dash}"' if dash else "") + '/>')
        parts.append('</g>')


def callout(parts, point, end, label, color=INK, sub=None):
    x, y = end
    line(parts, [point, [x, y - 8]], color, 1.1)
    def approximate_width(value, size):
        return sum(0.58 if ord(char) < 128 else 1.0 for char in value) * size
    box_width = max(approximate_width(label, 20), approximate_width(sub or "", 15)) + 14
    parts.append(f'<rect x="{x - 5}" y="{y - 35}" width="{box_width}" height="{58 if sub else 30}" fill="{PAPER}"/>')
    text(parts, x, y - 13, label, 20, color, 600)
    if sub:
        text(parts, x, y + 13, sub, 15, "#68746d")


def write_svg(output, name, parts, render):
    path = output / f"{name}.svg"
    path.write_text("\n".join(parts + ["</svg>"]) + "\n", encoding="utf-8")
    if render:
        import cairosvg
        cairosvg.svg2png(url=str(path), write_to=str(path.with_suffix(".png")))


def build(root: Path, output: Path, render=True):
    root, output = Path(root), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if sha(root / BASELINE) != BASELINE_SHA:
        raise ValueError("V13r2 baseline image identity changed")
    geometry = build_geometry(root)
    raw = {f["id"]: f for f in geometry["features"]}
    H = matrix_for(raw)
    if abs(float(np.linalg.det(H))) < 1e-12:
        raise ValueError("Singular pictorial projection")
    # A uniform display crop; it is never a new placement of the temple.
    detail = [[5.2, 0.0, -1830.0], [0.0, 5.2, -1784.0], [0.0, 0.0, 1.0]]
    projected = []
    for source in geometry["features"]:
        f = copy.deepcopy(source)
        f["projected_geometry"] = {"type": source["geometry"]["type"], "coordinates": walk(source["geometry"]["coordinates"], H)}
        f["visible_in_clean_guide"], f["guide_visibility_reason"] = visibility(source)
        f["visible_in_review_guide"] = f["visible_in_clean_guide"] or source["id"] == "r11-yongning-YN11-GATE-E-MARK"
        f["source_geometry_sha256"] = hashlib.sha256(json.dumps(source["geometry"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        f["ground_bbox_px"] = bounds({f["id"]: f}, [f["id"]])
        f["ground_centre_px"] = project(H, centre(source["geometry"]))
        f["matrix_id"] = "r12-shared-ground-homography-v1"
        projected.append(f)
    features = {f["id"]: f for f in projected}
    groups = {
        "yongning_wall_segments": [f["id"] for f in projected if f["id"].startswith("r11-yongning-YN11-WALL")],
        "yongning_tower_plinth": ["r11-yongning-YN11-TOWER-PLINTH"],
        "yongning_south_gate": ["r11-yongning-YN11-GATE-S"],
        "yongning_buddha_hall": ["r11-yongning-YN11-BUDDHA-HALL"],
        "changhe_main_base": ["r11-changhe-gate-main-base"],
        "changhe_west_que_visible_edge": ["r11-changhe-gate-west-que"],
        "changhe_east_que_visible_edge": ["r11-changhe-gate-east-que"],
        "taiji_scale_patch": ["r11-taiji-scale"],
    }
    key_bounds = {}
    for name, ids in groups.items():
        bb = bounds(features, ids)
        key_bounds[name] = {"feature_ids": ids, "ground_bbox_xyxy_px": bb,
                            "ground_bbox_xyxy_percent": [100 * bb[k] / CANVAS[k % 2] for k in range(4)],
                            "projected_group_bbox_centre_px": [(bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2],
                            "individual_ground_centres_px": {i: features[i]["ground_centre_px"] for i in ids}}
    source_paths = {s["path"] for s in geometry["sources"]}
    source_paths |= {"research/city-plan-r11/frame-bindings.json", BASELINE,
                     "tools/city_plan_r11_geometry.py", "tools/prosperity_maps.py", "tools/prosperity_gate_geometry.py", "tools/panorama_r12_projection.py"}
    hashes = {p: sha(root / p) for p in sorted(source_paths)}
    anchors = [
        {"feature_id": "geo-yongning-pagoda-reference", "target_ground_pixel": [515, 430], "definition": "旧全景木塔地面基脚附近的构图参照；不是塔顶、屋脊或现场控制。"},
        {"feature_id": "geo-changhe-palace-gate", "target_ground_pixel": [650, 315], "definition": "旧全景宫前入口地面附近的构图参照；不是门楼屋脊或现场控制。"},
    ]
    for a in anchors:
        a["r11_source_xy_m"] = raw[a["feature_id"]]["geometry"]["coordinates"]
        a["actual_projected_ground_pixel"] = project(H, a["r11_source_xy_m"])
        a["display_anchor_residual_px"] = math.dist(a["target_ground_pixel"], a["actual_projected_ground_pixel"])
        a["is_verified_field_control"] = False
    taiji = project(H, raw["geo-taiji-hall-reference"]["geometry"]["coordinates"])
    data = {"schema": "luoyang-panorama-r12-ground-projection-v1", "research_version": "R12.1", "candidate_version": "V14",
            "baseline_source_sha": BASELINE_COMMIT, "baseline_source_path": BASELINE, "source_pixel_hash": BASELINE_SHA,
            "source_frame": geometry["frame"], "source_inputs_sha256": hashes,
            "canvas_px": CANVAS, "matrix_id": "r12-shared-ground-homography-v1", "source_xy_m_to_canvas_homography": H,
            "inverse_homography": np.linalg.inv(np.asarray(H)).tolist(),
            "projection_formula": "[u,v,w]^T=H*[x_east_m,y_north_m,1]^T; canvas=(u/w,v/w)",
            "fixed_composition_parameters": {"a_px_per_m": 0.38, "g_per_m": 0.00012, "cross_street_rows_horizontal": True,
                                             "two_display_anchor_fit_only": True, "per_object_transform_count": 0},
            "display_anchors": anchors,
            "old_taiji_composition_reference": {"rough_ground_pixel": [610, 175], "used_for_fitting": False, "uncertain_visual_pick": True,
                                               "new_ground_pixel": taiji, "new_minus_old_px": [taiji[0] - 610, taiji[1] - 175],
                                               "note": "仅说明旧全景地面构图与共同平面不能逐像素套准；不是遗址偏移量。"},
            "detail_view": {"canvas_px": [1600, 900], "overview_pixel_to_detail_pixel": detail,
                            "source_xy_m_to_detail_homography": (np.asarray(detail) @ np.asarray(H)).tolist(),
                            "uniform_display_zoom": 5.2, "independent_relayout": False},
            "key_ground_bounds": key_bounds, "features": projected,
            "field_registration_verified": False, "new_ancient_coordinates": 0, "new_ancient_bank_geometries": 0,
            "new_verified_shared_controls": 0, "assigned_building_heights": 0, "historic_camera_reconstructed": False,
            "source_06a_or_R11_geometry_modified": False,
            "limits": ["同方向虚拟视点底稿，不是旧图逐像素测绘配准；构图锚点不增加历史定位可靠性。",
                       "同一H作用于全部R11几何；局部详图只作等比显示放大，不把寺院单独放大后塞回全城。",
                       "所有线均为地面投影，不能当屋顶、完整房基或可直接量测的历史建筑立面。",
                       "永宁寺南门源图长宽与塔座的关系通过共同投影表达，不能拿最终透视像素宽深比直接核45.7/19。",
                       "旧全景寺院相对较宽、宫城纵深安排与本投影不一致；新图允许改变这些艺术占地。",
                       "宫城2013层、外郭范围线、旧宫城北界闭合包络以及旧06a寺墙不进入清洁艺术导图。",
                       "原图北门、僧房、回廊与无证院内道路没有补出；木塔地基大框不作塔身或院墙。",
                       "516—528综合研究层；不同来源的线不因此成为同一年实测完整建筑。"],
            "validation": {"source_feature_count": len(projected), "source_geometry_identity_preserved": True,
                           "all_features_use_same_matrix": True, "open_lines_not_closed": True,
                           "yongning_component_count": sum(f["id"].startswith("r11-yongning-") for f in projected),
                           "changhe_component_count": sum(f["id"].startswith("r11-changhe-") for f in projected),
                           "palace2013_drawn_as_contemporary_buildings": False,
                           "maximum_display_anchor_residual_px": max(a["display_anchor_residual_px"] for a in anchors)}}
    (output / "projection.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    clean = svg_start(*CANVAS, "R12共同平面透视底稿；仅地面轮廓，无建筑高度")
    draw_features(clean, projected)
    write_svg(output, "projection-clean", clean, render)

    annotated = svg_start(*CANVAS, "R12共同坐标至全景：同方向虚拟视点底稿")
    draw_features(annotated, projected)
    east_mark = features["r11-yongning-YN11-GATE-E-MARK"]["ground_centre_px"]
    for delta in (-1, 1):
        line(annotated, [[east_mark[0]-2, east_mark[1]-2*delta], [east_mark[0]+2, east_mark[1]+2*delta]], COLORS["gate"], 1.2)
    text(annotated, 50, 45, "R12.1 / 全城共同平面 → 全景地面布局", 28, weight=600)
    text(annotated, 50, 74, "所有地物共用一个透视变换；地上高度、屋顶和未证院界未生成。", 17, "#6d7971")
    callout(annotated, [515, 430], [70, 370], "永宁寺：23个同源构件", COLORS["wall"], "门、塔座、佛殿和寺墙作为整体投影")
    callout(annotated, [650, 315], [880, 315], "阊阖门：10项局部构件", COLORS["palace"], "两阙可见边保持开放；地下线不升为楼体")
    callout(annotated, taiji, [880, 215], "太极：报告尺度片", COLORS["palace"], "新落位由统一变换产生；未以旧像素强拟合")
    text(annotated, 70, 724, "地面表达", 21, weight=600)
    for y, color, label in [(762, COLORS["wall"], "寺墙刊图线段"), (799, COLORS["tower"], "木塔基座与突出部分"), (836, COLORS["gate"], "南门／西门刊图轮廓")]:
        line(annotated, [[70, y - 6], [110, y - 6]], color, 4)
        text(annotated, 127, y, label, 19, color)
    text(annotated, 610, 750, "灰色为来源骨架；虚线和缺口保留原角色。", 18, "#68746d")
    text(annotated, 610, 784, "不绘外郭范围墙，不补宫城北界，不把调查点或夯土块立成建筑。", 18, "#68746d")
    text(annotated, 610, 818, "局部图接入全城仍为候选；已核实地共同控制点 = 0。", 18, "#68746d")
    text(annotated, 70, 902, "本底稿只约束平面关系；构图参考点与最终全景像素均不是古代坐标。", 18, "#68746d")
    write_svg(output, "projection-overview", annotated, render)

    local_clean = svg_start(1600, 900, "永宁寺局部：同一透视矩阵的等比放大；仅地面轮廓")
    draw_features(local_clean, projected, detail, True)
    write_svg(output, "projection-yongning-clean", local_clean, render)

    local = svg_start(1600, 900, "永宁寺刊图构件：共享透视与占地关系")
    draw_features(local, projected, detail, True)
    text(local, 55, 52, "永宁寺 / 同一透视的局部放大", 32, weight=600)
    text(local, 55, 91, "23构件同源、同尺；南门、西门、佛殿与塔座不再单独排列。", 20, "#68746d")
    def dp(ident):
        return project(detail, features[ident]["ground_centre_px"])
    east_detail = project(detail, east_mark)
    for delta in (-1, 1):
        line(local, [[east_detail[0]-5, east_detail[1]-5*delta], [east_detail[0]+5, east_detail[1]+5*delta]], COLORS["gate"], 2)
    callout(local, dp("r11-yongning-YN11-BUDDHA-HALL"), [1120, 260], "佛殿基址图示框", COLORS["hall"], "框线不是本轮确认的完整殿身")
    callout(local, dp("r11-yongning-YN11-TOWER-PLINTH"), [1120, 410], "塔座主体约39米见方", COLORS["tower"], "四侧突出部分分别保留")
    callout(local, east_detail, [1120, 495], "东门仅为图示标位", COLORS["gate"], "点号不扩成门基或建筑")
    callout(local, dp("r11-yongning-YN11-GATE-S"), [1120, 580], "南门长边近东西", COLORS["gate"], "图读约45.7×19.0米；不推定门孔或立面")
    callout(local, dp("r11-yongning-YN11-GATE-W"), [70, 465], "西门基址", COLORS["gate"], "保留不规则边与门缺口")
    foundation_corner = features["r11-yongning-YN11-TOWER-FOUNDATION"]["projected_geometry"]["coordinates"][0][0]
    callout(local, project(detail, foundation_corner), [70, 620], "木塔地基大框", "#7e8484", "灰虚线，不是塔身、塔院或围墙")
    callout(local, dp("r11-yongning-YN11-WALL-N"), [520, 205], "寺墙按刊图线段保留", COLORS["wall"], "北门、僧房、回廊未补画")
    text(local, 55, 758, "南门占地长边略大于塔座主体；两者都经过同一个地面透视。", 23, weight=600)
    text(local, 55, 799, "不能用透视图上的像素宽深比直接核对45.7÷19，也不能把地基大框当作九层塔的塔身足迹。", 19, "#68746d")
    text(local, 55, 840, "此页只是上一页的等比局部放大（5.2倍），没有单独挪位、拉伸或改变寺院方向。", 19, "#68746d")
    write_svg(output, "projection-yongning", local, render)
    if any(sha(root / p) != h for p, h in hashes.items()):
        raise ValueError("A source input changed during projection")
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-render", action="store_true")
    args = parser.parse_args()
    result = build(args.root, args.output or args.root / "research/panorama-r12", not args.no_render)
    print(json.dumps({"features": len(result["features"]), "field_registration_verified": False,
                      "key_ground_bounds": result["key_ground_bounds"]}, ensure_ascii=False))
