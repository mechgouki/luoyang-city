# R6.2 全城道路：正式验收与长期证据

本批已完成发布与正式站验收。研究时段 **516—528年**，研究版本 **R6.2**，专题版本 **all-road-atlas-r6.2**。发布提交 `0f5904a109751e5a24ab0d0c95592362f1e26c94`，来自 [PR #73](https://github.com/mechgouki/luoyang-city/pull/73)。首页继续使用用户选定的 **07号 / panorama-approved-v11**。

## 正式成果

[全城道路总览](https://mechgouki.github.io/luoyang-city/luoyang-all-roads.html) · [总图SVG](https://mechgouki.github.io/luoyang-city/all-roads/city-all-roads.svg) · [84行逐路CSV](https://mechgouki.github.io/luoyang-city/all-roads/records.csv) · [完整JSON](https://mechgouki.github.io/luoyang-city/all-roads/records.json) · [339行覆盖CSV](https://mechgouki.github.io/luoyang-city/all-roads/coverage.csv) · [manifest](https://mechgouki.github.io/luoyang-city/all-roads/manifest.json) · [离线ZIP](https://mechgouki.github.io/luoyang-city/downloads/luoyang-all-roads.zip)。

84项为证据记录：旧来源21、文献26、宫路11、坊街证据7、门道14、桥道5。原339实体、100条含道路定位词的主引文均有覆盖去向，保存60条对应关系和13项排除／参照。六条白马寺坊街与一条未分条集合分别登记；记录数不作为独立古街总数。

## 已完成的检查

- [最终PR运行44892508146](https://github.com/mechgouki/luoyang-city/actions/runs/44892508146)成功：固定Python3.11环境218项研究回归、6项首页测试、整站浏览器回归通过。
- [正式运行44893240321](https://github.com/mechgouki/luoyang-city/actions/runs/44893240321)的build、deploy、verify-live全部success；最终完成于 **2026-11-21 18:28:47（北京时间）**，原始UTC时间保留于工作流记录。
- PR实际测试源为 `bdd8cf493d810659e31cb276ea21af9a83b5fda9`；其Git树与发布提交均为 `0566c278e063b8b2607e5a2bb7dd3a6ee115efed`，已经实际读取比对。
- 正式HTTP校验795项公开资源；另行独立HTTPS读取27项不同资源、共28次响应，首尾build-info相同，提交对应生产版本。
- 1440×960桌面与390×844手机均实测类别和编号检索、筛选恢复、深链接、图层、缩放、横移、每端6次实际下载、断网离线包和无JavaScript阅读。每端7项检查均通过，无浏览器运行错误。
- 八张最终PR道路截图与已逐张人工审阅的图像相同，八张正式站截图又与最终PR图像逐字节一致；16张原始截图全部保存。具体SHA-256比较见acceptance-summary.json。
- 正式浏览器六项下载哈希、正式HTTP报告与独立HTTPS读取三者一致。PR JSON／manifest／ZIP带PR自身提交标识，按各自阶段检验，不要求跨提交字节相同。
- 两个正式首页入口均保留07号v11，原R6.1记录和入口、旧专题与下载回归通过。

## 目录与来源绑定

- `pr/`：最终PR的15件原始证据、采集元数据和SHA256SUMS。初次PR运行不充作最终验收。
- `live/`：正式站14件原始证据、采集元数据和SHA256SUMS，含完整795项资源报告。
- `production/`：独立HTTPS报告、响应索引与首尾build-info原字节。索引中的其他原响应文件保存在会话工作区；此长期副本保存其实际哈希，不伪造或重建未归档响应体。
- `local/`：研究复核、CSV实际导入、指针清点和本地准备记录。Python3.12完整研究回归为216/218，两处旧冻结数值指纹差异如实保留；最终门槛是固定Python3.11的218/218成功。
- `tools/`：原始证据采集与独立HTTPS回读脚本。
- `github-workflows.json`：实际运行／作业／步骤结论、提交和Git树、artifact编号、摘要及到期日。
- `acceptance-summary.json`：版本、统计、检查结果、截图比较和研究限制。
- 根目录`SHA256SUMS`覆盖本目录全部文件，除清单自身。

阶段evidence-metadata中的workflow_conclusion保持null：采集脚本只验证归档材料，实际GitHub成功结论由根部github-workflows.json记录。`homepage-approved-v9`是沿用的历史测试目录／文件名，其中本次检查的实际首页仍为 **07 / panorama-approved-v11**。

原PR artifact `14703031842` 到期于 `2026-12-05T10:11:40Z`；正式artifact `14703660216` 到期于 `2026-12-21T10:28:40Z`。本分支留存必要报告和截图，不依赖临时artifact持续存在。

## 研究边界与下一原件

来源图之间不做无据配准，不补原路断点，不新增古道路坐标或516—528岸线。永巷箭杆属于原图方向示意；坊街符号不组成实测网格；宫路、门道及桥道的期段、局部量值和未知端点分别保留。W01—W34沿用原等级，永桥两岸登陆点继续未知。

下一首要原件仍为1993年《北魏洛阳外廓城和水道的勘查》602—608页及不裁边的完整附图，连同比例尺、图例和边注核对实测线、推定线、探孔和最后路土点。维普1002554709；知网KAGU199307004／CJFD9093。2022年运河报告暂缓，毁后洛阳后置。
