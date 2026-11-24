#!/usr/bin/env python3
"""Draw the two-image Yongning ground comparison from frozen coordinates.

The original PNG bytes are embedded unchanged. SVG viewports perform the
analysis crops; there is no image resampling, pixel editing, or fitted geometry.
Only overlay.svg and overlay.png are written. A selected image's actual audit
and reviewed, image-specific Chinese captions are required for final rendering.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import cairocffi as cairo
import cairosvg
from PIL import Image


REPO = Path(__file__).resolve().parents[1]
DEST = REPO / 'research/panorama-r12/yongning-triptych-20261124'
W, H = 2400, 1500
MARGIN, GAP, COL = 64, 40, 1116
MAIN_Y = 260
MAIN_CROP = (0, 620, 1254, 634)
MAIN_H = COL * MAIN_CROP[3] / MAIN_CROP[2]
INSET_Y = 879
INSET_W, INSET_H = 540, 232
INSETS = [('塔座基脚', (465, 900, 270, 116)),
          ('南门基脚', (425, 1110, 270, 116))]
P = {'paper': '#f4f1e9', 'panel': '#fffdf8', 'ink': '#193b40',
     'muted': '#5f716f', 'border': '#d4d8cd', 'source': '#12677d',
     'observed': '#c4532c', 'hidden': '#965c88', 'guide': '#6c7b38',
     'gold': '#b89d66'}
PRIMARY = {'YN11-TOWER-PLINTH', 'YN11-BUDDHA-HALL', 'YN11-GATE-S'}

# This is deliberately keyed to the exact selected raster. Add captions only
# after reading its completed audit; unknown images cannot inherit a verdict.
REVIEWED_CAPTIONS: dict[str, dict] = {
    'c1a831ed0fac45daccede52a10a3cd50a0225617148698cd9c766dc5cd36b9c5': {
        'panel_status': '局部改善 · 完整基址未通过',
        'cards': [
            {'title': '层数与前后关系保持',
             'lines': ['完整局部中：木塔九层，南门三层。',
                       '门塔基脚分开，后殿仍位于塔后。',
                       '修正图已去掉原彩线；此处重加分析线。']},
            {'title': '塔座前缘接近，整环仍待修正',
             'lines': ['前缘三点纵向差约 −0.7～+1.2 像素。',
                       '侧缘、四角尚未全部重合；',
                       '不能由前缘接近推定整座通过。']},
            {'title': '南门与后殿仍有可见残差',
             'lines': ['南门前缘约低 11～13 像素；',
                       '后殿左前缘约低 6 像素。',
                       '遮挡段与实体寺墙尚未验收。']},
        ],
    },
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def n(value: float) -> str:
    return format(float(value), '.9f').rstrip('0').rstrip('.') or '0'


def polyline(points, close=False) -> str:
    if not points:
        return ''
    result = 'M' + ' '.join(n(v) for v in points[0])
    result += ''.join('L' + ' '.join(n(v) for v in xy) for xy in points[1:])
    return result + ('Z' if close else '')


class OutlinedText:
    """Use installed CJK glyph outlines so the SVG needs no external font."""
    def __init__(self):
        self.ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 8, 8))

    def setup(self, size, bold=False, serif=False):
        self.ctx.select_font_face('Noto Serif CJK SC' if serif else 'Noto Sans CJK SC',
                                  cairo.FONT_SLANT_NORMAL,
                                  cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
        self.ctx.set_font_size(size)

    def width(self, text, size, bold=False, serif=False):
        self.setup(size, bold, serif)
        return self.ctx.text_extents(text)[4]

    def draw(self, text, x, y, size=24, fill=None, bold=False, serif=False):
        self.setup(size, bold, serif)
        self.ctx.new_path()
        self.ctx.move_to(x, y)
        self.ctx.text_path(text)
        commands = []
        for kind, points in self.ctx.copy_path():
            if kind == cairo.PATH_MOVE_TO:
                commands.append('M' + ' '.join(n(v) for v in points))
            elif kind == cairo.PATH_LINE_TO:
                commands.append('L' + ' '.join(n(v) for v in points))
            elif kind == cairo.PATH_CURVE_TO:
                commands.append('C' + ' '.join(n(v) for v in points))
            elif kind == cairo.PATH_CLOSE_PATH:
                commands.append('Z')
        return (f'<g aria-label={quoteattr(text)}><title>{escape(text)}</title>'
                f'<path fill="{fill or P["ink"]}" d="{"".join(commands)}"/></g>')


TEXT = OutlinedText()


def stroke(points, color, width=1.7, dash=None, close=False, halo=True, attrs=''):
    d = polyline(points, close)
    if not d:
        return ''
    out = ''
    if halo:
        out += (f'<path d="{d}" fill="none" stroke="#fffef9" stroke-opacity=".86" '
                f'stroke-width="{width + 2.1}" stroke-linejoin="round"/>')
    out += (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linejoin="round" stroke-linecap="round" '
            + (f'stroke-dasharray="{dash}" ' if dash else '') + attrs + '/>')
    return out


def circle(x, y, radius, stroke_color, fill='white', width=1.5):
    return (f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(radius)}" '
            f'stroke="{stroke_color}" stroke-width="{n(width)}" fill="{fill}"/>')


def label(text, x, y, size=22, color=None):
    width = TEXT.width(text, size) + 18
    return (f'<rect x="{n(x - 8)}" y="{n(y - size - 3)}" width="{n(width)}" '
            f'height="{n(size + 12)}" rx="5" fill="#fffdf8" fill-opacity=".94"/>'
            + TEXT.draw(text, x, y, size, color or P['ink']))


def audited_image(audit: dict, image: Path):
    actual_sha = sha(image)
    recorded = audit.get('image', {})
    if recorded.get('sha256') != actual_sha:
        raise ValueError(f'Audit does not identify the actual image: {image}')
    if (audit.get('actual_view_performed') is not True
            and recorded.get('actually_viewed') is not True):
        raise ValueError('An actual image review is required')
    with Image.open(image) as raster:
        if raster.size != (1254, 1254):
            raise ValueError('This figure requires the audited 1254 × 1254 canvas')
    if audit.get('coordinate_frame', {}).get('size_px', [1254, 1254]) != [1254, 1254]:
        raise ValueError('Observed coordinates must use the same 1254-pixel canvas')
    if not audit.get('observed_visible_paths'):
        raise ValueError('Actual observed material edges must be supplied')
    return actual_sha


def hidden_segments(audit, features):
    """Only source positions classified as obscured in this image's audit."""
    result = []
    seen = set()

    def add(points):
        key = json.dumps(points)
        if points and key not in seen:
            result.append(points)
            seen.add(key)

    for item in audit.get('occluded_source_segments', []):
        if item.get('expected_segment_px'):
            add(item['expected_segment_px'])
        elif item.get('source_edge', '').startswith('north_'):
            feature = features.get(item.get('component_id'))
            if feature:
                add(feature['local_1254_coordinates'][:2])
    for fid, edges in audit.get('edge_visibility_coverage', {}).items():
        north = str(edges.get('north_v0_v1', '')).lower()
        if fid in features and any(word in north for word in ('hidden', 'obscur')):
            add(features[fid]['local_1254_coordinates'][:2])
    return result


