#!/usr/bin/env python3
"""P4.4 browser checks on build and live Pages: six types, evidence, downloads and no hidden prior work."""
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
parser.add_argument("--output",default="artifacts/prosperity-architecture-p44-browser")
args=parser.parse_args()
out=ROOT/args.output
out.mkdir(parents=True,exist_ok=True)
checks=[];errors=[];server=None;temporary=None
if args.base_url:
    base=args.base_url.rstrip("/")+"/"
else:
    temporary=tempfile.TemporaryDirectory()
    root=Path(temporary.name)
    (root/"luoyang-city").symlink_to(ROOT/"_site",target_is_directory=True)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*unused):pass
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(Quiet,directory=root))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}/luoyang-city/"

def ok(text):
    checks.append(text)
    print("PASS",text,flush=True)
def no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")

try:
    with sync_playwright() as pw:
        options={"headless":True}
        if os.environ.get("CHROMIUM_PATH"):
            options["executable_path"]=os.environ["CHROMIUM_PATH"]
        browser=pw.chromium.launch(**options)
        context=browser.new_context(viewport={"width":1450,"height":960})
        page=context.new_page()
        page.on("pageerror",lambda e:errors.append(str(e)))
        response=page.goto(base+"prosperity-architecture.html",wait_until="networkidle")
        assert response.status==200
        page.wait_for_function("document.documentElement.dataset.architectureReady==='true'")
        expect(page.locator("h1")).to_contain_text("门")
        assert page.locator("[data-type]").count()==6
        assert page.locator("[data-type-panel]").count()==6
        expect(page.locator('[data-type-panel="east_ge_gate"]')).to_be_visible()
        assert page.locator("figure img").count()==3
        for graphic in page.locator("figure img").all():
            assert graphic.evaluate("(el)=>el.complete && el.naturalWidth>0")
        no_overflow(page)
        page.screenshot(path=str(out/"desktop.png"),full_page=True)
        ok("P4.4 desktop displays three original morphology panels with the east-ge source scope selected")
        page.locator('[data-type="inner_city_gate"]').click()
        expect(page.locator('[data-type-panel="inner_city_gate"]')).to_be_visible()
        assert "type=inner_city_gate" in page.url
        page.locator('[data-type="corridor_court_gate"]').click()
        expect(page.locator('[data-type-panel="corridor_court_gate"]')).to_contain_text("2.5m")
        assert "type=corridor_court_gate" in page.url
        page.reload(wait_until="networkidle")
        page.wait_for_function("document.documentElement.dataset.architectureReady==='true'")
        expect(page.locator('[data-type="corridor_court_gate"]')).to_have_attribute("aria-pressed","true")
        ok("Architecture type selection changes actual evidence panels and persists in URL/refresh")
        j=context.request.get(base+"prosperity-architecture/data.json")
        assert j.status==200
        data=j.json()
        assert data["version"]=="prosperity-architecture-p44" and len(data["types"])==6
        assert data["geo_registration"]["verified_common_ground_controls"]==0
        assert data["geo_registration"]["roof_dimensions_verified"] is False
        assert len(data["source_scope_comparisons"])==3
        for resource,prefix in [
            ("prosperity-architecture/gate-matrix.svg",b"<svg"),
            ("prosperity-architecture/east-ge-source-comparison.svg",b"<svg"),
            ("prosperity-architecture/palace-relation-grammar.svg",b"<svg"),
            ("prosperity-architecture/measurements.csv",None),
            ("downloads/prosperity-architecture-p44-atlas.pdf",b"%PDF-"),
            ("downloads/prosperity-architecture-p44-package.zip",b"PK")]:
            r=context.request.get(base+resource)
            assert r.status==200,(resource,r.status)
            assert len(r.body())>60
            if prefix:
                assert r.body().lstrip().startswith(prefix),resource
        old=context.request.get(base+"prosperity-palace-boundaries.html")
        assert old.status==200 and b"prosperity-architecture.html" in old.body()
        ok("Live assets and old P4.3 next-stage link resolve, with zero inferred geographic controls")
        mctx=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        m=mctx.new_page()
        m.on("pageerror",lambda e:errors.append(str(e)))
        m.goto(base+"prosperity-architecture.html",wait_until="networkidle")
        m.wait_for_function("document.documentElement.dataset.architectureReady==='true'")
        no_overflow(m)
        m.locator('[data-type="palace_axial_gate"]').tap()
        expect(m.locator('[data-type-panel="palace_axial_gate"]')).to_be_visible()
        no_overflow(m)
        for img in m.locator("figure img").all():
            assert img.evaluate("(el)=>el.complete && el.naturalWidth>0")
        m.screenshot(path=str(out/"mobile.png"),full_page=True)
        mctx.close()
        ok("390px mobile supports type selection, all original diagrams and no horizontal overflow")
        nctx=browser.new_context(viewport={"width":390,"height":844},java_script_enabled=False)
        n=nctx.new_page()
        n.goto(base+"prosperity-architecture.html",wait_until="networkidle")
        assert n.locator(".type-panel:visible").count()==6
        assert n.locator("figure img").count()==3
        no_overflow(n)
        nctx.close()
        ok("All six source interpretations remain readable without JavaScript")
        assert not errors,errors
        context.close();browser.close()
finally:
    (out/"report.json").write_text(
       json.dumps({"base_url":base,"checks":checks,"errors":errors},
                  ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if server:server.shutdown()
    if temporary:temporary.cleanup()
