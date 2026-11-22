"""Publish a reviewed candidate image without replacing the approved homepage."""
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
from urllib.parse import urlsplit
import zlib

from city_nodes_r7_contract import BUILD_CONTROL_FILES
from city_nodes_r7_verify import webp_size
from homepage_artwork_v10 import PAGES, V12
from panorama_v13_contract import FOLDER, KEY, MANIFEST, PAGE, RECORD, RESEARCH_VERSION, VERSION, add_home, restore_home
from panorama_v13_page import make_page

ROOT = Path(__file__).resolve().parents[1]
SOURCE_RECORD = "research/panorama-r8/image-record.json"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_file(path):
    candidate = (ROOT / path).resolve()
    assert candidate.is_relative_to(ROOT) and candidate.is_file(), (path, "Missing project input")
    return candidate


def validate_record(record):
    assert record["schema"] == "luoyang-panorama-v13-image-v1"
    assert record["revision"] == "panorama-candidate-v13"
    assert record["status"] == "candidate_for_review"
    assert record["homepage_replacement_approved"] is False
    assert record["generation_tool"] == "built-in image_gen"
    assert record["source_image"]["path"] == "web/assets/luoyang-panorama-approved-v12.webp"
    assert record["source_image"]["sha256"] == V12.full_sha
    assert record["title"] and record["alt"] and record["prompt_file"]
    for name in ("full", "small"):
        image = record[name]
        assert all(isinstance(image[key], int) and image[key] > 0 for key in ("width", "height"))
        assert re.fullmatch(r"[a-f0-9]{64}", image["sha256"])
        assert image["path"].endswith(".webp"), "Published candidate must have a WebP source"
    original = record["source_png"]
    raw_png = source_file(original["path"]).read_bytes()
    assert digest(raw_png) == original["sha256"] == record["source_png_sha256"], "Original PNG differs from the reviewed candidate"
    assert raw_png[:8] == b"\x89PNG\r\n\x1a\n", "Original candidate is not a PNG"
    assert len(raw_png) >= 33 and raw_png[8:16] == b"\x00\x00\x00\x0dIHDR", "Missing PNG IHDR"
    assert zlib.crc32(raw_png[12:29]) == struct.unpack(">I", raw_png[29:33])[0], "Invalid PNG IHDR checksum"
    png_size = struct.unpack(">II", raw_png[16:24])
    assert png_size == (original["width"], original["height"]) == (record["full"]["width"], record["full"]["height"]), "Candidate frame differs from original PNG"
    assert record["small"]["width"] <= record["full"]["width"]
    ratio = lambda item: item["width"] / item["height"]
    assert abs(ratio(record["full"]) - ratio(record["small"])) < .005, "Mobile frame differs from the candidate"
    assert abs(ratio(record["full"]) - 1672 / 941) < .03, "Candidate lost the approved wide composition"
    assert record["changes"] and record["remaining_limits"]
    ids = []
    for change in record["changes"]:
        assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", change["id"])
        ids.append(change["id"])
        for field in ("title", "observation", "evidence", "change", "limitation"):
            assert isinstance(change[field], str) and change[field].strip(), (change["id"], field)
        assert change["evidence_links"], change["id"]
        for link in change["evidence_links"]:
            assert link["label"] and link["url"]
            parsed = urlsplit(link["url"])
            assert parsed.scheme in ("", "https", "http") and not link["url"].startswith("//"), link
    assert len(ids) == len(set(ids)), "Duplicate change identifiers"
    assert all(isinstance(item, str) and item.strip() for item in record["remaining_limits"])
    return record


