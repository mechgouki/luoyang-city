#!/usr/bin/env python3
"""Read an immutable R9 evidence commit back from Git; never publish or alter payload.

Example (run only after the archive commit has been authorized and supplied):
  python /tmp/r9_verify_archive_remote.py COMMIT \
    evidence/city-spatial-r9/2026-11-22/ \
    /tmp/luoyang-r9-archive-upload-list.json

The only Git write is fetching objects without a refspec destination, tags,
FETCH_HEAD, remote-tracking updates, or automatic maintenance. Every archive path
is verified, while each distinct remote blob is read only once via cat-file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


DEFAULT_REPO = Path('/workspace/scratch/b7f9dff5a3b9/luoyang-r9')
DEFAULT_REPORT = Path('/tmp/r9-archive-remote-readback.json')
DEFAULT_BRANCH = 'evidence/city-spatial-r9-20261122'
DEFAULT_PARENT = '1a988bc51adc74288ec8a8aa682499444007a33c'
GENERATED = {'archive-inventory.json', 'archive-scope.json', 'archive-sensitive-scan.json'}
OID = re.compile(r'[0-9a-f]{40}\Z')
SHA256 = re.compile(r'[0-9a-f]{64}\Z')
CHUNK = 1024 * 1024


class VerificationError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f'Duplicate JSON key: {key!r}')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def inside(path, parent):
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def safe_relative(value):
    require(isinstance(value, str) and value, 'Archive path must be nonempty text')
    require(not any(c in value for c in ('\x00', '\n', '\r', '\\')), f'Unsafe archive path: {value!r}')
    path = PurePosixPath(value)
    require(not path.is_absolute() and str(path) == value, f'Noncanonical archive path: {value!r}')
    require(all(part not in ('', '.', '..') for part in value.split('/')), f'Unsafe archive path: {value!r}')
    return value


def hash_file(path):
    require(path.is_file() and not path.is_symlink(), f'Expected regular payload file: {path}')
    before = path.stat()
    h256 = hashlib.sha256()
    hblob = hashlib.sha1(f'blob {before.st_size}\0'.encode())
    size = 0
    with path.open('rb') as stream:
        while chunk := stream.read(CHUNK):
            h256.update(chunk)
            hblob.update(chunk)
            size += len(chunk)
    after = path.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), f'Payload changed during read: {path}')
    require(size == before.st_size, f'Payload size changed during read: {path}')
    return {'bytes': size, 'sha256': h256.hexdigest(), 'gitblob': hblob.hexdigest()}


def git(repo, *args, timeout=60):
    env = os.environ.copy()
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0', GIT_NO_REPLACE_OBJECTS='1')
    result = subprocess.run(['git', '-C', str(repo), *args], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=env, timeout=timeout)
    if result.returncode:
        detail = result.stderr.decode('utf-8', errors='replace')[-3000:]
        raise VerificationError(f'git {args[0]} failed ({result.returncode}): {detail}')
    return result.stdout


def refs_snapshot(repo):
    return git(repo, 'for-each-ref', '--format=%(refname)%00%(objectname)').decode().splitlines()


def fetch_head_snapshot(repo):
    raw = git(repo, 'rev-parse', '--git-path', 'FETCH_HEAD').decode().strip()
    path = Path(raw)
    if not path.is_absolute():
        path = repo / path
    if not path.exists():
        return {'exists': False}
    data = path.read_bytes()
    return {'exists': True, 'bytes': len(data), 'sha256': digest(data)}


def branch_tip(repo, remote, branch):
    ref = 'refs/heads/' + branch
    raw = git(repo, 'ls-remote', '--exit-code', remote, ref, timeout=180)
    rows = [line.split(b'\t', 1) for line in raw.splitlines()]
    rows = [row for row in rows if len(row) == 2 and row[1].decode() == ref]
    require(len(rows) == 1, f'Expected exactly one remote branch: {ref}')
    return rows[0][0].decode()


def read_tree(repo, commit, prefix):
    data = git(repo, 'ls-tree', '-r', '-z', '--full-tree', commit, '--', prefix)
    entries = {}
    for record in data.split(b'\0'):
        if not record:
            continue
        header, path_raw = record.split(b'\t', 1)
        mode, kind, oid = header.decode('ascii').split()
        path = path_raw.decode('utf-8')
        require(path.startswith(prefix), f'Unexpected path outside requested prefix: {path!r}')
        relative = safe_relative(path[len(prefix):])
        require(relative not in entries, f'Duplicate tree path: {relative}')
        require(kind == 'blob' and mode in ('100644', '100755'), f'Non-regular tree entry: {path} ({mode} {kind})')
        require(OID.fullmatch(oid) is not None, f'Unexpected object id: {oid}')
        entries[relative] = {'mode': mode, 'gitblob': oid}
    return entries


def read_remote_blobs(repo, object_ids, keep_bytes):
    """Read each unique object once, retaining raw bytes only for three controls."""
    results = {}
    retained = {}
    env = os.environ.copy()
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1')
    with tempfile.TemporaryFile() as errors:
        proc = subprocess.Popen(['git', '-C', str(repo), 'cat-file', '--batch'],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=errors, env=env)
        try:
            for oid in sorted(set(object_ids)):
                proc.stdin.write(oid.encode('ascii') + b'\n')
                proc.stdin.flush()
                header = proc.stdout.readline(160).rstrip(b'\n').split()
                require(len(header) == 3, f'Invalid or missing cat-file object header for {oid}: {header!r}')
                actual_oid, kind, size_raw = header
                require(actual_oid.decode() == oid and kind == b'blob', f'Unexpected cat-file object type/id: {oid}')
                size = int(size_raw)
                require(size >= 0, f'Invalid blob size: {oid}')
                h256 = hashlib.sha256()
                hblob = hashlib.sha1(f'blob {size}\0'.encode())
                content = bytearray() if oid in keep_bytes else None
                remaining = size
                while remaining:
                    chunk = proc.stdout.read(min(CHUNK, remaining))
                    require(bool(chunk), f'Truncated cat-file object: {oid}')
                    h256.update(chunk)
                    hblob.update(chunk)
                    if content is not None:
                        content.extend(chunk)
                    remaining -= len(chunk)
                require(proc.stdout.read(1) == b'\n', f'Invalid cat-file object terminator: {oid}')
                calculated_oid = hblob.hexdigest()
                require(calculated_oid == oid, f'Blob contents fail their Git object identity: {oid}')
                results[oid] = {'bytes': size, 'sha256': h256.hexdigest(), 'gitblob': calculated_oid}
                if content is not None:
                    retained[oid] = bytes(content)
            proc.stdin.close()
            require(proc.wait(timeout=30) == 0, 'cat-file exited with a failure')
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
    return results, retained


def atomic_report(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix=path.name + '.', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    os.replace(temporary, path)


def verify(args, report):
    repo = args.repo.resolve()
    require(not inside(args.report, repo), 'Report must stay outside the repository source tree')
    require(args.report.resolve() != args.upload_list.resolve(), 'Report cannot overwrite its final upload list')
    require(OID.fullmatch(args.commit) is not None, 'Supply a full lowercase 40-character archive commit')
    prefix = safe_relative(args.prefix.rstrip('/')) + '/'
    require(args.prefix in (prefix, prefix[:-1]), 'Noncanonical archive prefix')
    require(not args.remote.startswith('-') and bool(args.remote), 'Unsafe Git remote argument')
    require(not args.branch.startswith('-') and bool(args.branch), 'Unsafe branch name')
    require(OID.fullmatch(args.expected_parent) is not None, 'Supply a full expected main parent commit')
    require(git(repo, 'rev-parse', '--show-object-format').strip() == b'sha1', 'Upload-list Git blob identities require a SHA-1 Git repository')

    report['stage'] = 'validate_final_upload_list_and_payload'
    raw_list = args.upload_list.read_bytes()
    manifest = strict_json(raw_list)
    require(manifest.get('schema') == 'luoyang-r9-archive-upload-list-v1', 'Unexpected final upload-list schema')
    payload = Path(manifest['payload_root']).resolve()
    source_root = Path(manifest['source_root']).resolve() if manifest.get('source_root') else None
    require(not inside(args.report, payload), 'Report must stay outside archive payload')
    require(source_root is None or not inside(args.report, source_root), 'Report must stay outside evidence inputs as well')
    require(not inside(args.upload_list, payload), 'Final upload list must be external to payload')
    expected = {}
    for row in manifest['files']:
        path = safe_relative(row['path'])
        require(path not in expected, f'Duplicate upload-list path: {path}')
        require(isinstance(row['bytes'], int) and not isinstance(row['bytes'], bool) and row['bytes'] >= 0, f'Invalid byte count: {path}')
        require(SHA256.fullmatch(row['sha256']) is not None, f'Invalid SHA-256: {path}')
        require(OID.fullmatch(row['gitblob']) is not None, f'Invalid Git blob: {path}')
        expected[path] = row
    require(bool(expected), 'Empty archive upload list')
    require(manifest['file_count'] == len(expected), 'Upload-list file count mismatch')
    require(manifest['total_bytes'] == sum(row['bytes'] for row in expected.values()), 'Upload-list byte count mismatch')
    controls = {path for path, row in expected.items() if row.get('origin') == 'generated_archive_record'}
    require(controls == GENERATED, f'Expected exactly the three generated indexes, got {sorted(controls)}')
    require(not manifest.get('unexpected_payload_files'), 'Preparation reports unexpected payload files')

    actual_local = set()
    for path in payload.rglob('*'):
        require(not path.is_symlink(), f'Symlink not permitted in frozen payload: {path}')
        if path.is_file():
            actual_local.add(path.relative_to(payload).as_posix())
    require(actual_local == set(expected), 'Frozen payload path set differs from final upload list')
    local_controls = {}
    for relative, row in sorted(expected.items()):
        path = payload / relative
        require(inside(path, payload), f'Payload path escapes root: {relative}')
        hashes = hash_file(path)
        require(all(hashes[key] == row[key] for key in ('bytes', 'sha256', 'gitblob')), f'Frozen payload bytes differ from final list: {relative}')
        if relative in GENERATED:
            content = path.read_bytes()
            require(len(content) == row['bytes'] and digest(content) == row['sha256'], f'Generated index changed while read: {relative}')
            local_controls[relative] = content
    report.update(archive_commit=args.commit, prefix=prefix, remote=args.remote,
                  remote_branch=args.branch, expected_main_parent=args.expected_parent,
                  upload_list=str(args.upload_list.resolve()), upload_list_sha256=digest(raw_list),
                  payload_root=str(payload), expected_file_count=len(expected),
                  expected_total_bytes=manifest['total_bytes'], local_payload_matches_final_list=True)

    report['stage'] = 'fetch_remote_commit_without_refs'
    before_refs = refs_snapshot(repo)
    before_fetch_head = fetch_head_snapshot(repo)
    report['remote_branch_tip_before_fetch'] = branch_tip(repo, args.remote, args.branch)
    require(report['remote_branch_tip_before_fetch'] == args.commit, 'Remote archive branch does not name the supplied commit')
    git(repo, 'fetch', '--no-tags', '--no-prune', '--no-prune-tags', '--no-write-fetch-head',
        '--no-write-commit-graph', '--no-recurse-submodules', '--no-auto-maintenance', '--refmap=', args.remote,
        args.commit, timeout=args.fetch_timeout)
    after_refs = refs_snapshot(repo)
    after_fetch_head = fetch_head_snapshot(repo)
    report['refs_unchanged'] = before_refs == after_refs
    report['fetch_head_unchanged'] = before_fetch_head == after_fetch_head
    report['refs_snapshot_sha256'] = digest('\n'.join(before_refs).encode())
    require(report['refs_unchanged'], 'Refs changed across fetch; cannot assert a ref-free readback')
    require(report['fetch_head_unchanged'], 'FETCH_HEAD changed across fetch')
    require(git(repo, 'cat-file', '-t', args.commit).strip() == b'commit', 'Fetched archive object is not a commit')
    require(git(repo, 'rev-parse', args.commit + '^{commit}').decode().strip() == args.commit, 'Fetched commit identity mismatch')

    report['stage'] = 'verify_main_parent_and_exact_archive_paths'
    parents = git(repo, 'rev-list', '--parents', '-n', '1', args.commit).decode().split()[1:]
    require(parents == [args.expected_parent], f'Archive is not a single child of the expected main commit: {parents}')
    changes = git(repo, 'diff-tree', '--no-commit-id', '--name-only', '--no-renames',
                  '-r', '-z', args.expected_parent, args.commit).split(b'\0')
    changed_paths = [path.decode('utf-8') for path in changes if path]
    outside = [path for path in changed_paths if not path.startswith(prefix)]
    report['archive_parent'] = parents[0]
    report['changed_paths_outside_archive_prefix'] = outside
    require(not outside, f'Archive commit changes paths outside prefix: {outside[:10]}')
    tree = read_tree(repo, args.commit, prefix)
    missing = sorted(set(expected) - set(tree))
    unexpected = sorted(set(tree) - set(expected))
    report['path_set'] = {'expected': len(expected), 'actual': len(tree), 'missing': missing, 'unexpected': unexpected}
    require(not missing and not unexpected, 'Remote archive prefix does not contain the exact final path set')

    report['stage'] = 'read_remote_blob_bytes_and_verify_every_path'
    keep = {tree[path]['gitblob'] for path in GENERATED}
    objects, kept = read_remote_blobs(repo, (entry['gitblob'] for entry in tree.values()), keep)
    files = []
    mismatches = []
    for relative, row in sorted(expected.items()):
        entry = tree[relative]
        actual = objects[entry['gitblob']]
        differences = [key for key in ('bytes', 'sha256', 'gitblob') if actual[key] != row[key]]
        record = {'path': relative, 'remote_path': prefix + relative, 'mode': entry['mode'], **actual,
                  'matches_final_upload_list': not differences}
        if differences:
            record['mismatched_fields'] = differences
            record['expected'] = {key: row[key] for key in ('bytes', 'sha256', 'gitblob')}
            mismatches.append(relative)
        files.append(record)
    report['files'] = files
    report['files_verified'] = len(files)
    report['remote_unique_blobs_read'] = len(objects)
    report['remote_unique_blob_bytes_read'] = sum(row['bytes'] for row in objects.values())
    report['remote_total_bytes_by_path'] = sum(row['bytes'] for row in files)
    report['mismatched_paths'] = mismatches
    require(not mismatches, f'Remote archive content differs at {len(mismatches)} path(s)')

    report['stage'] = 'verify_generated_index_bytes_and_input_stability'
    index_results = []
    for relative in sorted(GENERATED):
        remote_bytes = kept[tree[relative]['gitblob']]
        current_local_bytes = (payload / relative).read_bytes()
        equal = remote_bytes == local_controls[relative] == current_local_bytes
        index_results.append({'path': relative, 'bytes_equal_to_frozen_local_index': equal,
                              'bytes': len(remote_bytes), 'sha256': digest(remote_bytes),
                              'gitblob': tree[relative]['gitblob']})
        require(equal, f'Generated index raw bytes differ: {relative}')
    report['generated_indexes'] = index_results
    report['upload_list_unchanged_during_readback'] = args.upload_list.read_bytes() == raw_list
    require(report['upload_list_unchanged_during_readback'], 'Final upload list changed during remote readback')
    require(refs_snapshot(repo) == before_refs, 'Refs changed during readback')
    require(fetch_head_snapshot(repo) == before_fetch_head, 'FETCH_HEAD changed during readback')
    report['stage'] = 'complete'
    report['status'] = 'passed'
    report['completed_at_utc'] = datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('commit', help='Full immutable archive commit id, supplied by root')
    parser.add_argument('prefix', help='Repository archive directory, including or excluding final slash')
    parser.add_argument('upload_list', type=Path, help='Final external upload-list JSON')
    parser.add_argument('--repo', type=Path, default=DEFAULT_REPO)
    parser.add_argument('--remote', default='origin')
    parser.add_argument('--branch', default=DEFAULT_BRANCH)
    parser.add_argument('--expected-parent', default=DEFAULT_PARENT)
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT)
    parser.add_argument('--fetch-timeout', type=int, default=300)
    args = parser.parse_args()
    report = {'schema': 'luoyang-r9-archive-remote-readback-v1', 'reviewer': 'r9_validation',
              'started_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'running',
              'source_or_payload_mutations': [], 'ref_creation_requested': False,
              'method': 'Fetch the exact remote branch commit without refs; inspect the immutable tree and read each unique actual blob once through git cat-file --batch; verify every path against the final external upload list.'}
    try:
        verify(args, report)
    except Exception as error:
        report.update(status='failed', error_type=type(error).__name__, error=str(error),
                      completed_at_utc=datetime.now(timezone.utc).isoformat())
    # Guard the destination again even when validation failed early.
    try:
        require(not inside(args.report, args.repo), 'Refusing to write report inside the repository source tree')
        require(args.report.resolve() != args.upload_list.resolve(), 'Refusing to overwrite the final upload list')
        if args.upload_list.exists():
            raw = strict_json(args.upload_list.read_bytes())
            for key in ('payload_root', 'source_root'):
                if raw.get(key):
                    require(not inside(args.report, Path(raw[key])), f'Refusing to write report inside {key}')
        atomic_report(args.report.resolve(), report)
    except Exception as error:
        print(json.dumps({'status': 'failed', 'report_written': False, 'error': str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({'status': report['status'], 'stage': report.get('stage'),
                      'report': str(args.report.resolve()), 'report_sha256': digest(args.report.read_bytes()),
                      'archive_commit': report.get('archive_commit'), 'files_verified': report.get('files_verified', 0),
                      'remote_unique_blobs_read': report.get('remote_unique_blobs_read', 0),
                      **({'error': report['error']} if 'error' in report else {})}, ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
