"""Select reusable R7 CI evidence from an Actions ZIP without re-encoding it.

Retains all browser reports, root test/runtime summaries, and every screenshot
for R7, the R6.2 road return navigation, and the V12 homepage. Large build
products, terrain data and duplicate download bodies remain in the original ZIP.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
from zipfile import ZipFile
from zoneinfo import ZoneInfo

FOCUS = {"city-nodes-r7-browser", "all-road-atlas-r62-browser", "homepage-approved-v9-browser"}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def selected(name):
    path = PurePosixPath(name)
    if "downloads" in path.parts or any(p.startswith("terrain-products") for p in path.parts):
        return False
    top = path.parts[0].removeprefix("live-")
    if path.suffix.lower() == ".png":
        return top in FOCUS and len(path.parts) == 2
    if len(path.parts) == 1:
        return path.suffix.lower() in {".txt", ".json", ".log"}
    return len(path.parts) == 2 and path.suffix.lower() == ".json" and (
        path.name == "results.json" or path.name == "report.json" or path.name.endswith("-report.json"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=["original-pr", "corrected-pr", "merge-build", "live"], required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--artifact-id")
    parser.add_argument("--expected-source", help="Actual checkout SHA; a PR merge-ref SHA differs from the PR head")
    args = parser.parse_args()
    assert not args.output.exists() or not any(args.output.iterdir()), "Use a new empty evidence folder"
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = dict(schema="luoyang-r7-actions-evidence-selection-v1", stage=args.stage,
                    captured_at_beijing=datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
                    workflow_url=f"https://github.com/mechgouki/luoyang-city/actions/runs/{args.run_id}",
                    workflow_run_id=args.run_id, artifact_id=args.artifact_id,
                    original_zip=dict(filename=args.zip.name, bytes=args.zip.stat().st_size,
                                      sha256=digest(args.zip.read_bytes())),
                    expected_source_commit=args.expected_source,
                    selection_rule="All browser reports and root text/JSON logs; all R7, R6.2, V12 PNGs; no terrain or duplicate downloads",
                    files=[], report_summary=[], meaning="Extraction records provenance only; it does not replace the workflow outcome or assert deployment success.")
    with ZipFile(args.zip) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)), "Duplicate ZIP names"
        chosen = sorted(name for name in names if not name.endswith("/") and selected(name))
        assert chosen, "No matching evidence in archive"
        seen_focus = set()
        for name in chosen:
            path = PurePosixPath(name)
            assert not path.is_absolute() and ".." not in path.parts
            entry = archive.getinfo(name)
            assert not stat.S_ISLNK(entry.external_attr >> 16), (name, "Symlink rejected")
            assert entry.file_size < 32 * 1024 * 1024, (name, "Unexpectedly large selected evidence")
            raw = archive.read(name)
            target = args.output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            assert target.read_bytes() == raw
            manifest["files"].append(dict(path=name, bytes=len(raw), sha256=digest(raw),
                                          zip_crc32=f"{entry.CRC:08x}", byte_identical_to_artifact=True))
            if path.suffix.lower() == ".png":
                seen_focus.add(path.parts[0].removeprefix("live-"))
            if path.suffix.lower() == ".json":
                record = json.loads(raw)
                if isinstance(record, dict) and ("checks" in record or name == "live-http.json"):
                    source = record.get("source_commit")
                    if args.expected_source and source:
                        assert source == args.expected_source, (name, "Report belongs to another checkout")
                    checks = record.get("checks", [])
                    manifest["report_summary"].append(dict(path=name, status=record.get("status", "not_explicit"),
                                                           error_count=len(record.get("errors", [])),
                                                           check_groups=len(checks), source_commit=source))
        assert seen_focus == FOCUS, ("Missing focus screenshot set", sorted(FOCUS - seen_focus))
    manifest["totals"] = dict(files=len(manifest["files"]), bytes=sum(f["bytes"] for f in manifest["files"]),
                              screenshots=sum(f["path"].endswith(".png") for f in manifest["files"]),
                              summarized_browser_or_http_reports=len(manifest["report_summary"]))
    (args.output / "artifact-selection.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(stage=args.stage, **manifest["totals"],
                         source_commits=sorted({r["source_commit"] for r in manifest["report_summary"] if r["source_commit"]})), ensure_ascii=False))


if __name__ == "__main__":
    main()
