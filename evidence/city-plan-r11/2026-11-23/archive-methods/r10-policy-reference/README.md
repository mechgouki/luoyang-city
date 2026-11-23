# R10.1 全城总平面与十一片区布局：永久验收证据

本目录保存 2026-11-22 正式发布的真实验收材料。正式站为 [北魏洛阳文献地图](https://mechgouki.github.io/luoyang-city/)，本轮入口为 [全城总平面与十一片区](https://mechgouki.github.io/luoyang-city/luoyang-city-layout.html#overview)。发布结果与归档完整性分别核验；本目录不把早期失败运行、局部通过或本地图面审阅写成正式站验收成功。

## 发布身份与结论

| 项目 | 固定身份／结果 |
|---|---|
| 研究版本 | R10.1；516–528 综合研究时窗 |
| 合并 PR | [#81](https://github.com/mechgouki/luoyang-city/pull/81) |
| 正式提交 | `a2d1aac203d468ab0584a09f2c9ec0bfc6dd372b` |
| 正式源码树 | `2efc3c9cfb26ee3a5d579b5a4df3d767bac62581` |
| PR 最后验收 | [45034680481](https://github.com/mechgouki/luoyang-city/actions/runs/45034680481)：success；head `88c359588349f8c1f6bb2cd8d346fd7f4aada783`，实际测试 merge ref `d37e31cef48f23fdc62587622e27584e842e3d11` |
| 正式工作流 | [45035882296](https://github.com/mechgouki/luoyang-city/actions/runs/45035882296)：completed / success |
| 正式三个 gate | build `137249422596`、deploy `137253268867`、verify-live `137253370102` 均 success |
| 工作流最后更新时间 | 2026-11-22 15:28:24 UTC／上海时间 23:28:24 |

完整机器可读结论与关键原始文件身份见 [acceptance.json](acceptance.json)。运行最终 API 原文见 [main-live/api-final-run.json](main-live/api-final-run.json) 和 [main-live/api-final-jobs.json](main-live/api-final-jobs.json)。归档提交是正式源码提交的独立证据分支后继；正式源码与页面内容不因归档而改变。最终归档提交和独立远端逐字节回读结果记在 [实施 Issue #52](https://github.com/mechgouki/luoyang-city/issues/52) 的本轮交接中，避免把验收自身递归写入待验对象。

## 成果范围与研究边界

已发布 11 片区、42 个关系分窗、96 项空间判断、321 个图签和 259 条图内关系。共 321 次图签出现；其中涉及 245 个去重的原名录实体，另含道路、园地、活动等必要关系标签。保留原有 339 对象总目录、84 条道路证据与 34 条水系索引。PDF 为 16 页，下载清单为 21 个唯一文件。

这些图是带证据入口的来源骨架、相对关系与未定边界表达。它们不构成同一年份的完整实测城市平面。来源图位置、文献相对关系、候选判断和未定位对象继续分别显示；23 项片区缺口与 6 项全城缺口合计 29 项。未补造古代坐标、统一配准、历史岸线，也未提升原始证据等级。V12 与 V13r2 位图没有在本轮重新生成。详细发布计数保存在 [main-build/summary.json](main-build/summary.json)，以实际下载的 `atlas.json` 和正式 `build-info.json` 为依据。

## 正式下载与网页验收

[download-cross-stage-ci-http.json](download-cross-stage-ci-http.json) 对照正式构建桌面、构建手机、正式站桌面、正式站手机及 CI HTTPS 五路：21 个文件全部 SHA256 一致。四个浏览器流共保存 84 次真实下载的原字节，并核验 70 张 R10 截图；各阶段分别为桌面 17 张、手机 18 张。正式站 CI HTTPS 共检查 888 个资源，原始报告保存在 [main-live/artifacts/live-http.json](main-live/artifacts/live-http.json)。

[download-cross-stage-root-http.json](download-cross-stage-root-http.json) 再以 root 独立 HTTPS 结果复核相同下载。`root-public/` 保存 30 个公开资源的实际字节，其中包括全部 21 个下载文件；其实际字节又在归档阶段逐项重算 SHA256。PR 桌面与手机的 42 次下载也完整保存、内部一致，但不会错误要求含提交戳的 PR 资产与正式提交资产相同。

桌面／手机真实浏览器报告覆盖十二幅内联图的缩放、平移、键盘与复位，片区／依据筛选，搜索及 URL 状态恢复，受冲突筛选影响的目标恢复，证据展开，实际下载，离线 ZIP 和禁用 JavaScript 阅读；以各原始报告记录的测试范围为准。所有既有版本的完整浏览器回归报告与日志保留在同一正式运行证据中。

root 另在真实公开页面操作 R03 筛选、流觞搜索、瑶光寺图签跳转、来源展开、R07 缩放复位、清除筛选和总图阅读。记录见 [root-public/manual-browser-review.json](root-public/manual-browser-review.json)。这份记录诚实限定为人工抽查，不冒称逐一人工遍历全部图签、关系或独立完成隐藏目标恢复；完整自动化结论由各 CI 报告支持。人工截图已在对话中显示和目检，没有另行导出文件；长期保留的截图来自真实 CI 包。

## 实际正式 PDF 的逐页 QA

正式构建浏览器实际下载的 PDF 为 2,292,515 bytes，SHA256 为 `6251d946450719247d62ebef36e7770ea49c8fd8df646b4b592e15de110a9810`。生产四路浏览器与独立 HTTPS 的 PDF 字节均与此一致。

[map-qa/production/qa-report.json](map-qa/production/qa-report.json) 及同目录 16 张 Poppler PNG、16 页抽取文字、字体、链接和比较报告保存完整审阅链。前 15 页的 PNG 字节、像素和全文均与此前逐页目检的真实 CI 图集一致；第 16 页再次实际目检，仅提交戳改变，变化边框为 `[127, 1110, 508, 1125]`。687 个注释的目标与矩形全部一致：676 个外链、11 个片区内跳；32 个字体子集全部嵌入并具有 Unicode 映射。没有阻断性排版缺陷。

较早的本地 PDF 使用不同的字体环境，SHA 与正式 PDF 不同。本地预检和首次真实 CI 图集审阅分别保存在 `map-qa/local-final/` 与 `map-qa/pr-failed-45032715660/`，其原报告保持原身份，不被改写为生产验收。A3 密集关系图需要放大或按 A3 尺寸阅读；整页缩至手机宽度只作为总览。

## 目录导览

| 目录／文件 | 作用 |
|---|---|
| `local-preflight/` | 本地 58 项完整回归、17 项受影响回归、确定性检查及早期真实失败日志；保留当时的版本与范围 |
| `pr-initial-45032488183/` | 因新确定性修正提交而取消的初始运行；不记为通过或断言失败 |
| `pr-failed-45032715660/` | 第 11 次快速下载未发出 download event 的失败报告、截图、10 个已完成下载、原日志及诊断 |
| `pr-failed-45033555972/` | R10 两设备各 21 次下载已通过，但后续全套浏览器超过 8 分钟预算的运行 |
| `pr/` | 最终成功 PR 的完整构建、语义和浏览器报告、截图、真实下载与源码身份 |
| `main-build/` | 实际正式源码构建的完整报告、截图、真实下载、原日志与 artifact 身份 |
| `main-live/` | 正式站完整验收包、HTTPS 报告、浏览器材料、deploy／verify-live 原日志及最终 API 结论 |
| `root-public/` | 独立公开 HTTPS 原字节、响应信息、build-info 与实际人工操作记录 |
| `map-qa/` | 本地、首次 CI 和最终生产 PDF 的完整图面审阅链 |
| `independent-preflight/` | 独立验收人员对回读方案、公开字节与生产 QA 的准备审查；不代替最终远端回读 |
| `archive-methods/` | 解包、交叉核验、归档、原生树计算、远端逐字节回读及公开 HTTPS 方法脚本 |

第一次下载失败的判断是由 Chromium 固定版本的第一方源码支持的推断，完整限定见 `pr-failed-45032715660/failure-analysis.json`。修复仅给真实点击加 150 ms 间隔，没有关闭浏览器安全策略、删减下载、降低断言或延长单项 30 秒超时。第二次失败保留为套件预算超时；之后仅将工作流两处完整浏览器步骤的预算从 8 分钟改为 12 分钟，job 上限仍为 20 分钟。最终成功 PR 与正式站已执行完整保留的套件。

## 永久归档规则

[archive-inventory.json](archive-inventory.json) 为每个正文文件记录字节数、SHA256 和 Git blob SHA，并列出六个实际 Actions ZIP 的完整成员身份与去向。[archive-scope.json](archive-scope.json) 列出全部保留和剔除范围；[archive-sensitive-scan.json](archive-sensitive-scan.json) 记录 UTF-8 文本及保留 ZIP 内文本的凭据／私钥／认证 URL 模式扫描。扫描结果只列文件名与规则名，不记录敏感片段。空结果是检查结果，不是对所有未知秘密格式的绝对保证。

永久归档只剔除两类已逐字节核定的冗余材料：每个成员均已验证的 Actions 外层 ZIP；以及 SHA256 与 R9 永久范围完全相同的七个地形中间件，来源说明与元数据仍保留。真实浏览器下载的 ZIP 保留。体积较大的 `github-pages` 部署 tar 按既定授权不重复下载；其 artifact ID、大小、摘要与范围说明保留，正式资源通过浏览器与公开 HTTPS 的实际字节验收。

原始 incoming 材料在归档过程中没有改写或删除。本地 payload 可使用硬链接减少临时物理占用；每个最终路径在 Git 中仍由独立内容对象引用。上传前再次计算全部 SHA256／Git blob，远端回读依据精确提交、父提交、原生根树和外部 upload manifest 验证全部路径、模式与实际字节，并核对归档前缀外的生产源码没有变化。

三个生成索引因自引用问题不列在自身 inventory 中；其完整字节身份由外部冻结 upload manifest 和最终独立远端回读覆盖。最终回读报告和该 manifest 的 SHA256 另记入实施 Issue 的固定交接，不以自身声明代替验证。
