"""Readable, self-contained city-node pages; source frames remain independent."""
from html import escape
import re

from city_nodes_r7_contract import BASE, BUNDLE, FOLDER, MANIFEST, PAGE, VERSION


def h(value):
    return escape(str(value), quote=True)


def human(value):
    if value is None or value == [] or value == {}:
        return '未记'
    if isinstance(value, list):
        return '；'.join(human(item) for item in value)
    if isinstance(value, dict):
        return '；'.join(str(key) + '：' + human(item) for key, item in value.items())
    return str(value)


def link(url, label, **attrs):
    extra = ''.join(' ' + key.rstrip('_').replace('_', '-') + '="' + h(value) + '"' for key, value in attrs.items())
    return '<a href="' + h(url) + '"' + extra + '>' + h(label) + '</a>'


def chips(ids, kind, names=None):
    names = names or {}
    return '<div class="record-links">' + ''.join(
        link('#' + kind + '-' + identifier, identifier + (' ' + names[identifier] if identifier in names else ''))
        for identifier in ids) + '</div>'


def source_list(sources, include_access=False):
    result = []
    for source in sources:
        title = source.get('title', source.get('name', source.get('id', '来源')))
        name = link(source['url'], title) if source.get('url') else h(title)
        locator = source.get('locator', source.get('pages_figure', source.get('scope', '')))
        details = '<span class="source-locator">' + h(human(locator)) + '</span>' if locator else ''
        if include_access and source.get('access_status'):
            details += '<p class="source-access">' + h(source['access_status']) + '</p>'
        if source.get('evidence_type'):
            details += '<p class="source-access">' + h(source['evidence_type']) + '</p>'
        result.append('<li>' + name + details + '</li>')
    return '<ul class="source-list">' + ''.join(result) + '</ul>'


def inline_svg(svg):
    svg = re.sub(r'^\s*<\?xml[^>]*\?>\s*', '', svg)
    return svg.replace(BASE + PAGE + '#', '#')


def map_figure(key, svg, title, note):
    minimum = 1000 if key == 'overview' else 820
    return f'''<figure class="map-figure" id="map-{h(key)}" data-map="{h(key)}" data-min-width="{minimum}">
<div class="map-controls" hidden><label for="zoom-{h(key)}">放大 <input id="zoom-{h(key)}" data-map-zoom="{h(key)}" type="range" min="100" max="220" step="20" value="100"><output data-zoom-value>100%</output></label><button type="button" data-map-reset="{h(key)}">回到全图</button><span>可拖动滚动条；键盘方向键可移动图面</span></div>
<div class="map-scroll" tabindex="0" aria-label="{h(title)}，可上下左右滚动">{inline_svg(svg)}</div>
<figcaption><p>{h(note)}</p>{link('./' + FOLDER + '/' + key + '.svg', '打开完整矢量图 ↗')}</figcaption>
<p class="map-status" aria-live="polite" hidden></p></figure>'''


def finding_card(finding, node, commit):
    source_map = {s['id']: s for s in node.get('source_refs', [])}
    sources = [source_map[s] for s in finding.get('source_ids', []) if s in source_map]
    fields = [
        ('依据与判断', finding.get('claim')),
        ('图中怎样表示', finding.get('drawing_decision')),
        ('相较已有成果', finding.get('change_from_prior')),
        ('适用年代', finding.get('period')),
        ('仍待核实', finding.get('limitation')),
    ]
    facts = ''.join('<div><dt>' + label + '</dt><dd>' + h(value) + '</dd></div>'
                    for label, value in fields if value)
    inputs = []
    for item in finding.get('source_inputs', []):
        path = item.get('path', '')
        if path:
            inputs.append('<li>' + link('https://github.com/mechgouki/luoyang-city/blob/' + commit + '/' + path,
                                        path.rsplit('/', 1)[-1]) + ' <span class="technical">' + h(item.get('pointer', '')) + '</span></li>')
    trace = '<details class="trace"><summary>核验记录中的来源位置</summary><ul>' + ''.join(inputs) + '</ul></details>' if inputs else ''
    roads = chips(finding.get('road_ids', []), 'segment')
    waters = chips(finding.get('water_ids', []), 'water') if finding.get('water_ids') else ''
    return f'''<details class="finding" id="finding-{h(finding['id'])}" tabindex="-1"><summary><span class="record-id">{h(finding['id'])}</span><span>{h(finding.get('public_label') or finding['title'])}</span></summary><div class="details-body"><dl class="facts finding-facts">{facts}</dl>{roads}{waters}{source_list(sources)}{trace}<p class="back-link">{link('#map-' + node['id'], '回到本节点图 ↑', data_return_map=node['id'])}</p></div></details>'''


