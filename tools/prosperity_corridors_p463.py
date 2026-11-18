"""Publish the survey dimensions and the two independent readings of Hongchi."""
import html
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from dual_cartography import dump, load, sha
from north_b4 import render_atlas
from prosperity_anchors_p461 import ROOT, SITE, digest, offline_page
from prosperity_network_p462 import PAGE as PREVIOUS

FOLDER = "corridors-463"
SOURCE = ROOT / "research/prosperity-v4" / FOLDER
PAGE = "prosperity-corridors-p463.html"
ATLAS = f"downloads/{FOLDER}.pdf"
BUNDLE = f"downloads/{FOLDER}.zip"
MANIFEST = f"{FOLDER}/bundle-manifest.json"
ENTRY = f'<p id="p463-entry"><a href="./{PAGE}">续读 · 外郭九道、白马寺里坊与鸿池陂</a></p>\n'
INK, MUTED, ROAD, WATER = "#263a34", "#4b625a", "#805536", "#21647a"


def node(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {key.replace("_", "-"): str(value) for key, value in attrs.items()})


def label(root, x, y, value, size=19, color=INK, anchor="start"):
    node(root, "text", x=x, y=y, fill=color, font_size=size, text_anchor=anchor).text = str(value)


def line(root, x1, y1, x2, y2, color=ROAD, width=3, dash=None):
    item = node(root, "line", x1=x1, x2=x2, y1=y1, y2=y2, stroke=color, stroke_width=width)
    if dash:
        item.set("stroke-dasharray", dash)


def plate(title, subtitle):
    root = ET.Element("svg", xmlns="http://www.w3.org/2000/svg", width="1020", height="740",
                      viewBox="0 0 1020 740", attrib={"font-family": "Noto Sans CJK SC, sans-serif"})
    node(root, "title").text = title
    node(root, "rect", x=0, y=0, width=1020, height=740, fill="#faf8f0")
    label(root, 44, 61, title, 34)
    label(root, 45, 101, subtitle, 19, MUTED)
    line(root, 45, 123, 975, 123, "#b4b9a9", 1)
    return root


def ward_plate(ward):
    root = plate("白马寺北 · 六条坊内道路", "2024年发掘汇报所载间距，北在上。正交轴线代表名义位置，短线终点仅为截绘。")
    cx, cy, scale = 356, 362, 2.8
    halfwidth = ward["central_ns_width_m"] * scale / 2
    node(root, "rect", x=cx-halfwidth, y=201, width=halfwidth*2, height=319, fill="#dfccae")
    for offset in ward["ns_offsets_m"]:
        x = cx + scale * offset
        line(root, x, 201, x, 520, ROAD, 2, "8 5" if offset == 0 else None)
    for offset in ward["ew_offsets_m"]:
        y = cy + scale * offset
        line(root, 74, y, 639, y)
    for x, caption in [(cx-43*scale, "86 m"), (cx+43*scale, "86 m")]:
        line(root, x-43*scale, 177, x+43*scale, 177, MUTED, 1)
        for xx in [x-43*scale, x+43*scale]:
            line(root, xx, 169, xx, 184, MUTED, 1)
        label(root, x, 165, caption, 19, INK, "middle")
    for y in (cy-20*scale, cy+20*scale):
        label(root, 625, y+6, "40 m", 18, INK)
    label(root, cx, 548, "中央纵街 · 宽约22 m", 20, ROAD, "middle")
    line(root, 700, 155, 700, 551, "#bec0b2", 1)
    for y, t, s in [(191,"2025年 · 坊南入口",23),(238,"南北向居中道路",19),(278,"↓",26),
                     (320,"坊门候选缺口",19),(352,"宽约7.5 m",23),(404,"↓",26),
                     (450,"西阳门外大道",21),(502,"大道北侧发现缺口；",17),(528,"坊内纵路留有车辙。",17)]:
        label(root, 838, y, t, s, INK, "middle")
    line(root, 77, 582, 77+40*scale, 582, INK, 4)
    for m in (0, 20, 40):
        x = 77+m*scale
        line(root, x, 576, x, 588, INK, 2)
        label(root, x, 610, str(m), 15, INK, "middle")
    label(root, 208, 600, "米 · 左图", 16)
    label(root, 45, 651, "两侧纵路的名义跨度为172米，南北两条横路的名义跨度为80米。完整坊界与次级路宽仍待测。", 18)
    label(root, 45, 690, "右栏只示连通。坊门至坊内中央十字的距离未见公布。图据郭晓涛2024年度报告、2025年度发掘报道。", 16, MUTED)
    return root


def outer_plate(data, old):
    root = plate("哪九条大道从内城通向外郭？", "按出城方向分组。六条东西向道路可对读两端门位，另三条只画资料能够约束的关系。")
    labels = {r["id"]:r for r in old["corridors"]}
    label(root, 48, 167, "内城城门", 20)
    label(root, 395, 167, "外郭内所见关系", 20)
    for i, (name, direction, ident) in enumerate(data["roads"]):
        y = 210 + i*46
        label(root, 50, y, direction + "出　" + name, 20)
        if ident:
            rec = labels[ident]
            label(root, 395, y, f'{rec["outer_gate"]}　·　门间图上直距约 {rec["map_chord_estimate_km"]:.1f} 公里', 19, ROAD)
        elif direction == "西":
            label(root, 395, y, "城门外有道；西端郭门尚缺可核的配对", 19, MUTED)
        else:
            label(root, 395, y, "邙山上与另一北出道会合；会合点待定位", 19, MUTED)
        line(root, 48, y+14, 966, y+14, "#ddded3", 1)
    label(root, 48, 653, "城南开阳门、平昌门外另有两条大道，地方综述将它们列在这九条之外。", 19)
    label(root, 48, 694, "据《文化瀍河》外郭城街道段、钱国祥2018年图一。图上直距不代表完整路长或沿线均经发掘。", 16, MUTED)
    return root


