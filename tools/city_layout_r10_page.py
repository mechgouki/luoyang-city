"""Readable HTML for the whole-city layout atlas; all evidence survives without JS."""
import html
import json

BASE = "https://mechgouki.github.io/luoyang-city/"
PAGE = "luoyang-city-layout.html"
FOLDER = "city-layout-r10"
BASIS = {"source": "来源图对应", "relation": "文献／报告关系",
         "interpretation": "候选／研究解释", "unknown": "仍待定位"}
LEVELS = {"source": "来源图有对应", "candidate": "候选范围参照",
          "relative": "文献相对关系", "unlocated": "位置未定"}
TYPES = {"temple": "寺院", "palace_gate": "宫门", "road": "道路", "office": "官署",
         "school": "学校", "ritual_site": "礼制场所", "ward": "里坊",
         "named_place_unknown_function": "名称已知、用途未定", "former_residence": "宅第前身",
         "residence": "宅第", "former_market": "旧市", "water": "水体", "garden": "园地",
         "platform": "台", "well": "井", "palace_structure": "宫殿构筑物",
         "enclosure": "围合范围", "enclosure_gate": "院门", "former_structure": "前代建筑",
         "reserved_site": "预留地", "former_office": "官署旧址", "former_ward": "旧里坊",
         "artificial_hill": "人工山", "storehouse": "仓储", "hill_or_palace_structure_disputed": "山／宫殿构筑物待辨",
         "hill": "山丘", "grove": "林地", "stele": "碑刻", "city_gate": "城门", "market": "市场",
         "county_site": "县址", "garden_complex": "园林群", "pond": "池", "watercourse": "水道",
         "river": "河流", "mountain_region": "山地范围", "residence_building": "宅内建筑",
         "bridge": "桥", "historical_site": "历史地点", "weir": "堰", "training_ground": "训练场",
         "regional_landmark": "区域参照", "pass": "关隘", "watercourse_region": "水道地段", "area": "区域"}
EXISTING_DRAWINGS = {
    "R02": [("luoyang-city-spatial.html#map-panel-baima", "白马坊街的既有空间联读")],
    "R03": [("prosperity-axis.html", "宫城中轴与分段量距"),
            ("prosperity-taiji-courts.html", "太极殿、东堂与北侧宫院"),
            ("prosperity-palace-boundaries.html", "宫城边界与仓区")],
    "R04": [("prosperity-backbone-p469.html", "建春门原图与城市接合")],
    "R07": [("prosperity-gate.html", "阊阖门局部考古平面"),
            ("prosperity-core.html", "核心建筑尺度与局部结构")],
    "R10": [("prosperity-south-p466.html", "城南道路与水系分期")],
}


def h(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value if value is not None else ""), quote=True)


def prose(value):
    return h("；".join(value) if isinstance(value, list) and all(isinstance(x, str) for x in value) else value)


def link(url, title, extra=""):
    return f'<a href="{h(url)}" {extra}>{h(title)}</a>'


def text_search(row, extra=()):
    return h(" ".join([json.dumps(row, ensure_ascii=False), *extra]))


def region_links(ids):
    return " ".join(link("#region-" + rid, rid, 'class="region-chip"')
                    if rid != "register" else '<span class="region-chip">待分区名录</span>' for rid in ids)


def map_block(svg, target, title):
    svg = svg.replace(BASE + PAGE + "#", "#")
    if svg.startswith("<?xml"):
        svg = svg.split("?>", 1)[1]
    buttons = [("zoom-in", "放大"), ("zoom-out", "缩小"), ("reset", "复位"),
               ("pan-left", "左移"), ("pan-right", "右移"), ("pan-up", "上移"), ("pan-down", "下移")]
    controls = "".join(f'<button type="button" data-map-target="{target}" data-action="{action}" aria-label="{h(title + chr(65306) + label)}">{label}</button>'
                       for action, label in buttons)
    return f'<div class="map-tools" aria-label="{h(title)}图面操作">{controls}<span>可横向滚动；方向键可平移</span></div><div class="map-viewport" data-map-id="{target}" tabindex="0" aria-label="{h(title)}">{svg}</div>'


