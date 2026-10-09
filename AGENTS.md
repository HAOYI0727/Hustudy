# Hustudy：Codex 开发规范

本文件用于约束在此目录及子目录中的开发工作。先阅读 `main_idea.md`、`Hustudy_requirements.md` 与 `Hustudy_team_collaboration.md`；本版新增功能以 v0.4 四模块协作基线为准。用户明确的新要求优先于文档；需求发生变化时同步更新相关基线，不能悄悄扩大范围。

## 1. 项目定位与首版目标

Hustudy 是面向大学生的工具类产品，核心为PPTX/PDF/DOCX 等课程文档阅读、结构化 AI 讲解、个人知识库、Markdown 笔记与资料/图片交叉引用、历年真题分析与期末模拟题生成。沿用此前 StudyLens 的学习闭环，产品名称统一为 Hustudy。

首版完整流程：创建课程 → 上传 PPTX/PDF/DOCX/Markdown → 阅读与笔记/图片引用 → AI 知识点讲解 → 上传历年真题并校正拆题 → 确认考点与课件映射 → 查看历史分布和资料缺口 → 确认蓝图 → 生成模拟卷并审阅 → 作答 → 错题回源 → 补弱复习。

模拟题拟合是匹配用户设置的章节、题型、分值、数量和难度标签，不是预测教师真题。难度、主观题评分与费曼报告必须标注为辅助估计。

## 2. 范围与执行原则

1. 首先交付 `Hustudy_requirements.md` 中的 P0。DOCX、图片引用、真题拆分校正、考点映射与历史统计属于 P0。P1 包括语义检索、跨资料自动对齐、扫描试卷 OCR、费曼和间隔复习；考研考公外部信息聚合、语音和多人协同为 P2。
2. 4 人是开发团队规模，不能据此默认需要多人实时协同编辑。
3. 采用本地优先的 Web 单体：浏览器 + FastAPI + 本地 SQLite/文件存储。配置真实远程模型时，仅在用户确认后发送选定资料片段；不宣称全离线运行真实大模型。
4. 先定义共享领域实体、接口和状态，再开发页面。不得拼接几个 GitHub 仓库形成相互独立的用户系统与数据库。
5. 借鉴开源功能设计；若引入源码或资源，先核对对应版本许可证、保留署名和要求的声明，记录到 `docs/third_party.md`。未核实的仓库地址或许可证不得写成已确认事实。
6. 日常开发不引入微服务、Redis、复杂消息队列、Kubernetes 或图数据库。复杂处理用数据库任务记录 + 单独 worker 进程，避免请求超时。
7. 文档、笔记、试卷、答案、检索过滤与文件下载均检查用户归属。权限控制在服务端执行。
8. 所有外部模型响应经过 schema 校验和业务校验。长文本可作为字段值；结构字段、引用和题目选项不能只靠正则从聊天文本猜测。
9. 测试必须覆盖业务风险，不要求每个无逻辑 CRUD 都写同样的测试。代码、测试、迁移、接口文档和需求追踪保持一致。
10. 禁止虚构用户访谈、人工核实、性能数据、满意度、测试结果或 AI 使用日志。

## 3. 技术基线

以下是实施选型，不代表已验证所有版本组合。初始化时检查运行环境与官方文档，锁定依赖版本并提交锁文件。

