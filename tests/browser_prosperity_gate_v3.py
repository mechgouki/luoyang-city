#!/usr/bin/env python3
"""Exercise the published gate drawings, deep links, mobile use, and static fallback."""
import argparse
import functools
import http.server
import json
import os
from pathlib import Path
import tempfile
import threading
from urllib.parse import urlencode

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--base-url')
parser.add_argument('--output', default='artifacts/prosperity-gate-v3-browser')
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
        def log_message(self, *unused):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=server_root))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/luoyang-city/'


def ok(name):
    checks.append({'name': name, 'status': 'passed'})
    print('PASS', name, flush=True)


def ready(target, view='local'):
    target.wait_for_function('document.documentElement.dataset.gateReady === "true"', timeout=45000)
    expect(target.locator('#map-viewport')).to_have_attribute('data-view', view)


def parameters(target):
    return target.evaluate('Object.fromEntries(new URLSearchParams(location.hash.slice(1)))')


def view_box(target):
    return [float(value) for value in target.locator('#map-viewport > svg').get_attribute('viewBox').split()]


def no_overflow(target):
    assert target.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')


def assert_component(target, component):
    expect(target.locator('#component-select')).to_have_value(component['id'])
    expect(target.locator('#component-detail h2')).to_have_text(component['label'])
    expect(target.locator('.measure-value')).to_have_text(component['dimensions_label'])
    expect(target.locator('#component-detail')).to_contain_text(component['note'])
    for source in component['source_links']:
        expect(target.locator('#component-detail a').filter(has_text=source['label']).first()).to_have_attribute('href', source['url'])
    assert parameters(target)['component'] == component['id']


