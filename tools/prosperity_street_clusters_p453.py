#!/usr/bin/env python3
"""P4.5.3: three source-graded qualitative city clusters, NO historical GIS placement.

Two independent manuscript-relation plates plus a third, verbatim retained
P4.5.1 source-geographic map. All edges are relations, never routing geometry.
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
OUT=SITE/"prosperity-street-clusters"
VERSION="prosperity-street-clusters-p453"
SRC=ROOT/"research/prosperity-v4/street-clusters-p453.json"
B1=ROOT/"research/dual-b1/decisions.json"
B7=ROOT/"research/dual-b7/luonan-river-markets.json"
B8=ROOT/"research/dual-b8/cross-batch-review.json"
P1=ROOT/"research/prosperity-v1/text-review.json"
P451=ROOT/"research/prosperity-v4/city-distribution-p451.json"
P452=ROOT/"research/prosperity-v4/road-functions-p452.json"
GEO=ROOT/"research/prosperity-v1/geographic-evidence.json"
ENT=ROOT/"data/entities.json"
MUTABLE={"prosperity-road-functions.html","release.json","build-info.json"}
GRADES={"A":"#3b806a","C":"#a27d45"}
RELATIONS={
"west_of":"在其西","east_of":"在其东",
"north_of":"在其北","south_of":"在其南",
"outside":"位于门外","on":"位于其上","within":"属于其内"}
SLUGS={"K01":"palace-street","K02":"jianchun-stones","K03":"south-bridge-market"}

def read(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def h(s):return html.escape(str(s),quote=True)

def validate(d,b1,b7,b8,p1,p451,p452,geo,entities,info):
    assert d["version"]==VERSION
    assert len(d["clusters"])==3
    assert p451["version"]=="prosperity-city-distribution-p451"
    assert p452["version"]=="prosperity-road-functions-p452"
    assert info["prosperity_road_functions"]["version"]=="prosperity-road-functions-p452"
    assert info["homepage_approved_v9"]["hero_revision"]=="panorama-approved-v9"
    ids={x["id"] for x in entities}
    assert len(ids)==len(entities)==339
    g={x["id"]:x for x in geo["features"]}
    assert len(g)==30
    srcs={
       "P1":{x.get("legacy_title") for x in p1["records"]},
       "B1":{x["id"] for x in b1["decisions"]},
       "B7":{x["id"] for x in b7["evidence"]},
       "B8":{x["id"] for x in b8["records"]}
    }
    for c in d["clusters"]:
        assert c["non_geographic"] is True
        nodes={n["id"]:n for n in c["nodes"]}
        assert len(nodes)==len(c["nodes"])
        assert set(nodes)<=ids
        for n in c["nodes"]:
            if n["feature_id"] is not None:
                assert n["feature_id"] in g
                # The source-map source ID is already old; never derive
                # a new architectural footprint from its symbol corners.
                assert n["feature_id"] not in ("geo-modern-luo-river",)
        for e in c["edges"]:
            assert e["subject"] in nodes and e["object"] in nodes
            assert e["predicate"] in RELATIONS
            assert e["grade"] in ("A","C")
            assert e["geographic_line_allowed"] is False
            record=e["source_record"]
            if record.startswith(("B1:","B7:","B8:")):
                prefix,key=record.split(":",1)
            else:
                prefix,key="P1",record
            assert key in srcs[prefix],record
            assert e["quote"] and e["scope"]
    edges=[x for c in d["clusters"] for x in c["edges"]]
    assert len(edges)==17
    assert len([x for x in edges if x["grade"]=="A"])==16
    assert len([x for x in edges if x["grade"]=="C"])==1
    assert d["audit"]["direct_edges"]==16
    assert d["audit"]["interpretive_edges"]==1
    assert d["audit"]["documentary_entity_ids"]==len({n["id"] for c in d["clusters"] for n in c["nodes"]})==20
    assert d["audit"]["new_ancient_wgs84_points"]==0
    assert d["audit"]["existing_source_geometry_modified"] is False
    assert d["audit"]["ancient_river_channel_constructed"] is False
    assert d["audit"]["historical_population_density_estimated"] is False
    assert d["audit"]["homepage_visual_changed"] is False
    assert d["diagram_contract"]["new_historical_coordinates_added"]==0
    for item in d["spatial_index_references"]:
        assert item["feature_id"] in g and item["entity_id"] in ids
    assert read(SITE/"homepage/approval-v9.json")["hero"]["revision"]=="panorama-approved-v9"
    return {e["id"]:e for e in edges}

def relation_plate(c):
    root=svg(1800,1370,c["title"]+" · 历史文字关系图，非地理点")
    text(root,66,59,"盛时洛阳 · P4.5.3 · 从文献中拆出关系，不从美术中生成位置",22,"#5c7f6b",weight=700)
    text(root,66,119,c["title"],36,C["ink"],weight=700)
    text(root,66,162,"以下每行是一次文献关系陈述；左右、上下行只是排版；不是历史坐标、路线或距离。",18,C["muted"])
    path(root,"M66 185H1734","#d7e1d8",2)
    names={x["id"]:x["name"] for x in c["nodes"]}
    for i,e in enumerate(c["edges"]):
        y=210+i*127
        rect(root,70,y,1655,116,"#ffffff","#d3dfd6",2,9)
        col=GRADES[e["grade"]]
        rect(root,90,y+19,57,50,col,col,1,6)
        text(root,118,y+53,e["grade"],24,"#fff","middle",700)
        text(root,167,y+42,names[e["subject"]],24,C["ink"],weight=650)
        text(root,677,y+43,RELATIONS[e["predicate"]]+" · 文献关系",22,col,weight=650)
        text(root,1113,y+43,names[e["object"]],24,C["ink"],weight=650)
        path(root,f"M590 {y+40}H645",col,3)
        path(root,f"M1033 {y+40}H1084",col,3)
        text(root,168,y+93,e["quote"],19,"#63766a")
        text(root,1642,y+93,e["source_record"],17,col,"end",600)
    if len(c["edges"])<8:
        yy=220+len(c["edges"])*127
        text(root,82,yy+41,"阶段限制：本图只表达报告中的相对关系；不将位置靠近误当同体或新的街道路网。",21,"#8f714c")
        for j,n in enumerate(c["uncertainty_notes"][:4]):
            text(root,82,yy+91+j*37,"· "+n,18,C["muted"])
    text(root,70,1329,"A=原文明确的定性关系 · C=跨句或编者工作解释 · 所有边均非GIS测量边；未重新定位古洛水、院墙、屋顶。",19,C["muted"])
    return root

def edges_csv(d):
    t=io.StringIO()
    wr=csv.writer(t)
    wr.writerow(["edge_id","cluster_id","subject_entity_id","predicate","object_entity_id","evidence_grade",
                 "source_record","original_excerpt","scope","is_geospatial_polyline"])
    for c in d["clusters"]:
        for e in c["edges"]:
            wr.writerow([e["id"],c["id"],e["subject"],e["predicate"],e["object"],e["grade"],e["source_record"],e["quote"],e["scope"],"false"])
    return t.getvalue()

def sources_csv(d):
    stream=io.StringIO()
    wr=csv.writer(stream)
    wr.writerow(["cluster_id","node_id","name","kind","original_source_feature_id","new_absolute_location"])
    for c in d["clusters"]:
        for n in c["nodes"]:
            wr.writerow([c["id"],n["id"],n["name"],n["role"],n["feature_id"] or "","false"])
    return stream.getvalue()

def page(d,info):
    tabs="".join(
      f'<button type="button" data-cluster="{h(c["id"])}" aria-controls="cluster-{h(c["id"])}" aria-pressed="false">'
      f'{h(c["id"])}　{h(c["title"].split("：")[0])}</button>'
      for c in d["clusters"])
    groups=""
    for c in d["clusters"]:
        rows="".join(
          f'<tr class="relation-row" data-evidence-grade="{h(e["grade"])}">'
          f'<td><span class="evidence grade-{h(e["grade"])}">{h(e["grade"])}</span></td>'
          f'<td>{h(next(n["name"] for n in c["nodes"] if n["id"]==e["subject"]))}</td>'
          f'<td>{h(RELATIONS[e["predicate"]])}</td>'
          f'<td>{h(next(n["name"] for n in c["nodes"] if n["id"]==e["object"]))}</td>'
          f'<td>{h(e["source_record"])} · {h(e["scope"])}</td></tr>'
          for e in c["edges"])
        cautions="".join(f'<li>{h(x)}</li>' for x in c["uncertainty_notes"])
        groups+=(
          f'<article id="cluster-{h(c["id"])}" class="cluster" data-cluster-panel="{h(c["id"])}">'
          f'<h3>{h(c["title"])}</h3>'
          f'<p>{h(c["reading_scope"])}</p>'
          f'<figure><img src="./prosperity-street-clusters/{SLUGS[c["id"]]}.svg" '
          f'alt="{h(c["title"]+"关系证据板，不可用作已配准古代地图")}">'
          '<figcaption>箭头代表原典叙述中的主谓关系，不是可导航道路、建筑立面或统一米尺空间图。</figcaption></figure>'
          '<div class="detail-table"><table><thead><tr><th>证据</th><th>主体</th><th>关系</th>'
          '<th>参照对象</th><th>原资料与解释范围</th></tr></thead>'
          f'<tbody>{rows}</tbody></table></div>'
          f'<div class="readnote"><strong>不能据此补画：</strong><ul>{cautions}</ul></div></article>'
        )
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>盛时洛阳 P4.5.3｜宫前、建春、洛南三个文献建筑关系群</title>
<meta name="description" content="三组洛阳城道路与建筑方位证据，16条直接关系与1条条件解释，不伪造历史GIS坐标。">
<link rel="stylesheet" href="./prosperity-street-clusters/style.css"></head>
<body><header><a href="./">盛时洛阳</a><nav>
<a href="./prosperity-road-functions.html">P4.5.2 道路骨架</a>
<a href="./prosperity-city-distribution.html">P4.5.1 建筑来源图</a><a href="#download">资料包</a></nav></header>
<main><section>
<p class="eyebrow">P4.5.3 · 分开“直接明文”“叙述解释”“已有来源地图”</p>
<h1>已知哪些建筑在道路两侧，比先画满全城民居更重要。</h1>
<p class="lead">依据先前已校读的《洛阳伽蓝记》卷一至卷三及B1、B7、B8、P1研究档案，整理宫前御道、建春门两石桥及洛南市场三个关系组。复用既有20个不同实体ID，记录16条直接文字关系与1条需条件解释的关系。</p>
<div class="stats"><span>3组道路建筑关系</span><span>20个已登记实体</span><span>16条直接关系</span><span>1条条件解释</span><span>新增古址坐标 0</span></div>
<p class="warning"><strong>这不是已经完成地理定位的院墙、道路或坊里。</strong>图上的箭头只说明古籍文本方位及从属；文献一里、四里不转换成地图米数。已批准的北魏洛阳全景是视觉层，不提供考古测量坐标。</p>
</section>
<section id="relations"><h2>01 · 三组局部城市关系</h2>
<p>切换场景及证据等级。A表示原文明确的定性关系，C表示需解释的文献承接；二者都不意味着新的地理配准。</p>
<div class="tabs" role="group" aria-label="选择历史建筑群">{tabs}</div>
<div class="filters" role="group" aria-label="关系证据等级过滤">
<strong>显示证据：</strong>
<button type="button" data-grade="all" aria-pressed="false">全部</button>
<button type="button" data-grade="A" aria-pressed="false">直接明文 A</button>
<button type="button" data-grade="C" aria-pressed="false">条件解释 C</button></div>
{groups}
</section>
<section id="index"><h2>02 · 与已有遗址来源图分开核对</h2>
<figure class="source-index"><img src="./prosperity-street-clusters/source-index-unchanged.svg"
alt="P4.5.1已有四个来源图点及30项原始几何保持不变">
<figcaption>本图是P4.5.1既有地理工作图的原样副本；并未将上方三组文字关系绘成新的古代道路点线，也没有以近现代河道识别北魏水系。</figcaption></figure>
<p><a href="./prosperity-city-distribution.html">查看P4.5.1建筑位置与台基尺寸的独立证据层</a>。该图只有来源地图已存在的概化建筑参照，国子学、两卫府、永桥等文本对象还没有足以复原其真实建筑足迹的共同测绘控制。</p></section>
<section id="sources"><h2>03 · 文献与分期约束</h2>
<p>宫前官署：<a href="https://deerpark.app/cbeta/B0077/1">卷一</a>的原句给出永宁寺御道西、左卫府道东及官署南向顺序；太尉府在御道西仍是已有研究的条件性文本解读。建春桥梁：<a href="https://deerpark.app/cbeta/B0077/2">卷二</a>记第一石桥527年颓坏、另一东石桥南北方向及建阳/绥民两里位于桥北大道两侧。洛南：<a href="https://deerpark.app/cbeta/B0077/3">卷三</a>记宣阳门外四里至永桥，以及四通市在洛水南；卷二归正里鱼鳖巷市不得与四通市合并。</p>
<p>原始发掘带尺图未取得共用控制之前，所有建筑群只能作为可追溯的方位关系图，不据此生成北魏街区建筑密度、完整市场区、多边形坊墙、古桥路线或屋顶高度。</p></section>
<section id="download"><h2>04 · 证据表、图册与完整研究包</h2>
<div class="downloads">
<a href="./downloads/prosperity-street-clusters-p453-atlas.pdf">四页图册 PDF</a>
<a href="./downloads/prosperity-street-clusters-p453-package.zip">完整研究包 ZIP</a>
<a href="./prosperity-street-clusters/data.json">来源及关系 JSON</a>
<a href="./prosperity-street-clusters/edges.csv">17条关系 CSV</a>
<a href="./prosperity-street-clusters/nodes.csv">20个对象 CSV</a>
</div><p class="muted">图册第4页为P4.5.1来源几何参考图的原样副本。更详尽的研究限度见该版数据及原《洛阳伽蓝记》段落记录。</p></section>
<footer>盛时洛阳 P4.5.3 · 研究提交 {h(info["source_commit"][:10])} · <a href="./">返回已批准的宏伟洛阳首页</a></footer>
</main><script src="./prosperity-street-clusters/app.js" defer></script></body></html>"""

