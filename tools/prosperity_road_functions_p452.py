#!/usr/bin/env python3
"""P4.5.2: show source-map road *remnants* and separate qualitative document relations.

The eight geometric roads are cloned exclusively from already-published P1 SVG
path data (no new historical site points). Documentary road-side relations live
in a separate, NON-geographic panel. Nothing is inferred from the H2 panorama.
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

from dual_cartography import NS,C,node,text,rect,path,svg,write_svg
from north_b4 import render_atlas

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
OUT=SITE/"prosperity-road-functions"
VERSION="prosperity-road-functions-p452"
SRC=ROOT/"research/prosperity-v4/road-functions-p452.json"
SOURCE_GEO=ROOT/"research/prosperity-v1/geographic-evidence.json"
SOURCE_P451=ROOT/"research/prosperity-v4/city-distribution-p451.json"
SOURCE_B1=ROOT/"research/dual-b1/decisions.json"
SOURCE_B7=ROOT/"research/dual-b7/luonan-river-markets.json"
SOURCE_B8=ROOT/"research/dual-b8/cross-batch-review.json"
SOURCE_P1=ROOT/"research/prosperity-v1/text-review.json"
SOURCE_ENT=ROOT/"data/entities.json"
MUTABLE={"prosperity-city-distribution.html","release.json","build-info.json"}
ROAD_COLORS=["#ac7551","#547970","#728f5c","#8094a5","#8b7898","#537f96","#9b8263","#7c8a71"]

def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def esc(s):
    return html.escape(str(s),quote=True)

def verify_sources(d,geo,p451,b1,b7,b8,p1,entities,info):
    assert d["version"]==VERSION and geo["crs"]=="EPSG:4610"
    assert len(geo["features"])==30 and len(d["road_segments"])==8
    assert p451["version"]=="prosperity-city-distribution-p451"
    assert len(p451["anchored_buildings"])==4
    assert info["prosperity_city_distribution"]["version"]=="prosperity-city-distribution-p451"
    assert info["homepage_approved_v9"]["hero_revision"]=="panorama-approved-v9"
    assert sha(SITE/"prosperity/source-layout.svg")==info["files_sha256"]["prosperity/source-layout.svg"]
    assert read(SITE/"homepage/approval-v9.json")["hero"]["status"]=="approved"
    lookup={f["id"]:f for f in geo["features"]}
    assert len(lookup)==30
    ids={x["id"] for x in entities}
    assert len(entities)==339 and len(ids)==len(entities)
    known_roads={f["id"] for f in geo["features"] if f["id"].startswith("geo-road-") or f["id"].startswith("geo-tongtuo-")}
    asserted={x["feature_id"] for x in d["road_segments"]}
    assert len(asserted)==8 and asserted==known_roads,(asserted,known_roads)
    assert all(x["geometry"]["type"]=="MultiLineString" for x in (lookup[fid] for fid in known_roads))
    assert len(d["contexts"])==5 and len(d["nongeographic_function_groups"])==5
    assert d["unchanged_assets"]["changed_ancient_original_geometries"]==0
    assert d["unchanged_assets"]["added_historical_geographic_anchors"]==0
    assert d["unchanged_assets"]["drawn_population_density_maps"]==0
    assert all(not c["route_measured"] for c in d["contexts"])
    assert all(not x["new_building_footprint"] for x in d["nongeographic_function_groups"])
    for x in d["road_segments"]:
        f=lookup[x["feature_id"]]
        assert f["source_feature_code"]==x["source_code"]
        assert f["layer"]=="site_remains"
        assert f["source_id"]=="unesco-1442-management-06a"
        assert f["approximation"]["status"]=="source_map_generalized"
        assert not f["approximation"]["is_field_verified_gcp"]
        assert x["evidence"].startswith("source_map_generalized")
        if x["id"]=="D01":
            assert x["sourced_length_m"]==1650
            assert x["sourced_width_m_range"]==[40,65]
        else:
            assert x["sourced_length_m"] is None and x["sourced_width_m_range"] is None
    assert {x["id"] for x in d["contexts"]}=={f"R{i:02d}" for i in range(1,6)}
    assert {x["id"] for x in d["road_segments"]}=={f"D{i:02d}" for i in range(1,9)}
    for c in d["contexts"]:
        assert set(c["mapped_road_ids"])<={x["id"] for x in d["road_segments"]}
        assert set(c["entity_ids"])<=ids
        assert set(c["other_source_feature_ids"])<=set(lookup)
    for group in d["nongeographic_function_groups"]:
        assert set(group["entity_ids"])<=ids
        assert set(group["source_context_ids"])<={x["id"] for x in d["contexts"]}
    decisions={x["id"] for x in b1["decisions"]}
    evidence={x["id"] for x in b7["evidence"]}
    cases={x["id"] for x in b8["records"]}
    src_quotes={x.get("legacy_title") for x in p1["records"]}
    required={"B03","B06","B07","B08"}
    assert required<=decisions
    assert {"LR01","LR04","LR07","LR10"}<=evidence
    assert {"CB08","CB09","CB11","CB13"}<=cases
    assert {"v2.5:E01","v2.5:E03","v2.5:E04"}<=src_quotes
    # The 5 contexts reuse these exact older evidence IDs, but we never
    # mark a real surveyed road connection or bridge point as created.
    assert all(ref.split("#")[0].startswith("research/") for c in d["contexts"] for ref in c["provenance_refs"])
    assert d["data_lineage"]["direct_historical_earth_controls_acquired"]==0
    assert d["data_lineage"]["new_absolute_coordinates_added"]==0
    assert not d["data_lineage"]["modern_river_used_as_ancient_river"]
    return lookup

def metrics(d,lookup):
    enriched=[]
    for x in d["road_segments"]:
        f=lookup[x["feature_id"]]
        g=f["geometry"]
        assert g["type"]=="MultiLineString"
        lines=g["coordinates"]
        assert all(len(line)>=2 for line in lines)
        enriched.append({
            **x,"published_source_geometry_type":g["type"],
            "source_map_line_parts":len(lines),
            "source_map_vertex_count":sum(len(line) for line in lines),
            "source_period":f["source_historical_period"],
            "source_reported_legend":f.get("source_legend"),
            "source_map_layer":f["layer"],
            "original_geometry_unchanged":True,
            "source_map_wgs84_registration_verified":False
        })
    return enriched

def original_svg_road_overlay(src,roads):
    root=ET.parse(src).getroot()
    assert root.get("viewBox")=="0 0 1800 1440"
    assert root.tag==f"{{{NS}}}svg"
    layer=node(root,"g",id="p452-existing-road-overlays",
               data_geometry_role="unmodified_original_source_svg_paths_no_new_connections")
    parts={}
    for i,x in enumerate(roads):
        lookup=[g for g in root.iter() if g.get("data-feature-id")==x["feature_id"]]
        assert len(lookup)==1,(x["feature_id"],len(lookup))
        srcpaths=[e for e in lookup[0].iter() if e.tag==f"{{{NS}}}path" and e.get("d")]
        assert len(srcpaths)==x["source_map_line_parts"],(x["id"],len(srcpaths),x["source_map_line_parts"])
        g=node(layer,"g",data_road_id=x["id"],
               data_source_feature_ref=x["feature_id"],data_active="false",
               aria_pressed="false",role="button",tabindex="0")
        g.set("class","road-group")
        node(g,"title").text=x["name"]+"；只以原P1已画路径作交互高亮，不表示额外可通道路。"
        for p in srcpaths:
            e=node(g,"path",d=p.get("d"),fill="none",stroke=ROAD_COLORS[i],
                   stroke_width=14,opacity=".68",pointer_events="stroke")
            e.set("class","road-line")
        parts[x["id"]]=[p.get("d") for p in srcpaths]
    for x in root.iter():
        if x.tag==f"{{{NS}}}title" and x.text and "盛时城市分布" in x.text:
            x.text="盛时洛阳 P4.5.2：原P1来源图8条道路遗存高亮，非新道路配准"
            break
    return root,parts

def heading(r,kicker,title,sub,w=1800):
    text(r,62,53,kicker,20,"#5b816d",weight=700)
    text(r,62,106,title,36,C["ink"],weight=700)
    text(r,62,149,sub,19,C["muted"])
    path(r,f"M62 172H{w-62}","#d2dcd2",2)

def relation_plate(d):
    root=svg(1800,1450,"五组文献道路关系：明确证据而非GIS连接")
    heading(root,"P4.5.2 / TEXT VS SOURCE-GEOMETRY",
            "五组道路与建筑关系，各自有证据等级",
            "卡片的上下左右为排版，不代表城市真实方位或各组间可直接通行。")
    summaries=[
        ("R01","来源图","阊阖门图符／铜驼大道／宫南横街","不能将图上铜驼残线自动等于完整宫前御道。"),
        ("R02","正文方位","永宁寺：宫前门南一里、御道西","明文为关系；“一里”不转换为米或独立坐标。"),
        ("R03","桥梁分身份","建春第一石桥／东石桥与桥北大道","527颓桥只在第一桥；两里东西不产生坊墙。"),
        ("R04","文字交通","宣阳门／永桥浮桥／洛南四通市","四里不是实测路线；永桥市别名不定桥头市场。"),
        ("R05","正文＋解释","左卫东／右卫西／官署国子学南序","太尉御道路侧工作解释，不传递给所有相邻建筑。")
    ]
    for i,(ident,grade,name,note) in enumerate(summaries):
        y=212+i*236
        rect(root,60,y,1680,209,"#ffffff","#d8e1d8",2,11)
        rect(root,83,y+21,14,51,ROAD_COLORS[i],ROAD_COLORS[i],1,2)
        text(root,117,y+56,ident+"  "+grade,30,ROAD_COLORS[i],weight=700)
        text(root,117,y+111,name,27,C["ink"],weight=650)
        text(root,117,y+168,note,21,"#9b7651")
    text(root,65,1415,"白底只是研究展示：源图路网不补线，古道不投WGS84，旧图道路宽度与桥位不凭图示线厚推定。",18,C["muted"])
    return root

def function_plate(d):
    root=svg(1800,1430,"盛时洛阳五类功能名录：以文字关系展示不虚构面积密度")
    heading(root,"P4.5.2 / DOCUMENTARY FUNCTIONS",
            "五类城市功能可以分类，尚不能画成实测用地密度",
            "每张卡都列有旧对象ID和文献情境；这不是坊墙、市场、学校或人口密度地图。")
    cols=[(68,193),(928,193),(68,560),(928,560),(68,927)]
    for x,(cx,cy) in zip(d["nongeographic_function_groups"],cols):
        rect(root,cx,cy,805,328,"#fff","#d4ddd4",2,11)
        text(root,cx+24,cy+51,x["id"]+"  "+x["title"],31,"#336a58",weight=700)
        text(root,cx+24,cy+101,"功能："+x["type"]+" · 地理足迹：未新增",20,C["muted"])
        text(root,cx+24,cy+144,"原实体ID："+"、".join(x["entity_ids"][:3]),19,C["ink"])
        if len(x["entity_ids"])>3:
            text(root,cx+24,cy+176,"其余："+",".join(x["entity_ids"][3:]),18,C["muted"])
        lines=wrap(x["note"],29)
        for j,t in enumerate(lines[:3]):
            text(root,cx+24,cy+224+j*34,t,20,"#8d704e")
    rect(root,928,927,805,328,"#e9efea","#b6c9b9",2,11)
    text(root,956,983,"方法限制：0新增地理点 · 0推测人口密度",25,"#376a58",weight=700)
    for j,s in enumerate(["旧30项来源图几何完全不变","铜驼街不自动等于完整御道","永桥不落在近现代洛水线上","没有得到古代桥宽、建筑古高及院墙全界"]):
        text(root,957,1046+j*44,"· "+s,20,C["ink"])
    text(root,67,1370,"时层：516—528年盛时文献综合；来源图含魏晋—北魏多时层遗存，现代河道属1997/1999底图参考。",19,C["muted"])
    return root

def wrap(textval,n):
    return [textval[k:k+n] for k in range(0,len(textval),n)]

def read_csv(roads):
    stream=io.StringIO()
    writer=csv.writer(stream)
    writer.writerow(["road_id","feature_id","source_feature_code","source_period",
                     "source_map_subpaths","source_map_vertices","source_report_length_m",
                     "source_report_width_min_m","source_report_width_max_m",
                     "source_geometric_type","new_ancient_coords","ancient_surface_verified"])
    for x in roads:
        width=x["sourced_width_m_range"] or ["",""]
        writer.writerow([x["id"],x["feature_id"],x["source_code"],x["source_period"],
                         x["source_map_line_parts"],x["source_map_vertex_count"],
                         x["sourced_length_m"] if x["sourced_length_m"] is not None else "",
                         width[0],width[1],x["published_source_geometry_type"],0,"false"])
    return stream.getvalue()

def context_csv(d):
    s=io.StringIO()
    wr=csv.writer(s)
    wr.writerow(["context_id","title","evidence_grade","mapped_source_road_ids","historical_entity_ids","direct_quote","original_source_refs","route_measured","limits"])
    for x in d["contexts"]:
        wr.writerow([x["id"],x["title"],x["grade"],";".join(x["mapped_road_ids"]),
                     ";".join(x["entity_ids"]),x["original_quote"] or "",
                     ";".join(x["provenance_refs"]),"false",x["not_proved"]])
    return s.getvalue()

def page(d,svg_root,info):
    road_cards=[]
    for x in d["road_segments"]:
        explanation=(f'{x["name"]}：来源图原编号 {x["source_code"]}；'
                     f'记录分离的图段 {x["source_map_line_parts"]} 组（绘图结构，非通行道路条数）。'
                     f' {x["annotation"]} 原始来源图线未经改动。')
        road_cards.append(
            f'<button type="button" data-road-control="{h(x["id"])}" '
            f'data-reading="{h(explanation)}" aria-pressed="false">'
            f'<strong>{h(x["id"])}　{h(x["name"])}</strong>'
            f'<small>{h(x["source_code"])} · 源图概化的{h(x["source_map_line_parts"])}组线条</small></button>')
    context_buttons=[]
    for x in d["contexts"]:
        explanation=(
            f'{x["title"]}。{x["historical_claim"]} '
            f'不能推出：{x["not_proved"]} '
            f'来源索引：{", ".join(x["provenance_refs"])}。'
        )
        context_buttons.append(
            f'<button type="button" data-context="{h(x["id"])}" '
            f'data-reading="{h(explanation)}" aria-pressed="false">'
            f'<strong>{h(x["id"])}　{h(x["title"])}</strong>'
            f'<small>{h(x["grade"])}层证据 · 尚无可量的完整路线</small></button>')
    road_rows="".join(
        f'<tr><td>{h(x["id"])}</td><td>{h(x["name"])}</td><td>{h(x["source_code"])}</td>'
        f'<td>{x["source_map_line_parts"]}</td><td>{h(x["source_period"])}</td>'
        f'<td>{h(str(x["sourced_width_m_range"]) if x["sourced_width_m_range"] is not None else "未独立登记")}</td></tr>'
        for x in d["road_segments"])
    directory="".join(
        f'<article><span class="tag">{h(x["id"])} · 文献功能目录（非地理足迹）</span>'
        f'<h3>{h(x["title"])}</h3><p>{h(x["note"])}</p>'
        f'<p class="muted">已有实体ID：{h(", ".join(x["entity_ids"]))}</p></article>'
        for x in d["nongeographic_function_groups"])
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>盛时洛阳 P4.5.2 · 道路骨架、文献路侧与建筑功能</title>
<meta name="description" content="八项来源图道路残段与五组道路文献关系分离，市场、寺院、里坊与学校不作伪精确城市密度。">
<link rel="stylesheet" href="./prosperity-road-functions/style.css"></head>
<body><header><a href="./">盛时洛阳</a><nav>
<a href="./prosperity-city-distribution.html">P4.5.1 建筑来源分布</a>
<a href="./prosperity.html">P1 源图</a><a href="#contexts">关系审查</a><a href="#downloads">下载</a></nav></header>
<main>
<section><p class="eyebrow">P4.5.2 · 城市骨架从“图上的线”与“书里的方位”分别阅读</p>
<h1>路网残段可以绘制，整座城市的街区不能凭空补齐。</h1>
<p class="lead">本批复用原P1图中的八项道路残线，检查铜驼大道、宫城南横街、内城横纵道路图示范围；同时对照永宁寺御道西、建春门两石桥、宣阳永桥、官署与国子学等五组文本关系。</p>
<div class="facts"><span>8项既有道路遗存线</span><span>5组文献道路情境</span><span>5类非空间功能目录</span><span>新增古址坐标 0</span></div>
<div class="caution"><strong>来源图残线不是完整北魏交通网。</strong>尤其不能直接把图中铜驼大道和《洛阳伽蓝记》宫前御道认作同一条已测线路。东石桥、建春第一石桥和永桥不能合并，近现代洛水位置不等于北魏河道。</div>
</section>
<section id="map"><h2>01 · 2012年来源图已有的八段道路结构</h2>
<div class="layout"><figure class="map">{svg_root}
<figcaption>从P1来源图的30项几何中只复用八条已画路迹（图示路径字节不改），着色用于交互。路线上没有追加交叉口、坊墙或新桥梁；颜色不表示真实古代路面材质。</figcaption></figure>
<div><h3>选择道路，查看证据与未证项目</h3><div class="road-list" role="group" aria-label="现有来源图道路选择">{''.join(road_cards)}</div>
<div class="info" aria-live="polite"><strong>原来源线与限制</strong><p id="road-reading">从左图或道路条目选择。</p></div>
<p class="muted">8条记录的绘图子段数量由来源GeoJSON式geometry结构读取，不代表可连续通行的八条完整道路。</p></div></div>
<p><a href="./prosperity-road-functions/road-evidence-map.svg">独立放大SVG</a> · <a href="./prosperity/source-layout.svg">对照未经改动的P1来源图</a></p>
</section>
<section id="contexts"><h2>02 · 五组跨文献的道路—建筑关系</h2>
<figure class="diagram"><img src="./prosperity-road-functions/qualitative-relations.svg" alt="五组道路与建筑的相对关系与证据等级，明确不是实测地理路网">
<figcaption>五组关系各有独立的对象ID与出处，不让景明行像穿过未记载的永桥，不把第一桥的527毁损扩展到其它桥梁。</figcaption></figure>
<div class="context-layout"><div class="context-list" role="group" aria-label="选择文献道路情境">{''.join(context_buttons)}</div>
<div class="detail"><h3>文字证据与不可推出的结论</h3><p id="context-detail">点选左侧一组，查看明文、来源和推断边界。</p>
<div class="evidence"><strong>如何区分证据</strong><p>A：原文方位明示；B：旧来源图概略路迹；C：前后文序列/校勘解释；D：纯目录未定位。</p>
<p>同一段道路如果仅由图示方位判断，不能自动获得古代道路名称与交通功能；文本说明“御道西”也不能自动接到该图上的具体坐标点。</p></div></div></div>
</section>
<section id="function"><h2>03 · 市场、寺院、官署、学校与里坊的类型目录</h2>
<figure class="diagram"><img src="./prosperity-road-functions/function-layers.svg" alt="五类文献功能目录，不生成市场建筑占地和人口密度">
<figcaption>功能分组来自既有实体/文献档案，只是阅读组织。没有使用图上建筑符号数量计算市肆、人口或街道密度。</figcaption></figure>
<div class="directory">{directory}</div>
<p>四通市俗称永桥市，但只有洛水南的文献关系；归正里鱼鳖市是另一条里内巷市记录。两市都售鱼并不证明同一市场。<a href="./dual-luonan.html#markets?id=LR10">回到洛南市场史料</a>。</p>
</section>
<section id="roadtable"><h2>04 · 路迹来源表</h2>
<div class="tablewrap"><table><thead><tr><th>ID</th><th>来源路段</th><th>图号</th><th>图中子段</th><th>遗址时层</th><th>表列路宽</th></tr></thead><tbody>{road_rows}</tbody></table></div>
<p>铜驼大道来源表列现存段约长1650m、宽40—65m；它并不是对整条北魏御道每一段的现场测量。其余路段没有足以直接登记的米制宽度，不使用SVG笔画粗细补数。</p>
<p>文本来源：<a href="https://deerpark.app/cbeta/B0077/1">《洛阳伽蓝记》卷一</a>、<a href="https://deerpark.app/cbeta/B0077/2">卷二</a>、<a href="https://deerpark.app/cbeta/B0077/3">卷三</a>；遗址来源：<a href="https://whc.unesco.org/uploads/nominations/1442.pdf">世界遗产申报图册06a</a>。本页的校勘与推断均保留既有B1/B7/B8/P1原研究结论，不将大众转载计为独立古代测绘。</p></section>
<section id="downloads"><h2>05 · 研究成果与数据</h2>
<div class="downloads">
<a href="./downloads/prosperity-road-functions-p452-atlas.pdf">三页证据图册 PDF</a>
<a href="./downloads/prosperity-road-functions-p452-package.zip">完整资料 ZIP</a>
<a href="./prosperity-road-functions/data.json">证据 JSON</a>
<a href="./prosperity-road-functions/source-roads.csv">八条路迹 CSV</a>
<a href="./prosperity-road-functions/text-contexts.csv">五组关系 CSV</a></div>
<p class="muted">没有生成新古址控制点、古代道路连接线、桥面尺寸、市场房屋占地或人流密度。首页H2已批准的全景和以前的P4.5.1建筑分布数据保持不变。</p></section>
<footer>盛时洛阳 P4.5.2 · 来源提交 {h(info["source_commit"][:10])} ·
<a href="./">返回正式盛时全景首页</a></footer>
</main><script src="./prosperity-road-functions/app.js" defer></script></body></html>"""