def next_originals(node):
    items = []
    for source in node.get('next_originals', []):
        title = source.get('title', '下一原件')
        locator = source.get('locator', '')
        purpose = source.get('needed_to_decide', '')
        items.append('<li><strong>' + h(title) + '</strong>' +
                     ('<p>' + h(locator) + '</p>' if locator else '') +
                     ('<p><span class="field-label">用来判断：</span>' + h(purpose) + '</p>' if purpose else '') + '</li>')
    return '<details class="next-originals"><summary>下一份能改变判断的原件</summary><ol>' + ''.join(items) + '</ol></details>'


def node_section(node, svg, commit, number):
    identifier = node['id']
    title = node.get('public_title', node['title'])
    requirements = node.get('display_requirements', [])
    note = ' '.join(requirements[:2]) or '图面保留来源与关系各自的性质；未知接续不补线。'
    findings = ''.join(finding_card(finding, node, commit) for finding in node['findings'])
    relations = ''.join('<tr><th scope="row">' + h(row.get('from', '')) + ' → ' + h(row.get('to', '')) +
                        '</th><td>' + h(row.get('relation', '')) + '</td><td>' + h(row.get('period', '')) +
                        '</td><td>' + h(row.get('drawing_decision', '')) + '</td></tr>' for row in node.get('relations', []))
    relation_table = ('<details class="relation-details"><summary>关系与量距逐项对照</summary><div class="table-scroll" tabindex="0" aria-label="关系对照表，可左右滚动"><table><thead><tr><th>对象</th><th>关系</th><th>年代适用</th><th>图面处理</th></tr></thead><tbody>' + relations + '</tbody></table></div></details>') if relations else ''
    sources = '<details class="node-sources"><summary>本节点来源与本轮读取状态</summary>' + source_list(node.get('source_refs', []), True) + '</details>'
    return f'''<section class="node-section" id="node-{h(identifier)}" tabindex="-1" aria-labelledby="title-{h(identifier)}"><div class="section-heading"><div><p class="eyebrow">节点 {number:02d}</p><h2 id="title-{h(identifier)}">{h(title)}</h2></div>{link('#overview', '回到城市总览 ↑')}</div><p class="node-question">{h(node.get('question', ''))}</p><p class="section-intro">{h(node.get('summary', ''))}</p>
{map_figure(identifier, svg, title, note)}<div class="node-reading"><div><h3>这次核验怎样影响图面</h3><p class="muted">展开条目，查看依据、时期与本批的具体取舍。</p>{findings}</div><aside class="node-aside"><h3>从节点查到逐段证据</h3>{chips(node.get('road_ids', []), 'segment')}{chips(node.get('water_ids', []), 'water') if node.get('water_ids') else ''}<p>道路编号沿用已有登记。相邻编号、图面间距和关系框均不代表实测街址。</p>{next_originals(node)}</aside></div>{relation_table}{sources}</section>'''


def metric_list(metrics):
    items = []
    for metric in metrics:
        if not isinstance(metric, dict):
            items.append('<li>' + h(human(metric)) + '</li>')
            continue
        value = metric.get('value', metric.get('values', ''))
        heading = str(metric.get('label', '报告量值')) + ('：' + human(value) if value != '' else '') + str(metric.get('unit', ''))
        scope = metric.get('scope', '')
        items.append('<li><strong>' + h(heading) + '</strong>' + ('<br>' + h(scope) if scope else '') + '</li>')
    return '<ul class="metric-list">' + ''.join(items) + '</ul>' if items else '<p>本条未登记可直接采用的报告量值。</p>'