def sources(row, source_commit):
    evidence = {(x["path"], x["pointer"]): x for x in row.get("source_evidence", [])}
    items = []
    for ref in row["source_inputs"]:
        path, pointer = ref["path"], ref["pointer"]
        item = evidence.get((path, pointer), {})
        url = f"https://github.com/mechgouki/luoyang-city/blob/{source_commit}/{path}"
        anchor = link(url, path, f'data-source-path="{h(path)}" data-source-pointer="{h(pointer)}"')
        excerpt = f'<p class="source-excerpt">{h(item["excerpt"])}</p>' if item.get("excerpt") else ""
        items.append(f'<li>{anchor}<code>{h(pointer or "/")}</code>{excerpt}</li>')
    return '<details class="source-details"><summary>回查来源记录与字段</summary><p>下列节录来自既有来源记录；原文、校读与研究摘要按原字段阅读。</p><ul>' + "".join(items) + "</ul></details>"


def decision_row(row, commit):
    entities = " ".join(link("#entity-" + eid, eid) for eid in row["entity_ids"])
    return f'''<tr class="decision-row" id="decision-{h(row['id'])}" tabindex="-1"
data-region="{h(row['region_id'])}" data-basis="{h(row['basis'])}" data-search="{text_search(row)}">
<td data-label="空间判断"><a class="record-id" href="#decision-{h(row['id'])}">{h(row['id'])}</a><h3>{h(row['title'])}</h3><span class="small">{h(row['region_title'])}</span></td>
<td data-label="采用的判断"><p>{h(row['judgment'])}</p><p class="phase-note">{h(row['phase_note'])}</p></td>
<td data-label="图面变化"><p>{h(row['map_change'])}</p><div class="record-links">{entities}</div></td>
<td data-label="边界与依据"><p>{h(row['remaining_unknown'])}</p>{sources(row, commit)}</td></tr>'''


def coverage_row(row):
    diagrams = "、".join(row["diagram_node_ids"]) or "本轮未为此对象绘独立关系节点"
    decisions = " ".join(link("#decision-" + key, key) for key in row["decision_ids"])
    feature_links = " ".join(link(BASE + "prosperity-city-atlas.html#feature-" + fid, fid) for fid in row["feature_ids"])
    source = link(row.get("source_url") or BASE + "prosperity-city-atlas.html#entity-" + row["id"], "原始出处入口")
    return f'''<tr class="coverage-row" id="entity-{h(row['id'])}" tabindex="-1"
data-region="{h(' '.join(row['region_ids']))}" data-basis="{h(row['basis'])}" data-search="{text_search(row)}">
<td data-label="对象"><a class="record-id" href="#entity-{h(row['id'])}">{h(row['id'])}</a><h3>{h(row['name'])}</h3><span class="small">{h(TYPES.get(row.get('type'), row.get('type')))} · {h(row.get('temporal_label') or row['period'])}</span></td>
<td data-label="原有定位依据"><span class="badge {h(row['basis'])}">{h(LEVELS[row['level']])}</span><p>{h(row['placement'])}</p><div class="record-links">{feature_links}</div></td>
<td data-label="本轮图面去向">{region_links(row['region_ids'])}<p><strong>{h(row['representation'])}</strong></p><details><summary>查看图面节点与判断编号</summary><p>{h(diagrams)}</p><div class="record-links">{decisions}</div></details></td>
<td data-label="出处与下一依据"><p>{h(row['next_evidence'])}</p>{source}<p class="small">{h(row.get('source_ref'))}</p></td></tr>'''


def network_row(row):
    kind = "道路证据" if row["kind"] == "road" else "水系索引"
    original = row["original"]
    phase = original.get("period") or original.get("placement") or ""
    decisions = " ".join(link("#decision-" + key, key) for key in row["decision_ids"])
    return f'''<tr class="network-row" id="network-{h(row['id'])}" tabindex="-1"
data-region="{h(' '.join(row['region_ids']))}" data-basis="{h(row['basis'])}" data-search="{text_search(row)}">
<td data-label="路水记录"><a class="record-id" href="#network-{h(row['id'])}">{h(row['record_id'])}</a><h3>{h(row['name'])}</h3><span class="small">{kind}</span><p><span class="badge {h(row['basis'])}">{h(BASIS[row['basis']])}</span></p></td>
<td data-label="已有空间依据"><p>{prose(row['finding'])}</p><p class="phase-note">{h(phase)}</p></td>
<td data-label="本轮关联">{region_links(row['region_ids'])}<div class="record-links">{decisions}</div><p class="small">关联表示本轮判断引用了此记录，不增加同名道路或水体。</p></td>
<td data-label="保留边界"><p>{prose(row['limit'])}</p>{link(row['source_url'],'回到完整路水专题')}<details><summary>发布数据回查</summary>{link(BASE + row['source_path'], row['source_path'], f'data-published-source-path="{h(row["source_path"])}" data-source-pointer="{h(row["source_pointer"])}"')}<code>{h(row['source_pointer'])}</code></details></td></tr>'''


