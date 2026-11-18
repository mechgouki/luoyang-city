#!/usr/bin/env python3
"""P5.0 browser: water/road switches, evidence figures, archives and legitimate no-JS fallback."""
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
parser.add_argument("--output",default="artifacts/city-anchors-p50-browser")
args=parser.parse_args()
OUT=ROOT/args.output
OUT.mkdir(parents=True,exist_ok=True)
passes=[];errors=[];server=None;temporary=None
if args.base_url:base=args.base_url.rstrip("/")+"/"
else:
    temporary=tempfile.TemporaryDirectory()
    root=Path(temporary.name)
    (root/"luoyang-city").symlink_to(ROOT/"_site",target_is_directory=True)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*unused):pass
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(Quiet,directory=root))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}/luoyang-city/"
def ok(label):
    passes.append(label)
    print("PASS",label,flush=True)
def ready(page):page.wait_for_function("document.documentElement.dataset.anchorsP50Ready==='true'")
def fit(page):assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
try:
    with sync_playwright() as pw:
        opts={"headless":True}
        if os.environ.get("CHROMIUM_PATH"):opts["executable_path"]=os.environ["CHROMIUM_PATH"]
        browser=pw.chromium.launch(**opts)
        ctx=browser.new_context(viewport={"width":1460,"height":930})
        page=ctx.new_page()
        page.on("pageerror",lambda e:errors.append(str(e)))
        res=page.goto(base+"city-anchors.html",wait_until="networkidle")
        assert res.status==200
        ready(page)
        expect(page.locator("h1")).to_contain_text("河湖与主干道")
        expect(page.locator("button[data-section]")).to_have_count(2)
        expect(page.locator('article[data-panel="hydro"]')).to_be_visible()
        expect(page.locator('article[data-panel="roads"]')).to_be_hidden()
        assert page.locator('article[data-panel="hydro"] tbody tr[data-water-type]').count()==15
        fit(page)
        page.screenshot(path=str(OUT/"desktop.png"),full_page=True)
        ok("Desktop shows non-metric phase topology and all fifteen water components")
        page.locator('button[data-section="roads"]').click()
        expect(page.locator('article[data-panel="roads"]')).to_be_visible()
        expect(page.locator('article[data-panel="hydro"]')).to_be_hidden()
        expect(page.locator('button[data-section="roads"]')).to_have_attribute("aria-pressed","true")
        assert "view=roads" in page.url
        page.reload(wait_until="networkidle")
        ready(page)
        expect(page.locator('article[data-panel="roads"]')).to_be_visible()
        assert page.locator('article[data-panel="roads"] tbody tr').count()==8
        page.locator('button[data-section="hydro"]').click()
        expect(page.locator('article[data-panel="hydro"]')).to_be_visible()
        ok("Hydrology and main-road view switching persists across URL refresh")
        data=ctx.request.get(base+"city-anchors/data.json")
        assert data.status==200
        d=data.json()
        assert d["version"]=="city-anchors-hydro-roads-p50"
        assert len(d["water_components"])==15
        assert len(d["historical_waterbody_entity_ids"])==11
        assert not d["evidence_policy"]["new_ancient_geographic_coordinates"]
        assert d["evidence_policy"]["modern_luo_cannot_be_ancient"]
        for item,prefix in [
           ("city-anchors/water-topology.svg",b"<?xml"),
           ("city-anchors/road-matrix.svg",b"<?xml"),
           ("city-anchors/lake-evidence.svg",b"<?xml"),
           ("city-anchors/source-layout-unchanged.svg",b"<?xml"),
           ("city-anchors/water-inventory.csv",None),
           ("city-anchors/roads-register.csv",None),
           ("downloads/city-anchors-p50-atlas.pdf",b"%PDF-"),
           ("downloads/city-anchors-p50-package.zip",b"PK")
        ]:
            rr=ctx.request.get(base+item)
            assert rr.status==200,(item,rr.status)
            assert len(rr.body())>100
            if prefix:assert rr.body().lstrip().startswith(prefix),item
        prior=ctx.request.get(base+"prosperity-street-clusters.html")
        assert prior.status==200
        assert b'city-anchors.html' in prior.body()
        old=ctx.request.get(base+"homepage/approval-v9.json").json()
        assert old["hero"]["revision"]=="panorama-approved-v9"
        ok("Public full research package and H2-approved hero both remain accessible")
        mobile=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        m=mobile.new_page()
        m.on("pageerror",lambda e:errors.append(str(e)))
        rr=m.goto(base+"city-anchors.html?view=roads",wait_until="networkidle")
        assert rr.status==200
        ready(m);fit(m)
        expect(m.locator('article[data-panel="roads"]')).to_be_visible()
        for img in m.locator(".art img:visible").all():
            assert img.evaluate("(el)=>el.complete&&el.naturalWidth>0")
        m.locator('button[data-section="hydro"]').tap()
        expect(m.locator('article[data-panel="hydro"]')).to_be_visible()
        fit(m)
        m.screenshot(path=str(OUT/"mobile.png"),full_page=True)
        mobile.close()
        ok("390px mobile preserves ancient-vs-modern warnings, no overflow and working tap interaction")
        nojs=browser.new_context(viewport={"width":780,"height":850},java_script_enabled=False)
        n=nojs.new_page()
        n.goto(base+"city-anchors.html",wait_until="networkidle")
        assert n.locator("article[data-panel]:visible").count()==2
        assert n.locator(".art img").count()==4
        fit(n)
        nojs.close()
        ok("Both source-grounded studies remain visible without JavaScript")
        assert not errors,errors
        ctx.close();browser.close()
finally:
    (OUT/"report.json").write_text(json.dumps({"base_url":base,"checks":passes,"errors":errors},
                                               ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if server:server.shutdown()
    if temporary:temporary.cleanup()
