#!/usr/bin/env python3
"""P4.1 independently auditable source-image inventory and competing-distance exhibit."""
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
OUT=SITE/"prosperity-axis-sources"
INPUT=ROOT/"research/prosperity-v4/primary-source-audit.json"
VERSION="prosperity-axis-p41-source-audit"

def esc(s):return html.escape(str(s),quote=True)
def load(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def txt(x,y,s,size=24,color="#263f36",weight=500,anchor="start"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" font-family="Noto Sans CJK SC,Microsoft YaHei,sans-serif" '
            f'fill="{color}">{esc(s)}</text>')
def rect(x,y,w,h,fill="#fffdf7",stroke="#d8ded5",r=9):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" />'
def base(title,subtitle):
    return ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000" role="img" '
            'aria-label="'+esc(title)+'">',
            '<rect width="1600" height="1000" fill="#f7f6f0"/>',
            txt(65,62,"盛时洛阳 · P4.1 原刊图证校核",22,"#687e73",600),
            txt(65,125,title,42,"#243e36",700),
            txt(65,163,subtitle,22,"#63776e"),
            '<path d="M65 193H1530" stroke="#d8dfd8" stroke-width="2"/>']
def close(parts,foot):
    parts.extend(['<path d="M65 928H1530" stroke="#d8dfd8" stroke-width="2"/>',
                  txt(65,966,foot,19,"#6e7f74"),'</svg>'])
    return "\n".join(parts)+"\n"

def svg_alternatives(d):
    a=d["alternatives"]
    assert len(a)==2
    x0=157; scale=2.12
    shared=95+80
    p=base("同一中轴的两种距离记录","2009—2013 原刊归属对读：数字为报道近似值，不是已配准的城市平面。")
    p.append(rect(65,217,1470,598))
    for idx,row in enumerate(a):
        y=348+idx*268
        col="#3b8274" if idx==0 else "#ad7848"
        p.append(txt(98,y-72,"奈文研 2011：约 200 m" if idx==0 else "钱国祥研究：约 300 m",29,col,700))
        points=[x0,x0+95*scale,x0+175*scale,x0+(175+row["third_to_taiji_m"])*scale]
        for segnum,(a1,a2) in enumerate(zip(points[:-1],points[1:])):
            p.append(f'<path d="M{a1:.2f} {y}H{a2:.2f}" stroke="{["#789787","#789787",col][segnum]}" stroke-width="13" stroke-linecap="round"/>')
            p.append(txt((a1+a2)/2,y-20,["95 m","80 m",str(row["third_to_taiji_m"])+" m"][segnum],21,"#305448",650,"middle"))
        for x,label in zip(points,["阊阖门","二号门","三号门","太极殿"]):
            p.append(f'<circle cx="{x:.2f}" cy="{y}" r="11" fill="#315d4f" stroke="#fff" stroke-width="3"/>')
            p.append(txt(round(x),y+34,label,19,"#375b50",600,"middle"))
        p.append(txt(97,y+83,f'分段累计 ≈ {row["sum_m"]} m',26,col,700))
        p.append(txt(460,y+83,f'与机构另报约460m相比：{row["difference_vs_external_m"]:+g}m',22,"#766a5a"))
    p.append(rect(75,841,1450,65,fill="#f0ede2"))
    p.append(txt(94,883,"不要把两组报道叠成一张唯一坐标地图；比例仅表达各自数字中的相对长度。",22,"#6e5f48"))
    return close(p,"来源：奈文研2011，钱国祥2012/译稿与洛阳市考古研究院2024；端点与测线均待核。")

def svg_source_inventory(d):
    p=base("到底取得了哪些考古原图？","逐份区分机构公开图、钻探示意、发掘照片和未取得的《考古》正式平面。")
    arr=[
      ("2009 奈文研","图25、26宫城结构；图27阊阖门","二号门：只有现场照片／概略，未得完整带尺平面","#326f5f"),
      ("2010 奈文研","图20宫城关系；图21阊阖门构造","三号门：主要是图23—25现场照片，非全站点平面","#93765b"),
      ("2011 奈文研","图7宫城布局及一/二/三号门","已核看原刊图7；记录三号门到太极殿约200米","#436f91"),
      ("2013 奈文研","图69宫城总图，比例尺0—200m","一号门与阊阖门是编号/历史名称对应，不增新门","#457c66"),
      ("《考古》2009/2010","联合考古队正式二/三号门简报","题名与期号已核；原版完整测绘图尚未取得","#a4654a")]
    x=75
    for idx,(name,have,limit,col) in enumerate(arr):
        y=224+idx*132
        p.append(rect(x,y,1448,113,fill="#fffdf8"))
        p.append(f'<rect x="{x}" y="{y}" width="8" height="113" fill="{col}"/>')
        p.append(txt(108,y+40,name,27,col,700))
        p.append(txt(453,y+42,have,22,"#2b4d42",600))
        p.append(txt(453,y+79,limit,20,"#69776e"))
    return close(p,"原刊链接、页码、图号、传承关系和获取状态，详见研究数据及站点的来源卡。")

