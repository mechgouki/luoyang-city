#!/usr/bin/env python3
"""Publish auditable local gate readings without placing them in city coordinates."""
from pathlib import Path
import csv
import hashlib
import html
import io
import json
import math
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image
from dual_cartography import dump, load
from north_b4 import fp, render_atlas
from prosperity_gate_geometry import (
    build_gate_geometry, render_gate_local, render_gate_city_link,
    render_gate_diagnostics,
)


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / '_site'
OUT = SITE / 'prosperity-gate'
RESEARCH = ROOT / 'research/prosperity-v3'
VERSION = 'prosperity-gate-v3'
ENTRY_UPDATES = [
    ('index.html', 'index-before-gate.html', 'gate-detail-home-entry'),
    ('v3.0-dual.html', 'v3.0-dual-before-gate.html', 'gate-detail-home-entry'),
    ('prosperity.html', 'prosperity-before-gate.html', 'gate-detail-entry'),
    ('prosperity-core.html', 'prosperity-core-before-gate.html', 'gate-detail-core-entry'),
]
MUTABLE = {item[0] for item in ENTRY_UPDATES} | {'build-info.json', 'release.json'}
ARCHIVES = {item[1] for item in ENTRY_UPDATES}
MAPS = {
    'local': {
        'filename': 'local-plan.svg', 'title': '阊阖门局部平面',
        'note': '图内米制来自原件比例尺。局部原点与图内方向用于量读，尚未接入城市坐标。',
        'renderer': render_gate_local,
    },
    'city': {
        'filename': 'city-link.svg', 'title': '局部平面与城市位置：接合依据',
        'note': '来源总图只提供城市概略锚点。局部平面与城市坐标的变换尚未核定，图内轮廓未作为新的古址落位。',
        'renderer': render_gate_city_link,
    },
    'diagnostics': {
        'filename': 'scale-diagnostics.svg', 'title': '图内量读与附表尺度核对',
        'note': '原件比例尺读数与附表门基尺寸分别保留。读数差异不通过拉伸图像或移动城市锚点消除。',
        'renderer': render_gate_diagnostics,
    },
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def own(path):
    return (path.startswith('prosperity-gate/') or path == 'prosperity-gate.html'
            or path in ARCHIVES or path.startswith('downloads/prosperity-gate-v3-')
            or (path.startswith('_assets/') and '-prosperity-gate-v3.' in path))


def esc(value):
    return html.escape(str(value), quote=True)


def prose(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return '；'.join(prose(item) for item in value)
    if isinstance(value, dict):
        return '；'.join(f'{key}：{prose(item)}' for key, item in value.items())
    return str(value) if value is not None else ''


def point_pairs(value):
    """Flatten nested geometry arrays, preserving the original vertex order."""
    if isinstance(value, (list, tuple)):
        if len(value) == 2 and all(isinstance(item, (int, float)) for item in value):
            if not all(math.isfinite(item) for item in value):
                raise ValueError('A reading contains a non-finite coordinate')
            return [list(value)]
        return [point for part in value for point in point_pairs(part)]
    if isinstance(value, dict):
        if {'x', 'y'} <= set(value):
            return point_pairs([value['x'], value['y']])
        for key in ['coordinates', 'points', 'vertices']:
            if key in value:
                return point_pairs(value[key])
    raise ValueError('Readings must contain explicit source or local coordinate pairs')


def source_records(raw):
    records = raw.values() if isinstance(raw, dict) else raw
    result = []
    for item in records:
        assert item.get('id') and item.get('url'), 'Sources need stable IDs and URLs'
        assert item['url'].startswith(('https://', 'http://')), 'Source URLs must be web references'
        result.append({**item, 'label': item.get('label') or item.get('title') or item['id'],
                       'note': prose(item.get('note') or item.get('source_level') or '')})
    assert len({item['id'] for item in result}) == len(result), 'Duplicate source ID'
    return result


def source_links(component, sources):
    refs = component.get('source_ref', [])
    refs = refs if isinstance(refs, list) else [refs]
    refs = [ref.get('id') if isinstance(ref, dict) else ref for ref in refs]
    by_id = {source['id']: source for source in sources}
    assert refs and all(ref in by_id for ref in refs), f"Unknown source reference for {component['id']}"
    return [{'id': by_id[ref]['id'], 'label': by_id[ref]['label'], 'url': by_id[ref]['url']} for ref in refs]


def component_for_page(component, sources):
    raw_points = point_pairs(component['source_px'])
    metric_points = point_pairs(component['coordinates_m'])
    assert len(raw_points) == len(metric_points), f"Mismatched vertex count: {component['id']}"
    tolerance = prose(component['trace_tolerance_px'])
    return {**component,
            'label': component.get('label') or component.get('title') or component['id'],
            'note': prose(component['note']),
            'evidence_label': component.get('evidence_label') or prose(component['evidence_status']),
            'dimensions_label': component.get('dimensions_label') or '图内描摹，尺寸未单列',
            'trace_note': f'原件描摹范围约 ±{tolerance} px；只表示图面线宽与读取范围，不等同遗址测量精度。',
            'reading_label': f'本构成保存 {len(raw_points)} 个原件读点。CSV 分列原件像素和换算后的局部米制，原始读点顺序保持不变。',
            'source_links': source_links(component, sources)}


def component_html(component):
    links = ''.join(f'<a href="{esc(source["url"])}" target="_blank" rel="noopener">{esc(source["label"])} ↗</a>'
                    for source in component['source_links'])
    return (f'<h2>{esc(component["label"])}</h2><p class="evidence-label">{esc(component["evidence_label"])}</p>'
            f'<p class="measure-label">图内量读 / 构成说明</p><p class="measure-value">{esc(component["dimensions_label"])}</p>'
            f'<dl class="component-facts"><dt>原件怎样支持这一构成</dt><dd>{esc(component["note"])}</dd>'
            f'<dt>读数使用范围</dt><dd>{esc(component["trace_note"])}</dd></dl><div class="component-links">{links}'
            '<a href="#source-comparison">对照来源原图 ↓</a>'
            '<a href="./prosperity-gate/readings.csv" download>下载像素与局部米制读数</a></div>'
            '<details class="reading-details"><summary>查看读数层说明</summary>'
            f'<p>{esc(component["reading_label"])}</p><p>图内原点与轴向只服务本图量读；这些坐标不作为古址经纬度发布。</p></details>')


def readings_csv(components):
    stream = io.StringIO(newline='')
    fields = ['component_id', 'label', 'kind', 'geometry_type', 'vertex_index', 'source_x_px', 'source_y_px',
              'local_x_m', 'local_y_m', 'trace_tolerance_px', 'evidence_status', 'source_ref', 'coordinate_scope']
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for component in components:
        source = point_pairs(component['source_px'])
        metric = point_pairs(component['coordinates_m'])
        assert len(source) == len(metric), component['id']
        for index, (pixel, local) in enumerate(zip(source, metric)):
            writer.writerow({'component_id': component['id'], 'label': component['label'],
                'kind': component['kind'], 'geometry_type': component['geometry_type'], 'vertex_index': index,
                'source_x_px': format(pixel[0], '.10g'), 'source_y_px': format(pixel[1], '.10g'),
                'local_x_m': format(local[0], '.10g'), 'local_y_m': format(local[1], '.10g'),
                'trace_tolerance_px': prose(component['trace_tolerance_px']),
                'evidence_status': prose(component['evidence_status']), 'source_ref': prose(component['source_ref']),
                'coordinate_scope': 'image_local_only; city_registration_unverified'})
    return stream.getvalue()


def patch_entries():
    """Archive prior pages verbatim; each navigation addition is one removable block."""
    records = []
    for path, archive_path, entry_id in ENTRY_UPDATES:
        target, archive = SITE / path, SITE / archive_path
        current = target.read_bytes()
        pattern = rb'<p id="' + entry_id.encode() + rb'"[^>]*>.*?</p>'
        matches = list(re.finditer(pattern, current, flags=re.S))
        if matches:
            assert len(matches) == 1 and archive.exists(), f'Unexpected existing P3 entry: {path}'
            before = archive.read_bytes()
            assert re.sub(pattern, b'', current, flags=re.S) == before, f'Prior page changed outside P3 entry: {path}'
        else:
            before = current
            if archive.exists():
                assert archive.read_bytes() == before, f'Archive does not match prior page: {path}'
            else:
                archive.write_bytes(before)
        block = (f'<p id="{entry_id}" style="padding:12px 16px;background:#e9efdf;border-left:3px solid #48715b">'
                 '<a href="./prosperity-gate.html" style="color:#244c3e;font-weight:600">'
                 '继续近看阊阖门：局部平面、原件量读与城市接合依据 →</a>'
                 ' · <a href="./prosperity-axis.html" style="color:#244c3e;font-weight:600">'
                 '宫城中轴：分段量距、道路与遗址分期 →</a></p>').encode()
        if path in {'index.html', 'v3.0-dual.html'}:
            section = re.search(rb'<section id="prosperity-entry"[^>]*>.*?</section>', before, flags=re.S)
            assert section, f'Missing prosperity entry: {path}'
            position = section.end() - len(b'</section>')
        else:
            marker = b'<nav class="view-switch"' if path == 'prosperity.html' else b'<div class="view-controls">'
            position = before.find(marker)
            assert position >= 0, f'Missing entry insertion point: {path}'
        after = before[:position] + block + before[position:]
        assert re.sub(pattern, b'', after, flags=re.S) == before, f'Entry is not exactly reversible: {path}'
        target.write_bytes(after)
        records.append({'path': path, 'archive_path': archive_path, 'before_sha256': sha(archive),
                        'after_sha256': sha(target), 'entry_id': entry_id,
                        'intent': '仅在可移除入口块内增加阊阖门 P3 与宫城中轴 P4 专题入口；其余页面字节保留。'})
    return records


def copy_source_raster(raw):
    relative = Path(raw['path'])
    original = (ROOT / relative if relative.parts[0] == 'research' else RESEARCH / relative).resolve()
    assert original.is_relative_to(RESEARCH.resolve()), 'The source raster must be a tracked P3 research input'
    assert sha(original) == raw['sha256'], 'Source raster checksum mismatch'
    with Image.open(original) as image:
        width, height = image.size
    assert width == raw['width_px'] and height == raw['height_px'], 'Source raster dimensions changed'
    target_relative = original.relative_to(RESEARCH)
    target = OUT / target_relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(original, target)
    assert sha(target) == raw['sha256']
    return {**raw, 'url': './prosperity-gate/' + target_relative.as_posix()}



def comparison_figure(source, raster, raster_source):
    """Two literal copies of the same image coordinate space, not a city placement."""
    w, h = raster['width_px'], raster['height_px']
    palette = {'gate_base':'#236a64', 'passage':'#ad671f',
               'que_base':'#4c537b', 'underground_foundation':'#9c7d3b',
               'foundation_connection':'#34798f'}
    traces = []
    for item in source['components']:
        tag = 'polygon' if item['geometry_type'] == 'Polygon' else 'polyline'
        pts = ' '.join(f'{point[0]},{point[1]}' for point in item['source_px'])
        dash = (' stroke-dasharray="6 5"' if item['kind'] in {'passage','foundation_connection'}
                else ' stroke-dasharray="10 7"' if item['kind'] == 'underground_foundation' else '')
        traces.append(
            f'<g data-compare-component="{esc(item["id"])}" role="button" tabindex="0" '
            f'aria-pressed="false" aria-label="选择{esc(item["label"])}">'
            f'<title>{esc(item["label"])}：{esc(item["note"])}</title>'
            f'<{tag} class="comparison-trace-line" points="{pts}" fill="none" '
            f'stroke="{palette[item["kind"]]}" stroke-width="2.8" '
            f'vector-effect="non-scaling-stroke"{dash}/></g>')
    img = esc(raster['url'])
    return ''.join([
        '<figure class="comparison-board"><div class="compare-panes">',
        '<div class="compare-pane"><h3>01 · 考古原图（保留完整画幅）</h3>',
        f'<a class="compare-frame" href="{img}" target="_blank" rel="noopener">'
        f'<img id="comparison-original" src="{img}" width="{w}" height="{h}" loading="eager" '
        'alt="阊阖门原件：包含平面、剖面、比例尺、北箭和探方标注"></a>',
        '<p>原件 555 × 434 px，无重采样；点击可单独放大。</p></div>',
        '<div class="compare-pane"><h3>02 · 同像素位置的人工描绘</h3>',
        '<div class="compare-frame" id="comparison-drawing">',
        f'<svg id="comparison-trace" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        'role="group" aria-label="阊阖门原图同像素读线，含10个可选构件">',
        '<title>十项人工描线与左图使用同一原件像素坐标</title>',
        f'<rect x="0" y="0" width="{w}" height="{h}" fill="#f8f7f1"/>',
        f'<image id="comparison-underlay" x="0" y="0" width="{w}" height="{h}" '
        f'href="{img}" opacity="0" preserveAspectRatio="none"/>',
        *traces, '</svg></div>',
        '<div class="comparison-controls"><label for="comparison-opacity">'
        '在右图叠加考古原图 <output id="comparison-opacity-value" for="comparison-opacity">0%（仅描线）</output></label>',
        '<input type="range" id="comparison-opacity" min="0" max="90" step="5" value="0" '
        'aria-label="在描绘图上叠加考古原图的透明度" disabled>',
        '<div class="comparison-actions"><button id="comparison-mix" type="button" disabled>叠加 55% 检查</button>'
        '<button id="comparison-clear" type="button" disabled>只看描绘</button></div></div>',
        '<p>在右图滑动叠加比例，可直接核对线条落点；点击线条查看对应出处。</p></div></div>',
        '<div class="comparison-legend"><span>绿色实线：门基</span><span>橙色虚线：三门道可辨段</span>'
        '<span>紫色实线：阙基边</span><span>金色虚线：地下基础</span>'
        '<span>蓝色虚线：连接路径示意</span></div>',
        '<figcaption>右图只描绘10项读线，未描绘处不表示不存在。门道截取端线不是墙；'
        '阙基开放端不补齐，地下基础虚线不是地面建筑边，连接线也不代表廊宽。'
        '两图一致的只是原件像素位置，未完成古址地理坐标配准。'
        f' <a href="{esc(raster_source["url"])}" target="_blank" rel="noopener">原始 PDF 第1962页 ↗</a>'
        f' <a href="{img}" target="_blank" rel="noopener">单独打开原件 JPEG ↗</a></figcaption></figure>'])


def axis_evidence_markup(axis):
    """Order-only palace axis evidence; no fictitious coordinates or spacings."""
    nodes = ''.join(
        f'<li class="axis-node"><span class="axis-order">{item["order_south_to_north"]:02d}</span>'
        f'<div><strong>{esc(item["label"])}</strong><p>{esc(item["description"])}</p></div></li>'
        for item in axis['nodes'])
    refs = ' · '.join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["title"])}</a>'
                      for s in axis['sources'])
    return (f'<ol class="axis-sequence">{nodes}</ol>'
            '<p class="axis-limit">按<strong>南 → 北</strong>阅读的是研究文献支持的相对序列，'
            '不是等距排布或实测宫墙、道路、院界。二号/三号门分别对应止车门/端门是研究者的身份解释，'
            '目前尚未取得可逐点并入城市坐标的共同控制。</p>'
            f'<p class="axis-source-links">资料：{refs} · '
            '<a href="./prosperity-gate/palace-axis-preliminary.json">下载四节点来源关系 JSON</a></p>')

