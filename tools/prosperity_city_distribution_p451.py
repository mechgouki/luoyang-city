#!/usr/bin/env python3
"""P4.5.1: evidence-ranked city distribution grounded in previously published map shapes.

Reuse existing P1 map SVG marker positions *exactly*. Link only source feature IDs
to independently reported structure types and dimension cards. Never register
additional historical coordinates or infer building footprints/upper-storey heights.
"""
from pathlib import Path
import csv
import hashlib
import html
import io
import json
import shutil
import xml.etree.ElementTree as ET
import zipfile

from dual_cartography import NS, node, text, rect, path, svg, write_svg, C
from north_b4 import render_atlas

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
OUT=SITE/"prosperity-city-distribution"
SRC=ROOT/"research/prosperity-v4/city-distribution-p451.json"
SOURCE_GEO=ROOT/"research/prosperity-v1/geographic-evidence.json"
SOURCE_DIM=ROOT/"research/prosperity-v1/building-dimensions.json"
SOURCE_TYPES=ROOT/"research/prosperity-v4/architecture-types-p44.json"
P43=ROOT/"research/prosperity-v4/palace-boundary-variants-p43.json"
VERSION="prosperity-city-distribution-p451"
COLORS={"C01":"#ad7543","C02":"#366b79","C03":"#577a4e","C04":"#825f96"}
MUTABLE={"index.html","v3.0-dual.html","release.json","build-info.json"}
NAVMARK='<p class="home-research-footnote">'

