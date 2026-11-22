#!/usr/bin/env python3
"""Verify one authorized GitHub artifact ZIP and safely extract exact bytes."""
import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath


def main():
    p = argparse.ArgumentParser()
    p.add_argument("zip", type=Path)
    p.add_argument("destination", type=Path)
    p.add_argument("--sha256", required=True)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    raw = a.zip.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == a.sha256, "Artifact SHA256 differs from GitHub metadata"
    assert not a.destination.exists() or not any(a.destination.iterdir())
    a.destination.mkdir(parents=True, exist_ok=True)
    rows, seen = [], set()
    with zipfile.ZipFile(a.zip) as archive:
        for member in archive.infolist():
            name = member.filename.rstrip("/")
            rel = PurePosixPath(name)
            assert name and str(rel) == name and not rel.is_absolute() and ".." not in rel.parts
            assert not any(c in name for c in ("\\", "\x00", "\r", "\n", ":"))
            assert name not in seen, "Duplicate ZIP member"
            seen.add(name)
            assert not stat.S_ISLNK(member.external_attr >> 16), "Symlink ZIP member"
            target = a.destination / rel
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            payload = archive.read(member)
            assert len(payload) == member.file_size
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            assert target.read_bytes() == payload
            rows.append({"path": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    report = {"schema": "luoyang-r10-artifact-extraction-v1", "status": "passed", "artifact_zip": a.zip.name,
              "artifact_bytes": len(raw), "artifact_sha256": a.sha256, "github_digest_verified": True,
              "file_count": len(rows), "extracted_bytes": sum(row["bytes"] for row in rows), "files": rows,
              "signed_download_url_retained": False, "errors": []}
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "artifact_bytes", "artifact_sha256", "file_count", "extracted_bytes")}))


if __name__ == "__main__":
    main()
