# Hustudy

Hustudy 是面向大学生的本地优先课程学习工具，围绕“资料阅读 → 知识点讲解 → 笔记与引用 → 真题分析 → 模拟练习 → 错题复习”形成学习闭环。首版采用 React/Vite 前端、FastAPI 后端、SQLite 与本地文件存储，按共享基础层加四大业务模块协作推进。

## 当前版本

当前代码已经具备可演示的 P0 最小闭环：

```text
注册/登录 → 创建课程 → 上传资料 → 解析切片 → 搜索/阅读
→ Markdown 笔记与 Citation → Mock AI 带来源问答
→ 真题导入/拆题 → 蓝图 → DRAFT 模拟卷
→ 审阅为 READY → 作答/评分 → 错题 → 复习任务
```

已完成的主要功能：

| 区域 | 当前能力 | 代码位置 |
|---|---|---|
| 共享基础层 | FastAPI 应用工厂、CORS、request_id、SQLite、认证、课程归属过滤 | `backend/app/core`、`backend/app/routers/auth.py`、`courses.py` |
| M1 MaterialHub | 资料上传、hash 去重、版本、ProcessingJob、Markdown/TXT 解析、PDF/DOCX/PPTX 解析适配器、切片、文本搜索、原文件访问 | `backend/app/services/materials.py`、`documents.py`、`backend/app/routers/documents.py` |
| M2 AI Study | Mock 问答、中文匹配、引用、StudyReport、`grounded`/`insufficient_evidence`/`provider_error` | `backend/app/routers/ai.py`、`backend/app/schemas/ai.py` |
| M3 NoteGraph | 笔记 CRUD、revision 冲突、UUID 双链、反链、Citation、Asset 基础接口 | `backend/app/routers/notes.py`、`backend/app/models/notes.py` |
| M4 ExamPilot | Topic、真题导入/拆题确认、蓝图、DRAFT 试卷、审阅、作答评分、错题、复习任务、反馈 | `backend/app/routers/exams.py`、`backend/app/models/exams.py` |
| 前端工作台 | 登录、课程、资料、笔记、AI、考试、复习导航和基础交互 | `frontend/src/main.tsx`、`frontend/src/styles.css` |

当前验证结果：后端 pytest 3 项通过，前端 TypeScript 检查通过，Vite 生产构建通过，FastAPI `/health` 返回 200。完整复现步骤和已知限制见 [`collaboration/project_handoff.md`](collaboration/project_handoff.md)。

## 快速开始

推荐在网络可用的终端执行一次初始化：

```bash
cd /Users/zhy/Desktop/hustudy
./scripts/setup.sh
```

脚本会创建 `.venv`、安装后端依赖、生成 `.env` 并安装前端依赖。项目推荐 Python 3.12，当前也兼容 Python 3.11；需要指定解释器时执行：

```bash
PYTHON_BIN=python3.12 ./scripts/setup.sh
```

打开 `.env`，把 `HUSTUDY_JWT_SECRET` 换成随机长字符串。然后分别在两个终端启动：

```bash
# 终端一：后端
.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload
```

```bash
# 终端二：前端
npm run dev --prefix frontend
```

浏览器访问：

- 前端：`http://localhost:5173/`
- 后端健康检查：`http://127.0.0.1:8000/health`
- OpenAPI：`http://127.0.0.1:8000/docs`

PDF、DOCX、PPTX 解析依赖以下包；如果初始化时因网络原因未安装，可单独执行：

```bash
.venv/bin/pip install pypdf==5.1.0 python-docx==1.1.2 python-pptx==1.0.2
```

## 验证命令

```bash
.venv/bin/python -m pytest -q
./scripts/check.sh
npm run check --prefix frontend
npm run build --prefix frontend
```

浏览器验收建议依次检查：注册和课程创建、Markdown 上传与切片、正文/标题搜索、笔记双链与反链、Mock AI 引用、真题和蓝图、DRAFT 到 READY、作答提交、错题复习，以及两个账号之间的归属隔离。

## 四模块推进计划

### A：共享基础层 + M1 MaterialHub

负责认证、课程、数据库迁移、文件存储、ProcessingJob、四格式资料解析、预览降级、版本、切片、图片和关键词索引。下一步完成 Alembic 第一版迁移、worker 租约/重试/取消、LibreOffice/PDF.js 预览、四格式 fixture、图片安全校验和 FTS5 索引。

对外稳定提供 `DocumentVersion`、`ChunkRef`、`AssetRef`、`Citation`、`ProcessingJob`。其他模块不能直接读取原始文件或私自修改 M1 表结构。

### B：M2 AI Study

负责 Mock/真实 Provider、提示词版本、课程范围检索、StudyReport、结构化输出校验、引用校验、证据不足、provider_error 和预算。下一步整理 `LLMProvider` 接口，接入 schema 校验、超时/预算记录和发送范围确认，再推进语义检索、费曼报告和难度辅助估计。

只能消费 M1 已校验的 `Citation`/`ChunkRef`，不能上传文件、修改笔记正文或直接创建正式试卷。

### C：M3 NoteGraph

负责 Markdown 编辑、自动保存、revision 冲突、标签、UUID 双链/反链、Citation、图片嵌入、导出和备份。下一步完善重命名与删除失效、Citation 回源、`![[asset:<uuid>|说明]]`、知识库导出、备份恢复和 AI 草稿审阅。

使用 M1 提供的有效来源，不自行解析资料，不改变原始版本，也不替用户确认考点或主观题最终得分。

### D：M4 ExamPilot

负责真题导入、拆题校正、Topic 映射、历史统计、蓝图、三种生成模式、审阅、作答、评分、错题与复习。下一步完善父子题/跨页引用、映射状态、统计快照、同考点变式/历史蓝图/薄弱项专项、题干 hash 去重、主观题 rubric、提交幂等和复习日历。

只能调用已校验的 M2 题目草稿，必须遵守 `DRAFT → REVIEWED → READY`，正式试卷需要保存生成时的资料和模型快照。

## 协作与文档入口

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

Alembic 正式迁移、LibreOffice/PDF.js 预览、备份恢复、真实 LLM Provider、OCR、语义检索、完整真题统计、完整权限/E2E 测试和真实用户反馈仍需后续推进。扫描 PDF 在 P0 只保留原页并提示人工转录。真实模型密钥只能放后端 `.env`，`data/`、用户文件、数据库、`.env` 和 `node_modules/` 不应提交到 GitHub/Gitee。

协作分支建议使用 `feature/m1-material`、`feature/m2-ai`、`feature/m3-note`、`feature/m4-exam` 和 `fix/<issue>`；跨模块字段先更新 `docs/contracts.md`，再修改代码和调用方。
