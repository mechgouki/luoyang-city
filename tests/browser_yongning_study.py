"""Read the actual three-image study and retain every real browser download."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import time

from playwright.sync_api import expect, sync_playwright
from browser_city_west_p472 import SIZES, base_url
from browser_layout import assert_loaded_viewport

ROOT = Path(__file__).resolve().parents[1]
PAGE = "luoyang-yongning-study.html"
ROLES = {"overlay": "overlay", "corrected_local": "corrected-local", "reintegration_preview": "reintegration-preview"}


def exercise(browser, base, device, output, expected_commit=None):
    report = dict(device=device, viewport=SIZES[device], checks=[], downloads={}, retained_downloads={},
                  download_attempts=[], screenshots={}, image_dimensions=[], errors=[], java_script_enabled=False)
    started = time.monotonic()
    settings = dict(viewport=SIZES[device], is_mobile=device == "mobile", has_touch=device == "mobile",
                    reduced_motion="reduce", java_script_enabled=False, accept_downloads=True)
    with browser.new_context(**settings) as context:
        page = context.new_page()
        page.on("pageerror", lambda error: report["errors"].append(str(error)))
        try:
            response = context.request.get(base + "build-info.json")
            assert response.ok
            info = response.json()
            parent = info["panorama_review_v14"]
            meta = parent["yongning_study"]
            report["source_commit"] = info["source_commit"]
            assert meta["source_commit"] == parent["source_commit"] == info["source_commit"]
            if expected_commit:
                assert expected_commit == info["source_commit"]
            assert meta["homepage_replacement_approved"] is meta["full_panorama_accepted"] is False
            assert parent["homepage_revision"] == meta["homepage_revision"] == "panorama-approved-v12"
            assert parent["status"] == "needs_revision" and parent["review_status"] == "rejected_needs_revision"
            assert len(parent["download_files"]) == 27
            review_response = context.request.get(base + meta["review"])
            assert review_response.ok
            review = review_response.json()
            assert hashlib.sha256(review_response.body()).hexdigest() == info["files_sha256"][meta["review"]]
            assert review["status"] == meta["review_status"]
            assert review["image_sha256"] == {role: image["sha256"] for role, image in meta["images"].items()}
            report.update(review_status=review["status"], full_panorama_accepted=False,
                          homepage_replacement_approved=False, previous_v14_downloads=27)

            page.goto(base + parent["page"], wait_until="load")
            expect(page.locator("#review-status")).to_contain_text("V14试绘审查·未通过")
            expect(page.locator("#yongning-study-entry")).to_have_count(1)
            page.locator("#yongning-study-entry").click()
            page.wait_for_url("**/" + PAGE, wait_until="load")
            expect(page).to_have_title("盛时洛阳 · 永宁寺三图审查")
            expect(page.locator("body")).to_have_attribute("data-review-status", review["status"])
            expect(page.locator("#study-review-status")).to_be_visible()
            expect(page.locator("#study-review-status")).to_contain_text(review["summary"])
            expect(page.locator("#study-review-status")).to_contain_text("首页继续采用已批准的 V12")
            expect(page.locator("#study-review-status")).to_contain_text("既有六次 V14 试绘仍未通过")
            expect(page.locator("#review-findings li")).to_have_text(review["findings"])
            expect(page.locator("#limits li")).to_have_text(review["remaining_limits"])
            expect(page.locator("figure[data-study-image]")).to_have_count(3)
            assert_loaded_viewport(page, tolerance=1, report=report)
            report["checks"].append("The actual V14 entry reaches the study; original review findings and limits remain visible without JavaScript, while V12 and all six rejected attempts retain their state")

            for role, anchor in ROLES.items():
                page.locator('.reading-path a[href="#' + anchor + '"]').click()
                assert page.evaluate("location.hash") == "#" + anchor
                section = page.locator("#" + anchor)
                section.scroll_into_view_if_needed()
                figure = section.locator("figure")
                image = meta["images"][role]
                expect(figure).to_have_attribute("data-source-sha256", image["sha256"])
                expect(figure.locator("img")).to_have_attribute("src", "./" + image["path"])
                page.wait_for_function("s => {const image=document.querySelector(s);return image.complete&&image.naturalWidth>0}", arg="#" + anchor + " img")
                measured = figure.locator("img").evaluate("el => ({width:el.naturalWidth,height:el.naturalHeight,box:el.getBoundingClientRect().toJSON(),fit:getComputedStyle(el).objectFit})")
                assert (measured["width"], measured["height"]) == (image["width"], image["height"])
                assert measured["fit"] == "contain"
                assert abs(measured["box"]["width"] / measured["box"]["height"] - image["width"] / image["height"]) < .01
                report["image_dimensions"].append(dict(role=role, path=image["path"], **measured))
                expect(figure.locator(".original-image")).to_have_attribute("href", "./" + image["path"])
                assert_loaded_viewport(page, tolerance=1, report=report)
                name = device + "-" + anchor + ".png"
                screenshot = section.screenshot(path=output / name, animations="disabled")
                report["screenshots"][name] = hashlib.sha256(screenshot).hexdigest()
            page.locator('.reading-path a[href="#corrected-local"]').focus()
            page.keyboard.press("Enter")
            page.reload(wait_until="load")
            assert page.evaluate("location.hash") == "#corrected-local"
            expect(page.locator("#corrected-local-title")).to_be_in_viewport()
            report["checks"].append("All three actual images load uncropped at their declared natural dimensions; figure links, keyboard anchors, reload and both viewport layouts work")

            page.locator('.reading-path a[href="#downloads"]').click()
            expect(page.locator("#downloads a[download]")).to_have_count(len(meta["download_files"]))
            for path in meta["download_files"]:
                member = PurePosixPath(path)
                assert not member.is_absolute() and ".." not in member.parts and "\\" not in path
                attempt = dict(path=path, attempt=1, click_delay_ms=150, status="started")
                report["download_attempts"].append(attempt)
                with page.expect_download(timeout=20000) as event:
                    page.locator('#downloads a[download][href="./' + path + '"]').click(delay=150)
                download = event.value
                assert download.failure() is None, (path, download.failure())
                retained_path = PurePosixPath("downloads") / device / member
                retained = output / retained_path
                retained.parent.mkdir(parents=True, exist_ok=True)
                download.save_as(retained)
                content = retained.read_bytes()
                checksum = hashlib.sha256(content).hexdigest()
                assert checksum == info["files_sha256"][path], path
                report["downloads"][path] = checksum
                report["retained_downloads"][path] = dict(bytes=len(content), sha256=checksum, retained_path=str(retained_path))
                attempt.update(status="passed", bytes=len(content), sha256=checksum, suggested_filename=download.suggested_filename)
            assert set(report["downloads"]) == set(report["retained_downloads"]) == set(meta["download_files"])
            report["checks"].append("Every new download comes from one actual click and retains bytes matching this build's manifest; the separate 27-item V14 download list is unchanged")
            assert not report["errors"], report["errors"]
            report["status"] = "passed"
        except Exception as error:
            report.update(status="failed", url=page.url, error=str(error))
            if report["download_attempts"] and report["download_attempts"][-1]["status"] == "started":
                report["download_attempts"][-1].update(status="failed", error=str(error))
            if not page.is_closed():
                name = device + "-failure.png"
                screenshot = page.screenshot(path=output / name, animations="disabled", full_page=True)
                report["screenshots"][name] = hashlib.sha256(screenshot).hexdigest()
            raise
        finally:
            report["elapsed_seconds"] = round(time.monotonic() - started, 3)
            (output / (device + "-report.json")).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url")
    parser.add_argument("--commit")
    parser.add_argument("--output", default="artifacts/yongning-study-browser")
    parser.add_argument("--browser-executable")
    args = parser.parse_args()
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    with base_url(args.base_url) as base, sync_playwright() as playwright:
        executable = args.browser_executable or os.environ.get("CHROMIUM_PATH")
        browser = playwright.chromium.launch(**({"executable_path": executable} if executable else {}))
        try:
            for device in SIZES:
                report = exercise(browser, base, device, output, args.commit)
                print(f"PASS Yongning study {device}: {len(report['checks'])} groups, {len(report['downloads'])} downloads, {report['elapsed_seconds']}s", flush=True)
        finally:
            browser.close()
