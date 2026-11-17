#!/usr/bin/env python3
"""Read P4.2 Taiji/palace-courts sources, states, SVGs on build and real HTTPS."""
import argparse,functools,http.server,json,os,tempfile,threading
from pathlib import Path
from playwright.sync_api import expect,sync_playwright
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument("--base-url");parser.add_argument("--output",default="artifacts/prosperity-taiji-courts-p42-browser")
args=parser.parse_args()
out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True)
server=temp=None;checks=[];errors=[]
if args.base_url:base=args.base_url.rstrip("/")+"/"
else:
 temp=tempfile.TemporaryDirectory();t=Path(temp.name);(t/"luoyang-city").symlink_to(ROOT/"_site",target_is_directory=True)
 class Quiet(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*unused):pass
 server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(Quiet,directory=t))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 base=f"http://127.0.0.1:{server.server_port}/luoyang-city/"
def ok(name):
 checks.append({"name":name,"status":"passed"});print("PASS",name,flush=True)
def no_overflow(page):
 assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
try:
 with sync_playwright() as pw:
  opts={"headless":True}
  if os.environ.get("CHROMIUM_PATH"):opts["executable_path"]=os.environ["CHROMIUM_PATH"]
  browser=pw.chromium.launch(**opts)
  ctx=browser.new_context(viewport={"width":1480,"height":960})
  page=ctx.new_page();page.on("pageerror",lambda e:errors.append(str(e)))
  response=ctx.request.get(base+"prosperity-taiji-courts/data.json")
  assert response.status==200
  d=response.json()
  assert d["version"]=="prosperity-taiji-courts-p42"
  assert d["geographic_registration"]["new_absolute_coordinates"]==0
  assert [x["ew_m"] for x in d["courtyard_extent_variants"]]==[340,320]
  response=page.goto(base+"prosperity-taiji-courts.html",wait_until="networkidle")
  assert response.status==200
  page.wait_for_function("document.documentElement.dataset.taijiReady==='true'")
  expect(page.locator("h1")).to_contain_text("东堂")
  expect(page.locator("#extent-result")).to_contain_text("340m")
  expect(page.locator(".phase-detail[data-phase-card='northern_wei']")).to_be_visible()
  assert page.locator("figure img").count()==3
  for img in page.locator("figure img").all():
   assert img.evaluate("(el)=>el.complete && el.naturalWidth>0")
  no_overflow(page);page.screenshot(path=str(out/"desktop-taiji-courts.png"),full_page=True)
  ok("P4.2 displays three legitimate source-scope figures and the default Northern Wei reconstruction phase")
  page.locator('[data-phase="wei_jin"]').click()
  expect(page.locator(".phase-detail[data-phase-card='wei_jin']")).to_contain_text("砖砌拱券")
  assert "phase=wei_jin" in page.url
  page.locator('[data-phase="northern_zhou"]').click()
  expect(page.locator(".phase-detail[data-phase-card='northern_zhou']")).to_contain_text("未完成")
  page.locator('[data-phase="northern_wei"]').click()
  expect(page.locator(".phase-detail[data-phase-card='northern_wei']")).to_contain_text("夯土隔墙")
  page.reload(wait_until="networkidle")
  page.wait_for_function("document.documentElement.dataset.taijiReady==='true'")
  expect(page.locator('[data-phase="northern_wei"]')).to_have_attribute("aria-pressed","true")
  ok("three chronological building types toggle correctly and maintain the URL/refresh state")
  page.locator("#extent-select").select_option("B")
  expect(page.locator("#extent-result")).to_contain_text("320m")
  expect(page.locator("#extent-result")).to_contain_text("380m")
  expect(page.locator("#extent-result")).to_contain_text("70m")
  assert "extent=B" in page.url
  page.reload(wait_until="networkidle")
  page.wait_for_function("document.documentElement.dataset.taijiReady==='true'")
  expect(page.locator("#extent-select")).to_have_value("B")
  page.locator("#extent-select").select_option("A")
  expect(page.locator("#extent-result")).to_contain_text("310m")
  ok("alternative 340x310 and 320x380 courtyard-report dimensions remain separately selectable")
  assert page.locator(".source-card").count()==len(d["sources"])==6
  expect(page.locator("#northern-courts")).to_contain_text("37m")
  expect(page.locator("#northern-courts")).to_contain_text("52m")
  expect(page.locator("#halls")).to_contain_text("47.9")
  expect(page.locator("#halls")).to_contain_text("48×23")
  expect(page.locator("#phases")).to_contain_text("北周")
  ok("partial excavation limits, hall dimension variations, phase labels and original publications are explicit")
  for path,signature in [
   ("prosperity-taiji-courts/halls-scale.svg",b"<svg"),
   ("prosperity-taiji-courts/north-courts-relations.svg",b"<svg"),
   ("prosperity-taiji-courts/court-extents.svg",b"<svg"),
   ("prosperity-taiji-courts/data.json",b"{"),
   ("prosperity-taiji-courts/measurements.csv",None),
   ("downloads/prosperity-taiji-courts-p42-atlas.pdf",b"%PDF-"),
   ("downloads/prosperity-taiji-courts-p42-package.zip",b"PK")]:
   response=ctx.request.get(base+path)
   assert response.status==200,path
   raw=response.body()
   assert len(raw)>45,path
   if signature:assert raw.lstrip().startswith(signature),path
  ok("all three P4.2 SVGs and the public JSON, CSV, PDF and ZIP resolve from the built or live site")
  for old in ["index.html","prosperity-gate.html","prosperity-axis.html","prosperity-axis-sources.html"]:
   r=ctx.request.get(base+old);assert r.status==200
   assert b"prosperity-taiji-courts.html" in r.body()
  ok("the home and all earlier source comparison pages link to the new P4.2 milestone")
  mobile=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
  m=mobile.new_page();m.on("pageerror",lambda e:errors.append(str(e)))
  m.goto(base+"prosperity-taiji-courts.html",wait_until="networkidle")
  m.wait_for_function("document.documentElement.dataset.taijiReady==='true'")
  no_overflow(m)
  assert m.locator("figure img").count()==3
  for img in m.locator("figure img").all():assert img.evaluate("(el)=>el.complete && el.naturalWidth>0")
  m.locator('[data-phase="wei_jin"]').tap()
  expect(m.locator(".phase-detail[data-phase-card='wei_jin']")).to_be_visible()
  m.locator("#extent-select").select_option("B")
  expect(m.locator("#extent-result")).to_contain_text("380m")
  no_overflow(m);m.screenshot(path=str(out/"mobile-taiji-courts.png"),full_page=True);mobile.close()
  ok("390px mobile has usable source comparisons and phase/extents controls without horizontal overflow")
  nojs=browser.new_context(viewport={"width":390,"height":844},java_script_enabled=False)
  n=nojs.new_page();n.goto(base+"prosperity-taiji-courts.html",wait_until="networkidle")
  expect(n.locator(".phase-detail[data-phase-card='northern_wei']")).to_be_visible()
  assert n.locator(".source-card").count()==6
  assert all(img.evaluate("(el)=>el.complete && el.naturalWidth>0") for img in n.locator("figure img").all())
  no_overflow(n);nojs.close()
  ok("without JavaScript all three figures and their citations are still readable")
  assert not errors,errors
  ctx.close();browser.close()
finally:
 (out/"report.json").write_text(json.dumps({"base_url":base,"checks":checks,"errors":errors},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 if server:server.shutdown()
 if temp:temp.cleanup()
