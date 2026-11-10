#!/usr/bin/env python3
"""Validate Luoyang Atlas static website data and local link assets."""
from pathlib import Path
import json, re, sys, xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1]
errors=[]
def data(name):
 p=root/'data'/name
 try:return json.loads(p.read_text(encoding='utf-8'))
 except Exception as exc:errors.append(f'{name}: {exc}');return []
e=data('entities.json');r=data('regions.json');s=data('sheets.json');d=data('disputes.json');m=data('markers.json');manifest=data('manifest.json')
assert isinstance(e,list) and isinstance(r,list) and isinstance(s,list) and isinstance(d,list) and isinstance(m,list)
if len(e)!=339:errors.append(f'entities count {len(e)} !=339')
if len(r)!=11:errors.append(f'regions count {len(r)} !=11')
if len(s)!=37:errors.append(f'sheets count {len(s)} !=37')
if len(d)!=30:errors.append(f'disputes count {len(d)} !=30')
ids=[p.get('id') for p in e]
if len(set(ids))!=len(ids):errors.append('duplicate entity ids')
for x in m:
 if any(z not in ids for z in x.get('ids',[])):errors.append('marker has unknown entity id')
for x in s:
 for k in ('svg','thumbnail'):
  if not (root/x[k]).is_file():errors.append(f'missing {x[k]}')
for path in ('index.html','styles.css','app.js','assets/master-v24.svg','downloads/luoyang-v24-regional-atlas.pdf'):
 if not (root/path).is_file():errors.append(f'missing {path}')
try:
 tree=ET.parse(root/'assets/master-v24.svg');
 if tree.getroot().tag.split('}')[-1]!='svg':errors.append('master asset is not SVG')
except Exception as exc:errors.append(f'master SVG: {exc}')
if manifest.get('canonical_records')!=len(e):errors.append('manifest count mismatch')
if errors:
 print('\n'.join('ERROR: '+x for x in errors),file=sys.stderr)
 sys.exit(1)
print(f'OK: {len(e)} entities; {len(m)} map targets; {len(d)} disputes; {len(r)} regions; {len(s)} sheets')
