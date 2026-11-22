"""Publish a unified reading atlas and twenty auditable spatial decisions."""
import copy
import csv
import hashlib
import html
import json
import shutil
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from city_spatial_r9_maps import VIEWS, build_map
from homepage_artwork_v10 import V12

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research/city-spatial-r9"
BASE = "https://mechgouki.github.io/luoyang-city/"
KEY = "city_spatial_r9"
VERSION = "city-spatial-r9"
PAGE = "luoyang-city-spatial.html"
FOLDER = "city-spatial-r9"
MANIFEST = FOLDER + "/manifest.json"
BUNDLE = "downloads/city-spatial-r9.zip"
NODES = [("palace-yongning", "宫前与永宁"), ("baima", "白马寺坊街"), ("sima", "司马门与仓区"), ("jianchun", "建春门桥渠")]
BASIS = {"source": "来源图位置", "relation": "文献／报告关系", "unknown": "仍待定位"}
CSV_FIELDS = ["id", "node_id", "node_title", "title", "evidence_classes", "previous_expression", "judgment", "evidence", "map_change", "remaining_unknown", "panorama_action", "prior_finding_ids", "road_ids", "water_ids", "source_inputs", "anchor_kind"]


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pointer(document, path):
    node = document
    for token in path.strip("/").split("/") if path else ():
        token = token.replace("~1", "/").replace("~0", "~")
        node = node[int(token)] if isinstance(node, list) else node[token]
    return node


def build_data(site, source_commit):
    data = copy.deepcopy(load(DATA / "decisions.json"))
    data["source_commit"] = source_commit
    data["implementation_version"] = VERSION
    data["nodes"] = [dict(id=key, title=title) for key, title in NODES]
    data["evidence_basis_status"] = "R9复用R7已核判断并改善图面；本轮原件续查见source-audit.json；没有新增历史定位或证据等级升级。"
    data["source_frames_registered_together"] = False
    data["new_historical_coordinates"] = 0
    data["new_shoreline_geometries"] = 0
    data["evidence_grade_upgrades"] = 0
    data["homepage_revision"] = "panorama-approved-v12"
    data["homepage_replacement_approved"] = False
    data["map_views"] = VIEWS
    sources = {}
    source_hashes = {"research/city-spatial-r9/decisions.json": sha(DATA / "decisions.json")}
    reviews = {}
    for key, title in NODES:
        path = ROOT / "research/city-nodes-r7/reviews" / (key + ".json")
        reviews[key] = load(path)
        source_hashes[str(path.relative_to(ROOT))] = sha(path)
        for src in reviews[key]["source_refs"]:
            src = copy.deepcopy(src)
            src["provenance_stage"] = "R7.1"
            src["prior_access_status"] = src.pop("access_status")
            src["prior_checked_on"] = src.pop("checked_on")
            sources[src["id"]] = src
    for row in data["decisions"]:
        review = reviews[row["node_id"]]
        row["node_title"] = dict(NODES)[row["node_id"]]
        findings = [f for f in review["findings"] if f["id"] in row["prior_finding_ids"]]
        assert len(findings) == len(row["prior_finding_ids"])
        row["road_ids"] = sorted({rid for f in findings for rid in f.get("road_ids", [])})
        row["water_ids"] = sorted({wid for f in findings for wid in f.get("water_ids", [])})
        inputs = []
        for finding in findings:
            index = next(i for i, f in enumerate(review["findings"]) if f["id"] == finding["id"])
            inputs.append(dict(path="research/city-nodes-r7/reviews/" + row["node_id"] + ".json", pointer="/findings/" + str(index)))
            inputs.extend(copy.deepcopy(finding["source_inputs"]))
        seen = set()
        row["source_inputs"] = []
        for item in inputs:
            token = (item["path"], item["pointer"])
            if token in seen:
                continue
            seen.add(token)
            path = ROOT / item["path"]
            pointer(load(path), item["pointer"])
            item["sha256"] = sha(path)
            source_hashes[item["path"]] = item["sha256"]
            row["source_inputs"].append(item)
        text_checks = [t for t in review.get("text_checks", []) if t["id"] in row.get("text_check_ids", [])]
        evidence = []
        for sid in dict.fromkeys(sid for f in findings for sid in f["source_ids"]):
            source = sources[sid]
            quoted = [t for t in text_checks if sid in t["source_ids"]]
            evidence.append(dict(source_id=sid, title=source["title"], url=source["url"],
                                 locator="；".join(t["locator"] for t in quoted) if quoted else source["locator"],
                                 excerpt_or_summary="\n".join(t["excerpt"] for t in quoted) if quoted else "；".join(f["claim"] for f in findings if sid in f["source_ids"]),
                                 quote_kind="classical_text_quote" if quoted else "prior_review_summary",
                                 provenance_stage="R7.1", access_note=source["prior_access_status"],
                                 original_figure_url=source.get("figure_url")))
        row["evidence"] = evidence
        row["geometry_changed"] = False
        row["evidence_grade_upgraded"] = False
        row["prior_review_url"] = BASE + "luoyang-city-nodes.html#finding-" + row["prior_finding_ids"][0]
    for filename in ["research/prosperity-v1/geographic-evidence.json", "research/prosperity-r5/sima-road.json"]:
        source_hashes[filename] = sha(ROOT / filename)
    audit = DATA / "source-audit.json"
    if audit.exists():
        source_hashes[str(audit.relative_to(ROOT))] = sha(audit)
        data["source_audit"] = FOLDER + "/source-audit.json"
    data["sources"] = list(sources.values())
    data["source_inputs_sha256"] = source_hashes
    data["published_inputs_sha256"] = {"city-atlas/atlas.json": sha(site / "city-atlas/atlas.json"),
                                       "city-nodes/readings.json": sha(site / "city-nodes/readings.json")}
    data["counts"] = dict(nodes=4, decisions=len(data["decisions"]), source_features=sum(not f["id"].startswith("geo-modern-") for f in load(site / "city-atlas/atlas.json")["features"]),
                          existing_findings_reused=len({f for row in data["decisions"] for f in row["prior_finding_ids"]}),
                          sources=len({e["source_id"] for row in data["decisions"] for e in row["evidence"]}),
                          source_sima_atomic_lines=len(load(ROOT / "research/prosperity-r5/sima-road.json")["image"]["sima_road_ink_px"]))
    data["csv_fields"] = CSV_FIELDS
    data["csv_encoding"] = "UTF-8 with BOM; lists and objects are JSON; absence of a coordinate is not a zero coordinate"
    return data