| 层 | 首版选择 | 约束 |
|---|---|---|
| 后端 | Python 3.12、FastAPI、Pydantic 2、SQLAlchemy 2、Alembic | 使用同步 SQLAlchemy；耗时任务放 worker，避免阻塞异步事件循环 |
| 存储 | SQLite、FTS5、本地文件 | 启用外键和 WAL、设置忙等待；记录中文分词版本；迁移时校验 FTS5 可用 |
| 解析 | python-pptx、pypdf、python-docx、Markdown 解析器 | 按正文顺序提取 DOCX 段落/表格；不把 PPTX 或 DOCX 解析器当排版渲染器 |
| PPTX 预览 | LibreOffice 无头转换为 PDF + PDF.js | worker 隔离转换、限制超时；失败时显示结构化文本视图和状态说明 |
| 搜索 | jieba 等中文分词 + FTS5 | 原文与检索 token 字段分离，引用偏移只针对原文 |
| 前端 | React、TypeScript、Vite、Ant Design、React Router、TanStack Query | 数据请求统一；React 渲染中不直接执行生成任务 |
| 笔记 | Markdown 编辑器、react-markdown、清洗器 | 禁用未经清洗的 HTML；引用是结构化对象 |
| 模型 | LLMProvider：Mock 与可配置真实 Provider | 具体名称、端点、密钥通过配置；密钥只存后端环境 |
| 测试 | pytest、httpx、Vitest、Playwright、Ruff、TypeScript 检查 | 单元、API、闭环 E2E；不用真实网络测试替代确定性测试 |
| P1 | 选一种嵌入索引适配器、ECharts/React Flow 按需引入 | 不能同时维护 Chroma 与 FAISS；未启用语义搜索时不得声称已启用 |

真实模型适配器开发前核对所选服务的当前官方接口。Mock 只提供固定演示资料对应的确定性结果；未知输入返回能力限制，不能伪装真实理解。

## 4. 项目目录

```text
Hustudy/
  AGENTS.md
  main_idea.md
  Hustudy_requirements.md
  backend/
    app/
      core/          # 配置、安全、异常、数据库
      models/        # SQLAlchemy 实体
      schemas/       # 请求、响应、模型输出结构
      repositories/  # 带归属过滤的数据访问
      services/      # 课程、资料、笔记、AI、试卷、复习
      routers/       # HTTP 入口
      ai/            # providers、prompts、retrieval、validators
      workers/       # 解析、预览、模型生成任务
    migrations/
    tests/
  frontend/src/
    pages/           # 登录、课程、资料、阅读、笔记、试卷、错题、复习
    features/        # 按业务域组织组件与交互
    api/             # 由 OpenAPI 生成/维护的客户端
    types/
  scripts/           # 初始化、演示种子、备份恢复、启动
  data/              # 运行数据；不提交用户文件或密钥
  fixtures/          # 自制/获授权的小型测试资料
  docs/              # API、设计、决策、测试、追踪、AI记录、用户指南
```

数据库迁移由成员 A 统一整合；其他成员先提出 schema 变更。业务命名统一 `user_id` 为所有者，不混用含义不明的 `flag` 或多套软删除规则。

## 5. 领域模型与引用契约

核心实体：User、Course、Document、DocumentVersion、DocumentChunk、ProcessingJob、Note、NoteLink、Asset、AssetReference、Citation、AIResult、Topic、TopicSource、PastPaper、PastQuestion、QuestionTopicMapping、ExamAnalysisReport、ExamBlueprint、ExamPaper、Question、ExamAttempt、AttemptAnswer、Mistake、ReviewTask、Feedback。

所有用户业务对象都有 `id`、`user_id`、`created_at`、`updated_at`；数据库时间存 UTC，复习日历按账户时区计算，默认 Asia/Shanghai。响应使用带时区 ISO 8601。UUID 用于持久对象；数值排序字段不能充当永久 ID。

版本和引用要求：

- Document 是资料身份；DocumentVersion 是一次不可变内容导入。覆盖上传必须新增版本。
- Chunk 属于版本，保存 `locator_type`（slide/page/heading/docx_block）、`locator_value`、正文与原文偏移；Markdown 偏移明确使用 Unicode 字符序号、从 0 开始、左闭右开。
- Citation 同时存版本 ID、chunk ID、定位、原文摘录和摘录 hash；服务器验证摘录确实存在。后续更新资料不能静默把旧引用指向新内容。
- 笔记之间使用 `[[note:<uuid>|显示名]]`。资料引用保存结构化 Citation，通过编辑器插入；禁止仅靠名称拼接定位。
- NoteLink 保存 source_note_id、target_note_id 和显示标签。反向链接从关系计算，不重复保存两套不一致列表。
- 图片采用 Asset 和 AssetReference，保存 MIME、hash、大小、alt/caption、版本来源与归属；引用用 UUID。图片删除后所有位置显示失效，不能破坏笔记正文。图中文字只在 OCR/人工转录明确可用时进入正文检索。
- 删除笔记后，现有引用显示“目标已删除”；删除文档撤销文件读取和检索资格，只保留删除标记及引用元数据，相关引用显示不可用。不得继续发送被删资料给模型。

