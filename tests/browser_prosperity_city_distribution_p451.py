#!/usr/bin/env python3
"""P4.5.1 website acceptance: original source geometry, selectable points, downloadable evidence."""
import argparse
import functools
import http.server
import json
import os
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import expect,sync_playwright

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument("--base-url")
parser.add_argument("--output",default="artifacts/prosperity-city-distribution-p451-browser")
args=parser.parse_args()
OUT=ROOT/args.output
OUT.mkdir(parents=True,exist_ok=True)
server=None;temporary=None;passes=[];errors=[]
if args.base_url:
    base=args.base_url.rstrip("/")+"/"
else:
    temporary=tempfile.TemporaryDirectory()
    tmp=Path(temporary.name)
    (tmp/"luoyang-city").symlink_to(ROOT/"_site",target_is_directory=True)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*unused):pass
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),
        functools.partial(Quiet,directory=tmp))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}/luoyang-city/"
def ok(s):
    passes.append(s)
    print("PASS",s,flush=True)
def no_overflow(p):
    assert p.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
try:
    with sync_playwright() as pw:
        options={"headless":True}
        if os.environ.get("CHROMIUM_PATH"):
            options["executable_path"]=os.environ["CHROMIUM_PATH"]
        browser=pw.chromium.launch(**options)
        ctx=browser.new_context(viewport={"width":1480,"height":950})
        page=ctx.new_page()
        page.on("pageerror",lambda err:errors.append(str(err)))
        response=page.goto(base+"prosperity-city-distribution.html",wait_until="networkidle")
        assert response.status==200
        page.wait_for_function('document.documentElement.dataset.p451Ready==="true"')
        expect(page.locator("h1")).to_contain_text("城市骨架")
        expect(page.locator(".source-binding")).to_have_count(4)
        expect(page.locator("button[data-select-binding]")).to_have_count(4)
        assert page.locator("#map svg").count()==1
        assert page.locator("#map svg [data-feature-id]").count()>=30
        no_overflow(page)
        page.screenshot(path=str(OUT/"desktop.png"),full_page=True)
        ok("Desktop renders four selectable source-map anchors without adding geodetic locations")
        for binding in ("C02","C03","C04","C01"):
            page.locator(f'button[data-select-binding="{binding}"]').click()
            expect(page.locator(f'.source-binding[data-binding-id="{binding}"]')).to_have_attribute("data-selected","true")
            expect(page.locator(f'button[data-select-binding="{binding}"]')).to_have_attribute("aria-pressed","true")
            assert f"focus={binding}" in page.url
            expect(page.locator("#selected-reading")).to_contain_text("来源图")
        page.reload(wait_until="networkidle")
        page.wait_for_function('document.documentElement.dataset.p451Ready==="true"')
        expect(page.locator('button[data-select-binding="C01"]')).to_have_attribute("aria-pressed","true")
        page.locator('.source-binding[data-binding-id="C02"]').click()
        expect(page.locator('button[data-select-binding="C02"]')).to_have_attribute("aria-pressed","true")
        page.reload(wait_until="networkidle")
        page.wait_for_function('document.documentElement.dataset.p451Ready==="true"')
        expect(page.locator('button[data-select-binding="C02"]')).to_have_attribute("aria-pressed","true")
        ok("Selection from cards or original map markers updates the evidence, URL and reloaded focus")
        out=ctx.request.get(base+"prosperity-city-distribution/data.json")
        assert out.status==200
        d=out.json()
        assert d["version"]=="prosperity-city-distribution-p451"
        assert len(d["anchored_buildings"])==4
        assert len(d["unplaced_p44_types"])==4
        assert d["source_map_overlay"]["new_historical_coordinates_added"]==0
        assert d["source_map_overlay"]["original_base_map_sha256"]
        for item,prefix in [
            ("prosperity-city-distribution/grounded-distribution.svg",b"<?xml"),
            ("prosperity-city-distribution/scale-plates.svg",b"<?xml"),
            ("prosperity-city-distribution/evidence-tiers.svg",b"<?xml"),
            ("prosperity-city-distribution/measurements.csv",None),
            ("downloads/prosperity-city-distribution-p451-atlas.pdf",b"%PDF"),
            ("downloads/prosperity-city-distribution-p451-package.zip",b"PK")
        ]:
            res=ctx.request.get(base+item)
            assert res.status==200,(item,res.status)
            assert len(res.body())>100,item
            if prefix: assert res.body().lstrip().startswith(prefix),item
        approved=ctx.request.get(base+"homepage/approval-v9.json").json()
        assert approved["hero"]["revision"]=="panorama-approved-v9"
        index=ctx.request.get(base+"index.html")
        assert index.status==200
        assert b'prosperity-p451-entry' in index.body()
        ok("Published SVG/PDF/ZIP/CSV/JSON and H2-approved homepage link resolve on the same host")
        mobile=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        m=mobile.new_page()
        m.on("pageerror",lambda err:errors.append(str(err)))
        r=m.goto(base+"prosperity-city-distribution.html?focus=C04",wait_until="networkidle")
        assert r.status==200
        m.wait_for_function('document.documentElement.dataset.p451Ready==="true"')
        expect(m.locator('button[data-select-binding="C04"]')).to_have_attribute("aria-pressed","true")
        no_overflow(m)
        for img in m.locator(".diagram img").all():
            assert img.evaluate("(el)=>el.complete&&el.naturalWidth>0")
        m.locator('button[data-select-binding="C03"]').tap()
        expect(m.locator('button[data-select-binding="C03"]')).to_have_attribute("aria-pressed","true")
        no_overflow(m)
        m.screenshot(path=str(OUT/"mobile.png"),full_page=True)
        mobile.close()
        ok("390px mobile shows full evidence maps, source content and working tap selection")
        passive=browser.new_context(viewport={"width":700,"height":900},java_script_enabled=False)
        p=passive.new_page()
        p.goto(base+"prosperity-city-distribution.html",wait_until="networkidle")
        assert p.locator('button[data-select-binding]').count()==4
        assert p.locator(".source-binding").count()==4
        assert p.locator(".diagram img").count()==2
        no_overflow(p)
        passive.close()
        ok("All static source diagrams and explanatory data stay readable without JavaScript")
        assert not errors,errors
        ctx.close();browser.close()
finally:
    (OUT/"report.json").write_text(json.dumps({
      "base_url":base,"checks":passes,"browser_errors":errors},ensure_ascii=False,indent=2)+"\n",
      encoding="utf-8")
    if server:server.shutdown()
    if temporary:temporary.cleanup()
