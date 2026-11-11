#!/usr/bin/env python3
"""Browser acceptance at the real project subpath, locally or after deployment."""
import argparse, functools, http.server, json, os, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--base-url');parser.add_argument('--output',default='artifacts/browser');args=parser.parse_args()
out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True)
server=None;tmp=None
if args.base_url:base=args.base_url.rstrip('/')+'/'
else:
 tmp=tempfile.TemporaryDirectory();p=Path(tmp.name);(p/'luoyang-city').symlink_to(ROOT/'_site',target_is_directory=True)
 class Quiet(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=p))
 threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/luoyang-city/'
results=[];errors=[]
def passed(name):results.append({'name':name,'status':'passed'});print('PASS',name,flush=True)
try:
 with sync_playwright() as pw:
  opts={'headless':True}
  if os.environ.get('CHROMIUM_PATH'):opts['executable_path']=os.environ['CHROMIUM_PATH']
  browser=pw.chromium.launch(**opts)
  ctx=browser.new_context(viewport={'width':1540,'height':1040})
  page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(base,wait_until='networkidle');page.wait_for_function("document.documentElement.dataset.researchReady==='true'")
  expect(page.locator('.region-btn')).to_have_count(11);expect(page.locator('.feature-target')).to_have_count(179);passed('project subpath loads all baseline records and marker overlay')
  for code in [f'R{i:02d}' for i in range(1,12)]:
   page.locator(f'.region-btn[data-code="{code}"]').click();expect(page.locator('#map-status')).to_contain_text(code)
   assert page.evaluate('viewBox.every(Number.isFinite) && viewBox[2]>0 && viewBox[3]>0')
   center_visible=page.evaluate('''() => {const r=regions.find(x=>x.code===selectedRegion);const b=drawingBounds(...r.bbox);const cx=b[0]+b[2]/2,cy=b[1]+b[3]/2;return cx>=viewBox[0]&&cy>=viewBox[1]&&cx<=viewBox[0]+viewBox[2]&&cy<=viewBox[1]+viewBox[3]}''')
   assert center_visible,code
  passed('all 11 region centers lie inside the selected camera')
  page.goto(base+'#map?entity=ic_yongning',wait_until='networkidle');page.wait_for_function("document.documentElement.dataset.researchReady==='true'")
  expect(page.locator('.inspector-name')).to_have_text('永宁寺')
  page.locator('.feature-target[data-ids="ic_yongning"] .feature-hit').click();expect(page.locator('.inspector-name')).to_have_text('永宁寺');passed('ordinary physical marker click opens Yongning')
  expect(page.locator('#inspector-body')).to_contain_text('v2.5 专题证据')
  page.locator('#inspector-body a[href="#map?entity=ic_taiwei"]').click();expect(page.locator('.inspector-name')).to_have_text('太尉府');passed('Yongning to Taiwei relationship navigation')
  page.screenshot(path=str(out/'entity.png'),full_page=True)
  page.locator('#inspector-body a[href="#issues?issue=C01"]').click();expect(page.locator('#issue-detail')).to_contain_text('尚待研究');expect(page.locator('#issue-detail')).to_contain_text('v1.1')
  assert page.locator('#issue-detail a[href$="e01.svg"]').count()==1
  passed('C01 preserves legacy plate and links current stable sheet IDs')
  page.locator('#issue-status-filters button[data-state="clarified"]').click();expect(page.locator('.issue-item:visible')).to_have_count(2);passed('30 questions are classified; clarified status is not an unresolved count')
  page.goto(base+'#research?panel=B&evidence=E07',wait_until='networkidle');page.wait_for_function("document.documentElement.dataset.researchReady==='true'")
  expect(page.locator('#evidence-E07')).to_have_class('r-card r-selected');expect(page.locator('#evidence-E07')).to_contain_text('范');passed('evidence deep link restores panel B and E07 after reload')
  for panel in ['A','B','C']:
   page.locator(f'.r-tabs a[href="#research?panel={panel}"]').click()
   expect(page.locator('#research-diagram')).to_have_attribute('src',f'./assets/research/R07-{panel}.svg')
   page.wait_for_function("document.querySelector('#research-diagram').complete && document.querySelector('#research-diagram').naturalWidth>0")
   page.screenshot(path=str(out/f'research-{panel.lower()}.png'),full_page=True)
  passed('all three diagrams render with evidence cards')
  page.goto(base+'#map',wait_until='networkidle');page.wait_for_function("document.documentElement.dataset.researchReady==='true'")
  page.locator('#place-search').fill('景明');page.locator('.search-item').first.click();expect(page.locator('.inspector-name')).to_contain_text('景明');passed('site search works')
  unlocated=page.evaluate("entities.find(e=>!markers.some(m=>m.ids.includes(e.id)))?.id")
  page.goto(base+'#map?entity='+unlocated,wait_until='networkidle');page.wait_for_function("document.documentElement.dataset.researchReady==='true'")
  expect(page.locator('#inspector-body')).to_contain_text('具体位置未定');passed('unlocated record does not acquire a map point')
  page.locator('a[data-nav="atlas"]').click();expect(page.locator('.sheet-card')).to_have_count(37);passed('37 original atlas sheets remain available')
  page.goto(base+'#map',wait_until='networkidle');page.wait_for_function("document.documentElement.dataset.researchReady==='true'")
  page.locator('#home-map').click();expect(page.locator('.atlas-svg')).to_have_class('atlas-svg r-overview')
  page.locator('#detail-mode').select_option('full');assert not page.locator('.atlas-svg').evaluate("el=>el.classList.contains('r-overview')");passed('overview/detail label switch does not mutate source SVG')
  page.screenshot(path=str(out/'desktop.png'),full_page=True)
  ctx.close()
  mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=1)
  page=mobile.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(base,wait_until='networkidle');page.wait_for_function("document.documentElement.dataset.researchReady==='true'")
  page.locator('#filter-toggle').tap();page.locator('.region-btn[data-code="R07"]').tap();expect(page.locator('#map-status')).to_contain_text('R07')
  page.goto(base+'#map?entity=ic_yongning',wait_until='networkidle');page.wait_for_function("document.documentElement.dataset.researchReady==='true'");expect(page.locator('.inspector-name')).to_have_text('永宁寺')
  page.locator('#close-inspector').tap();assert not page.locator('#inspector').evaluate("x=>x.classList.contains('open')");passed('mobile filters, region selection and evidence drawer')
  page.goto(base+'#research?panel=B',wait_until='networkidle');page.wait_for_function("document.documentElement.dataset.researchReady==='true'")
  assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2'),'mobile horizontal page overflow'
  page.screenshot(path=str(out/'mobile.png'),full_page=True);passed('mobile research layout has no page overflow')
  assert not errors,errors
  passed('no browser runtime errors');browser.close()
except Exception as exc:
 results.append({'name':'browser acceptance','status':'failed','error':str(exc)});raise
finally:
 (out/'results.json').write_text(json.dumps({'base_url':base,'checks':results,'runtime_errors':errors},ensure_ascii=False,indent=2))
 if server:server.shutdown()
 if tmp:tmp.cleanup()
