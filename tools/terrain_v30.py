#!/usr/bin/env python3
"""Process authenticated real DSM bytes; preserve historical geometry and releases.
Build after chronology_v29.py. Nothing here locates an ancient building or channel.
"""
from __future__ import annotations
import argparse, hashlib, html, io, json, math, os, re, shutil, time, urllib.request, zipfile
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds, Resampling
from rasterio.windows import from_bounds, Window
from pyproj import Transformer, Geod
from scipy.ndimage import gaussian_filter, binary_erosion
from PIL import Image
import contourpy
ROOT=Path(__file__).resolve().parents[1]
BBOX=[112.35,34.50,112.95,34.95]
CRS='EPSG:32649'; CELL=30.0; NODATA=-9999.; SIGMA=90.; CONTOUR=25.
RELEASE='v3.0-alpha.1'
SOURCES={
 'cop30.tif':{'url':'https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/Copernicus_DSM_COG_10_N34_00_E112_00_DEM/Copernicus_DSM_COG_10_N34_00_E112_00_DEM.tif','sha256':'60bde4a8534d1b18b8c1bd0a275c8e4f6153d526a14df740f240e0f13ed7dad7'},
 'ams-ni49-7.jpg':{'url':'https://maps.lib.utexas.edu/maps/ams/china/txu-oclc-10552568-ni49-7.jpg','sha256':'005a2b3c81f9135ab03739f2c8f52566c554f7c7af56c6bad5d9b47927970532'},
 'ams-ni49-8.jpg':{'url':'https://maps.lib.utexas.edu/maps/ams/china/txu-oclc-10552568-ni49-8.jpg','sha256':'d3525d1e86cc47536bb978721409e06852a07a3aee7298f69fb94b86cf94917c'}}
