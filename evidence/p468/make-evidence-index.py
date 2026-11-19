"""Index completed P4.6.8 production evidence; refuse partial acceptance."""
import hashlib
import json
from pathlib import Path
p=Path(__file__).parent
readback=json.loads((p/'public-readback.json').read_text())
jobs=json.loads((p/'production-jobs.json').read_text())['jobs']
assert {j['name']:j['conclusion'] for j in jobs}=={'build':'success','deploy':'success','verify-live':'success'}
live=json.loads((p/'live-http.json').read_text())
assert live['commit']==readback['source_commit'] and live['status']==readback['status']=='passed'
for device in ['desktop','mobile']:
    r=json.loads((p/f'live-{device}-report.json').read_text())
    assert r['status']=='passed' and r['errors']==[] and r['map_count']==5
    assert r['base_url'].startswith('https://mechgouki.github.io/')
context=json.loads((p/'acceptance-context.json').read_text())
context['production_status']='build_deploy_verify-live_success'
context['checked_beijing']=readback['checked_beijing'];context['live_checked_files']=live['checked_files']
(p/'acceptance-context.json').write_text(json.dumps(context,ensure_ascii=False,indent=2)+'\n')
pdf_sha=hashlib.sha256((p/'water-468.pdf').read_bytes()).hexdigest()
text=f'''# P4.6.8 正式站验收长期副本

核对时间：{readback['checked_beijing']}（北京时间）。

- 发布提交：`{readback['source_commit']}`。
- [PR #57](https://github.com/mechgouki/luoyang-city/pull/57)。
- [生产运行 {context['production_run_id']}](https://github.com/mechgouki/luoyang-city/actions/runs/{context['production_run_id']})：build、deploy、verify-live 全部成功。
- [正式专题](https://mechgouki.github.io/luoyang-city/prosperity-water-p468.html) · [五页图册](https://mechgouki.github.io/luoyang-city/downloads/water-468.pdf)。

## 实际验收

`live-http.json` 保存生产工作流对 {live['checked_files']} 项公网资源的实际哈希检查；`production-jobs.json` 和 `build-info.json` 对应发布提交。`public-readback.json` 另行回读 {readback['checked_files']} 个关键文件，核五页PDF与全部新下载，并对P467五SVG／53段JSON／原PDF、P466原PDF和H2两张图复核封存SHA。

`live-desktop-report.json`、`live-mobile-report.json` 两端均passed、无页面错误，检查五图切换、选段、三层筛选、深链复载、缩放／键盘平移／鼠标与触摸拖动、无JS完整证据、报告原值表、八JSON／五SVG／PDF下载，以及P467勘误链接到第五图的往返。保存的PNG均为浏览器实际截图原字节，`-map.png`为完整图面截图。PR报告使用CI本地服务地址，生产报告使用github.io，分别保留。

PDF SHA-256：`{pdf_sha}`。图册页数及下载字节由实际文件核验，未以链接存在代替。

## 研究结果及更正

五图47条关系，流向12、相连2、相邻20、包含7、层位2、解释4。补核12项旧水体，并重核5项池名；5项重核与前册重叠，不增加原清单34项总数。9行原典／报告原值保持观测对象与时层。新增地理坐标、米制图测、516—528年岸线均为0。

P467旧I09及覆盖表将W20濛汜池、W21碧海曲池挂入华林园诸海的映射已撤回；旧PDF／JSON作为历史字节保留。P467前页显著勘误和P468机器可读更正是当前判断：濛汜在长秋寺北，夏有水、冬竭；碧海在西游园台下。群体供水恢复“若旱魃为害”的条件，不展为各池口或逐年恒流。撤回映射不证明两池绝无水路。

`pr-attempts.json` 保留失败尝试及修正原因。首轮错误要求图顶贴0px，改验完整视口边界；第二轮在禁用JavaScript时等待页面主上下文异步回调，改用Playwright滚动及同步几何检查。第三轮桌面全部通过，手机无JS页面长来源标签等撑至427px，超过390px视口；修正局部换行、内容最小宽度与公开分类标签，同时加强配置视口宽度检查，避免移动浏览器扩张innerWidth造成漏检。未隐藏页面溢出、跳过交互或无JS证据，均以最终通过的实际浏览器运行作验收。

## 可直接执行的原件断点

水-02优先取得2022报告图2-2（印21／数字44）及图2-2-4整幅折页（数字45，含图例、尺标、全孔号）。先对剖线与孔号，再登记渠宽、渠深、沉积界面和断代；未完成配对前不定516—528河岸及永桥桥头。

2011鸿池调查原图、杨萧杨2021下册358—369校勘原章、城壕逐孔报告、宫西完整平剖、路-02《考古》1993年602—608原刊仍有缺件。全清单核读完成不表示全部岸线、池口或每年通水已定；缺证处保留相对关系、并列解释或空白，无需用户替证据裁决。

固定续接：[Issue #52](https://github.com/mechgouki/luoyang-city/issues/52)；原页、量测与验收：[Issue #47](https://github.com/mechgouki/luoyang-city/issues/47)。
'''
(p/'README.md').write_text(text)
files=[]
for f in sorted(p.iterdir()):
    if f.is_file() and f.name!='manifest.json':
        data=f.read_bytes();files.append({'path':f.name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(p/'manifest.json').write_text(json.dumps({'source_commit':readback['source_commit'],'files':files},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'files':len(files),'pdf_sha256':pdf_sha,'status':'indexed'},ensure_ascii=False))
