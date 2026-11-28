"""Publish the unchanged V6 study and the current reviewed homepage scene.

The filename and metadata key are stable compatibility entry points introduced
in V15. V16 updates this same final layer rather than stacking a duplicate
publisher. Historical V12–V14 checks still validate their own bytes; the rejected
V15 scene and its technical evidence remain distinct from the current artwork.
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
VERSION = "homepage-yongning-v16"
REVISION = "panorama-yongning-v16"
PAGE = "luoyang-yongning-v6.html"
FOLDER = "yongning-v6"
META = "homepage/approval-v16.json"
ARCHIVE = "homepage/v16/archive/"
RESEARCH = ROOT / "research/yongning-structure-colour-v6-20261128"
LEGACY_ART = ROOT / "research/homepage-yongning-v15-20261128"
ART = ROOT / "research/homepage-yongning-v16-20261128"
SCENE_FOLDER = "homepage/v16"
PAGES = ("index.html", "v3.0-dual.html")
MUTABLE = {*PAGES, "release.json"}
PREVIOUS_INFO = ARCHIVE + "build-info.json"
PREVIOUS_RELEASE = ARCHIVE + "release.json"
NAV = '<a id="nav-yongning-v6" href="./luoyang-yongning-v6.html">永宁寺专题</a>'.encode()
CAPTION_OLD = "北魏洛阳 · 研究性复原示意 · 全幅取景版".encode()
CAPTION_NEW = ('北魏洛阳 · 研究性复原示意 · 永宁寺塔与原图空间环境修订 V16 · '
               '<a href="./luoyang-yongning-v6.html">查看高度、结构与色彩依据 ↗</a>').encode()
MILESTONE = "永宁寺 V6 高度、结构与色彩专题 · 首页空间环境修订 V16"
AUTHORIZATION = "好的 这张图作为一个专题放入首页，然后根据这张图improve 首页大图"
CORRECTION = "首页大图已按这张图调整，这个图不对的 完全没有考虑好原图的空间环境，请修改"
SCENE_FILES = ("draw_tower_scene.py", "tower-layer.svg", "tower-projection.json", "render_scene.mjs",
               "homepage-scene.svg", "courtyard-background.png", "generation-attempts.json")
CURRENT_SCENE_FILES = ("source-scene.png", "homepage-scene.svg", "scene-assembly.json", "render_scene.mjs",
                       "render-audit.json", "scene-background-v12.webp", "temple-edit-candidate-04.png",
                       "generation-prompt.txt", "generation-attempts.json", "visual-review.md")
SPATIAL_CHECKS = ("camera_and_horizon", "plinth_ground_contact", "courtyard_and_neighbours",
                  "scale_and_depth", "roof_perspective", "lighting_and_atmosphere")
V15_SOURCE_COMMIT = "148436edc7707bc4e002d634d6f74b8e3c2ac22c"
V15_WORKFLOW = "https://github.com/mechgouki/luoyang-city/actions/runs/46138856161"
V15_EVIDENCE_COMMIT = "a5e0e67d1a6ac30025611599fbeb6d617ca599f2"
V15_META_SHA256 = "f0e3eeecc4477c7aabb6924d624a16ecf9330e43fc2fb73a0352e99ef91ec7f9"
V15_INFO_SHA256 = "702a428b7651f92fdfc3f345d9fd0c97f33ddc0590d6af9b403f315981b6ad4f"
V15_PUBLIC_FILES = ("homepage/approval-v15.json", "homepage/v15/archive/build-info.json",
                    "homepage/v15/archive/release.json", "homepage/v15/archive/index.html",
                    "homepage/v15/archive/v3.0-dual.html")
V15_SNAPSHOT = "homepage/history/v15/"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record():
    return json.loads((ART / "image-record.json").read_bytes())


def legacy_record():
    return json.loads((LEGACY_ART / "image-record.json").read_bytes())


def legacy_publication_paths():
    paths = {path: path for path in V15_PUBLIC_FILES}
    paths.update({path: V15_SNAPSHOT + path for path in ("build-info.json", "release.json", *PAGES)})
    return paths


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
    assert all(raw.count(marker) == 1 for marker in markers), "Incomplete current homepage layer"
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
                  homepage_hero_approval_scope="implementation_review_under_user_instruction",
                  homepage_user_final_pixels_approved=False,
                  homepage_superseded_revision="panorama-yongning-v15",
                  homepage_superseded_review_status="rejected_by_user",
                  yongning_tower_study_version="V6", yongning_tower_study=PAGE,
                  current_milestone=MILESTONE)
    return result


def restore_v14_context(info, reader):
    """Validate the current layer before exposing the exact V14 predecessor."""
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
        assert digest(get(path)) == hashes[path] == expected, (path, "Current homepage bytes differ")
    expected_paths = set(old["files_sha256"]) | set(meta["files_sha256"]) | {META}
    assert set(hashes) == expected_paths, "Current homepage inventory changed outside its scope"
    assert set(meta["files_sha256"]) == set(hashes) - set(old["files_sha256"]) - {META}
    assert meta["homepage_stylesheet"] == style_asset()
    asset_paths = {meta["hero"]["asset"], meta["hero"]["small_asset"], meta["homepage_stylesheet"]}
    old_hero = legacy_record()["hero"]
    asset_paths.update((old_hero["asset"], old_hero["small_asset"]))
    assert all(p.startswith((FOLDER + "/", ARCHIVE, SCENE_FOLDER + "/")) or p == PAGE or p in asset_paths
               or p in legacy_publication_paths().values() for p in meta["files_sha256"])
    protected = set(old["files_sha256"]) - MUTABLE
    assert len(protected) == meta["protected_public_file_count"]
    assert all(hashes[path] == old["files_sha256"][path] for path in protected), "Earlier resource hash changed"
    overrides = {"build-info.json": previous_raw, "release.json": get(PREVIOUS_RELEASE)}
    for page in PAGES:
        before, after = get(ARCHIVE + page), get(page)
        assert digest(before) == old["files_sha256"][page] == meta["homepage_before_sha256"][page]
        assert digest(after) == hashes[page] == meta["homepage_after_sha256"][page]
        assert restore_home(after) == before, "Current homepage edits are not exactly reversible"
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


def verify_legacy_art(get, hashes):
    """Keep V15's exact construction proof; it is not a claim of visual acceptance."""
    from PIL import Image
    art = legacy_record()
    hero = art["hero"]
    old_info_raw = get(V15_SNAPSHOT + "build-info.json")
    assert digest(old_info_raw) == V15_INFO_SHA256
    old_info = json.loads(old_info_raw)
    assert old_info["source_commit"] == V15_SOURCE_COMMIT
    old_meta_raw = get("homepage/approval-v15.json")
    assert digest(old_meta_raw) == V15_META_SHA256
    old_meta = json.loads(old_meta_raw)
    assert old_info[KEY] == old_meta and old_meta["source_commit"] == V15_SOURCE_COMMIT
    for source, public_path in legacy_publication_paths().items():
        raw = get(public_path)
        assert raw == (LEGACY_ART / "publication" / source).read_bytes(), (source, "Historical publication snapshot changed")
        expected = V15_INFO_SHA256 if source == "build-info.json" else old_info["files_sha256"][source]
        assert digest(raw) == hashes[public_path] == expected
    for path, expected in old_meta["files_sha256"].items():
        assert digest(get(path)) == expected, (path, "V15 addition is no longer available with its original bytes")
    assert hero["revision"] == "panorama-yongning-v15"
    assert get(FOLDER + "/homepage-image-record.json") == (LEGACY_ART / "image-record.json").read_bytes()
    assert hero["source_sha256"] == digest(get(FOLDER + "/homepage/homepage-scene.svg"))
    for name in SCENE_FILES:
        raw = get(FOLDER + "/homepage/" + name)
        assert raw == (LEGACY_ART / name).read_bytes(), (name, "Historical V15 source changed")
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


