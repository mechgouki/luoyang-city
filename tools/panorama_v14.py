"""Publish a V14 image review, including explicit rejected trial drawings."""
import argparse
import copy
from functools import lru_cache
import io
import json
from pathlib import Path
import re
import struct
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
import zlib

import PIL
from PIL import Image, features

from city_nodes_r7_verify import webp_size
from homepage_artwork_v10 import V12
from panorama_v14_contract import (
    KEY, VERSION, RESEARCH_VERSION, PAGE, FOLDER, MANIFEST, RECORD, SOURCE_RECORD,
    HOME_PAGES, BUILD_CONTROL_FILES, HOME_ARCHIVES, RELEASE_ARCHIVE,
    ACCEPTED_REVIEW_STATUSES, REJECTED_REVIEW_STATUS, HOME_ENTRIES_BY_STATUS, DISPLAY_GUIDE_ROLES,
    milestone, digest, add_home, restore_r11_context,
)
from panorama_v14_page import make_page

ROOT = Path(__file__).resolve().parents[1]
OLD_RECORD = "research/city-spatial-r9/panorama-image-record.json"
WEBP_CONVERSION = {
    "schema": "luoyang-panorama-webp-conversion-v1",
    "source": "source_png",
    "pillow_version": "11.2.1",
    "webp_version": "1.5.0",
    "color_mode": "RGB",
    "full": {"format": "WEBP", "quality": 92, "method": 6, "lossless": False, "exact": False},
    "small": {"source": "source_png", "width": 960,
              "height_rule": "round(source_height * 960 / source_width)",
              "resample": "LANCZOS", "format": "WEBP", "quality": 92,
              "method": 6, "lossless": False, "exact": False},
    "metadata_policy": "omit_exif_icc_xmp",
    "crop": False,
}


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_file(path):
    result = (ROOT / path).resolve()
    assert result.is_relative_to(ROOT) and result.is_file(), (path, "Missing project input")
    return result


