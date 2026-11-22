"""Publish the whole-city and eleven-region layout atlas without inventing positions."""
import copy
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from city_layout_r10_contract import (
    KEY, VERSION, RESEARCH_VERSION, PAGE, FOLDER, MANIFEST, DATA, PDF, BUNDLE,
    HOME_PAGES, BUILD_CONTROL_FILES, RELEASE_ARCHIVE, HOME_ARCHIVES,
    CURRENT_MILESTONE, add_home, restore_r9_context,
)
from city_layout_r10_maps import build_overview, build_region
from city_layout_r10_pdf import build_pdf
from city_layout_r10_page import make_page

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research/city-layout-r10"
BASE = "https://mechgouki.github.io/luoyang-city/"
REGION_IDS = [f"R{i:02d}" for i in range(1, 12)]
BASIS = {
    "source": "来源图对应", "relation": "文献／报告关系",
    "interpretation": "候选／研究解释", "unknown": "仍待定位",
}
LEVEL_BASIS = {"source": "source", "candidate": "interpretation",
               "relative": "relation", "unlocated": "unknown"}
COVERAGE_FIELDS = [
    "id", "name", "type", "level", "period", "region_ids", "focus_regions",
    "evidence_regions", "diagram_node_ids", "decision_ids", "representation",
    "feature_ids", "placement", "next_evidence", "source_ref", "source_url",
]
DECISION_FIELDS = [
    "id", "region_id", "region_title", "title", "judgment", "map_change",
    "remaining_unknown", "phase_note", "entity_ids", "road_ids", "water_ids",
    "source_inputs", "source_evidence",
]
GAP_FIELDS = [
    "id", "region_id", "region_title", "title", "known", "unknown",
    "next_evidence", "source_inputs",
]
NETWORK_FIELDS = [
    "id", "kind", "record_id", "name", "region_ids", "basis", "decision_ids",
    "source_path", "source_pointer", "source_url", "finding", "limit", "original",
]
PUBLISHED_INPUTS = (
    "city-atlas/atlas.json", "all-roads/records.json",
    "water-location-data.json", "city-spatial-r9/decisions.json",
)