def csv_data(d):
    out=io.StringIO()
    w=csv.writer(out)
    w.writerow(["topic","source_id","year","reported_value_m","detail","status"])
    for item in d["distance_conflicts"]:
        s=next(x for x in d["sources"] if x["id"]==item["source_ids"][0])
        w.writerow(["gate3_to_taiji",s["id"],s["year"],item["distance_m"],item["position_reference"],"approx_endpoints_unknown"])
    for row in d["second_gate_phased_dimensions"]:
        w.writerow(["gate2_ns_width",row["source_id"],row["publish_year"],row["north_south_m"],
                   row["scope"],"reported_estimate"])
    for item in d["alternatives"]:
        w.writerow(["computed_chain",item["source_ids"][0],"",item["sum_m"],
                    item["name"],"derived_not_independent_survey"])
    return out.getvalue()

def source_cards(d):
    cards=[]
    for item in d["sources"]:
        if item["source_kind"]=="formal-excavation-journal-not-accessed":
            status="原刊图件待取得"
        elif item["id"] in ["NARA2011","NARA2013"]:
            status="公开原刊图已核看"
        else:status="公开资料已核／仍有缺图"
        url=item["url"]+(item.get("page_fragment") or "")
        # URL already contains page= for some sources
        if item.get("page_fragment") and "#page=" in item["url"]:url=item["url"]
        fig="、".join(item.get("figure_refs",[]))
        if len(fig)>190:fig=fig[:185]+"…"
        cards.append(
            '<article class="source-card"><p class="source-status">'+esc(status)+'</p>'
            '<h3>'+esc(item["year"])+' · '+esc(item["title"])+'</h3>'
            '<p>'+esc(item["publication"])+'</p>'
            '<p><strong>已查图号：</strong>'+esc(fig or "本轮未取得可复核原刊插图")+'</p>'
            '<p class="source-limit">'+esc(item["assessment"])+'</p>'
            '<a target="_blank" rel="noopener" href="'+esc(url)+'">'+
            ('打开引用该文的机构目录 ↗' if item["source_kind"]=="formal-excavation-journal-not-accessed" else '直接打开来源 PDF / 文章 ↗')+'</a>'
            '</article>')
    return "\n".join(cards)

