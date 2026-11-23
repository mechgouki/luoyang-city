#!/usr/bin/env python3
"""Check an assembled/indexed payload against its external frozen manifest.

Reads payload bytes only; writes one external proof. Planned Git mode is 100644;
local executable permission bits are not interpreted as an upload mode.
This does not upload, verify remote objects, or rerun the sensitive-pattern scan.
"""
import argparse
import codecs
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile

INDEXES = ('archive-inventory.json', 'archive-scope.json', 'archive-sensitive-scan.json')
REQUIRED = ('README.md', 'acceptance.json', 'current-state-after-acceptance.json',
            'assembly-scope.json', *INDEXES)
IDENTITY = ('bytes', 'sha256', 'git_blob_sha1')
SCHEMAS = {'archive-inventory.json': 'luoyang-r12-archive-inventory-v1',
           'archive-scope.json': 'luoyang-r12-archive-scope-v1',
           'archive-sensitive-scan.json': 'luoyang-r12-archive-sensitive-scan-v1',
           'assembly-scope.json': 'luoyang-r12-evidence-assembly-scope-v1'}


def need(condition, location):
    if not condition:
        raise ValueError(location)


def relative(value, location):
    need(isinstance(value, str) and value and '\\' not in value
         and not any(ord(c) < 32 or ord(c) == 127 for c in value), location)
    p = PurePosixPath(value)
    need(not p.is_absolute() and str(p) == value and value != '.'
         and '..' not in p.parts and not re.match(r'^[A-Za-z]:', value)
         and all(part.casefold() != '.git' for part in p.parts), location)
    return value


def regular_stamp(path):
    s = path.lstat()
    need(stat.S_ISREG(s.st_mode), 'non-regular file: ' + str(path))
    return s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns


def snapshot(root):
    result = {}
    def walk_error(error):
        raise error
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        for name in dirs:
            need(not (Path(directory) / name).is_symlink(), 'directory symlink: ' + str(Path(directory) / name))
        for name in files:
            path = Path(directory) / name
            key = relative(path.relative_to(root).as_posix(), 'invalid payload path')
            result[key] = regular_stamp(path)
    return result


def read_file(path, before, capture=False, probe_text=False):
    need(regular_stamp(path) == before, 'changed before read: ' + str(path))
    sha, blob = hashlib.sha256(), hashlib.sha1(('blob %d\0' % before[3]).encode())
    parts, size, text = [], 0, True
    decoder = codecs.getincrementaldecoder('utf-8')('strict') if probe_text else None
    with path.open('rb') as stream:
        need(os.fstat(stream.fileno()).st_ino == before[1], 'changed open file: ' + str(path))
        while block := stream.read(1024 * 1024):
            size += len(block)
            sha.update(block)
            blob.update(block)
            if capture:
                parts.append(block)
            if probe_text and text:
                try:
                    if b'\0' in block:
                        text = False
                    else:
                        decoder.decode(block, final=False)
                except UnicodeDecodeError:
                    text = False
        if probe_text and text:
            try:
                decoder.decode(b'', final=True)
            except UnicodeDecodeError:
                text = False
    need(regular_stamp(path) == before and size == before[3], 'changed while reading: ' + str(path))
    return {'bytes': size, 'sha256': sha.hexdigest(), 'git_blob_sha1': blob.hexdigest(),
            'mode': '100644'}, b''.join(parts), text


def document(raw, location):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, 'duplicate JSON key: ' + location)
            result[key] = value
        return result
    try:
        result = json.loads(raw, object_pairs_hook=unique)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError('invalid JSON: ' + location) from None
    need(isinstance(result, dict), 'JSON object required: ' + location)
    return result


def entries(rows, location, mode_required=False, prefix=''):
    need(isinstance(rows, list), location)
    result = {}
    for i, row in enumerate(rows):
        at = location + '/' + str(i)
        need(isinstance(row, dict), at)
        name = relative(row.get('path'), at + '/path')
        if prefix:
            need(name.startswith(prefix + '/'), at + '/path outside prefix')
            name = relative(name[len(prefix) + 1:], at + '/relative path')
        need(name not in result, 'duplicate path: ' + location + '/' + name)
        need(type(row.get('bytes')) is int and row['bytes'] >= 0, at + '/bytes')
        for field, length in (('sha256', 64), ('git_blob_sha1', 40)):
            need(isinstance(row.get(field), str) and re.fullmatch('[0-9a-f]{%d}' % length, row[field]), at + '/' + field)
        need((not mode_required and 'mode' not in row) or row.get('mode') == '100644', at + '/mode')
        result[name] = row
    return result


def same_paths(actual, expected, location):
    missing, extra = set(expected) - set(actual), set(actual) - set(expected)
    need(not missing, location + '/missing/' + (min(missing) if missing else ''))
    need(not extra, location + '/extra/' + (min(extra) if extra else ''))


