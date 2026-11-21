"""Publish a source-frame hydrography plate and a locational register for every water ID."""
import csv
import json
from collections import Counter
from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research/water-atlas"
V4 = ROOT / "research/prosperity-v4"
BASE = "https://mechgouki.github.io/luoyang-city/"
PAGE = "luoyang-water-atlas.html"
CSV = "water-locations.csv"
JSON = "water-location-data.json"
ZIP = "downloads/luoyang-water-atlas.zip"


def load(path):
    return json.loads(path.read_text())


def link(url, label):
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


def points(values):
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in values)


def regional(fig):
    labels = {"W01": (660, 241, "洛水"), "W03": (450, 319, "伊水"),
              "W04": (336, 160, "谷水"), "W05": (154, 167, "瀍水"),
              "W06": (674, 102, "城东阳渠"), "W07": (213, 239, "千金堨"),
              "W09": (14, 296, "旧枝渎"), "W30": (815, 145, "鸿池陂"),
              "W31": (647, 62, "七里涧"), "W33": (288, 39, "金谷水")}
    marks = []
    for name, poly in fig["cities"]:
        marks.append(f'<polygon points="{points(poly)}" fill="#e3dac9" stroke="#776950" stroke-width="2"/>')
    for wid, name, kind, xy in fig["traces"]:
        if kind == "symbol":
            x, y = xy[0]
            mark = f'<circle cx="{x}" cy="{y}" r="6" fill="#09656c"/>'
        else:
            dash = ' stroke-dasharray="6 5"' if kind == "dry" else ''
            mark = f'<polyline points="{points(xy)}" stroke="#18767b" fill="none" stroke-width="3" stroke-linejoin="round"{dash}/>'
        marks.append(f'<a href="#{wid}"><title>{escape(name)} · {wid}</title>{mark}</a>')
    for wid, (x, y, name) in labels.items():
        marks.append(f'<a href="#{wid}"><text x="{x}" y="{y}">{name}</text></a>')
    return ('<svg viewBox="0 0 971 360" role="img" aria-label="据黄学超图1描录的古水道与陂堨位置">'
            + ''.join(marks) + '<text x="489" y="132" class="town">洛阳城</text>'
            '<text x="89" y="295" class="town">王城</text><text x="923" y="40">北 ↑</text></svg>')


def city(features):
    by_id = {f["id"].removeprefix("geo-"): f["source_pdf_geometry"] for f in features}
    marks = []
    for fid, color, dash in [("inner-wall-aboveground", "#766650", ""), ("inner-wall-underground", "#998b79", "2 1"),
                            ("palace-walls", "#995f3d", ""), ("modern-luo-river", "#9994ae", "3 2")]:
        geom = by_id[fid]
        lines = [geom["coordinates"]] if geom["type"] == "LineString" else geom["coordinates"]
        for line in lines:
            marks.append(f'<polyline points="{points(line)}" fill="none" stroke="{color}" stroke-width="1.4" stroke-dasharray="{dash or "none"}"/>')
    gates = [("daxia-gate","大夏门","W04",-2,-4),("guangmo-gate","广莫门","W04",0,-4),
             ("jianchun-gate","建春门","W06",3,-2),("dongyang-gate","东阳门","W32",3,-2),
             ("qingyang-gate","青阳门","W32",3,1),("ximing-gate","西明门","W04",-21,0),
             ("xiyang-gate","西阳门","W25",-21,0),("qianqiu-gate","千秋门","W14",-16,-4)]
    for fid, label, wid, dx, dy in gates:
        x, y = by_id[fid]["coordinates"]
        marks.append(f'<a href="#{wid}"><circle cx="{x}" cy="{y}" r="1.5" fill="#704d33"/>'
                     f'<text x="{x+dx}" y="{y+dy}">{label}</text></a>')
    return ('<svg class="city" viewBox="242 229 175 192" aria-label="06a内城墙、八座参照城门及近现代洛河局部" role="img">'
            + ''.join(marks) + '<text x="310" y="314">宫城</text><text x="324" y="362">内城</text>'
            '<text x="250" y="416">近现代洛河 · 局部</text></svg>')


