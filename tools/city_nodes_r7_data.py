"""Read-only joins of existing entities, roads, waters and four reviewed nodes."""
import copy
import hashlib
import json
from pathlib import Path

from city_nodes_r7_contract import BASE, PAGE, VERSION

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research/city-nodes-r7"
ORDER = ("palace-yongning", "baima", "sima", "jianchun")
TITLES = {
    "palace-yongning": "宫前御道与永宁寺",
    "baima": "白马寺南坊门与坊街",
    "sima": "司马门内道路与仓区",
    "jianchun": "建春门三桥与水道",
}
SHORT = {"palace-yongning": "宫前与永宁", "baima": "白马寺坊街", "sima": "司马门与仓区", "jianchun": "建春门桥渠"}
BASIS_LABELS = {"documentary": "文献关系", "source_geometry": "来源图对应", "source_trace": "来源图笔画",
                "interpretation": "研究解释", "temporal": "年代核验", "negative_control": "接合限制",
                "reported_measurement": "报告量值", "excavation": "发掘观察", "unknown": "仍待证"}
RELATION_LABELS = {"explicit": "材料明确记述", "interpretive": "研究解释", "candidate": "候选对应", "unknown": "接续待证"}
GUIDES = [
    dict(id="palace", label="宫城与阊阖门", x=38, y=25, node="palace-yongning", road_ids=["G01"], water_ids=[],
         level="来源图与建筑关系", statement="宫城、宫前阊阖门与太极殿有来源图参照。画中的殿堂外观、屋顶与完整院落属于艺术表达。", link="#node-palace-yongning"),
    dict(id="yongning", label="永宁寺", x=30, y=41, node="palace-yongning", road_ids=["R01","T01"], water_ids=[],
         level="位置参照与文献关系", statement="永宁寺与宫前御道的相对位置可对读。寺院墙迹、塔基图符与文献所记寺东官署分别查证，不从画面量寺院尺寸。", link="#node-palace-yongning"),
    dict(id="avenue", label="宫前大道", x=43, y=41, node="palace-yongning", road_ids=["R01","T01"], water_ids=[],
         level="原图残段与文献道路", statement="图06a的铜驼道路残段与文献御道保留候选对应。画面中的连续大道不能填补研究图的断段或证明全程同路。", link="#segment-R01"),
    dict(id="southgate", label="南城门与门外道路", x=47, y=56, node=None, road_ids=["T13"], water_ids=["W01"],
         level="文献相对位置", statement="宣阳门外御道与永桥有文献接续。南门、古南墙及桥头的同框位置仍待原测依据；首页的门墙和道路连续形态为展示推定。", link="#segment-T13"),
    dict(id="luo", label="洛水", x=34, y=76, node=None, road_ids=["B04"], water_ids=["W01"],
         level="水道关系，岸线未定", statement="洛水与永桥的跨水关系有据。现有材料未测定516—528年的完整河岸，画面的水面宽度、洲滩和两岸形状为艺术表达。", link="#water-W01"),
    dict(id="bridge", label="永桥与两岸", x=58, y=78, node=None, road_ids=["B04","T15"], water_ids=["W01"],
         level="浮桥有据，登陆点未知", statement="文献记宣阳门外至洛水浮桥。北岸、南岸登陆点均未知，四里是门至洛水的相对距离，不能作桥长或画面比例尺。", link="#segment-B04"),
]


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pointer(document, path):
    node = document
    for token in path.strip("/").split("/") if path else ():
        token = token.replace("~1", "/").replace("~0", "~")
        node = node[int(token)] if isinstance(node, list) else node[token]
    return node


