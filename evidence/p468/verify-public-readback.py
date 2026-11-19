"""Recheck P4.6.8 production, all downloads and the preserved P4.6.7/H2 bytes."""
import argparse
import concurrent.futures
import datetime
import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen
from pypdf import PdfReader

p=argparse.ArgumentParser()
p.add_argument('--commit',required=True)
p.add_argument('--output',type=Path,default=Path(__file__).parent)
args=p.parse_args()
base='https://mechgouki.github.io/luoyang-city/'
args.output.mkdir(parents=True,exist_ok=True)
fixed=json.loads((Path(__file__).parent/'preserved-sha256.json').read_text())
def get(path):
    with urlopen(Request(base+path,headers={'User-Agent':'Luoyang-research-readback/1.0'}),timeout=45) as response:
        return response.read(),response.status,response.headers.get('Content-Type'),response.geturl()
raw,status,_,_=get('build-info.json')
info=json.loads(raw)
assert status==200 and info['source_commit']==args.commit
water=info['prosperity_water_p468']
assert water['source_commit']==args.commit and water['atlas_pages']==5
assert water['reported_value_rows']==9 and water['legacy_objects_reviewed']==17
assert info['prosperity_water_p467']['source_commit']=='e6d0aaec76b5d25ed347f377ce19d7361b47f9a2'
(args.output/'build-info.json').write_bytes(raw)
paths=list(dict.fromkeys([water['page'],water['atlas'],*water['data_files'],
    *['water-468/'+name for name in water['plates']],
    'water-468/study.css','water-468/water-ui.js',
    'prosperity-water-p467.html','prosperity-south-p466.html','prosperity-field-p464.html',
    *fixed]))
def check(path):
    body,http,content_type,url=get(path)
    digest=hashlib.sha256(body).hexdigest()
    assert http==200 and digest==info['files_sha256'][path],path
    if path in fixed: assert digest==fixed[path],path
    extra={}
    if path==water['atlas']:
        extra['pdf_pages']=len(PdfReader(io.BytesIO(body)).pages)
        assert extra['pdf_pages']==5
        (args.output/'water-468.pdf').write_bytes(body)
    if path==water['readings']:
        data=json.loads(body)
        assert len(data['plates'])==5 and sum(len(x['segments']) for x in data['plates'])==water['segments']
        assert data['new_metric_measurements']==0 and data['geographic_coordinates'] is None
        assert data['new_516_528_bank_geometry'] is None
    if path=='prosperity-water-p467.html':
        assert body.count(b'id="p468-entry"')==1 and body.count(b'id="p468-pool-correction"')==1
    if path=='prosperity-south-p466.html': assert body.count(b'id="p467-entry"')==1
    if path==water['page']:
        assert b'id="measurements"' in body and b'id="water-study-data"' in body
    return {'path':path,'url':url,'http_status':http,'content_type':content_type,
            'bytes':len(body),'sha256':digest,'status':'passed',**extra}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(check,paths))
report={'checked_beijing':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds'),
        'base_url':base,'source_commit':info['source_commit'],'status':'passed','checked_files':len(results),
        'h2_p466_p467_bytes_unchanged':True,'water_metadata':water,'files':results}
(args.output/'public-readback.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'passed','source_commit':info['source_commit'],'checked_files':len(results),
                  'pdf_pages':5,'pdf_sha256':info['files_sha256'][water['atlas']]},ensure_ascii=False))