def load(path):
    return json.loads(Path(path).read_bytes())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(path):
    return digest(Path(path).read_bytes())


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pointer(document, path):
    value = document
    for token in path.strip("/").split("/") if path else ():
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def source_refs(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "source_inputs":
                yield from item
            else:
                yield from source_refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from source_refs(item)


def excerpt(value):
    """Show a labeled source-record excerpt, never relabel summaries as quotations."""
    if isinstance(value, str):
        text = value
    elif isinstance(value, dict):
        fields = ("quote", "source_quote", "reading", "claim", "interpretation",
                  "finding", "judgment", "map_change", "remaining_unknown",
                  "limit", "limitation", "note", "summary")
        lines = [str(value[k]) for k in fields if isinstance(value.get(k), str)]
        text = "；".join(lines) if lines else json.dumps(value, ensure_ascii=False)
    else:
        text = json.dumps(value, ensure_ascii=False)
    return text[:1100] + ("…" if len(text) > 1100 else "")


def build_data(site, source_commit):
    site = Path(site)
    raw = load(RESEARCH / "regions.json")
    regions = copy.deepcopy(raw["regions"])
    if [r["id"] for r in regions] != REGION_IDS:
        raise ValueError("R10 requires all eleven regions in their existing identity order")
    atlas = load(site / "city-atlas/atlas.json")
    roads = load(site / "all-roads/records.json")
    water = load(site / "water-location-data.json")
    entity_index = {e["id"]: e for e in atlas["entities"]}
    road_index = {r["id"]: r for r in roads["records"]}
    water_index = {r["id"]: r for r in water["register"]}
    assert len(entity_index) == 339 and len(road_index) == 84 and len(water_index) == 34
    hashes = {
        str((RESEARCH / name).relative_to(ROOT)): sha(RESEARCH / name)
        for name in ("regions.json", "source-review.json")
    }

    @lru_cache(maxsize=None)
    def read_source(name):
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("Source escapes repository: " + name)
        hashes[name] = sha(path)
        return load(path)

    refs = {}
    for ref in source_refs(raw):
        token = (ref["path"], ref["pointer"])
        value = pointer(read_source(token[0]), token[1])
        refs[token] = {
            "path": token[0], "pointer": token[1], "sha256": hashes[token[0]],
            "excerpt": excerpt(value), "excerpt_kind": "existing_source_record",
            "url": f"https://github.com/mechgouki/luoyang-city/blob/{source_commit}/{token[0]}",
        }

    diagrams = defaultdict(list)
    drawn_regions = defaultdict(set)
    discussed_regions = defaultdict(set)
    entity_decisions = defaultdict(list)
    network_decisions = defaultdict(list)
    network_regions = defaultdict(set)
    decisions, gaps = [], []
    for region in regions:
        rid = region["id"]
        for panel in region["panels"]:
            ids = {node["id"] for node in panel["nodes"]}
            if len(ids) != len(panel["nodes"]):
                raise ValueError("Repeated diagram node in " + panel["id"])
            for edge in panel["relations"]:
                if edge["from"] not in ids or edge["to"] not in ids:
                    raise ValueError("Relation endpoint not in its panel: " + edge["id"])
            for node in panel["nodes"]:
                for eid in node["entity_ids"]:
                    if eid not in entity_index:
                        raise ValueError("New or unknown entity identity: " + eid)
                    diagrams[eid].append(node["id"])
                    drawn_regions[eid].add(rid)
        for original in region["decisions"]:
            row = copy.deepcopy(original)
            row.update(region_id=rid, region_title=region["title"])
            row["source_evidence"] = [refs[(r["path"], r["pointer"])] for r in row["source_inputs"]]
            row["basis"] = "relation"
            row["geometry_changed"] = False
            row["evidence_grade_upgraded"] = False
            for eid in row["entity_ids"]:
                if eid not in entity_index:
                    raise ValueError("Decision has unknown entity: " + eid)
                entity_decisions[eid].append(row["id"])
                discussed_regions[eid].add(rid)
            for kind, index, field in (("road", road_index, "road_ids"), ("water", water_index, "water_ids")):
                for nid in row[field]:
                    if nid not in index:
                        raise ValueError("Unknown network identity: " + nid)
                    network_regions[(kind, nid)].add(rid)
                    network_decisions[(kind, nid)].append(row["id"])
            decisions.append(row)
        for item in region["gaps"]:
            row = copy.deepcopy(item)
            row.update(region_id=rid, region_title=region["title"], basis="unknown")
            gaps.append(row)

    coverage = []
    for original in atlas["entities"]:
        row = copy.deepcopy(original)
        eid = row["id"]
        region_ids = sorted(set(row["focus_regions"]) | set(row["evidence_regions"]) |
                            drawn_regions[eid] | discussed_regions[eid])
        region_ids = [r for r in region_ids if r in REGION_IDS]
        row["region_ids"] = region_ids or ["register"]
        row["diagram_node_ids"] = sorted(set(diagrams[eid]))
        row["decision_ids"] = sorted(set(entity_decisions[eid]))
        row["representation"] = (
            "关系节点" if row["diagram_node_ids"] else "分区名录" if region_ids else "待分区名录"
        )
        row["basis"] = LEVEL_BASIS[row["level"]]
        row["original_location_level_preserved"] = True
        coverage.append(row)

    networks = []
    for kind, source_path, field, records, page in (
        ("road", "all-roads/records.json", "records", roads["records"], "luoyang-all-roads.html"),
        ("water", "water-location-data.json", "register", water["register"], "luoyang-water-atlas.html"),
    ):
        for index, original in enumerate(records):
            rid = original["id"]
            regions_for_record = sorted(network_regions[(kind, rid)])
            if kind == "road":
                network_basis = {"source": "source", "reconstruction": "interpretation"}.get(original.get("evidence_level"), "relation")
            else:
                network_basis = {"研究图河段／符号": "interpretation", "近现代底图线": "source"}.get(original.get("placement"), "relation")
            networks.append({
                "id": kind + "-" + rid, "kind": kind, "record_id": rid,
                "name": original["name"], "region_ids": regions_for_record or ["register"],
                "basis": network_basis, "decision_ids": sorted(set(network_decisions[(kind, rid)])),
                "source_path": source_path, "source_pointer": f"/{field}/{index}",
                "source_url": BASE + page + "#" + rid,
                "finding": original.get("finding") or original.get("locatable_segment") or original.get("location_summary") or original.get("placement") or original.get("claim") or "完整对象、原图读点和使用层见既有专题。",
                "limit": original.get("limit") or original.get("missing_evidence") or original.get("uncertainty") or original.get("limits") or original.get("geometry_limit") or "本轮关联仅表示此片区使用该条证据；没有新增古代路线或岸线。",
                "original": copy.deepcopy(original),
            })

    # Six established city-scale gaps stay visible beside the source frame.
    for original in atlas["gaps"]:
        gid = original["id"]
        geo = load(ROOT / "research/prosperity-v1/geographic-evidence.json")
        index = next(i for i, row in enumerate(geo["unlocated_or_unverified"]) if row["id"] == gid)
        p = "research/prosperity-v1/geographic-evidence.json"
        hashes[p] = sha(ROOT / p)
        gaps.append({
            "id": gid, "region_id": "all", "region_title": "全城骨架",
            "title": original.get("label") or original.get("name") or gid,
            "known": "来源图骨架已保留；本项沿用全城定位依据中的未定登记。",
            "unknown": original.get("reason") or original.get("status") or original.get("note") or "尚无可接受的完整共同定位依据。",
            "next_evidence": original["next_evidence"], "basis": "unknown",
            "source_inputs": [{"path": p, "pointer": f"/unlocated_or_unverified/{index}"}],
            "original": copy.deepcopy(original),
        })
    if len({r["id"] for r in decisions}) != len(decisions) or len({r["id"] for r in gaps}) != len(gaps):
        raise ValueError("Repeated decision or gap ID")
    features = [copy.deepcopy(f) for f in atlas["features"] if not f["id"].startswith("geo-modern-")]
    counts = {
        "regions": len(regions), "panels": sum(len(r["panels"]) for r in regions),
        "diagram_nodes": sum(len(p["nodes"]) for r in regions for p in r["panels"]),
        "diagram_relations": sum(len(p["relations"]) for r in regions for p in r["panels"]),
        "decisions": len(decisions), "gaps": len(gaps), "city_scale_gaps": len(atlas["gaps"]),
        "entities": len(coverage), "coverage": len(coverage),
        "location_levels": dict(Counter(r["level"] for r in coverage)),
        "representations": dict(Counter(r["representation"] for r in coverage)),
        "source_features": len(features), "road_records": len(roads["records"]),
        "water_records": len(water["register"]), "network_records": len(networks),
        "source_files": len(hashes), "source_pointers": len(refs),
    }
    return {
        "schema": "luoyang-city-layout-r10-atlas-v1",
        "research_version": RESEARCH_VERSION, "implementation_version": VERSION,
        "source_commit": source_commit, "baseline_commit": raw["baseline_commit"],
        "target_years": raw["target_years"], "coordinate_contract": raw["coordinate_contract"],
        "regions": regions, "coverage": coverage, "decisions": decisions, "gaps": gaps,
        "networks": networks, "features": features, "counts": counts,
        "csv_fields": {"coverage": COVERAGE_FIELDS, "decisions": DECISION_FIELDS,
                       "gaps": GAP_FIELDS, "networks": NETWORK_FIELDS},
        "source_inputs_sha256": hashes,
        "published_inputs_sha256": {p: sha(site / p) for p in PUBLISHED_INPUTS},
        "source_review": FOLDER + "/source-review.json",
        "homepage_revision": "panorama-approved-v12", "homepage_replacement_approved": False,
        "new_historical_coordinates": 0, "new_shoreline_geometries": 0,
        "evidence_grade_upgrades": 0, "source_frames_registered_together": False,
        "drawing_contract": {
            "scope": "十一片区系统深化；完整项目对象与既有路水记录均有覆盖去向。",
            "diagram_positions_are_historical_coordinates": False,
            "all_catalog_entities_have_individual_footprints": False,
            "entire_scene_historically_validated": False,
            "panorama_raster_changed": False,
            "unassociated_network_records": "保留既有专题，不因未被本轮决定引用而删除或新分配地理片区。",
        },
    }


def write_csv(path, fields, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                k: json.dumps(row.get(k), ensure_ascii=False) if row.get(k) is None or isinstance(row.get(k), (dict, list, bool))
                else row[k] for k in fields
            })


