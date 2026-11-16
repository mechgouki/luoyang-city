#!/usr/bin/env python3
"""Exercise the P4 quantitative source review on actual build and deployed HTTPS."""
import argparse
import functools
import http.server
import json
import os
from pathlib import Path
import tempfile
import threading
from urllib.parse import urljoin

from playwright.sync_api import expect, sync_playwright

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument("--base-url")
parser.add_argument("--output",default="artifacts/prosperity-axis-v4-browser")
args=parser.parse_args()
out=ROOT/args.output
out.mkdir(parents=True,exist_ok=True)
server=temp=None
checks=[]
errors=[]
if args.base_url:
    base=args.base_url.rstrip("/")+"/"
else:
    temp=tempfile.TemporaryDirectory()
    root=Path(temp.name)
    (root/"luoyang-city").symlink_to(ROOT/"_site",target_is_directory=True)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*unused):pass
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(Quiet,directory=root))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}/luoyang-city/"

def passed(label):
    checks.append({"name":label,"status":"passed"})
    print("PASS",label,flush=True)

def no_overflow(p):
    assert p.evaluate("document.documentElement.scrollWidth <= innerWidth+2")

try:
    with sync_playwright() as pw:
        opts={"headless":True}
        if os.getenv("CHROMIUM_PATH"):
            opts["executable_path"]=os.environ["CHROMIUM_PATH"]
        browser=pw.chromium.launch(**opts)
        ctx=browser.new_context(viewport={"width":1440,"height":960})
        page=ctx.new_page()
        page.on("pageerror",lambda e:errors.append(str(e)))
        resp=ctx.request.get(base+"prosperity-axis/data.json")
        assert resp.status==200
        data=resp.json()
        assert data["version"]=="prosperity-axis-p4-metric-review"
        assert data["registration"]["verified_common_controls"]==0
        assert [x["length_m"] for x in data["axis_segments"]]==[95,80,300]
        res=page.goto(base+"prosperity-axis.html",wait_until="networkidle")
        assert res.status==200
        expect(page.locator("h1")).to_contain_text("一座宫城")
        page.wait_for_function("document.documentElement.dataset.phaseReady==='true'")
        assert page.locator(".figure img").count()==3
        for elem in page.locator(".figure img").all():
            assert elem.evaluate("(img)=>img.complete && img.naturalWidth>0"),"SVG preview must be visible"
        expect(page.locator(".phase-detail[data-phase-card='early']")).to_be_visible()
        no_overflow(page)
        assert "475" in page.locator("#distance").inner_text()
        assert "460" in page.locator("#distance").inner_text()
        assert "15" in page.locator("#distance").inner_text()
        page.screenshot(path=str(out/"desktop-axis.png"),full_page=True)
        passed("three genuine scale figures and visible 475/460 difference load in P4 desktop")

        page.locator('[data-phase="middle"]').click()
        expect(page.locator('[data-phase="middle"]')).to_have_attribute("aria-pressed","true")
        expect(page.locator(".phase-detail[data-phase-card='middle']")).to_be_visible()
        expect(page.locator(".phase-detail[data-phase-card='early']")).to_be_hidden()
        assert "phase=middle" in page.url
        page.reload(wait_until="networkidle")
        page.wait_for_function("document.documentElement.dataset.phaseReady==='true'")
        expect(page.locator(".phase-detail[data-phase-card='middle']")).to_be_visible()
        page.locator('[data-phase="late"]').click()
        expect(page.locator(".phase-detail[data-phase-card='late']")).to_contain_text("柱网")
        page.locator('[data-phase="early"]').click()
        expect(page.locator(".phase-detail[data-phase-card='early']")).to_contain_text("残存")
        passed("three archaeological phases switch evidence and preserve URL state after reload")

        source_links=page.locator("#originals .source-grid article a")
        assert source_links.count()>=4
        for a in source_links.all():
            expect(a).to_have_attribute("href",__import__("re").compile(r"^https://|^\.\/prosperity-gate"))
        expect(page.locator('a[href="./prosperity-gate.html#source-comparison"]').first).to_be_visible()
        expect(page.locator("#taiji")).to_contain_text("102.3")
        expect(page.locator("#taiji")).to_contain_text("98.4")
        expect(page.locator("#taiji")).to_contain_text("西堂")
        passed("original publications are directly reachable as links and Taiji uncertainty remains visible")

        for path,prefix in [
            ("prosperity-axis/axis-segments.svg",b"<svg"),
            ("prosperity-axis/third-gate-phases.svg",b"<svg"),
            ("prosperity-axis/taiji-dimensions.svg",b"<svg"),
            ("prosperity-axis/measurements.csv",None),
            ("prosperity-axis/data.json",b"{"),
            ("downloads/prosperity-axis-v4-atlas.pdf",b"%PDF-"),
            ("downloads/prosperity-axis-v4-package.zip",b"PK")]:
            resp=ctx.request.get(base+path)
            assert resp.status==200,path
            body=resp.body()
            assert len(body)>35,path
            if prefix:assert body.lstrip().startswith(prefix),path
        passed("all three SVGs, source-scoped CSV/JSON, three-page PDF and ZIP download correctly")

        orig=ctx.request.get(base+"prosperity-gate.html")
        assert orig.status==200 and b"prosperity-axis.html" in orig.body()
        home=ctx.request.get(base+"index.html")
        assert home.status==200 and b"prosperity-axis.html" in home.body()
        passed("P4 is discoverable from the already-published original comparison and home entry")

        mobile=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        mp=mobile.new_page()
        mp.on("pageerror",lambda e:errors.append(str(e)))
        mp.goto(base+"prosperity-axis.html",wait_until="networkidle")
        mp.wait_for_function("document.documentElement.dataset.phaseReady==='true'")
        no_overflow(mp)
        assert mp.locator(".figure img").count()==3
        for im in mp.locator(".figure img").all():
            assert im.evaluate("(img)=>img.complete && img.naturalWidth>0")
        mp.locator('[data-phase="middle"]').tap()
        expect(mp.locator(".phase-detail[data-phase-card='middle']")).to_be_visible()
        mp.screenshot(path=str(out/"mobile-axis.png"),full_page=True)
        no_overflow(mp)
        mobile.close()
        passed("mobile reading, all source comparison figures and phase selection have no overflow")

        nojs=browser.new_context(viewport={"width":390,"height":844},java_script_enabled=False)
        np=nojs.new_page()
        np.goto(base+"prosperity-axis.html",wait_until="networkidle")
        expect(np.locator(".phase-detail[data-phase-card='early']")).to_be_visible()
        assert np.locator(".figure img").count()==3
        for im in np.locator(".figure img").all():
            assert im.evaluate("(img)=>img.complete && img.naturalWidth>0")
        no_overflow(np)
        nojs.close()
        passed("without JavaScript all source diagrams, public links and default archaeological phase remain readable")
        assert not errors,errors
        ctx.close()
        browser.close()
finally:
    (out/"report.json").write_text(json.dumps({"checks":checks,"errors":errors,"base_url":base},
                                             ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if server:server.shutdown()
    if temp:temp.cleanup()