NOTICE='produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.'
LIABILITY='The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30.'
PALETTE_LEVELS=[80,120,160,220,320,500,800,1200]
PALETTE_COLORS=[[221,234,226],[216,229,205],[221,224,189],[223,212,168],[207,185,147],[182,152,122],[158,134,119],[230,224,215]]

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def dump(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def acquire(cache):
 cache.mkdir(parents=True,exist_ok=True)
 for name,s in SOURCES.items():
  p=cache/name
  if p.exists() and sha(p)==s['sha256']:continue
  tmp=p.with_suffix(p.suffix+'.part')
  for attempt in range(3):
   try:
    req=urllib.request.Request(s['url'],headers={'User-Agent':'Luoyang-Research-Terrain/3.0'})
    with urllib.request.urlopen(req,timeout=90) as r,tmp.open('wb') as f:
     if r.status!=200:raise ValueError('HTTP '+str(r.status))
     size=0
     while True:
      b=r.read(1048576)
      if not b:break
      size+=len(b)
      if size>100_000_000:raise ValueError('Unexpected input size')
      f.write(b)
    if sha(tmp)!=s['sha256']:raise ValueError('Source hash changed; review required, not silently replaced')
    tmp.replace(p);break
   except Exception:
    tmp.unlink(missing_ok=True)
    if attempt==2:raise
    time.sleep(2*(attempt+1))

def smooth(z,sigma_px):
 good=np.isfinite(z);den=gaussian_filter(good.astype(float),sigma_px)
 num=gaussian_filter(np.where(good,z,0.),sigma_px)
 out=np.divide(num,den,out=np.full(z.shape,np.nan),where=den>.999)
 out[~good]=np.nan;return out

def derivatives(z,spacing=CELL):
 if spacing<=0:raise ValueError('positive spacing required')
 good=np.isfinite(z);g=np.where(good,z,0.).astype(float)
 ds,dx=np.gradient(g,spacing,spacing);north=-ds
 slope=np.degrees(np.arctan(np.hypot(dx,north)))
 norm=np.sqrt(1+dx*dx+north*north);shade=np.zeros(z.shape)
 for az in (225,270,315,360):
  a=math.radians(az);alt=math.radians(45)
  shade+=np.clip((-dx*math.sin(a)*math.cos(alt)-north*math.cos(a)*math.cos(alt)+math.sin(alt))/norm,0,1)/4
 good=binary_erosion(good,structure=np.ones((3,3)),border_value=0)
 slope[~good]=np.nan;shade[~good]=np.nan
 return slope,shade

def tiff(p,z,tr,tags):
 with rasterio.open(p,'w',driver='GTiff',width=z.shape[1],height=z.shape[0],count=1,dtype='float32',crs=CRS,transform=tr,nodata=NODATA,compress='deflate',predictor=3,tiled=True) as ds:
  ds.write(np.where(np.isfinite(z),z,NODATA).astype('float32'),1);ds.update_tags(**{k:str(v) for k,v in tags.items()})
def rgba(arr,valid,path):
 a=np.where(valid,255,0).astype('uint8')
 Image.fromarray(np.dstack([np.clip(arr,0,255).astype('uint8'),a])).save(path)

def process(cache,work,pub):
 for n,s in SOURCES.items():assert sha(cache/n)==s['sha256'],n
 work.mkdir(parents=True,exist_ok=True);pub.mkdir(parents=True,exist_ok=True)
 with rasterio.open(cache/'cop30.tif') as src:
  assert src.crs.to_epsg()==4326 and src.shape==(3600,3600)
  assert src.tags().get('SYNTHETIC_TEST_DATA')!='true'
  assert src.bounds.left<=BBOX[0]<BBOX[2]<=src.bounds.right and src.bounds.bottom<=BBOX[1]<BBOX[3]<=src.bounds.top
  b=transform_bounds(src.crs,CRS,*BBOX,densify_pts=41)
  left,bottom=math.floor(b[0]/CELL)*CELL,math.floor(b[1]/CELL)*CELL
  right,top=math.ceil(b[2]/CELL)*CELL,math.ceil(b[3]/CELL)*CELL
  width,height=round((right-left)/CELL),round((top-bottom)/CELL)
  tr=from_origin(left,top,CELL,CELL);z=np.full((height,width),NODATA,np.float32)
  reproject(rasterio.band(src,1),z,src_transform=src.transform,src_crs=src.crs,dst_transform=tr,dst_crs=CRS,dst_nodata=NODATA,resampling=Resampling.bilinear)
  w=from_bounds(*BBOX,transform=src.transform)
  a0,b0=math.floor(w.col_off),math.floor(w.row_off);a1,b1=math.ceil(w.col_off+w.width),math.ceil(w.row_off+w.height)
  win=Window(a0,b0,a1-a0,b1-b0);native=src.read(1,window=win)
  pro=src.profile.copy();pro.update(driver='GTiff',width=native.shape[1],height=native.shape[0],transform=src.window_transform(win),compress='deflate',predictor=3)
  with rasterio.open(work/'native-samples-wgs84.tif','w',**pro) as dst:dst.write(native,1);dst.update_tags(source_sha256=SOURCES['cop30.tif']['sha256'],historical_terrain='false',AREA_OR_POINT='Point')
  source_meta={'shape':list(src.shape),'crs':str(src.crs),'bounds':list(src.bounds),'spacing_degrees':list(src.res),'tags':src.tags(),'source_release':'AWS Copernicus DEM 2021 release (not acquisition date)','sample_values_changed_in_native_crop':False}
 xs=left+(np.arange(width)+.5)*CELL;ys=top-(np.arange(height)+.5)*CELL
 xx,yy=np.meshgrid(xs,ys);to_ll=Transformer.from_crs(CRS,'EPSG:4326',always_xy=True)
 lon,lat=to_ll.transform(xx,yy)
 mask=(lon>=BBOX[0])&(lon<=BBOX[2])&(lat>=BBOX[1])&(lat<=BBOX[3])&(z!=NODATA)
 z[~mask]=np.nan;sm=smooth(z,SIGMA/CELL)
 slope_raw,_=derivatives(z);slope_display,hill=derivatives(sm)
 tags={'modern_surface_only':'true','ancient_geographic_features_added':0,'horizontal_crs':CRS,'height_reference':'EGM2008 inherited; no vertical transformation','source_sha256':SOURCES['cop30.tif']['sha256'],'cell_m':CELL,'aoi_mask':'WGS84 bounding box applied at projected pixel centres','SYNTHETIC_TEST_DATA':'false'}
 for name,arr,smoothing,units in [('modern-dsm-30m.tif',z,0,'m'),('display-dsm-sigma90m.tif',sm,SIGMA,'m'),('slope-native-scale-deg.tif',slope_raw,0,'degree'),('slope-display-sigma90m-deg.tif',slope_display,SIGMA,'degree'),('hillshade-display.tif',hill,SIGMA,'dimensionless')]:
  tiff(work/name,arr,tr,dict(tags,smoothing_sigma_m=smoothing,units=units))
 val=np.nan_to_num(z,nan=80);colors=np.stack([np.interp(val,PALETTE_LEVELS,np.array(PALETTE_COLORS)[:,i]) for i in range(3)],-1)
 colors*=(.60+.55*np.nan_to_num(hill,nan=.707))[:,:,None]
 rgba(colors,np.isfinite(z),pub/'relief.png')
 gray=np.repeat((np.nan_to_num(hill)*255)[:,:,None],3,axis=2);rgba(gray,np.isfinite(hill),pub/'hillshade.png')
 levels=np.array([0,2,5,10,20,35,90]);scolors=np.array([[233,241,226],[206,226,187],[174,205,151],[218,197,132],[201,151,106],[161,99,77]])
 ix=np.clip(np.searchsorted(levels,np.nan_to_num(slope_display),side='right')-1,0,5)
 rgba(scolors[ix],np.isfinite(slope_display),pub/'slope.png')
 ixraw=np.clip(np.searchsorted(levels,np.nan_to_num(slope_raw),side='right')-1,0,5)
 rgba(scolors[ixraw],np.isfinite(slope_raw),pub/'raw-slope.png')
 gen=contourpy.contour_generator(x=xs,y=ys,z=np.ma.masked_invalid(sm),name='serial')
 features=[];svg_paths=[]
 for h in np.arange(math.ceil(np.nanmin(sm)/CONTOUR)*CONTOUR,np.nanmax(sm),CONTOUR):
  for line in gen.lines(h):
   if len(line)<2:continue
   lo,la=to_ll.transform(line[:,0],line[:,1])
   features.append({'type':'Feature','properties':{'elevation_m':float(h),'surface':'modern DSM','smoothing_sigma_m':SIGMA,'ancient':False},'geometry':{'type':'LineString','coordinates':np.round(np.column_stack([lo,la]),7).tolist()}})
   pix=np.column_stack([(line[:,0]-left)/CELL,(top-line[:,1])/CELL]);svg_paths.append('<path d="M'+' L'.join(f'{x:.1f},{y:.1f}' for x,y in pix)+'"/>')
 dump(work/'contours-25m-wgs84.geojson',{'type':'FeatureCollection','features':features})
 (pub/'contours.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"><title>25m modern DSM display contours, sigma90m; not ancient terrain</title><g fill="none" stroke="#6a593f" opacity=".55" stroke-width=".65">'+''.join(svg_paths)+'</g></svg>',encoding='utf-8')
 stride=6;zg=z[::stride,::stride];rawg=slope_raw[::stride,::stride]
 samples={'step_pixels':stride,'shape':list(zg.shape),'elevation_m':[[None if not np.isfinite(v) else round(float(v),1) for v in row] for row in zg],
 'raw_slope_degrees':[[None if not np.isfinite(v) else round(float(v),1) for v in row] for row in rawg],
 'lonlat':np.round(np.stack([lon[::stride,::stride],lat[::stride,::stride]],axis=-1),6).tolist(),
 'meaning':'Nearest sample on a 180m display readout grid. Full-resolution GIS rasters are separate; not a survey or ancient elevation.'}
 dump(pub/'samples.json',samples)
 valid=z[np.isfinite(z)];geod=Geod(ellps='WGS84');area,_=geod.polygon_area_perimeter([BBOX[0],BBOX[2],BBOX[2],BBOX[0]],[BBOX[1],BBOX[1],BBOX[3],BBOX[3]])
 metadata={'version':RELEASE,'status':'real_modern_dsm_processed','synthetic':False,'analysis_crs':CRS,'bbox_wgs84':BBOX,'bbox_meaning':'analysis window, not ancient city boundary','analysis_grid':[height,width],'analysis_extent_m':[left,bottom,right,top],'cell_m':CELL,'area_geodesic_km2':abs(area)/1e6,'valid_pixels':len(valid),'masked_pixels':int(z.size-len(valid)),
 'elevation_m':{'min':float(valid.min()),'max':float(valid.max()),'median':float(np.median(valid)),'p05':float(np.percentile(valid,5)),'p95':float(np.percentile(valid,95))},
 'raw_slope_deg':{'median':float(np.nanmedian(slope_raw)),'p95':float(np.nanpercentile(slope_raw,95))},
 'display_smoothing_sigma_m':SIGMA,'slope_bins_deg':levels.tolist(),'slope_colors':scolors.tolist(),'elevation_legend_m':PALETTE_LEVELS,'elevation_colors':PALETTE_COLORS,'contour_interval_m':CONTOUR,'contour_features':len(features),'source':source_meta,'sources':SOURCES,
 'vertical_reference':'EGM2008 source heights; no vertical datum transformation','derivative_method':'central differences in metre CRS; slopes from raw and sigma90m surfaces both retained; equal-weight four-azimuth illumination at 45 degrees, vertical exaggeration 1',
 'source_notice':NOTICE,'liability_notice':LIABILITY,'ancient_registered_nodes':0,
 'limitations':['DSM includes vegetation, infrastructure and buildings, not bare earth.','Grid spacing is not horizontal or historical accuracy.','90m Gaussian sigma is display generalisation, not removal of buildings.','No sink filling, inferred palaeochannels, archaeological georeferencing or conversion of old SVG pixels.','Archival maps have reviewed marginalia but are not georeferenced; horizontal datum is unresolved.']}
 to_xy=Transformer.from_crs('EPSG:4326',CRS,always_xy=True)
 seam_x,seam_y=to_xy.transform(np.repeat(112.5,51),np.linspace(BBOX[1],BBOX[3],51))
 metadata['ams_sheet_seam_pixels']=np.column_stack([(seam_x-left)/CELL,(top-seam_y)/CELL]).round(3).tolist()
 dump(pub/'metadata.json',metadata);dump(work/'metadata.json',metadata)
 (work/'SOURCE-NOTICE.txt').write_text(NOTICE+'\n'+LIABILITY+'\n'+json.dumps(SOURCES,indent=2)+'\nAMS sources: US Army Map Service, UT Austin Libraries; no ancient channel registration.\n',encoding='utf-8')
 archive=[]
 for num,name,title,bbox,printing in [('7','ams-ni49-7.jpg','LO-YANG / 洛陽',[111,34,112.5,35],'1964-11'),('8','ams-ni49-8.jpg','CHENG-HSIEN / 鄭縣',[112.5,34,114,35],'1964-09')]:
  im=Image.open(cache/name);im.verify();im=Image.open(cache/name)
  p=pub/name;shutil.copyfile(cache/name,p)
  thumb=im.copy();thumb.thumbnail((1500,1500));thumb.save(pub/f'ams-{num}-preview.jpg',quality=88)
  im.crop((240,im.height-490,1220,im.height-40)).save(pub/f'ams-{num}-imprint.jpg')
  archive.append({'sheet':'NI49-'+num,'title':title,'scale':250000,'edition':'Edition 1-AMS / series L500','compiled_year':1955,'printing':printing,'compilation_note':'Compiled from earlier mapping including 1945 AMS and Japanese 1:100,000 sheets 1942–44; not a single-date survey.','nominal_graticule_bbox':bbox,'grid_projection':'Transverse Mercator; blue 10000m UTM grid on International Spheroid','contours_on_source_m':[100,50],'horizontal_datum':'not identified on reviewed margin; WGS84 equivalence not established','georeferenced':False,'raw_image':name,'preview_image':f'ams-{num}-preview.jpg','imprint_image':f'ams-{num}-imprint.jpg','review_method':'visual reading of actual full-resolution image and its margins, no OCR'})
 dump(pub/'archival-review.json',archive)
 im=Image.open(pub/'relief.png');im.thumbnail((1000,1000));im.save(pub/'preview.png')
 return metadata,archive

def publish(out,cache):
 info=load(out/'build-info.json');assert info.get('chronology_version')=='v2.9'
 immutable={str(p.relative_to(out)):sha(p) for p in (out/'data').glob('*.json')}
 immutable.update({p:sha(out/p) for p in ['assets/master-v24.svg','assets/master-v28-review.svg','downloads/luoyang-v24-regional-atlas.pdf','v2.8.html','v2.9.html']})
 pub=out/'terrain/v3.0';work=ROOT/'artifacts/terrain-products-v30'
 meta,archive=process(cache,work,pub)
 net=load(out/'data/network-v27.json')
 skeleton={'basis':'v2.7 textual network','nodes':net['nodes'],'edges':net['edges'],'passages':net['passages'],'sources':net['sources'],'historical_registered_nodes':0,'geometry':None}
 dump(pub/'historical-skeleton.json',skeleton)
 if len(skeleton['nodes'])!=48:raise ValueError('Historical network baseline changed')
 with zipfile.ZipFile(out/'downloads/luoyang-terrain-v30-gis.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(work.iterdir()):
   if p.is_file():z.write(p,p.name)
  for p in ['archival-review.json','historical-skeleton.json']:z.write(pub/p,p)
 template=(ROOT/'web/terrain-v30.html').read_text(encoding='utf-8')
 metadata=dict(meta,archive=archive,source_commit=info['source_commit'],network_counts={'nodes':len(net['nodes']),'edges':len(net['edges']),'passages':len(net['passages'])})
 page=template.replace('__TERRAIN_METADATA__',json.dumps(metadata,ensure_ascii=False).replace('</','<\\/'))
 (out/'v3.0.html').write_text(page,encoding='utf-8')
 (out/'downloads/terrain-method-v30.html').write_text('<!doctype html><meta charset="utf-8"><title>真实地形处理报告 v3.0</title><style>body{max-width:1100px;margin:40px auto;font:16px/1.8 sans-serif;padding:20px}pre{white-space:pre-wrap;word-break:break-word}</style><h1>真实地形基底 · v3.0 第一批</h1><p>现代地表、近现代地图与古代文字骨架分层；未给北魏城、水、桥、寺确定真实坐标。</p><p><a href="../v3.0.html">交互地形图</a> · <a href="luoyang-terrain-v30-gis.zip">完整GIS包</a></p><pre>'+html.escape(json.dumps(metadata,ensure_ascii=False,indent=2))+'</pre>',encoding='utf-8')
 release=dict(load(out/'release.json'),release=RELEASE,web_version='0.7.0',entrypoint='v3.0.html',description='真实现代地形第一批：投影DSM、山影、坡度、等高线；古代几何未配准')
 dump(out/'release.json',release)
 index=(out/'index.html').read_text(encoding='utf-8')
 runtime=re.search(r'<script src="\./([^\"]+-runtime\.js)"></script>',index);assert runtime
 boot=(out/runtime.group(1)).read_text(encoding='utf-8');boot=re.sub(r'window\.ATLAS_RELEASE=.*?;\n','window.ATLAS_RELEASE='+json.dumps(release,ensure_ascii=False)+';\n',boot,count=1)
 name='_assets/'+hashlib.sha256(boot.encode()).hexdigest()[:20]+'-runtime.js';(out/name).write_text(boot,encoding='utf-8');index=index.replace(runtime.group(1),name,1)
 index=index.replace('<span class="brand-release">v2.9</span>',f'<span class="brand-release">{RELEASE}</span>')
 index=index.replace('当前公开版本 · v2.9 / 同址时层对照','当前公开版本 · v3.0 第一批 / 真实地形基底')
 index=index.replace('<nav aria-label="主导航" class="topnav">','<nav aria-label="主导航" class="topnav"><a href="./v3.0.html">真实地形 v3.0 ↗</a>',1)
 card='<section id="terrain-release-entry" style="display:flex;gap:20px;align-items:center;flex-wrap:wrap;background:#edf2e8;border:1px solid #bfcfbc;padding:18px;margin:15px 0;border-radius:8px"><a href="./v3.0.html"><img src="./terrain/v3.0/preview.png" alt="已由真实Copernicus高程生成的洛阳地形底图" style="width:220px;max-width:100%;height:130px;object-fit:cover"></a><div><h2>现在可以查看真实地形，而不只是文献示意图</h2><p>现代地表 · 30米投影网格 · 山影 / 坡度 / 25米等高线 · 两幅历史地图原件</p><p>这不是北魏地表实测；古代河道与建筑仍需定位核查。</p><a href="./v3.0.html"><strong>打开 v3.0 真实地形图 ↗</strong></a></div></section>'
 index=index.replace('<div class="v28-summary">',card+'<div class="v28-summary">',1)
 (out/'index.html').write_text(index,encoding='utf-8')
 for p,h in immutable.items():assert sha(out/p)==h,p
 info.update(portal_version=RELEASE,web_version='0.7.0',terrain_version=RELEASE,terrain_counts={'pixels':meta['valid_pixels'],'contours':meta['contour_features'],'archival_maps':2,'ancient_georeferenced':0},terrain_source_sha256=SOURCES['cop30.tif']['sha256'])
 info['files_sha256']={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='build-info.json'}
 dump(out/'build-info.json',info)
 print(json.dumps({'version':RELEASE,'grid':meta['analysis_grid'],'elevation':meta['elevation_m'],'contours':meta['contour_features'],'old_data_unchanged':True},ensure_ascii=False))

def main():
 p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,default=ROOT/'.cache-terrain-v30');p.add_argument('--output',type=Path,default=ROOT/'_site');p.add_argument('--no-download',action='store_true');args=p.parse_args()
 if not args.no_download:acquire(args.input_dir)
 publish(args.output,args.input_dir)
if __name__=='__main__':main()
