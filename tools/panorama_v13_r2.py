"""Publish the R9 spatially constrained V13 revision as an unapproved candidate."""
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
from urllib.parse import urlsplit
import zlib

from city_nodes_r7_contract import BUILD_CONTROL_FILES
from city_nodes_r7_verify import webp_size
from homepage_artwork_v10 import PAGES, V12
from panorama_v13_r2_contract import (CURRENT_MILESTONE, FOLDER, KEY, MANIFEST, PAGE,
    RECORD, RESEARCH_VERSION, SOURCE_RECORD, VERSION, add_home, strip_current_entries)
from panorama_v13_r2_page import make_page

ROOT = Path(__file__).resolve().parents[1]
OLD_RECORD = 'research/panorama-r8/image-record.json'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def source_file(path):
    result = (ROOT / path).resolve()
    assert result.is_relative_to(ROOT) and result.is_file(), (path, 'Missing project input')
    return result


def validate_record(record):
    assert record['schema'] == 'luoyang-panorama-v13-r2-image-v1'
    assert record['revision'] == 'panorama-candidate-v13-r2'
    assert record['status'] == 'candidate_for_review'
    assert record['homepage_replacement_approved'] is False
    assert record['generation_tool'] == 'built-in image_gen'
    previous = json.loads(source_file(OLD_RECORD).read_bytes())
    assert record['source_image']['path'] == previous['full']['path']
    assert record['source_image']['sha256'] == previous['full']['sha256']
    assert digest(source_file(record['source_image']['path']).read_bytes()) == record['source_image']['sha256']
    assert all(record.get(k) for k in ('title', 'alt', 'prompt_file', 'candidate_review_file', 'changes', 'remaining_limits'))
    assert isinstance(record['historical_gate_reconstruction_completed'], bool)
    for scale in ('full', 'small'):
        im = record[scale]
        assert all(type(im[k]) is int and im[k] > 0 for k in ('width', 'height'))
        assert re.fullmatch(r'[a-f0-9]{64}', im['sha256']) and im['path'].endswith('.webp')
        raw = source_file(im['path']).read_bytes()
        assert digest(raw) == im['sha256'] and webp_size(raw) == (im['width'], im['height'])
    original = record['source_png']
    png = source_file(original['path']).read_bytes()
    assert digest(png) == original['sha256'] == record['source_png_sha256']
    assert png[:16] == b'\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR' and len(png) >= 33
    assert zlib.crc32(png[12:29]) == struct.unpack('>I', png[29:33])[0]
    dimensions = struct.unpack('>II', png[16:24])
    assert dimensions == (original['width'], original['height']) == (record['full']['width'], record['full']['height'])
    assert record['small']['width'] <= record['full']['width']
    ratio = lambda im: im['width'] / im['height']
    assert abs(ratio(record['full']) - ratio(record['small'])) < .005, 'Mobile image is cropped'
    assert abs(ratio(record['full']) - 1672 / 941) < .03, 'Wide composition was lost'
    detail = record['detail_view']
    assert detail['caption'] and set(detail['views']) == {'v13r2', 'v13'}
    assert all(type(detail[k]) is int and detail[k] > 0 for k in ('width', 'height'))
    for kind, position in detail['views'].items():
        image = record['full'] if kind == 'v13r2' else previous['full']
        assert all(type(position[k]) is int and position[k] >= 0 for k in ('x', 'y'))
        assert position['x'] + detail['width'] <= image['width']
        assert position['y'] + detail['height'] <= image['height']
    ids = []
    for item in record['changes']:
        assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', item['id'])
        ids.append(item['id'])
        assert all(isinstance(item[k], str) and item[k].strip() for k in ('title', 'observation', 'evidence', 'change', 'limitation'))
        assert item['evidence_links']
        for link in item['evidence_links']:
            parsed = urlsplit(link['url'])
            assert link['label'] and parsed.scheme in ('', 'https', 'http') and not link['url'].startswith('//')
    assert len(ids) == len(set(ids))
    assert all(isinstance(x, str) and x.strip() for x in record['remaining_limits'])
    review = json.loads(source_file(record['candidate_review_file']).read_bytes())
    assert review['source_png_sha256'] == record['source_png_sha256'], 'Review describes a different generated image'
    assert review.get('homepage_replacement_approved', False) is False
    if record.get('position_guide'):
        guide = record['position_guide']
        assert digest(source_file(guide['path']).read_bytes()) == guide['sha256'], 'Position guide differs from the generation record'
    return record


