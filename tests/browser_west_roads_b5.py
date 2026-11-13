#!/usr/bin/env python3
"""Actual HTTP/HTTPS acceptance for literary B5 and historical datum provenance."""
import argparse,functools,http.server,json,os,tempfile,threading
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--base-url');p.add_argument('--output',default='artifacts/west-roads-b5-browser');args=p.parse_args()
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
def ready(p):p.wait_for_function("document.documentElement.dataset.westRoadsB5Ready==='true'")
def datum_ready(p):p.wait_for_function("document.documentElement.dataset.historicalDatumReady==='true'")
try:
 with sync_playwright() as pw:
  opts={'headless':True}
  if os.environ.get('CHROMIUM_PATH'):opts['executable_path']=os.environ['CHROMIUM_PATH']
  browser=pw.chromium.launch(**opts);ctx=browser.new_context(viewport={'width':1500,'height':1000});page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(base,wait_until='networkidle');page.wait_for_function("document.documentElement.dataset.westRoadsMainReady==='true'")
  expect(page.locator('#west-roads-b5-entry')).to_be_visible()
  for batch,count in [('dual-b1',7),('dual-b2',8),('dual-b4',4),('dual-b5',11)]:
   expect(page.locator('#map-viewport [data-batch="'+batch+'"]')).to_have_count(count)
  expect(page.locator('#map-viewport #west-glyphs-b3')).to_have_count(1)
  expect(page.locator('.feature-target')).to_have_count(179)
  expect(page.locator('#map-viewport [data-batch="dual-b5"][data-entity-id="w_xuanzhong"]')).to_contain_text('城阳王徽宅')
  for eid in ['w_yongming','w_wangdianyu']:
   expect(page.locator('#map-viewport [data-batch="dual-b5"][data-entity-id="'+eid+'"]')).to_have_count(0)
  ok('eleven B5 symbols coexist with B1-B4; 179 original targets and nonspatial sidecars preserved')
  page.goto(base+'#map?region=R02',wait_until='networkidle')
  page.locator('.feature-target[data-ids="w_rongjue"] .feature-hit').click()
  expect(page.locator('.west-roads-coverage')).to_contain_text('WR03')
  expect(page.locator('.west-roads-coverage a')).to_have_attribute('href','./dual-west-roads.html#literary?id=WR03')
  ok('physical Rongjue click opens attributed B5 evidence')
  page.goto(base+'dual-west-roads.html#literary?id=WR06',wait_until='networkidle');ready(page)
  expect(page.locator('#evidence-picker option')).to_have_count(24)
  expect(page.locator('#detail')).to_contain_text('先后')
  expect(page.locator('#release-status')).to_contain_text('构建一致')
  expect(page.locator('#map')).to_have_attribute('src','./dual/maps/L07.svg')
  page.screenshot(path=str(out/'west-roads-desktop.png'),full_page=True)
  ok('L07 and 24 source records load with correct release identity')
  page.locator('#archive').check();expect(page.locator('#map')).to_have_attribute('src','./dual/maps/L07-archive.svg')
  page.reload(wait_until='networkidle');ready(page)
  expect(page.locator('#archive')).to_be_checked();expect(page.locator('#evidence-picker')).to_have_value('WR06')
  page.locator('#archive').uncheck();page.locator('#zoom-in').click();assert page.locator('#map').evaluate('e=>e.style.width')=='140%'
  page.locator('#zoom-reset').click();assert page.locator('#map').evaluate('e=>e.style.width')=='100%'
  ok('archive, evidence deep link and zoom restore correctly')
  page.locator('[data-tab="relations"]').click();expect(page.locator('#map')).to_have_attribute('src','./dual/maps/W5-relations.svg')
  page.locator('#evidence-picker').select_option('WR14');expect(page.locator('#detail')).to_contain_text('隔牆並門')
  page.locator('[data-tab="layers"]').click();expect(page.locator('#map')).to_have_attribute('src','./dual/maps/W5-layers.svg')
  page.locator('#evidence-picker').select_option('WR20');expect(page.locator('#detail')).to_contain_text('529')
  page.locator('[data-tab="evidence"]').click();expect(page.locator('#all-evidence article')).to_have_count(24)
  ok('partial-order, neighbour and house-to-temple time layers are inspectable')
  page.goto(base+'historical-datum.html',wait_until='networkidle');datum_ready(page)
  expect(page.locator('#datum-crop-picker option')).to_have_count(7)
  before=page.locator('#datum-margin-image').get_attribute('src')
  page.locator('[data-datum-sheet="NI49-8"]').click()
  assert page.locator('#datum-margin-image').get_attribute('src')!=before
  page.locator('#datum-crop-picker').select_option('compilation')
  page.wait_for_function("document.querySelector('#datum-margin-image').complete && document.querySelector('#datum-margin-image').naturalWidth>0")
  page.locator('#datum-source-toggle').click()
  expect(page.locator('#datum-source-details')).to_have_attribute('open','')
  expect(page.locator('#datum-source-body')).to_be_visible()
  expect(page.locator('#datum-source-details')).to_contain_text('WGS')
  ok('both original scan margins and digital-provider provenance are inspectable')
  page.locator('#datum-candidate-filter').select_option('approved')
  expect(page.locator('#datum-candidate-list')).to_contain_text('0')
  page.reload(wait_until='networkidle');datum_ready(page)
  expect(page.locator('[data-datum-sheet="NI49-8"]')).to_have_attribute('aria-pressed','true')
  expect(page.locator('#datum-crop-picker')).to_have_value('compilation')
  expect(page.locator('#datum-candidate-filter')).to_have_value('approved')
  expect(page.locator('#datum-source-details')).to_have_attribute('open','')
  expect(page.locator('#datum-source-body')).to_be_visible()
  page.locator('#datum-candidate-filter').select_option('pending')
  expect(page.locator('#datum-candidate-list')).to_contain_text('岩体')
  page.screenshot(path=str(out/'historical-datum-desktop.png'),full_page=True)
  ok('candidate screening and deep links preserve zero approved ground controls')
  for f in ['downloads/dual-west-roads-b5-atlas.pdf','downloads/dual-west-roads-b5-package.zip','downloads/dual-west-roads-b5-evidence.csv','downloads/luoyang-historical-datum-b5.zip','dual/maps/L07.svg','dual/maps/W5-evidence.svg','historical-datum/source-summary.svg','historical-datum/review-summary.svg']:
   response=ctx.request.get(base+f);assert response.status==200,(f,response.status)
  data=ctx.request.get(base+'dual/west-roads-b5.json').json();info=ctx.request.get(base+'build-info.json').json();datum=ctx.request.get(base+'historical-datum/metadata.json').json()
  assert data['source_commit']==info['source_commit']==info['west_roads_b5']['source_commit']==datum['source_commit']
  assert data['ancient_absolute_positions_added']==0 and datum['ancient_geographic_positions_added']==0
  assert datum['original_horizontal_datum'] is None and len(datum['approved_ground_control_points'])==0
  assert not datum['project_registration_to_wgs84'] and not datum['ground_accuracy_assessed']
  assert all(s['digitized_product']['assignment_role']=='post_publication_digitization_working_definition' for s in datum['sheets'])
  assert ctx.request.get(base+'dual/west-roads-b5-preservation.json').json()['protected_unchanged'] is True
  ok('new downloads, all prior assets and research metadata retain identity and interpretation boundaries')
  mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);mp=mobile.new_page();mp.on('pageerror',lambda e:errors.append(str(e)))
  mp.goto(base,wait_until='networkidle');mp.wait_for_function("document.documentElement.dataset.westRoadsMainReady==='true'")
  assert mp.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
  mp.goto(base+'dual-west-roads.html',wait_until='networkidle');ready(mp)
  assert mp.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
  mp.locator('[data-tab="layers"]').tap();mp.locator('#evidence-picker').select_option('WR09');expect(mp.locator('#detail')).to_contain_text('永熙')
  mp.screenshot(path=str(out/'west-roads-mobile.png'),full_page=True)
  mp.goto(base+'historical-datum.html',wait_until='networkidle');datum_ready(mp)
  assert mp.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
  mp.locator('[data-datum-sheet="NI49-8"]').tap();mp.locator('#datum-crop-picker').select_option('compilation');mp.locator('#datum-candidate-filter').select_option('approved')
  expect(mp.locator('#datum-candidate-list')).to_contain_text('0')
  mp.screenshot(path=str(out/'historical-datum-mobile.png'),full_page=True)
  ok('390px main, literary evidence and historical datum controls work without horizontal overflow')
  assert not errors,errors;ok('zero browser runtime errors');browser.close()
except Exception as e:
 checks.append({'name':'B5 browser acceptance','status':'failed','error':str(e)})
 if page:
  try:page.screenshot(path=str(out/'failure.png'),full_page=True)
  except Exception:pass
 raise
finally:
 (out/'results.json').write_text(json.dumps({'base_url':base,'checks':checks,'runtime_errors':errors},ensure_ascii=False,indent=2))
 if srv:srv.shutdown()
 if tmp:tmp.cleanup()
