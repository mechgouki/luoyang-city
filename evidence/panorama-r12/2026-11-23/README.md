# R12.1 共同透视依据与 V14 试绘审查：技术发布验收

**技术发布验收已通过；V14 六次全景试绘仍全部未通过。** 主显示第五次，第六次为独立附录，状态保持 `needs_revision / rejected_needs_revision`，首页继续已批准的 V12。本记录确认审查页、资源身份、生产流程和实际浏览器／下载证据，不接纳候选图或授权更换首页。

生产提交：`4579a6b8990a91780bf83391967c301218c0711e`；Git tree：`69aef90f87200463e97a4f5331be90029cc0c9c2`。[正式首页](https://mechgouki.github.io/luoyang-city/) · [V14 审查页](https://mechgouki.github.io/luoyang-city/luoyang-panorama-v14.html) · [统一平面](https://mechgouki.github.io/luoyang-city/luoyang-city-plan.html) · [生产运行45182742216](https://github.com/mechgouki/luoyang-city/actions/runs/45182742216)。

CI 最后一项任务完成于 **2026-11-23 21:51:21（上海）**。全部最终原件核对后，本技术验收记录生成于 **2026-11-23 22:06:48（上海）**；两者均不表示之后的档案远端回读已经发生。详细记录见 [acceptance.json](acceptance.json)，接续状态见 [current-state-after-acceptance.json](current-state-after-acceptance.json)。

## 本次实际验收

以下时间均为2026-11-23上海时间；ID、结论和时间直接来自[本次 attempt jobs 原始 API](production-45182742216-a1/api/api-jobs-attempt1-final.json)。

| 任务 | 实际 job ID | 起止时间 | 用时 | 结论 |
| --- | --- | --- | --- | --- |
| build | `137720438238` | 21:19:16—21:32:23 | 787 秒 | `success` |
| deploy | `137727902581` | 21:32:28—21:32:45 | 17 秒 | `success` |
| verify-live | `137728114930` | 21:32:48—21:51:21 | 1113 秒 | `success` |

[最终收取记录](production-45182742216-a1/collection-summary.json) 与 [源树身份](production-45182742216-a1/source-tree-identity-check.json) 核实：build 和 live 的实际 checkout、Pages 源提交均为上述生产提交，树与 PR86 实际测试树相同。公开 `build-info.json` 原字节与本次 Pages 一致，SHA-256 为 `00c438d6dad74ad252785072f2adaea91281e0067d661950b09c882cdacab6b8`。

- **完整 HTTP 检查：958 项资源，0 次重试。** [原始清单](production-45182742216-a1/live-http-original.json) 的路径集合、字节数和 SHA-256 与本次 Pages／发布清单逐项对应；仅排除未发布的空控制文件 `.nojekyll`。报告内 `checked_at` 原字段保留，完成时间按真实 job step 记录。
- **build 与 live 各有62份原始报告、42个浏览器证据目录。** [build核对](production-45182742216-a1/build-all-browser-reports-check.json) 和 [live核对v2](production-45182742216-a1/live-all-browser-reports-check-v2.json) 均检查原件内容与错误字段。每阶段36份明确声明顶层 `passed`，26份旧格式未声明；30份含源提交，32份未声明。R11汇总重复嵌入两份设备报告，文件数不能当作独立测试数。每阶段225条截图hash引用去重为215个文件。
- **V14四组实际下载核对通过：** build桌面、build手机、live桌面、live手机各27次真实点击下载、27个下载对象及3张登记截图，与同次Pages对应。见 [build下载核对](production-45182742216-a1/build-browser-download-cross-check.json) 与 [live下载核对](production-45182742216-a1/live-v14-browser-download-cross-check.json)。HTTP专项还记录917项受保护公开文件、2个可回溯首页；首页图像版本保持V12，不把新增入口等HTML变化说成从未发生。
- **主控独立正式站回读：42文件，含27个必需下载。** [回读记录](root-live-4579a6b8/readback.json) 与 [Pages原字节交叉核对](root-live-4579a6b8/pages-build-info-cross-check.json) 绑定本次提交。早前主控在 `fa5398b` 已交互审看；最终公开HTML、CSS、JS及六张展示图共9项实际字节相同，见 [连续性证明](root-live-4579a6b8/ui-publication-continuity.json)。这不是第二次主控浏览器会话；本次双端实际交互由完成的live CI另行证明。

P470/P471的live输出目录与build默认目录存在两个明确名称差异。初次派生汇总假定统一前缀，列出4个路径差异；[原结果](production-45182742216-a1/live-all-browser-reports-check.json) 及同字节副本保留。[精确映射](production-45182742216-a1/browser-output-mapping-v2.json) 依据固定工作流、脚本默认值与原日志，仅处理这两个名称，核对全部42输出目录和62份内容。这是收取映射修正，不是CI失败，也没有修改原报告或源工作流。

## 保留的实际历史

| 阶段 | 实际结果 | 证据 |
| --- | --- | --- |
| PR84首轮，45165875123 | 新发布层提前拦截R9 ZIP篡改，旧内层断言未到达，build失败 | [记录](pr-45165875123-a1/collection-summary.json) |
| PR84修复，45167225217 | 修正断言后build通过，保留外层拒绝和内层精确检查 | [记录](pr-45167225217-a1/collection-summary.json) |
| 生产fa5398b，45169490719 | build / deploy成功；verify-live缺PIL，浏览器未执行 | [记录](production-45169490719-a1/collection-summary.json) |
| PR85，45173171686 | 补齐Pillow 11.2.1，PR构建、身份及下载核对通过 | [记录](pr-45173171686-a1/collection-summary.json) |
| 生产33c14be，45175501815 | HTTP与V14专项通过；完整旧版回归至B3时取消，后续未完成 | [记录](production-45175501815-a1/collection-summary.json) |
| PR86，45180026243 | 只把verify-live总预算20→40分钟，完整PR构建和原件身份核对通过 | [记录](pr-45180026243-a1/collection-summary.json) |
| 最终生产4579a6b，45182742216 | build / deploy / verify-live均success，完整原件与独立公开回读通过 | [记录](production-45182742216-a1/collection-summary.json) |

`33c14be` job实耗20分23秒，实际结论是 `cancelled`，原日志只明确写取消；没有取得明确timeout注释。预算比较支持扩大总时限，不能把历史结论改成 `timed_out`。PR86保持各HTTP／浏览器步骤及各自超时不变。所有失败、取消和初次派生检查原件继续保留，最终成功不覆盖它们。

## 两张局部试片与宫城地面窗口

两张永宁寺试片独立于原六次全景，**不是第七／第八次全景或首页候选**。

- [试片01](next-step-yongning-study/independent-review.json)：九层塔、三层南门及独立基脚更清楚，但画幅比例改变，完整几何未通过。
- [试片02](next-step-yongning-study/attempt-02/independent-review.json)：保留九层塔、三层南门、塔后佛殿与独立基脚；1536方形输入至1254方形输出等比。八处同名可见基脚南缘大体接近冻结投影，约读不确定性约±4px；完整角点、遮挡边和寺墙端点未核，尚不能直接回嵌或认定完整几何通过。

[宫城纯地面控制窗口](next-step-palace-control/README.md) 仅把冻结SVG外层视窗改为 `590 220 110 110`，等比显示1536×1536；开始标签后的字节保持。13个对象涵盖阊阖门构件、二号门尺度片、三号门早期南半残存尺度片及太极殿尺度片。它没有补地上体块、高度或完整院落，也未解决候选绑定、量距端点及异报。开放边、地下轮廓和连接路径保留各自证据角色；原粗线一起放大，重叠、虚线间隙和空白不能当建筑尺寸或历史上没有建筑的证据。

这些材料已有[研究固定检查点b91f102](https://github.com/mechgouki/luoyang-city/blob/b91f102911753a95b378d88b1bbf80f8fd3599e2/research/panorama-r12/local-controls-20261123/README.md)，22文件、3,044,036 bytes独立远端逐字节通过。[回读记录](cross-checks/local-controls-remote-checkpoint.json) 与 [逐文件证明](cross-checks/local-controls-provenance/remote-verification.json) 保留。该研究检查点不证明完整宫城形制或授予首页批准。

下一步以第二张试片作结构／材质参考，冻结SVG继续控制布局；先核对完整轮廓、可见基脚、遮挡边和墙端，按同一显示变换回嵌，再用宫城登记保留阊阖门、二三号门的证据角色与前后层次。地上表达保持艺术假设标注，不移动冻结地面对象或重拟合H迎合生成图。完成实际全景复查后再给用户审看具体候选，首页V12保持。

89项来源几何、863顶点使用同一地面投影；现场共同控制点为0，没有新增古代实测坐标、古岸几何或已证建筑高度。516—528年仍是综合研究窗口，不由画面推定全城共时、完整坊界或未知建筑轮廓。

## 来源状态与后续档案协议

生产提交中的 `research/current-state.json` 是发布前 `pending_verification` 快照，其精确字节身份见 [生产源清单](source-identity/production-4579a6b8-source-manifest.json)。[本次接受后状态](current-state-after-acceptance.json) 从该固定来源另存真实技术结果，保留原快照和上一R11发布身份；没有改main，也没有为登记验收触发新部署。

实际Pages artifact有959个成员身份，长期CAS选择保留42个出版原件；build与live证据分别保留736、691个完整成员。其他Pages旧资源只有身份账时，不据此宣称其字节全部永久保存。浏览器实际下载的ZIP必须保留；Actions传输包装与精确固定旧地形引用的省略范围由组装记录明确说明。

**最终技术档案按以下协议完成，本文不填写尚未产生的档案commit或远端回读结论。** 唯一parent为 `4579a6b8990a91780bf83391967c301218c0711e`，只新增 `evidence/panorama-r12/2026-11-23/`；父树前缀原先不存在，见 [父提交与范围核对](source-identity/archive-final-parent-scope.json)。主控使用现有assemble / freeze / remote-byte-verify流程，在组装后生成 `assembly-scope.json`、`archive-inventory.json`、`archive-scope.json`、`archive-sensitive-scan.json`，一并纳入冻结清单。真正远端档案commit、独立逐字节回读及固定链接写入单独验证分支和#52最终交接，不回填冻结档案形成自引用。

#52和#47继续OPEN。已发送的[技术pending接续](https://github.com/mechgouki/luoyang-city/issues/52#issuecomment-7102439255) 与[研究接续](https://github.com/mechgouki/luoyang-city/issues/47#issuecomment-7102531343) 作为历史保留。最终交接读取最新issue正文，仅替换当前R12状态块并保留所有历史，不以最初R11正文覆盖本次进展。
