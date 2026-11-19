"""Draw the southern gate roads, the excavated Biyong channels and the written itineraries."""
import shutil
from xml.etree import ElementTree as ET

from dual_cartography import dump, load, sha
from north_b4 import render_atlas
from prosperity_anchors_p461 import ROOT, SITE
from prosperity_corridors_p463 import INK, MUTED, ROAD, WATER, label, line, node, plate
from prosperity_gates_p465 import PAGE as PREVIOUS, trace

FOLDER = "south-466"
SOURCE = ROOT / "research/prosperity-v4" / FOLDER
PAGE = "prosperity-south-p466.html"
ATLAS = f"downloads/{FOLDER}.pdf"
PRESERVED_SOURCE_COMMIT = "a5d9fa3ee0a1eccce7cbd2e53cebcb57e9983632"
PRESERVED_ATLAS_SHA256 = "90e8011316936430cd06a2cf5660d8c749936c89f758ca9058d2d40b29990589"
ENTRY = f'<p id="p466-entry"><a href="./{PAGE}">续读 · 城南两条大道、谷水与永桥</a></p>\n'
PAPER, PALE, RULE = "#faf8f0", "#dce9e6", "#c2cabd"


def marker(root, x, y, filled, color=ROAD):
    node(root, "circle", cx=x, cy=y, r=5, stroke=color, stroke_width=2.6,
         fill=color if filled else PAPER)


def plan_plate(data):
    root = plate("城南两条大道怎样夹住明堂", "钱国祥2018年复原图的城南局部。原图北向上，水岸、道路、遗址符号按同一像素比例摘绘。")
    def project(x, y):
        return 61 + (x - 475) * 2.1, 202 + (y - 549) * 2.1

    north = data["north_bank_sample_px"]
    south = data["south_bank_sample_px"]
    pts = [project(*pt) for pt in north + list(reversed(south))]
    node(root, "polygon", points=" ".join(f"{x:.1f},{y:.1f}" for x, y in pts), fill=PALE)
    for bank in (north, south):
        trace(root, bank, project, WATER, 2.6)
    for name, samples in data["road_samples_px"].items():
        trace(root, samples, project, ROAD, 3)
        x, y = project(*samples[0])
        label(root, x, y-18, name+"门", 18, ROAD, "middle")
    trace(root, data["bridge_symbol_ends_px"], project, INK, 6)
    y = data["reading_row_y_px"]
    edges = data["road_edges_at_row_px"]
    left, right = [project(sum(edges[k])/2, y)[0] for k in ("平昌", "开阳")]
    row = project(0, y)[1]
    line(root, left, row, right, row, MUTED, 1.7, "5 3")
    for x in (left, right):
        line(root, x, row-5, x, row+5, MUTED, 2)
    label(root, (left+right)/2, row-11, "39 px", 16, MUTED, "middle")
    offsets = {"灵台":(-8,-12,"end"), "明堂":(2,31,"middle"),
               "辟雍":(5,31,"middle"), "太学":(10,-8,"start")}
    for name, point in data["places_px"].items():
        x, y = project(*point)
        marker(root, x, y, name in ("明堂", "太学"))
        dx, dy, anchor = offsets[name]
        label(root, x+dx, y+dy, name, 18, INK, anchor)
    label(root, 219, 477, "永桥", 18, INK, "end")
    label(root, 320, 538, "古洛河", 23, WATER)
    line(root, 471, 600, 471 + 46*2.1, 600, INK, 3)
    for x in (471, 471+46*2.1):
        line(root, x, 594, x, 606, INK, 2)
    label(root, 518, 630, "图上 0.5 公里", 16, MUTED, "middle")
    line(root, 648, 148, 648, 625, RULE, 1)
    label(root, 674, 182, "两道相隔多远？", 24)
    label(root, 674, 226, "取明堂以北同一图行，量两条", 18)
    label(root, 674, 256, "道路双线各自的中点。", 18)
    label(root, 674, 307, "39 像素 ÷ 每公里 92 像素", 20, ROAD)
    label(root, 674, 347, "图上约 0.4 公里", 25, ROAD)
    label(root, 674, 390, "地面实测间距尚待道路总图。", 17, MUTED)
    label(root, 674, 457, "遗址在盛时怎样使用？", 20)
    label(root, 674, 493, "实心　明堂重修、太学恢复。", 17)
    label(root, 674, 522, "《伽蓝记》记明堂营建于正光年间。", 16, MUTED)
    label(root, 674, 561, "空心　灵台旧址改作寺院，", 18)
    label(root, 674, 591, "　　　辟雍旧基未见北魏重修。", 17)
    line(root, 44, 650, 975, 650, RULE, 1)
    label(root, 44, 684, "永桥取原图桥符号，古洛河取原图河带局部。桥符号两端与道路截绘处都没有地面测点。", 17)
    label(root, 44, 714, "图源：钱国祥2018年图一，朱岩石2024年图6转载；遗址使用分期据2010年南郊考古成果选介。", 15, MUTED)
    return root