def escape(value):
    return html.escape(str(value), quote=True)


def make_row(row):
    badges = "".join(f'<span class="badge {escape(k)}">{BASIS[k]}</span>' for k in row["evidence_classes"])
    evidence = []
    for index, item in enumerate(row["evidence"]):
        quote = escape(item["excerpt_or_summary"]).replace("\n", "<br>")
        detail = f'<blockquote>{quote}</blockquote>' if item["quote_kind"] == "classical_text_quote" else f'<details><summary>查看既有核验摘要</summary><p>{quote}</p></details>'
        if item.get("original_figure_url"):
            detail += f'<a href="{escape(item["original_figure_url"])}">原图入口</a>'
        evidence.append(f'<div class="evidence-item"><a href="{escape(item["url"])}">{escape(item["title"])}</a><span class="evidence-locator">{escape(item["locator"])}</span>{detail}</div>')
    terms = " ".join([row["id"], row["title"], row["node_title"], row["judgment"], row["map_change"], row["remaining_unknown"], *row["road_ids"], *row["water_ids"], *row["prior_finding_ids"]])
    source_details = "".join(f'<p><a href="https://github.com/mechgouki/luoyang-city/blob/{escape(row.get("source_commit", "main"))}/{escape(item["path"])}">{escape(item["path"])}</a><br>{escape(item["pointer"])}</p>' for item in row["source_inputs"])
    return f'''<tr class="decision-row" id="decision-{row['id']}" tabindex="-1" data-node="{row['node_id']}" data-basis="{' '.join(row['evidence_classes'])}" data-search="{escape(terms)}">
<td data-label="空间判断"><a class="decision-id" href="#decision-{row['id']}">{row['id']}</a><div class="decision-title">{escape(row['title'])}</div><span class="node-label">{escape(row['node_title'])}</span><div class="badges">{badges}</div></td>
<td data-label="本轮采用的判断"><p>{escape(row['judgment'])}</p><details class="prior"><summary>此前表达</summary><p>{escape(row['previous_expression'])}</p></details></td>
<td data-label="原文／原图依据">{''.join(evidence)}<details class="prior"><summary>来源记录与回查指针</summary><p>复用既有核验 {escape('、'.join(row['prior_finding_ids']))}；本轮原件访问状态见来源审计。</p><a href="{escape(row['prior_review_url'])}">返回四节点原核验</a>{source_details}</details></td>
<td data-label="图上改变了什么"><p>{escape(row['map_change'])}</p><p class="prior">全景约束：{escape(row['panorama_action'])}</p></td>
<td data-label="仍不能确定"><p>{escape(row['remaining_unknown'])}</p></td></tr>'''


