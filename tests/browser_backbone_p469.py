"""Exercise P4.6.9 maps, source contexts and real downloads in desktop/mobile browsers."""
import argparse
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
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PAGE = "prosperity-backbone-p469.html"
MAPS = ("frame-06a", "frame-qian2018")
SVG = "{http://www.w3.org/2000/svg}"


def ready(page):
    page.wait_for_function("document.body.dataset.backboneReady === '1'")


def compact(text):
    return re.sub(r"\s+", "", text or "")


def fit(page, output, stem):
    """Measure the rendered page width, preserving evidence for any overflow."""
    viewport = page.viewport_size
    assert viewport, "A configured viewport is required"
    widths = page.evaluate("""({documentWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth, innerWidth: innerWidth})""")
    widths["viewportWidth"] = viewport["width"]
    if all(widths[name] <= viewport["width"] + 2
           for name in ("documentWidth", "clientWidth", "innerWidth")):
        return
    offenders = page.evaluate("""limit => [...document.body.querySelectorAll('*')]
        .filter(node => node instanceof HTMLElement && node.getClientRects().length)
        .map(node => {
            const r = node.getBoundingClientRect(), s = getComputedStyle(node);
            return {tag: node.tagName, id: node.id, className: node.className,
                x: r.x, right: r.right, width: r.width, scrollWidth: node.scrollWidth,
                clientWidth: node.clientWidth, overflowX: s.overflowX,
                text: (node.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 140)};
        }).filter(item => item.x < -2 || item.right > limit + 2 ||
            item.overflowX === 'visible' && item.scrollWidth > item.clientWidth + 2)
        .slice(0, 20)""", viewport["width"])
    diagnostic = {"url": page.url, "widths": widths, "overflow_elements": offenders}
    try:
        page.screenshot(path=str(output / f"{stem}.png"), animations="disabled")
    except Exception as error:
        diagnostic["screenshot_error"] = str(error)
    (output / f"{stem}.json").write_text(
        json.dumps(diagnostic, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raise AssertionError(f"P469 page exceeds viewport: {widths}")


def panel(page, map_id):
    return page.locator(f"#map-{map_id}")


def choose_map(page, map_id):
    button = page.locator(f'[data-map-choice="{map_id}"]')
    expect(button).to_be_visible()
    button.click()
    expect(button).to_have_attribute("aria-pressed", "true")
    for candidate in MAPS:
        if candidate == map_id:
            expect(panel(page, candidate)).to_be_visible()
        else:
            expect(panel(page, candidate)).to_be_hidden()
    assert parse_qs(urlsplit(page.url).fragment).get("map") == [map_id]


def capture_map(page, map_id, output, stem, *, javascript_enabled=True):
    """Capture the full map viewport, not just its surrounding caption or controls."""
    map_panel = panel(page, map_id)
    viewport = map_panel.locator(".map-viewport")
    expect(viewport).to_be_visible()
    expect(viewport.locator(f'svg[id="{map_id}"]')).to_be_visible()
    if javascript_enabled:
        viewport.evaluate("""async node => {
            await document.fonts.ready;
            node.scrollIntoView({block: 'start', inline: 'nearest', behavior: 'instant'});
            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            const r = node.getBoundingClientRect();
            if (r.height <= innerHeight && r.bottom > innerHeight) {
                window.scrollBy({top: r.bottom - innerHeight, behavior: 'instant'});
                await new Promise(resolve => requestAnimationFrame(resolve));
            }
        }""")
    else:
        viewport.scroll_into_view_if_needed()
        viewport.evaluate("""node => {
            const r = node.getBoundingClientRect();
            if (r.height <= innerHeight && r.bottom > innerHeight)
                window.scrollBy({top: r.bottom - innerHeight, behavior: 'instant'});
        }""")
    bounds, size = viewport.bounding_box(), page.viewport_size
    assert bounds and size
    assert bounds["x"] >= -2 and bounds["y"] >= -2, bounds
    assert bounds["x"] + bounds["width"] <= size["width"] + 2, bounds
    assert bounds["y"] + bounds["height"] <= size["height"] + 2, bounds
    svg_bounds = viewport.locator("svg").bounding_box()
    assert svg_bounds and svg_bounds["width"] > 100 and svg_bounds["height"] > 100
    assert svg_bounds["x"] >= bounds["x"] - 2, (bounds, svg_bounds)
    assert svg_bounds["y"] >= bounds["y"] - 2, (bounds, svg_bounds)
    assert svg_bounds["x"] + svg_bounds["width"] <= bounds["x"] + bounds["width"] + 2, (bounds, svg_bounds)
    assert svg_bounds["y"] + svg_bounds["height"] <= bounds["y"] + bounds["height"] + 2, (bounds, svg_bounds)
    fit(page, output, stem + "-overflow")
    page.screenshot(path=str(output / f"{stem}.png"), animations="disabled")
    viewport.screenshot(path=str(output / f"{stem}-map.png"), animations="disabled")
    return {"viewport": bounds, "svg": svg_bounds}


def context_label(data, feature_id):
    features = next(item for item in data["frames"] if item["id"] == "frame-06a")["feature_summary"]
    label = next(item["label"] for item in features if item["id"] == feature_id)
    return label.replace("位置参考", "").replace("图示残段", "")


def check_zoom(page, map_id, mobile):
    """Use the visible zoom button and native wheel/touch scrolling, then restore."""
    viewport = panel(page, map_id).locator(".map-viewport")
    drawing = viewport.locator("svg")
    initial = drawing.bounding_box()
    assert initial
    native_mark = drawing.locator("[data-source-kind]").first
    before_mark = native_mark.bounding_box()
    assert before_mark
    zoom = page.locator(f'[data-zoom="{map_id}"]')
    zoom.click()
    expect(zoom).to_have_attribute("aria-pressed", "true")
    expect(viewport).to_have_class(re.compile(r"\bis-zoomed\b"))
    enlarged = drawing.bounding_box()
    assert enlarged and enlarged["width"] > initial["width"] * 1.5
    enlarged_mark = native_mark.bounding_box()
    assert enlarged_mark and max(enlarged_mark["width"], enlarged_mark["height"]) > \
        max(before_mark["width"], before_mark["height"]) * 1.5, "Zoom must enlarge source geometry, not only its SVG box"
    viewport.scroll_into_view_if_needed()
    bounds, size = viewport.bounding_box(), page.viewport_size
    assert bounds and size
    left, right = max(0, bounds["x"]), min(size["width"], bounds["x"] + bounds["width"])
    top, bottom = max(0, bounds["y"]), min(size["height"], bounds["y"] + bounds["height"])
    assert right - left > 100 and bottom - top > 50
    x, y = left + (right - left) * .75, top + (bottom - top) * .5
    if mobile:
        session = page.context.new_cdp_session(page)
        try:
            point = {"x": x, "y": y, "id": 1, "radiusX": 5, "radiusY": 5, "force": 1}
            session.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [point]})
            for step in range(1, 6):
                session.send("Input.dispatchTouchEvent", {
                    "type": "touchMove", "touchPoints": [{**point, "x": x - step * 25}]})
            session.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        finally:
            session.detach()
    else:
        page.mouse.move(x, y)
        page.mouse.wheel(320, 0)
    page.wait_for_function("id => document.querySelector(`[data-map-scroll='${id}']`).scrollLeft > 0", arg=map_id)
    zoom.click()
    expect(zoom).to_have_attribute("aria-pressed", "false")
    expect(viewport).not_to_have_class(re.compile(r"\bis-zoomed\b"))
    restored = drawing.bounding_box()
    assert restored and abs(restored["width"] - initial["width"]) <= 2


