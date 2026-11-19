"""Exercise P4.6.8 supplementary water maps through their public entry chain."""
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
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from xml.etree import ElementTree as ET

from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PAGE = "prosperity-water-p468.html"
SVG = "{http://www.w3.org/2000/svg}"


def ready(page):
    page.wait_for_function("document.documentElement.dataset.water468Ready === 'true'")


def fit(page):
    widths = page.evaluate("({document:document.documentElement.scrollWidth, viewport:innerWidth})")
    assert widths["document"] <= widths["viewport"] + 2, widths


def active_panel(page):
    return page.locator("[data-plate-panel]:visible")


def capture_map(page, panel, output, stem):
    """Keep the actual diagram in frame, and retain an uncluttered map crop for review."""
    viewport = panel.locator(".map-viewport")
    expect(viewport).to_be_visible()
    viewport.evaluate("""async node => {
        await document.fonts.ready;
        node.scrollIntoView({block: 'start', inline: 'nearest', behavior: 'instant'});
    }""")
    bounds = viewport.bounding_box()
    size = page.viewport_size
    assert bounds and size, "The map must have a real viewport before its screenshot"
    assert -2 <= bounds["y"] <= 2, bounds
    assert bounds["y"] + bounds["height"] <= size["height"] + 2, bounds
    fit(page)
    page.screenshot(path=str(output / f"{stem}.png"), animations="disabled")
    viewport.screenshot(path=str(output / f"{stem}-map.png"), animations="disabled")


def expected_segments(plate, layer):
    if layer == "all":
        return plate["segments"]
    wanted = {"text_context"} if layer == "text" else {"older_event", "broad_survey"}
    return [segment for segment in plate["segments"] if segment["period_class"] in wanted]


def check_layer(page, plate, layer):
    expect(page.locator("#water-layer")).to_have_value(layer)
    shown = expected_segments(plate, layer)
    assert active_panel(page).locator(".water-segment:visible").count() == len(shown)
    assert page.locator("#segment-choice option").count() == max(1, len(shown))
    if not shown:
        expect(page.locator("#segment-choice")).to_be_disabled()
        expect(page.locator("#segment-detail .empty-detail")).to_be_visible()
    fit(page)
    return shown


def check_selected(page, segment):
    expect(page.locator("#segment-choice")).to_have_value(segment["id"])
    expect(page.locator("#segment-detail h3")).to_have_text(segment["label"])
    expect(page.locator("#segment-detail .detail-reading")).to_have_text(segment.get("reading", ""))
    expect(page.locator("#segment-detail .detail-limit")).to_have_text(segment.get("limit", ""))
    expect(page.locator("#segment-detail .detail-locator")).to_have_text(segment.get("locator", ""))
    expect(page.locator("#segment-detail .detail-tag").first).not_to_be_empty()
    if segment.get("quote"):
        expect(page.locator("#segment-detail .detail-quote")).to_have_text(segment["quote"])
    else:
        expect(page.locator("#segment-detail .detail-quote")).to_have_count(0)
    expect(page.locator("#segment-detail .detail-sources a")).to_have_count(len(segment["source_ids"]))
    selected = active_panel(page).locator(".water-segment.is-selected")
    expect(selected).to_have_count(1)
    expect(selected).to_have_attribute("data-segment-id", segment["id"])
    expect(selected).to_have_attribute("aria-pressed", "true")


def viewbox(map_element):
    return [float(value) for value in map_element.get_attribute("viewBox").split()]


def drag_map(page, map_element, mobile=False):
    map_element.scroll_into_view_if_needed()
    rect = map_element.bounding_box()
    assert rect and rect["width"] > 100 and rect["height"] > 100
    x, y = rect["x"] + rect["width"] * .5, rect["y"] + rect["height"] * .5
    if mobile:
        # Touch emulation exercises pointer capture and touch-action in the mobile viewport.
        session = page.context.new_cdp_session(page)
        try:
            point = {"x": x, "y": y, "id": 1, "radiusX": 6, "radiusY": 6, "force": 1}
            session.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [point]})
            for step in range(1, 5):
                session.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{**point, "x": x+step*12, "y": y+step*4}]})
            session.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        finally:
            session.detach()
    else:
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x+48, y+16, steps=5)
        page.mouse.up()


