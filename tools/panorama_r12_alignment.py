#!/usr/bin/env python3
"""Draw the frozen ground target against the rejected fifth image's manual audit.

This is a native vector diagnostic. It never edits or embeds the source PNG,
never estimates obscured ground centres, and never writes to the R11/projection
inputs. The two panels have one identical enlargement of original-image pixels.
"""
from pathlib import Path
import hashlib
import html
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/panorama-r12'
PROJECTION = OUT / 'projection.json'
REVIEW = OUT / 'reviews/v14-attempt5-review.json'
SOURCE_PNG = OUT / 'panorama-v14-source.png'
SIZE = (1920, 1430)
WINDOW = (440, 390, 590, 495)
SCALE = 4.6
PANEL_ORIGINS = ((120, 275), (1040, 275))
COLORS = {'ink': '#263d3a', 'muted': '#5b6b65', 'paper': '#f7f5ee',
          'target': '#186f69', 'red': '#ae3f34', 'amber': '#aa7217',
          'line': '#d6ded6', 'faint': '#adc4be'}
IDS = {'tower': 'r11-yongning-YN11-TOWER-PLINTH',
       'hall': 'r11-yongning-YN11-BUDDHA-HALL',
       'gate': 'r11-yongning-YN11-GATE-S'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import cairosvg
    from PIL import Image
    projection = json.loads(PROJECTION.read_text())
    review = json.loads(REVIEW.read_text())
    assert review['attempt'] == 5 and review['status'].startswith('rejected')
    assert review['homepage_replacement_approved'] is False
    assert review['source_projection_fidelity_passed'] is False
    assert review['candidate_image']['sha256'] == sha(SOURCE_PNG)
    assert review['projection_reference']['sha256'] == sha(PROJECTION)
    with Image.open(SOURCE_PNG) as im:
        assert list(im.size) == review['candidate_image']['size_px'] == [1672, 941]
    observed = review['manual_ground_observations']
    gate = observed['south_gate']
    hall = observed['buddha_hall']
    tower = observed['tower']
    wall = observed['yongning_low_wall_group']
    assert tower['full_ground_centre_observed'] is None
    counts = review['visible_storey_counts']
    assert counts['south_gate']['complete_principal_storeys_clearly_visible'] == 2
    assert counts['tower']['total_independently_identified_principal_storeys'] == 9
    features = {f['id']: f for f in projection['features']}
    wall_features = [f for f in projection['features']
                     if f['id'].startswith('r11-yongning-YN11-WALL-')]
    assert len(wall_features) == 7
    selected = wall_features + [features[x] for x in IDS.values()]
    before = {str(p.relative_to(ROOT)): sha(p) for p in [PROJECTION, REVIEW, SOURCE_PNG]}
    pieces = []

    def add(value):
        pieces.append(value)

    def text(x, y, value, size=22, color='ink', weight=400, anchor='start'):
        fill = COLORS.get(color, color)
        add(f'<text x="{x:.3f}" y="{y:.3f}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{html.escape(str(value))}</text>')

    def line(x1, y1, x2, y2, color='line', width=1.3, dash=None):
        extra = f' stroke-dasharray="{dash}"' if dash else ''
        add(f'<path d="M{x1:.5f},{y1:.5f}L{x2:.5f},{y2:.5f}" fill="none" '
            f'stroke="{COLORS.get(color,color)}" stroke-width="{width}"{extra}/>')

    def rect(x, y, width, height, fill='none', stroke='line', radius=0, dash=None, opacity=1):
        extra = f' stroke-dasharray="{dash}"' if dash else ''
        add(f'<rect x="{x:.5f}" y="{y:.5f}" width="{width:.5f}" height="{height:.5f}" '
            f'rx="{radius}" fill="{COLORS.get(fill,fill)}" stroke="{COLORS.get(stroke,stroke)}" '
            f'stroke-width="2" opacity="{opacity}"{extra}/>')

    def xy(panel, point):
        ox, oy = PANEL_ORIGINS[panel]
        return ox + (point[0] - WINDOW[0]) * SCALE, oy + (point[1] - WINDOW[1]) * SCALE

    def draw_targets(panel, faint=False):
        color = COLORS['faint' if faint else 'target']
        for feature in selected:
            geom = feature['projected_geometry']
            points = geom['coordinates'] if geom['type'] == 'LineString' else geom['coordinates'][0]
            q = [xy(panel, p) for p in points]
            d = 'M' + 'L'.join(f'{x:.5f},{y:.5f}' for x, y in q)
            if geom['type'] == 'Polygon':
                d += 'Z'
            dashed = ' stroke-dasharray="10 7"' if geom['type'] == 'LineString' else ''
            add(f'<path data-feature-id="{feature["id"]}" d="{d}" fill="none" '
                f'stroke="{color}" stroke-width="{2 if faint else 3}"{dashed}/>')

    def point(panel, p, color='red'):
        x, y = xy(panel, p)
        add(f'<circle cx="{x:.5f}" cy="{y:.5f}" r="6" fill="{COLORS[color]}" stroke="#fff" stroke-width="2"/>')
        return x, y

    def width_interval(panel, p, widths):
        x, y = xy(panel, p)
        small, large = [w * SCALE / 2 for w in widths]
        line(x - large, y, x + large, y, 'amber', 2)
        line(x - small, y, x + small, y, 'red', 6)
        for endpoint in (-large, large):
            line(x + endpoint, y - 10, x + endpoint, y + 10, 'amber', 2)
        for endpoint in (-small, small):
            line(x + endpoint, y - 5, x + endpoint, y + 5, 'red', 2)
        point(panel, p)

    def label(panel, p, label_text, target_x, target_y, color='target'):
        x, y = xy(panel, p)
        line(x + 8, y, target_x - 12, target_y - 7, color, 1.2)
        text(target_x, target_y, label_text, 20, color)

    title = '永宁寺：底稿目标与第五次试绘偏差'
    description = ('Two equally scaled original-image pixel panels compare unchanged R12 ground geometry '
                   'with approximate manual observations of the rejected fifth generated image. '
                   'No raster is embedded or modified. Manual ranges are not surveyed coordinates.')
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE[0]}" height="{SIZE[1]}" '
        f'viewBox="0 0 {SIZE[0]} {SIZE[1]}" font-family="Noto Sans CJK SC,sans-serif">'
        f'<title>{html.escape(title)}</title><desc>{html.escape(description)}</desc>')
    rect(0, 0, *SIZE, fill='paper', stroke='none')
    text(60, 65, title, 39, weight=700)
    text(60, 106, '第五次试绘未通过空间与门楼检查；本图是几何诊断，不是新艺术全景。', 24, 'red', 600)
    text(60, 141, '同一原图坐标 1672 × 941 px · 两栏同一倍率 · 图像人工约读，非实测', 22, 'muted')

    for panel, start in enumerate((50, 970)):
        rect(start, 171, 900, 645, fill='#fffefa', radius=12)
        text(start + 30, 212, 'A  冻结投影几何' if panel == 0 else 'B  第五次试绘的人工约读', 29, 'target' if panel == 0 else 'red', 600)
        text(start + 30, 245, '七段寺墙保留缺口；仅画塔座、佛殿框与南门基址。' if panel == 0 else '淡绿为同一目标；红点/宽度线与琥珀框为图像约读。', 20, 'muted')
        for x in (440, 460, 480, 500, 520, 540, 560, 580):
            x1, y1 = xy(panel, (x, WINDOW[1])); _, y2 = xy(panel, (x, WINDOW[3]))
            line(x1, y1, x1, y2, width=.8)
            text(x1, y2 + 25, x, 16, 'muted', anchor='middle')
        for y in (390, 410, 430, 450, 470, 490):
            x1, y1 = xy(panel, (WINDOW[0], y)); x2, _ = xy(panel, (WINDOW[2], y))
            line(x1, y1, x2, y1, width=.8)
            text(x1 - 12, y1 + 6, y, 16, 'muted', anchor='end')
        text(start + 835, 795, '原图 x / px', 17, 'muted', anchor='end')
        draw_targets(panel, faint=bool(panel))

    label(0, features[IDS['hall']]['ground_centre_px'], '佛殿刊图框', 750, 387)
    label(0, features[IDS['tower']]['ground_centre_px'], '塔座主体', 750, 465)
    label(0, features[IDS['gate']]['ground_centre_px'], '南门基址', 750, 570)
    text(185, 682, '寺墙画面包络：', 19, 'target')
    text(185, 710, 'x 459–565，y 399–454', 20, 'target')
    text(185, 738, '包络不是新增院墙轮廓。', 18, 'muted')

    bbox = wall['observed_ground_bbox_approx_px']
    bx, by = xy(1, bbox[:2])
    rect(bx, by, (bbox[2]-bbox[0])*SCALE, (bbox[3]-bbox[1])*SCALE,
         stroke='amber', dash='12 7')
    text(1120, 340, '低墙整体范围约：', 19, 'amber')
    text(1120, 369, 'x 454–578，y 420–483', 21, 'amber')
    line(1280, 379, bx + 16, by, 'amber', 1.4)
    width_interval(1, hall['observed_building_front_base_centre_approx_px'],
                   hall['observed_building_front_base_width_approx_px'])
    label(1, hall['observed_building_front_base_centre_approx_px'], '佛殿前基', 1535, 443, 'red')
    lowest = tower['lowest_timber_body_front_approx_px']
    point(1, lowest, 'amber')
    label(1, lowest, '最低木构前缘', 1535, 505, 'amber')
    width_interval(1, gate['observed_threshold_approx_px'],
                   gate['observed_building_front_base_width_approx_px'])
    label(1, gate['observed_threshold_approx_px'], '门槛约 (515,477)', 1525, 689, 'red')
    text(1130, 745, '粗线=宽度区间下限；细线/端帽=上限。', 18, 'muted')
    y_range = tower['plinth_or_stair_front_y_approx_px']
    yy = [xy(1, (WINDOW[2], y))[1] for y in y_range]
    # A one-dimensional axis bracket in the gutter, not a tower footprint.
    line(1780, yy[0], 1780, yy[1], 'amber', 5)
    line(1772, yy[0], 1788, yy[0], 'amber', 2)
    line(1772, yy[1], 1788, yy[1], 'amber', 2)
    text(1742, 560, '塔基/阶前缘', 17, 'amber')
    text(1742, 585, '仅 y≈441–445', 17, 'amber')
    text(1742, 612, '未画完整基址', 17, 'muted')

    text(60, 865, '关键核对：哪些没有满足共同底稿', 29, weight=600)
    rect(60, 886, 1800, 316, fill='#fffefa', radius=10)
    widths = {key: features[ident]['ground_bbox_px'][2] - features[ident]['ground_bbox_px'][0]
              for key, ident in IDS.items()}
    rows = [
        ('寺墙范围', '目标包络 x459–565 / y399–454', '约读 x454–578 / y420–483', '画面整体偏前，且略宽'),
        ('南门', f'目标基址宽 {widths["gate"]:.1f} px；框心约 (512,451)', '门前基宽约 38–43 px；门槛约 (515,477)', '只辨 2 层；要求 3 层'),
        ('佛殿', f'目标刊图框宽 {widths["hall"]:.1f} px；框心约 (517,414)', '前基宽约 45–50 px；前基点约 (517,426)', '宽度仍大，前缘偏前'),
        ('木塔', '目标塔座下缘最前 y≈433.7', '木构前缘 y≈440；基/阶前缘 y≈441–445', '9 层主要木构可辨；中心未定'),
    ]
    for x, heading in [(82, '对象'), (275, '冻结投影的图面目标'), (865, '第五次试绘的人工约读'), (1470, '本轮判断')]:
        text(x, 927, heading, 22, 'muted', 600)
    line(80, 945, 1840, 945)
    for index, values in enumerate(rows):
        y = 983 + index*60
        for col, (x, value) in enumerate(zip((82,275,865,1470), values)):
            text(x, y, value, 20 if col else 22, 'red' if col == 3 and index < 3 else 'ink', 600 if col == 0 else 400)
        if index < 3:
            line(80, y+20, 1840, y+20, width=.8)

    text(60, 1244, '约读限制：主要点位约 ±5 px，墙段约 ±10 px；门槛/前基/台阶与目标框心口径不同，不能直接当同一点的实测位移。', 20, 'muted')
    text(60, 1277, '宽度线只按约读点居中显示区间，不补出完整门殿基址；塔完整地面中心被遮，未猜测。九层塔不抵销门楼与占地检查失败。', 20, 'muted')
    text(60, 1310, 'H 未修改；局部图接入全城仍为候选绑定。y 增大仅表示画面更靠前，不是新的古代坐标或历史距离。', 20, 'muted')
    text(60, 1354, '试绘 PNG SHA256：' + sha(SOURCE_PNG), 15, 'muted')
    text(60, 1382, '审查 JSON SHA256：' + sha(REVIEW), 15, 'muted')
    add('</svg>')
    svg = ''.join(pieces)
    ET.fromstring(svg)
    assert '<image' not in svg and 'href=' not in svg
    path = OUT / 'alignment-audit.svg'
    path.write_text(svg, encoding='utf-8')
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(OUT/'alignment-audit.png'))
    output = {
        'schema': 'luoyang-r12-failed-sample-alignment-audit-v1',
        'research_version': 'R12.1', 'attempt': 5,
        'status': 'rejected_sample_diagnostic_not_accepted_candidate',
        'source_image': {'path':str(SOURCE_PNG.relative_to(ROOT)), 'sha256':sha(SOURCE_PNG),
                         'original_review_path':review['candidate_image']['file'],
                         'canvas_px':[1672,941], 'modified':False, 'embedded_in_diagram':False},
        'review': {'path':str(REVIEW.relative_to(ROOT)), 'sha256':sha(REVIEW),
                   'status':review['status'], 'manual_observation_pointer':'/manual_ground_observations'},
        'source_inputs_sha256': {**projection['source_inputs_sha256'], **before,
                                str(Path(__file__).resolve().relative_to(ROOT)):sha(Path(__file__))},
        'ground_projection': {'path':str(PROJECTION.relative_to(ROOT)), 'sha256':sha(PROJECTION),
                              'matrix_id':projection['matrix_id'],
                              'source_xy_m_to_canvas_homography':projection['source_xy_m_to_canvas_homography'],
                              'modified':False},
        'drawing': {'canvas_px':list(SIZE), 'original_pixel_window':list(WINDOW),
                    'uniform_display_scale':SCALE, 'panel_origins_px':[list(x) for x in PANEL_ORIGINS],
                    'mapping':'panel_pixel = panel_origin + 4.6 * (original_pixel - [440,390])',
                    'manual_width_display':'Interval bars are centred on the approximate reference point solely for display; they are not traced foundation edges.',
                    'tower_bracket':'The gutter bracket uses only source-image y; its drawing x is not an observed tower coordinate.'},
        'frozen_target_features': [{k:f[k] for k in ['id','label','geometry_role','placement_status',
                                  'projected_geometry','ground_bbox_px','ground_centre_px','source_refs','limits']} for f in selected],
        'manual_ground_observations':observed,
        'visible_storey_counts':counts,
        'target_projected_bbox_width_px':widths,
        'field_registration_verified':False, 'new_ancient_coordinates':0,
        'homepage_replacement_approved':False, 'source_projection_fidelity_passed':False,
        'obscured_tower_ground_centre_estimated':False,
        'limits':[
            'Frozen plan geometry and image manual observations have different evidence roles.',
            'Thresholds, front-base points, stairs and source footprint centres are not interchangeable control points.',
            'No observed foundation depth or full tower centre is invented.',
            'Coordinates are pixels of the actual fifth image, not new measured historic locations.',
            'The diagram explains this failed sample; it does not certify the full city or any upper structure.'],
        'outputs_sha256':{name:sha(OUT/name) for name in ['alignment-audit.svg','alignment-audit.png']},
    }
    for p, h in before.items():
        assert sha(ROOT/p) == h, ('Read-only source changed', p)
    (OUT/'alignment-audit.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'outputs':output['outputs_sha256'], 'source_png_sha256':sha(SOURCE_PNG),
                      'review_sha256':sha(REVIEW), 'frozen_H_unchanged':True},ensure_ascii=False))


if __name__ == '__main__':
    main()
