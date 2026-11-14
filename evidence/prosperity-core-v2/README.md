# 盛时洛阳 P2：核心建筑尺度与局部结构验收归档

本版完成 PR 验证、生产构建、部署及正式 HTTPS 网站验收。正式入口：[核心建筑，进入真实尺度](https://mechgouki.github.io/luoyang-city/prosperity-core.html)。[生产运行 43587199337](https://github.com/mechgouki/luoyang-city/actions/runs/43587199337) 的 `build`、`deploy`、`verify-live` 均为 `success`；原始时间记录使用 UTC。

P2完成三处核心建筑尺度片、三张局部结构图和院界差异校核。完整盛时城市全景、古地面与精确考古配准仍在推进。

## 提交与来源

- 实施 PR：[mechgouki/luoyang-city#27](https://github.com/mechgouki/luoyang-city/pull/27)。
- 通过的 PR 运行：[43586652076](https://github.com/mechgouki/luoyang-city/actions/runs/43586652076)。PR 按既有流程只构建验证，部署和正式站阶段跳过。
- PR 分支提交：`fd72ae0defb0a3abd2a7818d8c94baa5c9f12114`。
- PR 测试合并提交：`fb34b53fe16cc3e063ae343105c72c075f75d7a4`。
- 正式合并与公开构建提交：`9b2e2c79ed51fc68400f87b0b7a26b6223d4a7f6`。
- 三者源码树相同：`8dace59fae84211b9a251400037b642ca001a219`。见 [commit-provenance.json](commit-provenance.json)。
- 长期证据分支：`evidence/prosperity-core-v2-9b2e2c7`；归档目录：`evidence/prosperity-core-v2`。

| 生产阶段 | Job ID | 结果 |
|---|---:|---|
| build | 132424137391 | success |
| deploy | 132425303311 | success |
| verify-live | 132425386954 | success |

原始元数据见 [production-run.json](production-run.json)、[production-jobs.json](production-jobs.json) 和 [production-artifacts.json](production-artifacts.json)。

## 验收结果

| 阶段 | Python | Node | 浏览器套件 / 检查 | JS 运行时错误 |
|---|---:|---:|---:|---:|
| PR 构建 | 249 项通过 | 5 项通过 | 16 套 / 239 项通过 | 0 |
| 生产构建 | 249 项通过 | 5 项通过 | 16 套 / 239 项通过 | 0 |
| 正式 HTTPS 网站 | 使用已验收构建 | 使用已验收构建 | 16 套 / 239 项通过 | 0 |

249项 Python 来自每次构建的19份原始报告，包含旧239项和本版新增10项；Node TAP均为5 pass、0 fail、0 skipped。浏览器原始报告逐条为passed，runtime_errors为空。三个阶段分别计数，不将重复执行当成新增覆盖。

P2每阶段新增12个浏览器检查组，涵盖普通指针与键盘点选、缩放和拖动、区域聚焦、平面与斜视独立视窗、深链接和后退恢复、非法参数回退、来源/下载/附图，以及1500px、900px、390px显示。语义测试独立核对实际米制边长、原锚点、角度约定、SVG顶点和投影、原三面墙保留、院框排除、结构空值、PDF页数和ZIP字节。旧B1—B8、H1与P1全部继续验收。

逐套计数见 [summary.json](summary.json)；原始报告分别在 [pr/](pr/)、[build/](build/)、[live/](live/)。

### 公开资源

[live/live-http.json](live/live-http.json) 在 `2026-11-14T10:56:36Z` 记录448个唯一公开资源全部通过，HTTP重试为0。每项SHA-256均与另外从正式网站下载的 [build-info.json](live/build-info.json) 一致；[release.json](live/release.json)、构建信息和验收报告均指向正式合并提交。

公开构建清单共449项，其中 `.nojekyll` 是不公开的构建控制文件，单独记录并排除；没有把该项当成丢失资源。P2记录422个受保护旧文件；首页和P1页面新增入口的可控改动在保留机制中单列。

PR、生产构建和正式站使用同一个浏览器镜像摘要，原始记录保存在各自的 `browser-runtime-digest.json` 中。

### 视觉复核

七页PDF已逐页检视，永宁寺塔基标签换为两行后重新检查通过。六张PR浏览器截图已独立复核；正式站六张截图中五张与PR截图字节完全相同。

桌面完整页面截图仅在 `x=16–153、y=991–1092` 的焦点跳转链接区域有差异：全页截屏的滚动/焦点状态使“跳到核心区地图”链接上下移动，其余像素完全相同。该差异已单独检视；地图、附图、来源、下载、页尾和主要控件没有布局回退。

六张正式站截图位于 [live/live-prosperity-core-v2-browser/](live/live-prosperity-core-v2-browser/)，包含桌面首屏、宫城斜视、完整附图与来源、平板、手机首屏和手机完整页面。

## 保存范围与完整性

归档保留全部原始JSON/TXT报告、两份Node TAP原文片段、六张本版正式站截图、公开版本信息、原始工作流及artifact元数据。三个用于提取证据的ZIP在提取前均核对SHA-256；对应ID和摘要见summary。Pages部署包仅保留元数据，没有声称对未下载的部署包另做文件摘要核对。

完整Actions ZIP、其他版本截图和Pages部署包没有复制进本目录。原始artifact的ID、大小、摘要和到期时间仍保存，长期复核使用本目录内的报告和截图。

最终文件数和各目录计数见summary。[SHA256SUMS](SHA256SUMS) 校验除清单自身外的全部文件；可在本目录运行 `sha256sum -c SHA256SUMS` 复核字节。

## 图面成果与研究边界

- 宫城阊阖门基44.5×24.4m、太极殿遗址约100×60m、永宁寺地上塔基遗存约38.2m方形，形成三处定尺参照片。平面和斜视使用同一几何，原图代表点没有移动。
- 三张无比例局部结构图表达27个部件、30条关系；提供7页图册、SVG、几何/研究JSON和ZIP。
- 来源图墙间距约264.9m与表列院宽212m存在差异；独立院框没有进入城市落位，也未补北墙。
- 时层仍为516—528河阴之变前合成区间。来源坐标仍为西安1980，工作朝向不等于实测建筑方位角；位置概略、尺寸出处和显示安排分别保存。
- 古代地面、建筑原高、完整柱网与屋顶未复原；斜视7px厚度是显示参数，2.2m残高和6m地下夯土深度没有转为盛时建筑高度。
- 局部结构图的真实坐标与未知距离保持空值。北门不施屋，南门地面通道数未定，僧房为非定位目录；基址连接不自动成为有顶廊，破坏沟不转为盛时水道。

公开方法与出处见[位置与尺度说明](https://mechgouki.github.io/luoyang-city/prosperity-core/method.md)及[局部结构说明](https://mechgouki.github.io/luoyang-city/prosperity-core/relations.md)。没有重发布1GB来源PDF或完整原图。
