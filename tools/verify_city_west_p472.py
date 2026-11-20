"""Check P472 outputs and the chain of P470/P471 preservation fingerprints."""
import copy
import csv
import hashlib
import io
import json
import zipfile
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
PAGE = "prosperity-city-west.html"
COMMON, NORTH = "prosperity-city-common.html", "prosperity-city-north.html"
C_MAN, N_MAN = "common-470/bundle-manifest.json", "north-471/bundle-manifest.json"
C_ZIP, N_ZIP = "downloads/common-470.zip", "downloads/north-471.zip"
FOLDER = "west-472/"
MANIFEST, BUNDLE = FOLDER+"bundle-manifest.json", "downloads/west-472.zip"
ASSETS = {FOLDER+n for n in ("west-source.svg","west-relations.svg","readings.json","evidence.csv","crosswalk.json","study.css","west-ui.js")}
DOWNLOADS = ASSETS - {FOLDER+"study.css", FOLDER+"west-ui.js"} | {MANIFEST, BUNDLE}
NS = "{http://www.w3.org/2000/svg}"


def digest(content):
    return hashlib.sha256(content).hexdigest()


class Links(HTMLParser):
    def __init__(self, raw):
        super().__init__()
        self.ids, self.links, self.downloads = [], [], []
        self.feed(raw.decode())

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        for key in ("href","src"):
            if key in a:
                self.links.append(a[key])
        if "download" in a:
            self.downloads.append(a["href"].removeprefix("./"))


def json_bytes(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2)+"\n").encode()


def restore_commit(content, current, baseline):
    assert current.encode() in content, "Expected an explicit page publication reference"
    return content.replace(current.encode(),baseline.encode()).replace(current[:12].encode(),baseline[:12].encode())


def check_preservation(info, get, baseline):
    """Reconstruct each accepted predecessor digest from its allowed substitutions."""
    old, live = baseline["source_commit"], info["source_commit"]
    old_hash = baseline["pages_and_derived_files"]
    current_hash = info["files_sha256"]
    for path, expected in baseline["stable"].items():
        assert digest(get(path)) == current_hash[path] == expected, path

    west = info["prosperity_city_west_p472"]["preservation"]
    north = info["prosperity_city_north_p471"]["preservation"]
    assert west["previous_page"] == NORTH and west["entry_id"] == "p472-entry"
    west_entry = west["entry_html"].encode()
    north_html = get(NORTH)
    assert north_html.count(west_entry) == north_html.count(b'id="p472-entry"') == 1
    assert 'href="./prosperity-city-west.html"' in west["entry_html"]
    stripped = north_html.replace(west_entry, b"")
    assert digest(stripped) == west["previous_page_sha256"]
    assert digest(restore_commit(stripped, live, old)) == old_hash[NORTH]
    common_html = get(COMMON)
    assert digest(restore_commit(common_html, live, old)) == old_hash[COMMON]
    north_entry = north["entry_html"].encode()
    assert common_html.count(north_entry) == common_html.count(b'id="p471-entry"') == 1
    underlying = common_html.replace(north_entry,b"")
    assert digest(underlying) == north["previous_page_sha256"]
    assert digest(restore_commit(underlying,live,old)) == baseline["north_previous_page_sha256"]

    assert set(west["protected_files_sha256"]) == set(baseline["stable"]) | {C_MAN, C_ZIP, N_MAN, N_ZIP, COMMON}
    for path, expected in west["protected_files_sha256"].items():
        assert digest(get(path)) == current_hash[path] == expected, path
    for key, manifest, bundle in (("prosperity_city_common_p470", C_MAN,C_ZIP),
                                  ("prosperity_city_north_p471", N_MAN,N_ZIP)):
        raw_manifest = get(manifest)
        m = json.loads(raw_manifest)
        assert m["source_commit"] == live and m["preservation"] == info[key]["preservation"]
        restored = copy.deepcopy(m)
        restored["source_commit"] = old
        if manifest == N_MAN:
            pres = restored["preservation"]
            assert pres["previous_page"] == COMMON and pres["previous_page_sha256"] == digest(underlying)
            pres["previous_page_sha256"] = baseline["north_previous_page_sha256"]
            for path in (C_MAN,C_ZIP):
                assert pres["protected_files_sha256"][path] == digest(get(path)) == current_hash[path]
                pres["protected_files_sha256"][path] = old_hash[path]
        assert digest(json_bytes(restored)) == old_hash[manifest], manifest
        with zipfile.ZipFile(io.BytesIO(get(bundle))) as z:
            previous = baseline["offline_members"][bundle]
            assert len(z.namelist()) == len(previous) and set(z.namelist()) == set(previous)
            for name, expected in previous.items():
                raw = z.read(name)
                if name == "index.html":
                    actual = digest(restore_commit(raw,live,old))
                elif name == manifest:
                    assert raw == raw_manifest
                    actual = digest(json_bytes(restored))
                else:
                    assert raw == get(name)
                    actual = digest(raw)
                assert actual == expected, (bundle,name)
    return {"frozen_files":len(baseline["stable"]), "protected_in_build":len(west["protected_files_sha256"]),
            "previous_offline_members":sum(map(len,baseline["offline_members"].values())),
            "previous_pages":2, "previous_manifests":2, "previous_bundles":2}


