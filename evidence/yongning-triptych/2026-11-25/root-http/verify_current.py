"""Independent HTTPS readback of the existing Yongning publication, 2026-11-25.

This does not recreate the missing earlier 49-file manual session or rerun CI.
All original response bytes are retained; timestamps record this invocation.
"""
from pathlib import Path, PurePosixPath
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import sys
import urllib.request

ROOT = Path('/workspace/scratch/f1dbf35eff8a/luoyang-city')
OUT = Path(__file__).resolve().parent
BASE = 'https://mechgouki.github.io/luoyang-city/'
COMMIT = 'bbfbac9022e133e61836614f3b120cf42efde43e'
START = datetime.now(timezone.utc).isoformat()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def get(path):
    request = urllib.request.Request(BASE + path, headers={'User-Agent':'LuoyangResearchVerification/1.0'})
    with urllib.request.urlopen(request, timeout=50) as response:
        body = response.read()
        headers = dict(response.headers)
        status = response.status
        url = response.url
    return body, dict(path=path, url=url, status=status, bytes=len(body), sha256=sha(body),
                     etag=headers.get('ETag'), last_modified=headers.get('Last-Modified'),
                     retrieved_at=datetime.now(timezone.utc).isoformat())

start_bytes, start_response = get('build-info.json')
info = json.loads(start_bytes)
assert info['source_commit'] == COMMIT
(OUT/'build-info-current-start.json').write_bytes(start_bytes)
parent = info['panorama_review_v14']
study = parent['yongning_study']
assert study['version'] == 'yongning-triptych-20261124'
paths = set(study['files_sha256']) | set(study['download_files'])
paths |= set(parent['download_files'])
paths |= {parent['page'], parent['manifest'], parent['record'], 'index.html', 'release.json', 'homepage/approval-v12.json'}
for image_record in parent['images'].values():
    paths.update(value for key, value in image_record.items()
                 if isinstance(value, str) and value in info['files_sha256'])
# Keep the actual source bytes required by the already published verifier.
hashes = info['files_sha256']
records = []
cached = {}

def fetch_one(path):
    assert path in hashes, path
    relative = PurePosixPath(path)
    assert not relative.is_absolute() and '..' not in relative.parts
    body, record = get(path)
    assert record['sha256'] == hashes[path], (path, 'publication SHA mismatch')
    output = OUT/'files'/path
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(body)
    return path, body, record

with ThreadPoolExecutor(max_workers=4) as pool:
    for path, body, record in pool.map(fetch_one, sorted(paths)):
        cached[path] = body
        records.append(record)

def reader(path):
    if path not in cached:
        key, body, record = fetch_one(path)
        cached[key] = body
        records.append(record)
    return cached[path]

sys.path.insert(0, str(ROOT/'tools'))
import yongning_study
study_verification = yongning_study.verify(info, reader, root=ROOT)
end_bytes, end_response = get('build-info.json')
(OUT/'build-info-current-end.json').write_bytes(end_bytes)
assert end_bytes == start_bytes, 'Source changed during readback'
report = dict(schema='luoyang-yongning-independent-live-readback-v1', status='passed',
              source_commit=COMMIT, started_at=START, completed_at=datetime.now(timezone.utc).isoformat(),
              scope='Current study, its eight downloads, V14 downloads and display identity, homepage approval; not a repeat of full-site CI',
              previous_49_file_session_reconstructed=False,
              requests_with_retry=0, unique_hashed_paths=len(records), build_info_stable=True,
              build_info_start=start_response, build_info_end=end_response,
              study_verification=study_verification, files=sorted(records,key=lambda row:row['path']),
              whole_ground_geometry_passed=False, full_panorama_accepted=False, homepage_replacement_approved=False)
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({key:report[key] for key in ['status','source_commit','unique_hashed_paths','completed_at']},ensure_ascii=False))
