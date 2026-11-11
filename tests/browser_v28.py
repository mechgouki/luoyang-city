#!/usr/bin/env python3
"""User-visible default map, release, old-cache isolation and mobile acceptance."""
import argparse,functools,http.server,json,os,tempfile,threading
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--base-url');p.add_argument('--output',default='artifacts/v28-browser');args=p.parse_args()
out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True);server=None;temp=None
if args.base_url:base=args.base_url.rstrip('/')+'/'
else:
 temp=tempfile.TemporaryDirectory();root=Path(temp.name);(root/'luoyang-city').symlink_to(ROOT/'_site',target_is_directory=True)
 class Quiet(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=root))
 threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/luoyang-city/'
results=[];errors=[]
def ok(name):results.append({'name':name,'status':'passed'});print('PASS',name,flush=True)
def ready(page):page.wait_for_function("document.documentElement.dataset.portal28Ready==='true'",timeout=45000)
try:
 with sync_playwright() as pw:
  opts={'headless':True}
  if os.environ.get('CHROMIUM_PATH'):opts['executable_path']=os.environ['CHROMIUM_PATH']
  browser=pw.chromium.launch(**opts);ctx=browser.new_context(viewport={'width':1540,'height':1100})
  page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  response=page.goto(base,wait_until='networkidle');assert response.status==200;ready(page)
  expect(page.locator('.brand-release')).to_have_text('v2.8');expect(page.locator('.map-header h1')).to_contain_text('最新研究')
  assert '交互图册 · v2.4' not in page.locator('.map-header').inner_text();ok('root homepage visibly shows integrated v2.8, not v2.4 title')
  expect(page.locator('#review-layer-v28 .v28-signal')).to_have_count(35)
  expect(page.locator('.feature-target')).to_have_count(179)
  expect(page.locator('#inspector-body')).to_contain_text('地图已经接入的新成果');ok('35 research overlays and 179 original click targets share the default map')
  expect(page.locator('#v28-online-status')).to_contain_text('已核对在线发布',timeout=15000)
  info=ctx.request.get(base+'build-info.json').json();rel=ctx.request.get(base+'release.json').json()
  assert rel['source_commit']==info['source_commit'] and rel['release']=='v2.8' and info['portal_version']=='v2.8';ok('actual release metadata matches deployed build commit')
  page.screenshot(path=str(out/'default-desktop.png'),full_page=True)
  page.locator('[data-v28-layer="baseline"]').click();expect(page.locator('#review-layer-v28')).to_be_hidden()
  page.locator('[data-v28-layer="review"]').click();expect(page.locator('#review-layer-v28')).to_be_visible();ok('baseline and research layers genuinely change the displayed map')
  page.locator('[data-v28-layer="events"]').click();page.locator('#v28-year').select_option('547');expect(page.locator('#inspector-body')).to_contain_text('547年')
  assert page.locator('.v28-signal[data-review-event="false"]:visible').count()==0
  assert page.locator('.v28-signal[data-review-event="true"]:visible').count()==4
  assert page.locator('.v28-signal[data-entities="v3_shijing"]').count()==0;ok('event layer marks only four existing anchors; unmapped movable objects get no invented point')
  page.goto(base+'#map?entity=ic_yongning&layer=events&year=547',wait_until='networkidle');ready(page)
  expect(page.locator('.v28-coverage')).to_contain_text('永宁塔火灾');expect(page.locator('.v28-coverage')).to_contain_text('此年状态仍须另证')
  expect(page.locator('.inspector-name')).to_have_text('永宁寺');ok('547 entity reading retains scoped past events without asserting permanent destruction')
  page.goto(base+'#map?region=R07',wait_until='networkidle');ready(page);expect(page.locator('#map-status')).to_contain_text('R07')
  page.locator('.feature-target[data-ids="ic_taiwei"] .feature-hit').click();expect(page.locator('.v28-coverage')).to_contain_text('候选位置')
  page.screenshot(path=str(out/'r07-desktop.png'),full_page=True);ok('real marker click opens integrated evidence and model entry')
  page.goto(base+'v2.8.html#map?layer=events&year=534',wait_until='networkidle');ready(page);page.reload(wait_until='networkidle');ready(page)
  expect(page.locator('[data-v28-layer="events"]')).to_have_attribute('aria-pressed','true');expect(page.locator('#v28-year')).to_have_value('534');ok('separate release URL restores layer and year on reload')
  paths=page.locator('script[src],link[rel="stylesheet"]').evaluate_all('(els)=>els.map(e=>e.getAttribute("src")||e.getAttribute("href"))')
  assert all(path.startswith('./_assets/') for path in paths);ok('every executing script and stylesheet uses content-addressed URLs')
  # Simulate stale legacy assets. The new entry must never request these URLs.
  stale=browser.new_context(viewport={'width':1540,'height':1000});hits=[];p2=stale.new_page();p2.on('pageerror',lambda e:errors.append(str(e)))
  root_path=urlsplit(base).path
  def old_assets(route):
   path=urlsplit(route.request.url).path
   if path==root_path+'app.js' or path==root_path+'styles.css' or path.startswith(root_path+'data/') or path==root_path+'assets/master-v24.svg':
    hits.append(path);route.fulfill(status=200,body='stale v2.4 content',content_type='text/plain')
   else:route.continue_()
  p2.route('**/*',old_assets);p2.goto(base+'v2.8.html#map',wait_until='networkidle');ready(p2)
  assert hits==[],hits;expect(p2.locator('.v28-signal')).to_have_count(35);ok('new entry ignores simulated stale unversioned v2.4 JS, CSS, JSON and map cache')
  # A newer manifest produces a safe same-site update link, not a false green claim.
  future=dict(rel,source_commit='f'*40)
  p2.route('**/release.json?*',lambda route:route.fulfill(status=200,body=json.dumps(future),content_type='application/json'))
  p2.locator('#v28-check-release').click();expect(p2.locator('#v28-update-link')).to_be_visible();expect(p2.locator('#v28-online-status')).to_contain_text('另一个发布版本');ok('different release commit produces an explicit update path')
  p2.route('**/release.json?*',lambda route:route.abort());p2.locator('#v28-check-release').click();expect(p2.locator('#v28-online-status')).to_contain_text('暂未核对');ok('failed online check never claims verified freshness')
  stale.close()
  for path in ['assets/master-v28-review.svg','downloads/release-v28.html','data/review-layer-v28.json']:
   assert ctx.request.get(base+path).status==200
  ok('new map download, release report and coverage data are publicly accessible')
  mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
  mp=mobile.new_page();mp.on('pageerror',lambda e:errors.append(str(e)))
  mp.goto(base+'v2.8.html',wait_until='networkidle');ready(mp)
  expect(mp.locator('.brand-release')).to_have_text('v2.8');assert mp.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
  mp.locator('[data-v28-layer="events"]').tap();mp.locator('#v28-year').select_option('527');expect(mp.locator('#v28-layer-legend')).to_contain_text('527')
  mp.screenshot(path=str(out/'mobile.png'),full_page=True);ok('mobile default page exposes release and working event-layer controls without page overflow')
  assert not errors,errors;ok('no runtime errors in normal and stale-cache browser contexts');browser.close()
except Exception as exc:
 results.append({'name':'acceptance','status':'failed','error':str(exc)});raise
finally:
 (out/'results.json').write_text(json.dumps({'base_url':base,'checks':results,'runtime_errors':errors},ensure_ascii=False,indent=2))
 if server:server.shutdown()
 if temp:temp.cleanup()