引用示例（ID 为示例占位符）：

```json
{
  "version_id": "<uuid>",
  "chunk_id": "<uuid>",
  "locator": {"type": "slide", "value": 12},
  "quote": "摘录的原文",
  "availability": "active"
}
```

## 6. 核心状态与异常处理

ProcessingJob：QUEUED → RUNNING → SUCCEEDED / FAILED / CANCELLED。解析任务失败可重试；worker 重启后将过期运行租约恢复为待重试，设置最大尝试次数。任务类型区分 PARSE、PREVIEW、INDEX、AI_ANALYSIS、GENERATE_PAPER。

DocumentVersion 保存 `parse_status`、`preview_status`、`index_status`，不要用单一 READY 掩盖其中某项失败。只有解析和关键词索引完成后可检索；预览失败可用文本阅读；向量索引未完成不影响关键词检索。

Note 用 `revision` 乐观锁保存；冲突返回 409，显示本地内容与服务器版本，不能静默覆盖。

ExamPaper：DRAFT → REVIEWED → READY → ARCHIVED。生成的是 DRAFT；用户审阅并确认后才能开始模拟考试。试卷及题目快照不可因重生成而改变已有作答。

ExamAttempt：IN_PROGRESS → SUBMITTED → SCORED。首次提交后不可覆盖；重复提交相同请求返回已有结果。截止时间由服务端校验；答题中每次保存都能恢复。

## 7. API 契约

统一前缀 `/api/v1`；统一错误形态 `error.code/message/details/request_id`，保留正确 HTTP 状态码。创建资源用 201，任务入队用 202，参数校验用 422，归属不可访问按统一策略返回 404。

| 域 | 主要接口 |
|---|---|
| 用户与课程 | POST /auth/register、POST /auth/login、GET /auth/me；/courses 的 CRUD |
| 资料 | POST /courses/{id}/documents；GET /documents/{id}/versions；GET /jobs/{id}；DELETE /documents/{id} |
| 阅读 | GET /versions/{id}/chunks；GET /versions/{id}/preview；GET /versions/{id}/original |
| 搜索 | GET /courses/{id}/search?q=…；结果包含定位、版本和后端评分 |
| 笔记 | /notes 的 CRUD；GET /notes/{id}/backlinks；GET /notes/{id}/citations |
| AI | POST /courses/{id}/ai-queries；POST /versions/{id}/analyses；GET /ai-results/{id} |
| 试卷 | POST /exam-blueprints；POST /exam-blueprints/{id}/generate；GET /exam-papers/{id}；POST /exam-papers/{id}/review |
| 作答 | POST /exam-papers/{id}/attempts；PUT /attempts/{id}/answers/{question_id}；POST /attempts/{id}/submit |
| 复习 | GET /mistakes；POST /review-tasks；GET /review-tasks/today；POST /review-tasks/{id}/complete |
| 备份反馈 | POST /backups；POST /backups/restore；POST /feedback |

考生接口只返回题干、选项与分值。答案、rubric 和解析在提交后由单独接口返回，不能在前端藏一个含标准答案的完整 JSON。

## 8. AI、检索与拟卷规则

P0 使用中文分词关键词检索，并以可校正的 Topic 列表统一真题与课件术语；P1 才引入向量搜索。混合检索采用 RRF 等可解释排序，不直接混合未归一化的 cosine 与 BM25 分数。排序分数不是回答正确率，不能展示成“可信度 98%”。

输入资料视为待分析数据，文档内指令不得提升为系统指令。先按归属、课程、版本有效性过滤，再检索并检查引用。返回 `grounded`、`insufficient_evidence` 或 `provider_error`，证据不足时不生成假引用。

模拟卷生成分为四步：

