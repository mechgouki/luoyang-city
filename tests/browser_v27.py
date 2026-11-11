#!/usr/bin/env python3
"""Real HTTP/HTTPS acceptance of v2.7; no mocked fetch responses."""
import argparse,functools,http.server,json,os,tempfile,threading
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--base-url');p.add_argument('--output',default='artifacts/v27-browser');args=p.parse_args()
out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True);server=None;tmp=None
if args.base_url:base=args.base_url.rstrip('/')+'/'
else:
 tmp=tempfile.TemporaryDirectory();root=Path(tmp.name);(root/'luoyang-city').symlink_to(ROOT/'_site',target_is_directory=True)
 class Quiet(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*a):pass
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=root));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/luoyang-city/'
checks=[];errors=[]
def ok(name):checks.append({'name':name,'status':'passed'});print('PASS',name,flush=True)
def ready(page):page.wait_for_function("document.documentElement.dataset.network27Ready==='true' && document.documentElement.dataset.researchReady==='true' && document.documentElement.dataset.model26Ready==='true'")
def query(page,q):return page.locator('#n27-queries tr[data-query="'+q+'"]')
try:
 with sync_playwright() as pw:
  opts={'headless':True}
  if os.environ.get('CHROMIUM_PATH'):opts['executable_path']=os.environ['CHROMIUM_PATH']
  browser=pw.chromium.launch(**opts);ctx=browser.new_context(viewport={'width':1540,'height':1040});page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(base+'#network',wait_until='networkidle');ready(page)
  expect(page.locator('#n27-queries tbody tr')).to_have_count(10);expect(page.locator('[data-join]')).to_have_count(4);ok('new network entry loads all queries and four explicit conditions')
  expect(query(page,'Q1')).to_contain_text('本条件下可建立');expect(query(page,'Q2')).to_contain_text('材料未建立')
  page.locator('[data-join="J1"]').check();expect(query(page,'Q2')).to_contain_text('本条件下可建立');ok('cross-source east path needs J1')
  page.reload(wait_until='networkidle');ready(page);expect(page.locator('[data-join="J1"]')).to_be_checked();expect(query(page,'Q2')).to_contain_text('本条件下可建立');ok('join settings survive a complete reload')
  expect(query(page,'Q3')).to_contain_text('材料未建立');page.locator('[data-join="J2"]').check();expect(query(page,'Q3')).to_contain_text('本条件下可建立');ok('southern canal path changes only with J2')
  page.locator('[data-join="J3"]').check();expect(query(page,'Q10')).to_contain_text('本条件下可建立');expect(query(page,'Q8')).to_contain_text('材料未建立');expect(query(page,'Q4')).to_contain_text('材料未建立');ok('bridge identity and alignment never become flow')
  page.locator('[data-join="FLOOD"]').check();expect(query(page,'Q7')).to_contain_text('本条件下可建立');ok('historical overflow is conditional rather than default permanent flow')
  page.locator('#n27-source').select_option('W');expect(query(page,'Q2')).to_contain_text('材料未建立');expect(query(page,'Q5')).to_contain_text('材料未建立');expect(query(page,'Q1')).to_contain_text('本条件下可建立');ok('source filtering removes its text and dependent joins')
  page.locator('#n27-source').select_option('LW');query(page,'Q3').locator('summary').click();expect(query(page,'Q3')).to_contain_text('JOIN2');ok('path certificate shows actual selected edges and premises')
  page.screenshot(path=str(out/'network-desktop.png'),full_page=True)
  for panel in ['east','palace','west','yong']:
   page.goto(base+'#network?panel='+panel,wait_until='networkidle');ready(page)
   expect(page.locator('#n27-diagram')).to_have_attribute('src','./assets/networks-v27/'+panel+'.svg')
   page.wait_for_function("document.querySelector('#n27-diagram').complete && document.querySelector('#n27-diagram').naturalWidth>0")
   page.locator('.n27-diagrams').screenshot(path=str(out/panel)+'.png')
  ok('all four typed network diagrams render')
  page.goto(base+'#network?tab=evidence&item=N08',wait_until='networkidle');ready(page);expect(page.locator('#n27-N08')).to_have_class('n27-card selected');expect(page.locator('#n27-N08')).to_contain_text('靑陽');ok('evidence deep link preserves source wording and selection')
  page.goto(base+'#network?tab=events&year=527',wait_until='networkidle');ready(page)
  expect(page.locator('[data-event="T04"]')).to_have_attribute('data-status','event_in_selected_year');expect(page.locator('[data-event="T04"]')).to_contain_text('建春门石桥')
  expect(page.locator('[data-event="T05"]')).to_have_attribute('data-status','event_not_yet_in_recorded_window');ok('527 bridge event does not shift to Yong bridge or to 534 tower fire')
  page.locator('#n27-year').fill('523');page.locator('#n27-year').press('Tab');expect(page.locator('[data-event="T03"]')).to_have_attribute('data-status','year_inside_uncertain_event_window')
  page.locator('#n27-year').fill('526');page.locator('#n27-year').press('Tab');expect(page.locator('[data-event="T03"]')).to_have_attribute('data-status','past_event_later_state_unknown');ok('construction interval does not generate completion or permanent construction status')
  page.locator('#n27-year').fill('547');page.locator('#n27-year').press('Tab')
  expect(page.locator('[data-event="T05"]')).to_have_attribute('data-status','past_event_later_state_unknown');expect(page.locator('[data-event="T09"]')).to_have_attribute('data-status','undated_reference')
  expect(page.locator('[data-event="T08"]')).to_contain_text('不下传全部建筑');ok('547 preserves undated columns, unknown later condition and aggregate scope')
  page.screenshot(path=str(out/'events.png'),full_page=True)
  page.goto(base+'#network?tab=events&entity=bridge_yong',wait_until='networkidle');ready(page);expect(page.locator('.n27-empty')).to_be_visible();ok('a bridge without a sampled event does not inherit another bridge damage')
  page.goto(base+'#network?tab=audit',wait_until='networkidle');ready(page);expect(page.locator('#n27-audit tbody tr')).to_have_count(339);ok('event coverage audit retains every baseline object')
  page.goto(base+'#map?entity=bridge_jianchun',wait_until='networkidle');ready(page);expect(page.locator('#inspector-body')).to_contain_text('水陆关系与事件范围');page.locator('#inspector-body a[href="#network?tab=events&entity=bridge_jianchun&year=547"]').click();expect(page.locator('[data-event="T04"]')).to_be_visible();ok('baseline entity links to its scoped event view')
  # Check static reports and graph data through actual HTTP, not DOM-only mocks.
  for path in ['downloads/network-study-v27.html','downloads/events-v27.csv','downloads/event-audit-v27.csv','data/network-v27.json']:
   response=ctx.request.get(base+path);assert response.status==200 and len(response.body())>100,path
  ok('standalone reports and data exports are public')
  mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);page=mobile.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(base+'#network?tab=network',wait_until='networkidle');ready(page);page.locator('[data-join="J1"]').check();expect(query(page,'Q2')).to_contain_text('本条件下可建立')
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2');page.screenshot(path=str(out/'mobile.png'),full_page=True)
  page.goto(base+'#network?tab=events&year=547',wait_until='networkidle');ready(page);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2');ok('mobile controls, tables and event cards remain within viewport')
  assert not errors,errors;ok('no desktop or mobile runtime errors');browser.close()
except Exception as ex:
 checks.append({'name':'v2.7 acceptance','status':'failed','error':str(ex)});raise
finally:
 (out/'results.json').write_text(json.dumps({'base_url':base,'checks':checks,'runtime_errors':errors},ensure_ascii=False,indent=2))
 if server:server.shutdown()
 if tmp:tmp.cleanup()
