#!/usr/bin/env python3
"""P4.5.2 real desktop/mobile browser: 8 exact source roads, 5 textual contexts."""
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
parser.add_argument("--output",default="artifacts/prosperity-road-functions-p452-browser")
args=parser.parse_args()
OUT=ROOT/args.output;OUT.mkdir(parents=True,exist_ok=True)
passes=[];errors=[];server=None;temporary=None
if args.base_url:
    base=args.base_url.rstrip("/")+"/"
else:
    temporary=tempfile.TemporaryDirectory()
    parent=Path(temporary.name)
    (parent/"luoyang-city").symlink_to(ROOT/"_site",target_is_directory=True)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),
       functools.partial(Quiet,directory=parent))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}/luoyang-city/"
def ok(x):passes.append(x);print("PASS",x,flush=True)
def ready(p):p.wait_for_function("document.documentElement.dataset.roadP452Ready==='true'")
def fit(p):assert p.evaluate("document.documentElement.scrollWidth <= innerWidth+2")
try:
    with sync_playwright() as pw:
        opt={"headless":True}
        if os.environ.get("CHROMIUM_PATH"):
            opt["executable_path"]=os.environ["CHROMIUM_PATH"]
        browser=pw.chromium.launch(**opt)
        ctx=browser.new_context(viewport={"width":1420,"height":940})
        page=ctx.new_page()
        page.on("pageerror",lambda err:errors.append(str(err)))
        res=page.goto(base+"prosperity-road-functions.html",wait_until="networkidle")
        assert res.status==200
        ready(page)
        expect(page.locator("h1")).to_contain_text("路网残段")
        expect(page.locator(".road-group")).to_have_count(8)
        expect(page.locator("button[data-road-control]")).to_have_count(8)
        expect(page.locator("button[data-context]")).to_have_count(5)
        expect(page.locator(".directory article")).to_have_count(5)
        fit(page)
        page.screenshot(path=str(OUT/"desktop.png"),full_page=True)
        ok("Desktop displays eight source-map road remnants and five separate documentary contexts")
        for road in ("D03","D08","D01"):
            b=page.locator(f'button[data-road-control="{road}"]')
            b.click()
            expect(b).to_have_attribute("aria-pressed","true")
            expect(page.locator(f'.road-group[data-road-id="{road}"]')).to_have_attribute("data-active","true")
            assert f"road={road}" in page.url
            expect(page.locator("#road-reading")).to_contain_text("来源图")
        m=page.locator('.road-group[data-road-id="D02"]')
        m.focus()
        m.press("Enter")
        expect(page.locator('button[data-road-control="D02"]')).to_have_attribute("aria-pressed","true")
        for ident in ("R02","R04","R05"):
            btn=page.locator(f'button[data-context="{ident}"]')
            btn.click()
            expect(btn).to_have_attribute("aria-pressed","true")
            assert f"context={ident}" in page.url
            expect(page.locator("#context-detail")).to_contain_text("不能推出")
        page.reload(wait_until="networkidle")
        ready(page)
        expect(page.locator('button[data-road-control="D02"]')).to_have_attribute("aria-pressed","true")
        expect(page.locator('button[data-context="R05"]')).to_have_attribute("aria-pressed","true")
        ok("Road cards, map keyboard selection, text contexts and URL deep links update real evidence")
        data=ctx.request.get(base+"prosperity-road-functions/data.json").json()
        assert data["version"]=="prosperity-road-functions-p452"
        assert len(data["road_source_details"])==8
        assert data["source_map_overlay"]["new_street_connections_added"]==0
        assert data["source_map_overlay"]["new_historical_coordinates_added"]==0
        assert not data["data_lineage"]["modern_river_used_as_ancient_river"]
        for asset,prefix in [
            ("prosperity-road-functions/road-evidence-map.svg",b"<?xml"),
            ("prosperity-road-functions/qualitative-relations.svg",b"<?xml"),
            ("prosperity-road-functions/function-layers.svg",b"<?xml"),
            ("prosperity-road-functions/source-roads.csv",None),
            ("prosperity-road-functions/text-contexts.csv",None),
            ("downloads/prosperity-road-functions-p452-atlas.pdf",b"%PDF-"),
            ("downloads/prosperity-road-functions-p452-package.zip",b"PK")
        ]:
            req=ctx.request.get(base+asset)
            assert req.status==200,(asset,req.status)
            assert len(req.body())>100
            if prefix:assert req.body().lstrip().startswith(prefix),asset
        before=ctx.request.get(base+"prosperity-city-distribution.html")
        assert before.status==200
        assert b'prosperity-road-functions.html' in before.body()
        current=ctx.request.get(base+"homepage/approval-v9.json").json()
        assert current["hero"]["revision"]=="panorama-approved-v9"
        ok("New PDF/ZIP/SVG/CSV/JSON download; approved H2 hero and P4.5.1 upstream link preserved")
        mobile=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        m=mobile.new_page()
        m.on("pageerror",lambda err:errors.append(str(err)))
        rsp=m.goto(base+"prosperity-road-functions.html?road=D05&context=R04",wait_until="networkidle")
        assert rsp.status==200
        ready(m)
        fit(m)
        expect(m.locator('button[data-road-control="D05"]')).to_have_attribute("aria-pressed","true")
        expect(m.locator('button[data-context="R04"]')).to_have_attribute("aria-pressed","true")
        for img in m.locator(".diagram img").all():
            assert img.evaluate("(el)=>el.complete&&el.naturalWidth>0")
        m.locator('button[data-road-control="D07"]').tap()
        expect(m.locator('button[data-road-control="D07"]')).to_have_attribute("aria-pressed","true")
        fit(m)
        m.screenshot(path=str(OUT/"mobile.png"),full_page=True)
        mobile.close()
        ok("390px mobile displays both relation diagrams without overflow and permits real taps")
        static=browser.new_context(viewport={"width":650,"height":890},java_script_enabled=False)
        page2=static.new_page()
        page2.goto(base+"prosperity-road-functions.html",wait_until="networkidle")
        assert page2.locator(".road-group").count()==8
        assert page2.locator(".directory article").count()==5
        assert page2.locator(".diagram img").count()==2
        fit(page2)
        static.close()
        ok("No-JS fallback still shows original map, road table and source/function diagrams")
        assert not errors,errors
        ctx.close();browser.close()
finally:
    (OUT/"report.json").write_text(json.dumps({
        "base_url":base,"checks":passes,"errors":errors},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if server:server.shutdown()
    if temporary:temporary.cleanup()
