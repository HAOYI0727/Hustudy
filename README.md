# Hustudy

2026-10-17 M2-TOPICS-REUSE：新生成练习题逐题选择/校验本次所选知识点子集并显示名称；三种真实AI预览可显式复用同用户/课程/请求/来源/模型/当前提示词下的完整成功结果，无新任务或模型调用。保留确认后重新生成；变更或失效则拒绝复用，无依赖/迁移。[使用、验证与重启](docs/gcx/topics_reuse_2026_10_17.md)。

2026-10-17 M2报告容量修复：解除步骤8项/知识点依据3条等过小上限，改为学习步骤64项、知识点32项、每处依据64条等有界容量，完整保留内容并逐条核验，不靠截断掩盖假引用。报告v6，只改报告；重启worker后复测。[详情](docs/gcx/report_capacity_2026_10_17.md)。

2026-10-17 M2报告自测补救：模型漏自测依据时舍弃无引用原题，保留有依据题目，并基于已校验知识点/例题补足基础自测，页面和笔记明确标注；不猜引用、不增加模型调用。报告v5，重启worker、刷新页面。[说明](docs/gcx/selfcheck_completion_2026_10_17.md)。

2026-10-17 M2真实课件修复：学习报告纳入完整可提取正文（最多400段/24万字符），分批预览确认、持久进度与失败后显式续跑；候选最多128段/32000字符，报告/候选采用原文编号引用，编程选项保留运算符。AI宽屏双栏独立滚动，窄屏快捷跳转。需重启后端和worker、刷新网页，无新依赖/迁移。[使用与验收](docs/gcx/real_materials_2026_10_17.md)。

2026-10-17 M2学习报告：附加概念链接无效时移除并显示提示，不再丢弃整篇报告；必填结构与原文引用仍严格检查。结构错误显示“输出格式不符”，报告提示词v3，需重启worker、刷新页面。[说明](docs/gcx/report_structure_2026_10_17.md)。

2026-10-17 M2资料问答引用修复：由程序提供原文摘录编号，AI选择编号，程序取回原文，减少抄写差异导致的失败；原有引用、权限与确认校验保留。需重启worker，后端--reload自动加载，前端刷新即可。[说明](docs/gcx/qa_excerpts_2026_10_17.md)。

2026-10-17 M2引用反馈修复：AI返回内容但证据未通过原文检查时，显示“引用校验失败”；错误提示区分片段ID与摘录，练习提示词v3加强复制原文要求。保留严格校验、确认发送与失败不自动重试。重启worker，后端--reload自动加载，浏览器强制刷新；[详情](docs/gcx/citation_feedback_2026_10_17.md)。

## 2026-10-16 M2候选与基础完善（gcx）

AI学习新增「题目候选 · 待审阅」：单选/判断/简答，指定结构/同考点变式/自选弱项；预览设置与材料后确认生成，可查看答案/评分细则、来源和历史，导出作者审阅用JSON。报告和候选都有受自制样例约束的固定演示；问答/报告/候选可精确选择片段，课程问答有持久历史，模型错误区分余额、并发、频率等安全代码。

不再按轮换日期刻意分段，详见[当前M2状态与依赖](docs/gcx/m2_plan.md)、[验收](docs/gcx/candidate_acceptance.md)、[公开候选schema](docs/gcx/question_draft_schema.json)。无新迁移/依赖/环境，重启后端和worker即可加载。M4仍需映射正式蓝图章节并集成试卷，教师/真题事实标签和真人质量验收不冒称完成。手动上传见[累计清单](docs/gcx/changed_files_2026_10_16.md)。


## 2026-10-16 M2真实教学报告（gcx）

AI学习新增「章节学习报告 · 需确认」：选择资料/学习方式 → 来源预览与覆盖提示 → 明确确认 → 后台报告 → 目标/知识点/例题/自测/引用 → 可编辑笔记草稿，报告自动保存并提供最近20条历史。请重启后端和worker加载新代码；不需要新增迁移或安装依赖。Windows现有Python启动步骤见[环境指南](docs/setup_guide.md)，使用见[用户指南](docs/user_guide.md)。

成员现为gcx=M2、xtc=M4（含轮换时段互换），使用GitHub网页手动上传；旧分支/姓名描述按历史保留。模块关联回归45项、Vitest14项和Chrome2项通过；全量初次129通过/3项既有Windows权限相关失败，详情见[验收](docs/gcx/study_report_acceptance.md)。真实模型报告学科质量、WebKit/实机与M4候选仍待后续，不标全部M2/P0完成。


