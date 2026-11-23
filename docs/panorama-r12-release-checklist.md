# R12.1 / V14 发布与长期证据最小完整清单

本清单是实施检查点，**不是上线证明**。编写时只读核对了工作区、远端 `main`、Issue #52／#47 和 R11 长期档案，没有推送、合并、评论或重新运行测试。最终交付性质已改为：**已完成的共同透视依据＋六次未通过试绘的审查档案（第五次为主显示，第六次为独立附录）**。第五次 PNG 是实际生成并审查过的样张，不是占位图；允许以 `needs_revision / rejected_needs_revision` 明确发布失败审查，不能将它称为已完成的空间校正版或已通过候选。发布仍须完整技术门禁通过，且所有未解决阻断项原样可见。

## 0. 已核对的基线和交付边界

| 项目 | 本次核对结果 |
| --- | --- |
| 仓库、工作分支 | `mechgouki/luoyang-city`；`feat/panorama-v14-spatial` |
| 远端已验收 main | `129abaee724870ec00bc25c6e2fd2998a215063b` |
| 该提交源码树 | `f6ed7ac2587da1f5639b76bc4c2b86097eed796d` |
| 本轮版本 | 研究 `R12.1`；实现 `panorama-review-v14`；沿用图像标识 `panorama-candidate-v14`，本次实际状态为未通过试绘 |
| 新页面 | `https://mechgouki.github.io/luoyang-city/luoyang-panorama-v14.html` |
| 首页图与试绘状态 | 首页仍为批准的 V12；V14 为 `needs_revision / rejected_needs_revision`，`homepage_replacement_approved=false` |
| 固定交接入口 | [#52](https://github.com/mechgouki/luoyang-city/issues/52)；当前顶部为 R11.1，保持 OPEN |
| 研究记录入口 | [#47](https://github.com/mechgouki/luoyang-city/issues/47)；保持 OPEN，不以本轮发布结清原图和定位缺口 |
| 旧长期档案分支 | `evidence/city-plan-r11-20261123` |
| 旧档案固定提交 | `b276f8e9495be7d4e8a38ddfa65ffc2bf9e85611` |

上述远端身份在编写时已实际读取；实施提交前再检查最新状态，不能用这张表覆盖随后出现的修改。R11 的[固定档案说明](https://github.com/mechgouki/luoyang-city/blob/b276f8e9495be7d4e8a38ddfa65ffc2bf9e85611/evidence/city-plan-r11/2026-11-23/README.md)和[最终交接](https://github.com/mechgouki/luoyang-city/issues/52#issuecomment-7091022307)是本清单采用的归档先例。

依 [AGENTS.md](../AGENTS.md)，已批准里程碑的发布路径是 **PR 构建与审查 → 合并 main → build → deploy → verify-live → 正式站回读 → 长期归档与交接**。发布未通过样张的审查页不授权替换首页图。图像的视觉检查、页面技术检查、空间证据可靠性分别记录；技术验收通过不能将试绘的失败改成通过。

## 1. 提交内容：逐项纳入，明确排除恢复产物

初次检查时受跟踪文件差异为 5 个文件、16 行新增。这只是当时的阶段快照，不包含未跟踪的新文件及后来补齐的拒用状态链；最终以实际暂存清单为准，不能用早期 `git diff --stat` 代替完整提交清单。

### 1.1 本轮已修改的旧文件，必须一同提交

| 文件 | 必要作用 |
| --- | --- |
| `.github/workflows/pages.yml` | 增加 V14 语义／验证、构建浏览器、生产浏览器门禁；旧门禁保留 |
| `tools/build_all.py` | 在 R11 之后构建 R12／V14 |
| `tools/city_plan_r11_contract.py` | 向旧链恢复前，先严格校验和剥离 R12 增量 |
| `tools/city_plan_r11_verify.py` | 旧 R11 验证适配已校验的 R12 上层 |
| `tools/verify_live.py` | 将 V14 纳入正式 HTTPS 与语义验收 |

### 1.2 本轮新增的代码、页面和说明，必须提交

- `tools/panorama_r12_projection.py`、`tools/panorama_r12_massing.py`、`tools/panorama_r12_alignment.py`、`tools/panorama_r12_record.py`。
- `tools/panorama_v14.py`、`tools/panorama_v14_contract.py`、`tools/panorama_v14_page.py`、`tools/panorama_v14_verify.py`。
- `web/panorama-v14.css`、`web/panorama-v14.js`。
- `web/assets/luoyang-panorama-candidate-v14.webp`、`web/assets/luoyang-panorama-candidate-v14-small.webp`；均为实际第五次未通过样张的无裁切派生图，文件名不构成通过认定。
- `tests/test_panorama_v14.py`、`tests/browser_panorama_v14.py`。
- `docs/panorama-r12-projection.md`、`docs/panorama-v14.md`、本清单 `docs/panorama-r12-release-checklist.md`。

### 1.3 研究输入及实际成图记录，必须按最终 record 收齐

`research/panorama-r12/` 中以下已生成文件属于本轮可复算输入和过程记录：

- `projection.json`、`projection-qa.json`；`projection-clean`、`projection-overview`、`projection-yongning-clean`、`projection-yongning` 各自的 SVG／PNG。
- `massing-display-parameters.json`；`massing-overview-clean`、`massing-yongning-clean`、`massing-yongning-counted` 各自的 SVG／PNG。
- `alignment-audit.svg`、`alignment-audit.png`、`alignment-audit.json`，以冻结投影和第 5 次人工约读解释偏差，不嵌入或改写原图。
- `generation-prompts.txt`、`generation-attempts.json`。
- `generation-inputs/attempt3-input-manifest.json`、旧版 `attempt3-massing-display-parameters.json`、旧版 `attempt3-panorama_r12_massing.py`，以及 `attempt3-massing-overview-clean`、`attempt3-massing-yongning-counted` 的 SVG／PNG。它们保存第三次生成真实使用的输入，不能改成后来增加说明的新版。
- `reviews/v14-review-framework.json` 与 `reviews/v14-attempt1-review.json` 至 `reviews/v14-attempt6-review.json`；原始失败审查按原字节保存。
- `attempts/attempt-1.png` 至 `attempts/attempt-4.png`，第五次的 canonical 原图 `panorama-v14-source.png`，以及第六次附录 `attempts/attempt-6.png`、`attempts/attempt-6-prompt.txt`。六次失败生成的真实原 PNG 均保存，不能仅留临时路径或失败摘要。
- `image-record.json`、`candidate-review.json`、`visual-audit.json`、`change-evidence.json`、`change-evidence.csv`；初始 `change-evidence-draft.json` 若保留，应明确是草稿而非最终结论。

最终提交须包含 `research/panorama-r12/image-record.json` 引用的实际原始 PNG、全幅 WebP、手机版 WebP、全部 `supporting_assets`、`candidate_review_file` 和本轮提供的 `visual_audit_file`。初稿曾记录“最终 record 尚未齐备”；这是此前阶段快照，现已由真实第五次样张和拒用记录补齐，不代表本次最终交付仍缺记录。文件名与下载数量以最终实际 record 为准，不能提前写入虚构成功次数。

两份发布审查必须绑定同一张第五次 PNG 的 SHA256：`45813547ae4555e9b60226f72adfd6df75aa0a36324a23c50966adc3092a0fa6`。WebP 由它按固定转换算法派生。record 的 `status=needs_revision`、两审查的 `review_status=rejected_needs_revision` 必须一致，record 完整保留两份审查阻断项的去重并集；阻断项不得被清空。第五次原始独立审查 hash 为 `63d50a665ae7f20cc679132f6f693045fcac4c3863033283c9280ab2e4476bc3`，原件继续保存；发布用归一化审查不替换原件。样张在页面显示为“试绘未通过”，不得借技术发布进入“已通过候选”状态。

第六次附录的 PNG SHA256 为 `8047a77d6df12e2ef32e2a6833fa0d20f106d2be6fbf48467cffb841c5bf5ef8`，原始提示词 SHA256 为 `08177233cc5ce81f3c00c54fdb20d0f0a0703150d7f7cd0c0e0f3e66bffe8725`，独立审查 SHA256 为 `f0c45c44a08bad5e3bbf078811591f13e7f02be1ce6d957a546b3fcce08c154b`。该次结论为 `rejected_two_storey_gate_and_ground_projection_unmet`，不替换主显示第五次。总次数6、主显示5、最新试绘6分别登记；第六次可见门槛约y477—479等观察只留在本轮附录，不改写第五次的原审查或偏差图。

如主控本轮同步“当前状态”摘要，另需一同提交 `research/current-state.json`、`README.md` 与 `docs/current-state-and-next.md` 的受管理区块，并由 `tools/current_state.py` 同步。`last_verified_release` 应保持真实已验收版本，不能预填尚未发生的生产 SHA、运行或证据提交。不要手改受管理区块而漏改源 JSON。[来源：`tools/current_state.py`](../tools/current_state.py)

### 1.4 明确不提交的文件

**`downloads/luoyang-v24-regional-atlas.pdf` 应从本轮提交中排除。** 它目前未被 Git 跟踪，由 `build_all.py --prepare-only` 调用 `tools/assemble_pdf.py`，从已跟踪的 `downloads/parts/part01.bin` 至 `part06.bin` 恢复旧基线。预期为 **8,612,460 bytes**，SHA256 为 `14f30eeb1e525d090e8d75acfd896049e57b57d0d6b3381c16d1c4f289b72823`。它不是本轮新成果，不应作为整份重复二进制加入提交；现有 `.gitignore` 没有该项，采用显式路径暂存即可，不必为本轮扩改忽略规则。[来源：`tools/assemble_pdf.py`](../tools/assemble_pdf.py)、[`tools/build_all.py`](../tools/build_all.py)

同时排除 `_site/`、临时环境、缓存、原始 Actions 下载目录及本地预览日志；必要的实际验收证据进入独立证据分支。R11 研究输入、原 V13r2 PNG、V12 图像和旧证据不能被同名重写。

暂存前后用 `git status --short --untracked-files=all`、`git diff --cached --name-status`、`git diff --cached --check` 检查完整范围；不要对整个工作区盲目 `git add .`。本清单只要求复核已有验证结果，未要求重新运行已经充分通过的同版本本地测试。

## 2. PR：取得真实 tested merge 和 tree

### 2.1 提交与 PR 身份

1. 确认远端 main 没有未知新提交，再提交本轮精确文件集。记录完整 40 位 PR head SHA 和该 head 的 Git tree。
2. 推送当前研究分支并创建／更新唯一实施 PR，base 为 main。说明共同透视成果、第五次真实样张仍未通过、阻断项可见、旧首页保留、研究边界及已实际完成的验证；不要写 `Closes #47` 或 `Closes #52`。
3. 记录 PR API 原文：number、head SHA、base SHA、状态及更新时间。每次后续推送都使旧 head 的通过记录成为历史记录，不能据此验收新 head。
4. 等 `.github/workflows/pages.yml` 对这次 head 的 PR 运行完成。PR 的 build 必须 success；deploy、verify-live 因工作流条件跳过是预期行为，不能算生产通过。

### 2.2 三份原始证据共同确定测试提交

**不能把 Actions run 的 `head_sha` 或 PR 页当下的 `merge_commit_sha`直接写成“实际 tested merge”。** 本仓库 R11 的成功 PR 原始 collector 已按下面的方法区分两者：[固定参考代码](https://github.com/mechgouki/luoyang-city/blob/b276f8e9495be7d4e8a38ddfa65ffc2bf9e85611/evidence/city-plan-r11/2026-11-23/archive-methods/collect_successful_pr.py)。

1. 保存这次运行的 run API、**具体 run attempt** 的完整 jobs API、build job 的完整日志。用 checkout 步骤中 `git log -1 --format=%H` 的实际输出确定 `tested_merge_sha`，保留日志原文和定位信息。
2. 下载该次运行的 `github-pages` artifact，核对 artifact ID、API digest、实际 ZIP 字节及成员清单。安全读取内部 `artifact.tar` 的 `build-info.json`，要求其中 `source_commit` 与日志实际 checkout SHA 相同；`panorama_review_v14.source_commit` 也须相同。
3. 读取 Git data API 的 `git/commits/{tested_merge_sha}`，保存完整 commit 对象，取得 `tree.sha` 和 parents。把 PR head、测试合并提交、测试树作为三个不同字段记录，不能用短 SHA 混写。

最少保存 `pr_head_sha`、`tested_merge_sha`、`tested_tree_sha`、tested parents、run ID、run attempt、build job ID、完成结论、checkout 日志 hash、Pages artifact ID／digest／到期时间，以及 Pages 内 build-info 的原始字节和 hash。临时 `refs/pull/N/merge` 可能变化或消失，不能只保留该 ref 名。

### 2.3 读取接口及分页要求

以下为 GitHub GET 路径，前缀均为 `https://api.github.com/repos/mechgouki/luoyang-city`；实际编号由本轮运行填入。

| 读取目的 | GET 路径 |
| --- | --- |
| PR 当时身份 | `/pulls/{PR}` |
| 匹配工作流与 head 的 PR 运行 | `/actions/workflows/pages.yml/runs?event=pull_request&head_sha={HEAD}&per_page=100&page={PAGE}` |
| 确定运行状态和 attempt | `/actions/runs/{RUN}` |
| 固定 attempt 的全部 jobs | `/actions/runs/{RUN}/attempts/{ATTEMPT}/jobs?per_page=100&page={PAGE}` |
| job 原始日志 | `/actions/jobs/{JOB}/logs`，通过可跟随临时下载重定向的日志工具保存 |
| artifacts 清单 | `/actions/runs/{RUN}/artifacts?per_page=100&page={PAGE}` |
| 精确源码 commit/tree | `/git/commits/{SHA}`，再按返回的 tree SHA 读取 `/git/trees/{TREE}?recursive=1` |

匹配工作流路径、事件、head 和 PR 编号，不取“最近一个绿色运行”。有分页就完整取回；便利工具若只返回第一页或 latest attempt，不能与指定历史 attempt 的日志混用。树响应若 `truncated=true`，按子树继续取得完整清单。artifact 若发生 rerun，记录具体 ID 和创建时间，不仅按同名文件选择。

## 3. 生产：同树、三关口与正式站身份

1. 合并前再次确认待合并 head 就是已测试 head；base 已变化时需确认新的集成版本已被正确测试。按既有授权合并 main，不强推覆盖历史。
2. 保存正式 merge／squash 结果的完整 `production_commit` 与 Git commit API，取得 `production_tree`。要求其 tree 与成功 PR 的 `tested_tree_sha` 一致；不同则不能把该 PR 的通过当作生产源码验收，必须解释变化并完成对应验证。
3. 记录匹配该生产 commit 的 main push 工作流，不误用 PR 运行或别的提交。实际 `build`、`deploy`、`verify-live` 三个 job 均需 `completed / success`，保存每个 job ID、时间和结论。
4. `deploy` 成功但 `verify-live` 失败时，状态应为“已部署、尚未验收”，保留失败日志并修复；不得宣称自动回滚或结清实施任务。[来源：`AGENTS.md`](../AGENTS.md)
5. 从正式 HTTPS 独立读回原字节 `build-info.json` 和 `release.json`，保存获取时间、URL、字节数、SHA256。`source_commit` 必须是生产 commit；`panorama_review_v14` 必须存在，`status=needs_revision`、`review_status=rejected_needs_revision`、阻断项集合及计数一致，首页仍为 V12，且未经批准标志为 false。首页新入口、页面标题、无脚本正文和 URL 切换后都应继续标明“试绘未通过”。

当前工作流的运行环境是 Python 3.11 和已锁定依赖；Playwright 镜像为 `mcr.microsoft.com/playwright/python:v1.57.0-noble`，pip Playwright 为 1.57.0。保留实际 `browser-runtime-digest.json` 和 `pdf-font-resolution.txt`。当前新增门禁不移除旧门禁、不增加超时预算。[来源：`pages.yml`](../.github/workflows/pages.yml)

## 4. 下载清单：从生产数据导出，不手写数量

### 4.1 全站公开资源清单

保存生产 `build-info.json.files_sha256` 的**完整映射**，并保存 CI 的 `live-http.json` 原件。要求：

- `live-http.status == "passed"`，commit 等于生产 commit。
- `checked_files == len(files)`，实际路径集合等于 `files_sha256` 排除明确不发布的 `.nojekyll` 后的集合；不得沿用 R11 的“920项”作为本轮预期数字。
- 每条实际 bytes、SHA256 与生产清单一致；HTTP 重试若存在如实记录，不把重试后的结果描述为无重试。

`build-info.json` 自身不能放进自身 hash 映射，必须另存原始字节身份。[来源：`tools/verify_live.py`](../tools/verify_live.py)

### 4.2 V14 全部下载与实际文件

以生产 `build-info.json.panorama_review_v14.download_files` 为唯一完整下载集合，读取并保存其 `manifest`（当前为 `panorama-v14/manifest.json`）和 `record`（当前为 `panorama-v14/review.json`）。不要仅选 PNG 和两张底稿，也不要依据文件扩展名推断“全部”。

为每条下载建立一行清单，至少包含：发布路径、生产预期 SHA256、实际 bytes／SHA256、实际本地保留路径、来源 run/job/device、是否真实点击，以及使用的是 PR 还是生产 source commit。下载集合覆盖试绘全幅、原始 PNG、record、提示词、成图审查、选定支持材料和 manifest；可选独立审查加入后数量会变化，按最终 record 实际计算。[来源：`tools/panorama_v14.py`](../tools/panorama_v14.py)

生产 build 和生产 live 的 desktop／mobile 报告，每端都必须满足：

```text
set(report.downloads) == set(meta.download_files)
set(report.retained_downloads) == set(meta.download_files)
actual_bytes_sha256 == report_sha256 == production_build_info_sha256
```

报告位置分别为 `panorama-v14-browser/{desktop,mobile}-report.json` 和 `live-panorama-v14-browser/{desktop,mobile}-report.json`；下载原件路径由各报告的 `retained_path` 给出。所有下载都应来自测试中的一次真实 `click` 与 `expect_download`，保留尝试记录；不能用后补 HTTP 文件伪称浏览器真实下载。[来源：`tests/browser_panorama_v14.py`](../tests/browser_panorama_v14.py)

PR 两端下载与 **PR 自己的** Pages 包比较，生产四路下载与 **生产** Pages 包及正式站比较。两次 source commit 不同会使某些 JSON／报告字节不同；测试源码树相同不表示所有带提交戳的发布文件也应跨提交相同。

主控独立公网回读至少覆盖本轮全部下载、V14 页面、两个首页、新 manifest／record／交互脚本／样式、V14 全小两图及旧 V13r2／V12 图像，保存实际原字节。全站资源仍由完整 `live-http` 清单验收，旧 R11 下载和全部旧回归继续由原 CI 报告覆盖。人工网页审看应操作实际部署页并保留对应版本身份，不能将本地截图称为线上操作。

## 5. Actions 证据：到期前收取，保留真实历史

当前 `pages.yml` 的保留时间为：

| Artifact | 工作流阶段 | 到期窗口 |
| --- | --- | --- |
| `github-pages` | PR／生产 build | 7 天 |
| `browser-build-evidence` | PR／生产 build，`if: always()` | 14 天 |
| `live-acceptance-evidence` | 生产 verify-live，`if: always()` | 30 天 |

因此最短收取窗口是 **7 天**；实际操作应在该轮完成后立即取回。保存 API 返回的精确 `expires_at`，不要按文档日期估算。最终成功运行必须收取，发生过的失败 PR／生产运行同样保存已有 artifact、完整日志与失败状态；没有执行的步骤不能写成通过。

最小完整归档包括：

1. PR、run、固定 attempt jobs、artifact 列表、精确 head／tested merge／production commit/tree 的 API 原文；完整 build、deploy、verify-live 日志。
2. 最终 PR、最终生产的实际 artifact 成员，包括新版和旧回归报告、截图、浏览器真实下载原字节、镜像摘要和字体解析记录；若有失败，另按 run/attempt 分目录保留。
3. Pages 包中的原始 build-info／release、V14 全部发布文件、R12 predecessor 归档；完整包的逐成员身份和收取报告。不能用事后本地重建文件替换本次实际 Pages 输出。
4. 正式站独立回读及全部下载 manifest、实际原件；源输入和生成／审查历史，特别是第三次旧输入与后来增加说明版的区别。
5. 所有报告汇总成 `acceptance.json`，数字从实际记录推导；分开记录技术发布验收状态与图像 `needs_revision / rejected_needs_revision` 状态，列明未获首页替换批准、空间绑定未实测、未知上部结构及六次试绘被拒原因。技术字段中的 accepted 不能用来描述该张图像通过。

解包时核对 API digest、ZIP 字节、每个成员的相对路径、bytes／SHA256，拒绝路径穿越、重复路径和链接伪装；Pages 的内层 tar 同样处理。对 artifact 下载和解包的记录是存证核验，不是重跑整套网站测试。

## 6. 永久证据分支及独立回读

采用 R11 既有模式，建议新分支 `evidence/panorama-r12-YYYYMMDD`，目录 `evidence/panorama-r12/YYYY-MM-DD/`；日期按实际归档日填写，不预填成功日期。

1. 从**最终生产 commit** 建立独立证据分支／工作区。最终归档 commit 以该生产 commit 为唯一 parent，仅新增指定证据前缀。不要将大批证据合并回 main，不因证据整理触发重新发布，也不覆盖旧 R11 档案。
2. 创建 `README.md`、`acceptance.json`、`archive-inventory.json`、`archive-scope.json`，以及沿用既有归档方法所需的检查记录。inventory 对每条实际文件记录路径、bytes、SHA256、Git blob；同 blob 可去重上传，每个逻辑路径仍保留身份。
3. 允许省略的只是已核实的冗余：逐成员核对后的 Actions 外层 ZIP、已绑定实际发布字节和完整成员账的 Pages 包装 tar、与此前永久档案 hash 完全一致且逐项登记的旧地形中间物。**浏览器实际下载的 ZIP 是验收对象，不能以“ZIP 包装”为由省略。** 改变的文件不得套用“未变”排除规则。
4. 延续 R11 已明确的材料范围：保存源 URL、页码、hash、提取事实与本项目生成图，不将整份第三方原刊 PDF、原始栅格、裁图或带原图底图的叠照自动纳入公开证据。输出原日志前沿用已有敏感字段检查；不得把认证令牌或临时签名 URL 当长期下载地址。
5. 生成外部冻结 upload manifest，覆盖全部最终路径，包括索引文件自身。R11 先例中的三个索引 `archive-inventory.json`、`archive-scope.json`、`archive-sensitive-scan.json` 不放进各自生成的自引用 inventory，但必须纳入外部冻结清单和独立远端回读。
6. 推送／写入后，从一个新的空 bare 仓库或等价独立读取流程取得**精确归档 commit**；核对唯一 parent、完整 tree、文件 mode、证据前缀外字节、所有实际文件的 bytes／SHA256／Git blob，以及索引原件。仅核对上传回执、目录名或文件数量不够。
7. 再读远端 main，确认仍为预期生产版本，或者记录此后合法的新生产变化；归档操作本身不得改动 main。将归档 SHA、冻结上传清单 SHA、独立回读报告 SHA 和结论写入外部交接，不反复改写已核定档案以嵌入自身验收。

可复用的旧方法以其固定版本为参考，先调整路径、schema 和本轮字段，不直接运行其中写死的 R11 临时目录或 26 个下载断言：[R11 archive-methods](https://github.com/mechgouki/luoyang-city/tree/b276f8e9495be7d4e8a38ddfa65ffc2bf9e85611/evidence/city-plan-r11/2026-11-23/archive-methods)。永久链接使用 commit SHA，不能仅提供会移动的分支名。

## 7. PR、#52、#47 的最后交接

必须先完成上述真实动作，再填入交接结果，保留每个状态的原始时点。不要预写“已上线”。

| 位置 | 必需内容 |
| --- | --- |
| 实施 PR | 最终 head、实际 tested merge/tree、PR run/attempt；合并后 production commit/tree、生产 run 和三关口；正式入口、永久证据固定链接；第五次样张仍未通过、未批准首页替换及研究限制 |
| #52 顶部当前状态与完整交接评论 | R12.1 已完成的共同透视依据和未通过试绘审查页、正式 URL、真实生产 SHA/run、可回查的下载与归档、实际完成时间、继续改绘断点；保留 R11 及更早历史快照 |
| #47 研究评论 | 本轮哪些地面关系确实更可靠、哪些只是艺术视点／占位；共享 H 与未验证外部绑定；来源与图面变化对应；失败成图的诚实记录与待证事项 |

两 Issue 均继续 OPEN。#47 的较早正文含历史首页和旧阶段安排，不能将其中旧 H2 身份代替已验收 V12，亦不能用它否定用户本轮已批准的共同平面约束候选工作；当前状态以 #52 最新区段、本轮用户授权及真实生产证据为准。

完成后用户交付应给正式“V14 试绘审查·未通过”链接、共同透视／逐项依据／偏差核验图入口，说明已完成的几何成果与试绘仍未落实的部分。首页仍为 V12；不能把六次失败后交付审查记录说成空间校正全景已经完成。后续须实际改绘并重新审查；只有未来的具体合格候选获用户另行确认，才能执行首页替换。

## 8. 收口条件

- [ ] 六次真实试绘原图和原审查保留，第六次PNG、实际提示词与审查可独立下载；第五次发布用审查、派生图、提示词、投影与支持材料身份闭合，明确 needs_revision 且阻断项完整可见。
- [ ] 精确提交文件集已检查，恢复用旧 PDF 和本地构建产物未入提交。
- [ ] PR 真实 checkout SHA、Pages source commit、Git tested tree 对应；所验 head 正是待合并 head。
- [ ] 正式提交与已测试源码树一致，生产三个 job 全部 success。
- [ ] 正式 build-info、全站 HTTP manifest、V14 全部下载与双端真实文件逐项吻合；原 R11 和批准 V12 保持合同要求。
- [ ] 有到期日的 Actions 材料已取回，永久证据提交已独立远端逐字节回读。
- [ ] PR、#52、#47 已登记真实版本、限制和固定证据链接；两长期研究入口保持 OPEN。

以上项目尚未发生的部分保持未勾选；本清单自身不替代各项证据。
