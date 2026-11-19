"""Publish the segment-by-segment documentary water maps, without georegistration."""
import html
import json
import math
import re
import shutil
from collections import Counter
from xml.etree import ElementTree as ET

from dual_cartography import dump, load, sha
from north_b4 import render_atlas
from prosperity_anchors_p461 import ROOT, SITE
from prosperity_corridors_p463 import INK, MUTED, WATER, label, line

FOLDER = "water-467"
SOURCE = ROOT / "research/prosperity-v4" / FOLDER
PAGE = "prosperity-water-p467.html"
PREVIOUS = "prosperity-south-p466.html"
ATLAS = f"downloads/{FOLDER}.pdf"
VERSION = "prosperity-water-p467"
ARCHIVED_ATLAS = ROOT / "research/prosperity-v4/archive/water-467.pdf"
ARCHIVED_COMMIT = "e6d0aaec76b5d25ed347f377ce19d7361b47f9a2"
ARCHIVED_ATLAS_SHA = "68c994d5a558ee222134afd98cf15e095b6b4dce4c75d999e68c9789d4d0d404"
ENTRY = f'<p id="p467-entry"><a href="./{PAGE}">续读 · 河流与水道：城内外的连接与分期</a></p>\n'
CORRECTION = ('<aside id="p467-water-correction" style="border-left:4px solid #956b46;padding:.7rem 1rem;background:#f1ebde">'
              '<strong>2026-11-19校读补充：</strong>下图及下文沿传本文序说明鸿池后接七里涧。'
              '熊会贞与黄学超对七里涧的身份、接入水支有不同解释，现已在'
              f'<a href="./{PAGE}#map=east-readings&amp;layer=all">P4.6.7第3图</a>并列。'
              '这里的传本文序不能单独证明鸿池东出口的实际位置或516—528年连续通航。'
              '本册旧PDF与读数保留原样，请连同新校读阅读。</aside>\n')
PAPER, RULE, OLD, PROPOSED = "#faf8f0", "#c6cec3", "#836446", "#9b694e"
RELATION_LABELS = {"flow": "明确流向", "connection": "相连，方向未定", "adjacency": "仅相邻", "containment": "位于其内", "stratigraphy": "层位先后", "proposal": "开渠提议", "hypothesis": "复原解释"}
PERIOD_LABELS = {"text_context": "文献语境", "older_event": "早期记事／旧迹", "broad_survey": "宽年代调查", "interpretation": "后出解释", "proposal": "提议，实施待证"}


def node(parent, tag, **attrs):
    attributes = dict(attrs.pop("attrib", {}))
    attributes.update({key.replace("_", "-"): str(value) for key, value in attrs.items()})
    return ET.SubElement(parent, tag, attributes)


def esc(value):
    return html.escape(str(value), quote=True)


def safe_id(value):
    return re.sub(r"[^a-zA-Z0-9_-]", "-", str(value))


def wrapped(value, limit):
    """Short CJK lines for the SVG, honoring intentional source line breaks."""
    result = []
    for paragraph in str(value).split("\n"):
        if not paragraph:
            result.append("")
        while paragraph:
            result.append(paragraph[:limit])
            paragraph = paragraph[limit:]
    return result


def paragraph(root, x, y, value, size=16, color=MUTED, limit=60, leading=23, anchor="start"):
    for index, part in enumerate(wrapped(value, limit)):
        label(root, x, y + index * leading, part, size, color, anchor)


def midpoint(points):
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    total = sum(lengths)
    if total == 0:
        return points[0]
    target = total * 0.5
    for a, b, length in zip(points, points[1:], lengths):
        if target <= length and length:
            fraction = target / length
            return a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction
        target -= length
    return points[-1]


def style_for(segment):
    relation, period = segment["relationship_type"], segment["period_class"]
    if relation in ("adjacency", "containment"):
        return "#87918a", "2 7", 2.0
    if relation == "stratigraphy":
        return "#777080", "3 6", 2.2
    if relation in ("proposal", "hypothesis") or period in ("interpretation", "proposal"):
        return PROPOSED, "8 6", 2.7
    if period in ("older_event", "broad_survey"):
        return OLD, "10 5", 3.2
    return WATER, None, 3.6