def same_identity(a, b, location, mode=False):
    for field in IDENTITY + (('mode',) if mode else ()):
        need(a.get(field) == b.get(field), location + '/' + field)


def totals(rows):
    unique = {}
    for name, row in rows.items():
        key, value = row['git_blob_sha1'], (row['bytes'], row['sha256'])
        need(key not in unique or unique[key] == value, 'conflicting blob identity: ' + name)
        unique[key] = value
    return {'file_count': len(rows), 'logical_bytes': sum(r['bytes'] for r in rows.values()),
            'unique_blob_count': len(unique), 'unique_blob_bytes': sum(v[0] for v in unique.values())}


def counts(found, wanted, location):
    need(isinstance(found, dict), location)
    for key, value in wanted.items():
        need(type(found.get(key)) is int and found[key] == value, location + '/' + key)


def index_names(value, location):
    need(isinstance(value, list) and all(isinstance(x, str) for x in value)
         and len(value) == 3 and set(value) == set(INDEXES), location)


def write_proof(path, report):
    fd, temp = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = {'schema': 'luoyang-r12-index-freeze-consistency-v1', 'status': 'failed',
              'started_at_utc': datetime.now(timezone.utc).isoformat()}
    output = None
    try:
        for raw in (args.root, args.manifest, args.output):
            for path in (raw.absolute(), *raw.absolute().parents):
                need(not path.is_symlink(), 'symlink in argument path: ' + str(path))
        root, manifest_path, candidate = (p.resolve() for p in (args.root, args.manifest, args.output))
        need(root != candidate and root not in candidate.parents, 'output must be external')
        need(root != manifest_path and root not in manifest_path.parents, 'manifest must be external')
        need(candidate != manifest_path, 'output would overwrite manifest')
        need(candidate.parent.is_dir(), 'output parent directory is missing')
        if candidate.exists():
            regular_stamp(candidate)
        output = candidate
        need(root.is_dir(), 'payload root is missing')
        first = snapshot(root)
        manifest_stamp = regular_stamp(manifest_path)
        manifest_id, raw, _ = read_file(manifest_path, manifest_stamp, capture=True)
        manifest = document(raw, 'manifest')
        need(manifest.get('schema') == 'luoyang-frozen-upload-manifest-v1', 'manifest/schema')
        need(isinstance(manifest.get('expected_single_parent'), str)
             and re.fullmatch('[0-9a-f]{40}', manifest['expected_single_parent']), 'manifest/expected_single_parent')
        prefix = manifest.get('repository_prefix')
        need(isinstance(prefix, str), 'manifest/repository_prefix')
        prefix = relative(prefix[:-1] if prefix.endswith('/') else prefix, 'manifest/repository_prefix')
        need(prefix.startswith('evidence/'), 'manifest/repository_prefix')
        frozen = entries(manifest.get('files'), 'manifest/files', True, prefix)
        same_paths(first, frozen, 'payload versus manifest')
        for name in REQUIRED:
            need(name in frozen, 'required/' + name)
        actual, docs, text_flags = {}, {}, {}
        for name in sorted(first):
            found, content, is_text = read_file(root / name, first[name], name in SCHEMAS, name not in INDEXES)
            same_identity(found, frozen[name], 'actual/' + name, True)
            actual[name], text_flags[name] = found, is_text
            if name in SCHEMAS:
                docs[name] = document(content, name)
                need(docs[name].get('schema') == SCHEMAS[name], name + '/schema')
        final_totals = totals(actual)
        counts(manifest, final_totals, 'manifest/counts')
        inventory, scope, scan, assembly = (docs[n] for n in (*INDEXES, 'assembly-scope.json'))
        inv = entries(inventory.get('files'), 'inventory/files', True)
        need(not set(inv) & set(INDEXES), 'inventory contains generated index')
        same_paths(actual, set(inv) | set(INDEXES), 'inventory plus three indexes')
        for name, row in inv.items():
            same_identity(row, frozen[name], 'inventory/' + name, True)
        index_names(inventory.get('generated_indexes_excluded_to_avoid_self_reference'), 'inventory/exclusions')
        before_totals = totals(inv)
        counts(inventory, {k + '_before_indexes': v for k, v in before_totals.items()}, 'inventory/counts')
        need(assembly.get('status') == 'assembled_not_frozen_or_accepted', 'assembly/status')
        copied = entries(assembly.get('copied_files'), 'assembly/copied_files')
        excluded = entries(assembly.get('excluded_files'), 'assembly/excluded_files')
        generated = {'assembly-scope.json', *INDEXES}
        need(not set(copied) & generated and not set(excluded) & generated, 'assembly contains generated file')
        need(not set(copied) & set(excluded), 'assembly copied/excluded overlap')
        same_paths(actual, set(copied) | generated, 'assembly plus scope and indexes')
        for name, row in copied.items():
            same_identity(row, frozen[name], 'assembly/copied/' + name)
        for name, row in excluded.items():
            need(row.get('reason_code') in ('unchanged_terrain_intermediate', 'actions_zip_transport_wrapper'),
                 'assembly/excluded/' + name + '/reason_code')
        exceptions = assembly.get('terrain_exceptions')
        need(isinstance(exceptions, list), 'assembly/terrain_exceptions')
        assembly_counts = {'source_files': len(copied) + len(excluded),
            'source_bytes': sum(r['bytes'] for r in (*copied.values(), *excluded.values())),
            'copied_files': len(copied), 'copied_bytes': sum(r['bytes'] for r in copied.values()),
            'excluded_files': len(excluded), 'excluded_bytes': sum(r['bytes'] for r in excluded.values()),
            'copied_cas_objects': sum(n.startswith('cas/objects/') for n in copied),
            'unchanged_terrain_objects': sum(r['reason_code'] == 'unchanged_terrain_intermediate' for r in excluded.values()),
            'terrain_logical_exceptions': len(exceptions),
            'actions_wrappers': sum(r['reason_code'] == 'actions_zip_transport_wrapper' for r in excluded.values()),
            'unchanged_ingest_files': sum(n.startswith('cas/ingests/') for n in copied)}
        for key in ('actual_counts', 'planned_counts'):
            counts(assembly.get(key), assembly_counts, 'assembly/' + key)
        counts(scope.get('assembly_counts'), assembly_counts, 'archive-scope/assembly_counts')
        counts(scope, {'file_count_before_indexes': len(inv)}, 'archive-scope/counts')
        scope_identity = scope.get('assembly_scope')
        need(isinstance(scope_identity, dict) and scope_identity.get('path') == 'assembly-scope.json', 'archive-scope/assembly_scope/path')
        same_identity(scope_identity, frozen['assembly-scope.json'], 'archive-scope/assembly_scope')
        index_names(scope.get('generated_indexes_added_after_assembly'), 'archive-scope/indexes')
        index_names(scan.get('generated_indexes_excluded'), 'archive-sensitive-scan/exclusions')
        scan_counts = {'files_considered': len(inv), 'utf8_text_files_scanned': sum(text_flags[n] for n in inv),
            'utf8_text_bytes_scanned': sum(actual[n]['bytes'] for n in inv if text_flags[n]),
            'binary_files_not_text_scanned': sum(not text_flags[n] for n in inv)}
        counts(scan, scan_counts, 'archive-sensitive-scan/counts')
        need(scan.get('status') == 'passed_for_listed_patterns' and scan.get('matches') == [], 'archive-sensitive-scan/status-or-matches')
        need(snapshot(root) == first, 'payload changed during consistency check')
        need(regular_stamp(manifest_path) == manifest_stamp, 'manifest changed during consistency check')
        report.update(status='passed', root=str(root), repository_prefix=prefix,
            expected_single_parent=manifest['expected_single_parent'],
            manifest={'path': str(manifest_path), **{k: manifest_id[k] for k in IDENTITY}},
            planned_git_mode='100644', final_statistics=final_totals,
            inventory_statistics=before_totals, assembly_statistics=assembly_counts,
            sensitive_scan_accounting=scan_counts,
            required_files=[{'path': n, **actual[n]} for n in REQUIRED],
            checks={'actual_files_match_frozen_identities_and_planned_modes': True,
                    'final_paths_equal_inventory_plus_exactly_three_indexes': True,
                    'inventory_identities_and_modes_match_frozen_manifest': True,
                    'final_paths_equal_assembly_copied_plus_scope_plus_indexes': True,
                    'assembly_copied_identities_match_frozen_manifest': True,
                    'archive_scope_assembly_identity_matches_frozen_manifest': True,
                    'recorded_statistics_recomputed': True, 'inputs_unchanged_during_check': True},
            limits='Local frozen-package consistency only; no remote verification, historical acceptance, completeness beyond assembly, or new sensitive-pattern certification.')
    except (OSError, ValueError, KeyError, TypeError) as error:
        report['error_location'] = (str(error) if isinstance(error, ValueError)
                                    else str(getattr(error, 'filename', None) or type(error).__name__))
    report['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
    try:
        if output is not None:
            write_proof(output, report)
    except OSError as error:
        print(json.dumps({'status': 'failed', 'error_location': str(error.filename or 'external proof write')}), file=sys.stderr)
        return 2
    if report['status'] != 'passed':
        print(json.dumps({'status': 'failed', 'error_location': report.get('error_location', 'verification')}), file=sys.stderr)
        return 2
    print(json.dumps({'status': 'passed', 'files_verified': report['final_statistics']['file_count'], 'output': str(output)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
