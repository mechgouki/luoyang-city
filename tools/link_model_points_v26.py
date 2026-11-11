#!/usr/bin/env python3
"""Link *generated* SVG circles to solver objects; never read the old map."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'_site'
data=json.loads((OUT/'data/milestone-v26.json').read_text())
for plan in data['candidates']:
    tree=ET.parse(OUT/plan['path']);root=tree.getroot()
    circles=root.findall('{http://www.w3.org/2000/svg}circle')
    coords=plan['coordinates']
    ids=sorted([i for i in coords['x'] if i!='ic_palace_avenue'],key=lambda i:(-coords['y'][i],coords['x'][i]))
    assert len(ids)==len(circles)==21
    points=[{'entity_id':i,'x':float(c.attrib['cx']),'y':float(c.attrib['cy'])} for i,c in zip(ids,circles)]
    assert [(p['y'],p['x']) for p in points]==sorted((p['y'],p['x']) for p in points)
    plan['display_points']=points
    plan['svg_view_box']=[float(v) for v in root.attrib['viewBox'].split()]
    plan['display_points_scope']='Generated SVG hit targets only; not historical geometry.'
(OUT/'data/milestone-v26.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(OUT/'models-v26-click.js').write_bytes((ROOT/'models-v26-click.js').read_bytes())
index=(OUT/'index.html').read_text()
assert 'models-v26-click.js' not in index
index=index.replace('</head>','<script defer src="./models-v26-click.js"></script></head>')
(OUT/'index.html').write_text(index)
info=json.loads((OUT/'build-info.json').read_text())
info['files_sha256']={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='build-info.json'}
(OUT/'build-info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
print('v2.6 candidate point links: 13 generated SVGs, 21 object targets each; no old-map input')
