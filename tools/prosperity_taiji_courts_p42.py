#!/usr/bin/env python3
"""P4.2: reconstruct only documented Taiji / east-hall type and courtyard relations."""
from pathlib import Path
import csv
import hashlib
import html
import io
import json
import shutil
import xml.etree.ElementTree as ET
import zipfile
from north_b4 import render_atlas

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
OUT=SITE/"prosperity-taiji-courts"
SRC=ROOT/"research/prosperity-v4/taiji-court-relations.json"
VERSION="prosperity-taiji-courts-p42"
W,H=1480,960
def esc(x):return html.escape(str(x),quote=True)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def tx(x,y,string,size=23,fill="#2a4c42",weight=500,anchor="start"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'font-family="Noto Sans CJK SC,Microsoft YaHei,sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}">{esc(string)}</text>')
def box(x,y,w,h,fill="#fffcf7",stroke="#d4ded6",r=10):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{fill}" stroke="{stroke}"/>'
def svg_begin(title,subtitle):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}">',
            f'<rect width="{W}" height="{H}" fill="#f6f5f0"/>',
            tx(65,58,"盛时洛阳 P4.2 · 有据的建筑组合",22,"#5f8072",700),
            tx(65,113,title,39,"#23483d",700),
            tx(65,154,subtitle,20,"#6b7f73"),
            '<path d="M65 187H1415" stroke="#d6dfd8" stroke-width="2"/>']
def svg_end(parts,foot):
    parts.extend(['<path d="M65 905H1415" stroke="#d6dfd8" />',
                  tx(65,940,foot,19,"#6d8074"),'</svg>'])
    return "\n".join(parts)+"\n"

def hall_scale_svg(d):
    m=d["main_hall"];e=d["east_hall"]["observations"][0]
    s=3.6; cx=395;cy=493
    north=m["north_ew_m"]*s;south=m["south_ew_m"]*s;depth=m["ns_review_m"]*s
    x_right=cx+north/2
    hall_left=x_right+e["gap_from_main_east_m"]*s
    ew=e["ew_m"]*s;ns=e["ns_m"]*s
    p=svg_begin("主殿与东堂：不是重复的大殿模型",
                "同一米尺对读台基边长；东堂与主殿的南北对齐仅为图面编排，未取得实测偏移。")
    p.append(box(65,216,1350,615))
    pts=(f'{cx-north/2:.2f},{cy-depth/2:.2f} {cx+north/2:.2f},{cy-depth/2:.2f} '
         f'{cx+south/2:.2f},{cy+depth/2:.2f} {cx-south/2:.2f},{cy+depth/2:.2f}')
    p.append(f'<polygon points="{pts}" fill="#86b2a4" fill-opacity=".42" stroke="#2e7764" stroke-width="4"/>')
    p.append(tx(cx,cy-9,"太极殿主殿台基",24,"#255b4f",700,"middle"))
    p.append(tx(cx,cy+26,"北宽102.3 · 南宽98.4 m",20,"#255b4f",600,"middle"))
    p.append(tx(cx,cy+depth/2+42,"进深报告范围58—61.5m",20,"#526b5c",500,"middle"))
    east_y=cy-ns/2
    p.append(f'<rect x="{hall_left:.2f}" y="{east_y:.2f}" width="{ew:.2f}" height="{ns:.2f}" '
             'fill="#c5a77a" fill-opacity=".40" stroke="#a78550" stroke-width="4"/>')
    p.append(tx(hall_left+ew/2,cy-10,"太极东堂",22,"#8d6532",700,"middle"))
    p.append(tx(hall_left+ew/2,cy+23,"47.9 × 21.3 m",20,"#8d6532",550,"middle"))
    p.append(f'<path d="M{x_right:.1f} {cy:.1f}H{hall_left:.1f}" stroke="#b66044" stroke-width="3" stroke-dasharray="6 5"/>')
    p.append(tx((x_right+hall_left)/2,cy-17,"13 m",18,"#b66044",700,"middle"))
    p.append(tx(1000,300,"2020 另一发表口径",25,"#496e5b",700))
    for i,line in enumerate(["东堂 48 × 23 m","距主殿约 14 m","不平均两个来源的尺寸","西堂形状/宽度本轮未补画"]):
        p.append(tx(1000,347+45*i,line,21,"#617468"))
    p.append(tx(1000,643,"东閤门（约4m通道）",22,"#42685a",600))
    p.append(tx(1000,685,"上层阁道：基于柱础推断",19,"#a06547",500))
    return svg_end(p,"来源：吉林大学2016考古成果介绍／徐龙国2020；上图不提供北魏时期真实屋顶和建筑高度。")

