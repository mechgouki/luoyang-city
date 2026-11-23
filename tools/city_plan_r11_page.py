"""The shared-coordinate plan, its evidence, and the complete unplaced register."""
import html
import json
from collections import Counter

from city_plan_r11_contract import BUNDLE, DATA, FOLDER, PAGE
from city_plan_r11_maps import LAYER_NAMES, world_svg
from xml.etree import ElementTree as ET

BASE = "https://mechgouki.github.io/luoyang-city/"


def h(v):
    if isinstance(v, (list, dict)):
        v = json.dumps(v, ensure_ascii=False)
    return html.escape(str(v if v is not None else ""), quote=True)


def prose(v):
    return "；".join(str(x) for x in v) if isinstance(v, list) else str(v or "")


def reference_list(refs, commit):
    items=[]
    for ref in refs:
        url=ref.get("url") or (f"https://github.com/mechgouki/luoyang-city/blob/{commit}/{ref['path']}" if ref.get("path") else "")
        label=ref.get("locator") or ref.get("label") or ref.get("id") or ref.get("path") or "来源记录"
        if not url: continue
        items.append(f'<li><a href="{h(url)}" rel="noopener">{h(label)}</a><code>{h(ref.get("path", ""))}{h(ref.get("pointer", ""))}</code></li>')
    return '<details><summary>回查依据</summary><ul class="source-list">'+''.join(items)+'</ul></details>' if items else ''


def feature_row(f, commit):
    role=f.get("geometry_role", "")
    hidden_note = '独立来源对照层，默认关闭，可在母图显式开启。' if f.get('layer')=='palace' else '本项默认隐藏：仅为旧显示范围。'
    button_label='查看范围依据' if role=='legacy_display_envelope' else '在母图查看'
    return f'''<tr id="feature-{h(f['id'])}" class="feature-row" data-layer="{h(f['layer'])}">
<td data-label="图上构件"><strong>{h(f.get('label', f['id']))}</strong><span class="record-id">{h(f['id'])}</span><button type="button" class="plain-button" data-focus-feature="{h(f['id'])}">{button_label}</button></td>
<td data-label="表达方式"><p>{h(LAYER_NAMES[f['layer']])}</p><span class="record-id">{h(role)}</span>{'<p>'+h(hidden_note)+'</p>' if f.get('default_visible') is False else ''}</td>
<td data-label="落位与限制"><p>{h(prose(f.get('limits', [])))}</p>{reference_list(f.get('source_refs', []),commit)}</td>
<td data-label="共同坐标"><details><summary>{h(f['geometry']['type'])} · 工作坐标</summary><code>{h(f['geometry'])}</code></details><span class="record-id">几何校验 {h(f['geometry_sha256'][:16])}</span></td></tr>'''


def coverage_row(e, data):
    names={f['id']:f.get('label',f['id']) for f in data['features']}
    features=e.get('feature_ids',[])
    links=' · '.join(f'<a href="#feature-{h(fid)}">{h(names.get(fid,fid))}</a>' for fid in features)
    status=e.get('placement_label') or e.get('placement_class') or e.get('placement_status') or '未定位'
    status={'source_geometry_bound':'有来源几何关联；具体落位等级见构件记录','candidate_marker':'独立文献候选点','directional_group_only':'共同方位签；内部位置未定','unplaced':'保留未定位／时相名录'}.get(status,status)
    limit=e.get('unplaced_reason') or e.get('placement_note') or e.get('limit') or e.get('limits') or ''
    phase=e.get('temporal_note') or e.get('phase_note') or e.get('period') or ''
    q=json.dumps(e,ensure_ascii=False)
    return f'''<tr id="entity-{h(e['id'])}" class="coverage-row" data-search="{h(q)}" data-placement="{h(e['placement_group'])}">
<td data-label="名录对象"><strong>{h(e['name'])}</strong><span class="record-id">{h(e['id'])}</span></td>
<td data-label="本轮去向"><p>{h(status)}</p><p>{links or '保留名录，不制造图上位置。'}</p></td>
<td data-label="时相与位置限制"><p>{h(prose(phase))}</p><p>{h(prose(limit))}</p>{reference_list(e.get('source_refs',[]),data['source_commit'])}</td></tr>'''


