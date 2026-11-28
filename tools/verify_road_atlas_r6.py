"""Verify the road release against its source register and the published evidence boundaries."""
import csv
import io
import json
from collections import Counter
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from verify_city_west_p472 import Links, digest

ROOT = Path(__file__).resolve().parents[1]
KEY = "road_locations"
VERSION = "road-atlas-r6.1"
PAGE = "luoyang-road-atlas.html"
FOLDER = "road-atlas"
DATA = FOLDER + "/roads.json"
CSV = FOLDER + "/roads.csv"
SVG = FOLDER + "/city-roads.svg"
MANIFEST = FOLDER + "/manifest.json"
BUNDLE = "downloads/luoyang-road-atlas.zip"
DOWNLOADS = (SVG, CSV, DATA, MANIFEST, BUNDLE)
ROAD_IDS = [f"R{i:02d}" for i in range(1, 9)] + [f"O{i:02d}" for i in range(1, 12)] + ["X01", "X02"]
NS = "{http://www.w3.org/2000/svg}"


def verify_research(data):
    """Check risks that could turn a source drawing or relation into surveyed geography."""
    assert data["version"] == "R6.1" and data["target_years"] == [516, 528]
    assert data["source_count"] == 21 and [r["id"] for r in data["roads"]] == ROAD_IDS
    assert data["new_field_measurements"] == data["new_geographic_coordinates"] == data["accepted_516_528_bank_geometries"] == 0
    frames = {f["id"]: f for f in data["frames"]}
    assert all(f["geographic_transform"] is None for f in frames.values())
    sources = {s["id"] for s in data["sources"]}
    rows = {r["id"]: r for r in data["roads"]}
    supplements = {r["id"]: r for r in data["supplements"]}
    assert set(supplements) == {"S01", "S02", "S03"}
    assert Counter(r["trace_grade"] for r in rows.values()) == {
        "来源图路迹": 8, "复原图路迹": 5, "复原图两端": 6, "发掘地段": 2}
    legacy = json.loads((ROOT / "research/prosperity-v4/hydro-roads-anchor-p46.json").read_bytes())
    original = {r["id"]: r for r in legacy["main_road_records"]}
    feature_data = json.loads((ROOT / "research/prosperity-v1/geographic-evidence.json").read_bytes())
    features = {f["id"]: f for f in feature_data["features"]}
    endpoints = json.loads((ROOT / "research/prosperity-v4/network-462/outer.json").read_bytes())
    corridors = {r["id"]: r for r in endpoints["corridors"]}
    required = ("period", "source_refs", "locatable_segment", "start", "end", "endpoint_status",
                "inferred_connections", "missing_evidence", "overlap_note")
    for row in rows.values():
        assert all(row[key] for key in required), row["id"]
        assert row["legacy_source_record"] == original[row["id"]]
        assert set(row["source_refs"]) <= sources
        assert row["surveyed_full_line"] is False and row["geographic_transform"] is None
        assert all(m["new_measurement"] is False and m["source_ref"] in sources for m in row["reported_metrics"])
        assert set(row["overlap_ids"]) <= set(rows) | set(supplements)
        geometry = row["geometry"]
        if row["id"].startswith("R"):
            assert geometry["frame_id"] == "frame-06a" and geometry["kind"] == "trace"
            native = features[row["source_feature_id"]]["source_pdf_geometry"]
            assert geometry["type"] == native["type"] and geometry["coordinates"] == native["coordinates"], row["id"]
            assert row["reconstruction_geometry"] is None
        else:
            assert geometry is None, "An unregistered route acquired 06a geometry: " + row["id"]
            drawing = row["reconstruction_geometry"]
            if row["id"].startswith("O"):
                assert drawing["frame_id"] == "frame-qian2018"
                if drawing["kind"] == "endpoint_only":
                    original_pair = corridors[row["source_code"]]
                    assert drawing["type"] == "MultiPoint" and drawing["coordinates"] == [
                        original_pair["inner_station_px"], original_pair["outer_station_px"]]
                else:
                    assert drawing["kind"] == "trace" and drawing["type"] == "MultiLineString"
            else:
                assert drawing is None

    north = json.loads((ROOT / "research/prosperity-v4/gates-465/readings.json").read_bytes())["later_plan"]
    south = json.loads((ROOT / "research/prosperity-v4/south-466/readings.json").read_bytes())["plan"]
    traced = {"O04": [north["west"]["trace_px"]],
              "O05": [north["north"][0]["to_wall_px"], north["north"][0]["beyond_wall_to_frame_px"]],
              "O06": [north["north"][1]["to_wall_px"], north["north"][1]["beyond_wall_to_frame_px"]],
              "O10": [south["road_samples_px"]["开阳"]], "O11": [south["road_samples_px"]["平昌"]]}
    for identifier, coordinates in traced.items():
        assert rows[identifier]["reconstruction_geometry"]["coordinates"] == coordinates
    assert supplements["S01"]["geometry"] is None
    assert supplements["S01"]["metrics"]["south_opening_width_approx_m"] == 7.5
    assert supplements["S01"]["metrics"]["central_ns_street_width_approx_m"] == 22
    assert supplements["S02"]["accepted_transfer_to_06a"] is False
    assert supplements["S02"]["geometry"] is None
    assert supplements["S02"]["reconstruction_geometry"]["frame_id"] == "frame-sima2023"
    assert supplements["S03"]["bank_landings"] == [None, None]
    assert supplements["S03"]["reconstruction_geometry"]["coordinates"] == south["bridge_symbol_ends_px"]
    for relation in data["crosswalk"]:
        assert set(relation["records"]) <= set(rows) | set(supplements)
        assert relation["relation"] and relation["decision"] and relation["basis"]
    for path, checksum in data["input_sha256"].items():
        assert digest((ROOT / path).read_bytes()) == checksum, path
    return {"source_traces": 8, "reconstruction_traces": 5, "endpoint_pairs": 6, "excavation_localities": 2}


