"""Reuse the reviewed urban relations for P4.7 without assigning map positions.

The P453 clusters remain the historical records.  This module only packages
their existing sources, P452 function groups and existing source-map bindings
for the common reading view.  It does not draw, georeference or infer edges.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


CLUSTERS_PATH = "research/prosperity-v4/street-clusters-p453.json"
FUNCTIONS_PATH = "research/prosperity-v4/road-functions-p452.json"
P1_PATH = "research/prosperity-v1/text-review.json"
B1_PATH = "research/dual-b1/decisions.json"
B7_PATH = "research/dual-b7/luonan-river-markets.json"
SOURCE_PATHS = (CLUSTERS_PATH, FUNCTIONS_PATH, P1_PATH, B1_PATH, B7_PATH)

EXPECTED_BINDINGS = {
    ("geo-changhe-palace-gate", "ic_changhe_palace", "K01"),
    ("geo-yongning-temple-walls", "ic_yongning", "K01"),
    ("geo-jianchun-gate", "gate_jianchun", "K02"),
}
EXPECTED_REFERENCES = {
    "ic_palace_avenue", "ic_changhe_palace", "road_eaststone_north",
    "gate_xuanyang", "luoshui",
}


def _indexed(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    """Reject duplicate record IDs instead of silently choosing one version."""
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate urban source record key: {key}")
    return result


def build_relations(root: Path) -> dict[str, Any]:
    """Return a source-preserving, non-geographic urban reading bundle.

    ``scene_bindings`` copies P453's three existing source references.  In
    particular Yongning is linked through its partial temple-wall reference,
    never through a newly inferred pagoda-centre or temple-centre location.
    """
    root = Path(root)
    source_bytes = {relative: (root / relative).read_bytes() for relative in SOURCE_PATHS}
    documents = {relative: json.loads(content) for relative, content in source_bytes.items()}
    source = documents[CLUSTERS_PATH]
    functions_source = documents[FUNCTIONS_PATH]
    clusters = copy.deepcopy(source["clusters"])
    functions = copy.deepcopy(functions_source["nongeographic_function_groups"])
    bindings = copy.deepcopy(source["spatial_index_references"])

    cluster_index = _indexed(clusters, "id")
    if set(cluster_index) != {"K01", "K02", "K03"}:
        raise ValueError("Review the common-view scope before changing the three P453 scenes")
    node_rows = [node for cluster in clusters for node in cluster["nodes"]]
    nodes = _indexed(node_rows, "id")
    edges = [edge for cluster in clusters for edge in cluster["edges"]]
    events = [event for cluster in clusters for event in cluster.get("temporal_events", [])]
    _indexed(edges, "id")
    _indexed(events, "id")
    grades = Counter(edge["grade"] for edge in edges)
    if (len(nodes), len(edges), len(events), dict(grades)) != (20, 17, 2, {"A": 16, "C": 1}):
        raise ValueError("The reviewed P453 object, relation, event or grade inventory changed")
    if any(not cluster["non_geographic"] for cluster in clusters):
        raise ValueError("Urban scenes must retain their non-geographic status")
    if any(edge["geographic_line_allowed"] for edge in edges):
        raise ValueError("Textual urban relations cannot become geographic lines in the common view")
    for edge in edges:
        if edge["subject"] not in nodes or edge["object"] not in nodes:
            raise ValueError("Urban relation refers to an undeclared P453 object: " + edge["id"])
    for event in events:
        if event["subject"] not in nodes:
            raise ValueError("Urban event refers to an undeclared P453 object: " + event["id"])

    binding_keys = {(row["feature_id"], row["entity_id"], row["cluster_id"]) for row in bindings}
    if len(bindings) != 3 or binding_keys != EXPECTED_BINDINGS:
        raise ValueError("Existing P453 source-map bindings changed and require a separate review")
    for binding in bindings:
        cluster = cluster_index[binding["cluster_id"]]
        node = next(node for node in cluster["nodes"] if node["id"] == binding["entity_id"])
        if node["feature_id"] != binding["feature_id"]:
            raise ValueError("Scene binding no longer matches its original P453 node")
    bound_ids = {binding["entity_id"] for binding in bindings}
    if any(node["feature_id"] is not None for key, node in nodes.items() if key not in bound_ids):
        raise ValueError("An unlocated P453 object gained an unreviewed source-map identity")

    if {group["id"] for group in functions} != {"T01", "T02", "T03", "T04", "T05"}:
        raise ValueError("Review the P452 functional classification before changing its five groups")
    function_ids = {entity_id for group in functions for entity_id in group["entity_ids"]}
    if not function_ids <= nodes.keys():
        raise ValueError("P452 function group contains an object outside the reviewed P453 scenes")
    references = set(nodes) - function_ids
    if len(function_ids) != 15 or references != EXPECTED_REFERENCES:
        raise ValueError("Keep the 15 function objects distinct from the five scene references")

    p1_records = _indexed(documents[P1_PATH]["records"], "legacy_title")
    b1_records = _indexed(documents[B1_PATH]["decisions"], "id")
    b1_sources = _indexed(documents[B1_PATH]["sources"], "id")
    b7_records = _indexed(documents[B7_PATH]["evidence"], "id")
    b7_sources = _indexed(documents[B7_PATH]["sources"], "id")
    records: dict[str, dict[str, Any]] = {}
    for item in [*edges, *events]:
        record_id = item["source_record"]
        if record_id in records:
            continue
        if record_id.startswith("B1:"):
            record = b1_records[record_id.split(":", 1)[1]]
            relative = B1_PATH
            locator = record.get("quote_locator", record.get("legacy_locator", ""))
            links = [copy.deepcopy(b1_sources[key]) for key in record["source_ids"]]
        elif record_id.startswith("B7:"):
            record = b7_records[record_id.split(":", 1)[1]]
            relative = B7_PATH
            locator = record["quote_locator"]
            links = [copy.deepcopy(b7_sources[key]) for key in record["sources"]]
        elif record_id.startswith("v2.5:"):
            record = p1_records[record_id]
            relative = P1_PATH
            locator = record.get("legacy_locator", "")
            links = [{"id": check["declared_source_id"],
                      "title": check["declared_source_id"] + "本原文校读",
                      "url": check["declared_url"]}
                     for check in record["source_checks"]]
        else:
            raise ValueError("Unsupported urban source namespace: " + record_id)
        records[record_id] = {"source_path": relative, "locator": locator,
                              "links": links, "record": copy.deepcopy(record)}

    return {
        "version": "P4.7",
        "source_version": source["version"],
        "source_inputs_sha256": {
            relative: hashlib.sha256(content).hexdigest()
            for relative, content in source_bytes.items()
        },
        "clusters": clusters,
        "source_records": records,
        "evidence_grades": copy.deepcopy(source["evidence_grades"]),
        "entity_names": {entity_id: node["name"] for entity_id, node in nodes.items()},
        "functions": functions,
        "scene_bindings": bindings,
        "reference_entity_ids": [entity_id for entity_id in nodes if entity_id in references],
        "counts": {
            "scene_count": len(clusters),
            "object_count": len(nodes),
            "relation_count": len(edges),
            "direct_relation_count": grades["A"],
            "interpretive_relation_count": grades["C"],
            "event_count": len(events),
            "function_group_count": len(functions),
            "function_object_count": len(function_ids),
            "reference_object_count": len(references),
            "source_binding_count": len(bindings),
            "source_record_count": len(records),
        },
        "forbidden_inferences": copy.deepcopy(source["forbidden_inferences"]),
        "new_historical_relationships": 0,
        "new_historical_coordinates": 0,
        "limitations": [
            "三组场景逐条复用P453的原关系、原文、证据等级和限制；没有新增历史关系。",
            "五类功能仅分类15个对象；另外5个对象是场景参照，未扩充为功能建筑或新的地理点。",
            "A／C等级区分文字关系与条件解释，不表示测量精度、绝对位置或实址范围。",
            "场景仅有P453既存的三个来源图绑定；永宁寺通过部分寺墙读K01，不给塔心附加寺院关系。",
            "宫前御道未与铜驼大道图示残段建立全段同体关系；文献方位和里数不转换为地理线。",
            "洛南K03没有来源图地理绑定；宣阳门、永桥、洛水及市场不能定位到现代河线或图符端点。",
            "城市关系、时间事件与水系记录分别计数；同一原典的不同转录不构成独立考古测量。",
        ],
    }
