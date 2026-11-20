"""Publish the north-city source view and retain the earlier study contents."""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from city_north_471_data import build_data
from city_north_471_map import make_maps
from prosperity_anchors_p461 import offline_page
from prosperity_city_common_p470 import PROTECTED_FILES as PREVIOUS_PROTECTED

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
FOLDER = "north-471"
SOURCE = ROOT / "research/prosperity-v4" / FOLDER
PAGE = "prosperity-city-north.html"
PREVIOUS = "prosperity-city-common.html"
VERSION = "prosperity-city-north-p471"
MANIFEST = FOLDER + "/bundle-manifest.json"
BUNDLE = "downloads/north-471.zip"
OFFICIAL = "https://mechgouki.github.io/luoyang-city/"
ENTRY = ('<aside id="p471-entry" style="border-left:4px solid #285e4c;padding:1.2rem 1.4rem;'
         'background:#e8ede2;margin:1.5rem 0"><strong>继续 · 北门与金墉</strong>'
         f'<p><a href="./{PAGE}">放大查看金墉丙城、大夏门与广莫门 →</a>'
         '　联读城北门道、水程与16条现行文献校读。</p></aside>\n')
CSV_FIELDS = ("evidence_id", "group_id", "title", "display_quote", "legacy_quote",
              "annotations", "reading", "limit", "temporal_note", "source_ids",
              "geographic_coordinates")
ASSET_NAMES = ("city-overview.svg", "north-detail.svg", "readings.json", "evidence.csv",
               "study.css", "north-ui.js", "reuse-plan.json")
DOWNLOADS = (FOLDER + "/city-overview.svg", FOLDER + "/north-detail.svg",
             FOLDER + "/readings.json", FOLDER + "/evidence.csv",
             FOLDER + "/reuse-plan.json", MANIFEST, BUNDLE)
PROTECTED_FILES = (*PREVIOUS_PROTECTED, "prosperity-backbone-p469.html",
                   *["common-470/" + name for name in ("city-common.svg", "readings.json", "places.csv",
                         "study.css", "common-ui.js", "reuse-plan.json", "bundle-manifest.json")],
                   "downloads/common-470.zip")