def check_context(page, data, feature_id):
    """Check only the active context article, including the exact assigned evidence."""
    navigation = next(item for item in data["water_evidence_navigation"]
                      if item["mapped_feature_id"] == feature_id)
    expect(page.locator("#anchor-choice")).to_have_value(feature_id)
    expect(page.locator("#context-heading")).to_contain_text(context_label(data, feature_id))
    article = page.locator(f"#context-{feature_id}")
    expect(article).to_be_visible()
    for other in data["water_evidence_navigation"]:
        if other["mapped_feature_id"] != feature_id:
            expect(page.locator(f'#context-{other["mapped_feature_id"]}')).to_be_hidden()
    text = compact(article.inner_text())
    assert compact(navigation["limit"]) in text, feature_id
    relations = {relation["ref"]: relation for relation in data["current_relations"]}
    hrefs = set(article.locator("a[href]").evaluate_all("nodes => nodes.map(node => node.href)"))
    for ref in navigation["evidence_refs"]:
        relation = relations[ref]
        for field in ("label", "quote", "limit"):
            assert compact(relation.get(field)) in text, (feature_id, ref, field)
        # The browser normalizes both ./ prefixes and non-ASCII path encoding.
        expected = page.evaluate("values => values.map(value => new URL(value, location.href).href)",
                                [relation["page"], *[source["url"] for source in relation["sources"]]])
        assert expected[0] in hrefs, (feature_id, ref, "map link")
        for source, canonical_url in zip(relation["sources"], expected[1:]):
            assert canonical_url in hrefs, (feature_id, ref, source["id"])
    assert parse_qs(urlsplit(page.url).fragment).get("anchor") == [feature_id]
    return navigation["evidence_refs"]


