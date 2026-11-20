"""Publish the west city reading room after the northern city view."""
import csv
import hashlib
import io
import json
import shutil
import zipfile
from pathlib import Path

from city_west_472_data import FOLDER, ROOT, build_data
from city_west_472_maps import LIVE, PAGE, relations, source_map, svg_text
from prosperity_anchors_p461 import offline_page
from prosperity_city_common_p470 import dump, esc, load, sha

SOURCE = ROOT / "research/prosperity-v4" / FOLDER
PREVIOUS = "prosperity-city-north.html"
VERSION = "prosperity-city-west-p472"
KEY = "prosperity_city_west_p472"
BUNDLE = "downloads/west-472.zip"
MANIFEST = FOLDER + "/bundle-manifest.json"
ASSETS = tuple(FOLDER+"/"+name for name in (
    "west-source.svg", "west-relations.svg", "readings.json", "evidence.csv", "crosswalk.json", "study.css", "west-ui.js"))
DOWNLOADS = (*ASSETS[:5], MANIFEST, BUNDLE)
ENTRY = ('<aside id="p472-entry" style="border-left:4px solid #285e4c;background:#e8ede2;padding:1rem 1.4rem">'
         '<a href="./prosperity-city-west.html"><strong>继续读城西门道与坊寺 →</strong></a>'
         '<p>从西阳门、西明门读到门外御道、寺宅关系与所据年代。</p></aside>\n')
MARKER = '<section class="section" id="north-view">'
TYPES = {"continuous_short_quote":"连续短引", "explicit_excerpt":"节录", "edited_reading_with_visible_markers":"含校补标记的校读"}


def link(url, label):
    return f'<a href="{esc(url)}">{esc(label)}</a>'


def article(row, entities, sources):
    b, p, work = row["b5"], row["p1"], row["working_reading"]
    key = row["id"]
    checks = []
    for checked in p["source_checks"]:
        spans = "、".join(s["line_start"]+"–"+s["line_end"] for s in checked["segments"])
        checks.append(link(checked["retrieved_url"], checked["declared_source_id"]+" · "+spans))
    variants = [f'{esc(sources[v["source"]]["title"])}：{esc(v["reading"])}' for v in b["variants"]]
    pairs = [("B5校读", esc(b["reading"])), ("时期", esc(b["temporal_note"] or work["period_label"])),
             ("适用范围", esc(b["limit"])), ("相关对象", "、".join(link("#entity-"+i, entities[i]["name"]) for i in b["entities"])),
             ("引文所在", esc(b["quote_locator"])+" · "+link(sources[b["quote_source"]]["url"], sources[b["quote_source"]]["title"])),
             ("文本层", esc(p["legacy_evidence_layer"])), ("P1电子匹配行号", "；".join(checks)),
             ("B5参校卷册", "、".join(link(sources[s]["url"], s) for s in b["sources"]))]
    if variants:
        pairs.append(("版本与校语", "<br>".join(variants)))
    definition = "".join(f"<dt>{esc(label)}</dt><dd>{value}</dd>" for label, value in pairs)
    return (f'<article class="record" id="{key}" data-record="{key}" data-owner="{row["group"]}">'
            f'<span class="meta">{link("#"+key,key)} · {esc(work["period_label"])}</span><h4>{esc(b["title"])}</h4>'
            f'<blockquote>{esc(p["legacy_quote"])}</blockquote><p>{esc(work["map_reading"])}</p>'
            f'<details><summary>{esc(TYPES[p["quotation_class"]])} · 校本、时期与出处</summary><dl>{definition}</dl></details></article>')


def page_html(data, commit):
    entities = {e["id"]: e for e in data["entities"]}
    sources = {s["id"]: s for s in data["text_sources"]}
    features = {f["id"]: f for f in data["features"]}
    groups, records = data["groups"], data["records"]
    group_links = [link("#group-"+g["id"], g["label"]+f' · {len(g["evidence_ids"])}条') for g in groups]
    points = []
    for p in data["map_points"]:
        f = features[p["feature_id"]]
        points.append(f'<li>{link("#entity-"+p["entity_id"],p["label"])}<small>{esc(f["source_feature_code"])}'
                      f' · {esc(f["source_historical_period"])} · 概化图符中心</small></li>')
    objects = []
    for e in entities.values():
        status = "来源图符 "+features[e["feature_id"]]["source_feature_code"] if e["feature_id"] else "未定位"
        links = " · ".join(link("#"+key, key) for key in e["records"])
        objects.append(f'<li id="entity-{e["id"]}" data-object="{e["id"]}" data-name="{esc(e["name"])}" '
                       f'data-records="{" ".join(e["records"])}">{link("#entity-"+e["id"],e["name"])}'
                       f'<small>{esc(status)} · {esc(e["period_label"])}</small><div data-object-links>{links}</div></li>')
    sections = []
    for g in groups:
        cards = "".join(article(r, entities, sources) for r in records if r["group"] == g["id"])
        sections.append(f'<div class="group" id="group-{g["id"]}" data-group="{g["id"]}"><h3>{esc(g["label"])}</h3>'
                        f'<div class="record-grid">{cards}</div></div>')
    labels = [("门址参照图","SVG · 06a原绘要素"), ("门道与坊寺关系图","SVG · 无比例"),
              ("完整证据与来源","JSON · 24条对读与22个对象"), ("逐条证据表","CSV · 引文、时层、来源、限定"),
              ("图面取舍对照表","JSON · 每条记录的工作层"), ("文件校验清单","JSON · SHA-256"), ("离线专题","ZIP · 两图、网页及数据")]
    downloads = "".join(f'<a download href="./{path}">{label}<small>{note}</small></a>'
                        for path, (label, note) in zip(DOWNLOADS, labels, strict=True))
    git = "https://github.com/mechgouki/luoyang-city"
    provenance = '<p>'+link(git+"/blob/"+commit+"/docs/prosperity-city-west-p472-notes.md", "研究与变更说明")+" · "+link(
        git+"/commit/"+commit, "发布依据 "+commit[:12])+'</p>'
    content = (SOURCE / "index.html").read_text()
    parts = {"MAP": svg_text(source_map(data, "")), "RELATIONS": svg_text(relations("")),
             "POINTS": "<ul>"+"".join(points)+"</ul>", "GROUP_NAV":"<ol>"+"".join(f"<li>{a}</li>" for a in group_links)+"</ol>",
             "ENTITIES":'<ul class="object-grid">'+"".join(objects)+"</ul>", "FILTERS":"".join(group_links),
             "EVIDENCE":"".join(sections), "DOWNLOADS":downloads, "PROVENANCE":provenance}
    for marker, value in parts.items():
        token = "<!-- "+marker+" -->"
        if content.count(token) != 1:
            raise ValueError("Review P472 page marker "+marker)
        content = content.replace(token, value)
    return content


