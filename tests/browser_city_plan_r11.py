"""Exercise the released R11 shared plane on desktop/mobile, no-JS and offline.

Downloads come from actual, paced browser clicks and must match the deployment's
released SHA-256 values.  Camera/layer actions must never change source geometry.
This script uses the normal pinned Playwright runtime; it has no launch-policy,
network, download-throttling, or access-control workarounds.
"""

import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import time
from urllib.parse import parse_qs, urlsplit
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader

from browser_city_west_p472 import SIZES, base_url
from browser_layout import assert_loaded_viewport


ROOT = Path(__file__).resolve().parents[1]
PAGE = "luoyang-city-plan.html"
KEY = "city_plan_r11"
DATA = "city-plan-r11/plan.json"
FRAME = "r11-xian1980-source-local-aeqd"
VIEW_IDS = ["all", "core", "changhe", "yongning", "palace2013", *[f"R{i:02}" for i in range(1, 12)]]
LAYERS = ["source", "trace", "scale", "candidate", "palace"]
LEGACY = "geo-palace-layout-envelope"
TOWER = "r11-yongning-YN11-TOWER-PLINTH"
GATE = "r11-changhe-gate-main-base"
PDF_CACHE = {}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_member(name):
    p = PurePosixPath(name)
    assert name and not p.is_absolute() and ".." not in p.parts and "\\" not in name, name
    return p


def expected_coverage(data, kind="all", query=""):
    query = query.lower()
    return [e["id"] for e in data["coverage"]
            if (kind == "all" or e["placement_group"] == kind)
            and (not query or query in json.dumps(e, ensure_ascii=False).lower())]


def font_object(value):
    return value.get_object() if hasattr(value, "get_object") else value


def pdf_audit(raw, data, commit):
    """Read the downloaded bytes: page count, actual text, paper size and fonts."""
    checksum = digest(raw)
    if checksum in PDF_CACHE:
        return {**copy.deepcopy(PDF_CACHE[checksum]), "reused_identical_verified_pdf": True}
    pdf = PdfReader(io.BytesIO(raw))
    wanted = data["pdf"]["pages"]
    assert len(pdf.pages) == wanted == len(data["views"]) + 1
    assert commit in str((pdf.metadata or {}).get("/Keywords", ""))
    fonts, pages = [], []

    def inspect_font(ref, page_number):
        font = font_object(ref)
        descendants = font_object(font.get("/DescendantFonts"))
        if descendants:
            for child in descendants:
                inspect_font(child, page_number)
            return
        name = str(font.get("/BaseFont", font.get("/Name", "unnamed")))
        subtype = str(font.get("/Subtype", ""))
        descriptor = font_object(font.get("/FontDescriptor"))
        programs = []
        if descriptor:
            for key in ("/FontFile", "/FontFile2", "/FontFile3"):
                if key in descriptor:
                    stream = font_object(descriptor[key])
                    size = len(stream.get_data())
                    assert size > 0, (page_number, name, key)
                    programs.append({"type": key, "bytes": size})
        type3 = subtype == "/Type3" and bool(font_object(font.get("/CharProcs")))
        assert programs or type3, ("Unembedded PDF font", page_number, name, subtype)
        fonts.append({"page": page_number, "name": name, "subtype": subtype,
                      "embedded_programs": programs, "type3_embedded_charprocs": type3})

    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        chinese = sum("\u3400" <= c <= "\u9fff" for c in text)
        assert chinese >= 8, ("Unreadable Chinese PDF page", i + 1, text[:120])
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        expected_mm = (594, 420) if i == 0 else (420, 297)
        assert abs(width - expected_mm[0] * 72 / 25.4) < 1
        assert abs(height - expected_mm[1] * 72 / 25.4) < 1
        resources = font_object(page.get("/Resources")) or {}
        page_fonts = font_object(resources.get("/Font")) or {}
        assert page_fonts, ("No PDF font resources", i + 1)
        for ref in page_fonts.values():
            inspect_font(ref, i + 1)
        pages.append({"page": i + 1, "width_pt": width, "height_pt": height,
                      "chinese_characters": chinese})
    result = {"pages": wanted, "pages_checked": pages, "fonts": fonts,
              "font_names": sorted({f["name"] for f in fonts}),
              "all_fonts_embedded": True, "sha256": checksum}
    PDF_CACHE[checksum] = copy.deepcopy(result)
    return {**result, "reused_identical_verified_pdf": False}


