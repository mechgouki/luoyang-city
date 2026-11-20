"""Verify the public atlas, its native geometry and predecessor releases using standard Python."""
import copy
import csv
import io
import json
import re
import zipfile
from collections import Counter
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from verify_city_west_p472 import Links, digest, json_bytes, restore_commit

ROOT=Path(__file__).resolve().parents[1]
PAGE="prosperity-city-atlas.html"
WEST="prosperity-city-west.html"
HOME_ARCHIVE="homepage/history/index-before-r4.html"
KEY="prosperity_city_atlas_r4"
BASE="https://mechgouki.github.io/luoyang-city/"
NS="{http://www.w3.org/2000/svg}"
ENTRY='<p id="r4-atlas-entry"><a href="./prosperity-city-atlas.html"><strong>盛时洛阳城市分布总图 · 查阅全城对象与定位依据 →</strong></a></p>\n'.encode()


def predecessors(info,get,fixture):
    old,now=fixture["source_commit"],info["source_commit"]
    sums=info["files_sha256"]
    data=info[KEY]
    for path in ("index.html",WEST):
        content=get(path)
        assert content.count(ENTRY)==1 and digest(content)==sums[path]
        if path=="index.html" and "prosperity_city_panorama_r5" in info:
            from city_panorama_r5_contract import before_r5
            content=before_r5(info,path,content)
        before=content.replace(ENTRY,b"")
        assert digest(before)==data["entry_predecessors"][path]
        if path==WEST:
            assert digest(restore_commit(before,now,old))==fixture["west_page"]
        else:
            assert before==get(HOME_ARCHIVE) and digest(before)==sums[HOME_ARCHIVE]
            runtime,=re.findall(rb'<script src="\./([^"]*-runtime.js)"',before)
            boot=get(runtime.decode()); actual=digest(boot)
            assert actual==sums[runtime.decode()] and actual[:20] in runtime.decode()
            first=boot.splitlines()[0].decode()
            assert json.loads(first.split("=",1)[1].removesuffix(";"))["source_commit"]==now
            assert digest(before.replace(runtime,fixture["runtime"].encode()))==fixture["home"]
    west=info["prosperity_city_west_p472"]
    for name,checksum in fixture["assets"].items():
        assert digest(get(name))==sums[name]==checksum
    m=json.loads(get(west["manifest"]))
    assert m["source_commit"]==now and m["preservation"]==west["preservation"]
    original=copy.deepcopy(m)
    original["source_commit"]=old
    pre=original["preservation"]
    assert digest(get(pre["previous_page"]).replace(pre["entry_html"].encode(),b""))==pre["previous_page_sha256"]
    pre["previous_page_sha256"]=fixture["prior_north_before_entry"]
    # P472's verifier independently replays the P470 and P471 manifests, pages and every ZIP member.
    for name,checksum in fixture["upstream_hashes"].items():
        assert pre["protected_files_sha256"][name]==digest(get(name))==sums[name]
        pre["protected_files_sha256"][name]=checksum
    assert digest(json_bytes(original))==fixture["manifest"]
    members=fixture["bundle_members"]
    with zipfile.ZipFile(io.BytesIO(get(west["bundle"]))) as z:
        assert sorted(z.namelist())==sorted(members)
        for name,checksum in members.items():
            raw=z.read(name)
            if name=="index.html": raw=restore_commit(raw,now,old)
            elif name==west["manifest"]:
                assert raw==get(name)
                raw=json_bytes(original)
            else: assert raw==get(name)
            assert digest(raw)==checksum,name
    return {"p472_stable_assets":len(fixture["assets"]),"p472_offline_members":len(members),"entry_pages":2}


