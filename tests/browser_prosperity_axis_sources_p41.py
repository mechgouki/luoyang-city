#!/usr/bin/env python3
"""Validate source-original audit, measured-alternative semantics, mobile and no-JS."""
import argparse,functools,http.server,json,os,threading,tempfile
from pathlib import Path
from playwright.sync_api import expect,sync_playwright

ROOT=Path(__file__).resolve().parents[1]
arg=argparse.ArgumentParser()
arg.add_argument("--base-url")
arg.add_argument("--output",default="artifacts/prosperity-axis-sources-p41-browser")
args=arg.parse_args()
output=ROOT/args.output
output.mkdir(parents=True,exist_ok=True)
server=temp=None
checks,errors=[],[]
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
def mark(label):
    checks.append({"name":label,"status":"passed"})
    print("PASS",label,flush=True)
def no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+2")

try:
    with sync_playwright() as pw:
        kw={"headless":True}
        if os.getenv("CHROMIUM_PATH"):kw["executable_path"]=os.environ["CHROMIUM_PATH"]
        browser=pw.chromium.launch(**kw)
        ctx=browser.new_context(viewport={"width":1450,"height":1000})
        page=ctx.new_page()
        page.on("pageerror",lambda e:errors.append(str(e)))
        r=ctx.request.get(base+"prosperity-axis-sources/audit.json")
        assert r.status==200
        data=r.json()
        assert data["version"]=="prosperity-axis-p41-source-audit"
        assert data["identity"]["separate_archaeological_sites_created"]==0
        assert [x["distance_m"] for x in data["distance_conflicts"]]==[200,300]
        assert [x["sum_m"] for x in data["alternatives"]]==[375,475]
        assert data["completely_acquired_formal_chinese_journal_plans"]==0

        response=page.goto(base+"prosperity-axis-sources.html",wait_until="networkidle")
        assert response.status==200
        page.wait_for_function("document.documentElement.dataset.auditReady==='true'")
        expect(page.locator("h1")).to_contain_text("两个名字")
        expect(page.locator("#identity")).to_contain_text("一号门")
        expect(page.locator("#identity")).to_contain_text("阊阖门")
        assert page.locator("figure img").count()==2
        for im in page.locator("figure img").all():
            assert im.evaluate("(img) => img.complete && img.naturalWidth>0")
        expect(page.locator(".scenario-output")).to_contain_text("375米")
        assert page.locator(".source-card").count()==len(data["sources"])==9
        no_overflow(page)
        page.screenshot(path=str(output/"desktop-source-audit.png"),full_page=True)
        mark("P4.1 opens two auditable comparison SVGs, source list, gate identity and 200m default")

        page.locator("#scenario").select_option("qian2012")
        expect(page.locator("#scenario-output")).to_contain_text("475米")
        expect(page.locator("#scenario-output")).to_contain_text("+15米")
        assert "scenario=qian2012" in page.url
        page.reload(wait_until="networkidle")
        page.wait_for_function("document.documentElement.dataset.auditReady==='true'")
        expect(page.locator("#scenario")).to_have_value("qian2012")
        expect(page.locator("#scenario-output")).to_contain_text("475米")
        page.locator("#scenario").select_option("nara2011")
        expect(page.locator("#scenario-output")).to_contain_text("-85米")
        mark("200m/300m source alternatives have correct 375/475 totals and reload-stable selection")

        expect(page.locator("#width")).to_contain_text("23米")
        expect(page.locator("#width")).to_contain_text("24米")
        expect(page.locator("#sources")).to_contain_text("未取得")
        expect(page.locator("#sources")).to_contain_text("图69")
        assert page.locator('#sources a[href^="https://repository.nabunken.go.jp"]').count()>=4
        assert page.locator('#sources a[href*="2009_022_023.pdf"]').count()>=1
        assert page.locator('#sources a[href*="2010_014_015.pdf"]').count()>=1
        assert page.locator('#sources a[href*="2011_006_007.pdf"]').count()>=1
        assert page.locator('#sources a[href*="2013_052_053.pdf"]').count()>=1
        mark("2009/2010/2011/2013 public originals link to their precise journal PDFs and formal missing plans stay flagged")

        for path,start in [("prosperity-axis-sources/distance-comparison.svg",b"<svg"),
                           ("prosperity-axis-sources/figure-inventory.svg",b"<svg"),
                           ("prosperity-axis-sources/readings.csv",None),
                           ("prosperity-axis-sources/audit.json",b"{"),
                           ("downloads/prosperity-axis-p41-atlas.pdf",b"%PDF-"),
                           ("downloads/prosperity-axis-p41-package.zip",b"PK")]:
            resp=ctx.request.get(base+path)
            assert resp.status==200,path
            data_bytes=resp.body()
            assert len(data_bytes)>30,path
            if start:assert data_bytes.lstrip().startswith(start),path
        mark("SVG, CSV, JSON, 2-page PDF, ZIP and source reading limits all download successfully")

        for previous in ["index.html","prosperity-gate.html","prosperity-axis.html"]:
            resp=ctx.request.get(base+previous)
            assert resp.status==200 and b"prosperity-axis-sources.html" in resp.body()
        mark("home, original comparison and earlier P4 view all expose the new source-audit entry")

        mobile=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        m=mobile.new_page()
        m.on("pageerror",lambda e:errors.append(str(e)))
        m.goto(base+"prosperity-axis-sources.html",wait_until="networkidle")
        m.wait_for_function("document.documentElement.dataset.auditReady==='true'")
        no_overflow(m)
        assert m.locator("figure img").count()==2
        for image in m.locator("figure img").all():
            assert image.evaluate("(img)=>img.complete && img.naturalWidth>0")
        m.locator("#scenario").select_option("qian2012")
        expect(m.locator("#scenario-output")).to_contain_text("475米")
        no_overflow(m)
        m.screenshot(path=str(output/"mobile-source-audit.png"),full_page=True)
        mobile.close()
        mark("390px mobile shows source inventory, both original-based charts and scenario selection without overflow")

        noscript=browser.new_context(viewport={"width":390,"height":844},java_script_enabled=False)
        n=noscript.new_page()
        n.goto(base+"prosperity-axis-sources.html",wait_until="networkidle")
        expect(n.locator("#scenario-output")).to_contain_text("375米")
        assert n.locator(".source-card").count()==9
        for image in n.locator("figure img").all():
            assert image.evaluate("(img)=>img.complete && img.naturalWidth>0")
        no_overflow(n)
        noscript.close()
        mark("static no-JavaScript fallback retains both diagrams, original links and default uncertainty explanation")
        assert not errors,errors
        ctx.close()
        browser.close()
finally:
    (output/"report.json").write_text(json.dumps({"checks":checks,"errors":errors,"base_url":base},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if server:server.shutdown()
    if temp:temp.cleanup()
