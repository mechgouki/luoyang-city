# V13 二修候选：城市空间依据与南门审看

研究版本为R9.1，实现版本为`panorama-review-v13-r2`。本批接续已发布的前版V13审看页，不覆盖其图像、依据或历史记录。当前首页继续采用已批准的V12。

## 用户可见成果

新入口为`luoyang-panorama-v13-r2.html`，包含本轮V13二修、前版V13和V12三个完整画面；前后并排模式比较二修与前版V13，手机按顺序上下排列。URL参数`view=v13r2|v13|v12|compare`可恢复模式，默认显示二修候选。关闭JavaScript后仍能依次阅读三幅完整图、南门局部和所有依据。

南门与寺墙提供两个同倍率观察窗口。窗口直接引用各自完整WebP，以相同原图像素宽高的SVG视窗显示；不另造局部照片，不改动原图像素。观察范围记录在源记录的`detail_view`，并通过构建检查与浏览器检查验证两窗口采用相同倍率。局部观察不作为建筑测绘。

依据导览区分本轮改变、沿用并复核和仍不能具体定位的对象。每张卡记录成图观察、依据、采用的处理和限制，并链接R9总图的`decision-SP01`至`decision-SP20`及R7逐段证据。具体门楼是否达到预期，以绑定本张原始PNG哈希的成图审查为准，页面模板不预先宣称修订成功。

## 源记录与构建接口

源记录为`research/city-spatial-r9/panorama-image-record.json`，沿用前版可追溯字段并采用schema `luoyang-panorama-v13-r2-image-v1`。必须提供原始PNG、全幅WebP、等比手机版的实际尺寸和SHA-256，真实生成提示词路径、成图审查路径、逐项改动与限制。`source_image`绑定前版V13，`candidate_review_file`必须描述同一个原始PNG。

构建顺序为`city_spatial_r9.build(site)`之后执行`panorama_v13_r2.build(site)`。发布文件位于`panorama-v13-r2/`，metadata键为`panorama_review_v13_r2`。完整绘图说明、原件续查记录、实际成图审查和清单可下载；若提供独立视觉审查文件，也随本版保存。

两首页仅在现有V13审看入口后精确增加两个链接：城市空间总图和V13二修。`strip_current_entries()`只接受这组连续、唯一、字节完全一致的插入；任何其他变更不被静默剥除。构建前两首页的字节和前一阶段release原字节分别保存，当前版本可以严格还原到上一步。

## 保护与验收

`homepage_replacement_approved`固定为false，候选状态为`candidate_for_review`。V12主图、手机版及批准metadata、前版V13页面与全部资源、R7节点与下载、R9空间总图在本构建中均按字节保护。前一阶段release另存为`panorama-v13-r2/release-before-v13-r2.json`，其路径与SHA由`predecessor_release`记录。

新增检查覆盖候选原始图身份、三图完整比例、两处原图细部同倍率、未经批准状态、两首页精确还原、所有旧资源保护、跨页证据锚点和真实下载。桌面与手机浏览器检查均支持本地和正式站，并记录来源提交、截图、错误与下载哈希。

本说明只记录实现和核验要求；正式上线状态以主分支生产运行、`build-info.json`与固定交接Issue #52为准。页面发布不能代替对具体首页候选的用户审看确认。
