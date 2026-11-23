#!/usr/bin/env python3
"""Select exact new blobs; preserve every path and never perform remote writes."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--known-remote-blobs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw_manifest = args.manifest.read_bytes()
    manifest = json.loads(raw_manifest)
    root = Path(manifest['payload_root']).resolve()
    known_doc = json.loads(args.known_remote_blobs.read_text())
    known = {row['gitblob']: row for row in known_doc['blobs']}
    unique = {}
    paths = set()
    for row in manifest['files']:
        relative = PurePosixPath(row['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        assert row['path'] == str(relative) and row['path'] not in paths
        paths.add(row['path'])
        path = root / relative
        assert path.is_file() and not path.is_symlink()
        raw = path.read_bytes()
        identity = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                    'gitblob': hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()}
        assert all(identity[key] == row[key] for key in identity), row['path']
        item = unique.setdefault(identity['gitblob'], {**identity, 'source_path': row['path'], 'paths': []})
        item['paths'].append(row['path'])
    reused, new = [], []
    for sha, item in sorted(unique.items()):
        if sha in known:
            old = known[sha]
            assert item['bytes'] == old['bytes'], sha
            if old.get('sha256'):
                assert item['sha256'] == old['sha256'], sha
            reused.append({**item, 'known_remote_commit': old['known_remote_commit'],
                           'known_remote_path': old['example_path']})
        else:
            new.append(item)
    out = {'schema': 'luoyang-r11-blob-upload-plan-v1', 'remote_writes_performed': False,
           'payload_root': str(root), 'manifest_sha256': hashlib.sha256(raw_manifest).hexdigest(),
           'file_count': len(paths), 'unique_blob_count': len(unique),
           'reused_blob_count': len(reused), 'new_blob_count': len(new),
           'new_blob_bytes': sum(row['bytes'] for row in new),
           'reused_unique_bytes': sum(row['bytes'] for row in reused),
           'reused': reused, 'new': new,
           'upload_rule': 'Upload each new content blob once and verify the returned SHA. Reference all paths by their exact blob SHA. Create tree/commit/ref only after parent confirms the accepted release and the final tree equals the locally computed identity.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: out[key] for key in ['file_count', 'unique_blob_count', 'reused_blob_count', 'new_blob_count', 'new_blob_bytes']}))


if __name__ == '__main__':
    main()
