# 首页空间环境修订 V16

本目录保存图像生成工具编辑的寺院局部、原 V12 栅格背景、可编辑 SVG 装配源、渲染程序、实际提示词、人工空间审查与图片身份。源图和审查指纹必须匹配，`image-record.json` 的 `accepted_for_publication` 在审查完成前保持 `false`。

局部放置范围为原画的 `(380,180,270,270)`，四边仅在矩形内侧2px渐隐。没有矢量立面塔或全城重绘。`render-audit.json` 记录源 PNG 矩形外 RGB 像素精确保留检查；两幅有损 WebP 不适用逐像素不变声明。

重现装配与网站尺寸：`node research/homepage-yongning-v16-20261128/render_scene.mjs`。渲染依赖版本随审计记录保存。

V6 专题源文件和图像不变。V15 源目录继续作为历史制作记录保存；V15 的技术验收通过与之后的用户视觉否定，分别登记在本目录的 `supersedes` 字段和当前状态表中。

发布行为与限制见 [V16 版本说明](../../docs/homepage-yongning-v16-release-notes.md)。现有发布器、测试文件名和兼容元数据键沿用 V15 接入点，当前 `version` 与 `hero_revision` 以图像记录和发布清单为准。