def evidence_csv(data):
    result = io.StringIO(newline="")
    fields = ["id","p1_key","group","title","entity_ids","source_bindings","period","quote","quotation_class",
              "textual_layer","variants","source_checks","source_ids","locator","reading","limit","temporal_note",
              "map_reading","electronic_match","manual_context_review","geographic_coordinates"]
    csvfile = csv.DictWriter(result, fieldnames=fields)
    csvfile.writeheader()
    entities = {e["id"]: e for e in data["entities"]}
    for row in data["records"]:
        b, p, work = row["b5"], row["p1"], row["working_reading"]
        values = {k:b[k] for k in ("id","title","quote","textual_layer","variants","reading","limit","temporal_note","geographic_coordinates")}
        values.update(p1_key=p["key"], group=row["group"], entity_ids=b["entities"],
                      source_bindings={e:entities[e]["feature_id"] for e in b["entities"]}, period=work["period_label"],
                      quotation_class=p["quotation_class"], source_checks=p["source_checks"], source_ids=b["sources"],
                      locator=b["quote_locator"], map_reading=work["map_reading"],
                      electronic_match=p["legacy_quote_passed_normalized_sequence_check"], manual_context_review=p["manual_context_review"])
        csvfile.writerow({k: json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list,bool)) else v for k,v in values.items()})
    return result.getvalue()


def build(site=ROOT / "_site"):
    site = Path(site)
    info, release = load(site/"build-info.json"), load(site/"release.json")
    hashes, commit = info["files_sha256"], info["source_commit"]
    north = info["prosperity_city_north_p471"]
    protected = set(north["preservation"]["protected_files_sha256"]) | set(north["download_files"]) | {
        north["preservation"]["previous_page"],
        "north-471/study.css", "north-471/north-ui.js"}
    protected_sha = {path:sha(site/path) for path in sorted(protected)}
    if any(hashes[path] != digest for path,digest in protected_sha.items()):
        raise ValueError("P471 inputs disagree with this build's manifest")
    previous = (site/PREVIOUS).read_text()
    if previous.count(ENTRY) > 1:
        raise ValueError("Duplicate west continuation")
    original = previous.replace(ENTRY, "")
    before = hashlib.sha256(original.encode()).hexdigest()
    expected = info.get(KEY, {}).get("preservation", {}).get("previous_page_sha256", hashes[PREVIOUS])
    if before != expected or original.count(MARKER) != 1:
        raise ValueError("Review the P471 page before installing the continuation")
    data = build_data()
    dest = site/FOLDER
    dest.mkdir(exist_ok=True)
    for name, plate in (("west-source.svg", source_map(data, LIVE)), ("west-relations.svg", relations(LIVE))):
        (dest/name).write_text(svg_text(plate)+"\n")
    dump(dest/"readings.json", data)
    (dest/"evidence.csv").write_text(evidence_csv(data), encoding="utf-8-sig", newline="")
    for path in ASSETS[4:]:
        shutil.copyfile(SOURCE/Path(path).name, site/path)
    page = page_html(data, commit)
    (site/PAGE).write_text(page)
    (site/PREVIOUS).write_text(original.replace(MARKER, ENTRY+MARKER, 1))
    preservation = {"previous_page":PREVIOUS, "previous_page_sha256":before, "entry_id":"p472-entry",
                    "entry_html":ENTRY, "protected_files_sha256":protected_sha}
    study = {"version":VERSION, "source_commit":commit, "page":PAGE, "manifest":MANIFEST, "bundle":BUNDLE,
             "download_files":list(DOWNLOADS), "counts":data["counts"], "preservation":preservation,
             "source_inputs_sha256":data["source_inputs_sha256"]}
    dump(site/MANIFEST, study | {"files_sha256":{p:sha(site/p) for p in ASSETS}})
    with zipfile.ZipFile(site/BUNDLE, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("index.html", offline_page(page, FOLDER, ""))
        for path in (*ASSETS, MANIFEST):
            archive.write(site/path, path)
    release["extensions"] = sorted(set(release["extensions"]) | {VERSION})
    release[KEY+"_version"] = VERSION
    release["current_milestone"] = "盛时 P4.7.2 · 城西门道与坊寺"
    dump(site/"release.json", release)
    if any(sha(site/path) != digest for path,digest in protected_sha.items()):
        raise ValueError("P472 modified a protected asset")
    info[KEY] = study
    for path in (*ASSETS, MANIFEST, BUNDLE, PREVIOUS, PAGE, "release.json"):
        hashes[path] = sha(site/path)
    dump(site/"build-info.json", info)
    return study


if __name__ == "__main__":
    print(build()["counts"])