def gap_card(row, commit):
    return f'''<article class="gap-card" id="gap-{h(row['id'])}" tabindex="-1" data-region="{h(row['region_id'])}"
data-basis="unknown" data-search="{text_search(row)}"><span class="record-id">{h(row['id'])} · {h(row['region_title'])}</span><h3>{h(row['title'])}</h3>
<p><strong>已知：</strong>{h(row['known'])}</p><p><strong>仍缺：</strong>{h(row['unknown'])}</p><p class="next-evidence"><strong>有效的下一依据：</strong>{h(row['next_evidence'])}</p>{sources(row, commit)}</article>'''


def make_page(data, overview, region_svgs, downloads, offline=False):
    prefix = BASE if offline else ""
    counts, commit = data["counts"], data["source_commit"]
    choices = "".join(f'<option value="{r["id"]}">{r["id"]} {h(r["title"])}</option>' for r in data["regions"])
    cards, sheets = [], []
    for region in data["regions"]:
        rid = region["id"]
        n = sum(rid in row["region_ids"] for row in data["coverage"])
        first = region["decisions"][0]["id"]
        cards.append(f'''<a class="region-nav-card" href="#region-{rid}"><span>{rid}</span><h3>{h(region['title'])}</h3><p>{len(region['panels'])}个关系窗 · {len(region['decisions'])}项判断 · 涉及{n}个名录对象</p></a>''')
        decision_chips = " ".join(link("#decision-" + d["id"], d["id"], 'class="decision-chip"') for d in region["decisions"])
        gaps = " ".join(link("#gap-" + g["id"], g["title"]) for g in region["gaps"])
        previous = " ".join(link(BASE + path, label) for path, label in EXISTING_DRAWINGS.get(rid, []))
        drawing_links = '<p class="small">继续联读既有图纸：</p><div class="record-links">' + previous + '</div>' if previous else ""
        sheets.append(f'''<section class="region-sheet" id="region-{rid}" data-region="{rid}" tabindex="-1">
<div class="section-heading"><div><p class="eyebrow">{rid} · 片区布局深化</p><h2>{h(region['title'])}</h2></div><a class="text-link" href="#decision-{first}">本区逐项依据 →</a></div>
<p class="section-intro">{h(region['intro'])}</p>{map_block(region_svgs[rid], rid, region['title'])}
<div class="region-reading"><div><h3>本区现在能看清什么</h3><p>{h(region['summary'])}</p><div class="record-links">{decision_chips}</div></div>
<div><h3>对全景布局的约束</h3><p>{h(region['panorama_implication'])}</p><p>{link(BASE + region['old_topic_url'], '回到既有专题')}</p>{drawing_links}<div class="record-links">{gaps}</div></div></div></section>''')
    download_links = []
    for path, title, note in downloads:
        url = BASE + path if offline and path.endswith(".zip") else path
        download_links.append(f'<a href="{h(url)}" download data-download="{h(path)}"><strong>{h(title)}</strong><span>{h(note)}</span></a>')
    decision_rows = "".join(decision_row(r, commit) for r in data["decisions"])
    coverage_rows = "".join(coverage_row(r) for r in data["coverage"])
    network_rows = "".join(network_row(r) for r in data["networks"])
    gap_cards = "".join(gap_card(r, commit) for r in data["gaps"])
    changes = "".join(f'<li><a href="#region-{r["id"]}">{r["id"]} {h(r["title"])}</a><p>{h(r["summary"])}</p></li>' for r in data["regions"])
    basis_options = "".join(f'<option value="{k}">{v}</option>' for k, v in BASIS.items())
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="source-commit" content="{h(commit)}"><meta name="description" content="盛时洛阳全城总平面与十一片区布局深化：原图骨架、分区关系、339对象覆盖和路水证据同页回查。">
<title>全城总平面与十一片区 · 盛时洛阳</title><link rel="stylesheet" href="{FOLDER}/atlas.css"><script src="{FOLDER}/atlas.js" defer></script></head>
<body><a class="skip" href="#overview">跳到全城总平面</a>
<div class="topbar"><nav class="shell" aria-label="项目导航"><a class="brand" href="{prefix}index.html">盛时洛阳</a><div><a href="{prefix}prosperity-city-atlas.html">来源总图</a><a href="{prefix}luoyang-all-roads.html">道路</a><a href="{prefix}luoyang-water-atlas.html">水系</a><a href="{prefix}luoyang-panorama-v13-r2.html">全景候选</a></div></nav></div>
<header class="hero"><div class="shell"><p class="eyebrow">R10.1 · 516—528年综合研究窗口</p><h1>从全城骨架，<br>读到十一片区内部</h1><p class="hero-intro">沿城市总平面进入十一片区，查看门、路、水、院落与里坊之间能够成立的关系。每一项图面判断都连接来源和仍待解决的问题。</p>
<nav class="jump-nav" aria-label="本页导航"><a href="#overview">全城总平面</a><a href="#regions">十一片区</a><a href="#decisions">空间判断</a><a href="#coverage">对象覆盖</a><a href="#networks">路水覆盖</a><a href="#gaps">未定项</a><a href="#downloads">图册与下载</a></nav></div></header>
<main class="shell"><div class="facts"><div><strong>11</strong><span>片区深化图</span></div><div><strong>{counts['panels']}</strong><span>独立关系窗</span></div><div><strong>{counts['decisions']}</strong><span>可回查空间判断</span></div><div><strong>339</strong><span>名录对象完整覆盖</span></div><div><strong>84 + 34</strong><span>道路证据／水系索引</span></div></div>
<aside class="reading-key"><strong>读图约定</strong><p>全城骨架保留来源图的原点、原段与缺口；分区图按相对关系组织，窗口间没有共同测绘定位。图中位置、线长和节点大小不能量取古代距离。沿革、制度成员与空间关系采用不同画法。</p><div class="legend"><span class="badge source">来源图对应</span><span class="badge relation">文献／报告关系</span><span class="badge interpretation">候选／研究解释</span><span class="badge unknown">仍待定位</span></div></aside>
<noscript><p class="notice">脚本未启用：全城图、十一片区和所有证据仍可阅读。请使用目录、图上链接或浏览器查找；下载的图册和离线包同样保留全部内容。</p></noscript>
<section id="overview"><div class="section-heading"><div><p class="eyebrow">第一层 · 城市骨架</p><h2>全城总平面</h2></div><a class="text-link" href="{FOLDER}/overview.svg" download>下载总图 SVG →</a></div><p class="section-intro">沿用28项古迹来源几何，保留缺失的南部城界、道路端点与独立图框。十一片区入口用于组织阅读，不能作为已经测定的分区边界。</p>{map_block(overview,'overview','全城总平面')}</section>
<section id="regions"><div class="section-heading"><div><p class="eyebrow">第二层 · 片区内部</p><h2>十一片区，一套阅读方法</h2></div><a class="text-link" href="{h(downloads[1][0])}" download>下载{data["pdf_pages"]}页图册 →</a></div><p class="section-intro">各区在既有图面上展开内部关系和证据边界。对象可以跨区阅读；每个节点代表被说明的对象，不等于一座新增定位建筑。</p><div class="region-nav-grid">{''.join(cards)}</div></section>
<section id="filters" class="filters" aria-label="片区与证据筛选"><label for="region-select">片区<select id="region-select"><option value="all">全部十一片区</option>{choices}<option value="register">待分区／既有专题保留</option></select></label><label for="search">地点、编号或关键词<input id="search" type="search" placeholder="如：宣阳门、宫院、R10-R07、W01" autocomplete="off"></label><label for="basis-filter">依据性质<select id="basis-filter"><option value="all">全部依据</option>{basis_options}</select></label><button id="clear-filters" type="button">清除筛选</button><p>片区选择同步图面与表格；关键词和依据性质筛选下方记录。网址保存当前选择。</p></section>
<div id="region-sheets">{''.join(sheets)}</div><p id="region-empty" class="notice" hidden>这些记录保留在名录或既有专题中，本轮没有为其新增片区位置。请在下方覆盖表查看具体出处。</p>
<section id="decisions"><div class="section-heading"><div><p class="eyebrow">第三层 · 判断与改图</p><h2>空间判断—依据—图面变化</h2></div><span class="count" id="decision-count" data-visible-count="{counts['decisions']}" role="status" aria-live="polite">显示 {counts['decisions']} / {counts['decisions']} 项</span></div><p class="section-intro">逐项说明这轮画清了什么、采用什么判断以及还不能画到哪里。来源节录与真实文件字段一起保留。</p>
<div class="table-scroll"><table><thead><tr><th>空间判断</th><th>采用的判断</th><th>图面变化</th><th>边界与依据</th></tr></thead><tbody>{decision_rows}</tbody></table></div><p class="empty-state" data-empty-for="decision" hidden>没有匹配的空间判断。</p></section>
<section id="coverage"><div class="section-heading"><div><p class="eyebrow">全城逐项覆盖</p><h2>339个对象，各有去向</h2></div><span class="count" id="coverage-count" data-visible-count="339" role="status" aria-live="polite">显示 339 / 339 项</span></div><p class="section-intro">原定位等级沿用来源总图：11项有来源图对应，1项为候选范围，315项依文献相对关系，12项位置未定。这是名录对象的依据分类，不能作为古城建筑总数或复原完成率。</p>
<details class="table-fold" open><summary>查看对象覆盖与图面去向</summary><div class="table-scroll"><table><thead><tr><th>对象</th><th>原有定位依据</th><th>本轮图面去向</th><th>出处与下一依据</th></tr></thead><tbody>{coverage_rows}</tbody></table></div></details><p class="empty-state" data-empty-for="coverage" hidden>没有匹配的名录对象。</p></section>
<section id="networks"><div class="section-heading"><div><p class="eyebrow">道路与水系</p><h2>保留每条既有路水记录</h2></div><span class="count" id="network-count" data-visible-count="118" role="status" aria-live="polite">显示 118 / 118 项</span></div><p class="section-intro">84条道路证据包含路段、门道、桥道与集合记录，34项水系索引包含近现代参照W02。它们不是84条已去重古路或34条完整古岸。未被本轮决定引用的记录继续保留原专题。</p>
<details class="table-fold"><summary>查看118条路水记录与本轮关联</summary><div class="table-scroll"><table><thead><tr><th>路水记录</th><th>已有空间依据</th><th>本轮关联</th><th>保留边界</th></tr></thead><tbody>{network_rows}</tbody></table></div></details><p class="empty-state" data-empty-for="network" hidden>没有匹配的道路或水系记录。</p></section>
<section id="gaps"><div class="section-heading"><div><p class="eyebrow">未知内容在图上保留</p><h2>全城与片区的未定项</h2></div><span class="count" id="gap-count" data-visible-count="{counts['gaps']}" role="status" aria-live="polite">显示 {counts['gaps']} / {counts['gaps']} 项</span></div><p class="section-intro">六项全城骨架缺口与各区内部问题分开登记。有效的下一证据须能说明位置、尺度、同一对象或具体使用层，目录线索和图面相近不能替代。</p><div class="gap-grid">{gap_cards}</div><p class="empty-state" data-empty-for="gap" hidden>没有匹配的未定项。</p></section>
<section id="panorama" class="panorama-section"><p class="eyebrow">让布局约束全景</p><h2>这轮对城市画面的具体要求</h2><p class="section-intro">本轮新增的是总平面与分区图纸。下列各区规则可回查到图面；现有V13二修继续作为艺术全景候选，首页主图保持V12。</p><details><summary>展开十一片区的布局要点</summary><ol class="change-list">{changes}</ol></details><a class="primary-link" href="{prefix}luoyang-panorama-v13-r2.html?view=compare#comparison">对照现有全景候选</a></section>
<section id="boundaries"><h2>完成范围与研究边界</h2><div class="boundary-grid"><article><h3>本轮完成的图纸</h3><p>全城来源骨架、十一片区内部关系、完整名录与路水覆盖、逐项判断和未定接口共同交付。每个片区都有独立关系窗和本区判断；已有对象ID与定位等级保留。</p></article><article><h3>仍需要原件的定位问题</h3><p>1993外郭道路水道报告原页与完整附图、2011东阳渠鸿池陂简报完整原页图版仍缺。古岸、桥头、完整城界、古地面与建筑原高没有因图册完成而获得新坐标。2022渠道报告继续暂缓。</p></article></div><p class="notice">本轮新增古代坐标0、古岸几何0、证据等级提升0。516—528年为综合研究窗口；不同建筑、道路与水流的确切使用年代继续逐项说明。南门二修指永宁寺南门，内城宣阳门与南墙仍属定位缺口。</p></section>
<section id="downloads"><div class="section-heading"><div><p class="eyebrow">带走这套图纸</p><h2>图册、矢量图与完整证据</h2></div></div><p class="section-intro">PDF供连续审看与打印，SVG保留可放大的文字与证据链接，CSV适合对照，JSON保存完整记录与来源指针。离线包包含本页、图册、所有本轮图件和表格；外部原文与既有专题链接仍需联网。</p><div class="download-grid">{''.join(download_links)}</div></section>
</main><footer><div class="shell"><strong>盛时洛阳 · R10.1</strong><p>全城总平面与十一片区布局系统深化</p><p>来源提交 <code>{h(commit)}</code> · <a href="https://github.com/mechgouki/luoyang-city/issues/52">研究交接</a> · <a href="#overview">回到总平面 ↑</a></p></div></footer></body></html>'''
