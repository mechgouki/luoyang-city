# R8.1／V13全景候选：正式发布验收档案

2026年11月22日，项目完成依据城市证据校订的V13候选图审看页，并修复既有R7地图键盘移动后的复位偏移。**网页发布验收通过；首页主图仍是已批准的V12，V13尚未获准替换首页。**

[正式审看页：V13／V12并排对照](https://mechgouki.github.io/luoyang-city/luoyang-panorama-v13.html?view=compare#comparison) · [四节点联读](https://mechgouki.github.io/luoyang-city/luoyang-city-nodes.html) · [PR #79](https://github.com/mechgouki/luoyang-city/pull/79) · [研究记录 #47](https://github.com/mechgouki/luoyang-city/issues/47) · [固定交接 #52](https://github.com/mechgouki/luoyang-city/issues/52)

## 发布身份与结果

| 项目 | 实际记录 |
| --- | --- |
| 正式main | `fc62dd0fa439e01fbf13899fe8b9eea7f9c101f0` |
| 已审源码tree | `760adfa3f4f851213853a786e94551354d25db04` |
| PR head | `33604407bb1dd8a35336c58d6aa49143d61bcc5e` |
| PR实际测试merge-ref | `2792d5986852a87eee3ab607197c17df9a59fcfe`；tree与正式main相同 |
| PR成功运行 | [44990962140](https://github.com/mechgouki/luoyang-city/actions/runs/44990962140) |
| 正式运行 | [44991627755](https://github.com/mechgouki/luoyang-city/actions/runs/44991627755) |
| 正式三阶段 | build、deploy、verify-live全部success |
| 完成时间 | 2026-11-22 14:15:06（Asia/Shanghai） |
| 正式HTTPS核对 | 834项公开资源；根`.nojekyll`为构建控制文件，不当作已公开HTTP响应 |
| 本批页面 | `panorama-review-v13`，研究R8.1；七项图面判断、七项下载 |
| 首页状态 | `panorama-approved-v12`；`homepage_replacement_approved=false` |

完整汇总见[acceptance.json](acceptance.json)，根直接获取的最终运行／job API记录见[final-workflow-api.json](final-workflow-api.json)。

## 实际可见成果与研究边界

选用生成步骤pass02：九层主要木构塔身可以在原幅中辨读，金刹另计。保留寺院在宫前门南、御道西的方向关系与舟承浮桥，局部采用有永宁寺西墙遗存依据的浅色抹面表达；各项均区分原依据、实际成图与艺术取值。

**寺南门三重形制尚未可靠落实。** 后续三张尝试把门楼推离寺墙，均未采用；选定图保留较低门形，并在页面显著披露这项绘制欠缺。不能以发布成功宣称整幅图已经完成精确历史复原，也不能以候选页发布代替用户的首页换图批准。

1993道路水道报告已核至目录及真实阅读入口，但普通访问转入登录页；2011东阳渠、鸿池陂简报新增2024文集及馆藏线索，尚未核得目标篇的重印正文或完整附图。本轮该项续查新增原刊页、完整原图、古代坐标及古岸几何均为0。2022运河报告仍按既定决定暂缓。

原PNG的SHA-256为`1808eeb9c2a25a2c22777ae8fba7ae437c983b091de5674b094d10e47cb1c0b1`；网页全幅图为`ddded211c38b2c27e2268c74d22a9151f861ac335e90118c5d244a2effbb9a78`。原PNG为1671×941，手机版为960×541。此前所有草案及拒绝理由见正式源码中的`research/panorama-r8/generation-prompts.txt`与`image-record.json`。

## 读者操作与真实下载

PR、正式main构建、正式站三组原始报告分别保留。各组R7桌面／手机均完成八组操作检查和九项真实下载，复位均从`(40,40)`回到`(0,0)`。各组V13桌面／手机均完成五组操作检查、七项真实下载及无脚本检查；每端记录七次布局测量。正式站所有R7、V13下载SHA-256与main构建对应报告逐项一致，相关页面错误数组均为空。

V13桌面候选图实际1671×941，手机版实际960×541，均按自然比例显示。独立四截图目检见[root-review/pr-visual-review.json](root-review/pr-visual-review.json)。根人工核对正式首页入口、图像切换、并排、刷新恢复、宫前证据跳转、寺门限制与返回对照，见[root-review/live-browser-review.json](root-review/live-browser-review.json)。该人工记录捕获时自动验收尚在运行，其时间边界完整保留；本页汇总采用后来实际完成的正式运行。

根另外直接获取31个HTTPS响应，涉及30个不同URL，原字节保存于[root-review/production/http-responses](root-review/production/http-responses)。开闭两次build-info完全一致；七个新下载、V12固定图像指纹与R7四节点／28段记录均核对通过。详见[http-capture.json](root-review/production/http-capture.json)及可复用采集脚本。

## 证据分层

| 目录 | 性质与适用范围 |
| --- | --- |
| `local-preflight/` | 本机Python3.12、借用d334来源旧_site的局部预验；保留缺rasterio的实际失败，不能代替完整CI |
| `pr-failed-44990398220/` | 第一次PR失败原始报告／日志：R7手机复位偏移7→31，V13浏览器尚未执行 |
| `pr/` | 修复后PR成功运行，实际测试提交2792d598…；原始报告与截图 |
| `main-build/` | 正式main构建与浏览器成功产物；捕获时run尚在进行的状态原样保留 |
| `main-live/` | 实际正式站HTTPS及桌面／手机浏览器产物、最终运行元数据和日志 |
| `root-review/` | 独立HTTP原字节、人工浏览器观察与四截图静态目检记录 |

首次失败的旧断言已轮询五秒仍未归零。本轮修复仅将地图容器自身、无修饰键的四方向键改为即时步进，复位即时归零；SVG链接键盘行为保留。原有横向归零断言保留，并增加纵向归零、焦点、截图后再次检查。没有用忽略失败或扩大容差换取通过。R7研究记录与图面几何不因这一运行交互修复而改变；相应运行脚本和离线包确有更新。

Actions ZIP只是临时取证来源，文件指纹与GitHub artifact digest核对后，所需JSON、日志和原始PNG按原字节留存；没有重新生成截图冒充CI结果。现代论文正文、登录页面与签名下载参数不在本档案内。上一R7.1验收仍可查[独立历史档案](https://github.com/mechgouki/luoyang-city/blob/637dd943fee13a30ca754cdd3d97c85bb8adc8b9/evidence/city-nodes-r7/2026-11-22/README.md)。

## 如何复核本档案

`archive-index.json`列出各内容文件的bytes、SHA-256及Git blob SHA；索引不自我哈希。`verify-remote-archive.py`读取已经fetch的不可变Git提交，核对本目录完整路径集、每项原字节与索引自身字节。最终远端回读的提交SHA、文件数与结果记录在#52本次交接中，避免让档案预先声称自己的未来提交已获验证。
