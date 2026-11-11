# 北魏洛阳文献地图 · Luoyang Atlas

以《洛阳伽蓝记》及其校注、相关史地文献为基础的可追溯历史城市地图。
仓库：`mechgouki/luoyang-city`。研究基线：**v2.4**；网站实现：**web 0.1.1**。

> 盛时图采用 516—528 年河阴之变前的文献合成时层，不是某一年实测地图。图形尺寸、城墙轮廓和未定院界不能换算为历史地理坐标。

## 内容

339 条实体、179 组交互标记、11 个分区、37 张图页和 30 条争议。
网页支持 SVG 缩放、区域定位、地点检索、史料详情、争议浏览及图册下载。
原始研究数据与绘图代码仍保留在仓库；首版为无第三方运行时依赖的 HTML、CSS、JavaScript 和 SVG 静态网站。

## 首次发布：只需一次 Pages 设置

网站目标地址：`https://mechgouki.github.io/luoyang-city/`。
**目标地址不代表已经部署成功；以 Actions 的 deploy 任务和实际访问为准。**

1. 仓库管理员打开 https://github.com/mechgouki/luoyang-city/settings/pages 。
2. 在 **Build and deployment → Source** 中选择 **GitHub Actions**。
3. 在 **Actions → Validate and deploy Luoyang Atlas → Run workflow** 运行 `main`；也可以重试失败的部署任务。

现有工作流会先校验、打包，再部署。无需提供密码、个人访问令牌或扩大其他仓库的权限。
不推荐直接从 `main / (root)` 发布：本仓库的 PDF 需要先合并分片，且发布文件应从 `_site/` 生成。

## 本地构建

需要 Python 3.11+，Node.js 18+（回归测试使用内置 node:test，无 npm 依赖）。

```sh
python3 tools/assemble_pdf.py
python3 tools/validate_site.py
node --check app.js
node --test tests/map-interactions.test.cjs
python3 tools/build_site.py
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
- `docs/resume-review.md`：本轮续接核查、修复和仍需验证的事项。

本次仅修复网页和发布流程，未调整 v2.4 历史研究判断。UI 更新不等同于研究版本变化。

## 史料、许可与限制

以范祥雍《校注》为工作底本，周祖谟《校释》等参与校核；相关引文、出处、采用解释与异说见实体数据、争议目录及研究说明。转引不能自动视为独立互证，未定位对象不得自动生成历史街址。

代码与本项目复原图不能替代他人书影、图版或照片的许可。**对外复用许可证尚未确定，仓库暂不授予开放源代码许可。**第三方资料须分别核查权利与引用要求。