def build(site=ROOT / "_site"):
    info = json.loads((site / "build-info.json").read_bytes())
    release = json.loads((site / "release.json").read_bytes())
    old_meta = info.get(KEY)
    if old_meta:
        release = json.loads((site / old_meta["predecessor_release"]["path"]).read_bytes())
    record = validate_record(json.loads(source_file(SOURCE_RECORD).read_bytes()))
    dest = site / FOLDER
    dest.mkdir(parents=True, exist_ok=True)
    inputs = {SOURCE_RECORD: digest(source_file(SOURCE_RECORD).read_bytes()),
              record["source_png"]["path"]: digest(source_file(record["source_png"]["path"]).read_bytes())}
    assets = []

    def copy_input(source, target):
        original = source_file(source)
        raw = original.read_bytes()
        inputs[source] = digest(raw)
        (site / target).parent.mkdir(parents=True, exist_ok=True)
        (site / target).write_bytes(raw)
        assets.append(target)
        return raw

    images = {}
    for version in ("v13", "v12"):
        for scale in ("full", "small"):
            suffix = "" if scale == "full" else "-small"
            target = FOLDER + "/" + version + suffix + ".webp"
            if version == "v13":
                image = record[scale]
                raw = copy_input(image["path"], target)
                assert digest(raw) == image["sha256"] and webp_size(raw) == (image["width"], image["height"]), target
            else:
                original, checksum = (V12.full, V12.full_sha) if scale == "full" else (V12.small, V12.small_sha)
                raw = (site / original).read_bytes()
                assert digest(raw) == checksum, "Approved homepage image changed"
                (site / target).write_bytes(raw)
                assets.append(target)
            width, height = webp_size(raw)
            images.setdefault(version, {})[scale] = target
            images[version][scale + "_sha256"] = digest(raw)
            images[version][("" if scale == "full" else "small_") + "width"] = width
            images[version][("" if scale == "full" else "small_") + "height"] = height
        images[version]["revision"] = record["revision"] if version == "v13" else V12.revision

    prompt = FOLDER + "/generation-prompt.txt"
    copy_input(record["prompt_file"], prompt)
    audit_files = []
    for name in ("source-audit.json", "visual-audit.json", "candidate-review.json"):
        source = "research/panorama-r8/" + name
        if (ROOT / source).is_file():
            target = FOLDER + "/" + name
            raw = copy_input(source, target)
            if name == "candidate-review.json":
                assert re.fullmatch(r"[a-f0-9]{64}", record["source_png_sha256"])
                assert json.loads(raw)["source_png_sha256"] == record["source_png_sha256"], "Candidate review describes another generated image"
            audit_files.append(target)
    for name, target in (("panorama-v13.css", "review.css"), ("panorama-v13.js", "review.js")):
        copy_input("web/" + name, FOLDER + "/" + target)
    data = dict(schema="luoyang-panorama-v13-review-v1", research_version=RESEARCH_VERSION,
                implementation_version=VERSION, source_commit=info["source_commit"],
                target_years=[516, 528], candidate=copy.deepcopy(record), images=images,
                new_ancient_coordinates=0, new_shoreline_geometries=0,
                homepage_revision=V12.revision, homepage_replacement_approved=False,
                source_inputs_sha256=inputs, audit_files=audit_files)
    dump(site / RECORD, data)
    assets.append(RECORD)
    downloads = [images["v13"]["full"], RECORD, prompt, *audit_files, MANIFEST]
    (site / PAGE).write_text(make_page(data, downloads), encoding="utf-8")

    prior_homes = {}
    archive_files = []
    for page in PAGES:
        before = restore_home((site / page).read_bytes())
        archive = "homepage/history/" + page.replace(".html", "-before-v13-review.html")
        (site / archive).write_bytes(before)
        prior_homes[page] = dict(archive=archive, sha256=digest(before))
        archive_files.append(archive)
        (site / page).write_bytes(add_home(before))
    release_archive = FOLDER + "/release-before-v13.json"
    dump(site / release_archive, release)
    assets.append(release_archive)
    excluded = {*PAGES, "release.json", PAGE, *archive_files}
    protected = {path: checksum for path, checksum in info["files_sha256"].items()
                 if path not in excluded and not path.startswith(FOLDER + "/")}
    controls = {path: protected.pop(path) for path in BUILD_CONTROL_FILES}
    for path, checksum in {**protected, **controls}.items():
        assert digest((site / path).read_bytes()) == checksum, (path, "Earlier published resource changed")
    meta = dict(version=VERSION, research_version=RESEARCH_VERSION, source_commit=info["source_commit"],
                page=PAGE, manifest=MANIFEST, record=RECORD, status="candidate_for_review",
                homepage_revision=V12.revision, homepage_replacement_approved=False,
                candidate_revision=record["revision"], source_inputs_sha256=inputs,
                files_sha256={path: digest((site / path).read_bytes()) for path in assets},
                images=images, change_count=len(record["changes"]), download_files=downloads,
                new_ancient_coordinates=0, new_shoreline_geometries=0,
                predecessor_homepage=prior_homes,
                predecessor_release=dict(path=release_archive, sha256=digest((site / release_archive).read_bytes())),
                protected_files_sha256=protected, build_control_files_sha256=controls)
    dump(site / MANIFEST, meta)
    info[KEY] = meta
    release["extensions"] = sorted(set(release["extensions"]) | {VERSION})
    release[KEY + "_version"] = VERSION
    release["current_milestone"] = "盛时 R8.1 · 依城市证据校订V13全景候选图"
    dump(site / "release.json", release)
    for path in [*assets, *archive_files, MANIFEST, PAGE, *PAGES, "release.json"]:
        info["files_sha256"][path] = digest((site / path).read_bytes())
    dump(site / "build-info.json", info)
    return meta


if __name__ == "__main__":
    result = build()
    print(json.dumps({key: result[key] for key in ("version", "status", "change_count", "homepage_revision", "homepage_replacement_approved")}, ensure_ascii=False))