def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,d):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(d,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def h(s):
    return html.escape(str(s),quote=True)
def verify_input(data,geo,dim,typ,prev,info):
    assert data["version"]==VERSION
    assert geo["crs"]=="EPSG:4610" or geo["crs"].get("id")=="EPSG:4610"
    features=geo["features"]
    assert len(features)==data["source_map_audit"]["total_features"]==30
    assert sum(bool(f.get("entity_id")) for f in features)==13
    assert len(data["anchored_buildings"])==4
    assert len(data["unplaced_p44_types"])==4
    assert len(typ["types"])==6
    assert prev["version"]=="prosperity-palace-boundaries-p43"
    assert info["homepage_approved_v9"]["hero_revision"]=="panorama-approved-v9"
    assert read(SITE/"homepage/approval-v9.json")["hero"]["status"]=="approved"
    assert info["prosperity_architecture"]["types"]==6
    lookup={f["id"]:f for f in features}
    assert len(lookup)==len(features)
    declared_types={t["id"]:t for t in typ["types"]}
    unplaced={x["type_id"] for x in data["unplaced_p44_types"]}
    anchored={x["type_id"] for x in data["anchored_buildings"] if x["type_id"]}
    assert unplaced|anchored==set(declared_types) and not(unplaced&anchored)
    measures={m["item_id"]:m for m in dim["massing_items"]}
    assert {r["id"] for r in data["anchored_buildings"]}==set(COLORS)
    for item in data["anchored_buildings"]:
        source=lookup[item["feature_id"]]
        assert source["geometry"]["type"]=="Point" and source["layer"]=="site_remains"
        assert item["entity_id"]==source.get("entity_id")
        assert not item["site_registered_polygon_allowed"]
        assert item["measured_elevation_m"] is None and not item["roof_style_verified"]
        ref=item.get("dimension_item_id")
        if ref is not None:
            model=measures[ref]["plan_dimensions_m"]
            dims=item["reported_footprint_m"]
            if ref=="M02": expected=(model["east_west"],model["north_south"])
            elif ref=="M03": expected=(model["east_west_approx"],model["north_south_approx"])
            elif ref=="M05": expected=(model["surviving_square_side_approx"],)*2
            else: raise AssertionError(f"Unrecognized dimension source {ref}")
            assert (dims["east_west"],dims["north_south"])==expected
        elif item["type_id"]=="inner_city_gate":
            from_p44=declared_types["inner_city_gate"]["observed_evidence"]
            assert item["reported_footprint_m"]=={
                "east_west":from_p44["platform_ew_m"],
                "north_south":from_p44["platform_ns_m"]}
        else:raise AssertionError("Dimensions need published origin")
    enclosure=data["enclosure_context"][0]
    assert enclosure["feature_id"]=="geo-yongning-temple-walls"
    assert lookup[enclosure["feature_id"]]["geometry"]["type"]=="MultiLineString"
    assert not enclosure["closed_polygon_allowed"]
    assert enclosure["reported_enclosure_m"]=={
        "east_west":measures["M04"]["plan_dimensions_m"]["east_west"],
        "north_south":measures["M04"]["plan_dimensions_m"]["north_south"]}
    assert data["source_map_audit"]["newly_geolocated_historical_buildings"]==0
    assert data["source_map_audit"]["independently_registered_ancient_gcp_count"]==0
    return lookup

def append_overlays(existing,data,lookup):
    root=ET.parse(existing).getroot()
    assert root.tag==f"{{{NS}}}svg"
    assert root.get("viewBox")=="0 0 1800 1440"
    icons=node(root,"g",id="p451-evidence-anchors",data_geometry_role="source_map_symbol_centers_only")
    pixel={}
    for item in data["anchored_buildings"]:
        fid=item["feature_id"]
        groups=[x for x in root.iter() if x.get("data-feature-id")==fid]
        assert len(groups)==1,(fid,len(groups))
        dots=[c for c in groups[0].iter() if c.tag==f"{{{NS}}}circle" and c.get("r")=="8"]
        assert len(dots)==1,(fid,len(dots))
        cx,cy=float(dots[0].get("cx")),float(dots[0].get("cy"))
        pixel[item["id"]]=[round(cx,2),round(cy,2)]
        g=node(icons,"g",data_binding_id=item["id"],data_feature_id=fid,
               data_selected="false",aria_pressed="false",role="button",tabindex="0")
        g.set("class","source-binding")
        node(g,"title").text=(item["id"]+" "+item["name"]+
                             "；仅沿用来源图的概略符号中心。点击查看建筑类型和尺度限制。")
        halo=node(g,"circle",cx=cx,cy=cy,r=26,fill="#ffffff",
                  stroke=COLORS[item["id"]],stroke_width=4)
        halo.set("class","spot")
        node(g,"circle",cx=cx,cy=cy,r=18,fill=COLORS[item["id"]],stroke="#fff",stroke_width=2)
        text(g,cx,cy+7,item["id"][-2:],19,"#ffffff","middle",700)
    node(root,"title").text="盛时洛阳 P4.5.1 · 原来源图 30 项几何上的四处建筑类型与尺度锚点（非实测建筑边界）"
    return root,pixel

def heading(r,kicker,title,sub,width=1800):
    text(r,64,55,kicker,21,"#607e6a",weight=700)
    text(r,64,113,title,39,C["ink"],weight=700)
    text(r,64,153,sub,20,C["muted"])
    path(r,f"M64 173H{width-64}","#d2dcd2",2)

def scale_plate(data):
    root=svg(1800,1280,"盛时洛阳四种建筑的同米尺平面尺度；与地理参考点不共测量坐标")
    heading(root,"P4.5.1 / SOURCE DIMENSIONS","已报告的局部尺度，不是全城定位的真实建筑轮廓",
            "四个尺寸片按统一 3.2 px/m 绘制；框的中心仅为页面排版，不共享古址原点或宫墙控制。")
    centers=[(485,425),(1335,425),(485,905),(1335,905)]
    scale=3.2
    for item,(cx,cy) in zip(data["anchored_buildings"],centers):
        x0,y0=cx-406,cy-193
        rect(root,x0,y0,812,395,"#ffffff","#d6dfd7",2,12)
        text(root,x0+32,y0+49,item["id"]+"  "+item["name"],28,COLORS[item["id"]],weight=700)
        dims=item["reported_footprint_m"]
        ew=float(dims["east_west"])
        ns=float(dims["north_south"])
        # These are source-published bounding size reports in a separate
        # comparison plate. They are NOT registered site polygons.
        width=ew*scale
        height=ns*scale
        rect_el=rect(root,cx-width/2,cy-height/2+10,width,height,
                     "#e4ede7",COLORS[item["id"]],3,0)
        rect_el.set("data-binding-id",item["id"])
        rect_el.set("data-reported-ew-m",str(ew))
        rect_el.set("data-reported-ns-m",str(ns))
        rect_el.set("data-kind","unplaced_dimension_reference_only")
        label=f'{ew:g} × {ns:g}m'
        if item["dimensions_approximate"]:label="约 "+label
        text(root,cx,cy+152,label,23,COLORS[item["id"]],"middle",700)
        text(root,cx,cy+185,("遗存塔基，不是塔身" if item["id"]=="C04"
                else "门址尺度，非门楼外形" if item["id"] in ("C01","C02")
                else "主殿遗址参考尺度"),17,C["muted"],"middle")
    path(root,"M106 1199h320",C["ink"],5)
    for xx in (106,426):path(root,f"M{xx} 1189v20",C["ink"],4)
    text(root,266,1181,"100m / 图中统一比例",18,C["muted"],"middle")
    text(root,65,1250,"比例只用于发表尺寸的平面比较；不知道实际建筑高度、屋面形制、古地面以及完整院墙测线。",20,C["muted"])
    return root

def tiers_plate(data):
    root=svg(1800,1360,"盛时洛阳 P4.5.1 来源位置与未定位建筑类型分层目录")
    heading(root,"P4.5.1 / PROVENANCE GRADES","已对应位置 ≠ 完整建筑足迹；已知类型 ≠ 可独立定位",
            "左侧：四个来源图已有代表点；右侧：四种只有局部证据、不强行落点的宫门类型。")
    for idx,item in enumerate(data["anchored_buildings"]):
        y=224+idx*210
        rect(root,70,y,800,185,"#ffffff","#d3dfd5",2,9)
        rect(root,92,y+20,12,52,COLORS[item["id"]],COLORS[item["id"]],1,2)
        text(root,120,y+47,item["id"]+"  "+item["name"],27,COLORS[item["id"]],weight=700)
        text(root,120,y+91,"来源图标识："+item["feature_id"],19,C["ink"])
        text(root,120,y+129,"尺度："+item["dimension_source"],18,C["muted"])
        text(root,120,y+159,"没有古高或已注册真实台基多边形",18,"#a2774e")
    for idx,item in enumerate(data["unplaced_p44_types"]):
        y=224+idx*210
        rect(root,929,y,800,185,"#ffffff","#dacfc2",2,9)
        rect(root,950,y+20,12,52,"#a68a66","#a68a66",1,2)
        text(root,976,y+48,item["id"]+"  "+item["example"],27,"#886d4d",weight=700)
        text(root,976,y+90,item["type_id"],21,C["muted"])
        text(root,976,y+131,"有建筑形式／关系资料，暂无独立来源图定位点",18,C["muted"])
        text(root,976,y+161,"禁止以主图空白处补齐宫门坐标",18,"#a2774e")
    path(root,"M70 1125H1730","#d5ddd2",2)
    text(root,70,1171,"此外，市场／里坊／学校的记载仍作为非空间性名录与关系层；不是城市人口密度调查。",23,C["ink"])
    text(root,70,1213,"永宁寺局部围墙仅保留来源图多折线与表列301×212m异记，禁止闭合成真实完整院界。",21,"#a2774e")
    text(root,70,1260,"历史图形来源：2012申遗保护管理图06a；底图1997航摄／1999测量；古今地面与不同朝代分期另核。",20,C["muted"])
    text(root,70,1305,"新增独立古址地面控制点 0 · 新古代地理定位 0 · 古建筑屋顶与高度测量 0。",20,"#4b6859")
    return root

def measurements_csv(data):
    stream=io.StringIO()
    writer=csv.writer(stream)
    writer.writerow(["id","name","source_feature_id","original_entity_id","architectural_type_id",
                     "plan_ew_reported_m","plan_ns_reported_m","dimension_source",
                     "approximate","registered_building_footprint","roof_height_known"])
    for d in data["anchored_buildings"]:
        m=d["reported_footprint_m"]
        writer.writerow([d["id"],d["name"],d["feature_id"],d["entity_id"] or "",
              d["type_id"] or "",m["east_west"],m["north_south"],d["dimension_source"],
              "true" if d["dimensions_approximate"] else "false","false","false"])
    return stream.getvalue()

def stylesheet_image_page(data,fig_svg,info):
    button_html=[]
    for item in data["anchored_buildings"]:
        explanation=(f'{item["name"]}：来源图标识 {item["feature_id"]}；'
          f'{item["dimension_source"]}，仅为独立发表的局部尺度。'
          '代表点不是原址已配准台基轮廓，古高与屋顶不详。')
        button_html.append(
            f'<button type="button" data-select-binding="{h(item["id"])}" '
            f'data-explanation="{h(explanation)}" aria-pressed="false">'
            f'<b>{h(item["id"][-2:])}</b><span>{h(item["name"])}'
            f'<em>来源图已有代表点／局部台基尺寸单独核对</em></span></button>')
    unplaced="".join(
       f'<div class="card"><span class="label">仅类型／尚无独立古址点</span>'
       f'<h3>{h(item["example"])}</h3><p>{h(item["type_id"])}</p>'
       f'<p class="muted">不绘制来源图之外的新历史位置。</p></div>'
       for item in data["unplaced_p44_types"])
    rows="".join(
      f'<tr><td>{h(item["name"])}</td><td>{h(item["feature_id"])}</td>'
      f'<td>{h(item["reported_footprint_m"]["east_west"])}m × '
      f'{h(item["reported_footprint_m"]["north_south"])}m</td>'
      f'<td>{h(item["dimension_source"])}</td>'
      f'<td>图示点位、尺寸分开；没有已配准足迹</td></tr>'
      for item in data["anchored_buildings"])
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>盛时洛阳 P4.5.1 · 来源图锚点与建筑类型分布</title>
<meta name="description" content="四处建筑与30个来源几何对象的可追溯关联、同尺度台基比较、未定位门制目录。">
<link rel="stylesheet" href="./prosperity-city-distribution/style.css"></head>
<body><header><a href="./">盛时洛阳</a>
<nav><a href="./prosperity.html">盛时来源图P1</a><a href="./prosperity-architecture.html">门制P4.4</a><a href="#downloads">下载</a></nav>
</header><main>
<section><p class="eyebrow">P4.5.1 · 同一个来源图，四处有迹可核的建筑参照</p>
<h1>先把建筑类型放回已有的城市骨架，再讨论宏伟全景</h1>
<p class="lead">本页直接继承2012年来源图30项几何中的4个建筑符号中心，关联阊阖门、建春门、太极殿与永宁塔基的已报告局部尺度。另有永宁寺局部围墙残段及4种尚不能独立定位的门制。</p>
<div class="chips"><span>30项来源图几何</span><span>13项关联既有实体ID</span>
<span>4处已有建筑参考点</span><span>4种宫门类型未独立定位</span><span>新增古址坐标 0</span></div>
<div class="caution"><strong>这不是四座建筑的实测地理多边形。</strong>图上的点位取自来源图概略符号中心；建筑尺寸另在不定位的同米尺图里比较。西安1980来源网格、1997/1999底图的现代洛水河道、北魏盛时解释和艺术全景彼此独立；现代洛水不能直接当作北魏河道。</div>
</section>
<section id="map"><h2>01 · 来源图上的四处建筑参照</h2>
<div class="mapsplit">
<figure class="map source-svg">{fig_svg}
<figcaption>原P1来源图线与节点未经修改；新增01—04只是读取原SVG已经存在的点位，再标注建筑类型证据。可点选标记及右侧条目。地图不能用于推算古墙或街区面积。</figcaption>
</figure>
<div class="reading-panel"><h3>选一处，查看它为什么可以标在这里</h3>
<div class="places" role="group" aria-label="建筑来源参照选择">{''.join(button_html)}</div>
<div class="selection" aria-live="polite"><strong>来源与限制</strong><p id="selected-reading">选择建筑参照，查看历史证据及不能推出的内容。</p></div>
<p class="muted">古籍文献图与来源图是两套不同的坐标组织方式；本页不把P1画布坐标转换为经纬度。</p></div></div>
<p><a href="./prosperity-city-distribution/grounded-distribution.svg">单独放大来源图SVG</a> ·
<a href="./prosperity/source-layout.svg">对读原P1城市来源骨架</a></p></section>
<section id="dimensions"><h2>02 · 四个建筑尺度片，统一米尺但不共地理位置</h2>
<figure class="diagram"><img src="./prosperity-city-distribution/scale-plates.svg"
alt="阊阖门、建春门、太极殿、永宁寺塔基的不同报告平面尺度同米尺比较，不代表已定位真实建筑足迹">
<figcaption>四张独立尺度片遵守统一米制；不是按图上实际点位绘成的已核建筑外轮廓。永宁38.2m方形指地上遗存塔基，而非九层木塔的顶部宽度或高度。</figcaption></figure>
<div class="tablewrap"><table><thead><tr><th>对象</th><th>来源图标识</th><th>发表尺寸</th><th>来源</th><th>地理与立面限制</th></tr></thead>
<tbody>{rows}</tbody></table></div></section>
<section id="unknown"><h2>03 · 建筑类别有记录，不等于每座门都已有坐标</h2>
<figure class="diagram"><img src="./prosperity-city-distribution/evidence-tiers.svg" alt="四处既有来源图代表点与四种未独立定位门制的证据层级总览">
<figcaption>这是一张非空间的证据目录。未定院门继续放在目录而不是补到宫城地图空白处。</figcaption></figure>
<div class="cards">{unplaced}</div>
<p>居民、市场、学校的记载仍可按类型与所属关系查阅，但尚不能从现有绘图点位推算人口密度与建筑面积。<a href="./dual-luonan.html#markets?id=LR10">查看市场专题</a>。</p></section>
<section id="sources"><h2>04 · 这批研究使用的来源层</h2>
<p>城市骨架来自2012年申遗保护管理图06a的已整理来源几何（西安1980图上网格；其背景采用1997航摄及1999测量），它包含多朝代遗存；并非独立验证了516—528每一座建筑的精确足迹。建筑尺寸使用P1、P4.2与P4.4的逐项报告，建筑形制推断不等同于出土立面。</p>
<p>太极殿宫院的310／370／380m三种范围口径、永宁寺残墙与301×212m表列院界的差异，继续保留为未解决问题。<a href="./prosperity-palace-boundaries.html">宫院尺寸证据</a> · <a href="./prosperity-architecture.html">建筑类型依据</a> · <a href="https://whc.unesco.org/uploads/nominations/1442.pdf">原申遗资料</a>。</p></section>
<section id="downloads"><h2>05 · 可审查与下载的成果</h2><div class="downloads">
<a href="./downloads/prosperity-city-distribution-p451-atlas.pdf">三页证据图册 PDF</a>
<a href="./downloads/prosperity-city-distribution-p451-package.zip">研究工作包 ZIP</a>
<a href="./prosperity-city-distribution/data.json">建筑关联 JSON</a>
<a href="./prosperity-city-distribution/measurements.csv">四处量距 CSV</a>
<a href="./prosperity-city-distribution/grounded-distribution.svg">带图例来源图 SVG</a>
</div><p class="muted">公开材料只承诺现有来源范围、报告尺寸与结构类型的联系；不主张已完成古代地面、全城人口密度、完整北魏街坊或三维建筑屋顶。</p></section>
<footer>P4.5.1 · 来源版本 {h(info["source_commit"][:10])} ·
<a href="./">返回已批准的盛时洛阳全景首页</a></footer>
</main><script src="./prosperity-city-distribution/app.js" defer></script></body></html>"""

def build():
    info=read(SITE/"build-info.json")
    release=read(SITE/"release.json")
    data=read(SRC)
    geo=read(SOURCE_GEO)
    dims=read(SOURCE_DIM)
    types=read(SOURCE_TYPES)
    p43=read(P43)
    lookup=verify_input(data,geo,dims,types,p43,info)
    assert not (SITE/"prosperity-city-distribution.html").exists()
    pre_hashes=dict(info["files_sha256"])
    protected={path:sha for path,sha in pre_hashes.items() if path not in MUTABLE}
    assert all(digest(SITE/path)==sha for path,sha in protected.items()),"Source/archived assets changed before P451"
    OUT.mkdir(parents=True,exist_ok=True)
    for src,name in [("web/prosperity-city-distribution.css","style.css"),
                     ("web/prosperity-city-distribution.js","app.js")]:
        shutil.copyfile(ROOT/src,OUT/name)
    original=SITE/"prosperity/source-layout.svg"
    chart,view_coords=append_overlays(original,data,lookup)
    result={
       **data,
       "source_map_overlay":{
         "type":"P1_svg_existing_symbol_centers_only",
         "base_map_asset":"prosperity/source-layout.svg",
         "original_base_map_sha256":pre_hashes["prosperity/source-layout.svg"],
         "new_historical_coordinates_added":0,
         "display_only_svg_locations":view_coords,
         "display_coordinates_have_ancient_geographic_meaning":False,
         "do_not_use_as_building_footprint_corners":True
       }
    }
    dump(OUT/"data.json",result)
    (OUT/"measurements.csv").write_text(measurements_csv(data),encoding="utf-8-sig")
    mapfile=OUT/"grounded-distribution.svg"
    scale=OUT/"scale-plates.svg"
    tier=OUT/"evidence-tiers.svg"
    write_svg(mapfile,chart)
    write_svg(scale,scale_plate(data))
    write_svg(tier,tiers_plate(data))
    for f in (mapfile,scale,tier):
        root=ET.parse(f).getroot()
        assert root.tag==f"{{{NS}}}svg"
    (SITE/"downloads").mkdir(exist_ok=True)
    pdf=SITE/"downloads/prosperity-city-distribution-p451-atlas.pdf"
    render_atlas([mapfile,scale,tier],pdf)
    page=SITE/"prosperity-city-distribution.html"
    page.write_text(stylesheet_image_page(data,ET.tostring(chart,encoding="unicode"),info),encoding="utf-8")
    (OUT/"README.md").write_text(
       "P4.5.1: P1图符中心原样继承，4处建筑关联；4种P4.4门制不独立定位。\n"
       "SVG中的data-binding-id与display_only_svg_locations仅是版面像素参照，不是古代独立测量点。\n"
       "四个局部尺寸片使用相同像素/米，但在地理图上不叠画台基或院墙。\n"
       "已批准首页V9不变；现代洛水线不当北魏水道。\n",encoding="utf-8")
    # Discoverability, but without modifying the approved H2 hero illustration.
    excerpt=(
       '<section id="prosperity-p451-entry" style="padding:16px 20px;margin:14px 0;'
       'border:1px solid #cad9d0;border-left:4px solid #658b73;background:#f2f6f0">'
       '<h3 style="margin:0 0 8px">盛时洛阳 P4.5.1 · 城市来源图与建筑类型</h3>'
       '<p style="margin:0 0 9px">四处有来源图参照的建筑点、四组局部尺度，以及仍未独立定位的宫门类型。</p>'
       '<a href="./prosperity-city-distribution.html">查看同一城市骨架的建筑分布审查图 →</a>'
       '</section>\n'
    )
    old_html={}
    for name in ("index.html","v3.0-dual.html"):
        p=SITE/name
        b=p.read_bytes()
        old_html[name]=digest(p)
        pre=OUT/"history"/name.replace(".html","-before-p451.html")
        pre.parent.mkdir(exist_ok=True)
        pre.write_bytes(b)
        old=b.decode("utf-8")
        assert old.count(NAVMARK)==1
        assert 'data-hero-revision="panorama-approved-v9"' in old
        p.write_text(old.replace(NAVMARK,excerpt+NAVMARK,1),encoding="utf-8")
    (OUT/"README.md").write_text((OUT/"README.md").read_text(encoding="utf-8")
      + "已存P4.5.1加入入口前的H2完整网页快照（history）。\n",encoding="utf-8")
    dump(OUT/"preservation.json",{
      "version":VERSION,"source_commit":info["source_commit"],
      "protected_unchanged":True,"protected_files_sha256":protected,
      "source_map_original_sha256":pre_hashes["prosperity/source-layout.svg"],
      "intentional_html_edits":["index.html","v3.0-dual.html"],
      "pre_edit_html_sha256":old_html,
      "homepage_hero_approved_revision":"panorama-approved-v9"
    })
    assert all(digest(SITE/p)==value for p,value in protected.items()),"P451 changed earlier publication"
    members={f"prosperity-city-distribution/{p.relative_to(OUT)}":p
             for p in sorted(OUT.rglob("*")) if p.is_file()}
    members["prosperity-city-distribution.html"]=page
    members[f"downloads/{pdf.name}"]=pdf
    dump(OUT/"bundle-manifest.json",{"version":VERSION,"source_commit":info["source_commit"],
        "files_sha256":{name:digest(file) for name,file in members.items()}})
    members["prosperity-city-distribution/bundle-manifest.json"]=OUT/"bundle-manifest.json"
    archive=SITE/"downloads/prosperity-city-distribution-p451-package.zip"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
        for name,file in members.items():
            z.write(file,name)
    release["extensions"]=sorted(set(release.get("extensions",[])+[VERSION]))
    release["prosperity_city_distribution_version"]=VERSION
    release["current_milestone"]="盛时P4.5.1：已有城市骨架上四处建筑类型与尺度的来源分层"
    dump(SITE/"release.json",release)
    info["prosperity_city_distribution"]={
       "version":VERSION,"source_commit":info["source_commit"],
       "source_feature_count":len(geo["features"]),
       "source_entity_bound_feature_count":sum(bool(f.get("entity_id")) for f in geo["features"]),
       "anchored_building_count":len(data["anchored_buildings"]),
       "unlocated_gate_type_count":len(data["unplaced_p44_types"]),
       "atlas_pages":3,"new_absolute_ancient_coordinates":0,
       "measured_roof_heights_added":0,
       "source_map_sha256":digest(original),
       "metadata":"prosperity-city-distribution/data.json"
    }
    info["files_sha256"]={str(p.relative_to(SITE)):digest(p) for p in sorted(SITE.rglob("*"))
                          if p.is_file() and p.name!="build-info.json"}
    dump(SITE/"build-info.json",info)
    print(json.dumps(info["prosperity_city_distribution"],ensure_ascii=False))

if __name__=="__main__":
    build()
