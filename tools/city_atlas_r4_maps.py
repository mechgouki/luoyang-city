"""Vector plates for the accepted 06a frame and the independent documentary canvas."""
import json
from xml.etree import ElementTree as ET

from city_atlas_r4_data import index

PAGE = "prosperity-city-atlas.html"
LIVE = "https://mechgouki.github.io/luoyang-city/" + PAGE
NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
INK, GREEN, GOLD, PALE = "#243e35", "#246252", "#a27339", "#f5f3eb"
POINT_LABELS = {
    "geo-jinyong-bing-reference":"金墉丙城", "geo-yongning-pagoda-reference":"永宁塔基",
    "geo-changhe-palace-gate":"宫城阊阖门", "geo-taiji-hall-reference":"太极殿",
    "geo-qianqiu-gate":"千秋门", "geo-yunlong-gate":"云龙门", "geo-jianchun-gate":"建春门",
    "geo-daxia-gate":"大夏门", "geo-guangmo-gate":"广莫门", "geo-xiyang-gate":"西阳门",
    "geo-dongyang-gate":"东阳门", "geo-qingyang-gate":"青阳门", "geo-ximing-gate":"西明门",
}


def element(parent, tag, **attrs):
    return ET.SubElement(parent, "{"+NS+"}"+tag, {k.replace("_","-"):str(v) for k,v in attrs.items()})


def label(parent, x, y, message, size=16, **attrs):
    node = element(parent,"text",x=x,y=y,font_family="Noto Sans CJK SC, sans-serif",font_size=size,**attrs)
    node.text = message
    return node


def plate(title, desc, height):
    root = ET.Element("{"+NS+"}svg", {"viewBox":f"0 0 980 {height}","width":"980","height":str(height),
                                    "role":"img","aria-label":title,"lang":"zh-CN"})
    element(root,"title").text = title
    element(root,"desc").text = desc
    element(root,"rect",width=980,height=height,fill=PALE)
    label(root,34,45,title,28,fill=INK,font_weight="600")
    label(root,34,75,desc,15,fill="#4f6155")
    return root


def geometry(parent, feature, scale):
    fid = feature["id"]
    shape = feature["source_pdf_geometry"]
    kind, coords = shape["type"],shape["coordinates"]
    is_point = kind=="Point"
    if is_point:
        element(parent,"circle",cx=coords[0],cy=coords[1],r=4/scale,fill="#fffefa",
                stroke=GREEN,stroke_width=2.1/scale,data_native_geometry=fid)
        return
    modern = feature["layer"]=="modern_geographic_reference"
    road = feature["source_feature_code"].startswith(("Lh-","Lz-"))
    outer = feature["layer"]=="regional_reconstruction_range"
    candidate = feature["layer"]=="layout_envelope"
    ink = "none" if candidate else "#568599" if modern else GOLD if road else "#83917a" if outer else GREEN
    dash = (6,5) if outer or modern else (3,3) if "underground" in fid or fid in (
        "geo-palace-walls","geo-jinyong-bing-wall","geo-yongning-temple-walls") else None
    for line in ([coords] if kind=="LineString" else coords):
        path = " ".join(("M" if i==0 else "L")+f"{x} {y}" for i,(x,y) in enumerate(line))
        attrs = {"d":path+(" Z" if candidate else ""), "fill":"#dcdfbf" if candidate else "none",
                 "stroke":ink,"stroke_width":(1.5 if road or outer else 2.2)/scale, "data_native_geometry":fid}
        if dash:
            attrs["stroke_dasharray"] = " ".join(str(i/scale) for i in dash)
        element(parent,"path",**attrs)


