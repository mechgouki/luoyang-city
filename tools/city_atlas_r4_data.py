"""Join the published city views using catalogue identities and source-native frames."""
from collections import Counter, defaultdict
from pathlib import Path

from prosperity_city_common_p470 import load, sha

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "research/prosperity-r4"
INPUTS = {
    "catalog": "data/entities.json", "text": "prosperity/text-review.json",
    "geo": "prosperity/geographic-evidence.json", "plan": "prosperity/data.json",
    "literary_svg": "prosperity/literary-plan.svg", "ledger": "city-review/ledger.json",
    "cases": "city-review/cases.json", "common": "common-470/readings.json",
    "north": "north-471/readings.json", "west": "west-472/readings.json",
    "terrain": "prosperity/terrain-constraints.json", "backbone": "backbone-469/readings.json",
    "jianchun": "backbone-469/jianchun-plan-audit.json", "qian_svg": "backbone-469/frame-qian2018.svg",
}
P46 = "research/prosperity-v4/hydro-roads-anchor-p46.json"
LEVELS = {"source": "来源图有对应", "candidate": "候选范围参照", "relative": "文献相对关系", "unlocated": "位置未定"}
PERIODS = {"attested": "528年前有记载", "conditional": "依赖身份或时段条件", "later": "后出寺名或构件时层",
           "name": "名称分期", "undated": "年代未详", "unspecified": "名录未单列断代"}
# A reading's topic is distinct from a survey polygon and from a location assignment.
BATCH_TOPICS = {"B2": "R03", "B3": "R05", "B4": "R01", "B5": "R02", "B7": "R11", "v2.5": "R07"}
# The older cross-city water and event batch spans more than one plate.
NETWORK_TOPICS = {
    "N01":["R04"], "N02":["R04"], "N03":["R04"], "N04":["R01","R04"], "N05":["R03"],
    "N06":["R03","R07"], "N07":["R07"], "N08":["R02","R07","R08"], "N09":["R07","R08"],
    "N10":["R10"], "N11":[], "N12":["R10","R11"], "N13":["R07","R10","R11"], "N14":["R07","R10"],
    "N15":["R07"], "N16":["R10"], "N17":["R04"], "N18":[], "N19":["R10"], "N20":[],
}
NEXT_GAP = {
    "gap-xuanyang-gate": "取得南墙与门道同图、带测网和断代的发掘或勘探记录。",
    "gap-inner-south-wall": "取得能跨接分段并识别北魏层位的墙基测线或钻孔。",
    "gap-complete-jinyong": "取得可分辨甲、乙、丙三城及其分期的同框测绘图。",
    "gap-historical-luo": "取得有孔号、剖面、同层古岸及共同控制的河段资料。",
    "gap-historical-terrain": "取得同一高程基准下可分期的古土层、剖面和测点。",
    "gap-datum-transformation": "取得该地区适用的地理基准转换参数与独立检查点。",
}


def index(rows, key="id"):
    return {r[key]: r for r in rows}


def subset(row, keys):
    return {k: row[k] for k in keys}


def evidence_table(text, north, west):
    northern, western = index(north["evidence"]), index(west["records"])
    records = []
    for r in text["records"]:
        manual = r["manual_context_review"] or {}
        item = subset(r, ("key", "affected_entity_ids", "batch", "legacy_id", "legacy_path", "quotation_class",
                          "source_checks", "manual_context_review", "legacy_quote_passed_normalized_sequence_check",
                          "electronic_text_checked", "record_role"))
        item.update(title=r["legacy_title"], quote=manual.get("corrected_quote") or r["legacy_quote"],
                    reading=manual.get("finding") or r["legacy_reading_preserved"], locator=manual.get("locator") or r["legacy_locator"],
                    text_layer=r["legacy_evidence_layer"], temporal_note=r["legacy_temporal_note_preserved"],
                    annotations=[], region=BATCH_TOPICS.get(r["batch"]), legacy_quote=r["legacy_quote"])
        if r["batch"] == "B6":
            item["region"] = {"EI": "R08", "EO": "R09"}[r["legacy_id"][:2]]
        if r["batch"] == "B4":
            row = northern[r["legacy_id"]]
            overlay = row["reading_overlay"]
            item.update(quote=overlay["quote"], text_layer=overlay["textual_layer"], annotations=overlay["annotations"],
                        limit=row["limit"], temporal_note=row["temporal_note"], regional_reading=row["reading"])
        if r["batch"] == "B5":
            row = western[r["legacy_id"]]
            item.update(regional_reading=row["working_reading"]["map_reading"], period_scope=row["working_reading"]["period_label"],
                        limit=row["b5"]["limit"], variants=row["b5"]["variants"])
        item["regions"] = [item["region"]] if item["region"] else []
        if r["batch"] == "v2.7":
            item["regions"] = NETWORK_TOPICS[r["legacy_id"]]
        if r["batch"] == "B1":
            n = int(r["legacy_id"][1:])
            item["regions"] = ["R07" if n <= 5 else "R04" if n <= 9 else "R10"]
        if r["key"] == "v2.5:E02":
            item["regions"] = ["R06","R07"]
        if r["key"] in ("v2.7:N18","v2.7:N20"):
            item["period_scope"] = "目标时层之后的全城事件或回顾；保留文本，无逐址几何。"
        records.append(item)
    return records