def north_courts_svg(d):
    d2=d["northern_courts"]
    assert d2["west"]["inner_court_ew_m"]==8 and d2["east"]["southern_corridor_bays"]==9
    p=svg_begin("东堂北侧：道路、廊庑与两组院落的关系",
                "只有已记载的相邻、道路、南廊和局部天井；以下卡片为无比例关系式，不是完整发掘平面。")
    p.append(box(70,218,1340,600))
    p.append(box(150,242,1110,96,fill="#e0eae2",stroke="#aac9b7"))
    p.append(tx(705,295,"北方：院落其余边界未全部揭露  ·  不补院墙",24,"#406b59",650,"middle"))
    p.append(box(180,358,490,237,fill="#f5efe2"))
    p.append(box(750,358,490,237,fill="#f5efe2"))
    p.append(tx(423,405,"西侧院落",29,"#85663c",700,"middle"))
    p.append(tx(423,448,"院址东西约20m  ·  南廊4间",20,"#876a43",500,"middle"))
    p.append(tx(423,490,"石铺天井约 8×4m",20,"#876a43",500,"middle"))
    p.append(tx(423,533,"北正房3间，宽约9m",20,"#876a43",500,"middle"))
    p.append(tx(996,405,"东侧院落",29,"#85663c",700,"middle"))
    p.append(tx(996,448,"南廊9间，残长约37m",20,"#876a43",500,"middle"))
    p.append(tx(996,490,"仅掘出部分南部建筑",20,"#876a43",500,"middle"))
    p.append(tx(996,533,"东缘超出发掘区，不封闭",20,"#876a43",500,"middle"))
    p.append(box(170,620,1100,81,fill="#dfeaf0",stroke="#94bbc8"))
    p.append(tx(720,668,"东西向铺砖道路：残长约52m、宽约4m；西端单门道约3.5m",22,"#367183",650,"middle"))
    p.append(f'<path d="M720 702V760" stroke="#709f8f" stroke-width="6" stroke-dasharray="9 8"/>')
    p.append(box(493,756,453,57,fill="#e0e9df",stroke="#a6c2ac"))
    p.append(tx(720,793,"太极东堂（在两院以南）",22,"#437356",650,"middle"))
    return svg_end(p,"材料：吉林大学2016公布的东堂北院与道路发掘文字；不得从本图读取院落间距或实测坐标。")

def outer_scopes_svg(d):
    a,b=d["courtyard_extent_variants"]
    s=1.24
    p=svg_begin("太极殿宫院：两组范围不应直接拼合",
                "使用同一像素/米比例对比尺寸；各框中心为排版锚点，未找到它们真实共用的南墙或北墙。")
    p.append(box(65,210,1350,640))
    items=[(a,405,520,"#477f6f"),(b,1055,520,"#a17c4d")]
    for row,x,y,col in items:
        w=row["ew_m"]*s;h=row["ns_m"]*s
        p.append(f'<rect x="{x-w/2:.2f}" y="{y-h/2:.2f}" width="{w:.2f}" height="{h:.2f}" '
                 f'stroke="{col}" stroke-width="4" stroke-dasharray="12 7" fill="{col}" fill-opacity=".10"/>')
        p.append(tx(x,y-12,row["label"],24,col,700,"middle"))
        p.append(tx(x,y+30,f'{row["ew_m"]}m × {row["ns_m"]}m',25,col,700,"middle"))
    p.append(tx(740,815,"B 与 A：东西 −20m；南北 +70m。没有共同控制，不能把任一框当作已定位宫墙。",22,"#785c43",600,"middle"))
    return svg_end(p,"来源：2015成果介绍与2017讲座（A）；2023政务考古综述（B）；发表口径与年代仍须对校。")

