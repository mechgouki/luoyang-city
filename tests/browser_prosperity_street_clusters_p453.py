#!/usr/bin/env python3
"""P4.5.3 browser: 3 text clusters, grade A/C filters, old GIS evidence and downloads."""
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
p=argparse.ArgumentParser()
p.add_argument("--base-url")
p.add_argument("--output",default="artifacts/prosperity-street-clusters-p453-browser")
args=p.parse_args()
OUT=ROOT/args.output;OUT.mkdir(parents=True,exist_ok=True)
okays=[];errors=[];server=None;temporary=None
if args.base_url:base=args.base_url.rstrip("/")+"/"
else:
    temporary=tempfile.TemporaryDirectory()
    workspace=Path(temporary.name)
    (workspace/"luoyang-city").symlink_to(ROOT/"_site",target_is_directory=True)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*unused):pass
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),
       functools.partial(Quiet,directory=workspace))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}/luoyang-city/"
def ok(name):okays.append(name);print("PASS",name,flush=True)
def ready(page):page.wait_for_function("document.documentElement.dataset.p453Ready==='true'")
def fit(page):assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
try:
    with sync_playwright() as pw:
        opts={"headless":True}
        if os.environ.get("CHROMIUM_PATH"):opts["executable_path"]=os.environ["CHROMIUM_PATH"]
        browser=pw.chromium.launch(**opts)
        ctx=browser.new_context(viewport={"width":1440,"height":950})
        page=ctx.new_page()
        page.on("pageerror",lambda err:errors.append(str(err)))
        response=page.goto(base+"prosperity-street-clusters.html",wait_until="networkidle")
        assert response.status==200
        ready(page)
        expect(page.locator("h1")).to_contain_text("道路两侧")
        expect(page.locator("button[data-cluster]")).to_have_count(3)
        expect(page.locator("article[data-cluster-panel]")).to_have_count(3)
        expect(page.locator('article[data-cluster-panel="K01"]')).to_be_visible()
        assert page.locator('article[data-cluster-panel="K01"] tr.relation-row:visible').count()==8
        assert page.locator('article[data-cluster-panel="K02"]').is_hidden()
        fit(page)
        page.screenshot(path=str(OUT/"desktop.png"),full_page=True)
        ok("Desktop defaults to the 8 palace textual relations, without showing all cluster panels at once")
        page.locator('button[data-grade="C"]').click()
        expect(page.locator('button[data-grade="C"]')).to_have_attribute("aria-pressed","true")
        assert page.locator('article[data-cluster-panel="K01"] tr.relation-row:visible').count()==1
        assert "grade=C" in page.url
        page.locator('button[data-cluster="K02"]').click()
        assert page.locator('article[data-cluster-panel="K02"]').is_visible()
        assert page.locator('article[data-cluster-panel="K02"] tr.relation-row:visible').count()==0
        page.locator('button[data-grade="A"]').click()
        assert page.locator('article[data-cluster-panel="K02"] tr.relation-row:visible').count()==5
        assert "cluster=K02" in page.url and "grade=A" in page.url
        page.reload(wait_until="networkidle")
        ready(page)
        expect(page.locator('button[data-cluster="K02"]')).to_have_attribute("aria-pressed","true")
        expect(page.locator('button[data-grade="A"]')).to_have_attribute("aria-pressed","true")
        ok("Cluster tabs and A/C evidence filter update visible rows and deep links survive refresh")
        d=ctx.request.get(base+"prosperity-street-clusters/data.json").json()
        assert d["version"]=="prosperity-street-clusters-p453"
        assert d["audit"]["direct_edges"]==16 and d["audit"]["interpretive_edges"]==1
        assert d["audit"]["new_ancient_wgs84_points"]==0
        assert d["diagram_contract"]["source_map_overlay_policy"].startswith("reuse")
        for resource,prefix in [
            ("prosperity-street-clusters/palace-street.svg",b"<?xml"),
            ("prosperity-street-clusters/jianchun-stones.svg",b"<?xml"),
            ("prosperity-street-clusters/south-bridge-market.svg",b"<?xml"),
            ("prosperity-street-clusters/source-index-unchanged.svg",b"<?xml"),
            ("prosperity-street-clusters/edges.csv",None),
            ("prosperity-street-clusters/nodes.csv",None),
            ("downloads/prosperity-street-clusters-p453-atlas.pdf",b"%PDF-"),
            ("downloads/prosperity-street-clusters-p453-package.zip",b"PK")
        ]:
            res=ctx.request.get(base+resource)
            assert res.status==200,(resource,res.status)
            assert len(res.body())>100
            if prefix: assert res.body().lstrip().startswith(prefix),resource
        prior=ctx.request.get(base+"prosperity-road-functions.html")
        assert prior.status==200
        assert b'prosperity-street-clusters.html' in prior.body()
        approved=ctx.request.get(base+"homepage/approval-v9.json").json()
        assert approved["hero"]["revision"]=="panorama-approved-v9"
        ok("JSON, three source-graded SVGs, byte-preserved original index, PDF/ZIP/CSVs and upstream link accessible")
        mobile=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        m=mobile.new_page()
        m.on("pageerror",lambda err:errors.append(str(err)))
        r=m.goto(base+"prosperity-street-clusters.html?cluster=K03&grade=A",wait_until="networkidle")
        assert r.status==200
        ready(m)
        fit(m)
        expect(m.locator('button[data-cluster="K03"]')).to_have_attribute("aria-pressed","true")
        assert m.locator('article[data-cluster-panel="K03"] tr.relation-row:visible').count()==4
        for img in m.locator(".cluster figure img:visible").all():
            assert img.evaluate("(el)=>el.complete&&el.naturalWidth>0")
        m.locator('button[data-cluster="K01"]').tap()
        expect(m.locator('button[data-cluster="K01"]')).to_have_attribute("aria-pressed","true")
        fit(m)
        m.screenshot(path=str(OUT/"mobile.png"),full_page=True)
        mobile.close()
        ok("390px mobile supports direct-link to Luonan and switches back to palace, without horizontal overflow")
        nojs=browser.new_context(viewport={"width":800,"height":840},java_script_enabled=False)
        no=nojs.new_page()
        no.goto(base+"prosperity-street-clusters.html",wait_until="networkidle")
        assert no.locator('article[data-cluster-panel]:visible').count()==3
        for img in no.locator(".cluster figure img").all():
            assert img.evaluate("(el)=>el.complete&&el.naturalWidth>0")
        fit(no)
        nojs.close()
        ok("All three source manuscript context plates remain visible without JavaScript")
        assert not errors,errors
        ctx.close();browser.close()
finally:
    (OUT/"report.json").write_text(json.dumps({"base_url":base,"checks":okays,"errors":errors},
                             ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if server:server.shutdown()
    if temporary:temporary.cleanup()