def geometry_snapshot(page):
    """Exclude screen-sized symbols, labels, strokes and visibility choices."""
    return page.locator("#city-plan-map [data-feature-id]").evaluate_all("""nodes => nodes.map(n => ({
        id: n.dataset.featureId,
        hash: n.dataset.geometrySha256,
        role: n.dataset.geometryRole,
        paths: [...n.children].filter(c => c.tagName.toLowerCase() === 'path').map(c => c.getAttribute('d')),
        anchors: [...n.children].filter(c => c.tagName.toLowerCase() === 'g').map(c => c.getAttribute('transform'))
    })).sort((a,b) => a.id.localeCompare(b.id))""")


def camera(page):
    return [float(x) for x in page.locator("#city-plan-map").get_attribute("viewBox").split()]


def same_camera(actual, wanted, tolerance=0.02):
    assert len(actual) == len(wanted) == 4
    assert all(abs(a - b) <= tolerance for a, b in zip(actual, wanted)), (actual, wanted)


def painted(page):
    page.wait_for_function(r"""() => {
        const s = document.getElementById('city-plan-map');
        return s && s.dataset.visibleWidthM === Number(s.getAttribute('viewBox').split(/\s+/)[2]).toFixed(3);
    }""")


def layer_count(page, layer, number):
    page.wait_for_function("""({layer, number}) =>
        [...document.querySelectorAll('#city-plan-map [data-feature-id]')]
        .filter(n => n.dataset.layer === layer && getComputedStyle(n).display !== 'none').length === number
    """, arg={"layer": layer, "number": number})


def open_fold(page, ident):
    fold = page.locator("#" + ident)
    if fold.get_attribute("open") is None:
        fold.locator(":scope > summary").click()


def close_fold(page, ident):
    fold = page.locator("#" + ident)
    if fold.get_attribute("open") is not None:
        fold.locator(":scope > summary").click()


def coverage_rows(page, data, kind="all", query="", *, counts=True):
    expected = expected_coverage(data, kind, query)
    rows = page.locator(".coverage-row:visible")
    expect(rows).to_have_count(len(expected))
    actual = rows.evaluate_all("nodes => nodes.map(n => n.id.slice('entity-'.length))")
    assert actual == expected, (kind, query, actual, expected)
    if counts:
        expect(page.locator("#coverage-count")).to_have_attribute("data-visible-count", str(len(expected)))
        if expected:
            expect(page.locator("#coverage-empty")).to_be_hidden()
        else:
            expect(page.locator("#coverage-empty")).to_be_visible()


