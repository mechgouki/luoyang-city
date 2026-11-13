#!/usr/bin/env python3
"""Publish B7 catalog production histories without inferring map use or a CRS.

Run after the B6 build and before the final B7 release generator. All evidence
is already recorded in the reviewed JSON; this builder performs no networking.
An existing site/build-info.json is required to bind the publication identity.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import textwrap
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'research/dual-b7/source-continuity.json'
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
P = {'paper': '#f8f7f1', 'ink': '#263f37', 'green': '#326754',
     'line': '#ccd4c5', 'pale': '#edf1e7', 'ochre': '#f0e8d6'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_data(path=DATA):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_data(data):
    """Reject unsupported upgrades from catalog facts to original-map evidence."""
    for key in ('original_horizontal_datum', 'original_geographic_crs'):
        require(data[key] is None, 'No original-map datum or CRS is established')
    for key in ('project_registration_to_wgs84', 'ground_accuracy_assessed',
                'modern_dsm_modified', 'coordinate_assignment_performed',
                'new_historical_image_obtained'):
        require(data[key] is False, 'No geographic operation or new historical scan is authorized')
    require(data['approved_ground_control_points'] == [], 'No approved ground points')
    require(data['ancient_geographic_positions_added'] == data['ancient_channels_added'] == 0,
            'No ancient coordinates or channels may be added')
    require(data['source_assets'] == [], 'This batch has no newly reviewed historical image assets')
    records = {r['id']: r for r in data['records']}
    expected = {'zhengzhou-1942': ('YG821-2507', '000008299342'),
                'yanshi-1934': ('YG821-2519', '000008299355'),
                'sishui-1935': ('YG821-2516', '000008299352')}
    require(set(records) == set(expected) and len(data['records']) == 3, 'Three reviewed catalog records required')
    sources = {s['id']: s for s in data['sources']}
    for key, (call, bib) in expected.items():
        record = records[key]
        source = sources[record['source_id']]
        require((record['call_number'], record['bibliographic_id']) == (call, bib), 'Catalog identity changed')
        require((source['call_number'], source['bibliographic_id']) == (call, bib), 'Source identity changed')
        require(source['url'] == 'https://ndlsearch.ndl.go.jp/books/R100000002-I' + bib,
                'Official catalog URL must identify the reviewed record')
        require(re.fullmatch('[0-9a-f]{64}', source['response_sha256']) is not None, 'Response SHA required')
        require(source['historical_image_inspected'] is source['full_original_map_obtained'] is False,
                'Catalog response is not an inspected historical scan')
        require(record['note_basis'] == 'official_catalog_general_note_not_new_map_collar_inspection',
                'Production dates must remain catalog-note evidence')
        require(record['catalog_only'] is True and record['original_scan_seen_in_this_batch'] is False,
                'No original image was inspected for these three records')
        require(record['raw_scan_crop_xyxy'] is record['coordinates'] is None, 'No pixels or geographic points established')
        require(record['original_horizontal_datum'] is record['original_geographic_crs'] is None,
                'No original-map datum or CRS is established')
        require(record['approved_as_ground_control'] is record['actual_l500_source_match'] is record['actual_l531_source_match'] is False,
                'Period or institution match does not establish map use or a control point')
        require(record['unknowns'] and record['next_gate'], 'Unresolved evidence and next gate required')
    z, y, s = (records[k] for k in expected)
    require((z['photography_date'], z['survey_date'], z['plate_date'], z['publication_date_as_cataloged']) ==
            ('1942-08', '1942-11', None, '[1942]'), 'Zhengzhou photography, survey and inferred publication must remain distinct')
    require(z['publication_year_bracketed'] is True and z['status'] == 'period-match', 'Keep catalog brackets and candidate status')
    require(z['period_matches_l500_west_citation'] is True, 'Zhengzhou is a period candidate only')
    require((y['upstream_map_date'], y['upstream_map_scale_denominator'], y['plate_date'], y['publication_date_as_cataloged']) ==
            ('1926', 100000, '1934', '1934.4'), 'Yanshi parent map, plate and publication are distinct')
    require((s['upstream_map_date'], s['upstream_map_scale_denominator'], s['plate_date'], s['publication_date_as_cataloged']) ==
            ('1931', 50000, '1934', '1935.1'), 'Sishui parent map, plate and publication are distinct')
    for record in (y, s):
        require(record['photography_date'] is record['survey_date'] is None, 'Plate making is not a new survey')
        require(record['status'] == 'earlier' and record['period_matches_l500_west_citation'] is False,
                'Earlier editions cannot become the 1942–44 edition')
    relations = {r['id']: r for r in data['baseline_relations']}
    require(relations['L500-east']['japanese_source_listed'] is False, 'Do not add Japanese sources to the east collar')
    require(relations['L531-chinese-base']['observed_printed_year'] == 1946 and
            relations['L531-chinese-base']['compiled_year'] == 1945, 'Keep observed printing separate from compilation')
    counts = data['review_counts']
    require(counts == {'catalog_records_reviewed': 3, 'period_matched_catalog_candidates': 1,
                      'earlier_impressions': 2, 'upstream_chinese_map_mentions': 2,
                      'historical_scans_added': 0, 'exact_l500_source_matches': 0,
                      'exact_l531_source_matches': 0, 'approved_ground_control_points': 0},
            'Review counts do not match the reviewed evidence')


def node(parent, name, **attrs):
    return ET.SubElement(parent, '{' + NS + '}' + name,
                         {k.replace('_', '-'): str(v) for k, v in attrs.items()})


def rect(parent, x, y, width, height, fill, **attrs):
    return node(parent, 'rect', x=x, y=y, width=width, height=height, fill=fill, **attrs)


def label(parent, x, y, content, size=28, fill=None, weight=400):
    node(parent, 'text', x=x, y=y, font_size=size, fill=fill or P['ink'], font_weight=weight).text = str(content)


def wrapped(parent, x, y, content, units=30, size=27, leading=42, fill=None):
    lines, current, used = [], '', 0.0
    for char in content:
        width = 1.0 if unicodedata.east_asian_width(char) in {'W', 'F'} else .56
        closing = char in '。，；：？！、）】》」』.,;:?!'
        if char == '\n' or (used + width > units and not closing):
            lines.append(current); current = ''; used = 0.0
            if char == '\n':
                continue
        current += char; used += width
    if current:
        lines.append(current)
    for i, line in enumerate(lines):
        label(parent, x, y + i * leading, line, size, fill)
    return y + len(lines) * leading


def svg_base(title, subtitle):
    root = ET.Element('{' + NS + '}svg', {'width': '2200', 'height': '1560', 'viewBox': '0 0 2200 1560', 'role': 'img'})
    node(root, 'title').text = title
    node(root, 'desc').text = subtitle
    rect(root, 0, 0, 2200, 1560, P['paper'])
    group = node(root, 'g', font_family='Noto Sans CJK SC, sans-serif')
    label(group, 70, 76, '北魏洛阳研究 / B7 单幅目录与来源连续性', 27, P['green'])
    label(group, 70, 147, title, 48, weight=700)
    label(group, 70, 205, subtitle, 28)
    return root, group


def write_svg(path, root):
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def edition_plate(data, pub):
    root, g = svg_base('同系列的三幅图，年份与制作路径不同', '以下来自NDL单幅目录一般注记；本批未取得三幅原图，不能表述为已亲见图边。')
    columns = [70, 470, 810, 1120, 1430, 1740, 2130]
    headers = ['单幅目录／馆号', '中国底图', '摄影', '测量', '制版', '出版字段']
    rect(g, 70, 262, 2060, 84, P['green'], rx=10)
    for i, title in enumerate(headers):
        label(g, columns[i] + 24, 316, title, 28, '#ffffff', 700)
    rows = [
        ('郑州／開封11號', 'YG821-2507', '时期相符候选', [('目录未记', ''), ('1942-08', '昭和17年8月'), ('1942-11', '昭和17年11月'), ('目录未记', ''), ('[1942]', '保留馆方方括号')]),
        ('偃师／開封21號', 'YG821-2519', '目录1934版次', [('1926', '1:100000'), ('目录未记', ''), ('目录未记', ''), ('1934', '昭和9年製版'), ('1934.4', '目录记载')]),
        ('汜水／開封16號', 'YG821-2516', '目录1935版次', [('1931', '1:50000'), ('目录未记', ''), ('目录未记', ''), ('1934', '昭和9年製版'), ('1935.1', '目录记载')]),
    ]
    for row_index, (title, call, status, cells) in enumerate(rows):
        y = 346 + row_index * 225
        rect(g, 70, y, 2060, 225, '#ffffff' if row_index % 2 == 0 else P['pale'], stroke=P['line'])
        label(g, 94, y + 58, title, 30, weight=700)
        label(g, 94, y + 112, call, 27)
        label(g, 94, y + 170, status, 26, P['green'])
        for i, (value, note) in enumerate(cells, 1):
            node(g, 'line', x1=columns[i], x2=columns[i], y1=y, y2=y + 225, stroke=P['line'])
            label(g, columns[i] + 24, y + 88, value, 33, weight=700 if value != '目录未记' else 400)
            if note:
                label(g, columns[i] + 24, y + 146, note, 24)
    rect(g, 70, 1053, 1008, 255, P['ochre'], rx=12)
    label(g, 100, 1102, '日期不能相互替代', 31, weight=700)
    wrapped(g, 100, 1155, '摄影是拍摄过程；测量是目录所记测量。制版可能依据旧图，不能自动解释为新测。出版是本幅书志日期。', 33, 28, 43)
    rect(g, 1102, 1053, 1028, 255, '#ffffff', stroke=P['line'], rx=12)
    label(g, 1132, 1102, '目录未记，不等于该步骤没有发生', 31, weight=700)
    wrapped(g, 1132, 1155, '郑州[1942]保留目录推定形式；早期两幅的摄影／测量字段空缺。实际内容、边界与修订须取得原图再核。', 34, 28, 43)
    rect(g, 70, 1340, 2060, 160, P['pale'], rx=12)
    label(g, 100, 1394, '新增单幅目录 3 / 本批取得历史扫描 0 / 已证实L500或L531实际用图关系 0', 31, weight=700)
    label(g, 100, 1442, '来源：国立国会图书馆，YG821-2507、YG821-2519、YG821-2516；书目ID与URL见随附JSON。', 25)
    label(g, 100, 1479, '原纸图水平基准仍未知；没有新增地面控制点、古址坐标或古河道。', 25)
    write_svg(pub / 'edition-summary.svg', root)


def continuity_plate(data, pub):
    root, g = svg_base('具体制作链已可追查，实际用图关系仍须另证', '左侧只连目录一般注记明说的制作关系；右侧逐项审核，不把时期或尺度相容画成已证来源链。')
    specs = [
        ('郑州／開封11號 · YG821-2507', [('1942年8月', '摄影', '目录记空中摄影'), ('1942年11月', '测量', '目录记航空摄影测量'), ('[1942]', '出版', '馆方推定年份')],
         '时期与机构相符，仍是目录候选', '目录列郑州及周边县，不能按年份塞入西幅NI49-7来源链。东幅NI49-8编图栏未列日本图源。', '还缺原图边界、印次及AMS逐幅引用记录。'),
        ('偃师／開封21號 · YG821-2519', [('1926年', '河南十万分一底图', '國民革命軍總司令部\n參謀處'), ('1934年', '制版', '目录未载新测日期'), ('1934年4月', '出版', '本条目录版次')],
         '目录版次早于1942—44', '1934制版不等于1934新测；这条1934目录不能直接充作L500所引印本。', '尚未核是否有后续修订／翻印；不提前排除。'),
        ('汜水／開封16號 · YG821-2516', [('1931年', '河南五万分一底图', '參謀本部\n陸地測量總局'), ('1934年', '制版', '底图年与制版年分列'), ('1935年1月', '出版', '本条目录版次')],
         '取得中国五万分一底图线索', '1931与1:50000符合L531所引时段和尺度，但尚未证为同一底图、同一编图机构或同一图幅。', '需核中国底图图号与AMS清单，不合并两条链。'),
    ]
    for i, (title, stages, verdict, reasoning, gate) in enumerate(specs):
        y = 250 + i * 355
        rect(g, 70, y, 1320, 325, '#ffffff', stroke=P['line'], rx=12)
        label(g, 100, y + 49, title, 31, weight=700)
        for j, (date, meaning, note) in enumerate(stages):
            x = 100 + j * 430
            rect(g, x, y + 78, 400, 216, P['pale'], rx=9)
            label(g, x + 22, y + 124, date, 32, weight=700)
            label(g, x + 22, y + 170, meaning, 27, P['green'], 700)
            wrapped(g, x + 22, y + 216, note, 13, 25, 35)
            if j < 2:
                label(g, x + 402, y + 184, '→', 28, P['green'], 700)
        rect(g, 1420, y, 710, 325, P['ochre'] if i == 0 else '#ffffff', stroke=P['line'], rx=12)
        label(g, 1450, y + 49, verdict, 29, weight=700)
        wrapped(g, 1450, y + 102, reasoning, 23, 27, 39)
        wrapped(g, 1450, y + 243, gate, 24, 26, 38, P['green'])
    rect(g, 70, 1340, 2060, 160, P['pale'], rx=12)
    label(g, 100, 1394, '审核结果：实际L500／L531用图匹配均为0；获准地面控制点0；完整水平基准仍未知。', 30, weight=700)
    label(g, 100, 1442, '这三条记录是目录证据；B6已见L531的1946印次／1945编图继续分别保留。本批没有新历史扫描。', 25)
    label(g, 100, 1479, '来源：NDL单件目录一般注记；L500／L531边栏对照沿用B5、B6已核材料，详见随附JSON。', 25)
    write_svg(pub / 'continuity-summary.svg', root)


def page_html():
    return '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>B7 外邦图单幅目录与来源连续性审核｜洛阳城复原</title>
<style>
:root{color-scheme:light;--ink:#263f37;--paper:#f8f7f1;--green:#326754;--line:#ccd4c5}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.75 system-ui,"Noto Sans CJK SC",sans-serif}main{max-width:1420px;margin:auto;padding:28px 24px 64px}h1,h2,h3,p{margin-top:0}h1{font-size:clamp(28px,4vw,46px);line-height:1.3;margin-bottom:18px}h2{font-size:26px}h3{font-size:20px;margin-bottom:12px}a{color:#245d48;text-underline-offset:3px}nav,.actions{display:flex;flex-wrap:wrap;gap:12px 22px;margin-bottom:24px}.eyebrow{font-weight:700;color:var(--green);letter-spacing:.04em}.intro{max-width:1020px}.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:26px;min-width:0;margin-top:22px}.meaning{background:#edf1e7;border-left:4px solid var(--green);padding:16px 20px;margin:18px 0}.meaning strong{display:block;margin-bottom:7px}.small{font-size:14px;color:#516258}.controls{display:grid;grid-template-columns:1.5fr 1fr 1fr;gap:18px;margin:22px 0}label{font-weight:700;display:block}select,button{font:inherit;color:var(--ink);border:1px solid #8a9c8c;border-radius:7px;background:#fff;min-height:46px;padding:8px 12px;max-width:100%}select{display:block;width:100%;margin-top:7px}button{cursor:pointer}button:hover,button:focus-visible{background:#edf1e7}button:focus-visible,a:focus-visible,select:focus-visible{outline:3px solid #a8bd77;outline-offset:3px}.status{display:inline-block;background:#edf1e7;padding:5px 12px;border-radius:5px;font-size:15px;margin-bottom:16px}.two-column{display:grid;grid-template-columns:1.3fr 1fr;gap:24px}.date-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}.date-cell{background:#f6f7f0;border:1px solid var(--line);padding:15px 12px;border-radius:7px}.date-cell strong{display:block;font-size:23px;margin-top:8px;overflow-wrap:anywhere}.date-cell span{font-size:14px}.label-value{display:grid;grid-template-columns:7em minmax(0,1fr);gap:8px 16px;margin:16px 0}.label-value dt{font-weight:700}.label-value dd{margin:0;overflow-wrap:anywhere}.lineage-list{padding-left:25px}.lineage-list li{padding:4px 0 13px}.lineage-list strong{display:block}.plate-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.plate-grid img{width:100%;height:auto;border:1px solid var(--line);display:block}.plate-grid figure{margin:0}.plate-grid figcaption{font-size:14px;margin-top:8px}code{font-size:13px;overflow-wrap:anywhere;word-break:break-all}blockquote{margin:15px 0;padding:12px 18px;background:#f8f5eb;border-left:3px solid #b6a67d;overflow-wrap:anywhere}.gate-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.gate{border-top:1px solid var(--line);padding-top:16px}.gate p{margin-bottom:0}ul{padding-left:23px}li{margin:7px 0}[hidden]{display:none!important}#continuity-error{background:#fff0dd;padding:18px}footer{margin-top:35px;font-size:14px}
@media(max-width:780px){main{padding:22px 16px 44px}.controls,.two-column,.plate-grid,.gate-grid{grid-template-columns:1fr}.card{padding:20px}.date-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.label-value{grid-template-columns:1fr;gap:3px}.label-value dd{margin-bottom:10px}nav,.actions{gap:10px 16px}.date-cell strong{font-size:22px}}
</style></head><body><main>
<nav aria-label="研究导航"><a href="./index.html">洛阳研究首页</a><a href="./dual-luonan.html">洛南馆里 B7</a><a href="./ground-review.html">B6 地物与原图边栏</a><a href="./historical-datum.html">B5 水平基准调查</a></nav>
<header><p class="eyebrow">历史地形研究 · B7</p><h1>外邦图单幅目录与来源连续性审核</h1><p class="intro">三个馆号带来不同的制作路径：郑州的1942年摄影与测量，偃师的1926年底图与1934年制版，汜水的1931年五万分一底图。本页逐项显示目录证据、相容条件和仍未证明的部分。</p><div class="meaning"><strong>本批新增单幅目录3条，历史扫描0幅，已确认实际用图关系0条</strong>制作日期来自NDL一般注记；本批未取得这三幅原图。原纸图完整水平基准未知，未配准到WGS84，获准地面控制点仍为0。</div></header>
<p id="continuity-error" role="alert" hidden></p>
<section class="card" aria-labelledby="review-heading"><h2 id="review-heading">逐幅核读</h2>
<div class="controls"><label>单幅记录<select id="continuity-record" aria-label="单幅记录"></select></label><label>目录筛选<select id="continuity-filter"><option value="all">全部3条</option><option value="period-match">时期相符候选</option><option value="earlier">早于目标时段的版次</option></select></label><label>阅读方式<select id="continuity-view"><option value="timeline">制作年代表</option><option value="lineage">来源关系审核</option></select></label></div>
<p class="small" id="continuity-count" aria-live="polite"></p><div id="continuity-reading" aria-live="polite"></div>
<div class="actions"><button id="continuity-source-toggle" type="button" aria-expanded="false" aria-controls="continuity-source-detail">展开来源详情</button><a id="continuity-source-link" href="#" target="_blank" rel="noopener">查看官方单件目录 ↗</a></div><section id="continuity-source-detail" hidden></section></section>
<section class="card"><h2>两张审核图板</h2><div class="plate-grid"><figure><a href="./source-continuity/edition-summary.svg" target="_blank"><img src="./source-continuity/edition-summary.svg" alt="三幅单件目录的底图、摄影、测量、制版与出版日期对照" loading="lazy"></a><figcaption>五种日期分别记录；空缺只表示目录未记。</figcaption></figure><figure><a href="./source-continuity/continuity-summary.svg" target="_blank"><img src="./source-continuity/continuity-summary.svg" alt="三条目录制作关系及尚未证实的AMS实际用图关系" loading="lazy"></a><figcaption>左侧为目录明载关系，右侧为逐项审核结论。</figcaption></figure></div></section>
<section class="card"><h2>下一步需要什么证据</h2><div id="continuity-gates" class="gate-grid"></div><h3 style="margin-top:26px">本批边界</h3><ul id="continuity-limits"></ul></section>
<section class="card"><h2>下载与复核</h2><div class="actions"><a id="continuity-download" href="./downloads/luoyang-source-continuity-b7.zip">下载 B7 来源连续性审核包 ZIP</a><a href="./source-continuity/metadata.json">结构化证据 JSON</a><a href="./source-continuity/research.md">完整研究说明</a></div><p class="small">审核包含单件目录URL、馆号、书目ID、引用字段、响应SHA-256与源码。本批没有新原图裁片，不含地理坐标或配准文件。</p><p id="continuity-build" class="small"></p></section>
<footer>本页显示研究进度及其限制。来源连续性、完整测量基准与地面控制点准入分别审核。</footer>
</main><script src="./source-continuity/continuity.js"></script></body></html>'''


def build(site):
    site = Path(site)
    data = copy.deepcopy(read_data())
    validate_data(data)
    build_info = site / 'build-info.json'
    identity = read_data(build_info)
    require(isinstance(identity.get('source_commit'), str) and bool(identity['source_commit']),
            'Existing site source_commit is required')
    data['source_commit'] = identity['source_commit']
    data['research_input_sha256'] = sha(DATA)
    data['named_records'] = len(data['records'])
    data['approved_control_points'] = 0
    pub = site / 'source-continuity'
    pub.mkdir(parents=True, exist_ok=True)
    (pub / 'metadata.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(ROOT / 'web/source-continuity-b7.js', pub / 'continuity.js')
    shutil.copyfile(ROOT / 'docs/source-continuity-b7-research.md', pub / 'research.md')
    (site / 'source-continuity.html').write_text(page_html(), encoding='utf-8')
    edition_plate(data, pub)
    continuity_plate(data, pub)
    (pub / 'README.txt').write_text('B7 外邦图单幅目录与来源连续性审核\n\n' + data['summary'] + '\n\n' + '\n'.join(data['limitations']) + '\n\n本批原图影像与裁片新增数为0。目录响应SHA只识别本次取得的字节，不保证网站内容恒定。\n', encoding='utf-8')
    identity['source_continuity_b7'] = {
        'source_commit': data['source_commit'],
        'review_counts': copy.deepcopy(data['review_counts']),
        'metadata': 'source-continuity/metadata.json',
        'metadata_sha256': sha(pub / 'metadata.json'),
        'original_horizontal_datum': None,
        'project_registration_to_wgs84': False,
        'approved_control_points': 0,
    }
    build_info.write_text(json.dumps(identity, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    downloads = site / 'downloads'
    downloads.mkdir(exist_ok=True)
    with zipfile.ZipFile(downloads / 'luoyang-source-continuity-b7.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(pub.rglob('*')):
            if path.is_file():
                archive.write(path, 'source-continuity/' + path.relative_to(pub).as_posix())
        for path in [DATA, ROOT / 'docs/source-continuity-b7-research.md', Path(__file__), ROOT / 'web/source-continuity-b7.js']:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.write(site / 'source-continuity.html', 'source-continuity.html')
        archive.writestr('build-info.json', json.dumps({'source_commit': data['source_commit'],
                         'source_continuity_b7': identity['source_continuity_b7']}, ensure_ascii=False, indent=2) + '\n')
        archive.writestr('REPRODUCE.txt', textwrap.dedent('''\
            B7 catalog production and source continuity review
            Python 3.11+ standard library only. No network or image inputs required.
            In the extracted archive: python tools/source_continuity_b7.py --site .
            The packaged build-info.json supplies the reviewed source_commit.
            Serve the archive directory by HTTP and open /source-continuity.html.
            Three official catalog records are evidence, not inspected original maps.
            Catalog response SHA-256 values identify one retrieval, not immutable URLs.
            No original-map CRS, map-use match, geographic coordinates or control points.
            Cross-topic navigation requires the full project website.
            '''))
    print('B7 source continuity: 3 catalog records, 1 period candidate, 2 earlier editions, 2 plates; 0 actual-source matches or ground points.')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=ROOT / '_site')
    args = parser.parse_args()
    build(args.site)


if __name__ == '__main__':
    main()
