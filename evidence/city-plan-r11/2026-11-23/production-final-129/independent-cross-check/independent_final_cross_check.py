#!/usr/bin/env python3
"""Read-only R11 final release byte/report cross-check, with retained methods.

The four browser streams retain downloaded bytes and screenshots. The CI HTTPS
report retains response hashes; root-public retains independently read-back
bytes. This script makes that distinction explicit and never rewrites evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from pypdf import PdfReader


def load(path):
    return json.loads(path.read_text())


def identity(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--incoming", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checked-at-utc", required=True)
    args = parser.parse_args()
    incoming, out = args.incoming.resolve(), args.output.resolve()
    assert not out.is_relative_to(incoming), "Output must not modify frozen evidence"
    out.mkdir(parents=True, exist_ok=True)
    helper = Path(__file__).with_name("verify_downloads.py")
    paths = {
        "build_info": incoming / "root-public/public/build-info.json",
        "build_browser": incoming / "artifacts/city-plan-r11-browser",
        "live_browser": incoming / "live-artifacts/live-city-plan-r11-browser",
        "https_report": incoming / "live-artifacts/live-http.json",
        "root_public": incoming / "root-public/public",
        "root_report": incoming / "root-public/public-readback-report.json",
    }
    helper_out = out / "browser-https-cross-check.json"
    command = [sys.executable, str(helper), "--build-info", str(paths["build_info"]),
               "--main-build", str(paths["build_browser"]),
               "--main-live", str(paths["live_browser"]),
               "--live-http", str(paths["https_report"]),
               "--output", str(helper_out)]
    run = subprocess.run(command, check=True, capture_output=True, text=True)
    (out / "verify-downloads-stdout.txt").write_text(run.stdout)
    assert not run.stderr, run.stderr

    info = load(paths["build_info"])
    http = load(paths["https_report"])
    root = load(paths["root_report"])
    helper_result = load(helper_out)
    commit = "129abaee724870ec00bc25c6e2fd2998a215063b"
    pdf_hash = "2466af8e41776be7731a99e35bf9e417faf035e16116c7d6ee475c2927047fc6"
    assert info["source_commit"] == http["commit"] == root["source_commit"] == commit
    assert http["status"] == root["status"] == helper_result["status"] == "passed"
    download_paths = info["city_plan_r11"]["download_files"]
    assert len(download_paths) == len(set(download_paths)) == 26
    http_by_path = {r["path"]: r for r in http["files"]}
    assert len(http_by_path) == len(http["files"]) == http["checked_files"]
    for path, row in http_by_path.items():
        assert row["status"] == "passed", path
        assert row["sha256"] == info["files_sha256"][path], path
    assert http["http_retries"] == []

    root_by_path = {r["path"]: r for r in root["public_files"]}
    assert len(root_by_path) == len(root["public_files"])
    root_actual = {}
    for path, row in root_by_path.items():
        actual = identity(paths["root_public"] / path)
        assert actual["bytes"] == row["bytes"], path
        assert actual["sha256"] == row["sha256"] == info["files_sha256"][path], path
        assert row["status"] == "passed"
        assert http_by_path[path]["sha256"] == actual["sha256"], path
        root_actual[path] = actual

    streams = {}
    evidence_reports = []
    tower_id = "r11-yongning-YN11-TOWER-PLINTH"
    for phase, directory in (("production-build", paths["build_browser"]),
                             ("production-live", paths["live_browser"])):
        for device in ("desktop", "mobile"):
            report_path = directory / (device + "-report.json")
            report = load(report_path)
            evidence_reports.append(identity(report_path))
            assert report["status"] == "passed" and report["errors"] == []
            assert report["source_commit"] == commit
            assert len(report["checks"]) == 7
            assert len(report["downloads"]) == len(report["retained_downloads"]) == 26
            attempts = report["download_attempts"]
            assert len(attempts) == 26
            assert {r["path"] for r in attempts} == set(download_paths)
            assert all(r["status"] == "passed" and r["click_delay_ms"] == 150 for r in attempts)
            assert len(report["screenshots"]) == 5
            assert report["pdf"]["pages"] == 17
            assert report["pdf"]["sha256"] == pdf_hash
            assert report["pdf"]["all_fonts_embedded"] is True
            assert report["offline_network_disabled"] is True
            assert report["offline_network_requests"] == []
            hit = report["tower_hit_test"]["selected_point"]
            assert hit["hit_tag"] == "path" and hit["hit_feature"] == tower_id
            assert hit["hit_label"] is None and hit["target_box"]["width"] >= 50
            assert report["tower_hit_test"]["labels_visible"] is False
            label_hit = report["tower_hit_test"]["independent_label"]
            assert label_hit["hit_label"] == label_hit["id"]
            assert label_hit["hit_tag"] == "text" and label_hit["hit_feature"] is None
            assert any("hit-verified tower-polygon click" in text for text in report["checks"])
            streams[phase + "-" + device] = {
                "status": "passed", "source_commit": commit,
                "check_groups": len(report["checks"]), "checks": report["checks"],
                "actual_download_count": len(report["downloads"]),
                "single_attempt_paced_click_count": len(attempts),
                "retained_screenshot_count": len(report["screenshots"]),
                "elapsed_seconds": report["elapsed_seconds"],
                "pdf_pages": report["pdf"]["pages"], "pdf_sha256": report["pdf"]["sha256"],
                "all_fonts_embedded": report["pdf"]["all_fonts_embedded"],
                "tower_hit_test": report["tower_hit_test"],
                "tower_own_visible_path_hit_assertions_passed": True,
                "independent_label_hit_assertions_passed": True,
                "strict_post_click_selection_check_group_passed": True,
                "offline_network_disabled": True, "offline_network_requests": [],
            }

    rows = []
    for row in helper_result["files"]:
        path = row["path"]
        assert path in root_actual
        assert root_actual[path]["sha256"] == row["sha256"]
        rows.append({**row, "root_independent_public_sha256": root_actual[path]["sha256"],
                     "root_retained_bytes": root_actual[path]["bytes"],
                     "four_browser_streams_ci_https_record_root_actual_bytes_equal": True})

    pdf = paths["root_public"] / "downloads/city-plan-r11.pdf"
    pdf_reader = PdfReader(pdf)
    assert len(pdf_reader.pages) == 17
    assert commit in pdf_reader.metadata.get("/Keywords", "")
    assert identity(pdf)["sha256"] == pdf_hash
    result = {
        "schema": "luoyang-r11-final-independent-cross-check-v1",
        "status": "passed", "source_commit": commit,
        "checked_at_utc": args.checked_at_utc,
        "scope": "Final production only. Four retained browser download streams are rehashed; CI HTTPS hash records are matched to release metadata; root independent public retained bytes are rehashed. This is not a new browser or network run.",
        "PUBLIC_COUNT": http["checked_files"],
        "ci_https_actual_report_rows": len(http["files"]),
        "ci_https_all_rows_passed_and_match_build_info": True,
        "ci_https_http_retries": http["http_retries"],
        "root_independent_public_files_rehashed": len(root_actual),
        "unique_download_files": len(download_paths),
        "four_browser_actual_downloads_rehashed": 4 * len(download_paths),
        "four_browser_screenshots_rehashed": sum(s["retained_screenshot_count"] for s in streams.values()),
        "four_browser_streams_ci_https_record_root_actual_bytes_equal": True,
        "streams": streams,
        "pdf": {**identity(pdf), "pages_independently_parsed": len(pdf_reader.pages),
                "metadata_commit_matches_final_release": True},
        "files": rows,
        "source_evidence": [identity(paths["build_info"]), identity(paths["https_report"]),
                            identity(paths["root_report"])] + evidence_reports,
        "retained_methods": [identity(helper), identity(Path(__file__))],
        "helper_result": identity(helper_out),
        "helper_command": command,
        "frozen_archive_inputs_modified": False,
        "repository_modified": False,
        "errors": [],
    }
    output = out / "final-independent-cross-check.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "PUBLIC_COUNT": result["PUBLIC_COUNT"],
                      "actual_downloads": result["four_browser_actual_downloads_rehashed"],
                      "screenshots": result["four_browser_screenshots_rehashed"],
                      "root_actual_files": result["root_independent_public_files_rehashed"],
                      "pdf_pages": len(pdf_reader.pages), "result": identity(output)},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
