#!/usr/bin/env python3
"""Actual local/live HTTP terrain reading; do not replace with screenshots alone."""
import argparse,functools,http.server,json,os,tempfile,threading
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--base-url');p.add_argument('--output',default='artifacts/v30-browser');a=p.parse_args()
out=ROOT/a.output;out.mkdir(parents=True,exist_ok=True);srv=None;tmp=None;checks=[];errors=[]
if a.base_url:base=a.base_url.rstrip('/')+'/'
else:
 tmp=tempfile.TemporaryDirectory();root=Path(tmp.name);(root/'luoyang-city').symlink_to(ROOT/'_site',target_is_directory=True)
 class Quiet(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
 srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=root));threading.Thread(target=srv.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{srv.server_port}/luoyang-city/'
def ok(n):checks.append({'name':n,'status':'passed'});print('PASS',n,flush=True)
def ready(p):p.wait_for_function("document.documentElement.dataset.terrainReady==='true'",timeout=60000)
try:
 with sync_playwright() as pw:
  kw={'headless':True}
  if os.environ.get('CHROMIUM_PATH'):kw['executable_path']=os.environ['CHROMIUM_PATH']
  browser=pw.chromium.launch(**kw);ctx=browser.new_context(viewport={'width':1540,'height':1100});page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(base,wait_until='networkidle');expect(page.locator('#terrain-release-entry')).to_be_visible();expect(page.locator('.brand-release')).to_have_text('v3.0-alpha.1');ok('default website visibly shows current terrain release and real preview')
  page.locator('#terrain-release-entry a').last.click();ready(page);expect(page.locator('#release-status')).to_contain_text('已核对线上提交');ok('real terrain entry loads under the repository subpath')
  expect(page.locator('#raster-image')).to_have_attribute('href','./terrain/v3.0/relief.png');ok('real raster, not synthetic fixture or empty placeholder')
  page.screenshot(path=str(out/'terrain-desktop.png'),full_page=True)
  for v in ['hillshade','slope','raw-slope','relief']:
   page.locator('#raster-layer').select_option(v);expect(page.locator('#raster-image')).to_have_attribute('href','./terrain/v3.0/'+v+'.png')
  ok('elevation, hillshade, raw and smoothed slopes switch actual images')
  page.locator('#contour-toggle').check();expect(page.locator('#contour-image')).to_be_visible();page.locator('#sheet-toggle').check();expect(page.locator('#sheet-line')).to_be_visible();ok('contours and archival sheet seam are independent overlays')
  old=page.locator('#terrain-svg').get_attribute('viewBox');page.locator('#zoom-in').click();assert page.locator('#terrain-svg').get_attribute('viewBox')!=old
  page.locator('#reset-view').click();assert page.locator('#terrain-svg').get_attribute('viewBox')==old;ok('terrain camera zoom and reset')
  box=page.locator('#terrain-canvas').bounding_box();page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2);expect(page.locator('#sample-readout')).to_contain_text('180米');expect(page.locator('#sample-readout')).to_contain_text('现代地表');ok('physical map click reads a labelled coarse modern-surface sample')
  page.locator('#raster-layer').select_option('slope');page.reload(wait_until='networkidle');ready(page);expect(page.locator('#raster-layer')).to_have_value('slope');expect(page.locator('#contour-toggle')).to_be_checked();ok('terrain layer and contour deep link restore after full reload')
  page.locator('[data-tab="archive"]').click();expect(page.locator('#archive-cards article')).to_have_count(2);expect(page.locator('#panel-archive')).to_contain_text('不把它们宣称为已配准');expect(page.locator('#archive-cards')).to_contain_text('1964-09');ok('archival maps expose edition, compilation, printing and unresolved datum')
  page.screenshot(path=str(out/'archival-desktop.png'),full_page=True)
  page.locator('[data-tab="skeleton"]').click();expect(page.locator('#passages .passage')).to_have_count(20);page.locator('#passage-filter').select_option('palace');expect(page.locator('#passages .passage')).to_have_count(5);expect(page.locator('#panel-skeleton')).to_contain_text('0个新增古代经纬度');ok('historical network remains textual, filtered and explicitly unregistered')
  for path in ['downloads/luoyang-terrain-v30-gis.zip','terrain/v3.0/metadata.json','downloads/terrain-method-v30.html','terrain/v3.0/ams-ni49-7.jpg','terrain/v3.0/ams-ni49-8.jpg']:
   assert ctx.request.get(base+path).status==200,path
  meta=ctx.request.get(base+'terrain/v3.0/metadata.json').json();assert meta['synthetic'] is False and meta['ancient_registered_nodes']==0 and meta['analysis_grid']==[1695,1860];ok('actual product downloads and manifest are publicly accessible')
  mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);mp=mobile.new_page();mp.on('pageerror',lambda e:errors.append(str(e)))
  mp.goto(base+'v3.0.html',wait_until='networkidle');ready(mp);assert mp.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
  mp.locator('#contour-toggle').check();mp.locator('#raster-layer').select_option('hillshade');expect(mp.locator('#contour-image')).to_be_visible();mp.screenshot(path=str(out/'terrain-mobile.png'),full_page=True);ok('mobile terrain controls work without horizontal page overflow')
  assert not errors,errors;ok('zero runtime errors');browser.close()
except Exception as e:checks.append({'name':'acceptance','status':'failed','error':str(e)});raise
finally:
 (out/'results.json').write_text(json.dumps({'base_url':base,'checks':checks,'runtime_errors':errors},ensure_ascii=False,indent=2))
 if srv:srv.shutdown()
 if tmp:tmp.cleanup()
