"""Exercise the actual P470 map, evidence panels and downloads on desktop/mobile."""
import argparse
import csv
import functools
import hashlib
import http.server
import io
import json
import os
import re
import tempfile
import threading
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from xml.etree import ElementTree as ET

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PAGE = "prosperity-city-common.html"
DOWNLOADS = (
    "common-470/city-common.svg", "common-470/readings.json", "common-470/places.csv",
    "common-470/reuse-plan.json", "common-470/bundle-manifest.json", "downloads/common-470.zip",
)
SIZES = {"desktop": {"width": 1440, "height": 950}, "mobile": {"width": 390, "height": 844}}


def sha(content):
    return hashlib.sha256(content).hexdigest()


def compact(text):
    return re.sub(r"\s+", "", text or "")


def ready(page):
    page.wait_for_function("document.body.dataset.commonReady === '1'")


def fit(page):
    widths = page.evaluate("""({documentWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth, innerWidth: innerWidth})""")
    assert page.viewport_size
    assert all(value <= page.viewport_size["width"] + 2 for value in widths.values()), widths


def screenshot(page, output, report, stem, selector=None):
    page.evaluate("document.fonts.ready")
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    fit(page)
    target = output / f"p470-{report['device']}-{stem}.png"
    if selector:
        element = page.locator(selector)
        expect(element).to_be_visible()
        element.screenshot(path=str(target), animations="disabled")
    else:
        page.screenshot(path=str(target), animations="disabled")
    report["screenshot_sha256"][target.name] = sha(target.read_bytes())


def assert_place(page, place):
    identifier = place["id"]
    expect(page.locator("body")).to_have_attribute("data-current-place", identifier)
    for candidate in ("C01", "C02", "C03", "C04"):
        card = page.locator(f"#place-{candidate}")
        button = page.locator(f'[data-place-choice="{candidate}"]')
        if candidate == identifier:
            expect(card).to_be_visible()
            expect(button).to_have_attribute("aria-pressed", "true")
            assert compact(place["name"]) in compact(card.inner_text())
        else:
            expect(card).to_be_hidden()
            expect(button).to_have_attribute("aria-pressed", "false")
    selected = page.locator('#city-common-map [data-place-id].is-selected')
    assert set(selected.evaluate_all("nodes => nodes.map(node => node.dataset.placeId)")) == {identifier}
    for feature in place["reading_navigation"]["selection_feature_ids"]:
        mark = page.locator(f'#city-common-map [data-feature-id="{feature}"]')
        expect(mark).to_have_class(re.compile(r"\bis-selected\b"))
    expect(page.locator("#place-overview")).to_be_hidden()
    scenes = place["reading_navigation"]["urban_cluster_ids"]
    expect(page.locator("body")).to_have_attribute("data-current-scene", scenes[0] if scenes else "")
    if not scenes:
        expect(page.locator("#scene-none")).to_be_visible()
        expect(page.locator("[data-scene-panel]:visible")).to_have_count(0)
    state = parse_qs(urlsplit(page.url).fragment)
    assert state.get("place") == [identifier], state


def assert_scene(page, scene, *, nojs=False):
    panel = page.locator(f'#scene-{scene["id"]}')
    expect(panel).to_be_visible()
    if not nojs:
        expect(page.locator("body")).to_have_attribute("data-current-scene", scene["id"])
        expect(page.locator(f'[data-scene-choice="{scene["id"]}"]')).to_have_attribute("aria-pressed", "true")
        expect(page.locator("[data-scene-panel]:visible")).to_have_count(1)
    expect(panel.locator("[data-urban-edge-id]")).to_have_count(len(scene["edges"]))
    for edge in scene["edges"]:
        row = panel.locator(f'[data-urban-edge-id="{edge["id"]}"]')
        expect(row).to_be_visible()
        details = row.locator("details")
        if details.count() and details.first.get_attribute("open") is None:
            details.first.locator("summary").click()
        text = compact(row.inner_text())
        assert compact(edge["quote"]) in text, edge["id"]
        assert compact(edge["scope"]) in text, edge["id"]
        assert edge["grade"] in row.inner_text(), edge["id"]
    for event in scene.get("temporal_events", []):
        row = panel.locator(f'[data-urban-event-id="{event["id"]}"]')
        expect(row).to_be_visible()
        assert compact(event["event"]) in compact(row.inner_text()), event["id"]
        assert compact(event["scope"]) in compact(row.inner_text()), event["id"]
    if scene["id"] == "K03":
        expect(panel.locator('[data-scene-location-status="unbound"]')).to_be_visible()
        if not nojs:
            expect(page.locator("body")).to_have_attribute("data-current-place", "")
            expect(page.locator('#city-common-map [data-place-id].is-selected')).to_have_count(0)
            expect(page.locator("#place-overview")).to_be_visible()
            expect(page.locator("[data-place-card]:visible")).to_have_count(0)


