# 北魏洛阳文献地图 · Luoyang Atlas

以《洛阳伽蓝记》及其校注、相关史地文献为基础的可追溯历史城市地图。
仓库：`mechgouki/luoyang-city`。几何封存基线：**v2.4**；既有研究工作线：**B1—B8**；当前研究批次：**P4.6.7 / prosperity-water-p467**（河流与水道）；首页沿用**已批准的 H2《北魏洛阳盛景全景俯瞰》**。本批发布及验收状态以[固定交接表 #52](https://github.com/mechgouki/luoyang-city/issues/52)最新记录为准。

> 盛时图采用 516—528 年河阴之变前的文献合成时层，不是某一年实测地图。文献关系画布的图形大小与显示间距不代表历史测量；来源图坐标、表列尺寸、工作朝向和未定院界分别记录，不能拼接成未经验证的精确遗址边线。

## 内容

339 条实体、179 组交互标记、11 个分区、37 张图页和 30 条争议。
网页支持 SVG 缩放、区域定位、地点检索、史料详情、争议浏览及图册下载。
原始研究数据与绘图代码仍保留在仓库；首版为无第三方运行时依赖的 HTML、CSS、JavaScript 和 SVG 静态网站。

## 当前成果与正式入口

正式网站：[mechgouki.github.io/luoyang-city](https://mechgouki.github.io/luoyang-city/)。现有GitHub Actions在main提交后自动构建、部署、验收；无需重新设置Pages。每批正式完成以对应提交的build、deploy、verify-live全部成功为准。

**P4.6.7 河流与水道**整理为[五图专题](https://mechgouki.github.io/luoyang-city/prosperity-water-p467.html)：绕城干流与城东南支、入城支渠与园池、七里涧的两种读法与调查止点、两处引洛与河渠分期、伊洛与西北来水。共53段关系，分为流向36、连接8、解释假说5、工程提议2、相邻2；数量不表示53条已定位古河道。目标时层为516—528年，旧道、已涸水体、工程提议与跨期证据分别标识。新增历史位置0、米制量测0，尚未完成全部河岸及各年通水核定。研究依据、图层边界及旧版衔接见[P4.6.7说明](docs/prosperity-water-p467-notes.md)。本地132项语义测试已通过；本地浏览器因环境拒绝socket而未能运行，PR/main CI和正式站桌面、手机、下载验收仍须以实际记录确认。

[固定交接表 #52](https://github.com/mechgouki/luoyang-city/issues/52)管理当前进度、验收状态和下一步；[研究记录 #47](https://github.com/mechgouki/luoyang-city/issues/47)保存史料、原图页码、量测依据与研究判断。存在并行会话更新时，以#52最新记录续接。

当前按用户确认的顺序持续推进盛时洛阳：文献平面 → 历史地形与定位依据 → 城市分布 → 从布局深化全景。P1把183条旧证据电子文本追溯、236处字面约束审查、申遗原图的30项几何与相同布局的鸟瞰接入[盛时工作页](https://mechgouki.github.io/luoyang-city/prosperity.html)，另提供6页图册。详见[本版说明](docs/prosperity-v1-release-notes.md)。历史地面、绝对精度与全城建筑复原仍未完成，毁后场景后置。

P2继续把3座核心建筑的表列尺度落实到[核心建筑尺度页](https://mechgouki.github.io/luoyang-city/prosperity-core.html)：宫城阊阖门基、太极殿遗址与永宁寺塔基在平面和斜视中使用相同几何；位置概略、尺寸出处与工作朝向分别说明。另提供三张局部结构图（27个部件、30条关系）、永宁院界尺寸差异校核、7页图册。院界模板没有强行落位，未知古高与屋顶没有补绘。详见[P2说明](docs/prosperity-core-v2-release-notes.md)。

P3把阊阖门从外接尺度片推进到[局部考古平面](https://mechgouki.github.io/luoyang-city/prosperity-gate.html)：依据申遗原件的门址图及其20m比例尺，逐项量读可辨的门基、通道与两阙，并提供原图叠照、尺度核对和城市接合视图。原图量读与独立表列尺寸分别保留；城市视图仍沿用P1来源锚点，不宣称已经完成实测配准。附3页图册、SVG、CSV、JSON和复现包。详见[P3说明](docs/prosperity-gate-v3-release-notes.md)与[量读方法](docs/prosperity-gate-method.md)。

首页沿用用户于2026-11-17批准的H2主图，连接历史问题、互动地图和研究资料。主图的建筑造型及构图不作为新的历史定位或尺寸证据；建筑扩绘与全景重绘留待城市骨架确定之后。见[H2批准图说明](docs/homepage-approved-v9-release-notes.md)。[H1首页说明](docs/homepage-v1-release-notes.md)保留为历史记录，其中第八版暂用稿状态已由H2批准记录接续。

| 工作线 | 内容 | 入口 |
| --- | --- | --- |
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

需要 Python 3.11+、Node.js；固定依赖与完整验收以`.github/workflows/pages.yml`为准。

```sh
python3 tools/assemble_pdf.py
python3 tools/validate_site.py
node --check app.js
node --test tests/map-interactions.test.cjs
python3 tools/build_site.py
python3 tools/research_v25.py
python3 tools/milestone_v26.py
python3 tools/link_model_points_v26.py
python3 tools/network_v27.py
python3 tools/portal_v28.py
python3 tools/chronology_v29.py
python3 tools/terrain_v30.py
python3 tools/dual_release.py
python3 tools/west_b3.py
python3 tools/historical_frame_b4.py
python3 tools/north_b4.py
python3 tools/historical_datum_b5.py
python3 tools/west_roads_b5.py
python3 tools/ground_review_b6.py
python3 tools/southeast_b6.py
python3 tools/source_continuity_b7.py
python3 tools/luonan_b7.py
python3 tools/city_review_b8.py
python3 tools/homepage_v1.py
python3 tools/prosperity_v1.py
python3 tools/prosperity_core_v2.py
python3 tools/prosperity_gate_v3.py
python3 -m unittest discover -s tests -p 'test_prosperity*.py' -v
python3 -m http.server 8000 --directory _site
```

在浏览器访问 `http://localhost:8000/`。不要直接双击 HTML。

## 文件与版本

- `data/`：网页索引和原始研究副本；地区 bbox 使用 `[x, y, width, height]`。
- `assets/`：母图与各页 SVG；母图排版变换与文献绘图坐标分别处理。
- `research/v2.4/`：原始资料、审计和模板。
- `downloads/parts/`：原始 PDF 分片；`tools/assemble_pdf.py` 合并并校验 SHA-256。
- `tools/build_site.py`：生成 `_site/`；只收录浏览网站需要的文件。
- `_site/build-info.json`：构建所用提交、记录数、坐标格式及文件校验值。
- `tests/`：区域坐标与点击／拖动回归测试。
- `research/dual-b1`至`research/dual-b6`：各批证据、解释边界和绘图决定。
- `docs/current-state-and-next.md`：当前进度与下一批；各批release-notes记录实际变化。

所有旧版入口、原始37页图册、实体ID及示意锚点保持可追溯。B4与B5各有6页图册，B6有8页；另提供证据CSV、JSON、SVG、类型图、历史图面校准、基准调查及具名地物审核复现包。真实发布门槛见`AGENTS.md`。

## 史料、许可与限制

以范祥雍《校注》为工作底本，周祖谟《校释》等参与校核；相关引文、出处、采用解释与异说见实体数据、争议目录及研究说明。转引不能自动视为独立互证，未定位对象不得自动生成历史街址。

代码与本项目复原图不能替代他人书影、图版或照片的许可。**对外复用许可证尚未确定，仓库暂不授予开放源代码许可。**第三方资料须分别核查权利与引用要求。