Hustudy 是面向大学生的本地优先课程学习工具，围绕“资料阅读 → 知识点讲解 → 笔记与引用 → 真题分析 → 模拟练习 → 错题复习”形成学习闭环。首版采用 React/Vite 前端、FastAPI 后端、SQLite 与本地文件存储，按共享基础层加四大业务模块协作推进。

## 当前版本

更新：2026-10-16。当前具备可演示的学习闭环；共享基础层 + M1 核心实现已通过自动验收，A01–A08 为 Review，A09/A10 正式集成交付为 Doing。其他模块仍有 P0 缺口，不代表完整初版或正式发布完成。

当前可运行流程：

```text
注册/登录 → 创建课程 → 上传资料 → 解析切片 → 搜索/阅读
→ Markdown 笔记与 Citation → 演示检索 / 确认发送的 GLM 课程问答
→ 真题导入/拆题 → 蓝图 → DRAFT 模拟卷
→ 审阅为 READY → 作答/评分 → 错题 → 复习任务
```

已完成的主要功能：

| 区域 | 当前能力 | 代码位置 |
|---|---|---|
| 共享基础层 | FastAPI/request_id、标准 JWT、课程整理与删除隔离、SQLite/Alembic 0001–0012、原子文件存储、完整账户备份/空账户恢复 | `backend/app/core`、`backend/app/routers/auth.py`、`courses.py` |
| M1 MaterialHub | 有界上传、hash 去重、不可变版本、独立 worker/租约/取消恢复/重试/幂等索引重建、四格式切片、中文 FTS5、分类/标签整理与版本筛选、原文关联笔记、人工补录确认/修订、图片改名/说明/标签查找与分页、后台课程资料ZIP/来源清单、PPTX/Word原格式与PDF原页阅读、独立兼容PDF、资料/笔记分页检索和删除撤权 | `backend/app/services`、`workers/materials.py`、`routers/documents.py`、`routers/assets.py` |
| M2 AI Study | 演示检索、GLM-4.7-Flash 课程问答、片段预览/逐次确认、结构化响应与引用校验；问答/报告/三模式候选/固定演示/精确片段/历史；真实质量与正式M4集成待验 | `backend/app/routers/ai.py`、`routers/remote_ai.py`、`schemas/remote_ai.py` |
| M3 NoteGraph | Markdown 安全预览、自动保存、revision 冲突、UUID 双链/反链、Citation 回源、图片嵌入/反链与解码校验 | `backend/app/routers/notes.py`、`frontend/src/components/knowledge.tsx` |
| M4 ExamPilot | 基础 Topic、拆题草稿/确认、蓝图、演示 DRAFT 试卷、审阅、作答与客观评分、错题复习；完整映射统计/真实三模式生成待补 | `backend/app/routers/exams.py`、`backend/app/models/exams.py` |
| 前端工作台 | Router/Query/Ant Design 基线、401原账户恢复保留草稿、统一视觉/图标/状态、电脑/iPad/手机布局、抽屉导航和可折叠目录 | `frontend/src/main.tsx`、`frontend/src/styles.css` |

最近验收分别记录，不能将不同日期的数量相加：

| 范围 | 已执行结果 | 证据 |
|---|---|---|
| 后端与共享检查（10-15） | 116项pytest、Ruff、迁移漂移、安全显示、PDF实际渲染通过；独立3.12亦有116项记录 | [测试报告](docs/test_report.md) |
| 前端（10-16） | 14项Vitest、TypeScript/构建、42项Chrome/WebKit完整回归（3.6分钟）通过 | [视觉与多端截图](docs/zhy/shared_platform/visual_polish_acceptance.md) |
| 本机容量/环境（10-15） | 10课程/200资料/1000笔记基线与同机干净源码重建通过；不是其他机器或所有复杂样本的成绩 | [实际范围与JSON](docs/zhy/materialhub/search_capacity_acceptance.md) |

当前状态以[队长任务表](collaboration/zhy/task_status.md)、[完成度核查](docs/zhy/completion_audit.md)为准，逐轮历史见[公共进度](docs/progress.md)。本次仅校正文档，没有重跑以上业务测试。

## 快速开始

推荐在网络可用的终端执行一次初始化：

```bash
# 进入已克隆的仓库根目录
./scripts/setup.sh
```

