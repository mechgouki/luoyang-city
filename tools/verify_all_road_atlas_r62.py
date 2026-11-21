"""Check complete road coverage without turning source records into an invented network."""
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
from verify_road_atlas_r6 import ROAD_IDS, verify_research as verify_legacy_research

ROOT = Path(__file__).resolve().parents[1]
KEY = "all_road_locations"
VERSION = "all-road-atlas-r6.2"
PAGE = "luoyang-all-roads.html"
FOLDER = "all-roads"
SOURCE = ROOT / "research/roads-r62/catalog.json"
SVG = FOLDER + "/city-all-roads.svg"
CSV = FOLDER + "/records.csv"
DATA = FOLDER + "/records.json"
COVERAGE = FOLDER + "/coverage.csv"
MANIFEST = FOLDER + "/manifest.json"
BUNDLE = "downloads/luoyang-all-roads.zip"
DOWNLOADS = (SVG, CSV, DATA, COVERAGE, MANIFEST, BUNDLE)
GROUPS = ("legacy", "documentary", "palace", "ward", "gate", "bridge")
NS = "{http://www.w3.org/2000/svg}"


def load(path):
    return json.loads((ROOT / path).read_bytes())


def records_by_group(data):
    return {group: [r for r in data["records"] if r["group"] == group] for group in GROUPS}


def _source_ids(data):
    source_rows = data["sources"]
    if isinstance(source_rows, dict):
        return set(source_rows)
    ids = [s["id"] for s in source_rows]
    assert len(ids) == len(set(ids)), "Duplicate source identifiers"
    return set(ids)


def _entity_ids(records):
    return {identifier for row in records for identifier in row.get("entity_ids", [])}


def _check_input_hashes(hashes):
    assert hashes, "Input provenance is empty"
    for path, checksum in hashes.items():
        target = (ROOT / path).resolve()
        assert target.is_relative_to(ROOT), path
        assert target.is_file() and digest(target.read_bytes()) == checksum, path


def _pointer(document, pointer):
    assert pointer == "" or pointer.startswith("/"), pointer
    current = document
    for part in pointer.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


def _input_ref(reference):
    """Resolve an explicit repository input; a source location never supplies a GIS transform."""
    assert isinstance(reference, dict), reference
    path = reference.get("source_path") or reference.get("path") or reference.get("file")
    pointer = reference.get("json_pointer", reference.get("pointer"))
    assert path and pointer is not None, reference
    target = (ROOT / path).resolve()
    assert target.is_relative_to(ROOT) and target.is_file(), reference
    return _pointer(json.loads(target.read_bytes()), pointer)


