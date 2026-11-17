#!/usr/bin/env python3
"""P4: reproducible source-scoped segment and footprint review, never city registration."""
from pathlib import Path
import csv
import hashlib
import html
import io
import json
import math
import shutil
import xml.etree.ElementTree as ET
import zipfile

from north_b4 import render_atlas

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
OUT = SITE / "prosperity-axis"
DATA = ROOT / "research/prosperity-v4/axis-measurements.json"
VERSION = "prosperity-axis-p4-metric-review"
VIEWBOX = "0 0 1440 840"

def esc(x):
    return html.escape(str(x), quote=True)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def dump(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def text(x, y, label, size=25, color="#2c4740", weight=500, anchor="start"):
    return (f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" fill="{color}" '
            f'font-family="Noto Sans CJK SC,Microsoft YaHei,sans-serif" '
            f'font-size="{size}" font-weight="{weight}">{esc(label)}</text>')

def box(x,y,w,h,fill="#ffffff",stroke="#d3dcd5",r=14):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}"/>'

def start_svg(title, subtitle):
    return ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="'+VIEWBOX+'" role="img" aria-label="'+esc(title)+'">',
            '<rect width="1440" height="840" fill="#f6f5ef"/>',
            text(60,65,"盛时洛阳 · P4 考古尺度证据",20,"#738f81",600),
            text(60,119,title,40,"#213e35",700),
            text(60,162,subtitle,20,"#667a70"),
            '<path d="M60 189H1380" stroke="#d8dfd8" stroke-width="2"/>']

def end_svg(parts, foot):
    parts.append('<path d="M60 779H1380" stroke="#d8dfd8"/>')
    parts.append(text(60,809,foot,18,"#65766d"))
    parts.append('</svg>')
    return "\n".join(parts) + "\n"

def svg_metric(d):
    segments=d["axis_segments"]
    values=[s["length_m"] for s in segments]
    total=sum(values)
    assert values==[95,80,300] and total==d["chain_sum_m"]==475
    alternative=d["independent_report"]["distance_m"]
    assert alternative==460 and total-alternative==d["comparison_difference_m"]==15
    p=start_svg("三段距离与一个不同口径的总距","所有数字为文献报告的近似值；轴线上图示位置仅按分段报道作累计，不是城市坐标。")
    x0=154
    s=1.95
    xs=[x0,x0+95*s,x0+175*s,x0+475*s]
    p.append(box(70,215,1300,366))
    for i,(a,b) in enumerate(zip(xs[:-1],xs[1:])):
        p.append(f'<path d="M{a:.2f} 366 H{b:.2f}" stroke="{["#327f72","#8e9a66","#bb8450"][i]}" stroke-width="14" stroke-linecap="round"/>')
        p.append(text((a+b)/2,333,f"{values[i]} m",28,"#29473f",700,"middle"))
    labels=["阊阖门","二号宫门","三号宫门","太极殿"]
    for x,l in zip(xs,labels):
        p.append(f'<circle cx="{x:.2f}" cy="366" r="12" fill="#244e43" stroke="#fff" stroke-width="4"/>')
        p.append(text(x,410,l,21,"#304c43",600,"middle"))
    p.append(text(99,475,"分段相加",21,"#3b5e52",600))
    p.append(text(285,476,"95 + 80 + 300 = 475 m（推算，仅作对读）",22,"#3b5e52"))
    p.append(box(70,602,1300,144,fill="#f4eadc",stroke="#d8c0a8"))
    p.append(text(100,641,"另一机构报道",23,"#86633b",600))
    p.append(text(350,641,"阊阖门 → 太极殿：约 460 m",26,"#86633b",700))
    p.append(text(100,690,"表面差额约 15 m，原报告未核清端点、测线及取整方式；不能判定为遗址冲突。",21,"#6a5b43"))
    return end_svg(p,"来源：钱国祥2012中文报告（分段值）；洛阳市考古研究院2024（总距）。")