def make_page(data, svg, downloads, offline=False):
    linkbase = BASE if offline else ""
    rows = []
    for original in data["decisions"]:
        row = dict(original, source_commit=data["source_commit"])
        rows.append(make_row(row))
    options = ''.join(f'<option value="{key}">{title}</option>' for key, title in NODES)
    download_html = []
    for path, name, note in downloads:
        # The ZIP itself is not recursively included in its offline copy.
        href = BASE + path if offline and path == BUNDLE else "./" + path
        download_html.append(f'<a href="{href}" download data-download="{path}">{name}<span>{note}</span></a>')
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="source-commit" content="{escape(data['source_commit'])}"><meta name="description" content="盛时洛阳四处城市节点的空间总图与20项可回查判断：来源图位置、文献关系和仍待定位对象分别呈现。"><title>城市空间总图与证据对照 · 盛时洛阳</title><link rel="stylesheet" href="{FOLDER}/atlas.css"><script src="{FOLDER}/atlas.js" defer></script></head>
<body><a class="skip" href="#overview">跳到城市空间总图</a><div class="topbar"><nav class="shell" aria-label="项目入口"><a href="{linkbase}index.html">盛时洛阳</a><a href="{linkbase}prosperity-city-atlas.html">全城分布图</a><a href="{linkbase}luoyang-city-nodes.html">四节点原核验</a><a href="{linkbase}luoyang-panorama-v13-r2.html">V13修订候选</a></nav></div>
<header class="hero"><div class="shell"><p class="eyebrow">城市空间研究 · R9.1</p><h1>从空间判断，到可回查的城市布局</h1><p>把宫前与永宁、白马寺坊街、司马门与仓区、建春门桥渠接入同一阅读框架。先看城市骨架，再看四处局部如何组织，最后沿20项判断回到原文与原图。</p><nav class="hero-nav" aria-label="本页导航"><a href="#overview">城市空间总图</a><a href="#decisions">判断与图面变化</a><a href="#boundaries">原件与未定边界</a><a href="#downloads">下载与离线阅读</a></nav></div></header>
<main class="shell"><div class="facts"><div><strong>4处节点</strong><span>同一图例，独立来源图框</span></div><div><strong>20项判断</strong><span>每项连接依据、变化与限制</span></div><div><strong>516—528年</strong><span>综合研究窗口，具体使用层分别核验</span></div></div>
<noscript><p class="noscript">脚本未启用：完整总图与20项证据仍可阅读和下载。请使用图上SP编号或浏览器查找进入对应证据行。</p></noscript>
<section id="changes"><h2>这轮具体画清楚了什么</h2><p class="section-intro">本轮把已有核验转化为更清楚的空间组织。图面发生变化，历史定位等级保持原有边界。</p><div class="change-grid">
<article class="change"><h3>宫前：门、寺与路侧</h3><p>门南与道西分别成立；官署不镜像排列，铜驼残段与御道仍保留候选对应。</p><a href="#decision-SP02">查看 SP02—SP05</a></article>
<article class="change"><h3>白马：街、口与交通带</h3><p>中央十字突出，次街断段保留；南口单列，三个宽度分别归到实际对象。</p><a href="#decision-SP06">查看 SP06—SP10</a></article>
<article class="change"><h3>司马：宫院、主路与仓区</h3><p>宫院内部夹道、司马门路和仓区内路分开；仓区两种分区方向各有表达。</p><a href="#decision-SP11">查看 SP11—SP15</a></article>
<article class="change"><h3>建春：桥向、分期与接口</h3><p>东石桥南北通行；三桥各守叙述，水道解释按性质分开，桥头渠口仍待定位。</p><a href="#decision-SP16">查看 SP16—SP20</a></article></div></section>
<section id="overview"><h2>一张总图，逐层阅读</h2><p class="section-intro">主图保持06a来源骨架；四个局部窗说明关系。局部窗的位置与间距是阅读安排，不能据此量取古代距离或拼成共同测绘平面。</p>
<div class="toolbar"><label for="map-view">选择图面<select id="map-view"><option value="all">完整总图</option><option value="source">来源骨架与图例</option>{options}</select></label><div class="buttons"><button id="zoom-in" type="button">放大</button><button id="zoom-out" type="button">缩小</button><button id="reset-map" type="button">复位当前图面</button></div><div class="buttons" aria-label="放大后的图面平移"><button id="pan-left" type="button" aria-label="向左平移图面">左移</button><button id="pan-right" type="button" aria-label="向右平移图面">右移</button><button id="pan-up" type="button" aria-label="向上平移图面">上移</button><button id="pan-down" type="button" aria-label="向下平移图面">下移</button></div></div>
<div class="map-wrap" id="map-viewport" tabindex="0" aria-label="可横向滚动的城市空间总图">{svg}</div><p class="map-note">点图中SP编号、文字或线段，进入对应证据行。手机可横向滚动阅读局部窗；放大后用平移按钮或在图框上按方向键查看边缘。</p><div class="map-legend"><span><i class="swatch"></i>来源图位置</span><span><i class="swatch relation"></i>文献／报告关系</span><span><i class="swatch unknown"></i>仍待定位或解释</span></div></section>
<section id="decisions"><h2>空间判断—依据—图面变化</h2><p class="section-intro">每项判断说明此前怎样表达、本轮采用什么依据、总图怎样改变，以及仍不能确定什么。道路编号沿用原记录；记录数量不等于独立古路数量。</p>
<div class="filter-grid"><label for="search">检索地点、编号或关键词<input id="search" type="search" placeholder="如：太尉府、P01、桥头、7.5" autocomplete="off"></label><label for="node-filter">节点<select id="node-filter"><option value="all">全部节点</option>{options}</select></label><label for="basis-filter">依据性质<select id="basis-filter"><option value="all">全部依据</option>{''.join(f'<option value="{key}">{value}</option>' for key,value in BASIS.items())}</select></label><button id="reset-filters" type="button">清除筛选</button></div>
<div class="filter-status"><span id="result-count" role="status" aria-live="polite" data-visible-count="20">显示 20 / 20 项空间判断</span><span>筛选与图面选择可随网址恢复；每项有独立深链接。</span></div>
<div class="table-wrap"><table id="decisions-table"><caption>来源栏保留原文或既有核验摘要；现代报道、来源图提取与研究解释分别注明，复用核验不等于本轮重获原件。</caption><thead><tr><th scope="col">空间判断</th><th scope="col">本轮采用的判断</th><th scope="col">原文／原图依据</th><th scope="col">图上改变了什么</th><th scope="col">仍不能确定</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div><div class="empty" id="no-results" hidden>没有匹配的判断。可以缩短关键词，或清除节点与依据筛选。</div></section>
<section id="boundaries"><h2>原件续查与明确保留的边界</h2><div class="boundary-grid"><article class="boundary"><h3>1993外郭道路与水道报告</h3><p>原刊602—608页、完整附图、图例及逐路末测点仍未取得。本轮访问目录与阅读入口的实际结果见来源审计；目录、登录页不计作全文。</p></article><article class="boundary"><h3>2011东阳渠、鸿池陂简报</h3><p>已有重印本与馆藏线索，原页和完整图版仍缺。桥头、渠口、古岸以及共同测绘位置保持待证；2022运河报告继续暂缓。</p></article></div><p class="section-intro">本轮新增古代坐标0、古岸几何0、证据等级提升0。城市空间的改善来自已有约束的落实：能画清的关系画清，未定的端点与接口留在图上。</p></section>
<section class="next-image" id="panorama-guide"><div><h2>让全景服从这些空间判断</h2><p>V13修订候选及依据导览集中展示南门修订与本轮城市布局约束。图像中的建筑外观与未测尺度仍属研究性表达；首页替换继续按具体候选审看结果处理。</p></div><a href="{linkbase}luoyang-panorama-v13-r2.html">查看 V13 修订候选</a></section>
<section id="downloads"><h2>下载与离线阅读</h2><p class="section-intro">SVG可放大和分享；CSV保留表格字段；JSON包含逐项来源指针与输入文件校验值。离线包包含本页、总图、完整证据及来源审计。</p><div class="download-grid">{''.join(download_html)}</div></section></main>
<footer class="foot"><div class="shell">研究 R9.1 · 实现 city-spatial-r9 · 来源提交 <code>{escape(data['source_commit'])}</code><br>继承 R7四节点核验与R8候选审看基线；原文、遗迹提取、研究解释和艺术画面各保留其证据性质。</div></footer><script type="application/json" id="map-views">{json.dumps(VIEWS, ensure_ascii=False)}</script></body></html>'''


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(row.get(key), ensure_ascii=False) if isinstance(row.get(key), (list, dict)) or row.get(key) is None else row[key] for key in CSV_FIELDS})


def build(site=ROOT / "_site"):
    site = Path(site)
    info = load(site / "build-info.json")
    old_meta = info.get(KEY)
    if old_meta:
        prior = old_meta["predecessor_release"]
        release_bytes = (site / prior["path"]).read_bytes()
        assert hashlib.sha256(release_bytes).hexdigest() == prior["sha256"], "R9 predecessor release changed"
    else:
        release_bytes = (site / "release.json").read_bytes()
    dest = site / FOLDER
    dest.mkdir(parents=True, exist_ok=True)
    history = dest / "history"
    history.mkdir(exist_ok=True)
    previous_release = history / "release-before-r9.json"
    previous_release.write_bytes(release_bytes)
    data = build_data(site, info["source_commit"])
    svg = build_map(load(site / "city-atlas/atlas.json"), data, load(ROOT / "research/prosperity-r5/sima-road.json"))
    dump(dest / "decisions.json", data)
    write_csv(dest / "decisions.csv", data["decisions"])
    # Standalone SVG resolves its evidence links on the public page.
    standalone = svg.replace('href="#decision-', 'href="' + BASE + PAGE + '#decision-')
    (dest / "overview.svg").write_text(standalone, encoding="utf-8")
    for suffix in ("css", "js"):
        shutil.copyfile(ROOT / "web" / (VERSION + "." + suffix), dest / ("atlas." + suffix))
    downloads = [
        (FOLDER + "/overview.svg", "城市空间总图 · SVG", "一张总图，含四节点关系窗"),
        (FOLDER + "/decisions.csv", "空间判断对照表 · CSV", "20项判断，列表与指针字段为JSON"),
        (FOLDER + "/decisions.json", "完整证据与布局规则 · JSON", "来源、指针、边界与输入校验值"),
    ]
    if (DATA / "source-audit.json").exists():
        shutil.copyfile(DATA / "source-audit.json", dest / "source-audit.json")
        downloads.append((FOLDER + "/source-audit.json", "原件续查与来源审计 · JSON", "实际读到什么，仍缺哪些原页图版"))
    downloads.extend([(MANIFEST, "本版文件清单 · JSON", "下载文件的SHA-256及版本边界"), (BUNDLE, "完整离线阅读包 · ZIP", "解压后打开index.html")])
    (site / PAGE).write_text(make_page(data, svg, downloads), encoding="utf-8")
    assets = [FOLDER + "/" + path.name for path in sorted(dest.iterdir()) if path.is_file() and path.name != "manifest.json"]
    assets.append(str(previous_release.relative_to(site)))
    protected = {}
    protected_candidates = ["luoyang-city-nodes.html", "city-nodes/readings.json", "city-nodes/segments.csv", "city-nodes/manifest.json",
                            "downloads/luoyang-city-nodes.zip", "all-roads/records.json", V12.full, V12.small, V12.metadata,
                            "luoyang-panorama-v13.html", "panorama-v13/review.json", "panorama-v13/manifest.json"]
    for key in ("city_nodes_r7", "panorama_review_v13"):
        for path in info.get(key, {}).get("files_sha256", {}):
            protected_candidates.append(path)
    for path in sorted(set(protected_candidates)):
        if (site / path).is_file():
            protected[path] = sha(site / path)
            if path in info["files_sha256"]:
                assert protected[path] == info["files_sha256"][path], "Predecessor changed before R9: " + path
    meta = dict(version=VERSION, research_version="R9.1", source_commit=info["source_commit"], page=PAGE,
                manifest=MANIFEST, bundle=BUNDLE, offline_entry="index.html", counts=data["counts"],
                download_files=[x[0] for x in downloads], files_sha256={path: sha(site / path) for path in [*assets, PAGE]},
                protected_files_sha256=protected, source_inputs_sha256=data["source_inputs_sha256"],
                published_inputs_sha256=data["published_inputs_sha256"],
                predecessor_release=dict(path=str(previous_release.relative_to(site)), sha256=sha(previous_release)),
                coordinate_contract=data["coordinate_contract"], source_frames_registered_together=False,
                new_historical_coordinates=0, new_shoreline_geometries=0, evidence_grade_upgrades=0,
                homepage_revision="panorama-approved-v12", homepage_replacement_approved=False,
                map_views=VIEWS)
    dump(site / MANIFEST, meta)
    with ZipFile(site / BUNDLE, "w", ZIP_DEFLATED) as archive:
        archive.writestr("index.html", make_page(data, svg, downloads, offline=True))
        for path in [*assets, MANIFEST]:
            archive.writestr(path, (site / path).read_bytes())
    info[KEY] = meta
    release = json.loads(release_bytes)
    release["extensions"] = sorted(set(release["extensions"]) | {VERSION})
    release[KEY + "_version"] = VERSION
    release["current_milestone"] = "盛时 R9.1 · 城市空间总图、20项判断与V13修订候选"
    dump(site / "release.json", release)
    for path in [*assets, MANIFEST, BUNDLE, PAGE, "release.json"]:
        info["files_sha256"][path] = sha(site / path)
    dump(site / "build-info.json", info)
    return meta


def verify(site=ROOT / "_site"):
    site = Path(site)
    info = load(site / "build-info.json")
    meta = info[KEY]
    errors = []
    for key in ("files_sha256", "protected_files_sha256"):
        for path, expected in meta[key].items():
            if not (site / path).is_file() or sha(site / path) != expected:
                errors.append("hash mismatch: " + path)
    data = load(site / FOLDER / "decisions.json")
    if len(data["decisions"]) != 20 or len({row["id"] for row in data["decisions"]}) != 20:
        errors.append("decision identity/count mismatch")
    if data["source_frames_registered_together"] or data["new_historical_coordinates"] or data["new_shoreline_geometries"]:
        errors.append("historical geometry boundary violated")
    for path, expected in data["source_inputs_sha256"].items():
        if sha(ROOT / path) != expected:
            errors.append("research input changed: " + path)
    return dict(version=VERSION, source_commit=meta["source_commit"], errors=errors, counts=data["counts"])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, default=ROOT / "_site")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    result = verify(args.site) if args.verify else build(args.site)
    print(json.dumps(result if args.verify else result["counts"], ensure_ascii=False))
    if result.get("errors"):
        raise SystemExit(1)
