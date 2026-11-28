"""Publish the V6 pagoda study and the independently reviewed V15 homepage edit.

This final, reversible layer archives the exact prior publication context. The
historical V12–V14 checks still validate their own bytes; this module separately
checks the actual current homepage, study, sources and downloadable assets.
"""
import argparse
import copy
import hashlib
import io
import json
import re
import shutil
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
KEY = "homepage_yongning_v15"
VERSION = "homepage-yongning-v15"
REVISION = "panorama-yongning-v15"
PAGE = "luoyang-yongning-v6.html"
FOLDER = "yongning-v6"
META = "homepage/approval-v15.json"
ARCHIVE = "homepage/v15/archive/"
RESEARCH = ROOT / "research/yongning-structure-colour-v6-20261128"
ART = ROOT / "research/homepage-yongning-v15-20261128"
PAGES = ("index.html", "v3.0-dual.html")
MUTABLE = {*PAGES, "release.json"}
PREVIOUS_INFO = ARCHIVE + "build-info.json"
PREVIOUS_RELEASE = ARCHIVE + "release.json"
NAV = '<a id="nav-yongning-v6" href="./luoyang-yongning-v6.html">永宁寺专题</a>'.encode()
CAPTION_OLD = "北魏洛阳 · 研究性复原示意 · 全幅取景版".encode()
CAPTION_NEW = ('北魏洛阳 · 研究性复原示意 · 永宁寺塔依V6方案修订 · '
               '<a href="./luoyang-yongning-v6.html">查看高度、结构与色彩依据 ↗</a>').encode()
MILESTONE = "永宁寺 V6 高度、结构与色彩专题 · 首页塔形修订 V15"
AUTHORIZATION = "好的 这张图作为一个专题放入首页，然后根据这张图improve 首页大图"
SCENE_FILES = ("draw_tower_scene.py", "tower-layer.svg", "tower-projection.json", "render_scene.mjs",
               "homepage-scene.svg", "courtyard-background.png", "generation-attempts.json")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record():
    return json.loads((ART / "image-record.json").read_bytes())


def feature():
    return (ROOT / "web/homepage-yongning-v15.html").read_bytes()


def style_asset():
    checksum = digest((ROOT / "web/homepage-yongning-v15.css").read_bytes())
    return "_assets/" + checksum[:20] + "-homepage-yongning-v15.css"


def style_tag():
    return f'<link rel="stylesheet" href="./{style_asset()}" data-homepage-layout="yongning-v15">'.encode()


def replace_once(raw, old, new):
    assert raw.count(old) == 1, ("Expected one exact homepage edit anchor", old[:100])
    return raw.replace(old, new, 1)


def hero_changes(hero):
    from homepage_artwork_v10 import V12
    return (
        (f'data-hero-revision="{V12.revision}"'.encode(), f'data-hero-revision="{REVISION}"'.encode()),
        (f'src="./{V12.full}" width="1672" height="941"'.encode(),
         f'src="./{hero["asset"]}" width="{hero["width"]}" height="{hero["height"]}"'.encode()),
        (f'srcset="./{V12.small}"'.encode(), f'srcset="./{hero["small_asset"]}"'.encode()),
        (f'alt="{V12.alt}"'.encode(), f'alt="{hero["alt"]}"'.encode()),
        (CAPTION_OLD, CAPTION_NEW),
    )


def add_home(raw, hero):
    assert b'id="home-yongning"' not in raw
    for before, after in hero_changes(hero):
        raw = replace_once(raw, before, after)
    raw = replace_once(raw, b'</head>', style_tag() + b'</head>')
    anchor = b'  <section id="home-questions"'
    raw = replace_once(raw, anchor, feature() + anchor)
    nav_anchor = b'<a href="#map" data-home-nav="map"'
    return replace_once(raw, nav_anchor, NAV + nav_anchor)


def restore_home(raw):
    markers = (b'data-hero-revision="' + REVISION.encode() + b'"', b'id="home-yongning"', b'id="nav-yongning-v6"')
    if not any(marker in raw for marker in markers):
        return raw
    assert all(raw.count(marker) == 1 for marker in markers), "Incomplete V15 homepage layer"
    raw = replace_once(raw, feature(), b'')
    raw = replace_once(raw, NAV, b'')
    raw = replace_once(raw, style_tag(), b'')
    for before, after in reversed(hero_changes(record()["hero"])):
        raw = replace_once(raw, after, before)
    return raw


