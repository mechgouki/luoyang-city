"""Use the normal pinned CI browser to exercise the west maps on both viewports."""
import argparse
from contextlib import contextmanager
import functools
import hashlib
import http.server
import json
from pathlib import Path
import tempfile
import threading
import zipfile

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = "prosperity-city-west.html"
NORTH = "prosperity-city-north.html"
SIZES = {"desktop":{"width":1440,"height":960}, "mobile":{"width":390,"height":844}}


@contextmanager
def base_url(url):
    if url:
        yield url.rstrip("/")+"/"
        return
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp)/"luoyang-city").symlink_to(ROOT/"_site",target_is_directory=True)
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self,*args):
                pass
        with http.server.ThreadingHTTPServer(("127.0.0.1",0), functools.partial(Quiet,directory=tmp)) as server:
            thread = threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                yield f"http://127.0.0.1:{server.server_port}/luoyang-city/"
            finally:
                server.shutdown()
                thread.join()


def exercise(browser, base, device, output):
    size = SIZES[device]
    settings = dict(viewport=size, is_mobile=device=="mobile", has_touch=device=="mobile", reduced_motion="reduce")
    context = browser.new_context(**settings,accept_downloads=True)
    page = context.new_page()
    report = {"device":device,"viewport":size,"checks":[],"screenshots":{},"downloads":{},"errors":[]}
    page.on("pageerror",lambda err:report["errors"].append(str(err)))
    def capture(where, label):
        name = device+"-"+label+".png"
        content = where.screenshot(path=str(output/name),animations="disabled")
        report["screenshots"][name] = hashlib.sha256(content).hexdigest()
    def width_check(view, record_id, mode):
        width = size["width"]
        box = view.locator("#"+record_id).bounding_box()
        assert box and box["x"] >= -1 and box["x"]+box["width"] <= width+1, (mode,width,box)
        scroll = view.locator("html").evaluate("node => node.scrollWidth")
        assert scroll <= width+1, (mode,width,scroll)
        report.setdefault("expanded_widths",{})[mode] = {"viewport":width, "card":box["width"], "document":scroll}

    def count(number):
        expect(page.locator("[data-record]:visible")).to_have_count(number)
    try:
        info = page.request.get(base+"build-info.json").json()
        meta = info["prosperity_city_west_p472"]
        report["source_commit"] = info["source_commit"]
        page.goto(base+NORTH)
        page.locator("#p472-entry a").click()
        page.wait_for_url("**/"+PAGE)
        expect(page.locator("html")).to_have_class("enhanced")
        count(24)
        assert page.locator("html").evaluate("node => node.scrollWidth") <= size["width"]+1
        capture(page.locator("#source-plate"),"source")
        capture(page.locator("#relations-plate"),"relations")
        report["checks"].append("P471 entry, both readable plates and viewport fit")

        for point, records in (("gate_xiyang",4),("gate_ximing",2),("ic_changhe_palace",1)):
            page.locator(f'#west-source a[data-entity="{point}"] [data-point]').click()
            count(records)
            expect(page.locator("#west-source .picked")).to_have_attribute("data-entity",point)
            expect(page.locator("#entity-"+point)).to_contain_text("来源图符")
        page.locator('#entity-gate_changhe_west > a').click()
        count(3)
        expect(page.locator("#west-source .picked")).to_have_count(0)
        expect(page.locator("#entity-gate_changhe_west")).to_contain_text("未定位")
        capture(page.locator("#entity-gate_changhe_west"),"unlocated")
        report["checks"].append("All three original gate symbols and unlocated west Changhe identity")

        page.locator("#show-roads").uncheck()
        expect(page.locator('[data-layer="source-roads"]')).to_be_hidden()
        expect(page.locator('[data-layer="source-walls"]')).to_be_visible()
        page.locator("#show-roads").check()
        for identifier in ("source-plate","relations-plate"):
            button = page.locator(f'[data-zoom="{identifier}"]')
            button.click()
            area = page.locator("#"+identifier)
            assert area.evaluate("n => n.scrollWidth > n.clientWidth")
            area.focus()
            page.keyboard.press("ArrowRight")
            page.wait_for_function("id => document.getElementById(id).scrollLeft > 0",arg=identifier)
            button.click()
            expect(button).to_have_attribute("aria-pressed","false")
        report["checks"].append("Road overlay, both zooms, keyboard horizontal scroll and reset")

        for key,n in (("order",2),("changhe",9),("xiyang",11),("ximing",2)):
            page.locator(f'.chips a[href="#group-{key}"]').click()
            count(n)
        page.locator('.chips a[href="#records"]').click()
        count(24)
        page.locator('#west-relations [href="#WR08"]').click()
        count(1)
        for _ in range(2):
            expect(page.locator("#WR08 details")).to_have_attribute("open","")
            expect(page.locator("#WR08 blockquote")).to_contain_text("〔立〕")
            expect(page.locator("#WR08 details")).to_contain_text("留环")
            bounds = page.locator("#WR08").bounding_box()
            assert bounds and 0 <= bounds["y"] < size["height"], bounds
            page.reload()
        capture(page.locator("#WR08"),"edited-reading")
        page.locator('.chips a[href="#group-ximing"]').click()
        page.go_back()
        expect(page.locator("#WR08 details")).to_be_visible()
        count(1)
        page.goto(base+PAGE+"#WR18")
        expect(page.locator("#WR18 details")).to_have_attribute("open","")
        width_check(page,"WR18","javascript")
        report["checks"].append("Four groups, source lines, WR08 deep link, reload, history and expanded WR18 width")

        for path in meta["download_files"]:
            anchor = page.locator(f'a[download][href="./{path}"]')
            with page.expect_download(timeout=30000) as event:
                anchor.click()
            download = event.value
            assert download.failure() is None and download.url == base+path, download.url
            target = output/"downloads"/device/Path(path).name
            target.parent.mkdir(parents=True,exist_ok=True)
            download.save_as(target)
            checksum = hashlib.sha256(target.read_bytes()).hexdigest()
            assert checksum == info["files_sha256"][path],path
            report["downloads"][path]=checksum
            page.wait_for_timeout(160)
        with zipfile.ZipFile(output/"downloads"/device/"west-472.zip") as archive:
            assert len(archive.namelist()) == 9
            with tempfile.TemporaryDirectory() as tmp:
                archive.extractall(tmp)
                offline = context.new_page()
                offline.goto((Path(tmp)/"index.html").as_uri()+"#WR24")
                expect(offline.locator("#WR24 details")).to_have_attribute("open","")
                expect(offline.locator("#WR24")).to_contain_text("同一性")
                expect(offline.locator("#WR23")).to_be_hidden()
                capture(offline.locator("#WR24"),"offline-baima")
                offline.close()
        report["checks"].append("Seven real downloads with SHA-256, nine ZIP members, offline file interaction")
        with browser.new_context(**settings,java_script_enabled=False) as plain:
            nojs = plain.new_page()
            nojs.goto(base+PAGE+"#relations")
            expect(nojs.locator("[data-record]:visible")).to_have_count(24)
            expect(nojs.locator("[data-object]:visible")).to_have_count(22)
            nojs.locator('#west-relations [href="#WR18"]').click()
            nojs.wait_for_url("**/"+PAGE+"#WR18")
            nojs.locator("#WR18 summary").click()
            expect(nojs.locator("#WR18 details")).to_contain_text("528年前必定竣工")
            width_check(nojs,"WR18","no_javascript")
            capture(nojs.locator("#WR18"),"nojs-period")
        report["checks"].append("No-JS native map jump, all records, all objects and phase limits")
        assert not report["errors"],report["errors"]
        report["status"]="passed"
        print(f"PASS P472 {device}: {len(report['checks'])} groups, {len(report['downloads'])} downloads, {len(report['screenshots'])} screenshots",flush=True)
    except Exception as error:
        report.update(status="failed",failure=str(error),url=page.url)
        page.screenshot(path=str(output/(device+"-failure.png")))
        raise
    finally:
        (output/(device+"-report.json")).write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
        context.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--output",default="artifacts/city-west-p472-browser")
    args = parser.parse_args()
    output = ROOT/args.output
    output.mkdir(parents=True,exist_ok=True)
    with base_url(args.base_url) as base, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for device in SIZES:
                exercise(browser,base,device,output)
        finally:
            browser.close()
