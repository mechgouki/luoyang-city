#!/usr/bin/env python3
"""Acquire adjacent AMS sheet and openly licensed modern river reference."""
from pathlib import Path
import json,time,urllib.request,urllib.parse,hashlib
from terrain_source_v30 import download,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/terrain-source-v30';OUT.mkdir(parents=True,exist_ok=True)
p=OUT/'ams-ni49-8.jpg';url='https://maps.lib.utexas.edu/maps/ams/china/txu-oclc-10552568-ni49-8.jpg';download(url,p)
receipt={'ams-ni49-8.jpg':{'url':url,'sha256':sha(p),'bytes':p.stat().st_size}}
query='[out:json][timeout:60];way["waterway"="river"](34.55,112.30,34.90,112.90);out geom;'
errors=[]
for endpoint in ['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter']:
 try:
  req=urllib.request.Request(endpoint,data=urllib.parse.urlencode({'data':query}).encode(),headers={'User-Agent':'Luoyang-Atlas-Research/3.0'})
  with urllib.request.urlopen(req,timeout=90) as r:raw=r.read()
  data=json.loads(raw);assert len(data.get('elements',[]))>0
  (OUT/'osm-rivers-raw.json').write_bytes(raw)
  features=[]
  for x in data['elements']:
   g=x.get('geometry',[])
   if len(g)>1:features.append({'type':'Feature','properties':{'osm_type':x['type'],'osm_id':x['id'],'tags':x.get('tags',{}),'temporal_scope':'modern volunteer map; not Northern Wei'},'geometry':{'type':'LineString','coordinates':[[v['lon'],v['lat']] for v in g]}})
  fc={'type':'FeatureCollection','license':'ODbL 1.0; https://www.openstreetmap.org/copyright','attribution':'© OpenStreetMap contributors','osm_timestamp':data.get('osm3s',{}).get('timestamp_osm_base'),'features':features}
  (OUT/'osm-rivers.geojson').write_text(json.dumps(fc,ensure_ascii=False,separators=(',',':')))
  receipt['osm']={'endpoint':endpoint,'query':query,'raw_sha256':hashlib.sha256(raw).hexdigest(),'features':len(features),'timestamp':fc['osm_timestamp'],'license':fc['license']};break
 except Exception as e:errors.append(str(e))
else:receipt['osm']={'status':'not_acquired','errors':errors}
receipt['acquired_at_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());(OUT/'extra-source-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print(json.dumps(receipt,ensure_ascii=False))
