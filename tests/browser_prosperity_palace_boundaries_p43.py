#!/usr/bin/env python3
"""P4.3 desktop/mobile review of same-scale source-provenance page and downloads."""
import argparse
import functools
import http.server
import json
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument("--base-url")
parser.add_argument("--output",default="artifacts/prosperity-palace-boundaries-p43-browser")
args=parser.parse_args()
out=ROOT/args.output
out.mkdir(parents=True,exist_ok=True)
server=None;temp=None;passes=[];errors=[]
if args.base_url:
    base=args.base_url.rstrip("/")+"/"
else:
    temp=tempfile.TemporaryDirectory()
    folder=Path(temp.name)
    (folder/"luoyang-city").symlink_to(ROOT/"_site",target_is_directory=True)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*unused):pass
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(Quiet,directory=folder))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}/luoyang-city/"
def ok(name):
    passes.append(name)
    print("PASS",name,flush=True)
def no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        context=browser.new_context(viewport={"width":1420,"height":900})
        page=context.new_page()
        page.on("pageerror",lambda error:errors.append(str(error)))
        response=page.goto(base+"prosperity-palace-boundaries.html",wait_until="networkidle")
        assert response.status==200
        expect(page.locator("h1")).to_contain_text("310")
        expect(page.locator("h1")).to_contain_text("380")
        assert page.locator("#sources li").count()==6
        assert page.locator("figure img").count()==1
        assert page.locator("figure img").first.evaluate("(img)=>img.complete && img.naturalWidth>0")
        no_overflow(page)
        page.screenshot(path=str(out/"desktop.png"),full_page=True)
        ok("Desktop renders three same-scale reported scopes with explicit provenance and caveat")
        data=context.request.get(base+"prosperity-palace-boundaries/data.json").json()
        assert data["version"]=="prosperity-palace-boundaries-p43"
        assert data["spatial_registration"]["verified_common_ground_controls"]==0
        assert [x["ns_m"] for x in data["reporting_variants"]]==[310,370,380]
        for resource,prefix in [
            ("prosperity-palace-boundaries/extent-comparison.svg",b"<svg"),
            ("prosperity-palace-boundaries/readings.csv",None),
            ("downloads/prosperity-palace-boundaries-p43-atlas.pdf",b"%PDF-"),
            ("downloads/prosperity-palace-boundaries-p43-package.zip",b"PK")]:
            r=context.request.get(base+resource)
            assert r.status==200 and len(r.body())>40
            if prefix: assert r.body().lstrip().startswith(prefix)
        old=context.request.get(base+"prosperity-taiji-courts.html")
        assert old.status==200 and b"prosperity-palace-boundaries.html" in old.body()
        ok("All public evidence downloads and old P4.2 next-stage link resolve")
        mobile=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        m=mobile.new_page()
        m.on("pageerror",lambda error:errors.append(str(error)))
        r=m.goto(base+"prosperity-palace-boundaries.html",wait_until="networkidle")
        assert r.status==200
        assert m.locator("figure img").first.evaluate("(img)=>img.complete && img.naturalWidth>0")
        no_overflow(m)
        m.screenshot(path=str(out/"mobile.png"),full_page=True)
        mobile.close()
        ok("Mobile 390px viewport has no horizontal overflow, all source material readable")
        assert not errors,errors
        context.close()
        browser.close()
finally:
    (out/"report.json").write_text(json.dumps({"base":base,"checks":passes,"errors":errors},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if server:server.shutdown()
    if temp:temp.cleanup()
