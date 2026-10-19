# Hustudy 持续交接日志

<a id="h-20261019-fzk-001"></a>
## H-20261019-FZK-001：M3功能与验收整理提交（待团队接收）

2026-10-19，Codex辅助fzk；分支codex/fzk-m3-note-tags。用户授权提交GitHub，确认第1–8项及编辑/识别流程通过，第9项暂缓。包含笔记目录/导入/标签、图片/导出、引用/保存、回收站、公式及识别插入，0013–0018迁移和备份/worker适配。82后端、58前端单元、22Chrome及构建通过，[验证与限制](../docs/fzk/m3_completion_audit.md)、[人工反馈](../docs/fzk/manual_recheck.md)。已清理停用功能旧指南与重复导出说明，保留必要兼容契约；未提交密钥/运行数据/无关文件。zhy接收迁移与共享层，gcx/xtc核对消费端，不代签团队验收。下方历史切片的“待本人复验/未提交”以本条最新状态为准。

2026-10-19人工反馈补充：用户确认M3-CAPTURE-TEXT-01验收通过（M3-EDITOR-MATH-03此前已通过）。本条更新下方相应历史“待本人复验”状态，不代替团队接收；后续按[逐项复验队列](../docs/fzk/manual_recheck.md)补验回收站等未明确反馈项目，继续不提交/推送。

## M3-CAPTURE-TEXT-01 · fzk（2026-10-19，Review / 待接收，未提交）

