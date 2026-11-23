# R12.1 技术档案：独立远端回读证明

**主档案已从独立远端对象库逐文件回读通过。** 核验完成时间为2026-11-23 22:19:18（上海）；该时间晚于生产CI完成与技术验收记录，不倒填到此前阶段。

主档案固定提交：`12668fd6b0db76dd961b1233f6af9ab0b86cf2c7`；tree：`c57c2006094bcadfbdb1d548c382a4802480c407`；唯一parent：生产提交`4579a6b8990a91780bf83391967c301218c0711e`。

[技术档案及研究边界](https://github.com/mechgouki/luoyang-city/blob/12668fd6b0db76dd961b1233f6af9ab0b86cf2c7/evidence/panorama-r12/2026-11-23/README.md) · [技术验收记录](https://github.com/mechgouki/luoyang-city/blob/12668fd6b0db76dd961b1233f6af9ab0b86cf2c7/evidence/panorama-r12/2026-11-23/acceptance.json) · [验收后接续状态](https://github.com/mechgouki/luoyang-city/blob/12668fd6b0db76dd961b1233f6af9ab0b86cf2c7/evidence/panorama-r12/2026-11-23/current-state-after-acceptance.json)。

## 实际回读范围与结果

| 项目 | 实际核验值 |
| --- | ---: |
| 冻结文件路径 | 2070 |
| 唯一blob | 1842 |
| 逻辑文件字节 | 611475327 |
| 唯一blob字节 | 581564830 |
| 前缀之外保持原样的文件路径 | 730 |
| 前缀之外保持原样的目录树 | 66 |

[remote-byte-readback.json](remote-byte-readback.json) 逐项记录实际读取的Git对象字节。文件路径集合、mode、字节数、SHA-256及重算的Git blob SHA-1均与[frozen-upload-manifest.json](frozen-upload-manifest.json)一致；提交只有上述一个parent，只在`evidence/panorama-r12/2026-11-23/`新增内容，前缀之外没有修改。四份生成的范围／索引文件同样回读，没有豁免。

- 冻结清单：973964 bytes，SHA-256 `21cd95e9106ac85fc3d4d21d126cb0c6dfe157a1ea1375b71b22cd2ffa926d08`。
- 主档案回读报告：1111233 bytes，SHA-256 `a811aaa02371655e4ceae4cebb93d20ebe516ee1021f87cdc0b416f7093a67b2`。
- 组装／内部索引／外部冻结清单一致性证明：[index-freeze-consistency.json](index-freeze-consistency.json)，SHA-256 `cd4aa46f0ffbd42639729043248a52c609dc74e9ff99008ee244ca195845c209`；[实际方法文件](check_frozen_index_consistency.py)一并保留。

## 独立来源与发布过程

[remote-fetch-provenance.json](remote-fetch-provenance.json) 保留新建bare对象库和实际远端fetch的命令、时间及结果。对象库中的生产基线与最终证据均从GitHub真实取得；未复制源工作树对象，没有alternates。最后fetch用已独立取得的生产SHA作为协商提示，随后核对FETCH_HEAD。回读程序禁用replacement/lazy-fetch，并逐个重算实际对象身份。原始回读方法在[主档案archive-methods](https://github.com/mechgouki/luoyang-city/tree/12668fd6b0db76dd961b1233f6af9ab0b86cf2c7/evidence/panorama-r12/2026-11-23/archive-methods)中。

[primary-publication-receipts.json](primary-publication-receipts.json)保留真实创建结果与传输异常：两次大目录请求超时，按冻结内容计算的目标tree随后GET为404；改用较小的不可变子目录请求后成功，最终root tree精确等于原冻结内容所算的目标。之后才创建主档案commit与新分支。具体分批计划见[tree-transport-plan.json](tree-transport-plan.json)，最后50个缺失blob的真实返回值见[frozen-blob-upload-receipts.json](frozen-blob-upload-receipts.json)。该操作回执在独立回读之前写入，其中的阶段状态保留当时事实。

[archive-preflight.json](archive-preflight.json)记录原目标分支和父树目标前缀不存在；[archive-commit-api.json](archive-commit-api.json)再次核实最终实际commit/tree/parent。[main-after-primary-archive.json](main-after-primary-archive.json)显示main仍为4579；[public-source-after-primary-archive.json](public-source-after-primary-archive.json)记录22:19:14实际公开build-info，806833字节及SHA-256与同次生产Pages原件直接相等。此前main观察另存[main-before-primary-archive.json](main-before-primary-archive.json)。

## 本验证目录的边界

本目录在主档案完成后另存，不回写已冻结主档案。验证提交以主档案commit为唯一parent，只新增`evidence/panorama-r12/2026-11-23-verification/`。本目录也须冻结、创建固定提交并独立远端回读；实际验证提交与自身回读结果在完成后写入[#52最终交接](https://github.com/mechgouki/luoyang-city/issues/52)，不把自身commit或自身核验报告回填进本目录造成自引用。

这是技术证据的保存与字节核验。六次全景仍全部未通过，主显示第五次、第六次为独立附录；首页继续已批准的V12。两张永宁寺局部试片和13对象宫城地面窗口仅作下一步研究控制，不证明完整建筑几何、古代实测注册或首页替换资格。#52与#47保持OPEN。