def phase_geometry(d):
    phases=d["third_gate"]
    specs=[
       ("early","魏晋—北魏早期残存部分",40,10,phases["early"]["remarks"],"#438b7d"),
       ("middle","北魏晚期或以后中期夯土",55,45,phases["middle"]["remarks"],"#ae8a51"),
       ("late","北周时期晚期柱网基址",40,10,phases["late"]["remarks"],"#80677b")]
    p=start_svg("三号宫门：三层遗存不应叠成一座建筑","下方平面块按报告长宽取同一示意比例；各期边框在这里并排对读，未地理重叠。")
    for idx,(key,label,w,h,note,col) in enumerate(specs):
        x=70+idx*460
        p.append(box(x,218,432,470))
        p.append(text(x+18,258,label,23,"#29473e",700))
        p.append(text(x+18,307,f"东西 {w:g} m · 南北 {'残' if key!='middle' else ''}{h:g} m",22,"#65786e"))
        px=4.3
        aw=w*px; ah=h*px
        cx=x+216; cy=453
        p.append(f'<rect x="{cx-aw/2:.2f}" y="{cy-ah/2:.2f}" width="{aw:.2f}" height="{ah:.2f}" fill="{col}" fill-opacity=".21" stroke="{col}" stroke-width="4"'+ (' stroke-dasharray="11 7"' if key!="middle" else '')+'/>')
        p.append(text(cx,cy+6,"残部" if key!="middle" else "中期大夯土",23,col,700,"middle"))
        p.append(text(x+18,608,("保留残部 ≠ 原门总体" if key=="early" else "含较早瓦片 ≠ 营建定年" if key=="middle" else "后期柱网 ≠ 北魏柱网"),21,"#8a5d40",600))
    return end_svg(p,"这些是不同层位的残存范围/改建范围，不能反向补成某年门址完整平面。")

def svg_taiji(d):
    t=d["taiji"]
    m=t["main_hall"]; e=t["east_hall"]
    assert m["north_width_m"]==102.3 and m["south_width_m"]==98.4
    assert m["ns_depth_m_reported"]==[59,61.5] and e["reported_gap_from_main_east_m"]==14
    p=start_svg("太极殿与东堂：建筑体量不必相同","同一米尺比较殿基尺寸；图中南北对齐纯属编排，不能作为考古测得的相对纵向坐标。")
    p.append(box(62,218,1316,480))
    scale=3.3
    m_n=m["north_width_m"]*scale; m_s=m["south_width_m"]*scale; h=61.5*scale
    x=420; y=480
    points=f"{x-m_n/2:.2f},{y-h/2:.2f} {x+m_n/2:.2f},{y-h/2:.2f} {x+m_s/2:.2f},{y+h/2:.2f} {x-m_s/2:.2f},{y+h/2:.2f}"
    p.append(f'<polygon points="{points}" fill="#6f9990" fill-opacity=".28" stroke="#236a64" stroke-width="4"/>')
    p.append(text(x,y-8,"太极殿主殿台基",24,"#23594d",700,"middle"))
    p.append(text(x,y+30,"深 59—61.5 m",21,"#23594d",500,"middle"))
    p.append(text(x,y-h/2-18,"北边 102.3 m",22,"#2f5447",600,"middle"))
    p.append(text(x,y+h/2+35,"南边 98.4 m",22,"#2f5447",600,"middle"))
    # East-side separation is measured, but the y-position drawn below is not.
    eastleft=(x+m_n/2)+e["reported_gap_from_main_east_m"]*scale
    ew=e["ew_m"]*scale; ns=e["ns_m"]*scale
    ex=eastleft; ey=y-50
    p.append(f'<rect x="{ex:.2f}" y="{ey:.2f}" width="{ew:.2f}" height="{ns:.2f}" fill="#b4a06f" fill-opacity=".29" stroke="#a48245" stroke-width="4"/>')
    p.append(text(ex+ew/2,ey+ns/2+7,"太极东堂",22,"#8c6d36",700,"middle"))
    p.append(text(ex+ew/2,ey-17,"48 × 23 m",22,"#795d36",600,"middle"))
    ygap=ey+ns/2
    p.append(f'<path d="M{x+m_n/2:.2f} {ygap:.2f} H{ex:.2f}" stroke="#b25841" stroke-width="3" stroke-dasharray="7 5"/>')
    p.append(text((x+m_n/2+ex)/2,ygap-13,"14 m",18,"#b25841",700,"middle"))
    p.append(text(925,350,"太极西堂：存在有据",25,"#385a50",600))
    p.append(text(925,397,"本轮未取得独立尺寸",22,"#536f64"))
    p.append(text(925,438,"不复制东堂为对称模型",22,"#b06d54"))
    return end_svg(p,"来源：徐龙国《两汉魏晋南北朝都城建筑的发展演变》；各期台基与建筑屋顶不可混同。")

