# Hustudy 四人协作与课程交付指南

本文与 `AGENTS.md`、`main_idea.md`、`Hustudy_requirements.md` 一起使用，专门解决“队长搭建基础框架、三名成员并行开发、最终能够集成验收”的协作问题。

## 1. 总体组织方式

Hustudy 采用一个共享基础层和四个业务模块：

```text
共享基础层：认证、课程、数据库、文件存储、任务状态、API规范、测试与Gitee
       ├── M1 MaterialHub：资料上传、解析、预览、切片、分类、检索
       ├── M2 AI Study：RAG、知识点报告、重点难点考点、AI结果校验
       ├── M3 NoteGraph：Markdown、标签、双链、图片、Citation、导出
       └── M4 ExamPilot：真题、考点映射、统计、模拟题、作答、错题复习
```

共享基础层由队长先搭建。四名成员分别拥有一个模块的代码、测试和文档；其他成员通过稳定接口使用模块，不直接修改对方的内部表和服务。

## 2. 四名成员的职责和十项任务

角色 A 为 zhy（张昊轶）队长，负责共享层、M1 和最终集成；B 为 xtc（向天晨）负责 M2；C 为 fzk（付振琨）负责 M3；D 为 gcx（高长鑫）负责 M4。成员映射统一见 `collaboration/roles.md`，仓库账号/Issue/PR/Wiki 地址按实际补充。

个人协作进度放 `collaboration/<成员>/progress.md`，功能与优化放 `docs/<成员>/features.md`、`optimizations.md`；根级文件维护公共契约、规则、操作和集成状态。每个切片提交/PR 前追加 `collaboration/handoff.md`，接收人记录真实复验，队长汇总任务板/进度/追踪。模板不代表本人已完成或已接收。完整维护约束见 `AGENTS.md` 第 20 节。

| 成员 | 模块 | 任务编号 | 任务内容 |
|---|---|---|---|
| A 队长 | M1 MaterialHub + 基础层 | A01–A10 | A01 monorepo/环境；A02 用户课程与 JWT；A03 SQLAlchemy/Alembic；A04 文件存储/Job；A05 四格式上传；A06 PPTX/PDF/DOCX/MD 解析；A07 预览和降级；A08 FTS5/索引；A09 Gitee/CI/启动脚本；A10 集成分支和发布构建 |
| B | M2 AI Study | B01–B10 | B01 Provider/Mock；B02 Prompt 版本；B03 检索上下文；B04 课程问答；B05 章节讲解；B06 重点难点考点报告；B07 引用/坏 JSON 校验；B08 异步任务与进度；B09 AI 测试；B10 AI 使用文档 |
| C | M3 NoteGraph | C01–C10 | C01 Markdown 编辑器；C02 标签/全文检索界面；C03 UUID 双链；C04 反向链接；C05 图片上传/嵌入；C06 资料 Citation；C07 导出/备份；C08 自动保存/409 冲突；C09 笔记与安全测试；C10 交互说明和原型 |
| D | M4 ExamPilot | D01–D10 | D01 真题导入；D02 AI 拆题与人工校正；D03 Topic/课件映射；D04 历史统计/缺口；D05 蓝图约束；D06 三种模拟题模式；D07 作答/判分；D08 错题/复习；D09 全链路 E2E；D10 试用、反馈和汇报演示 |

四人各领取 10 个任务，总任务数为 40，满足教案“任务数不少于 30、每人约 5–10 个任务”的要求。任务状态统一使用 `Todo / Doing / Review / Done / Blocked`。

## 3. 队长第一阶段搭建顺序

队长第一次让 Codex 执行时，只完成基础骨架，不提前实现四个模块的全部业务逻辑：

1. 创建 `backend/`、`frontend/`、`docs/`、`fixtures/`、`scripts/` 和 `data/` 目录；
2. 初始化 FastAPI、React/Vite、环境配置、日志、CORS、统一响应和健康检查；
3. 创建 User、Course、Document、DocumentVersion、ProcessingJob 的最小迁移；
4. 实现 Mock 登录用户和 `user_id` 过滤；
5. 定义共享 Pydantic schemas：`Citation`、`ChunkRef`、`AssetRef`、`JobStatus`、错误响应；
6. 写入 `docs/contracts.md`，固定 API 前缀、UUID、时间、状态、错误码和分页格式；
7. 提供一条可运行的 `make dev` 或等价启动命令、一条测试命令和一份 `.env.example`；
8. 加入最小 CI 或本地检查脚本，并在 Gitee 建立 `main`、`develop` 和队员功能分支。

第一阶段通过条件：后端健康检查返回成功；前端可以打开登录/课程占位页面；数据库迁移可重复执行；Mock 用户不能访问另一用户的课程；测试命令在干净环境可运行。

## 4. 共享契约

### 4.1 通用资源字段

```text
id: UUID
user_id: UUID
created_at / updated_at: UTC ISO 8601
status: 明确枚举
revision: 乐观锁资源使用
```

### 4.2 资料和引用

M1 输出 `DocumentVersion`、`ChunkRef`、`AssetRef`。引用必须携带 `version_id`、`chunk_id`、定位类型和值、原文摘录和 hash。M2、M3、M4 只能引用这些结构，不能用文件名、页码字符串自行拼接来源。

### 4.3 AI 输出

