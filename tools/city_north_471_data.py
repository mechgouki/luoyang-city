"""Reuse northern-city source geometry and reviewed text without new locations.

Public API: ``build_data(root: Path) -> dict``.  This assembler performs no
writes.  The B4 records remain intact; display code must read
``evidence[*].reading_overlay.quote`` so the inherited NG15 correction cannot
silently revert to its legacy mixed-layer quotation.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from city_common_470_data import build_data as build_common


PLAN_PATH = "research/prosperity-v4/north-471/reuse-plan.json"
NORTH_PATH = "research/dual-b4/north-gates.json"
REVIEW_PATH = "research/prosperity-v1/text-review.json"
GEO_PATH = "research/prosperity-v1/geographic-evidence.json"
ENTITY_PATH = "data/entities.json"
WATER_PATH = "research/prosperity-v4/backbone-469/readings.json"
ROADS_PATH = "research/prosperity-v4/network-462/roads.json"
DIRECT_INPUTS = (NORTH_PATH, REVIEW_PATH, GEO_PATH, ENTITY_PATH, WATER_PATH, ROADS_PATH)
VERSION = "P4.7.1"
ADDITIONS = ("geo-jinyong-bing-wall", "geo-jinyong-bing-reference")
NORTH_IDS = tuple(f"NG{number:02d}" for number in range(1, 17))
REFERENCE_NAMES = {
    "north_wall_buildings": "两门之间城上宫观（集合叙述）",
    "road_daxia": "大夏门御道（文献参照）",
    "road_guangmo": "广莫门御道（文献参照）",
    "city_gate_or_palace_unspecified": "城阙（所指未定）",
    "luoyang_city": "洛阳城（整体参照）",
    "tile_making_activity": "制瓦活动（功能叙述）",
    "road_before_jinyong": "金墉城前东西大道（文献参照）",
    "city_reference_in_jinyong_context": "金墉语境中的城（指代待定）",
}


def _require(condition, message):
    if not condition:
        raise ValueError("P471 source review required: " + message)


def _read(root, relative, expected=None):
    raw = (root / relative).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None:
        _require(digest == expected, "frozen input changed: " + relative)
    return json.loads(raw.decode("utf-8")), digest


def _indexed(rows, key, label):
    result = {row[key]: row for row in rows}
    _require(len(result) == len(rows), "duplicate " + label)
    return result


def _overlay(original, review, sources):
    """Add display fields, retaining the original B4 quote separately."""
    _require(review["legacy_quote"] == original["quote"], "P1/B4 quote identity " + original["id"])
    _require(review["legacy_path"] == NORTH_PATH, "P1/B4 source path " + original["id"])
    _require(review["legacy_reading_preserved"] == original["reading"],
             "P1/B4 interpretation identity " + original["id"])
    _require(review["legacy_temporal_note_preserved"] == original["temporal_note"],
             "P1/B4 temporal note identity " + original["id"])
    _require(review["geographic_coordinates"] is None,
             "text review cannot provide coordinates")
    manual = review["manual_context_review"]
    correction = manual is not None and bool(manual.get("corrected_quote"))
    annotations = []
    source_ids = list(original["sources"])
    if correction:
        _require(original["id"] == "NG15"
                 and manual["kind"] == "modern_annotation_mixed_into_ancient_quote",
                 "unexpected new northern text correction")
        quote = manual["corrected_quote"]
        for context in manual["source_contexts"]:
            matching = [key for key, source in sources.items() if source["url"] == context["url"]]
            _require(len(matching) == 1, "reviewed northern source URL is unregistered")
            if matching[0] not in source_ids:
                source_ids.append(matching[0])
            if context["layer"] == "现代夹注":
                annotation = deepcopy(context)
                annotation["author"] = manual["editorial_note"]["author"]
                annotations.append(annotation)
        _require(len(annotations) == 2, "NG15 must expose both modern notes separately")
        _require(all(note["quote"].rstrip("。") not in quote for note in annotations),
                 "NG15 modern note leaked back into the displayed body")
        _require(all(check["status"] == "matched" for check in manual["corrected_excerpt_checks"]),
                 "NG15 corrected body must retain its existing source checks")
    else:
        _require(manual is None and review["legacy_quote_passed_normalized_sequence_check"],
                 "unresolved northern excerpt: " + original["id"])
        quote = original["quote"]
    return {
        "quote": quote,
        "textual_layer": "古籍正文（继承P1现行分层校读）" if correction else original["textual_layer"],
        "annotations": annotations,
        "review_key": review["key"],
        "review_source_path": REVIEW_PATH,
        "locator": manual["locator"] if correction else original["quote_locator"],
        "status": "corrected_body_with_separate_modern_annotations" if correction else "legacy_excerpt_reviewed",
        "status_label": "正文与现代夹注已分列" if correction else "沿用P1已核引文",
        "correction_applied": correction,
        "source_links": [deepcopy(sources[key]) for key in source_ids],
        "checked_source_ids": [row["declared_source_id"] for row in review["source_checks"]],
        "scope": review["checked_scope"],
        "legacy_quote_display_allowed_as_body": not correction,
        "new_historical_discovery": False,
    }


def build_data(root: Path) -> dict:
    root = Path(root)
    plan, plan_sha = _read(root, PLAN_PATH)
    _require(plan["version"] == VERSION, "reuse-plan version")
    _require(plan["added_existing_feature_ids"] == list(ADDITIONS), "only two existing Jinyong additions")
    common = build_common(root)
    expected = plan["required_input_sha256"]
    _require(set(expected) == set(common["source_inputs_sha256"]) | {NORTH_PATH, ENTITY_PATH},
             "input inventory differs from the common view plus B4 and existing entities")
    for relative, digest in common["source_inputs_sha256"].items():
        _require(expected[relative] == digest, "common input identity: " + relative)
    documents = {}
    hashes = dict(common["source_inputs_sha256"])
    for relative in DIRECT_INPUTS:
        documents[relative], digest = _read(root, relative, expected[relative])
        _require(relative not in hashes or hashes[relative] == digest, "conflicting input digest")
        hashes[relative] = digest
    hashes[PLAN_PATH] = plan_sha

    geo = documents[GEO_PATH]
    source_features = _indexed(geo["features"], "id", "source feature IDs")
    _require(geo["crs"] == "EPSG:4610" and common["source_frame"]["id"] == "frame-06a",
             "keep the original Xian 1980 source frame")
    common_ids = [feature["id"] for feature in common["features"]]
    _require(not set(ADDITIONS) & set(common_ids), "Jinyong additions already present")
    features = deepcopy(common["features"]) + [deepcopy(source_features[key]) for key in ADDITIONS]
    feature_ids = [feature["id"] for feature in features]
    _require(len(feature_ids) == len(set(feature_ids)), "duplicate display feature")
    _require(all(feature == source_features[feature["id"]] for feature in features),
             "all original source feature fields and geometry must remain unchanged")
    walls, point = (source_features[key] for key in ADDITIONS)
    _require(all(item["entity_id"] == "ic_jinyong"
                 and item["entity_binding_scope"] == "partial_component_reference"
                 for item in (walls, point)), "Jinyong remains a partial-component reference")
    wall_geometry = walls["source_pdf_geometry"]
    point_geometry = point["source_pdf_geometry"]
    _require(wall_geometry["type"] == "MultiLineString" and point_geometry["type"] == "Point",
             "Jinyong original geometry kinds")
    parts = wall_geometry["coordinates"]
    vertices = [xy for part in parts for xy in part]
    _require(len(parts) == 5 and len(vertices) == 13 and all(part[0] != part[-1] for part in parts),
             "five open Jinyong wall parts and thirteen original vertices")
    _require(point["approximation"]["status"] == "representative_point_within_mapped_remains"
             and not point["approximation"]["is_field_verified_gcp"], "representative point is not a gate or control")
    for frame in plan["display_frames"].values():
        xmin, ymin, xmax, ymax = frame["native_bounds"]
        _require(frame["native_units"] == "PDF point" and frame["semantics"] == "display_crop_only",
                 "display bounds must not be claimed as new geographic registration")
        _require(all(xmin <= x <= xmax and ymin <= y <= ymax
                     for x, y in [*vertices, point_geometry["coordinates"]]),
                 "Jinyong original geometry falls outside its reviewed display frame")

    northern = documents[NORTH_PATH]
    original_evidence = deepcopy(northern["evidence"])
    originals = _indexed(original_evidence, "id", "B4 evidence IDs")
    _require(tuple(originals) == NORTH_IDS, "retain all sixteen B4 evidence records")
    _require(northern["ancient_absolute_positions_added"] == 0
             and all(row["geographic_coordinates"] is None for row in original_evidence),
             "B4 evidence has no historical geographic coordinates")
    reviews = {row["key"]: row for row in documents[REVIEW_PATH]["records"] if row["batch"] == "B4"}
    _require(set(reviews) == {"B4:" + key for key in NORTH_IDS}, "sixteen corresponding P1 reviews")
    sources = _indexed(northern["sources"], "id", "B4 source IDs")
    _require(set(sources) == {"Z1", "F1", "Z5", "F5"}, "four inherited electronic editions")
    evidence = []
    for original in original_evidence:
        row = deepcopy(original)
        row["reading_overlay"] = _overlay(original, reviews["B4:" + original["id"]], sources)
        _require({key: value for key, value in row.items() if key != "reading_overlay"} == original,
                 "B4 record was overwritten: " + original["id"])
        evidence.append(row)
    groups = deepcopy(plan["evidence_groups"])
    grouped_ids = [identifier for group in groups for identifier in group["evidence_ids"]]
    _require(len(grouped_ids) == 16 and set(grouped_ids) == set(NORTH_IDS),
             "three reading groups must cover each original record once")

    entities = _indexed(documents[ENTITY_PATH], "id", "existing entity IDs")
    entity_ids = sorted({identifier for row in original_evidence for identifier in row["entities"]})
    _require(all(identifier in entities for identifier in entity_ids), "B4 entity missing from current inventory")
    entity_names = {identifier: entities[identifier]["name"] for identifier in entity_ids}
    entity_bindings = []
    for identifier in entity_ids:
        matches = [item for item in features if item.get("entity_id") == identifier]
        scopes = {item["entity_binding_scope"] for item in matches}
        _require(len(scopes) <= 1, "conflicting northern source binding scopes")
        entry_ids = [key for key, value in plan["north_entry_entities"].items() if value == identifier]
        _require(len(entry_ids) <= 1, "duplicate northern entry entity")
        entity_bindings.append({
            "entity_id": identifier, "name": entities[identifier]["name"],
            "type": entities[identifier]["type"],
            "temporal_state": entities[identifier].get("temporal_state"),
            "feature_ids": [item["id"] for item in matches],
            "binding_scope": next(iter(scopes)) if scopes else None,
            "entry_id": entry_ids[0] if entry_ids else None,
            "geographic_coordinates": None,
            "scope": ("仅沿用来源图组成参照，不定位完整金墉三城。" if identifier == "ic_jinyong" else
                      "仅沿用同名城门图符，文献关系不继承坐标。") if matches else
                     "保留文献对象身份；本批无来源图地理绑定，不生成图上位置。",
        })
    bound = [row for row in entity_bindings if row["feature_ids"]]
    _require({row["entity_id"] for row in bound} == {"ic_jinyong", "gate_daxia", "gate_guangmo"},
             "only the three original northern source identities are available")
    _require(entities["n_chanxu"]["temporal_state"] == "undated", "Chanxu's date must remain undetermined")
    constraints = [item for row in original_evidence for item in row["constraints"]]
    roles = set()
    for item in constraints:
        roles.add(item["subject"])
        if "object" in item:
            roles.add(item["object"])
        roles.update(item.get("objects", []))
    _require(roles - set(entity_ids) == set(REFERENCE_NAMES), "the original relation-role inventory changed")
    _require(originals["NG04"]["constraints"][1]["basis"] == "editorial_supplement"
             and originals["NG07"]["constraints"][0]["distance_endpoints"] is None,
             "keep the visible supplement and the unlocated one-li endpoints")

    water = _indexed(documents[WATER_PATH]["current_relations"], "ref", "current water refs")
    water_relations = [deepcopy(water[key]) for key in plan["water_relation_ids"]]
    _require(all(row["geographic_coordinates"] is None
                 and not row["annual_flow_516_528_confirmed"] for row in water_relations),
             "water records cannot gain coordinates or annual flow confirmation")
    road_source = documents[ROADS_PATH]
    road_index = _indexed(road_source["routes"], "code", "road codes")
    roads = [deepcopy(road_index[key]) for key in plan["road_codes"]]
    _require(all(row["source_pdf_geometry"] == source_features[row["p1_feature_id"]]["source_pdf_geometry"]
                 for row in roads), "north road source geometry changed")
    road_source_ids = {identifier for row in roads for identifier in row["source_ids"]}
    road_sources = [deepcopy(item) for item in road_source["sources"] if item["id"] in road_source_ids]
    _require({row["id"] for row in road_sources} == road_source_ids, "missing inherited road source")

    entry_copy = {
        "N01": {
            "name": "金墉丙城", "point_feature_id": "geo-jinyong-bing-reference",
            "role_label": "丙城部分遗存与范围内代表点",
            "scope": "五段原图残墙与一个已登记的范围内图示代表点；只代表金墉丙城部分。代表点不是门址、实测控制点或完整金墉中心，不用310×240米附表值闭合墙线。",
            "water_scope": "只联读原文金墉城北的既有水程；原文全城叙述不改指丙城，水线不落在丙城残墙北侧。",
            "detail_links": [{"label": "北门—金墉原文献专题", "href": "dual-north.html"},
                             {"label": "北垣河道与承明道路核读", "href": "prosperity-gates-p465.html"}],
        },
        "N02": {
            "name": "大夏门", "point_feature_id": "geo-daxia-gate",
            "role_label": "来源图门址图符中心",
            "scope": "沿用大夏门同名身份和来源图符。三层楼及营造主体保留原校读与年代限制；禅虚寺、两种武场和光风园不因门址参照而获得坐标。",
            "water_scope": "沿用大夏门相关水程的阅读入口；东行支与入华林园支分别保存，不新增分支点或门下古河槽。",
            "detail_links": [{"label": "大夏门水系上下文", "href": "prosperity-backbone-p469.html#context-geo-daxia-gate"},
                             {"label": "北门—金墉原文献专题", "href": "dual-north.html"}],
        },
        "N03": {
            "name": "广莫门", "point_feature_id": "geo-guangmo-gate",
            "role_label": "来源图门址图符中心",
            "scope": "沿用广莫门同名身份和来源图符。凝玄的门外、路东与永平里属分别阅读；一里不定位坊界，高显不匹配现代高点，闻义里不强挂御道一侧。",
            "water_scope": "联读广莫门北转向建春门的文字行程；不补古岸线，也不由该水段推定邙山北路终点。",
            "detail_links": [{"label": "广莫门水系上下文", "href": "prosperity-backbone-p469.html#context-geo-guangmo-gate"},
                             {"label": "北门—金墉原文献专题", "href": "dual-north.html"}],
        },
    }
    north_entries = []
    for entry_id, content in entry_copy.items():
        row = {"id": entry_id, **deepcopy(content),
               "entity_id": plan["north_entry_entities"][entry_id],
               "feature_ids": deepcopy(plan["north_entry_features"][entry_id]),
               "evidence_ids": deepcopy(plan["north_entry_evidence"][entry_id]),
               "water_relation_ids": deepcopy(plan["north_entry_water_relations"][entry_id]),
               "navigation_semantics": "context_link_only"}
        _require(all(key in feature_ids for key in row["feature_ids"])
                 and row["point_feature_id"] in row["feature_ids"], "entry's original feature reference")
        _require(all(source_features[key]["entity_id"] == row["entity_id"] for key in row["feature_ids"]),
                 "entry cannot introduce a new entity binding")
        _require(set(row["evidence_ids"]) <= set(NORTH_IDS)
                 and set(row["water_relation_ids"]) <= set(plan["water_relation_ids"]),
                 "entry refers to an unavailable existing record")
        north_entries.append(row)

    counts = {
        "source_features": len(geo["features"]), "features": len(features),
        "site_remains": sum(row["layer"] == "site_remains" for row in features),
        "modern_features": sum(row["layer"] == "modern_geographic_reference" for row in features),
        "prior_common_features": len(common["features"]), "added_existing_features": len(ADDITIONS),
        "north_entries": len(north_entries), "evidence_records": len(evidence),
        "evidence_groups": len(groups), "entities": len(entity_ids),
        "bound_entities": len(bound), "unbound_entities": len(entity_ids) - len(bound),
        "source_binding_features": sum(len(row["feature_ids"]) for row in bound),
        "constraints": len(constraints), "water_relations": len(water_relations), "roads": len(roads),
        "jinyong_wall_parts": len(parts), "jinyong_wall_vertices": len(vertices),
        "corrected_quotations": sum(row["reading_overlay"]["correction_applied"] for row in evidence),
        "modern_annotations": sum(len(row["reading_overlay"]["annotations"]) for row in evidence),
        "new_geographic_coordinates": 0, "new_metric_measurements": 0,
        "new_historical_relationships": 0, "new_geographic_footprints": 0,
    }
    _require(counts == plan["expected_counts"], "northern inventory or source-only accounting changed")
    source_frame = deepcopy(common["source_frame"])
    source_frame.update(display_feature_count=len(features), display_feature_ids=feature_ids,
                        prior_common_display_feature_ids=common_ids, added_existing_feature_ids=list(ADDITIONS))
    return {
        "schema_version": "1.0.0", "version": VERSION,
        "title": "北门、金墉与北城用地：同源位置和文献关系联读",
        "study_date": plan["study_date"], "source_baseline_commit": plan["source_baseline_commit"],
        "target_period": common["target_period"], "phase_rule": common["phase_rule"],
        "common": common, "source_frame": source_frame, "features": features,
        "north_entries": north_entries, "original_evidence": original_evidence,
        "evidence": evidence, "evidence_groups": groups, "entity_names": entity_names,
        "reference_names": deepcopy(REFERENCE_NAMES), "entity_bindings": entity_bindings,
        "source_records": deepcopy(sources), "text_review_records": deepcopy(reviews),
        "water_relations": water_relations, "roads": roads, "road_sources": road_sources,
        "source_inputs_sha256": hashes, "counts": counts,
        "constraint_basis_counts": dict(Counter(row["basis"] for row in constraints)),
        "constraint_accounting": plan["constraint_accounting"],
        "limitations": deepcopy(plan["limitations"]),
        "display_frames": deepcopy(plan["display_frames"]),
        "modern_feature_id": common["modern_feature_id"], "modern_reference_default_visible": False,
        "new_geographic_transform": None,
        "road_role_bindings": [],
        "water_navigation_semantics": "context_link_only",
    }
