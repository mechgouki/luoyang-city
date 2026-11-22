"""Publish the four-node reading atlas without changing the approved image or source geometry."""
import csv
import hashlib
import json
import shutil
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from city_nodes_r7_contract import BASE, BUILD_CONTROL_FILES, BUNDLE, FOLDER, KEY, MANIFEST, PAGE, ROAD_ENTRY, VERSION, add_home, restore_home
from city_nodes_r7_data import build_data
from city_nodes_r7_maps import build_maps
from city_nodes_r7_page import make_page
from homepage_artwork_v10 import PAGES, V12

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research/city-nodes-r7"
CSV_FIELDS = ["id", "name", "node_ids", "node_names", "evidence_level", "period", "temporal_status", "temporal_label",
              "locatable_segment", "start", "end", "endpoint_status", "ancient_endpoint_coordinates",
              "gates", "water_constraints", "geometry_status", "geometry_label", "geometry_refs",
              "inferred_connections", "identity_notes", "reported_metrics", "findings", "context_findings", "missing_evidence",
              "source_refs", "source_citations", "review_source_citations", "source_inputs", "next_originals", "original_url"]
ROAD_PAGE = "luoyang-all-roads.html"


def digest(content):
    return hashlib.sha256(content).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def csv_value(value):
    return json.dumps(value, ensure_ascii=False) if value is None or isinstance(value, (list, dict)) else value


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key, "")) for key in CSV_FIELDS})


def build(site=ROOT / "_site"):
    info = json.loads((site / "build-info.json").read_bytes())
    release = json.loads((site / "release.json").read_bytes())
    dest = site / FOLDER
    dest.mkdir(exist_ok=True)
    data = build_data(site)
    data["source_commit"] = info["source_commit"]
    data["csv_fields"] = CSV_FIELDS
    data["csv_encoding"] = "UTF-8 with BOM; list/object cells use JSON; null is unknown, never zero"
    svgs = build_maps(json.loads((site / "city-atlas/atlas.json").read_bytes()), data)
    for key, svg in svgs.items():
        (dest / (key + ".svg")).write_text(svg, encoding="utf-8")
    dump(dest / "readings.json", data)
    write_csv(dest / "segments.csv", data["segments"])
    for name in ("atlas.css", "atlas.js"):
        shutil.copyfile(DATA / name, dest / name)
    hero = dict(full=FOLDER + "/homepage-v12.webp", small=FOLDER + "/homepage-v12-small.webp",
                width=1672, height=941, revision=V12.revision)
    for name, original, expected in ((hero["full"], V12.full, V12.full_sha), (hero["small"], V12.small, V12.small_sha)):
        assert sha(site / original) == expected
        shutil.copyfile(site / original, site / name)
    (site / PAGE).write_text(make_page(data, svgs, hero, info["source_commit"]), encoding="utf-8")

    # Record and preserve the exact immediately preceding home pages, then add
    # only the three declared navigation/text edits. Running this stage twice is safe.
    previous_home = {}
    archive_files = []
    for page in PAGES:
        before = restore_home((site / page).read_bytes())
        archive = "homepage/history/" + page.replace(".html", "-before-r7.html")
        (site / archive).write_bytes(before)
        previous_home[page] = dict(archive=archive, sha256=digest(before))
        archive_files.append(archive)
        (site / page).write_bytes(add_home(before))
    road_before = (site / ROAD_PAGE).read_bytes()
    if ROAD_ENTRY in road_before:
        assert road_before.count(ROAD_ENTRY) == 1
        road_before = road_before.replace(ROAD_ENTRY, b"", 1)
    assert road_before.count(b"</header>") == 1
    road_archive = "homepage/history/all-roads-before-r7.html"
    (site / road_archive).parent.mkdir(parents=True, exist_ok=True)
    (site / road_archive).write_bytes(road_before)
    (site / ROAD_PAGE).write_bytes(road_before.replace(b"</header>", b"</header>" + ROAD_ENTRY, 1))
    archive_files.append(road_archive)

    assets = [FOLDER + "/" + name for name in [*(key + ".svg" for key in svgs), "readings.json", "segments.csv", "atlas.css", "atlas.js", "homepage-v12.webp", "homepage-v12-small.webp"]]
    excluded = {*PAGES, ROAD_PAGE, "release.json", PAGE, BUNDLE, *archive_files}
    protected = {path: expected for path, expected in info["files_sha256"].items()
                 if path not in excluded and not path.startswith(FOLDER + "/")}
    for path, expected in protected.items():
        assert sha(site / path) == expected, "Earlier build input or public resource changed: " + path
    # Preserve control-file bytes locally without presenting a consumed Pages
    # marker as a downloadable predecessor resource.
    build_controls = {path: protected.pop(path) for path in BUILD_CONTROL_FILES}
    meta = dict(version=VERSION, research_version="R7.1", source_commit=info["source_commit"],
                page=PAGE, manifest=MANIFEST, bundle=BUNDLE,
                download_files=[*(FOLDER + "/" + key + ".svg" for key in svgs), FOLDER + "/segments.csv", FOLDER + "/readings.json", MANIFEST, BUNDLE],
                counts=data["counts"], baseline_counts=dict(entities=339, roads=84, waters=34),
                new_historical_coordinates=0, new_shoreline_geometries=0,
                source_frames_registered_together=False, homepage_revision=V12.revision,
                source_inputs_sha256=data["source_inputs_sha256"], published_inputs_sha256=data["published_inputs_sha256"],
                files_sha256={path: sha(site / path) for path in assets},
                protected_files_sha256=protected, build_control_files_sha256=build_controls,
                predecessor_homepage=previous_home,
                predecessor_road_page=dict(path=ROAD_PAGE, archive=road_archive, sha256=digest(road_before)),
                hero=hero, scope=data["scope"])
    dump(site / MANIFEST, meta)
    with ZipFile(site / BUNDLE, "w", ZIP_DEFLATED) as archive:
        archive.writestr("index.html", make_page(data, svgs, hero, info["source_commit"], offline=True))
        for path in [*assets, MANIFEST]:
            archive.writestr(path, (site / path).read_bytes())
    info[KEY] = meta
    release["extensions"] = sorted(set(release["extensions"]) | {VERSION})
    release[KEY + "_version"] = VERSION
    release["current_milestone"] = "盛时 R7.1 · 四处城市节点、联读总览与首页依据导览"
    dump(site / "release.json", release)
    for path in [*assets, *archive_files, MANIFEST, BUNDLE, PAGE, *PAGES, ROAD_PAGE, "release.json"]:
        info["files_sha256"][path] = sha(site / path)
    dump(site / "build-info.json", info)
    return meta


if __name__ == "__main__":
    print(json.dumps(build()["counts"], ensure_ascii=False))
