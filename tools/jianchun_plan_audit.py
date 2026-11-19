"""Read Jianchun's published local plan without registering it to the city map."""
import html
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from dual_cartography import load, sha

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/prosperity-v4/backbone-469"
AUDIT = SOURCE / "jianchun-plan-audit.json"
GEO = ROOT / "research/prosperity-v1/geographic-evidence.json"
NS = "http://www.w3.org/2000/svg"
PAPER, INK, MUTED = "#faf8f1", "#263c34", "#60716a"
FIGURES = ("jianchun-source-context.svg", "jianchun-structure-reading.svg")
ARTICLE = "https://www.sohu.com/a/298263205_199807"
PREFACE = "https://www.wenwu.com/newsinfo/3210484.html"


def tag(parent, name, **attrs):
    return ET.SubElement(parent, "{" + NS + "}" + name, {
        key.rstrip("_").replace("_", "-"): str(value)
        for key, value in attrs.items() if value is not None
    })


def text(parent, x, y, value, size=22, fill=INK, **attrs):
    element = tag(parent, "text", x=x, y=y, font_size=size, fill=fill, **attrs)
    element.text = value
    return element


def plate(identifier, title, subtitle):
    svg = ET.Element("{" + NS + "}svg", {
        "id": identifier, "viewBox": "0 0 640 760", "width": "640", "height": "760",
        "role": "img", "aria-labelledby": identifier + "-title " + identifier + "-desc",
        "lang": "zh-CN",
    })
    tag(svg, "title", id=identifier + "-title").text = title
    tag(svg, "desc", id=identifier + "-desc").text = subtitle
    tag(svg, "style").text = "text{font-family:'Noto Sans CJK SC','Microsoft YaHei',sans-serif}"
    tag(svg, "rect", width=640, height=760, fill=PAPER)
    text(svg, 30, 42, title, 29, font_weight="700")
    text(svg, 30, 79, subtitle, 19, MUTED)
    return svg


def context_figure():
    geo = load(GEO)
    features = {item["id"]: item for item in geo["features"]}
    gate = features["geo-jianchun-gate"]
    roads = load(ROOT / "research/prosperity-v4/network-462/roads.json")
    road_id = next(item["p1_feature_id"] for item in roads["routes"] if item["code"] == "Lh-3")
    svg = plate("jianchun-source-context", "01 / 全城图中的建春门", "管理规划图06a局部 · 原坐标与分段")
    tag(svg, "metadata").text = json.dumps({
        "source_frame": "06a", "native_units": "PDF point", "source_sha256": sha(GEO),
        "source_feature_ids": ["geo-inner-wall-aboveground", "geo-inner-wall-underground", road_id, gate["id"]],
        "new_geographic_geometry": False, "gate_symbol_is_ground_control": False,
        "crop_viewbox": [365, 284, 30, 25], "display_crop_is_not_archaeological_boundary": True,
    }, ensure_ascii=False)
    tag(svg, "rect", x=30, y=109, width=580, height=488, rx=10, fill="#edf0e6", stroke="#d8dcd0")
    native = tag(svg, "svg", x=32, y=111, width=576, height=484,
                 viewBox="365 284 30 25", overflow="hidden", data_native_units="PDF point")
    for feature_id, color, width, dash in [
        ("geo-inner-wall-aboveground", "#a29b81", .48, None),
        ("geo-inner-wall-underground", "#a29b81", .28, ".5 .3"),
        (road_id, "#a36042", .25, None),
    ]:
        feature = features[feature_id]
        geometry = feature["source_pdf_geometry"]
        parts = geometry["coordinates"] if geometry["type"] == "MultiLineString" else [geometry["coordinates"]]
        for number, points in enumerate(parts, 1):
            path = " ".join(("M" if i == 0 else "L") + f"{p[0]} {p[1]}" for i, p in enumerate(points))
            tag(native, "path", d=path, fill="none", stroke=color, stroke_width=width,
                stroke_dasharray=dash, data_source_feature_id=feature_id, data_part=number)
    x, y = gate["source_pdf_geometry"]["coordinates"]
    tag(native, "circle", cx=x, cy=y, r=.42, fill="#faf8f1", stroke="#34685e", stroke_width=.18,
        data_source_feature_id=gate["id"], data_semantics="source-symbol-center-not-ground-control")
    text(native, x+1.2, y-.6, "建春门", 1.25, font_weight="700")
    text(native, x+1.2, y+1.1, "Cnm-8 图符中心", .85, MUTED)
    text(native, 366, 292.2, "Lh-3 道路图示残段", .95, "#a36042")
    text(native, 380, 289.5, "东墙遗存", 1.05, "#756e57")
    text(svg, 30, 641, "保留墙线缺口，不把缺口两端当成门宽。", 23)
    text(svg, 30, 681, "圆圈为阅读符号，大小不代表实际门基。", 22, MUTED)
    text(svg, 30, 723, "来源：UNESCO 1442.pdf 第3457页 · 图06a", 18, MUTED)
    return svg


