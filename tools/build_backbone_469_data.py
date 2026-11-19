"""Derive a current, source-separated index without changing archived geometry."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "research/prosperity-v4/backbone-469"


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main():
    audit = read("research/prosperity-v4/backbone-469/source-frame-audit.json")
    data = {key: copy.deepcopy(audit[key]) for key in (
        "frames", "water_evidence_navigation", "correction", "corrected_current_I09",
        "current_water_ledger", "input_sha256")}
    data.update({
        "schema_version": "1.0",
        "version": "P4.6.9",
        "title": "水陆骨架：遗存图、复原图与水系证据联读",
        "summary": "把已经核读的城墙、门址、八条内城道路及城周读点按各自原图汇合；34项水体采用校正后的证据索引。两套图框保持独立，水道关系只在证据栏中关联。",
        "target_period": "516—528年",
        "target_period_ce": [516, 528],
        "study_date": "2026-11-19",
        "baseline_commit": audit["baseline_commit"],
        "new_geographic_coordinates": 0,
        "new_metric_measurements": 0,
        "new_516_528_bank_geometry": None,
        "phase_rule": "目标时段是516—528年；源图遗存的东汉至北魏、魏晋至北魏或北魏大阶段均按来源保留，不改写为目标十三年逐段持续使用的证明。",
        "scope_completion": {
            "water_evidence_inventory": "已将34项旧编号及P467/P468的100条关系汇成当前可查询视图，并应用P468校正。",
            "ancient_riverbank_reconstruction": "未完成；目前没有新增可归入516—528年的精确古河岸。",
            "book_2022": "按用户2026-11-19指示暂缓，不再作为本轮推进前提。",
            "road_02": "原刊最后实测点、邙山北路终点及合流仍未核得，已完成有边界的新增路径补查。",
            "road_01": "南门与大道相接可入关系骨架；南门至中央十字的完整距离和连续揭露仍未证。",
        },
        "unknowns": {
            "inner_south_wall_geometry": None,
            "xuanyang_gate_geographic_coordinates": None,
            "yongqiao_bank_landings": [None, None],
            "north_road_confluence_coordinates": None,
            "chengming_westernmost_survey_station": None,
            "daxia_last_field_station": None,
            "guangmo_last_field_station": None,
            "yinluo_section_width_m": None,
            "yinluo_section_depth_m": None,
            "biyong_flow_516_528": None,
            "ward_gate_to_central_cross_m": None,
        },
        "source_reading_notes": [
            "图06a使用来源PDF点坐标；其另存地理几何仍为西安1980/EPSG:4610，不当作WGS84。",
            "钱2018图一的三批读点均来自朱2024印页17图6同一1145×951嵌入图；图上尺度只说明复原图读数。",
            "六组东西郭门两端不是六条新追踪线；缺失的中段不补连成连续实测道路。",
            "古洛水图带为后出学者复原表达；桥符号两端为图符端，不是考古登陆点。",
            "水体与门道的链接表示文献上下文；无相对距离时不把水线贴附或平移到道路边。",
            "水体旧编号用于来源追踪，不代表34个可逐一划界、互不重叠且同期通水的实体。",
        ],
        "source_access_files": ["road01-source-audit.json", "road02-access-20261119.json"],
    })
    geo = read("research/prosperity-v1/geographic-evidence.json")
    gates = read("research/prosperity-v4/gates-465/readings.json")
    south = read("research/prosperity-v4/south-466/readings.json")
    outer = read("research/prosperity-v4/network-462/outer.json")
    data["frames"][0]["features"] = copy.deepcopy(geo["features"])
    data["frames"][0]["source_crs"] = copy.deepcopy(geo["crs"])
    data["frames"][0]["sources"] = copy.deepcopy(geo["sources"])
    data["frames"][0]["rendering_coordinate_system"] = "source_pdf_geometry; PDF points, upper-left origin"
    data["frames"][0]["modern_river_default_visible"] = False
    data["frames"][0]["provisional_envelope_default_visible"] = False
    data["frames"][1]["north_reading"] = copy.deepcopy(gates["later_plan"])
    data["frames"][1]["south_reading"] = copy.deepcopy(south["plan"])
    data["frames"][1]["outer_corridors"] = copy.deepcopy(outer["corridors"])
    data["frames"][1]["outer_corridor_display"] = "endpoint_pairs_only; no newly traced road"
    data["frames"][1]["geographic_transform"] = None
    data["frames"][2]["geographic_transform"] = None

    relations, plates = [], []
    for version, folder in (("P467", "water-467"), ("P468", "water-468")):
        src = read(f"research/prosperity-v4/{folder}/readings.json")
        sources = {s["id"]: s for s in src["sources"]}
        for plate in src["plates"]:
            plate_ref = f"{version}/{plate['id']}"
            page = f"prosperity-water-{version.lower()}.html#map={plate['id']}&layer=all"
            plates.append({"ref": plate_ref, "title": plate["title"], "page": page,
                           "svg": f"{folder}/{plate['id']}.svg", "segment_count": len(plate["segments"])})
            nodes = {node["id"]: node["label"] for node in plate["nodes"]}
            for raw in plate["segments"]:
                # SVG layout coordinates have no role in the current evidence index.
                item = {key: copy.deepcopy(value) for key, value in raw.items()
                        if key not in {"points", "x", "y", "label_position"}}
                item.update({"ref": f"{plate_ref}/{raw['id']}", "version": version,
                             "plate_id": plate["id"], "plate_title": plate["title"],
                             "page": page, "from_label": nodes[raw["from"]],
                             "to_label": nodes[raw["to"]],
                             "sources": [copy.deepcopy(sources[sid]) for sid in raw["source_ids"]],
                             "geographic_coordinates": None,
                             "legacy_water_ids": copy.deepcopy(raw.get("legacy_water_ids", [])),
                             "legacy_index_semantics": "subject_or_source_context; not a hydraulic connection"})
                if item["ref"] == "P467/inner/I09":
                    correction = data["corrected_current_I09"]
                    item["legacy_water_ids"] = correction["legacy_water_ids"][:]
                    item["quote"] = correction["quote"]
                    item["reading"] = correction["meaning"]
                    item["limit"] = "仅为华林园池群在旱涝条件下的总说，不分配到各池接口，不推定全年恒流。撤回W20/W21索引也不证明两池绝无水路。"
                    item["current_correction"] = data["correction"]["id"]
                relations.append(item)

    # The source supplement intentionally split these archaeological contexts.
    # Do not turn the old broad W14 label into identity with every palace drain.
    explicit_subjects = {
        "M03": ["W10"], "M06": ["W10"], "M07": ["W10"], "M08": ["W10"],
        "M09": ["W11"], "M10": ["W12"], "D07": ["W13"], "D08": ["W13"],
    }
    for item in relations:
        if item["version"] == "P468" and item["id"] in explicit_subjects:
            item["legacy_water_ids"] = explicit_subjects[item["id"]]
            item["legacy_index_semantics"] = "current thematic subject index; retain relationship and phase class"
    for water in data["current_water_ledger"]:
        water["current_refs"] = [s["ref"] for s in relations if water["id"] in s["legacy_water_ids"]]
        water["geometry"] = None
        water["geographic_frame"] = None
        water["target_bank_geometry"] = None
        if water["current_record_source"] == "P468":
            water["context_plate_refs"] = ["P468/" + water["current_record"]["本册图"]]
        else:
            water["context_plate_refs"] = sorted({"/".join(ref.split("/")[:2]) for ref in water["current_refs"]})
        if water["id"] == "W14":
            water["current_record"]["状态"] = "旧编号只作研究入口；宫西主区、北窗口、千秋门及早期明渠分开，不能把全图水道合并为同一魏晋设施。"
        if water["id"] in {"W20", "W21"}:
            # The archive pointer remains provenance, never a current reverse link.
            water["archive_record_status"] = "withdrawn historical index; not current evidence"
        water["current_index_basis"] = "图段主题索引，非管网节点或逐年通水名册；主题图链接不等于其中全部图段归属此水体。"
    data["current_relations"] = relations
    data["relation_plates"] = plates
    data["counts"] = {"source_features_06a": len(geo["features"]), "source_road_features": 8,
                      "qian_outer_endpoint_pairs": len(outer["corridors"]),
                      "water_records": len(data["current_water_ledger"]), "current_relations": len(relations),
                      "relationship_plates": len(plates), "place_context_links": len(data["water_evidence_navigation"])}
    data["road01"] = read("research/prosperity-v4/backbone-469/road01-source-audit.json")
    for path, expected in data["input_sha256"].items():
        actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Archived input changed: {path}")
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "readings.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
