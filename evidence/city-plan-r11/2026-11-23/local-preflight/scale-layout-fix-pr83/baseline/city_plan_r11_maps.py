"""One metric working plane; every sheet is a viewport on identical geometry.

Symbol sizes and label offsets are publication choices. They are kept separate
from feature coordinates; no label adjustment can move a reconstructed object.
"""
import hashlib
import json
import math
from xml.etree import ElementTree as ET

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
BASE = "https://mechgouki.github.io/luoyang-city/luoyang-city-plan.html"
COLORS = {"source": "#315f57", "trace": "#815e92", "scale": "#ad7134", "candidate": "#be8446", "palace": "#608198"}
LAYER_NAMES = {"source": "来源总图骨架", "trace": "局部原图轮廓 · 候选接入", "scale": "有据尺度片 · 位置含假定", "candidate": "文献方位 · 候选点", "palace": "2013宫城刊图 · 对照层"}
W, H = 1920, 1360


def el(parent, tag, **attrs):
    return ET.SubElement(parent, "{" + NS + "}" + tag, {k.replace("_", "-"): str(v) for k, v in attrs.items() if v is not None})


def text(parent, x, y, content, size=18, **attrs):
    n = el(parent, "text", x=x, y=y, font_size=size, **attrs)
    n.text = str(content)
    return n


def points(geometry):
    c = geometry["coordinates"]
    def walk(v):
        if isinstance(v[0], (int, float)):
            yield v
        else:
            for child in v:
                yield from walk(child)
    return list(walk(c))


def bounds(features, pad=0):
    ps = [p for f in features if f.get("geometry") for p in points(f["geometry"])]
    if not ps:
        return None
    xs, ys = zip(*ps)
    return [min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad]


def intersects(feature, box):
    b = bounds([feature])
    return bool(b and b[0] <= box[2] and b[2] >= box[0] and b[1] <= box[3] and b[3] >= box[1])


def frame_box(box, width=1600, height=1000, pad=.04):
    x0, y0, x1, y1 = box
    cx, cy = (x0+x1)/2, (y0+y1)/2
    dx, dy = max(x1-x0, 60)*(1+pad*2), max(y1-y0, 60)*(1+pad*2)
    if dx/dy < width/height:
        dx = dy*width/height
    else:
        dy = dx*height/width
    return [cx-dx/2, cy-dy/2, cx+dx/2, cy+dy/2]


def layer(feature):
    role = feature.get("geometry_role", "")
    if feature.get("toggle_group") == "palace-2013" or feature["id"].startswith("r11-palace2013-"):
        return "palace"
    if role.startswith("published_") or role in {"local_plan_trace", "local_plan_direction_trace"}:
        return "trace"
    if "template" in role:
        return "scale"
    if feature.get("placement_status") == "source_frame_reuse" or feature["id"].startswith("geo-"):
        return "source"
    return "candidate"


