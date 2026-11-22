"""Read every road category on desktop/mobile, offline, and without JavaScript."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright
from browser_city_west_p472 import SIZES, base_url

ROOT = Path(__file__).resolve().parents[1]
PAGE = "luoyang-all-roads.html"
KEY = "all_road_locations"
GROUPS = ("legacy", "documentary", "palace", "ward", "gate", "bridge")


def exercise(browser, base, device, output):
    settings = dict(viewport=SIZES[device], is_mobile=device == "mobile",
                    has_touch=device == "mobile", reduced_motion="reduce")
    report = dict(device=device, viewport=SIZES[device], checks=[], downloads={}, screenshots={}, errors=[])
    active_page = None

    def watch(page):
        page.on("pageerror", lambda error: report["errors"].append(str(error)))

    def fits(page):
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), page.url

    def count(page, number):
        expect(page.locator("details[data-record]:visible")).to_have_count(number)

    def capture(locator, label):
        name = device + "-" + label + ".png"
        raw = locator.screenshot(path=output / name, animations="disabled")
        report["screenshots"][name] = hashlib.sha256(raw).hexdigest()

    @contextmanager
    def checked_page(context):
        local_page = context.new_page()
        watch(local_page)
        try:
            yield local_page
        except Exception as error:
            report["failure_context"] = dict(url=local_page.url, error=str(error))
            capture(local_page, "failure")
            raise

    with browser.new_context(**settings, accept_downloads=True) as context:
        page = context.new_page()
        active_page = page
        watch(page)
        try:
            info = context.request.get(base + "build-info.json").json()
            meta = info[KEY]
            data = context.request.get(base + "all-roads/records.json").json()
            records = data["records"]
            ids = [r["id"] for r in records]
            grouped = {group: [r for r in records if r["group"] == group] for group in GROUPS}
            palace = grouped["palace"][0]["id"]
            ward = grouped["ward"][0]["id"]
            textual = next((r["id"] for r in grouped["documentary"]
                            if "ic_qianqiu_road" in r.get("entity_ids", [])), grouped["documentary"][0]["id"])
            gate = grouped["gate"][0]["id"]
            report["source_commit"] = info["source_commit"]
            report["record_count"] = len(records)
            page.goto(base + "luoyang-road-atlas.html", wait_until="domcontentloaded")
            expect(page.locator("details[data-road]")).to_have_count(21)
            page.locator("#all-roads-entry a").click()
            expect(page.locator("h1")).to_have_text("全城道路总览")
            expect(page.locator("details[data-record]")).to_have_count(len(records))
            actual = page.locator("details[data-record]").evaluate_all("nodes => nodes.map(n => n.id)")
            assert len(actual) == len(set(actual)) and set(actual) == set(ids)
            fits(page)
            expect(page.locator("#coverage")).to_be_attached()
            expect(page.locator("#exclusions")).to_be_attached()
            capture(page.locator("#map-scroll"), "whole-atlas")
            report["checks"].append("R6.1 entrance preserves its 21 records; complete catalog, coverage and exclusions are present")

            for group in GROUPS:
                page.locator("#group-filter").select_option(group)
                count(page, len(grouped[group]))
                assert set(page.locator("details[data-record]:visible").evaluate_all("nodes => nodes.map(n => n.dataset.group)")) == {group}
            page.reload(wait_until="domcontentloaded")
            expect(page.locator("#group-filter")).to_have_value("bridge")
            count(page, len(grouped["bridge"]))
            page.locator("#clear").click()
            count(page, len(records))
            page.locator("#query").fill(textual)
            count(page, 1)
            expect(page.locator("#" + textual)).to_be_visible()
            page.reload(wait_until="domcontentloaded")
            expect(page.locator("#query")).to_have_value(textual)
            count(page, 1)
            page.locator("#query").fill("missing-r62-no-match")
            count(page, 0)
            expect(page.locator("#empty")).to_be_visible()
            expect(page.locator("#count")).to_contain_text("0")
            page.locator("#clear").click()
            count(page, len(records))
            report["checks"].append("All six categories filter correctly; exact documentary ID, persistent filters, no-result and reset work")

            page.goto(base + PAGE + "#" + palace, wait_until="domcontentloaded")
            expect(page.locator("#" + palace)).to_have_attribute("open", "")
            fits(page)
            capture(page.locator("#" + palace), "palace-evidence")
            page.locator("#query").fill(textual)
            count(page, 1)
            assert page.evaluate("location.hash") == "", "Old palace anchor overrides the new query"
            page.reload(wait_until="domcontentloaded")
            expect(page.locator("#query")).to_have_value(textual)
            count(page, 1)
            assert page.evaluate("location.hash") == ""
            page.goto(base + PAGE + "#" + ward, wait_until="domcontentloaded")
            expect(page.locator("#" + ward)).to_have_attribute("open", "")
            fits(page)
            capture(page.locator("#" + ward), "ward-evidence")
            report["checks"].append("Palace and ward deep links open; a new search clears an older anchor and survives reload")

            # A reader can return from evidence to its existing source frame or qualitative index.
            # Screen bounds are checked on both desktop and mobile, independently of ancient geometry.
            for identifier in (palace, ward):
                page.goto(base + PAGE + "#" + identifier, wait_until="domcontentloaded")
                return_link = page.locator(f'#{identifier} [data-show-record="{identifier}"]')
                if identifier == palace:
                    page.locator("#show-source").uncheck()
                return_link.click()
                assert page.url.endswith("#map-record-" + identifier)
                target = page.locator("#map-record-" + identifier)
                assert target.evaluate("node => node.classList.contains('map-selected')")
                assert page.evaluate("document.activeElement.id") == "map-record-" + identifier
                assert target.evaluate("""node => {
                    const item = node.getBoundingClientRect();
                    const frame = document.getElementById('map-scroll').getBoundingClientRect();
                    return item.right > frame.left && item.left < frame.right &&
                           item.bottom > frame.top && item.top < frame.bottom;
                }"""), "Return link did not reveal the selected item inside its source/index frame"
                expect(page.locator("#map-status")).to_contain_text(identifier)
                if identifier == palace:
                    expect(page.locator("#show-source")).to_be_checked()
                page.reload(wait_until="domcontentloaded")
                assert page.url.endswith("#map-record-" + identifier)
                assert target.evaluate("node => node.classList.contains('map-selected')")
                target.focus()
                page.keyboard.press("Enter")
                assert page.url.endswith("#" + identifier)
                expect(page.locator("#" + identifier)).to_have_attribute("open", "")
                expect(return_link).to_be_in_viewport()
                fits(page)
            report["checks"].append("Evidence returns to the existing source/index item with highlight and keyboard focus; required layers, reload and map-to-card round trip work")

            page.locator("#show-source").uncheck()
            page.locator("#show-inferred").uncheck()
            page.locator("#show-unknown").check()
            page.reload(wait_until="domcontentloaded")
            expect(page.locator("#show-source")).not_to_be_checked()
            expect(page.locator("#show-inferred")).not_to_be_checked()
            expect(page.locator('#all-road-map [data-layer="source"]:visible')).to_have_count(0)
            expect(page.locator('#all-road-map [data-layer="inferred"]:visible')).to_have_count(0)
            assert page.locator('#all-road-map [data-layer="unknown"]:visible').count() > 0
            page.locator("#show-source").check()
            page.locator("#show-inferred").check()
            page.locator(f'#all-road-map a[href="#{palace}"]').first.focus()
            page.keyboard.press("Enter")
            expect(page.locator("#" + palace)).to_have_attribute("open", "")
            assert page.url.endswith("#" + palace)
            page.locator('[data-map-panel="0,2130"]').click()
            assert page.locator("#map-scroll").evaluate("node => node.scrollTop > 0"), "Ward/bridge panel navigation did not scroll the map"
            capture(page.locator("#map-scroll"), "ward-bridge-map")
            page.locator('[data-map-panel="0,0"]').click()
            expect(page.locator("#map-scroll")).to_have_js_property("scrollTop", 0)
            initial_width = page.locator("#all-road-map").bounding_box()["width"]
            page.locator("#zoom").focus()
            page.keyboard.press("End")
            assert page.locator("#all-road-map").bounding_box()["width"] > initial_width * 1.5
            scroll = page.locator("#map-scroll")
            assert scroll.evaluate("node => node.scrollWidth > node.clientWidth")
            scroll.focus()
            page.keyboard.press("ArrowRight")
            page.wait_for_function("document.getElementById('map-scroll').scrollLeft > 0")
            page.locator("#zoom").focus()
            page.keyboard.press("Home")
            fits(page)
            report["checks"].append("Source, inference and unknown layers persist; magnification and keyboard horizontal panning work")

            with tempfile.TemporaryDirectory() as temporary:
                for path in meta["download_files"]:
                    link = page.locator(f'[download][href="./{path}"], [download][href="{path}"]').first
                    with page.expect_download() as event:
                        link.click()
                    raw = Path(event.value.path()).read_bytes()
                    checksum = hashlib.sha256(raw).hexdigest()
                    assert checksum == info["files_sha256"][path], path
                    report["downloads"][path] = checksum
                    if path == meta["bundle"]:
                        with ZipFile(event.value.path()) as archive:
                            archive.extractall(temporary)
                assert len(report["downloads"]) == 6
                with browser.new_context(**settings, offline=True) as disconnected, checked_page(disconnected) as local:
                    active_page = local
                    local.goto((Path(temporary) / "index.html").as_uri() + "#" + ward)
                    expect(local.locator("#all-road-map")).to_be_visible()
                    expect(local.locator("#" + ward)).to_have_attribute("open", "")
                    expect(local.locator("details[data-record]")).to_have_count(len(records))
                    local.locator("#query").fill(gate)
                    count(local, 1)
                    assert local.evaluate("location.hash") == ""
                    local.reload(wait_until="domcontentloaded")
                    expect(local.locator("#query")).to_have_value(gate)
                    expect(local.locator("#" + gate)).to_be_visible()
                    count(local, 1)
                    fits(local)
                    report["checks"].append("Disconnected ZIP restores a ward deep link, searches a gate record, and preserves it after reload")
                active_page = page
                with browser.new_context(**settings, java_script_enabled=False) as disabled, checked_page(disabled) as plain:
                    active_page = plain
                    plain.goto(base + PAGE + "#" + ward, wait_until="domcontentloaded")
                    expect(plain.locator("details[data-record]")).to_have_count(len(records))
                    summary = plain.locator("#" + ward + " > summary")
                    expect(summary).to_be_in_viewport()
                    summary.click()
                    expect(plain.locator("#" + ward)).to_have_attribute("open", "")
                    fits(plain)
                    report["checks"].append("Native details open by an actual click without JavaScript")
                active_page = page
            report["checks"].append("All six advertised downloads were actually downloaded and matched release SHA-256")
            approval = context.request.get(base + "homepage/approval-v11.json").json()
            assert approval["hero"]["selection_number"] == "07"
            assert approval["hero"]["revision"] == "panorama-approved-v11"
            current = context.request.get(base + "homepage/approval-v12.json").json()
            assert current["previous_revision"] == approval["hero"]["revision"]
            assert current["hero"]["revision"] == "panorama-approved-v12"
            assert current["hero"]["source_sha256"] == "c7954dfc3ee659de756c62d0f634e40eddfd2ecc93cc8b833f53f6c0e0dc69ca"
            for name in ("index.html", "v3.0-dual.html"):
                raw = context.request.get(base + name).body()
                assert b'data-hero-revision="panorama-approved-v12"' in raw
                assert current["hero"]["asset"].encode() in raw
                archived = context.request.get(base + "homepage/history/" + name.replace(".html", "-before-v12.html")).body()
                assert b'data-hero-revision="panorama-approved-v11"' in archived
                assert hashlib.sha256(archived).hexdigest() == current["previous_html_sha256"][name]
            report["homepage"] = dict(current=current["hero"]["revision"], archived=approval["hero"]["revision"])
            assert not report["errors"], report["errors"]
            report["status"] = "passed"
        except Exception as error:
            target = active_page if active_page is not None and not active_page.is_closed() else page
            report.update(status="failed", url=report.get("failure_context", {}).get("url", target.url), error=str(error))
            if "failure_context" not in report and not target.is_closed():
                capture(target, "failure")
            raise
        finally:
            (output / (device + "-report.json")).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--output", default="artifacts/all-road-atlas-r62-browser")
    args = parser.parse_args()
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    with base_url(args.base_url) as base, sync_playwright() as playwright:
        options = {"executable_path": os.environ["CHROMIUM_PATH"]} if os.environ.get("CHROMIUM_PATH") else {}
        browser = playwright.chromium.launch(**options)
        try:
            for device in SIZES:
                exercise(browser, base, device, output)
        finally:
            browser.close()
