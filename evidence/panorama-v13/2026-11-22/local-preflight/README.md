# 本地预验的范围

本目录原样保留本地预验报告。它们只证明未提交 V13 增量在借用的旧生成站点上完成了有限检查；不替代 GitHub Actions 对实际 PR merge-ref、main 提交的 Python 3.11 完整构建与正式站验收。

- 本地 Python 为 3.12.14；未绕过 `build_all.py` 的 Python 3.11 版本要求。
- 借用站点来源为 `d33474764aab494ef8a61e243f2c919a0e4f6288`，819 项；工作树当时 HEAD 为 `557c468649d6919bd249ddd891b9c97cd37cf706`，V13 改动尚未提交。
- 4 个 V13 语义测试及 6 个已批准首页测试通过；本目录保存两类测试的实际输出。
- R7 完整 unittest 在导入时因缺少 `rasterio` 被阻；独立 R7 发布校验通过，其报告 `source_commit` 仍是借用站点的 d334 来源。
- 最终原 PNG 关联校验通过，SHA-256 为 `1808eeb9c2a25a2c22777ae8fba7ae437c983b091de5674b094d10e47cb1c0b1`，真实尺寸 1671 × 941。
- 候选 V13 保持 `homepage_replacement_approved: false`；寺南门三重形制尚未可靠落实。通过软件测试不表示历史复原全部完成，也不表示获批替换首页。

证据来源是同目录的 `panorama-v13-preflight-context.json`、`city-nodes-r7-preservation-v13-preflight.json` 、两份 V13 测试记录、`city-nodes-r7-local-tests.txt` 与 `homepage-v12-local-tests.txt`；6 份原始记录的内容均未改写。完整 CI 将另外归档，不将这些本地结果合并成正式通过声明。