def png_size(raw):
    assert raw[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR" and len(raw) >= 33
    assert zlib.crc32(raw[12:29]) == struct.unpack(">I", raw[29:33])[0]
    return struct.unpack(">II", raw[16:24])


@lru_cache(maxsize=4)
def _encode_candidate_webp(source_png):
    """Return deterministic full/small bytes directly from one opaque PNG.

    Cache keys contain the complete source bytes, so overwriting a candidate
    path cannot reuse a derivative from another generation attempt.
    """
    assert PIL.__version__ == WEBP_CONVERSION["pillow_version"], "Use the pinned Pillow conversion runtime"
    assert features.version_module("webp") == WEBP_CONVERSION["webp_version"], "WebP encoder differs from the recorded conversion"
    width, height = png_size(source_png)
    assert width >= WEBP_CONVERSION["small"]["width"], "Candidate is smaller than the fixed mobile derivative"
    with Image.open(io.BytesIO(source_png)) as original:
        original.load()
        assert original.format == "PNG" and original.size == (width, height)
        if "A" in original.getbands():
            assert original.getchannel("A").getextrema() == (255, 255), "An opaque panorama is required"
        source = original.convert("RGB")
    mobile_width = WEBP_CONVERSION["small"]["width"]
    mobile_height = round(height * mobile_width / width)
    variants = {"full": source,
                "small": source.resize((mobile_width, mobile_height), Image.Resampling.LANCZOS)}
    result = {}
    for scale, image in variants.items():
        buffer = io.BytesIO()
        image.save(buffer, format="WEBP", quality=92, method=6, lossless=False,
                   exact=False, exif=b"", icc_profile=b"", xmp=b"")
        result[scale] = buffer.getvalue()
    return result["full"], result["small"]


def encode_candidate_webp(source_png):
    """Expose fresh mapping containers; cached encoded byte values stay immutable."""
    full, small = _encode_candidate_webp(source_png)
    return {"full": full, "small": small}


def validate_webp_derivatives(source_png, conversion, derivatives):
    """Reject another attempt's image or a same-size crop despite valid hashes."""
    assert conversion == WEBP_CONVERSION, "Image conversion differs from the fixed no-crop contract"
    expected = encode_candidate_webp(source_png)
    assert set(derivatives) == {"full", "small"}
    for scale, raw in derivatives.items():
        assert raw == expected[scale], (scale, "WebP was not derived from this exact PNG with the recorded conversion")


def validate_review_identity(review, source_png_sha256, label="Review", *,
                             record_status="candidate_for_review", expected_review_status=None):
    assert review["source_png_sha256"] == source_png_sha256, label + " describes a different generated image"
    assert review["homepage_replacement_approved"] is False, label + " cannot approve the homepage"
    assert record_status in HOME_ENTRIES_BY_STATUS, "Unknown V14 image status"
    if record_status == "needs_revision":
        assert review["review_status"] == REJECTED_REVIEW_STATUS, label + " must remain explicitly rejected"
        findings = review.get("blocking_findings")
        assert isinstance(findings, list) and findings, label + " must retain its blocking visual findings"
        assert all(isinstance(item, str) and item.strip() for item in findings), label + " has an empty or non-text blocking finding"
    else:
        assert review["review_status"] in ACCEPTED_REVIEW_STATUSES, label + " is not accepted for user review"
        assert not review.get("blocking_findings"), label + " has unresolved blocking visual findings"
    if expected_review_status is not None:
        assert review["review_status"] == expected_review_status, label + " disagrees with the recorded review state"


def validate_record_review_state(record, review, audit=None):
    """Keep publication readiness separate from whether the image was accepted.

    Rejected records expose the ordered union of every review's blockers. An
    independent audit cannot silently lose a finding when the page is built.
    """
    status = record["status"]
    validate_review_identity(review, record["source_png_sha256"], "Candidate review", record_status=status)
    review_status = review["review_status"]
    if audit is not None:
        validate_review_identity(audit, record["source_png_sha256"], "Independent visual audit",
                                 record_status=status, expected_review_status=review_status)
    findings = list(dict.fromkeys([*(review.get("blocking_findings") or []),
                                   *((audit or {}).get("blocking_findings") or [])]))
    if status == "needs_revision":
        assert record.get("review_status") == review_status, "Rejected image record must declare the same rejected review state"
        assert record.get("blocking_findings") == findings, "Rejected image record must expose all review blockers without omission"
    else:
        assert record.get("review_status", review_status) == review_status, "Image record and review disagree"
        assert not record.get("blocking_findings"), "An accepted record cannot retain blocking findings"
    return dict(status=status, review_status=review_status, blocking_findings=findings,
                blocking_findings_count=len(findings))


def validate_record(record):
    assert record["schema"] == "luoyang-panorama-v14-image-v1"
    assert record["revision"] == "panorama-candidate-v14"
    assert record["status"] in HOME_ENTRIES_BY_STATUS
    assert record["homepage_replacement_approved"] is False
    assert record["generation_tool"] == "built-in image_gen"
    previous = json.loads(source_file(OLD_RECORD).read_bytes())
    assert record["source_image"] == {"path": previous["full"]["path"], "sha256": previous["full"]["sha256"]}
    assert digest(source_file(record["source_image"]["path"]).read_bytes()) == record["source_image"]["sha256"]
    assert all(record.get(k) for k in ("title", "alt", "prompt_file", "candidate_review_file", "changes", "remaining_limits", "supporting_assets"))
    if record["status"] == "needs_revision":
        assert "未通过" in record["title"], "Rejected trial title must state that it did not pass"
    source_file(record["prompt_file"])
    derivatives = {}
    for scale in ("full", "small"):
        item = record[scale]
        assert all(type(item[k]) is int and item[k] > 0 for k in ("width", "height"))
        assert re.fullmatch(r"[a-f0-9]{64}", item["sha256"]) and item["path"].endswith(".webp")
        raw = source_file(item["path"]).read_bytes()
        assert digest(raw) == item["sha256"] and webp_size(raw) == (item["width"], item["height"])
        derivatives[scale] = raw
    original = record["source_png"]
    raw = source_file(original["path"]).read_bytes()
    assert original["path"].endswith(".png")
    assert digest(raw) == original["sha256"] == record["source_png_sha256"]
    assert png_size(raw) == (original["width"], original["height"]) == (record["full"]["width"], record["full"]["height"])
    validate_webp_derivatives(raw, record["conversion"], derivatives)
    assert record["small"]["width"] <= record["full"]["width"]
    ratio = lambda item: item["width"] / item["height"]
    assert abs(ratio(record["full"]) - ratio(record["small"])) < .005, "Mobile image is cropped"
    assert abs(ratio(record["full"]) - 1672 / 941) < .035, "Wide composition was lost"
    identifiers = []
    for item in record["changes"]:
        assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item["id"])
        identifiers.append(item["id"])
        assert item["treatment_type"] in {"changed", "retained", "not_located", "attempted_not_accepted"}
        if item["treatment_type"] == "attempted_not_accepted":
            assert record["status"] == "needs_revision", "A failed attempted change cannot be relabelled as an accepted candidate"
        assert all(isinstance(item[k], str) and item[k].strip() for k in ("title", "observation", "evidence", "change", "limitation"))
        assert item["evidence_links"]
        for link in item["evidence_links"]:
            parsed = urlsplit(link["url"])
            assert link["label"] and parsed.scheme in ("", "https", "http") and not link["url"].startswith("//")
    assert len(identifiers) == len(set(identifiers))
    if record["status"] == "needs_revision":
        assert any(item["treatment_type"] == "attempted_not_accepted" for item in record["changes"]), "Rejected trial must identify its unsuccessful attempted changes"
    assert all(isinstance(x, str) and x.strip() for x in record["remaining_limits"])
    roles, asset_ids = [], []
    for item in record["supporting_assets"]:
        assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item["id"])
        assert item["title"] and item["description"] and item["role"]
        assert isinstance(item["download"], bool)
        raw = source_file(item["path"]).read_bytes()
        assert digest(raw) == item["sha256"], (item["path"], "Supporting input changed")
        suffix = Path(item["path"]).suffix.lower()
        assert suffix in {".svg", ".png", ".json", ".csv", ".md", ".txt"}
        if suffix == ".svg":
            svg = ET.fromstring(raw)
            assert svg.tag.endswith("}svg") and svg.get("viewBox"), item["path"]
            for node in svg.iter():
                for key, value in node.attrib.items():
                    if key.rsplit("}", 1)[-1] == "href":
                        assert value.startswith(("data:", "#")), "Projection SVG must be self-contained"
        if item["role"] in DISPLAY_GUIDE_ROLES:
            assert suffix in {".svg", ".png"}
        if item["role"] == "attempt_review":
            assert suffix == ".json" and item["download"] is True, "Every trial review must remain available as its complete original JSON"
        if item["role"] == "projection_data":
            assert suffix == ".json"
            projection = json.loads(raw)
            assert projection["field_registration_verified"] is False
            assert projection["new_ancient_coordinates"] == 0
            assert projection["source_inputs_sha256"]
            for path, checksum in projection["source_inputs_sha256"].items():
                assert digest(source_file(path).read_bytes()) == checksum, (path, "Projection source changed")
        roles.append(item["role"])
        asset_ids.append(item["id"])
    assert len(asset_ids) == len(set(asset_ids))
    assert {"projection_overview", "projection_yongning", "projection_data"} <= set(roles)
    review = json.loads(source_file(record["candidate_review_file"]).read_bytes())
    audit = json.loads(source_file(record["visual_audit_file"]).read_bytes()) if record.get("visual_audit_file") else None
    validate_record_review_state(record, review, audit)
    return record