def structure_figure():
    svg = plate("jianchun-structure-reading", "02 / 局部遗迹怎样阅读", "据钱2018图二与正文 · 关系示意，不按比例")
    tag(svg, "metadata").text = json.dumps({
        "source": ARTICLE, "figure": 2, "role": "qualitative-structural-reading-not-traced-plan",
        "metric_geometry": False, "geographic_transform": None,
        "central_passage_measurement": "reported surviving width, not complete original clear width",
        "drain_date": "Han-Jin, operation in 516-528 unverified",
        "north": "source drawing label, no numeric azimuth or datum",
    }, ensure_ascii=False)
    defs = tag(svg, "defs")
    pattern = tag(defs, "pattern", id="jianchun-silt", width=13, height=13, patternUnits="userSpaceOnUse")
    tag(pattern, "path", d="M0 13 L13 0", stroke="#d8ccb2", stroke_width=2)
    # Display rows express the order of surviving structures, not measured edges.
    tag(svg, "line", x1=567, y1=145, x2=567, y2=106, stroke=MUTED, stroke_width=2)
    tag(svg, "path", d="M562 114 L567 105 L572 114", fill="none", stroke=MUTED, stroke_width=2)
    text(svg, 428, 128, "北（原图标注）", 18, MUTED)
    rows = [
        (150, 48, "北侧墩台", "#d8d1ba"),
        (212, 76, "北门道 · 报告宽6米", "#eaf0e6"),
        (303, 39, "隔墙", "#d8d1ba"),
        (357, 104, "中央区域 · 图标淤土", "url(#jianchun-silt)"),
        (476, 39, "隔墙", "#d8d1ba"),
        (530, 70, "南门道 · 报告宽6米", "#eaf0e6"),
        (615, 48, "南侧墩台", "#d8d1ba"),
    ]
    for y, height, label, color in rows:
        tag(svg, "rect", x=50, y=y, width=540, height=height, rx=7, fill=color,
            stroke="#b8bea8", stroke_dasharray="5 4", data_geometry="display-only-not-measured")
        text(svg, 320, y+(34 if height < 60 else 32), label, 23, text_anchor="middle")
    text(svg, 320, 270, "其下排水遗迹：汉晋层位", 18, "#427b87", text_anchor="middle")
    text(svg, 320, 428, "8米为残宽；完整净宽尚未核实", 19, MUTED, text_anchor="middle")
    text(svg, 30, 707, "图面共现 ≠ 盛时同期使用；不接入古水网。", 22, MUTED)
    text(svg, 30, 741, "框与间距仅为排版；无建筑足迹、柱网或屋高推补。", 18, MUTED)
    return svg


def build_figures(destination):
    destination = Path(destination)
    result = []
    for name, drawing in zip(FIGURES, (context_figure(), structure_figure())):
        ET.indent(drawing)
        path = destination / name
        ET.ElementTree(drawing).write(path, encoding="utf-8", xml_declaration=True)
        result.append(path)
    return result


