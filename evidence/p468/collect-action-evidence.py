"""Extract the P4.6.8 acceptance reports and raw screenshots from completed Actions ZIPs."""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile
p=argparse.ArgumentParser()
p.add_argument('--pr-zip',type=Path,required=True)
p.add_argument('--live-zip',type=Path,required=True)
p.add_argument('--output',type=Path,default=Path(__file__).parent)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
with ZipFile(a.pr_zip) as z:
    for device in ['desktop','mobile']:
        names=[n for n in z.namelist() if n.endswith('/p468-'+device+'-report.json')]
        assert len(names)==1,names
        raw=z.read(names[0]);report=json.loads(raw)
        assert report['status']=='passed' and report['errors']==[] and report['map_count']==5
        (a.output/f'pr-{device}-report.json').write_bytes(raw)
    names=[n for n in z.namelist() if n.endswith('prosperity-semantic-tests.txt')]
    assert len(names)==1
    (a.output/'pr-semantic-tests.txt').write_bytes(z.read(names[0]))
with ZipFile(a.live_zip) as z:
    names=[n for n in z.namelist() if n.endswith('live-http.json')]
    assert len(names)==1
    (a.output/'live-http.json').write_bytes(z.read(names[0]))
    for device in ['desktop','mobile']:
        names=[n for n in z.namelist() if n.endswith('/p468-'+device+'-report.json')]
        assert len(names)==1,names
        raw=z.read(names[0]);report=json.loads(raw)
        assert report['status']=='passed' and report['errors']==[] and report['map_count']==5
        assert report['base_url'].startswith('https://mechgouki.github.io/')
        (a.output/f'live-{device}-report.json').write_bytes(raw)
    screenshots=[n for n in z.namelist() if Path(n).name.startswith('p468-') and n.endswith('.png')]
    assert len(screenshots)>=20,len(screenshots)
    for name in screenshots:
        (a.output/Path(name).name.replace('p468-','live-',1)).write_bytes(z.read(name))
print(json.dumps({'screenshots':len(screenshots),'reports':'extracted'},ensure_ascii=False))
