# 永宁寺三图：GitHub API 与作业日志恢复记录

本目录于 2026-11-25 重新从 GitHub 读取元数据与原始作业日志。它保存已有运行的证据，没有重新触发工作流，也没有写入远端。

## 可以确认的技术状态

PR #87 已合并；当前 main 为 `bbfbac9022e133e61836614f3b120cf42efde43e`。PR 的实际测试 checkout 为 `4eedbf6c452ab6d1cb3bccf2864c182201c68eb3`，见 `pr-build.log` 与摘录。PR head、测试 merge 和 production 的 tree 均为 `92fa3faf994ed1172512697b18024a5c9948d54b`，三份 Git commit API 响应分别保存。

PR 运行 45360973001 的 build 成功；PR deploy / verify-live 按规则跳过。生产运行 45363321713 第一次 build 与 deploy 成功，verify-live 在旧版 `tests/browser_prosperity_axis_v4.py:65` 因 `SVG preview must be visible` 断言失败。原日志保留，失败原因没有进一步确诊，不能仅凭重跑成功写成网络故障。

第二次仅重跑失败的 live 验收，2026-11-24 21:09:37（上海）成功结束。attempt 2 API 同时列出 build/deploy 成功条目，但开始与完成时间与第一次完全一致；不表述为重新构建或重新发布。

## 本目录不能代替的验收

本目录没有独立回读当前正式站资源，没有下载或验证 Actions ZIP 字节；这两项另由主控和归档任务完成。技术验收成功不改变图像未通过的结论，完整基址、全景与首页替换仍未批准。

PR #87 原文仅列本地检查并说合并后应验收和保存原始证据；没有提到独立 49 文件回读，没有给出该证据的外部下载位置。API 报告 PR comments=0、review_comments=0，评论列表为 []。

## 内容与处理方式

- `pr-87.json`、`pr-87-comments.json`：PR 原始 API 内容与空评论列表。
- `production-run.json`、`production-attempt-1.json`、`production-attempt-2.json`：生产运行及两次尝试。
- `production-attempt-1-jobs.json`、`production-attempt-2-jobs.json`：各次完整 job 元数据与步骤。
- `pr-run.json`、`pr-run-jobs.json`：PR 运行及完整 job 元数据。
- `main-branch.json`、三份 `*-commit.json`：当前远端 head 及实际 tree 身份。
- 四份完整 `.log`：PR build、生产 build、失败 live 与成功 live 原始解码日志。
- 两份 `*-excerpt.log`：由上述原日志抽出的 checkout／失败位置，非替代原件。
- `api-retrieval-provenance.json`：每份原件的 API URL 与内容保存约定。
- `acceptance-api-facts.json`：依据原件生成的最小事实摘要。
- `api-evidence-manifest.json`：精确文件集、字节数与 SHA-256（清单不自哈希）。

API 返回的文本和解码日志保存为 UTF-8；源文本没有终止换行时增加一个 LF。没有 HTTP 响应头或原压缩传输容器的字节声明。来源字符数已按 JavaScript UTF-16 计数核对本地文件，确保除上述 LF 外未截断或改写。
