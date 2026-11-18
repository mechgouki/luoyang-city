#!/usr/bin/env python3
"""P4.6 browser: water and street evidence table, modern-only geometry, and all downloads."""
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
parser.add_argument("--output",default="artifacts/prosperity-hydro-roads-p46-browser")
args=parser.parse_args()
out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True)
server=None;temporary=None;checks=[];errors=[]
if args.base_url:base=args.base_url.rstrip("/")+"/"
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
def ok(s):checks.append(s);print("PASS",s,flush=True)
def ready(p):p.wait_for_function("document.documentElement.dataset.cityAnchorsReady==='true'")
def fit(p):assert p.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
try:
    with sync_playwright() as pw:
        kw={"headless":True}
        if os.environ.get("CHROMIUM_PATH"):
            kw["executable_path"]=os.environ["CHROMIUM_PATH"]
        browser=pw.chromium.launch(**kw)
        ctx=browser.new_context(viewport={"width":1440,"height":950})
        page=ctx.new_page()
        page.on("pageerror",lambda e:errors.append(str(e)))
        response=page.goto(base+"prosperity-hydro-roads.html",wait_until="networkidle")
        assert response.status==200
        ready(page)
        expect(page.locator("h1")).to_contain_text("河湖")
        expect(page.locator("button[data-mode]")).to_have_count(2)
        expect(page.locator("tr[data-row]")).to_have_count(55)
        assert page.locator("[data-table-panel='water'] tr[data-row]").count()==34
        assert page.locator("[data-table-panel='roads'] tr[data-row]").count()==21
        for im in page.locator(".plates img").all():
            assert im.evaluate("(el)=>el.complete && el.naturalWidth>0")
        fit(page)
        page.screenshot(path=str(out/"desktop.png"),full_page=True)
        ok("Desktop: 34 water entries, 21 road reports and four source-review diagrams")
        # Search is an active client-side filter, not a decorative field.
        input_water=page.locator("[data-table-panel='water'] [data-filter-search]")
        input_water.fill("翟泉")
        assert page.locator("[data-table-panel='water'] tr[data-row]:visible").count()>=1
        assert page.locator("[data-table-panel='water'] tr[data-row]:visible").count()<34
        input_water.fill("")
        page.locator("[data-table-panel='water'] [data-tier-select]").select_option("registered_modern_basemap_line")
        assert page.locator("[data-table-panel='water'] tr[data-row]:visible").count()==1
        expect(page.locator("[data-table-panel='water'] tr[data-row='W02']")).to_be_visible()
        page.locator("[data-table-panel='water'] [data-tier-select]").select_option("all")
        page.locator("button[data-mode='roads']").click()
        assert "view=roads" in page.url
        assert page.locator("[data-table-panel='roads']").is_visible()
        assert page.locator("[data-table-panel='water']").is_hidden()
        page.locator("[data-table-panel='roads'] [data-tier-select]").select_option("preserved_source_map_geometry")
        assert page.locator("[data-table-panel='roads'] tr[data-row]:visible").count()==8
        page.locator("[data-table-panel='roads'] [data-tier-select]").select_option("external_survey_without_registered_line")
        assert page.locator("[data-table-panel='roads'] tr[data-row]:visible").count()==11
        page.reload(wait_until="networkidle")
        ready(page)
        expect(page.locator("button[data-mode='roads']")).to_have_attribute("aria-pressed","true")
        ok("Source-tier filters separate one modern river from eight source roads and eleven outer road reports")
        data=ctx.request.get(base+"prosperity-hydro-roads/data.json").json()
        assert data["version"]=="prosperity-hydro-roads-anchor-p46"
        assert data["coordinates_added"]==0
        assert data["verified_new_ancient_common_ground_controls"]==0
        assert len(data["water_features"])==34 and len(data["main_road_records"])==21
        assert len(data["water_features"])!=len(data["main_road_records"])
        prior=ctx.request.get(base+"prosperity/source-layout.svg")
        preserved=ctx.request.get(base+"prosperity-hydro-roads/unaltered-source-layout.svg")
        assert prior.status==200 and preserved.status==200
        assert prior.body()==preserved.body()
        for path,prefix in [
          ("prosperity-hydro-roads/hydrology-topology.svg",b"<?xml"),
          ("prosperity-hydro-roads/roads-evidence.svg",b"<?xml"),
          ("prosperity-hydro-roads/anchor-gates.svg",b"<?xml"),
          ("prosperity-hydro-roads/water.csv",None),
          ("prosperity-hydro-roads/roads.csv",None),
          ("downloads/prosperity-hydro-roads-p46-atlas.pdf",b"%PDF-"),
          ("downloads/prosperity-hydro-roads-p46-package.zip",b"PK")
        ]:
            resource=ctx.request.get(base+path)
            assert resource.status==200,(path,resource.status)
            assert len(resource.body())>100
            if prefix:assert resource.body().lstrip().startswith(prefix),path
        old=ctx.request.get(base+"prosperity-street-clusters.html")
        assert old.status==200 and b"prosperity-hydro-roads.html" in old.body()
        hero=ctx.request.get(base+"homepage/approval-v9.json").json()
        assert hero["hero"]["revision"]=="panorama-approved-v9"
        ok("Public source SVG is byte-identical; PDF/ZIP/CSV JSON and upstream link accessible")
        mobile=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        m=mobile.new_page()
        m.on("pageerror",lambda e:errors.append(str(e)))
        res=m.goto(base+"prosperity-hydro-roads.html?view=roads",wait_until="networkidle")
        assert res.status==200
        ready(m)
        fit(m)
        expect(m.locator("button[data-mode='roads']")).to_have_attribute("aria-pressed","true")
        m.locator("button[data-mode='water']").tap()
        expect(m.locator("[data-table-panel='water']")).to_be_visible()
        fit(m)
        for image in m.locator(".plates img").all():
            assert image.evaluate("(el)=>el.complete && el.naturalWidth>0")
        m.screenshot(path=str(out/"mobile.png"),full_page=True)
        mobile.close()
        ok("390px mobile supports water/road selection and shows all four diagrams without overflow")
        nojs=browser.new_context(viewport={"width":720,"height":900},java_script_enabled=False)
        p=nojs.new_page()
        p.goto(base+"prosperity-hydro-roads.html",wait_until="networkidle")
        assert p.locator("tr[data-row]:visible").count()==55
        fit(p)
        nojs.close()
        ok("No-JS fallback shows full unmodified evidence inventory")
        assert not errors,errors
        ctx.close();browser.close()
finally:
    (out/"report.json").write_text(json.dumps(
        {"base_url":base,"checks":checks,"errors":errors},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if server:server.shutdown()
    if temporary:temporary.cleanup()
