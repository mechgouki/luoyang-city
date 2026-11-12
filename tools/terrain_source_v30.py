#!/usr/bin/env python3
"""Acquire actual terrain and archival map bytes. No synthetic elevation fallback."""
from pathlib import Path
import argparse, hashlib, json, math, shutil, time, urllib.request, zipfile
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds, reproject, Resampling
from rasterio.transform import from_origin
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
BBOX=(112.30,34.55,112.90,34.90)
URLS={
 'cop30_N34E112.tif':'https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N34_00_E112_00_DEM/Copernicus_DSM_COG_10_N34_00_E112_00_DEM.tif',
 'ams-ni49-7.jpg':'https://maps.lib.utexas.edu/maps/ams/china/txu-oclc-10552568-ni49-7.jpg'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def download(url,path):
 if path.exists() and path.stat().st_size>10000:return
 for n in range(3):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'Luoyang-Atlas-Terrain-Research/3.0'})
   with urllib.request.urlopen(req,timeout=90) as r,open(path.with_suffix(path.suffix+'.tmp'),'wb') as f:shutil.copyfileobj(r,f)
   path.with_suffix(path.suffix+'.tmp').replace(path);return
  except Exception:
   if n==2:raise
   time.sleep(4*(n+1))
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',default='artifacts/terrain-source-v30');p.add_argument('--include-repo',action='store_true');args=p.parse_args()
 out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True);cache=ROOT/'.cache-terrain';cache.mkdir(exist_ok=True)
 receipts={}
 for name,url in URLS.items():
  path=cache/name;download(url,path);receipts[name]={'url':url,'bytes':path.stat().st_size,'sha256':sha(path),'acquired_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 with rasterio.open(cache/'cop30_N34E112.tif') as src:
  w=from_bounds(*BBOX,transform=src.transform).round_offsets().round_lengths();a=src.read(1,window=w);trans=src.window_transform(w)
  profile=src.profile.copy();profile.update(width=a.shape[1],height=a.shape[0],transform=trans,count=1,driver='GTiff',compress='deflate',predictor=3)
  with rasterio.open(out/'modern-dsm-native.tif','w',**profile) as d:d.write(a,1)
  receipts['dem_metadata']={'crs':str(src.crs),'bounds':list(src.bounds),'resolution':list(src.res),'nodata':src.nodata,'tags':src.tags(),'source_grid':list(src.shape),'bbox_requested_wgs84':list(BBOX),'native_crop_grid':list(a.shape),'native_crop_bounds':list(rasterio.transform.array_bounds(*a.shape,trans))}
  b=transform_bounds(src.crs,'EPSG:32649',*BBOX,densify_pts=21);xmin=math.floor(b[0]/30)*30;ymax=math.ceil(b[3]/30)*30
  nx=math.ceil((b[2]-xmin)/30);ny=math.ceil((ymax-b[1])/30);dsttrans=from_origin(xmin,ymax,30,30)
  arr=np.full((ny,nx),-9999,dtype=np.float32)
  reproject(a,arr,src_transform=trans,src_crs=src.crs,src_nodata=src.nodata,dst_transform=dsttrans,dst_crs='EPSG:32649',dst_nodata=-9999,resampling=Resampling.bilinear)
  with rasterio.open(out/'modern-dsm-utm49-30m.tif','w',driver='GTiff',height=ny,width=nx,count=1,dtype='float32',crs='EPSG:32649',transform=dsttrans,nodata=-9999,compress='deflate',predictor=3) as d:d.write(arr,1)
  good=arr!=-9999;v=arr[good]
  receipts['analysis_grid']={'crs':'EPSG:32649','resolution_m':30,'shape':[ny,nx],'bounds':list(rasterio.transform.array_bounds(ny,nx,dsttrans)),'valid_pixels':int(good.sum()),'total_pixels':int(arr.size),'min_m':float(v.min()),'max_m':float(v.max()),'quantiles_m':dict(zip(['1','5','25','50','75','95','99'],map(float,np.percentile(v,[1,5,25,50,75,95,99]))))}
  q=np.clip((arr-np.percentile(v,1))/(np.percentile(v,99)-np.percentile(v,1)),0,1);q[~good]=1
  Image.fromarray((255*(1-q)).astype('uint8')).save(out/'dem-preview.png')
 shutil.copyfile(cache/'ams-ni49-7.jpg',out/'ams-ni49-7.jpg')
 im=Image.open(out/'ams-ni49-7.jpg');receipts['ams_dimensions']=list(im.size);im.thumbnail((1600,1600));im.save(out/'ams-preview.jpg')
 receipts['limitations']=['Copernicus GLO-30 is modern DSM including buildings and vegetation, not bare-earth Northern Wei terrain.','2021 AWS release is not the acquisition date; source acquisition and vertical datum require product documentation.','AMS scanned map is a later cartographic source, not a Northern Wei survey; edition and marginalia must be read before georeferencing.','No prior schematic SVG coordinates are transformed into geographic ancient-site positions.']
 (out/'source-receipt.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2))
 if args.include_repo:
  with zipfile.ZipFile(out/'repository-source.zip','w',zipfile.ZIP_DEFLATED) as z:
   for path in sorted(ROOT.rglob('*')):
    rel=path.relative_to(ROOT)
    if path.is_file() and rel.parts[0] not in {'.git','.cache-terrain','artifacts','_site'}:z.write(path,str(rel))
 print(json.dumps(receipts['analysis_grid'],ensure_ascii=False));print('SOURCE ACQUISITION COMPLETE')
if __name__=='__main__':main()
