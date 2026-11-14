#!/usr/bin/env python3
"""Exercise the public homepage journey, with the existing maps behind it."""
import argparse
import functools
import http.server
import json
import os
import re
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--base-url')
parser.add_argument('--output', default='artifacts/homepage-v1-browser')
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


def ready(target, dataset='homepageReady'):
    target.wait_for_function(
        '(key) => document.documentElement.dataset[key] === "true"',
        arg=dataset, timeout=45000)


def no_overflow(target):
    assert target.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')


def hero_loaded(target):
    target.wait_for_function('''() => {
        const image = document.querySelector('#home-hero img');
        return image && image.complete && image.naturalWidth >= 640;
    }''')
    expect(target.locator('#home-hero img')).to_have_attribute('alt', re.compile(r'.+'))


try:
    with sync_playwright() as pw:
        options = {'headless': True}
        if os.environ.get('CHROMIUM_PATH'):
            options['executable_path'] = os.environ['CHROMIUM_PATH']
        browser = pw.chromium.launch(**options)
        context = browser.new_context(viewport={'width': 1500, 'height': 1000})
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))

        response = page.goto(base, wait_until='networkidle')
        assert response.status == 200
        ready(page)
        ready(page, 'cityMainReady')
        hero_loaded(page)
        expect(page.locator('#home-hero')).to_be_visible()
        expect(page.locator('#home-hero')).to_contain_text('研究性复原示意')
        expect(page.locator('#home-start')).to_contain_text('开始探索')
        expect(page.locator('#home-questions a[data-question]')).to_have_count(3)
        assert page.evaluate('''() => {
            const selectors = ['#home-hero', '#home-questions', '#map-viewport', '#home-research'];
            const positions = selectors.map(s => document.querySelector(s).getBoundingClientRect().top);
            return positions.every((value, index) => index === 0 || value > positions[index - 1]);
        }'''), 'Expected city, questions, working map, then research'
        assert page.locator('#home-hero img').evaluate('image => image.getBoundingClientRect().width >= innerWidth * .75')
        no_overflow(page)
        page.screenshot(path=str(out / 'homepage-desktop-first-screen.png'))
        page.screenshot(path=str(out / 'homepage-desktop.png'), full_page=True)
        ok('desktop homepage presents the large panorama, three questions, live map and research in order')

        page.locator('#home-start').click()
        page.wait_for_function('location.hash === "#map"')
        expect(page.locator('#home-hero')).to_be_hidden()
        expect(page.locator('#map-viewport')).to_be_in_viewport()
        expect(page.locator('.feature-target')).to_have_count(179)
        before_zoom = page.locator('#map-viewport > svg').get_attribute('viewBox')
        page.locator('#zoom-in').click()
        expect(page.locator('#map-viewport > svg')).not_to_have_attribute('viewBox', before_zoom)
        page.locator('#home-map').click()
        page.locator('.region-btn[data-code="R07"]').click()
        expect(page.locator('#map-status')).to_contain_text('R07')
        page.locator('#place-search').fill('永宁')
        page.locator('.search-item').first.click()
        expect(page.locator('.inspector-name')).to_have_text('永宁寺')
        page.reload(wait_until='networkidle')
        ready(page)
        expect(page.locator('#home-hero')).to_be_hidden()
        expect(page.locator('.inspector-name')).to_have_text('永宁寺')
        ok('start exploration reaches the actual map; zoom, region, search and shared entity reload work')

        page.goto(base + '#home', wait_until='networkidle')
        ready(page)
        expect(page.locator('#home-hero')).to_be_visible()
        page.locator('#home-research').scroll_into_view_if_needed()
        expect(page.locator('#home-research #city-b8-entry')).to_be_visible()
        expect(page.locator('#home-research #dual-release-entry')).to_be_visible()
        page.locator('#b8-review-toggle').uncheck()
        expect(page.locator('#map-viewport #city-audit-overlay-b8')).to_be_hidden()
        page.locator('#b8-review-toggle').check()
        expect(page.locator('#map-viewport #city-audit-overlay-b8')).to_be_visible()
        ok('the relocated research area keeps B1-B8 access and the working map overlay control')

        # These assertions follow actual question links to already published evidence.
        for question in ['yongning', 'markets', 'identity']:
            page.goto(base + '#home', wait_until='networkidle')
            ready(page)
            page.locator(f'#home-questions a[data-question="{question}"]').click()
            if question == 'yongning':
                ready(page, 'dualReady')
                expect(page.locator('#entity-picker')).to_have_value('ic_yongning')
                expect(page.locator('#inspector-title')).to_contain_text('永宁')
            elif question == 'markets':
                ready(page, 'luonanB7Ready')
                expect(page.locator('#evidence-picker')).to_have_value('LR10')
                expect(page.locator('#detail')).to_contain_text('四通市')
                expect(page.locator('#detail')).to_contain_text('归正里')
                expect(page.locator('#detail')).to_contain_text('鱼')
                expect(page.locator('[data-tab="markets"]')).to_have_attribute('aria-pressed', 'true')
            else:
                ready(page, 'cityReviewReady')
                expect(page.locator('[data-view="cases"]')).to_have_attribute('aria-pressed', 'true')
                expect(page.locator('#case-detail')).to_contain_text('同名')
                assert page.evaluate('new URLSearchParams(location.hash.slice(1)).get("case")') == 'CB01'
            page.reload(wait_until='networkidle')
            ready(page, {'yongning': 'dualReady', 'markets': 'luonanB7Ready', 'identity': 'cityReviewReady'}[question])
            no_overflow(page)
            page.go_back(wait_until='networkidle')
            ready(page)
            expect(page.locator('#home-hero')).to_be_visible()
            ok(f'{question} question opens the intended evidence, survives reload and returns to the homepage')

        page.goto(base + '#research?panel=B&evidence=E07', wait_until='networkidle')
        ready(page)
        ready(page, 'researchReady')
        expect(page.locator('#home-hero')).to_be_hidden()
        expect(page.locator('#evidence-E07')).to_have_class('r-card r-selected')
        page.goto(base + '#about', wait_until='networkidle')
        ready(page)
        expect(page.locator('#page-about')).to_be_visible()
        expect(page.locator('#home-hero')).to_be_hidden()
        page.goto(base + 'v3.0-dual.html#home', wait_until='networkidle')
        ready(page)
        hero_loaded(page)
        expect(page.locator('#home-hero')).to_be_visible()
        ok('existing research and about routes stay direct; the current release URL has the same homepage')

        tablet = browser.new_context(viewport={'width': 900, 'height': 1000})
        tablet_page = tablet.new_page()
        tablet_page.on('pageerror', lambda error: errors.append(str(error)))
        tablet_page.goto(base, wait_until='networkidle')
        ready(tablet_page)
        hero_loaded(tablet_page)
        no_overflow(tablet_page)
        assert tablet_page.evaluate('''() => {
            const header = document.querySelector('.masthead').getBoundingClientRect();
            const navigation = document.querySelector('.masthead .topnav').getBoundingClientRect();
            const hero = document.querySelector('#home-hero').getBoundingClientRect();
            return navigation.bottom <= header.bottom + 2 && header.bottom <= hero.top + 2;
        }'''), 'The wrapped navigation must stay inside the header and above the panorama'
        tablet_page.screenshot(path=str(out / 'homepage-tablet-first-screen.png'))
        tablet.close()
        ok('900px wrapped navigation stays above the panorama without overlap or horizontal overflow')

        mobile = browser.new_context(viewport={'width': 390, 'height': 844},
                                     is_mobile=True, has_touch=True, device_scale_factor=1)
        mobile_page = mobile.new_page()
        mobile_page.on('pageerror', lambda error: errors.append(str(error)))
        mobile_page.goto(base, wait_until='networkidle')
        ready(mobile_page)
        ready(mobile_page, 'cityMainReady')
        hero_loaded(mobile_page)
        no_overflow(mobile_page)
        expect(mobile_page.locator('#home-questions a[data-question]')).to_have_count(3)
        mobile_page.screenshot(path=str(out / 'homepage-mobile-first-screen.png'))
        mobile_page.screenshot(path=str(out / 'homepage-mobile.png'), full_page=True)
        mobile_page.locator('#home-start').tap()
        expect(mobile_page.locator('#home-hero')).to_be_hidden()
        expect(mobile_page.locator('#map-viewport')).to_be_in_viewport()
        mobile_page.locator('#filter-toggle').tap()
        mobile_page.locator('.region-btn[data-code="R11"]').tap()
        expect(mobile_page.locator('#map-status')).to_contain_text('R11')
        no_overflow(mobile_page)
        mobile_page.goto(base + '#home', wait_until='networkidle')
        ready(mobile_page)
        mobile_page.locator('#home-questions a[data-question="markets"]').tap()
        ready(mobile_page, 'luonanB7Ready')
        expect(mobile_page.locator('#evidence-picker')).to_have_value('LR10')
        no_overflow(mobile_page)
        mobile_page.go_back(wait_until='networkidle')
        ready(mobile_page)
        expect(mobile_page.locator('#home-hero')).to_be_visible()
        no_overflow(mobile_page)
        ok('390px homepage, tap-to-map, regional filters and question navigation work without page overflow')

        assert not errors, errors
        ok('zero browser runtime errors during the homepage journeys')
        browser.close()
except Exception as error:
    checks.append({'name': 'homepage browser acceptance', 'status': 'failed', 'error': str(error)})
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
