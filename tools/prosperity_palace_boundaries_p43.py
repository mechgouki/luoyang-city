#!/usr/bin/env python3
"""P4.3: publish three unregistered palace-court scope reports without inventing walls."""
from pathlib import Path
import csv
import hashlib
import html
import io
import json
import xml.etree.ElementTree as ET
import zipfile
from north_b4 import render_atlas

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
OUT=SITE/"prosperity-palace-boundaries"
SRC=ROOT/"research/prosperity-v4/palace-boundary-variants-p43.json"
VERSION="prosperity-palace-boundaries-p43"
W,H=1580,940
COLORS=("#396f65","#9a7845","#64759e")

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def dump(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def esc(value):
    return html.escape(str(value),quote=True)
def text(x,y,value,size=24,color="#2c4b45",weight=500,anchor="start"):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-family="Noto Sans CJK SC, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{esc(value)}</text>'

def scope_svg(data):
    scale=1.10 # pixels per reported metre; illustration only, never geolocation
    centers=(265,790,1315)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="三组太极殿宫院发表尺度，等尺比较，不是已定位古代宫墙">',
           f'<rect width="{W}" height="{H}" fill="#f5f4ef"/>',
           text(62,65,"盛时洛阳  ·  P4.3 · 宫院范围来源审查",25,"#668478",700),
           text(62,128,"三种发表尺度，不能拼成同一堵宫墙",39,"#294c40",700),
           text(62,173,"所有矩形使用同一米尺；中心位置仅用于排版，不共享历史南墙、北墙、坐标原点。",21,"#63776c")]
    for row,x,col in zip(data["reporting_variants"],centers,COLORS):
        width=row["ew_m"]*scale
        depth=row["ns_m"]*scale
        y=510
        left=x-width/2
        top=y-depth/2
        parts.extend([
           f'<rect x="{left:.2f}" y="{top:.2f}" width="{width:.2f}" height="{depth:.2f}" fill="{col}" fill-opacity=".09" stroke="{col}" stroke-width="4" stroke-dasharray="13 8"/>',
           text(x,252,f'口径 {row["id"]}',31,col,700,"middle"),
           text(x,486,f'{row["ew_m"]} × {row["ns_m"]} m',29,col,700,"middle"),
           text(x,763,row["reported_period"],19,col,600,"middle"),
           text(x,803,"约数 / 未核院界端点",19,"#6c716c",500,"middle")
        ])
    parts.extend([
         f'<path d="M65 836H1515" stroke="#d2d9d1" stroke-width="2"/>',
         text(70,870,"B−A：东西 −20m / 南北 +60m   ·   C−A：东西 −20m / 南北 +70m   ·   C−B：南北 +10m",22,"#4a655b"),
         text(70,906,"以上为报道数字的差异，并非院墙位移；2017局部院角不能直接补成宫院外框。",20,"#896d4e"),
         "</svg>"
    ])
    return "\n".join(parts)+"\n"

STYLE="""*{box-sizing:border-box}body{margin:0;background:#f7f7f2;color:#253a32;font-family:system-ui,"Noto Sans CJK SC","Microsoft YaHei",sans-serif;line-height:1.75}
header{background:#193d35;color:#fff;padding:15px max(20px,calc((100vw - 1080px)/2));display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap}
header a{color:#e6f0e6;text-decoration:none;margin-right:16px}
main{max-width:1080px;margin:auto;padding:35px 22px 80px}
.eyebrow{letter-spacing:.06em;color:#577b6d;font-weight:700;font-size:.88rem}
h1{font-size:clamp(1.8rem,3.8vw,3rem);line-height:1.25;margin:9px 0 20px}
h2{margin:0 0 13px;font-size:1.5rem}
section{padding:26px 0;border-bottom:1px solid #dce3d8}
p{margin:10px 0}
figure{margin:18px 0;background:#fff;border:1px solid #d4ddd5;border-radius:12px;overflow:hidden}
figure img{width:100%;display:block}
figcaption{font-size:.91rem;padding:12px 17px;background:#f1f3ee;color:#52685e}
table{width:100%;border-collapse:collapse;background:#fff}
th,td{padding:10px;border-bottom:1px solid #dce4da;text-align:left;vertical-align:top}
th{background:#edf1ea}
.table-wrap{overflow-x:auto}
a{color:#286e61}
.links{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}
.links a{padding:10px 15px;background:#e6eee9;border-radius:7px;text-decoration:none}
.caution{border-left:4px solid #b9935b;padding:9px 15px;background:#f6efe1}
.sources li{margin-bottom:12px}
small{color:#64776c}footer{padding:25px 0;color:#69796d}
@media(max-width:640px){header{display:block}main{padding:24px 16px 55px}th,td{min-width:115px;padding:8px;font-size:.89rem}.links a{width:100%}}
"""

