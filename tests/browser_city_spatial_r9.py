"""Exercise the R9 spatial reading experience on desktop, mobile and offline."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
from urllib.parse import urlsplit
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright
from browser_city_west_p472 import SIZES, base_url
from browser_layout import assert_loaded_viewport

ROOT = Path(__file__).resolve().parents[1]
PAGE = "luoyang-city-spatial.html"
KEY = "city_spatial_r9"
DATA = "city-spatial-r9/decisions.json"
NODES = ("palace-yongning", "baima", "sima", "jianchun")


def exercise(browser, base, device, output, expected_commit=None):
    settings = dict(viewport=SIZES[device], is_mobile=device == "mobile",
                    has_touch=device == "mobile", reduced_motion="reduce")
    report = dict(device=device, viewport=SIZES[device], checks=[], downloads={},
                  screenshots={}, errors=[], viewboxes={})
    active_page = None

    def watch(page):
        page.on("pageerror", lambda error: report["errors"].append(str(error)))

    def capture(page, label):
        name = device + "-" + label + ".png"
        raw = page.screenshot(path=output / name, animations="disabled")
        report["screenshots"][name] = hashlib.sha256(raw).hexdigest()

    def fits(page):
        assert_loaded_viewport(page, tolerance=1, report=report)

    def visible_rows(page, expected):
        target = page.locator("#decisions-table .decision-row:visible")
        expect(target).to_have_count(len(expected))
        identifiers = target.evaluate_all("rows => rows.map(row => row.id.replace(/^decision-/, ''))")
        assert identifiers == [row["id"] for row in expected], (identifiers, expected)

    with browser.new_context(**settings, accept_downloads=True) as context:
        page = context.new_page()
        active_page = page
        watch(page)
        try:
            response = context.request.get(base + "build-info.json")
            assert response.ok
            info = response.json()
            meta = info[KEY]
            data_response = context.request.get(base + DATA)
            assert data_response.ok
            data = data_response.json()
            rows = data["decisions"]
            report["source_commit"] = info["source_commit"]
            assert meta["source_commit"] == data["source_commit"] == info["source_commit"]
            if expected_commit:
                assert info["source_commit"] == expected_commit, "Browser reached another deployment"
            assert data["source_frames_registered_together"] is False
            assert data["new_historical_coordinates"] == data["new_shoreline_geometries"] == 0
            page.goto(base + PAGE, wait_until="load")
            expect(page.locator("#spatial-map")).to_be_visible()
            expect(page.locator("#decisions-table .decision-row")).to_have_count(len(rows))
            visible_rows(page, rows)
            fits(page)
            capture(page, "overview")
            report["checks"].append("The unified spatial figure and every reviewed decision load from the exact released commit")

            for node in NODES:
                page.locator("#node-filter").select_option(node)
                visible_rows(page, [row for row in rows if row["node_id"] == node])
            page.locator("#node-filter").select_option("all")
            for basis in ("source", "relation", "unknown"):
                page.locator("#basis-filter").select_option(basis)
                visible_rows(page, [row for row in rows if basis in row["evidence_classes"]])
            page.locator("#reset-filters").click()
            visible_rows(page, rows)
            chosen = rows[0]
            page.locator("#node-filter").select_option(chosen["node_id"])
            page.locator("#basis-filter").select_option(chosen["evidence_classes"][0])
            page.locator("#search").fill(chosen["id"])
            visible_rows(page, [chosen])
            page.reload(wait_until="load")
            expect(page.locator("#search")).to_have_value(chosen["id"])
            expect(page.locator("#node-filter")).to_have_value(chosen["node_id"])
            expect(page.locator("#basis-filter")).to_have_value(chosen["evidence_classes"][0])
            visible_rows(page, [chosen])
            fits(page)
            capture(page, "filtered-evidence")
            page.locator("#search").fill("NO_MATCH_R9_8675309")
            visible_rows(page, [])
            expect(page.locator("#result-count")).to_contain_text("0")
            page.locator("#reset-filters").click()
            expect(page.locator("#search")).to_have_value("")
            expect(page.locator("#node-filter")).to_have_value("all")
            expect(page.locator("#basis-filter")).to_have_value("all")
            visible_rows(page, rows)
            report["checks"].append("All four nodes and three evidence categories filter by real row IDs; combined search survives reload, and empty results reset correctly")

            svg = page.locator("#spatial-map")
            for view in ("source", *NODES, "all"):
                page.locator("#map-view").select_option(view)
                initial = svg.get_attribute("viewBox")
                assert initial
                page.locator("#zoom-in").click()
                zoomed = svg.get_attribute("viewBox")
                assert float(zoomed.split()[2]) < float(initial.split()[2]), (view, initial, zoomed)
                if view == "palace-yongning":
                    viewport = page.locator("#map-viewport")
                    page.locator("#pan-right").click()
                    page.locator("#pan-down").click()
                    moved = svg.get_attribute("viewBox")
                    assert float(moved.split()[0]) > float(zoomed.split()[0])
                    assert float(moved.split()[1]) > float(zoomed.split()[1])
                    page.locator("#reset-map").click()
                    expect(svg).to_have_attribute("viewBox", initial)
                    expect(viewport).to_have_js_property("scrollLeft", 0)
                    expect(viewport).to_have_js_property("scrollTop", 0)
                    page.locator("#zoom-in").click()
                    keyboard_start = svg.get_attribute("viewBox")
                    viewport.focus()
                    page.keyboard.press("ArrowRight")
                    page.keyboard.press("ArrowDown")
                    keyboard_moved = svg.get_attribute("viewBox")
                    assert float(keyboard_moved.split()[0]) > float(keyboard_start.split()[0])
                    assert float(keyboard_moved.split()[1]) > float(keyboard_start.split()[1])
                    report["pan_reset"] = dict(before=zoomed, buttons=moved, keyboard=keyboard_moved)
                    if device == "mobile":
                        assert svg.bounding_box()["width"] >= 700, "Local labels were shrunk into an unreadable miniature"
                        assert viewport.evaluate("el => el.scrollWidth > el.clientWidth")
                page.locator("#reset-map").click()
                expect(svg).to_have_attribute("viewBox", initial)
                page.reload(wait_until="load")
                expect(page.locator("#map-view")).to_have_value(view)
                expect(svg).to_have_attribute("viewBox", initial)
                report["viewboxes"][view] = initial
            fits(page)
            capture(page, "map-reset")
            report["checks"].append("Source and all four node windows have working zoom, button and keyboard panning, exact current-view reset and URL-restored view selection")

            for node in NODES:
                chosen = next(row for row in rows if row["node_id"] == node)
                page.goto(base + PAGE + "?node=invalid&basis=unknown&q=NO_MATCH_R9#decision-" + chosen["id"], wait_until="load")
                target = page.locator("#decision-" + chosen["id"])
                expect(target).to_be_visible()
                expect(target).to_be_in_viewport()
                page.reload(wait_until="load")
                expect(target).to_be_visible()
                fits(page)
                page.locator("#reset-filters").click()
                page.locator("#map-view").select_option(node)
                anchor = page.locator('#spatial-map a[data-decision="' + chosen["id"] + '"]').first
                anchor.focus()
                page.keyboard.press("Enter")
                assert page.evaluate("location.hash") == "#decision-" + chosen["id"]
                expect(target).to_be_visible()
            capture(page, "node-evidence")
            report["checks"].append("Each node can be opened by a shareable evidence anchor despite conflicting filters, refreshed, and reached from its SVG link using the keyboard")

            with tempfile.TemporaryDirectory() as temporary:
                for path in meta["download_files"]:
                    link = page.locator('[data-download][download][href="./' + path + '"]')
                    expect(link).to_have_count(1)
                    with page.expect_download() as event:
                        link.click()
                    raw = Path(event.value.path()).read_bytes()
                    checksum = hashlib.sha256(raw).hexdigest()
                    assert checksum == info["files_sha256"][path], path
                    report["downloads"][path] = checksum
                    if path == meta["bundle"]:
                        with ZipFile(io.BytesIO(raw)) as archive:
                            for name in archive.namelist():
                                member = PurePosixPath(name)
                                assert not member.is_absolute() and ".." not in member.parts, name
                            archive.extractall(temporary)
                assert set(report["downloads"]) == set(meta["download_files"])
                with browser.new_context(**settings, offline=True) as disconnected:
                    local = disconnected.new_page()
                    active_page = local
                    watch(local)
                    local.goto((Path(temporary) / meta.get("offline_entry", "index.html")).as_uri(), wait_until="load")
                    expect(local.locator("#spatial-map")).to_be_visible()
                    visible_rows(local, rows)
                    local.locator("#node-filter").select_option("jianchun")
                    visible_rows(local, [row for row in rows if row["node_id"] == "jianchun"])
                    chosen = next(row for row in rows if row["node_id"] == "jianchun")
                    local.locator("#search").fill(chosen["id"])
                    visible_rows(local, [chosen])
                    local.reload(wait_until="load")
                    visible_rows(local, [chosen])
                    fits(local)
                    capture(local, "offline")
            active_page = page
            report["checks"].append("Every real download matches its released SHA-256; the ZIP opens without a network and retains the complete map, evidence, filtering and reload state")

            with browser.new_context(**settings, java_script_enabled=False) as disabled:
                plain = disabled.new_page()
                active_page = plain
                watch(plain)
                plain.goto(base + PAGE + "#decision-" + rows[0]["id"], wait_until="load")
                expect(plain.locator("#spatial-map")).to_be_visible()
                visible_rows(plain, rows)
                expect(plain.locator("#decision-" + rows[0]["id"])).to_be_in_viewport()
                fits(plain)
                capture(plain, "without-javascript")
            active_page = page
            report["checks"].append("With JavaScript disabled, the full map and all source-linked decisions remain readable and native evidence anchors work")
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
    parser.add_argument("--output", default="artifacts/city-spatial-r9-browser")
    parser.add_argument("--browser-executable")
    args = parser.parse_args()
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    with base_url(args.base_url) as base, sync_playwright() as playwright:
        executable = args.browser_executable or os.environ.get("CHROMIUM_PATH")
        browser = playwright.chromium.launch(**({"executable_path": executable} if executable else {}))
        try:
            for device in SIZES:
                exercise(browser, base, device, output, args.commit)
        finally:
            browser.close()