def build(site=ROOT / '_site'):
    info = json.loads((site / 'build-info.json').read_bytes())
    old_meta = info.get(KEY)
    release_raw = (site / (old_meta['predecessor_release']['path'] if old_meta else 'release.json')).read_bytes()
    release = json.loads(release_raw)
    record = validate_record(json.loads(source_file(SOURCE_RECORD).read_bytes()))
    previous = json.loads(source_file(OLD_RECORD).read_bytes())
    assert 'panorama_review_v13' in info, 'R9 candidate requires the preserved V13 review'
    assert (site / 'luoyang-city-spatial.html').is_file(), 'Build city_spatial_r9 first'
    dest = site / FOLDER
    dest.mkdir(parents=True, exist_ok=True)
    inputs = {p: digest(source_file(p).read_bytes()) for p in (SOURCE_RECORD, OLD_RECORD, record['source_png']['path'])}
    if record.get('position_guide'):
        inputs[record['position_guide']['path']] = record['position_guide']['sha256']
    assets = []

    def copy_input(source, target):
        raw = source_file(source).read_bytes()
        inputs[source] = digest(raw)
        (site / target).parent.mkdir(parents=True, exist_ok=True)
        (site / target).write_bytes(raw)
        assets.append(target)
        return raw

    images = {}
    for kind in ('v13r2', 'v13', 'v12'):
        for scale in ('full', 'small'):
            target = FOLDER + '/' + kind + ('' if scale == 'full' else '-small') + '.webp'
            if kind == 'v13r2':
                im = record[scale]
                raw = copy_input(im['path'], target)
                assert digest(raw) == im['sha256']
            else:
                source = info['panorama_review_v13']['images']['v13'][scale] if kind == 'v13' else (V12.full if scale == 'full' else V12.small)
                raw = (site / source).read_bytes()
                expected = previous[scale]['sha256'] if kind == 'v13' else (V12.full_sha if scale == 'full' else V12.small_sha)
                assert digest(raw) == expected, 'A previously reviewed image changed'
                (site / target).write_bytes(raw)
                assets.append(target)
            width, height = webp_size(raw)
            im = images.setdefault(kind, {})
            im[scale] = target
            im[scale + '_sha256'] = digest(raw)
            im[('' if scale == 'full' else 'small_') + 'width'] = width
            im[('' if scale == 'full' else 'small_') + 'height'] = height
        images[kind]['revision'] = record['revision'] if kind == 'v13r2' else (previous['revision'] if kind == 'v13' else V12.revision)

    prompt = FOLDER + '/generation-prompt.txt'
    copy_input(record['prompt_file'], prompt)
    audit_sources = {'source-audit.json': 'research/city-spatial-r9/source-audit.json',
                     'candidate-review.json': record['candidate_review_file']}
    if record.get('visual_audit_file'):
        audit_sources['visual-audit.json'] = record['visual_audit_file']
    audit_files = []
    audit_mapping = {}
    for filename, source in audit_sources.items():
        target = FOLDER + '/' + filename
        copy_input(source, target)
        audit_files.append(target)
        audit_mapping[target] = source
    for source, name in (('web/panorama-v13-r2.css', 'review.css'), ('web/panorama-v13-r2.js', 'review.js')):
        copy_input(source, FOLDER + '/' + name)
    data = dict(schema='luoyang-panorama-v13-r2-review-v1', research_version=RESEARCH_VERSION,
                implementation_version=VERSION, source_commit=info['source_commit'],
                target_years=[516, 528], candidate=copy.deepcopy(record), images=images,
                new_ancient_coordinates=0, new_shoreline_geometries=0,
                homepage_revision=V12.revision, homepage_replacement_approved=False,
                source_inputs_sha256=inputs, audit_files=audit_files, audit_source_paths=audit_mapping)
    dump(site / RECORD, data)
    assets.append(RECORD)
    downloads = [images['v13r2']['full'], RECORD, prompt, *audit_files, MANIFEST]
    (site / PAGE).write_text(make_page(data, downloads), encoding='utf-8')
    prior_homes = {}
    archive_files = []
    for page in PAGES:
        before = strip_current_entries((site / page).read_bytes())
        archive = FOLDER + '/homepage-before-r2-' + page
        (site / archive).write_bytes(before)
        prior_homes[page] = dict(archive=archive, sha256=digest(before))
        assets.append(archive)
        archive_files.append(archive)
        (site / page).write_bytes(add_home(before))
    release_archive = FOLDER + '/release-before-v13-r2.json'
    (site / release_archive).write_bytes(release_raw)
    assets.append(release_archive)
    excluded = {*PAGES, 'release.json', PAGE}
    protected = {path: checksum for path, checksum in info['files_sha256'].items()
                 if path not in excluded and not path.startswith(FOLDER + '/')}
    controls = {path: protected.pop(path) for path in BUILD_CONTROL_FILES}
    for path, checksum in {**protected, **controls}.items():
        assert digest((site / path).read_bytes()) == checksum, (path, 'Earlier published resource changed')
    meta = dict(version=VERSION, research_version=RESEARCH_VERSION, source_commit=info['source_commit'],
                page=PAGE, manifest=MANIFEST, record=RECORD, status='candidate_for_review',
                homepage_revision=V12.revision, homepage_replacement_approved=False,
                candidate_revision=record['revision'], source_inputs_sha256=inputs,
                files_sha256={path: digest((site / path).read_bytes()) for path in assets},
                images=images, change_count=len(record['changes']), download_files=downloads,
                new_ancient_coordinates=0, new_shoreline_geometries=0,
                predecessor_homepage=prior_homes,
                predecessor_release=dict(path=release_archive, sha256=digest(release_raw)),
                protected_files_sha256=protected, build_control_files_sha256=controls)
    dump(site / MANIFEST, meta)
    info[KEY] = meta
    release['extensions'] = sorted(set(release['extensions']) | {VERSION})
    release[KEY + '_version'] = VERSION
    release['current_milestone'] = CURRENT_MILESTONE
    dump(site / 'release.json', release)
    for path in [*assets, MANIFEST, PAGE, *PAGES, 'release.json']:
        info['files_sha256'][path] = digest((site / path).read_bytes())
    dump(site / 'build-info.json', info)
    return meta


if __name__ == '__main__':
    result = build()
    print(json.dumps({key: result[key] for key in ('version', 'status', 'change_count', 'homepage_revision', 'homepage_replacement_approved')}, ensure_ascii=False))
