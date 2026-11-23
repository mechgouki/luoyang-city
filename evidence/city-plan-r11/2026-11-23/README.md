# R11.1 全城共同坐标复原平面：永久验收证据

本目录保存 2026-11-23 正式发布的原始构建、正式站、图纸和回查证据。正式成果入口为[全城统一坐标·复原工作平面](https://mechgouki.github.io/luoyang-city/luoyang-city-plan.html)，图册为[17 页正式 PDF](https://mechgouki.github.io/luoyang-city/downloads/city-plan-r11.pdf)。本目录保留两次失败 PR、首次生产的两项人工排版发现、本地修正和最终通过记录，各自保持当时身份。

## 最终发布身份

| 项目 | 固定身份与结论 |
|---|---|
| 研究版本与时窗 | R11.1；516–528 盛时综合研究平面 |
| 主 PR | [#82](https://github.com/mechgouki/luoyang-city/pull/82) |
| 排版小修 PR | [#83](https://github.com/mechgouki/luoyang-city/pull/83) |
| 最终正式提交 | `129abaee724870ec00bc25c6e2fd2998a215063b` |
| 最终源码树 | `f6ed7ac2587da1f5639b76bc4c2b86097eed796d` |
| 小修 PR 实际测试提交 | `1faf2a4380e1e4676f78f5533ed045ceffe3a4ae`；与正式提交同树 |
| 小修 PR 运行 | [45101964789](https://github.com/mechgouki/luoyang-city/actions/runs/45101964789)，completed / success |
| 最终生产运行 | [45103224890](https://github.com/mechgouki/luoyang-city/actions/runs/45103224890)，completed / success |
| 生产三个关口 | build `137458587738`、deploy `137462473919`、verify-live `137462590965` 全部 success |
| 最终完成时间 | 2026-11-23 03:24:29 UTC／上海时间 11:24:29 |

[acceptance.json](acceptance.json) 汇总最终结果与原始材料身份。[最终运行 API](production-final-129/api-final-run.json) 和[最终 jobs API](production-final-129/api-final-jobs.json) 保留实际状态。归档提交以最终正式提交为唯一父提交，只在独立 evidence 分支新增本证据前缀，生产源码与 main 不因归档而改变。最终归档提交、独立远端逐字节回读和外部冻结清单摘要由主控记入[实施 Issue #52](https://github.com/mechgouki/luoyang-city/issues/52)，避免将验收自身递归写入待验对象。

## 成果范围与空间判断边界

正式平面含 237 个有类型的几何项：28 项原来源几何、33 项来源图示描摹、4 项尺寸参照、24 项独立宫城概览图示、148 个候选位置点。339 条名录记录全部接入阅读与回查，其中来源定位组 11 条、候选组 163 条、未定位组 165 条。候选点与名录记录存在合并共签，两个计数口径分别保留。

全城、宫城、阊阖、永宁、宫城来源对照及十一片区共 16 个视窗共用同一几何数据；有 302 条约束、35 份来源输入和 1,614 个依据指针。17 页 PDF 的首页为 A2 横向，其余页面为 A3 横向，保留矢量线条与可搜索中文；提供 26 个唯一下载文件。

本轮完成的是共同工作坐标下的证据平面。已可描的源图轮廓、图示范围和候选位置统一读图，未知街坊、院落和建筑边界继续留空。339 条目录与 237 项几何均不能解释为相同数量的测定建筑。没有新增古代测量坐标、历史岸线或经实测验证的共同控制点；局部平面接入母图的单锚、图北等候选绑定保留明确限制。各片区视窗边缘不是历史坊界。

外郭绿色虚线 `geo-outer-city-related-remains` 表示**外郭相关遗存范围图示**，不是一圈连续实测外郭城墙。原 28 项来源几何逐点保留，旧宫城墙线的来源线型也保留。V12 首页位图与 V13r2 候选位图未在本轮重绘，首页新增可逆的共同平面入口。

### 两组新增原图事实

- **永宁寺刊载完整平面**：23 项可辨构件，包括保留门缺口与原图线型的七段寺墙、塔地基、塔座、佛殿图示框、南西门边界及道路／水沟线。北门没有补造；柱础图例不被解释为完整上部建筑。50 米图尺严格等比例读取，没有将院界分轴拉伸成文献的 212 × 301 米。邻接候选仅使用这张图的七段寺墙包络，旧来源残墙作为独立来源回查。
- **奈良 2013 年宫城概览图**：24 项图示隔壁、版筑范围、道路和调查位置，以独立来源比较层展示，默认隐藏。图上开放的北边没有补闭；调查黑块仅作调查位置点。太极殿等名称附近的灰块称为版筑图示范围，不称详细殿基。阊阖—太极图示参照距离约 501.68 米，与旧来源约 573.88 米的差异保留，没有用两点拟合消除来源冲突。

两组原图的 URL、页码、图号、原始 PDF／图像 hash、比例尺和北针取点、逐构件事实矢量及限制保存在 [最终来源输入](source-inputs-final-129/production-source-identity.json) 及相应 JSON、方法文档。永久档案不收整份第三方来源 PDF、原始栅格、裁图或带原图底图的叠照。35 份研究输入在首次生产与最终小修之间逐字节相同；新增固定 renderer 源码记录排版修正。

## 正式站与实际下载验收

最终生产构建桌面、构建手机、正式站桌面、正式站手机各完成 7 组检查、26 次真实点击下载和 5 张截图，共保留 104 次下载的原字节及 20 张 R11 截图。四路下载、CI HTTPS 及主控独立公网实际文件逐项 SHA256 相同。最终 CI HTTPS 报告实际检查 **920** 个资源，`checked_files` 与文件数组长度一致，状态 passed，无 HTTP 重试；原始报告为 [live-http.json](production-final-129/live-artifacts/live-http.json)。

[独立跨阶段核验](production-final-129/independent-cross-check/) 保存可复跑方法与核验结果。主控 [公网回读报告](production-final-129/root-public/public-readback-report.json) 独立检查 35 项实际资源，另保存 build-info 原字节，包括全部 26 个下载。含提交戳的 PR 文件只与各自测试提交的 Pages 产物比较，不被要求与生产提交字节相同。

浏览器报告覆盖全部 16 个视窗、五类图层、来源比较层默认状态、缩放平移与恢复、搜索和异名、339 条目录、证据入口、实际文件下载、离线 ZIP 及禁用 JavaScript 阅读。手机真实塔座点击先关闭名称、实际放大三次，在可见轮廓内取点；必须由 `elementFromPoint` 命中塔座自身 path，然后真实点击并通过严格对象标题断言，再恢复名称另行点击图签。四路报告均保留该命中记录。既有研究版本的完整浏览器回归和原日志也随实际 CI 包保留。

主控实际人工浏览器会话发生在首次生产 e137，原记录保存在 [原人工 UI 记录](production-candidate-e137/root-public/public-ui-review.json)。最终 [deployed-ui-identity.json](production-final-129/root-public/deployed-ui-identity.json) 证明公开版初始交互 SVG、atlas.js 和 atlas.css 与该次实际审看的资源逐字节相同；它不冒称又执行了一次人工浏览器会话。最终 129 的真实完整交互由本次 CI 另行验证。

## 实际正式 PDF 的修前后核验

最终公开 PDF 为 **2,126,410 bytes**，SHA256 为 `2466af8e41776be7731a99e35bf9e417faf035e16116c7d6ee475c2927047fc6`。四路浏览器实际下载与独立公网原字节均为同一文件。

[最终生产 PDF QA](production-final-129/map-qa/final/final-production-pdf-qa.json) 保存 17 页 144 dpi 渲染、联系表、逐页文字、字体及精确比较。34 个字体项均嵌入并有 Unicode 映射。与首次实际生产 PDF 比较，14 页像素完全相同；第 8 页“西阳门外御道”与第 13 页“通商／大货〔市东，内部无序〕”仅移动图签并保留引线，均已重看整页和放大细节，原遮字已解决；第 17 页仅正式提交页脚改变，也已实际目检。

16 张最终公开地图 SVG 与冻结修正稿逐字节相同；`method.svg` 仅提交号由 e137 改为 129，不能称 17 张 SVG 全字节一致。237 项 feature、16 个视窗取景与全部原标签均保持。A2／A3 密集图应放大或按对应纸幅阅读，手机整页缩略图用于总览。

## 运行历史及目录导览

| 目录 | 如实保留的阶段与结论 |
|---|---|
| `pr-failed-45095919491/` | PR82 第一轮：R4／R5 旧入口恢复兼容断言两项失败，浏览器未执行 |
| `pr-failed-45096652591/` | PR82 第二轮：桌面通过；手机中心点击选中同心地基图签，未通过塔座标题断言；失败截图与原日志保留 |
| `pr-success-45097907766/` | PR82 成功，实际测试 merge `283e1578…`；构建及完整浏览器通过 |
| `production-candidate-e137/` | 首次生产 e137／45099225785 三关口通过；独立人工 PDF QA 另发现两处轻微遮字，保留 CI 与人工发现各自结论 |
| `local-preflight/` | 初始预检、兼容修复 263 项本地测试及本地排版修正；均保留 local 身份 |
| `pr-success-45101964789/` | 小修 PR83 成功，head45d6069c、实际测试 merge1faf、treef6ed；33 项 Pages 资源与 52 次 PR 真实下载核对 |
| `production-final-129/` | 最终生产全部原始 API、三份 artifact 成员、完整日志、正式下载、独立公网原字节与正式 PDF QA |
| `source-inputs/` | 首次生产 e137 的固定来源输入快照，不改写为最终版本 |
| `source-inputs-final-129/` | 最终 129 的 35 份研究输入、5 份方法文档和固定 renderer 源码，逐项绑定 Git blob |
| `source-identities/` | 固定提交和源码树的 Git API 原文 |
| `source-review/` | 来源 hash、元数据及提取事实核验，不含第三方原图 |
| `archive-preparation/` | 独立归档口径审查及最终限定写入授权记录 |
| `archive-methods/` | 解包、哈希、交叉核验、原生树、精确远端回读方法，以及 R10 永久范围规则参考 |

历史报告中的 pending 标志记录其收集时点；最终通过由本目录的 acceptance 和最终 API 明确确认，原报告不被追改。首次手机失败的修复保留真实点击和严格断言，没有将塔地基与塔座混同。排版 PR83 只改变两处图签布局，没有改动历史几何。

## 永久范围和完整性核验

[archive-inventory.json](archive-inventory.json) 为每个正文路径列出字节数、SHA256 与 Git blob SHA，并逐项记录 12 个 Actions 原始 ZIP 的成员身份与去向。[archive-scope.json](archive-scope.json) 列出全部保留和省略项目；实际浏览器下载的 ZIP 保留。

仅按已验证规则省略冗余包装：每个成员字节已核定的 Actions 外层 ZIP；实际 R11 发布字节及元数据已核定的 Pages 部署 tar；与 R10 永久范围 SHA256 完全相同的七类地形中间件。完整原 ZIP 和 tar 在本地取证目录保持未改写；归档不重复储存二进制包装。地形来源说明及元数据继续保留。原图版权边界由允许材料清单、已知原始来源 hash 排除和源数据审查共同限定。

[archive-sensitive-scan.json](archive-sensitive-scan.json) 记录 UTF-8 文本及保留 ZIP 内文本的凭据、私钥和认证 URL 模式扫描；扫描数是文本检查数，不是逐张图片版权审查数。空发现保留其启发式检查边界。

上传按精确 Git blob 去重，每个路径仍保留原字节身份。小 UTF-8 文件可经 Git tree 的 content 批量形成对象，仍核对预期 blob SHA 与本地原生根树。最终独立核验从远端精确提交获取 Git 对象，逐项读取实际字节，核查唯一父提交、根树、文件模式、前缀外源码和 main，不能只信上传回执。

三个生成索引不列入自身 inventory，以免自引用；它们由外部冻结 upload manifest 和最终独立远端回读一并覆盖。归档完整性与历史空间可靠性是不同结论，图中证据等级和不确定范围不会因长期保存而提高。
