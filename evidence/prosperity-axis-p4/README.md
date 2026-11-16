# 盛时 P4：宫城中轴考古尺度专题的正式验收归档

本归档只保存**官方公开工作流日志及发布事实**。项目研究图件、源码、原发掘报告链接和三页 PDF 已包含在已验收的生产代码与 Pages 资源内，不复制整个大站或另行分发原刊。

- 功能 PR：[31](https://github.com/mechgouki/luoyang-city/pull/31)
- PR head：`b96ad0f6805cecbd3ff17f37db8fa52de497f6ba`。
- 实际生产提交：`1b28f71f56db28d287aab94e8f48d8d084b60664`。
- PR head、正式合并源码 tree：`29812dac8e00f7414881498f4fe85600def04b38`，之前版本的研究图与原件保存。
- [PR CI 43884408277](https://github.com/mechgouki/luoyang-city/actions/runs/43884408277)：completed/success。
- [正式 CI 43885369995](https://github.com/mechgouki/luoyang-city/actions/runs/43885369995)：completed/success；`build`、`deploy`、`verify-live` 三任务 success。
- PR/生产各完成 P3+P4 及既有研究的语义检查；其中 P3/P4 prosperity suite **58项通过**。
- PR、正式构建与实际 HTTPS 线上新 P4 浏览器测试全部通过，包含三图资源加载、三期切换并刷新保留 URL、首页与 P3 入口、手机与 JavaScript 关闭回退、CSV/JSON/PDF/ZIP 下载。
- 正式 `verify-live` 日志明确：**482 public assets verified, HTTP retries: 0**；全部原有旧地图浏览器检查继续执行。
- 此证据只证明实现/数据相对于提交保持一致；**不是**古址定位、北魏单期遗址或460/475米测线已经获得田野复核。

## 本归档文件

- `pr-build.log`：PR CI 构建、测试及浏览器执行的原始日志。
- `production-build.log`：正式主分支构建、测试及浏览器执行的原始日志。
- `production-verify-live.log`：正式 HTTPS 资源核验及完整浏览器检查原始日志。
- `manifest.json`：官方记录、对应 Job ID 与 Git blob 校验ID。

本归档分支不用于触发 Pages 部署，也不改变已经发布的 `main`。