def assert_layer(page, name, visible):
    control = page.locator("#layer-" + name)
    expect(control).to_be_checked(checked=visible)
    layers = page.locator(f'#city-common-map [data-city-layer="{name}"]')
    assert layers.count(), name
    for layer in layers.all():
        if visible:
            expect(layer).to_be_visible()
        else:
            expect(layer).to_be_hidden()


def actual_downloads(page, base, output, data, info, report):
    saved = {}
    for path in DOWNLOADS:
        report["download_target"] = {"path": path, "url": base + path,
                                     "page_url": page.url, "viewport": page.viewport_size}
        attempt = {"path": path, "status": "pending"}
        report["download_attempts"].append(attempt)
        link = page.locator(f'a[download][href="{path}"], a[download][href="./{path}"]')
        expect(link).to_have_count(1)
        expect(link).to_be_visible()
        # A failed target is retained before waiting; there is no silent retry.
        with page.expect_download() as pending:
            link.click()
        download = pending.value
        failure = download.failure()
        assert failure is None, f"{path}: {failure}"
        target = output / "downloads" / report["device"] / path
        target.parent.mkdir(parents=True, exist_ok=True)
        download.save_as(str(target))
        content = target.read_bytes()
        digest = sha(content)
        assert digest == info["files_sha256"][path], f"Download hash mismatch: {path}"
        saved[path] = content
        report["download_sha256"][path] = digest
        attempt.update(status="passed", bytes=len(content), sha256=digest,
                       suggested_filename=download.suggested_filename)
    report["download_target"] = None
    assert len(report["download_sha256"]) == 6
    assert ET.fromstring(saved[DOWNLOADS[0]]).get("id") == "city-common-map"
    assert json.loads(saved[DOWNLOADS[1]]) == data
    rows = list(csv.DictReader(io.StringIO(saved[DOWNLOADS[2]].decode("utf-8-sig"))))
    assert {row["card_id"] for row in rows} == {"C01", "C02", "C03", "C04"}
    taiji = next(row for row in rows if row["card_id"] == "C03")
    assert taiji["entity_id"] == "" and taiji["scene_binding_feature_id"] == ""
    assert json.loads(saved[DOWNLOADS[3]])["expected_counts"] == data["counts"]
    manifest = json.loads(saved[DOWNLOADS[4]])
    assert manifest["source_commit"] == info["source_commit"]
    with zipfile.ZipFile(io.BytesIO(saved[DOWNLOADS[5]])) as archive:
        members = set(archive.namelist())
        assert members == set(manifest["files_sha256"]) | {DOWNLOADS[4], "index.html"}
        assert archive.read(DOWNLOADS[4]) == saved[DOWNLOADS[4]]
        for path, expected in manifest["files_sha256"].items():
            assert sha(archive.read(path)) == expected, path
            if path in saved:
                assert archive.read(path) == saved[path], path
        report["bundle_members"] = len(members)


def nojs(browser, base, output, device, data, report):
    context = browser.new_context(viewport=SIZES[device], is_mobile=device == "mobile",
                                  has_touch=device == "mobile", java_script_enabled=False,
                                  reduced_motion="reduce")
    page = context.new_page()
    try:
        response = page.goto(base + PAGE, wait_until="load")
        assert response.ok
        expect(page.locator("[data-place-card]:visible")).to_have_count(4)
        expect(page.locator("[data-scene-panel]:visible")).to_have_count(3)
        expect(page.locator("[data-function-object]:visible")).to_have_count(15)
        for scene in data["urban"]["clusters"]:
            assert_scene(page, scene, nojs=True)
        expect(page.locator('#city-common-map [data-city-layer="modern"]')).to_be_hidden()
        point = page.locator('#city-common-map [data-place-id="C04"] circle[data-source-feature-id]').first
        point.click()
        assert urlsplit(page.url).fragment == "place-C04"
        expect(page.locator("#place-C04")).to_be_visible()
        assert compact(next(place for place in data["places"] if place["id"] == "C04")["name"]) in compact(page.locator("#place-C04").inner_text())
        for path in DOWNLOADS:
            expect(page.locator(f'a[download][href="./{path}"], a[download][href="{path}"]')).to_be_visible()
        screenshot(page, output, report, "nojs-map", "#common-map-scroll")
        screenshot(page, output, report, "nojs-C04", "#place-C04")
        screenshot(page, output, report, "nojs-K03", "#scene-K03")
        report["no_javascript"] = {"status": "passed", "building_cards": 4, "scenes": 3,
                                   "relations": 17, "events": 2, "function_objects": 15,
                                   "download_links": 6, "fallback_fragment": "place-C04"}
    except Exception:
        report["no_javascript"] = {"status": "failed", "url": page.url, "viewport": page.viewport_size}
        try:
            page.screenshot(path=str(output / f"p470-{device}-nojs-failure.png"), animations="disabled")
        except Exception as error:
            report["no_javascript"]["screenshot_error"] = str(error)
        raise
    finally:
        context.close()


