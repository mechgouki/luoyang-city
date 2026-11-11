# GitHub 迁移续接核查 · web 0.1.1

研究基线仍为 v2.4；本次不改动历史位置、339 条实体、30 条争议、11 个分区或 37 张图页。

## 已确认的上一个停止点

仓库 `mechgouki/luoyang-city` 的源数据并未丢失。`780ec3e` 已将研究源文件提交，`5d96dc5` 已保存原始 PDF 分片和完整性校验程序。它们不是尚待上传的本地文件。

此前最近一次 Actions 的数据检查通过，部署在 `configure-pages` 初始化环节失败。启用 Pages 与向仓库推送文件是两项不同操作；不要将“代码已经上传”写成“网站已经上线”。

## 本次修复

1. 分区框实际采用 `[x, y, width, height]`；旧代码误作 `[x1, y1, x2, y2]`，导致多个分区跳转偏移。现在按原始格式读取。
2. 母图有 `translate(200 640)` 的页面排版平移。点击层现在放在同一绘图组内；相机边界通过该组矩阵转换。未修改任何历史研究坐标。
3. 普通点击原先过早捕获到整个视口，使鼠标无法打开地点。现在只在超过拖动阈值后捕获，并按同一屏幕变换平移。
4. PDF 的分片合并和 SHA-256 核验移到独立 build 任务，在尝试上线前完成。
5. 网站只发布 `_site/` 明确列出的文件，不再上传整个仓库根目录；源数据、程序、PDF 分片和测试仍保存在 GitHub。
6. 移除默认令牌无法完成的自动启用 Pages；部署配置失败时显示具体的人工初始化步骤。

## 核验方法与边界

- `node --test tests/map-interactions.test.cjs`：5 项回归测试，包括全部 11 区的边界读取、坐标变换和鼠标／拖动事件。
- 数据校验：339 实体、179 交互标记、30 争议、11 区、37 图页。
- 原始图册 SHA-256：`14f30eeb1e525d090e8d75acfd896049e57b57d0d6b3381c16d1c4f289b72823`。
- 浏览器离线检查：以本地数据提供 fetch 响应，检查 11 区可见范围、鼠标点选永宁、景明检索、未定位对象、图册、C01、手机视图，共 20 项通过。此检查不是线上 Pages 可访问性检查。
- 发布后仍需核对真实 HTTPS 地址、子路径资源与下载响应；以 Actions 的 deploy 成功和实际网页访问为准。

## 一次性启用

仓库 Settings → Pages → Build and deployment → Source → GitHub Actions。
然后在 Actions 中选择本工作流，Run workflow（main）或重新运行失败的部署任务。
目标地址：`https://mechgouki.github.io/luoyang-city/`。

官方依据：
- https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- https://github.com/actions/configure-pages/blob/main/action.yml （enablement 需要 GITHUB_TOKEN 以外的令牌）