def page_html(d, info):
    fig_sources=source_cards(d)
    return f"""<!doctype html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="北魏洛阳宫城原刊考古图对比：一号门与阊阖门、三号门至太极殿200/300米异记、二号门23/24米尺寸差及取得原刊状态。">
<title>盛时洛阳 · 宫城考古原刊图证复核 P4.1</title>
<link rel="stylesheet" href="./prosperity-axis-sources/style.css"></head><body>
<header><a href="./">洛 · 盛时洛阳</a><nav aria-label="研究导航">
<a href="./prosperity-axis.html">返回中轴尺度 P4</a><a href="./prosperity-gate.html#source-comparison">阊阖门原图</a>
<a href="#sources">逐份查看原刊图</a></nav></header>
<main><section class="intro"><p class="eyebrow">P4.1 · 原始考古图源校核</p>
<h1>同一座宫门的两个名字，同一段距离的两种记法。</h1>
<p>这不是一张新的“标准答案地图”。我们把原刊图、考古编号、不同阶段量距和缺失图件放在同一页面，
使读者能在<strong>解释历史城市</strong>之前，先检查我们实际持有什么证据。</p>
<div class="headline-stats"><div><b>1</b><span>已核对的编号／历史门名关系</span></div>
<div><b>2</b><span>三号门—太极殿相互冲突的约值</span></div>
<div><b>0</b><span>新增地理实测控制点</span></div></div></section>
<section class="group" id="identity"><p class="eyebrow">01 · 编号与身份</p><h2>“一号门”不等于新增一座宫城正门</h2>
<p>奈文研2011年研究正文将宫城正门称为<strong>一号建筑遗构／一号门</strong>，
并与二、三号门及太极殿排列在宫城中轴。2013年图69则将“一号门”和“阊阖门”标注于同一宫城南部正门位置。
结合2009年有关阊阖门的发掘说明，我们把它们记录为<strong>同一遗址的考古编号与历史门名</strong>，不再误建第二座门。</p>
<p class="notice">这是一项对象身份判断，不意味着我们已经确认图69的像素与P3原件之间存在独立地理配准。</p>
<p><a href="https://repository.nabunken.go.jp/dspace/bitstream/11177/1974/1/BA67898227_2011_006_007.pdf#page=1" target="_blank" rel="noopener">原图：2011年第6页图7 ↗</a>
　<a href="https://repository.nabunken.go.jp/dspace/bitstream/11177/6157/1/BA67898227_2013_052_053.pdf#page=1" target="_blank" rel="noopener">原图：2013年第52页图69 ↗</a></p></section>
<section class="group" id="distance"><p class="eyebrow">02 · 距离异记</p><h2>约200米还是约300米？两种情况都要保留</h2>
<p>奈文研2011年调查概要记三号宫门至太极殿约200米；
钱国祥研究报告及后续译稿记约300米。同一研究项目不同发表文本存在约100米差距，尚不清楚是否来自测量端点、
对应遗址范围、修订或文字错误。不能依据文献数目投票，也不能直接判定某一方错误。</p>
<figure><img src="./prosperity-axis-sources/distance-comparison.svg" alt="2011采用三号门到太极殿200米时，三段累计375米；另一份报告采用300米时累计475米；另报总距约460米。">
<figcaption>图中两列共享95、80米报告值，第三段保留200或300米两种说法；展示的是数字方案，不是测得的古址经纬度。</figcaption></figure>
<div class="scenario-controls"><label for="scenario">查看某一种报告口径：</label>
<select id="scenario"><option value="nara2011">奈文研2011 · 200米</option><option value="qian2012">钱国祥研究 · 300米</option></select>
<div id="scenario-output" class="scenario-output" aria-live="polite">奈文研2011：累计约375米；与另报总距约460米相差约-85米。该差额不是考古测量误差区间。</div></div>
<p class="notice">原有 P4 页面比较的475米与460米差15米只对应300米假设；若采用2011年200米说法，同样相加则为375米，
与460米差85米。两组累计都不是独立田野总距，更不应强行拟合成一致的城市位置。</p></section>
<section class="group" id="width"><p class="eyebrow">03 · 尺度差异</p><h2>二号门“23米”与“24米”来自不同阶段的发表</h2>
<p>奈文研2009年的二号门初期报告称东西约44.5米、南北约23米，
2010年后续研究称东西约44.5米、南北约24米。后者与P4既有约24米记录一致，
但我们没有取得可比较的两版完整测量边线；因此这次把两个阶段数值并列保存。</p></section>
<section class="group" id="figures"><p class="eyebrow">04 · 实际图件</p>
<h2>哪些原始图已经核看，哪些还只是线索</h2>
<figure><img src="./prosperity-axis-sources/figure-inventory.svg" alt="2009、2010、2011、2013奈文研报告及《考古》正式简报的图版取得状态。">
<figcaption>这是本项目的图源清单，不是对原刊图版的改绘。版权原图通过下方直接链接打开，站内不复制整份学术PDF。</figcaption></figure>
<div class="source-grid" id="sources">{fig_sources}</div></section>
<section class="group" id="limits"><p class="eyebrow">05 · 下一项可复核工作</p>
<h2>仍然缺的是《考古》正式简报的平面图和同一套测量控制</h2>
<p>目前已取得2009、2010、2011、2013年奈文研公开概要与主要图注，但尚未独立取得《考古》2009年第5期
二号建筑遗址、2010年第6期三号建筑遗址的<strong>完整、可逐点读线的原始测绘平面</strong>。
因此这一步仍不新增宫门绝对坐标，无法把两份距离说法合成一张唯一宫城分期图。</p>
<p>需要进一步核查正式简报的图版版次、比例尺、太极殿对应的南北边界及量距起讫点；之后才能将可辨轮廓
与既有阊阖门P3同类地记录局部像素—米制关系。未证之处继续留白。</p></section>
<section class="group" id="downloads"><p class="eyebrow">06 · 数据与图册</p><h2>可下载的研究成果</h2>
<div class="downloads"><a href="./downloads/prosperity-axis-p41-atlas.pdf">两页图证核查图册 PDF</a>
<a href="./downloads/prosperity-axis-p41-package.zip">完整资料包 ZIP</a>
<a href="./prosperity-axis-sources/audit.json">原刊核查 JSON</a>
<a href="./prosperity-axis-sources/readings.csv">异记与量距 CSV</a></div></section>
<footer><a href="./prosperity-axis.html">返回 P4 宫城中轴尺度</a><span>P4.1 · {esc(info['source_commit'][:8])} · 图证审核</span></footer>
</main><script src="./prosperity-axis-sources/app.js"></script></body></html>"""

