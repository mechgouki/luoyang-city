"""Exercise P471 source maps, reviewed readings and real downloads in Chromium."""
import argparse
import csv
import datetime
import functools
import hashlib
import http.server
import io
import json
import os
import re
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from xml.etree import ElementTree as ET

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PAGE = "prosperity-city-north.html"
PREVIOUS = "prosperity-city-common.html"
DOWNLOADS = (
    "north-471/city-overview.svg", "north-471/north-detail.svg", "north-471/readings.json",
    "north-471/evidence.csv", "north-471/reuse-plan.json", "north-471/bundle-manifest.json",
    "downloads/north-471.zip",
)
SIZES = {"desktop": {"width": 1440, "height": 950}, "mobile": {"width": 390, "height": 844}}
MAPS = {"north": "north-detail-map", "overview": "north-overview-map"}


def sha(content):
    return hashlib.sha256(content).hexdigest()


def compact(text):
    return re.sub(r"\s+", "", text or "")


def ready(page):
    page.wait_for_function("document.body.dataset.northReady === '1'")


def fit(page):
    widths = page.evaluate("""({documentWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth, innerWidth: innerWidth})""")
    assert page.viewport_size
    assert all(value <= page.viewport_size["width"] + 2 for value in widths.values()), widths


def screenshot(page, output, report, stem, selector=None, *, javascript_enabled=True):
    if javascript_enabled:
        page.evaluate("document.fonts.ready")
        # Wait for native keyboard scrolling to settle, not an arbitrary delay.
        page.evaluate("""() => new Promise(resolve => {
            const boxes = [...document.querySelectorAll('[data-map-scroll]')];
            let previous = '', stable = 0;
            function sample() {
                const current = boxes.map(node => node.scrollLeft).join(',');
                stable = current === previous ? stable + 1 : 0;
                previous = current;
                if (stable >= 3) resolve(); else requestAnimationFrame(sample);
            }
            requestAnimationFrame(sample);
        })""")
    # No-JS screenshots use native locator stability; disabled rAF would hang.
    fit(page)
    target = output / f"p471-{report['device']}-{stem}.png"
    if selector:
        element = page.locator(selector)
        expect(element).to_be_visible()
        element.screenshot(path=str(target), animations="disabled")
    else:
        page.screenshot(path=str(target), animations="disabled")
    report["screenshot_sha256"][target.name] = sha(target.read_bytes())


def assert_map(page, choice):
    expect(page.locator("body")).to_have_attribute("data-current-map", choice)
    for candidate, svg in MAPS.items():
        panel = page.locator(f'[data-map-panel="{candidate}"]')
        expect(panel).to_have_count(1)
        expect(page.locator("#" + svg + " [data-feature-id]")).to_have_count(27)
        if candidate == choice:
            expect(panel).to_be_visible()
        else:
            expect(panel).to_be_hidden()


def assert_entry(page, entry):
    identifier = entry["id"]
    expect(page.locator("body")).to_have_attribute("data-current-north", identifier)
    for candidate in ("N01", "N02", "N03"):
        card = page.locator("#north-" + candidate)
        control = page.locator(f'[data-north-choice="{candidate}"]')
        expect(control).to_have_attribute("aria-pressed", str(candidate == identifier).lower())
        if candidate == identifier:
            expect(card).to_be_visible()
            assert compact(entry["name"]) in compact(card.inner_text())
            assert compact(entry["scope"]) in compact(card.inner_text())
        else:
            expect(card).to_be_hidden()
    for svg in MAPS.values():
        selected = page.locator(f'#{svg} [data-north-id].is-selected')
        assert set(selected.evaluate_all("nodes => nodes.map(node => node.dataset.northId)")) == {identifier}
        for feature in entry["feature_ids"]:
            expect(page.locator(f'#{svg} [data-feature-id="{feature}"]')).to_have_class(re.compile(r"\bis-selected\b"))


def assert_layer(page, name, visible):
    expect(page.locator("#north-layer-" + name)).to_be_checked(checked=visible)
    current = page.locator("body").get_attribute("data-current-map")
    for choice, svg in MAPS.items():
        layers = page.locator(f'#{svg} [data-city-layer="{name}"]')
        assert layers.count(), (choice, name)
        for layer in layers.all():
            own_display = layer.evaluate("node => getComputedStyle(node).display !== 'none' && !node.hidden")
            assert own_display == visible, (choice, name, own_display, visible)
            if choice == current:
                if visible:
                    expect(layer).to_be_visible()
                else:
                    expect(layer).to_be_hidden()


