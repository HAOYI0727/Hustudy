# Hustudy API（Phase 0）

服务默认运行在 `http://127.0.0.1:8000`，OpenAPI 地址为 `/docs`。

| 方法 | 路径 | 说明 | 状态 |
|---|---|---|---|
| GET | `/health` | 数据库和服务健康检查 | 已实现 |
| POST | `/api/v1/auth/register` | 注册并返回 bearer token | 已实现 |
| POST | `/api/v1/auth/login` | 登录并返回 bearer token | 已实现 |
| GET | `/api/v1/auth/me` | 查询当前用户 | 已实现 |
| GET/POST | `/api/v1/courses` | 当前用户课程列表/创建 | 已实现 |
| PATCH/DELETE | `/api/v1/courses/{course_id}` | 当前用户课程更新/删除 | 已实现 |

认证使用 `Authorization: Bearer <access_token>`。错误响应按 `docs/contracts.md` 的 `error.code/message/details/request_id` 形态返回。资料、笔记、AI、真题和考试 API 将在对应阶段追加。

## 当前 P0 可运行接口（2026-10-09）

以下接口已接入 FastAPI，并由前端工作台调用：

| 模块 | 已覆盖接口 |
|---|---|
| 资料 | `POST /api/v1/courses/{id}/documents`、`GET /courses/{id}/documents`、`GET /documents/{id}/versions`、`GET /versions/{id}/chunks`、`GET /courses/{id}/search`、`GET /jobs/{id}`、`GET /versions/{id}/original`、`DELETE /documents/{id}` |
| 笔记与图片 | `GET/POST/PATCH/DELETE /notes`、`GET /notes/{id}/backlinks`、`GET /notes/{id}/citations`、`POST /assets`、`GET /assets/{id}` |
| AI | `POST /courses/{id}/ai-queries`、`GET /ai-results/{id}`、`POST /versions/{id}/study-reports` |
| 真题与试卷 | 课程考点、真题导入/拆题/确认、蓝图、试卷生成/审阅、作答保存/提交 |
| 复习 | `GET /mistakes`、`GET/POST /review-tasks`、`POST /review-tasks/{id}/complete`、`POST /feedback` |

演示模型固定标记为 `demo`；真实 Provider 尚未配置。资料解析支持 Markdown/TXT，PDF/DOCX/PPTX 依赖安装后启用；扫描 PDF 会返回可观察的失败状态。