def download_paths(study):
    """Resolve the build manifest's actual deliverables, including all audit JSON."""
    resources = set()

    def collect(value):
        if isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
        elif isinstance(value, str) and re.search(r"\.(pdf|svg|json|zip)$", value):
            if "/" not in value:
                value = "backbone-469/" + value
            resources.add(value)

    collect(study)
    return sorted(resources)


def check_downloads(page, base, output, device, data, report):
    response = page.request.get(base + "build-info.json")
    assert response.ok
    info = response.json()
    resources = download_paths(info["prosperity_backbone_p469"])
    assert len([path for path in resources if path.endswith(".pdf")]) == 1, resources
    assert len([path for path in resources if path.endswith(".svg")]) == 2, resources
    assert len([path for path in resources if path.endswith(".zip")]) == 1, resources
    assert any(path.endswith("/readings.json") for path in resources), resources
    folder = output / "downloads" / device
    folder.mkdir(parents=True, exist_ok=True)
    for path in resources:
        if path.endswith(".svg"):
            choose_map(page, Path(path).stem)
        link = page.locator(f'a[href={json.dumps(path)}],a[href={json.dumps("./" + path)}]').first
        expect(link).to_be_visible()
        with page.expect_download() as pending:
            link.click()
        downloaded = pending.value
        assert downloaded.failure() is None, (path, downloaded.failure())
        saved = folder / Path(path).name
        downloaded.save_as(saved)
        body = saved.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        assert digest == info["files_sha256"][path], path
        report["download_sha256"][path] = digest
        if path.endswith(".pdf"):
            assert body.startswith(b"%PDF-")
            assert len(PdfReader(io.BytesIO(body)).pages) == 2
        elif path.endswith(".json"):
            parsed = json.loads(body)
            if path.endswith("/readings.json"):
                assert parsed == data
        elif path.endswith(".svg"):
            drawing = ET.fromstring(body)
            assert drawing.tag == SVG + "svg"
            assert drawing.attrib.get("viewBox"), path
            assert drawing.attrib.get("id") == Path(path).stem, path
            assert any(element.tag in {SVG + tag for tag in
                       ("path", "line", "polyline", "polygon", "image", "circle")}
                       for element in drawing.iter()), path
        else:
            with zipfile.ZipFile(io.BytesIO(body)) as archive:
                names = archive.namelist()
                assert any(name.endswith("index.html") for name in names), names
                for resource in resources:
                    if resource.endswith((".svg", ".json")):
                        matches = [name for name in names if Path(name).name == Path(resource).name]
                        assert len(matches) == 1, (resource, matches)
                        assert hashlib.sha256(archive.read(matches[0])).hexdigest() == info["files_sha256"][resource]
    return resources


