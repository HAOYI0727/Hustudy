# Hustudy 项目复现与开发交接

更新时间：2026-10-09

这份文档用于帮助新成员在现有代码基础上完成本地复现、确认当前版本，再按四个业务模块继续开发。它与根目录 `AGENTS.md`、`main_idea.md`、`Hustudy_requirements.md`、`Hustudy_team_collaboration.md` 以及 `docs/contracts.md` 配套使用。

## 1. 项目当前状态

Hustudy 是一个本地优先的大学生课程学习工具。当前代码已经形成一条可演示的最小闭环：

```text
注册/登录 → 创建课程 → 上传资料 → 解析切片 → 搜索/阅读
→ Markdown 笔记与 Citation → Mock AI 带来源问答
→ 真题导入/拆题 → 蓝图 → DRAFT 模拟卷
→ 审阅为 READY → 作答/评分 → 错题 → 复习任务
```

已经完成并可复现的部分：

| 领域 | 当前实现 | 主要位置 |
|---|---|---|
| 共享基础层 | FastAPI 应用工厂、CORS、request_id、SQLite、用户认证、课程归属 | `backend/app/core`、`backend/app/routers/auth.py`、`courses.py` |
| M1 MaterialHub | 资料上传、hash 去重、版本、ProcessingJob、Markdown/TXT 解析、PDF/DOCX/PPTX 解析适配器、切片、文本搜索、原文件下载 | `backend/app/services/materials.py`、`documents.py`、`backend/app/routers/documents.py` |
| M2 AI Study | Mock 问答、中文匹配、`grounded`/`insufficient_evidence`/`provider_error`、引用、StudyReport | `backend/app/routers/ai.py`、`backend/app/schemas/ai.py` |
| M3 NoteGraph | 笔记 CRUD、revision 冲突、UUID 双链、反链、Citation、Asset 基础接口 | `backend/app/routers/notes.py`、`backend/app/models/notes.py` |
| M4 ExamPilot | Topic、真题导入/拆题确认、蓝图约束、DRAFT 试卷、审阅、客观题作答评分、错题、复习任务、反馈 | `backend/app/routers/exams.py`、`backend/app/models/exams.py` |
| 前端工作台 | 登录、课程、资料、笔记、AI、考试、复习导航和基础交互 | `frontend/src/main.tsx`、`frontend/src/styles.css` |

当前已验证：后端 pytest 3 项通过，前端 TypeScript 检查通过，Vite 生产构建通过，FastAPI `/health` 返回 200。工具环境不能直接绑定用户本机端口，因此完整 Safari 联调需要成员在自己的终端启动后端和前端。

当前仍属于待完成或部分完成：Alembic 正式迁移、LibreOffice/PDF.js 预览、备份恢复、真实 LLM Provider、OCR、语义检索、完整真题统计、完整权限/E2E 测试和真实用户反馈。不要把这些内容写成“已实现”。

## 2. 执行环境要求

- 推荐 Python 3.12；当前项目兼容 Python 3.11，现有开发环境使用 Python 3.11.15。
- Node.js 与 npm：用于 Vite/React 前端，建议使用当前 LTS。
- macOS、Linux 或 Windows 均可；路径和启动命令按本机 shell 调整。
- 浏览器：Safari、Chrome 或 Edge 均可。
- 运行数据写入 `data/`，用户上传文件和本地数据库不要提交到仓库。
- 真实模型密钥只放在后端 `.env`，不能放在前端代码或提交记录中。

后端固定依赖见 `backend/requirements.txt`：FastAPI、Uvicorn、Pydantic、SQLAlchemy、Alembic、multipart、HTTPX、pytest、Ruff，以及 `pypdf`、`python-docx`、`python-pptx` 三个解析库。前端依赖和命令见 `frontend/package.json`：React、React DOM、Vite、TypeScript 和 React 类型定义。

## 3. 首次安装与启动

在网络可用的终端执行：

