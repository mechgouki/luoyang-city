"""Exercise the R10 atlas on desktop, mobile, without JavaScript and offline.

The browser obtains build metadata, evidence and downloads from the requested
deployment. Downloads are real browser downloads, checked against released
hashes before the ZIP is opened with all network access disabled.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
from urllib.parse import parse_qs, urlsplit
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader
from browser_city_west_p472 import SIZES, base_url
from browser_layout import assert_loaded_viewport

ROOT = Path(__file__).resolve().parents[1]
PAGE = "luoyang-city-layout.html"
KEY = "city_layout_r10"
DATA = "city-layout-r10/atlas.json"
REGIONS = ["R" + str(number).zfill(2) for number in range(1, 12)]
GROUPS = {
    "decisions": ("decision-row", "decision-", "decision-count"),
    "coverage": ("coverage-row", "entity-", "coverage-count"),
    "networks": ("network-row", "network-", "network-count"),
    "gaps": ("gap-card", "gap-", "gap-count"),
}


def expected_rows(data, group, region="all", basis="all", query=""):
    result = []
    for row in data[group]:
        membership = row.get("region_ids", [row["region_id"]] if "region_id" in row else ["register"])
        region_match = region == "all" or region in membership or "all" in membership
        basis_match = basis == "all" or row["basis"] == basis
        query_match = not query or query.lower() in json.dumps(row, ensure_ascii=False).lower()
        if region_match and basis_match and query_match:
            result.append(row)
    return result


def exercise(browser, base, device, output, expected_commit=None):
    settings = dict(viewport=SIZES[device], is_mobile=device == "mobile", has_touch=device == "mobile",
                    reduced_motion="reduce")
    report = dict(device=device, viewport=SIZES[device], checks=[], downloads={}, screenshots={}, errors=[], maps={})
    active = None

    def watch(page):
        page.on("pageerror", lambda error: report["errors"].append(str(error)))

    def capture(page_or_element, label):
        name = device + "-" + label + ".png"
        raw = page_or_element.screenshot(path=output / name, animations="disabled")
        report["screenshots"][name] = hashlib.sha256(raw).hexdigest()

    def fits(page):
        return assert_loaded_viewport(page, tolerance=1, report=report)

    def open_tables(page):
        for selector in ("#coverage details.table-fold", "#networks details.table-fold"):
            element = page.locator(selector)
            if element.count() and element.get_attribute("open") is None:
                element.locator(":scope > summary").click()

    def check_rows(page, data, *, region="all", basis="all", query="", counts=True):
        for group, (class_name, prefix, counter) in GROUPS.items():
            expected = expected_rows(data, group, region, basis, query)
            rows = page.locator("." + class_name + ":visible")
            expect(rows).to_have_count(len(expected))
            identifiers = rows.evaluate_all("nodes => nodes.map(node => node.id)")
            assert identifiers == [prefix + row["id"] for row in expected], (group, region, basis, query, identifiers)
            if counts:
                expect(page.locator("#" + counter)).to_have_attribute("data-visible-count", str(len(expected)))

    def check_sheets(page, region):
        expected = REGIONS if region == "all" else [] if region == "register" else [region]
        visible = page.locator(".region-sheet:visible")
        expect(visible).to_have_count(len(expected))
        assert visible.evaluate_all("nodes => nodes.map(node => node.id)") == ["region-" + rid for rid in expected]
        expect(page.locator("#city-layout-overview")).to_be_visible()

    with browser.new_context(**settings, accept_downloads=True) as context:
        page = context.new_page()
        active = page
        watch(page)
        try:
            response = context.request.get(base + "build-info.json")
            assert response.ok
            info, data_response = response.json(), context.request.get(base + DATA)
            assert data_response.ok
            data, meta = data_response.json(), info[KEY]
            assert info["source_commit"] == data["source_commit"] == meta["source_commit"]
            if expected_commit:
                assert info["source_commit"] == expected_commit, "Browser reached a different deployment"
            report["source_commit"] = info["source_commit"]
            assert len(data["coverage"]) == 339 and len(data["networks"]) == 118
            assert data["source_frames_registered_together"] is False
            assert data["new_historical_coordinates"] == data["new_shoreline_geometries"] == data["evidence_grade_upgrades"] == 0

            page.goto(base + PAGE, wait_until="load")
            expect(page.locator("#city-layout-overview")).to_be_visible()
            fits(page)
            capture(page, "entry")
            open_tables(page)
            check_rows(page, data)
            check_sheets(page, "all")
            report["checks"].append("All twelve inline figures, 339 original objects and 118 original road/water records load from the released commit")

            for region in [*REGIONS, "register", "all"]:
                page.locator("#region-select").select_option(region)
                check_sheets(page, region)
                check_rows(page, data, region=region)
            for basis in ("source", "relation", "interpretation", "unknown"):
                page.locator("#basis-filter").select_option(basis)
                check_rows(page, data, basis=basis)
            page.locator("#clear-filters").click()
            chosen = data["decisions"][0]
            page.locator("#region-select").select_option(chosen["region_id"])
            page.locator("#basis-filter").select_option(chosen["basis"])
            page.locator("#search").fill(chosen["id"])
            check_rows(page, data, region=chosen["region_id"], basis=chosen["basis"], query=chosen["id"])
            query = parse_qs(urlsplit(page.url).query)
            assert query["region"] == [chosen["region_id"]] and query["basis"] == [chosen["basis"]] and query["q"] == [chosen["id"]]
            page.reload(wait_until="load")
            open_tables(page)
            expect(page.locator("#region-select")).to_have_value(chosen["region_id"])
            expect(page.locator("#basis-filter")).to_have_value(chosen["basis"])
            expect(page.locator("#search")).to_have_value(chosen["id"])
            check_rows(page, data, region=chosen["region_id"], basis=chosen["basis"], query=chosen["id"])
            fits(page)
            page.locator("#decision-" + chosen["id"]).scroll_into_view_if_needed()
            capture(page, "restored-filter")
            page.locator("#search").fill("NO_MATCH_R10_8675309")
            check_rows(page, data, region=chosen["region_id"], basis=chosen["basis"], query="NO_MATCH_R10_8675309")
            page.locator("#clear-filters").click()
            expect(page.locator("#search")).to_have_value("")
            expect(page.locator("#basis-filter")).to_have_value("all")
            expect(page.locator("#region-select")).to_have_value("all")
            check_rows(page, data)
            check_sheets(page, "all")
            report["checks"].append("All region and basis filters match original record IDs and counters; combined query restores from URL, empty results and reset work")

            for target in ("overview", *REGIONS):
                region = "all" if target == "overview" else target
                page.locator("#region-select").select_option(region)
                viewport = page.locator('.map-viewport[data-map-id="' + target + '"]')
                svg = viewport.locator("svg")
                viewport.scroll_into_view_if_needed()
                initial = svg.get_attribute("viewBox")
                assert initial and initial == svg.get_attribute("data-original-viewbox")

                def button(action):
                    return page.locator('[data-map-target="' + target + '"][data-action="' + action + '"]')

                button("zoom-in").click()
                zoomed = svg.get_attribute("viewBox")
                assert float(zoomed.split()[2]) < float(initial.split()[2]), target
                button("zoom-out").click()
                assert float(svg.get_attribute("viewBox").split()[2]) > float(zoomed.split()[2]), target
                button("zoom-in").click()
                zoomed = svg.get_attribute("viewBox")
                button("pan-right").click()
                button("pan-down").click()
                moved = svg.get_attribute("viewBox")
                assert float(moved.split()[0]) > float(zoomed.split()[0]) and float(moved.split()[1]) > float(zoomed.split()[1]), target
                button("pan-left").click()
                button("pan-up").click()
                back = svg.get_attribute("viewBox")
                assert all(abs(float(a) - float(b)) < .01 for a, b in zip(back.split(), zoomed.split(), strict=True)), target
                viewport.focus()
                page.keyboard.press("ArrowRight")
                keyboard_moved = svg.get_attribute("viewBox")
                assert float(keyboard_moved.split()[0]) > float(back.split()[0]), target
                button("reset").click()
                expect(svg).to_have_attribute("viewBox", initial)
                expect(viewport).to_have_js_property("scrollLeft", 0)
                expect(viewport).to_have_js_property("scrollTop", 0)
                if device == "mobile":
                    assert svg.bounding_box()["width"] >= 700, "Map labels were reduced to an unreadable mobile thumbnail"
                    assert viewport.evaluate("element => element.scrollWidth > element.clientWidth")
                    if target == "overview":
                        viewport.hover()
                        page.mouse.wheel(540, 0)
                        page.wait_for_function("document.querySelector('.map-viewport[data-map-id=overview]').scrollLeft > 0")
                        report["mobile_native_scroll"] = viewport.evaluate("element => element.scrollLeft")
                        capture(viewport, "overview-scrolled")
                        button("reset").click()
                        expect(viewport).to_have_js_property("scrollLeft", 0)
                        expect(svg).to_have_attribute("viewBox", initial)
                fits(page)
                capture(viewport, "map-" + target)
                report["maps"][target] = dict(original=initial, zoomed=zoomed, panned=moved, keyboard=keyboard_moved)
            page.reload(wait_until="load")
            expect(page.locator("#region-select")).to_have_value("R11")
            check_sheets(page, "R11")
            expect(page.locator('#region-map-R11')).to_have_attribute("viewBox", report["maps"]["R11"]["original"])
            report["checks"].append("All twelve maps support zoom, four-direction buttons, keyboard panning and exact reset; each has an actual viewport screenshot")

            for region in REGIONS:
                chosen = next(row for row in data["decisions"] if row["region_id"] == region)
                page.goto(base + PAGE + "?region=register&basis=source&q=NO_MATCH_R10#decision-" + chosen["id"], wait_until="load")
                target = page.locator("#decision-" + chosen["id"])
                expect(target).to_be_visible()
                expect(target).to_be_in_viewport()
                expect(page.locator("#search")).to_have_value("")
                expect(page.locator("#basis-filter")).to_have_value("all")
                page.reload(wait_until="load")
                expect(target).to_be_visible()
                page.locator("#clear-filters").click()
                page.locator("#region-select").select_option(region)
                anchor = page.locator('#region-map-' + region + ' a[data-decision="' + chosen["id"] + '"]').first
                anchor.focus()
                page.keyboard.press("Enter")
                expect(target).to_be_visible()
                expect(target).to_be_in_viewport()
                assert page.evaluate("location.hash") == "#decision-" + chosen["id"]
            for group, prefix in (("coverage", "entity-"), ("networks", "network-"), ("gaps", "gap-")):
                record = data[group][0]
                page.goto(base + PAGE + "?region=register&basis=source&q=NO_MATCH_R10#" + prefix + record["id"], wait_until="load")
                target = page.locator("#" + prefix + record["id"])
                expect(target).to_be_visible()
                expect(target).to_be_in_viewport()
            page.goto(base + PAGE + "?region=register&basis=unknown&q=NO_MATCH_R10#region-R03", wait_until="load")
            expect(page.locator("#region-R03")).to_be_visible()
            expect(page.locator("#region-R03")).to_be_in_viewport()
            fits(page)
            capture(page, "deep-link")
            report["checks"].append("Each regional decision, object, road/water row, gap and region anchor overrides conflicting filters and reveals collapsed evidence; map links work by keyboard")

            with tempfile.TemporaryDirectory() as temporary:
                for path in meta["download_files"]:
                    link = page.locator('a[data-download="' + path + '"][download]')
                    expect(link).to_have_count(1)
                    with page.expect_download() as event:
                        link.click()
                    downloaded = event.value
                    assert downloaded.failure() is None, (path, downloaded.failure())
                    raw = Path(downloaded.path()).read_bytes()
                    checksum = hashlib.sha256(raw).hexdigest()
                    assert checksum == info["files_sha256"][path], path
                    report["downloads"][path] = checksum
                    if path.endswith(".pdf"):
                        actual_pdf = PdfReader(io.BytesIO(raw))
                        assert len(actual_pdf.pages) == 13
                        assert all(any("\u3400" <= char <= "\u9fff" for char in pdf_page.extract_text()) for pdf_page in actual_pdf.pages)
                        report["pdf_pages"] = len(actual_pdf.pages)
                    if path == meta["bundle"]:
                        with ZipFile(io.BytesIO(raw)) as archive:
                            for name in archive.namelist():
                                member = PurePosixPath(name)
                                assert not member.is_absolute() and ".." not in member.parts and "\\" not in name
                            archive.extractall(temporary)
                assert len(report["downloads"]) == 21 and set(report["downloads"]) == set(meta["download_files"])
                with browser.new_context(**settings, offline=True) as disconnected:
                    local = disconnected.new_page()
                    active = local
                    watch(local)
                    local.goto((Path(temporary) / meta["offline_entry"]).as_uri(), wait_until="load")
                    expect(local.locator("#city-layout-overview")).to_be_visible()
                    open_tables(local)
                    check_rows(local, data)
                    check_sheets(local, "all")
                    chosen = next(row for row in data["decisions"] if row["region_id"] == "R07")
                    local.locator("#region-select").select_option("R07")
                    local.locator("#search").fill(chosen["id"])
                    check_rows(local, data, region="R07", query=chosen["id"])
                    local.reload(wait_until="load")
                    open_tables(local)
                    check_rows(local, data, region="R07", query=chosen["id"])
                    expect(local.locator("#region-map-R07")).to_be_visible()
                    fits(local)
                    capture(local, "offline")
            active = page
            report["checks"].append("All 21 real browser downloads match released hashes, the PDF has 13 readable pages, and the complete ZIP works with network disabled and state restored")

            with browser.new_context(**settings, java_script_enabled=False) as disabled:
                plain = disabled.new_page()
                active = plain
                watch(plain)
                chosen = data["decisions"][0]
                plain.goto(base + PAGE + "#decision-" + chosen["id"], wait_until="load")
                expect(plain.locator("#decision-" + chosen["id"])).to_be_in_viewport()
                open_tables(plain)
                check_rows(plain, data, counts=False)
                check_sheets(plain, "all")
                source = plain.locator("#decision-" + chosen["id"] + " details.source-details")
                source.locator(":scope > summary").click()
                expect(source.locator("a[data-source-path]").first).to_be_visible()
                fits(plain)
                capture(plain, "without-javascript")
            active = page
            report["checks"].append("With JavaScript disabled all maps, original records and source excerpts remain readable through native links and disclosure controls")
            assert not report["errors"], report["errors"]
            report["status"] = "passed"
        except Exception as error:
            target = active if active and not active.is_closed() else page
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
    parser.add_argument("--output", default="artifacts/city-layout-r10-browser")
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
