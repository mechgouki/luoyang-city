#!/usr/bin/env python3
"""Freeze exact local archive files for a connector upload and independent reread.

Write the result OUTSIDE the directory being frozen to avoid self reference.
Does not upload, create Git objects, commit, or change a repository.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--prefix", required=True, help="Exact repository evidence prefix")
    p.add_argument("--parent", required=True, help="Exact production commit")
    p.add_argument("--output", required=True)
    args = p.parse_args()
    root = Path(args.root).resolve()
    output = Path(args.output).resolve()
    if output == root or root in output.parents:
        raise ValueError("Frozen manifest must be outside its own input tree")
    if not args.prefix.startswith("evidence/") or ".." in Path(args.prefix).parts or "\\" in args.prefix:
        raise ValueError("Expected a safe evidence/ repository prefix")
    if not re.fullmatch(r"[0-9a-f]{40}", args.parent):
        raise ValueError("Expected an exact 40-character production commit")
    entries = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symbolic links are not allowed: " + str(path))
        if not path.is_file():
            continue
        size = path.stat().st_size
        sha = hashlib.sha256()
        blob = hashlib.sha1(("blob %d\0" % size).encode())
        with path.open("rb") as f:
            while block := f.read(1024 * 1024):
                sha.update(block)
                blob.update(block)
        relative = path.relative_to(root).as_posix()
        entries.append({"path": args.prefix.rstrip("/") + "/" + relative,
            "local_path": str(path), "bytes": size, "sha256": sha.hexdigest(),
            "git_blob_sha1": blob.hexdigest(), "mode": "100644"})
    unique = {x["git_blob_sha1"]: x["bytes"] for x in entries}
    result = {"schema": "luoyang-frozen-upload-manifest-v1", "expected_single_parent": args.parent,
        "repository_prefix": args.prefix, "file_count": len(entries), "unique_blob_count": len(unique),
        "logical_bytes": sum(x["bytes"] for x in entries), "unique_blob_bytes": sum(unique.values()),
        "files": entries,
        "note": "Upload plan only. Root tree and all actual remote bytes require a separate independent readback."}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "files"}))


if __name__ == "__main__":
    main()
