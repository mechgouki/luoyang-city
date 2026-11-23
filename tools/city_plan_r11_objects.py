#!/usr/bin/env python3
"""Bind catalog identities and reviewable point hypotheses to the R11 mother plan.

R10 node/entity ownership is not geometry identity.  This module preserves that
separation, never invents building footprints, and never moves source geometry.
The only newly generated geometries are explicitly provisional display Points.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

CONFIG = "research/city-plan-r11/objects.json"
CARDINAL = {"east_of": (0, 1), "west_of": (0, -1),
            "north_of": (1, 1), "south_of": (1, -1)}
NONSPATIAL_KINDS = {"event", "institution", "activity", "interpretation",
                    "unknown_endpoint", "metric_object", "object_group", "object"}
COMPONENT_KINDS = {"component", "pool_group"}
NON_DIRECTION = {
    "within": "semantic_containment_no_boundary_or_internal_position",
    "membership": "unordered_membership_no_location",
    "same_source": "shared_reference_not_geometric_registration",
    "sequence": "nonspatial_order_not_street_or_geographic_order",
    "adjacent": "nonmetric_neighborhood_not_touching_boundaries",
    "unknown_connection": "unresolved_connection_not_a_route",
    "identity_candidate": "candidate_identity_no_automatic_geometry_union",
}


def _read(root: Path, path: str):
    return json.loads((root / path).read_text(encoding="utf-8"))


def _points(geometry: dict) -> list:
    def walk(c):
        if c and isinstance(c[0], (int, float)):
            return [c]
        return [p for cc in c for p in walk(cc)]
    return walk(geometry["coordinates"])


def _bbox(geometries: list[dict]) -> list[float] | None:
    p = [point for g in geometries for point in _points(g)]
    return ([min(x[0] for x in p), min(x[1] for x in p),
             max(x[0] for x in p), max(x[1] for x in p)] if p else None)


def _unique_refs(refs: list[dict]) -> list[dict]:
    seen, result = set(), []
    for r in refs:
        key = (r.get("path"), r.get("pointer"), r.get("id"))
        if key not in seen:
            seen.add(key)
            result.append(r)
    return result


def _linear_solve(matrix: list, values: list) -> list:
    """Three-variable pivoted elimination; no numerical package dependency."""
    rows = [list(map(float, row)) + [float(v)] for row, v in zip(matrix, values)]
    n = len(rows)
    for j in range(n):
        pivot = max(range(j, n), key=lambda k: abs(rows[k][j]))
        if abs(rows[pivot][j]) < 1e-10:
            raise ValueError("Named-gate display references do not span an affine fit")
        rows[j], rows[pivot] = rows[pivot], rows[j]
        divisor = rows[j][j]
        rows[j] = [v / divisor for v in rows[j]]
        for k in range(n):
            if k != j:
                multiplier = rows[k][j]
                rows[k] = [a - multiplier * b for a, b in zip(rows[k], rows[j])]
    return [rows[k][-1] for k in range(n)]


def _apply(matrix: list, xy: list) -> list[float]:
    return [matrix[axis][0] * xy[0] + matrix[axis][1] * xy[1] + matrix[axis][2]
            for axis in range(2)]


def _fit_registration(config: dict, old_markers: dict, geometry: dict) -> dict:
    source = {f["id"]: f for f in geometry["features"]}
    controls = []
    for c in config["registration"]["controls"]:
        old = old_markers.get(c["entity_id"])
        target = source.get(c["source_feature_id"])
        if not old or not target or target["geometry"]["type"] != "Point":
            raise ValueError("Missing named-gate display reference: " + c["entity_id"])
        if c["entity_id"] not in target.get("entity_ids", []):
            raise ValueError("Gate source identity changed: " + c["entity_id"])
        controls.append({**c, "legacy_xy": list(old["xy"]),
                         "source_xy_m": list(target["geometry"]["coordinates"]),
                         "legacy_source_ref": old["source_ref"],
                         "source_refs": target.get("source_refs", [])})
    center = [sum(c["legacy_xy"][i] for c in controls) / len(controls) for i in range(2)]
    scale = 1000.0
    design = [[(c["legacy_xy"][0] - center[0]) / scale,
               (c["legacy_xy"][1] - center[1]) / scale, 1.0] for c in controls]
    normal = [[sum(row[i] * row[j] for row in design) for j in range(3)] for i in range(3)]
    matrix = []
    for axis in range(2):
        rhs = [sum(row[j] * c["source_xy_m"][axis] for row, c in zip(design, controls)) for j in range(3)]
        a, b, intercept = _linear_solve(normal, rhs)
        matrix.append([a / scale, b / scale, intercept - a * center[0] / scale - b * center[1] / scale])
    matrix.append([0.0, 0.0, 1.0])
    for c in controls:
        fit = _apply(matrix, c["legacy_xy"])
        delta = [fit[i] - c["source_xy_m"][i] for i in range(2)]
        c.update(fitted_xy_m=fit, residual_xy_m=delta, residual_norm_m=math.hypot(*delta))
    return {**copy.deepcopy(config["registration"]), "matrix": matrix,
            "controls": controls, "control_count": len(controls),
            "rmse_display_m": math.sqrt(sum(c["residual_norm_m"] ** 2 for c in controls) / len(controls)),
            "max_residual_display_m": max(c["residual_norm_m"] for c in controls),
            "determinant_xy": matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0],
            "applied_to_source_geometries": False,
            "independent_survey_control_points": 0, "coordinate_precision_is_accuracy": False}


def build_objects(root: Path, geometry: dict) -> dict:
    root = Path(root)
    config = _read(root, CONFIG)
    inputs = {k: _read(root, p) for k, p in config["inputs"].items()}
    paths = config["inputs"]
    hashes = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in [CONFIG, *paths.values()]}

    def ref(path, pointer, ident=None, **extra):
        return {"id": ident or path + "#" + pointer, "path": path, "pointer": pointer,
                "sha256": hashes.get(path) or hashlib.sha256((root / path).read_bytes()).hexdigest(), **extra}

    catalog = {e["id"]: e for e in inputs["catalog"]}
    catalog_index = {e["id"]: i for i, e in enumerate(inputs["catalog"])}
    temporal = inputs["temporal"]
    source_features = {f["id"]: f for f in geometry["features"]}
    frame_id = geometry["frame"]["id"]
    canonical = config["canonical_entities"]
    def eid_object(eid):
        return "object-" + canonical.get(eid, eid)
    def entity_ref(eid, suffix=""):
        e = catalog[eid]
        return ref(paths["catalog"], f"/{catalog_index[eid]}{suffix}", "catalog-" + eid,
                   url=e.get("source_url"), locator=e.get("source_ref"))

    legacy_markers = {}
    for i, marker in enumerate(inputs["markers"]):
        for eid in marker["ids"]:
            legacy_markers.setdefault(eid, {"xy": [marker["x"], marker["y"]], "kind": marker["kind"],
                "label": marker.get("label", ""), "source_ref": ref(paths["markers"], f"/{i}")})
    for i, gate in enumerate(inputs["scene"]["gates"]):
        legacy_markers[gate[0]] = {"xy": [gate[1], gate[2]], "kind": "gate", "label": gate[4],
                                  "source_ref": ref(paths["scene"], f"/gates/{i}")}
    # Road midpoints are working reference tokens, never reconstructed endpoints.
    for i, road in enumerate(inputs["scene"]["base_roads"]):
        points = road["points"]
        for eid in road["ids"]:
            legacy_markers.setdefault(eid, {"xy": [sum(p[k] for p in points) / len(points) for k in range(2)],
                "kind": "road_reference", "label": road["key"],
                "source_ref": ref(paths["scene"], f"/base_roads/{i}"),
                "warning": "旧道路中点仅作候选参照；旧端点、全线、宽度不导入。"})
    registration = _fit_registration(config, legacy_markers, geometry)
    audits = defaultdict(list)
    feature_audit = {}
    for i, a in enumerate(inputs["semantic_audit"]["features"]):
        feature_audit[a["feature_ref"]] = (i, a)
        for eid in a["entity_ids"]:
            audits[eid].append(a)

    objects, node_to_object, entity_to_objects = {}, {}, defaultdict(set)
    r10_nodes, r10_decisions = {}, {}
    def ensure(oid, label, kind, eids=(), node_id=None, source_refs=(), region_id=None, nonspatial=False):
        if oid not in objects:
            objects[oid] = {"id": oid, "object_id": oid, "component_id": oid,
                "label": label, "kind": kind, "entity_ids": [], "r10_node_ids": [],
                "source_refs": [], "region_ids": [], "source_feature_ids": [],
                "evaluation_feature_ids": [], "geometry": None, "candidate_xy_m": None,
                "seed": None, "nonspatial": nonspatial, "fixed": False,
                "placement_status": "unplaced", "unplaced_reason": None,
                "constrained_axes": [], "unconstrained_axes": ["x", "y"],
                "geographic_coordinates": None, "member_of": [], "limits": []}
        o = objects[oid]
        for eid in eids:
            if eid not in catalog:
                raise ValueError("Unknown catalog entity " + eid)
            if eid not in o["entity_ids"]:
                o["entity_ids"].append(eid)
            entity_to_objects[eid].add(oid)
        if node_id and node_id not in o["r10_node_ids"]:
            o["r10_node_ids"].append(node_id)
        if region_id and region_id not in o["region_ids"]:
            o["region_ids"].append(region_id)
        o["source_refs"] = _unique_refs(o["source_refs"] + list(source_refs))
        return o

    # Catalog ownership is not physical identity: events and temple components
    # keep independent object IDs even when they cite the same catalog ID.
    for ri, region in enumerate(inputs["r10"]["regions"]):
        for di, decision in enumerate(region["decisions"]):
            r10_decisions[decision["id"]] = (decision, f"/regions/{ri}/decisions/{di}")
        for pi, panel in enumerate(region["panels"]):
            for ni, node in enumerate(panel["nodes"]):
                node_id, eids, kind = node["id"], node.get("entity_ids", []), node["kind"]
                pointer = f"/regions/{ri}/panels/{pi}/nodes/{ni}"
                nonspatial = kind in NONSPATIAL_KINDS
                if node_id in config["node_object_bindings"]:
                    oid = config["node_object_bindings"][node_id]
                elif nonspatial:
                    oid = "annotation-" + node_id
                elif kind in COMPONENT_KINDS or not eids:
                    oid = "component-" + node_id
                elif eids[0] in config["long_reference_entities"]:
                    oid = "reference-" + node_id
                else:
                    oid = eid_object(eids[0])
                r10_nodes[node_id] = node
                node_to_object[node_id] = oid
                o = ensure(oid, node["label"], kind, eids, node_id,
                    [ref(paths["r10"], pointer, node_id), *[ref(s["path"], s["pointer"]) for s in node.get("source_inputs", [])]],
                    region["id"], nonspatial)
                if node.get("note") and node["note"] not in o["limits"]:
                    o["limits"].append(node["note"])
                o.setdefault("basis", []).append(node.get("basis", ""))
    for eid, e in catalog.items():
        # Event-only / regional records still retain a separate catalog object.
        physical = [oid for oid in entity_to_objects[eid] if not objects[oid]["nonspatial"]]
        if not physical:
            ensure(eid_object(eid), e["name"], e["type"], [eid], source_refs=[entity_ref(eid)])
        for oid in entity_to_objects[eid]:
            objects[oid]["source_refs"] = _unique_refs(objects[oid]["source_refs"] + [entity_ref(eid)])

    # Explicit source bindings, including separate temple and tower identities.
    for c in config["registration"]["controls"]:
        oid = eid_object(c["entity_id"])
        o = ensure(oid, catalog[c["entity_id"]]["name"], "gate", [c["entity_id"]])
        o["source_feature_ids"] = [c["source_feature_id"]]
        o["evaluation_feature_ids"] = [c["source_feature_id"]]
        o["evaluation_proxy"] = "named_source_map_symbol_not_excavated_control_point"
    for oid, binding in config["source_object_bindings"].items():
        o = objects.get(oid)
        if not o:
            continue
        ids = [fid for fid in binding.get("feature_ids", []) if fid in source_features]
        ids += [fid for fid in source_features if any(fid.startswith(p) for p in binding.get("feature_prefixes", []))]
        o.update(source_feature_ids=list(dict.fromkeys(ids)), label=binding.get("label", o["label"]),
                 evaluation_proxy=binding["evaluation_proxy"])
        if binding.get("evaluation_limit"):
            o["limits"].append(binding["evaluation_limit"])
        missing_evaluation = [fid for fid in binding.get("evaluation_feature_ids", []) if fid not in source_features]
        if missing_evaluation:
            raise ValueError("Required explicit evaluation geometry is missing for " + oid + ": " + ", ".join(missing_evaluation))
        o["evaluation_feature_ids"] = [fid for fid in binding.get("evaluation_feature_ids", ids) if fid in source_features]
        if not o["evaluation_feature_ids"]:
            o["evaluation_feature_ids"] = ids
    for o in objects.values():
        if o["source_feature_ids"]:
            o["fixed"] = True
            o["placement_status"] = "source_bound"
            o["evaluation_bbox_m"] = _bbox([source_features[fid]["geometry"] for fid in o["evaluation_feature_ids"]])
            o["source_refs"] = _unique_refs(o["source_refs"] + [r for fid in o["source_feature_ids"] for r in source_features[fid].get("source_refs", [])])
            o["limits"].append("绑定已绘源项；不生成新的主体中心点。方向数值如用包络，仅指所列已见／刊载几何，非完整古代界线。")

    # Remaining source components are readable objects, never new catalog IDs.
    owned_source_ids = {fid for o in objects.values() for fid in o["source_feature_ids"]}
    for fid, f in source_features.items():
        if fid in owned_source_ids:
            continue
        oid = "source-component-" + f.get("component_id", fid)
        if oid in objects:
            oid += "-" + fid
        o = ensure(oid, f["label"], "source_component", f.get("entity_ids", []),
                   source_refs=f.get("source_refs", []))
        o.update(source_feature_ids=[fid], evaluation_feature_ids=[fid], fixed=True,
                 placement_status="source_bound", evaluation_proxy=f["geometry_role"],
                 evaluation_bbox_m=_bbox([f["geometry"]]))
        o["region_ids"] = list(f.get("region_ids", []))
        o["limits"] += f.get("limits", [])

    constraints = []
    def add_constraint(cid, source_oid, target_oid, typ, label, refs, origin, **extra):
        if source_oid not in objects or target_oid not in objects:
            raise ValueError("Unknown object in constraint " + cid)
        c = {"id": cid, "from_object_id": source_oid, "to_object_id": target_oid,
             "type": typ, "label": label, "origin": origin, "source_refs": _unique_refs(refs),
             "from_entity_ids": objects[source_oid]["entity_ids"], "to_entity_ids": objects[target_oid]["entity_ids"],
             "status": "pending", "evaluated": False, "numeric_evaluation": None,
             "distance_evidence_used": False, "shared_axis_inferred": False,
             "street_or_boundary_created": False, **extra}
        if typ in CARDINAL:
            axis, sign = CARDINAL[typ]
            c.update(constraint_class="single_axis_order", axis="xy"[axis], positive_direction=sign,
                     operator=">" if sign > 0 else "<", other_axis="unconstrained")
            for oid in (source_oid, target_oid):
                if "xy"[axis] not in objects[oid]["constrained_axes"]:
                    objects[oid]["constrained_axes"].append("xy"[axis])
        else:
            c.update(constraint_class=NON_DIRECTION.get(typ, "nonspatial_reference"), status="not_a_coordinate_constraint")
            if typ in {"within", "membership"}:
                objects[source_oid]["member_of"].append(target_oid)
        constraints.append(c)

    for ri, region in enumerate(inputs["r10"]["regions"]):
        for pi, panel in enumerate(region["panels"]):
            for li, relation in enumerate(panel["relations"]):
                refs = [ref(paths["r10"], f"/regions/{ri}/panels/{pi}/relations/{li}", relation["id"])]
                refs += [ref(s["path"], s["pointer"]) for s in relation.get("source_inputs", [])]
                add_constraint(relation["id"], node_to_object[relation["from"]], node_to_object[relation["to"]],
                    relation["type"], relation["label"], refs, "R10", region_id=region["id"],
                    from_r10_node=relation["from"], to_r10_node=relation["to"],
                    uncertainty=relation.get("uncertainty"), original_relation=copy.deepcopy(relation))

    # A reviewed subset fills R10 omissions; no bulk import of the 482 mixed-schema
    # legacy constraints, and no conversion of original li/step distances.
    for si, supplement in enumerate(config["supplemental_catalog_relations"]):
        eid = supplement["entity_id"]
        ci = supplement["constraint_index"]
        c = catalog[eid]["constraints"][ci]
        typ = supplement.get("type", c["relation"])
        add_constraint(f"R11-C{si+1:03d}", eid_object(eid), eid_object(supplement["target_entity_id"]), typ,
            supplement.get("note", catalog[eid]["source_quote"]),
            [entity_ref(eid, f"/constraints/{ci}"), ref(CONFIG, f"/supplemental_catalog_relations/{si}")],
            "catalog_reviewed_supplement", conditional=supplement.get("conditional", False))
    for gi, context in enumerate(config["gate_contexts"]):
        eid, gate_id = context["entity_id"], context["gate_entity_id"]
        add_constraint(f"R11-G{gi+1:03d}", eid_object(eid), eid_object(gate_id), context["relation"],
            context["context"], [entity_ref(eid, f"/constraints/{context['catalog_constraint_index']}"),
                                   ref(CONFIG, f"/gate_contexts/{gi}")],
            "gate_inside_outside_context", conditional=context.get("conditional", False),
            inference="门内外与已核城墙侧别给大方向，不提供门道同轴、距离或连续街段。")
    for xi, extra in enumerate(config["reviewed_extra_relations"]):
        refs = [ref(CONFIG, f"/reviewed_extra_relations/{xi}")]
        if extra.get("r10_decision_id"):
            d, pointer = r10_decisions[extra["r10_decision_id"]]
            refs += [ref(paths["r10"], pointer, d["id"])]
            refs += [ref(s["path"], s["pointer"]) for s in d["source_inputs"]]
        else:
            refs.append(entity_ref(extra["source_entity_id"], "/source_quote"))
        add_constraint(extra["id"], eid_object(extra["from_entity_id"]), eid_object(extra["to_entity_id"]),
                       extra["type"], extra["label"], refs, "reviewed_cross_panel_link",
                       conditional=extra.get("conditional", False), note=extra.get("note"))

    for ci, containment in enumerate(config.get("supplemental_containments", [])):
        eid, index = containment["entity_id"], containment["constraint_index"]
        add_constraint(f"R11-M{ci+1:03d}", eid_object(eid), eid_object(containment["target_entity_id"]),
            "within", containment["note"],
            [entity_ref(eid, f"/constraints/{index}"), ref(CONFIG, f"/supplemental_containments/{ci}")],
            "reviewed_direction_group_context", individual_location_proved=False)

    # A visible side-group is not an invented placement for every member.
    group_for = {}
    for gi, group in enumerate(config["directional_groups"]):
        members = [eid_object(eid) for eid in group["entity_ids"]]
        g = ensure(group["id"], group["label"], "directional_group", group["entity_ids"],
                   source_refs=[ref(CONFIG, f"/directional_groups/{gi}")])
        g["member_object_ids"] = members
        g["not_individual_locations"] = True
        for oid in members:
            group_for[oid] = g["id"]
            g["constrained_axes"] = sorted(set(g["constrained_axes"] + objects[oid]["constrained_axes"]))
            g["region_ids"] = sorted(set(g["region_ids"] + objects[oid]["region_ids"]))
            g["source_refs"] = _unique_refs(g["source_refs"] + objects[oid]["source_refs"])
            objects[oid]["evaluation_proxy_object_id"] = g["id"]
        ai, audit = feature_audit[group["feature_ref"]]
        box = audit.get("original_display_box")
        if box:
            g["legacy_group_seed"] = {"xy": [box[0] + box[2] / 2, box[1] + box[3] / 2],
                "source_ref": ref(paths["semantic_audit"], f"/features/{ai}"),
                "meaning": "共同方向群的公开排版参照，非成员址点、地块中心或距离证据。"}
        g["limits"].append(config["directional_group_note"])

    for c in constraints:
        c["evaluation_from_object_id"] = group_for.get(c["from_object_id"], c["from_object_id"])
        c["evaluation_to_object_id"] = group_for.get(c["to_object_id"], c["to_object_id"])
        c["uses_joint_directional_group_proxy"] = (c["evaluation_from_object_id"] != c["from_object_id"] or
                                                     c["evaluation_to_object_id"] != c["to_object_id"])

    # Period and unlocated-object protections have precedence over marker glyphs.
    blocked = {}
    for oid, o in objects.items():
        states = {temporal.get(eid, {}).get("prosperity_state", catalog[eid].get("temporal_state")) for eid in o["entity_ids"]}
        o["phase_states"] = sorted("unknown" if s is None else str(s) for s in states)
        o["phase_notes"] = list(dict.fromkeys(temporal[eid]["note"] for eid in o["entity_ids"] if eid in temporal))
        if oid.startswith("object-"):
            late = [temporal[eid] for eid in o["entity_ids"] if temporal.get(eid, {}).get("prosperity_state") == "later_temple"]
            if late:
                o["label"] = late[0].get("main_scene_name") or late[0]["prior_name"]
                o["kind"] = "residence"
                o["main_phase_role"] = "earlier_residence_not_later_temple"
            elif any(eid in temporal and temporal[eid].get("prosperity_state") == "name_layer" for eid in o["entity_ids"]):
                blocked[oid] = "名称或前代历史层，未证为516—528活动设施。"
        if o["nonspatial"]:
            blocked[oid] = "事件、制度、解释或活动说明，不是可放置建筑轮廓。"
        if any(eid in config["long_reference_entities"] for eid in o["entity_ids"]):
            if not o["fixed"]:
                blocked[oid] = config["reference_note"]
        for eid in o["entity_ids"]:
            if eid in config["force_unplaced"] and not o["fixed"]:
                blocked[oid] = config["force_unplaced"][eid]
            e = catalog[eid]
            if not o["fixed"] and not o["r10_node_ids"] and (eid.startswith(("r_", "e_")) or
                    "register_only" in e.get("modes", []) or "world_reference" in e.get("frames", [])):
                blocked.setdefault(oid, "城外地域、名录或方向参照；无本城独立落位依据。")
        o["constrained_axes"] = sorted(set(o["constrained_axes"]))
        o["unconstrained_axes"] = [a for a in "xy" if a not in o["constrained_axes"]]
        if oid in group_for:
            o["limits"].append("仅共同方向签可显示；本成员不具有独立候选坐标。")
        for eid in o["entity_ids"]:
            for a in audits[eid]:
                if a["action"] in {"sidecar", "membership_list", "needs_review"} and a["reason"] not in o["limits"]:
                    o["limits"].append(a["reason"])

    active = {oid for oid, o in objects.items() if (o["fixed"] or o["constrained_axes"]) and oid not in blocked and oid not in group_for}
    # Membership alone cannot activate an object.  When both objects already
    # have independent directions, containment can carry only broad context.
    adjacency = defaultdict(list)
    for c in constraints:
        a, b = c["evaluation_from_object_id"], c["evaluation_to_object_id"]
        if a == b or a not in active or b not in active:
            continue
        if c["type"] in CARDINAL or c["type"] == "within":
            adjacency[a].append((b, c["id"], c["type"]))
            adjacency[b].append((a, c["id"], c["type"]))
    anchors = sorted(oid for oid in active if objects[oid]["fixed"] and objects[oid].get("evaluation_bbox_m"))
    support = {oid: {"anchor_object_id": oid, "constraint_ids": [], "context_only_edges": []} for oid in anchors}
    queue = deque(anchors)
    while queue:
        current = queue.popleft()
        for adjacent, cid, typ in adjacency[current]:
            if adjacent in support:
                continue
            parent = support[current]
            support[adjacent] = {"anchor_object_id": parent["anchor_object_id"],
                "constraint_ids": parent["constraint_ids"] + [cid],
                "context_only_edges": parent["context_only_edges"] + ([cid] if typ == "within" else [])}
            queue.append(adjacent)
    candidate_ids = {oid for oid in active if oid in support and not objects[oid]["fixed"]}
    positions = {}
    for oid in sorted(candidate_ids):
        o = objects[oid]
        o["source_attachment_path"] = support[oid]
        if o.get("legacy_group_seed"):
            seed = o["legacy_group_seed"]
            positions[oid] = _apply(registration["matrix"], seed["xy"])
            o["seed"] = {"method": "affine_registered_joint_directional_group_token",
                "legacy_xy": seed["xy"], "initial_xy_m": list(positions[oid]),
                "source_refs": [seed["source_ref"]], "meaning": seed["meaning"]}
            continue
        choices = []
        for eid in o["entity_ids"]:
            marker = legacy_markers.get(eid)
            sidecar = any(a["action"] == "sidecar" for a in audits[eid])
            if marker and marker["kind"] != "group" and not sidecar:
                choices.append((eid, marker))
        if choices:
            eid, marker = choices[0]
            positions[oid] = _apply(registration["matrix"], marker["xy"])
            o["seed"] = {"method": "affine_registered_legacy_display_marker",
                "entity_id_used": eid, "legacy_xy": marker["xy"], "legacy_kind": marker["kind"],
                "initial_xy_m": list(positions[oid]), "source_refs": [marker["source_ref"]],
                "shape_or_width_imported": False, "warning": marker.get("warning", "旧图签仅是可改动候选种子，不是古址测点。")}

    def box_for(oid):
        if oid in positions:
            p = positions[oid]
            return [p[0], p[1], p[0], p[1]]
        return objects[oid].get("evaluation_bbox_m") if objects[oid]["fixed"] else None

    def midpoint(box):
        return [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2]

    # Every generated seed records its free-axis choice.  No later label or
    # collision-avoidance movement is folded back into the model coordinates.
    step = float(config["solver"]["propagation_seed_step_m"])
    for _ in range(len(candidate_ids) + 1):
        progress = False
        for c in constraints:
            a, b = c["evaluation_from_object_id"], c["evaluation_to_object_id"]
            if c["type"] not in CARDINAL or a == b:
                continue
            axis, sign = CARDINAL[c["type"]]
            for unknown, known, movement in ((a, b, sign), (b, a, -sign)):
                known_box = box_for(known)
                if unknown not in candidate_ids or unknown in positions or not known_box:
                    continue
                p = midpoint(known_box)
                p[axis] = known_box[axis + (2 if movement > 0 else 0)] + movement * step
                positions[unknown] = p
                objects[unknown]["seed"] = {"method": "direction_propagation_display_choice",
                    "initial_xy_m": list(p), "reference_object_id": known,
                    "constraint_id": c["id"], "direction_axis": "xy"[axis],
                    "free_axis_inherited_from_reference_proxy": "xy"[1-axis],
                    "reference_bbox_used_m": known_box, "display_step_m": step,
                    "step_is_historical_distance": False,
                    "source_refs": c["source_refs"]}
                progress = True
        # Only already direction-bearing objects may use a container's broad
        # display context; this cannot produce a point for a pure member.
        for oid in sorted(candidate_ids - positions.keys()):
            for other, cid, typ in adjacency[oid]:
                b = box_for(other)
                if typ == "within" and b:
                    positions[oid] = midpoint(b)
                    objects[oid]["seed"] = {"method": "direction_group_container_context",
                        "initial_xy_m": list(positions[oid]), "reference_object_id": other,
                        "constraint_id": cid, "reference_bbox_used_m": b,
                        "individual_location_proved": False,
                        "warning": "此为已有独立方向对象的容纳情境种子；未据所属关系定位普通成员。"}
                    progress = True
                    break
        if not progress:
            break

    margin = float(config["solver"]["display_margin_m"])
    tolerance = float(config["solver"]["numeric_tolerance_m"])
    iterations = 0
    for iterations in range(1, int(config["solver"]["max_iterations"]) + 1):
        maximum_move = 0.0
        for c in constraints:
            if c["type"] not in CARDINAL:
                continue
            a, b = c["evaluation_from_object_id"], c["evaluation_to_object_id"]
            aa, bb = box_for(a), box_for(b)
            if a == b or not aa or not bb:
                continue
            axis, sign = CARDINAL[c["type"]]
            av = aa[axis if sign > 0 else axis + 2]
            bv = bb[axis + 2 if sign > 0 else axis]
            correction = margin - sign * (av - bv)
            if correction <= tolerance:
                continue
            movable = [oid for oid in (a, b) if oid in positions]
            if not movable:
                continue
            delta = correction / len(movable)
            if a in positions:
                positions[a][axis] += sign * delta
            if b in positions:
                positions[b][axis] -= sign * delta
            maximum_move = max(maximum_move, delta)
        if maximum_move <= tolerance:
            break

    features = []
    for oid, o in objects.items():
        o["unconstrained_axes"] = [a for a in "xy" if a not in o["constrained_axes"]]
        if o["fixed"]:
            o["feature_ids"] = list(o["source_feature_ids"])
        elif oid in positions:
            xy = positions[oid]
            if not all(math.isfinite(v) for v in xy):
                raise ValueError("Nonfinite candidate position " + oid)
            o["candidate_xy_m"] = list(xy)
            o["geometry"] = {"type": "Point", "coordinates": list(xy)}
            o["placement_status"] = "directional_group_reference" if o["kind"] == "directional_group" else "candidate_marker"
            o["source_attachment_path"] = support[oid]
            o["position_unique"] = False
            o["coordinate_frame"] = frame_id
            o["layout_adjustment_m"] = [xy[i] - o["seed"]["initial_xy_m"][i] for i in range(2)]
            o["layout_adjustment_norm_m"] = math.hypot(*o["layout_adjustment_m"])
            o["label_offset_in_data"] = [0, 0]
            fid = "r11-candidate-" + oid
            o["feature_ids"] = [fid]
            limits = ["候选绘图点，不是测得建筑中心、寺院中心、地块边界或米制间距。",
                      "所选位置不唯一；未述轴保持自由，不推同街、等距、邻接或共同中轴。",
                      "所有排版位移留在候选数据；源几何未移动。"] + o["limits"]
            if support[oid]["context_only_edges"]:
                limits.append("到源对象的关系链含容纳情境边，只有广域归属；它不是定位控制。")
            features.append({"id": fid, "component_id": oid, "entity_ids": list(o["entity_ids"]),
                "label": o["label"], "kind": o["kind"], "geometry": copy.deepcopy(o["geometry"]),
                "geometry_role": "candidate_marker", "placement_status": o["placement_status"],
                "coordinate_frame": frame_id, "region_ids": list(o["region_ids"]),
                "source_refs": o["source_refs"], "limits": limits,
                "position_unique": False, "not_individual_locations": o.get("not_individual_locations", False),
                "constrained_axes": o["constrained_axes"], "unconstrained_axes": o["unconstrained_axes"],
                "source_attachment_path": support[oid], "phase_states": o["phase_states"],
                "candidate_seed": o["seed"], "layout_adjustment_m": o["layout_adjustment_m"],
                "registered_geometry": False, "building_footprint": False})
        elif oid in group_for:
            group = objects[group_for[oid]]
            o["placement_status"] = "directional_group_member" if group_for[oid] in positions else "unplaced_relation_group"
            o["unplaced_reason"] = "共同方向保留于群签，成员内部方位与独立址点未记。"
            o["feature_ids"] = ["r11-candidate-" + group_for[oid]] if group_for[oid] in positions else []
            o["evaluation_proxy_xy_m"] = positions.get(group_for[oid])
        else:
            o["feature_ids"] = []
            if oid in blocked:
                o["placement_status"] = "unplaced_annotation_or_reference"
                o["unplaced_reason"] = blocked[oid]
            elif not o["constrained_axes"]:
                o["placement_status"] = "unplaced_membership" if o["member_of"] else "unplaced_register"
                o["unplaced_reason"] = "只有所属、同源、名称、身份或时间信息；没有可落实的独立方向／定位。"
            else:
                o["placement_status"] = "unplaced_relation_group"
                o["unplaced_reason"] = "局部方向存在，但尚无可核关系链接入源锚；不把旧卡片位置变成全城址点。"

    for c in constraints:
        if c["type"] not in CARDINAL:
            continue
        a, b = c["evaluation_from_object_id"], c["evaluation_to_object_id"]
        aa, bb = box_for(a), box_for(b)
        if a == b:
            c["status"] = "unresolved_same_proxy"
            c["reason"] = "双方共用显示proxy，不能评价相互方位。"
            continue
        if not aa or not bb:
            c["status"] = "unavailable"
            c["reason"] = "一方或双方尚未落位；保存原关系，不以图签代替坐标。"
            c["unavailable_object_ids"] = [oid for oid, box in ((a, aa), (b, bb)) if not box]
            continue
        axis, sign = CARDINAL[c["type"]]
        av = aa[axis if sign > 0 else axis + 2]
        bv = bb[axis + 2 if sign > 0 else axis]
        separation = sign * (av - bv)
        c["evaluated"] = True
        c["status"] = "satisfied" if separation > tolerance else "unsatisfied"
        c["numeric_evaluation"] = {
            "axis": "xy"[axis], "signed_separation_m": separation,
            "from_proxy_axis_range_m": [aa[axis], aa[axis+2]],
            "to_proxy_axis_range_m": [bb[axis], bb[axis+2]],
            "from_proxy_object_id": a, "to_proxy_object_id": b,
            "required_display_margin_m": margin, "satisfies_direction": separation > tolerance,
            "satisfies_display_margin": separation >= margin - tolerance,
            "both_source_proxies_fixed": objects[a]["fixed"] and objects[b]["fixed"],
            "archaeological_distance": False,
            "meaning": "只核当前候选布局与所列源／显示proxy的单轴顺序，不证明古代距离、完整界线或唯一位置。"}
        if c["status"] == "unsatisfied":
            c["reason"] = "当前固定源proxy／候选约束未能满足；保留差异，不移动源几何消除冲突。"

    # Complete the member register without feeding inherited memberships to
    # the coordinate solver.  Only unambiguous names/IDs are resolved.
    names = defaultdict(set)
    for eid, e in catalog.items():
        for name in [eid, e.get("name"), e.get("source_name"), *e.get("aliases", [])]:
            if isinstance(name, str) and name:
                names[name].add(eid)
    unresolved_memberships = []
    for eid, e in catalog.items():
        for ci, relation in enumerate(e.get("constraints", [])):
            if relation["relation"] not in {"inside", "within", "in_ward", "within_region", "at_region", "contains"}:
                continue
            raw_target = relation.get("target_id") or relation.get("target")
            targets = {raw_target} if raw_target in catalog else names.get(raw_target, set())
            if len(targets) != 1:
                unresolved_memberships.append({"entity_id": eid, "raw_target": raw_target,
                    "source_ref": entity_ref(eid, f"/constraints/{ci}"), "candidate_entity_ids": sorted(targets)})
                continue
            target = next(iter(targets))
            child, parent = (target, eid) if relation["relation"] == "contains" else (eid, target)
            a, b = eid_object(child), eid_object(parent)
            if a not in objects or b not in objects or a == b:
                continue
            link = {"parent_object_id": b, "parent_entity_id": parent,
                "source_refs": [entity_ref(eid, f"/constraints/{ci}")],
                "geometry_or_coordinate_inferred": False, "used_by_solver": False,
                "basis": relation.get("evidence_kind", relation.get("basis"))}
            objects[a].setdefault("catalog_membership_links", []).append(link)
            if b not in objects[a]["member_of"]:
                objects[a]["member_of"].append(b)
    for _ in range(12):
        changed = False
        for o in objects.values():
            regions_before = set(o["region_ids"])
            regions_after = regions_before | {r for p in o["member_of"] if p in objects for r in objects[p]["region_ids"]}
            if regions_after != regions_before:
                o["region_ids"] = sorted(regions_after)
                changed = True
        if not changed:
            break

    geometry_by_entity = defaultdict(list)
    for f in geometry["features"]:
        for eid in f.get("entity_ids", []):
            geometry_by_entity[eid].append(f["id"])
    constraint_by_entity = defaultdict(list)
    for c in constraints:
        for eid in set(c["from_entity_ids"] + c["to_entity_ids"]):
            constraint_by_entity[eid].append(c["id"])
    entities = []
    for eid, original in catalog.items():
        oids = sorted(entity_to_objects[eid])
        rows = [objects[oid] for oid in oids]
        feature_ids = sorted(set(geometry_by_entity[eid] + [fid for o in rows for fid in o.get("feature_ids", [])]))
        own_candidates = [o for o in rows if o["placement_status"] == "candidate_marker"]
        group_candidates = [o for o in rows if o["placement_status"] in {"directional_group_reference", "directional_group_member"}]
        if geometry_by_entity[eid]:
            placement_class, reason = "source_geometry_bound", None
        elif own_candidates:
            placement_class, reason = "candidate_marker", None
        elif group_candidates:
            placement_class, reason = "directional_group_only", "已入共同方向签；成员独立位置、内部次序和地块界线未定。"
        else:
            placement_class = "unplaced"
            reason = "；".join(dict.fromkeys(o["unplaced_reason"] for o in rows if o["unplaced_reason"]))
        override = temporal.get(eid, {})
        temporal_ref = [ref(paths["temporal"], "/" + eid, "temporal-" + eid)] if override else []
        entities.append({"id": eid, "entity_id": eid, "map_id": original["map_id"],
            "name": original["name"], "source_name": original.get("source_name"),
            "main_scene_name": override.get("main_scene_name") or original["name"],
            "type": original["type"], "object_ids": oids,
            "component_ids": [o["component_id"] for o in rows], "feature_ids": feature_ids,
            "placement_class": placement_class, "unplaced_reason": reason,
            "temporal_state": override.get("prosperity_state", original.get("temporal_state")),
            "temporal_note": override.get("note"), "tower_state": override.get("tower_state"),
            "later_elements": override.get("later_elements", []),
            "source_url": original.get("source_url"), "source_ref": original.get("source_ref"),
            "source_quote": original.get("source_quote"),
            "source_refs": _unique_refs([entity_ref(eid), *temporal_ref, *[r for o in rows for r in o["source_refs"]]]),
            "r10_node_ids": sorted({n for o in rows for n in o["r10_node_ids"]}),
            "constraint_ids": sorted(set(constraint_by_entity[eid])),
            "region_ids": sorted({r for o in rows for r in o["region_ids"]}),
            "catalog_membership_links": [link for o in rows for link in o.get("catalog_membership_links", [])],
            "member_of": sorted({p for o in rows for p in o["member_of"]}),
            "original_constraints": original.get("constraints", []),
            "original_frames": original.get("frames", []), "original_modes": original.get("modes", []),
            "geographic_coordinates": None, "is_one_building_footprint": False})

    # Every region is a crop of the same mother coordinates, never a new frame.
    regions = []
    for ri, r in enumerate(inputs["regions"]):
        code = r["code"]
        r10_region = next(x for x in inputs["r10"]["regions"] if x["id"] == code)
        related_eids = set(r["focus_ids"]) | {eid for o in objects.values() if code in o["region_ids"] for eid in o["entity_ids"]}
        geometries = [f["geometry"] for f in [*geometry["features"], *features]
                      if code in f.get("region_ids", []) or any(eid in related_eids for eid in f.get("entity_ids", []))]
        bbox = _bbox(geometries)
        method = "extent_of_related_features_on_master_frame"
        if bbox:
            padding = max(120.0, max(bbox[2]-bbox[0], bbox[3]-bbox[1]) * .08)
            bbox = [bbox[0]-padding, bbox[1]-padding, bbox[2]+padding, bbox[3]+padding]
        else:
            x, y, w, h = r["bbox"]
            pts = [_apply(registration["matrix"], p) for p in [[x,y],[x+w,y],[x+w,y+h],[x,y+h]]]
            bbox = [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)]
            method = "registered_legacy_view_crop_only_no_location_claim"
        regions.append({"id": code, "region_id": code, "title": r10_region["title"],
            "coordinate_frame": frame_id, "bbox": bbox, "view_bbox_m": bbox,
            "extent_role": "view_crop_not_historical_boundary", "extent_method": method,
            "entity_ids": sorted(related_eids),
            "feature_ids": [f["id"] for f in [*geometry["features"], *features]
                if code in f.get("region_ids", []) or any(eid in related_eids for eid in f.get("entity_ids", []))],
            "source_refs": [ref(paths["regions"], f"/{ri}"), ref(paths["r10"], f"/regions/{ri}")],
            "limits": ["只是同一母图的阅读窗口，不是行政区、里坊或遗址边界。",
                       "未定位名录仍随所属区域可查，不因裁图获得坐标。"]})

    for o in objects.values():
        o["source_refs"] = _unique_refs(o["source_refs"])
        o["limits"] = list(dict.fromkeys(o["limits"]))
        o.pop("legacy_group_seed", None)
    direction_constraints = [c for c in constraints if c["type"] in CARDINAL]
    r10_direction = [c for c in direction_constraints if c["origin"] == "R10"]
    diagnostics = {"catalog_entities": len(entities), "r10_nodes": len(node_to_object),
        "r10_node_to_object": node_to_object, "physical_geometry_identity_inferred_from_entity_id": False,
        "objects": len(objects), "candidate_features": len(features),
        "catalog_placement_counts": dict(Counter(e["placement_class"] for e in entities)),
        "object_placement_counts": dict(Counter(o["placement_status"] for o in objects.values())),
        "r10_catalog_entities": len({eid for n in r10_nodes.values() for eid in n.get("entity_ids", [])}),
        "r10_relations": sum(c["origin"] == "R10" for c in constraints),
        "r10_direction_constraints": len(r10_direction),
        "r10_direction_status_counts": dict(Counter(c["status"] for c in r10_direction)),
        "all_direction_status_counts": dict(Counter(c["status"] for c in direction_constraints)),
        "registration": registration, "solver": {**config["solver"], "iterations": iterations},
        "source_geometries_modified": False, "new_building_footprints_generated": 0,
        "original_distances_converted_to_metres": 0,
        "unresolved_catalog_memberships": unresolved_memberships,
        "unsatisfied_constraint_ids": [c["id"] for c in direction_constraints if c["status"] == "unsatisfied"],
        "unavailable_constraint_ids": [c["id"] for c in direction_constraints if c["status"] == "unavailable"],
        "largest_candidate_adjustments": sorted([{"object_id": o["id"], "label": o["label"],
            "norm_m": o.get("layout_adjustment_norm_m", 0), "xy_m": o.get("layout_adjustment_m")}
            for o in objects.values() if o["id"] in positions], key=lambda x:x["norm_m"], reverse=True)[:20],
        "validation_scope": "这核查可见布局与既有方向记录的相容，不是古代测绘、位置唯一性或史实证明。"}
    if len(entities) != 339 or set(e["id"] for e in entities) != set(catalog):
        raise ValueError("R11 catalog coverage must preserve the 339 original identities")
    if len(r10_nodes) != 321 or len(r10_direction) != 164:
        raise ValueError("R10 node/direction baseline changed; review before rebuilding")
    if any(f["geometry"]["type"] != "Point" for f in features):
        raise ValueError("Object module must not synthesize footprints or street lines")
    return {"frame": geometry["frame"], "objects": list(objects.values()), "features": features,
            "entities": entities, "constraints": constraints, "diagnostics": diagnostics,
            "regions": regions, "sources": [ref(p, "", "input-"+k) for k,p in paths.items()] + [ref(CONFIG, "", "r11-object-method")]}


if __name__ == "__main__":
    import argparse
    from city_plan_r11_geometry import build_geometry
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_objects(args.root, build_geometry(args.root))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({k:result["diagnostics"][k] for k in ["catalog_entities","objects","candidate_features",
        "catalog_placement_counts","r10_direction_status_counts"]}, ensure_ascii=False))