def current_release(previous):
    result = copy.deepcopy(previous)
    result["extensions"] = sorted(set(result["extensions"]) | {VERSION, "yongning-tower-v6"})
    result.update(homepage_hero_revision=REVISION, homepage_hero_status="approved",
                  homepage_hero_approval_date="2026-11-28", homepage_current_metadata=META,
                  yongning_tower_study_version="V6", yongning_tower_study=PAGE,
                  current_milestone=MILESTONE)
    return result


def restore_v14_context(info, reader):
    """Validate the real V15 layer before exposing the exact V14 predecessor."""
    if KEY not in info:
        return info, reader
    get = lru_cache(maxsize=None)(reader)
    meta, hashes = info[KEY], info["files_sha256"]
    assert meta == json.loads(get(META))
    assert digest(get(META)) == hashes[META]
    assert meta["version"] == VERSION and meta["hero_revision"] == REVISION
    assert meta["source_commit"] == info["source_commit"]
    assert meta["previous_release"] == PREVIOUS_RELEASE
    assert meta["previous_build_info"] == PREVIOUS_INFO
    assert meta["metadata"] == META and meta["study_page"] == PAGE
    assert meta["previous_revision"] == "panorama-approved-v12"
    assert meta["previous_metadata"] == "homepage/approval-v12.json"
    previous_raw = get(PREVIOUS_INFO)
    assert digest(previous_raw) == meta["previous_build_info_sha256"] == hashes[PREVIOUS_INFO]
    old = json.loads(previous_raw)
    assert KEY not in old and old["source_commit"] == info["source_commit"]
    for path, expected in meta["files_sha256"].items():
        assert digest(get(path)) == hashes[path] == expected, (path, "V15 bytes differ")
    expected_paths = set(old["files_sha256"]) | set(meta["files_sha256"]) | {META}
    assert set(hashes) == expected_paths, "V15 inventory changed outside its scope"
    assert set(meta["files_sha256"]) == set(hashes) - set(old["files_sha256"]) - {META}
    assert meta["homepage_stylesheet"] == style_asset()
    asset_paths = {meta["hero"]["asset"], meta["hero"]["small_asset"], meta["homepage_stylesheet"]}
    assert all(p.startswith((FOLDER + "/", ARCHIVE)) or p == PAGE or p in asset_paths for p in meta["files_sha256"])
    protected = set(old["files_sha256"]) - MUTABLE
    assert len(protected) == meta["protected_public_file_count"]
    assert all(hashes[path] == old["files_sha256"][path] for path in protected), "Earlier resource hash changed"
    overrides = {"build-info.json": previous_raw, "release.json": get(PREVIOUS_RELEASE)}
    for page in PAGES:
        before, after = get(ARCHIVE + page), get(page)
        assert digest(before) == old["files_sha256"][page] == meta["homepage_before_sha256"][page]
        assert digest(after) == hashes[page] == meta["homepage_after_sha256"][page]
        assert restore_home(after) == before, "V15 homepage edits are not exactly reversible"
        overrides[page] = before
    assert digest(overrides["release.json"]) == old["files_sha256"]["release.json"]
    assert digest(get("release.json")) == hashes["release.json"], "Current release bytes differ from the public inventory"
    assert json.loads(get("release.json")) == current_release(json.loads(overrides["release.json"]))
    expected_info = copy.deepcopy(old)
    expected_info[KEY] = meta
    expected_info["files_sha256"] = hashes
    assert info == expected_info, "Unrelated build metadata changed"

    def read(path):
        return overrides[path] if path in overrides else get(path)

    return old, read