def verify_catalog(data):
    """Use independent old inputs to verify coverage, not the new catalog's claimed count."""
    assert data.get("research_version", data.get("version")) == "R6.2"
    assert data["target_years"] == [516, 528]
    assert data["new_historical_coordinates"] == data["accepted_target_bank_geometries"] == 0
    assert data["source_frames_registered_together"] is False
    assert data["original_1993_figure_verified"] is False
    records = data["records"]
    ids = [r["id"] for r in records]
    assert len(ids) == len(set(ids)), "Duplicate road evidence record identifiers"
    groups = records_by_group(data)
    assert set(r["group"] for r in records) == set(GROUPS)
    assert [r["id"] for r in groups["legacy"]] == ROAD_IDS
    legacy = load("research/roads-r6/roads.json")
    legacy_counts = verify_legacy_research(legacy)
    for retained, original in zip(groups["legacy"], legacy["roads"], strict=True):
        for field, value in original.items():
            actual = retained[field]
            if field == "source_refs":
                actual = [ref.removeprefix("legacy:") for ref in actual]
            elif field == "reported_metrics":
                actual = [dict(metric, source_ref=metric["source_ref"].removeprefix("legacy:")) for metric in actual]
            assert actual == value, (retained["id"], "Changed original source field", field)
    assert data["legacy_crosswalk"] == legacy["crosswalk"]
    assert data["legacy_supplements"] == legacy["supplements"]
    entities = load("data/entities.json")
    expected_roads = {e["id"] for e in entities if e["type"] in {"road", "道路"}}
    expected_bridges = {e["id"] for e in entities if e["type"] in {"bridge", "桥", "浮桥"}}
    assert len(expected_roads) == 21 and len(expected_bridges) == 5
    assert expected_roads <= _entity_ids(groups["documentary"]), "A previously registered documentary road disappeared"
    assert expected_bridges <= _entity_ids(groups["bridge"]), "A previously registered bridge disappeared"
    assert "market_fish" not in _entity_ids(records), "A lane market was converted into a road"
    sources = _source_ids(data)
    frame_ids = [frame["id"] for frame in data["frames"]]
    assert len(frame_ids) == len(set(frame_ids)), "Duplicate source-frame identifiers"
    required = ("id", "name", "record_kind", "period", "locatable_segment", "start", "end",
                "endpoint_status", "identity_notes", "missing_evidence")
    for row in records:
        assert all(row.get(key) for key in required), (row["id"], "Missing route evidence fields")
        assert row.get("source_refs") and set(row["source_refs"]) <= sources, row["id"]
        assert set(row.get("legacy_ids", [])) <= set(ROAD_IDS) | {"S01", "S02", "S03"}, row["id"]
        assert isinstance(row["geometry_refs"], list), row["id"]
        assert isinstance(row["reported_metrics"], list), row["id"]
        assert isinstance(row["water_constraints"], list), row["id"]
        assert row["source_inputs"], (row["id"], "No traceable repository evidence input")
        for reference in row["source_inputs"]:
            _input_ref(reference)
        for reference in row["geometry_refs"]:
            native = _input_ref(reference)
            assert isinstance(native, (dict, list)) and native, (row["id"], reference)
            assert reference["native_geometry"] == native, (row["id"], "Native source geometry changed")
            assert reference["city_registration"] is False, (row["id"], reference)
            assert reference["frame_id"] in frame_ids, (row["id"], reference)
            assert reference["kind"] and reference["scope"], (row["id"], reference)
        for field in ("geographic_coordinates", "world_coordinates", "geographic_transform"):
            if field in row:
                assert row[field] is None, (row["id"], field)
        for metric in row["reported_metrics"]:
            assert metric["new_measurement"] is False and metric["source_ref"] in sources, row["id"]
            assert metric["label"] and metric["unit"] and metric["scope"], row["id"]
    assert data["coverage"] and data["exclusions"] and data["frames"]
    for frame in data["frames"]:
        for field in ("geographic_transform", "world_coordinates", "geographic_coordinates"):
            if field in frame:
                assert frame[field] is None, (frame.get("id"), field)
    coverage_ids = [r["entity_id"] for r in data["coverage"]]
    assert len(coverage_ids) == len(set(coverage_ids)) == len(entities)
    assert set(coverage_ids) == {e["id"] for e in entities}, "The all-entity coverage table omits or invents an entity"
    for covered in data["coverage"]:
        original = _input_ref(covered["source_input"])
        assert original["id"] == covered["entity_id"]
        assert original["name"] == covered["name"] and original["type"] == covered["entity_type"]
        assert covered["status"] and covered["reason"]
        assert set(covered["record_ids"]) <= set(ids), covered["entity_id"]
        if covered["entity_id"] in expected_roads | expected_bridges:
            assert covered["record_ids"], covered["entity_id"]
    audit = data["coverage_audit"]
    assert audit["canonical_entity_total"] == len(entities)
    assert set(audit["canonical_road_ids"]) == expected_roads
    assert set(audit["canonical_bridge_ids"]) == expected_bridges
    assert audit["canonical_road_count"] == len(expected_roads)
    assert audit["canonical_bridge_count"] == len(expected_bridges)
    mentions = audit["entity_road_quote_mentions"]
    assert audit["road_quote_mention_count"] == len(mentions)
    assert audit["unresolved_road_quote_mentions"] == []
    for mention in mentions:
        assert mention["source_quote"] == _input_ref(mention["source_input"])
        assert mention["disposition"] and mention["reason"]
        assert set(mention["mapped_record_ids"]) <= set(ids)
    exclusion_ids = [r["id"] for r in data["exclusions"]]
    assert len(exclusion_ids) == len(set(exclusion_ids))
    for exclusion in data["exclusions"]:
        assert exclusion["reason"] and exclusion["disposition"]
        for reference in exclusion["source_inputs"]:
            _input_ref(reference)
    return dict(records=len(records), groups=dict(Counter(r["group"] for r in records)),
                documentary_entities=len(expected_roads), bridge_entities=len(expected_bridges),
                coverage=len(data["coverage"]), exclusions=len(data["exclusions"]),
                legacy_research=legacy_counts)