def constraint_row(c, commit, names):
    label=c.get('label') or c.get('relation') or c.get('type') or c.get('kind') or c.get('predicate') or ''
    status=c.get('status') or c.get('evaluation_status') or c.get('application_status') or ''
    status={'satisfied':'候选布局中的方向符合','unavailable':'缺少定位，暂不作坐标评估','not_a_coordinate_constraint':'保留语义关系，不转换成坐标','unsatisfied':'仍有冲突，保留待查'}.get(status,status)
    detail=c.get('reason') or c.get('limit') or c.get('limits') or c.get('uncertainty') or c.get('note') or ''
    a=c.get('from_object_id') or c.get('source_object_id') or c.get('from') or c.get('a') or c.get('subject_id') or ''
    b=c.get('to_object_id') or c.get('target_object_id') or c.get('to') or c.get('b') or c.get('target_id') or ''
    a=names.get(a,a);b=names.get(b,b)
    return f'<tr id="constraint-{h(c["id"])}"><td data-label="关系"><span class="record-id">{h(c["id"])}</span>{h(label)}<p>{h(a)} → {h(b)}</p></td><td data-label="本轮评估">{h(status)}<p>{h(prose(detail))}</p></td><td data-label="回查">{reference_list(c.get("source_refs",[]),commit)}<details><summary>完整关系记录</summary><code>{h(c)}</code></details></td></tr>'


