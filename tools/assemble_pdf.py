#!/usr/bin/env python3
"""Reconstruct the unchanged v2.4 atlas PDF from six GitHub-friendly binary fragments."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "downloads" / "parts"
OUTPUT = ROOT / "downloads" / "luoyang-v24-regional-atlas.pdf"
EXPECTED_SHA256 = "14f30eeb1e525d090e8d75acfd896049e57b57d0d6b3381c16d1c4f289b72823"
EXPECTED_SIZE = 8612460
pieces = [PARTS / f"part{i:02d}.bin" for i in range(1, 7)]
if not all(p.is_file() for p in pieces):
    raise SystemExit("Missing one or more atlas PDF fragments")
combined = b"".join(p.read_bytes() for p in pieces)
if len(combined) != EXPECTED_SIZE or hashlib.sha256(combined).hexdigest() != EXPECTED_SHA256:
    raise SystemExit("PDF integrity check failed")
OUTPUT.write_bytes(combined)
print(f"OK: restored {OUTPUT.name} ({len(combined)} bytes), SHA-256 verified")
