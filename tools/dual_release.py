#!/usr/bin/env python3
"""Finalize the parallel-map release, including mandatory source attribution.

The primary research generator remains independently testable. This packaging
step adds notices, preserves archives, and includes all workbench image inputs.
"""
from pathlib import Path
import hashlib
import json
import re
import zipfile
import xml.etree.ElementTree as ET
import rasterio
import dual_batch1 as dual

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'_site'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    dual.main()
    meta=json.loads((OUT/'terrain/v3.0/metadata.json').read_text())
    notice=meta['source_notice']+'\n\n'+meta['liability_notice']
    notice+='\n\nDerived classification: exploratory modern surface morphology only. Not Northern Wei terrain, palaeochannels or building locations.\n'
    (OUT/'dual1/SOURCE-NOTICE.txt').write_text(notice,encoding='utf-8')
    svg_path=OUT/'dual1/terrain-parallel.svg'
    tree=ET.parse(svg_path);svg=tree.getroot()
    svg.set('viewBox','0 0 1800 1360')
    svg.find('{'+dual.NS+'}rect').set('height','1360')
    description=ET.SubElement(svg,'{'+dual.NS+'}desc');description.text=notice
    copyright_lines=[
      'Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018',
      'provided under COPERNICUS by the European Union and ESA; all rights reserved.',
      'The organisations in charge of the Copernicus programme by law or by delegation',
      'do not incur any liability for any use of the Copernicus WorldDEM-30.'
    ]
    for y,line in zip([1270,1292,1314,1336],copyright_lines):
        dual.txt(svg,45,y,line,14,'#68796b')
    svg_path.write_text(ET.tostring(svg,encoding='unicode'),encoding='utf-8')
    with rasterio.open(OUT/'dual1/modern-form-classes.tif','r+') as ds:
        ds.update_tags(SOURCE_NOTICE=meta['source_notice'],LIABILITY_NOTICE=meta['liability_notice'])
    method_path=OUT/'dual1/terrain-method.json'
    method=json.loads(method_path.read_text());method['liability_notice']=meta['liability_notice']
    method_path.write_text(json.dumps(method,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    changes_path=OUT/'dual1/changes.json'
    changes=json.loads(changes_path.read_text());changes['terrain']=method
    changes_path.write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page=OUT/'dual-map.html';body=page.read_text()
    # Every newly rendered terrain view starts with classification; keep its
    # selector synchronized after changing regions or returning from a document.
    needle="svg=$('#canvas svg');home=defaultbox();"
    assert body.count(needle)==1
    body=body.replace(needle,"svg=$('#canvas svg');if(mode==='terrain')$('#terrain-style').value='interpretation';home=defaultbox();")
    body=body.replace("$('#source-notice').textContent=data.terrain.source_notice;","$('#source-notice').textContent=data.terrain.source_notice+' '+data.terrain.liability_notice;")
    page.write_text(body,encoding='utf-8')
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
    report=OUT/'downloads/dual1-report.html'
    report.write_text(report.read_text().replace('</html>','<p>'+dual.E(meta['liability_notice'])+'</p></html>'),encoding='utf-8')
    with zipfile.ZipFile(OUT/'downloads/dual1-workpack.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted((OUT/'dual1').iterdir()):
            if f.is_file():z.write(f,'dual1/'+f.name)
        for path in ['dual-map.html','release.json','assets/master-v24.svg','terrain/v3.0/relief.png','downloads/dual1-report.html','downloads/dual1-changes.csv']:
            z.write(OUT/path,path)
        for path in ['tools/dual_batch1.py','tools/dual_release.py','research/dual1/changes.json','dual1.html','tests/test_dual1.py','tests/browser_dual1.py']:
            z.write(ROOT/path,'source/'+path)
        z.writestr('README.md',readme)
    build=json.loads((OUT/'build-info.json').read_text())
    build['files_sha256']={str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='build-info.json'}
    (OUT/'build-info.json').write_text(json.dumps(build,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Parallel maps packaged with full Copernicus notices and offline report assets.')

if __name__=='__main__':main()
