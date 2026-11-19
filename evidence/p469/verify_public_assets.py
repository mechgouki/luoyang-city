import concurrent.futures
import hashlib
import io
import json
import pathlib
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

from pypdf import PdfReader

ROOT = pathlib.Path('/workspace/scratch/085c80f18d26')
REPO = ROOT / 'luoyang-city'
WORK = ROOT / 'p469-work'
ASSETS = WORK / 'assets'
ASSETS.mkdir(exist_ok=True)
BASE = 'https://mechgouki.github.io/luoyang-city/'
COMMIT = 'e58880049cb88db17379a63bbe2377c63a7e7fe2'
report = {
    'schema': 'p469-independent-public-asset-verification-v1',
    'started_at_utc': datetime.now(timezone.utc).isoformat(),
    'base_url': BASE,
    'expected_source_commit': COMMIT,
    'scope': 'Bounded independent public-resource readback; not a browser-interaction replacement',
    'network_attempt_limit': 3,
    'network_timeout_seconds': 30,
    'checks': [],
    'files': [],
}
cache = {}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def fetch(path):
    attempts = []
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(BASE + path, headers={'User-Agent': 'Luoyang-P469-Public-Verification/1.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
                status = response.status
            attempts.append({'attempt': attempt, 'status': status, 'bytes': len(data)})
            if status != 200:
                raise RuntimeError(f'HTTP status {status}')
            return {'path': path, 'status': 'passed', 'http_status': status, 'bytes': len(data),
                    'sha256': sha(data), 'attempts': attempts}, data
        except Exception as exc:
            attempts.append({'attempt': attempt, 'error': type(exc).__name__, 'message': str(exc)})
            if attempt == 3:
                return {'path': path, 'status': 'failed', 'attempts': attempts}, None
            time.sleep(attempt)

def record(path, row, data, manifest=None):
    if data is not None:
        cache[path] = data
        dest = ASSETS / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        if manifest is not None:
            row['expected_sha256'] = manifest[path]
            row['manifest_hash_matches'] = row['sha256'] == manifest[path]
            if not row['manifest_hash_matches']:
                row['status'] = 'failed'
    report['files'].append(row)

def check(name, condition, detail=None):
    row = {'name': name, 'status': 'passed' if condition else 'failed'}
    if detail is not None:
        row['detail'] = detail
    report['checks'].append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)

row, data = fetch('build-info.json')
record('build-info.json', row, data)
info = json.loads(data)
check('live_source_commit_matches_expected', info['source_commit'] == COMMIT, info['source_commit'])
check('P469_source_commit_matches_expected', info['prosperity_backbone_p469']['source_commit'] == COMMIT)
hashes = info['files_sha256']
row, data = fetch('homepage/approval-v9.json')
record('homepage/approval-v9.json', row, data, hashes)
hero = json.loads(data)['hero']
paths = {p for p in hashes if p.startswith('backbone-469/')}
paths |= {'prosperity-backbone-p469.html', 'downloads/backbone-469.pdf', 'downloads/backbone-469.zip'}
paths |= {hero['asset'], hero['small_asset'], 'index.html', 'prosperity-water-p468.html'}
paths |= {'downloads/south-466.pdf', 'downloads/water-467.pdf', 'downloads/water-468.pdf',
          'water-467/readings.json'}
paths |= {'water-467/' + name for name in info['prosperity_water_p467']['plates']}
paths |= set(info['prosperity_water_p468']['data_files'])
paths |= {'water-468/' + name for name in info['prosperity_water_p468']['plates']}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    pending = {pool.submit(fetch, path): path for path in sorted(paths)}
    for future in concurrent.futures.as_completed(pending):
        path = pending[future]
        row, data = future.result()
        record(path, row, data, hashes)
        print(json.dumps({k: row[k] for k in ['path', 'status', 'bytes'] if k in row}, ensure_ascii=False), flush=True)

check('approved_H2_desktop_unchanged', sha(cache[hero['asset']]) == '6465657667ba740d3fc99cde2495a864d3a8a446e2086c25984c0c547eed5825')
check('approved_H2_mobile_unchanged', sha(cache[hero['small_asset']]) == '98459529d0a2d8210aaf2728b0c1673ca38b46df2f7b761c9064f1c21fe053b6')
check('P466_PDF_unchanged_from_repository_archive', cache['downloads/south-466.pdf'] == (REPO/'research/prosperity-v4/archive/south-466.pdf').read_bytes())
check('P467_PDF_unchanged_from_repository_archive', cache['downloads/water-467.pdf'] == (REPO/'research/prosperity-v4/archive/water-467.pdf').read_bytes())
check('P467_readings_unchanged_from_repository_source', cache['water-467/readings.json'] == (REPO/'research/prosperity-v4/water-467/readings.json').read_bytes())
check('P468_PDF_matches_previous_release_registered_hash', sha(cache['downloads/water-468.pdf']) == 'c9e562c6c8f27a5fd1d316e9a5f6e2f6db13f7a95d9d0b41d3219501e572eb3f')
for path in info['prosperity_water_p468']['data_files']:
    check('P468_data_matches_repository_source:' + path, cache[path] == (REPO/'research/prosperity-v4'/path).read_bytes())

for path, count in [('downloads/backbone-469.pdf', 2), ('downloads/south-466.pdf', 3),
                    ('downloads/water-467.pdf', 5), ('downloads/water-468.pdf', 5)]:
    actual = len(PdfReader(io.BytesIO(cache[path])).pages)
    check('PDF_page_count:' + path, actual == count, {'expected': count, 'actual': actual})

manifest_path = 'backbone-469/bundle-manifest.json'
manifest = json.loads(cache[manifest_path])
check('offline_manifest_source_commit', manifest['source_commit'] == COMMIT)
for path, digest in manifest['source_inputs_sha256'].items():
    check('offline_manifest_source_hash:' + path, sha((REPO/path).read_bytes()) == digest)

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.add(a['id'])
        self.links.extend(a[k] for k in ['href', 'src'] if k in a)

with zipfile.ZipFile(io.BytesIO(cache['downloads/backbone-469.zip'])) as archive:
    names = archive.namelist()
    members = set(names)
    expected = set(manifest['files_sha256']) | {manifest_path, 'index.html'}
    check('offline_zip_members_exactly_match_manifest', members == expected and len(members) == len(names),
          {'member_count': len(names), 'expected_count': len(expected),
           'unexpected': sorted(members-expected), 'missing': sorted(expected-members)})
    check('offline_zip_manifest_matches_public_manifest', archive.read(manifest_path) == cache[manifest_path])
    member_checks = []
    for path, digest in manifest['files_sha256'].items():
        content = archive.read(path)
        member_checks.append({'path': path, 'hash_matches': sha(content) == digest,
                              'matches_public_asset': content == cache[path]})
    check('offline_zip_all_member_hashes_and_public_bytes_match', all(r['hash_matches'] and r['matches_public_asset'] for r in member_checks), member_checks)
    markup = Links()
    markup.feed(archive.read('index.html').decode('utf-8'))
    missing_links = []
    for link in markup.links:
        u = urlsplit(link)
        if u.scheme or u.netloc:
            continue
        if u.path and unquote(u.path).removeprefix('./') not in members:
            missing_links.append(link)
        elif not u.path and u.fragment and unquote(u.fragment) not in markup.ids:
            missing_links.append(link)
    check('offline_zip_local_links_resolve', not missing_links, missing_links)

page = Links()
page.feed(cache['prosperity-backbone-p469.html'].decode('utf-8'))
advertised = {unquote(urlsplit(link).path).removeprefix('./') for link in page.links
              if not urlsplit(link).scheme and not urlsplit(link).netloc}
downloads = {p for p in advertised if p.startswith('backbone-469/') and (p.endswith('.json') or p.endswith('.svg'))}
downloads |= {p for p in advertised if p.startswith('downloads/backbone-469.')}
check('all_advertised_P469_downloads_verified', downloads <= cache.keys(), {'count': len(downloads), 'paths': sorted(downloads)})
check('P468_page_contains_P469_entry_anchor', 'p469-entry' in cache['prosperity-water-p468.html'].decode('utf-8'))

previous_path = WORK / 'p468-previous-build-info.json'
previous = json.loads(previous_path.read_text())
previous_paths = ['water-467/' + name for name in info['prosperity_water_p467']['plates']]
previous_paths += ['downloads/south-466.pdf', 'downloads/water-467.pdf',
                   'water-467/readings.json', 'downloads/water-468.pdf']
for path in previous_paths:
    expected = previous['files_sha256'][path]
    actual = sha(cache[path])
    check('matches_prior_P468_release:' + path, actual == expected,
          {'previous_source_commit': previous['source_commit'],
           'expected_sha256': expected, 'actual_sha256': actual})
report['previous_release_reference'] = {
    'source_url': 'https://raw.githubusercontent.com/mechgouki/luoyang-city/a018052a2462632c2090e17fd8721fa8afc9fb74/evidence/p468/build-info.json',
    'evidence_commit': 'a018052a2462632c2090e17fd8721fa8afc9fb74',
    'source_commit': previous['source_commit'],
    'local_reference': previous_path.name,
    'sha256': sha(previous_path.read_bytes()),
}

report['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
report['checked_files'] = len(report['files'])
report['checked_assertions'] = len(report['checks'])
report['status'] = 'passed' if all(r['status'] == 'passed' for r in report['files'] + report['checks']) else 'failed'
report['http_failed_attempts'] = sum('error' in a for r in report['files'] for a in r.get('attempts', []))
(WORK/'public-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
summary = [f"P469 independent public readback: {report['status']}", f"Commit: {info['source_commit']}",
           f"Files: {report['checked_files']}; assertions: {report['checked_assertions']}; failed HTTP attempts: {report['http_failed_attempts']}",
           'P469 PDF pages: 2; ZIP exact member list, hashes, public-byte equality and local links checked.',
           'H2 approved desktop/mobile bytes, P466 archive PDF, P467 archive PDF/readings and P468 registered PDF/source JSON checked.',
           'P467 five SVGs, PDF/readings, P466 PDF and P468 PDF also match the previous P468 evidence build-info (evidence commit a018052a2462632c2090e17fd8721fa8afc9fb74).',
           'This readback does not replace browser interaction or production workflow acceptance.']
for p in ['downloads/backbone-469.pdf','downloads/backbone-469.zip','downloads/water-468.pdf']:
    summary.append(p+': '+sha(cache[p]))
(WORK/'public-verification-summary.txt').write_text('\n'.join(summary)+'\n')
print('\n'.join(summary), flush=True)