def verify_current_art(get, hashes):
    """Verify the reviewed scene identity and its explicitly limited visual claims."""
    from PIL import Image, ImageChops
    from homepage_artwork_v10 import V12
    art = record()
    hero = art["hero"]
    assert art["schema"] == "homepage-yongning-v16-image-record-v1"
    assert hero["revision"] == REVISION and hero["based_on_revision"] == "panorama-approved-v12"
    assert hero["source_kind"] == "imagegen_local_edit_native_scene_assembly"
    assert hero["status"] == "approved" and hero["approval_date"] == "2026-11-28"
    assert hero["approval_scope"] == "implementation_review_under_user_instruction"
    assert hero["user_final_pixels_approved"] is False
    assert get(SCENE_FOLDER + "/image-record.json") == (ART / "image-record.json").read_bytes()
    assert set(art["scene_files_sha256"]) == set(CURRENT_SCENE_FILES)
    for name in CURRENT_SCENE_FILES:
        raw = get(SCENE_FOLDER + "/" + name)
        assert raw == (ART / name).read_bytes(), (name, "Current scene differs from reviewed source")
        assert digest(raw) == art["scene_files_sha256"][name]
    source = get(SCENE_FOLDER + "/source-scene.png")
    assert hero["source_sha256"] == digest(source)
    with Image.open(io.BytesIO(source)) as scene:
        assert scene.format == "PNG" and list(scene.size) == art["source_dimensions"]
        scene_rgb = scene.convert("RGB")
    assembly = json.loads(get(SCENE_FOLDER + "/scene-assembly.json"))
    audit = json.loads(get(SCENE_FOLDER + "/render-audit.json"))
    assert assembly["source_kind"] == audit["source_kind"] == hero["source_kind"]
    assert assembly["schema"] == "homepage-yongning-v16-native-scene-assembly-v1"
    assert audit["schema"] == "homepage-yongning-v16-render-audit-v1"
    assert assembly["canvas"] == {"width": 1672, "height": 941}
    assert assembly["historical_camera_calibration"] is False and assembly["city_wide_metric_registration"] is False
    assert assembly["source_ground_homography_modified"] is False and assembly["new_ancient_coordinates"] == 0
    rect = assembly["local_edit"]["rectangle_px"]
    assert rect == {"x": 380, "y": 180, "width": 270, "height": 270}
    assert assembly["local_edit"]["selected_attempt"] == 4
    assert assembly["local_edit"]["new_vector_tower_geometry"] is False
    assert 0 <= assembly["local_edit"]["feather_px"] <= 6
    background = get(SCENE_FOLDER + "/" + assembly["background"]["file"])
    patch = get(SCENE_FOLDER + "/" + assembly["local_edit"]["file"])
    assert background == get(V12.full)
    assert digest(background) == assembly["background"]["sha256"] == audit["background_sha256"]
    assert digest(patch) == assembly["local_edit"]["sha256"] == audit["patch_sha256"]
    assert audit["local_rectangle_px"] == rect and audit["edge_feather_px"] == assembly["local_edit"]["feather_px"]
    assert audit["png_sha256"] == hero["source_sha256"]
    assert audit["full_webp_sha256"] == hero["asset_sha256"] and audit["small_webp_sha256"] == hero["small_asset_sha256"]
    svg_raw = get(SCENE_FOLDER + "/homepage-scene.svg")
    assert audit["svg_sha256"] == digest(svg_raw)
    svg = ET.fromstring(svg_raw)
    assert svg.attrib["width"] == "1672" and svg.attrib["height"] == "941" and svg.attrib["viewBox"] == "0 0 1672 941"
    assert all(node.tag.rsplit("}", 1)[-1] in {"title", "desc", "defs", "image"} for node in svg)
    images = svg.findall(".//{http://www.w3.org/2000/svg}image")
    assert len(images) == 2 and [node.attrib["data-kind"] for node in images] == ["original-v12-background", "imagegen-local-scene"]
    assert images[0].attrib["href"] == "./" + assembly["background"]["file"]
    assert {key: int(images[0].attrib[key]) for key in ("x", "y", "width", "height")} == {"x": 0, "y": 0, "width": 1672, "height": 941}
    assert images[1].attrib["href"] == "./" + assembly["local_edit"]["file"]
    assert {key: int(images[1].attrib[key]) for key in ("x", "y", "width", "height")} == rect
    assert not svg.findall(".//{http://www.w3.org/2000/svg}path") and not svg.findall(".//{http://www.w3.org/2000/svg}polygon")
    assert audit["new_vector_tower_geometry"] is False
    assert audit["outside_rectangle_changed_rgb_pixels"] == audit["outside_rectangle_max_channel_delta"] == 0
    assert audit["outside_rectangle_pixels"] == 1672 * 941 - 270 * 270
    # This is an exact source-PNG comparison; WebP derivatives remain lossy.
    with Image.open(io.BytesIO(background)) as original:
        base_rgb = original.convert("RGB")
    x, y, width, height = (rect[key] for key in ("x", "y", "width", "height"))
    for box in ((0, 0, 1672, y), (0, y + height, 1672, 941),
                (0, y, x, y + height), (x + width, y, 1672, y + height)):
        assert ImageChops.difference(base_rgb.crop(box), scene_rgb.crop(box)).getbbox() is None
    review = art["visual_review"]
    assert review["accepted_for_publication"] is True
    assert review["reviewed_image_sha256"] == hero["source_sha256"]
    assert review["reviewed_webp_sha256"] == {"full": hero["asset_sha256"], "small": hero["small_asset_sha256"]}
    assert review["reference_revision"] == "panorama-approved-v12"
    assert review["scope"] == "visual_scene_consistency_not_archaeological_registration"
    assert set(review["spatial_checks"]) == set(SPATIAL_CHECKS)
    assert all(review["spatial_checks"][key] is True for key in SPATIAL_CHECKS)
    assert art["structural_feasibility"] == "not_established"
    assert art["new_ancient_coordinates"] == 0 and art["historical_ground_truth_upgraded"] is False
    assert art["source_ground_homography_modified"] is False and art["city_wide_metric_registration"] is False
    assert art["surrounding_pixels_claimed_identical"] is False
    assert art["source_png_outside_edit_rectangle_pixels_identical"] is True
    assert art["published_lossy_webp_pixel_identity_claimed"] is False
    previous = art["supersedes"]
    assert previous["revision"] == "panorama-yongning-v15" and previous["visual_status"] == "rejected_by_user"
    assert previous["user_feedback"] == CORRECTION and previous["technical_acceptance_status"] == "passed"
    assert previous["source_commit"] == V15_SOURCE_COMMIT and previous["workflow_url"] == V15_WORKFLOW
    assert previous["evidence_commit"] == V15_EVIDENCE_COMMIT
    assert previous["original_image_record_sha256"] == digest((LEGACY_ART / "image-record.json").read_bytes())
    for path_key, sha_key, width_key, height_key in (("asset", "asset_sha256", "width", "height"),
                                                   ("small_asset", "small_asset_sha256", "small_width", "small_height")):
        raw = get(hero[path_key])
        assert digest(raw) == hashes[hero[path_key]] == hero[sha_key]
        with Image.open(io.BytesIO(raw)) as image:
            assert image.format == "WEBP" and image.size == (hero[width_key], hero[height_key])
        assert abs(hero[width_key] / hero[height_key] - art["source_dimensions"][0] / art["source_dimensions"][1]) < .005


