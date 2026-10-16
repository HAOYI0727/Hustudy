# Hustudy 项目复现与开发交接

本文件用于环境复现与历史项目说明；最新实现/验证状态以 [公共进度](../docs/progress.md) 文末为准，最新安装/启动以 [环境指南](../docs/setup_guide.md) 和 [README](../README.md) 为准。每次成员变更交接请追加 [handoff.md](handoff.md)，个人进度/证据见 [协作目录](README.md)。后文早期任务与验证数量保留历史，不作为当前完成状态。

更新时间：2026-10-16

这份文档用于帮助新成员在现有代码基础上完成本地复现、确认当前版本，再按四个业务模块继续开发。它与根目录 `AGENTS.md`、`main_idea.md`、`Hustudy_requirements.md`、`Hustudy_team_collaboration.md` 以及 `docs/contracts.md` 配套使用。

## 1. 项目当前状态

Hustudy 是一个本地优先的大学生课程学习工具。当前代码已经形成一条可演示的最小闭环：

```text
注册/登录 → 创建课程 → 上传资料 → 解析切片 → 搜索/阅读
→ Markdown 笔记与 Citation → 演示检索 / 确认发送的GLM问答
→ 真题导入/拆题 → 蓝图 → DRAFT 模拟卷
→ 审阅为 READY → 作答/评分 → 错题 → 复习任务
```

当前能力以根[README](../README.md)功能表为准：共享JWT/课程/SQLite迁移/存储任务与完整备份恢复、M1四格式解析/原格式阅读/兼容PDF/图片引用/人工补录/分页检索、笔记与基础AI/考试闭环、统一多端工作台均有实现。A01–A08 Review、A09/A10 Doing，成员审阅/正式发布并未完成。

最近后端共享检查116项（10-15），前端14Vitest/42项Chrome-WebKit/类型构建（10-16）通过；详见[测试报告](../docs/test_report.md)。完整真实教学报告、笔记标签/独立附件ZIP、M4映射统计/真实三模式拟卷、真人试用及正式交付仍待推进；OCR/语义检索属于P1。本文文档同步未重跑业务测试。

## 2. 执行环境要求

- 推荐 Python 3.12；当前项目兼容 Python 3.11，现有开发环境使用 Python 3.11.15。
- Node.js/npm须满足锁定Vite与PDF.js要求，具体版本约束见[环境指南](../docs/setup_guide.md)。
- 本机已在macOS验证；其他系统需自行核对依赖和shell，未冒记跨系统验收。
- 浏览器：Safari、Chrome 或 Edge 均可。
- 运行数据写入 `data/`，用户上传文件和本地数据库不要提交到仓库。
- 真实模型密钥只放在后端 `.env`，不能放在前端代码或提交记录中。

后端固定安装版本见 `backend/requirements.lock`：FastAPI、Uvicorn、Pydantic、SQLAlchemy、Alembic、multipart、HTTPX、pytest、Ruff，以及 `pypdf`、`python-docx`、`python-pptx` 三个解析库。前端依赖和命令见 `frontend/package.json`：React、React DOM、Vite、TypeScript 和 React 类型定义。

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

安装脚本会创建 `.venv`、安装后端依赖、生成 `.env` 并安装前端依赖。setup为JWT空值/旧占位初始化随机密钥并保留有效配置；不要为了复现而反复轮换已有密钥。

分别打开两个终端：

```bash
# 终端一：后端 + 资料 worker
bash scripts/dev.sh
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
.venv/bin/python -m pip install -r backend/requirements.lock
```

缺少解析库时，Markdown/TXT 仍可使用；上传 PDF、DOCX、PPTX 会得到明确的失败状态和错误原因，不会伪装成成功解析。

## 4. 复现后的验收步骤

