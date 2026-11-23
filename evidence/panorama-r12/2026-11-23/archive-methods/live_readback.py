#!/usr/bin/env python3
"""Read actual public R12 bytes after production; do not rebuild them."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.request
from urllib.parse import urljoin, urlparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip('/') + '/'
    origin = urlparse(base)
    assert origin.scheme == 'https' and not origin.query and not origin.fragment
    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    report = {'schema': 'luoyang-r12-independent-live-readback-v1',
              'base_url': base, 'expected_commit': args.commit,
              'started_at': datetime.now(timezone.utc).isoformat(),
              'status': 'in_progress', 'files': {}}

    def get(path, expected=None):
        member = PurePosixPath(path)
        assert not member.is_absolute() and '..' not in member.parts and '\\' not in path
        assert str(member) == path
        url = urljoin(base, path)
        assert url.startswith(base)
        request = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(request, timeout=60) as response:
            assert response.status == 200 and response.url.startswith(base)
            raw = response.read()
            headers = {key: response.headers.get(key) for key in
                       ('Content-Type', 'Content-Length', 'ETag', 'Last-Modified', 'Date')}
        digest = hashlib.sha256(raw).hexdigest()
        target = root / 'bytes' / member
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        record = {'url': url, 'fetched_at': datetime.now(timezone.utc).isoformat(),
                  'bytes': len(raw), 'sha256': digest, 'headers': headers,
                  'retained_path': str(target.relative_to(root)),
                  'expected_sha256': expected, 'hash_matches': expected is None or digest == expected}
        report['files'][path] = record
        assert record['hash_matches'], 'Public byte mismatch: ' + path
        return raw

    try:
        info = json.loads(get('build-info.json'))
        assert info['source_commit'] == args.commit
        meta = info['panorama_review_v14']
        assert meta['source_commit'] == args.commit
        assert meta['status'] == 'needs_revision'
        assert meta['review_status'] == 'rejected_needs_revision'
        assert meta['homepage_replacement_approved'] is False
        assert meta['blocking_findings']
        wanted = set(meta['download_files']) | set(meta['files_sha256']) | {
            'release.json', 'index.html', 'v3.0-dual.html', meta['page'], meta['record'], meta['manifest']}
        for image in meta['images'].values():
            wanted.update([image['full'], image['small']])
        for path in sorted(wanted):
            get(path, info['files_sha256'][path])
        release = json.loads((root / 'bytes/release.json').read_bytes())
        assert release['panorama_review_v14_status'] == meta['status']
        assert release['panorama_review_v14_review_status'] == meta['review_status']
        for home in ['index.html', 'v3.0-dual.html']:
            html = (root / 'bytes' / home).read_text()
            assert 'data-hero-revision="panorama-approved-v12"' in html
            assert 'V14试绘审查·未通过' in html
        report.update(status='passed', source_commit=info['source_commit'],
                      image_status=meta['status'], image_review_status=meta['review_status'],
                      homepage_replacement_approved=False,
                      required_downloads=list(meta['download_files']),
                      verified_files=len(report['files']), download_count=len(meta['download_files']))
    except Exception as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        (root / 'readback.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key not in ('files', 'required_downloads')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
