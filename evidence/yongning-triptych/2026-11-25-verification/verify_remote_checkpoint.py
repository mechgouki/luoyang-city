"""Verify a fetched checkpoint against a frozen path/byte manifest.

Fetch into an independent bare object database before invoking this script.
It verifies commit ancestry, whole-tree scope, paths, modes, blob identity,
byte count and SHA-256; no network access or mutations happen in this script.
"""
import argparse
from datetime import datetime,timezone
import hashlib,json,subprocess
from pathlib import Path

ap=argparse.ArgumentParser()
ap.add_argument('--git-dir',type=Path,required=True)
ap.add_argument('--manifest',type=Path,required=True)
ap.add_argument('--out',type=Path,required=True)
args=ap.parse_args()
frozen=json.loads(args.manifest.read_text())
def git(*params):
 return subprocess.check_output(['git','--git-dir',str(args.git_dir),*params])
def tree(ref):
 result={}
 for raw in git('ls-tree','-r','-z',ref).split(b'\0'):
  if not raw: continue
  meta,path=raw.split(b'\t',1)
  mode,kind,sha=meta.decode().split()
  result[path.decode()]={'mode':mode,'type':kind,'sha':sha}
 return result

commit=frozen['commit'];base=frozen['base_commit']
assert git('rev-parse','refs/verify/checkpoint').decode().strip()==commit
raw_commit=git('cat-file','-p',commit).decode()
parents=[x.split()[1] for x in raw_commit.splitlines() if x.startswith('parent ')]
assert parents==[base],parents
actual_tree=git('rev-parse',commit+'^{tree}').decode().strip()
assert actual_tree==frozen['tree']
old,new=tree(base),tree(commit)
changes={p for p in old.keys()|new.keys() if old.get(p)!=new.get(p)}
expected={row['path']:row for row in frozen['files']}
assert changes==set(expected),{'unexpected':sorted(changes-set(expected)),'missing':sorted(set(expected)-changes)}
assert all(p not in old for p in changes),'Archive overwrote an existing path'
verified={};rows=[]
for path,row in sorted(expected.items()):
 entry=new[path]
 assert entry=={key:row[key] for key in ['mode','type','sha']},path
 sha=entry['sha']
 if sha not in verified:
  raw=git('cat-file','blob',sha)
  assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==sha
  verified[sha]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 actual=verified[sha]
 assert actual=={key:row[key] for key in ['bytes','sha256']},path
 rows.append({'path':path,'mode':entry['mode'],'git_blob_sha':sha,**actual})
report=dict(schema='luoyang-yongning-independent-remote-readback-v1',status='passed',
 verified_at=datetime.now(timezone.utc).isoformat(),commit=commit,base_commit=base,tree=actual_tree,
 expected_manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
 independent_object_database=str(args.git_dir),scope='Objects fetched from the published checkpoint branch into this independently initialized bare database',
 sole_parent_verified=True,all_changed_paths_are_additions=True,paths_outside_frozen_prefixes_changed=0,
 verified_files=len(rows),unique_blobs_read=len(verified),total_file_bytes=sum(x['bytes'] for x in rows),
 unique_blob_bytes=sum(x['bytes'] for x in verified.values()),files=rows,
 production_deployment_rerun=False,image_acceptance_not_asserted=True)
args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','commit','tree','verified_files','unique_blobs_read','total_file_bytes','verified_at']}))
