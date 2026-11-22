"""Preserve original V13 Actions reports and focus screenshots from a ZIP.

All V13 JSON and PNG files are retained at any depth, in build and live forms.
Other browser JSON, root text/JSON logs, R7, R6.2 and V12 screenshots are also
retained. This records provenance, not workflow acceptance or approval.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
from zipfile import ZipFile

FOCUS = {"city-nodes-r7-browser", "all-road-atlas-r62-browser",
         "homepage-approved-v9-browser", "panorama-v13-browser"}
V13 = "panorama-v13-browser"
V13_REQUIRED = {"desktop-report.json", "mobile-report.json",
                "desktop-comparison.png", "mobile-comparison.png",
                "desktop-without-javascript.png", "mobile-without-javascript.png"}


def fingerprint(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                git_blob_sha=hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest())


def normalized(name):
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts or "\\" in name or path.as_posix() != name:
        raise ValueError("Unsafe or non-normalized ZIP path: " + repr(name))
    return path


def selected(name):
    path = PurePosixPath(name)
    top = path.parts[0].removeprefix("live-")
    suffix = path.suffix.lower()
    if top == V13 and suffix in {".json", ".png"}:
        return True
    if "downloads" in path.parts or any(p.startswith("terrain-products") for p in path.parts):
        return False
    if suffix == ".png":
        return top in FOCUS
    if len(path.parts) == 1:
        return suffix in {".txt", ".json", ".log"}
    if suffix == ".json" and (top == "browser" or top.endswith("-browser")):
        return True
    return len(path.parts) == 2 and suffix == ".json" and (
        path.name in {"results.json", "report.json"} or path.name.endswith("-report.json"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=["pr", "main-build", "main-live"], required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--expected-source", required=True, help="Actual tested checkout SHA, including PR merge-ref")
    parser.add_argument("--require-full-focus", action="store_true", help="Require all four focus screenshot sets and six V13 success files")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_source):
        raise ValueError("Expected source must be a full 40-character Git SHA")
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("Use a new empty evidence folder")
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = dict(schema="luoyang-v13-actions-evidence-selection-v1", stage=args.stage,
                    captured_at_utc=datetime.now(timezone.utc).isoformat(),
                    workflow_url=f"https://github.com/mechgouki/luoyang-city/actions/runs/{args.run_id}",
                    workflow_run_id=args.run_id, artifact_id=args.artifact_id,
                    original_zip=dict(filename=args.zip.name, **fingerprint(args.zip.read_bytes())),
                    expected_source_commit=args.expected_source,
                    selection_rule="Every V13 JSON and PNG at any depth; other browser JSON and root text/JSON logs; all R7/R6.2/V12 PNGs; original bytes preserved",
                    files=[], report_summary=[],
                    meaning="Artifact provenance only; workflow outcome, deployment acceptance and homepage approval are separate facts.")
    with ZipFile(args.zip) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP names")
        chosen = sorted(name for name in names if not name.endswith("/") and selected(name))
        if not chosen:
            raise ValueError("No selected evidence")
        seen_focus, v13_names, json_records, source_commits = set(), set(), [], set()
        for name in chosen:
            path = normalized(name)
            entry = archive.getinfo(name)
            if stat.S_ISLNK(entry.external_attr >> 16) or entry.file_size >= 32 * 1024 * 1024:
                raise ValueError("Symlink or unexpectedly large selected evidence: " + name)
            raw = archive.read(name)  # ZipFile verifies original CRC on each complete read.
            target = args.output / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            if target.read_bytes() != raw:
                raise ValueError("Extracted bytes changed: " + name)
            manifest["files"].append(dict(path=name, **fingerprint(raw),
                                          zip_crc32=f"{entry.CRC:08x}", byte_identical_to_artifact=True))
            top = path.parts[0].removeprefix("live-")
            if top == V13:
                v13_names.add(PurePosixPath(*path.parts[1:]).as_posix())
            if path.suffix.lower() == ".png":
                seen_focus.add(top)
            if path.suffix.lower() == ".json":
                record = json.loads(raw)
                json_records.append((path, record))
                if isinstance(record, dict):
                    source = record.get("source_commit")
                    if source:
                        if source != args.expected_source:
                            raise ValueError(f"Report source differs from expected checkout: {name}: {source}")
                        source_commits.add(source)
                    if "checks" in record or name == "live-http.json":
                        manifest["report_summary"].append(dict(path=name, status=record.get("status", "not_explicit"),
                            error_count=len(record.get("errors", [])), check_groups=len(record.get("checks", [])), source_commit=source))
        verified_screenshot_references = []
        for path, record in json_records:
            if path.parts[0].removeprefix("live-") != V13 or not isinstance(record, dict):
                continue
            for filename, checksum in record.get("screenshots", {}).items():
                screenshot = normalized((path.parent / normalized(filename)).as_posix())
                raw = (args.output / screenshot).read_bytes()
                if hashlib.sha256(raw).hexdigest() != checksum:
                    raise ValueError("V13 screenshot checksum differs from original report: " + str(screenshot))
                verified_screenshot_references.append(str(screenshot))
        missing_focus = sorted(FOCUS - seen_focus)
        missing_v13 = sorted(V13_REQUIRED - v13_names)
        if args.require_full_focus and (missing_focus or missing_v13 or not source_commits):
            raise ValueError(f"Incomplete success evidence: focus={missing_focus}, V13={missing_v13}, source={source_commits}")
        all_v13_json_png = {name for name in names if not name.endswith("/") and
                           PurePosixPath(name).parts[0].removeprefix("live-") == V13 and
                           PurePosixPath(name).suffix.lower() in {".json", ".png"}}
        if not all_v13_json_png.issubset(set(chosen)):
            raise ValueError("A V13 JSON or PNG was omitted")
        manifest["focus_completeness"] = dict(missing_screenshot_sets=missing_focus,
            missing_v13_success_files=missing_v13, all_original_v13_json_png_retained=True,
            verified_v13_screenshot_references=sorted(verified_screenshot_references))
        manifest["source_commits"] = sorted(source_commits)
    manifest["totals"] = dict(files=len(manifest["files"]), bytes=sum(f["bytes"] for f in manifest["files"]),
                              screenshots=sum(f["path"].lower().endswith(".png") for f in manifest["files"]),
                              v13_json_png_files=len(all_v13_json_png), summarized_reports=len(manifest["report_summary"]))
    (args.output / "artifact-selection.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(stage=args.stage, **manifest["totals"], source_commits=manifest["source_commits"],
                         focus_completeness=manifest["focus_completeness"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