def scene(scene_id, image, audit, geometry):
    encoded = base64.b64encode(image.read_bytes()).decode('ascii')
    out = [f'<g id="{scene_id}">',
           f'<image x="0" y="0" width="1254" height="1254" '
           f'xlink:href="data:image/png;base64,{encoded}"/>']
    features = {f['id']: f for f in geometry['features']}
    endpoints = set()
    for feature in geometry['features']:
        points = feature['local_1254_coordinates']
        fid = feature['id']
        primary = fid in PRIMARY
        color = P['source'] if primary else P['guide']
        out.append(stroke(points, color, 1.85 if primary else 1.35,
                          None if primary else '5 4', feature['type'] == 'Polygon',
                          attrs=f'data-source-feature="{fid}"'))
        if primary:
            for x, y in points[:-1]:
                out.append(circle(x, y, 3.0, color))
        if feature['role'] == 'published_wall_centerline':
            for x, y in (points[0], points[-1]):
                key = (round(x, 7), round(y, 7))
                if key not in endpoints:
                    out.append(circle(x, y, 4.0, P['guide'], '#fffdf8', 1.8))
                    endpoints.add(key)
    for points in hidden_segments(audit, features):
        out.append(stroke(points, P['hidden'], 2.45, '5 4', halo=True))
    for record in audit['observed_visible_paths']:
        points = record.get('observed_polyline_px')
        if not points:
            continue
        uncertain = 'uncertain' in record.get('classification', '')
        out.append(stroke(points, P['observed'], 1.8, '4 3' if uncertain else None,
                          attrs=f'data-observed-edge={quoteattr(record.get("id", ""))}'))
    # Source labels are located in unused space. They never substitute a source
    # centre, roof edge or label leader for an observed ground control point.
    for text, xy, target in [
        ('佛殿刊图框', (820, 811), (729, 815)),
        ('塔座主体', (825, 968), (677, 970)),
        ('南门基址', (815, 1202), (662, 1174)),
        ('木塔地基框', (150, 1054), (348, 1022)),
    ]:
        out.append(stroke([(xy[0] - 10, xy[1] - 8), target], P['muted'], 1.15,
                          halo=False))
        out.append(label(text, *xy, 23))
    for text, xy in [
        ('北墙', (240, 645)), ('西北段', (150, 746)), ('西南段', (103, 1012)),
        ('东北段', (1090, 806)), ('东南段', (1055, 1092)),
        ('南墙西段', (220, 1185)), ('南墙东段', (830, 1150)),
    ]:
        out.append(label(text, *xy, 20, P['guide']))
    out.append('</g>')
    return ''.join(out)