```bash
cd /Users/zhy/Desktop/hustudy
./scripts/setup.sh
```

如果明确使用 Python 3.12：

```bash
PYTHON_BIN=python3.12 ./scripts/setup.sh
```

安装脚本会创建 `.venv`、安装后端依赖、生成 `.env` 并安装前端依赖。首次使用后检查 `.env`，至少设置一个随机的 `HUSTUDY_JWT_SECRET`。

分别打开两个终端：

```bash
# 终端一：后端
.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload
```

```bash
# 终端二：前端
npm run dev --prefix frontend
```

访问：

- 前端：`http://localhost:5173/`
- 后端健康检查：`http://127.0.0.1:8000/health`
- OpenAPI：`http://127.0.0.1:8000/docs`

若当前网络无法安装解析库，可单独重试：

```bash
.venv/bin/pip install pypdf==5.1.0 python-docx==1.1.2 python-pptx==1.0.2
```

缺少解析库时，Markdown/TXT 仍可使用；上传 PDF、DOCX、PPTX 会得到明确的失败状态和错误原因，不会伪装成成功解析。

## 4. 复现后的验收步骤

新成员先执行：

```bash
.venv/bin/python -m pytest -q
./scripts/check.sh
npm run check --prefix frontend
npm run build --prefix frontend
```

随后在浏览器完成以下人工检查：

1. 注册账号并创建一门课程。
2. 上传一个 Markdown 文件，确认资料状态为 `SUCCEEDED`，能看到切片和文本。
3. 用正文关键词和标题关键词搜索，确认结果含定位信息。
4. 创建笔记，使用 `[[note:<uuid>|名称]]` 创建双链，确认反链可见。
5. 发起 Mock AI 问答，确认显示“演示模型”和引用，证据不足时显示限制状态。
6. 创建 Topic、导入真题、拆题并确认，创建蓝图并生成 DRAFT 试卷。
7. 审阅试卷为 READY，开始作答，确认考生接口不返回答案，提交后能看到得分、错题和复习任务。
8. 用另一账号访问第一账号的课程、资料、笔记和试卷，确认服务端返回不可访问。

## 5. 四大模块后续任务

### A：共享基础层 + M1 MaterialHub

优先顺序：

1. 生成并评审 Alembic 第一版迁移，停止依赖开发期自动建表。
2. 完善 ProcessingJob worker：租约、重试、取消、过期 RUNNING 恢复和最大尝试次数。
3. 补齐 PDF 文本预览、LibreOffice 无头转换、PDF.js 预览失败降级。
4. 完成 PPTX/PDF/DOCX/Markdown fixture，验证定位、DOCX 段落/表格顺序、扫描 PDF 失败状态。
5. 增加 PNG/JPEG/WebP 真实类型、解码尺寸、10 MiB 限制、来源版本和删除失效检查。
6. 实现 FTS5 或等价的可解释关键词索引，并保留原文偏移与分词字段分离。

交接边界：对外稳定提供 `DocumentVersion`、`ChunkRef`、`AssetRef`、`Citation`、`ProcessingJob`；其他模块不能直接读取上传文件或修改 M1 表结构。

### B：M2 AI Study

优先顺序：

1. 将当前演示逻辑整理为 `LLMProvider` 接口，保留 Mock Provider。
2. 增加结构化响应校验：StudyReport、AIResult、QuestionDraft 不能依赖正则解析自由文本。
3. 完善课程范围检索、引用摘录校验、资料删除过滤和证据不足路径。
4. 增加提示词版本、token/预算记录、超时和 provider_error 处理。
5. 在用户明确确认发送范围后再接入真实 Provider；页面持续显示模型模式。
6. 后续再做 P1 语义检索、费曼报告和难度辅助估计，不能把 AI 建议写成教师标注或事实结论。

交接边界：只消费 M1 已校验的 `Citation`/`ChunkRef`，不上传文件、不修改笔记正文、不创建正式试卷。

### C：M3 NoteGraph

