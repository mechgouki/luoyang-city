# P2核心建筑局部结构：阊阖门与永宁寺

核读日期：2026-11-14。交付：[core-relations.json](../research/prosperity-v2/core-relations.json)。

本轮已经形成三套可以直接绘制的独立局部结构数据：**宫城阊阖门、永宁寺院内联系、永宁塔基**，合计27个部件节点、30条关系。数据为地图新增可阅读、可点选的局部结构；不是把上轮待办换一种方式列出。新节点只属于局部图，不写入原339实体名录，不改变P1地理坐标或封存图。

## 一、本轮实际可以增加的地图内容

| 场景 | 相比单一图符新增的可画结构 | 主要依据 | 本轮可用精度 |
|---|---|---|---|
| 宫城阊阖门 | 主门基内的西、中、东三通道；东西两阙；西侧1号院、东侧2号院和北侧3、4号院；门区与阙区之间两侧基址连接 | 申遗PDF1962／附录37的下方平剖图 | 部件、次序、相对方向与基址接续；不提供廊宽、柱距或精确折线 |
| 永宁寺院内 | 塔北佛殿；四门分别标示南门三重、东西门两重、北门不施屋；僧房楼观另作非定位目录 | PDF1965／附录40上图，伽蓝记卷一相关正文 | 塔—佛殿南北关系和四门侧别；门的沿墙位置与各院内距离仍未测 |
| 永宁塔基 | 中央土坯塔心；环绕构造／柱位证据组；四向慢道 | PDF1966／附录41的塔基平剖图 | 塔心、环绕关系、四向外接慢道；没有逐柱位置、坡度或完整环廊尺度 |

这三套数据的部件和关系均已落盘。页面可以直接生成三张局部图，并将阊阖门部件连接到既有`ic_changhe_palace`，永宁两图连接到既有`ic_yongning`。

## 二、图版能读到什么，不能精确描到什么

实际检查了PDF整页及其**原始内嵌图像**，没有以放大显示冒称增加分辨率。