def downloads_for(data):
    downloads = [
        (FOLDER + "/overview.svg", "全城总平面 · SVG", "来源骨架、城市缺口与十一片区入口"),
        (PDF, "全城与十一片区图册 · PDF", f"{data['pdf_pages']}页；图面、图例与证据边界"),
    ]
    downloads.extend((FOLDER + "/regions/" + r["id"] + ".svg",
                      r["id"] + " " + r["title"] + " · SVG", "独立关系窗与本区空间判断")
                     for r in data["regions"])
    downloads.extend([
        (FOLDER + "/coverage.csv", "全城对象覆盖 · CSV", "339个名录对象，原定位等级与本轮图面去向"),
        (FOLDER + "/decisions.csv", "空间判断与图面变化 · CSV", "逐项判断、来源字段、改图内容和限制"),
        (FOLDER + "/gaps.csv", "全城与片区未定项 · CSV", "已知内容、未知边界与下一项有效证据"),
        (FOLDER + "/networks.csv", "道路与水系覆盖 · CSV", "84条道路证据、34项水系索引，原记录完整保留"),
        (DATA, "完整布局与证据 · JSON", "全部关系窗、对象覆盖、来源指针和输入哈希"),
        (FOLDER + "/source-review.json", "本轮来源复核 · JSON", "复用范围、实际核读文件与原件缺口"),
        (MANIFEST, "版本与文件清单 · JSON", "本轮产物及既有资源保护的SHA-256"),
        (BUNDLE, "完整离线阅读包 · ZIP", "解压后打开index.html，可看图册和查表"),
    ])
    assert len(downloads) == 21
    return downloads