def verify(info, reader):
    from PIL import Image
    from city_nodes_r7_verify import Document, verify_links
    get = lru_cache(maxsize=None)(reader)
    assert KEY in info, "Current homepage and V6 study are missing"
    old, prior = restore_v14_context(info, get)
    meta, hashes = info[KEY], info["files_sha256"]
    for path, expected in old["files_sha256"].items():
        if path not in MUTABLE and path != ".nojekyll":
            assert digest(get(path)) == expected, (path, "Protected public bytes changed")
    hero = meta["hero"]
    assert meta["authorization_quote"] == AUTHORIZATION
    assert meta["research_source_commit"] == "d6e1754fa5b9dd6f3bb79ac3d152ccb6e104eac0"
    assert meta["structural_feasibility"] == "not_established"
    assert meta["new_ancient_coordinates"] == 0 and meta["historical_ground_truth_upgraded"] is False
    assert hero == record()["hero"] and hero["revision"] == REVISION
    assert hero["based_on_revision"] == "panorama-approved-v12"
    assert hero["status"] == "approved" and hero["approval_date"] == "2026-11-28"
    art = record()
    assert get(FOLDER + "/homepage-image-record.json") == (ART / "image-record.json").read_bytes()
    assert hero["source_sha256"] == digest(get(FOLDER + "/homepage/homepage-scene.svg"))
    for name in SCENE_FILES:
        raw = get(FOLDER + "/homepage/" + name)
        assert raw == (ART / name).read_bytes(), (name, "Native scene differs from reviewed source")
        assert digest(raw) == art["scene_files_sha256"][name]
    projection = json.loads(get(FOLDER + "/homepage/tower-projection.json"))
    tower = ET.fromstring(get(FOLDER + "/homepage/tower-layer.svg"))
    counts = {kind: len(tower.findall('.//{http://www.w3.org/2000/svg}g[@data-kind="' + kind + '"]'))
              for kind in ("wall-storey", "main-roof", "external-balcony", "gold-disc")}
    assert counts == projection["exact_group_counts"] == {
        "wall-storey": 9, "main-roof": 9, "external-balcony": 8, "gold-disc": 11}
    assert not tower.findall('.//{http://www.w3.org/2000/svg}image')
    assert projection["svg_sha256"] == digest(get(FOLDER + "/homepage/tower-layer.svg"))
    assert projection["script_sha256"] == digest(get(FOLDER + "/homepage/draw_tower_scene.py"))
    assert projection["source_parameters_sha256"] == digest(get(FOLDER + "/design-parameters.json"))
    assert projection["source_height_algorithm_sha256"] == digest(get(FOLDER + "/draw_scaled_elevation.py"))
    display = projection["display_projection"]
    assert display["front_plinth_ground_midpoint_screen_px"] == [516.0, 403.0]
    assert display["apex_screen_px"] == [517.91, 203.878]
    assert display["original_r12_frozen_H_used"] is False
    assert display["source_ground_homography_modified"] is False
    assert display["not_registration_to_archaeology_or_historic_camera"] is True
    for path_key, sha_key, width_key, height_key in (("asset", "asset_sha256", "width", "height"),
                                                   ("small_asset", "small_asset_sha256", "small_width", "small_height")):
        raw = get(hero[path_key])
        assert digest(raw) == hashes[hero[path_key]] == hero[sha_key]
        with Image.open(io.BytesIO(raw)) as image:
            assert image.format == "WEBP" and image.size == (hero[width_key], hero[height_key])
    assert digest(get(FOLDER + "/yongning-v6-scaled-elevation.png")) == "b8825ca58939751a2ec411ab86cd63ea6eaaad41b6dac7ceb98a32f37a4a0d30"
    assert digest(get(FOLDER + "/mechanics-results.json")) == "4823f8739e8d7af032dbe92933c2e33f620b2352e11ede5eeddc3d1d1ffbf2b6"
    for path in RESEARCH.iterdir():
        if path.is_file():
            assert get(FOLDER + "/" + path.name) == path.read_bytes(), path.name
    topic = verify_links(get(PAGE), hashes, current=PAGE)
    assert get(PAGE) == (ROOT / "web/yongning-v6.html").read_bytes(), "Study content differs from reviewed source"
    assert get(FOLDER + "/topic.css") == (ROOT / "web/yongning-v6.css").read_bytes(), "Study presentation differs from reviewed source"
    assert get(FOLDER + "/homepage.css") == (ROOT / "web/homepage-yongning-v15.css").read_bytes(), "Homepage presentation differs from reviewed source"
    assert get(meta["homepage_stylesheet"]) == get(FOLDER + "/homepage.css"), "Fingerprinted homepage stylesheet differs"
    assert len(topic.ids) == len(set(topic.ids))
    assert {"height", "colour", "mechanics", "sources", "v6-elevation", "research-verdict"} <= set(topic.ids)
    for link in topic.links:
        url = urlsplit(link)
        if not url.scheme and url.path and url.fragment:
            target = url.path.removeprefix("./")
            if target in ("", "index.html", "v3.0-dual.html") and url.fragment in ("map", "home"):
                continue  # Existing SPA routes are exercised in the browser gate.
            assert url.fragment in Document(get(target)).ids, link
    raw = get(PAGE).decode()
    assert "整体结构可行性尚未确立，不能据此认定安全可建。" in raw and "133.77" in raw and "147" in raw
    assert "1/200" in raw and "131.8" in raw and "朱" in raw
    for page in PAGES:
        doc = Document(get(page))
        assert len(doc.ids) == len(set(doc.ids))
        assert {"home-yongning", "home-yongning-entry", "nav-yongning-v6", "home-hero", "home-questions", "map-viewport"} <= set(doc.ids)
        assert get(page).count(feature()) == 1
    return dict(status="passed", source_commit=info["source_commit"], hero_revision=REVISION,
                study_page=PAGE, study_elevation_sha256=hashes[FOLDER + "/yongning-v6-scaled-elevation.png"],
                new_assets=len(meta["files_sha256"]), protected_public_files=meta["protected_public_file_count"],
                reversible_homepages=2, structural_feasibility="not_established", downloads=len(topic.downloads))


