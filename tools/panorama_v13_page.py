"""A full-frame candidate review with evidence beside, never over, the artwork."""
from html import escape

from panorama_v13_contract import FOLDER, MANIFEST, RECORD


def make_page(data, downloads):
    candidate = data["candidate"]
    images = data["images"]

    def picture(kind, title, caption, alt):
        im = images[kind]
        return f'''<figure id="figure-{kind}" class="panorama-figure" data-version="{kind}">
<picture><source media="(max-width: 700px)" srcset="./{im['small']}"><img src="./{im['full']}" width="{im['width']}" height="{im['height']}" alt="{escape(alt, quote=True)}" data-revision="{im['revision']}" fetchpriority="high"></picture>
<figcaption><strong>{escape(title)}</strong><span>{escape(caption)}</span></figcaption></figure>'''

    figures = picture("v13", "V13 · 候选全景", "依据近期核验校订，待你审看后决定是否用于首页。", candidate["alt"])
    figures += picture("v12", "V12 · 当前首页", "保留已批准的全幅取景版，供逐项对照。", "当前首页V12：宫城、永宁寺、街道、南城门、洛水与完整浮桥的研究性全景。")
    changes = []
    for item in candidate["changes"]:
        links = " · ".join(f'<a href="{escape(link["url"], quote=True)}">{escape(link["label"])}</a>' for link in item["evidence_links"])
        changes.append(f'''<article class="change-card" id="change-{escape(item['id'], quote=True)}" tabindex="-1">
<h3>{escape(item['title'])}</h3><p class="observation">{escape(item['observation'])}</p>
<dl><div><dt>依据</dt><dd>{escape(item['evidence'])}</dd></div><div><dt>图面处理</dt><dd>{escape(item['change'])}</dd></div><div><dt>仍须保留</dt><dd>{escape(item['limitation'])}</dd></div></dl>
<p class="source-links">{links}</p><a class="back-to-image" href="#comparison">返回全景对照</a></article>''')
    limits = "".join(f"<li>{escape(item)}</li>" for item in candidate["remaining_limits"])
    file_labels = {images["v13"]["full"]: "V13 全幅图", RECORD: "图面改动与依据", FOLDER + "/generation-prompt.txt": "本版绘图说明", FOLDER + "/source-audit.json": "原件核读记录", FOLDER + "/visual-audit.json": "V12 图面核查", FOLDER + "/candidate-review.json": "V13 成图核查", MANIFEST: "版本与文件清单"}
    files = "".join(f'<a download href="./{escape(path, quote=True)}">{escape(file_labels.get(path, path.rsplit("/", 1)[-1]))}</a>' for path in downloads)
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>盛时洛阳 · V13 全景校订审看</title><meta name="description" content="根据城市节点核验校订的北魏洛阳全景候选图：对照V12，逐项阅读改图依据与尚未确定的空间关系。">
<link rel="stylesheet" href="./{FOLDER}/review.css"><script defer src="./{FOLDER}/review.js"></script></head>
<body><a class="skip-link" href="#main">跳到正文</a>
<header class="site-header"><nav class="wrap" aria-label="网站导航"><a class="brand" href="./index.html">盛时洛阳</a><div><a href="./luoyang-city-nodes.html#overview">城市节点联读</a><a href="./luoyang-city-nodes.html#panorama">V12 画面依据</a><a href="#changes">本次校订</a></div></nav></header>
<main id="main"><div class="intro wrap"><p class="eyebrow">城市证据与全景 · R8.1</p><h1>盛时洛阳，全景校订 V13</h1>
<p class="lead">把近期核验中能够成立的空间关系落实到画面，再把尚无定论的地方交代清楚。</p>
<p class="review-status" id="review-status"><strong>候选图 · 待审看</strong> 当前首页仍采用已批准的 V12。本页先提供完整新图及对照依据。</p></div>
<section id="comparison" aria-labelledby="comparison-title"><div class="section-heading wrap"><div><h2 id="comparison-title">全幅对照</h2><p>两幅图均按原始比例展示，切换时可对照同一地段。</p></div>
<div id="view-controls" class="view-controls" role="group" aria-label="选择对照方式" hidden><button type="button" data-view="v13" aria-pressed="true">V13 候选</button><button type="button" data-view="v12" aria-pressed="false">V12 当前</button><button type="button" data-view="compare" aria-pressed="false">并排对照</button></div></div>
<div id="image-comparison" class="image-comparison">{figures}</div><p id="view-status" class="wrap view-status" aria-live="polite">无脚本时，两幅完整图依次展示。</p></section>
<section id="changes" class="wrap evidence-section" aria-labelledby="changes-title"><div class="section-heading"><div><p class="eyebrow">从依据到画面</p><h2 id="changes-title">本次具体校订</h2><p>下面记录成图中实际采用的处理；每项保留依据与不能推出的结论。</p></div></div><div class="changes-grid">{''.join(changes)}</div></section>
<section id="limits" class="wrap limits-section" aria-labelledby="limits-title"><h2 id="limits-title">怎样理解这张复原图</h2><p>研究窗口仍为516—528年。这是一张受证据约束的艺术全景；画面细节本身不成为新的考古证据，也不新增古代坐标或古岸测线。</p><ul>{limits}</ul><p><a href="./luoyang-city-nodes.html#register">回查逐段证据</a> · <a href="./prosperity-city-atlas.html">查看城市分布图</a> · <a href="./luoyang-water-atlas.html">查看水系定位依据</a></p></section>
<section id="downloads" class="wrap downloads-section" aria-labelledby="downloads-title"><h2 id="downloads-title">下载本版图像与依据</h2><div class="download-links">{files}</div></section>
</main><footer class="wrap"><p>盛时洛阳 · 全景候选 V13 · 研究 R8.1</p><p>首页换图需在这张具体候选图审看后确认；本页发布不改变 V12 的批准状态。</p></footer></body></html>'''
