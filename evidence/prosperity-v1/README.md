# 盛时洛阳 P1：正式发布验收归档

本版已完成 PR 验证、生产构建、部署及正式 HTTPS 站点验收。正式发布运行 [43581755260](https://github.com/mechgouki/luoyang-city/actions/runs/43581755260) 的 `build`、`deploy`、`verify-live` 均为 `success`；记录时间为 2026-11-14 UTC。网站入口为[盛时洛阳：从文献平面到城市分布](https://mechgouki.github.io/luoyang-city/prosperity.html)。

这是盛时文献审校与城市骨架第一版的工程验收。古代地面、绝对位置精度和完整古城复原仍保留研究边界，见文末。

## 提交与来源

- 实施 PR：[mechgouki/luoyang-city#26](https://github.com/mechgouki/luoyang-city/pull/26)。通过的 [PR 运行 43581095325](https://github.com/mechgouki/luoyang-city/actions/runs/43581095325) 执行构建验证，PR 阶段的部署与正式站验证按工作流跳过。
- PR 分支提交：`efcf7c50f6c0897f7eb93afc3ee6d61f56e764bb`。
- PR 测试合并提交：`951210b4c71b95487fe28f9a74859a696f2b8419`。
- 正式合并与公开构建提交：`6824dd363332099c6afc9c31d7beff0f221ca320`。
- 两个合并提交的源码树相同：`c7dea8250f78b1e1c8527c52f1913a0c5353cef5`。详见 [commit-provenance.json](commit-provenance.json)。
- 长期证据分支：`evidence/prosperity-v1-6824dd3`；目录：`evidence/prosperity-v1`。

| 生产 job | Job ID | 结果 |
|---|---:|---|
| build | 132407776938 | success |
| deploy | 132408765240 | success |
| verify-live | 132408849670 | success |

原始运行和步骤记录见 [production-run.json](production-run.json)、[production-jobs.json](production-jobs.json)。

## 验收结果

| 验证阶段 | Python | Node | 浏览器套件 / 检查 | JS 运行时错误 |
|---|---:|---:|---:|---:|
| PR 构建 | 239 项通过 | 5 项通过 | 15 套 / 227 条通过 | 0 |
| 生产构建 | 239 项通过 | 5 项通过 | 15 套 / 227 条通过 | 0 |
| 正式 HTTPS 站点 | 使用已验收构建 | 使用已验收构建 | 15 套 / 227 条通过 | 0 |

每次构建的 Python 数量来自 19 份 `Ran … / OK` 原始报告，包括既有 216 项和本版新增 23 项。Node TAP 原文片段均记录 5 pass、0 fail、0 skipped。浏览器报告逐条检查均为 `passed`，各报告 `runtime_errors` 均为空。阶段数量分别统计，不把同一组检查在不同阶段的重复执行当作新增覆盖。

[summary.json](summary.json) 保存逐套计数及报告路径；原始报告分别位于 [pr/](pr/)、[build/](build/)、[live/](live/)。盛时套件每阶段 18 条检查，覆盖真实地图缩放与拖动、179 个正式键盘目标、共享组成员、地点筛选、独立来源要素、现代参照开关、深链接、来源与文献核对、历史地形线索，以及 1500px、900px、390px 页面。

### 线上资源与版本

[live/live-http.json](live/live-http.json) 在 `2026-11-14T09:46:30Z` 记录 **425 个唯一公开文件全部通过**，逐项 SHA-256 与实时下载的 [build-info.json](live/build-info.json) 相同，HTTP 重试为 **0**。[release.json](live/release.json)、构建信息和 HTTP 验收报告的提交均为正式合并提交。

构建清单有 426 项，其中 `.nojekyll` 是不公开的构建控制文件，报告单独记录；425 项公开资源哈希全部匹配，没有将该控制文件记为资源缺失。

PR、生产构建、正式站浏览器使用相同镜像摘要，原始记录分别在各目录的 `browser-runtime-digest.json`：

`mcr.microsoft.com/playwright/python@sha256:3de745b23fc4b33fccbcb3f592ee52dd5c80ce79f19f839c825ce23364e403c1`

## 本归档保存范围

本目录保留**全部原始 JSON/TXT 报告、两份 Node TAP 原文片段，以及本版 6 张正式站截图**。保存的是可核对的验收材料，没有复制整个数十 MB 的 Actions ZIP、其他版本截图或 Pages 部署产物。

- `pr/`：42 份原始 JSON/TXT 材料，另存 PR jobs、artifacts 元数据和 Node 片段，共 45 个文件。
- `build/`：42 份原始 JSON/TXT 材料及 Node 片段，共 43 个文件。
- `live/`：15 份正式站浏览器结果、HTTP 验收、运行器摘要、实时下载的 build-info/release，以及 6 张盛时截图，共 25 个文件。
- 根目录：生产 run/jobs/artifacts 与提交溯源 4 份原始 JSON，以及本 README、summary 和 SHA256SUMS。

原 ZIP 的 artifact ID、大小、SHA-256 和到期时间保留于 [pr/artifacts.json](pr/artifacts.json) 与 [production-artifacts.json](production-artifacts.json)，便于核对来源。本目录共有 120 个文件；[SHA256SUMS](SHA256SUMS) 使用相对路径校验其中除清单自身外的 119 个文件。在本目录运行 `sha256sum -c SHA256SUMS` 可复核归档字节。

### 本版正式站截图

以下截图来自生产 `verify-live`，与 PR 截图分开记录。

| 文件 | 尺寸 |
|---|---:|
| [prosperity-desktop-first-screen.png](live/live-prosperity-v1-browser/prosperity-desktop-first-screen.png) | 1500 × 1000 |
| [prosperity-geography.png](live/live-prosperity-v1-browser/prosperity-geography.png) | 1500 × 1000 |
| [prosperity-mobile-first-screen.png](live/live-prosperity-v1-browser/prosperity-mobile-first-screen.png) | 390 × 844 |
| [prosperity-mobile.png](live/live-prosperity-v1-browser/prosperity-mobile.png) | 390 × 6824 |
| [prosperity-panorama.png](live/live-prosperity-v1-browser/prosperity-panorama.png) | 1500 × 1000 |
| [prosperity-tablet-first-screen.png](live/live-prosperity-v1-browser/prosperity-tablet-first-screen.png) | 900 × 1000 |

## 实际成果与研究边界

公开构建元数据记录：**339 个文献实体、30 个来源图几何、11 个有来源图位置绑定的既有实体、183 条文献记录、5 条历史地形约束、8 项建筑尺度与基底资料、6 页图册**。404 个受保护旧文件继续保留。详见 [build/prosperity-build.json](build/prosperity-build.json) 与 [live/build-info.json](live/build-info.json)。

文献电子匹配不等于全版本古刻书影逐叶校勘；来源图的代表点、遗存线和显示范围不自动确证盛时院界。来源坐标仍为 EPSG:4610，WGS84 配准尚未完成，原图拟合残差也不代表地面定位精度。现代河道参照、历史地形线索、局部壕泥与基底深度分别说明，**未生成古代 DEM**。布局鸟瞰由同一套平面几何计算，未据此补出全城建筑立面、民居密度或完整古城。
