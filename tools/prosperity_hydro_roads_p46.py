#!/usr/bin/env python3
"""P4.6: source-graded water + trunk-road anchor audit.

No ancient water polylines or synthetic street vertices are generated. An exact
copy of the old P1 source map is paired with purely schematic research plates.
Only known source features may have coordinates, which remain unchanged.
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

from dual_cartography import NS, C, node, text, rect, path, svg, write_svg
from north_b4 import render_atlas

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
OUT=SITE/"prosperity-hydro-roads"
SRC=ROOT/"research/prosperity-v4/hydro-roads-anchor-p46.json"
GEO=ROOT/"research/prosperity-v1/geographic-evidence.json"
TERRAIN=ROOT/"research/prosperity-v1/terrain-constraints.json"
P452=ROOT/"research/prosperity-v4/road-functions-p452.json"
P453=ROOT/"research/prosperity-v4/street-clusters-p453.json"
VERSION="prosperity-hydro-roads-anchor-p46"
MUTABLE={"prosperity-street-clusters.html","release.json","build-info.json"}
W,H=1800,1440

def read(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def esc(s):return html.escape(str(s),quote=True)
def note(root,x,y,words,color="#677d6d",size=20):
    text(root,x,y,words,size,color)
def box(root,x,y,w,h,fill="#fff",border="#d5ded6"):
    return rect(root,x,y,w,h,fill,border,2,10)
def header(root,kicker,title,desc):
    text(root,60,62,kicker,23,"#597c67",weight=700)
    text(root,60,117,title,39,C["ink"],weight=700)
    text(root,60,164,desc,20,C["muted"])
    path(root,"M60 185H1740","#d8e2d8",2)
def footer(root,desc):
    path(root,"M60 1390H1740","#d8e2d8",2)
    text(root,61,1420,desc,17,C["muted"])

def validate(d,geo,terrain,p452,p453,info):
    assert d["version"]==VERSION
    assert len(d["water_features"])==34
    assert len(d["main_road_records"])==21
    assert len(d["source_registry"])==17
    assert geo["crs"]=="EPSG:4610"
    assert len(geo["features"])==30
    assert p452["version"]=="prosperity-road-functions-p452"
    assert p453["version"]=="prosperity-street-clusters-p453"
    assert info["prosperity_street_clusters"]["version"]=="prosperity-street-clusters-p453"
    assert info["homepage_approved_v9"]["hero_revision"]=="panorama-approved-v9"
    assert sha(SITE/"prosperity/source-layout.svg")==info["files_sha256"]["prosperity/source-layout.svg"]
    assert read(SITE/"homepage/approval-v9.json")["hero"]["status"]=="approved"
    srcs={x["id"] for x in d["source_registry"]}
    assert len(srcs)==len(d["source_registry"])
    features={x["id"]:x for x in geo["features"]}
    assert len(features)==30
    assert {x["id"] for x in d["water_features"]}=={f"W{i:02d}" for i in range(1,35)}
    assert len({x["id"] for x in d["main_road_records"]})==21
    wmodern=[x for x in d["water_features"] if x["position_tier"]=="registered_modern_basemap_line"]
    assert len(wmodern)==1 and wmodern[0]["id"]=="W02"
    assert wmodern[0]["registered_source_feature_id"]=="geo-modern-luo-river"
    assert features["geo-modern-luo-river"]["layer"]=="modern_geographic_reference"
    assert all(not x["ancient_geographic_line_or_polygon_verified"] for x in d["water_features"])
    assert all(x["independent_ground_controls"]==0 for x in d["water_features"])
    for x in d["water_features"]:
        assert set(x["source_ids"])<=srcs,(x["id"],x["source_ids"])
        if x["registered_source_feature_id"]:
            assert x["registered_source_feature_id"] in features
    assert all(not x["ancient_full_route_georegistered"] for x in d["main_road_records"])
    assert all(x["new_route_polyline"] is None for x in d["main_road_records"])
    old=p452["road_segments"]
    assert len(old)==8
    for i,r in enumerate(d["main_road_records"][:8]):
        assert r["id"]==f"R{i+1:02d}"
        assert r["registered_source_feature_id"]==old[i]["feature_id"]
        assert r["linked_prior_road_id"]=="P452:"+old[i]["id"]
        assert features[r["registered_source_feature_id"]]["geometry"]["type"]=="MultiLineString"
    outer=d["main_road_records"][8:19]
    assert len(outer)==11
    assert [x["id"] for x in outer]==[f"O{i:02d}" for i in range(1,12)]
    assert all(x["registered_source_feature_id"] is None for x in outer)
    newer=d["main_road_records"][19:]
    assert [x["id"] for x in newer]==["X01","X02"]
    assert newer[0]["sourced_metrics"]["width_approx_m"]==34
    assert newer[0]["sourced_metrics"]["length_approx_m"]==2500
    assert newer[1]["sourced_metrics"]["neighborhood_gate_gap_approx_m"]==7.5
    assert "terrain-luo-northward-after-sui" in {x["id"] for x in terrain["records"]}
    inner=d["inner_city_ten_road_literature_summary"]
    assert len(inner["east_west"])==inner["east_west_count"]==5
    assert len(inner["north_south"])==inner["north_south_count"]==5
    assert all(x["registered_original_survey_polyline"] is None for x in inner["east_west"]+inner["north_south"])
    assert inner["exact_survey_to_old_eight_matched"] is False
    local=d["baima_local_ward_2024"]
    assert local["excavated_ward_streets_reported"]==6
    assert (local["local_ew_street_spacing_m"],local["local_ns_street_spacing_m"])==(40,86)
    assert local["extension_to_whole_outer_city_allowed"] is False
    assert d["ancient_luo_yi_geologic_trend_2024"]["phase_specific_516_528_polyline_verified"] is False
    assert d["northern_wei_east_yangqu_phase_controversy"]["not_a_confirmed_complete_field_dated_continuous_channel"]
    assert len(d["original_document_acquisition_queue"])==7
    assert all(not x["scaled_survey_plan_acquired"] for x in d["original_document_acquisition_queue"])
    assert d["coordinates_added"]==0
    assert d["verified_new_ancient_common_ground_controls"]==0
    assert d["historic_waterbody_polygons_added"]==0
    assert d["historic_full_road_polylines_added"]==0
    assert not d["approved_artistic_panorama_changed"]

def water_plate(d):
    root=svg(W,H,"古代河渠与园池：定性关系板，非地图")
    header(root,"P4.6 / HISTORIC WATER / 文献与考古分层",
           "北魏河渠有系统关系，精确古河线仍未取得",
           "这是一张文献水路关系图。各框的相对间距、连线和转折是排版，不是古代地理位置。")
    # Upper: phased river/engineering network -- intentionally schematic.
    box(root,64,222,800,475,"#ecf1ec","#c6d8c9")
    text(root,92,270,"西侧：千金堨、引水与多期改道",28,C["ink"],weight=700)
    text(root,99,331,"谷水／瀍水",27,"#427c76",weight=700)
    path(root,"M290 323 H401","#6a9890",4,"9 6")
    text(root,432,330,"千金堨",29,"#427c76",weight=700)
    text(root,98,384,"北魏重修；谷水、瀍水为重要水源",20,C["muted"])
    text(root,99,451,"湖沟故道  →  千金渠引水",23,"#546e61")
    text(root,99,504,"洛水枝渎重浚：学者研究提出的候选",21,"#956a45")
    text(root,99,560,"张方沟／西郭排水：沿郭关系有据",22,"#546e61")
    text(root,99,625,"渠堨与多期水流不保证同一时刻全部通水",19,"#956a45")
    box(root,900,222,834,475,"#ebf2f4","#c5d7dc")
    text(root,928,270,"东侧：城周阳渠、建春门水道",28,C["ink"],weight=700)
    text(root,936,334,"城北谷水 → 建春门石桥",25,"#447b96",weight=700)
    text(root,936,391,"城南水道 → 城东阳渠",25,"#447b96")
    text(root,936,449,"北支／南支：据《水经注》整理的解释",21,"#956a45")
    text(root,936,505,"魏晋宫城西墙渠：仅有局部剖面",21,C["muted"])
    text(root,936,558,"1997/1999洛水线：只允许作现代参考",21,"#9b6941")
    text(root,936,625,"没有已配准的北魏全流域古河道线",20,C["muted"])
    box(root,64,738,1670,565,"#fff","#d7e1d7")
    text(root,94,789,"湖池不能混为一湖：原典记录的是多个独立水体",30,C["ink"],weight=700)
    texts=[
      ("翟泉＝苍龙海","太仓南、华林园东，非天渊池"),
      ("华林园大海＝天渊池","园中主池、九华台与蓬莱山等关系"),
      ("玄武池","园中山北；不是天渊池别名"),
      ("流觞池／扶桑海","都堂附近不同池；石窦连通仅为古籍描述"),
      ("濛汜池","夏季有水、冬季涸；不可画常年湖"),
      ("碧海曲池／昭仪寺池","各归不同地点的文字关系"),
      ("永和里南北两池","两个水体，不画成一条南北长湖"),
      ("咸池／土山鱼池／景明三池","各有园林或寺院语境；原形与水面尺度未定")
    ]
    for i,(a,b) in enumerate(texts):
        x=94+(i%2)*795;y=841+(i//2)*104
        rect(root,x,y-25,744,89,"#f4f7f3","#e1e9df",1,7)
        text(root,x+16,y+4,a,23,"#3b7059",weight=700)
        text(root,x+16,y+39,b,18,C["muted"])
    footer(root,"34条水体／河渠／设施清单不等于34条已确定北魏水线。古代精确河湖轮廓现仍为0。")
    return root

def roads_plate(d):
    root=svg(W,H,"内城8项路迹与外郭9+2条大道研究状态")
    header(root,"P4.6 / MAIN STREETS / 干道审查",
           "八条旧图路迹，不等于九条外郭大道",
           "不同统计口径来自不同测绘/文献：8项P1遗址路迹、9条外郭御道、2条另见外路和新发掘。")
    box(root,60,220,810,955,"#fff","#d5e1d6")
    text(root,87,269,"A｜P1旧底图八项内城道路",29,"#3c7060",weight=700)
    for i,road in enumerate(d["main_road_records"][:8]):
        y=332+i*96
        text(root,98,y,road["id"],22,"#386a5a",weight=700)
        text(root,192,y,road["name"],24,C["ink"])
        text(root,194,y+36,road["scope"].split("；")[0][:27],16,C["muted"])
    box(root,908,220,830,955,"#fff","#d5e1d6")
    text(root,937,269,"B｜外郭九条御道（文史汇总）",29,"#8a6844",weight=700)
    for i,road in enumerate(d["main_road_records"][8:17]):
        y=330+i*82
        text(root,947,y,road["id"],21,"#947249",weight=700)
        text(root,1034,y,road["name"],23,C["ink"])
        text(root,1035,y+29,"缺可配准完整原测线路",15,C["muted"])
    text(root,942,1091,"另有：开阳门外、平昌门外两条大道",21,C["ink"])
    box(root,60,1210,1678,125,"#edf3ee","#c7d8ce")
    text(root,91,1246,"C｜2020西明—青阳大道：约2.5km / 34m，历多朝，报告有北魏车辙",22,"#315e51",weight=700)
    text(root,91,1300,"D｜2024里坊六条局部路，40/86m为路间距；2025坊门缺口7.5m≠干道宽",22,"#315e51")
    footer(root,"不同来源线路可能重叠，不能把8+9+2+2按21条互不相同街道简单相加。精确同线关系仍待原测绘图。")
    return root

def evidence_plate(d):
    root=svg(W,H,"城市骨架当前证据与地理控制门槛")
    header(root,"P4.6 / COMPLETENESS GATE",
           "哪些能定位、哪些能约束、哪些仍没有坐标？",
           "源图层、文字流向、考古局部测量和艺术全景为不同层次，不能自动互相升级。")
    groups=[
      ("0","北魏河湖完整GIS线／面","目前无可独立复核的全古河道或主要湖岸"),
      ("1","近现代洛水来源图折线","只属于1997航摄、1999实测底图；禁止北魏转用"),
      ("8","既有内城路迹源图几何","30项来源图中的8项概略道路，保留原样"),
      ("9","外郭御道勘探归纳","九条道路名称/方向有汇总，缺逐条可配准原测线"),
      ("2","2020、2025新增关键发掘","有实际路土/交会信息，原图共同控制未取得"),
      ("34","河湖水工设施第一轮登记","源名、分期与类型目录，湖面真实面积未核"),
      ("0","新获古地理共同控制点","古水网、内外郭道路仍需同基准实测端点")
    ]
    for i,(number,title,detail) in enumerate(groups):
        x=63+(i%2)*850;y=229+(i//2)*276
        if i==6:x=63
        w=810 if i<6 else 1669
        rect(root,x,y,w,252,"#ffffff","#d4e0d6",2,12)
        text(root,x+31,y+96,number,71,"#437f6a",weight=750)
        text(root,x+192,y+84,title,26,C["ink"],weight=700)
        text(root,x+193,y+132,detail,17,C["muted"])
        if i==6:break
    footer(root,"“尚未确定”不等于原址不存在，需补原始带尺图、时相、测线与共同控制后才能进入完整城市底图。")
    return root

def ledger_csv(data,key):
    out=io.StringIO()
    if key=="water_features":
        fields=["id","name","kind","position_tier","period","existing_entity_id","registered_source_feature_id",
                "ancient_geographic_line_or_polygon_verified","relative_topology_note","source_ids"]
    else:
        fields=["id","name","position_tier","scope","linked_prior_road_id","registered_source_feature_id",
                "ancient_full_route_georegistered","sourced_metrics","source_ids"]
    wr=csv.writer(out)
    wr.writerow(fields)
    for r in data[key]:
        wr.writerow([json.dumps(r.get(field),ensure_ascii=False) if isinstance(r.get(field),(list,dict))
                     else str(r.get(field)) if r.get(field) is not None else "" for field in fields])
    return out.getvalue()

def html_page(d,info):
    badge=lambda tier: "已定位近现代河道" if tier=="registered_modern_basemap_line" else "已有来源路迹" if tier=="preserved_source_map_geometry" else "待独立定位"
    source_lookup={s["id"]:s for s in d["source_registry"]}
    water_rows="".join(
      f'<tr data-row="{esc(w["id"])}" data-tier="{esc(w["position_tier"])}">'
      f'<td>{esc(w["id"])}</td><td><strong>{esc(w["name"])}</strong></td><td>{esc(w["kind"])}</td>'
      f'<td><span class="status unverified">{esc(badge(w["position_tier"]))}</span><p class="note">{esc(w["position_tier"])}</p></td>'
      f'<td>{esc(w["relative_topology_note"])}</td><td>{esc("、".join(w["source_ids"]))}</td></tr>'
      for w in d["water_features"]
    )
    road_rows="".join(
      f'<tr data-row="{esc(w["id"])}" data-tier="{esc(w["position_tier"])}">'
      f'<td>{esc(w["id"])}</td><td><strong>{esc(w["name"])}</strong></td>'
      f'<td><span class="status {" " if w["position_tier"]=="preserved_source_map_geometry" else "unverified"}">'
      f'{esc(badge(w["position_tier"]))}</span><p class="note">{esc(w["position_tier"])}</p></td>'
      f'<td>{esc(w["scope"])}</td>'
      f'<td>{esc("、".join(w["source_ids"]))}</td></tr>'
      for w in d["main_road_records"]
    )
    sources="".join(
       f'<li><strong>{esc(s["id"])}：</strong>'
       +(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["title"])}</a>'
         if s.get("url") else esc(s["title"]))
       +f'。{esc(s["caution"])}</li>'
       for s in d["source_registry"])
    gates=d["completion_gates"]
    tolist=lambda arr:"".join("<li>"+esc(s)+"</li>" for s in arr)
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>北魏洛阳 P4.6 · 河湖水系与城市主干道定位核查</title>
<meta name="description" content="北魏洛阳城市水网及主干道空间审计：34项河湖水工、8项旧图路迹、外郭九条御道与新考古证据的分期审查。">
<link rel="stylesheet" href="./prosperity-hydro-roads/style.css"></head>
<body><header><a href="./">盛时洛阳</a><nav>
<a href="./prosperity-street-clusters.html">上版P4.5.3</a><a href="#ledger">逐项核查表</a><a href="#gates">定位门槛</a><a href="#downloads">下载</a></nav></header>
<main>
<section><p class="kicker">P4.6 · 城市水网和主干道优先 · 首轮实证范围核对</p>
<h1>洛阳的河湖和主干道，还不能宣布全部确定。</h1>
<p class="lead">我们已经有多处真实道路遗址、水道钻探和古籍相对位置，但<strong>没有经过统一勘测控制的北魏河湖全网和完整主干道GIS</strong>。本批先把全部已找到的研究记录分层，避免未来建筑群和全景依赖不存在的精确地图。</p>
<div class="stats"><span>34项河湖水工名物（初查）</span><span>8项旧图道路折线</span>
<span>9条外郭大道勘探归纳</span><span>2020与2025新发掘</span><span>新古代地理控制 0</span></div>
<p class="warning"><strong>严禁混层：</strong>现代洛水已有来源图折线，但它不是北魏洛水；古代河渠的文献连通关系不是现代经纬度；湖泊的“位于某园内／某门外”不能反推实际水面边界；外郭9条御道不等于原P1的8条内城路迹。</p>
</section>
<section id="plates"><h2>01 · 证据图件与城市骨架</h2>
<div class="plates">
<figure><a href="./prosperity-hydro-roads/hydrology-topology.svg"><img src="./prosperity-hydro-roads/hydrology-topology.svg" alt="古代水道系统和华林园多个湖池的非地理证据板"></a><figcaption>古河渠的分期与园池名物：说明关系，不伪造河床与湖岸。</figcaption></figure>
<figure><a href="./prosperity-hydro-roads/roads-evidence.svg"><img src="./prosperity-hydro-roads/roads-evidence.svg" alt="内城八条旧来源路迹、外郭九条御道与2020/2025道路发掘分层对照"></a><figcaption>内外郭干道与新发掘按来源分层，不把不同统计口径直接相加。</figcaption></figure>
<figure><a href="./prosperity-hydro-roads/anchor-gates.svg"><img src="./prosperity-hydro-roads/anchor-gates.svg" alt="北魏河湖道路当前锚定程度和需要补原始测绘图的门槛"></a><figcaption>锚定完成度与缺失的共同测量控制。</figcaption></figure>
<figure><a href="./prosperity-hydro-roads/unaltered-source-layout.svg"><img src="./prosperity-hydro-roads/unaltered-source-layout.svg" alt="原P1已有地图源图30项几何的逐字节副本，不包含新增古河湖线"></a><figcaption>完全不变的P1来源图：能显示已登记遗址与近现代河道，不能代替古代全流域水文图。</figcaption></figure>
</div></section>
<section id="ledger"><h2>02 · 逐个查找水体和主干道</h2>
<p>搜索中文名称、分类、来源编号，或按已有空间依据过滤。列表中的“待定位”不是否定历史上存在，而是**本站还没有可复核的北魏地理边界或中心线**。</p>
<div class="tabs" role="group" aria-label="选择水系或主干道清单">
<button type="button" data-mode="water" aria-pressed="false">河流与湖泊 · 34项</button>
<button type="button" data-mode="roads" aria-pressed="false">主干道与发掘 · 21条来源记录</button></div>
<div data-table-panel="water">
<div class="toolbar"><input type="search" data-filter-search placeholder="搜索：天渊、阳渠、翟泉等" aria-label="筛选水系表">
<select data-tier-select aria-label="按水体证据状态筛选"><option value="all">全部证据类别</option>
<option value="registered_modern_basemap_line">只有近现代来源线</option>
<option value="documentary_relative_only">古籍相对位置</option>
<option value="excavated_local_unregistered">局部考古未配准</option>
<option value="reconstructed_topology_unregistered">学术重建拓扑未配准</option>
<option value="phase_conditional_topology">分期假说</option></select>
<span data-visible-count class="note">34项</span></div>
<div class="tablewrap"><table><thead><tr><th>编号</th><th>名称</th><th>类别</th><th>锚定状态</th><th>目前的证据／限制</th><th>来源</th></tr></thead><tbody>{water_rows}</tbody></table></div></div>
<div data-table-panel="roads">
<div class="toolbar"><input type="search" data-filter-search placeholder="搜索：西阳、铜驼、青阳、白马寺等" aria-label="筛选道路表">
<select data-tier-select aria-label="按道路证据状态筛选"><option value="all">全部证据类别</option>
<option value="preserved_source_map_geometry">已登记原来源图线</option>
<option value="external_survey_without_registered_line">外郭道路勘探汇总</option>
<option value="published_excavation_unregistered">新发掘未独立配准</option></select>
<span data-visible-count class="note">21项</span></div>
<div class="tablewrap"><table><thead><tr><th>编号</th><th>大道或道路</th><th>锚定状态</th><th>明确依据与局限</th><th>来源</th></tr></thead><tbody>{road_rows}</tbody></table></div></div>
<p>另据2023考古综述，内城主道为<strong>东西五条＋南北五条</strong>的文字目录，不等于旧来源图8项残线，仍缺逐条同址测线。2024白马寺邻近里坊出现<strong>六条局部道路</strong>，40米与86米为相邻道路间距，不能当成道路宽，也不能作为全外郭统一坊格。2024地质研究提示洛水北移、伊水合流位置变更；2026水利论文认为建春门北侧宽渠可能保留东汉旧层、北魏阳渠更可能在道路南侧，均待原测绘复核。</p>
</section>
<section id="gates"><h2>03 · 什么时候才能说“主骨架确定好了”？</h2>
<div class="pending">
<h3>水文地图完成条件</h3><ol>{tolist(gates["hydrology"])}</ol>
<h3>道路地图完成条件</h3><ol>{tolist(gates["roads"])}</ol>
<p>这两套条件落实之前，新建筑的空间位置仍只能使用已有遗址点、局部比例图或有据的文字方位，不允许从视觉全景恢复绝对坐标。</p></div>
</section>
<section id="originals"><h2>04 · 关键原测量图取得清单</h2>
<p>以下七类报告仍没有本项目可直接量读、带统一尺度与控制点的原始平面；取得这些资料是从“审查线索”升级为真正古代河湖与主干道地理底图的必要条件。</p>
<ol>{''.join('<li>'+esc(v["title"])+'：'+esc(v["target"])+'</li>' for v in d["original_document_acquisition_queue"])}</ol>
</section>
<section id="sources"><h2>04 · 原件、同行研究及边界</h2>
<ol>{sources}</ol>
<p>已核的2026年历史水利论文是研究解释而非新发掘统一测量图；2012年申遗图册包含1997/1999底图；2019、2020、2025的道路成果来自不同调查／发掘阶段，不可因同名或线条交叉在网页上就自动合并为连续古城路网。</p>
</section>
<section id="downloads"><h2>05 · 源数据与审阅包</h2>
<div class="downloads">
<a href="./downloads/prosperity-hydro-roads-p46-atlas.pdf">四页证据图册 PDF</a>
<a href="./downloads/prosperity-hydro-roads-p46-package.zip">完整研究包 ZIP</a>
<a href="./prosperity-hydro-roads/data.json">所有水体道路 JSON</a>
<a href="./prosperity-hydro-roads/water.csv">水体清单 CSV</a>
<a href="./prosperity-hydro-roads/roads.csv">主干道清单 CSV</a></div>
<p class="note">审核数据首轮来自现有339实体与可获取的正式考古、古籍和2026年论文；不是宣称已穷尽中国文献中的每条溪沟、湖塘，也没有把未测东西画成肯定存在的古代线路。</p>
</section>
<footer>P4.6 · source commit {esc(info["source_commit"][:10])} · <a href="./">返回已批准的北魏洛阳盛景首页</a></footer>
</main><script src="./prosperity-hydro-roads/app.js" defer></script></body></html>"""

