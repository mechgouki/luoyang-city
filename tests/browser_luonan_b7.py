#!/usr/bin/env python3
"""Real browser acceptance for B7 Luonan reading groups and source continuity."""
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
parser.add_argument('--output', default='artifacts/luonan-b7-browser')
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


def ready(target, dataset='luonanB7Ready'):
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
        ready(page, 'luonanMainReady')
        expect(page.locator('#luonan-b7-entry')).to_be_visible()
        for batch, count in [('dual-b1', 7), ('dual-b2', 8), ('dual-b4', 4),
                             ('dual-b5', 11), ('dual-b6', 20), ('dual-b7', 7)]:
            expect(page.locator(f'#map-viewport [data-batch="{batch}"]')).to_have_count(count)
        expect(page.locator('#map-viewport #west-glyphs-b3')).to_have_count(1)
        expect(page.locator('.feature-target')).to_have_count(179)
        expect(page.locator('#map-viewport [data-batch="dual-b7"][data-entity-id]')).to_have_count(0)
        expect(page.locator('#luonan-bridge-b7')).to_have_attribute('data-locating-mode', 'bridge_annotation')
        expect(page.locator('#luonan-bridge-b7')).to_have_attribute('data-entity-ids', 'bridge_yong v3_yong_huabiao')
        expect(page.locator('#luonan-direction-b7')).to_have_attribute('data-locating-mode', 'direction_reference')
        for group in ['temples', 'fish', 'sitong']:
            expect(page.locator(f'#luonan-{group}-b7')).to_have_attribute('data-locating-mode', 'nonspatial_annotation')
            expect(page.locator(f'#luonan-{group}-b7')).to_have_attribute('data-footprint', 'false')
        expect(page.locator('#luonan-fish-b7')).to_contain_text('归正里')
        expect(page.locator('#luonan-sitong-b7')).to_contain_text('未证为同一市场')
        assert page.locator('.feature-target').evaluate_all('''targets => targets.every(target =>
            !target.dataset.ids.split(',').some(id => ['bridge_yong', 'road_siyi'].includes(id)))''')
        ok('seven B7 reading groups preserve earlier symbols and 179 targets without a new bridge point')

        for ids, record in [
            ('li_guizheng,li_guide,li_muhua,li_muyi', 'LG01'),
            ('market_fish,house_xiaobaoyin', 'LR07'),
            ('market_sitong', 'LR10'),
        ]:
            page.goto(base + '#map?region=R11', wait_until='networkidle')
            page.locator(f'.feature-target[data-ids="{ids}"] .feature-hit').click()
            expect(page.locator('.luonan-coverage')).to_contain_text(record)
            expect(page.locator('.luonan-coverage a')).to_have_attribute(
                'href', f'./dual-luonan.html#map?id={record}')
        page.goto(base + '#map?entity=bridge_yong', wait_until='networkidle')
        expect(page.locator('.luonan-coverage')).to_contain_text('LR01')
        expect(page.locator('.luonan-coverage a')).to_have_attribute('href', './dual-luonan.html#map?id=LG01')
        expect(page.locator('.feature-target')).to_have_count(179)
        ok('existing ward and market clicks plus the unlocated bridge record expose B7 evidence links')

        page.goto(base + 'dual-luonan.html#map?id=LR07', wait_until='networkidle')
        ready(page)
        expect(page.locator('[data-tab]')).to_have_count(5)
        expect(page.locator('#evidence-picker option')).to_have_count(25)
        expect(page.locator('#evidence-picker')).to_have_value('LR07')
        expect(page.locator('#detail')).to_contain_text('吴人坊')
        expect(page.locator('#release-status')).to_contain_text('构建一致')
        expect(page.locator('#summary-count')).to_contain_text('25 条证据')
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/L10.svg')
        image_loaded(page, '#map')
        page.screenshot(path=str(out / 'luonan-map-desktop.png'), full_page=True)
        ok('five literary views and all 25 evidence records load with matching build identity')

        page.locator('#archive').check()
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/L10-archive.svg')
        assert hash_params(page) == {'id': 'LR07', 'archive': '1'}
        page.reload(wait_until='networkidle')
        ready(page)
        expect(page.locator('#archive')).to_be_checked()
        expect(page.locator('#evidence-picker')).to_have_value('LR07')
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/L10-archive.svg')
        image_loaded(page, '#map')
        page.locator('#zoom-in').click()
        assert page.locator('#map').evaluate('element => element.style.width') == '140%'
        page.locator('#zoom-out').click()
        assert page.locator('#map').evaluate('element => element.style.width') == '100%'
        page.locator('#zoom-in').click()
        page.locator('#zoom-reset').click()
        assert page.locator('#map').evaluate('element => element.style.width') == '100%'
        page.locator('#archive').uncheck()
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/L10.svg')
        assert hash_params(page) == {'id': 'LR07'}
        ok('L10 archive, evidence deep link and all zoom controls restore correctly')

        page.locator('[data-tab="institutions"]').click()
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/LN7-institutions.svg')
        expect(page.locator('#archive-control')).to_be_hidden()
        page.locator('#evidence-picker').select_option('LG07')
        expect(page.locator('[data-tab="institutions"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#detail')).to_contain_text('没有重写三年已后')
        expect(page.locator('#detail')).to_contain_text('等待期未记')
        page.locator('#evidence-picker').select_option('LG11')
        expect(page.locator('#detail')).to_contain_text('不能把523直接写成归正寺始建年')
        image_loaded(page, '#map')
        ok('institutional correspondences retain unrecorded waiting periods and undated temple conversion')

        page.locator('[data-tab="markets"]').click()
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/LN7-markets.svg')
        page.locator('#evidence-picker').select_option('LR10')
        expect(page.locator('#detail')).to_contain_text('材料未证明两者同体')
        expect(page.locator('#detail')).to_contain_text('俗称永桥市不能自动增添桥旁精确位置')
        page.locator('#evidence-picker').select_option('LR08')
        page.locator('#detail .record-variants summary').click()
        expect(page.locator('#detail .record-variants')).to_have_attribute('open', '')
        expect(page.locator('#detail .record-variants')).to_contain_text('正光')
        expect(page.locator('#detail .record-variants')).to_contain_text('景明')
        expect(page.locator('[data-tab="markets"]')).to_have_attribute('aria-pressed', 'true')
        image_loaded(page, '#map')
        page.screenshot(path=str(out / 'luonan-markets-desktop.png'), full_page=True)
        ok('market records remain distinct and the textual date variants are accessible')

        page.locator('[data-tab="layers"]').click()
        expect(page.locator('#map')).to_have_attribute('src', './dual/maps/LN7-layers.svg')
        for record, phrases in [
            ('LR06', ['萧宝夤旧宅', '这个人不是后文萧正德']),
            ('LR03', ['二十丈', '图尺']),
            ('LR14', ['531', '途中被杀', '盛时母图不得']),
        ]:
            page.locator('#evidence-picker').select_option(record)
            expect(page.locator('[data-tab="layers"]')).to_have_attribute('aria-pressed', 'true')
            for phrase in phrases:
                expect(page.locator('#detail')).to_contain_text(phrase)
        page.reload(wait_until='networkidle')
        ready(page)
        expect(page.locator('[data-tab="layers"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#evidence-picker')).to_have_value('LR14')
        expect(page.locator('#archive-control')).to_be_hidden()
        image_loaded(page, '#map')
        ok('time layers preserve the former residence, unscaled huabiao and later lion events')

        page.locator('[data-tab="evidence"]').click()
        expect(page.locator('#all-evidence article.evidence-card')).to_have_count(25)
        expect(page.locator('#reading-grid')).to_be_hidden()
        page.reload(wait_until='networkidle')
        ready(page)
        expect(page.locator('[data-tab="evidence"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#all-evidence')).to_be_visible()
        page.locator('#record-LR10 a[href="#map?id=LR10"]').click()
        expect(page.locator('[data-tab="map"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#evidence-picker')).to_have_value('LR10')
        expect(page.locator('#detail')).to_contain_text('与鱼鳖巷市保持分记录')
        ok('the full evidence view restores from its hash and links back to the selected map record')

        info = read_json(context, 'build-info.json')
        data = read_json(context, 'dual/luonan-b7.json')
        continuity = read_json(context, 'source-continuity/metadata.json')
        records = {record['id']: record for record in continuity['records']}
        sources = {source['id']: source for source in continuity['sources']}
        page.goto(base + 'source-continuity.html', wait_until='networkidle')
        ready(page, 'sourceContinuityReady')
        expect(page.locator('#continuity-filter')).to_have_value('all')
        expect(page.locator('#continuity-record option')).to_have_count(3)
        expect(page.locator('#continuity-record')).to_have_value('zhengzhou-1942')
        expect(page.locator('#continuity-view')).to_have_value('timeline')
        expect(page.locator('#continuity-reading')).to_contain_text(records['zhengzhou-1942']['title'])
        expect(page.locator('#continuity-timeline')).to_be_visible()
        for date_kind in ['摄影', '测量', '制版', '出版']:
            expect(page.locator('#continuity-timeline')).to_contain_text(date_kind)
        expect(page.locator('#continuity-source-detail')).to_be_hidden()
        expect(page.locator('#continuity-count')).to_contain_text('新增历史扫描0幅')
        ok('three catalog records open with separate production dates and zero new historical scans')

        page.locator('#continuity-filter').select_option('period-match')
        expect(page.locator('#continuity-record option')).to_have_count(1)
        expect(page.locator('#continuity-record')).to_have_value('zhengzhou-1942')
        page.locator('#continuity-filter').select_option('earlier')
        expect(page.locator('#continuity-record option')).to_have_count(2)
        expect(page.locator('#continuity-record')).to_have_value('yanshi-1934')
        for record in ['yanshi-1934', 'sishui-1935']:
            page.locator('#continuity-record').select_option(record)
            expect(page.locator('#continuity-reading')).to_contain_text(records[record]['title'])
            expect(page.locator('#continuity-source-link')).to_have_attribute(
                'href', sources[records[record]['source_id']]['url'])
            assert hash_params(page)['record'] == record
        page.locator('#continuity-filter').select_option('period-match')
        expect(page.locator('#continuity-record')).to_have_value('zhengzhou-1942')
        ok('period and earlier-edition filters select only eligible records and their official source links')

        page.locator('#continuity-filter').select_option('earlier')
        page.locator('#continuity-record').select_option('sishui-1935')
        page.locator('#continuity-view').select_option('lineage')
        expect(page.locator('#continuity-lineage')).to_be_visible()
        expect(page.locator('#continuity-timeline')).to_have_count(0)
        expect(page.locator('#continuity-lineage')).to_contain_text('目录明载的制作关系')
        expect(page.locator('#continuity-lineage')).to_contain_text('与AMS实际用图关系：仍未证')
        expect(page.locator('#continuity-record')).to_have_value('sishui-1935')
        page.locator('#continuity-view').select_option('timeline')
        expect(page.locator('#continuity-timeline')).to_be_visible()
        expect(page.locator('#continuity-lineage')).to_have_count(0)
        page.locator('#continuity-view').select_option('lineage')
        ok('timeline and source lineage switch for the same record without asserting an AMS source match')

        page.locator('#continuity-source-toggle').click()
        expect(page.locator('#continuity-source-toggle')).to_have_attribute('aria-expanded', 'true')
        expect(page.locator('#continuity-source-detail')).to_be_visible()
        expect(page.locator('#continuity-source-detail')).to_contain_text(records['sishui-1935']['catalog_title'])
        assert hash_params(page) == {'record': 'sishui-1935', 'filter': 'earlier', 'view': 'lineage', 'open': '1'}
        page.reload(wait_until='networkidle')
        ready(page, 'sourceContinuityReady')
        expect(page.locator('#continuity-record')).to_have_value('sishui-1935')
        expect(page.locator('#continuity-filter')).to_have_value('earlier')
        expect(page.locator('#continuity-view')).to_have_value('lineage')
        expect(page.locator('#continuity-lineage')).to_be_visible()
        expect(page.locator('#continuity-source-toggle')).to_have_attribute('aria-expanded', 'true')
        expect(page.locator('#continuity-source-detail')).to_be_visible()
        expect(page.locator('#continuity-source-detail')).to_contain_text(records['sishui-1935']['catalog_title'])
        page.screenshot(path=str(out / 'source-continuity-desktop.png'), full_page=True)
        page.locator('#continuity-source-toggle').click()
        expect(page.locator('#continuity-source-detail')).to_be_hidden()
        assert hash_params(page)['open'] == '0'
        ok('record, filter, view and expanded source details restore from all four hash fields')

        expect(page.locator('#continuity-download')).to_have_attribute('href', './downloads/luoyang-source-continuity-b7.zip')
        page.goto(base + 'dual-luonan.html', wait_until='networkidle')
        ready(page)
        for path in ['downloads/dual-luonan-b7-atlas.pdf', 'dual/luonan-b7-map.png',
                     'downloads/dual-luonan-b7-evidence.csv', 'dual/luonan-b7.json',
                     'downloads/dual-luonan-b7-package.zip']:
            expect(page.locator(f'.downloads a[href="./{path}"]')).to_be_visible()
        downloads = [
            'downloads/dual-luonan-b7-atlas.pdf', 'downloads/dual-luonan-b7-evidence.csv',
            'downloads/dual-luonan-b7-package.zip', 'downloads/luoyang-source-continuity-b7.zip',
            'dual/luonan-b7.json', 'source-continuity/metadata.json',
            'dual/maps/L10.svg', 'dual/maps/L10-archive.svg',
            'dual/maps/LN7-institutions.svg', 'dual/maps/LN7-markets.svg', 'dual/maps/LN7-layers.svg',
            'dual/maps/LN7-evidence-groups.svg', 'dual/maps/LN7-evidence-river.svg',
            'source-continuity/edition-summary.svg', 'source-continuity/continuity-summary.svg',
            'assets/master-dual-b7-luonan.svg', 'dual/luonan-b7-map.png', 'dual/luonan-b7-preview.png',
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
            elif path.endswith('.png'):
                assert content.startswith(b'\x89PNG\r\n\x1a\n'), path
        ok('eighteen actual downloads and diagrams match the published SHA256 manifest')

        assert data['source_commit'] == info['source_commit'] == info['luonan_b7']['source_commit']
        assert continuity['source_commit'] == info['source_commit'] == info['source_continuity_b7']['source_commit']
        assert len(data['evidence']) == info['luonan_b7']['records'] == 25
        assert {record['source_region'] for record in data['evidence']} == {'R11'}
        assert all(record['geographic_coordinates'] is None for record in data['evidence'])
        assert data['source_family_count'] == 1 and data['ancient_absolute_positions_added'] == 0
        assert data['region']['id'] == 'L10' and data['region']['bbox'] == [4100, 8720, 4350, 2230]
        audit = data['drawing_audit']
        assert audit['reading_groups_changed'] == 7 and audit['original_target_count'] == 179
        assert audit['anchors_moved'] is False and audit['bridge_interactive_marker_present'] is False
        assert audit['new_individual_site_glyphs'] == audit['new_interactive_targets'] == audit['new_ancient_coordinates'] == 0
        literary = {record['id']: record for record in data['evidence']}
        assert literary['LR04']['direction_reference_only'] is True and literary['LR04']['altar_footprint'] is None
        assert literary['LR07']['ward_id'] == 'li_guizheng'
        assert literary['LR10']['fish_sitong_identity_established'] is False and literary['LR10']['merge_authorized'] is False
        assert literary['LR11']['main_temporal_state'] == 'undated'
        assert literary['LR14']['lion_alive_in_main_period_allowed'] is False
        assert continuity['named_records'] == 3 and continuity['approved_control_points'] == 0
        assert continuity['review_counts'] == info['source_continuity_b7']['review_counts']
        assert continuity['review_counts']['period_matched_catalog_candidates'] == 1
        assert continuity['review_counts']['earlier_impressions'] == 2
        assert continuity['review_counts']['historical_scans_added'] == 0
        assert continuity['review_counts']['exact_l500_source_matches'] == continuity['review_counts']['exact_l531_source_matches'] == 0
        assert continuity['approved_ground_control_points'] == [] and continuity['source_assets'] == []
        assert continuity['original_horizontal_datum'] is None and continuity['original_geographic_crs'] is None
        assert not continuity['project_registration_to_wgs84'] and not continuity['ground_accuracy_assessed']
        assert not continuity['coordinate_assignment_performed'] and not continuity['modern_dsm_modified']
        assert not continuity['new_historical_image_obtained']
        assert continuity['ancient_geographic_positions_added'] == continuity['ancient_channels_added'] == 0
        assert read_json(context, 'dual/luonan-b7-preservation.json')['protected_unchanged'] is True
        ok('B7 metadata binds the release and preserves unlocated literary records and unconfirmed catalog matches')

        mobile = browser.new_context(viewport={'width': 390, 'height': 844},
                                     is_mobile=True, has_touch=True)
        mobile_page = mobile.new_page()
        mobile_page.on('pageerror', lambda error: errors.append(str(error)))
        mobile_page.goto(base, wait_until='networkidle')
        ready(mobile_page, 'luonanMainReady')
        expect(mobile_page.locator('.feature-target')).to_have_count(179)
        no_overflow(mobile_page)
        mobile_page.goto(base + 'dual-luonan.html#map?id=LR07', wait_until='networkidle')
        ready(mobile_page)
        no_overflow(mobile_page)
        mobile_page.locator('#archive').check()
        mobile_page.reload(wait_until='networkidle')
        ready(mobile_page)
        expect(mobile_page.locator('#archive')).to_be_checked()
        expect(mobile_page.locator('#evidence-picker')).to_have_value('LR07')
        expect(mobile_page.locator('#map')).to_have_attribute('src', './dual/maps/L10-archive.svg')
        image_loaded(mobile_page, '#map')
        for tab in ['institutions', 'markets', 'layers', 'evidence', 'map']:
            mobile_page.locator(f'[data-tab="{tab}"]').tap()
            expect(mobile_page.locator(f'[data-tab="{tab}"]')).to_have_attribute('aria-pressed', 'true')
            no_overflow(mobile_page)
        mobile_page.locator('#evidence-picker').select_option('LR10')
        expect(mobile_page.locator('#detail')).to_contain_text('与鱼鳖巷市保持分记录')
        no_overflow(mobile_page)
        mobile_page.screenshot(path=str(out / 'luonan-mobile.png'), full_page=True)
        ok('390px main map and all literary tabs, archive and evidence controls work without page overflow')

        mobile_page.goto(base + 'source-continuity.html', wait_until='networkidle')
        ready(mobile_page, 'sourceContinuityReady')
        no_overflow(mobile_page)
        mobile_page.locator('#continuity-filter').select_option('earlier')
        mobile_page.locator('#continuity-record').select_option('yanshi-1934')
        mobile_page.locator('#continuity-view').select_option('lineage')
        mobile_page.locator('#continuity-source-toggle').tap()
        expect(mobile_page.locator('#continuity-source-detail')).to_be_visible()
        no_overflow(mobile_page)
        mobile_page.reload(wait_until='networkidle')
        ready(mobile_page, 'sourceContinuityReady')
        expect(mobile_page.locator('#continuity-filter')).to_have_value('earlier')
        expect(mobile_page.locator('#continuity-record')).to_have_value('yanshi-1934')
        expect(mobile_page.locator('#continuity-view')).to_have_value('lineage')
        expect(mobile_page.locator('#continuity-source-toggle')).to_have_attribute('aria-expanded', 'true')
        expect(mobile_page.locator('#continuity-source-detail')).to_be_visible()
        expect(mobile_page.locator('#continuity-reading')).to_contain_text(records['yanshi-1934']['title'])
        no_overflow(mobile_page)
        mobile_page.screenshot(path=str(out / 'source-continuity-mobile.png'), full_page=True)
        ok('390px source-continuity filtering, reading views and expanded details survive reload without overflow')

        assert not errors, errors
        ok('zero browser runtime errors')
        browser.close()
except Exception as error:
    checks.append({'name': 'B7 browser acceptance', 'status': 'failed', 'error': str(error)})
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
