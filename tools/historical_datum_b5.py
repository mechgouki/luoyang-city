#!/usr/bin/env python3
"""Publish the B5 datum-source investigation without assigning a map datum.

Reads reviewed research JSON and hash-locked UT scans. No network, coordinate
conversion, ground point extraction or edits to B4 are performed. Run after B4
and before the final release generator, which refreshes the build manifest.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import shutil
import textwrap
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'research/dual-b5/historical-datum.json'
NS = 'http://www.w3.org/2000/svg'
XL = 'http://www.w3.org/1999/xlink'
ET.register_namespace('', NS)
ET.register_namespace('xlink', XL)
PALETTE = {'paper': '#f8f7f1', 'ink': '#263f37', 'green': '#326754',
           'line': '#ccd4c5', 'pale': '#edf1e7', 'ochre': '#f0e8d6'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_data(path=DATA):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate_data(data):
    """Fail closed if a research distinction required by this release is lost."""
    assert data['original_horizontal_datum'] is None
    assert data['original_geographic_crs'] is None
    assert data['project_registration_to_wgs84'] is False
    assert data['ground_accuracy_assessed'] is False
    assert data['ancient_geographic_positions_added'] == 0
    assert data['ancient_channels_added'] == 0
    assert data['modern_dsm_modified'] is False
    assert data['approved_ground_control_points'] == []
    assert data['english_excerpt']['word_count'] == len(data['english_excerpt']['text'].split()) <= 15
    assert {s['id'] for s in data['sheets']} == {'NI49-7', 'NI49-8'}
    for sheet in data['sheets']:
        paper = sheet['paper_map']; digital = sheet['digitized_product']; b4 = sheet['b4_internal_calibration']
        assert paper['horizontal_datum'] is None and paper['geographic_crs'] is None
        assert paper['ellipsoid_as_printed'] == 'International Spheroid'
        assert paper['grid_zone_designation_as_printed'] == '49S'
        assert digital['assignment_role'] == 'post_publication_digitization_working_definition'
        assert digital['original_paper_datum_identified'] is False
        assert digital['assigned_horizontal_datum'] == 'D_WGS_1984'
        assert digital['registration_control_count'] == 4
        assert digital['independent_ground_check_count_reported'] is None
        assert b4['fit_count'] == 8 and b4['heldout_count'] == 5
        assert b4['geographic_crs'] is None and b4['ground_accuracy_assessed'] is False
        assert len(digital['metadata_sha256']) == 64
        assert digital['repository_commit'] in digital['metadata_url']
        width, height = sheet['source_size_px']
        ids = set()
        for crop in sheet['crops']:
            assert crop['id'] not in ids
            ids.add(crop['id'])
            x0, y0, x1, y1 = crop['raw_scan_crop_xyxy']
            assert all(isinstance(v, int) for v in (x0, y0, x1, y1))
            assert 0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height
    for candidate in data['candidate_review_queue']:
        assert candidate['record_kind'] == 'feature_type_screening'
        assert candidate['physical_feature_identified'] is False
        assert candidate['approved_as_ground_control'] is False
        assert candidate['coordinates'] is None
        assert candidate['status'] in {'pending', 'excluded'}


def verified_images(data, cache):
    """Verify both originals before writing any publication assets."""
    images = {}
    for sheet in data['sheets']:
        path = Path(cache) / sheet['source_file']
        if not path.is_file():
            raise FileNotFoundError(f'Required reviewed scan is missing; run terrain_v30.py first: {path}')
        if sha(path) != sheet['source_sha256']:
            raise ValueError(f'Source scan SHA-256 mismatch; margin selections require review: {path}')
        with Image.open(path) as source:
            if list(source.size) != sheet['source_size_px']:
                raise ValueError(f'Source scan dimensions changed: {path}')
            images[sheet['id']] = source.convert('RGB')
    return images


def node(parent, name, **attrs):
    return ET.SubElement(parent, '{' + NS + '}' + name, {k.replace('_', '-'): str(v) for k, v in attrs.items()})


def rectangle(parent, x, y, width, height, fill, **attrs):
    return node(parent, 'rect', x=x, y=y, width=width, height=height, fill=fill, **attrs)


def label(parent, x, y, content, size=28, fill=None, weight=400):
    el = node(parent, 'text', x=x, y=y, font_size=size, fill=fill or PALETTE['ink'], font_weight=weight)
    el.text = str(content)
    return el


def wrapped(parent, x, y, content, units=40, size=27, leading=42, fill=None):
    """Wrap by visual character width so CJK text remains inside fixed plates."""
    lines, current, used = [], '', 0.0
    for char in content:
        width = 1.0 if unicodedata.east_asian_width(char) in {'W', 'F'} else .56
        if char == '\n' or used + width > units:
            lines.append(current); current = ''; used = 0.0
            if char == '\n':
                continue
        current += char; used += width
    if current:
        lines.append(current)
    for i, line in enumerate(lines):
        label(parent, x, y + i * leading, line, size=size, fill=fill)
    return y + len(lines) * leading


def svg_base(title, subtitle):
    root = ET.Element('{' + NS + '}svg', {'width': '2200', 'height': '1560', 'viewBox': '0 0 2200 1560', 'role': 'img'})
    node(root, 'title').text = title
    rectangle(root, 0, 0, 2200, 1560, PALETTE['paper'])
    group = node(root, 'g', font_family='Noto Sans CJK SC, sans-serif')
    label(group, 70, 76, '北魏洛阳研究 / B5 历史地图基准调查', 27, PALETTE['green'])
    label(group, 70, 147, title, 48, weight=700)
    label(group, 70, 205, subtitle, 28)
    return root, group


def embedded_image(parent, path, x, y, width, height):
    payload = base64.b64encode(Path(path).read_bytes()).decode('ascii')
    el = node(parent, 'image', x=x, y=y, width=width, height=height, preserveAspectRatio='xMidYMid meet')
    el.set('{' + XL + '}href', 'data:image/png;base64,' + payload)


def write_svg(path, root):
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def source_plate(data, pub):
    root, group = svg_base('原纸图的说明，与2005年数字化的选择', '边栏证据已核读；原馆过程记录已查明；原纸图完整水平基准仍未识别。')
    for index, sheet in enumerate(data['sheets']):
        y = 260 + index * 530
        paper = sheet['paper_map']; digital = sheet['digitized_product']
        crops = {c['id']: c for c in sheet['crops']}
        rectangle(group, 70, y, 990, 495, '#ffffff', stroke=PALETTE['line'], rx=12)
        rectangle(group, 1090, y, 1040, 495, PALETTE['pale'], stroke=PALETTE['line'], rx=12)
        label(group, 100, y + 51, sheet['id'] + ' · ' + ('洛阳' if index == 0 else '郑县') + ' / 原纸图', 33, weight=700)
        embedded_image(group, pub / crops['projection-grid']['image'], 100, y + 70, 930, 145)
        label(group, 100, y + 251, '横轴墨卡托 · UTM第49带 · International Spheroid', 26)
        embedded_image(group, pub / crops['printing']['image'], 100, y + 280, 930, 84)
        label(group, 100, y + 400, '编图1955 / 印刷' + paper['printed_date'] + ' / 原图1:250,000', 27)
        label(group, 100, y + 452, '椭球已知，原纸图 datum 仍未识别', 30, PALETTE['green'], 700)
        label(group, 1120, y + 51, '同版同印刷年月 / 哈佛数字产品', 32, weight=700)
        wrapped(group, 1120, y + 110, '2005年2月处理步骤说明：原系列未公布关联水平基准；为全系列统一，数字化时赋予WGS_1984。', units=33, size=27, leading=43)
        label(group, 1120, y + 248, '4组角点附近印刷UTM坐标 / ArcMap 9.0', 27)
        label(group, 1120, y + 299, '所赋基准：D_WGS_1984（数字产品工作定义）', 27, PALETTE['green'], 700)
        label(group, 1120, y + 347, '原馆XML：procstep[2]/procdesc，第' + str(digital['process_location']['line_start']) + '—' + str(digital['process_location']['line_end']) + '行', 24)
        label(group, 1120, y + 397, '不同扫描影像，不移植像素变换或world file', 27)
        label(group, 1120, y + 451, '地面检查：未报告；本项目尚无获准地面点', 26)
    rectangle(group, 70, 1340, 2060, 160, PALETTE['ochre'], rx=12)
    label(group, 100, 1390, '原馆过程记录：' + data['english_excerpt']['text'], 27)
    label(group, 100, 1439, '出处：Harvard Map Collection / 两幅固定版本FGDC XML；摘句只说明机构记录，未补出AMS原始测量基准。', 25)
    label(group, 100, 1480, '文件身份、原图裁片像素框、固定commit及SHA-256见随附metadata.json。', 23)
    write_svg(pub / 'source-summary.svg', root)


def review_plate(data, pub):
    root, group = svg_base('残差的适用范围，与地面点的准入门槛', '不同影像、不同控制方案、不同统计对象；数值不用于地面精度排名。')
    x = [70, 425, 990, 1545]
    widths = [355, 565, 555, 585]
    headings = ['图幅', '哈佛：4角格网转换', 'B4：8点图内拟合', 'B4：5点同图留出']
    for col in range(4):
        rectangle(group, x[col], 265, widths[col], 75, PALETTE['green'])
        label(group, x[col] + 20, 313, headings[col], 28, '#ffffff', 700)
    for i, sheet in enumerate(data['sheets']):
        y = 340 + i * 116; digital = sheet['digitized_product']; b4 = sheet['b4_internal_calibration']
        values = [sheet['id'], f'约 {digital["rms_m"]:.1f} 米', f'约 {b4["fit_rms_printed_grid_m"]:.1f} 印刷网格米', f'约 {b4["heldout_rms_printed_grid_m"]:.1f} 印刷网格米']
        notes = ['不同馆藏扫描', '转换残差；无地面检查', '参与拟合的8个蓝网交点', f'{b4["heldout_rms_scan_px"]:.1f}扫描像素；未参加拟合']
        for col in range(4):
            rectangle(group, x[col], y, widths[col], 116, '#ffffff', stroke=PALETTE['line'])
            label(group, x[col] + 20, y + 47, values[col], 31, weight=700)
            label(group, x[col] + 20, y + 88, notes[col], 24)
    rectangle(group, 70, 610, 2060, 130, PALETTE['ochre'], rx=10)
    label(group, 95, 658, '所有列都不是独立地面精度。哈佛RMS与B4留出RMS不能互换，不能据此计算精度提高百分比。', 29)
    label(group, 95, 706, '本批没有转换原纸图坐标，没有修改现代DSM，没有新增古址经纬度或古河道。', 27)
    label(group, 70, 807, '地物类型审核队列 / 具体已确认实体 0 / 获准地面控制点 0', 33, weight=700)
    row_y = 850
    for record in data['candidate_review_queue']:
        is_pending = record['status'] == 'pending'
        rectangle(group, 70, row_y, 2060, 76, '#ffffff', stroke=PALETTE['line'])
        label(group, 90, row_y + 48, record['status_label'], 27, PALETTE['green'] if is_pending else '#8b6235', 700)
        label(group, 280, row_y + 48, record['title'], 27)
        short = {'stable-rock': '须辨认原图与现代资料中的同一明确点', 'surviving-base': '须证明原址连续及符号含义一致',
                 'bridge-abutment': '须排除重建、迁位与引道改线', 'mobile-water': '先排除河道移动；固定岩岸需另行取证',
                 'label-centre': '文字排布和概略中心不构成测量点'}[record['id']]
        label(group, 1110, row_y + 48, short, 27)
        row_y += 85
    rectangle(group, 70, 1320, 2060, 180, PALETTE['pale'], rx=12)
    label(group, 95, 1370, '下一步：查原始大地测量依据 → 确认跨年代同一实体 → 预留独立地面检查 → 限定用途验证', 28, weight=700)
    wrapped(group, 95, 1425, '这些是待查类型和排除规则，不是已在两幅图中找到的具名地面点。候选获准前不附坐标；即使现代配准通过，也仍须另做古代水系与遗址证据研究。', units=72, size=27, leading=43)
    write_svg(pub / 'review-summary.svg', root)


def page_html():
    return '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>洛阳历史图幅 · 原纸图与数字化的基准调查 B5</title>
<style>
:root{color-scheme:light;--ink:#263f37;--green:#326754;--paper:#f8f7f1;--line:#ccd4c5;--pale:#edf1e7}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.75 system-ui,"Noto Sans CJK SC",sans-serif}a{color:#24644a;overflow-wrap:anywhere}button,select{font:inherit;color:inherit}button{cursor:pointer}header{padding:25px 4vw;background:var(--pale);border-bottom:1px solid var(--line)}nav{display:flex;flex-wrap:wrap;gap:17px;font-size:14px}.kicker{font-size:12px;letter-spacing:.12em;color:#61735f}h1{font-size:clamp(25px,3.2vw,42px);line-height:1.35;margin:20px 0 14px}h2{font-size:23px;line-height:1.4;margin:0 0 15px}h3{font-size:18px;margin:0 0 10px}p{margin:10px 0}.lede{max-width:1040px}main{max-width:1660px;margin:auto;padding:28px 3.8vw}.controls{display:flex;flex-wrap:wrap;gap:9px;align-items:center;margin-bottom:22px}.controls button,.download{border:1px solid #afc0ac;background:white;padding:8px 15px;border-radius:6px}.controls button[aria-pressed="true"]{background:var(--green);color:#fff}.spacer{flex:1}.status{display:inline-block;padding:4px 10px;border-radius:99px;background:#e2e8d8;font-size:12px;margin:6px 6px 0 0}.pair{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:22px}.panel,.section{background:#fff;border:1px solid var(--line);border-radius:10px;padding:24px;min-width:0}.panel p,.section p{overflow-wrap:anywhere}.section{margin-top:24px}.panel.digital{background:#f2f5ec}label{display:block;margin:12px 0 6px}select{width:100%;max-width:100%;padding:10px;border:1px solid #b7c5b0;border-radius:5px;background:#fff}.crop-box{background:#f6f4ed;border:1px solid #d1d6c9;margin:16px 0 10px;min-height:150px;display:flex;align-items:center;justify-content:center}.crop-box a{display:block;width:100%}.crop-box img{display:block;max-width:100%;width:100%;height:auto;max-height:450px;object-fit:contain}.small{font-size:13px;color:#5d6e62}.meaning{border-left:4px solid #b8945b;background:#f3ecdd;padding:15px 18px;margin:18px 0}.meaning strong{display:block}.label-value{display:grid;grid-template-columns:120px minmax(0,1fr);gap:8px 15px;margin:20px 0}.label-value dt{color:#657666}.label-value dd{margin:0;overflow-wrap:anywhere}.quote{border-left:4px solid var(--green);padding:12px 18px;background:white;margin:17px 0;font-size:17px;overflow-wrap:anywhere}.quote p{margin:0}.quote .small{margin-top:8px}details{margin-top:18px;border-top:1px solid var(--line);padding-top:14px}summary{font-weight:600;cursor:pointer}code{font-size:12px;overflow-wrap:anywhere;word-break:break-all}.metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px;margin:20px 0}.metric{padding:19px;background:var(--pale);border:1px solid var(--line);border-radius:7px}.metric strong{display:block;font-size:27px;line-height:1.5}.metric .small{margin:8px 0 0}.candidate-head{display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap}.candidate-head select{width:240px}.candidate-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:20px}.candidate{padding:20px;border:1px solid var(--line);border-radius:7px}.candidate .status{margin-bottom:12px}.empty{grid-column:1/-1;padding:24px;background:var(--pale);border-radius:7px}.gates{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.gate{border-left:3px solid var(--green);padding-left:17px}.sources{display:flex;flex-wrap:wrap;gap:12px 22px;margin-top:18px}.error{color:#a22;font-weight:700}footer{padding:20px 4vw 35px;border-top:1px solid var(--line);font-size:13px;color:#60715f}@media(max-width:900px){.pair{grid-template-columns:1fr}.metrics{grid-template-columns:1fr}.candidate-list,.gates{grid-template-columns:1fr}.panel,.section{padding:20px}}@media(max-width:480px){main{padding:20px 4vw}.panel,.section{padding:17px}.label-value{grid-template-columns:95px minmax(0,1fr);font-size:14px}.controls .spacer{display:none}.controls{align-items:stretch}.download{width:100%;text-align:center}.candidate-head select{width:100%}h2{font-size:21px}.quote{padding:10px 13px}.metric strong{font-size:25px}}
</style></head><body>
<header><nav><a href="./">文献母图</a><a href="./dual-west-roads.html">城西道路 B5</a><a href="./historical-frame.html">印刷格网校准 B4</a><a href="./v3.0.html">现代地形</a></nav><p class="kicker">B5 / 原图、数字化与基准调查</p><h1>2005年赋予的 WGS84，来自数字化的选择</h1><p class="lede">哈佛原馆过程记录明确说明：AMS未随这个系列公布关联水平基准，数字化时统一采用WGS_1984。现在可以追溯这项处理决定；原纸图的完整水平基准仍未识别。</p><p><span class="status">两幅真实原图边栏</span><span class="status">原馆固定版本XML</span><span class="status">获准地面控制点 0</span></p></header>
<main><p id="datum-error" class="error" hidden></p><section class="controls" aria-label="选择历史图幅"><button data-datum-sheet="NI49-7" aria-pressed="true">洛阳 NI49-7</button><button data-datum-sheet="NI49-8" aria-pressed="false">郑县 NI49-8</button><span class="spacer"></span><a id="datum-download" class="download" href="./downloads/luoyang-historical-datum-b5.zip">下载来源与审核包</a></section>
<div class="pair"><section class="panel"><p class="kicker">纸图上实际印了什么</p><h2 id="datum-paper-title">原纸图边栏</h2><label for="datum-crop-picker">选择可复核的边栏</label><select id="datum-crop-picker"></select><div class="crop-box"><a id="datum-margin-full" target="_blank" rel="noopener"><img id="datum-margin-image" alt="历史地图边栏裁片"></a></div><p class="small">点击裁片可打开原像素图像查看细字。</p><p id="datum-crop-meaning"></p><p id="datum-crop-position" class="small"></p><dl class="label-value" id="datum-paper-facts"></dl><div class="meaning"><strong>原纸图水平基准：未识别</strong>椭球名称和格网带号不足以补出完整基准。49S中的S为纬带，不能读作南半球。</div><p><a id="datum-scan-link" target="_blank" rel="noopener">查看UT Austin原始扫描 ↗</a></p></section>
<section class="panel digital"><p class="kicker">2005年数字化增加了什么</p><h2>哈佛原馆的处理记录</h2><div class="quote"><p id="datum-excerpt" lang="en"></p><p class="small">原馆元数据第二处理步骤，短摘句；其余为中文转述。</p></div><p>为使整套L500数字影像采用一致的坐标定义，馆方选择了WGS_1984。这个选择说明数字产品如何被组织，不能反推出原纸图使用的完整大地基准。</p><dl class="label-value" id="datum-digital-facts"></dl><p id="datum-same-edition"></p><details id="datum-source-details"><summary id="datum-source-toggle">查看原馆来源、位置与文件身份</summary><div id="datum-source-body"></div></details></section></div>
<section class="section"><h2>三个残差口径分别看</h2><p>哈佛的4角转换、本项目的8点拟合和5点同图留出使用不同影像或控制方案。数值大小不构成地面精度排名。</p><div id="datum-metrics" class="metrics"></div><div class="meaning"><strong>尚无独立地面精度结论</strong>这些数值没有证明近代河岸、古代建筑或北魏城址的地面位置。完整小数只保留在研究数据中以便核验；页面小数不表示亚米级定位。</div><p><a href="./historical-frame.html">返回B4的26个可点击原图交点</a></p></section>
<section class="section"><div class="candidate-head"><div><h2>稳定地物的审核队列</h2><p class="small">以下是待查类型与排除规则，尚无具名实体入选，也没有坐标。</p></div><div><label for="datum-candidate-filter">按审核状态查看</label><select id="datum-candidate-filter"><option value="all">全部类型</option><option value="pending">待查类型</option><option value="excluded">当前排除</option><option value="approved">已获准地面点</option></select></div></div><p id="datum-candidate-count" aria-live="polite"></p><div id="datum-candidate-list" class="candidate-list"></div></section>
<section class="section"><h2>下一阶段的四道证据门槛</h2><div id="datum-gates" class="gates"></div><div class="sources"><a href="./historical-datum/metadata.json">完整调查JSON</a><a href="./historical-datum/research.md">研究说明与来源索引</a><a href="./historical-datum/source-summary.svg">原图与数字化来源图版</a><a href="./historical-datum/review-summary.svg">残差与地物审核图版</a><a href="https://earth-info.nga.mil/?action=coordsys&amp;dir=coordsys" target="_blank" rel="noopener">NGA格网带定义 ↗</a></div></section>
</main><footer>本批新增古代经纬度0、古河道0，现代DSM未修改；原纸图水平基准保持未识别。调查进度不等于完成现代配准或古地形复原。</footer><script src="./historical-datum/datum.js"></script></body></html>'''


def build(site, cache):
    data = copy.deepcopy(read_data())
    validate_data(data)
    images = verified_images(data, cache)
    site = Path(site); cache = Path(cache)
    build_info = site / 'build-info.json'
    data['source_commit'] = read_data(build_info).get('source_commit') if build_info.is_file() else None
    data['build_identity_note'] = 'source_commit继承本次网站构建；单独离线复建而无build-info.json时为null。'
    pub = site / 'historical-datum'
    (pub / 'crops').mkdir(parents=True, exist_ok=True)
    for sheet in data['sheets']:
        for crop in sheet['crops']:
            crop['image'] = f'crops/{sheet["id"]}-{crop["id"]}.png'
            output = pub / crop['image']
            images[sheet['id']].crop(crop['raw_scan_crop_xyxy']).save(output, optimize=True)
            crop['image_sha256'] = sha(output)
            crop['image_size_px'] = [crop['raw_scan_crop_xyxy'][2] - crop['raw_scan_crop_xyxy'][0],
                                     crop['raw_scan_crop_xyxy'][3] - crop['raw_scan_crop_xyxy'][1]]
    (pub / 'metadata.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(ROOT / 'web/historical-datum-b5.js', pub / 'datum.js')
    shutil.copyfile(ROOT / 'docs/historical-datum-b5-research.md', pub / 'research.md')
    (site / 'historical-datum.html').write_text(page_html(), encoding='utf-8')
    source_plate(data, pub); review_plate(data, pub)
    (pub / 'README.txt').write_text('B5 历史地图基准调查\n\n' + data['summary'] + '\n\n' + '\n'.join(data['limitations']) + '\n\n元数据来自原馆固定commit的XML人工核验；构建不进行网络请求。裁片为原图无标注PNG，裁片坐标及哈希可在metadata.json逐一查验。没有赋予地理CRS或附加world file。\n', encoding='utf-8')
    downloads = site / 'downloads'; downloads.mkdir(exist_ok=True)
    with zipfile.ZipFile(downloads / 'luoyang-historical-datum-b5.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(pub.rglob('*')):
            if path.is_file():
                z.write(path, 'historical-datum/' + path.relative_to(pub).as_posix())
        for path in [DATA, ROOT / 'docs/historical-datum-b5-research.md', Path(__file__), ROOT / 'web/historical-datum-b5.js']:
            z.write(path, path.relative_to(ROOT).as_posix())
        z.write(site / 'historical-datum.html', 'historical-datum.html')
        for sheet in data['sheets']:
            z.write(cache / sheet['source_file'], 'inputs/' + sheet['source_file'])
        z.writestr('REPRODUCE.txt', textwrap.dedent('''\
            B5 historical datum-source investigation
            Dependencies: Python 3.11+, Pillow.
            Run: python tools/historical_datum_b5.py --cache inputs --site rebuilt
            Serve the archive folder with python -m http.server 8000 and open /historical-datum.html.
            Two reviewed source scans are included; SHA-256 is verified before output.
            Harvard XML is identified by official fixed-commit URLs, SHA-256 and XPath in metadata.json.
            No network access is needed to rebuild. Raw Harvard XML is not bundled.
            All crops are image-only. No geographic CRS, transformation or ground points are assigned.
            External navigation links require the full project website.
            '''))
    print('B5 datum investigation: 2 reviewed scans, 14 reproducible crops, 2 source plates; original datum unresolved; 0 approved ground points.')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=ROOT / '_site')
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache-terrain-v30')
    args = parser.parse_args()
    build(args.site, args.cache)


if __name__ == '__main__':
    main()
