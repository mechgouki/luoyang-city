#!/usr/bin/env python3
"""Index an assembled evidence payload before the external full-tree freeze."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat

INDEXES = ('archive-inventory.json', 'archive-scope.json', 'archive-sensitive-scan.json')
REQUIRED = ('README.md', 'acceptance.json', 'current-state-after-acceptance.json', 'assembly-scope.json')
RULES = {
    'github_token': rb'(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}',
    'github_fine_grained_token': rb'github_pat_[A-Za-z0-9_]{40,}',
    'private_key_header': rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
    'azure_signed_query': rb'(?i)[?&]sig=[A-Za-z0-9%+/=_-]{20,}',
    'aws_signed_query': rb'(?i)[?&]X-Amz-Signature=[0-9a-f]{40,}',
    'openai_key': rb'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}',
}


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'git_blob_sha1': hashlib.sha1(('blob %d\0' % len(raw)).encode() + raw).hexdigest()}


def stamp(path):
    value = path.lstat()
    if not stat.S_ISREG(value.st_mode):
        raise ValueError('Not a regular file: ' + str(path))
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        raise ValueError('Assembled payload is missing')
    for name in REQUIRED:
        if not (root / name).is_file():
            raise ValueError('Required final document is missing: ' + name)
    if any((root / name).exists() for name in INDEXES):
        raise ValueError('Generated indexes already exist; refusing to overwrite')
    for path in root.rglob('*'):
        if path.is_symlink():
            raise ValueError('Symlink is not allowed: ' + str(path))
    paths = sorted(path for path in root.rglob('*') if path.is_file())
    original_stamps = {path: stamp(path) for path in paths}
    rows, hits = [], []
    text_files = binary_files = text_bytes = 0
    for path in paths:
        raw = path.read_bytes()
        if stamp(path) != original_stamps[path]:
            raise ValueError('File changed while indexing: ' + str(path))
        relative = path.relative_to(root).as_posix()
        rows.append({'path': relative, 'mode': '100644', **identity(raw)})
        try:
            if b'\0' in raw:
                raise UnicodeDecodeError('utf-8', raw, 0, 1, 'NUL indicates binary input')
            raw.decode('utf-8')
        except UnicodeDecodeError:
            binary_files += 1
            continue
        text_files += 1
        text_bytes += len(raw)
        for name, pattern in RULES.items():
            for match in re.finditer(pattern, raw):
                hits.append({'path': relative, 'rule': name,
                             'line': raw.count(b'\n', 0, match.start()) + 1})
    if {path: stamp(path) for path in root.rglob('*') if path.is_file()} != original_stamps:
        raise ValueError('Payload changed during indexing')
    if hits:
        raise ValueError('Publication scan needs review; matched locations only: ' + json.dumps(hits))
    assembly_raw = (root / 'assembly-scope.json').read_bytes()
    assembly = json.loads(assembly_raw)
    if assembly['status'] != 'assembled_not_frozen_or_accepted':
        raise ValueError('Unexpected assembly state')
    unique = {row['git_blob_sha1']: row['bytes'] for row in rows}
    now = datetime.now(timezone.utc).isoformat()
    inventory = {'schema': 'luoyang-r12-archive-inventory-v1', 'generated_at_utc': now,
                 'scope': 'Every assembled file before these three generated indexes. The external freeze includes all three index files and is the complete upload inventory.',
                 'generated_indexes_excluded_to_avoid_self_reference': list(INDEXES),
                 'file_count_before_indexes': len(rows), 'logical_bytes_before_indexes': sum(row['bytes'] for row in rows),
                 'unique_blob_count_before_indexes': len(unique), 'unique_blob_bytes_before_indexes': sum(unique.values()),
                 'files': rows}
    scope = {'schema': 'luoyang-r12-archive-scope-v1', 'generated_at_utc': now,
             'assembly_scope': {'path': 'assembly-scope.json', **identity(assembly_raw)},
             'assembly_counts': assembly['actual_counts'],
             'file_count_before_indexes': len(rows),
             'generated_indexes_added_after_assembly': list(INDEXES),
             'rule': 'No additional exclusions. Original browser downloads, including ZIPs, remain in CAS. Only the exact assembly-scope transport-wrapper and fixed prior-terrain exceptions apply.',
             'pages_retention': 'Every Pages member has an identity ledger; only selected Pages bytes are retained. Unretained old members are not a claim of permanent byte preservation or cross-release equality.',
             'final_complete_counts': 'Read the external frozen-upload-manifest, which includes the three index files themselves.',
             'archive_verification': 'Independent remote commit/tree/blob verification is performed after freezing; this scope document does not certify an upload.'}
    scan = {'schema': 'luoyang-r12-archive-sensitive-scan-v1', 'generated_at_utc': now,
            'status': 'passed_for_listed_patterns', 'files_considered': len(rows),
            'utf8_text_files_scanned': text_files, 'utf8_text_bytes_scanned': text_bytes,
            'binary_files_not_text_scanned': binary_files, 'rules': {key: value.decode('ascii') for key, value in RULES.items()},
            'matches': [], 'generated_indexes_excluded': list(INDEXES),
            'scope': 'Limited scan of actual UTF-8 text payloads, including extensionless CAS text objects. Binary files and ZIP payloads are not unpacked by this scan. This is not an exhaustive security certification. Raw matched secret values are never emitted.'}
    for name, value in zip(INDEXES, (inventory, scope, scan)):
        with (root / name).open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'indexed_files_before_indexes': len(rows), 'generated_indexes': list(INDEXES),
                      'text_scan_status': scan['status'], 'text_files_scanned': text_files,
                      'binary_files_not_text_scanned': binary_files}, ensure_ascii=False))


if __name__ == '__main__':
    main()
