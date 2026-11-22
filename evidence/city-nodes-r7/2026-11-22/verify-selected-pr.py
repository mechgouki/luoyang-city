"""Verify the preserved, selected original PR75 evidence without network access."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent / "original-pr"
manifest = json.loads((root / "selection-manifest.json").read_bytes())
entries = manifest["files"] + manifest["derived_files"]
paths = [row["path"] for row in entries]
assert len(paths) == len(set(paths))
assert {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} == set(paths) | {"selection-manifest.json"}
for row in entries:
    target = (root / row["path"]).resolve()
    assert target.is_relative_to(root.resolve())
    raw = target.read_bytes()
    assert len(raw) == row["bytes"], row["path"]
    assert hashlib.sha256(raw).hexdigest() == row["sha256"], row["path"]
print(json.dumps(dict(status="passed", files_verified=len(entries),
                      original_files=len(manifest["files"]), screenshots=manifest["totals"]["screenshots"],
                      original_artifact_verified_files=manifest["totals"]["artifact_verified_files"],
                      tested_source_commit=manifest["tested_source_commit"])))
