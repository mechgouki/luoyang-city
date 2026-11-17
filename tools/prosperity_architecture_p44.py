#!/usr/bin/env python3
"""P4.4: archaeological gate morphology -- three original diagrams, no imagined historical roofs."""
from pathlib import Path
from north_b4 import render_atlas
import csv
import hashlib
import html
import io
import json
import shutil
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
OUT=SITE/"prosperity-architecture"
SRC=ROOT/"research/prosperity-v4/architecture-types-p44.json"
VERSION="prosperity-architecture-p44"
W,H=1660,1050
PAPER="#f6f5f0"
INK="#28453c"
MUTED="#62786c"
COLORS={
"city_defensive":"#567d77",
"palace_ceremonial":"#9f7849",
"palace_side_ceremonial":"#9f8669",
"inter_hall_link":"#447d91",
"smaller_courtyard_gate":"#8a736a",
"courtyard_corridor":"#71925f"
}

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def dump(path,obj):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def esc(s):
    return html.escape(str(s),quote=True)

def tx(x,y,s,size=23,fill=INK,weight=500,anchor="start"):
    return (
        f'<text x="{float(x):.1f}" y="{float(y):.1f}" '
        f'text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" '
        f'font-family="Noto Sans CJK SC,Microsoft YaHei,sans-serif" fill="{fill}">{esc(s)}</text>'
    )

def rect(x,y,w,h,fill="#fff",stroke="#d6dfd7",radius=8,stroke_width=2,dash=None):
    dashed=f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{float(x):.1f}" y="{float(y):.1f}" width="{float(w):.1f}" '
            f'height="{float(h):.1f}" rx="{radius}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{stroke_width}"{dashed}/>' )

def line(x1,y1,x2,y2,color="#536e62",width=3,dash=None):
    other=f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="M{float(x1):.1f},{float(y1):.1f} L{float(x2):.1f},{float(y2):.1f}" '
            f'fill="none" stroke="{color}" stroke-width="{width}"{other}/>' )

def dot(x,y,r=5,color="#3f766a"):
    return f'<circle cx="{float(x):.1f}" cy="{float(y):.1f}" r="{r}" fill="{color}"/>'

def sheet(title,subtitle):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'role="img" aria-label="{esc(title)}">',
        rect(0,0,W,H,PAPER,PAPER,0,0),
        tx(55,58,"盛时洛阳 · P4.4 · 从已见遗构到建筑类型",23,"#5e8071",700),
        tx(55,111,title,36,INK,700),
        tx(55,155,subtitle,20,MUTED),
        line(55,177,1605,177,"#d9e3d8",2)
    ]

def finish(p,footer):
    p.extend([line(55,1009,1605,1009,"#d9e3d8",2),
              tx(55,1037,footer,18,MUTED),"</svg>"])
    return "\n".join(p)+"\n"

def post_grid(x,y,columns,rows,step_x,step_y,color):
    out=[]
    for j in range(rows):
        for i in range(columns):
            out.append(dot(x+i*step_x,y+j*step_y,5,color))
    return out

def three_openings(p,x,y,width=340):
    p.append(rect(x,y,width,96,"#e8ede5","#a7b9ab",4,2))
    for shift in (-1,0,1):
        cx=x+width/2+shift*90
        p.append(rect(cx-24,y-13,48,122,"#fff","#90aaa0",3,2))
        p.append(line(cx,y-23,cx,y+120,"#8aa99e",2,"6 8"))