1. 校验蓝图：每个题型、分值、题数、章节覆盖；总分等于题型项目 `count * points` 总和。章节分配必须使用整数题数并与总题数一致；难度是标签，不是难度测量。
2. 逐题生成：题干、选项、答案/rubric、解析、章节、难度标签、引用、来源是否曾为 AI 草稿。
3. 校验与去重：引用真实、答案合法、分值精确、题数满足；同卷标准化题干 hash 去重。P1 再增加语义去重。预算内最多两轮修复。
4. 失败显式返回不足原因与可调整项，不能无声降低数量或伪造证据。成功试卷仍要求用户审阅。

客观题按规则判分；主观题保存 rubric 和 AI 建议分，允许用户覆盖并保留原建议。首次作答才算错题事件；网络重试不能重复增加错误次数。相关错题创建复习任务需幂等。

Mock 模式默认演示资料，页面固定显示“演示模型”。远程模式用户拒绝发送时仍可阅读、记笔记、检索和查看已有结果，不执行新模型任务。

## 9. 四人协作约定（概要）

| 代号 | 主责 | 接口交接 |
|---|---|---|
| A 队长 | 共享基础层 + M1 MaterialHub：认证课程、SQLite、迁移、文件存储、四格式解析、索引与集成 | 提供 DocumentVersion/Chunk/Citation/Asset/Job 契约，并维护 `main`/`develop` |
| B | M2 AI Study：Provider、RAG、知识点教学报告、重点难点考点、AI 结果校验 | 消费 M1 的 Citation，只输出结构化 StudyReport/AIResult/QuestionDraft |
| C | M3 NoteGraph：Markdown、图片、标签、双链、反链、回源、导出与冲突处理 | 使用 M1 Citation，AI 内容以可审阅草稿方式插入 |
| D | M4 ExamPilot：真题拆分映射、历史统计、蓝图、模拟题、作答、错题复习与试用 | 调用已校验的 M2 草稿，使用 M1 授权和 M3 回源跳转 |

每人维护本模块 API 与测试，并互相评审。不能让 D 独自承担所有测试。共享模型/schema 先评审；使用独立分支或工作目录，避免同时覆盖相同文件。人类团队协作不意味着自动启动多个 AI 子代理。

## 10. Codex 实施流程与完成定义

收到明确“实现第 N 阶段”时，只完成该阶段及必要依赖；收到“完成初版”时按阶段持续推进到全部 P0，不能停在计划。

阶段顺序：0 基线与契约 → 1 认证课程 → 2 四格式解析阅读 → 3 笔记图片双链 → 4 AI 分析检索 → 4A 真题拆分/映射/统计 → 5 拟卷作答 → 6 错题复习备份 → 7 测试交付。P1 在 P0 验收后推进。

每轮：检查现有代码和用户改动 → 将任务对应到需求 ID → 完成最小闭环 → 运行有针对性的测试、类型检查与构建 → 更新 `docs/traceability.md` 和 `docs/progress.md` → 报告实际结果和限制。禁止把测试未执行写成通过。

必须验证：

- PPTX 原文定位、DOCX 段落/表格顺序与预览失败降级；非法文件、扫描 PDF 无文本；图片归属、删除失效与导出恢复。
- 笔记引用、重命名、并发冲突、目标删除、版本更新。
- 另一用户不能访问任何文档、检索结果、笔记、试卷或预览文件。
- AI 输出坏 JSON、假引用、超时、证据不足、Mock/真实模式标记。
- 真题拆分、跨页题目、未知分值与无官方答案、考点映射校正、重复试卷去重、已审阅样本统计。
- 蓝图不满足约束、试卷数量分值、双来源与真题改写检测、答案不提前泄露、重复提交与中断恢复。
- 错题去重、复习时区、备份恢复完整性。

具体量化指标遵循 `Hustudy_requirements.md`；所有指标是验收目标，未经测量不能填成成果。

## 11. 课程文档与个人提交

当前附件要求的是个人需求分析实验。4 人项目可共享项目背景和技术契约，但个人提交必须由本人审阅，记录本人实际使用的提示词、采纳/修改/否决、人工核实结果。不能伪造其他成员工作或将小组计划冒充已完成实验。

