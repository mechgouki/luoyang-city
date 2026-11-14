# 盛时文献平面图：引文、版本与字面约束复查

复查日期：2026-11-14。基线：`1d541938cb8b21cb218d5bbd934cf41bbdfa9fc8`。

本阶段完成的是**183条历批证据的电子转录追溯审计和236处字面约束目标的语义分类**。实际取得15份来源，重新读入文字层，按正文与现代夹注分开核查；没有把旧数据里的“已核”标签直接计作本轮成果。新工作层的可用更正与制图指令保存在 [text-review.json](../research/prosperity-v1/text-review.json)。旧JSON、既有实体ID及封存图件均保留。

## 1. 完成程度与统计口径

| 项目 | 数量 | 准确含义 |
|---|---:|---|
| 证据记录全覆盖 | 183 | v2.5、v2.7及B1—B7共11个输入文件；其中B1是带古文短引的制图决定，E18是项目逻辑推理，不能都算独立古文证据 |
| 旧quote按规范化节录顺序直接匹配 | 172 | 至少一个实际取得的所列版本匹配；去标点、空白、控制字符及版式“校”标签，保留异字，不是古刻逐字校勘 |
| 主异常或特殊抽取经人工上下文处理 | 11 | 缺省略号、字形规范化、校改取字、PDF夹注混排、错误转述或混入现代夹注；改引再按对应电子正文匹配 |
| 另行对照的次选版本差异 | 10 | 实际列出另一版的字面及定位；识别差异，不裁断哪一字最接近古书原貌；这10项与上述记录覆盖交叉，不能相加成193条 |
| 逐来源匹配尝试 | 225 | 201次旧引直接匹配；24次不直接匹配已由11主异常涉及的14个来源实例及10次次选版本对读解释 |
| 来源取得与定位 | 15 | 周、范各五卷HTML，河南志、水经注两版、伽蓝记四部丛刊卷三及范电子重排PDF |
| 未解释的电子引文匹配失败记录 | 0 | 只说明本轮字符与文本层的失败已有说明；不能说所有异文、身份、年代、古址均已解决 |
| 字面约束清单 | 236处／93种字面目标 | 每处保留原约束、关系、原目标、候选与分类；不是236个遗失地点 |
| 唯一目录名称跳转 | 198 | 仅名称或别名唯一对应；不升级为史证 |
| 需要语义分类的其余目标 | 38 | 包括范围、代词、复合参照、朝向、自身尺度及动物对象 |
| 新发现的实质项目引文错误记录 | 2 | B2:G13与B4:NG15；是修正项目旧证据展示，不是新的历史或考古发现 |
| 继承既有更正 | 1 | B2:G15由B8:CB14已更正，本轮仅重新核对与继承，不冒充新发现 |
| 新增实体／古代经纬度／名称匹配升级史证 | 0／0／0 | 第一阶段不提供古址精确定位 |

适合对外的措辞是：“183条旧证据已完成本轮电子文本追溯；172条按节录顺序匹配，11条经人工处理，另说明10处版本差异。”不宜写“183条原典已全面校勘”，也不宜把225次来源匹配称作225份独立史证。

周祖谟、范祥雍、四部丛刊与范电子PDF均属于《洛阳伽蓝记》文本家族；不同整理本相合不能重复计作独立目击。旧`source`、`sources`有时只是整条证据的支持书目，不表示其中每本都给出了完全一致的逐句引文。数字与原字段在JSON中分别保存。

## 2. 两项影响新平面图的实质修正

### 2.1 B2:G13：都堂在柰林西；扶桑为海

旧quote为“園中有柰林……碑西有都堂……堂東有扶桑殿。”，包含三种不同问题：

- “園中有柰林”不是两整理本逐字句，而是把百果园后连续叙事压缩成了明确的园内归属句。柰林归百果园仍可作为篇章回指解释，但必须放在释读层。
- 两本均记“柰林西有都堂”，旧引的“碑西”换错了方向参照。
- 两本均记“堂東有扶桑海”，旧引的“殿”把水体误成了建筑。

可使用的准确节录为：

> 柰林南有石碑一所，……高祖於碑北作苗茨堂。……柰林西有都堂，有流觴池。堂東有扶桑海。

