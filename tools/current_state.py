"""Keep current summaries in sync; leave historical milestone records untouched."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'research/current-state.json'
START = '<!-- current-state:start -->'
END = '<!-- current-state:end -->'


def summary(data, source_link):
    research, home = data['research'], data['homepage']
    release = data['last_verified_release']
    years = '—'.join(str(n) for n in data['target_years'])
    return '\n'.join([
        START,
        f"当前状态（{data['updated_at_beijing']}）：研究 **{research['version']} / {research['implementation_version']}**（{research['title']}）；"
        f"首页修订为 **{home['label']} `{home['revision']}`**（{home['review_status_label']}）；几何封存基线 **{data['geometry_baseline']}**。研究时段为 **{years} 年**。",
        '',
        f"[正式首页]({home['url']}) · [现行研究入口]({research['url']}) · "
        f"[上一已验收发布 `{release['source_commit'][:7]}`]({release['workflow_url']}) · "
        f"[长期验收证据]({release['acceptance_url']}) · [最新交接 #52]({data['handoff_url']})。",
        '',
        f"以上摘要由[当前状态登记]({source_link})生成。首页、研究批次和封存底图的版本分别理解；旧批次中的 V9／V11 与旧进度仅为历史记录。新一批正式完成仍以对应发布提交的构建、部署与正式站验收为准。",
        END,
    ])


def synchronize(write=False):
    data = json.loads(SOURCE.read_text())
    paths = [('README.md', 'research/current-state.json'),
             ('docs/current-state-and-next.md', '../research/current-state.json')]
    changed = []
    for name, source_link in paths:
        path = ROOT / name
        original = path.read_text()
        if original.count(START) != 1 or original.count(END) != 1:
            raise ValueError(f'{name}: expected one current-state managed block')
        before, rest = original.split(START, 1)
        _, after = rest.split(END, 1)
        updated = before + summary(data, source_link) + after
        if updated != original:
            changed.append(name)
            if write:
                path.write_text(updated)
    if changed and not write:
        raise SystemExit('Current summaries differ: ' + ', '.join(changed) +
                         '. Run python tools/current_state.py --write.')
    return changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--write', action='store_true', help='Update only the two current-summary blocks')
    mode.add_argument('--check', action='store_true', help='Verify summaries without writing (default)')
    args = parser.parse_args()
    changed = synchronize(args.write)
    print('Current state: ' + (', '.join(changed) + ' updated' if changed else 'summaries match'))