def csv_rows(d):
    buf=io.StringIO()
    writer=csv.writer(buf)
    writer.writerow(["kind","id","property","value_m","uncertainty_or_limits","source_ids"])
    for row in d["axis_segments"]:
        writer.writerow(["axis_segment",row["id"],row["from"]+" → "+row["to"],row["length_m"],row["qualifier"],";".join(row["source_ids"])])
    writer.writerow(["alternative_total","independent_total","阊阖门 → 太极殿",d["independent_report"]["distance_m"],"端点未核同", "LUOYANG2024"])
    m=d["taiji"]["main_hall"]
    for key in ["north_width_m","south_width_m"]:
        writer.writerow(["taiji_main","main",key,m[key],"不同边长，不画规则矩形","XU2020"])
    for i,value in enumerate(m["ns_depth_m_reported"]):
        writer.writerow(["taiji_main","main",["ns_depth_lower","ns_depth_upper"][i],value,"59—61.5m报道范围","XU2020"])
    for key,value in d["taiji"]["east_hall"].items():
        if key in ["ew_m","ns_m","reported_gap_from_main_east_m"]:
            writer.writerow(["taiji_east","east_hall",key,value,"东堂南北偏移未核","XU2020"])
    for key in ["early","middle","late"]:
        item=d["third_gate"][key]
        for k,v in item.items():
            if k.endswith("_m_approx"):
                writer.writerow(["third_gate_phase",key,k,v,"不同时期基址不可相互覆盖","QIAN2012"])
    return buf.getvalue()