def verify_evidence_boundaries(data):
    """Guard the concrete width/spacing, component and phase distinctions reviewed in this atlas."""
    rows = {row["id"]: row for row in data["records"]}

    def metric(identifier, label):
        values = [m["value"] for m in rows[identifier]["reported_metrics"] if m["label"] == label]
        assert len(values) == 1, (identifier, label)
        return values[0]

    axis = load("research/prosperity-v4/axis-measurements.json")
    second = axis["second_gate"]
    assert metric("P02", "铺砖路宽") == second["north_south_paved_road_width_m"]
    assert metric("P03", "距门南侧报告值") == second["ew_road_south_distance_report_m"]
    assert metric("P04", "距门北侧报告值") == second["ew_road_north_distance_report_m"]
    assert metric("P03", "路宽约") == metric("P04", "路宽约") == second["ew_road_width_m_approx"]
    assert metric("P07", "夹道宽") == axis["northeast_court"]["alley_width_m"]
    assert metric("G03", "门道数") == second["passage_count"]
    assert rows["G12"]["record_kind"] == "gate_node_passages_unknown"
    assert rows["G12"]["reported_metrics"] == [], "Three passages were invented for the third palace gate"
    original_gate = load("research/prosperity-v3/gate-plan.json")
    assert metric("G01", "可辨门道数") == len([c for c in original_gate["components"] if c["kind"] == "passage"])
    jianchun = load("research/prosperity-v4/backbone-469/jianchun-plan-audit.json")
    quantities = {r["id"]: r for r in jianchun["reported_quantities"]}
    assert metric("G02", "中门道残宽") == quantities["JQ03"]["value"]
    assert metric("G02", "南、北门道各宽") == quantities["JQ04"]["value_each"]
    types = load("research/prosperity-v4/architecture-types-p44.json")
    disputed = types["source_scope_comparisons"][2]["readings"]
    assert metric("G07", "门道宽约") == disputed[0]["value_m"]
    assert metric("G08", "门口宽约") == disputed[1]["value_m"]
    assert "G08" in json.dumps(rows["G07"]["identity_notes"], ensure_ascii=False)
    assert "G07" in json.dumps(rows["G08"]["identity_notes"], ensure_ascii=False)
    baima = load("research/prosperity-v4/backbone-469/road01-source-audit.json")
    measurements = baima["metrics_reported_not_remeasured"]
    assert metric("F01", "街宽约") == measurements["central_ns_street_width_approx_m"]
    for identifier, value in zip(("F02", "F03"), measurements["lateral_ns_street_distance_from_central_street_reported_m"], strict=True):
        assert metric(identifier, "距居中纵街") == value
    for identifier, value in zip(("F05", "F06"), measurements["lateral_ew_street_distance_from_central_street_reported_m"], strict=True):
        assert metric(identifier, "距居中横街") == value
    assert metric("G11", "缺口宽约") == measurements["south_opening_width_approx_m"]
    assert metric("G11", "车辙密集带宽") == measurements["rut_band_width_m"]
    assert metric("G11", "南端沟槽东西长约") == measurements["possible_threshold_groove_ew_length_approx_m"]
    assert rows["F07"]["record_kind"] == "reported_road_class_unresolved"
    assert rows["F07"]["reported_metrics"] == [] and rows["F07"]["geometry_refs"] == []
    assert {r["id"] for r in data["records"] if r["record_kind"] == "reported_ward_road"} == {f"F{i:02d}" for i in range(1, 7)}
    assert rows["B04"]["geometry_refs"][0]["kind"] == "symbol"
    assert metric("B04", "宣阳门至洛水") == "四里"
    assert {"older_phase_reference", "later_phase_excluded", "architectural_reading_unresolved",
            "foundation_connection_not_verified_passage"} <= {r["disposition"] for r in data["exclusions"]}
    return dict(ward_streets=6, unresolved_ward_road_class=1, third_gate_passage_count=None,
                source_gate_passage_bands=3)


