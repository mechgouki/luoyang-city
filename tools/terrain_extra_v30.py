#!/usr/bin/env python3
"""Adjacent archival sheet and dated satellite surface-water reference.
OSM access failed in preflight; it is not an input or a fabricated substitute.
"""
from pathlib import Path
import json,time,urllib.request
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import reproject,Resampling
from terrain_source_v30 import download,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/terrain-source-v30';OUT.mkdir(parents=True,exist_ok=True)
p=OUT/'ams-ni49-8.jpg';url='https://maps.lib.utexas.edu/maps/ams/china/txu-oclc-10552568-ni49-8.jpg';download(url,p)
receipt={'ams-ni49-8.jpg':{'url':url,'sha256':sha(p),'bytes':p.stat().st_size}}
with rasterio.open(OUT/'modern-dsm-utm49-30m.tif') as r:prof=r.profile;shape=r.shape;trans=r.transform;crs=r.crs
# Read the full upstream cell for the enclosing projected rectangle. A clipped
# geographic source window would leave triangular no-data slivers after warping.
with rasterio.open(ROOT/'.cache-terrain/cop30_N34E112.tif') as s:
 arr=np.full(shape,-9999,dtype=np.float32)
 reproject(rasterio.band(s,1),arr,src_transform=s.transform,src_crs=s.crs,dst_transform=trans,dst_crs=crs,dst_nodata=-9999,resampling=Resampling.bilinear)
with rasterio.open(OUT/'modern-dsm-utm49-30m.tif','w',**prof) as r:r.write(arr,1)
assert np.all(arr!=-9999)
rec=json.loads((OUT/'source-receipt.json').read_text());rec['analysis_grid'].update(valid_pixels=int(arr.size),min_m=float(arr.min()),max_m=float(arr.max()),quantiles_m=dict(zip(['1','5','25','50','75','95','99'],map(float,np.percentile(arr,[1,5,25,50,75,95,99])))));rec['analysis_grid']['footprint_note']='Projected enclosing rectangle sampled from full source tile; native geographic crop remains separately preserved.';(OUT/'source-receipt.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2))
url='https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N33E111_Map.tif'
with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',GDAL_HTTP_TIMEOUT='90'):
 with rasterio.open(url) as s:
  window=from_bounds(112.27,34.52,112.93,34.93,transform=s.transform).round_offsets().round_lengths();cover=s.read(1,window=window);ct=s.window_transform(window);native=s.profile.copy();native.update(width=cover.shape[1],height=cover.shape[0],transform=ct,compress='deflate')
  with rasterio.open(OUT/'worldcover-2021-native.tif','w',**native) as r:r.write(cover,1)
  dest=np.zeros(shape,dtype=np.uint8)
  reproject(cover,dest,src_transform=ct,src_crs=s.crs,src_nodata=0,dst_transform=trans,dst_crs=crs,dst_nodata=0,resampling=Resampling.nearest)
  receipt['worldcover']={'url':url,'source_crs':str(s.crs),'native_pixel_spacing_degrees':list(s.res),'native_window_sha256':sha(OUT/'worldcover-2021-native.tif'),'dataset':'ESA WorldCover 10m 2021 v200','license':'CC BY 4.0','water_class':80,'water_definition':'Permanent water bodies classification for 2021; not a 2026 observation or ancient river channel.','output_resampling':'nearest-neighbour onto 30m DSM grid','water_pixels_30m':int((dest==80).sum()),'nodata_pixels':int((dest==0).sum())}
profile=prof.copy();profile.update(dtype='uint8',nodata=0,predictor=1)
with rasterio.open(OUT/'worldcover-2021-utm49-30m.tif','w',**profile) as r:r.write(dest,1)
assert (dest==80).any() and not (dest==0).any()
receipt['acquired_at_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());(OUT/'extra-source-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print(json.dumps(receipt,ensure_ascii=False))