定位：[周本卷一](https://deerpark.app/cbeta/B0077/1)，B12n0077_p0094a12—14、p0095a11—12；[范本卷一](https://deerpark.app/cbeta/B0078/1)，B12n0078_p0406a11—12、p0407a02。JSON保存了百果园前文、石碑／苗茨堂段、都堂／流觞池／扶桑海及其后诸海总括的必要上下文，正文与现代夹注分开。

**制图决定：**沿用`ic_nailin`、`ic_dutang`、`ic_liushang`、`ic_fusang`等既有ID，在宫苑的未定位关系插图中显示“都堂在柰林西”和“堂东扶桑海”；扶桑采用水体符号。碑在柰林南、苗茨堂在碑北，各自保留参照。既有实体名录原本已经正确，不应再造“扶桑殿”或把它当作新发现地点。这些关系仍不提供池岸、堂宽、园墙或现代坐标。

### 2.2 B4:NG15：承明门正文与现代注分层

[周本卷一](https://deerpark.app/cbeta/B0077/1) B12n0077_p0082a09的正文为：

> 瑤光寺北有承明門，有金墉城，即魏氏所築。

“城之西北門也。”处在`small.inline-note`的现代夹注层；“有字上疑有脫文。”亦为同处周注。旧quote把第一句夹注接入古文，造成“城西北”似为该句古文明言的印象。[范本卷一](https://deerpark.app/cbeta/B0078/1) B12n0078_p0387a06亦可定位上述古文。两本没有因此成为互不依赖的独立空间调查。

**制图决定：**“瑶光寺北承明门”显示为正文方位；“城之西北门”显示为周氏夹注。承明在西墙门序的依据另接NG13、WR01，不以被夹注污染的旧句一并担保。金墉接句保留缺文疑问，不填成具体相邻距离或新道路。这修正了证据层，不要求移置既有主案锚点。

## 3. 其余9项主异常：只更正相应层次

| 记录 | 本轮处理 | 对布局的影响 |
|---|---|---|
| v2.5:E06 | 河南志实际为淩陰里，旧引写凌；逐字引用保留来源字形 | 无新地块或序列改变；司州条不能省成无差别同文 |
| v2.5:E10 | 所列四库转录作𣲖、于，旧引规范成派、於 | 说明规范化，不改河道 |
| v2.7:N02 | 造与桥北大道之间有桥南马市等文，补明示省略号 | 不让删文产生桥、里、马市紧邻错觉 |
| v2.7:N03 | 阳渠南与阳渠北两句之间有租场句，补省略号 | 不把节录当连续地块边界 |
| v2.7:N11 | 电子PDF夹校混排；用同范本卷四HTML分层复核 | 长分桥条件性分流与中朝回溯保持原界限 |
| v2.7:N14 | 旧引移动至字并漏删节；采用已有B7:LR05周本短引 | 行像进宣阳不增补必经永桥路线 |
| v2.7:N19 | 范电子本显示㯋（鄴），旧引取校正字鄴 | 说明取字，不改变石经迁徙史事 |
| B2:G15 | 继承B8已完成的概述／原文分层更正 | 保留陽穀原字与改渠校注，不画地下池水全互联或全年常流 |
| B2:G16 | 周作入寺婬穢，范保留入瑤光寺婬穢，旧引规范为淫 | 侵扰不成为寺院或塔的焚毁证据 |

G15准确引文跨周本p0095a14至p0096a01，范本在p0407a03—04。PDF页码需区分页内印码与文件计数：N11在页内100、文件第101页；N18在页内44、文件第45页。这里只读取电子重排文字与页码，没有声称核验古刻书影。

## 4. 盛时骨架、里距与时层的可用范围

门序、明确的道侧、寺北／道东等关系，可以为文献平面图提供有方向的组织结构。水经注的沿流叙述可以给出水段的先后关系，但桥下流水不能自动变成沿河道路；诸海地下联系也不能画成地表河槽。宣阳外四里、门外一里余、市周回八里等原文量度应保留原单位和语境；本轮没有确定换算率、现代距离或图上像素比例。

“高显、下临城阙”可保留为凝玄寺的相对地势线索；海内营作的蓬莱山不能用现代DSM的天然高点替代。宫苑景山殿名物、张伦私园同名山、昭仪池与翟泉等既有身份条件仍须分开。下一阶段将它们交给历史地形与定位依据研究，不能仅凭本轮字符串匹配落点。

盛时以既有516—528河阴前综合窗口为工作范围，并不代表这些建筑在窗口内每一年、每个构件同时完整存在。大觉与平等的永熙塔、宣忠兑现舍宅、531以后建中用途、永安末到京狮子等后出状态不能前推。寺院本体的存在、宅改寺、塔始建与塔竣工分别登记；“未定”不能被绘制成“已证晚出”或“已毁”。这些规则依既有证据保留，本轮未新增统一落成年表。

## 5. 236处字面目标的语义处理

198处目标与名录名称或别名唯一相合，可作为页面跳转。这里的唯一性只是现有339项名录里的检索唯一，不意味着史书中的同名对象已证为一处。关系、原句、原目标和候选均保留，`historical_identity_verified`、`adds_spatial_constraint`始终为false。

38处其余目标中，12处是洛阳城范围参照，9处是伊水／洛水这对区间边界，另17处涉及前身宅、宫城范围、道路两侧集合、回指歧义、自身尺度、动物等。具体例子：

- “南北”是朝向值，“寺院”在景明方五百步约束中是本寺尺度，“白象”在乘黄曹饲养记录中是动物；三者都不是缺失城市地点。
- “建阳里／绥民里”保留两个道路两侧对象；“永桥／洛水”区分桥语境与水岸角色；“伊水／洛水”保留两条边界河流。
- “庄严寺／东安里”保留回指候选；“秦太上公二寺”不能自动解释为两座寺各自都已给出同一测量关系。
- “汉濯龙园”仍属跨时段同址主张；“城西”在金墉叙事中的指代不能自动决定为金墉或全洛阳城。
- “广平王怀宅〔平等寺址〕”“杨氏家宅”保留前身用途，不自动并入别的广平王寺院或杨椿单宅。

全部236处在JSON逐条可查，本文附录亦逐条列出。无旧约束被改写，无候选自动成为古址。

## 6. 仍须继续核查的内容

**文本层已经做了什么：**实际读取15份来源；完成172条旧引的顺序字符匹配；人工处理11条主异常；对读10个次选版本的具体差异。G13与NG15的必要上下文、现代注层、版本定位均已分列。

**仍未做或不在该结论内的内容：**古刻、写本与书影逐叶校勘；10个版本差异的原貌裁断；各读法涉及的实体同一性、年代是否同期、绝对古址位置和古代地貌。诸如周补學、魏、有，退／延酤，準／阜財，中（東）及釗（剛）等，已经识别来源差别，但不等于本轮裁定了古书原字。上述项目不能用“未解释匹配失败0”掩盖。

## 7. 实现、复现与发布边界

`tools/prosperity_text_audit.py`只生成新的审计层；实际完整源HTML/PDF不提交。公开JSON保存URL、取得日期、SHA-256、字节数和定位；现代校注只为NG15文本层问题保留两句必要短引，没有大段再分发校注全文。

已有源缓存时：

```bash
python tools/prosperity_text_audit.py --source-cache /path/to/prosperity-text-cache
python tools/prosperity_text_audit.py --check
python -m unittest discover -s tests -p 'test_prosperity_text_audit.py'
```

源缓存需含周、范各五卷HTML、H/W/W16/L3S HTML及LF.pdf/LF.txt；URL和校验哈希见JSON。无源缓存时仍能执行清单与安全边界回归检查。测试覆盖正文／现代夹注区分、古书子注保留、未标删节拒绝、错名拒绝、节录顺序、全部旧证据和字面约束覆盖、关键非实体不落点，以及B8更正不冒充本轮发现。

本文件与JSON是文献研究交付。页面集成、构建、上线和资源哈希核验由主任务完成，不能以本文件生成成功代替网站已更新。

## 附录A：183条证据全覆盖清单

“匹配”为至少一个版本规范化顺序相合；“人工”为11项主异常／特殊抽取；“另版”为另有已具体列明的次选版本差异。位置用CBETA行号或原记录篇章定位，详情见JSON。

| 记录 | 本轮类别 | 来源与定位 | 保留条件 |
|---|---|---|---|
| v2.5:E01 | 匹配 | B0078-1 0341a04；B0077-1 0043a11 | 正文＋异文记录 |
| v2.5:E02 | 匹配 | B0078-1 0341a05；B0077-1 0043a15—0044a07 | 正文 |
| v2.5:E03 | 匹配 | B0078-1 0341a06；B0077-1 0044a08—0044a09 | 正文 |
| v2.5:E04 | 匹配；另版 | B0078-1 0341a06—0341a07、0341a07—0341a08 | 周本补學；本条旧引采用范本国子南，不能当两本无差别同文。 |
| v2.5:E05 | 匹配 | B0078-1 0341a08—0341a09；B0077-1 0044a14—0045a02 | 正文 |
| v2.5:E06 | 人工 | H 卷三·后魏城阙古迹，右卫府至凌阴里条 | 河南志电子本作淩陰里；旧引写凌陰里。字形须记录，不改实体或南北链。 |
| v2.5:E07 | 匹配 | B0078-1 0341a08 | 现代校者解释 |
| v2.5:E08 | 匹配 | B0077-1 0045a01 | 现代校者解释 |
| v2.5:E09 | 匹配 | H 卷三·后魏城阙古迹，太尉府条及宫前诸署总括 | 后出地志正文 |
| v2.5:E10 | 人工 | W 卷十六·穀水，西门支渠段；电子转录，不冒用未核页码 | 所列四库转录作𣲖、于；旧引规范为派、於，未显式说明；不由字形差异重画渠线。 |
| v2.5:E11 | 匹配 | H 卷三·后魏城阙古迹，右城东之前 | 后出地志正文 |
| v2.5:E12 | 匹配 | H 卷三·后魏城阙古迹，右城东之后首条 | 后出地志正文＋断句限定 |
| v2.5:E13 | 匹配 | B0078-1 0392a04—0392a06；B0077-1 0083a11—0083a14 | 正文＋校补 |
| v2.5:E14 | 匹配 | B0077-1 0083a15—0084a03；B0078-1 0392a06—0392a07 | 正文＋校者论证 |
| v2.5:E15 | 匹配 | W 卷十六·穀水，铜驼街与永宁寺段 | 古文旁证 |
| v2.5:E16 | 匹配 | H 卷三·后魏城阙古迹，太尉府后两条 | 后出地志正文 |
| v2.5:E17 | 匹配 | B0078-1 0341a11、0342a15；B0077-1 0045a06、0047a04 | 正文 |
| v2.5:E18 | 匹配；另版 | B0078-1 0341a09；B0077-1 0045a02 | 河南志是太社—司州—淩陰里条目链，非逐字社南有凌陰里；层级和异名不可压平。 |
| v2.7:N01 | 匹配 | B0077-2 0099a07—0099a08 | 仅追溯字面；身份、同期与位置另核 |
| v2.7:N02 | 人工 | B0077-2 0106a11—0106a12、0107a01 | 晉太康元年造与橋北大道之间尚有桥南马市等文；旧引缺省略号，不能造成紧邻错觉。 |
| v2.7:N03 | 人工 | B0077-2 0100a04、0100a06 | 两句之间有寺南有租塲，需明示节录；不能删文后让读者以为是连续两句。 |
| v2.7:N04 | 匹配 | W16 广莫门北至马市石桥段 | 仅追溯字面；身份、同期与位置另核 |
| v2.7:N05 | 匹配 | W16 城西阊阖门·入城上渠至千秋段 | 仅追溯字面；身份、同期与位置另核 |
| v2.7:N06 | 匹配 | W16 千秋门南流至宫城阊阖门、铜驼街段 | 仅追溯字面；身份、同期与位置另核 |
| v2.7:N07 | 匹配 | W16 永宁寺段后·庙社之间 | 仅追溯字面；身份、同期与位置另核 |
| v2.7:N08 | 匹配 | W16 西明门左枝渠至青阳段 | 仅追溯字面；身份、同期与位置另核 |
| v2.7:N09 | 匹配 | W16 铜驼街东流至东阳门石桥段 | 仅追溯字面；身份、同期与位置另核 |
| v2.7:N10 | 匹配 | W16 西明门以下·津阳、宣阳、灵台、明堂、开阳段 | 仅追溯字面；身份、同期与位置另核 |
| v2.7:N11 | 人工 | B0078-4 0577a15—0578a01、0578a04 | 电子PDF正文与夹校在抽取流中混排；印刷页码100（PDF文件第101页）上下文确认，并按同一范本卷四HTML剥离夹注核到正文，不把PDF抽取断裂当引文错误。 |
| v2.7:N12 | 匹配 | L3S 卷三·永桥、四夷馆里连续段 | 仅追溯字面；身份、同期与位置另核 |
| v2.7:N13 | 匹配 | W16 宣阳门段·对宫门与浮桁 | 仅追溯字面；身份、同期与位置另核 |
| v2.7:N14 | 人工 | B0077-3 0144a14、0145a01—0145a02 | 旧引把至移到四月七日前，略掉录像段而未标删节，并采用八日校读；使用已在B7:LR05正确列出的周本节录。 |
| v2.7:N15 | 匹配 | B0078-1 0341a04、0352a01 | 仅追溯字面；身份、同期与位置另核 |
| v2.7:N16 | 匹配 | B0078-3 0472a04、0472a09 | 仅追溯字面；身份、同期与位置另核 |
| v2.7:N17 | 匹配 | B0077-2 0099a11—0099a13 | 仅追溯字面；身份、同期与位置另核 |
| v2.7:N18 | 匹配 | LF PDF-file-page-45;printed-page-44 | 仅追溯字面；身份、同期与位置另核 |
| v2.7:N19 | 人工 | B0078-3 0486a05 | 范电子正文显示㯋（鄴）；旧引采用鄴这一校正读法。史事无新增，需显示版本取舍。 |
| v2.7:N20 | 匹配 | B0078-1 0321a14—0322a03 | 仅追溯字面；身份、同期与位置另核 |
| B1:B01 | 匹配 | B0077-1 0047a04 | 仅追溯字面；身份、同期与位置另核 |
| B1:B02 | 匹配 | B0077-1 0073a07 | 仅追溯字面；身份、同期与位置另核 |
| B1:B03 | 匹配 | B0077-1 0043a15 | 仅追溯字面；身份、同期与位置另核 |
| B1:B04 | 匹配 | B0077-1 0083a11 | 仅追溯字面；身份、同期与位置另核 |
| B1:B05 | 匹配 | B0077-1 0044a14 | 仅追溯字面；身份、同期与位置另核 |
| B1:B06 | 匹配 | B0077-2 0099a11—0099a12 | 仅追溯字面；身份、同期与位置另核 |
| B1:B07 | 匹配 | B0077-2 0106a12 | 仅追溯字面；身份、同期与位置另核 |
| B1:B08 | 匹配 | B0077-2 0107a01 | 仅追溯字面；身份、同期与位置另核 |
| B1:B09 | 匹配 | B0077-2 0107a11 | 仅追溯字面；身份、同期与位置另核 |
| B1:B10 | 匹配 | B0077-3 0144a04 | 仅追溯字面；身份、同期与位置另核 |
| B1:B11 | 匹配 | B0077-3 0144a09 | 仅追溯字面；身份、同期与位置另核 |
| B1:B12 | 匹配 | B0077-3 0152a02—0152a03 | 仅追溯字面；身份、同期与位置另核 |
| B1:B13 | 匹配 | B0077-3 0153a08 | 仅追溯字面；身份、同期与位置另核 |
| B1:B14 | 匹配 | B0077-3 0145a01 | 仅追溯字面；身份、同期与位置另核 |
| B2:G01 | 匹配 | B0077-1 0080a05—0080a06；B0078-1 0386a04—0386a05 | 正文方位 |
| B2:G02 | 匹配 | B0077-1 0081a03、0081a07—0081a08；B0078-1 0386a13、0386a13—0386a14 | 正文构成 |
| B2:G03 | 匹配 | B0077-1 0080a08；B0078-1 0386a06 | 正文所属 |
| B2:G04 | 匹配 | B0077-1 0080a08—0080a09；B0078-1 0386a06—0386a07 | 正文内部关系 |
| B2:G05 | 匹配 | B0077-1 0080a10、0080a11；B0078-1 0386a07—0386a08、0386a08 | 正文方向＋回指解释 |
| B2:G06 | 匹配 | B0077-1 0080a13、0080a15—0081a01；B0078-1 0386a10、0386a11 | 正文方向＋数量总括 |
| B2:G07 | 匹配；另版 | B0078-1 0405a13、0405a14—0405a15 | 周本显式补魏字；旧引采用无补字的范本字面。 |
| B2:G08 | 匹配 | B0077-1 0093a05—0093a06；B0078-1 0405a15 | 正文营作／所属 |
| B2:G09 | 匹配 | B0077-1 0093a06；B0078-1 0405a15—0406a01 | 原文＋校补异说 |
| B2:G10 | 匹配 | B0077-1 0093a14；B0078-1 0406a03 | 原文＋现代校者解释 |
| B2:G11 | 匹配 | B0077-1 0094a01、0094a02、0094a04；B0078-1 0406a03—0406a04、0406a04、0406a05 | 正文方向＋前文回指前提 |
| B2:G12 | 匹配 | B0077-1 0094a04、0094a05；B0078-1 0406a05、0406a07 | 正文重复参照 |
| B2:G13 | 人工 | B0077-1 0094a12、0094a14、0095a11—0095a12；B0078-1 0406a11、0406a12、0407a02 | 三项不同性质问题：園中有柰林为篇章归属概括而非逐字句；都堂在柰林西，旧引误成碑西；扶桑为海，旧引误成殿。既有实体名录和约束已正确，新工作层修正旧证据卡，不新增实体。 |
| B2:G14 | 匹配 | B0077-1 0095a13—0095a14；B0078-1 0407a02—0407a03 | 正文集合联系 |
| B2:G15 | 人工 | B0077-1 0095a14—0096a01；B0078-1 0407a03—0407a04 | B8:CB14已判定旧引为压缩概述。本轮重新对电子正文相合，只继承既有更正，不算本阶段新发现。 |
| B2:G16 | 人工 | B0077-1 0067a06、0082a06 | 周本作入寺婬穢，旧引转写淫穢；范p0387a03–04还保留入瑤光寺婬穢。字形及删名须说明，侵扰没有提供寺毁明文。 |
| B3:W01 | 匹配 | B0077-4 0188a11；B0078-4 0542a07 | 仅追溯字面；身份、同期与位置另核 |
| B3:W02 | 匹配 | B0077-4 0188a11；B0078-4 0542a07 | 仅追溯字面；身份、同期与位置另核 |
| B3:W03 | 匹配 | B0077-4 0189a10；B0078-4 0542a12—0542a13 | 仅追溯字面；身份、同期与位置另核 |
| B3:W04 | 匹配 | B0077-4 0190a01；B0078-4 0543a02 | 仅追溯字面；身份、同期与位置另核 |
| B3:W05 | 匹配；另版 | B0078-4 0543a15 | 周本正文用延酤，范本用退酤；属于既有版本读法差别，不新增第二里。 |
| B3:W06 | 匹配；另版 | B0078-4 0544a10—0544a11 | 周本正文补有字；旧引采用范本未补字句。 |
| B3:W07 | 匹配；另版 | B0077-4 0193a02—0193a03 | 范本电子正文作準財，周本作阜財；名称取舍与既有校注条件保留。 |
| B3:W08 | 匹配；另版 | B0077-4 0193a09—0193a10、0193a15—0194a01 | 范本电子正文作準財里；旧引在周本可定位，不应把两版本相合说成逐字无异。 |
| B3:W09 | 匹配 | B0077-4 0188a11；B0078-4 0542a07 | 仅追溯字面；身份、同期与位置另核 |
| B3:W10 | 匹配 | B0077-4 0188a15；B0078-4 0542a08—0542a09 | 仅追溯字面；身份、同期与位置另核 |
| B3:W11 | 匹配 | B0077-4 0188a15；B0078-4 0542a09 | 仅追溯字面；身份、同期与位置另核 |
| B3:W12 | 匹配；另版 | B0077-4 0189a01 | 范本显示中（東）、釗（剛）的校正标记；台东侯刚采用校正读法，不是无条件的原传字面。 |
| B3:W13 | 匹配 | B0077-4 0189a04；B0078-4 0542a10 | 仅追溯字面；身份、同期与位置另核 |
| B3:W14 | 匹配；另版 | B0077-4 0195a03—0195a04 | 范本作退酤，周本作延酤；寿丘界域仍为原里距与范围句，不据此生成现代矩形。 |
| B3:W15 | 匹配；另版 | B0078-4 0546a12—0546a13、0547a09 | 周本文栢、范本文柏字形不同；两本都不是堂平面或尺度图。 |
| B3:W16 | 匹配 | B0077-4 0199a09；B0078-4 0548a12 | 仅追溯字面；身份、同期与位置另核 |
| B4:NG01 | 匹配 | B0077-1 0038a01—0038a02、0038a13 | 传世正文（按所标电子整理本） |
| B4:NG02 | 匹配 | B0078-1 0324a09—0324a10、0324a13 | 北魏营造归属采用周、范校读；传文混有曹魏旧楼叙述，不据此证明曹魏结构原样延续到516—528年。 |
| B4:NG03 | 匹配 | B0078-1 0324a14—0324a15 | 传世正文（按所标电子整理本） |
| B4:NG04 | 匹配 | B0077-5 0213a05 | 沿用旧基线undated；本次不改为516—528年必存。 |
| B4:NG05 | 匹配 | B0077-5 0213a05—0213a06 | 使用季节与建筑存在年份是不同字段。 |
| B4:NG06 | 匹配 | B0077-5 0214a02—0214a07 | 中朝旧用／正文叙述现在；转换确年未记。 |
| B4:NG07 | 匹配 | B0077-5 0214a14 | 传世正文（按所标电子整理本） |
| B4:NG08 | 匹配 | B0077-5 0215a10 | 传世正文（按所标电子整理本） |
| B4:NG09 | 匹配 | B0077-5 0215a08—0215a09 | 沿用基线attested_by_528；不宣称建寺在迁京当年或525年。 |
| B4:NG10 | 匹配 | B0077-5 0215a12、0215a14 | 传世正文（按所标电子整理本） |
| B4:NG11 | 匹配 | B0077-5 0215a15—0216a01 | 传世正文（按所标电子整理本） |
| B4:NG12 | 匹配 | B0077-5 0216a03、0216a10 | 传世正文（按所标电子整理本） |
| B4:NG13 | 匹配 | B0077-1 0037a03—0037a04 | 传世正文（按所标电子整理本） |
| B4:NG14 | 匹配 | B0077-1 0037a06—0037a08 | 校订正文；〔与〕为周校补字 |
| B4:NG15 | 人工 | B0077-1 0082a09；B0078-1 0387a06 | 城之西北門也处于周本small.inline-note；有字上疑有脫文亦为周注。旧引把第一条夹注接入古籍正文。古文仍支持瑶光寺北承明门，金墉接句不补空间距离。 |
| B4:NG16 | 匹配 | B0077-1 0083a03—0083a06 | 传世正文（按所标电子整理本） |
| B5:WR01 | 匹配 | B0077-1 0036a02、0036a03、0036a05、0036a08、0037a03 | 古籍正文短引（按所标电子整理本，夹注分离） |
| B5:WR02 | 匹配 | B0077-1 0043a11 | 古籍正文短引（按所标电子整理本，夹注分离） |
| B5:WR03 | 匹配 | B0077-4 0202a14 | 沿用attested_by_528；本批不从追谥文献或所立二字另定具体建寺年。 |
| B5:WR04 | 匹配 | B0077-4 0202a14、0202a15 | 寺院盛时状态与所述塔的单独竣工年分开；塔完工年份未明。 |
| B5:WR05 | 匹配 | B0077-4 0204a06—0204a07 | 大觉仍为undated；空间关系本身不解决其初设寺年。 |
| B5:WR06 | 匹配 | B0077-4 0204a06—0204a07、0205a01 | 沿用永明attested_by_528；不因与大觉相邻叙述而统一两寺年代。 |
| B5:WR07 | 匹配 | B0077-4 0205a03、0205a04 | 宣武所立支持既有盛时以前建寺层；本条未给具体建立年或各构件竣工年。 |
| B5:WR08 | 匹配 | B0077-4 0204a06、0204a10 | 保留undated；施主姓名与宅改寺叙述不足在本批确定初设寺的公元年。 |
| B5:WR09 | 匹配 | B0077-4 0204a14 | 明确晚于516—528盛时综合窗口；寺本体初设年仍未定。 |
| B5:WR10 | 匹配 | B0077-4 0204a07 | 景观描写不能单独证明建筑在某一盛时年份的完整状态。 |
| B5:WR11 | 匹配 | B0077-4 0184a12 | 沿用undated；本批未取得把寺与其全部构件限定于528年前的新增证据。 |
| B5:WR12 | 匹配 | B0077-4 0184a13 | 三层为所述类型，具体构件年代未定；不把塔像作为516—528已完工证据。 |
| B5:WR13 | 匹配 | B0077-4 0184a14、0184a14—0184a15、0186a01 | 普泰末属盛时窗口之后；赵逸说不能自动补成盛时连续存续证据。 |
| B5:WR14 | 匹配 | B0077-4 0186a04—0186a05 | 法云与宝光均保持undated；空间近邻不自动统一两寺建立时间。 |
| B5:WR15 | 匹配 | B0077-4 0186a08、0186a09 | 保留undated；摩罗活动与器物在寺叙述不单独确定建寺年。 |
| B5:WR16 | 匹配 | B0077-4 0187a04 | 沿用原宅记录；不从后出官衔反推某年宅第才建立。 |
| B5:WR17 | 匹配 | B0077-4 0175a05、0175a05—0175a06 | 沿用寺院attested_by_528；宅、寺、塔不是同一时点全部新建。 |
| B5:WR18 | 匹配 | B0077-4 0176a15、0177a12 | 沿用five_storey_after_525_completion_before_cutoff_unproved；不改为528年前必定竣工。 |
| B5:WR19 | 匹配 | B0077-4 0177a14—0177a15 | 沿用later_temple；地点与用途时间分别登记。 |
| B5:WR20 | 匹配 | B0077-4 0178a04—0178a05 | 沿用元颢529年败散后的寺院状态；不前推至525或528年。 |
| B5:WR21 | 匹配 | B0077-4 0181a08、0181a14 | 沿用attested_by_528及原有施主证据链；本批不把宣忠的529年改寺事件套给王典御。 |
| B5:WR22 | 匹配 | B0077-4 0208a01—0208a02、0208a08—0208a09 | 永安二年像事不是舍半宅的独立起始年；不把后续神异事件转换为改寺年表。 |
| B5:WR23 | 匹配 | B0077-4 0182a04 | 沿用undated；不由汉代建寺传统把全部建筑定为盛时必存。 |
| B5:WR24 | 匹配 | B0077-5 0263a04 | 两条均保留undated；不互相借年代补成连续建寺史。 |
| B6:EI01 | 匹配 | B0077-1 0033a12、0034a01、0034a07 | 古籍正文短引；开阳句的门字为周本正文采用、校语明示的补字 |
| B6:EI02 | 匹配 | B0077-1 0085a09、0086a04、0086a06 | 沿用 undated：本批未取得足以锁定528年河阴之变前这一寺院形态的证据；空心不表示必定晚出。 |
| B6:EI03 | 匹配 | B0077-1 0085a10 | 古籍正文采用校补、删衍后的周本读法；有字为显式校补，东西关系仅在校读解释中列注引 |
| B6:EI04 | 匹配 | B0078-1 0394a07—0394a08 | 古籍正文短引（按所标电子整理本，夹注分离） |
| B6:EI05 | 匹配 | B0078-1 0395a01、0395a02、0395a02—0395a03 | 昭仪池为本条所述池；石崇旧池和绿珠楼属于晋事追述，不自动视为北魏仍存建筑。 |
| B6:EI06 | 匹配 | B0077-1 0087a04 | 沿用 undated；王翊卒年及其官衔不等同建寺日期，本批不将寺院状态升级为河阴之变前实证。 |
| B6:EI07 | 匹配 | B0077-1 0087a07、0087a09、0087a11、0087a11—0087a12 | 愿会寺仍 undated；神桑砍伐的永熙时段只作为周注推定，不倒填为寺院始建年。 |
| B6:EI08 | 匹配 | B0078-1 0395a11、0395a15 | 光明沿用 undated；宅寺转换的先后清楚，转换年月未明。 |
| B6:EI09 | 匹配 | B0077-1 0088a05—0088a06、0088a09、0088a09—0088a10 | 266年只归所引像铭；寺院建立年月不明，维持 undated。 |
| B6:EI10 | 匹配 | B0078-1 0399a01—0399a02、0399a03 | 保留基线 attested_by_528 的寺院活动判断；五重描述未另有竣工纪年，亦不改为主图塔节点。 |
| B6:EI11 | 匹配 | B0078-1 0400a01、0400a03 | 沿用 undated，空心不表示寺院必在528年之后才建。 |
| B6:EI12 | 匹配 | B0077-1 0089a06—0089a07、0089a07—0089a08 | 沿用 undated。 |
| B6:EI13 | 匹配 | B0078-1 0400a05、0400a05、0400a05、0400a08—0400a09 | 正文当世贵里与董卓旧事分层；六位宅主的官衔列举不证明六宅在516—528某一年全部同期存在。 |
| B6:EI14 | 匹配 | B0078-1 0402a06、0402a07 | 景林沿用 undated；园本条无独立始建年，不增具体年代。 |
| B6:EI15 | 匹配 | B0078-1 0402a07—0402a08 | 禅房与小型精舍没有另立制作或落成年份；不据构件存在升级景林的 undated 状态。 |
| B6:EI16 | 匹配 | B0078-1 0402a11、0402a13 | 普泰531年仅作为所引任官语境；景林、园、石铭各自的营建或刻立年月仍未由本条确定。 |
| B6:EO01 | 匹配 | B0077-1 0033a04、0033a05、0033a12、0034a01 | 古籍正文短引（按所标电子整理本，夹注分离） |
| B6:EO02 | 匹配 | B0077-2 0111a10 | 沿用undated；空心表示截至528年前的寺院状态未获限定，不等于寺必晚出。 |
| B6:EO03 | 匹配 | B0077-2 0111a10 | 古籍正文短引（按所标电子整理本，夹注分离） |
| B6:EO04 | 匹配 | B0077-2 0112a02、0112a08、0112a11 | 沿用attested_by_528及胡太后立寺背景；本批不把其母卒年、追赠或寺名直接等同于建寺完工年。 |
| B6:EO05 | 匹配 | B0077-2 0113a08 | 寺院attested_by_528不自动证明这座五层塔在516—528全段已成。 |
| B6:EO06 | 匹配 | B0077-2 0116a12—0116a15 | 正始年号504—508；立寺时段与捐款、后人刊碑分开，不能精确为504年建成。 |
| B6:EO07 | 匹配 | B0077-2 0116a15—0117a01 | 古籍正文短引（按所标电子整理本，夹注分离） |
| B6:EO08 | 匹配 | B0077-2 0117a08 | 古籍正文短引（按所标电子整理本，夹注分离） |
| B6:EO09 | 匹配 | B0077-2 0123a06、0123a10 | 寺院盛时依据见EO10；五层塔另见EO11，不能由舍宅句合并两种时层。 |
| B6:EO10 | 匹配 | B0077-2 0124a01 | 沿用attested_by_528的寺本体时层；金像年代和物理身份未统一，不能据此指定盛时金像细部。 |
| B6:EO11 | 匹配 | B0077-2 0130a13、0131a01—0131a02 | 532始造；完成年候选533、534均在516—528主层之外。 |
| B6:EO12 | 匹配 | B0077-2 0131a13—0131a14 | 沿用高祖迁洛后创居、遂分宅的较早叙事链，attested_by_528；不另报确定完工年。 |
| B6:EO13 | 匹配 | B0077-2 0132a06—0132a07 | 普泰元年531事件之后；上限和完工日未知。盛时不画建中寺状态。 |
| B6:EO14 | 匹配 | B0077-2 0132a08 | 古籍正文短引（按所标电子整理本，夹注分离） |
| B6:EO15 | 匹配 | B0077-2 0105a15—0106a02 | 沿用既有attested_by_528记录，但时层继承取决于两次宝明记载的候选同一性；不得抹去条件。 |
| B6:EO16 | 匹配 | B0077-2 0132a10 | 古籍正文短引（按所标电子整理本，夹注分离） |
| B6:EO17 | 匹配 | B0077-2 0139a05—0139a06 | 古籍正文短引（按所标电子整理本，夹注分离） |
| B6:EO18 | 匹配 | B0077-2 0139a06、0139a07—0139a08 | 永安528—530，河阴之后；普泰元年像事为更晚的寺中叙事，不是建寺完工日。 |
| B7:LG01 | 匹配 | B0077-3 0160a06—0160a07、0160a07 | 古籍正文短引（按所标电子整理本，夹注分离） |
| B7:LG02 | 匹配 | B0077-3 0160a07、0160a08 | 采用周校释正文的目录短引；馆名及馆里区分涉及校补，非声称底本完整无异 |
| B7:LG03 | 匹配 | B0077-3 0160a14 | 三年是本句的相对等待期，没有给出统一起算年或馆里建成年。 |
| B7:LG04 | 匹配 | B0077-3 0161a10—0161a11 | 明确的是这条制度叙述中的三年等待期；下文个案与季节性入侍另记，不同于统一建成年。 |
| B7:LG05 | 匹配 | B0077-3 0161a12、0162a03、0162a04—0162a05 | 正光元年（520）为此来朝事件的正文纪年；不是馆里建成年。个案赐宅的独立日期未记。 |
| B7:LG06 | 匹配 | B0077-3 0162a05—0162a06 | 季节模式无独立年度与精确日期；不据此为馆里增加始建、停用或拆迁年。 |
| B7:LG07 | 匹配 | B0077-3 0162a08—0162a10 | 东、西两组授宅等待时间未明写；本批不从吴、北两句移入三年。 |
| B7:LG08 | 匹配 | B0077-3 0162a10—0162a12 | 古籍正文短引（按所标电子整理本，夹注分离） |
| B7:LG09 | 匹配 | B0077-3 0162a12—0162a13 | 古籍正文短引（按所标电子整理本，夹注分离） |
| B7:LG10 | 匹配 | B0077-3 0161a07—0161a08 | 来降纪年：正文正光四年523；周注转引史载正光三年522。本批未裁决，且二者都不是归正寺的独立创建纪年。 |
| B7:LG11 | 匹配 | B0078-3 0500a09 | 保持undated；创建年、完工年未知。萧正德来降纪年和吴人一般三年授宅制度均不能替代本寺的独立年代证据。 |
| B7:LR01 | 匹配 | B0077-3 0158a06—0158a07 | 桥的记述属于文献场景，建桥、重建和持续通行的起讫年月均未记。 |
| B7:LR02 | 匹配 | B0077-3 0158a09、0160a03 | 神龟518—520为作颂时段，不等于桥始建、完工或维修时段。 |
| B7:LR03 | 匹配 | B0077-3 0160a04—0160a05 | 华表营造年未记；不自动与神龟作颂同年。 |
| B7:LR04 | 匹配 | B0077-3 0160a06—0160a07 | 古籍正文短引（按所标电子整理本，夹注分离） |
| B7:LR05 | 匹配 | B0077-3 0144a14、0145a01—0145a02 | 四月七日集像、八日入城是仪式叙述；未给本批可独立落到某公历年的桥梁通行事件。 |
| B7:LR06 | 匹配 | B0077-3 0161a01、0161a04—0161a05、0161a07 | 景明初提供初来背景；迁入永安里在世宗朝，具体年未记。归正里宅在盛时只作旧宅附见，不推断宅已毁。 |
| B7:LR07 | 匹配 | B0077-2 0132a12—0132a13、0132a14、0132a15 | 巷市成立年未明；张景仁受宅或迁居的年号不自动成为市场创建年。 |
| B7:LR08 | 匹配 | B0077-2 0132a11—0132a13、0132a15—0133a01 | 正光520—525／范校景明500—503只是年号范围；原文初字不等于必在元年。后述永安二年酒宴另属529事件，不能用于巷市建成年。 |
| B7:LR09 | 匹配 | B0077-2 0132a13—0132a15 | 古籍正文短引（按所标电子整理本，夹注分离） |
| B7:LR10 | 匹配 | B0077-3 0162a15—0163a02 | 四通市新设年未记；附化商民背景和采购描写不生成明确营建年。 |
| B7:LR11 | 匹配 | B0077-3 0165a02 | 沿用undated；后接故事的太后、明帝语境只记叙事时层，不据此裁定寺院始建年或每年存续。 |
| B7:LR12 | 匹配 | B0077-3 0163a04 | 两坊共同列名不等于两种动物在516—528年同时在场；动物时层见LR13、LR14。 |
| B7:LR13 | 匹配 | B0077-3 0163a06、0163a11—0163a12、0163a14 | 永平二年509为入贡；后在胡太后时期徙坊，具体年未记。诏徙不提供建筑完工日期。 |
| B7:LR14 | 匹配 | B0077-3 0164a05、0164a12、0164a13、0164a14—0164a15 | 正文永安末；Z3注引对应530。普泰元年531送归诏令及途中杀弃，均不进入516—528河阴之前的活狮场景。 |

## 附录B：236处字面约束逐条清单

候选ID仅用于目录跳转；空白候选以“—”表示，没有自动新增实体。原约束和每种语义的具体说明在JSON中保留。

| 序号 | 原实体与约束索引 | 原目标 | 语义类别 | 候选ID |
|---|---|---|---|---|
| 1 | v2_mingxuan [0] | 建春门 | unique_catalog_name_link | gate_jianchun |
| 2 | v2_mingxuan [1] | 建春门石桥 | unique_catalog_name_link | bridge_jianchun |
| 3 | v2_longhua [0] | 建春门 | unique_catalog_name_link | gate_jianchun |
| 4 | v2_longhua [1] | 阳渠 | unique_catalog_name_link | water_yangqu |
| 5 | v2_longhua [2] | 租场〔常满仓旧址〕 | unique_catalog_name_link | v2_changmancang |
| 6 | v2_yingluo [0] | 建春门 | unique_catalog_name_link | gate_jianchun |
| 7 | v2_yingluo [1] | 建春门外御道 | unique_catalog_name_link | road_jianchun |
| 8 | v2_yingluo [2] | 建阳里 | unique_catalog_name_link | li_jianyang |
| 9 | v2_cishan [0] | 建阳里 | unique_catalog_name_link | li_jianyang |
| 10 | v2_huihe [0] | 建阳里 | unique_catalog_name_link | li_jianyang |
| 11 | v2_tongjue [0] | 建阳里 | unique_catalog_name_link | li_jianyang |
| 12 | v2_huixuan [0] | 建阳里 | unique_catalog_name_link | li_jianyang |
| 13 | v2_zongsheng [0] | 建阳里 | unique_catalog_name_link | li_jianyang |
| 14 | v2_xiping [0] | 建阳里 | unique_catalog_name_link | li_jianyang |
| 15 | v2_chongzhen [0] | 建阳里 | unique_catalog_name_link | li_jianyang |
| 16 | v2_yinguo [0] | 建阳里 | unique_catalog_name_link | li_jianyang |
| 17 | v2_weichang [0] | 建阳里 | unique_catalog_name_link | li_jianyang |
| 18 | v2_weichang [1] | 东石桥 | unique_catalog_name_link | bridge_eaststone |
| 19 | v2_weichang [2] | 中朝牛马市 | unique_catalog_name_link | v2_horsemarket |
| 20 | v2_jingxing [0] | 东石桥 | unique_catalog_name_link | bridge_eaststone |
| 21 | v2_baoming [0] | 洛阳城 | regional_reference | — |
| 22 | v2_baoming [1] | 苏秦冢 | unique_catalog_name_link | tomb_suqin |
| 23 | v2_baoming [2] | 孝义里 | unique_catalog_name_link | li_xiaoyi |
| 24 | xref_banruo [0] | 洛阳城 | regional_reference | — |
| 25 | xref_chanlin [0] | 洛阳城 | regional_reference | — |
| 26 | xref_lingjue [0] | 洛阳城 | regional_reference | — |
| 27 | v2_taikang [0] | 杜子休宅 | unique_catalog_name_link | house_duzixiu |
| 28 | v2_taikang [1] | 崇义里 | unique_catalog_name_link | li_chongyi |
| 29 | v2_lingying [0] | 杜子休宅 | unique_catalog_name_link | house_duzixiu |
| 30 | v2_lingying [1] | 崇义里 | unique_catalog_name_link | li_chongyi |
| 31 | v2_lingying [2] | 建春门外御道 | unique_catalog_name_link | road_jianchun |
| 32 | v2_zhuangyan [0] | 东阳门 | unique_catalog_name_link | gate_dongyang |
| 33 | v2_zhuangyan [1] | 东阳门外御道 | unique_catalog_name_link | road_dongyang |
| 34 | v2_zhuangyan [2] | 东安里 | unique_catalog_name_link | li_dongan |
| 35 | v2_zhuangyan [3] | 租场〔东安里北〕 | unique_catalog_name_link | v2_dongan_taxfield |
| 36 | v2_qintaishangjun [0] | 东阳门 | unique_catalog_name_link | gate_dongyang |
| 37 | v2_qintaishangjun [1] | 东阳门外御道 | unique_catalog_name_link | road_dongyang |
| 38 | v2_qintaishangjun [2] | 晖文里 | unique_catalog_name_link | li_huiwen |
| 39 | v2_zhengshi [0] | 东阳门 | unique_catalog_name_link | gate_dongyang |
| 40 | v2_zhengshi [1] | 东阳门外御道 | unique_catalog_name_link | road_dongyang |
| 41 | v2_zhengshi [2] | 敬义里 | unique_catalog_name_link | li_jingyi |
| 42 | v2_pingdeng [0] | 清阳门 | unique_catalog_name_link | gate_qingyang |
| 43 | v2_pingdeng [1] | 清阳门外御道 | unique_catalog_name_link | road_qingyang |
| 44 | v2_pingdeng [2] | 孝敬里 | unique_catalog_name_link | li_xiaojing |
| 45 | v2_pingdeng [3] | 广平王怀宅〔平等寺址〕 | prior_use_state | — |
| 46 | v2_jingning [0] | 清阳门 | unique_catalog_name_link | gate_qingyang |
| 47 | v2_jingning [1] | 清阳门外御道 | unique_catalog_name_link | road_qingyang |
| 48 | v2_jingning [2] | 景宁里 | unique_catalog_name_link | li_jingning |
| 49 | v2_jingning [3] | 杨椿宅 | unique_catalog_name_link | house_yangchun |
| 50 | v2_jianzhong [0] | 杨氏家宅 | prior_use_state | — |
| 51 | v2_jianzhong [1] | 景宁里 | unique_catalog_name_link | li_jingning |
| 52 | v2_guijue [0] | 刘胡兄弟宅 | unique_catalog_name_link | house_liuhu |
| 53 | v2_guijue [1] | 殖货里 | unique_catalog_name_link | li_zhihuo |
| 54 | road_jianchun [0] | 建春门 | unique_catalog_name_link | gate_jianchun |
| 55 | bridge_jianchun [0] | 建春门 | unique_catalog_name_link | gate_jianchun |
| 56 | bridge_jianchun [1] | 谷水／阳渠 | contextual_water_names | gushui、water_yangqu |
| 57 | water_yangqu [0] | 建春门 | unique_catalog_name_link | gate_jianchun |
| 58 | water_yangqu [1] | 建阳里 | unique_catalog_name_link | li_jianyang |
| 59 | water_yangqu [2] | 龙华寺〔城东〕 | unique_catalog_name_link | v2_longhua |
| 60 | v2_changmancang [0] | 明悬尼寺 | unique_catalog_name_link | v2_mingxuan |
| 61 | v2_changmancang [1] | 龙华寺〔城东〕 | unique_catalog_name_link | v2_longhua |
| 62 | li_jianyang [0] | 阳渠 | unique_catalog_name_link | water_yangqu |
| 63 | li_jianyang [1] | 建春门外御道 | unique_catalog_name_link | road_jianchun |
| 64 | li_jianyang [2] | 东石桥北大道 | unique_catalog_name_link | road_eaststone_north |
| 65 | v2_qiting [0] | 建阳里 | unique_catalog_name_link | li_jianyang |
| 66 | xref_ningxiantang [0] | 宫城 | scope_reference | palace_scope |
| 67 | bridge_eaststone [0] | 建春门 | unique_catalog_name_link | gate_jianchun |
| 68 | bridge_eaststone [1] | 南北 | orientation_value | — |
| 69 | road_eaststone_north [0] | 东石桥 | unique_catalog_name_link | bridge_eaststone |
| 70 | road_eaststone_north [1] | 建阳里／绥民里 | compound_both_sides | li_jianyang、li_suimin |
| 71 | v2_horsemarket [0] | 东石桥 | unique_catalog_name_link | bridge_eaststone |
| 72 | v2_horsemarket [1] | 魏昌尼寺 | unique_catalog_name_link | v2_weichang |
| 73 | li_suimin [0] | 建阳里 | unique_catalog_name_link | li_jianyang |
| 74 | li_suimin [1] | 东石桥北大道 | unique_catalog_name_link | road_eaststone_north |
| 75 | office_luoyang [0] | 绥民里 | unique_catalog_name_link | li_suimin |
| 76 | office_luoyang [1] | 渠水〔此段〕 | unresolved_water_segment | — |
| 77 | li_chongyi [0] | 绥民里 | unique_catalog_name_link | li_suimin |
| 78 | house_duzixiu [0] | 崇义里 | unique_catalog_name_link | li_chongyi |
| 79 | house_duzixiu [1] | 建春门外御道 | unique_catalog_name_link | road_jianchun |
| 80 | house_duzixiu [2] | 灵应寺 | unique_catalog_name_link | v2_lingying |
| 81 | v2_taiwei_oldstupa [0] | 太尉府 | unique_catalog_name_link | ic_taiwei |
| 82 | bridge_qili [0] | 崇义里 | unique_catalog_name_link | li_chongyi |
| 83 | gate_sanmen [0] | 七里桥 | unique_catalog_name_link | bridge_qili |
| 84 | road_dongyang [0] | 东阳门 | unique_catalog_name_link | gate_dongyang |
| 85 | li_dongan [0] | 东阳门 | unique_catalog_name_link | gate_dongyang |
| 86 | li_dongan [1] | 东阳门外御道 | unique_catalog_name_link | road_dongyang |
| 87 | v2_dongan_taxfield [0] | 庄严寺／东安里 | ambiguous_antecedent | v2_zhuangyan、li_dongan |
| 88 | li_huiwen [0] | 东阳门外御道 | unique_catalog_name_link | road_dongyang |
| 89 | li_huiwen [1] | 秦太上君寺 | unique_catalog_name_link | v2_qintaishangjun |
| 90 | li_jingyi [0] | 东阳门外御道 | unique_catalog_name_link | road_dongyang |
| 91 | office_dianyu [0] | 敬义里 | unique_catalog_name_link | li_jingyi |
| 92 | li_zhaode [0] | 敬义里 | unique_catalog_name_link | li_jingyi |
| 93 | v2_jingyangshan [0] | 张伦宅园 | nested_scope_reference | house_zhanglun |
| 94 | v2_jingyangshan [1] | 昭德里 | unique_catalog_name_link | li_zhaode |
| 95 | road_qingyang [0] | 清阳门 | unique_catalog_name_link | gate_qingyang |
| 96 | li_xiaojing [0] | 清阳门外御道 | unique_catalog_name_link | road_qingyang |
| 97 | li_xiaojing [1] | 平等寺 | unique_catalog_name_link | v2_pingdeng |
| 98 | li_jingning [0] | 清阳门外御道 | unique_catalog_name_link | road_qingyang |
| 99 | li_jingning [1] | 景宁寺 | unique_catalog_name_link | v2_jingning |
| 100 | li_xiaoyi [0] | 清阳门 | unique_catalog_name_link | gate_qingyang |
| 101 | li_xiaoyi [1] | 清阳门外御道 | unique_catalog_name_link | road_qingyang |
| 102 | tomb_suqin [0] | 孝义里 | unique_catalog_name_link | li_xiaoyi |
| 103 | tomb_suqin [1] | 宝明寺 | unique_catalog_name_link | v2_baoming |
| 104 | market_small [0] | 孝义里 | unique_catalog_name_link | li_xiaoyi |
| 105 | li_zhihuo [0] | 洛阳小市 | unique_catalog_name_link | market_small |
| 106 | li_zhihuo [1] | 孝义里 | unique_catalog_name_link | li_xiaoyi |
| 107 | house_liuxuanming [0] | 绥民里 | unique_catalog_name_link | li_suimin |
| 108 | house_simayue [0] | 东安里 | unique_catalog_name_link | li_dongan |
| 109 | house_daoxuan [0] | 东安里 | unique_catalog_name_link | li_dongan |
| 110 | house_lizhennu [0] | 东安里 | unique_catalog_name_link | li_dongan |
| 111 | house_gongsunxiang [0] | 东安里 | unique_catalog_name_link | li_dongan |
| 112 | house_cuiguang [0] | 晖文里 | unique_catalog_name_link | li_huiwen |
| 113 | house_liyanshi [0] | 晖文里 | unique_catalog_name_link | li_huiwen |
| 114 | house_lishao [0] | 晖文里 | unique_catalog_name_link | li_huiwen |
| 115 | house_zhengdaozhao [0] | 晖文里 | unique_catalog_name_link | li_huiwen |
| 116 | house_youzhao [0] | 昭德里 | unique_catalog_name_link | li_zhaode |
| 117 | house_libiao [0] | 昭德里 | unique_catalog_name_link | li_zhaode |
| 118 | house_cuixiu [0] | 昭德里 | unique_catalog_name_link | li_zhaode |
| 119 | house_changjing [0] | 昭德里 | unique_catalog_name_link | li_zhaode |
| 120 | house_zhanglun [0] | 昭德里 | unique_catalog_name_link | li_zhaode |
| 121 | house_yangchun [0] | 景宁里 | unique_catalog_name_link | li_jingning |
| 122 | house_liuhu [0] | 殖货里 | unique_catalog_name_link | li_zhihuo |
| 123 | house_xiuhe [0] | 李延寔宅 | unique_catalog_name_link | house_liyanshi |
| 124 | house_zhangjingren [0] | 洛阳小市 | unique_catalog_name_link | market_small |
| 125 | house_zhangjingren [1] | 孝义里 | unique_catalog_name_link | li_xiaoyi |
| 126 | v3_jingming [0] | 宣阳门 | unique_catalog_name_link | gate_xuanyang |
| 127 | v3_jingming [1] | 宣阳门外御道 | unique_catalog_name_link | road_xuanyang |
| 128 | v3_jingming [2] | 寺院 | self_extent_attribute | — |
| 129 | v3_datong [0] | 景明寺 | unique_catalog_name_link | v3_jingming |
| 130 | v3_datong [1] | 利民里 | unique_catalog_name_link | li_limin |
| 131 | v3_zhaofu [0] | 高显略／高显洛宅 | unique_catalog_name_link | house_gaoxian |
| 132 | v3_zhaofu [1] | 大统寺 | unique_catalog_name_link | v3_datong |
| 133 | v3_qintaigong_w [0] | 景明寺 | unique_catalog_name_link | v3_jingming |
| 134 | v3_qintaigong_w [1] | 秦太上公东寺 | unique_catalog_name_link | v3_qintaigong_e |
| 135 | v3_qintaigong_w [2] | 洛水 | unique_catalog_name_link | luoshui |
| 136 | v3_qintaigong_e [0] | 景明寺 | unique_catalog_name_link | v3_jingming |
| 137 | v3_qintaigong_e [1] | 秦太上公西寺 | unique_catalog_name_link | v3_qintaigong_w |
| 138 | v3_qintaigong_e [2] | 洛水 | unique_catalog_name_link | luoshui |
| 139 | v3_baode [0] | 开阳门 | unique_catalog_name_link | gate_kaiyang |
| 140 | v3_wenjue_dajue [0] | 劝学里 | unique_catalog_name_link | li_quanxue |
| 141 | v3_sanbao [0] | 劝学里 | unique_catalog_name_link | li_quanxue |
| 142 | v3_ningyuan [0] | 劝学里 | unique_catalog_name_link | li_quanxue |
| 143 | v3_zhengjue [0] | 延贤里 | unique_catalog_name_link | li_yanxian |
| 144 | v3_longhua [0] | 报德寺 | unique_catalog_name_link | v3_baode |
| 145 | v3_zhuisheng [0] | 报德寺 | unique_catalog_name_link | v3_baode |
| 146 | v3_guizheng [0] | 归正里 | unique_catalog_name_link | li_guizheng |
| 147 | v3_guizheng [1] | 萧正德宅 | contextual_name_link | house_xiaozhengde |
| 148 | v3_puti [0] | 慕义里 | unique_catalog_name_link | li_muyi |
| 149 | v3_gaoyang [0] | 津阳门 | unique_catalog_name_link | gate_jinyang |
| 150 | v3_gaoyang [1] | 津阳门外御道 | unique_catalog_name_link | road_jinyang |
| 151 | v3_gaoyang [2] | 高阳王雍宅 | unique_catalog_name_link | house_gaoyang |
| 152 | v3_chongxu [0] | 洛阳城 | regional_reference | — |
| 153 | v3_chongxu [1] | 汉濯龙园 | disputed_period_identity_claim | garden_zhuolong |
| 154 | road_xuanyang [0] | 宣阳门 | unique_catalog_name_link | gate_xuanyang |
| 155 | li_limin [0] | 大统寺 | unique_catalog_name_link | v3_datong |
| 156 | house_gaoxian [0] | 大统寺 | unique_catalog_name_link | v3_datong |
| 157 | v3_lingtai [0] | 秦太上公二寺 | ambiguous_group_antecedent | v3_qintaigong_e、v3_qintaigong_w |
| 158 | v3_biyong [0] | 灵台 | unique_catalog_name_link | v3_lingtai |
| 159 | v3_mingtang [0] | 辟雍 | unique_catalog_name_link | v3_biyong |
| 160 | v3_lingtai_stupa [0] | 灵台 | unique_catalog_name_link | v3_lingtai |
| 161 | v3_muzheng [0] | 明堂 | unique_catalog_name_link | v3_mingtang |
| 162 | road_kaiyang [0] | 开阳门 | unique_catalog_name_link | gate_kaiyang |
| 163 | v3_hanguozixue [0] | 开阳门御道 | unique_catalog_name_link | road_kaiyang |
| 164 | v3_shijing [0] | 汉国子学堂〔石经遗址〕 | unique_catalog_name_link | v3_hanguozixue |
| 165 | li_quanxue [0] | 汉国子学堂〔石经遗址〕 | unique_catalog_name_link | v3_hanguozixue |
| 166 | li_quanxue [1] | 文觉寺／大觉寺〔劝学里〕 | unique_catalog_name_link | v3_wenjue_dajue |
| 167 | li_quanxue [2] | 三宝寺 | unique_catalog_name_link | v3_sanbao |
| 168 | li_quanxue [3] | 宁远寺 | unique_catalog_name_link | v3_ningyuan |
| 169 | li_yanxian [0] | 劝学里 | unique_catalog_name_link | li_quanxue |
| 170 | bridge_yong [0] | 宣阳门 | unique_catalog_name_link | gate_xuanyang |
| 171 | bridge_yong [1] | 洛水 | unique_catalog_name_link | luoshui |
| 172 | v3_yong_huabiao [0] | 永桥／洛水 | compound_distinct_roles | bridge_yong、luoshui |
| 173 | altar_yuanqiu [0] | 四夷馆里区域 | aggregate_scope_reference | — |
| 174 | road_siyi [0] | 永桥 | unique_catalog_name_link | bridge_yong |
| 175 | road_siyi [1] | 圜丘 | unique_catalog_name_link | altar_yuanqiu |
| 176 | road_siyi [2] | 伊水／洛水 | compound_boundary_rivers | water_yi、luoshui |
| 177 | guan_jinling [0] | 永桥南御道〔四夷馆里段〕 | unique_catalog_name_link | road_siyi |
| 178 | guan_jinling [1] | 永桥 | unique_catalog_name_link | bridge_yong |
| 179 | guan_jinling [2] | 圜丘 | unique_catalog_name_link | altar_yuanqiu |
| 180 | guan_jinling [3] | 伊水／洛水 | compound_boundary_rivers | water_yi、luoshui |
| 181 | guan_yanran [0] | 永桥南御道〔四夷馆里段〕 | unique_catalog_name_link | road_siyi |
| 182 | guan_yanran [1] | 永桥 | unique_catalog_name_link | bridge_yong |
| 183 | guan_yanran [2] | 圜丘 | unique_catalog_name_link | altar_yuanqiu |
| 184 | guan_yanran [3] | 伊水／洛水 | compound_boundary_rivers | water_yi、luoshui |
| 185 | guan_fusang [0] | 永桥南御道〔四夷馆里段〕 | unique_catalog_name_link | road_siyi |
| 186 | guan_fusang [1] | 永桥 | unique_catalog_name_link | bridge_yong |
| 187 | guan_fusang [2] | 圜丘 | unique_catalog_name_link | altar_yuanqiu |
| 188 | guan_fusang [3] | 伊水／洛水 | compound_boundary_rivers | water_yi、luoshui |
| 189 | guan_yanzi [0] | 永桥南御道〔四夷馆里段〕 | unique_catalog_name_link | road_siyi |
| 190 | guan_yanzi [1] | 永桥 | unique_catalog_name_link | bridge_yong |
| 191 | guan_yanzi [2] | 圜丘 | unique_catalog_name_link | altar_yuanqiu |
| 192 | guan_yanzi [3] | 伊水／洛水 | compound_boundary_rivers | water_yi、luoshui |
| 193 | li_guizheng [0] | 永桥南御道〔四夷馆里段〕 | unique_catalog_name_link | road_siyi |
| 194 | li_guizheng [1] | 永桥 | unique_catalog_name_link | bridge_yong |
| 195 | li_guizheng [2] | 圜丘 | unique_catalog_name_link | altar_yuanqiu |
| 196 | li_guizheng [3] | 伊水／洛水 | compound_boundary_rivers | water_yi、luoshui |
| 197 | li_guide [0] | 永桥南御道〔四夷馆里段〕 | unique_catalog_name_link | road_siyi |
| 198 | li_guide [1] | 永桥 | unique_catalog_name_link | bridge_yong |
| 199 | li_guide [2] | 圜丘 | unique_catalog_name_link | altar_yuanqiu |
| 200 | li_guide [3] | 伊水／洛水 | compound_boundary_rivers | water_yi、luoshui |
| 201 | li_muhua [0] | 永桥南御道〔四夷馆里段〕 | unique_catalog_name_link | road_siyi |
| 202 | li_muhua [1] | 永桥 | unique_catalog_name_link | bridge_yong |
| 203 | li_muhua [2] | 圜丘 | unique_catalog_name_link | altar_yuanqiu |
| 204 | li_muhua [3] | 伊水／洛水 | compound_boundary_rivers | water_yi、luoshui |
| 205 | li_muyi [0] | 永桥南御道〔四夷馆里段〕 | unique_catalog_name_link | road_siyi |
| 206 | li_muyi [1] | 永桥 | unique_catalog_name_link | bridge_yong |
| 207 | li_muyi [2] | 圜丘 | unique_catalog_name_link | altar_yuanqiu |
| 208 | li_muyi [3] | 伊水／洛水 | compound_boundary_rivers | water_yi、luoshui |
| 209 | market_sitong [0] | 洛水 | unique_catalog_name_link | luoshui |
| 210 | market_fish [0] | 归正里 | unique_catalog_name_link | li_guizheng |
| 211 | fang_whiteelephant [0] | 永桥 | unique_catalog_name_link | bridge_yong |
| 212 | fang_whiteelephant [1] | 永桥南御道〔四夷馆里段〕 | unique_catalog_name_link | road_siyi |
| 213 | fang_lion [0] | 永桥 | unique_catalog_name_link | bridge_yong |
| 214 | fang_lion [1] | 永桥南御道〔四夷馆里段〕 | unique_catalog_name_link | road_siyi |
| 215 | xref_chenghuang [0] | 白象 | nonbuilt_object | — |
| 216 | li_fucai [0] | 洛阳城 | regional_reference | — |
| 217 | road_jinyang [0] | 津阳门 | unique_catalog_name_link | gate_jinyang |
| 218 | house_gaoyang [0] | 津阳门 | unique_catalog_name_link | gate_jinyang |
| 219 | house_gaoyang [1] | 津阳门外御道 | unique_catalog_name_link | road_jinyang |
| 220 | house_gaoyang [2] | 高阳王寺 | unique_catalog_name_link | v3_gaoyang |
| 221 | li_zhonggan [0] | 高阳王雍宅 | unique_catalog_name_link | house_gaoyang |
| 222 | li_zhaoyi [0] | 洛阳城 | regional_reference | — |
| 223 | house_yuanshikang [0] | 清阳门 | unique_catalog_name_link | gate_qingyang |
| 224 | garden_zhuolong [0] | 崇虚寺 | unique_catalog_name_link | v3_chongxu |
| 225 | excluded_luozhiyuan_house [0] | 灵台 | unique_catalog_name_link | v3_lingtai |
| 226 | excluded_luozhiyuan_house [1] | 洛水 | unique_catalog_name_link | luoshui |
| 227 | house_xiaozhengde [0] | 归正里 | unique_catalog_name_link | li_guizheng |
| 228 | house_xiaozhengde [1] | 归正寺 | unique_catalog_name_link | v3_guizheng |
| 229 | house_xiaobaoyin [0] | 归正里 | unique_catalog_name_link | li_guizheng |
| 230 | house_xiaobaoyin [1] | 永安里 | unique_catalog_name_link | li_yongan |
| 231 | li_yongan [0] | 洛阳城 | regional_reference | — |
| 232 | n_wenyi [0] | luoyang_city | regional_reference | — |
| 233 | e_shiguan [0] | luoyang_city | regional_reference | — |
| 234 | r_guankou [0] | luoyang_city | regional_reference | — |
| 235 | r_chanjian [0] | luoyang_city | regional_reference | — |
| 236 | a_wangnan [0] | city_reference_in_jinyong_context | ambiguous_city_antecedent | — |

## 附录C：取得的来源目录

每份来源的实际取得日期、原字节SHA-256及解析规则保存在JSON。下列同书整理本不互相计作独立史证。

| 快照键 | 来源入口 | 文本范围 |
|---|---|---|
| B0077-1 | [周祖谟校释卷1](https://deerpark.app/cbeta/B0077/1) | 古籍正文及古书子注保留；small.inline-note现代夹注单列。非夹注流也含前言，匹配位置须结合篇章定位。 |
| B0077-2 | [周祖谟校释卷2](https://deerpark.app/cbeta/B0077/2) | 古籍正文及古书子注保留；small.inline-note现代夹注单列。非夹注流也含前言，匹配位置须结合篇章定位。 |
| B0077-3 | [周祖谟校释卷3](https://deerpark.app/cbeta/B0077/3) | 古籍正文及古书子注保留；small.inline-note现代夹注单列。非夹注流也含前言，匹配位置须结合篇章定位。 |
| B0077-4 | [周祖谟校释卷4](https://deerpark.app/cbeta/B0077/4) | 古籍正文及古书子注保留；small.inline-note现代夹注单列。非夹注流也含前言，匹配位置须结合篇章定位。 |
| B0077-5 | [周祖谟校释卷5](https://deerpark.app/cbeta/B0077/5) | 古籍正文及古书子注保留；small.inline-note现代夹注单列。非夹注流也含前言，匹配位置须结合篇章定位。 |
| B0078-1 | [范祥雍校注卷1](https://deerpark.app/cbeta/B0078/1) | 古籍正文及古书子注保留；small.inline-note现代夹注单列。非夹注流也含前言，匹配位置须结合篇章定位。 |
| B0078-2 | [范祥雍校注卷2](https://deerpark.app/cbeta/B0078/2) | 古籍正文及古书子注保留；small.inline-note现代夹注单列。非夹注流也含前言，匹配位置须结合篇章定位。 |
| B0078-3 | [范祥雍校注卷3](https://deerpark.app/cbeta/B0078/3) | 古籍正文及古书子注保留；small.inline-note现代夹注单列。非夹注流也含前言，匹配位置须结合篇章定位。 |
| B0078-4 | [范祥雍校注卷4](https://deerpark.app/cbeta/B0078/4) | 古籍正文及古书子注保留；small.inline-note现代夹注单列。非夹注流也含前言，匹配位置须结合篇章定位。 |
| B0078-5 | [范祥雍校注卷5](https://deerpark.app/cbeta/B0078/5) | 古籍正文及古书子注保留；small.inline-note现代夹注单列。非夹注流也含前言，匹配位置须结合篇章定位。 |
| H | [《河南志》后魏城阙古迹电子转录](https://zh.wikisource.org/wiki/河南志) | 河南志自身条目小字保留，限定后魏城阙古迹；不把后出汇编当北魏目击。 |
| W | [《水经注集释订讹》卷十六所载经注](https://zh.wikisource.org/wiki/水經注集釋訂訛_(四庫全書本)/卷16) | 剥离small中的后出集释或校按，保留所载经注正文。 |
| W16 | [《水经注》四部丛刊本卷十六电子转录](https://zh.wikisource.org/wiki/水經注_(四部叢刊本)/卷第十六) | 剥离small中的后出集释或校按，保留所载经注正文。 |
| L3S | [《洛阳伽蓝记》四部丛刊本卷三电子转录](https://zh.wikisource.org/wiki/洛陽伽藍記_(四部叢刊本)/卷三) | 电子转录正文；未逐叶核书影。 |
| LF | [范祥雍校注 CBETA 电子重排 PDF](https://dlbs.liberal.ntu.edu.tw/FULLTEXT/sutra/B/B0078.pdf) | pdftotext电子文字含混排校注；只用于页定位，N11另按同版HTML正文分层复核。 |
