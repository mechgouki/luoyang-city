#!/usr/bin/env python3
"""Real browser acceptance for the B8 city ledger and bounded source review."""
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
parser.add_argument('--output', default='artifacts/city-b8-browser')
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


def ready(target, dataset='cityReviewReady'):
    target.wait_for_function(
        '(key) => document.documentElement.dataset[key] === "true"', arg=dataset)


def hash_params(target):
    return target.evaluate('Object.fromEntries(new URLSearchParams(location.hash.slice(1)))')


def read_json(context, path):
    response = context.request.get(base + path)
    assert response.status == 200, (path, response.status)
    return response.json()


def no_overflow(target):
    assert target.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')


def image_loaded(target, selector):
    target.wait_for_function(
        '(selector) => { const image = document.querySelector(selector); '
        'return image && image.complete && image.naturalWidth > 0; }', arg=selector)


def clear_filters(target):
    target.locator('[data-view="map"]').click()
    target.locator('#clear-filters').click()
    expect(target.locator('#entity-filter')).to_have_value('all')
    expect(target.locator('#region-filter')).to_have_value('all')
    expect(target.locator('#entity-search')).to_have_value('')


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
        ready(page, 'cityMainReady')
        expect(page.locator('#city-b8-entry')).to_be_visible()
        expect(page.locator('.feature-target')).to_have_count(179)
        expect(page.locator('#map-viewport #city-audit-overlay-b8 .city-review-target')).to_have_count(179)
        for batch, count in [('dual-b1', 7), ('dual-b2', 8), ('dual-b4', 4),
                             ('dual-b5', 11), ('dual-b6', 20), ('dual-b7', 7)]:
            expect(page.locator(f'#map-viewport [data-batch="{batch}"]')).to_have_count(count)
        expect(page.locator('#map-viewport #west-glyphs-b3')).to_have_count(1)
        page.locator('#b8-review-toggle').uncheck()
        expect(page.locator('#map-viewport #city-audit-overlay-b8')).to_be_hidden()
        page.locator('#b8-review-toggle').check()
        expect(page.locator('#map-viewport #city-audit-overlay-b8')).to_be_visible()
        ok('B8 reading rings retain all earlier drawing batches and the original 179 interactive targets')

        page.goto(base + '#map?region=R09', wait_until='networkidle')
        page.locator('.feature-target[data-ids="v2_baoming"] .feature-hit').click()
        expect(page.locator('.city-review-coverage')).to_be_visible()
        expect(page.locator('.city-current-reading')).to_contain_text('同名')
        expect(page.locator('.baseline-temporal')).to_contain_text('基线字段')
        expect(page.locator('.city-review-coverage a[href="./dual-city-review.html#view=map&entity=v2_baoming"]')).to_be_visible()
        page.goto(base + '#map?entity=bridge_yong', wait_until='networkidle')
        expect(page.locator('.city-review-coverage')).to_contain_text('原交互层无目标')
        expect(page.locator('.city-review-coverage a[href="./dual-city-review.html#view=map&entity=bridge_yong"]')).to_be_visible()
        assert page.locator('.feature-target').evaluate_all('''targets => targets.every(target =>
            !target.dataset.ids.split(',').includes('bridge_yong'))''')
        ok('the main inspector separates Baoming conditions from its legacy field and keeps Yong bridge unlocated')

        info = read_json(context, 'build-info.json')
        ledger = read_json(context, 'city-review/ledger.json')
        cases = read_json(context, 'city-review/cases.json')
        sources = read_json(context, 'source-access/metadata.json')
        metadata = read_json(context, 'city-review/metadata.json')
        rows = {record['id']: record for record in ledger['entities']}
        page.goto(base + 'dual-city-review.html', wait_until='networkidle')
        ready(page)
        expect(page.locator('[data-view]')).to_have_count(4)
        expect(page.locator('#entity-select option')).to_have_count(339)
        expect(page.locator('#region-filter option')).to_have_count(12)
        expect(page.locator('#map-holder #city-audit-overlay-b8 .city-review-target')).to_have_count(179)
        expect(page.locator('#metric-entities')).to_have_text('339')
        expect(page.locator('#metric-targets')).to_have_text('179')
        expect(page.locator('#metric-cases')).to_have_text('14')
        expect(page.locator('#metric-unmapped')).to_have_text('102')
        expect(page.locator('#release-status')).to_contain_text('构建一致')
        page.screenshot(path=str(out / 'city-review-desktop.png'), full_page=True)
        ok('four city views load all 339 records and 179 reading rings with the matching release identity')

        for value, count in [('individual', 136), ('group_member', 101), ('no_interactive_target', 102)]:
            page.locator('#entity-filter').select_option(value)
            expect(page.locator('#entity-select option')).to_have_count(count)
            expect(page.locator('#result-count')).to_contain_text(f'匹配 {count} / 339')
            assert all(rows[value_id]['marker_state'] == value for value_id in
                       page.locator('#entity-select option').evaluate_all('options => options.map(x => x.value)'))
        ok('interaction filters expose the actual 136 individual, 101 grouped and 102 untargeted entities')

        for value, count in [('has_evidence', 209), ('catalog_only', 130)]:
            page.locator('#entity-filter').select_option(value)
            expect(page.locator('#entity-select option')).to_have_count(count)
            selected = page.locator('#entity-select option').evaluate_all('options => options.map(x => x.value)')
            assert all(bool(rows[entity_id]['direct_evidence_refs']) == (value == 'has_evidence') for entity_id in selected)
        page.locator('#entity-filter').select_option('review_cases')
        expect(page.locator('#entity-select option')).to_have_count(sum(bool(row['case_ids']) for row in rows.values()))
        assert all(rows[entity_id]['case_ids'] for entity_id in
                   page.locator('#entity-select option').evaluate_all('options => options.map(x => x.value)'))
        ok('evidence and case filters distinguish explicit references from historical verification')

        clear_filters(page)
        for query, entity_id in [('P167', 'bridge_yong'), ('宝明', 'v2_baoming'),
                                 ('ic_donggong_reserved', 'ic_donggong_reserved')]:
            page.locator('#entity-search').fill(query)
            expect(page.locator('#entity-select option')).to_have_count(1)
            expect(page.locator('#entity-select')).to_have_value(entity_id)
            expect(page.locator('#entity-detail')).to_contain_text(entity_id)
        page.locator('#entity-search').fill('__b8_no_entity_match__')
        expect(page.locator('#entity-select option')).to_have_count(0)
        expect(page.locator('#entity-select')).to_be_disabled()
        expect(page.locator('#focus-selection')).to_be_disabled()
        expect(page.locator('#entity-detail')).to_contain_text('没有匹配实体')
        page.locator('#clear-filters').click()
        expect(page.locator('#entity-select option')).to_have_count(339)
        ok('name, map-number and entity-ID searches work and empty results do not create a selected point')

        page.locator('#region-filter').select_option('R11')
        expect(page.locator('#entity-select option')).to_have_count(15)
        expect(page.locator('#entity-select option[value="house_xiaobaoyin"]')).to_have_count(0)
        page.locator('#entity-select').select_option('bridge_yong')
        expect(page.locator('#focus-selection')).to_be_disabled()
        expect(page.locator('#entity-detail')).to_contain_text('R10、R11')
        expect(page.locator('#entity-detail')).to_contain_text('无可计算命中')
        expect(page.locator('#map-holder .city-review-target.selected')).to_have_count(0)
        clear_filters(page)
        page.locator('#entity-select').select_option('house_xiaobaoyin')
        expect(page.locator('#entity-detail')).to_contain_text('显式焦点名录：没有列入')
        expect(page.locator('#entity-detail')).to_contain_text('既有锚点落入图幅：R11')
        ok('region filtering uses explicit focus membership while bridge and incidental crop matches retain their limits')

        page.locator('#entity-select').select_option('ic_donggong_reserved')
        shared_target = rows['ic_donggong_reserved']['targets'][0]['id']
        assert rows['ic_taicang_jin']['targets'][0]['id'] == shared_target
        expect(page.locator('#entity-detail .group-members [data-entity-open]')).to_have_count(2)
        expect(page.locator('#map-holder .city-review-target.selected')).to_have_count(1)
        expect(page.locator(f'#map-holder .city-review-target[data-target-id="{shared_target}"]')).to_have_attribute(
            'data-entity-ids', 'ic_donggong_reserved ic_taicang_jin')
        page.locator('#entity-detail [data-entity-open="ic_taicang_jin"]').click()
        expect(page.locator('#entity-select')).to_have_value('ic_taicang_jin')
        expect(page.locator('#map-holder .city-review-target.selected')).to_have_count(1)
        page.locator('#focus-selection').click()
        assert page.locator('#map-holder').evaluate('element => element.style.width') == '320%'
        page.locator(f'#map-holder .city-review-target[data-target-id="{shared_target}"]').click()
        expect(page.locator('#entity-select')).to_have_value('ic_donggong_reserved')
        expect(page.locator('#map-holder .city-review-target')).to_have_count(179)
        ok('the shared palace-reserve area keeps one target for two members and supports physical ring selection')

        page.locator('#zoom-reset').click()
        assert page.locator('#map-holder').evaluate('element => element.style.width') == '100%'
        page.locator('#zoom-in').click()
        assert page.locator('#map-holder').evaluate('element => element.style.width') == '140%'
        page.locator('#zoom-out').click()
        assert page.locator('#map-holder').evaluate('element => element.style.width') == '100%'
        page.locator('#entity-filter').select_option('group_member')
        page.locator('#region-filter').select_option('R03')
        page.locator('#entity-search').fill('P70')
        expect(page.locator('#entity-select')).to_have_value('ic_donggong_reserved')
        page.locator('#show-review').uncheck()
        expect(page.locator('#map-holder #city-audit-overlay-b8')).to_be_hidden()
        expected_hash = {'view': 'map', 'entity': 'ic_donggong_reserved', 'filter': 'group_member',
                         'region': 'R03', 'q': 'P70', 'case': hash_params(page)['case'], 'overlay': '0'}
        assert hash_params(page) == expected_hash
        page.reload(wait_until='networkidle')
        ready(page)
        assert hash_params(page) == expected_hash
        expect(page.locator('#entity-filter')).to_have_value('group_member')
        expect(page.locator('#region-filter')).to_have_value('R03')
        expect(page.locator('#entity-search')).to_have_value('P70')
        expect(page.locator('#entity-select')).to_have_value('ic_donggong_reserved')
        expect(page.locator('#show-review')).not_to_be_checked()
        expect(page.locator('#map-holder #city-audit-overlay-b8')).to_be_hidden()
        page.locator('#show-review').check()
        expect(page.locator('#map-holder #city-audit-overlay-b8')).to_be_visible()
        ok('zoom and overlay controls work and all seven city hash fields restore the selected filtered record')

        clear_filters(page)
        page.locator('[data-view="ledger"]').click()
        expect(page.locator('#ledger-body tr[data-entity-row]')).to_have_count(339)
        page.locator('#entity-filter').select_option('no_interactive_target')
        expect(page.locator('#ledger-body tr[data-entity-row]')).to_have_count(102)
        expect(page.locator('#ledger-body tr[data-entity-row="bridge_yong"]')).to_contain_text('无交互目标')
        page.locator('#ledger-body [data-entity-open="bridge_yong"]').click()
        expect(page.locator('[data-view="map"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#entity-select')).to_have_value('bridge_yong')
        expect(page.locator('#focus-selection')).to_be_disabled()
        expect(page.locator('#entity-filter')).to_have_value('all')
        ok('the full ledger and filtered rows navigate to the same entity without assigning a new marker')

        page.locator('#entity-select').select_option('v2_baoming')
        expect(page.locator('#entity-detail .current-reading')).to_contain_text('同名')
        expect(page.locator('#entity-detail .legacy-field')).to_contain_text('盛时已有记载')
        expect(page.locator('#entity-detail')).to_contain_text('conditional-identity')
        expect(page.locator('#entity-detail a[href="./dual-southeast.html#outer?id=EO15"]')).to_be_visible()
        assert rows['v2_baoming']['legacy_temporal_state'] == 'attested_by_528'
        assert rows['v2_baoming']['drawing_status']['current_temporal_displays'] == ['conditional-identity']
        ok('Baoming presents its current identity condition beside the preserved baseline temporal field')

        page.locator('[data-view="cases"]').click()
        expect(page.locator('#case-list [data-case]')).to_have_count(14)
        correction = next(record for record in cases['records'] if record.get('errata', {}).get('legacy_record_id') == 'G15')
        page.locator(f'#case-list [data-case="{correction["id"]}"]').click()
        expect(page.locator('#case-detail .quotation-correction')).to_be_visible()
        expect(page.locator('#case-detail .quotation-correction')).to_contain_text(correction['errata']['legacy_quote'])
        expect(page.locator('#case-detail .quotation-correction')).to_contain_text(correction['errata']['corrected_source_quote'])
        for boundary in correction['required_boundary']:
            expect(page.locator('#case-detail')).to_contain_text(boundary)
        page.reload(wait_until='networkidle')
        ready(page)
        expect(page.locator('[data-view="cases"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator(f'#case-list [data-case="{correction["id"]}"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#case-detail .quotation-correction')).to_be_visible()
        old_dual = read_json(context, 'dual/data.json')
        old_g15 = next(record for record in old_dual['b2']['evidence'] if record['id'] == 'G15')
        assert old_g15['quote'] == correction['errata']['legacy_quote']
        assert old_g15['quote'] != correction['errata']['corrected_source_quote']
        page.screenshot(path=str(out / 'city-review-correction-desktop.png'), full_page=True)
        ok('fourteen cases include a restored G15 quotation correction while the earlier B2 record remains unchanged')

        page.locator('[data-view="sources"]').click()
        expect(page.locator('#source-content')).to_be_visible()
        for record in sources['access_records']:
            expect(page.locator('#source-content')).to_contain_text(record['target_call_number'])
            expect(page.locator('#source-content')).to_contain_text(record['status_label'])
        for record in sources['upstream_records']:
            expect(page.locator('#source-content')).to_contain_text(record['catalog_record_number'])
            expect(page.locator('#source-content')).to_contain_text(str(record['catalog_sheet_count']))
        for phrase in ['本批取得目标历史扫描：0', '取得接合表影像：0', '确证 AMS 实际用图：0', '获准地面控制点：0']:
            expect(page.locator('#source-content')).to_contain_text(phrase)
        for record in sources['structure_reviews']:
            expect(page.locator('#source-content')).to_contain_text(record['title'])
            expect(page.locator('#source-content')).to_contain_text(record['verdict'])
        page.locator('#source-content details summary').click()
        expect(page.locator('#source-content details')).to_have_attribute('open', '')
        for path in ['source-access/access-summary.svg', 'source-access/upstream-summary.svg']:
            image_loaded(page, f'#source-content img[src="./{path}"]')
        page.screenshot(path=str(out / 'city-review-sources-desktop.png'), full_page=True)
        ok('source access distinguishes catalog and index leads from scans, actual map matches and surviving controls')

        assert all(data['source_commit'] == info['source_commit'] for data in [ledger, cases, sources, metadata])
        assert info['city_review_b8']['entities'] == len(ledger['entities']) == 339
        assert ledger['counts']['direct_evidence_records'] == 183 and ledger['counts']['direct_evidence_refs'] == 506
        assert ledger['counts']['new_historical_verifications'] == ledger['counts']['new_ancient_coordinates'] == 0
        assert all(row['geographic_coordinates'] is None and row['historical_verification_added'] is False for row in rows.values())
        assert 'city_jinyang' not in rows
        assert rows['ic_sanji_jinyang']['constraint_references'][0]['resolution'] == 'known_external_reference'
        assert sources['original_horizontal_datum'] is None and sources['original_geographic_crs'] is None
        assert not sources['project_registration_to_wgs84'] and not sources['ground_accuracy_assessed']
        assert not sources['coordinate_assignment_performed'] and not sources['modern_dsm_modified']
        assert not sources['new_historical_image_obtained']
        assert sources['approved_ground_control_points'] == [] and sources['source_assets'] == []
        assert sources['ancient_geographic_positions_added'] == sources['ancient_channels_added'] == 0
        assert len(sources['access_records']) == 3 and len(sources['upstream_records']) == 2 and len(sources['structure_reviews']) == 1
        assert all(record['historical_image_obtained'] is False and record['actual_ams_source_match'] is False for record in sources['access_records'])
        assert all(record['actual_parent_sheet_match'] is False and record['index_sheet_obtained'] is False for record in sources['upstream_records'])
        assert all(record['approved_as_ground_control'] is False and record['coordinates'] is None and record['anchor_pixel'] is None for record in sources['structure_reviews'])
        ok('published metadata retains one commit and zero added historical verification, coordinates or control points')

        outputs = metadata['outputs']
        assert isinstance(outputs, list) and outputs and len(outputs) == len(set(outputs))
        minimum = {'downloads/luoyang-city-review-b8-atlas.pdf', 'city-review/overview.png',
                   'downloads/luoyang-city-review-b8-ledger.csv', 'city-review/ledger.json',
                   'city-review/cases.json', 'downloads/luoyang-city-review-b8-package.zip'}
        assert minimum.issubset(outputs)
        for path in minimum:
            expect(page.locator(f'.downloads a[href="./{path}"]')).to_be_visible()
        paths = sorted(set(outputs) | {'city-review/metadata.json', 'source-access/metadata.json'})
        for path in paths:
            assert path and not path.startswith('/') and '..' not in path.split('/') and ':' not in path, path
            response = context.request.get(base + path)
            assert response.status == 200, (path, response.status)
            content = response.body()
            assert hashlib.sha256(content).hexdigest() == info['files_sha256'][path], path
            if path.endswith('.pdf'):
                assert content.startswith(b'%PDF-'), path
            elif path.endswith('.zip'):
                assert content.startswith(b'PK\x03\x04'), path
            elif path.endswith('.png'):
                assert content.startswith(b'\x89PNG\r\n\x1a\n'), path
        ok(f'all {len(paths)} declared B8 downloads and metadata match their actual published SHA256 hashes')

        mobile = browser.new_context(viewport={'width': 390, 'height': 844},
                                     is_mobile=True, has_touch=True)
        mobile_page = mobile.new_page()
        mobile_page.on('pageerror', lambda error: errors.append(str(error)))
        mobile_page.goto(base, wait_until='networkidle')
        ready(mobile_page, 'cityMainReady')
        expect(mobile_page.locator('.feature-target')).to_have_count(179)
        no_overflow(mobile_page)
        mobile_page.goto(base + 'dual-city-review.html', wait_until='networkidle')
        ready(mobile_page)
        no_overflow(mobile_page)
        mobile_page.locator('#entity-filter').select_option('no_interactive_target')
        expect(mobile_page.locator('#entity-select option')).to_have_count(102)
        mobile_page.locator('#entity-search').fill('P167')
        expect(mobile_page.locator('#entity-select')).to_have_value('bridge_yong')
        expect(mobile_page.locator('#focus-selection')).to_be_disabled()
        mobile_page.locator('#show-review').uncheck()
        mobile_page.reload(wait_until='networkidle')
        ready(mobile_page)
        expect(mobile_page.locator('#entity-filter')).to_have_value('no_interactive_target')
        expect(mobile_page.locator('#entity-search')).to_have_value('P167')
        expect(mobile_page.locator('#entity-select')).to_have_value('bridge_yong')
        expect(mobile_page.locator('#focus-selection')).to_be_disabled()
        expect(mobile_page.locator('#show-review')).not_to_be_checked()
        no_overflow(mobile_page)
        mobile_page.screenshot(path=str(out / 'city-review-mobile.png'), full_page=True)
        ok('390px main and city maps retain 179 targets and restore the untargeted bridge filter without overflow')

        mobile_page.locator('#clear-filters').click()
        mobile_page.locator('[data-view="ledger"]').tap()
        expect(mobile_page.locator('#ledger-body tr[data-entity-row]')).to_have_count(339)
        no_overflow(mobile_page)
        mobile_page.locator('[data-view="cases"]').tap()
        mobile_page.locator(f'#case-list [data-case="{correction["id"]}"]').tap()
        expect(mobile_page.locator('#case-detail .quotation-correction')).to_be_visible()
        no_overflow(mobile_page)
        mobile_page.locator('[data-view="sources"]').tap()
        no_overflow(mobile_page)
        expected_mobile_hash = hash_params(mobile_page)
        assert expected_mobile_hash['view'] == 'sources' and expected_mobile_hash['case'] == correction['id']
        mobile_page.reload(wait_until='networkidle')
        ready(mobile_page)
        assert hash_params(mobile_page) == expected_mobile_hash
        expect(mobile_page.locator('[data-view="sources"]')).to_have_attribute('aria-pressed', 'true')
        expect(mobile_page.locator('#source-content')).to_contain_text('本批取得目标历史扫描：0')
        no_overflow(mobile_page)
        mobile_page.screenshot(path=str(out / 'city-review-sources-mobile.png'), full_page=True)
        ok('390px ledger, quotation correction and source views remain usable and restore without page overflow')

        assert not errors, errors
        ok('zero browser runtime errors')
        browser.close()
except Exception as error:
    checks.append({'name': 'B8 browser acceptance', 'status': 'failed', 'error': str(error)})
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
