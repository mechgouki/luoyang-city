# 数据出处、限制与页面行为

## 上游资料

本仓库基于 `luoyang-v24-workpack.zip` 的研究数据、同版 37 页图册、全城 SVG。文件摘要记录于 `data/manifest.json`。研究数据没有从同名地名或地名出现顺序推定无证据的实测街址。

- `data/research-places.json`：原始实体与出处结构（保留不改动）。
- `data/research-drawing-register-v24.json`：339 条记录的网页与制图显示去向。
- `data/research-baseline-scene-v23.json`：v2.4 继承的布局数据与 11 个分区范围。
- `data/research-disputes.json`：保留原研究争议。
- `data/research-semantic-display-audit-v24.json`：此前图面与资料解释检查。

`data/entities.json` 等文件是为了网页阅读而派生的索引，并非额外史料。

## 关于 179 个点击标记

网页初版从现有 246 项绘图对象中提取了可以与实体 ID 关联的 `node`、`compound`、`area`、`group` 以及城门符号等，形成 179 组图形点击范围。图形命中区域是 UI 操作便利性设计，不是实体实际占地；未被点击标记覆盖的 339 条实体仍可在文本搜索中找到。

## 文献断言与图形位置

- `source_quote`：传世文本及校注转录的原句或摘要。
- `location_constraints`：经过研究整理的方向、邻接与所属关系，应回查来源。
- `temporal_state`：针对盛时综合图的表达状态，不等于确证某年在建或毁坏。
- 绘图坐标：供当前母图和分区一体缩放使用；不映射经纬度或现代地籍界线。

在分区名录中只知道“某寺属于某里”的情况下，不应在主图自动分配精确位置。独立关系栏也不参与全城坐标的拼贴。

## 变更流程

研究争议作为结构化记录留在 Git；GitHub Issue 负责收集讨论。若采用新解释，需更新实体、原文判断、绘图对象和验证记录，保持历史版本可以追溯。