def draw_plate(plate, number, total, study_label="盛时洛阳  /  P4.6.7  /  水系关系"):
    pid = safe_id(plate["id"])
    root = ET.Element("svg", xmlns="http://www.w3.org/2000/svg", width="1020", height="760",
                      viewBox="0 0 1020 760", role="img", attrib={"font-family": "Noto Sans CJK SC, sans-serif",
                      "data-water-map": plate["id"], "aria-labelledby": f"title-{pid} desc-{pid}"})
    node(root, "title", id=f"title-{pid}").text = plate["title"]
    node(root, "desc", id=f"desc-{pid}").text = "相对位置关系图，非实测比例。只有明确流向使用箭头。编号可在网页和JSON中查阅原典与判断。"
    node(root, "rect", x=0, y=0, width=1020, height=760, fill=PAPER)
    defs = node(root, "defs")
    for color_name, color in (("water", WATER), ("old", OLD), ("proposed", PROPOSED)):
        marker = node(defs, "marker", id=f"arrow-{pid}-{color_name}", markerWidth=13, markerHeight=11,
                      refX=12, refY=5.5, orient="auto", markerUnits="userSpaceOnUse")
        node(marker, "path", d="M 0 0 L 12 5.5 L 0 11 L 3 5.5 Z", fill=color)
    label(root, 44, 23, study_label, 12, MUTED)
    label(root, 975, 25, f"{number:02d} / {total:02d}", 14, MUTED, "end")
    label(root, 44, 62, plate["title"], 30, INK)
    subtitle = plate.get("subtitle", "")
    paragraph(root, 45, 88, subtitle, 16, MUTED, 58, 21)
    legend_y = 128
    legend = (
        (45, "流向", WATER, None, True),
        (203, "相连", WATER, None, False),
        (361, "仅相邻", "#87918a", "2 7", False),
        (539, "旧迹／调查", OLD, "10 5", False),
        (768, "提议／解释", PROPOSED, "8 6", False),
    )
    if plate.get("legend_mode") == "p468":
        legend = (
            (45, "流向", WATER, None, True),
            (190, "相连", WATER, None, False),
            (335, "方位相邻", "#87918a", "2 7", False),
            (500, "位于其内", "#87918a", "2 7", False),
            (665, "层位先后", "#777080", "3 6", False),
            (840, "解释", PROPOSED, "8 6", False),
        )
    for x, text, color, dash, arrow in legend:
        line(root, x, legend_y, x+37, legend_y, color, 2.6, dash)
        if arrow:
            node(root, "path", d=f"M{x+29} {legend_y-4} L{x+38} {legend_y} L{x+29} {legend_y+4}", fill="none", stroke=color, stroke_width=2)
        label(root, x+46, legend_y+5, text, 14, MUTED)
    line(root, 45, 143, 975, 143, RULE, 1)

    for box in plate.get("reference_boxes", []):
        node(root, "rect", x=box["x"], y=box["y"], width=box["width"], height=box["height"],
             rx=7, fill="#f0f1e9", stroke="#b7c0b6", stroke_width=1.2, stroke_dasharray="5 5")
        paragraph(root, box["x"]+box["width"]/2, box["y"]+24, box["label"], 15, "#718075", 20, 21, "middle")

    water = node(root, "g", attrib={"class": "water-segments"})
    for index, segment in enumerate(plate["segments"], 1):
        color, dash, width = style_for(segment)
        group = node(water, "g", attrib={"class": "water-segment", "data-segment-id": segment["id"],
                     "data-period-class": segment["period_class"], "data-relationship": segment["relationship_type"],
                     "data-from": segment["from"], "data-to": segment["to"],
                     "tabindex": "0", "role": "button", "aria-label": f"{index:02d} {segment['label']}，查看依据"})
        node(group, "title").text = f"{index:02d} {segment['label']} · {RELATION_LABELS[segment['relationship_type']]} · {PERIOD_LABELS[segment['period_class']]}"
        points = segment["points"]
        commands = "M " + " L ".join(f"{x:g} {y:g}" for x, y in points)
        node(group, "path", d=commands, fill="none", stroke="transparent", stroke_width=24,
             attrib={"class": "segment-hit", "pointer-events": "stroke"})
        route = node(group, "path", d=commands, fill="none", stroke=color, stroke_width=width,
                     stroke_linejoin="round", stroke_linecap="round", attrib={"class": "segment-route"})
        if dash:
            route.set("stroke-dasharray", dash)
        if segment["relationship_type"] == "flow":
            color_name = "water" if color == WATER else "old" if color == OLD else "proposed"
            route.set("marker-end", f"url(#arrow-{pid}-{color_name})")
        x, y = segment.get("label_position", midpoint(points))
        node(group, "circle", cx=f"{x:g}", cy=f"{y:g}", r=11.5, fill=PAPER, stroke=color, stroke_width=1.3,
             attrib={"class": "segment-number-bg"})
        label(group, x, y+4, f"{index:02d}", 11.5, color, "middle")

    places = node(root, "g", attrib={"class": "water-nodes"})
    for item in plate["nodes"]:
        x, y, kind = item["x"], item["y"], item.get("kind", "place")
        group = node(places, "g", attrib={"class": "water-node", "data-node-id": item["id"], "data-kind": kind})
        if kind in ("city", "gate", "building", "site"):
            node(group, "rect", x=x-5, y=y-5, width=10, height=10, fill=PAPER, stroke=INK, stroke_width=1.8)
        elif kind in ("pond", "lake", "pool"):
            node(group, "ellipse", cx=x, cy=y, rx=8, ry=5, fill="#dcebe5", stroke=WATER, stroke_width=1.7)
        elif kind in ("break", "gap", "unknown", "end"):
            node(group, "circle", cx=x, cy=y, r=6, fill=PAPER, stroke=PROPOSED, stroke_width=2)
        elif kind not in ("label", "reference"):
            node(group, "circle", cx=x, cy=y, r=4, fill=PAPER, stroke=WATER, stroke_width=1.8)
        dx, dy = item.get("label_dx", 0), item.get("label_dy", -16)
        anchor = item.get("label_anchor", "middle")
        paragraph(group, x+dx, y+dy, item["label"], 17, INK, 15, 22, anchor)
    for annotation in plate.get("annotations", []):
        paragraph(root, annotation["x"], annotation["y"], annotation["text"], 15, MUTED, annotation.get("max_chars", 34), 21)

    line(root, 45, 632, 975, 632, RULE, 1)
    notes = plate.get("notes", [])
    note_lines = []
    for note in notes:
        note_lines.extend(wrapped(note, 64))
    if len(note_lines) > 4:
        raise ValueError(f"Plate {plate['id']} notes need more than four footer lines; shorten the notes")
    for index, note in enumerate(note_lines):
        label(root, 45, 657+index*20, note, 14, MUTED)
    label(root, 45, 744, "相对位置 · 非实测比例 · 图中编号对应网页逐段依据与 readings.json", 13, MUTED)
    label(root, 975, 744, "PDF / SVG 为完整证据层", 12, MUTED, "end")
    return root