`Hustudy_requirements.md` 是需求基线 v1.0；人工核实项和运行结果必须按实际证据更新，不得为了凑评分删除“未核实/未实现”的状态。教案节点、Gitee Wiki 目录、甘特图和发布维护要求见 `Hustudy_team_collaboration.md`。

## 13. 四大核心模块与共享基础层

Hustudy 采用“共享基础层 + 四个业务模块”的协作结构。四名成员各自负责一个业务模块；队长额外负责共享基础层、接口契约、数据库迁移、集成分支和最终验收。业务模块之间只能通过共享 schema、service interface 和事件契约交互，不能直接读取其他模块的数据库表。

```text
                    ┌──────────────────────────┐
                    │  Shared Platform Layer    │
                    │  Auth / Course / DB / Job │
                    │  Storage / API / Test     │
                    └───────────┬──────────────┘
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼                 ▼
       Module 1            Module 2            Module 3            Module 4
       MaterialHub         AI Study             NoteGraph            ExamPilot
       资料与知识库          AI学习分析            笔记与交叉引用         真题与复习
```

### Module 1：MaterialHub 资料库与知识索引

负责 PPTX/PDF/DOCX/Markdown/图片的上传、分类、版本、解析、预览、切片、关键词检索、来源定位和删除失效。

- 允许修改：`documents`、`document_versions`、`document_chunks`、`assets`、`processing_jobs` 及对应 repository/service/router/test；
- 对外提供：`DocumentVersion`、`ChunkRef`、`AssetRef`、`Citation`、`ProcessingJob`；
- 不负责：AI 解释文本、真题考点判断、笔记正文和试卷生成；
- 必须通过：三种文档解析、DOCX block 顺序、PPTX 预览降级、图片类型校验、跨用户下载隔离。

### Module 2：AI Study AI学习与知识点分析

负责 Mock/真实 LLM Provider、提示词版本、RAG 上下文选择、章节总结、重点难点考点报告、例子、自测题、回答引用校验和任务预算。

- 允许修改：`ai/`、`study_reports`、`ai_results`、AI schemas/services/routers/tests；
- 依赖：Module 1 只读 `Citation`、`ChunkRef` 和有效版本查询；
- 不负责：直接上传文件、修改用户笔记、创建正式试卷或写入作答记录；
- 必须通过：`grounded`、`insufficient_evidence`、`provider_error` 三种路径，坏 JSON、超时、假引用和发送确认。

### Module 3：NoteGraph 笔记与交叉引用

负责 Markdown 编辑、标签、自动保存、revision 冲突、双链、反链、图片嵌入、资料 Citation 插入、回源、知识库导出和备份交互。

- 允许修改：`notes`、`note_links`、`citations`、`asset_references`、笔记页面/组件/测试；
- 依赖：Module 1 提供有效来源，不自行解析文件；Module 2 的 AI 草稿必须作为可审阅草稿插入；
- 不负责：改变原始资料版本、替用户确认真题考点、给主观题自动定最终分；
- 必须通过：重命名后链接有效、目标删除显示失效、并发保存返回 409、导出附件 hash 一致。

### Module 4：ExamPilot 真题、模拟题与复习

负责历年真题导入元数据、拆题草稿、人工校正、Topic 映射、历史统计、资料缺口、蓝图、三种生成模式、作答、判分、错题和复习任务。

- 允许修改：`past_papers`、`past_questions`、`topics`、`topic_mappings`、`exam_*`、`mistakes`、`review_tasks` 及对应前端/测试；
- 依赖：Module 1 的来源和文件；Module 2 的结构化题目草稿；Module 3 的回源跳转；
- 不负责：重新上传或修改资料、直接调用未校验的模型文本、绕过试卷 DRAFT/REVIEWED/READY 状态；
- 必须通过：父子题不重复计分、未知年份/分值不补造、映射校正后可重算、正式试卷保留来源快照。

## 14. 队长负责的共享基础层

队长先搭建并维护以下稳定骨架，其他成员在骨架上开发，不重复创建第二套用户和数据库：