def main():
    d=load(INPUT)
    assert d["version"]==VERSION
    assert d["identity"]["separate_archaeological_sites_created"]==0
    assert [x["distance_m"] for x in d["distance_conflicts"]]==[200,300]
    assert [x["sum_m"] for x in d["alternatives"]]==[375,475]
    assert d["completely_acquired_formal_chinese_journal_plans"]==0
    assert d["city_registration"]["new_city_control_points"]==0
    assert d["city_registration"]["absolute_coordinates_added"]==0
    assert not (SITE/"prosperity-axis-sources.html").exists()
    info=load(SITE/"build-info.json")
    assert info["prosperity_axis"]["version"]=="prosperity-axis-p4-metric-review"
    OUT.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/"web/prosperity-axis-sources.css",OUT/"style.css")
    shutil.copyfile(ROOT/"web/prosperity-axis-sources.js",OUT/"app.js")
    dump(OUT/"audit.json",d)
    (OUT/"readings.csv").write_text(csv_data(d),encoding="utf-8-sig")
    figs=[("distance-comparison.svg",svg_alternatives(d)),
          ("figure-inventory.svg",svg_source_inventory(d))]
    atlas_paths=[]
    for name,content in figs:
        path=OUT/name
        path.write_text(content,encoding="utf-8")
        root=ET.fromstring(content)
        assert root.tag=="{http://www.w3.org/2000/svg}svg"
        assert root.attrib["viewBox"]=="0 0 1600 1000"
        atlas_paths.append(path)
    (SITE/"downloads").mkdir(parents=True,exist_ok=True)
    pdf=SITE/"downloads/prosperity-axis-p41-atlas.pdf"
    render_atlas(atlas_paths,pdf)
    page=SITE/"prosperity-axis-sources.html"
    page.write_text(page_html(d,info),encoding="utf-8")
    readme=OUT/"README.md"
    readme.write_text(
        "# P4.1 原刊核查\n\n"
        "复核奈文研2009、2010、2011、2013的机构公开原刊及图号；2009、2010《考古》正式简报的完整图版仍未取得。\n"
        "数值分歧：3号→太极殿2011约200m vs 钱国祥2012约300m；由95/80组成的分段累计分别375/475m。\n"
        "直接总距另约460m；不可将非独立测量与不同端点硬拟合。\n"
        "数据保持1号门=阊阖门同一考古对象、未增地理坐标及控制点、原刊图不入压缩包。\n",encoding="utf-8"
    )
    members={f"prosperity-axis-sources/{p.name}":p for p in sorted(OUT.iterdir()) if p.is_file()}
    members["prosperity-axis-sources.html"]=page
    members[f"downloads/{pdf.name}"]=pdf
    dump(OUT/"bundle-manifest.json",{
        "version":VERSION,"source_commit":info["source_commit"],
        "files_sha256":{name:sha(path) for name,path in members.items()}
    })
    members["prosperity-axis-sources/bundle-manifest.json"]=OUT/"bundle-manifest.json"
    with zipfile.ZipFile(SITE/"downloads/prosperity-axis-p41-package.zip","w",zipfile.ZIP_DEFLATED) as archive:
        for name,p in members.items():archive.write(p,name)
    release=load(SITE/"release.json")
    release["extensions"]=sorted(set(release.get("extensions",[])+[VERSION]))
    release["prosperity_axis_source_audit_version"]=VERSION
    release["current_milestone"]="盛时P4.1：宫城考古原刊图证与测距异记校核"
    dump(SITE/"release.json",release)
    info["prosperity_axis_source_audit"]={
        "version":VERSION,"source_commit":info["source_commit"],
        "source_count":len(d["sources"]),"figures":len(figs),
        "conflict_variants":[200,300],"identity_merged_count":1,
        "registration_verified":False,"new_ancient_coordinates":0,
        "metadata":"prosperity-axis-sources/audit.json"
    }
    info["files_sha256"]={str(p.relative_to(SITE)):sha(p) for p in sorted(SITE.rglob("*"))
                          if p.is_file() and p.name!="build-info.json"}
    dump(SITE/"build-info.json",info)
    print(json.dumps(info["prosperity_axis_source_audit"],ensure_ascii=False))

if __name__=="__main__":main()