def source_links(segment, source_by_id):
    result = []
    for sid in segment.get("source_ids", []):
        source = source_by_id[sid]
        result.append(f'<a href="{esc(source["url"])}" target="_blank" rel="noopener">{esc(source["title"])}</a>')
    return " · ".join(result)


def evidence_html(data):
    sources = {source["id"]: source for source in data["sources"]}
    result = []
    for plate in data["plates"]:
        result.append(f'<section class="evidence-group"><h3>{esc(plate["title"])}</h3><div class="table-scroll"><table><thead><tr><th>图段</th><th>原典与定位</th><th>采用的判断</th></tr></thead><tbody>')
        for index, segment in enumerate(plate["segments"], 1):
            quote = esc(segment.get("quote", "")).replace("\n", "<br>")
            result.append(f'<tr id="evidence-{esc(segment["id"])}"><th scope="row"><span class="row-number">{index:02d}</span>{esc(segment["label"])}<small>{esc(segment["id"])} · {RELATION_LABELS[segment["relationship_type"]]}<br>{PERIOD_LABELS[segment["period_class"]]}</small></th>'
                          f'<td><blockquote>{quote or "此项采用调查报告或后出解释，详见所列来源。"}</blockquote><p class="locator">{esc(segment.get("locator", ""))}</p>{source_links(segment, sources)}</td>'
                          f'<td><p>{esc(segment.get("reading", ""))}</p><p class="limit"><strong>可确定到这里：</strong>{esc(segment.get("limit", ""))}</p></td></tr>')
        result.append("</tbody></table></div></section>")
    return "\n".join(result)