脚本会创建 `.venv`、按锁文件安装前后端依赖并生成 `.env`。前端 PDF.js 要求 Node >=22.13.0 或 >=24（本机实测 25.2.1），本地渲染检查需保留 npm 默认可选依赖。项目推荐 Python 3.12，本机既有服务使用 Python 3.11.15，独立 Python 3.12.13 锁依赖116项回归已有通过记录；需要指定解释器时执行：

```bash
PYTHON_BIN=python3.12 ./scripts/setup.sh
```

setup会为JWT空值或旧占位自动生成强随机密钥并保留有效配置。密钥仅保存在根目录 `.env` 并由后端读取，不要重复轮换；然后分别在两个终端启动：

```bash
# 终端一：后端 + 资料 worker
bash scripts/dev.sh
```

```bash
# 终端二：前端
npm run dev --prefix frontend
```

浏览器访问：

- 前端：`http://localhost:5173/`
- 后端健康检查：`http://127.0.0.1:8000/health`
- OpenAPI：`http://127.0.0.1:8000/docs`

后端依赖按 `backend/requirements.lock` 安装。PDF 用 PDF.js 直接按页阅读；PPTX/DOCX 直接本地原格式预览，无需等待转换。LibreOffice 仅用于“兼容预览（PDF）”和现有截图路径，缺失/失败时保留原格式与文本入口。当前使用本地打包的 PDF.js 按页阅读，可保存当前页图片并记录来源版本/页号；截图可从课程图片回到原页。若后端已在运行，可在新终端执行 `bash scripts/worker.sh` 启动资料处理。自制样例位于 `fixtures/materialhub_demo.md`。

课程图片可整理名称、说明和标签，并按元数据/标签/来源筛选与分页；改名保留原文件、UUID和来源。并发修改显示409冲突并保留本地输入；查找不识别图中文字。操作见 [docs/user_guide.md](docs/user_guide.md)，最新交接见 [handoff.md](collaboration/handoff.md)。

## 验证命令

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q
bash scripts/check.sh
npm run check --prefix frontend
npm run build --prefix frontend
# 浏览器测试使用8056/5178与临时数据；先按环境指南准备浏览器
npm run test:e2e --prefix frontend
```

浏览器验收建议依次检查：注册和课程创建、Markdown 上传与切片、正文/标题搜索、笔记双链与反链、Mock AI 引用、真题和蓝图、DRAFT 到 READY、作答提交、错题复习，以及两个账号之间的归属隔离。

## 四模块推进计划

### A：共享基础层 + M1 MaterialHub

负责认证课程、迁移、存储/任务、四格式解析、原格式与兼容阅读、版本/图片/来源、关键词分页检索和共享集成。标准JWT、原子存储、完整账户恢复及核心M1流程已有自动证据；下一步为复杂真实样本/实机矩阵、极限资源、成员评审/签收、集成发布和真实试用，不重复实现已通过的基础功能。

对外稳定提供 `DocumentVersion`、`ChunkRef`、`AssetRef`、`Citation`、`ProcessingJob`。其他模块不能直接读取原始文件或私自修改 M1 表结构。

### B：M2 AI Study

负责Provider/RAG、教学报告、结构化校验与预算。GLM-4.7-Flash课程问答已接入，必须先预览片段并逐次确认发送；问答、报告、结构化题目候选、固定演示、精确片段与持久历史已接入；下一步为M4正式蓝图集成、外部证据契约和人工质量验收。演示检索不代表真实理解，语义检索与费曼仍是P1。

只能消费 M1 已校验的 `Citation`/`ChunkRef`，不能上传文件、修改笔记正文或直接创建正式试卷。

### C：M3 NoteGraph

负责Markdown、自动保存/冲突、双链/反链、Citation和图片。现有安全预览、回源、图片嵌入、单笔记导出与共享账户备份适配已实现；下一步补笔记标签和独立知识库附件ZIP，不将完整账户恢复误列为尚未实现。

使用 M1 提供的有效来源，不自行解析资料，不改变原始版本，也不替用户确认考点或主观题最终得分。

### D：M4 ExamPilot

负责真题导入、拆题校正、Topic 映射、历史统计、蓝图、三种生成模式、审阅、作答、评分、错题与复习。下一步完善父子题/跨页引用、映射状态、统计快照、同考点变式/历史蓝图/薄弱项专项、题干 hash 去重、主观题 rubric、提交幂等和复习日历。

只能调用已校验的 M2 题目草稿，必须遵守 `DRAFT → REVIEWED → READY`，正式试卷需要保存生成时的资料和模型快照。

## 协作与文档入口

团队分工为：**zhy（A）共享基础层 + M1、gcx（B）M2 AI Study、fzk（C）M3 NoteGraph、xtc（D）M4 ExamPilot**。成员与模块映射由 [roles.md](collaboration/roles.md) 统一维护。

```text
collaboration/                    docs/
  README.md                         README.md
  handoff.md       # 实时交接        contracts.md / api.md / decisions.md
  workflow.md / task_board.md        progress.md / traceability.md
  project_handoff.md                 setup_guide.md / third_party.md
  zhy/                              zhy/
  xtc/           # 每人 progress     xtc/          # 每人 features
  fzk/                              fzk/          # 与 optimizations
  gcx/                              gcx/