def phase(e, b8):
    if b8["current_review"].get("temporal_label"):
        return "conditional"
    return {None: "unspecified", "undated": "undated", "later_temple": "later", "attested_by_528": "attested",
            "name_layer": "name"}[e["temporal_state"]]


IDENTITY_ONLY = set("""associated associated_former_site associated_with associated_with_gate associated_access_via
converted_from historically_associated_with historical_site historical_site_of later_became later_moved_to
not_identical predecessor_of predecessor_site prior_housing_of related_gate reported_former_identity
same_historical_site same_site_claim extent_original orientation""".split())


def placement(raw, entity, direct, related, reviews):
    if direct:
        return "source", entity["placement_note"], None
    if "geo-palace-layout-envelope" in related:
        return "candidate", "宫城三面墙有来源图参照，北缘仅为候选范围的填色闭合边。", None
    if raw["id"] in reviews:
        level, reference, reading = reviews[raw["id"]]
        return level, reading, reference
    if any(c["relation"] not in IDENTITY_ONLY for c in raw["constraints"]):
        return "relative", "名录保存相对位置或范围的记载，参照对象、断代及语义限定见依据栏。", None
    return "unlocated", "本项现有依据只到名录、身份、用途或沿革，尚缺独立定位。", None


def resume_condition(row, level):
    if level == "source":
        return "如需精化，核对带比例尺、断代及独立控制的原测图，标定图符或遗存的实际范围。"
    if level == "candidate":
        return "取得同层北墙端点及与三面墙的联测图，核清文献范围与墙段的对应。"
    kind = row["type"]
    if kind in {"河流", "water", "水道", "river", "pond", "watercourse", "watercourse_region", "weir"}:
        return "须有可断代的河槽、池岸或渠段剖面，且能同图对应已知控制位置。"
    if kind in {"road", "道路", "桥", "浮桥", "bridge", "city_gate", "城门", "郭门", "palace_gate"}:
        return "须有可辨端点或桥门遗迹的原测平面，附比例尺、时期与可独立复认的控制。"
    if not row["constraints"]:
        return "先核能辨认同一对象、时期和邻接参照的记载，再核有共同控制的原位置图。"
    return "先核引文的参照对象及同一时期，再取同时覆盖双方的带尺位置图和独立控制。"


