#!/usr/bin/env python3
"""Inspect retained original browser reports; do not run a browser or modify CAS."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--store', type=Path, required=True)
p.add_argument('--baseline', type=Path, required=True)
p.add_argument('--evidence', type=Path, required=True)
p.add_argument('--jobs', type=Path, required=True)
p.add_argument('--phase', choices=['build', 'live'], required=True)
p.add_argument('--expected-commit', required=True)
p.add_argument('--mapping', type=Path)
a = p.parse_args()
baseline = json.loads(a.baseline.read_text())
evidence = json.loads(a.evidence.read_text())
jobs = json.loads(a.jobs.read_text())

def is_report(path):
    return path.endswith(('-report.json', '/report.json', '/results.json'))

mapping = None
if a.phase == 'live':
    if not a.mapping:
        raise ValueError('Live phase requires explicit source-backed output mapping')
    mapping = json.loads(a.mapping.read_text())
    assert mapping['source_commit'] == a.expected_commit
    assert mapping['directory_overrides'] == {
        'prosperity-city-common-p470-browser': 'live-city-common-p470-browser',
        'prosperity-city-north-p471-browser': 'live-city-north-p471-browser'}
    for proof in [mapping['workflow_source'], mapping['build_job_log'], mapping['live_job_log']] + [x['source'] for x in mapping['alias_source_proof']]:
        raw = Path(proof['path']).read_bytes()
        assert len(raw) == proof['bytes'] and hashlib.sha256(raw).hexdigest() == proof['sha256']
    originals = {m['path'] for m in baseline['members'] if is_report(m['path'])}
    assert set(mapping['report_path_mapping']) == originals
    expected = set(mapping['report_path_mapping'].values())
    assert {x.split('/')[0] for x in expected} == set(mapping['actual_live_output_directories'])
else:
    expected = {m['path'] for m in baseline['members'] if is_report(m['path'])}

members = {m['path']: m for m in evidence['members'] if is_report(m['path'])}
issues = []
if set(members) != expected:
    issues.append({'missing_reports': sorted(expected - set(members)),
                   'unexpected_reports': sorted(set(members) - expected)})
job_name = 'build' if a.phase == 'build' else 'verify-live'
matching = [j for j in jobs['jobs'] if j['name'] == job_name]
if len(matching) != 1 or matching[0]['conclusion'] != 'success':
    issues.append({'job_not_success': job_name})
step_name = ('Exercise current and all earlier map interactions' if a.phase == 'build'
             else 'Exercise current and all earlier deployed map versions')
steps = [s for j in matching for s in j['steps'] if s['name'] == step_name]
if len(steps) != 1 or steps[0]['conclusion'] != 'success':
    issues.append({'browser_step_not_success': step_name})

def inspect(node, label):
    found = []
    if node.get('status') is not None and node['status'] != 'passed':
        found.append({'node': label, 'status': node['status']})
    for key in ('errors', 'runtime_errors'):
        if key in node and node[key] != []:
            found.append({'node': label, key: node[key]})
    for key in ('source_commit', 'expected_commit'):
        if node.get(key) and node[key] != a.expected_commit:
            found.append({'node': label, key: node[key]})
    if 'checks' in node:
        checks = node['checks']
        if not isinstance(checks, list) or not checks:
            found.append({'node': label, 'invalid_checks': True})
        else:
            for number, check in enumerate(checks):
                if isinstance(check, dict):
                    if check.get('status') != 'passed':
                        found.append({'node': label, 'check': number, 'value': check})
                elif not isinstance(check, str) or not check:
                    found.append({'node': label, 'invalid_check': number})
    elif not isinstance(node.get('devices'), dict):
        found.append({'node': label, 'no_checks_or_device_reports': True})
    for device, report in node.get('devices', {}).items():
        found.extend(inspect(report, label + '/' + device))
    return found

reports = []
for name, member in sorted(members.items()):
    raw = (a.store / member['retained_path']).read_bytes()
    if len(raw) != member['bytes'] or hashlib.sha256(raw).hexdigest() != member['sha256']:
        issues.append({'report': name, 'retained_byte_identity_mismatch': True})
    data = json.loads(raw)
    report_issues = inspect(data, name)
    issues.extend(report_issues)
    reports.append({'path': name, 'bytes': member['bytes'], 'sha256': member['sha256'],
                    'git_blob_sha1': member['git_blob_sha1'],
                    'reported_status': data.get('status'),
                    'checks_count': len(data.get('checks', [])),
                    'errors': data.get('errors'), 'runtime_errors': data.get('runtime_errors'),
                    'inspection_status': 'failed' if report_issues else 'passed'})

result = {'schema': 'luoyang-original-browser-suite-check-v2',
          'method_version': 'check_original_browser_reports_v2.py',
          'mapping_file': str(a.mapping) if a.mapping else None,
          'mapping_sha256': hashlib.sha256(a.mapping.read_bytes()).hexdigest() if a.mapping else None,
          'status': 'failed' if issues else 'passed', 'phase': a.phase,
          'expected_commit': a.expected_commit, 'baseline_ingest': str(a.baseline),
          'evidence_ingest': str(a.evidence), 'attempt_jobs_api': str(a.jobs),
          'expected_report_count': len(expected), 'actual_report_count': len(members),
          'browser_directory_count': len({n.split('/')[0] for n in members}),
          'job_conclusion': matching[0]['conclusion'] if len(matching) == 1 else None,
          'browser_step_conclusion': steps[0]['conclusion'] if len(steps) == 1 else None,
          'reports': reports, 'issues': issues,
          'note': 'Original reports, checks and error fields inspected against their CAS bytes; no browser rerun or image-geometry approval.'}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(bool(issues))