def build_data(site):
    atlas = load(site / "city-atlas/atlas.json")
    catalog = load(ROOT / "research/roads-r62/catalog.json")
    by_road = {r["id"]: r for r in catalog["records"]}
    sources = catalog["sources"] if isinstance(catalog["sources"], dict) else {s["id"]: s for s in catalog["sources"]}
    by_water = {w["id"]: w for w in atlas["waters"]}
    nodes, inputs = [], {}
    for key in ORDER:
        path = DATA / "reviews" / (key + ".json")
        node = load(path)
        assert node["id"] == key and node["accepted_new_geographic_coordinates"] == 0
        node.update(short_title=SHORT[key], public_title=TITLES[key])
        inputs[str(path.relative_to(ROOT))] = sha(path)
        for finding in node["findings"]:
            for item in finding.get("source_inputs", []):
                native = ROOT / item["path"]
                if native.suffix == ".json":
                    pointer(load(native), item["pointer"])
                inputs[item["path"]] = sha(native)
        for rid in node["road_ids"]:
            assert rid in by_road, (key, rid)
        for wid in node["water_ids"]:
            assert wid in by_water, (key, wid)
        nodes.append(node)
    ids = set(r for n in nodes for r in n["road_ids"]) | set(r for g in GUIDES for r in g["road_ids"])
    rows = []
    for original in catalog["records"]:
        if original["id"] not in ids:
            continue
        row = copy.deepcopy(original)
        row["node_ids"] = [n["id"] for n in nodes if row["id"] in n["road_ids"]]
        row["node_names"] = [TITLES[n] for n in row["node_ids"]] or ["首页南城门、洛水与永桥导览"]
        row["findings"] = [dict(node_id=n["id"], **copy.deepcopy(f))
                           for n in nodes for f in n["findings"] if row["id"] in f.get("road_ids", [])]
        row["context_findings"] = [dict(node_id=n["id"], **copy.deepcopy(f))
                                   for n in nodes for f in n["findings"] if row["id"] in f.get("context_road_ids", [])]
        cited = {(f["node_id"], source) for f in row["findings"] + row["context_findings"] for source in f["source_ids"]}
        row["review_source_citations"] = [dict(node_id=n["id"], **copy.deepcopy(source))
                                          for n in nodes for source in n["source_refs"] if (n["id"], source["id"]) in cited]
        row["next_originals"] = [dict(node_id=n["id"], **copy.deepcopy(item))
                                for n in nodes if n["id"] in row["node_ids"] for item in n["next_originals"]]
        row["source_citations"] = [dict(id=ref, **{k: v for k, v in sources[ref].items() if k != "id"}) for ref in row["source_refs"]]
        row["geometry_status"] = "source_frame" if row.get("geometry_refs") else "relation_only"
        row["geometry_label"] = "有独立来源图笔画或符号" if row.get("geometry_refs") else "目前只到地段或关系"
        row["temporal_status"] = "changes_within_window" if row["id"] == "B01" else "documentary_reference" if row["group"] in ("documentary", "bridge") else "phase_not_resolved"
        row["temporal_label"] = {"changes_within_window": "527年状态有变化", "documentary_reference": "文献时层，使用年份未逐年细分", "phase_not_resolved": "宽时段材料，516—528同期性待核"}[row["temporal_status"]]
        row["original_url"] = BASE + "luoyang-all-roads.html#" + row["id"]
        rows.append(row)
    water_ids = set(w for n in nodes for w in n["water_ids"]) | set(w for g in GUIDES for w in g["water_ids"]) | set(w["id"] for r in rows for w in r.get("water_constraints", []))
    waters = []
    for wid, original in by_water.items():
        if wid not in water_ids:
            continue
        row = copy.deepcopy(original)
        row["node_ids"] = [n["id"] for n in nodes if wid in n["water_ids"]]
        row["original_url"] = BASE + "luoyang-water-atlas.html#" + wid
        waters.append(row)
    entity_index = [dict(id=e["id"], name=e["name"], placement=e["placement"], period=e["period"],
                         node_ids=[n["id"] for n in nodes if e["id"] in n["entity_ids"]],
                         url=BASE + "prosperity-city-atlas.html#entity-" + e["id"]) for e in atlas["entities"]]
    road_index = [dict(id=r["id"], name=r["name"], group=r["group"], entity_ids=r.get("entity_ids", []),
                       node_ids=[n["id"] for n in nodes if r["id"] in n["road_ids"]],
                       url=BASE + "luoyang-all-roads.html#" + r["id"]) for r in catalog["records"]]
    water_index = [dict(id=w["id"], name=w["name"], node_ids=[n["id"] for n in nodes if w["id"] in n["water_ids"]],
                        url=BASE + "luoyang-water-atlas.html#" + w["id"]) for w in atlas["waters"]]
    for path in ("research/roads-r62/catalog.json", "research/prosperity-v1/geographic-evidence.json", "research/prosperity-r5/sima-road.json", "research/water-atlas/huang-figure1.json", "research/water-atlas/locations.tsv"):
        inputs[path] = sha(ROOT / path)
    # The new join does not alter its ancestors. Record every available native
    # input, including the segment geometry references and reviewed JSON pointers.
    def visit(value):
        if isinstance(value, dict):
            for key in ("path", "source_path"):
                candidate = value.get(key)
                if isinstance(candidate, str) and (ROOT / candidate).is_file():
                    inputs[candidate] = sha(ROOT / candidate)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(nodes)
    visit(rows)
    for path, expected in atlas["research_inputs_sha256"].items():
        assert sha(ROOT / path) == expected
        inputs[path] = expected
    published_inputs = dict(atlas["source_inputs_sha256"])
    published_inputs["city-atlas/atlas.json"] = sha(site / "city-atlas/atlas.json")
    return dict(schema="luoyang-city-nodes-v1", research_version="R7.1", implementation_version=VERSION,
                target_years=[516, 528], nodes=nodes, segments=rows, waters=waters, guides=copy.deepcopy(GUIDES),
                entity_index=entity_index, road_index=road_index, water_index=water_index,
                source_inputs_sha256=inputs, published_inputs_sha256=published_inputs,
                source_frames_registered_together=False,
                new_historical_coordinates=0, new_shoreline_geometries=0, homepage_revision="panorama-approved-v12",
                counts=dict(nodes=len(nodes), findings=sum(len(n["findings"]) for n in nodes),
                            relations=sum(len(n["relations"]) for n in nodes), segments=len(rows), waters=len(waters),
                            entities_indexed=len(entity_index), roads_indexed=len(road_index), waters_indexed=len(water_index)),
                scope="四处节点的关系、量值对象和同期性核验；逐段表按来源记录登记，计数不等于独立古路数量。")
