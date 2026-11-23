#!/usr/bin/env python3
"""Independently hash every archived Git blob against the upload manifest.

The caller fetches the exact immutable archive commit from origin first and
records GitHub's branch/commit API identity separately. This verifier reads the
objects directly, without trusting a checked-out copy or a previous report.
"""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


def run(repo, *args):
    env = dict(os.environ, GIT_NO_REPLACE_OBJECTS="1", GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    return subprocess.check_output(["git", "-C", str(repo), *args], env=env)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--expected-parent", required=True)
    p.add_argument("--expected-root-tree", required=True)
    p.add_argument("--prefix", required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    assert len(a.commit) == 40 and all(c in "0123456789abcdef" for c in a.commit)
    assert len(a.expected_parent) == 40 and all(c in "0123456789abcdef" for c in a.expected_parent)
    assert len(a.expected_root_tree) == 40 and all(c in "0123456789abcdef" for c in a.expected_root_tree)
    assert a.output.resolve() != a.manifest.resolve()
    assert a.repo.resolve() not in a.output.resolve().parents
    prefix = a.prefix.strip("/") + "/"
    assert not prefix.startswith("/") and ".." not in prefix.split("/")
    before_refs = run(a.repo, "for-each-ref", "--format=%(refname)%00%(objectname)")
    parents = run(a.repo, "show", "-s", "--format=%P", a.commit).decode().strip().split()
    assert parents == [a.expected_parent], (parents, "Archive is not a direct child of the accepted production commit")
    actual_root = run(a.repo, "rev-parse", a.commit + "^{tree}").decode().strip()
    assert actual_root == a.expected_root_tree
    manifest_bytes = a.manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    for key in ("payload_root", "source_root"):
        if manifest.get(key):
            assert Path(manifest[key]).resolve() not in a.output.resolve().parents
    expected = {prefix + row["path"]: row for row in manifest["files"]}
    assert len(expected) == len(manifest["files"])
    changed = set(run(a.repo, "diff", "--name-only", "-z", a.expected_parent, a.commit).decode().rstrip("\0").split("\0"))
    assert changed == set(expected), "Changes outside the exact new archive file set"
    actual = {}
    for line in run(a.repo, "ls-tree", "-r", "-z", a.commit, "--", prefix).split(b"\0"):
        if not line:
            continue
        metadata, raw_path = line.split(b"\t", 1)
        mode, typ, sha = metadata.decode().split()
        name = raw_path.decode()
        assert mode == "100644" and typ == "blob", (name, mode, typ)
        actual[name] = sha
    assert set(actual) == set(expected), {"missing": sorted(set(expected)-set(actual)), "extra": sorted(set(actual)-set(expected))}
    env = dict(os.environ, GIT_NO_REPLACE_OBJECTS="1", GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    process = subprocess.Popen(["git", "-C", str(a.repo), "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env)
    verified, unique = [], {}
    try:
        for name in sorted(actual):
            sha, row = actual[name], expected[name]
            assert sha == row["gitblob"], (name, "Tree SHA differs")
            if sha not in unique:
                process.stdin.write((sha + "\n").encode())
                process.stdin.flush()
                header = process.stdout.readline().decode().strip().split()
                assert len(header) == 3 and header[0] == sha and header[1] == "blob", header
                size = int(header[2])
                raw = process.stdout.read(size)
                assert len(raw) == size and process.stdout.read(1) == b"\n"
                unique[sha] = {"bytes": size, "sha256": hashlib.sha256(raw).hexdigest(),
                               "gitblob": hashlib.sha1(f"blob {size}\0".encode() + raw).hexdigest()}
            obtained = unique[sha]
            assert obtained == {key: row[key] for key in ("bytes", "sha256", "gitblob")}, (name, "Blob bytes differ")
            verified.append({"path": name, **obtained})
    finally:
        process.stdin.close()
        process.wait()
    assert process.returncode == 0
    generated = {"archive-inventory.json", "archive-scope.json", "archive-sensitive-scan.json"}
    inventory = json.loads(run(a.repo, "show", a.commit + ":" + prefix + "archive-inventory.json"))
    indexed = {row["path"]: row for row in inventory["files"]}
    projected = {row["path"]: row for row in manifest["files"] if row["path"] not in generated}
    assert indexed == projected and inventory["file_count"] == len(indexed)
    scope = json.loads(run(a.repo, "show", a.commit + ":" + prefix + "archive-scope.json"))
    omitted = {row["path"]: row for row in scope["excluded"]}
    assert not set(omitted).intersection(indexed)
    assert scope["source_file_count"] == len(indexed) + len(omitted)
    for wrapper in inventory["verified_artifact_wrappers"]:
        assert wrapper["path"] in omitted
        assert wrapper["member_count"] == len(wrapper["members"])
        for member in wrapper["members"]:
            retained = member["path"] in indexed
            assert retained == member["retained_separately"]
            row = indexed[member["path"]] if retained else omitted[member["path"]]
            assert all(row[key] == member[key] for key in ("bytes", "sha256", "gitblob"))
    scan = json.loads(run(a.repo, "show", a.commit + ":" + prefix + "archive-sensitive-scan.json"))
    assert scan["review_needed_before_upload"] is False and not scan["findings_filenames_and_rule_names_only"]
    assert run(a.repo, "for-each-ref", "--format=%(refname)%00%(objectname)") == before_refs
    report = {"schema": "luoyang-r11-archive-remote-readback-v1", "status": "passed", "archive_commit": a.commit,
              "archive_tree": actual_root, "archive_parent": a.expected_parent,
              "exact_source_tree_preserved_outside_new_archive": True,
              "archive_indexes_and_wrapper_members_reconciled": True, "refs_unchanged": True,
              "prefix": prefix, "file_count": len(verified), "unique_blob_count": len(unique),
              "total_bytes": sum(row["bytes"] for row in verified),
              "upload_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
              "verification_method": "Exact immutable Git tree enumeration and independent per-blob byte/SHA256/Git-blob verification; no checkout or prior readback result is trusted.",
              "files": verified, "errors": []}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "archive_commit", "file_count", "unique_blob_count", "total_bytes")}))


if __name__ == "__main__":
    main()
