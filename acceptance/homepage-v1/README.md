# H1 首页发布验收长期记录

正式网站：https://mechgouki.github.io/luoyang-city/

- 界面里程碑：H1 / homepage-v1；研究工作层：B8；底图几何：v2.4。
- 实施 PR：https://github.com/mechgouki/luoyang-city/pull/25
- 实施提交：`c8cf6034a1d499bee60921169d41c3cefc778e88`。
- 生产合并提交：`1d541938cb8b21cb218d5bbd934cf41bbdfa9fc8`。
- PR 验收：https://github.com/mechgouki/luoyang-city/actions/runs/43556783910
- 生产验收：https://github.com/mechgouki/luoyang-city/actions/runs/43557485331

## 结果

生产 build、deploy、verify-live 均为 success。406 个公开资源的 HTTPS 内容与发布哈希一致；14 套生产浏览器检查共 209 项通过，其中首页 10 项覆盖桌面、900px 平板、390px 手机、地图操作、三个问题深链接、刷新与返回。398 个既有研究资源逐字节保留。线上 build-info.json 和 release.json 均记录上述生产提交。

## 文件与追溯

- `pr-acceptance.json`：PR 浏览器检查与首页构建报告，保留原始 UTF-8 JSON、字节数和 SHA-256。
- `production-acceptance.json`：生产工作流的实际任务结果、全部 HTTPS 资源哈希检查、14 套正式站浏览器原始报告、浏览器运行环境摘要及直接版本核对。原始报告从 Actions ZIP 提取，ZIP 摘要已复核。
- `visual-review.md`：桌面、平板和手机视觉检查；原始截图位于记录的 Actions artifact，长期保留其尺寸、摘要和审查结论。未重复存储 PNG、地形栅格或可重建产物。

该证据分支作为长期归档保存，不合入 main，不触发重复网站部署。原始 Actions artifact 会到期，以上 JSON 文本仍可按所存摘要逐字恢复与复核。

## 表达边界

首页主图为研究性复原示意。H1 调整阅读入口和排版，不增加历史确证、古址坐标或测量精度。已有 B1—B8 内容、实体 ID、图册下载、历史版本和未定解释保持可追溯。下一研究批次仍为 B9，引文逐字核对与历史图接合索引追查。
