#!/usr/bin/env python3
"""Browser acceptance for additional West B3, retaining B1/palace B2."""
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
import argparse,functools,http.server,json,os,tempfile,threading
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--base-url');p.add_argument('--output',default='artifacts/west-b3-browser');args=p.parse_args()
out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
srv=None;tmp=None
if args.base_url:base=args.base_url.rstrip('/')+'/'
else:
 tmp=tempfile.TemporaryDirectory();root=Path(tmp.name);(root/'luoyang-city').symlink_to(ROOT/'_site',target_is_directory=True)
 class Quiet(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
 srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=root))
 threading.Thread(target=srv.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{srv.server_port}/luoyang-city/'
def ok(s):checks.append({'name':s,'status':'passed'});print('PASS',s,flush=True)
page=None
try:
 with sync_playwright() as pw:
  opts={'headless':True}
  if os.environ.get('CHROMIUM_PATH'):opts['executable_path']=os.environ['CHROMIUM_PATH']
  b=pw.chromium.launch(**opts);ctx=b.new_context(viewport={'width':1440,'height':950});page=ctx.new_page()
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(base,wait_until='networkidle')
  page.wait_for_function("document.documentElement.dataset.dualMainReady==='true'")
  expect(page.locator('#west-b3-entry')).to_be_visible()
  expect(page.locator('#map-viewport #west-glyphs-b3')).to_have_count(1)
  expect(page.locator('#map-viewport [data-batch="dual-b1"]')).to_have_count(7)
  expect(page.locator('#map-viewport [data-batch="dual-b2"]')).to_have_count(8)
  expect(page.locator('.feature-target')).to_have_count(179)
  ok('homepage new B3 glyphs and banner; B1+B2 and 179 original targets preserved')
  page.goto(base+'dual-west.html',wait_until='networkidle')
  page.wait_for_function("document.documentElement.dataset.westB3Ready==='true'")
  expect(page.locator('#site option')).to_have_count(16)
  expect(page.locator('#map')).to_have_attribute('src','./dual/maps/L05.svg')
  ok('separate city-west research page and 16 evidence records load')
  page.locator('#site').select_option('W14')
  expect(page.locator('#detail')).to_contain_text('張方溝')
  expect(page.locator('#detail')).to_contain_text('未定位')
  ok('four-boundary Shouqiu evidence shows its original units and coordinate limits')
  page.locator('[data-tab="relations"]').click()
  expect(page.locator('#map')).to_have_attribute('src','./dual/maps/W-market.svg')
  page.locator('[data-tab="terrain"]').click()
  expect(page.locator('#map')).to_have_attribute('src','./dual/terrain-reading.png')
  expect(page.locator('#caption')).to_contain_text('没有任何古建筑位置线')
  ok('text relations and actual modern terrain are separate views')
  page.locator('[data-tab="evidence"]').click()
  expect(page.locator('#all article')).to_have_count(16)
  ok('all 16 full evidence cards inspectable')
  page.screenshot(path=str(out/'west-desktop.png'),full_page=True)
  page.reload(wait_until='networkidle')
  page.wait_for_function("document.documentElement.dataset.westB3Ready==='true'")
  expect(page.locator('#site')).to_have_value('W14')
  ok('deep link and selected evidence survive reload')
  for f in ['dual/maps/L05.svg','dual/maps/W-market.svg','dual/maps/T3-west.svg','dual/west-b3.json','downloads/dual-west-b3-atlas.pdf','downloads/dual-west-b3-evidence.csv']:
   r=ctx.request.get(base+f);assert r.status==200,(f,r.status)
  info=ctx.request.get(base+'build-info.json').json()
  west=ctx.request.get(base+'dual/west-b3.json').json()
  assert info['west_b3']['source_commit']==info['source_commit']
  assert west['ancient_absolute_positions_added']==0
  assert all(e['geographic_coordinates'] is None for e in west['evidence'])
  for p in ['dual-b1.html','dual-b2.html','v2.8.html','v2.9.html','v3.0.html']:
   assert ctx.request.get(base+p).status==200,p
  ok('PDF/CSV/SVG/JSON and all prior independent version entries accessible')
  mobile=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
  mp=mobile.new_page();mp.on('pageerror',lambda e:errors.append(str(e)))
  mp.goto(base+'dual-west.html',wait_until='networkidle')
  mp.wait_for_function("document.documentElement.dataset.westB3Ready==='true'")
  assert mp.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
  mp.locator('[data-tab="terrain"]').tap()
  expect(mp.locator('#map')).to_have_attribute('src','./dual/terrain-reading.png')
  mp.locator('#site').select_option('W09')
  expect(mp.locator('#detail')).to_contain_text('市南')
  mp.screenshot(path=str(out/'west-mobile.png'),full_page=True)
  ok('mobile evidence and terrain toggles work with no horizontal page overflow')
  assert not errors,errors;ok('no browser runtime errors');b.close()
except Exception as e:
 checks.append({'name':'B3 browser acceptance','status':'failed','error':str(e)})
 if page:
  try:page.screenshot(path=str(out/'failure.png'),full_page=True)
  except Exception:pass
 raise
finally:
 (out/'results.json').write_text(json.dumps({'base_url':base,'checks':checks,'runtime_errors':errors},ensure_ascii=False,indent=2))
 if srv:srv.shutdown()
 if tmp:tmp.cleanup()
