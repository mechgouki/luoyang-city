#!/usr/bin/env python3
"""Real browser acceptance for B6 literary regions and named ground review."""
import argparse
import functools
import hashlib
import http.server
import json
import os
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--base-url')
parser.add_argument('--output', default='artifacts/southeast-b6-browser')
args = parser.parse_args()
out = ROOT / args.output
out.mkdir(parents=True, exist_ok=True)
checks, errors = [], []
server = temporary = page = None

if args.base_url:
    base = args.base_url.rstrip('/') + '/'
else:
    temporary = tempfile.TemporaryDirectory()
    server_root = Path(temporary.name)
    (server_root / 'luoyang-city').symlink_to(ROOT / '_site', target_is_directory=True)

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(
        ('127.0.0.1', 0), functools.partial(Quiet, directory=server_root))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/luoyang-city/'


def ok(name):
    checks.append({'name': name, 'status': 'passed'})
    print('PASS', name, flush=True)


def ready(target, dataset='southeastB6Ready'):
    target.wait_for_function(
        '(key) => document.documentElement.dataset[key] === "true"', arg=dataset)


def image_loaded(target, selector):
    target.wait_for_function(
        '(selector) => { const image = document.querySelector(selector); '
        'return image && image.complete && image.naturalWidth > 0; }', arg=selector)


def hash_params(target):
    return target.evaluate('''() => {
        const hash = location.hash.slice(1);
        return Object.fromEntries(new URLSearchParams(
            hash.includes('?') ? hash.slice(hash.indexOf('?') + 1) : hash));
    }''')


def read_json(context, path):
    response = context.request.get(base + path)
    assert response.status == 200, (path, response.status)
    return response.json()


def no_overflow(target):
    assert target.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')


