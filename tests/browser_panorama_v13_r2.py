"""Exercise all three images, same-scale details, source anchors and real downloads."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from browser_city_west_p472 import SIZES, base_url
from browser_layout import assert_loaded_viewport

ROOT = Path(__file__).resolve().parents[1]
PAGE = 'luoyang-panorama-v13-r2.html'
KEY = 'panorama_review_v13_r2'


def exercise(browser, base, device, output, expected_commit=None):
    settings = dict(viewport=SIZES[device], is_mobile=device == 'mobile', has_touch=device == 'mobile', reduced_motion='reduce')
    report = dict(device=device, viewport=SIZES[device], checks=[], downloads={}, screenshots={}, image_dimensions=[], detail_views=[], errors=[])

    def capture(page, label):
        name = device + '-' + label + '.png'
        raw = page.screenshot(path=output / name, animations='disabled', full_page=True)
        report['screenshots'][name] = hashlib.sha256(raw).hexdigest()

    with browser.new_context(**settings, accept_downloads=True) as context:
        page = context.new_page()
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        try:
            info = context.request.get(base + 'build-info.json').json()
            meta = info[KEY]
            report['source_commit'] = info['source_commit']
            assert meta['source_commit'] == info['source_commit']
            if expected_commit:
                assert info['source_commit'] == expected_commit
            assert meta['homepage_replacement_approved'] is False
            for home in ('index.html', 'v3.0-dual.html'):
                page.goto(base + home, wait_until='load')
                expect(page.locator('[data-hero-revision="panorama-approved-v12"]')).to_be_visible()
                expect(page.locator('#r9-spatial-entry')).to_have_attribute('href', './luoyang-city-spatial.html')
                expect(page.locator('#r8-panorama-entry')).to_have_count(1)
                page.locator('#r9-panorama-entry').click()
                page.wait_for_url('**/' + PAGE, wait_until='load')
                expect(page.locator('#review-status')).to_contain_text('待审看')
                expect(page.locator('#figure-v13r2')).to_be_visible()
                expect(page.locator('#figure-v13')).to_be_hidden()
                expect(page.locator('#figure-v12')).to_be_hidden()
                assert_loaded_viewport(page, tolerance=1, report=report)
            report['checks'].append('Both homepages preserve V12 and old V13 while linking the spatial overview and new unapproved candidate')

            for kind in ('v13r2', 'v13', 'v12'):
                page.locator(f'button[data-view="{kind}"]').click()
                figure = page.locator('#figure-' + kind)
                expect(figure).to_be_visible()
                image = figure.locator('img')
                page.wait_for_function('selector => { const image = document.querySelector(selector); return image.complete && image.naturalWidth > 0; }', arg='#figure-' + kind + ' img')
                size = image.evaluate('el => ({width:el.naturalWidth,height:el.naturalHeight,box:el.getBoundingClientRect().toJSON(),fit:getComputedStyle(el).objectFit,current:el.currentSrc})')
                expected = meta['images'][kind]
                prefix = 'small_' if device == 'mobile' else ''
                assert (size['width'], size['height']) == (expected[prefix + 'width'], expected[prefix + 'height'])
                assert abs(size['box']['width'] / size['box']['height'] - size['width'] / size['height']) < .01
                assert size['fit'] == 'contain'
                report['image_dimensions'].append(dict(version=kind, **size))
                page.reload(wait_until='load')
                expect(page.locator(f'button[data-view="{kind}"]')).to_have_attribute('aria-pressed', 'true')
                assert_loaded_viewport(page, tolerance=1, report=report)
            page.locator('button[data-view="compare"]').focus()
            page.keyboard.press('Enter')
            expect(page.locator('#figure-v13r2')).to_be_visible()
            expect(page.locator('#figure-v13')).to_be_visible()
            expect(page.locator('#figure-v12')).to_be_hidden()
            page.reload(wait_until='load')
            expect(page.locator('button[data-view="compare"]')).to_have_attribute('aria-pressed', 'true')
            assert_loaded_viewport(page, tolerance=1, report=report)
            capture(page, 'comparison')
            report['checks'].append('Three full-frame modes, keyboard before/after comparison and URL-restored modes work at natural proportions')

            record = context.request.get(base + meta['record']).json()
            detail = record['candidate']['detail_view']
            page.goto(base + PAGE + '?view=compare#gate-detail', wait_until='load')
            scales = []
            for kind in ('v13r2', 'v13'):
                svg = page.locator('#detail-' + kind + ' svg')
                expect(svg).to_be_visible()
                state = svg.evaluate('el => ({viewBox:el.getAttribute("viewBox"),box:el.getBoundingClientRect().toJSON(),href:el.querySelector("image").getAttribute("href"),width:el.querySelector("image").getAttribute("width"),height:el.querySelector("image").getAttribute("height")})')
                pos, im = detail['views'][kind], meta['images'][kind]
                assert state['viewBox'] == f"{pos['x']} {pos['y']} {detail['width']} {detail['height']}"
                assert state['href'] == './' + im['full']
                assert (int(state['width']), int(state['height'])) == (im['width'], im['height'])
                assert abs(state['box']['width'] / state['box']['height'] - detail['width'] / detail['height']) < .01
                scales.append(state['box']['width'] / detail['width'])
                report['detail_views'].append(dict(version=kind, **state))
            assert abs(scales[0] - scales[1]) < .005, 'Gate views have unequal source-pixel magnification'
            assert_loaded_viewport(page, tolerance=1, report=report)
            report['checks'].append('Both gate details reference the original full images at identical source-pixel magnification')

            page.locator('a[href="./luoyang-city-spatial.html#decision-SP02"]').first.click()
            page.wait_for_url('**/luoyang-city-spatial.html#decision-SP02', wait_until='load')
            expect(page.locator('#decision-SP02')).to_have_count(1)
            first = record['candidate']['changes'][0]['id']
            page.goto(base + PAGE + '?view=compare#change-' + first, wait_until='load')
            expect(page.locator('.change-card')).to_have_count(meta['change_count'])
            expect(page.locator('#change-' + first)).to_be_in_viewport()
            page.locator('#change-' + first + ' .back-to-image').click()
            assert page.evaluate('location.hash') == '#comparison'
            report['checks'].append('Spatial-decision links, shareable change anchors and return-to-image navigation work')

            for path in meta['download_files']:
                with page.expect_download() as event:
                    page.locator(f'[download][href="./{path}"]').click()
                raw = Path(event.value.path()).read_bytes()
                checksum = hashlib.sha256(raw).hexdigest()
                assert checksum == info['files_sha256'][path], path
                report['downloads'][path] = checksum
            report['checks'].append('Every actual candidate, audit and manifest download matches released bytes')
            with browser.new_context(**settings, java_script_enabled=False) as disabled:
                plain = disabled.new_page()
                plain.on('pageerror', lambda error: report['errors'].append(str(error)))
                plain.goto(base + PAGE, wait_until='load')
                for kind in ('v13r2', 'v13', 'v12'):
                    expect(plain.locator('#figure-' + kind)).to_be_visible()
                expect(plain.locator('.detail-figure')).to_have_count(2)
                expect(plain.locator('.change-card')).to_have_count(meta['change_count'])
                assert_loaded_viewport(plain, tolerance=1, report=report)
                capture(plain, 'without-javascript')
            report['checks'].append('Without JavaScript all three complete images, gate details and source decisions remain readable')
            assert not report['errors'], report['errors']
            report['status'] = 'passed'
        except Exception as error:
            report.update(status='failed', url=page.url, error=str(error))
            if not page.is_closed():
                capture(page, 'failure')
            raise
        finally:
            (output / (device + '-report.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url')
    parser.add_argument('--commit')
    parser.add_argument('--output', default='artifacts/panorama-v13-r2-browser')
    parser.add_argument('--browser-executable')
    args = parser.parse_args()
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    with base_url(args.base_url) as base, sync_playwright() as playwright:
        executable = args.browser_executable or os.environ.get('CHROMIUM_PATH')
        browser = playwright.chromium.launch(**({'executable_path': executable} if executable else {}))
        try:
            for device in SIZES:
                exercise(browser, base, device, output, args.commit)
        finally:
            browser.close()
