"""Verify the published views, their primary inputs, downloads and predecessor pages."""
import io
import json
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from city_panorama_r5_contract import ATLAS, HOME, KEY, before_r5, digest
from city_panorama_r5_page import BUNDLE, FILES, FOLDER, MANIFEST, PAGE
from city_panorama_r5_scene import CAMERAS, MODELS, project, svg
from verify_city_west_p472 import Links

ARCH="research/prosperity-v4/city-distribution-p451.json"
ROOT=Path(__file__).resolve().parents[1]
NS="{http://www.w3.org/2000/svg}"


class Resources(HTMLParser):
    def __init__(self,blob):
        super().__init__(); self.urls=[]; self.feed(blob.decode())

    def handle_starttag(self,tag,attributes):
        a=dict(attributes)
        for key in ("href","src","srcset"):
            if key in a:self.urls.append(a[key])


def verify(info,reader):
    get=lru_cache(maxsize=None)(reader)
    meta=info[KEY];sums=info["files_sha256"]; release=json.loads(get("release.json"))
    assert meta==json.loads(get(MANIFEST)) and meta["source_commit"]==info["source_commit"]
    assert meta["version"]==release[KEY+"_version"] and meta["version"] in release["extensions"]
    assert meta["download_files"]==list(FILES)
    for p,h in meta["files_sha256"].items():assert digest(get(p))==h==sums[p],p
    for p in (PAGE,MANIFEST,BUNDLE,HOME,ATLAS):assert digest(get(p))==sums[p],p
    for p in [HOME,ATLAS]:before_r5(info,p,get(p))
    hero=json.loads(get("homepage/approval-v9.json"))["hero"]
    assert hero["revision"]=="panorama-approved-v9"
    for p,h in [(hero["asset"],"6465657667ba740d3fc99cde2495a864d3a8a446e2086c25984c0c547eed5825"),
                (hero["small_asset"],"98459529d0a2d8210aaf2728b0c1673ca38b46df2f7b761c9064f1c21fe053b6")]:
        assert digest(get(p))==sums[p]==h
    scene=json.loads(get(FOLDER+"/scene.json"));atlas=json.loads(get(scene["source_atlas"]))
    assert digest(get(scene["source_atlas"]))==scene["source_atlas_sha256"]==sums[scene["source_atlas"]]
    arch=(ROOT/ARCH).read_bytes();assert digest(arch)==scene["architecture_sha256"]
    original={r["id"]:r for r in json.loads(arch)["anchored_buildings"]}
    assert set(original)=={m["id"] for m in scene["models"]}=={"C01","C02","C03","C04"}
    expected={f["id"]:f for f in atlas["features"] if not f["id"].startswith("geo-modern-")}
    assert len(scene["features"])==len(expected)==meta["feature_count"]==28
    for f in scene["features"]:assert all(expected[f["id"]][k]==v for k,v in f.items())
    assert set(scene["excluded_modern_features"])=={"geo-modern-mang-hill-label","geo-modern-luo-river"}
    assert not scene["new_historical_coordinates"] and scene["elevation_ground_m"] is None
    assert scene["accepted_jianchun_control_pairs"]==atlas["jianchun"]["research_accounting"]["accepted_control_pairs"]==0
    assert scene["r4_location_counts"]==atlas["counts"]["levels"]
    assert scene["cameras"]==CAMERAS
    for m in scene["models"]:
        assert all(m[k]==v for k,v in original[m["id"]].items())
        assert m["graphic_model"]==MODELS[m["feature_id"]] and m["measured_elevation_m"] is None
        x,y=m["source_pdf_point"];assert [x,y]==expected[m["feature_id"]]["source_pdf_geometry"]["coordinates"]
        for key,c in CAMERAS.items():assert m["projected_ground_px"][key]==[round(v,4) for v in project(x,y,0,c)]
    image=scene["image"];assert not image["homepage_replacement_approved"]
    for p,key in [("panorama.webp","published_full_sha256"),("panorama-small.webp","published_small_sha256")]:
        raw=get(FOLDER+"/"+p);assert raw[:4]==b"RIFF" and raw[8:12]==b"WEBP" and digest(raw)==image[key]
    for v in CAMERAS:
        raw=get(FOLDER+"/"+v+".svg"); assert raw==svg(scene,v).encode()
        tree=ET.fromstring(raw);assert {a.get("data-feature") for a in tree.iter(NS+"a") if a.get("data-feature")}==set(expected)
        assert {a.get("data-label") for a in tree.iter(NS+"a") if a.get("data-label")}==set(original)
        area=tree.find(".//*[@data-feature='geo-palace-layout-envelope']/"+NS+"polygon")
        assert area is not None and area.get("stroke")=="none"
    page=get(PAGE);doc=Links(page)
    assert doc.downloads==list(FILES) and len(doc.ids)==len(set(doc.ids))
    assert set(original)|{"art","core","city","show-anchors"}<=set(doc.ids)
    for p in Resources(page).urls:
        u=urlsplit(p)
        if u.scheme:continue
        if u.path and u.path!="./":assert u.path.removeprefix("./") in sums,p
        if not u.path and u.fragment:assert u.fragment in doc.ids,p
    with ZipFile(io.BytesIO(get(BUNDLE))) as z:
        members=z.namelist()
        assert sorted(members)==sorted(["index.html",MANIFEST,*meta["files_sha256"]])
        for p in members:
            if p!="index.html":assert z.read(p)==get(p),p
        for url in Resources(z.read("index.html")).urls:
            u=urlsplit(url)
            if not u.scheme and u.path:assert u.path.removeprefix("./") in members,url
    return dict(status="passed",source_commit=info["source_commit"],source_features=len(expected),models=len(original),
                views=3,download_count=len(FILES),offline_members=len(members),distinct_resources=get.cache_info().misses,
                protected_prior_pages=2,approved_homepage_images=2)