def assert_group(page, data, choice):
    expect(page.locator("body")).to_have_attribute("data-current-group", choice)
    for group in data["evidence_groups"]:
        panel = page.locator(f'[data-evidence-group="{group["id"]}"]')
        if choice in ("all", group["id"]):
            expect(panel).to_be_visible()
        else:
            expect(panel).to_be_hidden()
    expected = len(data["evidence"]) if choice == "all" else len(next(group for group in data["evidence_groups"] if group["id"] == choice)["evidence_ids"])
    expect(page.locator("[data-evidence-id]:visible")).to_have_count(expected)


def assert_reading(page, row):
    article = page.locator("#evidence-" + row["id"])
    expect(article).to_be_visible()
    detail = article.locator("details[data-reading-detail]")
    expect(detail).to_have_count(1)
    if detail.get_attribute("open") is None:
        detail.locator(":scope > summary").click()
    for nested in detail.locator("details").all():
        if nested.get_attribute("open") is None:
            nested.locator(":scope > summary").click()
    quote = article.locator("[data-evidence-quote]")
    expect(quote).to_have_count(1)
    expect(quote).to_be_visible()
    assert compact(quote.inner_text()) == compact(row["reading_overlay"]["quote"]), row["id"]
    text = compact(article.inner_text())
    for field in ("reading", "limit", "temporal_note"):
        if row[field]:
            assert compact(row[field]) in text, (row["id"], field)
    for variant in row["variants"]:
        assert compact(variant["reading"]) in text, row["id"]
    notes = article.locator("[data-modern-annotation]")
    expect(notes).to_have_count(len(row["reading_overlay"]["annotations"]))
    for annotation in row["reading_overlay"]["annotations"]:
        assert any(compact(annotation["quote"]) in compact(note.inner_text()) and annotation["author"] in note.inner_text() for note in notes.all())
        assert compact(annotation["quote"]) not in compact(quote.inner_text())
    if row["id"] == "NG15":
        assert compact(quote.inner_text()) != compact(row["quote"])


def assert_water_roads(page, data):
    for water in data["water_relations"]:
        card = page.locator(f'[data-water-id="{water["ref"]}"]')
        expect(card).to_be_visible()
        detail = card.locator("details")
        if detail.count() and detail.first.get_attribute("open") is None:
            detail.first.locator(":scope > summary").click()
        for field in ("quote", "reading", "limit"):
            assert compact(water[field]) in compact(card.inner_text()), (water["ref"], field)
    for road in data["roads"]:
        card = page.locator(f'[data-north-road-code="{road["code"]}"]')
        expect(card).to_be_visible()
        for field in ("code", "title", "observation", "measure_scope"):
            assert compact(road[field]) in compact(card.inner_text()), (road["code"], field)