def main():
    info=read(SITE/"build-info.json")
    release=read(SITE/"release.json")
    data=read(SRC)
    geo=read(GEO);terrain=read(TERRAIN);p452=read(P452);p453=read(P453)
    validate(data,geo,terrain,p452,p453,info)
    assert not (SITE/"prosperity-hydro-roads.html").exists()
    before=dict(info["files_sha256"])
    preserved={k:v for k,v in before.items() if k not in MUTABLE}
    assert all(sha(SITE/k)==v for k,v in preserved.items())
    OUT.mkdir(parents=True,exist_ok=True)
    for source,name in [("web/prosperity-hydro-roads.css","style.css"),("web/prosperity-hydro-roads.js","app.js")]:
        shutil.copyfile(ROOT/source,OUT/name)
    copy=OUT/"unaltered-source-layout.svg"
    shutil.copyfile(SITE/"prosperity/source-layout.svg",copy)
    assert sha(copy)==before["prosperity/source-layout.svg"]
    maps=[]
    for name,body in [
      ("hydrology-topology.svg",water_plate(data)),
      ("roads-evidence.svg",roads_plate(data)),
      ("anchor-gates.svg",evidence_plate(data))
    ]:
        file=OUT/name;write_svg(file,body)
        assert ET.parse(file).getroot().tag==f"{{{NS}}}svg"
        maps.append(file)
    maps.append(copy)
    (OUT/"water.csv").write_text(ledger_csv(data,"water_features"),encoding="utf-8-sig")
    (OUT/"roads.csv").write_text(ledger_csv(data,"main_road_records"),encoding="utf-8-sig")
    enriched=dict(data)
    enriched["build_reference"]={
       "version":VERSION,"source_commit":info["source_commit"],
       "prior_original_source_map_sha256":before["prosperity/source-layout.svg"],
       "original_map_copied_byte_identically":True,
       "ancient_water_or_road_geometric_points_added":0
    }
    dump(OUT/"data.json",enriched)
    pdf=SITE/"downloads/prosperity-hydro-roads-p46-atlas.pdf"
    pdf.parent.mkdir(parents=True,exist_ok=True)
    render_atlas(maps,pdf)
    page=SITE/"prosperity-hydro-roads.html"
    page.write_text(html_page(data,info),encoding="utf-8")
    (OUT/"README.md").write_text(
       "P4.6 城市骨架优先：34项首轮河湖水工及21条不去重的道路来源记录。\n"
       "P1 2012来源图逐字节复制；旧八条路、现代1997/1999洛水、外郭九条道路及新发掘各自独立。\n"
       "2026水利研究为历史水路拓扑推演，非新取得统一坐标。海和池没有画岸线。\n"
       "尚未全部确定：本阶段是实证核查底稿及待测控制点目录，而非完成全北魏GIS。\n",
       encoding="utf-8")
    # Link latest already-published study, and archive its exact HTML for audit.
    previous=SITE/"prosperity-street-clusters.html"
    old=previous.read_text(encoding="utf-8")
    marker='<footer>盛时洛阳 P4.5.3 ·'
    assert old.count(marker)==1
    archive=OUT/"history/prosperity-street-clusters-before-p46.html"
    archive.parent.mkdir(parents=True,exist_ok=True)
    archive.write_text(old,encoding="utf-8")
    insert=(
      '<section id="p46-first"><h2>新阶段P4.6：先锚定河湖与全城主干道</h2>'
      '<p>旧八条内城路迹、新考古大道、外郭九御道，以及河湖名物各自按证据状态查阅；不会把新关系当成古坐标。</p>'
      '<p><a href="./prosperity-hydro-roads.html">进入 P4.6 河湖与主干道锚定总审查 →</a></p></section>'
    )
    previous.write_text(old.replace(marker,insert+marker,1),encoding="utf-8")
    dump(OUT/"preservation.json",{
       "version":VERSION,"source_commit":info["source_commit"],"protected_unchanged":True,
       "protected_sha256":preserved,
       "prior_html_sha256":hashlib.sha256(old.encode("utf-8")).hexdigest(),
       "original_source_map_sha256":before["prosperity/source-layout.svg"],
       "new_historical_coordinates":0,"approved_h2_visual_unchanged":True
    })
    assert all(sha(SITE/k)==v for k,v in preserved.items())
    members={f"prosperity-hydro-roads/{f.relative_to(OUT)}":f for f in OUT.rglob("*") if f.is_file()}
    members["prosperity-hydro-roads.html"]=page
    members[f"downloads/{pdf.name}"]=pdf
    dump(OUT/"bundle-manifest.json",{"version":VERSION,"source_commit":info["source_commit"],
      "files_sha256":{name:sha(f) for name,f in members.items()}})
    members["prosperity-hydro-roads/bundle-manifest.json"]=OUT/"bundle-manifest.json"
    bundle=SITE/"downloads/prosperity-hydro-roads-p46-package.zip"
    with zipfile.ZipFile(bundle,"w",zipfile.ZIP_DEFLATED) as z:
        for name,f in members.items():z.write(f,name)
    release["extensions"]=sorted(set(release.get("extensions",[])+[VERSION]))
    release["prosperity_hydro_roads_version"]=VERSION
    release["current_milestone"]="盛时P4.6：河湖与内外郭主干路优先，证据分层与缺测骨架审计"
    dump(SITE/"release.json",release)
    info["prosperity_hydro_roads"]={
      "version":VERSION,"source_commit":info["source_commit"],
      "water_feature_records":len(data["water_features"]),
      "road_source_records":len(data["main_road_records"]),
      "registered_historical_water_polygons":0,
      "registered_historical_complete_road_lines":0,
      "modern_luo_source_reference_lines":1,
      "existing_inner_road_features_preserved":8,
      "outer_major_road_reports_pending_registration":9,
      "independent_ancient_common_controls_added":0,
      "atlas_pages":len(maps),"metadata":"prosperity-hydro-roads/data.json"
    }
    info["files_sha256"]={str(p.relative_to(SITE)):sha(p)
                           for p in sorted(SITE.rglob("*")) if p.is_file() and p.name!="build-info.json"}
    dump(SITE/"build-info.json",info)
    print(json.dumps(info["prosperity_hydro_roads"],ensure_ascii=False))

if __name__=="__main__":
    from prosperity_anchors_p461 import build as publish_source_readings
    from prosperity_south_p466 import build as publish_south
    from prosperity_water_p467 import build as publish_water
    from prosperity_water_p468 import build as publish_water_remainders
    from prosperity_gates_p465 import build as publish_gates
    from prosperity_field_p464 import build as publish_field
    from prosperity_corridors_p463 import build as publish_corridors
    from prosperity_network_p462 import build as publish_network

    main()
    publish_source_readings()
    publish_network()
    publish_corridors()
    publish_field()
    publish_gates()
    publish_south()
    publish_water()
    publish_water_remainders()
