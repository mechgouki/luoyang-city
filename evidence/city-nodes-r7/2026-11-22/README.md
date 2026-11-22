# R7.1 城市节点联读与 V12 导览：最终发布验收档案

**本批生产发布与正式站验收已完成。** 最终源提交为 `557c468649d6919bd249ddd891b9c97cd37cf706`，源树为 `b05e0692132f085adf9f00c3702fb095e3f06c5f`。[运行44984166317](https://github.com/mechgouki/luoyang-city/actions/runs/44984166317)的 `build`、`deploy`、`verify-live` 均为 success；完成时间为北京时间2026年11月22日12:32:14。

研究窗口保持516—528年；研究R7.1，实现city-nodes-r7.1；首页沿用已批准的 panorama-approved-v12 全幅图。

[正式首页](https://mechgouki.github.io/luoyang-city/) · [联读总览](https://mechgouki.github.io/luoyang-city/luoyang-city-nodes.html#overview) · [逐段证据](https://mechgouki.github.io/luoyang-city/luoyang-city-nodes.html#register) · [V12依据导览](https://mechgouki.github.io/luoyang-city/luoyang-city-nodes.html#panorama) · [下载](https://mechgouki.github.io/luoyang-city/luoyang-city-nodes.html#downloads)

## 成果与判断边界

交付四处节点、1张联读总览和4张局部图、32项判断与32条关系、28条来源记录的30字段证据表、V12六点依据导览。证据保留原ID并接回339项实体、84条道路来源和34项水系索引；28条记录不代表28条独立古路。

| 节点 | 已落实到图文的空间判断 | 继续保留的缺口 |
| --- | --- | --- |
| 宫前阊阖门—御道—永宁寺 | 永宁寺在宫前阊阖门南、御道西；太尉府在寺东、右卫府南有明文；“太尉府道西”另列段落解释。 | 铜驼残段与御道仅为候选对应；路段、官署院界和古里数基点不补定。 |
| 白马寺南坊门—居中纵街—中央横街 | 中央十字与南口交会分列；22米街宽、7.5米缺口、4.6米车辙带各归其对象。 | 两处间缺共同测线；86／40米量距端和逐街同期性未核同，不拼完整坊界或九个已发掘交点。 |
| 太极宫院—司马门内路—仓区 | 宫院东墙、司马门内路、宫内仓区西墙按东西次序表达；40米、4.7米、13米分别归属主路、夹道、仓区内路。 | 六根原图道路线保留断口；仓区框不当墙，宫内外仓区和168／13／3排统计口径不强行合并。 |
| 建春门—三桥—城东水道 | 三桥分别登记，东石桥保留南北桥向；527年受损仅归第一桥；渠迹、研究解释和异文分列。 | 共同桥头与古岸缺联测；汉晋暗渠不直接推为目标时段仍通水。 |

没有新增古代坐标或古岸线几何。下一批优先取得1993年外郭道路水道原刊602—608页与完整附图，再补白马寺同基准总平面和分层、司马门共同平剖面与仓区窖号图、建春门1988年位置图及2011年东阳渠／鸿池陂原刊图版、七里涧校读原页。原件缺失与历史争议没有因本次发布而被宣告解决。

## 最终正式站验收

- `final-live/live-http.json` 记录818项公开资源HTTPS与发布指纹核对通过，来源为最终557c468提交。根 `.nojekyll` 是构建控制标记，其本地字节契约与实际公开资源检查分开，未泛化忽略404。
- 最终R7桌面及手机报告均为 passed，每种设备都完成9个真实下载，以及首页入口、图文往返、筛选、深链接刷新、键盘操作、离线阅读和无脚本阅读检查。
- R4、R5、R6、R6.2、R7的10份最终报告包含72次布局测量：文档均已complete，实际超出宽度均为0，各自原0／1像素容差保留。
- `final-live-independent/` 保留39次真实HTTPS响应（38个URL）。起止build-info一致；CSV为28行30列且与JSON逐值对应；离线ZIP有13个成员，CRC及公开成员字节核对通过，含28个离线证据锚点。V12大小两幅图与已批准指纹一致。
- 44张重点PNG与同源正式构建44／44字节一致。这是字节比对，不声称逐张人工目视。另有五张完整SVG的逐图目视核查，最终公开SVG与被审查原图指纹全部一致。
- 手工网页操作记录来自已部署的9599123；之后只有测试加载前提和说明文档变更，没有产品生成器、数据、CSS或图像变更，见 `content-source-continuity.json`。最终557c468的公开UI由其本身完整生产CI验证。

49份正式站浏览器报告中，17份自带source_commit并等于最终提交；32份旧报告未记录该字段，按原字节保存，以同次工作流与原artifact关联。没有为旧报告补写其未记录的来源。

## 阶段与来源

| 目录或文件 | 证明范围与实际结果 |
| --- | --- |
| `original-pr/`、`original-live-failure/` | PR75通过；原主干ccf2453因误请求根.nojekyll而未通过正式验收。 |
| `corrected-pr/` | PR76通过：精确区分控制标记，并澄清SI02宫院墙与宫城墙。 |
| `merge-build/`、`main959-live-failure/`、`live-independent/` | 中间9599123构建、部署和HTTP通过；旧R6初始即时量宽失败。 |
| `readiness-pr/` | PR77通过：R6增加有上限的文档load前提和实际尺寸诊断。 |
| `main-d7-build/`、`main-d7-live-failure/`、`main-d7-independent/` | 中间d7cd18a构建、部署、HTTP和R6通过；相邻R6.2同类即时量宽失败。 |
| `family-readiness-pr/` | PR78通过：统一五组联读浏览器检查的加载前提，保留全部原判据。 |
| **`final-build/`、`final-live/`、`final-live-independent/`** | **唯一最终接受的557c468生产构建、正式站验收和独立HTTP原始响应。** |
| `acceptance-summary.json`、`production-workflow-run.json`、`production-workflow-jobs.json` | 最终验收汇总与GitHub真实运行／job元数据。 |
| `source-provenance.json` | PR head、实际测试merge-ref、主干提交和运行结果的区分。 |
| `full-svg-review.json`、`manual-live-ui-review.json` | 整幅静态图面与已说明来源的人工页面操作核查。 |
| `layout-family-audit.json` | 同类测试加载前提的源码审查与修改范围。 |
| `archive-index.json`、`build-archive-index.py`、`verify-remote-archive.py` | 显式归档清单、字节／SHA-256／Git blob指纹与远端Git对象回读方法。 |

所有失败记录保留其原状态。稍后的正常截图不被用来反推较早失败断言瞬间的页面状态；PR测试来源明确记为实际merge-ref，不冒充PR head。

## 长期档案的回读与交接

`archive-index.json` 列出本目录全部选定证据的精确字节与两类指纹，并排除自身以避免自指校验。最终Git提交必须按该清单逐项回读远端对象，清单本身也单独验证。实际回读结果、不可变归档提交和清单指纹登记于[Issue #52](https://github.com/mechgouki/luoyang-city/issues/52)，研究判断与原件续接登记于[Issue #47](https://github.com/mechgouki/luoyang-city/issues/47)。

归档保存所需报告、原始日志、重点PNG和选定正式HTTPS响应。大体积Actions原ZIP及临时SVG渲染PNG不重复纳入；从正式站捕获的离线下载ZIP继续保存。源代码随最终接受的main树归档，证据分支不会改变正式main或重新部署网站。
