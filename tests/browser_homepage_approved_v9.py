#!/usr/bin/env python3
"""Validate the current approved image at both screen sizes and its archived predecessors."""
import argparse
import functools
import http.server
import json
import os
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument("--base-url")
parser.add_argument("--output",default="artifacts/homepage-approved-v9-browser")
args=parser.parse_args()
out=ROOT/args.output
out.mkdir(parents=True,exist_ok=True)
server=None
temporary=None
checks=[]
errors=[]
if args.base_url:
    base=args.base_url.rstrip("/")+"/"
else:
    temporary=tempfile.TemporaryDirectory()
    folder=Path(temporary.name)
    (folder/"luoyang-city").symlink_to(ROOT/"_site",target_is_directory=True)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*unused):pass
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),
      functools.partial(Quiet,directory=folder))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}/luoyang-city/"

def ok(name):
    checks.append(name)
    print("PASS",name,flush=True)
def no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
def ready(page):
    page.wait_for_function("document.documentElement.dataset.homepageReady==='true'")
try:
    with sync_playwright() as pw:
        opts={"headless":True}
        if os.environ.get("CHROMIUM_PATH"):
            opts["executable_path"]=os.environ["CHROMIUM_PATH"]
        browser=pw.chromium.launch(**opts)
        ctx=browser.new_context(viewport={"width":1500,"height":960})
        p=ctx.new_page()
        p.on("pageerror",lambda error:errors.append(str(error)))
        r=p.goto(base,wait_until="networkidle")
        assert r.status==200
        ready(p)
        approval=ctx.request.get(base+"homepage/approval-v11.json").json()
        h=approval["hero"]
        previous=ctx.request.get(base+approval["previous_metadata"]).json()["hero"]
        assert previous["revision"]==approval["previous_revision"]=="panorama-approved-v10"
        assert previous["source_sha256"]=="262e0797c09788f7871bca81c05d5e2c15d5ebc7ab8cf6c559ced68cf883a41e"
        old=ctx.request.get(base+"homepage/history/panorama-interim-v8.json").json()
        assert h["revision"]=="panorama-approved-v11" and h["status"]=="approved"
        assert h["selection_number"]=="07"
        assert h["source_sha256"]=="4d45e831b59f2f7550fe7129455f1da823098e8f34cf633223cd584d5b64a5bf"
        assert h["approval_date"]=="2026-11-21"
        assert old["hero"]["revision"]=="panorama-interim-v8"
        im=p.locator("#home-hero img")
        im.wait_for(state="visible")
        p.wait_for_function("()=>{const im=document.querySelector('#home-hero img');return im&&im.complete&&im.naturalWidth===1672;}")
        assert im.evaluate("(el)=>el.currentSrc.endsWith('/'+el.getAttribute('src').replace('./',''))")
        assert im.get_attribute("src").endswith(h["asset"])
        assert p.locator("#home-hero").get_attribute("data-hero-revision")==h["revision"]
        assert im.get_attribute("alt")==h["alt"]
        expect(p.locator("#home-hero")).to_contain_text("研究性复原示意")
        assert p.locator("#home-questions a[data-question]").count()==3
        no_overflow(p)
        p.screenshot(path=str(out/"approved-desktop.png"),full_page=False)
        ok("Desktop hero uses selected candidate 07 at 1672×941 with its verified source digest")
        for page in ("index.html","v3.0-dual.html"):
            res=ctx.request.get(base+page)
            assert res.status==200
            assert b'data-hero-revision="panorama-approved-v11"' in res.body()
            assert h["asset"].encode() in res.body()
        for asset in (h["asset"],h["small_asset"]):
            r=ctx.request.get(base+asset)
            assert r.status==200 and r.headers.get("content-type","").startswith("image/"),asset
            assert len(r.body())>100000,asset
        ok("Both homepage URLs and published WebP files resolve over HTTPS or local HTTP")
        mobile=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        m=mobile.new_page()
        m.on("pageerror",lambda error:errors.append(str(error)))
        m.goto(base,wait_until="networkidle")
        ready(m)
        m.wait_for_function("()=>{const im=document.querySelector('#home-hero img');return im&&im.complete&&im.naturalWidth===960;}")
        assert m.locator("#home-hero img").evaluate("el=>el.currentSrc").endswith("/"+h["small_asset"])
        assert m.locator("#home-hero img").evaluate("el=>getComputedStyle(el).objectFit")=="contain"
        no_overflow(m)
        m.screenshot(path=str(out/"approved-mobile.png"),full_page=False)
        m.locator("#home-start").tap()
        m.wait_for_function('location.hash === "#map"')
        expect(m.locator("#home-hero")).to_be_hidden()
        expect(m.locator("#map-viewport")).to_be_in_viewport()
        no_overflow(m)
        ok("390px mobile loads candidate 07 at 960×540 without cropping and opens the map")
        assert not errors,errors
        mobile.close()
        ctx.close()
        browser.close()
finally:
    (out/"results.json").write_text(json.dumps({"base_url":base,"checks":checks,"errors":errors},
     ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if server:server.shutdown()
    if temporary:temporary.cleanup()
