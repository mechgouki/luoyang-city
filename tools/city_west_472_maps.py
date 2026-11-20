"""Two reading plates: original 06a vertices and a separate documentary diagram."""
from xml.etree import ElementTree as ET

from prosperity_city_common_p470 import SVG_NS, feature_paths, tag, text

PAGE = "prosperity-city-west.html"
LIVE = "https://mechgouki.github.io/luoyang-city/" + PAGE
INK, GREEN, RED, PAPER, MUTED = "#252e26", "#28594d", "#96452f", "#fbf8ee", "#526052"


def plate(identifier, height, title, desc):
    root = ET.Element(f"{{{SVG_NS}}}svg", {"id": identifier, "viewBox": f"0 0 620 {height}",
                      "role": "group", "aria-labelledby": identifier+"-title "+identifier+"-desc", "lang": "zh-CN"})
    tag(root, "title", id=identifier+"-title").text = title
    tag(root, "desc", id=identifier+"-desc").text = desc
    tag(root, "style").text = ("text{font-family:'Noto Sans CJK SC','Microsoft YaHei',sans-serif}"
                              "a:focus rect,a:hover rect{stroke:#a24d36;stroke-width:2}"
                              "a:focus circle,a:hover circle,.picked circle[data-point]{fill:#b74924}")
    tag(root, "rect", width=620, height=height, fill=PAPER)
    return root


def source_map(data, target):
    root = plate("west-source", 680, "城西与宫前的三处门址参照",
                 "06a原图的城墙和道路残段，标出西阳、西明两座西门及供辨名的宫城阊阖门。")
    root.set("data-source-frame", "06a")
    text(root, 24, 38, "城西与宫前", 26, INK, font_weight=700)
    text(root, 24, 64, "保护管理图 06a  ·  遗存与道路原绘残段", 16, MUTED)
    tag(root, "rect", x=14, y=83, width=592, height=510, fill="#f0f0e4", stroke="#c5c6b5")
    clip = tag(tag(root, "defs"), "clipPath", id="west-source-clip")
    tag(clip, "rect", x=15, y=84, width=590, height=508)
    # Original PDF userspace is north-up on this plate. Presentation scale only.
    area = tag(tag(root, "g", clip_path="url(#west-source-clip)"), "g",
               transform="translate(126 95) scale(3.08) translate(-265 -235)", data_units="PDF point")
    roads = tag(area, "g", data_layer="source-roads")
    walls = tag(area, "g", data_layer="source-walls")
    points = {p["feature_id"]: p for p in data["map_points"]}
    features = {f["id"]: f for f in data["features"]}
    for f in data["features"]:
        if f["id"] in points:
            continue
        wall = "wall" in f["id"]
        group = tag(walls if wall else roads, "g", data_feature=f["id"])
        tag(group, "title").text = f["label"]+" · "+f["source_feature_code"]
        feature_paths(group, f, "#637467" if wall else "#ae8055", .86 if wall else .55,
                      "1.6 1.1" if f["id"] == "geo-inner-wall-underground" else None)
    for fid, p in points.items():
        f = features[fid]
        x, y = f["source_pdf_geometry"]["coordinates"]
        palace = p["entity_id"] == "ic_changhe_palace"
        a = tag(area, "a", href=target+"#entity-"+p["entity_id"], data_feature=fid, data_entity=p["entity_id"],
                aria_label=p["label"]+" · "+f["source_feature_code"])
        tag(a, "title").text = p["label"]+" · "+f["source_feature_code"]+" · "+f["source_historical_period"]
        tag(a, "circle", cx=x, cy=y, r=6, fill="transparent")
        tag(a, "circle", cx=x, cy=y, r=2.0, fill=PAPER if palace else GREEN, stroke=GREEN,
            stroke_width=.85, data_point=fid)
        # Label offsets are typography, kept outside the source geometry.
        dx = 6 if palace else -6
        text(a, x+dx, y+1.5, p["label"], 5.3, INK, class_="place-label",
             text_anchor="start" if palace else "end", font_weight=700)
    text(root, 552, 116, "北 ↑", 18, GREEN)
    text(root, 28, 622, "● 西墙两门　 ○ 宫门辨名　 ━ 城墙　 ┄ 地下墙段", 17, GREEN)
    text(root, 28, 651, "赭线为来源图的道路残段。三条门外文献御道均未配线。", 16, MUTED)
    return root


