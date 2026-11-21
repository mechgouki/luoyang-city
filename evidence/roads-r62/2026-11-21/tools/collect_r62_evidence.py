#!/usr/bin/env python3
"""Collect R6.2 acceptance evidence from an unmodified GitHub Actions ZIP.

Standard library only. No network, git, remote writes, or broad ZIP extraction.
Validation finishes before creating output. Existing output is never overwritten.

Example:
  python collect_r62_evidence.py --zip r62-pr-evidence.zip --phase pr \
    --expected-source-commit <40-hex-commit> --output r62-evidence/pr
  python collect_r62_evidence.py --zip r62-live-evidence.zip --phase live \
    --expected-source-commit <40-hex-commit> --output r62-evidence/live

The destination can later be preserved at evidence/roads-r62/2026-11-21/{phase}.
--check-only validates without creating a destination or final manifest.

The frozen R6.2 browser script records FOUR screenshots per device (eight in
total), including the extra ward/bridge panel image. All are retained and hashed.
Homepage and unittest reports do not carry source_commit fields: their original
bytes are retained, and the manifest records their same-artifact binding without
inventing a per-report commit or overall status.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from zipfile import BadZipFile, ZipFile


LIVE_BASE = "https://mechgouki.github.io/luoyang-city/"
DOWNLOADS = {
    "all-roads/city-all-roads.svg", "all-roads/records.csv",
    "all-roads/records.json", "all-roads/coverage.csv", "all-roads/manifest.json",
    "downloads/luoyang-all-roads.zip",
}
SCREENSHOTS = ("whole-atlas", "palace-evidence", "ward-evidence", "ward-bridge-map")
RECORD_COUNT = 84
RECORD_GROUPS = {"legacy": 21, "documentary": 26, "palace": 11, "ward": 7, "gate": 14, "bridge": 5}
TEST_REPORTS = ("prosperity-semantic-tests.txt", "homepage-approved-v9-tests.txt")
ROAD_CHECKS = {
    "R6.1 entrance preserves its 21 records; complete catalog, coverage and exclusions are present",
    "All six categories filter correctly; exact documentary ID, persistent filters, no-result and reset work",
    "Palace and ward deep links open; a new search clears an older anchor and survives reload",
    "Source, inference and unknown layers persist; magnification and keyboard horizontal panning work",
    "Disconnected ZIP restores a ward deep link, searches a gate record, and preserves it after reload",
    "Native details open by an actual click without JavaScript",
    "All six advertised downloads were actually downloaded and matched release SHA-256",
}
APPROVAL_CHECKS = {
    "Desktop hero uses selected candidate 07 at 1672×941 with its verified source digest",
    "Both homepage URLs and published WebP files resolve over HTTPS or local HTTP",
    "390px mobile loads candidate 07 at 960×540 without cropping and opens the map",
}
HOMEPAGE_CHECKS = {
    "desktop homepage presents the large panorama, three questions, live map and research in order",
    "start exploration reaches the actual map; zoom, region, search and shared entity reload work",
    "the relocated research area keeps B1-B8 access and the working map overlay control",
    "existing research and about routes stay direct; the current release URL has the same homepage",
    "900px wrapped navigation stays above the panorama without overlap or horizontal overflow",
    "390px homepage, tap-to-map, regional filters and question navigation work without page overflow",
    "zero browser runtime errors during the homepage journeys",
} | {
    f"{q} question opens the intended evidence, survives reload and returns to the homepage"
    for q in ("yongning", "markets", "identity")
}


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def is_sha(value):
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def whitelist(phase):
    prefix = "live-" if phase == "live" else ""
    roads = prefix + "all-road-atlas-r62-browser"
    names = {"browser-runtime-digest.json"}
    for device in ("desktop", "mobile"):
        names.add(f"{roads}/{device}-report.json")
        names.update(f"{roads}/{device}-{kind}.png" for kind in SCREENSHOTS)
    names.update(prefix + folder + "/results.json" for folder in
                 ("homepage-v1-browser", "homepage-approved-v9-browser"))
    names.update({"live-http.json"} if phase == "live" else TEST_REPORTS)
    return roads, prefix, names


def validate(raw, phase, commit, roads, prefix):
    audits = []

    def read_json(name):
        try:
            return json.loads(raw[name])
        except (ValueError, UnicodeError) as error:
            raise ValueError(f"{name}: invalid JSON: {error}") from error

    road_downloads = {}
    for device in ("desktop", "mobile"):
        name = f"{roads}/{device}-report.json"
        report = read_json(name)
        demand(isinstance(report, dict), f"{name}: expected a JSON object")
        demand(report.get("status") == "passed", f"{name}: status is not passed")
        demand(report.get("device") == device, f"{name}: device does not match filename")
        demand(report.get("source_commit") == commit, f"{name}: source_commit mismatch")
        demand(report.get("errors") == [] and not report.get("error"), f"{name}: recorded errors")
        demand(not report.get("failure_context"), f"{name}: a failed browser context was recorded")
        demand(report.get("record_count") == RECORD_COUNT, f"{name}: complete record inventory differs")
        checks = report.get("checks", [])
        demand(len(checks) == len(ROAD_CHECKS) and set(checks) == ROAD_CHECKS,
               f"{name}: complete R6.2 browser checks missing or changed")
        viewport = {"width": 1440, "height": 960} if device == "desktop" else {"width": 390, "height": 844}
        demand(report.get("viewport") == viewport, f"{name}: expected viewport was not tested")
        shots = {f"{device}-{kind}.png" for kind in SCREENSHOTS}
        demand(set(report.get("screenshots", {})) == shots,
               f"{name}: expected exactly the four frozen R6.2 screenshots")
        for screenshot in shots:
            picture = raw[f"{roads}/{screenshot}"]
            demand(picture.startswith(b"\x89PNG\r\n\x1a\n"), f"{screenshot}: not a PNG")
            demand(is_sha(report["screenshots"][screenshot]) and digest(picture) == report["screenshots"][screenshot],
                   f"{screenshot}: screenshot SHA-256 differs from report")
        hashes = report.get("downloads", {})
        demand(isinstance(hashes, dict) and set(hashes) == DOWNLOADS and all(is_sha(v) for v in hashes.values()),
               f"{name}: incomplete or malformed six-download digest record")
        road_downloads[device] = hashes
        audits.append({"path": name, "reported_status": "passed", "source_commit": commit,
                       "screenshot_hashes_verified": len(SCREENSHOTS), "reported_download_hashes": hashes,
                       "record_count": report["record_count"], "viewport": viewport,
                       "checks": report["checks"]})
    demand(road_downloads["desktop"] == road_downloads["mobile"],
           "Desktop and mobile downloaded different road assets")

    for folder, expected, error_field in (
        ("homepage-v1-browser", HOMEPAGE_CHECKS, "runtime_errors"),
        ("homepage-approved-v9-browser", APPROVAL_CHECKS, "errors"),
    ):
        name = prefix + folder + "/results.json"
        report = read_json(name)
        demand(isinstance(report, dict), f"{name}: expected a JSON object")
        checks = report.get("checks", [])
        demand(report.get(error_field) == [], f"{name}: runtime errors or missing error field")
        demand(not report.get("error"), f"{name}: recorded error")
        demand(report.get("status") in (None, "passed"), f"{name}: non-passing status")
        for field in ("source_commit", "commit"):
            if field in report:
                demand(report[field] == commit, f"{name}: explicit {field} differs from expected commit")
        if folder == "homepage-v1-browser":
            demand(all(isinstance(c, dict) and c.get("status") == "passed" for c in checks),
                   f"{name}: a homepage check did not pass")
            names = [c.get("name") for c in checks]
        else:
            demand(all(isinstance(c, str) for c in checks), f"{name}: changed check schema")
            names = checks
        demand(len(names) == len(expected) and set(names) == expected,
               f"{name}: expected current homepage checks are incomplete or changed")
        if phase == "live":
            demand(report.get("base_url") == LIVE_BASE, f"{name}: unexpected live base URL")
        audits.append({"path": name, "reported_status": report.get("status"),
                       "reported_source_commit": report.get("source_commit"),
                       "validation": "complete_expected_checks_without_recorded_errors",
                       "recorded_check_count": len(checks), "base_url": report.get("base_url"),
                       "source_commit_binding": "same artifact as commit-checked R6.2 browser reports",
                       "note": "The original report's optional status/source_commit are recorded as supplied; absent fields are not fabricated."})

    runtime = read_json("browser-runtime-digest.json")
    demand(isinstance(runtime, list) and runtime and all(
        isinstance(v, str) and re.fullmatch(r".+@sha256:[a-f0-9]{64}", v) for v in runtime),
        "browser-runtime-digest.json: expected pinned image digest list")

    if phase == "pr":
        for name in TEST_REPORTS:
            body = raw[name].decode("utf-8-sig")
            match = re.search(r"(?m)^Ran ([1-9][0-9]*) tests? in [^\n]+\n\s*\nOK\s*\Z", body)
            demand(match is not None, f"{name}: no complete successful unittest summary")
            demand(not re.search(r"(?m)^(?:FAILED|ERROR:|FAIL:|Traceback)", body),
                   f"{name}: failure diagnostics present")
            markers = ({"test_prosperity_all_road_atlas_r62.AllRoadAtlas",
                        "test_all_known_road_families_have_evidence_records",
                        "test_local_widths_passage_components_and_unknowns_are_not_promoted",
                        "test_downloads_offline_bundle_and_predecessors",
                        "test_prosperity_road_atlas_r6.RoadAtlas"}
                       if name == TEST_REPORTS[0] else {"test_current_homepage_matches_selected_candidate_07"})
            demand(all(marker in body for marker in markers),
                   f"{name}: expected R6.2/old-R6/current-homepage test coverage absent")
            demand(int(match[1]) >= (218 if name == TEST_REPORTS[0] else 6),
                   f"{name}: incomplete regression suite count")
            audits.append({"path": name, "reported_result": "OK", "tests": int(match[1]),
                           "source_commit_binding": "same artifact as commit-checked road reports"})
    else:
        name = "live-http.json"
        report = read_json(name)
        demand(isinstance(report, dict), f"{name}: expected a JSON object")
        demand(report.get("status") == "passed", f"{name}: status is not passed")
        demand(report.get("commit") == commit, f"{name}: source commit mismatch")
        demand(report.get("base_url") == LIVE_BASE, f"{name}: unexpected live base URL")
        files = report.get("files", [])
        demand(isinstance(files, list) and files and all(isinstance(f, dict) for f in files) and
               len(files) == report.get("checked_files"), f"{name}: incomplete file count")
        demand(all(f.get("status") == "passed" and is_sha(f.get("sha256")) for f in files),
               f"{name}: a public file did not pass hash verification")
        lookup = {f["path"]: f for f in files}
        demand(len(lookup) == len(files), f"{name}: duplicate public file paths")
        for path, checksum in road_downloads["desktop"].items():
            demand(path in lookup and lookup[path]["sha256"] == checksum,
                   f"{name}: live HTTP and browser download hashes disagree for {path}")
        road = report.get("all_road_locations", {})
        demand(isinstance(road, dict) and road.get("status") == "passed" and road.get("source_commit") == commit,
               f"{name}: R6.2 verifier missing or did not pass for the expected commit")
        counts = road.get("counts", {})
        demand(isinstance(counts, dict) and counts.get("records") == RECORD_COUNT and counts.get("groups") == RECORD_GROUPS,
               f"{name}: R6.2 record/category counts differ")
        demand(counts.get("coverage") == 339 and counts.get("documentary_entities") == 21 and
               counts.get("bridge_entities") == 5 and counts.get("exclusions") == 13,
               f"{name}: complete source coverage counts differ")
        demand(road.get("downloads") == 6 and road.get("offline_members") == 8,
               f"{name}: complete downloads/offline bundle not verified")
        preservation = road.get("preservation", {})
        demand(isinstance(preservation, dict) and preservation.get("old_sources") == 21 and preservation.get("homepage") == "panorama-approved-v11 / 07",
               f"{name}: current homepage preservation result missing")
        expected_native = {"old_inner_records": 8, "old_outer_records": 11, "sima_native_parts": 6,
                           "gate_native_polygons": 3, "directional_arrow_stems": 6}
        demand(road.get("native_figure") == expected_native, f"{name}: original SVG geometry preservation not verified")
        expected_boundaries = {"ward_streets": 6, "unresolved_ward_road_class": 1,
                               "third_gate_passage_count": None, "source_gate_passage_bands": 3}
        demand(road.get("evidence_boundaries") == expected_boundaries,
               f"{name}: road/passage/phase evidence boundaries not verified")
        legacy = report.get("road_locations", {})
        demand(isinstance(legacy, dict) and legacy.get("status") == "passed" and legacy.get("source_commit") == commit and
               legacy.get("records") == 21 and legacy.get("supplements") == 3,
               f"{name}: old R6.1 verification missing or from another commit")
        audits.append({"path": name, "reported_status": "passed", "source_commit": commit,
                       "checked_files": report["checked_files"], "checked_at": report.get("checked_at"),
                       "all_road_locations": road, "six_browser_download_hashes_match_http": True})
    return audits, runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zip", required=True, type=Path, dest="archive")
    parser.add_argument("--phase", required=True, choices=("pr", "live"))
    parser.add_argument("--expected-source-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workflow-url", help="Recorded provenance only; not remotely verified by this script")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    commit = args.expected_source_commit.lower()
    demand(re.fullmatch(r"[a-f0-9]{40}", commit) is not None, "Expected source commit must be a full 40-hex SHA")
    archive = args.archive.resolve()
    output = args.output.absolute()
    demand(archive.is_file(), f"ZIP not found: {archive}")
    demand(not output.exists() and not output.is_symlink(), f"Refusing existing output: {output}")
    roads, prefix, allowed = whitelist(args.phase)
    with ZipFile(archive) as zipped:
        inventory = [i.filename for i in zipped.infolist() if not i.is_dir()]
        duplicates = sorted(n for n, count in Counter(inventory).items() if count > 1)
        demand(not duplicates, f"Ambiguous ZIP with duplicate member names: {duplicates}")
        missing = sorted(allowed - set(inventory))
        demand(not missing, "Required evidence missing: " + ", ".join(missing))
        raw = {name: zipped.read(name) for name in sorted(allowed)}
    audits, runtime = validate(raw, args.phase, commit, roads, prefix)
    metadata = {
        "schema": "luoyang-roads-r62-selected-evidence-v1",
        "phase": args.phase, "expected_source_commit": commit,
        "collection_validation": "passed_for_selected_evidence",
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_archive": {"name": archive.name, "bytes": archive.stat().st_size,
                          "sha256": file_digest(archive)},
        "workflow_url": args.workflow_url,
        "workflow_conclusion": None,
        "workflow_conclusion_note": "Workflow/job conclusions must be checked separately; this script validates only retained reports.",
        "browser_runtime_digests": runtime,
        "whitelist": sorted(allowed), "selected_files": len(raw),
        "excluded_archive_file_count": len(inventory) - len(raw),
        "road_screenshots": 2 * len(SCREENSHOTS), "report_validations": audits,
        "semantic_tests": ("Retained in this PR artifact." if args.phase == "pr" else
                           "The live job does not produce semantic-test TXT files; retain the PR build evidence separately."),
        "files": [{"path": name, "bytes": len(body), "sha256": digest(body)}
                  for name, body in sorted(raw.items())],
        "checksum_file": "SHA256SUMS",
        "checksum_scope": "All retained source files plus evidence-metadata.json; checksum file excludes itself.",
    }
    if args.check_only:
        print(json.dumps({"validation": "passed", "phase": args.phase, "source_commit": commit,
                          "selected_files": len(raw), "output_written": False}, ensure_ascii=False))
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".r62-evidence-", dir=output.parent))
    try:
        for name, body in raw.items():
            destination = staging / name  # name is from the fixed whitelist, never a ZIP-supplied path.
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
        meta_raw = (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode()
        (staging / "evidence-metadata.json").write_bytes(meta_raw)
        checksums = [(digest(body), name) for name, body in raw.items()]
        checksums.append((digest(meta_raw), "evidence-metadata.json"))
        (staging / "SHA256SUMS").write_text("".join(f"{sha}  {name}\n" for sha, name in
                                                    sorted(checksums, key=lambda item: item[1])))
        demand(not output.exists(), f"Output appeared while validating; refusing overwrite: {output}")
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    print(json.dumps({"validation": "passed", "phase": args.phase, "source_commit": commit,
                      "selected_files": len(raw), "road_screenshots": 2 * len(SCREENSHOTS),
                      "metadata": str(output / "evidence-metadata.json")}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, BadZipFile) as error:
        print(f"REFUSED: {error}\nNo final evidence manifest was produced.", file=sys.stderr)
        raise SystemExit(2)
