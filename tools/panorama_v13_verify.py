"""Check candidate provenance, exact homepage restoration and public resources."""
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from city_nodes_r7_contract import BUILD_CONTROL_FILES
from city_nodes_r7_verify import Document, verify_links, webp_size
from homepage_artwork_v10 import PAGES, V12
from panorama_v13_contract import FOLDER, HOME_ENTRY, KEY, MANIFEST, PAGE, RECORD, RESEARCH_VERSION, VERSION, restore_home

ROOT = Path(__file__).resolve().parents[1]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(info, reader, *, build_control_reader=None):
    from city_spatial_r9_compat import restore_r8_context
    info, reader = restore_r8_context(info, reader)
    get = lru_cache(maxsize=None)(reader)
    hashes = info["files_sha256"]
    meta = info[KEY]
    assert json.loads(get(MANIFEST)) == meta
    assert meta["version"] == VERSION and meta["research_version"] == RESEARCH_VERSION
    data = json.loads(get(RECORD))
    assert data["source_commit"] == meta["source_commit"] == info["source_commit"]
    assert data["research_version"] == RESEARCH_VERSION and data["implementation_version"] == VERSION
    assert data["target_years"] == [516, 528]
    assert meta["status"] == data["candidate"]["status"] == "candidate_for_review"
    assert meta["homepage_revision"] == data["homepage_revision"] == V12.revision
    assert data["homepage_replacement_approved"] is meta["homepage_replacement_approved"] is False
    assert data["candidate"]["homepage_replacement_approved"] is False
    assert data["new_ancient_coordinates"] == meta["new_ancient_coordinates"] == 0
    assert data["new_shoreline_geometries"] == meta["new_shoreline_geometries"] == 0
    assert meta["candidate_revision"] == data["candidate"]["revision"] == "panorama-candidate-v13"
    assert data["source_inputs_sha256"] == meta["source_inputs_sha256"]
    for path, checksum in data["source_inputs_sha256"].items():
        source = (ROOT / path).resolve()
        assert source.is_relative_to(ROOT) and source.is_file(), path
        assert digest(source.read_bytes()) == checksum, (path, "Source evidence changed")
    source_record = json.loads((ROOT / "research/panorama-r8/image-record.json").read_bytes())
    assert data["candidate"] == source_record, "Publication changed a reviewed image decision"
    assert source_record["source_image"]["sha256"] == V12.full_sha
    original = source_record["source_png"]
    assert data["source_inputs_sha256"][original["path"]] == original["sha256"] == source_record["source_png_sha256"], "Original image is not bound to the candidate evidence"
    assert data["images"] == meta["images"]
    assert len(source_record["changes"]) == meta["change_count"] > 0
    assert source_record["remaining_limits"]
    resources = meta["files_sha256"]
    assert set(resources) == {path for path in hashes if path.startswith(FOLDER + "/") and path != MANIFEST}
    for path, checksum in resources.items():
        assert digest(get(path)) == hashes[path] == checksum, path
    for path in (PAGE, MANIFEST):
        assert digest(get(path)) == hashes[path], path
    for version, image in data["images"].items():
        for scale in ("full", "small"):
            raw = get(image[scale])
            assert digest(raw) == image[scale + "_sha256"]
            prefix = "" if scale == "full" else "small_"
            assert webp_size(raw) == (image[prefix + "width"], image[prefix + "height"])
            if version == "v13":
                expected = source_record[scale]
                assert digest(raw) == expected["sha256"] and webp_size(raw) == (expected["width"], expected["height"])
            else:
                original, checksum = (V12.full, V12.full_sha) if scale == "full" else (V12.small, V12.small_sha)
                assert raw == get(original) and digest(raw) == checksum, "Approved image was altered"
    assert get(FOLDER + "/generation-prompt.txt") == (ROOT / source_record["prompt_file"]).read_bytes()
    for path in data["audit_files"]:
        assert get(path) == (ROOT / "research/panorama-r8" / Path(path).name).read_bytes()
        if Path(path).name == "candidate-review.json":
            assert json.loads(get(path))["source_png_sha256"] == source_record["source_png_sha256"], "The final review belongs to another candidate"

    protected = meta["protected_files_sha256"]
    mandatory = {"city-nodes/readings.json", "city-nodes/segments.csv", "city-nodes/manifest.json", "downloads/luoyang-city-nodes.zip",
                 "luoyang-city-nodes.html", "all-roads/records.json", V12.full, V12.small, V12.metadata}
    assert mandatory <= set(protected)
    for path, checksum in protected.items():
        assert digest(get(path)) == hashes[path] == checksum, (path, "Earlier result changed")
    controls = meta["build_control_files_sha256"]
    assert set(controls) == BUILD_CONTROL_FILES and not BUILD_CONTROL_FILES.intersection(protected)
    for path, checksum in controls.items():
        assert hashes[path] == checksum
        if build_control_reader:
            assert digest(build_control_reader(path)) == checksum
    assert set(meta["predecessor_homepage"]) == set(PAGES)
    for page, prior in meta["predecessor_homepage"].items():
        current = get(page)
        archive = get(prior["archive"])
        assert current.count(HOME_ENTRY) == 1
        assert digest(current) == hashes[page]
        assert restore_home(current) == archive
        assert digest(archive) == hashes[prior["archive"]] == prior["sha256"]
        assert f'data-hero-revision="{V12.revision}"'.encode() in current
        assert b'panorama-candidate-v13' not in current, "Candidate was installed as the homepage hero"
    release = json.loads(get("release.json"))
    prior_release = meta["predecessor_release"]
    raw_release = get(prior_release["path"])
    assert digest(raw_release) == prior_release["sha256"]
    expected_release = json.loads(raw_release)
    expected_release["extensions"] = sorted(set(expected_release["extensions"]) | {VERSION})
    expected_release[KEY + "_version"] = VERSION
    expected_release["current_milestone"] = "盛时 R8.1 · 依城市证据校订V13全景候选图"
    assert release == expected_release
    assert release["homepage_hero_revision"] == V12.revision and release["homepage_hero_status"] == "approved"

    doc = verify_links(get(PAGE), hashes, current=PAGE)
    anchors = set(doc.ids)
    assert {"main", "comparison", "review-status", "view-controls", "view-status", "figure-v13", "figure-v12", "changes", "limits", "downloads"} <= anchors
    assert doc.downloads == meta["download_files"]
    for item in source_record["changes"]:
        assert "change-" + item["id"] in anchors
        for link in item["evidence_links"]:
            assert link["url"] in doc.links
            parsed = urlsplit(link["url"])
            if not parsed.scheme and parsed.path and parsed.fragment:
                target = parsed.path.removeprefix("./")
                assert parsed.fragment in Document(get(target)).ids, link
    return dict(status="passed", source_commit=info["source_commit"], candidate_revision=meta["candidate_revision"],
                homepage_revision=V12.revision, homepage_replacement_approved=False,
                change_count=meta["change_count"], downloads=len(doc.downloads),
                protected_public_files=len(protected), reversible_homepages=len(PAGES),
                new_ancient_coordinates=0, new_shoreline_geometries=0)
