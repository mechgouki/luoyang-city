#!/usr/bin/env python3
"""Prepare a native Git tree identity and bounded GitHub tree-upload plan.

This changes no index, working file or ref. Git mktree --missing computes real
tree objects from already hash-identified blobs; remote object upload and ref
creation remain separate explicitly authorized operations.
"""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path, PurePosixPath


def git(repo, *args, data=None):
    env = dict(os.environ, GIT_NO_REPLACE_OBJECTS="1", GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(["git", "-C", str(repo), *args], input=data,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=True)
    return result.stdout


def make_tree(repo, entries):
    raw = b"".join((f"{row['mode']} {row['type']} {row['sha']}\t".encode() + row["path"].encode() + b"\0")
                   for row in entries)
    return git(repo, "mktree", "--missing", "-z", data=raw).decode().strip()


def read_tree(repo, sha):
    rows = []
    for raw in git(repo, "ls-tree", "-z", sha).split(b"\0"):
        if not raw:
            continue
        metadata, path = raw.split(b"\t", 1)
        mode, typ, object_sha = metadata.decode().split()
        rows.append({"path": path.decode(), "mode": mode, "type": typ, "sha": object_sha})
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--base-commit", required=True)
    p.add_argument("--prefix", required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--chunk-size", type=int, default=100)
    a = p.parse_args()
    assert len(a.base_commit) == 40 and all(c in "0123456789abcdef" for c in a.base_commit)
    prefix = PurePosixPath(a.prefix)
    assert not prefix.is_absolute() and ".." not in prefix.parts and str(prefix) == a.prefix.strip("/")
    before = git(a.repo, "for-each-ref", "--format=%(refname)%00%(objectname)")
    raw_manifest = a.manifest.read_bytes()
    manifest = json.loads(raw_manifest)
    files = manifest["files"]
    assert len(files) == len({row["path"] for row in files})
    directories = {"": {}}
    flat = []
    for row in files:
        rel = PurePosixPath(row["path"])
        assert not rel.is_absolute() and ".." not in rel.parts and str(rel) == row["path"]
        assert all(c in "0123456789abcdef" for c in row["gitblob"]) and len(row["gitblob"]) == 40
        assert not any(c in row["path"] for c in ("\0", "\r", "\n", "\\"))
        for parent in rel.parents:
            directories.setdefault("" if str(parent) == "." else str(parent), {})
        parent = "" if str(rel.parent) == "." else str(rel.parent)
        directories[parent][rel.name] = {"path": rel.name, "mode": "100644", "type": "blob", "sha": row["gitblob"]}
        flat.append({"path": str(prefix / rel), "mode": "100644", "type": "blob", "sha": row["gitblob"]})
    subtree_shas = {}
    for name in sorted(directories, key=lambda value: (value.count("/") + bool(value), value), reverse=True):
        sha = make_tree(a.repo, list(directories[name].values()))
        subtree_shas[name] = sha
        if name:
            path = PurePosixPath(name)
            parent = "" if str(path.parent) == "." else str(path.parent)
            directories[parent][path.name] = {"path": path.name, "mode": "040000", "type": "tree", "sha": sha}
    base_tree = git(a.repo, "rev-parse", a.base_commit + "^{tree}").decode().strip()

    def graft(tree_sha, parts):
        entries = read_tree(a.repo, tree_sha) if tree_sha else []
        old = next((row for row in entries if row["path"] == parts[0]), None)
        if len(parts) == 1:
            assert old is None, "Refusing to overwrite an existing permanent archive directory"
            child = subtree_shas[""]
        else:
            assert old is None or old["type"] == "tree"
            child = graft(old["sha"] if old else None, parts[1:])
        replacement = {"path": parts[0], "mode": "040000", "type": "tree", "sha": child}
        entries = [row for row in entries if row["path"] != parts[0]] + [replacement]
        return make_tree(a.repo, entries)

    expected_root = graft(base_tree, prefix.parts)
    assert git(a.repo, "for-each-ref", "--format=%(refname)%00%(objectname)") == before
    flat.sort(key=lambda row: row["path"])
    chunks = [flat[start:start + a.chunk_size] for start in range(0, len(flat), a.chunk_size)]
    out = {"schema": "luoyang-r11-evidence-tree-plan-v1", "base_commit": a.base_commit, "base_tree": base_tree,
           "archive_prefix": str(prefix), "archive_subtree": subtree_shas[""], "expected_root_tree": expected_root,
           "file_count": len(flat), "manifest_sha256": hashlib.sha256(raw_manifest).hexdigest(),
           "upload_method": "Sequential chunks, first base_tree=base_tree and later base_tree=previous returned tree. Final result must equal expected_root_tree. No ref may be changed during tree preparation.",
           "chunk_size": a.chunk_size, "chunks": chunks, "refs_unchanged": True}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: out[key] for key in ("base_commit", "file_count", "archive_subtree", "expected_root_tree", "refs_unchanged")}))


if __name__ == "__main__":
    main()
