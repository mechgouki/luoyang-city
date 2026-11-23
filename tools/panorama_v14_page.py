"""A full-frame candidate, common-plane projection, and auditable change guide."""
from html import escape
from pathlib import PurePosixPath

from panorama_v14_contract import FOLDER, MANIFEST, RECORD


def make_page(data, downloads):
    candidate, images = data["candidate"], data["images"]
    rejected = candidate["status"] == "needs_revision"
    assert data["status"] == candidate["status"]
    title = "V14试绘审查·未通过" if rejected else "V14 空间校正版候选"
    heading = title if rejected else "盛时洛阳，空间校正版 V14"
    lead = ("共同平面与透视底稿已形成可复算的布局依据；本轮试绘仍未通过空间与形制核查。以下公开实际偏差、逐项依据和试绘过程。" if rejected else
            "先从共同平面投出布局底稿，再回到全景，检查永宁寺、阊阖门与宫城的空间关系。")
    status_heading = "V14试绘审查·未通过" if rejected else "候选图 · 待审看"
    status_text = ("当前首页继续采用已批准的 V12。V14 是未通过的试绘样张，不能作为已完成空间校正的成果或替换首页的候选。" if rejected else
                   "当前首页仍采用已批准的 V12。这里同时呈现新候选、改图基础和当前首页，便于集中比较。")
    button_label = "V14试绘·未通过" if rejected else "V14 新候选"
    change_title = "空间判断与试绘结果对照" if rejected else "空间判断与图面变化对照"
    change_note = ("已试改但未通过的对象分别列出实际偏差，底稿成立不代表试绘达标。窄屏可横向查看完整表格。" if rejected else
                   "每一项区分本轮实际改变、沿用关系和仍未落定的部分。窄屏可横向查看完整表格。")
    details_title = "逐项核对：依据、试改与未通过之处" if rejected else "这次为什么这样改"
    download_title = "下载未通过试绘、底稿与审查依据" if rejected else "下载候选、底稿与依据"
    names = {"v14": "V14 试绘样张 · 未通过" if rejected else "V14 · 空间校正版候选", "v13r2": "V13 二修 · 改图基础", "v12": "V12 · 当前首页"}
    captions = {
        "v14": ("本张试绘仍有阻断问题，尚未达到共同平面布局与形制要求；完整保留以便核对失败原因。" if rejected else
                "以共同坐标平面与透视底稿约束布局，实际改变与剩余差异逐项列明。"),
        "v13r2": "保留已核的南门三层、九层塔与寺墙从属，比较本轮空间变化。",
        "v12": "已批准的全幅首页图；本次候选审看保留其批准状态。",
    }
    figures = []
    for kind in ("v14", "v13r2", "v12"):
        item = images[kind]
        alt = candidate["alt"] if kind == "v14" else names[kind] + "，完整原幅供对照。"
        figures.append(f'''<figure id="figure-{kind}" class="panorama-figure" data-version="{kind}">
<picture><source media="(max-width: 700px)" srcset="./{item['small']}"><img src="./{item['full']}" width="{item['width']}" height="{item['height']}" alt="{escape(alt, quote=True)}" data-revision="{item['revision']}" {'fetchpriority="high"' if kind == 'v14' else ''}></picture>
<figcaption><strong>{names[kind]}</strong><span>{captions[kind]}</span></figcaption></figure>''')
    guides = []
    for role in ("projection_overview", "projection_yongning", "massing_display", "alignment_audit"):
        for item in data["supporting_assets"]:
            if item["role"] != role:
                continue
            guides.append(f'''<figure id="guide-{escape(item['id'], quote=True)}" class="projection-figure" data-role="{role}" data-source-sha256="{item['sha256']}">
<a class="guide-open" href="./{escape(item['published_path'], quote=True)}" aria-label="打开{escape(item['title'], quote=True)}原图"><img src="./{escape(item['published_path'], quote=True)}" alt="{escape(item['title'] + '。' + item['description'], quote=True)}" loading="lazy"></a>
<figcaption><strong>{escape(item['title'])}</strong><p>{escape(item['description'])}</p><a href="./{escape(item['published_path'], quote=True)}">打开完整底稿</a></figcaption></figure>''')
    blockers = ""
    if rejected:
        assert data["blocking_findings"], "Rejected trial must show its actual blockers before the image"
        entries = "".join(f'<li data-blocking-index="{i}">{escape(text)}</li>' for i, text in enumerate(data["blocking_findings"]))
        blockers = f'''<section id="blocking-findings" class="wrap blocking-findings" aria-labelledby="blocking-findings-title">
<h2 id="blocking-findings-title">本次试绘未通过的原因</h2><p>以下为当前样张的实际审查结果。共同透视底稿与来源依据保持可回查；这些偏差尚未解决。</p><ul>{entries}</ul>
<p><a href="./{FOLDER}/candidate-review.json">查看本张完整审查</a> · <a href="#change-table">逐项对照依据与试改结果</a></p></section>'''
    labels = {"changed": "本轮改变", "retained": "沿用并复核", "not_located": "仍不具体定位", "attempted_not_accepted": "已试改，未通过"}
    changes, rows = [], []
    for item in candidate["changes"]:
        links = " · ".join(f'<a href="{escape(link["url"], quote=True)}">{escape(link["label"])}</a>' for link in item["evidence_links"])
        changes.append(f'''<article id="change-{escape(item['id'], quote=True)}" class="change-card" tabindex="-1" data-treatment="{item['treatment_type']}">
<p class="treatment-label">{labels[item['treatment_type']]}</p><h3>{escape(item['title'])}</h3>
<dl><div><dt>实际成图观察</dt><dd>{escape(item['observation'])}</dd></div><div><dt>来源与空间依据</dt><dd>{escape(item['evidence'])}</dd></div><div><dt>画面采用的处理</dt><dd>{escape(item['change'])}</dd></div><div><dt>仍不能确定</dt><dd>{escape(item['limitation'])}</dd></div></dl>
<p class="source-links">{links}</p><a class="back-to-image" href="#comparison">返回全幅对照</a></article>''')
        rows.append(f'<tr data-treatment="{item["treatment_type"]}"><th scope="row"><a href="#change-{escape(item["id"], quote=True)}">{escape(item["title"])}</a></th><td>{labels[item["treatment_type"]]}</td><td>{escape(item["evidence"])}</td><td>{escape(item["change"])}</td><td>{escape(item["limitation"])}</td></tr>')
    attempts = [item for item in data["supporting_assets"] if item["role"] == "attempt_review"]
    history = ""
    if attempts:
        cards = "".join(f'<li id="attempt-{escape(item["id"], quote=True)}" data-attempt-review="{escape(item["id"], quote=True)}"><h3>{escape(item["title"])}</h3><p>{escape(item["description"])}</p><a href="./{escape(item["published_path"], quote=True)}">回查本次试绘完整审查</a></li>' for item in attempts)
        history = f'<section id="attempt-history" class="wrap evidence-section" aria-labelledby="attempt-history-title"><h2 id="attempt-history-title">{len(attempts)} 次试绘审查记录</h2><p>每轮保留自己的实际观察、问题与图像身份；后续试绘不覆盖先前记录。</p><ol class="attempt-history-list">{cards}</ol></section>'
    limits = "".join(f"<li>{escape(text)}</li>" for text in candidate["remaining_limits"])
    download_names = {images["v14"]["full"]: "未通过试绘全幅 WebP" if rejected else "V14 全幅 WebP", data["source_png"]: "未通过试绘原始 PNG" if rejected else "V14 原始 PNG", RECORD: "试绘与依据完整记录" if rejected else "候选与依据完整记录", FOLDER + "/generation-prompts.txt": "实际绘图说明", FOLDER + "/candidate-review.json": "实际成图审查", FOLDER + "/visual-audit.json": "独立视觉审查", MANIFEST: "版本与文件清单"}
    download_names.update({x["published_path"]: x["title"] for x in data["supporting_assets"]})
    files = "".join(f'<a download href="./{escape(path, quote=True)}">{escape(download_names.get(path, PurePosixPath(path).name))}</a>' for path in downloads)
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>盛时洛阳 · {title}</title><meta name="description" content="{title}：R11共同平面、可复算透视底稿、V14与V13二修及V12完整对照，逐项审查结果与来源依据。">
<link rel="stylesheet" href="./{FOLDER}/review.css"><script defer src="./{FOLDER}/review.js"></script></head>
<body data-image-status="{data['status']}" data-review-status="{data['review_status']}"><a class="skip-link" href="#main">跳到正文</a><header class="site-header"><nav class="wrap" aria-label="网站导航"><a class="brand" href="./index.html">盛时洛阳</a><div><a href="./luoyang-city-plan.html#plan-reader">共同坐标平面</a><a href="./luoyang-panorama-v13-r2.html">V13 二修记录</a><a href="./luoyang-city-nodes.html#register">逐段证据</a></div></nav></header>
<main id="main"><div class="intro wrap"><p class="eyebrow">共同平面与试绘审查 · R12.1</p><h1>{heading}</h1>
<p class="lead">{lead}</p>
<p class="review-status" id="review-status" data-status="{data['status']}"><strong>{status_heading}</strong> {status_text}</p>
<p class="reading-path"><a href="#projection">查看透视布局底稿</a><a href="#change-table">查看改动对照表</a><a href="#changes">回查逐项依据</a></p></div>
{blockers}
<section id="comparison" aria-labelledby="comparison-title"><div class="section-heading wrap"><div><h2 id="comparison-title">完整画面对照</h2><p>三幅图保持各自完整比例；并排模式比较 V14 与 V13 二修。</p></div>
<div id="view-controls" class="view-controls" role="group" aria-label="选择对照方式" hidden><button type="button" data-view="v14" aria-pressed="true">{button_label}</button><button type="button" data-view="v13r2" aria-pressed="false">V13 二修</button><button type="button" data-view="v12" aria-pressed="false">V12 首页</button><button type="button" data-view="compare" aria-pressed="false">前后并排</button></div></div>
<div id="image-comparison" class="image-comparison" data-image-status="{data['status']}">{''.join(figures)}</div><p id="view-status" class="wrap view-status" aria-live="polite">{'V14试绘审查未通过。' if rejected else ''}无脚本时，三幅完整图依次展示。</p></section>
<section id="projection" class="wrap projection-section" aria-labelledby="projection-title"><div class="section-heading"><div><p class="eyebrow">先看布局，再看成图</p><h2 id="projection-title">从共同平面到透视底稿</h2><p>底稿保留来源几何及其证据身份；全景是否遵循底稿，须逐项查看实际成图。</p></div></div>
<div class="evidence-levels"><article><h3>原图内部比例</h3><p>同一来源图中的门、塔座、佛殿与墙段采用同一尺度，作为局部布局约束。</p></article><article><h3>艺术构图位置</h3><p>透视视点、画面投影和上部建筑表现服务于阅读；它们不产生新的实测坐标。</p></article><article><h3>待核的外部落位</h3><p>局部图接入全城仍属候选绑定。共同坐标、内部比例与原址精度分别登记。</p></article></div>
<div class="projection-grid">{''.join(guides)}</div><p class="detail-note">宫城2013图中的调查标记、版筑范围和不明时相线条保留其来源角色；外郭相关遗存范围与片区视窗也不自动成为城墙或坊界。</p>
<p><a href="./luoyang-city-plan.html?view=yongning#plan-reader">回到永宁寺共同平面</a> · <a href="./luoyang-city-plan.html?view=changhe#plan-reader">回到阊阖门共同平面</a></p></section>
<section id="change-table" class="wrap evidence-section" aria-labelledby="change-table-title"><div class="section-heading"><div><h2 id="change-table-title">{change_title}</h2><p>{change_note}</p></div></div><div class="table-scroll" tabindex="0" role="region" aria-label="可横向滚动的改动对照表"><table><thead><tr><th scope="col">对象</th><th scope="col">本轮状态</th><th scope="col">来源与空间依据</th><th scope="col">画面处理</th><th scope="col">保留的限制</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
<section id="changes" class="wrap evidence-section" aria-labelledby="changes-title"><div class="section-heading"><div><p class="eyebrow">成图与来源逐项核对</p><h2 id="changes-title">{details_title}</h2><p>观察写的是实际生成结果；来源说明与不能确定的部分同时保留。</p></div></div><div class="changes-grid">{''.join(changes)}</div></section>
{history}
<section id="limits" class="wrap limits-section" aria-labelledby="limits-title"><h2 id="limits-title">仍需保留的研究边界</h2><p>画面采用516—528年的综合研究窗口。共同工作平面与艺术全景均不能替代遗址测绘，未获依据的建筑边界继续待证。</p><ul>{limits}</ul><p><a href="./luoyang-city-plan.html#coverage">查看全量名录与定位状态</a> · <a href="./luoyang-city-plan.html#plan-reader">回查共同坐标母图</a></p></section>
<section id="downloads" class="wrap downloads-section" aria-labelledby="downloads-title"><h2 id="downloads-title">{download_title}</h2><div class="download-links">{files}</div></section>
</main><footer class="wrap"><p>盛时洛阳 · {title} · 研究 R12.1</p><p>{'当前首页继续采用 V12；V14 尚未通过空间与形制核查。' if rejected else '本页保留当前首页 V12 的批准状态，新候选供具体审看。'}</p></footer></body></html>'''
