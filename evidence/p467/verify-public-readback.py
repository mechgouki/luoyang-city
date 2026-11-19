"""Recheck the published P4.6.7 files and preserved H2/P4.6.6 bytes."""
import argparse
import concurrent.futures
import datetime
import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

from pypdf import PdfReader

p = argparse.ArgumentParser()
p.add_argument('--commit', required=True)
p.add_argument('--output', type=Path, default=Path(__file__).parent)
args = p.parse_args()
base = 'https://mechgouki.github.io/luoyang-city/'
args.output.mkdir(parents=True, exist_ok=True)

def get(path):
    with urlopen(Request(base + path, headers={'User-Agent': 'Luoyang-research-readback/1.0'}), timeout=45) as r:
        body = r.read()
        return body, r.status, r.headers.get('Content-Type'), r.geturl()

raw, status, _, _ = get('build-info.json')
info = json.loads(raw)
assert status == 200 and info['source_commit'] == args.commit
water = info['prosperity_water_p467']
assert water['source_commit'] == args.commit and water['atlas_pages'] == 5 and water['segments'] == 53
(args.output / 'build-info.json').write_bytes(raw)

paths = [
    water['page'], water['atlas'], *water['data_files'],
    *['water-467/' + name for name in water['plates']],
    'prosperity-south-p466.html', 'prosperity-field-p464.html',
    'downloads/south-466.pdf',
    '_assets/6465657667ba740d3fc9-luoyang-panorama-approved-v9.webp',
    '_assets/98459529d0a2d8210aaf-luoyang-panorama-approved-v9-small.webp',
]
fixed = {
    'downloads/south-466.pdf': '90e8011316936430cd06a2cf5660d8c749936c89f758ca9058d2d40b29990589',
    paths[-2]: '6465657667ba740d3fc99cde2495a864d3a8a446e2086c25984c0c547eed5825',
    paths[-1]: '98459529d0a2d8210aaf2728b0c1673ca38b46df2f7b761c9064f1c21fe053b6',
}

def check(path):
    body, http, content_type, url = get(path)
    digest = hashlib.sha256(body).hexdigest()
    assert http == 200 and digest == info['files_sha256'][path], path
    if path in fixed:
        assert digest == fixed[path], path
    extra = {}
    if path == water['atlas']:
        extra['pdf_pages'] = len(PdfReader(io.BytesIO(body)).pages)
        assert extra['pdf_pages'] == 5
        (args.output / 'water-467.pdf').write_bytes(body)
    if path == water['readings']:
        data = json.loads(body)
        assert len(data['plates']) == 5
        assert data['new_metric_measurements'] == 0
        assert data['new_516_528_bank_geometry'] is None
        assert data['geographic_coordinates'] is None
    if path == 'prosperity-south-p466.html':
        assert b'id="p467-entry"' in body
    if path == 'prosperity-field-p464.html':
        assert b'id="p467-water-correction"' in body
    return {'path': path, 'url': url, 'http_status': http, 'content_type': content_type,
            'bytes': len(body), 'sha256': digest, 'status': 'passed', **extra}

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(check, paths))
report = {
    'checked_beijing': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds'),
    'base_url': base, 'source_commit': info['source_commit'], 'status': 'passed',
    'checked_files': len(results), 'h2_and_p466_bytes_unchanged': True,
    'water_metadata': water, 'files': results,
}
(args.output / 'public-readback.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'source_commit': info['source_commit'], 'checked_files': len(results),
                  'pdf_pages': 5, 'pdf_sha256': info['files_sha256'][water['atlas']]}, ensure_ascii=False))