1. monorepo 目录、README、`.env.example`、锁文件和本地启动脚本；
2. FastAPI app factory、配置、日志、CORS、统一响应、错误码和 request_id；
3. SQLite/SQLAlchemy/Alembic、基础 User/Course、外键、WAL、UTC 时间和 `user_id` 过滤；
4. JWT 登录、测试用户 fixture、文件存储抽象和统一 ProcessingJob；
5. 前端路由、布局、API client、错误/加载/空状态组件；
6. CI 或本地检查入口：后端测试、前端类型检查、构建、Ruff 和迁移检查；
7. `docs/api.md`、`docs/decisions.md`、`docs/progress.md`、`docs/traceability.md` 初始版本。

队长不得在没有评审的情况下替业务成员重写模块内部实现。共享层的修改必须先更新接口契约，再通知受影响模块。

## 15. 分支、提交与合并规则

- 分支：`main` 只保留可演示版本；`develop` 用于集成；个人分支使用 `feature/m1-upload`、`feature/m2-rag`、`feature/m3-notes`、`feature/m4-exam`、`fix/<issue>`；
- 提交：使用 `feat(module): ...`、`fix(module): ...`、`test(module): ...`、`docs: ...`；一个提交尽量只解决一个可审阅问题；
- 合并前：必须说明需求 ID、修改文件、迁移变化、测试命令、未完成风险；
- 禁止：直接向 `main` 推送未测试代码、覆盖别人成员未提交的修改、在业务模块中偷偷修改共享表结构；
- 数据库变更：先在 `docs/contracts.md` 写字段和迁移意图，由队长合并迁移；
- API 变更：先更新 Pydantic schema/OpenAPI 示例和调用方，再修改 service/router；
- 冲突解决：以共享契约为准，保留两边业务行为的测试；不能用“最后一次保存”静默解决语义冲突。

## 16. Codex 模块开发协议

每次向 Codex 提交任务必须明确模块编号、需求 ID、允许修改目录和验收命令。Codex 必须：

1. 阅读 `AGENTS.md`、`main_idea.md`、`Hustudy_requirements.md`、`Hustudy_team_collaboration.md`；
2. 说明当前模块的输入、输出、依赖和不修改的目录；
3. 先检查 git diff 和已有用户改动；
4. 只完成一个可验收垂直切片，代码、测试、文档一起提交；
5. 若需要跨模块变更，先提出契约变更，不直接实现隐式耦合；
6. 运行模块测试和必要的集成测试，报告实际输出；
7. 更新进度和追踪矩阵，不把计划写成完成。

推荐任务格式：

```text
模块：M2 AI Study
任务：实现 FR-17 课程范围内带来源问答
允许修改：backend/app/ai、backend/app/services/ai、对应 schemas/tests、docs/api.md
依赖：M1 已提供有效 ChunkRef/Citation 查询
禁止修改：M1 解析器、M3 笔记表、M4 试卷表
验收：TC-10、TC-11、TC-12；pytest ...；前端构建（如涉及）
```

## 17. 集成顺序与 Definition of Done

集成顺序固定为：共享基础层 → M1 资料上传/解析 → M3 笔记与引用 → M2 AI 分析 → M4 真题与试卷 → 全链路验收。M2 和 M4 可以并行设计 schema，但 M4 只有在 M1 的 Citation 契约稳定后才能接入真实资料。

一个任务只有同时满足以下条件才算完成：需求 ID 可追踪；输入输出和异常已定义；代码通过对应测试；没有破坏其他模块；数据库变更有迁移；API 或交互有文档；真实测试结果已记录；未完成项和风险已公开。

## 18. 课程教案对齐规则

教案要求最多 4 人分组，使用 Gitee 记录软件过程和管理；个人需求分析/设计报告与小组项目交付分开计算。Hustudy 必须把课程证据当作项目交付物，而不是开发结束后补写。

