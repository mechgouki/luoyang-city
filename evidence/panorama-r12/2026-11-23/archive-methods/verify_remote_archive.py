#!/usr/bin/env python3
"""Independently verify a fixed evidence commit in a separately fetched bare repo.

Only Git object bytes and an external frozen-upload-manifest are read. The
manifest's local_path fields are never opened. No fetch, checkout, Git write,
source-worktree access, project test, or image acceptance decision is performed.
The caller must separately retain provenance for the fresh remote fetch.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


OID = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SCHEMA = "luoyang-frozen-upload-manifest-v1"
CHUNK = 1024 * 1024


class VerificationFailure(ValueError):
    def __init__(self, message, **details):
        super().__init__(message)
        self.details = details


def require(condition, message, **details):
    if not condition:
        raise VerificationFailure(message, **details)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def safe_path(value):
    require(isinstance(value, str) and value, "Empty or non-text repository path")
    require(not value.startswith("/") and "\\" not in value,
            "Absolute or backslash repository path", path=value)
    require(not re.match(r"^[A-Za-z]:", value), "Drive-qualified repository path", path=value)
    require(not any(ord(c) < 32 or ord(c) == 127 for c in value),
            "Control character in repository path", path=repr(value))
    parts = value.split("/")
    require(all(p not in ("", ".", "..") and p.casefold() != ".git" for p in parts),
            "Unsafe or non-canonical repository path", path=value)
    require(len(value.encode("utf-8")) <= 4096 and all(len(p.encode("utf-8")) <= 255 for p in parts),
            "Repository path exceeds filesystem-safe limits", path=value)
    return value


def is_int(value):
    return type(value) is int and value >= 0


def read_manifest(path, expected_parent, report):
    raw = path.read_bytes()
    report["manifest"] = {"path": str(path), "bytes": len(raw),
                          "sha256": hashlib.sha256(raw).hexdigest()}
    manifest = json.loads(raw)
    require(isinstance(manifest, dict) and manifest.get("schema") == SCHEMA,
            "Unexpected frozen-manifest schema")
    require(manifest.get("expected_single_parent") == expected_parent,
            "Manifest parent differs from --parent")
    raw_prefix = manifest.get("repository_prefix")
    require(isinstance(raw_prefix, str), "Missing repository_prefix")
    prefix = raw_prefix[:-1] if raw_prefix.endswith("/") else raw_prefix
    safe_path(prefix)
    require(prefix.startswith("evidence/"), "Manifest prefix must be below evidence/", prefix=prefix)
    rows = manifest.get("files")
    require(isinstance(rows, list), "Manifest files must be an array")
    files, blobs = {}, {}
    for row in rows:
        require(isinstance(row, dict), "Non-object manifest entry")
        name = safe_path(row.get("path"))
        require(name.startswith(prefix + "/"), "Manifest path escaped evidence prefix", path=name)
        require(name not in files, "Duplicate manifest path", path=name)
        require(row.get("mode") == "100644", "Frozen manifest contains a non-regular or unexpected mode", path=name)
        require(is_int(row.get("bytes")), "Invalid manifest byte count", path=name)
        require(isinstance(row.get("sha256"), str) and SHA256.fullmatch(row["sha256"]),
                "Invalid manifest SHA256", path=name)
        require(isinstance(row.get("git_blob_sha1"), str) and OID.fullmatch(row["git_blob_sha1"]),
                "Invalid manifest Git blob SHA1", path=name)
        identity = (row["bytes"], row["sha256"])
        previous = blobs.setdefault(row["git_blob_sha1"], identity)
        require(previous == identity, "Conflicting claims for one Git blob", blob=row["git_blob_sha1"])
        files[name] = row
    for name in files:
        parts = name.split("/")
        require(not any("/".join(parts[:i]) in files for i in range(1, len(parts))),
                "Manifest has a file/directory path collision", path=name)
    totals = {"file_count": len(files), "unique_blob_count": len(blobs),
              "logical_bytes": sum(r["bytes"] for r in files.values()),
              "unique_blob_bytes": sum(v[0] for v in blobs.values())}
    for key, value in totals.items():
        require(is_int(manifest.get(key)) and manifest[key] == value,
                "Frozen-manifest count is inconsistent", field=key, expected=value, actual=manifest.get(key))
    report["manifest"].update(schema=SCHEMA, repository_prefix=prefix, **totals)
    report["checks"]["frozen_manifest_structure"] = True
    return prefix, files


class GitObjects:
    """One cat-file --batch process; independently hash every object consumed."""

    def __init__(self, git_dir):
        self.git_dir = git_dir
        self.env = os.environ.copy()
        for key in ("GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
            require(not self.env.get(key), "External Git object store is not allowed", environment_key=key)
        self.env.update(GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0")
        self.command = ["git", "--no-pager", "--git-dir", str(git_dir)]
        require(self.run("rev-parse", "--is-bare-repository").strip() == b"true",
                "The supplied Git directory is not a bare repository")
        require(self.run("rev-parse", "--show-object-format").strip() == b"sha1",
                "This manifest requires a SHA1 Git repository")
        for relative in ("objects/info/alternates", "info/grafts"):
            candidate = git_dir / relative
            require(not candidate.exists() or not candidate.read_bytes().strip(),
                    "Alternates or grafts would invalidate independent object provenance", file=str(candidate))
        require(not (git_dir / "objects").is_symlink(), "Object directory must not be a symlink")
        self.process = subprocess.Popen(self.command + ["cat-file", "--batch"],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, env=self.env)
        self.object_counts = defaultdict(int)
        self.bytes_read = 0
        self.tree_cache = {}

    def run(self, *arguments):
        result = subprocess.run(self.command + list(arguments), env=self.env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        require(result.returncode == 0, "Read-only Git command failed",
                command=list(arguments), error=result.stderr.decode("utf-8", "replace")[:2000])
        return result.stdout

    def object(self, oid, wanted_type, *, collect=False):
        require(isinstance(oid, str) and OID.fullmatch(oid), "Expected an exact Git object ID", oid=oid)
        self.process.stdin.write((oid + "\n").encode("ascii"))
        self.process.stdin.flush()
        header = self.process.stdout.readline(1024)
        fields = header.rstrip(b"\n").split(b" ")
        require(len(fields) == 3 and fields[0] == oid.encode("ascii") and fields[2].isdigit(),
                "Missing object or malformed cat-file response", oid=oid, response=header.decode("ascii", "replace"))
        kind, size = fields[1].decode("ascii"), int(fields[2])
        require(kind == wanted_type, "Git object has the wrong type", oid=oid, wanted=wanted_type, actual=kind)
        require(not collect or size <= 64 * CHUNK, "Unreasonably large metadata object", oid=oid, size=size)
        git_hash = hashlib.sha1((kind + " " + str(size) + "\0").encode("ascii"))
        content_hash = hashlib.sha256()
        collected, remaining = [], size
        while remaining:
            block = self.process.stdout.read(min(CHUNK, remaining))
            require(block, "Unexpected EOF in Git object", oid=oid, remaining=remaining)
            remaining -= len(block)
            git_hash.update(block)
            content_hash.update(block)
            if collect:
                collected.append(block)
        require(self.process.stdout.read(1) == b"\n", "Missing cat-file object delimiter", oid=oid)
        require(git_hash.hexdigest() == oid, "Object bytes do not hash to the requested Git ID", oid=oid)
        self.object_counts[kind] += 1
        self.bytes_read += size
        return {"oid": oid, "type": kind, "bytes": size, "sha256": content_hash.hexdigest(),
                "data": b"".join(collected) if collect else None}

    def commit(self, oid):
        obj = self.object(oid, "commit", collect=True)
        header = obj["data"].split(b"\n\n", 1)[0].split(b"\n")
        trees, parents = [], []
        for line in header:
            for label, target in ((b"tree ", trees), (b"parent ", parents)):
                if line.startswith(label):
                    value = line[len(label):].decode("ascii")
                    require(OID.fullmatch(value), "Malformed commit header object ID", commit=oid)
                    target.append(value)
        require(len(trees) == 1, "Commit must contain exactly one tree header", commit=oid)
        return {"sha": oid, "tree_sha": trees[0], "parents": parents,
                "bytes": obj["bytes"], "content_sha256": obj["sha256"]}

    def tree(self, oid):
        if oid in self.tree_cache:
            return self.tree_cache[oid]
        raw = self.object(oid, "tree", collect=True)["data"]
        rows, names, offset = [], set(), 0
        while offset < len(raw):
            space, zero = raw.find(b" ", offset), raw.find(b"\0", offset)
            require(offset < space < zero and zero + 21 <= len(raw), "Malformed raw Git tree", tree=oid)
            mode = raw[offset:space].decode("ascii")
            name = raw[space + 1:zero].decode("utf-8", "strict")
            require("/" not in name, "Slash inside a tree entry name", tree=oid, name=name)
            safe_path(name)
            require(name not in names, "Duplicate name inside a Git tree", tree=oid, name=name)
            names.add(name)
            require(mode not in ("120000", "160000"), "Symbolic links and gitlinks are forbidden", tree=oid, name=name, mode=mode)
            require(mode in ("40000", "040000", "100644", "100755"),
                    "Unexpected Git tree mode", tree=oid, name=name, mode=mode)
            rows.append({"name": name, "mode": "040000" if mode in ("40000", "040000") else mode,
                         "type": "tree" if mode in ("40000", "040000") else "blob",
                         "sha": raw[zero + 1:zero + 21].hex()})
            offset = zero + 21
        self.tree_cache[oid] = rows
        return rows

    def inventory(self, root_tree):
        files, directories = {}, {}

        def walk(oid, prefix, chain):
            require(oid not in chain and len(chain) < 256, "Cyclic or excessive-depth Git tree", tree=oid)
            for row in self.tree(oid):
                name = safe_path(prefix + "/" + row["name"] if prefix else row["name"])
                require(name not in files and name not in directories, "Duplicate full Git tree path", path=name)
                identity = {"mode": row["mode"], "type": row["type"], "sha": row["sha"]}
                if row["type"] == "tree":
                    directories[name] = identity
                    walk(row["sha"], name, chain | {oid})
                else:
                    files[name] = identity

        walk(root_tree, "", set())
        return files, directories

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()


def verify(args, report):
    require(OID.fullmatch(args.commit) and OID.fullmatch(args.parent),
            "--commit and --parent must be exact lowercase 40-character IDs")
    prefix, expected = read_manifest(args.manifest, args.parent, report)
    objects = GitObjects(args.git_dir)
    report["object_source"] = {"git_dir": str(args.git_dir), "bare_repository": True,
                               "alternates_used": False, "replacement_objects_disabled": True,
                               "lazy_fetch_disabled": True, "source_worktree_files_read": False,
                               "network_operations_performed": False,
                               "fetch_provenance": "Caller must retain the separate fresh remote-fetch record."}
    try:
        archive, parent = objects.commit(args.commit), objects.commit(args.parent)
        report.update(archive=archive, production_parent=parent)
        require(archive["parents"] == [args.parent], "Archive does not have exactly the expected sole parent",
                expected=[args.parent], actual=archive["parents"])
        report["checks"]["exact_single_parent"] = True
        actual_files, actual_dirs = objects.inventory(archive["tree_sha"])
        parent_files, parent_dirs = objects.inventory(parent["tree_sha"])
        within = lambda p: p == prefix or p.startswith(prefix + "/")
        actual_prefix = {p: row for p, row in actual_files.items() if within(p)}
        outside = {p: row for p, row in actual_files.items() if not within(p)}
        parent_outside = {p: row for p, row in parent_files.items() if not within(p)}
        differences = [p for p in sorted(set(outside) | set(parent_outside)) if outside.get(p) != parent_outside.get(p)]
        require(not differences, "Production file paths, modes or blob IDs changed outside the evidence prefix",
                changed_paths=differences)
        ancestors = {"/".join(prefix.split("/")[:i]) for i in range(1, len(prefix.split("/")))}
        outside_dirs = {p: row for p, row in actual_dirs.items() if not within(p) and p not in ancestors}
        parent_outside_dirs = {p: row for p, row in parent_dirs.items() if not within(p) and p not in ancestors}
        require(outside_dirs == parent_outside_dirs, "An unrelated or empty directory tree changed outside the evidence prefix",
                changed_paths=[p for p in sorted(set(outside_dirs) | set(parent_outside_dirs)) if outside_dirs.get(p) != parent_outside_dirs.get(p)])
        report["checks"]["outside_prefix_complete_path_mode_blob_map_unchanged"] = True
        report["checks"]["outside_prefix_directory_trees_unchanged"] = True
        require(set(actual_prefix) == set(expected), "Archive path set differs from frozen manifest",
                missing_paths=sorted(set(expected) - set(actual_prefix)), extra_paths=sorted(set(actual_prefix) - set(expected)))
        expected_dirs = set()
        for name in expected:
            parts = name.split("/")
            expected_dirs.update("/".join(parts[:i]) for i in range(1, len(parts)) if within("/".join(parts[:i])))
        require({p for p in actual_dirs if within(p)} == expected_dirs,
                "Archive contains unexpected empty or missing directories inside the evidence prefix")
        report["checks"]["complete_prefix_path_set_matches_manifest"] = True
        groups = defaultdict(list)
        for name in sorted(expected):
            row, found = expected[name], actual_prefix[name]
            require(found["mode"] == row["mode"] and found["sha"] == row["git_blob_sha1"],
                    "Archive path mode or blob ID differs from manifest", path=name, actual=found)
            groups[found["sha"]].append(name)
        blob_results = {}
        for oid, paths in sorted(groups.items()):
            actual = objects.object(oid, "blob")
            expected_row = expected[paths[0]]
            require(actual["bytes"] == expected_row["bytes"] and actual["sha256"] == expected_row["sha256"],
                    "Real Git blob bytes or SHA256 differ from frozen manifest", blob=oid, paths=paths,
                    actual_bytes=actual["bytes"], actual_sha256=actual["sha256"],
                    expected_bytes=expected_row["bytes"], expected_sha256=expected_row["sha256"])
            blob_results[oid] = {"sha": oid, "bytes": actual["bytes"], "sha256": actual["sha256"], "path_count": len(paths)}
        report["files"] = [{"path": name, "mode": actual_prefix[name]["mode"], "git_blob_sha1": actual_prefix[name]["sha"],
                            "bytes": blob_results[actual_prefix[name]["sha"]]["bytes"],
                            "sha256": blob_results[actual_prefix[name]["sha"]]["sha256"], "matched": True}
                           for name in sorted(expected)]
        report["blobs"] = list(blob_results.values())
        report["statistics"] = {"verified_file_paths": len(expected), "verified_unique_blobs": len(blob_results),
                                "verified_logical_bytes": sum(v["bytes"] for v in expected.values()),
                                "verified_unique_blob_bytes": sum(v["bytes"] for v in blob_results.values()),
                                "outside_prefix_file_paths": len(outside), "outside_prefix_directory_trees": len(outside_dirs),
                                "archive_total_file_paths": len(actual_files), "production_total_file_paths": len(parent_files),
                                "verified_unique_tree_objects": len(objects.tree_cache),
                                "git_object_bytes_read": objects.bytes_read}
        report["checks"].update(all_manifest_files_verified_from_real_git_object_bytes=True,
                                every_blob_git_sha1_recomputed=True, every_blob_sha256_recomputed=True,
                                generated_index_files_included_without_exemption=True,
                                symlinks_gitlinks_and_unsafe_paths_rejected=True)
        report["generated_index_paths_verified"] = [p for p in sorted(expected)
            if p.rsplit("/", 1)[-1] in {"archive-inventory.json", "archive-scope.json", "archive-sensitive-scan.json"}]
        report["status"] = "passed"
    finally:
        objects.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git-dir", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--parent", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.git_dir, args.manifest, args.output = (p.resolve() for p in (args.git_dir, args.manifest, args.output))
    if args.output == args.git_dir or args.git_dir in args.output.parents or args.output == args.manifest:
        parser.error("Report output must be outside the bare repository and must not overwrite the frozen manifest")
    report = {"schema": "luoyang-independent-remote-archive-verification-v1", "status": "failed",
              "started_at_utc": utc_now(), "checks": {}, "requested_commit": args.commit,
              "requested_parent": args.parent, "verification_kind": "archive_identity_and_byte_integrity",
              "image_quality_or_historical_validity_checked": False,
              "note": "A passing archive verification is not image approval or historical validation."}
    try:
        verify(args, report)
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error),
                           "details": getattr(error, "details", {})}
    report["completed_at_utc"] = utc_now()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent, prefix=args.output.name + ".", delete=False) as temp:
        json.dump(report, temp, ensure_ascii=False, indent=2)
        temp.write("\n")
        temp_path = Path(temp.name)
    os.replace(temp_path, args.output)
    print(json.dumps({"status": report["status"], "report": str(args.output),
                      "statistics": report.get("statistics"), "error": report.get("error")}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