def build(site):
    fig = load(DATA / "huang-figure1.json")
    ledger = load(V4 / "backbone-469/readings.json")
    broad = load(V4 / "hydro-roads-anchor-p46.json")
    atlas = load(site / "city-atlas/atlas.json")
    source_index = {s["id"]:s for s in broad["source_registry"]}
    relations = {r["ref"]: r for r in ledger["current_relations"]}
    current = {r["id"]:r for r in ledger["current_water_ledger"]}
    baseline = {r["id"]:r for r in broad["water_features"]}
    traced = {t[0] for t in fig["traces"]}
    feature_index = {f["id"].removeprefix("geo-"):f for f in atlas["features"]}
    landmarks = {
        "W02":["modern-luo-river"], "W04":["jinyong-bing-reference","daxia-gate","guangmo-gate","jianchun-gate","ximing-gate"],
        "W06":["jianchun-gate"], "W11":["inner-wall-aboveground","inner-wall-underground"],
        "W12":["inner-wall-aboveground","inner-wall-underground"], "W13":["palace-walls"],
        "W14":["qianqiu-gate"], "W21":["qianqiu-gate"], "W25":["xiyang-gate"],
        "W28":["qianqiu-gate"], "W32":["qingyang-gate","dongyang-gate"]}
    rows = []
    with (DATA / "locations.tsv").open() as stream:
        for wid, kind, place, finding, limit in csv.reader(stream, delimiter="\t"):
            sources = {}
            for sid in baseline[wid]["source_ids"]:
                src = source_index[sid]
                if src.get("url"):
                    sources[src["title"]] = src["url"]
            evidence = []
            for ref in current[wid]["current_refs"]:
                rel = relations[ref]
                evidence.append({"id": ref, "from": rel["from_label"], "to": rel["to_label"],
                                 "reading": rel["reading"], "limit": rel["limit"], "url": BASE + rel["page"]})
                for src in rel["sources"]:
                    if src.get("url"):
                        sources[src["title"]] = src["url"]
            if wid in traced:
                sources["黄学超图1原图"] = fig["image"]
            if wid == "W01":
                sources["城仓正祥，图25"] = load(V4 / "anchor-461/fig25.json")["source"]["pdf_url"]
            if wid in {"W13","W14"}:
                audit = load(V4 / "water-468/west-palace-source-audit.json")
                for s in audit["sources"]:
                    if s.get("url") and s.get("title"):
                        sources[s["title"]] = s["url"]
            if wid == "W30":
                for s in load(V4 / "anchor-461/hongchi.json")["sources"]:
                    if s.get("url"): sources[s["title"]] = s["url"]
            method = "研究图河段／符号" if wid in traced else ("近现代底图线" if wid == "W02" else "相对位置或遗迹地段")
            rows.append(dict(id=wid, name=baseline[wid]["name"], group=kind, placement=method,
                             locality=place, finding=finding, limit=limit, sources=sources, evidence=evidence, anchors=landmarks.get(wid,[])))
    assert [r["id"] for r in rows] == sorted(current) == sorted(baseline)
    assert len(rows) == 34 and len(traced) == 10
    with (site / CSV).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["编号","名称","类型","定位精度","地段","方位依据","时代与界限","出处","关系索引"])
        for r in rows:
            writer.writerow([r[k] for k in ("id","name","group","placement","locality","finding","limit")]
                            + [" | ".join(n+" "+u for n,u in r["sources"].items())," | ".join(e["id"] for e in r["evidence"])])
    data = {"version":"水系定位图集 1.0","target_years":[516,528],"source_figure":fig,
            "accepted_target_bank_geometries":0,"register":rows,
            "anchor_frame":{"crs":atlas["crs"],"source":"申遗图06a","usage":"墙、门为定位参照物。W02是近现代水线。"},
            "anchors":{key:{k:feature_index[key][k] for k in ("id","label","geometry","source_pdf_geometry","approximation")}
                       for key in sorted({key for keys in landmarks.values() for key in keys})}}
    (site / JSON).write_text(json.dumps(data, ensure_ascii=False, indent=2))
    sections = []
    for kind, count in Counter(r["group"] for r in rows).items():
        items = []
        for r in (r for r in rows if r["group"] == kind):
            sources = "　".join(link(u,n) for n,u in r["sources"].items())
            refs = "　".join(link(e["url"],e["id"].split("/")[-1]) for e in r["evidence"])
            anchor_notes = []
            for key in r["anchors"]:
                f = feature_index[key]
                name = f["label"]
                if f["geometry"]["type"] == "Point":
                    lon, lat = f["geometry"]["coordinates"]
                    name += f"（东经{lon:.4f}°，北纬{lat:.4f}°）"
                anchor_notes.append(link(BASE+"prosperity-city-atlas.html#feature-"+f["id"],name))
            anchors = "；".join(anchor_notes)
            if anchors: anchors = "<p>06a地理参照（西安80坐标系）　"+anchors+"</p>"
            items.append(f'<article id="{r["id"]}"><small>{r["id"]} · {r["placement"]}</small>'
                         f'<h3>{escape(r["name"])}</h3><strong>{escape(r["locality"])}</strong>'
                         f'<p>{escape(r["finding"])}</p><p class="limit">{escape(r["limit"])}</p>'
                         f'<details><summary>出处与图段</summary>{anchors}<p>{sources}</p><p>{refs}</p></details></article>')
        sections.append(f'<section id="group-{rows.index(next(r for r in rows if r["group"]==kind))}">'
                        f'<h2>{kind} <small>{count}</small></h2><div class="grid">{"".join(items)}</div></section>')
    groups = list(dict.fromkeys(r["group"] for r in rows))
    jumps = "　".join(link("#group-"+str(next(i for i,r in enumerate(rows) if r["group"]==g)),g) for g in groups)
    page = (DATA / "atlas.html").read_text()
    substitutions = {"REGION":regional(fig), "CITY":city(atlas["features"]), "ROWS":"".join(sections),
                     "GROUPS":jumps, "ORIGINAL":link(fig["image"],"查看黄学超图1原图"),
                     "PAPER":link(fig["publication"],"原刊与摘要"),"CSV":CSV,"DATA":JSON}
    for key, value in substitutions.items():
        page = page.replace("@"+key+"@", value)
    (site / PAGE).write_text(page.replace("@ZIP@", ZIP))
    (site / ZIP).parent.mkdir(exist_ok=True)
    with ZipFile(site / ZIP,"w",ZIP_DEFLATED) as bundle:
        bundle.writestr(PAGE, page.replace("@ZIP@", BASE+ZIP))
        for name in [CSV, JSON]: bundle.write(site/name, name)
    return [PAGE, CSV, JSON, ZIP]
