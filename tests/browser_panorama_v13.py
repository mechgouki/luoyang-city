"""Verify both homepage entries, full-frame comparison, links and real downloads."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from browser_city_west_p472 import SIZES, base_url
from browser_layout import assert_loaded_viewport

ROOT = Path(__file__).resolve().parents[1]
PAGE = "luoyang-panorama-v13.html"
KEY = "panorama_review_v13"


def exercise(browser, base, device, output, expected_commit=None):
    settings = dict(viewport=SIZES[device], is_mobile=device == "mobile", has_touch=device == "mobile", reduced_motion="reduce")
    report = dict(device=device, viewport=SIZES[device], checks=[], downloads={}, screenshots={}, image_dimensions=[], errors=[])

    def capture(page, label):
        name = device + "-" + label + ".png"
        raw = page.screenshot(path=output / name, animations="disabled", full_page=True)
        report["screenshots"][name] = hashlib.sha256(raw).hexdigest()

    with browser.new_context(**settings, accept_downloads=True) as context:
        page = context.new_page()
        page.on("pageerror", lambda error: report["errors"].append(str(error)))
        try:
            info = context.request.get(base + "build-info.json").json()
            meta = info[KEY]
            report["source_commit"] = info["source_commit"]
            assert meta["source_commit"] == info["source_commit"]
            if expected_commit:
                assert info["source_commit"] == expected_commit
            assert meta["homepage_replacement_approved"] is False
            for home in ("index.html", "v3.0-dual.html"):
                page.goto(base + home, wait_until="load")
                expect(page.locator('[data-hero-revision="panorama-approved-v12"]')).to_be_visible()
                page.locator("#r8-panorama-entry").click()
                page.wait_for_url("**/" + PAGE, wait_until="load")
                expect(page.locator("#review-status")).to_contain_text("待审看")
                expect(page.locator("#figure-v13")).to_be_visible()
                expect(page.locator("#figure-v12")).to_be_hidden()
                assert_loaded_viewport(page, tolerance=1, report=report)
            report["checks"].append("Both homepage entries preserve approved V12 and lead to the explicitly unapproved V13 candidate")

            for version in ("v13", "v12"):
                page.locator(f'button[data-view="{version}"]').click()
                figure = page.locator("#figure-" + version)
                expect(figure).to_be_visible()
                image = figure.locator("img")
                page.wait_for_function("selector => { const image = document.querySelector(selector); return image.complete && image.naturalWidth > 0; }", arg="#figure-" + version + " img")
                size = image.evaluate("el => ({width:el.naturalWidth,height:el.naturalHeight,box:el.getBoundingClientRect().toJSON(),fit:getComputedStyle(el).objectFit,current:el.currentSrc})")
                expected = meta["images"][version]
                prefix = "small_" if device == "mobile" else ""
                assert (size["width"], size["height"]) == (expected[prefix + "width"], expected[prefix + "height"])
                assert abs(size["box"]["width"] / size["box"]["height"] - size["width"] / size["height"]) < .01
                assert size["fit"] == "contain"
                report["image_dimensions"].append(dict(version=version, **size))
                assert_loaded_viewport(page, tolerance=1, report=report)
            page.reload(wait_until="load")
            expect(page.locator('button[data-view="v12"]')).to_have_attribute("aria-pressed", "true")
            expect(page.locator("#figure-v12")).to_be_visible()
            page.locator('button[data-view="compare"]').focus()
            page.keyboard.press("Enter")
            expect(page.locator("#figure-v12")).to_be_visible()
            expect(page.locator("#figure-v13")).to_be_visible()
            page.reload(wait_until="load")
            expect(page.locator('button[data-view="compare"]')).to_have_attribute("aria-pressed", "true")
            assert_loaded_viewport(page, tolerance=1, report=report)
            capture(page, "comparison")
            report["checks"].append("Full and mobile images retain natural proportions; keyboard comparison and URL-restored view modes work")

            record = context.request.get(base + meta["record"]).json()
            first_id = record["candidate"]["changes"][0]["id"]
            page.goto(base + PAGE + "?view=compare#change-" + first_id, wait_until="load")
            expect(page.locator(".change-card")).to_have_count(meta["change_count"])
            expect(page.locator("#change-" + first_id)).to_be_in_viewport()
            page.locator("#change-" + first_id + " .back-to-image").click()
            assert page.evaluate("location.hash") == "#comparison"
            assert_loaded_viewport(page, tolerance=1, report=report)
            report["checks"].append("Every reviewed change is rendered; shareable evidence anchors and return-to-image links work")

            for path in meta["download_files"]:
                with page.expect_download() as event:
                    page.locator(f'[download][href="./{path}"]').click()
                raw = Path(event.value.path()).read_bytes()
                checksum = hashlib.sha256(raw).hexdigest()
                assert checksum == info["files_sha256"][path], path
                report["downloads"][path] = checksum
            report["checks"].append("Every advertised candidate and evidence download matches its released bytes")
            with browser.new_context(**settings, java_script_enabled=False) as disabled:
                plain = disabled.new_page()
                plain.on("pageerror", lambda error: report["errors"].append(str(error)))
                plain.goto(base + PAGE, wait_until="load")
                expect(plain.locator("#figure-v13")).to_be_visible()
                expect(plain.locator("#figure-v12")).to_be_visible()
                expect(plain.locator(".change-card")).to_have_count(meta["change_count"])
                assert_loaded_viewport(plain, tolerance=1, report=report)
                capture(plain, "without-javascript")
            report["checks"].append("Without JavaScript both complete artworks and all evidence remain readable")
            assert not report["errors"], report["errors"]
            report["status"] = "passed"
        except Exception as error:
            report.update(status="failed", url=page.url, error=str(error))
            if not page.is_closed():
                capture(page, "failure")
            raise
        finally:
            (output / (device + "-report.json")).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--commit")
    parser.add_argument("--output", default="artifacts/panorama-v13-browser")
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
