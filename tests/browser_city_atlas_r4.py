"""Real browser journeys for the city atlas locally, from Pages, and from its offline ZIP."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright
from browser_layout import assert_loaded_viewport
from browser_city_west_p472 import SIZES, base_url

ROOT=Path(__file__).resolve().parents[1]
PAGE="prosperity-city-atlas.html"
KEY="prosperity_city_atlas_r4"


def exercise(browser,base,device,output):
    settings={"viewport":SIZES[device],"accept_downloads":True}
    report={"device":device,"checks":[],"downloads":{},"screenshots":{},"errors":[]}
    def capture(locator,name):
        name=device+"-"+name+".png"
        report["screenshots"][name]=hashlib.sha256(locator.screenshot(path=output/name)).hexdigest()
    with browser.new_context(**settings) as ctx:
        p=ctx.new_page()
        p.on("pageerror",lambda err:report["errors"].append(str(err)))
        try:
            info=ctx.request.get(base+"build-info.json").json(); meta=info[KEY]
            report["source_commit"]=info["source_commit"]
            p.goto(base,wait_until="load")
            p.locator("#r4-atlas-entry a").click()
            expect(p.locator("h1")).to_have_text("盛时洛阳城市分布总图")
            expect(p.locator("[data-object]")).to_have_count(339)
            expect(p.locator("#view-city")).to_be_visible()
            assert_loaded_viewport(p, tolerance=0, report=report)
            capture(p.locator("#view-city figure"),"overview")
            p.locator("[data-tab=core]").click()
            p.locator("#modern").check()
            p.locator("#candidate").uncheck()
            assert "modern=1" in p.url and "candidate=0" in p.url
            p.reload(wait_until="load")
            expect(p.locator("#modern")).to_be_checked(); expect(p.locator("#candidate")).not_to_be_checked()
            with p.expect_download() as event:p.locator("#export-view").click()
            saved=ET.parse(event.value.path()).getroot()
            assert saved.find(".//*[@data-layer='candidate']").get("display")=="none"
            assert saved.find(".//*[@data-layer='modern']").get("display") is None
            a=p.locator('#view-core a[href="#feature-geo-jianchun-gate"]').last
            a.click()
            expect(p.locator("#feature-geo-jianchun-gate")).to_have_attribute("open","")
            expect(p.locator("#feature-geo-jianchun-gate")).to_contain_text("100")
            report["checks"].append("Homepage, native source feature, shared layer URL, filtered SVG download")

            p.locator('[data-tab="relations"]').click()
            p.locator('#view-relations [data-reading="B2:G13"]').click()
            g13=p.locator('[id="reading-B2:G13"]')
            expect(g13).to_have_attribute("open","");expect(g13.locator("blockquote")).to_contain_text("柰林西有都堂")
            p.goto(base+PAGE+"#reading-B4:NG15");ng=p.locator('[id="reading-B4:NG15"]')
            expect(ng).to_contain_text("现代夹注")
            assert "西北門" not in ng.locator("blockquote").inner_text()
            capture(ng,"corrected-reading")
            p.goto(base+PAGE+"#view-literary")
            shared=p.locator('#view-literary [data-target-id="target-029"]')
            shared.click()
            expect(p.locator("#group-target-029")).to_have_attribute("open","")
            p.locator('#group-target-029 [href="#entity-ic_jianzhong"]').click()
            expect(p.locator("#entity-ic_jianzhong")).to_contain_text("改寺")
            report["checks"].append("Regional relation, corrected quote and modern annotation, shared literary symbol and individual object")

            p.goto(base+PAGE+"#coverage");p.locator('[data-filter-region="R09"]').click()
            expect(p.locator("#region")).to_have_value("R09")
            p.locator("#period").select_option("conditional")
            p.locator("#q").fill("宝明")
            expect(p.locator("[data-object]:visible")).to_have_count(1)
            p.reload(wait_until="load")
            expect(p.locator("#q")).to_have_value("宝明")
            expect(p.locator("[data-object]:visible")).to_have_count(1)
            p.locator("#entity-v2_baoming > summary").click()
            expect(p.locator("#entity-v2_baoming")).to_contain_text("前期身份有条件")
            assert_loaded_viewport(p, tolerance=0, report=report)
            capture(p.locator("#entity-v2_baoming"),"baoming")
            p.locator("#q").fill("missing-000");expect(p.locator("#matched")).to_contain_text("没有符合条件")
            p.locator("#reset").click();expect(p.locator("[data-object]:visible")).to_have_count(339)
            p.goto(base+PAGE+"#water-W20")
            w=p.locator("#water-W20");expect(w).to_have_attribute("open","");expect(w).to_contain_text("撤回")
            w.locator('a[href^="#channel-"]').first.click()
            expect(p.locator('[id="channel-P468/palace-pools-audit/H01"]')).to_have_attribute("open","")
            p.goto(base+PAGE+"#jianchun-control");expect(p.locator("#jianchun-control")).to_contain_text("确认点对　0")
            report["checks"].append("Region, period and name filters, restored query, empty results, source limits, corrected water links")

            with tempfile.TemporaryDirectory() as tmp:
                for path in meta["download_files"]:
                    with p.expect_download() as event:p.locator(f'[download][href="./{path}"]').click()
                    f=Path(event.value.path())
                    checksum=hashlib.sha256(f.read_bytes()).hexdigest()
                    assert checksum==info["files_sha256"][path],path
                    report["downloads"][path]=checksum
                    if path==meta["bundle"]:
                        with ZipFile(f) as z:z.extractall(tmp)
                with browser.new_context(**settings,offline=True) as black:
                    offline=black.new_page();offline.goto((Path(tmp)/"index.html").as_uri()+"#entity-gate_changhe_west")
                    expect(offline.locator("#entity-gate_changhe_west")).to_have_attribute("open","")
                    offline.locator('[data-tab="qian"]').click()
                    assert offline.locator("#view-qian img").evaluate("im => im.complete && im.naturalWidth>0")
                    expect(offline.locator("[data-object]")).to_have_count(339)
            with browser.new_context(**settings,java_script_enabled=False) as plain:
                n=plain.new_page();n.goto(base+PAGE+"#view-relations")
                n.locator('#view-relations [data-entity="ic_nailin"]').click()
                n.locator("#entity-ic_nailin > summary").click()
                expect(n.locator("#entity-ic_nailin")).to_contain_text("文献")
                assert_loaded_viewport(n, tolerance=0, report=report)
            report["checks"].append("Eleven public downloads with hashes, offline ZIP, native navigation without JavaScript")
            assert not report["errors"],report["errors"]
            report["status"]="passed"
        except Exception as e:
            report.update(status="failed",url=p.url,error=str(e));p.screenshot(path=output/(device+"-failure.png"));raise
        finally:
            (output/(device+"-report.json")).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--output",default="artifacts/city-atlas-r4-browser")
    args=parser.parse_args(); output=ROOT/args.output;output.mkdir(exist_ok=True,parents=True)
    with base_url(args.base_url) as base,sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            for device in SIZES:exercise(browser,base,device,output)
        finally:browser.close()
