"""Verify R9 candidate identity, equal-scale original-image views and preservation."""
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from city_nodes_r7_contract import BUILD_CONTROL_FILES
from city_nodes_r7_verify import Document, verify_links, webp_size
from homepage_artwork_v10 import PAGES, V12
from panorama_v13_r2_contract import (CURRENT_MILESTONE, FOLDER, HOME_ENTRIES, KEY,
    MANIFEST, PAGE, RECORD, RESEARCH_VERSION, SOURCE_RECORD, VERSION, strip_current_entries)

ROOT = Path(__file__).resolve().parents[1]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(info, reader, *, build_control_reader=None):
    from city_layout_r10_contract import restore_r9_context
    info, reader = restore_r9_context(info, reader)
    get = lru_cache(maxsize=None)(reader)
    hashes, meta = info['files_sha256'], info[KEY]
    assert json.loads(get(MANIFEST)) == meta
    assert meta['version'] == VERSION and meta['research_version'] == RESEARCH_VERSION
    data = json.loads(get(RECORD))
    assert data['source_commit'] == meta['source_commit'] == info['source_commit']
    assert data['research_version'] == RESEARCH_VERSION and data['implementation_version'] == VERSION
    assert data['target_years'] == [516, 528]
    assert meta['status'] == data['candidate']['status'] == 'candidate_for_review'
    assert data['candidate']['homepage_replacement_approved'] is data['homepage_replacement_approved'] is meta['homepage_replacement_approved'] is False
    assert meta['homepage_revision'] == data['homepage_revision'] == V12.revision
    assert data['new_ancient_coordinates'] == meta['new_ancient_coordinates'] == 0
    assert data['new_shoreline_geometries'] == meta['new_shoreline_geometries'] == 0
    assert data['candidate']['revision'] == meta['candidate_revision'] == 'panorama-candidate-v13-r2'
    assert data['source_inputs_sha256'] == meta['source_inputs_sha256']
    for path, checksum in data['source_inputs_sha256'].items():
        source = (ROOT / path).resolve()
        assert source.is_relative_to(ROOT) and source.is_file(), path
        assert digest(source.read_bytes()) == checksum, (path, 'Source evidence changed')
    record = json.loads((ROOT / SOURCE_RECORD).read_bytes())
    previous = json.loads((ROOT / 'research/panorama-r8/image-record.json').read_bytes())
    assert data['candidate'] == record, 'Published decisions differ from the selected record'
    assert record['source_image']['path'] == previous['full']['path']
    assert record['source_image']['sha256'] == previous['full']['sha256']
    assert record['source_png']['sha256'] == record['source_png_sha256'] == data['source_inputs_sha256'][record['source_png']['path']]
    assert data['images'] == meta['images'] and set(data['images']) == {'v13r2', 'v13', 'v12'}
    assert len(record['changes']) == meta['change_count'] > 0
    assert record['remaining_limits']
    resources = meta['files_sha256']
    assert set(resources) == {p for p in hashes if p.startswith(FOLDER + '/') and p != MANIFEST}
    for path, checksum in resources.items():
        assert digest(get(path)) == hashes[path] == checksum, path
    for path in (PAGE, MANIFEST):
        assert digest(get(path)) == hashes[path], path
    for kind, image in data['images'].items():
        for scale in ('full', 'small'):
            raw = get(image[scale])
            prefix = '' if scale == 'full' else 'small_'
            assert digest(raw) == image[scale + '_sha256']
            assert webp_size(raw) == (image[prefix + 'width'], image[prefix + 'height'])
            if kind == 'v13r2':
                original = record[scale]
                assert digest(raw) == original['sha256'] and webp_size(raw) == (original['width'], original['height'])
            elif kind == 'v13':
                assert digest(raw) == previous[scale]['sha256']
                assert raw == get(info['panorama_review_v13']['images']['v13'][scale]), 'Earlier V13 changed'
            else:
                original, checksum = (V12.full, V12.full_sha) if scale == 'full' else (V12.small, V12.small_sha)
                assert raw == get(original) and digest(raw) == checksum, 'Approved V12 changed'
    assert get(FOLDER + '/generation-prompt.txt') == (ROOT / record['prompt_file']).read_bytes()
    assert set(data['audit_files']) == set(data['audit_source_paths'])
    for path, source in data['audit_source_paths'].items():
        assert get(path) == (ROOT / source).read_bytes()
        if path.endswith('/candidate-review.json'):
            assert json.loads(get(path))['source_png_sha256'] == record['source_png_sha256']
    protected = meta['protected_files_sha256']
    mandatory = {'luoyang-panorama-v13.html', 'panorama-v13/review.json', 'panorama-v13/manifest.json',
                 'panorama-v13/v13.webp', 'panorama-v13/candidate-review.json', 'panorama-v13/generation-prompt.txt',
                 'luoyang-city-spatial.html', 'city-spatial-r9/manifest.json',
                 'city-nodes/readings.json', 'city-nodes/segments.csv', 'downloads/luoyang-city-nodes.zip',
                 V12.full, V12.small, V12.metadata}
    assert mandatory <= set(protected)
    for path, checksum in protected.items():
        assert digest(get(path)) == hashes[path] == checksum, (path, 'Earlier resource changed')
    controls = meta['build_control_files_sha256']
    assert set(controls) == BUILD_CONTROL_FILES and not BUILD_CONTROL_FILES.intersection(protected)
    for path, checksum in controls.items():
        assert hashes[path] == checksum
        if build_control_reader:
            assert digest(build_control_reader(path)) == checksum
    assert set(meta['predecessor_homepage']) == set(PAGES)
    for page, prior in meta['predecessor_homepage'].items():
        current, archive = get(page), get(prior['archive'])
        assert current.count(HOME_ENTRIES) == 1
        assert digest(current) == hashes[page]
        assert strip_current_entries(current) == archive
        assert digest(archive) == hashes[prior['archive']] == prior['sha256']
        assert f'data-hero-revision="{V12.revision}"'.encode() in current
        assert b'panorama-candidate-v13-r2' not in current
    prior = meta['predecessor_release']
    raw = get(prior['path'])
    assert digest(raw) == prior['sha256'] == hashes[prior['path']]
    expected = json.loads(raw)
    expected['extensions'] = sorted(set(expected['extensions']) | {VERSION})
    expected[KEY + '_version'] = VERSION
    expected['current_milestone'] = CURRENT_MILESTONE
    release = json.loads(get('release.json'))
    assert release == expected
    assert release['homepage_hero_revision'] == V12.revision and release['homepage_hero_status'] == 'approved'
    doc = verify_links(get(PAGE), hashes, current=PAGE)
    anchors = set(doc.ids)
    assert {'main', 'comparison', 'review-status', 'view-controls', 'view-status', 'gate-detail',
            'detail-v13r2', 'detail-v13', 'figure-v13r2', 'figure-v13', 'figure-v12', 'changes', 'limits', 'downloads'} <= anchors
    assert doc.downloads == meta['download_files']
    for item in record['changes']:
        assert 'change-' + item['id'] in anchors
        for link in item['evidence_links']:
            assert link['url'] in doc.links
    checked = set()
    for url in doc.links:
        parsed = urlsplit(url)
        if not parsed.scheme and parsed.path and parsed.fragment:
            target = parsed.path.removeprefix('./')
            if (target, parsed.fragment) not in checked:
                assert parsed.fragment in Document(get(target)).ids, url
                checked.add((target, parsed.fragment))
    assert any(url.startswith('./luoyang-city-spatial.html#decision-SP') for url in doc.links)
    detail = record['detail_view']
    svgs = [attrs for tag, attrs in doc.elements if tag == 'svg']
    original_views = [attrs for tag, attrs in doc.elements if tag == 'image']
    assert len(svgs) == len(original_views) == 2
    for kind, attrs, image_attrs in zip(('v13r2', 'v13'), svgs, original_views):
        pos, image = detail['views'][kind], data['images'][kind]
        assert attrs['viewbox'] == f"{pos['x']} {pos['y']} {detail['width']} {detail['height']}"
        assert (int(attrs['width']), int(attrs['height'])) == (detail['width'], detail['height'])
        assert attrs['preserveaspectratio'] == 'xMidYMid meet'
        assert image_attrs['href'] == './' + image['full'], 'Gate detail uses a substituted/cropped asset'
        assert (int(image_attrs['width']), int(image_attrs['height'])) == (image['width'], image['height'])
        assert image_attrs['x'] == image_attrs['y'] == '0'
    return dict(status='passed', source_commit=info['source_commit'], candidate_revision=meta['candidate_revision'],
                homepage_revision=V12.revision, homepage_replacement_approved=False,
                change_count=meta['change_count'], downloads=len(doc.downloads), protected_public_files=len(protected),
                reversible_homepages=len(PAGES), original_image_detail_views=2,
                verified_cross_page_anchors=len(checked), new_ancient_coordinates=0, new_shoreline_geometries=0)