def build_data(site):
    inputs = {k:load(site / path) for k,path in INPUTS.items() if not k.endswith("_svg")}
    p1, ledger, geo, text = (inputs[k] for k in ("plan", "ledger", "geo", "text"))
    common, north, west = (inputs[k] for k in ("common", "north", "west"))
    entities, directory, catalog = index(p1["entities"]), index(ledger["entities"]), inputs["catalog"]
    if set(entities) != set(directory) or set(entities) != set(index(catalog)):
        raise ValueError("P1, B8 and the catalogue must identify the same objects")
    records = evidence_table(text, north, west)
    by_entity, constraint_refs, decisions = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in records:
        for eid in r["affected_entity_ids"]:
            by_entity[eid].append(r)
    for ref in text["constraint_references"]:
        constraint_refs[ref["entity_id"]].append(ref["reference_key"])
    for decision in text["map_decisions"]:
        for eid in decision["affected_entity_ids"]:
            decisions[eid].append(decision["id"])
    current_topics = defaultdict(set)
    for cluster in common["urban"]["clusters"]:
        for n in cluster["nodes"]:
            current_topics[n["id"]].add("P470")
    for card in common["places"]:
        if card.get("entity_id"):
            current_topics[card["entity_id"]].add("P470")
    for row in north["entity_bindings"]:
        current_topics[row["entity_id"]].add("P471")
    for row in west["entities"]:
        current_topics[row["id"]].add("P472")
    related, direct = defaultdict(list), defaultdict(list)
    for f in geo["features"]:
        if f.get("entity_id"):
            direct[f["entity_id"]].append(f["id"])
        for eid in f.get("related_entity_ids", []):
            related[eid].append(f["id"])
    location_reviews = load(SOURCES / "location-readings.json")
    result = []
    for raw in catalog:
        eid = raw["id"]
        e, audit, readings = entities[eid], directory[eid], by_entity[eid]
        if set(e["source_feature_ids"]) != set(direct[eid]):
            raise ValueError("Review direct identity of " + eid)
        level, note, reference = placement(raw,e,direct[eid],related[eid],location_reviews)
        topics = sorted({region for r in readings for region in r["regions"]})
        item = subset(raw, ("id", "map_id", "source_name", "type", "juan", "source_url", "source_ref", "source_quote",
                            "constraints", "aliases"))
        item.update(name=audit["display_name"], level=level, p1_location=e["geographic_status"], period=phase(e,audit),
                    temporal_state=e["temporal_state"], temporal_label=e["temporal_label"], review_note=audit["current_review"].get("note"),
                    chronology=audit["chronology_refs"], drawing_periods=audit["drawing_status"]["current_temporal_displays"],
                    focus_regions=audit["explicit_focus_regions"], crop_regions=audit["crop_regions"], evidence_regions=topics,
                    current_topics=sorted(current_topics[eid]), feature_ids=direct[eid], context_features=related[eid],
                    placement=note, location_reading_ref=reference, next_evidence=resume_condition(raw,level), plan_targets=e["plan_target_ids"],
                    evidence=[r["key"] for r in readings], decisions=decisions[eid], cases=audit["case_ids"],
                    literal_targets=constraint_refs[eid])
        result.append(item)
    groups = load(SOURCES / "regions.json")
    regions_by_id, reading_index = index(ledger["regions"], "code"), index(records,"key")
    for region in groups:
        code = region["region"]
        if not {region["left"],region["right"]}.issubset(reading_index[region["evidence"]]["affected_entity_ids"]):
            raise ValueError("Regional example does not belong to its source " + code)
        region.update(focus_ids=regions_by_id[code]["focus_ids"], sheet=regions_by_id[code]["sheet_path"],
                      entity_ids=[e["id"] for e in result if code in e["focus_regions"] or code in e["evidence_regions"]])
    groups.append({"region":"register", "label":"其余名录与跨区对象",
                   "entity_ids":[e["id"] for e in result if not e["focus_regions"] and not e["evidence_regions"]]})
    p46, backbone = load(ROOT/P46), inputs["backbone"]
    water_orig = index(p46["water_features"])
    water = [dict(r,basis=water_orig[r["id"]]) for r in backbone["current_water_ledger"]]
    gaps = [dict(r,next_evidence=NEXT_GAP[r["id"]]) for r in geo["unlocated_or_unverified"]]
    return {
        "version":"R4.1", "period":"516—528 年河阴事件前的综合时层", "levels":LEVELS, "periods":PERIODS,
        "entities":result, "regions":groups, "records":records, "decisions":text["map_decisions"],
        "literal_targets":text["constraint_references"], "cases":inputs["cases"]["records"],
        "entities_without_source_binding":[e["id"] for e in result if not e["feature_ids"]],
        "targets":{t["id"]:t["member_ids"] for e in ledger["entities"] for t in e["targets"]},
        "features":geo["features"], "calibration":geo["calibration"], "crs":geo["crs"], "sources":geo["sources"],
        "exclusions":geo["excluded_from_prosperity_active_layer"], "gaps":gaps, "terrain":inputs["terrain"]["records"],
        "road_sources":p46["source_registry"], "roads":p46["main_road_records"], "waters":water,
        "water_relations":backbone["current_relations"], "water_correction":backbone["correction"],
        "unknowns":backbone["unknowns"], "qian_frame":backbone["frames"][1], "jianchun":inputs["jianchun"],
        "urban_clusters":common["urban"]["clusters"], "text_method":text["method"],
        "counts":{"entities":len(result), "levels":dict(Counter(e["level"] for e in result)),
                  "periods":dict(Counter(e["period"] for e in result)), "features":len(geo["features"]),
                  "direct_bindings":sum(map(len,direct.values())), "records":len(records), "literal_targets":len(text["constraint_references"]),
                  "manual_context_reviews":sum(r["manual_context_review"] is not None for r in records), "cases":len(inputs["cases"]["records"]),
                  "water_records":len(water), "water_relations":len(backbone["current_relations"]), "road_records":len(p46["main_road_records"])},
        "source_inputs_sha256":{path:sha(site/path) for path in INPUTS.values()},
        "research_inputs_sha256":{path:sha(ROOT/path) for path in (P46,"research/prosperity-r4/regions.json","research/prosperity-r4/location-readings.json")},
    }
