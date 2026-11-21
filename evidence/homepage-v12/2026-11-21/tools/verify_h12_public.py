#!/usr/bin/env python3
"""Read back the approved V12 homepage from the formal HTTPS site.

Usage:
    python verify_h12_public.py --commit FULL_MAIN_SHA --output-dir NEW_DIRECTORY

This is a read-only publication check. It never builds, deploys, changes repository
files, or substitutes local assets for HTTP responses. Repository source files
are used only as validators and are checked against the exact requested commit.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time
import traceback
from urllib.error import HTTPError
from zipfile import ZipFile


BASE = "https://mechgouki.github.io/luoyang-city/"
GROUPS = {"legacy": 21, "documentary": 26, "palace": 11,
          "ward": 7, "gate": 14, "bridge": 5}
REFERENCE_FILES = (
    "tools/live_http.py", "tools/homepage_artwork_v10.py",
    "web/homepage-full-frame-v12.css",
)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_path(path):
    if (not isinstance(path, str) or not path or "\\" in path or "\x00" in path
            or "?" in path or "#" in path):
        raise ValueError(f"Unsafe relative resource path: {path!r}")
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or ":" in parsed.parts[0] or any(p in {"", ".", ".."} for p in path.split("/")):
        raise ValueError(f"Unsafe relative resource path: {path!r}")
    return parsed


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def check_reference_files(repo, commit):
    checked = {}
    for name in REFERENCE_FILES:
        path = (repo / name).resolve()
        assert path.is_relative_to(repo) and path.is_file(), name
        local = path.read_bytes()
        assert local == git(repo, "show", f"{commit}:{name}"), f"Validator differs from requested commit: {name}"
        checked[name] = {"sha256": sha(local), "matches_requested_commit": True}
    return checked


class HeaderRecorder:
    """Instrument LiveFetcher's real default opener without replacing its policy.

    The default scoped redirect handler, HTTPS checks, finite retries, timeout,
    and cache-control request remain in LiveFetcher. Each real attempt retains
    parsed header pairs plus the HTTPMessage serialization. These are headers
    exposed by urllib, not a claimed raw TCP/TLS wire capture.
    """

    def __init__(self, fetcher, directory):
        self.original_open = fetcher._open
        self.directory = directory
        self.attempts = []
        fetcher._open = self.open

    def save_headers(self, record, response):
        headers = response.headers
        record.update(final_url=response.geturl(), http_status=getattr(response, "status", getattr(response, "code", None)))
        record["headers"] = list(headers.raw_items()) if hasattr(headers, "raw_items") else list(headers.items())
        serialized = headers.as_bytes() if hasattr(headers, "as_bytes") else str(headers).encode("utf-8")
        relative = f"http-attempts/{record['number']:03d}.headers.txt"
        target = self.directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(serialized)
        record.update(headers_file=relative, headers_sha256=sha(serialized),
                      headers_format="urllib HTTPMessage serialization; original header pairs retained")

    def open(self, request, **kwargs):
        record = {"number": len(self.attempts) + 1, "url": request.full_url,
                  "started_at": now(), "request_headers": list(request.header_items())}
        self.attempts.append(record)
        begin = time.monotonic()
        try:
            response = self.original_open(request, **kwargs)
            self.save_headers(record, response)
            return response
        except HTTPError as error:
            self.save_headers(record, error)
            record["error"] = {"type": type(error).__name__, "message": str(error)}
            raise
        except Exception as error:
            record["error"] = {"type": type(error).__name__, "message": str(error)}
            raise
        finally:
            record["headers_completed_at"] = now()
            record["time_to_headers_seconds"] = round(time.monotonic() - begin, 3)


class Reader:
    """Cache only response bodies actually retrieved over HTTPS in this run."""

    def __init__(self, fetcher, transport, directory):
        self.fetcher, self.transport, self.directory = fetcher, transport, directory
        self.cache, self.receipts = {}, []
        self.hashes = None
        self.cache_hits = 0

    def fetch(self, path, archive_name=None):
        safe_path(path)
        target = self.directory / "responses" / safe_path(archive_name or path)
        start, begin = now(), time.monotonic()
        first_attempt = len(self.transport.attempts)
        retries_before = len(self.fetcher.retries)
        print(f"[HTTPS] {path}", flush=True)
        receipt = {"requested_path": path, "url": BASE + path, "started_at": start}
        self.receipts.append(receipt)
        try:
            raw = self.fetcher.get(path)
            if not isinstance(raw, bytes):
                raise TypeError("LiveFetcher did not return original response bytes")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            receipt.update(http_status=200, bytes=len(raw), sha256=sha(raw),
                           saved_response=str(target.relative_to(self.directory)))
            if path != "build-info.json":
                expected = self.hashes.get(path) if self.hashes is not None else None
                receipt.update(declared_sha256=expected, matches_build_info=sha(raw) == expected)
                assert expected is not None, f"Resource absent from build-info hashes: {path}"
                assert sha(raw) == expected, f"Public bytes differ from build-info hash: {path}"
            receipt["status"] = "passed"
            return raw
        except Exception as error:
            receipt.update(status="failed", error={"type": type(error).__name__, "message": str(error)})
            if hasattr(error, "status"):
                receipt["http_status"] = error.status
            raise
        finally:
            receipt.update(completed_at=now(), elapsed_seconds=round(time.monotonic() - begin, 3),
                           http_attempt_numbers=[a["number"] for a in self.transport.attempts[first_attempt:]],
                           retries_during_request=len(self.fetcher.retries) - retries_before)

    def get(self, path):
        safe_path(path)
        if path in self.cache:
            self.cache_hits += 1
            return self.cache[path]
        raw = self.fetch(path)
        self.cache[path] = raw
        return raw


class Homepage(HTMLParser):
    def __init__(self, raw):
        super().__init__()
        self.links, self.stylesheets = [], []
        self.feed(raw.decode("utf-8"))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.links.append(attrs.get("href"))
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.stylesheets.append(attrs.get("href"))


def csv_data(raw):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    return list(reader), list(reader.fieldnames or [])


def verify_research_downloads(info, reader):
    manifest = json.loads(reader.get("all-roads/manifest.json"))
    assert manifest == info["all_road_locations"]
    assert manifest["source_commit"] == info["source_commit"]
    assert manifest["version"] == "all-road-atlas-r6.2"
    assert manifest["counts"]["records"] == 84 and manifest["counts"]["coverage"] == 339
    assert manifest["counts"]["groups"] == GROUPS
    for path, expected in manifest["files_sha256"].items():
        assert sha(reader.get(path)) == expected == info["files_sha256"][path], path
    data = json.loads(reader.get("all-roads/records.json"))
    records, record_columns = csv_data(reader.get("all-roads/records.csv"))
    coverage, coverage_columns = csv_data(reader.get("all-roads/coverage.csv"))
    water, water_columns = csv_data(reader.get("water-locations.csv"))
    assert len(records) == len(data["records"]) == 84
    assert len(coverage) == len(data["coverage"]) == 339
    assert [r["id"] for r in records] == [r["id"] for r in data["records"]]
    assert [r["entity_id"] for r in coverage] == [r["entity_id"] for r in data["coverage"]]
    assert dict(Counter(r["group"] for r in records)) == GROUPS
    assert len(water) == info["water_locations"]["register_count"] == 34
    assert [r["编号"] for r in water] == [f"W{i:02d}" for i in range(1, 35)]
    for page in ("luoyang-all-roads.html", "luoyang-water-atlas.html"):
        reader.get(page)
    bundle_raw = reader.get("downloads/luoyang-all-roads.zip")
    with ZipFile(io.BytesIO(bundle_raw)) as bundle:
        names = bundle.namelist()
        assert len(names) == len(set(names)) == 8
        assert set(names) == set(manifest["files_sha256"]) | {"index.html", "all-roads/manifest.json"}
        assert bundle.testzip() is None, "Offline ZIP contains a corrupt member"
        members = {}
        for path in names:
            safe_path(path)
            raw = bundle.read(path)
            members[path] = {"bytes": len(raw), "sha256": sha(raw)}
            if path != "index.html":
                assert raw == reader.get(path), f"ZIP differs from public member: {path}"
                members[path]["matches_public_resource"] = True
        members["index.html"]["integrity_basis"] = "ZIP CRC; offline index intentionally not a separate manifest-hashed public resource"
    return {"records": {"rows": len(records), "columns": record_columns},
            "coverage": {"rows": len(coverage), "columns": coverage_columns},
            "water": {"rows": len(water), "columns": water_columns},
            "groups": GROUPS, "offline_members": members,
            "scope": "Published download bytes, counts, identities and bundle integrity; no new historical research"}


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--commit", required=True, help="Exact 40-character deployed main commit")
    parser.add_argument("--output-dir", required=True, type=Path, help="New, empty evidence directory outside the repository")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent / "luoyang-city")
    parser.add_argument("--timeout", type=float, default=45, help="Per-request timeout, 0 < value <= 60")
    parser.add_argument("--attempts", type=int, default=4, help="Bounded transient-error attempts, 1–4")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[0-9a-fA-F]{40}", args.commit):
        parser.error("--commit must be exactly 40 hexadecimal characters")
    if not 0 < args.timeout <= 60 or not 1 <= args.attempts <= 4:
        parser.error("Invalid timeout or attempt limit")
    args.commit = args.commit.lower()
    args.repo, args.output_dir = args.repo.resolve(), args.output_dir.resolve()
    if args.output_dir.is_relative_to(args.repo):
        parser.error("--output-dir must be outside the repository")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("--output-dir must be empty; retain earlier evidence and choose a new directory")
    return args


def main(argv=None):
    args = arguments(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {"status": "running", "started_at": now(), "base_url": BASE,
              "expected_source_commit": args.commit, "checks": [],
              "runner_sha256": sha(Path(__file__).read_bytes()),
              "public_asset_policy": "Actual HTTPS response bytes only; no local fallback",
              "headers_policy": "Actual urllib response header pairs and serialized HTTPMessage retained per attempt",
              "repository_policy": "Source validators checked against the exact requested commit; repository never modified"}
    reader = transport = fetcher = None
    raw_info = None
    failure = None
    try:
        assert git(args.repo, "rev-parse", "--verify", args.commit + "^{commit}").decode().strip() == args.commit
        report["local_checkout_commit"] = git(args.repo, "rev-parse", "HEAD").decode().strip()
        report["reference_files"] = check_reference_files(args.repo, args.commit)
        report["checks"].append({"name": "validators_match_exact_commit", "status": "passed"})
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(args.repo / "tools"))
        from live_http import LiveFetcher
        import homepage_artwork_v10 as artwork
        from PIL import Image

        fetcher = LiveFetcher(BASE, attempts=args.attempts, timeout=args.timeout)
        transport = HeaderRecorder(fetcher, args.output_dir)
        reader = Reader(fetcher, transport, args.output_dir)
        raw_info = reader.get("build-info.json")
        info = json.loads(raw_info)
        report.update(observed_source_commit=info.get("source_commit"), build_info_sha256=sha(raw_info))
        assert info["source_commit"] == args.commit, ("Unexpected published commit", info["source_commit"], args.commit)
        reader.hashes = info["files_sha256"]
        release = json.loads(reader.get("release.json"))
        assert release["homepage_hero_revision"] == artwork.V12.revision == artwork.CURRENT.revision
        assert release["homepage_hero_status"] == "approved"
        report["checks"].append({"name": "published_commit_and_current_hero", "status": "passed"})

        # Reuse the exact committed reversible-history verifier. All reads passed
        # to it are genuine public HTTPS bodies fetched by the reader above.
        artwork.verify(info, release, reader.get)
        approval = json.loads(reader.get(artwork.V12.metadata))
        hero = approval["hero"]
        assert hero["selection_label"] == "全幅取景版" and hero["display_mode"] == "full_frame"
        assert hero["generated_image"] is True and hero["measured_reconstruction"] is False
        assert hero["historical_ground_truth_upgraded"] is False
        assert hero["title_position"] == hero["caption_position"] == "below_image"
        dimensions = {}
        for version in (artwork.V11, artwork.V12):
            for path, expected in ((version.full, (1672, 941)), (version.small, (960, 540))):
                raw = reader.get(path)
                with Image.open(io.BytesIO(raw)) as picture:
                    assert picture.format == "WEBP" and picture.size == expected, (path, picture.format, picture.size)
                    picture.load()
                    dimensions[path] = list(picture.size)
        entrances = {}
        for page in artwork.PAGES:
            raw = reader.get(page)
            parsed = Homepage(raw)
            assert raw.count(b'data-hero-revision="panorama-approved-v12"') == 1
            assert parsed.stylesheets.count("./" + artwork.LAYOUT_ASSET) == 1
            assert "./luoyang-all-roads.html" in parsed.links and "./luoyang-water-atlas.html" in parsed.links
            archive = reader.get(artwork.V12.archive(page))
            assert b'data-hero-revision="panorama-approved-v11"' in archive
            assert artwork.LAYOUT_TAG not in archive
            entrances[page] = {"sha256": sha(raw), "previous_v11_archive": artwork.V12.archive(page),
                               "previous_v11_sha256": sha(archive), "direct_road_and_water_links": True}
        report["homepage"] = {"revision": artwork.V12.revision, "label": hero["selection_label"],
                              "layout_asset": artwork.LAYOUT_ASSET, "layout_sha256": artwork.LAYOUT_SHA,
                              "source_image_sha256": hero["source_sha256"], "image_dimensions": dimensions,
                              "entrances": entrances, "v11_retained": True}
        report["checks"].append({"name": "both_homepages_v12_artwork_css_metadata_and_reversible_v11_history", "status": "passed"})
        report["research_downloads"] = verify_research_downloads(info, reader)
        report["checks"].append({"name": "84_road_records_339_entities_34_waters_and_8_member_offline_zip", "status": "passed"})
    except Exception as error:
        failure = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
        if all(hasattr(error, key) for key in ("path", "status", "attempts", "reason")):
            failure["http"] = {key: getattr(error, key) for key in ("path", "status", "attempts", "reason")}
    finally:
        # Take an uncached ending snapshot, including on validation failure where
        # the initial body exists. Publication movement never passes silently.
        if reader is not None and raw_info is not None:
            try:
                ending = reader.fetch("build-info.json", "build-info.end.json")
                report.update(ending_build_info_sha256=sha(ending), ending_source_commit=json.loads(ending).get("source_commit"))
                assert ending == raw_info, "build-info changed during readback; verify a stable publication again"
                report["checks"].append({"name": "unchanged_start_end_publication", "status": "passed"})
            except Exception as error:
                report["checks"].append({"name": "unchanged_start_end_publication", "status": "failed", "message": str(error)})
                if failure is None:
                    failure = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
        report["status"] = "failed" if failure else "passed"
        if failure:
            report["failure"] = failure
        report["completed_at"] = now()
        receipts = reader.receipts if reader else []
        attempts = transport.attempts if transport else []
        retries = fetcher.retries if fetcher else []
        report.update(response_count=len(receipts), distinct_public_resources=len({r["requested_path"] for r in receipts}),
                      successful_response_bytes=sum(r.get("bytes", 0) for r in receipts),
                      readback_cache_hits=reader.cache_hits if reader else 0, http_attempt_count=len(attempts), http_retries=retries)
        index = args.output_dir / "response-index.json"
        dump(index, {"base_url": BASE, "expected_source_commit": args.commit, "responses": receipts,
                     "http_attempts": attempts, "http_retries": retries})
        report["response_index"] = {"path": "response-index.json", "sha256": sha(index.read_bytes())}
        report_path = args.output_dir / "independent-live.json"
        dump(report_path, report)
        summary = {"status": report["status"], "expected_source_commit": args.commit,
                   "observed_source_commit": report.get("observed_source_commit"),
                   "checks": report["checks"], "response_count": len(receipts),
                   "http_retries": len(retries), "report": str(report_path), "response_index": str(index)}
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
