#!/usr/bin/env python3
"""Independently read back a published R6.2 release, retaining actual response bytes.

Usage after the merge commit has been fetched into the local repository:
    python verify_r62_public.py --commit FULL_MERGE_SHA --output-dir r62-production

Every published asset comes from HTTPS through tools.live_http.LiveFetcher.
Repository files are used only as the source/validator baseline. No public asset
can fall back to a local build, a fixture, or an expected hash.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time
import traceback


BASE = "https://mechgouki.github.io/luoyang-city/"
EXPECTED_GROUPS = {"legacy": 21, "documentary": 26, "palace": 11,
                   "ward": 7, "gate": 14, "bridge": 5}
VERIFIER_FILES = (
    "tools/live_http.py",
    "tools/verify_all_road_atlas_r62.py",
    "tools/verify_road_atlas_r6.py",
    "tools/verify_city_west_p472.py",
    "tools/homepage_artwork_v10.py",
)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_relative(path):
    if not isinstance(path, str) or not path or "\\" in path or "\x00" in path:
        raise ValueError(f"Unsafe resource path: {path!r}")
    parts = PurePosixPath(path)
    if parts.is_absolute() or any(p in {".", ".."} for p in path.split("/")):
        raise ValueError(f"Unsafe resource path: {path!r}")
    if ":" in parts.parts[0] or "?" in path or "#" in path:
        raise ValueError(f"Asset path must be relative without query or fragment: {path!r}")
    return parts


class RecordingReader:
    """Cache only bytes actually fetched in this run and archive each response."""

    def __init__(self, fetcher, output_dir, *, progress=True):
        self.fetcher = fetcher
        self.output_dir = Path(output_dir)
        self.progress = progress
        self.cache = {}
        self.receipts = []
        self.expected_hashes = None
        self.cache_hits = 0

    def bind_hashes(self, hashes):
        self.expected_hashes = dict(hashes)
        for receipt in self.receipts:
            self._check(receipt)

    def _check(self, receipt):
        path = receipt["requested_path"]
        if self.expected_hashes is None or path == "build-info.json":
            return
        expected = self.expected_hashes.get(path)
        receipt["declared_sha256"] = expected
        receipt["matches_build_info"] = receipt["sha256"] == expected
        if expected is None:
            raise AssertionError(f"Public resource is absent from build-info hashes: {path}")
        if not receipt["matches_build_info"]:
            raise AssertionError(f"Public response hash differs from build-info: {path}")

    def _fetch(self, path, archive_name):
        safe_relative(path)
        archive_name = safe_relative(archive_name)
        if self.progress:
            print(f"[HTTPS] {path}", flush=True)
        started = utc_now()
        begin = time.monotonic()
        prior_retries = len(self.fetcher.retries)
        raw = self.fetcher.get(path)
        if not isinstance(raw, bytes):
            raise TypeError("LiveFetcher must return original response bytes")
        target = self.output_dir / "responses" / archive_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        receipt = {
            "requested_path": path,
            "url": self.fetcher.base_url + path,
            "http_status": 200,
            "started_at": started,
            "completed_at": utc_now(),
            "elapsed_seconds": round(time.monotonic() - begin, 3),
            "bytes": len(raw),
            "sha256": digest(raw),
            "saved_response": str(target.relative_to(self.output_dir)),
            "retries_during_request": len(self.fetcher.retries) - prior_retries,
        }
        self.receipts.append(receipt)
        self._check(receipt)
        return raw

    def get(self, path):
        safe_relative(path)
        if path in self.cache:
            self.cache_hits += 1
            return self.cache[path]
        raw = self._fetch(path, path)
        self.cache[path] = raw
        return raw

    def fresh_build_info(self):
        return self._fetch("build-info.json", "build-info.end.json")


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args[:2])} failed: {detail}")
    return result.stdout


def check_reference_tree(repo, commit, expected_hashes):
    """Ensure the source baseline and verifier code are exactly from the requested commit."""
    checked = {}
    paths = set(expected_hashes) | set(VERIFIER_FILES)
    for path in sorted(paths):
        safe_relative(path)
        local = (repo / path).resolve()
        if not local.is_relative_to(repo) or not local.is_file():
            raise AssertionError(f"Missing or out-of-repository verification input: {path}")
        actual = digest(local.read_bytes())
        committed = digest(git(repo, "show", f"{commit}:{path}"))
        if actual != committed:
            raise AssertionError(f"Local input differs from requested commit: {path}")
        expected = expected_hashes.get(path)
        if expected is not None and actual != expected:
            raise AssertionError(f"Published input provenance differs from requested commit: {path}")
        checked[path] = {"sha256": actual, "matches_requested_commit": True,
                         "declared_input_sha256": expected}
    return checked


def csv_rows(raw):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    rows = list(reader)
    return rows, list(reader.fieldnames or [])


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--commit", required=True, help="Exact 40-character published main commit SHA")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent / "luoyang-city",
                        help="Repository containing the frozen verifier and research inputs")
    parser.add_argument("--base-url", default=BASE, help="HTTPS project base; default is the formal GitHub Pages site")
    parser.add_argument("--output-dir", type=Path, help="Report/response directory; defaults to a fresh timestamped directory")
    parser.add_argument("--timeout", type=float, default=45, help="Per-request timeout seconds, at most 60 (default 45)")
    parser.add_argument("--attempts", type=int, default=4, help="Finite transient-failure retry limit, 1–4 (default 4)")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[0-9a-fA-F]{40}", args.commit):
        parser.error("--commit must be an exact 40-character hexadecimal SHA")
    if not 0 < args.timeout <= 60:
        parser.error("--timeout must be greater than zero and at most 60")
    if not 1 <= args.attempts <= 4:
        parser.error("--attempts must be between 1 and 4")
    args.commit = args.commit.lower()
    args.repo = args.repo.resolve()
    if args.output_dir is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        args.output_dir = Path(__file__).resolve().parent / "r62-evidence" / f"public-{stamp}-{args.commit[:12]}"
    args.output_dir = args.output_dir.resolve()
    return args


def main(argv=None):
    args = parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "independent-live.json"
    index_path = args.output_dir / "response-index.json"
    report = {
        "status": "running", "started_at": utc_now(), "base_url": args.base_url,
        "expected_source_commit": args.commit, "repository": str(args.repo),
        "runner": str(Path(__file__).resolve()),
        "runner_sha256": digest(Path(__file__).read_bytes()),
        "asset_reading_policy": "HTTPS responses only; no local build or asset fallback",
        "output_dir": str(args.output_dir), "stages": [],
    }
    reader = None
    exit_code = 1
    try:
        resolved = git(args.repo, "rev-parse", "--verify", args.commit + "^{commit}").decode().strip()
        assert resolved == args.commit
        report["local_checkout_commit"] = git(args.repo, "rev-parse", "HEAD").decode().strip()
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(args.repo / "tools"))
        from live_http import LiveFetcher
        from verify_all_road_atlas_r62 import verify as verify_r62
        from verify_road_atlas_r6 import verify as verify_r6
        from homepage_artwork_v10 import V11

        fetcher = LiveFetcher(args.base_url, attempts=args.attempts, timeout=args.timeout)
        reader = RecordingReader(fetcher, args.output_dir)
        raw_info = reader.get("build-info.json")
        info = json.loads(raw_info)
        report["observed_source_commit"] = info.get("source_commit")
        report["build_info_sha256"] = digest(raw_info)
        assert info["source_commit"] == args.commit, ("Published commit differs", info["source_commit"], args.commit)
        reader.bind_hashes(info["files_sha256"])
        all_meta = info["all_road_locations"]
        assert all_meta["version"] == "all-road-atlas-r6.2"
        assert all_meta["counts"]["records"] == 84
        assert all_meta["counts"]["coverage"] == 339
        assert all_meta["counts"]["groups"] == EXPECTED_GROUPS
        assert len(all_meta["download_files"]) == 6
        report["stages"].append("published_commit_and_manifest_identity")

        old_data = json.loads(reader.get("road-atlas/roads.json"))
        input_hashes = dict(all_meta["source_inputs_sha256"])
        for path, checksum in old_data["source_inputs_sha256"].items():
            if path in input_hashes:
                assert input_hashes[path] == checksum, ("Cross-release input hash conflict", path)
            input_hashes[path] = checksum
        report["reference_inputs"] = check_reference_tree(args.repo, args.commit, input_hashes)
        report["stages"].append("repository_baseline_matches_requested_commit")

        print("[VERIFY] tools.verify_all_road_atlas_r62.verify", flush=True)
        report["r62_verification"] = verify_r62(info, reader.get)
        assert report["r62_verification"]["counts"]["records"] == 84
        assert report["r62_verification"]["counts"]["coverage"] == 339
        assert report["r62_verification"]["downloads"] == 6
        report["stages"].append("r62_full_public_verifier")

        print("[VERIFY] tools.verify_road_atlas_r6.verify", flush=True)
        report["r6_verification"] = verify_r6(info, reader.get)
        assert report["r6_verification"]["records"] == 21
        assert report["r6_verification"]["supplements"] == 3
        assert report["r6_verification"]["downloads"] == 5
        report["stages"].append("r6_regression_public_verifier")

        data = json.loads(reader.get("all-roads/records.json"))
        rows, columns = csv_rows(reader.get("all-roads/records.csv"))
        coverage, coverage_columns = csv_rows(reader.get("all-roads/coverage.csv"))
        old_rows, old_columns = csv_rows(reader.get("road-atlas/roads.csv"))
        assert len(rows) == len(data["records"]) == 84
        assert len(coverage) == len(data["coverage"]) == 339
        assert len(old_rows) == 21
        assert dict(Counter(row["group"] for row in rows)) == EXPECTED_GROUPS
        required_columns = {"id", "name", "period", "locatable_segment", "start", "end", "endpoint_status",
                            "gates", "water_constraints", "reported_metrics", "identity_notes",
                            "missing_evidence", "source_refs", "source_citations", "geometry_refs", "source_inputs"}
        assert required_columns <= set(columns), ("Evidence CSV missing fields", sorted(required_columns-set(columns)))
        assert all(row["period"] and row["locatable_segment"] and row["start"] and row["end"]
                   and row["missing_evidence"] and row["source_citations"] for row in rows)
        audit = data["coverage_audit"]
        assert audit["road_quote_mention_count"] == len(audit["entity_road_quote_mentions"]) == 100
        assert audit["canonical_road_count"] == 21 and audit["canonical_bridge_count"] == 5
        assert audit["canonical_gate_count"] == 17
        report["csv"] = {
            "all_records": {"rows":len(rows), "columns":columns},
            "entity_coverage": {"rows":len(coverage), "columns":coverage_columns},
            "legacy_roads": {"rows":len(old_rows), "columns":old_columns},
            "road_quote_mentions": 100,
        }
        report["stages"].append("84_records_339_entities_and_full_csv_fields")

        approval = json.loads(reader.get(V11.metadata))
        assert approval["source_commit"] == args.commit
        assert approval["hero"]["selection_number"] == "07"
        assert approval["hero"]["revision"] == "panorama-approved-v11"
        for page in ("index.html", "v3.0-dual.html"):
            html = reader.get(page)
            assert html.count(b'data-hero-revision="panorama-approved-v11"') == 1, page
            assert html.count(f'src="./{V11.full}"'.encode()) == 1, page
            assert html.count(f'srcset="./{V11.small}"'.encode()) == 1, page
        assert digest(reader.get(V11.full)) == V11.full_sha
        assert digest(reader.get(V11.small)) == V11.small_sha
        report["homepage"] = {
            "revision": V11.revision, "selection_number": "07", "entrances": ["index.html", "v3.0-dual.html"],
            "full_sha256": digest(reader.get(V11.full)), "small_sha256": digest(reader.get(V11.small)),
        }
        report["download_readbacks"] = {
            path: {"sha256":digest(reader.get(path)), "bytes":len(reader.get(path)),
                   "matches_build_info":digest(reader.get(path)) == info["files_sha256"][path]}
            for path in all_meta["download_files"]
        }
        report["legacy_download_readbacks"] = {
            path: {"sha256":digest(reader.get(path)), "bytes":len(reader.get(path)),
                   "matches_build_info":digest(reader.get(path)) == info["files_sha256"][path]}
            for path in info["road_locations"]["download_files"]
        }
        report["stages"].append("homepage_07_v11_both_entrances_and_actual_download_hashes")

        # A second independent HTTPS read detects publication changes during this run.
        final_info = reader.fresh_build_info()
        report["ending_build_info_sha256"] = digest(final_info)
        report["ending_source_commit"] = json.loads(final_info)["source_commit"]
        assert final_info == raw_info, "build-info changed during public acceptance; repeat after publication stabilizes"
        report["stages"].append("unchanged_publication_during_readback")
        report["status"] = "passed"
        exit_code = 0
    except Exception as error:
        report["status"] = "failed"
        report["failure"] = {"type":type(error).__name__, "message":str(error), "traceback":traceback.format_exc()}
        if all(hasattr(error,key) for key in ("path","status","attempts","reason")):
            report["failure"]["http"] = {key:getattr(error,key) for key in ("path","status","attempts","reason")}
        print(f"[FAILED] {type(error).__name__}: {error}", file=sys.stderr, flush=True)
    finally:
        report["completed_at"] = utc_now()
        receipts = reader.receipts if reader else []
        report["response_count"] = len(receipts)
        report["distinct_public_resources"] = len({r["requested_path"] for r in receipts})
        report["public_response_bytes"] = sum(r["bytes"] for r in receipts)
        report["readback_cache_hits"] = reader.cache_hits if reader else 0
        report["http_retries"] = reader.fetcher.retries if reader else []
        dump(index_path, {"base_url":args.base_url, "expected_source_commit":args.commit,
                          "responses":receipts, "http_retries":report["http_retries"]})
        report["response_index"] = {"path":str(index_path), "sha256":digest(index_path.read_bytes())}
        dump(report_path, report)
        print(json.dumps({"status":report["status"], "expected_source_commit":args.commit,
                          "observed_source_commit":report.get("observed_source_commit"),
                          "response_count":report["response_count"], "report":str(report_path),
                          "response_index":str(index_path)}, ensure_ascii=False, indent=2), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
