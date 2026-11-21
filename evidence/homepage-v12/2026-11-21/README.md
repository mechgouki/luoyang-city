# 首页 V12「全幅取景版」验收档案

正式首页：https://mechgouki.github.io/luoyang-city/

本档案在全部输入校验通过后生成。首页版本 **panorama-approved-v12**；实际 PR 测试源为 `190c485e7c325324aebd183c20ae91bc8603c9df`，正式发布提交为 `d33474764aab494ef8a61e243f2c919a0e4f6288`。PR 与正式站的首页原图 SHA-256、两个 WebP 资源 SHA-256 已相互核对，并与独立 HTTPS 原响应核对。

## 实际运行

- PR：https://github.com/mechgouki/luoyang-city/actions/runs/44903475054；快照明确记录 build 为 completed/success，若出现 deploy/verify-live 则必须为 completed/skipped。
- 正式站：https://github.com/mechgouki/luoyang-city/actions/runs/44904341782；快照明确记录 build、deploy、verify-live 均为 completed/success。
- 原始快照完整保存在 `github-workflows.json`。采集元数据中的 workflow_conclusion 不是工作流验收依据；本档案要求实际运行和作业记录明确成功。
- 正式 HTTP 清单验证 801 项资源；独立公开回读保留 32 次原响应、31 项不同资源，以及首尾一致的 build-info。

## 文件

`pr/`、`live/`、`production/` 保留三个输入目录的全部文件；原报告、截图、响应体、响应索引和响应头记录均未重建或省略。`tools/` 保存实际采集脚本、独立 HTTPS 校验脚本及本归档脚本。`summary.json` 记录提交、资源哈希、截图比对和检查结果；根目录 `SHA256SUMS` 覆盖全部文件，除清单自身。

截图逐一与原报告或采集清单核验哈希。PR 与正式截图是否逐字节相同见 summary；哈希一致性不冒充人工视觉审阅。生成时间：2026-11-21T20:47:23+08:00（Asia/Shanghai）。

本次只发布用户批准的首页图和完整画幅布局；图像仍是研究性复原示意，已有道路、水系证据等级和未知端点不因画面替换而升级。
