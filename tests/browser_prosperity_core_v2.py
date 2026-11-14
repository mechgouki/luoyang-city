#!/usr/bin/env python3
"""Exercise the real core-scale drawings, source evidence and responsive controls."""
import argparse
import functools
import http.server
import json
import os
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlencode, urlparse

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--base-url')
parser.add_argument('--output', default='artifacts/prosperity-core-v2-browser')
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


def ready(target, mode=None):
    target.wait_for_function(
        'document.documentElement.dataset.coreReady === "true"', timeout=45000)
    if mode:
        expect(target.locator('#map-viewport')).to_have_attribute('data-mode', mode)


def no_overflow(target):
    assert target.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')


def parameters(target):
    return target.evaluate('Object.fromEntries(new URLSearchParams(location.hash.slice(1)))')


def view_box(target):
    return [float(value) for value in target.locator('#map-viewport > svg').get_attribute('viewBox').split()]


def expect_notes(target, item):
    expect(target.locator('#item-detail h2')).to_have_text(item['name'])
    expect(target.locator('.measure-value')).to_have_text(item['dimensions_label'])
    for field in ['position_note', 'orientation_note', 'height_note']:
        value = item[field]
        for text in value if isinstance(value, list) else [value]:
            expect(target.locator('#item-detail')).to_contain_text(text)