def actual_downloads(page, base, output, data, info, report):
    saved = {}
    last_click = None
    started = time.monotonic()
    for path in DOWNLOADS:
        attempt = {"path": path, "url": base + path, "page_url": page.url,
                   "viewport": page.viewport_size, "status": "pending"}
        report["download_target"] = attempt
        report["download_attempts"].append(attempt)
        try:
            link = page.locator(f'a[download][href="{path}"], a[download][href="./{path}"]')
            expect(link).to_have_count(1)
            expect(link).to_be_visible()
            attempt["link_href"] = link.get_attribute("href")
            if last_click is not None:
                remaining = 0.15 - (time.monotonic() - last_click)
                if remaining > 0:
                    page.wait_for_timeout(remaining * 1000)
            last_click = time.monotonic()
            attempt["click_started_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            attempt["click_started_seconds"] = last_click - started
            with page.expect_download(timeout=30000) as pending:
                link.click()
            download = pending.value
            attempt["download_url"] = download.url
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
                           suggested_filename=download.suggested_filename,
                           elapsed_seconds=time.monotonic() - last_click)
        except Exception as error:
            attempt.update(status="failed", error=str(error), failure_page_url=page.url,
                           elapsed_seconds=time.monotonic() - last_click if last_click else None)
            target = output / f"p471-{report['device']}-download-failure.png"
            try:
                page.screenshot(path=str(target), animations="disabled")
                attempt["failure_screenshot"] = target.name
            except Exception as screenshot_error:
                attempt["screenshot_error"] = str(screenshot_error)
            raise
    report["download_target"] = None
    assert len(saved) == len(report["download_sha256"]) == 7
    assert ET.fromstring(saved[DOWNLOADS[0]]).get("id") == MAPS["overview"]
    assert ET.fromstring(saved[DOWNLOADS[1]]).get("id") == MAPS["north"]
    assert json.loads(saved[DOWNLOADS[2]]) == data
    rows = list(csv.DictReader(io.StringIO(saved[DOWNLOADS[3]].decode("utf-8-sig"))))
    evidence = {row["id"]: row for row in data["evidence"]}
    assert len(rows) == 16 and {row["evidence_id"] for row in rows} == set(evidence)
    for row in rows:
        original = evidence[row["evidence_id"]]
        assert row["display_quote"] == original["reading_overlay"]["quote"]
        assert row["legacy_quote"] == original["quote"]
        assert json.loads(row["annotations"]) == original["reading_overlay"]["annotations"]
        assert row["limit"] == original["limit"] and row["temporal_note"] == (original["temporal_note"] or "")
        assert row["geographic_coordinates"] == ""
    assert json.loads(saved[DOWNLOADS[4]])["expected_counts"] == data["counts"]
    manifest = json.loads(saved[DOWNLOADS[5]])
    assert manifest["source_commit"] == info["source_commit"]
    assert len(manifest["files_sha256"]) == 7
    with zipfile.ZipFile(io.BytesIO(saved[DOWNLOADS[6]])) as archive:
        members = set(archive.namelist())
        assert len(archive.namelist()) == len(members) == 9
        assert members == set(manifest["files_sha256"]) | {DOWNLOADS[5], "index.html"}
        assert archive.read(DOWNLOADS[5]) == saved[DOWNLOADS[5]]
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
        expect(page.locator("[data-north-card]:visible")).to_have_count(3)
        expect(page.locator("[data-map-panel]:visible")).to_have_count(2)
        expect(page.locator("[data-evidence-id]:visible")).to_have_count(16)
        expect(page.locator("[data-water-id]:visible")).to_have_count(5)
        expect(page.locator("[data-north-road-code]:visible")).to_have_count(3)
        for row in data["evidence"]:
            assert_reading(page, row)
        assert_water_roads(page, data)
        for svg in MAPS.values():
            expect(page.locator(f'#{svg} [data-city-layer="modern"]')).to_be_hidden()
        point = page.locator('#north-detail-map [data-north-id="N03"] circle[data-source-feature-id]').first
        point.click()
        page.wait_for_url("**/" + PAGE + "#north-N03")
        expect(page.locator("#north-N03")).to_be_visible()
        for path in DOWNLOADS:
            expect(page.locator(f'a[download][href="./{path}"], a[download][href="{path}"]')).to_be_visible()
        screenshot(page, output, report, "nojs-maps", '[data-map-scroll="north"]', javascript_enabled=False)
        screenshot(page, output, report, "nojs-N03", "#north-N03", javascript_enabled=False)
        screenshot(page, output, report, "nojs-NG15", "#evidence-NG15", javascript_enabled=False)
        report["no_javascript"] = {"status": "passed", "cards": 3, "maps": 2, "evidence": 16,
                                   "water": 5, "roads": 3, "download_links": 7,
                                   "fallback_fragment": "north-N03"}
    except Exception as error:
        report["no_javascript"] = {"status": "failed", "url": page.url,
                                   "viewport": page.viewport_size, "error": str(error)}
        try:
            page.screenshot(path=str(output / f"p471-{device}-nojs-failure.png"), animations="disabled")
        except Exception as screenshot_error:
            report["no_javascript"]["screenshot_error"] = str(screenshot_error)
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
        response = page.goto(base + PREVIOUS, wait_until="domcontentloaded")
        assert response.ok
        entry = page.locator("#p471-entry a")
        expect(entry).to_have_count(1)
        expect(entry).to_be_visible()
        entry.click()
        page.wait_for_url("**/" + PAGE + "*")
        ready(page)
        info_response = page.request.get(base + "build-info.json")
        data_response = page.request.get(base + "north-471/readings.json")
        assert info_response.ok and data_response.ok
        info, data = info_response.json(), data_response.json()
        report.update(source_commit=info["source_commit"], counts=data["counts"])
        entries = {row["id"]: row for row in data["north_entries"]}
        evidence = {row["id"]: row for row in data["evidence"]}
        assert_map(page, "north")
        assert_entry(page, entries["N01"])
        assert_group(page, data, "all")
        expect(page.locator("body")).to_have_attribute("data-current-record", "")
        for layer, visible in (("roads", True), ("walls", True), ("modern", False)):
            assert_layer(page, layer, visible)
        screenshot(page, output, report, "initial")
        screenshot(page, output, report, "map-north", '[data-map-scroll="north"]')
        report["checks"].append("Visible P470 entry opens north/N01/all with original roads and walls; modern reference is off")

        for identifier, entry_data in entries.items():
            point = page.locator(f'#north-detail-map [data-north-id="{identifier}"] circle[data-source-feature-id="{entry_data["point_feature_id"]}"]')
            expect(point).to_have_count(1)
            point.click()
            assert_entry(page, entry_data)
            screenshot(page, output, report, "card-" + identifier, "#north-" + identifier)
        for identifier, entry_data in entries.items():
            page.locator(f'[data-north-choice="{identifier}"]').click()
            assert_entry(page, entry_data)
        page.locator('[data-map-choice="overview"]').click()
        assert_map(page, "overview")
        for identifier, entry_data in entries.items():
            page.locator(f'#north-overview-map [data-north-id="{identifier}"] circle[data-source-feature-id="{entry_data["point_feature_id"]}"]').click()
            assert_entry(page, entry_data)
        screenshot(page, output, report, "map-overview", '[data-map-scroll="overview"]')
        report["checks"].append("Both source maps and all three entry controls select the same cards; N01 selects its point and five-part wall group")

        for layer in ("roads", "walls"):
            page.locator("#north-layer-" + layer).uncheck()
            assert_layer(page, layer, False)
            page.locator("#north-layer-" + layer).check()
            assert_layer(page, layer, True)
        page.locator("#north-layer-modern").check()
        assert_layer(page, "modern", True)
        page.locator('[data-map-choice="north"]').click()
        assert_map(page, "north")
        assert_layer(page, "modern", True)
        page.locator("#north-layer-modern").uncheck()
        assert_layer(page, "modern", False)
        report["checks"].append("Road, wall and modern-reference controls synchronize both map groups")

        drawing = page.locator("#north-detail-map")
        before = drawing.bounding_box()
        page.locator("#north-map-zoom").click()
        expect(page.locator("#north-map-zoom")).to_have_attribute("aria-pressed", "true")
        after = drawing.bounding_box()
        assert before and after and after["width"] > before["width"], (before, after)
        scroller = page.locator('[data-map-scroll="north"]')
        dimensions = scroller.evaluate("node => ({width: node.clientWidth, scrollWidth: node.scrollWidth})")
        assert dimensions["scrollWidth"] > dimensions["width"]
        scroller.focus()
        previous = scroller.evaluate("node => node.scrollLeft")
        page.keyboard.press("ArrowLeft" if previous > 0 else "ArrowRight")
        page.wait_for_function("({node, before}) => Math.abs(node.scrollLeft - before) > 1",
                               arg={"node": scroller.element_handle(), "before": previous})
        screenshot(page, output, report, "map-zoom", '[data-map-scroll="north"]')
        page.locator("#north-map-zoom").click()
        expect(page.locator("#north-map-zoom")).to_have_attribute("aria-pressed", "false")
        report["checks"].append("Zoom enlarges the map inside a keyboard-scrollable viewport and restores it")

        for group in data["evidence_groups"]:
            page.locator(f'[data-group-choice="{group["id"]}"]').click()
            assert_group(page, data, group["id"])
            for identifier in group["evidence_ids"]:
                assert_reading(page, evidence[identifier])
            screenshot(page, output, report, "group-" + group["id"], f'[data-evidence-group="{group["id"]}"]')
        page.locator('[data-group-choice="all"]').click()
        assert_group(page, data, "all")
        page.locator('[data-north-choice="N01"]').click()
        page.locator('#north-N01 [data-open-evidence="NG15"]').click()
        assert_group(page, data, "G02")
        expect(page.locator("body")).to_have_attribute("data-current-record", "NG15")
        expect(page.locator('#evidence-NG15 details[data-reading-detail]')).to_have_attribute("open", "")
        assert_reading(page, evidence["NG15"])
        screenshot(page, output, report, "NG15-correction", "#evidence-NG15")
        report["checks"].append("Three groups and all expose 16 original readings/limits/variants; N01 opens corrected NG15 with both Zhou annotations separated")

        expect(page.locator("[data-north-entity]")).to_have_count(16)
        expect(page.locator('[data-north-entity][data-entity-placed="true"]')).to_have_count(3)
        expect(page.locator('[data-north-entity][data-entity-placed="false"]')).to_have_count(13)
        for binding in data["entity_bindings"]:
            chip = page.locator(f'[data-north-entity="{binding["entity_id"]}"]')
            expect(chip).to_have_count(1)
            expect(chip).to_have_attribute("data-entity-placed", str(bool(binding["feature_ids"])).lower())
        assert_water_roads(page, data)
        screenshot(page, output, report, "water-roads", "#north-water")
        report["checks"].append("Sixteen entity chips retain 3 source bindings and 13 unlocated objects; five original water records and three roads remain readable")

        for place in data["common"]["places"]:
            anchor = page.locator(f'#north-overview-map [data-feature-id="{place["feature_id"]}"]')
            expect(anchor).to_have_attribute("href", re.compile(r"(?:\./)?prosperity-city-common\.html#place-" + place["id"] + r"$"))
            assert anchor.get_attribute("data-north-id") is None
        page.locator('[data-map-choice="overview"]').click()
        page.locator('#north-overview-map [data-feature-id="geo-yongning-pagoda-reference"] circle[data-source-feature-id]').click()
        page.wait_for_url("**/" + PREVIOUS + "*")
        page.wait_for_function("document.body.dataset.commonReady === '1'")
        expect(page.locator("body")).to_have_attribute("data-current-place", "C04")
        report["checks"].append("Four older building links retain their P470 cards; an actual Yongning point click returns to C04")

        fragment = "view=north&place=N01&group=G02&record=NG15&roads=0&walls=1&modern=1"
        page.goto(base + PAGE + "#" + fragment, wait_until="load")
        ready(page)
        for iteration in range(2):
            assert_map(page, "north")
            assert_entry(page, entries["N01"])
            assert_group(page, data, "G02")
            expect(page.locator("body")).to_have_attribute("data-current-record", "NG15")
            expect(page.locator('#evidence-NG15 details[data-reading-detail]')).to_have_attribute("open", "")
            for layer, visible in (("roads", False), ("walls", True), ("modern", True)):
                assert_layer(page, layer, visible)
            assert parse_qs(urlsplit(page.url).fragment) == parse_qs(fragment)
            # Inspect before any locator screenshot can scroll the record for us.
            bounds = page.locator("#evidence-NG15").bounding_box()
            viewport = page.viewport_size
            assert bounds and viewport
            assert 0 <= bounds["y"] < viewport["height"] and bounds["height"] > 0, {
                "record": "NG15", "iteration": iteration, "bounds": bounds,
                "viewport": viewport, "url": page.url}
            if iteration == 0:
                page.reload(wait_until="load")
                ready(page)
        screenshot(page, output, report, "deep-link", "#evidence-NG15")
        page.goto(base + PAGE + "#north-N03", wait_until="load")
        ready(page)
        assert_entry(page, entries["N03"])
        page.goto(base + PAGE + "#evidence-NG15", wait_until="load")
        ready(page)
        assert_group(page, data, "G02")
        expect(page.locator("body")).to_have_attribute("data-current-record", "NG15")
        assert_reading(page, evidence["NG15"])
        screenshot(page, output, report, "fallback-NG15", "#evidence-NG15")
        report["checks"].append("Combined map/place/group/record/layer state survives reload; native place and evidence fragments restore their target")

        actual_downloads(page, base, output, data, info, report)
        report["checks"].append("Seven real downloads match public hashes, corrected CSV and the complete nine-member offline ZIP")
        nojs(page.context.browser, base, output, device, data, report)
        report["checks"].append("No-JS retains two maps, three cards, all 16 readings, five waters, three roads and working native anchors")
        page.locator('header a[href="./prosperity-city-common.html"], header a[href="prosperity-city-common.html"]').click()
        page.wait_for_url("**/" + PREVIOUS + "*")
        expect(page.locator("#p471-entry a")).to_be_visible()
        report["checks"].append("Header returns to P470")
        assert not report["errors"], report["errors"]
        report["status"] = "passed"
        print(f"PASS P4.7.1 {device}: two maps, three entries, 16 readings, seven downloads and no-JS", flush=True)
    except Exception as error:
        report.update(status="failed", failure=str(error), current_url=page.url, viewport=page.viewport_size)
        try:
            failure_image = output / f"p471-{device}-failure.png"
            page.screenshot(path=str(failure_image), animations="disabled")
            report["failure_screenshot"] = failure_image.name
        except Exception as screenshot_error:
            report["failure_screenshot_error"] = str(screenshot_error)
        raise
    finally:
        page.remove_listener("pageerror", on_error)
        (output / f"p471-{device}-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--output", default="artifacts/prosperity-city-north-p471-browser")
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