def verify_figure_geometry(svg, data):
    """Check native geometry in the rendered SVG, independently of JSON preservation claims."""
    def points(node):
        return [[float(n) for n in point.split(",")] for point in node.get("points").split()]

    original = load("research/roads-r6/roads.json")
    old_rows = {r["id"]: r for r in original["roads"]}
    for identifier in ROAD_IDS[:8]:
        row = old_rows[identifier]
        observed = [points(node) for node in svg.iter(NS + "polyline")
                    if node.get("data-source-feature") == row["source_feature_id"] and node.get("data-part") is not None]
        assert observed == row["geometry"]["coordinates"], identifier
    for identifier in [f"O{i:02d}" for i in range(1, 12)]:
        candidates = [a for a in svg.iter(NS + "a") if a.get("data-record-ref") == identifier]
        assert len(candidates) == 1, identifier
        segments = list(candidates[0].iter(NS + "polyline"))
        native = old_rows[identifier]["reconstruction_geometry"]
        if native["kind"] == "endpoint_only":
            assert len(segments) == 1 and points(segments[0]) == native["coordinates"]
            assert segments[0].get("data-layer") == "inferred"
            assert segments[0].get("data-geometry-role") == "endpoint-pair-connector"
            assert segments[0].get("stroke-dasharray"), identifier
        else:
            assert [points(node) for node in segments] == native["coordinates"], identifier
    sima = [node for node in svg.iter() if node.get("data-frame") == "frame-sima2023"]
    assert len(sima) == 1
    assert [points(node) for node in sima[0].iter(NS + "polyline")] == load("research/prosperity-r5/sima-road.json")["image"]["sima_road_ink_px"]
    gate_frame = [node for node in svg.iter() if node.get("data-frame") == "frame-changhe-s37"]
    assert len(gate_frame) == 1, "Gate source frame cannot be looked up in the catalog"
    observed_gate = {node.get("data-component"): points(node) for node in gate_frame[0].iter(NS + "polygon")}
    expected_gate = {c["id"]: c["source_px"] for c in load("research/prosperity-v3/gate-plan.json")["components"] if c["kind"] == "passage"}
    assert observed_gate == expected_gate
    arrow_stems = [node for node in svg.iter(NS + "polyline") if node.get("data-geometry-role") == "source-direction-arrow-stems"]
    assert [points(node) for node in arrow_stems] == load("research/roads-r62/sources/yongxiang-arrows.json")["geometry"]["coordinates"]
    assert len(arrow_stems) == 6 and all(node.get("data-layer") == "inferred" for node in arrow_stems)
    return dict(old_inner_records=8, old_outer_records=11, sima_native_parts=6,
                gate_native_polygons=len(observed_gate), directional_arrow_stems=len(arrow_stems))


def _preservation(meta, info, get):
    old = info["road_locations"]
    preservation = meta["preservation"]
    assert preservation["previous_page"] == old["page"] == "luoyang-road-atlas.html"
    assert preservation["entry_id"] == "all-roads-entry"
    entry = preservation["entry_html"].encode()
    page = get(old["page"])
    assert page.count(entry) == page.count(b'id="all-roads-entry"') == 1
    assert digest(page.replace(entry, b"")) == preservation["previous_page_sha256"]
    assert PAGE.encode() in entry
    protected = preservation["protected_files_sha256"]
    expected = set(old["files_sha256"]) | {old["manifest"], old["bundle"]}
    assert expected <= set(protected), "An old road atlas download is outside preservation coverage"
    for path, checksum in protected.items():
        assert digest(get(path)) == info["files_sha256"][path] == checksum, path
    assert json.loads(get(old["manifest"])) == old
    old_data = json.loads(get("road-atlas/roads.json"))
    assert [r["id"] for r in old_data["roads"]] == ROAD_IDS
    assert len(old_data["supplements"]) == 3
    from homepage_artwork_v10 import V11, V12
    approval = json.loads(get(V11.metadata))
    assert approval["hero"]["selection_number"] == "07"
    assert approval["hero"]["revision"] == V11.revision
    for path, checksum in ((V11.full, V11.full_sha), (V11.small, V11.small_sha)):
        assert digest(get(path)) == info["files_sha256"][path] == checksum
    current = json.loads(get(V12.metadata))
    assert current["previous_revision"] == V11.revision
    assert current["hero"]["revision"] == V12.revision
    assert current["hero"]["source_sha256"] == V12.source_sha
    for path, checksum in ((V12.full, V12.full_sha), (V12.small, V12.small_sha)):
        assert digest(get(path)) == info["files_sha256"][path] == checksum
    for homepage in ("index.html", "v3.0-dual.html"):
        archived = get(V12.archive(homepage))
        assert b'data-hero-revision="panorama-approved-v11"' in archived
        assert digest(archived) == current["previous_html_sha256"][homepage]
        assert f'data-hero-revision="{V12.revision}"'.encode() in get(homepage)
        assert V12.full.encode() in get(homepage) and V12.small.encode() in get(homepage)
    return dict(protected_r6_files=len(protected), old_sources=21,
                homepage="panorama-approved-v11 / 07 (archived)", current_homepage=V12.revision)