def html_page(d, figures, info):
    src={item["id"]:item for item in d["sources"]}
    def link(key, text=None):
        obj=src[key]
        return '<a href="'+esc(obj["url"])+'" target="_blank" rel="noopener">'+esc(text or obj["title"])+" ↗</a>"
    cited="".join(
      '<li><strong>'+esc(x["author"])+'</strong> · '+esc(x["title"])+'（'+esc(x["locator"])+'）'
      +'<p>'+esc(x["note"])+'</p>'+link(x["id"],"打开公开原件")+"</li>"
      for x in d["sources"])
    phase_items=[]
    for key,label in [("early","魏晋—北魏早期残部"),("middle","北魏晚期或以后"),("late","北周晚期柱网")]:
        item=d["third_gate"][key]
        phase_items.append(
          '<section class="phase-detail" data-phase-card="'+key+'"'+('' if key=="early" else ' hidden')+'>'
          '<h3>'+esc(label)+'</h3><p>'+esc(item["remarks"])+'</p>'
          '<p class="sm">只报告此期现存范围；不将其当作早期完整门基或单一盛时建筑。</p></section>')
    content=f"""<!doctype html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>盛时洛阳 · 宫城中轴考古尺度与分期</title>
<meta name="description" content="阊阖门—二号宫门—三号宫门—太极殿的分段量距、道路、分期与原刊考古图核查。">
<link rel="stylesheet" href="./prosperity-axis/style.css"></head><body>
<header class="top"><a class="brand" href="./">洛 <span>盛时洛阳 · 考古空间研究</span></a>
<nav aria-label="研究导航"><a href="./prosperity.html">盛时总图</a><a href="./prosperity-gate.html#source-comparison">阊阖门原图对比</a><a href="./prosperity-axis-sources.html">原刊异记对照 P4.1</a><a href="./prosperity-taiji-courts.html">太极殿院落 P4.2</a><a href="#originals">原始图版</a><a href="#download">下载</a></nav></header>
<main class="shell">
<section class="hero"><p class="eyebrow">P4 · 中轴量距与时层审查</p>
<h1>一座宫城，不能只靠四个点画出来。</h1>
<p class="lead">这次把已有的南北次序推进为可追查的<strong>分段量距、二号门道路、三号门层位</strong>与<strong>太极殿／东堂尺度</strong>。
每组图都注明取自哪份研究报告；图中的排列不等于新的地理配准。</p>
<div class="stats"><div><b>3</b><span>考古报告中的分段距离</span></div><div><b>15 m</b><span>两种总距口径的表面差额</span></div><div><b>0</b><span>已获独立共同控制点</span></div></div></section>
<section class="section" id="distance"><div class="section-head"><span>01 · 量距</span><h2>阊阖门至太极殿，分段量距是怎样描述的</h2></div>
<p>钱国祥2012年报告给出约95、80、300米的连续关系，相加为约475米；洛阳市考古研究院2024年报道总距约460米。
两者相差约15米，但端点、路径与取整方法尚未核对，因此不标记为已证实的史料冲突。{link("QIAN2012","中文原始报告")} · {link("LUOYANG2024","机构报道")}</p>
<figure class="figure"><img src="./prosperity-axis/axis-segments.svg" alt="阊阖门到二号宫门95米，二号到三号80米，三号到太极殿300米；约475米相对约460米另报总距。"><figcaption>研究量距示意，不是基于共同控制点的遗址总图；箭头不代表真实通道宽度。</figcaption></figure></section>
<section class="section" id="roads"><div class="section-head"><span>02 · 道路</span><h2>二号宫门不是孤立的一座大殿</h2></div>
<div class="facts"><article><strong>44.5 × 24 m</strong><span>二号门夯土台基，约值</span></article>
<article><strong>三门道</strong><span>未见阊阖门式双阙</span></article>
<article><strong>7.9–8.1 m</strong><span>门道前后南北向包砖道路宽度</span></article>
<article><strong>约 10 m</strong><span>门南、门北东西向道路宽度</span></article></div>
<p>报告还记载东西向道路分别在二号门南侧约23米、北侧约40米，并发现约1.2米间距的车辙。
这些距离没有在本轮被解释成“距门基几何中心”，所以暂不画精确道路边界。{link("QIAN2012","原报告道路段")}</p></section>
<section class="section" id="phases"><div class="section-head"><span>03 · 叠压</span><h2>三号宫门：早期残基、中期夯土、晚期柱网必须分开</h2></div>
<figure class="figure"><img src="./prosperity-axis/third-gate-phases.svg" alt="三号宫门三个时期残存基址尺寸示意：早期40乘10米残部、中期55乘45米夯土、北周40乘10米柱网基址。"><figcaption>以同一图尺展示每期报告的范围，但三组框不是已经重合的实测分期套图。</figcaption></figure>
<div class="phase-controls" role="group" aria-label="选择三号宫门分期" id="phase-controls">
<button type="button" data-phase="early" aria-pressed="true">早期残部</button><button type="button" data-phase="middle" aria-pressed="false">中期夯土</button>
<button type="button" data-phase="late" aria-pressed="false">晚期柱网</button></div>
<div class="phase-inspector">{''.join(phase_items)}</div>
<p><strong>研究约束：</strong>三号宫门北半部受到后期扰动，早期40×10米是残存尺寸；中期55×45米是否属于北魏盛时尚未证实。不能用晚期完整柱网替代早期殿堂式宫门。{link("QIAN2012","原报告分期段")}</p></section>
<section class="section" id="taiji"><div class="section-head"><span>04 · 建筑尺度</span><h2>太极殿主殿和东堂的确不是同一种体量</h2></div>
<figure class="figure"><img src="./prosperity-axis/taiji-dimensions.svg" alt="太极殿主殿北宽102.3米南宽98.4米、南北深59至61.5米，太极东堂48乘23米，东侧间距14米；西堂仅标存在不补尺寸。"><figcaption>主殿保留南北不同宽度。东堂在图中的南北对齐仅为排版；西堂没有本轮独立尺寸，不复制东堂生成对称形状。</figcaption></figure>
<p>{link("XU2020","考古研究与图三")}记载太极殿主殿北边102.3米、南边98.4米、进深59—61.5米，东堂48×23米，东堂在主殿以东约14米。这里画的是台基尺度比较，不是盛时屋顶与楼高。</p>
<p>太极殿宫院东北角另有东西长96米、南北残长27米的院落记录和约4.7米夹道。它们是<strong>局部残存院落</strong>，不能当作整个宫院的尺寸。{link("HENAN2017","省考古机构报道")}</p></section>
<section class="section" id="originals"><div class="section-head"><span>05 · 原始图版</span><h2>直接核对出版的考古平面，不再只看我们的示意</h2></div>
<div class="source-grid"><article><h3>2013 年 · 宫城平面原图</h3><p>奈良文化财研究所《纪要2013》第52页图69：宫城、城墙、门殿及0—200m图内标尺。图中“一号门”和“阊阖门”指向同一宫城正门的考古编号与历史名称；此对应已在后续图证专题核查。</p>{link("NARA2013","打开原刊PDF的图69")}</article>
<article><h3>2012 年 · 中文考古报告</h3><p>钱国祥《汉魏洛阳故城北魏宫城中枢区南部的合作勘察》，中文部分第28—30页，记二、三号门及道路分期。其日文译文与中文稿属同一研究来源链。</p>{link("QIAN2012","打开2012会议原刊PDF")}</article>
<article><h3>太极殿 · 研究平面图</h3><p>徐龙国《两汉魏晋南北朝都城建筑的发展演变》，图三及太极殿主殿/东堂尺寸。此处提供原刊链接，未声称获得独立精测CAD。</p>{link("XU2020","打开原刊太极殿平面")}</article>
<article><h3>阊阖门 · 原生平剖图</h3><p>本站P3已提供同像素描线、原图叠照和完整出处；可直接进入交互比较。</p><p>{link("UNESCO-S37","打开阊阖门考古原图所在的申遗文档")}</p><a href="./prosperity-gate.html#source-comparison">打开已上线的原图对比 ↗</a></article></div></section>
<section class="section" id="source-audit"><div class="section-head"><span>新研究 · P4.1</span><h2>同一中轴为什么出现200米与300米两种写法？</h2></div><p>奈文研2011年调查概要写三号门至太极殿约200米，而钱国祥研究写约300米。后一种说法得出的475米累计只是一种读法，不是所有材料的共识。已把原刊图号、一号门命名和二号门23／24米之差放入独立专题。</p><p><a href="./prosperity-axis-sources.html">进入 P4.1：原始考古图证与测距异记对照 →</a></p></section>
<section class="section" id="download"><div class="section-head"><span>06 · 可复核文件</span><h2>本轮成果与未解决问题</h2></div>
<div class="downloads"><a href="./downloads/prosperity-axis-v4-atlas.pdf">三页考古尺度图册 PDF</a>
<a href="./downloads/prosperity-axis-v4-package.zip">完整研究资料 ZIP</a>
<a href="./prosperity-axis/data.json">分段、分期与来源 JSON</a><a href="./prosperity-axis/measurements.csv">量距 CSV</a></div>
<p><strong>未完成：</strong>二号、三号门的原始独立测绘图逐点量读、原图控制点和坐标基准；太极殿宫院各阶段精确叠合；516—528年的完整道路与院界。所有这些项目均保持未解状态。</p></section>
<footer><a href="./prosperity-gate.html">返回阊阖门局部原件</a><span id="version-stamp">P4 · {esc(info['source_commit'][:8])} · 研究性图式</span></footer>
</main><script src="./prosperity-axis/app.js"></script></body></html>"""
    return content

