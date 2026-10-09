# Hustudy 实施进度

更新时间：2026-10-09

## Phase 0：共享基础层

| 项目 | 状态 | 证据 |
|---|---|---|
| 工程目录与环境示例 | 已完成 | `backend/`、`frontend/`、`.env.example`、`README.md` |
| FastAPI 应用工厂、健康检查、CORS、request_id | 已完成 | `backend/app/main.py`、`backend/app/routers/health.py` |
| SQLite 外键/WAL/忙等待 | 已完成 | `backend/app/core/database.py` |
| User/Course 与密码/令牌基础 | 已完成 | `backend/app/models`、`backend/app/core/security.py` |
| 课程 API 的 user_id 归属过滤 | 已完成 | `backend/app/routers/courses.py` |
| Alembic 第一版迁移 | 未完成 | 当前仅开发期自动建表 |
| React 页面与真实 API 客户端 | 骨架 | `frontend/`；尚未安装依赖或实现业务页面 |

## 当前未完成

文档解析、预览、文件存储 API、笔记/图片、AI Provider、真题分析、拟卷、作答、复习、备份和 E2E 均未实现。性能、用户试用、模型质量和人工映射指标均保持待测，不能据此宣称通过需求验收。

## 下一步交接

1. A：生成并评审第一版 Alembic revision，补齐文件存储与 ProcessingJob。
2. M1：实现 FR-03–09/FR-36，先以自制 PPTX、PDF、DOCX、Markdown fixture 验证定位和降级。
3. M3：在 Citation 契约稳定后实现 FR-10–15/FR-37。
4. M2：消费 M1 的有效 ChunkRef，实现 grounded/insufficient_evidence/provider_error 三路径。
5. M4：等 Citation 和结构化题目草稿契约评审后实现真题、蓝图和作答。

## 本轮真实校验

- `./scripts/check.sh`：通过 Python AST 语法检查（21 个 Python 文件）；Ruff 因未安装而跳过。
- 安全原语检查：通过密码哈希往返、错误密码拒绝、访问令牌签名篡改拒绝。
- 前端静态基础检查：`frontend/package.json` JSON 有效，入口源码存在。
- 未执行：FastAPI/SQLAlchemy API 测试、Ruff、前端 `npm run build`。当前环境没有安装 Python 依赖或 `frontend/node_modules`，且目标技术基线要求 Python 3.12，当前解释器为 Python 3.9.6。
- Git：工作目录原先没有仓库，系统拒绝创建 `.git`，因此分支/提交需由团队在可写 Git 仓库中完成。

## 环境初始化

- `.venv`：已创建，解释器为 Python 3.11.15。
- 后端/前端依赖：当前沙箱网络受限，未安装；请按 `docs/setup_guide.md` 在本机完成。

## 2026-10-09 启动问题修复

修复 `backend/app/models/base.py` 中 `mapped_column` 的参数顺序错误：类型应先于 `ForeignKey` 传入。验证结果：应用启动生命周期通过，`GET /health` 使用 FastAPI `TestClient` 返回 200；后端 pytest 2 项通过。受当前执行环境限制，未通过工具直接绑定本机端口，但 Uvicorn 已完成应用加载和 startup。

## P0 第一版闭环进展（2026-10-09）

本轮已完成可演示的最小闭环：课程创建、资料上传与版本/任务状态、Markdown/TXT 解析、PDF/DOCX/PPTX 解析适配器、课程范围搜索、文本阅读、笔记 revision 冲突与双链、Citation/Asset 基础接口、演示 AI 问答与 StudyReport、真题导入/拆题确认、蓝图校验、DRAFT 试卷生成、审阅到 READY、作答保存/提交、客观题判分、错题与复习任务、反馈，以及对应前端工作台。

真实验证：

- `PYTHONPATH=backend .venv/bin/python -m pytest -q`：3 passed（含跨域归属、资料、AI、拟卷的烟雾闭环）。
- `npm run check --prefix frontend`：通过。
- `npm run build --prefix frontend`：通过，生成 `frontend/dist/`。
- `.venv/bin/ruff check backend/app backend/tests`：未通过；现有骨架大量使用单行分号写法（共 167 条 E/F 诊断），需单独安排格式化任务，未在本轮扩大修改范围。
- Safari/浏览器已验证登录页与课程工作台的页面渲染；工具沙箱不能直接绑定本机后端端口，需在用户终端启动 Uvicorn 后进行完整浏览器联调。

仍需团队在 P0 验收中补齐：Alembic 迁移、LibreOffice PDF 预览 worker、备份/恢复、完整权限与异常测试矩阵、真实 PPTX/PDF/DOCX fixture、真题考点统计和人工审阅证据。P1 的 OCR、语义检索、费曼报告、间隔复习和真实模型 Provider 不应标记为已完成。