def build(site=ROOT / "_site"):
    info = json.loads((site / "build-info.json").read_bytes())
    if KEY in info:
        info, old_reader = restore_r11_context(info, lambda p: (site / p).read_bytes())
        for path in (*HOME_PAGES, "release.json"):
            (site / path).write_bytes(old_reader(path))
    assert "city_plan_r11" in info and "panorama_review_v13_r2" in info
    release_raw = (site / "release.json").read_bytes()
    release = json.loads(release_raw)
    record = validate_record(json.loads(source_file(SOURCE_RECORD).read_bytes()))
    review_state = validate_record_review_state(
        record, json.loads(source_file(record["candidate_review_file"]).read_bytes()),
        json.loads(source_file(record["visual_audit_file"]).read_bytes()) if record.get("visual_audit_file") else None)
    previous = json.loads(source_file(OLD_RECORD).read_bytes())
    inputs = {p: digest(source_file(p).read_bytes()) for p in (SOURCE_RECORD, OLD_RECORD)}
    assets = []

    def copy_input(source, target):
        raw = source_file(source).read_bytes()
        inputs[source] = digest(raw)
        (site / target).parent.mkdir(parents=True, exist_ok=True)
        (site / target).write_bytes(raw)
        assets.append(target)
        return raw

    images = {}
    for kind in ("v14", "v13r2", "v12"):
        images[kind] = {}
        for scale in ("full", "small"):
            target = FOLDER + "/" + kind + ("" if scale == "full" else "-small") + ".webp"
            if kind == "v14":
                raw = copy_input(record[scale]["path"], target)
            else:
                source = info["panorama_review_v13_r2"]["images"]["v13r2"][scale] if kind == "v13r2" else (V12.full if scale == "full" else V12.small)
                raw = (site / source).read_bytes()
                checksum = previous[scale]["sha256"] if kind == "v13r2" else (V12.full_sha if scale == "full" else V12.small_sha)
                assert digest(raw) == checksum, "Earlier image identity changed"
                (site / target).parent.mkdir(parents=True, exist_ok=True)
                (site / target).write_bytes(raw)
                assets.append(target)
            width, height = webp_size(raw)
            images[kind].update({scale: target, scale + "_sha256": digest(raw),
                                ("" if scale == "full" else "small_") + "width": width,
                                ("" if scale == "full" else "small_") + "height": height})
        images[kind]["revision"] = record["revision"] if kind == "v14" else previous["revision"] if kind == "v13r2" else V12.revision
    original_target = FOLDER + "/panorama-v14-source.png"
    copy_input(record["source_png"]["path"], original_target)
    prompt = FOLDER + "/generation-prompts.txt"
    copy_input(record["prompt_file"], prompt)
    audit_sources = {FOLDER + "/candidate-review.json": record["candidate_review_file"]}
    if record.get("visual_audit_file"):
        audit_sources[FOLDER + "/visual-audit.json"] = record["visual_audit_file"]
    for target, source in audit_sources.items():
        copy_input(source, target)
    supporting = []
    for item in record["supporting_assets"]:
        target = FOLDER + "/evidence/" + item["id"] + Path(item["path"]).suffix.lower()
        copy_input(item["path"], target)
        supporting.append(dict(item, published_path=target))
        if item["role"] == "projection_data":
            inputs.update(json.loads(source_file(item["path"]).read_bytes())["source_inputs_sha256"])
    for suffix in ("css", "js"):
        copy_input("web/panorama-v14." + suffix, FOLDER + "/review." + suffix)
    from yongning_study import build as build_yongning_study
    study = build_yongning_study(site, info["source_commit"])
    assets.extend([*study["files_sha256"], study["manifest"]])
    data = dict(schema="luoyang-panorama-v14-review-v1", research_version=RESEARCH_VERSION,
                implementation_version=VERSION, source_commit=info["source_commit"],
                target_years=[516, 528], candidate=copy.deepcopy(record), images=images,
                supporting_assets=supporting, source_png=original_target,
                new_ancient_coordinates=0, new_shoreline_geometries=0, field_registration_verified=False,
                homepage_revision=V12.revision, homepage_replacement_approved=False,
                source_inputs_sha256=inputs, audit_source_paths=audit_sources, **review_state)
    dump(site / RECORD, data)
    assets.append(RECORD)
    downloads = [images["v14"]["full"], original_target, RECORD, prompt,
                 *audit_sources, *[x["published_path"] for x in supporting if x["download"]], MANIFEST]
    assert len(downloads) == len(set(downloads))
    (site / PAGE).write_text(make_page(data, downloads, study=study), encoding="utf-8")
    assets.append(PAGE)
    before_homes, after_homes = {}, {}
    for page in HOME_PAGES:
        before = (site / page).read_bytes()
        (site / HOME_ARCHIVES[page]).parent.mkdir(parents=True, exist_ok=True)
        (site / HOME_ARCHIVES[page]).write_bytes(before)
        assets.append(HOME_ARCHIVES[page])
        (site / page).write_bytes(add_home(before, record["status"]))
        before_homes[page], after_homes[page] = digest(before), digest((site / page).read_bytes())
    (site / RELEASE_ARCHIVE).write_bytes(release_raw)
    assets.append(RELEASE_ARCHIVE)
    protected = {p: h for p, h in info["files_sha256"].items() if p not in {*HOME_PAGES, "release.json", *BUILD_CONTROL_FILES}}
    controls = {p: info["files_sha256"][p] for p in BUILD_CONTROL_FILES}
    for path, checksum in {**protected, **controls}.items():
        assert digest((site / path).read_bytes()) == checksum, (path, "Earlier published resource changed")
    meta = dict(version=VERSION, research_version=RESEARCH_VERSION, source_commit=info["source_commit"],
                page=PAGE, manifest=MANIFEST, record=RECORD, **review_state,
                homepage_revision=V12.revision, homepage_replacement_approved=False,
                candidate_revision=record["revision"], source_inputs_sha256=inputs,
                files_sha256={p: digest((site / p).read_bytes()) for p in assets},
                images=images, source_png=original_target, supporting_assets=supporting,
                change_count=len(record["changes"]), download_files=downloads,
                new_ancient_coordinates=0, new_shoreline_geometries=0, field_registration_verified=False,
                homepage_before_sha256=before_homes, homepage_after_sha256=after_homes,
                predecessor_release=dict(path=RELEASE_ARCHIVE, sha256=digest(release_raw)),
                protected_files_sha256=protected, build_control_files_sha256=controls,
                yongning_study=study)
    dump(site / MANIFEST, meta)
    info[KEY] = meta
    release["extensions"] = sorted(set(release["extensions"]) | {VERSION})
    release[KEY + "_version"] = VERSION
    release[KEY + "_status"] = record["status"]
    release[KEY + "_review_status"] = review_state["review_status"]
    release["current_milestone"] = milestone(record["status"])
    dump(site / "release.json", release)
    for path in [*assets, MANIFEST, *HOME_PAGES, "release.json"]:
        info["files_sha256"][path] = digest((site / path).read_bytes())
    dump(site / "build-info.json", info)
    return meta


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "_site")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        from panorama_v14_verify import verify
        info = json.loads((args.site / "build-info.json").read_bytes())
        result = verify(info, lambda p: (args.site / p).read_bytes())
    else:
        meta = build(args.site)
        result = {k: meta[k] for k in ("version", "status", "change_count", "homepage_revision", "homepage_replacement_approved")}
    print(json.dumps(result, ensure_ascii=False, indent=2))