def main():
    info = load(SITE / 'build-info.json')
    assert info.get('prosperity_core', {}).get('version') == 'prosperity-core-v2', 'Build P2 before P3'
    protected = {str(path.relative_to(SITE)): sha(path) for path in SITE.rglob('*') if path.is_file()
                 and str(path.relative_to(SITE)) not in MUTABLE and not own(str(path.relative_to(SITE)))}
    source = load(RESEARCH / 'gate-plan.json')
    axis = load(ROOT / 'research/prosperity-v4/axis-sequence.json')
    assert axis['version'] == 'palace-axis-p4-initial'
    assert [node['order_south_to_north'] for node in axis['nodes']] == [1, 2, 3, 4]
    assert len(axis['relative_sequence']) == 3
    assert axis['limitations']['absolute_coordinates_assigned'] == 0
    assert axis['limitations']['common_city_control_points_verified'] == 0
    models = build_gate_geometry(source)
    assert source['city_link']['registration_verified'] is False
    assert models['city_link']['registration_verified'] is False
    assert models['components'], 'The local plan needs source-backed components'
    OUT.mkdir(parents=True, exist_ok=True)
    (SITE / 'downloads').mkdir(parents=True, exist_ok=True)
    sources = source_records(source['sources'])
    components = [component_for_page(component, sources) for component in models['components']]
    assert len({component['id'] for component in components}) == len(components), 'Duplicate component ID'
    default = next((component['id'] for component in components if component['kind'] in {'gate_base', 'gate_foundation', 'foundation'}), components[0]['id'])
    raster = copy_source_raster(source['source_raster'])
    source_directory = RESEARCH / 'sources'
    if source_directory.exists():
        shutil.copytree(source_directory, OUT / 'sources', dirs_exist_ok=True)
    maps, atlas_paths = {}, []
    for key, spec in MAPS.items():
        drawing = spec['renderer'](source, models)
        root = ET.fromstring(drawing)
        assert root.tag == '{http://www.w3.org/2000/svg}svg'
        assert [float(value) for value in root.get('viewBox', '').split()] == [0, 0, 1600, 1100]
        target = OUT / spec['filename']
        target.write_text(drawing, encoding='utf-8')
        atlas_paths.append(target)
        maps[key] = {'url': './prosperity-gate/' + spec['filename'], 'viewBox': [0, 0, 1600, 1100],
                     'title': spec['title'], 'note': spec['note']}
    ids_in_plan = {element.get('data-component-id') for element in ET.parse(atlas_paths[0]).getroot().iter()
                   if element.get('data-component-id')}
    assert {component['id'] for component in components} <= ids_in_plan, 'Every component needs a selectable local-plan trace'
    downloads = [
        {'label': '阊阖门研究图册 PDF', 'url': './downloads/prosperity-gate-v3-atlas.pdf', 'type': 'pdf'},
        {'label': '完整资料包 ZIP', 'url': './downloads/prosperity-gate-v3-package.zip', 'type': 'zip'},
        {'label': '原始考古图 JPEG', 'url': raster['url'], 'type': 'jpeg'},
        {'label': '局部平面 SVG', 'url': maps['local']['url'], 'type': 'svg'},
        {'label': '城市接合 SVG', 'url': maps['city']['url'], 'type': 'svg'},
        {'label': '尺度核对 SVG', 'url': maps['diagnostics']['url'], 'type': 'svg'},
        {'label': '原件读数与证据 JSON', 'url': './prosperity-gate/gate-plan.json', 'type': 'json'},
        {'label': '局部米制模型 JSON', 'url': './prosperity-gate/models.json', 'type': 'json'},
        {'label': '像素与米制读数 CSV', 'url': './prosperity-gate/readings.csv', 'type': 'csv'},
        {'label': '量读与接合方法说明', 'url': './prosperity-gate/method.md', 'type': 'md'},
    ]
    limits = {'registration_verified': False, 'new_ancient_absolute_coordinates': 0,
              'historical_heights_reconstructed': False, 'roofs_reconstructed': False,
              'ancient_ground_surface_reconstructed': False, 'city_footprint_placed': False,
              'external_true_north_verified': False, 'full_city_reconstruction_completed': False}
    data = {'version': VERSION, 'source_commit': info['source_commit'], 'title': '从原件，读懂阊阖门',
            'maps': maps, 'components': components, 'default_component': default,
            'source_raster': raster, 'sources': sources,
             'comparison_version': 'source-pixel-side-by-side-v1',
             'axis_evidence': {'version': axis['version'], 'url': './prosperity-gate/palace-axis-preliminary.json',
                               'nodes': len(axis['nodes']), 'city_registration_verified': False},
             'calibration': models['calibration'],
            'diagnostics': models['diagnostics'], 'city_link': models['city_link'],
            'research_limits': limits, 'downloads': downloads,
            'source_data': './prosperity-gate/gate-plan.json', 'coordinate_scope': 'image_local_only'}
    dump(OUT / 'data.json', data)
    shutil.copyfile(RESEARCH / 'gate-plan.json', OUT / 'gate-plan.json')
    dump(OUT / 'palace-axis-preliminary.json', axis)
    dump(OUT / 'models.json', {**models, 'publication_version': VERSION, 'source_commit': info['source_commit'],
                             'coordinate_scope': 'image_local_only', 'research_limits': limits})
    (OUT / 'readings.csv').write_text(readings_csv(components), encoding='utf-8-sig', newline='')
    shutil.copyfile(ROOT / 'docs/prosperity-gate-method.md', OUT / 'method.md')
    render_atlas(atlas_paths, SITE / 'downloads/prosperity-gate-v3-atlas.pdf')
    css = fp('prosperity-gate-v3.css', (ROOT / 'web/prosperity-gate-v3.css').read_bytes())
    js = fp('prosperity-gate-v3.js', (ROOT / 'web/prosperity-gate-v3.js').read_bytes())
    raster_ref = raster.get('source_ref')
    raster_source = next((item for item in sources if item['id'] == raster_ref), sources[0])
    source_figure = comparison_figure(source, raster, raster_source)
    axis_html = axis_evidence_markup(axis)
    initial = next(component for component in components if component['id'] == default)
    substitutions = {
        '{{COMPONENT_OPTIONS}}': ''.join(f'<option value="{esc(component["id"])}"' + (' selected' if component['id'] == default else '') + f'>{esc(component["label"])}</option>' for component in components),
        '{{INITIAL_DETAIL}}': component_html(initial), '{{SOURCE_FIGURE}}': source_figure,
        '{{AXIS_HTML}}': axis_html,
        '{{DOWNLOAD_LINKS}}': ''.join(f'<a href="{esc(item["url"])}" download>{esc(item["label"])}</a>' for item in downloads),
        '{{SOURCE_CARDS}}': ''.join(f'<article class="source-card"><h3>{esc(item["label"])}</h3><p>{esc(item["note"])}</p><a href="{esc(item["url"])}" target="_blank" rel="noopener">查看原件出处 ↗</a></article>' for item in sources),
        '{{VERSION_LABEL}}': '阊阖门 P3 · ' + esc(info['source_commit'][:8]),
        './prosperity-gate-v3.css': './' + css, './prosperity-gate-v3.js': './' + js,
    }
    page = (ROOT / 'web/prosperity-gate-v3.html').read_text(encoding='utf-8')
    for placeholder, value in substitutions.items():
        assert placeholder in page, placeholder
        page = page.replace(placeholder, value)
    assert '{{' not in page
    (SITE / 'prosperity-gate.html').write_text(page, encoding='utf-8')
    updates = patch_entries()
    assert all(sha(SITE / path) == expected for path, expected in protected.items()), 'A protected P2 or earlier asset changed'
    preservation = {'version': VERSION, 'source_commit': info['source_commit'], 'protected_unchanged': True,
                    'protected_files': protected, 'intentional_html_updates': updates,
                    'existing_entity_ids_unchanged': True, 'source_geometry_unchanged': True,
                    'previous_preservation_files_unchanged': True}
    dump(OUT / 'preservation.json', preservation)
    atlas = SITE / 'downloads/prosperity-gate-v3-atlas.pdf'
    members = {f'prosperity-gate/{path.relative_to(OUT).as_posix()}': path for path in sorted(OUT.rglob('*'))
               if path.is_file() and path.name != 'bundle-manifest.json'}
    members['downloads/' + atlas.name] = atlas
    dump(OUT / 'bundle-manifest.json', {'version': VERSION, 'source_commit': info['source_commit'],
                                       'files_sha256': {name: sha(path) for name, path in members.items()}})
    members['prosperity-gate/bundle-manifest.json'] = OUT / 'bundle-manifest.json'
    with zipfile.ZipFile(SITE / 'downloads/prosperity-gate-v3-package.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, path in members.items():
            archive.write(path, name)
        archive.writestr('README.txt', '阊阖门 P3：局部平面、城市接合诊断与尺度核对。\n'
            '先阅读 prosperity-gate/method.md；图册位于 downloads/。SVG 可单独打开。\n'
            'gate-plan.json 保留来源像素，models.json 保存局部米制，readings.csv 逐点并列两者。\n'
            '图内米制、附表尺寸与城市总图概略锚点分别保留。城市配准未核定，无新增古址经纬度、古高或屋顶复原。\n'
            'bundle-manifest.json 记录包内研究文件与图册的 SHA-256；其自身与本说明不形成递归哈希。\n')
    release = load(SITE / 'release.json')
    release['extensions'] = sorted(set(release.get('extensions', []) + [VERSION]))
    release['prosperity_gate_version'] = VERSION
    release['current_milestone'] = '盛时P3.1：考古原图对照与宫城中轴首批研究'
    release['palace_axis_preliminary_version'] = axis['version']
    dump(SITE / 'release.json', release)
    info['prosperity_gate'] = {'version': VERSION, 'source_commit': info['source_commit'],
        'components': len(components), 'atlas_pages': len(atlas_paths), 'source_raster_sha256': raster['sha256'],
        'comparison_version': 'source-pixel-side-by-side-v1', 'axis_evidence_version': axis['version'],
        'registration_verified': False, 'new_ancient_absolute_coordinates': 0,
        'historical_heights_reconstructed': False, 'roofs_reconstructed': False,
        'ancient_ground_surface_reconstructed': False, 'protected_files': len(protected),
        'metadata': 'prosperity-gate/data.json'}
    info['files_sha256'] = {str(path.relative_to(SITE)): sha(path) for path in sorted(SITE.rglob('*'))
                           if path.is_file() and path.name != 'build-info.json'}
    dump(SITE / 'build-info.json', info)
    dump(ROOT / 'artifacts/prosperity-gate-build.json', info['prosperity_gate'])
    print(json.dumps(info['prosperity_gate'], ensure_ascii=False))


if __name__ == '__main__':
    main()
