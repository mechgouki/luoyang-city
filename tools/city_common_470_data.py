"""Assemble P4.7 from frozen source records without changing their geometry.

Public API: build_data(root: Path) -> dict.  This module performs no writes.
The common map adds three already published source features to P469's 22-feature
view.  It does not create coordinates, entity identities, or historical edges.
"""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from city_common_470_relations import build_relations


PLAN_PATH = "research/prosperity-v4/common-470/reuse-plan.json"
GEO_PATH = "research/prosperity-v1/geographic-evidence.json"
PLACES_PATH = "research/prosperity-v4/city-distribution-p451.json"
NETWORK_PATH = "research/prosperity-v4/network-462/network.json"
ROADS_PATH = "research/prosperity-v4/network-462/roads.json"
BACKBONE_PATH = "research/prosperity-v4/backbone-469/readings.json"
JIANCHUN_PATH = "research/prosperity-v4/backbone-469/jianchun-plan-audit.json"
CORE_INPUTS = (GEO_PATH, PLACES_PATH, NETWORK_PATH, ROADS_PATH, BACKBONE_PATH, JIANCHUN_PATH)
VERSION = "P4.7"


def _require(condition, message):
    if not condition:
        raise ValueError("P470 source review required: " + message)


def _read(root, relative, expected_sha256=None):
    raw = (root / relative).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None:
        _require(digest == expected_sha256, "frozen input changed: " + relative)
    return json.loads(raw.decode("utf-8")), digest


def _unique(items, key, label):
    result = {item[key]: item for item in items}
    _require(len(result) == len(items), "duplicate " + label)
    return result


