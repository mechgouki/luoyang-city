"""Read the deployed R11 files independently and retain the actual HTTPS bytes."""
import argparse
import concurrent.futures
import hashlib
import io
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from pypdf import PdfReader

p = argparse.ArgumentParser()
p.add_argument("commit")
p.add_argument("--output", type=Path, default=Path("/tmp/r11-live-review"))
a = p.parse_args()
base = "https://mechgouki.github.io/luoyang-city/"
dest = a.output / "public"
dest.mkdir(parents=True, exist_ok=True)

def fetch(path):
    req = Request(base + path, headers={"User-Agent": "Luoyang-R11-public-verification", "Cache-Control": "no-cache"})
    with urlopen(req, timeout=45) as response:
        assert response.status == 200, (path, response.status)
        body = response.read()
    target = dest / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    return body

info = json.loads(fetch("build-info.json"))
assert info["source_commit"] == a.commit
meta = info["city_plan_r11"]
assert meta["source_commit"] == a.commit
paths = sorted(set(meta["files_sha256"]) | set(meta["download_files"]) | {"index.html", "v3.0-dual.html", "release.json"})

def check(path):
    body = fetch(path)
    actual = hashlib.sha256(body).hexdigest()
    assert actual == info["files_sha256"][path], (path, "SHA-256 mismatch")
    return {"path": path, "bytes": len(body), "sha256": actual, "status": "passed"}

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    checked = list(pool.map(check, paths))
assert json.loads((dest / meta["manifest"]).read_bytes()) == meta
data = json.loads((dest / meta["record"]).read_bytes())
assert data["source_commit"] == a.commit
assert len(data["features"]) == 237
assert len(data["coverage"]) == 339
assert len(data["constraints"]) == 302
assert len(data["views"]) == 16
assert sum(x["placement_group"] == "unplaced" for x in data["coverage"]) == 165
entry = '<a id="r11-plan-entry" href="./luoyang-city-plan.html">全城统一坐标 · 复原工作平面</a>'.encode()
for page in ("index.html", "v3.0-dual.html"):
    body = (dest / page).read_bytes()
    assert body.count(entry) == 1
    assert body.replace(entry, b"", 1) == (dest / "city-plan-r11/archive" / page).read_bytes()
pdf = PdfReader(io.BytesIO((dest / meta["pdf"]).read_bytes()))
assert len(pdf.pages) == 17
assert a.commit in str(pdf.metadata["/Keywords"])
assert all(any("\u3400" <= c <= "\u9fff" for c in page.extract_text()) for page in pdf.pages)
now = datetime.now(timezone.utc)
report = {"status": "passed", "source_commit": a.commit, "base_url": base,
          "checked_at_utc": now.isoformat(), "checked_at_shanghai": now.astimezone(ZoneInfo("Asia/Shanghai")).isoformat(),
          "public_files": checked, "download_links": len(meta["download_files"]), "counts": data["counts"],
          "unplaced_reasons": dict(Counter(row["unplaced_reason"] for row in data["coverage"] if row["placement_group"] == "unplaced")),
          "pdf_pages": len(pdf.pages), "homepage_exact_reversible_entries": 2,
          "scope": "Independent HTTPS readback of every R11 publication and download plus both homepages; full legacy and actual browser gates are retained separately in CI."}
(a.output / "public-readback-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "public_files"}, ensure_ascii=False))
print("verified_public_files", len(checked))
