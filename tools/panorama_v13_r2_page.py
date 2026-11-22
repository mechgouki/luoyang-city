"""Three intact images, equal-scale gate views, and traceable spatial decisions."""
from html import escape
from panorama_v13_r2_contract import FOLDER, MANIFEST, RECORD


def make_page(data, downloads):
    candidate, images = data['candidate'], data['images']
    names = {'v13r2': 'V13 二修 · 本轮候选', 'v13': 'V13 前版 · 上轮候选', 'v12': 'V12 · 当前首页'}
    captions = {'v13r2': '结合本轮城市空间判断进一步修订，供集中审看。',
                'v13': '保留上一轮九层塔候选，便于比较本轮实际变化。',
                'v12': '已批准的全幅首页图，首页继续采用此版。'}
    figures = []
    for kind in ('v13r2', 'v13', 'v12'):
        im = images[kind]
        alt = candidate['alt'] if kind == 'v13r2' else names[kind] + '，完整原幅供对照。'
        figures.append(f'''<figure id="figure-{kind}" class="panorama-figure" data-version="{kind}">
<picture><source media="(max-width: 700px)" srcset="./{im['small']}"><img src="./{im['full']}" width="{im['width']}" height="{im['height']}" alt="{escape(alt, quote=True)}" data-revision="{im['revision']}" {'fetchpriority="high"' if kind == 'v13r2' else ''}></picture>
<figcaption><strong>{names[kind]}</strong><span>{captions[kind]}</span></figcaption></figure>''')
    detail = candidate['detail_view']
    details = []
    for kind in ('v13r2', 'v13'):
        im, pos = images[kind], detail['views'][kind]
        details.append(f'''<figure class="detail-figure" id="detail-{kind}" data-source-sha256="{im['full_sha256']}">
<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="detail-title-{kind}" viewBox="{pos['x']} {pos['y']} {detail['width']} {detail['height']}" width="{detail['width']}" height="{detail['height']}" preserveAspectRatio="xMidYMid meet">
<title id="detail-title-{kind}">{names[kind]}：南门及相邻寺墙原图局部</title><image href="./{im['full']}" x="0" y="0" width="{im['width']}" height="{im['height']}" preserveAspectRatio="xMinYMin meet"/></svg>
<figcaption><strong>{names[kind]}</strong><span>同倍率观察南门、寺墙与前方道路。</span></figcaption></figure>''')
    treatment_names = {'changed': '本轮改变', 'retained': '沿用并复核', 'not_located': '仍不具体落点'}
    changes = []
    for item in candidate['changes']:
        links = ' · '.join(f'<a href="{escape(link["url"], quote=True)}">{escape(link["label"])}</a>' for link in item['evidence_links'])
        label = treatment_names.get(item.get('treatment_type'))
        badge = f'<p class="treatment-label">{label}</p>' if label else ''
        changes.append(f'''<article class="change-card" id="change-{escape(item['id'], quote=True)}" tabindex="-1">{badge}
<h3>{escape(item['title'])}</h3><p class="observation">{escape(item['observation'])}</p>
<dl><div><dt>依据</dt><dd>{escape(item['evidence'])}</dd></div><div><dt>画面采用的处理</dt><dd>{escape(item['change'])}</dd></div><div><dt>尚不能确定</dt><dd>{escape(item['limitation'])}</dd></div></dl>
<p class="source-links">{links}</p><a class="back-to-image" href="#comparison">返回全幅对照</a></article>''')
    limits = ''.join(f'<li>{escape(text)}</li>' for text in candidate['remaining_limits'])
    file_labels = {images['v13r2']['full']: 'V13 二修全幅图', RECORD: '图面判断与依据',
                   FOLDER + '/generation-prompt.txt': '本轮完整绘图说明', FOLDER + '/source-audit.json': '原件续查记录',
                   FOLDER + '/candidate-review.json': '本张成图审查', FOLDER + '/visual-audit.json': '图面独立复核',
                   MANIFEST: '版本与文件清单'}
    files = ''.join(f'<a download href="./{escape(path, quote=True)}">{escape(file_labels.get(path, path.rsplit("/", 1)[-1]))}</a>' for path in downloads)
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>盛时洛阳 · V13 二修候选审看</title><meta name="description" content="V13二修候选与前版及当前首页V12的完整对照：同倍率观察永宁寺南门与寺墙，逐项回查城市空间判断。">
<link rel="stylesheet" href="./{FOLDER}/review.css"><script defer src="./{FOLDER}/review.js"></script></head>
<body><a class="skip-link" href="#main">跳到正文</a><header class="site-header"><nav class="wrap" aria-label="网站导航"><a class="brand" href="./index.html">盛时洛阳</a><div><a href="./luoyang-city-spatial.html">城市空间总图</a><a href="./luoyang-city-spatial.html#decision-SP01">空间判断对照表</a><a href="./luoyang-city-nodes.html#register">逐段证据</a></div></nav></header>
<main id="main"><div class="intro wrap"><p class="eyebrow">城市空间与全景 · R9.1</p><h1>盛时洛阳，全景二修 V13</h1>
<p class="lead">从城市空间总图回到画面，逐项核对南门、寺墙与道路的关系。</p>
<p class="review-status" id="review-status"><strong>候选图 · 待审看</strong> 当前首页仍采用已批准的 V12。本页提供本轮候选、前版 V13 与 V12 的完整对照。</p>
<p class="reading-path"><a href="#gate-detail">观察南门与寺墙</a><a href="#changes">查看改图依据</a><a href="./luoyang-city-spatial.html#decision-SP01">回到20项空间判断</a></p></div>
<section id="comparison" aria-labelledby="comparison-title"><div class="section-heading wrap"><div><h2 id="comparison-title">完整画面对照</h2><p>保留原幅比例；并排模式比较本轮二修与前版 V13。</p></div>
<div id="view-controls" class="view-controls" role="group" aria-label="选择对照方式" hidden><button type="button" data-view="v13r2" aria-pressed="true">V13 二修</button><button type="button" data-view="v13" aria-pressed="false">V13 前版</button><button type="button" data-view="v12" aria-pressed="false">V12 首页</button><button type="button" data-view="compare" aria-pressed="false">前后并排</button></div></div>
<div id="image-comparison" class="image-comparison">{''.join(figures)}</div><p id="view-status" class="wrap view-status" aria-live="polite">无脚本时，三幅完整图依次展示。</p></section>
<section id="gate-detail" class="wrap detail-section" aria-labelledby="gate-detail-title"><div class="section-heading"><div><p class="eyebrow">局部审看</p><h2 id="gate-detail-title">南门、寺墙与前方道路</h2><p>{escape(detail['caption'])}</p></div></div><div class="detail-grid">{''.join(details)}</div>
<p class="detail-note">两处局部采用相同的原图像素范围尺寸与显示比例，仅用于观察原图；门楼形制与它所依附的院墙应一起判断。</p><p><a href="#comparison">返回完整画面</a> · <a href="./luoyang-city-spatial.html#decision-SP02">门南道西的空间依据</a> · <a href="./luoyang-city-nodes.html#map-palace-yongning">宫前与永宁寺逐项核验</a></p></section>
<section id="changes" class="wrap evidence-section" aria-labelledby="changes-title"><div class="section-heading"><div><p class="eyebrow">从判断到画面</p><h2 id="changes-title">本轮采用了哪些依据</h2><p>区分实际改变、沿用并复核的关系，以及仍不能在画面中具体定位的对象。</p></div></div><div class="changes-grid">{''.join(changes)}</div></section>
<section id="limits" class="wrap limits-section" aria-labelledby="limits-title"><h2 id="limits-title">这张复原图仍有哪些边界</h2><p>研究窗口为516—528年。城市空间图负责区分位置、关系与未定对象；艺术全景本身不产生新的考古坐标、古岸或测绘线。</p><ul>{limits}</ul><p><a href="./luoyang-city-spatial.html">查看深化后的空间总图</a> · <a href="./luoyang-city-nodes.html#register">回查逐段来源</a> · <a href="./luoyang-panorama-v13.html">查看前版V13完整审看记录</a></p></section>
<section id="downloads" class="wrap downloads-section" aria-labelledby="downloads-title"><h2 id="downloads-title">下载本轮候选与依据</h2><div class="download-links">{files}</div></section>
</main><footer class="wrap"><p>盛时洛阳 · V13 二修候选 · 研究 R9.1</p><p>首页换图仍需对这张具体候选作出确认；本页发布保留 V12 的批准状态。</p></footer></body></html>'''
