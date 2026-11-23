#!/usr/bin/env python3
"""Reconcile already-downloaded PR evidence. No remote writes or downloads."""
import argparse
import hashlib
import json
import re
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'gitblob': hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def unwrap(data):
    if 'data' in data:
        return data['data']
    if 'structuredContent' in data:
        value = data['structuredContent']
        return json.loads(value['content']) if 'content' in value else value
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--stage', required=True)
    parser.add_argument('--pr', type=int, required=True)
    parser.add_argument('--run', type=int, required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--expected-merge', required=True)
    parser.add_argument('--expected-tree', required=True)
    args = parser.parse_args()
    stage = args.archive / 'incoming' / args.stage
    run = unwrap(json.loads(sorted((stage / 'watch-api').glob('*-run.json'))[-1].read_text()))
    jobs = unwrap(json.loads(sorted((stage / 'watch-api').glob('*-jobs.json'))[-1].read_text()))['jobs']
    commit = unwrap(json.loads((stage / 'tested-merge-commit.json').read_text()))
    artifacts = unwrap(json.loads((stage / 'api-artifacts-full-raw.json').read_text()))['artifacts']
    assert run['id'] == args.run and run['head_sha'] == args.expected_head
    assert run['status'] == 'completed' and run['conclusion'] == 'success'
    assert commit['sha'] == args.expected_merge and commit['tree']['sha'] == args.expected_tree
    build = next(job for job in jobs if job['name'] == 'build')
    assert build['conclusion'] == 'success'
    log = stage / f'build-{build["id"]}.log'
    log_text = log.read_text(encoding='utf-8-sig')
    assert args.expected_merge in log_text
    assert re.search(r'git log -1 --format=%H[\s\S]{0,200}' + args.expected_merge, log_text), 'Actual checkout missing'
    write(stage / 'api-run-final.json', run)
    write(stage / 'api-jobs-final.json', {'jobs': jobs})
    write(stage / 'api-artifacts-final.json', {'artifacts': artifacts})
    tar_path = stage / 'pages-artifact/artifact.tar'
    rows = []
    with tarfile.open(tar_path, 'r') as archive:
        members = {}
        for member in archive.getmembers():
            path = member.name.removeprefix('./').rstrip('/')
            if not path:
                continue
            rel = PurePosixPath(path)
            assert not rel.is_absolute() and '..' not in rel.parts and '\\' not in path
            assert not member.issym() and not member.islnk(), (path, 'Tar links forbidden')
            if member.isfile():
                assert path not in members
                members[path] = member
        info = json.loads(archive.extractfile(members['build-info.json']).read())
        r11 = info['city_plan_r11']
        assert info['source_commit'] == args.expected_merge == r11['source_commit']
        selected = {'build-info.json', r11['manifest'], r11['pdf'], r11['bundle']} | set(r11['files_sha256'])
        for path in sorted(selected):
            raw = archive.extractfile(members[path]).read()
            actual = identity(raw)
            if path in r11['files_sha256']:
                assert actual['sha256'] == r11['files_sha256'][path], path
            target = stage / 'publication' / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                assert target.read_bytes() == raw
            else:
                target.write_bytes(raw)
            rows.append({'path': path, 'tar_member': members[path].name, **actual})
    pages = next(item for item in artifacts if item['name'] == 'github-pages')
    write(stage / 'publication-extraction.json', {
        'schema': 'luoyang-r11-pages-publication-extraction-v1', 'run_id': args.run,
        'source_commit': args.expected_merge, 'accepted_production': False,
        'artifact_id': pages['id'], 'artifact_zip_sha256': pages['digest'].split(':')[1],
        'tar_bytes': tar_path.stat().st_size, 'tar_sha256': identity(tar_path.read_bytes())['sha256'],
        'selection': 'All R11 files declared in actual Pages build-info, PDF and bundle, plus build-info itself; complete deployment tar remains retained locally.',
        'files': rows, 'file_count': len(rows)})
    selected_rows = {row['path']: row for row in rows}
    browser = stage / 'artifacts/city-plan-r11-browser'
    actual_files, devices = [], {}
    for device in ('desktop', 'mobile'):
        report = json.loads((browser / f'{device}-report.json').read_text())
        assert report['status'] == 'passed' and not report['errors']
        assert report['source_commit'] == args.expected_merge
        assert set(report['downloads']) == set(r11['download_files'])
        for path, expected in report['retained_downloads'].items():
            actual = identity((browser / expected['retained_path']).read_bytes())
            assert actual['bytes'] == expected['bytes']
            assert actual['sha256'] == expected['sha256'] == report['downloads'][path] == selected_rows[path]['sha256']
            actual_files.append({'kind': 'actual_download', 'device': device, 'path': path, **actual})
        for path, expected in report['screenshots'].items():
            actual = identity((browser / path).read_bytes())
            assert actual['sha256'] == expected
            actual_files.append({'kind': 'actual_screenshot', 'device': device, 'path': path, **actual})
        assert report['tower_hit_test']['selected_point']['hit_feature'] == 'r11-yongning-YN11-TOWER-PLINTH'
        assert report['tower_hit_test']['selected_point']['hit_tag'] == 'path'
        assert report['tower_hit_test']['independent_label']['hit_label'] == 'geo-yongning-pagoda-reference'
        devices[device] = {key: report[key] for key in ('status', 'elapsed_seconds', 'tower_hit_test')}
        devices[device].update({'completed_check_groups': len(report['checks']),
                               'download_count': len(report['downloads']), 'screenshot_count': len(report['screenshots'])})
    write(stage / 'browser-byte-check.json', {
        'schema': 'luoyang-r11-pr-browser-byte-check-v1', 'run_id': args.run,
        'source_commit': args.expected_merge, 'source_tree': args.expected_tree,
        'accepted_production': False, 'devices': devices, 'retained_files_actually_hashed': actual_files,
        'all_available_file_bytes_match_reports_and_actual_pages_artifact': True,
        'limit': 'Successful PR evidence only. A later production commit requires independent deployment/live acceptance.'})
    collections_path = args.archive / 'config/collections.json'
    collections = json.loads(collections_path.read_text())
    for item in artifacts:
        is_pages = item['name'] == 'github-pages'
        report_name = 'github-pages-extraction.json' if is_pages else 'evidence-extraction.json'
        extraction = json.loads((stage / report_name).read_text())
        assert extraction['status'] == 'passed' and not extraction['errors']
        assert extraction['artifact_bytes'] == item['size_in_bytes']
        assert extraction['artifact_sha256'] == item['digest'].split(':')[1]
        row = {'stage': args.stage, 'run_id': args.run, 'status': 'success', 'accepted_release': False,
               'accepted_pr': True, 'path': f'{args.stage}/' + ('github-pages.zip' if is_pages else 'evidence.zip'),
               'extracted': f'{args.stage}/' + ('pages-artifact' if is_pages else 'artifacts'),
               'artifact_id': item['id'], 'artifact_name': item['name'], 'digest': item['digest'],
               'member_count': extraction['file_count'], 'extracted_bytes': extraction['extracted_bytes'],
               'expires_at': item['expires_at'], 'collection_report': f'{args.stage}/collection-report.json'}
        existing = [entry for entry in collections['collections'] if entry['artifact_id'] == row['artifact_id']]
        assert not existing or existing == [row]
        if not existing:
            collections['collections'].append(row)
    write(collections_path, collections)
    summary = {'schema': 'luoyang-r11-successful-pr-collection-v1',
               'collected_utc': datetime.now(timezone.utc).isoformat(), 'repository': 'mechgouki/luoyang-city',
               'pr_number': args.pr, 'run_id': args.run, 'run_attempt': run['run_attempt'],
               'run_status': run['status'], 'run_conclusion': run['conclusion'],
               'accepted_pr': True, 'accepted_production': False,
               'pr_head_sha': args.expected_head, 'tested_merge_sha': args.expected_merge,
               'tested_tree_sha': args.expected_tree, 'tested_merge_parents': [p['sha'] for p in commit['parents']],
               'all_jobs': [{k: job[k] for k in ('id', 'name', 'status', 'conclusion')} for job in jobs],
               'complete_build_log': {'path': log.name, **identity(log.read_bytes())},
               'r11_browser_devices': devices,
               'actual_download_files_hashed': sum(r['kind'] == 'actual_download' for r in actual_files),
               'actual_screenshots_hashed': sum(r['kind'] == 'actual_screenshot' for r in actual_files),
               'publication_files_extracted': len(rows), 'raw_artifact_count': len(artifacts),
               'complete_artifact_members_verified': sum(json.loads((stage / n).read_text())['file_count'] for n in ('github-pages-extraction.json', 'evidence-extraction.json')),
               'production_workflow_accepted': False,
               'limit': 'PR build passes. Deploy/live jobs are intentionally skipped for pull requests; this does not accept production.'}
    write(stage / 'collection-report.json', summary)
    print(json.dumps({k: summary[k] for k in ('pr_number', 'run_id', 'tested_merge_sha', 'tested_tree_sha', 'actual_download_files_hashed', 'actual_screenshots_hashed', 'publication_files_extracted')}))


if __name__ == '__main__':
    main()
