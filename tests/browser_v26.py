#!/usr/bin/env python3
"""Run the v2.6 acceptance against the actual project subpath or live HTTPS."""
import argparse,functools,http.server,json,os,tempfile,threading
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--base-url');p.add_argument('--output',default='artifacts/v26-browser');a=p.parse_args()
out=ROOT/a.output;out.mkdir(parents=True,exist_ok=True);server=None;tmp=None
if a.base_url:base=a.base_url.rstrip('/')+'/'
else:
 tmp=tempfile.TemporaryDirectory();root=Path(tmp.name);(root/'luoyang-city').symlink_to(ROOT/'_site',target_is_directory=True)
 class Quiet(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=root))
 threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/luoyang-city/'
checks=[];errors=[];page=None

def ok(name):checks.append({'name':name,'status':'passed'});print('PASS',name,flush=True)
def ready(page):page.wait_for_function("document.documentElement.dataset.model26Ready==='true' && document.documentElement.dataset.researchReady==='true'")
try:
 with sync_playwright() as pw:
  kwargs={'headless':True}
  if os.environ.get('CHROMIUM_PATH'):kwargs['executable_path']=os.environ['CHROMIUM_PATH']
  browser=pw.chromium.launch(**kwargs);ctx=browser.new_context(viewport={'width':1540,'height':1040})
  page=ctx.new_page();page.on('pageerror',lambda err:errors.append(str(err)))
  page.goto(base+'#model?case=s011',wait_until='networkidle');ready(page)
  expect(page.locator('#m26-plan-image')).to_have_attribute('src','./assets/models-v26/s011-west.svg')
  expect(page.locator('.m26-plan-buttons a')).to_have_count(3);ok('s011 provides two feasible sides for the same premises')
  page.locator('.m26-plan-buttons a[href*="pick=east"]').click();expect(page.locator('#m26-plan-image')).to_have_attribute('src','./assets/models-v26/s011-east.svg')
  page.reload(wait_until='networkidle');ready(page);expect(page.locator('#m26-plan-image')).to_have_attribute('src','./assets/models-v26/s011-east.svg');ok('candidate deep link restores the east witness after full reload')
  page.screenshot(path=str(out/'candidate-east.png'),full_page=True)
  page.locator('input[data-assumption="west_side"]').check();expect(page.locator('#m26-case')).to_have_value('s111')
  expect(page.locator('.m26-plan-buttons a')).to_have_count(2);ok('enabling west-side inheritance removes the incompatible east witness')
  page.locator('input[data-assumption="jingle_east"]').uncheck();expect(page.locator('#m26-case')).to_have_value('s110')
  row=page.locator('.m26-table tbody tr').filter(has_text='景乐寺在御道东');expect(row).to_contain_text('模型内必然');ok('removing emendation alone retains alternative deduction')
  page.locator('input[data-assumption="east_side"]').uncheck();expect(page.locator('#m26-case')).to_have_value('s100')
  row=page.locator('.m26-table tbody tr').filter(has_text='景乐寺在御道东');expect(row).to_contain_text('未能限定');ok('removing both supporting premises exposes indeterminacy')
  page.locator('#m26-case').select_option('ritual111');expect(page.locator('#m26-conflict')).to_be_visible();ok('same identity-time-reference model exposes conflict cores')
  page.screenshot(path=str(out/'conflict.png'),full_page=True)
  for case in ['ritual011','ritual101','ritual110']:
   page.locator('#m26-case').select_option(case);expect(page.locator('#m26-conflict')).to_have_count(0)
  ok('relaxing each conflict premise restores consistency without asserting historical migration')
  page.goto(base+'#model?case=s110&tab=atoms&atom=GES',wait_until='networkidle');ready(page)
  expect(page.locator('#atom-GES')).to_have_class('m26-atom selected');expect(page.locator('#atom-GES')).to_contain_text('F08');expect(page.locator('#atom-GES')).to_contain_text('F09')
  page.locator('#atom-GES a[href^="#research"]').click();expect(page.locator('#page-research')).to_be_visible();ok('atomic assumptions link to underlying v2.5 evidence')
  page.goto(base+'#model?tab=relations',wait_until='networkidle');ready(page)
  expect(page.locator('#m26-relation-rows tr')).to_have_count(482)
  page.locator('#m26-target-filter').select_option('unresolved');expect(page.locator('#m26-relation-rows tr')).to_have_count(24)
  page.locator('#m26-relation-search').fill('city_jinyang');expect(page.locator('#m26-relation-rows tr')).to_have_count(1);ok('482 lossless rows and the broken pre-existing reference remain reviewable')
  page.goto(base+'#model?tab=sensitivity',wait_until='networkidle');ready(page);expect(page.locator('#m26-sensitivity tbody tr')).to_have_count(16);ok('all 16 scenario results are visible')
  for case in ['without_L','without_H','without_W','merge_taifu']:
   page.goto(base+'#model?case='+case,wait_until='networkidle');ready(page);expect(page.locator('#m26-case')).to_have_value(case)
  ok('source ablations and identity comparison do not fabricate new geographic layouts')
  page.goto(base+'#map?entity=ic_taiwei',wait_until='networkidle');ready(page);expect(page.locator('#inspector-body')).to_contain_text('打开R07空间检验');ok('baseline map links to the new model without changing entity IDs')
  page.goto(base+'#model?case=s011',wait_until='networkidle');ready(page);page.screenshot(path=str(out/'desktop.png'),full_page=True)
  # Every generated plan is exercised, not only the default pair.
  urls=page.evaluate('milestone26.candidates.map(p=>p.path)')
  for path in urls:
   resp=ctx.request.get(base+path);assert resp.status==200 and '<svg' in resp.text()
  ok('all 13 generated SVG candidates load')
  mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
  page=mobile.new_page();page.on('pageerror',lambda err:errors.append(str(err)))
  page.goto(base+'#model?case=s011',wait_until='networkidle');ready(page)
  page.locator('.m26-plan-buttons a[href*="pick=east"]').tap();expect(page.locator('#m26-plan-image')).to_have_attribute('src','./assets/models-v26/s011-east.svg')
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
  page.screenshot(path=str(out/'mobile.png'),full_page=True);ok('mobile candidate switching stays within page width')
  page.goto(base+'#model?tab=relations',wait_until='networkidle');ready(page)
  page.locator('#m26-target-filter').select_option('unresolved');expect(page.locator('#m26-relation-rows tr')).to_have_count(24)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2');ok('mobile relation review has contained table scrolling')
  assert not errors,errors;ok('no runtime errors in desktop or mobile');browser.close()
except Exception as ex:
 checks.append({'name':'acceptance','status':'failed','error':str(ex)})
 raise
finally:
 (out/'results.json').write_text(json.dumps({'base_url':base,'checks':checks,'runtime_errors':errors},ensure_ascii=False,indent=2))
 if server:server.shutdown()
 if tmp:tmp.cleanup()
