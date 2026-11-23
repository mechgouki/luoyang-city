"""Exercise actual V14 review modes, projection guides, source links and downloads."""
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
PAGE = "luoyang-panorama-v14.html"
KEY = "panorama_review_v14"


def exercise(browser, base, device, output, expected_commit=None):
    settings = dict(viewport=SIZES[device], is_mobile=device == "mobile", has_touch=device == "mobile", reduced_motion="reduce")
    report = dict(device=device, viewport=SIZES[device], checks=[], downloads={}, retained_downloads={}, download_attempts=[], screenshots={}, image_dimensions=[], projection_guides=[], errors=[])
    started = time.monotonic()

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
            record = context.request.get(base + meta["record"]).json()
            rejected = meta["status"] == "needs_revision"
            assert meta["status"] in {"candidate_for_review", "needs_revision"}
            assert record["status"] == record["candidate"]["status"] == meta["status"]
            assert record["review_status"] == meta["review_status"]
            assert record["blocking_findings"] == meta["blocking_findings"]
            assert len(record["blocking_findings"]) == meta["blocking_findings_count"]
            release = context.request.get(base + "release.json").json()
            assert release[KEY + "_status"] == meta["status"]
            assert release[KEY + "_review_status"] == meta["review_status"]
            if rejected:
                assert meta["review_status"] == "rejected_needs_revision" and meta["blocking_findings"]
                assert "V14试绘审查·未通过" in release["current_milestone"]
            else:
                assert meta["review_status"] in {"accepted_for_user_review", "accepted_for_user_review_with_known_limits"}
                assert not meta["blocking_findings"]
            report.update(image_status=meta["status"], image_review_status=meta["review_status"],
                          image_accepted_for_user_review=not rejected, blocking_findings=list(meta["blocking_findings"]))

            def assert_visible_review_state(target):
                expect(target.locator("body")).to_have_attribute("data-image-status", meta["status"])
                expect(target.locator("body")).to_have_attribute("data-review-status", meta["review_status"])
                expect(target.locator("#review-status")).to_have_attribute("data-status", meta["status"])
                expect(target.locator("#review-status")).to_be_visible()
                if rejected:
                    expect(target).to_have_title("盛时洛阳 · V14试绘审查·未通过")
                    expect(target.locator("h1")).to_have_text("V14试绘审查·未通过")
                    expect(target.locator("#review-status")).to_contain_text("V14试绘审查·未通过")
                    expect(target.locator("#blocking-findings")).to_be_visible()
                    expect(target.locator("#blocking-findings li")).to_have_text(meta["blocking_findings"])
                    for finding in target.locator("#blocking-findings li").all():
                        expect(finding).to_be_visible()
                    top = target.locator("#blocking-findings").bounding_box()
                    image = target.locator("#comparison").bounding_box()
                    assert top["y"] + top["height"] <= image["y"] + 1
                    expect(target.locator("#figure-v14 figcaption")).to_contain_text("未通过")
                    expect(target.locator("#figure-v14 img")).to_have_attribute("alt", record["candidate"]["alt"])
                    assert "未通过" in record["candidate"]["alt"]
                    expect(target.locator('button[data-view="v14"]')).to_contain_text("未通过")
                    expect(target.locator("#downloads-title")).to_contain_text("未通过")
                    for image_path in (record["source_png"], record["images"]["v14"]["full"]):
                        expect(target.locator('#downloads a[download][href="./' + image_path + '"]')).to_contain_text("未通过")
                else:
                    expect(target.locator("#review-status")).to_contain_text("待审看")
                    expect(target.locator("#blocking-findings")).to_have_count(0)

            for home in ("index.html", "v3.0-dual.html"):
                page.goto(base + home, wait_until="load")
                expect(page.locator('[data-hero-revision="panorama-approved-v12"]')).to_be_visible()
                expect(page.locator("#r11-plan-entry")).to_have_count(1)
                expect(page.locator("#r9-panorama-entry")).to_have_count(1)
                if rejected:
                    expect(page.locator("#r12-panorama-entry")).to_have_text("V14试绘审查·未通过")
                page.locator("#r12-panorama-entry").click()
                page.wait_for_url("**/" + PAGE, wait_until="load")
                assert_visible_review_state(page)
                expect(page.locator("#figure-v14")).to_be_visible()
                expect(page.locator("#figure-v13r2")).to_be_hidden()
                expect(page.locator("#figure-v12")).to_be_hidden()
                assert_loaded_viewport(page, tolerance=1, report=report)
            report["checks"].append("Both homepage entries preserve approved V12 and old links; image, review and release states agree, and every rejected-image blocker is visible before the image")

            for kind in ("v14", "v13r2", "v12"):
                page.locator(f'button[data-view="{kind}"]').click()
                figure = page.locator("#figure-" + kind)
                expect(figure).to_be_visible()
                page.wait_for_function("s => {const i=document.querySelector(s);return i.complete&&i.naturalWidth>0;}", arg="#figure-" + kind + " img")
                state = figure.locator("img").evaluate("el => ({width:el.naturalWidth,height:el.naturalHeight,box:el.getBoundingClientRect().toJSON(),fit:getComputedStyle(el).objectFit,current:el.currentSrc})")
                expected = meta["images"][kind]
                prefix = "small_" if device == "mobile" else ""
                assert (state["width"], state["height"]) == (expected[prefix + "width"], expected[prefix + "height"])
                assert abs(state["box"]["width"] / state["box"]["height"] - state["width"] / state["height"]) < .01
                assert state["fit"] == "contain"
                report["image_dimensions"].append(dict(version=kind, **state))
                page.reload(wait_until="load")
                expect(page.locator(f'button[data-view="{kind}"]')).to_have_attribute("aria-pressed", "true")
                if rejected and kind == "v14":
                    expect(page.locator("#view-status")).to_contain_text("未通过")
                assert_loaded_viewport(page, tolerance=1, report=report)
            page.locator('button[data-view="compare"]').focus()
            page.keyboard.press("Enter")
            expect(page.locator("#figure-v14")).to_be_visible()
            expect(page.locator("#figure-v13r2")).to_be_visible()
            expect(page.locator("#figure-v12")).to_be_hidden()
            page.reload(wait_until="load")
            expect(page.locator('button[data-view="compare"]')).to_have_attribute("aria-pressed", "true")
            if rejected:
                expect(page.locator("#view-status")).to_contain_text("未通过")
            assert_loaded_viewport(page, tolerance=1, report=report)
            capture(page, "comparison")
            report["checks"].append("Three full-frame modes, keyboard comparison and URL restoration preserve natural image proportions")

            guides = [x for x in record["supporting_assets"] if x["role"] in {"projection_overview", "projection_yongning", "massing_display", "alignment_audit"}]
            assert {"projection_overview", "projection_yongning"} <= {x["role"] for x in guides}
            page.goto(base + PAGE + "?view=v14#projection", wait_until="load")
            expect(page.locator(".projection-figure")).to_have_count(len(guides))
            for item in guides:
                figure = page.locator("#guide-" + item["id"])
                figure.scroll_into_view_if_needed()
                expect(figure).to_have_attribute("data-source-sha256", item["sha256"])
                expect(figure.locator("img")).to_have_attribute("src", "./" + item["published_path"])
                page.wait_for_function("s => {const i=document.querySelector(s);return i.complete&&i.naturalWidth>0;}", arg="#guide-" + item["id"] + " img")
                size = figure.locator("img").evaluate("el => ({width:el.naturalWidth,height:el.naturalHeight,box:el.getBoundingClientRect().toJSON(),fit:getComputedStyle(el).objectFit})")
                assert size["width"] > 0 and size["height"] > 0 and size["fit"] == "contain"
                assert abs(size["box"]["width"] / size["box"]["height"] - size["width"] / size["height"]) < .015
                report["projection_guides"].append(dict(id=item["id"], role=item["role"], **size))
            expect(page.locator(".evidence-levels article")).to_have_count(3)
            assert_loaded_viewport(page, tolerance=1, report=report)
            capture(page, "projection-and-evidence")
            report["checks"].append("Every actual projection, massing and alignment guide loads at its original proportion and source identity; mandatory pure projections remain distinct from artistic and visual-audit layers")

            first = record["candidate"]["changes"][0]["id"]
            page.goto(base + PAGE + "?view=compare#change-" + first, wait_until="load")
            expect(page.locator(".change-card")).to_have_count(meta["change_count"])
            expect(page.locator("#change-table tbody tr")).to_have_count(meta["change_count"])
            failed_changes = [item for item in record["candidate"]["changes"] if item["treatment_type"] == "attempted_not_accepted"]
            expect(page.locator('#changes [data-treatment="attempted_not_accepted"] .treatment-label')).to_have_text(["已试改，未通过"] * len(failed_changes))
            attempts = [item for item in record["supporting_assets"] if item["role"] == "attempt_review"]
            expect(page.locator("#attempt-history [data-attempt-review]")).to_have_count(len(attempts))
            for item in attempts:
                card = page.locator('#attempt-history [data-attempt-review="' + item["id"] + '"]')
                expect(card).to_contain_text(item["title"])
                expect(card).to_contain_text(item["description"])
                expect(card.locator("a")).to_have_attribute("href", "./" + item["published_path"])
            expect(page.locator("#change-" + first)).to_be_in_viewport()
            page.locator("#change-" + first + " .back-to-image").click()
            assert page.evaluate("location.hash") == "#comparison"
            page.locator('#projection a[href="./luoyang-city-plan.html?view=yongning#plan-reader"]').click()
            page.wait_for_url("**/luoyang-city-plan.html?view=yongning#plan-reader", wait_until="load")
            expect(page.locator("#plan-reader")).to_have_count(1)
            page.goto(base + PAGE + "?view=v14#downloads", wait_until="load")
            assert_loaded_viewport(page, tolerance=1, report=report)
            report["checks"].append("Change-table and per-object anchors, return navigation, and the actual R11 Yongning deep link work")

            expect(page.locator("#downloads a[download]")).to_have_count(len(meta["download_files"]))
            for path in meta["download_files"]:
                member = PurePosixPath(path)
                assert not member.is_absolute() and ".." not in member.parts and "\\" not in path
                attempt = dict(path=path, attempt=1, click_delay_ms=150, status="started")
                report["download_attempts"].append(attempt)
                with page.expect_download(timeout=20000) as event:
                    page.locator(f'#downloads [download][href="./{path}"]').click(delay=150)
                download = event.value
                assert download.failure() is None, (path, download.failure())
                relative = PurePosixPath("downloads") / device / member
                retained = output / relative
                retained.parent.mkdir(parents=True, exist_ok=True)
                download.save_as(retained)
                raw = retained.read_bytes()
                checksum = hashlib.sha256(raw).hexdigest()
                assert checksum == info["files_sha256"][path], path
                report["downloads"][path] = checksum
                report["retained_downloads"][path] = dict(sha256=checksum, bytes=len(raw), retained_path=str(relative))
                attempt.update(status="passed", sha256=checksum, bytes=len(raw), suggested_filename=download.suggested_filename)
            assert set(report["downloads"]) == set(meta["download_files"])
            report["checks"].append("Every download uses one genuine paced click, matches the release hash and retains its actual bytes")

            with browser.new_context(**settings, java_script_enabled=False) as disabled:
                plain = disabled.new_page()
                plain.on("pageerror", lambda error: report["errors"].append(str(error)))
                plain.goto(base + PAGE, wait_until="load")
                assert_visible_review_state(plain)
                for kind in ("v14", "v13r2", "v12"):
                    expect(plain.locator("#figure-" + kind)).to_be_visible()
                expect(plain.locator(".projection-figure")).to_have_count(len(guides))
                expect(plain.locator(".change-card")).to_have_count(meta["change_count"])
                expect(plain.locator("#attempt-history [data-attempt-review]")).to_have_count(len(attempts))
                expect(plain.locator("#downloads a[download]")).to_have_count(len(meta["download_files"]))
                for item in guides:
                    plain.locator("#guide-" + item["id"]).scroll_into_view_if_needed()
                    plain.wait_for_function("s => {const i=document.querySelector(s);return i.complete&&i.naturalWidth>0;}", arg="#guide-" + item["id"] + " img")
                assert_loaded_viewport(plain, tolerance=1, report=report)
                capture(plain, "without-javascript")
            report["checks"].append("Without JavaScript the image review status, every blocker, all three complete images, actual guides, attempted changes, trial reviews and downloads remain readable")
            assert not report["errors"], report["errors"]
            report["status"] = "passed"
        except Exception as error:
            report.update(status="failed", url=page.url, error=str(error))
            if report["download_attempts"] and report["download_attempts"][-1]["status"] == "started":
                report["download_attempts"][-1].update(status="failed", error=str(error))
            if not page.is_closed():
                capture(page, "failure")
            raise
        finally:
            report["elapsed_seconds"] = round(time.monotonic() - started, 3)
            (output / (device + "-report.json")).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--commit")
    parser.add_argument("--output", default="artifacts/panorama-v14-browser")
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
                print(f"PASS V14 {device}: {len(report['checks'])} groups, {len(report['downloads'])} downloads, {report['elapsed_seconds']}s", flush=True)
        finally:
            browser.close()
