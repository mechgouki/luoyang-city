"""One complete road atlas; native source frames and qualitative relations stay distinct."""
import copy
import csv
import hashlib
import json
import shutil
import textwrap
from collections import Counter
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from road_location_atlas import NS, PAPER, INK, MUTED, TEAL, AMBER, BLUE, tag, text, line, unknown, human

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'research/roads-r62'
BASE = 'https://mechgouki.github.io/luoyang-city/'
PAGE = 'luoyang-all-roads.html'
FOLDER = 'all-roads'
KEY = 'all_road_locations'
VERSION = 'all-road-atlas-r6.2'
MANIFEST = FOLDER + '/manifest.json'
BUNDLE = 'downloads/luoyang-all-roads.zip'
GROUPS = {
    'legacy': '主干道来源', 'documentary': '文献道路', 'palace': '宫内及宫墙外道路',
    'ward': '坊街证据', 'gate': '门道', 'bridge': '桥道',
}
DOWNLOADS = {
    FOLDER + '/city-all-roads.svg': '全城道路总图 · SVG',
    FOLDER + '/records.csv': '全部逐路证据 · CSV',
    FOLDER + '/records.json': '来源、原始读点与对应关系 · JSON',
    FOLDER + '/coverage.csv': '全库覆盖核对表 · CSV',
    MANIFEST: '版本与校验清单 · JSON',
    BUNDLE: '完整离线图集 · ZIP',
}


def load(path):
    return json.loads(path.read_bytes())


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def link(url, label):
    return '<a href="' + escape(url, quote=True) + '">' + escape(label) + '</a>'


def lookup(data):
    return data['sources'] if isinstance(data['sources'], dict) else {s['id']: s for s in data['sources']}


def route_link(parent, row, **attrs):
    rid = row['id'] if isinstance(row, dict) else row
    a = tag(parent, 'a', href=BASE + PAGE + '#' + rid, tabindex=0, data_record_ref=rid, **attrs)
    tag(a, 'title').text = row['name'] if isinstance(row, dict) else rid
    return a


def panel(root, x, y, width, height, title, subtitle):
    tag(root, 'rect', x=x, y=y, width=width, height=height, rx=5,
        fill='#fffdf7', stroke='#d1d6c7')
    text(root, x + 20, y + 36, title, 22, font_weight=600)
    text(root, x + 20, y + 64, subtitle, 14, MUTED)


def wrap_svg(parent, x, y, value, chars=25, size=14, color=MUTED, limit=None, step=23):
    lines = textwrap.wrap(str(value), chars, break_long_words=True, break_on_hyphens=False) or ['']
    if limit and len(lines) > limit:
        lines = lines[:limit]
        lines[-1] = lines[-1][:-1] + '…'
    for i, value in enumerate(lines):
        text(parent, x, y + i * step, value, size, color)


