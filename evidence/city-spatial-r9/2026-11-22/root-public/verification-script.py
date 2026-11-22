#!/usr/bin/env python3
"""Read-only post-deploy checks against the exact production commit."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.request import Request, urlopen

p = argparse.ArgumentParser()
p.add_argument('--commit', required=True)
p.add_argument('--output', required=True)
a = p.parse_args()
base = 'https://mechgouki.github.io/luoyang-city/'
out = Path(a.output)
out.mkdir(parents=True, exist_ok=True)

def fetch(path):
    req = Request(base + path + '?review=' + a.commit, headers={'Cache-Control': 'no-cache', 'User-Agent': 'Luoyang-R9-release-review'})
    with urlopen(req, timeout=45) as response:
        data = response.read()
        return data, response.status

opening, status = fetch('build-info.json')
assert status == 200
info = json.loads(opening)
assert info['source_commit'] == a.commit, info['source_commit']
assert info['city_spatial_r9']['source_commit'] == a.commit
assert info['panorama_review_v13_r2']['source_commit'] == a.commit
assert info['homepage_approved_v12']['hero_revision'] == 'panorama-approved-v12'
assert info['panorama_review_v13_r2']['homepage_replacement_approved'] is False
paths = {
    'release.json', 'index.html', 'v3.0-dual.html',
    'luoyang-city-spatial.html', 'luoyang-panorama-v13-r2.html',
    'luoyang-city-nodes.html', 'luoyang-panorama-v13.html',
    'panorama-v13/v13.webp', 'panorama-v13/v12.webp',
}
for key in ('city_spatial_r9', 'panorama_review_v13_r2'):
    paths.update(info[key]['download_files'])
for obj in info['panorama_review_v13_r2']['images'].values():
    paths.update((obj['full'], obj['small']))
paths.update(path for path in info['files_sha256'] if path.startswith('_assets/') and 'panorama-approved-v12' in path)

def check(path):
    data, status = fetch(path)
    digest = sha256(data).hexdigest()
    assert status == 200 and digest == info['files_sha256'][path], path
    if path in ('index.html', 'v3.0-dual.html'):
        assert data.count(b'id="r9-spatial-entry"') == 1
        assert data.count(b'id="r9-panorama-entry"') == 1
        assert b'panorama-approved-v12' in data
    if path == 'release.json':
        release = json.loads(data)
        assert release['homepage_hero_revision'] == 'panorama-approved-v12'
    return {'path': path, 'status': status, 'bytes': len(data), 'sha256': digest, 'matches_manifest': True}

with ThreadPoolExecutor(max_workers=6) as pool:
    checks = list(pool.map(check, sorted(paths)))
closing, status = fetch('build-info.json')
assert status == 200 and closing == opening, 'Production changed during check'
(out / 'build-info.json').write_bytes(opening)
report = {
    'status': 'passed', 'source_commit': a.commit,
    'checked_at_utc': datetime.now(timezone.utc).isoformat(),
    'base_url': base, 'opening_closing_build_info_equal': True,
    'build_info_sha256': sha256(opening).hexdigest(),
    'homepage_revision': 'panorama-approved-v12',
    'homepage_replacement_approved': False,
    'resource_count': len(checks), 'resources': checks,
    'scope': 'Additional root HTTP inspection of new deliverables, downloads, preserved candidate images and homepage entries; complete-site checks remain in production verify-live.'
}
(out / 'public-http-review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'commit': a.commit, 'resources': len(checks), 'report': str(out / 'public-http-review.json')}))
