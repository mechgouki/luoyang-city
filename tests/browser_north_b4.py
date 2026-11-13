#!/usr/bin/env python3
"""Actual HTTP/HTTPS acceptance for literary B4 and printed-grid calibration."""
import argparse,functools,http.server,json,os,tempfile,threading
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--base-url');p.add_argument('--output',default='artifacts/north-b4-browser');args=p.parse_args()
out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True)
checks=[];errors=[];srv=None;tmp=None;page=None
if args.base_url:base=args.base_url.rstrip('/')+'/'
else:
 tmp=tempfile.TemporaryDirectory();root=Path(tmp.name);(root/'luoyang-city').symlink_to(ROOT/'_site',target_is_directory=True)
 class Quiet(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
 srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=root))
 threading.Thread(target=srv.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{srv.server_port}/luoyang-city/'
def ok(name):checks.append({'name':name,'status':'passed'});print('PASS',name,flush=True)
def north_ready(p):p.wait_for_function("document.documentElement.dataset.northB4Ready==='true'")
def frame_ready(p):p.wait_for_function("document.documentElement.dataset.historicalFrameReady==='true'")
try:
 with sync_playwright() as pw:
  opts={'headless':True}
  if os.environ.get('CHROMIUM_PATH'):opts['executable_path']=os.environ['CHROMIUM_PATH']
  browser=pw.chromium.launch(**opts);ctx=browser.new_context(viewport={'width':1500,'height':1000});page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(base,wait_until='networkidle');page.wait_for_function("document.documentElement.dataset.northMainReady==='true'")
  expect(page.locator('#north-b4-entry')).to_be_visible()
  expect(page.locator('#map-viewport [data-batch="dual-b4"]')).to_have_count(4)
  expect(page.locator('#map-viewport [data-batch="dual-b1"]')).to_have_count(7)
  expect(page.locator('#map-viewport [data-batch="dual-b2"]')).to_have_count(8)
  expect(page.locator('#map-viewport #west-glyphs-b3')).to_have_count(1)
  expect(page.locator('.feature-target')).to_have_count(179)
  ok('current main contains four B4 type groups and preserves B1/B2/B3 and 179 original targets')
  page.goto(base+'#map?region=R01',wait_until='networkidle')
  page.locator('.feature-target[data-ids="gate_daxia"] .feature-hit').click()
  expect(page.locator('.north-coverage')).to_contain_text('NG02')
  expect(page.locator('.north-coverage a')).to_have_attribute('href','./dual-north.html#literary?id=NG01')
  ok('physical Daxia main-map click opens B4 evidence without script-order errors')
  page.goto(base+'dual-north.html#literary?id=NG02',wait_until='networkidle');north_ready(page)
  expect(page.locator('#evidence-picker option')).to_have_count(16)
  expect(page.locator('#detail')).to_contain_text('三层')
  expect(page.locator('#detail')).to_contain_text('校读')
  expect(page.locator('#release-status')).to_contain_text('构建一致')
  expect(page.locator('#map')).to_have_attribute('src','./dual/maps/L06.svg')
  page.screenshot(path=str(out/'north-desktop.png'),full_page=True)
  ok('new region and 16 attributed evidence records load with matching build metadata')
  page.locator('#archive').check();expect(page.locator('#map')).to_have_attribute('src','./dual/maps/L06-archive.svg')
  page.reload(wait_until='networkidle');north_ready(page)
  expect(page.locator('#archive')).to_be_checked();expect(page.locator('#evidence-picker')).to_have_value('NG02')
  page.locator('#archive').uncheck();expect(page.locator('#map')).to_have_attribute('src','./dual/maps/L06.svg')
  page.locator('#zoom-in').click();assert page.locator('#map').evaluate("e=>e.style.width")=='140%'
  page.locator('#zoom-reset').click();assert page.locator('#map').evaluate("e=>e.style.width")=='100%'
  ok('same-region archive comparison, selection deep link and zoom/reset work')
  page.locator('[data-tab="gates"]').click();expect(page.locator('#map')).to_have_attribute('src','./dual/maps/N-gates.svg')
  page.locator('[data-tab="membership"]').click();expect(page.locator('#map')).to_have_attribute('src','./dual/maps/N-membership.svg')
  page.locator('#evidence-picker').select_option('NG13');expect(page.locator('#detail')).to_contain_text('不是北面第三门')
  page.locator('[data-tab="evidence"]').click();expect(page.locator('#all-evidence article')).to_have_count(16)
  ok('directions, front relations and unlocated membership have separate readable views')
  page.goto(base+'historical-frame.html',wait_until='networkidle');frame_ready(page)
  expect(page.locator('#point-picker option')).to_have_count(13)
  expect(page.locator('#points-overlay circle')).to_have_count(13)
  expect(page.locator('#point-table tr')).to_have_count(13)
  page.locator('#point-picker').select_option('7-C03');expect(page.locator('#point-detail')).to_contain_text('未参加模型拟合')
  expect(page.locator('#crop-image')).to_have_attribute('src','./historical-frame/crops/7-C03.jpg')
  page.locator('#crosshair').uncheck();expect(page.locator('#crop-overlay')).to_be_hidden()
  page.locator('#crosshair').check();expect(page.locator('#crop-overlay')).to_be_visible()
  ok('printed-grid controls, held-out point crop and removable crosshair are inspectable')
  page.locator('[data-sheet="NI49-8"]').click();page.locator('#point-picker').select_option('8-C02')
  page.locator('[data-view="rectified"]').click();expect(page.locator('#main-image')).to_have_attribute('src','./historical-frame/sheet-8-rectified.jpg')
  expect(page.locator('#points-overlay')).to_be_hidden();expect(page.locator('#view-caption')).to_contain_text('未指定EPSG')
  page.reload(wait_until='networkidle');frame_ready(page)
  expect(page.locator('#point-picker')).to_have_value('8-C02');expect(page.locator('[data-view="rectified"]')).to_have_attribute('aria-pressed','true')
  page.locator('[data-view="scan"]').click();page.locator('#points-overlay circle[data-point="8-C04"]').click()
  expect(page.locator('#point-picker')).to_have_value('8-C04')
  page.screenshot(path=str(out/'historical-frame-desktop.png'),full_page=True)
  ok('both sheets, physical point clicks, image rectification and deep-link restoration work')
  for f in ['downloads/dual-north-b4-atlas.pdf','downloads/dual-north-b4-package.zip','downloads/dual-north-b4-evidence.csv','downloads/luoyang-historical-frame-b4.zip','historical-frame/points.csv','dual/maps/L06.svg','dual/maps/N-evidence.svg']:
   response=ctx.request.get(base+f);assert response.status==200,(f,response.status)
  data=ctx.request.get(base+'dual/north-b4.json').json();info=ctx.request.get(base+'build-info.json').json()
  frame=ctx.request.get(base+'historical-frame/metadata.json').json()
  assert data['source_commit']==info['source_commit']==info['north_b4']['source_commit']
  assert data['ancient_absolute_positions_added']==0 and frame['ancient_geographic_positions_added']==0
  assert all(s['calibration']['geographic_crs'] is None and s['calibration']['internal_holdout_check']['count']==5 for s in frame['sheets'])
  preserved=ctx.request.get(base+'dual/north-b4-preservation.json').json();assert preserved['protected_unchanged'] is True
  ok('PDF/CSV/ZIP/SVG and research records publish with source identity and no ancient registration')
  mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);mp=mobile.new_page();mp.on('pageerror',lambda e:errors.append(str(e)))
  mp.goto(base,wait_until='networkidle');mp.wait_for_function("document.documentElement.dataset.northMainReady==='true'")
  assert mp.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
  mp.goto(base+'dual-north.html',wait_until='networkidle');north_ready(mp)
  assert mp.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
  mp.locator('[data-tab="gates"]').tap();mp.locator('#evidence-picker').select_option('NG08');expect(mp.locator('#detail')).to_contain_text('地形高顯')
  mp.screenshot(path=str(out/'north-mobile.png'),full_page=True)
  mp.goto(base+'historical-frame.html',wait_until='networkidle');frame_ready(mp)
  assert mp.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
  mp.locator('[data-sheet="NI49-8"]').tap();mp.locator('#point-picker').select_option('8-C05');expect(mp.locator('#point-detail')).to_contain_text('不是地面检查点')
  mp.screenshot(path=str(out/'historical-frame-mobile.png'),full_page=True)
  ok('mobile main navigation, evidence and both map sheets work without page overflow')
  assert not errors,errors;ok('zero browser runtime errors');browser.close()
except Exception as e:
 checks.append({'name':'B4 browser acceptance','status':'failed','error':str(e)})
 if page:
  try:page.screenshot(path=str(out/'failure.png'),full_page=True)
  except Exception:pass
 raise
finally:
 (out/'results.json').write_text(json.dumps({'base_url':base,'checks':checks,'runtime_errors':errors},ensure_ascii=False,indent=2))
 if srv:srv.shutdown()
 if tmp:tmp.cleanup()
