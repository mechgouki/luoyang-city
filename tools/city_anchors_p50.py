#!/usr/bin/env python3
"""P5.0: Build honest water and trunk-road anchors before further Luoyang building infill.

Water network is a nonmetric, chronological research topology. Road '5+5'
are published synthesis names NOT matched 1:1 to P1's eight georeferenced
generalized remnants. Existing source map is copied byte-exact.
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
OUT=SITE/"city-anchors"
SRC=ROOT/"research/prosperity-v5/hydro-road-anchors-p50.json"
P452=ROOT/"research/prosperity-v4/road-functions-p452.json"
GEO=ROOT/"research/prosperity-v1/geographic-evidence.json"
ENT=ROOT/"data/entities.json"
TERRAIN=ROOT/"research/prosperity-v1/terrain-constraints.json"
VERSION="city-anchors-hydro-roads-p50"
MUTABLE={"prosperity-street-clusters.html","release.json","build-info.json"}
COL={"river":"#3e8396","river_diversion":"#3e8396","intake":"#628e75",
     "intake_candidate":"#a98c58","dam_and_canal":"#718c72","weir":"#718c72",
     "drain":"#56869a","moat":"#718c72","eastern_canal":"#4d789d",
     "eastern_drain":"#4d789d","reservoir":"#668c99",
     "excavated_multi_period":"#a38661","collective_pool_connectivity":"#a68c59",
     "excavation_stratigraphy":"#a68c59"}
def load(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def h(x):return html.escape(str(x),quote=True)
def validate(raw,p452,geo,ents,terrain,info):
    assert raw["version"]==VERSION
    assert raw["completion_status"].endswith("not_verified_complete_geographic_city_skeleton")
    assert geo["crs"]=="EPSG:4610"
    assert len(geo["features"])==30
    assert len(p452["road_segments"])==8
    assert p452["version"]=="prosperity-road-functions-p452"
    assert len(ents)==339
    assert info["prosperity_street_clusters"]["version"]=="prosperity-street-clusters-p453"
    assert load(SITE/"homepage/approval-v9.json")["hero"]["revision"]=="panorama-approved-v9"
    existing={e["id"]:e for e in ents}
    assert len(raw["water_components"])==15
    assert len(raw["historical_waterbody_entity_ids"])==11
    assert len(set(raw["historical_waterbody_entity_ids"]))==11
    for id in raw["historical_waterbody_entity_ids"]:
        assert id in existing and existing[id]["type"] in ("water","pond"),id
    for w in raw["water_components"]:
        assert w["ancient_516_528_metric_geometry"] is None
        assert w["shared_geodetic_control_count"]==0
        if w["old_entity_id"] is not None:
            assert w["old_entity_id"] in existing
    assert len(raw["hydrological_topology"])==10
    comp={x["id"] for x in raw["water_components"]}
    for edge in raw["hydrological_topology"]:
        assert edge["from"] in comp and edge["to"] in comp
        assert edge["ancient_geographic_polyline"] is None
        assert edge["draw_schematic_only"]
    oldids={x["feature_id"] for x in p452["road_segments"]}
    assert len(oldids)==8
    assert oldids==set(raw["roads"]["p1_old_remnant_feature_ids"])
    geoids={x["id"] for x in geo["features"]}
    assert oldids<=geoids
    assert len(raw["roads"]["inner_city_published_summary"]["ew"])==5
    assert len(raw["roads"]["inner_city_published_summary"]["ns"])==5
    assert raw["roads"]["outer_city"]["published_major_corridor_count"]==9
    assert raw["roads"]["outer_city"]["individual_old_original_survey_paths_acquired"]==0
    assert raw["roads"]["baimasi_local"]["new_roads_reported"]==6
    assert raw["roads"]["baimasi_local"]["local_ew_street_interval_m"]==40
    assert raw["roads"]["baimasi_local"]["local_ns_street_interval_m"]==86
    assert raw["roads"]["baimasi_local"]["extrapolation_to_citywide_not_allowed"] is True
    assert raw["evidence_policy"]["new_ancient_geographic_coordinates"]==0
    assert raw["evidence_policy"]["modern_luo_source_id"]=="geo-modern-luo-river"
    assert raw["evidence_policy"]["modern_luo_cannot_be_ancient"] is True
    assert raw["evidence_policy"]["exact_ancient_river_lines_registered"]==0
    assert raw["evidence_policy"]["homepage_modification_forbidden"]
    assert terrain["version"]=="prosperity-terrain-constraints-v1.0"
    assert len(terrain["records"])>=5
    return existing

def head(root,kicker,title,subtitle):
    text(root,60,60,kicker,21,"#587a69",weight=700)
    text(root,60,114,title,38,C["ink"],weight=700)
    text(root,60,157,subtitle,19,C["muted"])
    path(root,"M60 176H1740","#d3dfd5",2)

def water_topology(d):
    r=svg(1800,1450,"北魏洛阳P5水系拓扑假说：非地理定位示意")
    head(r,"P5.0  WATER / CHRONOLOGY","河谷自然水系 → 城西控水 → 城壕分流 → 城东调蓄",
         "每张卡只有来源命名与文献/考古分期；箭头为研究路径示意，不能当作河床折线。")
    stages=[
       [(90,241,"谷水／涧水 W03"),(90,390,"瀍水 W04"),(90,538,"古洛水 W01"),(90,687,"伊水 W02")],
       [(520,245,"湖沟 W05"),(520,408,"千金堨 W06"),(520,564,"引洛枝渎 W07（待核）")],
       [(968,247,"北/东/西城壕 W09"),(968,426,"西郭张方沟 W08")],
       [(1320,255,"东阳渠 W10"),(1320,429,"城东南谷水 W11"),(1320,607,"鸿池陂 W12")]
    ]
    stageColors=["#53859a","#6d937b","#7a9479","#5c849b"]
    for i,stage in enumerate(stages):
        for x,y,name in stage:
            rect(r,x,y, (365 if i<2 else 400),99,"#fff",stageColors[i],3,9)
            text(r,x+18,y+39,name,24,stageColors[i],weight=700)
            text(r,x+18,y+72,("历史河流/未定古槽" if i==0 else
                             "分期水利节点（非GIS）" if i==1 else
                             "部分钻探/多期图示" if i==2 else
                             "城东分洪/水道解释"),17,C["muted"])
    for y in (323,474,590):
        path(r,f"M458 {y}H509","#9eb6a4",3,"10 8")
    for y in (314,485):
        path(r,f"M895 {y}H953","#9eb6a4",3,"10 8")
    for y in (312,486):
        path(r,f"M1264 {y}H1307","#9eb6a4",3,"10 8")
    rect(r,77,823,1638,185,"#eff2e9","#c9d9cc",2,12)
    text(r,111,864,"三条不同性质的证据线不能合成一条全年常流的北魏河道",28,C["ink"],weight=700)
    for i,(label,sub) in enumerate([
        ("516–528 北魏盛时：千金堨、谷/瀍供水、城东阳渠有文献依据","阶段连通与真实岸线未有共同测量控制"),
        ("汉/魏晋旧渠：千秋门2022发现三条石渠及各时相水道","魏晋局部遗存 ≠ 北魏盛时每条都仍通水"),
        ("1997/1999 现代洛水：只有旧P1参考折线可按现代时层定位","2024地质研究表明洛水北迁，禁止倒套现代河槽")
    ])){
      text(r,114,912+i*32,label,20,i===1?"#9b704a":"#536c5f",weight=500)
    }
    rect(r,80,1053,1640,240,"#fff","#d4e0d9",2,11)
    text(r,110,1098,"关键学术分歧：建春门外的“道北宽渠”与“道南北魏阳渠”不可重叠入同一时相",23,"#a1794f",weight=700)
    for j,line in enumerate([
        "黄学超（2026）将御道北侧所见宽渠解释为较早东汉阶段；北魏阳渠趋向道南（论文复原）。",
        "现有仓库还没有该宽渠与北魏道南水道的原始分期测线，以及可比较的现场控制点。",
        "千秋门西南—东北石渠虽有考古发现，但出土地层为多时期，不可未经分期合并为北魏统一引水网。",
        "上面各卡连线均为非地理拓扑；河湖真实宽度、池岸、泥沙层年代和流量尚无法确定。"
    ]): text(r,111,1152+j*34,line,19,C["muted"])
    text(r,80,1394,"本图没有生成古代经纬坐标或河床中心线。参考：黄学超2026、洛阳申遗报告、2022千秋门水道、2024地质研究。",18,C["muted"])
    return r

def road_matrix(d):
    r=svg(1800,1450,"P5洛阳道路覆盖矩阵：8已有残线、5×2内城道路综述、9外郭大道待原测图")
    head(r,"P5.0  MAIN ROADS / COVERAGE","内城主街、外郭大道与里坊小路必须分三级核对",
         "图上列名来自公开考古综述，非本项目已注册的连续古代路网中心线。")
    inner=d["roads"]["inner_city_published_summary"]
    for x,name,items in [(58,"内城东西主街：综述5条",inner["ew"]),(920,"内城南北主街：综述5条",inner["ns"])]:
        rect(r,x,217,814,777,"#fff","#d5dfd6",2,11)
        text(r,x+24,263,name,29,"#315d50",weight=700)
        for i,item in enumerate(items):
            y=310+i*123
            rect(r,x+22,y,764,96,"#f7f9f5","#e1e7de",1,7)
            text(r,x+42,y+34,item["id"],22,"#537d66",weight=700)
            text(r,x+128,y+34,item["name"],20,C["ink"],weight=650)
            text(r,x+129,y+68,"尚未与原P1道路遗存逐条独立匹配",17,"#a08058")
    rect(r,60,1040,1680,250,"#eff3ed","#b7d0c1",2,12)
    text(r,91,1085,"项目已有：8项P1道路残段；外郭城：9条大路的综述线索（本仓库0条原测完整线）",25,C["ink"],weight=700)
    for i,line in enumerate([
        "白马寺局部：2024新见6条里坊路，40米/86米是局部街间距，不是全城路宽。",
        "2025：发现里坊南门及内部纵向十字街与西阳门外大道相交，是局部已发掘关系。",
        "主街总结5+5、外郭9、里坊6与来源图8项是不同尺度、不同统计口径，不能相加当已定位街道条数。",
        "不得从已经批准的洛阳艺术全景补出缺失路段、交叉口、桥位或里坊墙。"
    ]):text(r,92,1133+i*36,line,19,C["muted"])
    text(r,66,1394,"原始内外郭街道总平面与比例尺未取得共同地理控制，故本页不画合成十字网格。",19,C["muted"])
    return r

def lake_plate(d,entities):
    r=svg(1800,1450,"北魏洛阳宫苑水体与湖池位置登记，全部未取得核准岸线")
    head(r,"P5.0  PONDS / GARDENS","古籍有湖池名称与相对方位，不等于得到准确水面轮廓",
         "现有11项水体实体全部保留自己的史料/季节，既不拼接成宫苑一整片海，也不填新的地理水面。")
    items=[entities[i] for i in d["historical_waterbody_entity_ids"]]
    for idx,e in enumerate(items):
        row,col=divmod(idx,2)
        x=60+col*850
        y=215+row*185
        rect(r,x,y,810,160,"#fff","#d6e4db",2,9)
        text(r,x+22,y+40,f"{idx+1:02d}　{e['name']}",23,"#3b786a",weight=700)
        text(r,x+22,y+78,e["id"],18,C["muted"])
        quoted=e.get("source_quote","")
        # Never allow long quotes to spill into another item; a short
        # locator is already present in source data.json and HTML table.
        text(r,x+23,y+111,quoted[:26]+("…" if len(quoted)>26 else ""),18,"#60766a")
        text(r,x+23,y+139,"古水面尚无可核准岸线；不在GIS画池界",16,"#aa855c")
    rect(r,60,1333,1680,66,"#eff3ec","#bfd2c3",2,8)
    text(r,80,1375,"另需分开：景明寺三池、土山鱼池、城东南方湖/池、鸿池陂；“诸海”集合不是逐池直连证据。",20,C["ink"])
    return r

def csv_content(rows,fields):
    s=io.StringIO()
    writer=csv.writer(s)
    writer.writerow(fields)
    for item in rows:writer.writerow([item.get(k,"") if item.get(k) is not None else "" for k in fields])
    return s.getvalue()

def page(d,entities,info):
    components="".join(
        f'<tr data-water-type="{h(w["kind"])}"><td>{h(w["id"])}</td>'
        f'<td><strong>{h(w["name"])}</strong></td><td>{h(w["kind"])}</td>'
        f'<td>{h(w["evidence_summary"])}</td><td><span class="tag warn">古代精确线未核</span></td></tr>'
        for w in d["water_components"])
    wb="".join(
        f'<tr><td>{h(e["name"])}</td><td>{h(e["id"])}</td><td>{h(e["source_quote"])}</td>'
        f'<td><span class="tag warn">只有文献关系</span></td></tr>'
        for e in [entities[i] for i in d["historical_waterbody_entity_ids"]])
    additional="".join(
        f'<article><h3>{h(e["name"])}</h3><p>{h(e["note"])}</p></article>'
        for e in d["extra_lakes_and_pools"])
    road8="".join(f'<tr><td>{i+1}</td><td>{h(x)}</td><td>原P1概略遗存图线</td></tr>'
                  for i,x in enumerate(d["roads"]["p1_old_remnant_feature_ids"]))
    sources="".join(
       f'<li><a target="_blank" rel="noopener" href="{h(s["url"])}">{h(s["id"])}</a></li>'
       for s in d["sources"])
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>盛时洛阳 P5｜河湖和主干道城市骨架证据</title>
<meta name="description" content="整理北魏洛阳自然河流、城壕、阳渠、千金堨、宫苑湖池，以及内城五横五纵与外郭九道证据。">
<link rel="stylesheet" href="./city-anchors/style.css"></head>
<body><header><a href="./">盛时洛阳</a><nav><a href="./prosperity-road-functions.html">原道路残段</a><a href="./prosperity-street-clusters.html">文献方位</a><a href="#sources">来源</a></nav></header>
<main><section>
<p class="eyebrow">P5 · BLOCKING FOUNDATION / CITY SCALE</p>
<h1>先定河湖与主干道，再深化北魏洛阳的城市场景。</h1>
<p class="lead">这两项尚未全部定位。本专题在已有证据基础上登记水系15个主要对象、11项古籍水体实体、内城5横5纵的综述名录、外郭9条大道研究线索和旧来源图8项道路残段，并明确区分时层与测量缺口。</p>
<div class="stats"><span>15项河渠/控水对象</span><span>11个已登记湖池实体</span><span>内城道路综述 5+5</span><span>外郭主道线索 9</span><span>原P1已有路段 8</span><span>新的古坐标 0</span></div>
<div class="critical"><strong>目前不能说河流、湖岸与大路已经全部确定。</strong>唯一现有水线GIS参考来自1997航摄/1999测量的现代洛水，绝不将其投到516—528年北魏时层。不同年代渠线、学术复原图和旧发掘遗存都须提供独立测线与共同地理控制，才能升格为真正的城市骨架。</div>
</section>
<section id="evidence"><h2>01 · 分开查看水系与道路骨架</h2>
<div class="switch" role="group" aria-label="选择城市骨架研究类别">
<button type="button" data-section="hydro" aria-pressed="false">水系／河湖</button>
<button type="button" data-section="roads" aria-pressed="false">道路／主干街</button></div>
<article class="panel" data-panel="hydro">
<figure class="art"><img src="./city-anchors/water-topology.svg" alt="北魏洛阳河流、湖沟、千金堨、城壕、东阳渠及鸿池陂的分期非地理拓扑示意"><figcaption>本图只有水流系统的“关系假设”，不按比例、位置或历史流量绘河床。特别将建春门御道南北两侧渠道的时代争议保留下来。</figcaption></figure>
<h3>15项主要河渠与控水结构</h3>
<div class="tablewrap"><table><thead><tr><th>ID</th><th>对象</th><th>类别</th><th>现有认识／约束</th><th>定位状态</th></tr></thead><tbody>{components}</tbody></table></div>
<h3>湖池：原项目中的11个有名称实体</h3>
<figure class="art"><img src="./city-anchors/lake-evidence.svg" alt="11项北魏洛阳宫苑湖池水体文献清单，均没有独立岸线测量"><figcaption>其中昭仪寺池不能与翟泉合一，濛汜池为季节性水体；凡此诸海不是每两池都直接连通。</figcaption></figure>
<div class="tablewrap"><table><thead><tr><th>水体名称</th><th>原实体ID</th><th>史料现有文字</th><th>岸线状态</th></tr></thead><tbody>{wb}</tbody></table></div>
<div class="notes">{additional}</div></article>
<article class="panel" data-panel="roads">
<figure class="art"><img src="./city-anchors/road-matrix.svg" alt="内城五横五纵、外郭九道以及白马寺局部六条里坊道路的证据覆盖矩阵"><figcaption>五横五纵来源为公开考古综述，外郭九道同为已发表研究线索；旧P1八条残段尚未建立完整一对一匹配。</figcaption></figure>
<h3>已有P1来源图中的8项道路遗存</h3>
<div class="tablewrap"><table><thead><tr><th>序号</th><th>原图标识</th><th>来源性质</th></tr></thead><tbody>{road8}</tbody></table></div>
<p>2024年白马寺附近里坊发掘另发现6条局部街路，其横向道路间距40米、纵向道路间距86米。这些数字是<strong>局部道路间距</strong>，不是道路宽度，更不是整座北魏洛阳的统一街区尺度。2025年确认的坊门与西阳门外大道交会也属于局部发掘位置。</p>
<p>铜驼街来源图记现存段约1650米、宽40—65米；**不应将这一处的宽度套给别的道路**，更不能仅凭同在宫前便认作古籍御道全线。</p></article>
</section>
<section id="original"><h2>02 · 唯一可在现有来源图上直接对照的地理工作图</h2>
<figure class="art"><img src="./city-anchors/source-layout-unchanged.svg" alt="P1原始2012来源图城市几何，保留1997/1999现代洛水及8个来源道路残段，没有北魏古河湖新线"><figcaption>来源图原字节复制：已有遗址点、旧道路片段与现代洛水参考；这不是新增的北魏河湖、池岸和街道位置。任何未绘河道和古街路都不许按空白自造。</figcaption></figure>
</section>
<section id="gap"><h2>03 · 哪些是决定城市骨架前必须补齐的原始资料？</h2>
<div class="notes">{''.join(f'<article><span class="tag">优先级 {x["priority"]}</span><h3>{h(x["document"])}</h3><p>{h(x["goal"])}</p><p class="muted">目前尚无统一比例尺／共同地面控制的原测图可直接套入项目</p></article>' for x in d["acquisition_queue"])}</div>
<p>本阶段的成果是让缺口变得清楚、可审查。后续要实际获得古代路线的测线端点与时层，才能升级某一具体河段或主街到可定位范围；不能使用“图源已找到”代替“测绘控制已核准”。</p></section>
<section id="sources"><h2>04 · 研究依据</h2><p>本轮新增的2026年水利综合研究、2024年古河道地质论文、2022年宫城水道考古和2024—2025年白马寺道路发掘成果，均以发表资料分层标注。转载不是新的考古独立样本，学者绘出的示意流路不等于现场GPS测线。</p>
<p><a href="https://www.sohu.com/a/1082362449_121124389">阅读2026水利研究全文公开转载</a> · <a href="https://www.lsdlyj.com.cn/CN/10.20166/j.issn.2096-6822.L20230083">2024河道地质论文</a></p><p>全部来源索引：{', '.join(sources)}</p></section>
<section id="downloads"><h2>05 · 研究成果下载</h2><div class="downloads">
<a href="./downloads/city-anchors-p50-atlas.pdf">四页图册 PDF</a>
<a href="./downloads/city-anchors-p50-package.zip">完整研究包 ZIP</a>
<a href="./city-anchors/data.json">完整证据 JSON</a>
<a href="./city-anchors/water-inventory.csv">水系清单 CSV</a>
<a href="./city-anchors/roads-register.csv">道路清单 CSV</a></div>
<p class="muted">P5是城市骨架的研究性基线：已确认的资料范围有边界；没有宣称“所有古河湖与道路已测量完成”。已批准的首页全景不会被这批档案替换。</p></section>
<footer>P5.0 · 发布提交 {h(info["source_commit"][:10])} · <a href="./">返回北魏洛阳首页</a></footer>
</main><script src="./city-anchors/app.js" defer></script></body></html>"""

