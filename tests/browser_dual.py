#!/usr/bin/env python3
"""Actual HTTP acceptance: published B1 and next-region B2, desktop and mobile."""
import argparse,functools,http.server,json,os,tempfile,threading
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--base-url');p.add_argument('--output',default='artifacts/dual-browser');args=p.parse_args();out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True)
srv=None;tmp=None;checks=[];errors=[];page=None
if args.base_url:base=args.base_url.rstrip('/')+'/'
else:
 tmp=tempfile.TemporaryDirectory();root=Path(tmp.name);(root/'luoyang-city').symlink_to(ROOT/'_site',target_is_directory=True)
 class Quiet(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*a):pass
 srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=root));threading.Thread(target=srv.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{srv.server_port}/luoyang-city/'
def ok(s):checks.append({'name':s,'status':'passed'});print('PASS',s,flush=True)
def ready(p):p.wait_for_function("document.documentElement.dataset.dualReady==='true'",timeout=60000)
try:
 with sync_playwright() as pw:
  opts={'headless':True}
  if os.environ.get('CHROMIUM_PATH'):opts['executable_path']=os.environ['CHROMIUM_PATH']
  browser=pw.chromium.launch(**opts);ctx=browser.new_context(viewport={'width':1540,'height':1100});page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(base,wait_until='networkidle');page.wait_for_function("document.documentElement.dataset.dualMainReady==='true'")
  expect(page.locator('.brand-release')).to_have_text('v3.0-dual.b2');expect(page.locator('#dual-release-entry')).to_be_visible();ok('default home exposes the released B1+B2, not a hidden branch')
  expect(page.locator('#map-viewport [data-batch="dual-b1"]')).to_have_count(7);expect(page.locator('#map-viewport [data-batch="dual-b2"]')).to_have_count(8);expect(page.locator('.feature-target')).to_have_count(179);ok('current main map really redraws 15 groups while preserving all original click targets')
  page.goto(base+'#map?region=R03',wait_until='networkidle');page.locator('.feature-target[data-ids="ic_yaoguang"] .feature-hit').click();expect(page.locator('.dual-coverage')).to_contain_text('原图已深化');expect(page.locator('.inspector-name')).to_have_text('瑶光寺');ok('physical main-map click opens the new evidence section')
  page.screenshot(path=str(out/'main-r03.png'),full_page=True)
  page.goto(base+'dual-b1.html',wait_until='networkidle');ready(page);expect(page.locator('#region-picker')).to_have_value('L01');expect(page.locator('#canvas')).to_have_attribute('data-map','dual/maps/L01.svg');ok('approved B1 independently published with its original first-region entry')
  page.locator('#old-baseline').check();ready(page);expect(page.locator('#canvas')).to_have_attribute('data-map','assets/master-v24.svg');assert page.locator('#canvas [data-batch]').count()==0
  page.locator('#old-baseline').uncheck();ready(page);assert page.locator('#canvas [data-batch="dual-b1"]').count()==7;ok('archive comparison actually loads the old SVG rather than hiding a ring')
  for region in ['L01','L02','L03','L04']:
   page.locator('#region-picker').select_option(region);ready(page);expect(page.locator('#canvas')).to_have_attribute('data-map','dual/maps/'+region+'.svg')
  ok('all four regional maps load from the same current masters')
  page.goto(base+'dual-b2.html#literary?region=L04',wait_until='networkidle');ready(page)
  expect(page.locator('#release-status')).to_contain_text('已核对正式发布');old=page.locator('#canvas svg').first.get_attribute('viewBox');page.locator('#zoom-in').click();assert page.locator('#canvas svg').first.get_attribute('viewBox')!=old;page.locator('#reset').click();assert page.locator('#canvas svg').first.get_attribute('viewBox')==old;ok('B2 actual release metadata and zoom/reset controls work')
  target=page.locator('#canvas [data-entity-id="ic_jiuhua"]');target.click(position={'x':target.bounding_box()['width']/2,'y':target.bounding_box()['height']/2});ready(page);expect(page.locator('#inspector-title')).to_contain_text('九华');expect(page.locator('#inspector')).to_contain_text('G07');ok('B2 physical building click resolves to component evidence')
  page.screenshot(path=str(out/'palace-desktop.png'),full_page=True)
  page.reload(wait_until='networkidle');ready(page);expect(page.locator('#entity-picker')).to_have_value('ic_jiuhua');ok('region and selected object restore after full page reload')
  page.locator('[data-tab="conditions"]').click();ready(page)
  page.locator('#condition-mode').select_option('platform');ready(page);expect(page.locator('#canvas')).to_have_attribute('data-map','dual/maps/G-platform.svg')
  page.locator('#condition-mode').select_option('hill');ready(page);expect(page.locator('#canvas')).to_have_attribute('data-map','dual/maps/G-hill.svg');expect(page.locator('#canvas')).to_contain_text('不新增点');ok('Diaotai alternatives affect an explicit membership diagram, not a new coordinate')
  page.locator('#condition-mode').select_option('water');ready(page);expect(page.locator('#canvas')).to_contain_text('地下石窦');expect(page.locator('#canvas')).to_contain_text('不视为全年水文');page.screenshot(path=str(out/'underground-relations.png'),full_page=True);ok('underground collective relationships are distinct from surface-flow geometry')
  page.locator('[data-tab="terrain"]').click();ready(page);expect(page.locator('#canvas')).to_have_attribute('data-map','dual/maps/T2.svg');expect(page.locator('#legend')).to_contain_text('不是北魏');ok('independent terrain board shows unregistered ancient inserts without fake coordinates')
  page.screenshot(path=str(out/'terrain-desktop.png'),full_page=True)
  for mode,path in [('class','dual/terrain-classes.png'),('raw','terrain/v3.0/relief.png'),('board','dual/maps/T2.svg')]:
   page.locator('#terrain-mode').select_option(mode);ready(page);expect(page.locator('#canvas')).to_have_attribute('data-map',path)
  ok('modern raw relief, heuristic classification and interpretive board are distinct views')
  page.locator('[data-tab="evidence"]').click();ready(page);expect(page.locator('#all-evidence article')).to_have_count(30);expect(page.locator('#all-evidence')).to_contain_text('彼此前后没有明文');ok('14 prior decisions and 16 next-region evidence records are inspectable')
  for f in ['dual/data.json','dual/preservation.json','downloads/dual-map-atlas.pdf','downloads/dual-b1-atlas.pdf','downloads/dual-map-report.html','downloads/dual-evidence.csv','downloads/dual-map-package.zip','dual/b1-glyphs-decoded.json']:
   response=ctx.request.get(base+f);assert response.status==200,(f,response.status)
  info=ctx.request.get(base+'build-info.json').json();data=ctx.request.get(base+'dual/data.json').json();assert info['source_commit']==data['source_commit'] and info['dual_counts']['changed_groups']==15
  ok('published PDFs, reports, data and archive downloads are reachable and match the release')
  assert all(e['geographic_coordinates'] is None for e in data['b2']['evidence']);assert data['terrain']['ancient_registered_buildings']==0;ok('new evidence and modern terrain do not manufacture ancient geographic positions')
  for f in ['v2.8.html','v2.9.html','v3.0.html']:assert ctx.request.get(base+f).status==200
  ok('all independently archived earlier entrypoints remain available')
  mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);mp=mobile.new_page();mp.on('pageerror',lambda e:errors.append(str(e)))
  mp.goto(base+'dual-b2.html',wait_until='networkidle');ready(mp);assert mp.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
  mp.locator('[data-tab="terrain"]').tap();ready(mp);mp.locator('#terrain-mode').select_option('class');ready(mp);mp.locator('[data-tab="literary"]').tap();ready(mp);mp.locator('#entity-picker').select_option('ic_yaoguang');ready(mp);expect(mp.locator('#inspector-title')).to_have_text('瑶光寺');mp.screenshot(path=str(out/'mobile.png'),full_page=True);ok('mobile tabs, terrain and object selection work without page overflow')
  assert not errors,errors;ok('zero JavaScript runtime errors');browser.close()
except Exception as e:
 checks.append({'name':'dual browser acceptance','status':'failed','error':str(e)})
 if page:
  try:page.screenshot(path=str(out/'failure.png'),full_page=True)
  except Exception:pass
 raise
finally:
 (out/'results.json').write_text(json.dumps({'base_url':base,'checks':checks,'runtime_errors':errors},ensure_ascii=False,indent=2))
 if srv:srv.shutdown()
 if tmp:tmp.cleanup()
