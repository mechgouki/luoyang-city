"""Connect the manual e137 UI review to the exact final deployed UI assets."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

before = Path('/tmp/r11-live-review/public')
after = Path('/tmp/r11-final-live-review/public')
old_commit = 'e137f473278282c6c30a29e2c018de666577889a'
new_commit = '129abaee724870ec00bc25c6e2fd2998a215063b'
assert json.loads((before / 'build-info.json').read_text())['source_commit'] == old_commit
assert json.loads((after / 'build-info.json').read_text())['source_commit'] == new_commit
checks = []
for rel in ('city-plan-r11/atlas.js', 'city-plan-r11/atlas.css'):
    old = (before / rel).read_bytes()
    new = (after / rel).read_bytes()
    assert old == new, rel
    checks.append({'component': rel, 'byte_identical': True, 'bytes': len(new),
                   'sha256': hashlib.sha256(new).hexdigest()})
pattern = re.compile(r'<svg\b[^>]*\bid="city-plan-map"[^>]*>.*?</svg>', re.S)
old_html = (before / 'luoyang-city-plan.html').read_text()
new_html = (after / 'luoyang-city-plan.html').read_text()
old_match, new_match = pattern.search(old_html), pattern.search(new_html)
assert old_match and new_match
old_svg, new_svg = old_match.group(), new_match.group()
assert old_svg == new_svg
body = new_svg.encode('utf-8')
checks.append({'component': 'published HTML initial city-plan-map SVG',
               'byte_identical': True, 'bytes': len(body),
               'sha256': hashlib.sha256(body).hexdigest()})
report = {
    'status': 'deployed_interface_identity_verified',
    'checked_at_utc': datetime.now(timezone.utc).isoformat(),
    'manual_ui_review_source_commit': old_commit,
    'final_deployed_source_commit': new_commit,
    'manual_ui_review_report': '/tmp/r11-live-review/public-ui-review.json',
    'checks': checks,
    'scope': 'The manually reviewed JavaScript, CSS and initial interactive map are byte-identical in the actual new public page. This is not a claim of another manual browser session. Final desktop/mobile, download and legacy UI acceptance is recorded separately by production run 45103224890.',
    'final_full_live_workflow_status_when_recorded': 'pending',
    'review_url': 'https://mechgouki.github.io/luoyang-city/luoyang-city-plan.html?view=all&layers=source%2Ctrace%2Cscale%2Ccandidate#plan-reader'
}
out = after.parent / 'deployed-ui-identity.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
