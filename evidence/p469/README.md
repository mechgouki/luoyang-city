# P4.6.9 水陆骨架联读：初版正式站验收

核对时间：2026-11-19T20:29:07+08:00。发布提交 `e58880049cb88db17379a63bbe2377c63a7e7fe2`；[生产运行44520238130](https://github.com/mechgouki/luoyang-city/actions/runs/44520238130)第二次尝试的build、deploy、verify-live全部成功。

本目录保存不会随Actions附件过期而丢失的验收材料。主结果在 `acceptance.json`，逐文件哈希在 `manifest.json`。

## 实际完成

- 162项语义／回归通过；704项正式站资源通过。
- 桌面和390px手机各8组操作、10项真实下载、无JS阅读通过；页面错误为空。
- 24张生产截图与逐张人工查看的main构建截图完全同字节；两页PDF已逐页渲染查看。
- 额外独立读取41个公网文件，44项断言通过，无HTTP重试；离线ZIP共12成员，各成员与清单和公网字节相符。
- H2两图、P466 PDF、P467五SVG／readings／PDF及P468图册和八份JSON保持登记字节。

首次生产验收停在旧P3的gate-plan.json下载状态检查，日志未给具体HTTP状态。复核该文件HTTP 200及哈希后，仅重跑失败任务。同一提交通过；没有改研究数据、跳过测试或放宽门槛。失败日志和报告在 `initial-failure/`。

## 研究口径

两套来源框架分别保留，不能直接重叠为一张地理实测图。34项是旧水系研究编号，包含现代参照和专题入口；100条关系不是100条水流。P468更正已经应用到当前索引，濛汜池与碧海曲池不再挂入旧I09。新增古坐标、米制量测和516—528年古岸线均为0。

2022年运河报告按用户指示暂缓；古岸、永桥桥头、北路末测点与合流等继续留空。首页H2及旧版封存未改。

## 审阅说明

手机全图缩小时，图内小字需放大或开SVG/PDF细读。无JS全文可读，通用“放大”提示的小不一致已登记为后续文案改进，未将其描述为无JS交互能力。

[正式专题](https://mechgouki.github.io/luoyang-city/prosperity-backbone-p469.html) · [两页图册](https://mechgouki.github.io/luoyang-city/downloads/backbone-469.pdf) · [固定交接表](https://github.com/mechgouki/luoyang-city/issues/52)
