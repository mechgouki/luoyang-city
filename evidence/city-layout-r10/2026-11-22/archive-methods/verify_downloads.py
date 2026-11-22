#!/usr/bin/env python3
"""Verify retained R10 downloads across production build/live/HTTPS evidence."""
import argparse
import hashlib
import json
from pathlib import Path


def load(path):
    return json.loads(path.read_text())


def check_report(directory, device, commit, expected_paths):
    report = load(directory / (device + "-report.json"))
    assert report["status"] == "passed" and not report["errors"]
    assert report["source_commit"] == commit
    assert set(report["downloads"]) == set(report["retained_downloads"]) == set(expected_paths)
    assert report["pdf_pages"] == 16
    for path, expected_sha in report["downloads"].items():
        retained = report["retained_downloads"][path]
        actual = directory / retained["retained_path"]
        assert actual.resolve().is_relative_to(directory.resolve()), path
        raw = actual.read_bytes()
        assert len(raw) == retained["bytes"]
        assert hashlib.sha256(raw).hexdigest() == expected_sha == retained["sha256"], path
    for name, expected_sha in report["screenshots"].items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected_sha, name
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--build-info", type=Path, required=True)
    p.add_argument("--main-build", type=Path, required=True)
    p.add_argument("--main-live", type=Path, required=True)
    p.add_argument("--live-http", type=Path, required=True)
    p.add_argument("--pr", type=Path)
    p.add_argument("--pr-commit")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    info, http = load(a.build_info), load(a.live_http)
    meta = info["city_layout_r10"]
    commit = info["source_commit"]
    paths = meta["download_files"]
    assert len(paths) == 21 and len(set(paths)) == 21
    assert http["status"] == "passed" and http["commit"] == commit
    http_files = {row["path"]: row for row in http["files"]}
    streams = {}
    for phase, directory in (("production-build", a.main_build), ("production-live", a.main_live)):
        for device in ("desktop", "mobile"):
            streams[phase + "-" + device] = check_report(directory, device, commit, paths)
    rows = []
    for path in paths:
        expected = info["files_sha256"][path]
        assert http_files[path]["status"] == "passed" and http_files[path]["sha256"] == expected, path
        hashes = {name: report["downloads"][path] for name, report in streams.items()}
        assert set(hashes.values()) == {expected}, (path, hashes, expected)
        rows.append({"path": path, "sha256": expected, "production_streams": hashes, "https_sha256": http_files[path]["sha256"], "status": "passed"})
    pr = None
    if a.pr:
        assert a.pr_commit
        reports = {device: check_report(a.pr, device, a.pr_commit, paths) for device in ("desktop", "mobile")}
        assert reports["desktop"]["downloads"] == reports["mobile"]["downloads"]
        pr = {"commit": a.pr_commit, "desktop_mobile_download_hashes_equal": True,
              "download_files": len(paths), "actual_download_count": 2 * len(paths),
              "cross_commit_limit": "PR and production embed different source_commit values. Production assets are compared within the final release; PR assets are compared within the tested PR merge ref."}
    result = {"schema": "luoyang-r10-download-cross-stage-v1", "status": "passed", "production_commit": commit,
              "unique_download_files": len(paths), "actual_downloads_per_build_or_live_phase": 2 * len(paths),
              "production_build_and_live_actual_downloads": 4 * len(paths),
              "production_screenshot_counts": {name: len(report["screenshots"]) for name, report in streams.items()},
              "retained_download_bytes_verified": True, "retained_screenshot_bytes_verified": True,
              "production_build_desktop_mobile_live_desktop_mobile_and_https_hashes_equal": True,
              "pdf_pages": 16, "files": rows, "pr": pr, "errors": []}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "production_commit", "unique_download_files", "production_build_and_live_actual_downloads")}))


if __name__ == "__main__":
    main()