def geom_hash(feature):
    return hashlib.sha256(json.dumps(feature["geometry"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def path_data(geometry):
    typ, c = geometry["type"], geometry["coordinates"]
    def line(ring, closed=False):
        return "M" + "L".join(f"{p[0]:.6f},{-p[1]:.6f}" for p in ring) + ("Z" if closed else "")
    if typ == "LineString": return line(c)
    if typ == "MultiLineString": return " ".join(line(r) for r in c)
    if typ == "Polygon": return " ".join(line(r, True) for r in c)
    if typ == "MultiPolygon": return " ".join(line(r, True) for p in c for r in p)
    raise ValueError(typ)


def label_priority(f):
    l = layer(f)
    return (0 if l == "source" and f["geometry"]["type"] == "Point" else 1 if l == "trace" else 2 if l == "scale" else 3,
            len(f.get("label", "")), f["id"])


def labels(root, features, box, width, height, *, all_labels=False, show_palace=False):
    """Place only text around fixed anchors; every moved label has a leader."""
    x0, y0, x1, y1 = box
    unit = (x1-x0)/width
    chosen = [f for f in features if (f.get("default_visible") is not False or show_palace and layer(f)=="palace") and intersects(f, box)]
    chosen.sort(key=label_priority)
    occupied = []
    label_group = el(root, "g", data_annotation_layer="labels", aria_hidden="true")
    for f in chosen:
        l, typ = layer(f), f["geometry"]["type"]
        if typ != "Point" and l == "source":
            continue
        if x1-x0 > 2500 and l in {"trace", "scale"}:
            continue
        b = bounds([f]); ax, ay = (b[0]+b[2])/2, -(b[1]+b[3])/2
        if not (x0 <= ax <= x1 and -y1 <= ay <= -y0):
            continue
        label = f.get("label", f["id"])
        label = label.replace("（来源图标注）", "").replace("〔候选点〕", "")
        if len(label) > 21:
            label = label[:20] + "…"
        fs = 14 if width < 1400 else 17
        tw = sum(fs if ord(c) > 127 else fs*.57 for c in label)
        axp, ayp = (ax-x0)/unit, (ay+y1)/unit
        candidates = [(axp+10, ayp-7), (axp+10, ayp+19), (axp-tw-10, ayp-7),
                      (axp-tw-10, ayp+19), (axp+10, ayp-30), (axp+10, ayp+42),
                      (axp-tw-10, ayp-30), (axp-tw-10, ayp+42)]
        best = None
        for tx, ty in candidates:
            tx = max(8, min(width-tw-8, tx)); ty = max(fs+8, min(height-8, ty))
            rect = (tx-3, ty-fs-2, tx+tw+3, ty+4)
            overlap = sum(max(0, min(rect[2], o[2])-max(rect[0], o[0]))*max(0, min(rect[3], o[3])-max(rect[1], o[1])) for o in occupied)
            score = overlap*100 + abs(tx-axp) + abs(ty-ayp)
            if best is None or score < best[0]: best = score, tx, ty, rect, overlap
        _, tx, ty, rect, overlap = best
        if overlap > 0 and not all_labels:
            continue
        if overlap > fs*tw*.12:
            continue
        occupied.append(rect)
        group = el(label_group, "g", data_label_for=f["id"], data_layer=l)
        wx, wy = x0+tx*unit, -y1+ty*unit
        if abs(ty-ayp) > 22 or tx < axp:
            el(group, "path", d=f"M{ax} {ay}L{wx + min(max(axp-tx,0),tw)*unit} {wy-5*unit}",
               stroke=COLORS[l], stroke_width=.65*unit, fill="none", opacity=.8)
        el(group, "rect", x=wx-3*unit, y=wy-(fs+2)*unit, width=(tw+6)*unit, height=(fs+6)*unit,
           rx=2*unit, fill="#faf9f4", fill_opacity=.94)
        text(group, wx, wy, label, fs*unit, fill=COLORS[l])
    return label_group


def world_svg(data, box, width=1200, height=760, *, identifier="city-plan-map", title="全城统一坐标复原工作平面", href_base="", all_labels=False, show_palace=False):
    x0, y0, x1, y1 = frame_box(box, width, height, 0)
    box = [x0,y0,x1,y1]
    unit = (x1-x0)/width
    root = ET.Element("{"+NS+"}svg", {
        "id": identifier, "class": "plan-world", "viewBox": f"{x0} {-y1} {x1-x0} {y1-y0}",
        "width": str(width), "height": str(height), "role": "img", "aria-label": title,
        "data-coordinate-frame": data["frame"]["id"], "data-bounds": json.dumps(box),
        "data-reference-width": str(width), "data-reference-height": str(height),
        "font-family": "Noto Sans CJK SC, sans-serif", "style": "background:#f8f7f0"})
    el(root,"title").text=title
    el(root,"desc").text="全部形状使用共同来源坐标局部米制；紫色局部图示轮廓与金色候选点包含未验证的全城落位。文字排版不改变几何。"
    el(root,"metadata", data_role="coordinate-contract").text=json.dumps({"frame":data["frame"],"bounds":box,"same_geometry_in_every_view":True},ensure_ascii=False,separators=(",",":"))
    grid = el(root,"g",data_annotation_layer="grid",aria_hidden="true")
    step = 1000 if x1-x0>5000 else 500 if x1-x0>2500 else 200 if x1-x0>1000 else 100 if x1-x0>400 else 20
    for x in range(math.ceil(x0/step)*step, math.floor(x1/step)*step+1, step):
        el(grid,"path",d=f"M{x} {-y1}V{-y0}",fill="none",stroke="#dce2d9",stroke_width=.65*unit)
    for y in range(math.ceil(y0/step)*step, math.floor(y1/step)*step+1, step):
        el(grid,"path",d=f"M{x0} {-y}H{x1}",fill="none",stroke="#dce2d9",stroke_width=.65*unit)
    features = [f for f in data["features"] if f.get("geometry")]
    for f in sorted(features,key=lambda f: (0 if layer(f)=="source" else 1 if layer(f)=="trace" else 2 if layer(f)=="scale" else 3, f["id"])):
        l=layer(f);g=f["geometry"];color=COLORS[l]
        a=el(root,"a",href=href_base+"#feature-"+f["id"],data_feature_id=f["id"],data_layer=l,
             data_geometry_sha256=geom_hash(f),data_geometry_role=f.get("geometry_role"),
             data_placement_status=f.get("placement_status"),aria_label=f.get("label",f["id"]),
             style="display:none" if f.get("default_visible") is False and not (show_palace and l=="palace") else None)
        el(a,"title").text=f.get("label",f["id"])+" · "+LAYER_NAMES[l]
        if g["type"]=="Point":
            x,y=g["coordinates"]
            outer=el(a,"g",transform=f"translate({x:.6f},{-y:.6f})")
            symbol=el(outer,"g",data_screen_symbol="true",transform=f"scale({unit})")
            el(symbol,"circle",r=9,fill="transparent",stroke="none",data_hit_target="true")
            if l=="source":
                el(symbol,"circle",r=4.5,fill="#faf9f4",stroke=color,stroke_width=1.7)
                el(symbol,"circle",r=1.5,fill=color)
            else:
                el(symbol,"path",d="M-4.5 -4.5L4.5 4.5M-4.5 4.5L4.5 -4.5",fill="none",stroke=color,stroke_width=1.5)
        else:
            closed=g["type"] in {"Polygon","MultiPolygon"}
            role=f.get("geometry_role","")
            envelope=role in {"legacy_display_envelope","source_related_range"}
            px=1.9 if l=="source" else 1.7 if l=="trace" else 1.3
            dash="7 4" if l=="scale" else "5 3" if "underground" in f["id"] or envelope else None
            source_style=(f.get('source_rendering') or {}).get('line_style')
            if source_style=='dashed':dash='7 4'
            elif source_style=='dotted':dash='1 4'
            original_style = (f.get('source_legend') or {}).get('outline_line_style', '') if isinstance(f.get('source_legend'), dict) else ''
            if '点划线' in original_style:
                dash='7 3 1 3'
            elif '虚线' in original_style:
                dash='5 3'
            if role=='local_plan_direction_trace':
                dash='3 3';px=1.1
            fill=color if closed and (l in {"trace","scale","palace"} or envelope) else "none"
            p=el(a,"path",d=path_data(g),fill=fill,fill_opacity=.09 if envelope else .15,
                 stroke=color,stroke_width=px*unit,data_stroke_px=px,
                 stroke_dasharray=" ".join(str(float(v)*unit) for v in dash.split()) if dash else None,
                 data_dash_px=dash,stroke_linejoin="round",stroke_linecap="round")
            if envelope: p.set("stroke-dasharray",f"{3*unit} {6*unit}")
    labels(root,features,box,width,height,all_labels=all_labels,show_palace=show_palace)
    return root


def sheet(data, view):
    root=ET.Element("{"+NS+"}svg",{"width":str(W),"height":str(H),"viewBox":f"0 0 {W} {H}",
        "font-family":"Noto Sans CJK SC, sans-serif","data-view-id":view["id"],"data-coordinate-frame":data["frame"]["id"]})
    el(root,"rect",x=0,y=0,width=W,height=H,fill="#faf9f4")
    text(root,65,55,"LUOYANG / 516–528 / R11.1",18,fill="#7b7465",letter_spacing=2)
    text(root,65,107,view["title"],37,fill="#243d37",font_weight=600)
    text(root,65,145,view.get("subtitle","同一母图的取景；片区窗口不是历史边界。"),19,fill="#67726a")
    el(root,"path",d=f"M65 169H{W-65}",stroke="#cdd4ca",stroke_width=1)
    m=world_svg(data,view["bbox"],W-130,965,identifier="map-"+view["id"],title=view["title"],href_base=BASE,all_labels=True,show_palace=view["id"]=="palace2013")
    m.set("x","65");m.set("y","190");root.append(m)
    box=json.loads(m.get("data-bounds"));unit=(box[2]-box[0])/(W-130)
    text(root,W-90,225,"北 ↑",21,fill="#315f57",text_anchor="end")
    scale_m=1000 if box[2]-box[0]>5000 else 500 if box[2]-box[0]>2500 else 200 if box[2]-box[0]>1000 else 100 if box[2]-box[0]>400 else 20
    x,y=100,1120; length=scale_m/unit
    el(root,"rect",x=x-12,y=y-32,width=length+85,height=52,rx=3,fill="#faf9f4",fill_opacity=.94)
    el(root,"path",d=f"M{x} {y-6}V{y}H{x+length}V{y-6}",fill="none",stroke="#354c43",stroke_width=2)
    text(root,x,y-13,f"{scale_m} m",16,fill="#354c43")
    x=65
    for key in COLORS:
        el(root,"path",d=f"M{x} 1204h30",stroke=COLORS[key],stroke_width=3,
           stroke_dasharray="6 4" if key in {"scale","candidate"} else None)
        text(root,x+41,1211,LAYER_NAMES[key],15,fill=COLORS[key]);x += 358
    text(root,65,1254,"共同工作坐标：来源图西安1980局部米制。候选接入不等于考古实测配准；点号不表示建筑大小。",19,fill="#59675e")
    text(root,65,1285,"所有片区保持相同几何。未有边界依据的街坊、院落与建筑，保留为候选点或未定位名录，不补封闭轮廓。",18,fill="#59675e")
    text(root,65,1321,"回查完整图层、对象覆盖、变换与原文：mechgouki.github.io/luoyang-city/luoyang-city-plan.html",16,fill="#7b7465")
    return ET.tostring(root,encoding="unicode")


def method_sheet(data):
    root=ET.Element("{"+NS+"}svg",{"width":str(W),"height":str(H),"viewBox":f"0 0 {W} {H}","font-family":"Noto Sans CJK SC, sans-serif"})
    el(root,"rect",x=0,y=0,width=W,height=H,fill="#faf9f4")
    text(root,75,90,"怎样读这张统一坐标平面",39,fill="#243d37")
    sections=[
        ("一张母图，五种证据表达",[
            "绿色：沿用2012年来源总图的遗存线、符号和范围；来源图自身已有概化。",
            "紫色：从带比例尺的局部图逐点提取，再按明确假定接入母图。轮廓来源与落位可靠性分开记录。",
            "棕色虚线：依据报告尺寸生成的尺度片；不代表已取得完整发掘轮廓。",
            "金色叉号：文献方位的候选位置。无界址依据时，不用矩形假装坊墙、院墙或房基。",
            "蓝灰：2013宫城刊图独立对照层，默认关闭；隔壁、版筑范围和调查签不等于详细建筑足迹。"]),
        ("共同坐标可以复算，历史位置仍分层判断",[
            "母图采用西安1980来源图的局部等距投影，单位为米；没有转换成WGS84。",
            "阊阖门、永宁寺与2013宫城刊图分别保留原比例尺、北向、原点与接入矩阵。",
            "旧文献图只提供显式候选布局起点；同名对应点的拟合残差不是遗址定位误差。",
            "片区图仅裁取同一套坐标，不再为每个窗口另排对象。地图标签可移，实体坐标不随标签移动。"]),
        ("保留可检验的差异",[
            "宫城中轴的来源图距离与分段量距未闭合，不拉伸原图、也不自动补连门间道路。",
            "永宁寺新刊载平面与旧总图残墙分别保留；不强拟合不同来源的寺院长宽。",
            "年代不合516–528的建筑状态另行登记。后建塔、未证房屋和泛化宫院模板不进入主层。",
            "全目录339项包含建筑、道路、水体、里坊、群组及事件，不能读成339座建筑的考古平面。"]),
        ("回查与复用",[
            "网页可选片区、切换证据层、查名称并打开每个构件的依据；未定位对象仍可检索。",
            "下载包含全城与同坐标片区SVG、矢量PDF、对象覆盖、构件坐标与约束CSV。",
            "plan.json保留工作坐标、图源指针、尺度与落位限制；它不是WGS84 GeoJSON。",
            "历史原图未作为本项目新作转载。证据表标明出版来源、页码图号与复核记录。"]),
    ]
    y=158
    for title,rows in sections:
        text(root,75,y,title,27,fill="#315f57",font_weight=600);y+=49
        for line in rows:
            text(root,94,y,line,23,fill="#4c5e54");y+=43
        y+=39
    text(root,75,1313,"R11.1 · 全城统一坐标复原工作平面  |  source_commit: "+data["source_commit"],16,fill="#7b7465")
    return ET.tostring(root,encoding="unicode")