def source_plate(data, core=False, target=LIVE):
    title = "内城、宫城与道路残段" if core else "盛时洛阳城市分布总图"
    root = plate(title,"图06a原生图框  ·  2012年保护管理资料  ·  各遗存的时段见对应图档",706)
    left,top,w,h = 30,98,630,522
    x,y,sw,sh = (249,223,164,181) if core else (93,134,478,448)
    scale = min(w/sw,h/sh)
    element(root,"rect",x=left,y=top,width=w,height=h,fill="#fdfcf7",stroke="#c9cebf")
    defs = element(root,"defs")
    clipping = element(defs,"clipPath",id=("crop-core" if core else "crop-city"))
    element(clipping,"rect",x=left+1,y=top+1,width=w-2,height=h-2)
    frame = element(root,"g",clip_path=f"url(#{clipping.get('id')})")
    dx,dy = left+(w-sw*scale)/2-x*scale,top+(h-sh*scale)/2-y*scale
    native = element(frame,"g",transform=f"translate({dx} {dy}) scale({scale})",data_frame="06a-pdf")
    fs = sorted(data["features"],key=lambda f:(0 if f["layer"]=="layout_envelope" else 2 if f["source_pdf_geometry"]["type"]=="Point" else 1))
    for f in fs:
        fid = f["id"]
        modern = fid.startswith("geo-modern-")
        group = element(native,"a",href=target+"#feature-"+fid,data_feature=fid,data_layer=(
            "modern" if modern else "candidate" if f["layer"]=="layout_envelope" else "source"))
        if modern:
            group.set("display","none")
        element(group,"title").text = f["label"]+" · "+f["source_historical_period"]
        geometry(group,f,scale)
        if fid in POINT_LABELS and core:
            px,py = f["source_pdf_geometry"]["coordinates"]
            # Small numbers lead to the permanent source key on the right.
            label(group,px+5/scale,py-5/scale,str(list(POINT_LABELS).index(fid)+1),12/scale,fill=INK)
    if not core:
        cx,cy,cw,ch = 249*scale+dx,223*scale+dy,164*scale,181*scale
        element(frame,"rect",x=cx,y=cy,width=cw,height=ch,fill="none",stroke="#927b59",stroke_width=1.2,stroke_dasharray="3 4")
        label(frame,cx+cw+7,cy+13,"内城详图",14,fill=INK)
    label(root,44,123,"北 ↑",15,fill=INK)
    label(root,688,128,"内城遗址索引" if core else "图例与定位依据",20,fill=INK,font_weight="600")
    if core:
        for i,(fid,title) in enumerate(POINT_LABELS.items(),1):
            a=element(root,"a",href=target+"#feature-"+fid)
            label(a,690,155+(i-1)*30,f"{i:02}   {title}",16,fill=GREEN)
        label(root,688,577,"圆点表示原图符号中心。",14,fill=INK)
    else:
        for i,(symbol,caption,sub,color) in enumerate([
                ("━", "原图遗存线", "城墙按原段保留开口",GREEN),("━","道路原图残段","八条内城路迹分别读取",GOLD),
                ("┄","外郭相关遗存范围","原图所示范围的概括","#718068"),("■","宫城候选范围","北缘只参与填色","#adb786"),
                ("●","遗址代表点","门址、塔基等概化图符",GREEN),("○","近现代地理参照","洛水、邙山可单独打开","#568599")]):
            yy=170+i*60
            label(root,690,yy,symbol,24,fill=color);label(root,727,yy,caption,17,fill=INK)
            label(root,727,yy+22,sub,13,fill="#546358")
        label(root,688,552,"相对关系另见文献图。",15,fill=INK)
        label(root,688,577,"未定位对象可在索引查阅。",15,fill=INK)
    label(root,34,653,"来源坐标系为西安1980（EPSG:4610）。图形保留原PDF点坐标；图上距离须依所选来源与尺度解读。",15,fill=INK)
    label(root,34,681,"研究时层  516—528 年河阴事件前     ·     原图来源与分期可点选查询",14,fill="#58685c")
    return root


def relationship_plate(data,target=LIVE):
    root=plate("十一片区的文献关系","各行独立读图。左右排列便于对读，关系词记录方向、区间或事件先后。",830)
    es=index(data["entities"])
    for i,r in enumerate(data["regions"][:-1]):
        start=99+i*60
        element(root,"rect",x=27,y=start,width=926,height=55,fill="#fcfbf5" if i%2==0 else "#eeefe4")
        label(root,39,start+22,r["region"]+"   "+r["label"],14,fill=INK)
        for x,key in ((252,"left"),(670,"right")):
            a=element(root,"a",href=target+"#entity-"+r[key],data_entity=r[key])
            label(a,x,start+23,es[r[key]]["source_name"][:16],17,fill=GREEN,font_weight="600")
        a=element(root,"a",href=target+"#reading-"+r["evidence"],data_reading=r["evidence"])
        label(a,443,start+23,r["relation"],15,fill="#81572d")
        label(root,251,start+46,r["limit"],13,fill="#44594f")
    label(root,34,798,"选择对象可读其时期与来源；选择关系词可回到对应校读。各行的端点没有地理坐标。",15,fill=INK)
    return root


def literary_plate(source,target=LIVE):
    root=ET.fromstring(source)
    root.set("data-frame","documentary")
    for parent in root.iter():
        for i,node in enumerate(list(parent)):
            tid=node.get("data-target-id")
            if not tid or parent.tag=="{"+NS+"}a":
                continue
            members=json.loads(node.get("data-members"))
            target_id="entity-"+members[0] if len(members)==1 else "group-"+tid
            link=ET.Element("{"+NS+"}a",{"href":target+"#"+target_id})
            parent.remove(node)
            link.append(node)
            parent.insert(i,link)
    return root


def markup(root):
    return ET.tostring(root,encoding="unicode")
