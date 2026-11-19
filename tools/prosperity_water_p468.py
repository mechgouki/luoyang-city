"""Publish the remaining moats, palace drains and pond evidence as relative maps."""
import json
import shutil
from collections import Counter
from xml.etree import ElementTree as ET

from dual_cartography import dump, load, sha
from north_b4 import render_atlas
from prosperity_anchors_p461 import ROOT, SITE
from prosperity_water_p467 import draw_plate, esc, render_html, source_links, validate

FOLDER = "water-468"
SOURCE = ROOT / "research/prosperity-v4" / FOLDER
PAGE = "prosperity-water-p468.html"
PREVIOUS = "prosperity-water-p467.html"
ATLAS = f"downloads/{FOLDER}.pdf"
VERSION = "prosperity-water-p468"
ENTRY = (f'<p id="p468-entry" style="border-left:4px solid #206476;padding:1rem;background:#e8efe8">'
         f'<a href="./{PAGE}">续读 · 城壕、宫西水道与独立园池</a></p>\n')
CORRECTION = ('<aside id="p468-pool-correction" style="border-left:4px solid #956b46;padding:1rem;background:#f1ebde">'
              '<strong>2026-11-19园池范围更正：</strong>前册I09是华林园诸海的群体记述；'
              '将W20濛汜池、W21碧海曲池挂入I09的两项旧索引撤回。'
              '濛汜池见长秋寺北，原文记夏有水、冬则竭；碧海曲池见西游园凌云台下。'
              '该引文不足以证明两池属于华林园供水群，也不等于证明两池绝无水路。'
              '“谷水注之不竭”之前另有“若旱魃为害”的条件，不能省成全年恒定供水。'
              f'<a href="./{PAGE}#map=palace-pools-audit&amp;layer=all">查看逐池方位、季节性与勘误依据</a>。'
              '旧PDF、JSON及其索引保留历史字节，应与本更正同时阅读。</aside>\n')


def measurements_html(data):
    sources = {source["id"]: source for source in data["sources"]}
    result = ['<div class="table-scroll"><table><thead><tr><th>对象与时层</th><th>报告原值</th><th>量的含义与限制</th><th>出处</th></tr></thead><tbody>']
    for item in data.get("reported_measurements", []):
        result.append(f'<tr id="measure-{esc(item["id"])}"><th scope="row">{esc(item["label"])}<small>{esc(item["period"])}</small></th>'
                      f'<td>{esc(item["value_text"])}</td><td>{esc(item["meaning"])}<p>{esc(item["limit"])}</p></td>'
                      f'<td>{esc(item["locator"])}<p>{source_links(item, sources)}</p></td></tr>')
    result.append('</tbody></table></div>')
    return '\n'.join(result)


def corrections_html(data):
    return ('<aside class="correction-note" id="pool-scope-correction"><h2>园池范围的校正</h2>'
            '<p>本册第五图复核前册共用I09的五个池名：玄武池、流觞池和扶桑海分别保留原文方位；'
            '濛汜池与碧海曲池撤回该组供水索引。濛汜池的夏有水、冬则竭单列，'
            '西游园的碧海曲池也不因同属宫苑而并入华林园水路。</p>'
            '<p>“凡此诸海”只提供群体水路和旱涝调节记述，不能拆成每个池口的实测连接。'
            '此校正不改写旧版存档；逐池原文和撤回范围随本册证据下载。</p></aside>')


def build(site=SITE):
    data = load(SOURCE / "readings.json")
    validate(data)
    if data["new_metric_measurements"] != 0 or data["geographic_coordinates"] is not None:
        raise ValueError("P4.6.8 is an evidence reading, not a new georegistered survey")
    dest = site / FOLDER
    dest.mkdir(parents=True, exist_ok=True)
    (site / "downloads").mkdir(exist_ok=True)
    diagrams, paths = [], []
    for index, plate in enumerate(data["plates"], 1):
        diagram = draw_plate(plate, index, len(data["plates"]), "盛时洛阳  /  P4.6.8  /  水系余项")
        path = dest / f"{plate['id']}.svg"
        ET.ElementTree(diagram).write(path, encoding="utf-8", xml_declaration=True)
        diagrams.append(diagram)
        paths.append(path)
    render_atlas(paths, site / ATLAS)
    copied = [*sorted(SOURCE.glob("*.json")), SOURCE / "study.css", SOURCE / "water-ui.js"]
    for path in copied:
        shutil.copyfile(path, dest / path.name)
    page = render_html(data, diagrams, source_dir=SOURCE, folder=FOLDER)
    marker = "<!-- REPORTED_MEASUREMENTS -->"
    if page.count(marker) != 1:
        raise ValueError("Reported-value table marker is not unique")
    page = page.replace(marker, measurements_html(data))
    marker = "<!-- STUDY_CORRECTIONS -->"
    if page.count(marker) != 1:
        raise ValueError("Corrections marker is not unique")
    page = page.replace(marker, corrections_html(data))
    (site / PAGE).write_text(page, encoding="utf-8")

    previous = site / PREVIOUS
    original = previous.read_text(encoding="utf-8").replace(ENTRY, "").replace(CORRECTION, "")
    marker = '<section id="explore"'
    if original.count(marker) != 1 or 'P4.6.7' not in original:
        raise ValueError("Review P4.6.7 before adding its continuation")
    previous.write_text(original.replace(marker, CORRECTION + ENTRY + marker, 1), encoding="utf-8")
    info, release = load(site / "build-info.json"), load(site / "release.json")
    release["extensions"] = sorted(set(release["extensions"]) | {VERSION})
    release["prosperity_water_p468_version"] = VERSION
    release["current_milestone"] = "盛时 P4.6.8 · 城壕、宫西水道与独立园池"
    dump(site / "release.json", release)
    segments = [segment for plate in data["plates"] for segment in plate["segments"]]
    info["prosperity_water_p468"] = {
        "version": VERSION, "source_commit": info["source_commit"], "page": PAGE,
        "atlas": ATLAS, "readings": f"{FOLDER}/readings.json", "plates": [path.name for path in paths],
        "atlas_pages": len(paths), "segments": len(segments),
        "relation_counts": dict(Counter(segment["relationship_type"] for segment in segments)),
        "period_counts": dict(Counter(segment["period_class"] for segment in segments)),
        "layout_coordinates_only": True, "geographic_coordinates_added": 0,
        "new_metric_measurements": 0, "reported_value_rows": len(data["reported_measurements"]),
        "legacy_objects_reviewed": len(data["legacy_water_coverage"]), "entry_id": "p468-entry",
        "previously_unmapped_objects_reviewed": 12, "previously_grouped_objects_revisited": 5,
        "historical_correction": {"page": PREVIOUS, "id": "p468-pool-correction",
                                  "withdrawn_legacy_ids": ["W20", "W21"], "old_segment": "I09"},
        "data_files": [f"{FOLDER}/{path.name}" for path in copied if path.suffix == ".json"],
    }
    changed = [*paths, site / ATLAS, site / PAGE, previous, site / "release.json"]
    changed += [dest / path.name for path in copied]
    for path in changed:
        info["files_sha256"][path.relative_to(site).as_posix()] = sha(path)
    dump(site / "build-info.json", info)
    return info["prosperity_water_p468"]


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
