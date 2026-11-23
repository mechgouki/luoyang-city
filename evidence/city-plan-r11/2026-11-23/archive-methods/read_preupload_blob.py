#!/usr/bin/env python3
"""Read only an authorized immutable payload blob as bounded base64 chunks."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--plan', type=Path, required=True)
parser.add_argument('--gitblob', required=True)
parser.add_argument('--offset', type=int, default=0)
parser.add_argument('--length', type=int, default=450000)
args = parser.parse_args()
assert len(args.gitblob) == 40 and set(args.gitblob) <= set('0123456789abcdef')
assert args.offset >= 0 and args.offset % 3 == 0
assert 0 < args.length <= 450000 and args.length % 3 == 0
plan = json.loads(args.plan.read_text())
rows = [row for row in plan['new'] if row['gitblob'] == args.gitblob]
assert len(rows) == 1
row = rows[0]
root = Path(plan['payload_root']).resolve()
path = root / row['source_path']
assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root)
raw = path.read_bytes()
assert len(raw) == row['bytes']
assert hashlib.sha256(raw).hexdigest() == row['sha256']
assert hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest() == row['gitblob']
assert args.offset < len(raw) or len(raw) == 0
block = raw[args.offset:args.offset + args.length]
print(json.dumps({'gitblob': row['gitblob'], 'sha256': row['sha256'],
                  'bytes': len(raw), 'offset': args.offset, 'chunk_bytes': len(block),
                  'base64': base64.b64encode(block).decode('ascii')}, separators=(',', ':')))