def verify(info, reader):
    from city_nodes_r7_verify import Document, verify_links
    get = lru_cache(maxsize=None)(reader)
    assert KEY in info, "Current homepage and V6 study are missing"
    old, prior = restore_v14_context(info, get)
    meta, hashes = info[KEY], info["files_sha256"]
    for path, expected in old["files_sha256"].items():
        if path not in MUTABLE and path != ".nojekyll":
            assert digest(get(path)) == expected, (path, "Protected public bytes changed")
    assert meta["authorization_quote"] == AUTHORIZATION and meta["correction_quote"] == CORRECTION
    assert meta["research_source_commit"] == "d6e1754fa5b9dd6f3bb79ac3d152ccb6e104eac0"
    assert meta["structural_feasibility"] == "not_established"
    assert meta["new_ancient_coordinates"] == 0 and meta["historical_ground_truth_upgraded"] is False
    assert meta["hero"] == record()["hero"] and meta["current_image_record"] == SCENE_FOLDER + "/image-record.json"
    assert meta["supersedes"] == record()["supersedes"]
    verify_legacy_art(get, hashes)
    verify_current_art(get, hashes)
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
                reversible_homepages=2, structural_feasibility="not_established", downloads=len(topic.downloads),
                current_scene_source_kind=meta["hero"]["source_kind"],
                spatial_review_scope=record()["visual_review"]["scope"],
                superseded_visual_status=meta["supersedes"]["visual_status"],
                superseded_technical_status=meta["supersedes"]["technical_acceptance_status"])


