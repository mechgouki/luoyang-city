"""Publish the Baima gate measurements and the textual relations at Hongchi."""
import shutil
from xml.etree import ElementTree as ET

from dual_cartography import dump, load, sha
from north_b4 import render_atlas
from prosperity_anchors_p461 import ROOT, SITE, digest
from prosperity_corridors_p463 import INK, MUTED, ROAD, WATER, label, line, node, plate

SOURCE = ROOT / "research/prosperity-v4/source-checks"
PAGE = "prosperity-field-p464.html"
PREVIOUS = "prosperity-corridors-p463.html"
ENTRY = f'<p id="p464-entry"><a href="./{PAGE}">补图 · 白马寺南坊门量测与鸿池陂水路</a></p>\n'
ATLAS = "downloads/field-464.pdf"


def gate_plate(data):
    root = plate("白马寺北里坊 · 南门入口量测", "北魏废弃堆积层下，坊内居中纵街接入西阳门外大道。尺寸分行绘制，共用米尺。")
    origin, scale = 345, 22
    label(root, 45, 160, "发掘所见", 21)
    label(root, origin, 160, "各行从零起算，条形长度只表示尺寸", 18, MUTED)
    for metres in (0, 5, 10, 15, 20, 25):
        x = origin + metres * scale
        line(root, x, 191, x, 540, "#d8dace", 1)
        label(root, x, 183, str(metres), 16, MUTED, "middle")
    label(root, 937, 183, "米", 16, MUTED)
    low, high = data["east_foundation_ns_approx_m"]
    rows = [
        ("大道北侧缺口宽", data["road_opening_width_approx_m"], "约"),
        ("密集车辙带宽", data["rut_band_width_m"], ""),
        ("东西向沟槽 · 东西长", data["groove_ew_length_approx_m"], "约"),
        ("同一沟槽 · 南北宽", data["groove_ns_width_m"], ""),
        ("西侧褐土基槽 · 南北宽", data["west_foundation_ns_m"], ""),
        ("东侧红土基础 · 南北宽", low, "range"),
        ("同一基础 · 东西已揭露", data["east_foundation_ew_exposed_gt_m"], ">"),
    ]
    for index, (name, value, qualifier) in enumerate(rows):
        y = 221 + index * 50
        end = origin + value * scale
        label(root, 45, y + 7, name, 19)
        node(root, "rect", x=origin, y=y-5, width=value*scale, height=10, fill=ROAD)
        caption = f"{qualifier}{value:g}"
        if qualifier == "range":
            line(root, end, y, origin + high*scale, y, ROAD, 3, "3 3")
            end = origin + high*scale
            caption = f"约{low}–{high}"
        if qualifier == ">":
            node(root, "path", d=f"M {end} {y-5} l 7 5 -7 5", fill="none", stroke=ROAD, stroke_width=2)
        label(root, end + 14, y + 6, caption, 17, INK)
    label(root, 45, 584, "车辙带宽和沟槽长各为4.6米；两者的起讫点与量测对象不同。", 19)
    label(root, 45, 624, "西侧基槽与沟槽相接，发掘者推测与门墩、门槛有关。东侧红土基础的用途仍待确认。", 17, MUTED)
    label(root, 45, 658, "东侧基础残厚0.1–0.3米。坊内中央十字至此门的距离待有比例尺的总平面。", 17, MUTED)
    label(root, 45, 704, "据张效儒报告，中国社会科学院考古研究所2025年度考古工作成果汇报会纪要（三）。", 16, MUTED)
    return root


def water_plate(data):
    root = plate("鸿池陂 · 池内横塘与下游入洛", "按古籍分段读水。方位仅用在有原文依据的地方；图形间距不表示里程。")
    label(root, 45, 171, "池内与池东", 23, WATER)
    for x, first, second in [(48, "阮曲", "穀水转而东注"), (365, "鸿池陂", "池内有横塘"), (698, "七里涧", "后文记水东行，左合此涧")]:
        node(root, "rect", x=x, y=194, width=260, height=93, rx=9, fill="#e7efea", stroke="#96aaa3")
        label(root, x+17, 230, first, 23)
        label(root, x+17, 263, second, 16, MUTED)
    for x in (310, 627):
        end = x + 46
        line(root, x, 240, end, 240, WATER, 2)
        node(root, "path", d=f"M {end-6} 235 l 6 5 -6 5", fill="none", stroke=WATER, stroke_width=2)
    label(root, 55, 331, f"横塘呈{data['pond_internal_bank_orientation']}向；池中的南北位置、塘长与通水口位置未详。", 18, WATER)
    line(root, 45, 356, 974, 356, "#bcc8bd", 1)
    label(root, 45, 401, "古偃师城附近", 23, WATER)
    label(root, 50, 448, "卷十六 · 穀水", 20)
    label(root, 286, 448, data["downstream_gu"], 20)
    label(root, 50, 491, "卷十五 · 洛水", 20)
    label(root, 286, 491, data["downstream_luo"], 20)
    line(root, 45, 525, 974, 525, "#bcc8bd", 1)
    label(root, 45, 573, "洪池开渠的提议", 23, ROAD)
    label(root, 50, 616, "《魏书·李冲传》记孝文帝在池上泛舟，提出从池开渠入洛，并列用工与工期条件。", 17)
    label(root, 50, 650, "《高祖纪下》496年所记是拟引洛水入穀，该条未提鸿池。", 17)
    label(root, 50, 700, "盛时池南出口的位置、使用年代和通航情况仍缺田野证据。", 18, MUTED)
    return root


def build(site=SITE):
    dest = site / "field-464"
    dest.mkdir(exist_ok=True)
    data = load(SOURCE / "readings.json")
    plates = []
    for name, diagram in [("gate", gate_plate(data["ward"])), ("hongchi", water_plate(data["hongchi"]))]:
        path = dest / f"{name}.svg"
        ET.ElementTree(diagram).write(path, encoding="utf-8", xml_declaration=True)
        plates.append(path)
    render_atlas(plates, site / ATLAS)
    for name in ("readings.json", "ward-hongchi.md"):
        shutil.copyfile(SOURCE / name, dest / name)
    shutil.copyfile(SOURCE / "index.html", site / PAGE)
    previous = site / PREVIOUS
    content = previous.read_text().replace(ENTRY, "")
    marker = '<nav aria-label="本册目录">'
    if digest(content.encode()) != "f0f912a42b5f8ad44602994955c3830fd1e8486a786a7a47e8dfa8b8d0886285" or content.count(marker) != 1:
        raise ValueError("Review P4.6.3 page before adding the supplement link")
    previous.write_text(content.replace(marker, ENTRY + marker, 1))
    info = load(site / "build-info.json")
    release = load(site / "release.json")
    version = "prosperity-field-p464"
    release["extensions"] = sorted(set(release["extensions"]) | {version})
    release["current_milestone"] = "盛时 P4.6.4 · 白马寺南坊门量测与鸿池陂水路"
    dump(site / "release.json", release)
    info["prosperity_field_p464"] = {"version": version, "source_commit": info["source_commit"], "page": PAGE,
                                    "atlas": ATLAS, "readings": "field-464/readings.json", "plates": [p.name for p in plates]}
    for path in [*plates, dest / "readings.json", dest / "ward-hongchi.md", site / ATLAS, site / PAGE, previous, site / "release.json"]:
        info["files_sha256"][path.relative_to(site).as_posix()] = sha(path)
    dump(site / "build-info.json", info)
