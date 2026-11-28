"""Exercise the real homepage → V6 study journey and retain actual downloads.

Only the pinned Playwright runtime and the standard library are required. Image
identity comes from the live build-info manifest, PNG dimensions from its IHDR,
and rendered dimensions from the browser; this module never imports a publisher
or Pillow. It does not install or download a browser runtime.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct
import time
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET

from playwright.sync_api import expect, sync_playwright
from browser_city_west_p472 import SIZES, base_url
from browser_layout import assert_loaded_viewport


ROOT = Path(__file__).resolve().parents[1]
KEY = "homepage_yongning_v15"
PAGE = "luoyang-yongning-v6.html"
FOLDER = "yongning-v6"
ELEVATION = FOLDER + "/yongning-v6-scaled-elevation.png"
CHAPTERS = ("height", "colour", "mechanics", "sources")
UNESTABLISHED = re.compile(r"整体(?:结构)?可行性尚未(?:确立|证实)")


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_relative(path):
    member = PurePosixPath(path)
    assert path and not member.is_absolute() and ".." not in member.parts and "\\" not in path, path
    assert not urlsplit(path).scheme and not urlsplit(path).netloc, path
    return member


def relative_url(url, base):
    parsed, root = urlsplit(url), urlsplit(base)
    assert (parsed.scheme, parsed.netloc) == (root.scheme, root.netloc), url
    assert parsed.path.startswith(root.path), (url, base)
    path = parsed.path[len(root.path):]
    safe_relative(path)
    return path


def png_dimensions(raw):
    assert raw[:8] == b"\x89PNG\r\n\x1a\n" and raw[12:16] == b"IHDR", "Expected a PNG image"
    width, height = struct.unpack(">II", raw[16:24])
    assert width > 0 and height > 0
    return width, height


def exercise(browser, base, device, output, expected_commit=None):
    size = SIZES[device]
    if device == "mobile":
        assert size["width"] == 390, "The mobile acceptance viewport must be 390 px"
    report = dict(device=device, viewport=size, checks=[], screenshots={}, downloads={},
                  retained_downloads={}, download_attempts=[], fetched_files={}, image_dimensions=[],
                  anchor_checks=[], errors=[], java_script_enabled=True)
    started = time.monotonic()
    settings = dict(viewport=size, is_mobile=device == "mobile", has_touch=device == "mobile",
                    reduced_motion="reduce", java_script_enabled=True, accept_downloads=True)

    with browser.new_context(**settings) as context:
        page = context.new_page()
        page.set_default_timeout(20_000)
        page.on("pageerror", lambda error: report["errors"].append(str(error)))

        def capture(where, label):
            name = device + "-" + label + ".png"
            raw = where.screenshot(path=output / name, animations="disabled")
            report["screenshots"][name] = sha256(raw)

        try:
            response = context.request.get(base + "build-info.json", timeout=30_000)
            assert response.ok, (response.status, response.url)
            info_raw = response.body()
            info = json.loads(info_raw)
            meta = info[KEY]
            hashes = info["files_sha256"]
            report.update(source_commit=info["source_commit"], build_info_sha256=sha256(info_raw),
                          hero_revision=meta["hero_revision"], study_page=meta["study_page"])
            if expected_commit:
                assert info["source_commit"] == expected_commit, (info["source_commit"], expected_commit)
            assert meta["source_commit"] == info["source_commit"]
            assert meta["study_page"] == PAGE
            assert meta["structural_feasibility"] == "not_established"
            assert meta["new_ancient_coordinates"] == 0 and meta["historical_ground_truth_upgraded"] is False

            fetched = {}

            def checked_bytes(path):
                safe_relative(path)
                if path in fetched:
                    return fetched[path]
                expected = hashes[path]
                assert re.fullmatch(r"[0-9a-f]{64}", expected), path
                result = context.request.get(urljoin(base, path), timeout=30_000)
                assert result.ok, (path, result.status)
                assert relative_url(result.url, base) == path, result.url
                raw = result.body()
                checksum = sha256(raw)
                assert checksum == expected, (path, checksum, expected)
                report["fetched_files"][path] = dict(bytes=len(raw), sha256=checksum)
                fetched[path] = raw
                return raw

            assert json.loads(checked_bytes(meta["metadata"])) == meta
            release = json.loads(checked_bytes("release.json"))
            assert release["homepage_hero_revision"] == meta["hero_revision"]
            assert release["yongning_tower_study"] == PAGE
            assert release["yongning_tower_study_version"] == "V6"
            hero = meta["hero"]
            assert hero["revision"] == meta["hero_revision"] and hero["status"] == "approved"
            for asset, checksum in (("asset", "asset_sha256"), ("small_asset", "small_asset_sha256")):
                assert hashes[hero[asset]] == hero[checksum]
                checked_bytes(hero[asset])
            dimensions = png_dimensions(checked_bytes(ELEVATION))
            checked_bytes(PAGE)
            checked_bytes("index.html")
            checked_bytes(FOLDER + "/topic.css")
            checked_bytes(FOLDER + "/homepage.css")
            report["checks"].append("Live build identity, release, V15 metadata and current page/image/style bytes match the same source commit and SHA-256 manifest")

            def check_image(selector, allowed_dimensions, role):
                image = page.locator(selector)
                expect(image).to_have_count(1)
                image.scroll_into_view_if_needed()
                page.wait_for_function("s => {const i=document.querySelector(s); return i && i.complete && i.naturalWidth > 0}", arg=selector)
                measured = image.evaluate("""el => {
                    const box = el.getBoundingClientRect();
                    const clipped = [];
                    for (let p = el.parentElement; p && p !== document.body && p !== document.documentElement; p = p.parentElement) {
                        const s = getComputedStyle(p), r = p.getBoundingClientRect();
                        const clipsX = ['hidden', 'clip', 'scroll', 'auto'].includes(s.overflowX);
                        const clipsY = ['hidden', 'clip', 'scroll', 'auto'].includes(s.overflowY);
                        if ((clipsX && (box.left < r.left - 2 || box.right > r.right + 2)) ||
                            (clipsY && (box.top < r.top - 2 || box.bottom > r.bottom + 2)) || s.clipPath !== 'none') {
                            clipped.push({tag: p.tagName, id: p.id, overflowX: s.overflowX, overflowY: s.overflowY});
                        }
                    }
                    return {source: el.currentSrc, width: el.naturalWidth, height: el.naturalHeight,
                        box: box.toJSON(), fit: getComputedStyle(el).objectFit, clipped};
                }""")
                path = relative_url(measured["source"], base)
                assert path in allowed_dimensions, (role, path)
                width, height = allowed_dimensions[path]
                assert (measured["width"], measured["height"]) == (width, height), (role, measured)
                assert measured["fit"] == "contain", (role, measured)
                box = measured["box"]
                assert box["width"] > 0 and box["height"] > 0
                assert abs(box["width"] / box["height"] - width / height) < .005, (role, measured)
                assert box["left"] >= -1 and box["right"] <= size["width"] + 1, (role, measured)
                assert not measured["clipped"], (role, measured)
                raw = checked_bytes(path)
                measured.update(role=role, path=path, bytes=len(raw), sha256=sha256(raw))
                report["image_dimensions"].append(measured)
                return measured

            navigation = page.goto(base, wait_until="load")
            assert navigation and navigation.ok
            expect(page.locator("#home-hero")).to_have_attribute("data-hero-revision", meta["hero_revision"])
            expected_hero_sizes = {hero["asset"]: (hero["width"], hero["height"]),
                                   hero["small_asset"]: (hero["small_width"], hero["small_height"])}
            check_image("#home-hero img", expected_hero_sizes, "current-homepage-hero")
            assert_loaded_viewport(page, tolerance=1, report=report)
            capture(page.locator("#home-hero"), "homepage-hero")

            expect(page.locator("#home-yongning-entry")).to_have_count(1)
            expect(page.locator("#home-yongning-entry")).to_have_attribute("href", "./" + PAGE)
            expect(page.locator("#home-yongning .home-yongning-verdict")).to_contain_text(UNESTABLISHED)
            check_image("#home-yongning img", {ELEVATION: dimensions}, "homepage-study-plate")
            assert_loaded_viewport(page, tolerance=1, report=report)
            capture(page.locator("#home-yongning"), "homepage-study-entry")
            page.locator("#home-yongning-entry").click()
            page.wait_for_url("**/" + PAGE, wait_until="load")
            expect(page).to_have_title(re.compile("永宁寺塔 V6"))
            expect(page.locator("#research-verdict")).to_be_visible()
            expect(page.locator("#research-verdict")).to_contain_text(UNESTABLISHED)
            expect(page.locator("#research-verdict")).to_contain_text("不能据此认定安全可建")
            report["checks"].append("The actual homepage CTA reaches the V6 topic; both entry and topic retain the unestablished-feasibility statement")

            measured = check_image("#v6-elevation", {ELEVATION: dimensions}, "topic-full-elevation")
            expect(page.locator("#elevation-original")).to_have_attribute("href", "./" + ELEVATION)
            assert_loaded_viewport(page, tolerance=1, report=report)
            capture(page.locator("#elevation"), "topic-complete-elevation")
            with page.expect_popup() as event:
                page.locator("#elevation-original").click()
            original = event.value
            original.on("pageerror", lambda error: report["errors"].append(str(error)))
            try:
                original.wait_for_load_state("load")
                assert relative_url(original.url, base) == ELEVATION
                original.wait_for_function("() => {const i=document.querySelector('img');return i && i.complete && i.naturalWidth > 0}")
                actual = original.locator("img").first.evaluate("i => [i.naturalWidth, i.naturalHeight]")
                assert tuple(actual) == dimensions
                report["original_image_open"] = dict(url=original.url, width=actual[0], height=actual[1], sha256=measured["sha256"])
            finally:
                original.close()
            report["checks"].append("Current desktop/mobile hero and both study plates load at manifest-matching natural dimensions without cropping; the actual original-image link opens the complete PNG")

            for anchor in CHAPTERS:
                link = page.locator('.chapter-nav a[href="#' + anchor + '"]')
                expect(link).to_have_count(1)
                link.click()
                assert page.evaluate("location.hash") == "#" + anchor
                heading = page.locator("#" + anchor + "-title")
                expect(heading).to_be_in_viewport()
                assert_loaded_viewport(page, tolerance=1, report=report)
                page.reload(wait_until="load")
                assert page.evaluate("location.hash") == "#" + anchor
                expect(heading).to_be_in_viewport()
                assert_loaded_viewport(page, tolerance=1, report=report)
                capture(page, "chapter-" + anchor)
                report["anchor_checks"].append(dict(anchor=anchor, click=True, reload=True, heading_in_viewport=True))
            report["checks"].append("All four chapter links are exercised by real clicks and survive reload with their headings visible and no document overflow")

            page.locator('.chapter-nav a[href="#height"]').focus()
            page.keyboard.press("Enter")
            assert page.evaluate("location.hash") == "#height"
            details = page.locator(".research-detail")
            details.locator("summary").click()
            expect(details).to_have_attribute("open", "")
            expect(details).to_contain_text("112.9")
            assert_loaded_viewport(page, tolerance=1, report=report)
            page.locator('.chapter-nav a[href="#mechanics"]').click()
            expect(page.locator("#scenario-low")).to_contain_text("失稳")
            expect(page.locator("#scenario-middle")).to_contain_text("0.83")
            expect(page.locator("#scenario-upper")).to_contain_text("0.23")
            expect(page.locator("#drift-limit")).to_contain_text("131.8")
            expect(page.locator("#drift-limit")).to_contain_text("不是147")
            expect(page.locator("#scenario-upper")).to_contain_text("仅通过")
            summary_path = FOLDER + "/mechanics-summary.png"
            check_image(".mechanics-figure img", {summary_path: png_dimensions(checked_bytes(summary_path))}, "mechanics-summary")
            assert_loaded_viewport(page, tolerance=1, report=report)
            capture(page.locator("#lateral-scenarios"), "lateral-scenarios")
            report["checks"].append("Keyboard chapter navigation, native expanded layer heights, three drift cases and the complete mechanics chart retain their model boundaries")

            downloads = (
                (FOLDER + "/yongning-v6-scaled-elevation.svg", "#download-elevation-svg", "svg"),
                (FOLDER + "/lateral-sensitivity.csv", '#sources a[download][href="./yongning-v6/lateral-sensitivity.csv"]', "csv"),
            )
            for path, selector, kind in downloads:
                member = safe_relative(path)
                link = page.locator(selector)
                expect(link).to_have_count(1)
                expect(link).to_have_attribute("href", "./" + path)
                attempt = dict(path=path, attempt=1, status="started", selector=selector)
                report["download_attempts"].append(attempt)
                with page.expect_download(timeout=30_000) as event:
                    link.click(delay=150)
                download = event.value
                assert download.failure() is None, (path, download.failure())
                assert relative_url(download.url, base) == path
                retained_path = PurePosixPath("downloads") / device / member
                retained = output / retained_path
                retained.parent.mkdir(parents=True, exist_ok=True)
                download.save_as(retained)
                raw = retained.read_bytes()
                checksum = sha256(raw)
                assert checksum == hashes[path], (path, checksum, hashes[path])
                assert download.suggested_filename == member.name
                if kind == "svg":
                    root = ET.fromstring(raw)
                    assert root.tag == "{http://www.w3.org/2000/svg}svg"
                else:
                    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
                    assert rows and len(rows[0]) > 1, "The CSV must contain the actual scenario table"
                    attempt["data_rows"] = len(rows)
                attempt.update(status="passed", bytes=len(raw), sha256=checksum,
                               suggested_filename=download.suggested_filename)
                report["downloads"][path] = checksum
                report["retained_downloads"][path] = dict(bytes=len(raw), sha256=checksum, retained_path=str(retained_path))
            assert set(report["downloads"]) == {item[0] for item in downloads}
            assert set(report["downloads"]) == set(report["retained_downloads"])
            assert_loaded_viewport(page, tolerance=1, report=report)
            report["checks"].append("One real click for each SVG/CSV download retains parseable bytes with SHA-256 exactly matching this live build; no synthetic download substitutes")
            assert not report["errors"], report["errors"]
            report["status"] = "passed"
        except Exception as error:
            report.update(status="failed", error=repr(error), url=page.url)
            if report["download_attempts"] and report["download_attempts"][-1]["status"] == "started":
                report["download_attempts"][-1].update(status="failed", error=repr(error))
            if not page.is_closed():
                try:
                    capture(page, "failure")
                except Exception as screenshot_error:
                    report["failure_screenshot_error"] = repr(screenshot_error)
            raise
        finally:
            report["elapsed_seconds"] = round(time.monotonic() - started, 3)
            (output / (device + "-report.json")).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url")
    parser.add_argument("--commit")
    parser.add_argument("--output", default="artifacts/homepage-yongning-v15-browser")
    parser.add_argument("--browser-executable")
    args = parser.parse_args()
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    summary = dict(status="running", devices={}, errors=[])
    try:
        with base_url(args.base_url) as base, sync_playwright() as playwright:
            summary["base_url"] = base
            executable = args.browser_executable or os.environ.get("CHROMIUM_PATH")
            browser = playwright.chromium.launch(**({"executable_path": executable} if executable else {}))
            try:
                for device in SIZES:
                    try:
                        report = exercise(browser, base, device, output, args.commit)
                        summary["devices"][device] = dict(status="passed", report=device + "-report.json")
                        print(f"PASS homepage/V6 {device}: {len(report['checks'])} groups, {len(report['downloads'])} real downloads, {report['elapsed_seconds']}s", flush=True)
                    except Exception as error:
                        summary["devices"][device] = dict(status="failed", report=device + "-report.json", error=repr(error))
                        summary["errors"].append(device + ": " + repr(error))
                        print(f"FAIL homepage/V6 {device}: {error}", flush=True)
            finally:
                browser.close()
    except Exception as error:
        summary["errors"].append(repr(error))
    finally:
        summary["status"] = "passed" if not summary["errors"] and set(summary["devices"]) == set(SIZES) else "failed"
        (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