def pond_plate(data):
    root = plate("鸿池陂 · 两幅原图怎样画水口", "两栏分别按各自原图的接线位置绘点。圆点为图上读数，短线只表示接入方向；两幅图的尺度不同。")
    # Extend each short contact outward for its label, never connect the two source frames.
    guides = [[(-38,-49),(-74,17),(42,-37),(42,42)],[(-53,-60),(-76,43),(70,0)]]
    for i, fig in enumerate(data["figures"]):
        x0 = 50 + 495*i
        x1,y1,x2,y2 = fig["crop_xyxy"]
        factor = 1.64 if i==0 else 2.9
        xy = [(x0+45+(p[0]-x1)*factor, 232+(p[1]-y1)*factor) for _,_,p in fig["contacts"]]
        label(root, x0, 172, ["梁克敏 · 2022 图1","黄学超 · 2026 图1"][i], 25)
        label(root, x0, 205, ["汉魏水运渠道复原","《水经注》水系复原"][i], 18, MUTED)
        nodes = list(zip(xy,fig["contacts"],guides[i]))
        for (x,y), (_,name,_), (dx,dy) in nodes:
            line(root, x,y,x+dx,y+dy,WATER,3)
            node(root,"circle",cx=x,cy=y,r=6,fill=WATER)
            label(root,x+dx,y+dy+(-9 if dy<0 else 23),name,17,INK,"middle")
        label(root, x0+190, 368 if i==0 else 347, "鸿池陂", 22, MUTED, "middle")
        label(root,x0,553,["四处接线 · 南缘另有一线向洛水","三处古水接线 · 东侧标作谷水"][i],19,WATER)
    line(root, 509, 150, 509, 558, "#b4b9a9", 1)
    label(root, 46, 605, "梁图以线路相连表示汉魏水运；黄图以蓝线绘古水，红色今洛河另计。两者选取的时期和底图不同。",18)
    label(root, 46, 648, "考古参照：商城东一门石渠向东出门十余米接入低地，记录的是商代排水系统。",18)
    label(root, 46, 693, "图示接线不提供北魏岸界、现场渠口坐标或通航水深。原图尺寸、像素读数和出处见所附数据。",16,MUTED)
    return root


def build(site=SITE):
    info = load(site/"build-info.json")
    release = load(site/"release.json")
    dest = site / FOLDER
    dest.mkdir(exist_ok=True)
    data = load(SOURCE/"evidence.json")
    old = load(site/"network-462/outer.json")
    diagrams = {"outer": outer_plate(data, old), "ward": ward_plate(data["ward"]), "pond": pond_plate(data["hongchi"])}
    plates = []
    for name, svg in diagrams.items():
        path = dest / (name+".svg")
        ET.ElementTree(svg).write(path, encoding="utf-8", xml_declaration=True)
        plates.append(path)
    shutil.copyfile(SOURCE/"evidence.json",dest/"evidence.json")
    render_atlas(plates, site/ATLAS)
    sources = "".join(f'<li id="src-{key}"><a href="{html.escape(rec["url"], quote=True)}">{html.escape(rec["title"])}</a>。{html.escape(rec["locator"])}</li>' for key,rec in data["sources"].items())
    template = (SOURCE/"index.html").read_text()
    page = template.replace("<!-- SOURCES -->",sources)
    (site/PAGE).write_text(page)
    predecessor = site/PREVIOUS
    previous = predecessor.read_text().replace(ENTRY,"")
    marker = '<nav aria-label="图册目录">'
    if previous.count(marker)!=1 or digest(previous.encode())!="0147a872d2bc7c606a9cf2ad2d9c63a7564e48c9606c2b39fcbf09f6cb462c54":
        raise ValueError("P4.6.2 reading page differs from its published baseline")
    predecessor.write_text(previous.replace(marker,ENTRY+marker,1))
    assets = [*plates,dest/"evidence.json",site/ATLAS]
    files = {path.relative_to(site).as_posix():sha(path) for path in assets}
    offline = offline_page(page,FOLDER,ATLAS).encode()
    dump(site/MANIFEST,{"version":"prosperity-corridors-p463","source_commit":info["source_commit"],
                        "files_sha256":files,"offline_index_sha256":digest(offline)})
    with zipfile.ZipFile(site/BUNDLE,"w") as archive:
        for name,content in [("index.html",offline),*((n,(site/n).read_bytes()) for n in [*files,MANIFEST])]:
            archive.writestr(zipfile.ZipInfo(name),content,compress_type=zipfile.ZIP_DEFLATED)
    version = "prosperity-corridors-p463"
    release["extensions"] = sorted(set(release["extensions"]) | {version})
    release["current_milestone"] = "盛时 P4.6.3 · 外郭九道、白马寺里坊与鸿池陂"
    release["prosperity_corridors_p463_version"] = version
    dump(site/"release.json",release)
    info["prosperity_corridors_p463"] = {"version":version,"source_commit":info["source_commit"],"page":PAGE,
                                      "atlas":ATLAS,"bundle":BUNDLE,"manifest":MANIFEST,"atlas_plates":list(diagrams)}
    for name in [*files,PREVIOUS,PAGE,MANIFEST,BUNDLE,"release.json"]:
        info["files_sha256"][name] = sha(site/name)
    dump(site/"build-info.json",info)
