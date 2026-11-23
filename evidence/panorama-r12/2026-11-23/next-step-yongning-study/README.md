# 永宁寺局部结构试片

两张图均为独立局部艺术试片，**不是第七／第八幅全景，不是已批准的首页候选**。原V14六次全景试绘及其审查没有改写。

| 试片 | 已实际看到的结果 | 尚未通过的内容 | 后续用途 |
| --- | --- | --- | --- |
| [01 纵幅试片](structure-study-01.png) | 三层南门、九层木塔；门塔独立基脚、塔后殿关系更清楚 | 输入1280×1360，输出1088×1445，画幅非统一缩放；完整几何未核 | 结构可读性试验，保留原审查 |
| [02 方形试片](attempt-02/structure-study-02.png) | 保留上述结构；输入1536方形、输出1254方形，画幅比例修正；若干同名基脚前缘有限一致 | 全部基址角点、遮挡边、墙段端点与相机保真仍未验证；尚未回嵌全景 | 可作下一轮局部结构与材质参考，冻结SVG仍为布局依据 |

## 当前判断

第二张试片适合作下一轮全景编辑的辅助结构参考。它的三层南门和九层木塔可独立计数，南门与塔台基之间保持地面间隔；几处可见基脚南缘大体接近按同一投影计算的位置。**这些改善不等于完整几何通过。** 不得据此改写地面矩阵，也不能跳过实际回嵌全景后的审查。宫城门序、阊阖门构件及整座城市的既有图像问题尚未在这两张局部图中处理。

## 第一次试片原件

- [图像](structure-study-01.png)，SHA256 `d63fd413527eebbf80486d5ade9fe7cc5a978f67495b4b34c41fc2e87f95aa8a`。
- [输入导图](yongning-study-layout.png)、[SVG](yongning-study-layout.svg)、[显示变换](display-window.json)、[实际提示词](prompt.txt)、[独立审查](independent-review.json)。

第一次的独立审查与身份快照保持原字节；第二次结论不覆盖第一次失败的画幅检查。

## 第二次试片原件

- [详细说明与基脚对照](attempt-02/README.md)。
- [图像](attempt-02/structure-study-02.png)，SHA256 `7456b5d932128ab74c5770dedfa5866f05b806f9fa08ff3214c884f5fe1ac70a`。
- [独立审查](attempt-02/independent-review.json)、[布局导图](attempt-02/square-layout.png)、[SVG](attempt-02/square-layout.svg)、[显示变换](attempt-02/display-window.json)、[实际提示词](attempt-02/prompt.txt)。

两次布局输入均从 `research/panorama-r12/massing-yongning-clean.svg` 仅调整外层视窗和渲染尺寸形成。未改变冻结地面几何、矩阵或来源身份。生成图中的高度、收分、屋顶、开间、门洞和材质保持艺术表达身份，不构成新增考古立面成果。每份 `image-identity.json` 为生成后、审查前的快照，各自当前结论见对应独立审查。
