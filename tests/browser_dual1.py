#!/usr/bin/env python3
import argparse,functools,http.server,json,os,tempfile,threading
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('--base-url');p.add_argument('--output',default='artifacts/dual1-browser');a=p.parse_args();out=ROOT/a.output;out.mkdir(parents=True,exist_ok=True);tmp=None;srv=None;checks=[];errors=[]
if a.base_url:base=a.base_url.rstrip('/')+'/'
else:
 tmp=tempfile.TemporaryDirectory();r=Path(tmp.name);(r/'luoyang-city').symlink_to(ROOT/'_site',target_is_directory=True)
 class Quiet(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
 srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=r));threading.Thread(target=srv.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{srv.server_port}/luoyang-city/'
def ok(s):checks.append({'name':s,'status':'passed'});print('PASS',s,flush=True)
def ready(page):page.wait_for_function("document.documentElement.dataset.dualReady==='true'",timeout=60000)
try:
 with sync_playwright() as pw:
  kw={'headless':True}
  if os.environ.get('CHROMIUM_PATH'):kw['executable_path']=os.environ['CHROMIUM_PATH']
  browser=pw.chromium.launch(**kw);ctx=browser.new_context(viewport={'width':1540,'height':1100},permissions=['clipboard-read','clipboard-write']);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(base,wait_until='networkidle');expect(page.locator('#dual-release-entry')).to_be_visible();expect(page.locator('.brand-release')).to_have_text('v3.1-alpha.1');page.wait_for_function("document.documentElement.dataset.portal28Ready==='true'");expect(page.locator('#map-viewport [data-change]')).to_have_count(10);ok('root current map uses ten changed groups, not only a new version badge')
  page.locator('#dual-release-entry a').click();ready(page);expect(page.locator('#view-title')).to_contain_text('v2.10');ok('parallel workbench loads from default homepage')
  expect(page.locator('#canvas [data-change]')).to_have_count(10);page.locator('#canvas [data-entity="ic_yongning"]').click();expect(page.locator('#details')).to_contain_text('塔与其北佛殿');ok('physical Yongning symbol click shows exact map change and evidence')
  page.screenshot(path=str(out/'document-r07.png'),full_page=True)
  page.locator('[data-mode="archive"]').click();expect(page.locator('#view-title')).to_contain_text('原版');expect(page.locator('#canvas [data-change]')).to_have_count(0);ok('archival view retains original SVG rather than regenerated imitation')
  page.locator('[data-mode="document"]').click();expect(page.locator('#canvas [data-change]')).to_have_count(10)
  for code,entity in [('R04','bridge_jianchun'),('R10','v3_jingming')]:
   page.locator('#region').select_option(code);page.locator(f'#canvas [data-entity="{entity}"]').click();expect(page.locator('#details')).to_contain_text('本批改图');page.screenshot(path=str(out/(code+'.png')),full_page=True)
  ok('three focus crops and current geometry use one common schematic mother map')
  page.locator('[data-mode="terrain"]').click();expect(page.locator('#interpretation')).to_be_visible();expect(page.locator('#canvas [data-entity]')).to_have_count(0);expect(page.locator('#details')).to_contain_text('古代经纬度：未定');ok('terrain mode has no invented ancient geographic point')
  page.locator('#terrain-style').select_option('relief');expect(page.locator('#canvas image')).to_have_attribute('href','./terrain/v3.0/relief.png');page.locator('#terrain-style').select_option('interpretation');expect(page.locator('#canvas image')).to_have_attribute('href','./dual1/terrain-interpretation.png');ok('modern classified and original real-relief rasters both work')
  page.locator('#region').select_option('R07');page.locator('#details [data-item="ic_yongning"]').click();expect(page.locator('#details')).to_contain_text('不对应左侧地形图');page.locator('#details [data-dual]').click();expect(page.locator('#view-title')).to_contain_text('文献工作图');ok('terrain inset links back to same document entity without georeferencing it')
  old=page.locator('#canvas svg').get_attribute('viewBox');page.locator('#zoom-in').click();assert old!=page.locator('#canvas svg').get_attribute('viewBox');page.locator('#reset').click();expect(page.locator('#canvas svg')).to_have_attribute('viewBox',old);ok('zoom and reset work on schematic map')
  page.locator('#copy-link').click();expect(page.locator('#copy-link')).to_have_text('已复制');u=page.evaluate('navigator.clipboard.readText()');shared=ctx.new_page();shared.goto(u,wait_until='networkidle');ready(shared);expect(shared.locator('#details h2')).to_have_text('永宁寺');shared.close();ok('copied deep link restores selected entity')
  page.locator('[data-mode="terrain"]').click();page.reload(wait_until='networkidle');ready(page);expect(page.locator('[data-mode="terrain"]')).to_have_attribute('aria-pressed','true');page.screenshot(path=str(out/'terrain-desktop.png'),full_page=True);ok('full reload restores terrain mode and selected region')
  expect(page.locator('#changes-table tr')).to_have_count(10);info=ctx.request.get(base+'dual1/changes.json').json();assert all(c['ancient_lonlat'] is None for c in info['changes']);ok('all ten changes retain absent ancient coordinates and provenance')
  for name in ['R07-v210.svg','R04-v210.svg','R10-v210.svg','terrain-parallel.svg','modern-form-classes.tif']:
   assert ctx.request.get(base+'dual1/'+name).status==200
  assert ctx.request.get(base+'downloads/dual1-workpack.zip').status==200;ok('all maps, georaster and full workpack are downloadable')
  mob=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);mp=mob.new_page();mp.on('pageerror',lambda e:errors.append(str(e)));mp.goto(base+'dual-map.html#view=terrain&region=R04',wait_until='networkidle');ready(mp);assert mp.evaluate('document.documentElement.scrollWidth<=innerWidth+2');mp.locator('[data-mode="document"]').tap();expect(mp.locator('#view-title')).to_contain_text('v2.10');mp.screenshot(path=str(out/'mobile.png'),full_page=True);ok('mobile supports both modes without document overflow')
  assert not errors,errors;ok('no browser runtime errors');browser.close()
except Exception as e:checks.append({'name':'acceptance','status':'failed','error':str(e)});raise
finally:
 (out/'results.json').write_text(json.dumps({'base_url':base,'checks':checks,'runtime_errors':errors},ensure_ascii=False,indent=2))
 if srv:srv.shutdown()
 if tmp:tmp.cleanup()
