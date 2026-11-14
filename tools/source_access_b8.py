#!/usr/bin/env python3
"""Build the reviewed B8 source-access metadata and two plates, offline.

The parent release builder owns build-info, navigation, HTML and the final PDF.
Public API: build_review(site, source_commit) -> published metadata dictionary.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import unicodedata
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'research/dual-b8/source-access.json'
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
    require(data['original_horizontal_datum'] is data['original_geographic_crs'] is None,
            'Original horizontal datum and CRS remain unknown')
    require(data['approved_ground_control_points'] == [] and data['source_assets'] == [],
            'This review supplies neither ground points nor new original-map images')
    for key in ('project_registration_to_wgs84', 'ground_accuracy_assessed',
                'modern_dsm_modified', 'coordinate_assignment_performed', 'new_historical_image_obtained'):
        require(data[key] is False, 'No geographic operation or target scan is established')
    require(data['ancient_geographic_positions_added'] == data['ancient_channels_added'] == 0,
            'No ancient geographic data may be added')
    sources = {source['id'] for source in data['sources']}
    records = {record['id']: record for record in data['access_records']}
    targets = {'zhengzhou-1942': ('YG821-2507', '000008299342'),
               'yanshi-1934': ('YG821-2519', '000008299355'),
               'sishui-1935': ('YG821-2516', '000008299352')}
    require(set(records) == set(targets) and len(records) == 3, 'Exactly three reviewed NDL targets required')
    for key, identifiers in targets.items():
        record = records[key]
        require((record['target_call_number'], record['bibliographic_id']) == identifiers, 'NDL target identity changed')
        require(record['public_image_url'] is record['raw_scan_crop_xyxy'] is None, 'No target image or pixel frame obtained')
        require(record['historical_image_obtained'] is record['historical_image_inspected'] is record['actual_ams_source_match'] is False,
                'Catalog access is not a visually checked source-map match')
        require(record['status'] == 'catalog_verified_public_image_not_located', 'Do not upgrade a bounded access result')
        require(record['copy_request_status'] == 'service_route_identified_not_applied' and
                record['item_specific_copy_eligibility_confirmed'] is False, 'Copy eligibility or application is not established')
        require(set(record['source_ids']) <= sources, 'Missing access evidence source')
    require([records[key]['target_publication_as_cataloged'] for key in targets] == ['[1942]', '1934.4', '1935.1'],
            'Preserve the three target catalog editions including brackets')
    require('西9行南1段' in records['yanshi-1934']['target_series'] and
            '西9行南1段' in records['sishui-1935']['target_series'], 'Full series prefixes are part of the target identity')
    upstream = {record['id']: record for record in data['upstream_records']}
    require((upstream['henan-1926-100k']['catalog_record_number'], upstream['henan-1926-100k']['catalog_sheet_count']) == ('4788', 185),
            'Keep the 1926 catalog collection identity')
    require((upstream['henan-1931-50k']['catalog_record_number'], upstream['henan-1931-50k']['catalog_sheet_count']) == ('4798', 263),
            'Keep the 1931 catalog collection identity')
    require(upstream['henan-1931-50k']['index_sheet_documented'] is True and
            upstream['henan-1931-50k']['notes_as_cataloged'] == '接合表1張', 'The documented join-index target must remain explicit')
    for record in upstream.values():
        require(record['historical_sheet_number'] is None and record['index_sheet_obtained'] is False,
                'A catalog item number is not a historical sheet number or obtained index')
        require(record['actual_parent_sheet_match'] is record['catalog_record_number_is_historical_sheet_number'] is False,
                'Compatible series do not establish the actual parent sheet')
    require(upstream['henan-1926-100k']['catalog_year'] == '1926' and
            upstream['henan-1926-100k']['scale_denominator'] == 100000 and
            upstream['henan-1931-50k']['catalog_year'] == '1931' and
            upstream['henan-1931-50k']['scale_denominator'] == 50000,
            'Keep the distinct 1926 and 1931 upstream series')
    comparison = {record['id']: record for record in data['comparison_records']}
    require(comparison['CCTS-4793']['catalog_year'] == '1930' and comparison['CCTS-4793']['catalog_sheet_count'] == 137 and
            comparison['CCTS-4809']['catalog_year'] == '1917–1947' and comparison['CCTS-4809']['catalog_sheet_count'] == 499,
            'The 1930 and mixed-year collections must stay separate')
    query = next(item for item in data['catalog_queries'] if item['id'] == 'TOHOKU-KAIFENG')
    require(query['returnGeometry'] is False and len(query['records']) == query['returned_record_count'] == 35,
            'Keep the exact bounded university catalog review')
    require(query['target_complete_identity_matches'] == 0 and query['exceeded_transfer_limit_reported'] is False,
            'No exact target identity is established by this query')
    for record in query['records']:
        require(not {'geometry', 'coordinates', 'Shape__Area', 'Shape__Length', 'spatialReference'} & set(record),
                'Catalog geometry is not historical-map spatial evidence')
    pier = data['structure_reviews'][0]
    require(len(data['structure_reviews']) == 1 and pier['id'] == 'huanghe-railway-pier-11', 'One numbered structure exclusion is reviewed')
    require(pier['status'] == 'excluded_as_continuously_surviving_point', 'Reported collapse must not become point admission')
    require(pier['coordinates'] is pier['anchor_pixel'] is None and pier['approved_as_ground_control'] is False,
            'No structure coordinates or approved physical point')
    require(pier['physical_point_in_ams_identified'] is pier['current_component_identity_verified'] is False,
            'Historic pier identity is not a modern or AMS point match')
    require(pier['evidence_level'] == 'operator_retrospective_history_not_original_engineering_drawing',
            'The pier account is retrospective, not an original engineering measurement')
    counts = data['review_counts']
    require(counts['target_maps_access_reviewed'] == 3 and counts['bounded_university_catalog_records_screened'] == 35 and
            counts['upstream_target_series_records'] == 2 and counts['documented_join_index_targets'] == 1 and
            counts['rejected_name_or_number_matches'] == len(data['rejected_matches']) == 3 and
            counts['named_structure_exclusions_added'] == 1, 'Review counts do not match reviewed records')
    for key in ('target_historical_scans_obtained', 'join_index_images_obtained', 'actual_ams_source_matches', 'approved_ground_control_points'):
        require(counts[key] == 0, 'No scan, actual-use match or ground point established')


def node(parent, name, **attrs):
    return ET.SubElement(parent, '{' + NS + '}' + name,
                         {key.replace('_', '-'): str(value) for key, value in attrs.items()})


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
    label(group, 70, 76, '北魏洛阳研究 / B8 原图获取与底图调查', 27, P['green'])
    label(group, 70, 147, title, 47, weight=700)
    label(group, 70, 205, subtitle, 27)
    return root, group


def write_svg(path, root):
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def access_plate(data, pub):
    root, g = svg_base('三馆号已有明确获取路径，公开原图仍待取得', '本次核查单件页、精确馆号查询和机构服务说明；没有数字链接，不等于没有馆藏或禁止利用。')
    rect(g, 70, 250, 2060, 120, P['pale'], rx=12)
    label(g, 100, 297, '已核：东京本馆地图室闭架路径 ＋ 注册用户远隔复制服务', 32, weight=700)
    label(g, 100, 343, '未预约、未申请、未付款；具体资料能否复制、提供范围及形式仍须馆方核定。', 28)
    columns = [70, 650, 1270, 2130]
    rect(g, 70, 405, 2060, 75, P['green'], rx=9)
    for i, title in enumerate(('目标原图／准确馆号', '本次公开入口结果', '下一步取得什么')):
        label(g, columns[i] + 26, 455, title, 29, '#ffffff', 700)
    short = [
        ('郑州／開封11號', 'YG821-2507 · [1942]', '1942摄影／测量说明与全幅边框'),
        ('偃师／西9行南1段開封21號', 'YG821-2519 · 1934.4', '完整图系、版记及1926底图指认'),
        ('汜水／西9行南1段開封16號', 'YG821-2516 · 1935.1', '版记、1931底图图号及接合表'),
    ]
    for i, (title, call, target) in enumerate(short):
        y = 480 + i * 140
        rect(g, 70, y, 2060, 140, '#ffffff' if i % 2 == 0 else P['pale'], stroke=P['line'])
        label(g, 96, y + 53, title, 28, weight=700)
        label(g, 96, y + 105, call, 27)
        label(g, 676, y + 53, '纸本目录；精确馆号查询1条', 28)
        label(g, 676, y + 105, '未定位对应公开数字本', 26, P['green'])
        label(g, 1296, y + 53, target, 28)
        label(g, 1296, y + 105, '先核个件利用状态，再取原件或许可影像', 25)
    cards = [
        ('同名，不同图号与年份', 'TH002729 · 鄭州', '東大：開封10号／1923\n目标：開封11號／[1942]', '不以“鄭州”同名代替目标印本。'),
        ('末尾21号，仍须核完整图系', 'TH002737 · 高平縣', '東大：開封21号／1924\n目标：偃師／西9行南1段／1934', '完整题名、前缀与年份均不相同。'),
        ('同音字形，不能自动改名', '岐阜881081240 · 泗水縣', '目录：泗水縣／1934\n目标：河南汜水縣／1935.1', '“泗”与“汜”不能先合并再匹配。'),
    ]
    for i, (heading, name, pair, decision) in enumerate(cards):
        x = 70 + 695 * i
        rect(g, x, 940, 670, 340, P['ochre'] if i == 0 else '#ffffff', stroke=P['line'], rx=12)
        label(g, x + 26, 989, heading, 28, weight=700)
        label(g, x + 26, 1042, name, 28, P['green'], 700)
        wrapped(g, x + 26, 1094, pair, 22, 26, 40)
        wrapped(g, x + 26, 1211, decision, 23, 26, 39)
    rect(g, 70, 1320, 2060, 180, P['pale'], rx=12)
    label(g, 100, 1374, '東大“開封”字段限定查询35条；目标完整身份未匹配，不是全馆藏不存在。', 30, weight=700)
    label(g, 100, 1423, '来源：NDL三件目录及外邦图／远隔复制指南；東大公开目录；岐阜北支十万分一目录。', 26)
    label(g, 100, 1470, '本批目标历史扫描取得0；接合表影像取得0；未建立新的地面控制点或地理CRS。', 26)
    write_svg(pub / 'access-summary.svg', root)


def upstream_plate(data, pub):
    root, g = svg_base('1931底图接合表已见目录，单幅图号仍待取得', '新增中国舆图集合条目4788／4798；机构、年代、尺度相容，仍不等于同一单幅或AMS实际用图。')
    cards = [
        (70, '1926 河南十万分一', '185幅 · 目录4788', '國民革命軍總司令部參謀處',
         '目录补充：少量图幅由河南陆军测量局绘制。集合组成也需逐幅分清。',
         '下一步：取得该集合的图幅目录或接合表，核偃师对应单幅及其实际编制机构。'),
        (1130, '1931 河南五万分一', '263幅 · 目录4798', '參謀本部陸地測量總局',
         '明确注记：接合表1張。\n已确认有这个目录记录，尚未取得表的影像。',
         '下一步：优先取接合表，先查汜水对应图名和图号，再取得单幅版记核印次。'),
    ]
    for x, title, count, creator, finding, gate in cards:
        rect(g, x, 250, 1000, 590, '#ffffff', stroke=P['line'], rx=12)
        label(g, x + 30, 310, title, 38, weight=700)
        label(g, x + 30, 380, count, 41, P['green'], 700)
        label(g, x + 30, 440, '目录机构：' + creator, 28)
        wrapped(g, x + 30, 510, finding, 32, 29, 44)
        rect(g, x + 30, 635, 940, 170, P['pale'], rx=9)
        wrapped(g, x + 54, 681, gate, 30, 28, 43)
    rect(g, 70, 875, 1000, 220, P['ochre'], rx=12)
    label(g, 100, 925, '比较集合要分开：1930十万分一', 31, weight=700)
    wrapped(g, 100, 980, '目录4793，137幅，參謀本部陸地測量總局。年代和机构组合不同，不并作1926目标集合。', 32, 28, 42)
    rect(g, 1130, 875, 1000, 220, P['ochre'], rx=12)
    label(g, 1160, 925, '比较集合要分开：1917—1947五万分一', 30, weight=700)
    wrapped(g, 1160, 980, '目录4809，499幅，机构带“等”，另记圖表1張。宽年代集合不替代1931专条的接合表。', 32, 28, 42)
    rect(g, 70, 1130, 2060, 225, '#ffffff', stroke=P['line'], rx=12)
    label(g, 100, 1180, '具名构件否决：历史11号桥墩不能默认连续存续', 33, weight=700)
    wrapped(g, 100, 1235, '郑州桥工段供稿记1958年11号墩倒塌，后经抢修恢复交通。功能恢复不证明同一基础、墩位或测量部位未变。', 69, 28, 42)
    label(g, 100, 1321, '证据是养护部门回顾史述；原始墩号图、抢修竣工资料及现代同点测量尚未取得。', 27, P['green'])
    rect(g, 70, 1387, 2060, 113, P['pale'], rx=12)
    label(g, 100, 1432, '目录号≠历史图号；接合表记载≠已取得影像；原纸图水平基准未知；获准地面点0。', 29, weight=700)
    label(g, 100, 1477, '来源：CCTS《北京图书馆舆图要录》4788／4798／4793／4809；郑州桥工段供稿，2021-12-22。', 25)
    write_svg(pub / 'upstream-summary.svg', root)


def build_review(site, source_commit):
    """Write only this review's three outputs and return identity-bound metadata."""
    require(isinstance(source_commit, str) and bool(source_commit.strip()), 'Explicit source_commit is required')
    data = copy.deepcopy(read_data())
    validate_data(data)
    data['source_commit'] = source_commit
    data['research_input_sha256'] = sha(DATA)
    data['approved_control_points'] = 0
    data['plates'] = ['source-access/access-summary.svg', 'source-access/upstream-summary.svg']
    pub = Path(site) / 'source-access'
    pub.mkdir(parents=True, exist_ok=True)
    access_plate(data, pub)
    upstream_plate(data, pub)
    data['plate_sha256'] = {path.name: sha(path) for path in sorted(pub.glob('*-summary.svg'))}
    (pub / 'metadata.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    data = build_review(args.site, args.source_commit)
    print('B8 source access:', json.dumps(data['review_counts'], ensure_ascii=False))


if __name__ == '__main__':
    main()