def verify(info, read_bytes):
    get = lru_cache(maxsize=None)(read_bytes)
    meta = info["prosperity_city_west_p472"]
    raw_page = get(PAGE)
    links = Links(raw_page)
    assert len(set(links.ids)) == len(links.ids)
    assert len(links.downloads) == 7 and set(links.downloads) == set(meta["download_files"]) == DOWNLOADS
    manifest = json.loads(get(MANIFEST))
    assert manifest["source_commit"] == meta["source_commit"] == info["source_commit"]
    assert manifest == meta | {"files_sha256":manifest["files_sha256"]} and set(manifest["files_sha256"]) == ASSETS
    release = json.loads(get("release.json"))
    assert release["prosperity_city_west_p472_version"] == meta["version"] == "prosperity-city-west-p472"
    assert meta["version"] in release["extensions"]
    for path in ASSETS | {PAGE, BUNDLE, MANIFEST}:
        assert digest(get(path)) == info["files_sha256"][path], path
    for path, expected in manifest["files_sha256"].items():
        assert digest(get(path)) == expected, path
    data = json.loads(get(FOLDER+"readings.json"))
    assert data["counts"] == meta["counts"]
    assert data["counts"] == {"records":24, "entities":22, "bound":3, "unlocated":19, "source_features":14,
                              "original_constraint_entries":24, "electronic_matches":24, "manual_context_reviews":0,
                              "new_historical_coordinates":0, "new_measurements":0, "new_footprints":0}
    expected = [f"WR{i:02d}" for i in range(1,25)]
    assert [r["id"] for r in data["records"]] == expected
    assert sorted(k for g in data["groups"] for k in g["evidence_ids"]) == expected
    assert data["source_crs"] == "EPSG:4610" and data["new_geographic_transform"] is None
    assert data["source_inputs_sha256"] == meta["source_inputs_sha256"]
    for path, checksum in data["source_inputs_sha256"].items():
        assert digest((ROOT/path).read_bytes()) == checksum, path
    csv_rows = list(csv.DictReader(io.StringIO(get(FOLDER+"evidence.csv").decode("utf-8-sig"))))
    assert [r["id"] for r in csv_rows] == expected
    decisions = json.loads(get(FOLDER+"crosswalk.json"))["records"]
    assert len(decisions) == 24
    bindings = {e["id"]:e["feature_id"] for e in data["entities"]}
    assert len(bindings) == 22 and {e:f for e,f in bindings.items() if f} == {
        "ic_changhe_palace":"geo-changhe-palace-gate", "gate_ximing":"geo-ximing-gate", "gate_xiyang":"geo-xiyang-gate"}
    for r, c, decision in zip(data["records"],csv_rows,decisions,strict=True):
        b, p = r["b5"], r["p1"]
        assert r["working_reading"] == decision and c["map_reading"] == decision["map_reading"]
        assert b["id"] == r["id"] == c["id"] and p["key"] == c["p1_key"] == "B5:"+r["id"]
        assert b["quote"] == p["legacy_quote"] == c["quote"] and c["reading"] == b["reading"]
        assert p["manual_context_review"] is p["geographic_coordinates"] is b["geographic_coordinates"] is None
        assert p["electronic_text_checked"] and p["legacy_quote_passed_normalized_sequence_check"]
        assert c["geographic_coordinates"] == c["manual_context_review"] == ""
        assert json.loads(c["source_bindings"]) == {e:bindings[e] for e in b["entities"]}
        assert json.loads(c["variants"]) == b["variants"] and json.loads(c["source_checks"]) == p["source_checks"]
        assert c["limit"] == b["limit"] and c["period"] == decision["period_label"]
    assert set(expected).issubset(links.ids)
    assert all("entity-"+e in links.ids for e in bindings)
    checked = json.loads((ROOT/"research/prosperity-v1/geographic-evidence.json").read_bytes())
    originals = {f["id"]:f for f in checked["features"]}
    assert all(f == originals[f["id"]] for f in data["features"])
    source = ET.fromstring(get(FOLDER+"west-source.svg"))
    relations = ET.fromstring(get(FOLDER+"west-relations.svg"))
    assert {n.get("data-feature") for n in source.findall(".//*[@data-feature]")} == {f["id"] for f in data["features"]}
    assert not relations.findall(".//*[@data-feature]") and not relations.findall(".//*[@data-point]")
    for f in data["features"]:
        geom = f["source_pdf_geometry"]
        if geom["type"] == "Point":
            point, = source.findall(f'.//*[@data-point="{f["id"]}"]')
            assert [float(point.get(k)) for k in ("cx","cy")] == geom["coordinates"]
            assert f["approximation"]["working_display_tolerance_m"] == 100
            assert f["approximation"]["absolute_ground_accuracy_m"] is None and not f["approximation"]["is_field_verified_gcp"]
        else:
            lines = source.findall(f'.//*[@data-source-feature-id="{f["id"]}"]')
            assert len(lines) == len(geom["coordinates"])
            for line, coords in zip(lines,geom["coordinates"],strict=True):
                expected_path = " ".join(("M" if i==0 else "L")+f"{x} {y}" for i,(x,y) in enumerate(coords))
                assert line.get("d") == expected_path
    assert all(a.get("href").startswith("https://mechgouki.github.io/luoyang-city/"+PAGE+"#")
               and urlsplit(a.get("href")).fragment in links.ids for svg in (source,relations) for a in svg.iter(NS+"a"))
    with zipfile.ZipFile(io.BytesIO(get(BUNDLE))) as z:
        assert len(z.namelist()) == 9 and set(z.namelist()) == ASSETS | {MANIFEST,"index.html"}
        for name in ASSETS | {MANIFEST}:
            assert z.read(name) == get(name),name
        offline = Links(z.read("index.html"))
        for url in offline.links:
            parsed = urlsplit(url)
            if not parsed.scheme and not parsed.netloc:
                if parsed.path:
                    assert parsed.path.removeprefix("./") in z.namelist(),url
                else:
                    assert parsed.fragment in offline.ids,url
    baseline = json.loads((ROOT/"tests/fixtures/p471-published-hashes.json").read_bytes())
    preserved = check_preservation(info,get,baseline)
    return {"status":"passed", "source_commit":info["source_commit"], "distinct_resources":get.cache_info().misses,
            "counts":data["counts"], "downloads":len(DOWNLOADS), "archive_members":9, "preservation":preserved}