def make_page(data, downloads, *, offline=False):
    views=data['views'];counts=data['counts']
    initial=next(v for v in views if v['id']=='all')
    inline=ET.tostring(world_svg(data,initial['bbox']),encoding='unicode')
    options=''.join(f'<option value="{h(v["id"])}">{h(v["title"])}</option>' for v in views)
    layers=''.join(f'<label><input type="checkbox" {"checked" if key!="palace" else ""} data-layer-toggle="{key}"><span class="swatch {key}"></span>{h(value)}</label>' for key,value in LAYER_NAMES.items())
    buttons=''.join(f'<button type="button" data-map-action="{k}" aria-label="{label}">{label}</button>' for k,label in [('in','放大'),('out','缩小'),('left','左移'),('right','右移'),('up','上移'),('down','下移'),('reset','复位')])
    feature_rows=''.join(feature_row(f,data['source_commit']) for f in data['features'])
    coverage_rows=''.join(coverage_row(e,data) for e in data['coverage'])
    object_names={o['id']:o.get('label') or o.get('name') or o['id'] for o in data['objects']}
    constraints=''.join(constraint_row(c,data['source_commit'],object_names) for c in data['constraints'])
    dl=''.join(f'<a class="download-card" href="{h(BASE+path if offline and path==BUNDLE else path)}" {"" if offline and path==BUNDLE else "download"} data-download="{h(path)}"><strong>{h(title)}</strong><small>{h("重新获取本离线包需联网；包内图纸和表格可直接使用。" if offline and path==BUNDLE else note)}</small></a>' for path,title,note in downloads)
    region_links=''.join(f'<a href="#plan-reader" data-view-link="{h(v["id"])}">{h(v["title"])}</a>' for v in views if v['id'].startswith('R'))
    embedded=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    counts_by=Counter(e['placement_group'] for e in data['coverage'])
    summaries=''.join(f'<option value="{key}">{label}（{counts_by[key]}）</option>' for key,label in [('source','有来源几何关联'),('candidate','候选点或共同签'),('unplaced','未落位／另层名录')])
    bindings=json.dumps(data['bindings'],ensure_ascii=False,indent=2)
    diagnostics=json.dumps(data['diagnostics'],ensure_ascii=False,indent=2)
    registration=data['diagnostics']['objects']['registration']
    fit_note=f"文献候选点的初始化使用九个同名门图签作工作拟合；绘图残差均方根约{registration['rmse_display_m']:.1f}米、最大约{registration['max_residual_display_m']:.1f}米。这反映两套旧图表达的布局差，不能当作古址定位误差或精度。"
    sources=''.join(f'<li><a href="{h(s.get("url") or "https://github.com/mechgouki/luoyang-city/blob/"+data["source_commit"]+"/"+s.get("path",""))}">{h(s.get("label") or s.get("title") or s.get("id") or s.get("path"))}</a></li>' for s in data['source_summary'])
    prefix=BASE if offline else './'
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="北魏洛阳516–528年全城统一坐标复原工作平面：原图轮廓、候选落位、十一片区与逐项证据。"><title>洛阳 · 全城统一坐标复原工作平面 R11.1</title><link rel="stylesheet" href="{FOLDER}/atlas.css"><script src="{FOLDER}/atlas.js" defer></script></head>
<body><nav class="topnav"><a class="brand" href="{prefix}">洛阳 · 历史复原</a><a href="#plan-reader">统一平面</a><a href="#evidence">构件依据</a><a href="#coverage">全部对象</a><a href="#downloads">下载图纸</a><a href="{prefix}luoyang-city-layout.html">R10 关系图集</a></nav>
{'<div class="offline-note">离线阅读版：地图、表格和文件均在本包中；原始出版物与旧专题链接需要联网。</div>' if offline else ''}
<main><header class="hero"><div class="eyebrow">LUOYANG / SHARED CITY PLAN / R11.1</div><h1>洛阳 · 全城复原工作平面</h1><p class="lede">把来源总图、局部考古图和文献方位放进同一张可回查的母图。全城与十一片区共享坐标；有轮廓依据的对象画轮廓，只有方位依据的对象保留候选位置。</p><div class="status-line"><span class="tag">516–528 年盛时综合</span><span class="tag">一套坐标 · 十一片区取景</span><span class="tag candidate">候选接入层仍含定位假定</span></div>
<div class="stats"><div class="stat"><strong>{counts['source_features']}</strong><span>保留的来源骨架要素</span></div><div class="stat"><strong>{counts['trace_features']}</strong><span>从局部原图提取的构件</span></div><div class="stat"><strong>{counts['candidate_features']}</strong><span>文献候选点／共同位置签</span></div><div class="stat"><strong>{counts['entities']}</strong><span>逐项登记的全部名录对象</span></div></div></header>
<section id="plan-reader"><div class="section-heading"><div><h2>从全城，读到院落与门址</h2><p id="view-note">{h(initial['subtitle'])}</p></div><a href="{FOLDER}/maps/all.svg">打开全城矢量图</a></div>
<noscript><p class="no-js-note">当前未运行脚本：下方总图与全部证据表仍可阅读；请从下载区打开各片区图与局部图。</p></noscript>
<div class="reader"><div class="reader-toolbar"><label class="control view">取景范围<select id="view-select">{options}</select></label><label class="control search">查名称或编号<input id="map-search" type="search" placeholder="例如：永宁、阊阖、白马" autocomplete="off"></label><button id="clear-map-search" class="plain-button" type="button">清空</button><div class="map-buttons">{buttons}</div></div><div class="layer-tools">{layers}<label><input id="label-toggle" type="checkbox" checked>显示名称</label></div><div id="search-results" class="search-results" aria-live="polite"></div>
<div class="map-and-info"><div class="map-wrap"><div class="map-viewport" id="map-viewport" tabindex="0" aria-label="统一坐标平面，可用方向键移动">{inline}<div class="map-north">北 ↑</div></div><div class="map-caption"><span id="map-scale">来源图局部米制；非GPS定位</span><span>点选构件查依据 · 方向键移动 · ＋／－缩放</span></div></div><aside class="object-panel" id="object-panel" aria-live="polite"><h3 id="selected-title">选择一个构件</h3><p id="selected-layer" class="hint">绿色读骨架，紫色读局部原图，金色读候选位置。</p><div id="selected-evidence"><p>先看全城，再切换“宫城中轴”“阊阖门”“永宁寺”或任一片区。所有窗口裁取同一套几何。</p><p>局部图的轮廓可以清楚，接入全城的位置仍可能是假定；两者在每项记录中分别说明。</p></div></aside></div></div>
<p class="table-prompt">图上的叉号和圆点是定位符号，不表示建筑大小；名称可能因避让而移动，实体坐标保持不变。</p><div class="region-index">{region_links}</div></section>
<section><h2>这轮实际改变了什么</h2><div class="insights"><article class="insight"><h3>局部轮廓进入全城</h3><p>阊阖门图示门基、通道与开放遗迹线，连同新取得的永宁寺刊载平面，按原比例尺转成局部米制，再记录候选接入关系。</p></article><article class="insight"><h3>南门有了图示方向</h3><p>永宁寺南门不再只是一张无轴向尺寸卡：原图可辨的长边与门址轮廓进入母图；没有据此补画北门或完整柱网。</p></article><article class="insight"><h3>总图与片区不再各排一套</h3><p>十一片区只改变取景窗口。方位判断、群组位置签与未定位名录各有去向，不把同里成员排成虚构街列。</p></article></div></section>
<section><div class="section-heading"><h2>两处局部图，接回同一母图</h2><p>这里展示的是同坐标取景，并非另排的关系示意窗。</p></div><div class="inset-grid"><article class="inset"><header><h3>宫城阊阖门</h3><p>原图20米比例尺；开放边保持开放。候选绑定不改变原图尺度。</p></header><img src="{FOLDER}/maps/changhe.svg" alt="阊阖门在共同母图中的构件轮廓" loading="lazy"><a href="#plan-reader" data-view-link="changhe">在母图中放大阊阖门 →</a></article><article class="inset"><header><h3>永宁寺</h3><p>新刊载平面中的寺墙、塔基、佛殿与门址；不同来源残墙另层保留。</p></header><img src="{FOLDER}/maps/yongning.svg" alt="永宁寺在共同母图中的寺墙和建筑基址" loading="lazy"><a href="#plan-reader" data-view-link="yongning">在母图中放大永宁寺 →</a></article></div></section>
<section id="evidence"><h2>空间落位—依据—限制</h2><p class="section-intro">每个图上要素都有稳定编号、图源字段和几何校验值。来源坐标、图示轮廓、报告尺寸片与文献候选位置分别登记；下表可直接返回母图查看。</p><details class="fold" id="features-fold"><summary>展开全部 {len(data['features'])} 个图上要素的依据</summary><div class="table-wrap"><table><thead><tr><th>图上构件</th><th>表达方式</th><th>落位与限制</th><th>共同坐标</th></tr></thead><tbody>{feature_rows}</tbody></table></div></details></section>
<section id="coverage"><h2>全部对象都有交代</h2><p class="section-intro">339项是完整名录，不是339座建筑。能关联来源几何或进入候选布局的对象可回到图上；其余保留所属、时相与缺口，不以填满画面代替证据。</p><details class="fold" id="coverage-fold"><summary>展开全部对象与未定位名录</summary><div class="table-tools"><label class="control search">筛查名录<input id="coverage-search" type="search" placeholder="名称、原编号或位置说明"></label><label class="control">图面去向<select id="coverage-kind"><option value="all">全部对象</option>{summaries}</select></label><button id="coverage-reset" class="plain-button" type="button">重置</button><span id="coverage-count" class="count" data-visible-count="{len(data['coverage'])}">显示 {len(data['coverage'])} / {len(data['coverage'])} 项</span></div><div class="table-wrap"><table><thead><tr><th>名录对象</th><th>本轮去向</th><th>时相与位置限制</th></tr></thead><tbody>{coverage_rows}</tbody></table></div><p id="coverage-empty" class="empty-message" hidden>没有匹配对象。可清空搜索或切回全部对象。</p></details></section>
<section id="relations"><h2>方向约束与尚未闭合的关系</h2><p class="section-intro">南、北、东、西关系用于校核候选位置。所属、同源、记述次序不转换成距离、道路或院墙；无法评估或仍冲突的关系保留在表中。</p><details class="fold"><summary>展开 {len(data['constraints'])} 条关系及本轮处理</summary><div class="table-wrap"><table><thead><tr><th>关系</th><th>本轮评估</th><th>回查记录</th></tr></thead><tbody>{constraints}</tbody></table></div></details><div class="limit-note">本轮完成了共同工作坐标与可回查的落图系统。全城全部建筑的真实轮廓尚无完整史料支持；未知坊墙、院界、房基、道路连续段和北魏河岸不因统一坐标而自动得到证明。</div></section>
<section id="method"><h2>图源与共同坐标的读法</h2><p class="section-intro">{h(fit_note)}</p><ul class="source-list">{sources}</ul><details class="fold"><summary>查看接入方法、变换与差异记录</summary><div class="technical"><p>母图单位为米，来自既有西安1980来源图局部投影；没有转换成WGS84。局部轮廓等比接入，文字候选位置使用公开的工作拟合。数值小数位用于复算，不代表原址精度。</p><h3>各局部图接入约定</h3><pre>{h(bindings)}</pre><h3>尺度差异与约束诊断</h3><pre>{h(diagnostics)}</pre></div></details></section>
<section id="downloads"><h2>带走图纸与逐项证据</h2><p class="section-intro">全城图、局部图和十一片区图共享几何；JSON保留原始工作坐标与来源，CSV便于继续核验。离线包内含网页、全部图纸与表格。</p><div class="download-grid">{dl}</div></section>
<footer class="footer"><p>R11.1 · 516–528年盛时综合 · 首页图像继续保留已批准的V12。研究进展与正式发布验收分别登记。</p><p>构建提交：<a href="https://github.com/mechgouki/luoyang-city/commit/{h(data['source_commit'])}">{h(data['source_commit'])}</a> · <a href="https://github.com/mechgouki/luoyang-city/issues/52">完整交接</a> · <a href="{DATA}">数据与依据</a></p></footer></main><script id="plan-data" type="application/json">{embedded}</script></body></html>'''