def publish(site=SITE):
    info_raw = (site / "build-info.json").read_bytes()
    info = json.loads(info_raw)
    assert KEY not in info, "Build the predecessor first; the current homepage layer must run once at the end"
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
              (LEGACY_ART / "image-record.json", FOLDER + "/homepage-image-record.json"),
              (LEGACY_ART / "generation-prompts.txt", FOLDER + "/homepage-generation-prompts.txt"),
              (LEGACY_ART / "visual-review.md", FOLDER + "/homepage-visual-review.md"),
              (ART / "image-record.json", SCENE_FOLDER + "/image-record.json")]
    copies.extend((LEGACY_ART / name, FOLDER + "/homepage/" + name) for name in SCENE_FILES)
    copies.extend((ART / name, SCENE_FOLDER + "/" + name) for name in CURRENT_SCENE_FILES)
    copies.extend((LEGACY_ART / "publication" / source, public_path)
                  for source, public_path in legacy_publication_paths().items())
    for artwork in (legacy_record(), art):
        for path_key, source_key, checksum_key in (("asset", "full_source", "asset_sha256"), ("small_asset", "small_source", "small_asset_sha256")):
            source = ROOT / artwork[source_key]
            assert digest(source.read_bytes()) == artwork["hero"][checksum_key]
            copies.append((source, artwork["hero"][path_key]))
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
    assert all(hashes[p] == old_hashes[p] for p in protected), "Current homepage touched a protected resource"
    added = set(hashes) - set(old_hashes)
    assert META not in added
    meta = dict(version=VERSION, research_version="V6", hero_revision=REVISION, hero=hero, metadata=META,
                source_commit=info["source_commit"], research_source_commit="d6e1754fa5b9dd6f3bb79ac3d152ccb6e104eac0",
                study_page=PAGE, homepage_stylesheet=style_asset(), authorization_date="2026-11-28", authorization_quote=AUTHORIZATION,
                correction_quote=CORRECTION, current_image_record=SCENE_FOLDER + "/image-record.json", supersedes=art["supersedes"],
                scope="homepage_spatial_scene_revision_with_unchanged_v6_study", structural_feasibility="not_established",
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
    dump(ROOT / "artifacts/homepage-yongning-v16-verify.json", result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify(json.loads((SITE / "build-info.json").read_bytes()), lambda path: (SITE / path).read_bytes()), ensure_ascii=False))
    else:
        publish()