def morphology(p,t,x,y):
    id=t["id"]
    col=COLORS[t["category"]]
    area_x=x+64
    area_y=y+120
    if id=="inner_city_gate":
        three_openings(p,area_x,area_y+5,350)
        p.append(tx(x+240,y+262,"三门道 · 排叉柱坑 → 过梁推断",18,col,650,"middle"))
    elif id=="palace_axial_gate":
        p.append(rect(area_x+6,area_y+4,350,120,"#e6ded0","#b99560",3))
        p.extend(post_grid(area_x+31,area_y+19,8,5,41,23,col))
        p.append(tx(x+240,y+270,"7开间 × 4进深 / 40柱础",19,col,650,"middle"))
    elif id=="palace_side_gate":
        p.append(rect(area_x+28,area_y+10,300,112,"#e6ded0","#b99560",3))
        p.extend(post_grid(area_x+46,area_y+24,6,3,52,42,col))
        p.append(tx(x+240,y+270,"5开间 × 2进深 / 三门道",19,col,650,"middle"))
    elif id=="east_ge_gate":
        p.append(rect(area_x+12,area_y+12,320,100,"#edf2ee","#92a9a0",3))
        p.append(rect(area_x+110,area_y+11,106,100,"#fff","#6e989b",3))
        for i in range(4):
            for row in (area_y+19,area_y+103):
                p.append(dot(area_x+18+i*102,row,6,col))
        p.append(line(area_x+165,area_y-5,area_x+165,area_y+128,"#a17b54",3,"5 6"))
        p.append(tx(x+240,y+270,"南北门道 / 两排各四础石",18,col,650,"middle"))
    elif id=="roofed_court_gate":
        p.append(line(area_x+20,area_y+64,area_x+131,area_y+64,col,11))
        p.append(line(area_x+225,area_y+64,area_x+333,area_y+64,col,11))
        p.append(rect(area_x+132,area_y+16,92,95,"#e7ebdf",col,3))
        p.append(rect(area_x+165,area_y-5,28,138,"#fff",col,3,2,"8 5"))
        for xx in (area_x+143,area_x+213):
            for yy in (area_y+20,area_y+105):
                p.append(dot(xx,yy,5,col))
        p.append(tx(x+240,y+270,"单门道 / 隔墙 / 檐柱",19,col,650,"middle"))
    elif id=="corridor_court_gate":
        p.append(rect(area_x+12,area_y+25,320,74,"#eaf0e7",col,3))
        p.append(line(area_x+12,area_y+62,area_x+148,area_y+62,col,8))
        p.append(line(area_x+194,area_y+62,area_x+334,area_y+62,col,8))
        for xx in (area_x+42,area_x+114,area_x+232,area_x+304):
            p.append(dot(xx,area_y+27,6,col))
            p.append(dot(xx,area_y+97,6,col))
        p.append(rect(area_x+148,area_y+33,46,60,"#fff",col,2,2,"6 4"))
        p.append(tx(x+240,y+270,"中隔墙开门 / 两侧檐柱",19,col,650,"middle"))

def gate_matrix(data):
    p=sheet("六种门制，不是一种屋顶的六次复制",
            "平面示意只比较已报告的门道、柱础、开间类型；卡片位置和空间距离不等于古址分布。")
    descriptions=[
        ("建春门","3门道｜防御性城门"),
        ("阊阖门","7×4开间｜礼仪主门"),
        ("神虎门","5×2开间｜较小侧门"),
        ("东閤门","3×2开间｜殿间连接"),
        ("宫院屋宇门","1×2开间｜独立单门"),
        ("廊道式院门","院廊隔墙内单门")
    ]
    positions=[(55,201),(590,201),(1125,201),(55,587),(590,587),(1125,587)]
    for t,(short,sub),(x,y) in zip(data["types"],descriptions,positions):
        c=COLORS[t["category"]]
        p.append(rect(x,y,480,350,"#fff","#d4ded5",14))
        p.append(rect(x+20,y+18,11,38,c,c,2,0))
        p.append(tx(x+46,y+48,short,27,c,700))
        p.append(tx(x+30,y+88,sub,20,MUTED,550))
        morphology(p,t,x,y)
        p.append(tx(x+30,y+314,{"inner_city_gate":"排叉柱形式属结构解释","palace_axial_gate":"“三重楼观”未获原貌实证","palace_side_gate":"“两重楼观”为研究者推测","east_ge_gate":"上层阁道非实存立面","roofed_court_gate":"门顶样式与高度未定","corridor_court_gate":"屋面、院界范围未定"}[t["id"]],17,"#8e6f4d"))
    return finish(p,"• 表示报告中的柱础 · 方形表示示意台基/墙体 · 虚线表示功能标注；所有高度、屋面、城市坐标均未恢复。")