M2 输出经过 Pydantic 校验的 `StudyReport`、`AIResult` 或 `QuestionDraft`。M4 可以消费题目草稿，但必须重新执行题数、分值、引用和去重校验。M3 插入 AI 内容时保存 `model_mode` 和 `review_status`。

### 4.4 任务与错误

耗时工作统一返回任务 ID，状态为 `QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELLED`。HTTP API 不长时间等待模型或文档转换。错误使用 `error.code/message/details/request_id`；参数错误 422，任务入队 202，资源归属错误按 404 处理。

## 5. Gitee 协作流程

### 5.1 仓库和 Wiki

仓库主页必须包含：项目简介、在线地址、演示账号说明、启动方式、功能截图、成员分工、许可证/第三方说明和文档目录。Wiki 至少建立：

```text
01-项目立项与NABCD
02-用户与需求分析
03-原型与交互流程
04-甘特图与任务分配
05-架构/数据结构/算法设计
06-开发日志与版本记录
07-测试报告与测试用例
08-用户指南与发布说明
09-用户反馈与改进记录
10-成员项目体会
```

Wiki `04-甘特图与任务分配` 必须展示不少于 30 个功能任务、四名成员的责任、预计开始/结束节点和依赖关系；每次会议记录日期、参与者、目标、输入、决策、待解决问题和关联任务。原型页面要提供可访问链接及关键流程截图。

### 5.2 分支与合并

```text
main       可交付/可演示版本
develop    集成测试版本
feature/m1-material
feature/m2-ai
feature/m3-note
feature/m4-exam
```

成员每天在自己的功能分支提交；完成一个任务后创建合并请求，描述需求 ID、改动、测试、截图和风险。队长只合并通过评审和测试的提交。合并后必须在 Wiki 或 `docs/progress.md` 中记录。

### 5.3 提交消息

```text
feat(m1): add pptx document parser
feat(m2): validate grounded study report
feat(m3): support note backlinks
feat(m4): add past-question blueprint
test(m4): cover duplicate paper and unknown score
docs: update phase 2 integration checklist
```

## 6. 与教案时间节点对应的交付计划

| 节点 | 必须完成 | Hustudy 证据 |
|---|---|---|
| 第一次课 | 立项、头脑风暴、mindmap、会议记录/照片、NABCD、Gitee 主页 | Wiki `01`、思维导图图像、会议记录和原始照片 |
| 第二次课 | 智能需求获取和评审 | 需求来源、用户故事、AI 提示词、评审问题 |
| 第三次课前 | 需求分析提交、第一次师生沟通 | 主需求文档、AI/人工核实记录、追踪矩阵、沟通修改记录 |
| 第四次课 | 智能开发方法 | `AGENTS.md`、Codex 提示模板、任务分支和评审规则 |
| 第五次课 | 架构/数据/算法、设计报告、源码和可执行程序 | 架构图、ER 图、接口、状态机、Gitee 记录、可运行版本 |
| 第六次课 | 测试理论和计划 | 单元/API/E2E/性能/权限测试计划与用例 |
| 第七次课 | 测试报告、用户说明、发布、用户反馈 | 测试报告、用户指南、Gitee Pages/部署地址、反馈分析；发布地址按教案要求至少维护一个月 |
| 第八次课 | 8 分钟公开展示 | 演示脚本、PPT、录屏/照片、成员个人体会 |

教案评分为：需求分析 20%、原型/概要/详细设计 35%、编码与测试 30%、功能创意 10%、真实用户反馈 5%。因此每个阶段都需要留下证据，不能只在最后展示一个运行页面。

## 7. Codex 分阶段提示词

### 队长初始化

```text
你是 Hustudy 项目队长的工程助手。先阅读 AGENTS.md、main_idea.md、Hustudy_requirements.md 和 Hustudy_team_collaboration.md。
当前只实现 A01–A04：创建 monorepo、FastAPI/React 基线、配置日志、SQLite/Alembic、User/Course/DocumentVersion/ProcessingJob 最小模型、Mock 登录和健康检查。
不要实现四个业务模块的具体功能，不要修改队员模块目录。完成后运行迁移、后端测试、前端构建，并报告真实结果。
```

### 模块成员

```text
你负责 Hustudy 的 M<N> <模块名>，当前任务为 <任务编号>/<需求 ID>。
先阅读 AGENTS.md、main_idea.md、Hustudy_requirements.md 和本协作指南。
允许修改：<目录>；禁止修改：<其他模块目录>。
依赖的共享 schema/API：<列出契约>。
完成一个最小垂直切片，包含代码、测试、接口文档和异常路径；不要伪造测试通过。
```

## 8. 每个模块的完成定义

- 有一个可从 Gitee Issue 追溯的任务编号；
- 至少一个正常路径和一个异常路径测试；
- 服务端执行 `user_id` 权限检查；
- API、数据库迁移和前端状态一致；
- 交互包含加载、空数据、失败和成功状态；
- 产生截图、日志或测试报告等可复核证据；
- 能在 `develop` 分支通过集成测试；
- 更新个人项目体会所需的工作记录。

## 9. 队长每轮集成检查

```text
git status / git diff
→ 检查迁移与共享 schema
→ 后端测试与前端构建
→ 运行最短用户闭环
→ 检查 Gitee Wiki/Issue/提交记录
→ 记录已完成、风险、阻塞和下一步
```

队长不得用新增功能掩盖未修复的集成错误；当时间不足时，保留四模块最小闭环，优先砍掉 P1/P2，而不是砍掉测试、权限、来源和发布证据。
