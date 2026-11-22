"""Verify an indexed evidence archive in an already-fetched Git commit.

Read-only: no network access, fetch, checkout, repository/index edits, or result
files. The local index itself must exist at PREFIX + basename(--index) in the
commit; its exact bytes are verified separately because it cannot hash itself.
Each distinct blob is read once through git cat-file --batch, including blobs
reused at several paths. A compact JSON result goes to stdout; any discrepancy
exits nonzero. This verifies archived bytes, not release/CI acceptance.

Example (substitute an actual fetched commit, never a branch name):
    python3 verify-remote-archive.py --repo /path/to/luoyang-city \
      --commit FULL_40_CHARACTER_COMMIT_SHA --index /path/to/archive-index.json
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


SCHEMA = "luoyang-evidence-archive-readback-v1"
DEFAULT_PREFIX = "evidence/city-nodes-r7/2026-11-22/"
SHA1 = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")


class VerificationError(ValueError):
    def __init__(self, message, **details):
        super().__init__(message)
        self.details = details


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise VerificationError(message)


def relative_path(value):
    if not isinstance(value, str) or not value or "\0" in value or "\\" in value:
        raise VerificationError("Invalid archive-relative path", path=value)
    path = PurePosixPath(value)
    if (path.is_absolute() or value in (".", "..") or ".." in path.parts
            or path.as_posix() != value):
        raise VerificationError("Archive paths must be normalized relative POSIX paths", path=value)
    return value


def fingerprint_bytes(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                git_blob_sha=hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest())


def read_local_index(path):
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    if ((before.st_size, before.st_mtime_ns, before.st_ino)
            != (after.st_size, after.st_mtime_ns, after.st_ino)
            or len(raw) != before.st_size):
        raise VerificationError("Local index changed while being read")
    document = json.loads(raw)
    if not isinstance(document, dict) or not isinstance(document.get("files"), list):
        raise VerificationError("Index must contain a files array")
    return raw, document


def expected_files(document, index_name, index_raw, prefix):
    expected, unique = {}, {}
    for item in document["files"]:
        if not isinstance(item, dict):
            raise VerificationError("Malformed index file entry")
        path = relative_path(item.get("path"))
        if path == index_name:
            raise VerificationError("Index must not include a self-referential file entry", path=path)
        size, sha256, blob = item.get("bytes"), item.get("sha256"), item.get("git_blob_sha")
        if (type(size) is not int or size < 0 or not isinstance(sha256, str)
                or not SHA256.fullmatch(sha256) or not isinstance(blob, str) or not SHA1.fullmatch(blob)):
            raise VerificationError("Malformed length or checksum in index", path=path)
        full_path = prefix + path
        if full_path in expected:
            raise VerificationError("Duplicate index path", path=path)
        expected[full_path] = dict(bytes=size, sha256=sha256, git_blob_sha=blob)
    expected[prefix + index_name] = fingerprint_bytes(index_raw)
    for path, item in expected.items():
        blob = item["git_blob_sha"]
        if blob in unique and unique[blob] != item:
            raise VerificationError("Conflicting size or SHA-256 for one Git blob", path=path, blob=blob)
        unique[blob] = item
    return expected, unique


class ReadOnlyGit:
    def __init__(self, repo):
        self.command = ["git", "--no-optional-locks", "--no-replace-objects",
                        "--literal-pathspecs", "-c", "protocol.allow=never", "-C", str(repo)]
        self.env = os.environ.copy()
        # --repo, not an inherited shell override, selects the object database.
        for name in ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE",
                     "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
            self.env.pop(name, None)
        self.env.update(GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0",
                        GIT_OPTIONAL_LOCKS="0", GIT_NO_REPLACE_OBJECTS="1")

    def run(self, *args):
        result = subprocess.run(self.command + list(args), env=self.env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode:
            raise VerificationError("Git read failed", operation=args[0],
                                    detail=result.stderr.decode("utf-8", "replace").strip()[:1200])
        return result.stdout

    def tree(self, commit, prefix):
        raw = self.run("ls-tree", "-r", "-z", "--full-tree", commit, "--", prefix)
        result = {}
        for entry in raw.split(b"\0"):
            if not entry:
                continue
            metadata, path_raw = entry.split(b"\t", 1)
            mode, kind, blob = metadata.decode("ascii").split(" ")
            path = path_raw.decode("utf-8")
            if not path.startswith(prefix) or path in result:
                raise VerificationError("Unexpected or duplicate Git tree path", path=path)
            if kind != "blob" or mode not in ("100644", "100755"):
                raise VerificationError("Evidence tree contains a non-regular file", path=path,
                                        mode=mode, object_type=kind)
            result[path] = blob
        return result

    def verify_blobs(self, unique):
        process = subprocess.Popen(self.command + ["cat-file", "--batch"], env=self.env,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        read_count = read_bytes = 0
        try:
            for blob, expected in sorted(unique.items()):
                process.stdin.write(blob.encode("ascii") + b"\n")
                process.stdin.flush()
                header = process.stdout.readline().decode("ascii", "replace").rstrip("\n")
                fields = header.split(" ")
                if len(fields) != 3 or fields[:2] != [blob, "blob"]:
                    raise VerificationError("Missing or unexpected Git blob response", blob=blob,
                                            response=header[:300])
                try:
                    size = int(fields[2])
                except ValueError as error:
                    raise VerificationError("Malformed Git blob length", blob=blob) from error
                if size != expected["bytes"]:
                    raise VerificationError("Git blob length differs from index", blob=blob,
                                            expected=expected["bytes"], actual=size)
                sha256 = hashlib.sha256()
                git_hash = hashlib.sha1(b"blob " + str(size).encode("ascii") + b"\0")
                remaining = size
                while remaining:
                    block = process.stdout.read(min(1024 * 1024, remaining))
                    if not block:
                        raise VerificationError("Truncated Git blob bytes", blob=blob, remaining=remaining)
                    sha256.update(block)
                    git_hash.update(block)
                    remaining -= len(block)
                if process.stdout.read(1) != b"\n":
                    raise VerificationError("Malformed Git batch blob terminator", blob=blob)
                actual_sha256, actual_git_hash = sha256.hexdigest(), git_hash.hexdigest()
                if actual_sha256 != expected["sha256"] or actual_git_hash != blob:
                    raise VerificationError("Git blob bytes fail checksum verification", blob=blob,
                                            expected_sha256=expected["sha256"], actual_sha256=actual_sha256,
                                            actual_git_blob_sha=actual_git_hash)
                read_count += 1
                read_bytes += size
            process.stdin.close()
            process.wait(timeout=30)
            errors = process.stderr.read().decode("utf-8", "replace").strip()
            if process.returncode:
                raise VerificationError("Git batch reader failed", detail=errors[:1200])
            if process.stdout.read(1):
                raise VerificationError("Unexpected trailing Git batch output")
            return read_count, read_bytes
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream and not stream.closed:
                    stream.close()


def verify(args):
    repo = args.repo.resolve()
    if not repo.is_dir():
        raise VerificationError("Repository directory is missing")
    if not SHA1.fullmatch(args.commit):
        raise VerificationError("--commit must be the full lowercase 40-character fetched commit SHA")
    prefix = relative_path(args.prefix[:-1] if args.prefix.endswith("/") else args.prefix) + "/"
    index_path = args.index.resolve()
    index_name = relative_path(index_path.name)
    index_raw, document = read_local_index(index_path)
    expected, unique = expected_files(document, index_name, index_raw, prefix)
    git = ReadOnlyGit(repo)
    if git.run("rev-parse", "--show-object-format").strip() != b"sha1":
        raise VerificationError("This archive index requires a SHA-1 Git object repository")
    if git.run("cat-file", "-t", args.commit).strip() != b"commit":
        raise VerificationError("--commit does not identify an available commit object")
    tree = git.tree(args.commit, prefix)
    missing, extra = sorted(set(expected) - set(tree)), sorted(set(tree) - set(expected))
    if missing or extra:
        raise VerificationError("Archive tree path set differs from index plus index file",
                                missing_count=len(missing), extra_count=len(extra),
                                missing_paths=missing[:20], extra_paths=extra[:20])
    wrong = [path for path in sorted(expected) if tree[path] != expected[path]["git_blob_sha"]]
    if wrong:
        raise VerificationError("Archive tree has incorrect blob IDs", count=len(wrong),
                                paths=[dict(path=p, expected=expected[p]["git_blob_sha"], actual=tree[p])
                                       for p in wrong[:20]])
    blob_count, blob_bytes = git.verify_blobs(unique)
    index_fingerprint = expected[prefix + index_name]
    return dict(schema=SCHEMA, status="passed", commit=args.commit, prefix=prefix,
                indexed_files=len(document["files"]), verified_tree_files=len(tree),
                unique_blobs_read=blob_count, duplicate_reads_avoided=len(tree) - blob_count,
                unique_blob_bytes_read=blob_bytes,
                total_tree_file_bytes=sum(item["bytes"] for item in expected.values()),
                index_file=prefix + index_name, index_sha256=index_fingerprint["sha256"],
                index_git_blob_sha=index_fingerprint["git_blob_sha"],
                scope="Exact tree and blob bytes of the already-fetched local Git commit; no network access",
                release_acceptance="not_asserted_by_this_verifier")


def main(argv=None):
    parser = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    try:
        result = verify(parser.parse_args(argv))
    except Exception as error:
        result = dict(schema=SCHEMA, status="failed", error=str(error))
        if isinstance(error, VerificationError):
            result.update(error.details)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 1
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