| 教学关口 | 教案要求 | Hustudy 必须形成的证据 | 负责人 |
|---|---|---|---|
| 第一次课 | 头脑风暴、mindmap、会议记录/照片、NABCD、Gitee 立项 | `docs/01_project_kickoff.md`、原始会议照片、思维导图、Gitee Wiki 首页 | 队长组织，四人参加 |
| 第二次课 | 智能需求获取、需求评审 | 需求来源表、用户场景、需求评审记录、AI 协作提示词 | 队长 + Module 负责人 |
| 第三次课前 | 提交需求分析报告；第一次师生沟通 | `Hustudy_requirements.md`、AI 协作/人工核实记录、需求追踪矩阵；沟通意见和变更记录 | 队长提交，四人审阅 |
| 第四次课 | 智能化软件开发方法 | Codex/AI 使用规范、任务拆分、分支与评审记录 | 队长 |
| 第五次课 | 架构、数据结构、算法；提交设计报告；迁入迁出和代码管理；提交源代码及可执行程序 | 架构图、ER 图、API、状态机、算法说明、Gitee 提交记录、可运行版本 | 队长集成，四模块负责 |
| 第六次课 | 软件质量与智能测试 | 测试策略、测试用例、覆盖异常/性能/权限的记录 | 各模块测试，队长汇总 |
| 第七次课 | 功能/性能测试、测试报告、用户说明、公开发布、用户反馈 | `docs/test_report.md`、`docs/user_guide.md`、Gitee Pages/发布地址、匿名反馈与分析 | D 负责试用，队长发布 |
| 第八次课 | 每组 8 分钟公开讲解与展示，全程记录 | 汇报 PPT、演示脚本、录屏/照片、每名成员分工体会 | 四人共同准备 |

评分对齐：需求分析 20%，原型/概要设计/详细设计 35%，编码与测试 30%，功能创意 10%，真实用户反馈 5%；项目成绩占综合成绩 95%，考勤占 5%。不得用产品功能数量替代过程证据。教案要求每人领取约 5–10 个粒度适中的任务；当前四模块各安排 10 个任务，满足任务总数不少于 30 的要求。

每次 Gitee Wiki 更新必须包含：日期、参与者、目标、输入、决定、未决问题、变更的需求/任务 ID、证据链接。会议照片、原型访问地址、测试截图、发布地址和用户反馈不能只存在个人电脑中。
## 12. v0.3 知识点与真题分析契约

### 12.1 DOCX 与图片

DOCX 用正文 block（段落或表格）在该版本内的顺序定位；表格单元格可再指定 row/col。原始 Word 页码受布局环境影响，不能伪造。转换出的 PDF 页码是“预览页码”，不自动视作 DOCX 正文引用页码。转换/解析失败须保留可观察状态。

扫描 PDF 在 P0 可查看原页并人工补录题目。补录保存独立转录文本、来源页、确认人及时间，Citation 标 source_kind=manual_transcript；原文摘录校验针对转录文本，并保留原页供人工比对。不声称解析器已识别原图中文字。OCR 为 P1。

P0 图片支持 PNG/JPEG/WebP 上传、笔记内嵌与课件截图保存，每张≤10 MiB；服务端验证实际类型、解码尺寸和资源预算。截图保存来源版本与页号。采用 `![[asset:<uuid>|说明]]` 作为 Hustudy 内部嵌入语法，编辑器提供按钮；不是 Obsidian 插件/格式完全兼容声明。完整知识库导出把链接转成相对 Markdown 路径，并附 assets 目录和来源清单。

### 12.2 教学报告结构

StudyReport 字段：scope_version_ids、summary、topics、learning_sequence、prerequisites、examples、self_checks、citations、model_mode、review_status。

每个 topic 包含：稳定 topic_id、名称、别名、解释、重点理由、难点原因、常见误区、疑似考点、引用。每个“重点/难点/考点”标签都有 origin：

- teacher_mark：用户确认的教师标注/授课大纲；
- observed_exam：已审阅历年题中确实出现；
- ai_suggestion：AI 辅助推断。

不能把粗体或出现次数自动当教师考点；没有真题时不编“历年高频”。讲解按“学习目标→前置知识→概念→原理→例子→误区→自测”组织。来源矛盾列出双方，不强行合并成一个事实。

### 12.3 真题处理状态