def card(root, x, y, width, name, ref, target):
    a = tag(root, "a", href=target+"#"+ref, data_reading=ref, aria_label=name+"，读 "+ref)
    tag(a, "rect", x=x, y=y, width=width, height=40, rx=5, fill="#f4f0df", stroke="#b9baa5")
    text(a, x+width/2, y+26, name, 18, INK, text_anchor="middle")
    return a


def relations(target):
    root = plate("west-relations", 858, "城西三条门道的文献关系",
                 "图板依门序、阊阖门外、西阳门外和西明门外分栏，框线连接文字关系，间距无比例。")
    text(root, 24, 39, "沿三条西门道读《伽蓝记》", 26, INK, font_weight=700)
    text(root, 24, 66, "无比例关系图  ·  点选框内文字可读原条", 16, MUTED)
    def heading(y, label, ref):
        tag(root, "line", x1=24, x2=596, y1=y-24, y2=y-24, stroke="#c8c8b7")
        text(root, 26, y, label, 19, GREEN, font_weight=700)
        text(root, 593, y, ref, 14, MUTED, text_anchor="end")
    heading(112, "西墙四门　由南向北", "WR01—02")
    for x, name in ((26,"西明门"),(174,"西阳门"),(322,"城西阊阖门"),(470,"承明门")):
        card(root, x, 129, 124, name, "WR01", target)
        if x < 470:
            text(root, x+135, 156, "›", 24, MUTED, text_anchor="middle")
    text(root, 26, 198, "宫城阊阖门另属宫前。门序仅示相对次第。", 16, MUTED)
    heading(251, "城西阊阖门外　大觉以东有两条关系", "WR03—10、22")
    card(root, 30, 305, 119, "大觉寺", "WR08", target)
    tag(root, "path", d="M149 325 H172 V288 H308 M172 325 V358 H308", stroke="#88987c", fill="none")
    direction = tag(root, "a", href=target+"#WR05", data_reading="WR05")
    text(direction, 180, 279, "大觉在其西一里许", 15, MUTED)
    text(root, 182, 350, "永明在大觉东", 15, MUTED)
    card(root, 308, 267, 252, "融觉寺 · 门外道南", "WR03", target)
    card(root, 308, 337, 252, "永明寺 · 自身路侧未载", "WR06", target)
    text(root, 26, 412, "两支上下排版仅为分读，融觉与永明的相互方位未定。", 16, MUTED)
    card(root, 27, 432, 563, "永明寺西有宜年里，里内两宅无序", "WR22", target)
    heading(527, "西阳门外　分别看两侧与相邻寺宅", "WR11—16、19—21、23—24")
    card(root, 27, 548, 178, "道北 · 宝光寺", "WR11", target)
    card(root, 214, 548, 184, "法云在宝光西", "WR14", target)
    card(root, 407, 548, 184, "临淮宅在法云北", "WR16", target)
    card(root, 27, 604, 278, "城阳王徽宅 · 门外一里／道南", "WR19", target)
    card(root, 315, 604, 276, "白马西阳条 · 门外三里／道南", "WR23", target)
    text(root, 26, 675, "法云路侧未独立记载。白马西阳、瀍涧两条同一性待考。", 16, MUTED)
    heading(731, "西明门外　冲觉寺与追福塔分期", "WR17—18")
    card(root, 27, 750, 272, "原宅舍为寺 · 门外一里／道北", "WR17", target)
    card(root, 312, 750, 279, "525 年复政后 · 建五层塔", "WR18", target)
    text(root, 26, 823, "寺至迟528年已有依据，追福塔在此以前是否完工仍待证。", 16, MUTED)
    return root


def svg_text(element):
    ET.indent(element)
    return ET.tostring(element, encoding="unicode")