try:
    with sync_playwright() as pw:
        options = {'headless': True}
        if os.environ.get('CHROMIUM_PATH'):
            options['executable_path'] = os.environ['CHROMIUM_PATH']
        browser = pw.chromium.launch(**options)
        context = browser.new_context(viewport={'width': 1500, 'height': 1000})
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))

        page.goto(base, wait_until='networkidle')
        ready(page, 'southeastMainReady')
        expect(page.locator('#southeast-b6-entry')).to_be_visible()
        for batch, count in [('dual-b1', 7), ('dual-b2', 8), ('dual-b4', 4),
                             ('dual-b5', 11), ('dual-b6', 20)]:
            expect(page.locator(f'#map-viewport [data-batch="{batch}"]')).to_have_count(count)
        expect(page.locator('#map-viewport #west-glyphs-b3')).to_have_count(1)
        expect(page.locator('.feature-target')).to_have_count(179)
        expect(page.locator('#map-viewport [data-batch="dual-b6"][data-entity-id="ic_zhaoyi"]')).to_have_attribute('data-temporal-display', 'undated')
        expect(page.locator('#map-viewport [data-batch="dual-b6"][data-entity-id="v2_jianzhong"]')).to_contain_text('杨氏宅')
        expect(page.locator('#map-viewport [data-batch="dual-b6"][data-entity-id="v2_baoming"]')).to_have_attribute('data-temporal-display', 'conditional-identity')
        expect(page.locator('#map-viewport [data-batch="dual-b6"][data-entity-id="v2_baoming"]')).to_contain_text('前期年代依同名联接')
        for entity_id in ['ic_hutong', 'ic_yuanhui', 'ic_yishou', 'ic_guangming', 'v2_guijue']:
            expect(page.locator(f'#map-viewport [data-batch="dual-b6"][data-entity-id="{entity_id}"]')).to_have_count(0)
        ok('twenty B6 symbols coexist with B1-B5 and all 179 original hit targets')

        for region, entity_id, record, view in [
            ('R08', 'ic_zhaoyi', 'EI02', 'inner'),
            ('R09', 'office_dianyu', 'EO07', 'outer'),
        ]:
            page.goto(base + '#map?region=' + region, wait_until='networkidle')
            page.locator(f'.feature-target[data-ids="{entity_id}"] .feature-hit').click()
            expect(page.locator('.southeast-coverage')).to_contain_text(record)
            expect(page.locator('.southeast-coverage a')).to_have_attribute(
                'href', f'./dual-southeast.html#{view}?id={record}')
        ok('physical Zhaoyi and Dianyu clicks open the corresponding B6 evidence')

        page.goto(base + 'dual-southeast.html#inner?id=EI05', wait_until='networkidle')
        ready(page)
        expect(page.locator('[data-tab]')).to_have_count(5)
        expect(page.locator('#evidence-picker option')).to_have_count(34)
        expect(page.locator('#detail')).to_contain_text('昭仪池不是翟泉')
        expect(page.locator('#release-status')).to_contain_text('构建一致')
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/L08.svg')
        image_loaded(page, '#map')
        page.screenshot(path=str(out / 'southeast-inner-desktop.png'), full_page=True)
        ok('five literary views and 34 evidence records load with matching build identity')

        page.locator('#evidence-picker').select_option('EO07')
        expect(page.locator('[data-tab="outer"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/L09.svg')
        expect(page.locator('#detail')).to_contain_text('不是正始东邻')
        assert hash_params(page)['id'] == 'EO07'
        page.locator('#evidence-picker').select_option('EI07')
        expect(page.locator('[data-tab="inner"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/L08.svg')
        expect(page.locator('#detail')).to_contain_text('神桑')
        ok('selecting evidence automatically follows its inner or outer literary region')

        page.locator('#archive').check()
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/L08-archive.svg')
        assert hash_params(page) == {'id': 'EI07', 'archive': '1'}
        page.reload(wait_until='networkidle')
        ready(page)
        expect(page.locator('#archive')).to_be_checked()
        expect(page.locator('#evidence-picker')).to_have_value('EI07')
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/L08-archive.svg')
        image_loaded(page, '#map')
        page.locator('#zoom-in').click()
        assert page.locator('#map').evaluate('element => element.style.width') == '140%'
        page.locator('#zoom-reset').click()
        assert page.locator('#map').evaluate('element => element.style.width') == '100%'
        ok('L08 archive, evidence hash and zoom survive the expected interactions')

        page.locator('[data-tab="outer"]').click()
        expect(page.locator('#evidence-picker')).to_have_value('EO01')
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/L09-archive.svg')
        page.locator('#evidence-picker').select_option('EO11')
        page.reload(wait_until='networkidle')
        ready(page)
        expect(page.locator('[data-tab="outer"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#archive')).to_be_checked()
        expect(page.locator('#evidence-picker')).to_have_value('EO11')
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/L09-archive.svg')
        image_loaded(page, '#map')
        page.locator('#archive').uncheck()
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/L09.svg')
        assert hash_params(page) == {'id': 'EO11'}
        ok('L09 has its own working archive and restores its evidence deep link')

        page.locator('[data-tab="relations"]').click()
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/SE6-relations.svg')
        expect(page.locator('#archive-control')).to_be_hidden()
        image_loaded(page, '#map')
        page.locator('[data-tab="layers"]').click()
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/SE6-layers.svg')
        page.locator('#evidence-picker').select_option('EO11')
        expect(page.locator('[data-tab="layers"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#detail')).to_contain_text('533')
        expect(page.locator('#detail')).to_contain_text('534')
        image_loaded(page, '#map')
        page.locator('[data-tab="evidence"]').click()
        expect(page.locator('#all-evidence article')).to_have_count(34)
        expect(page.locator('#reading-grid')).to_be_hidden()
        page.locator('#record-EO14 a[href="#outer?id=EO14"]').click()
        expect(page.locator('[data-tab="outer"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#evidence-picker')).to_have_value('EO14')
        expect(page.locator('#detail')).to_contain_text('西北角直接修饰苏秦冢')
        page.screenshot(path=str(out / 'southeast-outer-desktop.png'), full_page=True)
        ok('relation, time-layer and full-source views keep attribution and regional navigation')

        info = read_json(context, 'build-info.json')
        data = read_json(context, 'dual/southeast-b6.json')
        ground = read_json(context, 'ground-review/metadata.json')
        sources = {source['id']: source for source in ground['sources']}
        lineages = {record['id']: record for record in ground['lineage_records']}
        page.goto(base + 'ground-review.html', wait_until='networkidle')
        ready(page, 'groundReviewReady')
        expect(page.locator('#ground-filter')).to_have_value('all')
        expect(page.locator('#ground-record option')).to_have_count(2)
        expect(page.locator('#ground-record')).to_have_value('baima')
        expect(page.locator('#ground-source')).to_have_value('MCT-BAIMA')
        expect(page.locator('#ground-source-detail')).to_be_hidden()
        expect(page.locator('#ground-record-detail')).to_be_visible()
        expect(page.locator('#ground-crop')).to_have_value('detail')
        expect(page.locator('#ground-scan-link')).to_have_attribute('href', sources['UT-8']['url'])
        image_loaded(page, '#ground-image')
        crop_urls = set()
        for crop in ['detail', 'context', 'legend']:
            page.locator('#ground-crop').select_option(crop)
            image_loaded(page, '#ground-image')
            crop_urls.add(page.locator('#ground-image').get_attribute('src'))
            assert hash_params(page)['crop'] == crop
        assert len(crop_urls) == 3
        ok('Baima opens three distinct original-scan crops with explicit source access')

        page.locator('#ground-record').select_option('huanghe-railway')
        expect(page.locator('#ground-source')).to_have_value('ZZ-BRIDGE')
        expect(page.locator('#ground-crop option')).to_have_count(2)
        expect(page.locator('#ground-crop')).to_have_value('detail')
        image_loaded(page, '#ground-image')
        bridge_detail = page.locator('#ground-image').get_attribute('src')
        page.locator('#ground-crop').select_option('context')
        image_loaded(page, '#ground-image')
        assert page.locator('#ground-image').get_attribute('src') != bridge_detail
        assert hash_params(page)['record'] == 'huanghe-railway'
        page.screenshot(path=str(out / 'ground-review-bridge-desktop.png'), full_page=True)
        ok('railway-bridge record loads its own crops and modern-source attribution')

        for status, record in [('pending', 'baima'), ('excluded', 'huanghe-railway')]:
            page.locator('#ground-filter').select_option(status)
            expect(page.locator('#ground-record option')).to_have_count(1)
            expect(page.locator('#ground-record')).to_have_value(record)
            expect(page.locator('#ground-record-detail')).to_be_visible()
            assert hash_params(page)['filter'] == status
        page.locator('#ground-filter').select_option('approved')
        expect(page.locator('#ground-empty')).to_be_visible()
        expect(page.locator('#ground-empty')).to_contain_text('获准地面控制点 0')
        expect(page.locator('#ground-record')).to_be_disabled()
        expect(page.locator('#ground-record-detail')).to_be_hidden()
        page.reload(wait_until='networkidle')
        ready(page, 'groundReviewReady')
        expect(page.locator('#ground-filter')).to_have_value('approved')
        expect(page.locator('#ground-empty')).to_be_visible()
        expect(page.locator('#ground-record')).to_be_disabled()
        expect(page.locator('#ground-record-detail')).to_be_hidden()
        ok('pending, excluded and empty approved filters work and restore without false controls')

        page.locator('#ground-filter').select_option('all')
        page.locator('#ground-record').select_option('baima')
        page.locator('#ground-crop').select_option('legend')
        page.locator('#ground-source').select_option('L531-K')
        expect(page.locator('#ground-source-detail')).to_be_hidden()
        page.locator('#ground-source-toggle').click()
        expect(page.locator('#ground-source-toggle')).to_have_attribute('aria-expanded', 'true')
        expect(page.locator('#ground-source-detail')).to_be_visible()
        expect(page.locator('#ground-source-detail')).to_contain_text(sources['L531-K']['title'])
        assert hash_params(page)['source'] == 'L531-K'
        assert hash_params(page)['open'] == '1'
        page.reload(wait_until='networkidle')
        ready(page, 'groundReviewReady')
        expect(page.locator('#ground-record')).to_have_value('baima')
        expect(page.locator('#ground-crop')).to_have_value('legend')
        expect(page.locator('#ground-source')).to_have_value('L531-K')
        expect(page.locator('#ground-source-detail')).to_be_visible()
        expect(page.locator('#ground-source-detail')).to_contain_text(sources['L531-K']['title'])
        page.locator('#ground-source-toggle').click()
        expect(page.locator('#ground-source-toggle')).to_have_attribute('aria-expanded', 'false')
        expect(page.locator('#ground-source-detail')).to_be_hidden()
        assert hash_params(page)['open'] == '0'
        ok('independent source selection and expanded provenance restore from the ground-review hash')

        expect(page.locator('#lineage-record option')).to_have_count(4)
        for lineage in ['l531-k', 'l531-l', 'japanese-north-china', 'survey-history']:
            page.locator('#lineage-record').select_option(lineage)
            expect(page.locator('#lineage-reading')).to_contain_text(lineages[lineage]['title'])
            assert hash_params(page)['lineage'] == lineage
        page.reload(wait_until='networkidle')
        ready(page, 'groundReviewReady')
        expect(page.locator('#lineage-record')).to_have_value('survey-history')
        expect(page.locator('#lineage-reading')).to_contain_text(lineages['survey-history']['title'])
        expect(page.locator('#ground-source')).to_have_value('L531-K')
        page.screenshot(path=str(out / 'ground-review-sources-desktop.png'), full_page=True)
        ok('four upstream-map lineage records remain distinct and persist independently of source selection')

        expect(page.locator('#ground-download')).to_have_attribute('href', './downloads/luoyang-ground-review-b6.zip')
        page.goto(base + 'dual-southeast.html', wait_until='networkidle')
        ready(page)
        for path in ['downloads/dual-southeast-b6-atlas.pdf',
                     'downloads/dual-southeast-b6-evidence.csv',
                     'downloads/dual-southeast-b6-package.zip',
                     'dual/southeast-b6.json']:
            expect(page.locator(f'.downloads a[href="./{path}"]')).to_be_visible()
        downloads = [
            'downloads/dual-southeast-b6-atlas.pdf',
            'downloads/dual-southeast-b6-evidence.csv',
            'downloads/dual-southeast-b6-package.zip',
            'downloads/luoyang-ground-review-b6.zip',
            'dual/southeast-b6.json', 'ground-review/metadata.json',
            'dual/maps/L08.svg', 'dual/maps/L08-archive.svg',
            'dual/maps/L09.svg', 'dual/maps/L09-archive.svg',
            'dual/maps/SE6-relations.svg', 'dual/maps/SE6-layers.svg',
            'dual/maps/SE6-evidence-inner.svg', 'dual/maps/SE6-evidence-outer.svg',
            'ground-review/candidate-summary.svg', 'ground-review/lineage-summary.svg',
        ]
        for path in downloads:
            response = context.request.get(base + path)
            assert response.status == 200, (path, response.status)
            content = response.body()
            assert hashlib.sha256(content).hexdigest() == info['files_sha256'][path], path
            if path.endswith('.pdf'):
                assert content.startswith(b'%PDF-'), path
            elif path.endswith('.zip'):
                assert content.startswith(b'PK\x03\x04'), path
        ok('sixteen actual downloads and diagrams match the published SHA256 manifest')

        assert data['source_commit'] == info['source_commit'] == info['southeast_b6']['source_commit'] == ground['source_commit']
        assert len(data['evidence']) == info['southeast_b6']['records'] == 34
        assert {record['source_region'] for record in data['evidence']} == {'R08', 'R09'}
        assert data['source_family_count'] == 1 and data['ancient_absolute_positions_added'] == 0
        assert data['drawing_audit']['type_groups_changed'] == 20
        assert data['drawing_audit']['anchors_moved'] is False
        assert ground['named_candidates'] == 2 and ground['approved_control_points'] == 0
        assert ground['approved_ground_control_points'] == []
        assert ground['original_horizontal_datum'] is None
        assert ground['original_geographic_crs'] is None
        assert not ground['project_registration_to_wgs84'] and not ground['ground_accuracy_assessed']
        assert not ground['coordinate_assignment_performed'] and not ground['modern_dsm_modified']
        assert ground['ancient_geographic_positions_added'] == ground['ancient_channels_added'] == 0
        assert read_json(context, 'dual/southeast-b6-preservation.json')['protected_unchanged'] is True
        ok('B6 metadata preserves source identity, prior assets and zero unearned geographic controls')

        mobile = browser.new_context(viewport={'width': 390, 'height': 844},
                                     is_mobile=True, has_touch=True)
        mobile_page = mobile.new_page()
        mobile_page.on('pageerror', lambda error: errors.append(str(error)))
        mobile_page.goto(base, wait_until='networkidle')
        ready(mobile_page, 'southeastMainReady')
        expect(mobile_page.locator('.feature-target')).to_have_count(179)
        no_overflow(mobile_page)
        mobile_page.goto(base + 'dual-southeast.html#inner?id=EI05', wait_until='networkidle')
        ready(mobile_page)
        no_overflow(mobile_page)
        mobile_page.locator('#evidence-picker').select_option('EO07')
        expect(mobile_page.locator('[data-tab="outer"]')).to_have_attribute('aria-pressed', 'true')
        expect(mobile_page.locator('#detail')).to_contain_text('不是正始东邻')
        mobile_page.locator('#archive').check()
        mobile_page.reload(wait_until='networkidle')
        ready(mobile_page)
        expect(mobile_page.locator('#archive')).to_be_checked()
        expect(mobile_page.locator('#map')).to_have_attribute('src', './dual/maps/L09-archive.svg')
        mobile_page.locator('[data-tab="layers"]').tap()
        mobile_page.locator('#evidence-picker').select_option('EO11')
        expect(mobile_page.locator('#detail')).to_contain_text('534')
        no_overflow(mobile_page)
        mobile_page.screenshot(path=str(out / 'southeast-mobile.png'), full_page=True)
        ok('390px main map and literary tabs, evidence and archive controls work without page overflow')

        mobile_page.goto(base + 'ground-review.html', wait_until='networkidle')
        ready(mobile_page, 'groundReviewReady')
        no_overflow(mobile_page)
        mobile_page.locator('#ground-filter').select_option('excluded')
        expect(mobile_page.locator('#ground-record')).to_have_value('huanghe-railway')
        mobile_page.locator('#ground-crop').select_option('context')
        image_loaded(mobile_page, '#ground-image')
        mobile_page.locator('#ground-source').select_option('ZZ-BRIDGE')
        mobile_page.locator('#ground-source-toggle').tap()
        expect(mobile_page.locator('#ground-source-detail')).to_be_visible()
        mobile_page.locator('#lineage-record').select_option('l531-l')
        mobile_page.reload(wait_until='networkidle')
        ready(mobile_page, 'groundReviewReady')
        expect(mobile_page.locator('#ground-filter')).to_have_value('excluded')
        expect(mobile_page.locator('#ground-record')).to_have_value('huanghe-railway')
        expect(mobile_page.locator('#ground-crop')).to_have_value('context')
        expect(mobile_page.locator('#ground-source')).to_have_value('ZZ-BRIDGE')
        expect(mobile_page.locator('#ground-source-detail')).to_be_visible()
        expect(mobile_page.locator('#lineage-record')).to_have_value('l531-l')
        no_overflow(mobile_page)
        mobile_page.locator('#ground-filter').select_option('approved')
        expect(mobile_page.locator('#ground-empty')).to_be_visible()
        expect(mobile_page.locator('#ground-record-detail')).to_be_hidden()
        no_overflow(mobile_page)
        mobile_page.screenshot(path=str(out / 'ground-review-mobile.png'), full_page=True)
        ok('390px ground-review filters, crops, source details and lineage survive reload and empty results')

        assert not errors, errors
        ok('zero browser runtime errors')
        browser.close()
except Exception as error:
    checks.append({'name': 'B6 browser acceptance', 'status': 'failed', 'error': str(error)})
    if page:
        try:
            page.screenshot(path=str(out / 'failure.png'), full_page=True)
        except Exception:
            pass
    raise
finally:
    (out / 'results.json').write_text(json.dumps(
        {'base_url': base, 'checks': checks, 'runtime_errors': errors}, ensure_ascii=False, indent=2))
    if server:
        server.shutdown()
    if temporary:
        temporary.cleanup()
