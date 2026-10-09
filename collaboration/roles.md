# 模块职责与交接

## A：共享基础层 + M1 MaterialHub

负责认证、课程、SQLite/Alembic、文件存储、ProcessingJob、PPTX/PDF/DOCX/Markdown/图片上传、解析、预览降级、版本、切片、关键词检索和归属隔离。对外输出 `DocumentVersion`、`ChunkRef`、`AssetRef`、`Citation`、`ProcessingJob`。

允许修改：`backend/app/core`、`models/material.py`、`services/documents.py`、`routers/documents.py`、相关 schema/test/migration。不能改变 M2/M3/M4 的业务事实表。

建议分支：`feature/m1-material`。交接验收：FR-03–09、FR-36–37、TC-02–06、TC-26–27。

## B：M2 AI Study

负责 Mock/真实 Provider、提示词版本、课程范围检索、StudyReport、AIResult、引用校验、证据不足、provider_error 和预算状态。Mock 结果必须标记演示模型；真实模式必须在服务端确认发送范围。

允许修改：`backend/app/ai`、`services/ai`、`routers/ai.py`、AI schema/test。只能消费 M1 的有效 Citation/ChunkRef，不能直接读取文件。

建议分支：`feature/m2-ai`。交接验收：FR-16–20、FR-38、TC-10–12、TC-29。

## C：M3 NoteGraph

负责 Markdown 编辑、自动保存、revision 409、标签、UUID 双链/反链、Citation、图片 Asset/AssetReference、导出与备份交互。

允许修改：`backend/app/models/notes.py`、`services/notes`、`routers/notes.py`、笔记前端组件和相关 test。引用必须通过 M1 校验；AI 内容只能作为可审阅草稿插入。

建议分支：`feature/m3-note`。交接验收：FR-10–15、FR-37、TC-07–09、TC-27。

## D：M4 ExamPilot

负责真题导入、拆题校正、Topic、映射、统计、蓝图、三种生成模式、审阅、作答、评分、错题、ReviewTask 和试用反馈。

允许修改：`backend/app/models/exams.py`、`services/exams`、`routers/exams.py`、考试前端和相关 test。不能绕过 `DRAFT → REVIEWED → READY`，不能向考生接口泄露答案。

建议分支：`feature/m4-exam`。交接验收：FR-21–30、FR-35、FR-39–45、TC-13–18、TC-28–31。

## 共享接口

所有持久对象使用 UUID、`user_id`、UTC 时间；引用包含版本、切片、定位、摘录和可用状态。跨模块字段先更新 `docs/contracts.md`，再改代码。数据库迁移由 A 统一生成和合并。