def viewport(scene_id, x, y, width, height, crop, border=True):
    content = (f'<svg x="{n(x)}" y="{n(y)}" width="{n(width)}" height="{n(height)}" '
               f'viewBox="{" ".join(n(v) for v in crop)}" preserveAspectRatio="xMidYMid meet" '
               f'overflow="hidden"><use xlink:href="#{scene_id}"/></svg>')
    if border:
        content += (f'<rect x="{n(x)}" y="{n(y)}" width="{n(width)}" height="{n(height)}" '
                    f'fill="none" stroke="{P["border"]}" stroke-width="1.6"/>')
    return content


def badge(text, right, y, color):
    width = TEXT.width(text, 21) + 30
    return (f'<rect x="{n(right - width)}" y="{y}" width="{n(width)}" height="39" '
            f'rx="19.5" fill="{color}" fill-opacity=".10"/>'
            + TEXT.draw(text, right - width + 15, y + 27, 21, color))


def build_figure(geometry, old_image, old_audit, new_image, new_audit, captions,
                 old_audit_path, new_audit_path):
    sources = {'old_image_sha256': sha(old_image), 'new_image_sha256': sha(new_image),
               'old_audit_sha256': sha(old_audit_path), 'new_audit_sha256': sha(new_audit_path),
               'source_projection_sha256': geometry['source_projection_sha256'],
               'analysis_crop_local_pixels': list(MAIN_CROP),
               'source_coordinate_transform_fitted': False,
               'original_png_bytes_embedded_unchanged': True,
               'rendering': 'SVG viewports and exact source coordinates; CJK glyphs outlined',
               'new_image_unmatched_source_corners':
                   new_audit.get('source_corners_without_observed_match', []),
               'interpretation': 'A material edge comparison, not a complete geometry or historical acceptance.'}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" '
           f'xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="figure-title figure-desc">',
           '<title id="figure-title">永宁寺｜基址叠加对照</title>',
           '<desc id="figure-desc">原局部试片与本轮修正使用相同地面窗口。冻结来源轮廓、'
           '可见材料边、遮挡未核和没有实体对应的来源控制分别表示。基脚对照不构成完整几何通过。</desc>',
           '<metadata>' + escape(json.dumps(sources, ensure_ascii=False)) + '</metadata>',
           '<defs>', scene('old-scene', old_image, old_audit, geometry),
           scene('new-scene', new_image, new_audit, geometry), '</defs>',
           f'<rect width="{W}" height="{H}" fill="{P["paper"]}"/>',
           TEXT.draw('同一冻结底稿 · 同一显示比例', 64, 53, 23, P['muted']),
           TEXT.draw('永宁寺｜基址叠加对照', 60, 125, 62, bold=True, serif=True),
           TEXT.draw('同尺度地面局部，上部已裁切；这里只核基脚，不据本图计层。',
                     64, 174, 26, P['muted']),
           TEXT.draw('来源位置不随生成图移动', 1960, 72, 23, P['muted']),
           TEXT.draw('图面约读 ≠ 遗址测量', 2000, 111, 23, P['muted']),
           f'<path d="M64 193H2336" stroke="{P["gold"]}" stroke-width="2"/>']
    for x, title, tag, sid in [
        (64, '01  原局部试片', '整体几何未通过', 'old-scene'),
        (1220, '02  本轮修正', captions['panel_status'], 'new-scene'),
    ]:
        out.append(TEXT.draw(title, x, 237, 31, bold=True))
        out.append(badge(tag, x + COL, 208, P['muted']))
        out.append(viewport(sid, x, MAIN_Y, COL, MAIN_H, MAIN_CROP))
        for i, (title, crop) in enumerate(INSETS):
            sx = x + i * (INSET_W + 36)
            out.append(TEXT.draw(title + ' · 同尺度放大', sx, 861, 22, P['muted'], bold=True))
            out.append(viewport(sid, sx, INSET_Y, INSET_W, INSET_H, crop))
    legends = [(P['source'], None, '冻结来源轮廓'),
               (P['observed'], None, '实见材料边'),
               (P['hidden'], '7 5', '遮挡，地面边未核'),
               (P['guide'], '5 4', '仅来源控制，无实体对应')]
    for i, (color, dash, text) in enumerate(legends):
        x = 64 + i * 568
        out.append(stroke([(x, 1160), (x + 56, 1160)], color, 3.6, dash, halo=False))
        if i == 3:
            out.append(circle(x, 1160, 5, color))
            out.append(circle(x + 56, 1160, 5, color))
        out.append(TEXT.draw(text, x + 72, 1169, 25, color, bold=True))
    out.append(TEXT.draw('橙实线：可见下缘；橙虚线：地面层位不明的侧轮廓。'
                         '蓝色空心圆：来源角点；落在留白而未重合者不作遮挡。',
                         64, 1213, 22, P['muted']))
    out.append(TEXT.draw('七段寺墙与空心端点仅标来源位置；佛殿仅对刊图框，'
                         '木塔地基框不作塔院，凸部不推定踏步、坡道或栏杆。',
                         64, 1246, 22, P['muted']))
    card_w = (W - 2 * MARGIN - 48) / 3
    for i, card in enumerate(captions['cards']):
        x = MARGIN + i * (card_w + 24)
        out.append(f'<rect x="{n(x)}" y="1276" width="{n(card_w)}" height="159" '
                   f'rx="13" fill="{P["panel"]}" stroke="{P["border"]}"/>')
        out.append(TEXT.draw(f'0{i+1}  ' + card['title'], x + 24, 1312, 25, bold=True))
        if len(card['lines']) > 3:
            raise ValueError('Keep each conclusion card to three short lines')
        for j, line in enumerate(card['lines']):
            if TEXT.width(line, 22) > card_w - 48:
                raise ValueError('Conclusion line is too long: ' + line)
            out.append(TEXT.draw(line, x + 24, 1348 + j * 30, 22, P['muted']))
    out.append(TEXT.draw('原 PNG 未改，旧试片自带彩线保留；图例解释后加分析线。'
                         '修正图边缘约读 ±2 像素，非考古实测误差；不构成全景或首页换图通过。',
                         64, 1474, 20, P['muted']))
    out.append('</svg>')
    return ''.join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--geometry', type=Path, default=DEST / 'inputs/geometry-control.json')
    parser.add_argument('--old-image', type=Path, default=DEST / 'inputs/study02.png')
    parser.add_argument('--old-audit', type=Path, default=DEST / 'inputs/study02-ground-audit.json')
    parser.add_argument('--corrected-image', type=Path, default=DEST / 'corrected-local.png')
    parser.add_argument('--corrected-audit', type=Path, default=DEST / 'inputs/corrected-local-v2-audit.json')
    parser.add_argument('--prepare', action='store_true', help='Validate inputs/layout without writing the figure')
    args = parser.parse_args()
    geometry = json.loads(args.geometry.read_text())
    if (geometry['reference_local_canvas_px'] != [1254, 1254]
            or geometry['ground_homography_modified']
            or geometry['per_object_transform_fitted']):
        raise ValueError('Use the frozen common display geometry')
    old_audit = json.loads(args.old_audit.read_text())
    old_sha = audited_image(old_audit, args.old_image)
    if args.prepare:
        print(json.dumps({'status': 'layout_prepared_no_figure_written', 'canvas': [W, H],
                          'source_features': len(geometry['features']), 'old_image_sha256': old_sha,
                          'main_crop': MAIN_CROP, 'main_panel_size': [COL, MAIN_H],
                          'required_next_input': 'selected corrected image and its actual audit'}, ensure_ascii=False))
        return
    if args.corrected_audit is None:
        raise ValueError('Final rendering requires the selected image audit')
    new_audit = json.loads(args.corrected_audit.read_text())
    new_sha = audited_image(new_audit, args.corrected_image)
    if new_sha not in REVIEWED_CAPTIONS:
        raise ValueError('Chinese findings have not yet been reviewed for this exact image')
    captions = REVIEWED_CAPTIONS[new_sha]
    svg = build_figure(geometry, args.old_image, old_audit, args.corrected_image,
                       new_audit, captions, args.old_audit, args.corrected_audit)
    svg_path, png_path = DEST / 'overlay.svg', DEST / 'overlay.png'
    svg_path.write_text(svg, encoding='utf-8')
    cairosvg.svg2png(bytestring=svg.encode('utf-8'), write_to=str(png_path),
                    output_width=W, output_height=H)
    print(json.dumps({'status': 'rendered', 'selected_image_sha256': new_sha,
                      'files': [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)}
                                for p in (svg_path, png_path)]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