def segment_card(row, node_names, guide_by_road):
    rid = row['id']
    associations = []
    for node in row.get('node_ids', []):
        associations.append(link('#map-' + node, '回到' + node_names[node] + '局部图 ↑',
                                 data_return_map=node, data_return_segment=rid))
    if not associations:
        associations = [link('#guide-' + guide['id'], '在首页导览中读' + guide['label'], data_guide_link=guide['id'])
                        for guide in guide_by_road.get(rid, [])]
    fields = [('可定位路段', row.get('locatable_segment')), ('时代与适用范围', row.get('period')),
              ('起点', row.get('start')), ('终点', row.get('end')), ('端点状态', row.get('endpoint_status')),
              ('所经城门', row.get('gates')), ('同路、相接或待核关系', row.get('identity_notes'))]
    facts = ''.join('<div><dt>' + title + '</dt><dd>' + h(human(value)) + '</dd></div>' for title, value in fields)
    findings = ''.join('<li>' + link('#finding-' + finding['id'], finding['id'] + ' ' + finding['claim']) +
                       '<p>' + h(finding['drawing_decision']) + '</p></li>' for finding in row.get('findings', []))
    findings = '<div class="segment-findings"><h4>本批核验</h4><ul>' + findings + '</ul></div>' if findings else ''
    context = ''.join('<li>' + link('#finding-' + finding['id'], finding['id'] + ' ' + (finding.get('public_label') or finding['title'])) +
                      '<p>' + h(finding['claim']) + '</p><p>' + h(finding['drawing_decision']) + '</p></li>'
                      for finding in row.get('context_findings', []))
    context = '<div class="segment-findings"><h4>空间判断的背景材料</h4><p class="muted">下列核验用于理解周边空间；其统计或解释不直接转作本条道路的位置与测量值。</p><ul>' + context + '</ul></div>' if context else ''
    water_items = []
    for water in row.get('water_constraints', []):
        if not isinstance(water, dict):
            water_items.append('<p>' + h(human(water)) + '</p>')
            continue
        wid = water.get('id', '')
        water_items.append('<p>' + link('#water-' + wid, wid + ' ' + water.get('locality', '相关水项')) +
                           '　' + h(water.get('relation', '')) + '</p><p class="muted">' + h(water.get('limit', '')) + '</p>')
    water_section = '<div class="water-constraints"><h4>桥渠关系</h4>' + ''.join(water_items) + '</div>' if water_items else ''
    quote = '<figure class="source-quote"><figcaption>原记录所引文献</figcaption><blockquote>' + h(row['source_quote']) + '</blockquote></figure>' if row.get('source_quote') else ''
    sources = '<h4>原道路登记出处</h4>' + source_list(row.get('source_citations', []))
    if row.get('review_source_citations'):
        sources += '<h4>本批核验出处</h4>' + source_list(row['review_source_citations'], True)
    if row.get('next_originals'):
        sources += next_originals(row)
    node_ids = ' '.join(row.get('node_ids', []) or ['panorama'])
    return f'''<details class="segment" id="segment-{h(rid)}" data-segment="{h(rid)}" data-nodes="{h(node_ids)}" data-evidence="{h(row['geometry_status'])}" tabindex="-1"><summary><span class="record-id">{h(rid)}</span><span class="segment-title">{h(row['name'])}<span class="segment-labels"><span>{h(row['geometry_label'])}</span><span>{h(row['temporal_label'])}</span></span></span></summary><div class="details-body"><nav class="record-actions" aria-label="{h(rid)}图文往返">{''.join(associations)}{link(row['original_url'], '查看原道路记录 ↗')}</nav><dl class="facts">{facts}</dl><h4>已有报告量值及其对象</h4>{metric_list(row.get('reported_metrics', []))}{findings}{context}{water_section}<div class="unknown-note"><h4>仍待证部分</h4><p>{h(human(row.get('missing_evidence')))}</p></div>{quote}<details class="segment-sources"><summary>出处、页码与图号</summary>{sources}</details></div></details>'''