def check_nojs(browser, base, data, output, device):
    mobile = device == "mobile"
    context = browser.new_context(viewport={"width": 390 if mobile else 1280, "height": 844 if mobile else 900},
                                  java_script_enabled=False)
    try:
        page = context.new_page()
        response = page.goto(base + PAGE, wait_until="load")
        assert response.ok
        expect(page.locator("#map-tabs")).to_be_hidden()
        expect(page.locator("#map-tools")).to_be_hidden()
        expect(page.locator("#evidence-panel")).to_be_hidden()
        assert page.locator("[data-plate-panel]:visible").count() == len(data["plates"])
        all_segments = [segment for plate in data["plates"] for segment in plate["segments"]]
        assert page.locator("#evidence tbody tr:visible").count() == len(all_segments)
        for segment in all_segments:
            row = page.locator(f'[id={json.dumps("evidence-" + segment["id"])}]')
            expect(row).to_be_visible()
            text = re.sub(r"\s+", "", row.inner_text())
            for field in ("label", "quote", "locator", "reading", "limit"):
                assert re.sub(r"\s+", "", segment.get(field, "")) in text, (segment["id"], field)
            assert row.locator("a[href]").count() == len(segment["source_ids"])
        assert page.locator("#measurements tbody tr").count() > 0
        expect(page.locator("#measurements tbody tr").first).not_to_be_empty()
        fit(page)
        capture_map(page, page.locator("[data-plate-panel]").first, output, f"p468-{device}-nojs")
    finally:
        context.close()


