## R12 接续记录｜2026-11-23 21:22（上海）

**正式发布验收仍在进行，本条不是最终交付。** 当前验证提交为 `4579a6b8990a91780bf83391967c301218c0711e`，[新生产运行 45182742216](https://github.com/mechgouki/luoyang-city/actions/runs/45182742216) 正在执行。来源 tree `69aef90f87200463e97a4f5331be90029cc0c9c2` 与 [PR86](https://github.com/mechgouki/luoyang-city/pull/86) 实际测试 merge `f442bbff2603b0c3f4d591a77694b51e44ea7b28` 一致；[PR运行45180026243](https://github.com/mechgouki/luoyang-city/actions/runs/45180026243)完整通过，实际checkout、Pages、Git tree及双端各27次下载已交叉核验。

上一生产 `33c14be3` / [run45175501815](https://github.com/mechgouki/luoyang-city/actions/runs/45175501815) 的 build、deploy 成功，958项HTTPS资源全部通过且0重试，V14桌面／手机各27项下载通过；verify-live在20分23秒后被取消，后续旧版回归未全部结束，不能记为正式验收通过。原日志只写“The operation was canceled.”；check-run注释接口不可由当前连接器读取，未把预算推断写成已取得明确timeout注释。失败原件与部分报告均保留。PR86只把verify-live总预算20分钟改为40分钟，所有检查及12分钟浏览器步骤上限保持；[PR85](https://github.com/mechgouki/luoyang-city/pull/85)先前已补齐固定Pillow依赖。

[共同透视与V14审查页](https://mechgouki.github.io/luoyang-city/luoyang-panorama-v14.html?view=compare#comparison)已可访问。主显示第5次，第6次独立附录，六次全景仍全部未通过；首页仍是批准的V12。新增两张永宁寺局部试片与全景分开登记：第二张能读出九层塔、三层南门、独立基脚和塔后殿，画幅比例统一；少量可见基脚前缘大体对应，但完整轮廓、遮挡边及实际全景回嵌尚未通过。另已整理阊阖10项构件、二号门、三号门早期南半残部、太极殿共13项地面控制；未新增上部高度，三号门残片不能当完整门基。

**下一动作：**完成新生产build→deploy→verify-live、独立正式站回读和长期证据逐字节回读，再更新本入口的最终验收状态。研究随后从冻结布局、局部结构参考和完整轮廓／遮挡核对继续；不改写地面矩阵来迁就生成图，不提前批准首页替换。两张试片与宫轴控制的固定研究分支正在保存，后续回执补固定链接。#52、#47继续OPEN。