def panorama(data, hero):
    points, cards, guide_links = [], [], []
    for number, guide in enumerate(data['guides'], 1):
        gid = guide['id']
        points.append(f'<a class="panorama-point" id="point-{h(gid)}" href="#guide-{h(gid)}" data-guide-point="{h(gid)}" style="left:{float(guide["x"])}%;top:{float(guide["y"])}%" aria-label="{number} {h(guide["label"])}，查看画面依据"><span>{number}</span></a>')
        guide_links.append(link('#guide-' + gid, str(number) + ' ' + guide['label']))
        cards.append(f'''<article class="guide-card" id="guide-{h(gid)}" data-guide="{h(gid)}" tabindex="-1"><p class="guide-kicker">画面 {number:02d} · {h(guide['level'])}</p><h3>{h(guide['label'])}</h3><p>{h(guide['statement'])}</p><div class="record-links">{link(guide['link'], '查对应依据 →')}{''.join(link('#segment-' + rid, rid) for rid in guide.get('road_ids', []))}{''.join(link('#water-' + wid, wid) for wid in guide.get('water_ids', []))}</div><p class="back-link">{link('#panorama', '回到全幅画面 ↑', data_return_guide=gid)}</p></article>''')
    return f'''<section class="panorama-section" id="panorama" tabindex="-1" aria-labelledby="panorama-title"><div class="section-heading"><div><p class="eyebrow">从画面回到依据</p><h2 id="panorama-title">这幅盛时洛阳，哪些部分有据？</h2></div></div><p class="section-intro">沿用已批准的全幅首页图。六处编号是阅读入口，点开可查道路、水流与建筑关系；画面上的位置不作为古代坐标，也不提高证据等级。</p>
<figure class="panorama-figure"><div class="panorama-stage"><picture><source media="(max-width:600px)" srcset="./{h(hero['small'])}"><img src="./{h(hero['full'])}" width="{hero['width']}" height="{hero['height']}" alt="盛时洛阳全幅艺术复原示意：宫城、永宁寺、主要道路、南城门、洛水与浮桥。古岸线、桥头和部分道路连接含艺术表达。" loading="lazy" decoding="async" data-hero-revision="{h(hero['revision'])}"></picture><div class="panorama-points">{''.join(points)}</div></div><figcaption><p>完整图幅按自然比例展示。编号用于解释画面；图中水面宽度、洲滩、建筑外观与未知连接仍按各自证据说明阅读。</p><label class="guide-toggle" hidden><input type="checkbox" id="show-panorama-guides" checked>显示画面编号</label></figcaption></figure>
<nav class="guide-index" aria-label="六处画面依据">{''.join(guide_links)}</nav><div class="guide-grid">{''.join(cards)}</div><aside class="picture-purpose"><h3>首页图与体量对照，怎样一起看？</h3><p>本页保留当前首页展示图。另一个全景专题使用图06a投影与建筑体量作对照，供核查来源布局、尺度和构图。两幅艺术图各有用途，画面标记均不承担跨图配准。</p>{link(BASE + 'prosperity-city-panorama.html', '打开来源投影与建筑体量对照 ↗')}</aside></section>'''


def water_section(data):
    constraints = {}
    for row in data['segments']:
        for item in row.get('water_constraints', []):
            if isinstance(item, dict) and item.get('id'):
                constraints.setdefault(item['id'], item)
    cards = []
    for water in data['waters']:
        wid = water['id']
        context = constraints.get(wid, {})
        basis = water.get('basis', {})
        note = basis.get('relative_topology_note', water.get('current_index_basis', ''))
        level = '<p class="water-level">' + h(context['level']) + '</p>' if context.get('level') else ''
        locality = '<p><span class="field-label">地段：</span>' + h(context['locality']) + '</p>' if context.get('locality') else ''
        limit = '<p class="unknown-note">' + h(context['limit']) + '</p>' if context.get('limit') else ''
        related = [row['id'] for row in data['segments'] if any(isinstance(c, dict) and c.get('id') == wid for c in row.get('water_constraints', []))]
        cards.append(f'''<article class="water-card" id="water-{h(wid)}" tabindex="-1"><p class="record-id">{h(wid)}</p><h3>{h(water['name'])}</h3>{level}{locality}<p>{h(note)}</p>{limit}{chips(related, 'segment')}<p>{link(water['original_url'], '查看水系原记录与图面 ↗')}</p></article>''')
    return '<section class="waters-section" id="waters"><div class="section-heading"><div><p class="eyebrow">道路经过怎样的水体</p><h2>水项与接续限制</h2></div></div><p class="section-intro">沿用既有水系登记。图上可描的研究河段、文献地望与同期实测岸线分别理解；本批没有增加北魏岸线。</p><div class="water-grid">' + ''.join(cards) + '</div></section>'