优先顺序：

1. 将当前笔记接口扩展为完整 Markdown 编辑器和自动保存。
2. 完善双链解析、重命名、目标删除后的失效提示和反链计算。
3. 完善 Citation 插入、版本变更后的旧引用保留、摘录 hash 校验和回源跳转。
4. 实现图片嵌入语法 `![[asset:<uuid>|说明]]`、AssetReference、来源截图和删除失效。
5. 实现知识库导出：相对 Markdown 路径、assets 目录、来源清单和 hash 校验。
6. 实现备份/恢复和并发冲突测试；AI 生成内容必须先保存为可审阅草稿。

交接边界：使用 M1 提供的有效来源，不自行解析原始资料；不改变原始资料版本，不替用户确认考点或主观题最终得分。

### D：M4 ExamPilot

优先顺序：

1. 完善真题父子题、跨页 Citation、未知年份/分值、官方答案来源和去重。
2. 增加人工拆题和考点映射校正，区分 `suggested`、`confirmed`、`rejected`。
3. 实现历史统计快照：主考点分值、次要标签题数、年份出现率、未知分值覆盖率和资料缺口。
4. 实现三种生成模式：同考点变式、历史蓝图模拟、薄弱项专项，并保存来源快照。
5. 强化蓝图整数约束、题型/分值/数量校验、标准化题干 hash 去重和最多两轮修复。
6. 完善主观题 rubric、AI 建议分与人工覆盖、重复提交幂等、截止时间和中断恢复。
7. 增加错题去重、首次提交规则、Asia/Shanghai 复习日历和备份恢复联动。

交接边界：只能调用已校验的 M2 题目草稿，不能绕过 `DRAFT → REVIEWED → READY`，正式试卷必须保留生成时的资料和模型快照。

## 6. 协作规则

- 分支建议：`feature/m1-material`、`feature/m2-ai`、`feature/m3-note`、`feature/m4-exam`、`fix/<issue>`。
- `main` 保持可演示版本，`develop` 用于集成。
- 数据库字段先写入 `docs/contracts.md`，由 A 统一迁移；不要在业务分支私自改共享表。
- API 先改 schema/OpenAPI 示例，再改 service/router 和调用方。
- 每次提交尽量只完成一个可审阅问题，使用 `feat(module): ...`、`fix(module): ...`、`test(module): ...`、`docs: ...`。
- 合并说明必须包含需求 ID、修改目录、迁移变化、测试命令、实际结果和未完成风险。
- 开发前先检查 `git diff`、`docs/progress.md`、`docs/contracts.md` 和自己的模块任务板。
- 角色 A/B/C/D 是占位符；团队确认姓名、仓库地址和分支后再补入，不要虚构成员信息。

## 7. 重要限制与排查

- 旧的 SQLAlchemy 报错 `String object has no attribute _set_parent_with_dispatch` 已修复，正确写法是 `mapped_column(String(36), ForeignKey(...), ...)`。
- 如果前端提示无法连接后端，先检查 Uvicorn 是否运行在 `127.0.0.1:8000`，再检查浏览器控制台和 CORS 配置。
- 如果上传 PDF/DOCX/PPTX 失败，先检查对应解析包和版本；扫描 PDF 在 P0 只保留原页并提示人工转录，不声称已完成 OCR。
- 如果 Ruff 报大量单行分号风格错误，先记录为格式化任务，不要在处理业务契约时顺手重写全部文件。
- `data/`、`.env`、用户上传文件、数据库文件、`node_modules/` 不应提交到 GitHub/Gitee。

## 8. 交接完成标准

新成员完成复现后，应在自己的分支提交一份简短记录，包含：使用的 Python/Node 版本、安装命令、四项验收命令的真实输出、浏览器人工验证结果、修改的需求 ID、尚未完成的风险，以及是否需要更新共享契约。只有代码、测试、文档和真实结果同时具备，任务才可在 `collaboration/task_board.md` 中标记为 `Done`。