def main():
    info=read(SITE/"build-info.json")
    release=read(SITE/"release.json")
    d=read(SRC)
    geo=read(SOURCE_GEO)
    p451=read(SOURCE_P451)
    b1=read(SOURCE_B1)
    b7=read(SOURCE_B7)
    b8=read(SOURCE_B8)
    p1=read(SOURCE_P1)
    entities=read(SOURCE_ENT)
    verify_sources(d,geo,p451,b1,b7,b8,p1,entities,info)
    assert not (SITE/"prosperity-road-functions.html").exists()
    old_assets=dict(info["files_sha256"])
    protected={file:digest for file,digest in old_assets.items() if file not in MUTABLE}
    assert all(sha(SITE/path)==value for path,value in protected.items())
    OUT.mkdir(parents=True,exist_ok=True)
    for src,target in [("web/prosperity-road-functions.css","style.css"),
                       ("web/prosperity-road-functions.js","app.js")]:
        shutil.copyfile(ROOT/src,OUT/target)
    enriched=metrics(d,{x["id"]:x for x in geo["features"]})
    image,source_paths=original_svg_road_overlay(SITE/"prosperity/source-layout.svg",enriched)
    page_info={
      **d,"road_source_details":enriched,
      "source_map_overlay":{
        "origin_asset":"prosperity/source-layout.svg",
        "source_map_sha256":old_assets["prosperity/source-layout.svg"],
        "cloned_exact_original_svg_path_data":source_paths,
        "same_existing_location_only":True,
        "new_historical_coordinates_added":0,
        "new_street_connections_added":0,
        "source_map_geometry_mutated":False
      }
    }
    dump(OUT/"data.json",page_info)
    (OUT/"source-roads.csv").write_text(read_csv(enriched),encoding="utf-8-sig")
    (OUT/"text-contexts.csv").write_text(context_csv(d),encoding="utf-8-sig")
    img=OUT/"road-evidence-map.svg"
    relations=OUT/"qualitative-relations.svg"
    functions=OUT/"function-layers.svg"
    write_svg(img,image)
    write_svg(relations,relation_plate(d))
    write_svg(functions,function_plate(d))
    for p in (img,relations,functions):
        assert ET.parse(p).getroot().tag==f"{{{NS}}}svg"
    (SITE/"downloads").mkdir(parents=True,exist_ok=True)
    pdf=SITE/"downloads/prosperity-road-functions-p452-atlas.pdf"
    render_atlas([img,relations,functions],pdf)
    page_file=SITE/"prosperity-road-functions.html"
    page_file.write_text(page({**d,"road_segments":enriched},ET.tostring(image,encoding="unicode"),info),encoding="utf-8")
    (OUT/"README.md").write_text(
     "P4.5.2继承P1的八条原有道路多段折线，不补支路、通行路网、古代街道宽度或古河道。\n"
     "独立文字关系不以图上的相近节点合并；现代洛水底图不是北魏河槽。\n"
     "宫前御道与铜驼大道可比较但尚未完成同址同线的独立测量确认。\n"
     "原H2全景批准图、P4.5.1数据均保留。\n",encoding="utf-8")
    prev=SITE/"prosperity-city-distribution.html"
    old=prev.read_text(encoding="utf-8")
    mark="<footer>P4.5.1 ·"
    assert old.count(mark)==1
    archived=OUT/"history/prosperity-city-distribution-before-p452.html"
    archived.parent.mkdir(parents=True,exist_ok=True)
    archived.write_text(old,encoding="utf-8")
    insertion=(
      '<section id="p452-next"><h2>新增P4.5.2：八组来源图道路残段与文献路侧</h2>'
      '<p>沿用P1已有的道路图形，不增加古代道路连接线；宫前御道、建春两桥、洛南永桥及官署学校分别核对。</p>'
      '<p><a href="./prosperity-road-functions.html">进入 P4.5.2 道路—功能关系专题 →</a></p>'
      '</section>'
    )
    prev.write_text(old.replace(mark,insertion+mark,1),encoding="utf-8")
    dump(OUT/"preservation.json",{
        "version":VERSION,"source_commit":info["source_commit"],
        "protected_unchanged":True,"protected_files":len(protected),
        "protected_sha256":protected,
        "previous_p451_html_sha256":hashlib.sha256(old.encode("utf-8")).hexdigest(),
        "current_approved_hero":"panorama-approved-v9",
        "intentional_updates":sorted(MUTABLE),
        "new_historical_geographic_anchors":0
    })
    assert all(sha(SITE/path)==digest for path,digest in protected.items()),"Prior published work modified"
    members={f"prosperity-road-functions/{p.relative_to(OUT)}":p for p in sorted(OUT.rglob("*")) if p.is_file()}
    members["prosperity-road-functions.html"]=page_file
    members[f"downloads/{pdf.name}"]=pdf
    dump(OUT/"bundle-manifest.json",{
      "version":VERSION,"source_commit":info["source_commit"],
      "files_sha256":{k:sha(f) for k,f in members.items()}
    })
    members["prosperity-road-functions/bundle-manifest.json"]=OUT/"bundle-manifest.json"
    bundle=SITE/"downloads/prosperity-road-functions-p452-package.zip"
    with zipfile.ZipFile(bundle,"w",zipfile.ZIP_DEFLATED) as z:
        for name,file in members.items():z.write(file,name)
    release["extensions"]=sorted(set(release.get("extensions",[])+[VERSION]))
    release["prosperity_road_functions_version"]=VERSION
    release["current_milestone"]="盛时P4.5.2：8条来源图道路残段与5组文献路侧/城市功能证据审查"
    dump(SITE/"release.json",release)
    info["prosperity_road_functions"]={
        "version":VERSION,"source_commit":info["source_commit"],
        "source_feature_count":len(geo["features"]),
        "road_feature_count":len(enriched),
        "documentary_context_count":len(d["contexts"]),
        "function_groups":len(d["nongeographic_function_groups"]),
        "atlas_pages":3,
        "source_map_sha256":old_assets["prosperity/source-layout.svg"],
        "new_ancient_coordinates":0,
        "measured_historical_road_connections":0,
        "historical_traffic_density_estimated":False,
        "metadata":"prosperity-road-functions/data.json"
    }
    info["files_sha256"]={
      str(p.relative_to(SITE)):sha(p)
      for p in sorted(SITE.rglob("*")) if p.is_file() and p.name!="build-info.json"
    }
    dump(SITE/"build-info.json",info)
    print(json.dumps(info["prosperity_road_functions"],ensure_ascii=False))

if __name__=="__main__":
    main()
