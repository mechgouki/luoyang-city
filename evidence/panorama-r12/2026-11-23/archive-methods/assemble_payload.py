#!/usr/bin/env python3
"""Assemble local R12 evidence into an empty directory; never freeze or publish it.

Use --dry-run while collection is still in progress. It hashes real files and
prints the proposed scope without creating or writing the destination. Without
--dry-run, copied bytes are checked and assembly-scope.json records the result.
Only authenticated Actions wrappers and the seven exact prior terrain objects
may be omitted; a retained non-terrain/Pages/auxiliary use blocks an exemption.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys


IDENTITY = ("bytes", "sha256", "git_blob_sha1")
TERRAIN = "terrain-products-v30/"
TERRAIN_NAMES = {
    "contours-25m-wgs84.geojson", "display-dsm-sigma90m.tif", "hillshade-display.tif",
    "modern-dsm-30m.tif", "native-samples-wgs84.tif", "slope-display-sigma90m-deg.tif",
    "slope-native-scale-deg.tif",
}
TERRAIN_SUPPORT = (TERRAIN + "SOURCE-NOTICE.txt", TERRAIN + "metadata.json")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def relative_name(value):
    need(isinstance(value, str) and value and "\\" not in value and "\0" not in value,
         "Invalid relative path: " + repr(value))
    path = PurePosixPath(value)
    need(not path.is_absolute() and ".." not in path.parts and str(path) == value
         and value != "." and not re.match(r"^[A-Za-z]:", value), "Unsafe path: " + value)
    return value


def stamp(path):
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode), "Expected regular file: " + str(path))
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def identity(path):
    before = stamp(path)
    sha = hashlib.sha256()
    blob = hashlib.sha1(("blob %d\0" % before[2]).encode())
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            size += len(block)
            sha.update(block)
            blob.update(block)
    need(before == stamp(path) and size == before[2], "File changed while hashing: " + str(path))
    return dict(bytes=size, sha256=sha.hexdigest(), git_blob_sha1=blob.hexdigest())


def declared_identity(entry):
    need(type(entry.get("bytes")) is int and entry["bytes"] >= 0, "Invalid byte count")
    for field, length in (("sha256", 64), ("git_blob_sha1", 40)):
        need(isinstance(entry.get(field), str) and re.fullmatch("[0-9a-f]{%d}" % length, entry[field]),
             "Invalid " + field)
    return {key: entry[key] for key in IDENTITY}


def snapshot(root):
    def fail_walk(error):
        raise error

    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=fail_walk):
        for name in dirs:
            path = Path(directory) / name
            need(not path.is_symlink(), "Directory symlink is not allowed: " + str(path))
        for name in files:
            path = Path(directory) / name
            result[relative_name(path.relative_to(root).as_posix())] = stamp(path)
    return result


def checked_root(raw):
    path = Path(raw).absolute()
    for ancestor in (path, *path.parents):
        need(not ancestor.is_symlink(), "Symlink is not allowed: " + str(ancestor))
    return path.resolve()


def empty_destination(out):
    need(not out.exists() or out.is_dir() and not any(out.iterdir()),
         "Destination must be absent or an empty directory: " + str(out))


def read_reference(path):
    before = identity(path)
    document = json.loads(path.read_bytes())
    need(identity(path) == before, "Terrain reference changed while reading")
    need(re.fullmatch(r"[0-9a-f]{40}", document.get("source_commit", "")), "Invalid reference commit")
    need(re.fullmatch(r"[0-9a-f]{64}", document.get("source_sha256", "")), "Invalid reference source digest")
    relative_name(document["source_path"])
    members = document.get("members", [])
    need(len(members) == 7, "Expected exactly seven fixed terrain reference members")
    by_path = {}
    for member in members:
        source = relative_name(member["path"])
        need(source.count(TERRAIN) == 1, "Invalid terrain reference path: " + source)
        logical = TERRAIN + source.split(TERRAIN, 1)[1]
        need(logical not in by_path, "Duplicate terrain reference: " + logical)
        need(member.get("reason_code") == "unchanged_terrain_intermediate", "Unexpected exemption reason")
        by_path[logical] = dict(reference_path=source, **declared_identity({
            **member, "git_blob_sha1": member.get("gitblob")}))
    need(set(by_path) == {TERRAIN + name for name in TERRAIN_NAMES}, "Terrain reference scope changed")
    return dict(file_name=path.name, **before, document=document), by_path


def plan(staging, terrain_reference):
    initial = snapshot(staging)
    need("assembly-scope.json" not in initial, "Staging is already an assembled payload")
    files = {name: identity(staging / name) for name in sorted(initial)}
    reference, allowed = read_reference(terrain_reference)
    refs = defaultdict(list)
    ingests = {}
    for name in files:
        if name.startswith("cas/objects/"):
            need(re.fullmatch(r"cas/objects/sha256/[0-9a-f]{64}", name), "Unexpected CAS object: " + name)
            need(files[name]["sha256"] == name.rsplit("/", 1)[1], "CAS name/content mismatch: " + name)
        if not name.startswith("cas/ingests/"):
            continue
        need(name.endswith(".json"), "Unexpected ingest file: " + name)
        doc = json.loads((staging / name).read_bytes())
        need(doc.get("schema") == "luoyang-actions-cas-ingest-v1", "Unknown ingest schema: " + name)
        need(doc.get("kind") in ("evidence", "pages"), "Unknown artifact kind: " + name)
        declared_identity(doc["artifact_zip"])
        members = {}
        for member in doc["members"]:
            logical = relative_name(member["path"])
            need(logical not in members, "Duplicate logical artifact path: " + name + ":" + logical)
            declared_identity(member)
            need(doc["kind"] != "evidence" or "retained_path" in member,
                 "Evidence ingest omitted a member: " + name + ":" + logical)
            members[logical] = member
        need(doc["member_count"] == len(members), "Ingest member count differs: " + name)
        if doc["kind"] == "pages":
            for logical in doc["pages"]["required_retained_paths"]:
                need(logical in members and "retained_path" in members[logical],
                     "Selected Pages bytes missing: " + name + ":" + logical)
        ingests[name] = dict(document=doc, members=members)

        def visit(value, pointer=""):
            if isinstance(value, dict):
                if "retained_path" in value:
                    retained = relative_name(value["retained_path"])
                    wanted = declared_identity(value)
                    need(retained == "objects/sha256/" + wanted["sha256"], "Noncanonical CAS reference")
                    object_path = "cas/" + retained
                    need(object_path in files and files[object_path] == wanted,
                         "Missing or changed retained object: " + name + pointer)
                    is_member = bool(re.fullmatch(r"/members/\d+", pointer))
                    refs[object_path].append(dict(ingest=name, ingest_label=doc["label"],
                        artifact_kind=doc["kind"], pointer=pointer,
                        role="artifact_member" if is_member else "auxiliary",
                        logical_path=value["path"] if is_member else None,
                        collection_retained_path=retained))
                for key, child in value.items():
                    visit(child, pointer + "/" + key.replace("~", "~0").replace("/", "~1"))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    visit(child, pointer + "/" + str(index))
        visit(doc)
    need(ingests, "No completed artifact ingests found")

    excluded = {}
    exceptions = []
    support = {}
    for object_path, uses in sorted(refs.items()):
        eligible = all(use["role"] == "artifact_member" and use["artifact_kind"] == "evidence"
            and use["logical_path"] in allowed
            and files[object_path] == {key: allowed[use["logical_path"]][key] for key in IDENTITY}
            for use in uses)
        if not eligible:
            continue
        # Both original notices must be retained by every ingest taking an exemption.
        if not all(all(logical in ingests[use["ingest"]]["members"] and
                       "retained_path" in ingests[use["ingest"]]["members"][logical]
                       for logical in TERRAIN_SUPPORT) for use in uses):
            continue
        excluded[object_path] = dict(reason_code="unchanged_terrain_intermediate",
                                    retained_reference_count=len(uses))
        for use in uses:
            exceptions.append(dict(**use, object_path=object_path, **files[object_path],
                reference_member_path=allowed[use["logical_path"]]["reference_path"],
                permanent_original_bytes_retained=False))
            for logical in TERRAIN_SUPPORT:
                item = ingests[use["ingest"]]["members"][logical]
                support[(use["ingest"], logical)] = dict(ingest=use["ingest"], logical_path=logical,
                    object_path="cas/" + item["retained_path"], **declared_identity(item))

    for name, file_identity in files.items():
        parts = PurePosixPath(name).parts
        # Only the run's direct download directory can contain temporary wrappers.
        # ZIP members downloaded by browsers are CAS objects and are never filtered here.
        if len(parts) == 3 and parts[0] != "cas" and parts[1] == "downloads" and name.endswith(".zip"):
            matches = [ingest for ingest, entry in ingests.items()
                       if declared_identity(entry["document"]["artifact_zip"]) == file_identity]
            if matches:
                excluded[name] = dict(reason_code="actions_zip_transport_wrapper", ingests=matches)
    for entry in support.values():
        need(entry["object_path"] not in excluded, "Terrain source notice/metadata cannot be excluded")
    need(snapshot(staging) == initial, "Staging changed during planning; retry after collection settles")

    copying = [dict(path=name, **value) for name, value in files.items() if name not in excluded]
    exclusions = [dict(path=name, **files[name], **reason) for name, reason in sorted(excluded.items())]
    counts = dict(source_files=len(files), source_bytes=sum(x["bytes"] for x in files.values()),
        copied_files=len(copying), copied_bytes=sum(x["bytes"] for x in copying),
        excluded_files=len(exclusions), excluded_bytes=sum(x["bytes"] for x in exclusions),
        copied_cas_objects=sum(x["path"].startswith("cas/objects/") for x in copying),
        unchanged_terrain_objects=sum(x["reason_code"] == "unchanged_terrain_intermediate" for x in exclusions),
        terrain_logical_exceptions=len(exceptions),
        actions_wrappers=sum(x["reason_code"] == "actions_zip_transport_wrapper" for x in exclusions),
        unchanged_ingest_files=len(ingests))
    scope = dict(schema="luoyang-r12-evidence-assembly-scope-v1",
        status="dry_run_only_not_assembled", planned_counts=counts,
        actual_counts=dict(copied_files=0, copied_bytes=0, excluded_files=0, excluded_bytes=0),
        planned_copy_files=copying, planned_excluded_files=exclusions,
        terrain_reference=reference, terrain_exceptions=exceptions,
        retained_terrain_source_material=list(support.values()),
        ingest_semantics=("Original ingest JSON bytes are copied unchanged. Each retained_path describes the "
            "collection-layer CAS location, not an unconditional promise of permanent original bytes. "
            "The per-ingest/path terrain exceptions here override permanent retention only; their exact "
            "identity was checked against actual collected bytes and the fixed reference. Original Pages "
            "unretained members remain identity-ledger entries, not a claim of permanent byte retention."),
        preservation_rule=("All other staged files and CAS objects are copied, including unreferenced objects, "
            "original reports/screenshots, actual browser downloads (including ZIPs), API metadata, selected "
            "Pages bytes and unmatched/new terrain. Any auxiliary, Pages or non-whitelisted logical use "
            "prevents a terrain object exemption."),
        inventory_note=("Counts cover staged source files only. This generated assembly-scope.json and later "
            "README/acceptance/inventory files must be included in the final independent freeze. Assembly "
            "does not certify collection completeness, acceptance, upload or publication."))
    return scope, initial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--terrain-reference", required=True)
    parser.add_argument("--dry-run", action="store_true", help="Read/hash/plan only; write nothing")
    args = parser.parse_args()
    staging, out, reference = (checked_root(value) for value in
                               (args.staging, args.out, args.terrain_reference))
    need(staging.is_dir(), "Staging directory is missing")
    need(staging != out and staging not in out.parents and out not in staging.parents,
         "Staging and destination must be separate, non-nested directories")
    empty_destination(out)
    scope, initial = plan(staging, reference)
    if args.dry_run:
        print(json.dumps(scope, ensure_ascii=False, indent=2))
        return
    empty_destination(out)
    need(snapshot(staging) == initial, "Staging changed before copying")
    out.mkdir(parents=True, exist_ok=True)
    for entry in scope["planned_copy_files"]:
        target = out / entry["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        need(not target.exists(), "Refusing to overwrite destination file: " + str(target))
        shutil.copyfile(staging / entry["path"], target)
        need(identity(target) == {key: entry[key] for key in IDENTITY},
             "Copied byte identity differs: " + entry["path"])
    need(snapshot(staging) == initial, "Staging changed while copying; output is incomplete and not accepted")
    scope["status"] = "assembled_not_frozen_or_accepted"
    scope["actual_counts"] = dict(scope["planned_counts"])
    scope["copied_files"] = scope.pop("planned_copy_files")
    scope["excluded_files"] = scope.pop("planned_excluded_files")
    with (out / "assembly-scope.json").open("x", encoding="utf-8") as stream:
        json.dump(scope, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(dict(scope=str(out / "assembly-scope.json"), status=scope["status"],
                          actual_counts=scope["actual_counts"]), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("Assembly refused: " + str(error), file=sys.stderr)
        sys.exit(2)
