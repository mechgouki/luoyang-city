#!/usr/bin/env python3
"""Calibrate two historical scans to their own printed metric grid.

This is deliberately not a geographic registration: the map's horizontal datum
is unresolved. No EPSG code, world file, ground accuracy or ancient position is
produced. Run after terrain_v30.py; final release code must refresh build-info.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html
import io
import json
from pathlib import Path
import shutil
import zipfile

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'research/dual-b4/historical-frame.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def dump(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fit_sheet(sheet):
    """Only preassigned fit observations enter the six-parameter model."""
    fit = [p for p in sheet['points'] if p['id'] in sheet['fit_point_ids']]
    check = [p for p in sheet['points'] if p['id'] in sheet['check_point_ids']]
    assert len(fit) == 8 and len(check) == 5
    assert not set(sheet['fit_point_ids']) & set(sheet['check_point_ids'])
    assert all(p['role'] == 'fit' for p in fit)
    assert all(p['role'] == 'check' for p in check)
    xy = np.array([p['pixel_xy'] for p in fit], dtype=float)
    grid = np.array([[p['printed_grid_east_m'], p['printed_grid_north_m']] for p in fit], dtype=float)
    # Centre observations to avoid unnecessary conditioning problems from metre offsets.
    mean = xy.mean(axis=0)
    A = np.column_stack([xy - mean, np.ones(len(xy))])
    coeff, _, rank, _ = np.linalg.lstsq(A, grid, rcond=None)
    assert rank == 3 and abs(np.linalg.det(coeff[:2])) > 1
    inv = np.linalg.inv(coeff[:2])
    records = []
    for p in sheet['points']:
        measured = np.array(p['pixel_xy'], dtype=float)
        target = np.array([p['printed_grid_east_m'], p['printed_grid_north_m']], dtype=float)
        predicted_grid = np.r_[measured - mean, 1] @ coeff
        residual = predicted_grid - target
        predicted_pixel = (target - coeff[2]) @ inv + mean
        pixel_residual = measured - predicted_pixel
        records.append(dict(p, predicted_printed_grid_m=predicted_grid.tolist(),
                            residual_printed_grid_m=residual.tolist(),
                            residual_norm_printed_grid_m=float(np.linalg.norm(residual)),
                            residual_scan_px=pixel_residual.tolist(),
                            residual_norm_scan_px=float(np.linalg.norm(pixel_residual))))
    def stats(role):
        chosen = [p for p in records if p['role'] == role]
        return {'count': len(chosen),
                'rms_vector_printed_grid_m': float(np.sqrt(np.mean([p['residual_norm_printed_grid_m'] ** 2 for p in chosen]))),
                'max_vector_printed_grid_m': max(p['residual_norm_printed_grid_m'] for p in chosen),
                'rms_vector_scan_px': float(np.sqrt(np.mean([p['residual_norm_scan_px'] ** 2 for p in chosen]))),
                'max_vector_scan_px': max(p['residual_norm_scan_px'] for p in chosen)}
    return {'model': 'centred six-parameter affine; ordinary least squares',
            'pixel_centre_for_numerical_stability': mean.tolist(),
            'coefficients_rows_x_y_intercept': coeff.tolist(),
            'equation': '[E,N] = [x-x_mean, y-y_mean, 1] @ coefficients; E,N are printed grid values, not WGS84.',
            'fit': stats('fit'), 'internal_holdout_check': stats('check'),
            'ground_accuracy': None, 'geographic_crs': None, 'observations': records}


def rectify(image, result, extent, step=50):
    """Image-only resampling of the controlled rectangle; no geospatial tags."""
    left, bottom, right, top = extent
    width, height = round((right-left)/step), round((top-bottom)/step)
    assert width > 0 and height > 0
    coeff = np.array(result['coefficients_rows_x_y_intercept'])
    mean = np.array(result['pixel_centre_for_numerical_stability'])
    inverse = np.linalg.inv(coeff[:2])
    # Pillow transform coordinates refer to pixel corners, while recorded controls
    # are pixel centres. Convert explicitly by adding 0.5 to source centre values.
    p0 = (np.array([left, top]) - coeff[2]) @ inverse + mean + 0.5
    dx = np.array([step, 0.]) @ inverse
    dy = np.array([0., -step]) @ inverse
    affine = (dx[0], dy[0], p0[0], dx[1], dy[1], p0[1])
    out = image.transform((width, height), Image.Transform.AFFINE, affine,
                          resample=Image.Resampling.BICUBIC, fillcolor=(250,248,241))
    return out, {'printed_grid_extent_m': extent, 'display_grid_units_per_pixel': step,
                 'size_px': [width,height], 'geographic_crs': None,
                 'meaning': 'Image-only rectification inside the fit-control rectangle; 50 printed-grid metres per output pixel is display sampling, not ground accuracy.',
                 'source_inverse_affine_pillow': [float(v) for v in affine],
                 'pixel_centre_conversion': 'recorded source pixel centres + 0.5 -> Pillow source corner convention'}


def page_html():
    return '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>洛阳历史图幅 · 26个印刷格网交点</title>
<style>
:root{color-scheme:light;--ink:#243e39;--green:#326e5c;--paper:#f8f7f1;--line:#cbd2c6;--fit:#237a79;--check:#b4543f}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.7 system-ui,"Noto Sans CJK SC",sans-serif}a{color:#28654d}button,select{font:inherit;color:inherit}button{cursor:pointer}header{padding:24px 4vw;background:#edf1e7;border-bottom:1px solid var(--line)}header nav{display:flex;flex-wrap:wrap;gap:18px;font-size:14px}h1{font-size:clamp(24px,3.3vw,39px);margin:20px 0 10px;line-height:1.35}.lede{max-width:1000px;margin:0}.eyebrow{letter-spacing:.12em;font-size:12px;color:#667767}main{max-width:1700px;margin:auto;padding:24px 3vw}.controls{display:flex;flex-wrap:wrap;gap:9px;align-items:center;margin:0 0 17px}.controls button,.download{border:1px solid #aebeb0;background:#fff;padding:8px 15px;border-radius:6px}.controls button[aria-pressed="true"]{background:var(--green);color:white}.controls .spacer{flex:1}.grid{display:grid;grid-template-columns:minmax(0,1fr) 350px;gap:22px}.viewer,.side,.method{background:#fff;border:1px solid var(--line);border-radius:9px}.viewer{padding:14px;overflow:auto;align-self:start}.scan{position:relative}.scan img{width:100%;height:auto;display:block}.scan svg{position:absolute;inset:0;width:100%;height:100%}.scan svg circle{cursor:pointer;stroke:white;stroke-width:4}.scan svg text{font-size:40px;fill:#fff;paint-order:stroke;stroke:#253c37;stroke-width:7px;pointer-events:none}.side{padding:20px}.side h2{font-size:20px;margin:4px 0 12px}.side label,.side select{display:block;width:100%}.side select{padding:8px;margin:8px 0 15px;background:white;border:1px solid var(--line)}.point-crop{position:relative}.point-crop img{width:100%;display:block}.point-crop svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}.note{color:#657369;font-size:13px}.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;padding:10px 0}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px}.metric{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}.metric article{background:#edf2e8;padding:15px;border:1px solid #d0d9ca;border-radius:6px}.metric strong{display:block;font-size:27px;line-height:1.4}.metric span{font-size:12px;color:#526559}.table-wrap{overflow:auto;margin-top:22px}table{border-collapse:collapse;width:100%;background:white;font-size:14px}th,td{padding:10px 12px;border-bottom:1px solid #dce1d7;text-align:left;white-space:nowrap}th{background:#edf1e7}tr.selected td{background:#f9eddb}td button{padding:0;background:none;border:0;color:#2c6b53;text-decoration:underline}details{margin:23px 0;padding:20px}summary{cursor:pointer;font-weight:600}details p{max-width:1050px}code{overflow-wrap:anywhere;font-size:12px}.rectified-label{display:flex;justify-content:space-between;gap:10px;font-size:12px;flex-wrap:wrap}.status{font-size:12px;padding:3px 9px;background:#e8e7d8;border-radius:99px;display:inline-block}.bounds{padding:15px 19px;border-left:4px solid #a47a41;background:#f2ede0;margin-top:17px}.bounds b{font-weight:600}.source-label{max-width:100%;height:auto}#error{color:#a22;font-weight:600}.fit-color{background:var(--fit)}.check-color{background:var(--check)}@media(max-width:900px){.grid{grid-template-columns:1fr}.metric{grid-template-columns:1fr 1fr}.metric article:last-child{grid-column:1/-1}.side{display:grid;grid-template-columns:1fr 1fr;gap:12px}.side h2,.side .point-head{grid-column:1/-1}}@media(max-width:560px){main{padding:18px 4vw}.side{display:block}.side .point-crop{max-width:360px}.metric strong{font-size:22px}h1{font-size:26px}.controls .spacer{display:none}}
</style></head><body>
<header><nav><a href="./">文献母图</a><a href="./dual-north.html">北门—金墉 B4</a><a href="./v3.0.html">现代地形</a><a href="./dual-west.html">城西 B3</a></nav><h1>两幅历史图的26个印刷格网交点</h1><p class="lede">用原图的蓝色10公里方格网，检查扫描图的旋转、尺度与局部偏差。每幅8点参与拟合、5点留出检查，点位裁片与计算参数可逐项复核。</p><p><span class="status">B4 · 扫描图内校准</span> <span class="note">水平基准未识别 · 古代地理定位新增0</span></p></header>
<main><p id="error" hidden></p><section class="controls" aria-label="图幅与视图选择"><button data-sheet="NI49-7" aria-pressed="true">洛阳 NI49-7</button><button data-sheet="NI49-8" aria-pressed="false">郑县 NI49-8</button><span class="spacer"></span><button data-view="scan" aria-pressed="true">原图与点位</button><button data-view="rectified" aria-pressed="false">网格整饰图</button><a class="download" href="./downloads/luoyang-historical-frame-b4.zip">下载校准包</a></section>
<div class="grid"><section><div class="viewer"><div class="rectified-label" id="extent"></div><div class="scan"><img id="main-image" alt="历史扫描地图"><svg id="points-overlay" role="group" aria-label="图幅中的拟合点和留出检查点"></svg></div><div class="legend"><span><i class="dot fit-color"></i>拟合点 F：计算模型</span><span><i class="dot check-color"></i>留出点 C：同图内部检查</span></div><p class="note" id="view-caption"></p></div><div class="metric" id="metrics"></div></section>
<aside class="side"><div class="point-head"><h2>逐点查看原图</h2><label for="point-picker">选择交点</label><select id="point-picker"></select></div><div><div class="point-crop"><img id="crop-image" alt="所选网格交点的原始图像裁片"><svg id="crop-overlay" viewBox="0 0 240 240"><circle cx="120" cy="120" r="14" fill="none" stroke="#fff" stroke-width="4"/><path d="M100 120h40M120 100v40" fill="none" stroke="#b64c2f" stroke-width="1.5"/></svg></div><label class="note"><input id="crosshair" type="checkbox" checked> 显示点选中心</label></div><div id="point-detail"></div></aside></div>
<div class="bounds"><b>这些数字说明什么？</b> 残差以原图印刷网格米及扫描像素表示，只检验同张图中的方格网一致性。它们不表示地面精度，也没有证明近代河岸的位置或北魏建筑的位置。</div>
<div class="table-wrap"><table><thead><tr><th>点号</th><th>用途</th><th>原图像素 x / y</th><th>印刷 E / N（网格米）</th><th>矢量残差（网格米）</th><th>扫描像素</th></tr></thead><tbody id="point-table"></tbody></table></div>
<details class="method" open><summary>方法、来源与下一步</summary><p>四边及中间分布的8个蓝网交点用普通最小二乘拟合六参数仿射模型；5个另外量取的内部交点从一开始就不参与拟合。全部交点先在真实原图上核读，未把检查点移向模型预测位置。</p><p>整饰图只展示控制点包围的矩形，按每像素50个印刷网格米取样。输出为普通图像，没有写入EPSG、地理坐标标签或world file。两幅图分别处理，尚未宣布跨图无缝拼接。</p><p>原图边栏注明横轴墨卡托及International Spheroid；这不足以确定完整水平大地基准。接下来需要查明基准，筛选跨年代稳定地物，再用独立地面检查点验证。当前留出点属于同一份扫描图，不是地面控制点。</p><p><a id="source-link" href="#" target="_blank" rel="noopener">查看原始扫描图 ↗</a> · <a href="./historical-frame/points.csv">交点CSV</a> · <a href="./historical-frame/metadata.json">完整参数与残差JSON</a></p><p class="note" id="source-meta"></p><img id="label-image" class="source-label" alt="原图边栏中的完整印刷网格标签"><p class="note">标签裁片用于核实蓝网数字的单位及量级；坐标值按原图记录，未转换到现代基准。</p></details>
</main><script src="./historical-frame/frame.js"></script></body></html>'''


def summary_svg(data, pub):
    def image_uri(path):
        return 'data:image/jpeg;base64,' + base64.b64encode(path.read_bytes()).decode()
    s = ['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1800" height="1350" viewBox="0 0 1800 1350">',
         '<rect width="1800" height="1350" fill="#f8f7f1"/>',
         '<g font-family="Noto Sans CJK SC,sans-serif" fill="#29463b">',
         '<text x="70" y="78" font-size="24">北魏洛阳研究 / B4 历史图幅处理</text>',
         '<text x="70" y="138" font-size="42">从原始扫描，到可逐点复核的印刷网格</text>',
         '<text x="70" y="187" font-size="24">两幅图 · 16个拟合点 · 10个留出检查点 · 新增古代经纬度 0</text>']
    for i, sh in enumerate(data['sheets']):
        x = 70 + i*865
        s += [f'<text x="{x}" y="258" font-size="30">{html.escape(sh["id"]+" · "+sh["title"])}</text>',
              f'<image x="{x}" y="282" width="795" height="610" xlink:href="{image_uri(pub/sh["overview_image"])}"/>']
        w,h = sh['source_size_px']; scale = min(795/w,610/h)
        padx, pady = (795-w*scale)/2, (610-h*scale)/2
        for p in sh['points']:
            px,py = p['pixel_xy']; color = '#237a79' if p['role']=='fit' else '#b4543f'
            s.append(f'<circle cx="{x+padx+px*scale:.2f}" cy="{282+pady+py*scale:.2f}" r="7" fill="{color}" stroke="white" stroke-width="2"/>')
        check=sh['calibration']['internal_holdout_check']; fit=sh['calibration']['fit']
        s += [f'<text x="{x}" y="950" font-size="26">拟合8点 / 留出5点；图内检查 RMS {check["rms_vector_scan_px"]:.1f} 像素</text>',
              f'<text x="{x}" y="995" font-size="22">拟合约 {fit["rms_vector_printed_grid_m"]:.0f} / 留出约 {check["rms_vector_printed_grid_m"]:.0f} 印刷网格米</text>']
    s += ['<rect x="70" y="1050" width="1660" height="210" rx="12" fill="#eee9db"/>',
          '<text x="95" y="1103" font-size="27">这是同图内部的格网一致性，不是地面精度。</text>',
          '<text x="95" y="1152" font-size="24">水平基准仍未识别；未与WGS84地形叠合，未添加古河道或古建筑位置。</text>',
          '<text x="95" y="1200" font-size="24">下一步：查明基准 → 核实稳定地物 → 独立地面检查 → 分年代历史水系对比。</text>',
          '</g></svg>']
    (pub/'frame-summary.svg').write_text('\n'.join(s),encoding='utf-8')


def build(site, cache):
    data = load(DATA)
    assert data['ancient_geographic_positions_added'] == 0
    assert data['ancient_channels_added'] == 0 and not data['modern_dsm_modified']
    pub = site/'historical-frame'; pub.mkdir(parents=True,exist_ok=True)
    crops = pub/'crops'; crops.mkdir(exist_ok=True)
    for sheet in data['sheets']:
        path=cache/sheet['source_file']
        if not path.exists():
            raise FileNotFoundError(f'Run terrain_v30.py first; required reviewed scan: {path}')
        if sha(path) != sheet['source_sha256']:
            raise ValueError('Source scan changed; point selections require review: '+str(path))
        original=Image.open(path).convert('RGB')
        assert list(original.size)==sheet['source_size_px']
        number=sheet['id'].split('-')[-1]
        sheet['overview_image']=f'sheet-{number}-overview.jpg'
        preview=original.copy();preview.thumbnail((1800,1800));preview.save(pub/sheet['overview_image'],quality=90)
        sheet['label_image']=f'sheet-{number}-labels.jpg'
        original.crop(tuple(sheet['label_evidence_crop_xyxy'])).save(pub/sheet['label_image'],quality=95)
        for p in sheet['points']:
            x,y=p['pixel_xy'];p['crop_image']='crops/'+p['id']+'.jpg'
            # Preserve unmarked pixels; the browser adds a separately switchable crosshair.
            original.crop((x-120,y-120,x+120,y+120)).save(pub/p['crop_image'],quality=95)
        result=fit_sheet(sheet)
        result['observations']=[dict(r,crop_image=p['crop_image']) for r,p in zip(result['observations'],sheet['points'])]
        sheet['calibration']=result
        rectified, metadata=rectify(original,result,sheet['rectified_printed_grid_extent_m'])
        sheet['rectified_image']=f'sheet-{number}-rectified.jpg'
        rectified.save(pub/sheet['rectified_image'],quality=92)
        sheet['rectification']=metadata
    dump(pub/'metadata.json',data)
    shutil.copyfile(ROOT/'web/historical-frame-b4.js',pub/'frame.js')
    (site/'historical-frame.html').write_text(page_html(),encoding='utf-8')
    with (pub/'points.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['sheet','point','role','pixel_x','pixel_y','printed_grid_E_m','printed_grid_N_m','residual_E_grid_m','residual_N_grid_m','residual_vector_grid_m','residual_vector_scan_px','ground_accuracy_assessed','geographic_crs'])
        for sheet in data['sheets']:
            for p in sheet['calibration']['observations']:
                writer.writerow([sheet['id'],p['id'],p['role'],*p['pixel_xy'],p['printed_grid_east_m'],p['printed_grid_north_m'],
                                 *[round(v,4) for v in p['residual_printed_grid_m']],round(p['residual_norm_printed_grid_m'],4),
                                 round(p['residual_norm_scan_px'],4),False,'UNASSIGNED'])
    summary_svg(data,pub)
    (pub/'README.txt').write_text('AMS印刷方格网校准 B4\n\n'+data['scope']+'\n\n'+'\n'.join(data['limitations'])+'\n\n坐标无EPSG标签；不附world file。精确模型参数仅供复算，不表示地面精度。\n',encoding='utf-8')
    downloads=site/'downloads';downloads.mkdir(exist_ok=True)
    with zipfile.ZipFile(downloads/'luoyang-historical-frame-b4.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(pub.rglob('*')):
            if p.is_file():z.write(p,'historical-frame/'+str(p.relative_to(pub)))
        z.write(DATA,'research/dual-b4/historical-frame.json')
        z.write(Path(__file__),'tools/historical_frame_b4.py')
        z.write(ROOT/'web/historical-frame-b4.js','web/historical-frame-b4.js')
        z.write(site/'historical-frame.html','historical-frame.html')
        for sheet in data['sheets']:
            z.write(cache/sheet['source_file'],'inputs/'+sheet['source_file'])
        z.writestr('REPRODUCE.txt', 'Dependencies: Python 3.11+, numpy, Pillow.\nRun: python tools/historical_frame_b4.py --cache inputs --site rebuilt\nServe this folder with python -m http.server 8000 and open /historical-frame.html.\nThe source scans are included and their SHA-256 is checked.\nExternal project navigation links require the full published website.\nThese coordinates are printed-grid values only; no geographic CRS is assigned.\n')
    for sh in data['sheets']:
        check=sh['calibration']['internal_holdout_check']
        print(sh['id'],f'8 fit / 5 internal holdout: RMS {check["rms_vector_printed_grid_m"]:.1f} printed-grid m; {check["rms_vector_scan_px"]:.2f} scan px; no ground accuracy claim')
    return data


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--site',type=Path,default=ROOT/'_site')
    ap.add_argument('--cache',type=Path,default=ROOT/'.cache-terrain-v30')
    args=ap.parse_args();build(args.site,args.cache)


if __name__=='__main__':
    main()
