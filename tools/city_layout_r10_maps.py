"""R10 vector atlas: unchanged source geometry and independent relationship plates.

The layout coordinates below are publication coordinates only.  No output of
the graph layout is written into an archaeological or geographic geometry.
"""
from collections import defaultdict
import json
import math
import re
import unicodedata
from xml.etree import ElementTree as ET

from city_atlas_r4_maps import geometry as source_geometry


NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
PAGE = "luoyang-city-layout.html"
LIVE = "https://mechgouki.github.io/luoyang-city/" + PAGE
W, H = 1680, 1188
INK, GREEN, GOLD, BLUE, GRAY = "#203a34", "#245f4c", "#966b39", "#4a6f91", "#687571"
PALE, WHITE, BORDER = "#f3f5ef", "#fffefa", "#ccd7cd"
COLORS = {"source": GREEN, "relation": GOLD, "interpretation": BLUE, "unknown": GRAY}
KIND_LABELS = {"spatial": "方位关系", "sequence": "叙述次序", "comparison": "解释对照", "membership": "无序归属"}
RELATION_LABELS = {
    "north_of": "在北", "south_of": "在南", "east_of": "在东", "west_of": "在西",
    "within": "范围内", "adjacent": "相邻", "sequence": "先后次序",
    "identity_candidate": "同一性待考", "unknown_connection": "接续未明",
    "membership": "属于", "same_source": "同一来源关联",
}
DIRECTIONS = {"north_of", "south_of", "east_of", "west_of"}
BOUNDARIES = [
    ("宣阳门与内城南墙", "缺同期门墙联测，现有残段不补成闭合南界。"),
    ("宫城北缘与完整金墉", "候选填色不作北墙，丙城局部不代替三城范围。"),
    ("连续道路与桥头接口", "末测点、门端、跨水处及各期路缘仍需逐段核对。"),
    ("洛水古岸与渠池岸线", "现代河线和研究图河段不能替代目标期实测古岸。"),
    ("六世纪古地面", "现代高程与遗存残高不当作北魏地面或建筑原高。"),
    ("跨图共同定位", "来源框独立；共同测点、基准转换与误差尚待核验。"),
]


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def el(parent, tag, **attrs):
    return ET.SubElement(parent, "{" + NS + "}" + tag,
                         {key.replace("_", "-"): str(value) for key, value in attrs.items() if value is not None})


def text(parent, x, y, value, size=20, **attrs):
    defaults = {"fill": INK}
    defaults.update(attrs)
    node = el(parent, "text", x=round(x, 3), y=round(y, 3), font_size=size, **defaults)
    node.text = str(value)
    return node


def rect(parent, x, y, width, height, **attrs):
    defaults = {"fill": WHITE, "stroke": BORDER, "stroke_width": 1.2, "rx": 10}
    defaults.update(attrs)
    return el(parent, "rect", x=x, y=y, width=width, height=height, **defaults)


def path(parent, points, **attrs):
    d = " ".join(("M" if i == 0 else "L") + f"{round(x, 3)} {round(y, 3)}" for i, (x, y) in enumerate(points))
    defaults = {"fill": "none", "stroke": GOLD, "stroke_width": 2.4}
    defaults.update(attrs)
    return el(parent, "path", d=d, **defaults)


def _units(value):
    return sum(1 if unicodedata.east_asian_width(c) in "WF" else .57 for c in str(value))


def wrap(value, max_units):
    """Wrap CJK and Latin without dropping content or adding a false ellipsis."""
    output = []
    for para in str(value).split("\n"):
        line = ""
        for char in para:
            if line and _units(line + char) > max_units and char not in "，。、；：！？）》」』】〕〉":
                output.append(line)
                line = char
            else:
                line += char
        output.append(line)
    return output


def paragraph(parent, x, y, value, width, size=20, leading=None, **attrs):
    leading = leading or size * 1.4
    rows = wrap(value, width / size)
    for i, row in enumerate(rows):
        text(parent, x, y + i * leading, row, size, **attrs)
    return len(rows) * leading


def _title(parent, value):
    el(parent, "title").text = value


def _anchor(parent, decision=None, label=None, bounds=None, target=None):
    href = target or (LIVE + "#decision-" + decision if decision else LIVE)
    attrs = dict(href=href, tabindex="0", aria_label=label or decision or "查阅依据")
    if decision:
        attrs["data_decision"] = decision
    if bounds:
        attrs["data_link_box"] = _json([round(v, 3) for v in bounds])
    a = el(parent, "a", **attrs)
    _title(a, label or decision or "查阅依据")
    return a