用户确认M3-EDITOR-MATH-03验收通过。按新要求完成M3 AI整理/配置启用停用、旧整理任务取消和识别文本插入当前笔记；先记录[契约](../docs/contracts.md#m3-capture-text-01)，历史笔记/识别保留，无新迁移，M2不受影响。13项后端、58项前端单元、12项Chrome/WebKit、类型/构建/Ruff通过，[证据与复验](../docs/fzk/capture_text_acceptance.md)。已确认本机队列为空后重启旧worker，保存笔记后刷新前端即可；其他环境需更新后台进程。本轮本人新增行为复验和团队接收待进行，继续不提交推送。

## M3-EDITOR-MATH-03 · fzk（2026-10-19，Review / 待接收，未提交）

用户确认M3-EDITOR-MATH-02验收通过。本轮完成五组图形符号、12种结构快捷输入、参数直接填写/嵌套/恢复、窗口最近使用与末尾续写，参考AxMath交互，约束见[共享契约](../docs/contracts.md#m3-editor-math-03)。56项前端单元、22项Chrome/WebKit回归、类型检查和生产构建通过；修复双引擎连续输入及源码切换选区问题，[证据与复验步骤](../docs/fzk/formula_graphic_input_acceptance.md)。无新依赖/API/schema，保存草稿后刷新前端即可。新增功能待本人手动复验及团队接收，未提交推送。

## M3-EDITOR-MATH-02 · fzk（2026-10-18，Review / 待接收，未提交）

M3-EDITOR-MATH-01收到用户“本轮手动复验通过”。本轮已实现357项/16分类符号模板、跨类搜索、嵌套参数、11种表格结构、窗口撤销和12节本地速查。52项前端单元、16项Chrome/WebKit及生产构建通过；[证据与手动步骤](../docs/fzk/formula_workspace_acceptance.md)、[共享契约](../docs/contracts.md#m3-editor-math-02)。无新依赖/API/schema，保留原安全和草稿边界。新增能力仍待用户复验与共享层评审，不替其他成员签收，未提交推送。

<a id="h-20261018-fzk-006"></a>
## H-20261018-FZK-006 · M3-TRASH-01（Review / 待接收，未提交）

用户确认M3-LAYOUT-DRAG-01本轮复验全部通过；本轮新增笔记回收站与原子批量删除/恢复/清空、30天默认可配置自动清理。先记录[共享契约](../docs/contracts.md#m3-trash-01)，0016迁移、备份升级和worker整合待zhy评审；不代签其他成员。69个不同后端、41前端单元、22个不同Chrome用例最终通过，Ruff/类型/构建通过；[使用、启动与验证明细](../docs/fzk/note_trash_acceptance.md)。不使用真实用户数据测试，不提交/推送。新功能本人复验待进行；启动需后端及worker重启，0016保留旧删除记录完整30天窗口。

<a id="h-20261018-fzk-005"></a>
## H-20261018-FZK-005：笔记工作区布局与拖动整理（Review / 待接收）

2026-10-18，Codex辅助fzk。用户确认004验收1–5通过；本轮C01/C02/C08/C10、FR-09/10/11界面改进，先记录[交互契约](../docs/contracts.md#m3-layout-drag-01)，再实施中央管理列表、简洁侧栏、模态工具和目录拖动。复用原API/revision，无迁移/依赖或其他模块行为改动。保留当前分支未提交工作，不commit/push/合并，不代签团队接收。

41前端单元、38个不同Chrome用例最终通过，类型/生产构建通过；首次拖动落点/按钮名称、测试GET连接重置和复验情况见[当前验收](../docs/fzk/note_workspace_acceptance.md)。覆盖中央选择预填导出、弹窗状态/登录恢复、实际拖动及循环/超深/冲突、原图片/引用/标签/目录ZIP/草稿保护。仅用隔离账户/数据库和自制资料，未调用真实模型；无全量后端重测声明。已运行0015的环境保存草稿后刷新前端即可。zhy接收UI与既有迁移整合、fzk本轮实测、实机/WebKit试用仍待。

<a id="h-20261018-fzk-004"></a>
## H-20261018-FZK-004：笔记文件夹、批量导入与整理、编辑器（Review / 待接收）

用户确认上一轮引用/回源、刷新/移除保留正文、前后台自动保存复验2/3/4成功；其余未反馈项不推定通过。M3-ORGANIZE-IMPORT-EDITOR-01先记录[公共契约](../docs/contracts.md#m3-organize-import-editor-01)及0015迁移提案，现已实现6级文件夹、保留目录ZIP/未归档根目录、批量MD导入/统一标签文件夹、批量标签/移动、分类建议及编辑器增强。分类建议采用本地可解释规则，经确认才移动；未调用真实模型。

56项相关后端、41项前端单元、32个不同Chrome用例最终通过；Ruff/TypeScript/Office/Vite构建及文档链接检查通过。浏览器首次回归有1项旧导出提示断言，更新后定向通过；首存焦点、批量期间锁定编辑区和深层ZIP离线图片已验证。[详细范围、实际命令与截图](../docs/fzk/note_organization_acceptance.md)。0015为M3派生组织模型，兼容旧0012–0014账户备份，待zhy评审整合；先重启API完成迁移再重启worker、刷新前端。新功能待fzk本人复验，不代签团队接收。工作区仍未提交/推送。

<a id="h-20261018-fzk-003"></a>
## H-20261018-FZK-003：M3余项审计、引用管理与保存恢复（Review / 待接收）

Codex辅助fzk，C06/C08/C09/C10、FR-11/13。用户明确确认图片上传/笔记导出成功，范围不扩大为全部边界或团队签收。先写AGENTS及[契约](../docs/contracts.md#m3-citation-lifecycle-01)，已实现引用去重/50条上限/移除/授权来源名与版本/失败重试、前后台自动保存恢复；无新迁移/依赖。仅M3及消费端兼容字段，M1/M2/M4业务不重写。

相关后端45个不同用例、36项Vitest、27项Chrome最终通过，Ruff/构建通过；初次新测试fixture、显示名断言与模拟时钟假设修正后定向复验，详细命令及390/1440截图见[M3审计与验证](../docs/fzk/m3_completion_audit.md)。新界面本人复验、zhy整合仍待，审阅笔记供M2/M4消费及P1图谱如实单列。后端自动重载或重启后刷新页面，含已移除引用的旧ZIP须重新导出；无本轮worker变更。工作区未提交/推送，不代签接收。

<a id="h-20261018-fzk-002"></a>
## H-20261018-FZK-002：所选笔记离线图片与批量上传（Review）

Codex辅助fzk；M3-BATCH-IMAGES-01、C05/C07/C09/C10、FR-09/14。先记录[契约](../docs/contracts.md#m3-batch-images-01)与AGENTS意图后实现：导出自动带所选笔记引用图片，批量上传复用M1单文件接口及AssetLibrary前端，无新迁移/依赖。18项相关后端、36项Vitest、17项Chrome最终通过，Ruff/构建通过；新增后端测试断言和浏览器总时限问题已修正复验，见[详细证据](../docs/fzk/note_batch_images_acceptance.md)。解压后断网file页面实际图片加载、精确范围/去重、部分失败仅重试未完成、旧功能回归已验证；重启API/worker并重新导出。仍不提交/推送，待fzk复验与zhy接收，不代签成员。

<a id="h-20261018-fzk-001"></a>
## H-20261018-FZK-001：简洁选择导出与笔记图片管理（Review）

Codex辅助fzk，M3-SIMPLE-EXPORT-01，C05/C07/C09/C10。用户反馈上传已成功但缺管理、单篇和ZIP笔记命名不直观、包结构冗余、不能选择范围、CMD校验不适合日常使用。本轮复用M1图库组件，单篇标题命名、勾选导出、默认仅Markdown及可选图片；内部安全校验保留。先更新[契约](../docs/contracts.md#m3-simple-export-01)，无新迁移，继续不提交/不推送，不代签成员。

17项相关后端、28项Vitest、15项Chrome及Ruff/构建通过；Chrome首次2项图片管理测试定位失败，修正后复验通过，非产品功能失败。范围/命令/截图见[验收](../docs/fzk/note_batch_images_acceptance.md)。新请求在sources_json.request冻结选择，旧包标legacy且不改写；重启API/worker再重新生成。同步需求FR-14、README、使用指南和fzk文档；fzk人工复验及zhy此前迁移/共享worker整合待接收，实机/WebKit/真实材料联调未宣称完成。

四名成员每完成一个可交接切片，或出现会影响下游的接口/阻塞时，在提交或 PR 前追加记录。这里记录变更交接；环境安装见 [project_handoff.md](project_handoff.md)，任务总览见 [task_board.md](task_board.md)，权威接口见 [contracts](../docs/contracts.md) 与 [API](../docs/api.md)。

## 维护方式

- 交接 ID：`H-YYYYMMDD-成员-序号`，同日同成员从 001 递增。正文添加小写同名 anchor，方便从个人文件链接。
- 新记录追加到文末，各条独立；旧记录修正保留日期与原因，不删除其他人的测试/风险。并发合并保留双方条目，检查 ID 不重复。
- 状态：**待接收 → 集成中 → 已验收**；阻塞写 **阻塞**、原因、责任人和解除条件。待接收即实施方已提供交接材料，不能推定其他成员已签收。
- 接收方在自己的接收栏追加记录者、日期、复验命令/输出与决定；全部所需接收复验及队长集成验证完成才标“已验收”。代码未合并时写明，个人完成不等于项目完成。
- 公共契约变更先记录意图并链接；只通知受影响模块。此文件是仓库记录，不会自动向成员发送消息。团队成员在开始任务、提交/PR 前主动读取。

## 新条目模板（复制到文末）

```markdown
<a id="h-yyyymmdd-成员-序号"></a>
### H-YYYYMMDD-成员-序号：切片标题

- 日期 / 记录者 / 实际实现者（含 AI 辅助）：
- 模块 / 任务 ID / 需求 ID：
- 状态：待接收 / 集成中 / 已验收 / 阻塞（选一项）
- 交出成员 → 接收成员；影响范围：
- 分支 / commit / PR：没有提交时写“工作区未提交”。
- 输入、依赖及公共契约：
- 实现功能/优化；修改文件或目录：
- API / schema / 迁移 / 配置变更；兼容与调用方操作：
- 验证环境、命令、实际输出；未执行项：
- 风险 / 阻塞 / 下一步与责任人：
- 个人 progress、features/optimizations 及证据链接：
- 接收记录：接收成员本人填写日期、复验、结果和未决问题。
- 集成记录：队长填写分支/commit、实际集成验证、任务板/追踪链接。
```

## 交接索引

| ID | 交出 → 接收 | 内容 | 状态 |
|---|---|---|---|
| [H-20261013-ZHY-001](#h-20261013-zhy-001) | zhy → xtc / fzk / gcx | M1 有效来源与跨模块辅助集成 | 待接收 |
| [H-20261013-ZHY-002](#h-20261013-zhy-002) | zhy → xtc / fzk / gcx | 四人文档结构与交接规范 | 待接收 |
| [H-20261013-ZHY-003](#h-20261013-zhy-003) | zhy → xtc / fzk / gcx | M1 整理/检索范围/原文关联与统一视觉 | 待接收 |
| [H-20261014-ZHY-001](#h-20261014-zhy-001) | zhy → fzk（xtc/gcx 知悉共享契约） | PDF 按页、截图来源、回页与删除撤权 | 待接收 |
| [H-20261014-ZHY-002](#h-20261014-zhy-002) | zhy → xtc / fzk / gcx | 人工 PDF 补录确认与不可变来源 | 待接收 |

<a id="h-20261013-zhy-001"></a>
### H-20261013-ZHY-001：M1 可靠导入与统一来源

- 日期：2026-10-13；记录者/实际辅助实施者：Codex（zhy 队长会话）；zhy 本人审阅：待填写。
- 模块/任务：共享层 + M1-可靠导入，必要的 M2–M4 集成；FR-03–06/08–09/13/36–37，NFR-06/10，作答辅助涉及 FR-21–27/30。
- 状态：待接收。交出 zhy → xtc、fzk、gcx；接收和人类模块评审尚未记录。
- 分支/commit/PR：当前工作区未提交；已有用户改动一并保留，不宣称已合并 develop/main。
- 依赖与契约：[contracts](../docs/contracts.md)、[API](../docs/api.md)；认证、课程、有效版本/Chunk/Citation/Asset/Job 共用，旧引用保留原版本。
- 修改范围：backend core/material models/repositories/services/workers/routers/schemas、0001–0003 迁移与风险测试；frontend api/components/materials/notes/ai/exams；scripts、公共文档。具体功能与边界见 [zhy/features](../docs/zhy/features.md)。
- 交接行为：上传返回 202，需要 worker；PARSE/INDEX/PREVIEW 分别观测；版本不可变；删除撤销读取和新来源。原件/预览走 Bearer Blob 请求，不在 URL 放令牌。
- 接收操作：xtc 使用有效版本来源并保留演示模型边界；fzk 复验 Citation 原子插入/回源、Markdown/图片失效与 AssetReference；gcx 复验干净考生响应、服务器截止、提交幂等及提交后 result。现有 AI/笔记/考试辅助是队长会话实施，不能写成三位成员本人完成。
- 迁移/配置：Alembic upgrade head，旧 SQLite 库升级前数据库备份；backend/requirements.lock + frontend/package-lock.json；bash scripts/dev.sh 同时启动后端与资料 worker，已有后端可另启 bash scripts/worker.sh。
- 历史实测（本条只引用上一代码切片，不冒作本次重新运行）：bash scripts/check.sh：15 pytest passed、1 条依赖弃用警告；Ruff、迁移漂移、Markdown 安全和 TypeScript/Vite 构建通过。Safari 只确认新版资料库渲染；本机 OpenAPI 新接口已加载。
- 未完成：LibreOffice 成功转换/PDF.js、完整 E2E/性能、来源反链与截图、附件 ZIP/恢复、真实 Provider、真题映射统计/双来源拟卷。下一步各主责按 [任务板](task_board.md) 接收和完善；A 维护迁移与共享集成。
- 个人证据：[progress](zhy/progress.md)、[features](../docs/zhy/features.md)、[optimizations](../docs/zhy/optimizations.md)；完整历史 [公共进度](../docs/progress.md)。
- 接收记录：xtc 待本人填写；fzk 待本人填写；gcx 待本人填写。
- 集成记录：未合并；公共契约、进度和追踪已有记录，不能据此标记全部 P0 已验收。

<a id="h-20261013-zhy-002"></a>
### H-20261013-ZHY-002：四人成员目录与持续交接规范

- 日期：2026-10-13；记录者/实际辅助实施者：Codex（zhy 队长会话）；输入为用户本轮四人目录与 handoff 要求，成员/角色对应沿用正式方案。
- 模块/任务/需求：共享协作流程；DOC-TEAM-01；NFR-10 的文档与复现证据增量，无新增产品功能需求。
- 状态：待接收。交出 zhy → xtc、fzk、gcx；zhy 本人审阅与接收方复验待填写。
- 分支/commit/PR：当前工作区未提交。
- 实现：collaboration 和 docs 均设 zhy/xtc/fzk/gcx；个人进度与功能/优化分开，公共契约/API/集成结果保留统一入口；handoff 使用唯一 ID、真实证据、本人接收与集成状态。
- 修改范围：AGENTS.md 第 19/20 节、README.md、协作指南、角色/流程/目录入口、个人记录模板、公共进度/追踪；未修改业务代码、数据库或运行网站。
- 契约/迁移：只变更团队文档维护规则；产品 API/schema/迁移无变化。已有公共跨模块历史保留；其他成员模板不填写虚构个人成果。
- 验证：本轮 Python 一次性文档检查通过：8 个成员目录、20 个成员文件，31 份入口/规范/个人文档的本地链接与锚点有效，2 个交接 ID 唯一；git diff --check 通过。仅文档变更，未重跑业务测试，未沿用上条测试数量冒称本轮测试。
- 接收操作：每人先读自己的两套目录和本日志；下次切片在提交/PR 前更新 progress、features/optimizations 和交接，按实际填写接收结果。公共契约仍在 docs 根级维护。
- 风险/下一步：仓库账号、Issue/PR、具体工期和各人实现记录按实际补充；合并本文件时保留双方新增条目并避免 ID 重复。
- 证据：[zhy/progress](zhy/progress.md)、[功能](../docs/zhy/features.md)、[规则](../AGENTS.md#20-四人文档隔离与统一交接规则)、[目录](README.md)。
- 接收记录：xtc 待本人填写；fzk 待本人填写；gcx 待本人填写。
- 集成记录：未合并；本轮文档变更由队长在正式提交/合并后补 commit 与 Wiki/PR 链接。

<a id="h-20261013-zhy-003"></a>
### H-20261013-ZHY-003：资料整理、原文关联与统一视觉

- 日期：2026-10-13；记录者/实际辅助实施者：Codex（zhy 队长会话）；zhy 本人审阅待填写。
- 模块/任务/需求：共享层 + M1；M1-ORGANIZE-01；FR-07/09/13、NFR-06/09/10；M3 只读接口增量，不改 M2/M4 内部。
- 状态：待接收。交出 zhy → xtc/fzk/gcx：fzk 接收原文关联笔记只读服务/导航契约，xtc/gcx 接收公共响应和前端控件约定，不冒填成员评审。
- 分支/commit/PR：工作区未提交；已有用户改动保留，无提交/合并声明。
- 输入/输出：[contracts](../docs/contracts.md)、[API](../docs/api.md)；当前用户课程/资料/版本 → 分类标签/版本命中/关联笔记。共享授权来源，M1 路由通过 M3 只读服务查询，不直接读笔记表。
- 改动：backend material model/schema/router、search 与 note_references service、0004 migration、test_material_organization/test_migrations；frontend API、materials、platform 查找/首页/指南、Icon/workspace/main/styles；公共文档与 zhy 记录。详情 [features](../docs/zhy/features.md)。
- API/迁移：PATCH documents 元数据；documents/search 可选分类/标签，search latest_only 默认 false 保持兼容；references 按版本/片段/归属返回有效笔记；响应补 UTC 时间、category/tags/version_no、jobs 资料名称。0004 加 category/tags/分类索引，执行升级后再启新代码；现有版本/引用不动，JSON1 验证失败停止升级。
- 接收操作：xtc 保持 search 旧默认，需最新范围时显式传参；fzk 使用 note_id 跳转与当前标题，不把资料反链存成第二份列表；gcx 复验公共 SVG/按钮/状态/焦点和 reduced-motion，不更改试卷/作答状态。其他模块可复用 Icon，不引入第二套图标风格。
- 真实验证：bash scripts/check.sh：18 pytest passed，1 条依赖弃用警告；Ruff/迁移升级与漂移/Markdown 安全 SSR/TypeScript/Vite 通过。Safari 现有 PPTX 117 片段→香农 2 命中，整理面板、专注阅读、回顶及资料/AI 公共样式观察；未修改用户元数据/上传私人文件，完整保存/引用跳转 E2E 待测。
- 文档检查：13 份相关文档、84 个本地链接与 3 个交接 ID 检查通过，git diff --check 通过；资料操作见 [用户指南](../docs/user_guide.md)。
- 风险/下一步：课程分类/标签、笔记标签仍未完成；PDF.js/LibreOffice 成功转换、附件 ZIP/恢复、真实 Provider、真题统计和双来源生成、性能/真实试用待推进。以上不标全 P0 Done。
- 个人证据：[progress](zhy/progress.md)、[features](../docs/zhy/features.md)、[optimizations](../docs/zhy/optimizations.md)；[公共进度](../docs/progress.md)、[追踪](../docs/traceability.md)。
- 接收记录：xtc/fzk/gcx 待本人填写日期、命令、实际结果和决定。
- 集成记录：工作区统一检查通过，未合并；提交/PR/Wiki、接收复验及正式集成状态由队长按实际补充。

<a id="h-20261014-zhy-001"></a>
### H-20261014-ZHY-001：按页阅读与截图来源闭环

- 日期：2026-10-14；记录者/辅助实施者 Codex（zhy 队长会话）；zhy 本人审阅待填写。
- 模块/任务/需求：共享层 + M1；M1-PREVIEW-ASSET-01；FR-06/07/08/37、NFR-06/09/10。状态待接收，工作区未提交/合并；用户既有修改保留。
- 交出 zhy → fzk：图片消费方接收可选 source_version_id/source_page/source_locator_type 和 metadata 接口。xtc/gcx 知悉只读来源契约；M2/M4 内部没有本轮改动，截图不自动进入模型或检索。
- 输入/输出：授权 PDF 预览及当前页 PNG → 带固定版本/确定页号的 Asset；只关联当前用户课程有效版本，DOCX 标 preview_page，不伪造正文页码。[contracts](../docs/contracts.md)、[API](../docs/api.md)。
- 文件范围：M1 assets router/service/repository；现有 models/notes.py 只扩 Asset，schemas/notes.py 只扩 AssetResponse；notes router 图片 HTTP 入口搬至 M1，笔记/双链/Citation/反链行为保持。main/courses 共享入口与课程删除图片撤权；0005/tests；frontend materials/PdfReader、knowledge 图库、API/Help/styles/Vite；scripts/verify_pdf 与检查入口、fixtures/preview_demo.pdf、依赖锁/声明与公共文档。
- 迁移：0005 来源 FK/页/类型。SQLite 保持外键开启，在真实事务中临时保存/恢复原 AssetReference 与索引，故障回滚；既有版本、原图片及引用 UUID 保留。生产数据库升级前有既有 SQLite 备份策略；该数据库备份不代替完整个人备份。
- API：图片上传新增成对 source_version_id/source_page，校验实际预览页数与图片预算；新 GET assets/{id}/metadata；旧 URL/上传/笔记 UUID 嵌入兼容。来源文档/课程删除后文件 404、图库排除、metadata unavailable，笔记正文保留。
- 前端：本地 PDF.js 6.4.299 页码/翻页/缩放与截图，过期渲染取消、300 万像素/单边 12000；图库刷新、外部来源标识与回固定原页。worker/CMap/字体/ICC/解码器本地构建，许可证保留。Node >=22.13.0 或 >=24，本机 25.2.1；npm 默认可选 @napi-rs/canvas 用于 Node 校验。
- 实测 bash scripts/check.sh：22 pytest passed（1 条 Starlette/anyio 警告）、Ruff、迁移漂移、Markdown 安全、PDF.js 两页不同 PNG/文本/预算/页越界、TypeScript/Vite 通过。test_preview_assets 覆盖非法来源、跨用户/课程、旧版保持、删除失效；test_migrations 覆盖原图片反链保留及重建故障回滚。
- Safari：新版资料/图片区域已渲染；窗口/选择器被切换，完整 PDF 上传/截图/回页未完成，不能把 Node 渲染写为 Safari E2E。未上传用户私人文件，未改其现有资料名或删除数据。
- 未完成/下一步：LibreOffice 成功路径、Safari 全链路/尺寸/性能、人工转录、资产标签/检索、附件 ZIP/完整恢复；完整 P0 仍 Doing。[缺口分析](../docs/zhy/materialhub/materialhub_gap_analysis.md)给出依赖顺序。
- 接收操作：fzk 复验旧图片插入/删除失效，消费来源字段但不把预览页拼成 DOCX block；回页按版本 ID。模型/试卷成员只消费已授权来源，不读文件路径、不自动发送截图。
- 个人证据：[progress](zhy/progress.md)、[features](../docs/zhy/features.md)、[optimizations](../docs/zhy/optimizations.md)、[公共进度](../docs/progress.md)。
- 接收记录：fzk 待本人填写日期、复验命令和结果；xtc/gcx 契约知悉待填写。
- 集成记录：本地工作区检查通过，未合并；正式 commit/PR/Wiki 及人类评审由队长按实际补充。

<a id="h-20261014-zhy-002"></a>
### H-20261014-ZHY-002：人工 PDF 补录与来源可靠性

- 日期：2026-10-14；记录者/辅助实施者 Codex（zhy 队长会话）；本人审阅待填写。状态待接收；代码工作区未提交/合并，已有用户修改保留。
- 模块/任务/需求：共享层 + M1；M1-TRANSCRIPT-01；FR-04/07/08/09/13，FR-39/40 的扫描来源依赖、NFR-06/10。无 OCR/远程模型/P1 范围，M4 内部未改。
- 输入/输出：当前用户原始 PDF 版本、真实页号、人工文字 → 独立草稿/确认/历史记录、人工 Chunk/Citation。先写 [contracts](../docs/contracts.md)，实现接口见 [API](../docs/api.md)。
- 文件：material models/ManualTranscript、Chunk source_kind、Citation source_kind、schemas/transcripts；transcripts router/service、共享来源 eligibility/checked_chunk、search/documents/worker；M2 上下文只接共享源过滤，M3 只记录/显示来源类型；frontend Material/PdfReader/Transcripts/API/搜索/AI/笔记来源/Help/styles；0006、4 新风险测试、文档。
- API/兼容：GET/POST versions/{id}/transcripts，PATCH transcripts/{id}，POST confirm/withdraw；草稿 revision 冲突 409 且本地保留，真实页数/格式/字符/版本配额服务端校验；旧 Citation/Chunk source_kind 默认 extracted。人工确认不伪改原 PDF parse/index 状态。检索只选当前确认，旧引用仍指旧文本；WITHDRAWN 不回退旧修订、引用 unavailable。
- 迁移 0006：新 ManualTranscript、当前确认页部分唯一索引、两个 source_kind 字段；旧身份与原文保留。运行库已只读确认 head=0006；本会话启动的旧资料 worker 已停止并重新启动加载新逻辑，没有终止用户另起的进程。
- 实测 bash scripts/check.sh：26 pytest passed（1 条依赖弃用警告），Ruff、迁移升级/漂移、Markdown 安全、PDF.js 实际双页、TypeScript/Vite 通过。新增测试覆盖草稿隔离/确认重试/修订竞争/撤回/越权与源删除、模拟旧 revision；另注入初次解析中断，恢复真实 pypdf 成功提取两页，人工 UUID 仍保留。并发线程压力未执行。
- Safari：当前窗口在 localhost:4321 无关页面下载提示中；未处理提示或上传用户文件，本轮未完成补录浏览器闭环。API/类型/构建结果不能冒充 E2E。
- 接收操作：xtc 使用 indexable_source，只检索当前确认补录并输出 source_kind，不自动发送远程；fzk 保存真实 Citation.source_kind，旧历史引用原文不覆写，撤回显示不可用；gcx 可消费人工 Chunk/定位/确认信息，正式拆题/映射仍按自身流程，不把人工补录当 OCR。
- 风险/下一步：Safari E2E、资源/并发压力、版本配额实机、资产标签/说明检索、任务取消/分页、完整导出/恢复、M4 消费与全 P0 验收仍待推进。
- 证据：[个人进度](zhy/progress.md)、[features](../docs/zhy/features.md)、[optimizations](../docs/zhy/optimizations.md)、[公共进度](../docs/progress.md)、[追踪](../docs/traceability.md)。
- 接收记录：xtc/fzk/gcx 待本人填写实际复验与决定；集成记录：本地检查通过，正式 commit/PR/Wiki 与人类评审待队长补充。

<a id="h-20261014-zhy-003"></a>
### H-20261014-ZHY-003：课程图片整理与元数据查找

- 日期/记录者：2026-10-14，Codex（zhy 队长会话辅助实施）；zhy 本人审阅待填。状态待接收，工作区未提交/合并，已有用户修改保留。
- 模块/需求/任务：共享层 + M1；M1-ASSET-ORGANIZE-01；FR-37 改名/说明/标签、FR-09 图片整理支持，NFR-06/07/10。没有扩展P1/P2，M2/M4内部未改。
- 输入/输出：本人课程图片与整理字段 → name/alt/tags/revision、可筛选分页目录、冲突最新元数据；不可变文件/hash/UUID/来源版本页号不变。先更新[contracts](../docs/contracts.md)，接口见[API](../docs/api.md)。
- 交出 zhy → fzk：旧数组 Asset 响应追加 name/tags/revision/UTC时间；笔记插入下拉框显示新名称，嵌入仍用原UUID，已有正文中的说明不自动改写。M3业务表/正文/保存逻辑未改；xtc/gcx知悉这是元数据查找，图中文字不自动进入检索/模型。
- 文件范围：共享Asset模型/AssetResponse/0007；M1 repositories/assets、schemas/assets、services/asset_organization、routers/assets、上传默认展示名；frontend materials/AssetLibrary（从公共knowledge移入M1）、API/styles、materials引用跳转、notes插入菜单展示适配；风险/迁移测试和公共/个人文档。
- API/迁移：PATCH assets/{id}原子revision条件更新，非法/null/未知字段422、越权/失效404、旧revision409.details.server_asset；GET courses/{id}/assets/page返回items/total/offset/limit/tags，过滤/计数/候选/写入共用有效来源条件，旧GET数组接口兼容。0007只追加列/回填旧名，SQLite DDL前开启真实事务，中断整体回滚可重试；旧反链UUID保留。
- 实测：`bash scripts/check.sh`：30 pytest passed（1条依赖弃用警告）、Ruff、迁移升级/ORM漂移、Markdown安全、PDF.js两页渲染、TypeScript/Vite构建通过。3新图片风险测试验证文件/hash/来源/反链不变、冲突、字面查找/精确标签/分页/归属/删除资格/预算；1新迁移故障测试验证回滚与重试，旧库测试追加回填。运行库只读确认head=0007、新列存在。
- Safari/限制：已观察Hustudy课程总览；窗口在动作前切换到其他项目导致元素失效，图片完整浏览器闭环未完成。未修改用户已有课程/图片或上传私人文件。未做线程压力、性能、真实用户试用。完整附件导出/备份、课程/笔记标签、资料/任务分页、显式任务取消/重建和完整P0仍待推进。
- 接收操作：fzk复验图片插入、原UUID反链、改名后回源、删除失效；页面上的409不得自动覆盖本地输入。无需改笔记正文中的历史说明。队长后续补Safari闭环/资源验收，再评审父需求状态。
- 证据：[个人进度](zhy/progress.md)、[features](../docs/zhy/features.md)、[optimizations](../docs/zhy/optimizations.md)、[公共进度](../docs/progress.md)、[追踪](../docs/traceability.md)。接收时间/决定由fzk本人填写；xtc/gcx知悉待填；commit/PR/Wiki和正式集成状态由队长按实际补充。

<a id="h-20261014-zhy-004"></a>
### H-20261014-ZHY-004：资料任务控制与本轮验收

- 日期/记录者：2026-10-14，Codex（zhy队长会话辅助）；本人审阅待填。工作区未提交/合并，状态待接收，用户既有修改/个人文件删除保留。
- 模块/任务/需求：共享 + M1；M1-JOB-CONTROL-01；FR-05/09、NFR-06/07/10。输入本人有效版本/任务，输出取消/恢复/幂等重建状态；M2/M3/M4内部业务表不改，无新增迁移。[contracts](../docs/contracts.md)、[API](../docs/api.md)。
- 交出zhy→xtc/fzk/gcx：取消可令版本PARSE/INDEX/PREVIEW为CANCELLED；来源UUID/已存原文/笔记引用不变，M2继续消费既有有效来源资格。恢复仍用原任务/尝试预算，不假定每次PARSE重试都会自动换新依赖任务；需要用户显式恢复失败/取消依赖。
- 文件：services/material_jobs、routers/documents、schemas/material；workers/materials领取/恢复/完成/FTS异常租约/预览输出/依赖排队；frontend API/materials任务按钮/筛选/请求恢复、共享select CSS；test_material_job_controls及公共/zhy证据文档。无M2–M4内部重写、无新依赖。
- 语义：POST cancel/扩retry/POST versions reindex，UUID重放返回原任务，不同请求已有活跃任务409；版本锁与条件租约写防迟到覆盖，预览每尝试独立文件、丢租约清理本次输出。取消停止结果写回，不宣称立即终止子进程；数据库仍head0007。
- 实测：bash scripts/check.sh全量35pytest passed（1条依赖弃用警告）、Ruff/迁移漂移/Markdown安全/PDF.js双页/类型/构建通过；列表归属补强后5个任务风险测试再通过，最终前端改动后再次构建通过。确定性交错/索引失败回滚/引用保持/预算/预览取消/人工来源边界，完整证据见[验收报告](../docs/zhy/materialhub/acceptance_2026_10_14.md)。已重启此前本会话的worker，无用户其他进程终止。
- Safari：窗口菜单选中Hustudy后，113片段/独立状态/预览降级/重建入口、图片空状态及窄窗口布局已观察；原生select样式已统一，最终截图待复验。独立课程提交被切换打断，运行库确认未保存；未操作已有资料任务或上传私人文件。完整取消→恢复→重建浏览器闭环、压力与真实用户试用未完成。
- 继续开放：资料/任务分页、课程整理、附件ZIP/完整恢复、LibreOffice成功转换、全资源权限矩阵/E2E和完整P0。自动验收通过不等于父需求/成员接收/合并完成。
- 接收操作：三位成员按本人流程复验来源状态与原引用保持，不能直接改任务表解除取消/重试上限；接收日期/结果待本人填写。zhy补正式commit/PR/Wiki、人工审阅与集成验收。
- 个人证据：[progress](zhy/progress.md)、[features](../docs/zhy/features.md)、[optimizations](../docs/zhy/optimizations.md)，公共[进度](../docs/progress.md)/[追踪](../docs/traceability.md)。

<a id="h-20261014-zhy-005"></a>
### H-20261014-ZHY-005：课程资料包与共享恢复验收

- 日期/记录者：2026-10-14，Codex（zhy队长会话辅助），本人审阅待填；工作区未提交/合并，状态待接收。用户现有改动及个人报告删除保留。
- 模块/任务/需求：共享 + M1，M1-EXPORT-01；FR-14/15/37的M1文件依赖，NFR-06/07/10。输入本人课程→原件/版本/预览/文本/确认补录/图片/来源ZIP；不含笔记、AI、考试/作答，不支持恢复，不标父需求Done。先更新[contracts](../docs/contracts.md)，实际接口见[API](../docs/api.md)。
- 交出zhy→xtc/fzk/gcx：M1来源清单保留UUID、原文定位/Unicode偏移/source_kind、每文件hash。fzk可据此设计完整笔记附件ZIP，但本包没有其正文/双链导出；xtc/gcx无需修改内部数据，不把资料包当完整学习记录备份，也不自动向模型发送包。
- 范围：models/material MaterialExport、0008/schema/router/service/worker；main/courses入口、资料worker调度/恢复；前端API/MaterialExports/materials/资产变更回调/Help/styles；独立脚本/5新风险测试/迁移head断言/公共与zhy记录。M2–M4业务表及内部逻辑不改。
- 迁移/API：0008追加导出表/课程和job FK，原资料/引用不重建；请求UUID幂等/同课程活跃导出409/最多20条；列表/详情/失败重试/ZIP下载/移除。后台MATERIAL_EXPORT，读快照/流式hash、256MiB总内容/16MiB元数据/120秒/70000成员；正文SQL预算先验。来源删除/撤回旧包下载404、文件损坏409、归属404；已下载本地副本无法撤销。
- 可靠性：失败与丢租约不挂载产物，中断旧ZIP恢复清理；完成只认本租约。测试暴露SQLite时间ORM内存比较问题，PARSE/EXPORT恢复使用数据库条件执行并清理缓存，新Session验证通过。运行库head=0008，已重启本会话worker，没有终止用户其他进程。
- 实测：bash scripts/check.sh：40pytest passed（1条依赖弃用警告）、Ruff/迁移漂移/Markdown安全/PDF.js双页/类型/构建通过。最终资源预检后5个导出风险测试/Ruff再通过，最终前端调整后构建通过。样例四格式/两个MD版本/3图片/确认和草稿、租约/预算/hash/删除/越权/路径；离线恶意ZIP拒绝，不执行真实网络。
- Safari验收：生成→后台完成→查看hash→ZIP下载，下载管理器显示约19.2MB（界面18.34MiB）。实际包3资料/3版本/374片段/377内容文件；下载文件离线大小/hash全部通过，整包hash匹配界面。原课程内容未修改，没有向外部服务发送；用户ZIP保留本机，不放docs/fixtures/Git。最后截图工具不可用，未保存最终布局截图。
- 判定/下一步：详见[验收与正式A01–A10关口](../docs/zhy/materialhub/material_export_acceptance.md)。资料/任务分页、课程标签、M3知识库ZIP/完整账户恢复、Python3.12/LO成功转换、压力/全资源矩阵、Gitee/CI/发布/用户试用仍待推进。
- 接收操作：成员本人复核UUID/来源类型/文件hash契约；当前包不是完整恢复输入。接收日期/测试/决定待本人填写；zhy补本人审阅/正式commit/PR/Wiki与集成发布，不将自动检查冒充人工签收。
- 证据：[progress](zhy/progress.md)、[features](../docs/zhy/features.md)、[optimizations](../docs/zhy/optimizations.md)、[验收](../docs/zhy/materialhub/material_export_acceptance.md)、[公共进度](../docs/progress.md)/[追踪](../docs/traceability.md)。

<a id="h-20261014-zhy-006"></a>
### H-20261014-ZHY-006：共享课程整理与验收

- 日期/记录者：2026-10-14，Codex（zhy队长会话辅助）；本人审阅待填。工作区未提交/合并，状态待接收，用户改动与个人报告删除保留。
- 模块/任务/需求：共享 + M1依赖，PLATFORM-COURSE-01、正式A02、FR-02/09、TC-01/06、NFR-06/10。本人课程→组织元数据/过滤/冲突；先更新[contracts](../docs/contracts.md)，[API](../docs/api.md)。M2–M4内部业务表/算法不改。
- 交出zhy→xtc/fzk/gcx：CourseResponse追加category/tags/revision，原课程/资料/笔记/考试UUID不变；旧列表/创建兼容。PATCH必须revision+至少一字段，未提交字段保留；旧revision409.details.server_course，不能静默覆盖。课程标签不自动传播。
- 文件/迁移：models/schemas/services/routers课程层、0009；API/Overview/CourseEditor/styles；课程/迁移风险测试及公共/zhy文档。0009只追加列/default，失败整体回滚，关系不重建。
- 实测：bash scripts/check.sh：43pytest passed（10.25秒、1条依赖弃用警告），Ruff/迁移漂移/Markdown安全/PDF.js双页/类型/构建通过；最终前端构建通过，主包约507KB提示。运行库head0009，本会话worker已重启加载新模型，未终止其他用户进程。
- Safari：自制课程创建→改名/描述标签保留→分类筛选/搜索空状态/重置→刷新持久化；双标签页409、本地保留、加载服务器版本已观察。最终标签按钮/排序/冲突刷新补丁复验受窗口切换限制；截图仅局部。自制课程保留复验，新增验收标签页已关闭；既有课程未改，无模型发送。
- 待办/接收：FR-02删除需M3课程笔记清理契约（当前SET NULL有关系脱离风险）及完整撤权；笔记标签/性能、资料任务分页、完整恢复/环境/发布待推进。成员本人复验Course字段/旧PATCH适配，填写接收时间/测试/决定；队长补commit/PR/Wiki/人工审阅。不能当父需求或全部P0 Done。
- 证据：[验收](../docs/zhy/shared_platform/course_organization_acceptance.md)、[个人进度](zhy/progress.md)、[features](../docs/zhy/features.md)、[optimizations](../docs/zhy/optimizations.md)、[公共进度](../docs/progress.md)/[追踪](../docs/traceability.md)。

<a id="h-20261014-zhy-007"></a>
### H-20261014-ZHY-007：课程删除与基本功能验收

- 2026-10-14，Codex（zhy会话辅助）；工作区未提交/合并，本人审阅/模块接收待填。PLATFORM-COURSE-DELETE-01，正式A02/A03/A04/A10，FR-01/02、TC-01/23、NFR-06/07/10。
- 先更新[contracts](../docs/contracts.md)与模块count/retire服务边界；Course新增deleted_at（0010）、GET删除预览、DELETE必须revision。共享协调器不直接读M2–M4内部表；各模块适配仅生命周期/授权，不改生成/评分/笔记算法。
- 交出zhy→xtc/fzk/gcx：只消费有效课程；删除后笔记不转全局、外部Citation保留unavailable，M2结果/M4记录及关联复习清理，独立任务保留。所有清理在同一事务，不在模块适配器里commit；失败全回滚。前端确认输入课程名；旧DELETE客户端补revision。
- 范围：Course/0010/schema/router、courses与course/material/note/ai/exam_retirement服务；M1资源与导出/worker课程有效性、M2/M3/M4授权/写入边界；前端API/Overview/CourseEditor/CourseDeletion/main/styles；风险测试/旧调用适配/文档。
- 实测：47pytest passed（10.56秒、1条依赖弃用警告），Ruff/迁移漂移/Markdown安全/PDF实际双页/类型/构建通过；29读取URL对两账户撤权、模块故障回滚、迟到ZIP清理、认证API风险通过。运行库head0010，只重启本会话worker。
- Safari：影响预览/名称不匹配禁用/匹配启用/返回保留课程通过；没有最终删除用户库课程，实际删除在隔离测试执行。逻辑撤权不是物理擦除；完整备份恢复等尚未完成。
- 接收：成员本人复验生命周期接口/有效课程检查/无独立commit，填写时间/结果/决定；zhy补正式评审/commit/PR/Wiki。标准JWT迁移、资料分页、完整恢复/M2–M4规划、性能/环境/E2E/发布待办，不标全部P0 Done。
- 证据：[验收矩阵](../docs/zhy/shared_platform/basic_acceptance.md)、[公开测试报告](../docs/test_report.md)、[个人进度](zhy/progress.md)、[features](../docs/zhy/features.md)/[optimizations](../docs/zhy/optimizations.md)。

<a id="h-20261014-zhy-008"></a>
### H-20261014-ZHY-008：智谱真实课程问答

- 日期/记录者：2026-10-14，Codex（zhy队长集成会话辅助）；未提交/合并，本人审阅/成员接收待填。用户指定GLM-4.7-Flash，密钥值不记入协作材料，不冒记xtc本人贡献。
- 模块/需求：M2-ZHIPU-QA-01，FR-16/17/19/20问答、TC-10/11/12，正式B03/B04/B07/B08与共享/M1依赖。先更新[contracts](../docs/contracts.md)，[API](../docs/api.md)。
- 交出zhy→xtc/fzk/gcx：M1只读ai_context选择/验证同课程来源；M2 RemoteQuery不可变预览→确认→AI_ANALYSIS(resource_id=RemoteQuery)→真实AIResult/结构化Citation。worker只领取本模块资源任务；网络等待不占写锁。M3草稿冻结引用，M4不得直接拿未审阅结果作正式试卷。
- 文件/迁移：后端配置/SecretStr、0011/RemoteQuery/schema/providers/context/service/router/worker；生命周期取消与共享job读取；前端API/RealQueries/AIStudy/模式提示/帮助/草稿；配置/自制probe脚本/fixture/风险测试/文档。只扩展课程问答，不启用真实报告/M4生成。
- 语义：GET配置不含密钥，预览不调用；严格确认/15分钟/同预览幂等/每课程一个活跃任务。派发前核对，派发后不可召回；取消/删源不采纳迟到结果。坏JSON/伪引用/截断/401/429/超时/网络/预算失败，不自动重发，保留旧结果。
- 实测：67pytest passed（11.68秒、1条依赖弃用警告），Ruff/迁移漂移/Markdown安全/PDF实际双页/类型/构建通过；20项新增风险场景使用假密钥/MockTransport。实际自制苹果请求grounded/1引用/417tokens；没有自动发送用户课件。
- 运行：.env0600/忽略，前端产物/代码/文档密钥扫描无命中；head0011。默认沙箱网络受限，获准外网的本会话worker已启动，其他用户进程未终止。配置更新需重启API/worker。
- Safari/剩余：模式/配置/预览入口已观察，文件选择遭状态切换，完整正向闭环未完成。保留/训练/远程删除政策未核实，真实报告/题目/统计、完整备份与全部P0待办。
- 接收：xtc复验Provider/schema/任务预算/坏输出路径；fzk复验草稿来源冻结/删除失效；gcx维持审阅/双来源生成门禁。本人填写接收时间/测试/决定，zhy补正式评审/commit/PR/Wiki。
- 证据：[验收](../docs/zhy/integration/zhipu_qa_acceptance.md)、[个人进度](zhy/progress.md)、[features](../docs/zhy/features.md)/[optimizations](../docs/zhy/optimizations.md)。
- 2026-10-15补验：新增AIAnswerPreview及组件SSR检查，生成链接/图片不产生导航/外部加载，原文回源走Citation；最终67pytest（12.29秒）与全部共享检查通过。Safari切换真实模式后返回登录，原因未定，正向确认/结果/草稿闭环待补；本人审阅/接收状态不变。

<a id="h-20261015-zhy-009"></a>
### H-20261015-ZHY-009：队长完成核查与文档分类

- 日期/记录者：2026-10-15，Codex（zhy队长会话辅助）；DOC-ZHY-AUDIT-01；工作区未提交/合并，状态待接收，本人审阅/接收待填。用户要求核实共享基础层+M1是否全部完成并正确归档。
- 输入/结论：正式A01–A10、需求/规划、代码及历史验收。整体Doing，尚未全部实现/验收；明确标准JWT、统一存储/低磁盘、前端基线、规模/完整恢复/环境/交付缺口，不计算虚假完成率。
- 分类：7份个人记录分别归入docs/zhy/shared_platform、materialhub、integration、history；features改为当前分类，新增[技术核查](../docs/zhy/completion_audit.md)与[当前任务状态](zhy/task_status.md)。公共API/契约/操作/全站集成结论保留根级，统一handoff不迁入个人目录；同步导航与相对链接。
- 交出zhy→xtc/fzk/gcx：GLM问答属于M2队长辅助集成，M3知识库ZIP、M4分析/拟卷仍由原模块主责；完整备份由共享层协调模块契约。只编辑zhy与公共入口，不代写其他成员个人贡献、签收或实验结果。
- 需求/代码影响：A01–A10与FR-01–09/36/37、FR-14/15共享依赖、NFR-01/02/06/08/09/10追踪更清楚；无业务代码/schema/迁移/依赖变化，不改变P0/P1范围，也没有远程发送。
- 验证：本轮执行文档链接/归档保持/唯一ID/差异检查，具体结果补在本条末尾；未重跑业务测试。67项通过是此前代码检查结果，不冒记本轮测试运行。
- 接收操作：各成员按[任务状态](zhy/task_status.md)确认依赖与模块边界；有技术基线调整先提公共决策/契约，接收时间/复验/决定由本人填写。zhy审阅核查结论并补正式提交/PR/Wiki。
- 实际文档校验：64份文档、577个本地链接全部存在；7份归档报告保留日期证据与当前核查入口，12个handoff ID唯一；正式A01–A10在当前任务表各出现一次；两目录四人成员入口保留，用户已删除个人报告未恢复；git diff --check通过。没有将链接校验当业务测试。

<a id="h-20261015-zhy-010"></a>
### H-20261015-ZHY-010：共享认证/存储与M1目录规模

- 2026-10-15，Codex辅助zhy，工作区未提交/合并，状态待接收，本人审阅待填。任务PLATFORM-AUTH-02、PLATFORM-STORAGE-01、M1-BROWSE-01；正式A02/A04/A05/A08/A10，FR-01/03/05/09/37、NFR-01/06/07/10。
- 先定义公共契约；标准JWT替换/旧会话重登、强密钥初始化、401反馈；统一原子文件适配器/低磁盘507/回滚与worker预算；资料/全部历史任务分页/稳定排序/页外回源。无数据库迁移，不改M2–M4业务算法/个人记录。
- 验证：新增29个风险场景，最终96passed(15.84秒)及Ruff/迁移漂移/显示安全/PDF双页/类型/构建通过；JWT与存储阶段分别89/94。实际命令bash scripts/check.sh，日志/tmp/hustudy-browse-01.log。Safari/容量/p95未测。
- 交出zhy→xtc/fzk/gcx：Bearer/响应字段保留，新登录是JWT；旧token401不可兼容。旧资料/jobs数组API仍可用，新分页计数先归属过滤；统一FileStorage不代替模块权限。成员按本人环境复验并填写接收，不代签。
- 证据：docs/zhy/shared_platform/auth_jwt_acceptance.md、storage_acceptance.md，docs/zhy/materialhub/browse_acceptance.md。完整账户恢复、前端基线、环境/性能/浏览器与发布仍待推进。

<a id="h-20261015-zhy-011"></a>
### H-20261015-ZHY-011：完整账户备份与空账户恢复

- 2026-10-15，Codex辅助zhy；PLATFORM-BACKUP-01，A03/A04/A10，FR-15、NFR-08/06/07/10。工作区未提交/合并，状态待接收，本人审阅待填。
- 先更新公共契约，0012只新增account_archives；共享协调器经M1/M2/M3/M4快照/校验/应用适配器导出/恢复，不直接操作其他模块内部表。新账户身份保留，业务UUID/hash/UTC/引用保持，FTS重建；不导出凭据/密钥，不恢复自动模型任务，不复制可重建M1 ZIP文件。
- POST /backups、GET列表/详情/下载、POST /backups/restore（file+confirm=RESTORE_EMPTY_ACCOUNT）、DELETE终态记录；同库UUID冲突/非空账户拒绝，文件/清单/schema/归属/FK/Citation/预算先校验，任一失败回滚业务与清理本次文件。最多50条，运行中不可移除。
- 实测：新增5项集成风险测试含四格式、3图、3笔记双链、2卷作答、人工历史来源/演示AI/错题/时区的隔离往返；损坏/实际字节/伪引用/越权/缺失关系/提交故障/过期不重放/终态清理通过。最后bash scripts/check.sh 101passed(16.43秒)及共享Ruff/迁移漂移/显示安全/PDF/类型构建通过；日志/tmp/hustudy-platform-final.log。
- 运行库只读确认0012，迁移前由既有机制在线备份；现有用户账户未删除/覆盖，移除源对象只发生于隔离测试库。Safari/跨机器/压力未完成；M3单独知识库ZIP、前端基线/环境/正式发布仍待推进。
- 交出zhy→xtc/fzk/gcx：各自只维护自身备份适配器和新增schema版本，不能绕过单事务或自动派发模型；schema变更同步备份格式/迁移/追踪。本人填写接收/复验，不能将队长辅助记录冒记为成员本人贡献。
- 证据：[验收](../docs/zhy/shared_platform/account_backup_acceptance.md)，公共API/contracts及个人task_status/progress/features同步。

<a id="h-20261015-zhy-012"></a>
### H-20261015-ZHY-012：共享前端基线、会话恢复与隔离验收

- 2026-10-15，Codex辅助zhy；PLATFORM-WEB-BASE-01，A01/A02/A09/A10，FR-01/03/06/09/11/13/15，NFR-06/07/09/10。工作区未提交/合并，状态待接收，本人审阅待填。
- 输入/决定：既定React Router/Query/Ant Design基线、当前编辑草稿和API；先更新contracts，再接URL导航/统一离开保护、会话+写入代次GET去重/失效、同账户重登保留草稿、统一主题与按需加载。无数据库/API破坏性变化，不改M2/M4算法；M1/M3仅调整重登时初始定位不覆盖草稿。
- 实测：check101pytest15.52秒、10Vitest、Ruff/迁移漂移/显示安全/PDF实渲染/类型构建通过；Chrome/WebKit各4项共8项52.2秒，含真实隔离API上传检索、定位导航、401后两类草稿保留及备份实际下载hash。独立Python3.12.13锁依赖101passed24.19秒。1条依赖警告；主包485.85KB，无500KB提示。
- 隔离：8056/5178、TemporaryDirectory数据库/文件、Mock/空远程密钥，不改用户8000/5173课程；401为测试注入，登录为真实API。Safari查看资料/备份入口；本轮管理的旧worker已重启。未更换用户运行解释器，未发送课程到远程模型。
- 交出zhy→xtc/fzk/gcx：导航继续走共享路由；JSON读取经公共client，失败的模型确认不能自动重试；token更新不重置已有编辑内容。新增模块页面统一主题/加载状态，服务端仍执行所有权检查。成员本人复验并填写接收，不代记。
- 未决：Office成功转换、完整业务/多标签页/跨机器/容量性能、CI/Gitee/正式评审发布和真实试用；M3知识库ZIP、M2真实报告、M4正式拆题统计/真实拟卷仍属原模块。
- 证据：[验收](../docs/zhy/shared_platform/web_base_acceptance.md)、[环境操作](../docs/setup_guide.md)、[当前任务](zhy/task_status.md)。成员接收时间/证据/决定由本人补充。
- 最终复核：61份文档577个本地链接无缺失、16个handoff锚点唯一；git diff --check、setup/check的bash语法、隔离服务Ruff、3.12临时迁移/漂移与最后前端类型/构建通过。未改其他成员个人记录、未恢复用户已删除个人报告。

<a id="h-20261015-zhy-013"></a>
### H-20261015-ZHY-013：Office预览恢复、Safari兼容与隐藏页

- 2026-10-15，Codex辅助zhy；M1-PREVIEW-RECOVERY-01，A04/A07/A10，FR-05/06/07/13/36/37、NFR-06/07/10。工作区未提交/合并，待本人审阅/成员接收。
- 先补contracts，再实现能力检测/后端路径配置/显式预览恢复，复用原任务次数与归属；转换60秒/独立profile/PDF预算与可读性校验，失败不发布。新GET material-capabilities、POST versions/{id}/preview-jobs，无迁移，不改M2–M4内部。
- 实际Safari课件失败两层：缺LibreOffice→安装26.8.1；渲染Map.getOrInsertComputed缺失→同版本PDF.js legacy显示层/worker。新增错误详情/重试打开和阅读区恢复入口。PPTX导出隐藏页并校验数量，旧错位预览读取/截图拒绝，有截图不静默改变来源。
- 最终验证：check110pytest15.47秒、10Vitest、Ruff/迁移漂移/安全显示/PDF双页/类型构建通过；Chrome/WebKit14项约1.5分钟（移除新Map方法、隐藏PPT页、三格式真实转换截图回源），独立3.12相关17项3.40秒。主包485.98KB/PDF阅读器492.59KB，1条依赖警告；不是性能达标证据。
- 当前无截图旧课件缓存通过M1归属服务恢复146页/146张，原件/版本/Chunk未变；Safari曾实际显示第一页。最新146页在新标签因会话过期需原账户登录，未获取密码/冒记最终实机再打开。现有其他浏览页保留，无用户课件远程发送。
- 交出zhy→xtc/fzk/gcx：来源继续按固定版本/原slide或docx_block；DOCX预览为preview_page。Office失败可文本降级，截图仅使用已通过页号检查的预览；不要绕过服务读取错位旧缓存。新增schema或预览来源行为变动先更新公共契约。
- 证据：[验收](../docs/zhy/materialhub/preview_recovery_acceptance.md)、[实际测试报告](../docs/test_report.md)、[当前任务](zhy/task_status.md)。复杂版式、已有错误截图人工处理、完整矩阵/容量/p95/发布待办；本人接收时间/复验由本人填写，不能代签。初拟搜索分页仍待后续独立切片。

<a id="h-20261015-zhy-014"></a>
### H-20261015-ZHY-014：分页检索、解析完整性与队长自动验收

- 日期2026-10-15，Codex辅助zhy；M1-SEARCH-02，A01/A02/A04–A10、FR-04/05/06/07/08/09/13/15/36/37、NFR-01/02/03/06/07/10、TC-06/21/23/25。工作区未提交/合并，状态待接收，本人审阅待填写。
- 先写contracts，再实现GET search/page与M3只读note-search适配器、Unicode纯文本摘要和双独立分页；旧search数组50条不变，新页可遍历全部结果。SQLite显式只读快照使计数/页内容一致；跨页不是冻结快照。PPTX组合形状漏文修复，不重写旧不可变版本；新导入版本生效。笔记不可用提示适配不改正文。无迁移/新增依赖。
- 代码范围：共享database/search_excerpt、M1 search/material parser/schema/router、M3 note_search只读service/schema/router、公共client/SearchExcerpt/Search工作区、笔记一处状态文字、对应测试与隔离验收脚本。M2/M4算法与他人成员个人目录未改。
- 最终bash scripts/check.sh：116pytest16.69秒、12Vitest及Ruff/迁移漂移/显示安全/PDF/类型构建通过；3.12.13工作区116项16.96秒；Chrome/WebKit20项1.8分钟无重试。先修复新增测试漏接确认框的2项超时，再全量通过；PPTX漏文先有失败复现。19类读取/10种越权写及课程删除矩阵通过。
- 容量：隔离10课/200实际上传文档/1000笔记/5000chunk，5类HTTP接口各100次/4并发，p95最大275.814ms；20张PPTX/50页文本PDF解析索引0.191/0.1766秒。同机M4/24GiB，不冒记低配/物理冷盘/复杂样本。干净源码新venv/npm ci重建115项21.66秒与共享check通过（快照早于新增归属矩阵，最新工作区另116项）。
- 交出zhy→xtc/fzk/gcx：摘要偏移仅显示，不可当Citation；消费新分页的total/offset，不用旧数组长度代表总量。M1不得直接查笔记表，走M3只读适配器；历史引用不受新解析影响。真实成员复验/签收由本人填写，不能代记。
- 证据：[验收及JSON](../docs/zhy/materialhub/search_capacity_acceptance.md)、[当前完成判断](../docs/zhy/completion_audit.md)、[任务状态](zhy/task_status.md)。A01–A08进入Review；A09/A10的Gitee/评审/成员签收/全站剩余模块集成/发布和真实试用继续Doing。无用户资料/密钥复制或真实模型调用；极限资源/多worker长压/其他机器/本机Safari全矩阵另列。
- H-20261015-ZHY-014最终复核：63份文档622个本地链接有效、18个handoff锚点唯一，git diff --check/Ruff/bash语法通过。追加跨窗口删除导致空页的分页提示/返回页钳制修复，Chrome/WebKit同一分页场景2项12.6秒通过，不与全量20项累加；TypeScript通过，日志/tmp/hustudy-search-deletion-final.log。

<a id="h-20261015-zhy-015"></a>
### H-20261015-ZHY-015：PPT/PDF/Word原格式阅读

- 2026-10-15，Codex辅助zhy，M1-NATIVE-PREVIEW-01，FR-06/36/07/37依赖、NFR-06/10、TC-04/26，用户CR-M1-NATIVE-01；工作区未提交/合并，状态待接收，本人审阅待填。
- 输入为授权原件，输出PPTX/Word本地直接预览、PDF原页、独立兼容PDF。先更新contracts/需求/方案/AGENTS，再实现原格式阅读器/nonce隔离frame/runtime、原件可取消读取、M1入口/兼容诊断折叠、构建pre钩子/许可及测试。无迁移，不改M2/M3/M4内部业务或成员个人记录。
- PPT按原幻灯片/隐藏页，Word段落样式/表格图片/显式分页，提供翻页/跳转/缩放/PPT演示。原格式不依赖转换成功；失败显式重试或用户选择兼容。后台解析只补文本，保持当前模式。原件/Chunk/Citation不重写，截图仍走既有PDF页来源契约。
- iframe仅allow-scripts，无同源/网络/弹窗/表单权限，仅传字节/通道不传token。消息source/origin/channel/页数校验；本地IIFE及nonce-CSP，外部资源/父存储访问阻止。上游版本、Apache/MIT/MPL嵌入源码声明及ECMA通知完整保留，见third_party与licenses，未修改上游覆盖文件。
- 实测：116pytest19.60秒及共享检查；14Vitest；最终Chrome/WebKit26项2.1分钟无重试，含6项新原格式/坏ZIP恢复和确定性后台完成不切模式。修正StrictMode故障注入和真实后台重置问题后才最终通过。最后类型/构建通过；新增依赖后未重做容量、独立3.12全量或干净安装，不冒记为新测量。
- 交出zhy→xtc/fzk/gcx：preview_status继续代表兼容PDF，不由客户端改写；原格式页不作为DOCX引用页码，现有Citation/Asset回源保持。不要移除nonce/原件权限/消息校验或给frame加same-origin；保留build:office和许可。成员本人复验并记录接收，不代签。
- [验收](../docs/zhy/materialhub/native_preview_acceptance.md)，[当前核查](../docs/zhy/completion_audit.md)。旧.ppt/.doc/完整Office动画和复杂版式不承诺，实机Safari完整矩阵/团队评审/正式发布继续待验收；本轮未访问用户原件或发起真实模型调用。
- H-20261015-ZHY-015最终复核：26E2E/14Vitest/类型构建通过；64文档638本地链接有效、19锚点唯一，diff/Ruff/Node脚本语法通过，许可归档与生成notice一致。生产静态原格式runtime/notice由构建生成，主包486.40KB；未改用户课程/恢复其删除报告或替成员签收。


<a id="h-20261015-zhy-016"></a>
### H-20261015-ZHY-016：全站多屏排布与统一密度

- 2026-10-15，Codex辅助zhy；PLATFORM-RESPONSIVE-01、CR-PLATFORM-RESPONSIVE-01、NFR-09/10及FR-06/10/17/25展示。本人审阅/成员接收待填，工作区未提交/合并，保持已有用户改动与删除。
- 先更新contracts，再实现共享responsive.css、WorkspaceNavigation/CompactLibrary，主壳层与M1/M3展示容器；总览描述摘要、PPT比例外框；M2/M4只消费共享样式，未重写算法/他人个人记录，无API/schema/迁移/新依赖。
- 界面13px/标题20–26px、桌面紧凑侧栏、窄屏吸顶抽屉/焦点恢复、资料笔记目录折叠并保持挂载；触屏44px热区/16px输入，代码表格容器滚动，原格式字号/引用独立。取消离开仍保留草稿，成功导航才关闭；旋转与401沿用已有保护。
- 实际全量Chrome/WebKit40项3.2分钟无重试、14Vitest、TypeScript/构建通过；吸顶收尾20项1.5分钟、PPT比例与实际画布可视区6项31.8秒、WebKit三尺寸截图3项22.7秒子集通过，不累加。初轮Chrome首尾Tab与Array.at目标lib问题已修正；后端未改未重跑，历史116项不冒记本轮结果。
- 交出zhy→xtc/fzk/gcx：统一断点/控件/图标/密度，新界面按共享样式接入；不能裁掉body溢出掩盖问题，不缩小源文档字体，不绕过离开确认或销毁折叠内容状态。自身模块后续交互需复验触屏和中等桌面。本人接收/复验由本人填写，不代签。
- [验收与5张自制样例截图](../docs/zhy/shared_platform/responsive_layout_acceptance.md)、[当前任务](zhy/task_status.md)。浏览器宽度/触控模拟不是iPad/iPhone实机或TC-24真实用户反馈；正式Gitee/评审/发布与其他模块剩余P0状态不变。未改运行库或调用真实模型。

- H-20261015-ZHY-016最终复核：最后TypeScript/Vite构建通过（主包488.37KB），67份文档683本地链接无缺失、20交接锚点唯一，git diff --check通过；5张自制数据截图已归档，未代填成员签收或实机/真实用户结论。


<a id="h-20261016-zhy-001"></a>
### H-20261016-ZHY-001：全站视觉与交互状态统一

- 日期2026-10-16，Codex辅助zhy，PLATFORM-VISUAL-02、NFR-09/10及FR-06/10/17/25展示；工作区未提交/合并，状态待接收，本人审阅待填。
- 输入为用户继续优化整体感/文字/按钮/配色的要求；先写contracts，再以公共responsive.css/主题统一色板、文字/卡片、按钮/焦点/状态，顶部区域与侧栏账户、空状态/备份主题、自制SVG、真题/蓝图标签及登录/帮助文案。M2–M4仅必要展示适配，不改业务算法/数据库/API，无迁移/依赖/远程资源或模型调用。
- 实际最终Chrome/WebKit42项3.6分钟无重试、14Vitest（397ms）、类型/构建通过；7处关键配色≥4.5及减少动效/5尺寸触控/原闭环通过。首轮跨夜33通过9超时、重启中断保留说明，未扩大时限或算作通过；连续全量没有重现。后端未改未重跑。
- 交出zhy→xtc/fzk/gcx：复用公共主色/字体/按钮/状态与SVG，保留44px触控/16px表单及原文独立字号；状态配文字，不靠颜色或虚构数据美化。继续使用既有路由/未保存保护/模型发送确认，模块后续页面改动复验同一视觉与多屏。成员本人复验/签收待填写，不代签。
- [验收与5张自制数据截图](../docs/zhy/shared_platform/visual_polish_acceptance.md)、[当前任务](zhy/task_status.md)。本机5173开发服务保留；未操作用户课程或密钥。实机Safari/iPad/iPhone完整矩阵、真人试用、Gitee/合并/发布与其他模块剩余P0不因此完成。

- H-20261016-ZHY-001最终复核：浏览器进程退出0，42项完整通过；68份文档701本地链接无缺失，21交接锚点唯一，git diff --check通过。成员本人审阅/签收仍待填写。


<a id="h-20261016-zhy-002"></a>
### H-20261016-ZHY-002：进度文档校正与GitHub同步指引

- 2026-10-16，Codex辅助zhy，DOC-PROGRESS-SYNC-01，NFR-10/A09/A10；状态待接收，本人审阅待填，工作区未提交/合并。
- 输入为已有实现/实际验收与用户“微调README、collaboration、docs并告知Git提交推送”要求；输出为当前能力/待办/日期清晰的入口、公共路线/复现/追踪、zhy索引及github_sync操作指南。README旧增量折叠保留，任务板/进度历史不改写；xtc/fzk/gcx本人记录未代写。
- 核对本地main、HEAD67a76a9、SSH origin=HAOYI0727/Hustudy、现有忽略规则与已跟踪tsbuildinfo；两份个人报告删除保留原状态。未执行fetch/分支创建/暂存/commit/push，未联网确认远端更多分支，提交/PR链接由实际执行后补入。
- 本轮纯文档：仅检查本地链接/交接ID与git diff --check；未重跑后端/前端/浏览器/性能测试，无代码/迁移/运行数据或模型请求变更。已有116后端和14Vitest/42双引擎保持各自实际日期，不等同本轮新测量。
- 交出zhy→xtc/fzk/gcx：先读当前入口/正式任务，再读历史；A01–A08 Review、A09/A10 Doing及其他模块剩余P0不变。按[GitHub指南](github_sync.md)评审同步功能分支，真正推送/复验后补commit与本人接收，不代填已合并/发布或Gitee证据。

- H-20261016-ZHY-002文档校验：69份文档748个本地链接有效，22个交接ID唯一，git diff --check通过；暂存区无变更，未执行提交/推送或重跑业务测试。


<a id="h-20261016-zhy-003"></a>
### H-20261016-ZHY-003：zhy阶段成果提交与GitHub发布

- 2026-10-16，用户明确授权Codex辅助zhy完成提交推送；分支feature/platform-materialhub，commit信息注明zhy。主分支保留，不合并、不代签成员；推送结果待远端校验后补充。
- 当前暂存包含共享层/M1、必要模块集成、测试、自制样例与文档；既有两份个人报告删除保留，生成的tsbuildinfo差异不提交。候选322文件约8.03MiB，无运行数据/已配置密钥命中或超50MiB文件。
- SSH fetch被GitHub公钥认证拒绝；已通过连接器确认本人HAOYI0727具目标仓库写入权限，改用授权GitHub接口发布同一Git树。未修改原远程SSH设置，不输出或索取密钥。
- 阶段测试引用既有10-15后端116项、10-16前端14Vitest/42双引擎，不重跑或冒记本次测量。首次完整暂存检查发现上游许可证保留空白及2处源码EOF空行；仅清理2处源码EOF，原许可证不改写，其余源码/文档空白检查继续执行。
- 本人/成员评审与develop集成、全P0/实机/真实用户/正式发布仍待；本次仅发布功能分支。实际commit/远端一致性以完成后的核对记录为准。

<a id="h-20261016-gcx-001"></a>
### H-20261016-GCX-001：M2真实章节报告闭环

- 日期/成员：2026-10-16，gcx=B/M2，Codex辅助实现；用户已确认与xtc交换模块和时段。
- 状态：待接收/Review；工作区未上传GitHub、无commit/PR/发布。人工审阅待gcx本人填写，未代签其他成员。
- 需求/任务：FR-16–20、FR-18.1–12；B02/03/05–10。功能/操作/真实证据见[gcx验收](../docs/gcx/study_report_acceptance.md)、[后续计划](../docs/gcx/m2_plan.md)。
- 修改：M2 schema/provider/service/router/worker、AI页面及报告展示、测试与Windows验证入口；共享只读来源新增报告范围查询。无新数据库schema/迁移/依赖；不改M3/M4业务内部，不自动调用真实模型。
- 契约：courses/{id}/study-reports/preview → 既有remote-queries确认/查询/取消 → 持久报告及历史；具体见[公共契约](../docs/contracts.md)。仅发送所见范围、预算/截断明确；教学标签仅AI建议，真实质量需人工核实。
- 真实验证：最终关联回归45 passed/14.69秒；Vitest14、Chrome390/1440px共2 passed/17.1秒；Ruff/类型/构建/迁移漂移/Markdown显示安全/PDF实渲染通过。全量初次129通过/3个既有Windows权限前提失败；不是全站通过。Chrome AI响应为替身，真实模型端到端未验。
- 接收人：xtc（M4候选接口后续依赖）、fzk（报告草稿到笔记）、zhy（共享来源与集成）。请各自复验，不将待接收当已验收。
- 下一步：重启API/worker，用户自行确认发送以核对真实报告；10月24–25日统一M4枚举并实现QuestionDraft；WebKit/实机、学科质量、全站Windows测试适配待补。
- 接收/复验：待接收人本人填写。

<a id="h-20261016-gcx-002"></a>
### H-20261016-GCX-002：M2候选、精确来源、完整演示与错误诊断

- 日期/成员：2026-10-16，gcx=B/M2，Codex辅助实现。用户最新授权取消M2按日期刻意分段，按依赖持续提前交付。
- 状态：Review/待接收；本地工作区未上传GitHub/未发布，无commit/PR。gcx本人审阅、xtc/fzk/zhy接收均待本人填写。
- 范围：真实3模式/3题型QuestionDraft，严格整批校验、M4只读目标/已确认原题快照、完整固定报告和候选演示、精确片段、持久问答/候选历史、安全错误细分、作者审阅与JSON导出。M2 schema/provider/service/router/worker和AI页面/测试/文档；新增exam_ai_context只读桥，不commit，不改M4业务状态或共享数据库schema。
- 输入/输出：先以courses/{id}/question-drafts/preview取得不可变设置/目标/原题/材料，再沿用remote-queries确认/查询/取消；输出永远draft候选。公开[QuestionDraft Schema](../docs/gcx/question_draft_schema.json)，只读桥的to_exam_enums提供旧模式/题型转换。完整API见[契约](../docs/contracts.md)。
- 实际测试：最终关联89 passed/27.77秒；Chrome390/1440px报告/候选/精确选择/导出/历史/固定报告共4 passed/22.5秒；Vitest14、Ruff/类型/构建、迁移无漂移/安全显示/PDF通过。全量中间版167通过/3个既有Windows权限前提失败，44.19秒；不声称最终全量或真实学科质量通过。
- 证据：[本轮验收](../docs/gcx/candidate_acceptance.md)、[当前B01–B10与依赖](../docs/gcx/m2_plan.md)、[人工评估空表](../docs/gcx/evaluation_checklist.md)、[累计上传清单](../docs/gcx/changed_files_2026_10_16.md)。用户此前报告基本正常，仅作操作反馈，不代填质量正确率。
- 真实依赖：M4未提供章节UUID实体，候选chapter_id暂为DocumentVersion UUID并声明chapter_ref_kind=document_version；xtc需映射正式蓝图、重新校验全卷数量/章节/分值/状态并冻结来源，不能直接当正式试卷。M1教师标注/M4完整确认映射和统计证据契约缺失，报告teacher_mark/observed_exam仍未接入。原题确认不等于考点映射确认。
- 接收人：xtc（候选服务/正式章节与试卷接入）、fzk（报告/问答草稿与来源）、zhy（只读桥、共享集成、Windows测试前提）。不自动外发消息，不代签。
- 用户复验：重启API和worker，刷新AI页面；可用自制资料/“进程与线程”Topic运行固定候选/报告，或自行预览确认真实请求。真实质量/WebKit/实机/成员接收仍待。
- 接收/复验：待接收人本人填写。

## H-20261016-GCX-003

2026-10-16，Codex辅助gcx，M2结构化响应诊断；工作区未提交/未上传，待接收。接收人：xtc、zhy（未签收）。用户约400字请求仍结构化输出失败，历史原始错误原因未知。Provider区分INVALID_JSON与INVALID_OUTPUT，后者message仅含schema白名单字段路径与固定原因；候选prompt v2提供完整示例，QuestionDraft与DB不变。76项回归通过/12.34秒，Ruff通过；未调用真实模型。重启worker后新确认请求使用更新，旧记录不迁移。详情见docs/gcx/optimizations.md。

## H-20261016-GCX-004

2026-10-16，Codex辅助gcx，M2-LABEL-REVIEW-01，工作区未提交/未上传，待接收。接收人fzk/xtc/zhy，未代签。补FR-38标签审阅→Markdown正文→现有笔记接口，保留原始AI结果/建议/引用；报告新增可选教学分层/概念关系/难点步骤/复习建议，旧JSON兼容，提示词/固定演示v2，无数据库迁移和新依赖。M3接口未改。后端87/前端17/Chrome4、构建/安全/Ruff通过；未调用真实模型。教师/真题依据、M4正式蓝图映射、真实质量与实机仍待接收复验。详情见[验收](../docs/gcx/basic_acceptance.md)。

H-20261016-GCX-004用户反馈补充（2026-10-16）：gcx表示本轮新增功能试用后认为没有问题；未代签fzk/xtc/zhy接收，未关闭真实模型质量及跨模块依赖。此次仅文档更新。

## H-20261016-GCX-005

2026-10-16，Codex辅助gcx，M2入口命名与用途说明；工作区未提交/未上传，待接收，未代签其他成员。入口名改为资料原文检索、资料问答、学习报告、练习题生成；本地检索不调用模型，预览确认及结果审阅流程保持。修改frontend/src/features/ai/index.tsx及现有浏览器定位，测试更新不涉及其他模块行为。TypeScript检查通过，4项M2 Chrome流程通过/25.3秒。文档见gcx/features、optimizations和个人progress；无API/schema/依赖变化，不需后端/worker重启。

## H-20261017-GCX-001

Codex辅助gcx，M2-MODEL-53-FLASH，用户指定GLM-5.3-Flash。原Hustudy-main的Settings/.env.example/configure脚本默认新模型，保留旧4.7兼容；本机.env只改模型，不上传。Provider新模型启用思考+low effort，JSON/预算/引用保持，状态文档对应模型切换；旧预览/旧排队任务配置变更后拒绝派发。104后端/4Chrome及Ruff通过，未调用真实模型、新增依赖或迁移；真实内容/费用/权限待用户实际确认。工作区未上传、待zhy/xtc/fzk接收，不代签；旧已上传83项副本/已下载版本未修改。[证据和重启](../docs/gcx/model_switch_2026_10_17.md)。


<a id="h-20261017-gcx-002"></a>
## H-20261017-GCX-002：逐题知识点与已有结果复用

- 日期/成员：2026-10-17，Codex辅助gcx，M2-TOPICS-REUSE。状态：本地实施、待接收；未上传或代签接收，无commit/PR链接。
- 输入/输出：新候选信封per_question_topics=true、提示词v5，逐题非空合法Topic子集；页面与既有QuestionDraft JSON保留每题关联。旧信封/历史兼容，不改正式试卷。
- 复用：三类真实任务预览新增reusable_result；POST /remote-queries/{id}/reuse显式选择已有结果，归属/来源/设置/当前提示词/模型/完整成功及依赖复验，无新任务/模型调用。仍可显式确认重新生成，失败/部分/演示/旧提示词不复用，无新表/迁移/依赖。
- 验证：165项关联后端、25项Vitest、Chrome390/1440px共6项及Ruff/类型/构建通过；临时数据与模拟AI，无真实质量或完整全量通过声明。
- 重启：worker须重启；API --reload自动加载否则重启；网页刷新，前端dev不用重启。普通Python与Anaconda完整路径命令、人工验收及新增上传文件见[交付记录](../docs/gcx/topics_reuse_2026_10_17.md)。旧上传副本/下载版未更新。
- 接收：zhy集成、xtc候选消费；M4正式章节/试卷约束不在此次修改中。知识点配额、跨批去重、预算及学科质量仍待后续，不宣称整个M2完成。接收与实际复验待本人填写。

<a id="h-20261017-fzk-001"></a>
## H-20261017-FZK-001：M3笔记标签与搜索整理

- 日期/实际实现者：2026-10-17，Codex在fzk会话辅助；C02/C08/C09、FR-09/10/11。分支codex/fzk-m3-note-tags，基线f789a6b；工作区未提交/未推送，Review/待接收，人工审阅未填写。
- 先提出[Note.tags与0013迁移契约](../docs/contracts.md#m3-note-tags-01)，再实现存储/标签校验/搜索筛选/冲突与备份兼容。接收人zhy（迁移、备份整合）、gcx（M2草稿兼容）、xtc（后续笔记消费）；不修改其他成员个人记录。
- 实际后端全量264通过/3个既有Windows权限前提失败，含14项新增M3；27Vitest、12Chrome集成、Ruff/类型/构建/迁移漂移通过，详见[fzk验收记录](../docs/fzk/note_tags_acceptance.md)。保留原uvloop修复并补Windows专用tzdata。独立附件ZIP仍待后续，不宣称全部M3完成。
- 重启：先安装requirements.lock，再停止旧worker，重启API完成0013迁移后启动worker、刷新前端。旧0012备份可恢复；新备份需0013程序。没有实际用户库测试或真实模型调用。
- 接收/复验：待成员本人填写；自动测试不替代人工签收或main合并。
<a id="h-20261017-fzk-002"></a>
## H-20261017-FZK-002：M3便携导出与笔记生命周期

2026-10-17，fzk会话Codex辅助；用户已明确“以上功能验收均成功”，对应上一轮标签功能，不扩展为本轮功能或团队集成验收。C01/C03/C07/C08/C09/C10，FR-10/11/12/14/37；Review/待接收，分支codex/fzk-m3-note-tags，基线f789a6b，按用户要求不commit/push/合并。

- 实现：全账户有效笔记/引用图片知识库ZIP及来源/hash清单；持久任务、重试/取消/租约迟到保护、来源撤回后拒绝旧包；删除确认与revision冲突；网络恢复/创建请求幂等；跨课程双链及保存保留归属。先定义[公共契约](../docs/contracts.md#m3-portable-notes-01)，实际结果和复验步骤见[fzk验收](../docs/fzk/m3_completion_audit.md)。
- 共享影响：新增0014_note_exports派生表；worker分派NOTE_EXPORT；账户备份排除此控制表/任务，manifest升级0014并兼容0012/0013。未改M1解析、M2模型调用或M4考试业务。zhy评审0013/0014及共享备份/worker；gcx复验报告草稿（旧POST可不传request_id），xtc后续按原Note/Citation消费。
- 实际验证：275后端通过/3个既有Windows权限前提失败（非新增M3）；27Vitest、17Chrome、Ruff/类型/构建/迁移漂移通过。新增后端10项导出生命周期与0013兼容案例，浏览器含M2→M3/平台回归，无真实模型调用。照片/数据均自制临时样例。
- 启动顺序：停止旧worker → API启动升级0014（既有预迁移备份）→ 启动worker → 刷新前端。新增包由worker生成；离线校验脚本scripts/verify_note_package.py。待本轮fzk人工验收、zhy集成和实机/跨浏览器/真实材料联调；不代签其他成员。

<a id="h-20261017-fzk-003"></a>
## H-20261017-FZK-003：M3图片上传与导出命名

2026-10-17，Codex辅助fzk；M3-IMAGE-NAMING-01，C05/C07/C09/C10、FR-14/37。先记录AGENTS、[契约](../docs/contracts.md#m3-image-naming-01)和本条意图后实施；同一codex/fzk-m3-note-tags，基线f789a6b，仍未提交/推送/合并，Review/待接收。

- 用户确认双链插入/改名后链接、ZIP校验、后端停止后未保存正文保留；未确认的删除/冲突等场景不代填人工验收。反馈缺少图片上传入口及UUID命名难管理。
- 修改：笔记编辑器复用M1上传接口，成功插图并预览；失败/上传中输入保留，401不自动重传。新ZIP下载名带账户时区日期时间，成员按课程/标题/图片名称分配唯一名称，转换实际相对链接；保留来源、UUID身份和hash校验。
- 兼容：NoteExport新增filename响应，无新表/迁移/依赖；已有包不改写，须重新导出使用新目录。API/worker均需加载新代码，前端刷新。
- 验证：12项相关后端、12项Chrome、27项Vitest、Ruff/构建通过；390/1440宽度截图已检查，含真实临时上传/worker打包/离线校验。无用户数据修改或真实AI调用；本轮没有重跑全部后端，上一轮3个Windows环境失败不据此宣称已解决。[详细证据与复测步骤](../docs/fzk/note_batch_images_acceptance.md)。
- 待办：fzk复验新入口/命名，zhy整合共享API/worker及此前0013/0014；实机/WebKit和真实材料联调仍待。不代签其他成员接收。

## M3-EDITOR-MATH-01（2026-10-18，fzk）

用户暂时搁置AI识别开发，本轮只优化Markdown编辑器。参考用户截图改为分组线性图标工具栏，保留中文悬浮说明/aria-label、键盘操作及触屏热区；不复制截图素材，不引入另一套图标体系。新增本地LaTeX公式编辑弹窗，行内/独立公式、常用模板/符号、即时预览与错误提示、选区插入和原公式修改；标准$...$/$$...$$保存，笔记预览真实渲染公式。渲染禁用可信HTML/外部资源，限制公式长度及宏展开，不改变UUID双链/图片/安全Markdown。保留撤销、草稿/冲突保护、分屏和专注；只有用户确认插入才修改正文。更新依赖许可与锁文件，覆盖390/1440布局、公式插入编辑撤销及安全回归；同步fzk文档，不提交推送，不继续AI识别功能开发。

## 2026-10-18 M3 图标工具栏与公式编辑器

M3-EDITOR-MATH-01 已在工作区实现。用户暂缓 AI 识别后续开发；此次只改 Markdown 编辑器、公式渲染、依赖与相关测试/文档。zhy 评审公共 Icon/NotePreview、精确依赖锁与许可生成钩子；fzk 按[五步复验](../docs/fzk/note_math_editor_acceptance.md)核对。无新迁移或 API，不改变 UUID 链接/图片授权/正文 revision；未提交推送，未代签其他成员。