def comparison_panel(data):
    p=sheet("东閤门：门道、础心距与同址问题要分开",
            "六组原始数字中的三对口径不强行平均，也不把院北两座“西端门”自动判作同一地物。")
    g=data["source_scope_comparisons"]
    titles=["01｜东閤门中间门道宽","02｜东閤门侧间进深","03｜东堂北院西端门"]
    notes=[
        "4米是门道约宽；4.3米是中间一间础心距。",
        "2016与2018所量端点、发表阶段尚未统一。",
        "3.5米道路西端门 ≠ 已确认4米屋宇式门。"
    ]
    for i,row in enumerate(g):
        y=211+i*243
        p.append(rect(55,y,1550,208,"#fff","#d6dfd7",12))
        p.append(tx(93,y+48,titles[i],26,INK,700))
        a,b=row["readings"]
        p.append(rect(91,y+72,670,72,"#e9f1ef","#bad6cc",8))
        p.append(rect(828,y+72,686,72,"#f4eee5","#dbc7aa",8))
        p.append(tx(111,y+100,f'{a["source_id"]} · {a["value_m"]}m',22,"#426f61",700))
        p.append(tx(111,y+129,a["measure"],17,"#577b6a"))
        p.append(tx(849,y+100,f'{b["source_id"]} · {b["value_m"]}m',22,"#98714f",700))
        p.append(tx(849,y+129,b["measure"],17,"#8d755c"))
        p.append(tx(91,y+178,notes[i],20,"#7c624c",550))
    return finish(p,"禁止对不同端点数字求均值、消除未证差异；原刊图六至九尚未独立获得带尺底图及可核的城市共同控制。")

def node(p,x,y,w,h,title,subtitle,color):
    p.append(rect(x,y,w,h,"#fff",color,11,3))
    p.append(tx(x+w/2,y+36,title,24,color,700,"middle"))
    p.append(tx(x+w/2,y+65,subtitle,17,MUTED,500,"middle"))

def grammar_plate(data):
    p=sheet("先组织宫城的结构，再谈复原全景的宏伟",
            "三条分开示意的建筑关系，不合并为真实平面；上下位置仅为排版，不能读取实际南北距离。")
    p.append(rect(55,210,1550,193,"#e9efeb","#b9cbc0",12))
    p.append(tx(90,248,"宫城礼仪轴线（历史门序）",25,INK,700))
    for x,name,sub in [(100,"阊阖门","7×4 · 3门道"),(460,"止车门","轴线第二道"),(820,"端门","轴线第三道"),(1180,"太极殿","主要正殿")]:
        node(p,x,272,280,95,name,sub,"#876746")
    for a in (380,740,1100):
        p.append(line(a,320,a+80,320,"#7c997f",4))
        p.append(tx(a+40,312,"顺序",16,"#7c997f",500,"middle"))
    p.append(rect(55,441,1550,222,"#e8eff2","#aac7d0",12))
    p.append(tx(90,479,"太极殿—东堂殿间连接（不是完整台基平面）",25,INK,700))
    node(p,160,526,345,95,"太极殿主殿","大型台基"," #547988".strip())
    node(p,660,526,345,95,"东閤门","下门道／上阁道推定","#397a90")
    node(p,1150,526,345,95,"太极东堂","较小独立台基","#547988")
    p.append(line(505,569,660,569,"#5b95a0",5))
    p.append(line(1005,569,1150,569,"#5b95a0",5))
    p.append(rect(55,703,1550,244,"#f0eee6","#d5c7a9",12))
    p.append(tx(90,741,"东堂北院落：铺砖道路 + 两院廊庑（关系层）",25,INK,700))
    node(p,111,785,370,111,"东堂北铺砖道路","宽约4m，残长约52m","#806f49")
    node(p,644,785,370,111,"西侧局部院落","南廊4间，天井局部","#69846b")
    node(p,1176,785,370,111,"东侧局部院落","南廊9间，东缘未全掘","#69846b")
    p.append(line(481,833,644,833,"#ac9e79",4,"9 7"))
    p.append(line(1014,833,1176,833,"#ac9e79",4,"9 7"))
    return finish(p,"此板只为已记载的类型与关系；缺真实宫院墙界、共同控制点及北魏上部建筑高度，禁止按此示意图拼3D城址。")

