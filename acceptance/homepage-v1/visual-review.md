# H1 首页视觉验收

结论：**通过，可以合并。** 本记录对应 PR #25 的构建截图，不代表生产网站已经完成验收。

- PR：[mechgouki/luoyang-city#25](https://github.com/mechgouki/luoyang-city/pull/25)
- PR 验收运行：[43556783910](https://github.com/mechgouki/luoyang-city/actions/runs/43556783910)
- PR head：`c8cf6034a1d499bee60921169d41c3cefc778e88`
- 构建报告原始 source_commit：`18aee165ff764598c905ff366e91f1301202aa61`。按原值保留，不推断该值的提交类型。

## 已查看的图像

路径均为本轮 `browser-build-evidence` artifact 内的路径；字节数与 SHA-256 保存在 `pr-acceptance.json`。本轮长期目录保留文本结果，未额外复制 PNG。

| 图像 | 像素尺寸 | 审查来源 |
| --- | --- | --- |
| `homepage-v1-browser/homepage-desktop-first-screen.png` | 1500 × 1000 | root 已检查并确认通过 |
| `homepage-v1-browser/homepage-mobile-first-screen.png` | 390 × 844 | homepage_verification 已直接查看 |
| `homepage-v1-browser/homepage-tablet-first-screen.png` | 900 × 1000 | homepage_verification 已直接查看 |
| `homepage-v1-browser/homepage-mobile.png` | 390 × 5305 | homepage_verification 已直接查看 |

## 观察结论

手机主图完整保留木塔、长街和远景宫城；标题移到图片下方，按钮没有挤压、重叠或裁切。手机全页中，三个问题、互动地图和后置研究区顺序正确，未见内容遮挡或横向溢出。

900px 平板的两行导航完整位于页头内，主图从页头下方开始。此前发现的 851—1000px 页头固定高度冲突已经修正，截图与新布局断言一致。

桌面视觉 QA 由 root 独立完成并确认通过；本报告明确保留这一归属，未将其记作本代理的直接检查。未发现需要阻塞合并的视觉或布局问题。

## 与自动验收的对应

原始 JSON 共记录 14 个浏览器套件、209 个通过项，其中首页 10 项；失败项 0，运行时错误 0。首页构建报告记录 398 个既有资源保持不变。原始结果及原始构建报告以逐文件 UTF-8 原文保存于 `pr-acceptance.json`，可按其 SHA-256 复核。

## 后续正式验收

生产提交为 `1d541938cb8b21cb218d5bbd934cf41bbdfa9fc8`，生产运行 [43557485331](https://github.com/mechgouki/luoyang-city/actions/runs/43557485331)。本目录等待 root 补入该运行的实际 build、deploy、verify-live、HTTPS 哈希及生产浏览器结果；本 PR 证据包未包含或预先宣称这些结果。

## 生产验收补记

生产运行的 build、deploy、verify-live 均已成功。406 个公开资源与下载文件的哈希核对通过，14 套正式站浏览器测试共 209 项通过；线上 build-info.json 的提交与合并提交一致。root 已在正式浏览器确认首页全景、开始探索及 LR10 市场问题的展开结果。首次导航有一次 sheets 请求未成功，一次正常刷新后恢复；原因未确认，此观察与自动测试零运行错误分开记录。完整正式报告见 production-acceptance.json。