def publish(site=SITE):
    info_raw = (site / "build-info.json").read_bytes()
    info = json.loads(info_raw)
    assert KEY not in info, "Build the predecessor first; V15 must run once at the end"
    old_hashes = dict(info["files_sha256"])
    assert all(digest((site / p).read_bytes()) == checksum for p, checksum in old_hashes.items()), "Predecessor contains changed bytes"
    art = record()
    hero = art["hero"]
    assert art["visual_review"]["accepted_for_publication"] is True
    for path in ["build-info.json", "release.json", *PAGES]:
        destination = site / ARCHIVE / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(site / path, destination)
    for path in RESEARCH.iterdir():
        if path.is_file():
            target = site / FOLDER / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    copies = [(ROOT / "web/yongning-v6.html", PAGE), (ROOT / "web/yongning-v6.css", FOLDER + "/topic.css"),
              (ROOT / "web/homepage-yongning-v15.css", FOLDER + "/homepage.css"),
              (ROOT / "web/homepage-yongning-v15.css", style_asset()),
              (ART / "image-record.json", FOLDER + "/homepage-image-record.json"),
              (ART / "generation-prompts.txt", FOLDER + "/homepage-generation-prompts.txt"),
              (ART / "visual-review.md", FOLDER + "/homepage-visual-review.md")]
    copies.extend((ART / name, FOLDER + "/homepage/" + name) for name in SCENE_FILES)
    for path_key, source_key, checksum_key in (("asset", "full_source", "asset_sha256"), ("small_asset", "small_source", "small_asset_sha256")):
        source = ROOT / art[source_key]
        assert digest(source.read_bytes()) == hero[checksum_key]
        copies.append((source, hero[path_key]))
    for source, relative in copies:
        destination = site / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    before, after = {}, {}
    for page in PAGES:
        raw = (site / page).read_bytes()
        before[page] = digest(raw)
        changed = add_home(raw, hero)
        (site / page).write_bytes(changed)
        after[page] = digest(changed)
    release = current_release(json.loads((site / "release.json").read_bytes()))
    dump(site / "release.json", release)
    hashes = {str(p.relative_to(site)): digest(p.read_bytes()) for p in sorted(site.rglob("*")) if p.is_file() and p != site / "build-info.json"}
    protected = set(old_hashes) - MUTABLE
    assert all(hashes[p] == old_hashes[p] for p in protected), "V15 touched a protected resource"
    added = set(hashes) - set(old_hashes)
    assert META not in added
    meta = dict(version=VERSION, research_version="V6", hero_revision=REVISION, hero=hero, metadata=META,
                source_commit=info["source_commit"], research_source_commit="d6e1754fa5b9dd6f3bb79ac3d152ccb6e104eac0",
                study_page=PAGE, homepage_stylesheet=style_asset(), authorization_date="2026-11-28", authorization_quote=AUTHORIZATION,
                scope="homepage_tower_edit_and_research_feature", structural_feasibility="not_established",
                new_ancient_coordinates=0, historical_ground_truth_upgraded=False,
                previous_revision="panorama-approved-v12", previous_metadata="homepage/approval-v12.json",
                previous_release=PREVIOUS_RELEASE, previous_build_info=PREVIOUS_INFO,
                previous_build_info_sha256=digest(info_raw), protected_public_file_count=len(protected),
                homepage_before_sha256=before, homepage_after_sha256=after,
                files_sha256={p: hashes[p] for p in sorted(added)})
    dump(site / META, meta)
    hashes[META] = digest((site / META).read_bytes())
    info[KEY] = meta
    info["files_sha256"] = hashes
    dump(site / "build-info.json", info)
    result = verify(info, lambda path: (site / path).read_bytes())
    dump(ROOT / "artifacts/homepage-yongning-v15-verify.json", result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify(json.loads((SITE / "build-info.json").read_bytes()), lambda path: (SITE / path).read_bytes()), ensure_ascii=False))
    else:
        publish()
