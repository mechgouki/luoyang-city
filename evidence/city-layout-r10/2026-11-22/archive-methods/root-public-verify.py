#!/usr/bin/env python3
"""Read back the actual published R10 files without browser or local build caches."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.request

BASE = "https://mechgouki.github.io/luoyang-city/"


def request(path):
    req = urllib.request.Request(BASE + path, headers={"Cache-Control": "no-cache", "User-Agent": "Luoyang-R10-acceptance"})
    with urllib.request.urlopen(req, timeout=45) as response:
        assert response.status == 200, (path, response.status)
        assert response.url.startswith(BASE), (path, "Unexpected host redirect")
        raw = response.read()
        headers = {key: response.headers[key] for key in ("Content-Type", "Content-Length", "ETag", "Last-Modified", "Date") if key in response.headers}
    return raw, headers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    raw_info, info_headers = request("build-info.json")
    info = json.loads(raw_info)
    assert info["source_commit"] == args.commit, (info["source_commit"], args.commit)
    meta = info["city_layout_r10"]
    assert meta["source_commit"] == args.commit and meta["version"] == "city-layout-r10"
    downloads = set(meta["download_files"])
    assert len(downloads) == 21
    assert meta["counts"]["regions"] == 11 and meta["pdf_pages"] == 16
    (args.output / "build-info.json").write_bytes(raw_info)
    paths = sorted(downloads | set(meta["files_sha256"]) | {meta["page"], "index.html", "v3.0-dual.html", "release.json"})

    def check(path):
        safe = PurePosixPath(path)
        assert not safe.is_absolute() and ".." not in safe.parts and "?" not in path and "#" not in path
        raw, headers = request(path)
        actual = hashlib.sha256(raw).hexdigest()
        assert actual == info["files_sha256"][path], (path, "Public file hash differs from published build-info")
        relative = ("downloads/" if path in downloads else "resources/") + path
        destination = args.output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        return {"path": path, "url": BASE + path, "status": "passed", "bytes": len(raw), "sha256": actual, "retained_path": relative, "headers": headers}

    rows = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs = {pool.submit(check, path): path for path in paths}
        for job in as_completed(jobs):
            rows.append(job.result())
    second, _ = request("build-info.json")
    assert second == raw_info, "Published release changed during HTTPS readback"
    result = {"schema": "luoyang-r10-root-public-https-v1", "status": "passed", "commit": args.commit,
              "checked_at_utc": datetime.now(timezone.utc).isoformat(), "base_url": BASE,
              "build_info_sha256": hashlib.sha256(raw_info).hexdigest(), "build_info_headers": info_headers,
              "unique_download_files": len(downloads), "public_files": len(rows), "counts": meta["counts"],
              "files": sorted(rows, key=lambda row: row["path"]), "errors": []}
    (args.output / "https-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "commit", "public_files", "unique_download_files")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