```

个人进度在 `collaboration/<成员>/progress.md`，实现的功能与优化说明在 `docs/<成员>/features.md`、`optimizations.md`。同级公共文件继续维护统一接口、约束、操作与集成状态；个人说明引用公共契约，不另建一套。已有跨模块历史记录保留，不能将 AI 辅助的集成改动冒记为其他成员本人完成。

每次完成一个修改切片，在提交/PR 前：更新个人记录 → 在 [handoff.md](collaboration/handoff.md) 追加唯一交接 ID、修改范围、真实测试结果、风险与接收人 → 接收人记录复验 → 队长同步公共任务板、进度与追踪。影响下游的未完成接口和阻塞也要及时记录；“待接收”不等于“已验收”。完整规则见 [AGENTS.md 第 20 节](AGENTS.md#20-四人文档隔离与统一交接规则)。

个人入口：[zhy](collaboration/zhy/README.md)、[xtc](collaboration/xtc/README.md)、[fzk](collaboration/fzk/README.md)、[gcx](collaboration/gcx/README.md)。技术文档导航见 [docs/README.md](docs/README.md)。

2026-10-16队长核查：共享基础层 + M1核心自动验收通过，整体仍待正式评审与交付。[当前A01–A10任务表](collaboration/zhy/task_status.md)管理状态和后续依赖，[完成度核查](docs/zhy/completion_audit.md)列技术证据与缺口；[zhy文档](docs/zhy/README.md)按共享基础层、M1、跨模块集成及历史分类。公共契约/操作/全站进度与handoff保留根级，GLM问答记为队长辅助M2集成，不算M1独有功能。历史骨架Done、构建成功及自动测试均不能替代正式交付。

- [`AGENTS.md`](AGENTS.md)：项目开发规范、领域模型、API 契约和四模块边界。
- [`main_idea.md`](main_idea.md)：产品思路与学习闭环。
- [`Hustudy_requirements.md`](Hustudy_requirements.md)：需求基线入口。
- [`Hustudy_team_collaboration.md`](Hustudy_team_collaboration.md)：课程教案、团队协作和过程证据要求。
- [`collaboration/project_handoff.md`](collaboration/project_handoff.md)：合作者复现、验收和后续推进指南。
- [`collaboration/roles.md`](collaboration/roles.md)：A/B/C/D 职责与接口边界。
- [`collaboration/task_board.md`](collaboration/task_board.md)：任务状态和验收证据。
- [`collaboration/workflow.md`](collaboration/workflow.md)：分支、评审、契约变更和测试流程。
- [`collaboration/roadmap.md`](collaboration/roadmap.md)：P0 后续、P1/P2 和创新方向。
- [`docs/api.md`](docs/api.md)：已实现 API 概览。
- [`docs/contracts.md`](docs/contracts.md)：共享实体、引用和状态契约。
- [`docs/progress.md`](docs/progress.md)：真实进度、测试结果和未完成风险。
- [`docs/setup_guide.md`](docs/setup_guide.md)：环境安装与日常操作指南。

## 当前限制

P0仍需完成M2真实质量验收/教师与真题证据、M4正式候选接入、M3标签与独立知识库ZIP、M4完整拆题校正/映射统计/证据约束三模式生成，以及跨模块最终集成、实机/真人试用和正式发布。OCR、语义检索、费曼/间隔复习为P1。旧二进制`.ppt/.doc`需先另存为`.pptx/.docx`；直接预览不保证完整Office动画与所有复杂版式。扫描PDF可看原页并人工确认补录，不能声称已有OCR。

真实模型密钥只进后端读取的 `.env`。用户原件、数据库、依赖和构建产物不提交；`fixtures/`和文档证据仅使用自制/获授权资料。完整账户备份与课程资料包用途不同，恢复只到满足UUID/归属约束的空账户。
协作分支建议使用 `feature/m1-material`、`feature/m2-ai`、`feature/m3-note`、`feature/m4-exam` 和 `fix/<issue>`；跨模块字段先更新 `docs/contracts.md`，再修改代码和调用方。

## GitHub同步

当前用户使用GitHub网页手动上传，本地为源码副本，没有Git历史；本轮未上传或发布。先取得团队最新版本，再按[本轮变更清单](docs/gcx/changed_files_2026_10_16.md)上传源码、测试与文档，并注明删除文件和交接ID。早期SSH/分支操作留作历史参考，见[同步说明](collaboration/github_sync.md)。GitHub源代码同步不等于网站部署，课程要求的Gitee/Wiki证据仍需另行维护。

<details>
<summary>开发历史（旧状态按日期保留，当前结论以上文为准）</summary>

## 2026-10-13 集成更新

前端已按 `features/materials`、`features/ai`、`features/notes`、`features/exams` 拆分，共享 UI 位于 `components/workspace.tsx`。蓝图支持编辑题数/分值/时长；课程切换清空工作区旧状态，过期登录回到登录页。后端统一错误追踪编号，测试使用隔离临时库。本轮 pytest 为 6 passed，前端构建通过；Safari 已验证登录与蓝图动态重算。交接和下一轮优先级见 [集成记录](collaboration/integration_2026_10_13.md)。

2026-10-14 队长缺口分析与依赖顺序见 [M1 分析](docs/zhy/materialhub/materialhub_gap_analysis.md)，本轮交接见 [H-20261014-ZHY-001](collaboration/handoff.md#h-20261014-zhy-001)。

扫描 PDF 可在原页阅读点击“补录本页文字”：保存草稿 → 对照原页 → 核对确认 → 检索/引用。确认不会更改原始解析失败状态；修订与旧引用分开保存，撤回不自动回退。当前仅支持原始 PDF。

## 2026-10-14 最新任务管理验收

资料任务可取消和恢复，关键词索引可按选中版本幂等重建；租约保护防迟到结果覆盖，恢复不清零尝试预算，原文与引用不改。自动检查通过，完整Safari流程/附件备份/压力仍待补。具体判定见[本轮验收报告](docs/zhy/materialhub/acceptance_2026_10_14.md)，交接[004](collaboration/handoff.md#h-20261014-zhy-004)待成员接收。

## 2026-10-14 课程资料包与验收

在资料页展开“课程资料包”，后台生成各版本原件、可用预览、解析文本、确认人工来源、图片和来源清单，保留UUID与hash。源删除/撤回/文件损坏停止旧包下载；不是完整账户备份，当前不能恢复导入。40项自动检查通过；Safari实际3份资料/3版本包下载，374片段/377内容文件与整包hash验证通过。[验收及正式队长A01–A10关口](docs/zhy/materialhub/material_export_acceptance.md)保留完整备份/环境/压力/发布等待办。

## 2026-10-14 共享课程整理

课程总览支持创建时分类/标签、改名/描述/分类/标签整理、关键词与组合筛选/排序、可点标签和revision冲突对照。0009保留旧课程与资料/笔记UUID，改名不再清空未提交描述。43项自动检查通过；Safari创建/改名/刷新/双标签页冲突已验收。课程删除完整关联清理、资料/任务分页与完整恢复仍待补，详见[验收](docs/zhy/shared_platform/course_organization_acceptance.md)与[交接006](collaboration/handoff.md#h-20261014-zhy-006)。

## 最新基本功能验收（2026-10-14）

课程删除已补影响预览/名称确认/revision与同事务跨模块清理，保留其他笔记的失效来源，取消活跃任务，避免孤立笔记/复习与迟到结果。0010追加标记；最终47项测试及共享检查通过，Safari确认保护已观察，用户课程未删除。[公开测试报告](docs/test_report.md)、[基本功能与剩余关口](docs/zhy/shared_platform/basic_acceptance.md)。当前仍不是全部P0验收完成。

## 智谱真实课程问答（2026-10-14）

已接入GLM-4.7-Flash：后端密钥→课程片段预览→逐次确认→后台任务→JSON/原文引用校验→结果回源/笔记草稿。使用.venv/bin/python scripts/configure_zhipu.py隐藏输入配置，重启API与worker。默认演示不发送；真实调用仅发送确认的片段，保留/训练/删除政策细项未核实。

67项回归/共享检查通过，自制真实请求grounded/1引用/417tokens；Safari模式入口观察通过，完整正向浏览器闭环待补。[验收](docs/zhy/integration/zhipu_qa_acceptance.md)、[配置指南](docs/setup_guide.md)。真实章节报告、M4生成与完整P0仍未完成，密钥不提交Git/前端/文档。

2026-10-15共享层升级：标准HS256 JWT已启用，旧会话需重新登录；setup自动初始化后端强签名密钥并保留有效配置。文件/图片原子写入，低磁盘507；资料与全部处理记录可服务端筛选/分页，页外引用正常回源。最新96项回归/共享检查通过，完整恢复、前端基线与环境/性能/发布仍待补。

2026-10-15新增“备份与恢复”：后台生成包含资料/图片/笔记引用/AI/试卷作答/错题复习的完整账户ZIP，校验后恢复到新数据库的空账户，保持业务UUID/hash/关系。保留源对象的同库账户会拒绝UUID冲突，不覆盖数据；迁移0012。当前101项回归与共享检查通过，跨机器/Safari/压力及其余基线仍待验收。


## 2026-10-15 共享前端与当前验收

页面导航已接入React Router，地址记录课程和引用来源，支持刷新/前进后退及未保存确认；TanStack Query统一GET的会话隔离/去重/写入失效，变更不自动重试。登录过期弹出原账户登录框，保留原笔记和资料整理草稿。Ant Design主题沿用公共视觉，工作区按需加载，当前主包485.85KB。

最新共享检查101项后端、10项Vitest、迁移/显示安全/PDF实渲染/类型/构建通过；隔离Chrome/WebKit共8项浏览器闭环通过，包含真实API上传检索与完整备份下载hash。Python3.12.13独立环境101项通过，现有服务解释器未替换。命令和限制见[环境指南](docs/setup_guide.md)、[zhy前端验收](docs/zhy/shared_platform/web_base_acceptance.md)。LibreOffice成功转换、完整业务矩阵、容量/性能、人类评审/Gitee/发布及真实用户反馈仍待完成，不能称全部P0完成。

## 2026-10-15 PDF预览修复

PPTX/DOCX需要本机LibreOffice转PDF；本机已安装并验证真实转换，阅读区新增环境检查和原版本“重试预览”。Safari因新Map方法缺失而渲染失败的问题已改用同版本PDF.js legacy解决；PPTX保留隐藏页并核对页号，旧错位截图不会被静默重新指向。

最新110项后端、10项Vitest、14项Chrome/WebKit闭环及共享检查通过；独立Python3.12相关17项补验通过。原课件旧缓存已146页/146张一致，当前Safari新标签页会话过期需原账户重新登录后查看。[验收与剩余限制](docs/zhy/materialhub/preview_recovery_acceptance.md)。

### 队长共享层与M1当前验收

知识查找现支持资料/笔记独立服务端分页和原文命中摘要，不再截断前50个结果；PPTX嵌套组合文字/表格提取已补齐。新增双引擎补录/撤回/来源回跳/课程删除闭环，10课程/200文档/1000笔记的本机容量读性能已测，Python3.12干净源码重建通过。具体范围、实际数值和限制见[zhy验收](docs/zhy/materialhub/search_capacity_acceptance.md)。

本地完整自动验收：`HUSTUDY_E2E_CHROME_CHANNEL=chrome bash scripts/accept_captain.sh`（需已准备浏览器，使用隔离临时数据）。功能自动通过不代表Gitee正式合并、成员签收或全站其他模块完成。

### PPT / PDF / Word 按原格式预览

选中资料后，`.pptx` 点“PPT 预览”，`.docx` 点“Word 预览”，`.pdf` 点“PDF 预览”。Office直接在本地浏览器读取原件，支持基础样式/表格/图片、翻页与缩放，PPT另有演示模式；不需等待PDF转换。转换路径另叫“兼容预览（PDF）”，用于静态版式核对和截图；文本引用保持原契约。

开发/构建会自动生成隔离运行时（npm run build:office）；不上传文档给外部服务。首版不支持旧.ppt/.doc或完整Office动画/编辑，复杂排版有差异。最新14Vitest、26项Chrome/WebKit闭环通过，具体说明见[zhy原格式验收](docs/zhy/materialhub/native_preview_acceptance.md)。


全站多屏布局：电脑使用紧凑侧栏；平板/手机使用吸顶导航菜单，手机资料与笔记目录可折叠。统一字号/卡片密度并保留触控热区、输入可读性与文档独立缩放。40项双引擎/14Vitest/类型构建通过，具体范围与实机待验边界见[响应式验收](docs/zhy/shared_platform/responsive_layout_acceptance.md)。


2026-10-16视觉细化：统一主色、文字层级、按钮/选中/禁用/焦点与语义状态，增加工作区/账户标识、功能图标与可见表单标签；保留电脑/iPad/手机布局及触控尺寸。最新42项双引擎、14Vitest、类型与构建通过，截图与实际边界见[视觉验收](docs/zhy/shared_platform/visual_polish_acceptance.md)。

</details>

### M2结构化响应诊断补充（2026-10-16）

候选真实测试反馈：约400字仍出现结构化输出失败，不能归因为资料过长。候选提示词v2增加完整字段示例；JSON语法错误与字段错误分开显示，只展示白名单字段路径和固定原因，不保留或输出模型原文。重启worker后重新预览确认才使用更新，旧失败记录不改写。模拟HTTP回归76 passed/12.34秒；未调用真实模型，原始失败的具体字段仍待新请求验证。

### M2基础完成状态纠正（2026-10-16）

M2基础功能尚未全部实现和验收。报告标签缺少逐项编辑交互，教师/真题标签依据未接入；真实候选修正复验、真实质量及M4正式组卷对接待验/依赖。当前优先补基础缺口，不以长课件增强或界面美化代替基础交付。逐项依据与下一步见docs/gcx/m2_plan.md最新核查。

### M2基础补齐：标签审阅与教学结构（2026-10-16）

新增重点/难点/考点建议逐项增删改及理由审阅，显式转为可编辑笔记，保留原始AI建议/身份与引用；切换模式和保存失败保留草稿。报告新增知识点分层、报告内概念关系、难点突破步骤及复习建议，兼容旧结果，固定报告演示可离线复验。后端87、前端17、Chrome桌面/窄屏4项通过，未调用真实模型。真实质量、教师/真题证据和M4正式组卷仍待验/依赖。[验收与使用](docs/gcx/basic_acceptance.md)。

M2-LABEL-REVIEW-01用户试用反馈（2026-10-16）：用户表示本轮新增功能尝试后没有问题；记录为本轮人工试用反馈，不代表真实AI质量或全部M2通过。详见docs/gcx/basic_acceptance.md。

M2页面入口现为“资料原文检索、资料问答、学习报告、练习题生成”，入口下显示用途；发送确认在预览区域，结果保留审阅提示。此次仅前端显示调整，刷新浏览器即可，不需重启后端或worker。

手动上传准备：按实际本地目录整理了[上传指南](docs/gcx/upload_guide.md)、[M2累计文件清单](docs/gcx/upload_files_m2.txt)和[完整源码清单](docs/gcx/upload_files_full.txt)。这些是路径清单，不是与远端的差异；排除.env、本机运行数据、依赖/构建/缓存。

### 2026-10-17 M2完整剩余范围审计

此前“主要只剩验收”的判断不完整。模型平台切换尚未实现；分批处理、步骤计数、失败续跑、缓存隔离、逐题Topic配额等仍有需求缺口。全部剩余开发、跨模块依赖、真实验收及P1范围见[完整审计](docs/gcx/m2_remaining_audit_2026_10_17.md)。旧成果已由用户报告上传合并并完成本地下载复验，不代表这些新待办已完成。本次只改文档，不需重启服务。

### 当前模型：GLM-5.3-Flash（2026-10-17）

原Hustudy-main已按用户要求切换默认及本机配置为glm-5.3-flash，保留glm-4.7-flash配置兼容。新模型必须开启思考，已适配JSON调用；原密钥保留。需重启后端与worker，前端刷新并重新预览确认。104项后端/4项Chrome模拟验证通过，未调用真实模型，不保证免费/额度/真实生成质量。其他下载副本和GitHub尚未同步。[变化及重启命令](docs/gcx/model_switch_2026_10_17.md)。