def main():
    info=read(SITE/"build-info.json");release=read(SITE/"release.json")
    d=read(SRC)
    validate(d,read(B1),read(B7),read(B8),read(P1),read(P451),read(P452),
             read(GEO),read(ENT),info)
    assert not (SITE/"prosperity-street-clusters.html").exists()
    original=info["files_sha256"].copy()
    protected={name:value for name,value in original.items() if name not in MUTABLE}
    assert all(sha(SITE/name)==v for name,v in protected.items())
    OUT.mkdir(parents=True,exist_ok=True)
    for source,target in [("web/prosperity-street-clusters.css","style.css"),
                           ("web/prosperity-street-clusters.js","app.js")]:
        shutil.copyfile(ROOT/source,OUT/target)
    dump(OUT/"data.json",d)
    (OUT/"edges.csv").write_text(edges_csv(d),encoding="utf-8-sig")
    (OUT/"nodes.csv").write_text(sources_csv(d),encoding="utf-8-sig")
    illustrations=[]
    for c in d["clusters"]:
        p=OUT/(SLUGS[c["id"]]+".svg")
        write_svg(p,relation_plate(c));illustrations.append(p)
        assert ET.parse(p).getroot().tag==f"{{{NS}}}svg"
    index_original=SITE/"prosperity-city-distribution/grounded-distribution.svg"
    ref=OUT/"source-index-unchanged.svg"
    shutil.copyfile(index_original,ref)
    assert sha(ref)==sha(index_original)
    assert len(ET.parse(ref).getroot().findall(".//{"+NS+"circle"))>=4
    illustrations.append(ref)
    (SITE/"downloads").mkdir(exist_ok=True)
    pdf=SITE/"downloads/prosperity-street-clusters-p453-atlas.pdf"
    render_atlas(illustrations,pdf)
    pagefile=SITE/"prosperity-street-clusters.html"
    pagefile.write_text(page(d,info),encoding="utf-8")
    (OUT/"README.md").write_text(
        "P4.5.3：三个古籍局部建筑关系群，16直接关系+1条件性文本解释。所有位置为非地理示意。\n"
        "第4页来源图按字节复制P4.5.1原有来源地理SVG；没有通过箭头补古代道路。\n"
        "新增古址坐标0、坊墙面积0、历史屋顶古高0；已批准H2首页视觉未改。\n",encoding="utf-8")
    previous=SITE/"prosperity-road-functions.html"
    content=previous.read_text(encoding="utf-8")
    archive=OUT/"history/prosperity-road-functions-before-p453.html"
    archive.parent.mkdir(exist_ok=True)
    archive.write_text(content,encoding="utf-8")
    marker="<footer>盛时洛阳 P4.5.2 ·"
    assert content.count(marker)==1
    addition=(
      '<section id="p453-next"><h2>新研究 P4.5.3：宫前、建春门与洛南三个局部关系群</h2>'
      '<p>从道路来源图走向方位关系：区分16条原文明示边和1条条件解释；均不生成新古代坐标。</p>'
      '<p><a href="./prosperity-street-clusters.html">打开 P4.5.3 古籍建筑关系专题 →</a></p>'
      '</section>'
    )
    previous.write_text(content.replace(marker,addition+marker,1),encoding="utf-8")
    dump(OUT/"preservation.json",{
        "version":VERSION,"source_commit":info["source_commit"],"protected_files":protected,
        "protected_unchanged":True,
        "source_index_sha256":original["prosperity-city-distribution/grounded-distribution.svg"],
        "source_index_verbatim":True,
        "previous_p452_html_sha256":hashlib.sha256(content.encode()).hexdigest(),
        "new_historical_coordinates":0,
        "approved_homepage_hero_unchanged":True
    })
    assert all(sha(SITE/name)==v for name,v in protected.items())
    members={f"prosperity-street-clusters/{p.relative_to(OUT)}":p for p in OUT.rglob("*") if p.is_file()}
    members["prosperity-street-clusters.html"]=pagefile
    members[f"downloads/{pdf.name}"]=pdf
    dump(OUT/"bundle-manifest.json",{"version":VERSION,"source_commit":info["source_commit"],
        "files_sha256":{k:sha(f) for k,f in members.items()}})
    members["prosperity-street-clusters/bundle-manifest.json"]=OUT/"bundle-manifest.json"
    zipfile_path=SITE/"downloads/prosperity-street-clusters-p453-package.zip"
    with zipfile.ZipFile(zipfile_path,"w",zipfile.ZIP_DEFLATED) as z:
        for name,p in members.items():z.write(p,name)
    release["extensions"]=sorted(set(release.get("extensions",[])+[VERSION]))
    release["prosperity_street_clusters_version"]=VERSION
    release["current_milestone"]="盛时P4.5.3：三组宫前/两桥/洛南文献建筑关系的来源分层"
    dump(SITE/"release.json",release)
    info["prosperity_street_clusters"]={
       "version":VERSION,"source_commit":info["source_commit"],
       "cluster_count":3,"documentary_entities":20,"direct_relations":16,"conditional_relations":1,
       "source_map_sha256":sha(ref),"atlas_pages":4,"ancient_geographic_coordinates_added":0,
       "estimated_population_density":False,"metadata":"prosperity-street-clusters/data.json"}
    info["files_sha256"]={str(p.relative_to(SITE)):sha(p) for p in sorted(SITE.rglob("*"))
                            if p.is_file() and p.name!="build-info.json"}
    dump(SITE/"build-info.json",info)
    print(json.dumps(info["prosperity_street_clusters"],ensure_ascii=False))

if __name__=="__main__":
    main()
