"""Capture and independently check the actual R7 production HTTP responses.

This script reads public HTTPS only. It does not substitute local build products
for missing responses and does not claim that CI or browser acceptance passed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import quote
from urllib.request import Request, urlopen
from zipfile import ZipFile
from zoneinfo import ZoneInfo


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def request(base, path):
    url = base + quote(path, safe="/")
    with urlopen(Request(url, headers={"User-Agent": "Luoyang-R7-acceptance/1.1"}), timeout=40) as response:
        raw = response.read()
        assert response.status == 200
        assert response.geturl() == url, (path, "Unexpected redirected response")
        return raw, dict(path=path or "/", url=url, final_url=response.geturl(), status=response.status,
                         bytes=len(raw), sha256=digest(raw), headers=dict(response.headers.items()))


def verify_readings(raw, meta, commit):
    data = json.loads(raw)
    assert data["source_commit"] == commit
    assert data["research_version"] == "R7.1"
    assert data["implementation_version"] == "city-nodes-r7.1"
    assert data["homepage_revision"] == "panorama-approved-v12"
    assert data["target_years"] == [516, 528]
    actual = dict(nodes=len(data["nodes"]), findings=sum(len(n["findings"]) for n in data["nodes"]),
                  relations=sum(len(n["relations"]) for n in data["nodes"]), segments=len(data["segments"]),
                  waters=len(data["waters"]), entities_indexed=len(data["entity_index"]),
                  roads_indexed=len(data["road_index"]), waters_indexed=len(data["water_index"]))
    assert actual == data["counts"] == meta["counts"]
    assert actual == dict(nodes=4, findings=32, relations=32, segments=28, waters=9,
                         entities_indexed=339, roads_indexed=84, waters_indexed=34)
    for field in ("nodes", "segments", "waters", "entity_index", "road_index", "water_index"):
        ids = [row["id"] for row in data[field]]
        assert len(ids) == len(set(ids)), (field, "Duplicate identifiers")
    assert data["new_historical_coordinates"] == data["new_shoreline_geometries"] == 0
    assert data["source_frames_registered_together"] is False
    return data, actual


def verify_csv(raw, data):
    assert raw.startswith(b"\xef\xbb\xbf"), "CSV lost its declared UTF-8 BOM"
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    assert reader.fieldnames == data["csv_fields"], "CSV fields differ from JSON"
    rows = list(reader)
    assert len(rows) == 28 == len(data["segments"])
    for actual, expected in zip(rows, data["segments"]):
        assert None not in actual, "Unexpected surplus CSV fields"
        for field in reader.fieldnames:
            value = expected.get(field, "")
            if value is None or isinstance(value, (list, dict)):
                assert json.loads(actual[field]) == value, (expected["id"], field, "CSV lost structured content")
            else:
                assert actual[field] == str(value), (expected["id"], field, "CSV value changed")
    return dict(rows=len(rows), columns=len(reader.fieldnames), exact_json_values_preserved=True,
                encoding="UTF-8 BOM", unknown_values_preserved=True)


def verify_zip(raw, meta, bodies):
    with ZipFile(io.BytesIO(raw)) as archive:
        members = archive.namelist()
        assert len(members) == len(set(members)), "Duplicate ZIP member"
        assert all(not PurePosixPath(p).is_absolute() and ".." not in PurePosixPath(p).parts for p in members)
        assert archive.testzip() is None, "ZIP CRC failed"
        expected = set(meta["files_sha256"]) | {"index.html", meta["manifest"]}
        assert set(members) == expected, ("ZIP member mismatch", sorted(expected - set(members)), sorted(set(members) - expected))
        for path in members:
            if path != "index.html":
                assert archive.read(path) == bodies[path], (path, "ZIP differs from actual HTTP response")
        html = archive.read("index.html").decode("utf-8")
        assert 'id="overview"' in html and 'id="panorama"' in html and 'id="register"' in html
        for row in json.loads(bodies["city-nodes/readings.json"])["segments"]:
            assert 'id="segment-' + row["id"] + '"' in html, (row["id"], "Missing offline source record")
        assert meta["hero"]["full"] in members and meta["hero"]["small"] in members
        return dict(members=len(members), paths=sorted(members), crc_passed=True,
                    public_members_byte_identical=True, offline_segment_anchors=28)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--base-url", default="https://mechgouki.github.io/luoyang-city/")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    assert re.fullmatch(r"[0-9a-f]{40}", args.commit), "Expected exact full source commit"
    base = args.base_url.rstrip("/") + "/"
    assert base.startswith("https://")
    dest = Path(args.output)
    bodies_dir = dest / "http-responses"
    bodies_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
    opening, opening_entry = request(base, "build-info.json")
    info = json.loads(opening)
    assert info["source_commit"] == args.commit, "Production serves another commit"
    meta = info["city_nodes_r7"]
    assert meta["source_commit"] == args.commit
    (bodies_dir / "build-info.json").write_bytes(opening)
    opening_entry["stored_as"] = "http-responses/build-info.json"
    records = [opening_entry]
    approval, approval_entry = request(base, "homepage/approval-v12.json")
    assert digest(approval) == info["files_sha256"]["homepage/approval-v12.json"]
    hero = json.loads(approval)["hero"]
    paths = {"", "index.html", "v3.0-dual.html", "release.json", meta["page"], meta["manifest"], meta["bundle"],
             *meta["files_sha256"], "luoyang-all-roads.html", "all-roads/city-all-roads.svg", "all-roads/records.json",
             "all-roads/records.csv", "all-roads/manifest.json", "downloads/luoyang-all-roads.zip",
             "luoyang-water-atlas.html", "water-locations.csv", "water-location-data.json",
             "prosperity-city-atlas.html", "city-atlas/atlas.json", "prosperity-city-panorama.html"}
    paths.update(hero[k] for k in ("asset", "small_asset", "layout_asset"))
    paths.update(row["archive"] for row in meta["predecessor_homepage"].values())
    paths.add(meta["predecessor_road_page"]["archive"])
    bodies = {"homepage/approval-v12.json": approval}
    (bodies_dir / "homepage").mkdir(parents=True, exist_ok=True)
    (bodies_dir / "homepage/approval-v12.json").write_bytes(approval)
    approval_entry.update(stored_as="http-responses/homepage/approval-v12.json",
                          release_sha256=info["files_sha256"]["homepage/approval-v12.json"], hash_matches=True)
    records.append(approval_entry)

    def capture(path):
        content, report = request(base, path)
        expected = info["files_sha256"][path or "index.html"]
        assert report["sha256"] == expected, (path, "Release hash differs from actual response")
        target = bodies_dir / (path or "site-root.html")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        report.update(stored_as=str(target.relative_to(dest)), release_sha256=expected, hash_matches=True)
        return path, content, report

    with ThreadPoolExecutor(max_workers=4) as pool:
        for path, content, report in pool.map(capture, sorted(paths)):
            bodies[path] = content
            records.append(report)
    assert json.loads(bodies["release.json"])["source_commit"] == args.commit
    manifest = json.loads(bodies[meta["manifest"]])
    assert manifest == meta, "Actual manifest differs from opening build-info"
    for path, expected in manifest["files_sha256"].items():
        assert digest(bodies[path]) == expected == info["files_sha256"][path]
    data, counts = verify_readings(bodies["city-nodes/readings.json"], meta, args.commit)
    csv_result = verify_csv(bodies["city-nodes/segments.csv"], data)
    zip_result = verify_zip(bodies[meta["bundle"]], meta, bodies)
    assert bodies[meta["hero"]["full"]] == bodies[hero["asset"]]
    assert bodies[meta["hero"]["small"]] == bodies[hero["small_asset"]]
    assert digest(bodies[hero["asset"]]) == "d8d5be74d123b5eeaac50ce68955787e26686b92c1a30031f6c3289692fbf4c2"
    assert digest(bodies[hero["small_asset"]]) == "eb836bc7ba458ae392c313c030ee7ed9654bd838bb46b62e8fdf418e5e369f21"

    closing, closing_entry = request(base, "build-info.json")
    (bodies_dir / "build-info-closing.json").write_bytes(closing)
    closing_entry["stored_as"] = "http-responses/build-info-closing.json"
    records.append(closing_entry)
    assert json.loads(closing)["source_commit"] == args.commit
    assert closing == opening, "Deployment changed during capture; repeat against one settled release"
    finished = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
    document = dict(schema="luoyang-r7-production-capture-v2", started_at_beijing=started, finished_at_beijing=finished,
                    base_url=base, source_commit=args.commit, status="passed", response_count=len(records),
                    distinct_urls=len({r["url"] for r in records}), records=records,
                    checks=dict(opening_closing_build_info_byte_identical=True, commit_consistent=True,
                                manifest_matches_build_info=True, counts=counts, csv=csv_result, zip=zip_result,
                                v12_guide_images_match_approved_public_images=True,
                                v12_fixed_approved_fingerprints_preserved=True),
                    meaning="Every saved body came from its recorded HTTPS response. This verifies selected public content; CI/browser results must be retained separately.")
    (dest / "http-capture.json").write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: document[k] for k in ("source_commit", "status", "response_count", "distinct_urls", "checks")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