try:
    with sync_playwright() as pw:
        options = {'headless': True}
        if os.environ.get('CHROMIUM_PATH'):
            options['executable_path'] = os.environ['CHROMIUM_PATH']
        browser = pw.chromium.launch(**options)
        context = browser.new_context(viewport={'width': 1500, 'height': 1000})
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        response = context.request.get(base + 'prosperity-gate/data.json')
        assert response.status == 200
        data = response.json()
        assert data['version'] == 'prosperity-gate-v3'
        assert data['city_link']['registration_verified'] is False
        assert set(data['maps']) == {'local', 'city', 'diagnostics'}
        components = {item['id']: item for item in data['components']}
        main = components[data['default_component']]
        passage = next(item for item in components.values() if item['kind'] == 'passage')
        que = next(item for item in components.values() if item['kind'] == 'que_base')

        response = page.goto(base + 'prosperity-gate.html#' + urlencode({'view': 'local', 'component': main['id'], 'source': '1'}), wait_until='networkidle')
        assert response.status == 200
        ready(page)
        expect(page.locator('#version-status')).to_have_attribute('data-verified', 'true')
        assert_component(page, main)
        no_overflow(page)
        workspace = page.locator('#gate-workspace').bounding_box()
        map_bounds = page.locator('#map-viewport').bounding_box()
        assert map_bounds['width'] > workspace['width'] * .65
        assert map_bounds['height'] >= 500
        expect(page.locator('#source-toggle')).to_be_checked()
        expect(page.locator('#source-layer')).to_be_visible()
        page.screenshot(path=str(out / 'desktop-local.png'), full_page=True)
        ok('desktop source-backed plan occupies the main workspace and verifies its release')

        target = page.locator(f'#map-viewport [data-component-id="{passage["id"]}"]').first()
        target.focus()
        page.keyboard.press('Enter')
        assert_component(page, passage)
        expect(target).to_have_attribute('aria-pressed', 'true')
        page.locator('#component-select').select_option(que['id'])
        assert_component(page, que)
        ok('keyboard map selection and native component selector expose the actual source notes')

        original = view_box(page)
        page.locator('#zoom-in').click()
        assert view_box(page)[2] < original[2]
        page.locator('#map-viewport').focus()
        page.keyboard.press('Home')
        assert view_box(page) == original
        page.keyboard.press('=')
        assert view_box(page)[2] < original[2]
        map_bounds = page.locator('#map-viewport').bounding_box()
        before_drag = view_box(page)
        page.mouse.move(map_bounds['x'] + 80, map_bounds['y'] + 90)
        page.mouse.down()
        page.mouse.move(map_bounds['x'] + 150, map_bounds['y'] + 140, steps=6)
        page.mouse.up()
        assert view_box(page)[:2] != before_drag[:2]
        page.locator('#reset-map').click()
        assert view_box(page) == original
        page.locator('#component-select').select_option(passage['id'])
        page.locator('#focus-component').click()
        assert view_box(page)[2] < original[2]
        page.locator('#reset-map').click()
        ok('zoom, keyboard camera controls, drag, reset, and component framing work')

        page.locator('#source-toggle').uncheck()
        expect(page.locator('#source-layer')).to_be_hidden()
        assert parameters(page)['source'] == '0'
        page.locator('[data-view="city"]').click()
        ready(page, 'city')
        assert_component(page, passage)
        expect(page.locator('#view-note')).to_contain_text('尚未核定')
        page.locator('#gate-workspace').screenshot(path=str(out / 'desktop-city.png'))
        page.locator('[data-view="diagnostics"]').click()
        ready(page, 'diagnostics')
        assert_component(page, passage)
        page.locator('#gate-workspace').screenshot(path=str(out / 'desktop-diagnostics.png'))
        deep_link = page.url
        page.reload(wait_until='networkidle')
        ready(page, 'diagnostics')
        assert_component(page, passage)
        assert parameters(page) == {'view': 'diagnostics', 'component': passage['id'], 'source': '0'}
        page.locator('[data-view="local"]').click()
        ready(page)
        expect(page.locator('#source-layer')).to_be_hidden()
        page.go_back(wait_until='networkidle')
        ready(page, 'diagnostics')
        assert page.url == deep_link
        ok('three views, original-layer state, reload, and browser history retain deep-link selection')

        page.locator('#copy-link').click()
        expect(page.locator('#share-status')).to_contain_text('链接')
        if page.locator('#share-url').is_visible():
            expect(page.locator('#share-url')).to_have_value(page.url)
        page.goto(base + 'prosperity-gate.html#' + urlencode({'view': 'unknown', 'component': '<script>alert(1)</script>', 'source': 'bad'}), wait_until='networkidle')
        ready(page)
        assert parameters(page) == {'view': 'local', 'component': main['id'], 'source': '1'}
        assert_component(page, main)
        page.locator('#component-detail a[href="#source-comparison"]').click()
        expect(page.locator('#source-comparison')).to_be_in_viewport()
        expect(page.locator('#map-viewport')).to_have_attribute('data-view', 'local')
        ok('share URL fallback, unknown-state normalization, and in-page original comparison work')

        for item in data['downloads']:
            response = context.request.get(base + item['url'].removeprefix('./'))
            assert response.status == 200, item['url']
            body = response.body()
            assert len(body) > 40
            if item['type'] == 'pdf':
                assert body.startswith(b'%PDF-')
            elif item['type'] == 'zip':
                assert body.startswith(b'PK')
        response = context.request.get(base + data['source_raster']['url'].removeprefix('./'))
        assert response.status == 200 and len(response.body()) > 1000
        ok('every advertised SVG, source raster, PDF, ZIP, CSV, JSON, and method download resolves')

        mobile = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        mobile_page = mobile.new_page()
        mobile_page.on('pageerror', lambda error: errors.append(str(error)))
        mobile_page.goto(base + 'prosperity-gate.html', wait_until='networkidle')
        ready(mobile_page)
        no_overflow(mobile_page)
        assert mobile_page.locator('#map-viewport').bounding_box()['height'] >= 330
        mobile_page.locator('#component-select').select_option(que['id'])
        assert_component(mobile_page, que)
        mobile_page.locator('[data-view="city"]').click()
        ready(mobile_page, 'city')
        no_overflow(mobile_page)
        mobile_page.locator('[data-view="local"]').click()
        ready(mobile_page)
        mobile_page.locator('#source-toggle').uncheck()
        expect(mobile_page.locator('#source-layer')).to_be_hidden()
        no_overflow(mobile_page)
        mobile_page.screenshot(path=str(out / 'mobile-local.png'), full_page=True)
        mobile_page.locator('#download-links').scroll_into_view_if_needed()
        expect(mobile_page.locator('#download-links a').first()).to_be_visible()
        mobile.close()
        ok('mobile layout has no overflow and keeps view, source, component, and download controls usable')

        no_script = browser.new_context(viewport={'width': 390, 'height': 844}, java_script_enabled=False)
        fallback = no_script.new_page()
        fallback.goto(base + 'prosperity-gate.html', wait_until='networkidle')
        expect(fallback.locator('.fallback-map')).to_be_visible()
        assert fallback.locator('.fallback-map').evaluate('(image) => image.complete && image.naturalWidth > 0')
        expect(fallback.locator('.fallback-note')).to_contain_text('局部平面')
        expect(fallback.locator('#component-detail')).to_contain_text(main['note'])
        assert fallback.locator('#download-links a').count() == len(data['downloads'])
        no_overflow(fallback)
        fallback.screenshot(path=str(out / 'no-javascript.png'), full_page=True)
        no_script.close()
        ok('without JavaScript the static plan, initial evidence, original, and complete download list remain')

        failed = browser.new_context(viewport={'width': 1000, 'height': 800})
        failure_page = failed.new_page()
        failure_page.route('**/prosperity-gate/data.json', lambda route: route.abort())
        failure_page.goto(base + 'prosperity-gate.html', wait_until='networkidle')
        expect(failure_page.locator('.error-message')).to_contain_text('静态图件')
        expect(failure_page.locator('.fallback-map')).to_be_visible()
        assert failure_page.locator('#download-links a').count() == len(data['downloads'])
        failed.close()
        ok('a failed data request preserves static reading and direct downloads')

        assert not errors, errors
        context.close()
        browser.close()
except Exception as error:
    errors.append(str(error))
    if page:
        try:
            page.screenshot(path=str(out / 'failure.png'), full_page=True)
        except Exception:
            pass
    raise
finally:
    (out / 'report.json').write_text(json.dumps({'checks': checks, 'errors': errors, 'base_url': base}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if server:
        server.shutdown()
    if temporary:
        temporary.cleanup()
