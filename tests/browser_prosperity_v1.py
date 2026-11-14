#!/usr/bin/env python3
"""Exercise the actual prosperity maps, source links and shared-object journeys."""
import argparse
import functools
import http.server
import json
import os
import re
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlencode, urlparse

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--base-url')
parser.add_argument('--output', default='artifacts/prosperity-v1-browser')
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


def ready(target, view=None):
    target.wait_for_function(
        'document.documentElement.dataset.prosperityReady === "true"', timeout=45000)
    if view:
        expect(target.locator('#map-viewport')).to_have_attribute('data-current-view', view)


def no_overflow(target):
    assert target.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')


def parameters(target):
    return target.evaluate('Object.fromEntries(new URLSearchParams(location.hash.slice(1)))')


def read_data(context):
    response = context.request.get(base + 'prosperity/data.json')
    assert response.status == 200
    return response.json()


def shape_box(target):
    return target.locator('#map-viewport > svg').get_attribute('viewBox')


try:
    with sync_playwright() as pw:
        options = {'headless': True}
        if os.environ.get('CHROMIUM_PATH'):
            options['executable_path'] = os.environ['CHROMIUM_PATH']
        browser = pw.chromium.launch(**options)
        context = browser.new_context(viewport={'width': 1500, 'height': 1000})
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        data = read_data(context)
        records = {e['id']: e for e in data['entities']}
        views = [v for v in ['plan', 'geography', 'panorama'] if data['maps'].get(v, {}).get('url')]
        assert 'plan' in views and 'geography' in views
        preferred = 'ic_yongning' if 'ic_yongning' in records else data['entities'][0]['id']

        response = page.goto(base + 'prosperity.html', wait_until='networkidle')
        assert response.status == 200
        ready(page, 'plan')
        expect(page.locator('h1')).to_contain_text('盛时洛阳')
        expect(page.locator('.eyebrow')).to_contain_text('516—528')
        expect(page.locator('#view-switch button:visible')).to_have_count(len(views))
        expect(page.locator('#entity-select option')).to_have_count(len(records))
        expect(page.locator('#basis-label')).to_have_text(data['maps']['plan']['basis_label'])
        expect(page.locator('#release-status')).to_contain_text('正式发布一致')
        expect(page.locator('#modern-reference-control')).to_be_hidden()
        expect(page.locator('#map-viewport [role="button"]')).to_have_count(179)
        expect(page.locator('#map-viewport #prosperity-plan-targets [data-target-id][role="button"]')).to_have_count(179)
        no_overflow(page)
        page.screenshot(path=str(out / 'prosperity-desktop-first-screen.png'))
        ok('the prosperity page loads its real documentary map, bounded geography mode and all object records')

        before = shape_box(page)
        page.locator('#zoom-in').click()
        expect(page.locator('#map-viewport > svg')).not_to_have_attribute('viewBox', before)
        zoomed = shape_box(page)
        viewport = page.locator('#map-viewport').bounding_box()
        page.mouse.move(viewport['x'] + viewport['width'] * .55, viewport['y'] + viewport['height'] * .52)
        page.mouse.down()
        page.mouse.move(viewport['x'] + viewport['width'] * .63, viewport['y'] + viewport['height'] * .58, steps=8)
        page.mouse.up()
        assert shape_box(page) != zoomed
        page.locator('#reset-map').click()
        assert shape_box(page) == before
        ok('the actual SVG supports zoom, drag and restoration of its original view')

        # Select through the map itself: focus a real feature to keep even small symbols reachable.
        direct = page.locator('#map-viewport #prosperity-plan-targets [data-target-id][role="button"][aria-label]:visible')
        feature_nodes = direct.evaluate_all('nodes => nodes.map(n => ({target:n.getAttribute("data-target-id"), id:n.getAttribute("data-entity-id")||""}))')
        solo_nodes = [n for n in feature_nodes if n['id'] in records]
        assert solo_nodes, 'The documentary map should retain independently selectable records'
        eligible = next((n for n in solo_nodes if n['id'] == preferred), solo_nodes[0])
        target = page.locator('#map-viewport #prosperity-plan-targets [data-target-id="'+eligible['target']+'"]')
        target.focus()
        target.press('Enter')
        ready(page, 'plan')
        assert parameters(page)['entity'] == eligible['id']
        expect(page.locator('#entity-detail h2')).to_have_text(records[eligible['id']]['name'])
        assert page.locator('#map-viewport .prosperity-selected').count() > 0
        clicked_entity = parameters(page)['entity']
        page.locator('#focus-selection').click()
        page.locator('#entity-search').fill('无此地点-pointer-check')
        ready(page)
        expect(page.locator('#entity-select')).to_be_disabled()
        target.click()
        ready(page)
        assert parameters(page)['entity'] == clicked_entity
        expect(page.locator('#entity-search')).to_have_value('')
        ok('keyboard and pointer selection on real map features open existing entities and clear incompatible filters')

        page.locator('#reset-map').click()
        groups = page.locator('#map-viewport #prosperity-plan-targets [data-target-id][role="button"]')
        shared_index = groups.evaluate_all('''nodes => nodes.findIndex(n => {
            const ids=(n.getAttribute('data-entity-ids')||'').split(/[ ,]+/).filter(Boolean);
            const members=JSON.parse(n.getAttribute('data-members')||'[]');
            return new Set([...ids,...members.map(m => typeof m==='string'?m:m.id)]).size > 1;
        })''')
        assert shared_index >= 0, 'Existing shared reading positions must remain groups'
        group = groups.nth(shared_index)
        group.focus()
        group.press('Enter')
        ready(page, 'plan')
        assert parameters(page).get('group') and not parameters(page).get('entity')
        expect(page.locator('[data-group-detail]')).to_contain_text('没有因此得到确认')
        members = page.locator('[data-group-member]').evaluate_all('nodes => nodes.map(n => n.dataset.groupMember)')
        assert len(members) > 1 and all(member in records for member in members)
        page.locator('[data-group-member]').last.click()
        ready(page, 'plan')
        assert parameters(page)['entity'] == members[-1]
        expect(page.locator('#entity-detail')).to_contain_text('共同阅读组')
        page.reload(wait_until='networkidle')
        ready(page, 'plan')
        assert parameters(page).get('group') and parameters(page)['entity'] == members[-1]
        page.locator('#clear-filters').click()
        ready(page)
        ok('shared map positions first offer members, preserve group identity and never silently choose a separate address')

        page.locator('#entity-search').fill(preferred)
        ready(page)
        expected = [e for e in data['entities'] if any(preferred.casefold() in str(v).casefold()
                    for v in [e['id'], e['name'], e.get('display_name', ''), *e.get('aliases', [])])]
        expect(page.locator('#entity-select option')).to_have_count(len(expected))
        page.locator('#entity-select').select_option(preferred)
        ready(page)
        expect(page.locator('#entity-detail h2')).to_have_text(records[preferred]['name'])
        page.reload(wait_until='networkidle')
        ready(page, 'plan')
        assert parameters(page)['entity'] == preferred and parameters(page)['q'] == preferred
        expect(page.locator('#entity-search')).to_have_value(preferred)
        page.locator('#entity-search').fill('无此地点-acceptance-xyz')
        ready(page)
        expect(page.locator('#entity-select')).to_be_disabled()
        expect(page.locator('#entity-detail')).to_contain_text('没有匹配的地点')
        page.locator('#clear-filters').click()
        ready(page)
        expect(page.locator('#entity-select option')).to_have_count(len(records))
        ok('search, empty results, clearing and deep-link reload preserve the selected documentary record')

        region = next(r for r in data['regions'] if r.get('entity_ids'))
        page.locator('#region-filter').select_option(region['id'])
        ready(page)
        region_ids = set(region['entity_ids']) & set(records)
        assert set(page.locator('#entity-select option').evaluate_all('nodes => nodes.map(n => n.value)')) == region_ids
        page.locator('#clear-filters').click()
        ready(page)
        kind = next(e['kind'] for e in data['entities'] if e.get('kind'))
        page.locator('#kind-filter').select_option(kind)
        ready(page)
        assert set(page.locator('#entity-select option').evaluate_all('nodes => nodes.map(n => n.value)')) == {e['id'] for e in data['entities'] if e.get('kind') == kind}
        page.locator('#clear-filters').click()
        ready(page)
        ok('region and type filters show the records explicitly assigned to each selection')

        illustrated = next((e for e in data['entities'] if e.get('detail_figure', {}).get('url')), None)
        if illustrated:
            page.locator('#entity-select').select_option(illustrated['id'])
            ready(page)
            page.wait_for_function('''() => {
                const image=document.querySelector('.detail-figure img');
                return image && image.complete && image.naturalWidth > 0;
            }''')
            expect(page.locator('.detail-figure img')).to_have_attribute('alt',re.compile(r'.+'))
            if illustrated['detail_figure'].get('caption'):
                expect(page.locator('.detail-figure figcaption')).to_have_text(illustrated['detail_figure']['caption'])
            ok('the selected record loads its actual relationship figure together with its explanatory caption')

        page.locator('#zoom-in').click()
        plan_box = shape_box(page)
        page.locator('[data-view="geography"]').click()
        ready(page, 'geography')
        expect(page.locator('#basis-label')).to_have_text(data['maps']['geography']['basis_label'])
        assert page.locator('#map-viewport').get_attribute('data-map') == data['maps']['geography']['url']
        page.locator('#zoom-in').click()
        geo_box = shape_box(page)
        page.locator('[data-view="plan"]').click()
        ready(page, 'plan')
        assert shape_box(page) == plan_box
        page.locator('[data-view="geography"]').click()
        ready(page, 'geography')
        assert shape_box(page) == geo_box
        page.screenshot(path=str(out / 'prosperity-geography.png'))
        ok('documentary and geographic maps retain separate camera positions and display their own source basis')

        modern_layers = page.locator('#map-viewport [data-layer="modern_reference"]')
        assert modern_layers.count() > 0, 'Modern geographic references must have a separately controllable layer'
        expect(page.locator('#modern-reference-control')).to_be_visible()
        expect(page.locator('#modern-reference')).not_to_be_checked()
        assert modern_layers.evaluate_all('nodes => nodes.every(n => getComputedStyle(n).display === "none")')
        page.locator('#modern-reference').check()
        ready(page, 'geography')
        assert modern_layers.evaluate_all('nodes => nodes.every(n => getComputedStyle(n).display !== "none")')
        assert parameters(page)['modern'] == '1'
        page.locator('[data-view="plan"]').click()
        ready(page, 'plan')
        expect(page.locator('#modern-reference-control')).to_be_hidden()
        page.locator('[data-view="geography"]').click()
        ready(page, 'geography')
        expect(page.locator('#modern-reference')).to_be_checked()
        page.reload(wait_until='networkidle')
        ready(page, 'geography')
        expect(page.locator('#modern-reference')).to_be_checked()
        assert modern_layers.evaluate_all('nodes => nodes.every(n => getComputedStyle(n).display !== "none")')
        page.locator('#modern-reference').uncheck()
        ready(page, 'geography')
        assert modern_layers.evaluate_all('nodes => nodes.every(n => getComputedStyle(n).display === "none")')
        ok('modern geographic references start hidden and can be toggled independently with their deep-link state preserved')

        unlocated = next((e for e in data['entities'] if e.get('geographic_status') == 'unlocated'), None)
        assert unlocated, 'At least one genuinely unlocated documentary object must remain unlocated'
        page.locator('#entity-select').select_option(unlocated['id'])
        ready(page, 'geography')
        expect(page.locator('#entity-detail [data-geographic-status]')).to_have_attribute('data-geographic-status', 'unlocated')
        expect(page.locator('#entity-detail')).to_contain_text('没有为它指定地理落点')
        expect(page.locator('#focus-selection')).to_be_disabled()
        assert page.locator('#map-viewport .prosperity-selected').count() == 0
        ok('unlocated objects keep their records but acquire no selectable geographic point or focus position')

        mapped = next((e for e in data['entities'] if e.get('geographic_status') in ['source_mapped_extent', 'verified_point', 'candidate_area']), None)
        if mapped:
            page.locator('#entity-select').select_option(mapped['id'])
            ready(page, 'geography')
            expect(page.locator('#entity-detail [data-geographic-status]')).to_have_attribute('data-geographic-status', mapped['geographic_status'])
            for note in mapped['placement_note'] if isinstance(mapped['placement_note'], list) else [mapped['placement_note']]:
                expect(page.locator('#entity-detail')).to_contain_text(note)
            if mapped['geographic_status'] == 'source_mapped_extent':
                expect(page.locator('#entity-detail')).to_contain_text('不自动等同于北魏院界')
            assert page.locator('#map-viewport .prosperity-selected').count() > 0
            expect(page.locator('#focus-selection')).to_be_enabled()
            ok('mapped source positions, extents or candidates open their actual geometry and retain their stated evidential limits')

        source_feature = next(f for f in data['source_features'] if not f.get('entity_id') and not f['id'].startswith('geo-modern-'))
        feature_title = source_feature.get('title') or source_feature.get('label') or source_feature['id']
        source_node = page.get_by_role('button', name=feature_title, exact=True).first
        source_node.focus()
        source_node.press('Enter')
        ready(page, 'geography')
        assert parameters(page)['feature'] == source_feature['id'] and not parameters(page).get('entity')
        expect(page.locator('#entity-detail h2')).to_have_text(feature_title)
        expect(page.locator('#entity-detail')).to_contain_text(source_feature['placement_note'])
        for field in ['source_period','source_historical_period','temporal_interpretation']:
            if source_feature.get(field) and isinstance(source_feature[field],str):
                expect(page.locator('#entity-detail')).to_contain_text(source_feature[field])
        expect(page.locator('#entity-detail')).to_contain_text('与文献地点名录分别保存')
        expect(page.locator('#entity-select option:not([value=""])')).to_have_count(len(records))
        source_record = next(s for s in data['sources'] if s['id'] == source_feature['source_id'])
        expect(page.locator('#entity-detail')).to_contain_text(source_record['title'])
        assert page.locator('#entity-detail a').count() > 0
        page.locator('#reset-map').click()
        source_before = shape_box(page)
        page.locator('#focus-selection').click()
        assert shape_box(page) != source_before
        page.reload(wait_until='networkidle')
        ready(page, 'geography')
        assert parameters(page)['feature'] == source_feature['id'] and not parameters(page).get('entity')
        expect(page.locator('[data-source-feature-detail]')).to_have_attribute('data-source-feature-detail',source_feature['id'])
        ok('independent source-map features open their own evidence, focus their drawn geometry and restore without adding city entities')

        deep_entity = mapped['id'] if mapped else preferred
        page.goto(base + 'prosperity.html#' + urlencode({'view':'geography','entity':deep_entity}), wait_until='networkidle')
        ready(page, 'geography')
        expect(page.locator('#entity-select')).to_have_value(deep_entity)
        page.reload(wait_until='networkidle')
        ready(page, 'geography')
        expect(page.locator('#entity-select')).to_have_value(deep_entity)
        page.locator('[data-view="plan"]').click()
        ready(page, 'plan')
        page.go_back()
        ready(page, 'geography')
        expect(page.locator('#entity-select')).to_have_value(deep_entity)
        ok('geographic entity links survive reload and browser back navigation')

        with page.expect_popup() as popup_info:
            page.locator('#download-map').click()
        popup = popup_info.value
        popup.wait_for_load_state()
        assert popup.url == page.locator('#download-map').get_attribute('href')
        popup.close()
        page.locator('#sources-link').click()
        expect(page.locator('#source-catalog')).to_have_attribute('open', '')
        expect(page.locator('#source-list .source-card')).to_have_count(len(data.get('sources', [])))
        assert len(data.get('sources', [])) > 0
        source_links = page.locator('#source-list a').evaluate_all('links => links.map(a => a.href)')
        assert source_links and all(href.startswith(('https://', 'http://')) for href in source_links)
        expect(page.locator('#download-links a')).to_have_count(len(data.get('downloads', [])))
        review_counts = data['text_review_summary']
        review_decisions = data['map_decisions']
        page.locator('#text-review > summary').click()
        expect(page.locator('#text-review')).to_have_attribute('open','')
        expect(page.locator('[data-text-decision]')).to_have_count(len(review_decisions))
        for key in ['evidence_records','legacy_quote_sequence_match_records','manual_exception_records']:
            expect(page.locator('#text-review-summary')).to_contain_text(str(review_counts[key]))
        expect(page.locator('#text-review-summary')).to_contain_text('全版本的书影逐叶校勘仍待继续')
        expect(page.locator('#text-decisions')).not_to_contain_text('small.inline-note')
        assert any(d['id']=='TXT08' for d in review_decisions)
        expect(page.locator('[data-text-decision="TXT08"]')).to_be_visible()
        terrain_constraints = data['terrain_constraints']
        assert terrain_constraints, 'Reviewed historical terrain clues must remain accessible'
        page.locator('#terrain-review > summary').click()
        expect(page.locator('[data-terrain-constraint]')).to_have_count(len(terrain_constraints))
        terrain_url = urlparse(page.locator('[data-terrain-constraint] a').first.get_attribute('href'))
        assert terrain_url.scheme in ('https','http') and terrain_url.netloc
        no_overflow(page)
        ok('the current SVG, source catalog, global text-review decisions and downloadable artifacts remain accessible')

        if 'panorama' in views:
            page.locator('[data-view="panorama"]').click()
            ready(page, 'panorama')
            expect(page.locator('#basis-label')).to_have_text(data['maps']['panorama']['basis_label'])
            assert page.locator('#map-viewport').get_attribute('data-map') == data['maps']['panorama']['url']
            expect(page.locator('#modern-reference')).not_to_be_checked()
            assert page.locator('#map-viewport [data-layer="modern_reference"]').evaluate_all('nodes => nodes.length > 0 && nodes.every(n => getComputedStyle(n).display === "none")')
            page.screenshot(path=str(out / 'prosperity-panorama.png'))
            ok('the optional layout-derived panorama loads its declared model and evidential basis')

        tablet_context = browser.new_context(viewport={'width':900,'height':1000})
        tablet = tablet_context.new_page()
        tablet.on('pageerror', lambda error: errors.append(str(error)))
        tablet.goto(base + 'prosperity.html', wait_until='networkidle')
        ready(tablet, 'plan')
        no_overflow(tablet)
        assert tablet.locator('.site-header').bounding_box()['y'] + tablet.locator('.site-header').bounding_box()['height'] <= tablet.locator('.introduction').bounding_box()['y']
        tablet.screenshot(path=str(out / 'prosperity-tablet-first-screen.png'))
        tablet.locator('[data-view="geography"]').click()
        ready(tablet, 'geography')
        no_overflow(tablet)
        ok('the 900px layout keeps navigation, both maps and the inspector within the page')

        mobile_context = browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=1)
        mobile = mobile_context.new_page()
        mobile.on('pageerror', lambda error: errors.append(str(error)))
        mobile.goto(base + 'prosperity.html', wait_until='networkidle')
        ready(mobile, 'plan')
        no_overflow(mobile)
        mobile.screenshot(path=str(out / 'prosperity-mobile-first-screen.png'))
        mobile.locator('#filter-toggle').tap()
        mobile.locator('#entity-search').fill(preferred)
        ready(mobile)
        mobile.locator('#entity-select').select_option(preferred)
        ready(mobile)
        expect(mobile.locator('#entity-detail h2')).to_have_text(records[preferred]['name'])
        mobile.locator('[data-view="geography"]').tap()
        ready(mobile, 'geography')
        mobile.locator('#clear-filters').tap()
        ready(mobile)
        mobile.locator('#entity-select').select_option(unlocated['id'])
        ready(mobile)
        expect(mobile.locator('#focus-selection')).to_be_disabled()
        mobile.locator('#sources-link').tap()
        expect(mobile.locator('#source-catalog')).to_have_attribute('open','')
        no_overflow(mobile)
        mobile.screenshot(path=str(out / 'prosperity-mobile.png'), full_page=True)
        ok('390px touch navigation, object search, unlocated records and sources work without horizontal overflow')

        assert not errors, errors
        ok('zero browser runtime errors during the prosperity journeys')
        browser.close()
except Exception as error:
    checks.append({'name':'prosperity browser acceptance','status':'failed','error':str(error)})
    if page:
        try:
            page.screenshot(path=str(out / 'failure.png'), full_page=True)
        except Exception:
            pass
    raise
finally:
    (out / 'results.json').write_text(json.dumps(
        {'base_url':base,'checks':checks,'runtime_errors':errors},ensure_ascii=False,indent=2))
    if server:
        server.shutdown()
    if temporary:
        temporary.cleanup()