def check_page(page, base, output, device):
    output.mkdir(parents=True, exist_ok=True)
    report = {"base_url": base, "device": device, "viewport": SIZES[device], "status": "running",
              "checks": [], "errors": [], "download_sha256": {}, "download_attempts": [],
              "download_target": None, "screenshot_sha256": {}}
    on_error = lambda error: report["errors"].append(str(error))
    page.on("pageerror", on_error)
    try:
        response = page.goto(base + "prosperity-backbone-p469.html", wait_until="domcontentloaded")
        assert response.ok
        entry = page.locator("#p470-entry a")
        expect(entry).to_have_count(1)
        expect(entry).to_be_visible()
        entry.click()
        page.wait_for_url("**/" + PAGE + "*")
        ready(page)
        expect(page.locator("h1")).to_be_visible()
        report["checks"].append("Visible P469 continuation opens the independent P470 page")
        response = page.request.get(base + "build-info.json")
        assert response.ok
        info = response.json()
        response = page.request.get(base + "common-470/readings.json")
        assert response.ok
        data = response.json()
        report["source_commit"] = info["source_commit"]
        report["counts"] = data["counts"]
        assert data["counts"]["features"] == 25
        places = {place["id"]: place for place in data["places"]}
        expect(page.locator("body")).to_have_attribute("data-current-place", "C01")
        expect(page.locator("body")).to_have_attribute("data-current-scene", "K01")
        for layer, visible in (("roads", True), ("walls", True), ("modern", False)):
            assert_layer(page, layer, visible)
        screenshot(page, output, report, "initial")
        screenshot(page, output, report, "map-default", "#common-map-scroll")
        report["checks"].append("Initial C01/K01 state shows source roads and walls with modern reference hidden")

        for identifier, place in places.items():
            point = page.locator(f'#city-common-map [data-place-id="{identifier}"] circle[data-source-feature-id="{place["feature_id"]}"]')
            expect(point).to_have_count(1)
            point.click()
            assert_place(page, place)
            screenshot(page, output, report, "place-" + identifier, "#place-" + identifier)
        report["checks"].append("Four actual SVG point clicks select original cards; C04 highlights tower and temple wall, C03 has no scene binding")
        for identifier, place in places.items():
            page.locator(f'[data-place-choice="{identifier}"]').click()
            assert_place(page, place)
        report["checks"].append("Four visible card controls select the same map features and preserve scene scope")

        for scene in data["urban"]["clusters"]:
            page.locator(f'[data-scene-choice="{scene["id"]}"]').click()
            assert_scene(page, scene)
            screenshot(page, output, report, "scene-" + scene["id"], "#scene-" + scene["id"])
        report["checks"].append("Three scene controls expose all 17 original quotations/scopes and two events; K03 clears geographic selection")

        for layer in ("roads", "walls"):
            page.locator("#layer-" + layer).uncheck()
            assert_layer(page, layer, False)
            page.locator("#layer-" + layer).check()
            assert_layer(page, layer, True)
        page.locator("#layer-modern").check()
        assert_layer(page, "modern", True)
        screenshot(page, output, report, "map-modern", "#common-map-scroll")
        page.locator("#layer-modern").uncheck()
        assert_layer(page, "modern", False)
        report["checks"].append("Road, wall and modern-reference toggles operate on the actual SVG source groups")

        drawing = page.locator("#city-common-map")
        before = drawing.bounding_box()
        page.locator("#map-zoom").click()
        expect(page.locator("#map-zoom")).to_have_attribute("aria-pressed", "true")
        after = drawing.bounding_box()
        assert before and after and after["width"] > before["width"], (before, after)
        scroller = page.locator("#common-map-scroll")
        scroll = scroller.evaluate("node => ({width: node.clientWidth, scrollWidth: node.scrollWidth})")
        assert scroll["scrollWidth"] > scroll["width"]
        scroller.focus()
        previous = scroller.evaluate("node => node.scrollLeft")
        page.keyboard.press("ArrowLeft" if previous > 0 else "ArrowRight")
        page.wait_for_function("({node, before}) => Math.abs(node.scrollLeft - before) > 1",
                               arg={"node": scroller.element_handle(), "before": previous})
        screenshot(page, output, report, "map-zoom", "#common-map-scroll")
        page.locator("#map-zoom").click()
        expect(page.locator("#map-zoom")).to_have_attribute("aria-pressed", "false")
        report["checks"].append("Zoom enlarges the native map within a horizontally scrollable viewport and restores the overview")

        page.goto(base + PAGE + "#place=C04&scene=K01&roads=0&walls=1&modern=1", wait_until="load")
        ready(page)
        for iteration in range(2):
            assert_place(page, places["C04"])
            for layer, visible in (("roads", False), ("walls", True), ("modern", True)):
                assert_layer(page, layer, visible)
            if iteration == 0:
                page.reload(wait_until="load")
                ready(page)
        screenshot(page, output, report, "deep-link", "#common-map-scroll")
        page.goto(base + PAGE + "#place=&scene=K03&roads=1&walls=1&modern=0", wait_until="load")
        ready(page)
        assert_scene(page, next(scene for scene in data["urban"]["clusters"] if scene["id"] == "K03"))
        page.reload(wait_until="load")
        ready(page)
        expect(page.locator("body")).to_have_attribute("data-current-place", "")
        expect(page.locator("body")).to_have_attribute("data-current-scene", "K03")
        expect(page.locator("#scene-K03")).to_be_visible()
        expect(page.locator("#place-overview")).to_be_visible()
        report["checks"].append("C04 layers and unbound K03 deep links restore on reload without inventing a map selection")

        filter_control = page.locator("#function-filter")
        before_state = page.locator("body").get_attribute("data-current-scene")
        filter_control.select_option("T04")
        expect(page.locator("[data-function-object]:visible")).to_have_count(2)
        expect(page.locator("#function-count")).to_contain_text("2")
        assert page.locator("body").get_attribute("data-current-scene") == before_state
        screenshot(page, output, report, "functions-T04", "#functions")
        link = page.locator("[data-function-object]:visible [data-open-scene]").first
        target_scene = link.get_attribute("data-open-scene")
        link.click()
        expect(page.locator("body")).to_have_attribute("data-current-scene", target_scene)
        filter_control.select_option("all")
        expect(page.locator("[data-function-object]:visible")).to_have_count(15)
        report["checks"].append("Function filter shows two T04 objects, its evidence link opens the scene, and all restores 15 objects")

        actual_downloads(page, base, output, data, info, report)
        report["checks"].append("Six actual SVG/JSON/CSV/ZIP browser downloads match public hashes and the complete offline manifest")
        nojs(page.context.browser, base, output, device, data, report)
        report["checks"].append("No-JS retains four cards, three scenes, 17 relations, two events, 15 function objects and working SVG fallback links")
        page.locator('header a[href="./prosperity-backbone-p469.html"]').click()
        page.wait_for_url("**/prosperity-backbone-p469.html*")
        expect(page.locator("#p470-entry a")).to_be_visible()
        report["checks"].append("Header returns to the previous source-frame study")
        assert not report["errors"], report["errors"]
        report["status"] = "passed"
        print(f"PASS P4.7 {device}: four map cards, three scenes, six downloads and no-JS", flush=True)
    except Exception as error:
        report.update(status="failed", failure=str(error), current_url=page.url, viewport=page.viewport_size)
        try:
            failure_image = output / f"p470-{device}-failure.png"
            page.screenshot(path=str(failure_image), animations="disabled")
            report["failure_screenshot"] = failure_image.name
        except Exception as screenshot_error:
            report["failure_screenshot_error"] = str(screenshot_error)
        raise
    finally:
        page.remove_listener("pageerror", on_error)
        (output / f"p470-{device}-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--output", default="artifacts/prosperity-city-common-p470-browser")
    args = parser.parse_args()
    output = ROOT / args.output
    server = temporary = None
    try:
        if args.base_url:
            base = args.base_url.rstrip("/") + "/"
        else:
            temporary = tempfile.TemporaryDirectory()
            folder = Path(temporary.name)
            (folder / "luoyang-city").symlink_to(ROOT / "_site", target_is_directory=True)

            class Quiet(http.server.SimpleHTTPRequestHandler):
                def log_message(self, *unused):
                    pass

            server = http.server.ThreadingHTTPServer(
                ("127.0.0.1", 0), functools.partial(Quiet, directory=folder))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{server.server_port}/luoyang-city/"
        with sync_playwright() as playwright:
            launch = {"headless": True}
            if os.environ.get("CHROMIUM_PATH"):
                launch["executable_path"] = os.environ["CHROMIUM_PATH"]
            browser = playwright.chromium.launch(**launch)
            try:
                for device, size in SIZES.items():
                    context = browser.new_context(viewport=size, is_mobile=device == "mobile",
                                                  has_touch=device == "mobile", accept_downloads=True,
                                                  reduced_motion="reduce")
                    try:
                        check_page(context.new_page(), base, output, device)
                    finally:
                        context.close()
            finally:
                browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
        if temporary:
            temporary.cleanup()


if __name__ == "__main__":
    main()
