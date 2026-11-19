"""Index completed P4.6.7 production evidence; refuse a partial acceptance."""
import datetime
import hashlib
import json
from pathlib import Path

p = Path(__file__).parent
readback = json.loads((p / 'public-readback.json').read_text())
jobs = json.loads((p / 'production-jobs.json').read_text())['jobs']
assert {j['name']: j['conclusion'] for j in jobs} == {
    'build': 'success', 'deploy': 'success', 'verify-live': 'success'
}
live = json.loads((p / 'live-http.json').read_text())
assert live['commit'] == readback['source_commit']
assert live['status'] == readback['status'] == 'passed'
for device in ['desktop', 'mobile']:
    r = json.loads((p / f'live-{device}-report.json').read_text())
    assert r['status'] == 'passed' and r['errors'] == [] and r['map_count'] == 5
    assert r['base_url'].startswith('https://mechgouki.github.io/')

context = json.loads((p / 'acceptance-context.json').read_text())
context['production_status'] = 'build_deploy_verify-live_success'
context['checked_beijing'] = readback['checked_beijing']
context['live_checked_files'] = live['checked_files']
(p / 'acceptance-context.json').write_text(json.dumps(context, ensure_ascii=False, indent=2) + '\n')

pdf_sha = hashlib.sha256((p / 'water-467.pdf').read_bytes()).hexdigest()
text = f'''# P4.6.7 正式站验收长期副本

核对时间：{readback['checked_beijing']}（北京时间）。

- 发布提交：`{readback['source_commit']}`。
- [PR #56](https://github.com/mechgouki/luoyang-city/pull/56)。
- [生产运行 44496324313](https://github.com/mechgouki/luoyang-city/actions/runs/44496324313)：build、deploy、verify-live 全部成功。
- [正式专题](https://mechgouki.github.io/luoyang-city/prosperity-water-p467.html) · [五页图册](https://mechgouki.github.io/luoyang-city/downloads/water-467.pdf)。

## 验收内容

`live-http.json` 保存正式工作流对 {live['checked_files']} 项公网资源的实际哈希检查；`production-jobs.json` 保存三任务结果；`build-info.json` 对应本次发布提交。

`live-desktop-report.json`、`live-mobile-report.json` 保存正式站五图操作结果：选段、证据层筛选、SVG编号点选、深链接复载、缩放／平移／触摸拖动、无JavaScript阅读、PDF／JSON／SVG下载及哈希。两端均为passed、无页面错误。原始截图保留实际字节；完整下载图册另存为`water-467.pdf`。

`public-readback.json` 是发布后的独立回读，核查 {readback['checked_files']} 个关键文件、五页PDF，以及P466 PDF和首页H2两张图的封存哈希。PDF SHA-256：`{pdf_sha}`。

PR报告对应本地CI服务地址，正式报告对应github.io；两类报告分别保存，不混记生产验收。视窗截图只反映当时可见范围，全部图段的操作与下载覆盖见报告，不能由单张视窗截图推断图下方均已拍入。SVG及PDF完整图面已在制图时视觉核查。

## 可复用研究与边界

五图共53个关系段，类型为36个流向、8个连接、5个解释假说、2个工程提议、2个相邻。53不是河道数，也不表示每段在516—528年的每一年通水。没有新增米制量测、绝对历史坐标或目标年代实测岸线。

`ancient-leaves-readback.json` 记录《水经注》四部本两叶的图页、字句与核读影像哈希；`yang2021-access-audit.json` 记录新增的下册定位与访问结果。完整逐段出处见主分支`research/prosperity-v4/water-467/`；访问失败没有写成原图取得。

水-02仍等待2022报告图2-2（印21／数字44）和图2-2-4整幅折页（数字45，含尺标、图例和全部孔号）；取得后先对剖线方向与孔号，再记录渠宽、渠深、界面和断代。2011原调查图及杨萧杨2021下册358—369页分别仍是原图与校读文本缺件。桥头和岸段只在同层证据支持时提升定位精度。水-04已另行启动张方沟、城壕、宫西水道与独立园池核读；这些余项有可继续利用的原典和原刊，不因城南缺图一并暂停。下一实际动作以#52最新记录为准。

固定进度入口：[Issue #52](https://github.com/mechgouki/luoyang-city/issues/52)；史料与验收：[Issue #47](https://github.com/mechgouki/luoyang-city/issues/47)。
'''
(p / 'README.md').write_text(text)
files = []
for f in sorted(p.iterdir()):
    if f.is_file() and f.name != 'manifest.json':
        data = f.read_bytes()
        files.append({'path': f.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
(p / 'manifest.json').write_text(json.dumps({'source_commit': readback['source_commit'], 'files': files}, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'files': len(files), 'pdf_sha256': pdf_sha, 'status': 'indexed'}, ensure_ascii=False))
