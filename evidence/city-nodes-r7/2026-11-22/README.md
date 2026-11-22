# R7.1 城市节点联读与 V12 导览：发布验收档案

**当前状态：研究成果已部署；整体正式站验收尚未完成。** 本次快照保留已通过的内容检查和实际失败，不宣告里程碑验收完成。

研究窗口为516—528年；研究R7.1，实现city-nodes-r7.1；首页保持panorama-approved-v12。四处节点、32项核验判断、28条来源记录、五张联读图、六点首页导览的内容已经核对；尚缺原始图版和共同测线的部分在图文中保留。

## 当前收尾

- 原主干ccf2453因根.nojekyll构建标记被误作公开资源而失败；PR76精确区分构建标记与实际公开资源，并修正SI02的宫院／宫城边界表述。
- 中间主干9599123通过构建、部署和818项公开资源核对，旧R6首次导航量宽失败；PR77补上有界load等待与实际尺寸诊断。
- 中间主干d7cd18a的运行44982066390中，构建、部署、HTTP与R6公开浏览器检查通过；R6.2同类首次量宽检查失败。稍后的正常截图不冒充断言瞬间状态的证明。
- PR78正在集中处理R4、R5、R6、R6.2、R7同一组测试的加载前提，保持各自0或1像素的原容差。运行44983493286进行中。产品网页、CSS、研究数据和V12图像保持原样。

## 已保存的阶段

| 目录或文件 | 证明范围 |
| --- | --- |
| original-pr/ | 原PR75测试的必要报告与截图 |
| original-live-failure/ | 原正式运行的.nojekyll失败报告 |
| corrected-pr/ | PR76实际构建、测试、截图、下载与离线检查 |
| merge-build/、main959-live-failure/、live-independent/ | main959的构建成功、正式浏览器失败及独立HTTP快照 |
| readiness-pr/ | PR77实际测试提交、R6加载诊断与重点截图 |
| main-d7-build/、main-d7-live-failure/、main-d7-independent/ | maind7的构建成功、正式R6.2失败与39响应的独立HTTP快照 |
| full-svg-review.json | 五张完整SVG逐图目视检查及精确指纹 |
| manual-live-ui-review.json | 研究内容正式页的首页入口、六点导览、证据检索及原图回链操作 |
| source-provenance.json | PR head、实际测试merge-ref、各次主干与工作流状态 |
| build-archive-index.py、verify-remote-archive.py | 显式证据清单和Git真实字节回读；不凭这两项宣告生产验收 |

旧报告按其捕获时的真实状态保留。最终被接受的生产提交、三阶段结果、正式站桌面／手机报告和远端归档回读，将在后续成功后单独登记，并在Issue #47、#52留存。