def plate(data, old_svg):
    """SVG layout transforms never establish a common city or ground coordinate system."""
    records = data['records']
    groups = {g: [r for r in records if r['group'] == g] for g in GROUPS}
    root = ET.Element('{' + NS + '}svg', {
        'viewBox': '0 0 1440 3430', 'width': '1440', 'height': '3430',
        'role': 'img', 'aria-labelledby': 'all-road-title all-road-description', 'lang': 'zh-CN'})
    tag(root, 'title', id='all-road-title').text = '盛时洛阳全城道路总览'
    tag(root, 'desc', id='all-road-description').text = (
        '上部为两个独立来源图框；中部为司马门、永巷及宫内局部道路；下部为坊街、门道、桥道和全部文献道路索引。'
        '原始路迹保留断段，示意关系另标，端点未知留空。各分图没有地理配准，卡片排列不是古代道路坐标。')
    tag(root, 'rect', width=1440, height=3430, fill=PAPER)
    defs = tag(root, 'defs')
    clip = tag(defs, 'clipPath', id='legacy-frames-clip')
    tag(clip, 'rect', width=1440, height=830)
    marker = tag(defs, 'marker', id='source-arrow', viewBox='0 0 10 10', refX=9, refY=5,
                 markerWidth=5, markerHeight=5, orient='auto-start-reverse')
    tag(marker, 'path', d='M 0 1 L 9 5 L 0 9', fill='none', stroke=AMBER, stroke_width=1.5)
    legacy = ET.fromstring(old_svg)
    # Preserve every old numeric path; only its presentation and links belong to this new atlas.
    for element in legacy.iter():
        if element.tag == '{' + NS + '}text' and element.text:
            if element.text == '盛时洛阳 · 全城主干道分级定位':
                element.text = '盛时洛阳 · 全城道路总览'
            elif element.text == '虚线：门端间示意连接':
                element.text = '虚线／箭杆：示意关系'
            elif element.text == '空圈：最后实测点／登陆点未知':
                element.text = '空圈：端点或接续未知'
            elif '研究时段 516—528 年  /  21' in element.text:
                element.text = '研究时段 516—528 年  /  道路、门道、桥道同批登记  /  各来源图框分别读取'
        if element.tag == '{' + NS + '}a':
            rid = element.get('data-road-ref')
            if rid == 'S03':
                label = ''.join(element.itertext())
                entity = 'road_jinyang' if '津阳' in label else 'road_xuanyang' if '宣阳' in label else None
                found = next((r for r in records if entity and entity in r.get('entity_ids', [])), None)
                if found is None:
                    found = next((r for r in groups['bridge'] if '永桥' in r['name']), None)
                rid = found['id'] if found else 'T13'
            if rid and rid not in {'S01', 'S02'}:
                element.set('href', BASE + PAGE + '#' + rid)
                element.set('data-record-ref', rid)
    g = tag(root, 'g', clip_path='url(#legacy-frames-clip)')
    g.append(legacy)
    # The cropped old supplement cards do not belong to this new SVG DOM.
    for parent in list(legacy.iter()):
        for child in list(parent):
            if child.get('data-road-ref') in {'S01', 'S02'} or child.get('data-frame') == 'qualitative-relations':
                parent.remove(child)

    panel(root, 28, 850, 440, 575, 'C  司马门内道路', '2023 原图像素 · 三段双线分别保留')
    sima = next(r for r in groups['palace'] if '司马门' in r['name'])
    sdata = load(ROOT / 'research/prosperity-r5/sima-road.json')['image']
    sg = tag(route_link(root, sima), 'g', transform='translate(-59 568) scale(.48)',
             data_frame='frame-sima2023')
    for i, coords in enumerate(sdata['sima_road_ink_px']):
        line(sg, coords, TEAL, 5, data_layer='source', data_part=i,
             data_geometry_role='native-source-ink-not-road-width')
    box = sdata['storage_box_centerline_px']
    tag(sg, 'rect', x=box[0], y=box[1], width=box[2]-box[0], height=box[3]-box[1],
        fill='none', stroke=BLUE, stroke_width=3, stroke_dasharray='8 7', data_layer='inferred')
    text(sg, 748, 970, '仓区示意框', 26, BLUE, text_anchor='middle')
    text(sg, 748, 1010, '不是墙线', 26, BLUE, text_anchor='middle')
    for xy in [sdata['sima_road_ink_px'][0][0], sdata['sima_road_ink_px'][-1][-1]]:
        unknown(sg, xy, 8, data_geometry_role='source-ink-end-not-ancient-terminus')
    gx, gy = sdata['gate_label_px']
    text(sg, gx, gy + 42, sima['id'] + ' 司马门方向', 28, TEAL, text_anchor='middle')
    text(root, 50, 1321, '最宽约40米：北魏路面的报告量值。', 16, TEAL)
    text(root, 50, 1350, '双线间距不量路宽，仓区框不量墙距。', 15, MUTED)
    text(root, 50, 1380, '与A图没有可接受的共同测点。', 15, AMBER)
    text(root, 50, 1405, '图中缺口不补连；点击进入逐路记录。', 14, MUTED)

    panel(root, 488, 850, 924, 575, 'D  永巷〔推定名〕：图示与局部发掘', '2021 年发掘语境图，新华社2022年刊载 · 上为北 · 无比例尺')
    yrow = next(r for r in groups['palace'] if '永巷' in r['name'])
    ydata = load(DATA / 'sources/yongxiang-arrows.json')
    text(root, 510, 952, '六段箭杆据来源图摘读；箭头只表示图示走向，不表示单向交通。', 16, AMBER)
    text(root, 510, 981, '2022年局部发掘：东折处路宽约6.5→11米；魏晋早期通道宽约4米。', 15)
    yg = tag(route_link(root, yrow), 'g', transform='translate(530 910) scale(.8)',
             data_frame='frame-yongxiang2021')
    for i, coords in enumerate(ydata['geometry']['coordinates']):
        line(yg, coords, AMBER, 5, marker_end='url(#source-arrow)', data_layer='inferred',
             data_part=i, data_geometry_role='source-direction-arrow-stems')
    text(yg, 157, 423, '千秋门题注', 21, MUTED, text_anchor='middle')
    text(yg, 875, 418, '司马门内道路题注', 21, MUTED, text_anchor='end')
    tag(yg, 'rect', x=422, y=483, width=173, height=113, fill='#edf0e5',
        stroke='#a5b1a2', stroke_width=2, stroke_dasharray='6 6', data_layer='inferred')
    text(yg, 508, 529, '显阳殿遗址', 22, MUTED, text_anchor='middle')
    text(yg, 508, 563, '原图示意范围', 19, MUTED, text_anchor='middle')
    text(root, 510, 1398, yrow['id'] + '  黄色箭头间留白不补连；不据箭头推出路缘、桥位或已证交会点。', 15, AMBER)

    panel(root, 28, 1450, 900, 650, 'E  宫内与宫墙外：逐处局部证据', '下列卡片只作检索排版，不按宫内位置、方向或距离排列。起讫详见逐路记录。')
    for i, row in enumerate(groups['palace']):
        x, y = 48 + (i % 3) * 287, 1538 + (i // 3) * 132
        a = route_link(root, row, data_geometry_role='nonspatial-record-card')
        tag(a, 'rect', x=x, y=y, width=269, height=114, rx=3, fill='#edf0e5', stroke='#d4dccf')
        text(a, x + 12, y + 26, row['id'], 15, TEAL, font_weight=700)
        wrap_svg(a, x + 12, y + 51, row['name'], chars=16, size=15, color=INK, limit=2, step=21)
        text(a, x + 12, y + 98, '点开核对路段、量值及分期 →', 12, MUTED)
    text(root, 48, 2080, '局部宽度、残长与探沟尺寸分别记录；不由相邻建筑拼成完整宫路网。', 15, AMBER)

    panel(root, 948, 1450, 464, 350, 'F  宫前阊阖门：三门道', '原发掘平面像素摘读 · 单独图框')
    gates = load(ROOT / 'research/prosperity-v3/gate-plan.json')
    grow = next((r for r in groups['gate'] if '阊阖' in r['name']), groups['gate'][0])
    gg = tag(route_link(root, grow), 'g', transform='translate(740 1410) scale(1.32)',
             data_frame='frame-changhe-s37')
    components = gates['components']
    if isinstance(components, list):
        components = {c['id']: c for c in components}
    for key, comp in components.items():
        if 'passage' not in key:
            continue
        coords = comp.get('source_px') or comp.get('polygon_px') or comp.get('geometry_px') or comp.get('points_px')
        if isinstance(coords, dict):
            coords = coords.get('coordinates')
        if coords:
            tag(gg, 'polygon', points=' '.join(f'{x},{y}' for x, y in coords),
                fill='#d9e8df', stroke=TEAL, stroke_width=1.5, data_layer='source',
                data_geometry_role='visible-middle-passage-band', data_component=key)
    text(root, 970, 1705, grow['id'] + '  仅摘读原图可见的门道中段。', 15, TEAL)
    text(root, 970, 1735, '矩形边界不是完整门道长度或封闭墙。', 14, MUTED)
    text(root, 970, 1764, '不向二号、三号宫门补成连续道路。', 14, AMBER)
    panel(root, 948, 1820, 464, 280, 'G  有门道证据的节点', '门道条目另计；未见通道数量的不补“三门道”。')
    gate_short = ['宫前阊阖门三道','建春门三道','二号宫门三道','神虎门三道','东掖门三道',
                  '太极殿东閤门','横道西端单门道','屋宇式院门','廊道式院门','三门〔东郭〕',
                  '白马寺南坊门','三号宫门〔数未定〕','永巷东折门','太极北廊三处门']
    for i, row in enumerate(groups['gate']):
        x, y = 968 + (i % 2) * 222, 1913 + (i // 2) * 27
        a = route_link(root, row, data_geometry_role='nonspatial-record-card')
        text(a, x, y, row['id'] + ' ' + gate_short[i], 13, TEAL)

    panel(root, 28, 2130, 550, 480, 'H  白马寺南：六条坊街', '三条南北街、三条东西街分别登记；以下符号不组成实测方格网。')
    for i, row in enumerate(groups['ward'][:6]):
        x, y = 50 + (i % 3) * 174, 2233 + (i // 3) * 132
        a = route_link(root, row, data_geometry_role='qualitative-ward-street-symbol')
        text(a, x, y, row['id'], 16, TEAL, font_weight=700)
        ends = [[x + 67, y + 20], [x + 67, y + 57]] if i < 3 else [[x + 22, y + 25], [x + 117, y + 25]]
        line(a, ends, AMBER, 3, stroke_dasharray='6 6', data_layer='inferred')
        for xy in ends:
            unknown(a, xy, 5)
        wrap_svg(a, x, y + (82 if i < 3 else 57), row['name'], chars=10, size=13, limit=2, step=21)
    if len(groups['ward']) > 6:
        a = route_link(root, groups['ward'][6])
        text(a, 50, 2464, groups['ward'][6]['id'] + ' 坊间道路：未分条集合，另立证据记录。', 14, TEAL)
    text(root, 50, 2495, '居中纵街宽约22米；相邻横街间距约40米。', 15, TEAL)
    text(root, 50, 2524, '南坊门缺口约7.5米；车辙带4.6米。', 15)
    text(root, 50, 2553, '以上四种量值不能互换，门到中央十字距离未知。', 14, AMBER)
    a = route_link(root, 'X02')
    text(a, 50, 2582, 'X02 西阳门外大道 ↔ 南坊门 ↔ 坊内中路', 15, TEAL)

    panel(root, 598, 2130, 814, 480, 'I  桥道：过水关系与登陆点', '五个既有桥实体全部接入。比定桥名、古里距离及坍塌事件各守其出处。')
    for i, row in enumerate(groups['bridge']):
        y = 2233 + i * 73
        a = route_link(root, row, data_geometry_role='qualitative-bridge-relation')
        text(a, 620, y, row['id'] + ' ' + row['name'], 17, TEAL, font_weight=600)
        wrap_svg(a, 620, y + 27, row['locatable_segment'], chars=45, size=14, limit=2, step=21)

    panel(root, 28, 2640, 1384, 680, 'J  文献道路：全部定位关系索引', '门内、门外、桥南道路分别保留；以下三列只作检索排版，不是道路平面或连续路线。')
    for i, row in enumerate(groups['documentary']):
        x, y = 50 + (i % 3) * 457, 2742 + (i // 3) * 64
        a = route_link(root, row, data_geometry_role='nonspatial-documentary-index')
        text(a, x, y, row['id'] + ' ' + row['name'], 16, TEAL, font_weight=600)
        wrap_svg(a, x, y + 24, row['locatable_segment'], chars=28, size=12, limit=1)
    xrow = next(r for r in groups['legacy'] if r['id'] == 'X01')
    a = route_link(root, xrow)
    text(a, 32, 3350, 'X01 西明—青阳大道局部发掘：与R03候选对应，原测线未取得；不重复算成另一条大道。', 16, TEAL)
    text(root, 32, 3380, 'R6.2 · 本批完整登记现有材料；不是古代道路总数。1993年602—608页及完整附图仍待取得。', 16, AMBER)
    text(root, 32, 3410, '全部原始读点、时代、报告量值、桥渠约束与缺件见逐路表。地理配准为零；未新增盛时北魏古岸线。', 14, MUTED)
    return ET.tostring(root, encoding='unicode') + '\n'


def source_html(data, refs):
    sources = lookup(data)
    items = []
    for ref in refs:
        source = sources[ref]
        title = source.get('title', source.get('name', ref))
        url = source.get('url')
        locator = source.get('locator', source.get('pages_figure', source.get('scope', '')))
        items.append('<li>' + (link(url, title) if url else escape(title)) +
                     '　' + escape(human(locator)) + '</li>')
    return '<ul>' + ''.join(items) + '</ul>'


def card(row, data):
    labels = [('可定位路段', 'locatable_segment'), ('时代与适用范围', 'period'),
              ('起点', 'start'), ('终点', 'end'), ('端点状态', 'endpoint_status'),
              ('所经城门', 'gates'), ('已有报告量值与口径', 'reported_metrics'),
              ('同路、相接或待核关系', 'identity_notes')]
    facts = ''.join('<div><dt>' + title + '</dt><dd>' + escape(human(row.get(field))) + '</dd></div>'
                    for title, field in labels)
    water = []
    for item in row.get('water_constraints', []):
        if isinstance(item, dict):
            wid = item.get('id', item.get('water_id', ''))
            title = wid + ' ' + item.get('relation', '')
            body = '；'.join(human(item[k]) for k in ('level', 'locality', 'limit') if k in item)
            water.append('<p>' + (link(BASE + 'luoyang-water-atlas.html#' + wid, title)
                                   if wid.startswith('W') else escape(title)) + '　' + escape(body) + '</p>')
        else:
            water.append('<p>' + escape(human(item)) + '</p>')
    geometry = '保留独立来源图读点；图的性质与限制见出处和定位说明。' if row['geometry_refs'] else '尚无可直接描绘的原图路段；以文献或发掘地段关系登记。'
    names = {r['id']:r['name'] for r in data['records']}
    neighbors = set()
    for relation in data.get('identity_crosswalk', []):
        if row['id'] == relation.get('from'):
            neighbors.add(relation.get('to'))
        if row['id'] == relation.get('to'):
            neighbors.add(relation.get('from'))
    related = ' · '.join(link('#'+rid, rid+' '+names[rid]) for rid in sorted(neighbors) if rid in names)
    if related:
        related = '<p class="related"><strong>对照记录：</strong>' + related + '</p>'
    return f'''<details class="road" data-record="{row['id']}" data-group="{row['group']}" id="{row['id']}"><summary><span class="road-id">{row['id']}</span><span class="road-title">{escape(row['name'])}</span><span class="badge">{GROUPS[row['group']]}</span></summary><div class="road-body"><p class="geometry-note">{geometry}</p><dl class="facts">{facts}</dl>{related}<div class="constraint"><strong>桥渠约束与仍待证部分</strong>{''.join(water)}<p>{escape(human(row['missing_evidence']))}</p></div><div class="sources"><strong>出处、页码与图号</strong>{source_html(data,row['source_refs'])}</div></div></details>'''


def table(rows, columns):
    return '<div class="table-wrap"><table><thead><tr>' + ''.join('<th>' + escape(label) + '</th>' for key, label in columns) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + escape(human(row.get(key))) + '</td>' for key, label in columns) + '</tr>' for row in rows) + '</tbody></table></div>'


def make_page(data, svg, commit, offline=False):
    prefix = BASE if offline else './'
    counts = Counter(r['group'] for r in data['records'])
    inline = svg.replace('<svg ', '<svg id="all-road-map" ', 1).replace(BASE + PAGE + '#', '#')
    registers = ''.join('<section class="register-group"><h3>' + label + ' <small>' + str(counts[group]) + ' 条记录</small></h3>' + ''.join(card(r, data) for r in data['records'] if r['group'] == group) + '</section>' for group, label in GROUPS.items())
    numbers = ''.join('<a href="#register" data-category-link="' + group + '"><strong>' + str(counts[group]) + '</strong>' + label + '</a>' for group, label in GROUPS.items())
    downloads = ''.join('<li><a download href="' + (BASE if offline and path == BUNDLE else './') + path + '">' + label + '</a></li>' for path, label in DOWNLOADS.items())
    coverage_fields = list(data['coverage'][0])
    # Stable compact human-facing columns; the CSV/JSON retain every coverage field.
    selected = [key for key in ['entity_id', 'name', 'entity_type', 'record_ids', 'status', 'reason', 'decision'] if key in coverage_fields]
    if not selected:
        selected = coverage_fields[:5]
    column_names = {'entity_id':'原实体编号','name':'名称','entity_type':'原登记类型','record_ids':'对应记录','status':'核对状态','reason':'理由','decision':'处理说明'}
    coverage = table(data['coverage'], [(key, column_names.get(key, key)) for key in selected])
    exclusions = ''.join('<li><strong>' + escape(row.get('id','') + ' ' + row.get('name','')) + '</strong>：' + escape(row.get('reason',row.get('note',''))) + '</li>' for row in data['exclusions'])
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>全城道路总览 · 盛时洛阳</title><meta name="description" content="一次汇集主干道来源、文献道路、宫内细路、六条坊街、门道与五处桥道，逐段区分图面依据、推定连接和未知端点。"><link rel="stylesheet" href="./all-roads/atlas.css"><script src="./all-roads/atlas.js" defer></script></head><body>
<header><div class="wrap">{link(prefix,'盛时洛阳 · 城市复原')}<nav>{link(prefix+'luoyang-road-atlas.html','主干道来源图')}{link(prefix+'luoyang-water-atlas.html','水系定位')}{link(prefix+'prosperity-city-panorama.html','城市全景')}{link('#downloads','下载图表')}</nav></div></header>
<main class="wrap"><section class="mast"><div><p class="eyebrow">北魏都城研究 / 516—528 年 / R6.2</p><h1>全城道路总览</h1></div><p class="lead">从御道、宫路到坊街、门道与桥道，把现有材料一次收齐。每条记录都能回查时代、出处、路段和端点；同路候选并列核对，原图断点继续保留。</p></section>
<div class="numbers">{numbers}</div><p class="scope-note"><strong>{len(data['records'])} 条是证据记录数，不是独立古代道路总数。</strong> 21条旧主干道来源与21个既有文献道路实体采用不同统计口径；同路、同段或相接关系见逐路表。缺原件的部分已列入，不代表已复原全部古代街巷。</p>
<figure class="figure"><div class="map-tools" id="map-tools" hidden><label><input id="show-source" type="checkbox" checked><span class="key-line"></span>图面路迹</label><label><input id="show-inferred" type="checkbox" checked><span class="key-line inferred"></span>示意／推定</label><label><input id="show-unknown" type="checkbox" checked><span class="key-point"></span>端点未知</label><label for="zoom">放大 <input id="zoom" type="range" min="100" max="220" step="20" value="100"><output id="zoom-value">100%</output></label><div class="panel-nav"><button data-map-panel="0,0">内城与外围</button><button data-map-panel="0,850">司马门与永巷</button><button data-map-panel="0,1450">宫路与门道</button><button data-map-panel="0,2130">坊街与桥道</button><button data-map-panel="0,2640">文献道路</button></div></div><div id="map-scroll" tabindex="0" aria-label="全城道路总图，可上下左右滚动或用分区按钮阅读">{inline}</div><figcaption><p><strong>一张总图，多幅独立来源图框。</strong> 实线说明来源图上有可读笔画；其中后世复原样线仍保留其性质。虚线与永巷箭杆表示示意关系，空圈表示古路端点或接续仍未知。下方局部卡片与文献索引只按阅读顺序排版。点选编号可展开证据。</p>{link('./all-roads/city-all-roads.svg','打开完整矢量图 ↗')}</figcaption></figure>
<div class="reading"><article><h3>完整登记，不抹平差别</h3><p>全部既有道路实体、桥实体及有依据的门道一起核对。宫城阊阖门与西垣阊阖门、道路与门道、同路的不同出处分别保存。</p></article><article><h3>宽度必须跟着路段读</h3><p>司马门内道路、仓区内路、永巷各期路面、坊门缺口与车辙带使用不同量值。探沟长宽和遗迹残长均不转写成整条街道尺寸。</p></article><article><h3>跨水处保留未知</h3><p>五处桥道逐项登记。永桥两岸登陆点、谷水／阳渠部分分合点继续沿用水系等级；不凭道路方向补出古岸线与桥头。</p></article></div>
<section id="register"><div class="section-head"><h2>全部逐路证据</h2><p>可按编号、路名、城门、桥渠查找</p></div><div class="filter" id="filter" hidden><label for="query">查找 <input id="query" type="search" placeholder="如 T04、永巷、白马寺"></label><label for="group-filter">类别 <select id="group-filter"><option value="">全部类别</option>{''.join('<option value="'+g+'">'+n+'</option>' for g,n in GROUPS.items())}</select></label><button id="clear" type="button">显示全部</button><output id="count" aria-live="polite">{len(data['records'])} / {len(data['records'])} 条证据记录</output></div><noscript><p>可直接点开每条记录；地图编号和下载无需脚本。</p></noscript><p id="empty" class="empty" hidden>没有符合条件的记录。可清空条件后继续查阅。</p>{registers}</section>
<section class="audit" id="coverage"><h2>全库覆盖核对</h2><p>逐项核对原实体库及本次补入的局部路段。寺院、里坊引文中的道路地址指向相应道路记录，不把每次道路提及另算一条路；可下载完整覆盖表。</p><details><summary>展开 {len(data['coverage'])} 项覆盖记录</summary>{coverage}</details></section>
<section class="audit" id="exclusions"><h2>未另立道路的条目</h2><p>泛称、重复提及、跨时期路面与缺乏道路证据的名称，按理由保留在核对结果中。</p><details><summary>展开 {len(data['exclusions'])} 项边界说明</summary><ul>{exclusions}</ul></details></section>
<section class="audit" id="next-original"><h2>仍可继续核查的原件</h2><p><strong>首项仍是1993年《北魏洛阳外廓城和水道的勘查》602—608页及完整附图。</strong> 必须连同图例与图边取得，才能区别实测线、推定线、探孔与最后测点。维普文献号1002554709，知网篇名代码KAGU199307004，收录库CJFD9093。</p><p>白马寺三纵三横街道还需完整发掘总平面与测线端点；宫城局部新材料须继续核对魏晋、北魏与北周层位。永巷来源图箭头只是解释性方向，千秋门平面图的“北朝遗迹”不自动细化成516—528年。2022年运河报告仍按原决定暂缓。</p><p>{link('https://www.cqvip.com/journal/94762X/1000076712','1993原刊期次页')} · {link('https://github.com/mechgouki/luoyang-city/blob/'+commit+'/research/roads-r62/sources/road-source-audit.json','本批原件访问与读图审计')} · {link('https://github.com/mechgouki/luoyang-city/issues/47','道路研究记录 #47')}</p></section>
<section class="downloads" id="downloads"><h2>下载与离线阅读</h2><p>逐路CSV保留全部类别与证据字段，覆盖CSV说明原库条目的去向。JSON保存出处、输入位置和原图读点；SVG可放大、打印，ZIP可断网查表。</p><ul>{downloads}</ul></section></main>
<footer class="footer"><div class="wrap">研究 R6.2 / 网站 {VERSION} · 来源提交 {escape(commit[:12])}　{link('https://github.com/mechgouki/luoyang-city/issues/52','项目交接 #52')}　{link(prefix,'项目首页')}</div></footer></body></html>'''


def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: human(row.get(key)) for key in fields})


def input_paths(data):
    paths = {'research/roads-r62/catalog.json', 'research/roads-r62/sources/road-source-audit.json',
             'research/roads-r62/sources/yongxiang-arrows.json', 'research/roads-r6/roads.json',
             'research/prosperity-r5/sima-road.json', 'research/prosperity-v3/gate-plan.json',
             'data/entities.json'}
    def visit(value):
        if isinstance(value, dict):
            for key in ['source_path', 'path', 'file', 'local_path']:
                item = value.get(key)
                if isinstance(item, str) and (ROOT / item).is_file():
                    paths.add(item)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(data)
    return sorted(paths)


def build(site=ROOT / '_site'):
    info = load(site / 'build-info.json')
    release = load(site / 'release.json')
    dest = site / FOLDER
    dest.mkdir(exist_ok=True)
    data = load(DATA / 'catalog.json')
    data.update(source_commit=info['source_commit'], implementation_version=VERSION,
                new_historical_coordinates=0, accepted_target_bank_geometries=0,
                source_frames_registered_together=False)
    inputs = {path: sha(ROOT / path) for path in input_paths(data)}
    data['source_inputs_sha256'] = inputs
    svg = plate(data, (site / 'road-atlas/city-roads.svg').read_text())
    (dest / 'city-all-roads.svg').write_text(svg)
    dump(dest / 'records.json', data)
    fields = ['id','name','group','record_kind','entity_ids','legacy_ids','period','locatable_segment',
              'start','end','endpoint_status','gates','water_constraints','reported_metrics',
              'identity_notes','missing_evidence','source_refs','source_citations','geometry_refs','source_inputs']
    sources = lookup(data)
    rows = copy.deepcopy(data['records'])
    for row in rows:
        row['source_citations'] = [' · '.join(str(sources[ref].get(k,'')) for k in ['title','locator','url']).strip(' ·') for ref in row['source_refs']]
    write_csv(dest / 'records.csv', rows, fields)
    coverage_fields = list(dict.fromkeys(key for row in data['coverage'] for key in row))
    write_csv(dest / 'coverage.csv', data['coverage'], coverage_fields)
    for name in ['atlas.css','atlas.js']:
        shutil.copyfile(DATA / name, dest / name)
    (site / PAGE).write_text(make_page(data, svg, info['source_commit']))
    assets = [FOLDER + '/' + name for name in ['city-all-roads.svg','records.csv','records.json','coverage.csv','atlas.css','atlas.js']]
    old_page = site / 'luoyang-road-atlas.html'
    # Idempotent local rebuilding removes only our earlier exact, recorded entrance.
    old_meta = info.get(KEY)
    old_html = old_page.read_text()
    if old_meta:
        old_html = old_html.replace(old_meta['preservation']['entry_html'], '')
    entry = '<section id="all-roads-entry" class="wrap" style="padding-top:24px;padding-bottom:24px"><h2>全城道路总览已补齐</h2><p>宫路、坊街、文献道路、门道与桥道同批登记；原有21条主干道来源继续保留。</p><p><a href="./luoyang-all-roads.html">进入全城道路总览 →</a></p></section>'
    previous_hash = hashlib.sha256(old_html.encode()).hexdigest()
    assert old_html.count('</main>') == 1 and 'id="all-roads-entry"' not in old_html
    old_page.write_text(old_html.replace('</main>', '</main>' + entry))
    old = info['road_locations']
    protected = {p: sha(site / p) for p in set(old['files_sha256']) | {old['manifest'],old['bundle']}}
    study = dict(version=VERSION,research_version='R6.2',source_commit=info['source_commit'],
                 page=PAGE,manifest=MANIFEST,bundle=BUNDLE,download_files=list(DOWNLOADS),
                 counts=dict(records=len(data['records']),groups=dict(Counter(r['group'] for r in data['records'])),
                             coverage=len(data['coverage']),exclusions=len(data['exclusions'])),
                 source_inputs_sha256=inputs,files_sha256={p:sha(site/p) for p in assets},
                 preservation=dict(previous_page='luoyang-road-atlas.html',entry_id='all-roads-entry',
                     entry_html=entry,previous_page_sha256=previous_hash,protected_files_sha256=protected,
                     homepage='panorama-approved-v11',selection_number='07'))
    dump(site / MANIFEST, study)
    with ZipFile(site / BUNDLE, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('index.html', make_page(data, svg, info['source_commit'], offline=True))
        for path in [*assets,MANIFEST]:
            archive.write(site / path, path)
    info[KEY] = study
    release['extensions'] = sorted(set(release['extensions']) | {VERSION})
    release[KEY + '_version'] = VERSION
    release['current_milestone'] = '盛时 R6.2 · 全城道路、门道与桥道总览'
    dump(site / 'release.json', release)
    for path in [*assets,MANIFEST,BUNDLE,PAGE,'luoyang-road-atlas.html','release.json']:
        info['files_sha256'][path] = sha(site / path)
    dump(site / 'build-info.json', info)
    return study


if __name__ == '__main__':
    print(build()['counts'])
