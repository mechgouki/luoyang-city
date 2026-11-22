"""Read R7 on desktop/mobile, follow evidence round trips, and open the ZIP offline."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright
from browser_city_west_p472 import SIZES, base_url

ROOT = Path(__file__).resolve().parents[1]
PAGE = "luoyang-city-nodes.html"
KEY = "city_nodes_r7"
NODE_ROADS = {"palace-yongning": "R01", "baima": "G11", "sima": "P01", "jianchun": "B01"}


def exercise(browser, base, device, output, expected_commit=None):
    settings = dict(viewport=SIZES[device], is_mobile=device == "mobile",
                    has_touch=device == "mobile", reduced_motion="reduce")
    report = dict(device=device, viewport=SIZES[device], checks=[], downloads={}, screenshots={}, errors=[])
    active_page = None

    def watch(page):
        page.on("pageerror", lambda error: report["errors"].append(str(error)))

    def fits(page):
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), page.url

    def count(page, number):
        expect(page.locator(".segment[data-segment]:visible")).to_have_count(number)

    def capture(target, label):
        name = device + "-" + label + ".png"
        raw = target.screenshot(path=output / name, animations="disabled")
        report["screenshots"][name] = hashlib.sha256(raw).hexdigest()

    with browser.new_context(**settings, accept_downloads=True) as context:
        page = context.new_page()
        active_page = page
        watch(page)
        try:
            info = context.request.get(base + "build-info.json").json()
            meta = info[KEY]
            data = context.request.get(base + "city-nodes/readings.json").json()
            assert meta["source_commit"] == data["source_commit"] == info["source_commit"]
            if expected_commit:
                assert info["source_commit"] == expected_commit, "Browser reached another deployment"
            report["source_commit"] = info["source_commit"]
            records = data["segments"]
            assert data["counts"]["entities_indexed"] == 339
            assert data["counts"]["roads_indexed"] == 84 and data["counts"]["waters_indexed"] == 34

            for homepage in ("index.html", "v3.0-dual.html"):
                page.goto(base + homepage, wait_until="domcontentloaded")
                expect(page.locator('[data-hero-revision="panorama-approved-v12"]')).to_be_visible()
                page.locator("#r7-home-guide").click()
                page.wait_for_url("**/" + PAGE + "#panorama")
                expect(page.locator(".guide-card")).to_have_count(6)
                hero = page.locator('.panorama-stage img[data-hero-revision="panorama-approved-v12"]')
                expect(hero).to_be_visible()
                page.wait_for_function("document.querySelector('.panorama-stage img').complete && document.querySelector('.panorama-stage img').naturalWidth > 0")
                dimensions = hero.evaluate("el => ({width:el.naturalWidth,height:el.naturalHeight,current:el.currentSrc,box:el.getBoundingClientRect().toJSON(),fit:getComputedStyle(el).objectFit})")
                expected_size = (960, 540) if device == "mobile" else (1672, 941)
                assert (dimensions["width"], dimensions["height"]) == expected_size
                ratio = dimensions["box"]["width"] / dimensions["box"]["height"]
                assert abs(ratio - expected_size[0] / expected_size[1]) < .01, "V12 is cropped or distorted"
                points = page.locator(".panorama-point").evaluate_all("items => items.map(el => el.getBoundingClientRect().toJSON())")
                for index, point in enumerate(points):
                    for other in points[index + 1:]:
                        overlap_x = min(point["right"], other["right"]) - max(point["left"], other["left"])
                        overlap_y = min(point["bottom"], other["bottom"]) - max(point["top"], other["top"])
                        assert overlap_x <= 0 or overlap_y <= 0, "Picture guide targets overlap"
                fits(page)
            capture(page.locator(".panorama-figure"), "v12-guide")
            report["checks"].append("Both V12 home entries reach the six-point guide; desktop/mobile image dimensions and full-frame proportions remain intact")

            page.goto(base + "luoyang-all-roads.html", wait_until="domcontentloaded")
            expect(page.locator("details[data-record]")).to_have_count(84)
            page.locator("#r7-road-entry a").click()
            page.wait_for_url("**/" + PAGE)
            expect(page.locator(".map-figure")).to_have_count(5)
            expect(page.locator(".finding")).to_have_count(data["counts"]["findings"])
            expect(page.locator(".segment[data-segment]")).to_have_count(len(records))
            count(page, len(records))
            fits(page)
            capture(page.locator("#map-overview .map-scroll"), "overview")
            report["checks"].append("R6.2 retains all 84 records and leads to five R7 maps, all reviewed findings, and all 28 linked source records")

            for node in [*NODE_ROADS, "panorama"]:
                page.locator("#node-filter").select_option(node)
                expected = [r for r in records if node in r["node_ids"] or node == "panorama" and not r["node_ids"]]
                count(page, len(expected))
            page.locator("#segment-clear").click()
            for evidence in ("source_frame", "relation_only"):
                page.locator("#evidence-filter").select_option(evidence)
                count(page, sum(r["geometry_status"] == evidence for r in records))
            page.reload(wait_until="domcontentloaded")
            expect(page.locator("#evidence-filter")).to_have_value("relation_only")
            page.locator("#segment-clear").click()
            page.locator("#segment-query").fill("P01")
            count(page, 1)
            expect(page.locator("#segment-P01")).to_be_visible()
            page.reload(wait_until="domcontentloaded")
            expect(page.locator("#segment-query")).to_have_value("P01")
            count(page, 1)
            page.locator("#segment-query").fill("no-such-r7-record")
            count(page, 0)
            expect(page.locator("#segment-empty")).to_be_visible()
            page.locator("#segment-clear").click()
            count(page, len(records))
            # Shareable filters combine; a direct record link is still allowed to
            # reveal its record and clears a conflicting filter rather than hiding it.
            page.goto(base + PAGE + "?q=G11&node=baima&evidence=relation_only", wait_until="domcontentloaded")
            count(page, 1)
            expect(page.locator("#segment-G11")).to_be_visible()
            page.goto(base + PAGE + "?q=G11&node=baima#segment-P01", wait_until="domcontentloaded")
            expect(page.locator("#segment-P01")).to_have_attribute("open", "")
            expect(page.locator("#segment-query")).to_have_value("")
            expect(page.locator("#node-filter")).to_have_value("")
            page.locator("#segment-query").fill("G11")
            count(page, 1)
            assert page.evaluate("location.hash") == "#register", "A stale deep link overrides a later search"
            page.reload(wait_until="domcontentloaded")
            count(page, 1)
            expect(page.locator("#segment-query")).to_have_value("G11")
            report["checks"].append("Every node and evidence filter works; exact IDs, combined URL filters, reload, no-result state and conflicting deep links retain a usable result")

            for node, rid in NODE_ROADS.items():
                page.goto(base + PAGE + "#segment-" + rid, wait_until="domcontentloaded")
                card = page.locator("#segment-" + rid)
                expect(card).to_have_attribute("open", "")
                fits(page)
                capture(card, node + "-evidence")
                card.locator(f'[data-return-map="{node}"][data-return-segment="{rid}"]').click()
                assert page.evaluate("location.hash") == "#map-" + node
                target = page.locator(f'#map-{node} [data-segment-ref="{rid}"].is-selected').first
                expect(target).to_be_attached()
                assert target.evaluate("node => document.activeElement === node"), (node, "No keyboard focus after map return")
                assert target.evaluate("""node => {
                    const a=node.getBoundingClientRect();
                    const b=node.closest('.map-scroll').getBoundingClientRect();
                    return a.right>b.left && a.left<b.right && a.bottom>b.top && a.top<b.bottom;
                }"""), (node, "Selected item remains outside the map viewport")
                expect(page.locator("#map-" + node + " .map-status")).to_contain_text(rid)
                capture(page.locator("#map-" + node + " .map-scroll"), node + "-map")
                page.reload(wait_until="domcontentloaded")
                expect(target).to_be_attached()
                target.focus()
                page.keyboard.press("Enter")
                assert page.evaluate("location.hash") == "#segment-" + rid
                expect(card).to_have_attribute("open", "")
                fits(page)
            report["checks"].append("All four local maps return from evidence to the existing item with selection, focus and visible bounds; reload and keyboard Enter return to the same source record")

            page.goto(base + PAGE + "#finding-SI07", wait_until="domcontentloaded")
            expect(page.locator("#finding-SI07")).to_have_attribute("open", "")
            expect(page.locator("#finding-SI07")).to_contain_text("统计范围")
            capture(page.locator("#finding-SI07"), "warehouse-scope")
            page.goto(base + PAGE + "#water-W01", wait_until="domcontentloaded")
            expect(page.locator("#water-W01")).to_be_visible()
            page.goto(base + PAGE + "#map-overview", wait_until="domcontentloaded")
            zoom = page.locator("#zoom-overview")
            initial_width = page.locator("#map-overview svg").bounding_box()["width"]
            zoom.focus()
            page.keyboard.press("End")
            assert page.locator("#map-overview svg").bounding_box()["width"] > initial_width * 1.5
            page.reload(wait_until="domcontentloaded")
            expect(zoom).to_have_value("220")
            scroll = page.locator("#map-overview .map-scroll")
            assert scroll.evaluate("el => el.scrollWidth > el.clientWidth")
            scroll.focus()
            page.keyboard.press("ArrowRight")
            page.wait_for_function("document.querySelector('#map-overview .map-scroll').scrollLeft > 0")
            page.locator('[data-map-reset="overview"]').click()
            expect(zoom).to_have_value("100")
            expect(scroll).to_have_js_property("scrollLeft", 0)
            fits(page)
            report["checks"].append("Finding and water anchors reveal their evidence; overview zoom persists, keyboard panning works, and reset restores the whole map")

            page.goto(base + PAGE + "#panorama", wait_until="domcontentloaded")
            page.locator("#point-bridge").click()
            expect(page.locator("#guide-bridge")).to_have_class("guide-card is-selected")
            expect(page.locator("#guide-bridge")).to_contain_text("登陆点")
            page.locator('#guide-bridge [data-return-guide="bridge"]').click()
            expect(page.locator("#point-bridge")).to_have_attribute("aria-current", "true")
            page.reload(wait_until="domcontentloaded")
            expect(page.locator("#point-bridge")).to_have_attribute("aria-current", "true")
            page.locator("#show-panorama-guides").uncheck()
            expect(page.locator(".panorama-points")).to_be_hidden()
            page.locator("#show-panorama-guides").check()
            report["checks"].append("V12 bridge hotspot explains unknown landings, returns to the same picture point, survives reload, and can be hidden to read the full artwork")

            with tempfile.TemporaryDirectory() as temporary:
                for path in meta["download_files"]:
                    link = page.locator(f'[download][href="./{path}"]').first
                    with page.expect_download() as event:
                        link.click()
                    raw = Path(event.value.path()).read_bytes()
                    checksum = hashlib.sha256(raw).hexdigest()
                    assert checksum == info["files_sha256"][path], path
                    report["downloads"][path] = checksum
                    if path == meta["bundle"]:
                        with ZipFile(event.value.path()) as archive:
                            archive.extractall(temporary)
                assert len(report["downloads"]) == 9
                with browser.new_context(**settings, offline=True) as disconnected:
                    local = disconnected.new_page()
                    active_page = local
                    watch(local)
                    local.goto((Path(temporary) / "index.html").as_uri() + "#segment-P01")
                    expect(local.locator("#segment-P01")).to_have_attribute("open", "")
                    expect(local.locator(".map-figure")).to_have_count(5)
                    expect(local.locator(".finding")).to_have_count(data["counts"]["findings"])
                    local.locator("#segment-query").fill("G11")
                    count(local, 1)
                    local.reload(wait_until="domcontentloaded")
                    expect(local.locator("#segment-query")).to_have_value("G11")
                    count(local, 1)
                    local.goto((Path(temporary) / "index.html").as_uri() + "#panorama")
                    local.wait_for_function("document.querySelector('.panorama-stage img').complete && document.querySelector('.panorama-stage img').naturalWidth > 0")
                    fits(local)
                    capture(local.locator(".panorama-figure"), "offline-v12")
                active_page = page
            report["checks"].append("All nine advertised downloads match release hashes; disconnected ZIP preserves five maps, every finding, exact-ID search and the full V12 image")

            with browser.new_context(**settings, java_script_enabled=False) as disabled:
                plain = disabled.new_page()
                active_page = plain
                watch(plain)
                plain.goto(base + PAGE, wait_until="domcontentloaded")
                expect(plain.locator(".segment[data-segment]")).to_have_count(len(records))
                expect(plain.locator(".map-figure")).to_have_count(5)
                plain.locator("#segment-G11 > summary").click()
                expect(plain.locator("#segment-G11")).to_have_attribute("open", "")
                fits(plain)
                capture(plain.locator("#segment-G11"), "without-javascript")
            active_page = page
            report["checks"].append("With JavaScript disabled, every map and record remains in the HTML and native evidence details still open by click")
            assert not report["errors"], report["errors"]
            report["status"] = "passed"
        except Exception as error:
            target = active_page if active_page and not active_page.is_closed() else page
            report.update(status="failed", url=target.url, error=str(error))
            if not target.is_closed():
                capture(target, "failure")
            raise
        finally:
            (output / (device + "-report.json")).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--commit")
    parser.add_argument("--output", default="artifacts/city-nodes-r7-browser")
    parser.add_argument("--browser-executable", help="Explicit local Chromium path; CI uses its pinned Playwright browser")
    args = parser.parse_args()
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    with base_url(args.base_url) as base, sync_playwright() as playwright:
        executable = args.browser_executable or os.environ.get("CHROMIUM_PATH")
        options = {"executable_path": executable} if executable else {}
        browser = playwright.chromium.launch(**options)
        try:
            for device in SIZES:
                exercise(browser, base, device, output, args.commit)
        finally:
            browser.close()