METRICS={
"platform_ns_m":"台基南北长",
"platform_ew_m":"台基东西长",
"center_passage_report_m":"中门残宽",
"side_passages_report_m":"两侧门残宽",
"postpit_remains":"柱础坑见存",
"changhe_platform_ew_m":"阊阖门台基东西长",
"changhe_platform_ns_m":"阊阖门台基南北宽",
"changhe_column_bases":"阊阖门柱础数",
"changhe_que_bases":"阊阖门双阙台基数",
"paired_que_found":"双阙基址",
"excavation_report_year":"研究年度",
"eave_column_base_rows":"檐柱础排数",
"base_count_per_row":"每排柱础数量",
"side_rammed_partition_width_m_approx":"两侧夯土隔墙宽约",
"rammed_wall_remaining_height_m":"夯土隔墙残高（非古高）",
"door_opening_m_approx":"报告门道宽约",
"partition_width_m_approx":"隔墙宽约",
"eave_column_diameter_m_approx":"檐柱础石直径约",
"post_to_post_spacing_m_range":"报告柱础心间距范围"
}
METRIC_NOUNITS={"postpit_remains","paired_que_found","changhe_column_bases","changhe_que_bases","excavation_report_year","base_count_per_row","eave_column_base_rows"}
def observed(t):
    result=[]
    for key,value in t["observed_evidence"].items():
        if isinstance(value,bool):
            shown="是" if value else "否"
        elif isinstance(value,list):
            shown="—".join(map(str,value))+"m"
        else:
            shown=str(value)+("" if key in METRIC_NOUNITS else "m")
        result.append(f'{METRICS.get(key,key)}：{shown}')
    grid=t.get("reported_bay_grid")
    if grid:
        result.append(f'报告开间：面阔{grid["frontage_bays"]}间 × 进深{grid["depth_bays"]}间')
    return "；".join(result)

def csv_text(data):
    s=io.StringIO()
    writer=csv.writer(s)
    writer.writerow(["type_id","name","style","source_ids","passages","frontage_bays","depth_bays","historical_roof_height_m","upper_storeys_known","geographic_registration","observations"])
    for t in data["types"]:
        grid=t.get("reported_bay_grid") or {}
        writer.writerow([t["id"],t["name"],t["style"],",".join(t["source_ids"]),
                         t["passage_count"],grid.get("frontage_bays"),grid.get("depth_bays"),
                         "",str(t["upper_floors_known"]).lower(),"unregistered",observed(t)])
    return s.getvalue()

