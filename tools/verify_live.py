#!/usr/bin/env python3
"""Check all public HTTPS assets, including the unchanged original PDF hash.

.nojekyll is a build-control file, excluded from the upload-pages artifact by
GitHub's action. It is not a public asset and is explicitly recorded as such.
"""
import argparse, concurrent.futures, hashlib, json, os, time
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen
p=argparse.ArgumentParser();p.add_argument('--base-url',required=True);p.add_argument('--commit',default=os.environ.get('GITHUB_SHA'));p.add_argument('--output',default='artifacts/live-http.json');args=p.parse_args()
base=args.base_url.rstrip('/')+'/'
if urlparse(base).scheme!='https':raise SystemExit('HTTPS required for live verification')
def get(path):
 target=urljoin(base,quote(path,safe='/'))
 if not target.startswith(base) or '..' in PurePosixPath(path).parts:raise ValueError('Unsafe asset path')
 req=Request(target,headers={'User-Agent':'Luoyang-Atlas-Acceptance/0.2.0','Cache-Control':'no-cache'})
 with urlopen(req,timeout=30) as response:
  if response.status!=200:raise ValueError(f'{path}: HTTP {response.status}')
  if not response.geturl().startswith(base):raise ValueError(f'{path}: unexpected redirect')
  return response.read()
info=None
for attempt in range(12):
 try:
  info=json.loads(get('build-info.json'))
  if args.commit and info['source_commit']!=args.commit:raise ValueError('Deployment/CDN still serves another commit')
  if info.get('supplement_version')!='v2.5-r07':raise ValueError('Missing v2.5 supplement')
  break
 except Exception:
  if attempt==11:raise
  time.sleep(10)
results=[];excluded=['.nojekyll']
def check(item):
 path,digest=item;body=get(path);actual=hashlib.sha256(body).hexdigest()
 if actual!=digest:raise ValueError(f'{path}: SHA-256 mismatch')
 return {'path':path,'bytes':len(body),'sha256':actual,'status':'passed'}
try:
 public_files=[(path,digest) for path,digest in info['files_sha256'].items() if path not in excluded]
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
  results=list(pool.map(check,public_files))
 assert info['counts']['sheets']==37 and info['counts']['entities']==339
 assert len(json.loads(get('data/research-v25.json'))['evidence'])==18
 report={'base_url':base,'commit':info['source_commit'],'status':'passed','checked_files':len(results),'build_control_not_published':excluded,'files':results,'checked_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 print(f'LIVE PASS: {len(results)} public assets verified; 37 original SVGs, 3 R07 diagrams and original PDF included')
except Exception as e:
 report={'base_url':base,'status':'failed','error':str(e),'files':results};raise
finally:
 target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,ensure_ascii=False,indent=2))