def verify(info, reader):
    from homepage_yongning_v15 import restore_v14_context
    info, reader = restore_v14_context(info, reader)
    get = lru_cache(maxsize=None)(reader)
    hashes = info["files_sha256"]
    meta = info[KEY]
    release = json.loads(get("release.json"))
    assert meta == json.loads(get(MANIFEST)), "Road manifest differs from build-info"
    assert meta["version"] == VERSION and VERSION in release["extensions"]
    assert meta["source_commit"] == info["source_commit"]
    assert (meta["page"], meta["manifest"], meta["bundle"]) == (PAGE, MANIFEST, BUNDLE)
    assert meta["download_files"] == list(DOWNLOADS)
    for path, checksum in meta["files_sha256"].items():
        assert digest(get(path)) == hashes[path] == checksum, path
    for path in (*DOWNLOADS, PAGE):
        assert digest(get(path)) == hashes[path], path

    data = json.loads(get(DATA))
    source = json.loads((ROOT / "research/roads-r6/roads.json").read_bytes())
    research_counts = verify_research(data)
    assert data["source_commit"] == info["source_commit"]
    for key in ("frames", "sources", "crosswalk", "junctions", "input_sha256", "research_limits"):
        assert data[key] == source[key], "Public research field changed: " + key
    rows = data["roads"]
    assert len(rows) == 21 and [r["id"] for r in rows] == ROAD_IDS
    original = {r["id"]: r for r in source["roads"]}
    assert set(original) == set(ROAD_IDS)
    for row in rows:
        assert all(row[key] == value for key, value in original[row["id"]].items()), row["id"]
    assert data["supplements"] == source["supplements"] and len(data["supplements"]) == 3
    for path, checksum in data["source_inputs_sha256"].items():
        target = (ROOT / path).resolve()
        assert target.is_relative_to(ROOT), path
        assert digest(target.read_bytes()) == checksum, path
    assert "research/roads-r6/roads.json" in data["source_inputs_sha256"]
    water = {r["id"]: r for r in json.loads(get("water-location-data.json"))["register"]}
    for record in [*rows, *data["supplements"]]:
        for constraint in record.get("water_constraints", []):
            if not constraint["id"].startswith("W"):
                assert constraint["limit"] and constraint["relation"]
                continue
            original_water = water[constraint["id"]]
            assert constraint["level"] == original_water["placement"]
            assert constraint["locality"] == original_water["locality"]
            assert constraint["limit"] == original_water["limit"]

    listed = list(csv.DictReader(io.StringIO(get(CSV).decode("utf-8-sig"))))
    assert len(listed) == 21 and [r["id"] for r in listed] == ROAD_IDS
    assert len(listed[0]) >= 10, "Evidence CSV omits the route-by-route research fields"
    for row, entry in zip(rows, listed, strict=True):
        assert row["name"] == entry["name"], row["id"]

    svg = ET.fromstring(get(SVG))
    assert svg.tag == NS + "svg" and svg.get("viewBox"), "Main road figure is not standalone SVG"
    assert {e.get("data-layer") for e in svg.iter() if e.get("data-layer")} == {"source", "inferred", "unknown"}
    page = get(PAGE)
    document = Links(page)
    assert len(document.ids) == len(set(document.ids)), "Duplicate IDs break map-to-evidence navigation"
    assert set(ROAD_IDS) <= set(document.ids)
    assert document.downloads == list(DOWNLOADS)
    assert {"road-map", "map-scroll", "query", "count", "clear", "zoom", "evidence-filter",
            "show-source", "show-inferred", "show-unknown"} <= set(document.ids)
    for url in document.links:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc:
            continue
        if parts.path and parts.path != "./":
            assert parts.path.removeprefix("./") in hashes, url
        elif parts.fragment:
            assert parts.fragment in document.ids, url
    for element in svg.iter(NS + "a"):
        href = element.get("href") or element.get("{http://www.w3.org/1999/xlink}href")
        if href:
            parts = urlsplit(href)
            if parts.fragment and parts.path.endswith(PAGE):
                assert parts.fragment in document.ids, href

    for entrance in ("prosperity-city-panorama.html", "luoyang-water-atlas.html"):
        content = get(entrance)
        assert content.count(b'id="road-atlas-entry"') == 1, entrance
        assert PAGE.encode() in content

    with ZipFile(io.BytesIO(get(BUNDLE))) as archive:
        members = archive.namelist()
        assert len(members) == len(set(members)), "Duplicate ZIP members"
        assert set(members) == set(meta["files_sha256"]) | {"index.html", MANIFEST}
        for path in members:
            if path != "index.html":
                assert archive.read(path) == get(path), path
        offline = Links(archive.read("index.html"))
        for url in offline.links:
            parts = urlsplit(url)
            if parts.scheme or parts.netloc:
                continue
            if parts.path:
                assert parts.path.removeprefix("./") in members, url
            elif parts.fragment:
                assert parts.fragment in offline.ids, url

    from homepage_artwork_v10 import V11, V12
    approval = json.loads(get(V11.metadata))
    assert approval["hero"]["selection_number"] == "07"
    assert approval["hero"]["revision"] == V11.revision
    for path, checksum in ((V11.full, V11.full_sha), (V11.small, V11.small_sha)):
        assert digest(get(path)) == hashes[path] == checksum
    current = json.loads(get(V12.metadata))
    assert current["previous_revision"] == V11.revision
    assert current["hero"]["revision"] == V12.revision
    assert current["hero"]["source_sha256"] == V12.source_sha
    for path, checksum in ((V12.full, V12.full_sha), (V12.small, V12.small_sha)):
        assert digest(get(path)) == hashes[path] == checksum
    for homepage in ("index.html", "v3.0-dual.html"):
        archived = get(V12.archive(homepage))
        assert b'data-hero-revision="panorama-approved-v11"' in archived
        assert digest(archived) == current["previous_html_sha256"][homepage]
        assert f'data-hero-revision="{V12.revision}"'.encode() in get(homepage)
        assert V12.full.encode() in get(homepage) and V12.small.encode() in get(homepage)

    return dict(status="passed", source_commit=info["source_commit"], records=len(rows),
                supplements=len(data["supplements"]), downloads=len(DOWNLOADS),
                research_counts=research_counts,
                offline_members=len(members), distinct_resources=get.cache_info().misses,
                preserved_homepage="panorama-approved-v11 / 07 (archived)",
                current_homepage=V12.revision)
