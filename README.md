# 北魏洛阳文献地图 · Luoyang Atlas

一个以《洛阳伽蓝记》及其校注、相关史地文献为基础的**可追溯历史城市地图**。本仓库保存 v2.4 盛时综合平面图的在线浏览版本、原始研究数据、分区图、争议目录和部分生成工具。

> 当前时段为 **516—528 年河阴之变前的文献合成图**，**不是某一年的实测城市地图**。地图上的图形尺寸、城墙轮廓及未定院界都是研究表示，不应换算为现代坐标或古代里数。

## 在线浏览

- 网站（发布后）：`https://mechgouki.github.io/luoyang-city/`
- 全城地图：交互缩放、分区定位、地点检索、原文引用。
- 分区图册：37 张地图与附图，可放大 SVG，附完整 PDF 下载。
- 研究争议：30 条争议及“本版采用的画法”说明。

## 技术特点

首个可部署版本为**纯静态网站**（HTML + CSS + Vanilla JavaScript + SVG）。GitHub Pages 可以直接发布，不需要数据库或第三方依赖；数据与地图由 `/data/` 和 `/assets/` 读取。后续如需 Astro 架构，可以保留公开的数据契约并迁移前端。此方案与最初 Astro 技术设想有所调整，是为了让首版先可验证、易部署。

## 本地运行

不要双击 `index.html` 直接打开（`file://` 会限制资源读取）；在仓库根目录运行：

```sh
python3 -m http.server 8000
```

浏览 `http://localhost:8000/`。

## 仓库目录

```text
index.html                网站入口
styles.css                统一图式和移动端样式
app.js                    SVG 缩放、对象选择、检索和争议浏览
assets/master-v24.svg     v2.4 母图（独立研究绘图坐标）
assets/sheets/            37 页矢量单图与网页缩略图
data/entities.json        从原始记录整理的 339 条检索索引
 data/markers.json        179 个有地图图形关联的交互标记
 data/disputes.json       30 条研究争议
 data/regions.json        11 个分区及其裁切范围
 data/sheets.json         37 张图册的目录
 data/research-*          v2.4 原始数据与审查登记保留副本
downloads/                37 页 PDF 图册
tools/                    既有母图生成脚本和网站数据校验
.github/workflows/        可选的 GitHub Pages Actions 自动部署
```

## 文献与校注

《洛阳伽蓝记》以范祥雍《校注》为工作底本，周祖谟《校释》等进行交叉校核；附带《河南志》《水经注》等旁证。具体的来源地址、卷条和引文见 `data/entities.json`、`data/research-places.json` 以及争议说明。版本关系和间接转引并不等于独立互证。

图形与文本的版权不能混同：本仓库收录的研究复原图和制图代码由项目形成；他人书影、图版、照片、全文等如无明确再分发权限，不纳入网站。其他资料的使用应遵守原提供方的许可与合理引用要求。**项目对外的复用许可证尚未确定，仓库暂不附开放源代码许可。**

## 发布 GitHub Pages

1. 创建 GitHub 仓库 `mechgouki/luoyang-city`（公开）。
2. 上传上述文件到默认分支 `main`。
3. 在仓库 `Settings → Pages → Build and deployment` 选择 **GitHub Actions**，本仓库已经包含部署工作流。
4. 推送到 `main` 后，可在 `Actions` 查看验证与 Pages 发布状态；部署成功后访问 `https://mechgouki.github.io/luoyang-city/`。

如果暂时不启用 Actions，也可在 Pages 中使用 `Deploy from a branch → main / (root)` 直接发布静态文件，二者选一种即可。

## 研究版本

- `atlas-v2.4`：本次网页采用的历史地图和数据基线。
- `web-v0.1.0`：首个静态交互网站的实现版本。

更新网页 UI 不等同于修订历史布局。改变史料解释时，应同时更新对应争议、地图、审计与研究版本。