# 首页永宁寺塔修订 V15

研究版本V6、网站视觉版本V15。详见 `visual-review.md`、`image-record.json` 与 `../../docs/homepage-yongning-v15-release-notes.md`。

## 可重现的原生场景

```sh
python research/homepage-yongning-v15-20261128/draw_tower_scene.py
node research/homepage-yongning-v15-20261128/render_scene.mjs
```

Node需能解析Sharp 0.35.5（也支持 `CODEX_PRIMARY_RUNTIME_NODE_MODULES`）。渲染器生成完整PNG中间件及两种WebP；PNG中间件不重复入库，源SVG、背景PNG与正式WebP均保留。各依赖版本见图像记录。图像生成的背景作为冻结输入保留，不声称用提示词能够逐像素重现。

`homepage-scene.svg` 引用同目录 `courtyard-background.png`。塔层是可独立检查的纯SVG，无嵌入位图；其尺寸来源与显示投影见 `tower-projection.json`。精确立面与文献、色彩和力学依据在V6专题中独立提供。
