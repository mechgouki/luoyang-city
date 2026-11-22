#!/usr/bin/env python3
"""Build a hash-audited permanent evidence payload without changing source evidence.

Input manifest example:
{"source":"/tmp/r10-archive-work/incoming", "destination":".../payload",
 "wrappers":[{"path":"main-build/evidence.zip", "extracted":"main-build/artifacts",
              "run_id":123, "artifact_id":456, "digest":"sha256:..."}],
 "terrain_baseline":"/tmp/r10-archive-work/config/r9-archive-scope.json"}

Acceptance is recorded separately from this mechanical archive operation. A
passing inventory never implies passing CI, deployment or research validation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath

SCHEMA = "luoyang-r10-permanent-evidence"
INDEX_FILES = {"archive-inventory.json", "archive-scope.json", "archive-sensitive-scan.json"}
PATTERNS = {
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "bearer_secret": re.compile(r"(?i)\bauthorization[\"']?\s*[:=]\s*[\"']?bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    "authenticated_query": re.compile(r"(?i)[?&](?:access_token|auth_token|x-amz-signature|x-amz-credential|x-amz-security-token|x-goog-signature|sig)=[^&\s\"'<>]{8,}"),
}


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ident_bytes(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "gitblob": hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()}


def ident(path):
    # The source artifacts fit in RAM individually; read once to bind both hashes.
    return ident_bytes(path.read_bytes())


def safe_rel(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or ".." in p.parts or "\\" in name or ":" in name:
        raise ValueError(f"Unsafe relative path: {name!r}")
    return p


def scan(raw, label, findings):
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return 0
    if "\0" in text:
        return 0
    rules = [name for name, pattern in PATTERNS.items() if pattern.search(text)]
    if rules:
        # Do not retain matched values, snippets or credential-bearing URLs.
        findings.append({"path": label, "rules": rules})
    return 1


def terrain_hashes(path):
    prior = json.loads(path.read_text())
    result = {}
    for row in prior["excluded_redundant_or_intermediate_files"]:
        if row["reason_code"] != "unchanged_terrain_intermediate":
            continue
        name = PurePosixPath(row["path"]).name
        if name in result and result[name] != row["sha256"]:
            raise AssertionError((name, "Inconsistent prior terrain hashes"))
        result[name] = row["sha256"]
    assert len(result) == 7, result
    return result


def verify_wrapper(source, item):
    wrapper_path = str(safe_rel(item["path"]))
    extracted = safe_rel(item["extracted"])
    path = source / wrapper_path
    result = {"path": wrapper_path, **ident(path), "run_id": item.get("run_id"),
              "artifact_id": item.get("artifact_id"), "members": []}
    if item.get("digest"):
        algorithm, value = item["digest"].split(":", 1)
        assert algorithm == "sha256" and value == result["sha256"], (wrapper_path, "Artifact digest mismatch")
        result["github_artifact_digest_verified"] = True
    else:
        result["github_artifact_digest_verified"] = False
    with zipfile.ZipFile(path) as archive:
        seen = set()
        for member in archive.infolist():
            rel = safe_rel(member.filename.rstrip("/"))
            assert str(rel) not in seen, (wrapper_path, str(rel), "Duplicate ZIP member")
            seen.add(str(rel))
            assert not stat.S_ISLNK(member.external_attr >> 16), (wrapper_path, str(rel), "Symlink ZIP member")
            if member.is_dir():
                continue
            actual = source / extracted / rel
            assert actual.is_file() and not actual.is_symlink(), (wrapper_path, str(rel), "Missing extracted member")
            raw = archive.read(member)
            expected = ident_bytes(raw)
            assert ident(actual) == expected, (wrapper_path, str(rel), "Extracted bytes differ")
            result["members"].append({"path": str(extracted / rel), **expected})
    result["member_count"] = len(result["members"])
    return result


def prepare(config):
    source = Path(config["source"]).resolve()
    destination = Path(config["destination"]).resolve()
    assert source.is_dir() and source != destination
    assert source not in destination.parents and destination not in source.parents
    storage = config.get("payload_storage", "copy")
    assert storage in {"copy", "hardlink"}, storage
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Destination must be absent or empty; use a new snapshot directory")
    wrappers = [verify_wrapper(source, item) for item in config.get("wrappers", [])]
    wrapper_by_path = {row["path"]: row for row in wrappers}
    assert len(wrapper_by_path) == len(wrappers)
    baseline = terrain_hashes(Path(config["terrain_baseline"]))
    included, excluded, changed_terrain, findings = [], [], [], []
    scan_count, total_bytes, source_count = 0, 0, 0
    source_files = sorted(path for path in source.rglob("*") if path.is_file() or path.is_symlink())
    for path in source_files:
        assert not path.is_symlink(), (str(path), "Do not archive a symlink")
        relative = path.relative_to(source).as_posix()
        safe_rel(relative)
        assert relative not in INDEX_FILES, (relative, "Input must not contain generated archive indexes")
        raw = path.read_bytes()
        row = {"path": relative, **ident_bytes(raw)}
        source_count += 1
        total_bytes += len(raw)
        scan_count += scan(raw, relative, findings)
        if relative in wrapper_by_path:
            excluded.append({**row, "reason_code": "verified_artifact_wrapper",
                             "reason": "Every extracted member matched this wrapper; retained and omitted members are itemized separately."})
            continue
        is_terrain = "terrain-products-v30" in path.parts and path.name in baseline
        if is_terrain and row["sha256"] == baseline[path.name]:
            excluded.append({**row, "reason_code": "unchanged_terrain_intermediate",
                             "reason": "SHA256 matches the prior R9 permanent archive scope. Source notice and metadata remain included."})
            continue
        if is_terrain:
            changed_terrain.append(row)
        if zipfile.is_zipfile(path):
            # Real browser ZIP downloads are retained and their text members are scanned too.
            with zipfile.ZipFile(path) as archive:
                for member in archive.infolist():
                    if not member.is_dir():
                        scan_count += scan(archive.read(member), relative + "!" + member.filename, findings)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if storage == "hardlink":
            os.link(path, target)
        else:
            shutil.copyfile(path, target)
        assert ident(target) == {key: row[key] for key in ("bytes", "sha256", "gitblob")}
        included.append(row)
    retained_paths = {row["path"] for row in included}
    for wrapper in wrappers:
        for member in wrapper["members"]:
            member["retained_separately"] = member["path"] in retained_paths
        wrapper["members_retained_separately"] = sum(row["retained_separately"] for row in wrapper["members"])
        wrapper["members_not_retained_separately"] = wrapper["member_count"] - wrapper["members_retained_separately"]
    inventory = {"schema": SCHEMA + "-inventory-v1", "files": included, "verified_artifact_wrappers": wrappers,
                 "file_count": len(included), "total_bytes": sum(row["bytes"] for row in included),
                 "generated_indexes_not_in_this_inventory": sorted(INDEX_FILES),
                 "self_reference_policy": "These three generated indexes are separately hashed in the upload manifest and remote readback report."}
    scope = {"schema": SCHEMA + "-scope-v1", "source_file_count": source_count, "source_total_bytes": total_bytes,
             "included_file_count_before_indexes": len(included), "included_total_bytes_before_indexes": inventory["total_bytes"],
             "excluded": excluded, "changed_terrain_retained": changed_terrain,
             "retained_actual_download_zips": sorted(path for path in retained_paths if "/downloads/" in path and path.endswith(".zip")),
             "raw_sources_changed_or_deleted": False,
             "payload_storage": storage,
             "payload_storage_limit": "Hardlinks, when selected, are only a local storage arrangement for frozen source bytes. Git stores each path by its content blob; final source hashes and remote byte readback remain mandatory.",
             "acceptance_limit": "Archive integrity only. Workflow and public-site acceptance are stated in separate evidence, never inferred from this inventory."}
    sensitive = {"schema": SCHEMA + "-sensitive-scan-v1", "scanned_text_file_or_zip_member_count": scan_count,
                 "method": "Heuristic credential and authenticated-URL patterns; values and snippets are never included in this report.",
                 "limitation": "An empty result is not a guarantee; possible findings require review before upload.",
                 "findings_filenames_and_rule_names_only": findings, "review_needed_before_upload": bool(findings)}
    dump(destination / "archive-inventory.json", inventory)
    dump(destination / "archive-scope.json", scope)
    dump(destination / "archive-sensitive-scan.json", sensitive)
    upload = [{"path": path.relative_to(destination).as_posix(), **ident(path)}
              for path in sorted(destination.rglob("*")) if path.is_file()]
    expected = {row["path"]: row for row in included}
    for row in upload:
        if row["path"] in expected:
            assert row == expected[row["path"]], (row["path"], "Frozen source changed while preparing payload")
    dump(destination.parent / (destination.name + "-upload-manifest.json"), {"payload_root": str(destination), "source_root": str(source), "files": upload, "file_count": len(upload),
         "total_bytes": sum(row["bytes"] for row in upload), "unique_blob_count": len({row["gitblob"] for row in upload})})
    print(json.dumps({"destination": str(destination), "files": len(upload), "unique_blobs": len({row["gitblob"] for row in upload}),
                      "total_bytes": sum(row["bytes"] for row in upload), "sensitive_review_required": bool(findings)}, ensure_ascii=False))
    if findings:
        raise SystemExit("Archive upload blocked pending sensitive-field review")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    prepare(json.loads(args.config.read_text()))
