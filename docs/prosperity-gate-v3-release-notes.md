# 盛时 P3：阊阖门局部平面与城市接合诊断

## 本轮目标

把 P2 的阊阖门构成关系推进到可逐点复算的局部平面。页面以图件为主空间，让读者选择门基、门道或阙基读出处，开关原件底图，并在局部量读、城市接合和尺度核对之间切换。

发布入口为 `prosperity-gate.html`。示例深链：

`prosperity-gate.html#view=local&component=gate-main-base&source=1`

深链保存视图、所选构成及原件底图状态。视图参数为 `local`、`city`、`diagnostics`；构成使用研究数据中的稳定 ID。

## 研究层次

原件来自 UNESCO 申遗文档 `1442.pdf` 第 1962 页的阊阖门平剖图。研究输入保存原生 555 × 434 像素 JPEG，并登记出处和 SHA-256；图像没有为了增加细节而重采样。附表门基尺寸见同文档第 1927 页 Cgm-3；城市来源锚点仍沿用管理规划图 06a 的 P1/P2 读数。

本轮有 10 个可选择构成：

- 主门基主体边缘 1 项。
- 三门道可辨中段 3 项。
- 东西阙基可见实线 2 项。
- 东西阙地下基础来源虚线 2 项。
- 门基至两侧阙基的连接路径示意线 2 项。

阙基可见边缘保留开放端；来源虚线不升级成地上建筑边；连接示意线的线宽不表示真实廊宽。探方框、扰动和模糊接口没有补成完整建筑轮廓。

原件横向 20 m 比例尺读作 81 px。图内坐标使用同一比例尺和原件北箭定义的局部轴，原点取门基量读角点的算术平均。北箭的外部基准、扫描纵横比例和局部原点与总图图符中心的对应均未独立核定。像素描摹范围和最保守读图包络只表达原件读取限制，不作为统计置信区间或现场测量精度。

附表的 44.5 × 24.4 m 与图内读数分别保留。附表数值不参与比例尺标定，也不通过拉伸原件或移动城市锚点消除差异。局部到城市的配准尚未核定：共同控制点为零，平移、旋转和城市足迹均保持未解。

## 页面与下载

页面提供三个主视图：

| 视图 | 作用 | 使用边界 |
| --- | --- | --- |
| 局部平面 | 在原件底图上逐项选择门基、门道、阙基与连接关系 | 图内米制与出处明确；开放轮廓保持开放 |
| 城市接合 | 并列说明局部坐标、城市概略锚点和缺少的控制条件 | 不把局部原点、像素或图内北箭直接变成古址经纬度 |
| 尺度核对 | 对照原件比例尺量读、附表尺寸和读图包络 | 不将来源汇编内的尺度对读称作独立实测验证 |

地图支持拖动、按钮缩放、键盘 `+` / `-`、`Home` 复位、`Enter` / 空格选择构成，以及“查看所选”。构成也可通过原生选择框查阅。手机端将出处面板置于图件下方，并保留原件、当前 SVG 和下载入口。

静态 HTML 内含局部 SVG 图片、默认构成的出处、原件对照和完整下载列表。关闭 JavaScript 或数据请求失败时，这些内容仍可阅读。

下载包括：

- 三张可单独打开的 SVG。
- 三页 PDF 图册。
- 原件像素、来源及研究限制 JSON。
- 局部米制模型 JSON。
- 按构成与顶点逐行排列的 CSV，分列 `source_x_px` / `source_y_px` 与 `local_x_m` / `local_y_m`。
- 量读与接合方法说明 Markdown。
- 包含图件、读数、原件、方法、图册和哈希目录的 ZIP。

## 生成与版本登记

`tools/prosperity_gate_v3.py` 在 P2 生成器之后运行，读取 `research/prosperity-v3/gate-plan.json` 与 `tools/prosperity_gate_geometry.py` 的模型和 SVG 输出。它不改研究读数或既有城市几何。

发布元数据增加：

- `build-info.prosperity_gate.version = prosperity-gate-v3`。
- `build-info.prosperity_gate.metadata = prosperity-gate/data.json`。
- `release.prosperity_gate_version = prosperity-gate-v3`。
- `release.extensions` 中登记 `prosperity-gate-v3`。
- `release.current_milestone = 盛时P3：阊阖门局部平面与城市接合诊断`。

`build-info.files_sha256` 包含全部新产物。ZIP 内的 `bundle-manifest.json` 列出包内研究文件和图册的哈希；目录自身和 README 不形成递归哈希。

## 旧资产与入口变更

P2 的保存证明保持原字节。本轮只向四张旧 HTML 各添加一个指向 P3 的 `<p>` 入口；新块之外不插入空白或修改旧内容。删除该块后必须与归档逐字节相同。

| 修改页 | 原字节归档 | 入口 ID |
| --- | --- | --- |
| `index.html` | `index-before-gate.html` | `gate-detail-home-entry` |
| `v3.0-dual.html` | `v3.0-dual-before-gate.html` | `gate-detail-home-entry` |
| `prosperity.html` | `prosperity-before-gate.html` | `gate-detail-entry` |
| `prosperity-core.html` | `prosperity-core-before-gate.html` | `gate-detail-core-entry` |

`prosperity-gate/preservation.json` 的 `intentional_html_updates` 逐项记录 `path`、`archive_path`、`before_sha256`、`after_sha256` 与 `entry_id`。它的 `protected_files` 验证其余 P2 及更早资产没有变化。旧 P2 的 P1 页面哈希经 `prosperity-before-gate.html` 接入归档链，仍可核对其原始发布状态。

## 验证范围

`tests/test_prosperity_gate_v3.py` 检查原件哈希与尺寸、像素与米制逐点对应、统一比例下的保形、图内北东轴方向、附表值不参与标定、开放轮廓、城市接合未解、CSV 单位边界、图册与 ZIP、无脚本基本内容以及旧 HTML 的精确可逆归档链。

`tests/browser_prosperity_gate_v3.py` 检查三视图、组件出处、键盘与缩放拖动、深链与浏览器历史、原件层状态、完整下载、手机布局、无脚本模式及数据加载失败后的静态阅读。它支持 `--base-url` 和 `CHROMIUM_PATH`，同一脚本用于构建产物与线上站点。

2026-11-15 本地增量构建完成，12 项 P3 语义测试通过。PDF 按项目既有流程用 Poppler 渲染，三页均已逐页检查；JavaScript 和 Python 语法检查通过。本地容器不能启动浏览器，浏览器验收由可运行浏览器的构建环境执行，未把未运行的浏览器检查记为通过。正式里程碑以发布工作流与线上检查结果为准。

## 尚未完成的研究

本轮没有核定局部与城市的变换，没有新增古址绝对坐标、盛时建筑高度、屋顶或古代地面。永宁寺院宽差异沿用 P2 未定结论。下一步需要共同位置控制、北向基准以及扫描尺度核对，才能决定哪些局部轮廓可进入城市分布图。
