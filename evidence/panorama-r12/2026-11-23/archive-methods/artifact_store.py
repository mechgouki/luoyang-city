#!/usr/bin/env python3
"""Ingest an actual Actions ZIP without duplicating large member bytes.

No network or repository writes. Original member bytes are addressed by SHA256;
ingest manifests retain every original path, size, digest and Git blob identity.
Pages archives retain the full member identity ledger but only the current V14
publication, build metadata, and two homepage bytes. Evidence archives retain
every file. Wrappers are audited, not copied into the permanent store.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
import tempfile
import zipfile


def clean_name(raw, directory=False):
    if not isinstance(raw, str) or "\\" in raw or "\x00" in raw:
        raise ValueError("Invalid archive path")
    while raw.startswith("./"):
        raw = raw[2:]
    if directory:
        raw = raw.rstrip("/")
    if raw in ("", ".") and directory:
        return ""
    parts = PurePosixPath(raw).parts
    if not parts or raw.startswith("/") or ".." in parts or re.match(r"^[A-Za-z]:", raw):
        raise ValueError("Unsafe archive path: " + repr(raw))
    canonical = str(PurePosixPath(raw))
    if canonical != raw:
        raise ValueError("Noncanonical archive path: " + repr(raw))
    return canonical


def hash_stream(stream, size, root=None, retain=False):
    h = hashlib.sha256()
    g = hashlib.sha1(("blob %d\0" % size).encode())
    n = 0
    tmp = None
    handle = None
    if retain:
        (root / "objects" / "sha256").mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".incoming-", dir=root / "objects")
        handle = os.fdopen(fd, "wb")
    try:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            n += len(block)
            if n > size:
                raise ValueError("Archive member exceeds declared size")
            h.update(block)
            g.update(block)
            if handle:
                handle.write(block)
        if n != size:
            raise ValueError("Archive member size mismatch")
        result = {"bytes": n, "sha256": h.hexdigest(), "git_blob_sha1": g.hexdigest()}
        if handle:
            handle.close()
            handle = None
            relative = "objects/sha256/" + h.hexdigest()
            target = root / relative
            if target.exists():
                if target.is_symlink() or target.stat().st_size != n:
                    raise ValueError("Existing object identity mismatch")
                with target.open("rb") as old:
                    if hash_stream(old, n)["sha256"] != h.hexdigest():
                        raise ValueError("Existing object content mismatch")
            else:
                os.replace(tmp, target)
                tmp = None
            result["retained_path"] = relative
        return result
    finally:
        if handle:
            handle.close()
        if tmp and Path(tmp).exists():
            Path(tmp).unlink()


def load_retained(root, entry):
    return json.loads((root / entry["retained_path"]).read_bytes())


def checked_zip_members(z):
    seen = set()
    members = []
    for member in z.infolist():
        name = clean_name(member.filename, member.is_dir())
        if name in seen:
            raise ValueError("Duplicate archive member: " + name)
        seen.add(name)
        mode = member.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise ValueError("Nonregular ZIP member: " + name)
        if member.flag_bits & 1:
            raise ValueError("Encrypted ZIP member: " + name)
        if not member.is_dir():
            members.append((name, member))
    return members


def ingest(args):
    root = Path(args.out).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", args.label):
        raise ValueError("Label must be a simple file identifier")
    output = root / "ingests" / (args.label + ".json")
    if output.exists():
        raise ValueError("Ingest label already exists; use a new label")
    source = Path(args.zip)
    with source.open("rb") as f:
        wrapper = hash_stream(f, source.stat().st_size)
    metadata = json.loads(Path(args.artifact_metadata).read_bytes()) if args.artifact_metadata else {}
    expected = args.expected_sha256 or metadata.get("digest")
    if not expected:
        raise ValueError("Supply the actual API artifact digest or --expected-sha256")
    expected = expected.removeprefix("sha256:").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or expected != wrapper["sha256"]:
        raise ValueError("Actions ZIP digest does not match expected identity")
    report = {"schema": "luoyang-actions-cas-ingest-v1", "label": args.label,
              "kind": args.kind, "status": "byte_ingest_verified_not_release_acceptance",
              "artifact_zip": wrapper, "artifact_api": metadata, "members": [],
              "note": "Member bytes retained unchanged. Original paths map to content-addressed objects. Wrapper ZIP not copied."}
    if args.artifact_metadata:
        raw = Path(args.artifact_metadata).read_bytes()
        report["artifact_api_raw"] = hash_stream(io.BytesIO(raw), len(raw), root, True)
    with zipfile.ZipFile(source) as z:
        zmembers = checked_zip_members(z)
        if args.kind == "evidence":
            for name, member in zmembers:
                with z.open(member) as stream:
                    item = hash_stream(stream, member.file_size, root, True)
                report["members"].append(dict(path=name, **item))
        else:
            tars = [(name, m) for name, m in zmembers if name.endswith(".tar")]
            if len(tars) != 1 or len(zmembers) != 1:
                raise ValueError("Pages ZIP must contain one regular TAR member")
            tar_name, tar_member = tars[0]
            with z.open(tar_member) as f:
                report["pages_tar"] = dict(path=tar_name, **hash_stream(f, tar_member.file_size))
            keep = {"build-info.json", "release.json", "index.html", "v3.0-dual.html", ".nojekyll"}
            prefixes = ["panorama-v14/", *(args.keep_prefix or [])]
            seen = set()
            with z.open(tar_member) as stream, tarfile.open(fileobj=stream, mode="r|*") as t:
                for m in t:
                    name = clean_name(m.name, m.isdir())
                    if not name and m.isdir():
                        continue
                    if name in seen:
                        raise ValueError("Duplicate TAR member: " + name)
                    seen.add(name)
                    if m.isdir():
                        continue
                    if not m.isfile() or m.issym() or m.islnk():
                        raise ValueError("Nonregular TAR member: " + name)
                    with t.extractfile(m) as f:
                        item = hash_stream(f, m.size, root, name in keep or any(name.startswith(p) for p in prefixes))
                    report["members"].append(dict(path=name, **item))
            entries = {x["path"]: x for x in report["members"]}
            if "build-info.json" not in entries:
                raise ValueError("Actual Pages TAR has no build-info.json")
            info = load_retained(root, entries["build-info.json"])
            hashes = info["files_sha256"]
            problems = []
            excluded_controls = []
            for path, digest in hashes.items():
                if path == ".nojekyll" and path not in entries and digest == hashlib.sha256(b"").hexdigest():
                    excluded_controls.append(path)
                    continue
                if path not in entries or entries[path]["sha256"] != digest:
                    problems.append(path)
            unknown = sorted(set(entries) - set(hashes) - {"build-info.json", ".nojekyll"})
            if problems or unknown:
                raise ValueError("Pages manifest mismatch: " + json.dumps({"mismatch": problems, "unlisted": unknown}))
            meta = info.get("panorama_review_v14")
            if not meta or meta["source_commit"] != info["source_commit"]:
                raise ValueError("V14 source identity missing or inconsistent")
            required = set(meta["files_sha256"]) | set(meta["download_files"]) | {
                meta["page"], meta["record"], meta["manifest"]} | keep
            required.discard(".nojekyll")
            missing = [p for p in required if p not in entries]
            if missing:
                raise ValueError("Missing mandatory Pages files: " + repr(missing))
            additional = {p for p in required if "retained_path" not in entries[p]}
            if additional:
                with z.open(tar_member) as stream, tarfile.open(fileobj=stream, mode="r|*") as t:
                    for m in t:
                        name = clean_name(m.name, m.isdir())
                        if name in additional:
                            with t.extractfile(m) as f:
                                entries[name].update(hash_stream(f, m.size, root, True))
            report["pages"] = {"source_commit": info["source_commit"],
                "publication_status": meta["status"], "review_status": meta["review_status"],
                "homepage_replacement_approved": meta["homepage_replacement_approved"],
                "empty_build_control_not_in_tar": excluded_controls,
                "full_member_inventory_verified": True, "download_files": meta["download_files"],
                "required_retained_paths": sorted(required),
                "omitted_bytes_scope": "Other Pages member identities are in the full ledger, but their bytes are not retained by this selective ingest. Any unchanged-prior-archive exemption needs a separate exact fixed-reference hash check."}
    report["member_count"] = len(report["members"])
    report["logical_retained_bytes"] = sum(x["bytes"] for x in report["members"] if "retained_path" in x)
    unique = {x["sha256"]: x["bytes"] for x in report["members"] if "retained_path" in x}
    report["unique_retained_bytes"] = sum(unique.values())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"manifest": str(output), "members": report["member_count"],
        "logical_bytes": report["logical_retained_bytes"], "unique_bytes": report["unique_retained_bytes"]}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", required=True)
    p.add_argument("--kind", choices=["pages", "evidence"], required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--artifact-metadata", help="Unchanged single artifact API JSON")
    p.add_argument("--expected-sha256", help="Actual GitHub API digest when metadata is supplied separately")
    p.add_argument("--keep-prefix", action="append", help="Extra Pages prefix selection; default panorama-v14/")
    ingest(p.parse_args())


if __name__ == "__main__":
    main()
