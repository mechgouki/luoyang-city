"""Independently verify the released whole-city plan and eleven R10 layouts.

All published bytes come from ``reader``. Repository sources are comparison
inputs only: they never substitute for missing live assets. This module uses
only the standard library so the same semantic checks run after deployment.
"""
import copy
import csv
import io
import json
import re
import stat
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from city_layout_r10_contract import (
    BUILD_CONTROL_FILES, BUNDLE, DATA, FOLDER, HOME_ARCHIVES, HOME_PAGES, KEY,
    MANIFEST, PAGE, PDF, RELEASE_ARCHIVE, RESEARCH_VERSION, VERSION, digest,
    restore_r9_context,
)
from city_nodes_r7_verify import Document, verify_links, verify_native_features
from city_spatial_r9_verify import Tree, normalized
from homepage_artwork_v10 import V12

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://mechgouki.github.io/luoyang-city/"
SOURCE = "research/city-layout-r10/regions.json"
SOURCE_REVIEW = "research/city-layout-r10/source-review.json"
REVIEW = FOLDER + "/source-review.json"
OVERVIEW = FOLDER + "/overview.svg"
REGIONS = tuple("R" + str(number).zfill(2) for number in range(1, 12))
SVGS = (OVERVIEW, *(FOLDER + "/regions/" + rid + ".svg" for rid in REGIONS))
CSVS = {name: FOLDER + "/" + name + ".csv" for name in ("coverage", "decisions", "gaps", "networks")}
CSV_REQUIRED = {
    "coverage": {"id", "name", "level", "period", "region_ids", "diagram_node_ids", "representation",
                 "feature_ids", "placement", "next_evidence", "source_ref", "source_url"},
    "decisions": {"id", "region_id", "title", "judgment", "map_change", "remaining_unknown", "phase_note",
                  "entity_ids", "road_ids", "water_ids", "source_inputs", "source_evidence"},
    "gaps": {"id", "region_id", "title", "known", "unknown", "next_evidence", "source_inputs"},
    "networks": {"id", "kind", "record_id", "name", "region_ids", "source_path", "source_pointer", "original"},
}
PUBLIC_INPUTS = {"city-atlas/atlas.json", "all-roads/records.json", "water-location-data.json", "city-spatial-r9/decisions.json"}
BASIS = {"source", "relation", "interpretation", "unknown"}
RELATIONS = {"north_of", "south_of", "east_of", "west_of", "within", "adjacent", "sequence",
             "identity_candidate", "unknown_connection", "membership", "same_source"}
NS = "{http://www.w3.org/2000/svg}"


def unique(rows, field="id"):
    identifiers = [row[field] for row in rows]
    assert all(isinstance(value, str) and value for value in identifiers)
    assert len(identifiers) == len(set(identifiers)), (field, "Duplicate identifiers")
    return dict(zip(identifiers, rows, strict=True))


def pointer(document, path):
    """Resolve strict RFC 6901 paths, rejecting accidental negative indexing."""
    assert isinstance(path, str) and (path == "" or path.startswith("/")), path
    current = document
    for encoded in path.split("/")[1:]:
        assert not re.search(r"~(?![01])", encoded), (path, "Invalid pointer escape")
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            assert re.fullmatch(r"0|[1-9][0-9]*", token), path
            index = int(token)
            assert index < len(current), (path, "Array index is not present")
            current = current[index]
        else:
            assert isinstance(current, dict) and token in current, (path, "Object key is not present")
            current = current[token]
    return current


def preserved(actual, expected, location="research"):
    """Original reviewed values survive; derived object fields may be added."""
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and set(expected) <= set(actual), location
        for key, value in expected.items():
            preserved(actual[key], value, location + "/" + key)
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected), location
        for index, (value, original) in enumerate(zip(actual, expected, strict=True)):
            preserved(value, original, location + "/" + str(index))
    else:
        assert actual == expected and type(actual) is type(expected), (location, "Reviewed value changed")