PastPaper 记录 course_id、year（未知可空）、variant、provenance、document_version_id、内容 hash、review_status；来源为用户提供，默认不保证官方真实性。跨页题目可包含多条 Citation。

PastQuestion 保存原题号、题干、子题、选项、分值（未知为 null）、原始答案及其来源、AI 参考答案与其标记，不能覆盖原始答案。拆题先输出 DRAFT，用户支持合并、拆分、改题干/分值并确认。

QuestionTopicMapping 保存 topic_id、primary/secondary、依据引用、suggested/confirmed/rejected 状态。课程 Topic 可人工改名、合并；别名归一后才统计，修改已确认映射使旧报告标记 STALE 并重算。拆题与映射必须经过确认后才能进入正式统计；草稿另列不能混入分母。

### 12.4 历史统计与补弱

统计快照保存所用 paper/question/mapping 版本、未知年份数、未知分值数、独立样本数。相同文件重复上传或同年同卷重复材料按 hash 和人工确认去重。

主考点用于分值统计；次要标签用于涉及题数，不能将一道多考点题的完整分数重复加到每个考点。未知分值不按 0 分补全；单列未知数量与已知分值覆盖率。年份出现率使用已知年份的不同年份数，不能称未来命中率。

资料匹配显示“已确认有匹配/仅 AI 候选/当前已导入资料未匹配”，最后一项不等于课程没有讲过。差距报告对比历史考点、课件 Topic、笔记与本人已完成作答，未作答的掌握状态为 unknown，不从阅读时长推定掌握。

### 12.5 依据真题生成新题

新增生成模式：同考点变式、历史蓝图模拟、薄弱项专项。P0 自动数量分配在章级别；topic 目标逐题标注和校验。若用户配置严格 topic 配额，必须将其作为显式约束检查，不可作为可选提示忽略。

每题保留 original_past_question_ids（设计参考）、material_citation_ids（知识依据）、mode、topic_ids、difficulty_label、generation_status。真题题干引用不自动成为答案正确性的依据；没有课件/已审阅答案支持时提示补充资料。

标准化题干与本卷/参考原题 hash 相同则拒绝；P1 语义相似检查再检测只换名的近重复。变式应改变条件、数值或情景并重算答案，用户仍要审阅计算与开放题。冻结试卷必须记录检索资料和模型输出快照，不因后续真题重新标注改变旧作答。

### 12.6 新接口

- POST /courses/{id}/assets；GET /assets/{id}；GET /assets/{id}/references；DELETE /assets/{id}
- POST /versions/{id}/study-reports；GET /study-reports/{id}
- POST /courses/{id}/past-papers；POST /past-papers/{id}/extract；PATCH /past-questions/{id}
- POST /past-papers/{id}/confirm；PUT /past-questions/{id}/topic-mappings
- GET /courses/{id}/topics；PATCH /topics/{id}；POST /topics/{id}/merge
- POST /courses/{id}/exam-analyses；GET /exam-analyses/{id}；GET /exam-analyses/{id}/gaps

真题分析不能修改学生已保存笔记；自动生成笔记一律先保存草稿，用户确认后合并。

## 19. 当前代码协作入口

首版代码的四人协作资料统一维护在 `collaboration/`：`roles.md` 记录 A/B/C/D 模块边界与接口，`task_board.md` 记录 P0 任务和真实状态，`workflow.md` 记录分支/评审/测试流程，`roadmap.md` 记录 P0 后优化、P1/P2 与创新候选。角色姓名仍需团队在 GitHub/Gitee 建仓后补充，不能把占位角色写成已确认事实。

当前可运行闭环为：注册/登录 → 创建课程 → 上传 Markdown 并生成切片 → 关键词搜索与文本阅读 → 创建 Markdown 笔记与结构化 Citation → Mock AI 带来源问答 → 创建考点/导入并拆分真题 → 校验蓝图 → 生成 DRAFT 试卷 → 审阅为 READY → 作答、客观评分、错题与复习任务。PPTX/PDF/DOCX 解析依赖 `backend/requirements.txt` 中的可选解析库；真实模型、OCR、语义检索、复杂统计和完整备份仍按 `collaboration/task_board.md` 保持待办。
