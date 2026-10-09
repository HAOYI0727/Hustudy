# Hustudy 共享契约（Phase 0）

根目录是唯一工程根。四个业务模块通过 `backend/app/schemas`、服务接口和 API 交互，不能直接读写其他模块的表。成员 A 统一维护数据库迁移。

## API

- 前缀：`/api/v1`
- 资源 ID：UUID 字符串；时间：带时区 ISO 8601，数据库按 UTC 保存。
- 归属错误统一按 404 处理，避免泄露其他用户对象是否存在。
- 创建资源返回 201；异步任务入队返回 202；参数错误返回 422。
- 统一错误形态：`{"error":{"code","message","details","request_id"}}`。

Phase 0 已落地：`/health`、`/api/v1/auth/register`、`/api/v1/auth/login`、`/api/v1/auth/me`、课程 CRUD。其余接口按阶段增加，不在骨架中伪装为可用。

## 共享对象

`Citation` 固定包含 `version_id`、`chunk_id`、`locator`、`quote`、`availability`；`locator.type` 为 `slide/page/heading/docx_block`。后续 M1 必须验证 quote 属于对应 chunk，M2/M3/M4 只能消费校验后的对象。

处理任务状态为 `QUEUED → RUNNING → SUCCEEDED/FAILED/CANCELLED`。文档版本的 `parse_status`、`preview_status`、`index_status` 必须分开保存。

## 模块边界

| 模块 | 目录/表的所有权 | 对外依赖 |
|---|---|---|
| M1 MaterialHub | `services/materials`、解析器、文档/版本/chunk/asset/job | 共享认证、课程、Citation |
| M2 AI Study | `ai`、`services/ai`、StudyReport/AIResult | M1 只读 Citation/ChunkRef |
| M3 NoteGraph | `services/notes`、笔记/双链/引用 | M1 Citation；M2 可审阅草稿 |
| M4 ExamPilot | `services/exams`、真题/Topic/试卷/复习 | M1 来源；M2 题目草稿；M3 回源 |
