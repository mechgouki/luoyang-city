"""Desktop, mobile, no-JavaScript, and offline acceptance for the published panorama."""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright
from browser_layout import assert_loaded_viewport
from browser_city_west_p472 import base_url, SIZES

ROOT=Path(__file__).resolve().parents[1]
PAGE="prosperity-city-panorama.html"


def exercise(browser,base,device,out):
    report={"device":device,"checks":[],"downloads":{},"screenshots":{},"errors":[]}
    def capture(locator,label):
        name=device+"-"+label+".png"
        report["screenshots"][name]=hashlib.sha256(locator.screenshot(path=out/name)).hexdigest()
    opts={"viewport":SIZES[device],"is_mobile":device=="mobile","has_touch":device=="mobile"}
    with browser.new_context(**opts,accept_downloads=True) as ctx:
        p=ctx.new_page();p.on("pageerror",lambda e:report["errors"].append(str(e)))
        try:
            info=ctx.request.get(base+"build-info.json").json();meta=info["prosperity_city_panorama_r5"]
            report["source_commit"]=info["source_commit"]
            p.goto(base,wait_until="load");p.locator("#r5-panorama-entry a").click()
            p.wait_for_url("**/" + PAGE, wait_until="load", timeout=30_000)
            expect(p.locator("h1")).to_have_text("盛时洛阳全景")
            p.locator(".illustration img").evaluate("(im)=>im.decode()")
            assert ("panorama-small.webp" if device=="mobile" else "panorama.webp") in p.locator(".illustration img").evaluate("im=>im.currentSrc")
            expect(p.locator("#art")).to_be_visible()
            p.locator("#show-anchors").check();expect(p.locator(".overlay")).to_be_visible()
            expect(p.locator(".overlay [data-anchor]")).to_have_count(4)
            capture(p.locator(".illustration"),"landmarks")
            p.locator(".tabbar [href='#core']").click();expect(p.locator("#core")).to_be_visible()
            expect(p.locator("#art")).to_be_hidden()
            p.reload(wait_until="load");expect(p.locator("#core")).to_be_visible()
            capture(p.locator("#core .canvas"),"core")
            p.locator("#core [data-label=C04]").click();assert p.url.endswith("#C04")
            p.locator("#C04 a").first.click();assert p.url.endswith("#feature-geo-yongning-pagoda-reference")
            p.goto(base+"prosperity-city-atlas.html");p.locator("#r5-panorama-entry a").click()
            p.wait_for_url("**/" + PAGE, wait_until="load", timeout=30_000)
            p.locator(".tabbar [href='#city']").click();expect(p.locator("#city")).to_be_visible()
            p.locator(".tabbar [href='#art']").click();expect(p.locator("#art")).to_be_visible()
            p.go_back();expect(p.locator("#city")).to_be_visible()
            assert_loaded_viewport(p, tolerance=0, report=report)
            report["checks"].append("Two entrances, responsive artwork, four comparison marks, source cards and restoration of shared views")
            p.locator(".tabbar [href='#palace-east']").click()
            expect(p.locator("#palace-east")).to_be_visible()
            expect(p.locator("#palace-east article")).to_have_count(4)
            p.locator("#palace-east img").evaluate("im=>im.decode()")
            p.reload(wait_until="load")
            expect(p.locator("#east-title")).to_be_visible()
            assert_loaded_viewport(p, tolerance=0, report=report)
            capture(p.locator("#palace-east figure img"),"palace-east")
            p.locator("#palace-east [href='#sima-road']").click()
            expect(p.locator("#sima-title")).to_be_visible()
            p.reload(wait_until="load")
            expect(p.locator("#sima-road")).to_contain_text("39.3")
            p.locator("#sima-road img").evaluate("im=>im.decode()")
            assert_loaded_viewport(p, tolerance=0, report=report)
            capture(p.locator("#sima-road figure img"),"sima-road")
            with ctx.new_page() as water:
                water.goto(base+PAGE)
                water.get_by_role("link",name="河流与水系定位图集").click()
                expect(water.locator(".grid article")).to_have_count(34)
                water.locator("#query").fill("W21")
                expect(water.locator("article:not([hidden])[id^=W]")).to_have_count(1)
                water.locator("#clear").click()
                water.locator("svg a[href='#W30']").last.click()
                expect(water.locator("#W30")).to_be_in_viewport()
                water.reload()
                expect(water.locator("#W30")).to_be_in_viewport()
                assert_loaded_viewport(water, tolerance=0, report=report)
                for filename in ["water-locations.csv","water-location-data.json","downloads/luoyang-water-atlas.zip"]:
                    blob=ctx.request.get(base+filename)
                    assert blob.ok and hashlib.sha256(blob.body()).hexdigest()==info["files_sha256"][filename]
                water.screenshot(path=out/(device+"-water.png"))
            with tempfile.TemporaryDirectory() as tmp:
                for path in meta["download_files"]:
                    with p.expect_download() as ev:p.locator(f'[download][href="./{path}"]').click()
                    checksum=hashlib.sha256(Path(ev.value.path()).read_bytes()).hexdigest()
                    assert checksum==info["files_sha256"][path];report["downloads"][path]=checksum
                    if path==meta["bundle"]:
                        with ZipFile(ev.value.path()) as z:z.extractall(tmp)
                with browser.new_context(**opts,offline=True) as off:
                    page=off.new_page();page.goto((Path(tmp)/"index.html").as_uri())
                    page.locator(".illustration img").evaluate("(im)=>im.decode()")
                    page.locator(".tabbar [href='#palace-east']").click()
                    page.locator("#palace-east img").evaluate("im=>im.decode()")
                    expect(page.locator("#palace-east")).to_contain_text("东围墙")
                    page.locator("#palace-east [href='#sima-road']").click()
                    expect(page.locator("#sima-road")).to_contain_text("仓区西墙")
                    page.locator("#sima-road img").evaluate("im=>im.decode()")
                    page.locator(".tabbar [href='#city']").click();expect(page.locator("#city")).to_be_visible()
                    page.locator("#city [data-label=C03]").click();expect(page.locator("#C03")).to_contain_text("太极殿")
            with browser.new_context(**opts,java_script_enabled=False) as disabled:
                page=disabled.new_page();page.goto(base+PAGE+"#core")
                expect(page.locator("#core")).to_be_visible();expect(page.locator("#city")).to_be_visible()
                assert_loaded_viewport(page, tolerance=0, report=report)
            report["checks"].append("Eight actual downloads, verified hashes, disconnected artwork and models, native no-JavaScript navigation")
            assert not report["errors"];report["status"]="passed"
        except Exception as e:
            report.update(status="failed",error=str(e));p.screenshot(path=out/(device+"-failure.png"));raise
        finally:
            (out/(device+"-report.json")).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--base-url");parser.add_argument("--output",default="artifacts/city-panorama-r5-browser")
    args=parser.parse_args();out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True)
    with base_url(args.base_url) as base,sync_playwright() as playwright:
        browser=playwright.chromium.launch()
        try:
            for device in SIZES:exercise(browser,base,device,out)
        finally:browser.close()
