"""Two R7 plates: retain native geometry; keep textual relationships unscaled."""

from city_nodes_r7_maps import box, el, label, lines, link, native_frame, plate

INK, GREEN, GOLD, BLUE = "#263f36", "#315f4e", "#916331", "#427a8b"
MUTED = "#59695d"


def _road(parent, rid, x, y, message, size=18, **attrs):
    target = link(parent, "segment-" + rid, rid)
    label(target, x, y, message, size, fill=attrs.pop("fill", GREEN), **attrs)
    return target


def _arrow(parent, x1, y1, x2, y2, color=GREEN, dashed=False):
    """A relationship arrow, never a historical road or shoreline geometry."""
    import math

    attrs = dict(x1=x1, y1=y1, x2=x2, y2=y2, stroke=color, stroke_width=2,
                 data_diagram="relationship-not-geographic")
    if dashed:
        attrs["stroke_dasharray"] = "7 5"
    el(parent, "line", **attrs)
    theta = math.atan2(y2 - y1, x2 - x1)
    wings = [(x2 - 9 * math.cos(theta + angle), y2 - 9 * math.sin(theta + angle))
             for angle in (-.48, .48)]
    el(parent, "polyline", points=f"{wings[0][0]},{wings[0][1]} {x2},{y2} {wings[1][0]},{wings[1][1]}",
       stroke=color, stroke_width=2, fill="none")


def _relation_row(parent, y, left, relation, right, interpretation=False):
    color = GOLD if interpretation else GREEN
    label(parent, 512, y, left, 19, fill=INK)
    _arrow(parent, 665, y - 7, 921, y - 7, color, interpretation)
    label(parent, 790, y - 19, relation, 17, fill=color, text_anchor="middle")
    label(parent, 955, y, right, 19, fill=INK)


def palace_map(atlas, data):
    root = plate("r7-palace-yongning", "宫前御道与永宁寺 · 方向、残迹和解释",
                 "516—528 年｜左侧保留原图坐标，右侧逐条读文献关系；官署图框用于排版，不表示院落位置", 1040)
    label(root, 40, 125, "① 原图06a：门、寺、路三类参照", 21, font_weight="700")
    label(root, 488, 125, "② 文献关系：每一条看清参照物", 21, font_weight="700")
    wanted = {"geo-yongning-temple-walls", "geo-yongning-pagoda-reference",
              "geo-changhe-palace-gate", "geo-tongtuo-avenue"}
    features = [f for f in atlas["features"] if f["id"] in wanted]
    _, scale, dx, dy = native_frame(root, "r7-palace-native", 40, 151, 408, 430,
                                   (285, 316, 42, 80), features,
                                   {"geo-tongtuo-avenue": "R01", "geo-changhe-palace-gate": "G01"})
    label(root, 58, 181, "北 ↑", 18)
    px = lambda x: dx + x * scale
    py = lambda y: dy + y * scale
    _road(root, "G01", 310, 221, "宫前阊阖门", 17)
    _road(root, "G01", 310, 246, "G01 · 图符", 16)
    el(root, "line", x1=px(314), y1=py(325.36), x2=304, y2=217, stroke="#82917d", stroke_width=1)
    label(root, 58, 345, "永宁寺墙迹", 18, fill=GREEN)
    label(root, 58, 370, "与塔基图符", 16, fill=MUTED)
    el(root, "line", x1=166, y1=350, x2=px(293.7), y2=py(355), stroke="#82917d", stroke_width=1)
    _road(root, "R01", 310, 423, "铜驼残段", 18)
    _road(root, "R01", 310, 449, "R01 · 三段", 16)
    label(root, 310, 544, "南端未知", 17, fill=GOLD)
    el(root, "circle", cx=px(312.1), cy=py(391), r=6, fill="#fffdf7", stroke=GOLD, stroke_width=2)
    lines(root, 58, 520, ["墙迹保留断笔", "图符不是建筑轮廓"], 16, 25, fill=MUTED)

    box(root, 40, 598, 408, 179, fill="#eef1e6")
    label(root, 59, 630, "门南一里、御道西", 22, fill=GREEN, font_weight="700")
    lines(root, 59, 661, ["永宁寺的两个方向均有原文。", "“一里”没有给出量距的具体基点，", "不转换为本图的米数。"], 17, 27)
    _road(root, "T01", 59, 754, "T01 文献御道 ↔ R01 候选对应", 16, fill=GOLD)

    box(root, 480, 151, 680, 626)
    label(root, 502, 186, "明文路侧：只表示东西，不表示正对或等距", 18, fill=GREEN, font_weight="600")
    _relation_row(root, 235, "右卫府", "御道西", "宫前御道")
    _relation_row(root, 290, "左卫府", "御道东", "宫前御道")
    _road(root, "T01", 1008, 323, "查 T01 →", 16)
    el(root, "line", x1=501, y1=340, x2=1137, y2=340, stroke="#d7dccf")
    label(root, 502, 373, "明文南序：以下三行独立，不传递未知的路侧", 18, fill=GREEN, font_weight="600")
    _relation_row(root, 419, "司徒府", "在南侧", "左卫府")
    _relation_row(root, 473, "国子学", "在南侧", "司徒府")
    _relation_row(root, 527, "太尉府", "在南侧", "右卫府")
    el(root, "line", x1=501, y1=548, x2=1137, y2=548, stroke="#d7dccf")
    label(root, 502, 583, "太尉府：寺东是明文，道西是段落解释", 19, fill=INK, font_weight="600")
    _relation_row(root, 632, "太尉府", "在东侧 · 明文", "永宁寺")
    _relation_row(root, 704, "太尉府", "在西侧 · 解释", "宫前御道", True)
    label(root, 502, 751, "实线为直接关系；金色虚线为解释。两者不互换。", 16, fill=MUTED)

    box(root, 40, 803, 545, 133, fill="#f3ecd9", stroke="#dac8a5")
    a = link(root, "finding-PY07")
    label(a, 59, 835, "516 年创寺：时间锚点", 21, fill=GOLD, font_weight="700")
    lines(a, 59, 866, ["创立年不能替代全部建筑的完成年。", "门、路和寺的遗迹宽年代分别保留。", "516—528 是综合研究窗口，非逐年相同快照。"], 17, 26)
    box(root, 605, 803, 555, 133, fill="#eaf1ef", stroke="#c2d6d7")
    a = link(root, "finding-PY08")
    label(a, 624, 835, "夹路支水：只画关系，接口留空", 21, fill=BLUE, font_weight="700")
    lines(a, 624, 866, ["既有郦注校读记夹路分支、寺在水西。", "不把R01路中线画成水沟；不补桥涵与岸线。", "局部水支未单列W号，原始校读可回查。"], 17, 26)
    lines(root, 40, 973, ["原图指针：geographic-evidence.json /features/6、7、8、10；周校卷一0043—0044，范校0341。",
                          "图面限度：无新增坐标；来源图断笔、文献方位与首页建筑外观各守证据层。点道路名查看逐段表。"], 16, 28)
    return root