def build():
    data=load(SRC)
    info=load(SITE/"build-info.json")
    release=load(SITE/"release.json")
    ents=load(ENT)
    byid=validate(data,load(P452),load(GEO),ents,load(TERRAIN),info)
    assert not (SITE/"city-anchors.html").exists()
    previous=dict(info["files_sha256"])
    protected={k:v for k,v in previous.items() if k not in MUTABLE}
    assert all(sha(SITE/k)==v for k,v in protected.items())
    OUT.mkdir(parents=True,exist_ok=True)
    for source,name in [("web/city-anchors-p50.css","style.css"),("web/city-anchors-p50.js","app.js")]:
        shutil.copyfile(ROOT/source,OUT/name)
    annotated={**data,
      "waterbody_entity_evidence":[{
          "id":i,"name":byid[i]["name"],"type":byid[i]["type"],
          "original_quote":byid[i]["source_quote"],
          "original_ref":byid[i]["source_ref"],
          "registered_ancient_shoreline":False
      } for i in data["historical_waterbody_entity_ids"]],
      "baseline_source_map_asset":"prosperity/source-layout.svg",
      "baseline_source_map_sha256":previous["prosperity/source-layout.svg"]}
    dump(OUT/"data.json",annotated)
    (OUT/"water-inventory.csv").write_text(
        csv_content(data["water_components"],["id","name","old_entity_id","kind","evidence_summary"]),encoding="utf-8-sig")
    roadrows=data["roads"]["inner_city_published_summary"]["ew"]+data["roads"]["inner_city_published_summary"]["ns"]
    (OUT/"roads-register.csv").write_text(
        csv_content(roadrows,["id","name"]),encoding="utf-8-sig")
    figs=[]
    for file,image in [("water-topology.svg",water_topology(data)),
                       ("road-matrix.svg",road_matrix(data)),
                       ("lake-evidence.svg",lake_plate(data,byid))]:
        p=OUT/file;write_svg(p,image);figs.append(p)
        assert ET.parse(p).getroot().tag==f"{{{NS}}}svg"
    old_source=SITE/"prosperity/source-layout.svg"
    copied=OUT/"source-layout-unchanged.svg"
    shutil.copyfile(old_source,copied)
    assert sha(old_source)==sha(copied)
    figs.append(copied)
    (SITE/"downloads").mkdir(exist_ok=True)
    pdf=SITE/"downloads/city-anchors-p50-atlas.pdf"
    render_atlas(figs,pdf)
    pagefile=SITE/"city-anchors.html"
    pagefile.write_text(page(data,byid,info),encoding="utf-8")
    (OUT/"README.md").write_text(
      "P5: hydrological source/phase topology and major roads coverage, not a completed ancient GIS.\n"
      "One old source-map line is modern 1997/1999 Luo, not Northern Wei; historical rivers and lakes lack registered ancient centerlines/shorelines.\n"
      "Inner 5EW+5NS and outer 9 from published summaries do not match 8 P1 fragments 1:1; Baima 6 local ward streets separate.\n"
      "Original map copied byte-identical and H2 approved panorama unchanged.\n",encoding="utf-8")
    previous_page=SITE/"prosperity-street-clusters.html"
    existing=previous_page.read_text(encoding="utf-8")
    marker="<footer>盛时洛阳 P4.5.3 ·"
    assert existing.count(marker)==1
    archive=OUT/"history/prosperity-street-clusters-before-p50.html"
    archive.parent.mkdir(exist_ok=True)
    archive.write_text(existing,encoding="utf-8")
    add=('<section id="p50-blocking"><h2>城市骨架优先：河湖、渠道与主干道路来源图审查</h2>'
         '<p>本研究线现在优先于继续增添建筑，核准古河和主街之前不补古城空白处。</p>'
         '<p><a href="./city-anchors.html">进入P5城市河湖与道路骨架研究 →</a></p></section>')
    previous_page.write_text(existing.replace(marker,add+marker,1),encoding="utf-8")
    dump(OUT/"preservation.json",{
       "version":VERSION,"source_commit":info["source_commit"],
       "all_prior_protected_unchanged":True,"protected_sha256":protected,
       "source_map_original_sha256":sha(old_source),
       "original_p453_html_sha256":hashlib.sha256(existing.encode()).hexdigest(),
       "new_ancient_coordinates":0,"homepage_hero_still":"panorama-approved-v9"})
    assert all(sha(SITE/k)==v for k,v in protected.items())
    files={f"city-anchors/{p.relative_to(OUT)}":p for p in OUT.rglob("*") if p.is_file()}
    files["city-anchors.html"]=pagefile
    files[f"downloads/{pdf.name}"]=pdf
    dump(OUT/"bundle-manifest.json",{"version":VERSION,"source_commit":info["source_commit"],
          "files_sha256":{k:sha(v) for k,v in files.items()}})
    files["city-anchors/bundle-manifest.json"]=OUT/"bundle-manifest.json"
    bundle=SITE/"downloads/city-anchors-p50-package.zip"
    with zipfile.ZipFile(bundle,"w",zipfile.ZIP_DEFLATED) as z:
        for name,file in files.items():z.write(file,name)
    release["extensions"]=sorted(set(release.get("extensions",[])+[VERSION]))
    release["city_anchors_version"]=VERSION
    release["current_milestone"]="P5 城市骨架优先：河湖分期证据与主干道完整性审查"
    dump(SITE/"release.json",release)
    info["city_anchors"]={
      "version":VERSION,"source_commit":info["source_commit"],
      "water_components":len(data["water_components"]),
      "waterbody_named_entities":len(data["historical_waterbody_entity_ids"]),
      "p1_road_remnants":8,"inner_main_road_summary":10,"outer_major_road_summary":9,
      "atlas_pages":4,"approved_ancient_geo_controls":0,
      "complete_historical_water_network":False,
      "complete_georeferenced_trunk_road_network":False,
      "original_source_map_sha256":sha(copied),
      "metadata":"city-anchors/data.json"}
    info["files_sha256"]={str(p.relative_to(SITE)):sha(p)
                          for p in sorted(SITE.rglob("*")) if p.is_file() and p.name!="build-info.json"}
    dump(SITE/"build-info.json",info)
    print(json.dumps(info["city_anchors"],ensure_ascii=False))
if __name__=="__main__":
    build()
