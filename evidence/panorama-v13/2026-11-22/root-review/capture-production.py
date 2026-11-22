"""Independently capture actual V13 public responses from one settled release.

All saved bodies come from recorded HTTPS GETs. CI and browser acceptance are
separate evidence; local generated files never substitute for missing responses.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def request(base, path):
    url = base + quote(path, safe="/")
    with urlopen(Request(url, headers={"User-Agent": "Luoyang-V13-public-acceptance/1.0"}), timeout=40) as response:
        raw = response.read()
        assert response.status == 200 and response.geturl() == url, (path, "Unexpected public response")
        return raw, dict(path=path or "/", url=url, final_url=response.geturl(), status=response.status,
                         bytes=len(raw), sha256=digest(raw), headers=dict(response.headers.items()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--base-url", default="https://mechgouki.github.io/luoyang-city/")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    assert re.fullmatch(r"[0-9a-f]{40}", args.commit)
    base = args.base_url.rstrip("/") + "/"
    assert base.startswith("https://")
    dest = Path(args.output)
    dest.mkdir(parents=True, exist_ok=True)
    saved = dest / "http-responses"
    saved.mkdir(exist_ok=True)
    started = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
    opening, opening_entry = request(base, "build-info.json")
    info = json.loads(opening)
    assert info["source_commit"] == args.commit, "Another source commit is live"
    meta = info["panorama_review_v13"]
    assert meta["source_commit"] == args.commit
    assert meta["homepage_replacement_approved"] is False
    assert meta["candidate_revision"] == "panorama-candidate-v13"
    assert meta["homepage_revision"] == "panorama-approved-v12"
    (saved / "build-info.json").write_bytes(opening)
    opening_entry["stored_as"] = "http-responses/build-info.json"
    records = [opening_entry]

    approval, approval_entry = request(base, "homepage/approval-v12.json")
    assert digest(approval) == info["files_sha256"]["homepage/approval-v12.json"]
    hero = json.loads(approval)["hero"]
    (saved / "homepage").mkdir(exist_ok=True)
    (saved / "homepage/approval-v12.json").write_bytes(approval)
    approval_entry.update(stored_as="http-responses/homepage/approval-v12.json", hash_matches=True,
                          release_sha256=info["files_sha256"]["homepage/approval-v12.json"])
    records.append(approval_entry)
    paths = {"", "index.html", "v3.0-dual.html", "release.json", meta["page"], meta["manifest"],
             *meta["files_sha256"], *meta["download_files"],
             "luoyang-city-nodes.html", "city-nodes/readings.json", "city-nodes/segments.csv",
             "city-nodes/manifest.json", "downloads/luoyang-city-nodes.zip"}
    paths.update(hero[k] for k in ("asset", "small_asset", "layout_asset"))
    paths.update(row["archive"] for row in meta["predecessor_homepage"].values())
    bodies = {"homepage/approval-v12.json": approval}

    def capture(path):
        raw, entry = request(base, path)
        expected = info["files_sha256"][path or "index.html"]
        assert digest(raw) == expected, (path, "Public bytes differ from declared release")
        target = saved / (path or "site-root.html")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        entry.update(stored_as=str(target.relative_to(dest)), release_sha256=expected, hash_matches=True)
        return path, raw, entry

    with ThreadPoolExecutor(max_workers=4) as pool:
        for path, raw, entry in pool.map(capture, sorted(paths)):
            bodies[path] = raw
            records.append(entry)
    assert json.loads(bodies[meta["manifest"]]) == meta
    review = json.loads(bodies[meta["record"]])
    candidate = review["candidate"]
    assert review["source_commit"] == args.commit
    assert review["homepage_replacement_approved"] is candidate["homepage_replacement_approved"] is False
    assert candidate["historical_gate_reconstruction_completed"] is False
    assert candidate["source_png_sha256"] == "1808eeb9c2a25a2c22777ae8fba7ae437c983b091de5674b094d10e47cb1c0b1"
    assert len(candidate["changes"]) == meta["change_count"] == 7
    assert len(meta["download_files"]) == 7
    assert json.loads(bodies["release.json"])["source_commit"] == args.commit
    selected = meta["images"]["v13"]
    assert digest(bodies[selected["full"]]) == "ddded211c38b2c27e2268c74d22a9151f861ac335e90118c5d244a2effbb9a78"
    assert digest(bodies[selected["small"]]) == "4ab2fc67ad262d853ed07442d2f26493231cebe5e1e66df97cc157dba7205678"
    assert (selected["width"], selected["height"], selected["small_width"], selected["small_height"]) == (1671, 941, 960, 541)
    assert bodies[meta["images"]["v12"]["full"]] == bodies[hero["asset"]]
    assert bodies[meta["images"]["v12"]["small"]] == bodies[hero["small_asset"]]
    assert digest(bodies[hero["asset"]]) == "d8d5be74d123b5eeaac50ce68955787e26686b92c1a30031f6c3289692fbf4c2"
    assert digest(bodies[hero["small_asset"]]) == "eb836bc7ba458ae392c313c030ee7ed9654bd838bb46b62e8fdf418e5e369f21"
    final_review = json.loads(bodies["panorama-v13/candidate-review.json"])
    assert final_review["source_png_sha256"] == candidate["source_png_sha256"]
    assert final_review["homepage_replacement_approved"] is False
    assert final_review["historical_gate_reconstruction_completed"] is False
    assert final_review["review_status"] == "accepted_for_user_review_with_known_limits"
    for path in ("index.html", "v3.0-dual.html"):
        assert bodies[path].count(b'id="r8-panorama-entry"') == 1
        assert b'data-hero-revision="panorama-approved-v12"' in bodies[path]
        assert b'panorama-candidate-v13' not in bodies[path]
    r7 = json.loads(bodies["city-nodes/readings.json"])
    assert r7["source_commit"] == args.commit and r7["counts"]["nodes"] == 4 and r7["counts"]["segments"] == 28
    assert r7["source_frames_registered_together"] is False
    assert review["new_ancient_coordinates"] == review["new_shoreline_geometries"] == 0
    closing, closing_entry = request(base, "build-info.json")
    (saved / "build-info-closing.json").write_bytes(closing)
    closing_entry["stored_as"] = "http-responses/build-info-closing.json"
    records.append(closing_entry)
    assert closing == opening, "Release changed during capture"
    result = dict(schema="luoyang-v13-production-capture-v1", status="passed", source_commit=args.commit,
                  started_at_beijing=started, finished_at_beijing=datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
                  base_url=base, response_count=len(records), distinct_urls=len({r["url"] for r in records}), records=records,
                  checks=dict(opening_closing_build_info_byte_identical=True, manifest_matches_build_info=True,
                              selected_pass02_identity_verified=True, candidate_changes=7, advertised_downloads=7,
                              v12_fixed_approved_fingerprints_preserved=True, v12_still_homepage=True,
                              historical_gate_reconstruction_completed=False, homepage_replacement_approved=False,
                              r7_nodes=4, r7_segments=28, new_ancient_coordinates=0, new_shoreline_geometries=0),
                  meaning="Saved bodies are actual public responses; full CI and browser reports are separate evidence.")
    (dest / "http-capture.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k:result[k] for k in ("status", "source_commit", "response_count", "distinct_urls", "checks")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