def ditch_plate(data):
    root = plate("辟雍水沟从北侧分水，两支折向南", "据南郊考古成果选介的量测绘制。北在上，横纵同尺度，方位取报告所述方向。")
    cx, fork_y, scale = 318, 298, 0.70
    start_y = fork_y - data["trunk_preserved_m"]*scale
    end_y = fork_y + data["south_each_approx_m"]*scale
    spread = data["lateral_each_gt_m"]*scale
    for side in (-1, 1):
        x = cx+side*spread
        line(root, cx, fork_y, x, fork_y, WATER, 4)
        line(root, x, fork_y, x, end_y, WATER, 4)
        marker(root, x, end_y, False, WATER)
        label(root, (cx+x)/2, fork_y-13, "180余米", 17, INK, "middle")
    line(root, cx, start_y, cx, fork_y, WATER, 5)
    line(root, cx-9, start_y+3, cx+9, start_y-3, INK, 2)
    marker(root, cx, fork_y, True, WATER)
    label(root, cx, start_y-14, "北端遭今洛河冲毁", 18, INK, "middle")
    label(root, cx+13, (start_y+fork_y)/2, "残长180米", 18)
    label(root, cx-151, 443, "约400米", 18, WATER, "end")
    label(root, cx+145, 443, "约400米", 18, WATER)
    ref_y = fork_y + data["fork_north_of_hall_approx_m"]*scale
    line(root, cx+9, fork_y+6, cx+9, ref_y, MUTED, 1.4, "5 3")
    line(root, cx-1, ref_y, cx+18, ref_y, MUTED, 1.6)
    label(root, cx+22, (fork_y+ref_y)/2, "约156米", 16, MUTED)
    label(root, cx, ref_y+31, "中心殿基北面", 18, INK, "middle")
    label(root, cx, 604, "南端失去踪迹", 17, MUTED, "middle")
    line(root, 69, 640, 69+scale*100, 640, INK, 3)
    for x in (69, 69+scale*100):
        line(root, x, 635, x, 646, INK, 2)
    label(root, 151, 646, "100米", 16, MUTED)
    line(root, 614, 148, 614, 648, RULE, 1)
    label(root, 641, 183, "北侧引水干道", 23)
    label(root, 641, 220, "残长180米，沟宽4–5米。", 19)
    label(root, 641, 272, "分流后的沟槽", 23)
    label(root, 641, 311, "一般宽3–4米，局部不足2米。", 19)
    label(root, 641, 350, "图中两支各取180米作为下限。", 17, MUTED)
    label(root, 641, 415, "南端是否相通？", 23)
    label(root, 641, 455, "现有勘探未追到两支的南端，", 17)
    label(root, 641, 486, "供水源头也有待确认。", 17)
    label(root, 641, 547, "年代", 22, ROAD)
    label(root, 641, 583, "遗址以东汉、魏晋为主。", 18)
    label(root, 641, 613, "516—528年沟内有无流水待证。", 17)
    line(root, 44, 663, 975, 663, RULE, 1)
    label(root, 44, 700, "2010年南郊考古成果选介（1962—1992年调查发掘）。引水干道的北端为残存边界。", 17, MUTED)
    return root