def check_page(page, base, output, device):
    """Follow P4.6.6 → P4.6.7 → P4.6.8 and return to P4.6.6 for the full-site chain."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {"base_url": base, "device": device, "status": "running", "checks": [], "download_sha256": {}, "errors": []}
    on_error = lambda error: report["errors"].append(str(error))
    page.on("pageerror", on_error)
    try:
        response = page.goto(base + "prosperity-south-p466.html", wait_until="domcontentloaded")
        assert response.ok
        expect(page.locator("#p467-entry a")).to_have_count(1)
        page.locator("#p467-entry a").click()
        page.wait_for_url("**/prosperity-water-p467.html*")
        page.wait_for_function("document.documentElement.dataset.water467Ready === 'true'")
        expect(page.locator("#p468-entry a")).to_have_count(1)
        page.locator("#p468-entry a").click()
        page.wait_for_url("**/prosperity-water-p468.html*")
        ready(page)
        expect(page.locator("h1")).to_be_visible()
        json_response = page.request.get(base + "water-468/readings.json")
        assert json_response.ok
        data = json_response.json()
        plate_count = len(data["plates"])
        assert plate_count >= 3
        expect(page.locator("[data-plate-choice]")).to_have_count(plate_count)
        assert data == page.locator("#water-study-data").evaluate("node => JSON.parse(node.textContent)")
        assert all(plate.get("default_layer") == "all" for plate in data["plates"])
        report["map_count"] = plate_count
        report["containment_segments"] = sum(segment["relationship_type"] == "containment"
                                              for plate in data["plates"] for segment in plate["segments"])
        report["checks"].append(f"P4.6.6 → P4.6.7 → P4.6.8 entry opens {plate_count} maps, each initially showing all evidence")

        for number, plate in enumerate(data["plates"], 1):
            button = page.locator(f'[data-plate-choice={json.dumps(plate["id"])}]')
            button.click()
            expect(button).to_have_attribute("aria-pressed", "true")
            expect(active_panel(page)).to_have_count(1)
            expect(active_panel(page)).to_have_attribute("data-plate-panel", plate["id"])
            default = plate.get("default_layer", "text")
            shown = check_layer(page, plate, default)
            assert shown, f"Default layer unexpectedly blank: {plate['id']}"
            segment = shown[-1]
            page.locator("#segment-choice").select_option(segment["id"])
            check_selected(page, segment)
            state = parse_qs(urlsplit(page.url).fragment)
            assert state["map"] == [plate["id"]] and state["segment"] == [segment["id"]] and state["layer"] == [default]
            page.reload(wait_until="load")
            ready(page)
            check_selected(page, segment)
            check_layer(page, plate, default)
            capture_map(page, active_panel(page), output, f"p468-{device}-{number:02d}-{plate['id']}")

            for layer in ("text", "survey", "all"):
                page.locator("#water-layer").select_option(layer)
                check_layer(page, plate, layer)
            # Containment is a selectable relation with evidence, but never a flow arrow.
            contained = next((item for item in plate["segments"] if item["relationship_type"] == "containment"), None)
            if contained:
                page.locator("#segment-choice").select_option(contained["id"])
                check_selected(page, contained)
            # Activate an SVG route itself, independently of the list selector.
            segment = plate["segments"][-1]
            route = active_panel(page).locator(f'[data-segment-id={json.dumps(segment["id"])}]')
            route.locator(".segment-number-bg").click()
            check_selected(page, segment)
            page.locator("#full-evidence-link").click()
            assert urlsplit(page.url).fragment == "evidence-" + segment["id"]
            page.reload(wait_until="load")
            ready(page)
            assert urlsplit(page.url).fragment == "evidence-" + segment["id"], "Ordinary evidence anchors must survive reload"
            fit(page)
            report["checks"].append(f"Map {number}: default layer, list and SVG selection, three filters, map/segment reload and evidence anchor")

        page.locator('nav a[href="#measurements"]').click()
        assert urlsplit(page.url).fragment == "measurements"
        page.reload(wait_until="load")
        ready(page)
        assert urlsplit(page.url).fragment == "measurements"
        measurements = page.locator("#measurements")
        expect(measurements).to_be_visible()
        assert measurements.locator("tbody tr").count() > 0
        expect(measurements.locator("tbody tr").first).not_to_be_empty()
        fit(page)
        measurements.evaluate("node => node.scrollIntoView({block:'start', behavior:'instant'})")
        page.screenshot(path=str(output / f"p468-{device}-measurements.png"), animations="disabled")
        report["checks"].append("Reported measurements navigation and reload preserve a nonempty table without horizontal page overflow")

        # Zoom and actual movement use the first map; reset must restore its complete viewBox.
        first = data["plates"][0]
        page.locator(f'[data-plate-choice={json.dumps(first["id"])}]').click()
        page.locator("#water-layer").select_option("all")
        map_element = active_panel(page).locator("svg")
        assert viewbox(map_element) == [0, 0, 1020, 760]
        page.locator("#zoom-in").click()
        page.locator("#zoom-in").click()
        expect(page.locator("#zoom-level")).to_have_text("150%")
        zoomed = viewbox(map_element)
        assert zoomed[2] < 1020 and zoomed[3] < 760
        map_element.focus()
        map_element.press("ArrowRight")
        keyboard = viewbox(map_element)
        assert keyboard[0] > zoomed[0], "Keyboard panning did not move the viewport"
        drag_map(page, map_element, device == "mobile")
        dragged = viewbox(map_element)
        assert dragged[:2] != keyboard[:2], "Pointer/touch drag did not move the viewport"
        expect(active_panel(page).locator(".map-viewport")).not_to_have_class(re.compile(r"\bis-dragging\b"))
        page.locator("#zoom-out").click()
        expect(page.locator("#zoom-level")).to_have_text("125%")
        page.locator("#zoom-reset").click()
        assert viewbox(map_element) == [0, 0, 1020, 760]
        expect(page.locator("#zoom-out")).to_be_disabled()
        fit(page)
        report["checks"].append("Zoom, keyboard pan, touch drag on mobile or mouse drag on desktop, and full-view reset")

        # Resolve the actual visible download links, then inspect their content and published digests.
        info_response = page.request.get(base + "build-info.json")
        assert info_response.ok
        info = info_response.json()
        study = info["prosperity_water_p468"]
        resources = [study["atlas"], *study["data_files"], *["water-468/" + name for name in study["plates"]]]
        assert len(study["plates"]) == plate_count
        for path in resources:
            if path.endswith(".svg"):
                plate = next(item for item in data["plates"] if path.endswith("/"+item["id"]+".svg"))
                page.locator(f'[data-plate-choice={json.dumps(plate["id"])}]').click()
            link = page.locator(f'a[href={json.dumps(path)}]').first
            assert link.count() == 1, path
            expect(link).to_be_visible()
            result = page.request.get(link.evaluate("anchor => anchor.href"))
            assert result.ok, (path, result.status)
            body = result.body()
            digest = hashlib.sha256(body).hexdigest()
            assert digest == info["files_sha256"][path], path
            report["download_sha256"][path] = digest
            if path.endswith(".pdf"):
                assert body.startswith(b"%PDF-") and len(PdfReader(io.BytesIO(body)).pages) == plate_count
            elif path.endswith(".json"):
                json.loads(body)
            else:
                drawing = ET.fromstring(body)
                plate = next(item for item in data["plates"] if path.endswith("/"+item["id"]+".svg"))
                groups = {group.attrib["data-segment-id"]: group for group in drawing.iter(SVG+"g") if "data-segment-id" in group.attrib}
                assert len(groups) == len(plate["segments"]), "Downloaded SVG must retain the entire evidence layer"
                for segment in plate["segments"]:
                    routes = [item for item in groups[segment["id"]].iter(SVG+"path") if item.attrib.get("class") == "segment-route"]
                    assert len(routes) == 1
                    assert bool(routes[0].attrib.get("marker-end")) == (segment["relationship_type"] == "flow"), segment["id"]
                    assert not routes[0].attrib.get("marker-start"), segment["id"]
        report["checks"].append(f"Public PDF has {plate_count} pages; all JSON and SVG downloads match build-info; only flow routes carry arrows, including {report['containment_segments']} arrowless containment relations")

        check_nojs(page.context.browser, base, data, output, device)
        report["checks"].append(f"No-JS view keeps all {plate_count} maps and every evidence row, with no horizontal page overflow")
        capture_map(page, active_panel(page), output, f"p468-{device}")

        # Return through the user-facing headers, leaving P4.6.6 for the pre-existing chain.
        page.locator('header a[href$="prosperity-water-p467.html"]').click()
        page.wait_for_url("**/prosperity-water-p467.html*")
        page.wait_for_function("document.documentElement.dataset.water467Ready === 'true'")
        expect(page.locator("#p468-entry a")).to_be_visible()
        page.locator('header a[href$="prosperity-south-p466.html"]').click()
        page.wait_for_url("**/prosperity-south-p466.html")
        expect(page.locator("#p467-entry a")).to_be_visible()
        report["checks"].append("P4.6.8 header returns to P4.6.7, then P4.6.6, preserving the existing browser-test chain")
        assert not report["errors"], report["errors"]
        report["status"] = "passed"
        print(f"PASS P4.6.8 {device}: {plate_count} maps, layers, deep links, zoom/pan, downloads and no-JS evidence", flush=True)
    except Exception as error:
        report["status"] = "failed"
        report["failure"] = str(error)
        raise
    finally:
        page.remove_listener("pageerror", on_error)
        (output / f"p468-{device}-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--output", default="artifacts/prosperity-water-p468-browser")
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

            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=folder))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            server_started = True
            base = f"http://127.0.0.1:{server.server_port}/luoyang-city/"
        with sync_playwright() as playwright:
            launch = {"headless": True}
            if os.environ.get("CHROMIUM_PATH"):
                launch["executable_path"] = os.environ["CHROMIUM_PATH"]
            browser = playwright.chromium.launch(**launch)
            try:
                for device, size in (("desktop", {"width":1440,"height":950}), ("mobile", {"width":390,"height":844})):
                    context = browser.new_context(viewport=size, is_mobile=device=="mobile", has_touch=device=="mobile")
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