def check_nojs(browser, base, data, output, device):
    mobile = device == "mobile"
    context = browser.new_context(
        viewport={"width": 390 if mobile else 1440, "height": 844 if mobile else 950},
        java_script_enabled=False, accept_downloads=True)
    try:
        page = context.new_page()
        response = page.goto(base + PAGE, wait_until="load")
        assert response.ok
        for map_id in MAPS:
            expect(panel(page, map_id)).to_be_visible()
            capture_map(page, map_id, output, f"p469-{device}-nojs-{map_id}", javascript_enabled=False)
        expect(panel(page, "frame-06a").locator("#modern-river-469")).to_be_hidden()
        for navigation in data["water_evidence_navigation"]:
            article = page.locator(f'#context-{navigation["mapped_feature_id"]}')
            expect(article).to_be_visible()
            assert compact(navigation["limit"]) in compact(article.inner_text())
        for water in data["current_water_ledger"]:
            row = page.locator(f'#water-{water["id"]}')
            expect(row).to_be_visible()
            assert compact(water["name"]) in compact(row.inner_text()), water["id"]
        expect(page.locator("#current-i09")).to_contain_text(data["corrected_current_I09"]["quote"])
        expect(page.locator("#unknowns")).to_be_visible()
        fit(page, output, f"p469-{device}-nojs-overflow")
    finally:
        context.close()