def section_html():
    # The independent evidence JSON is shipped verbatim; source-plan images remain link-only.
    data = load(AUDIT)
    status = data["read_status"]
    if status["geographic_transform"] is not None or status["accepted_control_pairs"]:
        raise ValueError("A new geographic transform requires independent control review")
    for source in data["frozen_inputs"]:
        if sha(ROOT / source["path"]) != source["sha256"]:
            raise ValueError("Jianchun source changed: " + source["path"])
    return f'''<section class="jianchun-audit" id="jianchun-plan-audit" aria-labelledby="jianchun-audit-heading">
      <p class="eyebrow">本次补充 / 从城市位置读到门内遗迹</p>
      <h4 id="jianchun-audit-heading">建春门平面：形制已能读，精确落位还缺什么？</h4>
      <p>钱国祥2018年论文图二的公开重刊图现已核读。图上有北向与0—3米图尺；它显示局部遗迹，06a提供城市位置参照，两图分别保留自己的图框。</p>
      <div class="jianchun-status"><span>重刊平面图：已目读</span><span>1988原刊整页：待得</span><span>可复认共同控制：0组</span></div>
      <div class="jianchun-figures">
        <figure><img src="./backbone-469/{FIGURES[0]}" width="640" height="760" loading="lazy" alt="06a原坐标局部：建春门图符、原有东墙分段与Lh-3道路残线。"/><figcaption>城市位置参照。墙线断点未获证实对应门基角点。</figcaption></figure>
        <figure><img src="./backbone-469/{FIGURES[1]}" width="640" height="760" loading="lazy" alt="不按比例的局部结构关系：北南墩台、两侧门道、隔墙、中部淤土及北门道下汉晋排水遗迹。"/><figcaption>结构关系示意。框形与间距均为排版，不表示原迹轮廓。</figcaption></figure>
      </div>
      <p class="source-line">图二原图仅链接核验，未在本站转载。<a href="{ARTICLE}" target="_blank" rel="noopener">打开考古所发布的论文与图二 ↗</a> · <a href="https://whc.unesco.org/uploads/nominations/1442.pdf#page=3457" target="_blank" rel="noopener">打开06a原图 ↗</a></p>
      <div class="jianchun-fact-grid">
        <article><h5>尺度按残存状态分别读</h5><p>正文记门址南北30米、东西12.5米；中门道<strong>残宽8米</strong>，南北两道各6米，隔墙宽4—5米。这些是报告转述值，没有进行新增量测。</p><p>图框被截断的边缘不能当作门基轮廓；上述尺寸也不拼成一个完整规则矩形。</p></article>
        <article><h5>实存、推测与年代分开</h5><p>北门道南侧存6个排叉柱础坑，文中推测应有8个；不能把推测数全部画为出土柱础。</p><p>北门道下沟槽归于汉晋层位；其516—528年的使用状态仍待证，不将它接上盛时水道。</p></article>
      </div>
      <details class="jianchun-controls"><summary>为什么暂不叠到全城地图？查看5类对应检查</summary>
        <div class="table-scroll"><table><thead><tr><th>候选对应</th><th>现有证据</th><th>当前结论</th></tr></thead><tbody>
          <tr><th>同名门址</th><td>两图都指建春门；06a仅有概略图符中心</td><td>身份可联读，未建立同一测量点</td></tr>
          <tr><th>墩台或门基角</th><td>局部图有残迹，06a不提供对应角点</td><td>不能组成控制点对</td></tr>
          <tr><th>城墙分段端点</th><td>06a端点与局部图的残边、图框截点含义不同</td><td>不能机械对应</td></tr>
          <tr><th>道路与排水口</th><td>全城道路线与门内路土、沟槽缺联测关系</td><td>不能推算路口或渠口</td></tr>
          <tr><th>门外桥头</th><td>本次可读局部图未提供桥位或桥头</td><td>第一石桥、东石桥继续分开保留相对关系</td></tr>
        </tbody></table></div>
        <p>原图的北箭头没有说明方位角或基准；0—3米图尺用于读局部图，不能补出全城位置。当前判断仅针对已读图版，不声称原发掘测绘没有控制资料。</p>
      </details>
      <details class="jianchun-dates"><summary>资料中的发掘年份存在异记</summary><p>钱国祥2018正文记1986年；段鹏琦公开自序记1985年10—12月。本版同时保留，未自行合并为1985—1986年。后者目录中的104是文集重印起始页，并非1988原刊页码。<a href="{PREFACE}" target="_blank" rel="noopener">核对文物出版社公开自序与目录 ↗</a></p></details>
      <p class="jianchun-next"><strong>下一定位依据：</strong>取得能标明门基角点或测量网与城墙、门外大道关系的原位置图或联测数据，再核对同一物理点及坐标基准。两座石桥的位置不会从门内尺寸外推。</p>
    </section>'''
