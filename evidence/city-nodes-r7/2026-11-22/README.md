# R7.1 城市节点联读与 V12 导览：发布验收档案

当前档案状态：修正PR已通过；最终主干发布验收进行中。本次快照不宣告正式站验收完成。

- 研究窗口：516—528年；研究R7.1，实现city-nodes-r7.1；批准首页panorama-approved-v12。
- 最终源提交：9599123701766cbdfe5971095af638898f407efe。
- 修正PR：#76；运行44979526114成功。实际测试merge-ref为2827a108e68bc113453df66bf18e5133e6072b65。
- 修正PR与最终main的Git树均为e9f3f16df602680ee4e5a465c2c922812fc88d96。
- 最终主干运行：[44980204847](https://github.com/mechgouki/luoyang-city/actions/runs/44980204847)。

## 已保留材料

- `original-pr/`：原PR75检查的必要报告与截图，精确保留范围见其selection-manifest.json。
- `original-live-failure/`：原正式运行44972925535因根.nojekyll误作公开资源而失败的实际报告。该报告不被后来的成功覆盖。
- `corrected-pr/`：修正PR76的实际构建、测试、截图、下载与离线检查证据；测试源码与PR head分列。
- `full-svg-review.json`：五张完整SVG的原指纹和逐图目视检查；本地渲染核查不替代正式站验收。
- `source-provenance.json`：原版、修正PR、最终main之间的来源关系。
- `extract-actions-evidence.py`、`capture-production.py`：原Actions成员提取与实际公网回读脚本。

最终主干构建、正式站浏览器报告、独立HTTP回读与完成清单将在同一证据分支继续补齐；最终结果以本档案后续提交及Issue #47、#52的完成记录为准。