def build_data(root: Path) -> dict:
    """Return a complete source-preserving dataset for the independent P470 page.

    features, roads, gates, enclosure_context and water records are exact deep
    copies of the cited source records.  places retain every P451 field and add
    reading_navigation only.  That field is a UI association, never a new site
    binding or a geographic relation.  urban is returned by the independent
    relation assembler without rewriting its nodes or edges.
    """
    root = Path(root)
    plan, plan_sha = _read(root, PLAN_PATH)
    _require(plan["version"] == VERSION, "reuse-plan version")
    expected_hashes = plan["required_input_sha256"]
    _require(set(expected_hashes) == set(CORE_INPUTS), "core input inventory")
    inputs, hashes = {}, {PLAN_PATH: plan_sha}
    for relative in CORE_INPUTS:
        inputs[relative], hashes[relative] = _read(root, relative, expected_hashes[relative])

    geo = inputs[GEO_PATH]
    distribution = inputs[PLACES_PATH]
    network = inputs[NETWORK_PATH]
    road_data = inputs[ROADS_PATH]
    backbone = inputs[BACKBONE_PATH]
    jianchun = inputs[JIANCHUN_PATH]
    feature_lookup = _unique(geo["features"], "id", "source feature IDs")
    cards = _unique(distribution["anchored_buildings"], "id", "building card IDs")
    _require(geo["crs"] == "EPSG:4610", "source CRS must remain Xian 1980")
    _require({key: value["feature_id"] for key, value in cards.items()}
             == plan["expected_card_feature_ids"], "P451 four-card identity map")
    _require(distribution["inputs"]["source_geography"] == GEO_PATH, "P451 source map")
    _require(road_data["source_data"] == GEO_PATH, "P462 source map")
    _require(road_data["source_sha256"] == hashes[GEO_PATH], "P462 geometry provenance")
    _require(backbone["input_sha256"][GEO_PATH] == hashes[GEO_PATH], "P469 geometry provenance")
    source_frame = next(frame for frame in backbone["frames"]
                        if frame["id"] == plan["source_frame_id"])
    _require(source_frame["input"] == GEO_PATH and source_frame["crs"] == geo["crs"],
             "P469 source frame identity")

    road_ids = [route["p1_feature_id"] for route in road_data["routes"]]
    gate_ids = [gate["id"] for gate in network["gates"]]
    wall_ids = list(plan["prior_backbone_wall_feature_ids"])
    modern_id = plan["modern_feature_id"]
    previous_ids = [*wall_ids, *road_ids, *gate_ids, modern_id]
    _require(len(previous_ids) == len(set(previous_ids)), "P469 display IDs must be unique")
    _require([row["p1_feature_id"] for row in source_frame["road_bindings"]] == road_ids,
             "P469 and P462 road inventory differs")
    for route in road_data["routes"]:
        feature = feature_lookup[route["p1_feature_id"]]
        _require(route["source_pdf_geometry"] == feature["source_pdf_geometry"],
                 "road vertices or original parts differ: " + route["code"])
    for gate in network["gates"]:
        feature = feature_lookup[gate["id"]]
        _require(feature["source_pdf_geometry"]["type"] == "Point"
                 and gate["point"] == feature["source_pdf_geometry"]["coordinates"],
                 "gate center differs from P1: " + gate["id"])

    _require(len(distribution["enclosure_context"]) == 1, "P451 enclosure inventory")
    enclosure = distribution["enclosure_context"][0]
    enclosure_id = enclosure["feature_id"]
    _require(enclosure_id == plan["expected_enclosure_feature_id"]
             and not enclosure["closed_polygon_allowed"], "Yongning partial enclosure role")
    _require(feature_lookup[enclosure_id]["source_pdf_geometry"]["type"] == "MultiLineString",
             "Yongning walls must remain open source parts")
    added_ids = [card["feature_id"] for card in distribution["anchored_buildings"]
                 if card["feature_id"] not in previous_ids]
    if enclosure_id not in previous_ids and enclosure_id not in added_ids:
        added_ids.append(enclosure_id)
    _require(added_ids == plan["expected_added_existing_feature_ids"],
             "additional objects must be the three existing P451 features")
    feature_ids = [*previous_ids, *added_ids]
    _require(len(feature_ids) == len(set(feature_ids)), "duplicate common-view features")
    features = [deepcopy(feature_lookup[identifier]) for identifier in feature_ids]
    wall_ids.append(enclosure_id)

    urban = build_relations(root)
    _require(urban["source_inputs_sha256"] == plan["required_urban_input_sha256"],
             "frozen urban inputs changed")
    for relative, digest in urban["source_inputs_sha256"].items():
        actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        _require(actual == digest, "urban source digest mismatch: " + relative)
        _require(relative not in hashes or hashes[relative] == digest,
                 "conflicting source digest: " + relative)
        hashes[relative] = digest
    _require(urban["new_historical_relationships"] == 0
             and urban["new_historical_coordinates"] == 0, "urban source-only accounting")
    scene_ids = {scene["id"] for scene in urban["clusters"]}
    source_bindings = urban["scene_bindings"]
    places = []
    for original in distribution["anchored_buildings"]:
        card = deepcopy(original)
        feature = feature_lookup[card["feature_id"]]
        _require(card["entity_id"] == feature.get("entity_id"),
                 "card entity must keep the original value, including null: " + card["id"])
        _require(feature["source_pdf_geometry"]["type"] == "Point"
                 and not card["site_registered_polygon_allowed"],
                 "building card must refer to a point, not a registered footprint")
        policy = plan["place_navigation_policy"][card["id"]]
        binding_id = policy["scene_binding_feature_id"]
        selected_ids = [card["feature_id"]]
        bindings = []
        if binding_id is not None:
            bindings = [deepcopy(binding) for binding in source_bindings
                        if binding["feature_id"] == binding_id]
            _require(len(bindings) == 1, "unique existing scene binding for " + card["id"])
            _require(bindings[0]["entity_id"] == card["entity_id"],
                     "scene navigation cannot change entity identity")
            _require(bindings[0]["cluster_id"] in scene_ids, "missing source scene")
            _require(binding_id in feature_ids, "scene reference not present in common map")
            if binding_id != card["feature_id"]:
                _require(card["id"] == "C04" and binding_id == enclosure_id,
                         "only Yongning component-to-enclosure navigation is authorized")
                selected_ids.append(binding_id)
        else:
            _require(card["id"] == "C03" and card["entity_id"] is None,
                     "unbound Taiji must remain a feature-only reference")
        card["reading_navigation"] = {
            "semantics": "project_reading_navigation_only",
            "selection_feature_ids": selected_ids,
            "scene_binding_feature_id": binding_id,
            "scene_bindings": bindings,
            "urban_cluster_ids": [binding["cluster_id"] for binding in bindings],
            "scope": policy["scope"],
            "detail_links": deepcopy(policy["detail_links"]),
        }
        _require({key: value for key, value in card.items() if key != "reading_navigation"}
                 == original, "P451 card fields were changed")
        places.append(card)

    jianchun_status = jianchun["read_status"]
    _require(jianchun_status["geographic_transform"] is None
             and jianchun_status["accepted_control_pairs"] == [],
             "Jianchun local plan must remain separate")
    _require(jianchun["feature_id"] == cards["C02"]["feature_id"], "Jianchun identity")
    _require(all(row["mapped_feature_id"] in feature_ids
                 and row["semantics"] == "context_link_only"
                 for row in backbone["water_evidence_navigation"]),
             "water navigation must keep its existing source-only references")
    _require(all(row["geometry"] is None and row["geographic_frame"] is None
                 and row["target_bank_geometry"] is None
                 for row in backbone["current_water_ledger"]),
             "water index must not introduce located rivers or banks")
    _require(backbone["new_geographic_coordinates"] == 0
             and backbone["new_metric_measurements"] == 0, "P469 accounting")
    _require(feature_lookup[modern_id]["layer"] == "modern_geographic_reference",
             "modern Luo River must not become an ancient feature")
    _require(not plan["modern_reference_default_visible"], "modern reference starts hidden")
    for feature in features:
        _require(feature == feature_lookup[feature["id"]], "source feature was changed")

    counts = {
        "source_features": len(geo["features"]),
        "features": len(features),
        "site_remains": sum(feature["layer"] == "site_remains" for feature in features),
        "modern_features": sum(feature["layer"] == "modern_geographic_reference" for feature in features),
        "prior_backbone_features": len(previous_ids),
        "added_existing_features": len(added_ids),
        "building_cards": len(places),
        "roads": len(road_data["routes"]),
        "gate_points": len(network["gates"]),
        "wall_groups": len(wall_ids),
        "partial_enclosure_parts": len(feature_lookup[enclosure_id]["source_pdf_geometry"]["coordinates"]),
        "water_records": len(backbone["current_water_ledger"]),
        "water_relations": len(backbone["current_relations"]),
        "water_context_links": len(backbone["water_evidence_navigation"]),
        "urban_scenes": urban["counts"]["scene_count"],
        "urban_relations": urban["counts"]["relation_count"],
        "new_geographic_coordinates": 0,
        "new_metric_measurements": 0,
        "new_historical_edges": 0,
        "new_geographic_footprints": 0,
    }
    _require(counts == plan["expected_counts"], "common-view inventory or accounting changed")
    return {
        "schema_version": "1.0.0",
        "version": VERSION,
        "title": "宫城、道路与寺院：城市骨架和建筑证据共同视图",
        "study_date": plan["study_date"],
        "source_baseline_commit": plan["source_baseline_commit"],
        "source_inputs_sha256": hashes,
        "source_frame": {
            "id": source_frame["id"],
            "source": source_frame["source"],
            "source_path": GEO_PATH,
            "native_geometry": source_frame["native_geometry"],
            "native_units": "PDF point",
            "crs": geo["crs"],
            "coordinate_order": geo["coordinate_order"],
            "geographic_geometry_note": geo["geometry_format_note"],
            "source_feature_count": len(geo["features"]),
            "display_feature_count": len(features),
            "prior_backbone_display_feature_ids": previous_ids,
            "added_existing_feature_ids": added_ids,
            "display_feature_ids": feature_ids,
            "shared_source_not_new_registration": True,
            "new_geographic_transform": None,
        },
        "source_map_sources": deepcopy(geo["sources"]),
        "features": features,
        "places": places,
        "enclosure_context": deepcopy(distribution["enclosure_context"]),
        "roads": deepcopy(road_data["routes"]),
        "road_sources": deepcopy(road_data["sources"]),
        "gates": deepcopy(network["gates"]),
        "wall_feature_ids": wall_ids,
        "modern_feature_id": modern_id,
        "modern_reference_default_visible": plan["modern_reference_default_visible"],
        "not_rendered_source_features": [
            {"id": feature["id"], "label": feature["label"], "layer": feature["layer"]}
            for feature in geo["features"] if feature["id"] not in feature_ids
        ],
        "unplaced_p44_types": deepcopy(distribution["unplaced_p44_types"]),
        "water_evidence_navigation": deepcopy(backbone["water_evidence_navigation"]),
        "current_water_ledger": deepcopy(backbone["current_water_ledger"]),
        "current_relations": deepcopy(backbone["current_relations"]),
        "water_correction": deepcopy(backbone["correction"]),
        "corrected_current_I09": deepcopy(backbone["corrected_current_I09"]),
        "water_relation_plates": deepcopy(backbone["relation_plates"]),
        "urban": urban,
        "jianchun_plan_audit": deepcopy(jianchun),
        "target_period": backbone["target_period"],
        "phase_rule": backbone["phase_rule"],
        "excluded_geometry_sources": deepcopy(plan["excluded_geometry_sources"]),
        "counts": counts,
        "limitations": deepcopy(plan["limitations"]),
    }
