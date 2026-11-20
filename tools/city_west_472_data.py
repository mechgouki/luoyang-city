"""Assemble B5 and its P1 readings without changing either source."""
from pathlib import Path

from prosperity_city_common_p470 import load, sha

ROOT = Path(__file__).resolve().parents[1]
FOLDER = "west-472"
CROSSWALK = f"research/prosperity-v4/{FOLDER}/crosswalk.json"
B5 = "research/dual-b5/west-roads.json"
P1 = "research/prosperity-v1/text-review.json"
GEO = "research/prosperity-v1/geographic-evidence.json"
CATALOG = "data/entities.json"
STATE = {None: "名录未给单独时态", "undated": "年代未定", "attested_by_528": "至迟528年有据",
         "later_temple": "盛时为宅，寺院后出"}


def build_data(root=ROOT):
    plan = load(root / CROSSWALK)
    for path, digest in plan["source_inputs_sha256"].items():
        if sha(root / path) != digest:
            raise ValueError(f"P472 input changed, review the crosswalk: {path}")
    b5, p1, geo, catalog = [load(root / path) for path in (B5, P1, GEO, CATALOG)]
    originals = {r["id"]: r for r in b5["evidence"]}
    reviews = {r["key"]: r for r in p1["records"] if r["batch"] == "B5"}
    membership = {key: group["id"] for group in plan["groups"] for key in group["evidence_ids"]}
    expected = [f"WR{i:02d}" for i in range(1, 25)]
    if (list(originals) != expected or {r["legacy_id"] for r in reviews.values()} != set(expected)
            or [r["id"] for r in plan["records"]] != expected or set(membership) != set(expected)
            or sum(len(g["evidence_ids"]) for g in plan["groups"]) != len(expected)):
        raise ValueError("B5, P1 and the four reading groups must cover WR01–WR24 exactly once")

    records = []
    for decision in plan["records"]:
        key = decision["id"]
        b, p = originals[key], reviews[decision["p1_key"]]
        if (b["entities"] != p["affected_entity_ids"] or b["quote"] != p["legacy_quote"]
                or p["legacy_reading_preserved"] != b["reading"] or p["legacy_temporal_note_preserved"] != b["temporal_note"]
                or p["legacy_id"] != key or p["manual_context_review"] is not None
                or not p["electronic_text_checked"] or not p["legacy_quote_passed_normalized_sequence_check"]
                or p["geographic_coordinates"] is not None or b["geographic_coordinates"] is not None):
            raise ValueError(f"Review changed source layers for {key}")
        records.append({"id": key, "group": membership[key], "b5": b, "p1": p,
                        "working_reading": decision,
                        "p1_decisions": [d["id"] for d in p1["map_decisions"] if p["key"] in d["evidence_keys"]]})

    ids = {e for r in originals.values() for e in r["entities"]}
    bindings = {f["entity_id"]: f["id"] for f in geo["features"] if f.get("entity_id") in ids}
    if bindings != {p["entity_id"]: p["feature_id"] for p in plan["map_points"]}:
        raise ValueError("Review west gate identities before changing source bindings")
    entities = []
    for e in catalog:
        if e["id"] not in ids:
            continue
        entities.append({k: e[k] for k in ("id", "name", "source_name", "type", "temporal_state")} |
                        {"period_label": STATE[e["temporal_state"]], "feature_id": bindings.get(e["id"]),
                         "records": [k for k, b in originals.items() if e["id"] in b["entities"]]})
    feature_ids = set(plan["background_ids"]) | set(bindings.values())
    features = [f for f in geo["features"] if f["id"] in feature_ids]
    if len(entities) != len(ids) or len(features) != len(feature_ids):
        raise ValueError("Missing original catalog or source feature")
    snapshot_keys = {s["source_snapshot_key"] for p in reviews.values() for s in p["source_checks"]}
    return {"version": plan["version"], "window": plan["window"], "base_commit": plan["base_commit"],
            "source_inputs_sha256": {**plan["source_inputs_sha256"], CROSSWALK: sha(root / CROSSWALK)},
            "groups": plan["groups"], "records": records, "entities": entities, "map_points": plan["map_points"],
            "features": features, "source_crs": geo["crs"], "source_map": geo["sources"][0],
            "text_sources": b5["sources"], "source_family_count": b5["source_family_count"],
            "p1_snapshots": [s for s in p1["source_snapshots"] if s["key"] in snapshot_keys],
            "p1_map_decisions": [d for d in p1["map_decisions"] if any(k in reviews for k in d["evidence_keys"])],
            "legacy_canvas": b5["region"], "new_geographic_transform": None,
            "counts": {"records": len(records), "entities": len(entities), "bound": len(bindings),
                       "unlocated": len(entities)-len(bindings), "source_features": len(features),
                       "original_constraint_entries": sum(len(r["constraints"]) for r in originals.values()),
                       "electronic_matches": sum(r["legacy_quote_passed_normalized_sequence_check"] for r in reviews.values()),
                       "manual_context_reviews": sum(r["manual_context_review"] is not None for r in reviews.values()),
                       "new_historical_coordinates": 0, "new_measurements": 0, "new_footprints": 0}}
