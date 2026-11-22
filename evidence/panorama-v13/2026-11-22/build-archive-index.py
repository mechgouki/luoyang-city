"""Index explicitly selected evidence; compare local bytes to upload receipts.

No network calls, repository mutations or edits to evidence files are made.
An index is written only when --output is explicitly supplied. Without it this
is a read-only check. Nothing here determines whether a release was accepted.

Example, after the named directories have actually been populated:

    python3 build-archive-index.py --root /tmp/luoyang-v13-final-evidence \
      --include local-preflight --include pr --include main-build --include main-live \
      --include build-archive-index.py --include extract-actions-evidence.py \
      --include verify-remote-archive.py \
      --stage-label local-preflight='Python 3.12 over borrowed d334 site; not full CI' \
      --stage-label pr='PR79 exact merge-ref workflow evidence; inspect recorded outcome' \
      --ledger /tmp/luoyang-v13-pr-evidence-blobs.json \
      --output /tmp/luoyang-v13-final-evidence/archive-index.json

Run without --output, adding the remaining ledgers and --require-uploaded, to
check that every selected content blob has a matching saved upload receipt.
Remote Git tree/blob readback remains a separate verification step.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from zoneinfo import ZoneInfo


SCHEMA = "luoyang-evidence-archive-index-v1"
SHA1 = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")


def relative_path(value):
    """Accept explicit, normalized archive-relative paths only."""
    path = PurePosixPath(value)
    if not value or value in (".", "./") or path.is_absolute() or ".." in path.parts:
        raise ValueError("Include/ledger paths must be explicit paths beneath the archive root: " + value)
    if "\\" in value or path.as_posix() != value.rstrip("/"):
        raise ValueError("Use normalized POSIX archive paths: " + value)
    return path.as_posix()


def exclusion_reason(path, output_relative=None):
    """Keep only captured public download ZIPs, not temporary Actions ZIPs."""
    parts = PurePosixPath(path).parts
    if "__pycache__" in parts:
        return "Python bytecode cache"
    if "full-svg-png" in parts:
        return "Temporary full-SVG raster inspection"
    if path == output_relative:
        return "Index output cannot hash itself"
    if PurePosixPath(path).suffix.lower() == ".pyc":
        return "Python bytecode cache"
    if PurePosixPath(path).suffix.lower() == ".zip":
        captured_download = any(parts[i:i + 2] == ("http-responses", "downloads")
                                for i in range(len(parts) - 1))
        if not captured_download:
            return "Temporary/source ZIP; only captured public download ZIPs are retained"
    return None


def fingerprint(path):
    """Stream exact file bytes; fail if the file changes during the read."""
    before = path.stat()
    sha256 = hashlib.sha256()
    git_blob = hashlib.sha1(b"blob " + str(before.st_size).encode("ascii") + b"\0")
    actual_bytes = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            actual_bytes += len(block)
            sha256.update(block)
            git_blob.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError("File changed during indexing: " + str(path))
    if actual_bytes != before.st_size:
        raise ValueError("File length changed during indexing: " + str(path))
    return dict(bytes=actual_bytes, sha256=sha256.hexdigest(), git_blob_sha=git_blob.hexdigest())


def validate_includes(root, includes):
    values = [relative_path(value) for value in includes]
    if len(values) != len(set(values)):
        raise ValueError("Duplicate --include entries")
    paths = [PurePosixPath(value) for value in values]
    for i, path in enumerate(paths):
        for other in paths[i + 1:]:
            if path in other.parents or other in path.parents:
                raise ValueError("Overlapping includes are ambiguous stages: " + str(path) + " and " + str(other))
    for value in values:
        path = root / value
        if not path.exists():
            raise ValueError("Required evidence path is missing: " + value)
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Include resolves outside the root or is a symlink: " + value)
        if not path.is_file() and not path.is_dir():
            raise ValueError("Unsupported evidence path type: " + value)
    return values


def scan_stage(root, stage, output_relative):
    """Do not follow symlinks; return selected files and explicit exclusions."""
    base = root / stage
    files, excluded = [], []

    def consider(path):
        rel = path.relative_to(root).as_posix()
        reason = exclusion_reason(rel, output_relative)
        if reason:
            excluded.append(dict(path=rel, reason=reason))
            return
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Symlink or external path in evidence: " + rel)
        files.append(dict(path=rel, stage=stage, **fingerprint(path)))

    if base.is_file():
        consider(base)
    else:
        for directory, dirs, names in os.walk(base, followlinks=False):
            directory = Path(directory)
            for name in sorted(dirs[:]):
                path = directory / name
                rel = path.relative_to(root).as_posix()
                reason = exclusion_reason(rel, output_relative)
                if reason:
                    excluded.append(dict(path=rel + "/", reason=reason))
                    dirs.remove(name)
                elif path.is_symlink():
                    raise ValueError("Symlink directory in evidence: " + rel)
            for name in sorted(names):
                consider(directory / name)
    return files, excluded


def load_ledgers(ledger_paths):
    by_path, by_blob = defaultdict(list), defaultdict(list)
    sources = []
    for source in ledger_paths:
        path = Path(source).resolve()
        raw = path.read_bytes()
        document = json.loads(raw)
        if not isinstance(document, dict) or not isinstance(document.get("files"), list):
            raise ValueError("Upload ledger must contain a files array: " + str(path))
        sources.append(dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(),
                            entries=len(document["files"]), complete=document.get("complete"),
                            source_commit=document.get("source_commit")))
        for item in document["files"]:
            rel = relative_path(item["path"])
            sha = item.get("git_blob_sha", "")
            checksum = item.get("sha256", "")
            size = item.get("bytes")
            if not SHA1.fullmatch(sha) or not SHA256.fullmatch(checksum) or type(size) is not int or size < 0:
                raise ValueError("Malformed receipt in " + str(path) + ": " + rel)
            receipt = dict(path=rel, git_blob_sha=sha, sha256=checksum, bytes=size, ledger=str(path))
            for previous in by_blob[sha]:
                if (previous["sha256"], previous["bytes"]) != (checksum, size):
                    raise ValueError("Conflicting SHA-256/size for one Git blob: " + sha)
            by_path[rel].append(receipt)
            by_blob[sha].append(receipt)
    return sources, by_path, by_blob


def compare_uploads(files, ledger_paths):
    sources, by_path, by_blob = load_ledgers(ledger_paths)
    missing, stale_paths = [], []
    counters = Counter()
    for item in files:
        same_path = by_path.get(item["path"], [])
        matching = [r for r in same_path if (r["git_blob_sha"], r["sha256"], r["bytes"]) ==
                    (item["git_blob_sha"], item["sha256"], item["bytes"])]
        reusable = [r for r in by_blob.get(item["git_blob_sha"], [])
                    if (r["sha256"], r["bytes"]) == (item["sha256"], item["bytes"])]
        if matching:
            kind, receipts = "same_path_receipt", matching
        elif reusable:
            kind, receipts = "identical_blob_receipt", reusable
        else:
            kind, receipts = "missing_upload_receipt", []
            missing.append({k: item[k] for k in ("path", "git_blob_sha", "sha256", "bytes")})
        if same_path and not matching:
            stale_paths.append(dict(path=item["path"], current_git_blob_sha=item["git_blob_sha"],
                                    recorded_git_blob_shas=sorted({r["git_blob_sha"] for r in same_path})))
        item["upload_receipt"] = dict(status=kind,
                                      ledgers=sorted({r["ledger"] for r in receipts}),
                                      recorded_paths=sorted({r["path"] for r in receipts}))
        counters[kind] += 1
    return dict(scope="Comparison with saved receipts only; no remote tree/blob readback performed",
                status="not_requested" if not ledger_paths else "complete" if not missing else "incomplete",
                ledgers=sources, counts=dict(counters), missing_uploads=missing,
                stale_path_receipts=stale_paths,
                incomplete_ledger_files=[s["path"] for s in sources if s["complete"] is not True])


def parse_labels(values, includes):
    labels = {}
    for value in values:
        key, sep, label = value.partition("=")
        if not sep or key not in includes or not label.strip():
            raise ValueError("--stage-label must be included-path=description: " + value)
        if key in labels:
            raise ValueError("Duplicate stage label: " + key)
        labels[key] = label
    return labels


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--include", action="append", required=True,
                        help="Explicit relative evidence directory or root file; repeat for each stage/file")
    parser.add_argument("--stage-label", action="append", default=[], metavar="PATH=DESCRIPTION")
    parser.add_argument("--ledger", action="append", default=[], help="Saved upload ledger; repeat as needed")
    parser.add_argument("--require-uploaded", action="store_true",
                        help="Exit 2 if a selected blob lacks a saved receipt or a supplied ledger is incomplete")
    parser.add_argument("--output", type=Path,
                        help="Optional new index file; omit for a read-only scan and ledger comparison")
    parser.add_argument("--overwrite", action="store_true", help="Explicitly replace an existing index output")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        raise ValueError("Archive root does not exist")
    includes = validate_includes(root, args.include)
    labels = parse_labels(args.stage_label, includes)
    output = args.output.resolve() if args.output else None
    output_relative = output.relative_to(root).as_posix() if output and output.is_relative_to(root) else None
    if output and output.exists() and not args.overwrite:
        raise ValueError("Index output already exists; use a new name or explicit --overwrite")
    if args.require_uploaded and not args.ledger:
        raise ValueError("--require-uploaded needs at least one --ledger")
    files, excluded, stages = [], [], []
    for stage in includes:
        selected, omitted = scan_stage(root, stage, output_relative)
        files.extend(selected)
        excluded.extend(omitted)
        stages.append(dict(path=stage, description=labels.get(stage, "Explicitly selected evidence; outcome not inferred"),
                           kind="directory" if (root / stage).is_dir() else "root_file",
                           files=len(selected), bytes=sum(row["bytes"] for row in selected),
                           distinct_git_blobs=len({row["git_blob_sha"] for row in selected}),
                           excluded_entries=len(omitted)))
    files.sort(key=lambda row: row["path"])
    if len(files) != len({row["path"] for row in files}):
        raise ValueError("Duplicate evidence paths")
    comparison = compare_uploads(files, args.ledger)
    totals = dict(files=len(files), bytes=sum(row["bytes"] for row in files),
                  distinct_git_blobs=len({row["git_blob_sha"] for row in files}),
                  stages=len(stages), excluded_entries=len(excluded),
                  retained_public_zip_files=sum(row["path"].lower().endswith(".zip") for row in files))
    document = dict(schema=SCHEMA, created_at_beijing=datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
                    archive_root=str(root), selection=includes,
                    release_acceptance="not_asserted_by_this_index",
                    meaning="Exact local bytes and saved upload receipts. Stage labels are supplied by the caller; this index does not establish workflow success or final acceptance.",
                    index_self_hash="Excluded to avoid a self-referential checksum; verify the index as its own Git blob separately",
                    exclusion_policy=dict(omitted_directories=["full-svg-png", "__pycache__"],
                                          zip_rule="Retain only ZIPs beneath http-responses/downloads; omit temporary raw Actions ZIPs elsewhere"),
                    totals=totals, stages=stages, files=files,
                    excluded=sorted(excluded, key=lambda row: row["path"]), upload_comparison=comparison)
    if output:
        if not output.parent.is_dir():
            raise ValueError("Output parent does not exist; the scanner does not create extra directories")
        # Output is the only write this program performs.
        with output.open("w" if args.overwrite else "x", encoding="utf-8") as stream:
            stream.write(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(index_written=str(output) if output else None, totals=totals,
                          stages=stages, upload_comparison_status=comparison["status"],
                          missing_uploads=comparison["missing_uploads"],
                          stale_path_receipts=comparison["stale_path_receipts"],
                          incomplete_ledger_files=comparison["incomplete_ledger_files"],
                          release_acceptance="not_asserted_by_this_index"), ensure_ascii=False, indent=2))
    incomplete = comparison["missing_uploads"] or comparison["incomplete_ledger_files"]
    return 2 if args.require_uploaded and incomplete else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        print("Evidence index error: " + str(error), file=sys.stderr)
        sys.exit(1)