| 图版 | 内嵌图原生尺寸 | 本轮目读结果与限制 |
|---|---:|---|
| [PDF1962，附录37，下图](https://whc.unesco.org/uploads/nominations/1442.pdf#page=1962) | 555×434像素 | 有北箭、20m比例尺、三通道和院阙标签。可读局部拓扑；未测角度、廊宽、柱距或完整边线。北箭不等于图面竖直就是精确真北 |
| [PDF1965，附录40，上图](https://whc.unesco.org/uploads/nominations/1442.pdf#page=1965) | 555×569像素 | 可见塔、佛殿、西门、东门及南门标签；南部有源图灰带遮挡。未见可读北箭，不从同页下图借北箭 |
| PDF1965，附录40，下方西门图 | 507×302像素 | 北箭朝图面右；实测基槽边缘和复原线须区分。不能据此镜像复制东门 |
| [PDF1966，附录41，塔基图](https://whc.unesco.org/uploads/nominations/1442.pdf#page=1966) | 554×672像素 | 有略向左上北箭与5m比例尺；塔心、外围构造与四向慢道可读。下方局部有灰带，不开展精确柱位或边界量测 |

图像哈希、PDF页码、内嵌图序号与查看规则均保存在数据`sources`中。图源只作为核读依据，本文件未重新分发整张原图。

“有比例尺”并不等于本轮完成了测绘。当前图版足以立即绘制有依据的**局部关系结构**，但不支持宣称已经取得精确局部建筑平面或可直接投到地理地图的足迹。

## 三、宫城阊阖门：三通道与院阙结构

### 可直接绘制

图37中央门基内明确标有西间道、中间道、东间道，可以把既有门基图符拆成三条可点通道，保留西—中—东次序。图中两阙有明确标签，位于主门基图示南侧两翼。西侧1号院、东侧2号院及其北面的3、4号院可以分别作为阅读区标出。

门区两侧与相应阙区之间存在可读的着色基址／边界接续。本轮用**“西侧基址连接”“东侧基址连接”**表达，并保存门基到阙区的结构联系；不把这些条带全部命名为已证有顶廊道，也不将关系线解释为精确步行路线。

[附表PDF1927／附录2，Cgm-3](https://whc.unesco.org/uploads/nominations/1442.pdf#page=1927)所记44.5m东西、24.4m南北仅赋给**主门基**。两阙、四院和连接基址的完整包络、尺寸仍为空，不把门基矩形套到整个门阙群。

### 不补绘

图中的粗黑外框包含探方、剖面或图框性质，不能一律闭合成院墙。两阙下方另标地下基础夯土，不能与地上范围合并成同一条建筑边界。未核出每段廊宽、每柱位置、门楼层数、阙楼高度、屋顶、瓦作和确切立面，这些均不生成。

## 四、永宁寺：塔北佛殿与四门差异

### 塔与佛殿

[周本卷一](https://deerpark.app/cbeta/B0077/1)B12n0077_p0047a04明确记：

> 浮圖北有佛殿一所，形如太極殿。

图40亦可见佛殿基址位于塔图示上方。本轮保存“佛殿在塔北”，但**不附加共轴、距离或同一基座尺寸**。附表PDF1931／附录6的佛殿条目仍称形状、结构尺度未清；“形如太极殿”不能使佛殿获得太极约100×60m的尺度。因此佛殿使用未知尺寸标签图符，不画一个貌似测得的殿基矩形。

塔的九层木构为文献陈述。已有塔基方形遗存边长约38.2m可以继续进入尺寸说明，2.2m只作为遗存残高。九十丈等历史高度说法不转换为本轮米制体块高。

### 四门区别

周本p0048a12—13记四面各开一门，可作为四个侧别关系。图40直接可读西、东及南门标签；北门在这幅缩图中未见清楚独立平面，北门类型由古文支持。

| 门 | 可显示的本轮依据 | 保持未知的部分 |
|---|---|---|
| 南门 | 文献“楼三重”；图版有南门标签，既有附表列长45.5m、宽19.1m、残高1.2m | 沿墙位置、长宽轴向、底层孔道数量、原高与屋顶 |
| 西门 | 文献楼两重；图版西侧标签，附表列东西18.2m、南北外侧24m／内侧30m | 未按原图完成的不规则平面、沿墙距离、原高与屋顶 |
| 东门 | 文献楼两重；图版东侧标签 | 尺寸空白，不镜像西门生成足迹 |
| 北门 | 文献“一道”“不施屋”“似乌头门” | 图版没有提供可量独立基址；不开出假精确门宽，不加楼屋 |

南门还有一个重要读法边界：[周本](https://deerpark.app/cbeta/B0077/1)p0048a13—15作“通三閣道”，[范本](https://deerpark.app/cbeta/B0078/1)p0343a10—12作“通三道”。本轮保留两读，不把它自动变成三个已考古确认的地面门孔。数据中南门`ground_passage_count`保持`null`；与图37明确三通道的宫城阊阖门严格分开。

北门`roof_present=false`仅表示原文“不施屋”这一类型限制，不意味着其他尺寸或构件都已测明。

### 僧房与院墙

周本p0047a09—10的“僧房樓觀，一千餘間”是合计叙述，未给逐栋分布。数据把它放入`unlocated_catalogue`，作为地图旁的非定位构件目录，不能把卡片所在的屏幕左侧解释成寺西院落，也不展开为一千个等大单元。

院框使用已有301×212m范围说明，作为关系容器；本图不宣称四边均已精确描出。短椽瓦覆墙顶可显示为文字类型，不能据此生成确定墙高、坡角、瓦式或完整院墙立面。

## 五、永宁塔基：从方形标记增加到结构联系

图41明确标出中央土坯塔心、外围构造及柱位符号，四向各有一处慢道／Slopeway标注。本轮提供：

- 一个塔基遗存范围节点，继续关联约38.2m方形的来源尺度；
- 一个中央塔心节点，其真实边界与大小为空；
- 一个环绕构造／柱位证据组，用断续或虚线表达围绕关系；
- 北、南、西、东四处慢道节点，分别连接台基相应侧，长度、宽度、坡度与方位角均为空。

这些可以立即改变局部图的结构，而不需要编造塔身高度。外围柱位不逐个数点、不补齐整齐网格，也不把“环绕”升级为完整环廊。

图中北、南破坏带明确标“破坏沟／Destroyed Canal”。它们作为损坏观察保留，**不进入盛时水渠或排水系统**。图版没有给出成沟确年，本轮也不额外断言它属于哪次现代工程。

## 六、供渲染器使用的数据契约

顶层结构为`sources`、`evidence`、`scenes`。三个场景ID分别是：

- `changhe_gate_complex`
- `yongning_compound`
- `yongning_pagoda_base`

每个场景给定`viewBox`、`nodes`、`relations`和具体`rendering_guidance`。节点ID是新局部图的部件ID，不是对古城实体名录新增登记。

节点的`diagram_layout`使用左上角`x/y`及`width/height`，单位为`editorial_canvas`，只用于排版；`shape`用于区分实测尺度说明、未知尺寸标签、虚边阅读区、门符号、非定位目录等。凡未经测量的真实位置和形状统一保存：

```json
{
  "measured_plan_xy_m": null,
  "geographic_coordinates": null,
  "footprint_geometry_m": null,
  "historical_height_m": null,
  "roof_model": null
}
```

关系使用`subject/relation/object`，并给出`evidence_refs`、`source_refs`、`display_label`。距离和精确方位角为空。图上需要等宽通道、对齐文字或规则院区框时，应显示为关系图的排版选择，不把这些像素数导出为古代米数。

建议优先使用如下视觉语义：

| 数据类型 | 推荐显示 | 不应表现为 |
|---|---|---|
| `passage` | 三条独立通道符号，标西／中／东 | 已测门洞宽度与开间 |
| `courtyard_reading_area` | 虚边院区阅读框 | 完整已发掘院墙 |
| `foundation_connection` | 细线或浅色基址连接，标签明确 | 有顶廊立面或精确通行路线 |
| `unmeasured_building` | 未定尺寸的文字／类型标记 | 看似按比例的殿基 |
| `nonspatial_component_group` | 图外非定位构件目录 | 沿屏幕方位确定的建筑群 |
| `surrounding_structural_evidence` | 断续围绕提示、构造组 | 完整环廊、等距柱网 |
| `ramp` | 四向连接符号 | 已量坡度、坡长与标高 |

## 七、核查范围与完成度

本轮完成9条图版观察与7条古文短引。古文重新对照已取得的电子正文，并记录匹配位置；南门周、范读法分列。图版观察由原始内嵌图确认，额外做了一次独立只读复核，结果一致：三通道、院阙、塔心与四慢道可读；连接条带不能全部称有顶廊；粗黑外框不能通作院墙；破坏沟不能当古渠。

已检查27个节点与30条关系均有有效来源引用；边端点均存在；所有实际坐标、米制距离和历史高度保持空值；北门无屋、南门底层孔道未定、僧房不定位等限制保存为机器可读字段。P1三个输入文件的哈希保留，未覆盖旧文件；没有修改程序、网页或tests。

完成的是**可以直接加入地图的局部结构数据**。本轮没有完成精确局部描摹、建筑立面复原或地理配准，数据生成也不等于网站已发布。

## 附录A：局部节点清单

| 场景 | 节点ID | 名称 | 绘图类型 | 证据 |
|---|---|---|---|---|
| changhe_gate_complex | cg-base | 主门基 | gate_base | G01 |
| changhe_gate_complex | cg-pass-west | 西间道 | passage | G01 |
| changhe_gate_complex | cg-pass-middle | 中间道 | passage | G01 |
| changhe_gate_complex | cg-pass-east | 东间道 | passage | G01 |
| changhe_gate_complex | cg-que-west | 西阙基址 | que_site | G02 |
| changhe_gate_complex | cg-que-east | 东阙基址 | que_site | G02 |
| changhe_gate_complex | cg-court-1 | 西侧1号院 | courtyard_reading_area | G03 |
| changhe_gate_complex | cg-court-2 | 东侧2号院 | courtyard_reading_area | G03 |
| changhe_gate_complex | cg-court-3 | 3号院 | courtyard_reading_area | G03 |
| changhe_gate_complex | cg-court-4 | 4号院 | courtyard_reading_area | G03 |
| changhe_gate_complex | cg-connection-west | 西侧基址连接 | foundation_connection | G04 |
| changhe_gate_complex | cg-connection-east | 东侧基址连接 | foundation_connection | G04 |
| yongning_compound | yn-enclosure | 寺院范围参照 | compound_extent | T04 |
| yongning_compound | yn-tower | 九层木塔／塔基 | pagoda_site | Y01, T01 |
| yongning_compound | yn-hall | 塔北佛殿 | unmeasured_building | Y01, T02 |
| yongning_compound | yn-gate-west | 西门 · 文献两重 | temple_gate | Y01, T04, T06 |
| yongning_compound | yn-gate-east | 东门 · 文献两重 | temple_gate | Y01, T04, T06 |
| yongning_compound | yn-gate-south | 南门 · 文献三重 | temple_gate | Y01, T04, T05 |
| yongning_compound | yn-gate-north | 北门 · 不施屋 | temple_gate | T04, T07 |
| yongning_compound | yn-lodgings | 僧房楼观 · 分布未定 | nonspatial_component_group | T03 |
| yongning_pagoda_base | yb-footing | 方形塔基遗存 | pagoda_footing | Y02, Y03 |
| yongning_pagoda_base | yb-core | 中央土坯塔心 | adobe_core | Y02 |
| yongning_pagoda_base | yb-surround | 环绕构造与柱位符号 | surrounding_structural_evidence | Y02 |
| yongning_pagoda_base | yb-ramp-north | 北向慢道 | ramp | Y03 |
| yongning_pagoda_base | yb-ramp-south | 南向慢道 | ramp | Y03 |
| yongning_pagoda_base | yb-ramp-west | 西向慢道 | ramp | Y03 |
| yongning_pagoda_base | yb-ramp-east | 东向慢道 | ramp | Y03 |

## 附录B：关系清单

下表关系均未给米制距离；图示方向是局部读取或古文方位，不是新取得的地理坐标。

| 关系ID | 主体 | 关系 | 对象 | 证据 |
|---|---|---|---|---|
| CG01 | cg-pass-west | 位于门基内 | cg-base | G01 |
| CG02 | cg-pass-middle | 位于门基内 | cg-base | G01 |
| CG03 | cg-pass-east | 位于门基内 | cg-base | G01 |
| CG04 | cg-pass-west | 西 → 中 | cg-pass-middle | G01 |
| CG05 | cg-pass-middle | 中 → 东 | cg-pass-east | G01 |
| CG06 | cg-que-west | 图示西南翼 | cg-base | G02 |
| CG07 | cg-que-east | 图示东南翼 | cg-base | G02 |
| CG08 | cg-court-1 | 西侧院 | cg-base | G03 |
| CG09 | cg-court-2 | 东侧院 | cg-base | G03 |
| CG10 | cg-court-3 | 北侧3号院 | cg-court-1 | G03 |
| CG11 | cg-court-4 | 北侧4号院 | cg-court-2 | G03 |
| CG12 | cg-connection-west | 接主门西侧基址 | cg-base | G04 |
| CG13 | cg-connection-west | 接西阙基址 | cg-que-west | G04 |
| CG14 | cg-connection-east | 接主门东侧基址 | cg-base | G04 |
| CG15 | cg-connection-east | 接东阙基址 | cg-que-east | G04 |
| YN01 | yn-hall | 佛殿在塔北 | yn-tower | T02, Y01 |
| YN02 | yn-tower | 寺内塔 | yn-enclosure | T01, Y01 |
| YN03 | yn-hall | 寺内佛殿 | yn-enclosure | T02, Y01 |
| YN04 | yn-gate-west | 西门，沿墙位置未测 | yn-enclosure | T04, T06, Y01 |
| YN05 | yn-gate-east | 东门，沿墙位置未测 | yn-enclosure | T04, T06, Y01 |
| YN06 | yn-gate-south | 南门，局部图有遮挡 | yn-enclosure | T04, T05, Y01 |
| YN07 | yn-gate-north | 文献北门 | yn-enclosure | T04, T07 |
| YN08 | yn-lodgings | 寺内构件记载；未定位 | yn-enclosure | T03 |
| YB01 | yb-core | 塔基中央构造 | yb-footing | Y02 |
| YB02 | yb-surround | 环绕关系，非完整环廊 | yb-core | Y02 |
| YB03 | yb-surround | 塔基内构造证据 | yb-footing | Y02 |
| YB04 | yb-ramp-north | 北侧慢道 | yb-footing | Y03 |
| YB05 | yb-ramp-south | 南侧慢道 | yb-footing | Y03 |
| YB06 | yb-ramp-west | 西侧慢道 | yb-footing | Y03 |
| YB07 | yb-ramp-east | 东侧慢道 | yb-footing | Y03 |