def make_page(data, svgs, hero, commit, offline=False):
    nodes = data['nodes']
    counts = data['counts']
    names = {n['id']: n.get('short_title', n.get('public_title', n['title'])) for n in nodes}
    node_nav = ''.join(link('#node-' + n['id'], f'{index:02d} ' + names[n['id']]) for index, n in enumerate(nodes, 1))
    node_sections = ''.join(node_section(node, svgs[node['id']], commit, number) for number, node in enumerate(nodes, 1))
    guide_by_road = {}
    for guide in data['guides']:
        for rid in guide.get('road_ids', []):
            guide_by_road.setdefault(rid, []).append(guide)
    segment_cards = ''.join(segment_card(row, names, guide_by_road) for row in data['segments'])
    options = ''.join('<option value="' + h(n['id']) + '">' + h(names[n['id']]) + '</option>' for n in nodes)
    download_items = [(FOLDER + '/overview.svg', '联读总览 · SVG')]
    download_items += [(FOLDER + '/' + n['id'] + '.svg', names[n['id']] + ' · SVG') for n in nodes]
    download_items += [(FOLDER + '/segments.csv', '逐段证据表 · CSV'),
                       (FOLDER + '/readings.json', '核验与来源记录 · JSON'),
                       (MANIFEST, '版本与校验清单 · JSON'), (BUNDLE, '完整离线图集 · ZIP')]
    downloads = ''.join('<li>' + link((BASE if offline and path == BUNDLE else './') + path, label, download='') + '</li>' for path, label in download_items)
    changes = ''.join('<li>' + link('#node-' + n['id'], names[n['id']]) + '：' + h(n.get('summary', '')) + '</li>' for n in nodes)
    offline_note = '<p class="offline-note">离线包可阅读本页、图面和证据；原件及历史专题的链接需联网访问。</p>' if offline else ''
    overview_note = '来源图骨架与四处节点联读。各局部图保留自己的来源框架；关系排版不提供新的古代坐标。'
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>道路、水流与城市节点 · 盛时洛阳</title><meta name="description" content="联读宫前御道、白马寺坊街、司马门道路与建春门桥渠，逐段回查来源、年代及仍未知的连接。"><link rel="stylesheet" href="./{FOLDER}/atlas.css"><script defer src="./{FOLDER}/atlas.js"></script></head>
<body data-page="city-nodes-r7"><a class="skip-link" href="#main">跳到正文</a><header class="site-header"><div class="wrap header-row">{link(BASE, '盛时洛阳', class_='brand')}<nav aria-label="研究导航">{link('#overview', '城市总览')}{link('#panorama', '首页图依据')}{link('#register', '逐段证据')}{link('#downloads', '下载')}</nav></div></header>
<main id="main" class="wrap"><section class="mast"><p class="eyebrow">北魏洛阳 · 516—528 年</p><h1>从道路与水流，<br class="wide-only">读懂四处城市节点</h1><p class="lead">一段道路怎样经过城门、连接街坊或跨越水流？把图面、时代与原件放在一起，逐处辨明已有依据、研究解释和仍未知的接续。</p><nav class="node-nav" aria-label="四处城市节点">{node_nav}</nav>{offline_note}</section>
<section id="overview" class="overview-section" tabindex="-1" aria-labelledby="overview-title"><div class="section-heading"><div><p class="eyebrow">先看城市，再读局部</p><h2 id="overview-title">四处节点联读总览</h2></div><p class="small-count">{counts['nodes']}处节点 · {counts['findings']}项核验<br>{counts['segments']}条本批联读来源记录</p></div><p class="section-intro">总览接入已有城市骨架。图中的定位参照、局部路迹和关系示意各守其来源；点击节点或编号，沿同一对象回查下方证据。</p><ul class="legend" aria-label="图面性质"><li><span class="legend-source"></span>来源图笔画或位置参照</li><li><span class="legend-relation"></span>文献关系或研究解释</li><li><span class="legend-unknown"></span>端点或接续待证</li></ul>{map_figure('overview', svgs['overview'], '四处城市节点联读总览', overview_note)}<details class="reading-note"><summary>这张总览能告诉我们什么？</summary><p>实线可表示来源图中可读的笔画，原图若属复原示意，其性质也继续保留。局部图有自己的图框，不能把各图的像素或排列距离拼成实测全城。516—528年为盛时综合研究窗口，宽时代遗迹与窗口内状态变化分别注明。</p><p>本批核验聚焦关系、量值对象与同期性；逐段记录数不是独立古代道路总数。</p></details></section>
{node_sections}
{panorama(data, hero)}
<section class="register-section" id="register" aria-labelledby="register-title"><div class="section-heading"><div><p class="eyebrow">从图面回查原件</p><h2 id="register-title">逐段证据</h2></div>{link(BASE + 'luoyang-all-roads.html', '查看全城84条道路记录 ↗')}</div><p class="section-intro">本表收录四处节点与首页导览涉及的来源记录。编号沿用全城道路总表；来源图符号、报告量值与文献关系分别保留。</p><div class="filters" id="segment-filters" hidden><label for="segment-query">查找<input type="search" id="segment-query" placeholder="如 永桥、P01、坊门"></label><label for="node-filter">节点<select id="node-filter"><option value="">全部节点</option>{options}<option value="panorama">首页南城门与永桥</option></select></label><label for="evidence-filter">图面依据<select id="evidence-filter"><option value="">全部依据</option><option value="source_frame">有独立来源图笔画或符号</option><option value="relation_only">目前只到地段或关系</option></select></label><button type="button" id="segment-clear">清空筛选</button><output id="segment-count" aria-live="polite">{counts['segments']} / {counts['segments']} 条来源记录</output></div><noscript><p class="reading-note">无需脚本也可展开全部记录、查阅来源和下载图表；图上编号直接链接到对应条目。</p></noscript><p id="segment-empty" class="empty-note" hidden>没有符合条件的记录。请换一个词，或清空节点与依据筛选。</p><div class="segment-list">{segment_cards}</div></section>
{water_section(data)}
<section class="changes-section" id="changes"><div class="section-heading"><div><p class="eyebrow">本批的具体取舍</p><h2>哪些判断进入了图面</h2></div></div><ul>{changes}</ul><p>每一项核验都保留其来源、适用时期、绘图决定与下一原件。已核定的关系可以联读；共同测线、精确端点与完整岸线尚未取得的部分继续留缺。</p></section>
<section class="downloads-section" id="downloads"><div class="section-heading"><div><p class="eyebrow">带走图面与依据</p><h2>下载与离线阅读</h2></div></div><p class="section-intro">矢量图可放大打印，CSV保留逐段证据，JSON保存核验与来源。离线图集包含本页、全部图面、首页图与证据表。</p><ul class="downloads">{downloads}</ul></section></main>
<footer class="site-footer"><div class="wrap"><p>盛时洛阳 · 研究 {h(data['research_version'])} · 首页沿用全幅取景版 V12</p><p>{link(BASE, '正式首页')} · {link(BASE + 'prosperity-city-atlas.html', '城市定位依据')} · {link(BASE + 'luoyang-water-atlas.html', '水系定位')} · {link('https://github.com/mechgouki/luoyang-city/issues/47', '研究记录')} · {link('https://github.com/mechgouki/luoyang-city/issues/52', '当前交接')}</p><p class="technical">实现 {h(VERSION)} · 来源提交 {h(commit[:12])} · 独立图框未合并配准；未新增古代坐标或岸线。</p></div></footer></body></html>'''