def references(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "source_inputs":
                assert isinstance(item, list)
                yield from item
            else:
                yield from references(item)
    elif isinstance(value, list):
        for item in value:
            yield from references(item)


def source_inputs(data, meta):
    fingerprints = data["source_inputs_sha256"]
    assert fingerprints == meta["source_inputs_sha256"]
    required = {SOURCE, SOURCE_REVIEW, "research/prosperity-v1/geographic-evidence.json"}
    assert required <= set(fingerprints)
    documents = {}
    for path, checksum in fingerprints.items():
        local = (ROOT / path).resolve()
        assert not PurePosixPath(path).is_absolute() and local.is_relative_to(ROOT) and local.is_file(), path
        assert ".." not in PurePosixPath(path).parts and "\\" not in path, path
        raw = local.read_bytes()
        assert digest(raw) == checksum, (path, "Research source bytes changed")
        if local.suffix == ".json":
            documents[path] = json.loads(raw)
    total = 0
    used = set()
    for reference in references(data["regions"]):
        path, where = reference["path"], reference["pointer"]
        assert path in documents and path in fingerprints, reference
        actual = pointer(documents[path], where)
        if "sha256" in reference:
            assert reference["sha256"] == fingerprints[path], reference
        if "native_geometry" in reference:
            assert reference["native_geometry"] == actual, reference
        if "city_registration" in reference:
            assert reference["city_registration"] is False, reference
        total += 1
        used.add(path)
    assert total > 0
    assert set(fingerprints) == used | required, "Research inventory omitted a used file or counted an unrelated source"
    return documents, dict(input_files=len(fingerprints), resolved_pointers=total,
                           referenced_files=len(used))


def verify_data(data, meta, info, public_inputs):
    original = json.loads((ROOT / SOURCE).read_bytes())
    for field, value in original.items():
        if field != "schema":
            preserved(data[field], value, field)
    assert data["schema"] == "luoyang-city-layout-r10-atlas-v1"
    assert original["schema"] == "luoyang-city-layout-r10-regions-v1"
    assert data["research_version"] == meta["research_version"] == RESEARCH_VERSION
    assert data["implementation_version"] == meta["version"] == VERSION
    assert data["source_commit"] == meta["source_commit"] == info["source_commit"]
    assert data["target_years"] == [516, 528]
    assert data["coordinate_contract"] == meta["coordinate_contract"]
    for field in ("new_historical_coordinates", "new_shoreline_geometries", "evidence_grade_upgrades"):
        assert data[field] == meta[field] == 0, (field, "Unsupported precision upgrade")
    assert data["source_frames_registered_together"] is meta["source_frames_registered_together"] is False
    assert data["homepage_replacement_approved"] is meta["homepage_replacement_approved"] is False
    assert data["homepage_revision"] == meta["homepage_revision"] == V12.revision
    for field in ("diagram_positions_are_historical_coordinates", "all_catalog_entities_have_individual_footprints",
                  "entire_scene_historically_validated", "panorama_raster_changed"):
        assert data["drawing_contract"][field] is False, (field, "Drawing scope acquired an unsupported historical claim")
    documents, evidence = source_inputs(data, meta)
    regions = unique(data["regions"])
    assert tuple(regions) == REGIONS, "All eleven real region layouts must survive in order"
    atlas = public_inputs["city-atlas/atlas.json"]
    old_entities = unique(atlas["entities"])
    old_roads = unique(public_inputs["all-roads/records.json"]["records"])
    old_water = unique(public_inputs["water-location-data.json"]["register"])
    assert (len(old_entities), len(old_roads), len(old_water)) == (339, 84, 34)
    assert public_inputs["water-location-data.json"]["accepted_target_bank_geometries"] == 0

    flat_decisions, flat_gaps, all_nodes, all_relations = [], [], [], []
    entity_regions, entity_nodes = defaultdict(set), defaultdict(list)
    road_regions, water_regions = defaultdict(set), defaultdict(set)
    for rid, region in regions.items():
        for field in ("title", "intro", "summary", "panorama_implication", "old_topic_url"):
            assert isinstance(region[field], str) and region[field].strip(), (rid, field)
        topic = urlsplit(region["old_topic_url"])
        assert not topic.scheme and not topic.netloc and topic.path in info["files_sha256"], (rid, "Previous topic link is missing")
        assert 2 <= len(region["panels"]) <= 8, (rid, "Region lacks substantive reading windows or exceeds its two readable sheets")
        assert len(region["decisions"]) >= 4 and region["gaps"], (rid, "Region lacks actual judgments and unresolved evidence")
        unique(region["panels"])
        for panel in region["panels"]:
            assert panel["kind"] in {"spatial", "sequence", "comparison", "membership"}
            assert panel["title"].strip() and panel["caption"].strip()
            nodes = unique(panel["nodes"])
            assert len(nodes) >= 2, (panel["id"], "Panel lacks substantive objects")
            assert panel["relations"] or panel["kind"] == "comparison", (panel["id"], "Non-comparison panel lacks a supported relationship")
            for node in nodes.values():
                assert node["label"].strip() and node["note"].strip()
                assert node["basis"] in BASIS and node["source_inputs"], node["id"]
                assert set(node["entity_ids"]) <= set(old_entities), node["id"]
                assert not ({"latitude", "longitude", "geographic_coordinates", "geometry"} & set(node)), node["id"]
                if node["basis"] == "source":
                    assert all(old_entities[eid]["level"] == "source" for eid in node["entity_ids"]), (node["id"], "Source-site symbol silently acquired an unproved catalog identity")
                for eid in node["entity_ids"]:
                    entity_regions[eid].add(rid)
                    entity_nodes[eid].append(node["id"])
                all_nodes.append(node)
            unique(panel["relations"])
            for relation in panel["relations"]:
                assert relation["from"] in nodes and relation["to"] in nodes
                assert relation["type"] in RELATIONS and relation["from"] != relation["to"]
                assert relation["label"].strip() and relation["uncertainty"].strip() and relation["source_inputs"]
                all_relations.append(relation)
        unique(region["decisions"])
        for row in region["decisions"]:
            assert row["id"].startswith("R10-" + rid + "-")
            for field in ("title", "judgment", "map_change", "remaining_unknown", "phase_note"):
                assert isinstance(row[field], str) and row[field].strip(), (row["id"], field)
            assert row["source_inputs"]
            for field, existing in (("entity_ids", old_entities), ("road_ids", old_roads), ("water_ids", old_water)):
                assert set(row[field]) <= set(existing), (row["id"], field, "Unknown original ID")
            for eid in row["entity_ids"]:
                entity_regions[eid].add(rid)
            for record in row["road_ids"]:
                road_regions[record].add(rid)
            for record in row["water_ids"]:
                water_regions[record].add(rid)
            flat_decisions.append((rid, row))
        unique(region["gaps"])
        for gap in region["gaps"]:
            for field in ("title", "known", "unknown", "next_evidence"):
                assert gap[field].strip(), (gap["id"], field)
            assert gap["source_inputs"]
            flat_gaps.append((rid, gap))
    unique(all_nodes)
    unique(all_relations)
    decisions, gaps = unique(data["decisions"]), unique(data["gaps"])
    assert list(decisions) == [row["id"] for _, row in flat_decisions]
    original_city_gaps = unique(atlas["gaps"])
    assert list(gaps) == [row["id"] for _, row in flat_gaps] + list(original_city_gaps)
    for output, original_rows in ((decisions, flat_decisions), (gaps, flat_gaps)):
        for rid, row in original_rows:
            actual = output[row["id"]]
            preserved(actual, row, row["id"])
            assert actual["region_id"] == rid and actual["basis"] in BASIS
    for gid, original_gap in original_city_gaps.items():
        gap = gaps[gid]
        assert gap["original"] == original_gap
        assert gap["next_evidence"] == original_gap["next_evidence"]
        assert gap["region_id"] == "all" and gap["basis"] == "unknown"
        assert gap["title"] and gap["known"] and gap["unknown"]
        assert len(gap["source_inputs"]) == 1
        ref = gap["source_inputs"][0]
        resolved = pointer(documents[ref["path"]], ref["pointer"])
        assert resolved["id"] == gid
        preserved(original_gap, resolved, gid)
    for row in decisions.values():
        assert row["geometry_changed"] is row["evidence_grade_upgraded"] is False
        assert row["region_title"] == regions[row["region_id"]]["title"]
        assert len(row["source_evidence"]) == len(row["source_inputs"])
        for reference, evidence_row in zip(row["source_inputs"], row["source_evidence"], strict=True):
            path, where = reference["path"], reference["pointer"]
            assert evidence_row["path"] == path and evidence_row["pointer"] == where
            assert evidence_row["sha256"] == data["source_inputs_sha256"][path]
            assert evidence_row["url"] == "https://github.com/mechgouki/luoyang-city/blob/" + data["source_commit"] + "/" + path
            assert evidence_row["excerpt_kind"] == "existing_source_record", "Reused record was relabelled an original quotation"
            resolved = pointer(documents[path], where)
            if isinstance(resolved, str):
                text = resolved
            elif isinstance(resolved, dict):
                fields = ("quote", "source_quote", "reading", "claim", "interpretation", "finding",
                          "judgment", "map_change", "remaining_unknown", "limit", "limitation", "note", "summary")
                lines = [resolved[key] for key in fields if isinstance(resolved.get(key), str)]
                text = "；".join(lines) if lines else json.dumps(resolved, ensure_ascii=False)
            else:
                text = json.dumps(resolved, ensure_ascii=False)
            assert evidence_row["excerpt"] == text[:1100] + ("…" if len(text) > 1100 else ""), (row["id"], "Source-record excerpt changed")

    prior_path = "research/city-spatial-r9/decisions.json"
    prior_rows = unique(public_inputs["city-spatial-r9/decisions.json"]["decisions"])
    assert set(prior_rows) == {"SP" + str(number).zfill(2) for number in range(1, 21)}
    core_regions = {"palace-yongning": "R07", "baima": "R02", "sima": "R03", "jianchun": "R04"}
    integrated = set()
    for node_id, rid in core_regions.items():
        expected = {row["id"] for row in prior_rows.values() if row["node_id"] == node_id}
        assert len(expected) == 5
        actual_by_area = {}
        for area in ("panels", "decisions"):
            resolved = [pointer(documents[prior_path], ref["pointer"]) for ref in references(regions[rid][area])
                        if ref["path"] == prior_path]
            actual_by_area[area] = {row["id"] for row in resolved if isinstance(row, dict) and row.get("id") in prior_rows}
        assert expected <= actual_by_area["decisions"], (rid, "Prior core-node judgments were not integrated into this region")
        assert expected & actual_by_area["panels"], (rid, "Core node is mentioned in a table but absent from its actual map")
        integrated.update(expected)
    assert len(integrated) == 20

    coverage = unique(data["coverage"])
    assert list(coverage) == list(old_entities), "Coverage loses or invents an original object"
    for eid, row in coverage.items():
        preserved(row, old_entities[eid], eid)
        original_regions = set(old_entities[eid]["focus_regions"] + old_entities[eid]["evidence_regions"])
        expected_regions = sorted(original_regions | entity_regions[eid])
        assert row["region_ids"] == (expected_regions or ["register"]), eid
        assert set(row["region_ids"]) <= {*REGIONS, "register"}, eid
        assert row["diagram_node_ids"] == sorted(set(entity_nodes[eid])), (eid, "Diagram membership changed")
        assert row["basis"] in BASIS and row["representation"].strip()
        assert row["basis"] == {"source": "source", "relative": "relation", "candidate": "interpretation", "unlocated": "unknown"}[row["level"]]
        assert row["original_location_level_preserved"] is True
        expected_decisions = sorted({decision["id"] for decision in decisions.values() if eid in decision["entity_ids"]})
        assert row["decision_ids"] == expected_decisions
        assert row["representation"] == ("关系节点" if entity_nodes[eid] else "分区名录" if expected_regions else "待分区名录")
        for field in ("geographic_coordinates", "coordinates", "geometry", "source_pdf_geometry", "latitude", "longitude"):
            if field not in old_entities[eid]:
                assert field not in row or row[field] is None, (eid, "Invented object coordinates")

    networks = unique(data["networks"])
    expected_networks = ["road-" + rid for rid in old_roads] + ["water-" + wid for wid in old_water]
    assert list(networks) == expected_networks, "Road evidence or water index lost its original identity"
    for kind, records, source, prefix, membership in (
            ("road", old_roads, "all-roads/records.json", "/records/", road_regions),
            ("water", old_water, "water-location-data.json", "/register/", water_regions)):
        for index, (record_id, original_record) in enumerate(records.items()):
            row = networks[kind + "-" + record_id]
            assert row["kind"] == kind and row["record_id"] == record_id
            assert row["original"] == original_record, (record_id, "Original network evidence changed")
            assert row["source_path"] == source and row["source_pointer"] == prefix + str(index)
            assert pointer(public_inputs[source], row["source_pointer"]) == original_record
            assert row["region_ids"] == (sorted(membership[record_id]) or ["register"]), (record_id, "Unsupported network association")
            field = "road_ids" if kind == "road" else "water_ids"
            assert row["decision_ids"] == sorted({decision["id"] for decision in decisions.values() if record_id in decision[field]})
            if kind == "road":
                expected_basis = {"source": "source", "reconstruction": "interpretation"}.get(original_record.get("evidence_level"), "relation")
            else:
                expected_basis = {"研究图河段／符号": "interpretation", "近现代底图线": "source"}.get(original_record.get("placement"), "relation")
            assert row["basis"] == expected_basis, (record_id, "Original network evidence type was relabelled")
            assert row["name"] == original_record["name"], (record_id, "Displayed network identity changed")

    features = [feature for feature in atlas["features"] if not feature["id"].startswith("geo-modern-")]
    originals = {feature["id"]: feature for feature in documents["research/prosperity-v1/geographic-evidence.json"]["features"]
                 if not feature["id"].startswith("geo-modern-")}
    assert len(features) == len(originals) == 28
    assert {feature["id"] for feature in features} == set(originals)
    for feature in features:
        assert feature["source_pdf_geometry"] == originals[feature["id"]]["source_pdf_geometry"]
    assert data["features"] == features, "R10 source frame altered an existing feature"
    counts = dict(regions=len(regions), panels=sum(len(region["panels"]) for region in regions.values()),
                  decisions=len(decisions), gaps=len(gaps), coverage=len(coverage), source_features=len(features),
                  network_records=len(networks), road_records=len(old_roads), water_records=len(old_water))
    assert data["counts"] == meta["counts"]
    for key, value in counts.items():
        assert data["counts"][key] == value, (key, "Reported count differs from actual evidence")
    for key, value in (("diagram_nodes", len(all_nodes)), ("diagram_relations", len(all_relations)),
                       ("city_scale_gaps", len(original_city_gaps)), ("entities", len(coverage)),
                       ("source_files", len(data["source_inputs_sha256"]))):
        if key in data["counts"]:
            assert data["counts"][key] == value
    assert data["counts"]["location_levels"] == dict(Counter(row["level"] for row in coverage.values()))
    assert data["counts"]["representations"] == dict(Counter(row["representation"] for row in coverage.values()))
    unique_refs = {(ref["path"], ref["pointer"]) for ref in references(data["regions"])}
    assert data["counts"]["source_pointers"] == len(unique_refs)
    return dict(counts=counts, **evidence, integrated_r9_judgments=len(integrated),
                original_placement_levels=dict(Counter(row["level"] for row in coverage.values())))


def verify_csv(raw, rows, fields):
    assert raw.startswith(b"\xef\xbb\xbf"), "Downloadable CSV must declare UTF-8 with its BOM"
    table = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    assert table.fieldnames == fields and len(fields) == len(set(fields))
    actual = list(table)
    assert len(actual) == len(rows)
    assert [row["id"] for row in actual] == [row["id"] for row in rows]
    assert {"id"} <= set(fields)
    for rendered, original in zip(actual, rows, strict=True):
        assert None not in rendered, "CSV contains unlabelled columns"
        for field in fields:
            value = original[field]
            if isinstance(value, (dict, list, bool)) or value is None:
                assert json.loads(rendered[field]) == value, (original["id"], field, "Lossy CSV value")
            else:
                assert rendered[field] == str(value), (original["id"], field, "Changed CSV text")
    return len(actual)


def verify_source_review(review, data):
    assert review["schema"] == "luoyang-city-layout-r10-source-review-v1"
    assert review["research_version"] == RESEARCH_VERSION and review["target_years"] == [516, 528]
    assert review["baseline_commit"] == data["baseline_commit"]
    assert review["review_mode"] == "existing_repository_sources_only"
    assert all(type(value) is int and value == 0 for value in review["actual_new_acquisition"].values())
    nodes = [node for region in data["regions"] for panel in region["panels"] for node in panel["nodes"]]
    relations = [row for region in data["regions"] for panel in region["panels"] for row in panel["relations"]]
    decisions = [row for region in data["regions"] for row in region["decisions"]]
    gaps = [row for region in data["regions"] for row in region["gaps"]]
    used_by, occurrences = defaultdict(set), 0
    for row in [*nodes, *relations, *decisions, *gaps]:
        for ref in row["source_inputs"]:
            used_by[(ref["path"], ref["pointer"])].add(row["id"])
            occurrences += 1
    paths = {path for path, _ in used_by}
    documents = {path: json.loads((ROOT / path).read_bytes()) for path in paths}
    files = unique(review["reviewed_files"], "path")
    assert set(files) == paths
    for path, row in files.items():
        raw = (ROOT / path).read_bytes()
        assert row["bytes"] == len(raw) and row["sha256"] == digest(raw) == data["source_inputs_sha256"][path]
        assert row["reviewed_pointer_count"] == sum(file == path for file, _ in used_by)
    records = {(row["path"], row["pointer"]): row for row in review["reviewed_records"]}
    assert len(records) == len(review["reviewed_records"]) and set(records) == set(used_by)
    for (path, where), row in records.items():
        original = pointer(documents[path], where)
        canonical = json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        assert row["canonical_record_sha256"] == digest(canonical), (path, where, "Reviewed-record fingerprint differs")
        assert row["used_by"] == sorted(used_by[(path, where)]), (path, where, "Source-review usage join differs")
        preserved(original, row["record_extract"], path + where)
        assert "不是古籍原句" in row["extract_layer"] and "不是新考古发现" in row["extract_layer"]
    entity_ids = {eid for row in [*nodes, *decisions] for eid in row["entity_ids"]}
    road_ids = {rid for row in decisions for rid in row["road_ids"]}
    water_ids = {wid for row in decisions for wid in row["water_ids"]}
    counts = dict(regions=len(data["regions"]), panels=sum(len(region["panels"]) for region in data["regions"]),
                  nodes=len(nodes), relations=len(relations), decisions=len(decisions), gaps=len(gaps),
                  referenced_entity_ids=len(entity_ids), referenced_road_ids=len(road_ids), referenced_water_ids=len(water_ids),
                  reviewed_json_files=len(paths), unique_json_pointers=len(used_by), source_input_occurrences=occurrences,
                  distinct_diagram_entity_ids=len({eid for node in nodes for eid in node["entity_ids"]}), diagram_label_occurrences=len(nodes))
    documentation = unique(review["existing_drawing_records_rechecked_for_documentation"], "path")
    assert set(documentation) == {"research/prosperity-v2/core-scale-basis.json", "research/prosperity-v3/gate-plan.json"}
    for path, row in documentation.items():
        raw = (ROOT / path).read_bytes()
        assert row["bytes"] == len(raw) and row["sha256"] == digest(raw), (path, "Existing drawing documentation changed")
        assert row["review_scope"].strip()
    counts["documentation_only_existing_drawing_files"] = len(documentation)
    assert review["counts"] == counts, "Source-review counts differ from the actual research graph"
    assert review["validation"]["graph_items_with_relevant_decision"] == len(nodes) + len(relations)
    assert review["validation"]["graph_items_without_relevant_decision"] == 0
    assert review["network_reference_policy"]["unassigned_roads"] == 84 - len(road_ids)
    assert review["network_reference_policy"]["unassigned_waters"] == 34 - len(water_ids)
    assert review["regional_register_audit_summary"]["pdf_layout_plan_pages"] == data["pdf_pages"]
    for original in review["primary_original_access"]:
        assert original["original_pages_read"] == [] and original["complete_original_plan_read"] is False
        for reference in original["source_inputs"]:
            pointer(json.loads((ROOT / reference["path"]).read_bytes()), reference["pointer"])
    return dict(reviewed_records=len(records), reviewed_files=len(files), actual_new_acquisition=review["actual_new_acquisition"])


def verify_item_links(element, item, data, region_id):
    """A valid page anchor alone is insufficient: it must carry this evidence."""
    links = list(element.iter(NS + "a"))
    assert links, (item["id"], "Diagram item has no precise evidence link")
    available = {row["id"]: row for row in data["decisions"] if row["region_id"] == region_id}
    sources = {(ref["path"], ref["pointer"]) for ref in item["source_inputs"]}
    for link in links:
        decision = link.get("data-decision")
        if decision:
            assert decision in available, (item["id"], "Evidence link leaves its actual reviewed region")
            row = available[decision]
            joined = sources & {(ref["path"], ref["pointer"]) for ref in row["source_inputs"]}
            entities = set(item.get("entity_ids", [])) & set(row["entity_ids"])
            assert joined or entities, (item["id"], decision, "Valid anchor points to an unrelated judgment")
        else:
            href = link.get("href") or link.get("{http://www.w3.org/1999/xlink}href")
            matches = [(path, where) for path, where in sources
                       if href == "https://github.com/mechgouki/luoyang-city/blob/" + data["source_commit"] + "/" + path
                       and link.get("data-source-pointer") == where]
            assert matches, (item["id"], href, "Diagram link falls back to the page top or an imprecise source")


def verify_page_box(value, page_count, item_id):
    box = json.loads(value) if isinstance(value, str) else value
    assert isinstance(box, list) and len(box) == 4, item_id
    x, y, width, height = map(float, box)
    assert width > 0 and height > 0 and x >= -.02 and y >= -.02, (item_id, "Invalid visible figure bounds")
    assert x + width <= 1680.02 and y + height <= 1188 * page_count + .02, (item_id, "Figure element is clipped by the full canvas")
    page_index = max(0, int((y + .02) // 1188))
    assert y + height <= (page_index + 1) * 1188 + .02, (item_id, "Figure element crosses a PDF crop boundary")


def verify_svg(raw, data, region_id=None, *, standalone=True):
    root = ET.fromstring(raw)
    assert root.tag == NS + "svg"
    assert root.get("id") == ("region-map-" + region_id if region_id else "city-layout-overview")
    viewbox = root.get("viewBox")
    values = [float(value) for value in viewbox.split()]
    assert len(values) == 4 and values[2] > 0 and values[3] > 0
    assert root.get("role") == "img" and list(root.iter(NS + "title")) and list(root.iter(NS + "desc"))
    ids = [element.get("id") for element in root.iter() if element.get("id")]
    assert len(ids) == len(set(ids)), "Duplicate SVG anchors"
    decisions = {row["id"] for row in data["decisions"] if region_id and row["region_id"] == region_id}
    linked = set()
    for element in root.iter():
        identifier = element.get("data-decision")
        if identifier:
            assert identifier in decisions, identifier
            expected = (BASE + PAGE if standalone else "") + "#decision-" + identifier
            assert (element.get("href") or element.get("{http://www.w3.org/1999/xlink}href")) == expected
            linked.add(identifier)
    assert linked == decisions, (region_id or "overview", "Not every decision can be reached from the figure")
    if not region_id:
        region_links = [element for element in root.iter() if element.get("data-region-link")]
        assert [element.get("data-region-link") for element in region_links] == list(REGIONS)
        for element in region_links:
            expected = (BASE + PAGE if standalone else "") + "#region-" + element.get("data-region-link")
            assert element.get("href") == expected
        frames = [element for element in root.iter() if element.get("data-frame") == "frame-06a"]
        assert len(frames) == 1
        frame = frames[0]
        assert frame.get("data-coordinate-space") == "06a-source-pdf-units"
        assert frame.get("data-city-registration") == "false"
        number = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?"
        transform = re.fullmatch(r"translate\((" + number + r")[ ,]+(" + number + r")\)\s+scale\((" + number + r")\)", frame.get("transform", ""))
        assert transform and float(transform.group(3)) > 0, "Source frame was distorted, rotated or reflected"
        historical = copy.deepcopy(root)
        originals = {feature["id"]: feature for feature in json.loads(
            (ROOT / "research/prosperity-v1/geographic-evidence.json").read_bytes())["features"]}
        modern_groups = [element for element in root.iter() if element.get("data-layer") == "modern"]
        for group in modern_groups:
            assert group.get("display") == "none", "A modern reference became visible historical geometry"
        modern_ids = {element.get("data-native-geometry") for group in modern_groups for element in group.iter()
                      if element.get("data-native-geometry")}
        verify_native_features(root, "R10-independent-source-frame")
        for element in historical.iter():
            fid = element.get("data-native-geometry")
            if fid:
                assert json.loads(element.get("data-source-geometry")) == originals[fid]["source_pdf_geometry"]
                assert not element.get("transform"), (fid, "Source ink was moved independently inside its source frame")
                if originals[fid]["layer"] == "layout_envelope":
                    assert element.get("stroke") == "none" and element.get("data-role") == "candidate-fill-not-evidenced-north-wall", (fid, "Candidate fill acquired an unevidenced wall edge")
                elif element.tag == NS + "path":
                    assert "Z" not in element.get("d", "").upper(), (fid, "A source gap was closed without new geometry vertices")
                if fid.startswith("geo-modern-"):
                    assert fid in modern_ids
                    del element.attrib["data-native-geometry"]
        retained = verify_native_features(historical, "overview")
        assert retained == 28
        return dict(source_features=retained, linked_decisions=len(linked), viewbox=viewbox)
    assert root.get("data-region") == region_id
    assert root.get("data-coordinate-space") == "unscaled-relationship"
    page_count = int(root.get("data-pdf-pages"))
    assert page_count in {1, 2}
    assert values == [0, 0, 1680, 1188 * page_count], (region_id, "PDF slices no longer match the complete SVG canvas")
    assert not any(element.get("transform") for element in root.iter()), "Regional display coordinates omit a transform"
    region = next(region for region in data["regions"] if region["id"] == region_id)
    panels = [element for element in root.iter() if element.get("data-panel")]
    assert [element.get("data-panel") for element in panels] == [panel["id"] for panel in region["panels"]]
    panels_per_page = Counter(int(float(json.loads(element.get("data-panel-bounds"))[1]) // 1188) for element in panels)
    assert set(panels_per_page) == set(range(page_count)) and all(1 <= count <= 4 for count in panels_per_page.values()), (region_id, "Continuation page is empty or too densely packed")
    for container, panel in zip(panels, region["panels"], strict=True):
        assert container.get("data-panel-kind") == panel["kind"]
        assert container.get("data-coordinate-space") == "unscaled-relationship"
        verify_page_box(container.get("data-panel-bounds"), page_count, panel["id"])
        visible_panel = "".join("".join(text.itertext()) for text in container.iter(NS + "text"))
        assert "".join(panel["caption"].split()) in "".join(visible_panel.split()), (panel["id"], "Figure lost its full reading boundary")
        nodes = {element.get("data-node"): element for element in container.iter() if element.get("data-node")}
        edges = {element.get("data-relation"): element for element in container.iter() if element.get("data-relation")}
        assert set(nodes) == {node["id"] for node in panel["nodes"]}
        assert set(edges) == {edge["id"] for edge in panel["relations"]}
        for collection, records in ((nodes, panel["nodes"]), (edges, panel["relations"])):
            for record in records:
                element = collection[record["id"]]
                content = "".join("".join(text.itertext()) for text in element.iter(NS + "text"))
                assert "".join(record["label"].split()) in "".join(content.split()), (record["id"], "Figure lost the visible original label")
                assert element.get("data-label") == record["label"]
                assert json.loads(element.get("data-source-inputs")) == record["source_inputs"], record["id"]
                verify_item_links(element, record, data, region_id)
        for record in panel["nodes"]:
            element = nodes[record["id"]]
            assert element.get("data-node-x") is not None and element.get("data-node-y") is not None
            assert element.get("data-basis") == record["basis"]
            assert json.loads(element.get("data-entity-ids")) == record["entity_ids"]
            assert element.get("data-coordinate-space") == "display-only-not-ancient-coordinates"
            assert record["note"] in "".join(element.itertext()), (record["id"], "Node lost its source qualification")
            assert not any(child.get("transform") for child in element.iter()), "Node coordinates omit a display transform"
            links = [child for child in element if child.tag == NS + "a"]
            assert len(links) == 1
            x, y = float(element.get("data-node-x")), float(element.get("data-node-y"))
            box = json.loads(links[0].get("data-link-box"))
            verify_page_box(box, page_count, record["id"])
            assert abs(x - (box[0] + box[2] / 2)) < .002 and abs(y - (box[1] + box[3] / 2)) < .002
            boxes = [child for child in links[0] if child.tag == NS + "rect"]
            if boxes:
                rectangle = boxes[0]
                assert abs(x - (float(rectangle.get("x")) + float(rectangle.get("width")) / 2)) < .002
                assert abs(y - (float(rectangle.get("y")) + float(rectangle.get("height")) / 2)) < .002
        for record in panel["relations"]:
            element = edges[record["id"]]
            assert element.get("data-from") == record["from"] and element.get("data-to") == record["to"]
            assert element.get("data-relation-type") == record["type"]
            assert element.get("data-uncertainty") == record["uncertainty"]
            label_boxes = [child.get("data-visible-label-box") for child in element.iter() if child.get("data-visible-label-box")]
            assert label_boxes, (record["id"], "Full relationship label has no checked visible bounds")
            for box in label_boxes:
                verify_page_box(box, page_count, record["id"])
        # Only literal directional constraints are tested as geometric order.
        # Membership, sequence and identity hypotheses never become metric sites.
        for edge in panel["relations"]:
            if edge["type"] not in {"north_of", "south_of", "east_of", "west_of"}:
                continue
            start, end = nodes[edge["from"]], nodes[edge["to"]]
            if all(element.get("data-node-x") is not None and element.get("data-node-y") is not None for element in (start, end)):
                x1, y1 = float(start.get("data-node-x")), float(start.get("data-node-y"))
                x2, y2 = float(end.get("data-node-x")), float(end.get("data-node-y"))
                correct = {"north_of": y1 < y2, "south_of": y1 > y2, "east_of": x1 > x2, "west_of": x1 < x2}
                assert correct[edge["type"]], (edge["id"], "Drawn direction contradicts its source relation")
    return dict(panels=len(panels), nodes=sum(len(panel["nodes"]) for panel in region["panels"]), pdf_pages=page_count,
                relations=sum(len(panel["relations"]) for panel in region["panels"]), linked_decisions=len(linked), viewbox=viewbox)


def verify_page(raw, data, files, *, offline=False):
    document = Document(raw)
    assert len(document.ids) == len(set(document.ids)), "Duplicate HTML anchors"
    expected = {"region-select", "search", "basis-filter", "clear-filters", "decision-count", "coverage-count",
                "gap-count", "network-count", "city-layout-overview"}
    expected.update("region-" + rid for rid in REGIONS)
    expected.update("decision-" + row["id"] for row in data["decisions"])
    expected.update("entity-" + row["id"] for row in data["coverage"])
    expected.update("network-" + row["id"] for row in data["networks"])
    expected.update("gap-" + row["id"] for row in data["gaps"])
    assert expected <= set(document.ids), (sorted(expected - set(document.ids)), "Required interface or evidence anchor missing")
    if not offline:
        verify_links(raw, files, current=PAGE)
    tree = Tree(raw)
    elements = list(tree.root.walk())
    by_id = {node.attrs["id"]: node for node in elements if node.attrs.get("id")}
    for selector, values in (("region-select", ["all", *REGIONS, "register"]),
                             ("basis-filter", ["all", "source", "relation", "interpretation", "unknown"])):
        assert [node.attrs.get("value") for node in by_id[selector].walk() if node.tag == "option"] == values
    sections = [node for node in elements if node.has_class("region-sheet")]
    assert [node.attrs["id"] for node in sections] == ["region-" + rid for rid in REGIONS]
    assert all("hidden" not in node.attrs for node in sections), "Region sheets must work without JavaScript"
    groups = (("decisions", "decision-row", "decision-", ("title", "judgment", "map_change", "remaining_unknown", "phase_note")),
              ("coverage", "coverage-row", "entity-", ("id", "name", "placement", "next_evidence")),
              ("networks", "network-row", "network-", ("record_id", "name")),
              ("gaps", "gap-card", "gap-", ("title", "known", "unknown", "next_evidence")))
    for name, class_name, prefix, text_fields in groups:
        nodes = [node for node in elements if node.has_class(class_name)]
        assert [node.attrs.get("id") for node in nodes] == [prefix + row["id"] for row in data[name]], name
        for node, row in zip(nodes, data[name], strict=True):
            assert "hidden" not in node.attrs, (row["id"], "No-JavaScript content was hidden")
            regions = row.get("region_ids", [row["region_id"]] if "region_id" in row else [])
            assert node.attrs.get("data-region", "").split() == (regions or ["register"])
            assert node.attrs.get("data-basis") == row["basis"] and node.attrs.get("data-search")
            content = normalized(node.text())
            for field in text_fields:
                assert normalized(str(row[field])) in content, (row["id"], field, "Published row lost evidence content")
            if "source_inputs" in row:
                refs = [(child.attrs.get("data-source-path"), child.attrs.get("data-source-pointer"))
                        for child in node.walk() if child.attrs.get("data-source-path")]
                assert refs == [(ref["path"], ref["pointer"]) for ref in row["source_inputs"]], row["id"]
                for child in node.walk():
                    if child.attrs.get("data-source-path"):
                        assert child.tag == "a"
                        expected_href = "https://github.com/mechgouki/luoyang-city/blob/" + data["source_commit"] + "/" + child.attrs["data-source-path"]
                        assert child.attrs.get("href") == expected_href
                        assert child.attrs["data-source-pointer"] in node.text()
            if row.get("source_evidence"):
                shown = [child for child in node.walk() if child.has_class("source-excerpt")]
                assert [normalized(child.text()) for child in shown] == [normalized(item["excerpt"]) for item in row["source_evidence"]]
                assert not any(child.tag == "blockquote" for child in node.walk()), "Record excerpt was displayed as a fresh original quotation"
            if name == "networks":
                source_links = [child for child in node.walk() if child.attrs.get("data-published-source-path")]
                assert len(source_links) == 1
                source_link = source_links[0]
                assert source_link.attrs["data-published-source-path"] == row["source_path"]
                assert source_link.attrs["data-source-pointer"] == row["source_pointer"]
                assert source_link.attrs["href"] == BASE + row["source_path"]
                assert row["source_pointer"] in node.text()
                assert row["source_url"] in [child.attrs.get("href") for child in node.walk() if child.tag == "a"]
    figures = re.findall(rb"<svg\b.*?</svg>", raw, flags=re.DOTALL)
    assert len(figures) == 12, "Page lacks one of its twelve complete inline SVGs"
    verify_svg(figures[0], data, standalone=False)
    for rid, figure in zip(REGIONS, figures[1:], strict=True):
        verify_svg(figure, data, rid, standalone=False)
    viewports = [node for node in elements if node.has_class("map-viewport")]
    assert [node.attrs.get("data-map-id") for node in viewports] == ["overview", *REGIONS]
    actions = {"zoom-in", "zoom-out", "reset", "pan-left", "pan-right", "pan-up", "pan-down"}
    for map_id in ("overview", *REGIONS):
        buttons = [node for node in elements if node.attrs.get("data-map-target") == map_id]
        assert {node.attrs.get("data-action") for node in buttons} == actions
    return document, figures


def verify(info, reader, *, build_control_reader=None):
    get = lru_cache(maxsize=None)(reader)
    hashes, meta = info["files_sha256"], info[KEY]
    assert meta["page"] == PAGE and meta["manifest"] == MANIFEST and meta["bundle"] == BUNDLE and meta["pdf"] == PDF
    assert meta["offline_entry"] == "index.html"
    assert json.loads(get(MANIFEST)) == meta, "Live manifest differs from build-info"
    resources = meta["files_sha256"]
    expected_resources = {path for path in hashes if path.startswith(FOLDER + "/") and path != MANIFEST} | {PAGE, PDF}
    assert set(resources) == expected_resources, "R10 manifest omits a published resource"
    mandatory = {DATA, REVIEW, PAGE, PDF, RELEASE_ARCHIVE, *HOME_ARCHIVES.values(), *SVGS, *CSVS.values(),
                 FOLDER + "/atlas.css", FOLDER + "/atlas.js"}
    assert mandatory <= set(resources)
    for path in [*resources, MANIFEST, BUNDLE, "release.json", *HOME_PAGES]:
        raw = get(path)
        assert isinstance(raw, bytes), (path, "Reader did not return actual resource bytes")
        assert digest(raw) == hashes[path], (path, "Published hash mismatch")
        if path in resources:
            assert resources[path] == hashes[path], (path, "Manifest hash mismatch")
    for suffix in ("css", "js"):
        assert get(FOLDER + "/atlas." + suffix) == (ROOT / "web" / (VERSION + "." + suffix)).read_bytes()
    restored, old_reader = restore_r9_context(info, get)
    assert KEY not in restored
    assert set(meta["predecessor_homepage"]) == set(HOME_PAGES)
    for page in HOME_PAGES:
        assert meta["predecessor_homepage"][page] == dict(archive=HOME_ARCHIVES[page], sha256=meta["homepage_before_sha256"][page])
        assert old_reader(page) == get(HOME_ARCHIVES[page])

    protected, controls = meta["protected_files_sha256"], meta["build_control_files_sha256"]
    new_files = set(resources) | {MANIFEST, BUNDLE, *HOME_PAGES, "release.json"}
    assert set(controls) == BUILD_CONTROL_FILES & set(hashes)
    assert set(protected) == set(hashes) - new_files - set(controls), "Protected predecessor inventory is incomplete"
    assert not (set(protected) & BUILD_CONTROL_FILES)
    for path, checksum in protected.items():
        assert digest(get(path)) == hashes[path] == checksum, (path, "Previous publication changed")
    for path, checksum in controls.items():
        assert checksum == hashes[path]
        if build_control_reader:
            assert digest(build_control_reader(path)) == checksum
    assert digest(get(V12.full)) == V12.full_sha and digest(get(V12.small)) == V12.small_sha

    data = json.loads(get(DATA))
    assert data["published_inputs_sha256"] == meta["published_inputs_sha256"]
    assert PUBLIC_INPUTS <= set(data["published_inputs_sha256"])
    public_inputs = {}
    for path, checksum in data["published_inputs_sha256"].items():
        assert digest(get(path)) == checksum == hashes[path], (path, "Published source input changed")
        if path.endswith(".json"):
            public_inputs[path] = json.loads(get(path))
    research = verify_data(data, meta, info, public_inputs)
    network_pages = {kind: Document(get(path)) for kind, path in
                     (("road", "luoyang-all-roads.html"), ("water", "luoyang-water-atlas.html"))}
    for row in data["networks"]:
        old_page = "luoyang-all-roads.html" if row["kind"] == "road" else "luoyang-water-atlas.html"
        assert row["source_url"] == BASE + old_page + "#" + row["record_id"]
        assert row["record_id"] in network_pages[row["kind"]].ids, (row["id"], "Previous network anchor no longer resolves")
    assert get(REVIEW) == (ROOT / SOURCE_REVIEW).read_bytes(), "Source-access report changed in publication"
    review = json.loads(get(REVIEW))
    review_result = verify_source_review(review, data)
    assert set(data["csv_fields"]) == set(CSVS)
    for name, required in CSV_REQUIRED.items():
        assert required <= set(data["csv_fields"][name]), (name, "CSV omitted required evidence columns")
    csv_counts = {name: verify_csv(get(path), data[name], data["csv_fields"][name]) for name, path in CSVS.items()}
    assert get(PDF).startswith(b"%PDF-") and get(PDF).rstrip().endswith(b"%%EOF")
    maps = {"overview": verify_svg(get(OVERVIEW), data)}
    for rid, path in zip(REGIONS, SVGS[1:], strict=True):
        maps[rid] = verify_svg(get(path), data, rid)
    next_page, region_pages = 1, {}
    for rid in REGIONS:
        region_pages[rid] = next_page
        next_page += maps[rid]["pdf_pages"]
    pdf_pages = next_page + 1
    assert data["pdf_pages"] == data["counts"]["pdf_pages"] == meta["pdf_pages"] == pdf_pages
    assert meta["region_pages"] == region_pages, "PDF index does not point to each region's actual first page"
    document, inline = verify_page(get(PAGE), data, hashes)
    for path, figure in zip(SVGS, inline, strict=True):
        assert get(path) == figure.replace(b'href="#', ('href="' + BASE + PAGE + '#').encode()), (path, "Inline and download figure differ")
    downloads = [*SVGS, PDF, *CSVS.values(), DATA, REVIEW, MANIFEST, BUNDLE]
    primary_downloads = [attrs["data-download"] for tag, attrs in document.elements if tag == "a" and "data-download" in attrs]
    assert len(downloads) == 21 and set(document.downloads) == set(meta["download_files"]) == set(downloads)
    assert len(primary_downloads) == len(meta["download_files"]) == len(downloads)
    assert primary_downloads == meta["download_files"]

    with ZipFile(io.BytesIO(get(BUNDLE))) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)), "Duplicate offline archive members"
        expected_members = set(resources) | {MANIFEST, "index.html"}
        assert set(names) == expected_members, "Offline bundle is incomplete or contains unexpected files"
        for member in archive.infolist():
            path = PurePosixPath(member.filename)
            assert not path.is_absolute() and ".." not in path.parts and "\\" not in member.filename
            assert not member.is_dir() and not stat.S_ISLNK(member.external_attr >> 16)
            if member.filename != "index.html":
                assert archive.read(member.filename) == get(member.filename), (member.filename, "Offline content differs")
        offline = archive.read("index.html")
        verify_page(offline, data, hashes, offline=True)
        # Only links to resources not in this archive may be made absolute.
        expected_offline = get(PAGE)
        page_tree = Tree(expected_offline)
        for element in page_tree.root.walk():
            if element.tag != "a" or not element.attrs.get("href"):
                continue
            href = element.attrs["href"]
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            path = parsed.path.removeprefix("./")
            if path not in expected_members or path == "index.html":
                expected_offline = expected_offline.replace(('href="' + href + '"').encode(), ('href="' + BASE + path +
                                                          ("?" + parsed.query if parsed.query else "") +
                                                          ("#" + parsed.fragment if parsed.fragment else "") + '"').encode())
        assert offline == expected_offline, "Offline HTML differs beyond its required navigation rewrites"
        archive_count = len(names)
    return dict(status="passed", source_commit=info["source_commit"], research=research, source_review=review_result, csv_rows=csv_counts,
                maps=maps, pdf_pages=pdf_pages, region_pages=region_pages, downloads=len(downloads), offline_members=archive_count,
                protected_public_files=len(protected), reversible_homepages=len(HOME_PAGES),
                new_historical_coordinates=0, new_shoreline_geometries=0, evidence_grade_upgrades=0,
                homepage_revision=V12.revision, homepage_replacement_approved=False)
