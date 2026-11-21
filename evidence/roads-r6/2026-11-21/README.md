# R6.1 全城主干道：正式验收与长期证据

本批已完成发布与正式站验收。研究时段516—528年，研究版本 **R6.1**，专题版本 **road-atlas-r6.1**。main发布提交 `0e04a0018f085321afbecc7a4e35be0b8cc9da51`，来自 [PR #72](https://github.com/mechgouki/luoyang-city/pull/72)。首页继续使用用户选定的 **07号 / panorama-approved-v11**。

## 已完成的检查

- [PR运行44886935582](https://github.com/mechgouki/luoyang-city/actions/runs/44886935582)成功：215项研究测试、6项首页测试、整站浏览器回归通过。
- [正式运行44887623733](https://github.com/mechgouki/luoyang-city/actions/runs/44887623733)的build、deploy、verify-live全部success；最终完成于2026-11-21 17:17:48（北京时间）。
- 正式站786项公开资源逐项核验哈希，无HTTP重试。本批另由独立HTTPS回读确认17项资源、21行20列CSV、3项补充、5项下载、7成员离线包及首页07/v11。
- 1440×960桌面与390×844手机均实测入口、检索、筛选恢复、图层、深链接、缩放、横移、每端五次实际下载、断网离线阅读、无JavaScript原生阅读。没有浏览器运行错误。
- 六张PR道路截图均经人工检查；六张正式站截图与对应PR截图的SHA-256逐字节相同。PR合并测试提交和main发布提交的Git树也相同。
- 主图SVG、CSV、JSON、manifest和ZIP的浏览器下载哈希与正式HTTP校验、独立回读三者一致。

## 目录

- `pr/`：合并前13件原始证据、收集元数据与SHA256SUMS。
- `live/`：正式站12件原始证据、收集元数据与SHA256SUMS；包括完整786项公开资源报告。
- `independent-live.json`：独立正式站读取结果及五项下载哈希。
- `acceptance-summary.json`：本批验收、版本、图面数量和研究边界。
- `github-workflows.json`：GitHub实际运行／步骤、原始artifact标识及到期日、相同Git树的记录。
- 根目录`SHA256SUMS`：本目录全部文件的校验值，除清单自身。

原始PR artifact `14700925293` 将于2026-12-05到期；live artifact `14700812218` 将于2026-12-21到期。此分支保存本批必要的原始报告和截图，不依赖临时artifact持续存在。各阶段的`evidence-metadata.json`中的`workflow_conclusion: null`只表示收集脚本不推断工作流总体状态；实际GitHub成功结果保存于`github-workflows.json`与上述运行记录。

## 成果与研究边界

[专题](https://mechgouki.github.io/luoyang-city/luoyang-road-atlas.html) · [主图SVG](https://mechgouki.github.io/luoyang-city/road-atlas/city-roads.svg) · [21行证据CSV](https://mechgouki.github.io/luoyang-city/road-atlas/roads.csv) · [完整JSON](https://mechgouki.github.io/luoyang-city/road-atlas/roads.json) · [离线ZIP](https://mechgouki.github.io/luoyang-city/downloads/luoyang-road-atlas.zip)。

21条来源记录包含8条原图路迹、5条后出复原图读线、6组门端读点、2处发掘地段；登记12组对应、3项补充。保留来源图框和断笔；无新增田野测量、古道路经纬度或盛时古岸。

1993年《北魏洛阳外廓城和水道的勘查》602—608页与完整地形附图仍缺，实测／推定图例及各路末测点不得据后出图补成已知。下一入口为维普文献1002554709、知网KAGU199307004。水系沿用W01—W34原等级，永桥登陆点等继续待证；2022年运河报告暂缓，毁后洛阳后置。