def verify(info,reader):
    get=lru_cache(maxsize=None)(reader)
    study=info[KEY]
    sums=info["files_sha256"]
    assert study["source_commit"]==info["source_commit"] and study["page"]==PAGE
    assert json.loads(get(study["manifest"]))==study
    release=json.loads(get("release.json"))
    assert study["version"] in release["extensions"] and study["version"]==release[KEY+"_version"]
    for path,expected in study["files_sha256"].items():
        assert digest(get(path))==sums[path]==expected,path
    for path in (study["bundle"],study["manifest"],PAGE):
        assert digest(get(path))==sums[path],path
    d=json.loads(get("city-atlas/atlas.json"))
    for path,h in d["source_inputs_sha256"].items():
        assert digest(get(path))==sums[path]==h,path
    for path,h in d["research_inputs_sha256"].items():
        assert digest((ROOT/path).read_bytes())==h,path
    cat=json.loads(get("data/entities.json"))
    entities={e["id"]:e for e in d["entities"]}
    assert len(cat)==len(entities)==len(d["entities"])==339 and set(entities)=={c["id"] for c in cat}
    assert sorted(set().union(*(r["entity_ids"] for r in d["regions"])))==sorted(entities)
    assert len(d["regions"])==12 and set(d["targets"])=={t for e in entities.values() for t in e["plan_targets"]}
    raw=get(PAGE); doc=Links(raw)
    assert len(set(doc.ids))==len(doc.ids) and doc.downloads==study["download_files"]
    ids=set(doc.ids)
    assert all("entity-"+key in ids for key in entities)
    assert all(url[1:].split("?")[0] in ids for url in doc.links if url.startswith("#"))
    for url in doc.links:
        parsed=urlsplit(url)
        if not parsed.scheme and parsed.path not in ("","./"):
            assert parsed.path.removeprefix("./") in sums,url
    counts=d["counts"]
    assert study["counts"]==counts and counts["levels"]==Counter(r["level"] for r in entities.values())
    assert counts["periods"]==Counter(r["period"] for r in entities.values())
    assert counts["direct_bindings"]==13 and len(d["entities_without_source_binding"])==328
    assert {e for e in entities if not entities[e]["feature_ids"]}==set(d["entities_without_source_binding"])
    p1=json.loads(get("prosperity/text-review.json"))
    original={r["key"]:r for r in p1["records"]}
    assert d["literal_targets"]==p1["constraint_references"] and len(d["literal_targets"])==236
    assert all(not row["adds_spatial_constraint"] for row in d["literal_targets"])
    assert d["decisions"]==p1["map_decisions"] and len(d["cases"])==14
    evidence={r["key"]:r for r in d["records"]}
    assert len(original)==len(evidence)==183 and set(original)==set(evidence)
    for key,row in evidence.items():
        assert "reading-"+key in ids
        m=original[key]["manual_context_review"]
        assert row["manual_context_review"]==m and row["affected_entity_ids"]==original[key]["affected_entity_ids"]
        assert row["quote"]==((m or {}).get("corrected_quote") or original[key]["legacy_quote"])
    assert len(evidence["B4:NG15"]["annotations"])==2 and '西北門' not in evidence["B4:NG15"]["quote"]
    assert entities["v2_baoming"]["period"]=="conditional" and not entities["gate_changhe_west"]["feature_ids"]
    assert entities["palace_scope"]["level"]=="candidate" and not entities["palace_scope"]["feature_ids"]
    assert len(d["waters"])==34 and len(d["roads"])==21 and len(d["water_relations"])==100
    assert all(not w["target_bank_geometry"] for w in d["waters"])
    for w in d["waters"]:
        if w["id"] in ("W20","W21"): assert "P467/inner/I09" not in w["current_refs"]
    assert d["jianchun"]["research_accounting"]["accepted_control_pairs"]==0
    original_geo=json.loads(get("prosperity/geographic-evidence.json"))
    assert d["features"]==original_geo["features"] and d["crs"]=="EPSG:4610"
    assert d["qian_frame"]["geographic_transform"] is None
    for name in ("city","core"):
        svg=ET.fromstring(get("city-atlas/"+name+".svg"))
        features={n.get("data-feature"):n for n in svg.iter() if n.get("data-feature")}
        assert len(features)==len(d["features"])==30
        for f in d["features"]:
            parent=features[f["id"]]
            shape=f["source_pdf_geometry"]; kind=shape["type"]; coords=shape["coordinates"]
            nodes=parent.findall(".//*[@data-native-geometry]")
            if kind=="Point":
                assert len(nodes)==1 and [float(nodes[0].get(k)) for k in ("cx","cy")]==coords
            else:
                lines=[coords] if kind=="LineString" else coords
                assert len(lines)==len(nodes)
                for line,node in zip(lines,nodes):
                    path=" ".join(("M" if i==0 else "L")+f"{x} {y}" for i,(x,y) in enumerate(line))
                    assert node.get("d")==path+(" Z" if kind=="Polygon" else "")
                    if kind=="Polygon": assert node.get("stroke")=="none"
            assert parent.get("href")==BASE+PAGE+"#feature-"+f["id"]
            if f["id"].startswith("geo-modern-"): assert parent.get("display")=="none"
    literary=ET.fromstring(get("city-atlas/literary.svg"))
    actual={n.get("data-target-id"):json.loads(n.get("data-members")) for n in literary.iter() if n.get("data-target-id")}
    assert len(actual)==179 and actual==d["targets"]
    for name in ("city","core","relations","literary"):
        body=get("city-atlas/"+name+".svg").decode().strip()
        assert body.replace(BASE+PAGE+"#","#") in raw.decode()
        for link in ET.fromstring(body).iter(NS+"a"):
            assert urlsplit(link.get("href")).fragment in ids
    assert get("city-atlas/qian.svg")==get("backbone-469/frame-qian2018.svg")
    listed=list(csv.DictReader(io.StringIO(get("city-atlas/coverage.csv").decode("utf-8-sig"))))
    assert [r["id"] for r in listed]==list(entities)
    for r in listed:
        e=entities[r["id"]]
        for key in ("period","level","name","placement","next_evidence"):assert r[key]==e[key]
        for key in ("feature_ids","context_features","evidence","literal_targets"):assert json.loads(r[key])==e[key]
    basis=list(csv.DictReader(io.StringIO(get("city-atlas/basis.csv").decode("utf-8-sig"))))
    required=[f["id"] for f in d["features"]]+[r["id"] for k in ("waters","roads","terrain","gaps") for r in d[k]]+[d["qian_frame"]["id"]]
    assert [r["id"] for r in basis]==required
    with zipfile.ZipFile(io.BytesIO(get(study["bundle"]))) as z:
        members=z.namelist()
        assert sorted(members)==sorted(["index.html",study["manifest"],*study["files_sha256"]])
        for name in members:
            if name!="index.html":assert z.read(name)==get(name)
        offline=Links(z.read("index.html"))
        for url in offline.links:
            parts=urlsplit(url)
            if not parts.scheme and parts.path: assert parts.path.removeprefix("./") in members,url
            elif not parts.scheme and parts.fragment: assert parts.fragment.split("?")[0] in ids,url
    fixture=json.loads((ROOT/"tests/fixtures/r4-predecessor.json").read_bytes())
    protected=predecessors(info,get,fixture)
    return {"status":"passed","source_commit":study["source_commit"],"counts":counts,"downloads":len(doc.downloads),
            "basis_rows":len(basis),"archive_members":len(members),"coverage_rows":len(listed),
            "distinct_resources":get.cache_info().misses,"preservation":protected}