def build(site=ROOT / "_site"):
    site = Path(site)
    current_info = load(site / "build-info.json")
    previous_meta = current_info.get(KEY)
    previous_info, read_previous = restore_r9_context(current_info, lambda p: (site / p).read_bytes())
    # Rebuild only this stage while reading the exact frozen predecessor bytes.
    release_bytes = read_previous("release.json")
    before_homes = {p: read_previous(p) for p in HOME_PAGES}
    original_hashes = dict(previous_info["files_sha256"])
    if previous_meta:
        for path in previous_meta["files_sha256"]:
            original_hashes.pop(path, None)
        for path in (MANIFEST, BUNDLE):
            original_hashes.pop(path, None)
    for path in (*HOME_PAGES, "release.json"):
        original_hashes[path] = digest(read_previous(path))
    dest = site / FOLDER
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "regions").mkdir(exist_ok=True)
    (dest / "archive").mkdir(exist_ok=True)
    (site / RELEASE_ARCHIVE).write_bytes(release_bytes)
    for page, raw in before_homes.items():
        (site / HOME_ARCHIVES[page]).write_bytes(raw)
    data = build_data(site, previous_info["source_commit"])
    atlas = load(site / "city-atlas/atlas.json")
    overview = build_overview(atlas, data["regions"])
    region_svgs = {r["id"]: build_region(r) for r in data["regions"]}
    data["pdf_pages"] = 2 + sum(int(ET.fromstring(svg).get("data-pdf-pages", "1")) for svg in region_svgs.values())
    data["counts"]["pdf_pages"] = data["pdf_pages"]
    (dest / "overview.svg").write_text(overview, encoding="utf-8")
    for rid, svg in region_svgs.items():
        (dest / "regions" / (rid + ".svg")).write_text(svg, encoding="utf-8")
    dump(site / DATA, data)
    for name, fields, rows in (
        ("coverage", COVERAGE_FIELDS, data["coverage"]),
        ("decisions", DECISION_FIELDS, data["decisions"]),
        ("gaps", GAP_FIELDS, data["gaps"]),
        ("networks", NETWORK_FIELDS, data["networks"]),
    ):
        write_csv(dest / (name + ".csv"), fields, rows)
    shutil.copyfile(RESEARCH / "source-review.json", dest / "source-review.json")
    for ext in ("css", "js"):
        shutil.copyfile(ROOT / "web" / (VERSION + "." + ext), dest / ("atlas." + ext))
    (site / PDF).parent.mkdir(parents=True, exist_ok=True)
    pdf_result = build_pdf(site / PDF, overview, region_svgs, data)
    assert pdf_result["pages"] == data["pdf_pages"], "PDF page count differs from its complete SVG plates"
    downloads = downloads_for(data)
    (site / PAGE).write_text(make_page(data, overview, region_svgs, downloads), encoding="utf-8")
    for page, raw in before_homes.items():
        (site / page).write_bytes(add_home(raw))
    assets = sorted(str(p.relative_to(site)) for p in dest.rglob("*")
                    if p.is_file() and str(p.relative_to(site)) != MANIFEST)
    assets.extend([PAGE, PDF])
    protected = {
        p: v for p, v in original_hashes.items()
        if p not in {*HOME_PAGES, "release.json", *BUILD_CONTROL_FILES}
    }
    for path, expected in protected.items():
        assert sha(site / path) == expected, "R10 changed a protected existing resource: " + path
    metadata = {
        "version": VERSION, "research_version": RESEARCH_VERSION,
        "source_commit": data["source_commit"], "page": PAGE, "folder": FOLDER,
        "manifest": MANIFEST, "record": DATA, "pdf": PDF, "bundle": BUNDLE,
        "offline_entry": "index.html", "counts": data["counts"], "pdf_pages": data["pdf_pages"],
        "region_pages": pdf_result["region_pages"],
        "download_files": [d[0] for d in downloads],
        "files_sha256": {p: sha(site / p) for p in assets},
        "protected_files_sha256": protected,
        "build_control_files_sha256": {p: original_hashes[p] for p in BUILD_CONTROL_FILES if p in original_hashes},
        "source_inputs_sha256": data["source_inputs_sha256"],
        "published_inputs_sha256": data["published_inputs_sha256"],
        "coordinate_contract": data["coordinate_contract"],
        "predecessor_release": {"path": RELEASE_ARCHIVE, "sha256": digest(release_bytes)},
        "predecessor_homepage": {p: {"archive": HOME_ARCHIVES[p], "sha256": digest(b)} for p, b in before_homes.items()},
        "homepage_before_sha256": {p: digest(b) for p, b in before_homes.items()},
        "homepage_after_sha256": {p: sha(site / p) for p in HOME_PAGES},
        "homepage_revision": "panorama-approved-v12", "homepage_replacement_approved": False,
        "new_historical_coordinates": 0, "new_shoreline_geometries": 0,
        "evidence_grade_upgrades": 0, "source_frames_registered_together": False,
    }
    dump(site / MANIFEST, metadata)
    with ZipFile(site / BUNDLE, "w", ZIP_DEFLATED) as bundle:
        bundle.writestr("index.html", make_page(data, overview, region_svgs, downloads, offline=True))
        for path in [*assets, MANIFEST]:
            bundle.writestr(path, (site / path).read_bytes())
    release = json.loads(release_bytes)
    release["extensions"] = sorted(set(release["extensions"]) | {VERSION})
    release[KEY + "_version"] = VERSION
    release["current_milestone"] = CURRENT_MILESTONE
    dump(site / "release.json", release)
    info = copy.deepcopy(previous_info)
    info[KEY] = metadata
    info["files_sha256"] = original_hashes
    for path in [*assets, MANIFEST, BUNDLE, *HOME_PAGES, "release.json"]:
        info["files_sha256"][path] = sha(site / path)
    dump(site / "build-info.json", info)
    return metadata


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "_site")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        from city_layout_r10_verify import verify
        result = verify(load(args.site / "build-info.json"), lambda p: (args.site / p).read_bytes())
    else:
        result = build(args.site)["counts"]
    print(json.dumps(result, ensure_ascii=False))
    if result.get("errors"):
        raise SystemExit(1)