def _sheet(identifier, title, description, region=None, height=H):
    attrs = {
        "id": identifier, "viewBox": f"0 0 {W} {height}", "width": str(W), "height": str(height),
        "role": "img", "lang": "zh-CN", "font-family": "Noto Sans CJK SC, sans-serif",
        "aria-labelledby": identifier + "-title " + identifier + "-description",
        "data-original-viewbox": f"0 0 {W} {height}", "data-pdf-pages": str(height // H), "data-source-frames-registered-together": "false",
        "data-new-geographic-coordinates": "0", "data-new-shoreline-geometries": "0",
        "data-coordinate-space": "unscaled-relationship" if region else "independent-source-and-reading-frames",
    }
    if region:
        attrs["data-region"] = region
    root = ET.Element("{" + NS + "}svg", attrs)
    el(root, "title", id=identifier + "-title").text = title
    el(root, "desc", id=identifier + "-description").text = description
    rect(root, 0, 0, W, height, fill=PALE, stroke="none", rx=0)
    text(root, 40, 43, "盛时洛阳  /  R10 城市布局图集", 19, fill=GREEN, font_weight="600")
    text(root, 40, 91, title, 37, font_weight="700")
    paragraph(root, 40, 127, description, 1595, 20, leading=27, fill=GRAY)
    text(root, 40, height - 23, "516 至 528 年综合研究窗口  ·  来源位置、相对关系与艺术复原分别阅读", 16, fill=GRAY)
    text(root, W - 40, height - 23, region or "全城总览", 16, fill=GREEN, text_anchor="end")
    return root


def _source_key(source_inputs):
    return {(row.get("path"), row.get("pointer")) for row in source_inputs}


def _decision_for(region, item):
    """Select a real related decision; never invent a new source association."""
    requested = item.get("decision_id")
    valid = {row["id"] for row in region["decisions"]}
    if requested:
        if requested not in valid:
            raise ValueError("Unknown decision " + requested)
        return requested
    sources = _source_key(item.get("source_inputs", []))
    entities = set(item.get("entity_ids", []))
    scored = [(len(sources & _source_key(row.get("source_inputs", []))) * 10
               + len(entities & set(row.get("entity_ids", []))), row["id"])
              for row in region["decisions"]]
    score, identifier = max(scored, key=lambda value: (value[0], -int(value[1].rsplit("-", 1)[-1])))
    if not score:
        return None
    return identifier


def _arrow(parent, start, end, color, width=2.3):
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    wings = [(end[0] - 10 * math.cos(angle + a), end[1] - 10 * math.sin(angle + a)) for a in (-.45, .45)]
    path(parent, [wings[0], end, wings[1]], stroke=color, stroke_width=width)


def _relation_group(parent, relation):
    g = el(parent, "g", data_relation=relation["id"], data_from=relation["from"], data_to=relation["to"],
           data_relation_type=relation["type"], data_source_inputs=_json(relation.get("source_inputs", [])),
           data_label=relation["label"], data_uncertainty=relation.get("uncertainty", ""),
           data_coordinate_space="unscaled-relationship")
    _title(g, relation["label"] + "。" + relation.get("uncertainty", ""))
    return g


def _node_group(parent, region, node, x, y, width, height):
    g = el(parent, "g", data_node=node["id"], data_node_x=round(x, 3), data_node_y=round(y, 3),
           data_entity_ids=_json(node.get("entity_ids", [])), data_basis=node["basis"], data_kind=node["kind"],
           data_source_inputs=_json(node.get("source_inputs", [])), data_label=node["label"],
           data_coordinate_space="display-only-not-ancient-coordinates")
    _title(g, node["label"] + "。" + node.get("note", ""))
    return _anchor(g, _decision_for(region, node), node["label"] + "：查看判断与来源",
                   (x - width / 2, y - height / 2, width, height))


def _draw_node(parent, region, node, x, y, width=190, size=21, container=False):
    color = COLORS[node["basis"]]
    rows = wrap(node["label"], (width - 22) / size)
    height = max(32 if size <= 18 else 44, len(rows) * (size + 4) + 8)
    a = _node_group(parent, region, node, x, y, width, height)
    kind = node["kind"]
    if kind in {"road", "water", "river", "canal", "channel"} and not container:
        vertical = node.get("_display_road_axis") != "horizontal"
        span = height + 12
        if vertical:
            points = [(x, y - span / 2), (x, y + span / 2)]
        else:
            points = [(x - width / 2 + 6, y), (x + width / 2 - 6, y)]
        path(a, points, stroke=color, stroke_width=7,
             stroke_dasharray="8 5" if kind in {"water", "river", "canal", "channel"} else None)
        for px, py in points:
            el(a, "circle", cx=px, cy=py, r=4.5, fill=WHITE, stroke=color, stroke_width=1.8,
               data_endpoint="display-sample-not-historical-end")
        rect(a, x - width / 2, y - height / 2, width, height, fill=WHITE, stroke="none", rx=4)
    else:
        rect(a, x - width / 2, y - height / 2, width, height, fill="#fbfbf5", stroke=color,
             stroke_width=2, stroke_dasharray="6 4" if node["basis"] in {"interpretation", "unknown"} else None,
             rx=6 if kind not in {"gate", "wall"} else 0)
        if kind == "gate":
            for dx in (-width / 2 + 6, width / 2 - 6):
                path(a, [(x + dx, y - height / 2 + 6), (x + dx, y + height / 2 - 6)], stroke=color, stroke_width=3)
        elif kind in {"ward", "garden", "palace", "courtyard", "region", "market"}:
            path(a, [(x - width / 2 + 8, y - height / 2 - 5), (x + width / 2 - 8, y - height / 2 - 5)],
                 stroke=color, stroke_width=1.5, stroke_dasharray="3 4")
    start = y - (len(rows) - 1) * (size + 4) / 2 + size * .35
    for i, row in enumerate(rows):
        text(a, x, start + i * (size + 4), row, size, fill=color, text_anchor="middle", font_weight="600")
    return (x - width / 2, y - height / 2, width, height)


def _weak_components(ids, relations, extra_pairs=()):
    graph = {identifier: set() for identifier in ids}
    for a, b in [(r["from"], r["to"]) for r in relations] + list(extra_pairs):
        if a in graph and b in graph:
            graph[a].add(b)
            graph[b].add(a)
    result, seen = [], set()
    for identifier in ids:
        if identifier in seen:
            continue
        component, pending = [], [identifier]
        while pending:
            current = pending.pop(0)
            if current in seen:
                continue
            seen.add(current)
            component.append(current)
            pending.extend(sorted(graph[current] - seen))
        result.append(component)
    return result


def _ranks(ids, pairs):
    graph, indegree = {n: [] for n in ids}, {n: 0 for n in ids}
    involved = set()
    for a, b in sorted(set(pairs)):
        graph[a].append(b)
        indegree[b] += 1
        involved.update((a, b))
    rank = {n: 0. for n in involved}
    pending = [n for n in ids if indegree[n] == 0]
    count = 0
    while pending:
        a = pending.pop(0)
        count += 1
        for b in graph[a]:
            rank[b] = max(rank.get(b, 0), rank.get(a, 0) + 1)
            indegree[b] -= 1
            if indegree[b] == 0:
                pending.append(b)
    if count != len(ids):
        raise ValueError("Directional cycle cannot be laid out as a spatial relation")
    return {n: rank.get(n) for n in ids}


def _positions(ids, relations, bounds, kind="spatial"):
    x, y, width, height = bounds
    # A documented four-direction group is read around its common reference.
    # This is an unscaled compass arrangement; same-side members remain unordered.
    if len(ids) == 9 and len(relations) == 8 and all(r["type"] in DIRECTIONS for r in relations):
        references = {r["to"] for r in relations}
        groups = {typ: [r["from"] for r in relations if r["type"] == typ] for typ in DIRECTIONS}
        if len(references) == 1 and all(len(group) == 2 for group in groups.values()):
            center = next(iter(references))
            slots = {"north_of": ((.37, .16), (.63, .16)), "south_of": ((.37, .84), (.63, .84)),
                     "west_of": ((.13, .32), (.13, .68)), "east_of": ((.87, .32), (.87, .68))}
            points = {center: (x + width * .5, y + height * .5)}
            for typ, members in groups.items():
                for identifier, (fx, fy) in zip(members, slots[typ]):
                    points[identifier] = (x + width * fx, y + height * fy)
            return points, min(174, width * .225), 16
    xp, yp = [], []
    for r in relations:
        a, b, typ = r["from"], r["to"], r["type"]
        if a not in ids or b not in ids:
            continue
        if typ == "west_of": xp.append((a, b))
        elif typ == "east_of": xp.append((b, a))
        elif typ == "north_of": yp.append((a, b))
        elif typ == "south_of": yp.append((b, a))
        elif typ == "sequence" and kind == "sequence": xp.append((a, b))
    if not xp and not yp:
        cols = min(3, len(ids)) if len(ids) > 3 else len(ids)
        coords = {n: (i % cols, i // cols) for i, n in enumerate(ids)}
    else:
        xr, yr = _ranks(ids, xp), _ranks(ids, yp)
        neighbours = defaultdict(set)
        for r in relations:
            if r["from"] in ids and r["to"] in ids:
                neighbours[r["from"]].add(r["to"])
                neighbours[r["to"]].add(r["from"])
        for rank in (xr, yr):
            for _ in range(len(ids)):
                changes = {}
                for n in ids:
                    values = [rank[o] for o in neighbours[n] if rank[o] is not None]
                    if rank[n] is None and values:
                        changes[n] = sum(values) / len(values)
                if not changes:
                    break
                rank.update(changes)
        coords = {n: (xr[n] or 0., yr[n] or 0.) for n in ids}
        occupied = defaultdict(list)
        for n, pair in coords.items(): occupied[pair].append(n)
        for (xx, yy), group in occupied.items():
            if len(group) > 1:
                for i, n in enumerate(group):
                    offset = (i - (len(group) - 1) / 2) * .22
                    coords[n] = (xx, yy + offset) if xp and not yp else (xx + offset, yy)
    # Rank values express order only. Equal ordinal spacing removes accidental
    # near-collisions without suggesting measured historical distances.
    xu = sorted({point[0] for point in coords.values()})
    yu = sorted({point[1] for point in coords.values()})
    coords = {n: (xu.index(xx), yu.index(yy)) for n, (xx, yy) in coords.items()}
    # Find distinct publication cells satisfying every stated direction.  This
    # avoids linearly stacking all members of a garden into a false street.
    min_cols = max([1] + [int(v) + 1 for v in _ranks(ids, xp).values() if v is not None])
    min_rows = max([1] + [int(v) + 1 for v in _ranks(ids, yp).values() if v is not None])
    ideal = max(min_cols, min(len(ids), round(math.sqrt(len(ids) * width / max(height, 30) * .32))))
    degree = {n: sum(n in (r["from"], r["to"]) for r in relations) for n in ids}
    order = sorted(ids, key=lambda n: (-degree[n], ids.index(n)))
    xvalues, yvalues = [p[0] for p in coords.values()], [p[1] for p in coords.values()]
    answer = None
    for cols in sorted(range(min_cols, max(min_cols, min(len(ids), ideal + 2)) + 1), key=lambda c: abs(c - ideal)):
        rows = max(min_rows, math.ceil(len(ids) / cols))
        cells = [(xx, yy) for yy in range(rows) for xx in range(cols)]
        assigned, used = {}, set()
        attempts = [0]
        def valid(n, cell):
            for r in relations:
                if (r["type"] not in DIRECTIONS and not (r["type"] == "sequence" and kind == "sequence")) or n not in (r["from"], r["to"]):
                    continue
                other = r["to"] if n == r["from"] else r["from"]
                if other not in assigned:
                    continue
                a = cell if n == r["from"] else assigned[other]
                b = assigned[other] if n == r["from"] else cell
                checks = {"north_of": a[1] < b[1], "south_of": a[1] > b[1], "east_of": a[0] > b[0], "west_of": a[0] < b[0]}
                if r["type"] == "sequence":
                    checks["sequence"] = a[0] < b[0]
                if not checks[r["type"]]:
                    return False
            return True
        def search(index):
            attempts[0] += 1
            if attempts[0] > 150000:
                return False
            if index == len(order):
                return True
            n = order[index]
            xx, yy = coords[n]
            preferred = ((xx / max(1, max(xvalues))) * (cols - 1), (yy / max(1, max(yvalues))) * (rows - 1))
            for cell in sorted(cells, key=lambda p: (p[0] - preferred[0]) ** 2 + (p[1] - preferred[1]) ** 2):
                if cell in used or not valid(n, cell):
                    continue
                assigned[n] = cell
                used.add(cell)
                if search(index + 1):
                    return True
                used.remove(cell)
                del assigned[n]
            return False
        if search(0):
            answer = dict(assigned)
            break
    if answer is None:
        raise ValueError("No collision-free display ordering for " + ", ".join(ids))
    cell_width, cell_height = width / cols, height / rows
    size = 21 if cell_width >= 200 and cell_height >= 85 else 18 if cell_width >= 145 and cell_height >= 58 else 16
    node_width = min(218, cell_width * .86)
    points = {n: (x + (xx + .5) * cell_width, y + (yy + .5) * cell_height) for n, (xx, yy) in answer.items()}
    for r in relations:
        if r["from"] not in points or r["to"] not in points:
            continue
        a, b = points[r["from"]], points[r["to"]]
        checks = {"north_of": a[1] < b[1], "south_of": a[1] > b[1], "east_of": a[0] > b[0], "west_of": a[0] < b[0]}
        if r["type"] in checks and not checks[r["type"]]:
            raise ValueError("Cannot preserve direction for " + r["id"])
    return points, node_width, size


def _edge(parent, region, relation, points, widths, duplicate=0, bounds=None):
    if relation["from"] not in points or relation["to"] not in points:
        return
    g = _relation_group(parent, relation)
    typ = relation["type"]
    color = GRAY if typ == "unknown_connection" else BLUE if typ == "identity_candidate" else GOLD
    # Direction arrows start at the reference and point to the located object.
    start_id, end_id = ((relation["to"], relation["from"]) if typ in DIRECTIONS else (relation["from"], relation["to"]))
    sx, sy = points[start_id]
    ex, ey = points[end_id]
    dx, dy = ex - sx, ey - sy
    length = math.hypot(dx, dy) or 1
    ux, uy = dx / length, dy / length
    offset_start = min(widths[start_id] / 2 / max(abs(ux), .01), 29 / max(abs(uy), .01)) + 4
    offset_end = min(widths[end_id] / 2 / max(abs(ux), .01), 29 / max(abs(uy), .01)) + 6
    if offset_start + offset_end > length * .78:
        shrink = length * .78 / (offset_start + offset_end)
        offset_start *= shrink
        offset_end *= shrink
    a, b = (sx + ux * offset_start, sy + uy * offset_start), (ex - ux * offset_end, ey - uy * offset_end)
    bend = duplicate * 24
    if abs(dy) < 1 and typ in {"within", "membership", "same_source", "identity_candidate"}:
        between = [p for identifier, p in points.items() if identifier not in (start_id, end_id)
                   and min(sx, ex) < p[0] < max(sx, ex) and abs(p[1] - sy) < 25]
        if between:
            # Bypass intermediate members. A continuous line through another
            # member would imply a chain which the documentary source does not give.
            room = max(24, sy - bounds[1] - 4) if bounds else 36
            bend = -2 * min(58, room) * (1 if dx >= 0 else -1)
    cx, cy = (a[0] + b[0]) / 2 - uy * bend, (a[1] + b[1]) / 2 + ux * bend
    dashed = typ in {"unknown_connection", "identity_candidate", "same_source", "within", "membership"}
    el(g, "path", d=f"M{a[0]:.3f} {a[1]:.3f} Q{cx:.3f} {cy:.3f} {b[0]:.3f} {b[1]:.3f}",
       fill="none", stroke=color, stroke_width=2.3, stroke_dasharray="7 5" if dashed else None)
    if typ not in {"unknown_connection", "identity_candidate", "adjacent", "same_source"}:
        _arrow(g, (cx, cy), b, color)
    elif typ == "unknown_connection":
        for px, py in (a, b): el(g, "circle", cx=px, cy=py, r=4.8, fill=WHITE, stroke=color, stroke_width=2)
    return {"group": g, "relation": relation, "center": ((a[0] + 2 * cx + b[0]) / 4, (a[1] + 2 * cy + b[1]) / 4), "color": color,
            "horizontal": abs(dx) >= abs(dy), "sign": 1 if duplicate >= 0 else -1}


def _intersects(a, b, padding=3):
    return not (a[0] + a[2] + padding <= b[0] or b[0] + b[2] + padding <= a[0]
                or a[1] + a[3] + padding <= b[1] or b[1] + b[3] + padding <= a[1])


def _relation_key_layout(relations, bounds):
    """Reserve a visible printed key; its positions are publication coordinates."""
    x, y, width, height = bounds
    if not relations:
        return bounds, []
    size, leading = 16, 21
    alternatives = []
    maximum = 3 if width >= 650 else 2 if width >= 470 else 1
    for columns in range(1, maximum + 1):
        cw = (width - 14 * (columns - 1)) / columns
        rows = [wrap(r["label"], (cw - 35) / size) for r in relations]
        row_heights = [max(len(a) for a in rows[i:i + columns]) * leading + 4
                       for i in range(0, len(rows), columns)]
        total = 13 + sum(row_heights)
        alternatives.append((total, columns, cw, rows, row_heights))
    total, columns, cw, rows, row_heights = min(alternatives, key=lambda a: (a[0], -a[1]))
    key_y = y + height - total
    entries, yy = [], key_y + 13
    for i, relation in enumerate(relations):
        col = i % columns
        if i and col == 0:
            yy += row_heights[i // columns - 1]
        entries.append({"relation": relation, "number": i + 1, "rows": rows[i],
                        "box": (x + col * (cw + 14), yy, cw, len(rows[i]) * leading + 4),
                        "size": size, "leading": leading})
    return (x, y, width, max(36, key_y - y - 8)), entries


def _place_edge_markers(specs, bounds, occupied):
    """Use compact numbered markers on edges; full captions are in the key."""
    x, y, width, height = bounds
    for spec in specs:
        cx, cy = spec["center"]
        marker = 22
        candidates = [(cx, cy)]
        for distance in (17, 29, 42, 58, 76, 96, 124):
            for angle in range(0, 360, 30):
                rad = math.radians(angle)
                candidates.append((cx + distance * math.cos(rad), cy + distance * math.sin(rad)))
        candidates.sort(key=lambda a: (a[0] - cx) ** 2 + (a[1] - cy) ** 2)
        chosen = None
        for px, py in candidates:
            box = (px - marker / 2, py - marker / 2, marker, marker)
            if box[0] < x or box[1] < y or box[0] + marker > x + width or box[1] + marker > y + height:
                continue
            if any(_intersects(box, other, 1) for other in occupied):
                continue
            chosen = (px, py, box)
            break
        if chosen is None:
            # An exceptionally short edge may have no free position between
            # node labels. The marker uses the nearest page margin with an
            # explicit dotted annotation leader, never a new relation.
            px = min(x + width - 12, max(x + 12, cx))
            py = min(y + height - 12, max(y + 12, cy))
            chosen = (px, py, (px - 11, py - 11, 22, 22))
        px, py, box = chosen
        g = spec["group"]
        if math.hypot(px - cx, py - cy) > 18:
            path(g, [(cx, cy), (px, py)], stroke="#a1aba3", stroke_width=1, stroke_dasharray="2 3",
                 data_role="annotation-leader-not-spatial-connection")
        el(g, "circle", cx=px, cy=py, r=10.5, fill=WHITE, stroke=spec["color"], stroke_width=1.3,
           data_role="relation-number")
        text(g, px, py + 4, str(spec["number"]), 12, fill=spec["color"], text_anchor="middle", font_weight="700")
        occupied.append(box)


def _draw_relation_keys(parent, region, specs, entries, graph_bounds):
    if not entries:
        return
    x, y, width, height = graph_bounds
    line_y = min(e["box"][1] for e in entries) - 13
    path(parent, [(x, line_y), (x + width, line_y)], stroke="#dbe1d7", stroke_width=1)
    by_id = {s["relation"]["id"]: s for s in specs}
    for entry in entries:
        relation = entry["relation"]
        spec = by_id[relation["id"]]
        g = spec["group"]
        box = entry["box"]
        g.set("data-visible-label-box", _json(box))
        label = _anchor(g, _decision_for(region, relation), relation["label"] + "：查看依据", box)
        xx, yy, _, _ = box
        el(label, "circle", cx=xx + 11, cy=yy + 10, r=10.5, fill=WHITE, stroke=spec["color"], stroke_width=1.3)
        text(label, xx + 11, yy + 14, str(entry["number"]), 12, fill=spec["color"], text_anchor="middle", font_weight="700")
        for i, row in enumerate(entry["rows"]):
            text(label, xx + 29, yy + 16 + i * entry["leading"], row, entry["size"], fill=spec["color"])


def _draw_graph(parent, region, panel, bounds):
    nodes = {n["id"]: dict(n) for n in panel["nodes"]}
    relations = panel["relations"]
    graph_bounds, entries = _relation_key_layout(relations, bounds)
    x, y, width, height = graph_bounds
    parent.set("data-plot-bounds", _json(graph_bounds))
    # Each disconnected group receives a reading frame. These frames are not
    # city blocks, courtyard walls, or jointly controlled archaeological maps.
    ids = list(nodes)
    components = _weak_components(ids, relations)
    if len(components) == 1:
        cells = [graph_bounds]
    elif len(components) == 3 and width >= 650 and max(map(len, components)) >= 4:
        largest = max(range(3), key=lambda i: len(components[i]))
        small_height = min(150, max(100, height * .25)) if height >= 350 else min(74, max(58, height * .32))
        half = (width - 15) / 2
        small_cells = [(x, y, half, small_height), (x + half + 15, y, half, small_height)]
        cells = []
        for i in range(3):
            cells.append((x, y + small_height + 9, width, height - small_height - 9)
                         if i == largest else small_cells.pop(0))
    else:
        horizontal_depth = 1
        for group in components:
            pairs = []
            for r in relations:
                if r["from"] not in group or r["to"] not in group:
                    continue
                if r["type"] == "west_of": pairs.append((r["from"], r["to"]))
                elif r["type"] == "east_of": pairs.append((r["to"], r["from"]))
                elif r["type"] == "sequence" and panel["kind"] == "sequence": pairs.append((r["from"], r["to"]))
            horizontal_depth = max(horizontal_depth, max([0] + [v for v in _ranks(group, pairs).values() if v is not None]) + 1)
        columns = 2 if len(components) in {2, 4} and width >= 650 and horizontal_depth <= 2 else 1
        rows = math.ceil(len(components) / columns)
        gap = 12
        cw, ch = (width - gap * (columns - 1)) / columns, (height - gap * (rows - 1)) / rows
        cells = [(x + (i % columns) * (cw + gap), y + (i // columns) * (ch + gap), cw, ch) for i in range(len(components))]
    label_specs, occupied = [], []
    index = {r["id"]: i + 1 for i, r in enumerate(relations)}
    # Frames are all drawn first, so a subsequent group cannot cover an
    # earlier group's caption or edge marker.
    for i, cell in enumerate(cells):
        if len(components) > 1:
            cx, cy, cw, ch = cell
            rect(parent, cx, cy, cw, ch, fill="#fafbf6", stroke="#dbe1d7", rx=6,
                 data_independent_group=i + 1)
            text(parent, cx + 7, cy + 16, f"独立组 {i + 1}", 13, fill=GRAY)
            occupied.append((cx + 4, cy + 2, 75, 17))
    for i, (ids, cell) in enumerate(zip(components, cells)):
        cx, cy, cw, ch = cell
        if len(components) > 1:
            cell = (cx + 5, cy + 17, cw - 10, ch - 21)
        subrelations = [r for r in relations if r["from"] in ids and r["to"] in ids]
        points, node_width, size = _positions(ids, subrelations, cell, panel["kind"])
        max_width = min(218, node_width / .86 - 7)
        widths = {n: min(max_width, max(node_width, max(_units(line) for line in nodes[n]["label"].split("\n")) * size + 22))
                  for n in ids}
        duplicates = defaultdict(list)
        for r in subrelations:
            duplicates[tuple(sorted((r["from"], r["to"])))].append(r)
        group_specs = []
        for rels in duplicates.values():
            for j, r in enumerate(rels):
                spec = _edge(parent, region, r, points, widths, j - (len(rels) - 1) / 2, cell)
                spec["number"] = index[r["id"]]
                group_specs.append(spec)
                label_specs.append(spec)
        group_boxes = []
        for identifier, (px, py) in points.items():
            node = nodes[identifier]
            if node["kind"] == "road":
                sides = [r["type"] for r in subrelations if identifier in (r["from"], r["to"])]
                node["_display_road_axis"] = "vertical" if any(t in {"east_of", "west_of"} for t in sides) else "horizontal"
            box = _draw_node(parent, region, node, px, py, widths[identifier], size)
            group_boxes.append(box)
            occupied.append(box)
        _place_edge_markers(group_specs, cell, occupied)
    _draw_relation_keys(parent, region, label_specs, entries, graph_bounds)

def _panel(parent, region, panel, bounds):
    x, y, width, height = bounds
    group = el(parent, "g", data_panel=panel["id"], data_panel_kind=panel["kind"],
               data_coordinate_space="unscaled-relationship", data_panel_bounds=_json(bounds))
    rect(group, x, y, width, height, fill=WHITE, stroke=BORDER, rx=11)
    text(group, x + 21, y + 34, panel["title"], 25, fill=GREEN, font_weight="700")
    text(group, x + width - 20, y + 34, KIND_LABELS[panel["kind"]], 16, fill=GRAY, text_anchor="end")
    caption_height = paragraph(group, x + 21, y + 63, panel["caption"], width - 42, 17, leading=23, fill=GRAY)
    graph_y = y + 69 + caption_height
    if panel["kind"] == "spatial":
        text(group, x + width - 22, y + height - 12, "北在上、东在右；无比例", 15, fill=GRAY, text_anchor="end")
    else:
        text(group, x + width - 22, y + height - 12, "本窗排列不表示地理方向", 15, fill=GRAY, text_anchor="end")
    _draw_graph(group, region, panel, (x + 21, graph_y, width - 42, y + height - 30 - graph_y))


def build_region(region):
    """Return one A3-proportioned, self-contained SVG for a documentary region."""
    rid = region["id"]
    panels = region["panels"]
    if not 1 <= len(panels) <= 4:
        raise ValueError(rid + " needs one to four separately readable panels")
    page_count = 2 if rid in {"R02", "R03", "R10"} else 1
    height = H * page_count
    root = _sheet("region-map-" + rid, rid + "  " + region["title"] + ("〔上〕" if page_count == 2 else ""),
                  region["intro"], rid, height=height)
    el(root, "metadata").text = _json({"region": rid, "display_positions_are_coordinates": False,
        "sequence_and_membership_are_geographic": False,
        "rule": "Only explicitly labelled relationships are assertions; do not infer unstated directions from placement."})
    decisions = region["decisions"]
    columns = 3 if len(decisions) <= 6 else 4 if len(decisions) <= 8 else 5
    decision_rows = math.ceil(len(decisions) / columns)
    footer_height = 91 + decision_rows * 51
    y0, bottom = 158, height - 41 - footer_height
    gap = 22
    half = (W - 80 - gap) / 2
    if len(panels) == 1:
        boxes = [(40, y0, W - 80, bottom - y0)]
    elif len(panels) == 2:
        boxes = [(40 + i * (half + gap), y0, half, bottom - y0) for i in range(2)]
    else:
        ph = (bottom - y0 - gap) / 2
        boxes = [(40, y0, half, ph), (40 + half + gap, y0, half, ph)]
        if len(panels) == 3:
            boxes.append((40, y0 + ph + gap, W - 80, ph))
        else:
            boxes.extend([(40, y0 + ph + gap, half, ph), (40 + half + gap, y0 + ph + gap, half, ph)])
    if page_count == 2:
        first_bottom = H - 104
        first_height = first_bottom - y0
        second_y = H + y0
        boxes = [(40, y0, half, first_height), (40 + half + gap, y0, half, first_height),
                 (40, second_y, half, bottom - second_y),
                 (40 + half + gap, second_y, half, bottom - second_y)]
        text(root, 40, H - 66, "续页继续本区后两窗；本区判断编号与全景约束见下页。", 20, fill=GREEN)
        text(root, 40, H - 23, "516 至 528 年综合研究窗口  ·  同一区上下两页合读，排列不构成共同地理配准", 16, fill=GRAY)
        text(root, W - 40, H - 23, rid + " / 上", 16, fill=GREEN, text_anchor="end")
        path(root, [(0, H), (W, H)], stroke=BORDER, stroke_width=2, data_role="print-page-break")
        text(root, 40, H + 43, "盛时洛阳  /  R10 城市布局图集", 19, fill=GREEN, font_weight="600")
        text(root, 40, H + 91, rid + "  " + region["title"] + "〔下〕", 37, font_weight="700")
        paragraph(root, 40, H + 127, "续读：" + region["summary"], 1595, 20, leading=27, fill=GRAY)
    if rid == "R11":
        upper = (bottom - y0 - gap) / 2 - 24
        lower_y = y0 + upper + gap
        boxes = [(40, y0, half, upper), (40 + half + gap, y0, half, upper),
                 (40, lower_y, half, bottom - lower_y),
                 (40 + half + gap, lower_y, half, bottom - lower_y)]
    if rid == "R07":
        # The two expressly north-to-south office lists need tall independent
        # columns. Their printed sequence must not be folded into a false grid.
        full_height = bottom - y0
        narrow = (half - gap) / 2
        boxes = [(40, y0, half, (full_height - gap) / 2),
                 (40 + half + gap, y0, narrow, full_height),
                 (40 + half + gap + narrow + gap, y0, narrow, full_height),
                 (40, y0 + (full_height + gap) / 2, half, (full_height - gap) / 2)]
    for p, bounds in zip(panels, boxes): _panel(root, region, p, bounds)
    start = bottom + 30
    text(root, 42, start, "本区空间判断", 21, fill=GREEN, font_weight="700")
    text(root, 230, start, "点击编号回查来源与限制", 17, fill=GRAY)
    cw = (W - 80 - 16 * (columns - 1)) / columns
    for i, decision in enumerate(decisions):
        xx, yy = 40 + (i % columns) * (cw + 16), start + 13 + (i // columns) * 51
        a = _anchor(root, decision["id"], decision["title"], (xx, yy, cw, 43))
        rect(a, xx, yy, cw, 43, fill="#eaf0e8", stroke="none", rx=5)
        text(a, xx + 10, yy + 27, decision["id"], 15, fill=GREEN, font_weight="700")
        paragraph(a, xx + 130, yy + 18, decision["title"], cw - 142, 16, leading=18, fill=INK)
    implication_y = start + 29 + decision_rows * 51
    paragraph(root, 42, implication_y, "全景约束：" + region["panorama_implication"], W - 84, 18, leading=24, fill=GRAY)
    return ET.tostring(root, encoding="unicode")


def _source_frame(root, atlas, bounds):
    x, y, width, height = bounds
    rect(root, x, y, width, height, fill=WHITE, stroke=BORDER, rx=11)
    text(root, x + 20, y + 34, "A  来源骨架：图 06a 原始图框", 26, fill=GREEN, font_weight="700")
    text(root, x + 20, y + 65, "保留原段、断笔和概化图符；不是完整同期城市实测平面", 18, fill=GRAY)
    left, top, sw, sh = x + 24, y + 85, width - 48, height - 148
    bx, by, bw, bh = 93, 134, 478, 448
    scale = min(sw / bw, sh / bh)
    dx, dy = left + (sw - bw * scale) / 2 - bx * scale, top + (sh - bh * scale) / 2 - by * scale
    native = el(root, "g", transform=f"translate({dx} {dy}) scale({scale})", data_frame="frame-06a",
                data_coordinate_space="06a-source-pdf-units", data_city_registration="false")
    features = sorted(atlas["features"], key=lambda f: 0 if f["layer"] == "layout_envelope" else 2 if f["source_pdf_geometry"]["type"] == "Point" else 1)
    for feature in features:
        modern = feature["id"].startswith("geo-modern-")
        group = el(native, "a", href="https://mechgouki.github.io/luoyang-city/prosperity-city-atlas.html#feature-" + feature["id"],
                   data_feature=feature["id"], data_source_geometry=_json(feature["source_pdf_geometry"]),
                   data_layer="modern" if modern else "candidate" if feature["layer"] == "layout_envelope" else "source",
                   data_source_path="city-atlas/atlas.json", display="none" if modern else None)
        _title(group, feature["label"] + "；" + feature.get("source_historical_period", "按原图分期"))
        source_geometry(group, feature, scale)
        for primitive in group:
            if primitive.get("data-native-geometry"):
                primitive.set("data-source-geometry", _json(feature["source_pdf_geometry"]))
                if not modern and primitive.get("stroke") not in (None, "none"):
                    primitive.set("stroke", GREEN)
                if feature["layer"] == "layout_envelope":
                    primitive.set("fill", "#dfe9d5")
                    primitive.set("data-role", "candidate-fill-not-evidenced-north-wall")
    # Reading labels are outside the native geometry group and never become
    # archaeological coordinates or substituted source vertices.
    short = {
        "geo-jinyong-bing-reference": "金墉丙城局部", "geo-daxia-gate": "大夏门", "geo-guangmo-gate": "广莫门",
        "geo-taiji-hall-reference": "太极殿参照", "geo-changhe-palace-gate": "宫前阊阖门",
        "geo-yongning-pagoda-reference": "永宁寺塔基", "geo-xiyang-gate": "西阳门",
        "geo-jianchun-gate": "建春门", "geo-dongyang-gate": "东阳门",
        "geo-qingyang-gate": "青阳门", "geo-ximing-gate": "西明门",
    }
    left_ids = {"geo-jinyong-bing-reference", "geo-daxia-gate", "geo-taiji-hall-reference", "geo-changhe-palace-gate", "geo-yongning-pagoda-reference", "geo-xiyang-gate", "geo-ximing-gate"}
    for side in ("left", "right"):
        selected = [f for f in features if f["id"] in short and ((f["id"] in left_ids) == (side == "left"))]
        selected.sort(key=lambda f: f["source_pdf_geometry"]["coordinates"][1])
        for i, feature in enumerate(selected):
            px, py = feature["source_pdf_geometry"]["coordinates"]
            px, py = dx + px * scale, dy + py * scale
            lx = x + 22 if side == "left" else x + width - 22
            ly = y + 128 + i * min(66, (height - 218) / max(1, len(selected) - 1))
            endpoint = lx + 145 if side == "left" else lx - 110
            path(root, [(px, py), (endpoint, ly - 5)], stroke="#9aaba0", stroke_width=1.05, data_role="reading-leader-not-road")
            text(root, lx, ly, short[feature["id"]], 17, fill=GREEN, text_anchor="start" if side == "left" else "end")
    text(root, x + width - 34, y + 32, "北", 17, fill=GREEN, text_anchor="middle")
    path(root, [(x + width - 34, y + 58), (x + width - 34, y + 40)], stroke=GREEN, stroke_width=2)
    _arrow(root, (x + width - 34, y + 58), (x + width - 34, y + 40), GREEN)
    text(root, x + 20, y + height - 39, "宫城候选面北缘只参与填色；外郭是来源图相关遗存范围。", 17, fill=GRAY)
    text(root, x + 20, y + height - 15, "原图坐标：西安 1980。现代洛水与邙山另层默认关闭，不作北魏地面。", 17, fill=GRAY)


def build_overview(atlas, regions):
    """Return the source-native overview and a deliberately separate region index."""
    root = _sheet("city-layout-overview", "全城来源骨架与十一片区阅读总览",
                  "总图提供共同阅读入口；十一片区以明确关系深化布局，独立来源框与关系窗没有共同地理配准。")
    _source_frame(root, atlas, (40, 170, 1022, 748))
    x, y, width, height = 1084, 170, 556, 748
    rect(root, x, y, width, height, fill=WHITE, stroke=BORDER, rx=11)
    text(root, x + 20, y + 34, "B  十一区阅读索引", 26, fill=GREEN, font_weight="700")
    text(root, x + 20, y + 64, "此处是目录，不是十一块地理分区边界", 18, fill=GRAY)
    row_height = min(57, (height - 105) / max(1, len(regions)))
    for i, region in enumerate(regions):
        yy = y + 82 + i * row_height
        a = _anchor(root, label=region["title"] + "：打开片区图与依据", bounds=(x + 16, yy, width - 32, row_height - 6),
                    target=LIVE + "#region-" + region["id"])
        a.set("data-region-link", region["id"])
        rect(a, x + 16, yy, width - 32, row_height - 6, fill="#edf2e9" if i % 2 == 0 else "#f6f8f1", stroke="none", rx=5)
        text(a, x + 29, yy + 31, region["id"], 20, fill=GREEN, font_weight="700")
        text(a, x + 91, yy + 31, region["title"], 22, fill=INK)
        text(a, x + width - 30, yy + 31, str(len(region["panels"])) + " 窗", 16, fill=GRAY, text_anchor="end")
    text(root, 42, 955, "全城仍须保持可见的六类边界", 23, fill=GREEN, font_weight="700")
    for i, (title, note) in enumerate(BOUNDARIES):
        xx, yy = 40 + (i % 3) * 540, 974 + (i // 3) * 78
        rect(root, xx, yy, 520, 69, fill="#e9eee5", stroke="none", rx=6)
        text(root, xx + 12, yy + 25, title, 20, fill=GREEN, font_weight="600")
        paragraph(root, xx + 12, yy + 49, note, 495, 16, leading=19, fill=GRAY)
    el(root, "metadata").text = _json({"source": "city-atlas/atlas.json", "retained_historical_features": 28,
        "modern_reference_default_visible": False, "source_frames_registered_together": False,
        "region_index_is_geographic_partition": False})
    return ET.tostring(root, encoding="unicode")


def build_legend(data):
    """The final PDF plate explains how to read all other plates without a network."""
    root = _sheet("city-layout-legend", "图例、证据与尚未完成的空间",
                  "本图集完成既定材料的分区表达；完整历史复原仍取决于同层测线、共同控制、可靠时相与原图。")
    legends = [
        ("source", "来源图依据", "来源框内保留原段与缺口；关系窗绿色仅指来源身份，位置仍是非比例排版。"),
        ("relation", "文献／报告关系", "棕色方向与归属按明确证据表达。只有标出的关系构成判断，间距没有古代米制意义。"),
        ("interpretation", "条件解释", "蓝色虚线表示需要条件的读法或身份解释。不同方案分别阅读，不拼为同时成立的布局。"),
        ("unknown", "仍待定位", "灰色与空心端点保留接口、端点及位置未知。留白不证明古代不存在，也不由全景补齐。"),
    ]
    for i, (key, title, body) in enumerate(legends):
        xx, yy = 40 + i * 405, 182
        rect(root, xx, yy, 385, 216, fill=WHITE, stroke=BORDER, rx=10)
        path(root, [(xx + 20, yy + 35), (xx + 95, yy + 35)], stroke=COLORS[key], stroke_width=5,
             stroke_dasharray="8 5" if key in {"interpretation", "unknown"} else None)
        if key == "unknown":
            for px in (xx + 20, xx + 95): el(root, "circle", cx=px, cy=yy + 35, r=6, fill=WHITE, stroke=GRAY, stroke_width=2)
        text(root, xx + 20, yy + 78, title, 25, fill=COLORS[key], font_weight="700")
        paragraph(root, xx + 20, yy + 112, body, 345, 20, leading=29, fill=GRAY)
    text(root, 42, 445, "几种图面表达，各自回答不同的问题", 25, fill=GREEN, font_weight="700")
    descriptions = [
        "方位窗：北在上、东在右，但不按比例；不得由未连接的节点或方向传递补出新判断。",
        "归属窗：表示无序成员集合；框线只分阅读组，不是里墙、院墙或市场边界，排列不表示街序。",
        "次序窗与对照窗：解释营建、沿革、仪式或版本关系，不把时间先后画成城市道路。",
    ]
    for i, value in enumerate(descriptions):
        paragraph(root, 60, 484 + i * 40, value, 1560, 21, leading=28, fill=INK)
    text(root, 42, 632, "六类尚缺资料决定完整复原的边界", 25, fill=GREEN, font_weight="700")
    for i, (title, body) in enumerate(BOUNDARIES):
        xx, yy = 40 + (i % 3) * 540, 657 + (i // 3) * 145
        rect(root, xx, yy, 520, 126, fill=WHITE, stroke=BORDER, rx=9)
        text(root, xx + 18, yy + 34, str(i + 1) + "  " + title, 23, fill=GREEN, font_weight="600")
        paragraph(root, xx + 18, yy + 70, body, 484, 20, leading=28, fill=GRAY)
    regions = data.get("regions", [])
    decisions = data.get("decisions", [])
    if not decisions: decisions = [d for r in regions for d in r.get("decisions", [])]
    text(root, 42, 988, f"回查路径：11 区图  /  {len(decisions)} 项判断  /  原文与图页定位  /  完整 JSON、CSV 与离线包", 23, fill=GREEN, font_weight="600")
    paragraph(root, 42, 1025, "每张片区图的判断编号可回到正式网页。图中引用旧实体、道路和水系 ID，不把记录数量等同独立古址或道路数量。", 1580, 20, leading=29, fill=GRAY)
    text(root, 42, 1091, LIVE, 20, fill=GREEN)
    text(root, 42, 1125, "来源提交：" + data.get("source_commit", "由本次构建记录"), 17, fill=GRAY)
    return ET.tostring(root, encoding="unicode")