def render_html(data, diagrams, source_dir=SOURCE, folder=FOLDER):
    template = (source_dir / "index.html").read_text(encoding="utf-8")
    tabs, panels = [], []
    for index, (plate, diagram) in enumerate(zip(data["plates"], diagrams), 1):
        pid = plate["id"]
        tabs.append(f'<button type="button" data-plate-choice="{esc(pid)}" aria-pressed="{str(index == 1).lower()}"><span>{index:02d}</span>{esc(plate["title"])}</button>')
        svg = ET.tostring(diagram, encoding="unicode")
        panels.append(f'<article class="plate-panel" id="plate-{esc(pid)}" data-plate-panel="{esc(pid)}"><h3 class="sr-only">{esc(plate["title"])}</h3><div class="map-viewport">{svg}</div>'
                      f'<p class="map-caption">相对位置关系图，图上距离不表示实际里程。<a href="{folder}/{esc(pid)}.svg">下载本图 SVG</a></p></article>')
    source_html = "\n".join(f'<li id="source-{esc(s["id"])}"><a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["title"])}</a><p>{esc(s.get("locator", ""))}</p><small>{esc(s.get("type", ""))}</small></li>' for s in data["sources"])
    question_html = "\n".join(f'<article class="question"><h3>{esc(q["label"])}</h3><p>{esc(q["missing"])}</p><p class="question-decision">{esc(q["decision"])}</p></article>' for q in data.get("open_questions", []))
    coverage = data.get("legacy_water_coverage", [])
    coverage_html = ""
    if coverage:
        lines = []
        for item in coverage:
            if isinstance(item, str):
                lines.append(f"<li>{esc(item)}</li>")
            else:
                fields = [f'{key}：{value}' for key, value in item.items() if value is not None]
                lines.append(f'<li>{esc("；".join(fields))}</li>')
        coverage_html = '<details class="coverage"><summary>与前册水系对象的对应</summary><ul>'+"".join(lines)+"</ul></details>"
    encoded = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    additional = []
    for path in sorted(source_dir.glob("*.json")):
        if path.name == "readings.json":
            continue
        extra = load(path)
        title = extra.get("title", extra.get("task", path.stem)) if isinstance(extra, dict) else path.stem
        additional.append(f'<a href="{folder}/{esc(path.name)}">{esc(title)}（JSON） <span>↓</span></a>')
    replacements = {
        "<!-- PLATE_COUNT -->": str(len(data["plates"])),
        "<!-- PLATE_COUNT_CN -->": {1:"一",2:"两",3:"三",4:"四",5:"五",6:"六"}.get(len(data["plates"]), str(len(data["plates"]))),
        "<!-- STUDY_TITLE -->": esc(data["title"]),
        "<!-- STUDY_SUMMARY -->": esc(data.get("summary", "")),
        "<!-- GENERATED_TABS -->": "\n".join(tabs),
        "<!-- GENERATED_PLATES -->": "\n".join(panels),
        "<!-- GENERATED_EVIDENCE -->": evidence_html(data),
        "<!-- GENERATED_SOURCES -->": source_html,
        "<!-- GENERATED_QUESTIONS -->": question_html,
        "<!-- GENERATED_COVERAGE -->": coverage_html,
        "<!-- STUDY_DATA -->": encoded,
        "<!-- ADDITIONAL_DOWNLOADS -->": "\n".join(additional),
    }
    for marker, replacement in replacements.items():
        if marker not in template:
            raise ValueError(f"Missing HTML template marker: {marker}")
        template = template.replace(marker, replacement)
    return template


