# 冻结检查点的独立核验证明

被验检查点：`f67e00306e1f1f92c7c2c3957d0f4cfccbaa7be0`；来源生产 `bbfbac9022e133e61836614f3b120cf42efde43e`；被验 tree `ac50efd31c75e7c1b21401b393a3060db8f8f315`。

[固定技术档案](https://github.com/mechgouki/luoyang-city/blob/f67e00306e1f1f92c7c2c3957d0f4cfccbaa7be0/evidence/yongning-triptych/2026-11-25/README.md) · [固定局部 V3 研究检查点](https://github.com/mechgouki/luoyang-city/blob/f67e00306e1f1f92c7c2c3957d0f4cfccbaa7be0/research/panorama-r12/local-refinement-20261125/README.md)

## 核验结果

2026-11-25 **17:02:14（上海）**，从公开远端分支取入新建、独立的 bare Git 对象库后，逐文件核对通过：

- 两个冻结前缀共 **379 文件**，其中技术档案含索引 368 文件、局部研究含索引 11 文件。
- **302 个不同 blob**，路径合计 **109,365,265 字节**。
- 全部路径、mode、字节数、SHA-256、Git blob SHA 与冻结清单一致；两个索引自身也纳入核对。
- 唯一 parent 为生产源；两个前缀外的文件没有变化，既有路径没有被覆盖。
- 预检与远端回读分开保存，原件见下列文件。

本目录在被验对象之后建立，不修改原 379 文件。发布与图像状态的事实仍分别读取：三图专题技术验收通过；新局部 V3 不适合回嵌；完整全景与首页替换均未获通过。

## 原件

- `frozen-manifest.json`：在远端读取前固定的逐文件预期身份。
- `remote-readback.json`：实际远端对象逐文件核验结果与时间。
- `independent-preflight.json`：另一审阅流程对原始报告、HTTP 响应、来源指纹和研究结论的核对。
- `verify_remote_checkpoint.py`：实际执行的只读核验脚本。

复核时先从远端将固定检查点 fetch 到独立 bare 库的 `refs/verify/checkpoint`，将生产源 fetch 到 `refs/verify/production`，再运行本脚本，指定 `--git-dir`、`--manifest frozen-manifest.json`、`--out`。脚本不进行网络访问，不改变来源数据，也不重新宣告生产或图像验收。