def _bridge_card(parent, x, title, rid):
    box(parent, x, 151, 360, 335)
    _road(parent, rid, x + 20, 187, title, 22, font_weight="700")
    return el(parent, "g", data_diagram="documentary-bridge-relationship", data_bridge_record=rid)


def jianchun_map(atlas, data):
    root = plate("r7-jianchun", "建春门三桥 · 道路方向、水道解释与527年",
                 "516—528 年｜三桥独立登记；关系图无比例，桥头、古岸与道路交点均不由图上排版补定", 1320)
    label(root, 40, 125, "① 三桥先分清：不是同一条东西直线上的三个测点", 21, font_weight="700")
    first = _bridge_card(root, 40, "建春石桥  B01", "B01")
    lines(first, 60, 230, ["建春门外石桥", "明悬尼寺在桥南", "135年铭归此桥"], 19, 34)
    a = link(first, "finding-JC02")
    box(a, 60, 328, 320, 91, fill="#f3e7d6", stroke="#d3ae83")
    label(a, 77, 358, "527年：大雨受损", 21, fill="#8b512e", font_weight="700")
    label(a, 77, 389, "528年前是否修复：未知", 17, fill="#8b512e")
    label(first, 60, 458, "事件不传递给右侧两桥。", 17, fill=MUTED)

    second = _bridge_card(root, 420, "东石桥  B02", "B02")
    label(second, 440, 221, "明确南北通行 · 280年营造记载", 18, fill=GREEN)
    a = link(second, "segment-T10", "T10")
    el(a, "line", x1=600, y1=246, x2=600, y2=281, stroke=GOLD, stroke_width=6,
       data_diagram="bridge-north-road-direction")
    el(a, "circle", cx=600, cy=246, r=5, fill="#fffdf7", stroke=GOLD, stroke_width=2)
    label(a, 619, 264, "北大道 T10", 16, fill=GREEN)
    label(second, 444, 291, "建阳里（西）", 16)
    label(second, 642, 291, "绥民里（东）", 16)
    a = link(second, "segment-B02", "B02")
    el(a, "line", x1=587, y1=300, x2=587, y2=341, stroke=GREEN, stroke_width=3)
    el(a, "line", x1=613, y1=300, x2=613, y2=341, stroke=GREEN, stroke_width=3)
    for y in (304, 319, 334):
        el(a, "line", x1=588, y1=y, x2=612, y2=y, stroke=GREEN, stroke_width=2)
    label(second, 440, 332, "桥向 ↑↓", 17, fill=GREEN)
    a = link(second, "segment-T22", "T22")
    el(a, "line", x1=600, y1=357, x2=600, y2=391, stroke=GOLD, stroke_width=6)
    el(a, "circle", cx=600, cy=391, r=5, fill="#fffdf7", stroke=GOLD, stroke_width=2)
    label(a, 619, 381, "南道 T22", 16, fill=GREEN)
    lines(second, 440, 427, ["跨桥连续路面、御道路口未测定。", "马市石桥为候选比定。"], 17, 28)

    third = _bridge_card(root, 800, "七里桥  B03", "B03")
    label(third, 820, 230, "崇义里东有桥；桥东一里至郭门", 17)
    _road(third, "B03", 820, 289, "七里桥", 20)
    _arrow(third, 904, 282, 1058, 282)
    label(third, 978, 267, "东一里", 17, fill=GREEN, text_anchor="middle")
    _road(third, "G10", 1066, 283, "三门", 18)
    _road(third, "G10", 1066, 307, "G10", 16)
    lines(third, 820, 350, ["桥名“七里”不从建春门起量。", "旅人桥为候选比定。", "274／282年两说并存，", "不擅分为始建与重修。"], 17, 30)

    label(root, 40, 531, "② 水在路北／路南：遗迹记录与分期解释分别看", 21, font_weight="700")
    box(root, 40, 554, 550, 234, fill="#eef2ec")
    box(root, 610, 554, 550, 234, fill="#f3ede2")
    label(root, 60, 590, "路北宽渠 · 既有调查记录", 21, fill=BLUE, font_weight="700")
    label(root, 630, 590, "路南阳渠 · 黄氏分期复原", 21, fill=GOLD, font_weight="700")
    a = link(root, "water-W06")
    el(a, "line", x1=71, y1=630, x2=552, y2=630, stroke=BLUE, stroke_width=4,
       stroke_dasharray="4 6", data_water_ref="W06", data_diagram="relative-side-only")
    label(a, 82, 621, "北侧渠迹（不是本轮实测线）", 17, fill=BLUE)
    a = link(root, "segment-O07", "O07")
    el(a, "line", x1=71, y1=689, x2=552, y2=689, stroke=GOLD, stroke_width=4,
       data_diagram="relative-side-only")
    label(a, 82, 716, "O07 建春门外调查道路", 18, fill=GREEN)
    label(root, 60, 759, "宽年代遗迹，北魏各段分期仍待原孔位。", 17, fill=MUTED)
    a = link(root, "segment-T09", "T09")
    el(a, "line", x1=641, y1=627, x2=1122, y2=627, stroke=GOLD, stroke_width=4,
       data_diagram="relative-side-only")
    label(a, 652, 618, "T09 建春门外文献御道", 18, fill=GREEN)
    a = link(root, "water-W06")
    el(a, "line", x1=641, y1=688, x2=1122, y2=688, stroke=BLUE, stroke_width=3,
       stroke_dasharray="9 7", data_water_ref="W06", data_diagram="interpretation-not-bank")
    label(a, 652, 718, "南侧假说：解释西晋至北魏的桥渠关系", 17, fill=BLUE)
    label(root, 630, 759, "两框无比例，不合成两条同期实测河岸。", 17, fill=MUTED)

    label(root, 40, 833, "③ 门下暗渠与七里涧：两个仍须保留的分歧", 21, font_weight="700")
    box(root, 40, 856, 360, 319)
    label(root, 60, 890, "门符与局部图不能强配准", 20, font_weight="700")
    fs = [f for f in atlas["features"] if f["id"] == "geo-jianchun-gate"]
    _, scale, dx, dy = native_frame(root, "r7-jianchun-native", 60, 912, 110, 100,
                                   (371, 289, 15, 15), fs)
    label(root, 74, 932, "北 ↑", 15)
    lines(root, 188, 940, ["06a建春门图符", "只有概化位置", "不含实测桥头"], 16, 27)
    a = link(root, "finding-JC07")
    lines(a, 60, 1044, ["门下暗渠属汉晋下层。", "516—528继续通流未证；", "不画通往W06的接线。", "共同控制点：0。"], 17, 30)

    box(root, 420, 856, 740, 193, fill="#edf2ee")
    a = link(root, "finding-JC06")
    label(a, 440, 890, "七里涧 · 两种有署名的读法", 21, fill=BLUE, font_weight="700")
    label(a, 440, 923, "北来支流：黄学超援杨萧杨校读", 18, fill=GREEN, font_weight="600")
    label(a, 440, 950, "在马市桥后接七里涧段；从北来，南入阳渠。", 17)
    label(a, 440, 984, "传本文序：熊会贞按语", 18, fill=GOLD, font_weight="600")
    label(a, 440, 1011, "解释为城北、东侧水的下流异名；池后合流仍属解释。", 17)
    box(root, 420, 1066, 740, 109, fill="#f3ecd9", stroke="#dac8a5")
    a = _road(root, "T26", 440, 1097, "T26 乐里道：句中转向的是水", 20, fill=GOLD, font_weight="700")
    lines(a, 440, 1127, ["“其水……屈而东出阳渠”不提供道路向东拐折的测线。", "未定汇口、桥头和郭门端点均保留未知。"], 17, 27)
    lines(root, 40, 1215, ["来源：周校卷二0099、0106—0107、0111；crossings.json；water-01-collation.json /claims/0—2。",
                           "局部图：钱2018图二重取复核；门符 geographic-evidence.json /features/20。图像层位沿用原审计。",
                           "下一件原件：1993《考古》602—608及完整附图，核实测／推定分界、最后探孔和过渠测线。"], 16, 30)
    return root
