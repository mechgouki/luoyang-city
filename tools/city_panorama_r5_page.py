"""The online and offline editions share views, research notes and navigation."""
from html import escape
from city_panorama_r5_scene import BASE, R4

PAGE="prosperity-city-panorama.html"
FOLDER="city-panorama"
BUNDLE="downloads/city-panorama.zip"
MANIFEST=FOLDER+"/manifest.json"
FILES={
    FOLDER+"/panorama.webp":"鸟瞰原幅 · WebP",FOLDER+"/core.svg":"宫寺体量图 · SVG",
    FOLDER+"/city.svg":"全城体量图 · SVG",FOLDER+"/scene.json":"布局、相机与艺术参数 · JSON",
    FOLDER+"/palace-east.svg":"宫城东部布局 · SVG",
    FOLDER+"/sima-road.svg":"司马门内道路核读图 · SVG",
    MANIFEST:"发布校验清单 · JSON",BUNDLE:"完整离线包 · ZIP",
}


def link(url,label):
    return f'<a href="{escape(url,quote=True)}">{escape(label)}</a>'


def make_page(scene,plates,offline=False):
    root=BASE if offline else "./"
    atlas=root+R4
    models=scene["models"]
    def inline(key):
        markup=plates[key]
        for m in models:
            href=BASE+R4+"#feature-"+m["feature_id"]
            markup=markup.replace('href="'+href+'"','href="#'+m["id"]+'"')
        return markup.replace(BASE+R4+"#",atlas+"#").replace('<svg ','<svg class="canvas sheet" ',1)
    east=scene["east_palace"]
    source_links={s[0]:link(s[2],s[1]) for s in east["sources"]}
    east_notes=[]
    for record in east["records"]:
        citations=" · ".join(source_links[key] for key in record["sources"])
        east_notes.append(f'<article class="entry"><h3>{escape(record["name"])}</h3><p>{escape(record["text"])}</p><small>{citations}</small></article>')
    sima=scene["sima_road"]
    sima_sources={key:link(url,name) for key,name,url,_ in sima["sources"]}
    sima_rows=[]
    for label,note,*keys in sima["rows"]:
        refs=" · ".join(sima_sources[key] for key in keys)
        sima_rows.append(f'<article class="entry"><h3>{escape(label)}</h3><p>{escape(note)}</p><small>{refs}</small></article>')
    check=sima["diagnostic"]
    cards=[]
    for m in models:
        size=m["reported_footprint_m"]
        refs=[link(atlas+'#feature-'+m["feature_id"],"R4 来源图符")]
        if m["entity_id"]: refs.append(link(atlas+'#entity-'+m["entity_id"],"文献对象"))
        cards.append(f'<article class="entry" id="{m["id"]}"><h3>{escape(m["name"])}</h3><p>{escape(m["note"])}</p>'
                     f'<small>报告平面约东西 {size["east_west"]} 米、南北 {size["north_south"]} 米。{escape(m["chronology"])}</small>'
                     f'<div class="tools">{" ".join(refs)}</div></article>')
    sources="".join("<li>"+link(root+url[2:] if url.startswith("./") else url,name)+"　"+escape(note)+"</li>" for name,url,note in scene["sources"])
    notes="".join('<article class="entry"><h3>'+escape(name)+'</h3><p>'+escape(content)+'</p></article>' for name,content in scene["art_direction"])
    downloads="".join(f'<li><a href="{(BASE if offline and path==BUNDLE else "./")+path}" download>{label}</a></li>' for path,label in FILES.items())
    legend='<div class="key"><span>墙线</span><span class="buried">地下残线</span><span class="road">路迹残段</span><span class="area">宫城候选面</span><span class="point">图符参考点</span></div>'
    names="".join(link("#"+m["id"],m["name"]) for m in models)
    marks=[]
    img=scene["image"]
    for m in models:
        x,y=m["projected_ground_px"]["core"];u,v=img["painting_footpoints_px"][m["id"]]
        u=u*1600/img["width"];v=v*950/img["height"]
        marks.append(f'<g data-anchor="{m["id"]}"><title>{escape(m["name"])}</title><path d="M{x},{y} L{u},{v}" stroke="white" stroke-width="3"/>'
                     f'<circle cx="{x}" cy="{y}" r="11" fill="none" stroke="#123f3b" stroke-width="6"/>'
                     f'<circle cx="{x}" cy="{y}" r="11" fill="none" stroke="#fff" stroke-width="2.8"/>'
                     f'<circle cx="{u:.2f}" cy="{v:.2f}" r="4.8" fill="#ffc583" stroke="#422e20" stroke-width="2"/>'
                     f'<text x="{x+16}" y="{y-12}" fill="#fff" stroke="#23372e" stroke-width="5" paint-order="stroke" font-size="21" font-family="sans-serif">{escape(m["name"])}</text></g>')
    overlay='<svg class="overlay" viewBox="0 0 1600 950" preserveAspectRatio="none" aria-hidden="true">'+''.join(marks)+'</svg>'
    structural=[]
    for key,title,caption in [
        ("core","宫寺核心","与鸟瞰画共用取景方向。点击四座建筑的图签可查图符、遗存与报告平面量测。"),
        ("city","全城范围","全图保留外郭相关遗存的概略范围。宫城北缘只作候选范围填色，八条道路沿用可见残段。")]:
        structural.append(f'<figure class="plate" id="{key}" data-view>{legend}{inline(key)}<figcaption><span><strong>{title}</strong>　{caption}</span>{link("./"+FOLDER+"/"+key+".svg","打开可缩放原图 ↗")}</figcaption><div class="tools">{names}</div></figure>')
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="从永宁寺、御道与宫前阊阖门读北魏洛阳的盛时布局。"><title>盛时洛阳 · 城市全景</title><link rel="stylesheet" href="./{FOLDER}/panorama.css"><script src="./{FOLDER}/panorama.js" defer></script></head>
<body><header><div class="wrap">{link(root,"北魏洛阳文献地图")}<nav class="navlinks">{link(atlas,"R4 城市分布总图")}{link(root+"luoyang-water-atlas.html","河流与水系定位图集")}<span id="road-atlas-entry">{link(root+"luoyang-road-atlas.html","全城主干道定位")}</span>{link("#buildings","建筑依据")}{link("#downloads","下载")}</nav></div></header><main class="wrap">
<div class="mast"><div><p class="date">北魏　·　公元 516—528 年</p><h1>盛时洛阳全景</h1></div><p class="lead">自城南向北望。沿永宁寺东侧的御道入宫，阊阖门在前，太极殿在后。切换体量图可查这条视线的出处。</p></div>
<nav class="tabbar" aria-label="全景视图">{link("#art","盛时鸟瞰")}{link("#core","宫寺体量")}{link("#city","全城体量")}{link("#palace-east","宫城东部")}{link("#sima-road","司马门内路")}</nav>
<figure class="plate" id="art" data-view><input id="show-anchors" type="checkbox"><label for="show-anchors">对照四处建筑落点</label><span class="read-key">白圈为体量图参考点，金点为画面取读点</span><div class="illustration"><picture><source media="(max-width:680px)" srcset="./{FOLDER}/panorama-small.webp"><img class="canvas sheet" src="./{FOLDER}/panorama.webp" width="{scene["image"]["width"]}" height="{scene["image"]["height"]}" alt="自城南向北俯瞰，永宁寺木塔在御道左前方，宫门、太极殿在其东北方向。街坊在城内外展开。"></picture>{overlay}</div>
<figcaption><span><strong>自城南望宫城</strong>　以图06a投影为构图底稿的艺术复原。建筑位置以体量图为准。</span>{link("./"+FOLDER+"/panorama.webp","放大鸟瞰原幅 ↗")}</figcaption></figure>
{"".join(structural)}
<section class="plate" id="palace-east" data-view aria-labelledby="east-title"><h2 id="east-title">宫城东部布局</h2>
<figure class="plate"><img class="canvas sheet" src="./{FOLDER}/palace-east.svg" width="1000" height="860" alt="上图依次列出太极殿宫院、司马门内道路、宫内仓储、宫城东墙和宫外仓窖。下图另示宫外仓区的东围墙与广莫门内道路。"><figcaption><span>两幅图各自读方位与次序，具体路宽和分期见下方考古记录。</span>{link("./"+FOLDER+"/palace-east.svg","放大工作图 ↗")}</figcaption></figure>
<div class="east-notes">{"".join(east_notes)}</div><p>{escape(east["period"])}</p><p>{link("#sima-road","查看司马门内道路与两侧墙线 →")}</p></section>
<section class="plate" id="sima-road" data-view aria-labelledby="sima-title"><h2 id="sima-title">司马门内道路与两侧墙线</h2>
<figure class="plate"><img class="canvas sheet" src="./{FOLDER}/sima-road.svg" width="1000" height="720" alt="用千秋门和宫前阊阖门对齐图符，太极殿留下独立检查；宫内仓窖区蓝框在其东面。"><figcaption><span>左图取考古队位置图的三个建筑图符与仓区标示，右图放大太极殿的比对结果。</span>{link("./"+FOLDER+"/sima-road.svg","放大核读图 ↗")}</figcaption></figure>
<p>将 R4 的千秋门和宫前阊阖门与位置图的门身中心对齐，预留太极殿作检验。两图的殿址相差 {check["offset_px"]:.1f} 个原图像素，按图尺折约 {check["map_equivalent_m"]:.0f} 米。建筑图符中心的选法会影响读数。此次接入全城总图的墙段为零。</p>
<div class="east-notes">{"".join(sima_rows)}<article class="entry"><h3>仓区蓝框能量出什么？</h3><p>原图图尺每100米占88像素。蓝框按中线换读，东西约{check["box_graphic_size_m"][0]}米、南北约{check["box_graphic_size_m"][1]}米。发掘方介绍的仓区约东西150米、南北600米。两组数字的取点口径不同，蓝框边线不能充当仓区西墙的实测线。</p><small>{sima_sources["map"]} · {link(sima["image"]["url"],"考古队原图")} · {sima_sources["region"]}</small></article></div>
<p>{escape(sima["transfer"]["next"])}</p><div class="tools">{link(atlas+"#feature-geo-taiji-hall-reference","对照 R4 太极殿图符")}{link("#palace-east","返回宫城东部")}</div></section>
<div class="content"><section id="buildings"><h2>四处建筑依据</h2>{"".join(cards)}</section><section id="interpretation"><h2>画面如何复原</h2><p>两幅体量图沿用 R4 的 28 项图面要素。原图展示容差及逐项年代可在 R4 查阅。四座形体取自既有建筑对照表，屋顶与高度单独登记。太极殿沿用独立参考点。艺术画中的塔檐作了简化，九层木塔可在宫寺体量图中逐层查看。</p>{notes}</section></div>
<section class="sources" id="sources"><h2>图源与核读</h2><ul>{sources}</ul></section><section class="downloads" id="downloads"><h2>下载</h2><ul>{downloads}</ul></section>
</main><footer><div class="wrap">R5.3 · 盛时城市全景　{link(atlas,"返回城市分布总图")}　{link(root+"","项目首页")}</div></footer></body></html>\n'''