def page(data,info):
    tabs="".join(
        f'<button type="button" data-type="{esc(t["id"])}" aria-controls="panel-{esc(t["id"])}" aria-pressed="false">{esc(t["name"])}</button>'
        for t in data["types"])
    panels=""
    for t in data["types"]:
        warnings="".join("<li>"+esc(x)+"</li>" for x in t["limitations"])
        source_refs="、".join(t["source_ids"])
        panels+=(
          f'<article id="panel-{esc(t["id"])}" class="type-panel" data-type-panel="{esc(t["id"])}">'
          f'<span class="pill">{esc(t["style"])} · {esc(t["category"])}</span>'
          f'<h3>{esc(t["name"])}｜{esc(t["place_example"])}</h3>'
          '<div class="detail-grid"><div><strong>公开报告所见</strong>'
          f'<p>{esc(observed(t))}。来源：{esc(source_refs)}。</p></div>'
          f'<div><strong>作者解释／结构推断</strong><p>{esc(t["inference"])}</p></div></div>'
          '<p><strong>不能由此推出：</strong></p><ul>'+warnings+'</ul>'
          '<p class="muted">本项目没有从原始图版量读可配准地理坐标；古高、完整屋顶和古地面均为未知。</p></article>'
        )
    comparisons="".join(
      f'<tr><td>{esc({"east_gate_center_door":"东閤门中央","east_gate_depth":"东閤门进深","west_court_gate":"院北西端门身份"}[c["id"]])}</td>'
      f'<td>{esc(c["readings"][0]["value_m"])}m（{esc(c["readings"][0]["source_id"])}）</td>'
      f'<td>{esc(c["readings"][1]["value_m"])}m（{esc(c["readings"][1]["source_id"])}）</td>'
      f'<td>{esc(c["result"])}</td></tr>'
      for c in data["source_scope_comparisons"])
    sources="".join(
      f'<li><a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["title"])}</a>'
      f'<p>{esc(s["accessed_publication"])}。{esc(s["figure_read_status"])}</p></li>'
      for s in data["sources"])
    figures=[
      ("gate-matrix.svg","六类建筑类型与柱础组织","基于已见证据的分型而非重画原刊；全部布局点距仅为卡片示意。"),
      ("east-ge-source-comparison.svg","东閤门数值与院门身份异记","两版文献对照的数字、测量对象和未核端点独立保留。"),
      ("palace-relation-grammar.svg","宫门轴线、殿间连接与北院廊庑","只有单独证实的相邻、顺序或所属关系；不是全宫实测平面。")
    ]
    gallery="".join(
        f'<figure><a href="./prosperity-architecture/{file}" target="_blank" rel="noopener">'
        f'<img src="./prosperity-architecture/{file}" alt="{esc(title)}"></a>'
        f'<figcaption><strong>{esc(title)}</strong> — {esc(detail)}</figcaption></figure>'
        for file,title,detail in figures)
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>盛时洛阳 P4.4｜六种宫城建筑类型与局部体量研究</title>
<meta name="description" content="以公开发掘成果分类复核北魏洛阳城门、宫门、东閤门、廊道式与屋宇式宫院门，区分遗迹与推断。">
<link rel="stylesheet" href="./prosperity-architecture/style.css"></head>
<body>
<header><a href="./">盛时洛阳</a><nav><a href="./prosperity-palace-boundaries.html">P4.3 宫院范围</a><a href="#types">建筑类型</a><a href="#sources">来源</a><a href="#downloads">下载</a></nav></header>
<main>
<section><p class="eyebrow">P4.4 · 从同一种重复屋顶，走向可核查的建筑群差异</p>
<h1>北魏洛阳的门，不该长得都一样。</h1>
<p class="lede">依据钱国祥2018年的城门与宫院门研究、2016及2017年太极殿考古公布资料，整理六种不同等级、功能和柱础组织的建筑，明确何者可见、何者只是上部结构推断。</p>
<div class="alert"><strong>这不是古代立面复原或真实宫城总图。</strong>没有新增古址经纬度、未证宫院边界、北魏屋顶高度或材色。台基残高不代表原楼高；“三重／两重门楼”属于研究者对文献的解释。</div></section>
<section id="plates"><h2>01 · 三张建筑结构样板</h2>{gallery}</section>
<section id="types"><h2>02 · 按类型查阅依据与限制</h2>
<p>选择具体类型，查看已报告的柱础、台基和门道，以及还不能确定的形制。无JavaScript时下方完整资料仍可直接阅读。</p>
<div class="tabs" role="group" aria-label="选择建筑类型">{tabs}</div>
<div id="type-panels">{panels}</div></section>
<section id="conflicts"><h2>03 · 数字相近不等于同一测线</h2>
<div class="table-wrap"><table><thead><tr><th>对照项</th><th>第一发表</th><th>第二发表</th><th>处理状态</th></tr></thead><tbody>{comparisons}</tbody></table></div>
<p>第一项一个是门道宽、一个是础心间距；第二项未取得共同的深度测量端点；第三项涉及可能不同的院门。三项都不能直接算平均值或推出古址重合。</p></section>
<section id="sources"><h2>04 · 学术出处与图版边界</h2>
<ol class="sources">{sources}</ol>
<p>钱国祥论文原刊于《华夏考古》2018年第6期，2019公开转载注明省略注释。其图六—九的图题已核；本项目目前没有独立可量读的整幅原刊测绘平面，也不再分发受版权保护的原图。</p>
<p><a href="./prosperity-taiji-courts.html">返回P4.2原始台基与北院关系</a> · <a href="./prosperity-palace-boundaries.html">查看P4.3三种宫院尺度</a></p></section>
<section id="downloads"><h2>05 · 图册与证据数据</h2>
<div class="downloads"><a href="./downloads/prosperity-architecture-p44-atlas.pdf">三页图册 PDF</a>
<a href="./downloads/prosperity-architecture-p44-package.zip">完整研究包 ZIP</a>
<a href="./prosperity-architecture/data.json">原始证据 JSON</a>
<a href="./prosperity-architecture/measurements.csv">类型与量距 CSV</a></div>
<p>继续工作：回查原刊图六—九的测绘比例尺与原始图层，再将已核建筑类型接入有据的城市空间分布。第八版首页全景保持暂用状态，不会在未审核前替换。</p></section>
<footer>盛时P4.4 · {esc(info["source_commit"][:10])} · <a href="./">北魏洛阳文献地图</a></footer>
</main><script src="./prosperity-architecture/app.js"></script></body></html>"""

def main():
    data=read(SRC)
    assert data["version"]==VERSION
    assert len(data["types"])==6
    assert data["geo_registration"]["verified_common_ground_controls"]==0
    assert data["geo_registration"]["roof_dimensions_verified"] is False
    assert all(t["roof_height_m"] is None and not t["upper_floors_known"] for t in data["types"])
    info=read(SITE/"build-info.json")
    assert info["prosperity_palace_boundaries"]["version"]=="prosperity-palace-boundaries-p43"
    assert not (SITE/"prosperity-architecture.html").exists()
    OUT.mkdir(parents=True,exist_ok=True)
    for s,target in [("web/prosperity-architecture.css","style.css"),
                     ("web/prosperity-architecture.js","app.js")]:
        shutil.copyfile(ROOT/s,OUT/target)
    dump(OUT/"data.json",data)
    (OUT/"measurements.csv").write_text(csv_text(data),encoding="utf-8-sig")
    figures=[
       ("gate-matrix.svg",gate_matrix(data)),
       ("east-ge-source-comparison.svg",comparison_panel(data)),
       ("palace-relation-grammar.svg",grammar_plate(data))
    ]
    paths=[]
    for name,body in figures:
        path=OUT/name
        path.write_text(body,encoding="utf-8")
        root=ET.fromstring(body)
        assert root.tag=="{http://www.w3.org/2000/svg}svg"
        assert root.attrib["viewBox"]==f"0 0 {W} {H}"
        paths.append(path)
    (SITE/"downloads").mkdir(parents=True,exist_ok=True)
    pdf=SITE/"downloads/prosperity-architecture-p44-atlas.pdf"
    render_atlas(paths,pdf)
    page_file=SITE/"prosperity-architecture.html"
    page_file.write_text(page(data,info),encoding="utf-8")
    (OUT/"README.md").write_text(
        "P4.4 六类已报道门制、柱础和结构解释，三张本项目原创示意图。\n"
        "图式不提供任何地理配准、真实古高、屋顶颜色和完整院界。\n"
        "上层阁道、楼观层数、排叉柱过梁、两面坡廊庑来自研究解释，应与遗迹读数分层。\n"
        "2016/2018东閤门尺寸与西端门身份异记独立保留，不平均、不合并。\n",
        encoding="utf-8")
    previous=SITE/"prosperity-palace-boundaries.html"
    existing=previous.read_text(encoding="utf-8")
    marker='<footer><a href="./prosperity-taiji-courts.html">'
    assert existing.count(marker)==1
    addition=(
        '<section id="p44-next"><h2>新专题 P4.4：宫门与院门的真实类型差异</h2>'
        '<p><a href="./prosperity-architecture.html">进入P4.4：六类宫门、阁道与廊院结构 →</a></p>'
        '<p>保留本页P4.3三套报告尺度，不把新建筑类型推演成实际宫墙或上部屋顶高度。</p></section>'
    )
    previous.write_text(existing.replace(marker,addition+marker),encoding="utf-8")
    members={f"prosperity-architecture/{p.name}":p for p in sorted(OUT.iterdir()) if p.is_file()}
    members["prosperity-architecture.html"]=page_file
    members[f"downloads/{pdf.name}"]=pdf
    dump(OUT/"bundle-manifest.json",{
       "version":VERSION,"source_commit":info["source_commit"],
       "files_sha256":{name:digest(item) for name,item in members.items()}
    })
    members["prosperity-architecture/bundle-manifest.json"]=OUT/"bundle-manifest.json"
    with zipfile.ZipFile(SITE/"downloads/prosperity-architecture-p44-package.zip","w",zipfile.ZIP_DEFLATED) as archive:
        for name,item in members.items():
            archive.write(item,name)
    release=read(SITE/"release.json")
    release["extensions"]=sorted(set(release.get("extensions",[])+[VERSION]))
    release["prosperity_architecture_version"]=VERSION
    release["current_milestone"]="盛时P4.4：宫城六类门制、柱础与廊庑差异研究"
    dump(SITE/"release.json",release)
    info["prosperity_architecture"]={
       "version":VERSION,"source_commit":info["source_commit"],
       "types":len(data["types"]),"source_count":len(data["sources"]),
       "plates":len(figures),"atlas_pages":len(figures),"new_absolute_ancient_coordinates":0,
       "common_geographic_controls":0,
       "metadata":"prosperity-architecture/data.json"
    }
    info["files_sha256"]={str(p.relative_to(SITE)):digest(p)
                           for p in sorted(SITE.rglob("*")) if p.is_file() and p.name!="build-info.json"}
    dump(SITE/"build-info.json",info)
    print(json.dumps(info["prosperity_architecture"],ensure_ascii=False))

if __name__=="__main__":
    main()