def validate(data):
    if not data["plates"]:
        raise ValueError("P4.6.7 requires at least one map")
    sources = {source["id"] for source in data["sources"]}
    plate_ids, segment_ids = set(), set()
    for plate in data["plates"]:
        pid = plate["id"]
        if pid in plate_ids or safe_id(pid) != pid:
            raise ValueError(f"Invalid or repeated plate ID: {pid}")
        plate_ids.add(pid)
        node_ids = {item["id"] for item in plate["nodes"]}
        for segment in plate["segments"]:
            if segment["id"] in segment_ids:
                raise ValueError(f"Repeated segment ID: {segment['id']}")
            segment_ids.add(segment["id"])
            if segment["from"] not in node_ids or segment["to"] not in node_ids:
                raise ValueError(f"Segment endpoints absent: {segment['id']}")
            if segment["relationship_type"] not in RELATION_LABELS or segment["period_class"] not in PERIOD_LABELS:
                raise ValueError(f"Unrecognized evidence class: {segment['id']}")
            if not segment.get("source_ids") or not set(segment["source_ids"]) <= sources:
                raise ValueError(f"Unresolved source: {segment['id']}")
            if len(segment["points"]) < 2:
                raise ValueError(f"Missing layout points: {segment['id']}")


def build(site=SITE):
    data = load(SOURCE / "readings.json")
    validate(data)
    dest = site / FOLDER
    dest.mkdir(parents=True, exist_ok=True)
    (site / "downloads").mkdir(exist_ok=True)
    diagrams, paths = [], []
    for index, plate in enumerate(data["plates"], 1):
        diagram = draw_plate(plate, index, len(data["plates"]))
        path = dest / f"{plate['id']}.svg"
        ET.ElementTree(diagram).write(path, encoding="utf-8", xml_declaration=True)
        diagrams.append(diagram)
        paths.append(path)
    if sha(ARCHIVED_ATLAS) != ARCHIVED_ATLAS_SHA:
        raise ValueError("Archived P4.6.7 PDF bytes changed")
    shutil.copyfile(ARCHIVED_ATLAS, site / ATLAS)
    copied = [*sorted(SOURCE.glob("*.json")), SOURCE / "study.css", SOURCE / "water-ui.js"]
    for path in copied:
        shutil.copyfile(path, dest / path.name)
    (site / PAGE).write_text(render_html(data, diagrams), encoding="utf-8")

    previous = site / PREVIOUS
    original = previous.read_text(encoding="utf-8").replace(ENTRY, "")
    expected = (ROOT / "research/prosperity-v4/south-466/index.html").read_text(encoding="utf-8")
    marker = '<nav aria-label="本册目录">'
    if original != expected or original.count(marker) != 1:
        raise ValueError("Review the preserved P4.6.6 page before adding its continuation")
    previous.write_text(original.replace(marker, ENTRY+marker, 1), encoding="utf-8")
    earlier = site / "prosperity-field-p464.html"
    field_page = earlier.read_text(encoding="utf-8").replace(CORRECTION, "")
    field_marker = '<section id="hongchi">'
    if field_page.count(field_marker) != 1:
        raise ValueError("P4.6.4 correction anchor is not unique")
    earlier.write_text(field_page.replace(field_marker, CORRECTION+field_marker, 1), encoding="utf-8")
    info, release = load(site / "build-info.json"), load(site / "release.json")
    release["extensions"] = sorted(set(release["extensions"]) | {VERSION})
    release["prosperity_water_p467_version"] = VERSION
    release["current_milestone"] = "盛时 P4.6.7 · 河流与水道：城内外的连接与分期"
    dump(site / "release.json", release)
    segments = [segment for plate in data["plates"] for segment in plate["segments"]]
    info["prosperity_water_p467"] = {
        "version": VERSION, "source_commit": ARCHIVED_COMMIT, "page": PAGE,
        "atlas": ATLAS, "readings": f"{FOLDER}/readings.json", "plates": [path.name for path in paths],
        "atlas_pages": len(paths), "segments": len(segments),
        "relation_counts": dict(Counter(segment["relationship_type"] for segment in segments)),
        "period_counts": dict(Counter(segment["period_class"] for segment in segments)),
        "layout_coordinates_only": True, "geographic_coordinates_added": 0,
        "entry_id": "p467-entry",
        "data_files": [f"{FOLDER}/{path.name}" for path in copied if path.suffix == ".json"],
        "historical_correction": {"page": earlier.name, "id": "p467-water-correction", "topic": "七里涧接文及身份的不同解释"},
    }
    changed = [*paths, site / ATLAS, site / PAGE, previous, earlier, site / "release.json"]
    changed += [dest / path.name for path in copied]
    for path in changed:
        info["files_sha256"][path.relative_to(site).as_posix()] = sha(path)
    dump(site / "build-info.json", info)
    return info["prosperity_water_p467"]


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