def esc(value):
    return html.escape(str(value), quote=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def links(sources):
    result = []
    for source in sources:
        title = source.get("title", source.get("label", source.get("id", "来源")))
        url = source.get("url", source.get("href"))
        if url:
            result.append(f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(title)}</a>')
        else:
            result.append(esc(title))
    return "；".join(result)


def choices(data):
    return "".join(f'<a role="button" href="#north-{esc(row["id"])}" '
                   f'data-north-choice="{esc(row["id"])}" '
                   f'aria-pressed="{str(row["id"] == "N01").lower()}">'
                   f'{esc(row["id"])}　{esc(row["name"])}</a>' for row in data["north_entries"])


def north_cards(data):
    features = {row["id"]: row for row in data["features"]}
    cards = []
    water = {row["ref"]: row for row in data["water_relations"]}
    for entry in data["north_entries"]:
        identifier = entry["id"]
        feature = features[entry["point_feature_id"]]
        evidence = "".join(f'<a href="#evidence-{esc(record)}" data-open-evidence="{esc(record)}">{esc(record)} ↗</a>'
                           for record in entry["evidence_ids"])
        detail = "".join(f'<li><a href="{esc(link["href"])}">{esc(link["label"])}</a></li>'
                         for link in entry["detail_links"])
        water_links = "".join(f'<li><a href="#water-{esc(ref.replace("/", "-"))}">{esc(water[ref]["label"])}</a></li>'
                              for ref in entry["water_relation_ids"])
        period = feature.get("source_historical_period", "按原来源的时期记录阅读")
        cards.append(f'<article class="reference-card" id="north-{identifier}" data-north-card="{identifier}">'
                     f'<p class="eyebrow">{identifier} / 北城来源参照</p><h3>{esc(entry["name"])}</h3>'
                     f'<span class="role">{esc(entry["role_label"])}</span>'
                     f'<p class="card-label">位置与范围</p><p class="scope">{esc(entry["scope"])}</p>'
                     f'<p class="card-label">来源记录的时期</p><p class="caption">{esc(period)}</p>'
                     f'<p class="card-label">关联的原文与校读</p><div class="evidence-links">{evidence}</div>'
                     f'<p class="card-label">相邻水程的阅读入口</p><p class="scope">{esc(entry["water_scope"])}</p>'
                     f'<ul class="detail-links">{water_links}</ul><ul class="detail-links">{detail}</ul></article>')
    return "\n".join(cards)


def evidence_card(record):
    identifier = record["id"]
    overlay = record["reading_overlay"]
    annotations = []
    for index, item in enumerate(overlay["annotations"], 1):
        annotations.append(f'<div data-modern-annotation="{identifier}-{index}"><p>{esc(item["quote"])}</p>'
                           f'<p class="source-line">{esc(item.get("author", ""))} · {esc(item["layer"])} · '
                           f'<a href="{esc(item["url"])}">{esc(item["locator"])}</a></p></div>')
    annotation_block = ('<section class="annotations"><h5>现代夹注 · 与正文分列</h5>'
                        + "".join(annotations) + "</section>") if annotations else ""
    correction = ('<p class="correction-note">本条沿用P1已核正正文；下列周氏夹注不计入传世正文。</p>'
                  if overlay["correction_applied"] else "")
    variants = "".join(f'<li>{esc(item.get("source", ""))}：{esc(item["reading"])}</li>'
                       for item in record.get("variants", []))
    variant_block = ('<details><summary>版本差异与读法</summary><ul class="variant-list">'
                     + variants + "</ul></details>") if variants else ""
    temporal = (f'<p class="temporal"><strong>年代与状态：</strong>{esc(record["temporal_note"])}</p>'
                if record.get("temporal_note") else "")
    return (f'<article class="evidence-card" id="evidence-{identifier}" data-evidence-id="{identifier}" '
            f'data-corrected="{str(overlay["correction_applied"]).lower()}">'
            f'<span class="record-id">{identifier}</span><h4>{esc(record["title"])}</h4>'
            f'<p class="reading">{esc(record["reading"])}</p><p class="limit">{esc(record["limit"])}</p>'
            f'{temporal}<details data-reading-detail><summary>展开原文、校读与出处</summary>{correction}'
            f'<blockquote data-evidence-quote="{identifier}">{esc(overlay["quote"])}</blockquote>'
            f'<p class="source-line">{esc(overlay["textual_layer"])} · {esc(record["quote_locator"])}<br>'
            f'{esc(overlay["locator"])}<br>{links(overlay["source_links"])}</p>'
            f'{annotation_block}{variant_block}</details></article>')


def evidence_sections(data):
    records = {row["id"]: row for row in data["evidence"]}
    result = []
    for group in data["evidence_groups"]:
        cards = "".join(evidence_card(records[identifier]) for identifier in group["evidence_ids"])
        result.append(f'<section class="evidence-group" id="group-{esc(group["id"])}" '
                      f'data-evidence-group="{esc(group["id"])}"><h3>{esc(group["title"])}</h3>'
                      f'<p class="group-description">{esc(group["scope"])}</p><div class="evidence-grid">{cards}</div></section>')
    return "\n".join(result)


def entity_chips(data):
    placed = {entry["entity_id"] for entry in data["north_entries"]}
    result = []
    for identifier, name in data["entity_names"].items():
        label = "已有局部来源参照" if identifier == "ic_jinyong" else "已有来源参照" if identifier in placed else "文献对象 · 尚未定位"
        result.append(f'<span class="entity-chip" data-north-entity="{esc(identifier)}" '
                      f'data-entity-placed="{str(identifier in placed).lower()}">{esc(name)}<small>{label}</small></span>')
    return "".join(result)


def water_cards(data):
    result = []
    for record in data["water_relations"]:
        identifier = record["ref"]
        result.append(f'<article class="water-card" id="water-{esc(identifier.replace("/", "-"))}" '
                      f'data-water-id="{esc(identifier)}"><span class="ref">{esc(identifier)}</span>'
                      f'<h3>{esc(record["label"])}</h3><p class="water-route">'
                      f'{esc(record["from_label"].replace(chr(10), " "))} → {esc(record["to_label"].replace(chr(10), " "))}</p>'
                      f'<p class="reading">{esc(record["reading"])}</p><p class="limit">{esc(record["limit"])}</p>'
                      f'<details><summary>查看水程原文与出处</summary><blockquote>{esc(record["quote"])}</blockquote>'
                      f'<p class="source-line">{esc(record["locator"])}<br>{links(record["sources"])}</p>'
                      f'<p class="caption">原文关系记录 · 地理坐标未定 · 516—528年逐年通水未确认</p></details>'
                      f'<a class="source-line" href="{esc(record["page"])}">打开原水系图与完整上下文 ↗</a></article>')
    return "\n".join(result)


def road_cards(data):
    source_lookup = {row["id"]: row for row in data["road_sources"]}
    result = []
    for road in data["roads"]:
        width = "—".join(str(value) for value in road["report_width_m_approx"])
        result.append(f'<article class="road-card" data-north-road-code="{esc(road["code"])}">'
                      f'<p class="eyebrow">{esc(road["code"])} · {esc(road["label"])}</p><h3>{esc(road["title"])}</h3>'
                      f'<dl><dt>报告调查段残长</dt><dd>约{esc(road["report_length_m_approx"])}米</dd>'
                      f'<dt>报告路宽</dt><dd>约{esc(width)}米</dd></dl><p>{esc(road["observation"])}</p>'
                      f'<p class="limit">{esc(road["measure_scope"])}</p><p class="source-line">'
                      f'{links([source_lookup[key] for key in road["source_ids"]])}</p></article>')
    return "\n".join(result)


def evidence_csv(data):
    groups = {record: group["id"] for group in data["evidence_groups"] for record in group["evidence_ids"]}
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for record in data["evidence"]:
        overlay = record["reading_overlay"]
        writer.writerow({"evidence_id": record["id"], "group_id": groups[record["id"]], "title": record["title"],
                         "display_quote": overlay["quote"], "legacy_quote": record["quote"],
                         "annotations": json.dumps(overlay["annotations"], ensure_ascii=False),
                         "reading": record["reading"], "limit": record["limit"],
                         "temporal_note": record.get("temporal_note") or "",
                         "source_ids": json.dumps(record["sources"], ensure_ascii=False),
                         "geographic_coordinates": ""})
    return "\ufeff" + output.getvalue()


def page_html(data, maps, commit):
    page = (SOURCE / "index.html").read_text(encoding="utf-8")
    rendered = {}
    for key, drawing in maps.items():
        rendered[key] = (ET.tostring(drawing, encoding="unicode")
                         .replace(OFFICIAL + PAGE + "#north-", "#north-")
                         .replace(OFFICIAL + PREVIOUS, "./" + PREVIOUS))
    download_labels = (("全城参照图", "SVG · 27项同源要素"), ("北部放大图", "SVG · 原图局部裁切"),
                       ("完整依据", "JSON · 原记录与现行校读"), ("文献证据表", "CSV · 正文与旧引分列"),
                       ("来源复用说明", "JSON · 输入与范围"), ("成果校验清单", "JSON · SHA-256"),
                       ("离线资料包", "ZIP · 含本页，共9个成员"))
    downloads = "".join(f'<a download href="./{path}">{esc(label)}<small>{esc(note)}</small></a>'
                        for path, (label, note) in zip(DOWNLOADS, download_labels))
    inputs = '<ul class="source-inputs">' + "".join(
        f'<li><a href="https://github.com/mechgouki/luoyang-city/blob/{esc(commit)}/{esc(path)}">{esc(path)}</a><br>'
        f'<code>{esc(digest)}</code></li>' for path, digest in data["source_inputs_sha256"].items()) + "</ul>"
    replacements = {
        "NORTH_CHOICES": choices(data), "NORTH_CARDS": north_cards(data),
        "MAP_NORTH": rendered["north"], "MAP_OVERVIEW": rendered["overview"],
        "GROUP_CHOICES": "".join(f'<a role="button" href="#group-{esc(group["id"])}" '
                                   f'data-group-choice="{esc(group["id"])}" aria-pressed="false">{esc(group["title"])}</a>'
                                   for group in data["evidence_groups"]),
        "EVIDENCE_GROUPS": evidence_sections(data), "ENTITY_CHIPS": entity_chips(data),
        "WATER_CARDS": water_cards(data), "ROAD_CARDS": road_cards(data),
        "DOWNLOAD_LINKS": downloads, "SOURCE_INPUTS": inputs,
        "BUILD_COMMIT": f'发布依据 <a href="https://github.com/mechgouki/luoyang-city/commit/{esc(commit)}">{esc(commit[:12])}</a>',
    }
    for marker, value in replacements.items():
        needle = "<!-- " + marker + " -->"
        if page.count(needle) != 1:
            raise ValueError("P471 template marker changed: " + marker)
        page = page.replace(needle, value)
    return page


def build(site=SITE):
    site = Path(site)
    info, release = load(site / "build-info.json"), load(site / "release.json")
    protected = {path: sha(site / path) for path in PROTECTED_FILES}
    for path in info["files_sha256"]:
        if path.endswith(("-luoyang-panorama.webp", "-luoyang-panorama-small.webp",
                          "-luoyang-panorama-approved-v9.webp", "-luoyang-panorama-approved-v9-small.webp")):
            protected[path] = sha(site / path)
    previous = site / PREVIOUS
    original = previous.read_text(encoding="utf-8").replace(ENTRY, "")
    marker = '<section class="section" id="city-map">'
    if original.count(marker) != 1:
        raise ValueError("Review the P470 page before adding the P471 entry")
    previous_sha = hashlib.sha256(original.encode()).hexdigest()
    data = build_data(ROOT)
    dest = site / FOLDER
    dest.mkdir(parents=True, exist_ok=True)
    (site / "downloads").mkdir(exist_ok=True)
    maps = make_maps(data)
    for key, filename in (("overview", "city-overview.svg"), ("north", "north-detail.svg")):
        ET.indent(maps[key])
        ET.ElementTree(maps[key]).write(dest / filename, encoding="utf-8", xml_declaration=True)
    dump(dest / "readings.json", data)
    (dest / "evidence.csv").write_text(evidence_csv(data), encoding="utf-8", newline="")
    for filename in ("study.css", "north-ui.js", "reuse-plan.json"):
        shutil.copyfile(SOURCE / filename, dest / filename)
    page = page_html(data, maps, info["source_commit"])
    (site / PAGE).write_text(page, encoding="utf-8")
    previous.write_text(original.replace(marker, ENTRY + marker, 1), encoding="utf-8")
    if previous.read_text(encoding="utf-8").replace(ENTRY, "") != original:
        raise ValueError("P471 changed P470 beyond its unique continuation entry")
    assets = [dest / filename for filename in ASSET_NAMES]
    preservation = {"previous_page": PREVIOUS, "previous_page_sha256": previous_sha,
                    "entry_id": "p471-entry", "entry_html": ENTRY, "protected_files_sha256": protected,
                    "scope": "Hashes protect prior builders' output in this same release; P470 publication commit provenance is compared separately across releases.",
                    "cross_release_stable_files": [path for path in protected
                        if path not in ("common-470/bundle-manifest.json", "downloads/common-470.zip")]}
    manifest = {"version": VERSION, "source_commit": info["source_commit"], "page": PAGE, "bundle": BUNDLE,
                "source_inputs_sha256": data["source_inputs_sha256"],
                "files_sha256": {path.relative_to(site).as_posix(): sha(path) for path in assets},
                "counts": data["counts"], "new_historical_coordinates": 0, "new_metric_measurements": 0,
                "new_historical_relationships": 0, "new_geographic_footprints": 0, "preservation": preservation}
    dump(site / MANIFEST, manifest)
    with zipfile.ZipFile(site / BUNDLE, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("index.html", offline_page(page, FOLDER, ""))
        for path in [*assets, site / MANIFEST]:
            archive.write(path, path.relative_to(site).as_posix())
    release["extensions"] = sorted(set(release["extensions"]) | {VERSION})
    release["prosperity_city_north_p471_version"] = VERSION
    release["current_milestone"] = "盛时 P4.7.1 · 北门与金墉城市分布联读"
    dump(site / "release.json", release)
    study = {"version": VERSION, "source_commit": info["source_commit"], "page": PAGE,
             "folder": FOLDER, "bundle": BUNDLE, "package": BUNDLE, "manifest": MANIFEST,
             "readings": FOLDER + "/readings.json", "plates": ["city-overview.svg", "north-detail.svg"],
             "entry_id": "p471-entry", "counts": data["counts"], "source_inputs_sha256": data["source_inputs_sha256"],
             "download_files": list(DOWNLOADS), "preservation": preservation,
             "new_historical_coordinates": 0, "new_metric_measurements": 0,
             "new_historical_relationships": 0, "new_geographic_footprints": 0, "new_geographic_transform": None}
    info["prosperity_city_north_p471"] = study
    for path in [*assets, site / PAGE, previous, site / MANIFEST, site / BUNDLE, site / "release.json"]:
        info["files_sha256"][path.relative_to(site).as_posix()] = sha(path)
    if any(sha(site / path) != digest for path, digest in protected.items()):
        raise ValueError("P471 modified a protected prior asset")
    if any(sha(ROOT / path) != digest for path, digest in data["source_inputs_sha256"].items()):
        raise ValueError("P471 modified a source record")
    dump(site / "build-info.json", info)
    return study


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