新成员先执行：

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q
bash scripts/check.sh
npm run check --prefix frontend
npm run build --prefix frontend
npm run test:e2e --prefix frontend
```

随后在浏览器完成以下人工检查：

1. 注册账号并创建一门课程。
2. 上传一个 Markdown 文件，确认资料状态为 `SUCCEEDED`，能看到切片和文本。
3. 用正文关键词和标题关键词搜索，确认结果含定位信息。
4. 创建笔记，使用 `[[note:<uuid>|名称]]` 创建双链，确认反链可见。
5. 发起 Mock AI 问答，确认显示演示模式/演示检索标识和引用，证据不足时显示限制状态。
6. 创建 Topic、导入真题、拆题并确认，创建蓝图并生成 DRAFT 试卷。
7. 审阅试卷为 READY，开始作答，确认考生接口不返回答案，提交后能看到得分、错题和复习任务。
8. 用另一账号访问第一账号的课程、资料、笔记和试卷，确认服务端返回不可访问。

## 5. 四大模块后续任务

### A：共享基础层 + M1 MaterialHub

当前状态与证据看[zhy正式任务表](zhy/task_status.md)，不重复安排已有迁移、worker、解析/索引、原格式阅读和完整账户恢复的实现。优先进行真实复杂样本/实机与极限输入验证、成员复验、Gitee过程证据、集成分支和正式发布。基础功能自动通过不等于全部队长职责已完成。

交接边界：对外稳定提供 `DocumentVersion`、`ChunkRef`、`AssetRef`、`Citation`、`ProcessingJob`；其他模块不能直接读取上传文件或修改 M1 表结构。

### B：M2 AI Study

演示检索与GLM课程问答已经接入（片段预览/逐次发送确认/结构化及引用校验），见[集成验收](../docs/zhy/integration/zhipu_qa_acceptance.md)。下一步完善真实教学报告、知识点/例子/自测和M4结构化题目草稿及质量评测；不得把已实现的Provider确认路径继续当Todo，也不能将课程问答等同全部教学能力。P1另行推进。

交接边界：只消费 M1 已校验的 `Citation`/`ChunkRef`，不上传文件、不修改笔记正文、不创建正式试卷。

### C：M3 NoteGraph

现有Markdown编辑、安全预览、自动保存/409、UUID双链/反链、Citation回源、图片嵌入/失效和单笔记导出继续维护。下一步补笔记标签、独立知识库ZIP/附件相对路径与来源清单。共享完整账户备份/恢复已实现并有模块适配，不是本模块尚未实现项；独立知识库ZIP与账户ZIP用途不同。

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
- 成员/角色已经确认：zhy/A、xtc/B、fzk/C、gcx/D；仓库账号、地址、PR 和分支证据仍须按实际补入。每人维护同名目录，提交/PR 前追加 handoff，由接收人本人记录复验，不代填他人签收。

## 7. 重要限制与排查

- 旧的 SQLAlchemy 报错 `String object has no attribute _set_parent_with_dispatch` 已修复，正确写法是 `mapped_column(String(36), ForeignKey(...), ...)`。
- 如果前端提示无法连接后端，先检查 Uvicorn 是否运行在 `127.0.0.1:8000`，再检查浏览器控制台和 CORS 配置。
- 如果上传 PDF/DOCX/PPTX 失败，先检查对应解析包和版本；扫描 PDF 在 P0 只保留原页并提示人工转录，不声称已完成 OCR。
- 如果 Ruff 报大量单行分号风格错误，先记录为格式化任务，不要在处理业务契约时顺手重写全部文件。
- `data/`、`.env`、用户上传文件、数据库文件、`node_modules/` 不应提交到 GitHub/Gitee。

## 8. 交接完成标准

新成员完成复现后，应在自己的分支提交一份简短记录，包含：使用的 Python/Node 版本、安装命令、适用验收命令的真实输出、浏览器人工验证结果、修改的需求 ID、尚未完成的风险，以及是否需要更新共享契约。只有代码、测试、文档和真实结果同时具备，任务才可在 `collaboration/task_board.md` 中标记为 `Done`。


GitHub源码提交/推送/PR按[github_sync.md](github_sync.md)操作；尚未推送不能写为远端已同步，Gitee课程证据与网站部署分别维护。
