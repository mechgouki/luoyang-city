#!/usr/bin/env python3
"""Publish reviewed named regions and source-map collars, without georeferencing.

All image inputs are local and hash locked. Run after west_roads_b5.py and before
the final B6 release generator. No network or geographic coordinate operation.
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
DATA = ROOT / 'research/dual-b6/ground-review.json'
NS = 'http://www.w3.org/2000/svg'
XL = 'http://www.w3.org/1999/xlink'
ET.register_namespace('', NS)
ET.register_namespace('xlink', XL)
P = {'paper': '#f8f7f1', 'ink': '#263f37', 'green': '#326754',
     'line': '#ccd4c5', 'pale': '#edf1e7', 'ochre': '#f0e8d6'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_data(path=DATA):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate_data(data):
    """Fail closed on unsupported CRS, point admission or source substitution."""
    assert data['original_horizontal_datum'] is None
    assert data['original_geographic_crs'] is None
    for key in ('project_registration_to_wgs84', 'ground_accuracy_assessed',
                'modern_dsm_modified', 'coordinate_assignment_performed'):
        assert data[key] is False
    assert data['approved_ground_control_points'] == []
    assert data['ancient_geographic_positions_added'] == data['ancient_channels_added'] == 0
    sheets = {s['id']: s for s in data['sheets']}
    sources = {s['id'] for s in data['sources']}
    assert set(sheets) == {'NI49-7', 'NI49-8'}
    assert len(sources) == len(data['sources'])
    assert {c['id'] for c in data['candidates']} == {'baima', 'huanghe-railway'}
    for sheet in sheets.values():
        assert sheet['original_horizontal_datum'] is None
        assert sheet['original_geographic_crs'] is None
        assert sheet['digital_assignment_role'] == 'post_publication_digitization_working_definition'
    for candidate in data['candidates']:
        assert candidate['status'] in {'pending', 'excluded'}
        assert candidate['record_kind'] in {'named_feature_region_review', 'named_feature_line_review'}
        assert candidate['approved_as_ground_control'] is False
        assert candidate['physical_point_identified'] is False
        assert candidate['coordinates'] is None and candidate['anchor_pixel'] is None
        assert candidate['default_source_id'] in candidate['source_ids']
        assert set(candidate['source_ids']) <= sources
        assert {'detail', 'context'} <= {c['id'] for c in candidate['crops']}
    for sheet in sheets.values():
        selections = [sheet['compilation_crop']]
        selections += [c for record in data['candidates'] if record['sheet_id'] == sheet['id'] for c in record['crops']]
        width, height = sheet['source_size_px']
        for crop in selections:
            x0, y0, x1, y1 = crop['raw_scan_crop_xyxy']
            assert all(isinstance(v, int) for v in (x0, y0, x1, y1))
            assert 0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height
    assets = {a['id']: a for a in data['source_assets']}
    assert len(assets) == 4
    for asset in assets.values():
        assert asset['kind'] == 'original_scale_iiif_region'
        assert asset['source_id'] in {'L531-K', 'L531-L'}
        assert asset['source_full_image_sha256'] is None
        assert len(asset['sha256']) == 64
        assert asset['local_file'].startswith('research/dual-b6/source-crops/')
        assert asset['rights_uri'] == 'http://rightsstatements.org/vocab/NKC/1.0/'
        x, y, w, h = asset['raw_iiif_crop_xywh']
        assert asset['raw_scan_crop_xyxy'] == [x, y, x + w, y + h]
        assert asset['size_px'] == [w, h]
        assert f'/{x},{y},{w},{h}/full/0/default.jpg' in asset['source_url']
        assert '/manifest/canvas/' in asset['source_canvas']
    for lineage in data['lineage_records']:
        assert lineage['exact_l500_source_impression_verified'] is False
        assert set(lineage['source_ids']) <= sources
        assert set(lineage['asset_ids']) <= set(assets)
        if lineage['id'] in {'l531-k', 'l531-l'}:
            assert lineage['observed_compiled_year'] == 1945
            assert lineage['observed_printed_year'] == 1946
            assert lineage['l500_cited_year'] == 1945
            assert lineage['projection_as_printed'] == 'Polyconic Projection'
            assert 'Yard' in lineage['grid_as_printed']
            assert lineage['original_horizontal_datum'] is None
            assert lineage['geographic_crs_assigned'] is None


def verified_images(data, cache):
    images = {}
    for sheet in data['sheets']:
        path = Path(cache) / sheet['source_file']
        if not path.is_file():
            raise FileNotFoundError(f'Reviewed scan required; run terrain_v30.py first: {path}')
        if sha(path) != sheet['source_sha256']:
            raise ValueError(f'Original scan SHA-256 mismatch: {path}')
        with Image.open(path) as image:
            if list(image.size) != sheet['source_size_px']:
                raise ValueError(f'Original scan dimensions changed: {path}')
            images[sheet['id']] = image.convert('RGB')
    return images


def verified_source_assets(data, root=ROOT):
    paths = {}
    for asset in data['source_assets']:
        path = Path(root) / asset['local_file']
        if sha(path) != asset['sha256']:
            raise ValueError(f'Fixed source crop SHA-256 mismatch: {path}')
        with Image.open(path) as image:
            if list(image.size) != asset['size_px']:
                raise ValueError(f'Fixed source crop dimensions changed: {path}')
        paths[asset['id']] = path
    return paths


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
        closing_punctuation = char in '。，；：？！、）】》」』.,;:?!'
        if char == '\n' or (used + width > units and not closing_punctuation):
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
    rect(root, 0, 0, 2200, 1560, P['paper'])
    g = node(root, 'g', font_family='Noto Sans CJK SC, sans-serif')
    label(g, 70, 76, '北魏洛阳研究 / B6 具名地物与编图来源审核', 27, P['green'])
    label(g, 70, 147, title, 48, weight=700)
    label(g, 70, 205, subtitle, 28)
    return root, g


def embed(parent, path, x, y, width, height):
    mime = 'image/jpeg' if Path(path).suffix.lower() in {'.jpg', '.jpeg'} else 'image/png'
    element = node(parent, 'image', x=x, y=y, width=width, height=height, preserveAspectRatio='xMidYMid meet')
    element.set('{' + XL + '}href', f'data:{mime};base64,' + base64.b64encode(Path(path).read_bytes()).decode('ascii'))


def write_svg(path, root):
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def candidate_plate(data, pub):
    root, g = svg_base('具名区域已经核读，测量点仍未获准', '两份原图裁片＋现代机构资料；文字、居住地圆圈和整桥线都不直接充作控制点。')
    short = [
        ('白马寺 / Pai-ma-ssu', '待补证 · 区域可辨，同点未定',
         '白馬寺名称邻近空心圆；同幅图例把圆圈列为“居住地”。没有单独画出可匹配现寺门基或塔心的测量点。',
         '不取地名、圆圈或现寺中心。文化部介绍支持现存寺院区域调查，未补齐某一建筑部位的跨期连续性。',
         '同期大比例尺图／航片 → 建筑部位 → 维修与测绘记录 → 独立现代测量', '[MCT-BAIMA] 文化部，2012-03-30'),
        ('黄河旧铁路桥 / 平汉线', '整桥线不准入为单点',
         '桥状线跨越黄河，平汉铁路名与岸边地名可核。线符号没有指定编号桥台、桥墩或可复测的基础部位。',
         '官方沿革有受损、换梁、加固、洪灾和拆除。排除整桥线与任意端点；个别存留桥台需另立记录。',
         '逐孔竣工图 → 拆建与加固记录 → 同一桥台编号／基础 → 现代工程测量。', '[ZZ-BRIDGE] 郑州市文物局，2016-10-25')]
    for i, (record, notes) in enumerate(zip(data['candidates'], short)):
        x = 70 + i * 1045
        title, status, seen, decision, gate, source = notes
        rect(g, x, 250, 1015, 1080, '#ffffff', stroke=P['line'], rx=12)
        label(g, x + 30, 300, status, 27, P['green'] if i == 0 else '#8b6235', 700)
        label(g, x + 30, 352, title, 35, weight=700)
        rect(g, x + 30, 378, 955, 400, '#f4f3eb', stroke=P['line'])
        detail = next(c for c in record['crops'] if c['id'] == 'detail')
        embed(g, pub / detail['image'], x + 45, 388, 925, 380)
        label(g, x + 30, 818, 'NI49-8 原像素裁片 / 未作地理变换', 23)
        wrapped(g, x + 30, 866, seen, units=33, size=27, leading=41)
        label(g, x + 30, 1015, '审核决定', 28, P['green'], 700)
        wrapped(g, x + 30, 1062, decision, units=33, size=27, leading=41)
        label(g, x + 30, 1190, '重新审核需要', 26, weight=700)
        wrapped(g, x + 30, 1234, gate, units=35, size=25, leading=38)
        label(g, x + 30, 1303, source, 22)
    rect(g, 70, 1360, 2060, 140, P['pale'], rx=12)
    label(g, 100, 1411, '获准地面控制点 0 / 原纸图水平基准未识别 / 本批没有地面精度结论', 31, weight=700)
    label(g, 100, 1465, '白马寺审核不裁决古代白马记录同异；桥梁审核不推定古河道。像素框、原图哈希与来源位置见随附JSON。', 26)
    write_svg(pub / 'candidate-summary.svg', root)


def lineage_plate(data, pub):
    root, g = svg_base('找到上游实物，也保留印次与基准的边界', 'L531目标图号已核；1945编图与1946印本分别记录；同源不等于同投影或同水平基准。')
    rect(g, 70, 250, 2060, 115, P['pale'], rx=12)
    label(g, 100, 294, 'L500编图栏的起点 / 1955年编图，1964年所见印本', 29, weight=700)
    label(g, 100, 340, 'NI49-7：I-49-K（1945）＋日本十万分一（1942—44）    NI49-8：I-49-K、I-49-L（1945）', 27)
    assets = {a['id']: a for a in data['source_assets']}
    for i, lineage in enumerate(data['lineage_records'][:2]):
        y = 395 + i * 345
        rect(g, 70, y, 2060, 315, '#ffffff', stroke=P['line'], rx=12)
        label(g, 100, y + 48, 'I-49-' + ('K 洛阳' if i == 0 else 'L 郑县'), 35, weight=700)
        label(g, 100, y + 103, '1946 实物印次', 30, P['green'], 700)
        wrapped(g, 100, y + 156, '编图1945；中国五万分一图。\nCentral Land Survey\n1931—38', units=18, size=27, leading=42)
        label(g, 100, y + 286, '[L531-' + ('K' if i == 0 else 'L') + '] Princeton 原图边栏', 22)
        asset = assets[lineage['asset_ids'][0]]
        embed(g, pub / asset['image'], 665, y + 12, 1435, 285)
    rect(g, 70, 1115, 1015, 385, '#ffffff', stroke=P['line'], rx=12)
    label(g, 100, 1167, '日本图与测量资料 / 目标印本仍待核', 29, weight=700)
    wrapped(g, 100, 1223, '中研院目录：1933—37年较早系列。东北大学有限标题检索：1923年洛陽縣十万分一图，未匹配1942—44。', units=33, size=27, leading=42)
    wrapped(g, 100, 1372, 'NIDS已给测量史与洛阳—西安地志档号；未取得地方控制网和基准实现资料。', units=33, size=27, leading=42)
    rect(g, 1115, 1115, 1015, 385, P['ochre'], rx=12)
    label(g, 1145, 1167, '不跨越的证据边界', 30, weight=700)
    wrapped(g, 1145, 1223, 'L531：多圆锥投影／10000码格网。L500：横轴墨卡托／UTM米制格网。上游图源不能替代下游的完整CRS。', units=33, size=27, leading=42)
    wrapped(g, 1145, 1372, '1946实物与L500所引1945印本的关系未确认；哈佛后期WGS84工作定义仍不回填到原纸图。', units=33, size=27, leading=42)
    write_svg(pub / 'lineage-summary.svg', root)


def page_html():
    return '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>洛阳历史图幅 · 具名地物与编图来源审核 B6</title>
<style>
:root{color-scheme:light;--ink:#263f37;--green:#326754;--paper:#f8f7f1;--line:#ccd4c5;--pale:#edf1e7}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.75 system-ui,"Noto Sans CJK SC",sans-serif}a{color:#24644a;overflow-wrap:anywhere}button,select{font:inherit;color:inherit;max-width:100%}button{cursor:pointer;padding:9px 15px;border:1px solid #afc0ac;border-radius:6px;background:#fff}header{padding:25px 4vw;background:var(--pale);border-bottom:1px solid var(--line)}nav{display:flex;flex-wrap:wrap;gap:16px;font-size:14px}.kicker{font-size:12px;letter-spacing:.1em;color:#61735f}h1{font-size:clamp(25px,3.2vw,42px);line-height:1.35;margin:20px 0 14px}h2{font-size:23px;line-height:1.4;margin:0 0 16px}h3{font-size:18px;line-height:1.5;margin:18px 0 10px}p{margin:10px 0}.lede{max-width:1100px}main{max-width:1660px;margin:auto;padding:28px 3.8vw}.toolbar{display:flex;gap:20px;justify-content:space-between;align-items:center;flex-wrap:wrap;margin-bottom:22px}.toolbar>div{min-width:230px}.download{border:1px solid #afc0ac;background:#fff;padding:10px 17px;border-radius:6px}.pair{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:22px}.panel,.section{background:#fff;border:1px solid var(--line);border-radius:10px;padding:24px;min-width:0}.section{margin-top:24px}.panel p,.section p,li,dd{overflow-wrap:anywhere}.small{font-size:13px;color:#5d6e62}.status{display:inline-block;padding:4px 10px;border-radius:99px;background:#e2e8d8;font-size:13px;margin:5px 5px 8px 0}label{display:block;margin:12px 0 6px;font-weight:600}select{display:block;width:100%;min-width:0;padding:10px;border:1px solid #b7c5b0;border-radius:5px;background:#fff}.crop-box{background:#f6f4ed;border:1px solid #d1d6c9;margin:16px 0 10px;min-height:180px;display:flex;align-items:center;justify-content:center}.crop-box a{width:100%}.crop-box img{display:block;width:100%;max-width:100%;height:auto;max-height:500px;object-fit:contain}.meaning{border-left:4px solid #b8945b;background:#f3ecdd;padding:15px 18px;margin:18px 0}.meaning strong{display:block}.label-value{display:grid;grid-template-columns:112px minmax(0,1fr);gap:9px 15px;margin:20px 0}.label-value dt{color:#617360}.label-value dd{margin:0}ul{padding-left:23px}li{margin:8px 0}.empty{padding:25px;border:1px solid var(--line);border-radius:8px;background:var(--pale)}code{font-size:12px;overflow-wrap:anywhere;word-break:break-all}.source-controls{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:end;margin-bottom:15px}.source-controls label{margin-top:0}.source-body{border-top:1px solid var(--line);padding-top:16px}.source-body img{width:100%;height:auto;display:block;border:1px solid var(--line);margin:15px 0}.lineage-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;margin-top:20px}.source-crop{background:#f7f6ef;border:1px solid var(--line);padding:14px;border-radius:7px}.source-crop img{width:100%;height:auto;display:block}.gates{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.gate{border-left:3px solid var(--green);padding-left:16px}.links{display:flex;flex-wrap:wrap;gap:12px 22px}.error{color:#a22;font-weight:700}footer{padding:22px 4vw 35px;border-top:1px solid var(--line);font-size:13px;color:#60715f}[hidden]{display:none!important}@media(max-width:900px){.pair,.lineage-grid,.gates{grid-template-columns:1fr}.panel,.section{padding:20px}}@media(max-width:480px){main{padding:20px 4vw}.panel,.section{padding:17px}.toolbar>div,.download{width:100%}.download{text-align:center}.source-controls{grid-template-columns:1fr}.label-value{grid-template-columns:85px minmax(0,1fr);font-size:14px}.meaning{padding:12px 14px}h2{font-size:21px}.crop-box img{max-height:440px}}
</style></head><body>
<header><nav><a href="./">文献母图</a><a href="./dual-southeast.html">城内至城东南 B6</a><a href="./historical-datum.html">原纸图基准 B5</a><a href="./historical-frame.html">图内格网校准 B4</a><a href="./v3.0.html">现代地形</a></nav><p class="kicker">B6 / 具名对象、连续性与原始图源</p><h1>找到地图上的名字，继续审核同一物理点</h1><p class="lede">本批核读白马寺地名区域与平汉铁路黄河跨河段，并取得L531上游图幅的真实边栏。两项具名审核都附原图裁片和后续门槛；获准地面控制点仍为0，原纸图完整水平基准仍未识别。</p><p><span class="status">具名审核 2 项</span><span class="status">L531 固定原比例裁片 4 张</span><span class="status">获准地面点 0</span></p></header>
<main><p id="ground-error" class="error" hidden></p><div class="toolbar"><div><label for="ground-filter">按审核状态查看</label><select id="ground-filter"><option value="all">全部具名记录</option><option value="pending">待补证区域</option><option value="excluded">当前排除为单点</option><option value="approved">获准地面控制点</option></select></div><a id="ground-download" class="download" href="./downloads/luoyang-ground-review-b6.zip">下载原图裁片与调查包</a></div><p id="ground-count" aria-live="polite"></p><label for="ground-record">选择具名审核对象</label><select id="ground-record"></select><div id="ground-empty" class="empty" hidden><h2>获准地面控制点 0</h2><p>当前没有具体物理点同时通过原图识别、跨年代连续和独立现代测量三道门槛。区域和线状对象尚不能作为控制点。</p></div>
<div id="ground-record-detail" class="pair" style="margin-top:22px"><section class="panel"><p class="kicker">原始扫描中能实际看见什么</p><h2 id="ground-title"></h2><label for="ground-crop">选择原图裁片</label><select id="ground-crop"></select><div class="crop-box"><a id="ground-image-link" target="_blank" rel="noopener"><img id="ground-image" alt="原图具名地物裁片"></a></div><p id="ground-crop-reading"></p><p id="ground-crop-position" class="small"></p><p class="small">点击图像查看原像素裁片。像素矩形是复查区域，不是测量点。</p><p><a id="ground-scan-link" target="_blank" rel="noopener">查看UT Austin原始扫描 ↗</a></p><div id="ground-map-facts"></div></section><section class="panel"><span id="ground-status" class="status"></span><h2>身份、连续性与审核决定</h2><div id="ground-review-reading"></div></section></div>
<section class="section"><h2>查看来源与引用位置</h2><div class="source-controls"><div><label for="ground-source">选择原图、馆藏或现代机构资料</label><select id="ground-source"></select></div><button id="ground-source-toggle" type="button" aria-expanded="false" aria-controls="ground-source-detail">展开来源详情</button></div><div id="ground-source-detail" class="source-body" hidden></div></section>
<section class="section"><p class="kicker">从L500编图边栏继续往上追</p><h2>图号、编图年与实物印次分别核对</h2><p>L500引用1945年的I-49-K／L；目前取得的Princeton实物标为1946年印本，编图栏确为1945年。两者的同印本关系仍待证明。</p><label for="lineage-record">选择来源链审核记录</label><select id="lineage-record"></select><div id="lineage-reading"></div><div id="lineage-images" class="lineage-grid"></div><div class="meaning"><strong>原纸图完整水平基准：仍未识别</strong>L531多圆锥投影、码制格网不继承给L500；哈佛后来赋予的WGS84继续保留为数字化工作定义。本批没有执行坐标转换。</div></section>
<section class="section"><h2>重新审核需要的证据</h2><div id="ground-gates" class="gates"></div><div class="links"><a href="./ground-review/metadata.json">完整研究JSON与SHA</a><a href="./ground-review/research.md">研究说明与来源索引</a><a href="./ground-review/candidate-summary.svg">具名地物审核图版</a><a href="./ground-review/lineage-summary.svg">上游来源链图版</a></div></section>
</main><footer>白马寺候选不裁决古代白马记录同异；桥梁审核不定位古河道。本批新增古址经纬度0、古河道0，现代DSM未修改。调查进度不等于完成现代配准或古地形复原。</footer><script src="./ground-review/ground.js"></script></body></html>'''


def build(site, cache):
    data = copy.deepcopy(read_data())
    validate_data(data)
    images = verified_images(data, cache)
    assets = verified_source_assets(data)
    site = Path(site); cache = Path(cache)
    build_info = site / 'build-info.json'
    data['source_commit'] = read_data(build_info).get('source_commit') if build_info.is_file() else None
    data['build_identity_note'] = 'source_commit继承本次网站构建；单独离线复建无build-info.json时为null。'
    data['named_candidates'] = len(data['candidates'])
    data['approved_control_points'] = len(data['approved_ground_control_points'])
    data['research_input_sha256'] = sha(DATA)
    pub = site / 'ground-review'
    (pub / 'crops').mkdir(parents=True, exist_ok=True)
    (pub / 'source-crops').mkdir(exist_ok=True)

    def publish_crop(crop, sheet_id, filename):
        crop['image'] = 'crops/' + filename + '.png'
        output = pub / crop['image']
        images[sheet_id].crop(crop['raw_scan_crop_xyxy']).save(output, optimize=True)
        crop['image_sha256'] = sha(output)
        x0, y0, x1, y1 = crop['raw_scan_crop_xyxy']
        crop['image_size_px'] = [x1 - x0, y1 - y0]

    for sheet in data['sheets']:
        publish_crop(sheet['compilation_crop'], sheet['id'], sheet['id'] + '-compilation')
    for record in data['candidates']:
        for crop in record['crops']:
            publish_crop(crop, record['sheet_id'], record['id'] + '-' + crop['id'])
    for asset in data['source_assets']:
        asset['image'] = 'source-crops/' + assets[asset['id']].name
        shutil.copyfile(assets[asset['id']], pub / asset['image'])
    (pub / 'metadata.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(ROOT / 'web/ground-review-b6.js', pub / 'ground.js')
    shutil.copyfile(ROOT / 'docs/ground-review-b6-research.md', pub / 'research.md')
    (site / 'ground-review.html').write_text(page_html(), encoding='utf-8')
    candidate_plate(data, pub); lineage_plate(data, pub)
    (pub / 'README.txt').write_text('B6 具名地物与来源链审核\n\n' + data['summary'] + '\n\n' + '\n'.join(data['limitations']) + '\n\nL500裁片从锁定扫描直接无标注裁切；L531裁片保留原馆IIIF响应字节。具体像素框、SHA、canvas和权利URI均见metadata.json。无地理CRS、world file或获准地面点。\n', encoding='utf-8')
    downloads = site / 'downloads'; downloads.mkdir(exist_ok=True)
    with zipfile.ZipFile(downloads / 'luoyang-ground-review-b6.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(pub.rglob('*')):
            if path.is_file():
                z.write(path, 'ground-review/' + path.relative_to(pub).as_posix())
        code_paths = [DATA, ROOT / 'docs/ground-review-b6-research.md', Path(__file__), ROOT / 'web/ground-review-b6.js']
        for path in code_paths + list(assets.values()):
            z.write(path, path.relative_to(ROOT).as_posix())
        z.write(site / 'ground-review.html', 'ground-review.html')
        for sheet in data['sheets']:
            z.write(cache / sheet['source_file'], 'inputs/' + sheet['source_file'])
        z.writestr('REPRODUCE.txt', textwrap.dedent('''\
            B6 named feature and source-map review
            Dependencies: Python 3.11+, Pillow.
            Rebuild: python tools/ground_review_b6.py --cache inputs --site rebuilt
            Serve the archive directory and open /ground-review.html for the packaged page.
            Both UT source scans and four reviewed Princeton IIIF region crops are included.
            Source bytes are SHA-256 verified before publication. No network required.
            Princeton credit: Army Map Service; Princeton University Library, Lewis Library,
            G7821.C2.s250 .A7M3. Original rights URI: http://rightsstatements.org/vocab/NKC/1.0/
            Source-crop hashes identify crop responses, not full-source TIFF files.
            No geographic CRS, world file, transformation or ground-point coordinates.
            External navigation and download links require the full project website.
            '''))
    identity = read_data(build_info) if build_info.is_file() else {'source_commit': data['source_commit']}
    identity['ground_review_b6'] = {
        'source_commit': data['source_commit'],
        'review_counts': copy.deepcopy(data['review_counts']),
        'metadata': 'ground-review/metadata.json',
        'metadata_sha256': sha(pub / 'metadata.json'),
        'original_horizontal_datum': None,
        'project_registration_to_wgs84': False,
        'approved_control_points': data['approved_control_points'],
    }
    build_info.write_text(json.dumps(identity, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('B6 ground review: 2 named region/line records, 7 raw L500 crops, 4 fixed L531 crops, 2 plates; 0 approved ground points.')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=ROOT / '_site')
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache-terrain-v30')
    args = parser.parse_args()
    build(args.site, args.cache)


if __name__ == '__main__':
    main()