def verify(info, reader):
    get = lru_cache(maxsize=None)(reader)
    hashes = info["files_sha256"]
    meta = info[KEY]
    assert meta == json.loads(get(MANIFEST))
    assert meta["version"] == VERSION and meta["research_version"] == "R6.2"
    assert meta["source_commit"] == info["source_commit"]
    assert (meta["page"], meta["manifest"], meta["bundle"]) == (PAGE, MANIFEST, BUNDLE)
    assert meta["download_files"] == list(DOWNLOADS)
    release = json.loads(get("release.json"))
    assert VERSION in release["extensions"]
    for path, checksum in meta["files_sha256"].items():
        assert digest(get(path)) == hashes[path] == checksum, path
    for path in (*DOWNLOADS, PAGE):
        assert digest(get(path)) == hashes[path], path
    data = json.loads(get(DATA))
    source = json.loads(SOURCE.read_bytes())
    counts = verify_catalog(data)
    assert data["source_commit"] == info["source_commit"]
    for field, value in source.items():
        assert data[field] == value, "Public catalog changed " + field
    boundaries = verify_evidence_boundaries(data)
    _check_input_hashes(meta["source_inputs_sha256"])
    assert "research/roads-r62/catalog.json" in meta["source_inputs_sha256"]
    for row in data["records"]:
        for reference in (*row["source_inputs"], *row["geometry_refs"]):
            path = reference.get("source_path") or reference.get("path") or reference.get("file")
            assert path in meta["source_inputs_sha256"], (row["id"], path, "Input hash not published")
    assert meta["counts"]["records"] == counts["records"]
    assert meta["counts"]["groups"] == counts["groups"]
    assert meta["counts"]["coverage"] == counts["coverage"]
    assert meta["counts"]["exclusions"] == counts["exclusions"]
    water = {r["id"]: r for r in json.loads(get("water-location-data.json"))["register"]}
    for row in data["records"]:
        for constraint in row["water_constraints"]:
            if not isinstance(constraint, dict) or not constraint.get("id", "").startswith("W"):
                continue
            original_water = water[constraint["id"]]
            assert constraint["level"] == original_water["placement"], row["id"]
            assert constraint["locality"] == original_water["locality"], row["id"]
            assert constraint["limit"] == original_water["limit"], row["id"]
    rows = list(csv.DictReader(io.StringIO(get(CSV).decode("utf-8-sig"))))
    assert [r["id"] for r in rows] == [r["id"] for r in data["records"]]
    assert len(rows[0]) >= 10, "CSV omits route-by-route evidence"
    for record, row in zip(data["records"], rows, strict=True):
        assert record["name"] == row["name"]
    coverage = list(csv.DictReader(io.StringIO(get(COVERAGE).decode("utf-8-sig"))))
    assert len(coverage) == len(data["coverage"]) and len(coverage[0]) >= 3
    for listed, original in zip(coverage, data["coverage"], strict=True):
        for field in ("entity_id", "name", "entity_type", "status", "reason"):
            assert listed[field] == original[field], (original["entity_id"], field)
    document = Links(get(PAGE))
    ids = set(document.ids)
    assert len(ids) == len(document.ids), "Duplicate IDs break deep links"
    assert {r["id"] for r in data["records"]} <= ids
    assert {"all-road-map", "map-scroll", "query", "group-filter", "clear", "count", "empty",
            "show-source", "show-inferred", "show-unknown", "zoom", "coverage", "exclusions"} <= ids
    assert document.downloads == list(DOWNLOADS)
    for url in document.links:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc:
            continue
        if parts.path and parts.path != "./":
            assert parts.path.removeprefix("./") in hashes, url
        elif parts.fragment:
            assert parts.fragment in ids, url
    svg = ET.fromstring(get(SVG))
    assert svg.tag == NS + "svg" and svg.get("viewBox")
    assert {e.get("data-layer") for e in svg.iter() if e.get("data-layer")} == {"source", "inferred", "unknown"}
    native_figure = verify_figure_geometry(svg, data)
    for anchor in svg.iter(NS + "a"):
        href = anchor.get("href") or anchor.get("{http://www.w3.org/1999/xlink}href")
        if href:
            parts = urlsplit(href)
            if parts.path.endswith(PAGE) or not parts.path:
                assert parts.fragment in ids, href
    with ZipFile(io.BytesIO(get(BUNDLE))) as archive:
        members = archive.namelist()
        assert len(members) == len(set(members)) == 8
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
    preservation = _preservation(meta, info, get)
    return dict(status="passed", source_commit=info["source_commit"], counts=counts,
                downloads=len(DOWNLOADS), offline_members=len(members),
                preservation=preservation, evidence_boundaries=boundaries, native_figure=native_figure,
                distinct_resources=get.cache_info().misses)
