#!/usr/bin/env python3
"""Exercise shared-coordinate temporal reading under actual local/live HTTP."""
import argparse,functools,http.server,json,os,tempfile,threading
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--base-url');p.add_argument('--output',default='artifacts/v29-browser');a=p.parse_args()
out=ROOT/a.output;out.mkdir(parents=True,exist_ok=True);server=None;tmp=None;page=None
if a.base_url:base=a.base_url.rstrip('/')+'/'
else:
 tmp=tempfile.TemporaryDirectory();root=Path(tmp.name);(root/'luoyang-city').symlink_to(ROOT/'_site',target_is_directory=True)
 class Quiet(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=root));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/luoyang-city/'
checks=[];errors=[]
def ok(name):checks.append({'name':name,'status':'passed'});print('PASS',name,flush=True)
def ready(page):page.wait_for_function("document.documentElement.dataset.chronology29Ready==='true'",timeout=45000)
def paired(page):
 return page.locator('#c29-left svg').get_attribute('viewBox')==page.locator('#c29-right svg').get_attribute('viewBox')
try:
 with sync_playwright() as pw:
  kw={'headless':True}
  if os.environ.get('CHROMIUM_PATH'):kw['executable_path']=os.environ['CHROMIUM_PATH']
  browser=pw.chromium.launch(**kw);ctx=browser.new_context(viewport={'width':1540,'height':1100})
  page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto(base,wait_until='networkidle');ready(page)
  current_release=ctx.request.get(base+'release.json').json()['release'];expect(page.locator('.brand-release')).to_have_text(current_release);expect(page.locator('.c29-entry')).to_be_visible();ok('default homepage visibly links the new temporal comparison')
  expect(page.locator('#v28-online-status')).to_contain_text('已核对在线发布');r=ctx.request.get(base+'release.json').json();b=ctx.request.get(base+'build-info.json').json()
  assert r['source_commit']==b['source_commit'] and r['release']==current_release and b['chronology_version']=='v2.9';ok('current release and build manifest agree')
  page.locator('.c29-entry a').click();expect(page.locator('#page-compare')).to_be_visible();expect(page.locator('#c29-site option')).to_have_count(12)
  expect(page.locator('#c29-left [data-dossier]')).to_have_count(11);expect(page.locator('#c29-right [data-dossier]')).to_have_count(11);assert paired(page);ok('twelve dossiers share eleven pre-existing independent anchors')
  before=page.locator('#c29-left svg').get_attribute('viewBox');page.locator('#c29-zoom-in').click();assert paired(page) and before!=page.locator('#c29-left svg').get_attribute('viewBox');ok('zoom synchronizes both reference views')
  area=page.locator('#c29-left').bounding_box();page.mouse.move(area['x']+35,area['y']+40);page.mouse.down();page.mouse.move(area['x']+95,area['y']+85,steps=5);page.mouse.up();assert paired(page);ok('drag synchronizes both reference views')
  page.locator('#c29-home').click();page.locator('#c29-left [data-dossier="D29-05"] circle').click();expect(page.locator('#c29-site')).to_have_value('D29-05');ok('physical existing map anchor opens the matching dossier');page.locator('#c29-site').select_option('D29-01')
  expect(page.locator('#record-T29-02')).to_have_attribute('data-time','before');expect(page.locator('#record-T29-02')).to_contain_text('不自动认定547年仍未修复');ok('534 tower fire does not become a 547 whole-temple state')
  page.screenshot(path=str(out/'comparison-desktop.png'),full_page=True)
  page.locator('#c29-site').select_option('D29-07');expect(page.locator('#c29-unlocated')).to_be_visible();expect(page.locator('#c29-left [data-dossier="D29-07"]')).to_have_count(0)
  expect(page.locator('#record-T29-16')).to_contain_text('不取平均');ok('group-only inner Jianzhong remains unplaced and preserves competing dates')
  page.locator('#c29-year').select_option('531');expect(page.locator('#record-T29-16')).to_have_attribute('data-time','alternatives');ok('alternative chronology is not flattened to a continuous interval')
  page.locator('#c29-site').select_option('D29-08');expect(page.locator('#c29-unlocated')).to_be_hidden();expect(page.locator('#record-T29-18')).to_have_attribute('data-time','lower_bound');ok('eastern Jianzhong remains a separate entity with an open time bound')
  page.locator('#c29-site').select_option('D29-09');page.locator('#c29-year').select_option('528');expect(page.locator('#record-T29-20')).to_have_attribute('data-time','later')
  page.locator('#c29-year').select_option('533');expect(page.locator('#record-T29-20')).to_have_attribute('data-time','at');ok('explicit 533 tower completion is not projected backward into the prosperous layer')
  page.locator('#c29-site').select_option('D29-02');expect(page.locator('.c29-record')).to_have_count(3);expect(page.locator('#record-T29-05')).to_contain_text('不是塔的竣工日期');ok('Jingming construction start and inscription commission remain distinct')
  page.goto(base+'v2.9.html#compare?site=D29-05&year=547',wait_until='networkidle');page.reload(wait_until='networkidle');ready(page)
  expect(page.locator('#c29-site')).to_have_value('D29-05');expect(page.locator('#record-T29-12')).to_have_attribute('data-time','lower_bound');expect(page.locator('#record-T29-12')).to_contain_text('不记作寺院火灾');ok('deep-link reload preserves site, year and activity-versus-building distinction')
  page.locator('#c29-site').select_option('D29-04');expect(page.locator('#record-T29-09')).to_contain_text('不等于拆毁学堂');expect(page.locator('#c29-left [data-dossier="v3_shijing"]')).to_have_count(0);ok('portable stones use a related place, not an invented object coordinate')
  for i in range(1,13):page.locator('#c29-site').select_option(f'D29-{i:02d}');assert paired(page)
  ok('every dossier maintains the same reference and two matching viewports')
  page.goto(base+'#map?entity=ic_jingle',wait_until='networkidle');ready(page);expect(page.locator('.c29-inline')).to_contain_text('同址时层对照');page.locator('.c29-inline a').click();expect(page.locator('#c29-site')).to_have_value('D29-05');ok('main map inspector links directly into new research')
  for path in ['downloads/chronology-v29.csv','downloads/chronology-study-v29.html','data/chronology-v29.json','assets/chronology-v29.svg']:
   assert ctx.request.get(base+path).status==200
  paths=page.locator('script[src],link[rel="stylesheet"]').evaluate_all('(els)=>els.map(e=>e.getAttribute("src")||e.getAttribute("href"))');assert all(x.startswith('./_assets/') for x in paths);ok('new downloads exist and executing dependencies stay fingerprinted')
  mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);mp=mobile.new_page();mp.on('pageerror',lambda e:errors.append(str(e)))
  mp.goto(base+'v2.9.html#compare?site=D29-09&year=533',wait_until='networkidle');ready(mp);mp.locator('#c29-site').select_option('D29-07');expect(mp.locator('#c29-unlocated')).to_be_visible();assert paired(mp)
  assert mp.evaluate('document.documentElement.scrollWidth<=innerWidth+2');mp.screenshot(path=str(out/'mobile.png'),full_page=True);ok('mobile dossier controls, unknown placement and side-by-side reference stack without overflow')
  assert not errors,errors;ok('no runtime errors in desktop or mobile');browser.close()
except Exception as e:
 checks.append({'name':'acceptance','status':'failed','error':str(e)});raise
finally:
 (out/'results.json').write_text(json.dumps({'base_url':base,'checks':checks,'runtime_errors':errors},ensure_ascii=False,indent=2))
 if server:server.shutdown()
 if tmp:tmp.cleanup()