def water_plate(data):
    root = plate("谷水、引洛渠与永桥各经过哪里", "三组记录的地点可相互参照。图中间距用于排列文字，图上交点不能代替发掘的桥涵或桥头。")
    label(root, 47, 170, "谷水从西向东", 24, WATER)
    label(root, 259, 169, "《水经注》卷十六", 17, MUTED)
    places = data["texts"]["gu_downstream_order"]
    for i, name in enumerate(places):
        x = 101+135*i
        if i < len(places)-1:
            line(root, x, 230, x+135, 230, WATER, 3)
        marker(root, x, 230, False, WATER)
        label(root, x, 207 if i % 2 == 0 else 266, name, 18, INK, "middle")
    label(root, 48, 302, "灵台一处有两种断句，此处只标谷水经过灵台附近。", 17, MUTED)
    line(root, 45, 326, 975, 326, RULE, 1)
    line(root, 508, 351, 508, 624, RULE, 1)
    label(root, 46, 368, "引洛渠在津阳门外街东", 23, WATER)
    label(root, 46, 401, "2022年报告对东汉工程的定位", 17, MUTED)
    line(root, 158, 452, 158, 565, ROAD, 4)
    label(root, 148, 514, "津阳门外街", 18, ROAD, "end")
    line(root, 306, 560, 306, 453, WATER, 4)
    node(root, "path", d="M298 465 L306 450 L314 465", fill="none", stroke=WATER, stroke_width=3)
    label(root, 306, 440, "城南阳渠", 18, WATER, "middle")
    label(root, 320, 516, "引洛渠", 18, WATER)
    label(root, 306, 590, "古洛河", 18, WATER, "middle")
    label(root, 534, 368, "永桥在宣阳门外御道上", 23, ROAD)
    label(root, 534, 401, "《水经注》卷十六与《洛阳伽蓝记》卷三", 17, MUTED)
    for a,b in ((453,502),(542,566)):
        line(root, 750, a, 750, b, ROAD, 4)
    label(root, 750, 442, "宣阳门", 18, ROAD, "middle")
    node(root, "rect", x=621, y=502, width=260, height=40, fill=PALE)
    line(root, 750, 501, 750, 543, INK, 6)
    label(root, 637, 529, "洛水", 17, WATER)
    label(root, 768, 529, "永桥", 17)
    label(root, 767, 479, "门外四里至水", 16, MUTED)
    label(root, 750, 591, "桥南御道通向圜丘", 18, ROAD, "middle")
    line(root, 45, 634, 975, 634, RULE, 1)
    label(root, 46, 672, "堰址的文字范围在西大郊北至大郊寨西南，2023年示意图中的永桥在西大郊以南。", 18)
    label(root, 46, 710, "渠口、洛河古岸和永桥两端的地层仍须核查。图上未将辟雍旧沟接入任何一条城南干渠。", 16, MUTED)
    return root


def build(site=SITE):
    dest = site / FOLDER
    dest.mkdir(exist_ok=True)
    data = load(SOURCE / "readings.json")
    plates = []
    for name, drawing in (("roads", plan_plate(data["plan"])), ("ditch", ditch_plate(data["excavation"]["biyong"])),
                          ("waters", water_plate(data))):
        path = dest / f"{name}.svg"
        ET.ElementTree(drawing).write(path, encoding="utf-8", xml_declaration=True)
        plates.append(path)
    archived_atlas = ROOT / "research/prosperity-v4/archive/south-466.pdf"
    if sha(archived_atlas) != PRESERVED_ATLAS_SHA256:
        raise ValueError("The accepted P4.6.6 atlas must retain its verified bytes")
    shutil.copyfile(archived_atlas, site / ATLAS)
    shutil.copyfile(SOURCE / "readings.json", dest / "readings.json")
    shutil.copyfile(SOURCE / "index.html", site / PAGE)
    previous = site / PREVIOUS
    original = previous.read_text().replace(ENTRY, "")
    marker_html = '<nav aria-label="本册目录">'
    if original != (ROOT / "research/prosperity-v4/gates-465/index.html").read_text() or original.count(marker_html) != 1:
        raise ValueError("Review the P4.6.5 article before adding its continuation")
    previous.write_text(original.replace(marker_html, ENTRY + marker_html, 1))
    info, release = load(site / "build-info.json"), load(site / "release.json")
    version = "prosperity-south-p466"
    release["extensions"] = sorted(set(release["extensions"]) | {version})
    release["current_milestone"] = "盛时 P4.6.6 · 城南两条大道、谷水与永桥"
    dump(site / "release.json", release)
    info["prosperity_south_p466"] = {"version": version, "source_commit": PRESERVED_SOURCE_COMMIT, "page": PAGE,
                                     "atlas": ATLAS, "readings": f"{FOLDER}/readings.json", "plates": [p.name for p in plates]}
    for path in [*plates, dest / "readings.json", site / PAGE, site / ATLAS, previous, site / "release.json"]:
        info["files_sha256"][path.relative_to(site).as_posix()] = sha(path)
    dump(site / "build-info.json", info)