def main():
    d=read(DATA)
    assert d["version"]==VERSION
    assert [r["length_m"] for r in d["axis_segments"]]==[95,80,300]
    assert d["comparison_difference_m"]==d["chain_sum_m"]-d["independent_report"]["distance_m"]
    assert d["comparison_status"].startswith("unspecified_reference_points")
    assert d["registration"]["verified_common_controls"]==0
    assert d["registration"]["absolute_points_added"]==0
    assert d["third_gate"]["early"]["kind"]=="surviving_not_original_full_footprint"
    assert d["third_gate"]["middle"]["kind"]=="later_disturbance_ram_earth"
    assert d["taiji"]["west_hall"]["geometry"] is None
    info=read(SITE/"build-info.json")
    assert info["prosperity_gate"]["version"]=="prosperity-gate-v3"
    assert not (SITE/"prosperity-axis.html").exists(), "The P4 page should be generated afresh"
    OUT.mkdir(parents=True,exist_ok=True)
    for source, dest in [("web/prosperity-axis-v4.css","style.css"),("web/prosperity-axis-v4.js","app.js")]:
        shutil.copyfile(ROOT/source,OUT/dest)
    dump(OUT/"data.json",d)
    (OUT/"measurements.csv").write_text(csv_rows(d),encoding="utf-8-sig")
    figures=[
        ("axis-segments.svg",svg_metric(d)),
        ("third-gate-phases.svg",phase_geometry(d)),
        ("taiji-dimensions.svg",svg_taiji(d))]
    paths=[]
    for filename,content in figures:
        path=OUT/filename
        path.write_text(content,encoding="utf-8")
        node=ET.fromstring(content)
        assert node.tag=="{http://www.w3.org/2000/svg}svg"
        assert node.get("viewBox")==VIEWBOX
        paths.append(path)
    (SITE/"downloads").mkdir(parents=True,exist_ok=True)
    atlas=SITE/"downloads/prosperity-axis-v4-atlas.pdf"
    render_atlas(paths,atlas)
    page=SITE/"prosperity-axis.html"
    page.write_text(html_page(d,figures,info),encoding="utf-8")
    readme=OUT/"README.md"
    readme.write_text(
      "# P4: 宫城中轴距离与分期研究\n\n"
      "先看 axis-segments.svg；比较460m与475m时请保留量距口径差异。\n"
      "third-gate-phases.svg展示三个时期，不可叠为一个时期的完整遗址。\n"
      "taiji-dimensions.svg只采用主殿与东堂本批已有尺寸，西堂不补形。\n"
      "正式图源连接保存在 data.json 中，原刊PDF因版权与文件体积不重新打包。\n"
      "外部共同控制点零，原始考古DWG/CAD未取得，古地面、屋顶和古河道未复原。\n",encoding="utf-8")
    members={f"prosperity-axis/{p.name}":p for p in sorted(OUT.iterdir()) if p.is_file()}
    members["prosperity-axis.html"]=page
    members[f"downloads/{atlas.name}"]=atlas
    manifest={"version":VERSION,"source_commit":info["source_commit"],"files_sha256":{name:digest(p) for name,p in members.items()}}
    dump(OUT/"bundle-manifest.json",manifest)
    members["prosperity-axis/bundle-manifest.json"]=OUT/"bundle-manifest.json"
    zip_path=SITE/"downloads/prosperity-axis-v4-package.zip"
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as archive:
        for name,path in members.items():
            archive.write(path,name)
    release=read(SITE/"release.json")
    release["extensions"]=sorted(set(release.get("extensions",[])+[VERSION]))
    release["prosperity_axis_version"]=VERSION
    release["current_milestone"]="盛时P4：宫城中轴考古量距与分期审阅"
    dump(SITE/"release.json",release)
    info["prosperity_axis"]={"version":VERSION,"source_commit":info["source_commit"],
                              "figure_count":len(figures),"source_count":len(d["sources"]),
                              "atlas_pages":len(figures),"unresolved_registration":True,
                              "absolute_points_added":0,
                              "metadata":"prosperity-axis/data.json"}
    info["files_sha256"]={str(path.relative_to(SITE)):digest(path) for path in sorted(SITE.rglob("*"))
                          if path.is_file() and path.name!="build-info.json"}
    dump(SITE/"build-info.json",info)
    print(json.dumps(info["prosperity_axis"],ensure_ascii=False))

if __name__=="__main__":
    main()
