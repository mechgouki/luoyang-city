#!/usr/bin/env python3
"""Collect the V12 full-frame homepage's selected PR/live acceptance evidence.

Standard library only. Reads an unmodified GitHub Actions ZIP, validates all
selected material before writing, and copies only fixed-whitelist bytes. It
does not fetch, upload, invoke git, extract arbitrary paths, or overwrite output.

Use the source_commit actually tested by the PR run (its synthetic merge commit,
not automatically the branch head). For live, use the released main commit.
The workflow URL is recorded provenance, not proof of workflow/job success.

Example:
  python collect_h12_evidence.py --zip h12-pr-evidence.zip --phase pr \
    --expected-source-commit FULL_TESTED_SHA --output h12-evidence/pr
  python collect_h12_evidence.py --zip h12-live-evidence.zip --phase live \
    --expected-source-commit FULL_RELEASE_SHA --output h12-evidence/live

--check-only validates without creating an output directory or final metadata.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import sys
import tempfile
from urllib.parse import urlsplit
from zipfile import BadZipFile, ZipFile


LIVE_BASE = "https://mechgouki.github.io/luoyang-city/"
SOURCE_PNG_SHA = "c7954dfc3ee659de756c62d0f634e40eddfd2ecc93cc8b833f53f6c0e0dc69ca"
FULL_SHA = "d8d5be74d123b5eeaac50ce68955787e26686b92c1a30031f6c3289692fbf4c2"
SMALL_SHA = "eb836bc7ba458ae392c313c030ee7ed9654bd838bb46b62e8fdf418e5e369f21"
FULL_ASSET = f"_assets/{FULL_SHA[:20]}-luoyang-panorama-approved-v12.webp"
SMALL_ASSET = f"_assets/{SMALL_SHA[:20]}-luoyang-panorama-approved-v12-small.webp"
ASSET_HASHES = {FULL_ASSET: FULL_SHA, SMALL_ASSET: SMALL_SHA}
DEVICES = {"desktop": (1500, 960), "wide": (1920, 1080),
           "tablet": (768, 1024), "mobile": (390, 844)}
ENTRIES = {"index", "dual"}
APPROVAL_SHOTS = {f"approved-{device}{suffix}.png" for device in DEVICES
                  for suffix in ("", "-dual")} | {
                      "approved-desktop-full-hero.png", "approved-mobile-full-hero.png"}
JOURNEY_SHOTS = {"homepage-desktop-first-screen.png": (1500, 1000),
                 "homepage-tablet-first-screen.png": (900, 1000),
                 "homepage-mobile-first-screen.png": (390, 844)}
APPROVAL_CHECKS = {
    "Both homepage URLs use the approved full-frame source; actual WebP hashes and the v11 archive match their provenance"
} | {
    f"{width}px {entry} displays the entire panorama in proportion, with its title and caption below the image"
    for width, _ in DEVICES.values() for entry in ENTRIES
} | {
    f"390px {entry} opens the actual map from the full-frame homepage" for entry in ENTRIES
}
JOURNEY_CHECKS = {
    "desktop homepage presents the large panorama, three questions, live map and research in order",
    "start exploration reaches the actual map; zoom, region, search and shared entity reload work",
    "the relocated research area keeps B1-B8 access and the working map overlay control",
    "existing research and about routes stay direct; the current release URL has the same homepage",
    "900px wrapped navigation stays above the panorama without overlap or horizontal overflow",
    "390px homepage, tap-to-map, regional filters and question navigation work without page overflow",
    "zero browser runtime errors during the homepage journeys",
} | {
    f"{question} question opens the intended evidence, survives reload and returns to the homepage"
    for question in ("yongning", "markets", "identity")
}
# Fingerprints of sorted unittest identities, joined by LF with a final LF.
# The research suite is unchanged from the successful R6.2 PR. The six homepage
# identities include the current full-frame test in place of the former 07 test.
TEST_REPORTS = {
    "prosperity-semantic-tests.txt": (218, "fcb1e081e81448a8a4769962bb204af1d7955b81b45856edf82c5ffa580d083d"),
    "homepage-approved-v9-tests.txt": (6, "a9a176fd039c13cbbd75e2c7056b08a3d5cfba1e4cb6bf07f591fb26eaef17d0"),
}
MAX_SELECTED_FILE = 64 * 1024 * 1024
MAX_SELECTED_TOTAL = 160 * 1024 * 1024


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def is_sha(value):
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def relative_path(value):
    return (isinstance(value, str) and bool(value) and "\\" not in value and "\x00" not in value
            and not PurePosixPath(value).is_absolute()
            and not any(part in ("", ".", "..") for part in value.split("/"))
            and ":" not in value and "?" not in value and "#" not in value)


def png_size(raw, name):
    demand(len(raw) >= 33 and raw[:8] == b"\x89PNG\r\n\x1a\n" and raw[12:16] == b"IHDR",
           f"{name}: invalid PNG header")
    width, height = struct.unpack(">II", raw[16:24])
    demand(0 < width <= 20000 and 0 < height <= 50000, f"{name}: invalid PNG dimensions")
    return width, height


def whitelist(phase):
    prefix = "live-" if phase == "live" else ""
    approval = prefix + "homepage-approved-v9-browser"
    journey = prefix + "homepage-v1-browser"
    names = {"browser-runtime-digest.json", f"{approval}/results.json", f"{journey}/results.json"}
    names.update(f"{approval}/{name}" for name in APPROVAL_SHOTS)
    names.update(f"{journey}/{name}" for name in JOURNEY_SHOTS)
    names.update({"live-http.json"} if phase == "live" else TEST_REPORTS)
    return approval, journey, names


def validate_base(value, phase, name):
    demand(isinstance(value, str), f"{name}: base_url is missing")
    if phase == "live":
        demand(value == LIVE_BASE, f"{name}: unexpected live base_url")
    else:
        parsed = urlsplit(value)
        demand(parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
               and parsed.port is not None and parsed.path == "/luoyang-city/"
               and not parsed.query and not parsed.fragment,
               f"{name}: expected the PR's local HTTP test server")


def validate_tests(body, name, commit):
    text = body.decode("utf-8-sig")
    summary = re.search(r"(?m)^Ran ([1-9][0-9]*) tests? in [^\n]+\n\s*\nOK\s*\Z", text)
    demand(summary is not None, f"{name}: no complete successful unittest summary")
    demand(not re.search(r"(?m)^(?:FAILED|ERROR:|FAIL:|Traceback)", text), f"{name}: failure diagnostics present")
    expected_count, expected_identity_sha = TEST_REPORTS[name]
    starts = list(re.finditer(r"(?m)^test_\S+ \(([^)]+)\)", text))
    identities = [match[1] for match in starts]
    demand(int(summary[1]) == len(identities) == len(set(identities)) == expected_count,
           f"{name}: incomplete or duplicated unittest inventory")
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else summary.start()
        block = text[match.start():end]
        demand(re.search(r"\.\.\. ok\s*(?:\n|\Z)", block) is not None,
               f"{name}: a test lacks its successful result: {match[1]}")
    actual_identity_sha = digest(("\n".join(sorted(identities)) + "\n").encode())
    demand(actual_identity_sha == expected_identity_sha, f"{name}: the complete expected test inventory differs")
    return {"path": name, "reported_result": "OK", "tests": expected_count,
            "test_identity_sha256": actual_identity_sha, "reported_source_commit": None,
            "source_commit_binding": "same artifact as the V12 browser report checked against expected_source_commit",
            "bound_source_commit": commit}


def validate(raw, phase, commit, approval_folder, journey_folder):
    audits = []

    def read_json(name):
        try:
            return json.loads(raw[name])
        except (ValueError, UnicodeError) as error:
            raise ValueError(f"{name}: invalid JSON: {error}") from error

    name = approval_folder + "/results.json"
    report = read_json(name)
    demand(isinstance(report, dict), f"{name}: expected object")
    demand(report.get("schema") == "luoyang-homepage-full-frame-v12", f"{name}: wrong report schema")
    demand(report.get("status") == "passed" and report.get("errors") == [] and not report.get("error"),
           f"{name}: run incomplete or contains errors")
    demand(report.get("source_commit") == commit, f"{name}: source_commit does not match expected test/release commit")
    demand(report.get("hero_revision") == "panorama-approved-v12", f"{name}: wrong homepage revision")
    demand(report.get("source_png_sha256") == SOURCE_PNG_SHA, f"{name}: wrong approved PNG identity")
    demand(report.get("asset_sha256") == ASSET_HASHES, f"{name}: wrong desktop/mobile WebP identities")
    validate_base(report.get("base_url"), phase, name)
    checks = report.get("checks", [])
    demand(isinstance(checks, list) and len(checks) == 11 and all(isinstance(c, str) for c in checks)
           and set(checks) == APPROVAL_CHECKS, f"{name}: complete 11-check acceptance is absent")
    shots = report.get("screenshots", {})
    demand(isinstance(shots, dict) and set(shots) == APPROVAL_SHOTS, f"{name}: expected exactly ten screenshots")
    for picture, expected in shots.items():
        content = raw[approval_folder + "/" + picture]
        png_size(content, picture)
        demand(is_sha(expected) and digest(content) == expected, f"{picture}: screenshot hash differs from report")

    layouts = report.get("layouts", [])
    demand(isinstance(layouts, list) and len(layouts) == 8 and all(isinstance(x, dict) for x in layouts),
           f"{name}: expected eight layout observations")
    pairs = [(layout.get("device"), layout.get("entry")) for layout in layouts]
    demand(len(set(pairs)) == 8 and set(pairs) == {(device, entry) for device in DEVICES for entry in ENTRIES},
           f"{name}: missing or duplicated entrance/viewport combination")
    for layout in layouts:
        device, entry = layout["device"], layout["entry"]
        width, height = DEVICES[device]
        demand(layout.get("viewport") == {"width": width, "height": height}, f"{device}/{entry}: wrong viewport")
        suffix = "" if entry == "index" else "-dual"
        filename = f"approved-{device}{suffix}.png"
        demand(layout.get("screenshot") == filename, f"{device}/{entry}: wrong screenshot binding")
        demand(png_size(raw[approval_folder + "/" + filename], filename) == (width, height),
               f"{filename}: screenshot does not match viewport")
        expected_url = report["base_url"] + ("" if entry == "index" else "v3.0-dual.html#home")
        demand(layout.get("url") == expected_url, f"{device}/{entry}: wrong tested URL")
        geometry = layout.get("geometry", {})
        demand(isinstance(geometry, dict) and geometry.get("object_fit") == "contain", f"{device}/{entry}: not contain")
        for rect_name in ("image", "caption", "copy"):
            rect = geometry.get(rect_name, {})
            demand(isinstance(rect, dict) and all(isinstance(rect.get(key), (int, float))
                   and not isinstance(rect[key], bool) and math.isfinite(rect[key])
                   for key in ("top", "bottom", "left", "right", "width", "height")),
                   f"{device}/{entry}: missing or nonfinite {rect_name} measurement")
            demand(rect["width"] > 0 and rect["height"] > 0, f"{device}/{entry}: zero-size {rect_name}")
            demand(abs(rect["bottom"] - rect["top"] - rect["height"]) < 0.1
                   and abs(rect["right"] - rect["left"] - rect["width"]) < 0.1,
                   f"{device}/{entry}: inconsistent {rect_name} coordinates")
        image = geometry["image"]
        demand(abs(image["height"] - image["width"] * 941 / 1672) <= 1, f"{device}/{entry}: image aspect ratio changed")
        demand(image["left"] >= -1 and image["right"] <= width + 1 and image["width"] >= width * .75,
               f"{device}/{entry}: image falls outside viewport or is too small")
        demand(geometry["caption"]["top"] >= image["bottom"] - 1 and geometry["copy"]["top"] >= image["bottom"] - 1,
               f"{device}/{entry}: caption or title covers the picture")
        expected_size = (960, 540) if device == "mobile" else (1672, 941)
        demand((geometry.get("natural_width"), geometry.get("natural_height")) == expected_size,
               f"{device}/{entry}: wrong actual image dimensions")
        expected_asset = SMALL_ASSET if device == "mobile" else FULL_ASSET
        demand(geometry.get("current_source") == report["base_url"] + expected_asset,
               f"{device}/{entry}: wrong actual selected image")
    audits.append({"path": name, "reported_status": report["status"], "reported_source_commit": report["source_commit"],
                   "hero_revision": report["hero_revision"], "source_png_sha256": report["source_png_sha256"],
                   "reported_asset_sha256": report["asset_sha256"], "checks": checks,
                   "layout_observations_checked": 8, "screenshot_hashes_verified": 10,
                   "base_url": report["base_url"],
                   "asset_validation_scope": "Browser-reported source/asset identities; WebP bytes are not in the evidence ZIP. Live HTTP hashes are cross-checked in live phase."})

    name = journey_folder + "/results.json"
    journey = read_json(name)
    demand(isinstance(journey, dict) and journey.get("runtime_errors") == [] and not journey.get("error"),
           f"{name}: runtime errors or invalid object")
    demand(journey.get("status") in (None, "passed"), f"{name}: failed status")
    for field in ("source_commit", "commit"):
        if field in journey:
            demand(journey[field] == commit, f"{name}: explicit {field} mismatches expected commit")
    validate_base(journey.get("base_url"), phase, name)
    steps = journey.get("checks", [])
    demand(isinstance(steps, list) and len(steps) == len(JOURNEY_CHECKS)
           and all(isinstance(step, dict) and step.get("status") == "passed" for step in steps),
           f"{name}: incomplete or failed homepage journey")
    demand({step.get("name") for step in steps} == JOURNEY_CHECKS, f"{name}: expected homepage journeys differ")
    for picture, dimensions in JOURNEY_SHOTS.items():
        demand(png_size(raw[journey_folder + "/" + picture], picture) == dimensions,
               f"{picture}: first-screen dimensions differ")
    audits.append({"path": name, "reported_status": journey.get("status"),
                   "reported_source_commit": journey.get("source_commit"),
                   "recorded_check_count": len(steps), "base_url": journey.get("base_url"),
                   "source_commit_binding": "same artifact as the V12 browser report checked against expected_source_commit",
                   "bound_source_commit": commit, "retained_first_screens": 3,
                   "screenshot_hashes_in_original_report": False,
                   "note": "Missing status/source_commit and screenshot hashes are not invented; collector hashes are in the retained-file inventory."})

    runtime = read_json("browser-runtime-digest.json")
    demand(isinstance(runtime, list) and runtime and all(isinstance(value, str) and
           re.fullmatch(r"mcr\.microsoft\.com/playwright/python@sha256:[a-f0-9]{64}", value) for value in runtime),
           "browser-runtime-digest.json: invalid browser image digest list")
    if phase == "pr":
        audits.extend(validate_tests(raw[name], name, commit) for name in TEST_REPORTS)
    else:
        name = "live-http.json"
        http = read_json(name)
        demand(isinstance(http, dict) and http.get("status") == "passed" and not http.get("error")
               and not http.get("errors"), f"{name}: incomplete or failed verification")
        demand(http.get("commit") == commit, f"{name}: released commit mismatch")
        validate_base(http.get("base_url"), phase, name)
        files = http.get("files", [])
        demand(isinstance(files, list) and len(files) == http.get("checked_files") and len(files) >= 795
               and all(isinstance(item, dict) for item in files), f"{name}: incomplete public file inventory")
        lookup = {}
        for item in files:
            path = item.get("path")
            demand(relative_path(path) and path not in lookup, f"{name}: unsafe or duplicate public file path")
            demand(item.get("status") == "passed" and is_sha(item.get("sha256"))
                   and isinstance(item.get("bytes"), int) and item["bytes"] >= 0,
                   f"{name}: a public file did not pass hash verification: {path}")
            lookup[path] = item
        required = set(ASSET_HASHES) | {"index.html", "v3.0-dual.html", "release.json", "homepage/approval-v12.json",
            "homepage/history/index-before-v12.html", "homepage/history/v3.0-dual-before-v12.html",
            "luoyang-all-roads.html", "all-roads/records.csv", "luoyang-water-atlas.html"}
        demand(required <= set(lookup), f"{name}: required homepage/research resources missing")
        styles = [path for path in lookup if re.fullmatch(r"_assets/[a-f0-9]{20}-homepage-full-frame-v12\.css", path)]
        demand(len(styles) == 1 and styles[0].split("/")[-1].startswith(lookup[styles[0]]["sha256"][:20]),
               f"{name}: missing or incorrectly fingerprinted full-frame stylesheet")
        demand(all(lookup[path]["sha256"] == checksum for path, checksum in ASSET_HASHES.items()),
               f"{name}: HTTP and browser disagree on V12 image hashes")
        for key, expected_count in (("road_locations", 21), ("all_road_locations", 84)):
            study = http.get(key, {})
            demand(isinstance(study, dict) and study.get("status") == "passed" and study.get("source_commit") == commit,
                   f"{name}: {key} verification missing or commit mismatch")
            count = study.get("records") if key == "road_locations" else study.get("counts", {}).get("records")
            demand(count == expected_count, f"{name}: {key} record inventory differs")
        audits.append({"path": name, "reported_status": http["status"], "reported_commit": http["commit"],
                       "checked_files": http["checked_files"], "checked_at": http.get("checked_at"),
                       "all_reported_public_files_passed": True, "browser_and_http_v12_image_hashes_match": True,
                       "full_frame_stylesheet": styles[0]})
    return audits, runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zip", required=True, type=Path, dest="archive")
    parser.add_argument("--phase", required=True, choices=("pr", "live"))
    parser.add_argument("--expected-source-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workflow-url", help="Recorded provenance only; workflow/job status must be checked separately")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    commit = args.expected_source_commit.lower()
    demand(re.fullmatch(r"[a-f0-9]{40}", commit) is not None, "Expected source commit must be a full 40-hex SHA")
    archive = args.archive.resolve()
    output = args.output.absolute()
    demand(archive.is_file(), f"ZIP not found: {archive}")
    demand(not output.exists() and not output.is_symlink(), f"Refusing existing output: {output}")
    approval, journey, allowed = whitelist(args.phase)
    with ZipFile(archive) as zipped:
        inventory = [item for item in zipped.infolist() if not item.is_dir()]
        duplicate_names = [name for name, count in Counter(item.filename for item in inventory).items() if count > 1]
        demand(not duplicate_names, f"Ambiguous ZIP duplicate members: {duplicate_names}")
        by_name = {item.filename: item for item in inventory}
        demand(allowed <= set(by_name), "Required evidence missing: " + ", ".join(sorted(allowed - set(by_name))))
        demand(sum(by_name[name].file_size for name in allowed) <= MAX_SELECTED_TOTAL, "Selected evidence exceeds size bound")
        raw = {}
        for name in sorted(allowed):
            item = by_name[name]
            demand(0 <= item.file_size <= MAX_SELECTED_FILE, f"{name}: selected member exceeds size bound")
            demand(not item.flag_bits & 1, f"{name}: encrypted member refused")
            mode = stat.S_IFMT(item.external_attr >> 16)
            demand(mode in (0, stat.S_IFREG), f"{name}: symlink/nonregular member refused")
            raw[name] = zipped.read(item)
    audits, runtime = validate(raw, args.phase, commit, approval, journey)
    metadata = {
        "schema": "luoyang-homepage-v12-selected-evidence-v1", "phase": args.phase,
        "expected_source_commit": commit, "collection_validation": "passed_for_selected_evidence",
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_archive": {"name": archive.name, "bytes": archive.stat().st_size, "sha256": file_digest(archive)},
        "workflow_url": args.workflow_url, "workflow_conclusion": None,
        "workflow_conclusion_note": "Check actual GitHub workflow/job results separately; this collector verifies retained evidence only.",
        "browser_runtime_digests": runtime, "hero_revision": "panorama-approved-v12",
        "approved_source_png_sha256": SOURCE_PNG_SHA, "approved_webp_sha256": ASSET_HASHES,
        "whitelist": sorted(allowed), "selected_files": len(raw),
        "excluded_archive_file_count": len(inventory) - len(raw),
        "screenshots_retained": 13, "screenshot_hashes_verified_against_browser_report": 10,
        "report_validations": audits,
        "semantic_tests": ("Complete 218-test research and 6-test homepage successful reports retained." if args.phase == "pr" else
                           "The live job does not contain semantic-test TXT files; retain the PR evidence separately."),
        "files": [{"path": name, "bytes": len(body), "sha256": digest(body)} for name, body in sorted(raw.items())],
        "checksum_file": "SHA256SUMS", "checksum_scope": "All copied source files and evidence-metadata.json; excludes the checksum file itself.",
    }
    if args.check_only:
        print(json.dumps({"validation": "passed", "phase": args.phase, "source_commit": commit,
                          "selected_files": len(raw), "screenshots": 13, "output_written": False}))
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".h12-evidence-", dir=output.parent))
    try:
        for name, body in raw.items():
            destination = staging / name  # Every name comes from the fixed whitelist.
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
        meta_raw = (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode()
        (staging / "evidence-metadata.json").write_bytes(meta_raw)
        checksums = {name: digest(body) for name, body in raw.items()}
        checksums["evidence-metadata.json"] = digest(meta_raw)
        (staging / "SHA256SUMS").write_text("".join(f"{value}  {name}\n" for name, value in sorted(checksums.items())))
        demand(not output.exists() and not output.is_symlink(), f"Output appeared during validation: {output}")
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    print(json.dumps({"validation": "passed", "phase": args.phase, "source_commit": commit,
                      "selected_files": len(raw), "screenshots": 13,
                      "metadata": str(output / "evidence-metadata.json")}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, BadZipFile, OverflowError, struct.error) as error:
        print(f"REFUSED: {error}\nNo final evidence manifest was produced.", file=sys.stderr)
        raise SystemExit(2)
