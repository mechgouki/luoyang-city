"""Exercise the road atlas on desktop, mobile, without scripts, and from its offline ZIP."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright
from browser_layout import assert_loaded_viewport
from browser_city_west_p472 import SIZES, base_url

ROOT = Path(__file__).resolve().parents[1]
PAGE = "luoyang-road-atlas.html"
KEY = "road_locations"
ROAD_IDS = [f"R{i:02d}" for i in range(1, 9)] + [f"O{i:02d}" for i in range(1, 12)] + ["X01", "X02"]


def exercise(browser, base, device, output):
    settings = dict(viewport=SIZES[device], is_mobile=device == "mobile",
                    has_touch=device == "mobile", reduced_motion="reduce")
    report = dict(device=device, viewport=SIZES[device], checks=[], downloads={}, screenshots={}, errors=[])

    def capture(locator, label):
        name = device + "-" + label + ".png"
        raw = locator.screenshot(path=output / name, animations="disabled")
        report["screenshots"][name] = hashlib.sha256(raw).hexdigest()

    def fits(page):
        assert_loaded_viewport(page, tolerance=1, report=report)

    def count(page, number):
        expect(page.locator("details[data-road]:visible")).to_have_count(number)

    with browser.new_context(**settings, accept_downloads=True) as context:
        page = context.new_page()
        page.on("pageerror", lambda error: report["errors"].append(str(error)))
        try:
            info = context.request.get(base + "build-info.json").json()
            meta = info[KEY]
            report["source_commit"] = info["source_commit"]
            page.goto(base + "prosperity-city-panorama.html", wait_until="load")
            page.locator("#road-atlas-entry a").click()
            expect(page.locator("h1")).to_contain_text("主干道")
            expect(page.locator("details[data-road]")).to_have_count(21)
            assert set(page.locator("details[data-road]").evaluate_all("nodes => nodes.map(n => n.id)")) == set(ROAD_IDS)
            fits(page)
            capture(page.locator("#map-scroll"), "map")
            page.goto(base + "luoyang-water-atlas.html", wait_until="load")
            page.locator("#road-atlas-entry a").click()
            expect(page.locator("#road-map")).to_be_visible()
            report["checks"].append("R5 and water entrances, all 21 source records, source map and viewport fit")

            page.locator("#query").fill("X02")
            count(page, 1)
            expect(page.locator("#X02")).to_be_visible()
            assert "q=X02" in page.url
            page.reload(wait_until="load")
            expect(page.locator("#query")).to_have_value("X02")
            count(page, 1)
            page.locator("#X02 > summary").click()
            expect(page.locator("#X02")).to_have_attribute("open", "")
            expect(page.locator("#X02")).to_contain_text("7.5")
            fits(page)
            capture(page.locator("#X02"), "baima-evidence")
            page.locator("#query").fill("missing-r6-no-match")
            count(page, 0)
            expect(page.locator("#count")).to_contain_text("0 / 21")
            page.locator("#clear").click()
            count(page, 21)
            page.locator("#evidence-filter").select_option("source")
            source_count = page.locator("details[data-road]:visible").count()
            assert 0 < source_count < 21
            page.reload(wait_until="load")
            expect(page.locator("#evidence-filter")).to_have_value("source")
            count(page, source_count)
            page.locator("#clear").click()
            report["checks"].append("Name/ID search, persistent evidence filter, empty results, reset and expanded field evidence")

            page.locator("#show-source").uncheck()
            page.locator("#show-inferred").uncheck()
            page.locator("#show-unknown").check()
            page.reload(wait_until="load")
            expect(page.locator("#show-source")).not_to_be_checked()
            expect(page.locator("#show-inferred")).not_to_be_checked()
            expect(page.locator("#show-unknown")).to_be_checked()
            expect(page.locator('#road-map [data-layer="source"]:visible')).to_have_count(0)
            expect(page.locator('#road-map [data-layer="inferred"]:visible')).to_have_count(0)
            assert page.locator('#road-map [data-layer="unknown"]:visible').count() > 0
            page.locator("#show-source").check()
            page.locator("#show-inferred").check()
            map_link = page.locator('#road-map a[href="#R01"]').last
            map_link.focus()
            page.keyboard.press("Enter")
            expect(page.locator("#R01")).to_have_attribute("open", "")
            assert page.url.endswith("#R01")
            page.reload(wait_until="load")
            expect(page.locator("#R01")).to_have_attribute("open", "")
            page.locator("#query").fill("X02")
            count(page, 1)
            assert not page.url.endswith("#R01"), "Old road anchor conflicts with the new search"
            page.reload(wait_until="load")
            expect(page.locator("#query")).to_have_value("X02")
            expect(page.locator("#X02")).to_be_visible()
            count(page, 1)
            assert page.evaluate("location.hash") == ""
            report["checks"].append("A new ID search clears the previous road anchor and survives reload")
            page.goto(base + PAGE + "#O11", wait_until="load")
            expect(page.locator("#O11")).to_have_attribute("open", "")
            fits(page)
            capture(page.locator("#O11"), "unknown-endpoint")
            initial_map_width = page.locator("#road-map").bounding_box()["width"]
            page.locator("#zoom").focus()
            page.keyboard.press("End")
            assert page.locator("#road-map").bounding_box()["width"] > initial_map_width * 1.5
            scroll = page.locator("#map-scroll")
            assert scroll.evaluate("node => node.scrollWidth > node.clientWidth")
            scroll.focus()
            page.keyboard.press("ArrowRight")
            page.wait_for_function("document.getElementById('map-scroll').scrollLeft > 0")
            page.locator("#zoom").focus()
            page.keyboard.press("Home")
            fits(page)
            report["checks"].append("Three evidence layers persist, map keyboard link and deep link restore, zoom and keyboard horizontal panning")

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
                assert len(report["downloads"]) == 5
                with browser.new_context(**settings, offline=True) as offline:
                    local = offline.new_page()
                    local.goto((Path(temporary) / "index.html").as_uri() + "#X02")
                    expect(local.locator("#road-map")).to_be_visible()
                    expect(local.locator("#X02")).to_have_attribute("open", "")
                    expect(local.locator("details[data-road]")).to_have_count(21)
                    local.locator("#query").fill("O11")
                    count(local, 1)
                    assert local.evaluate("location.hash") == ""
                    local.reload(wait_until="load")
                    expect(local.locator("#query")).to_have_value("O11")
                    expect(local.locator("#O11")).to_be_visible()
                    count(local, 1)
                    assert local.evaluate("location.hash") == ""
                    fits(local)
                with browser.new_context(**settings, java_script_enabled=False) as disabled:
                    plain = disabled.new_page()
                    plain.goto(base + PAGE + "#X02", wait_until="load")
                    expect(plain.locator("details[data-road]")).to_have_count(21)
                    report["no_javascript"] = {
                        "url": plain.url,
                        "scroll_behavior": plain.evaluate("getComputedStyle(document.documentElement).scrollBehavior"),
                        "summary_before": plain.locator("#X02 > summary").bounding_box(),
                    }
                    try:
                        expect(plain.locator("#X02 > summary")).to_be_in_viewport()
                        plain.locator("#X02 > summary").click()
                        expect(plain.locator("#X02")).to_contain_text("7.5")
                        expect(plain.locator("#X02")).to_have_attribute("open", "")
                        fits(plain)
                        report["no_javascript"]["status"] = "passed"
                    except Exception:
                        report["no_javascript"]["status"] = "failed"
                        report["no_javascript"]["summary_after"] = plain.locator("#X02 > summary").bounding_box()
                        filename = device + "-no-javascript-failure.png"
                        raw = plain.screenshot(path=output / filename)
                        report["screenshots"][filename] = hashlib.sha256(raw).hexdigest()
                        raise
            report["checks"].append("Five actual downloads with SHA-256, disconnected ZIP reading and search, native reading without JavaScript")

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
            report["checks"].append("Both homepage entries use approved full-frame v12 and preserve selected panorama 07 / v11 in the archive")
            assert not report["errors"], report["errors"]
            report["status"] = "passed"
        except Exception as error:
            report.update(status="failed", url=page.url, error=str(error))
            page.screenshot(path=output / (device + "-failure.png"))
            raise
        finally:
            (output / (device + "-report.json")).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--output", default="artifacts/road-atlas-r6-browser")
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
