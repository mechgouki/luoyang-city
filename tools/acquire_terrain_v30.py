#!/usr/bin/env python3
"""Download public research inputs only; no private data or credentials."""
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import hashlib,json,time
OUT=Path('terrain-inputs');OUT.mkdir(exist_ok=True)
SOURCES=[
 ('cop30_N34_E112.tif','https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N34_00_E112_00_DEM/Copernicus_DSM_COG_10_N34_00_E112_00_DEM.tif',True),
 ('ams-ni49-7.jpg','https://maps.lib.utexas.edu/maps/ams/china/txu-oclc-10552568-ni49-7.jpg',True),
 ('ams-ni49-8.jpg','https://maps.lib.utexas.edu/maps/ams/china/txu-oclc-10552568-ni49-8.jpg',True),
 ('cop30-readme.html','https://copernicus-dem-30m.s3.amazonaws.com/readme.html',False),
]
rows=[]
for name,url,required in SOURCES:
 row={'file':name,'url':url,'required':required,'retrieved_at':datetime.now(timezone.utc).isoformat()}
 for attempt in range(3):
  try:
   req=Request(url,headers={'User-Agent':'Luoyang-Atlas-research/3.0 (open geography research)'})
   with urlopen(req,timeout=90) as response:
    data=response.read();row.update(http=response.status,content_type=response.headers.get('Content-Type'),final_url=response.geturl())
   if name.endswith('.tif') and data[:2] not in (b'II',b'MM'):raise ValueError('Not TIFF')
   if name.endswith('.jpg') and not data.startswith(b'\xff\xd8'):raise ValueError('Not JPEG')
   (OUT/name).write_bytes(data);row.update(status='downloaded',bytes=len(data),sha256=hashlib.sha256(data).hexdigest());print(name,len(data),flush=True);break
  except Exception as exc:
   row.update(status='failed',error=str(exc));time.sleep(2)
 rows.append(row)
# Optional current mapped rivers, independently tagged as modern OSM data.
query='[out:json][timeout:90];way["waterway"="river"](34.48,112.22,34.94,112.94);out geom;'
for endpoint in ['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter']:
 try:
  from urllib.parse import urlencode
  req=Request(endpoint,data=urlencode({'data':query}).encode(),headers={'User-Agent':'Luoyang-Atlas-research/3.0'})
  with urlopen(req,timeout=110) as response:data=response.read()
  obj=json.loads(data);assert isinstance(obj.get('elements'),list)
  (OUT/'modern-rivers-osm.json').write_bytes(data)
  rows.append({'file':'modern-rivers-osm.json','url':endpoint,'query':query,'retrieved_at':datetime.now(timezone.utc).isoformat(),'status':'downloaded','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'license':'ODbL; OpenStreetMap contributors','note':'Modern mapped waterways, not historical river evidence.'});break
 except Exception as exc:print('Optional OSM:',str(exc),flush=True)
else:rows.append({'file':'modern-rivers-osm.json','status':'unavailable','note':'Do not fabricate replacement geometry.'})
(OUT/'acquisition.json').write_text(json.dumps({'sources':rows},ensure_ascii=False,indent=2)+'\n')
failed=[r['file'] for r in rows if r.get('required') and r['status']!='downloaded']
if failed:raise SystemExit('Required inputs missing: '+','.join(failed))
