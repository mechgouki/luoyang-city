#!/usr/bin/env python3
"""Verify a narrowly authorized immutable-blob batch; no remote mutations."""
import argparse
import json
import tarfile
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from prepare_archive import ident, scan, safe_rel, terrain_hashes, verify_wrapper, dump


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--archive', type=Path, required=True)
    ap.add_argument('--batch', required=True)
    ap.add_argument('--authorization', type=Path, required=True)
    args = ap.parse_args()
    root, source = args.archive, args.archive / 'incoming'
    auth = json.loads(args.authorization.read_text())
    assert auth['immutable_blobs_authorized'] and not auth['tree_commit_ref_authorized']
    prefixes, exact = auth['prefixes'], set(auth.get('exact_paths', []))
    def selected(path):
        return path in exact or any(path.startswith(prefix) for prefix in prefixes)
    collections = json.loads((root / 'config/collections.json').read_text())['collections']
    wrappers = [verify_wrapper(source, row) for row in collections if selected(row['path'])]
    wrapper_by_path = {row['path']: row for row in wrappers}
    deployment_tars = {}
    for item in collections:
        if not selected(item['path']) or item.get('artifact_name') != 'github-pages':
            continue
        stage = source / item['stage']
        tar_path = stage / 'pages-artifact/artifact.tar'
        actual = ident(tar_path)
        extraction = json.loads((stage / 'github-pages-extraction.json').read_text())
        member = extraction['files'][0]
        assert len(extraction['files']) == 1 and member['path'] == 'artifact.tar'
        assert actual['bytes'] == member['bytes'] and actual['sha256'] == member['sha256']
        public = stage / ('root-public/public' if item['stage'].startswith('production-') else 'publication')
        assert public.is_dir()
        rows = []
        with tarfile.open(tar_path, 'r') as archive:
            members = {}
            for member in archive.getmembers():
                path = member.name.removeprefix('./').rstrip('/')
                if not path:
                    continue
                safe_rel(path)
                assert not member.issym() and not member.islnk()
                if member.isfile():
                    assert path not in members
                    members[path] = member
            for local in sorted(public.rglob('*')):
                if not local.is_file():
                    continue
                path = local.relative_to(public).as_posix()
                raw = archive.extractfile(members[path]).read()
                assert raw == local.read_bytes(), (path, 'Published bytes differ from deployment tar')
                rows.append({'publication_path': path, 'retained_path': local.relative_to(source).as_posix(), **ident(local)})
        tar_relative = tar_path.relative_to(source).as_posix()
        proof = {'schema': 'luoyang-r11-deployment-tar-scope-v1', 'path': tar_relative, **actual,
                 'run_id': item['run_id'], 'artifact_id': item['artifact_id'],
                 'verified_actions_zip': item['path'], 'deployment_tar_file_member_count': len(members),
                 'retained_publication_files_verified': rows, 'retained_publication_file_count': len(rows),
                 'raw_tar_retained_locally': True, 'accepted_final_release': False,
                 'permanent_scope': 'Per the established R10 policy, the deployment tar is metadata only; actual R11 publication bytes and actual browser downloads are retained. This does not claim all older site assets are archived anew.'}
        dump(stage / 'deployment-tar-verification.json', proof)
        deployment_tars[tar_relative] = proof
    baseline = terrain_hashes(root / 'r10-reference/archive-scope.json')
    forbidden = {row['sha256'] for row in json.loads((root / 'config/forbidden-source-content.json').read_text())['forbidden_content']}
    files, excluded, findings = [], [], []
    scanned = 0
    for path in sorted(source.rglob('*')):
        if not path.is_file() and not path.is_symlink():
            continue
        relative = path.relative_to(source).as_posix()
        if not selected(relative):
            continue
        assert not path.is_symlink()
        safe_rel(relative)
        row = {'path': relative, **ident(path)}
        reason = None
        if row['sha256'] in forbidden:
            reason = 'third_party_source_or_source_backed_overlay'
        elif relative in wrapper_by_path:
            reason = 'verified_actions_outer_zip_all_members_accounted'
        elif relative in deployment_tars:
            reason = 'deployment_tar_metadata_and_actual_publication_bytes_verified'
        elif 'terrain-products-v30' in path.parts and path.name in baseline and row['sha256'] == baseline[path.name]:
            reason = 'unchanged_terrain_intermediate_matches_prior_permanent_sha256'
        if reason:
            excluded.append({**row, 'reason_code': reason})
            continue
        raw = path.read_bytes()
        scanned += scan(raw, relative, findings)
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                for member in archive.infolist():
                    if not member.is_dir():
                        scanned += scan(archive.read(member), relative + '!' + member.filename, findings)
        files.append(row)
    retained = {row['path'] for row in files}
    excluded_by_path = {row['path']: row for row in excluded}
    for wrapper in wrappers:
        for member in wrapper['members']:
            member['retained_separately'] = member['path'] in retained
            if not member['retained_separately']:
                member['omission_reason'] = excluded_by_path[member['path']]['reason_code']
    manifest = {'schema': 'luoyang-r11-authorized-preupload-manifest-v1',
                'authorization_scope': auth, 'production_workflow_accepted': False,
                'accepted_final_release': False, 'payload_root': str(source), 'source_root': str(source),
                'files': files, 'file_count': len(files), 'total_bytes': sum(row['bytes'] for row in files),
                'unique_blob_count': len({row['gitblob'] for row in files}),
                'remote_tree_commit_ref_writes_authorized': False}
    scope = {'schema': 'luoyang-r11-authorized-preupload-scope-v1',
             'prepared_utc': datetime.now(timezone.utc).isoformat(), 'authorization': auth,
             'included_file_count': len(files), 'excluded_but_raw_locally_retained': excluded,
             'verified_wrappers_and_member_disposition': wrappers,
             'verified_deployment_tar_count': len(deployment_tars),
             'scanned_text_file_or_zip_member_count': scanned,
             'sensitive_findings_filenames_rules_only': findings,
             'tree_commit_ref_writes': 0, 'accepted_final_release': False}
    dump(root / f'config/{args.batch}-scope.json', scope)
    assert not findings, 'Sensitive findings require review; no upload plan accepted'
    dump(root / f'config/{args.batch}-manifest.json', manifest)
    print(json.dumps({'batch': args.batch, 'files': len(files), 'unique_blobs': manifest['unique_blob_count'],
                      'logical_bytes': manifest['total_bytes'], 'excluded': len(excluded),
                      'verified_wrappers': len(wrappers), 'sensitive_findings': len(findings)}))


if __name__ == '__main__':
    main()
