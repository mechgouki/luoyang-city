#!/usr/bin/env python3
"""Finalize both map tracks with source notices and visible release metadata."""
from pathlib import Path
import hashlib,json,re,zipfile
import xml.etree.ElementTree as ET
import rasterio
import dual_batch1 as dual
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'_site'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    dual.main()
    meta=json.loads((OUT/'terrain/v3.0/metadata.json').read_text())
    notice=meta['source_notice']+'\n\n'+meta['liability_notice']
    notice+='\n\nDerived classification: exploratory modern surface morphology only. Not Northern Wei terrain, palaeochannels or building locations.\n'
    (OUT/'dual1/SOURCE-NOTICE.txt').write_text(notice,encoding='utf-8')
    svg_path=OUT/'dual1/terrain-parallel.svg';tree=ET.parse(svg_path);svg=tree.getroot()
    svg.set('viewBox','0 0 1800 1360');svg.find('{'+dual.NS+'}rect').set('height','1360')
    ET.SubElement(svg,'{'+dual.NS+'}desc').text=notice
    lines=[
      'Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018',
      'provided under COPERNICUS by the European Union and ESA; all rights reserved.',
      'The organisations in charge of the Copernicus programme by law or by delegation',
      'do not incur any liability for any use of the Copernicus WorldDEM-30.'
    ]
    for y,line in zip([1270,1292,1314,1336],lines):dual.txt(svg,45,y,line,14,'#68796b')
    svg_path.write_text(ET.tostring(svg,encoding='unicode'),encoding='utf-8')
    with rasterio.open(OUT/'dual1/modern-form-classes.tif','r+') as ds:ds.update_tags(SOURCE_NOTICE=meta['source_notice'],LIABILITY_NOTICE=meta['liability_notice'])
    method_path=OUT/'dual1/terrain-method.json';method=json.loads(method_path.read_text());method['liability_notice']=meta['liability_notice'];method_path.write_text(json.dumps(method,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    changes_path=OUT/'dual1/changes.json';changes=json.loads(changes_path.read_text());changes['terrain']=method;changes_path.write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page=OUT/'dual-map.html';body=page.read_text();needle="svg=$('#canvas svg');home=defaultbox();";assert body.count(needle)==1
    body=body.replace(needle,"svg=$('#canvas svg');if(mode==='terrain')$('#terrain-style').value='interpretation';home=defaultbox();")
    body=body.replace("$('#source-notice').textContent=data.terrain.source_notice;","$('#source-notice').textContent=data.terrain.source_notice+' '+data.terrain.liability_notice;")
    # Hollow SVG groups contain unpainted space. Add a transparent interaction
    # rectangle, not visible geometry, so ordinary clicks need not hit a stroke.
    hit_needle="n.setAttribute('tabindex','0');"
    assert body.count(hit_needle)==1
    hit="const bb=n.getBBox(),hit=document.createElementNS('http://www.w3.org/2000/svg','rect');hit.setAttribute('x',bb.x-8);hit.setAttribute('y',bb.y-8);hit.setAttribute('width',bb.width+16);hit.setAttribute('height',bb.height+16);hit.setAttribute('fill','transparent');hit.setAttribute('stroke','none');hit.setAttribute('pointer-events','all');hit.setAttribute('data-interaction-only','true');n.insertBefore(hit,n.firstChild);"
    body=body.replace(hit_needle,hit+hit_needle)
    page.write_text(body,encoding='utf-8')
    index=OUT/'index.html';text=index.read_text()
    text,n=re.subn(r'当前公开版本 · [^<]+','当前公开版本 · v3.1-alpha.1 / 双图并行第一批',text,count=1);assert n==1
    text=re.sub(r'<title>[^<]+</title>','<title>北魏洛阳 · 双图并行 v3.1 / 文献工作图 v2.10</title>',text,count=1)
    text=text.replace('id="dual-release-entry" class="c29-entry"','id="dual-release-entry" class="dual-entry"')
    style='<style>#dual-release-entry{display:flex;align-items:center;gap:12px 22px;flex-wrap:wrap;background:#edf2e6;border:1px solid #c6d4bd;border-left:4px solid #587c48;padding:16px 20px;margin:0 0 17px;border-radius:7px;color:#264d40}#dual-release-entry span{font-size:12px;color:#64766a}#dual-release-entry a{margin-left:auto;color:#23634c;font-weight:700;font-size:13px}</style>'
    text=text.replace('</head>',style+'</head>',1);index.write_text(text,encoding='utf-8')
    assert '当前公开版本 · v3.1-alpha.1' in text and 'id="dual-release-entry" class="dual-entry"' in text
    readme='''# Parallel maps: first batch

Open downloads/dual1-report.html to read the figures offline.
The workbench fetches JSON and SVG, so serve this directory with a local HTTP
server (for example: python -m http.server 8000) and open /dual-map.html.
The archived-map and modern relief inputs needed by the workbench are included.
Links to older evidence modules require the full live website or a full site copy.

The ten changed symbols are documentary display refinements. No ancient
geographic points have been created. The terrain classification uses actual
modern Copernicus DSM products but is exploratory, not an ancient landform map.
See dual1/SOURCE-NOTICE.txt and dual1/terrain-method.json.
'''
    (OUT/'dual1/README.md').write_text(readme,encoding='utf-8')
    report=OUT/'downloads/dual1-report.html';report.write_text(report.read_text().replace('</html>','<p>'+dual.E(meta['liability_notice'])+'</p></html>'),encoding='utf-8')
    with zipfile.ZipFile(OUT/'downloads/dual1-workpack.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted((OUT/'dual1').iterdir()):
            if f.is_file():z.write(f,'dual1/'+f.name)
        for path in ['dual-map.html','release.json','assets/master-v24.svg','terrain/v3.0/relief.png','downloads/dual1-report.html','downloads/dual1-changes.csv']:z.write(OUT/path,path)
        for path in ['tools/dual_batch1.py','tools/dual_release.py','research/dual1/changes.json','dual1.html','tests/test_dual1.py','tests/browser_dual1.py']:z.write(ROOT/path,'source/'+path)
        z.writestr('README.md',readme)
    build=json.loads((OUT/'build-info.json').read_text());build['files_sha256']={str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='build-info.json'}
    (OUT/'build-info.json').write_text(json.dumps(build,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Parallel maps packaged with synchronized root release, accessible hit areas, source notices and offline report assets.')
if __name__=='__main__':main()