try:
    with sync_playwright() as pw:
        options = {'headless': True}
        if os.environ.get('CHROMIUM_PATH'):
            options['executable_path'] = os.environ['CHROMIUM_PATH']
        browser = pw.chromium.launch(**options)
        context = browser.new_context(viewport={'width':1500, 'height':1000})
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        response = context.request.get(base + 'prosperity-core/data.json')
        assert response.status == 200
        data = response.json()
        assert data['version'] == 'prosperity-core-v2'
        items = {item['id']:item for item in data['items']}
        focuses = {focus['id']:focus for focus in data['focuses']}
        assert set(items) == {'core-changhe', 'core-taiji', 'core-yongning-tower'}
        assert set(focuses) == {'all', 'palace', 'yongning'}
        assert set(data['maps']) == {'plan', 'oblique'}

        response = page.goto(base + 'prosperity-core.html', wait_until='networkidle')
        assert response.status == 200
        ready(page, 'plan')
        expect(page.locator('h1')).to_have_text(data['title'])
        expect(page.locator('#period-label')).to_have_text(data['period'])
        expect(page.locator('#mode-switch button:visible')).to_have_count(2)
        expect(page.locator('#focus-switch button')).to_have_count(3)
        expect(page.locator('#item-switch button')).to_have_count(3)
        expect(page.locator('#version-status')).to_have_attribute('data-verified', 'true')
        expect(page.locator('#version-status')).to_have_text('本页与正式发布一致')
        expect(page.locator('#map-viewport [role="button"]')).to_have_count(3)
        expect(page.locator('#map-viewport g[data-core-id][tabindex="0"]')).to_have_count(3)
        assert set(page.locator('#map-viewport [role="button"]').evaluate_all('nodes => nodes.map(n => n.getAttribute("data-core-id"))')) == set(items)
        assert view_box(page) == focuses['all']['boxes']['plan']
        assert parameters(page) == {'mode':'plan', 'item':data['items'][0]['id'], 'focus':'all'}
        no_overflow(page)
        page.screenshot(path=str(out / 'core-desktop-first-screen.png'))
        ok('the core-scale page loads real data, three formal keyboard targets and a matching public build')

        original = view_box(page)
        page.locator('#zoom-in').click()
        assert view_box(page) != original
        zoomed = view_box(page)
        viewport = page.locator('#map-viewport').bounding_box()
        page.mouse.move(viewport['x'] + viewport['width'] * .6, viewport['y'] + viewport['height'] * .5)
        page.mouse.down()
        page.mouse.move(viewport['x'] + viewport['width'] * .69, viewport['y'] + viewport['height'] * .57, steps=8)
        page.mouse.up()
        assert view_box(page) != zoomed
        page.locator('#reset-map').click()
        assert view_box(page) == original
        ok('the real map zooms, drags and restores the selected regional view')

        for ident in ['core-taiji', 'core-changhe', 'core-yongning-tower']:
            target = page.locator('#map-viewport g[data-core-id="'+ident+'"]')
            target.focus()
            target.press('Enter')
            ready(page, 'plan')
            assert parameters(page)['item'] == ident
            expect_notes(page, items[ident])
            expect(target).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('#map-viewport .core-selected')).to_have_count(1)
        ok('each scale fragment is keyboard-selectable and opens its actual dimension, position, orientation and height notes')

        page.locator('#focus-item').click()
        assert view_box(page) != original
        page.locator('[data-item="core-changhe"]').click()
        ready(page)
        hit = page.locator('#map-viewport g[data-core-id="core-yongning-tower"] [data-role="interaction_only"]')
        expect(hit).to_have_count(1)
        hit.click()
        ready(page)
        assert parameters(page)['item'] == 'core-yongning-tower'
        expect_notes(page, items['core-yongning-tower'])
        page.locator('#reset-map').click()
        assert view_box(page) == original
        ok('ordinary pointer clicks on a real drawing hit zone select the building without forced events')

        for ident in ['palace', 'yongning', 'all']:
            page.locator('[data-focus="'+ident+'"]').click()
            ready(page, 'plan')
            assert parameters(page)['focus'] == ident
            assert view_box(page) == focuses[ident]['boxes']['plan']
        page.locator('[data-focus="palace"]').click()
        ready(page, 'plan')
        page.locator('#zoom-in').click()
        palace_plan_box = view_box(page)
        page.locator('[data-mode="oblique"]').click()
        ready(page, 'oblique')
        assert view_box(page) == focuses['palace']['boxes']['oblique']
        expect(page.locator('#map-title')).to_have_text(data['maps']['oblique']['title'])
        expect(page.locator('#map-viewport [role="button"]')).to_have_count(3)
        assert page.locator('#map-viewport').get_attribute('data-map') == data['maps']['oblique']['url']
        page.locator('#zoom-in').click()
        palace_oblique_box = view_box(page)
        page.locator('[data-mode="plan"]').click()
        ready(page, 'plan')
        assert view_box(page) == palace_plan_box
        page.locator('[data-mode="oblique"]').click()
        ready(page, 'oblique')
        assert view_box(page) == palace_oblique_box
        page.locator('[data-item="core-taiji"]').click()
        ready(page, 'oblique')
        page.screenshot(path=str(out / 'core-oblique.png'))
        ok('regional focus uses the supplied bounds and planar and oblique drawings retain their separate cameras')

        linked = {'mode':'oblique', 'item':'core-yongning-tower', 'focus':'yongning'}
        page.goto(base + 'prosperity-core.html#' + urlencode(linked), wait_until='networkidle')
        ready(page, 'oblique')
        assert parameters(page) == linked
        assert view_box(page) == focuses['yongning']['boxes']['oblique']
        expect_notes(page, items[linked['item']])
        page.reload(wait_until='networkidle')
        ready(page, 'oblique')
        assert parameters(page) == linked
        page.locator('[data-mode="plan"]').click()
        ready(page, 'plan')
        page.go_back()
        ready(page, 'oblique')
        assert parameters(page) == linked
        ok('mode, selected building and regional focus survive a deep-link reload and browser back')

        for fragment in ['mode=&item=&focus=', 'mode=unknown&item=unknown&focus=unknown']:
            page.goto(base + 'prosperity-core.html#' + fragment, wait_until='networkidle')
            ready(page, 'plan')
            assert parameters(page) == {'mode':'plan', 'item':data['items'][0]['id'], 'focus':'all'}
            expect_notes(page, data['items'][0])
            assert view_box(page) == focuses['all']['boxes']['plan']
        ok('empty or unknown URL parameters return to a valid overview and existing building')

        with page.expect_popup() as popup_info:
            page.locator('#open-map').click()
        popup = popup_info.value
        popup.wait_for_load_state()
        assert popup.url == page.locator('#open-map').get_attribute('href')
        popup.close()
        page.locator('#sources-link').click()
        expect(page.locator('#source-catalog')).to_have_attribute('open', '')
        assert data['sources'] and data['downloads']
        expect(page.locator('#source-list .source-card')).to_have_count(len(data['sources']))
        expect(page.locator('#download-links a')).to_have_count(len(data['downloads']))
        for href in page.locator('#source-list a, #download-links a, #item-detail .item-links a').evaluate_all('links => links.map(a => a.href)'):
            parsed = urlparse(href)
            assert parsed.scheme in ('http', 'https') and parsed.netloc
        ok('the current SVG opens and the original sources and downloadable artifacts have valid links')

        assert len(data['figures']) >= 2
        page.locator('#figures-link').click()
        expect(page.locator('#figure-list .figure-card')).to_have_count(len(data['figures']))
        expect(page.locator('.detail-figure img')).to_have_count(1)
        page.wait_for_function('''() => [...document.querySelectorAll('#figure-list img, .detail-figure img')].every(image => image.complete && image.naturalWidth > 0)''')
        expect(page.locator('#figures .section-heading')).to_contain_text('不作测绘平面使用')
        for figure in data['figures']:
            card = page.locator('[data-figure="'+figure['id']+'"]')
            expect(card.locator('h3')).to_have_text(figure['title'])
            if figure.get('caption'):
                expect(card.locator('figcaption')).to_contain_text(figure['caption'])
        with page.expect_popup() as popup_info:
            page.locator('#figure-list .figure-card > a').first.click()
        popup = popup_info.value
        popup.wait_for_load_state()
        assert popup.url == page.locator('#figure-list .figure-card > a').first.get_attribute('href')
        popup.close()
        no_overflow(page)
        page.screenshot(path=str(out / 'core-figures-and-sources.png'), full_page=True)
        ok('the actual scale comparison and local relationship drawings load with their explanatory captions')

        tablet_context = browser.new_context(viewport={'width':900, 'height':1000})
        tablet = tablet_context.new_page()
        tablet.on('pageerror', lambda error: errors.append(str(error)))
        tablet.goto(base + 'prosperity-core.html', wait_until='networkidle')
        ready(tablet, 'plan')
        no_overflow(tablet)
        header = tablet.locator('.site-header').bounding_box()
        assert header['y'] + header['height'] <= tablet.locator('.introduction').bounding_box()['y']
        tablet.locator('[data-focus="palace"]').click()
        ready(tablet, 'plan')
        assert view_box(tablet) == focuses['palace']['boxes']['plan']
        tablet.screenshot(path=str(out / 'core-tablet.png'))
        ok('the 900px layout keeps the map, selection controls and evidence within the page')

        mobile_context = browser.new_context(viewport={'width':390, 'height':844}, is_mobile=True, has_touch=True, device_scale_factor=1)
        mobile = mobile_context.new_page()
        mobile.on('pageerror', lambda error: errors.append(str(error)))
        mobile.goto(base + 'prosperity-core.html', wait_until='networkidle')
        ready(mobile, 'plan')
        no_overflow(mobile)
        mobile.screenshot(path=str(out / 'core-mobile-first-screen.png'))
        mobile.locator('[data-focus="yongning"]').tap()
        ready(mobile, 'plan')
        mobile.locator('[data-mode="oblique"]').tap()
        ready(mobile, 'oblique')
        mobile.locator('[data-item="core-yongning-tower"]').tap()
        ready(mobile, 'oblique')
        expect_notes(mobile, items['core-yongning-tower'])
        assert parameters(mobile) == linked
        before = view_box(mobile)
        mobile.locator('#zoom-in').tap()
        assert view_box(mobile) != before
        mobile.locator('#reset-map').tap()
        assert view_box(mobile) == focuses['yongning']['boxes']['oblique']
        mobile.reload(wait_until='networkidle')
        ready(mobile, 'oblique')
        assert parameters(mobile) == linked
        mobile.locator('#sources-link').tap()
        expect(mobile.locator('#source-catalog')).to_have_attribute('open', '')
        no_overflow(mobile)
        mobile.screenshot(path=str(out / 'core-mobile.png'), full_page=True)
        ok('390px touch controls, focus, selected evidence and reload work without horizontal overflow')

        assert not errors, errors
        ok('zero JavaScript runtime errors throughout the core-scale journeys')
        browser.close()
except Exception as error:
    checks.append({'name':'core-scale browser acceptance', 'status':'failed', 'error':str(error)})
    if page:
        try:
            page.screenshot(path=str(out / 'failure.png'), full_page=True)
        except Exception:
            pass
    raise
finally:
    (out / 'results.json').write_text(json.dumps({'base_url':base, 'checks':checks, 'runtime_errors':errors}, ensure_ascii=False, indent=2))
    if server:
        server.shutdown()
    if temporary:
        temporary.cleanup()
