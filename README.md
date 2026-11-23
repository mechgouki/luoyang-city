# 北魏洛阳文献地图 · Luoyang Atlas

以《洛阳伽蓝记》及其校注、相关史地文献为基础的可追溯历史城市地图。
仓库：`mechgouki/luoyang-city`；既有研究工作线：**B1—B8**。

<!-- current-state:start -->
当前状态（2026-11-23）：研究 **R12.1 / panorama-review-v14**（共同透视底稿与试绘审查（试绘未通过））；首页为用户批准的 **全幅取景版 `panorama-approved-v12`**；几何封存基线 **v2.4**。研究时段为 **516—528 年**。

[正式首页](https://mechgouki.github.io/luoyang-city/) · [现行研究入口](https://mechgouki.github.io/luoyang-city/luoyang-panorama-v14.html) · [上一已验收发布 `129abae`](https://github.com/mechgouki/luoyang-city/actions/runs/45103224890) · [长期验收证据](https://github.com/mechgouki/luoyang-city/blob/b276f8e9495be7d4e8a38ddfa65ffc2bf9e85611/evidence/city-plan-r11/2026-11-23/README.md) · [最新交接 #52](https://github.com/mechgouki/luoyang-city/issues/52)。

以上摘要由[当前状态登记](research/current-state.json)生成。首页、研究批次和封存底图的版本分别理解；旧批次中的 V9／V11 与旧进度仅为历史记录。新一批正式完成仍以对应发布提交的构建、部署与正式站验收为准。
<!-- current-state:end -->

> 盛时图采用 516—528 年河阴之变前的文献合成时层，不是某一年实测地图。文献关系画布的图形大小与显示间距不代表历史测量；来源图坐标、表列尺寸、工作朝向和未定院界分别记录，不能拼接成未经验证的精确遗址边线。

## 内容

339 条实体、179 组交互标记、11 个分区、37 张图页和 30 条争议。
网页支持 SVG 缩放、区域定位、地点检索、史料详情、争议浏览及图册下载。
原始研究数据与绘图代码仍保留在仓库；首版为无第三方运行时依赖的 HTML、CSS、JavaScript 和 SVG 静态网站。

## 当前成果与正式入口

正式网站：[mechgouki.github.io/luoyang-city](https://mechgouki.github.io/luoyang-city/)。现有GitHub Actions在main提交后自动构建、部署、验收；无需重新设置Pages。每批正式完成以对应提交的build、deploy、verify-live全部成功为准。

**R12.1 共同透视底稿与试绘审查：底稿已形成，全景校正尚未完成。** 本轮将 R11 的来源几何送入同一个可复算的地面透视，形成全城总览、永宁寺局部底稿、计层示意与逐项依据／偏差对照。V14 主显示保留第五次未通过试绘：南门层数、门基与寺墙位置、佛殿和塔座尺度及宫城关系仍有未解决问题；追加试绘单独留存，不覆盖该张的审查档案。[R12 审查页](https://mechgouki.github.io/luoyang-city/luoyang-panorama-v14.html)的技术发布与图像视觉通过分别判断，当前不预先宣告上线验收，实际发布状态见[#52](https://github.com/mechgouki/luoyang-city/issues/52)。[透视方法](docs/panorama-r12-projection.md)与[审查状态说明](docs/panorama-v14.md)保留候选绑定和艺术高度的边界；首页继续采用已批准 V12，V13 二修原样保留。

**R11.1 全城统一坐标复原工作平面**提供[可回查的共同母图](https://mechgouki.github.io/luoyang-city/luoyang-city-plan.html)：保留28项来源骨架，接入阊阖门与永宁寺33项局部原图构件、4个有据尺度片、独立可切换的2013宫城刊图24项对照要素，以及148个文献候选位置签。全城、局部和十一片区共16个取景使用同一几何，附17页矢量PDF、4份CSV、完整JSON与离线包。339项目录逐项交代，165项仍保留未定位；共同绘图坐标不等于完成全城实测配准或每栋建筑的真实轮廓。[研究范围与依据](docs/city-plan-r11-research.md)。首页图像继续V12，正式发布与长期验收见#52。

**R10.1 全城总平面与十一片区布局系统深化**把来源总图与各区内部关系接入[城市布局图集](https://mechgouki.github.io/luoyang-city/luoyang-city-layout.html)。全城图保留28项古迹来源几何与既有缺口；十一片区分别展开方位、通行次序、成员归属和沿革，不把无序名录画成街坊坐标。339个原对象、84条道路证据和34项水系索引均保留完整去向，提供逐项“空间判断—依据—图面变化”、16页PDF、12张SVG、4份CSV及离线包。[本轮研究与完成范围](docs/city-layout-r10-research.md)。首页继续使用V12，全景候选保留V13二修；新增古代坐标、古岸和定位等级提升均为0。正式上线及长期验收证据以#52的本轮交接为准。

**R6.2 全城道路总览**把现有材料一次收齐：[道路总图与逐路表](https://mechgouki.github.io/luoyang-city/luoyang-all-roads.html)，共84条证据记录（旧主干道来源21、文献道路26、宫路11、坊街证据7、门道14、桥道5），覆盖339个原实体和100条道路定位主引文；记录数不是独立古代道路数。六条坊街与未分条集合分别计数，来源图、推定连接和未知端点分别表示，保留全部原图框与分期限制。附CSV、JSON、覆盖表、SVG和离线包；[研究说明](docs/roads-r62-research.md)，实际发布与验收状态见#52。R6.1的[21条主干道来源图](https://mechgouki.github.io/luoyang-city/luoyang-road-atlas.html)继续保留。

**P4.6.8 城壕、宫西水道与独立园池**补入[五图专题](https://mechgouki.github.io/luoyang-city/prosperity-water-p468.html)：城西排水与内城壕沟、宫西水道、两处方湖与昭仪池、独立园池、宫苑池逐项复核。补核12个前册保留对象并重核5个池名；W20濛汜池／W21碧海曲池撤回I09旧索引，P467前页显示勘误。九行原典／报告数值区分宽度、残长、埋深和淤积语义。相邻、包含、层位不作水流，报告值不计为本项目新增图测。研究与未定项见[P4.6.8说明](docs/prosperity-water-p468-notes.md)，实际发布与验收状态以#52为准。

**P4.6.7 河流与水道**整理为[五图专题](https://mechgouki.github.io/luoyang-city/prosperity-water-p467.html)：绕城干流与城东南支、入城支渠与园池、七里涧的两种读法与调查止点、两处引洛与河渠分期、伊洛与西北来水。共53段关系，分为流向36、连接8、解释假说5、工程提议2、相邻2；数量不表示53条已定位古河道。目标时层为516—528年，旧道、已涸水体、工程提议与跨期证据分别标识。新增历史位置0、米制量测0，尚未完成全部河岸及各年通水核定。研究依据、图层边界及旧版衔接见[P4.6.7说明](docs/prosperity-water-p467-notes.md)。已由[发布提交e6d0aae](https://github.com/mechgouki/luoyang-city/commit/e6d0aaec76b5d25ed347f377ce19d7361b47f9a2)完成正式站验收，674项公网资源及桌面／手机／下载均通过；[长期验收副本](https://github.com/mechgouki/luoyang-city/tree/54bc53f53a95f0390c5f3c8fd181c6e070e16623/evidence/p467)已保存。

[固定交接表 #52](https://github.com/mechgouki/luoyang-city/issues/52)管理当前进度、验收状态和下一步；[研究记录 #47](https://github.com/mechgouki/luoyang-city/issues/47)保存史料、原图页码、量测依据与研究判断。存在并行会话更新时，以#52最新记录续接。

当前按用户确认的顺序持续推进盛时洛阳：文献平面 → 历史地形与定位依据 → 城市分布 → 从布局深化全景。P1把183条旧证据电子文本追溯、236处字面约束审查、申遗原图的30项几何与相同布局的鸟瞰接入[盛时工作页](https://mechgouki.github.io/luoyang-city/prosperity.html)，另提供6页图册。详见[本版说明](docs/prosperity-v1-release-notes.md)。历史地面、绝对精度与全城建筑复原仍未完成，毁后场景后置。

P2继续把3座核心建筑的表列尺度落实到[核心建筑尺度页](https://mechgouki.github.io/luoyang-city/prosperity-core.html)：宫城阊阖门基、太极殿遗址与永宁寺塔基在平面和斜视中使用相同几何；位置概略、尺寸出处与工作朝向分别说明。另提供三张局部结构图（27个部件、30条关系）、永宁院界尺寸差异校核、7页图册。院界模板没有强行落位，未知古高与屋顶没有补绘。详见[P2说明](docs/prosperity-core-v2-release-notes.md)。

P3把阊阖门从外接尺度片推进到[局部考古平面](https://mechgouki.github.io/luoyang-city/prosperity-gate.html)：依据申遗原件的门址图及其20m比例尺，逐项量读可辨的门基、通道与两阙，并提供原图叠照、尺度核对和城市接合视图。原图量读与独立表列尺寸分别保留；城市视图仍沿用P1来源锚点，不宣称已经完成实测配准。附3页图册、SVG、CSV、JSON和复现包。详见[P3说明](docs/prosperity-gate-v3-release-notes.md)与[量读方法](docs/prosperity-gate-method.md)。

首页采用2026-11-21用户明确批准的「全幅取景版」`panorama-approved-v12`，依据本轮道路、水系成果，在原07号构图上提高视点、后撤取景；桌面、平板和手机均整图等比展示，标题和图注放在图下。此前07号 `panorama-approved-v11`及[PR #71](https://github.com/mechgouki/luoyang-city/pull/71)的更正记录继续保留，不与本次新图混同。R4城市总图、R5全景、R5.3司马门道路与R6.2全城道路已交付，主页画面的建筑造型与构图不作为历史定位或量测依据。详见[本次首页变更说明](docs/homepage-full-frame-v12-release-notes.md)。

| 工作线 | 内容 | 入口 |
| --- | --- | --- |
| 盛时R11.1 | 全城统一坐标母图、三组原图来源、十一片区同坐标取景、339项去向与302条关系、17页图册 | [全城复原工作平面](https://mechgouki.github.io/luoyang-city/luoyang-city-plan.html) |
| 盛时R10.1 | 全城总平面、十一片区深化、339对象与118条路水记录覆盖、逐项依据和16页图册 | [城市布局图集](https://mechgouki.github.io/luoyang-city/luoyang-city-layout.html) |
| 盛时R6.2 | 84条道路、门道与桥道证据，339实体覆盖核对；分级图、逐路表、离线包 | [全城道路总览](https://mechgouki.github.io/luoyang-city/luoyang-all-roads.html) |
| 盛时R6.1 | 原有21条主干道来源与三处接续专题 | [主干道来源图](https://mechgouki.github.io/luoyang-city/luoyang-road-atlas.html) |
| 盛时R5 | 城市全景与司马门内道路专题 | [全景](https://mechgouki.github.io/luoyang-city/prosperity-city-panorama.html) |
| 盛时R4 | 城市分布及定位依据 | [城市总图](https://mechgouki.github.io/luoyang-city/prosperity-city-atlas.html) |
| 盛时P4.6.8 | 城壕、宫西水道与园池五图47段；补核12项、重核5项，含I09索引勘误及9行原值，发布状态见#52 | [水系补遗](https://mechgouki.github.io/luoyang-city/prosperity-water-p468.html) |
| 盛时P4.6.7 | 五图、53段河流与水道关系，七里涧两种校读与分期；发布状态见#52 | [河流与水道](https://mechgouki.github.io/luoyang-city/prosperity-water-p467.html) |
| 盛时P4.6.6 | 城南两条大道、谷水与永桥；旧PDF封存 | [城南道路与水系](https://mechgouki.github.io/luoyang-city/prosperity-south-p466.html) |
| 盛时P3 | 阊阖门局部平面、原图叠照、尺度核对与城市接合诊断 | [阊阖门平面](https://mechgouki.github.io/luoyang-city/prosperity-gate.html) |
| 盛时P2 | 3座核心尺度片、3张局部结构图、院界尺寸校核 | [核心建筑尺度](https://mechgouki.github.io/luoyang-city/prosperity-core.html) |
| 盛时P1 | 文献审校、来源图城市骨架、布局鸟瞰；339地点与30来源要素分开阅读 | [盛时工作页](https://mechgouki.github.io/luoyang-city/prosperity.html) |
| B1 | 宫前—永宁—景乐、建春两桥、景明—汉国子学堂—石经 | [B1](https://mechgouki.github.io/luoyang-city/dual-b1.html) |
| 宫苑B2 | 宫苑、瑶光、景阳山及地下水系条件 | [B2](https://mechgouki.github.io/luoyang-city/dual-b2.html) |
| 城西B3 | 大市、四向八里、皇女台、寿丘与王宅 | [B3](https://mechgouki.github.io/luoyang-city/dual-west.html) |
| 北门B4 | 两门、寺园、闻义里、承明—金墉；16条证据、4组类型调整 | [B4](https://mechgouki.github.io/luoyang-city/dual-north.html) |
| 城西门道B5 | 三门道、寺序约束、宅寺时层；24条证据、11组类型调整 | [B5](https://mechgouki.github.io/luoyang-city/dual-west-roads.html) |
| 城东南B6 | R08门内与R09门外；34条证据、20组类型调整、8页图册 | [B6](https://mechgouki.github.io/luoyang-city/dual-southeast.html) |
| 洛南B7 | 四馆四里、市场与永桥通行、25条记录 | [B7](https://mechgouki.github.io/luoyang-city/dual-luonan.html) |
| 全城B8 | 339项结构关联、14个跨批审校案例与图源追查 | [B8](https://mechgouki.github.io/luoyang-city/dual-city-review.html) |
| 现代地形 | 真实DSM、山影、坡度、等高线、两幅AMS原图 | [地形](https://mechgouki.github.io/luoyang-city/v3.0.html) |
| 历史图面B4 | 26个印刷格网交点；每幅8拟合、5内部留出 | [图面校准](https://mechgouki.github.io/luoyang-city/historical-frame.html) |
| 历史基准B5 | 两幅原图14张边栏裁片、原馆数字化记录；原纸图基准仍未识别 | [基准调查](https://mechgouki.github.io/luoyang-city/historical-datum.html) |
| 地物与来源B6 | 白马寺区域、黄河铁路桥具名审核；L531原图1946印次与编图链 | [地物审核](https://mechgouki.github.io/luoyang-city/ground-review.html) |

当前状态及后续顺序见 [docs/current-state-and-next.md](docs/current-state-and-next.md)。旧`project-plan.md`、`resume-review.md`保留历史阶段记录，不能以其中旧部署状态判断今天的进度。`release.json`主版本族保持`v3.0-dual.b2`，后续批次由`extensions`和`current_milestone`登记。

现代DSM不是北魏裸地；历史扫描图的同图格网残差不是地面精度。哈佛2005年赋予的WGS_1984是数字化工作定义，不能反推原纸图水平基准。当前未把文献像素或现代高点转换成古址经纬度。

## 本地构建

需要 **Python 3.11**、Node.js，以及[生产流程](.github/workflows/pages.yml)列明的固定依赖和 Noto Sans CJK SC 字体。请使用 Python 3.11 创建的环境，与 CI 保持一致；其他 Python 版本的浮点输出可能改变受保护 SVG 的字节校验值，因此完整构建入口会先检查运行版本。完整构建顺序集中在 `tools/build_all.py`；README 与 CI 共用这一入口。

```sh
python3.11 tools/build_all.py
python3.11 tools/validate_site.py
node --test tests/map-interactions.test.cjs
python3.11 -m unittest discover -s tests -p 'test_prosperity*.py' -v
python3.11 -m http.server 8000 --directory _site
```

在浏览器访问 `http://localhost:8000/`。不要直接双击 HTML。`python3 tools/build_all.py --list` 可在其他 Python 版本下查看完整顺序；构建不替代正式流程里的数据、语义、桌面／手机与线上验收。CI 在原有预检之前执行 `--prepare-only`，预检之后执行 `--site-only`，保留原来的阶段先后。

构建入口保留 CI 已提供的 `GITHUB_SHA`；本地默认读取当前 Git HEAD 的完整提交号。若使用不含 Git 元数据的源码副本，须通过 `--source-commit` 提供其完整40位来源提交号，供各批保护契约使用。

当前状态只在 `research/current-state.json` 登记；修改后运行 `python3 tools/current_state.py --write` 同步 README 与续接文档的当前摘要。`--check` 可验证摘要是否一致，不改写历史批次说明。

## 文件与版本

- `data/`：网页索引和原始研究副本；地区 bbox 使用 `[x, y, width, height]`。
- `assets/`：母图与各页 SVG；母图排版变换与文献绘图坐标分别处理。
- `research/v2.4/`：原始资料、审计和模板。
- `downloads/parts/`：原始 PDF 分片；`tools/assemble_pdf.py` 合并并校验 SHA-256。
- `tools/build_all.py`：当前完整构建入口；调用各历史阶段并保持原顺序。
- `tools/build_site.py`：生成最初的 `_site/`，后续阶段继续加入研究与专题。
- `research/current-state.json`：当前研究、首页、封存基线及上一已验收发布指针。
- `_site/build-info.json`：构建所用提交、记录数、坐标格式及文件校验值。
- `tests/`：区域坐标与点击／拖动回归测试。
- `research/dual-b1`至`research/dual-b6`：各批证据、解释边界和绘图决定。
- `docs/current-state-and-next.md`：当前进度与下一批；各批release-notes记录实际变化。

所有旧版入口、原始37页图册、实体ID及示意锚点保持可追溯。B4与B5各有6页图册，B6有8页；另提供证据CSV、JSON、SVG、类型图、历史图面校准、基准调查及具名地物审核复现包。真实发布门槛见`AGENTS.md`。

## 史料、许可与限制

以范祥雍《校注》为工作底本，周祖谟《校释》等参与校核；相关引文、出处、采用解释与异说见实体数据、争议目录及研究说明。转引不能自动视为独立互证，未定位对象不得自动生成历史街址。

代码与本项目复原图不能替代他人书影、图版或照片的许可。**对外复用许可证尚未确定，仓库暂不授予开放源代码许可。**第三方资料须分别核查权利与引用要求。
