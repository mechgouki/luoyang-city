#!/usr/bin/env python3
"""Check retained browser downloads against that run's actual Pages bytes.

Read-only: no network, no browser launch, no reconstruction of missing downloads.
Use the PR's Pages manifest with PR reports; production Pages with both production
build and live reports. This is evidence consistency, not a replacement for CI.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def need(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", required=True)
    p.add_argument("--pages", required=True, help="Pages ingest manifest")
    p.add_argument("--evidence", required=True, help="Browser build/live ingest manifest")
    p.add_argument("--report-prefix", required=True, help="panorama-v14-browser or live-panorama-v14-browser")
    p.add_argument("--expected-commit", required=True)
    args = p.parse_args()
    root = Path(args.store)
    pages = json.loads(Path(args.pages).read_text())
    ev = json.loads(Path(args.evidence).read_text())
    pe = {x["path"]: x for x in pages["members"]}
    ee = {x["path"]: x for x in ev["members"]}

    def raw(entry):
        relative = PurePosixPath(entry["retained_path"])
        need(not relative.is_absolute() and ".." not in relative.parts, "Unsafe retained path")
        path = root / relative
        data = path.read_bytes()
        need(len(data) == entry["bytes"], "Retained byte count mismatch")
        need(hashlib.sha256(data).hexdigest() == entry["sha256"], "Retained SHA256 mismatch")
        blob = hashlib.sha1(("blob %d\0" % len(data)).encode() + data).hexdigest()
        need(blob == entry["git_blob_sha1"], "Retained Git blob mismatch")
        return data

    info = json.loads(raw(pe["build-info.json"]))
    meta = info["panorama_review_v14"]
    need(info["source_commit"] == meta["source_commit"] == args.expected_commit, "Wrong Pages source commit")
    expected = set(meta["download_files"])
    summaries = []
    for device in ["desktop", "mobile"]:
        report_path = args.report_prefix.rstrip("/") + "/" + device + "-report.json"
        report = json.loads(raw(ee[report_path]))
        need(report["status"] == "passed" and not report.get("errors"), "Browser report not passed")
        need(report["source_commit"] == args.expected_commit, "Browser/Pages commit mismatch")
        need(set(report["downloads"]) == set(report["retained_downloads"]) == expected, "Incomplete browser download set")
        attempts = report["download_attempts"]
        passed = [x for x in attempts if x["status"] == "passed"]
        need({x["path"] for x in passed} == expected, "Missing actual click success records")
        for path in sorted(expected):
            download = report["retained_downloads"][path]
            retained = str(PurePosixPath(report_path).parent / PurePosixPath(download["retained_path"]))
            item = ee[retained]
            raw(item)
            raw(pe[path])
            wanted = info["files_sha256"][path]
            need(item["sha256"] == download["sha256"] == report["downloads"][path] == wanted == pe[path]["sha256"], "Download SHA256 mismatch: " + path)
            need(item["bytes"] == download["bytes"] == pe[path]["bytes"], "Download byte count mismatch: " + path)
        for name, digest in report["screenshots"].items():
            entry = ee[str(PurePosixPath(report_path).parent / name)]
            raw(entry)
            need(entry["sha256"] == digest, "Screenshot mismatch: " + name)
        summaries.append({"device": device, "report": report_path, "unique_downloads": len(expected),
            "actual_click_attempts": len(attempts), "passed_click_attempts": len(passed),
            "screenshots": len(report["screenshots"]), "status": "passed"})
    print(json.dumps({"schema": "luoyang-browser-download-cas-check-v1", "status": "passed",
        "source_commit": args.expected_commit, "pages_label": pages["label"],
        "evidence_label": ev["label"], "publication_status": meta["status"],
        "review_status": meta["review_status"], "devices": summaries,
        "note": "Checks retained original reports and bytes only; does not rerun browser interactions or certify image geometry."}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