def output_csv(d):
    stream=io.StringIO();w=csv.writer(stream)
    w.writerow(["group","source","element","dimension","reported_m","status"])
    m=d["main_hall"]
    for field in ["north_ew_m","south_ew_m","ns_review_m"]:
        w.writerow(["main_hall","XU2020","rammed_platform",field,m[field],"multi_phase_remaining"])
    for v in d["east_hall"]["observations"]:
        for field in ["ew_m","ns_m","gap_from_main_east_m"]:
            w.writerow(["east_hall",v["source_id"],"rammed_platform",field,v[field],"source_variant"])
    c=d["northern_courts"]
    for key in ["ew_m","ns_m"]:
        w.writerow(["west_inner_court","JLU2016","paved_inner_court",key,c["west"].get("inner_court_"+key,0),"partial_excavation"])
    for v in d["courtyard_extent_variants"]:
        for fld in ["ew_m","ns_m"]:
            w.writerow(["whole_court",",".join(v["source_ids"]),v["label"],fld,v[fld],"unknown_common_boundary"])
    return stream.getvalue()

def page(d,info):
    cards="".join(
        '<article class="source-card"><h3>'+esc(s["title"])+'</h3><p>'+esc(s["kind"])+'</p>'
        '<a href="'+esc(s["url"])+'" target="_blank" rel="noopener">查看来源 ↗</a></article>'
        for s in d["sources"])
    phases="".join(
       '<div class="phase-detail" data-phase-card="'+esc(x["id"])+'"'+('' if x["id"]=="northern_wei" else ' hidden')+'>'
       '<h3>'+esc(x["label"])+'</h3><p><strong>廊房：</strong>'+esc(x["corridor"])+'</p>'
       '<p><strong>排水：</strong>'+esc(x["drainage"])+'</p>'
       '<p><strong>院落边界：</strong>'+esc(x["boundary"])+'</p></div>'
       for x in d["phase_models"])
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>盛时洛阳 · 太极殿东堂与北侧宫院 P4.2</title>
<meta name="description" content="太极殿与东堂的台基体量、东堂北侧宫院道路与廊庑、北魏时层及两种宫院边界的对照。">
<link rel="stylesheet" href="./prosperity-taiji-courts/style.css"></head><body>
<header><a href="./">盛时洛阳</a><nav aria-label="研究导航">
<a href="./prosperity-axis.html">宫城中轴尺度 P4</a><a href="./prosperity-axis-sources.html">宫门原刊对照 P4.1</a>
<a href="#extent">宫院范围对照</a><a href="#sources">来源</a></nav></header>
<main><section class="intro"><p class="eyebrow">P4.2 · 从单体尺度走向真实建筑群</p>
<h1>太极殿之外，东堂与廊院也有各自的结构。</h1>
<p>本轮把已核考古报告中的主殿、东堂、东閤门、北侧院落和铺砖道路分层显示：
<strong>能量的台基采用同一尺比，只有相对关系的院落采用非比例组织图。</strong>不以建筑想象图填补缺失的院墙和屋顶。</p>
<div class="stats"><div><b>2</b><span>宫院范围发表口径</span></div><div><b>3</b><span>遗址营建时层</span></div>
<div><b>0</b><span>新增城市绝对坐标</span></div></div></section>
<section class="part" id="halls"><p class="eyebrow">01 · 有数值的台基</p>
<h2>主殿、东堂并不是同一块屋顶模型的复制</h2>
<p>主殿北边102.3m、南边98.4m，进深报告约58—61.5m。较早发掘介绍记录东堂约47.9×21.3m、东距约13m；
另一篇论文记录东堂约48×23m、间距约14m。两种口径均保留，不能强行平均。东堂之间的阁道上部结构仍属于推定。</p>
<figure><img src="./prosperity-taiji-courts/halls-scale.svg" alt="主殿北宽102.3米南宽98.4米与东堂约47.9乘21.3米的台基同尺度对照">
<figcaption>同尺度但无可靠南北错位测点；颜色只区分建筑台基，不能代表北魏屋面颜色。</figcaption></figure></section>
<section class="part" id="northern-courts"><p class="eyebrow">02 · 东堂以北</p><h2>两组院落、长廊、石铺天井和道路</h2>
<p>院落发掘主要在南半部。西侧院落东西约20m，南廊4间，内院石铺天井约8×4m；东侧院落南廊9间、残长约37m。
东堂与两院之间有残长约52m、宽约4m的东西向铺砖道路，西端有约3.5m的单门道。<strong>这些数字尚不能拼成完整封闭宫墙。</strong></p>
<figure><img src="./prosperity-taiji-courts/north-courts-relations.svg" alt="太极东堂北侧的两院、廊房、天井与铺砖道路非比例关系图">
<figcaption>只表达相邻关系与已发表的局部长度；不是考古原图的像素重描，也不提供真实院落间距。</figcaption></figure>
<p>2017年还确认了太极殿宫院东北角局部院落东西约96m、南北残长约27m及约4.7m夹道。
这组较后调查的院落，暂不与前述两小院无条件合并为同一院址。</p></section>
<section class="part" id="phases"><p class="eyebrow">03 · 分期</p><h2>北魏时期的廊庑组织与魏晋、北周并不一样</h2>
<div class="phase-controls" role="group" aria-label="选择建筑阶段">
<button type="button" data-phase="wei_jin" aria-pressed="false">魏晋早期</button>
<button type="button" data-phase="northern_wei" aria-pressed="true">北魏重修</button>
<button type="button" data-phase="northern_zhou" aria-pressed="false">北周晚期</button></div>
<div id="phase-inspector" aria-live="polite">{phases}</div>
<p>这些阶段来自对不同层位的考古解释，不意味着每一座院落在整个516—528年都有相同的墙体和排水设施。
尤其不能把北周未完成的大型夯筑直接当成“盛时洛阳”的现状。</p></section>
<section class="part" id="extent"><p class="eyebrow">04 · 宫院边界</p>
<h2>340×310m 与 320×380m：轮廓差别不能藏起来</h2>
<figure><img src="./prosperity-taiji-courts/court-extents.svg" alt="两种太极殿宫院发表尺度340乘310米与320乘380米，以相同比例并列">
<figcaption>两个范围均为报告约数；这只是等尺比比较，各矩形的位置与对齐是排版设置，未获得共同现场控制点。</figcaption></figure>
<div class="extent-choices"><label for="extent-select">选择一种发表口径：</label>
<select id="extent-select"><option value="A">2015/2017 · 340×310m</option><option value="B">2023 · 320×380m</option></select>
<p id="extent-result" aria-live="polite">方案A：东西约340m、南北约310m。南北边界、所选时相和共同锚点均未核对。</p></div>
<p><strong>方案B相对于方案A：</strong>东西少约20m，南北多约70m。它们或涉及不同测线、院墙认定或发表阶段；
现有资料不足以确定原因。任何一套范围都不自动变成城市经纬度上的确定宫墙。</p></section>
<section class="part" id="sources"><p class="eyebrow">05 · 核查原始资料</p><h2>点击查看考古发掘叙述与研究图版</h2>
<div class="sources">{cards}</div></section>
<section class="part" id="downloads"><p class="eyebrow">06 · 可复核文件</p><h2>图册与研究数据</h2>
<div class="downloads"><a href="./downloads/prosperity-taiji-courts-p42-atlas.pdf">三页图册 PDF</a>
<a href="./downloads/prosperity-taiji-courts-p42-package.zip">资料包 ZIP</a>
<a href="./prosperity-taiji-courts/data.json">证据 JSON</a>
<a href="./prosperity-taiji-courts/measurements.csv">量距 CSV</a></div>
<p>未得到可把东堂—廊院—宫墙接成全城坐标的共同地面控制点；目前没有新增古代建筑高度，也没有按未知轮廓重构屋顶。</p></section>
<footer><a href="./prosperity-axis-sources.html">返回前一阶段 P4.1</a><span>P4.2 · {esc(info["source_commit"][:8])}</span></footer>
</main><script src="./prosperity-taiji-courts/app.js"></script></body></html>"""

def main():
    d=read(SRC)
    assert d["version"]==VERSION
    assert d["main_hall"]["north_ew_m"]==102.3
    assert d["east_hall"]["observations"][0]["ew_m"]==47.9
    assert [x["ns_m"] for x in d["courtyard_extent_variants"]]==[310,380]
    assert d["geographic_registration"]["verified_common_control_points"]==0
    info=read(SITE/"build-info.json")
    assert info["prosperity_axis_source_audit"]["version"]=="prosperity-axis-p41-source-audit"
    assert not (SITE/"prosperity-taiji-courts.html").exists()
    OUT.mkdir(parents=True,exist_ok=True)
    for src,dest in [("web/prosperity-taiji-courts.css","style.css"),("web/prosperity-taiji-courts.js","app.js")]:
        shutil.copyfile(ROOT/src,OUT/dest)
    dump(OUT/"data.json",d)
    (OUT/"measurements.csv").write_text(output_csv(d),encoding="utf-8-sig")
    figures=[
        ("halls-scale.svg",hall_scale_svg(d)),
        ("north-courts-relations.svg",north_courts_svg(d)),
        ("court-extents.svg",outer_scopes_svg(d))]
    atlas_paths=[]
    for name,content in figures:
        item=OUT/name;item.write_text(content,encoding="utf-8")
        root=ET.fromstring(content)
        assert root.tag=="{http://www.w3.org/2000/svg}svg"
        assert root.get("viewBox")==f"0 0 {W} {H}"
        atlas_paths.append(item)
    (SITE/"downloads").mkdir(parents=True,exist_ok=True)
    pdf=SITE/"downloads/prosperity-taiji-courts-p42-atlas.pdf"
    render_atlas(atlas_paths,pdf)
    page_file=SITE/"prosperity-taiji-courts.html"
    page_file.write_text(page(d,info),encoding="utf-8")
    (OUT/"README.md").write_text(
        "P4.2 太极殿—东堂—院落分期图证\n"
        "halls-scale.svg采用实测台基的同米尺度，东堂南北相对错位未得证。\n"
        "north-courts-relations.svg只为连接关系目录，无长度比和真实坐标。\n"
        "court-extents.svg两组报告尺度并列，不等于确定院界；不得用共同中心点进行地理配准。\n"
        "魏晋、北魏、北周层位分开记录；同系考古报告不算独立来源重复投票。\n",encoding="utf-8")
    members={f"prosperity-taiji-courts/{x.name}":x for x in sorted(OUT.iterdir()) if x.is_file()}
    members["prosperity-taiji-courts.html"]=page_file
    members[f"downloads/{pdf.name}"]=pdf
    dump(OUT/"bundle-manifest.json",{"version":VERSION,"source_commit":info["source_commit"],
         "files_sha256":{k:digest(v) for k,v in members.items()}})
    members["prosperity-taiji-courts/bundle-manifest.json"]=OUT/"bundle-manifest.json"
    with zipfile.ZipFile(SITE/"downloads/prosperity-taiji-courts-p42-package.zip","w",zipfile.ZIP_DEFLATED) as z:
        for name,item in members.items():z.write(item,name)
    release=read(SITE/"release.json")
    release["extensions"]=sorted(set(release.get("extensions",[])+[VERSION]))
    release["prosperity_taiji_courts_version"]=VERSION
    release["current_milestone"]="盛时P4.2：太极殿东堂北院尺度、分期与范围比对"
    dump(SITE/"release.json",release)
    info["prosperity_taiji_courts"]={"version":VERSION,"source_commit":info["source_commit"],
        "sources":len(d["sources"]),"diagrams":len(figures),"atlas_pages":len(figures),
        "registered_absolute_locations_added":0,"verified_geographic_controls":0,
        "metadata":"prosperity-taiji-courts/data.json"}
    info["files_sha256"]={str(x.relative_to(SITE)):digest(x) for x in sorted(SITE.rglob("*"))
                         if x.is_file() and x.name!="build-info.json"}
    dump(SITE/"build-info.json",info)
    print(json.dumps(info["prosperity_taiji_courts"],ensure_ascii=False))
if __name__=="__main__":main()
