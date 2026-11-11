#!/usr/bin/env python3
"""Build a minimal Pages artifact; never publish the whole working tree."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import hashlib
import json
import os
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '_site'
PDF = 'downloads/luoyang-v24-regional-atlas.pdf'
PDF_SHA256 = '14f30eeb1e525d090e8d75acfd896049e57b57d0d6b3381c16d1c4f289b72823'
DATA = ('entities', 'markers', 'disputes', 'regions', 'sheets', 'manifest')

def require(ok, message):
    if not ok:
        raise ValueError(message)

def safe_path(base, relative):
    path = (base / relative).resolve()
    require(path.is_relative_to(base.resolve()), f'Unsafe local path: {relative}')
    return path

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('src', 'href') and value:
                url = urlsplit(value)
                if not url.scheme and not url.netloc and url.path:
                    self.paths.append(unquote(url.path))

def main():
    data = {name: json.loads((ROOT / 'data' / f'{name}.json').read_text()) for name in DATA}
    counts = {'entities': 339, 'markers': 179, 'regions': 11, 'sheets': 37, 'disputes': 30}
    for name, count in counts.items():
        require(len(data[name]) == count, f'{name}: expected {count} records')
    tree = ET.parse(ROOT / 'assets/master-v24.svg')
    hx, hy, hw, hh = map(float, tree.getroot().attrib['viewBox'].split())
    for region in data['regions']:
        x, y, width, height = region['bbox']
        require(width > 0 and height > 0, f"Invalid xywh region: {region['code']}")
        require(hx <= x and hy <= y and x + width <= hx + hw and y + height <= hy + hh,
                f"Region outside drawing: {region['code']}")
    pdf = (ROOT / PDF).read_bytes()
    require(hashlib.sha256(pdf).hexdigest() == PDF_SHA256, 'Assembled PDF hash mismatch')
    files = {'index.html', 'styles.css', 'app.js', '.nojekyll', 'assets/master-v24.svg', PDF,
             'docs/data-provenance.md', 'docs/v2.4-release-notes.txt'}
    files.update(f'data/{name}.json' for name in DATA)
    for sheet in data['sheets']:
        files.update((sheet['svg'], sheet['thumbnail']))
    for relative in files:
        require(safe_path(ROOT, relative).is_file(), f'Missing asset: {relative}')
    require(not OUT.is_symlink(), 'Refusing to replace a symlink at _site')
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    hashes = {}
    for relative in sorted(files):
        src, dest = safe_path(ROOT, relative), safe_path(OUT, relative)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        hashes[relative] = hashlib.sha256(dest.read_bytes()).hexdigest()
        if dest.suffix == '.svg':
            ET.parse(dest)
    links = Links()
    links.feed((OUT / 'index.html').read_text())
    for relative in links.paths:
        require(not relative.startswith('/'), f'Project Pages path must be relative: {relative}')
        require(safe_path(OUT, relative).is_file(), f'Broken local HTML link: {relative}')
    info = {'research_version': 'v2.4', 'web_version': '0.1.1',
            'source_commit': os.environ.get('GITHUB_SHA', 'local-review'),
            'region_bbox_format': 'x,y,width,height', 'counts': counts,
            'pdf_sha256': PDF_SHA256, 'files_sha256': hashes}
    (OUT / 'build-info.json').write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n')
    size = sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
    print(f'OK: {len(files) + 1} published files, {size:,} bytes; PDF hash and local links verified')
    print('Excluded: Git metadata, research sources, PDF fragments, scripts and tests')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as handle:
            handle.write('## Website build verified\n\n')
            handle.write(f'- Research baseline: v2.4; web implementation: 0.1.1\n- Counts: {counts}\n')
            handle.write(f'- Published files: {len(files) + 1}; bytes: {size:,}\n')
            handle.write('- Original PDF SHA-256 and local HTML links verified.\n')
            handle.write('- Build success is not deployment success; check the deploy job separately.\n')

if __name__ == '__main__':
    main()