def page(data,info):
    rows="".join(
       "<tr><td><b>"+esc(row["id"])+"</b></td><td>"+esc(row["ew_m"])+" m</td><td>"+esc(row["ns_m"])+" m</td><td>"+esc(row["source_grade"])+"</td><td>"+esc(", ".join(row["source_ids"]))+"</td></tr>"
       for row in data["reporting_variants"])
    sources="".join(
       '<li><a target="_blank" rel="noopener noreferrer" href="'+esc(s["url"])+'">'+esc(s["title"])+"</a> — "+esc(s["kind"])+"</li>"
       for s in data["sources"])
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>盛时洛阳 P4.3 · 太极殿宫院三案尺度与院界核定</title>
<meta name="description" content="太极殿宫院310／370／380米异记、原始出处、同尺度对照和未确定的真实院界。">
<link rel="stylesheet" href="./prosperity-palace-boundaries/style.css"></head>
<body><header><a href="./">盛时洛阳</a><nav><a href="./prosperity-taiji-courts.html">上一阶段 P4.2</a><a href="#sources">资料来源</a><a href="#downloads">下载</a></nav></header>
<main>
<section><p class="eyebrow">P4.3 · 历史布局核定 / 非宫墙复原图</p>
<h1>同一座宫院，为何出现310、370、380米三个南北尺寸？</h1>
<p>现有资料支持三种<strong>公开发表口径</strong>，而不是三条已经定位的真实宫墙。2022年的370米来自大众游览介绍，不能升级为独立考古测量。2015成果与2017讲座由同一考古传播链承接，不按出现次数投票。</p>
<p class="caution"><strong>目前不选定任一院界。</strong>缺少完整原版带尺测绘平面、共同测线起讫点、分期和可与城市总图对齐的独立控制点；新增古址坐标 0。</p></section>
<section id="scopes"><h2>01 · 同尺三案比较</h2>
<figure><a href="./prosperity-palace-boundaries/extent-comparison.svg" target="_blank" rel="noopener"><img src="./prosperity-palace-boundaries/extent-comparison.svg" alt="2015／2017约340乘310米、2022约320乘370米、2023约320乘380米三案宫院尺度同一图尺并列"></a>
<figcaption>三张虚线范围按相同米制绘制；中心、方向与实际院墙位置均未配准。点击打开 SVG 可放大。</figcaption></figure>
<div class="table-wrap"><table><thead><tr><th>来源组</th><th>东西约数</th><th>南北约数</th><th>证据等级</th><th>原始来源标识</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>相对于 A：B 的南北长度多约60米，C 多约70米；B 与 C 的差别约10米。这些数值<strong>不能</strong>自行解释为院墙移动、测量误差或相同的考古年代。</p></section>
<section id="anchors"><h2>02 · 局部院角能提供什么约束？</h2>
<p>2017年度发掘报告的东北角局部院址报告东西约96米、南北残长约27米、夹道4.7米。同一汇报还明确指出<strong>东围廊外侧就是宫院东墙，考古工作确认了东界、北界与东北角</strong>；只是本站尚未取得完整带尺测绘图、共用基点与分期，可核读的是文字报道，不能把这些发现直接画成全城坐标上的宫墙。</p>
<p>2021年建筑史研究也引用宫院宽320米，但该引用所依测线尚需回查正式图版。两项线索可以支持寻找原测绘图，不能据此猜出南墙、北墙、真实院落面积或屋顶高度。</p>
<p>另一个未决问题——P4.1中三号门至太极殿约200米或300米——涉及不同对象和量距端点，不能用本批310／370／380米替换或解决。</p></section>
<section id="sources"><h2>03 · 来源及独立性审查</h2><ol class="sources">{sources}</ol>
<p class="caution">上述链接包括机构转载、研究文章与大众介绍，来源等级不同；公开发表不能代替取得完整发掘原图。目前尚无已核定的整体宫院地理配准。</p></section>
<section id="downloads"><h2>04 · 研究数据与图册</h2>
<div class="links"><a href="./prosperity-palace-boundaries/data.json">证据 JSON</a>
<a href="./prosperity-palace-boundaries/readings.csv">量距 CSV</a>
<a href="./downloads/prosperity-palace-boundaries-p43-atlas.pdf">同尺图 PDF</a>
<a href="./downloads/prosperity-palace-boundaries-p43-package.zip">资料包 ZIP</a></div>
<p>下一步优先寻找原始院墙边界与带尺实测图；不得将本页三张尺寸片或2022年的二次叙述变成洛阳盛时城市总图的古址坐标。</p></section>
<footer><a href="./prosperity-taiji-courts.html">返回 P4.2 太极殿、东堂与北院</a> · P4.3 · 研究源码 {esc(info["source_commit"][:8])}</footer>
</main></body></html>"""

def measurements(data):
    s=io.StringIO()
    writer=csv.writer(s)
    writer.writerow(["variant","source_id","source_year","east_west_reported_m","north_south_reported_m","source_grade","approximate","ground_controls","shared_boundary_verified"])
    lookup={x["id"]:x for x in data["sources"]}
    for v in data["reporting_variants"]:
        for sid in v["source_ids"]:
            writer.writerow([v["id"],sid,lookup[sid]["year"],v["ew_m"],v["ns_m"],v["source_grade"],"true",0,"false"])
    return s.getvalue()

def main():
    data=read(SRC)
    claims=data["reporting_variants"]
    assert data["version"]==VERSION and [x["id"] for x in claims]==["A","B","C"]
    assert [(x["ew_m"],x["ns_m"]) for x in claims]==[(340,310),(320,370),(320,380)]
    assert data["metric_differences_m"]["C_minus_A"]=={"ew":-20,"ns":70}
    assert data["spatial_registration"]["verified_common_ground_controls"]==0
    assert data["spatial_registration"]["site_court_walls_overlay_allowed"] is False
    info=read(SITE/"build-info.json")
    assert info["prosperity_taiji_courts"]["version"]=="prosperity-taiji-courts-p42"
    assert not (SITE/"prosperity-palace-boundaries.html").exists()
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"style.css").write_text(STYLE,encoding="utf-8")
    dump(OUT/"data.json",data)
    (OUT/"readings.csv").write_text(measurements(data),encoding="utf-8-sig")
    svg=OUT/"extent-comparison.svg"
    svg.write_text(scope_svg(data),encoding="utf-8")
    root=ET.parse(svg).getroot()
    assert root.tag=="{http://www.w3.org/2000/svg}svg" and root.get("viewBox")==f"0 0 {W} {H}"
    (SITE/"downloads").mkdir(parents=True,exist_ok=True)
    pdf=SITE/"downloads/prosperity-palace-boundaries-p43-atlas.pdf"
    render_atlas([svg],pdf)
    page_file=SITE/"prosperity-palace-boundaries.html"
    page_file.write_text(page(data,info),encoding="utf-8")
    (OUT/"README.md").write_text(
       "P4.3：三案同尺但无坐标；宽度和深度仅是公开报告约值。\n"
       "2015与2017为同一团队传播链；2022大众说法待核；2023政务综述待核。\n"
       "2017东北角局部院址不拼合成整院；不生成地理定位宫墙或建筑高度。\n",encoding="utf-8")
    prev=SITE/"prosperity-taiji-courts.html"
    previous=prev.read_text(encoding="utf-8")
    marker='<footer><a href="./prosperity-axis-sources.html">'
    assert previous.count(marker)==1
    prev.write_text(previous.replace(marker,
       '<section id="p43-next" class="part"><h2>最新研究 P4.3：宫院尺度三案来源核定</h2>'
       '<p><a href="./prosperity-palace-boundaries.html">进入P4.3：310／370／380米同尺审查图 →</a></p>'
       '<p>保留本页P4.2两种尺度和各期院址；新案为2022大众说法，尚未证明真实院界。</p></section>'
       +marker),encoding="utf-8")
    members={f"prosperity-palace-boundaries/{x.name}":x for x in sorted(OUT.iterdir()) if x.is_file()}
    members["prosperity-palace-boundaries.html"]=page_file
    members[f"downloads/{pdf.name}"]=pdf
    dump(OUT/"bundle-manifest.json",{"version":VERSION,"source_commit":info["source_commit"],
        "files_sha256":{path:sha(file) for path,file in members.items()}})
    members["prosperity-palace-boundaries/bundle-manifest.json"]=OUT/"bundle-manifest.json"
    with zipfile.ZipFile(SITE/"downloads/prosperity-palace-boundaries-p43-package.zip","w",zipfile.ZIP_DEFLATED) as archive:
        for path,item in members.items():
            archive.write(item,path)
    release=read(SITE/"release.json")
    release["extensions"]=sorted(set(release.get("extensions",[])+[VERSION]))
    release["prosperity_palace_boundaries_version"]=VERSION
    release["current_milestone"]="盛时P4.3：太极殿宫院310／370／380米三种来源尺度与院界异记核查"
    dump(SITE/"release.json",release)
    info["prosperity_palace_boundaries"]={
       "version":VERSION,"source_commit":info["source_commit"],"source_reports":len(data["sources"]),
       "scope_variants":len(claims),"registered_absolute_locations_added":0,
       "verified_geographic_controls":0,"metadata":"prosperity-palace-boundaries/data.json",
       "atlas_pages":1}
    info["files_sha256"]={str(item.relative_to(SITE)):sha(item) for item in sorted(SITE.rglob("*"))
                          if item.is_file() and item.name!="build-info.json"}
    dump(SITE/"build-info.json",info)
    print(json.dumps(info["prosperity_palace_boundaries"],ensure_ascii=False))

if __name__=="__main__":
    main()