def exercise(browser, base, device, output, expected_commit=None):
    started = time.monotonic()
    settings = dict(viewport=SIZES[device], is_mobile=device == "mobile", has_touch=device == "mobile",
                    reduced_motion="reduce")
    report = {"device": device, "viewport": SIZES[device], "checks": [], "screenshots": {},
              "downloads": {}, "retained_downloads": {}, "download_attempts": [], "errors": [], "views": {}}
    active = None

    def watch(page):
        page.on("pageerror", lambda error: report["errors"].append(str(error)))

    def capture(page_or_element, label):
        path = output / (device + "-" + label + ".png")
        raw = page_or_element.screenshot(path=str(path), animations="disabled")
        report["screenshots"][path.name] = digest(raw)

    def fits(page):
        return assert_loaded_viewport(page, tolerance=1, report=report)

    with browser.new_context(**settings, accept_downloads=True) as context:
        page = context.new_page()
        context.set_default_timeout(8000)
        active = page
        watch(page)
        try:
            info_response = context.request.get(base + "build-info.json")
            assert info_response.ok, (info_response.status, info_response.url)
            info = info_response.json()
            assert KEY in info, "Requested deployment does not contain the R11 release"
            meta = info[KEY]
            response = context.request.get(base + DATA)
            assert response.ok and digest(response.body()) == info["files_sha256"][DATA]
            data = response.json()
            assert info["source_commit"] == data["source_commit"] == meta["source_commit"]
            if expected_commit:
                assert info["source_commit"] == expected_commit, "Browser reached a different deployment"
            assert data["counts"] == meta["counts"]
            assert data["frame"]["id"] == FRAME
            assert data["coordinate_contract"]["verified_shared_controls"] == 0
            assert data["coordinate_contract"]["field_registration_verified"] is False
            assert data["coordinate_contract"]["all_views_share_geometry"] is True
            assert len(data["coverage"]) == 339 and len(data["regions"]) == 11
            assert [v["id"] for v in data["views"]] == VIEW_IDS
            assert data["counts"]["trace_features"] == 33
            assert data["counts"]["published_overview_features"] == 24
            report["source_commit"] = info["source_commit"]
            features = {f["id"]: f for f in data["features"]}

            page.goto(base + PAGE, wait_until="load")
            expect(page.locator("html")).to_have_attribute("data-plan-ready", "true")
            expect(page.locator("#city-plan-map")).to_be_visible()
            expect(page.locator("#city-plan-map")).to_have_attribute("data-coordinate-frame", FRAME)
            assert json.loads(page.locator("#plan-data").text_content()) == data
            expect(page.locator("#view-select option")).to_have_count(16)
            assert page.locator("#view-select option").evaluate_all("nodes => nodes.map(n => n.value)") == VIEW_IDS
            expect(page.locator("[data-layer-toggle]")).to_have_count(5)
            expect(page.locator('[data-layer-toggle="palace"]')).not_to_be_checked()
            original = geometry_snapshot(page)
            assert len(original) == len(features)
            assert {x["id"]: x["hash"] for x in original} == {fid: f["geometry_sha256"] for fid, f in features.items()}
            expect(page.locator(f'#city-plan-map [data-feature-id="{LEGACY}"]')).to_be_hidden()
            fits(page)
            capture(page.locator("#map-viewport"), "all")
            report["checks"].append("Released commit, embedded data, all 16 views, 339 catalog entries and immutable source-geometry hashes agree")

            # Each view changes only the camera. Only the dedicated comparison
            # enables palace automatically; all other views retain the choice.
            page.locator("#view-select").select_option("R03")
            expect(page.locator('[data-layer-toggle="palace"]')).not_to_be_checked()
            layer_count(page, "palace", 0)
            palace_on = False
            for view in data["views"]:
                vid = view["id"]
                page.locator("#view-select").select_option(vid)
                painted(page)
                box = camera(page)
                x0, y0, x1, y1 = view["bbox"]
                assert abs(box[0] + box[2] / 2 - (x0 + x1) / 2) < 0.02
                assert abs(box[1] + box[3] / 2 + (y0 + y1) / 2) < 0.02
                assert box[2] + 0.02 >= x1 - x0 and box[3] + 0.02 >= y1 - y0
                if vid == "palace2013":
                    palace_on = True
                expect(page.locator('[data-layer-toggle="palace"]')).to_be_checked(checked=palace_on)
                layer_count(page, "palace", 24 if palace_on else 0)
                expect(page.locator(f'#city-plan-map [data-feature-id="{LEGACY}"]')).to_be_hidden()
                report["views"][vid] = {"camera": box, "palace_visible": palace_on}
            assert geometry_snapshot(page) == original
            page.locator("#view-select").select_option("all")
            expect(page.locator('[data-layer-toggle="palace"]')).to_be_checked()
            page.locator('[data-layer-toggle="palace"]').uncheck()
            page.locator("#view-select").select_option("R03")
            expect(page.locator('[data-layer-toggle="palace"]')).not_to_be_checked()
            page.locator("#view-select").select_option("all")
            for kind in LAYERS:
                toggle = page.locator(f'[data-layer-toggle="{kind}"]')
                toggle.check()
                expected = sum(f["layer"] == kind and (f.get("default_visible") is not False or kind == "palace")
                               for f in data["features"])
                layer_count(page, kind, expected)
                toggle.uncheck()
                layer_count(page, kind, 0)
                if kind != "palace":
                    toggle.check()
                    layer_count(page, kind, expected)
            page.locator("#label-toggle").uncheck()
            expect(page.locator("#city-plan-map")).to_have_attribute("data-label-count", "0")
            page.locator("#label-toggle").check()
            page.wait_for_function("Number(document.getElementById('city-plan-map').dataset.labelCount) > 0")
            report["checks"].append("All viewports preserve geometric paths; five layer controls and labels work; palace remains an explicit comparison and the legacy envelope stays hidden")

            page.locator("#view-select").select_option("yongning")
            painted(page)
            initial = camera(page)
            page.locator('[data-map-action="in"]').click()
            painted(page)
            zoomed = camera(page)
            assert zoomed[2] < initial[2]
            page.locator('[data-map-action="out"]').click()
            painted(page)
            assert camera(page)[2] > zoomed[2]
            page.locator('[data-map-action="in"]').click()
            painted(page)
            fixed = camera(page)
            page.locator('[data-map-action="right"]').click()
            page.locator('[data-map-action="down"]').click()
            painted(page)
            moved = camera(page)
            assert moved[0] > fixed[0] and moved[1] > fixed[1]
            page.locator('[data-map-action="left"]').click()
            page.locator('[data-map-action="up"]').click()
            painted(page)
            same_camera(camera(page), fixed)
            page.locator("#map-viewport").focus()
            page.keyboard.press("ArrowRight")
            painted(page)
            assert camera(page)[0] > fixed[0]
            page.keyboard.press("+")
            painted(page)
            assert camera(page)[2] < fixed[2]
            page.keyboard.press("0")
            painted(page)
            same_camera(camera(page), initial)
            page.locator('[data-map-action="reset"]').click()
            painted(page)
            same_camera(camera(page), initial)
            # This is an actual rendered polygon click, not a JS event dispatch.
            page.locator(f'#city-plan-map [data-feature-id="{TOWER}"] > path').click()
            expect(page.locator("#selected-title")).to_have_text(features[TOWER]["label"])
            expect(page.locator(f'#city-plan-map [data-feature-id="{TOWER}"]')).to_have_class("is-selected")
            expect(page.locator("#selected-evidence")).to_contain_text("候选")
            fits(page)
            capture(page.locator("#map-viewport"), "yongning-selected")
            other_labels = page.locator("#city-plan-map [data-label-for]").evaluate_all(
                "nodes => nodes.map(n => n.dataset.labelFor)")
            label_id = next(fid for fid in other_labels if fid != TOWER)
            page.locator(f'#city-plan-map [data-label-for="{label_id}"] text').click()
            expect(page.locator("#selected-title")).to_have_text(features[label_id]["label"])
            report["checks"].append("Buttons and keyboard zoom/pan/reset keep the same plane, and a real tower-polygon click opens its source/placement evidence")

            page.locator("#map-search").fill(TOWER)
            result = page.locator(f'[data-result-feature="{TOWER}"]')
            expect(result).to_be_visible()
            result.click()
            expect(page.locator("#selected-title")).to_have_text(features[TOWER]["label"])
            # Alias navigation must retain the source name even where the map
            # uses a period-appropriate former residence label.
            alias = next(e for e in data["coverage"] if e["id"] == "w_xuanzhong")
            assert alias["feature_ids"], "Xuanzhong alias lost its mapped object association"
            page.locator("#map-search").fill("宣忠")
            alias_matches = page.locator("#search-results [data-result-feature]")
            page.wait_for_function("document.querySelectorAll('#search-results [data-result-feature]').length > 0")
            result_ids = alias_matches.evaluate_all("nodes => nodes.map(n => n.dataset.resultFeature)")
            alias_id = next((fid for fid in alias["feature_ids"] if fid in result_ids), None)
            assert alias_id, ("Source-name alias did not reach its main-scene object", result_ids, alias["feature_ids"])
            page.locator(f'[data-result-feature="{alias_id}"]').click()
            expect(page.locator("#selected-title")).to_have_text(features[alias_id]["label"])
            painted(page)
            selected_camera = camera(page)
            query = parse_qs(urlsplit(page.url).query)
            assert query["q"] == ["宣忠"] and query["view"] == ["yongning"]
            assert query["feature"] == [alias_id]
            page.reload(wait_until="load")
            expect(page.locator("html")).to_have_attribute("data-plan-ready", "true")
            expect(page.locator("#view-select")).to_have_value("yongning")
            expect(page.locator("#map-search")).to_have_value("宣忠")
            expect(page.locator(f'[data-result-feature="{alias_id}"]')).to_be_visible()
            expect(page.locator("#selected-title")).to_have_text(features[alias_id]["label"])
            painted(page)
            same_camera(camera(page), selected_camera)
            # A deliberate new view supersedes a previously selected feature;
            # otherwise its saved feature zoom would wrongly win after reload.
            page.locator("#view-select").select_option("R04")
            painted(page)
            regional_camera = camera(page)
            regional_query = parse_qs(urlsplit(page.url).query)
            assert regional_query["view"] == ["R04"] and "feature" not in regional_query
            expect(page.locator("#city-plan-map .is-selected")).to_have_count(0)
            page.reload(wait_until="load")
            expect(page.locator("html")).to_have_attribute("data-plan-ready", "true")
            expect(page.locator("#view-select")).to_have_value("R04")
            painted(page)
            same_camera(camera(page), regional_camera)
            assert "feature" not in parse_qs(urlsplit(page.url).query)
            report["manual_view_after_feature"] = {"view": "R04", "camera": regional_camera,
                                                    "stale_feature_query_removed": True}
            page.locator("#map-search").fill("NO_MATCH_R11_8675309")
            expect(page.locator("#search-results [data-result-feature]")).to_have_count(0)
            page.locator("#clear-map-search").click()
            expect(page.locator("#map-search")).to_have_value("")
            expect(page.locator("#search-results")).to_be_empty()
            report["checks"].append("Feature-ID search, the 宣忠 alias, saved feature zoom and empty/reset search work; choosing R04 clears the old feature and reload restores the regional camera")

            open_fold(page, "coverage-fold")
            coverage_rows(page, data)
            for kind in ("source", "candidate", "unplaced"):
                page.locator("#coverage-kind").select_option(kind)
                coverage_rows(page, data, kind=kind)
            chosen = next(e for e in data["coverage"] if e["placement_group"] == "candidate")
            page.locator("#coverage-kind").select_option("candidate")
            page.locator("#coverage-search").fill(chosen["id"])
            coverage_rows(page, data, "candidate", chosen["id"])
            page.locator("#coverage-search").fill("NO_MATCH_R11_8675309")
            coverage_rows(page, data, "candidate", "NO_MATCH_R11_8675309")
            page.locator("#coverage-reset").click()
            coverage_rows(page, data)
            # A map search for an unplaced name must override a stale table kind.
            unplaced = next(e for e in data["coverage"] if e["placement_group"] == "unplaced")
            page.locator("#coverage-kind").select_option("source")
            page.locator("#map-search").fill(unplaced["id"])
            page.locator(f'#search-results a[href="#entity-{unplaced["id"]}"]').click()
            expect(page.locator("#coverage-kind")).to_have_value("all")
            expect(page.locator("#coverage-search")).to_have_value(unplaced["id"])
            expect(page.locator("#entity-" + unplaced["id"])).to_be_visible()
            page.locator("#coverage-reset").click()
            page.locator("#clear-map-search").click()
            coverage_rows(page, data)
            fits(page)
            close_fold(page, "coverage-fold")
            open_fold(page, "features-fold")
            page.locator(f'[data-focus-feature="{GATE}"]').click()
            expect(page.locator("#selected-title")).to_have_text(features[GATE]["label"])
            expect(page.locator("#selected-evidence a[href=\"#feature-" + GATE + "\"]")).to_be_visible()
            close_fold(page, "features-fold")
            page.locator("#view-select").select_option("palace2013")
            painted(page)
            capture(page.locator("#map-viewport"), "palace-comparison")
            assert geometry_snapshot(page) == original
            assert json.loads(page.locator("#plan-data").text_content()) == data
            report["checks"].append("All 339 coverage IDs and group/query counters agree; unplaced search overrides stale filters, table focus returns to real geometry, and no action rewrites coordinates")

            # One download attempt per released link, with real 150 ms mouse
            # presses. Do not retry blocked downloads or substitute request.get.
            with tempfile.TemporaryDirectory(prefix="city-plan-r11-offline-") as temporary:
                download_start = time.monotonic()
                expect(page.locator("a[data-download][download]")).to_have_count(len(meta["download_files"]))
                assert page.locator("a[data-download][download]").evaluate_all("nodes => nodes.map(n => n.dataset.download)") == meta["download_files"]
                bundle_seen = False
                for path in meta["download_files"]:
                    member = safe_member(path)
                    link = page.locator(f'a[data-download="{path}"][download]')
                    attempt_start = time.monotonic()
                    attempt = {"path": path, "href": link.get_attribute("href"), "status": "pending",
                               "started_seconds": round(attempt_start - download_start, 3), "click_delay_ms": 150}
                    report["download_attempts"].append(attempt)
                    report["attempt_path"] = path
                    with page.expect_download(timeout=20000) as event:
                        link.click(delay=150)
                    download = event.value
                    assert download.failure() is None, (path, download.failure())
                    relative = PurePosixPath("downloads") / device / member
                    retained = output / Path(relative)
                    retained.parent.mkdir(parents=True, exist_ok=True)
                    download.save_as(retained)
                    raw = retained.read_bytes()
                    checksum = digest(raw)
                    assert checksum == info["files_sha256"][path], path
                    report["downloads"][path] = checksum
                    report["retained_downloads"][path] = {"sha256": checksum, "bytes": len(raw), "retained_path": str(relative)}
                    attempt.update(status="passed", duration_seconds=round(time.monotonic() - attempt_start, 3),
                                   sha256=checksum, bytes=len(raw), suggested_filename=download.suggested_filename)
                    if path == meta["pdf"]:
                        report["pdf"] = pdf_audit(raw, data, info["source_commit"])
                    if path == meta["bundle"]:
                        with ZipFile(io.BytesIO(raw)) as archive:
                            names = archive.namelist()
                            assert len(names) == len(set(names))
                            assert set(names) == {"index.html", meta["manifest"], *meta["files_sha256"]}
                            for name in names:
                                safe_member(name)
                            for name, expected in meta["files_sha256"].items():
                                assert digest(archive.read(name)) == expected, ("ZIP member mismatch", name)
                            assert digest(archive.read(meta["manifest"])) == info["files_sha256"][meta["manifest"]]
                            archive.extractall(temporary)
                            report["offline_members"] = len(names)
                            bundle_seen = True
                    report["attempt_path"] = None
                assert bundle_seen and set(report["downloads"]) == set(meta["download_files"])
                assert report["pdf"]["pages"] == meta["pdf_details"]["pages"]

                with browser.new_context(**settings, offline=True) as disconnected:
                    disconnected.set_default_timeout(8000)
                    local = disconnected.new_page()
                    active = local
                    watch(local)
                    network = []
                    local.on("request", lambda request: network.append(request.url)
                             if request.url.startswith(("https://", "http://")) else None)
                    local.goto((Path(temporary) / meta["offline_entry"]).as_uri() + "?view=yongning", wait_until="load")
                    expect(local.locator("html")).to_have_attribute("data-plan-ready", "true")
                    assert json.loads(local.locator("#plan-data").text_content()) == data
                    expect(local.locator("#view-select")).to_have_value("yongning")
                    expect(local.locator("#city-plan-map")).to_be_visible()
                    # The inset SVGs intentionally use lazy loading. Bring them
                    # into view before requiring their local image resources.
                    for image in local.locator(".inset img").all():
                        image.scroll_into_view_if_needed()
                        expect(image).to_have_js_property("complete", True)
                        assert image.evaluate("n => n.naturalWidth > 0")
                    local.locator("#view-select").select_option("palace2013")
                    layer_count(local, "palace", 24)
                    local.locator("#map-search").fill(TOWER)
                    local.locator(f'[data-result-feature="{TOWER}"]').click()
                    expect(local.locator("#selected-title")).to_have_text(features[TOWER]["label"])
                    open_fold(local, "coverage-fold")
                    local.locator("#coverage-kind").select_option("unplaced")
                    coverage_rows(local, data, "unplaced")
                    close_fold(local, "coverage-fold")
                    assert geometry_snapshot(local) == original
                    fits(local)
                    capture(local.locator("#map-viewport"), "offline")
                    assert not network, ("Offline package requested remote resources", network)
                    report["offline_network_requests"] = network
                    report["offline_network_disabled"] = True
            active = page
            report["checks"].append("Every download is a genuine paced click with released hash, retained bytes and a single attempt; PDF paper sizes/text/embedded fonts and every ZIP member are checked; the offline UI runs with network disabled")

            with browser.new_context(**settings, java_script_enabled=False) as disabled:
                disabled.set_default_timeout(8000)
                plain = disabled.new_page()
                active = plain
                watch(plain)
                plain.goto(base + PAGE, wait_until="load")
                expect(plain.locator(".no-js-note")).to_be_visible()
                expect(plain.locator("#city-plan-map")).to_be_visible()
                assert json.loads(plain.locator("#plan-data").text_content()) == data
                open_fold(plain, "features-fold")
                expect(plain.locator(".feature-row:visible")).to_have_count(len(features))
                open_fold(plain, "coverage-fold")
                coverage_rows(plain, data, counts=False)
                native_link = plain.locator(f'.coverage-row a[href="#feature-{TOWER}"]').first
                expect(native_link).to_be_visible()
                native_link.click()
                expect(plain.locator("#feature-" + TOWER)).to_be_in_viewport()
                evidence = plain.locator("#feature-" + TOWER + " details").first
                evidence.locator(":scope > summary").click()
                expect(evidence.locator(".source-list a").first).to_be_visible()
                expect(plain.locator("a[data-download][download]")).to_have_count(len(meta["download_files"]))
                fits(plain)
                capture(plain, "without-javascript")
            active = page
            report["checks"].append("Without JavaScript the common-plane SVG, every feature and all 339 catalog objects remain readable; native evidence links and disclosure controls work")
            assert not report["errors"], report["errors"]
            report["status"] = "passed"
        except Exception as error:
            target = active if active and not active.is_closed() else page
            report.update(status="failed", error=str(error), url=target.url)
            if report.get("attempt_path") and report["download_attempts"]:
                report["download_attempts"][-1].update(status="failed", error=str(error))
            try:
                if not target.is_closed():
                    capture(target, "failure")
            except Exception as capture_error:
                report["failure_screenshot_error"] = str(capture_error)
            raise
        finally:
            report["elapsed_seconds"] = round(time.monotonic() - started, 3)
            (output / (device + "-report.json")).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url")
    parser.add_argument("--commit")
    parser.add_argument("--output", default="artifacts/city-plan-r11-browser")
    parser.add_argument("--browser-executable")
    args = parser.parse_args()
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    combined = {"status": "running", "base_url": args.base_url, "expected_commit": args.commit,
                "devices": {}, "no_policy_workarounds": True}
    try:
        with base_url(args.base_url) as base, sync_playwright() as playwright:
            executable = args.browser_executable or os.environ.get("CHROMIUM_PATH")
            browser = playwright.chromium.launch(**({"executable_path": executable} if executable else {}))
            try:
                for device in SIZES:
                    report = exercise(browser, base, device, output, args.commit)
                    combined["devices"][device] = report
                    print(f"PASS R11 {device}: {len(report['checks'])} groups, {len(report['downloads'])} downloads, {report['elapsed_seconds']}s", flush=True)
            finally:
                browser.close()
        combined["status"] = "passed"
    except Exception as error:
        combined.update(status="failed", error=str(error))
        for device in SIZES:
            path = output / (device + "-report.json")
            if path.exists():
                combined["devices"][device] = json.loads(path.read_text(encoding="utf-8"))
        raise
    finally:
        combined["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (output / "report.json").write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