def check_page(page, base, output, device):
    """Enter through P468 and finish by returning through the P469 header."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {"base_url": base, "device": device, "status": "running", "checks": [],
              "download_sha256": {}, "map_bounds": {}, "contexts": {}, "errors": []}
    on_error = lambda error: report["errors"].append(str(error))
    page.on("pageerror", on_error)
    try:
        response = page.goto(base + "prosperity-water-p468.html", wait_until="domcontentloaded")
        assert response.ok
        entry = page.locator("#p469-entry a")
        expect(entry).to_have_count(1)
        expect(entry).to_be_visible()
        entry.click()
        page.wait_for_url("**/" + PAGE + "*")
        ready(page)
        expect(page.locator("h1")).to_be_visible()
        report["checks"].append("P468 visible entry actually opens P469")
        response = page.request.get(base + "backbone-469/readings.json")
        assert response.ok
        data = response.json()
        assert data["version"] == "P4.6.9"
        assert len(data["water_evidence_navigation"]) == 9
        assert len(data["current_water_ledger"]) == 34

        for map_id in MAPS:
            choose_map(page, map_id)
            report["map_bounds"][map_id] = capture_map(
                page, map_id, output, f"p469-{device}-{map_id}")
            page.reload(wait_until="load")
            ready(page)
            expect(panel(page, map_id)).to_be_visible()
            assert parse_qs(urlsplit(page.url).fragment).get("map") == [map_id]
            check_zoom(page, map_id, device == "mobile")
            toggle = page.locator("#modern-river-toggle")
            if map_id == "frame-06a":
                expect(toggle).to_be_visible()
                expect(toggle).not_to_be_checked()
                modern = panel(page, map_id).locator("#modern-river-469")
                expect(modern).to_be_hidden()
                expect(modern).to_have_attribute("data-period", "1997/1999")
                toggle.check()
                expect(modern).to_be_visible()
                capture_map(page, map_id, output, f"p469-{device}-{map_id}-modern-on")
                toggle.uncheck()
                expect(modern).to_be_hidden()
            else:
                assert not toggle.is_visible() or toggle.is_disabled(), "The Qian frame must not imply it shares the modern-river overlay"
                expect(panel(page, map_id).locator("#modern-river-469")).to_have_count(0)
            report["checks"].append(f"{map_id}: real tab, complete map screenshot, reload, zoom/native scroll/reset and modern-river scope")

        # A real SVG marker click and a separate list choice must show different,
        # correctly sourced contexts. This cannot pass by finding hidden static text.
        choose_map(page, "frame-06a")
        for feature_id in ("geo-daxia-gate", "geo-qianqiu-gate"):
            marker = panel(page, "frame-06a").locator(f'a[data-context-id="{feature_id}"]')
            expect(marker).to_be_visible()
            marker.locator("circle").click()
            report["contexts"][feature_id] = check_context(page, data, feature_id)
            fit(page, output, f"p469-{device}-{feature_id}-overflow")
            page.locator("#context-details").screenshot(
                path=str(output / f"p469-{device}-{feature_id}-context.png"), animations="disabled")
        feature_id = "geo-guangmo-gate"
        page.locator("#anchor-choice").select_option(feature_id)
        report["contexts"][feature_id] = check_context(page, data, feature_id)
        page.reload(wait_until="load")
        ready(page)
        check_context(page, data, feature_id)
        report["checks"].append("Daxia and Qianqiu SVG markers, Guangmo list choice and reload show only their assigned water evidence")

        page.goto(base + PAGE + "#map=frame-06a&anchor=geo-daxia-gate&water=W20", wait_until="load")
        ready(page)
        check_context(page, data, "geo-daxia-gate")
        state = parse_qs(urlsplit(page.url).fragment)
        assert state.get("map") == ["frame-06a"] and state.get("water") == ["W20"]
        for water_id in ("W20", "W21"):
            record = next(water for water in data["current_water_ledger"] if water["id"] == water_id)
            assert "P467/inner/I09" not in record["current_refs"]
            row = page.locator(f"#water-{water_id}")
            expect(row).to_be_visible()
            assert compact(record["name"]) in compact(row.inner_text())
        expect(page.locator("#current-i09")).to_contain_text(data["corrected_current_I09"]["quote"])
        page.reload(wait_until="load")
        ready(page)
        assert parse_qs(urlsplit(page.url).fragment).get("water") == ["W20"]
        check_context(page, data, "geo-daxia-gate")
        page.locator('a[href="#source-method"]').first.click()
        assert urlsplit(page.url).fragment == "source-method"
        expect(page.locator("#source-method")).to_be_visible()
        expect(page.locator("#unknowns")).to_be_visible()
        page.reload(wait_until="load")
        ready(page)
        assert urlsplit(page.url).fragment == "source-method"
        fit(page, output, f"p469-{device}-deep-link-overflow")
        report["checks"].append("Combined map/anchor/W20 deep link, W20/W21 correction and ordinary source-method anchor survive reload")

        resources = check_downloads(page, base, output, device, data, report)
        report["checks"].append(f"Actual browser downloads: two-page PDF, two SVGs, offline ZIP and all manifest JSON; {len(resources)} matching hashes")
        check_nojs(page.context.browser, base, data, output, device)
        report["checks"].append("No-JS keeps both full maps, nine source contexts, 34 water rows, I09 correction and unknown boundaries")

        back = page.locator('header a[href$="prosperity-water-p468.html"]').first
        expect(back).to_be_visible()
        back.click()
        page.wait_for_url("**/prosperity-water-p468.html*")
        expect(page.locator("#p469-entry a")).to_be_visible()
        report["checks"].append("P469 header returns to P468")
        assert not report["errors"], report["errors"]
        report["status"] = "passed"
        print(f"PASS P4.6.9 {device}: two source frames, context interactions, downloads and no-JS", flush=True)
    except Exception as error:
        report["status"] = "failed"
        report["failure"] = str(error)
        raise
    finally:
        page.remove_listener("pageerror", on_error)
        (output / f"p469-{device}-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--output", default="artifacts/prosperity-backbone-p469-browser")
    args = parser.parse_args()
    output = ROOT / args.output
    server = temporary = None
    server_started = False
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
            server_started = True
            base = f"http://127.0.0.1:{server.server_port}/luoyang-city/"
        with sync_playwright() as playwright:
            launch = {"headless": True}
            if os.environ.get("CHROMIUM_PATH"):
                launch["executable_path"] = os.environ["CHROMIUM_PATH"]
            browser = playwright.chromium.launch(**launch)
            try:
                for device, size in (("desktop", {"width": 1440, "height": 950}),
                                     ("mobile", {"width": 390, "height": 844})):
                    context = browser.new_context(viewport=size, is_mobile=device == "mobile",
                                                  has_touch=device == "mobile", accept_downloads=True)
                    try:
                        check_page(context.new_page(), base, output, device)
                    finally:
                        context.close()
            finally:
                browser.close()
    finally:
        if server:
            if server_started:
                server.shutdown()
            server.server_close()
        if temporary:
            temporary.cleanup()


if __name__ == "__main__":
    main()
